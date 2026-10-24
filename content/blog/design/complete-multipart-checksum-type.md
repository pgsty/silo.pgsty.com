---
title: "Why CompleteMultipartUpload Must Return ChecksumType: Review of PR #57"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  CompleteMultipartUpload now returns the stored ChecksumType in its XML response body. Included in Server 20260903 alongside UploadPart and completion validation repairs.
tags: [Design, S3, Compatibility, Checksum]
weight: 20
draft: false
url: "/blog/design/complete-multipart-checksum-type/"
---

[PR #57](https://github.com/pgsty/silo/pull/57), contributed by Shooks (`@Dansyuqri`), resolved [#47](https://github.com/pgsty/silo/issues/47) and shipped in [Server 20260903](/blog/release/silo-20260903/). It restores the `ChecksumType` element in `CompleteMultipartUpload` XML responses whenever an object stores an additional S3 checksum.

## The Defect and Its Scope {#origin}

Investigation of [#31](https://github.com/pgsty/silo/issues/31) (reported by `@cbornet`) separated two distinct defects. Multipart `CRC32` completion calculation was repaired by commits `c8590413f` and `3e14733f1`. After a multipart upload completed, the stored object retained its checksum type and `HeadObject` or `GetObject` returned it, but the `CompleteMultipartUpload` XML response omitted `ChecksumType`. S3 SDK callers therefore received a valid checksum digest alongside a missing `ChecksumType`.

Although this omission did not corrupt stored object data, it prevented callers from distinguishing a `FULL_OBJECT` checksum from a `COMPOSITE` checksum using the completion response alone. Because both modes use the same Base64 digest length for a given algorithm, the digest string by itself does not indicate which calculation a verifier should reproduce.

## Response Contract {#contract}

| Stored Checksum State | `CompleteMultipartUpload` Response |
| --- | --- |
| Full-object checksum | `ChecksumType=FULL_OBJECT` with the algorithm digest element |
| Composite multipart checksum | `ChecksumType=COMPOSITE` with the algorithm digest element |
| No additional checksum | No `ChecksumType` element and no synthesized checksum |

The [S3 `CompleteMultipartUpload` specification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) defines `FULL_OBJECT` and `COMPOSITE` as the two checksum types. The object `ETag` remains a separate response field and is not a substitute for additional S3 checksum metadata.

## Implementation and Evidence {#implementation}

The change adds `ChecksumType string` with struct tag `xml:"ChecksumType,omitempty"` to `CompleteMultipartUploadResponse` and assigns `cs[xhttp.AmzChecksumType]` after decoding the stored checksum metadata. The response builder reuses the exact stored state already exposed by `HeadObject` and `GetObject`; it does not recalculate object bytes or infer a checksum type from the part count.

The [merged commit (`a96116b12`)](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee) includes XML response tests covering `FULL_OBJECT`, `COMPOSITE`, and checksum-free multipart completions.

## Compatibility and Adjacent Work {#impact}

XML parsers that ignore unknown elements remain compatible, and SDKs that inspect `ChecksumType` (such as `silo-go` at [`bc3b35f97`](https://github.com/pgsty/silo-go/commit/bc3b35f973d981920cd83e8b5d2b30a45ec1b6dc)) receive the stored value immediately on completion. No new checksum algorithm, on-disk metadata format, or object migration was introduced.

Two adjacent multipart checksum repairs also shipped in [Server 20260903](/blog/release/silo-20260903/): [UploadPart checksum inference](/blog/design/uploadpart-checksum/) and [CompleteMultipartUpload checksum error mapping](/blog/design/complete-multipart-checksum-errors/), where `CRC64NVME + COMPOSITE` is explicitly rejected rather than silently canonicalized.
