---
title: "Two SSE-C Keys, One CopyObject Response"
linkTitle: "CopyObject SSE-C Checksums"
date: 2026-08-28
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  CopyObject can carry one SSE-C key for the source and another for the destination. SILO stored the destination checksum under the destination key but tried to decrypt it for the response with the source key, silently omitting checksum fields.
tags: [Design, S3, SSE-C, Checksum, Compatibility]
weight: 17
draft: false
url: "/blog/design/copyobject-ssec-checksum-response/"
---

This note documents the `CopyObject` SSE-C checksum response repair committed as `e73436c99` and shipped in [Server 20260903](/blog/release/silo-20260903/). It covers the successful `CopyObject` XML and HTTP response after the destination object has committed; stored object bytes, checksum metadata, encryption formats, source decryption, federation, and replication remain unchanged.

## Overview {#tldr}

An SSE-C `CopyObject` request can supply two independent customer-provided encryption keys:

| Role | Request Headers | Purpose |
| --- | --- | --- |
| Source | `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` | Decrypt the source object and its stored metadata |
| Destination | `X-Amz-Server-Side-Encryption-Customer-*` | Encrypt and later interpret the committed destination object |

SILO encrypted the destination object and sealed its checksum metadata under the destination key. However, after the write committed, both the `CopyObjectResult` XML builder and the generic PUT-response header helper received the original `CopyObject` request headers. Because `decryptChecksums` prioritizes `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` headers whenever they are present—which is right while reading the source object—it attempted to unseal the committed destination's checksum metadata using the source key.

With source key `A` and destination key `B`:

```text
source body       --decrypt A--> logical bytes
logical bytes     --encrypt B--> committed destination
destination csum  --seal B-----> stored checksum metadata
response decoder  --try A------> key mismatch, checksum omitted
```

The stored destination object and its encrypted checksum metadata were valid, but the one-time `CopyObject` response omitted the checksum fields. The repair constructs a destination response-header view by stripping the three copy-source SSE-C headers, decrypts the committed destination checksum metadata once under key `B`, and reuses that map for both the `CopyObjectResult` XML body and the HTTP response headers.

## Observable Failure {#failure}

Triggering the bug required a checksum-bearing destination object and distinct source and destination SSE-C keys:

```http
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

- `CopyObject` succeeded with HTTP 200.
- `GetObject` on the destination with key `B` returned the expected plaintext body.
- `HeadObject` on the destination with key `B` decrypted the stored checksum metadata and returned `x-amz-checksum-crc32` and `x-amz-checksum-type`.
- The `CopyObject` XML body and HTTP response headers omitted both `ChecksumCRC32` / `x-amz-checksum-crc32` and `ChecksumType` / `x-amz-checksum-type`.

The same mismatch affected in-place SSE-C key rotation (copying an object onto itself with a new SSE-C key). Once the destination metadata was resealed under key `B`, the request still carried the old key `A` in the copy-source headers, causing response generation to fail checksum decryption.

## Why the Global Decrypter Must Not Change {#source-boundary}

`decryptChecksums` prefers copy-source SSE-C headers for a valid reason: earlier in `CopyObject`, the server inspects the source object's checksum metadata to decide whether to carry its algorithm forward, recompute a full-object digest from a composite source, or attach a default `CRC64NVME` checksum. When the source object is SSE-C encrypted, its checksum metadata is sealed under the source key and requires the `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` headers.

Inverting the global header priority inside `decryptChecksums` to prefer destination SSE-C headers would fix the post-commit response while breaking pre-commit source checksum inspection. The boundary is temporal and object-specific:

```text
before commit: full request headers        -> source SSE-C context
after commit:  destination-only headers    -> destination SSE-C context
```

## Implementation {#implementation}

### Destination Response View {#destination-view}

After the destination write commits, the handler clones the request header map and deletes the three copy-source SSE-C headers:

- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Algorithm`
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key`
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key-MD5`

Destination `X-Amz-Server-Side-Encryption-Customer-*` headers remain intact. `SSE-S3` and `SSE-KMS` destination metadata require no customer header and continue through the existing path.

### Decrypt Once, Project Twice {#single-decrypt}

Previously, `CopyObject` called `decryptChecksums` once while constructing the `CopyObjectResult` XML struct and a second time inside `setPutObjHeaders` while writing HTTP response headers. For `SSE-S3` or `SSE-KMS` objects, that duplicated KMS or master-key unseal work.

The repaired flow decrypts the destination checksum map once and projects it into both outputs:

```text
committed ObjectInfo
  -> decryptChecksums(destination headers) once
  -> CopyObjectResult XML fields
  -> x-amz-checksum-* and x-amz-checksum-type response headers
```

The general `setPutObjHeaders` helper remains unchanged for `PutObject`, `CompleteMultipartUpload`, and `DeleteObject`, while `CopyObject` passes the pre-decrypted checksum map directly to the shared header writer.

## Regression Matrix {#tests}

The encryption and API test suites cover:

- Plaintext source to SSE-C destination.
- Compressed and uncompressed SSE-C destinations.
- SSE-C source key `A` to SSE-C destination key `B`.
- Verification of checksum digest and `ChecksumType` in both `CopyObjectResult` XML and HTTP response headers.
- Verification that stored destination checksums decrypt with key `B` and match the destination body.
- In-place same-object SSE-C key rotation from key `A` to key `B`.
- `SSE-S3` source and destination combinations across erasure backends.

## Compatibility and Operational Impact {#impact}

- **Successful `CopyObject` responses:** Checksum digest and `ChecksumType` fields that were previously omitted when copying into an SSE-C destination now appear in both the XML body and HTTP response headers.
- **Stored objects:** No on-disk rewrite, metadata format change, or encryption format change is required; existing objects were already stored with valid destination checksum metadata.
- **Performance:** Checksum metadata is decrypted once per `CopyObject` response instead of twice, with no extra object read or hashing pass.
- **Rolling upgrades and rollback:** Upgraded nodes return the checksum fields immediately while older nodes may still omit them during a rolling upgrade window; stored objects remain readable across both versions.

## Conclusion {#conclusion}

Decrypting `ObjectInfo` before building the `CopyObjectResult` XML payload (`21870fa2e`) restores the stored checksum fields on SSE-C and KMS copy responses without altering storage layout or encryption semantics.
