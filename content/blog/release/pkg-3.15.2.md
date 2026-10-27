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

**silo-pkg v3.15.2 is released**, from [`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0). The [SILO 20261026 stack](/blog/release/silo-20261026/) uses this shared module directly as `github.com/pgsty/silo-pkg/v3`. This note covers the full 3.15 series since **v3.14.3**.

## 3.15.0: toolchain and shared dependencies {#dependencies}

The minimum Go version rises from **1.26 to 1.27.3**. Thirteen required modules change: JWX 3.4.0; etcd API/client/pkg/client 3.7.3; gRPC 1.84.0; grpc-gateway 2.32.0; go-json 0.11.2; swag/conv 0.29.2; go-colorable 0.1.16; cpuid 2.4.1; fwd 1.2.1; and the two Google generated API/RPC modules at `ce908d29299b`.

Consumers obtain Go's certificate-verification fix by rebuilding with Go 1.27.3; the library does not ship a Go runtime. Public package APIs, policy formats, authorization decisions and the [v3.14.3 policy optimizations](/blog/release/pkg-3.14.3/) remain intact.

## 3.15.1: upstream SDK repairs {#sdk}

The first SDK update selected upstream `ab93db7ba435` after v7.4.1, incorporating six fixes:

- Reject short sequential and parallel streamed multipart uploads before sending an incomplete part.
- Preserve sequential reads after `ReadAt` reaches EOF; reject negative `ReadAt` offsets before metadata access.
- Preserve read and seek bounds after `Object.Stat`.
- Emit each batch-delete fallback failure once.

## 3.15.2: replication removal {#replication}

The final selection is upstream **`v7.4.2-0.20261025165926-320af050c445`**. Removing bucket replication accepts **HTTP 200 and HTTP 204**, including an empty configuration passed to `SetBucketReplication`; AccessDenied and other failure responses remain errors. Upstream has not tagged v7.4.2. [Upstream changes](https://github.com/minio/minio-go/compare/v7.4.1...320af050c445).

## Compatibility and verification {#compatibility}

Keep go-humanize 1.0.1, go-runewidth 0.0.29 and go-systemd/v22 22.6.0 where applications require the established output and NetBSD behavior. Go does not inherit dependency replacements; each consuming application retains its own necessary replacements.

The v3.15.2 release passed full lint/race tests with LDAP, module verification and all three push workflows: [Go](https://github.com/pgsty/silo-pkg/actions/runs/40318147518), [LDAP](https://github.com/pgsty/silo-pkg/actions/runs/40318147326), [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/40318147298). HTTP fixtures accept 200/204 through both replication-removal entry points and retain 403 errors. Earlier 3.15 dependency regressions cover JWT boundaries, local etcd authentication/watch/lease persistence and CLI formatting.

No new CVE fix is claimed for the SDK patches. `GO-2026-5932` remains a module-level finding in deprecated OpenPGP code that the package does not import. See the [shared security inventory](/blog/release/silo-20261026/#runtime-fixes).

```go
require github.com/pgsty/silo-pkg/v3 v3.15.2
```

This is a **source-only release** with no executable, package or container. Server, Console and mcli adopt it by rebuilding. The supported dependency graph is the maintained PGSTY stack; upstream MinIO/MC compatibility is best effort. [GitHub release](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2) · [Complete changes](https://github.com/pgsty/silo-pkg/compare/v3.14.3...v3.15.2).
