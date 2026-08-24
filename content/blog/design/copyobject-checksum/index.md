---
title: "CopyObject Checksums Must Cover Logical Object Bytes"
date: 2026-08-24
lastmod: 2026-08-24
author: "Ruohang Feng"
summary: >
  When destination compression was enabled, SILO could persist a CopyObject checksum of the S2 storage stream instead of the logical S3 object. This record explains the plaintext-reader invariant, verification boundary, related fixes, and remediation of older objects.
tags: [Design, S3, Compatibility, Checksum]
weight: 10
draft: false
url: "/blog/design/copyobject-checksum/"
---

This is the design and verification record for [SILO #63](https://github.com/pgsty/silo/issues/63).

**Status:** the checksum-domain fix was merged through [PR #66](https://github.com/pgsty/silo/pull/66); public release pending.  
**Related fixes:** metadata-only transform state [#67](https://github.com/pgsty/silo/issues/67) through [PR #69](https://github.com/pgsty/silo/pull/69), and CopyObjectResult checksum fields [#68](https://github.com/pgsty/silo/issues/68) through [PR #70](https://github.com/pgsty/silo/pull/70); both merged, public release pending.
**Upstream client:** [minio-go #2295](https://github.com/minio/minio-go/pull/2295).  
**Release boundary:** a merge does not prove that a release artifact, package, or container image already contains the fix.

## The defect {#defect}

CopyObject reads the source as logical object data, then may compress and encrypt the destination storage stream. The old handler installed a requested server-side checksum on a reader that already represented compressed bytes:

    logical object -> S2 compression -> checksum -> optional encryption -> storage

The digest was valid but covered the wrong byte domain. A client downloading and independently hashing the object therefore obtained a different value. The API reproduction was deterministic:

    stored CRC32 before the fix: hN7ytg==
    logical object CRC32:         1WxbLg==

All five algorithms implemented by this SILO baseline were affected: CRC32, CRC32C, CRC64NVME, SHA1, and SHA256. Compression combined with encryption made the wrong value nondeterministic because encrypted-stream S2 padding is randomized.

## Accepted invariant {#invariant}

The logical checksum reader is now separate from storage transformation readers:

    logical object
        -> server-side checksum
        -> optional S2 compression
        -> storage hash
        -> optional server-side encryption
        -> erasure coding and commit

The handler installs the hasher before starting the compression goroutine. PutObjReader retains the logical reader even when its active storage reader is replaced. At EOF, the object layer requires the checksum to exist, be valid, and match the expected base algorithm before committing metadata.

This reuses the checksumReader contract introduced for multipart upload. It adds no second abstraction, no second object read, and no new on-disk representation.

## Verification boundary {#verification}

The permanent API suite covers all five algorithms and default CRC64NVME; uncompressed, compressed, encrypted-only, and compressed-plus-encrypted destinations; SSE-C and SSE-S3; encrypted and compressed sources; versioned buckets; full and multipart-composite source checksums; in-place copy; zero-length and threshold data; indexed S2 streams; ETag; body round trip; HEAD/GET checksum mode; and internal invariant failures.

The regression is red on the unfixed baseline and green on the repaired tree. Focused race tests, shuffled repeated runs, full cmd tests, the CGO-disabled kqueue/dev CI shape, lint, vet, cross-compilation, compatibility guards, and remote CI were also required before merge.

## Adjacent defects kept separate {#adjacent}

Adversarial review found two inherited defects in nearby code:

1. A metadata/reference-only self-copy could change compression markers without rewriting referenced data. Versioned SSE-C key rotation could also fall into an invalid rewrite. This is isolated in [#67](https://github.com/pgsty/silo/issues/67).
2. Successful CopyObject XML omitted checksum elements after the checksum was committed. The server response fix is [#68](https://github.com/pgsty/silo/issues/68); minio-go also discarded those fields and is followed in [#2295](https://github.com/minio/minio-go/pull/2295).

Legacy federated UploadPartCopy checksum recovery is a different API and remains [#64](https://github.com/pgsty/silo/issues/64).

The archived upstream minio/minio tree retains the original placement. silo-pkg does not own this reader chain. MCLI switches from server-side copy to download/upload when --checksum is requested, and SILO Console only passes CopyObject through minio-go, so neither required a duplicate server fix.

## Existing objects {#existing-objects}

The repair affects future CopyObject operations. It does not scan or rewrite checksum metadata already stored by an affected version.

Objects are candidates for verification when they were created by CopyObject, destination compression matched their key or content type, and they carry an additional S3 checksum. Retrieve the object with checksum mode enabled, independently hash the downloaded logical bytes with the reported algorithm, and compare the Base64 values.

To repair an object, copy it to a new key while explicitly selecting the checksum algorithm. An in-place copy is possible with x-amz-metadata-directive: REPLACE, but it rewrites the object and replaces the current value on an unversioned bucket; a versioned bucket receives a new version. Validate retention, legal hold, metadata, tags, encryption keys, free capacity, and rollback requirements before bulk remediation.

SILO does not perform automatic online backfill because that would read and rewrite user data outside an explicit S3 operation.
