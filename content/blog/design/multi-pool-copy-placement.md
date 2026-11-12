---
title: "Multi-Pool CopyObject: Cross-Pool Historical Version Self-Copy, Moving-Pool Authority, and Compression Indexes"
linkTitle: "Multi-Pool Copy Placement"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  Why copying a historical version of an object onto its own key failed with 404 NoSuchVersion across server pools, why placement and rewrite decisions must run before encryption and compression transforms, and why pooled copy rewrites must forward IndexCB for multi-block S2 ranged reads.
tags: [Design, Multi-Pool, CopyObject, Encryption, Compression]
weight: 10
draft: false
url: "/blog/design/multi-pool-copy-placement/"
---

This record covers an upstream-inherited multi-pool `CopyObject` failure family across `cmd/erasure-server-pool.go` and `cmd/object-handlers.go`, tracked under [#343](https://github.com/pgsty/silo/issues/343).

**Status:** Shipped in **[SILO 20261112](/blog/release/silo-20261112/)** (`RELEASE.2026-11-12T00-00-00Z`; commits [`a8824b341`](https://github.com/pgsty/silo/commit/a8824b341fce071cdd48356caaed37d76580c39e), [`e36ea51d9`](https://github.com/pgsty/silo/commit/e36ea51d9c3a28df7d60f1d105226b1d0049342e), and [`cd3e46a2b`](https://github.com/pgsty/silo/commit/cd3e46a2b7dee00b64c323d35ebdd32aab0fe644)). `SILO Server 20261109` and earlier—as well as upstream MinIO releases since `2020-08-03`—are affected.

## Short Answer {#tldr}

In a versioned bucket, S3 clients roll an object back to an earlier version by copying that historical version onto the same bucket and key (`PUT /bucket/key` with `x-amz-copy-source: /bucket/key?versionId=<old-version>`). Within a single erasure pool, `CopyObject` optimizes this operation (`srcInfo.versionOnly = true`) by appending a new version entry in `xl.meta` that references the existing `DataDir` on disk without copying payload bytes.

Inherited from upstream MinIO, `(*erasureServerPools).CopyObject` assumed that whenever `srcBucket == dstBucket` and `srcObject == dstObject`, the addressed historical version lived in the **same** server pool selected for the destination key (`poolIdx`, normally the pool holding the latest version). Whenever Pool 1 held the current version `v2` (written after pool expansion, rebalance, or partial decommission) while Pool 0 held historical version `v1`, dispatching `versionOnly = true` to Pool 1 looked up `v1` on Pool 1's drives and failed with **`404 NoSuchVersion`**—or, for encrypted/compressed objects where `CopyObjectHandler` had already skipped preparing a payload stream (`metadataOnly = true`), lacked the stream needed to rewrite bytes across pools. Additionally, when `erasureServerPools.CopyObject` did fall back to `PutObject` for cross-pool rewrites, it omitted `IndexCB: dstOpts.IndexCB`, dropping the multi-block S2 seek index (`Parts[0].Index`) on compressed copies larger than 8 MiB.

The repair introduces `prepareCopyObject` (`copyObjectPlan`), resolving target pool placement and whether payload bytes must be rewritten **under the object locks before** HTTP-layer encryption, checksum, and S2 compression transforms execute—while strictly binding in-place metadata updates to the authoritative copy's pool (even if that pool is draining or rebalancing) and forwarding `IndexCB` on pooled rewrites.

## Classification {#assessment}

| Aspect              | Assessment                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| :------------------ | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nature**          | Single-pool `DataDir`-sharing assumption applied across independent server pools, plus omitted `IndexCB` on pooled `PutObject` fallback. Inherited from upstream MinIO.                                                                                                                                                                                                                                                                                                                   |
| **Upstream origin** | Introduced in [`5ce82b45d`](https://github.com/pgsty/silo/commit/5ce82b45da652d93ed670f6072a2ada4939a8e03) (`2020-08-03`, [minio/minio#10170](https://github.com/minio/minio/pull/10170), *"add CopyObject optimization when source and destination are same"*) and carried into multi-pool `serverPools` in [`ad726b49b`](https://github.com/pgsty/silo/commit/ad726b49b4799cdb878ca0a6cdf06ea2dd3c19e7) (`2020-10-15`, [minio/minio#10679](https://github.com/minio/minio/pull/10679)). |
| **Affected scope**  | Multi-pool (`2+` server pools) deployments after pool expansion, rebalance, or decommission whenever historical versions and current versions of a key span different pools, or when multi-block S2 compressed objects (`> 8 MiB`) are rewritten across pools.                                                                                                                                                                                                                            |
| **Impact**          | Valid S3 historical-version rollback (`CopyObject` with `?versionId=`) fails with `404 NoSuchVersion`; pooled S2 compressed rewrites lose O(1) block-level ranged `GET` seeking.                                                                                                                                                                                                                                                                                                          |
| **Data safety**     | Source versions are untouched on `404`; however, naive placement fixes that use write allocation for in-place updates can promote stale duplicates on moving pools (prevented in `e36ea51d9`).                                                                                                                                                                                                                                                                                            |
{.wide .expand}

---

## 1. Upstream Provenance and Root Causes {#root-cause}

### 1.1 Cross-Pool `versionOnly` Assumption (`5ce82b45d`) {#version-only}

In [`5ce82b45d`](https://github.com/pgsty/silo/commit/5ce82b45da652d93ed670f6072a2ada4939a8e03) (`2020-08-03`), upstream optimized same-key copies into two zero-data-copy subcases:

1. **In-place metadata update:** Replacing user metadata, storage class, tags, or SSE-C key wrapper on an existing unversioned object (or a replication-addressed version `srcOpts.VersionID == dstOpts.VersionID`).
2. **Same-key historical version promotion (`srcInfo.versionOnly = true`):** Creating a new current version on `(bucket, key)` from an older `srcOpts.VersionID` by pointing the new version's `DataDir` at the old version's `DataDir` in the same `xl.meta`.

`DataDir` sharing is physically valid **only within the same erasure pool and set**, because each server pool has independent drives and erasure shards. Yet `CopyObjectHandler` (`cmd/object-handlers.go`) set `cpSrcDstSame = isStringEqual(pathJoin(srcBucket, srcObject), pathJoin(dstBucket, dstObject))` purely from bucket/key strings before knowing which pool held `srcOpts.VersionID` and which pool would store the new version:

- When `compressMetadata` or SSE-S3/SSE-KMS/SSE-C logic in `CopyObjectHandler` saw `cpSrcDstSame && metadataOnly`, it skipped opening a decrypted/re-encrypted/compressed `PutObjReader` stream (`srcInfo.PutObjReader == nil`), assuming storage would reuse the existing on-disk `DataDir`.
- Down in `(*erasureServerPools).CopyObject`, `getPoolIdx` picked Pool 1 (where the current version lived), set `srcInfo.versionOnly = true`, and called `z.serverPools[1].CopyObject(...)`—which searched Pool 1 for `srcOpts.VersionID` (stored on Pool 0) and returned `VersionNotFound` (`404 NoSuchVersion`).

### 1.2 Why Moving Pools Require Separating In-Place Updates from New Writes {#moving-pools}

Fixing cross-pool historical copies exposes a subtle trap when one of the pools is currently **draining (`decommissioning`) or rebalancing**:

- **Case A — True in-place metadata update** (for example, `X-Amz-Metadata-Directive: REPLACE` on an unversioned object, an SSE-C key rotation in place, or a replication metadata update where `srcOpts.VersionID == dstOpts.VersionID`):
  Suppose Pool 0 (currently decommissioning) holds the authoritative `current-body` of key `k`, while Pool 1 holds an older stale duplicate `stale-body` left behind by an interrupted operation. Normal write placement (`getPoolIdxNoLock`) skips decommissioning Pool 0 and returns Pool 1! If an in-place metadata update writes to Pool 1 and then retires duplicates on other pools, it promotes `stale-body` with a newer `ModTime` and deletes `current-body` on Pool 0—silently corrupting object data.
- **Case B — Same-key data rewrite** (for example, changing SSE-S3 encryption, recomputing checksums, or creating a new version in a different pool):
  Conversely, if an unversioned object lives only on decommissioning Pool 0 and the copy request changes encryption or checksums (`copyRewritesObjectData == true`), the server **must** write new data bytes to an **active** pool (Pool 1) rather than attempting an in-place lookup on Pool 1 (which would fail with `404`) or writing new data onto a draining pool.

### 1.3 Dropped `IndexCB` on Pooled `PutObject` Rewrites {#index-cb}

For compressible objects exceeding `compMinIndexSize` (`8 MiB`), `newS2CompressReader` generates an S2 block index via `dstOpts.IndexCB` so ranged `GET` requests can seek directly to the target 1 MiB block instead of decompressing from byte `0`. In `(*erasureServerPools).CopyObject`, the cross-pool `PutObject` fallback constructed a fresh `ObjectOptions` struct that copied `UserDefined`, `ServerSideEncryption`, and `MTime`, **omitting `IndexCB: dstOpts.IndexCB`**—silently discarding the compression seek index on every cross-pool compressed copy rewrite.

---

## 2. Solution Design: Why `prepareCopyObject` Is Necessary and Sufficient {#fix}

Commits [`a8824b341`](https://github.com/pgsty/silo/commit/a8824b341fce071cdd48356caaed37d76580c39e), [`e36ea51d9`](https://github.com/pgsty/silo/commit/e36ea51d9c3a28df7d60f1d105226b1d0049342e), and [`cd3e46a2b`](https://github.com/pgsty/silo/commit/cd3e46a2b7dee00b64c323d35ebdd32aab0fe644) establish a deterministic two-step copy contract:

1. **Lock-protected placement & rewrite planning before transforms (`prepareCopyObject`):**
   `CopyObjectHandler` acquires the cross-pool source/destination lock (`lockObjects`) and calls `prepareCopyObject` **before** deciding whether to run the in-place SSE-C key-rewrap fast path or construct decryption/re-encryption, checksum, and S2 compression streams:
   - First, `copyRewritesObjectData` evaluates whether encryption, legacy format, or checksum changes force a full payload rewrite (`reference = sameObject && !copyRewritesObjectData(...)`).
   - **In-place metadata update (`inPlace == true`):** When `reference` is true and the operation updates the exact version in place (`dstOpts.VersionID != "" && srcOpts.VersionID == dstOpts.VersionID`, or `!dstOpts.Versioned && srcOpts.VersionID == ""`), `prepareCopyObject` resolves `poolIdx` via `getLatestObjectInfoWithIdx`—binding the update strictly to the pool holding the **authoritative source copy**, even if that pool is currently decommissioning or rebalancing.
   - **New version or forced data rewrite (`inPlace == false`):** `prepareCopyObject` selects an active writable pool via `getPoolIdxNoLock`. If `reference` was otherwise eligible (`!z.SinglePool()`), it checks `sourcePool` via `getLatestObjectInfoWithIdx`: when `sourcePool == poolIdx`, zero-copy `versionOnly` reference sharing proceeds inside that pool; when `sourcePool != poolIdx`, `plan.rewrite = true` instructs `CopyObjectHandler` to clear `metadataOnly` and stream the source version through the full decryption/compression/encryption pipeline into `poolIdx`.
2. **Preserve `IndexCB` across pooled `PutObject` rewrites (`cd3e46a2b`):**
   `(*erasureServerPools).CopyObject` forwards `IndexCB: dstOpts.IndexCB` in `putOpts`, preserving `Parts[0].Index` on multi-block S2 compressed copies.

### Why This Is Necessary and Sufficient {#sufficiency}

- **Necessary:**
  - Planning placement *after* `CopyObjectHandler` builds `srcInfo` is too late: once `CopyObjectHandler` skips creating `PutObjReader` (or seals SSE-KMS/SSE-S3 headers for metadata-only mode), `erasureServerPools.CopyObject` cannot synthesize a decrypted/re-encrypted stream on its own.
  - Using `getPoolIdxNoLock` for `inPlace` updates corrupts objects when a draining pool holds the authoritative copy and an active pool holds a stale copy; conversely, treating encryption/checksum-changing copies on an unversioned key as `inPlace` breaks legitimate copies out of moving pools.
- **Sufficient:** Every combination of `{single-pool, multi-pool}` $\times$ `{active pool, draining/rebalancing pool}` $\times$ `{unversioned, UUID version, null version}` $\times$ `{plaintext, SSE-S3, SSE-KMS with AAD context, SSE-C, S2 compressed > 8 MiB}` now resolves placement once under lock and executes either an exact-pool metadata update or a complete active-pool stream rewrite (`cmd/object-copy-pools_test.go`).

---

## 3. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                         | Engineering Trade-Off & Operational Cost                                                                                                                                                                                                                                                                                                                                                                                                                     |
| :------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Physical byte rewrite on cross-pool self-copy** | When rolling back to a historical version stored in Pool 0 while current write placement selects Pool 1, SILO streams and writes the object's payload into Pool 1 rather than sharing `DataDir`. Because independent erasure pools share no physical disks, copying the bytes is physically unavoidable—and turns a deterministic `404 NoSuchVersion` failure into a valid S3 copy. Same-pool self-copies continue to share `DataDir` in O(1) metadata time. |
| **In-place metadata updates on draining pools**   | While a pool is decommissioning, an in-place metadata-only edit (`REPLACE` metadata or SSE-C key wrapper rotation) updates `xl.meta` on the draining pool where the authoritative bytes still reside; the decommission worker subsequently migrates that updated object cleanly to an active pool.                                                                                                                                                           |
{.wide .expand}

## Verification {#verification}

`cmd/object-copy-pools_test.go` verifies cross-pool historical version self-copies across plaintext, SSE-S3, SSE-KMS (with associated-data encryption context), SSE-C, and multi-block S2 compression (`Parts[0].Index` preserved), as well as moving-pool (`decommissioning` / `rebalancing`) authority preservation against stale duplicate copies and timestamp ties. See also [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/) and [Server Compatibility Notes](/compatibility/server/#candidate-after-20261109).
