---
title: "Pinned TLS Parameters and Handshake Compatibility"
linkTitle: "TLS Pinning and Handshakes"
date: 2026-09-17
lastmod: 2026-09-17
author: "Ruohang Feng"
summary: >
  Why Go 1.27 changed the TLS 1.3 ClientHello, how SILO's inherited explicit
  curve list prevented GODEBUG=tlsmlkem=0 from taking effect, what the 20260916
  repair covers, and the remediation options when a TLS-inspecting middlebox
  resets connections over new post-quantum identifiers.
tags: [Design, TLS, OIDC, Operations, Compatibility]
weight: 5
draft: false
url: "/blog/design/tls-parameter-pinning/"
---

After the Go TLS default repair [`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31) shipped in [Server 20260916](/blog/release/silo-20260916/), the reporter of [issue #154](https://github.com/pgsty/silo/issues/154) retested on that release and still saw `connection reset by peer` on OIDC discovery. Meanwhile, upstream Go issues reported the exact same symptom and traced it to TLS-inspecting middleboxes resetting connections over the `signature_algorithms_cert` extension (see [The Known Upstream Instance](#upstream)). This article extends [Go 1.27 TLS Defaults and OIDC Discovery Failure Modes](/blog/design/go127-tls-oidc-discovery/) with the post-release mechanism analysis, the scope of the 20260916 repair, the remediation options for affected deployments, and the resulting release and issue-closure gates.

## In Plain Terms {#plain}

A TLS connection opens with a **ClientHello** listing the algorithms the client supports. Many corporate networks place a middlebox in the path — a WAF, a TLS inspection appliance, or a load balancer — that parses that message. Some of those devices reset the connection when they encounter an unrecognized algorithm identifier.

Go 1.27 added three new identifiers to that message — the ML-DSA post-quantum signature schemes — for a total of **12 extra bytes**. Rebuilt on Go 1.27, SILO sends those extra 12 bytes in the TLS 1.3 ClientHello. A middlebox in front of the reporter's identity provider rejects the message and sends a TCP reset. `curl` from the same container succeeds because `curl` uses OpenSSL, which does not offer those identifiers.

Go provides a compatibility switch for hybrid key exchange, `GODEBUG=tlsmlkem=0`, which **only applies when the application has not specified its own curve list (`Config.CurvePreferences == nil`).** SILO carried an explicit curve list inherited from upstream that included a post-quantum entry, rendering `GODEBUG=tlsmlkem=0` ineffective. Commit [`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31) removes those explicit curve lists so `GODEBUG=tlsmlkem=0` works as designed.

However, **`GODEBUG=tlsmlkem=0` disables post-quantum key exchange (ML-KEM); it does not disable post-quantum signature algorithms (ML-DSA)**, and the 12 extra bytes added in Go 1.27 are ML-DSA identifiers. Go exposes no `GODEBUG` switch for ML-DSA. When a middlebox resets on the ML-DSA offer, removing `CurvePreferences` alone cannot suppress those 12 bytes — matching the retest result.

## What Go Is Actually Solving {#why-go}

