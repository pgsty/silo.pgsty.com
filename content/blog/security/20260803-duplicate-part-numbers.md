---
title: "Duplicate Part Numbers in CompleteMultipartUpload"
linkTitle: "Duplicate Part Numbers"
date: 2026-08-03
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "How CompleteMultipartUpload accepted duplicate part numbers in ascending order, why sort.SliceIsSorted missed [1, 1], and how Server 20260804 fixes it."
url: "/blog/security/duplicate-part-numbers/"
tags: ["S3", "Multipart Upload", "Correctness", "SILO"]
---

In `CompleteMultipartUpload`, the S3 API requires part numbers in the completion XML to be strictly ascending. Up through Server `20260725`, SILO enforced that invariant with `sort.SliceIsSorted` and a strict `<` comparator—which accepts non-decreasing sequences such as `[1, 1]` and duplicates the referenced part in the assembled object. [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) ([`pgsty/silo#49`](https://github.com/pgsty/silo/issues/49)) replaces that check with an explicit adjacent-pair comparison (`Parts[i-1].PartNumber >= Parts[i].PartNumber`) and fixes an adjacent empty-part panic in `ReadParts` (`2602177ef`).

## Conclusions first {#summary}

1. **The bug is real and small**: `CompleteMultipartUpload` used `sort.SliceIsSorted` with `<`, which tests non-decreasing order (`a[0] <= a[1] <= ...`) rather than strictly increasing order (`a[0] < a[1] < ...`). Passing duplicate part numbers such as `[1, 1]` succeeded and duplicated the underlying part in the final object.
2. **This is a data-integrity defect, not a CVE**: Triggering it requires a caller who already holds `s3:PutObject` permission on the target key and a valid `uploadId` for an in-progress multipart upload. It does not cross tenant, bucket, or credential boundaries.
3. **The fix stays at the HTTP handler boundary**: `cmd/object-handlers.go` rejects `Parts[i-1].PartNumber >= Parts[i].PartNumber` with `InvalidPartOrder` (HTTP 400). Sparse part numbers (`[1, 3]`, `[5, 9]`, `[3]`) remain valid.

---

## Why `sort.SliceIsSorted` Accepted Duplicates {#the-defect}

In `cmd/object-handlers.go`, `CompleteMultipartUploadHandler` validated the parsed `<CompleteMultipartUpload>` part list with:

```go
if !sort.SliceIsSorted(complMultipartUpload.Parts, func(i, j int) bool {
    return complMultipartUpload.Parts[i].PartNumber < complMultipartUpload.Parts[j].PartNumber
}) {
    writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
    return
}
```

In Go's standard library, `sort.SliceIsSorted` iterates `i` from `n-1` down to `1` and calls `less(i, i-1)`. If `less(i, i-1)` returns `true`, the slice is out of order. When two adjacent elements are equal (`Parts[i].PartNumber == Parts[i-1].PartNumber`), `Parts[i].PartNumber < Parts[i-1].PartNumber` evaluates to `false`, so `SliceIsSorted` treats them as sorted.

Replacing `sort.SliceIsSorted` with a direct adjacent check closes the gap:

```go
for i := 1; i < len(complMultipartUpload.Parts); i++ {
    if complMultipartUpload.Parts[i-1].PartNumber >= complMultipartUpload.Parts[i].PartNumber {
        writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
        return
    }
}
```

---

## Two Refactors Preserved the Defect {#archaeology}

Tracing `git log -S` across the handler history shows that the non-decreasing check survived two separate cleanups over nine years:

| Date | PR / Commit | What Changed | Why `[1, 1]` Survived |
|---|---|---|---|
| 2016-08 | [`minio/minio#2490`](https://github.com/minio/minio/pull/2490) | Introduced `sort.IsSorted(completedParts(complMultipartUpload.Parts))` with `Less(i, j) { return a[i].PartNumber < a[j].PartNumber }`. | `sort.IsSorted` only checks that no element is smaller than its predecessor. |
| 2017-11 | [`minio/minio#5170`](https://github.com/minio/minio/pull/5170) | Replaced the named `completedParts` type with `sort.SliceIsSorted` using the same `<` closure. | Mechanical refactor of the same comparator. |
| 2023-04 | [`minio/minio#17066`](https://github.com/minio/minio/pull/17066) | Moved `ErrInvalidPartOrder` validation earlier in `CompleteMultipartUploadHandler` before hitting the object layer. | Moved the check block verbatim without testing duplicate part numbers. |

Every unit and mint test for `ErrInvalidPartOrder` tested inversions such as `[2, 1]`, never adjacent duplicates such as `[1, 1]`.

---

## Observed Impact {#impact}

Before the fix, uploading a single 5 MiB part (`partNumber=1`) and completing the upload with two `<Part>` entries both referencing `PartNumber=1` and its ETag produced the following behavior:

| Step | Request | Pre-Fix Result | Post-Fix Result |
|---|---|---|---|
| 1 | `UploadPart(partNumber=1)` (5 MiB) | `200 OK`, returns `ETag: "e1"` | `200 OK`, returns `ETag: "e1"` |
| 2 | `CompleteMultipartUpload` with `[(1, "e1"), (1, "e1")]` | `200 OK`, `ETag: "...-2"` | `400 Bad Request` (`InvalidPartOrder`) |
| 3 | `HeadObject` / `GetObject` | `Content-Length: 10485760` (part 1 repeated twice) | Object not created; upload remains open |
| 4 | Retry `CompleteMultipartUpload` with `[(1, "e1")]` | `404 NoSuchUpload` (upload already consumed) | `200 OK`, `Content-Length: 5242880` |

Because `CompleteMultipartUpload` consumes the upload state on success, a buggy client that accidentally duplicated an entry in its completion XML (for example, when retrying an `UploadPart` call and appending to an in-memory slice instead of deduplicating by part number) silently wrote a corrupted object of the wrong size and could not retry completion without re-uploading every part.

---

## Why This Is Not a CVE {#not-a-cve}

We evaluated whether a malicious caller could weaponize duplicate part numbers for storage amplification:

1. **No physical disk amplification**: In erasure-coded storage, `CompleteMultipartUpload` records part metadata in `xl.meta` referencing the existing `part.1` data files on disk rather than copying part bytes per entry. Reading the object streams `part.1` twice, and background healing or copying materializes the logical size, but the caller could achieve the same result legitimately by uploading two parts or calling `UploadPartCopy`.
2. **Same-caller scope**: Executing `CompleteMultipartUpload` requires write access to the object and knowledge of the `uploadId`. No unauthenticated or read-only principal can trigger it.

The issue is therefore tracked as a correctness and S3 protocol compliance bug (`#49`) rather than a security advisory (`SN-2026-*`).

---

## Handler vs. Object-Layer Boundary {#boundary}

During investigation we checked whether `erasureObjects.CompleteMultipartUpload` (`cmd/erasure-multipart.go`) also validates part ordering. It does not: the object layer iterates `for i, part := range parts` and matches each entry against `uploadID` part metadata.

We kept the check in `CompleteMultipartUploadHandler` (`cmd/object-handlers.go`) rather than duplicating it inside every `ObjectLayer` implementation for two reasons:

1. **Single untrusted entry point**: Client-supplied completion lists enter only through `CompleteMultipartUploadHandler`. Internal callers (`batch-replicate`, `restore`, `decommission`, `rebalance`, and `PutObjectPart` pathways) construct part lists directly from existing `ObjectInfo.Parts` or sequential `1..n` loops.
2. **Fail-fast before lock acquisition**: Rejecting malformed XML in the HTTP handler avoids acquiring the object's namespace lock or reading upload metadata from disk.

---

## Preserving Sparse Part Numbers {#no-extra-constraints}

The S3 specification requires part numbers in `CompleteMultipartUpload` to be strictly increasing (`1 <= PartNumber <= 10,000`), **not** contiguous and **not** starting at `1`. A client that uploads parts `1`, `2`, `3` and completes using only `[1, 3]`, or completes using `[5, 9]` or `[3]`, is conforming to S3.

To make sure our fix did not over-constrain valid clients, we added explicit regression cases for:
- `[1, 3]` (sparse gap),
- `[3]` (single part not starting at `1`),
- `[1, 1]` and `[1, 2, 2, 3]` (adjacent duplicates, rejected with `ErrInvalidPartOrder`),
- `[1, 3, 2]` and `[2, 1]` (decreasing order, rejected with `ErrInvalidPartOrder`),
- `[1, 2, 1]` (non-adjacent duplicate, rejected with `ErrInvalidPartOrder`).

---

## Error Code Precedence for Out-of-Range Duplicates {#error-code}

One subtle edge case is an input that is **both** out of range (`PartNumber < 1`) and duplicated, such as `[0, 0]` or `[-1, -1]`.

Because `CompleteMultipartUploadHandler` validates part ordering before iterating into the object layer (where individual part numbers are looked up and `ErrInvalidPart` is returned), inputs like `[0, 0]` previously passed `sort.SliceIsSorted` and failed later in the object layer with `InvalidPart` (HTTP 400). With strict ordering enforced up front, `[0, 0]` and `[-1, -1]` now fail immediately at the handler with `InvalidPartOrder` (HTTP 400). Both error codes map to HTTP `400 Bad Request` and neither is retriable; a single out-of-range part (`[0]` or `[-1]`) still reaches the part lookup and returns `InvalidPart`.

---

## Mutation Testing and a Misleading Comment {#mutations}

While verifying the unit tests in `cmd/object-handlers-multipart_test.go`, we ran two manual mutations against the handler:

1. **Mutating the check to require `Parts[0].PartNumber == 1`**: Immediately caught by the sparse-part regression tests (`[3]` and `[5, 9]`).
2. **Deleting the `len(complMultipartUpload.Parts) == 0` guard**: Our draft test comment originally claimed that removing the empty-parts guard in the handler would allow an empty multipart completion to succeed. Running that mutation revealed something much more interesting: an empty `Parts` slice bypassed the handler check, entered the object layer, and triggered an index-out-of-range panic in `ReadParts` (`cmd/storage-rest-client.go`) inside an errgroup goroutine.

That second mutation served two purposes: we corrected the misleading comment in `cmd/object-handlers-multipart_test.go`, and we fixed `ReadParts` in commit `2602177ef` (also shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)) so that an empty `partNumbers` slice returns early instead of indexing `partNumbers[0]`.

---

## Declined Changes and Follow-Ups {#declined}

- **No retrospective repair tool**: Existing objects assembled from duplicate part lists before `20260804` have valid erasure metadata for their logical size; automatic truncation or deduplication would risk corrupting objects intentionally assembled from identical chunks.
- **No duplicate object-layer check**: As noted in [Handler vs. Object-Layer Boundary](#boundary), internal callers construct part lists from validated metadata, and `2602177ef` closes the `ReadParts` empty-slice boundary found during mutation testing.

## Review Record {#review}

Three independent review passes verified the handler predicate, error-code precedence (`InvalidPartOrder` vs. `InvalidPart`), sparse part numbering (`[3]` and `[5, 9]`), and the `ReadParts` empty-slice guard (`2602177ef`).

## Summary {#closing}

Shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`5df7b5466` and `2602177ef`), `CompleteMultipartUploadHandler` enforces strict part-number monotonicity (`PartNumber[i-1] < PartNumber[i]`) and `ReadParts` safely rejects empty part-number slices.
