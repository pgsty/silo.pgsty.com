---
title: "Pool Decommission and Rebalance: Nested Keys, Concurrent Sibling Deletes, and Offline-Drive Quorum"
linkTitle: "Pool Decommission Physical Progress"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  Why upstream pool decommissioning misses child keys hidden behind a parent object, strands already-migrated versions when a sibling version is concurrently deleted, and relies on quorum listing for its final empty check—and how bounded physical-progress rescans with erasure-quorum offline drive tolerance solve all three.
tags: [Design, Multi-Pool, Decommission, Rebalance, Erasure Coding]
weight: 10
draft: false
url: "/blog/design/pool-decommission-physical-progress/"
---

This record covers three upstream-inherited pool migration and retirement defects across `cmd/erasure-server-pool-decom.go`, `cmd/erasure-server-pool-rebalance.go`, and `cmd/erasure-server-pool-migration.go` ([#293](https://github.com/pgsty/silo/issues/293), [#340](https://github.com/pgsty/silo/issues/340)), continuing the [November 1 Pool Migration Integrity Review](/blog/design/pool-migration-integrity-review/).

**Status:** Merged to `main` in [`5dc4bd6a1`](https://github.com/pgsty/silo/commit/5dc4bd6a1d286608783529ba871e5eadd76a03c9) and [`8587e061b`](https://github.com/pgsty/silo/commit/8587e061bb7a407e6c98f7020f6475a96500e700); scheduled for the next post-[`20261109`](/blog/release/silo-20261109/) Server release.

## Short Answer {#tldr}

Retiring a storage pool (`mcli admin decommission start`) must satisfy two opposing requirements at once: **never mark a pool `Complete` while unmigrated user data or remote-tier cleanup obligations remain on its drives**, and **finish reliably under real-world workloads** (nested S3 key hierarchies, concurrent client deletes, and dead hardware drives within erasure parity).

Inherited from upstream MinIO, the migration engine violated both sides:

1. **Parent objects hid nested child keys (`#293`):** On disk, an object named `a/b` stores `<bucket>/a/b/xl.meta`, while a child object `a/b/c` stores `<bucket>/a/b/c/xl.meta` inside the same directory. When the scanner saw `xl.meta` at `a/b`, it yielded `a/b` as a leaf object without descending into `a/b/c`. A single-pass decommission migrated and removed `a/b/xl.meta`, leaving `a/b/c` behind on the retiring pool.
2. **Concurrent sibling-version deletes stranded migrated versions (`#340`):** Both decommission and rebalance cleaned up source versions only when `migratedCount == len(fivs.Versions)`. If a client or lifecycle worker deleted one sibling version while the other versions of that key were being copied to a destination pool, the equality check failed and **none** of the already-copied versions were removed from the source pool.
3. **Quorum-only final empty check vs. failed drives:** Upstream's `checkAfterDecomBucket` relied on standard quorum listing, which could report a bucket empty even when corrupt or split `xl.meta` files remained on online drives. Conversely, checking drives directly without tolerating `errDiskNotFound` within the erasure set's read quorum would block operators from retiring an aging pool that already has a dead drive—the primary operational reason pools are decommissioned.

The repair introduces bounded rescans driven strictly by **verified physical version removals**, retires each migrated candidate version independently of concurrently deleted siblings, and verifies physical emptiness across **every online drive** while tolerating offline (`errDiskNotFound`) drives within `setDriveCount - readQuorum` (except where all drives are required to prove that no `FreeVersion` remote-tier cleanup record remains).

## Classification {#assessment}

| Aspect              | Assessment                                                                                                                                                                                                                                                                                                                                                  |
| :------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nature**          | Incomplete single-pass tree walk (`#293`), all-or-nothing sibling cleanup gate (`#340`), and quorum-vs-physical completion verification. Inherited from upstream MinIO.                                                                                                                                                                                     |
| **Upstream origin** | Nested parent/child walk limitation in `listObjectsToDecommission` (`minio/minio` pool decommission baseline) and sibling-count gate `decommissioned == len(fivs.Versions)` in [`9af6c6cee`](https://github.com/pgsty/silo/commit/9af6c6ceeff5d63dc90c8e0fe356c4d91f8e6795) (`2023-06-21`, [minio/minio#17482](https://github.com/minio/minio/pull/17482)). |
| **Affected scope**  | Multi-pool (`2+` server pools) deployments running `decommission` or `rebalance` on upstream MinIO and SILO Server `20261109` and earlier.                                                                                                                                                                                                                  |
| **Impact**          | Decommission fails at final check or leaves hidden child objects / migrated duplicates on the draining pool; concurrent deletes force repeated manual decom restarts.                                                                                                                                                                                       |
{.wide .expand}

---

## 1. Upstream Provenance and Root Causes {#root-cause}

### 1.1 Parent Object Occluding Child Prefixes (`#293`) {#nested-keys}

S3 has a flat key namespace where both `logs/2026` (an object) and `logs/2026/11.gz` (another object) may coexist in the same bucket. On `xlStorage`, both map onto a single POSIX directory tree:

- `logs/2026` -> `<bucket>/logs/2026/xl.meta`
- `logs/2026/11.gz` -> `<bucket>/logs/2026/11.gz/xl.meta`

During a listing pass, `ReadDir` / `metache` treats any directory containing `xl.meta` as an object entry and stops descending into subdirectories beneath it. During `decommissionBucket`, Pass 1 discovers `logs/2026`, copies it to another pool, and deletes `<bucket>/logs/2026/xl.meta` from the source drives (leaving `<bucket>/logs/2026/` on disk as a plain directory containing `11.gz/`). Because upstream `decommissionBucket` walked each bucket only once before calling `checkAfterDecomBucket`, `logs/2026/11.gz` was never migrated: either `checkAfterDecomBucket` now saw `logs/2026/11.gz` and failed the entire decommission job, or—if below quorum—stranded it.

### 1.2 All-or-Nothing Sibling Cleanup Gate (`9af6c6cee`) {#sibling-gate}

In [`9af6c6cee`](https://github.com/pgsty/silo/commit/9af6c6ceeff5d63dc90c8e0fe356c4d91f8e6795) (`2023-06-21`), upstream gated source-pool version cleanup in both `decommission` and `rebalance` on:

```go
if decommissioned == len(fivs.Versions) {
    // delete migrated versions from source pool
}
```

On an active bucket, `fivs.Versions` is a point-in-time listing snapshot. Suppose key `k` has versions `[v3, v2, v1]`. Versions `v3` and `v2` copy cleanly to Pool 1 (`decommissioned = 2`), while a client concurrently deletes `v1` via `DELETE /bucket/k?versionId=v1` before the worker reaches `v1` (`ObjectNotFound` / `VersionNotFound`). Even though `v3` and `v2` are durably stored on Pool 1 and `v1` was intentionally deleted by the user, `decommissioned (2) != len(fivs.Versions) (3)` skipped source cleanup completely—leaving `v3` and `v2` duplicated on the draining pool.

### 1.3 Physical Verification vs. Failed Drives during Retirement {#offline-drives}

To ensure no hidden, split-brain, or corrupt `xl.meta` files remain when a pool is retired, `checkAfterDecomBucket` must inspect the physical drives of each erasure set rather than trusting high-level S3 listing alone (which suppresses sub-quorum and corrupt entries). However, requiring *every* configured drive slot (`len(disks)`) to respond online breaks the most common real-world decommission scenario: retiring an older server pool where `1` or `2` drives have already failed permanently (`errDiskNotFound`), well within the set's parity budget (for example, `1` dead drive in an `EC:4` 8-drive or 16-drive set).

---

## 2. Solution Design: Why It Is Necessary and Sufficient {#fix}

Commits [`5dc4bd6a1`](https://github.com/pgsty/silo/commit/5dc4bd6a1d286608783529ba871e5eadd76a03c9) and [`8587e061b`](https://github.com/pgsty/silo/commit/8587e061bb7a407e6c98f7020f6475a96500e700) resolve all three issues through three cooperating invariants:

1. **Candidate-level source retirement (`retireMigratedSourceVersions`):**
   - Each version that actually copied to a destination pool is appended to `candidates` (recording its exact `VersionID`, `ModTime`, `Type`, and transition state).
   - Source cleanup runs for every version in `candidates` regardless of whether a sibling version in `fivs.Versions` disappeared concurrently—still re-verifying under the object lock that the destination pool holds the migrated version and that shared remote-tier references are preserved (`deleteIfMigrated`).
   - Safe `FreeVersion` tier-cleanup records whose remote object has already been swept are retired via `retireDrainedFreeVersions`, while `FreeVersion` records that still own unswept remote-tier data are intentionally retained.
2. **Bounded rescans gated strictly on verified physical removals (`countAbsentMigrationVersions`):**
   - After migrating a batch of keys in `decommissionBucket`, the worker rescans the bucket **if and only if** the pass physically removed at least one version or `FreeVersion` from the source drives—exposing any child prefixes (`a/b/c`) that were previously hidden behind a parent `a/b/xl.meta`.
   - Crucially, a logical `NotFound` from S3/quorum read is **never** counted as physical progress on its own: `countAbsentMigrationVersions` reads raw `xl.meta` across the erasure set's online drives (`ReadXL`) to confirm the version is genuinely gone from every online drive. If an object has corrupt or split-quorum metadata that cannot be migrated or physically removed, `physicalRemoved == 0`, so the loop terminates cleanly instead of spinning forever, and `checkAfterDecomBucket` surfaces an actionable error. Context cancellation (`ctx.Err()`) also aborts immediately and propagates as an error rather than masquerading as an empty scan.
3. **Read-quorum offline drive tolerance with strict online remnant rejection (`8587e061b`):**
   - Both `countAbsentMigrationVersions` and `checkAfterDecomBucket` (`hasPhysicalMetaOnSet`) inspect **every online drive** in each erasure set:
     - Any remaining `xl.meta` on *any* online drive (`xl.meta` present, corrupt `xl.meta`, or unexpected I/O / `ListDir` error) immediately fails the empty check—preventing silent data loss even for sub-quorum remnants.
     - Offline / missing drives (`errors.Is(err, errDiskNotFound)`) are tolerated **up to `len(disks) - readQuorum`** (i.e., online drives `>= readQuorum`, where `readQuorum = getDefaultParityBlocks` complement `N - M`). If offline drives exceed parity (`online < readQuorum`), verification fails closed (`errErasureReadQuorum`) because an entire object could reside solely on the offline majority.
     - **Exception preserved for remote-tier safety:** `readTierHistory` (`FreeVersion` ownership check before deleting transitioned cold-tier data) continues to require **all** drives in the set to respond before declaring tier cleanup unneeded, so an offline drive holding the last `FreeVersion` record can never cause premature remote-tier deletion.

### Why This Is Necessary and Sufficient {#sufficiency}

- **Necessary:**
  - Without rescanning after parent removal, arbitrarily nested `a` -> `a/b` -> `a/b/c` chains leave depth $\ge 2$ keys unmigrated.
  - Gating rescans on logical `ObjectNotFound` instead of physical `ReadXL` absence would loop indefinitely whenever a sub-quorum or expired-split `xl.meta` stays on disk while returning logical `404`.
  - Requiring 100% of drives online in `checkAfterDecomBucket` blocks retiring pools with a single dead disk; relaxing checks on *online* drives to quorum would overlook 1-drive or $(K-1)$-drive remnants that were never migrated.
- **Sufficient:** Every finite directory tree of depth $D$ completes in at most $D + 1$ passes (`physicalRemoved > 0` decreases the finite count of on-disk versions monotonically on each rescan), concurrent sibling deletes no longer strand migrated copies, and single/multi-drive failures within parity no longer block pool retirement.

---

## 3. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                                    | Engineering Trade-Off & Operational Cost                                                                                                                                                                                                                                                                                                                                                   |
| :----------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Extra `ReadXL` / physical `ListDir` verification**         | Confirming physical version absence (`countAbsentMigrationVersions`) and walking physical directories in `checkAfterDecomBucket` adds metadata-only RPCs on the draining pool. Because decommissioning is an offline/background administrative lifecycle task and only inspects keys just processed (plus one final empty-tree walk), S3 foreground latency on active pools is unaffected. |
| **Multi-pass rescans on deeply nested object+prefix mixes**  | Buckets that store objects at *both* `p` and `p/child` run an extra listing pass per nesting level exposed. Standard buckets where prefixes are pure directories (no `xl.meta` on parent prefixes) finish without extra rescans once drained.                                                                                                                                              |
| **Intentional block when offline drive meets `FreeVersion`** | If a draining pool has an offline drive *and* holds transitioned objects with unresolved `FreeVersion` remote-tier cleanup records on that set, `readTierHistory` still refuses to discard tier ownership until either the drive reconnects or tier references are resolved—prioritizing zero remote data loss over forced pool removal.                                                   |
{.wide .expand}

## Verification {#verification}

`cmd/erasure-server-pool-migration-progress_test.go` verifies nested parent/child exposure (`a` + `a/b`), concurrent sibling-version deletion during migration, corrupt/split metadata non-spinning termination, cancellation propagation, single-drive-offline (`errDiskNotFound`) pool retirement success, and beyond-parity offline drive rejection. See the [Pool Decommission Operations Guide](/operations/deployments/baremetal-decommission-server-pool/#candidate-progress) and [Pool Migration Integrity Review](/blog/design/pool-migration-integrity-review/).