**Post-quantum key exchange requires advance migration.** Under a harvest-now-decrypt-later threat model, an adversary records encrypted traffic today and decrypts it years later once a cryptographically relevant quantum computer exists. Confidentiality therefore has to migrate before such a machine exists. NIST finalized ML-KEM ([FIPS 203](https://csrc.nist.gov/pubs/fips/203/final)) and ML-DSA ([FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)) in 2024, and the deployed form is hybrid: `X25519MLKEM768` runs classical X25519 and ML-KEM together and combines both secrets, so a flaw in ML-KEM leaves the connection at least as strong as X25519 alone. Browsers, CDNs, and SSH implementations have enabled hybrid key exchange by default since 2024; Go followed in 1.24.

**Handshake signatures have a different migration timeline.** Because handshake signatures cannot be forged retroactively to break past sessions, ML-DSA in TLS 1.3 today simply advertises client support for ML-DSA certificates. Go 1.27 added `MLDSA44`, `MLDSA65`, and `MLDSA87` to the default signature algorithm list, which accounts for the 12 extra bytes:

```go
// crypto/tls/defaults.go, Go 1.27.1
func defaultSupportedSignatureAlgorithms() []SignatureScheme {
    return []SignatureScheme{
        MLDSA44,        // 0x0904
        MLDSA65,        // 0x0905
        MLDSA87,        // 0x0906
        PSSWithSHA256,
        ECDSAWithP256AndSHA256,
        ...
```

Those identifiers are defined for TLS 1.3 only. `isDisabledSignatureAlgorithm` drops them when the configuration cannot reach TLS 1.3, which — as noted below — is the only lever an application has over them.

## The Switch That Was Never Meant to Cover Explicit Lists {#contract}

The change that exposed SILO's pinned curve list is documented in the [Go 1.27 release notes](https://go.dev/doc/go1.27):

> Post-quantum hybrid key exchanges can now be explicitly enabled in `Config.CurvePreferences` even if the `tlsmlkem=0` or `tlssecpmlkem=0` GODEBUG options are used. **Those options were always meant to only apply to the default set used when `Config.CurvePreferences` is nil.**

The standard library has documented the two paths as alternatives since Go 1.24:

```go
// CurvePreferences ... If empty, the default will be used.
//
// From Go 1.24, the default includes the [X25519MLKEM768] hybrid
// post-quantum key exchange. To disable it, set CurvePreferences
// explicitly or use the GODEBUG=tlsmlkem=0 environment variable.
```

In code it is one branch: an explicit list is used verbatim; only the empty case consults the defaults, and the GODEBUG lives in the default path.

```go
// crypto/tls/common.go, Go 1.27.1
func (c *Config) supportsCurve(version uint16, x CurveID) bool {
    if c != nil && len(c.CurvePreferences) != 0 {
        if !slices.Contains(c.CurvePreferences, x) { return false }   // your list, verbatim
        ...
    } else {
        if !defaultCurveEnabled(x) { return false }                   // the GODEBUG lives here
    }
```

The principle is that **explicit configuration outranks an environment variable** — otherwise an operator could silently override a security policy the developer wrote in code. Go 1.26 and earlier filtered explicit lists through the GODEBUG as well; SILO's behavior on Go 1.26 was therefore relying on something Go considers to have been a bug.

Go also ties GODEBUG *defaults* to the main module's `go` directive, so a module that still declares an older version keeps the older behavior until it moves. SILO's `go.mod` declares `go 1.27.1`, which explicitly adopts the 1.27 behavior.

## Where SILO's Debt Was — and Where It Still Is {#debt}

The list in question was `{X25519MLKEM768, CurveP256, X25519, CurveP384, CurveP521}`, inherited from upstream and later extended with the post-quantum entry. Pinning it produced the worst of both worlds: the deployment could not benefit from the library's evolving defaults, **and** could not use the library's compatibility switch.

`48e184652` removes that assignment at all eight Server TLS configuration points — the general external HTTP transport, the replication transport, the client-certificate cloud transport, the internode transport, both grid links, etcd, and the inbound S3/Console listener — retires the `TLSCurveIDs` helper, and adds wire-level regression tests across five outbound constructors, two peer TLS versions, and both GODEBUG settings. Certificate and hostname verification, cipher-suite policy, proxy handling, and HTTP/2 selection are unchanged, and no post-failure downgrade or retry was introduced. The earlier OIDC-only candidate was withdrawn because the same transport also serves identity plugins, notification and Lambda reachability checks, audit webhooks, and S3 cloud tiers.

**The same debt remains one layer down.** Cipher suites are still pinned: `crypto.TLSCiphers()` and `crypto.TLSCiphersBackwardCompatible()` are assigned in the outbound transports, LDAP, etcd, the grid links, and the inbound listener. The listener at least has `MINIO_API_SECURE_CIPHERS` to choose between the two sets; **no outbound path has any switch at all**.

The general rule this design establishes: **set `MinVersion` and leave the rest to the standard library.** Where an incompatible endpoint genuinely requires a narrower profile, expose it as product configuration that is visible in `mcli admin config` and in a support bundle — never as a value pinned in source. Protocol ossification is an old problem: TLS 1.3 had to disguise itself as TLS 1.2 on the wire, and GREASE exists precisely to force middleboxes to tolerate identifiers they do not know.

## What Is Actually Different on the Wire {#wire}

Measured against the same synthetic IdP fixture, with default settings:

| Build | ClientHello | ML-KEM (4588) | ML-DSA 0x0904-6 | User-Agent |
| --- | ---: | --- | --- | --- |
| 20260804, Go 1.26.5 — works | 1497 B | present | absent | `MinIO (…)` |
| 20260903, Go 1.27.1 — fails | 1509 B | present | present | `Silo (…)` |
| 20260916, Go 1.27.1 — repaired | 1509 B | present (default) | present | `Silo (…)` |
| 20260804 with `tlsmlkem=0` | 275 B | absent | absent | `MinIO (…)` |
| 20260903 with `tlsmlkem=0` | 1509 B | **still present** | present | `Silo (…)` |

Two readings matter and are easy to miss:

- **ML-KEM was already being offered by the working release.** Unless the operator had set `tlsmlkem=0` *before* the upgrade, ML-KEM is not a variable between the working and failing versions, and restoring the switch cannot by itself explain or repair their failure.
- **Under default settings, exactly two things changed between the two releases:** the three ML-DSA identifiers, and the HTTP User-Agent, which the rebrand changed from `MinIO (…)` to `Silo (…)`. The second only matters if the reset happens after the handshake completes.

## Blast Radius and Why the Symptom Misleads {#blast}

The pinned list covered both directions of every TLS path, but the consequences differ sharply:

| Path | Consequence of an incompatible ingress | Visibility |
| --- | --- | --- |
| OIDC discovery / JWKS | Identity init blocks, Console never starts, **the node serves nothing** | Immediate, fatal |
| KMS/KES, LDAP(S) | Encryption or directory authentication unavailable. Both already used default curves, so the GODEBUG always worked for them | Immediate |
| Replication targets | Replication silently backs up; visible only in metrics | Easy to miss |
| Audit/notification webhooks, Lambda checks | Audit records lost, events undelivered | Easy to miss |
| S3 tiers / cloud backends | Transition failures, remote objects unreadable | Easy to miss |
| etcd, internode grid | Internal traffic, rarely crosses such a device | Low |
| Inbound S3/Console listener | Clients cannot connect; determined by the *peer's* hello | Depends on client |

Only the identity path blocks startup, which is why it was reported first. The others degrade quietly, so a deployment can be affected without anyone filing an issue.

Which deployments are exposed at all:

| Situation | Why |
| --- | --- |
| An SSL-inspection NGFW, SASE, SWG, or IDS/IPS sits on the outbound path | The reported case, and the one with a confirmed vendor defect |
| Egress through an enterprise VPN that inspects TLS | Same mechanism, applied to the whole egress |
| The environment allow-lists **JA3/JA4 client fingerprints** | The fingerprint changes whenever the handshake changes, so **every toolchain upgrade can trip it**, with the same silent reset |
| An old TLS terminator or load balancer in front of the endpoint | Intolerant of unknown extensions, or mishandles a hello split across segments |
| **Migrating from an upstream MinIO release built with Go ≤ 1.22** | That handshake carried neither post-quantum key exchange nor ML-DSA — roughly 275 bytes against roughly 1509. This cohort makes the largest single jump and is the most exposed |
| Regulated environments that disallow post-quantum algorithms | They need the classical profile for policy reasons, not interoperability ones |

Deployments whose outbound paths carry no inspection device are unaffected and should not set any of the compatibility options below.

Four properties combine to make the symptom nearly undiagnosable in the field: identity initialization retries at randomized 0–3 second intervals; the discovery and JWKS fetches have **no total timeout**, so startup can hang indefinitely; `/minio/health/live` and `/minio/health/ready` **both stay 200** while identity is offline, so a Kubernetes readiness probe reports success (only `/minio/health/cluster` returns 503 with `X-Minio-Server-Status: iam-offline`); and the error text — `read: connection reset by peer` — does not say whether the TLS handshake completed. A `curl` control test from the same image then succeeds because `curl` uses a different TLS stack and negotiates HTTP/2.

## What 20260916 Itself Changed {#widening}

Removing a pinned list does not restore the previous wire format; it adopts the current Go default, which is larger:

| Release | `supported_groups` actually offered |
| --- | --- |
| 20260903 and earlier (pinned) | `X25519MLKEM768, X25519, P256, P384, P521` |
| 20260916 (Go defaults) | `X25519MLKEM768, SecP256r1MLKEM768, SecP384r1MLKEM1024, X25519, P256, P384, P521` |

For an operator who sets nothing, 20260916 therefore offers two additional post-quantum identifiers at every TLS endpoint, inbound and outbound. This is harmless for almost every deployment, but an ingress that allow-lists group identifiers could in principle be broken by 20260916 where 20260903 worked. `GODEBUG=tlssecpmlkem=0` disables those two while retaining `X25519MLKEM768`. For an operator who does set `tlsmlkem=0`, 20260916 produces a smaller, more conservative handshake than any prior release — which is the point of the repair.

## Three Mechanisms, One Discriminating Fact {#branches}

The investigation reproduced three mechanisms that each produce the reported error text. The 20260916 repair addresses one of them.

| Branch | Mechanism | Covered by 20260916 |
| --- | --- | --- |
| A | The ingress rejects ML-KEM, and the operator had `tlsmlkem=0` set before the upgrade | **Yes** — this is what the repair restores |
| B | The ingress rejects the ML-DSA signature identifiers | No. Only a TLS 1.2 cap suppresses the offer, and no such setting is exposed |
| C | An HTTP-layer rule rejects the changed `Silo` User-Agent after a successful handshake | No, and no TLS change is relevant to it |

A fourth observation explains why the `curl` control test misleads: the discovery transport disables HTTP/2 and sends no ALPN, while `curl` negotiated h2. That difference exists in both the working and failing releases.

**One fact separates A/B from C, and the fixture results separate B from A:** whether the reset arrives immediately after the ClientHello or only after the GET is written. A single packet capture in the failing network position, or the ingress's own reject reason for the same second, settles it.

## The Known Upstream Instance {#upstream}

Branch B is not hypothetical. Two upstream Go issues describe it:

- [golang/go#81199](https://github.com/golang/go/issues/81199), *"add a GODEBUG to disable advertising ML-DSA signature algorithms in the ClientHello (Go 1.27 regression against TLS-inspecting middleboxes)"*, open since 2026-08-28. The reported symptoms are identical to #154: `read: connection reset by peer` on every TLS 1.3 connection through a TLS-inspecting firewall, while `curl`, OpenSSL 3.6, and Node.js 24 succeed from the same host, a Go 1.26 build of the same program succeeds, and `MaxVersion: tls.VersionTLS12` works. The product named there is Palo Alto Prisma Access with PAN-OS 10.2.10-h37, and the Go team's reply notes that a patched version is available.
- [golang/go#79626](https://github.com/golang/go/issues/79626), closed, carries the diagnosis. A network administrator traced it with their own firewall team: a Palo Alto IDS/IPS threat signature for OpenSSL **CVE-2020-1967** — reported there as PA threat ID 58033, last updated 2022-07-12 — inspects the `signature_algorithms_cert` extension and resets connections whose algorithm list it does not expect. Palo Alto shipped a content update disabling that signature on 2026-06-23.

CVE-2020-1967 was a null-pointer dereference reachable through a malformed `signature_algorithms_cert`; the vendor's detector for it has been firing on legitimate modern handshakes. This also explains the 12-byte delta precisely: Go 1.27 adds three ML-DSA identifiers to **both** `signature_algorithms` and `signature_algorithms_cert`, which is 3 × 2 bytes in each of two extensions.

**Go will not provide a switch.** The Go security lead's position on #81199 is that they cannot GODEBUG every low-level ClientHello change, that GODEBUGs are reserved for changes that alter negotiated parameters, and that advertising a signature algorithm is not supposed to change anything. The proposed `tlsmldsa` setting ([golang/go#81307](https://github.com/golang/go/issues/81307)) has not landed, and Chrome is expected to start GREASEing `signature_algorithms_cert`, which will expose the remaining unpatched middleboxes even faster.

Two consequences follow for SILO:

1. **SILO cannot rely on an upstream `GODEBUG` knob for ML-DSA:** providing an explicit outbound TLS compatibility setting in SILO is required for deployments blocked on Branch B.
2. **Identify the TLS-inspecting middlebox on the outbound path:** applying the vendor's threat-signature content update resolves the root cause directly at the firewall.

## The Option Space {#options}

Grouped by who has to act. Each row solves specific branches:

**Ingress side — the only complete fix.**

| Action | Branches | Cost |
| --- | --- | --- |
| Update the middlebox — threat-signature content as well as firmware — so it tolerates unknown algorithm identifiers | A, B, C | Requires the device's owner. For the identified product a content update already exists, making this the shortest path |
| Route around it: point `MINIO_IDENTITY_OPENID_CONFIG_URL` at an endpoint that does not traverse the device, or use split-horizon DNS. The discovery document's `issuer` must not change | A, B, C | Certificate hostname and issuer consistency must hold |
| Terminate TLS in a sidecar (stunnel, Envoy) that connects to the IdP itself | A, B, C | An extra component and its own trust chain |
| Send the request through `HTTPS_PROXY` | none | A CONNECT tunnel forwards the same ClientHello; only a proxy that terminates TLS changes anything |

**Deployment side — available today.**

| Action | Branches | Cost |
| --- | --- | --- |
| `GODEBUG=tlsmlkem=0` | A | Disables hybrid key exchange process-wide, including internode links and the inbound listener; certificate verification unaffected |
| `GODEBUG=tlssecpmlkem=0` | the two groups added by 20260916 | Narrower; retains `X25519MLKEM768` |
| `GODEBUG=fips140=on` | A and B | **Not recommended.** The FIPS allow-lists exclude ML-KEM and ML-DSA, but also replace cipher suites and curves and exclude Ed25519/X25519 for the entire process |
| Remain on 20260804 | A, B, C | Forfeits every subsequent security fix; emergency measure only |
| Allow the `Silo` User-Agent at the ingress | C | One rule change |

**There is no way to disable ML-DSA via GODEBUG.** Go provides no GODEBUG for signature algorithms — the `crypto/tls` entries in `internal/godebugs/table.go` are `fips140ems`, `tlsmaxrsasize`, `tlsmlkem`, `tlssecpmlkem`, and `tlssha1` — and `tls.Config` has no signature-algorithm field. The only lever is the version gate: the identifiers are TLS 1.3-only, so capping `MaxVersion` at TLS 1.2 suppresses them.

## Why the Toolchain Is Not Rolled Back {#rollback}

Rebuilding on Go 1.26 would restore the exact handshake of the working release, and upstream reports confirm that downgrading works. It is still the wrong instrument, for five reasons:

1. **It pays for a middlebox defect with everyone's toolchain.** The device at fault has a vendor fix available.
2. **It expires.** Go supports the two most recent releases. Once Go 1.28 ships, a 1.26 build runs on a standard library that no longer receives security fixes, and the same decision returns with worse options.
3. **Upstream is keeping the new defaults.** Go has declined to add a switch, and Chrome plans to GREASE the same extension.
4. **All four repositories require Go 1.27.** Server, Console, `mcli`, and `silo-pkg` all declare `go 1.27.1`; building the current source with Go 1.26.7 is rejected by the module requirement, and transitive dependencies already require 1.27.
5. **It only covers one branch.** If the reset is caused by the HTTP-layer rule of branch C, the Go version is irrelevant.

Lowering the `go` directive in `go.mod` while compiling with Go 1.27 does not help either: that mechanism only governs behaviors controlled by a `GODEBUG` setting, and ML-DSA advertisement has none.

For an affected operator waiting on a firewall signature update, staying on the `20260804` release image is a valid temporary mitigation while the middlebox is patched.

## Requirements Taken from This {#requirements}

1. **Phase-labeled diagnostics on the discovery and JWKS fetches.** Record, via `httptrace`, connection established → handshake started → handshake completed (with negotiated version, suite, and group) → request written → first response byte, and name the last phase reached in the returned error. No configuration, no protocol change, and it separates branches A, B, and C from a log line instead of a packet capture.
2. **An explicit outbound TLS compatibility setting**, covering at least the identity provider: classical curves, and optionally a TLS 1.2 cap. It must be opt-in, warn loudly at startup, and be visible in `mcli admin config` and support bundles. `MINIO_API_SECURE_CIPHERS` is the existing precedent. This is the only in-process remedy for branch B.
3. **Startup robustness:** a total deadline and context cancellation for the discovery and JWKS fetches, and a decision on whether readiness should reflect identity state.
4. **A supported diagnostic subcommand** derived from the investigation probe: handshake phases, negotiated parameters, and classical / TLS 1.2 / User-Agent controls, so an operator can localize this class of failure directly.
5. **Retire the remaining pinned cipher suites**, or at minimum give outbound paths the switch the listener already has.

Two options are explicitly rejected:

- **Shipping a lowered default** — a `godebug` directive in `go.mod`, or `ENV GODEBUG=…` in the image — silently weakens post-quantum protection for every connection and still does not address branch B.
- **Automatic downgrade-and-retry after a reset** hands an active attacker a trivial way to force TLS 1.2 with classical curves by injecting an RST; browsers removed this kind of fallback for that reason.

## Release and Communication Gates {#gates}

The repair's compatibility requirement was documented in the Server README's TLS section, in [Go 1.27 TLS and OIDC](/blog/design/go127-tls-oidc-discovery/), and in the [20260916 release notes](/blog/release/silo-20260916/). However, three things were missed during issue handling:

- The reporter was not told in the issue that the repair requires setting `GODEBUG=tlsmlkem=0` to take effect, nor which branch it addresses.
- The `GODEBUG` requirement was documented as a change note without being highlighted as an explicit operator action on the upgrade checklist.
- The issue was closed when the PR merged, before the reporter confirmed a retest.

When a fix requires an operator-configured environment variable to take effect, it must be tracked through the same release-note and upgrade-checklist gates as a compatibility change:

1. Any repair whose effect depends on an operator action is listed as a **required action** in the release notes and upgrade checklist, with the same treatment as a coordinated-upgrade item.
2. An issue reported by an external user is closed only after that reporter confirms a retest; a merged patch changes status labels, not the issue state.
3. When a repair does not cover every branch of a reported symptom, the issue explicitly states which branch was addressed, which branches remain, and what discriminating evidence is needed.

## Attribution {#attribution}

This record extends the [#154 investigation and the September Go 1.27 stack review](/blog/design/go127-tls-oidc-discovery/) with the post-release retest analysis, the upstream Go issue findings, the option space, and the process gates. Go behavior is grounded in the Go 1.27.1 standard library source and the [official release notes](https://go.dev/doc/go1.27).
