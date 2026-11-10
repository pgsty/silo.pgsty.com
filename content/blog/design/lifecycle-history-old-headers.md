---
title: "Lifecycle History: One Version Under the Headers of Two Releases"
linkTitle: "Lifecycle History and Old Headers"
date: 2026-11-10
lastmod: 2026-11-10
author: "PGSTY SILO Maintainers"
summary: >
  Why lifecycle expiry of data written by a MinIO release before 2024-04-28 is refused for good once some drives of its erasure set were replaced, and why taking two release-dependent header fields out of the revision key is the minimum complete repair.
tags: [Design, Lifecycle, Erasure Coding, Compatibility]
weight: 10
draft: false
url: "/blog/design/lifecycle-history-old-headers/"
---

This record covers a defect found in a maintainer review of `RELEASE.2026-11-09T00-00-00Z` ([d99829238](https://github.com/pgsty/silo/commit/d998292387ccf1d2907749e0fb1575ef5fb93fda)). That release introduced it with [9f7b49369](https://github.com/pgsty/silo/commit/9f7b49369d4cbc1a5506af4bff05df05c8c8b6d3), part of the multi-pool lifecycle fix ([#278](https://github.com/pgsty/silo/issues/278)). The fix is [PR #332](https://github.com/pgsty/silo/pull/332); there is no separate GitHub issue.

**Status:** the fix and its regression tests are in [PR #332](https://github.com/pgsty/silo/pull/332), approved by an adversarial review in its second round; the first round changed the fix, see [Review history](#review). Not merged or released.

## Short answer {#tldr}

Since 20261109, a lifecycle expiry that depends on the other versions of a key first reads the key's version history from the drives of its erasure set, and accepts a version only when enough drives hold the same revision of it. A revision was identified by the version's header as the drive stores it, plus a digest of its metadata.

The stored header is not the same on every drive of an old version. A drive keeps the header that the release which wrote the version there stored, and MinIO releases before `RELEASE.2024-04-28` stored a header without erasure-coding fields. When a drive is replaced, heal writes the version to it with a current header and leaves the other drives alone. Reads and heal take both headers for the same version. The history did not: it counted two revisions, and when neither was on enough drives it refused the key.

The refusal is permanent. Every scanner cycle retries the expiry and fails the same way, GET works, and heal reports nothing to repair. No data is lost or deleted; versions that should expire stay.

The fix adds three lines to one function, `versionRevision` in `cmd/erasure-server-pool-lifecycle.go`: the revision key takes the two header fields that depend on the writing release as the current release computes them from the version's metadata, instead of from the drive. Upgrading is the whole remedy; nothing on disk changes.

## Classification {#assessment}

| Aspect               | Assessment                                                                                                                                                                                                                                                                    |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Nature               | Regression in `RELEASE.2026-11-09T00-00-00Z`: the new version history identifies a revision too strictly. It fails closed.                                                                                                                                                    |
| Affected deployments | Data taken over from MinIO whose version headers were stored by a release from `RELEASE.2021-11-24` until before `RELEASE.2024-04-28`, in an erasure set where some drives, but not nearly all, were replaced and healed since.                                               |
| Affected expiries    | With several pools: every ILM expiry in a versioned or versioning-suspended bucket, except the expiry of a restored copy. With any number of pools, one included: `ExpiredObjectAllVersions`, `DelMarkerExpiration`, and batch expiration that purges all versions.           |
| Not affected         | Data written by SILO or by MinIO from `RELEASE.2024-04-28` on; sets without a healed drive; on a single pool, the expiry of one version or one delete marker (`Expiration`, `NoncurrentVersionExpiration`, `ExpiredObjectDeleteMarker`); reads, writes, heal and replication. |
| Data safety          | Nothing is deleted or hidden. The affected versions stay readable.                                                                                                                                                                                                            |
| Severity             | High where it applies: the rules silently stop for the affected keys, storage grows and retention periods are not enforced. Low reach: it needs old data and a particular share of healed drives.                                                                             |
| Effort               | Small: one function, no storage RPC, no on-disk format, no configuration.                                                                                                                                                                                                     |
{.wide .expand}

## When it happens {#trigger}

Three conditions must hold together:

1. **An old header.** The version's entry in `xl.meta` was stored by a MinIO release from `RELEASE.2021-11-24`, the first with a per-version header, until before `RELEASE.2024-04-28`, the first to put the erasure coding into it. Later releases rewrite `xl.meta` without touching the headers of the versions they do not change, so a version keeps its old header while newer versions are added to the key.
2. **A partial heal.** Some drives of the erasure set were replaced, or lost the key for another reason, and heal wrote the version to them. These drives hold a current header.
3. **Neither group is large enough.** A revision counts when it is on more than half of the drives of the set and on the read quorum of the version: `max(n/2+1, n − parity)` drives.

| Erasure set     | Drives a revision needs | Refused when this many drives were healed |
| --------------- | ----------------------- | ----------------------------------------- |
| 16 drives, EC:4 | 12                      | 5 to 11 (reproduced)                      |
| 12 drives, EC:4 | 8                       | 5 to 7                                    |
| 8 drives, EC:4  | 5                       | 4                                         |
| 4 drives, EC:2  | 3                       | 2                                         |
| 2 drives        | 2                       | 1                                         |
{.wide .expand}

Only the first row was run; the others follow from the same rule. Small sets are hit soonest: one replaced drive in a two-drive set is enough.

What an operator sees for an affected key:

- `minio_ilm_expiry_incomplete_total{reason="history_unavailable"}` grows with every scanner cycle;
- the ILM trace reports `result=failed` with that reason, the audit log has an `ILMExpiry` entry tagged `ilm-incomplete-reason=history_unavailable`, and the server log says the expiry was not done because storage resources are insufficient for the write operation;
- GET and HEAD of the version succeed, and a heal of the key reports every drive as healthy.

## Root cause {#root-cause}

Line numbers are for [d99829238](https://github.com/pgsty/silo/commit/d998292387ccf1d2907749e0fb1575ef5fb93fda).

1. `objectVersions` reads `xl.meta` from every drive of the set and passes the version lists to `authoritativeHistory` (`cmd/erasure-server-pool-lifecycle.go:74-133`).
2. `authoritativeHistory` groups the drives of each version by `versionRevision` and accepts the largest group only when it has the majority and the read quorum (`:342`). Any version without such a group refuses the whole key with a read-quorum error.
3. `versionRevision` starts the key with the stored header, unchanged: `key := revisionKey{header: ver.header}` (`:222`). Only a legacy (`xl.json`) version had its signature replaced, because that signature covers per-shard checksums.
4. The version header has seven fields. Two of them depend on which release stored it:

| Field                          | What differs between releases                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EcN`, `EcM`                   | Added to the header by upstream [#19534](https://github.com/minio/minio/pull/19534), first released in `RELEASE.2024-04-28`. A header stored before reads as 0/0.                                                                                                                                                                                                                                          |
| `Signature`                    | A 32-bit hash of the version's metadata. Until upstream [#14125](https://github.com/minio/minio/pull/14125), first released in `RELEASE.2022-01-25`, it counted part ETags that are all empty, and a version written by a plain PUT before `RELEASE.2021-11-24` has such ETags. A header that one of the releases in between stored for such a version carries a signature that no later release computes. |
| `VersionID`, `ModTime`, `Type` | The same on every drive.                                                                                                                                                                                                                                                                                                                                                                                   |
| `Flags`                        | Derived from the metadata. One flag, whether a transitioned version uses its data directory, also depends on whether a restored copy had expired when the drive wrote the entry. It does not depend on the release and stays in the key as stored; see [Options](#options).                                                                                                                                |
{.wide .expand}

5. Heal decides by the decoded metadata, not by the header. It writes the version to the drives that lack it, with the header its own release computes, and finds the other drives healthy. Nothing rewrites their headers afterwards.

The rest of the server already treats these drives as one version. `matchesNotStrict` ignores the signature, `matchesEC` accepts a header without erasure coding next to one with it, and the listing comparison `metaCacheEntry.matches` compares "without considering EC" when only one side has it. The listing tolerance came with the upstream commit that added the fields, and `matchesEC` followed in upstream [#20351](https://github.com/minio/minio/pull/20351). The revision key added in 20261109 did not carry it over.

Everything the two fields say is also in the digest: the erasure coding is part of the version's metadata, and the signature is a weaker hash of the same metadata. Leaving them in the key added no information; it only tied the key to the release that wrote the drive.

## Where the behavior came from {#history}

### Provenance {#provenance}

**Introduced by SILO, in `RELEASE.2026-11-09T00-00-00Z`.** No earlier SILO release and no upstream MinIO release has the authoritative history or the revision key.

| Ingredient                                                     | Commit                                                                                                  | PR                                                  | First release                  |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ------------------------------ |
| Per-version header in `xl.meta`, with a signature              | [faf013ec8](https://github.com/pgsty/silo/commit/faf013ec84051b92ae0f420a658b8d35bb7bb000) (Klaus Post) | [#13573](https://github.com/minio/minio/pull/13573) | `RELEASE.2021-11-24T23-19-33Z` |
| Signature no longer counts empty part ETags                    | [0012ca8ca](https://github.com/pgsty/silo/commit/0012ca8ca5f816019d83c39b9018dc7992377e3b) (Klaus Post) | [#14125](https://github.com/minio/minio/pull/14125) | `RELEASE.2022-01-25T19-56-04Z` |
| Erasure coding in the header; comparisons tolerate its absence | [5f774951b](https://github.com/pgsty/silo/commit/5f774951b1cc464b3d8ebe39750fde1a2d09f23d) (Klaus Post) | [#19534](https://github.com/minio/minio/pull/19534) | `RELEASE.2024-04-28T17-53-50Z` |
| Revision key that includes the stored header                   | [9f7b49369](https://github.com/pgsty/silo/commit/9f7b49369d4cbc1a5506af4bff05df05c8c8b6d3) (SILO)       | part of the #278 fix                                | `RELEASE.2026-11-09T00-00-00Z` |
{.wide .expand}

## Options {#options}

### Option 1: rebuild the whole header from the metadata {#option-1}

The first suggestion: compute the header from the decoded version, as `restoreNeutralRevision` does for a version without its restore fields. Rejected. The flag that tells whether a transitioned version uses its data directory is computed from the restore expiry date and the clock. A key rebuilt this way changes when a restored copy expires, and the native restore compares keys it took before a commit with keys it reads after it. `fileInfoRevisions` accepts both values of the stored flag for exactly this reason, and relies on the key carrying the flag as stored.

### Option 2: take the erasure coding from the metadata only {#option-2}

Two lines, and it repairs the reported case. Insufficient: a version written by a plain PUT before `RELEASE.2021-11-24`, whose key was rewritten by a release before `RELEASE.2022-01-25` and partly healed later, still has two signatures on its drives and stays refused. The unit test for that header fails with this option alone.

### Option 3: rewrite old headers on the drives {#option-3}

Let heal or the scanner bring every drive to the current header. Rejected: it rewrites the metadata of every old object to repair a comparison, it makes heal find work on healthy drives, and until it has finished the expiry stays refused.

### Option 4: drop the header from the key {#option-4}

Identify a revision by the digest alone. Rejected: the stored data-directory flag is not in the digest, and the merge that orders the history needs one header for all drives of a revision. It is a larger change for the same result.

### Option 5: take the signature from the digest {#option-5}

The first version of this fix: the erasure coding from the metadata, and the signature from the digest for every version, as the key already does for a legacy version. Rejected after review. The signature is also what orders two versions of the same modification time in the merge, and each drive's version list keeps the order the drive gave it. With two such versions, each on 12 of 16 drives, 20261109 accepted all 40 layouts tried and this option refused 21.

### Option 6: compute both fields as the current release does {#option-6}

The erasure coding and the signature of an object version, computed from its decoded metadata by the functions that write a header today. For a version that a current release wrote, the result is the stored header, so nothing changes for it. Chosen.

## Proposed fix {#fix}

In `versionRevision`, after the digest of a decodable version is computed:

```go
switch v.Type {
case LegacyType:
	copy(key.header.Signature[:], key.digest[:])
case ObjectType:
	key.header.Signature = v.ObjectV2.Signature()
	key.header.EcN, key.header.EcM = uint8(v.ObjectV2.ErasureN), uint8(v.ObjectV2.ErasureM)
}
```

The legacy case is unchanged; the object case is new. A delete marker keeps its stored header: it has no erasure coding under any release, and no release changed how its signature is computed for the same metadata. A version whose metadata does not decode keeps its stored header and still matches only the same bytes.

The history that `authoritativeHistory` returns carries the header of the accepted key on every drive, as before. Nothing is written to a drive, and no key is stored anywhere: every read computes its keys again.

## Why it is sufficient and necessary {#sufficiency}

- **Sufficient.** Of the header fields, only the erasure coding and the signature depend on the release that stored them, and the key now has both as the current release computes them. The same function serves both readers of revision keys: the lifecycle history, and the generation a native restore selects. With the fix, the history accepts an old version on any number of healed drives, from none to all.
- **Necessary.** With the erasure coding alone, the old-signature header stays refused for 5 to 11 healed drives of 16. With the signature alone, the reported case stays refused.
- **Safe.** The digest covers the erasure coding and everything the signature hashed, so two revisions that differ in either still have two keys; a control test checks another erasure coding under the same header. A real split, such as a metadata update that reached half of the drives, is refused as before.
- **Unchanged for current data.** The key of a version that a current release wrote carries its header exactly as stored; a control in the end-to-end test checks this on written objects. For such data the history decides as 20261109 does.
- **Minimal.** One function and three added lines. No storage RPC, no on-disk format, no configuration, no change to heal or to any read path.

## Cost and compatibility {#cost}

- Cost: one more signature for each object version of each drive, a second encoding and a 64-bit hash of metadata the digest already reads. No extra I/O.
- On disk: nothing changes. Old headers stay as they are.
- Rolling upgrade: each node decides with its own code. A node that still runs 20261109 keeps refusing the affected keys; an upgraded node expires them. No coordination is needed.
- After the upgrade, the scanner queues the refused expiries again and they run. A deployment that was affected for some time should expect the delayed deletions to happen then.
- Native restore: `readRestoreGeneration` took such drives for a failed restore-status write and used its fallback, a generation without restore fields. It now finds one generation directly. The expiry of a restored copy refuses a generation found by the fallback, so by the code it no longer refuses these; that expiry was not run.

## Residual limits {#limits}

- **A restored copy that expired before a heal.** This is a separate defect of the same shape, and this fix does not repair it. The flag that stays in the key as stored says whether a transitioned version uses its data directory. A drive that wrote the version while its restored copy was on disk has it set; by the code, a drive healed after the copy expired has it clear. With such headers on 8 and 8 of 16 drives, the history is refused and the restore generation is found only by its fallback, which the expiry of the restored copy refuses. So the copy is not removed and the drives do not come together. The headers were crafted for this check; the heal that would produce them was not run. It needs enough drives healed between the expiry of a restored copy and its removal by the scanner, and gets its own record.
- **Two versions with the same time under an old signature.** For a version whose stored signature no current release computes, the key carries another signature than the drive, and the merge orders versions of the same modification time by it. Two such versions of one key, each missing on some drives, can be refused where 20261109 accepted them. Nothing is deleted.
- **Fixtures.** The tests model an old header by clearing the erasure-coding fields in a current `xl.meta`, and compute the old signature with the rule of the releases named above. No `xl.meta` written by those releases was used.

## Verification {#verification}

| Case                                                                        | 20261109         | With the fix                                |
| --------------------------------------------------------------------------- | ---------------- | ------------------------------------------- |
| Several pools, noncurrent-version expiry, 16 drives, 5 to 11 healed         | refused          | expires                                     |
| Same, 4 or 12 drives healed (control)                                       | expires          | expires                                     |
| One pool, expiry of all versions, 8 of 16 drives healed                     | refused          | expires                                     |
| Header signed by the rule before `RELEASE.2022-01-25`, 5 to 11 of 16 healed | refused          | accepted; still refused with Option 2 alone |
| Another erasure coding under the same header (control)                      | another revision | another revision                            |
| Restore generation on 8 healed drives of 16                                 | split            | one generation                              |
| Two versions of one time, each on 12 of 16 drives, 40 layouts (control)     | 40 accepted      | 40 accepted; 19 with Option 5               |
| Key of a version written by this release (control)                          | stored header    | stored header                               |
| Data-directory flag differs on 8 and 8 drives ([Residual limits](#limits))  | refused, split   | refused, split                              |
{.wide .expand}

Two tests are added to `cmd/erasure-server-pool-lifecycle-authority_test.go`. `TestPoolsLifecycleHeaderEras` builds the version lists of 16 drives for every count of healed drives and both old headers. `TestPoolsLifecycleHealedOldHeaders` writes two versions, checks that their keys carry the stored headers, gives them old headers, wipes and heals half of the drives, checks that reads work and heal has nothing left to do, and then expires a noncurrent version with two pools and all versions with one. Both fail on 20261109 and with Option 5, and pass with the fix. The two rows on equal times and on the data-directory flag were run as one-off probes and are not part of the suite.

The 192 existing tests of the lifecycle, restore, delete-all, tier, migration and `xl.meta` format suites pass with the fix, and `go vet` is clean. The full test suite and a run against data from an old MinIO release were not done.

## Review history {#review}

- Adversarial review, round 1, of the first version (Option 5): ran out of budget before a verdict. Its notes held two findings, and both were confirmed by test.
  - Taking the signature from the digest changes the order of versions of one time in the merge and refuses histories that 20261109 accepts. Adopted: Option 6 replaces Option 5, and the tests now fail with Option 5.
  - A header that differs only in the data-directory flag is left split, and the restored-copy expiry stays refused. This record had said the difference ends by itself; that was wrong and is corrected under [Residual limits](#limits). Not fixed here.
- Adversarial review, round 2, of the revised fix (Option 6): approved. It checked that the signature and erasure coding recomputed after decoding equal the stored ones for every object a current release writes, including the load-time repairs of old compression indexes and replication timestamps; that no two distinct revisions now share a key; that delete markers and free versions have no release-dependent header field; and that the restore readers of the key stay consistent. It could not run the tests in its read-only sandbox. One note on this record was adopted: which single-pool expiries are affected is now stated by rule name.

## References {#references}

- [Multi-Pool Lifecycle Expiry: Decide on the Whole Object](/blog/design/multi-pool-lifecycle-expiry/)
- [Lifecycle Delete-All Must Stay on One Key](/blog/design/ilm-delete-all-exact-key/)
- [Native Restore in Two Phases](/blog/design/native-restore-two-phase/)
- Upstream [#13573](https://github.com/minio/minio/pull/13573), [#14125](https://github.com/minio/minio/pull/14125), [#19534](https://github.com/minio/minio/pull/19534)
