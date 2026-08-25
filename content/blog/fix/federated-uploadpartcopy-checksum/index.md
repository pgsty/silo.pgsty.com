(B[m---
title: "Federated UploadPartCopy Checksum Repair"
linkTitle: "Federated UploadPartCopy Checksum"
date: 2026-08-24
author: "Ruohang Feng"
description: "How Silo returns the checksum from the exact remote part write in legacy etcd federation without changing ordinary UploadPart responses, and which versions must be upgraded together."
tags: [Fix, silo, S3, Checksum]
weight: 10
draft: true
url: "/blog/fix/federated-uploadpartcopy-checksum/"
---

> **Release status:** this fix note is a draft. It describes the repair for [Silo #64](https://github.com/pgsty/silo/issues/64), but does not claim that a release containing the repair has been published.

Legacy etcd federation handles an `UploadPartCopy` whose source and destination buckets live on different deployments by reading the source on one deployment and sending the copied bytes to the destination as an ordinary `UploadPart`. That translation created a response mismatch after the server-side checksum repair in [#46](https://github.com/pgsty/silo/issues/46): the destination computed and persisted the missing part checksum, but an ordinary `UploadPart` correctly omitted a checksum that the request did not provide. The proxy therefore had no value to place in `CopyPartResult`.

The repair keeps the external S3 contract unchanged. The existing federation client identifies its remote request with the minio-go application token `minio-federated/<version>`. When the destination successfully commits that request, it returns the non-empty checksum fields from the same internal `PartInfo` that contains the response ETag. Ordinary `UploadPart` callers still receive a checksum only when they supplied one.

The application token is a response-shape hint, not an authorization boundary. `User-Agent` is not trusted for access control, object visibility, or checksum validation. A caller that deliberately uses the token can only receive the checksum of the bytes it was already authorized to upload.

## Why the response is returned directly {#direct-response}

The proxy does not recover the checksum with `ListParts` after the write. A lookup would require an additional permission and network round trip, can scan many part metadata files, and can race with another writer replacing the same part number. Returning the checksum from the exact completed write binds the ETag and checksum to one result and adds no storage read.

The response contains only the concrete `x-amz-checksum-crc32`, `x-amz-checksum-crc32c`, `x-amz-checksum-sha1`, `x-amz-checksum-sha256`, or `x-amz-checksum-crc64nvme` value that exists. It does not add `x-amz-checksum-type` to `UploadPart`.

## Upgrade compatibility {#upgrade-compatibility}

Treat the repair as a coordinated federation upgrade:

| Proxy / source deployment | Destination deployment | Result |
|:--|:--|:--|
| Contains the #46 `CopyPartResult` checksum mapping | Contains both #46 checksum computation and the #64 response repair | `UploadPartCopy` returns the checksum for `FULL_OBJECT` and `COMPOSITE` uploads |
| Contains the #46 mapping | Contains #46 but not #64 | The remote part succeeds and persists its checksum, but the federated `CopyPartResult` can remain checksum-less |
| Any version | Predates #46 | A checksum-enabled remote upload may reject the forwarded part because no request checksum is available |
| Predates the #46 mapping | Contains #64 | The remote can return the value, but the old proxy is not guaranteed to expose it in `CopyPartResult` |

Upgrade every deployment that can act as either the source proxy or destination before relying on federated `UploadPartCopy` checksum responses. Mixed-version operation retains the older behavior; this change does not claim a new cross-version federation protocol.

## Verification scope {#verification}

The regression suite covers `CRC32` with `FULL_OBJECT`, `SHA256` with `COMPOSITE`, exact and lookalike application tokens, the real minio-go `Core.PutObjectPart` response parser, and concurrent writes replacing the same part number. It also keeps the existing assertion that an ordinary `UploadPart` without a request checksum does not expose the server-computed value.

This repair is limited to the checksum response. The legacy federated path's separate zero `LastModified` response defect is not changed here.
