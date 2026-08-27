---
title: "BadDigest, InvalidRequest, and the CompleteMultipartUpload Checksum Contract"
linkTitle: "Multipart Checksum Errors"
date: 2026-08-27
author: "Ruohang Feng"
summary: >
  SILO rejected three invalid CompleteMultipartUpload requests, but returned the wrong S3 error codes and missed one checksum-type mismatch direction. This record establishes the AWS evidence, upstream history, root cause, operation-scoped repair, regression matrix, and the separate evidence gate for CRC64NVME plus COMPOSITE.
tags: [Design, S3, Compatibility, Checksum]
weight: 31
draft: false
url: "/blog/design/complete-multipart-checksum-errors/"
---

This is the design, investigation, and verification record for [SILO #48](https://github.com/pgsty/silo/issues/48), with the decision boundary for the related [SILO #50](https://github.com/pgsty/silo/issues/50).

> **Status:** server implementation, full local package verification, and independent final re-review complete; commit, PR, remote CI, release, and deployment pending.<br>
> **Owner:** [`pgsty/silo`](https://github.com/pgsty/silo), the SILO server repository.<br>
> **Implementation scope:** `CompleteMultipartUpload` error semantics only; no storage-format, checksum-math, dependency, Console, package, or client change.<br>
> **Independent decision:** #50 remains probe-gated and is not part of this repair.

## Too Long; Didn't Read (TL;DR) {#tldr}

Issue #48 is valid and should be fixed, with two corrections to the original report.

First, the checksum-type comparison is worse than the issue states. SILO used bitmask containment instead of equality. An upload created as `FULL_OBJECT` and completed as `COMPOSITE` failed, but the reverse `COMPOSITE` to `FULL_OBJECT` direction could pass the type check. The repair must compare the base algorithm and normalized multipart object type independently and symmetrically.

Second, the missing-part-checksum row originally lacked a direct AWS capture. That evidence now exists in the official boto/s3transfer project: [issue #241](https://github.com/boto/s3transfer/issues/241) records a real S3 `InvalidRequest` response naming `sha256` and missing part 1, and [PR #242](https://github.com/boto/s3transfer/pull/242) repaired the client and added tests. This is strong enough to implement the response contract without a new AWS account probe.

The accepted behavior is:

| `CompleteMultipartUpload` failure | SILO before | Required behavior |
| --- | --- | --- |
| Supplied object checksum does not match the assembled object | `XAmzContentChecksumMismatch` | `BadDigest` |
| Completion checksum type differs from initiation, in either direction | one direction `InvalidArgument`; reverse direction could pass | `BadDigest` |
| A composite completion omits a checksum for a part | `InvalidPart` | `InvalidRequest`, naming the algorithm and part |

The repair uses completion-specific error types. It deliberately does **not** change the global mapping of `hash.ChecksumMismatch`, so `PutObject`, `UploadPart`, streaming trailers, and other operations retain their existing `XAmzContentChecksumMismatch` contract.

Issue #50 is a separate question. AWS documents that CRC64NVME is full-object only, but the available sources do not prove that S3 rejects an explicit `CRC64NVME + COMPOSITE` initiation instead of canonicalizing it. Upstream MinIO intentionally implemented canonicalization and exposes `FULL_OBJECT` in the initiation response, so the behavior is not silent. A raw AWS probe is required before changing it.

## Scope and decision {#scope}

This record answers two different questions:

1. Are the #48 error-code deviations real, externally observable compatibility defects with enough evidence to repair?
2. Does the same evidence authorize changing the CRC64NVME canonicalization described by #50?

The decisions are:

- **#48: accept with corrections and implement.** The error codes are part of the S3 wire contract. Returning a different code makes SDK behavior and operator diagnosis diverge even when the request is rejected in both systems.
- **#50: do not implement yet.** The capability matrix proves the resulting checksum must be full-object. It does not establish whether an invalid requested type is rejected, ignored, or canonicalized. Those are different wire contracts.

The repair is intentionally narrow. It does not add algorithms, recalculate stored data, reinterpret successful uploads, or change the optionality rules repaired for [#31](https://github.com/pgsty/silo/issues/31) and [#46](https://github.com/pgsty/silo/issues/46).

## Evidence ledger {#evidence}

Not all evidence has the same authority. The implementation decision uses the following hierarchy.

| Grade | Source | What it establishes | Limitation |
| --- | --- | --- | --- |
| A | [AWS checksum upload guide](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html) | A supplied full-object checksum mismatch fails with `BadDigest`; algorithm/type capability matrix | Does not show every response message |
| A | [AWS CompleteMultipartUpload API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) and [AWS CLI reference](https://docs.aws.amazon.com/cli/latest/reference/s3api/complete-multipart-upload.html) | A completion checksum type that differs from initiation fails with `BadDigest` | Does not publish the exact message text |
| B+ | [boto/s3transfer #241](https://github.com/boto/s3transfer/issues/241) | Real AWS S3 transcript: missing SHA256 checksum for part 1 returns `InvalidRequest` and names the algorithm and part | Captured in an official SDK project issue rather than an AWS API reference page |
| B+ | [boto/s3transfer #242](https://github.com/boto/s3transfer/pull/242) and the 0.6.1 changelog | The official transfer client was changed to forward UploadPartCopy checksums into completion; functional coverage prevents recurrence | Primarily client-side evidence |
| B | Local API probes and regression tests | SILO's old `XAmzContentChecksumMismatch`, `InvalidArgument`, `InvalidPart`, and reverse-direction bypass are reproducible on both object-layer backends | Establishes SILO, not AWS |
| C | Upstream MinIO history | Explains how the current behavior entered the lineage and why it remains | Intent is not proof of AWS parity |

This distinction matters. The original #48 comment correctly downgraded the third row while it was supported only by secondary reports. The boto transcript and the merged client repair close that evidence gap.

## The observable contract {#contract}

### Object checksum mismatch {#value-mismatch}

For a `FULL_OBJECT` multipart upload, SILO combines stored part checksums and compares the result with the optional object checksum supplied on completion. The old code returned `hash.ChecksumMismatch`. A global API mapping converted that type to:

```text
400 XAmzContentChecksumMismatch
```

AWS explicitly documents `BadDigest` for the corresponding completion integrity failure. Reusing the existing generic `ErrBadDigest` code without a custom message would still be misleading because its static text says `Content-MD5`; CRC32, CRC32C, and CRC64NVME are not Content-MD5.

The new response is therefore operation-specific:

```text
400 BadDigest
The CRC32 checksum you specified did not match the calculated checksum.
```

The response does not disclose the expected or supplied digest.

### Checksum type mismatch {#type-mismatch}

The checksum type saved by `CreateMultipartUpload` is part of the upload's contract. A completion may not switch between `COMPOSITE` and `FULL_OBJECT`.

The old test was:

```go
!provided.Type.Is(expectedType)
```

`ChecksumType.Is` is a containment operation over a bitmask, not equality. For CRC32:

```text
created FULL_OBJECT + completed COMPOSITE => rejected
created COMPOSITE   + completed FULL_OBJECT => containment succeeds
```

The second request could proceed using the persisted composite rules. If the caller supplied the composite checksum value under a `FULL_OBJECT` declaration, completion could even succeed. This is a protocol validation bypass, not merely the wrong error label.

The repair normalizes both values into multipart checksum types, then compares:

1. base algorithm equality; and
2. object type equality (`COMPOSITE` versus `FULL_OBJECT`).

Both mismatch directions now return `400 BadDigest`. Algorithm mismatch remains a separate `InvalidArgument` path because #48 and the cited AWS type contract do not authorize broadening that behavior.

### Missing composite part checksum {#missing-part}

For a composite upload, the completion XML must include the selected checksum for every listed part. SILO previously compared an empty client value with the stored part checksum and returned `InvalidPart`.

That conflated three different states:

- the part or ETag does not exist;
- a checksum was supplied but has the wrong value or algorithm;
- the required checksum element is absent.

The third state now has a dedicated error. Its wire message follows the AWS response captured by boto/s3transfer:

```text
400 InvalidRequest
The upload was created using a sha256 checksum. The complete request must include
the checksum for each part. It was missing for part 1 in the request.
```

The error is emitted for the first missing part and includes its actual number. `FULL_OBJECT` behavior is unchanged: a completion may omit per-part checksum elements, while any supplied part checksum must still be valid.

## Root cause in the upstream lineage {#upstream}

The behavior is inherited rather than a SILO-specific redesign.

- [MinIO PR #15433](https://github.com/minio/minio/pull/15433) introduced extended checksum handling and the global `hash.ChecksumMismatch` to `XAmzContentChecksumMismatch` mapping. That mapping is suitable for streaming upload validation but too broad for completion semantics.
- [MinIO PR #20855](https://github.com/minio/minio/pull/20855) added full-object checksums and CRC64NVME. It introduced the checksum-type comparison and intentionally canonicalized CRC64NVME to full-object with the comment that AWS appears to ignore the supplied mode.
- [MinIO PR #20953](https://github.com/minio/minio/pull/20953) tightened invalid algorithm/type combinations but retained the CRC64NVME special case. That is evidence of deliberate upstream behavior, not an accidental missing branch.
- [MinIO issue #20944](https://github.com/minio/minio/issues/20944) reported an AWS `BadDigest` versus MinIO `InvalidPart` difference. The divergence was acknowledged but not repaired.

The upstream repository is now archived. SILO therefore owns the compatibility decision, tests, and maintenance burden rather than waiting for an upstream correction.

## Repair design {#design}

### Operation-scoped errors {#operation-scoped}

Changing the global `hash.ChecksumMismatch` mapping would alter every operation that uses it. That would be a larger, weakly evidenced compatibility change.

The repair adds three package-private, sentinel-backed error helpers in the server command package. Keeping the helpers and the request-header-presence flag private avoids expanding SILO's exported Go compatibility surface:

- `completeMultipartChecksumMismatch`, mapped to `BadDigest` with a checksum-aware description;
- `completeMultipartChecksumTypeMismatch`, mapped to `BadDigest` with provided and initiated types;
- `missingPartChecksum`, mapped to `InvalidRequest` with algorithm and part number.

Only `CompleteMultipartUpload` produces these types. The global mapping remains:

```text
hash.ChecksumMismatch => XAmzContentChecksumMismatch
```

This preserves `PutObject` and `UploadPart` behavior and makes the compatibility boundary visible in code.

### Symmetric type validation {#symmetric-validation}

Both persisted and supplied types are normalized with the multipart flags before comparison. This is necessary because a bare CRC checksum type describes a non-multipart full-object checksum through `ObjType()`, while the same base value means composite after multipart context is applied. Object type is compared only when the completion request explicitly contains `x-amz-checksum-type`; omitting an optional header does not synthesize a `COMPOSITE` assertion.

The resulting invariant is:

```text
provided base algorithm == initiated base algorithm
AND
provided multipart object type == initiated multipart object type
```

The second condition applies only to an explicitly supplied type. This comparison is symmetric and remains compatible with the existing CRC64NVME canonicalization. It fixes #48 without silently deciding #50.

### Precise missing-value detection {#precise-missing}

For each part, the server already builds a map of all checksum fields supplied in the completion XML. The repair distinguishes:

```text
COMPOSITE + no checksum field supplied => missingPartChecksum / InvalidRequest
expected field present but wrong value => InvalidPart
only a different algorithm supplied    => InvalidPart
FULL_OBJECT + no checksum field         => allowed
FULL_OBJECT + any checksum field        => validate it
```

This is intentionally narrower than converting every part checksum failure to `InvalidRequest`. Only the state demonstrated by AWS evidence changes.

The same edit corrects the internal `InvalidPart` expected/actual field order. The generic S3 `InvalidPart` wire response did not expose those digest values, but internal error text and logs should still describe them correctly.

## Regression and detection matrix {#tests}

The API-level tests exercise signed HTTP requests through both the single-drive and erasure object-layer backends.

| Test | Request | Required assertion |
| --- | --- | --- |
| Full-object digest mismatch | Correct parts, wrong object CRC32 | HTTP 400, `BadDigest`, checksum-aware message, no object committed |
| Composite object digest mismatch | Correct CRC32 part values, wrong composite object value | HTTP 400, `BadDigest`; covers the separate checksum-of-checksums path |
| Type mismatch: full to composite | Initiate `FULL_OBJECT`, complete `COMPOSITE` | HTTP 400, `BadDigest`, provided/expected types named |
| Type mismatch: composite to full | Initiate `COMPOSITE`, complete `FULL_OBJECT` | HTTP 400, `BadDigest`; closes old containment bypass |
| Omitted optional type | Initiate `FULL_OBJECT`, complete with checksum value but no type header | Success; omission is not treated as explicit `COMPOSITE` |
| Algorithm mismatch guard | Initiate CRC32, complete with CRC32C | Still `InvalidArgument` |
| CRC64NVME #50 guard | Initiate and complete CRC64NVME with explicit `COMPOSITE` | Still succeeds through existing full-object canonicalization |
| Missing composite checksum | CRC32 and SHA256 composite uploads; omit all values, then omit only part 2 | HTTP 400, `InvalidRequest`, lowercase algorithm and actual missing part named |
| Global-mapping guard | Direct `hash.ChecksumMismatch` mapping | Still `XAmzContentChecksumMismatch` |
| UploadPart guard | Wrong client part checksum | Still `XAmzContentChecksumMismatch` |

Focused verification command:

```bash
go test ./cmd -run 'TestAPIErrCode$|TestAPICompleteMultipart(FullObjectChecksumMismatch|CompositeStillRequiresPartChecksums|CompositeChecksumMismatch|ChecksumTypeMismatch)$|TestAPIUploadPartServerSideChecksumDoesNotMaskClientErrors$' -count=1
```

Observed result on 2026-08-27:

```text
ok  github.com/minio/minio/cmd
```

The complete local package gate was then rerun after the review-driven additions:

```bash
go test ./cmd ./internal/hash -count=1
```

```text
ok  github.com/minio/minio/cmd           121.462s
ok  github.com/minio/minio/internal/hash   0.566s
```

`git diff --check` also passed. Independent review of the final diff remains a separate gate. A local pass is not remote CI, a merged commit is not a release, and a release is not production deployment.

## Independent adversarial review {#independent-review}

The first review of the actual server diff was performed with local Claude Code in read-only safe mode. Its verdict was **GO with no blocking findings**. It independently confirmed the operation-scoped mapping, symmetric bitmask normalization, per-part missing-value detection, both object-layer backends, and preservation of UploadPart behavior.

The review identified four useful gaps that were incorporated before the second full test run:

- distinguish an omitted optional type header from an explicit `COMPOSITE` assertion;
- separate value-mismatch and type-mismatch error types;
- exercise the composite checksum-of-checksums mismatch path;
- pin missing part 2, algorithm mismatch, and unchanged CRC64NVME canonicalization.

One first-review concern was rejected by primary evidence: it questioned whether checksum **type** mismatch should return `InvalidRequest`. The [AWS CompleteMultipartUpload reference](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) and [AWS CLI reference](https://docs.aws.amazon.com/cli/latest/reference/s3api/complete-multipart-upload.html) explicitly specify `BadDigest` when the completion type differs from initiation.

The final re-review verdict was **FINAL GO, no blockers**. It explicitly withdrew the earlier error-code concern, agreed with accepting #48 and deferring #50, verified that the new guards preserve the intended non-changes, and found no English/Chinese drift.

Three pre-existing, non-blocking observations remain outside this repair:

- composite part-count and value mismatches both become `BadDigest` with the same description;
- a full-object checksum carrying a `-N` suffix has that suffix ignored while its digest is still validated;
- an unrecognized non-empty `x-amz-checksum-type` is parsed as composite rather than rejected.

None is introduced by this patch, and none changes the #48 decision. They should be triaged separately if strict message or invalid-header parity becomes a maintenance priority.

## Why #50 is not included {#issue-50}

Issue #50 says `CRC64NVME + COMPOSITE` should be rejected at initiation. Three facts are confirmed:

1. AWS's algorithm matrix supports CRC64NVME only as a full-object checksum.
2. SILO and upstream MinIO canonicalize the request to full-object state.
3. The server returns `x-amz-checksum-type: FULL_OBJECT` from `CreateMultipartUpload`, so the substitution is externally visible rather than silent.

What is not confirmed is the decisive wire behavior: does AWS reject the explicit invalid combination, or accept it and return/carry full-object state? A capability matrix does not answer that question.

The upstream history also argues against guessing. PR #20855 added the canonicalization intentionally, and PR #20953 preserved it while tightening other invalid combinations. That may be based on an AWS observation, but the comment is not a reproducible transcript.

`PutObject` must not be bundled into this decision. Its API reference does not define `x-amz-checksum-type`, so accepting, rejecting, or ignoring that header is a separate undocumented-header question.

### Required AWS probe {#issue-50-probe}

Before changing #50, capture a raw SigV4 request and response against a general-purpose AWS S3 bucket:

1. send `CreateMultipartUpload` with `x-amz-checksum-algorithm: CRC64NVME` and `x-amz-checksum-type: COMPOSITE`;
2. record the HTTP status, error code/message, request ID, and all checksum response headers;
3. if accepted, upload one part and complete it, recording whether S3 requires per-part values and which type `HeadObject` reports;
4. repeat with `FULL_OBJECT` as the control;
5. probe `PutObject` separately, explicitly labeling it as an undocumented-header experiment.

Only a captured rejection authorizes replacing canonicalization with validation. If AWS accepts and canonicalizes, #50 should be corrected or closed rather than implemented.

## Compatibility and operational impact {#impact}

- **Successful requests:** unchanged.
- **Rejected requests:** HTTP status remains 400; S3 error code and message become AWS-compatible.
- **Integrity:** unchanged or stronger. The reverse type-bypass is closed; no failed completion commits an object.
- **Stored data:** no format, checksum encoding, metadata, erasure layout, migration, or backfill change.
- **Performance:** constant-time comparisons and error construction only; no additional data reads or hashing passes.
- **Security/privacy:** digest values are not returned in the new messages. Bucket and object names are not added to them.
- **Rolling upgrade:** nodes may return different error codes until all serving nodes are upgraded, but successful objects remain compatible.
- **Rollback:** restores the old error codes and asymmetric check; it does not require data rollback.
- **Other repositories:** no Console, shared-package, MCLI, or SDK change is required. This public design record is the only cross-repository deliverable.

## Merge and release gates {#gates}

Before merge:

1. complete the package-level test matrix and formatting checks;
2. obtain an independent review of the actual server diff and this evidence record;
3. keep #50 out of the patch unless a raw AWS transcript changes the decision;
4. run remote DCO, Go CI, vulnerability, and release-pipeline checks on the final commit;
5. confirm the branch is based on the current SILO `main` before merge.

After merge, record repository integration, release artifact, container image, deployment, and production probe as separate gates. None can be inferred from a local test or a documentation build.

## Conclusion {#conclusion}

#48 is a correct compatibility issue, and the evidence now covers all three rows. The safest repair does not relabel checksum failures globally. It teaches `CompleteMultipartUpload` to report its own protocol errors, compares checksum types symmetrically, and identifies a genuinely missing composite part checksum without confusing it with a missing part or a wrong value.

#50 is related by discovery history, not by proof. The server's current CRC64NVME canonicalization is deliberate and visible. Until AWS's exact response is captured, changing it would replace one unverified assumption with another.

That boundary is the central design decision: implement what the official contract and tests establish, test the hidden consequence found in the code, and leave the remaining policy question behind an explicit, reproducible evidence gate.
