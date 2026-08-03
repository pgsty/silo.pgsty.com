---
title: "silo-pkg 3.7.0 Released"
linkTitle: "silo-pkg 3.7.0 Released"
date: 2026-08-03
author: "Vonng"
description: "The first silo-pkg release under its new repository name fixes a policy condition-key bypass and three LDAP connection defects, and restores the module's actual minimum Go version."
tags: [silo-pkg, Silo, MinIO, release]
weight: 5
url: "/blog/release/pkg-3.7.0/"
aliases:
  - /blog/pkg-3.7.0/
  - /releases/pkg-3.7.0/
---

**Release date:** 2026-08-03 · **Version:** [v3.7.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.7.0) · **Repository:** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

This is the first `pgsty/silo-pkg` release under its new repository name. It fixes a policy bypass caused by condition-key lookup order, three defects in the LDAP connection path (two introduced by this fork in v3.6.2/v3.6.3), a certificate file-watcher leak, and restores the module's minimum Go version from `1.26.1` to the `1.25.0` it actually requires.

{{% alert color="warning" %}}
**The complete fix requires the matching server update**

The policy lookup change in this release and the server changes that reserve internal condition-key names and construct condition values from their real sources each cover one half of the problem. **Upgrading either side alone is incomplete.** Use a SILO server release that includes the [companion fix](https://github.com/pgsty/minio/commit/1a6d5b415f2e7e013a5339f6d60c3c6f371a1a03). See [Condition Value Sources and Precedence](/administration/identity-access-management/policy-based-access-control/#condition-value-sources) for the compatibility contract.
{{% /alert %}}

## What This Repository Is {#what-is-this}

`silo-pkg` is a maintained fork of [minio/pkg](https://github.com/minio/pkg), carrying fixes needed by community MinIO forks that the now commercially driven upstream no longer accepts. The repository was renamed from `pgsty/minio-pkg` on 2026-08-02.

The **module path intentionally remains unchanged** as `github.com/minio/pkg/v3`. Existing `import "github.com/minio/pkg/v3/..."` statements do not change; only the right-hand side of the `replace` directive does:

```go
replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.7.0
```

The `/v3` suffix is the module's major version, not a directory name, and must not be omitted. GitHub redirects the former repository name, but consumers should pin the new path directly.

Version numbers continue the upstream sequence so operators can see which upstream version a release is based on. That does **not** promise identical content: this fork omits changes that only serve closed-source products and carries fixes that upstream will not accept.

## Policy Condition-Key Lookup Order {#policy-condition-key}

`getValuesByKey()` previously looked up a policy condition key by its canonical MIME spelling (`http.CanonicalHeaderKey`) before trying the original name. The map it reads mixes values calculated by the server for the current request (`SourceIp`, `SecureTransport`, `CurrentTime`, `username`, and others, stored under condition-key spellings) with HTTP headers supplied by the request (stored under canonical MIME spellings).

**Checking the canonical spelling first allowed a client header to override a value calculated by the server.**

For a MinIO server this is a policy bypass. The simplest example is `s3:prefix`: a `Prefix` request header could satisfy a home-directory prefix condition while the real `?prefix=` query parameter still listed the entire bucket. The same path reached `aws:SourceIp`, `aws:SecureTransport`, `aws:CurrentTime`, `aws:EpochTime`, `aws:username`, `aws:userid`, `aws:principaltype`, `aws:UserAgent`, `aws:groups`, `ldap:username`, `ldap:groups`, `jwt:groups`, `s3:versionid`, `s3:signatureversion`, `s3:signatureAge`, `s3:authType`, and `s3:LocationConstraint`. Anonymous bucket policies were directly exposed. SigV4 did not prevent the attack because a client can add a header that is not listed in `SignedHeaders`.

There was a second consequence: when the server stored a value under one spelling and the policy key resolved another, the wrong entry won. `s3:object-lock-mode` could resolve to the caller's `X-Amz-Object-Lock-Mode` header rather than the retention mode the server would actually apply.

The fix reverses the lookup order: match the condition key's exact name first, then use the canonical spelling only as a fallback for condition keys that genuinely name request headers, such as the `s3:x-amz-*` family. This ports [minio/pkg#226](https://github.com/minio/pkg/pull/226) and adds regression coverage that the upstream change did not carry.

At the library's raw-map layer, if a producer stores one logical field under both the exact condition name and its canonical MIME name, the exact name now wins. This is a library lookup rule, not an S3 wire-protocol rule that says query parameters take precedence. The SILO server first normalizes condition values by their real source. For storage class and upload tagging, where both Header and query forms remain compatible, **Header presence wins, including an empty value**; query is only the fallback.

## LDAP Connection Path {#ldap}

This release fixes three defects in `connect()`. Two were introduced by this fork in `b0c08a7` and shipped in v3.6.2 and v3.6.3. **Users of either release should upgrade promptly.**

**StartTLS was skipped when `ServerInsecure` was enabled.** Upstream called `StartTLS` in an outer block controlled only by `ServerStartTLS`, so enabling both options created a plaintext connection and then upgraded it. `b0c08a7` moved the call into an `else` branch, making StartTLS unreachable whenever `ServerInsecure` was true. The connection stayed plaintext and the following bind sent credentials over that connection. MinIO exposes `MINIO_IDENTITY_LDAP_SERVER_INSECURE` and `MINIO_IDENTITY_LDAP_SERVER_STARTTLS` independently, and `Validate()` rejects no combination, so this state was reachable.

This release restores the upstream semantics: the two switches are **additive, not mutually exclusive**. `ServerInsecure` disables implicit `ldaps://`; `ServerStartTLS` still performs the upgrade. The exposure window is limited to v3.6.2 and v3.6.3.

**A Config without a TLS section could panic on the `ldaps://` path.** After `l.TLS.Clone()` moved outside the StartTLS branch, ordinary `ldaps://` connections also called it. `Clone()` returns nil for a nil receiver, but the next line assigned `ServerName`. The MinIO server always supplies TLS settings, but this is a library and `mc` also consumes it. The code now falls back to an empty `tls.Config`, matching what `DialURL` would have built.

**StartTLS had no deadline.** go-ldap only starts its request timer when `requestTimeout > 0`, while `StartTLS` itself has no timeout. A server that completed TCP setup and then stopped responding to the extension request could hold the connect goroutine forever. The timer is now armed before `StartTLS`.

**A failed StartTLS leaked the connection.** This was inherited from upstream. Dial failures do not return a connection, making StartTLS failure the only `connect()` path that could return both a connection and an error. Callers only took ownership when the error was nil, leaving a socket behind for every login attempt against a server with a broken upgrade. The failure path now closes the connection and returns nil.

## Other Fixes {#other-fixes}

- **certs: file watchers were never stopped.** `Manager.AddCertificate()` registered two `notify.Watch()` calls and stopped neither: if the second failed, the first leaked, and both survived until process exit after the manager closed. `Certificate.Watch()` and `watchFile()` had the same problem. All four paths now use `watchDirSafe()`, which returns a stop function invoked on errors and `ctx.Done()`. This ports the `certs/` part of [minio/pkg#228](https://github.com/minio/pkg/pull/228). On Windows the function replaces filesystem notification with polling rather than using polling only as a failure fallback, so certificate reload can lag by one `symlinkReloadInterval` (10 seconds). This fork has no Windows CI; that platform was only cross-compiled.
- **rng: reader subkeys came from a zeroed local variable.** `init()` read 32 bytes of entropy into `r.tmp` but derived four subkeys from a same-named zeroed local, collapsing four per-block streams into one. `Reset()` and `ResetSize()` then replayed the previous stream byte for byte. MinIO creates a new reader for each `randreader.New()` call and never resets it, so the practical server impact is limited; warp exposed the defect. This ports [minio/pkg#230](https://github.com/minio/pkg/pull/230).
- **xtime: `Duration` implemented `UnmarshalJSON` but not `MarshalJSON`.** Encoding produced an integer number of nanoseconds, while decoding unconditionally stripped the first and last byte and expected a quoted string, so neither direction could round-trip. It now encodes using `time.Duration`'s string form. This ports [minio/pkg#242](https://github.com/minio/pkg/pull/242).

## Compatibility Impact {#compatibility}

- **The minimum Go version moves from `1.26.1` down to `1.25.0`.** A patch number in the `go` directive is a hard minimum for every consumer, not a record of the toolchain used to build the module. The conventional split is a language version on the `go` line and a development version on a separate `toolchain` line. `1.25.0` is what the dependency graph actually requires and what upstream declares. CI now builds the complete test suite with Go 1.25 under `GOTOOLCHAIN=local`, so the minimum is proven rather than aspirational.
- **The JSON wire format of `xtime.Duration` changes** from a nanosecond integer to a duration string such as `"2h"` or `"30m"`. Persisted numeric values can no longer be read back. No such use was found in MinIO or `mc`: batch job definitions persist as YAML and the msgp path remains int64.
- **Deployments with both `ServerInsecure` and `ServerStartTLS` enabled whose LDAP server does not support StartTLS** connected successfully in plaintext on v3.6.2/v3.6.3 and now fail to connect. That is the correct result, but it surfaces during connection rather than configuration validation. Disable `ServerStartTLS` for such a server.

## Companion Server Behavior {#server-side}

- The policy change in this release **must** be paired with the server changes that reserve internal condition-key names and populate values by semantic source, as noted above.
- `s3:signatureAge` is exposed only after the SigV4 presigned-request verifier calculates it. A client-supplied `x-amz-signature-age` Header is ignored on every other request type.
- `s3:prefix`, `s3:delimiter`, and `s3:max-keys` come only from query parameters. Content hash, copy source, metadata directive, SSE, and object-lock conditions come only from the corresponding headers. The `X-Amz-Content-Sha256` query value consumed while verifying a presigned request does not become a policy condition.
- `s3:x-amz-storage-class` retains its compatible query form. Request tags on `PutObject` and `CreateMultipartUpload` do as well. For both fields, Header presence wins and query is used only when the Header is absent.
- `s3:ExistingObjectTag/*` comes only from tags loaded from the stored object, so a request's own `X-Amz-Tagging` can no longer impersonate existing object state. `PutObject`, `CreateMultipartUpload`, and `PutObjectTagging` bind `s3:RequestObjectTag/*` to the tag input those handlers consume, and unrelated query tagging is ignored. Other action paths retain the historical `X-Amz-Tagging` Header fallback for compatibility, so treat request-tag conditions as constraints only where the API actually consumes tags. See [Condition Value Sources and Precedence](/administration/identity-access-management/policy-based-access-control/#condition-value-sources) for the complete matrix.
- `aws:SourceIp` is calculated from `X-Forwarded-For`, `X-Real-IP`, and `Forwarded` without a trusted-proxy boundary. The first is enabled by default and the other two are unrestricted. An `IpAddress` condition is therefore **not enforceable** on a deployment that clients can reach directly. Put MinIO behind a reverse proxy that overwrites those headers.

## Dependencies and Tooling {#deps-and-tooling}

Dependency updates clear nine **reachable** findings reported by `govulncheck`: seven `x/crypto/ssh` issues reached through `sftp`, GO-2026-6061 in gRPC reached through etcd, and GO-2026-4945 in go-jose reached through oidc. One module-level notice remains, GO-2026-5932 in `x/crypto/openpgp`; that package is unmaintained, has no fixed version, and this repository does not import it.

Five dependencies—`minio-go`, `minio/mux`, `etcd client/v3`, `go-oidc`, and `lestrrat-go/jwx`—were deliberately not upgraded. MinIO consumes this module through `replace`, and Minimal Version Selection chooses the highest version in the entire graph, so upgrading them here would also pull the server forward. None has a reported vulnerability requiring that change.

All three workflows previously asked `setup-go` for a Go version lower than `go.mod` required and failed on the first Go command. They are now aligned. The linter also fetched an installer from the master branch and reinstalled it on every run; the URL and version are now pinned to `v2.11.3`, and a matching installed version skips the download. `make test` once again runs to completion.

## Changes Deliberately Not Taken from Upstream {#not-taken}

- AIStor policy vocabulary (Memory/cortex, Tables/Iceberg, KMS, compression, and annotations) and the typed action-constant refactor, none of which the community server implements.
- `securityAuditAdmin`, which grants `admin:ExportIAM` and therefore exposes every secret key despite what the name suggests.
- rng AVX2/NEON assembly. This path is already faster than any disk and the change cannot be validated on this project's hardware and CI.
- `net.BandwidthBytesPerSec` (declared but never read upstream), `replicationAdmin`, and `DistJobStatusAction`.
- Two changes that were initially taken and removed after review: the `consolereadonly` built-in policy and `GetAllGlobalCertificates`. Neither has a consumer. Once operators bind a built-in policy name to users, withdrawing it is particularly unsafe: policy mappings persist by name, and an unresolved name merges into an empty policy that denies everything. Its inherited `admin:CreateUser` Deny also cannot be combined with `iamAdmin`. The certificate helper inventoried a cache the community server never populates.
- Upstream's golangci-lint `tool` directive, which would add roughly 200 linter dependencies to every downstream consumer's module graph.

## Related Commits {#related-commits}

- [5c4bf50](https://github.com/pgsty/silo-pkg/commit/5c4bf503d5d5701327527f030a3c755266d741f1): fix(policy): prefer the exact key name over the canonical header form
- [045d10f](https://github.com/pgsty/silo-pkg/commit/045d10fd974760153024cd7d519919440c28c5cb): fix(ldap): guard a nil TLS config and arm the StartTLS deadline
- [424c3d0](https://github.com/pgsty/silo-pkg/commit/424c3d06057b579631a4a8a81ffae9985875f477): fix(ldap): close the connection when StartTLS fails
- [74dd36e](https://github.com/pgsty/silo-pkg/commit/74dd36e78a829782b6f04ad09fd908386e13c693): fix(ldap): keep StartTLS when ServerInsecure is also set
- [88b37ac](https://github.com/pgsty/silo-pkg/commit/88b37ace8a14a511e09b9b30567cde8e5bfa2398): fix(certs): stop file watchers on every exit path
- [13c26cd](https://github.com/pgsty/silo-pkg/commit/13c26cda3db1e36bb3b7904217271a32b73039b7): fix(rng): initialize the reader subkeys from the seeded entropy
- [4055b2f](https://github.com/pgsty/silo-pkg/commit/4055b2f7d5a33948004ac13a933aa978b57399e6): fix(xtime): marshal Duration as a duration string
- [802539f](https://github.com/pgsty/silo-pkg/commit/802539f36d723802c80dea3c18c88da33c5d87d4): chore(deps): refresh the dependency set and declare the real minimum Go
- [e4ec64a](https://github.com/pgsty/silo-pkg/commit/e4ec64a9453d9ad469f6fd4ece93b2462bd118ef): ci: build on the Go version go.mod requires, and prove the declared minimum
- [747d8b8](https://github.com/pgsty/silo-pkg/commit/747d8b865ca937f227b0f70aeec9f8b49d05f55d): build: pin the golangci-lint installer and skip a matching install
- [da6a22a](https://github.com/pgsty/silo-pkg/commit/da6a22a10143f2e23764c59f39306e9ac3282da5): docs: say what this fork is and how to depend on it
