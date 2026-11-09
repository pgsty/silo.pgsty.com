---
title: "Failed Writes and Phantom Empty Prefixes"
linkTitle: "Phantom Empty Prefixes"
date: 2026-11-04
lastmod: 2026-11-09
author: "PGSTY SILO Maintainers"
summary: >
  Why a write whose staged data is already gone can leave an empty object directory that later appears as a common prefix with nothing under it, and why removing empty directories on the rename failure path is the minimum complete repair.
tags: [Design, Storage, ListObjects, Operations]
weight: 10
draft: false
url: "/blog/design/failed-rename-empty-prefix/"
---

This record covers [issue #285](https://github.com/pgsty/silo/issues/285) and [PR #286](https://github.com/pgsty/silo/pull/286) by Denis Babchuk, evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) and the PR head [ed05d982a](https://github.com/pgsty/silo/commit/ed05d982a1d26502e3ed2c7c5605bcf422f5d228).

**Status:** fix approved by review and committed locally. Tested together with the other fixes for the next release on one integration branch: the full local suite with the `kqueue,dev` tags, the CI race selections run locally and an adversarial review of how the fixes interact all pass. Not merged or released. The fix keeps the PR #286 commit unchanged and adds one maintainer commit.

## Short answer {#tldr}

The report is real. A drive can run `xlStorage.RenameData` after the caller has given up and removed the staged data. The rename of the data directory then fails, but the object directory created for that rename stays behind, empty. It is invisible while other objects share its parent. Once they are deleted, the parent can no longer be removed, and a delimiter listing returns a common prefix with nothing under it.

No object data is lost, changed, or exposed. The damage is a permanent listing anomaly:

- tools that read every listed prefix fail on it, for example Iceberg `remove_orphan_files`;
- heal does not remove it;
- when the name of the empty object directory is not known, the only S3 cleanup is a destructive force delete of the prefix.

PR #286 is the right repair. When the data directory rename fails, it also removes the object directory if it is empty, and then each parent that becomes empty. The trailing slash limits the first removal to an empty directory, so an existing object, another data directory, or legacy data is never touched there.

We adopt it with three additions:

- The commit step of the same function, the rename of `xl.meta`, has its own failure branch. That branch leaves the same empty directory for writes without a data directory, such as inline and zero-byte objects, and gets the same one-line cleanup.
- The walk up the parents removes only empty directories. Before, it removed whatever was at each parent path, which a concurrent write can replace with the `xl.meta` of a committed object. The adversarial review showed that the new cleanup makes this reachable on every drive.
- A write whose rename fails because a concurrent cleanup removed a directory of its destination path, while its own source is still in place, creates the directories again and retries, up to once per path level. Direct metadata writes (`WriteMetadata` and `UpdateMetadata`) also retry `openFileAll` and `renameAll` up to once per path level when a concurrent `RenameData` empty-directory cleanup removes a parent directory during a first-version or delete-marker metadata write ([`479a49b28`](https://github.com/pgsty/silo/commit/479a49b28)).

The fix does not sweep directories that are already on the drives. A later write and delete of the same key removes one; [Residual limits](#limits) describes how to find and remove them.

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | Cleanup defect on the write failure path; inherited from upstream MinIO, not a regression in a SILO release. |
| Affected deployments | Erasure-coded deployments, in practice distributed ones, where a remote drive finishes `RenameData` after its caller gave up: slow or overloaded nodes, drive timeouts, client disconnects. |
| Affected writes | A write of a key that has no `xl.meta` on that drive, whose data lives in a data directory: objects above the inline threshold and multipart completions. Writes without a data directory reach the same state through the commit branch, with a narrower window. |
| Not affected | Successful writes; existing objects and versions; overwrites of a key that already has `xl.meta` on that drive. |
| Severity | Moderate. No data loss or corruption. Listings return empty prefixes indefinitely, tools that walk prefixes fail, and the directories accumulate under prefixes that still hold objects. |
| Reachability | Timing-dependent. The reporter could not reproduce it live with about 5000 client-cut writes on a 4-node cluster with injected latency, but found it in production on 12- and 16-drive sets. The tests build the state deterministically. |
| Release urgency | Not a data-safety blocker, but planned for the next release: production users hit it (Iceberg orphan cleanup). The cleanup and the retry run only when a rename fails; the directory-only walk up also applies to ordinary deletes, where it removes the same directories as before, except a parent that holds only a macOS `.DS_Store` file. |
| Remaining effort | The fix and its tests are done and reviewed locally. Remote CI, merge, and release remain. |
{.wide .expand}

## When it happens {#trigger}

The sequence on one drive:

{.steps}
1. A `PutObject` above the inline threshold, or a `CompleteMultipartUpload`, reaches the commit stage and calls `RenameData` on every drive of the erasure set.
2. The calling node stops waiting for a remote drive: the client disconnects, the request is canceled, or the drive call times out. The remote drive is not told. `RenameDataHandler` runs `RenameData` with `context.Background()`, and the grid single-request handler has no context at all. The remote drive wrapper, `xlStorageDiskIDCheck.RenameData`, bounds the call with the drive timeout (30 seconds by default) but returns at that deadline while a filesystem call in progress continues.
3. Without write quorum the caller fails the write. `renameData` undoes the drives that reported success. The deferred `deleteAll` in `PutObject` removes the staged object from `.minio.sys/tmp` on every drive. For multipart, an `AbortMultipartUpload` after the failed completion removes the upload directory.
4. The late `RenameData` reaches the data rename. `renameAll` first creates the destination's parents (`reliableRename` → `reliableMkdirAll`), which creates `<bucket>/<prefix>/<object>/`. The rename then fails with "not found", and the cleanup removes only the data directory path, which never existed.
5. Later, every other object under `<prefix>/` is deleted. Each delete removes its own object directory and stops at the parent, which still holds the empty `<object>/`.

With the empty directory left on enough drives, listings on main look like this (from the tests, where only `day=1/b=9/put/` is left):

| Request | Result on main |
| --- | --- |
| `ListObjectsV2` with `delimiter=/` and no prefix | prefix `day=1/` |
| `ListObjectsV2` with `delimiter=/` and prefix `day=1/` | prefix `day=1/b=9/` |
| `ListObjectsV2` with `delimiter=/` and prefix `day=1/b=9/` | nothing |
| Recursive `ListObjectsV2`, `ListObjectVersions`, `HEAD day=1/b=9/put` | nothing, nothing, not found |
{.wide .expand}

The prefix appears when the directory is on at least half of the set's drives, which is the default `strict` listing quorum. In a 16-drive set it is listed with the directory on 8 drives and not listed with it on 7.

## Root cause {#root-cause}

Two behaviors meet.

**The cleanup assumes the failed rename created nothing but the data directory.** `deleteFile(dstVolumeDir, dstDataPath, false, false)` removes the data directory when it exists and is empty. Only after a successful removal does it walk up and remove parents while they are empty. When the source was missing, the data directory never existed. The removal reports "not exist", `deleteFile` returns early, and the object directory that `reliableMkdirAll` created a moment earlier is never considered.

**The listing walk hides an empty directory, but not a directory that contains one.** A directory without `xl.meta` is reported as a prefix only when it is not empty. The empty `<object>/` is skipped. Its parent is not empty, so it is reported, and so is every ancestor above it. Deleting the other objects cannot fix this: each delete walks up to the parent, finds it not empty, and stops.

Nothing else cleans it up. Heal, including heal started by the data scanner, removes a directory only when fewer drives hold it than lack it. The scanner itself does not remove directories from drives.

## Where the behavior came from {#history}

### Provenance {#provenance}

**Introduced by upstream MinIO, not by SILO.** The leftover directory is older than the cleanup that was meant to prevent it. Every ingredient below is an upstream commit that is an ancestor of the SILO fork point ([`27742d469`](https://github.com/pgsty/silo/commit/27742d469), 2025-12-03). The cleanup block is byte-identical in MinIO `RELEASE.2025-07-23T15-54-02Z`, the release where the reporter saw it, in the last upstream release `RELEASE.2025-10-15T17-29-55Z`, in the archived upstream `master`, on `main`, and on every SILO release from `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z`. We compared the lines on each tag. SILO changed the late-write window once, for one release, and no SILO commit changed the cleanup.

| Ingredient | Commit (PR) | Date | First upstream release |
| --- | --- | --- | --- |
| A rename creates the destination's parent directories before it renames. | [`12f67d47f`](https://github.com/pgsty/silo/commit/12f67d47f) ([#5376](https://github.com/minio/minio/pull/5376)) | 2018-01-13 | `RELEASE.2018-01-18T20-33-21Z` |
| `RenameData` moves the data directory and `xl.meta` with that rename. There is no cleanup on failure, so the directory it created stays. | [`4915433bd`](https://github.com/pgsty/silo/commit/4915433bd) ([#9377](https://github.com/minio/minio/pull/9377)) | 2020-06-12 | `RELEASE.2020-07-11T06-07-16Z` |
| The failure cleanup is added: `deleteFile` on the data directory path, and on the `xl.meta` path in the commit branch. `deleteFile` for a missing path returns before it walks up, first as "not found" and since this commit as `nil`. | [`dd2831c1a`](https://github.com/pgsty/silo/commit/dd2831c1a) ([#12452](https://github.com/minio/minio/pull/12452)) | 2021-06-07 | `RELEASE.2021-06-07T21-40-51Z` |
| The commit-branch cleanup is retargeted from the `xl.meta` path to the data directory path, and a write with no data directory ID, which used to write `xl.meta` directly, now also goes through the staged-file rename. | [`c7f7c4738`](https://github.com/pgsty/silo/commit/c7f7c4738) ([#18801](https://github.com/minio/minio/pull/18801)) | 2024-02-20 | `RELEASE.2024-02-24T17-11-14Z` |
| Storage RPC handlers run drive mutations with `context.Background()` (grid). Before, the handler passed the request's context. | [`51aa59a73`](https://github.com/pgsty/silo/commit/51aa59a73) ([#18461](https://github.com/minio/minio/pull/18461)) | 2023-11-20 | `RELEASE.2023-12-02T10-51-33Z` |
| The drive wrapper bounds `RenameData` with a deadline and returns at it while the work continues: deadline worker, then `WithDeadline`, in its current form. | [`e7b60c4d6`](https://github.com/pgsty/silo/commit/e7b60c4d6) ([#17701](https://github.com/minio/minio/pull/17701)), [`4a6c97463`](https://github.com/pgsty/silo/commit/4a6c97463) ([#18861](https://github.com/minio/minio/pull/18861)), [`9693c382a`](https://github.com/pgsty/silo/commit/9693c382a) ([#19548](https://github.com/minio/minio/pull/19548)) | 2023-07-25, 2024-01-24, 2024-04-23 | `RELEASE.2023-08-04T17-40-21Z`, `RELEASE.2024-01-28T22-35-53Z`, `RELEASE.2024-04-28T17-53-50Z` |
{.wide .expand}

How the pieces fit:

- **The directory leak predates the cleanup.** From the first `RenameData` the rename created the object directory and nothing removed it when the rename failed. #12452 added a cleanup, but it targets paths that do not exist when the source is missing, and `deleteFile` returns before it considers any parent. It has never been able to remove this directory.
- **#18801 did not change the outcome.** Before it, the commit branch cleaned the `xl.meta` path, which a failed rename leaves absent. After it, the branch cleans the data directory path, which is absent for inline writes and a non-empty directory when the data rename had succeeded. Neither removes the empty object directory. The branch still creates it, so the commit step leaves the same leftover, as this record says.
- **The late write comes from the timing ingredients.** The drive wrapper's deadline (2023-2024) and the handler's `context.Background()` (#18461) let `RenameData` run after its caller gave up and the staged data was removed. The handler's context did not gate any step in `RenameData` at that time, so #18461 did not create the window. Cancellation checks added later (#19627, 2024-04-28) do not see the caller's cancellation on a remote drive. They fire only at the remote drive's own deadline, which its drive wrapper adds.
- **The cleanup text in the issue is accurate.** It matches `RELEASE.2025-07-23T15-54-02Z`, and the block has not changed since #19548 in April 2024.

**SILO changes** (all after the fork; none touched `deleteFile`, `RenameDataHandler`, or the two cleanup calls):

| SILO commit | Date | SILO releases | Effect on the leftover |
| --- | --- | --- | --- |
| [`f480086b6`](https://github.com/pgsty/silo/commit/f480086b6) (PR #232) | 2026-10-12 | `RELEASE.2026-10-18T00-00-00Z` and later | **Did not affect.** `errCommitMetaMissing` reclassifies a missing staged `xl.meta` as a write-quorum failure (503) after the cleanup call, so clients retry. The directory is left as before. |
| [`cd1f6cec3`](https://github.com/pgsty/silo/commit/cd1f6cec3), [`5ad1f344b`](https://github.com/pgsty/silo/commit/5ad1f344b) | 2026-10-25 | `RELEASE.2026-10-25T00-00-00Z` only | **Narrowed the late-write window.** The caller waited for each admitted `RenameData` (drive wrapper `WithDeadlineAndWait`, remote call without cancellation or default timeout) before it rolled back, removed staged files, and released the lock. The cleanup code was unchanged, so a write that still failed leaked the same way. |
| [`ea7c794a9`](https://github.com/pgsty/silo/commit/ea7c794a9), [`8a4097309`](https://github.com/pgsty/silo/commit/8a4097309), [`652a1c09d`](https://github.com/pgsty/silo/commit/652a1c09d) | 2026-10-25 | `RELEASE.2026-10-25T00-00-00Z` only | **Did not affect.** Per-path mutation locks, a separate rollback backup directory, and protection of unfinished commits from abandoned-data cleanup. |
| [`dcc2f20ba`](https://github.com/pgsty/silo/commit/dcc2f20ba) | 2026-10-26 | `RELEASE.2026-10-26T00-00-00Z` and `main` | **Restored the inherited window.** It withdrew the wait-for-inflight work above to keep the established timeout behavior; see [Storage Timeouts and Rollback Boundaries](/blog/design/multi-pool-object-consistency/#maintenance-20261026). |
| [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff), [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) | 2026-08-02, 2026-10-18 | `RELEASE.2026-08-04T00-00-00Z`, `RELEASE.2026-10-18T00-00-00Z` | **Did not affect.** Panic recovery inside the deadline worker, and prompt removal of empty multipart upload parents under the system bucket. Neither touches the destination object directory. |
{.wide .expand}

No SILO commit introduced or widened the leftover. The only SILO change that reduced the exposure was released once and withdrawn a day later, so `RELEASE.2026-10-26T00-00-00Z` carries the same exposure as upstream. Late drive operations remain a documented boundary, and this issue is one of their visible effects.

**Evidence.** The identity of the cleanup block on each tag, the ancestry of every commit, and the first release of each were checked with git (executed). The `20261025` narrowing and the effect of #18801 are from reading the diffs (reasoned). The reporter could not reproduce the late write live either; the deterministic tests under [Verification](#verification) build the state directly.

## Options {#options}

### Option 1: remove empty directories on the rename failure path {#option-1}

This is the approach of PR #286 and the chosen option. The function that created the directories removes them in the same call, on the same drive, and only when they are empty. It costs nothing on the success path and needs no new state.

### Option 2: make the remote `RenameData` honor the caller's cancellation {#option-2}

This would narrow the window without closing it, at a much higher cost. The grid single-request handler receives no context; the grid server knows the request deadline but uses it only to drop a late reply. Propagating cancellation needs a change to the grid request protocol or a different handler type for this call. Cancellation also cannot stop a filesystem call in progress, so a cancel that arrives between the directory creation and the rename still leaves the directory, and Option 1 would still be needed. SILO's earlier work to wait for admitted storage I/O was withdrawn to keep the established timeout behavior (see [history](#history)).

### Option 3: let heal or the scanner remove empty object directories {#option-3}

This is the only option that would sweep directories left by older releases or by a crash without any action by the user, but it is not adopted here. Heal deliberately removes only a directory that a minority of drives hold. Removing majority-present empty directories in the background would race with every first write between its directory creation and its rename, not only with late ones, unless it took the object lock and used an age threshold. That is a new destructive background behavior that needs its own design. It remains a possible follow-up for existing leftovers.

### Option 4: make listing ignore directories with no object below them {#option-4}

The walk only knows whether a directory is empty. Proving that a subtree holds no object means reading the whole subtree for every directory entry of a delimiter listing. The directories would also stay on the drives, and their parents still could not be removed. Rejected.

### Option 5: check the staged data before creating the destination {#option-5}

This adds a system call to every write and still races, because the staged data can disappear between the check and the rename. Rejected.

### Option 6: let `reliableRename` recreate the parent when it retries {#option-6}

This would let a concurrent writer survive a cleanup that removed its directory (see [the race below](#sufficiency)). It is not adopted in `reliableRename`. `renameAll` is shared by many callers, and the change would recreate destination parents in exactly the missing-source case, including for callers that have no cleanup.

A narrow form is adopted in `RenameData` instead: its two renames retry, recreating the directories, only when a directory of the destination path disappeared and the source is still in place. A missing source, which is the late-write case, is not retried, and the cleanup that follows covers a source that disappears during a retry.

## Proposed fix {#fix}

{.steps}
1. **Data rename failure branch (PR #286).** After the existing cleanup of the data directory, `RenameData` calls

   ```go
   s.deleteFile(dstVolumeDir, pathutil.Dir(dstFilePath)+SlashSeparator, false, false)
   ```

   The path is the object directory. Without recursion, `deleteFile` only tries to remove that directory. With the trailing slash, a directory that is not empty returns "not found", which the caller ignores, so nothing that holds data is removed. When the removal succeeds, `deleteFile` walks up and removes each parent while it is empty, stopping at the bucket directory.

   The PR adds two tests. `TestRenameDataStagedDataGoneLeavesNoPrefix` builds the reported state on a 16-drive set with a `PutObject` and a `CompleteMultipartUpload` of 8 MiB objects, then checks the listings and the drives. `TestRenameDataStagedDataGoneKeepsExistingObject` checks that a failed overwrite keeps the old object readable.
2. **Commit failure branch (maintainer addition).** The rename of `xl.meta` at the end of `RenameData` creates the object directory in the same way, and its failure branch has the same cleanup gap. For a write without a data directory, if the staged `xl.meta` disappears between its write and the commit, an empty object directory remains, with or without PR #286. The same call is added to that branch. `TestXLStorageRenameDataCommitMetaMissingRemovesEmptyDirs` reuses the `missingCommitMetaContext` hook of the existing `TestXLStorageRenameDataCommitMetaMissing`, which removes the staged `xl.meta` at exactly that point. It checks that a zero-byte and an inline write leave neither the object directory nor its empty parents, that a parent holding another object stays, and that a data directory moved before the failed commit stays in place.
3. **Directory-only walk up (maintainer addition, found by the adversarial review).** After a successful removal, `deleteFile` walks up and removes each parent. It called the removal without a trailing slash, which also deletes a file. Between two steps of a walk, another walk can remove the rest of the chain, and a writer can then commit an object whose `xl.meta` sits at the very path the first walk removes next: for the key `parent/xl.meta/child`, that is the object `parent`. The walk then deleted the committed metadata, on every drive where the interleaving happened. The walk now passes the parent with a trailing slash, so it removes only an empty directory and stops at anything else. The other walk can be the new cleanup, which makes the interleaving reachable with ordinary failed writes, or an ordinary delete, so the hazard also existed before the fix. `TestXLStorageWalkUpKeepsCommittedObject` reproduces it through `DeleteVersion` and through both cleanup branches.
4. **Retry after a concurrent cleanup (maintainer addition, found by the adversarial review).** The new cleanup can remove another write's destination directory between its creation and the rename. That write's rename then failed even though its source was intact, on every drive where this happened, with `IncompleteBody` (400), `NoSuchKey` (404), or a write-quorum error depending on the branch and the operation. Both renames in `RenameData` now retry when the directory creation or the rename of an attempt reports "not found" and the source is still in place. Direct metadata writes (`WriteMetadata` and `UpdateMetadata`) also retry `openFileAll` and `renameAll` up to once per path level when a concurrent `RenameData` empty-directory cleanup removes a parent directory during a first-version or delete-marker metadata write ([`479a49b28`](https://github.com/pgsty/silo/commit/479a49b28), `TestXLStorageMetadataWriteSurvivesRenameDataCleanup`). The decision uses the error of the attempt itself, before it is mapped to a storage error, because another write, for example of a nested key, can recreate the directories before the decision is made. Each retry runs the directory creation below its base directory again; see the cached-base limit under [Residual limits](#limits). A cleanup removes each directory of the path at most once, walking up, and every failed attempt needs at least one more removal, so the write retries up to once per path level below its base directory and no single cleanup can exhaust it. `TestRenameDataSurvivesConcurrentEmptyDirCleanup` runs a late failed `RenameData` of the same key on all 16 drives right after a `PutObject` (8 MiB and inline) or a `CompleteMultipartUpload` created the directory, and checks that the late call removed the directory and that the write still succeeds. `TestXLStorageRenameDataRetriesWhileCleanupWalksUp` removes `object/`, `b/`, and `a/` of `a/b/object` one at a time, each right after the write's next directory creation reached it, so that the walk defeats the first rename and both directory creations of the next attempt; the write must still succeed. A third case lets a write of `a/b/object/child` recreate the directories right after a failed creation.

The test helper `stagedDataGoneDisks` from PR #286 now swaps the drives behind the set's disk list under the lock that the list takes, instead of replacing the callback that background tasks read without it.

The two rename branches are the only places where `RenameData` creates the object directory of a new key. Items 3 and 4 do not change where directories are created. They make the cleanup safe for concurrent writes.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient.** The reported directory is created inside the failing `renameAll`. The cleanup runs immediately after it, on the same drive and in the same call, and removes exactly the directories that are empty, from the object directory upward. With the commit-branch addition, the same holds for writes without a data directory. Multipart completion uses the same `RenameData`, and the PR test covers it.

**Safe for data.** Every removal in the cleanup, the first one and each one of the walk up, removes only an empty directory. Anything that makes a directory non-empty keeps it: the `xl.meta` of existing versions, another data directory, legacy data, or a nested object below the same name. A file at a parent path, such as the `xl.meta` of an object committed there in the meantime, stops the walk. A recursive variant of the new cleanup fails `TestRenameDataStagedDataGoneKeepsExistingObject` and the `data_directory` case of the commit-branch test, and a walk up without the trailing slash fails `TestXLStorageWalkUpKeepsCommittedObject`, so the tests detect both destructive changes.

**A concurrent write of the same key.** The late `RenameData` runs after its caller has released the object lock, so another writer of the same key can reach the same drive at the same time, typically the client's retry. If the key has no `xl.meta` on that drive, the cleanup can remove the directory, and parents that are empty, between the other writer's directory creation and its rename. The late calls of one failed write reach every drive of the set, so this can happen on any number of drives. The other writer's rename or directory creation then fails while its source is still in place, so it creates the directories again and retries, up to once per path level. One cleanup removes each directory at most once, so it cannot exhaust the retries alone. The write fails on a drive only if several cleanups keep removing its directories through all retries. In that case the erasure layer counts the drive as failed for that write:

- with write quorum on the other drives, the write succeeds and tries to queue an MRF heal for the drive;
- without write quorum, the write fails as a whole, the drives that did commit are rolled back on a best-effort basis, and the client has to retry;
- a committed object is not removed: a drive that holds `xl.meta` for the key has a non-empty directory, and the walk up stops at a file.

Without the fix this interleaving does not fail, so the fix adds a new failure mode, made narrow by the retries. The class is not new, though. On main, an operation that outlives its lock can already change a single drive, for example with a late commit or a late rollback, and SILO documents that boundary. Deleting the last version of an object already removes its directory and empty parents with the same `deleteFile` call, and that storage RPC also runs with `context.Background()`. Writers of other keys are exposed when the cleanup removes a parent between the creation of that parent and of their own directory. `reliableMkdirAll` then retries once from a higher base directory, exactly as it does against the delete path today; a key whose own directory is one of the removed parents is covered by the retries above.

**Other cleanup branches.** Besides the commit branch, `RenameData` has cleanup for legacy data (`legacyPreserved`). That branch runs only when legacy content already exists at the destination, so the object directory is not empty there. Its own cleanup deletes the legacy data directory recursively and already walks up after a successful removal. It needs no change. The early returns before the first `renameAll` do not create the object directory of a new key.

**Necessary.** Without the cleanup, nothing removes the directory. `deleteFile` returns early, the walk hides it, and heal treats a directory that most drives hold as valid. The directories accumulate under every prefix that still holds objects and surface when those objects are deleted.

**Deliberately excluded.** Directories that are already on drives are not swept (see [Residual limits](#limits)), and the late `RenameData` itself is not stopped.

## Cost and compatibility {#cost}

- No API, configuration, storage-format, metric, route, or dependency change.
- Successful renames add no filesystem calls. When the directory creation or the rename of an attempt reports "not found", the drive checks whether the source is still in place and retries if it is. When the rename finally fails, the drive makes one more removal attempt on the object directory and then on each parent in turn, until a removal fails or the base directory is reached; the base directory is not removed.
- A failed first write no longer leaves its object directory on the drive, as long as the directories are empty and removable. Nothing reads an empty object directory, so for that case listings are the visible behavior that changes. Concurrent writes of the same key also change: they can now see their directory removed and retry, as described under [sufficiency](#sufficiency).
- The directory-only walk up applies to every caller of `deleteFile`, including object and version deletes. It removes the same empty directories as before and no longer deletes a file at a parent path. On macOS, a parent that holds only a Finder `.DS_Store` file is no longer removed by the walk up.
- Rollback restores the old behavior. No migration is needed in either direction.

## Residual limits {#limits}

- **Existing leftovers stay.** Directories created by older releases are not removed proactively. Under prefixes that still hold objects they stay invisible and surface when the last object there is deleted, so new empty prefixes can still appear after an upgrade. A later write of the same key followed by its delete removes one, as does the procedure below.
- **A crash leaves the same state.** If the process or the node stops between the directory creation and the rename, no cleanup runs.
- **A partly created path.** If creating the path fails partway, for example on a full drive, the parents created so far stay. The cleanup starts at the object directory, which then does not exist.
- **An orphaned data directory after the data rename.** When the data directory was already moved and the call then stops before `xl.meta` is in place, the data directory stays inside the object directory without `xl.meta`. This happens when the `xl.meta` rename fails, or when a cancellation check between the two renames fires, for example at the drive's own deadline. This is unchanged; the code deliberately avoids a recursive delete at that point. If it ever happened on half of the drives, it would also appear as a prefix, and the procedure below removes it.
- **Several concurrent cleanups.** The retries cover any single cleanup on a drive, also when another write recreates the directories in between. Several cleanups that keep removing a write's directories through all retries still fail the write on that drive. When the same failure happens on at least a write quorum of drives, the client sees an error that depends on the failing step: `AccessDenied` (403) when a directory creation failed, `IncompleteBody` (400) for `PutObject` or `NoSuchKey` (404) for `CompleteMultipartUpload` when the data rename failed, and `SlowDownWrite` (503) when the `xl.meta` rename failed. Otherwise a write that lost quorum reports a write-quorum error (503). These mappings are unchanged from main, where concurrent deletes that remove empty parents can already exhaust the single retry of the directory creation.
- **A cached base directory.** On an overwrite, the renames take the object directory as the base of the directory creation, because it held `xl.meta` when the call started. On Unix, if something removes it in the meantime, the retries do not recreate it; Windows does not use the base directory. The new cleanup cannot do this, because the directory holds `xl.meta`; the limit is unchanged from main.
- **The late `RenameData` still runs.** It can still recreate the staged `xl.meta` under `.minio.sys/tmp` or in the multipart upload directory; the tests show this on every drive with and without the fix. Those paths are internal, are not listed through S3, and are removed by the existing stale-upload cleanup after `stale_uploads_expiry` (24 hours by default). For inline objects, a late call can still commit metadata on that drive after the caller reported a failure. That is the late-commit boundary described in [Storage Timeouts and Rollback Boundaries](/blog/design/multi-pool-object-consistency/#maintenance-20261026).

### Removing an existing empty prefix {#cleanup}

{.steps}
1. Confirm that the prefix is empty: `mcli ls --recursive --versions ALIAS/BUCKET/PREFIX/` and `mcli ls --recursive --incomplete ALIAS/BUCKET/PREFIX/` return nothing.
2. Confirm that no client writes under that prefix any more. For a table format such as Iceberg, that means a partition that is no longer written.
3. Remove the deepest listed empty prefix with `mcli rm --force --purge ALIAS/BUCKET/PREFIX/`. The server deletes the prefix recursively on every drive of every erasure set and pool, then removes the parents that become empty. In the tests, purging `day=1/b=9/` also removed `day=1/` on all 16 drives.

The force delete is destructive. It removes **everything** under the prefix, including every version, without delete markers, and it cannot be undone. Use it only on a prefix that steps 1 and 2 have shown to be empty and unused.

There is a non-destructive alternative when the name of the empty object directory is known, for example `put` in `day=1/b=9/put/`. Listings do not show it; it can be read from the drives, or may be known from failed-request logs or application records. Write a zero-byte object at that exact key and delete it again; in a versioned bucket, delete it by its version ID. The delete removes the object directory and each parent that becomes empty, as for any other object. It does not help when a default retention period would apply to the new object.

Force delete is refused on buckets with Object Lock enabled. Unless the leaf name is known and no retention applies, there is no supported S3 path to remove such a prefix in those buckets. The directories hold no data and are safe to leave in place, but tools that read every listed prefix must tolerate them. Do not edit drive contents by hand.

## Verification {#verification}

Executed with Go 1.27.3 (darwin/arm64) in disposable worktrees, against main 69fcf50cd, the PR head, and the fix:

- **The regressions fail without the fix and pass with it.** With only the test files on main:
  - `TestRenameDataStagedDataGoneLeavesNoPrefix` fails: the root listing returns `day=1/`, `day=1/` returns `day=1/b=9/`, and `day=1` remains on 16 of 16 drives;
  - the commit-branch test fails for the zero-byte and the inline write, which leave their object directory;
  - `TestXLStorageWalkUpKeepsCommittedObject` fails in all three cases: through `DeleteVersion` the committed object `parent` is lost, and through the two `RenameData` branches the empty directory is not removed;
  - `TestRenameDataSurvivesConcurrentEmptyDirCleanup` fails because the late calls leave the object directory on all 16 drives;
  - `TestXLStorageRenameDataRetriesWhileCleanupWalksUp` fails because the write does not survive the first removal.

  With the PR head alone, the commit-branch test still fails, `TestXLStorageWalkUpKeepsCommittedObject` loses the committed object, and `TestRenameDataSurvivesConcurrentEmptyDirCleanup` fails all three writes, with `IncompleteBody`, `NoSuchKey`, and a write-quorum error. With the fix, all of them pass, also under `-race`. A late `RenameData` of `a/b/object` on each of 16 drives, paused at each removal of its walk so that it removes `object/`, `b/`, and `a/` during the write's first rename and both directory creations of the next attempt, made `PutObject` and `CompleteMultipartUpload` fail with `AccessDenied` when the write retried only once. With a write of `a/b/object/child` that recreated the directories right after a failed creation, the same happened when the retry decision checked the destination after the attempt. With the fix, both writes succeed in both schedules.
- **The guards detect destructive variants.** A recursive cleanup in the data branch fails `TestRenameDataStagedDataGoneKeepsExistingObject`, and in the commit branch it fails the `data_directory` case. A walk up without the trailing slash fails `TestXLStorageWalkUpKeepsCommittedObject`. Removing the retry fails `TestRenameDataSurvivesConcurrentEmptyDirCleanup`, allowing only one retry fails `TestXLStorageRenameDataRetriesWhileCleanupWalksUp` with access denied, and deciding the retry by checking the destination after the attempt fails its nested-writer case the same way. Controls pass on main and with the fix: `TestRenameDataStagedDataGoneKeepsExistingObject`, `TestXLStorageRenameDataCommitMetaMissing`, `TestRenameDataCommitMetaMissing`, and the `data_directory` case.
- **Test helper.** A concurrent reader of the set's disk list reports a data race with the PR's `stagedDataGoneDisks` under `-race` and none with the revised helper.
- **Listing quorum.** With the empty directory on 7 of 16 drives, no prefix is listed; on 8 and on 16 drives it is. Recursive listing, `ListObjectVersions`, and `HEAD` find nothing in every case.
- **Cleanup procedure.** At the object layer, the force-delete option removed the phantom `day=1/b=9/` chain on all 16 drives. The same option on another prefix also deleted a real object under it. In an unversioned bucket, a zero-byte `PutObject` at the leaf key followed by `DeleteObject` removed the chain without a force delete.
- **Side observations.** An inline 1 KiB `PutObject` succeeds even when its staged directory is removed before `RenameData`, because its data travels in the request. After the failed calls, the staged `xl.meta` was recreated under `.minio.sys/tmp` and in the multipart upload directory on all 16 drives, with and without the fix. `ListMultipartUploads` reported no upload. A cancellation after the data rename leaves the data directory without `xl.meta`, on main as with the fix.
- **Nearby tests.** With the fix, `go vet ./cmd` passes, and so do the 137 tests, the new ones included, selected by `^Test(XLStorage|XlStorage|Erasure|DeleteObject|DeleteFile|DeleteVersion|RenameData|PutObject|CompleteMultipart|ObjectComplete|Heal|ListObjects|Walk|Metacache|StorageTimeout|StorageRollback|ReduceWriteQuorumErrs|Multipart|ObjectNewMultipart|NewMultipart|Lifecycle|Decommission|Rebalance|Disk|Posix|Abort|CopyObject|GetObject|Rename|Reliable|OsMkdir|MkdirAll)`. The CI checks of PR #286 pass on its head.

Reasoned from code, not executed:

- the remote timing window itself; there is no live multi-node reproduction;
- eventual healing after a write that lost a drive to several concurrent cleanups;
- the legacy branch, the partly created path, the crash case, and the late inline commit;
- the removal of recreated staged metadata by the stale-upload cleanup;
- the cleanup alternative in versioned buckets, `mcli rm --force --purge` sending the force-delete header, and the refusal on Object Lock buckets;
- the trailing-slash semantics on Linux and Windows filesystems; the tests ran on macOS, and the two tests that schedule directory creations skip on Windows, where it is not traced;
- the upstream history.

The full `./cmd` suite was not run for this record.

**Integration.** The fix was cherry-picked onto one integration branch for the next release, on top of #278 and #281 and together with the lock-domain, heal dry-run, #259, `delete-all` and Console fixes. Every pick applied without conflicts. On that head the full `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` suite passes, as do the CI race-detector selections and a race selection that covers every new test. An adversarial review of the combination found no defects. It checked lock domains, cleanup paths and purge against restore with executed probes.

The passing local runs use the `kqueue,dev` tags. The untagged Ubuntu CI command, `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m`, remains pending on the final commit; the local tagged result does not replace that gate.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Adversarial review, round 1 | Requested changes. The walk up after a removal could delete a file at a parent path, so with a key such as `parent/xl.meta/child` the new cleanup, or an ordinary delete, could remove the `xl.meta` of an object committed in the meantime; fixed with the directory-only walk up (item 3), and reachable on main through deletes. The cleanup could remove another write's fresh directory and fail that write with 400 or 404; fixed with the retry (item 4). The PR's test helper raced with background readers of the disk list; fixed. Ten record corrections were applied. |
| Round 2 | Requested changes. One late call per drive, removing successive parents while the write retried, exhausted a single retry and returned 403. The retry now repeats up to once per path level. Reclassifying an exhausted failure as 503 was not taken; the residual is documented under [Residual limits](#limits). Seven record corrections were applied. |
| Round 3 | Requested changes. A write of a nested key that recreated the directories after a failed attempt hid the failure from the retry decision, which now uses the error of the attempt itself. The two tests that schedule directory creations skip on Windows. The overview now matches the cleanup guidance. |
| Round 4 | Approved with nits: three wording corrections about the cached base directory and the cleanup walk, applied. |
{.wide .expand}

## References {#references}

- Issue: [#285](https://github.com/pgsty/silo/issues/285)
- Contributor PR: [#286](https://github.com/pgsty/silo/pull/286)
- Commit-metadata error classification: [#232](https://github.com/pgsty/silo/pull/232) and [Write commit errors](/reference/s3-api-compatibility/#write-commit-errors)
- Late-operation boundary: [Storage Timeouts and Rollback Boundaries](/blog/design/multi-pool-object-consistency/#maintenance-20261026)
- Upstream origin of the cleanup: [minio/minio#12452](https://github.com/minio/minio/pull/12452)
