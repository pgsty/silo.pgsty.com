---
title: "Why CompleteMultipartUpload Must Return ChecksumType: Review of PR #57"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The completion response now returns the stored checksum type. Included in Server 20260903; scope, evidence and adjacent validation changes.
tags: [Design, S3, Compatibility, Checksum]
weight: 20
draft: false
url: "/blog/design/complete-multipart-checksum-type/"
---

[PR #57](https://github.com/pgsty/silo/pull/57), contributed by Shooks
(@Dansyuqri), fixed [#47](https://github.com/pgsty/silo/issues/47). The repair
is included in [Server 20260903](/blog/release/silo-20260903/).
This records the response contract; production deployment remains specific to
the artifact and installation an operator actually runs.

## The defect and its scope {#origin}

Investigation of @cbornet's [#31](https://github.com/pgsty/silo/issues/31)
separated two defects. Multipart CRC32 completion itself was repaired by
`c8590413f` and `3e14733f1`. After successful completion, the object retained its
checksum type and HEAD could return it, but completion XML omitted that type.
SDK callers therefore saw a missing `ChecksumType` beside a valid checksum value.

This omission did not corrupt stored data. It made a full-object checksum and
a composite checksum harder to distinguish. Their Base64 encodings do not tell
a consumer which calculation to reproduce.

## Response contract {#contract}

| Stored state | Completion response |
| --- | --- |
| Full-object checksum | `ChecksumType=FULL_OBJECT` with its algorithm value |
| Composite multipart checksum | `ChecksumType=COMPOSITE` with its algorithm value |
| No additional checksum | No `ChecksumType` element; no invented checksum |

The [S3 completion API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)
defines the two type values. ETag is a separate field and is not a substitute for
the additional S3 checksum.

## Implementation and evidence {#implementation}

The production change adds `ChecksumType string` with
`xml:"ChecksumType,omitempty"` to `CompleteMultipartUploadResponse` and assigns
`cs[xhttp.AmzChecksumType]` after decoding the stored checksum metadata. The
generator reuses the same state as the other checksum APIs; it does not
recalculate content or infer a type from part count.

The [merged PR](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee)
contains response tests for full-object, composite and absent checksums. The
original change also registered the exported field in the then-current rebrand
inventory. That inventory's exported-symbol section was subsequently removed by
`bc3b35f97`; it is not a current public API compatibility guarantee.

## Compatibility and adjacent work {#impact}

Readers that ignore unknown XML elements remain compatible. No new algorithm,
stored metadata format, object migration or checksum bypass was introduced.
The [UploadPart repair](/blog/design/uploadpart-checksum/) and
[completion validation](/blog/design/complete-multipart-checksum-errors/)
are separate changes, also included in Server 20260903. In particular,
`CRC64NVME + COMPOSITE` is rejected, not silently normalized.

<span id="algorithm-scope"></span>
<span id="baseline"></span>
<span id="before"></span>
<span id="conclusion"></span>
<span id="decision"></span>
<span id="evaluation"></span>
<span id="field"></span>
<span id="mapping"></span>
<span id="merge-sequence"></span>
<span id="notes"></span>
<span id="review"></span>
<span id="strengths"></span>
<span id="tests"></span>
<span id="tldr"></span>
<span id="why-it-works"></span>
