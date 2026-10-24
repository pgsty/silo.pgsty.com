---
title: "SILO Console 2.4.2 Released"
linkTitle: "Console 2.4.2"
date: 2026-10-17T20:49:49+08:00
author: "Vonng"
description: "mcli 20261018, minio-go v7.4.1, updated build tools, and preserved bucket-versioning error codes."
tags: [Release, Console]
weight: 1
url: "/blog/release/console-2.4.2/"
---

**Release:** [v2.4.2](https://github.com/pgsty/silo-console/releases/tag/v2.4.2) · **Source:** [`ef2dd2c41d21`](https://github.com/pgsty/silo-console/commit/ef2dd2c41d212ed6405c90fa8e5ab671899a7365).

Console v2.4.2 ships both as a standalone release and as the embedded Console in [Server 20261018](/blog/release/silo-20261018/#components) (see also the [silo-pkg v3.14.2 release notes](/blog/release/pkg-3.14.2/)).

## Changes {#changes}

- Adopt **mcli 20261018**, **silo-pkg v3.14.2**, and upstream **minio-go v7.4.1**. The SDK cleans up failed multipart uploads after cancellation, formats retention timestamps in UTC, and preserves requested STS durations (parallel GET and ComposeObject remain opt-in).
- Preserve wrapped S3 error codes during bucket-versioning operations so attempting to suspend versioning on an Object Lock bucket surfaces `InvalidBucketState` cleanly.
- Build with **Go 1.27.2** and **Node 24.22.0 LTS**. Refresh `golang.org/x/*` modules alongside compress **v1.20.3**, msgp **v1.6.5**, etcd **v3.7.2**, fwd **v1.2.1**, and cpuid **v2.4.1** (retaining go-systemd **v22.6.0** for NetBSD and tablewriter **v0.0.5** for MC API compatibility).
- Pin **GoReleaser v2.18.3**, **golangci-lint v2.15.0**, and **govulncheck v1.9.0**, rebuild embedded frontend assets as Console 2.4.2, and update pinned container build stages.

## Integration {#integration}

Because the retained module path has no `/v2` suffix, Go consumers reference Console v2.4.2 via pseudo-version `v0.0.0-20261017112417-ef2dd2c41d21`. An embedding Server must declare both Console and MC replacements explicitly:

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261017112417-ef2dd2c41d21
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261017101407-fa3b8bf72458
```

Console v2.4.2 requires `github.com/pgsty/silo-pkg/v3 v3.14.2` (see the [password-permission migration guide](/compatibility/password-permissions/)). Note that the `go-jose v4.1.6` 4096-bit RSA JWK limit applies only to Server OIDC paths that import `go-jose`; neither `go-jose` nor `go-ldap` is linked into the standalone Console binary.

## Delivery and validation {#delivery}

All **44 release assets** (6 platform binaries, 6 archives, 9 Linux packages, checksum manifests, SBOMs, and signed provenance attestations) were verified against tagged commit `ef2dd2c41d21`. The commit passed the full CI matrix (permissions, SSO, replication, browser tests, source-image equivalence, and reproducible packaging), vulnerability checks, the local Go race suite, 251 frontend unit tests, and live API/browser sharing checks against [Server 20261018](/blog/release/silo-20261018/).

The published `docker.io/pgsty/silo-console:v2.4.2` multi-arch (`linux/amd64` and `linux/arm64`) manifest digest is:

```text
sha256:4cf47061e0d2f249df3c1cd2a939966ff3c69cc3cf7d10a7b1b39d5c110ae999
```

[Release verification contract](https://github.com/pgsty/silo-console/blob/v2.4.2/docs/release-contract.md) · [Component matrix](/compatibility/versions/) · [Changes since v2.4.1](https://github.com/pgsty/silo-console/compare/v2.4.1...v2.4.2).
