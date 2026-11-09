---
title: "Lock Domains of Large Single-Pool Clusters"
linkTitle: "Single-Pool Lock Domains"
date: 2026-11-04
lastmod: 2026-11-09
author: "PGSTY SILO Maintainers"
summary: >
  Why DELETE and CopyObject can fail to exclude PUT on the same key in a distributed single-pool deployment whose erasure sets do not share the same hosts, which layouts that covers, what the race does to xl.meta, and the smallest routing change that closes it.
tags: [Design, Locking, Storage, Operations]
weight: 10
draft: false
url: "/blog/design/single-pool-lock-domains/"
---

This record covers a lock-domain defect found during review of the restored-copy fix ([Restored Copies: Expire the Copy, Not the Object](/blog/design/restored-copy-expiry/)), evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). No issue has been filed yet.

**Status:** fix approved by review and committed locally. Tested together with the other fixes for the next release on one integration branch: the full local suite with the `kqueue,dev` tags, the CI race selections run locally and an adversarial review of how the fixes interact all pass. Not merged or released.

## Short answer {#tldr}

The split is real, it is inherited from upstream MinIO, and it only exists when the erasure sets of a pool do not all use the same hosts. With the automatic layout that means a single pool of 18 or more hosts; up to 17 hosts every set contains every host and the lock groups are identical.

In such a pool the object lock of `DELETE`, bulk delete, `CopyObject`, and the upload-ID guards is taken from the lockers of the first erasure set. `PUT`, multipart completion, tag/retention/legal-hold/metadata updates, restore, transition and heal take it from the lockers of the set the key hashes to. For keys that hash to a set whose hosts differ from the first set's, the two locks never meet, so the operations are not mutually exclusive. `xlStorage` has no per-key serialization of its own: `RenameData`, `DeleteVersion`, `UpdateMetadata` and `WriteMetadata` all read `xl.meta`, modify it in memory, and write it back.

A probe that gives each set its own lock table races `PUT` against `DELETE` and against a metadata-only `CopyObject` on one key, 2100 iterations with shared tables and 2100 with split tables. With shared tables nothing goes wrong. With split tables:

- acknowledged versions or delete markers are missing from some drives of the set in a majority of iterations of a deliberately tight race;
- acknowledged `PUT`s end up on fewer drives than the read quorum, or on none;
- an unversioned object is left present on 1 to 5 of 16 drives;
- a metadata-only copy writes back the old body or leaves the object unreadable after both calls returned success.

