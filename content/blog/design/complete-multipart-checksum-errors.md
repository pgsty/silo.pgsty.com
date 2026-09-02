---
title: "BadDigest, InvalidRequest, and the CompleteMultipartUpload Checksum Contract"
linkTitle: "Multipart Checksum Errors"
date: 2026-08-27
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  SILO rejected three invalid CompleteMultipartUpload requests, but returned the wrong S3 error codes and missed checksum-type validation paths. This record establishes the AWS evidence, upstream history, operation-scoped repair, type-only follow-up, regression matrix, and the separate evidence gate for CRC64NVME plus COMPOSITE.
tags: [Design, S3, Compatibility, Checksum]
weight: 31
draft: false
url: "/blog/design/complete-multipart-checksum-errors/"
---

This is the design, investigation, and verification record for [SILO #48](https://github.com/pgsty/silo/issues/48), with the decision boundary for the related [SILO #50](https://github.com/pgsty/silo/issues/50).

> **Status:** [`pgsty/silo#74`](https://github.com/pgsty/silo/pull/74) merged as `590aeaa7d`, and [`pgsty/silo.pgsty.com#6`](https://github.com/pgsty/silo.pgsty.com/pull/6) merged as `9805dd7`; full local verification, remote CI, and independent Opus 5 Max acceptance review completed on the linked changes. Tag, release, package, image, deployment, and production verification remain separate pending gates.<br>
> **2026-08-28 follow-up:** signed-off server commit `7e079ff05` closes the remaining type-only and invalid-token bypass without changing CRC64NVME canonicalization. Complete local, tagged, race, static, build, and Fable Max verification passed; it was merged into `main` on 2026-08-29, and tag and delivery remain pending.<br>
> **2026-09-02 update:** the CRC64NVME exception described below no longer holds. `main` now rejects `CRC64NVME` combined with `COMPOSITE` at multipart initiation, in trailers, and at completion with `InvalidArgument` (`d28885d0e`, `d4c8da162`, `32b2aa49f`), resolving [pgsty/silo#50](https://github.com/pgsty/silo/issues/50) by rejection rather than canonicalization. The reasoning below is kept as the record of the earlier decision.<br>
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
| Completion declares a different type but sends no whole-object checksum | type assertion ignored | `BadDigest` |
| Completion sends an unknown non-empty type, with or without a checksum value | could be ignored or interpreted through checksum defaults | `InvalidArgument` |
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

For algorithms whose two object-type forms are both syntactically accepted—currently CRC32 and CRC32C—both mismatch directions now return `400 BadDigest`. SHA1 and SHA256 with `FULL_OBJECT` are rejected earlier as `InvalidArgument`; CRC64NVME is the canonicalized special case discussed under #50 below. Base-algorithm mismatch remains a separate `InvalidArgument` path because #48 and the cited AWS type contract do not authorize broadening that behavior.

### Type-only assertions and invalid tokens {#type-only-follow-up}

The first #48 repair remembered whether `x-amz-checksum-type` was present, but its object-layer comparison was still nested under `WantChecksum != nil`. `WantChecksum` is populated only when completion carries a checksum value. A caller could therefore send a type assertion without a whole-object checksum:

```text
CreateMultipartUpload:   CRC32 + COMPOSITE
CompleteMultipartUpload: x-amz-checksum-type: FULL_OBJECT
                         no x-amz-checksum-crc32 value
```

The server returned success and persisted the initiated composite state. It did not corrupt the object, but it accepted an explicit integrity assertion that contradicted the upload contract.

There was a second parser asymmetry. In the header-without-algorithm path used by completion, an unknown value such as `NOT_A_TYPE` could be ignored when a checksum header was also present. Relying on `ChecksumType.ObjType()` after creating an invalid bitmask would not be safe: an invalid non-multipart value can fall through to the full-object default. Raw enum validation must happen first.

The follow-up stores the explicit raw type string in `ObjectOptions`, accepts only `COMPOSITE` or `FULL_OBJECT`, and compares it with the initiated multipart type independently of `WantChecksum`. The order is deliberate:

1. reject every unknown non-empty token as `InvalidArgument`;
2. compare the base algorithm when a checksum value is supplied;
3. compare the explicit object type whenever the upload recorded a checksum algorithm;
4. report an explicit type mismatch as `BadDigest` even when no object checksum value was supplied.

CRC64NVME remains a deliberate exception. A raw `COMPOSITE` token is normalized to `FULL_OBJECT` before comparison, preserving the inherited behavior pending the #50 AWS probe. A legal type-only header on an upload that recorded no checksum algorithm remains outside the comparison because there is no initiated checksum type to assert against; its exact AWS error semantics remain unproven and were not expanded into this repair.

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
| Type mismatch: full to composite | Initiate CRC32 `FULL_OBJECT`, complete `COMPOSITE` | HTTP 400, `BadDigest`, provided/expected types named |
| Type mismatch: composite to full | Initiate CRC32 `COMPOSITE`, complete `FULL_OBJECT` | HTTP 400, `BadDigest`; closes old containment bypass |
| Type-only mismatch in both directions | Initiate one CRC32 type; complete with the opposite type and no object checksum value | HTTP 400, `BadDigest`; the explicit assertion cannot bypass validation by omitting the digest |
| Invalid explicit type | Complete with `NOT_A_TYPE` or lowercase `full_object`, with and without a checksum value | HTTP 400, `InvalidArgument`, no object committed |
| Matching type-only assertion | Initiate and complete CRC32 `COMPOSITE`, omit object checksum value | Success; the valid assertion is enforced without inventing a required digest |
| Omitted optional type | Initiate `FULL_OBJECT`, complete with checksum value but no type header | Success; omission is not treated as explicit `COMPOSITE` |
| Algorithm mismatch guard | Initiate CRC32, complete with CRC32C | Still `InvalidArgument` |
| CRC64NVME #50 guard | Initiate CRC64NVME with explicit `COMPOSITE`, then complete with explicit `COMPOSITE` | Still succeeds through existing full-object canonicalization; records the completion-side residue rather than claiming #48 validates the raw type token |
| Missing composite checksum | CRC32 and SHA256 composite uploads; omit all values, then omit only part 2 | HTTP 400, `InvalidRequest`, lowercase algorithm and actual missing part named |
| Global-mapping guard | Direct `hash.ChecksumMismatch` mapping | Still `XAmzContentChecksumMismatch` |
| UploadPart guard | Wrong client part checksum | Still `XAmzContentChecksumMismatch` |

The committed type-mismatch regression uses CRC32, while an independent acceptance probe covered CRC32C as well. The follow-up additionally covers type-only, unknown, lowercase, matching, and checksum-bearing invalid-token cases. The same matrix confirms that SHA1/SHA256 `FULL_OBJECT` requests stop earlier at the existing invalid-combination check and that CRC64NVME still canonicalizes an explicit `COMPOSITE` token. Those distinctions are protocol boundaries, not untested claims that every algorithm reaches the same error mapper.

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

The final first-round re-review verdict was **FINAL GO, no blockers**. It explicitly withdrew the earlier error-code concern, agreed with accepting #48 and deferring #50, verified that the new guards preserve the intended non-changes, and found no English/Chinese drift.

A subsequent independent acceptance run used Claude Code `claude-opus-5` with maximum effort. It returned **ACCEPT, no blocking findings**, reproduced the old composite-as-`FULL_OBJECT` bypass end to end against the pre-fix code, verified that the new API assertions fail against that code, and probed all five checksum algorithms in both type directions.

The 2026-08-28 follow-up received a separate local Fable Max mirror review over the complete uncommitted release-review diff. It returned **GO**, with no P0–P2 findings. The primary review independently checked its seven P3 observations: five were non-blocking boundaries, while two proposed causes were disproved by the actual config and key-rotation call paths. The review confirmed that raw invalid types are rejected before normalization, type-only mismatch is enforced, source-side checksum decryption still receives the full request, and CRC64NVME canonicalization remains untouched.

Five pre-existing or deliberately deferred, non-blocking observations remain outside these repairs:

- SHA1/SHA256 `FULL_OBJECT` combinations are rejected by the existing parser as `InvalidArgument` before the new type-mismatch mapper; only CRC32/CRC32C reach both mismatch directions;
- CRC64NVME treats any type value as full-object state, so completion with an explicit `COMPOSITE` token is still accepted through canonicalization pending the #50 AWS probe;
- when initiation recorded no checksum algorithm but completion supplies an object checksum, SILO returns `BadDigest`; AWS documentation says such a value is accepted and ignored, so this should be triaged as a separate compatibility issue;
- composite part-count and value mismatches both become `BadDigest` with the same description;
- a full-object checksum carrying a `-N` suffix has that suffix ignored while its digest is still validated.

None is introduced by these patches, and none changes the #48 decision. They should be triaged separately if strict message or invalid-header parity becomes a maintenance priority.

## Why #50 is not included {#issue-50}

Issue #50 says `CRC64NVME + COMPOSITE` should be rejected at initiation. Three facts are confirmed:

1. AWS's algorithm matrix supports CRC64NVME only as a full-object checksum.
2. SILO and upstream MinIO canonicalize the request to full-object state.
3. The server returns `x-amz-checksum-type: FULL_OBJECT` from `CreateMultipartUpload`, so the substitution is externally visible rather than silent.

What is not confirmed is the decisive wire behavior: does AWS reject the explicit invalid combination, or accept it and return/carry full-object state? A capability matrix does not answer that question.

The upstream history also argues against guessing. PR #20855 added the canonicalization intentionally, and PR #20953 preserved it while tightening other invalid combinations. That may be based on an AWS observation, but the comment is not a reproducible transcript.

The same representation also affects completion: `FullObjectRequested` treats every CRC64NVME checksum as full-object state, so a stored `FULL_OBJECT` upload completed with the raw header value `COMPOSITE` is accepted as full-object rather than rejected as a type mismatch. This completion-side residue falls under the same raw-token-versus-canonical-state evidence question. It is explicitly not claimed fixed by #48.

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

- **Successful requests:** checksum semantics are unchanged, except that omitting the optional `x-amz-checksum-type` header is no longer misclassified as an explicit `COMPOSITE` assertion. That intentional interoperability relaxation changes the old erroneous 400 into success.
- **Rejected requests:** apart from that omitted-header case, HTTP status remains 400; the affected S3 error code and message become AWS-compatible. Explicit type-only mismatch is now enforced, and an unknown non-empty type is rejected as `InvalidArgument` before bitmask normalization.
- **Integrity:** unchanged or stronger. The reverse type-bypass is closed; no failed completion commits an object.
- **Stored data:** no format, checksum encoding, metadata, erasure layout, migration, or backfill change.
- **Performance:** constant-time comparisons and error construction only; no additional data reads or hashing passes.
- **Security/privacy:** digest values are not returned in the new messages. Bucket and object names are not added to them.
- **Rolling upgrade:** nodes may return different error codes until all serving nodes are upgraded, but successful objects remain compatible.
- **Rollback:** restores the old error codes and asymmetric check; it does not require data rollback.
- **Other repositories:** no Console, shared-package, MCLI, or SDK change is required. This public design record is the only cross-repository deliverable.

## Merge and release gates {#gates}

| Gate | Base #48 repair | 2026-08-28 follow-up |
| --- | --- | --- |
| Design and local verification | complete | complete |
| Independent adversarial review | complete, ACCEPT | complete, GO |
| Signed-off server commit | complete | `7e079ff05` on `main` |
| Push, remote CI, and merge | merged as `590aeaa7d` | not established |
| Public design record | merged as `9805dd7` | this documentation update is local |
| Tag and release artifacts | not established | not established |
| Container image and package | not established | not established |
| Deployment and production probe | not established | not established |

The follow-up must keep #50 out unless a raw AWS transcript changes the decision, run remote DCO/Go CI/vulnerability/release-pipeline checks on its final commit, and merge from the current SILO `main`. Repository integration, release artifact, image, deployment, and production probe remain independent gates; none can be inferred from a local test or documentation build.

## Conclusion {#conclusion}

#48 is a correct compatibility issue, and the evidence now covers all three rows. The safest repair does not relabel checksum failures globally. It teaches `CompleteMultipartUpload` to report its own protocol errors, compares checksum types symmetrically, and identifies a genuinely missing composite part checksum without confusing it with a missing part or a wrong value.

#50 is related by discovery history, not by proof. The server's current CRC64NVME canonicalization is deliberate and visible. Until AWS's exact response is captured, changing it would replace one unverified assumption with another.

That boundary is the central design decision: implement what the official contract and tests establish, test the hidden consequence found in the code, and leave the remaining policy question behind an explicit, reproducible evidence gate.
