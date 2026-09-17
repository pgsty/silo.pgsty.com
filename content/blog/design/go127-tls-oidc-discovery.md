---
title: "Go 1.27 TLS Defaults and OIDC Discovery Failure Modes"
linkTitle: "Go 1.27 TLS and OIDC"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  What the Go 1.27 toolchain move changed at the TLS layer, how to diagnose an
  OIDC discovery failure by phase, and which health endpoint actually reports
  an offline identity provider. Written from the investigation of issue #154:
  mechanisms verified by synthetic experiments, with the customer-side root
  cause explicitly left unconfirmed.
tags: [Design, TLS, OIDC, Operations]
weight: 11
draft: false
url: "/blog/design/go127-tls-oidc-discovery/"
---

> **Publication update, 2026-09-17:** The Go TLS default repair (`48e184652`) shipped in [Server 20260916](/blog/release/silo-20260916/). Coordinated upgrades, opt-in prerequisites and remaining limitations still apply. Dated source-status and validation records below retain their original scope.

> **Follow-up, 2026-09-17:** the #154 reporter retested on 20260916 and reports the same failure. The repair restores the effect of `GODEBUG=tlsmlkem=0`; it does not change the default handshake, and it cannot address an ingress that rejects the new ML-DSA signature identifiers. The mechanism analysis, the full option space and the release-communication gates that follow from this are recorded in [Pinned TLS Parameters and Handshake Compatibility](/blog/design/tls-parameter-pinning/).

