---
title: "CopyObject Checksums Must Cover Logical Object Bytes"
date: 2026-08-24
lastmod: 2026-08-24
author: "Ruohang Feng"
summary: >
  Destination compression made it possible for SILO to persist a checksum of the S2 storage stream instead of the logical CopyObject result. This design record reconstructs the failure, compares the rejected fixes, defines the plaintext-reader invariant, proves why the selected solution works, and records rollout and remediation boundaries.
tags: [Design, S3, Compatibility, Checksum]
weight: 10
draft: false
url: "/blog/design/copyobject-checksum/"
---

This is the final design and verification record for [SILO issue #63](https://github.com/pgsty/silo/issues/63).

**Decision:** compute every server-generated CopyObject checksum over the logical destination object before compression or encryption, retain that reader separately from the storage reader, and refuse to publish the object if the expected checksum is unavailable at EOF.<br>
**Implementation:** [PR #66](https://github.com/pgsty/silo/pull/66), merged as commit <code>c0e715977</code>.<br>
**Related repairs:** transform-state preservation [#67](https://github.com/pgsty/silo/issues/67) / [PR #69](https://github.com/pgsty/silo/pull/69), and CopyObjectResult checksum fields [#68](https://github.com/pgsty/silo/issues/68) / [PR #70](https://github.com/pgsty/silo/pull/70).<br>
**Upstream client:** [minio-go PR #2295](https://github.com/minio/minio-go/pull/2295).<br>
**Release boundary:** these changes are merged into source, but no statement on this page implies that a particular release tag, RPM, DEB, APK, archive, or container image already contains them.

## Decision in one sentence {#decision}

A checksum is not merely a digest produced somewhere along the write path. It is a function of a precisely defined byte sequence. For S3 CopyObject, that sequence is the logical object returned to a client, not SILO's compressed or encrypted representation of that object.

The accepted pipeline is therefore:

~~~text
logical source bytes
    -> server-side S3 checksum
    -> optional S2 compression
    -> storage-stream hash and ETag delegation
    -> optional server-side encryption
    -> erasure coding
    -> EOF checksum validation
    -> atomic data and metadata commit
~~~

Everything else in this design follows from preserving that ordering.

## Background: one object, several integrity domains {#background}

SILO handles several values that are all casually called a checksum, but they protect different contracts.

| Value | Byte domain | Purpose |
| --- | --- | --- |
| Additional S3 checksum | Logical object bytes | Client-visible end-to-end integrity through HEAD, GET, attributes, and copy responses |
| ETag | Logical content in the ordinary single-part, unencrypted-compatible case; otherwise protocol-specific | Object identity and conditional request compatibility |
| Storage reader accounting | Compressed or encrypted write stream | Carry size, stream, and ETag delegation through the write path |
| Erasure bitrot checksum | Stored erasure shards | Detect corruption of SILO's physical representation |
| Encryption authentication | Ciphertext framing and keys | Detect tampering and authenticate encrypted storage |
| Compression index | S2 storage stream offsets | Support efficient reads of large compressed objects |

These values may be computed during one streaming write, but they are not interchangeable. In particular, a storage-stream checksum can be perfectly valid while being completely wrong as an S3 object checksum.

Amazon S3 documents that CopyObject produces a destination checksum and that a multipart source copied in one operation becomes a full-object checksum. The algorithm may be selected by the request, inherited from the source, or defaulted when the source has no checksum. The result describes the copied object, not a provider's private storage encoding.

## How #46 exposed #63 {#discovery}

The bug was found while repairing multipart checksum compatibility in [#46](https://github.com/pgsty/silo/issues/46).

That work established three internal rules for UploadPart and UploadPartCopy:

1. Keep a dedicated reader for logical plaintext checksum calculation.
2. Install a server fallback hasher in the handler, before compression or encryption can consume the stream.
3. Let the object layer validate and persist the completed result, rather than deciding the byte domain there.

The resulting private field, <code>checksumReader</code>, deliberately remained separate from the active <code>Reader</code> and the historical <code>rawReader</code>. <code>WithEncryption</code> may replace the active storage reader, but must not replace the logical checksum reader.

Reviewing ordinary CopyObject after #46 showed the same conceptual hazard in a different handler. The code created <code>newS2CompressReader</code>, wrapped its output as <code>srcInfo.Reader</code>, and only later called <code>AddServerSideChecksumHasher</code> on that reader. At that point the name <code>srcInfo.Reader</code> concealed an important fact: it represented the storage stream, not necessarily the S3 object stream.

#46 intentionally did not change CopyObject. Keeping #63 separate meant that the P0 multipart repair could be reviewed, released, or rolled back without bundling another API and another test matrix.

## Failure model {#failure-model}

### The old ordering

The relevant old flow was:

~~~text
GetObject logical reader
    -> start S2 compressor goroutine
    -> wrap compressed output in hash.Reader
    -> later choose destination checksum algorithm
    -> attach server-side hasher to compressed hash.Reader
    -> persist that result as the object's S3 checksum
~~~

The checksum did not cover missing or corrupt data from the storage writer's point of view. It covered the wrong, complete stream.

### Static hypothesis versus dynamic result

The original issue described two possible failures:

- the hasher could cover compressed data;
- the compression goroutine could consume logical input before the hasher was attached, causing a prefix to be missed.

The API reproduction confirmed the first and did not confirm the second. The hasher was attached to the compressor's output reader, so it observed the complete transformed stream from that reader's beginning. Bytes consumed on the compressor's input side were not bytes consumed from the output-side hash reader.

This distinction matters. The root cause is not an intermittent race that merely needs a lock. It is a deterministic data-domain error.

### Concrete reproduction

For the permanent test payload, the unfixed tree stored:

~~~text
CRC32 of S2 storage bytes: hN7ytg==
CRC32 of logical bytes:    1WxbLg==
~~~

The stored value was a legitimate CRC32, which is why ordinary metadata validation did not catch it. Only an independent checksum of the downloaded logical object exposed the mismatch.

CRC32, CRC32C, CRC64NVME, SHA1, and SHA256 all failed for compressed destinations. When compression and destination encryption were combined, S2 used randomized padding for the encrypted stream. The checksum was then not only wrong but nondeterministic across identical logical copies.

## Requirements and non-goals {#requirements}

The repair had to satisfy all of the following:

1. **Correct byte domain.** Server-generated checksums cover exactly the logical destination bytes.
2. **Single pass.** CopyObject must remain streaming; no second object read.
3. **Transformation independence.** Compression and encryption cannot change the logical checksum.
4. **Client compatibility.** Existing client-supplied checksum validation and algorithm selection remain unchanged.
5. **Multipart-source correctness.** A composite checksum from a multipart source is recomputed as a full-object checksum for the single-operation destination.
6. **Default behavior.** A source without a checksum still gives the destination the configured S3-compatible default, CRC64NVME in this baseline.
7. **ETag preservation.** Moving the checksum reader cannot silently change the CopyObject ETag contract.
8. **Fail closed.** If an internal caller asks for a server checksum but fails to produce it, SILO must not return success with missing integrity metadata.
9. **Format compatibility.** Persist results in the existing checksum metadata representation.
10. **Small rollback boundary.** Do not mix response-schema, federation, or metadata-only transform bugs into the core placement fix.

The following were explicit non-goals for #63:

- adding new checksum algorithms;
- changing the on-disk checksum encoding;
- scanning or backfilling old objects;
- fixing legacy federated UploadPartCopy;
- adding CopyObjectResult XML fields;
- changing MCLI or Console behavior.

## Alternatives considered {#alternatives}

| Option | Attraction | Why it was rejected |
| --- | --- | --- |
| Attach the hasher in the object layer | One centralized fallback for every caller | The object layer receives a storage-oriented reader after handler transformations. It cannot reliably reconstruct the logical byte domain, and attachment may be too late |
| Hash the S2 output | Minimal code movement | This is the demonstrated bug: it protects storage bytes, not S3 object bytes |
| Hash ciphertext | Convenient after encryption setup | Encryption IVs, framing, and authentication make the value provider-specific and often nondeterministic |
| Read the completed object a second time | Easy to reason about | Doubles I/O, breaks the single-pass streaming goal, delays responses, and is expensive for large or tiered objects |
| Buffer the whole object before transforming it | Simple sequencing | CopyObject supports large objects; whole-object buffering creates unacceptable memory and latency costs |
| Always copy the source checksum value | Avoids computation | Fails when the request selects another algorithm, when the source has no checksum, and when a multipart composite source must become a full-object checksum |
| Add a second CopyObject-only checksum abstraction | Keeps code local | Duplicates the invariant already created by #46 and gives future paths two subtly different contracts |
| Reuse the logical checksumReader before transformations | One streaming pass, existing metadata format, common invariant | Selected |

The selected option is not simply the one with the fewest changed lines. It is the smallest option that makes the byte-domain contract explicit and reusable.

## Final design {#design}

### 1. Construct the logical reader first

CopyObject obtains a source <code>GetObjectReader</code> that already yields the logical source object: stored compression has been decoded and source encryption has been removed using the authorized source options.

SILO wraps that stream in a logical <code>hash.Reader</code> with the known actual object size. For compressed destinations this also tightens the old unlimited length into a hard logical-size bound before compression.

At this point no compression goroutine has started.

### 2. Choose the destination checksum policy

The existing policy remains intact:

1. If the request supplies <code>x-amz-checksum-algorithm</code>, compute that base algorithm.
2. Otherwise inspect the source checksum.
3. A source full-object checksum can be retained because the logical bytes are unchanged.
4. A source multipart composite checksum must be recomputed with its base algorithm because CopyObject creates a single-operation full object.
5. A source without checksum metadata receives the default CRC64NVME checksum.

Only branches that require computation call <code>AddServerSideChecksumHasher</code>.

### 3. Start compression after hasher installation

For a compressed destination, the logical reader is captured as <code>checksumReader</code> and passed as the input to <code>newS2CompressReader</code>. The compressor therefore cannot obtain one byte without that byte first passing through the logical hasher.

The compressed output receives its own storage <code>hash.Reader</code>. A new <code>PutObjReader</code> is built around that storage reader, then <code>setChecksumReader</code> restores the logical reader reference.

~~~text
PutObjReader.Reader          = compressed or encrypted storage stream
PutObjReader.rawReader       = stream used for the historical ETag path
PutObjReader.checksumReader  = logical plaintext stream
~~~

No exported method or new package-level abstraction is required.

### 4. Preserve the separation through encryption

Destination encryption wraps the compressed storage reader and may replace <code>PutObjReader.Reader</code> through <code>WithEncryption</code>. It does not modify <code>checksumReader</code>.

The destination checksum is therefore identical for:

- plaintext storage;
- compressed storage;
- encrypted storage;
- compressed and encrypted storage.

If checksum metadata itself must be protected, the existing metadata encryption function encrypts the serialized checksum after calculation. That protects metadata at rest without changing what bytes were hashed.

### 5. Finalize at EOF and fail closed

The internal hash reader sets <code>ServerSideChecksumResult</code> only after its source returns EOF. In the compressed path, <code>io.Copy</code> drains the logical checksum reader before the compressor closes the pipe. The object writer cannot observe the compressed stream's EOF before the logical reader has finalized its checksum.

The object layer then validates:

- the result is present;
- the result is structurally valid;
- its base algorithm matches <code>WantServerSideChecksumType</code>.

Failure logs an internal invariant violation and aborts the write. Deferred erasure cleanup removes temporary shards before unique metadata is published. Returning HTTP 200 without a requested or default checksum would be a silent correctness failure and is therefore not an acceptable fallback.

### 6. Persist without a format change

The validated checksum is appended to the same <code>FileInfo.Checksum</code> representation already used by existing objects. Encrypted destinations reuse the existing metadata encrypter. HEAD, GET, GetObjectAttributes, replication metadata, and later readers continue to consume the same representation.

## Why the design is correct {#proof}

### Byte-domain proof

Every byte accepted by the compressor is read from <code>checksumReader</code>. The hasher is installed before the compressor is constructed. Therefore the digest input is exactly the compressor's logical input, not its output.

### Completeness proof

The compressor closes its output only after draining the logical input and closing the S2 writer. The object writer must read that output to EOF before completing the write. The checksum result is finalized on the logical input EOF, which precedes the observable storage EOF.

This creates a natural happens-before relationship through the pipe; no separate mutex or out-of-band signal is necessary. Targeted race tests and repeated shuffled executions confirm the implementation.

### ETag proof

The compressed reader is wrapped with the logical reader as its ETag delegate. Moving the S3 checksum hasher does not move ETag calculation onto S2 bytes. Permanent tests independently compare the final ETag with the logical object's MD5 in the compatible plaintext cases.

### Storage-integrity proof

The storage-side reader remains after compression for physical stream accounting and ETag delegation, while the erasure layer still writes its own bitrot protection for stored shards. Neither mechanism is replaced by the S3 logical checksum, and the S3 checksum is not presented as shard integrity.

### Encryption proof

The encryption reader consumes the storage stream after logical checksum calculation. Random encryption or padding cannot influence the checksum. SSE-C and SSE-S3 tests cover encrypted-only and compressed-plus-encrypted destinations, and an encrypted source verifies that source decryption also precedes hashing.

### Compatibility proof

For an uncompressed, unencrypted destination, <code>NewPutObjReader</code> initializes <code>checksumReader</code> and <code>rawReader</code> to the same reader, so the accessor change is behaviorally neutral.

The patch introduced no new server API and no new storage marker. The production portion was limited to three files and about 30 additions / 15 deletions. The larger test file reflects the compatibility matrix, not runtime complexity.

## Adversarial findings kept in separate fixes {#adjacent}

The review intentionally tried to break the solution around its boundaries. It found two real inherited defects, both independent of the checksum placement.

### Metadata-only transform state: #67

CopyObject derived destination compression metadata from current configuration before it knew whether object bytes would be rewritten. A metadata/reference-only self-copy could therefore add a compression marker to uncompressed data or remove the marker from compressed data.

Versioned copies exposed a deeper edge: an unresolved source VersionID could make a metadata-only operation fall through to <code>PutObject</code>. Versioned SSE-C key rotation then wrote plaintext while preserving encryption metadata, producing <code>sio: unsupported version</code>.

[PR #69](https://github.com/pgsty/silo/pull/69) fixed this separately by:

- preserving source transform metadata for metadata/reference-only updates;
- changing compression markers only when bytes are actually rewritten;
- passing the resolved source version into versioned reference copies.

Keeping this separate preserved #63's rollback boundary and prevented an apparently simple three-line guard from hiding the versioned corruption case.

### CopyObjectResult checksum response: #68

After #63, the object stored and returned the correct checksum through HEAD and GET, but the successful CopyObject XML still contained only LastModified and ETag.

[PR #70](https://github.com/pgsty/silo/pull/70) added the five checksum fields supported by this server plus ChecksumType, populated them from the committed destination ObjectInfo, and registered the exported fields in the compatibility baseline.

Active minio-go already had checksum fields on UploadInfo but discarded CopyObjectResult values. [Upstream PR #2295](https://github.com/minio/minio-go/pull/2295) connects those existing fields without adding public API.

## Verification evidence {#verification}

The permanent suite covers:

- CRC32, CRC32C, CRC64NVME, SHA1, and SHA256;
- explicit algorithms and default CRC64NVME;
- plain, compressed, encrypted-only, and compressed-plus-encrypted destinations;
- SSE-C and SSE-S3;
- encrypted and compressed sources;
- unversioned and versioned buckets;
- source full-object checksum preservation;
- multipart composite source conversion to a full-object checksum;
- in-place self-copy;
- empty data, exactly 4096 bytes, and 4097 bytes;
- the S2 compression-index path above 8 MiB;
- logical ETag and byte-for-byte body round trip;
- HEAD and GET with checksum mode enabled;
- missing and mismatched internal checksum results;
- absence of a published object after invariant failure.

Validation gates included:

~~~text
focused API tests
focused race tests
10 shuffled race iterations with GOMAXPROCS=8
full go test ./cmd
CGO-disabled kqueue,dev cmd tests
go vet
golangci-lint
compatibility and rebrand guards
cross compilation
vulnerability analysis
release-pipeline snapshot, SBOM, provenance, package, and image validation
~~~

The regression is red on the unfixed baseline and green on the repaired tree.

## Operational and rollout considerations {#operations}

### Mixed server versions

The metadata representation is unchanged, so an older node can read an object written with the corrected checksum. However, behavior during a rolling upgrade is request-node dependent: a CopyObject handled by an old node can still write the wrong value while a new node writes the correct value.

Upgrade all API-serving nodes before treating CopyObject checksum behavior as stable. A successful local build or one upgraded node is not sufficient release evidence.

### Existing objects

The fix affects future copies. SILO does not automatically scan or rewrite historical checksum metadata because doing so would read and rewrite user data outside an explicit S3 operation.

An object is a candidate for verification when:

- it was created by CopyObject on an affected server;
- destination compression matched its key or content type;
- it carries an additional S3 checksum.

Retrieve the checksum with checksum mode enabled, download the logical object, independently compute the named algorithm, and compare the Base64 value.

For remediation, prefer copying to a new key with an explicit destination checksum algorithm and verifying the result before replacing the original. An in-place copy with <code>x-amz-metadata-directive: REPLACE</code> also rewrites the object, but replaces the current value in an unversioned bucket and creates a new version in a versioned bucket. Review retention, legal hold, tags, user metadata, encryption keys, capacity, replication, and rollback requirements before a bulk rewrite.

### Release versus merge

The server fixes and this design record are merged and the document is deployed. That does not identify the first released binary containing the changes. Release notes must name the eventual tag and independently verify archives, packages, container manifests, checksums, signatures, SBOMs, and provenance.

## Cross-repository impact {#cross-repo}

| Repository | Decision |
| --- | --- |
| pgsty/silo | Owns the handler, reader chain, object-layer invariant, response schema, and tests |
| minio/minio | Archived upstream retains the original defect; no normal upstream server PR is possible |
| minio/minio-go | PR #2295 returns CopyObject checksum fields through existing UploadInfo fields; maintainer merge pending |
| pgsty/silo-pkg | No change: it does not own ObjectInfo, PutObjReader, or CopyObjectHandler |
| pgsty/mc | No change: requesting --checksum deliberately disables server-side copy and uses download/upload |
| pgsty/silo-console | No direct change: it passes CopyObject through minio-go and does not interpret the checksum result |
| silo.pgsty.com | Owns this bilingual design, release boundary, and historical-object guidance |

Legacy federated UploadPartCopy checksum recovery remains [issue #64](https://github.com/pgsty/silo/issues/64). It is a different API, response contract, and deployment topology and must not be presented as solved by this work.

## Final outcome {#outcome}

The repair is small because it does not invent a new checksum system. It makes an existing distinction explicit:

~~~text
S3 checksum reader = logical object contract
storage reader     = physical representation contract
~~~

Once those responsibilities are separated, compression, encryption, ETag, erasure coding, and metadata persistence can remain streaming and independently testable. That is why the solution fixes the demonstrated bug without trading it for extra I/O, unbounded buffering, a new disk format, or a second internal abstraction.
