---
title: "silo-pkg 3.15: Go 1.27.3 and S3 SDK Fixes"
linkTitle: "pkg 3.15.2"
date: 2026-10-26
lastmod: 2026-10-27
author: "SILO"
description: "The complete silo-pkg 3.15.0–3.15.2 changes since 3.14.3: dependency updates, multipart/read fixes and replication-removal compatibility."
tags: [Release, Dependencies]
weight: 3
url: "/blog/release/pkg-3.15.2/"
aliases:
  - /blog/release/pkg-3.15.0/
  - /blog/release/pkg-3.15.1/
---

**silo-pkg v3.15.2 is now released** (commit [`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0)) and is adopted directly across the [SILO 20261026 stack](/blog/release/silo-20261026/) as `github.com/pgsty/silo-pkg/v3`. This note summarizes the full 3.15 series (`v3.15.0`, `v3.15.1`, and `v3.15.2`) since **v3.14.3**.

## 3.15.0: Toolchain and shared dependencies {#dependencies}

The module's minimum Go version increases from **1.26 to 1.27.3**, alongside updates to 13 direct dependencies: JWX `3.4.0`, etcd `api` / `client/pkg` / `client` `3.7.3`, gRPC `1.84.0`, grpc-gateway `2.32.0`, `go-json 0.11.2`, `swag/conv 0.29.2`, `go-colorable 0.1.16`, `cpuid 2.4.1`, `fwd 1.2.1`, and the two Google generated API/RPC modules pinned at `ce908d29299b`.

Downstream applications must rebuild with Go 1.27.3 to pick up the Go standard library's certificate-verification fix. All public package APIs, IAM policy formats, authorization rules, and the [v3.14.3 policy evaluation optimizations](/blog/release/pkg-3.14.3/) remain unchanged.

## 3.15.1: Upstream S3 SDK fixes {#sdk}

`v3.15.1` advances upstream `minio-go` from `v7.4.1` to `ab93db7ba435`, bringing in six fixes:

- Rejects truncated sequential and parallel streamed multipart uploads before transmitting an incomplete part.
- Preserves sequential read state after `ReadAt` hits `EOF` and rejects negative `ReadAt` offsets before fetching object metadata.
- Fixes read and `Seek` bounds after calling `Object.Stat`.
- Deduplicates batch-delete fallback errors so each failed entry is reported once.

## 3.15.2: Bucket replication removal {#replication}

`v3.15.2` advances upstream `minio-go` to **`v7.4.2-0.20261025165926-320af050c445`** (a pinned pseudo-version, as upstream has not tagged `v7.4.2`). Removing bucket replication—including passing an empty configuration to `SetBucketReplication`—now accepts both **HTTP 200 and HTTP 204** while continuing to surface `AccessDenied` and other real errors (see [upstream comparison](https://github.com/minio/minio-go/compare/v7.4.1...320af050c445)).

## Compatibility and verification {#compatibility}

Downstream applications that rely on established CLI formatting and NetBSD builds continue to pin `go-humanize v1.0.1`, `go-runewidth v0.0.29`, and `go-systemd/v22 v22.6.0`. Because Go does not inherit `replace` directives from dependencies, each consuming application declares its own module replacements.

`v3.15.2` passed the full lint and `-race` test suites (including live LDAP integration), module verification, and all three CI workflows ([Go](https://github.com/pgsty/silo-pkg/actions/runs/40318147518), [LDAP](https://github.com/pgsty/silo-pkg/actions/runs/40318147326), and [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/40318147298)). HTTP fixtures verified that both replication-removal entry points accept `200`/`204` while preserving `403` errors, and earlier 3.15 regression suites covered JWT validation boundaries, local etcd auth/watch/lease persistence, and CLI formatting. Scanner finding `GO-2026-5932` resides in deprecated OpenPGP packages that `silo-pkg` does not import (see the [shared security inventory](/blog/release/silo-20261026/#runtime-fixes)).

```go
require github.com/pgsty/silo-pkg/v3 v3.15.2
```

`silo-pkg` is a **source-only Go module** adopted by rebuilding Server, Console, and mcli. The supported dependency graph is the coordinated PGSTY stack, with best-effort upstream MinIO/MC compatibility. [GitHub release](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2) · [Full commit comparison](https://github.com/pgsty/silo-pkg/compare/v3.14.3...v3.15.2).
