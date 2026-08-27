---
title: "Why CompleteMultipartUpload Must Return ChecksumType: Review of PR #57"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-08-26
author: "Ruohang Feng"
summary: >
  SILO persisted the right multipart checksum and could report its type through HEAD and other APIs, but CompleteMultipartUpload dropped ChecksumType from its XML result. This record explains the defect, why PR #57 fixes it with two production lines, the review findings, the CI and merge decision, compatibility impact, and the remaining release boundary.
tags: [Design, S3, Compatibility, Checksum]
weight: 20
draft: false
url: "/blog/design/complete-multipart-checksum-type/"
---

This is the design, review, and decision record for [SILO #47](https://github.com/pgsty/silo/issues/47) and [PR #57](https://github.com/pgsty/silo/pull/57).

> **Status on 2026-08-26:** [PR #57](https://github.com/pgsty/silo/pull/57) was approved and merged as [`a96116b1`](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee); [#47](https://github.com/pgsty/silo/issues/47) closed automatically. All nine checks on the tested PR head passed, followed by green Go CI and VulnCheck runs on `main`. No tagged release, package, container image, deployment, or production endpoint has yet been verified to contain the fix.<br>
> **Scope:** return the already-known checksum type from `CompleteMultipartUploadResult`; do not add new checksum algorithms.<br>
> **Owner:** [`pgsty/silo`](https://github.com/pgsty/silo), the SILO server repository.<br>
> **Release boundary:** code review, merge, a green `main`, a tagged release, packages, container images, deployment, and production verification are separate gates.

## Too Long; Didn't Read (TL;DR) {#tldr}

SILO already computed and persisted the correct checksum type for a completed multipart object. `HEAD`, `ListParts`, and `GetObjectAttributes` could expose it. The completion response could not, because its Go response struct had checksum value fields but no `ChecksumType` field.

PR #57 adds that field, copies the existing value from the checksum map, registers the new exported symbol in the compatibility baseline, and tests `FULL_OBJECT`, `COMPOSITE`, and the no-checksum case. It does not recalculate data, change metadata, migrate objects, or weaken integrity checks.

The repair is correct and intentionally narrow. Maintainers approved the fork workflows, refreshed the stale PR branch onto current `main`, required every new check to pass, submitted an approving review, and merged while preserving the contributor's signed-off commit. Repository integration is complete; release delivery remains a separate gate.

## Where the defect came from {#origin}

The defect was found while investigating [#31](https://github.com/pgsty/silo/issues/31), where a real boto3 client exposed several adjacent multipart-checksum incompatibilities. #31 was the data-path failure: a `FULL_OBJECT` CRC32 multipart upload could fail at completion. It was fixed independently by `0cff48f6c` and `75859690b`, then closed on 2026-08-04. That review deliberately split four adjacent findings into [#46](https://github.com/pgsty/silo/issues/46), #47, #48, and #50 instead of treating them as one checksum bug.

After the object completed successfully, another inconsistency remained:

```text
complete_multipart_upload() -> ChecksumType: None
head_object()               -> ChecksumType: FULL_OBJECT
```

AWS S3 returned `FULL_OBJECT` in both places. SILO returned the checksum value in the completion XML, and the committed object retained the correct type, but the completion SDK result exposed a null type.

That observation became #47. It is a presentation defect, not a checksum-calculation or storage defect. It does not explain the earlier `InvalidPart` failure from #31, and repairing it does not replace the [server-side part-checksum work tracked in #46](/blog/design/uploadpart-checksum/), which later landed independently as `7fea6d5a5`.

## The S3 response contract {#contract}

The [AWS CompleteMultipartUpload API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) defines `ChecksumType` as an element of `CompleteMultipartUploadResult`. Its valid values are:

| Value | Meaning |
| --- | --- |
| `FULL_OBJECT` | The reported checksum covers the logical bytes of the completed object. |
| `COMPOSITE` | The object checksum is derived from the checksums of its multipart parts. |

When an object has no additional S3 checksum, the element should be absent. A server must not invent a type with no checksum value.

This distinction matters to clients. The same Base64 field name can describe either a direct full-object checksum or a multipart composition. A client that validates the completion result needs the type to interpret the checksum correctly and to compare the response with the mode selected at `CreateMultipartUpload`.

## What SILO did before the PR {#before}

The completion handler already passed the committed `ObjectInfo` to `generateCompleteMultipartUploadResponse`. That generator already called:

```go
cs, _ := oi.decryptChecksums(0, h)
```

The checksum decoder returned a map containing both the algorithm value and the normalized object type:

```text
CRC32                 -> "...Base64..."
x-amz-checksum-type    -> "FULL_OBJECT" or "COMPOSITE"
```

The response struct copied the values for CRC32, CRC32C, CRC64NVME, SHA1, and SHA256. It simply had nowhere to put the type:

```text
committed ObjectInfo.Checksum
        -> decryptChecksums
        -> checksum values + x-amz-checksum-type
        -> CompleteMultipartUploadResponse
        -> checksum values copied, type discarded
        -> XML without <ChecksumType>
        -> SDK returns None / null
```

Other surfaces used the same state correctly. `ListParts` and `GetObjectAttributes` already returned `ChecksumType`; `HEAD` also reported the stored type. The loss was isolated to the success XML for `CompleteMultipartUpload`.

## What PR #57 changes {#implementation}

The contributed diff contains one signed-off commit, three files, 60 added lines, and no deletions. Only two production lines change. A maintainer later merged current `main` into the contributor branch to refresh its CI context; that merge changed history, not the three-file product diff.

### Add the response field {#field}

```go
ChecksumType string `xml:"ChecksumType,omitempty"`
```

`omitempty` is part of the compatibility contract: checksum-free uploads retain the old XML shape.

### Copy the existing normalized value {#mapping}

```go
ChecksumType: cs[xhttp.AmzChecksumType],
```

The generator does not infer the type from an ETag, algorithm name, or part count. It uses the same decoded metadata that already supplies the checksum values.

### Test the response surface {#tests}

The added test covers:

- no checksum: the Go field is empty and `<ChecksumType>` is absent;
- a full-object checksum: the field is `FULL_OBJECT` and the tag is present;
- a multipart composite checksum: the field is `COMPOSITE` and the tag is present.

It checks the response value before XML encoding and separately checks omission/presence after encoding.

### Record the exported compatibility symbol {#baseline}

`CompleteMultipartUploadResponse.ChecksumType` is an exported Go field. SILO's rebrand guard performs an exact comparison of the exported compatibility surface, so the PR correctly adds the field to `buildscripts/rebrand-guard/compat-baseline.json`. This is an acknowledgement of an intentional public surface change, not a bypass of the guard.

## Why the repair works {#why-it-works}

The correctness argument is a short chain of existing invariants.

1. `ObjectInfo.Checksum` is the committed checksum metadata. The completion response is generated only after the object layer returns the committed `ObjectInfo`.
2. `decryptChecksums(0, h)` uses the existing metadata-decryption path, including the request headers needed for SSE-C. No second decryption mechanism is added.
3. The checksum decoder writes `x-amz-checksum-type` only when it has decoded a non-empty checksum value.
4. Existing `ChecksumType.ObjType()` logic normalizes reachable states to `FULL_OBJECT` or `COMPOSITE`.
5. Indexing a nil or missing map entry returns the empty string.
6. XML `omitempty` removes the element for that empty string.

The resulting behavior is deterministic:

| Committed checksum state | Map value | Completion XML |
| --- | --- | --- |
| No additional checksum | empty | no `<ChecksumType>` |
| Full-object checksum | `FULL_OBJECT` | `<ChecksumType>FULL_OBJECT</ChecksumType>` |
| Multipart composite checksum | `COMPOSITE` | `<ChecksumType>COMPOSITE</ChecksumType>` |

The change is therefore a missing projection from established state to the wire response. It does not create new checksum state and cannot make an incorrect checksum correct. It makes the response describe the state the server has already validated and committed.

## Review and verification {#review}

The PR was reviewed after the contributor branch was refreshed onto current `main`. The update produced head `c4b9d38d`; the resulting tree hash, `39ec44c6b390c441413e490370f70fbacc4e6a91`, exactly matched the isolated local no-commit merge. The result was clean and included the intervening checksum work on `main`.

Local verification on that exact merge result included:

```text
targeted ChecksumType regression test
CGO_ENABLED=0 go test ./cmd/ -count=1 -timeout 30m
go vet ./cmd/
gofmt and git diff --check
rebrand compatibility guard
local DCO rule
```

The targeted regression completed in 2.174 seconds and the full `cmd` package test completed in 168.956 seconds. The commit author email matches its `Signed-off-by` trailer. Cryptographic Git commit signing is independent of DCO and is not required by this repository.

A separate read-only local Claude Code adversarial review inspected the merged diff, checksum serialization, XML path, current `main`, tests, DCO, and compatibility guard. Its verdict was **COMMENT**: the production change was correct and safe, but it preferred an additional HTTP-level completion test before merge. The maintainer agreed that such a test would improve fidelity, but disagreed that it was blocking: the handler delegates directly to the tested generator, while existing real MPU tests already cover persisted `FULL_OBJECT` and `COMPOSITE` states. The formal GitHub review therefore recorded **APPROVED** with the HTTP-level test as a follow-up.

### Actions, branch refresh, and merge {#merge-sequence}

The first four `action_required` runs had been created on 2026-08-09 against the PR's old base. After approval, DCO passed but the old [VulnCheck run](https://github.com/pgsty/silo/actions/runs/31306998949) used Go 1.26.5 and failed on newly published standard-library vulnerabilities fixed in Go 1.26.6. Current `main` had already moved to Go 1.27.0, and its latest VulnCheck was green. Treating the stale failure as either a product regression or an ignorable red check would both have been wrong.

The decision was to refresh the test context, not rerun or waive the stale result:

1. GitHub's update-branch API merged current `main` (`8d76a255c`) into contributor head `d014a12cf`, producing `c4b9d38d` without conflicts.
2. GitHub created four new fork workflow runs for the refreshed head; all four were explicitly approved again.
3. All nine reported checks passed: [DCO](https://github.com/pgsty/silo/actions/runs/32922040560), [VulnCheck](https://github.com/pgsty/silo/actions/runs/32922040457), six jobs in [Go CI](https://github.com/pgsty/silo/actions/runs/32922040467), and the [Test Release Pipeline](https://github.com/pgsty/silo/actions/runs/32922040567). The release validation job completed in 11 minutes 26 seconds.
4. A formal approving review was submitted against `c4b9d38d`.
5. Merge used an expected-head guard and the repository's normal merge strategy, producing `a96116b1`. This preserved the contributor's signed-off commit rather than rewriting it through a squash. The PR's `Resolves #47` relationship closed the issue one second later.
6. The post-merge `main` [VulnCheck](https://github.com/pgsty/silo/actions/runs/32922815310) and all six [Go CI](https://github.com/pgsty/silo/actions/runs/32922815278) jobs also passed; cross-compilation, the slowest job, completed in 9 minutes 54 seconds.

This sequence matters because “the patch passed once” was not the acceptance criterion. The exact tree merged into current `main` had to be the tree reviewed and tested, and a stale CI environment could not substitute for that proof.

## Evaluation of the PR {#evaluation}

### What is strong {#strengths}

- **The scope matches the defect.** Two production lines restore one missing response element.
- **It reuses authoritative state.** There is no duplicate type derivation and no new checksum algorithm branch.
- **Backward compatibility is explicit.** `omitempty` preserves checksum-free responses.
- **The test covers both valid values and absence.** A regression cannot silently restore the null result.
- **The compatibility baseline is updated deliberately.** CI is not weakened.
- **DCO provenance is complete.** The sole commit has a matching sign-off.

### Non-blocking review notes {#notes}

The test is correct for the changed generator but its fixtures are not byte-for-byte models of every production multipart metadata flag:

- the `FULL_OBJECT` fixture reaches the right value through a non-multipart checksum state rather than a completed multipart state carrying `ChecksumMultipart`, `ChecksumIncludesMultipart`, and `ChecksumFullObject`;
- the `COMPOSITE` fixture carries the multipart flag but omits the persisted per-part checksum block.

Existing API-level tests already exercise genuine `FULL_OBJECT` and `COMPOSITE` completion and verify their committed types. PR #57 tests the remaining projection from decoded state to the response field and XML. Adding an assertion to those full API tests would improve test fidelity, but it is not required for this two-line repair.

The PR places `ChecksumType` before the algorithm-specific fields, while AWS's example response and SILO's newer `CopyObjectResponse` place it after them. Mainstream S3 SDKs parse XML by element name, so this is a parity and style detail rather than a compatibility blocker. Moving the field is optional.

Finally, the contributor commit title says `feat:` even though the PR correctly marks itself as a bug fix. The final merge preserved that signed-off commit instead of rewriting it. This is a history/style imperfection, not a protocol or release blocker.

## Why new algorithms do not belong in this PR {#algorithm-scope}

AWS now documents additional fields such as SHA512, MD5, and XXHASH variants. Adding those XML fields alone would create false compatibility.

SILO's current checksum implementation supports CRC32, CRC32C, CRC64NVME, SHA1, and SHA256. A real new algorithm requires coordinated support across:

- request header parsing and validation;
- streaming checksum calculation;
- multipart `FULL_OBJECT` or `COMPOSITE` semantics;
- on-disk checksum encoding and decoding;
- UploadPart, UploadPartCopy, completion, copy, replication, HEAD, GET, ListParts, and GetObjectAttributes;
- SDK/client interoperability and a full encrypted/compressed/versioned test matrix.

PR #57 should not grow response-only placeholders for algorithms the server cannot calculate or persist. Each new algorithm family needs a separate compatibility decision, implementation, and review.

## Compatibility and operational impact {#impact}

- **S3 clients:** checksum-aware clients receive `ChecksumType` from future successful multipart completions instead of null.
- **Wire format:** one additive XML element appears only when an additional checksum exists. Clients that ignore unknown elements remain unaffected.
- **Integrity:** no checksum is recalculated or accepted differently. Existing validation semantics are unchanged.
- **Stored data:** no object, part, metadata, or erasure format changes. No migration or backfill.
- **Existing objects:** object state remains correct. A past completion response cannot be replayed; use HEAD or GetObjectAttributes to inspect an existing object's type.
- **Encryption:** the response uses the established checksum metadata-decryption path. No key material or new secret is exposed.
- **Performance:** one map lookup and one optional XML element; no extra object read, hashing pass, or allocation proportional to object size.
- **Rolling upgrade:** old nodes omit the element and new nodes return it. Requests and stored objects remain compatible, but client-visible behavior stabilizes only after all serving nodes are upgraded.
- **Rollback:** rolling back removes the response element from future completions; it does not damage objects created while the fix was present.
- **Other repositories:** no server dependency, silo-pkg, MCLI, or Console change is required. Public documentation belongs in this site.

This is an additive compatibility repair, not a release feature that requires operators to rewrite data. Its only externally visible effect is a more complete success response.

## Merge and release decision {#decision}

The final decision had six parts:

1. accept the narrow projection fix without recalculating checksums or changing storage;
2. keep SHA512, MD5, and XXHASH families out of #57 until they have end-to-end server support;
3. record an HTTP-level completion test as useful follow-up work, not a blocker for the directly tested generator repair;
4. reject stale CI as merge evidence, update the branch to current `main`, and approve the newly created workflows;
5. merge only after the refreshed head was formally approved and every check was green, using an expected-head guard and a normal merge that preserved the DCO-signed contribution;
6. let `Resolves #47` close the issue, then verify the resulting `main` workflows independently.

No dependency update, storage migration, or cross-repository implementation was required. That decision is now complete at the repository-integration gate.

A green `main` still does not prove that a SILO tag, release package, container image, deployment, or production endpoint contains the repair. Those delivery gates remain unverified and must be recorded separately when the next release ships.

## Conclusion {#conclusion}

PR #57 is a good example of a small compatibility fix whose correctness comes from respecting an existing source of truth. The checksum type was already calculated, validated, persisted, decryptable, and visible through other APIs. The completion response simply failed to project it into XML.

The accepted repair does exactly that projection and nothing more. It makes the wire response honest without touching user data, checksum mathematics, storage layout, or algorithm scope. The fork workflows, refreshed-head review, merge, automatic issue closure, and post-merge `main` verification are complete. What remains is delivery discipline: distinguish this merged fix from a tagged, packaged, imaged, deployed, and production-verified release.
