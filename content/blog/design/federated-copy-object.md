---
title: "Federated CopyObject: Preserve the Destination Contract"
linkTitle: "Federated CopyObject: Preserve the Destination Contract"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: "Legacy etcd federation must forward logical bytes, preserve destination encryption and Object Lock, and return the exact committed write."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/federated-copy-object/"
---

**Source status, 2026-09-16:** this records the main-branch CopyObject fixes in [#157](https://github.com/pgsty/silo/pull/157), [#159](https://github.com/pgsty/silo/pull/159), [#163](https://github.com/pgsty/silo/pull/163), [#177](https://github.com/pgsty/silo/pull/177) and [#179](https://github.com/pgsty/silo/pull/179). They are absent from Server 20260903. The subject is the **legacy etcd bucket-federation** path that forwards a copy to another deployment as `PutObject`, not the bucket/site replication scheduler.

## Forward bytes once, encrypt at the destination {#bytes}

The proxy reads logical source bytes: it decrypts and decompresses as needed, then declares the logical length to the destination. It must not locally encrypt/compress and ask the remote to do it again. SSE-C reads still require the source key and secure transport. The destination's explicit SSE headers or its own encryption defaults choose how the new object is stored; the proxy must not inject its local defaults when the caller selected none. SSE-KMS context is forwarded in the expected JSON-object form.

Trusted raw SSE-C replica CopyObject is explicitly rejected with `501 NotImplemented` in this federation path, before creating the destination. That combination is not made safe merely by passing replication markers. Ordinary key-authorized SSE-C copies and the dedicated replica path are different operations.

## Checksum and metadata rules {#checksums}

Remove every reserved internal metadata prefix, case-insensitively, from the ordinary forwarded write. Forward public metadata and tags through supported fields, not internal storage encoding. The checksum must describe the logical full object actually written:

- A requested algorithm or a multipart-composite source requires a full-object checksum at the destination.
- For a nonempty stream, the client uses a trailing checksum, including `x-amz-trailer`; the destination must consume and validate that trailer.
- Empty content uses the ordinary checksum header because there is no streamed checksum trailer to carry its digest.
- A stored full-object source checksum can be forwarded as an ordinary checksum header for validation.
- A required remote checksum that is missing, malformed or has a multipart `-N` suffix is an error; it must not be reported as a valid full-object result.

The remote write may already have committed when a malformed success response is detected. A resulting error does not prove destination absence. Inspect the written version before blindly retrying a versioned copy.

## Object Lock is not user metadata {#lock}

Forward legal hold through the typed `LegalHold` option so it becomes `x-amz-object-lock-legal-hold`, not `x-amz-meta-*`. Retain the full precision of the retention timestamp; routing it through a whole-second conversion would weaken the requested value. Authentication and the destination's Object Lock rules still apply.

## Return the committed write {#result}

The response and `ObjectCreated:Copy` event describe the destination key, logical size, ETag and exact version ID. Modification time is obtained from the destination write, not invented at the proxy or obtained through a later unversioned HEAD that could observe another writer. The internal write-time response is bound to the authenticated federation request. Source-version response headers still identify the selected source when one was provided.

## Evidence and deployment boundary {#verification}

See the [handler](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go), [write-time transport](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers-common.go), and `object-copy-federation*_test.go` / `object-federation-time_test.go`. Tests cover ordinary, empty, multipart, compressed and encrypted sources, remote checksum failures, destination defaults, legal hold, response identity and events. These component fixtures do not certify a production etcd federation or every S3-compatible destination.

Verify both forwarding and destination builds from the [component matrix](/compatibility/versions/). Existing objects are not rewritten by upgrading. Related records cover [SSE-C replica integrity](/blog/design/ssec-replica-integrity/) and [Object Lock ordering](/blog/design/object-lock-replication-ordering/).
