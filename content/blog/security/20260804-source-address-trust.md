---
title: "Three Headers, One Lie: Making the Client Source Address Mean Something"
linkTitle: "Source Address Trust"
date: 2026-08-04
author: "Ruohang Feng"
description: "A switch named for one header was being recommended as a defence against three. Disabling X-Forwarded-For left X-Real-IP and Forwarded answering in its place, so aws:SourceIp and every audit client address stayed forgeable by anyone who could reach the API port. The fix is an opt-in trusted-proxy boundary — and the more interesting decision was refusing to repair the old switch."
tags: [Security, Source Address]
weight: 100
draft: false
url: "/blog/security/source-address-trust/"
---

**Status:** Landed on `pgsty/minio` `master` as `fe6dc4780`, **unreleased**
**Classification:** Opt-in hardening plus a documentation defect, **not a vulnerability and not a regression**; no CVE assigned. The underlying weakness is inherited from upstream and its default behaviour is unchanged here
**Affected scope:** `aws:SourceIp` policy conditions, the audit log `remotehost` field, S3 event notification `Host`, and the client shown by `mc admin trace` — on any deployment whose S3 API port is reachable without passing through a header-sanitising proxy
**Upstream:** nothing to file — `minio/minio` is archived. Prior art there: [PR #4736](https://github.com/minio/minio/pull/4736) (2017, the concern raised and half-addressed), [discussion #17878](https://github.com/minio/minio/discussions/17878) (2023, maintainer marks it working as intended), [PR #20977](https://github.com/minio/minio/pull/20977) (2025, the partial switch)

> This article states plainly that an `IpAddress` policy condition is not enforceable on a directly-reachable MinIO deployment, and that this remains true by default after the change. That is a property of upstream MinIO as shipped, not a defect introduced by the fork, and it has never been documented anywhere. Publishing it is the point.

## Conclusions first {#summary}

- MinIO reads the client's address out of three interchangeable headers — `X-Forwarded-For`, `X-Real-IP`, RFC 7239 `Forwarded` — and never from the TCP connection unless all three are absent. That address becomes `aws:SourceIp` and the audit log's client field, so whoever controls it controls both IP-based access control and the attribution of every logged action.
- The one switch that existed, `_MINIO_API_XFF_HEADER=off`, suppresses **one** of those three. An attacker's response is to send `X-Real-IP` instead. Our own code comment was recommending it as the mitigation.
- **"Put MinIO behind a reverse proxy" is not sufficient**, for two independent reasons: on Kubernetes an Ingress and a ClusterIP Service routinely coexist so the proxy is not the only way in; and the stock nginx recipe *appends* to `X-Forwarded-For`, leaving a client-supplied entry in the left-most position — which is exactly where MinIO reads.
- The fix is a new opt-in setting, `MINIO_API_TRUSTED_PROXIES`, generalising a trusted-proxy mechanism this fork already built for LDAP STS rate limiting. Set to a list, forwarded headers are believed only from those peers and chains are walked right-to-left. Set to `none`, nothing is believed.
- **The most consequential decision was one we reversed.** The first implementation widened `_MINIO_API_XFF_HEADER=off` to suppress all three headers. That was the only part of the change that could alter an existing deployment's behaviour, and it was backed out. The switch keeps its exact upstream semantics, and upstream's `TestXFFDisabled` is retained unmodified as the proof.
- Net compatibility impact: **none for any deployment that does not opt in.**
- Adversarial review found four defects in the first implementation, including one that made the new setting silently ineffective for every deployment configured through an environment file.

## What the address is actually used for {#consumers}

The value comes from a single function, `handlers.GetSourceIPFromHeaders`. Tracing its consumers is what turns this from a logging curiosity into a security question:

| Consumer | Why it matters |
| :-- | :-- |
| `aws:SourceIp` (`cmd/bucket-policy.go`) | Decides `IpAddress` / `NotIpAddress` policy conditions |
| Audit `remotehost` | The record used to investigate every other incident |
| Event notification `Host` | Flows to downstream consumers as fact |
| `mc admin trace` client | Operator's live view of who is doing what |

Two of these are security-relevant in different ways. A forged `aws:SourceIp` is a live access-control bypass: an `IpAddress` condition meant to confine a principal to an office CIDR is satisfied by asserting an address in that CIDR, and a `NotIpAddress` deny is evaded by asserting one outside it. A forged audit address is quieter and arguably worse — it corrupts the record retroactively, it applies even where no IP-based policy exists, and nobody notices until they need the logs.

Note also that the value is never validated as an IP address in the default path. `Forwarded: for="_gazonk"` is accepted and returned verbatim; upstream's own test asserts it.

## The setting that looked like a mitigation {#the-switch}

`internal/handlers/proxy.go` gates exactly one header:

```go
if enableXFFHeader {
    if fwd := r.Header.Get(xForwardedFor); fwd != "" {
        // ... left-most entry
    }
}
if addr == "" {
    if fwd := r.Header.Get(xRealIP); fwd != "" {
        addr = fwd                       // not gated
    } else if fwd := r.Header.Get(forwarded); fwd != "" {
        // ... first for= element        // not gated
    }
}
```

Setting `_MINIO_API_XFF_HEADER=off` costs an attacker one line: send `X-Real-IP` instead of `X-Forwarded-For`. Worse, disabling `X-Forwarded-For` *moves* the trust to a header the operator has not thought about, so the switch can leave a deployment in a state its owner has not modelled.

Where did it come from? Upstream PR [minio/minio#20977](https://github.com/minio/minio/pull/20977), whose entire stated motivation is:

> Customer request to disable all XFF header handling, ping me in Slack for more details.

No security rationale, no mention of `X-Real-IP` or `Forwarded`, no public discussion of why one header was gated and two were not. The narrowness is an oversight, not a considered scope. That mattered for the design, because it meant nobody had decided the other two should stay trusted — but as we will see, it did *not* end up justifying a change to the switch.

### Upstream knew, in 2017 {#upstream-history}

The most interesting thing found while writing this up is that none of it is news to upstream. The history is a small lesson in how a security decision decays.

**August 2017.** `IpAddress` / `NotIpAddress` condition support is added in [PR #4736](https://github.com/minio/minio/pull/4736). During review the maintainer, @harshavardhana, raises exactly the concern this article is about: `X-Forwarded-For` is trivially spoofed, the left-most entry is the client's own, and using it for a security decision would let a malicious client reach objects. The contributor accepts it and **removes `X-Forwarded-For` support entirely**, leaving only `X-Real-IP`, on the stated reasoning that a proxy sets it and a client cannot manipulate it. Merged five days later.

That reasoning is half right, and its unstated half is the whole problem: `X-Real-IP` is untamperable *only if the proxy in front overwrites it*. Nothing enforced that, and nothing told operators it was load-bearing.

**Today.** `X-Forwarded-For` is read first, ahead of `X-Real-IP`. The 2017 decision did not survive; it dissolved across later refactors of the condition-value plumbing rather than being reversed on purpose. There is no commit that says "we are re-admitting the spoofable header into policy decisions" — which is precisely how this class of decay happens.

**August 2023.** In [discussion #17878](https://github.com/minio/minio/discussions/17878) an operator reports that source IPs behind a load balancer are unreliable. The maintainer's answer is unambiguous: without reliable source-IP visibility, IP-based restrictions are impractical, and the recommendation is to compartmentalise by tag or namespace instead. Marked working as intended.

So upstream's own position — stated by a maintainer, in public — is **do not rely on `aws:SourceIp`**. That is a defensible engineering stance. What is missing is anywhere an operator would encounter it: it is not in the policy documentation, not in the condition-key reference, and not near the setting that appears to make it safe. An `IpAddress` condition is accepted without complaint and behaves as though it works.

That gap is the actual defect being fixed here, and it reframes the change. The allow-list is not overturning an upstream judgement; it is offering the mechanism that would make the 2017 concern answerable, to the deployments that want it. The documentation is doing the heavier lifting: writing down a contract that has been implicit since 2017 and contradicted by its own switch since 2025.

## Why "put it behind a proxy" is not the answer {#proxy-is-not-enough}

This is the standard advice, and it fails in two common, independent ways.

### The proxy is not the only way in

On Kubernetes an Ingress and a ClusterIP Service routinely coexist. The Ingress sanitises headers; the Service does not, and any pod in the cluster can reach it. The security boundary is assumed to be the Ingress but is actually the pod network. The same shape appears in Pigsty deployments, where a load balancer fronts MinIO while the service ports remain reachable on the internal network.

### The canonical nginx recipe preserves attacker input

The near-universal snippet is:

```nginx
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
```

`$proxy_add_x_forwarded_for` expands to `$http_x_forwarded_for, $remote_addr` — it **appends** to whatever the client sent. A client sending `X-Forwarded-For: 1.2.3.4` causes nginx to forward `1.2.3.4, <real client>`. MinIO takes the **left-most** element, which is the attacker's.

So a correctly-proxied, hardened, no-direct-access deployment is *still* forgeable, because left-most parsing and append-style proxies are mutually incompatible. Only `proxy_set_header X-Forwarded-For $remote_addr;` (overwrite) is safe under the default mode, and that is not what operators copy from the documentation.

This is the finding that rules out a documentation-only fix. Deployment discipline cannot close it; the chain has to be read from the other end, which requires code.

## The design {#design}

Rather than inventing a mechanism, we generalised one this fork already has. `MINIO_IDENTITY_LDAP_STS_TRUSTED_PROXIES` — added during the [LDAP STS throttling work](/blog/security/cve-2026-33419/) — already implements CIDR allow-list parsing, catch-all rejection, and a right-to-left chain walk, scoped to rate-limit bucketing. The parser moved to `internal/config` and both paths now share it.

One setting selects the mode:

| Mode | `MINIO_API_TRUSTED_PROXIES` | Source address |
| :-- | :-- | :-- |
| Untrusted (default) | unset | unchanged from today |
| Trust nobody | `none` | always the TCP peer |
| Allow-listed | addresses and CIDR blocks | forwarded headers, only from listed peers |

Under the allow-listed mode, `X-Forwarded-For` and `Forwarded` are read right-to-left, stepping over entries that name a listed proxy, and the first remaining address wins. Each proxy appends the peer it actually saw, so an entry the client injected sits to the left of the one its proxy wrote and the walk stops before reaching it. Appending proxies become safe.

`GetSourceScheme` is deliberately untouched. It feeds the `Location` URL in S3 responses rather than a policy decision, and suppressing it would hand `http://` URLs to every deployment terminating TLS at a proxy.

## Trade-offs {#tradeoffs}

### Whether to change the default {#tradeoff-default}

Changing the default to distrust forwarded headers would make every existing reverse-proxy deployment's `aws:SourceIp` and audit addresses become the proxy's address overnight. Policies could fail closed; audit continuity would break.

Not changing it leaves directly-reachable deployments exposed.

**Decision: do not change it.** But "do not change" is not the same as "stay silent". The consequence is now written into the code comment and the operator documentation in as many words: under the default mode, an `IpAddress` condition is not access control and the audit address is not evidence. Making the cost visible so operators can choose is better than making a choice for them that detonates during a release window.

### Whether to widen the existing switch {#tradeoff-widen}

This is the decision we got wrong first and reversed, and it is the part of the story most worth recording.

The original brief asked that when an operator explicitly disables forwarded-header trust, clients must not be able to forge through an equivalent header. The obvious reading is "fix `_MINIO_API_XFF_HEADER=off` so it covers all three", and that is what the first implementation did.

The case for widening was decent. Upstream's PR title says "disable **all** X-Forwarded-For header handling"; its described scope is audit logs and IP-based access control, both of which are about not believing client-claimed addresses; the switch is undocumented, so its audience is small; and the failure direction is safe, since the fallback is the real TCP peer rather than an attacker-controlled value.

The case against turned out to be decisive. Widening it changes behaviour for a real population: operators whose proxy appends to `X-Forwarded-For` (polluted) but overwrites `X-Real-IP` (clean) may have discovered `off` as a way to get the correct address. Upstream's `TestXFFDisabled` asserts exactly that behaviour — with the switch off and both headers present, `X-Real-IP` wins — so the behaviour is not merely incidental, it is pinned by a test. Those operators would have seen audit addresses silently flip from the real client to their proxy, and `IpAddress` conditions potentially start denying.

The reversal came from separating the *goal* from the *mechanism*. The goal was "a complete, enforceable way to turn this off exists". Nothing required that the existing variable be the thing that provides it. Expressing it as `MINIO_API_TRUSTED_PROXIES=none` achieves the identical guarantee with **zero** effect on anyone who has not opted in.

**Decision: leave `_MINIO_API_XFF_HEADER` exactly as upstream defined it.** It gates `X-Forwarded-For` only, within whichever trust mode is in force. Upstream's `TestXFFDisabled` is retained unmodified and still passes. The documentation now says plainly what the switch is *not*: it is a parsing switch, not a trust boundary, and a client refused one header simply sends another.

A secondary benefit: this collapses two interacting variables into one policy setting, so there is no longer a precedence rule ("`off` outranks the allow-list") for operators to learn and for us to get wrong.

### Environment variable or config subsystem {#tradeoff-config}

Registering `trusted_proxies` as an `api` subsystem key would give `mc admin config` visibility, help text, and hot reload, matching how `sts_trusted_proxies` is done.

It would also introduce a window. Config subsystems load after the object layer initialises, so between process start and config application the trust policy would be empty — which under a "list is empty means trust everyone" reading is **fail-open**. A security boundary must not have a fail-open window. Separately, a trust boundary that can be changed at runtime is not obviously desirable.

**Decision: environment variable.** The cost is discoverability, and one bug described below.

### Loopback is always trusted as a peer {#tradeoff-loopback}

The FTP and SFTP front-ends connect to the S3 layer over `127.0.0.1` and declare their session's client with `X-Forwarded-For` (`cmd/sftp-server-driver.go`). An allow-list that does not exempt loopback attributes every FTP and SFTP request to the server itself.

The cost is that any process on the same host can forge. That is acceptable: an attacker who can open connections from localhost already has code execution on the host, and the threat model is lost well before this point. The FTP/SFTP regression, by contrast, would be certain and would affect everyone using those front-ends.

**Decision: exempt loopback as a peer.** Adversarial review then caught that the first implementation also treated loopback as a skippable *chain entry*, which is unnecessary for the FTP/SFTP case and actively harmful — see below. The two are now separate checks.

### `X-Forwarded-For` versus `X-Real-IP`: genuinely unresolvable {#tradeoff-precedence}

Under the allow-listed mode, which header wins when both are present?

- A proxy that authors only `X-Real-IP` and relays the client's `X-Forwarded-For` (some nginx configurations) → preferring `X-Forwarded-For` takes the forged value.
- A proxy that authors only `X-Forwarded-For` and relays the client's `X-Real-IP` (**AWS ALB**) → preferring `X-Real-IP` takes the forged value.

Both are common, and the server cannot tell which situation it is in from the request. This is not an undecided question; it is undecidable without the operator telling us what their proxy authors.

**Decision: prefer `X-Forwarded-For`.** It is the only one of the two that carries a chain that can be checked against the allow-list, and this path decides access control rather than rate-limit bucketing, so the value that can be validated should win. It also keeps header precedence identical to the default mode, so switching modes does not silently change precedence as well.

This **deliberately diverges** from `getSTSLDAPTrustedProxySourceIP`, which prefers `X-Real-IP`. Two contradicting implementations of the same question in one codebase is a hazard in itself, so both sites now carry a comment naming the divergence and its reason, so that nobody "unifies" them without re-deciding. The operator documentation states the mitigation for both directions: strip whichever header your proxy does not author.

### A broad allow-list is worse than no allow-list {#tradeoff-breadth}

This is the most counter-intuitive property and the one most likely to bite.

Entries on the list are skipped during the chain walk. So `MINIO_API_TRUSTED_PROXIES=10.0.0.0/8`, configured because the load balancer is `10.0.0.1`, makes every client inside `10/8` skippable as well. A client at `10.5.5.5` sending `X-Forwarded-For: 8.8.8.8` produces a chain of `8.8.8.8, 10.5.5.5`; the walk steps over `10.5.5.5` as a "trusted hop" and returns `8.8.8.8`.

A broad list therefore does not merely trust more peers — **it lets those peers forge.** nginx's `set_real_ip_from` has the same property with `real_ip_recursive`.

There is no algorithmic fix: the list is doing double duty as "who may forward" and "whose address may be discarded", and separating them would mean two lists to keep in sync. **Decision: keep one list, and make the constraint prominent** — a callout block in the operator documentation, and the rule stated in the code comment where the walk happens. Only `/0` is rejected as a catch-all, and the documentation says explicitly that this is a guardrail rather than a proof, since `0.0.0.0/1,128.0.0.0/1` covers the same ground.

### Multi-node forwarding {#tradeoff-multinode}

MinIO forwards requests between nodes for bucket-DNS routing, listing continuation, heal-by-token, batch jobs and pool decommissioning. The receiving node's TCP peer is the forwarding node, not the client.

| Mode | Receiving node resolves |
| :-- | :-- |
| Default | the client |
| `none` | **the forwarding node** |
| Allow-list without node addresses | **the forwarding node** |
| Allow-list with node addresses | the client |

This is not an obscure path: a `ListObjectsV2` continuation token carries the node index, so any client can cause its own request to be forwarded. Under `none`, that request is then evaluated with `aws:SourceIp` set to an internal node address — which an `IpAddress` condition allowing internal ranges would treat as a pass.

**Decision: document it, and steer multi-node clusters to the allow-list.** `none` cannot be corrected for this case, because it believes nothing by definition. Automatically seeding the cluster's own addresses was considered and rejected: it needs DNS resolution at startup and re-resolution as node addresses change, which is more machinery and more failure modes than the explicit configuration it replaces.

## Compatibility {#compatibility}

The change was deliberately structured so that risk is not spread evenly across it. Every piece is either opt-in or dead code in the default configuration.

| Change | Who is affected | Risk |
| :-- | :-- | :-- |
| `MINIO_API_TRUSTED_PROXIES` allow-list | only those who set it | none |
| Forwarder sanitises `X-Real-IP` / `Forwarded` | code path does not execute in default mode | none |
| Startup failure on a malformed value | only those who set it, incorrectly | none |
| Policy re-read after environment-file load | same result when nothing is set | none |
| LDAP parser extracted for sharing | nobody — pure code motion, verified identical | none |
| `_MINIO_API_XFF_HEADER` semantics | **nobody — reverted** | none |
| `_MINIO_API_XFF_HEADER` read timing | **nobody — upstream timing kept deliberately** | none |

**Evidence for the default path.** `unverifiedSourceIP` is a verbatim copy of the original function body, including its quirks: the `", "` separator, the fall-through when the left-most element is empty, and the acceptance of non-IP values such as `_gazonk`. An independent review verified behavioural parity against `HEAD` over 21 cases — empty `X-Forwarded-For`, a bare comma, a leading `", "`, `","` versus `", "` separators, `" , "`, IPv4-mapped addresses, bracketed IPv6, non-IP junk, and all three `Forwarded` forms. Upstream's `TestGetSourceIP` and `TestXFFDisabled` are both retained unmodified and pass.

**A subtlety self-review caught.** The new setting is read after `MINIO_CONFIG_ENV_FILE` is loaded, which is what makes it work in packaged deployments. The obvious tidiness move is to read `_MINIO_API_XFF_HEADER` in the same place — and that would have been a behaviour change, because upstream reads it at package initialisation, *before* environment files exist. An operator who wrote it into an environment file has it silently ignored today; picking it up would make an already-deployed setting suddenly start working, flipping their source addresses from the left-most `X-Forwarded-For` entry to `X-Real-IP`. The old switch therefore keeps upstream's read timing along with upstream's semantics, and a test pins that so nobody tidies it later. The quirk is documented instead: set it in the process environment if you want it honoured.

**The defensive code that was not defending anything.** Sharing the parser initially came with two extras: allow-list entries written in IPv4-mapped form were rewritten to the IPv4 prefix they denote, and the address being matched was unmapped and de-zoned. Both looked like corrections — an entry written `::ffff:192.168.1.10` is otherwise accepted and then matches nothing, which is a silent failure worth removing.

They were removed anyway, and the reason is worth recording. Both call paths reduce the address through `net.ParseIP(...).String()` before matching, and that already collapses `::ffff:10.0.0.1` to `10.0.0.1`; a dual-stack listener reports an IPv4 peer in plain form regardless. So neither extra could be reached by a real request. Their only observable effect was on what the *shared* function meant for the LDAP STS allow-list that had been using it first — 18 differences that a test could see by calling the function directly and no deployment could.

Worse, one of them manufactured the fail-open described below: rewriting `::ffff:0:0/96` turned a `/96` into `0.0.0.0/0`. Deleting the rewrite removes the bug's cause rather than ordering around it. What remains is pure code motion, verified identical to the previous implementation across every combination of 37 allow-list values and 21 peer addresses — zero parse differences, zero match differences. The wart it declined to fix (a mapped-form entry matches nothing) is the pre-existing behaviour, fails closed, and is now stated in the function's own comment so the next person does not re-derive the same tempting fix.

**The one residual risk worth naming.** The default mode's *code path* did change: there is now a switch and a function call in front of the original body. If that plumbing were wrong it would affect everyone, not just opt-in users. The parity testing above is why we believe it is not, but "verified equivalent over 21 cases" is a different claim from "provably identical", and the honest version is the former.

## What adversarial review found {#review}

An independent agent was tasked with breaking the first implementation. It found four real defects, all since fixed and covered by regression tests.

**A silent fail-open, and the worst of the four.** The trust policy was read in the package's `init()`. But `loadEnvVarsFromFiles()` calls `os.Setenv` for everything in `MINIO_CONFIG_ENV_FILE` long afterwards — which is how MinIO is configured in essentially every packaged deployment. An operator putting `MINIO_API_TRUSTED_PROXIES` in `/etc/default/minio` would have got the historical trust-any-peer mode, with no error reported, and a malformed value would have been silently ignored rather than fatal. The policy is now applied in `serverHandleEnvVars`, which runs after the file load and before any listener.

**Loopback skipped as a chain entry.** Described above: the peer exemption was being reused as a hop exemption, which is a needless instance of the broad-list problem. Now two separate checks.

**Two fail-closed correctness bugs.** A zoned IPv6 peer (`fe80::1%eth0`) canonicalised to nothing, because `net.ParseIP` rejects zones — so such a peer could never be a trusted proxy. And an allow-list entry written in IPv4-mapped form (`::ffff:192.168.1.10`) was accepted at startup and then matched nothing at all, since `netip.Prefix.Contains` is false across differing bit widths.

Two further defects were found while writing the documentation rather than the code, which is its own small lesson:

**Repeated header lines.** `Header.Get` returns only the *first* header line. HAProxy's `option forwardfor` **adds a second `X-Forwarded-For` line** rather than extending the first, so `Get` would hand back the client's line and put the forged value right back where the right-to-left walk exists to avoid it. Now flattened across all lines with `Header.Values`.

**The internal forwarder relayed client claims.** `internal/handlers/forwarder.go` set `X-Real-IP` only when absent, so a client's value passed between nodes unchanged. Under an allow-list that includes the cluster's own nodes — the configuration we recommend — a client could thereby borrow a peer node's authority. The forwarder now drops `X-Real-IP` and `Forwarded` when the incoming peer is not entitled to have set them. `X-Forwarded-For` needs no such handling, because Go's `ReverseProxy` appends the true peer and the receiving node's walk reaches that entry first.

### A second round, after the rework {#review-round-two}

Reworking the setting warranted a second adversarial pass, which was worth running: differential testing found **zero** behavioural differences against `HEAD` across 4,745,520 source-IP resolutions and 345,600 forwarder rewrites, but it also found three more ways to fail open — one of them introduced by the first round's own fix.

**A catch-all smuggled in as an IPv4-mapped prefix.** `MINIO_API_TRUSTED_PROXIES=::ffff:0:0/96` is a `/96` as written, so it passed the catch-all check; the rewrite that unmapped IPv4-mapped entries then turned it into `0.0.0.0/0`, trusting every peer. The first fix moved the breadth check to the far side of the rewrite. The eventual fix deleted the rewrite, once it became clear it was unreachable by any real request — which removes the cause instead of guarding its output.

This is the one most worth dwelling on. The fail-open was manufactured by a fix for an unrelated fail-*closed* bug, and the fix for the fail-open was a reordering that left the manufacturing step in place. Two rounds of correction, both defensible, neither addressing the fact that the code should not have been there. Hardening changes deserve the same adversarial treatment as the code they harden, and "is this reachable at all?" belongs near the front of that treatment.

**A deliberate value naming nobody.** `MINIO_API_TRUSTED_PROXIES=","` parsed to an empty list and fell back to the permissive default. An empty *unset* variable must mean "default", but a value the operator actually typed which names no proxy is a mistake, and answering it with trust-everyone is the one behaviour they cannot have wanted. It is now a startup error. Whitespace-only remains equivalent to unset, since that is what an empty shell variable expands to.

**A remote value that could not be read.** MinIO supports `env://` indirection, where a variable's value is fetched from a remote webhook. `env.Get` **discards** the error from that fetch and returns the empty string — which this code would have read as "unset", reinstating trust-any-peer at exactly the moment the operator's intent could not be determined. The setting is now read through `env.LookupEnv` so the error is surfaced and startup stops. This is a general hazard for any security-relevant setting read via `env.Get`, and worth remembering beyond this change.

### A third pass, attacking from angles the first two shared {#review-round-three}

Both earlier passes attacked the resolver as a unit. Two things that neither could see:

**Nothing had tested that the trust policy reaches a decision.** Every test to that point checked what the resolver returned, and the one test at the policy layer only asserted that `aws:SourceIp` *equalled* the resolver's output — in the default mode. So a version where the resolver was correct but the policy engine read something else would have passed everything. There is now a test that drives a forged `X-Forwarded-For` through `getConditionValues` into a real `IpAddress` evaluation under each mode: believed by default, ignored under `none`, ignored from an unlisted peer, and still honoured from the listed proxy. It passes, but it should have existed before the change was called done.

**The allow-listed mode had a resource amplification the default mode does not.** The chain was flattened into a slice before being walked, so a client behind a trusted proxy could turn the 1 MiB header allowance into roughly 33 MB of slice headers per request — around thirty-fold — plus a million-iteration walk. The default path never had this, because it uses `strings.Index` on the raw header. The walk now scans backwards over the header text in place, allocating nothing, and stops after 100 hops; real chains are a handful, the answer sits at the right-hand end, and running out of budget yields no address, which falls back to the peer. A test pins the zero-allocation property, because it is the kind of thing an innocent-looking refactor would undo.

Also corrected in this pass: the deployment contract was stated too narrowly. "The proxy must overwrite whichever headers it sets" misses the case that actually bites — a proxy that correctly authors only `X-Real-IP` or only `Forwarded` still relays the client's `X-Forwarded-For`, and that is the header read first. The general rule, now stated as such, is to strip every source-address header the proxy does not itself write.

One reported finding was reviewed and **not** treated as a defect: the catch-all guard rejects `/0` and nothing else, so `0.0.0.0/1,128.0.0.0/1` covers the same ground and is accepted. Tightening it would mean rejecting broad-but-not-`/0` prefixes in the parser now shared with the LDAP allow-list, newly failing configurations that are valid today, to defend against a value no deployment realistically holds. The documentation states plainly that the check is a guardrail rather than a proof, and the callout about naming proxies instead of subnets is where the real defence lives.

## Recommendations {#recommendations}

By topology:

- **Proxy you control, API port genuinely unreachable otherwise.** Set nothing. But verify whether your proxy overwrites or appends: if the config says `$proxy_add_x_forwarded_for`, you are forgeable today. Switch to `$remote_addr`, or adopt the allow-list.
- **Direct exposure, no proxy.** `MINIO_API_TRUSTED_PROXIES=none`.
- **Kubernetes or Pigsty, Ingress plus reachable Service.** The allow-list, containing the proxy addresses *and* the MinIO node addresses. This is the configuration that makes an `IpAddress` condition mean anything.
- **Any multi-node cluster.** The allow-list with node addresses, not `none`.

Two rules apply to every allow-list deployment. Name proxies, not the subnet they occupy. And **strip at the edge every source-address header your proxy does not itself write** — listing a peer means believing all three headers from it, they are consulted in a fixed order, and a header your proxy leaves alone is entirely the client's. A proxy that correctly authors only `X-Real-IP`, or only `Forwarded`, still relays the client's `X-Forwarded-For`, which is read first.

## What was not done {#not-done}

- **Automatic seeding of cluster node addresses.** Feasible via `EndpointServerPools`, but it needs DNS resolution and re-resolution on address changes. Explicit configuration was judged the smaller risk.
- **Registration as an `api` config key.** See the fail-open window above. Revisitable if observability turns out to matter more than the startup guarantee.
- **`ExistingObjectTag/*`.** The sibling defect from the condition-value hardening — it carries the request's own tags rather than the object's stored tags — remains open by decision, and is unaffected by any of this.

## Verdict on severity {#severity}

Default behaviour matches upstream, and MinIO has never documented `aws:SourceIp` as trustworthy on a directly-reachable deployment, so "the default is unsafe" is closer to a documentation defect than a vulnerability. One thing is squarely a defect, though: **an operator set an explicit security switch and it did not do what its name and its only public description implied**, and it failed silently. That is worth a record, scoped to the incompleteness of upstream's `_MINIO_API_XFF_HEADER` rather than to anything the fork introduced.

`minio/minio` is archived, so there is no upstream to coordinate with — the same position as [CVE-2026-42600](/blog/security/cve-2026-42600/).
