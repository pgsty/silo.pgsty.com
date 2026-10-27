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

**SILO Console v2.5.1 is now released** (commit [`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed)) and ships embedded inside **[SILO 20261026](/blog/release/silo-20261026/)**. This note summarizes the full 2.5 release series since **v2.4.2**, combining the `v2.5.0` interface overhaul and the `v2.5.1` patch fixes.

[GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) · [Downloads](/download/#console) · [Full commit comparison](https://github.com/pgsty/silo-console/compare/v2.4.2...v2.5.1)

## Navigation, overview, and metrics {#interface}

The 2.5 interface adopts neutral light and dark themes, system typography, consistent information density, Lucide icons, clear keyboard focus states, and `prefers-reduced-motion` support. A mobile drawer and tablet rail adapt navigation to narrow viewports while respecting saved user preferences; object details open in a focus-restoring bottom sheet on mobile, and dialogs and forms scale cleanly to smaller screens. English and Chinese localization, accessible controls, and license attributions remain built in.

Permission-aware navigation organizes Identity, Monitoring, Settings, and Tools around the active session's grants, consolidates bucket access under a single Buckets entry with recent-bucket shortcuts, and preserves post-login redirect targets and existing object deep links (`/browser` redirects to `/buckets`, and bare bucket-management URLs open the Summary tab). Help continues to link directly to Documentation, Video guides, and Blog/RSS feeds.

The Overview dashboard displays node and drive health, raw physical capacity, active alerts, quick actions, and data freshness. Capacity panels report the exact figures returned by Server rather than estimating usable erasure-coded capacity, marking uncollected statistics as unknown. Metrics V3 panels under Monitoring distinguish missing Prometheus samples from true zero values and handle per-node cluster metric exports accurately. Note that while Server 20261026 returns a live bucket inventory, bucket and account usage totals remain scanner-derived.

## Buckets, object browser, and tasks {#objects}

- **Bucket list:** Supports sorting, name filtering, URL query-parameter persistence, table/card view toggling, large-list virtualization, and explicit unknown-usage badges. Stable row keys keep selection attached to the right bucket across sorts, and in-flight search updates are discarded on navigation.
- **Fine-grained permission handling:** Write-only users can enter the object workspace; wildcard bucket-root grants and prefix restrictions are preserved; and rejected actions (such as tag edits) surface the server's error message directly (listing, read, and mutation permissions remain evaluated independently).
- **Bounded previews and CLI hints:** Adds bounded **1 MiB** previews for plain text, Markdown, and CSV/TSV files alongside source views, sanitized HTML rendering, and explicit truncation notices. Supported configuration forms also display secret-redacted `mcli` command equivalents.
- **Tasks center:** Tracks uploads, downloads, native streaming ZIP downloads, bulk deletes, noncurrent-version cleanup, and object restores with bounded mutation concurrency and failed-item-only retries (canceling a task does not roll back already-completed writes; verify large object or streaming ZIP downloads on disk after browser transfer completes).
- **Keyboard navigation and pagination:** Adds arrow-key navigation, Shift-range selection, current-page Select All, a keyboard-shortcut reference dialog, and permission-aware context menus. Cursor pagination remains unchanged—sorting, filtering, and Select All operate on the current page.

## Identity management and high-latency diagnostics {#identity}

User detail pages display account status, direct policies, group-inherited policies, and Access Key counts; policy pages distinguish native built-in, overridden built-in, and custom policies while showing assignment counts and affected identities. Native built-in policies remain read-only until explicitly overridden, and modified built-in policies offer a one-click **Reset**. Failed reloads clear stale editor contents, language switches preserve unsaved drafts, and forms bind labels properly while masking remote secrets.

**Note: Built-in policy Reset and live bucket inventory require Server 20261026.** Upgrading standalone Console by itself does not update an older Server's policy cache or replace its embedded frontend.

Across all six live diagnostic streams (Health, Trace, Logs, Watch, Speedtest, and Profile), Console now completes the WebSocket close handshake through the single existing reader goroutine with a shared **five-second close budget** that never cuts off active streams. This fixes the high-RTT health-report truncation and abnormal `1006` closures reported by [Azat / @azataiot in #63](https://github.com/pgsty/silo-console/issues/63) (wrapped timeouts still return close code `1008` without leaking internal details). Health-report downloads also reuse a single JSON decoder across the version probe and payload so buffered bytes are never dropped, reject truncated or canceled streams, and retain signed `madmin v3` transport and retry behavior.

## Fixes in 2.5.1 {#patch}

- **Group status toggles ([#67](https://github.com/pgsty/silo-console/pull/67)):** Enabling or disabling a group now preserves its existing members, while an explicit `members` array continues to replace membership.
- **OIDC groups and reverse-proxy cookies ([#66](https://github.com/pgsty/silo-console/pull/66)):** Preserves permissions for OIDC string-array group claims and sets `Secure` session cookies only when HTTPS or a trusted TLS proxy header is configured.
- **Credential exports and streaming ZIP errors ([#68](https://github.com/pgsty/silo-console/pull/68)):** Preserves exact UTF-8 JSON bytes when exporting Access Keys, and propagates the S3 HTTP error status when a streaming ZIP download fails before writing its first response byte.
- **Accessibility and focus restoration ([#68](https://github.com/pgsty/silo-console/pull/68)):** Restores keyboard focus across tables and dialogs, adds accessible names and progress-bar value attributes, and keeps the focused tab visible when resizing the viewport.
- **Companion dependencies ([#69](https://github.com/pgsty/silo-console/pull/69)):** Updates to `mcli 20261026`, `silo-pkg v3.15.2`, and the upstream SDK fix accepting HTTP `204` when removing bucket replication.

## Dependencies and delivery {#delivery}

Console 2.5.1 builds with Go **1.27.3**, Node **24.22.1**, Vite **8.3.5**, GoReleaser **2.19.0**, silo-pkg **3.15.2**, mcli **20261026**, and upstream minio-go **`320af050c445`**, while keeping `tablewriter v0.0.5`, `go-humanize v1.0.1`, `go-runewidth v0.0.29`, and `go-systemd v22.6.0` pinned for output and platform compatibility (see the [shared dependency and security inventory](/blog/release/silo-20261026/#runtime-fixes)).

The [GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) provides platform binaries and archives, Linux packages, source tarballs, SHA-256 checksums, SPDX SBOMs, and Sigstore/GitHub provenance attestations. Windows archives now use `.zip` (Linux and macOS retain `.tar.gz`), and multi-architecture container images are published at `docker.io/pgsty/silo-console:v2.5.1` (see the [release contract](https://github.com/pgsty/silo-console/blob/v2.5.1/docs/release-contract.md) for verification commands).

Frontend assets and embedded bundles build reproducibly in isolated workspaces. The supported administration target is **pgsty/silo** (with best-effort upstream MinIO compatibility), and all existing `CONSOLE_*` environment variables, API routes, service names, and Go module paths remain unchanged; see the [Console compatibility guide](/compatibility/console/) for API and embedding details.
