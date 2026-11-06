---
title: "A Failed Multipart Completion Can Strand the Upload"
linkTitle: "Multipart Completion Retry"
date: 2026-11-06
author: "PGSTY SILO Maintainers"
summary: >
  Why a CompleteMultipartUpload that misses write quorum can destroy the upload on the drives where its rename succeeded, leaving it stuck until stale-upload cleanup, and why the repair is deferred until storage operations can be fenced.
tags: [Design, Multipart, Erasure Coding, S3 Compatibility]
weight: 10
draft: false
url: "/blog/design/multipart-complete-retry/"
---

This record covers a defect found during local acceptance of the next release. It reproduces on [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) and is inherited from upstream MinIO. It has no GitHub issue yet.

**Status:** analyzed and reproduced. A fix was drafted, but an adversarial review rejected it as too risky for this release. The repair is deferred to the next release, together with completion fencing for storage operations. The next release lists the defect as a known issue.

## Short answer {#tldr}

When `CompleteMultipartUpload` fails to reach write quorum, the upload can become unusable, even after every drive is healthy again:

- Complete answers 503 again;
- uploading a part again under the same upload ID answers 503;
- ListParts lists no parts.

The upload stays like this until stale-upload cleanup removes it, so the client has to start a new upload and send every part again. When the rename succeeded on more drives than the parity count, the uploaded data cannot even be rebuilt. In one variant, where a drive applied the rename but its answer was lost, the retry answers 404 NoSuchUpload, which a client may read as "an earlier Complete succeeded".

The defect does not touch committed objects. The damage is to uploads in progress, at the moment a completion meets a drive fault.

A small fix that moves the parts back and restores the upload metadata makes the reproduction pass, but it can race with late storage operations and with stale-upload cleanup. In those races it could publish an object without its data, or count a drive without shards as a successful write. That would turn an availability defect into a data defect, so it is not in this release.

**Workaround:** when a completion fails with 503 and keeps failing after the cluster is healthy, abort the upload and upload the object again.

## Classification {#assessment}

| Aspect | Assessment |
|---|---|
| Nature | The failure path of multipart completion discards the upload. Inherited from upstream MinIO since 2020. |
| Impact | An upload whose completion met a drive fault must be uploaded again from the start, or, in the lost-answer variant, may look completed when it is not. |
| Data safety | This defect deletes no committed object. In-progress upload data is lost on the drives where the rename succeeded. A separate, older gap in the same undo (T4) can lose an overwritten null version that sits beside older versions. |
| Severity | S2: an availability and retry defect. It needs a drive fault during Complete. |
| Effort | A safe fix is medium: it depends on fencing storage operations. |

## When it happens {#trigger}

Complete renames the upload in place into the object. On a 4-drive set with EC 2+2 (write quorum 3), it happens when, for example:

- the rename fails on 2 drives and succeeds on 2 (a permission error, a full drive, a drive fault);
- one drive is offline and the rename fails on another;
- one drive applies the rename but its answer is lost, and the rename fails on another.

When the rename fails on only one drive, quorum is met and the commit succeeds. When it fails on fewer drives than write quorum requires but more than one, the upload survives on enough drives, but the first retry answers 400 InvalidPart, and only a re-upload of the parts works.

## Root cause {#root-cause}

Line numbers are for the local integration of the next release; the code path is the same on `69fcf50cd`.

1. Before the commit, Complete deletes the `part.N.meta` file of every completed part on every drive (`cmd/erasure-multipart.go:1663-1678`, `:1725`). This happens before anyone knows whether the commit will reach quorum.
2. The commit calls erasure `renameData` from the upload directory into the object (`:1734`). On each drive, `xlStorage.RenameData`:
   - writes the merged object `xl.meta` over the upload `xl.meta` (`cmd/xl-storage.go:2900`);
   - moves the upload's data directory, which holds all the parts, into the object (`:2926`);
   - moves `xl.meta` there too (`:2965`);
   - deletes the upload directory (`:2989-2996`).
3. Below write quorum, the undo calls `DeleteVersion(UndoWrite)` on the drives where the rename succeeded (`cmd/erasure-object.go:1140-1167`). That moves the version's data directory, which is the upload's parts, to the trash (`cmd/xl-storage.go:1387-1412`). Nothing moves anything back into `.minio.sys/multipart`.

Afterwards the upload exists only on the drives where the rename failed, and there it holds the merged object metadata instead of the upload's. Below write quorum, PutObjectPart and Complete answer 503. With no `part.N.meta` left anywhere, ListParts lists nothing.

### Provenance {#history}

