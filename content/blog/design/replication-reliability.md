---
title: "Replication Reliability: Delete Completion, MRF Visibility, and Resync Cancellation"
linkTitle: "Replication Reliability"
date: 2026-09-09
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The engineering record for SILO #153, #152, and #137: classify delete-marker purges accurately, expose drops from the bounded MRF queue, and bind resync cancellation to per-run contexts. Includes Round 2 on worker-side purge classification and persisted MRF marker recovery (PR #196), and Round 3 on exact-version purges, marker healing, and stale queued creations.
tags: [Design, Replication, S3, Review]
weight: 7
draft: false
url: "/blog/design/replication-reliability/"
---

This article records the root-cause analysis, design tradeoffs, and validation across three rounds of replication reliability repairs shipped in [Server 20260916](/blog/release/silo-20260916/):

- **Round 1 ([PR #162](https://github.com/pgsty/silo/pull/162), merged as [`d1105bbb`](https://github.com/pgsty/silo/commit/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e)):** addresses [#153](https://github.com/pgsty/silo/issues/153), [#152](https://github.com/pgsty/silo/issues/152), and [#137](https://github.com/pgsty/silo/issues/137), covering operation classification at the HTTP handler entry, MRF drop observability, and the resync cancellation lifecycle.
- **Round 2 ([PR #196](https://github.com/pgsty/silo/pull/196), commit [`0c61128d2`](https://github.com/pgsty/silo/commit/0c61128d2)):** repairs the replication worker's delete exits, outer status aggregation, and the persisted MRF marker-recovery path (see [Round 2](#second-round)).
- **Round 3 (commits [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3), [`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0), and [`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb)):** repairs exact-version purge drive writes and quorum checks, delete-marker healing metadata retention, and pre-send revalidation for queued marker creations (see [Round 3](#third-round)).

## Overall Decision and the Surrounding Series {#decision}

Each fix repairs the reproduced invariant at the smallest boundary that owns it, preserves existing background recovery mechanisms, and proves convergence with deterministic tests.

| Issue | Confirmed defect in SILO | Selected repair |
| :-- | :-- | :-- |
| #153: delete-marker purge | Single-object DELETE classified a permanent deletion as marker replication; the remote marker disappeared while source purge remained `PENDING` | Classify by purge status, matching bulk delete, scanner/heal, and resync |
| #152: invisible MRF drops | The queue was already bounded, but internal drop counters did not reach administration or monitoring; object and delete worker arguments were reversed | Expose existing counters, warn at actual drop sites with deduplication, and align worker routing |
| #137: unreliable resync cancellation | One shared token could not stop multiple runs; blocking phases missed cancellation; stale runs could overwrite terminal state | Give each run an owned context, cancel by resync ID, and constrain registration, finalization, and state updates |

Two earlier fixes in the same series addressed adjacent invariants:

- [#136](https://github.com/pgsty/silo/issues/136) / [PR #138](https://github.com/pgsty/silo/pull/138) repaired **counter completeness**: receive and apply the final result before persisting terminal state, rather than waiting for the one-minute periodic flush.
- [#139](https://github.com/pgsty/silo/issues/139) repaired **outcome accuracy**: record success and failure from the target's actual replication response rather than assuming success because an object already exists at the destination.
- #137 repairs **cancellation and resource lifecycle**: canceling a run stops its walker, workers, and result consumer, and prevents stale runs from overwriting a newer run's state.

Authorization to use internal replication semantics is covered in [No I/O Before Auth, No Privilege From Headers](/blog/design/cors-replication-trust/). Authoritative Object Lock state across pools is tracked in [#133](https://github.com/pgsty/silo/issues/133) and repaired by #178; see [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/).

## #153: Distinguishing Delete-Marker Replication from Version Purge {#delete-marker}

### Why the External Report and Local Reproduction Differ {#reported-vs-observed}

The original issue described a sustained HTTP 405 storm involving ILM and replication, and proposed treating every delete-marker 405 probe as completion. Source inspection and local reproduction showed why that diagnosis was incomplete and why the proposed patch would break deletion guarantees.

Starting from baseline [`450dcb848`](https://github.com/pgsty/silo/commit/450dcb8484bc1337deba0cf608cc893a6691d794), the reproduction used two locally built SILO servers, separate data directories, and `mcli` / `minio-go` clients. A key finding was that **`mcli` uses bulk DELETE even for a single key, and the bulk-delete path was already classified properly.** Exercising the faulty entry point required issuing a direct single-object S3 DELETE.

| Observation | Single-object DELETE before the fix | After the fix |
| :-- | :-- | :-- |
| Matching delete-marker version at the target | Removed | Removed |
| Purge state for that version in source `xl.meta` | Still `PENDING`, although ordinary replication status was complete | Cleanup completed on the first replication attempt |
| Original data version | Retained | Retained |
| Scanner needed to finish this cleanup | Required later recovery | No scanner assistance needed |

Checking only that the remote version disappeared would miss the lingering `PENDING` state in source `xl.meta`. The reproduction confirmed the misclassified initial purge, the wrong completion state, and an unnecessary `HEAD` probe, without triggering a sustained 405 storm because the scanner/heal and resync paths already selected the purge branch.

### Why One Classification Condition Is Sufficient {#purge-classification}

When permanently deleting an existing delete marker, the object layer returns both `DeleteMarker=true` and a non-empty `VersionPurgeStatus`. The former describes the version being acted on; the latter describes the permanent purge now in progress.

The old single-delete handler checked only `DeleteMarker` and populated `DeleteMarkerVersionID`. Completion then updated ordinary `ReplicationStatus` instead of `VersionPurgeStatus`. The repaired condition in the [`DeleteObject` handler](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/object-handlers.go#L3173) is:

```go
if objInfo.DeleteMarker && objInfo.VersionPurgeStatus.Empty() {
    dmVersionID = objInfo.VersionID
} else {
    versionID = objInfo.VersionID
}
```

This matches the condition already used by bulk delete, scanner/heal, and resync. It requires no on-disk format change and no new recovery loop; existing `PENDING` entries continue to be cleaned up by the scanner/heal purge path.

### Why HTTP 405 Is Not Unconditional Success {#why-not-405}

A `405 Method Not Allowed` from a versioned `HEAD` indicates that a delete marker exists at the target. For **replicating a delete marker**, that proves idempotent completion. For **permanently purging that version**, it proves the marker is still present at the target.

Marking `VersionPurgeComplete` on a `HEAD` 405 would let the source erase its local tracking metadata while leaving the target version behind. Remote 403, 405, and 503 responses during a purge are genuine failures that must be retried.

Git blame traces the `DeleteMarker`-only check to an upstream [2020-11-19 commit](https://github.com/pgsty/silo/commit/9a34fd5c4a1e1e9f3de050f49c00edea8e32b4b5). A [2023-07-10 optimization](https://github.com/pgsty/silo/commit/e8c98c32464361dd7643b55e028d5735a48ebefc) changed scheduling from `dsc.ReplicateAny()` to the returned object's replication or `PENDING` purge state while keeping the `DeleteMarker`-only branch, and a [2025-04-02 commit](https://github.com/pgsty/silo/commit/01447d2438c46cb4658c1e5a13f21f56b7f05a92) renamed `Pending` to `replication.VersionPurgePending` at that site.

## #152: Exposing Drops from the Bounded MRF Queue {#mrf}

MRF (Most Recent Failures) buffers recent failed replication operations for background retry. It enforces two bounds: `mrfSaveCh` has capacity **100000**, and `mrfRetryLimit` is **3**. Entries are dropped from the queue when `RetryCount > mrfRetryLimit` or when `mrfSaveCh` is full. The source object and its pending replication state remain on disk, and dropped queue entries are picked up later by the background scanner.

The defect was that `TotalDroppedCount` and `TotalDroppedBytes` incremented internally but were omitted from both administration statistics snapshots and from Prometheus v2/v3 metrics. A deterministic capacity-one test fixture reproduces the gap: one entry is queued, a 20-byte overflow entry and a 30-byte retry-exhausted entry are dropped, and internal totals reach **2 / 50** while administration endpoints report **0 / 0**.

### The Selected Minimum Change {#mrf-fix}

1. Atomically populate the existing drop counters into both administration snapshots.
2. Export cumulative drop counters in Prometheus metrics v2 and v3.
3. Log deduplicated warnings at the two **actual drop sites** (retry exhaustion and a full MRF channel) using static messages and deduplication keys so changing counter values do not defeat log deduplication. Normal worker-queue overflow into MRF does not drop the entry and does not log a drop warning.
4. Route ordinary object replication, healing, and deletion consistently by `(bucket, objectName)` to preserve per-object worker affinity.

| Interface | New metric |
| :-- | :-- |
| Prometheus v2 | `minio_node_replication_mrf_dropped_operations_total` |
| Prometheus v2 | `minio_node_replication_mrf_dropped_bytes_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_operations_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_bytes_total` |

These counters accumulate since Server startup and reset on restart. **Operations count dropped queue entries**, so repeated failures on the same object increment the counter multiple times; bytes sum known object sizes, with delete entries contributing zero bytes. Operators should monitor the rate of increase alongside replication backlog and target health.

The queue capacity and retry limit remain unchanged, keeping memory bounded while relying on the background scanner for eventual recovery.

## #137: Making Cancellation Part of a Run's Lifecycle {#resync}

### Why One Shared Token Cannot Cancel a Multi-Bucket Group {#cancel-failure}

Previously, cancellation pushed a single unkeyed token into a shared channel. Because a site resync can span multiple buckets (up to 10 concurrent bucket runs) with dispatchers and workers competing to read from the same channel, a cancel request could stop only one bucket, be consumed by an unrelated run, or remain buffered and abort a later run.

Two blocking stages also ignored cancellation: reading from `Walk` output and sending to a full worker channel. If workers exited first, the dispatcher could block indefinitely on a full channel. In addition, `Walk` inherited the parent context directly, so an early return left its walker goroutine running.

State tracking had three accompanying bugs: site-level `updateState` mutated a value copy without writing it back to the map; bucket-level `Canceled` state handling was incomplete; and a late finalizer could overwrite `Canceled` with `Completed`.

### Registration, Cancellation, and Status Share a Write Boundary {#cancel-design}

Each `resyncBucket` run now creates an owned `context.WithCancelCause` and registers it **before** waiting for a concurrency slot. Registration and `cancelResyncID` share the resyncer's state lock:

- Registration verifies that the target still exists and the resync ID still matches, and checks whether the run has already been canceled.
- Cancellation marks matching `Pending` and `Started` entries `Canceled` before canceling every registered context for that resync ID.
- Runs waiting for a concurrency slot are canceled immediately, and any run registering after cancellation observes the `Canceled` state on entry.
- `Walk`, dispatch, workers, and result sends all select on the run's owned context. Unrelated resync IDs are unaffected, and no shared token remains buffered.

A dedicated operation mutex serializes site start/cancel configuration updates, and in-flight runs are still canceled even if part of the target-configuration loop fails. Bucket finalizers and progress updates verify both the target and the resync ID, discarding late results from removed, replaced, or canceled runs. Site state writes back to the map, and `Canceled` is never overwritten by a late `Completed`.

### Success and Failure Require Different Finalization Order {#finish-order}

Finalization preserves the #136 ordering contract — terminal state is persisted only after the result consumer drains the channel:

```text
Success: close worker inputs → join workers → drain results
         → persist terminal state → return slot → cancel owned context and unregister

Failure/cancellation: cancel context first to unblock work → join workers and consumer
                      → persist the appropriate terminal state → return slot → unregister
```

Canceling the context before joining workers on a normal completion path would abort in-flight work and turn a completing run into `Failed`. Calling `finish` from a single `defer` sequences cleanup deterministically without an extra `sync.Once`.

`WithCancelCause` separates explicit user cancellation (`Canceled`) from parent-context shutdown. A run interrupted by server shutdown is not marked `Completed`, and a run still waiting for a concurrency slot during shutdown keeps its `Pending` state so it can resume on restart.

### Protecting Terminal State and Resumed Work {#terminal-and-recovery}

Because a cancel request can arrive between the context check and the disk write, `markStatus` re-checks the in-memory state under lock and preserves `Canceled` even if the caller computed `Completed`, while rejecting writes from superseded resync IDs. If an individual bucket finished and persisted before a site-wide cancel arrived, its bucket record remains `Completed` while the site record is marked `Canceled`.

On the restart recovery path, `loadResync` previously spawned recovery goroutines and immediately ran `defer cancel()`. In SILO's shared-lock implementation, that `cancel()` terminates the merged leader context, aborting the newly launched recovery goroutines. A `WaitGroup` now keeps the leader context alive until all resumed runs exit, while still canceling them if leadership is lost. Loading on-disk state also avoids overwriting newer in-memory start or cancel state.

## Design Review and Complexity Decisions {#review}

| Proposal or review point | Final decision |
| :-- | :-- |
| Treat a purge's 405 probe as completion | Rejected: marker existence does not prove permanent deletion |
| Add bounded retries, backoff, and a persistent MRF scheduler | Not introduced: the existing queue and scanner already provide recovery; the demonstrated gap is visibility |
| Send more shared cancellation tokens | Rejected: this still cannot guarantee identity routing, broadcast, or isolation from later tasks |
| Add a separate cancellation tombstone registry | Unnecessary: existing target status and resync ID under one lock close the registration race |
| Give each run an owned context and cancelable blocking operations | Retained: full-queue deadlock and walker leaks have deterministic reproductions |
| Protect `finish` with `sync.Once` | Narrowed: a single deferred call site makes `sync.Once` unnecessary |
| Wait for resumed runs before releasing leader context | Retained: SILO's leader context cancel is active, so the `WaitGroup` is required and covered by leadership-loss tests |

Two additional details were kept simple: the infrequent resync start operation reads and writes configuration under the status lock (matching terminal saves), and the active registry keys on `resyncOpts` (including `resyncBefore`).

## Validation and Reproducible Evidence {#evidence}

Regression tests were written against the unmodified baseline and verified to fail before applying the fixes. The test suite exercises the production HTTP handlers, erasure storage, Prometheus metric registries, and `resyncBucket`.

| Validation area | Result and evidence |
| :-- | :-- |
| Single-delete purge | ErasureSD and Erasure source/target cleanup; legacy `PENDING` recovery; marker idempotency; real 403/405/503 failure semantics |
| MRF | Actual capacity-one overflow and retry exhaustion; administration JSON; registered v2/v3 counter types and values; object/delete worker affinity |
| Resync | `testing/synctest` coverage for blocked `Walk`, full worker queues, user and queued cancellation, unrelated IDs, later tasks, terminal races, stale IDs, slot release, and leader recovery |
| Complete local suite | `go test ./... -count=1 -timeout=30m` passed across all 50 tested packages |
| Concurrency and repetition | Focused replication race tests passed; cancellation regressions passed 100 repetitions |
| Tooling and contracts | Local build, vet, lint, generated-file checks, rebrand compatibility guard, and `git diff --check` passed |
| Two native servers | Built from local source; direct single-object DELETE removed the target marker and source `xl.meta` entry while retaining the original data version |
| Remote integration | All eight PR checks passed, followed by all six main Go CI jobs and VulnCheck |

Regression test files at the merged commit: [delete markers](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-delete-marker_test.go), [MRF visibility](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-mrf-observability_test.go), and [cancellation lifecycle](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-resync-cancel_test.go). Reproducible test commands:

```bash
go test ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test -race ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test ./cmd -run '^TestResyncCancel' -count=100
go test ./... -count=1 -timeout=30m
```

| Evidence point | Exact identity |
| :-- | :-- |
| Baseline | `450dcb8484bc1337deba0cf608cc893a6691d794` |
| Final PR head | `66fe61ff65c83d68b74baa637a11623015c7aa21` |
| Merged main | `d1105bbb3d4a0afa33b3a4ac11b821235038ed0e` |
| PR Go CI | [34320440012](https://github.com/pgsty/silo/actions/runs/34320440012) |
| Main Go CI | [34321319278](https://github.com/pgsty/silo/actions/runs/34321319278) |
| Main VulnCheck | [34321319274](https://github.com/pgsty/silo/actions/runs/34321319274) |

## Maintenance Principles {#follow-up}

Replication and resync regression tests must independently assert five invariants: accurate operation classification, observable queue drops, per-object replication outcomes derived from target responses, complete terminal counters prior to state persistence, and full goroutine and slot cleanup on cancellation.

## Second Round (2026-09-16): Worker-Side Purge Classification and Persisted MRF Recovery {#second-round}

Round 1 classified deletes at the **HTTP handler entry** (#153), exposed MRF queue drops (#152), and completed the resync cancellation lifecycle (#137). Round 2 — [PR #196](https://github.com/pgsty/silo/pull/196), commit [`0c61128d2`](https://github.com/pgsty/silo/commit/0c61128d2), integration verification `aea3882c9` — repairs the background replication pipeline: the **worker's own delete exits**, outer status aggregation, and the **persisted MRF recovery path** for delete markers.

### What Was Still Broken {#second-round-defects}

- **Legacy-shape tasks were skipped entirely.** A task with an empty `VersionID`, a non-empty `DeleteMarkerVersionID`, a `COMPLETED` creation target, and a `PENDING` purge target never issued its DELETE because the per-target creation early-return suppressed it.
- **Fixing only the per-target function caused outer aggregation to misreport.** Outer status selection keyed on `VersionID` and creation state, so a failed legacy-shape purge aggregated as `COMPLETED`, emitted `ObjectReplicationComplete`, and **skipped persisted MRF queueing**.
- **Persisted MRF dropped every delete-marker 405.** Replaying an on-disk MRF entry for a delete-marker version returned the marker metadata alongside `MethodNotAllowed`, and the error branch discarded the entry instead of recovering it.
- **Status clobbering and duplicate requests.** Failed purges overwrote successful resync markers, completed purges were re-sent, and an unready `HEAD` probe unconditionally overwrote creation state.
- **Multi-target empty-state regex misparses corrupted creation metadata.** Replaying a disk marker that carried only creation metadata against a task carrying purge state parsed two empty target states as `Pending`; the deleted-flag guard then rewrote the entire creation block as empty entries with fresh timestamps.

Three root causes drove these failures: the worker lacked **task-level** purge classification (the per-target predicate in community PR [#184](https://github.com/pgsty/silo/pull/184) prevented composite purge statuses from ever reaching `COMPLETE`, though Julien Laurenceau's investigation and proposed fix informed this round); MRF recovery lacked a **valid-405 identity gate**; and delete tasks carried no retry counter, making `mrfRetryLimit` unreachable on the delete path.

### The Repair {#second-round-fix}

- **Unified purge classification across all exits.** `isVersionPurge()` (true when `VersionID` is non-empty, or when `DeleteMarkerVersionID` is non-empty alongside a composite purge status) drives both the inner per-target function and outer aggregation. Purge exits write only `VersionPurgeStatus` and leave `ReplicationStatus` empty, which signals the storage layer not to modify creation status.
- **Three-field clear guard.** On the purge path, all three creation-status fields are explicitly cleared so the multi-target regex misparse cannot occur during disk writes.
- **Canonical permanent-delete requests.** Purges send an explicit `versionId` with `ReplicationDeleteMarker=false` and skip the pre-flight `HEAD` readiness probe, preventing a lost-response retry from **re-creating a delete marker** via an unversioned fallback.
- **Valid-405 gate for MRF recovery.** `MethodNotAllowed` schedules recovery only when the returned object is a delete marker, the bucket/object/version identity matches, and the modification time is non-zero.
- **Bounded retry budget.** Delete tasks carry a retry counter that increments across all three persisted-MRF entry points (aggregation failure, lock failure, and queue-full fallback) up to `mrfRetryLimit`; after exhaustion, the background scanner can still schedule healing.
- **Boundary-only status mapping.** `COMPLETE` is mapped to `COMPLETED` only at the statistics and event-notification boundary, reusing the existing legacy constant.

### What 405 Means, Precisely {#second-round-405}

For **creation** (replicating a delete marker), a `HEAD` 405 on the target marker version means the marker *already exists at the target* — idempotent completion. For **purge** (permanently deleting a version), a 405 during local MRF identity probing with a matching marker identity means *the marker still exists and needs purging*; purge completion is decided solely by the remote DELETE response, where 403, 405, and 503 are always real failures. Empty or `null` version markers return `ObjectNotFound` rather than 405 and never enter the 405 gate.

### Boundaries That Remain {#second-round-limits}

The legacy in-memory task shape does not serialize across restarts and has no active producer; handling it provides defensive coverage. Targets without a configured client still log only, and target-level resync replacing a purge subset remains unchanged. For the tag-ordering and replica-metadata fixes in the same series, see [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/) and [Replica Metadata Normalization](/blog/design/replica-metadata-normalization/).

## Third Round (2026-09-16): Exact-Version Purges, Marker Healing, and Stale Creations {#third-round}

Round 2 made the worker's purge exits truthful. Round 3 — commits [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3), [`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0), and [`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb), shipped in [Server 20260916](/blog/release/silo-20260916/) (`40220bd836cbd066ca424fa4dc5dbb90057fb55a`, alongside `silo-pkg` `6f27ee6`) — repairs how an exact-version purge updates drives and how queued marker creations behave after a purge completes. It was prompted by three-site container runs (three sites, four processes and sixteen drives per site, EC 12+4) in which a purged delete marker reappeared on both target sites while the source site still returned the data version.

### What Was Still Broken {#third-round-defects}

- **A purge could write the delete marker it was removing.** Lookup marked a version under purge as deleted for visibility, and the purge write-back treated that flag as an instruction to write a delete marker to disk. Drives that lacked the marker had it written to them, causing a partially purged erasure set to flip-flop on retry rather than converge.
- **Missing versions were acknowledged without write quorum.** Because the read path reported a version absent once half of the drives said so, a retried purge returned 204 while up to half of the drives still held the delete marker.
- **Healing a delete marker stripped its replication metadata.** The heal path reconstructed delete markers with an empty metadata map. Healed markers lost their replication and purge state, appeared pending again, and could be re-replicated as fresh marker creations.
- **Queued marker creations executed after the purge finished.** Every GET, HEAD, or LIST on a pending delete marker, along with the scanner and MRF, queued a creation task carrying a snapshot of the marker; tasks from multiple frontends serialized on the per-object replication lock. In the reproduced timeline, both targets acknowledged the user's purge, and ~85 ms later a queued creation carrying the same `VersionID` and original modification time arrived at both targets. Because nothing in the wire request distinguished an initial creation from a stale replay, both targets recreated 16/16 marker copies while the source held 0/16.

### The Repair {#third-round-fix}

- **Classify purge intent once (`isVersionPurge`).** A request is a version purge when it carries a valid explicit `VersionID`, sets no marker-creation, prefix, data-movement, free-version, expiry, or transition options, and either carries a completed purge status, has no replication state, or is a trusted replica request. A purge never sets marker-creation flags, and its vote tally combines drives that physically removed the version with drives that confirmed it absent. The response reports a delete marker only when a stored marker was actually removed; a data version with an earlier pending purge is reported as a data version.
- **Require a write-quorum majority (`N/2+1`) to confirm absence.** When lookup reports a version missing on a retried purge, the server re-reads every drive. Fewer than `N/2+1` absent replies fail with insufficient write quorum, and any erasure set that still holds a copy is scheduled for MRF healing. Offline, corrupt, or unreadable drives never count as absent. The multi-pool layer applies the same check to pools skipped by lookup, and replica receivers resolve purges by version across pools.
- **Preserve stored metadata when healing markers.** Healing copies the delete marker's persisted metadata map and strips only transient healing, data-movement, and tiering keys. Typed state generation is restricted to fresh creation writes that have no stored metadata, and never fabricates timestamps.
- **Revalidate marker creations under the replication lock before sending.** Before transmitting a marker creation, the delete replication worker re-reads the source version under the per-object replication lock. If the version is missing, is no longer a delete marker, or is undergoing a purge, the task is stale and is dropped without modifying the source; inconclusive reads are retried via MRF rather than treated as absence.

### Evidence and Boundaries {#third-round-limits}

Two three-site batched-recovery runs (with and without a source restart, returning one target site in two halves) converged within ~15 s and remained consistent for the rest of a 450 s test window. The stale-creation regression fails on unmodified `main` and passes with the fix on both single-drive and 16-drive erasure fixtures.

Source-side revalidation under the lock cannot recall a creation request already in flight on the network or replayed by another site; closing that cross-site window requires a receiver-side persistent purge record or sequence number, tracked in [#217](https://github.com/pgsty/silo/issues/217). If all server processes crash simultaneously right after a majority-acknowledged purge, minority copies on drives that were offline during the purge can persist for up to seven scanner cycles, during which all frontends continue to serve the data version.
