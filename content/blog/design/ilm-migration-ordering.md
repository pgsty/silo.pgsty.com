---
title: "ILM Expiry and Pool Migration Ordering"
linkTitle: "ILM Migration Ordering"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO Maintainers"
summary: >
  Why lifecycle expiry and pool migration disagree about a versioned current object, what #266 fixes, and how #276 completes the replication, tier, and lifecycle safety boundaries.
tags: [Design, Lifecycle, Storage Pools, Replication]
weight: 13
draft: false
url: "/blog/design/ilm-migration-ordering/"
---

This record covers [issue #265](https://github.com/pgsty/silo/issues/265), the contributor change [PR #266](https://github.com/pgsty/silo/pull/266), and maintainer follow-up [#276](https://github.com/pgsty/silo/pull/276). The merged [#264](https://github.com/pgsty/silo/pull/264) and [#267](https://github.com/pgsty/silo/pull/267) are relevant predecessors. The review was updated against main after #276 on 2026-11-02. #266's decommission commit is [19910230a](https://github.com/pgsty/silo/commit/19910230a), and its rebalance commit is [a995921e5](https://github.com/pgsty/silo/commit/a995921e5).

## Short answer {#tldr}

The report is real. In a versioned bucket, an Expiration due on the current version creates a delete marker and leaves the data version as noncurrent. Decommission and rebalance treated every lifecycle DeleteAction as if the version itself had already been removed. They skipped copying it.

That creates two outcomes:

- decommission can report Complete and then lose the version when the old pool is removed, or fail depending on whether the expiry worker wins a race;
- rebalance can copy some versions but leave their source copies behind forever.

PR #266 makes the migration code distinguish these actions. We merged it to preserve the contributor's correct local fix. Maintainer follow-up [#276](https://github.com/pgsty/silo/pull/276) then routed ILM-selected deletion through the existing expiry contracts and added the missing safety fences. Together they are complete for decommission and ordinary hot-tier lifecycle migration. Rebalance still deliberately skips transitioned versions; that is a separate scope boundary.

Before #276, the local algorithm was correct for moving ordinary hot-tier versions, but four safety boundaries remained:

- a direct source purge can bypass bucket replication;
- a transitioned version can lose the only record that would lead to remote-tier cleanup;
- the code needs an explicit rule for a lifecycle configuration change between the walk and cleanup;
- a whole-object expiry can leave the current version in the source pool after decommission reports Complete.

These were separate from the original local migration bug. #276 closes them with small boundary changes and regression tests; no pool-migration redesign was needed.

## Timeline and origin {#history}

The first decommission skip for lifecycle-expired objects came from upstream [236ef03db](https://github.com/pgsty/silo/commit/236ef03db), dated 2022-07-14. Pool-level rebalance was introduced in [4523da654](https://github.com/pgsty/silo/commit/4523da654), dated 2022-10-25, with the same broad lifecycle idea. Upstream later changed skip accounting in [3637aad36](https://github.com/pgsty/silo/commit/3637aad36), dated 2023-05-11, and followed with rebalance matching in [9af6c6cee](https://github.com/pgsty/silo/commit/9af6c6cee), dated 2023-06-21.

SILO's migration cleanup was substantially tightened in [1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7), dated 2026-10-18. It stopped using a broad prefix cleanup and removed only versions that had passed source and destination checks. That made concurrent deletion safer, but it also meant that a version skipped by ILM could no longer be removed merely because a prefix was being deleted.

The issue is therefore an interaction between old lifecycle skip semantics and newer per-version safety checks. Neither part is wrong on its own; together they disagree about the state of a version.

## What triggers it {#trigger}

The main trigger is a rule becoming due between scanner passes, or a rule being added or changed shortly before migration:

1. A versioned bucket contains v1, v2, and current v3.
2. An Expiration rule is due for v3.
3. The migration walker evaluates the rule before the expiry worker has applied it.
4. The evaluator returns DeleteAction.

For a versioned bucket, DeleteAction means “create a delete marker above the current version.” It does not mean “remove v3 now.” The same migration also sees true version-only actions such as NoncurrentVersionExpiration, which do remove a particular version. These two actions cannot share the same migration behavior.

The race is worse when expiry is delayed. A current version can be skipped with no destination copy. If the source pool is removed, that version is gone. A version under COMPLIANCE retention is exposed too because the delete marker is allowed while the retained data version is still supposed to survive. A transitioned current version is another special case for decommission.

## Root cause in simple terms {#root-cause}

The old code used a boolean filter:

~~~text
if lifecycle action deletes something:
    queue expiry
    skip the version
~~~

That boolean erased the difference between:

- DeleteAction on a versioned object: add a marker, keep the current data version;
- DeleteVersionAction: remove one noncurrent version;
- DeleteAllVersionsAction: remove the whole object history;
- delete-restored actions: remove a restored copy while tier metadata has different rules.

The decommission worker then counted skipped versions as complete, while its final check ignored them. Rebalance did not count them, so its “all versions moved” condition never became true and source copies stayed.

The newer removeMovedVersions routine adds another necessary rule: it only removes a source version when a destination copy still preserves the read result. That is correct for moved versions but cannot be applied unchanged to a version that ILM will delete without a destination copy. If the skipped version remains after newer versions move away, it may become the latest version in the source pool and the queued expiry can re-evaluate to no action.

The direct purge added for that case has its own boundary. It calls the source pool's DeleteObject with a version ID and SkipFreeVersion. That is a storage cleanup operation; it is not the normal S3 delete path. It does not automatically run the replication decision, create VersionPurgePending state, or remove a remote tier object.

## How the maintainer follow-up closes the boundaries {#boundaries}

The original #266 direct source purge was a local storage cleanup operation. On its own, it did not automatically run the replication decision, create `VersionPurgePending` state, or remove a remote tier object. #276 keeps the action distinction from #266 but makes migration respect the contracts already owned by ordinary ILM expiry.

### Replication remains a second obligation

When a delete-replication rule applies, removing an expired source version is not complete until the target receives the version purge. #276 sends ILM-selected version deletes through the normal expiry path before source cleanup, so the replication state and queued purge exist before the source copy is retired. The regression test uses two pools, delays expiry, and verifies convergence on the target.

This is the smallest safe boundary because it reuses the existing replication path. It avoids duplicating replication decisions inside `removeMovedVersions`, while adding only the migration hand-off needed to prevent a delayed expiry task from finding `VersionNotFound` after the source has already disappeared.

### Tiered versions retain a cleanup obligation

A transitioned version needs remote-tier cleanup as well as hot-tier metadata cleanup. If remote deletion fails, the hot-tier metadata must retain a durable free-version record so a later scanner can retry. #276 performs the hot-tier transition and preserves that retry record when remote deletion cannot complete. The decommission path also checks the remaining ordinary and free versions before reporting completion.

This keeps the #264 two-view model intact: free versions remain internal cleanup records, while ordinary lifecycle and migration views exclude them. Rebalance still skips transitioned versions in #266; extending rebalance to move them is a separate scope decision.

### Lifecycle configuration changes fail closed

The migration walk records the lifecycle configuration update time. Cleanup compares that value before applying an irreversible source-side decision. If the configuration changed, migration stops and leaves the source data for a retry under the new rules.

Failing closed is the smallest safe semantic choice. It avoids silently applying a stale deletion decision and costs one extra migration attempt when an operator changes lifecycle policy during the walk.

### Whole-object expiry has an observable completion fence

`DeleteAllVersionsAction` and `DelMarkerDeleteAllVersionsAction` must remove the whole history before the old pool can be retired. #276 applies whole-object expiry before source cleanup and verifies that ordinary and free versions are gone before decommission reports completion. This prevents a current version from remaining only in the old pool while older versions have already moved.

The fence is deliberately expressed as an existing source-state check rather than a new asynchronous transaction. It preserves the current expiry worker and retry model while making `Complete` mean that the source pool no longer owns the object.

## Impact {#impact}

The operator can see:

- a decommission that reports Complete, followed by a missing current version after the old pool is removed;
- a decommission that fails with PreConditionFailed and needs a second run;
- a rebalance that reports progress but leaves duplicates in the source pool;
- versions under object lock or in a tier being lost from the source migration path;
- a replicated target retaining a version after the source purge;
- remote tier data orphaned after a transitioned version is directly purged;
- a lifecycle rule change being ignored by an already admitted source cleanup;
- duplicate copies that a later scanner pass does not remove.

This is a real migration correctness problem even when GET works before migration. The loss happens at the boundary where the old pool is retired.

## Options {#options}

### Block migration whenever lifecycle is due

This is safe but impractical. It turns a normal scanner delay into a migration outage, and it still needs a correct rescan after the rule changes.

### Run lifecycle synchronously before migration

This reduces the race but does not define what to do when the expiry queue, tier, or destination is unavailable. It also adds latency and still needs the migration walker to interpret the resulting metadata correctly.

### Skip every ILM action and delete the whole source prefix

This matches the old broad cleanup style but can remove a versioned current object before its delete marker is created in the destination. It also bypasses the per-version concurrency protections that SILO intentionally added.

### Distinguish action semantics and clean only what is safe

This is the minimum necessary design:

- move a current version when Expiration only creates a marker;
- skip a version that ILM truly deletes, but let source cleanup remove it without requiring a destination copy;
- keep whole-object deletion cases until the expiry action has removed the history everywhere;
- count rebalance skips as handled so moved source copies can be retired.

PR #266 implements this design.

### Move versions when deletion has external side effects

Replication and tier cleanup make a direct source purge more than a local metadata operation. Moving the version first and letting the ordinary ILM worker perform the deletion preserves the existing replication and tier contracts. It may keep one extra copy for a short time, but it avoids duplicating those contracts inside migration cleanup.

## PR assessment {#pr}

PR #266 is the correct contributor fix for the original local bug:

1. it stops treating a versioned current Expiration marker as if the data version had already been deleted;
2. it distinguishes version-only deletion from whole-object deletion;
3. it lets decommission and rebalance account for the versions that ILM will actually remove;
4. it preserves the per-version source and destination checks introduced by the newer migration cleanup.

We merged #266 to recognize that contribution. The maintainer follow-up [#276](https://github.com/pgsty/silo/pull/276) then added the necessary integration boundaries:

- replication state and queued purges are created before source cleanup;
- transitioned versions retain a retryable tier-cleanup record when remote deletion fails;
- lifecycle configuration changes invalidate a stale walk;
- whole-object actions are completed and verified before decommission reports success;
- decommission and rebalance use separate lifecycle audit sources;
- regression tests cover delayed expiry, replication, tier cleanup, configuration changes, whole-object expiry, and resumable decommission.

The combined result is sufficient and necessary for the reported decommission problem. It is also the smallest reasonable change: action semantics stay in the migration worker, replication and tier cleanup stay in their existing paths, and completion uses durable metadata checks already present in the system. A broader rewrite or a new metadata format would add complexity without closing a new correctness gap.

The cost is limited to a small amount of additional metadata work and, in some cases, one extra migration attempt or a short period with an extra copy. Those costs are preferable to silently losing a version, leaving a replicated target stale, or orphaning a remote tier object.

The implementation deliberately leaves rebalance support for transitioned versions outside this fix. That boundary should be handled as a separate change with its own tier-ownership tests rather than expanding #276 after the fact.

## Merge order and conflict {#merge}

The final order was intentional: #264 established the real-version view, #266 preserved the contributor's action distinction, and #276 added the maintainer-owned replication, tier, lifecycle-generation, and completion checks on top of both. The original #266 commits remain in the merged history.

The combined tests cover a free version above a lifecycle-expiring version, a transitioned version selected for deletion, replication-enabled version purge, lifecycle configuration changes, whole-object expiry, and a decommission retry after replication completes.

## Residual limits {#limits}

Rebalance still skips transitioned versions by design. This fix also does not heal an unavailable disk, reconstruct data already lost by an earlier completed decommission, or remove an old orphaned tier object whose free-version record was already discarded. Those are separate operational or scope decisions. Lifecycle configuration changes during migration now fail closed, so the operation must be retried under the new configuration.

## Verification references {#verification}

- Issue: [#265](https://github.com/pgsty/silo/issues/265)
- PR: [#266](https://github.com/pgsty/silo/pull/266)
- Current main used for review: [0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b)
- Free-version fix merged in [#264](https://github.com/pgsty/silo/pull/264)
- Mixed-EC migration fix merged in [#267](https://github.com/pgsty/silo/pull/267)
- Decommission fix commit: [19910230a](https://github.com/pgsty/silo/commit/19910230a)
- Rebalance fix commit: [a995921e5](https://github.com/pgsty/silo/commit/a995921e5)
- Related ILM replication proposal: [#240](https://github.com/pgsty/silo/pull/240)
- Original decommission skip: [236ef03db](https://github.com/pgsty/silo/commit/236ef03db)
- Pool rebalance introduction: [4523da654](https://github.com/pgsty/silo/commit/4523da654)
- SILO per-version cleanup change: [1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7)
