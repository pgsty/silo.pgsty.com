---
title: "SN-2026-018: Client Source Address Trust, Forwarded Headers, and aws:SourceIp"
linkTitle: "SN-2026-018: Source Address Trust"
date: 2026-08-04
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "Why _MINIO_API_XFF_HEADER=off still trusted X-Real-IP and Forwarded, why a naive reverse-proxy setup is not enough, and how MINIO_API_TRUSTED_PROXIES fixes source IP attribution (SN-2026-018)."
url: "/blog/security/source-address-trust/"
tags: ["Security", "IAM", "Network", "Reverse Proxy", "aws:SourceIp", "Audit", "SILO"]
---

**`SN-2026-018`** addresses client source-IP spoofing across `aws:SourceIp` IAM conditions, audit logs, bucket notification events, and admin HTTP traces in [silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) (`62f326d`) and [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`00a8171cb`, [`pgsty/silo#41`](https://github.com/pgsty/silo/issues/41)): `handlers.GetSourceIP` previously trusted `X-Forwarded-For`, `X-Real-IP`, and RFC 7239 `Forwarded` from any TCP peer by default, and setting `_MINIO_API_XFF_HEADER=off` only disabled `X-Forwarded-For` while continuing to trust client-supplied `X-Real-IP` and `Forwarded` headers.

## Conclusions first {#summary}

1. **`_MINIO_API_XFF_HEADER=off` left two headers wide open**: Setting `_MINIO_API_XFF_HEADER=off` skipped `X-Forwarded-For`, but `handlers.GetSourceIP` immediately fell through to `X-Real-IP` and `Forwarded`. Any direct client could forge `X-Real-IP: 10.0.0.1` to satisfy `aws:SourceIp` policies.
2. **"Put a reverse proxy in front" is often insufficient**: Even behind an ingress proxy, if the proxy appends to `X-Forwarded-For` (`proxy_add_x_forwarded_for`) while the server reads the left-most IP, or if internal pods can reach the server's ClusterIP directly, an attacker can still spoof `aws:SourceIp`.
3. **`MINIO_API_TRUSTED_PROXIES` provides explicit right-to-left chain verification**: [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) introduces `MINIO_API_TRUSTED_PROXIES` (`off` / `none`, CIDR/IP list, or `all` / `*` for legacy behavior) and walks `X-Forwarded-For` / `Forwarded` from right to left, stopping at the first hop not in the trusted proxy set.

---

## Every Consumer of `handlers.GetSourceIP` {#consumers}

In SILO, `handlers.GetSourceIP(r)` (`silo-pkg/handlers/proxy.go`) is the single function responsible for extracting the client IP address from an incoming `*http.Request`. Four security- and observability-sensitive subsystems depend on its return value:

| Consumer | Location | Security / Operational Role |
|---|---|---|
| `aws:SourceIp` IAM condition | `cmd/signature-v4-utils.go` (`getConditionValues`) | Evaluates `IpAddress` and `NotIpAddress` policy conditions on bucket and IAM policies. |
| Audit logging (`remotehost`) | `cmd/logger/audit.go` | Records the client IP in structured compliance audit logs. |
| Bucket notification events (`Host`) | `cmd/notification.go` | Populates `requestParameters.sourceIPAddress` in S3 event notifications. |
| Admin HTTP trace (`mc admin trace`) | `cmd/http-tracer.go` | Displays the client IP in live diagnostic traces. |

 Note that `handlers.GetSourceIPRaw` returned the first matched header token without validating whether it was even a syntactically valid IP address (a unit test in upstream `silo-pkg` literally asserted that `X-Forwarded-For: _gazonk` returned `"_gazonk"`!). While `IpAddress` condition evaluation parses the string with `net.ParseIP`, audit logs and notification payloads received the raw string.

---

## Why `_MINIO_API_XFF_HEADER=off` Did Not Stop Spoofing {#the-switch}

In `silo-pkg/handlers/proxy.go`, `GetSourceIPRaw` inspected three groups of headers in order:

```go
var xffHeaders = []string{"X-Forwarded-For", "x-forwarded-for"}
var realIPHeaders = []string{"X-Real-IP", "x-real-ip"}
var forwardedHeaders = []string{"Forwarded", "forwarded"}
```

When PR [`minio/minio#20977`](https://github.com/minio/minio/pull/20977) (and `minio/pkg#306`) added `_MINIO_API_XFF_HEADER=off` in February 2025, it gated **only** the `xffHeaders` loop:
- With `_MINIO_API_XFF_HEADER=off`, `GetSourceIPRaw` skipped `X-Forwarded-For`,
- Then immediately checked `X-Real-IP` (`realIPHeaders`) and `Forwarded` (`forwardedHeaders`) unconditionally!

Thus, an operator who set `_MINIO_API_XFF_HEADER=off` specifically to prevent `aws:SourceIp` spoofing on a directly exposed SILO endpoint remained completely vulnerable to `curl -H "X-Real-IP: 192.0.2.10"` or `curl -H "Forwarded: for=192.0.2.10"`.

### Upstream History since 2017 {#upstream-history}

This area had a long back-and-forth history:
- **2017-07 ([`minio/minio#4736`](https://github.com/minio/minio/pull/4736))**: Upstream briefly removed `X-Forwarded-For` from `GetSourceIP` after recognizing that clients could spoof `aws:SourceIp`.
- **Subsequent refactors**: Reverse-proxy deployments complained that `aws:SourceIp` and audit logs only saw the load balancer's IP, so `X-Forwarded-For`, `X-Real-IP`, and `Forwarded` were re-admitted—taking the **first** (left-most) comma-separated entry in `X-Forwarded-For`.
- **2023-08 ([`minio/minio#17878`](https://github.com/minio/minio/discussions/17878)) & 2025-02 ([`minio/minio#20977`](https://github.com/minio/minio/pull/20977))**: Operators requested a way to disable `X-Forwarded-For` trust, resulting in `_MINIO_API_XFF_HEADER`, which left `X-Real-IP` and `Forwarded` active.

---

## Why "Just Put a Reverse Proxy in Front" Is Not Enough {#proxy-is-not-enough}

A common misconception is that forwarded-header spoofing only matters when SILO is exposed directly to the internet without a reverse proxy. In practice, two standard production topologies remain vulnerable even when a reverse proxy is present:

1. **Left-most `X-Forwarded-For` vs. proxy append (`proxy_add_x_forwarded_for`)**: Standard nginx configurations use `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`, which **appends** the client's real IP to whatever `X-Forwarded-For` header the client sent. If the client sends `X-Forwarded-For: 10.0.0.5`, nginx forwards `X-Forwarded-For: 10.0.0.5, 203.0.113.99`. Because legacy `GetSourceIP` unconditionally took the **first** (left-most) address (`10.0.0.5`), the attacker's spoofed IP won even behind nginx!
2. **Coexisting ingress and direct paths (Kubernetes ClusterIP)**: In Kubernetes, external traffic arrives through an Ingress controller, while in-cluster workloads connect to the `silo` Service (`ClusterIP`) directly. If `GetSourceIP` blindly trusts forwarded headers whenever an Ingress exists, any pod inside the cluster can connect to the `ClusterIP` directly and forge `X-Forwarded-For` or `X-Real-IP` to impersonate a trusted subnet.

---

## Design of `MINIO_API_TRUSTED_PROXIES` {#design}

To solve both problems cleanly, `silo-pkg v3.12.0` (`62f326d`) and Server `20260804` (`00a8171cb`) introduce `MINIO_API_TRUSTED_PROXIES`:

| Setting | Peer Trust | Header Evaluation |
|---|---|---|
| `MINIO_API_TRUSTED_PROXIES=off` (or `none`) | Trust **no** proxy hops | Always uses the direct TCP peer (`r.RemoteAddr`) for external peers; ignores `X-Forwarded-For`, `X-Real-IP`, and `Forwarded`. |
| `MINIO_API_TRUSTED_PROXIES=10.0.1.0/24,192.168.1.10` | Trust only listed IPs/CIDRs | If `r.RemoteAddr` is not in the trusted set, returns `r.RemoteAddr` immediately. If `r.RemoteAddr` is trusted, walks `X-Forwarded-For` (or `Forwarded`) **from right to left** and returns the first IP not in the trusted set. |
| Unset, `all`, or `*` | Legacy compatibility mode | Preserves pre-`20260804` behavior (unless `_MINIO_API_XFF_HEADER=off` is set). |

Note that `handlers.GetSourceScheme` (`X-Forwarded-Proto`) is intentionally left untouched so TLS redirect and presigned URL scheme detection behind reverse proxies continue to work regardless of `MINIO_API_TRUSTED_PROXIES`.

---

## Seven Engineering Trade-Offs {#tradeoffs}

### 1. Default Compatibility vs. Secure-by-Configuration {#tradeoff-default}

Changing the unset default to `off` in a minor release would immediately break every reverse-proxy deployment that uses `aws:SourceIp` policies without having set `MINIO_API_TRUSTED_PROXIES`. We kept the unset default compatible and made `MINIO_API_TRUSTED_PROXIES=off` and CIDR lists first-class, documented controls.

### 2. Why We Reversed Widening `_MINIO_API_XFF_HEADER=off` {#tradeoff-widen}

In our first draft, we widened `_MINIO_API_XFF_HEADER=off` so that it also disabled `X-Real-IP` and `Forwarded`. Running the server test suite immediately failed `TestXFFDisabled` in `cmd/generic-handlers_test.go`!

Inspecting `TestXFFDisabled` showed why: the test specifically modelled an nginx reverse proxy that overwrites `X-Real-IP: $remote_addr` (trusted single IP) while appending to `X-Forwarded-For: $proxy_add_x_forwarded_for` (untrusted left-most IP). Operators who set `_MINIO_API_XFF_HEADER=off` in that exact topology relied on SILO ignoring `X-Forwarded-For` **so that it would fall through to `X-Real-IP`**. We therefore preserved `_MINIO_API_XFF_HEADER=off` semantics for `TestXFFDisabled` when `MINIO_API_TRUSTED_PROXIES` is unset, and provided `MINIO_API_TRUSTED_PROXIES=off` to disable **all** forwarded IP headers (`X-Forwarded-For`, `X-Real-IP`, and `Forwarded`).

### 3. Why `MINIO_API_TRUSTED_PROXIES` Is Env-Only (No `mc admin config` Key) {#tradeoff-config}

In SILO's startup sequence, the HTTP listener and initial request routing come up before the distributed `api` subsystem configuration is loaded from erasure storage. If trusted proxies were configured via `mc admin config set api`, there would be a startup window before config load where `GetSourceIP` either failed open or failed closed, and updating the setting at runtime would require atomic reloads across `silo-pkg`. Making `MINIO_API_TRUSTED_PROXIES` an environment variable configured before listener startup eliminates any race window.

### 4. Loopback Exemption: Peer vs. Chain Hop {#tradeoff-loopback}

SILO's built-in FTP and SFTP servers (`cmd/ftp-server.go`, `cmd/sftp-server.go`) and local inter-node forwarding connect to the S3 layer over loopback (`127.0.0.1` / `::1`) and pass the external client's IP in `X-Forwarded-For`. Therefore, when the **immediate TCP peer** (`r.RemoteAddr`) is loopback, SILO treats that local peer hop as trusted so FTP/SFTP audit logs and `aws:SourceIp` continue to see the real FTP/SFTP client IP.

Crucially, however, loopback is **not** implicitly trusted as an intermediate hop inside the `X-Forwarded-For` header chain! Otherwise, an external client behind one trusted proxy could send `X-Forwarded-For: 10.0.0.1, 127.0.0.1`, causing the right-to-left walker to skip the proxy (`r.RemoteAddr`), skip `127.0.0.1` in the header, and trust the attacker's `10.0.0.1`.

### 5. Header Precedence: `X-Forwarded-For` Before `X-Real-IP` {#tradeoff-precedence}

When `MINIO_API_TRUSTED_PROXIES` is configured with a CIDR/IP list, `GetSourceIP` evaluates `X-Forwarded-For` (right-to-left), then `X-Real-IP` (validated with `parseIP`), then `Forwarded` (right-to-left). Note that this differs intentionally from `getSTSLDAPTrustedProxySourceIP` (`cmd/sts-handlers.go`), which checks `X-Real-IP` first for single-hop LDAP STS proxies; in general multi-hop S3 proxy chains, `X-Forwarded-For` carries the hop-by-hop chain needed for right-to-left verification while `X-Real-IP` may remain frozen at an outer hop.

### 6. Broad CIDR Warning {#tradeoff-breadth}

If an operator sets `MINIO_API_TRUSTED_PROXIES=10.0.0.0/8` when ordinary application pods also run in `10.0.0.0/8`, any pod in that `/8` is treated as a trusted proxy and can forge `X-Forwarded-For`. Operators should list only the dedicated ingress/load-balancer IPs or subnet.

### 7. Multi-Node Distributed Clusters {#tradeoff-multinode}

In a multi-node SILO cluster (`silo server http://node{1..4}/data`), a load balancer may route a client request to Node 1, which internally proxies or forwards sub-requests to Nodes 2–4:

| Topology | What `MINIO_API_TRUSTED_PROXIES` Must Include |
|---|---|
| Single node behind reverse proxy | Reverse proxy IPs/CIDRs only |
| Multi-node cluster behind reverse proxy | Reverse proxy IPs/CIDRs **and** all SILO cluster node IPs/CIDRs |
| Direct client access to multi-node cluster (no external proxy) | All SILO cluster node IPs/CIDRs (or `off` if clients always hit nodes directly without peer forwarding) |

---

## Compatibility Details {#compatibility}

- **No non-IP garbage returned in trusted-proxy mode**: When `MINIO_API_TRUSTED_PROXIES` is active (`off` or CIDR list), every candidate header token is validated as a real IP address; malformed tokens like `_gazonk` are rejected rather than returned to callers.
- **Removal of unreachable IPv4-mapped prefix string hack**: Legacy `proxy.go` contained a string check for `"::ffff:"` that was unreachable or mishandled hex forms; `netip.Addr.Unmap()` now normalizes IPv4-mapped IPv6 addresses (`::ffff:192.0.2.1` -> `192.0.2.1`) cleanly.

---

## Bugs Caught During Multi-Pass Code Review {#review}

Iterative code review of the patch across `silo-pkg` and `silo` caught nine subtle edge cases before release:

### Second-Pass Review Findings {#review-round-two}

1. **`init()` vs. `MINIO_CONFIG_ENV_FILE` startup ordering**: Reading `MINIO_API_TRUSTED_PROXIES` and `_MINIO_API_XFF_HEADER` only inside a package `init()` function meant values loaded later from `MINIO_CONFIG_ENV_FILE` in `serverHandleEnvVars` were ignored! Server `20260804` explicitly re-applies both settings in `serverHandleEnvVars`.
2. **Loopback in-chain spoofing (`X-Forwarded-For: spoofed, 127.0.0.1`)**: Caught the distinction between trusting a loopback `r.RemoteAddr` peer vs. trusting `127.0.0.1` inside an `X-Forwarded-For` header list (fixed as described in [Trade-Off 4](#tradeoff-loopback)).
3. **IPv6 zone identifiers (`fe80::1%eth0`)**: Link-local IPv6 peers include a `%zone` suffix in `r.RemoteAddr`. Using `netip.ParseAddr` and stripping the zone before CIDR matching prevents link-local peers from failing IP parsing.
4. **Multiple `X-Forwarded-For` header lines (`r.Header.Values`)**: HTTP proxies such as HAProxy or Envoy may append a second `X-Forwarded-For` header line rather than comma-joining onto the first line. Calling `r.Header.Get("X-Forwarded-For")` read only the first (client-controlled!) header line. We switched to iterating `r.Header.Values("X-Forwarded-For")` from last header line to first.
5. **Internal `forwarder.go` header hygiene**: When `MINIO_API_TRUSTED_PROXIES` rejected an untrusted peer's `X-Real-IP` or `Forwarded` header, internal HTTP forwarding needed to avoid re-injecting untrusted headers alongside a trusted peer hop.
6. **`::ffff:0:0/96` CIDR unmapping**: Unmapping the prefix address of `::ffff:0:0/96` without checking prefix length would turn a `/96` IPv6 prefix into `0.0.0.0` and match all IPv4 addresses; we preserve CIDR prefix semantics accurately.

### Third-Pass Review Findings {#review-round-three}

7. **Fail-closed on empty CIDR list (`MINIO_API_TRUSTED_PROXIES=","`)**: If an operator sets `MINIO_API_TRUSTED_PROXIES=","` (or whitespace-only), silently treating the empty slice as "unset (trust all)" would fail open! Startup now returns an explicit configuration error if `MINIO_API_TRUSTED_PROXIES` is set to an empty or unparseable value.
8. **`os.LookupEnv` vs. `env.Get("")`**: Using `env.Get(EnvAPITrustedProxies, "")` could not distinguish between `MINIO_API_TRUSTED_PROXIES` being unset and being set to `""`; we check explicit presence so empty settings fail closed.
9. **Zero-allocation backwards scan and 100-hop cap**: Allocating `strings.Split(header, ",")` on every request allowed a client sending a 1 MB `X-Forwarded-For` header full of commas to trigger a ~33 MB slice allocation per request. We replaced `strings.Split` with an in-place right-to-left scanner and capped inspection at 100 hops.

---

## Operator Recommendations {#recommendations}

- **Direct-attached SILO (no reverse proxy)**: Set `MINIO_API_TRUSTED_PROXIES=off`.
- **SILO behind nginx / HAProxy / Envoy / Ingress**: Set `MINIO_API_TRUSTED_PROXIES` to the CIDR or IP list of the reverse proxies (and SILO node IPs in a multi-node cluster).

---

## Out of Scope {#not-done}

- **PROXY protocol v1/v2**: TCP-layer PROXY protocol support at the listener is separate from HTTP `X-Forwarded-For` / `Forwarded` parsing.
- **`GetSourceScheme`**: Left unchanged so HTTPS scheme detection behind TLS-terminating proxies continues to work independently of `MINIO_API_TRUSTED_PROXIES`.
- **`ExistingObjectTag/*` condition isolation**: Fixed separately in `2f55347f7` (also shipped in `20260804`) so only stored object tags—never client request headers—populate `ExistingObjectTag/*` conditions.

## Severity Classification {#severity}

Tracked as **`SN-2026-018`** in the SILO advisory ledger (as with [CVE-2026-42600](/blog/security/cve-2026-42600/), `minio/minio` is archived; severity is Moderate-to-High depending on whether policies rely on `aws:SourceIp`). Upgrading to [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) and setting `MINIO_API_TRUSTED_PROXIES` closes the spoofing vector across IAM, audit logs, notifications, and traces.
