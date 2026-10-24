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
  server. Covers the two timeout classes, the configuration matrix, how
  HTTP/1, HTTP/2, and TLS behave across phases, and why the rejected
  alternatives would have killed long uploads.
tags: [Design, HTTP, S3, Review]
weight: 10
draft: false
url: "/blog/design/request-header-timeouts/"
---

This article records the repair of Server's HTTP read deadlines, merged in [PR #196](https://github.com/pgsty/silo/pull/196) (fix [`055030ea5`](https://github.com/pgsty/silo/commit/055030ea5)) and shipped in [Server 20260916](/blog/release/silo-20260916/) (`40220bd836cbd066ca424fa4dc5dbb90057fb55a`).

The investigation was prompted by a slow-HTTP DoS scanner report ([#183](https://github.com/pgsty/silo/issues/183)) and verified via a direct TCP comparison (with the header limited to 100 ms and arriving over 400 ms, standard Go refuses where the pre-fix server returned 204) and a single-drive process probe where both flag and environment settings rejected a 400 ms slow header while healthy requests continued.

## Two Timeout Classes, One Connection {#classes}

- **Request-header absolute deadline.** `ReadHeaderTimeout` bounds the *total* time from the start of header reading to its completion. Trickle-feeding bytes cannot extend it. On HTTP/1 keep-alive connections, Go first uses `IdleTimeout` while waiting for the next request's initial bytes, then starts a fresh header deadline. `ReadHeaderTimeout` also participates in the separate TLS-handshake timeout calculation.
- **Body rolling idle timeout.** Once headers parse and the connection enters the active phase, rolling idle semantics take over: every successful read extends the deadline, and only a stall between bytes exceeding the configured idle timeout closes the connection. Long uploads and downloads that continue transferring bytes run without a total-duration cap at the HTTP/1 connection layer.

Before this repair, the first class did not take effect: the connection-layer wrapper replaced the socket deadline with `now + idle + 250 ms` before every partial read, overwriting whatever absolute deadline `net/http` had set — so a slow reader could hold a connection open indefinitely by sending one byte per idle window.

## Two Independent Defects {#root-cause}

1. **The connection wrapper overwrote the absolute deadline.** The `DeadlineConn` wrapper's read path reset the socket deadline on every partial read, defeating the read-header deadline Go's server sets. The direct-TCP baseline proved this in isolation: with a 100 ms header limit and a 2 s idle window, a header finishing at 400 ms was accepted.
2. **The CLI setting never reached the server context.** The CLI accepted `--read-header-timeout` and `MINIO_READ_HEADER_TIMEOUT`, including default parsing, but the server-context builder copied `IdleTimeout` while omitting `ReadHeaderTimeout`, so the running server always saw zero. Fixing defect 1 alone left the server accepting slow headers; the second fix wires `ReadHeaderTimeout` alongside the `IdleTimeout` binding.

This went unnoticed because the flag's default (30 s) matches the idle timeout's default, and with the flag unwired `net/http` fell back to that same 30 s read timeout — making default configurations appear to match the documented setting.

## Configuration {#config}

- **Flag:** `--read-header-timeout` (`Hidden: true`, absent from ordinary CLI help)
- **Environment:** `MINIO_READ_HEADER_TIMEOUT`
- **Default:** 30 s (equal to the idle timeout default)
- Neither timeout has a **YAML configuration field**; the value binds once at startup in order of flag > environment > default.

| Setting | Effect |
| :-- | :-- |
| `header > 0` | Absolute cap on HTTP/1 header phases; participates in Go's TLS-handshake read window (including the HTTP/2 handshake) |
| `header = 0` (explicit) | Falls back to Go's rule: the read timeout (= idle timeout) applies; the CLI default is 30 s |
| `header < 0` | Disables the header-specific cap; positive read/write timeouts still bound TLS handshake reads, and positive `IdleTimeout` still bounds the keep-alive wait |
| `idle` shortened, `header` unset | Header phase uses its own 30 s default — the one combination looser than a naive expectation, while still enforcing a fixed absolute cap |

Setting a negative value reopens unbounded slow-header trickling and should not be used in production. An incomplete header cut off by the deadline closes the connection directly rather than guaranteeing an HTTP error response. The initial report came from @AEGEGE's scanner issue [#183](https://github.com/pgsty/silo/issues/183), and [PR #195](https://github.com/pgsty/silo/pull/195) was integrated through [PR #196](https://github.com/pgsty/silo/pull/196).

## Behavior Across Protocols {#protocols}

- **HTTP/1**: headers and keep-alive waits use absolute deadlines; the request body uses the rolling idle timeout. The connection-state hook composes with any caller hook.
- **TLS**: handshake *reads* take the minimum of the positive header deadline and the existing read/write timeouts, and a fresh header deadline begins once the handshake completes; handshake *writes* retain rolling timeout semantics.
- **HTTP/2**: unchanged. When `h2` is negotiated, phase switching is skipped; `h2` retains its native absolute per-stream read timeout, and `ReadHeaderTimeout` is not passed into the `h2` configuration.
- **Internode connections**: Linux internode dialing manages its own rolling timeouts, and grid-hijacked connections unwrap to the underlying TCP connection before phase switching applies.

## Rejected Alternatives {#rejected}

- **Clamp all future deadlines globally.** Go 1.27 sets a whole-request deadline in some paths; with the read timeout equal to the idle timeout, clamping globally would hard-cap entire HTTP/1 requests (header plus body) and abort large uploads.
- **Drop the read timeout and reinterpret zero as rolling idle.** Zero is `net/http`'s sentinel for "never time out" on background reads and hijacked connections; reinterpreting it would break long-running handlers and strip `h2` of its per-stream timeout.
- **Wrap the body reader or use `http.ResponseController`.** Accounting for chunked encoding, connection draining, EOF transitions, and `h2` special cases requires a much larger surface area than fixing the connection deadline wrapper.
- **Reconstruct the standard library's deadline arithmetic in the hook.** That would duplicate `net/http` internals that shift across Go releases; recording the deadline the standard library actually requested avoids version drift.
- **Infer the phase by comparing timeout durations.** Because all three defaults are 30 s, "shorter than the idle window" cannot distinguish header deadlines from idle timeouts under default production settings.

## Verification and Limits {#verification}

Unit tests verify the connection wrapper across three consecutive refresh intervals (confirming the absolute cap never slides forward on partial reads), phase transitions across HTTP/1 keep-alive, TLS, and HTTP/2-only negotiation, and flag/env binding on the CLI context; a live process probe with a 100 ms header limit rejected a 400 ms slow header while serving normal traffic. Scope notes: TLS handshake writes remain rolling; handler CPU and storage waits are not bounded by socket read deadlines; and the absolute header cap applies without slack whereas rolling idle refreshes retain their ~250 ms slack window.

Upgrade notes (reducing the header timeout also narrows the TLS handshake read window) are documented in the [component matrix](/compatibility/versions/#september-reliability).

Related records: [tags](/blog/design/replicated-tag-ordering/) · [metadata](/blog/design/replica-metadata-normalization/) · [HTTP](/blog/design/request-header-timeouts/) · [audit](/operations/replication/replica-metadata-audit/)
