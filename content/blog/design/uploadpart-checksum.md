---
title: "Optional Checksums, Mandatory Failure: Repairing UploadPart and UploadPartCopy Compatibility"
linkTitle: "Multipart Checksum Compatibility"
date: 2026-08-24
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  SILO required every part in a checksum-enabled multipart upload to carry a per-part checksum. That rejected ordinary UploadPart requests that omitted an optional header and made UploadPartCopy unusable. This record covers discovery, AWS and AIStor research, rejected designs, the one-pass plaintext solution, the compatibility-baseline blocker, design review, and the consistency contract for follow-up repairs.
tags: [Design, S3, Compatibility, Checksum]
weight: 30
draft: false
url: "/blog/design/uploadpart-checksum/"
---

This is the design and implementation record for [SILO #46](https://github.com/pgsty/silo/issues/46) (merged as [`7fea6d5a5`](https://github.com/pgsty/silo/commit/7fea6d5a5) and shipped in [Server 20260903](/blog/release/silo-20260903/), with follow-up items [#63](https://github.com/pgsty/silo/issues/63) and [#64](https://github.com/pgsty/silo/issues/64)). It documents how handling an optional S3 part checksum header affected multipart completion semantics, copy responses, compression and encryption pipelines, and compatibility baselines.

## Too Long; Didn't Read (TL;DR) {#tldr}

A multipart upload (MPU) splits a large object into smaller parts. A client may attach a checksum to each part so the server can verify the transfer, but AWS defines that per-part header as optional. SILO previously treated it as mandatory: an ordinary `UploadPart` failed without one, and `UploadPartCopy` could never succeed because it has no request body to checksum.

After the fix, SILO still validates a checksum when the client sends one. When the client omits it, SILO computes the checksum in a single pass while reading the logical plaintext bytes and persists the result in part metadata. This happens before compression and encryption, requires no second disk read, and changes no on-disk format.

## Decision {#decision}

When a multipart upload declares a checksum algorithm in `CreateMultipartUpload`, SILO enforces the following contract:

1. If the client supplies a part checksum, the server validates it; a mismatched value or algorithm fails immediately and is never masked by server-side fallback computation.
2. If the client omits the part checksum, the server computes it in one pass with the MPU algorithm over the logical plaintext stream, before compression and encryption, and persists the result.
3. A normal `UploadPart` echoes a checksum response header only when the client supplied the checksum in the request; a server-computed fallback value is not echoed.
4. `UploadPartCopy` has no client part-body checksum, so the server computes the value and returns it in `CopyPartResult`.
5. `ListParts` returns the persisted part checksum.
6. `FULL_OBJECT` completion continues to combine the full-object checksum linearly from stored part checksums. `COMPOSITE` completion continues to require a checksum for every part, which clients can retrieve via `ListParts`.
7. Computation happens during the initial read; completion never re-reads the entire object.

## How We Found It {#discovery}

The defect surfaced while investigating a separate multipart checksum issue, [#31](https://github.com/pgsty/silo/issues/31).

#31 concerned `CompleteMultipartUpload`: for `FULL_OBJECT`, a client can complete an upload with part numbers, ETags, and an optional full-object checksum without listing every part checksum in the completion XML. Tracing that path backward exposed a stricter check in `erasureObjects.PutObjectPart`:

```go
if cs := fi.Metadata[hash.MinIOMultipartChecksum]; cs != "" {
    if r.ContentCRCType().String() != cs {
        return InvalidArgument{/* checksum missing */}
    }
}
```

Once an MPU declared a checksum algorithm, every `UploadPart` had to carry a matching `x-amz-checksum-*` header. Omitting it returned:

```text
400 InvalidArgument:
checksum missing, want "CRC32", got ""
```

API probes reproduced this error on both single-drive and erasure backends.

Inspecting `CopyObjectPartHandler` elevated the issue to P0. `UploadPartCopy` has no request body for the caller to checksum: the handler reads the source object, constructs an internal reader, and calls `PutObjectPart`. No client header or SDK setting could satisfy the check, so every checksum-enabled MPU rejected `UploadPartCopy` unconditionally.

## What AWS Requires {#aws-contract}

The S3 API specification defines distinct behavior across the three operations:

- The [AWS UploadPart API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html) defines each algorithm-specific checksum header as an optional data-integrity check and specifies that the response header is returned only when the checksum was provided in the request.
- The [AWS UploadPartCopy API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html) specifies that when an MPU was created with a checksum algorithm, `CopyPartResult` includes the computed checksum for the copied part.
- The [AWS ListParts API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html) returns the stored checksums for parts in an in-progress upload.

The algorithm and checksum-type support matrix is:

| Algorithm | `FULL_OBJECT` | `COMPOSITE` |
| --- | --- | --- |
| CRC64NVME | Supported | Unsupported |
| CRC32 / CRC32C | Supported | Supported |
| SHA1 / SHA256 | Unsupported | Supported |

`FULL_OBJECT` applies only to linearizable CRCs, whereas SHA1 and SHA256 require per-part digests to compute the `COMPOSITE`checksum at completion.

Although recent AWS SDKs calculate request checksums by default when supported, callers can set `request_checksum_calculation = when_required` or use low-level APIs that declare an algorithm on `CreateMultipartUpload` without sending checksum headers on every `UploadPart`.

## Why Removing the Check Is Not a Fix {#completion-invariant}

Simply deleting the check in `PutObjectPart` would defer the failure to `CompleteMultipartUpload`.

SILO does not re-read all object bytes during MPU completion. Instead, it reads `ObjectPartInfo.Checksums` from each `part.N.meta`:

- a missing entry immediately fails with `InvalidPart`;
- `FULL_OBJECT` calls `Checksum.AddPart` to combine part digests using their part lengths;
- `COMPOSITE` concatenates the raw part digest bytes and hashes them into the object-level digest.

The storage invariant is therefore:

```text
checksum-enabled MPU
        => every committed part has a checksum for the MPU algorithm
```

Removing the upload check without populating part metadata would let `UploadPart` succeed, omit checksums from `ListParts` and `UploadPartCopy`, and fail during `CompleteMultipartUpload`.

## Alternatives Considered {#alternatives}

| Option | Benefit | Fatal problem | Decision |
| --- | --- | --- | --- |
| Delete the strict check | Smallest diff | Part metadata still lacks the checksum; completion fails with `InvalidPart` | Rejected |
| Relax only `FULL_OBJECT` | Unblocks some default CRC clients | Leaves `COMPOSITE` and SHA1/SHA256 broken; cannot close #46 | Rejected |
| Re-read every part at completion | Avoids storing a digest during upload | Adds $O(\text{object size})$ second-pass I/O and leaves `ListParts` and copy responses incomplete | Rejected |
| Always return the server value from normal `UploadPart` | Simplifies federation forwarding | Violates the AWS `UploadPart` response contract | Rejected |
| Copy the AIStor implementation directly | Commercial precedent | Supports only mergeable CRCs and attaches the hasher where streams may already be compressed or encrypted | Rejected |
| Compute and persist in one pass over logical plaintext | Full protocol compliance, no second I/O, supports both CRC and SHA | Requires an explicit plaintext checksum reader separate from the storage reader | Accepted |

### What Commercial AIStor Revealed {#aistor}

We inspected MinIO AIStor `RELEASE.2026-08-07T18-34-35Z` using Go `pclntab` symbol recovery and ARM64 disassembly. Static analysis showed that AIStor:

- installs a server hasher when the client checksum is absent;
- persists the result in part metadata;
- includes checksum fields in `CopyPartResult`.

However, AIStor enables fallback computation only for `CanMerge()` algorithms (CRC32, CRC32C, and CRC64NVME), leaving SHA1 and SHA256 `COMPOSITE` uploads to fail with `checksum missing`. In addition, AIStor attaches the hasher inside the object layer to `r.Reader`, which under server-side compression or encryption already carries transformed storage bytes rather than logical S3 plaintext.

## How Design Review Overturned the First Design {#adversarial-review}

Our initial design placed the fallback inside `erasureObjects.PutObjectPart`: inspect the MPU metadata in the object layer and attach a server hasher whenever the incoming reader lacked a client checksum.

Design review caught a critical flaw on the compression path. `newS2CompressReader` is not a lazy wrapper; its constructor immediately spawns a goroutine:

```go
go func() {
    _, err := io.Copy(comp, r)
    // ...
}()
```

The S2 writer also prefetches multiple blocks concurrently. After constructing the compressor, the HTTP handler still parses options, sets up encryption, and calls into the object layer. By the time `PutObjectPart` attached a hasher, the compressor goroutine could already have consumed several MiB from the plaintext reader:

- a large part would produce a checksum missing its leading bytes;
- a small part could hit EOF before the hasher was attached and produce no checksum at all;
- mutating `ServerSideHasher` concurrently with `Read` would trigger a data race.

This split the responsibility cleanly across layers:

- **The HTTP handler** attaches the hasher to the logical plaintext stream before starting any eager transformation (such as concurrent compression or encryption).
- **The object layer** validates the algorithm, verifies that a checksum result was produced, and persists it atomically in `part.N.meta`.

## Final Implementation {#implementation}

### A Dedicated Logical Checksum Reader {#checksum-reader}

`PutObjReader` previously carried two readers:

- `Reader`, the stream written to storage (potentially compressed or encrypted);
- `rawReader`, used for ETag calculation.

Under compression, `rawReader` does not always read plaintext bytes directly; it may only forward an ETag through an `etag.Tagger` wrapper. To keep ETag handling untouched, we added an unexported field to `PutObjReader`:

```go
checksumReader *hash.Reader
```

`checksumReader` always wraps the logical S3 plaintext part stream. `WithEncryption` replaces the storage `Reader` while preserving `checksumReader`.

Unexported accessors on `PutObjReader`:

- report the effective checksum type (client-supplied or server-computed);
- return the client value when present;
- otherwise return the server-computed digest finalized at EOF.

Keeping these helpers unexported avoids expanding the public Go API and provides a shared internal mechanism for [#63](https://github.com/pgsty/silo/issues/63).

### Preparing the Hasher Before Transformations {#prepare-reader}

`prepareMultipartChecksumReader` inspects the algorithm and checksum type stored in the MPU metadata:

1. if the MPU declared no checksum algorithm, it does nothing;
2. if the client provided a checksum, it verifies that the base algorithm matches the MPU;
3. if the algorithm mismatches, it returns `InvalidArgument`;
4. if the client omitted the checksum, it attaches the matching server-side hasher to the plaintext `hash.Reader`.

For normal `UploadPart`:

- the compressed path prepares `actualReader` after parsing request checksums (`actualReader.AddChecksum`) and before calling `newS2CompressReader`;
- the uncompressed path prepares the request hash reader before wrapping it with encryption.

For `UploadPartCopy`:

- a checksum-enabled MPU wraps the logical source byte range in an inner `hash.Reader`;
- a range copy hashes only the requested byte interval;
- compression and destination encryption wrap the stream only after the inner hash reader is installed.

### The Object Layer Remains Authoritative {#object-layer}

Preparing the hasher in the handler does not relax the object-layer invariant. `erasureObjects.PutObjectPart` still:

- re-parses the expected MPU algorithm;
- verifies that the effective checksum type matches;
- reads the computed checksum map after erasure encoding finishes;
- logs an internal error and aborts if an enabled algorithm produced no digest;
- writes the checksum alongside the ETag, sizes, and part index into `part.N.meta` before atomically renaming the part.

Any internal caller that bypasses the HTTP handler without preparing a valid checksum is still rejected before committing the part.

### CopyPart Response Shape {#copy-response}

`CopyObjectPartResponse` adds the five supported checksum fields:

```text
ChecksumCRC32
ChecksumCRC32C
ChecksumCRC64NVME
ChecksumSHA1
ChecksumSHA256
```

Each field uses `omitempty`, preserving the existing XML output for MPUs without checksums. Normal `UploadPart` continues to echo the checksum header via `TransferChecksumHeader` only when supplied by the client.

## Why It Works {#why-it-works}

The resulting part pipeline is:

```text
logical plaintext part
        |
        +--> client checksum verifier (if supplied)
        |         or
        +--> server-side hasher (if omitted)
        |
        v
compression (optional)
        |
        v
encryption (optional)
        |
        v
erasure encode / storage
        |
        v
persist ETag + size + logical part checksum atomically
```

This satisfies all four constraints:

1. **Protocol compatibility:** omitting the optional per-part checksum header succeeds for `UploadPart`, and `UploadPartCopy` works out of the box.
2. **End-to-end verification when supplied:** client-provided checksums are still verified and never masked by server computation.
3. **Plaintext semantics:** checksums always cover logical S3 part bytes rather than compressed or encrypted bytes.
4. **Single-pass streaming:** hashing shares the existing read pass without buffering the full part in memory or re-reading from disk at completion.

`hash.Reader` finalizes `ServerSideChecksumResult` upon reaching EOF. On the compressed path, closing the compression pipe synchronizes the compressor goroutine with the storage read, so the digest is guaranteed to be finalized before `PutObjectPart` reads it after erasure encoding returns. Targeted `-race` tests verify this synchronization boundary.

## The Compatibility-Baseline Blocker {#compat-baseline}

The five new `CopyObjectPartResponse` fields are exported Go identifiers. SILO's `buildscripts/rebrand-guard` scans imports, environment variables, HTTP headers, routes, storage markers, and exported symbols, comparing them bidirectionally against `buildscripts/rebrand-guard/compat-baseline.json`. Any unrecorded addition fails CI.

After adding the five #46 fields to the baseline, the guard reported two remaining additions:

```text
internal/config/notify:notify:type:LegacyDatabaseTargetError
internal/config/notify:notify:method:LegacyDatabaseTargetError.Error
```

Those symbols came from an earlier database-notification fix (`f1ba68358`) on `main`, which exported `LegacyDatabaseTargetError` so the `cmd` startup path could match it via `errors.As` but omitted the baseline update.

Recording both the two notification symbols and the five #46 response fields produced a clean baseline diff of seven additions and zero deletions:

```text
exported=9021
Silo rebrand compatibility baseline is unchanged
```

## Verification Evidence {#verification}

The regression suite runs 76 subtests covering:

- CRC32, CRC32C, and CRC64NVME `FULL_OBJECT`;
- CRC32, SHA1, and SHA256 `COMPOSITE`;
- valid client checksums, mismatched algorithms, and corrupted values;
- omission of server-computed checksums from normal `UploadPart` response headers;
- presence of server-computed checksums in `UploadPartCopy` responses and `ListParts`;
- a 5 MiB + 1 KiB two-part full-object merge;
- zero-length parts and overwriting an existing part number;
- range copies verifying that SHA256 covers only the copied byte range;
- single-drive and 16-drive erasure backends;
- default, versioned, compressed, encrypted, and compressed-plus-encrypted configurations;
- explicit SSE-C and SSE-S3 encryption.

Local validation commands:

```text
go test -race ./cmd -run '^TestAPIUploadPartServerSideChecksum' -count=1
go test ./cmd -count=1
go test ./... -count=1
go vet ./cmd
git diff --check
go run ./buildscripts/rebrand-guard
```

## Cost, Risk, and Rolling-Upgrade Tradeoffs {#tradeoffs}

When a client omits a part checksum on a checksum-enabled MPU, the server hashes the plaintext stream during upload. CRC hashing adds negligible CPU overhead; SHA1 and SHA256 use more CPU, but both run inline with the existing stream read without buffering parts in memory or adding disk I/O.

During a rolling upgrade, upgraded nodes accept checksum-less `UploadPart` requests while unupgraded nodes still return 400. Because the on-disk `ObjectPartInfo.Checksums` format is unchanged, written parts remain compatible across versions, and client-facing behavior converges as soon as all nodes are upgraded.

## Why Two Follow-Ups Were Split Out {#follow-ups}

Design review identified two related issues with separate API and test boundaries:

### #63: CopyObject + Compression {#follow-up-copy}

Ordinary `CopyObject` with server-side checksums and compression could also attach its hasher to the compressed stream rather than the plaintext stream. [#63](https://github.com/pgsty/silo/issues/63) reuses the `checksumReader` mechanism introduced here to fix `CopyObject` under its own test matrix.

### #64: Legacy Federation {#follow-up-federation}

Legacy etcd federation proxies `UploadPartCopy` as a remote `UploadPart` request. Because a standard `UploadPart` response omits server-computed checksums, the proxy cannot read the fallback checksum from the remote response headers to populate `CopyPartResult`. [#64](https://github.com/pgsty/silo/issues/64) addresses the federated proxy path without altering external `UploadPart` response semantics.

Both follow-ups share the same streaming invariant:

> Every server-computed S3 checksum binds to the logical plaintext stream, is installed before any eager transform starts, and is validated and persisted by the object layer.

## Engineering Takeaways {#lessons}

1. **Client-optional headers can still back mandatory storage state.** When the S3 wire protocol allows callers to omit a per-part checksum, the server must compute it during upload so `CompleteMultipartUpload` always finds complete part metadata.
2. **Internal computation and response headers follow separate rules.** `UploadPart` computes missing part checksums for internal metadata while omitting them from response headers, whereas `UploadPartCopy` returns the server-computed digest in `CopyPartResult`.
3. **Attach stream hashers before concurrent transforms.** Because `newS2CompressReader` starts reading immediately in a background goroutine, any plaintext hasher must be installed before constructing the compressor.
4. **Verify third-party behavior against the full matrix.** Disassembling AIStor confirmed the server-side hashing approach, while also showing that SHA1/SHA256 `COMPOSITE` and compressed streams required broader handling.
5. **Track exported API changes in the compatibility baseline.** Updating `compat-baseline.json` keeps every intentional change to exported symbols explicit and auditable.
6. **Share core mechanisms across independent fixes.** [#63](https://github.com/pgsty/silo/issues/63) and [#64](https://github.com/pgsty/silo/issues/64) build on the same `checksumReader` design while keeping their own regression suites.
