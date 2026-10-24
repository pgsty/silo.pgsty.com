---
title: "Go 1.27 TLS Defaults and OIDC Discovery Failure Modes"
linkTitle: "Go 1.27 TLS and OIDC"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  What the Go 1.27 toolchain upgrade changed at the TLS layer, how to diagnose
  OIDC discovery failures by connection phase, and which health endpoint
  reports an offline identity provider. Distilled from the investigation of
  issue #154 and verified with synthetic experiments.
tags: [Design, TLS, OIDC, Operations]
weight: 11
draft: false
url: "/blog/design/go127-tls-oidc-discovery/"
---

After SILO's toolchain moved to Go 1.27, the Server TLS repair [`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31) ("fix(tls): honor Go key exchange defaults across transports", shipped in [Server 20260916](/blog/release/silo-20260916/)) removed explicit curve overrides across eight Server TLS configuration points. This article records the Go 1.27 TLS changes, the phase-based diagnostic method for OIDC discovery failures developed during the investigation of [issue #154](https://github.com/pgsty/silo/issues/154), and the health-endpoint behavior when an identity provider is unreachable at startup.

For the post-release retest analysis — why `GODEBUG=tlsmlkem=0` disables hybrid key exchange but does not suppress the 12-byte `ML-DSA` signature algorithm offer, and the configuration options for TLS-inspecting middleboxes — see [Pinned TLS Parameters and Handshake Compatibility](/blog/design/tls-parameter-pinning/).

## What Go 1.27 Changed {#go127}

- **Explicit `CurvePreferences` now override the ML-KEM compatibility switches.** `GODEBUG=tlsmlkem=0` removes all ML-KEM hybrids from the default curve set; `tlssecpmlkem=0` removes only the P-256/P-384 hybrids introduced in Go 1.26 while retaining `X25519MLKEM768`. In Go 1.27, any application that sets `CurvePreferences` explicitly retains ML-KEM in that list regardless of the `GODEBUG` switches. SILO Server had eight TLS configuration points setting an explicit list that included `X25519MLKEM768`; commit `48e184652` removes all eight assignments and retires the helper so those configuration points use Go's default curve set and honor the `GODEBUG` switches. Stack-wide review confirmed that `silo-pkg`, `mcli`, and Console clients already used the standard library defaults, while Console's HTTPS listener retains its separate P-256-only policy.
- **`ClientHello` now advertises ML-DSA signature algorithms** (code points `0x0904`–`0x0906`). Because ML-DSA is a signature scheme rather than a key-exchange mechanism, disabling hybrid key exchange leaves the ML-DSA offer intact, and middleboxes that reject unknown signature-algorithm code points are unaffected by ML-KEM switches.
- **`ClientHello` size increased.** Measured on identical source and dependencies: Go 1.26.5 defaults produce a 1497-byte `ClientHello`; Go 1.27.1 defaults produce 1509 bytes; under `tlsmlkem=0`, the old explicit curve list produced a 275-byte `ClientHello` without ML-KEM on Go 1.26.5, whereas Go 1.27.1 with that same explicit list still produced a 1509-byte `ClientHello` containing ML-KEM. Upgrading the compiler alone altered the outbound handshake payload.
- **macOS root-CA resolution follows the main module's `go` directive.** Whether a process honors `SSL_CERT_FILE`/`SSL_CERT_DIR` or queries the macOS Keychain is controlled by the `x509sslcertoverrideplatform` GODEBUG setting, whose default tracks the top-level main module's `go` directive: `go 1.26` main modules ignore both variables on macOS in favor of the platform Keychain, whereas `go 1.27` main modules honor them (regardless of older `go` directives in library dependencies). On macOS, setting either environment variable replaces Keychain trust entirely with the specified file or directory; if that path points to a stale or incomplete bundle, certificate chains that the Keychain would have trusted fail verification until the variable is unset.
- **Unchanged TLS and platform baselines.** TLS protocol versions, cipher suites, certificate and hostname verification, proxy resolution, and HTTP/2 negotiation remain unchanged, and audited Go 1.27 runtime changes such as the standard-library response-body drain cap (256 KiB / 50 ms) do not affect SILO. Go 1.27 binaries require macOS 13 or later, and the module graph across Server, Console, and `mc` requires Go ≥ 1.27.1.

