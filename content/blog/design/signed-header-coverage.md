---
title: "An Unsigned Header Is Not Part of the Request"
linkTitle: "Signed-Header Coverage"
date: 2026-09-09
lastmod: 2026-09-11
author: "Ruohang Feng"
summary: >
  A presigned or signed PUT authorized for one object could be turned into a server-side copy of any object the signing key can read, because SigV4 verification only walked the list of signed header names and never the x-amz-* headers that actually arrived, while the router selects CopyObject from an unsigned x-amz-copy-source header. This record defines SILO's unsigned-header rejection boundary, the payload-hash exception and trusted signature-age derivation, the PutObjectTagging injection reorder, the scope across signature modes, and the release evidence.
tags: [Design, Security, SigV4, CopyObject, Presigned, Compatibility]
weight: 6
draft: false
url: "/blog/design/signed-header-coverage/"
---

This record describes the unsigned-header coverage repair committed to SILO as [`123325430`](https://github.com/pgsty/silo/commit/123325430) and merged through [PR #173](https://github.com/pgsty/silo/pull/173), tracked as `SN-2026-011`. It was reported by Oren Yomtov against a released build and reproduced locally on both signature paths.

> **Status on 2026-09-11:** the original repair is pushed and merged through [PR #173](https://github.com/pgsty/silo/pull/173). The follow-up signing and payload-verification fixes described below are also merged through [PR #177](https://github.com/pgsty/silo/pull/177), with all eight PR checks passing. Source validation and published releases are separate: the currently published September 3 Server release does not contain these fixes.<br>
> **Scope:** SigV4 header coverage, consistent policy inputs and body-checksum verification. S3 field names, object and bucket metadata formats, replication protocols, encryption formats and client commands are unchanged.<br>
> **Security property:** unsigned client-supplied `x-amz-*` operation headers cannot change an authorized request; policy evaluation and body verification use the effective signed inputs.

## Too Long; Didn't Read (TL;DR) {#tldr}

A presigned `PUT` URL signs exactly one header, `host`. SILO confirmed that each header named in the signed-headers list had arrived, but it never walked the headers that *actually* arrived, so an `x-amz-*` header outside that list was accepted and used. `cmd/api-router.go` routes any `PUT` carrying `x-amz-copy-source` to `CopyObjectHandler` on that header alone. Together these turned a write grant for one object into a **server-side copy that reads any object the signing key can reach, executed as the signer** — a confused deputy. The Authorization-header path behaved the same way when the header was left out of `SignedHeaders`.

The repair states one invariant:

```text
As far as x-amz-* semantics go, the signed-headers list IS the request.
Any x-amz-* header not covered by it is refused before the handler runs.
```

This matches AWS S3, which refuses the same request with `AccessDenied` ("There were headers present in the request which were not signed"). The signing code was inherited byte-for-byte from upstream `minio/minio`, so every earlier SILO release, and upstream itself, carry the gap.

## Failure: the coverage gap {#failure}

`extractSignedHeaders` in `cmd/signature-v4-utils.go` iterates the *signed-headers list* and, for each name, pulls the value from the request (or the query string). It proves that every promised header is present. It never asks the opposite question — *is every `x-amz-*` header that arrived actually in the list?*

The one place that walked the arriving headers, `checkMetaHeaders`, matched only the `X-Amz-Meta-` prefix and was called only from the presigned path (`doesPresignedSignatureMatch`). The Authorization-header verifier (`doesSignatureMatch`) called nothing equivalent. So an unsigned `x-amz-copy-source` — or any other operation-shaping `x-amz-*` header — sailed through on both paths:

```text
presigned PUT (SignedHeaders=host)  ->  add unsigned  x-amz-copy-source: /src/secret
  -> router sees x-amz-copy-source  -> CopyObjectHandler
  -> copy runs as the signer, reading a bucket the URL never named
```

Reproduced locally on `RELEASE`-style builds: the control `PUT` returns `200` with an empty body; the same URL plus the one unsigned header returns `200` with a `CopyObjectResult` whose ETag is the md5 of the victim object, and the destination reads back the victim's bytes. Where the destination bucket already allows anonymous `GetObject`, the copied private bytes are then readable with no credentials at all.

## Provenance {#provenance}

The gap is inherited from upstream MinIO; SILO did not introduce it. The SigV4 verifier in `cmd/signature-v4-utils.go` and the Authorization-header path `doesSignatureMatch` in `cmd/signature-v4.go` are original MinIO code dating to 2016, and the header-driven CopyObject dispatch in `cmd/api-router.go` traces to 2019. The only routine that ever walked the arriving headers, `checkMetaHeaders`, was added upstream on 2023-07-27 in [minio/minio#17737](https://github.com/minio/minio/pull/17737) (`535f97ba6`). Upstream therefore recognized the class — an unsigned header must match the signed set — but scoped the check to the `X-Amz-Meta-` prefix and to the presigned path, leaving `x-amz-copy-source` and the whole Authorization-header path uncovered. The window has been open for the life of MinIO's S3 layer.

Before the unsigned-header repair, SILO's change to `cmd/signature-v4-utils.go` was the one-line dependency-path migration in `9b11dc946`, moving the `policy` import to `pgsty/silo-pkg/v3`. The vulnerable verification behavior came from upstream. The original repair (`123325430`) and the follow-ups in [PR #177](https://github.com/pgsty/silo/pull/177) change that boundary. The vulnerable code predates SILO's fork baseline, the upstream 2025-12-03 maintenance-mode commit from which the first SILO release was cut.

Upstream `minio/minio` is archived as of that handoff, so there is no upstream maintainer to take the patch. SILO inherited the code unchanged and is the only place it is fixed, as the security ledger already records for other inherited findings.

## The repair {#repair}

`checkMetaHeaders` becomes `checkUnsignedHeaders`, is broadened from the `X-Amz-Meta-` prefix to all of `X-Amz-`, and is called on **both** the presigned and Authorization-header paths. A header that is not covered by the signed set is refused with `ErrUnsignedHeaders` before any handler logic runs.

Four decisions shaped the exact boundary. Each had a plausible alternative that was rejected for a concrete reason.

### Membership, not value equality {#membership}

The inherited check compared `signedHeadersMap.Get(k) == val[0]`. For a header absent from the signed map, `Get` returns the empty string, so a header whose *first* value is empty compared equal and passed. A multi-value header such as `X-Amz-Copy-Source: ["", "/src/secret"]` could therefore smuggle an unsigned copy-source past a value-equality check. The repair tests **membership** in the signed set instead. A signed header's value is already bound by the signature, so value equality was never the property that mattered; presence in the list is.

### Exempt `X-Amz-Content-Sha256` {#exempt-content-sha256}

`X-Amz-Content-Sha256` can be omitted from `SignedHeaders` because the effective payload hash is bound separately in the canonical request. For presigned requests, the query value takes precedence, with a header fallback when the query value is absent. An explicit `UNSIGNED-PAYLOAD` remains valid. [PR #177](https://github.com/pgsty/silo/pull/177) aligns the policy condition with this effective value while preserving header-presence semantics, and checks header-only presigned body hashes in the generic authentication path as well as upload paths. The exception does not permit policy evaluation or body verification to use a different value.

### Derive signature age from the signed date {#exempt-signature-age}

The original repair exempted an internal `x-amz-signature-age` scratch header written after verification. That was too late for PUT and UploadPart authorization, which runs before signature verification. [PR #177](https://github.com/pgsty/silo/pull/177) instead derives `s3:signatureAge` directly from the signed `X-Amz-Date`, and removes the scratch header, its constant and its exemption. A forged date fails signature verification; an unsigned client header under the old name is rejected. Verification remains idempotent without mutating request headers.

### Inject `X-Amz-Tagging` after authentication {#tagging-reorder}

`PutObjectTaggingHandler` derives an `X-Amz-Tagging` header from the request *body* so that policy conditions can read it, and it previously did so before `authenticateRequest`. With the broadened check, that server-synthesized header — which the client never signs — would be refused as unsigned. The injection now happens after signature verification and before authorization, which still has it for policy conditions. **Rejected alternative:** blanket-exempt `X-Amz-Tagging` the way content-sha256 is exempt. That would let a client set object tags through an unsigned header on any signed or presigned write, reopening a smaller version of the same class of bug.

## Scope across signature modes {#scope}

- **Authorization-header (signed) and presigned SigV4:** both now enforced. These are the reachable paths.
- **Streaming SigV4:** not reachable for a copy. `authenticateRequest` returns `ErrSignatureVersionNotSupported` for streaming auth types, so `CopyObjectHandler`'s `checkRequestAuthType` rejects a streaming-signed copy before any copy occurs. The check is not added to the streaming verifier because the dispatch cannot reach it; a regression test pins that rejection.
- **SigV2:** unaffected. V2 canonicalization folds the `x-amz-*` headers into the string-to-sign by construction, so an added `x-amz-*` header changes the computed signature and is rejected as a signature mismatch.

## Status code: 400 versus 403 {#status-code}

AWS returns `403 Forbidden` for an unsigned header; SILO returns `400 AccessDenied` (`ErrUnsignedHeaders`), inherited from upstream. The attack is refused either way, and the error `Code` string is identical; only the HTTP status differs. Raising it to `403` is a one-line change to `cmd/api-errors.go` that also shifts the pre-existing meta-header rejection. It is left as a deliberate, reversible election rather than folded silently into a security fix, because it is a behavior change for the existing unsigned-meta-header path and is not required to close the vulnerability.

## Tests {#tests}

Several existing tests built a signed request and then set `x-amz-copy-source`, `x-amz-copy-source-range`, or `x-amz-metadata-directive` *after* signing — that is, they depended on the very behavior this fix removes. They now re-sign with `signRequestV4` after setting those headers, which is what every real S3 client does. `signRequestV4` excludes the `Authorization` header from its own signed set, so re-signing is safe. Current coverage includes `checkUnsignedHeaders` unit cases for empty first values, the payload-hash exception and rejection of the obsolete unsigned signature-age header and `TestPresignedVerifyIdempotent`, which verifies the same presigned request twice.

## Evidence {#evidence}

- A built server reproduced the confused deputy on both the presigned and Authorization-header paths, then refused both after the fix while the control `PUT`, a real `minio-go` `CopyObject`, `PutObject` with user metadata and tags, and body-based `PutObjectTagging` all continued to work.
- `go test ./cmd/` passes on the fix tree; `gofmt`, `gofumpt`, and `vet` are clean.
- Adversarial review (round one) independently surfaced three defects in the first draft — non-idempotent verification via the scratch header, the empty-first-value bypass, and over-rejection of an unsigned `x-amz-content-sha256` — each of which is addressed above and confirmed by re-running the reviewer's own adversarial test suite against the final tree.
- Adversarial review (round two, against the committed fix) found no regression and confirmed the re-signed tests keep their original intent: an invalid access key still returns `InvalidAccessKeyId`, and a wrong SSE-C key still returns `403` after the signature validates. It surfaced three *adjacent, pre-existing* gaps that also fail on the parent commit and are out of this change's scope; they are recorded under follow-ups below.

## Compatibility and operations {#impact}

- **Ordinary clients:** no request change. Every AWS SDK, `minio-go`, and `mc` already signs the `x-amz-*` headers it sends.
- **Unsigned `x-amz-*` headers:** now refused with `AccessDenied`, as on AWS. A client that added such a header without signing it was already outside the SigV4 contract.
- **Rolling upgrade:** wire and storage formats are unchanged. Upgraded nodes enforce the boundary; nodes still running an older build remain exposed until upgraded, so behavior can differ by node during the rolling window.
- **Rollback:** data written by the fixed version stays readable by the previous version, but rollback reopens the confused deputy.

## Residual risks and follow-ups {#residual-risks}

- **Release delivery:** a source fix and a public engineering record do not establish that a published binary or image contains the fix. Verify the selected release and artifact separately.
- **CVE:** the reporter requested one; the finding carries the stable fork-local `SN-2026-011` identifier until a CVE is assigned.
- **Status code election:** the `400`-versus-`403` choice above is open.
- **Adjacent signing fixes:** [PR #177](https://github.com/pgsty/silo/pull/177) addresses repeated copy-source ambiguity, signature-age authorization ordering, and the effective payload-hash policy value. It also closes the separately reproduced header-only presigned body-checksum gap. The regression set covers signed and presigned requests, policy enforcement before upload verification, and real HTTP bucket-policy tampering. These follow-ups are distinct from the original `SN-2026-011` finding; their merge and release status is recorded above.
- **The general question:** this repair covers `x-amz-*` request headers. Any future control that lets request syntax select an operation must answer the same question this one did — *is this value covered by the signature before it is allowed to mean anything?* The repeated-header gap above is the same question in a different guise: the value the signature binds and the value the handler consumes must be the one and the same.

## Conclusion {#conclusion}

The signature is the request. Everything an `x-amz-*` header claims is a claim until the signature covers it:

> Confirming that the promised headers arrived is not the same as confirming that the arrived headers were promised. Refuse any unsigned `x-amz-*` header before the handler runs, on every signature path a handler can be reached through.
