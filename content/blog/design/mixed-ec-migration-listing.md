---
title: "Mixed EC Layouts and Migration Listing"
linkTitle: "Mixed EC Migration Listing"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO Maintainers"
summary: >
  Why an object with two readable erasure-code layouts can disappear from decommission and rebalance listings, and why the narrow recount in PR #262 is the minimum safe repair.
tags: [Design, Storage Pools, Erasure Coding, Migration]
weight: 11
draft: false
url: "/blog/design/mixed-ec-migration-listing/"
---

This record covers [issue #261](https://github.com/pgsty/silo/issues/261) and [PR #262](https://github.com/pgsty/silo/pull/262), updated against main at [0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b) after the #276 follow-up. The fix was merged through maintainer PR [#267](https://github.com/pgsty/silo/pull/267); #262 was the superseded duplicate.

## Short answer {#tldr}

The report is real. A successful degraded overwrite can leave two EC layouts for one unversioned object: a newer copy on the drives that were online and an older copy on the drives that were offline. GET and ListObjectsV2 can choose the newer readable majority. Decommission and rebalance use an all-versions walk, where the metadata merge can choose the older layout as its reference and then count only that layout. If it is below quorum, the object disappears from the migration list. The migration reports success, and removing the old pool loses the object.

PR #262 described the right repair. It removes one overly narrow condition from the existing mixed-EC recount, keeps the recount limited to ordinary single null versions, and adds tests for quorum, stream order, migration, and excluded metadata shapes. That fix is now merged through #267, which also added the end-to-end pool-removal regression coverage.

## When it happens {#trigger}

The sequence needs all of these conditions:

1. The object is stored in an erasure-coded set.
2. A write or overwrite happens while one or more drives are unavailable.
3. Availability-optimized storage writes the new object with a different parity or layout on the drives that are available.
4. The old metadata remains on the drives that were unavailable.
5. The repair attempt does not finish before decommission or rebalance scans the set.

The object is still readable when one EC group has quorum. The failure depends on the order in which the old and new metadata streams arrive. That is why the report is intermittent across drive arrangements even though the underlying state is deterministic.

## Where the behavior came from {#history}

The mixed-layout state is a normal consequence of availability-optimized degraded writes. The relevant SILO listing repair was introduced in [e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067) on 2026-10-16 while fixing related listing consistency issues. That repair deliberately enabled a recount for latest-only reads. The all-versions migration callers continued using the old selection path.

The result was a split contract:

| Caller | Request mode | Main behavior |
| --- | --- | --- |
| GET and ListObjectsV2 | latest-only | Recount eligible mixed EC groups and select a readable quorum. |
| ListObjectVersions, decommission, rebalance, and some Walk callers | all versions | Stop after the ordinary merge fails; a minority layout can hide the readable majority. |
{.wide .expand}

The defect was therefore introduced by an incomplete scope boundary in the 2026-10-16 repair. The underlying degraded metadata state can be older; the data-loss path became visible when only one family of callers learned how to recover from it.

## Root cause in simple terms {#root-cause}

Imagine sixteen drives. Four still contain the old 12+4 metadata and twelve contain a newer 8+8 metadata. Both groups describe the same null version, but the EC headers differ.

The merge walks the metadata streams. When it sees the disagreement, it can switch to counting entries that match the current EC reference. The four old entries do not meet the quorum of eight, so the merge returns no version. The code that already repaired latest-only reads then performs a second, narrow recount and discovers that the twelve newer entries do meet quorum.

The migration path passed requestedVersions equal to zero. The mixed-EC fallback was guarded by requestedVersions equal to one. The same metadata therefore produced a readable object for GET and an empty migration entry for decommission.

The guard is important. We must not combine arbitrary EC groups, version histories, UUID collisions, delete markers, free versions, or legacy and partial headers. The safe case is an object where every non-empty stream contains exactly one ordinary null version with a modern EC header. In that case, listing the latest version and listing all versions are the same logical question.

## Impact {#impact}

The operator sees normal behavior until the pool is removed:

- GET returns the newer data.
- ListObjectsV2 returns the key.
- Decommission and its final check do not see the key.
- Rebalance leaves the key in the source pool.
- ListObjectVersions on an unversioned or suspended bucket can also omit the key.
- After the old pool is removed, GET and both listings lose the object.

The issue is serious because the migration status is falsely successful. A retry is not necessarily possible after the source pool has been removed.

## Options {#options}

### Option 1: require a successful heal before migration {#option-1-require-a-successful}

This is a useful operational mitigation, but it is not a complete fix. The drives may remain unavailable, MRF may give up, and GET does not necessarily enqueue a heal when the old metadata is valid. Blocking every migration until the layout is uniform would also make pool retirement depend on unrelated drive recovery.

### Option 2: force migration callers to use latest-only listing {#option-2-force-migration-callers}

This duplicates listing policy in decommission and rebalance and risks changing their version-history behavior. It also leaves ListObjectVersions and Walk callers inconsistent.

### Option 3: merge all EC groups or lower the quorum {#option-3-merge-all-ec}

This is unsafe. Two groups below quorum must not be added together merely because they describe the same key. Lowering the quorum can select data that cannot be reconstructed.

### Option 4: broaden the existing narrow recount {#option-4-broaden-the-existing}

This is the smallest safe change. The recount runs only after the normal selection fails, only for non-strict reads, and only for a single ordinary null version per stream. PR #262 applies exactly this option.

## PR assessment {#pr}

PR #262 changes the mixed-EC condition so it no longer depends on latest-only mode. It adds:

- the same selection assertions for requestedVersions one and zero;
- exclusions for strict, UUID, delete-marker, free-version, history, legacy, and partial EC metadata;
- migration tests for both decommission and rebalance;
- the new regression test in the race workflow.

The focused baseline tests fail on main for the readable mixed-EC cases and pass on the PR. The new tests also preserve the important negative cases where sub-quorum groups must remain unresolved. The patch changes no API, configuration, disk format, metric, or dependency.

The recommendation is accepted in the merged implementation: the narrow recount is sufficient for #261 and does not add a broad repair mechanism that could hide an unsafe metadata state. The original issue is closed as completed and #262 is closed as superseded by #267.

## Residual limits {#limits}

The patch selects a readable group; it does not heal the old group. Operators should still run healing when the unavailable drives return. It also cannot restore an object already lost by a previous completed decommission. The implementation remains best effort for other malformed or mixed version histories, by design.

## Verification references {#verification}

- Issue: [#261](https://github.com/pgsty/silo/issues/261)
- PR: [#262](https://github.com/pgsty/silo/pull/262)
- Merged maintainer PR: [#267](https://github.com/pgsty/silo/pull/267)
- Merge commit: [a7310d59f](https://github.com/pgsty/silo/commit/a7310d59fe307ae7fc4b57dc190b5e0c3de1a56a)
- Fix commit: [5eb6433f0](https://github.com/pgsty/silo/commit/5eb6433f0)
- Earlier mixed-EC listing repair: [e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067)
