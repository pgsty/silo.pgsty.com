---
title: "Per-Bucket CORS Wire Contract: Strict XML, Checksums, and Browser Responses"
linkTitle: "Bucket CORS Wire Contract"
date: 2026-08-29
lastmod: 2026-08-29
author: "Ruohang Feng"
summary: >
  SILO's first per-bucket CORS implementation accepted a second XML root, counted UTF-8 bytes instead of characters in rule IDs, and normalized lowercase methods outside the S3 enum. This B3 design record fixes the wire/parser/validation contract, documents the AWS and browser evidence, records the rejected alternatives, and keeps site-replication work explicitly out of scope.
tags: [Design, S3, CORS, XML, Compatibility]
weight: 33
draft: false
url: "/blog/design/bucket-cors-wire-contract/"
---

This document records the B3 protocol-hardening decision for per-bucket CORS after [SILO PR #71](https://github.com/pgsty/silo/pull/71) merged as [`e4e3007da`](https://github.com/pgsty/silo/commit/e4e3007da6d7d1198a6a050e34f84566d40a9654). It covers only the S3 request body, validation, checksum, matching, and browser-response contract. Site-replication ordering, tombstones, heal, status counters, and generic metadata refactoring remain separate work under [SILO #75](https://github.com/pgsty/silo/issues/75).

> **Status:** the standalone B3 implementation is local commit `ae879f6cc`; the final B2+B3 integration is signed commit `0eebc928f` on the issue-75 branch. The combined Opus 5 Max review preserved the strict parser, validation, checksum, MaxAge, wildcard, `Origin: null`, and fail-closed replication contracts, then identified and fixed a conflict-helper typo and a legacy-invalid metadata recovery risk. Focused combined tests pass; full combined verification is deliberately scheduled only after the code and documentation solution is frozen. The combined change remains unmerged, untagged, unpublished, undeployed, and not production-verified.<br>
> **Decision:** implement the strict B3 wire contract before the first SILO release containing per-bucket CORS. Do not normalize invalid input into validity, do not broaden the patch into site replication, and do not claim an overall release GO from local B3 evidence.

## Why this is a release blocker {#problem}

Bucket CORS is a standard S3 control plane. Its input is not merely configuration-shaped text: raw clients sign an exact XML request body, modern AWS SDKs attach a required payload checksum, SILO stores the accepted bytes verbatim, and `GetBucketCors` later returns those bytes to strict XML clients.

Three adversarial cases exposed holes in the merged implementation:

1. a valid `<CORSConfiguration>` followed by a second XML root was accepted and stored;
2. an ID containing exactly 255 Unicode characters was rejected because Go's `len(string)` counted UTF-8 bytes;
3. `<AllowedMethod>get</AllowedMethod>` was accepted because validation uppercased the value before checking the S3 enum.

These are server-side wire problems. The official AWS SDK models do not fully validate rule IDs or method strings on the client, and raw signed clients can always bypass typed SDK construction. The service must enforce the contract.

The second-root case is especially damaging. SILO stored the whole body, not just the first decoded element. A successful PUT could therefore make a later GET return a document with two roots, which standards-compliant XML clients reject.

## Authoritative contract {#contract}

The implementation uses current AWS documentation and generated SDK models as the protocol baseline:

- [PutBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketCors.html) defines the XML root, the 64 KB document limit, Content-MD5 and SDK checksum headers, up to 100 rules, and the rule-match conditions: origin, method, and every requested header must all match.
- [CORSRule](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CORSRule.html) defines the uppercase method values and the inclusive 255-character ID limit.
- [Elements of a CORS configuration](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html) permits at most one `*` in each allowed origin or allowed header.
- [Testing CORS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/testing-cors.html) shows a successful preflight returning the matched rule's full method list, requested allowed headers, exposed headers, credentials, and cache-variation headers.
- [S3 error responses](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/ErrorResponses.html) defines `MalformedXML` for XML that does not validate against the S3 schema and `BadDigest` for a mismatched Content-MD5 or checksum value.
- The generated [AWS SDK for Go v2 PutBucketCors operation](https://github.com/aws/aws-sdk-go-v2/blob/main/service/s3/api_op_PutBucketCors.go) marks the request checksum as required. Its [CORS types](https://github.com/aws/aws-sdk-go-v2/blob/main/service/s3/types/types.go) use an `int32` MaxAgeSeconds and leave most semantic validation to the server.
- The [WHATWG Fetch Standard](https://fetch.spec.whatwg.org/) forbids sharing a credentialed response when `Access-Control-Allow-Origin` is `*`.

A read-only OPTIONS request to the public AWS `landsat-pds` bucket independently confirmed the current response behavior: a wildcard rule returned `Access-Control-Allow-Origin: *`, the full `GET, HEAD` method list, and no `Access-Control-Allow-Credentials` header.

## Reproduction classification {#classification}

| Behavior | Result | Evidence and decision |
| --- | --- | --- |
| second XML root accepted | **REAL** | parser, signed in-process handler, and real TCP SigV4 all accepted it before the fix |
| 255 Unicode-character ID rejected | **REAL** | parser/Validate, signed handler, and real boto3 request reproduced SILO's rejection; accepting 255 code points is based on AWS's character wording and SDK model, not authenticated AWS PUT |
| lowercase method accepted | **REAL** | parser/Validate, signed handler, and real boto3 request all reproduced it |
| 64 KiB boundary | **NOT REAL** | 65,536 bytes already passed and 65,537 failed; keep regression coverage |
| 100-rule boundary | **NOT REAL** | exactly 100 already passed and 101 failed; keep regression coverage |
| first fully matching rule | **NOT REAL** | matching already fell through an earlier header-restrictive rule; preserve that behavior |
| checksum EOF bypass | **CONDITIONAL** | an in-memory reader could hide EOF from the checksum wrapper, while real TCP already rejected bad digests; remove the reader-dependent behavior anyway |
| empty and unknown XML members | **CONDITIONAL, resolved strictly** | AWS schema/error documentation supports rejection, but no authenticated AWS PUT black-box result was available |
| wildcard origin plus credentials | **REAL** | merged SILO echoed the origin and enabled credentials for `*`; live AWS and Fetch require `*` without credentials |
| `Origin: null` rewritten to wildcard | **REAL, found in final review** | inner forwarding middleware rewrote an explicitly matched `null` origin to `*` while retaining credentials; B3 now marks its response so the legacy rewrite skips it |
| negative MaxAge rejection | **CONDITIONAL, pre-existing** | retained because browser max-age is non-negative; no authenticated AWS PUT differential was available |

## Goals and non-goals {#scope}

### Goals {#goals}

- accept exactly one S3 CORS document element and only XML Misc after it;
- enforce the documented 64 KiB, 100-rule, ID, method, wildcard, and MaxAge contracts;
- verify Content-MD5 and modern SDK checksums independent of reader chunking behavior;
- retain the first fully matching rule semantics;
- return S3-compatible successful preflight and actual-request headers;
- make every changed behavior reviewable through parser, Validate, signed handler, and real-client tests;
- keep the exported compatibility manifest unchanged.

### Non-goals {#non-goals}

- change site-replication delivery, tombstones, heal, or status accounting;
- redesign global CORS fallback or metadata-error handling;
- add Console UI;
- introduce a general XML-schema framework;
- validate arbitrary XML attributes or require one namespace spelling;
- enforce cross-rule ID uniqueness without stronger current evidence;
- refactor unrelated lifecycle, tagging, policy, SSE, quota, or versioning parsers;
- commit, push, tag, publish an image, deploy, or claim production parity in this work item.

## Alternatives considered {#alternatives}

### A. Patch only the three reported lines {#alternative-three-lines}

This would add an EOF check, use a rune count, and remove method uppercasing. It is attractive but incomplete: it leaves unknown elements, duplicate singleton fields, empty numeric values, int32 overflow, the generic `?` wildcard, reader-dependent checksum verification, and incorrect wildcard/preflight responses.

**Rejected:** too narrow for the explicitly reviewed B3 contract.

### B. Normalize input into a canonical configuration {#alternative-normalize}

The server could uppercase methods, trim values, discard unknown elements, and keep only the first XML root. This is convenient for friendly clients but changes invalid signed wire input into a different valid configuration. It also preserves bytes that do not round-trip through `GetBucketCors` cleanly.

**Rejected:** S3 compatibility requires validation, not silent repair.

### C. Add a strict, B3-specific wire representation {#alternative-strict-wire}

Decode into private XML wire structs that capture direct text, unknown elements, repeated singleton fields, and MaxAge presence. Convert into the existing public `Config` and `Rule` types only after the XML shape is valid. Keep semantic checks in `Validate` and matching helpers.

**Selected:** it is strict where evidence exists, order-independent, namespace-tolerant, local to CORS, and adds no exported compatibility symbol.

### D. Validate every possible XML and header detail {#alternative-full-schema}

This would enforce namespace URIs, reject every unknown attribute, validate every response header as an RFC token, and add cross-rule ID uniqueness.

**Rejected for now:** these constraints lack sufficient differential evidence and risk unnecessary incompatibility.

## Final design {#design}

### 1. XML wire parser {#parser}

`ParseBucketCorsConfig` decodes into private wire-only types:

- `CORSConfiguration` is the only root;
- root and rule levels reject non-whitespace direct character data;
- unknown root, rule, and nested leaf elements are rejected;
- `ID` and `MaxAgeSeconds` may occur at most once per rule;
- list members remain repeatable and order-independent;
- MaxAge text must parse as a signed 32-bit integer;
- after the root closes, whitespace, comments, and processing instructions are allowed; another root, text, directive, or malformed token is rejected.

Namespace prefixes and the standard namespace declaration remain accepted because matching uses XML local names. Unknown attributes are not newly rejected. The existing `Config` and `Rule` XML tags remain for serialization compatibility, but production request and metadata parsing uses `ParseBucketCorsConfig`.

This parser also runs when stored bucket metadata is loaded. That is a deliberate pre-release choice: no SILO tag postdates PR #71, so there is no released per-bucket CORS population to migrate. A development build that previously stored malformed CORS XML makes the bucket's entire metadata record unloadable—not only its CORS view—until the stored CORS document is replaced or deleted.

### 2. Semantic validation {#validation}

`Validate` enforces:

- one through 100 rules;
- valid UTF-8 and no more than 255 Unicode code points in an ID;
- at least one non-empty allowed origin and one method per rule;
- methods exactly equal to `GET`, `PUT`, `HEAD`, `POST`, or `DELETE`;
- no `?` in an allowed origin or allowed header, because the inherited matcher treats it as a wildcard while S3 documents only `*`;
- at most one `*` in each allowed origin and allowed header;
- non-empty allowed and exposed header elements;
- MaxAgeSeconds from zero through `2^31-1`.

An empty ID remains allowed because ID itself is optional and current AWS documentation publishes no non-empty constraint. Cross-rule ID uniqueness remains outside this patch.

### 3. Matching {#matching}

The generic matcher is replaced on this path by a small single-`*` matcher:

```text
no *  -> exact match
one * -> prefix and suffix must both match; * may match zero bytes
```

Allowed-header matching remains case-insensitive, while the requested header spelling is preserved in the response. Method matching is case-sensitive after the S3 PUT path validates canonical stored values. Direct site-replication and heal writes in the merged base bypass that validation; they remain a separate integration requirement and can otherwise store a method that the B3 matcher will not execute.

`MatchPreflight` continues past a rule that matches origin and method but rejects one requested header. The selected rule is therefore the first rule that matches all three documented conditions. It also returns the exact origin element that matched and whether MaxAgeSeconds was present, preserving the difference between absent and explicit zero.

### 4. Request size and checksums {#checksums}

The handler keeps the existing positive Content-Length and 64 KiB guards. `validateLengthAndChecksum` still wraps the body with the shared checker, but the CORS handler now reads that wrapped body to EOF instead of placing another exact-length `LimitReader` outside it.

This makes checksum verification independent of whether the underlying reader returns the final bytes with or without `io.EOF` in the same call. A well-formed but mismatched Content-MD5 or full-header SDK checksum returns `BadDigest`; missing checksum material still returns the existing required-checksum error. The shared helper can classify malformed checksum syntax as missing, and this small-body path does not implement aws-chunked trailing-checksum decoding; those fidelity gaps remain outside B3. No second checksum implementation is added.

Modern boto3 traffic is a material compatibility gate because current botocore sends `x-amz-sdk-checksum-algorithm: CRC32` plus `x-amz-checksum-crc32`, not Content-MD5, for this required-checksum operation.

### 5. Browser responses {#responses}

The matched origin element controls the response:

| Matched element | `Access-Control-Allow-Origin` | `Access-Control-Allow-Credentials` |
| --- | --- | --- |
| `*` | `*` | omitted |
| `null` | `null` | `true` |
| exact origin | request origin | `true` |
| pattern such as `https://*` | request origin | `true` |

A successful preflight returns:

- the matched rule's complete `AllowedMethods` list;
- only the requested headers that the rule permits;
- configured `ExposeHeaders`;
- MaxAgeSeconds, including explicit zero;
- the existing three successful-preflight `Vary` dimensions.

Actual requests keep their existing continue-through behavior and receive origin, credentials, expose, and `Vary: Origin` headers when a rule matches. A request-context marker prevents the inner legacy forwarding middleware from rewriting an explicitly allowed `null` origin to `*`; unmarked global responses retain their historical workaround. Because `null` is shared by sandboxed documents and `file://` origins, operators should configure it only when credentialed access from all such contexts is intentional.

Allowed-origin elements are evaluated in document order. If a rule contains both a specific origin and `*`, place the specific origin first when that origin must retain reflected-origin credentials semantics.

The rejected-preflight body remains the existing bare 403 in this B3 patch. Producing the full AWS `AccessForbidden` XML shape and changing rejected-response cache/audit behavior require a separate wire decision rather than being smuggled into parser hardening.

## Implementation map {#implementation}

| Area | Files | Responsibility |
| --- | --- | --- |
| parser and validation | `internal/bucket/cors/cors.go` | private wire structs, strict trailing-token check, rune/enum/wildcard/MaxAge validation, matching |
| parser tests | `internal/bucket/cors/cors_test.go`, `cors_adversarial_test.go` | roots, XML Misc, unknown/nested/duplicate members, boundaries, matching |
| PUT handler | `cmd/bucket-cors-handlers.go` | size/checksum gates, EOF consumption, S3 error mapping |
| signed handler tests | `cmd/bucket-cors-adversarial_test.go` | three reported cases, 64 KiB, 100 rules, MD5 and CRC32 positive/negative cases |
| browser responses | `cmd/api-router.go`, `cmd/generic-handlers.go` | matched origin semantics, `null` marker, full methods, expose, explicit zero max age |
| response tests | `cmd/bucket-cors-middleware_test.go` | exact/pattern/wildcard/`null` origins, first full rule, headers, methods, expose, max age, credentials |

No site-replication source file belongs to this implementation boundary.

## Test and evidence matrix {#tests}

| Layer | Required evidence |
| --- | --- |
| parser | second root/text/dangling close rejected; trailing whitespace/comment/PI accepted; unknown/nested/duplicate rejected |
| Validate | 255 Unicode characters accepted, 256 rejected; lowercase and unsupported methods rejected; wildcard and empty-value cases |
| boundary | exactly 64 KiB and 100 rules accepted; one byte/rule over rejected; MaxAge absent/zero/negative/int32 overflow |
| signed handler | raw SigV4 PUT for all three reported failures; missing/bad MD5; valid/bad SDK CRC32 |
| middleware | first fully matching rule; wildcard, pattern, and `null` credentials; legacy unmarked `null` rewrite; full methods; requested headers; expose; explicit max age zero |
| focused race | CORS package and CORS handler/middleware tests under the race detector |
| full local | untagged and `kqueue,dev` full `cmd`; build; vet; pinned lint; generated/rebrand; diff check |
| real clients | `minio-go` v7.3.1 PUT/GET/preflight/DELETE and boto3/botocore CRC32 PUT/GET/preflight/DELETE plus adversarial rejects |
| external behavior | read-only OPTIONS against a public AWS bucket for wildcard, methods, credentials, and Vary |

## Adversarial review resolution {#review}

Claude Code Opus 5 ran at max effort against the evidence, implementation, and then this bilingual design plus the final code. The earlier implementation review returned **GO**. The publication review returned **GO WITH FIXES**, with no P0 or P1 and five P2 findings. After the accepted code and documentation changes, the same session returned **GO** with no P0–P2 finding.

Its non-blocking findings were independently adjudicated:

- the one behavioral P2 was accepted: an explicitly allowed actual `Origin: null` now survives the inner legacy forwarding middleware;
- the metadata-load blast radius and replication-validation exception are now stated precisely;
- returning an interior MaxAge pointer is read-only and the selected rule was already an interior pointer; no new mutation occurs;
- `BadDigest` is retained because the current AWS S3 error reference explicitly applies it to Content-MD5 or checksum mismatch;
- malformed checksum syntax, trailing-checksum decoding, no-match `Vary`, full `AccessForbidden` XML, and outer-middleware audit behavior are recorded but remain outside B3;
- non-UTF-8 XML declarations are not enabled because the S3 request syntax is UTF-8 and current SDKs emit UTF-8;
- method whitespace remains invalid while integer whitespace is accepted according to their different XML lexical domains;
- validating every exposed header as an RFC token is deferred without AWS differential evidence.

## Compatibility and rollout {#compatibility}

| Existing use | Effect |
| --- | --- |
| typed `minio-go` or boto3 CORS | valid configurations continue to round-trip; modern CRC32 requests are verified |
| raw valid XML | accepted up to the same size and rule limits |
| lowercase method | now rejected instead of normalized |
| 255 non-ASCII ID characters | now accepted; more than 255 rejected |
| second root, unknown element, duplicate singleton, empty/overflow MaxAge | now rejected as malformed XML |
| literal wildcard origin | now returns `*` without credentials |
| patterned origin | concrete request origin remains reflected with credentials |
| old development metadata containing malformed CORS XML | the entire bucket metadata record may be unloadable until the CORS XML is replaced or deleted |
| site replication | no B3 code change; its own convergence repair and tests remain separate |

The strictness change lands before any tagged SILO version contains per-bucket CORS. That timing is the compatibility window. Once released, this wire contract becomes stable and future relaxations or tightenings require their own differential evidence.

## Verification result and remaining gates {#gates}

The final local implementation passed:

- focused parser, Validate, signed handler, and middleware tests;
- focused race tests for `internal/bucket/cors` and CORS `cmd` paths;
- `go test ./cmd -count=1` and the full `kqueue,dev` `cmd` lane;
- `go build ./...` and `go vet ./...`;
- golangci-lint 2.13.1 with zero issues;
- generated-file, compatibility/rebrand, entrypoint, and diff checks;
- real boto3/botocore 1.43.58 and `minio-go` v7.3.1 regressions against a freshly built local server;
- final Claude Code Opus 5 max-effort review.

These results establish **B3 IMPLEMENTATION GO** only. Overall release remains blocked until the separate replication work is integrated, the server and documentation changes are committed and pushed, PR and merged-main CI pass, a release artifact is built, and deployment/production checks complete independently.

## Conclusion {#conclusion}

The final B3 design treats Bucket CORS as a signed S3 wire contract rather than a forgiving configuration file. It rejects malformed or noncanonical input before persistence, counts IDs as characters, validates modern SDK checksums, preserves documented first-full-rule selection, and emits browser-safe S3 responses.

The patch stays local to the CORS parser, validator, handler, matcher, response code, and tests. It adds no new service, schema, dependency, exported compatibility symbol, or site-replication refactor. That is the smallest complete solution supported by the protocol and live evidence.
