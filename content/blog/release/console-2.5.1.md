---
title: "SILO Console 2.5: Interface and Administration Updates"
linkTitle: "Console 2.5.1"
date: 2026-10-26
lastmod: 2026-10-27
author: "SILO"
description: "Console 2.5.0 and 2.5.1 changes since 2.4.2: the new interface, diagnostics, group permissions, downloads and accessibility."
tags: [Release, Console]
weight: 2
url: "/blog/release/console-2.5.1/"
aliases:
  - /blog/release/console-2.5.0/
---

**SILO Console v2.5.1 is released**, from [`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed). It is the Console version in the [SILO 20261026 release](/blog/release/silo-20261026/). This note covers the full 2.5 series since **v2.4.2**, including the 2.5.0 interface update and 2.5.1 repairs.

[GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) · [Downloads](/download/#console) · [All source changes](https://github.com/pgsty/silo-console/compare/v2.4.2...v2.5.1)

## Navigation, overview and metrics {#interface}

The interface uses neutral light/dark surfaces, system fonts, consistent density, Lucide icons, visible focus states and reduced-motion support. A mobile drawer and tablet rail adapt navigation to narrower screens; saved preferences take precedence. Object details become a mobile sheet with focus restoration, and dialogs/forms fit small screens. English and Chinese labels, accessible controls and legal attributions remain included.

Permission-aware navigation groups Identity, Monitoring, Settings and Tools, keeps one Buckets entry with recent buckets, and preserves remembered login destinations and existing object deep links. `/browser` redirects to `/buckets`; bare bucket administration links open Summary. Documentation, Video and Blog/RSS remain available through Help.

Overview shows server/drive health, raw capacity, alerts, quick actions and data freshness. Capacity uses Server-reported values rather than an estimated usable EC capacity; missing statistics remain unknown. Metrics V3 stays under Monitoring. Its panels distinguish missing samples from zero and respect per-node exports; bucket/account usage is scanner-derived, even though Server 20261026 now returns a live bucket inventory.

## Buckets, objects and tasks {#objects}

- Sort and filter bucket tables with URL query persistence, table/card views, large-list virtualization and explicit unknown usage. Stable identities keep selection attached to the right bucket. Pending search updates are discarded after navigation.
- Keep the object workspace accessible to write-only users, preserve wildcard bucket-root grants and prefix restrictions, and show server error details for rejected actions such as tag writes. Listing, reading and mutation permissions remain independent.
- Preview bounded text, Markdown and CSV/TSV, with source views, safe HTML handling and a visible **1 MiB** truncation notice. Supported forms show mcli equivalents without secrets.
- Track transfers, native ZIP downloads, bulk deletion, noncurrent-version cleanup and restoration in Tasks. Mutation concurrency is bounded and retries select failed targets. Canceling a task does not undo completed writes; browser handoff does not prove the download reached disk.
- Add keyboard navigation, range selection, current-page Select All, shortcut help and permission-aware context menus. Existing cursor pagination remains: sorting/filtering/select-all apply to the current page, not the whole bucket.

## Identity and diagnostics {#identity}

User pages show status, direct policies, group inheritance and access-key counts. Policy pages distinguish native, overridden and custom policies, display assignment counts and explain affected identities. Native policies are read-only until explicitly overridden; modified built-ins offer Reset. Failed reloads clear stale editor content, language changes preserve drafts, and forms associate labels correctly and mask remote secrets.

**Reset and live bucket inventory require Server 20261026.** Updating standalone Console alone does not patch an older Server's policy cache or replace its embedded UI.

Health, Trace, Logs, Watch, Speedtest and Profile finish the WebSocket close handshake using the existing sole reader and a shared **five-second close budget**, without limiting active streams. This repairs high-RTT health-report truncation and code 1006 closures reported by [Azat / @azataiot in #63](https://github.com/pgsty/silo-console/issues/63). Wrapped timeout errors retain close code 1008 without exposing internal details. Health reports reuse one JSON decoder across the version probe and payload, preserving buffered frames; truncated, canceled or failed reports are rejected. The signed madmin v3 transport and retry behavior remain.

## Repairs in 2.5.1 {#patch}

- A status-only group update preserves membership; explicitly supplied member arrays retain replacement semantics.
- OIDC string-array groups retain their permissions. Session cookies remain secure behind configured HTTPS or trusted TLS proxies; arbitrary forwarded headers are not trusted.
- Credential exports preserve exact UTF-8 JSON bytes. ZIP failures before the first response byte preserve the S3 error status without exposing backend details.
- Tables and controls restore focus, accessible names and progress values; the focused tab stays visible after resizing.
- Upgrade to released mcli 20261026, silo-pkg v3.15.2 and the upstream SDK fix accepting HTTP 204 when removing replication configuration.

These changes are recorded in [#67](https://github.com/pgsty/silo-console/pull/67), [#68](https://github.com/pgsty/silo-console/pull/68) and [#69](https://github.com/pgsty/silo-console/pull/69).

## Dependencies and delivery {#delivery}

Go **1.27.3**, Node **24.22.1**, Vite **8.3.5**, GoReleaser **2.19.0**, silo-pkg **3.15.2**, mcli **20261026**, and upstream minio-go **`320af050c445`** form the released baseline. The 2.5 series retains tablewriter 0.0.5, go-humanize 1.0.1, go-runewidth 0.0.29 and go-systemd 22.6.0 for output and platform compatibility. See the [shared dependency/security inventory](/blog/release/silo-20261026/#runtime-fixes).

The [release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) supplies platform binaries and archives, Linux packages, source, checksums, SPDX SBOMs and Sigstore/GitHub provenance. Windows archives use ZIP; Linux/macOS use tar.gz. Official images are `docker.io/pgsty/silo-console:v2.5.1` on Docker Hub. Verify with the [release contract](https://github.com/pgsty/silo-console/blob/v2.5.1/docs/release-contract.md).

The delivery checks enforce Windows ZIP bundles and pull platform digests before multi-architecture image promotion. Reproducibility builds use isolated workspaces with bounded temporary disk usage; the Semgrep runner is pinned to Python 3.12.12. Generated API files and embedded frontend assets are rebuilt with the compatibility checks described in the shared inventory.

The maintained administration target is **pgsty/silo**. Upstream MinIO compatibility remains best effort. Existing environment variables, API routes, service identities and module paths remain supported; use the [compatibility guide](/compatibility/console/) for the exact API and embedding graph.
