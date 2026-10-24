---
title: "SigV4 Signed-Header Coverage: Rejecting Unsigned x-amz-* Headers"
linkTitle: "Signed-Header Coverage"
date: 2026-09-09
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  A presigned or signed PUT authorized for a single object could be turned into a server-side copy of any object the signing key can read, because SigV4 verification only walked the list of signed header names without checking the x-amz-* headers that actually arrived, while the router dispatches CopyObject from an unsigned x-amz-copy-source header. This record documents SILO's unsigned-header rejection boundary, the payload-hash exemption and signature-age derivation, the PutObjectTagging injection reorder, scope across signature modes, and verification evidence.
tags: [Design, Security, SigV4, CopyObject, Presigned, Compatibility]
weight: 6
draft: false
url: "/blog/design/signed-header-coverage/"
---

This article records the unsigned-header coverage repair committed to SILO as [`123325430`](https://github.com/pgsty/silo/commit/123325430) in [PR #173](https://github.com/pgsty/silo/pull/173) (tracked as `SN-2026-011`) and the follow-up signing and payload-verification fixes in [PR #177](https://github.com/pgsty/silo/pull/177) (tracked as `SN-2026-012`), which shipped in [Server 20260916](/blog/release/silo-20260916/). The vulnerability was reported by Oren Yomtov and reproduced locally on both presigned and `Authorization`-header SigV4 paths.

## Summary (TL;DR) {#tldr}

A presigned `PUT` URL can sign only the `host` header. SILO confirmed that each header listed in `SignedHeaders` had arrived, but never inspected the full set of headers present on the incoming request, allowing `x-amz-*` headers outside `SignedHeaders` to pass through untouched. Meanwhile, `cmd/api-router.go` routes any `PUT` carrying `x-amz-copy-source` to `CopyObjectHandler` based on that header alone. Combined, these two behaviors allowed a caller to turn a single-object write grant into a **server-side copy that reads any object reachable by the signing key, executed under the signer's authority** — a confused deputy. The `Authorization`-header path behaved the same way whenever `x-amz-copy-source` was omitted from `SignedHeaders`.

The repair enforces one invariant:

```text
On ordinary signed and presigned SigV4 paths, every received x-amz-* header
must be covered by the signature, except for the separately bound X-Amz-Content-Sha256.
```

This matches AWS S3, which rejects the same request with `AccessDenied` ("There were headers present in the request which were not signed").

## Failure: The One-Way Coverage Gap {#failure}

`extractSignedHeaders` in `cmd/signature-v4-utils.go` iterates over the *signed-headers list* and pulls each named header from the request (or query string). That verifies that every promised header is present, but omits the converse check: *whether every arriving `x-amz-*` header is included in `SignedHeaders`*.

The only routine that inspected arriving headers, `checkMetaHeaders`, matched only the `X-Amz-Meta-` prefix and ran only on the presigned path (`doesPresignedSignatureMatch`). The `Authorization`-header verifier (`doesSignatureMatch`) had no equivalent check. As a result, an unsigned `x-amz-copy-source` — or any other operation-shaping `x-amz-*` header — passed through on both paths:

```text
presigned PUT (SignedHeaders=host)  ->  append unsigned x-amz-copy-source: /src/secret
  -> router matches x-amz-copy-source  -> dispatches CopyObjectHandler
  -> copy executes as the signer, reading a source bucket the URL never authorized
```

In local reproduction, the control `PUT` returns `200` with an empty body; the same presigned URL with an appended unsigned `x-amz-copy-source` header also returns `200`, returning a `CopyObjectResult` whose ETag matches the victim object's MD5 and writing the victim's bytes into the destination object. If the destination bucket permits anonymous `GetObject`, the copied private object becomes readable without credentials.

## Provenance {#provenance}

This gap was inherited from upstream MinIO. The SigV4 verifier in `cmd/signature-v4-utils.go` and `doesSignatureMatch` in `cmd/signature-v4.go` date back to 2016, and the header-driven `CopyObject` router dispatch in `cmd/api-router.go` dates to 2019. Upstream added `checkMetaHeaders` on 2023-07-27 in [minio/minio#17737](https://github.com/minio/minio/pull/17737) (`535f97ba6`), recognizing that arriving headers must be checked against the signed set, but scoped that check to the `X-Amz-Meta-` prefix on the presigned path — leaving `x-amz-copy-source` and the entire `Authorization`-header path uncovered.

Prior to this fix, SILO's only modification to `cmd/signature-v4-utils.go` was a single-line import path update in `9b11dc946` (`policy` moved to `pgsty/silo-pkg/v3`). Commit `123325430` and the follow-ups in [PR #177](https://github.com/pgsty/silo/pull/177) close the boundary across both paths.

## The Repair {#repair}

`checkMetaHeaders` is renamed to `checkUnsignedHeaders`, widened from `X-Amz-Meta-` to the full `X-Amz-` prefix, and invoked on **both** the presigned and `Authorization`-header paths. Any arriving `x-amz-*` header missing from the signed set is rejected with `ErrUnsignedHeaders` before handler logic runs.

Four design decisions define the exact boundary:

### Set Membership Lookup {#membership}

The inherited `checkMetaHeaders` function evaluated `signedHeadersMap.Get(k) == val[0]`. For a header absent from `signedHeadersMap`, `Get` returns `""`, so an unsigned multi-value header whose first element is empty — such as `X-Amz-Copy-Source: ["", "/src/secret"]` — evaluated equal and bypassed the check. `checkUnsignedHeaders` checks key membership in `signedHeadersMap` directly; once a header name is in the signed set, its values are already bound by the signature digest.

### Exempt `X-Amz-Content-Sha256` {#exempt-content-sha256}

`X-Amz-Content-Sha256` may be omitted from `SignedHeaders` because the effective payload hash is bound separately in the SigV4 canonical request. On presigned requests, the query parameter takes precedence and falls back to the header only when the query parameter is absent; an explicit `UNSIGNED-PAYLOAD` remains valid. [PR #177](https://github.com/pgsty/silo/pull/177) aligns policy-condition evaluation with this effective payload hash while preserving header-presence semantics, and enforces body-hash verification for header-only presigned requests in the generic authentication path as well as upload paths. Signature verification, policy evaluation, and payload verification all consume the same bound value.

### Derive Signature Age from the Signed Date {#exempt-signature-age}

The initial fix exempted an internal `x-amz-signature-age` scratch header written after signature verification. However, `PUT` and `UploadPart` evaluate authorization before signature verification, before that scratch header existed. [PR #177](https://github.com/pgsty/silo/pull/177) computes `s3:signatureAge` directly from the signed `X-Amz-Date` value and removes the scratch header, its constant, and its exemption. A tampered date fails signature verification, an unsigned client-supplied `x-amz-signature-age` header is rejected, and verification remains idempotent without mutating request headers.

### Inject `X-Amz-Tagging` After Signature Verification {#tagging-reorder}

`PutObjectTaggingHandler` synthesizes an `X-Amz-Tagging` header from the XML request body so that IAM policy conditions can inspect object tags, and previously injected that header before `authenticateRequest`. Under the widened `X-Amz-` check, that server-synthesized header would be rejected as unsigned. Moving the injection to run after signature verification and before policy authorization preserves tag condition evaluation while keeping signature verification strict. We rejected the alternative of blanket-exempting `X-Amz-Tagging`, which would have allowed clients to attach unsigned `X-Amz-Tagging` headers to arbitrary signed or presigned write requests.

## Scope Across Signature Modes {#scope}

- **`Authorization`-header (signed) and presigned SigV4:** both enforce `checkUnsignedHeaders`.
- **Streaming SigV4:** the seed verifier does not call `checkUnsignedHeaders`. Copy handlers reject streaming authentication through their standard authentication dispatch, while streaming `PUT` and `UploadPart` header coverage remains a separate boundary.
- **SigV2:** unaffected. V2 canonicalization folds all `x-amz-*` headers into the string-to-sign by construction, so any added `x-amz-*` header alters the expected signature and fails verification.

## Status Code: 400 vs. 403 {#status-code}

AWS S3 returns `403 Forbidden` for an unsigned header, whereas SILO returns `400 AccessDenied` (`ErrUnsignedHeaders`), inherited from upstream. Both reject the request with the `AccessDenied` S3 error code; only the HTTP status code differs. Changing `ErrUnsignedHeaders` to `403` in `cmd/api-errors.go` is a one-line change, but it would also alter the HTTP status for the existing unsigned `x-amz-meta-*` rejection path, so `400 AccessDenied` is retained for compatibility.

## Tests {#tests}

Several existing unit tests constructed a signed request and then attached `x-amz-copy-source`, `x-amz-copy-source-range`, or `x-amz-metadata-directive` *after* signing. Those tests now re-sign with `signRequestV4` after setting operation-shaping headers (`signRequestV4` excludes `Authorization` from its own signed set, making re-signing safe). Unit tests cover `checkUnsignedHeaders` against empty first values, the `X-Amz-Content-Sha256` exemption, rejection of unsigned `x-amz-signature-age` headers, and `TestPresignedVerifyIdempotent`, which verifies the same presigned request twice.

## Evidence {#evidence}

- Against a built server instance, the reproduction harness confirmed the confused-deputy copy on both presigned and `Authorization`-header paths before the fix, and confirmed that both are rejected after the fix while control `PUT` requests, `minio-go` `CopyObject`, `PutObject` with user metadata and tags, and body-based `PutObjectTagging` continue to succeed.
- `go test ./cmd/` passes cleanly, along with `gofmt`, `gofumpt`, and `go vet`.
- First-round code review identified three issues in the initial draft — non-idempotent verification via the scratch header, the empty-first-value bypass, and over-rejection of unsigned `x-amz-content-sha256` — all of which are resolved and covered by regression tests.
- Second-round review confirmed that the re-signed tests preserve their original assertions: an invalid access key still returns `InvalidAccessKeyId`, and a mismatched SSE-C key still returns `403` after signature verification.

## Compatibility and Operations {#impact}

- **Standard clients:** unaffected. Conforming SigV4 signers include all non-exempt `x-amz-*` headers they send in `SignedHeaders`.
- **Unsigned `x-amz-*` headers:** rejected with `AccessDenied`, matching AWS S3.
- **Rolling upgrade:** wire and on-disk storage formats are unchanged. Upgraded nodes enforce the check immediately, while unupgraded nodes remain exposed until replaced during a rolling upgrade.
- **Rollback:** data written under the patched version remains readable by older binaries, though rolling back reopens the confused-deputy vulnerability.

## Related Fixes and General Principle {#residual-risks}

- **Advisory identifiers:** the unsigned-header repair is tracked as `SN-2026-011`, and the companion payload-verification and signing fixes in [PR #177](https://github.com/pgsty/silo/pull/177) are tracked as [`SN-2026-012`](/about/security-advisories/#sn-2026-012).
- **Status code alignment:** the `400`-versus-`403` HTTP status question remains open for a future major release.
- **Adjacent signing fixes:** [PR #177](https://github.com/pgsty/silo/pull/177) resolves duplicate `x-amz-copy-source` header ambiguity, fixes signature-age authorization ordering and effective payload-hash policy evaluation, and closes the header-only presigned body-checksum gap. Regression tests cover signed and presigned requests, policy evaluation before upload verification, and live HTTP bucket-policy tampering.
- **General principle:** any request element that selects or shapes an operation must be covered by the signature before routing or handler logic acts on it, and the value bound by the signature must be identical to the value consumed by the handler.

## Conclusion {#conclusion}

SigV4 verification must verify both that every header listed in `SignedHeaders` is present and that every arriving `x-amz-*` header is listed in `SignedHeaders`. Rejecting unsigned `x-amz-*` headers before handler dispatch closes the confused-deputy boundary on both signed and presigned SigV4 paths. While this signing fix does not alter storage formats, upgrading to [Server 20260916](/blog/release/silo-20260916/) also includes [IAM changes requiring a coordinated upgrade](/operations/replication/iam-upgrade/).
