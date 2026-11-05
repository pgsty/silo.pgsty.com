---
title: "Restored Copies: Expire the Copy, Not the Object"
linkTitle: "Restored-Copy Expiry"
date: 2026-11-04
lastmod: 2026-11-05
author: "PGSTY SILO Maintainers"
summary: >
  Why the expiry of a restored copy of a current version hid the object or stripped an older null version, why addressing the exact version is the core repair, and which storage and native-restore safeguards have to ship with it.
tags: [Design, Lifecycle, Tiering, Data Safety]
weight: 10
draft: false
url: "/blog/design/restored-copy-expiry/"
---

This record covers [issue #281](https://github.com/pgsty/silo/issues/281) and [PR #282](https://github.com/pgsty/silo/pull/282) by Denis Babchuk, evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). The fix ships in the same maintainer integration PR as the multi-pool lifecycle fix ([Multi-Pool Lifecycle Expiry](/blog/design/multi-pool-lifecycle-expiry/), [#278](https://github.com/pgsty/silo/issues/278)). That PR keeps the contributor commit unchanged and adds the safeguards described below. It also depends on the [single-pool lock-domain fix](/blog/design/single-pool-lock-domains/), which must merge with it or before it.

**Status:** fix approved by review and committed locally. Tested together with the other fixes for the next release on one integration branch: the full test suite, the CI race selections and an adversarial review of how the fixes interact all pass. Not merged or released.

## Short answer {#tldr}

The report is real. After `POST ?restore`, a transitioned version gets a temporary local copy until the expiry date in `x-amz-restore`. When that date passes, lifecycle must remove the copy and nothing else: the version stays transitioned and is read from the tier again.

For a noncurrent version this already worked. For the current version, the cleanup was sent as a delete of the object, because the version ID was not passed:

- a versioned bucket got a new delete marker on top of the object, so GET and HEAD returned `NoSuchKey`;
- a versioning-suspended bucket had the delete applied to the `null` version underneath, which removed that version's data;
- without a `null` version, the delete failed silently and the restored copy stayed on the drives forever.

A plain GET or HEAD after the expiry date was enough to trigger it.

The core repair is the one PR #282 proposes: the cleanup always addresses the exact version the restored copy belongs to. Review then found that cleanup and restore had other ways to touch the wrong version, so the fix ships with four more groups of changes:

- a versioning-state correction;
- a storage-level guard that lets only completed tiered versions give up a restore cache;
- a set of native-restore repairs, so that restore itself cannot create, overwrite, or deadlock on the version it rehydrates;
- an ownership protocol for native restore, from the adversarial review. Each restore attempt owns the version it rehydrates. Its upload is private, so no other caller can reach it. Every restore decision uses the metadata that a quorum of drives agrees on.

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | Data-correctness defect in restored-copy expiry; inherited from upstream (the same code is in MinIO `RELEASE.2025-07-23T15-54-02Z` and master), not a regression in a published SILO release. |
| Affected | A restored current version in a versioned bucket (including a `null` current version written before versioning was enabled); a restored current version with a version ID in a versioning-suspended bucket. |
| Not affected | A restored noncurrent version; a restored `null` current version with versioning suspended; unversioned buckets. |
| Severity | Critical. The object is hidden under a delete marker. If the bucket also has a `NoncurrentVersionExpiration` rule, that rule later deletes the hidden version for good, tier object included. In suspended buckets, the data of an older `null` version is removed directly. |
| Reachability | Any restore of a tiered object, once its restore expires: the scanner, GET, HEAD, listings, decommission, or drive heal. |
| Release urgency | Blocks the next release. The core fix is small. The native-restore safeguards are larger, and they are implemented and reviewed. |
| Remaining effort | About 1 to 2 maintainer days, shared with the #278 integration. That covers integration with the lock-domain fix, full CI, and a restore run against a real remote tier. |

## When it happens {#trigger}

The restore sets its expiry date to UTC midnight at least `Days` (minimum one day) ahead, so the defect shows up a day or more after a restore. The reporter's test moves the date into the past and runs each lifecycle path, on one pool and on two:

| Layout | Result on main |
| --- | --- |
| Versioned bucket, restored current version | A delete marker hides the object; the restored copy stays until a later pass treats the version as noncurrent. |
| Versioned bucket, restored `null` current version | The same delete marker. |
| Suspended bucket, restored current version with a `null` version under it | The delete goes to the `null` version and removes its data; the restored copy and its expired `x-amz-restore` stay. |
| Suspended bucket, restored current version without a `null` version | `DeleteObject` fails with `VersionNotFound`, which is dropped without a log line; the copy stays and every pass retries. |

On main, 32 of the 56 cases in the contributor's test fail, for every path and both pool counts.

## Root cause {#root-cause}

`Lifecycle.Eval` returns `DeleteRestoredAction` for an expired restore of the latest version and `DeleteRestoredVersionAction` for any other version. `expireTransitionedObject` sets the version ID only for actions that `DeleteVersioned()` accepts, and that set contains `DeleteRestoredVersionAction` but not `DeleteRestoredAction`.

For the current version, `DeleteObject` therefore received no version ID and treated the request as a delete of the object. The `ExpireRestored` flag that should limit the delete to the restored copy had no version to act on:

- with versioning enabled, the ordinary path wrote a new delete marker;
- with versioning suspended, the request addressed the `null` version, which `xlMetaV2.DeleteVersion` found and whose data directory it returned for removal.

## Where the behavior came from {#history}

### Provenance {#provenance}

**Upstream origin, as a regression; not introduced by SILO.** The defect was introduced by [ee158e1](https://github.com/pgsty/silo/commit/ee158e161) ([minio/minio#19093](https://github.com/minio/minio/pull/19093), Krishnan Parthasarathi, 2024-02-22), first released as `RELEASE.2024-02-24T17-11-14Z`. The restored-copy branch did not always lack the version ID. SILO inherited the code at the fork, and every one of the 18 SILO releases, from `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z`, contains it. No SILO commit changed the branch.

| Step | Commit | PR | Date | First upstream release |
| --- | --- | --- | --- | --- |
| Both action types, `DeleteRestoredAction` and `DeleteRestoredVersionAction`, with ILM transition and restore | [1ebf6f1](https://github.com/pgsty/silo/commit/1ebf6f146) (Poorna Krishnamoorthy) | [#10565](https://github.com/minio/minio/pull/10565) | 2020-11-12 | `RELEASE.2020-11-25T22-36-25Z` |
| `expireTransitionedObject` passes `lcOpts.VersionID` for every action, restored copies included | [2ff655a](https://github.com/pgsty/silo/commit/2ff655a74) (Poorna Krishnamoorthy) | [#10945](https://github.com/minio/minio/pull/10945) | 2020-11-25 | `RELEASE.2020-11-25T22-36-25Z` |
| `DeleteRestored()` and `DeleteVersioned()` helpers; `DeleteVersioned()` covers `DeleteRestoredVersionAction` only | [b984bf8](https://github.com/pgsty/silo/commit/b984bf8d1) (Harshavardhana) | [#16757](https://github.com/minio/minio/pull/16757) | 2023-03-09 | `RELEASE.2023-03-09T23-16-13Z` |
| **The regression:** the version ID is set only `if lcEvent.Action.DeleteVersioned()` | [ee158e1](https://github.com/pgsty/silo/commit/ee158e161) | [#19093](https://github.com/minio/minio/pull/19093) | 2024-02-22 | `RELEASE.2024-02-24T17-11-14Z` |

Before #19093, every restored copy was addressed by the version ID of the object it belongs to, so a restored current version with a version ID was cleaned up correctly. The commit message of #19093 says that it fixes tiered objects whose current version was deleted instead of getting a delete marker. For that it replaced the version ID with the `DeleteVersioned()` gate, which the non-transitioned expiry path already used, and the gate leaves out `DeleteRestoredAction`. The restored-copy branch sits in the same function and lost its version ID as a side effect. A restored `null` current version reaches the expiry with an empty ID, and an empty ID was never addressed correctly, before or after #19093.

**What SILO changed around the branch.**

| SILO change | Date | Released | Effect on the defect |
| --- | --- | --- | --- |
| [8ed5c90](https://github.com/pgsty/silo/commit/8ed5c90dc) keep tier data when expiry only adds a delete marker ([#253](https://github.com/pgsty/silo/pull/253)) | 2026-10-23 | from `RELEASE.2026-10-25T00-00-00Z` | None. It sets the suspended state and a keep-remote decision below the restored-copy branch. Upstream never set the suspended state in this function, so the gap in the branch is inherited, and this change did not close it. |
| [0a546c7](https://github.com/pgsty/silo/commit/0a546c7a7) ILM cleanup during migration ([#276](https://github.com/pgsty/silo/pull/276)) | 2026-11-02 | main only | None. This is the commit that added "Recheck the lifecycle decision and create the hot-tier tombstone before touching the remote tier" below the branch. The restored-copy branch returns before that code, which only runs for the other actions. |
| [7a060ca](https://github.com/pgsty/silo/commit/7a060cab1) and its revert [9b76a21](https://github.com/pgsty/silo/commit/9b76a2167) | 2026-08-15, 2026-09-15 | only together, in `RELEASE.2026-09-16T00-00-00Z` | None. They did not change the branch. |

The nine lines from `DeleteRestored()` on are identical in all 18 SILO releases and in upstream master, and so is `DeleteVersioned()`. The fix therefore touches code that SILO has never modified.

**The native-restore defects fixed alongside.** The restore code is also inherited. `RestoreTransitionedObject` in the pools layer and the set layer, and `updateRestoreMetadata`, are identical to upstream master in all 18 SILO releases, and no SILO commit touches them.

| Defect | Origin | Commit | Date | First upstream release |
| --- | --- | --- | --- | --- |
| Multi-pool restore waits on its own lock | Upstream. The pools layer took the object lock and set `NoLock`, while the restore builds fresh options for its writes, which do not carry it. Before this change, the pools layer held no lock for a restore. | [6186d11](https://github.com/pgsty/silo/commit/6186d1176) ([#20495](https://github.com/minio/minio/pull/20495), Harshavardhana) | 2024-09-29 | `RELEASE.2024-10-02T17-50-41Z` |
| First read failure writes a new empty `null` version | Upstream. The failure path passes a zero `ObjectInfo` to the metadata update, which rewrites the latest version with an empty version ID. | [c829e3a](https://github.com/pgsty/silo/commit/c829e3a13) ([#12090](https://github.com/minio/minio/pull/12090), Krishnan Parthasarathi) with [cbfdf97](https://github.com/pgsty/silo/commit/cbfdf97ab) (Harshavardhana) | 2021-04-19, 2021-04-23 | `RELEASE.2021-05-11T23-27-41Z` |
| Version routing by the latest write location | Upstream. The pool lookup of a restore never carried the requested version. It was built that way in #12090, was made explicit by the pool lookup in [76b21de](https://github.com/pgsty/silo/commit/76b21de0c) ([#14012](https://github.com/minio/minio/pull/14012), 2022-01-10, `RELEASE.2022-01-25T19-56-04Z`), and was exempted for tag and metadata writes only in [c4d0c49](https://github.com/pgsty/silo/commit/c4d0c49a5) ([#17451](https://github.com/minio/minio/pull/17451)), not for restore. | [c829e3a](https://github.com/pgsty/silo/commit/c829e3a13) (#12090) | 2021-04-19 | `RELEASE.2021-05-11T23-27-41Z` |
| Single-pool restore without the object lock | Upstream. The single-pool shortcut returns before any lock. The first draft of the restore locked only its final metadata update, and [cbfdf97](https://github.com/pgsty/silo/commit/cbfdf97ab) removed that, so no release held the lock from the first read. #20495 added a lock for multi-pool deployments only. | [c829e3a](https://github.com/pgsty/silo/commit/c829e3a13), [cbfdf97](https://github.com/pgsty/silo/commit/cbfdf97ab) | 2021-04-23 | `RELEASE.2021-05-11T23-27-41Z` |

The multi-pool deadlock came in September 2024, seven months after the expiry regression. The other three have been in restore since its first release in May 2021. The remaining restore repairs in this fix (version identity of the POST handler, encoded objects, queued restores, and the lock order of multipart completion) depend on the same unchanged functions and on the multipart completion path. They have not been traced to individual commits. The same holds for the older restore defects that the adversarial review found. The [review history](#review) separates them from those the fix itself introduced.

Dates, PR numbers, and release membership come from the git history. The effects of the native-restore defects are those shown by the tests described under Verification. The statements about the empty version ID and about the origin of each native-restore defect come from reading the code.

## Options {#options}

### Option 1: pass the exact version (PR #282)

Always pass the version ID in the restored-copy branch, and map an empty ID to `null`. Then the current-version case takes the same path the noncurrent case already takes. This is the smallest change that reaches the root cause, and it is adopted.

### Option 2: collapse the two lifecycle actions into one

Making the evaluator return `DeleteRestoredVersionAction` for every version would have the same effect at the call site. It would also change the action names seen by audit, tracing, and other callers of the lifecycle package, for no added safety. Rejected.

### Option 3: a dedicated "drop restore cache" storage call

A separate storage operation would make it impossible to confuse cache cleanup with deletion. It would also add a new storage RPC, and rolling upgrades would have to handle nodes that do not know it. This is a reasonable long-term direction, not a release fix.

### Option 4: guard only in the storage layer

A guard can refuse to remove data that is not a restore cache. It cannot stop the object-delete path, which writes a delete marker before any cache logic runs. The storage guard is necessary as a second line of defense but is not sufficient alone.

## Proposed fix {#fix}

The fix has five groups. The first is PR #282 as submitted. Groups 2 to 4 are maintainer follow-ups from the first two review rounds, and group 5 comes from the adversarial review.

1. **Address the exact version (PR #282).** `expireTransitionedObject` always passes the version ID in its restored-copy branch. An empty ID is sent as `null`, because the ListObjects `max-keys=1` shortcut reads the latest version without the bucket's versioning, so a `null` version can arrive with an empty ID even in a versioned bucket.
2. **Keep the versioning state.** The bucket's suspended state is now set before the restored-copy branch returns, not after it. Without this, the cleanup of a restored noncurrent `null` version in a suspended bucket reached storage without that state; this layout adds eight cases to the contributor's test, and all of them failed without the change.
3. **Clean up only what is proven to be a restore cache.**
   - The cleanup needs fresh metadata. If the set cannot establish read quorum, it does not fall back to the blind delete that ordinary unversioned DELETE may use.
   - If a queued cleanup for the `null` version now finds a replacement delete marker, it returns `VersionNotFound` instead of acting on it.
   - Read failures during restore or cleanup no longer trigger dangling-object removal of the version being rehydrated.
   - In `xlMetaV2.DeleteVersion`, a restored-copy cleanup checks the stored version before any other mutation. Only a stored object version whose transition is complete owns a restore cache; for anything else the call is a no-op. The check uses what is stored, not what the request claims. Legacy `xl.json` objects cannot hold a completed transition and are left untouched.
4. **Make native restore safe to rely on.** Once expiry is correct, restore becomes the remaining way to damage the version. Review found each of the following against main and reproduced it in tests, and each is fixed:
   - *Version identity.* The background restore keeps the bucket's versioning context. Before this, restoring a `null` version could create a new version ID pointing at the same remote object. A later expiry of either version could then remove the shared remote object; that consequence is reasoned from the code path, not reproduced end to end.
   - *First read failure.* If the first read of the target version fails, restore returns without writing anything. Before this, requesting a missing version created a new, empty `null` version.
   - *Multi-pool deadlock.* The lock already held by the pools layer is forwarded to the rehydration write, the multipart completion, and the metadata update. Before this, a multi-pool restore waited on its own lock until it timed out.
   - *Version routing.* The pool is chosen by the requested version, not by the latest version's write location. Before this, restoring an old version in pool 0, while the latest version lived in pool 1, failed with `VersionNotFound`.
   - *Encoded objects.* Rehydration keeps the ETag, the original part numbers that encrypted multipart objects use to derive their keys, the logical sizes of compressed parts, and the part index. Objects written by older releases with legacy part sizes are handled.
   - *Object Lock integrity.* A single-pool restore now holds the object write lock from its first metadata read until the restored copy is committed, as multi-pool restores already did since upstream [minio/minio#20495](https://github.com/minio/minio/pull/20495). Without the lock, a legal hold or a COMPLIANCE retention extension acknowledged during the download was overwritten by the snapshot taken at the start.
   - *Queued restores.* A restore of another version of the same key waits for that lock instead of giving up after one timeout. Giving up would have left `ongoing-request="true"` on the version for good, so every later POST failed with `RestoreAlreadyInProgress`.
   - *Lock order.* Single-pool multipart completion now takes the object lock before the upload lock. Every path takes its locks in the order object, part, upload. Completion takes no part lock, because `PutObjectPart` holds its part lock while it waits for the upload lock. An empty upload ID no longer aliases the object lock and deadlocks.
5. **Give each native restore an owner (adversarial review).** With groups 1 to 4 in place, the adversarial review still found three kinds of gap. A restore could be reached by other callers. A restore could act on a minority view of the version's metadata. And an old attempt could act on a newer one. Each item below closes findings that it reproduced in tests.
   - *Attempt identity.* Each POST that starts a rehydration writes an attempt ID into the version's internal metadata. With it, POST records the identity it resolved: version ID, ETag, size and modification time. The background worker, its upload, its part writes and its completion all carry the attempt. If the attempt no longer owns the version, the worker stops without writing, completing or resetting anything. A later POST that finds an ongoing restore takes it over only when no attempt is running. Otherwise it answers `409 RestoreAlreadyInProgress` within a few seconds, instead of waiting for the download.
   - *Captured identity.* The worker writes with the versioning state and the explicit version ID that POST resolved, and a `null` target stays `null`. Before this, enabling versioning while a restore was queued gave the restored copy a new version ID that pointed at the same remote object. A replacement `null` object under the same ID counts as a different target.
   - *Recovery.* A worker that fails before it takes its snapshot resets its own attempt to a retryable state, with bounded retries. A failed restore aborts its upload. The upload records its real creation time, and stale-upload cleanup keeps it while its attempt owns the version. Before this, cleanup took the age of the restored object for the age of the upload and removed new restores of old objects.
   - *Private upload.* The rehydration upload carries an internal marker. Every public multipart operation answers `NoSuchUpload` for that upload, and listings hide it. The marker is decided over all drives:
     - a majority of drives must show the marker for the upload to count as private;
     - its absence counts only when no drive shows it and the unreadable drives are not a majority;
     - anything else fails closed, and the upload is neither exposed nor removed.

     A marker supplied as user metadata is dropped when the upload is created. The marker is stripped before the commit.
   - *Authoritative revision.* POST, the worker and the reset read the exact version from every drive. They use the metadata revision that at least `max(n/2+1, read quorum)` drives hold, identified as in the [multi-pool fix](/blog/design/multi-pool-lifecycle-expiry/): the version header plus a digest of the normalized metadata.
     - They change only the restore fields of that revision, and write it only to the drives that hold it. Before this, a status write could copy one stale drive's metadata to every drive, and an acknowledged legal hold was lost.
     - If a write fails, the drives get back the revision they had.
     - When drives differ only in restore fields, the revision without those fields still identifies the version. A later POST, or the attempt's own reset, can then bring the drives back into agreement. A reset applies only when its attempt is the only one in progress.
     - Without such a revision, the request fails and writes nothing.
   - *Expiry and heal use the same view.* The fresh recheck of restored-copy expiry needs its own reason: a restored-copy expiry action, a valid restore deadline that has passed, a completed transition, and no restore in progress. Before this, another lifecycle action that was due could remove a renewed cache. The recheck decides on that authoritative revision. It refuses when the drives disagree on the restore state. Heal copies restore fields to an outdated drive only when a quorum holds the same fields; otherwise it waits.
   - *Commit staging.* Completion stages the object's metadata inside the upload before renaming it into place. An upload in that state is treated as committing: it is hidden, it cannot be aborted, and stale-upload cleanup keeps it.
     - A completion holds a commit lock from staging to the end of the commit.
     - Stale cleanup takes that lock before it decides on any upload past the stale age, ordinary or not. It keeps the lock until its rename ends, also when the rename outlives the drive deadline. Abort takes the lock for a committing upload. While a commit holds it, abort refuses and stale cleanup skips the upload.
     - Abort removes what a failed commit left only when every copy is staged and older than one hour. Stale cleanup removes one drive's copy only when that copy is staged and older than one hour.
   - *Bounded waits.* POST's first read takes no lock. Its only lock wait is bounded.
   - *Rolling upgrades.* Older nodes do not know the marker and would expose the private upload. The node that serves a POST now asks every peer through a new internal capability RPC. Until every peer answers that it supports native restore, POST answers `503 ServiceUnavailable` and writes nothing. A queued worker asks again before it creates its upload.
   - *Lock domains.* The adversarial review reproduced `DELETE` and `CopyObject` racing a restore in a distributed single-pool deployment whose erasure sets do not share hosts. That inherited split is closed by the [single-pool lock-domain fix](/blog/design/single-pool-lock-domains/), which this group depends on, and is not repeated here.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient.** Every path that expires a restored copy ends in `expireTransitionedObject`, now with an exact version. These paths are the scanner, GET and HEAD, listings, decommission, and drive heal, and the set and storage layers then act only on that version. Three layers back each other up:

- the version ID chooses the target;
- fresh metadata confirms the target and its expiry date;
- the stored transition state proves the data is a cache.

A wrong target that is not a completed tiered version cannot lose its data. The native-restore repairs ensure that the version being cleaned up is the one that was restored, with its protection metadata intact.

Group 5 makes those repairs hold under concurrency and partial failure:

- One attempt owns a version at a time, and only that owner can rehydrate the version, complete the restore or reset it.
- On any node that runs this release, no public caller can reach the attempt's upload, and the gate keeps restores off while any node does not.
- POST, the worker, expiry and heal all decide on the same authoritative revision. When there is none, each of them fails closed.
- Nothing removes a committing upload while its commit can still be running.

**Necessary.**

- Without the exact version, the reported defect stays.
- Without the versioning-state change, suspended buckets keep a failing layout.
- Without the metadata and storage guards, a stale or misrouted cleanup can still remove the only data of a version that is not tiered.
- Without the native-restore repairs, fixing expiry would make restore the path to the same damage: new version aliases, empty versions, lost legal holds, or versions stuck as "in progress".
- Without group 5, the adversarial review reproduced the following:
  - a client completing the private upload, or writing parts into it;
  - a stale drive's metadata overwriting an acknowledged legal hold on every drive;
  - an old attempt resetting a newer one;
  - expiry or heal acting on a minority restore state;
  - stale cleanup removing a running commit.

These changes have to ship together. Unblocking the multi-pool restore deadlock before the cleanup is correct would make the damaging cleanup reachable on more deployments.

**What the guards do not claim.** The storage guard only prevents a non-tiered version from giving up its data. If a wrong target is itself a completed tiered version, the guard passes, and the worst case is the loss of that version's restore cache, not of its data. Correct targeting remains the job of the version ID and the metadata recheck.

## Cost and compatibility {#cost}

- No public API, configuration, metric, or dependency change. Two internal metadata keys are added: the attempt on the version and the marker on its upload. One internal peer RPC answers whether a node supports native restore. Older releases ignore the keys.
- Restored copies of current versions are now removed by themselves. Restored copies that stayed because the old cleanup failed are removed on the next pass.
- **Behavior change during restore.** While a restore downloads from the tier, requests that need the object's write lock wait for it, on single-pool and multi-pool deployments alike. That covers GET, HEAD, PUT, DELETE, tagging, legal hold, and retention. A request that waits longer than the operation timeout (about ten minutes) fails with `503 RequestTimeout`. Before this change, single-pool deployments served reads during a restore, at the cost of the Object Lock race described above. The release notes state this. [#284](https://github.com/pgsty/silo/issues/284) tracks a two-phase restore that holds the lock only around the snapshot and the commit.
- **Behavior changes of `POST ?restore`.**
  - It answers `503 ServiceUnavailable` and writes nothing while any peer runs an older release or cannot be reached.
  - It fails without writing when the drives do not agree on the version's metadata.
  - While a restore of that version runs, it answers `409 RestoreAlreadyInProgress` within a few seconds.
  - Errors other than an invalid object state keep their usual S3 mapping instead of all becoming `InvalidObjectState`.
- Every multipart completion takes one more lock: the commit lock, taken last. Stale-upload cleanup tries the same lock once for each upload past the stale age.
- Heal of a version waits while its drives disagree on restore fields and no quorum holds the same fields.
- Rollback restores the old behavior, including the defect. Do not roll back while restores are running: older releases do not keep the restore upload private.

## Residual limits {#limits}

- **Existing damage is not repaired.** Delete markers created by the old cleanup stay. They are ordinary markers and can be removed with `DELETE ?versionId=`, after confirming from the ILM audit log or bucket notifications that the marker came from a restored-copy expiry. Data already removed from a `null` version, and hidden versions already deleted by noncurrent rules, cannot be recovered by this fix.
- **Availability during long restores** is the trade-off described above, pending #284.
- **Lock domains in large single-pool deployments.** In a distributed single-pool deployment whose erasure sets do not share the same hosts, DELETE and CopyObject lock in a different lock domain from PUT, metadata updates, and restore. A DELETE or copy during a restore can then race with it. This inherited split is broader than restore. The [single-pool lock-domain fix](/blog/design/single-pool-lock-domains/) closes it, and this fix must not ship without that one.
- **Rolling upgrades.** Upgrades must be monotonic: an older binary must not rejoin while restore uploads exist. The gate stops new restores on upgraded nodes only. A POST that an older node serves still uses the old path. An upload created before an older node joined is exposed to that node until the upload ends.
- **Restart.** The retries that reset a failed attempt run in memory. After a restart the version stays ongoing until a later POST takes it over.
- **Disagreeing drives.** Heal and expiry of a version wait while its drives disagree on restore fields and no quorum holds the same fields. A later POST, or the attempt's own reset, brings the drives back into agreement once enough of them answer. If the drives also disagree on other metadata, so that no revision has a quorum even without the restore fields, neither restore nor heal changes the version. It then needs a later metadata write, such as a tag update, that rewrites it on every drive. This double-fault case is reasoned from the code, not tested.
- **Failed commits.** What a failed commit leaves in an upload stays for an hour. Abort of it is refused while any drive cannot be read. Stale-upload cleanup removes it drive by drive.
- **Hung cleanup renames.** A stale-upload rename that hangs past the drive deadline keeps that upload's commit lock until it ends. A completion of the same upload waits behind it while holding the object lock. Other operations on that key are then delayed until the completion is canceled or reaches the operation timeout. Other keys are not affected.
- **Inherited and unchanged.** The sweep of temporary files can remove an in-flight part of any upload that streams for longer than the stale-upload age. Ordinary GET and HEAD can still return a stale drive's metadata when the drives agree on modification time and ETag but not on other fields. Restore decisions no longer depend on that read.

## Verification {#verification}

**Groups 1 to 4, on the integration head.**

- `TestExpireRestoredCopy` covers eight layouts across four lifecycle paths (scanner, HEAD, listings, and the synchronous call made by decommission and drive heal), on one pool and two. That is 64 cases: the contributor's 56 plus 8 for the suspended noncurrent `null` layout. They fail on main and pass with the fix.
- `TestExpireRestoredRequiresFreshMetadata`, `TestExpireRestoredRenewedOrMissing`, `TestExpireRestoredStorageBoundary`, `TestExpireRestoredKeepsReplacementDeleteMarker`, `TestExpireRestoredMetadataReadKeepsMinorityVersion`, and `TestExpireRestoredStorageRejectsOtherTypes` cover the guards.
- The `TestNativeRestore*` tests and `TestMultipartCompletionLockAlias` cover the native-restore repairs: pools, version routing, initial failure, POST version identity, Object Lock serialization, queued restores, concurrent completion, read safety, and encoded and legacy objects.
- The full `./cmd` suite and the targeted race selection passed on the head reviewed in the maintainer rounds.

**Group 5.** The patch adds 36 tests, on one pool and two where the layout matters:

- *Private upload:* `TestRestoreUploadIsolatedFromPublicParts`, `TestRestoreUploadHiddenFromPublicEntryPoints`, `TestRestoreUploadMarkerSpoofing`, `TestRestoreUploadMarkerQuorum`, `TestRestoreUploadUnreadableFailsClosed`, `TestRestoreUploadOutlivesStaleAge`, `TestRestoreFailureAbortsUpload`, and `TestRestoreSplitKeepsRunningUpload`.
- *Commit staging:* `TestRestoreUploadStagingFailsClosed`, `TestRestoreAbandonedCommitAbort`, `TestRestoreFailedCommitStaleCleanup`, `TestCleanupStaleUploadsSkipsRunningCommit`, and `TestCleanupStaleUploadsHoldsLockThroughRename`. They include a commit stalled past the grace, leftovers with an unreadable or unstaged copy, an ordinary upload that cleanup read just before its commit staged, and a cleanup rename that outlives the drive deadline.
- *Status writes and attempts:*
  - `TestRestoreStatusUsesQuorumGeneration` and `TestRestoreAttemptGenerationFencing`;
  - `TestRestoreGenerationSplitNeedsQuorum`, `TestRestorePOSTStatusWriteSplit`, and `TestRestorePOSTStatusWritePartialFailure`;
  - `TestRestorePOSTKeepsConcurrentProtection` and `TestRestorePOSTRacesCacheExpiry`;
  - `TestRestorePOSTRejectsReplacedTarget`, `TestRestoreKeepsCapturedNullIdentity`, and `TestRestoreReplacementNullObject`;
  - `TestRestoreSupersededAttempt`, `TestRestoreRecoversStrandedMarker`, and `TestRestoreRestartTakeover`;
  - `TestRestorePOSTOngoingBound`, `TestRestoreDuplicatePoolCacheStates`, and `TestRestorePOSTControls`.
- *Expiry and heal:* `TestExpireRestoredNeedsOwnReason`, `TestExpireRestoredUsesQuorumGeneration`, and `TestRestoreHealNeedsRestoreQuorum`.
- *Rolling upgrades:* `TestNativeRestoreCapabilityGrid` uses a real test grid with an old-style peer. `TestNativeRestoreCapabilityCache`, `TestNativeRestoreRollingUpgradeGate`, and `TestNativeRestoreCapabilityRevalidates` cover caching, reconnects and cancellation.

The regressions from the design rounds fail on the previous integration head and pass with the patch. Each regression from the patch review fails with only its own fix disabled and passes with it. The controls pass both ways.

The restore, lifecycle, multipart, tiering, expiry, stale-upload and heal selection passes: 260 tests in `./cmd`. The lifecycle and grid packages pass. The race-detector selection of 63 restore and cleanup tests reports no race. `gofmt` and `go vet` are clean.

The adversarial review's own probes ran on the final patch, and 33 of 46 pass. The other 13 are accounted for:

- three need the lock-domain fix. On the integration branch they show the races can no longer happen: COPY no longer overwrites the restored version, DELETE waits for the restore, and a public abort cannot find the hidden upload;
- one hits the inherited temporary-part sweep;
- nine assert outcomes that the agreed design changes on purpose. Examples are a heal deferral treated as fatal, a race that can no longer start, cleanups that now wait for the lock, and a stale drive left for heal rather than rewritten.

**Still to run before merge.**

- remote CI on the final head;
- a restore and expiry run against a real remote tier with SSE;
- a rolling upgrade from the previous release.

Multi-node lock domains, real mixed-binary clusters, hour-long storage stalls and clock skew between nodes have not been exercised.

**Integration.** The fix sits on #278 in one integration branch for the next release, with the lock-domain, delete-all, heal dry-run, #259, #285 and Console fixes stacked on it. Every pick applied without conflicts. On that head the full `go test ./cmd/... ./internal/...` suite passes, as do the CI race-detector selections and a race selection that covers every new test. An adversarial review of the combination found no defects. It checked lock domains, cleanup paths and purge against restore with executed probes.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Maintainer rounds 1 and 2 | Found the versioning-state gap, the missing storage guard and the native-restore defects; fixed as groups 2 to 4. |
| Adversarial review, design rounds 1 and 2 | Requested changes. Found seven problems. One was introduced by group 4: a client could replace a part of the restore upload after it was validated, and the restore then committed those bytes over a COMPLIANCE-protected version. Six were older:<br>- POST overwrote newer protection metadata;<br>- enabling versioning while a restore was queued aliased the `null` version;<br>- failed restores stayed ongoing for good;<br>- stale-upload cleanup removed new restores of old objects;<br>- another lifecycle action could expire a renewed cache;<br>- failed multipart restores leaked their uploads.<br>Round 2 agreed the design of group 5. |
| Patch review, round 3 | Requested changes. Introduced: older nodes ignore the private marker, the marker check did not fail closed, and attempts were not fenced. Pre-existing: a status write could spread a stale drive's metadata, POST could act on a replacement `null` version, and the POST wait bound did not hold. The lock-domain split went to its own fix. |
| Patch review, rounds 4 to 10 | Round 4 found four problems: a failed POST write stranded recovery, commit staging exposed the upload, the capability check raced, and a stale first read bypassed the wait bound. Round 5 found five more: an old reset could clear a newer attempt, a split view let cleanup delete a running upload, the staging grace removed unstaged copies, a failed activity read restored the long wait, and a cached capability answer ignored cancellation. Round 6 found that expiry could follow a minority expired header. Round 7 found that heal could promote a minority restore state and that a committing upload could stay forever. Round 8 found that abort removed a leftover with an unknown age and that stale cleanup could remove a running commit. Round 9 found that stale cleanup could still remove an ordinary upload it had read just before the commit staged (pre-existing). Round 10 found that the cleanup's rename could outlive its lock at the drive deadline. All were fixed with regressions. |
| Patch review, round 11 | Approved with one documentation nit: a completion that waits behind a hung cleanup rename holds the object lock. Recorded under [Residual limits](#limits). |

## References {#references}

- Issue: [#281](https://github.com/pgsty/silo/issues/281)
- Contributor PR: [#282](https://github.com/pgsty/silo/pull/282)
- Companion fix: [Multi-Pool Lifecycle Expiry](/blog/design/multi-pool-lifecycle-expiry/) ([#278](https://github.com/pgsty/silo/issues/278))
- Restore lock follow-up: [#284](https://github.com/pgsty/silo/issues/284)
- Upstream multi-pool restore lock: [minio/minio#20495](https://github.com/minio/minio/pull/20495)
