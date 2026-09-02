---
title: "Two SSE-C Keys, One CopyObject Response"
linkTitle: "CopyObject SSE-C Checksums"
date: 2026-08-28
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  CopyObject can carry one SSE-C key for the source and another for the destination. SILO stored the destination checksum correctly but tried to decrypt it for the response with the source key, silently omitting checksum fields. This record explains the key-context boundary, response-only repair, single-decryption design, and regression matrix.
tags: [Design, S3, SSE-C, Checksum, Compatibility]
weight: 17
draft: false
url: "/blog/design/copyobject-ssec-checksum-response/"
---

This record explains the CopyObject SSE-C checksum response repair committed in SILO as `e73436c99`.

> **Status on 2026-08-28:** implementation, encryption and key-rotation tests, complete server suites, race tests, static checks, build, and independent Fable Max acceptance review are complete. The commit was merged into `main` on 2026-08-29 as `e73436c99`; tag, package, image, deployment, and production verification remain separate gates.<br>
> **Scope:** the successful CopyObject XML and HTTP response after the destination object has committed. Stored object bytes, checksum metadata, encryption format, source decryption, federation, replication, and historical objects are unchanged.<br>
> **Security property:** source SSE-C headers may decrypt only source state; destination SSE-C headers may decrypt only committed destination state.

## Too Long; Didn't Read (TL;DR) {#tldr}

An SSE-C copy can use two independent keys:

| Role | Request headers | Purpose |
| --- | --- | --- |
| source | `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` | decrypt the source object |
| destination | `X-Amz-Server-Side-Encryption-Customer-*` | encrypt and later interpret the committed destination object |

SILO correctly wrote the destination with its destination key. However, after commit, both the XML generator and the generic PUT-response header helper received the complete CopyObject request. The checksum metadata decrypter intentionally prefers copy-source SSE-C headers when they are present. That priority is correct while reading the source, but wrong when interpreting the committed destination.

With source key A and destination key B:

```text
source body       --decrypt A--> logical bytes
logical bytes     --encrypt B--> committed destination
destination csum  --seal B-----> stored checksum metadata
response decoder  --try A------> key mismatch, checksum omitted
```

The object and stored checksum were correct; only the successful response was incomplete. The repair constructs a destination response-header view by removing exactly the three copy-source SSE-C customer headers. It decrypts the destination checksum once, then reuses the resulting map for both XML and HTTP response headers.

## Observable failure {#failure}

The failure requires a checksum-bearing destination and distinct source/destination SSE-C contexts. A representative request supplies:

```text
x-amz-copy-source: /bucket/source
x-amz-copy-source-server-side-encryption-customer-algorithm: AES256
x-amz-copy-source-server-side-encryption-customer-key: <key A>
x-amz-copy-source-server-side-encryption-customer-key-md5: <md5 A>
x-amz-server-side-encryption-customer-algorithm: AES256
x-amz-server-side-encryption-customer-key: <key B>
x-amz-server-side-encryption-customer-key-md5: <md5 B>
x-amz-checksum-algorithm: CRC32
```

Before the repair:

- CopyObject returned HTTP 200;
- reading the destination with key B returned the correct body;
- stored destination checksum metadata decrypted with key B and matched the logical bytes;
- the CopyObject XML and HTTP response omitted CRC32 and `ChecksumType`.

This is a response-contract defect, not evidence of corrupted object data.

The same ambiguity affects same-object SSE-C key rotation. After metadata has been resealed under key B, the request still carries source key A in the copy-source headers. Response generation must describe the post-rotation object, so it must use B.

## Why the global decrypter must not change {#source-boundary}

The metadata decrypter's copy-source priority is not itself a bug. Earlier in CopyObject, the server examines source checksum metadata to decide whether to preserve its algorithm, recompute a full-object value, or add the default CRC64NVME checksum. For an SSE-C source, that metadata is protected by the source object key and therefore requires the copy-source headers.

Changing the global priority to prefer destination SSE-C headers would fix the final response while breaking source checksum interpretation. The safe boundary is temporal and object-specific:

```text
before commit: full request headers, source context
after commit:  destination-only SSE-C headers, destination context
```

The repair applies only at that post-commit boundary.

## Selected implementation {#implementation}

### Destination response view {#destination-view}

The handler clones the request headers and removes exactly:

- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Algorithm`;
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key`;
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key-MD5`.

Regular destination SSE-C headers remain. SSE-S3 and SSE-KMS destination metadata needs no customer key and continues through the existing path.

### Decrypt once, project twice {#single-decrypt}

Before the repair, CopyObject called `decryptChecksums` once while building XML and again while writing success headers. For SSE-S3 or SSE-KMS this could repeat KMS unseal work.

The repaired flow is:

```text
committed ObjectInfo
  -> decryptChecksums(destination headers) once
  -> CopyObjectResult XML fields
  -> x-amz-checksum-* and x-amz-checksum-type response headers
```

The generic `setPutObjHeaders` wrapper remains available to PutObject, CompleteMultipartUpload, and DeleteObject. CopyObject calls a narrow helper that accepts the already decrypted checksum map. ETag, VersionID, delete-marker, lifecycle prediction, and checksum header behavior remain in one shared implementation.

## Regression matrix {#tests}

The tests cover:

- plaintext source to SSE-C destination;
- compressed and uncompressed SSE-C destinations;
- SSE-C source key A to destination key B;
- checksum value and type in both CopyObject XML and HTTP headers;
- stored checksum decrypted with destination key B;
- destination body readable with B;
- same-object key rotation from A to B;
- checksum response after rotation;
- SSE-S3 source and destination combinations;
- all object-layer backends used by the API test harness.

The final combined tree passed focused encryption tests, the complete `cmd` and `internal` suites, the project's tagged test configuration, full `go test -race ./...`, vet, lint, generated-file checks, rebrand guards, and a local build. A mirror Fable Max review reported no P0–P2 findings and independently confirmed that source decryption still receives the full request while destination response decryption receives the filtered view.

## Compatibility and operational impact {#impact}

- **Successful CopyObject responses:** checksum fields that were previously missing now appear when the committed destination has a checksum.
- **Stored objects:** no rewrite, migration, metadata-format, or encryption-format change.
- **Existing objects:** unaffected; the defect existed only in the one-time successful response.
- **Clients:** no request change. Clients already providing both source and destination SSE-C keys receive a more complete S3-compatible result.
- **Performance:** one metadata checksum decryption instead of two; no additional object read or hash pass.
- **Rolling upgrade:** old nodes may omit the fields while new nodes return them. Stored objects remain mutually readable.
- **Rollback:** restores response omission but does not damage objects created while the repair was present.
- **Security:** no key or digest value is added to logs or error responses. The response carries only the checksum already authorized for the successful write.

This repair does not resolve the separately deferred legacy federation CopyObject branch and does not audit or modify historical compressed-object checksums. Those questions have different data and operational boundaries.

## Conclusion {#conclusion}

CopyObject is one request with two object identities. Reusing the full request after commit erased that distinction: a source key was allowed to shadow the destination key while describing destination metadata. The durable repair is not a new encryption scheme; it is an explicit context boundary, followed by one decryption and two faithful response projections.
