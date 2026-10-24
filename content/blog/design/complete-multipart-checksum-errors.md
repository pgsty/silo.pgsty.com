---
title: "BadDigest, InvalidRequest, and the CompleteMultipartUpload Checksum Contract"
linkTitle: "Multipart Checksum Errors"
date: 2026-08-27
lastmod: 2026-10-19
author: "Ruohang Feng"
summary: >
  CompleteMultipartUpload validates stored checksum types and returns operation-specific S3 error codes. CRC64NVME plus COMPOSITE is rejected in Server 20260903, and streaming-checksum validation shipped in Server 20260916.
tags: [Design, S3, Compatibility, Checksum]
weight: 31
draft: false
url: "/blog/design/complete-multipart-checksum-errors/"
---

The repairs for [#48](https://github.com/pgsty/silo/issues/48) and [#50](https://github.com/pgsty/silo/issues/50) shipped in [Server 20260903](/blog/release/silo-20260903/), and the streaming-checksum follow-up ([PR #143](https://github.com/pgsty/silo/pull/143)) shipped in [Server 20260916](/blog/release/silo-20260916/). This record supersedes the earlier August proposal to leave `CRC64NVME` canonicalization unchanged.

## 20261018: Message Text and Commit Failures {#october-errors}

[Server 20261018](/blog/release/silo-20261018/#reliability) includes the message fixes from [#225](https://github.com/pgsty/silo/issues/225), [#229](https://github.com/pgsty/silo/issues/229), and [#238](https://github.com/pgsty/silo/issues/238): S3-compatible `Content-MD5` capitalization, known algorithm names for `PutObject` and `UploadPart` mismatches, and removal of redundant "checksum" wording at completion. Unknown algorithms retain the generic description, and operation-specific error codes and validation requirements remain unchanged. The unchanged `UploadPart` mapper described below refers to the August repair scope; October updates its message rendering. Clients should match HTTP and S3 error codes rather than parse the full English message text.

Separately, [#232](https://github.com/pgsty/silo/issues/232) classifies staged `xl.meta` loss at final commit as `503 SlowDownWrite`. That status is distinct from the HTTP 400 client-checksum errors in the table below and does not change genuine incomplete-body handling. See the [S3 write-commit reference](/reference/s3-api-compatibility/#write-commit-errors).

## Why Validation Belongs at Completion {#problem}

`CreateMultipartUpload` selects the checksum algorithm and object checksum type, and each `UploadPart` call records its part checksum. `CompleteMultipartUpload` must validate both the final digest and any explicit type assertion against that stored contract. A completion request cannot change `COMPOSITE` to `FULL_OBJECT` merely because both share the same base algorithm, nor can it bypass a mismatched type assertion by omitting the final digest.

The repair distinguishes an omitted checksum type from an explicit type assertion and normalizes only internal representation flags. It introduces operation-specific error types for multipart completion while leaving `UploadPart` and the global checksum-mismatch error mapper unchanged.

## Current Error Contract {#tests}

All validation failures below return HTTP 400 and do not commit a completed object.

| Request Condition | S3 Error |
| --- | --- |
| Wrong full-object or composite object digest | `BadDigest` |
| Explicit supported type differs from the initiated type, including a type-only assertion | `BadDigest` |
| Unknown or lowercase type token | `InvalidArgument` |
| Completion algorithm differs from the initiated algorithm | `InvalidArgument` |
| Missing required composite part checksum | `InvalidRequest` (naming the algorithm and part number) |
| `CRC64NVME` with `COMPOSITE` at initiation | `InvalidArgument` |
| `CRC64NVME` value with `COMPOSITE` rejected by checksum parsing at completion | `InvalidArgument` |
| Bare `COMPOSITE` type at completion of a `CRC64NVME` `FULL_OBJECT` upload | `BadDigest` |
| Incorrect client checksum during `UploadPart` | `XAmzContentChecksumMismatch` |

For `FULL_OBJECT` uploads, per-part checksums in the completion XML may be omitted, while any supplied part checksums are still validated against stored part metadata. Matching type-only assertions are accepted. Omitting the optional checksum type header does not assert `COMPOSITE`. Combining `SHA1` or `SHA256` with `FULL_OBJECT` is rejected by the algorithm-and-type parser before reaching the stored-type comparison.

## CRC64NVME Decision and Source Evidence {#issue-50}

An early review considered deferring [#50](https://github.com/pgsty/silo/issues/50) pending further SDK compatibility evidence, where `CRC64NVME + COMPOSITE` had been silently canonicalized to `FULL_OBJECT`. That silent canonicalization hid invalid client requests instead of failing fast. [PR #93](https://github.com/pgsty/silo/pull/93) rejects the invalid `CRC64NVME + COMPOSITE` combination in both headers and trailers, and [PR #96](https://github.com/pgsty/silo/pull/96) removes the silent canonicalization during `CompleteMultipartUpload`. Because completion can fail either during header parsing (when both a `CRC64NVME` digest and `COMPOSITE` type are supplied) or during stored-type comparison (when only a bare `COMPOSITE` type header is sent against an initiated `CRC64NVME` `FULL_OBJECT` upload), the table above records two distinct error codes (`InvalidArgument` and `BadDigest`).

The initial completion error mapping landed in [PR #74](https://github.com/pgsty/silo/pull/74), with the explicit type-assertion follow-up (`7e079ff05`) merged through [PR #85](https://github.com/pgsty/silo/pull/85). The handler test suite in [`cmd/erasure-multipart-fullobject_test.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-multipart-fullobject_test.go) exercises full-object and composite digest mismatches, type-only assertions, invalid tokens, and both `CRC64NVME` rejection stages.

## Separate Streaming-Checksum Follow-Up {#streaming}

[PR #143](https://github.com/pgsty/silo/pull/143), resolving [#107](https://github.com/pgsty/silo/issues/107) (reported by `@cbornet`), handles `aws-chunked` requests that advertise `x-amz-trailer` but supply the checksum in a standard HTTP header—a pattern used by the AWS Java SDK v2. It also rejects invalid header-delivered checksum values instead of dropping validation. This streaming-checksum repair shipped in [Server 20260916](/blog/release/silo-20260916/) and is independent of multipart completion error mapping.

## Compatibility and Remaining Boundaries {#impact}

Callers that inspect S3 error codes receive `BadDigest` for completion digest or type mismatches and `InvalidRequest` for missing composite part checksums. Successful checksum-free multipart uploads and ETag semantics are unchanged, and no on-disk metadata migration is required. Related multipart completion contracts are covered in [CompleteMultipartUpload ChecksumType](/blog/design/complete-multipart-checksum-type/), [UploadPart Checksum](/blog/design/uploadpart-checksum/), and the [Duplicate Part Numbers Security Advisory](/blog/security/duplicate-part-numbers/).

Three narrower edge behaviors remain documented boundaries:

- Supplying a final checksum digest at completion when `CreateMultipartUpload` recorded no checksum algorithm is rejected as `BadDigest`.
- Composite part-count mismatches and composite digest mismatches share the same `BadDigest` error description.
- A `-N` part-count suffix attached to a `FULL_OBJECT` checksum header is ignored rather than validated as a part count.