Routing the single-pool `DELETE` and `CopyObject` lock to the hashed set removes every anomaly in the same probe. The fix does that for every single-pool object lock that used the first set: `DELETE` in all its forms, bulk delete (one lock per set, with the sets deleted concurrently), the COPY destination, `SelectObjectContent`, batch key rotation and the upload-ID guards. The COPY handler checks the source name first and then takes its source and destination locks together, before it reads the source. It needs no wire change, but it protects a pool only once every node runs it, so affected pools need a drained restart instead of a rolling upgrade ([Rolling upgrade](#upgrade)).

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | Lock-domain inconsistency between the pool layer and the set layer. Inherited from upstream MinIO since `RELEASE.2024-10-02T17-50-41Z`; not a SILO regression. SILO added a feature that depends on the lock (If-Match DELETE) and removed a caveat comment, but never changed the routing. |
| Affected deployments | Distributed, single pool, automatic or explicit layouts where some set uses a different host group than set 0. With `http://host{1...N}/disk{1...D}` that is N of 18 or more, for every D. Smaller clusters are affected only with a set size below the host count (`MINIO_ERASURE_SET_DRIVE_COUNT`, or hand-ordered argument lists). |
| Not affected | Single-node deployments (one in-process lock table shared by all sets). Multi-pool deployments, where the write paths also take the pool-level lock. Pools of up to 17 hosts with automatic layout. |
| Affected operations | `DELETE` against `PUT`, `CopyObject`, tag, retention, legal-hold and metadata updates, restore, transition, heal, replication writes; ILM expiry against an overwrite; If-Match `DELETE` against any writer; bulk delete; the upload-ID guards of complete, abort and list-parts against `PutObjectPart`. |
| Severity | High impact, narrow reach. A concurrent same-key race can lose an acknowledged write or delete marker, leave an object on a minority of drives, or make a successful metadata copy roll the data back. No effect on other keys, and no cross-tenant exposure. |
| Reachability | The race needs two writers on one key within the commit window of a few milliseconds. Ordinary S3 clients rarely do that, but ILM expiry against a fresh overwrite, replication, retry storms, and clients that overwrite and delete the same key (queues, locks, temp files) can. It is easily reproduced when forced and rare in normal traffic. In an 18-host cluster about half of all keys (those whose set uses a different host group from set 0) are exposed. |
| Release urgency | Planned fix in the next release rather than a hotfix. The change is local to the pool layer and the COPY handler; affected pools upgrade with a drained restart ([Rolling upgrade](#upgrade)). |
| Remaining effort | The fix and its tests are written. Remaining: remote CI and an acceptance run on a distributed pool. |
{.wide .expand}

## How the groups are built {#groups}

Each erasure set gets its own list of lockers: one locker per distinct host among the set's endpoints (`newErasureSets`). A distributed lock needs a strict majority of that list, and a host's lock server grants a resource name to one holder at a time. Two requests for the same key exclude each other only if they ask the same hosts. If the two lists are identical, they do. If they are disjoint, each side gets its own majority and both are granted. If they overlap partially, both can still be granted whenever the two quorums fit in the union, `qA + qB <= |A ∪ B|`.

The endpoints are expanded with the left-most ellipsis varying fastest, so in `http://host{1...N}/disk{1...D}` the host of endpoint `i` is `i mod N`. Sets are consecutive slices of `S` endpoints, and `S` is the largest divisor of `N*D` that is at most 16 and leaves the fewest sets. Checked by running the real `GetAllSets`:

| Layout | Set size S | Lock groups |
| --- | --- | --- |
| N = 2 to 17, any D from 1 to 32 | S >= N | Every set holds every host. Identical groups. |
| N = 18, D any | 9 | Set 0: hosts 1-9. Set 1: hosts 10-18. Disjoint. |
| N = 20 | 10 | Two disjoint halves, alternating across sets. |
| N = 24 | 12 | Two disjoint halves. |
| N = 32 | 16 | Hosts 1-16 and 17-32, alternating. Half of the keys are exposed. |
| N = 21 | 7 | Three disjoint thirds. |
| N = 25 | 5 | Five disjoint groups. Four fifths of the keys are exposed. |
| Single node, any D | any | One lock table for all sets. |
{.wide .expand}

The sweep covered N = 2 to 64 and D up to 32 for N up to 17, D in {1, 2, 3, 4, 6, 8, 12, 16} above. Every valid layout with N of 18 or more had differing groups, and in every one of them both quorums can be granted at the same time. The same holds for any smaller N when the set size is forced below N. Configuration-file layouts round-robin the disks across nodes in the same way.

## Operation table {#table}

Single pool, main at 69fcf50cd. "Set 0" is `erasureServerPools.NewNSLock` (`serverPools[0].sets[0]`); "hashed set" is `erasureObjects.NewNSLock` of `getHashedSet(object)`.

| Operation | Lock taken | Domain |
| --- | --- | --- |
| `PutObject` (z returns `serverPools[0].PutObject` before any pool lock; `putObject` locks at the set) | `er.NewNSLock` | hashed set |
| Conditional or replica-reconciling `PutObject` | `er.NewNSLock` | hashed set |
| `CompleteMultipartUpload`, object commit | `er.NewNSLock(object)` | hashed set |
| `CompleteMultipartUpload`, upload-ID guard | `z.NewNSLock(object/uploadID)` | set 0 |
| `AbortMultipartUpload`, `GetMultipartInfo`, `ListObjectParts` guards | `z.NewNSLock(object/uploadID)` | set 0 |
| `PutObjectPart` (part lock, upload-ID read lock) | `er.NewNSLock` | hashed set |
| `DeleteObject` (pool layer always locks; the set layer does not) | `z.NewNSLock` | set 0 |
| `DeleteObjects`, bulk (one lock over all names) | `z.NewNSLock` | set 0 |
| `CopyObject`, metadata-only and rewrite (the pool lock covers the fallback `PutObject` with `NoLock`) | `z.NewNSLock` | set 0 |
| `PutObjectTags`, `PutObjectMetadata` (retention, legal hold), `DeleteObjectTags` | `er.NewNSLock` | hashed set |
| `RestoreTransitionedObject`, `TransitionObject` | `er.NewNSLock` (restore reuses `PutObject`, parts, `CompleteMultipartUpload`, `CopyObject` with locks) | hashed set |
| Heal (`healObjectInPool` takes the pool lock only when `!SinglePool()`) | `er.NewNSLock` | hashed set |
| Replication write on the target (`PutObject`, metadata, copy) | as the operation above; plus `/[replicate]/<key>` via `objectAPI.NewNSLock` | hashed set; set 0 for the serializer |
| Replicated `DELETE` | `z.NewNSLock` | set 0 |
| ILM expiry (including the exact-key delete-all; `DeleteObject` with `Expiration`; the rule is re-evaluated under the lock) | `z.NewNSLock` | set 0 |
| Batch key rotation (`NewNSLock`, then `CopyObject` with `NoLock`) | `z.NewNSLock` | set 0 |
| `SelectObjectContent` (read lock) | `z.NewNSLock` | set 0 |
| `GetObject`, `HeadObject` | `er.NewNSLock` read | hashed set |
| Listing recovery (`listingRLock`, SILO) | set 0, then the source set | both |
{.wide .expand}

In a multi-pool deployment `PutObject`, `CompleteMultipartUpload`, tag and metadata updates, transition, restore and heal also take the pool lock and pass `NoLock` down, so every write shares set 0 with `DELETE`. The split exists because the single-pool shortcut `if z.SinglePool() { return z.serverPools[0].X }` skips the pool lock for the writers but not for `DELETE` and `CopyObject`.

## Root cause {#root-cause}

Two choices meet.

1. **The pool layer locks `DELETE` and `CopyObject` itself and always through the first set.** `erasureServerPools.NewNSLock` returns `serverPools[0].NewNSLock`, `erasureSets.NewNSLock` returns `sets[0].NewNSLock`. This is correct when every write also takes a pool-layer lock, which is what multi-pool does. `erasureObjects.DeleteObject` takes no lock of its own.
2. **The single-pool writers skip the pool lock and use the lock of the set they hash to.** The lockers of that set are built from the hosts of its own endpoints.

When both lock groups are the same host list, the two choices describe one domain. When they are not, `DELETE` and `PUT` on the same key hold locks that do not meet.

`xlStorage` does not repair this. `RenameData` reads the destination `xl.meta`, adds the version, writes the result to the staging path and renames it. `DeleteVersion` reads, removes the version, moves the data directory to the trash and writes back or deletes. `UpdateMetadata` and `WriteMetadata` read, modify and write. Nothing serializes two of them on one key and one drive except the namespace lock held by the caller. The higher layers add their own check-then-act steps: `DeleteObject` decides between marker and purge from an unlocked read, the dangling-object cleanup can purge a version that looks incomplete mid-commit, and the metadata-only `CopyObject` writes a snapshot of the `FileInfo` it read earlier.

## Where the behavior came from {#history}

**Upstream origin, in several steps.** All commits below are ancestors of the last upstream master [7aac2a2c5](https://github.com/pgsty/silo/commit/7aac2a2c5), and upstream master has the same code today.

| Ingredient | Commit | Date | First upstream release |
| --- | --- | --- | --- |
| Per-set locker groups | [e9b2bf00a](https://github.com/pgsty/silo/commit/e9b2bf00ad0d538c8bff729473b6fea7b83a1b59), [minio/minio#8492](https://github.com/minio/minio/pull/8492) | 2019-11-13 | `RELEASE.2019-12-17T23-16-33Z` |
| One locker per host and per set | [4550ac6ff](https://github.com/pgsty/silo/commit/4550ac6fff35d2acbb1497c8b47ec450fc870ea7), [minio/minio#11052](https://github.com/minio/minio/pull/11052) | 2020-12-10 | `RELEASE.2020-12-12T08-39-07Z` |
| Bulk delete locks through `getHashedSet("")` (a bulk-versus-single split begins) | [ab7d3cd50](https://github.com/pgsty/silo/commit/ab7d3cd5083e82b0acdd66e277962970c07c8fe5), [minio/minio#8974](https://github.com/minio/minio/pull/8974) | 2020-02-21 | `RELEASE.2020-02-27T00-23-05Z` |
| `CopyObject` takes the pool lock | [200caab82](https://github.com/pgsty/silo/commit/200caab82b622a0ec6c9776ee9b555aedbc9b320), [minio/minio#13280](https://github.com/minio/minio/pull/13280) | 2021-09-22 | `RELEASE.2021-09-23T04-46-24Z` |
| `DeleteObject` lock moved from the set to the pool layer | [d350b666f](https://github.com/pgsty/silo/commit/d350b666ff41df7369a530c177ab8c890474a619), [minio/minio#15521](https://github.com/minio/minio/pull/15521) | 2022-08-18 | `RELEASE.2022-08-22T23-53-06Z` |
| Pool lock always on pool 0 | [6c746843a](https://github.com/pgsty/silo/commit/6c746843ac0c1b273329ae400ce823f491d71390), [minio/minio#20356](https://github.com/minio/minio/pull/20356) | 2024-08-30 | `RELEASE.2024-09-09T16-59-28Z` |
| **Set lock always on set 0: creates the single-key split** | [afea40cc0](https://github.com/pgsty/silo/commit/afea40cc0fe1d823359ecbd229a0425021eb897b) | 2024-09-27 | `RELEASE.2024-10-02T17-50-41Z` |
{.wide .expand}

Until `RELEASE.2024-09-13T20-26-02Z`, `erasureSets.NewNSLock` with one name returned `getHashedSet(objects[0]).NewNSLock`. The pool lock of a single pool therefore landed in the hashed set, the same domain as `PutObject`, and the single-key `DELETE` and `CopyObject` were consistent. Only multi-name locks (bulk delete) used a different set, `getHashedSet("")`. [afea40cc0](https://github.com/pgsty/silo/commit/afea40cc0fe1d823359ecbd229a0425021eb897b) (Harshavardhana, 2024-09-27) replaced that with `sets[0]` so that multi-object deletion competes with locks granted to other callers. That is right when every writer takes a pool-layer lock, which holds for multi-pool, and wrong for a single pool where the writers lock at the set. The commit subject carries "(#93)", which is not a number in the public minio/minio repository, so there is no upstream pull request to link.

**First affected releases.** Upstream: `RELEASE.2024-10-02T17-50-41Z` for single-key `DELETE` and `CopyObject`; earlier for bulk delete only. SILO: [afea40cc0](https://github.com/pgsty/silo/commit/afea40cc0fe1d823359ecbd229a0425021eb897b) and [d350b666f](https://github.com/pgsty/silo/commit/d350b666ff41df7369a530c177ab8c890474a619) are ancestors of `RELEASE.2025-12-03T12-00-00Z`, the first SILO release, and of every release through `RELEASE.2026-10-26T00-00-00Z`. Every SILO release carries the split.

**SILO commits that changed the risk.**

| Commit | Date | First SILO release | Effect |
| --- | --- | --- | --- |
| [40bee4b7b](https://github.com/pgsty/silo/commit/40bee4b7ba756567b16117c70a4c28311e220d6c) If-Match `DELETE` (issue #10, PR #145) | 2026-09-06 | `RELEASE.2026-09-16T00-00-00Z` | Widened. The conditional check and the delete now rely on the pool lock being atomic with writers. The commit documents the limit ("a single erasure set (the default deployment)") but in a split cluster a writer can replace the object between check and delete, so a stale If-Match can still delete the newer object. |
| [7a060cab1](https://github.com/pgsty/silo/commit/7a060cab1edd5bbc17da7f703bbd1ab7415b6f7c) access-based ILM | 2026-08-15 | in `RELEASE.2026-09-16T00-00-00Z`, together with its revert [9b76a2167](https://github.com/pgsty/silo/commit/9b76a2167) (2026-09-15) | No effect on the split. Its rollback code states the split in plain words ("the top-level namespace lock is taken on pool 0 / set 0 ... a client PutObject locks the hashed set ... lockers are per set"), so the maintainers knew by August. |
| [e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938ed25c1bcd51efbb4ad6955073d195f7) multi-pool serialization (PR #178) | 2026-09-11 | `RELEASE.2026-09-16T00-00-00Z` | Did not change a single-pool lock domain. It added pool locks to multi-pool writers and removed the comment in `DeleteObject` that said the lock was shared with the write path "only within one set". The caveat is gone; the behavior it described is unchanged. |
| [87c1c6b3d](https://github.com/pgsty/silo/commit/87c1c6b3dc189799912f748572364e319676a7fc) listing recovery (issue #218, PR #239) | 2026-10-17 | `RELEASE.2026-10-18T00-00-00Z` | Narrowed, for one reader only. Listing recovery takes the set 0 and source-set read locks in fixed order to cover both domains. |
| `d2eb0ade9`, `cd1f6cec3`, `dcc2f20ba` | 2026-10-25 and 26 | `RELEASE.2026-10-25T00-00-00Z` (first two), `RELEASE.2026-10-26T00-00-00Z` | Moved where `PutObject` takes its set lock and back. No change of domain. |
| `1748f62c7`, `60c7179dd`, `7ce7fc8d1`, `5e7d60308` | 2026-09 and 10 | `RELEASE.2026-10-18`, `RELEASE.2026-10-18`, unreleased (2026-10-29), `RELEASE.2026-09-16` | Multi-pool and data-movement paths only. No change for a single pool. |
{.wide .expand}

The public design record [Restored Copy Expiry](/blog/design/restored-copy-expiry/) already lists "Lock domains in large single-pool deployments" as inherited and out of scope, and [Listing Recovery Lock Cost](/blog/design/listing-recovery-lock-cost/) describes the listing workaround.

**In short.** SILO did not introduce the defect. The commit that created the single-key split is the upstream [afea40cc0](https://github.com/pgsty/silo/commit/afea40cc0fe1d823359ecbd229a0425021eb897b) of 2024-09-27, first released in `RELEASE.2024-10-02T17-50-41Z`. SILO inherited it in `RELEASE.2025-12-03T12-00-00Z`, built a feature on top of it ([40bee4b7b](https://github.com/pgsty/silo/commit/40bee4b7ba756567b16117c70a4c28311e220d6c)), kept the caveat in a comment until [e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938ed25c1bcd51efbb4ad6955073d195f7), and has since worked around it only in listing recovery.

## Probe results {#probe}

The probe runs in a disposable worktree on main. It builds one pool of 32 local drives as two sets of 16 and picks keys that hash to set 1. `DELETE` and `CopyObject` then lock through set 0 and `PUT` locks through set 1. With the production-local setup both sets share one lock table; this models a distributed cluster whose sets share their hosts. The split setup gives each set its own table, the technique of the existing `TestNativeRestoreConcurrentCompletion`; it models fully disjoint lock groups. Each iteration seeds the key, starts `PUT` and the other operation behind a barrier with a random delay of up to 2 ms (a second run: up to 20 ms) on the second one, and reads `xl.meta` from every drive straight after both calls return. The machine was busy (load average 32), `-p 2`. Absolute rates are not production rates.

Window up to 2 ms, 300 iterations per row:

| Race | Shared lock table | Split lock tables |
| --- | --- | --- |
| Versioned `PUT` against `DELETE` | 0 anomalies | 188 iterations with an acknowledged version or marker missing on some drive; 70 with the acknowledged `PUT` on fewer drives than the read quorum (8 of 16); 127 `DELETE` calls failed with "not found" for a key that existed |
| Unversioned `PUT` against `DELETE` | 0 | 84 iterations ended with `xl.meta` on some but not all of the 16 drives (for example 1, 3, 4 or 5 drives) instead of all or none; 94 `DELETE` errors |
| Unversioned `PUT` against metadata-only `CopyObject` | 0 | 30 iterations read back the old body after both calls succeeded; 155 read "not found"; 48 copy errors |
{.wide .expand}

Window up to 20 ms, 400 iterations per row: the split rows fall to 34 iterations with a missing item, 10 with a mixed drive state, and 3 stale bodies plus 24 unreadable objects, and the shared rows stay at zero. The race is real but sensitive to timing, as expected.

Typical per-drive state after a versioned race with split tables, 16 drives: 11 drives hold the seed, the new version and the marker; 3 drives hold only the seed and the marker (the new version lost); 2 drives hold only the seed and the new version (the marker lost). In another iteration the `PUT` was acknowledged and its version was present on none of the 16 drives while `DELETE` returned "not found". That last path is not traced to a line; it is consistent with the delete path reading the object mid-commit and purging what it took for a dangling version.

With a probe-only change that routes `DELETE` and `CopyObject` to the hashed set (single pool), the same three races over 300 iterations each, shared and split, give zero anomalies in every row.

The probe does not use dsync, a network, or partially overlapping groups; it does not test bulk delete, the upload-ID guards, restore, or a mixed-version cluster. The tests of the fix cover all of these except a network and mixed binaries; see [Verification](#verification).

## Options {#options}

### Option 1: route single-pool object locks to the hashed set (chosen) {#option-1}

Lock every single-key object name that the pool layer locked in the first set in the set the object hashes to instead, where its writers lock it, and lock nowhere else. One helper on the pool layer returns that lock (`NewObjectNSLock`): for a single pool the lock of `serverPools[0].getHashedSet(object)`, otherwise `z.NewNSLock` unchanged. It is also on the `ObjectLayer` interface for `SelectObjectContent` and batch key rotation. Upload-ID guards pick the set by their object and keep their lock name `object/uploadID`, as `PutObjectPart` does. Bulk delete takes one lock per set and deletes the sets concurrently, up to 16 at a time; each set's group holds only its own lock. The COPY handler takes its source and destination locks together, before it opens the source. Generic `NewNSLock` keeps one stable domain for names that are not objects.

The number of lock RPCs does not change for single-key operations; a lock asks the hosts of one set instead of the hosts of set 0, which also spreads the load. Multi-pool deployments keep their lock domains, and single pools whose sets share their hosts lock the same hosts as before.

### Option 2: make `NewNSLock` route single names to the hashed set {#option-2}

This restores the pre-afea40cc0 behavior in one place, and fixes every caller at once. Multi-name locks still need a decision (that was why upstream changed it), the multi-pool pool lock would move from set 0 of pool 0 to the hashed set of pool 0, which changes the domain of every multi-pool lock, and composite names such as `object/uploadID` would hash by the whole name instead of by their object. The risk reaches further than the defect. Rejected.

### Option 3: one lock group for every object lock {#option-3}

Use all hosts of the pool, or set 0's hosts, for every object lock, including the set-layer ones. Exclusion would hold, but the group would grow to N hosts for each lock, or concentrate every lock on the hosts of set 0. It also changes the writers, so the mixed-version problem below applies to `PUT`. Rejected.

### Option 4: lock at the set layer for single pool {#option-4}

Make `erasureObjects.DeleteObject` and `CopyObject` take their own lock, as before 2022. The pool layer's check-then-delete logic (marker versus purge, If-Match, ILM re-evaluation) would then run before the lock, so the atomicity those features rely on is lost. Rejected.

### Option 5: document and advise {#option-5}

State that single pools of 18 or more hosts have this limit, and recommend pools of at most 17 hosts with additional pools as the cluster grows. This costs nothing but leaves the defect for the operators who already run such a pool, and they cannot restructure a pool. Rejected as a substitute; the release notes still carry the upgrade procedure below.

### Option 6: take both locks (dual locking) {#option-6}

Keep the set-0 lock of `DELETE`, COPY and the upload guards and add the hashed-set lock, always in that order, so that old and new nodes exclude each other during a rolling upgrade. The adversarial review of the design rejected it, with probes, for two reasons:

- **Overlapping groups block themselves.** When the two lock groups share hosts, as explicit layouts and some automatic ones do, the first lock's quorum can leave too few free hosts for the second lock of the same name. Equivalent groups block outright. Making that safe needs an atomic lock over the union of two groups, which SILO does not have.
- **Bulk delete forms a cycle with multipart completion.** Holding the set-0 lock over all names of a batch while taking the hashed groups cycles with a completion that holds its object lock in the hashed set and waits for its upload guard in set 0, because `parent/uploadID` is also a valid object key that the batch can name. An old-node COPY whose source and destination are both in the batch forms a similar cycle.

## Recommendation {#recommendation}

Adopt option 1 in the next release. This is what the fix implements.

1. **Routing.** In a single pool, these locks move from set 0 to the object's own set:
   - `DeleteObject`, every branch: plain, If-Match, ILM expiry (including the exact-key delete-all), data movement, and the replicated delete;
   - the destination lock of `CopyObject`;
   - the read lock of `SelectObjectContent`;
   - the lock of batch key rotation;
   - the upload-ID guards of `CompleteMultipartUpload`, `AbortMultipartUpload`, `GetMultipartInfo` and `ListObjectParts`.

   Names are normalized as storage stores them (directory objects as `name__XLDIR__`), for routing and for the lock name. Exactly one lock is taken: no set-0 lock is held alongside it. True prefix deletion (force delete) keeps its set-0 lock on the prefix name, which never covered the objects below it. Multi-pool deployments are unchanged. Generic `NewNSLock` stays as it is for bucket `.lck`, bucket `metadata.lock`, IAM revision locks, format and leader coordination, and the `/[replicate]/<key>` serializer.
2. **Bulk delete.** A single pool groups the names of `DeleteObjects` by their set and runs the groups concurrently, up to 16 at a time, as the set deletes of one bulk delete ran before the change. Each group takes its set's lock over all of its names in one multi-name lock request, deletes its sub-batch and releases the lock. A group holds only its own set's lock and waits for no other while it holds it, so the groups cannot hold each other. Each group's lock is taken in the request's context, never in a released lock's. A group whose lock cannot be taken fails as a whole, and the other groups still run. A group that starts after the request was canceled fails without doing any storage work. Results keep their positions, and validation errors, duplicate names, version and replication identity, and the per-key order of purges before markers are as before. Replication, events and ILM auditing stay with the callers, on the merged results. The multi-pool path is unchanged.

   The local lock of a single node takes several names one at a time and holds the earlier names while it waits for the next. A single node, where every set uses one local table, therefore keeps the one bulk lock of today. Any other local table is taken in attempts, each bounded as a whole, that release everything they hold. Distributed locks are granted or refused over the whole list of names.
3. **COPY.** The handler checks the source name before it locks anything, with the check that came first before the change, and locks the destination only when its name is valid; an invalid destination still fails at the copy's own destination check, after a missing source (404) or a failed source precondition (412). It computes its locks before it opens the source: a read lock on the source in its set, and a write lock on a local destination in its set. Requests are merged by the resource the lockers see, the cleaned bucket and object name, within one lock table, so a copy onto itself takes one write lock. The locks are taken transactionally: in one order, by lock domain and then by bucket and object; each lock after the first with a bounded wait. When that bounded wait times out while earlier locks are held, the copy releases them in reverse order, waits for that lock alone with a fresh instance until the deadline, releases it once it is free, and starts again from the first lock. Any other failed attempt releases every lock held in reverse order. Each new attempt follows a short random pause and uses new lock instances and a fresh context; one deadline covers all attempts. New instances matter because a lock instance names its holder and a distributed unlock is retried in the background: a late retry of an earlier attempt's unlock must not release the next attempt's lock. The source is then read under these locks, preconditions and inline data included. The destination lookups of Object Lock retention and of the tier sweeper, and the inner `CopyObject` and `PutObject`, run without taking the locks again. Everything under the locks runs in their context, so losing either lease aborts the copy, its lookups included. The locks are released once the copy is written, before a synchronous replication reads the destination.
4. **`listingRLock`** keeps its two read locks, set 0 and then the source set, with their bounded waits and cleanup. After this change the source set is where every single-pool writer locks; the set-0 lock remains while nodes of earlier releases may run, and can be dropped only behind an enforced version boundary.
5. **Comments.** The caveat that [e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938ed25c1bcd51efbb4ad6955073d195f7) removed from `DeleteObject` is back, rewritten for the new routing and the mixed-version limit. The If-Match paragraph that claimed atomicity only within one erasure set is corrected.
6. **Release notes.** Describe who is affected, the upgrade procedure below, and that adding pools changes the locking regime only for new writes.
{.steps}

### Lock ordering {#ordering}

After the change, every single-pool object lock is in the domain of the object's writers, and there is exactly one per name. The existing nesting stays: the `/[replicate]/<key>` serializer is taken first and an object lock inside it, never the reverse. Single-pool multipart completion takes the upload lock first and the object lock just before it commits, both in the object's set, as on main; with several pools it takes the object lock first and then the upload lock. Native restore no longer goes through multipart completion: it takes its restore lock and then the object lock ([Native Restore in Two Phases](/blog/design/native-restore-two-phase/)). Each group of a bulk delete holds only its own set's lock.

COPY is the only operation that takes the locks of two objects one after the other; a bulk delete asks for each set's names in one multi-name lock request. COPY sorts its locks, so two copies never wait on each other in a cycle, and it waits for its second lock only for a bounded time before releasing the first, so an operation that orders its locks differently, such as a copy on a node of an earlier release, delays it but cannot block it forever. It then waits for the contended lock alone: while a copy waits for a contended source, it holds nothing, and reads and writes of its destination proceed. Before this change, the handler opened the source, which held its read lock, and only then took the destination lock. Wherever both locks were in one domain, two copies in opposite directions between non-inline objects therefore already held each other until the lock timeout: on a single node, in a pool whose sets share their hosts, and with several pools. The tests reproduce that on the base. Moving only the destination lock to its own set would have added the same cycle between keys of different sets; the review reproduced that with a probe. The ordered acquisition removes both.

### Rolling upgrade {#upgrade}

Lock names and the lock RPC do not change; only the hosts a lock asks change. The fix protects a pool only when every node runs it.

- **Who is affected.** Single-pool deployments in which some set uses different hosts from set 0. That is every automatic layout with 18 or more hosts, and explicit layouts with a set size below the host count. For example, `http://host{1...18}/disk{1...4}` chooses a set size of 9 automatically and gives disjoint halves; an explicit set size of 12 gives sets whose host windows partially overlap. Pools whose sets all share their hosts, and multi-pool deployments, lock the same hosts as before and can be upgraded as usual.
- **Mixed versions.** While old and new nodes both serve an affected pool, an old-node `DELETE` or COPY locks in set 0 and a new-node one in the hashed set, so the two no longer exclude each other on the same key, although they did before. An old-node `DELETE` against any `PUT` stays as exposed as today. A new-node COPY and an old-node COPY in opposite directions can also hold each other until the new node's bounded wait releases its first lock; copies between old nodes keep their old behavior.
- **Procedure.** Upgrade affected pools with a drained restart: suspend incoming work; drain or stop in-flight and background operations (replication, ILM, batch jobs, healing); stop every old process before any new process serves; then resume. Roll back the same way. Restarting all nodes together is not enough on its own if old processes still serve while new ones start.
- **Adding pools** changes the locking regime only for the writes that go through the pools lock afterwards. It cannot split an existing pool or repair data already lost.
- **Cost.** A COPY may take more than one acquisition and may retry. A bulk delete takes one lock round trip per set it touches instead of one in total, but the sets run concurrently, up to 16 at a time, as they did before the change.

## Limits {#limits}

- The tests run in one process. They model the lock groups of a distributed pool with independent local tables and with in-process dsync lockers, disjoint and partially overlapping, over shared test drives. They do not run a real cluster of 18 or more hosts or mixed binaries; the mixed-version behavior above follows from the design probes and the code.
- The race probe's rates come from a tight, forced race on a loaded machine. They show that the race is possible and what its outcomes are, not how often it occurs in production.
- The local lock of a single node still takes the names of a bulk delete one at a time, as before. A batch that names an object together with names that alias another operation's lock names, such as `parent/uploadID/1`, can wait for that operation up to the lock timeout. Distributed pools are not affected.
- A COPY whose source stays write-locked waits up to its operation timeout, holding nothing.
- In an affected layout, a `DELETE` on a set that lost its lock quorum now waits for the delete operation timeout (1 to 5 minutes) and answers `503 RequestTimeout`. With the old routing, such a `DELETE` took its lock in set 0 and, while set 0 was healthy, failed at once with `InsufficientWriteQuorum`; but set 0 was then a single point of failure for every `DELETE` and COPY.
- `mcli admin top locks --json` reports the `source` of a COPY or bulk-delete lock as `getNSLocks` in `erasure-server-pool-locks.go`, not the handler that holds it. This is read from the code.
- Native restore no longer passes `CopyObject` a snapshot it read without the lock. It stages its copy without the object lock and checks the version again under the lock when it commits ([Native Restore in Two Phases](/blog/design/native-restore-two-phase/)).
- Existing damage (objects left on a minority of drives) is handled by heal as for any partial write. Heal takes the hashed-set lock, which after the fix is also the lock of `DELETE`.
- The path behind "acknowledged `PUT` on none of the drives" in the probe is consistent with the dangling-object cleanup but not traced.
- We did not measure the load effect of spreading the object locks over the hosts of each set instead of the first set.

## Verification {#verification}

Executed in disposable worktrees on the base of the fix:

- The regression tests split one test pool into two sets that share the drives but lock as distributed sets do, in four modes: one shared local table (as a single node, the control), a local table per set, in-process dsync lockers with no locker in common, and in-process dsync lockers with one of three in common, where each set can grant its quorum alone. One operation is held inside its storage commit and the other must wait. The cases are `PUT` against `DELETE`, an If-Match `DELETE` (which must then fail its condition), bulk `DELETE`, metadata-only and rewriting `CopyObject`; `DELETE` and metadata-only COPY against a tag update; restore against `DELETE` and COPY; `PutObjectPart` against complete and abort, with get-info and list-parts as controls that must not wait; multipart completion against bulk delete, with and without the upload-ID alias in the batch; bulk delete against part-lock aliases; bulk group failure and cancellation; the COPY handler against a `PUT` of its destination, and a copy onto itself, which must read the version that the `PUT` committed; reciprocal copies through the handler; the handler's destination lookups in an Object Lock bucket with a tier configured; `SelectObjectContent`; and batch key rotation. A differential test runs a versioned bulk delete with markers, purges, duplicates, an invalid name, a directory object and absent keys, and compares the grouped results with the single bulk lock.
- On the base, with only these tests applied, every exclusion case fails in the split modes because the second operation runs while the first holds its commit. The copy onto itself also fails with the shared table: it writes the metadata of the version it read before the lock over the new data. The bulk group cases fail because the base takes no lock in the writer's domain. The reciprocal copies fail on the base where both locks share one domain, with one shared table and with two pools: each copy holds its source read lock and waits for the other's, until the request ends. The other controls pass on both trees.
- Unit tests cover the helpers: routing of object and upload locks; the transactional acquisition (partial acquisition released, overall timeout, cancellation, a lost lease that ends the context and is retried with a fresh one, and a late background retry of an unlock whose reply was lost, which must not release the next attempt's lock); the bound of one local attempt over several names; the bounded local group acquisition; and the end of the COPY handler's destination lookup when a lease is lost. Ablations confirm that each of these tests fails without its part of the fix: a lookup that takes the lock again, a group taken in one unbounded acquisition, a lock instance reused across attempts, an attempt bounded per name, and lookups in the request's context.
- One existing test injected a retention or legal-hold change from inside the object layer's `CopyObject`, between the handler's Object Lock check and the write. The handler now makes that check under the destination's write lock, so that window no longer exists, and the injected write waited for the lock its own caller held. The test now injects the change just before the handler takes its locks, the latest point a concurrent writer can reach; its expected refusal and unchanged object stay the same. A new regression covers the window itself: it holds a COPY inside its write and requires a retention or legal-hold update of the destination to wait for the copy and then succeed, for a copy and a copy onto itself, in all four modes and with two pools. On the base the update lands between the check and the write in every topology, and the backend's own recheck then refuses the copy.
- The release review of 2026-11-06 found three regressions of the fix (see [Review history](#review)). Their fixes added these tests, each of which fails without its part of the change:
  - `TestLockDomainCopyRejectsAliasNames`, `TestLockDomainCopyErrorPrecedence` and `TestLockObjectsMergesByResource`: aliased source and destination names are refused with `400` before anything is locked, in every lock layout and with two pools; an invalid destination keeps the `404` and `412` precedence; an alias merges with its clean name, also with an alias of another set in a shared lock table;
  - `TestGetNSLocksWaitsHoldingNothing`, `TestGetNSLocksIdleWaitCancel`, `TestGetNSLocksIdleWaitDeadline` and `TestLockDomainCopyDoesNotStarveDestination`: a lock before the contended one stays free for others during the whole wait, a cancel or the deadline ends the wait with nothing held, and a `HEAD` of a copy's destination succeeds while the copy waits for its source; `TestGetNSLocksNonAtomicKeepsBoundedRetry` is the control;
  - `TestDeleteObjectsInSetsRunsGroupsConcurrently` and `TestDeleteObjectsInSetsQueuedGroupsCancel`: the drive calls of two sets overlap, and after a cancel a queued group makes no drive call while a group in flight keeps its own result.
- `gofmt` and `go vet ./cmd` are clean. The new tests pass under the race detector, and the existing lock, copy, delete, multipart, select, listing, lifecycle, decommission and rebalance tests of `./cmd` pass.

Still to run before merge: remote CI, and an acceptance run on a distributed single pool whose sets use different hosts.

**Integration.** The fix was cherry-picked onto one integration branch for the next release, on top of #278 and #281 and together with the delete-all, heal dry-run, #259, #285 and Console fixes. Every pick applied without conflicts. On that head the full `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` suite passes, as do the CI race-detector selections and a race selection that covers every new test. An adversarial review of the combination found no defects. It checked lock domains, cleanup paths and purge against restore with executed probes.

The passing local runs use the `kqueue,dev` tags. The untagged Ubuntu CI command, `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m`, remains pending on the final commit; the local tagged result does not replace that gate.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Design review, round 1 | Agreed with changes. Upload guards select the set by their object and keep their lock name; normalization as storage; true prefix deletion (force delete) distinguished from exact-key deletes of one object; bulk failure semantics specified. Two blockers: the COPY handler held the source read lock in the hashed set while it took the destination lock in set 0, so moving only the destination created a cycle between copies in opposite directions (reproduced); and "never worse during a rolling upgrade" was false, since old DELETE and COPY had excluded each other in set 0 (reproduced). |
| Design review, round 2 | Dual locking (option 6) proposed to keep old and new nodes exclusive. Rejected with probes: overlapping lock groups block the second lock of the same name, and holding the set-0 bulk lock while taking hashed locks cycles with multipart completion through the `parent/uploadID` alias. COPY must take its locks before opening the source, pass `NoLock` to the source read, and sort its locks. |
| Design review, round 3 | Dual locking dropped; single-domain routing with a drained upgrade agreed. Changes: the local lock backend acquires names one at a time, so a single node keeps its one bulk lock and other local tables use bounded attempts; resources of different sets can still share hosts; `NoLock` through every nested call of COPY, including the destination lookups; one deadline, fresh contexts and lease loss for COPY; a real drain procedure for upgrade and rollback; more tests. Premise corrected: `host{1...18}/disk{1...4}` chooses a set size of 9, and an explicit 12 gives overlapping windows. |
| Adversarial review, patch round 1 | Request changes; four findings, all accepted. Retries reused one lock instance, which names its holder, so a background retry of an unlock whose reply was lost could release the next attempt's lock (reproduced); every attempt now takes new instances. The destination lookups ran in the request's context and outlived a lost lease; the work under the locks now runs in their context. One attempt at a local lock over several names waited up to its bound for each name and overran the deadline; the attempt is now bounded as a whole. A test assumed that a distributed unlock completes at once; it now waits for the release. |
| Adversarial review, patch round 2 | Approved; no new findings. The four fixes were verified, also under the race detector, with further probes and the restore integration tests. Three statements of this record were corrected during the round: COPY is the only operation that takes two objects' locks one after the other (a bulk delete asks for a set's names in one multi-name lock request); the operation that orders its locks differently is a copy on a node of an earlier release, not a part copy; and such a copy holds a new copy only until the new node's bounded wait releases its first lock, not until the lock timeout. |
| Adversarial review, patch round 3 (record only) | Approved with nits. The three corrected statements and the history rows match the code. Nits applied: "one acquisition" became "one multi-name lock request", since the local backend takes several names one at a time; the Status line holds once the fix is committed, which followed this round. |
| Adversarial review, patch round 4 (one existing test) | Approved with nits. Moving the injection point of the adapted retention test before the locks is sound, but it alone would not catch a COPY that released its lock between its check and its write. Applied: a regression in which a retention or legal-hold update must wait for a COPY held inside its write. |
| Release review (2026-11-06) | Found three regressions of the fix: a copy whose source name aliases its destination, such as `a//x` onto `a/x`, locked one resource twice and waited on itself until the operation timeout; a copy waiting for a contended source held its destination write lock most of the time; and a bulk delete ran its set groups one after another. Fixed with the source-name check and the merge by resource, the wait that holds nothing, and concurrent groups. Two implementation-review rounds corrected test gaps: race-free timeouts and lock instances, aliases of another set in a shared lock table, and writers probed before readers. |
{.wide .expand}

## References {#references}

- [afea40cc0](https://github.com/pgsty/silo/commit/afea40cc0fe1d823359ecbd229a0425021eb897b): set lock always on set 0 (upstream, 2024-09-27).
- [d350b666f](https://github.com/pgsty/silo/commit/d350b666ff41df7369a530c177ab8c890474a619) and [minio/minio#15521](https://github.com/minio/minio/pull/15521): `DeleteObject` lock moved to the pool layer.
- [40bee4b7b](https://github.com/pgsty/silo/commit/40bee4b7ba756567b16117c70a4c28311e220d6c), [e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938ed25c1bcd51efbb4ad6955073d195f7), [87c1c6b3d](https://github.com/pgsty/silo/commit/87c1c6b3dc189799912f748572364e319676a7fc): SILO commits that touch the contract.
- [Restored Copy Expiry](/blog/design/restored-copy-expiry/) and [Listing Recovery Lock Cost](/blog/design/listing-recovery-lock-cost/): public records that mention the limit.