- Upstream [#9377](https://github.com/minio/minio/pull/9377) (`4915433bd`, 2020) replaced the old undo, which renamed the upload back, with the version delete that discards the data. Before it, a failed Complete could be retried.
- Upstream [#15346](https://github.com/minio/minio/pull/15346) (`f939d1c18`, 2022) introduced `part.N.meta` and its deletion before the rename.
- The merged metadata written into the source comes from `2d58a8d86` (2020).

## Options {#options}

### Option A: the undo moves the parts back

For a multipart source only, rename the data directory back into the upload before the existing `DeleteVersion(UndoWrite)`. Necessary, but not enough alone: the part metadata is already gone on every drive, and the upload metadata was moved or overwritten.

### Option B: delete the upload directory only after the caller decides

By the time a drive's rename succeeds, the upload directory is already empty, so delaying its removal saves nothing. It would also need a storage RPC change and every node upgraded. Rejected.

### Option C: rebuild the upload from the drives that still have it

The data may already be gone, the part ETags are lost, and a minority leftover cannot be told apart from the remains of an earlier successful Complete or Abort, so this could commit a second version. Rejected.

### Option D: keep `part.N.meta` until after the commit

This changes the success path and leaves part metadata in object directories after a crash. It still needs Option A and the metadata restore. Rejected.

### Option E: answer NoSuchUpload or abort the upload

Not a fix. S3 clients read NoSuchUpload on a retried Complete as "it may have succeeded".

## The drafted fix, and why it is deferred {#deferred}

The drafted fix combined Option A with a restore step in Complete. It kept a copy of each drive's upload metadata. When the commit failed, it checked on each drive with `CheckParts` that every part was present, rewrote each `part.N.meta`, and rewrote the upload `xl.meta` last. About 45 lines of code, failure path only, no storage RPC or format change. It made every case of the reproduction pass.

The adversarial review rejected it for this release:

- **A late rename can publish an empty object.** A remote rename can stage the object metadata and pause before moving the data, while its caller has already seen an error. The restore then writes the upload metadata back, and when the late rename resumes it publishes that metadata as the object: size zero, no parts. A late undo can likewise delete a successful retry, because it matches the reused version ID.
- **Stale-upload cleanup takes no lock.** It can remove an expired upload after `CheckParts` passed. The restore's writes then recreate a data directory that holds only part metadata, and a retry can count that drive as a successful write without shards.
- **Empty uploads lose their zero-length part files**, which the restore did not recreate.
- **The restore ignores lock loss and can run long under the locks:** it keeps writing after a distributed lock is lost, and an upload with thousands of parts means thousands of durable writes per drive.
- **A definite failure after the data moved still strands the upload**: a drive that failed after moving the parts but before committing the metadata is neither undone nor restored.

The first two would turn an availability defect into a data defect. Both come from the same missing guarantee: the coordinator cannot tell whether a storage operation that returned an error, or that it gave up on, has finished. That gap is already tracked separately for all write paths.

## What a complete fix needs {#needs}

- a way to fence or confirm the outcome of `RenameData` and of the undo on each drive before the upload's paths are reused;
- mutual exclusion between stale-upload cleanup and the restore, and a revalidation after the part metadata is written; a data directory must never be recreated after its last check;
- the zero-length part files of empty uploads;
- cancellation on lock loss, a total time budget, and bounded parallel writes;
- recovery of data that a definitely failed drive had already moved, or an explicit narrower scope.

## Cost and compatibility of a future fix {#cost}

The drafted approach needs no storage RPC or on-disk format change, and only the coordinating node runs new logic. Fencing storage operations may change that, because it needs the drive to report or reject operations by a generation. A design for it is part of the separate work on storage operation completion.

## Verification {#verification}

A deterministic unit test on a 4-drive EC 2+2 set uploads a 5 MiB and a 1 MiB part, breaks drives, runs Complete, restores the drives, and requires that ListParts shows both parts, that Complete succeeds by direct retry and after a re-upload, that the content matches, and that no drive holds object metadata without its parts. On `69fcf50cd` and on the local integration, every case fails:

| Scenario | Result today |
|---|---|
| Bucket directory read-only on 2 drives | stuck, 503 |
| Rename refused on 2 drives | stuck, 503 |
| One drive offline, rename refused on another | stuck, 503 |
| Rename applied with a lost answer, refused on another | 404 NoSuchUpload |
| Unversioned overwrite, rename refused on 2 drives | stuck, old object kept |
| Empty object | stuck |

The process-level acceptance reproduces the bucket-directory and offline-drive cases identically on `69fcf50cd` and on the next release.

## Related defects found on the way {#related}

- Parts that were uploaded but left out of the Complete list are moved into the object's data directory and stay there as orphaned files. Upstream since 2022.
- When the commit fails with a permission error on enough drives, Complete answers 403 instead of 503, so a client may not retry.

Both are tracked for the next release.

## Review history {#review}

- Adversarial review, round 1: rejected for this release, for the reasons in [The drafted fix, and why it is deferred](#deferred). The review also corrected this record: the drafted fix was not sufficient, the residual races were understated, and "no committed object is lost" was too broad because of the older undo gap.

## References {#references}

- Upstream [#9377](https://github.com/minio/minio/pull/9377), [#15346](https://github.com/minio/minio/pull/15346)
- [A Partial View Must Not Report an Existing Object as Missing](/blog/design/partial-view-read-404/)
