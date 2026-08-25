---
title: "silo-pkg 3.12.0 Released"
linkTitle: "silo/pkg 3.12.0"
date: 2026-08-24
author: "Vonng"
description: "silo-pkg 3.12.0 rejects bare ARN namespace prefixes on strict policy-write paths, preserves legacy policy loading, moves the maintained baseline to Go 1.27 and etcd 3.7.1, and ships the reviewed SILO dependency stack."
tags: [Release, pkg, Security]
weight: 5
url: "/blog/release/pkg-3.12.0/"
aliases:
  - /releases/pkg-3.12.0/
---

**Release date:** 2026-08-24 · **Version:** [v3.12.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) · **Commit:** [`2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a11cf3547313a2e79275f52a0654c212e58) · **Repository:** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

Version 3.12.0 is a main-line minor release with two themes: a policy-write guard for ARN prefixes that name no resource, and the maintained Go 1.27 / etcd 3.7 dependency baseline. It adds two exported inspection/validation methods, raises the verified consumer floor to Go 1.26, and is the first `silo-pkg` release whose strict validation path is enabled by the SILO server for named-policy and service-account policy writes.

> [!WARNING]
> **This package release and a SILO server release are different gates.** The package tag and GitHub Release are public. SILO `main` consumes it in [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617), with the operator note recorded as [`SN-2026-005`](https://github.com/pgsty/silo/commit/56c67dacf13cb3c5c1c59e64afec77ab145fb7f4). No date-style SILO server tag, container image, package set, deployment, or production rollout is established by this article.

## Release at a Glance {#glance}

- **Published:** the `silo-pkg v3.12.0` tag, GitHub Release, and strict library validation for bare ARN prefixes.
- **On SILO remote `main`:** named-policy and service-account policy write integration.
- **Deliberately permissive:** existing IAM policy loading, IAM import, and site-replication receive paths.
- **Deferred:** STS inline-policy strict validation and Console-side early validation; the server remains authoritative.
- **Not part of this release:** a SILO server binary, image, package, deployment, or production rollout.

## Bare ARN Prefixes Were Policy No-ops {#bare-arn}

An S3 resource ARN needs a resource after its namespace prefix:

```text
arn:aws:s3:::my-bucket
arn:aws:s3:::my-bucket/*
arn:aws:s3:::*
```

The policy parser also accepted the prefix by itself:

```text
arn:aws:s3:::
```

That string names no bucket or object. The existing parser normalized it to the wildcard resource type while retaining `arn:aws:s3:::` as the match pattern. Real S3 authorization candidates look like `bucket` or `bucket/object`, so the pattern normally matched nothing even though the policy validated successfully.

For statements that actually perform resource matching, the impact depends on `Effect` and on whether the prefix appears in `Resource` or `NotResource`:

| Statement shape | Existing runtime result |
|:--|:--|
| `Allow` + bare `Resource` | Grants nothing |
| `Deny` + bare `Resource` | The intended denial does not fire |
| `Allow` + bare `NotResource` | Excludes nothing and can grant far more than intended |
| `Deny` + bare `NotResource` | Can deny far more than intended |

The dangerous cases are policy-dependent fail-open behavior, not an unauthenticated remote exploit and not a CVE. A policy author, template, or automation must first submit the malformed resource. The same issue applies to registered S3 Tables and KMS ARN prefixes.

Resource-less admin actions, `sts:*` action statements, and the first phase of two-step KMS authorization bypass resource matching; a bare prefix does not change their existing runtime decision. Strict writes still reject the deceptive field so a policy cannot look scoped when that scope is ignored.

### The Historical `*arn:...` Spelling {#historical-spelling}

On the permissive compatibility path inherited from earlier releases, serializing a parsed bare prefix adds the wildcard type marker:

```text
arn:aws:s3:::  ->  *arn:aws:s3:::
```

Re-parsing either spelling produces the same internal resource value. The 3.12 guard therefore recognizes both the exact prefix and its historical star-prefixed serialization. This matters for stored/exported policies and for clients that parse and marshal a document before sending it to the server.

The accepted wildcard corpus remains unchanged: `*`, `**`, `***`, `*foo`, and explicit resources such as `arn:aws:s3:::*` still parse as before.

## A Strict Write Path, Not a Storage Migration {#strict-path}

The fix deliberately separates policy loading from policy creation:

- `ParseConfig` and `Validate` remain permissive. Existing stored policies keep loading and evaluating with the same matching and serialization behavior.
- `ParseConfigStrict` and `ValidateStrict` reject a registered ARN prefix that names no resource, in both `Resource` and `NotResource`.
- `Resource.IsBareARN()` detects the normalized exact/historical form without changing the exported `Resource` structure, `ParseResource`, matching, or JSON representation.
- `ResourceSet.ValidateStrict()` exposes the strict resource-set check to consumers.

Keeping the existing resource representation is important for mixed-version sites: v3.11 and v3.12 nodes continue to compare and serialize stored policies the same way, so this fix does not create a site-replication mismatch or require a storage migration.

## SILO Enables the Guard on Three Boundaries {#silo-integration}

SILO commit [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617) selects `silo-pkg v3.12.0` and uses strict parsing when:

1. creating or replacing a named IAM policy;
2. creating a service account with an inline session policy; and
3. updating a service account's inline session policy.

Compatibility-sensitive paths stay permissive in this rollout:

- loading named policies and embedded policies already at rest;
- IAM import/restore;
- site-replication receive and apply paths;
- STS inline session policies; and
- bucket policies, whose existing bucket/action validation already rejects these forms.

Enabling `ParseConfigStrict` also activates two pre-existing admin-policy checks: one admin statement may not contain both `Resource` and `NotResource`, and a bucket-scoped admin action may not use a non-S3 resource. These are intentional authorization tightenings and are documented in [`SN-2026-005`](https://github.com/pgsty/silo/blob/main/docs/security/advisories.md).

> [!IMPORTANT]
> In this article, **bare ARN prefix** means an ARN namespace with no resource after it, such as `arn:aws:s3:::`. It is different from the valid **bare bucket ARN** used in the 3.11 bucket/object-boundary fix, such as `arn:aws:s3:::my-bucket`.

## Operator Action {#operator-action}

Existing policies are not rewritten automatically because the intended resource cannot be inferred. Before deploying a SILO server build that contains the strict integration:

1. inspect named IAM policies for exact or historical bare prefixes;
2. inspect service-account inline policies;
3. replace each finding with the intended concrete resource; or use a suffix wildcard only if all resources in that namespace are truly intended; and
4. repeat the audit after all sites have completed the rolling upgrade.

Do not blindly turn every finding into `arn:aws:s3:::*`: that could replace an inert statement with a cluster-wide grant or denial. A legacy policy containing a bare prefix still loads, but it cannot be submitted unchanged through the three strict write endpoints; correct it before editing another property on the same policy or service account.

The safer audit path uses policy-info and access-key-info APIs rather than a full IAM export, because a complete export contains user and service-account secrets. STS strict validation remains deferred until live machine clients and their session-policy templates can be audited separately.

## Why This Is a Minor Release {#why-minor}

This is `v3.12.0`, not `v3.11.1`, because the release combines three compatibility-relevant changes:

1. the etcd client crosses from the 3.6 minor line to 3.7;
2. the module's verified `go` floor rises from 1.25.0 to 1.26.0; and
3. the package adds exported bare-ARN inspection and strict resource-set validation APIs.

The module path remains `github.com/minio/pkg/v3`; the `/v3` import suffix and every existing import site stay unchanged.

## Go and Dependency Baseline {#dependencies}

The `go` and `toolchain` directives have separate purposes:

- `go 1.26.0` is the supported consumer floor required by the selected etcd 3.7 modules.
- `toolchain go1.27.0` is the maintained development and CI baseline.
- CI actions move to the Node 24 runtime.

Key selected versions change as follows:

| Module | 3.11.0 | 3.12.0 |
|:--|:--|:--|
| `go.etcd.io/etcd/{api,client/pkg,client}/v3` | `3.6.6` | `3.7.1` |
| `golang.org/x/crypto` | `0.54.0` | `0.55.0` |
| `golang.org/x/net` | `0.57.0` | `0.58.0` |
| `golang.org/x/text` | `0.40.0` | `0.41.0` |
| `github.com/minio/minio-go/v7` | `7.0.97` | `7.0.99` |
| `github.com/minio/mux` | `1.8.2` | `1.9.2` |
| `github.com/cheggaaa/pb` | `1.0.29` | `1.0.30` |
| `github.com/lestrrat-go/jwx/v3` | `3.0.12` | `3.0.13` |
| `github.com/lestrrat-go/httprc/v3` | `3.0.1` | `3.0.6` |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `2.27.3` | `2.29.0` |
| `go.uber.org/zap` | `1.27.1` | `1.28.0` |

Smaller selected updates include `uax29` 2.3.1, `fastjson` 1.6.10, `secp256k1` 4.4.1, and `goccy/go-json` 0.10.6. The old `lestrrat-go/option` v1, `gogo/protobuf`, and stale test-only requirements leave the selected graph.

etcd 3.7.1 is the first fixed release on the 3.7 line for [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107), an unauthenticated TLS-listener denial of service. Updating these Go client modules does **not** upgrade an operator's external etcd server. SILO does not use the removed `grpc.WithBlock` behavior, and client compatibility with an etcd 3.6.14 server was exercised during release validation.

The dependency graph declares `coreos/go-systemd` 22.7.0, but the module replaces it with 22.6.0 because 22.7.0 does not compile on NetBSD. The SILO server carries the same portability override.

## Compatibility {#compatibility}

- Import paths and the module major remain unchanged.
- Existing policies keep loading and evaluating unchanged; only strict create/update calls reject the malformed prefixes.
- No policy, IAM database, wire protocol, or etcd data migration is performed.
- Downstream users of `grpc.WithBlock` in etcd client dial options must migrate to a supported readiness check; SILO does not use it.
- A real external etcd cluster upgrade remains a separate operational procedure.
- Upstream AIStor Memory and new AIStor-only S3 Tables action vocabularies are not imported by this fork.

Consumers select the release with:

```go
require github.com/minio/pkg/v3 v3.12.0

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.0
```

## Verification {#verification}

The tagged package passed:

- the repository's complete `make test` gate: pinned lint plus `go test -race -tags kqueue ./...`;
- targeted bare-ARN tests repeated to disturb Go map iteration order;
- `go mod verify`, `go vet`, `git diff --check`, and `govulncheck` with zero reachable vulnerabilities; and
- an implementation-level Claude Opus Max review with a **GO** verdict and no P0/P1 findings.

The SILO integration passed:

- the complete IAM server suite, including exact/historical named-policy rejection and service-account create/update rejection;
- `go test ./cmd -count=1`, `go vet ./cmd`, and `go test ./...`;
- golangci-lint 2.13.1 with zero findings, `go mod verify`, and `make check-gen`; and
- a second Claude Opus Max review with a **GO** verdict; mutation tests proved all three strict call sites and their integration assertions are load-bearing.

Direct VCS module resolution verified `v3.12.0` at commit `2b087a1` with module checksum:

```text
h1:1Bjqjb3KCt0oYhBLpH7W/e/5khTUoIgXWA12An1fbUc=
```

The release environment could not reach `proxy.golang.org` or `sum.golang.org` because those connections timed out, so public-proxy observation is not claimed as release evidence. The Git tag, GitHub Release, direct module archive, origin commit, and checksum were verified.

## Related Changes {#related-changes}

- [`2bc3a91`](https://github.com/pgsty/silo-pkg/commit/2bc3a91): move CI actions onto Node 24
- [`c8c6872`](https://github.com/pgsty/silo-pkg/commit/c8c6872): align the SILO Go dependency stack
- [`2b087a1`](https://github.com/pgsty/silo-pkg/commit/2b087a11cf3547313a2e79275f52a0654c212e58): reject bare ARN prefixes on strict policy writes; tagged `v3.12.0`
- [`30c49bd`](https://github.com/pgsty/silo-pkg/commit/30c49bd): update the README dependency example after the tag
- [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617): enable strict named-policy and service-account writes in SILO
- [`56c67dacf`](https://github.com/pgsty/silo/commit/56c67dacf13cb3c5c1c59e64afec77ab145fb7f4): record `SN-2026-005`

## What Is Not Released Here {#not-released}

This article does not claim a new SILO server version, binary, package, container image, deployment, production rollout, Console release, or strict STS rollout. Those remain separate release gates and must be reported separately when completed.
