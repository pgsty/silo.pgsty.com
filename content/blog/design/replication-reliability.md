---
title: "Replication Reliability: Delete Completion, MRF Visibility, and Resync Cancellation"
linkTitle: "Replication Reliability"
date: 2026-09-09
lastmod: 2026-09-09
author: "Ruohang Feng"
summary: >
  The decision record for SILO #153, #152, and #137: distinguish external reports from local evidence, classify delete-marker purges correctly, expose drops from the bounded MRF queue, and give resync cancellation a complete lifecycle. Includes Fable 5.1 Max review, rejected alternatives, and final validation.
tags: [Design, Replication, S3, Review]
weight: 7
draft: false
url: "/blog/design/replication-reliability/"
---

This page records the analysis, design choices, review, and implementation of [#153](https://github.com/pgsty/silo/issues/153), [#152](https://github.com/pgsty/silo/issues/152), and [#137](https://github.com/pgsty/silo/issues/137). They belong to the same replication reliability series, but affect operation classification, recovery visibility, and task lifecycle respectively. One general retry patch cannot repair all three.

> **As of 2026-09-09:** [PR #162](https://github.com/pgsty/silo/pull/162) is merged as [`d1105bbb`](https://github.com/pgsty/silo/commit/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e), and all three issues are closed. All eight checks on the tested PR head, followed by main Go CI and VulnCheck, passed.<br>
> **Review:** the plan was discussed with the installed Claude Code Fable 5.1 Max, followed by a review of the implementation. The final verdict was **GO**.<br>
> **Delivery boundary:** this work completed code, tests, and main integration. It did not create a Server tag or formal release, and does not establish that existing packages, images, or production deployments contain the fixes.

## Overall decision and the surrounding series {#decision}

The selection rule was to repair a reproduced invariant at the smallest boundary that owns it, retain existing recovery mechanisms, and use deterministic tests to prove that work can finish. Additional complexity needs a concrete counterexample.

| Issue | Confirmed defect in current SILO | Selected repair |
| :-- | :-- | :-- |
| #153: delete-marker purge | Single-object DELETE classified a permanent deletion as marker replication; the remote marker disappeared while source purge remained PENDING | Classify by purge status, matching bulk delete, scanner/heal, and resync |
| #152: invisible MRF drops | The queue was already bounded, but internal drop counters did not reach administration or monitoring; object and delete worker arguments were reversed | Expose existing counters, warn at actual drop sites with deduplication, and align worker routing |
| #137: unreliable resync cancellation | One shared token could not stop multiple runs; blocking phases missed cancellation; stale runs could overwrite terminal state | Give each run an owned context, cancel by resync ID, and constrain registration, finalization, and state updates |

The surrounding series had already separated three concepts that are easy to confuse:

- [#136](https://github.com/pgsty/silo/issues/136) / [PR #138](https://github.com/pgsty/silo/pull/138) repaired **counter completeness**: receive and apply the final result before persisting terminal state, without waiting for the one-minute periodic flush.
- [#139](https://github.com/pgsty/silo/issues/139) repaired **outcome accuracy**: an existing destination object does not prove that this update succeeded. Success and failure must come from the target's actual replication result.
- #137 repairs **cancellation and resource lifecycle**: the task must stop, its walker, workers, and result consumer must exit, and an old run must not pollute a new run's state. This change preserves the first two contracts rather than introducing another accounting mechanism.

Authorization to use internal replication semantics belongs to the earlier [CORS and replication trust record](/blog/design/cors-replication-trust/). Authoritative Object Lock state across pools remains tracked separately in [#133](https://github.com/pgsty/silo/issues/133), still open at this record's date. Closing these three issues does not mean every replication concern is resolved.

The release-gating target is the maintained `pgsty/silo` stack with Console, mcli, and silo-pkg. Compatibility with upstream MinIO/MC remains best effort. Neither a mechanism proposed for upstream nor an external experiment can automatically be treated as an observation on current SILO.

## #153: distinguish marker replication from permanent version deletion {#delete-marker}

### The report and the reproduction differ {#reported-vs-observed}

The original issue described a sustained HTTP 405 storm involving ILM and replication, and proposed treating every delete-marker 405 probe as completion. Current SILO source and measurements do not justify adopting that explanation and patch directly.

The baseline was [`450dcb848`](https://github.com/pgsty/silo/commit/450dcb8484bc1337deba0cf608cc893a6691d794). The experiment used two locally built SILO servers, separate disposable data directories, and maintained mcli / minio-go clients. A critical observation was that **mcli uses bulk DELETE even for a single key; that route was already correct.** A direct single-object S3 DELETE was therefore necessary to exercise the faulty entry point.

| Observation | Single-object DELETE before the fix | After the fix |
| :-- | :-- | :-- |
| Matching delete-marker version at the target | Removed | Removed |
| Purge state for that version in source `xl.meta` | Still PENDING, although ordinary replication status was complete | Cleanup completed on the first replication attempt |
| Original data version | Retained | Retained |
| Scanner needed to finish this cleanup | Required later recovery | No scanner assistance needed in this experiment |

Checking only that the remote version disappeared would falsely declare success. Source metadata must be inspected too. The reproduction establishes incorrect initial purge classification and completion state, plus an unnecessary probe. **It did not reproduce the external report's sustained 405 storm or request-volume figures.** Existing scanner/heal and resync producers already select the proper purge path; they cannot be described as necessarily repeating that erroneous probe every cycle.

### Why one classification condition is sufficient {#purge-classification}

When deleting an existing marker, the object layer can return both `DeleteMarker=true` and a nonempty `VersionPurgeStatus`. The former describes the version being operated on; the latter describes the operation now required. They are compatible facts.

The old single-delete handler checked only `DeleteMarker` and populated `DeleteMarkerVersionID`. Completion then updated ordinary `ReplicationStatus` instead of completing the purge. The final condition is:

```go
if objInfo.DeleteMarker && objInfo.VersionPurgeStatus.Empty() {
    dmVersionID = objInfo.VersionID
} else {
    versionID = objInfo.VersionID
}
```

This matches the classification already used by other producers. The fix belongs in the [DeleteObject handler](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/object-handlers.go#L3173). It requires no storage-format change, relaxation of replica deletion protection, or new recovery task. Legacy PENDING entries remain recoverable through the existing scanner/heal purge path.

### Why a 405 is not unconditional success {#why-not-405}

A 405 from a versioned HEAD can establish that the marker exists at the target. For **replicating a delete marker**, that can mean idempotent completion. For **permanently deleting that version**, it means there is still work to do.

Writing `VersionPurgeComplete` merely because HEAD returned 405 could let the source remove its metadata while leaving the unwanted target version behind. The implementation retains existing 405 semantics. Real remote failures such as 403, 405, and 503 must not be disguised as successful permanent deletion.

Source history traces marker-based classification to an upstream [2020-11-19 commit](https://github.com/pgsty/silo/commit/9a34fd5c4a1e1e9f3de050f49c00edea8e32b4b5). The [2023-07-10 optimization](https://github.com/pgsty/silo/commit/e8c98c32464361dd7643b55e028d5735a48ebefc) changed scheduling from `dsc.ReplicateAny()` to the returned object's replication/PENDING purge state while retaining classification based only on `DeleteMarker`. At this location, the [2025-04-02 commit](https://github.com/pgsty/silo/commit/01447d2438c46cb4658c1e5a13f21f56b7f05a92) merely moved `Pending` to `replication.VersionPurgePending`; it did not first introduce that scheduling condition. This identifies lineage, not a bisect across every historical release, and does not establish when the entire externally reported storm was introduced.

## #152: expose drops from an already bounded queue {#mrf}

MRF, or Most Recent Failures, records recent failed replication work for background processing. It already had limits: `mrfSaveCh` has capacity **100000**, and `mrfRetryLimit` is **3**. The code drops a queue entry when `RetryCount > mrfRetryLimit` or the save channel is full.

The source object and its pending replication state remain. Dropping a queue entry does not mean losing source data. However, subsequent repair depends on the scanner; a prompt retry can turn into a wait for a scan, so this mechanism does not establish a fixed recovery deadline.

The actual defect was that `TotalDroppedCount` / `TotalDroppedBytes` increased internally but were omitted from both public statistics snapshots and from Prometheus v2/v3. A deterministic capacity-one fixture demonstrates the failure: one entry is admitted, a 20-byte overflow entry and a 30-byte retry-exhausted entry are dropped, and internal totals become **2 / 50** while administration reports **0 / 0**.

### The selected minimum change {#mrf-fix}

1. Atomically read the existing counters into both administration snapshots.
2. Register and load cumulative counters in metrics v2 and v3, and document their meaning.
3. Warn at the two **actual drop sites**: retry exhaustion and a full MRF channel. Fixed messages and deduplication keys prevent changing counter values from defeating deduplication. Handing ordinary worker overflow to MRF is not itself a drop, so it does not gain a warning here.
4. Route ordinary objects, healing, and deletion consistently by `(bucket, objectName)` to restore worker affinity for the same object.

| Interface | New metric |
| :-- | :-- |
| Prometheus v2 | `minio_node_replication_mrf_dropped_operations_total` |
| Prometheus v2 | `minio_node_replication_mrf_dropped_bytes_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_operations_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_bytes_total` |

These counters accumulate since Server startup and reset on restart. **Operations count entries, not unique objects**; one object can contribute repeatedly. Bytes cover known sizes, with deletion entries contributing zero bytes. They measure neither data loss nor the complete backlog. Operators should examine increases alongside replication backlog and target health.

This work does not enlarge the queue, increase retry limits, add a persistent retry scheduler, or introduce another backoff framework. Existing limits continue to bound memory use, and the scanner remains the eventual repair mechanism. The repair makes an invisible condition observable; it does not promise a recovery deadline under arbitrary failures.

## #137: make cancellation part of a run's lifecycle {#resync}

### One token cannot cancel a group {#cancel-failure}

Previously, cancellation placed one unkeyed token into a shared channel. One site resync can cover several buckets, with up to 10 concurrent bucket runs, while dispatchers and workers compete to consume the token. Only one bucket might stop; an unrelated task might consume it; or a leftover token might affect a later task.

Two blocking phases had independent defects: a bare receive from Walk output did not observe cancellation, and sending to a full worker channel did not observe it either. Once a worker exited, the dispatcher could block forever on a channel with no receiver. Walk also inherited the parent context, so an early function return could not stop its own walker.

State handling had related faults: site `updateState` modified a local value without writing it back to the map; bucket Canceled handling was incomplete; and an old finalizer could overwrite canceled state with Completed.

### Registration, cancellation, and status share a write boundary {#cancel-design}

Each `resyncBucket` creates an owned `context.WithCancelCause` and registers **before** waiting for a concurrency slot. Registration and `cancelResyncID` share the resyncer's state lock:

- Registration validates that the target still exists and the resync ID still matches, and reads its current cancellation state.
- Cancellation marks matching Pending / Started states Canceled before canceling all matching registered contexts.
- A registered run still waiting for a slot receives cancellation; a run registered after cancellation sees the canceled state.
- Walk, dispatch, workers, and result sends observe that run's context. Unrelated IDs are unaffected, and there is no buffered token for a later task to consume.

A dedicated operation mutex serializes site start/cancel configuration setup. Canceling running work still executes if part of the target-configuration loop fails. Bucket finalizers and counter updates check the current target and resync ID, ignoring late results from removed, replaced, or canceled runs. Site state is actually written back, and a late Completed result cannot overwrite Canceled.

### Success and failure require different finalization order {#finish-order}

The result-consumer contract from #136 must remain intact: persist terminal state only after the consumer finishes.

```text
Success: close worker inputs → join workers → drain results
         → persist terminal state → return slot → cancel owned context and unregister

Failure/cancellation: cancel context first to unblock work → join workers and consumer
                      → persist the appropriate terminal state → return slot → unregister
```

Canceling before joining workers on a normal completion path could discard pending work and turn a successful run into Failed. The final code calls `finish` exactly once from one defer, using defer order to complete cleanup. It therefore needs no additional `sync.Once`.

`WithCancelCause` distinguishes an explicit user cancellation from parent-context interruption. User cancellation becomes Canceled; parent interruption observed during finalization must not leave an interrupted run marked Completed. Shutdown while a run is still waiting for a slot preserves the existing Pending state for restart recovery.

### Protect terminal state and resumed work {#terminal-and-recovery}

Cancellation can still arrive between the context check and the terminal save. Under its lock, `markStatus` must persist an existing Canceled state even if the finalizer previously computed Completed. An old resync ID must also be unable to overwrite a new run.

This is not a transaction across metadata files. If a bucket completed and persisted before cancellation, a subsequent site cancellation can leave different records reading “bucket Completed, site Canceled.” Completion happened first. The guarantee is that **late completion cannot turn an already canceled run back into Completed**, not that cancellation erases work completed before it.

The recovery loader, `loadResync`, previously launched goroutines and then immediately executed `defer cancel()`. Inspection of SILO's actual shared-lock implementation confirmed that this cancel ends the merged leader context; it is not a no-op. A WaitGroup now retains that context until resumed runs exit. Losing leadership still cancels the existing context; replacing it with a global context would bypass the leadership constraint. Loading disk state must also preserve newer in-memory start/cancel state.

## Fable review and the complexity decisions {#review}

The review used the installed Claude Code with model argument `claude-fable-5-1[1m]` and `--effort max`. Baseline reproductions and the minimal proposal produced agreement on all three repairs. The final patch and validation were then reviewed again, yielding GO. The conclusion rests on code and evidence, not model agreement alone.

| Proposal or review point | Final decision |
| :-- | :-- |
| Treat a purge's 405 probe as completion | Rejected: marker existence does not prove permanent deletion |
| Add bounded retries, backoff, and a persistent MRF scheduler | Not introduced: the existing queue and scanner already provide recovery; the demonstrated gap is visibility |
| Send more shared cancellation tokens | Rejected: this still cannot guarantee identity routing, broadcast, or isolation from later tasks |
| Add a separate cancellation tombstone registry | Unnecessary: existing target status and resync ID under one lock close the registration race |
| Give each run an owned context and cancelable blocking operations | Retained: full-queue deadlock and walker leaks have deterministic reproductions |
| Protect `finish` with `sync.Once` | Initial review required protection against double close; the final implementation has one deferred call site, and re-review accepted omitting Once |
| Wait for resumed runs before releasing leader context | Initial review required checking necessity; SILO's cancel is effective, so the WaitGroup stays, with leadership-loss coverage |

The final review accepted two further implementation boundaries. The infrequent resync start operation holds the status lock across configuration reads and writes, consistent with existing terminal saves. The active registry uses `resyncOpts`, including `resyncBefore`, as its key; current callers reuse the same in-memory values, and no identity mismatch was reproduced. Future changes that reconstruct time values or restore task identity should revisit equivalence, rather than adding another registry without evidence now.

## Validation and reproducible evidence {#evidence}

Regressions were added against unchanged production code first, and failed before the fixes. New tests exercise the production handler, real erasure storage, actual metric registration, and `resyncBucket`, rather than only testing helper logic that repeats the implementation.

| Validation area | Result and evidence |
| :-- | :-- |
| Single-delete purge | ErasureSD and Erasure source/target cleanup; legacy PENDING recovery; marker idempotency; real 403/405/503 failure semantics |
| MRF | Actual capacity-one overflow and retry exhaustion; administration JSON; registered v2/v3 counter types and values; object/delete worker affinity |
| Resync | `testing/synctest` coverage for blocked Walk, full worker queues, user and queued cancellation, unrelated IDs, later tasks, terminal races, stale IDs, slot release, and leader recovery |
| Complete local suite | `go test ./... -count=1 -timeout=30m` passed, with 50 tested packages |
| Concurrency and repetition | Focused replication race tests passed; cancellation regressions passed 100 repetitions |
| Tooling and contracts | Local build, vet, lint, generated-file checks, rebrand compatibility guard, and `git diff --check` passed; dependencies and compatibility baseline unchanged |
| Two native servers | Built from local source; direct single-object DELETE removed the target marker and source `xl.meta` entry while retaining the original data version; no downloaded Server Docker image |
| Remote integration | All eight PR checks passed, followed by all six main Go CI jobs and VulnCheck |

Tests pinned to the merged revision: [delete markers](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-delete-marker_test.go), [MRF visibility](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-mrf-observability_test.go), and [cancellation lifecycle](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-resync-cancel_test.go). With that revision and Go 1.27.1, the relevant checks can be repeated with:

```bash
go test ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test -race ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test ./cmd -run '^TestResyncCancel' -count=100
go test ./... -count=1 -timeout=30m
```

After complete local validation, only new-test formatting and fixtures changed: an existing ARN was reused, and the collector supplied the metric prefix, preventing the compatibility scanner from treating test strings as new protocol identifiers. The guard was not weakened. Relevant tests, lint, and compatibility checks were rerun after those adjustments, and remote CI checked the final commit.

| Evidence point | Exact identity |
| :-- | :-- |
| Baseline | `450dcb8484bc1337deba0cf608cc893a6691d794` |
| Final PR head | `66fe61ff65c83d68b74baa637a11623015c7aa21` |
| Merged main | `d1105bbb3d4a0afa33b3a4ac11b821235038ed0e`, with the same source tree as the final PR head |
| PR Go CI | [34320440012](https://github.com/pgsty/silo/actions/runs/34320440012) |
| Main Go CI | [34321319278](https://github.com/pgsty/silo/actions/runs/34321319278) |
| Main VulnCheck | [34321319274](https://github.com/pgsty/silo/actions/runs/34321319274) |

## Maintenance and release decisions {#follow-up}

Future changes must continue to establish operation identity, visible failure, truthful per-object outcomes, complete terminal counters, and cancellation that releases its own resources. Neither an API returning Completed nor an object existing at the destination can replace those checks.

The code verdict is GO, and the delivery facts are main integration and passing CI. A formal release still requires selecting a tag, verifying packages and images, and establishing that deployments contain the repair. The scanner-dependent MRF recovery delay, the open cross-pool issue, and the externally reported 405 storm not reproduced on current SILO remain part of this decision record.
