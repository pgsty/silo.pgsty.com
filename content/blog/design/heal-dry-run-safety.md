---
title: "Heal Dry Run Must Not Delete Data"
linkTitle: "Heal Dry Run Safety"
date: 2026-11-04
lastmod: 2026-11-06
author: "PGSTY SILO Maintainers"
summary: >
  Why an admin heal run as a dry run can still delete a dangling object version when its metadata has no read quorum, why a five-line early return is the right fix for this release, and why the same fix must also carry the dry-run flag to remote nodes during bucket heal.
tags: [Design, Healing, Data Safety, Operations]
weight: 10
draft: false
url: "/blog/design/heal-dry-run-safety/"
---

This record covers the dry-run part of [PR #280](https://github.com/pgsty/silo/pull/280) by Jasper Bernhardt ([`@dihmandrake`](https://github.com/dihmandrake)), evaluated against main at [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc). The same PR also verifies an object's drives concurrently during deep scans. That optimization is reviewed separately and is outside the scope of this record. CI has not yet run on the PR.

**Status:** fix approved by review and committed locally. Tested together with the other fixes for the next release on one integration branch: the full test suite, the CI race selections and an adversarial review of how the fixes interact all pass. Not merged or released.

## Short answer {#tldr}

The defect is real, and SILO inherited it from upstream MinIO. `mc admin heal --dry-run` is described as "only inspect data, but do not mutate". On main, a dry-run heal still runs the dangling-object purge for any object version whose `xl.meta` has no read quorum. If the drives that lack the metadata all answer "not found" and outnumber the version's parity blocks, `deleteIfDangling` sends a delete of the version to every available drive. Each drive that still holds the version and completes the delete loses it, data directory included, and the heal reports the object as not found. An operator who runs a dry run to assess a damaged cluster destroys the last metadata copies of the objects they are investigating.

The object-heal fix is the five-line early return from PR #280. When metadata quorum fails during a dry run, the heal returns the quorum error, with a set-level result built from the drive states it observed, before the purge. Real heals do not change. It should ship in the next release, split from the parallel verification change, with the contributor credited.

**Our audit found a second dry-run mutation, which PR #280 does not touch, and the fix covers it too.** In a multi-node deployment, bucket heal sends remote nodes only the bucket name and the remove flag. Without the dry-run flag, those nodes run a real bucket heal: they create the bucket directory on drives that lack it, or they remove empty bucket directories when the bucket is missing from every pool. No objects are deleted, but a dry run must not change anything. The fix adds the dry-run flag to the peer message and makes the remote handler honor it, so remote nodes take the same dry-run return as the local node. That is four functional lines, a small helper that builds the peer message, and a regression test.

The PR's second dry-run change reports a drive as `unknown` instead of `ok` when its part verification did not succeed. That is a reporting change, not a safety fix. Applied to dry runs only, it would make a dry run and a real heal report the same drive differently. It can wait for a change that fixes both modes.

## Classification {#assessment}

| Aspect | Assessment |
| --- | --- |
| Nature | The dry-run flag does not reach the dangling-object purge in `erasureObjects.healObject`, or the bucket heal that remote nodes run. Both break the safety promise of admin heal. Inherited from upstream MinIO; no SILO commit introduced or changed either. |
| Who can trigger it | Only an administrator with heal permission, through the admin heal API with `DryRun` set. One example is `mc admin heal --dry-run` (a hidden flag) on a bucket, a prefix, an object, or with `--recursive`. A site-wide dry run also walks `.minio.sys/config`, where the IAM and server configuration objects live. |
| Not affected | The scanner, MRF, background heal, and drive heal never set `DryRun`. SILO Console has no heal call path. Real heals behave as before. |
| What is deleted | The object version or delete marker being healed. Whenever metadata quorum fails and `isObjectDangling` judges the version dangling, a delete is attempted on every available drive, and each successful delete removes the version, data directory included. Drive errors during that delete are audited but not returned. |
| What else changes | In a multi-node deployment, a dry-run bucket heal makes every remote node create missing bucket directories on its drives, or remove empty ones when the bucket is missing from every pool. Directories with contents are never removed. |
| Severity | High. The affected versions are already unreadable through S3, and a real heal (and, in user buckets, a GET or HEAD) purges them by the same rule. The harm is that the operator's inspection tool makes an irreversible deletion that the operator explicitly asked it not to make. The last metadata copies are gone before anyone can decide on a recovery. |
| Release urgency | Blocks the next release. The fix is about ten lines of code, changes only dry runs, and comes with regression tests. |
| Remaining effort | The split and the review are done. Remaining: run CI, and check a dry-run bucket heal on a deployed multi-node cluster. |

## When it happens {#trigger}

Three conditions must hold:

1. A heal with `DryRun` reaches `healObject` for an object version. A heal walk heals each version separately.
2. `objectQuorumFromMeta` fails. Either the read errors do not leave half of the drives with a result, or no parity value is reported by enough readable copies: a parity needs as many agreeing copies as the read quorum it implies, which is the data-block count for an ordinary object. For example, an EC 3+1 version with only two readable copies fails although half of the drives answered.
3. `isObjectDangling` judges the version dangling. At this point no part checks have run, so the verdict requires:
   - at least one valid `xl.meta`;
   - every failing drive to answer "file not found" or "version not found". Any other error (an offline drive, corrupt metadata, a missing bucket directory, a timeout) vetoes the verdict. The heal reads metadata together with the data of small objects, so for a small object that is not inlined, a missing part file also produces "not found" even where `xl.meta` is present;
   - for an object version, more drives without metadata than the version has parity blocks, that is, fewer metadata copies than data blocks. For a delete marker, more than half of the drives without it.

For example, take four drives with EC 2+2. A 1 MiB object loses its `xl.meta` on three drives, while their part files remain. On main, a dry-run heal of that object removes the version from the fourth drive, the only place where its metadata still exists, and reports "object not found".

**Degraded clusters.** An offline drive answers `errDiskNotFound`. That error vetoes the dangling verdict, so a cleanly offline drive prevents the purge rather than causing it; we verified this. The verdict counts only drives that answer "not found", and it cannot tell why they do. Some drives answer "not found" without being authoritative:

- a replaced drive whose bucket directories already exist but which has not yet received the object;
- a drive that lost `xl.meta` while its part files remain. The source comment in `isObjectDangling` names this case as recoverable in principle.

Those are exactly the situations in which an operator reaches for a dry run. Whether the rule is right for real heals is a separate, inherited policy question. A dry run should not apply the rule at all.

## Root cause {#root-cause}

`healObject` copies `opts.DryRun` into `dryRun` and returns before any repair write, as its own comment says: "After this point, only have to repair data on disk - so return if it is a dry-run". The branch that handles a metadata quorum failure comes earlier. It calls `deleteIfDangling` without checking `dryRun`.

`deleteIfDangling` cannot check either. It takes `ObjectOptions`, which has no dry-run field, and it is shared with the GET, HEAD, `CopyObject`, `PutObjectMetadata`, and `PutObjectTags` paths, which purge dangling versions by design. It also fetches the drives from the erasure set itself, so a caller cannot restrict what it touches.

The other `deleteIfDangling` call in `healObject`, in the branch for objects that cannot be healed, comes after the dry-run return and is safe.

## Where the behavior came from {#history}

### Provenance

**Introduced by upstream MinIO, not by SILO.** Both defects come from upstream commits that are ancestors of the SILO fork point ([`27742d469`](https://github.com/pgsty/silo/commit/27742d469), 2025-12-03). They are in the last upstream release before the fork, `RELEASE.2025-10-15T17-29-55Z`, in the archived upstream `master`, and in every SILO release from `RELEASE.2025-12-03T12-00-00Z` through `RELEASE.2026-10-26T00-00-00Z`. We checked each tag: in `healObject` the first `deleteIfDangling` call precedes the dry-run return, and the remote bucket heal message carries no dry-run flag. No SILO commit introduced, widened, or narrowed either defect.

**Object heal.** Upstream once had the guard. Its `purgeObjectDangling` deleted only `if !opts.DryRun && opts.Remove`, from [`db2155551`](https://github.com/pgsty/silo/commit/db2155551) ([#9159](https://github.com/minio/minio/pull/9159), 2020-03-19, `RELEASE.2020-03-19T21-49-00Z`). Two changes took it apart in stages, and a third left the result in `healObject`:

| Step | Commit (PR) | Date | First upstream release | Effect |
| --- | --- | --- | --- | --- |
| The dry-run condition is dropped; `opts.Remove` stays. | [`b7c5e45ff`](https://github.com/pgsty/silo/commit/b7c5e45ff) ([#14053](https://github.com/minio/minio/pull/14053)) | 2022-01-07 | `RELEASE.2022-01-08T03-11-54Z` | A dry run combined with `--remove` deletes. A dry run alone does not. |
| The body is replaced by `deleteIfDangling`, which has no `Remove` gate. | [`f19a414e0`](https://github.com/pgsty/silo/commit/f19a414e0) ([#14273](https://github.com/minio/minio/pull/14273)) | 2022-02-08 | `RELEASE.2022-02-12T00-51-25Z` | **A plain dry run deletes.** This is the release where the reported behavior starts. |
| The call is inlined into `healObject`, before the dry-run return. | [`136d41775`](https://github.com/pgsty/silo/commit/136d41775) ([#15954](https://github.com/minio/minio/pull/15954)) | 2022-10-27 | `RELEASE.2022-10-29T06-21-33Z` | None. The quorum-failure branch stays ahead of the dry-run return. |
| The error returns of the branch are reshaped. | [`3549e583a`](https://github.com/pgsty/silo/commit/3549e583a) ([#19702](https://github.com/minio/minio/pull/19702)) | 2024-05-09 | `RELEASE.2024-05-10T01-41-38Z` | None on the gating. Most lines of the current branch date from this commit. |

**Bucket heal.** Before January 2024 the set-level bucket heal honored `DryRun`. Node-level bucket heal replaced it in [`e31081d79`](https://github.com/pgsty/silo/commit/e31081d79) ([#18612](https://github.com/minio/minio/pull/18612), 2024-01-10, `RELEASE.2024-01-11T07-46-16Z`). Its remote call sends only the bucket name and the remove flag, and the remote handler builds the heal options from those two values. The local implementation of the same call checks `DryRun`, so only the local node honors it. [`ff80cfd83`](https://github.com/pgsty/silo/commit/ff80cfd83) ([#18951](https://github.com/minio/minio/pull/18951), 2024-02-02, `RELEASE.2024-02-04T22-36-13Z`) moved the call to the grid with the same two values. Upstream `master` still has the gap.

**SILO changes** to the heal functions, `cmd/peer-s3-client.go`, `cmd/peer-s3-server.go`, and the heal handler in `cmd/peer-rest-server.go` after the fork:

| SILO commit | Date | SILO releases | Effect |
| --- | --- | --- | --- |
| [`0b1c21cb4`](https://github.com/pgsty/silo/commit/0b1c21cb4), [`2a04d5f48`](https://github.com/pgsty/silo/commit/2a04d5f48) | 2026-10-25 | `RELEASE.2026-10-25T00-00-00Z` only | **Did not affect.** The first added a generation-quorum check to `healObject` after the metadata-quorum branch, and the second removed it the same day. Its place is after the purge, so it neither guarded nor widened it. |
| [`e59a3d938`](https://github.com/pgsty/silo/commit/e59a3d938) | 2026-09-11 | `RELEASE.2026-09-16T00-00-00Z` and later | **Did not affect.** When the caller already holds the namespace lock, `HealObject` keeps that lock's context. |
| [`9b11dc946`](https://github.com/pgsty/silo/commit/9b11dc946) | 2026-09-03 | `RELEASE.2026-09-03T13-18-01Z` and later | **Did not affect.** Import path swap for the error-group helper. |
| [`7ce7fc8d1`](https://github.com/pgsty/silo/commit/7ce7fc8d1) | 2026-10-29 | unreleased | **Did not affect.** The heal walk lists free versions as well. It has no dry-run logic. |

SILO has not changed `deleteIfDangling`, `isObjectDangling`, `remotePeerS3Client.HealBucket`, or `HealBucketHandler`. It has not added a dry-run guard anywhere in this path. [PR #280](https://github.com/pgsty/silo/pull/280) is open and carries the object-heal guard, and the bucket-heal part is only proposed in this record.

**Evidence.** The commit ancestry, first releases, the presence of both defects on every tag, and the absence of SILO changes in these functions were checked with git. The behavior of the 2022 steps (a dry run with `--remove` first, a plain dry run later) is read from the diffs and was not run on those versions. The current behavior is reproduced by the tests under [Verification](#verification).

## Options {#options}

### Option 1: return early in `healObject`

This is PR #280's approach. When `objectQuorumFromMeta` fails and `dryRun` is set, `healObject` returns a `defaultHealResult` built from the errors it observed, together with the quorum error. The change is five lines in one function and affects dry runs only, so real heals behave exactly as today. Its limit is that it protects only this call site. A future dry-run path that calls `deleteIfDangling` somewhere else would need its own guard.

### Option 2: pass the dry-run flag into `deleteIfDangling`

`deleteIfDangling` would gain a parameter or an `ObjectOptions` field, so that it can reach a verdict without deleting. It could also return a "would purge" verdict for the report. The cost is that all six callers change, and four of them are object read and metadata-update paths that have no notion of a dry run. A future caller can also forget to pass the flag, just as it can forget the early return. That is a lot of churn for a small robustness gain. The "would purge" report belongs to a redesign of dry-run reporting.

### Option 3: a central guard

Dry-run heals would run against read-only wrappers of the drives, so that every write fails. This is the only option that catches future mistakes by construction. But `StorageAPI` has dozens of methods, `deleteIfDangling` fetches its drives from the erasure set rather than from its caller, and the bucket-heal gap is in the peer RPC layer, which such a wrapper would not cover. It is too large for a release fix.

A cheap version of the same idea works in tests. The PR's synthetic test drives embed a nil `StorageAPI`, so any mutation the test does not expect panics. The regression tests keep that pattern.

### Bucket heal on remote nodes

There are two ways to stop remote nodes from mutating during a dry run:

- **Carry the flag.** Send the dry-run flag in the peer message and honor it in the remote handler. Remote nodes then take the same early return that the local node takes. The message shape, the handler, and the error reduction stay the same, and remote nodes can report their state once dry-run bucket reporting is filled in.
- **Skip the call.** Have `S3PeerSys.HealBucket` not call remote nodes during a dry run. This also protects against older nodes during a rolling upgrade, but it gives up the remote half of any future dry-run report, and it adds a dry-run special case to the fan-out.

We carry the flag. Before the fix, every node already behaved as if the flag were false. During an upgrade, a mixed cluster behaves no worse than today, and once every node runs the fix, the gap is closed.

### The reporting change

In a dry-run deep scan, the PR reports a drive as `unknown` when its metadata was read but part verification did not succeed for a reason other than missing or corrupt parts. Such reasons include a drive that went offline during the check, a missing volume, a deadline, a cancellation, or denied access. On main, that drive is reported as `ok` in both modes, and repair decisions ignore these results.

The PR changes dry runs only. Its own test expects `unknown` from a dry run and `ok` from a real heal for the same state. `mc admin heal` counts only `ok` drives when it colors an object and when it groups objects by online drives. The same object would therefore look worse in a dry run than in the real heal that follows.

Reporting an unverified drive as `ok` is a real accuracy problem: an integrity audit can claim a clean result for data it did not check. But the problem exists in both modes, and it neither deletes nor changes data. It should be fixed for both modes together, including the "quorum loss" detail that the heal sequence derives from the same drive states.

**Recommendation:** for this release, Option 1 for object heal, and carry the flag for bucket heal. Defer the reporting change.

## Proposed fix {#fix}

The fix has two parts. Part 1 is the contributor's change from PR #280. Part 2 comes from the maintainer audit.

### Part 1: object heal returns before the dangling purge

**Code.** Take PR #280's first hunk in `healObject` unchanged:

```go
readQuorum, _, err := objectQuorumFromMeta(ctx, partsMetadata, errs, er.defaultParityCount)
if err != nil {
	if dryRun {
		// A metadata quorum failure must not delete dangling data in dry-run.
		return er.defaultHealResult(FileInfo{}, storageDisks, storageEndpoints,
			errs, bucket, object, versionID), err
	}
	m, derr := er.deleteIfDangling(ctx, bucket, object, partsMetadata, errs, nil, ObjectOptions{
		VersionID: versionID,
	})
	// unchanged
```

In a dry run, the set-level result maps each drive's read error to a drive state, for example `missing` where `xl.meta` is absent. This call passes `FileInfo{}`, so the result carries size zero and the default parity counts. The error is the one `objectQuorumFromMeta` returned, converted by `toObjectErr`: version or object not found when most drives say so, the corruption error when most copies are corrupt, or insufficient read quorum. A real heal still discards the per-drive errors before it reports a quorum failure, as it does today.

Not all of this reaches the admin report. When every pool answers not found, which is the common dangling case, `erasureServerPools.HealObject` replaces the set results with an empty item, so the report shows the not-found error without per-drive states, as it did on main after the purge. The observed states are visible when the error is something else, for example corrupt metadata, or insufficient read quorum. The latter also covers some dangling versions: an EC 3+1 version with two readable copies and two "not found" answers is dangling, and its dry run now reports insufficient read quorum with all four drive states.

**Tests.** Take the three PR tests that do not depend on parallel verification, together with their helpers:

- `TestNativeAuditDryRunPreservesFaults` uses synthetic drives and covers a metadata quorum failure, corrupt metadata, missing or corrupt parts, corrupt inline data, and a delete marker that lacks quorum;
- `TestNativeAuditDryRunPreservesDanglingFiles` uses real drives. It removes `xl.meta` from three of four drives and checks that a dry run leaves every file unchanged;
- `TestNativeAuditNonDryRunStillDeletesDangling` is the control: the same fixture without `DryRun` still reaches the purge.

Three small adaptations:

- `TestNativeAuditDryRunPreservesFaults` asserts the delete counter before the reporting assertions, so that on unfixed code the failure names the deletion;
- it asserts the converted error for each quorum case, version not found or the corruption error, instead of a check against `errFileNotFound` that could not fail after `toObjectErr`;
- the synthetic drive drops its `CheckParts` stub, which only the PR's parallel-verification and reporting tests use.

### Part 2: remote nodes honor the dry-run flag in bucket heal

**Code.** The fix adds a `peerS3BucketDryRun = "dry-run"` key next to `peerS3BucketDeleted`. `remotePeerS3Client.HealBucket` builds its message with a small encoder that adds the key, and `HealBucketHandler` reads it into `madmin.HealOpts.DryRun`:

```go
// peer-s3-client.go
func healBucketPeerMSS(bucket string, opts madmin.HealOpts) *grid.MSS {
	return grid.NewMSSWith(map[string]string{
		peerS3Bucket:        bucket,
		peerS3BucketDeleted: strconv.FormatBool(opts.Remove),
		peerS3BucketDryRun:  strconv.FormatBool(opts.DryRun),
	})
}

// peer-rest-server.go, HealBucketHandler
dryRun := mss.Get(peerS3BucketDryRun) == "true"
res, err := healBucketLocal(context.Background(), bucket, madmin.HealOpts{
	Remove: bucketDeleted,
	DryRun: dryRun,
})
```

`healBucketLocal` already returns before any `MakeVol` or `DeleteVol` when `DryRun` is set, so it needs no change. The RPC handler, its registration, and its result type also stay as they are.

**Test.** `TestPeerHealBucketDryRun` starts two grid managers and registers the peer handler on one of them. It then calls `remotePeerS3Client.HealBucket` on the other, so the request takes the real client, the grid connection, and the handler, against a four-drive set from which the bucket directory has been removed on one drive. Two dry-run requests, one with and one without `Remove`, must neither recreate the missing directory nor remove the empty ones. Two controls then prove that the fixture reaches both writes: a message without the dry-run key, as an older node sends it, recreates the directory, and a real heal with `Remove` removes the empty directories. The test uses no new identifiers, so it compiles on main, where it fails at the first dry-run assertion.

**Other peer heal calls.** We checked them all, and none has the same gap:

- format heal saves `format.json` only from the coordinating node and only under its own dry-run check. It opens the drives first, with the normal storage initialization, which runs before that check; see [Residual limits](#limits). The admin heal sequence does not queue format heal in this tree;
- the background heal status call is read-only;
- an admin heal request is proxied to another node only to poll an existing sequence by its token, never to start one.

### Delivery

- Split the dry-run hunk and those tests into their own commit and PR, separate from the parallel verification change. That change needs its own review, of I/O concurrency on slow drives and of cancellation, and its own CI.
- Preserve the contributor's credit. The production hunk is unchanged from the contributor's signed-off commit, but the tests are an adapted subset, so the split is a maintainer commit that carries a `Co-authored-by` trailer for Jasper Bernhardt and references PR #280.
- PR #280 then continues with the parallel verification and, if wanted, a reporting change that covers both modes.
- The PR description states that the implementation and tests were AI-written and that the contributor could not establish their correctness independently. The dry-run hunk is small enough for maintainers to verify it independently, as described below, and this record is based on that verification, not on the PR's own claims.
- Ship Part 2 in the same PR as a separate maintainer commit. It contains no contributor code, so the contributor credit stays on Part 1.

## Why it is sufficient and necessary {#sufficiency}

We audited every place where an admin dry-run heal can change data:

| Path | Possible mutation | Under `DryRun` on main | With the fix |
| --- | --- | --- | --- |
| `healObject`, metadata quorum failure | `deleteIfDangling` (`DeleteVersion` on all drives) | **Reached** | Not reached |
| `healObject`, objects that cannot be healed | `deleteIfDangling` | After the dry-run return | Unchanged |
| `healObject`, repair | Shard writes to the temporary area, `RenameData`, deletion of remote data directories, temporary cleanup | After the dry-run return | Unchanged |
| `HealObject`, deep-scan retry after bitrot | Runs `healObject` again with the same options | Inherits the above | Inherits the fix |
| `healObjectDir` | Deletes a dangling directory; `MakeVol` for missing directories | Delete needs `!dryRun && remove`; `MakeVol` comes after the dry-run return | Unchanged |
| `HealObjects` walk | `CheckAbandonedParts` | Needs `Remove && !DryRun`, and `checkAbandonedParts` checks `DryRun` again | Unchanged |
| Site-wide heal of `.minio.sys/config` | Same `healObject` path | **Reached** (the read path's purge skips `.minio.sys`; heal does not) | Not reached |
| Bucket heal, local node (`healBucketLocal`) | `DeleteVol`, `MakeVol` | Returns before any mutation | Unchanged |
| Bucket heal, remote nodes | `MakeVol`, non-forced `DeleteVol` | **Reached**: the flag is not sent | Not reached: the flag is sent and honored (older nodes still ignore it during an upgrade) |
| `HealFormat` | Writes `format.json` and replaces drives; drive initialization can create internal directories or migrate an old `format.json` | Saves under `if !dryRun`, but initialization runs before that check. The admin heal sequence does not queue it; the only caller in this tree is the new-drive monitor, with `dryRun` false | Unchanged |
| Site-wide heal, bucket listing | `ListBuckets` fills in creation times. For a bucket whose metadata is not cached, that loads bucket metadata through the ordinary object read path, which can migrate legacy bucket configuration files and queue MRF repair of `.metadata.bin` | Reached, through the same load the server attempts at startup and in its periodic metadata refresh | Unchanged; see [Residual limits](#limits) |
| Heal metadata reads (`ReadVersion`), `CheckParts`, `VerifyFile`, heal walks | None | Read-only | Unchanged |

The heal paths themselves queue no MRF entries; only the bucket-metadata load above can. The only side effect of the reached purge outside the drives is a `DeleteDanglingObject` audit entry, which is written when audit logging is configured.

**Sufficient.** With both parts, once every node runs the fix, an admin dry-run heal no longer runs heal's own mutations. Object heal returns before the purge. Bucket heal returns before `MakeVol` and `DeleteVol` on every node, not only on the node that coordinates the heal. Two pre-existing effects outside heal's repair logic remain and are listed under [Residual limits](#limits): the bucket-metadata load during a site-wide listing, and drive initialization in a directly invoked format heal.

**Necessary.**

- In a dry run, the quorum-failure branch is the only object-heal mutation that runs before the dry-run return. Without Part 1, the purge stays reachable.
- Remote bucket heal is the only other heal mutation that an admin dry run reaches. Without Part 2, every remote node of a multi-node deployment still heals bucket directories during a dry run.
- The reporting change is not needed for safety.

**Deliberately excluded:**

- the parallel verification in `checkObjectWithAllParts`;
- the `unknown` reporting change;
- the dangling-purge policy for real heals and read paths.

## Cost and compatibility {#cost}

- No API, configuration, metric, storage-format, or dependency change. Real heals are unchanged.
- The bucket heal peer message gains one optional key, `dry-run`. The message is a string map, and the grid codec decodes every key it receives, so a key unknown to the receiver is carried and ignored. We verified that a message with the new key round-trips through the codec and that the old handler accepts it. There is no new RPC handler and no handler version change.
- Rolling upgrade:
  - **A new node calling an old node.** The old node ignores the key and runs a real bucket heal, exactly as today.
  - **An old node calling a new node.** The message has no key, the new node reads `false`, and it runs a real bucket heal, exactly as today.
  - A dry-run bucket heal leaves bucket directories alone only after every node runs the fix. A mixed cluster is never worse than today.
- Dry-run results change as follows:
  - a dangling version is no longer deleted;
  - at set level, drives report the observed state instead of `ok`. The admin report shows this only when the error is not a not-found, because pool aggregation drops the set results when every pool answers not found;
  - the error is the converted `objectQuorumFromMeta` error instead of the result of a purge;
  - dry runs no longer emit `DeleteDanglingObject` audit entries;
  - remote nodes no longer change bucket directories, and their part of a dry-run bucket report is now empty, like the local part.
- Rollback restores the old behavior. No migration is needed in either direction.

## Residual limits {#limits}

- **Mixed-version clusters.** Until every node runs the fix, a dry-run bucket heal still makes older nodes create missing or remove empty bucket directories. Release notes should say that a dry run leaves bucket directories alone only after the upgrade completes.
- **A site-wide dry run loads bucket metadata.** Its bucket listing fills in creation times. For a bucket whose metadata is not in the cache, that is an ordinary metadata load, the same one the server attempts at startup and in its periodic refresh, which starts 15 minutes after the previous pass ends: it can migrate legacy bucket configuration files into `.metadata.bin` and queue MRF repair of a missing `.metadata.bin` copy. No object data is touched. The server's own loads make the same changes, but with no guaranteed time by which a migration or repair completes. A dry-run listing that skips creation times would avoid the load; that is a follow-up.
- **Format heal initializes drives before its dry-run check.** Opening the drives can create internal directories and migrate an old `format.json`. The admin heal sequence does not queue format heal in this tree, so an admin dry run does not reach it. A read-only format check would need read-only drive initialization.
- **A dry-run bucket heal reports no drive states.** `healBucketLocal` returns before it attaches the states it observed. With the fix, this is true on every node, not only on the local one, so a dry run gives a bucket summary with no per-drive detail. Filling in the observed states before the dry-run return belongs to the reporting follow-up.
- **Past dry runs cannot be undone.** If dry-run heals were run against damaged objects before this fix, any versions they purged are gone. When audit logging is configured, they appear as `DeleteDanglingObject` entries whose caller tag points to the heal code.
- **A dry run does not say "would purge".** After the fix, a dangling version shows up in the admin report either as a not-found error without drive states, when every pool answers not found and aggregation drops the set result, or as an insufficient-read-quorum error with drive states. In both cases the set result carries size zero and default parity counts. It is not flagged as something a real heal would delete. A "would purge" verdict is a candidate for the reporting follow-up.
- **Unverified drives are still reported as `ok`**, in both modes, until the reporting follow-up.
- **The real-heal dangling policy is unchanged.** It counts "not found" answers from drives that may not be authoritative. Reviewing that policy is separate work.

## Verification {#verification}

All runs used focused `go test -run` selections with `-p 2` and the `kqueue,dev` tags. "Main" means a disposable worktree at `69fcf50cd` that contains only the new test files.

**Executed, the defect on main.**

- A dry-run `HealObject` on synthetic drives, three of four answering "version not found", issues a `DeleteVersion` call to every drive, both for an object version and for a delete marker.
- With one of those drives offline instead, a real heal issues none, which confirms the offline veto.
- On real drives, a dry-run heal removes the last surviving `xl.meta`.
- Passed to the peer handler, a message with only the bucket name and the remove flag, the shape main's remote client sends for a dry-run request, recreates a missing bucket directory. The local `healBucketLocal` with `DryRun` does not. PR #280's changes make no difference.

**Executed, the committed tests.**

- On main:
  - `TestNativeAuditDryRunPreservesFaults` fails in its metadata-quorum and delete-marker subtests at the deletion assertion, and in its corrupt-metadata subtest at the reporting assertion: there the purge is vetoed, but main reports every drive as `ok`.
  - `TestNativeAuditDryRunPreservesDanglingFiles` fails: after the dry run, the object's directory is gone from the drive that held the last `xl.meta`.
  - `TestPeerHealBucketDryRun` compiles and fails at its first dry-run assertion: the remote node recreated the missing bucket directory.
  - The controls pass: `TestNativeAuditNonDryRunStillDeletesDangling`, and the missing-part, corrupt-part, and corrupt-inline subtests.
- With the fix, all of them pass, also with `-race -count=3`.
- Mutation checks on `TestPeerHealBucketDryRun`: the test fails if the client encoder omits the key, and it fails if the handler ignores the key.
- The new tests run together with the existing `TestHealing*`, `TestHealObject*`, `TestHealCorrectQuorum`, `TestHealLastDataShard`, `TestHealEmptyDirectoryErasure`, `TestIsObjectDangling`, and `TestFreeVersionHealObjects` tests in one process with `-race -count=2`, and all pass. The existing `TestPeer*`, `TestErasureHeal`, and grid package tests also pass without the race detector. `TestErasureHeal` panics in a ring buffer under the race detector on main as well; that is unrelated to this change.
- `gofmt` and `go vet ./cmd` are clean.

**Executed by the adversarial review.**

- With the new key, a message round-trips through the grid codec, and main's handler accepts it and ignores it: it recreates the missing directory and removes the empty ones. This is the "new node calling an old node" case.
- An object present in two pools is still healed through both pools; a healthy second pool still wins the aggregation.
- An empty dry-run result from every peer reduces without error, and the fan-out keeps `DryRun` while it rewrites `Remove` and `Recreate`.
- A site-wide dry run with an empty bucket-metadata cache migrates a legacy bucket configuration and queues MRF repair of a missing `.metadata.bin` copy, on main and with the fix. Skipping creation times in the listing avoids both.
- A directly invoked `HealFormat` dry run recreates a missing `.minio.sys/config` directory, on main and with the fix.
- At admin level, a dangling dry run reports an empty item with a not-found error; at set level, the same call reports three `missing` drives. An EC 3+1 version with two readable copies reports insufficient read quorum with four drive states, where main purged it.
- A site-wide dry-run sequence heals `.minio.sys/config` objects. With the fix, a dangling configuration object keeps its last `xl.meta`.

**Reasoned from code, not executed:**

- that only the admin heal API sets `DryRun`;
- that main's remote client sends only those two fields;
- that no other peer heal call drops the flag;
- how `mc admin heal` uses drive states;
- the upstream history.

**Not run:**

- the full `./cmd` suite;
- remote CI;
- a deployed multi-node cluster and a mixed-version upgrade. The peer test uses a real grid connection, but between two managers in one test process;
- an end-to-end `mc admin heal --dry-run`;
- the parallel verification tests.

**Integration.** The fix was cherry-picked onto one integration branch for the next release, on top of #278 and #281 and together with the lock-domain, #259, #285 and Console fixes. Every pick applied without conflicts. On that head the full `go test ./cmd/... ./internal/...` suite passes, as do the CI race-detector selections and a race selection that covers every new test. An adversarial review of the combination found no defects. It checked lock domains, cleanup paths and purge against restore with executed probes.

## Review history {#review}

| Round | Outcome |
| --- | --- |
| Adversarial review, round 1 | Requested changes. Five findings: a site-wide dry run's bucket listing loads uncached bucket metadata, which can migrate legacy bucket configuration and queue MRF repair (pre-existing); the real-drive test fixture leaves background workers and globals behind; a directly invoked format heal initializes drives before its dry-run check (pre-existing); pool aggregation drops the set-level drive states when every pool answers not found (pre-existing); one error assertion in the tests could not fail. Also eleven corrections to this record. Outcome: the listing effect was disputed as a blocker for this change, because the server attempts the same load at startup and in its periodic refresh, and it is documented with a named follow-up. The fixture finding was disputed: the tests follow the fixture convention of the existing heal tests, and a combined race run with those tests passed. The format and aggregation findings are documented. The assertion now checks the converted error for each case. All record corrections were applied. |
| Adversarial review, round 2 | Approved with nits. The reviewer withdrew the listing and fixture findings as release findings for these two parts. Two wording nits, that some dangling versions report insufficient read quorum with drive states, and that the periodic refresh has no completion bound, plus three more record corrections. All applied. |

## References {#references}

- Contributor PR: [#280](https://github.com/pgsty/silo/pull/280)
- Evaluated base: [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc)
- Upstream history: [minio/minio#14053](https://github.com/minio/minio/pull/14053), [minio/minio#14273](https://github.com/minio/minio/pull/14273), [minio/minio#15954](https://github.com/minio/minio/pull/15954), [minio/minio#18612](https://github.com/minio/minio/pull/18612)
- Related: [Object Healing](/operations/concepts/healing/), [`mc admin heal`](/reference/minio-mc-admin/mc-admin-heal/)
