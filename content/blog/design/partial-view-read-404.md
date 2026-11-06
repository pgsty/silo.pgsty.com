---
title: "A Partial View Must Not Report an Existing Object as Missing"
linkTitle: "Partial-View 404"
date: 2026-11-06
lastmod: 2026-11-06
author: "PGSTY SILO Maintainers"
summary: >
  Why a node that reaches only some drives of an erasure set can answer 404 NoSuchKey for an object that exists, and why mapping inconsistent metadata to "not found" only when every drive answered is the minimum complete repair.
tags: [Design, Erasure Coding, Availability, S3 Compatibility]
weight: 10
draft: false
url: "/blog/design/partial-view-read-404/"
---

This record covers a defect found during local acceptance of the next release. It reproduces on the local integration of the next release and on [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). It has no GitHub issue yet.

**Status:** fix approved by an adversarial review (with nits, all adopted) and implemented on a local branch. Not merged or released.

## Short answer {#tldr}

A node that has just restarted, or that has briefly lost its connection to some peers, sees only some drives of an erasure set. If the object's metadata on the drives it can see is split between two revisions, and neither revision reaches read quorum, GET and HEAD answer **404 NoSuchKey** for an object that exists.

No data is lost or deleted. But S3 clients, caches and replication treat 404 as final: a backup tool may record the key as gone, a cache may store the negative answer, and a conditional write may act on a false absence. The right answer from such a view is **503 SlowDownRead**, which clients retry.

The fix changes one file, `cmd/erasure-object.go`, by 37 added and 2 changed lines:

- inconsistent metadata becomes "not found" only when every drive of the set answered;
- when the version merge finds no version in quorum and some drive did not answer, a drive that holds a version reports a read-quorum error instead of "not found".