After SILO's toolchain moved to Go 1.27, the Server TLS repair
[`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31)
("fix(tls): honor Go key exchange defaults across transports") removed its
explicit curve overrides. This page records the TLS changes and the diagnostic method for OIDC
discovery failures that came out of [issue #154](https://github.com/pgsty/silo/issues/154),
and the operational facts an administrator needs when identity goes missing
at startup.

> **Release boundary, 2026-09-16:** Server 20260903 already uses Go 1.27.1,
> but does **not** contain `48e184652`. That later TLS repair is on main;
> upgrading the compiler and adopting this repair are separate changes.

> **Evidence class, stated up front.** Every mechanism below is verified by
> synthetic experiments: ClientHello captures, fresh-process CA probes, and
> fixture reproductions. The #154 customer's discovery URL and ingress
> configuration were never obtained, so **no root cause is claimed for that
> deployment** — two locally verified mechanisms could each produce the
> reported symptom, and either the ingress rejecting the new handshake, or a
> proxy rejecting the changed User-Agent, remains plausible. #154 was closed on
> 2026-09-11 on the strength of the merge; the 2026-09-17 retest on 20260916
> still fails, so an affected-environment retest with phase-level evidence is
> still owed.

## What Go 1.27 changed {#go127}

- **Explicit curve preferences now override the ML-KEM compat switches.**
  `GODEBUG=tlsmlkem=0` removes all ML-KEM hybrids from the default set; `tlssecpmlkem=0` removes only the P-256/P-384 hybrids introduced in Go 1.26 and retains X25519MLKEM768. An application that configures
  `CurvePreferences` explicitly keeps ML-KEM in whatever list it names — a
  deliberate Go 1.27 change. SILO had eight TLS configuration points setting
  an explicit list including X25519MLKEM768; the fix removes all eight
  assignments and retires the helper, so these Server configuration points
  follow Go's defaults and the compat switches work again. The stack review
  found pkg, mcli, and Console clients already used defaults; Console's
  HTTPS listener retains its separate P-256-only policy.
- **ClientHello now offers ML-DSA signature algorithms** (identifiers
  `0x0904`–`0x0906`). ML-DSA is a signature scheme and distinct from ML-KEM:
  disabling hybrid key exchange does not disable the ML-DSA offer, and an
  ingress that rejects ML-DSA is not fixed by any ML-KEM switch.
- **The ClientHello grew.** Measured on the same source and dependencies:
  Go 1.26.5 default 1497 bytes; Go 1.27.1 default 1509 bytes; the old
  explicit list under `tlsmlkem=0` produced a 275-byte hello with no ML-KEM,
  while Go 1.27.1 with an explicit list still produced 1509 bytes containing
  ML-KEM. Rebuilding with a different compiler alone changed the handshake.
- **macOS root-CA behavior flips with the module's Go directive.** A fresh
  process honoring `SSL_CERT_FILE`/`SSL_CERT_DIR` instead of the Keychain is
  governed by the `x509sslcertoverrideplatform` GODEBUG default, which
  follows the main module's `go` directive: `go 1.26` modules ignore those
  variables on macOS (platform store wins), `go 1.27` modules honor them —
  and the consuming *application's* directive wins even when a library
  module is older. Operators on macOS should know that setting either
  variable replaces Keychain trust wholesale with the file/directory given;
  a stale or incomplete path then breaks chains the Keychain would have
  accepted, and unsetting restores the Keychain.
- **Not everything changed.** TLS versions, cipher suites, certificate and
  hostname verification, proxy handling, and HTTP/2 selection are unaffected.
  The standard-library drain cap (256 KiB / 50 ms) and other audited Go 1.27
  changes showed no SILO dependency. Go 1.27 binaries require macOS 13 or
  newer. Downgrading is not a supported path: the module graph requires
  Go ≥ 1.27.1 across Server, Console, and mc.

## Why the OIDC-only patch was withdrawn {#patch}

The investigation first produced a minimal candidate: clear
`CurvePreferences` on the OIDC discovery transport only. It was deliberately
**not** shipped. The same transport serves identity plugins, notification and
lambda reachability checks, audit webhooks, and S3 cloud-backend tiers —
fixing two OIDC call sites would have left every other consumer on the
defective explicit list. The merged repair removes the explicit curves at all
eight Server configuration points so the compat switches apply there, keeps
certificate verification strict, and adds no protocol downgrade or automatic
fallback. The archived one-transport patch must not be reapplied on top of
the merged fix.

## Diagnosing a discovery failure by phase {#diagnostics}

The startup chain is: server start → identity system init → fetch
`.well-known/openid-configuration` (discovery) → fetch the `jwks_uri` keys →
IAM store ready → Console initializes. Console's own OIDC configuration
dialog validates through the same server-side transport. A failure anywhere
in the chain leaves IAM offline; a *successful discovery* does not clear the
JWKS fetch, and a 503 on JWKS blocks IAM just as hard.

Discriminate by where the connection dies:

- **Reset right after the TLS ClientHello** (`tls_start` then reset): suspect
  the ingress's ClientHello handling — proxy CONNECT rules, TLS terminators,
  or anything keyed on hello size or contents. This is where the Go 1.27
  changes land.
- **Reset after TLS completes** (`wrote_request` then reset): the TLS layer
  is fine; look at HTTP-layer policy — WAF rules, User-Agent allowlists (the
  server's UA changed from `MinIO` to `Silo` with the rebrand), routing.
  Replacing certificates or key exchange here has no targeted effect.
- **x509 errors**: compare the chain actually received, the SNI, and the
  trust store the process resolves (see the macOS section above).
- Always test from the same network position as the failing process — a
  fresh container does not inherit the failing container's network namespace,
  and same-IP/same-proxy controls come first.

## The health endpoint that tells the truth {#health}

`/minio/health/live` and `/minio/health/ready` **both stay 200 while IAM is
offline** — readiness as deployed does not cover the identity system. The
endpoint that reports it is `/minio/health/cluster`, which checks identity
initialization and returns 503 with the `X-Minio-Server-Status: iam-offline`
marker. Monitoring that should catch a broken IdP integration should probe
the cluster health, plus one authenticated operation.

Recovery is automatic: identity initialization retries at randomized 0–3 s
intervals, and a recovered IdP brings IAM back without a restart (observed
sub-second to ~1.4 s locally). Retrying cannot fix a persistent
incompatibility — a hello the ingress rejects stays rejected.

## Transport facts worth knowing {#transport}

The discovery/JWKS client builds its own transport: HTTP/2 disabled (no ALPN,
HTTP/1.1), proxies taken only from `HTTPS_PROXY`/`NO_PROXY` (uppercase
preferred; `ALL_PROXY` unused), DNS refresh defaulting to 30 s in Kubernetes/Docker and 10 min otherwise (overridable by the DNS cache TTL setting), dialing that walks
addresses in order without shuffling, and timeouts of 5 s per TCP dial,
10 s for the TLS handshake, and 1 min to response headers. There is **no
total timeout on the discovery or JWKS fetch itself** — a slow IdP can hold
startup indefinitely; tightening that is a known, separately-sized follow-up.

## Attribution {#attribution}

This record distills the issue #154 investigation and the September Go 1.27
stack review; the reproduction
artifacts and the full evidence chain are retained outside the documentation
tree. The supported statement is: the merged fix restores Go key-exchange
defaults at the eight affected Server configuration points, verified with synthetic negative
controls — it does not claim to have diagnosed any specific hidden
deployment, and no root cause is established for #154 until a retest in the
affected environment supplies phase-level evidence.

Go behavior is grounded in the [official 1.27 release notes](https://go.dev/doc/go1.27) and the actual toolchain. ClientHello byte counts above describe the recorded fixtures, not a fixed size for every connection.
