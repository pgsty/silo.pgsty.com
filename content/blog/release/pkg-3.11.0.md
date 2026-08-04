---
title: "silo-pkg 3.11.0 Released"
linkTitle: "silo-pkg 3.11.0 Released"
date: 2026-08-04
author: "Vonng"
description: "The fork's first pinned release restores the IAM bucket/object resource boundary that let an object-only grant reach bucket-level writes, fixes a policy condition-key bypass and three LDAP connection defects, and renumbers onto upstream's 3.11 line after the earlier tags were found to collide with upstream releases of the same numbers."
tags: [Release, pkg]
weight: 5
url: "/blog/release/pkg-3.11.0/"
aliases:
  - /blog/pkg-3.11.0/
  - /releases/pkg-3.11.0/
---

**Release date:** 2026-08-04 · **Version:** [v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) · **Commit:** [`d8b1fa7`](https://github.com/pgsty/silo-pkg/commit/d8b1fa7) · **Repository:** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

This is the fork's **first pinned release**. It restores the IAM bucket/object resource boundary reported as upstream [minio/minio#20449](https://github.com/minio/minio/issues/20449): a policy condition-key bypass fix, three LDAP connection defects, a certificate watcher leak, a seeded-RNG defect, and the module's real minimum Go version.


{{% alert color="warning" %}}
**Two things to check before upgrading**

1. **This release tightens authorization.** Twelve bucket-level write actions are no longer reachable through an object-only resource pattern such as `arn:aws:s3:::bucket/*`. If you write your own bucket-scoped policies, read [The IAM bucket/object boundary](#bucket-boundary) — the fix is one line of policy for anyone affected, and `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` restores the previous behaviour in full.
2. **The condition-key fix still needs its server half.** The policy lookup change and the server changes that reserve internal condition-key names each cover one half of that problem. The companion server work exists in `pgsty/minio` commit `2f55347f7` but is not yet on public `origin/master`, and no published Silo server release contains it. Verify that a later server release explicitly includes it.
{{% /alert %}}

## What This Repository Is {#what-is-this}

`silo-pkg` is a maintained fork of [minio/pkg](https://github.com/minio/pkg), carrying fixes needed by community MinIO forks that the now commercially driven upstream no longer accepts. The repository was renamed from `pgsty/minio-pkg` on 2026-08-02.

The **module path intentionally remains unchanged** as `github.com/minio/pkg/v3`. Existing `import "github.com/minio/pkg/v3/..."` statements do not change; only the right-hand side of the `replace` directive does:

```go
replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.11.0
```

The `/v3` suffix is the module's major version, not a directory name, and must not be omitted. It is also why this release is numbered `v3.11.0` rather than `v4.0.0`: Go requires the major version of a tag to match the major-version suffix declared in `go.mod`, so a `v4.0.0` tag on a `.../v3` module is rejected by the toolchain. Publishing a real `v4` would mean changing the module path and rewriting roughly 395 import sites across the server, `mc` and Console — abandoning the drop-in property that is the point of keeping upstream's path.

## The IAM Bucket/Object Boundary {#bucket-boundary}

Every bucket-level S3 operation authorizes with an empty object name. The IAM matcher turned that into a resource string and, for the empty-object case, appended a trailing slash:

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object"
} else {
    resource.WriteByte('/') // "bucket/"  <-- the defect
}
```

`"bucket/"` is matched by the wildcard pattern `"bucket/*"`, because `*` matches the empty string. A policy granting `s3:*` on `arn:aws:s3:::bucket/*` — which reads as *"anything, but only on the objects in this bucket"* — therefore also authorized bucket-level actions. In a multi-tenant cluster, a tenant holding only that grant could call `PutBucketPolicy` and install `{"Principal":"*"}`, making the bucket publicly readable or writable, or grant itself bucket-level control. It could also delete the bucket outright, which is the reproduction in the upstream issue.

The bucket-policy evaluation path used for anonymous access never had this slash and was already reference-correct. Only the IAM path was wrong, in exactly one place.

### Why not correct the whole boundary {#why-narrow}

Removing the slash for every bucket-level request is the obvious fix, and upstream tried it: the change was reverted the same day for breaking policies that relied on the old behaviour. Two properties make the full correction a migration rather than a patch.

**It revokes grants real deployments depend on.** It does not only revoke the dangerous bucket writes — it also revokes `ListBucket`, `GetBucketLocation` and `ListBucketMultipartUploads` when granted through `bucket/*`. The evidence is upstream's own test suite: eleven STS integration tests grant `s3:ListBucket` on `bucket/*` and then assert that listing works. If the project that wrote the server writes it that way, production policies do too.

**It cuts both directions.** The matcher builds the same resource string for `Allow` and `Deny`, so removing the slash tightens over-granting `Allow` statements *and simultaneously loosens over-blocking `Deny` statements*. An administrator who locked a bucket with `Deny s3:* on bucket/*` would silently lose that protection.

### How the protected set was chosen {#protected-set}

The scope was decided by one question: **does reaching this action give the caller something its object-scoped grant does not already provide?**

That question is the right one because of how the defect fires. Resource matching runs *after* action matching, so the bug only bites when the statement already grants the bucket-level action — which in practice means `s3:*`. The affected principal therefore already holds full read, write and delete over every object in the bucket. The useful question is not how dangerous an action sounds in the abstract, but what reaching it adds to a position that already includes all of the data.

**Withheld from object-only grants (twelve actions):**

| Action                                                                           | Why it qualifies                                                                                                                                                                                         |
|:---------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `PutBucketPolicy`, `DeleteBucketPolicy`                                          | Hand access to other principals, anonymous included, and can grant the caller bucket-level actions it was never given. Self-escalation and public exposure.                                              |
| `PutBucketObjectLockConfiguration`, `PutBucketVersioning`                        | Defeat protections that exist precisely to stop a holder of write access from destroying data.                                                                                                           |
| `PutReplicationConfiguration`, `PutLifecycleConfiguration`                       | Act under server credentials and keep acting after the caller's access is revoked.                                                                                                                       |
| `DeleteBucket`, `ForceDeleteBucket`                                              | Destroy the bucket entity and its configuration irreversibly. The reproduction in the upstream issue.                                                                                                    |
| `PutBucketCors`, `DeleteBucketCors`, `PutBucketQOS`, `PutInventoryConfiguration` | No server behaviour is attached to these today — no handler at all, or a handler that returns `NotImplemented` after the authorization check. Withholding them costs nothing and covers them in advance. |

**Deliberately not withheld**, and asserted by a test so that adding one is a deliberate act with a visible cost rather than an edit to a list:

- **`PutBucketTagging`, `PutBucketEncryption`, `PutBucketNotification`.** These are bucket-level writes and an earlier draft did withhold them. None gives the caller access it does not already hold — the harm is to the owner's posture, not to the access boundary — while a tenant handed `s3:*` on `bucket/*` and told the bucket is theirs may quite reasonably tag it, set default encryption, or wire up event notifications. Low security gain against a real compatibility cost is the wrong trade for a maintenance release.
- **`CreateBucket`.** It targets a bucket that does not exist yet, so there is nothing to mutate or destroy, and provisioning flows commonly create a tenant's bucket with that tenant's own `bucket/*` credentials.
- **The read/list family** (`ListBucket`, `GetBucketLocation`, the configuration reads). Breaking these is what got upstream's own attempt reverted. They wait for a migration-gated release.

Only `Allow` statements are affected. `Deny` statements keep the historical resource string, so no bucket lock is ever weakened, and `NotResource` exclusions keep their full reach.

### Monotonicity, and the claim that was wrong twice {#monotonicity}

All of the above rests on one property: **this change may remove permissions and must never add one.** That property was asserted twice from reasoning rather than from tests, and was false both times. Recording how is more useful than recording only the final state.

The first attempt let the withheld slash reach the **`NotResource`** match as well — and `NotResource` is an *exclusion*. An `Allow s3:* NotResource bucket/*` statement historically did not apply to bucket-level requests on that bucket; matching the exclusion against the bare bucket name made it stop matching, so the `Allow` it qualified grew, for exactly the writes being protected.

The second attempt fixed that and shipped saying the result was provably monotone. An independent adversarial review of that release produced a counterexample. Withholding the slash does not merely remove a match — it changes *which string patterns are matched against*, and a pattern can match `"mybucket"` without ever having matched `"mybucket/"`. A fixed-width wildcard is the clean case:

```
Allow s3:PutBucketPolicy on arn:aws:s3:::mybucke?
```

`?` matches exactly one character. Against the nine-character `"mybucket/"` it does not match, so this statement never authorized the bucket-level write. Against the new eight-character `"mybucket"` it does, so the hardening *granted* something the buggy matcher refused.

The fix is not another special case. On the protected path the matcher now requires **both** forms to match — the bare bucket name *and* the historical `"bucket/"`. The result is an intersection with the historical decision, so it is monotone **by construction**: there is no pattern it can newly satisfy, and no argument left to get wrong. `mybucket*` still grants (it matched both all along), `mybucket/*` is still withheld, and `mybucke?` is refused exactly as it always was.

Two lessons are worth carrying forward. **A correctness fix in an authorization path must never make anything newly allowed** — and the only way to know is to test both directions, because the reasoning felt airtight in both cases where it wasn't. And when a security property is load-bearing, **build it out of an operation that cannot violate it** rather than out of a case analysis believed to be complete.

### Evidence {#bucket-boundary-evidence}

The property is verified rather than argued. A decision corpus of **27,000 authorization outcomes** — 15 resource patterns × 3 buckets × 5 object names × 20 actions × 6 statement forms — was generated against both the pre-hardening baseline and this release and compared entry by entry:

| Transition                  |  Count |
|:----------------------------|-------:|
| `false → true` (broadening) |  **0** |
| `true → false` (narrowing)  |    144 |
| unchanged                   | 26,856 |

Every one of the 144 narrowed outcomes falls inside the design intent, with nothing outside it: exactly the twelve protected actions; only the three `Allow` statement forms, with zero transitions for `Deny`, `NotResource`-excluded or deny-`NotResource` forms; only four object-only resource patterns; and only bucket-level requests, with object-level requests entirely untouched. 12 × 4 × 3 = 144, fully accounted for.

Regression coverage exists at both layers. In this repository, twelve matcher tests pin each direction, including an invariant test that every protected action really is bucket-only — `ResetBucketReplicationState`, despite its name, is an object action and stays out. In the server, three end-to-end tests drive the real handlers at the client, inline-session-policy and S3-router levels; all three fail against the pre-fix build and pass against this one.

### What to change {#bucket-boundary-upgrade}

You are affected only if a stored policy grants one of the twelve actions — or `s3:*` — on a resource pattern containing `/`, with no bare bucket ARN for the same bucket. The fix is to add the bare ARN alongside the object pattern:

```json
"Resource": ["arn:aws:s3:::bucket", "arn:aws:s3:::bucket/*"]
```

That pairing is the conventional form, is what upstream's own tests use, and worked before this release as well. Built-in canned policies are unaffected — `readwrite`, `readonly`, `writeonly` and `diagnostics` all use `Resource: "*"`.

`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`, read once at startup, restores the historical matching in full — both the over-granting and the over-blocking. It is a single global switch; per-action scoping is [deferred](#deferred).

## Policy Condition-Key Lookup Order {#policy-condition-key}

`getValuesByKey()` previously looked up a policy condition key by its canonical MIME spelling (`http.CanonicalHeaderKey`) before trying the original name. The map it reads mixes values calculated by the server for the current request (`SourceIp`, `SecureTransport`, `CurrentTime`, `username` and others, stored under condition-key spellings) with HTTP headers supplied by the request (stored under canonical MIME spellings).

**Checking the canonical spelling first allowed a client header to override a value calculated by the server.**

For a MinIO server this is a policy bypass. The simplest example is `s3:prefix`: a `Prefix` request header could satisfy a home-directory prefix condition while the real `?prefix=` query parameter still listed the entire bucket. The same path reached `aws:SourceIp`, `aws:SecureTransport`, `aws:CurrentTime`, `aws:EpochTime`, `aws:username`, `aws:userid`, `aws:principaltype`, `aws:UserAgent`, `aws:groups`, `ldap:username`, `ldap:groups`, `jwt:groups`, `s3:versionid`, `s3:signatureversion`, `s3:signatureAge`, `s3:authType` and `s3:LocationConstraint`. Anonymous bucket policies were directly exposed. SigV4 did not prevent the attack because a client can add a header that is not listed in `SignedHeaders`.

There was a second consequence: when the server stored a value under one spelling and the policy key resolved another, the wrong entry won. `s3:object-lock-mode` could resolve to the caller's `X-Amz-Object-Lock-Mode` header rather than the retention mode the server would actually apply.

The fix reverses the lookup order: match the condition key's exact name first, then use the canonical spelling only as a fallback for condition keys that genuinely name request headers, such as the `s3:x-amz-*` family. This ports [minio/pkg#226](https://github.com/minio/pkg/pull/226) and adds regression coverage the upstream change did not carry.

At the library's raw-map layer, if a producer stores one logical field under both the exact condition name and its canonical MIME name, the exact name now wins. This is a library lookup rule, not an S3 wire-protocol rule that says query parameters take precedence. The Silo server first normalizes condition values by their real source. For storage class and upload tagging, where both Header and query forms remain compatible, **Header presence wins, including an empty value**; query is only the fallback.

## LDAP Connection Path {#ldap}

Three defects in `connect()`. Two were introduced by this fork in `b0c08a7` and shipped in v3.6.2 and v3.6.3. **Users of either release should upgrade promptly.**

**StartTLS was skipped when `ServerInsecure` was enabled.** Upstream called `StartTLS` in an outer block controlled only by `ServerStartTLS`, so enabling both options created a plaintext connection and then upgraded it. `b0c08a7` moved the call into an `else` branch, making StartTLS unreachable whenever `ServerInsecure` was true. The connection stayed plaintext and the following bind sent credentials over it. MinIO exposes `MINIO_IDENTITY_LDAP_SERVER_INSECURE` and `MINIO_IDENTITY_LDAP_SERVER_STARTTLS` independently and `Validate()` rejects no combination, so this state was reachable.

This release restores the upstream semantics: the two switches are **additive, not mutually exclusive**. `ServerInsecure` disables implicit `ldaps://`; `ServerStartTLS` still performs the upgrade. The exposure window is limited to v3.6.2 and v3.6.3.

**A Config without a TLS section could panic on the `ldaps://` path.** After `l.TLS.Clone()` moved outside the StartTLS branch, ordinary `ldaps://` connections also called it. `Clone()` returns nil for a nil receiver, but the next line assigned `ServerName`. The MinIO server always supplies TLS settings, but this is a library and `mc` also consumes it. The code now falls back to an empty `tls.Config`, matching what `DialURL` would have built.

**StartTLS had no deadline.** go-ldap only starts its request timer when `requestTimeout > 0`, while `StartTLS` itself has no timeout. A server that completed TCP setup and then stopped responding to the extension request could hold the connect goroutine forever. The timer is now armed before `StartTLS`.

**A failed StartTLS leaked the connection.** Inherited from upstream. Dial failures do not return a connection, making StartTLS failure the only `connect()` path that could return both a connection and an error. Callers only took ownership when the error was nil, leaving a socket behind for every login attempt against a server with a broken upgrade. The failure path now closes the connection and returns nil.

## Other Fixes {#other-fixes}

- **certs: file watchers were never stopped.** `Manager.AddCertificate()` registered two `notify.Watch()` calls and stopped neither: if the second failed, the first leaked, and both survived until process exit after the manager closed. `Certificate.Watch()` and `watchFile()` had the same problem. All four paths now use `watchDirSafe()`, which returns a stop function invoked on errors and `ctx.Done()`. This ports the `certs/` part of [minio/pkg#228](https://github.com/minio/pkg/pull/228). On Windows the function replaces filesystem notification with polling rather than using polling only as a failure fallback, so certificate reload can lag by one `symlinkReloadInterval` (10 seconds). This fork has no Windows CI; that platform was only cross-compiled.
- **rng: reader subkeys came from a zeroed local variable.** `init()` read 32 bytes of entropy into `r.tmp` but derived four subkeys from a same-named zeroed local, collapsing four per-block streams into one. `Reset()` and `ResetSize()` then replayed the previous stream byte for byte. MinIO creates a new reader for each `randreader.New()` call and never resets it, so the practical server impact is limited; warp exposed the defect. This ports [minio/pkg#230](https://github.com/minio/pkg/pull/230).
- **xtime: `Duration` implemented `UnmarshalJSON` but not `MarshalJSON`.** Encoding produced an integer number of nanoseconds while decoding unconditionally stripped the first and last byte and expected a quoted string, so neither direction could round-trip. It now encodes using `time.Duration`'s string form. This ports [minio/pkg#242](https://github.com/minio/pkg/pull/242).

## Compatibility Impact {#compatibility}

- **Twelve bucket-level write actions are no longer authorized through an object-only resource pattern.** See [What to change](#bucket-boundary-upgrade). Object access, `ListBucket`, `CreateBucket`, bucket tagging, default encryption and event notification are all unaffected, as are `Deny` statements and `NotResource` exclusions.
- **The minimum Go version moves from `1.26.1` down to `1.25.0`.** A patch number in the `go` directive is a hard minimum for every consumer, not a record of the toolchain used to build the module. The conventional split is a language version on the `go` line and a development version on a separate `toolchain` line. `1.25.0` is what the dependency graph actually requires and what upstream declares. CI builds the complete test suite with Go 1.25 under `GOTOOLCHAIN=local`, so the minimum is proven rather than aspirational.
- **The JSON wire format of `xtime.Duration` changes** from a nanosecond integer to a duration string such as `"2h"` or `"30m"`. Persisted numeric values can no longer be read back. No such use was found in MinIO or `mc`: batch job definitions persist as YAML and the msgp path remains int64.
- **Deployments with both `ServerInsecure` and `ServerStartTLS` enabled whose LDAP server does not support StartTLS** connected successfully in plaintext on v3.6.2/v3.6.3 and now fail to connect. That is the correct result, but it surfaces during connection rather than configuration validation. Disable `ServerStartTLS` for such a server.
- **`Policy.IsAllowedActions` can disagree with a direct decision for the twelve protected actions.** It enumerates `SupportedActions`, which includes the `s3:*` pattern itself, so the returned set can contain `s3:*` — and therefore appear to permit a protected action — while the direct evaluation denies it. Nothing in the server calls it, and Console calls it with an empty bucket name, which never reaches the hardened branch. Recorded rather than changed, because altering a public API's output in a maintenance release is the larger risk.

## Divergence from Upstream v3.11.0 {#divergence}

The version number follows upstream's line and makes no claim of identical content. The measured delta, comparing action-string constants across `policy/`:

|                              | Count |
|:-----------------------------|------:|
| Upstream `minio/pkg` v3.11.0 |   291 |
| `silo-pkg` v3.11.0           |   270 |

**24 actions exist only upstream:** six `s3:*ObjectAnnotation*` actions, five `admin:` actions (`DistJobStatus`, `Get`/`SetBucketCompression`, two `TablesReplication*`), and thirteen `s3tables:` actions covering function CRUD and tagging. These belong to the AIStor vocabulary this fork deliberately does not carry, because the community server does not implement them.

**Three actions are named differently on each side.** Upstream renamed and split these; this fork retains the earlier names:

| `silo-pkg` v3.11.0             | upstream `minio/pkg` v3.11.0                                 |
|:-------------------------------|:-------------------------------------------------------------|
| `s3tables:TagResource`         | `s3tables:TagTable`, `s3tables:TagWarehouse`                 |
| `s3tables:UntagResource`       | `s3tables:UntagTable`, `s3tables:UntagWarehouse`             |
| `s3tables:ListTagsForResource` | `s3tables:ListTagsForTable`, `s3tables:ListTagsForWarehouse` |

A policy naming any of these six action strings therefore validates on exactly one of the two. Nothing in the Silo server, `mc` or Console references them, so there is no impact inside this ecosystem — but a consumer swapping upstream v3.11.0 for this release should know the vocabulary is not interchangeable.

**rng has no arm64 assembly.** Upstream added `rng/xor_arm64.{go,s}` after this fork's divergence point; this release falls back to the pure-Go `xor_noasm.go` path on arm64. The result is correct and cross-compiles cleanly, but slower than upstream on that architecture. It is a clean candidate for a future sync, being a pure performance change with no vocabulary entanglement.

## Companion Server Behavior {#server-side}

- The condition-key change in this release **must** be paired with the server changes that reserve internal condition-key names and populate values by semantic source, as noted at the top.
- `s3:signatureAge` is exposed only after the SigV4 presigned-request verifier calculates it. A client-supplied `x-amz-signature-age` Header is ignored on every other request type.
- `s3:prefix`, `s3:delimiter` and `s3:max-keys` come only from query parameters. Content hash, copy source, metadata directive, SSE and object-lock conditions come only from the corresponding headers. The `X-Amz-Content-Sha256` query value consumed while verifying a presigned request does not become a policy condition.
- `s3:x-amz-storage-class` retains its compatible query form, as do request tags on `PutObject` and `CreateMultipartUpload`. For both fields, Header presence wins and query is used only when the Header is absent.
- `s3:ExistingObjectTag/*` comes only from tags loaded from the stored object, so a request's own `X-Amz-Tagging` can no longer impersonate existing object state. `PutObject`, `CreateMultipartUpload` and `PutObjectTagging` bind `s3:RequestObjectTag/*` to the tag input those handlers consume. Other action paths retain the historical `X-Amz-Tagging` Header fallback for compatibility, so treat request-tag conditions as constraints only where the API actually consumes tags.
- `aws:SourceIp` is calculated from forwarding headers. Whether it is enforceable depends on the server's trusted-proxy configuration; see the server's own release notes for `MINIO_API_TRUSTED_PROXIES`.

## Verification {#verification}

Everything below was run against the tagged commit, with the working tree clean and the tag pointing at `HEAD`:

- `make test` — golangci-lint plus `go test -race -tags kqueue ./...`, all packages passing.
- `go mod tidy -diff` clean; `gofmt -l` empty; `go vet ./...` clean.
- Cross-compilation for `linux/amd64`, `linux/arm64`, `darwin/arm64` and `windows/amd64`.
- `govulncheck ./...` — zero reachable vulnerabilities. One module-level notice remains, GO-2026-5932 in `x/crypto/openpgp`; that package is unmaintained, has no fixed version, and this repository does not import it.
- Resolution from an empty module cache through the public proxy, confirming the release is fetchable as published.
- The 27,000-outcome authorization corpus described [above](#bucket-boundary-evidence).

## Dependencies and Tooling {#deps-and-tooling}

Dependency updates clear nine **reachable** findings previously reported by `govulncheck`: seven `x/crypto/ssh` issues reached through `sftp`, GO-2026-6061 in gRPC reached through etcd, and GO-2026-4945 in go-jose reached through oidc.

Five dependencies — `minio-go`, `minio/mux`, `etcd client/v3`, `go-oidc` and `lestrrat-go/jwx` — were deliberately not upgraded. MinIO consumes this module through `replace`, and Minimal Version Selection chooses the highest version in the entire graph, so upgrading them here would also pull the server forward. None has a reported vulnerability requiring that change.

All three workflows previously asked `setup-go` for a Go version lower than `go.mod` required and failed on the first Go command; they are now aligned. The linter also fetched an installer from the master branch and reinstalled it on every run. The URL and version are now pinned to `v2.11.3`, and a matching installed version skips the download.

## Changes Deliberately Not Taken from Upstream {#not-taken}

- AIStor policy vocabulary (Memory/cortex, Tables/Iceberg, KMS, compression and annotations) and the typed action-constant refactor, none of which the community server implements. This is the source of the [action-vocabulary delta](#divergence).
- `securityAuditAdmin`, which grants `admin:ExportIAM` and therefore exposes every secret key despite what the name suggests.
- rng AVX2/NEON assembly. Revisiting the arm64 half is noted above as a future sync candidate.
- `net.BandwidthBytesPerSec` (declared but never read upstream), `replicationAdmin` and `DistJobStatusAction`.
- Two changes initially taken and removed after review: the `consolereadonly` built-in policy and `GetAllGlobalCertificates`. Neither has a consumer. Once operators bind a built-in policy name to users, withdrawing it is particularly unsafe: policy mappings persist by name, and an unresolved name merges into an empty policy that denies everything. Its inherited `admin:CreateUser` Deny also cannot be combined with `iamAdmin`. The certificate helper inventoried a cache the community server never populates.
- Upstream's golangci-lint `tool` directive, which would add roughly 200 linter dependencies to every downstream consumer's module graph.

## Deliberately Deferred {#deferred}

The general problem in minio/minio#20449 — that `bucket/*` still reaches `ListBucket`, `GetBucketLocation`, the configuration reads, `CreateBucket` and the three tenant-plausible writes — is **not** closed here. Closing it means revoking grants real deployments depend on, so it belongs to a release that carries a migration path.

What that release owes operators is more than a longer action list, because no one can enumerate every deployment's stored policies — which puts a hard ceiling on any approach that picks the protected set by guessing. Three things raise it:

- **A startup policy audit** that walks stored policies and names each one whose meaning changes, in both the grant and the deny direction. It is read-only and can ship *before* the enforcement change rather than with it, turning an upgrade surprise into a pre-upgrade checklist.
- **A denial that explains itself.** When a request is refused because only an object-scoped grant matched, say so and name the compatibility switch. A break an operator can diagnose in thirty seconds costs an order of magnitude less than a silent one.
- **A switch with a scope.** `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH` is all-or-nothing today, so an operator who needs one action back must reopen the self-escalation path along with it.

## Related Commits {#related-commits}

- [d8b1fa7](https://github.com/pgsty/silo-pkg/commit/d8b1fa7): fix(policy): settle the bucket-write hardening's scope and monotonicity
- [1f97549](https://github.com/pgsty/silo-pkg/commit/1f97549): fix(policy): extend the bucket-write hardening to every bucket-only write
- [3c24ad1](https://github.com/pgsty/silo-pkg/commit/3c24ad1): fix(policy): withhold object-only grants from sensitive bucket writes
- [da6a22a](https://github.com/pgsty/silo-pkg/commit/da6a22a10143f2e23764c59f39306e9ac3282da5): docs: say what this fork is and how to depend on it
- [4055b2f](https://github.com/pgsty/silo-pkg/commit/4055b2f7d5a33948004ac13a933aa978b57399e6): fix(xtime): marshal Duration as a duration string
- [13c26cd](https://github.com/pgsty/silo-pkg/commit/13c26cda3db1e36bb3b7904217271a32b73039b7): fix(rng): initialize the reader subkeys from the seeded entropy
- [88b37ac](https://github.com/pgsty/silo-pkg/commit/88b37ace8a14a511e09b9b30567cde8e5bfa2398): fix(certs): stop file watchers on every exit path
- [74dd36e](https://github.com/pgsty/silo-pkg/commit/74dd36e78a829782b6f04ad09fd908386e13c693): fix(ldap): keep StartTLS when ServerInsecure is also set
- [424c3d0](https://github.com/pgsty/silo-pkg/commit/424c3d06057b579631a4a8a81ffae9985875f477): fix(ldap): close the connection when StartTLS fails
- [045d10f](https://github.com/pgsty/silo-pkg/commit/045d10fd974760153024cd7d519919440c28c5cb): fix(ldap): guard a nil TLS config and arm the StartTLS deadline
- [5c4bf50](https://github.com/pgsty/silo-pkg/commit/5c4bf503d5d5701327527f030a3c755266d741f1): fix(policy): prefer the exact key name over the canonical header form
- [802539f](https://github.com/pgsty/silo-pkg/commit/802539f36d723802c80dea3c18c88da33c5d87d4): chore(deps): refresh the dependency set and declare the real minimum Go
- [e4ec64a](https://github.com/pgsty/silo-pkg/commit/e4ec64a9453d9ad469f6fd4ece93b2462bd118ef): ci: build on the Go version go.mod requires, and prove the declared minimum
- [747d8b8](https://github.com/pgsty/silo-pkg/commit/747d8b865ca937f227b0f70aeec9f8b49d05f55d): build: pin the golangci-lint installer and skip a matching install
