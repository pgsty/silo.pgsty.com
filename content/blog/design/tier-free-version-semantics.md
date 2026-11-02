---
title: "Tier Free Versions Are Internal Cleanup Records"
linkTitle: "Tier Free Version Semantics"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO Maintainers"
summary: >
  Why a tier free version is an internal cleanup record, how treating it as a normal version breaks lifecycle and pool migration, and why PR #264 is the minimum complete repair.
tags: [Design, Tiering, Lifecycle, Storage Pools, Compatibility]
weight: 12
draft: false
url: "/blog/design/tier-free-version-semantics/"
---

This record covers [issue #263](https://github.com/pgsty/silo/issues/263) and [PR #264](https://github.com/pgsty/silo/pull/264), updated against main at [0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b), with the #264 merge recorded at [0cfca29c](https://github.com/pgsty/silo/commit/0cfca29cb2f16e43cb8266d9259f0dc5298c53b3). The PR is three linked repairs, not three unrelated workarounds.

## Short answer {#tldr}

The report is real. A free version is an internal record left in xl.meta while SILO finishes deleting the remote tier object belonging to a deleted version. It has delete-marker type information and the deleted version's time, but it is not a user version. GET already ignores it. Several batch paths did not.

That mismatch causes four failures:

- lifecycle counts the real version below the free entry as noncurrent and can delete the wrong version;
- ListObjectVersions shows a delete marker over an object that GET can read;
- ListObjectsV2 hides the key;
- decommission and rebalance move the free record as a real delete marker, so removing the old pool can make the object unreadable.

PR #264 fixes the lifecycle view, the latest-marker checks, ordinary listing, and pool cleanup as one semantic boundary. Healing retains a separate all-entries view. The PR is now merged and is the required base for reviewing #266.

## What a free version means {#meaning}

The tiered object has two pieces:

1. metadata in the hot pool;
2. a remote object in the configured tier.

When the data version is deleted, SILO may not be able to delete the remote object immediately. It writes a free version that remembers the remote name, remote version, tier, and deletion time. The scanner later deletes the remote object and then the free record.

A client delete of a tiered version by version ID can create one. Overwriting a tiered null version can create one. An ILM expiry can create one when remote deletion fails. The record is useful to healing and tier cleanup, but it is not part of the S3 version history.

## Timeline and history {#history}

The free-version mechanism was added upstream in [a1df23051](https://github.com/pgsty/silo/commit/a1df23051), dated 2021-06-30, to track deletion of tiered content. The normal read conversion has long skipped free entries when deciding IsLatest and the successor time.

Upstream later changed metadata listing in [29a25a538](https://github.com/pgsty/silo/commit/29a25a538), dated 2024-06-07, so free versions appeared in version listings as delete markers. The stated goal was supportability: expose every xl.meta entry to an operator using a versions listing. That choice made an internal cleanup record visible through an S3 API and left the other batch consumers dependent on whether they asked for free entries.

The SILO failure is therefore not a newly introduced storage-format regression. It is an old representation being used as two different things:

- GET treated it as internal cleanup state.
- scanner, list, Walk, decommission, and rebalance treated it as an object version.

## Root cause in simple terms {#root-cause}

Suppose an object has real versions v1 and v2, then the latest tiered version v3 is deleted. The metadata may look conceptually like:

~~~text
free(v3 remote object, time of v3 deletion)
v2
v1
~~~

The free entry sorts above v2 because it carries v3's time. GET skips the first entry and returns v2. The scanner and version list did not skip it:

- v2 was marked noncurrent because the free entry was treated as its successor;
- the free entry was serialized as a delete marker;
- migration copied that marker to the new pool.

After the old pool was removed, the copied marker hid v2. The remote object reference was also lost from the tier-cleanup path.

## Impact {#impact}

The issue is data-correctness and API-correctness at the same time:

- A NoncurrentVersionExpiration rule can delete the actual latest real version.
- NewerNoncurrentVersions can retain the wrong count of versions.
- ListObjectVersions can show DM as latest while GET returns 200 for the real version below.
- ListObjectsV2 can omit a readable key.
- A decommission can complete while turning the free record into a permanent delete marker.
- If the remote object was not deleted yet, moving the free record can orphan tier data.
- If the tier is unavailable, silently completing the decommission is unsafe.

The issue affects a normal versioned-tier workflow, not just corrupted metadata. It is enough to delete a tiered version and start a migration before the scanner has finished its cleanup.

## Options {#options}

### Fix only the scanner

Recomputing IsLatest and successor times after removing free entries would stop the most dangerous over-expiry. It would not fix S3 listings or migration. A decommission could still create a delete marker.

### Fix only listings and migration

This would make the API and pool move look correct while lifecycle rules still delete the wrong version during the scanner pass. It is incomplete.

### Keep free entries visible everywhere

This preserves the upstream supportability behavior from #19878, but it exposes an internal cleanup record as a public delete marker and makes GET, lifecycle, listing, and movement disagree. SILO supports its maintained stack on logical object behavior; internal tier bookkeeping should not define the S3 history.

### Remove free entries immediately at delete time

This fails when the tier is temporarily unavailable. The free record is the durable reminder that remote cleanup is still pending. Removing it early risks orphaning the remote data.

### Use two explicit views

This is the smallest complete design:

- normal listing, lifecycle evaluation, Walk, decommission, and rebalance see real versions only;
- healing and tier cleanup can request all entries;
- decommission removes free entries' remote objects before removing their local records and fails if the tier cannot be contacted.

PR #264 implements this option.

## PR assessment {#pr}

The three commits in #264 have a coherent order:

1. getFileInfoVersions recomputes IsLatest, SuccessorModTime, and LatestModTime after free entries are partitioned out.
2. latest-delete-marker checks look past free entries.
3. ordinary FileInfoVersions excludes free entries, while healing calls an explicit all-entries helper; pagination skips keys that contain only free entries; decommission performs tier cleanup and makes failure retryable.

The focused tests fail on main for every new behavior except the intentional healing guard and pass on the PR. They cover lifecycle selection, ListObjectsV2, ListObjectVersions pagination, Walk, healing, decommission, rebalance, and an unavailable tier.

The user-visible change is deliberate: ListObjectVersions no longer exposes a free record as a delete marker. That is a compatibility difference from the 2024 upstream behavior, but it restores one logical view of the object and prevents an internal cleanup state from becoming a durable public tombstone. The retained upstream compatibility policy is best effort, while the maintained SILO stack is the release gate.

The recommendation was to accept #264, and that decision is now implemented in main. It was necessary as a whole. Taking only its first or second commit would have left an independent correctness hole in the next batch path.

## Operational boundary {#operations}

When a decommission finds free entries, it may contact the tier. A missing remote object is safe to ignore because the local record is already stale. A tier outage is different: the free record remains and decommission must fail so that a retry can finish cleanup. This is more visible operationally than main, but it avoids silently losing a cleanup obligation.

This repair cannot identify or restore plain delete markers created by an older buggy decommission. Those markers have lost the free-version flag. Affected objects must be recovered from backups or another authoritative copy.

## Verification references {#verification}

- Issue: [#263](https://github.com/pgsty/silo/issues/263)
- PR: [#264](https://github.com/pgsty/silo/pull/264)
- Merge commit: [0cfca29c](https://github.com/pgsty/silo/commit/0cfca29cb2f16e43cb8266d9259f0dc5298c53b3)
- Free-version introduction: [a1df23051](https://github.com/pgsty/silo/commit/a1df23051)
- Upstream listing change: [29a25a538](https://github.com/pgsty/silo/commit/29a25a538)
- PR head: [7ce7fc8d1](https://github.com/pgsty/silo/commit/7ce7fc8d1)
