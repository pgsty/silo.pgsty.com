---
title: "BadDigest, InvalidRequest, and the CompleteMultipartUpload Checksum Contract"
linkTitle: "Multipart Checksum Errors"
date: 2026-08-27
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Completion validates stored checksum types and returns operation-specific errors. CRC64NVME plus COMPOSITE is rejected in Server 20260903; streaming follow-up remains separate.
tags: [Design, S3, Compatibility, Checksum]
weight: 31
draft: false
url: "/blog/design/complete-multipart-checksum-errors/"
---

The repairs for [#48](https://github.com/pgsty/silo/issues/48) and
[#50](https://github.com/pgsty/silo/issues/50) are included in
[Server 20260903](/blog/release/silo-20260903/). This record supersedes the
August proposal to leave CRC64NVME canonicalization unchanged.

## Why validation belongs at completion {#problem}

Initiation selects the checksum algorithm and object type; each part records
its checksum. Completion must validate the final value and any explicit type
assertion against that stored contract. A request cannot change `COMPOSITE` to
`FULL_OBJECT` just because both share the same base algorithm, or bypass the
assertion by omitting the final digest.

The repair distinguishes an omitted type from an explicit type and normalizes
only internal representation flags. It uses operation-specific error types,
leaving UploadPart and the global checksum-mismatch mapper unchanged.

## Current error contract {#tests}

All failures below return HTTP 400 and do not commit a new completed object.

| Request condition | S3 error |
| --- | --- |
| Wrong full-object or composite object digest | `BadDigest` |
| Explicit supported type differs from the initiated type, including a type-only assertion | `BadDigest` |
| Unknown or lowercase type token | `InvalidArgument` |
| Completion algorithm differs from the initiated algorithm | `InvalidArgument` |
| Missing required composite part checksum | `InvalidRequest`, naming the algorithm and part |
| CRC64NVME with COMPOSITE at initiation | `InvalidArgument` |
| CRC64NVME value with COMPOSITE rejected by checksum parsing at completion | `InvalidArgument` |
| Bare COMPOSITE type at completion of a CRC64NVME FULL_OBJECT upload | `BadDigest` |
| Incorrect client checksum during UploadPart | Existing `XAmzContentChecksumMismatch` |

For `FULL_OBJECT`, part checksums may be omitted; any supplied values remain
validated. Matching type-only assertions are allowed. An omitted optional type
does not assert `COMPOSITE`. SHA1/SHA256 with `FULL_OBJECT` are rejected by the
algorithm/type parser before the stored-type comparison.

## CRC64NVME decision and source evidence {#issue-50}

The original review deferred #50 pending evidence; that is historical, not the
current contract. [PR #93](https://github.com/pgsty/silo/pull/93) rejects the
invalid algorithm/type combination in headers and trailers, and
[PR #96](https://github.com/pgsty/silo/pull/96) removes completion's canonicalization.
Both precede the 20260903 tag. Completion can fail at either parsing or stored-type
comparison, which explains the two distinct error codes above.

The initial mapping is in [PR #74](https://github.com/pgsty/silo/pull/74), with
the explicit type follow-up `7e079ff05` merged through
[PR #85](https://github.com/pgsty/silo/pull/85). Current
[handler tests](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-multipart-fullobject_test.go)
exercise full-object and composite mismatches, type-only assertions, invalid
tokens and both CRC64NVME rejection stages. This is committed regression
coverage, not a claim that this documentation update reran all Server tests.

## Separate streaming-checksum follow-up {#streaming}

[PR #143](https://github.com/pgsty/silo/pull/143), following @cbornet's
[#107](https://github.com/pgsty/silo/issues/107), handles an `aws-chunked` request
that advertises `x-amz-trailer` but supplies its checksum in a header, as used by
the AWS Java SDK v2. It also rejects an invalid header-delivered value instead
of dropping validation. This later repair is on main and **not in Server
20260903**. It is separate from completion error mapping.

## Compatibility and remaining boundaries {#impact}

Callers that inspect error codes now see checksum/type failures as `BadDigest`
and missing composite values as `InvalidRequest`. Successful checksum-free
uploads and ETag semantics are unchanged. No metadata migration is required.

Several narrower differences remain: providing a final digest when initiation
recorded no checksum is rejected as `BadDigest`; composite part-count and value
mismatches share one description; a `-N` suffix on a full-object checksum is
not itself validated as a part count. These are documented observations, not
claims of separately filed public issues or complete AWS parity.

<span id="conclusion"></span>
<span id="contract"></span>
<span id="design"></span>
<span id="evidence"></span>
<span id="gates"></span>
<span id="independent-review"></span>
<span id="issue-50-probe"></span>
<span id="missing-part"></span>
<span id="operation-scoped"></span>
<span id="precise-missing"></span>
<span id="scope"></span>
<span id="symmetric-validation"></span>
<span id="tldr"></span>
<span id="type-mismatch"></span>
<span id="type-only-follow-up"></span>
<span id="upstream"></span>
<span id="value-mismatch"></span>