A key that is absent from every drive that answered still gets 404 when enough drives answered. When every drive answered, the behavior is unchanged. Deletes, copies and maintenance that meet such a view now fail and retry instead of treating the object as absent; [Cost and compatibility](#cost) lists them.

## Classification {#assessment}

| Aspect | Assessment |
|---|---|
| Nature | Wrong error mapping on a degraded read. Inherited from upstream MinIO. |
| Impact | A false 404 for an existing object, until the node reconnects (up to about 16 s after boot) or heal makes the copies consistent. |
| Data safety | No data is deleted. The dangling-object check already refuses to act when a drive did not answer. |
| Severity | S1: a client-visible false absence. Low probability: it needs a partial write and a partial view at the same time. |
| Effort | Small: one file, no storage RPC, no on-disk format, no configuration. |

## When it happens {#trigger}

Two conditions must hold together:

1. **A write committed on a write quorum but not on every drive**, and it changed a field that the metadata quorum compares. Restores, transitions, restored-copy expiry and overwrites of an unversioned object all qualify. A drive that is offline during the write keeps the older revision until heal.
2. **A node reads through a partial view**: it reaches at least half of the drives, but the drives it reaches are split so that no revision has read quorum. With EC 4+4 on 8 drives, a node that sees 4 or 5 drives can hit this.

The acceptance run that found it: 4 nodes with 2 drives each, EC 4+4. Nodes 1 and 2 restarted together. A restore of `t1` through node 1 committed on 6 of 8 drives, because node 2's drives were not yet reachable. Node 2 could reach only its own pair (unrestored) and node 4's pair (restored). GET and HEAD through node 2 answered 404. The same failure appeared with `69fcf50cd`.

## Root cause {#root-cause}

Line numbers are for the local integration of the next release; the code is the same on `69fcf50cd`.

1. A drive that cannot be reached at boot stays empty in the node's erasure set (`cmd/erasure-sets.go:420`). It is reconnected after less than a second and then every 15 seconds (`:287-290`, `:349`).
2. In `getObjectFileInfo`, a drive that does not answer keeps `errDiskOngoingReq` (`cmd/erasure-object.go:792, 820`), which quorum counting ignores (`:57`).
3. The version merge and `objectQuorumFromMeta` accept 4 answers out of 8 (`cmd/erasure-object.go:659-661`, `cmd/erasure-metadata.go:560`).
4. `findFileInfoInQuorum` hashes the transition fields only for a remote version (`cmd/erasure-metadata.go:346`). A restored copy is not remote, so the 2 restored and 2 unrestored copies form two groups of 2, below read quorum 4. It returns `InsufficientReadQuorum{RQInconsistentMeta}` (`:386`).
5. `getObjectFileInfo` converts that error to `errFileNotFound` (`cmd/erasure-object.go:1007-1016`), which the API returns as NoSuchKey.

A second path leads to the same 404 for an unversioned overwrite: when no version reaches merge quorum, `pickLatestQuorumFilesInfo` marks every drive that answered as "not found", including drives that hold the object (`cmd/erasure-object.go:661-668`).

The tier is not involved. A refused tier connection maps to `XMinioBackendDown` (HTTP 400), never to NoSuchKey, and the read fails before it reaches the tier.

### Provenance {#history}

- The `RQInconsistentMeta` → not found conversion comes from upstream [#20522](https://github.com/minio/minio/pull/20522) (`dc86b8d9d`). Its commit message assumes "sufficient responses from all the drives"; the code does not check it.
- Hashing transition fields only for remote versions comes from upstream [#19165](https://github.com/minio/minio/pull/19165) (`c599c11e7`).
- Marking every drive "not found" after a failed merge comes from upstream `d48002271`.

## Options {#options}

### Option A: convert inconsistent metadata to "not found" only when every drive answered

Add the missing precondition. Every slot must hold metadata or a definitive "no such file, version, volume, or corrupt metadata". This fixes the restore and transition splits. 15 added and 2 changed lines.

### Option B: keep a read-quorum error when a failed merge had a partial view

When the merge finds no version and some drive did not answer, a drive that holds a version reports `errErasureReadQuorum` instead of `errFileNotFound`. This fixes the unversioned-overwrite path. 20 added lines.

### Option C: hash the transition fields for every transitioned version

This merges restored and unrestored copies into one group, and then the index order chooses which copy is served. It does not cover the unversioned overwrite, and it changes heal decisions from #19165. Rejected.

### Option D: make `/minio/health/cluster` reflect this node's own view

The cluster check counts drives as each owner node reports them, so it can say "healthy" while this node still cannot reach some peers. Changing that does not remove the 404, which any partial view can trigger, and changes semantics that orchestrators rely on. Rejected for this defect.

### Option E: reconnect drives faster after boot

This only narrows the window. It could be a separate change.

## Proposed fix {#fix}

Options A and B together, in `cmd/erasure-object.go`:

- a helper, `allDrivesAnswered(errs)`, true when every slot is nil or one of `errFileNotFound`, `errFileVersionNotFound`, `errFileCorrupt`, `errVolumeNotFound`. These are conclusive answers from a drive. Corrupt metadata counts as an answer because it is unusable, not because it proves the object never existed. An ongoing request, a missing or faulty drive, an unformatted drive, an access error, a transport error or a cancelled context are not answers;
- in `getObjectFileInfo`, the `RQInconsistentMeta` conversion requires `allDrivesAnswered`;
- in `pickLatestQuorumFilesInfo`, when the merge fails with "not found" and not every drive answered, a drive whose `xl.meta` holds a readable version gets `errErasureReadQuorum`.

## Why it is sufficient and necessary {#sufficiency}

- **Sufficient.** Both paths that turn a partial view into 404 now require every drive to have answered. Without that, the read keeps the quorum error and the API answers 503.
- **Necessary.** Option A alone leaves the unversioned-overwrite 404 (path B). Option B alone leaves the restore and transition 404 (path A). The reproduction test fails with either half missing.
- **Minimal.** It changes no storage RPC, no metadata hash and no health semantics, and the dangling-object purge deletes neither more nor less than before. A key that is really absent, or an object whose drives all answered, keeps its current answer.

## Cost and compatibility {#cost}

- Cost: one pass over the error slice, only on error paths. No extra I/O.
- S3: S3 promises strong read-after-write consistency, so NoSuchKey must mean the key is absent. 503 SlowDown is the transient code that SDKs retry.
- Mixed versions: the change is local to the node serving the request. During a rolling upgrade, old nodes still answer 404 in this state, upgraded nodes answer 503. No coordination is needed.
- Deliberate change: an unversioned object deleted while some drives were offline, read from a view that sees exactly as many stale copies as deleted ones, answers 503 instead of 404 until the node reconnects or heal runs. From that view the two histories cannot be told apart.
- Multi-pool, reasoned from the code: a read-quorum error counts as "the object is in this pool", so a PUT no longer creates a duplicate in another pool while one node has a partial view.
- Other operations that read through such a view now fail with 503 and retry, instead of treating the object as absent:
  - a multi-pool DELETE of an unversioned object whose copies split this way (`deleteObjectFromAllPools`), which before could take the guarded blind-delete path;
  - the source read of CopyObject, and tag or metadata updates;
  - decommission and rebalance, which retry or report the object instead of skipping it as missing.

## Residual limits {#limits}

- A versioned overwrite committed on a write quorum can still be served from the older revision through such a partial view. That is existing upstream behavior and out of scope.
- **A permanently failed drive.** `errDiskNotFound` counts as a drive that did not answer. In a set with a permanently failed drive, an object whose metadata is split with no revision in quorum therefore no longer answers 404:
  - GET and HEAD stay at 503;
  - its DELETE in a versioned or versioning-suspended bucket answers `InsufficientWriteQuorum`, and the dangling-object cleanup refuses because a drive is missing;
  - its DELETE in an unversioned bucket can still take the blind delete.

  Replacing the drive makes every drive of the set answer again. It does not by itself recover the object: heal can rebuild it only from enough surviving drives that agree on its metadata and hold its data. Without that, once every drive answers, the inconsistent read can turn into not found. To recover, replace the drive, let drive healing run, and then verify the object with a read and a listing of its versions; do not assume that it was recovered.
- `/minio/health/cluster` can report a node healthy before it reaches all of its peers' drives. Acceptance scripts should probe a write and a read through each node instead.

## Verification {#verification}

A deterministic unit test builds an 8-drive EC 4+4 set with an in-memory tier, commits a restore, a transition or an overwrite with two drives hidden, and reads through a view of four drives:

| Case | Before | After |
|---|---|---|
| Restore committed on 6 of 8 drives, versioned and unversioned bucket | 404 | 503 |
| Transition committed on 6 of 8 drives | 404 | 503 |
| Unversioned overwrite committed on 6 of 8 drives | 404 | 503 |
| Absent key, same view | 404 | 404 |
| Inconsistent copies, every drive answered | 404 | 404 |

The restore, transition and unversioned-overwrite cases assert a read-quorum error with HTTP 503. A versioned overwrite may serve the older version but must not be reported missing. Without the fix, the three cases fail; with Option A alone, the unversioned overwrite still fails.

About 100 related tests pass with the fix, covering read quorum, dangling objects, restore, listing and delete-marker purge.

## Review history {#review}

- Adversarial review, round 1: approved with nits. It checked the predicate against every error a drive slot can hold, every caller of the version merge, and the dangling-object purge. The nits were adopted: the tests assert 503 instead of only "not 404", and this record now lists the degraded deletes, copies and maintenance that fail instead of treating the object as absent, and no longer treats corrupt metadata as proof of absence.

## References {#references}

- Upstream [#20522](https://github.com/minio/minio/pull/20522), [#19165](https://github.com/minio/minio/pull/19165)
- [Restored Copies: Expire the Copy, Not the Object](/blog/design/restored-copy-expiry/)
