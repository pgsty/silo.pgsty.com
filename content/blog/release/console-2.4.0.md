---
title: "SILO Console 2.4.0 Released"
linkTitle: "SILO Console 2.4.0 Released"
date: 2026-09-08T22:51:37+08:00
author: "Vonng"
description: "Bounded object-browser pages and the accumulated correctness fixes since v2.3.0."
tags: [Release, console]
weight: 1
url: "/blog/release/console-2.4.0/"
---

[v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) was published
on 2026-09-08 from [`c103d08e`](https://github.com/pgsty/silo-console/commit/c103d08ec36aab8e08ba091d77b639158ce9f18f).
**September 16 follow-up:** [Console v2.4.1](/blog/release/console-2.4.1/) is the
current release. This article records the v2.4.0 behavior and dependencies.

## Released behavior {#changes}

- Object-browser directories load 100 entries per page by default, with choices
  of 50, 100, 250, 500 and 1000. Each page uses one S3 continuation-token request.
  Sorting, filtering and selection apply to the displayed page, not a complete
  directory scan; there is no unbounded “all” mode.
- Version deletion stays bound to the selected object and directory deletion to
  its prefix. Lifecycle edits preserve independent actions and unexposed
  settings; replication rule deletion is saved consistently.
- Transient network failures preserve sessions. Empty versioning state,
  malformed sidebar preferences and stale dropdown selections are handled.
- Embedded Console restores loopback proxy behavior when Server explicitly
  enables the policy; standalone trust defaults remain unchanged.
- Dependencies include pkg **v3.13.3**, MC source
  **`v0.0.0-20260908140805-c8aa5d25a63a`**, and upstream SDK **`0e78d3f18efe`**.
  This release consumed MC as source and did not itself publish a new mcli tag.

Correctly preserved Deny/NotResource clauses may reject requests that relied on
old deduplication defects. Restore already-lost clauses from the original policy
source. Embedders must copy the MC replacement from the
[tagged README](https://github.com/pgsty/silo-console/blob/v2.4.0/README.md).

## Later release {#unreleased}

[Console v2.4.1](/blog/release/console-2.4.1/) adds restricted shared downloads,
the password-permission split, streaming multi-object ZIPs, browser recovery
and verifiable release artifacts. It selects pkg v3.14.1 and mcli 20260916.
v2.4.0 uses the earlier browser-memory ZIP path. Read the
[password migration](/compatibility/password-permissions/) before upgrading.

The exact v2.4.0 source passed the complete Console CI matrix. The authoritative
historical record is its [tagged changelog](https://github.com/pgsty/silo-console/blob/v2.4.0/CHANGELOG.md),
[object-browser guide](https://github.com/pgsty/silo-console/blob/v2.4.0/docs/ObjectBrowser.md),
and [release assets](https://github.com/pgsty/silo-console/releases/tag/v2.4.0).
Later signature/provenance requirements do not retroactively apply to old assets.
