---
title: "SILO Console 2.6.0: Usage Scans and Safer Bucket Administration"
linkTitle: "Console 2.6.0"
date: 2026-11-05
author: "SILO"
description: "Console 2.6.0 adds folder and bucket usage, an optional durable worker, numeric validation, navigation fixes and security dependency updates."
tags: [Release, Console]
draft: false
weight: 1
url: "/blog/release/console-2.6.0/"
---

**Console 2.6.0 was published on 2026-11-05 (UTC+8)**, following
[2.5.1](/blog/release/console-2.5.1/). The
[GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.6.0)
records source commit `f8ab146695fd1df74e4b84128a286d552921bf00`, release assets
and verification evidence. This is a standalone Console release; Server's
embedded Console has its own release cycle.

[GitHub releases](https://github.com/pgsty/silo-console/releases) ·
[Release preparation PR #82](https://github.com/pgsty/silo-console/pull/82) ·
[Object management](/administration/console/managing-objects/)

## Folder and bucket usage {#usage}

The object browser can calculate folder sizes with cancellable metadata scans,
including optional retained-version totals. Current object bytes and retained
bytes are shown separately. The scan does not download object contents or
measure physical disk consumption. It runs with the caller's permissions;
listing versions requires permission to list versions.

Progress, freshness, and partial results remain visible. Unknown, unavailable,
failed, or interrupted measurements are not presented as zero. Only a completed
scan supplies a complete total; concurrent writes can still change a live
listing. Operators can bound scan duration, entries, folders, and concurrency.

An optional PostgreSQL-backed usage worker adds durable scan queues, checkpoints,
observer leases, and change-event reconciliation. Limited scans can be restarted
by an explicit refresh. Lease renewal is independent of a slow scan, and bucket
lists recover useful usage state after reloads. PostgreSQL is required only when
this optional worker is enabled.

See the [usage guide](/administration/console/managing-objects/#usage-scans) for
permissions, limits, environment variables, and worker operation. The original
folder-size feature and guide were contributed by **Urbanize** in
[PR #70](https://github.com/pgsty/silo-console/pull/70).

## Bucket administration and navigation {#fixes}

- Retention, quotas, and replication bandwidth are validated before numeric
  conversion. Inputs must fit the exact integer range of the JSON/browser API;
  byte displays and rate labels preserve fractional values where appropriate.
- Bucket creation rejects versioning exclusions on an object-locked bucket and
  reports failures when a requested configuration was not applied. A partial
  failure can leave a created bucket requiring inspection; creation is not an
  atomic transaction across all configuration APIs.
- Bucket lists preserve modern quota values and distinguish current bytes,
  retained bytes, partial measurements, and unavailable totals. Tables, cards,
  toolbars, and the retained column accommodate narrow screens and wider
  fallback fonts. API request widgets identify their four-minute count window.
- During object switches and browser Back/Forward navigation, details and
  version controls become hidden and inert until the accepted route renders.
  This prevents the previous object's controls remaining actionable under a
  different URL, including on slow CPUs ([PR #81](https://github.com/pgsty/silo-console/pull/81)).
- Embedded Console servers now receive the same three-minute keep-alive default
  as the CLI, so HTTP/2 asset requests reuse a persistent connection. An explicit
  `--keep-alive=0` still disables reuse.

## Runtime and security selections {#dependencies}

| Component | Released selection |
| --- | --- |
| Go | 1.27.3 |
| Node / Yarn | 24.22.1 / 4.13.0 |
| `silo-pkg/v3` | v3.15.2 |
| mcli source | Published 20261026 release, commit `0ceb298cdcd0` |
| Upstream `minio-go/v7` | `v7.4.2-0.20261025165926-320af050c445` |
| `golang.org/x/net` | v0.62.0 |
| `golang.org/x/crypto` | `v0.58.1-0.20261009181718-2f1f834330b2` |
{.wide .expand}

The `x/net` update includes the HTML parser/rendering fixes for
[GO-2026-6860](https://pkg.go.dev/vuln/GO-2026-6860) and
[GO-2026-6866](https://pkg.go.dev/vuln/GO-2026-6866). The selected `x/crypto`
revision separates the unsupported OpenPGP package from the main module, as
recorded by [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932).
The frontend also includes the URI decoder security update adopted after 2.5.1.

Existing compatibility pins remain: `go-systemd v22.6.0` for NetBSD portability,
`tablewriter v0.0.5`, `go-runewidth v0.0.29`, and `go-humanize v1.0.1` for reviewed
output behavior. Production JavaScript dependencies have an unfiltered audit
gate. The development-only `braces 3.0.3` exception remains tied to the committed
nesting-limit patch and its security regression tests, rather than a general
audit suppression.

## Integration and release boundary {#delivery}

The supported administration target is **pgsty/silo**, with the coordinated
Console, mcli, and silo-pkg dependency graph. Compatibility with unmodified
upstream MinIO remains best effort. The complete acceptance matrix covers
permissions, PostgreSQL usage work, sharing in standalone and embedded Console,
SSO, replication, reverse-proxy subpaths, browser behavior, cross-compilation,
package installation, and reproducibility.

Server 20261026 embeds Console 2.5.1. Installing standalone Console 2.6.0 does
not replace that embedded frontend or add newer server APIs. Usage-worker
integration and embedding must use a corresponding maintained SILO revision;
Console 2.6.0 alone is not a coordinated Server release. Existing module paths
and the required MC replacement are described in the
[embedding guide](https://github.com/pgsty/silo-console/blob/v2.6.0/docs/Embedding.md).

The tag workflow prepares binaries, archives, Linux packages, source, SHA-256
checksums, SPDX SBOMs, Sigstore signatures, GitHub provenance, and a versioned
Docker Hub candidate image. It requires successful validation of the exact
commit and verifies signatures and provenance before declaring the draft ready.
It does not advance `latest`. Publishing the verified GitHub draft is a separate
maintainer action that enables the promotion workflow; see the
[release contract](https://github.com/pgsty/silo-console/blob/v2.6.0/docs/release-contract.md).
