---
title: "Federated CopyObject: Preserve the Destination Contract"
linkTitle: "Federated CopyObject: Preserve the Destination Contract"
date: 2026-09-16
lastmod: 2026-09-17
author: "Ruohang Feng"
summary: >
  Shipped in Server 20260916 (PR #157, #159, #163, #177, #179), legacy etcd federated CopyObject forwards logical source bytes, preserves destination encryption defaults and Object Lock headers, validates full-object checksums, and returns the exact committed write identity.
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/federated-copy-object/"
---

[Server 20260916](/blog/release/silo-20260916/) repairs the legacy etcd bucket-federation `CopyObject` path across [PR #157](https://github.com/pgsty/silo/pull/157), [PR #159](https://github.com/pgsty/silo/pull/159), [PR #163](https://github.com/pgsty/silo/pull/163), [PR #177](https://github.com/pgsty/silo/pull/177), and [PR #179](https://github.com/pgsty/silo/pull/179). When `CopyObject` forwards a copy across federated deployments as a remote `PutObject`, the proxy streams logical source bytes, delegates destination encryption and Object Lock enforcement to the destination deployment, validates full-object checksums, and returns the exact committed version metadata.

## Logical Byte Streaming and Destination Encryption {#bytes}

The proxy reads logical source bytes by decrypting and decompressing the source object locally and declaring the logical content length on the outbound `PutObject` request:

- **No double transformation:** The proxy never encrypts or compresses payload bytes locally before forwarding them to the remote deployment.
- **SSE-C and SSE-KMS handling:** Reading an SSE-C source requires the source customer key over TLS. Destination encryption is governed by the request's explicit destination SSE headers or the destination bucket's default encryption configuration; the proxy never injects its own local encryption defaults when the caller omits SSE headers. SSE-KMS context headers are forwarded as valid JSON objects.
- **Raw SSE-C replica exclusion:** Trusted raw SSE-C replica `CopyObject` requests are rejected with `501 NotImplemented` on the federated path before creating any destination object.

## Checksum and Metadata Forwarding {#checksums}

The proxy strips all reserved internal metadata prefixes (case-insensitively) from the outbound `PutObject` call and forwards only public user metadata and tags through standard S3 headers. Checksums on the forwarded write must describe the logical full object written at the destination:

- **Algorithm and composite conversion:** When the request specifies a checksum algorithm or the source carries a multipart `COMPOSITE` checksum, the destination write computes and stores a `FULL_OBJECT` checksum.
- **Trailer vs. header delivery:** Nonempty streams deliver computed digests in an `x-amz-trailer` checksum trailer, which the destination validates. Zero-byte objects use a standard `x-amz-checksum-*` request header, and existing `FULL_OBJECT` source checksums are forwarded via standard checksum headers.
- **Remote response verification:** If a required checksum in the remote `PutObject` response is missing, malformed, or carries a multipart `-N` suffix, the proxy returns an error. Because the remote write may already have committed before response validation fails, callers copying into a versioned bucket should inspect the destination before retrying.

## Object Lock Precision and Typed Headers {#lock}

The proxy forwards legal hold state through the typed `LegalHold` client option so it is sent as `x-amz-object-lock-legal-hold` rather than `x-amz-meta-*` user metadata. Retention timestamps retain full sub-second precision instead of being truncated to whole seconds. The destination deployment enforces authentication and bucket Object Lock rules.

## Committed Write Identity {#result}

Both the `CopyObjectResult` XML response and the `ObjectCreated:Copy` notification event report the committed destination key, logical size, ETag, exact `VersionID`, and modification time returned in the authenticated write-time response from the destination deployment. The proxy neither fabricates a local timestamp nor issues a follow-up unversioned `HEAD` request that could observe a concurrent writer. When the caller specifies a source `versionId`, source-version response headers continue to identify the selected source version.

## Source and Test Index {#verification}

- **Implementation:** [`cmd/object-handlers.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go), [`cmd/object-handlers-common.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers-common.go) ([PR #157](https://github.com/pgsty/silo/pull/157), [PR #159](https://github.com/pgsty/silo/pull/159), [PR #163](https://github.com/pgsty/silo/pull/163), [PR #177](https://github.com/pgsty/silo/pull/177), [PR #179](https://github.com/pgsty/silo/pull/179))
- **Regression tests:** `cmd/object-copy-federation*_test.go`, `cmd/object-federation-time_test.go`
- **Related records:** [SSE-C Replica Integrity](/blog/design/ssec-replica-integrity/) · [Object Lock Replication Ordering](/blog/design/object-lock-replication-ordering/) · [Component Version Matrix](/compatibility/versions/)
