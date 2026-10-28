---
title: "Multi-Pool Deletion: Preserve the Latest Copy on Failure"
linkTitle: "Multi-Pool Delete Safety"
date: 2026-10-24
lastmod: 2026-10-26
author: "Ruohang Feng"
summary: "Why error reporting and online-drive checks were insufficient for multi-pool deletion, how staged cleanup protects the authoritative copy, and the measured performance and compatibility costs of PR #257."
tags: [Design, S3, Storage, Performance]
weight: 11
draft: false
url: "/blog/design/multi-pool-delete-safety/"
---

**Decision, October 24, 2026: merge the corrected [PR #257](https://github.com/pgsty/silo/pull/257) (shipped in [Server 20261026](/blog/release/silo-20261026/#server-20261026)).** Commit [`aafe4f8886`](https://github.com/pgsty/silo/commit/aafe4f8886a060ec698400043bee2f60e22140fd) fixes the multi-pool deletion failures reported in [issue #256](https://github.com/pgsty/silo/issues/256) and closes the in-flight failure window after preflight checks. The core invariant is direct: **finish cleaning up non-authoritative copies in other pools before deleting the authoritative copy that determines current reads.**

Denis Babchuk reported the issue and contributed the initial patch. Code review reproduced the failures, identified a remaining execution-time failure window in bulk deletion, and extended the fix with two-stage execution, per-item response identity preservation, partial-deletion retry handling, and shared tier-object protection.

## Background and Earlier Work {#background}

SILO uses capacity-weighted pool allocation. Overwriting an unversioned key can place the new value in pool B while an older physical copy remains in pool A. Reads resolve the latest logical object across pools, keeping the stale copy invisible until a subsequent delete encounters an error partway through execution.

Earlier multi-pool consistency fixes relate to this change as follows:

| Earlier work | What it protects | Relationship to this change |
| --- | --- | --- |
| [#178](https://github.com/pgsty/silo/pull/178) | Shared object locking and cross-pool reconciliation for conditional deletion and addressed versions | Provides the locking and reconciliation foundation reused here |
| [#199](https://github.com/pgsty/silo/issues/199), fixed by [#207](https://github.com/pgsty/silo/pull/207) | Conditional `PUT` evaluates the current logical object across pools | Retains capacity-weighted placement |
| [#248](https://github.com/pgsty/silo/pull/248), shipped in Server 20261018 | Pool migration cannot overwrite a newer payload or drop a delete marker | Protects rebalance and decommission paths |
| [#245](https://github.com/pgsty/silo/pull/245), closed without merging | Proposed keeping overwrites in their existing pool | Neither experiment met its performance target; deletion safety does not depend on overwrite affinity |

Those earlier changes did not cover ordinary unconditional deletion or bulk `DeleteObjects`. See [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/) for the shared locking and migration design, and [Overwrite Pool Affinity](/blog/design/overwrite-pool-affinity/) for the evaluation that retained the existing allocator.

## The Failure: A Delete Can Expose an Overwritten Value {#problem}

Consider this initial state:

```text
Pool A: reports/latest.json = "old"     ModTime = T1
Pool B: reports/latest.json = "latest"  ModTime = T2, T2 > T1
GET:    "latest"
```

If both pools execute a delete in parallel, pool B can finish removing `"latest"` before pool A fails with an I/O error. A single `DELETE` then returns an error to the caller, but the latest acknowledged value is already gone and the next `GET` returns `"old"`.

Issue #256 documented four symptoms:

| Operation | Original failure behavior |
| --- | --- |
| Ordinary unversioned `DELETE` | Returns an error after removing the latest copy, exposing an older overwritten value |
| Bulk `DeleteObjects` | A successful pool result masks another pool's deletion failure |
| Bulk deletion with an explicit version ID | Reports success even though the addressed version remains in another pool |
| Versioned single `DELETE` | Attempts to write the delete marker in an unwritable holding pool even when another readable holding pool can accept it |

Running the author's 11 regression subtests showed 10 failures on baseline `main` and 11 passes on the initial PR. However, review found that bulk deletion could still lose the latest copy when a drive failed after the preflight check.

### Why Preflight Was Not Enough {#preflight}

The initial patch checked whether affected erasure sets had enough online drives before starting bulk deletion. While that rejects known offline quorum loss early, online drive counts cannot guarantee that subsequent metadata reads, writes, or shard deletions will succeed.

Review tested a 45-case fault-injection matrix that started with all drives online, allowed the authoritative pool to finish deleting the latest copy, and then injected a failure inside `DeleteVersions` on the non-authoritative pool (covering simulated `EIO`, simulated storage disconnects, and real filesystem permission errors across every authoritative-pool position in two- and three-pool layouts, for unversioned, explicit `null`, and UUID-versioned objects):

- **Baseline `main` ([`000e653038`](https://github.com/pgsty/silo/commit/000e6530386433ff3800f9e0b2d01754ce159c48))**: Masked the per-item failure in all 45 cases.
- **Initial PR ([`a30270d9ba`](https://github.com/pgsty/silo/commit/a30270d9ba5bc6a5b9f47aa43850465a9b6a5e84))**: Reported the error, but lost the latest value in all 30 unversioned and explicit-`null` cases. The 15 UUID cases used identical payloads across copies of the same version and retained a copy while reporting the error.

Review also uncovered a separate response-identity bug: an early-error `DeletedObject` omitted `ReplicationState`, which the HTTP handler requires to reconstruct the original request entry's identity. In a signed bulk request with two blocked replicated version purges, the response returned one error entry and one empty deleted entry. Preserving only the key and version ID was insufficient.

## Per-Item Deletion Contract {#contract}

Under the existing shared object write lock, the repair enforces the following per-item rules:

1. Resolve the addressed object or version across pools and identify its authoritative copy.
2. Complete cleanup in every non-authoritative pool (Stage 0) before attempting to delete the authoritative copy (Stage 1).
3. If non-authoritative cleanup fails, return an error for that exact request item and leave its authoritative copy untouched.
4. Allow independent items in the same batch to complete normally.

Key operational boundaries:

- **Per-item protection rather than whole-batch rollback**: If an object has copies in three pools, Stage 0 may remove one older copy before failing on the second older copy. Stage 1 is then skipped so the healthy authoritative copy remains intact, and unrelated items that succeeded in the same batch are not rolled back.
- **In-flight errors on the final authoritative delete**: Once Stage 0 succeeds across all non-authoritative pools, Stage 1 deletes the authoritative copy. If a disk failure occurs midway through Stage 1 itself, the caller should inspect the object state and retry after recovery. The two-stage ordering specifically prevents removing the authoritative copy *when another pool's cleanup has failed*.
- **Explicit version or marker deletion**: Deleting an explicitly addressed historical version or delete marker legitimately makes the next older retained version current under standard S3 versioning rules.

## The Implemented Design {#implementation}

### Single-Object Deletion {#single-delete}

Ordinary unversioned deletion retires older copies before the newest copy and stops at the first failure. Conditional deletion and explicit-version deletion continue using `deleteObjectReconciled`. If the selected unversioned object has completed a tier transition, it also routes through `deleteObjectReconciled` so local cleanup preserves shared remote references.

When creating a delete marker for a single object held in multiple pools, pool selection skips pools known to lack delete quorum and chooses a readable holding pool that passes the check.

### Bulk Data Deletion in Two Stages {#bulk-delete}

The new [`deleteObjectsReconciled`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-consistency.go#L541) reuses the existing namespace write locks and `objectPoolInfos` resolver without introducing a second locking domain.

Lookup concurrency is capped at 32 objects. Each lookup inspects all pools for the addressed version, orders candidates by `ModTime`, and breaks exact timestamp ties by the lowest pool index to match read selection. Unreadable metadata is treated as an error rather than evidence of absence.

```text
Hold the shared write locks for the batch's unique keys
Resolve each item's authoritative pool

Stage 0: bulk cleanup in all non-authoritative pools
         record errors against the original items

Stage 1: delete the authoritative copies only for items
         whose Stage 0 cleanup succeeded

Process marker creation after data/version removal
Release the locks
```

**Pools still execute in parallel within each stage** using the existing erasure-set and disk-level bulk interfaces. Because two objects in the same batch can have their authoritative copies in different pools, a fixed global pool order cannot work; stages must be partitioned per item by authoritative pool.

Stage 0 also includes non-authoritative pools where lookup reported the object absent: a read-quorum absence does not prove that a temporarily unavailable drive holds no stale shard. If that pool cannot complete the delete, the item conservatively returns an error.

Every result entry initializes with the original key, version ID, and full `ReplicationState`, and explicit index mappings preserve request order across filtering and re-batching. The online-drive preflight remains in place to reject known quorum loss early, while two-stage execution enforces runtime safety.

### Versioning and Marker Ordering {#markers}

The batch entry point separates physical deletion from delete-marker creation using the same versioning rules as the lower layer:

| Request | Action |
| --- | --- |
| Explicit `versionId=null` or UUID | Physically remove the addressed version using two-stage cleanup in multi-pool batches |
| No version ID, ordinary unversioned key | Physically remove data using two-stage cleanup |
| No version ID, versioning enabled | Create a delete marker and retain historical versions |
| No version ID, versioning suspended | Create or replace the `null` delete marker |
| Prefix-specific versioning configuration | Evaluate `PrefixEnabledFn` for the key alongside the suspended state |

Physical deletion runs before marker creation, preserving execution order when a single batch explicitly purges a `null` version and creates a new delete marker for the same key. Marker-only batches continue using their existing path (see [Compatibility, Retry, and Operational Boundaries](#limits) for degraded-mode marker edge cases).

### Retry After Partial Disk Cleanup {#quorum-retry}

A second failure mode arises when a pool deletes a version from some drives before failing on the remaining drives. On retry, drives that just deleted the version return success while drives that already deleted it on the first attempt return `errFileNotFound` or `errFileVersionNotFound`. Counting those two response groups separately can prevent either group from reaching quorum.

The fix in [`erasureObjects.DeleteObjects`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-object.go#L1894) combines successful removals with `errFileNotFound` and `errFileVersionNotFound` **only for pure physical deletion** (unknown I/O errors never count toward quorum). Delete-marker creation and replication-state updates still require actual successful writes to reach quorum so an absent version cannot falsely acknowledge a marker or metadata transition that was never written.

Both single-version and bulk deletion paths (including marker writes on this path) use a delete quorum of `floor(N/2) + 1`, where `N` is the erasure set's drive count.

### Shared Tier Objects {#tier}

Physical copies in different pools can reference the same remote tier object, including when one copy has been restored locally. Retiring a non-authoritative local record must not enqueue that remote tier object for garbage collection while the retained authoritative copy still references it.

Bulk items with completed tier transitions therefore route through the existing per-object reconciler, preserving `SkipFreeVersion`, replication state, and prefix versioning options. That subset executes sequentially, which also prevents concurrent metadata updates for duplicate entries in the same batch, while ordinary local objects stay on the two-stage bulk path. Added regression tests cover shared and distinct remote references, restored copies, pre-authoritative failure, and explicit `SkipFreeVersion` requests.

## Verification at the Final Revision {#verification}

The commits evaluated during review and verification are:

| Revision | Role |
| --- | --- |
| [`000e653038`](https://github.com/pgsty/silo/commit/000e6530386433ff3800f9e0b2d01754ce159c48) | Baseline `main` (without #245 overwrite affinity) |
| [`a30270d9ba`](https://github.com/pgsty/silo/commit/a30270d9ba5bc6a5b9f47aa43850465a9b6a5e84) | Initial PR head; reproduced the post-preflight failure window |
| [`3c82748e14`](https://github.com/pgsty/silo/commit/3c82748e14495ed403739e60b7e669c977a488c1) | Added two-stage bulk cleanup, response identity preservation, and partial-deletion retry |
| [`a2073d2514`](https://github.com/pgsty/silo/commit/a2073d25142ced87b9bde8afa38aef2d0383768e) | Final PR head, adding shared-tier protection |
| [`aafe4f8886`](https://github.com/pgsty/silo/commit/aafe4f8886a060ec698400043bee2f60e22140fd) | Merged `main` (source tree identical to `a2073d2514`) |

The committed fault tests start with all drives online, inject failures inside `DeleteVersions`, and assert both an accurate per-item error and **zero deletion attempts against that item's authoritative copy**, verifying `GET` during failure, `GET` and version listing after recovery, retry completion, and normal completion of unrelated items:

| Coverage | Evidence in the merged tree |
| --- | --- |
| Post-preflight I/O failures, two/three pools, every authoritative position, unversioned/`null`/UUID | [`TestPoolsBulkDeleteKeepsLatestOnIOFailure`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-delete_test.go#L152) |
| Signed HTTP response identity with replication state | [`TestPoolsBulkDeleteReplicationIdentity`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-delete_test.go#L236) |
| Mixed null purge/marker, partial cleanup/retry, different authoritative pools | [Bulk ordering and retry tests](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-delete_test.go#L298) |
| Equal timestamps, unreadable metadata, shared lock/concurrent `PUT`, object-layer cancellation | [Selection and concurrency tests](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-delete_test.go#L410) |
| Physical-delete quorum versus marker/replication writes | [`TestBulkDeleteQuorumEvidence`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-delete_test.go#L552) |
| Shared tier references and restored objects | [`TestPoolsRetiringCopyPreservesSharedTierObject`](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-consistency_test.go#L1065) |
| Original single-delete, bulk-error, known-quorum-loss, and marker-placement regressions | [Original contribution's tests](https://github.com/pgsty/silo/blob/aafe4f8886a060ec698400043bee2f60e22140fd/cmd/erasure-server-pool-consistency_test.go#L1334) |

The new regressions fail deterministically against the initial PR's production code. The combined deletion, tier, and quorum test suite passed three consecutive `-race` runs before merge and an additional `-race` run after merge. Supplemental checks covered single-pool controls, prefix versioning configurations, directory and duplicate keys, Object Lock, version purges, and migration regressions.

Both [final-head Go CI](https://github.com/pgsty/silo/actions/runs/40075555190) and [merged-main Go CI](https://github.com/pgsty/silo/actions/runs/40076596611) passed full `cmd` and `internal` suites, race suites, static analysis, and cross-compilation for Linux, macOS, and Windows on amd64 and arm64, alongside [DCO](https://github.com/pgsty/silo/actions/runs/40075555131) and [VulnCheck](https://github.com/pgsty/silo/actions/runs/40076596621).

Regression test command:

```bash
go test -race ./cmd \
  -run '^Test(Pools(Delete|BulkDelete|RetiringCopyPreservesSharedTierObject)|BulkDeleteQuorumEvidence)' \
  -count=1 -timeout=5m
```

Live `mcli` verification ran against a two-pool server process (four directory drives per pool): populate data on the baseline binary, restart onto the fixed binary to verify reads, bulk deletes, UUID version deletes, enabled/suspended delete markers, and new writes, and then restart the baseline binary over the same data directories.

## Performance: Measured Deletion Cost {#performance}

Benchmarks compare baseline `000e653038` against final PR head `a2073d2514` (identical to merged `main`).

### Method {#performance-method}

- **Hardware**: Apple M5 Max (18 physical cores, 128 GiB RAM) with one 8 TB Apple SSD (APFS, ~95% full during testing; all logical directory drives shared this physical device).
- **Configuration**: Four directory drives per pool (EC 2+2), 4 KiB objects, 8 concurrent workers, `GOMAXPROCS=8`, exercising the object layer directly.
- **Matrix**: Five `pools / copies` layouts (where "copies" denotes physical copies of one logical object across pools rather than erasure shards), testing both single `DELETE` (1,024 requests per run) and 64-object bulk deletes (64 requests / 4,096 objects per run).
- **Sampling**: Three alternating pairs per layout and operation (baseline→fixed, fixed→baseline, baseline→fixed), recreating the identical initial state before timing each run. Total: 60 run samples, 30,720 single-delete requests, 1,920 bulk requests, and 153,600 logical objects deleted with zero errors.

### Results and Variation {#performance-results}

Throughput is measured in logical objects per second, showing the three-run median and observed range; **paired change is the median of the three paired percentage changes**.

| Pools / copies; operation | Baseline median [range] | Fixed median [range] | Paired change |
| --- | ---: | ---: | ---: |
| 1 / 1; `DELETE` | 1,286 [1,193–1,292] | 1,347 [1,269–1,371] | +6.1% |
| 1 / 1; bulk 64 | 1,786 [1,739–1,809] | 1,818 [1,680–1,982] | +4.5% |
| 2 / 1; `DELETE` | 1,350 [1,272–1,363] | 1,304 [1,270–1,327] | −1.7% |
| 2 / 1; bulk 64 | 1,477 [1,468–1,740] | 1,453 [1,149–1,604] | −7.8% |
| 2 / 2; `DELETE` | 560 [546–641] | 534 [469–534] | −16.3% |
| 2 / 2; bulk 64 | 606 [528–695] | 620 [546–707] | +2.2% |
| 3 / 1; `DELETE` | 988 [722–994] | 1,053 [974–1,130] | +13.6% |
| 3 / 1; bulk 64 | 1,338 [1,269–1,383] | 1,120 [1,055–1,163] | −16.9% |
| 3 / 3; `DELETE` | 364 [323–371] | 354 [335–364] | −2.0% |
| 3 / 3; bulk 64 | 404 [367–450] | 365 [313–378] | −14.5% |

Per-request latency in milliseconds (covering the full 64-object batch for bulk calls, shown as baseline→fixed):

| Pools / copies; operation | P50, ms | P99, ms |
| --- | ---: | ---: |
| 1 / 1; `DELETE` | 5.69 → 5.50 | 15.06 → 14.37 |
| 1 / 1; bulk 64 | 277.28 → 280.00 | 406.23 → 385.23 |
| 2 / 1; `DELETE` | 5.46 → 5.47 | 14.09 → 14.88 |
| 2 / 1; bulk 64 | 317.10 → 346.26 | 635.16 → 463.78 |
| 2 / 2; `DELETE` | 12.91 → 13.76 | 35.86 → 45.54 |
| 2 / 2; bulk 64 | 823.19 → 752.78 | 1,315.81 → 1,297.48 |
| 3 / 1; `DELETE` | 7.23 → 6.42 | 22.09 → 20.20 |
| 3 / 1; bulk 64 | 361.73 → 444.34 | 669.84 → 732.27 |
| 3 / 3; `DELETE` | 20.35 → 21.00 | 50.75 → 48.92 |
| 3 / 3; bulk 64 | 1,236.42 → 1,392.63 | 1,697.38 → 2,079.27 |

P99 uses the nearest-rank method (with 64 requests per bulk run, P99 is close to the per-run maximum). Single-pool controls retained their scheduling path and showed no regression. Three-pool bulk throughput decreased by **15–17%**, with a **22.5%** P99 increase on the 3-pool / 3-copy layout; two-pool / two-copy single deletion decreased by **16.3%** while bulk deletion in that layout stayed within run-to-run variation.

### Where the Cost Comes From {#performance-cost}

Single deletion serializes cleanup of older copies before the newest copy. Bulk deletion adds cross-pool metadata resolution and orders Stage 0 before Stage 1 while preserving cross-pool parallelism and disk batching within each stage. For a batch of $B$ items across $P$ pools with $N$ drives per erasure set, resolution inspects $B \times P$ pool states and the online preflight checks up to $B \times P \times N$ drive states. Because the shared key write locks span this work, the added latency can delay concurrent writes to the same keys. Accepting this multi-pool deletion cost is necessary to guarantee that failed deletes never drop the latest copy.

## Compatibility, Retry, and Operational Boundaries {#limits}

- **Error codes and client retries**: A single-delete write-quorum failure typically returns HTTP 503, whereas bulk `DeleteObjects` can return HTTP 200 with per-item errors such as `SlowDownWrite` in the response XML. With `MaxRetries=4`, the tested S3 SDK did not automatically retry an HTTP 200 bulk response containing per-item `SlowDownWrite`, while `mcli rm` surfaces the per-item failure. Callers must inspect bulk response entries and retry failed items after storage recovery, preserving the target `versionId` where applicable.
- **Concurrency and cancellation**: The shared object write locks serialize multi-pool deletion against participating pooled writes. Because the HTTP bulk-delete handler uses a detached background context, a client disconnect does not cancel an in-flight batch.
- **Suspended-bucket degraded bulk markers**: Supplemental testing noted an existing edge case already present on baseline `main`: in two- and three-pool layouts, when a versioning-suspended bucket with UUID-only history receives a bulk delete marker during drive degradation, explicitly purging the `null` marker after drive recovery can still return a quorum error (one run exposed the retained UUID history and another kept the marker). The marker-only bulk path remains unchanged here.
- **Object Lock and conditional delete**: Object Lock and retention authorization checks are unchanged. Batch XML ETag conditions remain unsupported; see [Conditional DELETE](/blog/design/conditional-delete/).
- **Upgrade and rollback**: No S3 parameter, RPC wire format, on-disk format, dependency, allocator rule, or configuration flag changes. During a mixed-version rolling upgrade, an unupgraded coordinating node still applies the older deletion path; rolling back to an older release cannot reconstruct a latest copy that was already lost.

## Rejected Alternatives {#alternatives}

| Alternative | Why it was rejected |
| --- | --- |
| Error aggregation alone | Prevents false-success replies, but cannot recover an authoritative copy that was already deleted |
| Online-drive preflight alone | Cannot prevent an I/O failure that occurs between the preflight check and the actual disk mutation |
| One fixed global pool order | Different objects in the same batch can have their authoritative copies in different pools |
| Serial per-object deletion for all bulk items | Unnecessarily sacrifices erasure-set and disk-level batching for ordinary local objects; the sequential per-object path is reserved only for items with shared tier references |
| Overwrite pool affinity (#245) | Regressed small-object writes and still left existing cross-pool duplicates, migrated copies, and interrupted cleanups to handle during deletion |
| Cross-pool rollback transactions or config flags | Two-stage per-item cleanup protects the authoritative copy without introducing distributed rollback state or extra configuration switches |
