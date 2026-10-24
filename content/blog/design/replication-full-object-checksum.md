---
title: "FULL_OBJECT Checksum Replication: Preserve the Type at Upload Initiation"
linkTitle: "FULL_OBJECT Replication"
date: 2026-10-24
lastmod: 2026-10-24
author: "Ruohang Feng"
summary: >
  PR #255 restores the FULL_OBJECT checksum type when replicating multipart CRC objects. This note documents the BadDigest failure chain, the upstream regression, why a three-line guard also repairs CopyObject replication, and the verification and upgrade guidance.
tags: [Design, Replication, S3, Checksum]
weight: 8
draft: false
url: "/blog/design/replication-full-object-checksum/"
---

[Issue #254](https://github.com/pgsty/silo/issues/254) reported a replication failure affecting multipart objects uploaded with a `FULL_OBJECT` CRC32 or CRC32C checksum: the object uploads and reads normally on the source, but the replication target rejects `CompleteMultipartUpload` with `400 BadDigest`. [PR #255](https://github.com/pgsty/silo/pull/255), contributed by Denis Babchuk (`@botdeniska`), restores the omitted checksum-type header in outgoing replication requests.

The patch was merged on October 24, 2026 as [`6d890fc86`](https://github.com/pgsty/silo/commit/6d890fc860c732cc0bd1925124c733362f803d2e), closing #254. It changes **five production lines (including two comment lines)** and adds 257 lines of regression tests.

## Observable Failure {#problem}

When an object has a multipart checksum recorded as `FULL_OBJECT` with algorithm CRC32 or CRC32C and bucket or site replication is enabled:

- The initial multipart upload succeeds and the source version remains readable.
- The replication sender transfers all parts to the target, but the target's `CompleteMultipartUpload` returns `400 BadDigest`.
- The source version remains in `FAILED` replication status and no replica version is created on the target.
- Every subsequent replication retry (including retries enqueued by `HeadObject` on the `FAILED` version) re-transfers the object parts and fails again at completion.

Multipart CRC64NVME objects replicate normally because the receiver defaults CRC64NVME to `FULL_OBJECT`; ordinary single-part `PUT` uploads and multipart `COMPOSITE` uploads are also unaffected. Performing a server-side `CopyObject` of an affected multipart `FULL_OBJECT` object triggers a second failure mode described [below](#copy).

## Root Cause: An Algorithm Does Not Define the Checksum Type {#root-cause}

For multipart CRC32 and CRC32C, the same algorithm supports two distinct object-level checksum calculations. Let `P1 ... Pn` be the part bodies and `||` denote byte concatenation:

| Type | Object checksum calculation |
| :-- | :-- |
| `FULL_OBJECT` | CRC computed across the concatenated bytes `P1 || ... || Pn`, encoded as Base64 |
| `COMPOSITE` | CRC computed across the concatenated **raw per-part CRC digests**, encoded as Base64 with the `-n` part-count suffix |

These two calculations produce different digests even for a single-part multipart upload. Forwarding only the algorithm name and digest value leaves the checksum semantics ambiguous.

The failure chain in the [replication sender](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L843) proceeds in four steps:

1. `putReplicationOpts()` calls `getCRCMeta()` to build object checksum headers. The previous implementation copied the digest value and `x-amz-checksum-algorithm`, but dropped `x-amz-checksum-type`.
2. `replicateObjectWithMultipart()` passes those options to `NewMultipartUpload` on the target. When CRC32 or CRC32C is initiated without an explicit checksum type, the target initializes and persists the upload as `COMPOSITE`.
3. After uploading all parts, the sender calls `getCRCMeta()` again for the completion request, sending the source's whole-object (`FULL_OBJECT`) CRC digest.
4. The target's [completion validator](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/erasure-multipart.go#L1378) reads the `COMPOSITE` type persisted at initiation, compares the supplied whole-object CRC against the composite CRC of the part checksums, and rejects the mismatch with `BadDigest`.

| Stage | Before the fix | After the fix |
| :-- | :-- | :-- |
| Source checksum metadata | CRC32/CRC32C + `FULL_OBJECT` | Unchanged |
| Target initiation headers | Algorithm only; type omitted | Algorithm + `FULL_OBJECT` |
| Target persisted upload type | `COMPOSITE` | `FULL_OBJECT` |
| Completion checksum | Source whole-object CRC | Source whole-object CRC + explicit `FULL_OBJECT` type |
| Target validation result | `400 BadDigest` | Valid completion |

The core invariant is that **replication must preserve the checksum algorithm, digest value, and type interpretation across both upload initiation and completion** so the target validates the transferred data under the same contract as the source.

## Upstream Regression and Earlier Repairs {#history}

Upstream MinIO commit [`4ea6f3b06`](https://github.com/minio/minio/commit/4ea6f3b06b5dc18bf967d1c13b97f33cc8bcdd87), merged on August 22, 2025 in PR #21535, removed checksum-type forwarding from `getCRCMeta()`. Prior to that commit, `getCRCMeta()` forwarded the checksum type unconditionally for every checksum—a behavior that cannot be restored wholesale without breaking single-PUT SHA replication (see [below](#guard)).

Three earlier SILO checksum fixes addressed separate parts of the lifecycle:

| Earlier change | What it fixed | Why replication initiation still failed |
| :-- | :-- | :-- |
| [`c8590413f`](https://github.com/pgsty/silo/commit/c8590413fd321a315f3779cd9b2a6f1cb72064da) (#31) | Allowed `FULL_OBJECT` completion requests to omit per-part checksums while validating the whole-object CRC | Requires the target upload to be initialized as `FULL_OBJECT` first |
| [`7e079ff05`](https://github.com/pgsty/silo/commit/7e079ff05c842afabb73c4572885cfb74604df17) | Verified that an explicitly supplied completion checksum type matches the type persisted at initiation | The replication sender omitted the type at both initiation and completion |
| [CompleteMultipartUpload ChecksumType response fix](/blog/design/complete-multipart-checksum-type/) | Returned `ChecksumType` in `CompleteMultipartUploadResult` XML to client SDKs | Governs client response serialization after completion, not outgoing replication headers |

## The Minimal Fix {#implementation}

Inside [`getCRCMeta()`](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L4242), immediately after copying a recognized checksum digest and algorithm, the patch adds:

```go
if isMP && cktype.CanMerge() && cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject {
    meta[xhttp.AmzChecksumType] = xhttp.AmzChecksumTypeFullObject
}
```

Each condition narrows forwarding to the exact domain required:

- `isMP`: Decoded from the **stored checksum's multipart flag** (which does not require the current object to carry a `-n` multipart ETag).
- `cktype.CanMerge()`: Selects the algorithms that support merging per-part CRCs into a full-object CRC (CRC32, CRC32C, and CRC64NVME).
- `cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject`: Forwards the type only when the stored checksum is actually `FULL_OBJECT`, never relabeling `COMPOSITE` checksums.

Because both upload initiation (`NewMultipartUpload`) and completion (`CompleteMultipartUpload`) call `getCRCMeta()`, this single guard restores the header across both phases. Individual `UploadPart` requests read per-part checksum maps that carry no object-level checksum type, leaving part headers unchanged, while CRC64NVME receives an explicit `FULL_OBJECT` header matching its existing default.

### Why Not Forward Every Stored Type? {#guard}

An ordinary single-PUT SHA1 or SHA256 object also records `FULL_OBJECT` in its stored and read checksum metadata. However, on the request parser side, [`getContentChecksum()`](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/internal/hash/checksum.go#L766) rejects an explicit `x-amz-checksum-type: FULL_OBJECT` header for non-mergeable algorithms such as SHA1 and SHA256.

Forwarding stored checksum types unconditionally would therefore break single-PUT SHA1/SHA256 replication. Gating on `isMP && cktype.CanMerge()` repairs multipart CRC replication while keeping single-PUT and `COMPOSITE` request headers unchanged.

### CopyObject Automatically Reuses the Single-PUT Path {#copy}

When a server-side `CopyObject` copies a multipart `FULL_OBJECT` object, the resulting object has a plain non-multipart ETag (`!objInfo.isMultipart()`) while retaining the multipart `FULL_OBJECT` checksum metadata. Because a `FULL_OBJECT` digest covers the entire logical payload, it remains valid when replicated via a single `PutObject`.

[`putReplicationOpts()` already contained](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication.go#L879) the routing check for this case:

```go
if !objInfo.isMultipart() && cs[xhttp.AmzChecksumType] == xhttp.AmzChecksumTypeFullObject {
    isMP = false
}
```

When `getCRCMeta()` dropped `x-amz-checksum-type`, that condition never matched, forcing the copied object down a one-part multipart replication path that failed with `BadDigest`. Restoring the type in `getCRCMeta()` re-enables this existing branch automatically: the copied object replicates through a single `PutObject` without any Copy-specific code or checksum recalculation.

## Rejected Alternatives {#alternatives}

| Alternative | Decision and rationale |
| :-- | :-- |
| Forward every checksum type unconditionally (pre-PR #21535 behavior) | Rejected: explicit `FULL_OBJECT` headers on SHA1/SHA256 requests are rejected by `getContentChecksum()` |
| Send the checksum type only on `CompleteMultipartUpload` | Rejected: the target upload is already initialized as `COMPOSITE`, and completion rejects a mismatched type |
| Default all CRC32/CRC32C multipart uploads to `FULL_OBJECT` | Rejected: breaks standard S3 `COMPOSITE` semantics |
| Drop the object checksum or bypass `BadDigest` validation | Rejected: sacrifices end-to-end integrity verification |
| Recalculate a `COMPOSITE` digest on the sender to match the target | Rejected: alters the replica's checksum type and digest value and adds unnecessary work |
| Add a separate `CopyObject` replication branch or CRC64NVME special case | Unnecessary: the existing `!objInfo.isMultipart()` branch and `CanMerge()` already cover both |
| Adjust replication retry budgets, queues, or resync scheduling | Ineffective: retrying an unchanged malformed request repeats the same `BadDigest` failure |

## Validation and Live Acceptance {#validation}

Running the new regression tests against the unmodified baseline [`aafe4f888`](https://github.com/pgsty/silo/commit/aafe4f8886a060ec698400043bee2f60e22140fd) reproduced `BadDigest` on `FULL_OBJECT` CRC32/CRC32C replication and failed the `CopyObject` routing assertion (`got true, want false`), while passing all control cases. With the patch applied, both test suites passed.

The [committed regression suite](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/bucket-replication-checksum_test.go) includes 8 table-driven header tests (checking both object-level and per-part headers) and 8 API integration cases across two versioned buckets, verifying routing decisions and matching checksum metadata.

Live acceptance testing ran **two single-drive SILO server instances** configured for site replication with `mcli` across 12 end-to-end cases:

| Case family | Algorithms / variants | Cases |
| :-- | :-- | --: |
| Single `PUT` | SHA256, SHA1, CRC32 | 3 |
| Multipart `COMPOSITE` | CRC32, CRC32C, SHA256 | 3 |
| Multipart `FULL_OBJECT` | CRC32, CRC32C | 2 |
| Multipart default `FULL_OBJECT` | CRC64NVME | 1 |
| `CopyObject` of multipart `FULL_OBJECT` | CRC32, CRC32C | 2 |
| Single-part multipart `FULL_OBJECT` | CRC32 | 1 |

All 12 cases reached `COMPLETED` on the source and `REPLICA` on the target, with independently computed checksum digests and types, version IDs, ETags, object sizes, and downloaded payload bytes matching across both endpoints.

Reproducible test commands:

```bash
go test ./cmd -count=1 -v \
  -run '^(TestGetCRCMetaChecksumType|TestReplicateObjectChecksumTypes)$'
go test ./cmd ./internal/hash -count=1 -timeout 10m \
  -run 'Replicat|Checksum|CRC|Multipart'
MINIO_API_REQUESTS_MAX=10000 CGO_ENABLED=0 \
  go test -tags kqueue,dev ./... -count=1 -timeout 30m
```

Both PR CI ([Go CI](https://github.com/pgsty/silo/actions/runs/39974825425), [DCO](https://github.com/pgsty/silo/actions/runs/39974825340), [VulnCheck](https://github.com/pgsty/silo/actions/runs/39974825530)) and merged-commit CI ([Go CI](https://github.com/pgsty/silo/actions/runs/40082832251), [VulnCheck](https://github.com/pgsty/silo/actions/runs/40082832247)) passed in full.

## Upgrade and Operational Guidance {#operations}

- **Upgrade the replication source**: Because the defect is an omitted header in outgoing replication requests, upgrading only the target cannot restore the missing `x-amz-checksum-type`. In active-active bidirectional replication, every site acts as a sender and must be upgraded. Mixed-version testing reported in [PR #255](https://github.com/pgsty/silo/pull/255) confirmed that a patched source replicates cleanly to an unpatched SILO target, whereas an unpatched source still fails against a patched target.
- **Replication paths covered**: Bucket replication, site replication, and batch replication ([`batchReplicationOpts()`](https://github.com/pgsty/silo/blob/6d890fc860c732cc0bd1925124c733362f803d2e/cmd/batch-handlers.go#L1593)) all delegate header construction to `putReplicationOpts()` and inherit the fix. SSE-C encrypted objects continue to pass encrypted checksum metadata through `X-Minio-Replication-Ssec-Crc`.
- **Recovering existing `FAILED` versions and rollback**: No configuration setting, on-disk metadata format, or public API changes. Existing `FAILED` versions retain valid checksum metadata on the source and complete replication on retry or resync once the sending node is upgraded; rolling back affects only subsequent outgoing replication requests and requires no metadata migration for already replicated objects.
