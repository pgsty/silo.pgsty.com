---
title: "Optional Checksums, Mandatory Failure: Repairing UploadPart and UploadPartCopy Compatibility"
linkTitle: "Multipart Checksum Compatibility"
date: 2026-08-24
author: "Ruohang Feng"
summary: >
  SILO required every part in a checksum-enabled multipart upload to carry a per-part checksum. That rejected ordinary UploadPart requests that omitted an optional header and made UploadPartCopy unusable. This record covers discovery, AWS and AIStor research, rejected designs, the one-pass plaintext solution, the compatibility-baseline blocker, adversarial review, and the consistency contract for follow-up repairs.
tags: [Design, S3, Compatibility, Checksum]
weight: 30
draft: false
url: "/blog/design/uploadpart-checksum/"
---

This is the complete design and implementation record for [SILO #46](https://github.com/pgsty/silo/issues/46). The repair was not merely a changed `if` statement. One apparently optional S3 header reached into multipart completion semantics, copy responses, compression and encryption pipelines, compatibility baselines, and release verification.

> **Status:** server implementation and local verification complete; commit, PR, remote CI, release, and production verification pending.<br>
> **Owner:** [`pgsty/silo`](https://github.com/pgsty/silo), the SILO server repository.<br>
> **Tracking:** [#46](https://github.com/pgsty/silo/issues/46).<br>
> **Independent follow-ups:** [#63 CopyObject + compression checksum](https://github.com/pgsty/silo/issues/63), [#64 federated UploadPartCopy checksum](https://github.com/pgsty/silo/issues/64).<br>
> **Adversarial review:** local Claude Code, Fable 5, `--effort max`; final verdict **GO**, with no blocking findings.

## Too Long; Didn't Read (TL;DR) {#tldr}

A multipart upload splits a large file into smaller parts. A client may attach a checksum to each part so the server can verify the transfer, but AWS defines that checksum as optional. SILO used to treat it as mandatory: an ordinary `UploadPart` failed without one, and `UploadPartCopy` could never work because it has no part-body checksum to provide.

After the repair, SILO still validates a checksum when the client sends one. When the client omits it, SILO computes the checksum while reading the original bytes and saves the result. This happens before compression and encryption, requires no second read, and changes no on-disk format. The result is AWS-compatible behavior without weakening data integrity.

## Decision {#decision}

When a multipart upload declares a checksum algorithm in `CreateMultipartUpload`, SILO applies this contract:

1. If the client supplies a part checksum, the server continues to validate it. A wrong value or algorithm fails and is never hidden by fallback computation.
2. If the client omits the part checksum, the server computes it in one pass with the MPU algorithm over the logical plaintext stream, before compression and encryption, and persists the result.
3. A normal `UploadPart` echoes a checksum response header only when the client supplied the checksum. A server-computed fallback is not echoed.
4. `UploadPartCopy` has no client part-body checksum, so the server computes the value and returns it in `CopyPartResult`.
5. `ListParts` returns the persisted part checksum.
6. `FULL_OBJECT` completion continues to linearize the full checksum from stored part checksums. `COMPOSITE` completion continues to require a checksum for every part; clients can recover those values with `ListParts`.
7. Computation occurs during the existing read. Completion never re-reads the entire object merely to manufacture missing state.

In one sentence:

> The optional input is the client-provided checksum value, not the server's responsibility to maintain a consistent checksum-enabled MPU.

## How we found it {#discovery}

The defect surfaced while investigating a different multipart checksum issue, [#31](https://github.com/pgsty/silo/issues/31).

#31 concerned `CompleteMultipartUpload`: for `FULL_OBJECT`, a client can complete with part numbers, ETags, and an optional full-object checksum without retaining every part checksum in the completion XML. Tracing that path backward exposed a stronger, earlier condition in `erasureObjects.PutObjectPart`:

```go
if cs := fi.Metadata[hash.MinIOMultipartChecksum]; cs != "" {
    if r.ContentCRCType().String() != cs {
        return InvalidArgument{/* checksum missing */}
    }
}
```

Once an MPU declared a checksum algorithm, every `UploadPart` had to carry the matching `x-amz-checksum-*` value. Omitting it returned:

```text
400 InvalidArgument:
checksum missing, want "CRC32", got ""
```

API-level probes reproduced the behavior on both the single-drive and erasure backends.

Reviewing `CopyObjectPartHandler` raised the severity from a client-configuration incompatibility to P0. `UploadPartCopy` has no request body for the caller to checksum. The handler reads the source object, constructs an internal reader, and eventually enters the same `PutObjectPart` implementation. There is no client header and no SDK setting that can repair the request. Every checksum-enabled MPU therefore rejected `UploadPartCopy` by construction.

## What AWS requires {#aws-contract}

This cannot be decided by saying that MinIO has historically behaved a certain way. The S3 protocol is the authority.

The [AWS UploadPart API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html) describes each algorithm-specific checksum header as something that “can be used as a data integrity check.” More importantly, its response fields say that the checksum is present only when it was provided in the request.

The [AWS UploadPartCopy API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html) is different: when the MPU was created with an algorithm, the copy result contains that part checksum. There is no copy request body, so this is necessarily a server-computed value.

The [AWS ListParts API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html) is the standard way to recover checksums for parts in an upload that is still in progress.

The algorithm/type matrix also rules out treating the repair as one Boolean flag:

| Algorithm | `FULL_OBJECT` | `COMPOSITE` |
| --- | --- | --- |
| CRC64NVME | Supported | Unsupported |
| CRC32 / CRC32C | Supported | Supported |
| SHA1 / SHA256 | Unsupported | Supported |

`FULL_OBJECT` is limited to CRCs that can be linearized, but SHA1 and SHA256 still need correct per-part digests for `COMPOSITE` completion.

SDK configuration makes the gap practical. Current AWS SDKs usually calculate request checksums when an operation supports them, but users can choose `request_checksum_calculation = when_required`, and low-level callers can initiate an algorithm without repeating it on every part. S3 accepts those requests; SILO did not.

## Why removing the check is not a fix {#completion-invariant}

The most tempting patch is to delete the comparison and allow a checksum-less part to proceed. That only moves the failure to completion.

SILO does not reconstruct and re-read all object bytes during MPU completion. It reads `ObjectPartInfo.Checksums` from each `part.N.meta`:

- a missing entry immediately becomes `InvalidPart`;
- `FULL_OBJECT` calls `Checksum.AddPart`, combining digests with their part lengths;
- `COMPOSITE` concatenates the raw digest bytes and hashes them into the object checksum.

The actual invariant is therefore:

```text
checksum-enabled MPU
        => every committed part has a checksum for the MPU algorithm
```

Deleting the upload check without filling the metadata would make `UploadPart` appear successful, leave `ListParts` incomplete, omit the `UploadPartCopy` response value, and fail later during completion. A delayed failure is harder to diagnose than the original immediate one.

## Alternatives considered {#alternatives}

| Option | Benefit | Fatal problem | Decision |
| --- | --- | --- | --- |
| Delete the strict check | Smallest diff | Part metadata still lacks the checksum; completion must fail | Rejected |
| Relax only `FULL_OBJECT` | Unblocks some default CRC clients | Leaves `COMPOSITE` and SHA incompatible; cannot close #46 | Rejected |
| Re-read every part at completion | Avoids storing a digest during upload | Adds O(object size) second-pass I/O and still cannot fix `ListParts` or the copy response | Rejected |
| Always return the server value from normal `UploadPart` | Makes federation forwarding easy | Violates the AWS response contract | Rejected |
| Copy the AIStor implementation exactly | Commercial precedent | CRC-only fallback and a transformed-stream placement risk | Rejected |
| Compute and persist in one pass over logical plaintext | Complete protocol behavior, no second I/O, CRC and SHA support | Requires an explicit plaintext checksum reader distinct from the storage reader | Accepted |

### What the commercial edition taught us {#aistor}

We downloaded and verified the then-current MinIO AIStor `RELEASE.2026-08-07T18-34-35Z`. Without a commercial license the server enters offline mode and denies S3 operations, so the evidence came from Go pclntab and ARM64 disassembly, not a black-box compatibility run.

The static analysis showed that AIStor already:

- installs a server hasher when the client checksum is absent;
- persists the result in part metadata;
- exposes checksum fields in `CopyPartResult`.

It nevertheless applies fallback only to `CanMerge()` algorithms—CRC32, CRC32C, and CRC64NVME. SHA1/SHA256 `COMPOSITE` still follows the old `checksum missing` path. More importantly, the hasher is attached in the object layer to the current `r.Reader`; under compression or encryption that reader may already represent transformed storage bytes.

AIStor validated the general direction—compute and store—but not an implementation that SILO could copy mechanically.

## How adversarial review overturned the first design {#adversarial-review}

The first plan tried to centralize every decision inside `erasureObjects.PutObjectPart`: read the MPU metadata in the object layer and install a server hasher when the incoming reader had no client checksum. It looked attractive because all internal callers would share one rule.

The first Fable 5 Max adversarial review found that this design was wrong for compression.

`newS2CompressReader` is not a lazy wrapper. Construction immediately launches a goroutine:

```go
go func() {
    _, err := io.Copy(comp, r)
    // ...
}()
```

The S2 writer also reads several blocks concurrently. After constructing the compressor, the handler still performs option parsing, encryption preparation, and the object-layer call. By the time `PutObjectPart` installed a hasher, the plaintext reader could already have lost several MiB:

- a large part would get a checksum with a missing prefix;
- a small part could reach EOF before installation and produce no result;
- mutating `ServerSideHasher` concurrently with `Read` would be a data race.

That finding changed the responsibility split:

> The handler installs the hasher before any eager transform starts; the object layer validates the algorithm, requires a result, and persists it atomically.

This was the decisive turn in the design. Putting logic in the lowest layer may look more uniform, but stream correctness depends equally on **when bytes begin moving** and **which representation of those bytes a layer can see**.

## Final implementation {#implementation}

### A dedicated logical checksum reader {#checksum-reader}

`PutObjReader` originally distinguished two concepts:

- `Reader`, the stream sent to storage, possibly compressed or encrypted;
- `rawReader`, used by older ETag and checksum code.

Under compression, even `rawReader` may not directly see plaintext; it can merely carry an ETag through an `etag.Tagger` chain. The repair therefore did not overload it. It added an unexported field:

```go
checksumReader *hash.Reader
```

This reader always represents the logical S3 part bytes. `WithEncryption` can replace the storage `Reader`, but it must preserve `checksumReader`.

Unexported accessors on `PutObjReader` then:

- return the effective client or server checksum type;
- prefer the client value whenever it exists;
- otherwise return the server result finalized at EOF.

Keeping the mechanism unexported minimizes public Go API growth and gives [#63](https://github.com/pgsty/silo/issues/63) a shared internal path without prematurely changing ordinary `CopyObject` behavior.

### Preparing the hasher before transformations {#prepare-reader}

`prepareMultipartChecksumReader` loads the algorithm and checksum type saved with the MPU:

1. no declared algorithm means no work;
2. an existing client checksum is compared by base algorithm;
3. a wrong algorithm preserves the `InvalidArgument` rejection;
4. an omitted client checksum installs the corresponding server hasher on the plaintext reader.

For normal `UploadPart`:

- the compressed path prepares `actualReader` after request-checksum parsing but before `newS2CompressReader`;
- the uncompressed path prepares the request hash reader before the encryption reader is constructed.

For `UploadPartCopy`:

- a checksum-enabled MPU first gets an inner hash reader over the logical source range;
- a range copy hashes only the selected bytes;
- compression and destination encryption start only after that reader is ready.

### The object layer remains authoritative {#object-layer}

Early handler preparation does not replace the storage invariant. `erasureObjects.PutObjectPart` still:

- re-parses the expected MPU algorithm;
- requires an effective checksum type that matches;
- obtains the checksum map after erasure encoding finishes;
- reports an internal error instead of committing if an enabled algorithm has no result;
- writes the checksum with the ETag, sizes, and index into `part.N.meta`, then atomically renames the part.

An internal caller that bypasses the HTTP handler without preparing a valid checksum is therefore rejected just as before. It cannot silently commit a part that violates the MPU invariant.

### CopyPart response shape {#copy-response}

`CopyObjectPartResponse` gained the five algorithms supported by this source tree:

```text
ChecksumCRC32
ChecksumCRC32C
ChecksumCRC64NVME
ChecksumSHA1
ChecksumSHA256
```

All are `omitempty`, so an MPU without checksums produces the old XML. Normal `UploadPart` still uses the existing `TransferChecksumHeader` and echoes only a client request value; fallback computation does not alter that response.

## Why it works {#why-it-works}

After the repair, the data flow is:

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

This satisfies four requirements that previously appeared to conflict:

1. **Protocol compatibility:** omitting an optional header succeeds.
2. **No integrity downgrade:** a supplied client value is still checked end to end and is never hidden by server fallback.
3. **Correct object semantics:** the checksum covers logical S3 bytes, not compressed data or ciphertext.
4. **Controlled cost:** hashing shares the existing read and adds CPU, not a second disk or network pass.

EOF has a precise role. `hash.Reader` finalizes `ServerSideChecksumResult` only when it reaches EOF. Closing the compression pipe synchronizes the compressor goroutine with the storage read; the object layer reads the result only after encoding returns. Targeted `-race` tests verified that concurrency boundary.

## The compatibility-baseline blocker {#compat-baseline}

The five new `CopyObjectPartResponse` fields are exported Go API. SILO's `buildscripts/rebrand-guard` rescans imports, environment variables, headers, routes, storage markers, and exported symbols, then compares them in both directions with `buildscripts/rebrand-guard/compat-baseline.json`. An unacknowledged symbol makes CI fail.

After recording the five #46 fields, the guard still reported two additions:

```text
internal/config/notify:notify:type:LegacyDatabaseTargetError
internal/config/notify:notify:method:LegacyDatabaseTargetError.Error
```

They did not come from #46. They belong to the earlier database-notification repair `f1ba68358` on the local `main` branch. The `cmd` startup path intentionally needs the exported type for `errors.As`, but that earlier commit had not updated the compatibility baseline. Every later change based on that HEAD would therefore fail the CI guard.

We chose “option A”: acknowledge the two notification symbols as part of their original repair while retaining the five #46 fields. The final baseline diff is exactly seven additions and zero deletions, and the guard reports:

```text
exported=9021
Silo rebrand compatibility baseline is unchanged
```

This does not disable the check. Exact set equality means that acknowledging a nonexistent symbol also fails. The change explicitly records two intentional compatibility-surface additions.

`golangci-lint` has not yet run locally; it remains a remote `go.yml` gate. Green local `go test`, `go vet`, race, and rebrand-guard results do not substitute for green remote CI.

## Verification evidence {#verification}

The new tests execute 76 subtests across:

- CRC32, CRC32C, and CRC64NVME `FULL_OBJECT`;
- CRC32, SHA1, and SHA256 `COMPOSITE`;
- correct client checksums, wrong algorithms, and wrong values;
- absence of a server-computed checksum in normal `UploadPart` responses;
- server values in `UploadPartCopy` responses and `ListParts`;
- a real 5 MiB + 1 KiB two-part full-object merge;
- zero-length parts and overwriting the same part number;
- a range copy whose SHA256 covers only the copied interval;
- single-drive and 16-drive erasure backends;
- default, versioned, compressed, encrypted, and compressed-plus-encrypted modes;
- explicit SSE-C and SSE-S3.

Local validation included:

```text
go test -race ./cmd -run '^TestAPIUploadPartServerSideChecksum' -count=1
go test ./cmd -count=1
go test ./... -count=1
go vet ./cmd
git diff --check
go run ./buildscripts/rebrand-guard
```

All passed. Two subsequent Claude Code Fable 5 Max implementation reviews and the final acceptance review returned **GO** with no blocking findings.

## Cost, risk, and release boundary {#tradeoffs}

When a client omits its value, the server performs one additional hash over the part. CRC cost is small; SHA costs more CPU. Both share the read that already had to occur, without buffering an entire part in memory or adding a completion-time second pass.

During a rolling upgrade, old and new nodes may answer the same checksum-less request differently: a new node accepts it while an old node returns 400. `ObjectPartInfo.Checksums` did not change format, so stored data remains downgrade-readable, but client-visible behavior stabilizes only after all serving nodes have upgraded. The release note must call that out.

This record describes a local `main` worktree. The implementation has not been committed, pushed, run through remote CI, or packaged into a release. SILO documentation belongs to `silo.pgsty.com`; a successful local Hugo build does not mean that the product in the wider [pgsty.com](https://pgsty.com) ecosystem has shipped.

## Why two follow-ups remain separate {#follow-ups}

Adversarial review found two related but independent issues.

### #63: CopyObject + compression {#follow-up-copy}

Ordinary `CopyObject` can also attach a server-side checksum to a transformed stream. It shares the root cause and the new `checksumReader` mechanism, but it is a different API with a different test matrix and rollback boundary. We chose a separate repair and require that PR to reuse this plaintext-reader contract instead of inventing a second abstraction.

### #64: legacy federation {#follow-up-federation}

Legacy etcd federation turns `UploadPartCopy` into an ordinary remote `UploadPart`. Under the AWS response semantics preserved here, that remote request does not return a server fallback value, so the proxy may still lack the checksum required for `CopyPartResult`. A follow-up must independently choose between a remote-returned value and an ETag-verified `ListParts` fallback. It must not make all external `UploadPart` responses non-compliant merely to simplify an internal proxy.

Separating them does not abandon consistency. Consistency is maintained through one shared rule:

> Every server-computed S3 checksum binds to the logical plaintext stream, is installed before any eager transform, and is validated and persisted by the object layer that owns the storage invariant.

## Lessons retained {#lessons}

The repair leaves lessons more durable than its individual lines of code:

1. **An optional header does not make internal state optional.** If the protocol lets the client omit a value, the server must produce the state its own completion path needs.
2. **Request acceptance and response disclosure are separate contracts.** A normal UploadPart may compute internally and still omit the value; UploadPartCopy must return it.
3. **Stream layers are defined by byte semantics.** The lowest layer is not automatically correct if it no longer sees logical bytes, and an eager goroutine turns “install later” into a race.
4. **A commercial implementation is evidence, not the specification.** AIStor showed the direction and the boundary that could not be copied.
5. **A compatibility guard is a change-acknowledgment mechanism.** `compat-baseline.json` exists to assign every new compatibility surface, not merely to make CI quiet.
6. **Independent defects should ship independently while sharing invariants.** #63 and #64 remain separate, but both must cite and obey the checksum-reader contract established here.

The final result is not a broad relaxation. It is a stricter and more accurate boundary: clients may omit optional information; the server may not omit correctness.