## Why the OIDC-Only Patch Was Withdrawn {#patch}

An initial candidate patch cleared `CurvePreferences` only on the OIDC discovery transport. We discarded that approach because the same transport constructor backs identity plugins, notification and Lambda reachability probes, audit webhooks, and S3 cloud-storage tiering — patching only the two OIDC call sites would have left every other outbound TLS consumer on the hardcoded curve list. The merged fix removes the explicit curve overrides across all eight Server TLS configuration points while keeping certificate verification strict and avoiding protocol downgrades or silent fallbacks.

## Diagnosing a Discovery Failure by Phase {#diagnostics}

The startup sequence runs: server start → identity subsystem initialization → fetch `.well-known/openid-configuration` (discovery) → fetch `jwks_uri` keys → IAM store ready → Console initialization. Console's OIDC configuration dialog validates through the same server-side transport. A failure at any step leaves IAM offline; even if the discovery document loads, a `503` or timeout when fetching `jwks_uri` still prevents IAM from coming online.

Isolate the failure by the phase where the connection terminates:

- **TCP reset immediately after `ClientHello`** (reset right after `tls_start`): inspect ingress or middlebox handling of the `ClientHello` packet — proxy `CONNECT` policies, TLS terminators, or middleboxes filtering on packet size or extension code points. All Go 1.27 handshake changes surface at this step.
- **Reset or error after the TLS handshake completes** (reset after `wrote_request`): the TLS handshake succeeded; check HTTP-layer policies such as WAF rules, `User-Agent` allowlists (the server's default User-Agent changed from `MinIO` to `Silo`), and layer-7 routing. Changing certificates or key-exchange settings will not affect failures at this stage.
- **x509 verification errors**: inspect the certificate chain returned by the peer, the SNI server name sent, and the trust store selected by the process (on macOS, check whether `SSL_CERT_FILE` or `SSL_CERT_DIR` is overriding the Keychain).
- Run diagnostic probes from the exact network namespace and egress path of the failing process, matching source IP and proxy settings.

## Health Endpoints and IAM Status {#health}

While IAM is offline, `/minio/health/live` and `/minio/health/ready` **both continue to return HTTP 200**, as neither probe gates on the identity subsystem. `/minio/health/cluster` checks identity initialization and returns `503 Service Unavailable` with the response header `X-Minio-Server-Status: iam-offline`. Monitoring designed to catch broken IdP integrations should probe `/minio/health/cluster` alongside an authenticated request.

Identity initialization retries automatically in the background at randomized 0–3 s intervals; once the IdP becomes reachable, IAM comes online without a process restart (measured at sub-second to ~1.4 s in local tests). Background retries only recover from transient reachability failures — a `ClientHello` rejected by a middlebox will fail on every retry until the TLS configuration or middlebox policy is updated.

## Discovery and JWKS Transport Parameters {#transport}

The OIDC discovery and JWKS client constructs a dedicated `http.Transport` with the following parameters: HTTP/2 disabled (no `h2` ALPN, HTTP/1.1 only); proxy settings read exclusively from `HTTPS_PROXY` and `NO_PROXY` (uppercase preferred; `ALL_PROXY` is ignored); DNS cache refresh defaulting to 30 s in Kubernetes/Docker environments and 10 min elsewhere (overridable via the DNS cache TTL setting); sequential address dialing without shuffling; and per-phase timeouts of 5 s per TCP dial, 10 s for the TLS handshake, and 1 min for response headers. **No overall request timeout is set on the discovery or JWKS fetch itself**, so a stalling IdP can hold startup initialization open indefinitely.

## Attribution {#attribution}

This note distills the [issue #154](https://github.com/pgsty/silo/issues/154) investigation and the September Go 1.27 stack review. Each behavior described above was verified with synthetic experiments (`ClientHello` packet captures, fresh-process root-CA probes, and local fixture reproductions) and cross-checked against the [Go 1.27 release notes](https://go.dev/doc/go1.27) and the `crypto/tls` and `crypto/x509` standard library implementations.
