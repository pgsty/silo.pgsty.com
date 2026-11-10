---
title: "Lifecycle Delete-All Must Stay on One Key"
linkTitle: "Delete-All on One Key"
date: 2026-11-04
lastmod: 2026-11-10
author: "PGSTY SILO Maintainers"
summary: >
  Why a lifecycle or batch "delete all versions" of one key also deletes every object stored under that key's name, and why purging the key's own versions by ID, under the object lock and after a recheck, is the minimum complete repair.
tags: [Design, Lifecycle, Batch Expiration, Data Safety]
weight: 10
draft: false
url: "/blog/design/ilm-delete-all-exact-key/"
---

This record covers a defect found during review of the [#278](https://github.com/pgsty/silo/issues/278) fix ([Multi-Pool Lifecycle Expiry](/blog/design/multi-pool-lifecycle-expiry/)). It was evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) and against the maintainer integration branch for #278 and #281, as it stood before integration.

**Status:** Shipped in [SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`).

## Short answer {#tldr}

The defect is real and gated `SILO Server 20261109`. Three operations remove "all versions" of a key:

- the lifecycle extension `ExpiredObjectAllVersions`;
- the lifecycle action `DelMarkerExpiration`;
- batch expiration with `purge.retainVersions: 0`, which is the default.

All three do it with a recursive delete of the key's directory on the drives. Object `a/b` is stored inside the directory of object `a`. Purging `a` therefore also removes `a/b`, `a/b/c`, and every other key that begins with `a/`. Those keys are removed in every erasure set and every pool, whatever their age, and whether or not any rule selects them. The purge writes one ILM audit entry and one bucket notification, both for `a`. Nothing records the other keys.

The same path has two further faults. It skips the recheck that should confirm the expiry under the object lock, so a version written after the scanner's decision is deleted too. It also drops the metadata of tiered versions without leaving tier free versions, so their remote objects are never cleaned up.

The fix replaces the recursive delete with a purge of the key's own versions by version ID. The purge runs under the object lock that the delete already holds and decides again on the versions it reads under that lock. It then deletes them one at a time, oldest first and the latest last, through the version delete of the drives, which removes the object directory only when it is empty. Keys with a transitioned version are refused in `SILO Server 20261109` and keep everything. The change sits on top of the #278 fix, which touches the same function, and on the [single-pool lock-domain fix](/blog/design/single-pool-lock-domains/).

## Classification {#assessment}

| Aspect               | Assessment                                                                                                                                                                                                                                                                                                                                                                   |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nature               | Data-loss defect in the implementation of "delete all versions". Inherited from upstream MinIO and present in every SILO release, including RELEASE.2026-10-26T00-00-00Z. Not a regression.                                                                                                                                                                                  |
| Affected deployments | Every erasure-coded deployment: one or more pools, one or more erasure sets. Versioned, versioning-suspended, and unversioned buckets.                                                                                                                                                                                                                                       |
| Affected operations  | `Expiration` with `ExpiredObjectAllVersions` (`mc ilm rule add --expire-all-object-versions`). `DelMarkerExpiration`. Batch expiration rules whose purge keeps no versions. Decommission and rebalance when they apply one of these rules during the move.                                                                                                                   |
| Affected layouts     | A key `K` that the operation removes while other keys begin with `K/`. The other keys need not match the rule or be old, and they can live in another erasure set or pool.                                                                                                                                                                                                   |
| Not affected         | Directory objects (`K/`), whose metadata is stored apart from their children. Sibling keys such as `Kx` or `K-1`. Lifecycle on Object Lock buckets, where both rule types are rejected at configuration and skipped at evaluation. Other lifecycle actions, which act on one version at a time. Force delete (`x-minio-force-delete`), which is a prefix delete by contract. |
| Severity             | Critical. Live objects that no rule selected are deleted permanently, and no audit entry, notification, or trace names them.                                                                                                                                                                                                                                                 |
| Reachability         | Ordinary configuration and ordinary key layouts: a key that is also the "folder" of other keys, such as `report` and `report/page-1`. A batch expiration job written with default settings reaches it.                                                                                                                                                                       |
| Release urgency      | Release blocker for `SILO Server 20261109` (shipped in `RELEASE.2026-11-09T00-00-00Z`).                                                                                                                                                                                                                                                                                      |
| Remaining effort     | Complete; shipped in `SILO Server 20261109` (`d998292387cc`).                                                                                                                                                                                                                                                                                                                |
{.wide .expand}

## When it happens {#trigger}

Three callers ask the pools layer for an all-versions delete:

- **The expiry worker**, `applyExpiryOnNonTransitionedObjects`. It runs expiries that the scanner queues, and also those that GET, HEAD, and listings queue when they see a due object.
- **The migration expiry**, `applyMigrationExpiry`. Since [#276](https://github.com/pgsty/silo/pull/276), decommission and rebalance call the worker's function directly during the walk.
- **Batch expiration**, `batchObjsForDelete`, for rules whose purge retains no versions.

We probed each one on main. In every layout, the old key is due and every other key is new:

| Probe                                                                                 | Layout                                                                                                                    | Result on main                                                    |
| ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| Scanner and expiry worker, `ExpiredObjectAllVersions`, one pool with two erasure sets | `ea/parent` (two versions); `ea/parent/child` in the same set; `ea/parent/deep/grandchild` in the other set; `ea/parentx` | parent, child, and grandchild deleted; `ea/parentx` kept          |
| The drive scanner's own folder walk, then the worker                                  | the same shape in one set                                                                                                 | the same                                                          |
| Two pools                                                                             | `ea/parent` in the first pool; `ea/parent/child` and `ea/parentx` in the second                                           | parent and child deleted; `ea/parentx` kept                       |
| `DelMarkerExpiration`                                                                 | `dm/parent` whose latest version is an old delete marker; `dm/parent/child`                                               | both deleted                                                      |
| Unversioned bucket                                                                    | `ea/parent`, `ea/parent/child`                                                                                            | both deleted                                                      |
| Directory object                                                                      | `ea/dir/`, `ea/dir/kid`                                                                                                   | `ea/dir/` deleted; `ea/dir/kid` kept                              |
| Batch expiration, rule `name: bx/parent`, default purge                               | `bx/parent`, `bx/parent/child`, `bx/parentx`                                                                              | parent and child deleted; `bx/parentx` kept                       |
| Decommission and rebalance with `ExpiredObjectAllVersions`                            | `obj-01`, `obj-01/child`, `obj-01x`                                                                                       | `obj-01` and `obj-01/child` gone from both pools; `obj-01x` moved |
{.wide .expand}

The probes give the same results on the #278 integration branch. That change does not mitigate this defect.

## Root cause {#root-cause}

The delete passes through three layers, and each one widens it.

1. **The callers ask for a prefix delete.** For `Action.DeleteAll()`, `applyExpiryOnNonTransitionedObjects` sets `DeletePrefix` and `DeletePrefixObject`. Batch expiration sets the same two flags.
2. **The pools layer drops the other options.** `erasureServerPools.DeleteObject` answers every `DeletePrefix` request with `deletePrefix`. That function calls each pool with a fresh `ObjectOptions{DeletePrefix: true}`, which loses two things:
   - `Expiration.Expire`. The recheck in `erasureObjects.DeleteObject`, which upstream added for exactly this action, therefore never runs.
   - `DeletePrefixObject`. `erasureSets.DeleteObject` therefore sends the delete to every erasure set of every pool, and it discards their errors.
3. **The drives delete a directory.** `erasureObjects.deletePrefix` calls `Delete` with `Recursive` and `Immediate` on every drive. On a drive, object `a` is the directory `a/`, which holds its `xl.meta` and data directories. Object `a/b` is `a/b/xl.meta`, inside that directory. The recursive delete moves the whole tree to the drive's trash and purges it at once.

Directory objects escape only because `a/` is stored as `a__XLDIR__`, next to `a/` rather than inside it.

The same path has three side effects:

- **No recheck.** The scanner may have decided minutes or hours earlier. On one pool, a version written after the decision is deleted with the rest; we reproduced this. Review of the #278 fix found a related case, which we reasoned through but did not probe: a decision made on incomplete metadata, for example with half of the drives unreadable and one of the rest missing a new version, deletes a committed version.
- **Tier leak.** Deleting `xl.meta` wholesale removes the record of every transitioned version, including free versions that earlier deletes left for tier cleanup. Their remote objects stay in the tier, and nothing refers to them any more. We reproduced this for the key and for its children.
- **Errors are ignored.** The fan-out across erasure sets reports success even when a set's delete fails.

## Where the behavior came from {#history}

### Provenance {#provenance}

**The defect came from upstream MinIO. SILO inherited it at the fork and did not introduce it.** The fork point is [27742d469](https://github.com/pgsty/silo/commit/27742d469462e1561c776f88ca7a1f26816d69e2) (2025-12-03). Every function on the defective path is unchanged from upstream master ([7aac2a2c5](https://github.com/pgsty/silo/commit/7aac2a2c5b7c882e68c1ce017d8256be2feea27f), 2026-02-12): `erasureServerPools.deletePrefix`, `erasureSets.deletePrefix`, `erasureSets.DeleteObject`, `erasureObjects.deletePrefix`, and `batchObjsForDelete` compare equal to upstream, and so does the `DeletePrefix` branch of `erasureServerPools.DeleteObject` and `erasureObjects.DeleteObject`. The lifecycle caller keeps its upstream options for a delete-all.

The defect is the combination of four upstream ingredients. The first release in which a lifecycle rule could delete other keys is `RELEASE.2023-06-29T05-12-28Z`. The first SILO release with the defect is `RELEASE.2025-12-03T12-00-00Z`, the first SILO tag. All 18 SILO releases from there through `RELEASE.2026-10-26T00-00-00Z` contain it.

**Upstream ingredients.**

| Ingredient                                                                                                                                                                                                       | Commit                                                                                                                                                     | Date and author                    | First upstream release         |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------ |
| A recursive delete of the key's directory on every drive of every erasure set, reached through a pools-level function that builds fresh options. Added for force delete, where removing a prefix is the purpose. | [7722b91e1](https://github.com/pgsty/silo/commit/7722b91e1dd465c957c014be4077f6d3039e5ee3), [minio/minio#12504](https://github.com/minio/minio/pull/12504) | 2021-06-16, Anis Elleuch           | `RELEASE.2021-06-17T00-10-46Z` |
| The first lifecycle caller: `ExpiredObjectAllVersions` sets `DeletePrefix`. The same commit moved the object lock ahead of the prefix branch.                                                                    | [aae684641](https://github.com/pgsty/silo/commit/aae684641325e1c37375d455c790e58d902bd7b6), [minio/minio#17521](https://github.com/minio/minio/pull/17521) | 2023-06-28, Harshavardhana         | `RELEASE.2023-06-29T05-12-28Z` |
| Batch expiration: a purge that keeps no versions deletes with `DeletePrefix`. At first it set no `DeletePrefixObject`, so it fanned out to every set.                                                            | [a50f26b7f](https://github.com/pgsty/silo/commit/a50f26b7f56e5e6b1df8a648423736319ecdabd6), [minio/minio#17946](https://github.com/minio/minio/pull/17946) | 2023-12-02, Krishnan Parthasarathi | `RELEASE.2023-12-02T10-51-33Z` |
| `DelMarkerExpiration`, which takes the same path.                                                                                                                                                                | [7926401cb](https://github.com/pgsty/silo/commit/7926401cbd5cceaacd9509f2e50e1f7d636c2eb8), [minio/minio#19481](https://github.com/minio/minio/pull/19481) | 2024-04-30, Krishnan Parthasarathi | `RELEASE.2024-05-01T01-11-10Z` |
{.wide .expand}

Upstream changes that touched the same functions and left the effect alone:

- [1a884cd8e](https://github.com/pgsty/silo/commit/1a884cd8e) ([minio/minio#13242](https://github.com/minio/minio/pull/13242), 2021-09-17, `RELEASE.2021-09-18T18-09-59Z`) made the fan-out across erasure sets concurrent and made it discard errors.
- [b49fc33cb](https://github.com/pgsty/silo/commit/b49fc33cb) ([minio/minio#15148](https://github.com/minio/minio/pull/15148), 2022-07-11, `RELEASE.2022-07-13T23-29-44Z`) made the force delete purge the drives' trash immediately.
- [88a89213f](https://github.com/pgsty/silo/commit/88a89213f) ([minio/minio#19231](https://github.com/minio/minio/pull/19231), 2024-03-09, `RELEASE.2024-03-10T02-53-48Z`) made that purge non-blocking.
- [6a1558081](https://github.com/pgsty/silo/commit/6a1558081) ([minio/minio#19685](https://github.com/minio/minio/pull/19685), 2024-05-06, `RELEASE.2024-05-07T06-41-25Z`) made the per-set drive delete return write-quorum errors. The fan-out across sets still discards them.

**Upstream changes that did not narrow the path.** None of the three takes effect, because the pools layer rebuilds the options:

- [eb55034df](https://github.com/pgsty/silo/commit/eb55034df) ([minio/minio#17827](https://github.com/minio/minio/pull/17827), 2023-08-09, `RELEASE.2023-08-09T23-30-22Z`) added `DeletePrefixObject`. It is an optimization that avoids the fan-out for configuration deletes. It does not protect other keys.
- [c61dd16a1](https://github.com/pgsty/silo/commit/c61dd16a1) ([minio/minio#19365](https://github.com/minio/minio/pull/19365), 2024-03-27, `RELEASE.2024-03-30T09-41-56Z`) set that flag in the scanner and in batch expiration, again "to avoid fan-out calls".
- [289223b6d](https://github.com/pgsty/silo/commit/289223b6d) ([minio/minio#19359](https://github.com/minio/minio/pull/19359), 2024-03-27, `RELEASE.2024-03-30T09-41-56Z`) added the recheck under `Expiration.Expire` in `erasureObjects.DeleteObject`. It is the only one of the three aimed at safety, and the pools-level call never reaches it.

**SILO releases.** The tags `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z` (18 tags) all contain the pools-level and set-level prefix functions, the scanner and batch call sites, and the drive-level delete in their upstream form.

**SILO commits that touched the path.** None changed the prefix delete itself. Their effect on the defect:

| Commit                                                                                                                                                                                                                                                                                                                                                                       | Date and author                                          | Released in                                                               | Effect                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [40bee4b7b](https://github.com/pgsty/silo/commit/40bee4b7b), [e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938)                                                                                                                                                                                                                                                     | 2026-09-06 and 2026-09-11, Feng Ruohang                  | `RELEASE.2026-09-16T00-00-00Z`                                            | None. In the `DeletePrefix` region of `erasureServerPools.DeleteObject` they only edited the comment above the object lock. The rest of their changes (conditional deletes, cross-pool serialization) sits after the branch.                                                                                                                                                                                                                         |
| [1cf529ce8](https://github.com/pgsty/silo/commit/1cf529ce8), [eb4f5e5b3](https://github.com/pgsty/silo/commit/eb4f5e5b3), [60c7179dd](https://github.com/pgsty/silo/commit/60c7179dd), [a30270d9b](https://github.com/pgsty/silo/commit/a30270d9b), [3c82748e1](https://github.com/pgsty/silo/commit/3c82748e1), [a2073d251](https://github.com/pgsty/silo/commit/a2073d251) | 2026-09-15 to 2026-10-24, Feng Ruohang and Denis Babchuk | `RELEASE.2026-09-16T00-00-00Z` to `RELEASE.2026-10-25T00-00-00Z`          | None. They changed other parts of `erasureServerPools.DeleteObject` and of the bulk delete (version-delete reconciliation across pools, data movement, delete-marker placement, tier references). The `DeletePrefix` branch returns before all of that code.                                                                                                                                                                                         |
| [1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7)                                                                                                                                                                                                                                                                                                                  | 2026-10-18, Feng Ruohang                                 | `RELEASE.2026-10-18T00-00-00Z`                                            | Narrowed one caller. Decommission and rebalance used to remove a moved key from the source pool with the prefix delete, as upstream does. They now remove the moved versions by ID. The commit's stated aim was concurrency safety.                                                                                                                                                                                                                  |
| [7a060cab1](https://github.com/pgsty/silo/commit/7a060cab1), [374de0fa3](https://github.com/pgsty/silo/commit/374de0fa3), [9b76a2167](https://github.com/pgsty/silo/commit/9b76a2167)                                                                                                                                                                                        | 2026-08-15, 2026-09-08, 2026-09-15                       | not released                                                              | An access-frequency relocation feature added a caller of the prefix delete on an exact key. It moved to version-addressed deletes and was then reverted. The `RELEASE.2026-09-16T00-00-00Z` tag contains none of it.                                                                                                                                                                                                                                 |
| [0a546c7a7](https://github.com/pgsty/silo/commit/0a546c7a7), merged with [#276](https://github.com/pgsty/silo/pull/276) in [0fc5a0b52](https://github.com/pgsty/silo/commit/0fc5a0b52)                                                                                                                                                                                       | 2026-11-02, Feng Ruohang                                 | `RELEASE.2026-11-09T00-00-00Z` (shipped together with this exact-key fix) | Widened on `main` before this fix. Decommission and rebalance send delete-all actions through `applyExpiryOnNonTransitionedObjects`, which added a caller of the defective path while leaving the delete-all options as they were. [19910230a](https://github.com/pgsty/silo/commit/19910230a) and [a995921e5](https://github.com/pgsty/silo/commit/a995921e5), which came before it, run version-only actions during migration and do not widen it. |
{.wide .expand}

So the defect is not a regression in any published SILO release. The only SILO change that widened its reach (#276) shipped in `SILO Server 20261109` together with this exact-key purge.

**Established from git history, not by running:** the introducing commits, their dates and the first upstream release for each, the byte-for-byte equality of the functions listed above with upstream master, and the contents of each SILO release. The behavior of each ingredient commit as a release was not rebuilt and run.

**Context.** Upstream master still has the same code. In SILO, #276 makes the migration walks run this expiry immediately.

## Options {#options}

### Option A: an exact-object delete on the drive {#option-a}

A new drive operation would remove `xl.meta` and the data directories it references, then remove the object directory only if it is empty.

- It protects the children.
- It deletes every version the drive holds, including versions written after the decision or missing from the quorum view. It still needs the recheck, and it cannot limit itself to the decided versions without taking a version list. At that point it is the existing `DeleteVersions` call.
- To avoid the tier leak, the drive would have to write free versions itself, which duplicates what the version-delete path already does.
- It needs a new storage call. A new flag on the existing `Delete` call would be unsafe: older nodes decode `DeleteOptions` and skip unknown fields, so during a rolling upgrade they would run the recursive delete on their drives.

Rejected: more storage code, an upgrade hazard, and it still needs Option B's logic.

### Option B: purge the key's own versions by ID {#option-b}

This is the recommended option.

- **Children.** The version-delete path (`xlStorage.deleteVersions`) rewrites or removes `xl.meta` and moves the data directory of each removed version to the trash. It removes the object directory only when that directory is empty, so other keys stay. A prototype through the existing bulk path deleted all four versions of a key, a delete marker and a tiered version among them, and left the children in both erasure sets intact.
- **Tiered versions.** `xlMetaV2.DeleteVersion` adds a free version for each transitioned version. The prototype left one, and the scanner's free-version cleanup removes the remote object later ([Tier Free Versions](/blog/design/tier-free-version-semantics/)).
- **Object Lock.** Lifecycle rejects both rule types on lock-enabled buckets at configuration and skips them at evaluation; the purge does not change that. Because the purge deletes by version ID, it can enforce retention and legal hold per version in this one place, where the primitive checks each physical revision it would remove. Authorization of a batch submitter is a separate check at the caller.
- **Replication.** Delete-all stays a local purge. Versions are removed without replication state, no delete marker is created, and nothing is queued, as today.
- **Quorum and partial history.**
  - The purge deletes only the versions it decided on. A version missing from the quorum view stays, and heal reconciles it.
  - A write-quorum failure leaves the key in place and the next scan retries.
  - When a long list is split into several calls, the oldest versions go first and the latest version last, so a partial purge never changes the current version or exposes an older one.
- **Multiple pools.** The same version list goes to the key's erasure set in every pool. A pool that does not hold a version answers "not found", which the bulk path accepts for a physical delete. The fan-out to every erasure set goes away.
- **Cost.** Each drive in one set per pool does one read-modify-write of `xl.meta` and one data-directory rename per version, all under the object lock. Very long histories are split into several calls.
- **Rolling upgrade.** The purge uses the existing `DeleteVersions` call, with no new wire field or format change.
- **The #278 check.** The merged check already reads the versions in all pools under the lock and evaluates the rule. The purge can use that list instead of a yes-or-no answer.

The design review changed three points of this option; [Proposed fix](#fix) describes the result. The bulk path reorders the versions of a key and has no barrier between pools: in a two-pool probe it removed the latest delete marker while the delete of an older version failed, and a read then returned that older version. The purge therefore deletes one version at a time. A free version alone does not make tiered keys safe here: it hands the remote object to the tier cleanup, and the review showed cases where a copy in another pool, or a delete that missed its quorum, still referenced that object. Keys with transitioned versions are therefore refused. And because duplicate copies and `null` writes repeat a version ID, the purge records every copy in every pool before it deletes anything.

### Option C: refuse when other keys exist under `K/` {#option-c}

A one-entry listing of `K/` before the purge would skip such keys.

- It races: a key written under `K/` after the listing is still deleted, because the lock on `K` does not serialize writes to `K/child`.
- The rule silently never applies to such keys.
- Every purge pays for a listing across all erasure sets.
- The tier leak and the missing recheck remain.

Rejected.

### Option D: keep the prefix delete, but pass `Expire` and `DeletePrefixObject` through {#option-d}

This restores the recheck. With those options, the set-level delete refused a version written after the decision. It does not protect the children: a child in the key's own erasure set is still deleted, while a child in another set survives. The loss would then depend on hashing, and the tier leak would remain.

Rejected as the fix. Its recheck is part of Option B.

## Proposed fix {#fix}

This is the design agreed in two design review rounds and implemented in the reviewed patch.

1. **A dedicated option.** The expiry worker, the migration expiry, and batch expiration request the purge through a new in-memory option, `ObjectOptions.DeleteAllVersions`, and stop setting `DeletePrefix` and `DeletePrefixObject`. `DeletePrefix` keeps its meaning for force delete and for internal callers that mean a prefix. The option is rejected together with `DeletePrefix`, a version ID, data movement, or any option that creates a delete marker. Every layer below the pools layer rejects it too, so a misrouted request never turns into another kind of delete.
2. **Decide on the history under the lock.** `erasureServerPools.DeleteObject` hands the request to the purge right after it takes the object lock, before the #278 check, on single-pool deployments too.
   - Lifecycle: the unchanged `lifecycleEventsAllPools` evaluates the rule on the versions of the key in all pools. The purge runs only if the latest version still carries a delete-all event.
   - Batch expiration has no rule to evaluate. The latest version must still be the one the walk matched, by version ID (an empty ID counts as `null`) and modification time. Otherwise the key is reported as not expired and is not retried.
   - A second read of the authoritative history of each pool records where each approved version lives: every copy, including older writes of the same ID such as `null` versions written in several pools. This read may only confirm the approval; it never adds a version. Any difference, or a history that the drives cannot tell, returns `InsufficientWriteQuorum` and deletes nothing. A key without versions is a success that removes nothing.
3. **Check every write before deleting any.**
   - The purge reads `xl.meta` on every drive of the key's set in every pool, including pools whose quorum view has no copy. A minority of drives can hold another revision of a version than the one the history accepted, so every revision of an approved version on every drive is checked. A drive that cannot be read could hide such a revision, and heal would later remove what a purge left on it, so an unreadable drive refuses the whole key. The purge then deletes on exactly the drive handles it read; a handle that a reconnect installs later is never used.
   - If any revision of any version is transitioned, the whole key is refused. See [Tiered keys](#tiered).
   - The purge enforces retention and legal hold on every write it would delete. A protected revision refuses the whole key.
4. **Delete in order, by version ID.**
   - One version at a time, oldest first, through the version delete of the drives (`DeleteVersion`) in the key's erasure set of each pool that holds a copy, on the drives it checked. That call rewrites `xl.meta`, moves the version's data directory to the trash, and removes the object directory only when it is empty. The delete writes no marker, no replication state, and no free version.
   - For each version, older writes go before the copy that reads choose.
   - The latest version goes last and alone, only after every older version is gone from every pool. A purge that stops therefore never changes what a read returns, and never exposes an older version.
   - The purge stops at the first error. A delete that reached its write quorum but failed on some drives is repeated on those drives a bounded number of times while the lock is still held; what remains is left to heal.
   - Each call has a budget of 1000 versions and one minute, its reads and checks included, checked before each version. A longer history stops before the latest version and continues on the next expiry, with a fresh history and a fresh decision.
5. **Report what was removed.** The purge counts the logical versions it removed, delete markers included, duplicate copies and free versions not, and returns the approved latest version. The ILM audit entry carries the count in the tag `ilm-versions-removed`. A purge that fails or stops after it began to delete is audited as partial (tag `ilm-partial`) with the count, the error and, starting in `SILO Server 20261109`, the tag `ilm-incomplete-reason`, also when it removed copies but no whole version; it is traced with `result=partial` and sends no removal notification. A purge that removed nothing because the key had nothing to remove sends no removal notification and only a plain trace. A lifecycle purge refused before it deleted anything (a tiered version, the rule no longer applying, Object Lock) is counted and traced with `result=refused`, its reason and its error, and is not audited. One that failed before it deleted anything (an unreadable history or another error) is also audited and logged. The reasons in `expiry_incomplete_total` are `tier_unsupported`, `budget` (stopped at its budget after progress), `changed` (the latest version that a batch matched has changed) and `history_unavailable`, plus the `not_applicable`, `locked` and `error` that other expiries share; see [Multi-Pool Lifecycle Expiry](/blog/design/multi-pool-lifecycle-expiry/#fix). Batch expiration counts objects and delete markers from the purge's results, and a job that failed to remove a delete marker is reported as failed.

### Tiered keys {#tiered}

Delete-all of a key with transitioned versions does not purge tiered versions in `SILO Server 20261109`.

- The expiry worker still sends a delete-all of a transitioned latest version to `expireTransitionedObject`. That writes a delete marker and keeps every version and remote object under it, and no later scan removes them.
- A key whose latest version is hot but whose older versions are tiered is refused, and nothing is deleted. Starting in `SILO Server 20261109`, the scanner of a pool that holds such a tiered version no longer queues the purge: each drive scanner counts the skip once per cycle as `tier_unsupported_skipped`. A tiered version that only another pool holds is unknown to that scanner, so the purge still decides and refuses the key with `tier_unsupported`, which is also logged; repeated identical refusals of a key are suppressed by the duplicate-suppression logger until its hourly reset. Batch expiration counts the key as refused in `keysRefused` (`complete-with-skips`, [`07b89b98f`](https://github.com/pgsty/silo/commit/07b89b98f)) and does not retry it within the run. During decommission or rebalance, `SILO Server 20261109` instead migrates the live versions and their tier metadata normally when tier evidence rules out whole-key expiry. It captures that evidence across all pools and drives before moving the first version, so a hot winning copy cannot hide a tiered duplicate or a minority revision. Physical completion checks still prevent a pool with residual data from being declared finished.

A tier-safe purge must not hand a remote object to the tier cleanup while any copy still references it, including after a delete that failed its quorum. That needs durable cleanup records and proof under the lock, and it is a separate change.

### Coordination {#coordination}

- **The #278 fix.** This change sits on the #278 commit and uses its helpers unchanged: `lifecycleEventsAllPools` for the decision and `objectVersions` for the per-pool histories. The purge runs before the merged check, so it needs neither `CheckedAllPools` nor the single-pool exemption.
- **The single-pool lock-domain fix.** On a single pool, writes of a key lock in its own erasure set, while `DELETE` locks in the first set; see [Lock Domains of Large Single-Pool Clusters](/blog/design/single-pool-lock-domains/). The purge decides and deletes under the `DELETE` lock, so it excludes every writer of the key only once that fix is in. It lands first, and this change is rebased onto it. The purge adds no locking of its own.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient.** Every delete-all reaches `erasureServerPools.DeleteObject`. That includes the expiry worker with all its producers (scanner, GET, HEAD, listings), the migration expiry, and batch expiration. With the dedicated option, none of them reaches a recursive delete:

- A version delete touches only the key's own `xl.meta` and data directories. Children have their own `xl.meta`, and the object directory is removed only when it is empty.
- The recheck runs under the lock that serializes writes to the key, with the same evaluator as the scanner, so a decision that no longer holds deletes nothing.
- Deleting only the approved list keeps versions that the quorum view missed.
- Deleting the latest version last keeps what reads return until every older version is gone.
- Refusing keys with transitioned versions keeps every remote object referenced.

**Necessary.** Each part closes a path that otherwise stays open:

- Without the exact purge, children are deleted. Option D shows that even the single-set prefix delete loses them.
- Without the recheck on single-pool deployments, versions written after the decision are deleted.
- Without restricting the delete to the approved list, versions missing from the quorum view are deleted.
- Without the order and the barrier before the latest version, a failed delete in one pool exposes an older version.
- Without the tier refusal, remote objects leak, or the tier cleanup removes one that a copy still uses.
- Without the batch and migration routing, those callers keep the prefix path.
- Without a dedicated option, a caller that sets the old flags would reach the prefix path again. `DeletePrefixObject` has had no effect on this path for years without anyone noticing. Starting in `SILO Server 20261109`, the pools layer also refuses `DeletePrefix` together with `Expiration.Expire` as `InvalidArgument`, so a lifecycle expiry never deletes a prefix. A force delete (`DeletePrefix` without an expiry) is unchanged.

**Deliberately excluded.**

- Force delete and the speedtest cleanup keep the prefix delete; it is their contract.
- Internal configuration deletes (`deleteConfig`, `delServerConfigHistory`) take the same recursive path on the system bucket. A collision needs a configuration name that extends another record's file name with `/`, such as an IAM user whose name begins with another user's name followed by `/identity.json/`. We confirmed the mechanism at the configuration layer. We did not check whether the admin API accepts such a name. This is low severity, and a follow-up can move these deletes to the same exact purge.

## Cost and compatibility {#cost}

- No API, configuration, storage-format, or wire change. The new options exist in memory only.
- Per delete-all, the purge reads `xl.meta` of the key's set in each pool three times: for the decision, for the placement, and to check every drive. Then, for each version, every drive of each set that holds a copy does one read-modify-write of `xl.meta` and one data-directory move. Today's delete is one recursive delete on every drive of every set. Large clusters do less work; keys with long histories do more and hold the object lock longer, at most for the budget of one call.
- Trash is purged in the background instead of immediately, so space comes back slightly later.
- A delete-all whose decision no longer holds now does nothing, single pool included; the scanner retries it on a later pass.
- Rolling upgrade is safe, because only existing storage calls are used. Protection is complete only once every node that executes expiries runs the fix: the node that runs an expiry decides how it deletes, so an old node in a mixed cluster still runs the recursive delete. Keep the interim mitigation until every node runs the fix.
- **Usage and quota.** The scanner accounts every version of a key under a delete-all at its size, queued or not, instead of as already removed. Usage, and so hard quota, drops after a fresh scan of the key's subtree once the purge succeeded; that can take up to the scanner's directory interval, not one cycle. The alerts on many versions and on large versions count the versions of a key that the scanner does not queue.
- Rollback restores the old behavior, and neither direction needs a migration.

## Residual limits {#limits}

- **Past losses are not repaired.** The recursive delete purges the trash immediately, so there is no practical on-drive undo.
- **Orphaned remote objects stay.** Remote objects already orphaned in a tier remain there. Their mapping to keys was in the deleted metadata, so cleaning them up is manual.
- **Tiered keys are not purged.** See [Tiered keys](#tiered).
- **A delete-all waits for every drive.** While a drive of the key's erasure set is offline, cannot read the key, or holds an `xl.meta` of the key that does not decode, the purge refuses the key with `history_unavailable` and the scanner tries again on a later pass. Callers still see a write quorum error (`503`). This is the price of checking every revision before deleting any.
- **CRC damage requires successful heal before purge.** `SILO Server 20261109` classifies an `xl.meta` checksum failure as storage corruption, including across the storage RPC error conversion. When an undecodable drive refuses the drive check or when half of the drives cannot be decoded during the history read ([`7a13780d8`](https://github.com/pgsty/silo/commit/7a13780d8)), the refused purge queues MRF heal for each version observed on the decodable drives, using the explicit `null` ID for the null version. Normal and deep object heal can rebuild the corrupt metadata from sufficient surviving copies; a later purge then retries. Dry run leaves the metadata untouched. Without metadata quorum, heal keeps the existing files and the purge remains refused. Other undecodable metadata errors are not promised the same repair path.
- **A drive handle names a drive, not a backend.** The purge deletes on the drive handles it checked, but each storage call resolves the backend again on the node that serves the drive. A backend that replaces a drive while a purge runs starts empty, and it receives the key only from a write or a heal of the key, which take the object lock the purge holds. An admin heal started with `nolock` skips that lock; that option is a separate issue.
- **Keys under an object key are not listed.** A listing does not descend into the directory of an object key, so while `K` exists, `K/child` is missing from listings, from batch expiration walks, and from the walks of decommission and rebalance. This is older than the fix. With the fix, `K/child` survives a delete-all of `K` that a decommission or rebalance runs, but the walk has already passed it. The first pass reports it as left behind, as it does without any lifecycle rule (executed); a later pass moves it.
- **Data directories are removed recursively.** Every version delete, not only delete-all, moves the version's data directory to the trash with its contents. A key named `K/<data-dir>/...`, where `<data-dir>` is the internal data-directory ID of a version of `K`, is removed with that version. The ID is not returned by the S3 API, so such a name needs internal metadata to construct. It is a separate storage-layer follow-up.
- **Legacy-format objects are not covered.** On drives from the oldest erasure format, objects still stored as `xl.json` are deleted recursively by every version delete, not only by delete-all. We reasoned this from the code and did not probe it.
- **The batch recheck is narrow.** Batch expiration can only confirm that the latest version is still the one it matched.
- **Mixed versions.** See [Cost and compatibility](#cost): an old node that runs an expiry still deletes recursively.

## Operator guidance for releases before 20261109 {#operators}

**Find exposure.**

- Lifecycle: run `mc ilm rule export ALIAS/BUCKET` and look for enabled rules that contain `"ExpiredObjectAllVersions": true` or `DelMarkerExpiration`.
- Batch expiration: run `mc batch list ALIAS --type expire` and `mc batch describe ALIAS JOB-ID`. Look for rules with no `purge.retainVersions` or with `retainVersions: 0`.
- Keys: in those buckets (or under the rule's prefix), list the keys including versions and delete markers, then print each key that is a path prefix of another key:

  ```sh
  mc ls --recursive --versions --json ALIAS/BUCKET | jq -r '.key' | sort -u > keys.txt
  awk 'NR == FNR { k[$0]; next }
       { n = split($0, p, "/"); a = p[1]
         for (i = 2; i <= n; i++) { if (a in k) print a " -> " $0; a = a "/" p[i] } }' keys.txt keys.txt
  ```

  A line `a -> a/b` means that a delete-all of `a` also removes `a/b`. A right side that ends in `/` is a directory object, which is not at risk.

**Mitigate until every node runs `SILO Server 20261109` or later.**

- Disable the affected rules with `mc ilm rule edit --id RULE-ID --disable ALIAS/BUCKET`, or remove the element from the rule.
- Where the policy is still needed, use per-version rules:
  - in versioned buckets, `Expiration` `Days` together with `NoncurrentVersionExpiration` `NoncurrentDays` and `ExpiredObjectDeleteMarker`;
  - in unversioned buckets, `Expiration` `Days` alone.

  These delete by version and do not take the recursive path (reasoned from code). They take longer to remove everything. On multi-pool deployments before `SILO Server 20261109`, they remain exposed to [#278](/blog/design/multi-pool-lifecycle-expiry/) until every node upgrades to `20261109`.
- A prefix or tag filter helps only if it excludes the parent keys. A filter that still selects `a` still removes `a/b`, because the children do not need to match.
- Do not run batch expiration jobs with the default purge on buckets that have such keys, and cancel running ones with `mc batch cancel`. `retainVersions` of 1 or more deletes by version (reasoned), but keeps that many versions.

**Detect past losses.**

- With audit logging, look for entries with API name `ILMExpiry` and tag `ilm-action` set to `DeleteAllVersionsAction` or `DelMarkerDeleteAllVersionsAction`. Bucket notifications `s3:ObjectRemoved:DeleteAllVersions` and `s3:LifecycleDelMarkerExpiration:Delete` carry the same information. Each one names only the parent key and the rule. There is no audit entry, notification, or trace for the keys removed with it.
- For batch expiration, the job status and the batch trace count and list only the keys the rules matched.
- For each parent key `K` found this way, compare the keys under `K/` before the event with what exists now. Earlier listings can come from an inventory, a backup, the application's own records, or a replication target. A key that is missing and has no delete record of its own was most likely removed by this defect.
- Delete-all is not replicated, so bucket replication targets may still hold those keys, unless the target runs the same rule. Site replication peers share the lifecycle configuration and apply it themselves, so they may have lost the same keys (reasoned).

## Verification {#verification}

**The fix, executed.** Focused `go test -run` selections with `-p 2`, on the fix and on a disposable worktree at [9f7b49369](https://github.com/pgsty/silo/commit/9f7b49369) with only the new tests added. Each regression below fails on that base and passes with the fix. The new tests pass with the race detector.

- Children in the key's own erasure set, in the other set, and deeper under the key keep all their versions after a lifecycle delete-all, for `ExpiredObjectAllVersions` and for `DelMarkerExpiration`. The same holds for a child in another pool, with copies of the key in both pools, and for a batch expiration purge, whose counts come from the purge.
- Decommission and rebalance remove the due key and keep its new child.
- A key named `ea/dir__XLDIR__/odd` inside the directory of the directory object `ea/dir/` survives the purge of `ea/dir/`.
- A version written after the scanner's decision survives on a single pool. A batch purge whose matched version is no longer the latest deletes nothing and counts nothing.
- On a single pool, an expiry on a history that half of the drives cannot read deletes nothing.
- A `null` version written in two pools whose newer write cannot be deleted is audited as partial with no version removed, since a copy is gone.
- A batch purge that removes the older version but fails on the latest delete marker counts the marker as failed, and the job as failed.
- Two pools, three versions: when the delete of the middle version fails, the oldest is removed, the latest stays and is still what reads return, the audit trace is marked partial with one version removed, and no removal notification is sent. Once the fault is gone, the next expiry completes and sends one notification for two versions.
- A budget of two versions stops a four-version purge before the latest version, reports partial progress, and the next expiry completes it.
- Keys with a tiered older version under a hot latest version, and keys with a tiered latest version in a batch purge, are refused with every version and remote object kept; batch expiration counts them as refused in `keysRefused` (`complete-with-skips`).
- A write protected by retention or legal hold refuses the whole key, including a protected older `null` write in another pool.
- A transitioned revision, or a revision under legal hold, on one drive of sixteen refuses the whole key, although the accepted revision is neither. So does a legal-hold revision on a drive that cannot be read, and one unreadable drive with no protection.
- A drive handle that replaces a checked one after the check receives no delete.
- A budget of 10 ms with slow metadata reads stops the purge before its first delete.
- A `null` version written in two pools: when the newer write cannot be deleted, the older write is gone and reads still return the newer one. The two copies of one version in two pools count as one removed version.
- A free version left by an earlier delete of a tiered version stays.
- The option is rejected together with every conflicting option, and by the layers below the pools layer. An absent key is a success that removes nothing.
- Controls that pass on both: a delete-all of a key without children removes every version; `ea/plainx` and `ea/plain-1` survive; the directory object `ea/dir/` is removed and `ea/dir/kid` stays; force delete still removes the prefix; a transitioned latest version still gets a delete marker; on two pools a stale decision is still refused.
- The existing lifecycle, expiry, batch, ILM, delete, decommission, and rebalance tests in `./cmd`, and `./internal/bucket/lifecycle`, pass with the fix.

**The defect, executed.** These runs used a disposable worktree at main `69fcf50cd` and focused `go test -run` selections with `-p 2`, without the race detector.

- **Direct call.** `DeleteObject` with the scanner's options for a delete-all of `eav-parent` deletes `eav-parent/child` and keeps `eav-parentx`.
- **Scanner and expiry worker.**
  - Lifecycle applied through `scannerItem.applyActions` and the real expiry worker gives the results in the [table above](#trigger): one pool with two erasure sets, `DelMarkerExpiration`, an unversioned bucket, and a directory object.
  - The drive scanner's own folder walk (`NSScanner`) queues the delete-all for the parent, and the worker then deletes its children.
- **Other callers.**
  - Two pools: a child in the second pool is deleted.
  - A batch expiration job started through `BatchJobExpire.Start` deletes the child of the key its rule names.
  - Decommission and rebalance remove both the due key and its new child from both pools.
- **Side effects.**
  - Tiered versions of the key and of its child leave their remote objects behind, with no metadata and no free version. A free version left by an earlier delete is wiped as well.
  - A version written after the scanner's decision is deleted on one pool. Calling the set-level delete directly with `Expire` and `DeletePrefixObject` refuses it.
  - The ILM trace shows one expiry entry, for the parent only.
  - The object layer accepts `ea/dir__XLDIR__/odd`, and it is deleted with the directory object `ea/dir/`.
  - Saving two configuration records, one under the other's path, and deleting the outer one also deletes the inner one.
- **Transitioned latest version.** A delete-all writes a delete marker, keeps both versions and the remote object, and the next scan queues nothing.
- **Option D.** The set-level prefix delete with the restored options deletes a child in the key's own set and keeps a child in the other set.
- **Option B prototype.** Deleting the key's versions by ID through the existing bulk path keeps all children and leaves a free version for the tiered version.
- **The #278 integration branch.** The single-pool, two-pool, migration, and single-pool stale-decision probes lose the same keys. The two-pool stale decision is refused there.

**Reasoned from code, not executed:**

- that the audit entry and the notification of the defective path are written only for the parent; they share the call site that produced the single trace entry;
- that GET, HEAD, and listings queue delete-all through the same worker;
- that the fan-out across erasure sets discards their errors;
- that older nodes skip unknown `DeleteOptions` fields;
- that per-version lifecycle rules and batch purges with `retainVersions` of 1 or more do not reach the recursive path;
- that replication targets keep the removed keys;
- the incomplete-metadata variant found in the #278 review;
- the legacy `xl.json` behavior;
- the immediate trash purge.

**Not run in the isolated worktree check:**

- a mixed-version rolling upgrade across separate hosts.

**Integration and release verification.** The fix was integrated for `SILO Server 20261109` on top of #278 and #281 together with the single-pool lock-domain, heal dry-run, #259, #285, and Console fixes without conflicts. Local integration runs passed the full `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` suite and CI race-detector selections, and an adversarial review of the combined branch checked lock domains, cleanup paths, and purge against restore with executed probes and found no defects. Release commit `d998292387cc` (`RELEASE.2026-11-09T00-00-00Z`) passed Go CI (including the untagged Ubuntu `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m` gate), VulnCheck, Test Release Pipeline, and release build verification.

## Review history {#review}

| Round                 | Outcome                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Design rounds 1 and 2 | Agreed with changes. The bulk path reorders versions and has no barrier between pools, so the purge deletes one version at a time, oldest first, with the latest last and alone. Free versions alone do not make tiered keys safe, so keys with transitioned versions are refused and tiered delete-all is deferred. Placement is recorded for every copy, retention and legal hold are enforced on every write, retries are bounded under the lock, each call has a budget, and reporting counts only confirmed removals. Writer exclusion on a single pool is left to the lock-domain fix, which lands first. The recursive data-directory removal of every version delete is a storage-layer follow-up. |
| Patch review, round 1 | Requested changes. Five findings: a minority drive's transitioned or legal-hold revision was not checked; a purge that removed a copy but no whole version was not audited as partial; the time budget left out the reads and checks; batch job completion ignored failed delete markers (an older predicate that the new counts exposed); a test fixture lacked the delete-marker count. All accepted and fixed with regressions.                                                                                                                                                                                                                                                                         |
| Patch review, round 2 | Requested changes. Three findings: an unreadable drive could hide a protected revision that heal later removes; the drive selection was applied to a fresh set of handles; a purge could start although it already knew it lacked a write quorum. All accepted: an unreadable drive now refuses the key, and the purge deletes on exactly the handles it checked.                                                                                                                                                                                                                                                                                                                                          |
| Patch review, round 3 | Requested changes. One finding: a retained handle does not pin the backend on the node that serves the drive. Disputed: a replacement backend starts empty and receives the key only from a write or a heal under the object lock the purge holds, and binding a backend incarnation would need a wire change.                                                                                                                                                                                                                                                                                                                                                                                             |
| Patch review, round 4 | Approved with nits. The reviewer withdrew the round-3 finding. Two nits: describe the selection as drive handles, with the replacement and locking assumptions, and name the admin heal `nolock` option as the exception. Both applied, in the code comment and under [Residual limits](#limits).                                                                                                                                                                                                                                                                                                                                                                                                          |
{.wide .expand}
## References {#references}

- Evaluated base: [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc)
- Related fix and record: [#278](https://github.com/pgsty/silo/issues/278), [Multi-Pool Lifecycle Expiry](/blog/design/multi-pool-lifecycle-expiry/)
- Migration expiry: [#276](https://github.com/pgsty/silo/pull/276), [ILM Expiry and Pool Migration Ordering](/blog/design/ilm-migration-ordering/)
- Tier cleanup: [Tier Free Versions Are Internal Cleanup Records](/blog/design/tier-free-version-semantics/)
- Upstream history: [minio/minio#12504](https://github.com/minio/minio/pull/12504), [minio/minio#17521](https://github.com/minio/minio/pull/17521), [minio/minio#17827](https://github.com/minio/minio/pull/17827), [minio/minio#17946](https://github.com/minio/minio/pull/17946), [minio/minio#19359](https://github.com/minio/minio/pull/19359), [minio/minio#19365](https://github.com/minio/minio/pull/19365), [minio/minio#19481](https://github.com/minio/minio/pull/19481)
- Operations: [Object Lifecycle Management](/administration/object-management/object-lifecycle-management/), [Batch Expiration](/administration/batch-framework-job-expire/), [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/), [`mc ilm rule edit`](/reference/minio-mc/mc-ilm-rule-edit/), [`mc ilm rule export`](/reference/minio-mc/mc-ilm-rule-export/)
