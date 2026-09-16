---
title: "Request-Header Deadlines: Absolute Header Limits and Rolling Body Idle Timeouts"
linkTitle: "Request-Header Deadlines"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The decision record for PR #196's HTTP deadline repair (fix 055030ea5): the
  connection wrapper's rolling deadline overwrote every absolute read-header
  deadline, and the --read-header-timeout flag was never wired into the
  server. Covers the two timeout classes, the configuration matrix, what
  HTTP/1, HTTP/2, and TLS each get, and why the rejected alternatives would
  have killed long uploads.
tags: [Design, HTTP, S3, Review]
weight: 10
draft: false
url: "/blog/design/request-header-timeouts/"
---

This page records the repair of Server's HTTP read deadlines, merged into
main as part of [PR #196](https://github.com/pgsty/silo/pull/196) (fix
[`055030ea5`](https://github.com/pgsty/silo/commit/055030ea5)).

> **As of 2026-09-16:** the fix is on verified main
> [`40220bd836cb`](https://github.com/pgsty/silo/commit/40220bd836cbd066ca424fa4dc5dbb90057fb55a). It is
> **not** in the published Server 20260903.<br>
> **Evidence class:** synthetic — a direct TCP comparison (header limited to
  100 ms, header arriving over 400 ms, standard Go refuses where old SILO
  returned 204), plus a real single-drive process probe where flag and
  environment settings both rejected a 400 ms slow header while healthy
  requests continued. No production incident is attributed; the issue that
  motivated the investigation is a slow-HTTP DoS scanner report that has not
  been reproduced against a deployed cluster.

## Two timeout classes, one connection {#classes}

- **Request-header absolute deadline.** `ReadHeaderTimeout` bounds the *total*
  time from the start of header reading to its completion. Trickle-feeding
  bytes cannot extend it. On HTTP/1 keep-alive connections, Go first uses
  `IdleTimeout` while waiting for the next request's initial bytes, then
  starts a fresh header deadline. `ReadHeaderTimeout` also participates in
  the separate TLS-handshake timeout calculation.
- **Body rolling idle timeout.** Once headers parse and the connection enters
  the active phase, the existing rolling semantics return: every successful
  read extends the deadline, and only a *stall between bytes* (the
  configured idle timeout) kills the connection. A long upload or download
  that keeps making progress is not capped in total duration by this HTTP/1
  repair; other protocol, proxy, and application timeouts still apply.

Before this repair, the first class did not exist in practice: the
connection-layer wrapper replaced the socket deadline with
`now + idle + 250 ms` before every partial read, overwriting whatever
absolute deadline `net/http` had set — so a slow reader could hold a
connection open indefinitely by sending one byte per idle window.

## Two independent defects {#root-cause}

1. **The connection layer neutralized the absolute deadline.** The
   `DeadlineConn` wrapper's read path reset the socket deadline on every
   partial read, defeating the read-header deadline Go's server sets. The
   direct-TCP baseline proved it in isolation: with a 100 ms header limit and
   a 2 s idle window, a header that finishes at 400 ms was accepted.
2. **The configuration never reached the server.** The CLI accepted
   `--read-header-timeout` and `MINIO_READ_HEADER_TIMEOUT`, parsed defaults
   and all — and the server-context builder copied `IdleTimeout` while
   dropping `ReadHeaderTimeout` entirely, so the running server always saw
   zero. Fixing defect 1 alone left the real process accepting slow headers;
   the second fix is one line next to the idle-timeout binding.

The reason this stayed invisible for so long: the flag's default (30 s) equals
the idle timeout's default, and with the flag unwired the server fell back to
exactly that same 30 s — so every observable default behaved as if configured.

## Configuration {#config}

- **Flag:** `--read-header-timeout` (`Hidden: true`, absent from ordinary CLI help)
- **Environment:** `MINIO_READ_HEADER_TIMEOUT`
- **Default:** 30 s (equal to the idle timeout default)
- There is **no YAML configuration field** for either timeout; the value binds
  once at startup from flag > environment > default.

| Setting | Effect |
| :-- | :-- |
| header > 0 | Absolute cap on HTTP/1 header phases; participates in Go's TLS-handshake read window (including the HTTP/2 handshake) |
| header = 0 (explicit) | Falls back to Go's rule: the read timeout (= idle timeout) applies; the CLI default is 30 s |
| header < 0 | Disables the header-specific cap. Positive read/write timeouts still bound TLS handshake reads, and positive `IdleTimeout` still bounds the keep-alive wait. This does not disable every connection timeout. |
| idle shortened, header unset | Header phase independently uses the 30 s default — the one combination looser than a naive expectation, though still strictly tighter than the pre-fix unbounded extension |

A negative value reopens unbounded slow-header trickling; it is not a recommended compatibility setting. An incomplete header cut off by the deadline normally sees a closed connection, not a guaranteed HTTP error status. The trigger was @AEGEGE's scanner report [#183](https://github.com/pgsty/silo/issues/183); [PR #195](https://github.com/pgsty/silo/pull/195) was integrated through #196. The experiment does not establish reproduction in that deployment.

## What each protocol gets {#protocols}

- **HTTP/1**: headers and keep-alive waits are absolute; the body keeps the
  rolling idle timeout. The connection-state hook composes with (rather than
  replaces) any caller hook.
- **TLS**: handshake *reads* take the minimum of the positive header
  deadline and the existing read/write timeouts; after the handshake, a fresh
  header limit begins. **The handshake's write side remains rolling** — this
  repair is not a complete TLS-handshake resource limit.
- **HTTP/2**: untouched. When h2 is negotiated, the phase switching is
  skipped entirely; h2 keeps its own native per-stream read timeout, which is
  absolute, and `ReadHeaderTimeout` never enters the h2 configuration.
- **Internal callers**: Linux internode dialing uses its own rolling
  semantics; grid-hijacked connections unwrap to the raw TCP connection
  before any of this applies.

## Rejected alternatives {#rejected}

- **Clamp all future deadlines globally.** Go 1.27 sets a whole-request
  deadline in some paths; with the read timeout equal to the idle timeout,
  this would hard-cap entire HTTP/1 requests — header plus body — and kill
  every large upload.
- **Drop the read timeout and reinterpret zero as rolling idle.** Zero is
  `net/http`'s "never time out" for background reads and hijacked
  connections; reinterpreting it would break long handlers, and h2 would
  lose its per-stream timeout.
- **Wrap the body reader / response controller.** Full chunked/drain/EOF
  accounting with h2 special cases is a far larger change than the header
  defect requires. (A later, unmerged branch explores a body-side response
  controller for the same DoS family; as of this record it is not part of
  main and not part of this repair's claims.)
- **Reconstruct the standard library's deadline arithmetic in the hook.**
  Duplicates stdlib internals that drift between Go versions; remembering the
  value stdlib actually asked for is the robust form.
- **Auto-derive strictness from value comparisons.** With all three defaults
  equal at 30 s, "shorter than the idle window" is indistinguishable in
  production defaults; such logic only works in test configurations.

## Verification and limits {#verification}

Tests pin the connection wrapper across three consecutive update periods
(no extrapolation of the absolute cap), the phase transitions over
HTTP/1 keep-alive, TLS, and HTTP/2-only negotiation, and the flag/env
binding on the real CLI context; a process probe exercised a live server
with a 100 ms header limit rejecting a header that takes 400 ms. Known
limits: the TLS handshake write side stays rolling; handler CPU/storage
waits have no deadline; the absolute header cap carries no slack while the
rolling idle keeps its ~250 ms update slack; and multi-node, cross-region
long-transfer acceptance is future work — the integration record explicitly
does not count a scripted S3 long transfer as passed for this repair.

The upgrade note (a shorter header timeout also narrows the TLS handshake
window; it is not a total-duration limit for uploads or downloads) is in the
[component matrix](/compatibility/versions/#september-reliability).

Related records: [tags](/blog/design/replicated-tag-ordering/) · [metadata](/blog/design/replica-metadata-normalization/) · [HTTP](/blog/design/request-header-timeouts/) · [audit](/operations/replication/replica-metadata-audit/)
