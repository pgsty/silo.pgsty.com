---
title: "SILO Console 2.4.2 Released"
linkTitle: "Console 2.4.2"
date: 2026-10-17T20:49:49+08:00
author: "Vonng"
description: "mcli 20261018, minio-go v7.4.1, updated build tools and correct bucket-versioning errors."
tags: [Release, Console]
weight: 1
url: "/blog/release/console-2.4.2/"
---

**Release:** [v2.4.2](https://github.com/pgsty/silo-console/releases/tag/v2.4.2) · **Source:** [`ef2dd2c41d21`](https://github.com/pgsty/silo-console/commit/ef2dd2c41d212ed6405c90fa8e5ab671899a7365).

This note records the published tag. Later development branches adopting pkg v3.14.3 do not change these published binaries. See the [Server 20261018 component matrix](/blog/release/silo-20261018/#components) and [pkg v3.14.2 release notes](/blog/release/pkg-3.14.2/).

## Changes {#changes}

- Select published **mcli 20261018**, **silo-pkg v3.14.2** and upstream **minio-go v7.4.1**. The SDK cleans up failed multipart uploads after cancellation, sends retention timestamps in UTC and preserves requested STS durations. Parallel GET and ComposeObject remain opt-in.
- Preserve wrapped S3 errors from bucket-versioning operations and report `InvalidBucketState` explicitly when Object Lock prevents suspension. The Server's protection remains unchanged.
- Build with **Go 1.27.2** and **Node 24.22.0 LTS**. Refresh Go x/* modules and targeted fixes in compress **v1.20.3**, msgp **v1.6.5**, etcd **v3.7.2**, fwd **v1.2.1** and cpuid **v2.4.1**. Keep go-systemd **v22.6.0** for NetBSD and tablewriter **v0.0.5** for the existing MC API.
- Use **GoReleaser v2.18.3**, **golangci-lint v2.15.0** and **govulncheck v1.9.0**. Rebuild embedded assets as Console 2.4.2 and update the pinned source-build container.

## Integration {#integration}

Go consumers use `v0.0.0-20261017112417-ef2dd2c41d21` because the retained module path has no `/v2` suffix. An embedding Server must select both Console and MC replacements explicitly:

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261017112417-ef2dd2c41d21
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261017101407-fa3b8bf72458
```

Console directly requires `github.com/pgsty/silo-pkg/v3 v3.14.2`. Existing password-permission migration rules remain in effect; see the [migration guide](/compatibility/password-permissions/). The go-jose **v4.1.6** RSA JWK limit applies to Server OIDC code that imports it; go-jose and go-ldap are not linked into the standalone Console binary.

A standalone Console upgrade does not replace the Server binary or automatically deploy Server security and storage repairs. Server 20261018 is publicly released; its own release record covers the Server artifacts and images. The supported administrative target is SILO, with unmodified upstream MinIO compatibility on a best-effort basis.

## Delivery and validation {#delivery}

Release binaries, archives, Linux packages and source are accompanied by checksums, SBOMs and signed provenance. The exact tagged commit passed the required CI matrix and vulnerability summaries, including permissions, SSO, replication, browser tests, source-image equivalence and reproducible packaging. Local acceptance also passed the full Go race suite and 251 frontend unit tests.

All **44 downloaded assets** were verified. Six platform binaries, six bundles and nine Linux packages carry the expected source, dependency versions and legal material. The checksum manifest's Sigstore signature and GitHub provenance were verified. The downloaded Console binary passed real API and browser sharing tests against the SILO 20261018 draft binary; Server remains unpublished.

The public `docker.io/pgsty/silo-console:v2.4.2` tag selects this verified Linux amd64/arm64 image:

```text
sha256:4cf47061e0d2f249df3c1cd2a939966ff3c69cc3cf7d10a7b1b39d5c110ae999
```

[Release verification contract](https://github.com/pgsty/silo-console/blob/v2.4.2/docs/release-contract.md) · [Component matrix](/compatibility/versions/) · [Changes since v2.4.1](https://github.com/pgsty/silo-console/compare/v2.4.1...v2.4.2).
