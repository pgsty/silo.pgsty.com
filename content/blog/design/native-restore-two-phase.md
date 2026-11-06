---
title: "Native Restore in Two Phases"
linkTitle: "Two-Phase Native Restore"
date: 2026-11-06
lastmod: 2026-11-06
author: "PGSTY SILO Maintainers"
summary: >
  Why a native restore held the object lock for its whole tier download, why the first fix of #281 also stranded failed ordinary uploads, and how staging outside the lock and a short, checked commit replace the private upload.
tags: [Design, Tiering, Locking, Availability]
weight: 10
draft: false
url: "/blog/design/native-restore-two-phase/"
---

This record covers [issue #284](https://github.com/pgsty/silo/issues/284) and two regressions of the first native-restore safeguards for [#281](https://github.com/pgsty/silo/issues/281), described in [Restored Copies: Expire the Copy, Not the Object](/blog/design/restored-copy-expiry/). It was evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) and the integration branch for the next release. The design replaces the private-upload part of the #281 safeguards; the rest of them stays.

**Status:** design approved after six review rounds, implementation approved after two, and committed locally on the integration branch for the next release. Not merged or released.

## Short answer {#tldr}

A native restore (`POST ?restore` of a transitioned version) downloads the version from its tier and writes a local copy. Two problems came from how that write was locked and where the copy was kept:

- **Reads and writes waited for the download ([#284](https://github.com/pgsty/silo/issues/284)).** On a deployment with several pools, the released code held the object write lock for the whole download. The first #281 safeguards made a single pool do the same, so that a legal hold set during the download was not overwritten, and they treated a busy object lock as "a restore is running". While an old version restored, every GET, HEAD, and write of the same key, including reads of other versions, waited for the download.
- **A failed ordinary upload got stuck.** The same safeguards kept the restored data in a multipart upload hidden by a private marker. Once an ordinary upload's completion failed after it had staged its metadata, the marker could no longer tell the two kinds apart. The ordinary upload then answered `InvalidUploadID` to every caller and could not be aborted for an hour.

The next release restores in two phases:

1. **Stage without the object lock.** The worker erasure-codes the tier copy into the tmp volume of the version's erasure set, as heal writes the shards it rebuilds. Other requests on the key do not wait.
2. **Commit under a short object lock.** The worker reads the version again, checks that its attempt still owns it and that the content it staged is still the version's content, and publishes the copy drive by drive. A publication that misses the write quorum is first converged under the same lock hold; what that pass cannot settle is retried later under fresh lock holds, and can stay unresolved after the retries or a crash.

A per-version restore lock tells whether a restore runs, instead of the object lock. Multipart completion goes back to its code on main, so ordinary uploads behave as they did before the #281 safeguards.

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | Availability defect in native restore, plus two regressions of the unreleased #281 safeguards. No data loss. |
| Affected | Native restore on every deployment. In the released code, multi-pool restores already held the object lock for the download; the single-pool hold and the stuck ordinary upload exist only on the unreleased integration branch. |
| Not affected | Reads of transitioned objects that do not restore; deployments without a remote tier. |
| Severity | High for availability: one restore of an old version could stall every access to its key for the length of a tier download. |
| Release urgency | Part of the next release. It replaces the private-upload design before that design ships. |
| Remaining effort | Code, two implementation reviews and the full test suite are done. Remote CI and an acceptance run on a distributed deployment remain. |

## Root cause {#root-cause}

Both regressions came from two choices of the first #281 safeguards:

- **The restore reused the public multipart namespace.** A restore upload differed from an ordinary upload only by a key in its `xl.meta`. Completion removes that key, and a failed completion leaves the merged object metadata in the upload directory. After such a failure the two could no longer be told apart, so every staged upload had to be hidden, ordinary ones included.
- **The download held the object lock, and the lock stood for the worker.** A POST inferred that a restore was running from a busy object lock. The lock could therefore not be shortened without first giving the worker another way to say it was alive.

## Design {#design}

### Restore lock, then object lock {#restore-lock}

Each version has a restore lock R, a distributed lock under the system bucket named by bucket, object and version ID. A POST takes R, waiting at most two seconds, and then the object lock O long enough to register its attempt. A new attempt hands R to the worker, which holds it for its whole run. Nothing else takes R, so nothing holds O while it waits for R: the order is always R before O.

R is a liveness hint, not an exclusion. A failed refresh of a distributed lock is treated as an offline node, so during a network partition a second node can take R while the first worker still runs. Correctness therefore depends only on the checks that the commit makes under O: a superseded worker finds that its attempt no longer owns the version and writes nothing. Its staging is private to it and does not disturb the new worker.

A POST that cannot take R within the wait reads the drives without a lock. It answers `409 RestoreAlreadyInProgress` when they show the version ongoing, and a retryable error when they do not or cannot tell. It never starts a second worker.

### Staging outside the object lock {#staging}

The worker stages into the pool that holds the attempt's version and the erasure set the object hashes to. It reads the tier stream, cuts it by the sizes of the version's parts, checks that their sum is the object size, and writes every part to `tmp/<id>/<data dir>/part.N` in the version's own erasure layout, with the streaming bitrot hashes that part uploads and heal use. It holds no object lock.

Each drive is tracked across every part:

- a drive that fails to write, encode or close any part is excluded and gets no further writer;
- before the commit, `CheckParts` runs on each remaining drive and every part must report success, so a drive whose tmp volume was moved away and then recreated by a later write is excluded too;
- when fewer drives than the write quorum remain, staging fails, the attempt clears its own marker, and the client can send the POST again.

Nothing is inlined: a restored copy always gets a new data directory.

### The commit under the object lock {#commit}

The worker then takes O, with the bounded wait of an ordinary operation. If it cannot, it clears its marker and deletes its staging. Under O it re-resolves the pool, which must still be the one it staged into, reads the version's authoritative revision, and checks:

| Check | Required to equal what was staged for | On a mismatch |
| --- | --- | --- |
| Attempt | The attempt owns the version. When the drives disagree on restore fields, its attempt must be the only one in progress. | Stop without writing; a newer attempt is left alone. |
| Version | Version ID, not a delete marker, modification time, ETag, size. | Stop; a deleted version is not revived and a new `null` version is not overwritten. |
| Tier copy | Transition complete, same tier, remote name and remote version. | Stop. |
| Parts | Part numbers and sizes. | Stop. |
| Erasure layout | Algorithm, data and parity blocks, block size, distribution. | Stop. |

Tags, retention, legal hold and replication state may change during the download. The commit takes them from the revision it read under O, so protection acknowledged during the download is kept. A newer delete marker above a version addressed by its ID does not stop the restore; only the disappearance of the version itself does.

### Publication drive by drive {#publication}

The commit publishes on every drive that holds the authoritative revision and kept its staging. It calls the drive's `RenameData` directly, as heal does, never through the erasure layer's rename, whose undo of a replaced version could delete the new data directory and keep metadata that points at it. Each drive gets the version as the commit read it there, with the new data directory, a completed restore, and the same restore fields on every drive. The inline-data marker is removed, because an older restore could have left it behind.

The commit succeeds when the copy reached the write quorum W:

- the replaced data directory is removed only on the drives that returned it, and only when they all returned the same one; otherwise it is left to abandoned-data cleanup;
- when some drives did not get the copy, the version is queued for MRF heal under its normalized version ID (`null` for the null version), and heal brings those drives to the restored revision.

### Convergence below the write quorum {#convergence}

If fewer than W drives confirm the copy, or a result is uncertain, the worker converges the version while it still holds O, and then in bounded in-memory retries, each of which takes O again. Only this worker knows what each drive held before the commit (Sᵢ), what the commit wrote there (Pᵢ), and what a convergence writes (Vᵢ). Every pass first reads every drive's entry and requires each one to equal one of them:

- **any other content stops the convergence**: someone changed the version between two lock holds, for example a key rotation, a tag update, a new attempt or heal; nothing is written, and the error is logged;
- **Pᵢ on W or more drives** means the commit did succeed, for example after a lost response; the version is queued for heal of the remaining drives;
- **otherwise** the worker writes Vᵢ, the revision without any restore fields or inline marker and with the old data directory, to every drive that holds the version. The version is then unrestored and a new POST can restore it. The content is still on the tier.

A convergence deletes no data directory; directories that nothing references any more are left to abandoned-data cleanup. When the retries run out or a pass stops, the worker logs `restore publication did not converge` with the bucket, object, version, attempt and data directory.

### Abandoned-data cleanup across pools {#abandoned-cleanup}

Between moving the data directory into place and renaming `xl.meta`, a drive briefly holds a directory that no metadata references yet. On a single pool, abandoned-data cleanup already takes the object lock of the same domain. With several pools it took only the lock of each pool's set, which O does not exclude. Abandoned-data cleanup now takes the pools-level object lock on several pools, as heal does, so it cannot remove a directory that a commit has moved into place. The same window exists for every PUT's rename and is closed by the same change.

### Multipart goes back to main {#multipart}

The restore exceptions in multipart completion, the private-upload marker, the commit lock of the first design, and the restore exception of the `null`-version Object Lock check are removed. Single-pool completion again takes the upload lock first and the object lock just before it commits, as on main; with several pools it takes the object lock first. An ordinary upload whose completion failed after staging behaves as on main again: it can be completed after its parts are uploaded again, or aborted at once. The inherited failure path described in [A Failed Multipart Completion Can Strand the Upload](/blog/design/multipart-complete-retry/) is unchanged.

## Capability protocol 2 {#capability}

Older servers do not take the restore lock, do not check the attempt under the object lock, and commit differently. Native restore therefore runs only while every server of the cluster positively answers that it speaks protocol 2:

- the server that handles a POST asks every peer, caches a positive answer for up to ten seconds, and answers `503 ServiceUnavailable` without writing anything while any peer does not confirm;
- a queued worker asks again before it starts, because a server may have been replaced by an older binary while the restore waited, and clears its marker when the gate is closed;
- a peer that cannot be reached blocks native restore. It is not proven stopped and may still run an older restore of the same version.

The design document of the two-phase restore said that only POST checks the gate. The code also checks it in the worker, and this record follows the code.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient.** A restore writes the version only in the commit, under O, after the checks above, and only the attempt that owns the version passes them. During the download it holds nothing that other requests wait for. Apart from the exclusions under [Residual limits](#limits), every outcome of the publication ends in one of three states: the copy on a write quorum, the unrestored revision on every drive that holds the version, or a logged stop that writes nothing.

**Necessary.**

- Without the restore lock, the object lock would still have to stand for the worker, and could not be released during the download.
- Without per-drive eligibility and `CheckParts`, a drive whose tmp volume was recreated could take part in a commit without its shards.
- Without the checks under O, a superseded worker, a replaced version or a changed layout could be published.
- Without per-drive `RenameData`, the erasure layer's undo could delete the new data of a replaced version while its metadata still pointed at it.
- Without the convergence, a publication below the write quorum would leave a version that may not be readable. On a 12-drive set with 8 data and 4 parity shards, seven published drives make a metadata read quorum but not enough shards to rebuild the data.
- Without the pools-level lock for abandoned-data cleanup, a multi-pool cleanup could delete a published data directory before its metadata was written.

## Cost and compatibility {#cost}

- **Ordinary requests.** GET, HEAD, PUT and multipart take no restore lock, make no capability check and read nothing more. A restore no longer blocks other requests on its key during the download. The scanner's abandoned-data check on several pools takes the pools-level object lock instead of the lock of each pool's set.
- **The commit.** It holds O for a re-read of the version's metadata and one `RenameData` per drive. That time grows with the size of the version's metadata, the shard and drive count and drive latency, not with the download time. It is not bounded to a fixed number of milliseconds.
- **The restore path.** One `CheckParts` per eligible drive before the commit, the refreshes of the restore lock, and tmp space for one encoded copy until the commit.
- **Duplicate POSTs.** A second POST for a version that is being restored waits up to two seconds for the restore lock before it answers `409 RestoreAlreadyInProgress`.
- **Leftovers.** Directories left by a convergence or by a failed rename wait for abandoned-data cleanup, and a crashed worker's staging waits for the stale tmp cleanup or a restart. Neither blocks a later restore.
- **Format.** No storage format or public API changes. The only new RPC is the capability question. The attempt key in a version's metadata is internal, and older binaries keep it unread.

## Upgrade, rollback and downgrade {#upgrade}

- **Upgrade.** Servers of an older release do not answer that they speak protocol 2, so POST answers `503` until every server runs this release. A marker left without an attempt ID by an older release is taken over by the next POST that gets the restore lock. The [lock-domain fix](/blog/design/single-pool-lock-domains/#upgrade) still requires a drained restart for single pools whose sets use different hosts.
- **Before a downgrade or rollback,** stop new restores and let running workers finish. An older binary does not know the restore lock, and the gate cannot stop a server that was already downgraded.
- **Check the logs** of every server for `restore publication did not converge`, and repair each version they name before the downgrade. The log is positive evidence only: a process that exits during a retry leaves no entry.
- **No existing tool proves that no publication split is left.** A heal dry run is not a certificate: it returns before it checks whether enough shards are available, so it misses a restored majority that cannot be rebuilt. A read-only inspection tool is part of the follow-up on coordinator crashes below.
- After a downgrade, a marker left ongoing answers `409` on the older binary, as upstream does.

## Residual limits {#limits}

- **A coordinator crash during publication.** If the server that runs the worker crashes while it publishes, or the convergence retries run out, the version can be left split: some drives restored, some not. Nothing converges it automatically. The version may not be readable, and a POST may fail, until it is repaired by hand or a later fix detects and converges such splits. Main has the same exposure for a crash during any write.
- **Storage calls that complete late.** A storage RPC can still be executing on a server after its caller returned with a timeout or an error, also while the commit holds O, and land after the check or the convergence. Every write path shares this limit; fencing storage RPCs is a separate item. A late copy on a minority of drives is healed back only when the unrestored revision holds the quorum that heal requires for restore fields.
- **The tier is assumed immutable.** The commit trusts that the same remote name and remote version name the same bytes, as every tier read does. An external writer that overwrites an unversioned tier object is outside this protection.
- **Lost staging.** A server restart moves its tmp volume away, and the stale tmp cleanup removes old directories. A drive affected during the download is excluded from the commit. Staging fails only when fewer eligible drives than the write quorum remain, and the POST can then be sent again. A restart of the coordinating server ends its attempt.
- **Restart.** The convergence and marker-reset retries run in memory. After a restart, a version stays ongoing until a later POST takes it over.

## Verification {#verification}

The regression tests of the two problems fail on the previous integration head, and the multipart one also passes on main:

- `TestRestoreDownloadKeepsKeyAvailable`: while the download of an old version is paused, GET, HEAD, `PutObjectTags` and PUT of the key's hot versions finish in time, on one pool and two, for a single-part and a multipart object;
- `TestMultipartFailedCommitRetriesLikeMain`: after a completion that staged its metadata and then failed, the client uploads its part again and completes, or aborts.

Fault-injection tests cover the protocol:

- `TestRestorePublicationBelowQuorumReverts` and `TestRestorePublicationBelowWriteQuorumOnWideSet` (seven of twelve drives on 8+4 revert, and the test fails when the threshold is relaxed to W-1);
- `TestRestorePublicationUncertainCommits` (lost answers), `TestRestoreConvergenceRetries` and `TestRestoreConvergenceStopsOnOtherWrites`;
- `TestRestoreRemovesOldDataDirOnlyWhenUnanimous`, `TestRestoreDropsStaleInlineMarker` and `TestRestorePublishedRevisionAcrossExpiry`;
- `TestRestoreStagingDropsRecreatedTmp`: on a four-drive set, a drive whose tmp volume was recreated during staging is excluded and the restore succeeds; with two such drives nothing is published;
- `TestRestoreSecondPOSTWhileRunning`, `TestRestoreTargetDeletedDuringDownload` and `TestRestoreTierNotFoundClearsMarker`;
- `TestCheckAbandonedPartsTakesPoolsLock` plants an unreferenced data directory, checks that it survives while the object lock is held and is removed afterwards, and fails without the pools-level lock;
- `TestRestorePartialCommitQueuesNullVersionHeal`: a commit that misses one drive of a noncurrent `null` version queues its heal under `null` and heals it back.

The thirteen tests of the private-upload marker and `TestNativeRestoreConcurrentCompletion`, which completed the restore's upload from a client, were dropped with that design. Four tests were reframed for the new semantics, among them the lock-domain restore test, which now holds the commit instead of the download. The full `./cmd/... ./internal/...` suite, a race selection of the restore, multipart, lock-domain and abandoned-data tests, `go vet` and `golangci-lint` pass.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Maintainer review of the first draft | Requested changes: stage in the existing tmp volume instead of a new namespace, and return multipart to main. |
| Design round 1 | Requested changes. The erasure layer's undo could delete the new data of a replaced version; a recreated tmp volume could publish missing shards; the split and erasure-layout checks were underspecified; the restore lock is only a liveness hint; leftovers and the tier assumption needed stating. All adopted. |
| Design round 2 | Requested changes. Abandoned-data cleanup did not share the object lock across pools; a rollback deleted directories a late write might reference; `WriteMetadata` truncates before it writes; `CheckParts` is a lower bound. Publication moved to per-drive `RenameData`, rollback stopped deleting directories, and cleanup took the pools-level lock. |
| Design round 3 | Requested changes. An old data directory can be shared by a sibling version; success must be judged against the write quorum; an expired inline restore keeps its marker. Recovery after a coordinator crash and storage calls that complete late were excluded by decision and tracked separately. |
| Design round 4 | Requested changes. A retry could overwrite a newer metadata write or a successor attempt; every convergence pass now compares each drive exactly with Sᵢ, Pᵢ and Vᵢ and stops on anything else. The late-RPC exclusion was widened to calls that land while the lock is held. |
| Design round 5 | Requested changes. Once publication started, every failure writes Vᵢ; a heal dry run cannot certify a downgrade; a late minority copy heals back only with a restore-field quorum. |
| Design round 6 | Approved with a nit, adopted: a retry before publication clears the marker, a retry after it only converges. |
| Implementation rounds 1 and 2 | Round 1 found three problems, each fixed with a test: the published revision depended on the clock across the copy's expiry; a tier 404 stranded the marker; the abandoned-data test passed without its fix. Round 2 approved; a 12-drive 8+4 test was added for the write-quorum threshold. |
| Release review (2026-11-06) | Found that a partial commit queued the MRF heal of a `null` version under its raw, empty version ID, while the convergence used `null`; heal already read the empty ID as `null`, and both paths now queue `null`. Also found that the capability comment still described the private upload, and that the design said only POST checks the gate. The comment now describes the restore lock, the attempt fence and the staged commit, and this record follows the code for the gate. |

## References {#references}

- Issue: [#284](https://github.com/pgsty/silo/issues/284)
- [Restored Copies: Expire the Copy, Not the Object](/blog/design/restored-copy-expiry/) ([#281](https://github.com/pgsty/silo/issues/281))
- [Lock Domains of Large Single-Pool Clusters](/blog/design/single-pool-lock-domains/)
- [A Failed Multipart Completion Can Strand the Upload](/blog/design/multipart-complete-retry/): the multipart failure path that this design leaves as on main
- [Heal Dry Run Must Not Delete Data](/blog/design/heal-dry-run-safety/)
- Upstream multi-pool restore lock: [minio/minio#20495](https://github.com/minio/minio/pull/20495)
