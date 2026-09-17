---
title: "Pinned TLS Parameters and Handshake Compatibility"
linkTitle: "TLS Pinning and Handshakes"
date: 2026-09-17
lastmod: 2026-09-17
author: "Ruohang Feng"
summary: >
  Why Go 1.27 changed the handshake, how SILO's inherited explicit algorithm
  lists turned a compatibility switch into a dead letter, what the 20260916
  repair does and does not cover, the full option space for an ingress that
  resets on a new ClientHello, and why a repair that only takes effect when the
  operator sets a GODEBUG is a compatibility contract change rather than a bugfix.
tags: [Design, TLS, OIDC, Operations, Compatibility]
weight: 5
draft: false
url: "/blog/design/tls-parameter-pinning/"
---

> **Status, 2026-09-17.** The Go TLS default repair
> [`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31)
> shipped in [Server 20260916](/blog/release/silo-20260916/). The reporter of
> [issue #154](https://github.com/pgsty/silo/issues/154) retested on that release
> and reports the same `connection reset by peer` on OIDC discovery. **No root
> cause is established for that deployment.** #154 was closed on 2026-09-11 on
> the strength of the merge rather than a retest; that was wrong, and this record
> states what the repair covers, what it cannot cover, and what has to change.

> **Update, 2026-09-17.** An upstream Go issue reports the same symptoms from a
> different product, and a second one carries a full diagnosis of the mechanism.
> Both are summarized in [The known upstream instance](#upstream). The practical
> consequence: the first question to ask an affected operator is what inspects
> that traffic, not what to set in SILO.

> **Evidence class.** Go behavior below is read from the Go 1.27.1 standard
> library source and the [official release notes](https://go.dev/doc/go1.27).
> Handshake byte counts and branch reproductions come from the synthetic
> fixtures of the #154 investigation, recorded in
> [Go 1.27 TLS and OIDC](/blog/design/go127-tls-oidc-discovery/). No forensic
> capture from the affected deployment has been obtained.

## In plain terms {#plain}

A TLS connection opens with a **ClientHello** listing the algorithms the client
supports. Many corporate networks put a device in the path — a WAF, a TLS
inspection appliance, a load balancer — that parses that message. Some of those
devices, on seeing an algorithm identifier they do not recognize, do not ignore
it: they reset the connection.

Go 1.27 added three new identifiers to that message — the ML-DSA post-quantum
signature schemes — for a total of **12 extra bytes**. Rebuilt on Go 1.27, SILO
says something slightly different on the wire than it did on Go 1.26. Something
in front of the reporter's identity provider does not accept it and sends a TCP
reset. `curl` from the same container succeeds because curl uses OpenSSL, which
does not offer those identifiers.

Go anticipated this class of breakage and provides an escape hatch,
`GODEBUG=tlsmlkem=0`. That switch has a precondition: **it only applies when the
application has not specified its own algorithm list.** SILO carried an explicit
curve list inherited from upstream, and that list happened to contain a
post-quantum entry — so the switch had no effect for us. The 2026-09-09 repair
removes those explicit lists, which makes the switch work again.

The limitation is the whole story: **the switch disables post-quantum key
exchange (ML-KEM); it cannot disable post-quantum signatures (ML-DSA)**, and the
12 extra bytes are ML-DSA. Go exposes no switch for those. If a deployment is
failing on the ML-DSA offer, the repair does nothing for it — which is consistent
with the retest result.

## What Go is actually solving {#why-go}

**Post-quantum key exchange is a deadline, not a preference.** The threat model
is harvest-now-decrypt-later: an adversary records encrypted traffic today and
decrypts it years later once a cryptographically relevant quantum computer
exists. Confidentiality therefore has to migrate *before* such a machine exists,
not after. NIST finalized ML-KEM ([FIPS 203](https://csrc.nist.gov/pubs/fips/203/final))
and ML-DSA ([FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)) in 2024, and
the deployed form is hybrid: `X25519MLKEM768` runs classical X25519 and ML-KEM
together and combines both secrets, so a flaw in ML-KEM leaves the connection no
weaker than X25519 alone. Browsers, CDNs and SSH implementations have been
enabling hybrid key exchange by default since 2024; Go followed in 1.24.

**Signatures are not on the same clock.** A signature cannot be forged
retroactively — a quantum computer built in 2035 does not invalidate a handshake
signed in 2026. So ML-DSA in TLS 1.3 today is an *advertisement of support*, not
a live dependency. Go 1.27 added `MLDSA44`, `MLDSA65` and `MLDSA87` to the
default signature algorithm list, which is where the 12 bytes come from:

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

Those identifiers are defined for TLS 1.3 only. `isDisabledSignatureAlgorithm`
drops them when the configuration cannot reach TLS 1.3, which — as noted below —
is the only lever an application has over them.

## The switch that was never meant to cover explicit lists {#contract}

The change that actually broke us is narrower and, read in context, defensible.
From the Go 1.27 release notes:

> Post-quantum hybrid key exchanges can now be explicitly enabled in
> `Config.CurvePreferences` even if the `tlsmlkem=0` or `tlssecpmlkem=0` GODEBUG
> options are used. **Those options were always meant to only apply to the
> default set used when `Config.CurvePreferences` is nil.**

The standard library has documented the two paths as alternatives since Go 1.24:

```go
// CurvePreferences ... If empty, the default will be used.
//
// From Go 1.24, the default includes the [X25519MLKEM768] hybrid
// post-quantum key exchange. To disable it, set CurvePreferences
// explicitly or use the GODEBUG=tlsmlkem=0 environment variable.
```

In code it is one branch: an explicit list is used verbatim; only the empty case
consults the defaults, and the GODEBUG lives in the default path.

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

The principle is that **explicit configuration outranks an environment
variable** — otherwise an operator could silently override a security policy the
developer wrote in code. Go 1.26 and earlier filtered explicit lists through the
GODEBUG as well; SILO's working behavior on Go 1.26 was therefore relying on
something Go considers to have been a bug.

Worth noting for future upgrades: Go ties GODEBUG *defaults* to the main module's
`go` directive, so a module that still declares an older version keeps the older
behavior until it moves. SILO's `go.mod` declares `go 1.27.1`, which is an
explicit statement that we take the 1.27 behavior.

## Where SILO's debt was — and where it still is {#debt}

The list in question was
`{X25519MLKEM768, CurveP256, X25519, CurveP384, CurveP521}`, inherited from
upstream and later extended with the post-quantum entry. Pinning it produced the
worst of both worlds: the deployment could not benefit from the library's
evolving defaults, **and** could not use the library's compatibility switch.

`48e184652` removes that assignment at all eight Server TLS configuration points —
the general external HTTP transport, the replication transport, the
client-certificate cloud transport, the internode transport, both grid links,
etcd, and the inbound S3/Console listener — retires the `TLSCurveIDs` helper, and
adds wire-level regression tests across five outbound constructors, two peer TLS
versions and both GODEBUG settings. Certificate and hostname verification,
cipher-suite policy, proxy handling and HTTP/2 selection are unchanged, and no
post-failure downgrade or retry was introduced. The earlier OIDC-only candidate
was withdrawn because the same transport also serves identity plugins,
notification and Lambda reachability checks, audit webhooks and S3 cloud tiers.

**The same debt remains one layer down.** Cipher suites are still pinned:
`crypto.TLSCiphers()` and `crypto.TLSCiphersBackwardCompatible()` are assigned in
the outbound transports, LDAP, etcd, the grid links and the inbound listener. The
listener at least has `MINIO_API_SECURE_CIPHERS` to choose between the two sets;
**no outbound path has any switch at all**. The next time Go changes the suite
defaults, the same script runs again.

The general guidance this record adopts: **set `MinVersion` and leave the rest to
the standard library.** Where an incompatible endpoint genuinely requires a
narrower profile, expose it as product configuration that is visible in
`mc admin config` and in a support bundle — never as a value pinned in source.
Protocol ossification is an old problem: TLS 1.3 had to disguise itself as TLS
1.2 on the wire, and GREASE exists precisely to force middleboxes to tolerate
identifiers they do not know.

## What is actually different on the wire {#wire}

Measured against the same synthetic IdP fixture, with default settings:

| Build | ClientHello | ML-KEM (4588) | ML-DSA 0x0904-6 | User-Agent |
| --- | ---: | --- | --- | --- |
| 20260804, Go 1.26.5 — works | 1497 B | present | absent | `MinIO (…)` |
| 20260903, Go 1.27.1 — fails | 1509 B | present | present | `Silo (…)` |
| 20260916, Go 1.27.1 — repaired | 1509 B | present (default) | present | `Silo (…)` |
| 20260804 with `tlsmlkem=0` | 275 B | absent | absent | `MinIO (…)` |
| 20260903 with `tlsmlkem=0` | 1509 B | **still present** | present | `Silo (…)` |

Two readings matter and are easy to miss.

**ML-KEM was already being offered by the working release.** Unless the operator
had set `tlsmlkem=0` *before* the upgrade, ML-KEM is not a variable between the
working and failing versions, and restoring the switch cannot by itself explain
or repair their failure.

**Under default settings, exactly two things changed between the two releases:**
the three ML-DSA identifiers, and the HTTP User-Agent, which the rebrand changed
from `MinIO (…)` to `Silo (…)`. The second only matters if the reset happens
after the handshake completes.

## Blast radius and why the symptom misleads {#blast}

The pinned list covered both directions of every TLS path, but the consequences
differ sharply:

| Path | Consequence of an incompatible ingress | Visibility |
| --- | --- | --- |
| OIDC discovery / JWKS | Identity init blocks, Console never starts, **the node serves nothing** | Immediate, fatal |
| KMS/KES, LDAP(S) | Encryption or directory authentication unavailable. Both already used default curves, so the GODEBUG always worked for them | Immediate |
| Replication targets | Replication silently backs up; visible only in metrics | Easy to miss |
| Audit/notification webhooks, Lambda checks | Audit records lost, events undelivered | Easy to miss |
| S3 tiers / cloud backends | Transition failures, remote objects unreadable | Easy to miss |
| etcd, internode grid | Internal traffic, rarely crosses such a device | Low |
| Inbound S3/Console listener | Clients cannot connect; determined by the *peer's* hello | Depends on client |

Only the identity path blocks startup, which is why it was reported first. The
others degrade quietly, so a deployment can be affected without anyone filing an
issue.

Which deployments are exposed at all:

| Situation | Why |
| --- | --- |
| An SSL-inspection NGFW, SASE, SWG or IDS/IPS sits on the outbound path | The reported case, and the one with a confirmed vendor defect |
| Egress through an enterprise VPN that inspects TLS | Same mechanism, applied to the whole egress |
| The environment allow-lists **JA3/JA4 client fingerprints** | The fingerprint changes whenever the handshake changes, so **every toolchain upgrade can trip it**, with the same silent reset |
| An old TLS terminator or load balancer in front of the endpoint | Intolerant of unknown extensions, or mishandles a hello split across segments |
| **Migrating from an upstream MinIO release built with Go ≤ 1.22** | That handshake carried neither post-quantum key exchange nor ML-DSA — roughly 275 bytes against roughly 1509. This cohort makes the largest single jump and is the most exposed |
| Regulated environments that disallow post-quantum algorithms | They need the classical profile for policy reasons, not interoperability ones |

Deployments whose outbound paths carry no inspection device are unaffected, and
should not set any of the compatibility options below.

Four properties combine to make the symptom nearly undiagnosable in the field:
identity initialization retries at randomized 0–3 second intervals; the discovery
and JWKS fetches have **no total timeout**, so startup can hang indefinitely;
`/minio/health/live` and `/minio/health/ready` **both stay 200** while identity is
offline, so a Kubernetes readiness probe reports success (only
`/minio/health/cluster` returns 503 with `X-Minio-Server-Status: iam-offline`);
and the error text — `read: connection reset by peer` — does not say whether the
TLS handshake completed. A curl control test from the same image then succeeds,
because curl uses a different TLS stack and negotiates HTTP/2.

## What 20260916 itself changed {#widening}

Removing a pinned list does not restore the previous wire format; it adopts the
current default, which is larger:

| Release | `supported_groups` actually offered |
| --- | --- |
| 20260903 and earlier (pinned) | `X25519MLKEM768, X25519, P256, P384, P521` |
| 20260916 (Go defaults) | `X25519MLKEM768, SecP256r1MLKEM768, SecP384r1MLKEM1024, X25519, P256, P384, P521` |

For an operator who sets nothing, 20260916 therefore offers two additional
post-quantum identifiers at every TLS endpoint, inbound and outbound. This is
harmless for almost every deployment, but an ingress that allow-lists group
identifiers could in principle be broken by 20260916 where 20260903 worked.
`GODEBUG=tlssecpmlkem=0` disables exactly those two while retaining
X25519MLKEM768. For an operator who does set `tlsmlkem=0`, 20260916 produces a
smaller, more conservative handshake than any prior release — which is the point
of the repair.

## Three mechanisms, one discriminating fact {#branches}

The investigation reproduced three mechanisms that each produce the reported
error text. The repair addresses one of them.

| Branch | Mechanism | Covered by 20260916 |
| --- | --- | --- |
| A | The ingress rejects ML-KEM, and the operator had `tlsmlkem=0` set before the upgrade | **Yes** — this is what the repair restores |
| B | The ingress rejects the ML-DSA signature identifiers | No. Only a TLS 1.2 cap suppresses the offer, and no such setting is exposed |
| C | An HTTP-layer rule rejects the changed `Silo` User-Agent after a successful handshake | No, and no TLS change is relevant to it |

A fourth observation explains why the curl control test misleads but not why the
upgrade regressed: the discovery transport disables HTTP/2 and sends no ALPN,
while curl negotiated h2. That difference exists in both the working and failing
releases.

**One fact separates A/B from C, and the fixture results separate B from A:**
whether the reset arrives immediately after the ClientHello or only after the GET
is written. A single packet capture in the failing network position, or the
ingress's own reject reason for the same second, settles it. That evidence was
never requested from the reporter — which is the process failure this record
exists to fix.

## The known upstream instance {#upstream}

Branch B is not hypothetical. Two upstream Go issues describe it:

- [golang/go#81199](https://github.com/golang/go/issues/81199), *"add a GODEBUG
  to disable advertising ML-DSA signature algorithms in the ClientHello (Go 1.27
  regression against TLS-inspecting middleboxes)"*, open since 2026-08-28.
  The reported symptoms are identical to #154: `read: connection reset by peer`
  on every TLS 1.3 connection through a TLS-inspecting firewall, while curl,
  OpenSSL 3.6 and Node.js 24 succeed from the same host, a Go 1.26 build of the
  same program succeeds, and `MaxVersion: tls.VersionTLS12` works. The product
  named there is Palo Alto Prisma Access with PAN-OS 10.2.10-h37, and the Go
  team's reply notes that a patched version is available.
- [golang/go#79626](https://github.com/golang/go/issues/79626), closed, carries
  the diagnosis. A network administrator traced it with their own firewall team:
  a Palo Alto IDS/IPS threat signature for OpenSSL **CVE-2020-1967** — reported
  there as PA threat ID 58033, last updated 2022-07-12 — inspects the
  `signature_algorithms_cert` extension and resets connections whose algorithm
  list it does not expect. Palo Alto shipped a content update disabling that
  signature on 2026-06-23.

CVE-2020-1967 was a null-pointer dereference reachable through a malformed
`signature_algorithms_cert`; the vendor's detector for it has now been firing on
legitimate modern handshakes for years. This also explains the 12-byte delta
precisely: Go 1.27 adds three ML-DSA identifiers to **both**
`signature_algorithms` and `signature_algorithms_cert`, which is 3 × 2 bytes in
each of two extensions.

**Go will not provide a switch.** The security lead's position on #81199 is that
they cannot GODEBUG every low-level ClientHello change, that GODEBUGs have been
reserved for changes that alter negotiated parameters, and that advertising a
signature algorithm is not supposed to change anything. The proposed `tlsmldsa`
setting ([golang/go#81307](https://github.com/golang/go/issues/81307)) has not
landed. Chrome is also expected to start GREASEing `signature_algorithms_cert`,
which will break the remaining affected devices harder and faster.

Two consequences for SILO. First, **no plan may depend on an upstream knob
appearing**: the explicit compatibility setting in the requirements below is
mandatory, not a fallback. Second, the fastest diagnostic question for any
affected operator is *what inspects this traffic* — a vendor content update may
close the case in one step, and that is a real fix rather than a workaround.

## The option space {#options}

Grouped by who has to act. Each row solves specific branches; before the
discriminating evidence exists, any of them is a guess.

**Ingress side — the only complete fix.**

| Action | Branches | Cost |
| --- | --- | --- |
| Update the middlebox — threat-signature content as well as firmware — so it tolerates unknown algorithm identifiers | A, B, C | Requires the device's owner. For the identified product a content update already exists, so this can be the shortest path, not the longest |
| Route around it: point `MINIO_IDENTITY_OPENID_CONFIG_URL` at an endpoint that does not traverse the device, or use split-horizon DNS. The discovery document's `issuer` must not change | A, B, C | Certificate hostname and issuer consistency must hold |
| Terminate TLS in a sidecar (stunnel, Envoy) that connects to the IdP itself | A, B, C | An extra component and its own trust chain |
| Send the request through `HTTPS_PROXY` | none | A CONNECT tunnel forwards the same ClientHello; only a proxy that terminates TLS changes anything |

**Deployment side — available today.**

| Action | Branches | Cost |
| --- | --- | --- |
| `GODEBUG=tlsmlkem=0` | A | Disables hybrid key exchange process-wide, including internode links and the inbound listener; certificate verification unaffected |
| `GODEBUG=tlssecpmlkem=0` | the two groups added by 20260916 | Narrower; retains X25519MLKEM768 |
| `GODEBUG=fips140=on` | A and B | **Not recommended.** The FIPS allow-lists exclude ML-KEM and ML-DSA, but also replace cipher suites and curves and exclude Ed25519/X25519 for the entire process |
| Remain on 20260804 | A, B, C | Forfeits every subsequent security fix; emergency measure only |
| Allow the `Silo` User-Agent at the ingress | C | One rule change |

**There is no way to disable ML-DSA today.** Go provides no GODEBUG for
signature algorithms — the crypto/tls entries in `internal/godebugs/table.go` are
`fips140ems`, `tlsmaxrsasize`, `tlsmlkem`, `tlssecpmlkem` and `tlssha1` — and
`tls.Config` has no signature-algorithm field. The only lever is the version
gate: the identifiers are TLS 1.3-only, so capping `MaxVersion` at TLS 1.2
suppresses them. SILO does not expose that anywhere. That is the gap.

## Why the toolchain is not rolled back {#rollback}

Rebuilding on Go 1.26 would restore the exact handshake of the working release,
and upstream reports confirm that downgrading works. It is still the wrong
instrument, for five reasons.

1. **It pays for someone else's defect with everyone's toolchain.** The device
   at fault has a vendor fix available.
2. **It expires.** Go supports the two most recent releases. Once Go 1.28 ships,
   a 1.26 build runs on a standard library that no longer receives security
   fixes, and the same decision returns with worse options.
3. **Upstream is not going back.** Go has declined to add a switch, and Chrome
   intends to GREASE the same extension. A rollback defers the problem rather
   than solving it.
4. **It is not a compiler swap.** Server, Console, mcli and silo-pkg all declare
   `go 1.27.1`; building the current source with Go 1.26.7 is rejected by the
   module requirement, so a downgrade is a coordinated change across four
   repositories plus whatever transitive modules already require 1.27.
5. **It only covers one branch.** If the reset is the HTTP-layer rule of branch
   C, the toolchain is irrelevant.

One adjacent idea does not work either: lowering the `go` directive in `go.mod`
while still compiling with 1.27. That mechanism only governs behaviors that have
a GODEBUG, and ML-DSA advertisement has none — it would change unrelated
defaults such as the macOS root-certificate behavior and leave the handshake
exactly as it is.

**Rolling back the release image is a different decision and a legitimate one.**
An affected operator staying on 20260804 while their appliance is patched is
sound emergency practice; the product freezing its compiler for the same reason
is not.

## Requirements taken from this {#requirements}

1. **Phase-labeled diagnostics on the discovery and JWKS fetches.** Record, via
   `httptrace`, connection established → handshake started → handshake completed
   (with negotiated version, suite and group) → request written → first response
   byte, and name the last phase reached in the returned error. No configuration,
   no protocol change, and it separates branches A, B and C from a log line
   instead of a packet capture. This is the highest-value item.
2. **An explicit outbound TLS compatibility setting**, covering at least the
   identity provider: classical curves, and optionally a TLS 1.2 cap. It must be
   opt-in, warn loudly at startup, and be visible in `mc admin config` and
   support bundles. `MINIO_API_SECURE_CIPHERS` is the existing precedent. This is
   the only in-process remedy for branch B, and since Go has declined to add a
   signature-algorithm switch, it is mandatory rather than a fallback.
3. **Startup robustness**: a total deadline and context cancellation for the
   discovery and JWKS fetches, and a decision on whether readiness should reflect
   identity state, which currently it does not.
4. **A supported diagnostic subcommand** derived from the investigation probe:
   handshake phases, negotiated parameters, and classical / TLS 1.2 / User-Agent
   controls, so an operator can localize this class of failure without us.
5. **Retire the remaining pinned cipher suites**, or at minimum give outbound
   paths the switch the listener already has.

Two options are explicitly rejected. **Shipping a lowered default** — a
`godebug` directive in `go.mod`, or `ENV GODEBUG=…` in the image — silently
weakens post-quantum protection for every connection and still does not address
branch B. **Automatic downgrade-and-retry after a reset** hands an active
attacker a trivial way to force TLS 1.2 with classical curves by injecting an
RST; browsers removed exactly this kind of fallback for that reason. If it is
ever built, it belongs behind the explicit opt-in of requirement 2.

## Release and communication gates {#gates}

The repair's compatibility requirement was documented — in the Server README's
TLS section, in [Go 1.27 TLS and OIDC](/blog/design/go127-tls-oidc-discovery/),
and in the [20260916 release notes](/blog/release/silo-20260916/). Three things
were not done, and each contributed directly to the outcome:

- The reporter was never told, in the issue, that the repair requires an
  operator-set GODEBUG to take effect, nor which branch it addresses.
- The requirement never entered an upgrade checklist. It was filed as a record of
  what changed rather than as an action the operator must take.
- The issue was closed on the merge rather than on a retest by the reporter.

The underlying misclassification is the lesson: this was treated as a correctness
repair (restore the library default) when it is also a **compatibility contract
change** — its effect depends on an operator action. Classified correctly, it
would have gone through the release-gate and user-communication paths rather than
the documentation path alone.

Three gates follow, and apply to every future change of this shape:

1. Any repair whose effect depends on an operator action is listed as a
   **required action** in the release notes and in the upgrade checklist, with
   the same treatment as a coordinated-upgrade item.
2. An issue reported by an external user is closed only after that reporter
   confirms a retest. A merged patch changes status labels, not the issue state.
3. When a repair does not fully resolve the reported symptom, the issue states
   which branch was addressed, which branches remain, and exactly what evidence
   is needed — rather than relying on the reporter finding a README section.

## Attribution {#attribution}

This record extends the [#154 investigation and the September Go 1.27 stack
review](/blog/design/go127-tls-oidc-discovery/) with the post-release retest
result, the mechanism analysis, the option space and the process gates.
Reproduction artifacts and the full evidence chain are retained outside the
documentation tree. The supportable statement remains: the merged repair restores
Go key-exchange defaults at the eight affected Server configuration points, and
that is verified with synthetic negative controls. It diagnoses no specific
deployment, and #154 requires a retest with phase-level evidence before any root
cause is claimed.
