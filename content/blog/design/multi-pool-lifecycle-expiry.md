---
title: "Multi-Pool Lifecycle Expiry: Decide on the Whole Object"
linkTitle: "Multi-Pool Lifecycle Expiry"
date: 2026-11-04
lastmod: 2026-11-04
author: "PGSTY SILO Maintainers"
summary: >
  Why lifecycle rules evaluated on the versions of one pool hide, delete, or resurrect versions stored in another pool, and why a recheck on the merged version list under the object lock is the minimum complete repair.
tags: [Design, Lifecycle, Storage Pools, Data Safety]
weight: 10
draft: false
url: "/blog/design/multi-pool-lifecycle-expiry/"
---

This record covers [issue #278](https://github.com/pgsty/silo/issues/278) and [PR #279](https://github.com/pgsty/silo/pull/279) by Denis Babchuk, evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). The fix will ship through a maintainer integration PR that keeps the contributor commits unchanged and adds the maintainer follow-ups described below. The restored-copy expiry fix ([#281](https://github.com/pgsty/silo/issues/281)) travels in the same integration PR and has its own record.

**Status:** the first version of the fix passed two maintainer review rounds. An adversarial review then requested changes: parts 6 to 9 under [Proposed fix](#fix). The patch that implements them was approved after four review rounds. Tested together with the other fixes for the next release on one integration branch: the full test suite, the CI race selections and an adversarial review of how the fixes interact all pass. Remote CI and multi-pool acceptance are still pending. Not merged, not released.

## Short answer {#tldr}

The report is real, and it is the most serious open defect for the next release. On a deployment with more than one pool, the versions of one key are often spread across pools. Lifecycle decides on the versions that one pool holds, but the expiry it starts deletes or hides the key in every pool. A version that is the latest in its own pool, but not the latest of the object, is treated as current. A delete marker that is alone in its pool is treated as a marker without older versions. The result is silent data loss: current versions hidden under a new delete marker, newer versions deleted with all versions, and deleted objects becoming readable again. Decommission and rebalance make the same decision and still report Complete.

The repair keeps every existing lifecycle decision point and adds one check where all of them converge. Before an ILM expiry deletes anything in a multi-pool deployment, the pools layer evaluates the rule again under the object lock, with the versions of the key in all pools merged into one list. An expiry that does not hold for the whole object is refused. So is one whose version history or lock protection cannot be established with authority. Decommission and rebalance move such a version instead of leaving it to the expiry. Single-pool deployments skip the merged read. All-versions expiry has a separate, older defect on every deployment, covered in its own record.

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | Data-correctness defect in lifecycle evaluation; inherited design, not a regression in a published SILO release. |
| Affected deployments | More than one pool, a versioned or versioning-suspended bucket, and an `Expiration`, `ExpiredObjectAllVersions`, `ExpiredObjectDeleteMarker`, or `DelMarkerExpiration` rule. |
| Not affected | Single-pool deployments; keys whose versions all live in one pool; restored-copy expiry (tracked in #281). |
| Severity | Critical. Versions are deleted or hidden without an error. The only traces are the ILM audit entry and the bucket notification. |
| Reachability | Ordinary S3 writes. In the reporter's reproduction, SILO's own placement put the versions of a third to a half of the keys into both pools. |
| Release urgency | Blocks the next release. Main already carries [#276](https://github.com/pgsty/silo/pull/276), which runs the migration expiry immediately during the decommission or rebalance walk. |
| Remaining effort | About 4 to 5 maintainer days: implement and review parts 6 to 9, then full CI and multi-pool acceptance runs. Parts 1 to 5 exist. |

## When it happens {#trigger}

A key gets versions in two pools in normal operation:

- a new version of an existing key is written to the pool with the most free space, not to the pool that already holds the key;
- two first writes of the same key race and land in different pools;
- a decommission or rebalance is interrupted after copying some versions.

The lifecycle rule then has to depend on the other versions of the key. The reporter's matrix on main shows each failure shape:

| Rule | Layout before the scan (newest first) | Result on main |
| --- | --- | --- |
| `Expiration` `Days=1` | p1 `[v1]`, p2 `[v2]` | A new delete marker hides the current `v2`. |
| `Expiration` with `ExpiredObjectAllVersions` | p1 `[v1]`, p2 `[v2]` | `v1` is taken as current and the whole key, including `v2`, is deleted. |
| `ExpiredObjectDeleteMarker` | p1 `[dm]`, p2 `[v1]` | The marker is removed and the deleted object reads as `v1` again. |
| `DelMarkerExpiration` | marker in one pool, newer version in the other | The marker expiry deletes the newer version with it (covered by Go tests; plain S3 writes do not produce this layout). |

Keys whose versions all live in one pool behave correctly in the same runs.

## Root cause {#root-cause}

Lifecycle evaluation needs three facts about each version: whether it is the latest (`IsLatest`), how many versions the object has (`NumVersions`), and when its successor was written (`SuccessorModTime`). Every producer of an expiry computes them from the versions it can see:

- the scanner and drive heal read the `xl.meta` of one erasure set;
- GET and HEAD of a `versionId` read the pool that holds that version;
- decommission and rebalance walk one pool.

The consumer is different. `applyExpiryOnNonTransitionedObjects` and `expireTransitionedObject` delete through the pools layer. A whole-object action deletes the prefix in every pool, and a new delete marker hides the key in every pool. For a single version or a new delete marker, the set-level recheck under the lock does not help, because it evaluates the versions of the set that takes the delete. When that set made the wrong decision, the recheck confirms it. For an all-versions expiry there is no recheck at all: the pools layer forwards it to `deletePrefix` with fresh options, so the set never sees `Expiration.Expire`. That path, and the way it also deletes keys nested under the expired key, is covered in a separate design record, published with its fix.

In short, the decision is local and the action is global.

## Where the behavior came from {#history}

### Provenance {#provenance}

**Upstream origin; not introduced by SILO.** The defect has two upstream ingredients: lifecycle decisions that are made on the versions one set can see but executed on the whole key, and a placement change that made keys with versions in several pools common. Every one of the 18 SILO releases, from `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z`, contains both. The SILO changes on this path either do not touch the decision or are not released; the ones that matter are listed below.

**Ingredient 1: a local decision with a global action.** Each producer evaluates the versions it reads, and each of these commits is in upstream and in every SILO release.

| Producer | Commit | PR | Date | First upstream release |
| --- | --- | --- | --- | --- |
| Scanner evaluates lifecycle per object (`scannerItem.applyActions`) | [43d6e3a](https://github.com/pgsty/silo/commit/43d6e3ae0) (Klaus Post) | [#9579](https://github.com/minio/minio/pull/9579) | 2020-06-12 | `RELEASE.2020-06-14T18-32-17Z` |
| Scanner uses the full evaluator on one set's version list | [01447d2](https://github.com/pgsty/silo/commit/01447d243) | [#21096](https://github.com/minio/minio/pull/21096) | 2025-04-02 | `RELEASE.2025-04-03T14-56-28Z` |
| GET and HEAD expire the version they read | [65aa2bc](https://github.com/pgsty/silo/commit/65aa2bc61) (Anis Elleuch) | [#11296](https://github.com/minio/minio/pull/11296) | 2021-02-01 | `RELEASE.2021-02-01T22-56-52Z` |
| Decommission skips and expires ILM-expired versions | [236ef03](https://github.com/pgsty/silo/commit/236ef03db) (Harshavardhana) | [#15300](https://github.com/minio/minio/pull/15300) | 2022-07-14 | `RELEASE.2022-07-15T03-44-22Z` |
| Rebalance, same filter | [4523da6](https://github.com/pgsty/silo/commit/4523da654) (Krishnan Parthasarathi) | [#15483](https://github.com/minio/minio/pull/15483) | 2022-10-25 | `RELEASE.2022-10-29T06-21-33Z` |
| Drive heal skips expired versions | [109a9e3](https://github.com/pgsty/silo/commit/109a9e3f3) (Harshavardhana) | [#18569](https://github.com/minio/minio/pull/18569) | 2023-12-01 | `RELEASE.2023-12-02T10-51-33Z` |

The consumers are the actions. The set-level recheck under the lock, `opts.Expiration.Expire` in `erasureObjects.DeleteObject`, comes from [35f2552](https://github.com/pgsty/silo/commit/35f2552fc) ([#13091](https://github.com/minio/minio/pull/13091), Harshavardhana, 2021-08-27, `RELEASE.2021-08-31T05-46-54Z`). It reads the versions of the one set that takes the delete. The all-versions action arrived in [aae6846](https://github.com/pgsty/silo/commit/aae684641) ([#17521](https://github.com/minio/minio/pull/17521), 2023-06-28, `RELEASE.2023-06-29T05-12-28Z`). Its own recheck, [289223b](https://github.com/pgsty/silo/commit/289223b6d) ([#19359](https://github.com/minio/minio/pull/19359), 2024-03-27, `RELEASE.2024-03-30T09-41-56Z`), is never reached through the pools layer: `erasureServerPools.DeleteObject` handles `DeletePrefix` by calling `deletePrefix`, which forwards only `DeletePrefix` to each pool and drops the expiry options (this comes from [7722b91](https://github.com/pgsty/silo/commit/7722b91e1), [#12504](https://github.com/minio/minio/pull/12504), 2021-06-15). On main, an all-versions expiry for which no rule applies returned no error and deleted the key, while the same request addressed to a single version was refused with `Version not found`. The code is the same in upstream master.

**Ingredient 2: placement that makes split keys common.** [83b2ad4](https://github.com/pgsty/silo/commit/83b2ad418) (jiuker, [minio/minio#21115](https://github.com/minio/minio/pull/21115), 2025-07-19) added `|| pinfo.Err == nil` to the condition in `getPoolIdx`, now `getWritePoolIdx`. Before it, only a key that did not exist yet was placed by free space, and a new version of an existing key stayed in the pool that held the key. After it, a key that exists is placed by free space as well, so the new version can land in another pool. The first upstream release with it is `RELEASE.2025-07-23T15-54-02Z`; `RELEASE.2025-07-18T21-56-31Z` does not have it. All 18 SILO releases do, and upstream master still does. The commit title concerns the free-space threshold of a single pool, and the effect on existing keys looks like a side effect, not a design decision. Free space chooses the pool by weighted random draw, not by "the pool with the most free space".

**What SILO changed on this path.**

| SILO change | Date | Released | Effect on the defect |
| --- | --- | --- | --- |
| [e59a3d9](https://github.com/pgsty/silo/commit/e59a3d938) serialize and reconcile multi-pool object updates | 2026-09-11 | from `RELEASE.2026-09-16T00-00-00Z` | Narrowed one trigger: a PUT now looks up and writes the key under one pools-layer lock, so two first writes can no longer both see the key as absent. Placement and lifecycle evaluation are unchanged, so split keys still arise. |
| [f54c048](https://github.com/pgsty/silo/commit/f54c04846) added, and [2a04d5f](https://github.com/pgsty/silo/commit/2a04d5f48) removed again, a write-recovery flag in `getWritePoolIdx` | 2026-10-25 | both in `RELEASE.2026-10-25T00-00-00Z` | None. The placement condition in the released code is the upstream one. |
| [7a060ca](https://github.com/pgsty/silo/commit/7a060cab1) relocate hot objects across pools, and its revert [9b76a21](https://github.com/pgsty/silo/commit/9b76a2167) | 2026-08-15, 2026-09-15 | only together, in `RELEASE.2026-09-16T00-00-00Z` | None. The feature never shipped without its removal. |
| [60c7179](https://github.com/pgsty/silo/commit/60c7179dd), [1748f62](https://github.com/pgsty/silo/commit/1748f62c7) and other migration safety fixes | 2026-10-18 | from `RELEASE.2026-10-18T00-00-00Z` | None. The `filterLifecycle` closures of decommission, rebalance, and heal in `RELEASE.2026-10-26T00-00-00Z` are identical to upstream master, and so is the scanner's evaluation. |
| [#266](https://github.com/pgsty/silo/pull/266) move ILM-expired current versions during decommission and rebalance ([19910230](https://github.com/pgsty/silo/commit/19910230a), [a995921](https://github.com/pgsty/silo/commit/a995921e5)) | 2026-10-29 | main only, after `RELEASE.2026-10-26T00-00-00Z` | Narrowed. On a versioned bucket the expiry of a current version only adds a delete marker, so the walk now moves the version instead of skipping it. |
| [#276](https://github.com/pgsty/silo/pull/276) ILM cleanup during migration ([0a546c7](https://github.com/pgsty/silo/commit/0a546c7a7)) | 2026-11-02 | main only | Widened, in timing. It judges the same pool-local copy as before, but runs the expiry, all-versions actions included, inside the walk before the source is retired. In the releases the walk skips the version and queues the same decision for the expiry workers. |
| [a803027](https://github.com/pgsty/silo/commit/a803027b0) count `DelMarkerExpiration` as an active rule | 2026-11-03 | main only | Widened exposure. The scanner skipped buckets whose only rule is `DelMarkerExpiration`; on main it evaluates them, which reaches the fourth failure shape above. |

So the defect that the released SILO builds contain is the upstream one, unchanged. #266 and #276 are not in any release tag. #276 does not create a new wrong decision. It makes an existing one execute immediately, which is why this fix gates the next release.

The first draft of the maintainer fix for this issue had two defects of its own, a legal-hold bypass through a stale minority metadata revision and a lost pending purge for duplicate copies. Review found them before release, and neither was ever merged or released.

Dates, PR numbers, and release membership come from the git history. The statement that the all-versions recheck is skipped was reproduced with a test on main; the other statements about code flow come from reading the code.

## Options {#options}

### Option 1: disable lifecycle, or skip expiry, when a key spans pools

This is safe but wrong in the other direction. Valid rules would stop applying for an unbounded time, and operators would have no signal that their retention policy no longer runs.

### Option 2: keep every version of a key in one pool

Pool affinity reduces how many new split keys are created. It cannot repair existing split keys, interrupted migrations, or concurrent first writes. SILO already evaluated an overwrite-affinity change and did not adopt it because of small-object overwrite regressions ([Overwrite Pool Affinity](/blog/design/overwrite-pool-affinity/)). Affinity is a possible future mitigation, not a correctness fix.

### Option 3: make every producer evaluate the merged versions

Every scanner visit, heal, read, and migration step would read the key from every pool. The cost would apply to the common case of an object with nothing to expire, and every producer would still race with writes between its decision and the delete.

### Option 4: recheck at the consumer, under the object lock

This is the chosen option and the approach of PR #279. Producers keep their cheap local decision. Only a delete that is about to happen pays for a merged read, and that read happens under the same object write lock as the delete, so the version list cannot change between the check and the action.

### Rejected additions

A global version index, a cross-request cache, or a new lifecycle state machine would add persistent state and new failure modes. None of them is needed to close the defect.

## Proposed fix {#fix}

The fix has nine parts:

- **Parts 1 and 2** are PR #279 as submitted.
- **Parts 3 to 5** came from the first two maintainer review rounds.
- **Parts 6 to 9** came from the adversarial review of that version. It reproduced two defects the earlier parts introduced and two older paths they left open. The design of parts 6 to 9 is agreed and the implementation is in progress.

1. **Merged evaluation at the consumer (PR #279, commit 1).** `lifecycleEventsAllPools` reads the versions of the key from its erasure set in every pool and ignores tier free versions. It merges them newest first, counting a version that has copies in two pools once. It then evaluates the rule with the full lifecycle evaluator, computing `IsLatest`, `NumVersions`, and `SuccessorModTime` for the whole object. `expiryApplies` maps the result to the delete that was requested:
   - an all-versions delete needs the latest version to carry a delete-all action;
   - a new delete marker needs the latest version to expire;
   - a specific version needs that version to carry its own delete action.

   The check has four outcomes:
   - approval;
   - `errLifecycleNotApplicable`, when the versions exist but the rule does not hold;
   - `ObjectNotFound` or `VersionNotFound`, when the target is absent;
   - `InsufficientWriteQuorum`, when the history cannot be read with authority (part 6).

   Other errors propagate. The scanner retries a refusal on a later pass. Unlike a not-found result, a refusal never acknowledges a pending replication purge, and a migration that is refused while the source version is still present does not retire it.

   `erasureServerPools.DeleteObject` runs the check under the object lock for ILM deletes on more than one pool, then marks the request as `CheckedAllPools`. `DeleteObjects` runs the same check once per key for each batch of ILM version purges.
2. **Migration moves what the rule does not cover (PR #279, commit 2).** Decommission and rebalance keep their per-pool expiry only when `migrationExpiryApplies` confirms it against all pools. Otherwise the version is moved like any other, and the scanner applies the rule later in the pool that then holds the key. Without this part, the walk's expiry would be refused and the decommission would stop with the version still in the pool it is retiring.
3. **All-pools approval in batched tiered noncurrent purges.** The new set-level `Expire` flag caused tiered `NewerNoncurrentVersions` batch purges to be rejected inside the set, and the batch adapter reported that rejection as success. `deleteObjectsReconciled` now forwards `CheckedAllPools` only for ILM entries with an explicit version ID, which are exactly the entries the pools layer has already checked.
4. **Read-triggered expiry checks the version that was read.** GET and HEAD return `NoSuchKey` and queue an expiry when the local evaluation says the version is due. For local delete candidates in a multi-pool deployment, the read path now repeats the evaluation on the merged list and matches the event by the identity of the version that was actually read.
   - A newer version elsewhere expiring does not justify hiding an older version that is still valid.
   - If the recheck fails or does not confirm the expiry, the read succeeds and nothing is queued.
   - Local "no action" results do not trigger any extra read.
5. **No removal notification for a refused expiry.** A batch entry refused with `errLifecycleNotApplicable` no longer emits an `s3:ObjectRemoved:Delete` notification or an ILM expiry audit entry. Part 9 extends this to every other uncommitted result.
6. **An authoritative version history, or no decision.**
   - **Acceptance rule.** A revision of a version is identified by its header plus a sha256 digest of its normalized metadata.
     - The digest uses an unambiguous encoding: each map is a separate section that records its entry count and holds length-prefixed entries in sorted key order.
     - Fields that differ between drives by design are excluded: the erasure index and the per-shard checksums of legacy objects.
     - The 4-byte header signature alone is not enough, because two different lock states can share it.

     `objectVersions` accepts a revision only when at least `max(n/2 + 1, the version's metadata read quorum)` drives of the set hold that revision, where `n` is the configured drive count of the set. Before the history is merged, each drive's non-accepted revisions are filtered out, so one stale drive cannot displace the majority.
   - **Refusal.** It refuses with `InsufficientWriteQuorum` when either:
     - a live version seen on any drive has no accepted revision;
     - half or more of the set's drives cannot be read.
   - **Scope.** These checks run before every early return. Cancellation is checked between versions and fails closed.
   - **What it closes.** Before this, one drive that missed a legal-hold update could supply the revision the merge used. And with half the drives unreadable, a fresh version below quorum dropped out of the history, so an all-versions expiry deleted it.
7. **Lock protection that the merge cannot lose.**
   - **Across pools.** Lock fields are read with the same key precedence as the lifecycle evaluator: the lowercase key first, then the canonical-case key. When copies of a version in different pools disagree on legal hold or on retention, the newer revision wins only if both carry valid, nonzero revision timestamps and one is strictly newer. Otherwise the object is refused.

     Copies with different modification times are separate writes, for example two `null` writes in a versioning-suspended bucket. The newest write decides. If an older write is still protected, the object is refused.
   - **In the set.** For a single-version ILM delete, the set re-reads the target under the lock and refuses in two cases:
     - a replication purge is pending;
     - the version is still protected (retention, legal hold, or an unavailable clock) after it replaces only those lock fields that the approved state proves superseded with a strictly newer, valid timestamp.

     Bulk deletes rely on part 6 and on the cross-pool rule.
8. **Duplicate copies with different replication state are refused.** For copies of one version in two pools, the composite replication status, the composite purge status, and the per-target maps are compared after parsing. Any semantic difference refuses the object. Before this, a pending purge on one copy disappeared from the merged view, and the version could expire before its purge had replicated.
9. **Only completed or already-absent removals are announced.** In the batch path, the `ObjectRemoved` notification and the ILM expiry audit are sent only when the entry was deleted or was confirmed already absent. Refusals, quorum failures, and configuration errors produce neither. Replication retry handling is unchanged.

When copies of one version in two pools are merged, their independently ordered retention, legal hold, and tag revisions are kept, under the strict ordering of part 7.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient, for the paths it covers.** In a multi-pool deployment, every ILM action on a single version or a delete marker reaches storage through `erasureServerPools.DeleteObject` or `erasureServerPools.DeleteObjects`. That covers the scanner, drive heal, read-triggered expiry, the expiry workers, and the migration walks. The merged check sits at that point:

- it runs under the object write lock that serializes writes to the key;
- it uses the scanner's evaluator;
- with parts 6 to 8, it refuses whenever the version history or the version's protection cannot be established.

On these paths, a wrong local decision is refused rather than executed. Migration consults the same check before it decides not to move a version.

**Not covered here: separate release blockers.**

- **All-versions expiry.** It does not get the same protection. On every deployment it goes through a recursive prefix delete that skips the set recheck and also deletes keys nested under the expired key. On a single pool it has no recheck at all.
- **Tiered latest version.** A delete-all of a tiered latest version writes a delete marker instead of purging the key.

Both are handled in a separate design record, published with its fix. Approving this fix does not approve the release on its own.

**Necessary.** Each part closes a path that otherwise stays open:

- Eligibility depends on versions in other pools. The decision therefore needs a complete cross-pool view, serialized with the delete. The pools-layer consumer under the object lock is where that view and the lock meet.
- Without the migration part, a decommission stops with refused versions still in the pool it is retiring.
- Without forwarding the all-pools approval in batches, tiered noncurrent purges are reported as done although the source kept the version.
- Without the read-path change, GET and HEAD still answer `NoSuchKey` for a valid version.
- Without part 6:
  - one stale drive can lift a legal hold;
  - an incomplete history can authorize deleting a committed version.
- Without part 7:
  - an equal-timestamp conflict between pools can drop a hold on the bulk path;
  - a pending purge can be ignored.
- Without part 8, a pending purge on a duplicate copy is ignored.
- Without parts 5 and 9, refused expiries are announced as deletions.

**Deliberately excluded.**

- Single-pool deployments skip the merged read. One thing does change for them: an ILM refusal now returns `errLifecycleNotApplicable` instead of a not-found error. Scanner callers treat both the same, and migration never treats a refusal as absence.
- Restored-copy expiry depends on the restore date, not on other versions, and is handled in [#281](https://github.com/pgsty/silo/issues/281).
- Unversioned single-copy deletes keep the set's own recheck, because each copy there is an independent write.

## Cost and compatibility {#cost}

- **Interfaces.** No new public schema, route, configuration, storage format, or dependency. `ExpirationOptions` gains in-memory fields only. The visible behavior changes are three:
  - expiries are refused;
  - GET and HEAD return a version where they used to answer `NoSuchKey`;
  - single pool returns the refusal error described above.
- **I/O and CPU.** In a multi-pool deployment, each ILM delete reads the key's full version history from every drive of one erasure set per pool, under the lock it already holds. It then decodes and hashes every version on every drive. The walks do this for each version they would expire. Batches do it once per key per call. Cancellation is cooperative, checked between versions and before and after the merge. The merge itself cannot be cancelled, so there is no wall-time bound. There is deliberately no cap on version count: a cap would stall cleanup of exactly the long-history keys lifecycle must clean.
- **Merge cost.** It grows faster than linearly with history length. With the merge used before this fix, 1,000 versions took about 2.4 ms and 8,000 about 230 ms, in memory, on 16 drive streams. These numbers measure the pre-fix merge, not the final implementation.
- **Which expiries run.** An expiry that does not hold for the whole object, or whose history cannot be established, no longer runs. One case now expires where it did not before: a rule with an object-size filter, on a key whose current version lives in a different pool from the first pool that holds the key.
- **Rollback.** Rollback restores the old behavior. No migration is needed in either direction.

## Residual limits {#limits}

- **Existing damage is not repaired.** Delete markers that the old behavior added stay. They are ordinary markers and can be removed with `DELETE ?versionId=` after checking the ILM audit log or bucket notifications. Versions that were already deleted cannot be recovered by this fix.
- **A refusal can last indefinitely.** The following refuse expiry until heal repairs the metadata, and repeated scans do not repair them:
  - the strict history rules;
  - stale protected copies;
  - leftover records;
  - disagreements in replication state.

  A degraded set, with half or more of its drives unreadable, also stops expiry for its keys.
- **Lifecycle convergence is not guaranteed.** A version can be noncurrent for the object but the latest in its own pool. The per-pool scanner may never propose it, so some due versions can remain until the versions are in one pool, for example after a decommission or rebalance.
- **Reads do not hide every due version.** GET or HEAD of an older version can return it while the latest version's all-versions rule is due.
- **Placement is unchanged.** New versions of existing keys still go to a pool chosen by free space, so split keys keep appearing. Whether SILO should prefer the key's pool is a separate placement and performance question.

## Verification {#verification}

**Parts 1 to 5, on the integration head.**

- `TestPoolsLifecycleSplitObject` and `TestPoolsMigrationLifecycleWholeObject`, from PR #279, cover the scanner, decommission, and rebalance. The HEAD case in the first test simulates evaluation and queueing; the real handlers are covered by the read tests below.
- `TestPoolsLifecycleTieredNoncurrentBatch`, `TestPoolsLifecycleTieredBatchReplication`, `TestPoolsLifecycleTieredBatchIdentity`, and `TestPoolsLifecycleBatchRejectionNotAnnounced` cover the batch path and its replication and notification side effects.
- `TestPoolsLifecycleDuplicateLockMetadata`, `TestPoolsLifecycleDuplicateTagMetadata`, and `TestPoolsLifecycleBatchRejectionReplication` cover merged copies and refused purges.
- `TestPoolsLifecycleReadHTTP`, `TestPoolsLifecycleReadAuthorizationAndClose`, `TestPoolsLifecycleReadBoundaries`, and `TestPoolsLifecycleReadProxy` exercise the real GET and HEAD handlers, including authorization order and reader cleanup.
- The earlier maintainer rounds recorded the full `./cmd` suite, the targeted race selection, and a mutation run in which the tests caught 37 of 38 mutations. The adversarial round did not re-run these.

**The adversarial review.** It used executable probes on the integration head, and the maintainers re-ran all of them with the same results.

- **Seven of the nine probes failed:**
  - a stale minority lock revision let a held version be deleted;
  - an incomplete history authorized an all-versions delete of a fresh version;
  - an all-versions delete removed a nested key;
  - a tiered all-versions expiry left the versions under a marker;
  - a pending purge on a duplicate copy was dropped;
  - a quorum refusal was announced as a removal;
  - the single-pool refusal error changed.
- **Two were measurements:** read coverage and merge cost.
- **Regressions.** Parts 6 to 9 turn the relevant probes into regressions. They also add these cases:
  - 8/8 conflicting revisions;
  - a reduced-parity partial version;
  - the unreadable-drive boundary;
  - leftover free versions;
  - cross-pool equal-timestamp protection on the single and bulk paths;
  - pending purges with delete-marker metadata;
  - equivalent per-target maps in different orders;
  - mixed batch side effects.
- **Controls.** A benign degraded set and a strictly newer cross-pool release must still expire.

**Patch review.** The approved patch adds 26 tests. They fail on the previous head and pass with the patch, with the race detector clean. The lifecycle, migration, restore and expiry selection passes, 88 tests with no failures. The reviewer's own probes, 11 in total, pass on the final patch.

**Still to run before merge.**

- remote CI on the final head;
- the reporter's `repro.sh` (scan and decommission);
- `docs/distributed/decom.sh`.

Multi-node lock domains and long-running scanner and migration behavior have not been exercised.

**Integration.** The fix is the base of one integration branch for the next release. #281 and the lock-domain, delete-all, heal dry-run, #259, #285 and Console fixes are stacked on it, and every pick applied without conflicts. On that head the full `go test ./cmd/... ./internal/...` suite passes, as do the CI race-detector selections and a race selection that covers every new test. An adversarial review of the combination found no defects. It checked lock domains, cleanup paths and purge against restore with executed probes.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Maintainer rounds 1 and 2 | Found the gap in forwarding the all-pools approval in batches, the read-path hiding of valid versions, and refused expiries announced as removals; fixed as parts 3 to 5. |
| Adversarial review | Requested changes. Two findings were introduced by parts 1 to 5: the stale-revision legal-hold bypass, and the lost pending purge on duplicate copies. Fixed as parts 6 to 8. Four findings were older: the incomplete-history delete-all, nested keys deleted by delete-all, tiered delete-all stalling, and the announcement of other refusals. Fixed as part 6 for multi-pool and part 9, or moved to the delete-all record. The single-pool error change is documented above. |
| Design rounds 2 and 3 | Agreed with changes. A revision needs a strict majority and the version's own read quorum. Supersession needs strictly newer, valid timestamps. A pending purge is an unconditional veto. Conflicting cross-pool protection is refused before approval. |
| Patch review, rounds 4 to 7 | Round 4 found that the 4-byte header signature cannot identify a revision. Round 5 found three more problems: lock keys read only in lowercase (pre-existing), a digest without map boundaries, and legacy per-shard checksums that never agree across drives. Round 6 found that nested legacy maps were hashed in an unsorted order. All were fixed with regressions. Round 7 approved the patch with no remaining findings in scope. |

## References {#references}


- Issue: [#278](https://github.com/pgsty/silo/issues/278)
- Contributor PR: [#279](https://github.com/pgsty/silo/pull/279)
- Related restored-copy expiry: [#281](https://github.com/pgsty/silo/issues/281), [#282](https://github.com/pgsty/silo/pull/282)
- Migration expiry change: [#276](https://github.com/pgsty/silo/pull/276) and [ILM Expiry and Pool Migration Ordering](/blog/design/ilm-migration-ordering/)
- Upstream placement change: [minio/minio#21115](https://github.com/minio/minio/pull/21115)
- Placement alternative not adopted: [Overwrite Pool Affinity](/blog/design/overwrite-pool-affinity/)
