---
title: "SSE-C Replica Integrity"
linkTitle: "SSE-C Replica Integrity"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: "Raw ciphertext, logical multipart sizes, retransmission and compression exclusions form one replica contract."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/ssec-replica-integrity/"
---

**Source status, 2026-09-16:** the repairs in [#122](https://github.com/pgsty/silo/pull/122), [#123](https://github.com/pgsty/silo/pull/123), [#124](https://github.com/pgsty/silo/pull/124), [#126](https://github.com/pgsty/silo/pull/126) and [#134](https://github.com/pgsty/silo/pull/134) are on main, not published Server 20260903. Earlier zero-byte/read-attribute authentication and destination-key checksum repairs did ship in 20260903. Do not treat all SSE-C fixes as one release.

## Ciphertext and trust {#ciphertext}

An ordinary SSE-C request supplies the customer key and operates on plaintext. An authorized replica transfer can carry raw ciphertext with the sealed object-key metadata needed to preserve the original object. The destination must store those bytes verbatim; encrypting them again produces an unreadable double-encrypted object. The internal marker alone is not authorization: the exact replication marker and the required replication permission remain mandatory.

This path does not reveal the customer key or make a normal keyless read permissible. Ordinary GET/HEAD and `GetObjectAttributes` keep their key/permission checks. [Federated raw SSE-C replica COPY](/blog/design/federated-copy-object/#bytes) is explicitly unsupported.

## Multipart sizes and checksums {#multipart}

Encrypted part size and logical plaintext part size are different. Replica multipart records preserve the actual logical size of each part so `partNumber` reads, ranges and `GetObjectAttributes` agree with the source after overwrite. Checksums must retain the correct encryption context and logical meaning; a checksum response cannot be decrypted with the source key after a copy committed under a different destination key.

For ordinary SSE-C key rotation, any explicitly requested checksum algorithm forces a complete rewrite on current main, even if it names the existing algorithm. A multipart source becomes a single-part destination; the ETag can change and replication retransmits object bytes. An eligible metadata-only rotation without that request preserves the prior checksum state, including absence. See the [operator procedure](/administration/server-side-encryption/server-side-encryption-sse-c/#rotate-the-sse-c-key-of-an-object).

## Retransmission and Object Lock {#retransmission}

A keyless target HEAD can report an existing SSE-C object as inaccessible rather than absent. The sender must distinguish this from `NoSuchKey`; it cannot assume an ordinary metadata-only COPY will repair the replica. Existing SSE-C replicas use object retransmission. A destination with undecodable old replica state can be replaced through the repaired retransmit path, while preserving the newer destination Object Lock state and ordering removal timestamps correctly.

A failed old replica is not automatically certified repaired after a Server upgrade. Re-read the exact source and replica versions with approved key access, compare the logical bytes and part boundaries, and check retention/legal hold separately. Never infer integrity from a successful metadata-only HEAD alone.

## Compression and historical objects {#compression}

Current main excludes every new SSE-C write from compression, including normal PUT, multipart initiation, COPY and Snowball. SSE-S3 and SSE-KMS continue to follow their encrypted-compression setting. This avoids a replica format that transports ciphertext without the required compression metadata.

Historical compressed SSE-C objects are not automatically rewritten. Preserve their keys and exact version identities, inventory affected data, and rehearse a supported rewrite/recovery path. The change is preventive, not a background migration or a promise that arbitrary old ciphertext can be recovered.

## Verification boundary {#verification}

The [compression decision](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-api-utils.go), `replication-trust-ssec-replica_test.go`, `erasure-multipart-ssec-replica_test.go`, `replication-ssec-retransmit_test.go` and `compression-ssec_test.go` preserve the relevant source and regression contracts. Tests include incorrect-key/unauthorized controls, multipart byte comparisons and retransmission cases. They do not replace a deployment's historical-state inventory.

See [Object Lock ordering](/blog/design/object-lock-replication-ordering/), [multi-pool consistency](/blog/design/multi-pool-object-consistency/) and [replica recovery](/operations/replication/replica-metadata-audit/). Upgrade every participating Server before relying on the combined behavior.
