---
title: "ListMultipartUploads Behavior and Design Trade-Offs"
linkTitle: "ListMultipartUploads"
date: 2026-08-30
weight: 20
description: "Why public ListMultipartUploads returned to MinIO-compatible behavior in Server 20261018, what on-disk scanning cost on 16-drive erasure sets, and which multipart repairs were kept."
url: "/blog/design/list-multipart-uploads/"
---

This note documents the `ListMultipartUploads` design across its full engineering lifecycle: the current MinIO-compatible contract in Server `20261018`, the October 18 partial rollback after 16-drive erasure-set capacity testing, the October 17 on-disk scan experiment (`#243`, merged as [`7e9454456`](https://github.com/pgsty/silo/commit/7e9454456ee7065cd1d782fc4498338324a94894)), the September 16 opt-in `strict` mode (`#198`), and the original August 30 root-cause analysis.

## Current Contract in Server 20261018 {#implementation}

Server `20261018` restores the traditional MinIO-compatible public `ListMultipartUploads` contract on `main` (commit [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423), followed by empty-upload-parent cleanup repair [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c)):

- Without `prefix`, `ListMultipartUploads` returns uploads currently tracked in the node-local in-memory multipart cache.
- With a non-empty `prefix`, `ListMultipartUploads` treats `prefix` as an exact object key (`sha256(bucket/object)`) and checks the multipart directory for that object on disk.
- `delimiter`, `key-marker`, `upload-id-marker`, and `encoding-type` are parsed by the handler, validated where required (`encoding-type=url`), and echoed in the XML response, while candidate selection follows the MinIO-compatible cache / exact-key path rather than a full `.minio.sys/multipart` disk scan.
- `UploadID`, `GetMultipartInfo`, `PutObjectPart`, `ListObjectParts`, `CompleteMultipartUpload`, and `AbortMultipartUpload` continue to work by `Bucket + Object + UploadID` across restarts because active uploads live on disk under `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>`.
- `MINIO_API_MULTIPART_LISTING` and `api multipart_listing` remain accepted as compatibility no-ops if present in older scripts or stored configs.
- `GET /minio/admin/v3/multipart-preflight` remains available and reports `mode: "legacy"` with `0` incompatible uploads.

## Why the Default Disk Scan Was Rolled Back on 2026-10-18 {#decision-20261018}

Between `2026-10-17` (`#243`, commit [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6)) and `2026-10-18` (commit [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423)), `main` briefly used an unindexed `.minio.sys/multipart` disk scan for all public `ListMultipartUploads` calls. Capacity analysis and benchmarks on 16-drive erasure sets showed that making this scan the unconditional default created a worse operational failure mode than the listing limitation it replaced.

### Why Restart Never Deleted Multipart Uploads

Active multipart uploads are stored on disk under `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta` and `part.*`. A server restart clears only the in-memory `multipartUploadsCache`; it does **not** remove unfinished uploads from disk. Retained `UploadID` values therefore remain usable across restarts until completed, explicitly aborted, or cleaned up by the background stale-upload sweep (default expiry: 7 days; check interval: 12 hours).

Because unfinished uploads accumulate across restarts and client retries, any operation that walks `.minio.sys/multipart` on disk scales with the total number of unfinished uploads currently stored in the erasure set, not merely the uploads created since the last process start.

### How the 100,000-Entry Guard Fails on a 16-Drive Erasure Set

The October 17 disk scan enforced `maxMultipartWalkEntries = 100000` across **all drives in an erasure set combined**, counting both `<sha256(bucket/object)>` directories and `<uploadID>` directories on every drive.

On an `N`-drive erasure set with `U` active uploads across `H` distinct keys, a single bucket-wide `ListMultipartUploads` call traverses:

$$\text{entries} = N \times (H + U)$$

When each upload uses a distinct object key ($H = U$):

- On a **4-drive** set, $4 \times (10{,}000 + 10{,}000) = 80{,}000$ directory entries—just under the `100,000` budget.
- On a **16-drive** set, $16 \times (3{,}126 + 3{,}126) = 100{,}032$ directory entries—exceeding the `100,000` budget at **3,126 active uploads** across the entire erasure set (all buckets combined) and failing every public scan with HTTP `503 SlowDown`.
- Even when all uploads share a **single object key** ($H = 1$), a 16-drive set reaches $16 \times (1 + 6{,}250) = 100{,}016$ entries at **6,250 uploads** for that key, so even an exact-key lookup (`prefix=<exact-object-key>`) failed with `503 SlowDown`.

### Provenance and Responsibility

| Change | Date / Commit | What It Did | Assessment |
| :--- | :--- | :--- | :--- |
| Initial `strict` mode (`#198`) | `2026-09-16` / [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc) | Added opt-in disk-backed listing behind `MINIO_API_MULTIPART_LISTING=strict`, keeping `legacy` as default | Safe opt-in boundary, but lacked a hard traversal cap |
| Security hardening (`SN-2026-009`..`012`) | `2026-09-16` / [`143f6970d`](https://github.com/pgsty/silo/commit/143f6970d) | Added `checkUploadID`, `maxMultipartWalkEntries = 100000`, `503 SlowDown` mapping, and `readQuorum` filtering | Essential DoS protection for the disk scan, but counted raw per-drive directory entries across all `N` drives |
| Unconditional unification (`#243`) | `2026-10-17` / [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6) | Removed `legacy` and made the disk scan unconditional for all public `ListMultipartUploads` calls | **Overreach**: turned a 4-drive benchmark result into a mandatory path that fails at 3,126 uploads on 16-drive sets |

### Partial Rollback Trade-Off Analysis

| Option | Public S3 Listing Fidelity | 16-Drive Capacity Behavior | Storage Format / Background I/O Impact | Decision |
| :--- | :--- | :--- | :--- | :--- |
| Keep `#243` unconditional disk scan | Full prefix/delimiter/marker listing up to 3,125 uploads on 16 drives | Fails with `503 SlowDown` at 3,126 distinct-key uploads across the set | `16 × (1 + H)` `ListDir` RPCs per uncached public listing | **Rejected** |
| Raise or remove `maxMultipartWalkEntries` | Works past 3,126 uploads | Reopens unbounded O($N \times U$) disk walk and memory allocation on unindexed `.minio.sys/multipart` | High latency and FD/RPC amplification under concurrent `GET /bucket?uploads` | **Rejected** |
| Build a persistent per-bucket multipart index | Full S3 listing without `sha256(bucket/object)` full scan | Scales with matching prefix | Requires a new distributed metadata index, heal protocol, and crash-recovery contract | **Deferred** (requires dedicated index design) |
| Full `git revert` of `#198`, `143f6970d`, and `#243` | Restores MinIO-compatible listing | No `100,000`-entry cliff | Would also discard `checkUploadID` path-traversal protection, abort cache/peer cleanup, and `xl.meta` identity metadata | **Rejected** |
| **Surgical partial rollback (`4733e1423` + `0f9199e0c`)** | Restores MinIO-compatible public listing (empty-prefix cache + non-empty exact-key lookup) | No cross-bucket `100,000`-entry cliff; exact-key lookup touches only `1` hash directory per drive | Preserves `xl.meta` identity fields, `checkUploadID`, abort cleanup, and empty-hash-parent removal | **Selected** |

### What Was Retained vs Rolled Back

1. **Rolled back on the public listing path (`4733e1423`)**:
   - Public `ListMultipartUploads` no longer walks every `<sha256(bucket/object)>` directory in `.minio.sys/multipart`.
   - Empty `prefix` reads the in-memory `multipartUploadsCache`; non-empty `prefix` hashes `bucket/prefix` directly and inspects only that single object's `<sha256(bucket/object)>` directory.
2. **Retained hardening and storage repairs (`4733e1423` + `0f9199e0c`)**:
   - `NewMultipartUpload` still writes `x-minio-internal-multipart-v1-bucket` and `x-minio-internal-multipart-v1-object` in `xl.meta`, keeping on-disk uploads self-describing for diagnostics and future indexed designs.
   - `checkUploadID` validation remains enforced on multipart operations (`SN-2026-009`).
   - `AbortMultipartUpload` still evicts the local cache entry and notifies peer nodes.
   - `cleanupStaleUploads` continues to remove expired uploads on disk, and commit [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) ensures that when the last `<uploadID>` under `.minio.sys/multipart/<sha256(bucket/object)>` is removed by expiry sweep, completion, or abort, the empty `<sha256(bucket/object)>` parent directory is also removed so empty hash directories do not accumulate indefinitely.

### Cost of Ordering vs Discovery

In `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>`, directory names are SHA-256 hashes of `bucket/object`, which destroys lexicographical key order and bucket boundaries. Answering an arbitrary prefix query (`prefix=trips/`) in S3 key order without an index requires reading `xl.meta` inside every active upload across every bucket in the erasure set before sorting and paginating the first page. By contrast, exact-key lookup (`prefix=trips/2026/a.mp4`) computes a single SHA-256 hash and lists only that one directory per drive (`O(N)` `ListDir` calls instead of `O(N × H)`).

### Validation Benchmarks on Commit `4733e1423` {#rollback-validation}

Measured with `go test -run=^$ -bench=BenchmarkMultipartPublicListingCapacity -benchmem -benchtime=1x ./cmd`:

| Scenario (`BenchmarkMultipartPublicListingCapacity`) | Before (`4ed86dfe6` Disk Scan) | After (`4733e1423` MinIO-Compatible Path) | Latency (`4733e1423`) | Memory / Allocs (`4733e1423`) |
| :--- | :--- | :--- | :--- | :--- |
| `4_drives_10000_distinct_keys/empty_prefix_cached` | `200 OK` (walked 80,000 entries on disk) | `200 OK` (1,000 uploads returned from cache) | `1.12 ms` | `257,104 B` / `14` allocs |
| `16_drives_3126_distinct_keys/empty_prefix_cached` | **`503 SlowDown`** (100,032 entries > 100,000 cap) | `200 OK` (1,000 uploads returned from cache) | `0.36 ms` | `90,208 B` / `14` allocs |
| `16_drives_3126_distinct_keys/exact_key_after_cache_clear` | **`503 SlowDown`** (walked all 3,126 hash dirs) | `200 OK` (1 upload returned from disk after cache clear) | `0.78 ms` | `30,024 B` / `389` allocs |
| `16_drives_10000_uploads_one_key/exact_key_lookup` | **`503 SlowDown`** (at 6,250 uploads for one key) | `200 OK` (1,000 uploads returned from disk) | `383.85 ms` | `13,721,672 B` / `236,704` allocs |

### Related Records {#related-records}

| Document | Scope |
| :--- | :--- |
| [S3 API Compatibility — Differences from S3 APIs for Multipart Uploads](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads) | Canonical user-facing compatibility reference for `ListMultipartUploads` in Server `20261018` |
| [SILO 20260916 Release Notes](/blog/release/silo-20260916/) | Published legacy default, opt-in strict behavior, UploadID validation, and cancellation boundaries |

---

## Historical Record: The October 17 Unification Attempt (`#243`) {#implementation-20261017}

On `2026-10-17`, PR `#243` (commit [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6)) briefly removed the `legacy`/`strict` mode switch and routed all `ListMultipartUploads` requests through the disk-backed implementation introduced in `#198`. Although rolled back the next day by `4733e1423`, the architectural analysis from `#243` is preserved below because it documents the exact storage format, quorum rules, and abort-race edge cases of `.minio.sys/multipart`.

## October 17 Architectural Decision Record {#decision-20261017}

### Target Contract of the October 17 Experiment {#decision-contract}

The October 17 experiment attempted to enforce the following invariants on `ListMultipartUploads` without introducing a separate metadata database:

1. **Restart durability**: `ListMultipartUploads` reads active uploads from `.minio.sys/multipart` on disk rather than relying exclusively on `multipartUploadsCache`.
2. **S3 filter and pagination semantics**: `prefix` is matched as a string prefix of the object key, `delimiter` collapses common prefixes into `CommonPrefixes`, and results are ordered by `(Key, Initiated, UploadID)` with `key-marker` and `upload-id-marker` pagination.
3. **Self-describing upload metadata**: `NewMultipartUpload` stores the bucket and object name inside each upload's `xl.meta` so on-disk uploads can be mapped back to `(Bucket, Object)` despite the `<sha256(bucket/object)>` directory layout.

### Why Unification Was Attempted {#decision-background}

Before `#198`, callers saw very different results depending on whether `prefix` was empty, a partial key prefix, or a full object key:

| Request Example | Traditional MinIO / `legacy` Behavior | S3 Standard / Disk-Scan Behavior |
| :--- | :--- | :--- |
| `GET /photos?uploads` (immediately after `CreateMultipartUpload`) | Returns uploads present in the local node's in-memory cache | Returns active uploads present at read quorum on disk |
| `GET /photos?uploads` (after server restart) | Returns empty list (`multipartUploadsCache` was cleared on restart) | Still returns active unfinished uploads from `.minio.sys/multipart` |
| `GET /photos?uploads&prefix=2026/` (directory prefix) | Returns empty list unless an object is literally named `2026/` (`sha256("photos/2026/")`) | Returns all active uploads whose key starts with `2026/` |
| `GET /photos?uploads&prefix=2026/trip.mov` (exact object key) | Looks up `.minio.sys/multipart/<sha256("photos/2026/trip.mov")>` on disk (survives restart) | Returns uploads whose key starts with `2026/trip.mov` |

Issues `#198` (`2026-09-16`) and `#213` initially kept both behaviors behind `MINIO_API_MULTIPART_LISTING=legacy|strict` so upgrades with pre-existing legacy uploads would not break silently. PR `#243` (`2026-10-17`) sought to eliminate the two-mode configuration surface after adding lazy backfill for older uploads.

### Alternatives Evaluated During `#243` {#decision-alternatives}

| Candidate | Restart Survival | Prefix & Marker Support | Extra Index Maintenance | Why Chosen / Why It Later Failed |
| :--- | :--- | :--- | :--- | :--- |
| 1. Keep `legacy` + `strict` dual mode | Only in `strict` | Only in `strict` | None | Rejected in `#243` to remove mode split; revisited in `4733e1423` |
| 2. In-memory cache only | No | Yes (while cached) | None | Rejected: loses all visibility on restart |
| 3. Scan `.minio.sys/multipart` + `xl.meta` identity (`#243`) | Yes | Yes | None | Chosen in `#243`; **rolled back in `4733e1423`** because O($N \times (H+U)$) walk hits 100k cap at 3,126 uploads on 16 drives |
| 4. Sidecar JSON file per upload | Yes | Yes | Extra file create/delete per upload | Rejected: doubles metadata file operations on create/abort |
| 5. Per-bucket on-disk multipart index tree | Yes | Yes (O(matching prefix)) | Requires distributed index heal & cleanup | Deferred: only viable long-term path for large erasure sets, but requires its own crash/heal protocol |
| 6. External KV / SQLite index | Yes | Yes | External state outside erasure coding | Rejected: violates self-contained erasure-set architecture |

### On-Disk Storage Layout and `xl.meta` Identity Fields {#decision-storage}

An active multipart upload is stored at:

```text
.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta
.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/part.1
...
```

Because `<sha256(bucket/object)>` is a one-way digest, the directory path alone does not reveal the bucket or object name. Commit [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc) extended `newUploadedObjectMetadata` in `cmd/erasure-multipart.go` to store two internal metadata keys in `xl.meta` (retained in `20261018`):

- `x-minio-internal-multipart-v1-bucket`: plain bucket name
- `x-minio-internal-multipart-v1-object`: plain object key

Compatibility check against upstream MessagePack `xl.meta` readers (verified against commit `3be10fcc1a44f6620ded0bd303461f9d688cca23`): `MetaSys` is a standard `map[string][]byte` inside `xl.meta`, so older readers ignore unknown `x-minio-internal-*` keys without schema errors.

### Discovery and Quorum Rules in the Disk-Scan Path {#decision-read-policy}

When the disk-scan path (`listMultipartUploadsScan`) ran in `#198` and `#243`, each erasure set executed five steps:

1. List `<sha256(bucket/object)>` directories under `.minio.sys/multipart` across all online drives, requiring each hash directory to appear on at least `readQuorum = floor(N/2) + 1` drives.
2. List `<uploadID>` subdirectories inside each quorum-present hash directory, validating every `uploadID` with `checkUploadID` and requiring `readQuorum` presence.
3. Read `xl.meta` from online drives for each candidate `uploadID` and require at least `readQuorum` drives to agree on `(Bucket, Object)`.
4. If an older pre-upgrade upload lacked `x-minio-internal-multipart-v1-*` keys, resolve `(Bucket, Object)` when an exact prefix or cache entry supplied the candidate key and lazily backfill `xl.meta`.
5. Filter by `Bucket`, `Prefix`, `Delimiter`, `KeyMarker`, and `UploadIDMarker`, sort by `(Key, Initiated, UploadID)`, and merge across pools.

### Directory Traversal Cost and 4-Drive Benchmark (`#243`) {#decision-cost}

On an `N`-drive erasure set with `H` active `<sha256(bucket/object)>` directories and `U` active `<uploadID>` directories across all buckets:

- Total directory entries inspected per uncached scan: $N \times (H + U)$
- Total `ListDir` operations per uncached scan: $N \times (1 + H)$

In `#243`, `BenchmarkMultipartListingCapacity` was run only on a **4-drive** single-set fixture (`N = 4`), where `10,000` uploads for a single key ($H = 1, U = 10{,}000$) produced $4 \times (1 + 10{,}000) = 40{,}004$ directory entries:

| 4-Drive Fixture (`BenchmarkMultipartListingCapacity` on `4ed86dfe6`) | Active Uploads | Wall Time | Memory Allocated | Allocations |
| :--- | ---: | ---: | ---: | ---: |
| Single object key ($H = 1, U = 10{,}000, N = 4$) | `10,000` | `101.6 ms` | `3.58 MB` | `61,210` |

That single-key, 4-drive benchmark masked the two multiplicative factors that broke on 16-drive sets the following day: $N = 16$ drives ($4\times$ multiplier) and distinct object keys $H = U$ ($2\times$ entry multiplier and $U\times$ `ListDir` multiplier), which together pushed `3,126` uploads over `maxMultipartWalkEntries = 100000`.

### Abort-vs-Delayed-Create Race on 16-Drive EC:8 Sets {#decision-abort}

During the `#243` review, we also analyzed whether `AbortMultipartUpload` could leave behind a resurrected upload under a fixed `readQuorum = floor(N/2) + 1` (for example, `9` on a 16-drive `EC:8` set):

1. Suppose `NewMultipartUpload` writes `xl.meta` on `8` drives immediately while `7` drives are stalled in flight and `1` drive is offline.
2. A concurrent `AbortMultipartUpload` deletes the `8` existing copies on the fast drives and returns.
3. The `7` delayed `NewMultipartUpload` writes then land on disk, and the `1` offline drive later heals or comes back with its copy—leaving `8` readable copies (`readQuorum` for `EC:8` object reads) of an upload that the client already aborted.

While `AbortMultipartUpload` cache eviction and peer notification (retained in `4733e1423`) keep the in-memory cache consistent across nodes, eliminating delayed-create resurrection on disk would require tombstones or per-upload generation locks.

### Summary of October 17 Code Changes (Later Partially Reverted) {#decision-changes}

- `cmd/object-api-interface.go`, `cmd/server-main.go`, `cmd/config-current.go`: made `api multipart_listing` a compatibility no-op (`4ed86dfe6`; retained as no-op in `4733e1423`).
- `cmd/erasure-multipart.go`: added lazy `xl.meta` identity backfill during exact-key resolution and routed all listings through the disk scanner (`4ed86dfe6`; public scan routing reverted in `4733e1423`, `xl.meta` write metadata and `0f9199e0c` empty-parent cleanup retained).

### October 17 Test Evidence {#decision-evidence}

- `go test ./cmd -run 'TestMultipartUploadListing|TestMultipartPreflight|TestMultipartListingConfig'` passed on `4ed86dfe6`.
- `BenchmarkMultipartListingCapacity` passed at `101.6 ms` on a 4-drive single-key fixture, which proved insufficient to catch the 16-drive distinct-key limit.

### Follow-Up Lessons from `#243` {#decision-followup}

Any future attempt to provide restart-durable arbitrary-prefix `ListMultipartUploads` **must** index active uploads by `(bucket, object, uploadID)` rather than scanning `.minio.sys/multipart/<sha256(bucket/object)>` directories across all drives in the erasure set, and **must** benchmark capacity on `16`-drive sets with distinct object keys ($H = U$).

---

## Historical Record: September 16 Opt-In `strict` Mode (`#198`) {#implementation-20260916}

Issue `#198` (commit [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc), hardened in [`143f6970d`](https://github.com/pgsty/silo/commit/143f6970d) and [`0ff5b37fc`](https://github.com/pgsty/silo/commit/0ff5b37fc)) delivered the initial opt-in implementation for Server `20260916`:

- Added `MINIO_API_MULTIPART_LISTING=legacy|strict` (default `legacy`) and `mcli admin config set/reset ALIAS api multipart_listing`.
- Added `GET /minio/admin/v3/multipart-preflight` so operators could check whether pre-existing `.minio.sys/multipart` directories lacked `x-minio-internal-multipart-v1-bucket` and `x-minio-internal-multipart-v1-object` before enabling `strict`.
- Enforced S3 ordering by `(Key, Initiated, encoded UploadID)` and `floor(N/2) + 1` drive discovery quorum in `strict` mode.
- Observed during September 16 Docker Desktop testing: `10,000` active uploads across `4` containers took `18.7 s` (`p95 = 2.68 s` at concurrency `10`) due to per-drive `xl.meta` reads over virtualized container filesystems.

---

## Original Root-Cause Analysis (2026-08-30) {#analysis-20260830}

### Overview {#plain-language}

In upstream MinIO's erasure-coded storage engine (`erasureObjects`), `CreateMultipartUpload` stores each upload on disk under `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>`, while also recording the upload in an in-memory per-bucket cache (`multipartUploadsCache`). Because the on-disk directory name hashes `bucket/object` with SHA-256, the storage layer can jump directly to a known object's multipart directory when given the exact `bucket` and `object`, but cannot list uploads by bucket or by key prefix from disk without opening every active upload directory.

### Original August 30 Recommendation {#decision}

The August 30 investigation recommended fixing `ListMultipartUploads` in two stages: first writing `(bucket, object)` identity metadata into `xl.meta` at `NewMultipartUpload` time and exposing an opt-in disk-backed mode (`#198`), and later evaluating whether the disk scan or a dedicated per-bucket index should become the default.

### Evidence and Sources {#sources}

#### AWS S3 Specification {#source-s3}

The AWS S3 `ListMultipartUploads` specification requires filtering by `prefix` and `delimiter`, lexicographical ordering by `Key` and `Initiated` time (with `UploadId` breaking ties), and continuation via `key-marker` and `upload-id-marker`.

#### Repository Issue `#198` {#source-issue}

Issue `#198` reported that `ListMultipartUploads` with a directory prefix (`prefix=dir/`) returned an empty list even immediately after `CreateMultipartUpload`, and that unprefixed `ListMultipartUploads` returned an empty list after a server restart even though `UploadPart` and `CompleteMultipartUpload` using the saved `UploadId` still succeeded.

#### Upstream MinIO History {#source-upstream}

- **MinIO PR `#5248`**: Replaced the earlier bucket-mirrored multipart tree with `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` to avoid deep path-length limits and empty parent-directory cleanup bugs on POSIX filesystems.
- **MinIO PR `#20407`**: Added the in-memory `multipartUploadsCache` so empty-prefix `ListMultipartUploads` could return recently created uploads without walking disk, while routing non-empty `prefix` directly to `listMultipartUploads(bucket, prefix, ...)` as an exact object key lookup.
- **MinIO Issue `#20989`**: Documented the resulting upstream limitation in `docs/minio-limits.md`: `ListMultipartUploads` is only supported with an empty prefix (from memory) or with `prefix` set to the full object key.

#### Code Inspection in `pgsty/silo` {#source-code}

- `cmd/bucket-handlers.go` (`ListMultipartUploadsHandler`): extracted `prefix`, `keyMarker`, `uploadIDMarker`, `delimiter`, and `maxUploads`, validated `encoding-type`, and passed them to `objectAPI.ListMultipartUploads`.
- `cmd/erasure-sets.go` (`erasureSets.ListMultipartUploads`): branched on `prefix == ""`—reading `multipartUploadsCache.List(bucket)` when empty, and hashing `pathJoin(bucket, prefix)` to call `set.listMultipartUploads` on a single disk hash directory when non-empty.
- `cmd/erasure-multipart.go` (`erasureObjects.listMultipartUploads`): listed `<uploadID>` directories under `.minio.sys/multipart/<sha256(bucket/object)>`, ignoring `delimiter`, `keyMarker`, and `uploadIDMarker`.
- `cmd/erasure-server-pool.go` (`erasureServerPools.ListMultipartUploads`): iterated across pools and returned early on the first pool that produced a non-empty result when `prefix != ""`.

#### Design Review Findings {#source-review}

The initial code review confirmed that the defect was architectural rather than a simple parser typo: the HTTP handler parsed every S3 query parameter, while the storage layer lacked an index mapping `bucket + key-prefix` to `<sha256(bucket/object)>`.

### Behavior Before `#198` (and Restored Default in `20261018`) {#current-behavior}

#### Empty `prefix` Path {#empty-prefix}

When `prefix == ""`:

1. `erasureSets.ListMultipartUploads` reads the in-memory `multipartUploadsCache` for `bucket`.
2. Uploads created before the last process restart are absent from the cache, even though their `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` directories remain intact on disk.
3. Cache synchronization across distributed nodes is best-effort (`updateMultipartUploadInfo`).

#### Non-Empty `prefix` Path {#nonempty-prefix}

When `prefix != ""`:

1. `erasureSets.ListMultipartUploads` treats `prefix` as a full object name (`object = prefix`), hashes `bucket/object` with SHA-256 to locate the target erasure set, and reads `.minio.sys/multipart/<sha256(bucket/object)>` on disk.
2. If a caller passes a true key prefix such as `prefix=photos/2026/`, the server hashes the literal string `"bucket/photos/2026/"`, finds no upload for an object with that exact name, and returns zero uploads.
3. If a caller passes the exact object key `prefix=photos/2026/video.mp4`, the server hashes `"bucket/photos/2026/video.mp4"`, reads the matching `<uploadID>` directories from disk, and returns all active uploads for that object even after a server restart.

#### Multi-Pool Early Return {#multiple-pools}

In `erasureServerPools.ListMultipartUploads`, the non-empty `prefix` path makes sense for an exact object key because `sha256(bucket/object)` maps deterministically to one erasure set in one pool, whereas true prefix listing across multiple pools would have needed to merge results from every pool.

### Why Legacy Uploads Cannot Be Backfilled Automatically Without Candidate Keys {#no-backfill}

Because `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta` historically stored neither the bucket name nor the object key, an existing pre-`20260916` upload directory on disk contains only a SHA-256 digest of `bucket/object`. Without either knowing the candidate `bucket/object` string (to verify its SHA-256 digest) or having `x-minio-internal-multipart-v1-bucket` and `x-minio-internal-multipart-v1-object` in `xl.meta`, the server cannot invert `sha256(bucket/object)` back to `(Bucket, Object)`.

### Structural Complexity {#complexity}

| Layer | What It Assumes | Consequence |
| :--- | :--- | :--- |
| S3 HTTP API (`ListMultipartUploadsHandler`) | `prefix` is a key prefix; `delimiter` groups common prefixes; markers paginate sorted keys | Expects ordered `(Key, Initiated, UploadID)` candidates per bucket |
| On-Disk Layout (`.minio.sys/multipart/<sha256(bucket/object)>`) | Callers always supply the exact `bucket` and `object` (`PutObjectPart`, `Complete`, `Abort`) | O(1) lookup by exact key, but no bucket partition and no lexicographical key order |
| In-Memory Cache (`multipartUploadsCache`) | Tracks uploads observed since process start | Fast O(bucket) listing for empty `prefix`, but ephemeral across restarts |

### Operational Impact {#impact}

#### Wire Compatibility Impact {#wire-impact}

SDKs and backup tools that call `ListMultipartUploads` with a directory `prefix` (such as `aws s3api list-multipart-uploads --bucket B --prefix dir/`) receive an empty list unless `prefix` equals the full object key.

#### Storage and Orphan Cleanup Impact {#storage-impact}

Tools that rely on `ListMultipartUploads` after a restart or with a directory prefix to discover and abort unfinished uploads cannot see those uploads via listing; however, Silo's built-in background stale-upload sweep (`cleanupStaleUploads`) walks `.minio.sys/multipart` directly by modification time and cleans up expired uploads regardless of `ListMultipartUploads` behavior.

#### Operational Trade-Off {#operational-impact}

As proven on `2026-10-18`, forcing `ListMultipartUploads` to walk `.minio.sys/multipart` on every uncached public request turns a listing limitation into a `503 SlowDown` availability cliff at `3,126` active uploads on 16-drive erasure sets. Keeping the MinIO-compatible path protects cluster-wide `ListMultipartUploads` availability while preserving exact-key disk lookup and background expiry cleanup.

#### Severity Classification {#severity}

- **Data integrity risk**: None (`PutObjectPart`, `CompleteMultipartUpload`, and `AbortMultipartUpload` address uploads by exact `Bucket + Object + UploadID`).
- **S3 API compatibility gap**: Documented difference in [S3 API Compatibility](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads).

### Design Options Compared {#options}

#### Option 0: Keep Traditional Behavior Without Documentation {#option-zero}

Leaves callers surprised when `prefix=dir/` returns empty results. Rejected in favor of explicit documentation and retained `xl.meta` identity metadata.

#### Option 1: Preserve MinIO-Compatible Behavior and Document the Contract (`20261018` Choice) {#option-divergence}

Keeps empty-prefix listing backed by the in-memory cache and non-empty `prefix` backed by exact-key disk lookup, while keeping `xl.meta` self-describing and fixing empty hash-parent cleanup (`0f9199e0c`). Selected in `20261018` after the 16-drive scan regression.

#### Option 2: Scan `.minio.sys/multipart` on Disk with `xl.meta` Identity {#option-scan}

Implemented as opt-in `strict` mode in `#198` and briefly made default in `#243`. Works on small upload counts, but scales as $O(N \times (H + U))$ across all buckets in an erasure set and hits the `100,000`-entry traversal cap at `3,126` distinct-key uploads on a 16-drive set.

#### Option 3: Dedicated Per-Bucket Multipart Index {#option-index}

Maintains a bucket-scoped, prefix-ordered metadata index alongside `.minio.sys/multipart`. Avoids cross-bucket SHA-256 directory scans, at the cost of maintaining and healing a second distributed metadata structure on every `CreateMultipartUpload`, `CompleteMultipartUpload`, `AbortMultipartUpload`, and expiry sweep.

#### Option 4: Expand In-Memory Cache to Support Prefix/Delimiter Only {#option-cache-only}

Applies full S3 `prefix`, `delimiter`, and marker filtering to `multipartUploadsCache` in memory without disk scanning. Fast and bounded, but still loses visibility of pre-restart uploads until an exact-key operation touches them.

### Reference Architecture for Disk-Backed Listing (Implemented in `#198`, Rolled Back on Public Path in `4733e1423`) {#recommended-design}

#### 1. Contract Definition {#contract-first}

Define exact ordering `(Key, Initiated, UploadID)` and marker continuation rules before touching storage routines.

#### 2. Write Path (`xl.meta` Identity) {#write-path}

Write `x-minio-internal-multipart-v1-bucket` and `x-minio-internal-multipart-v1-object` into `xl.meta` in `NewMultipartUpload` (retained in `20261018`).

#### 3. Read Path {#read-path}

Require `readQuorum` agreement across drives when reading multipart metadata from disk.

#### 4. Semantic Filtering Layer {#semantic-layer}

Apply `Prefix`, `Delimiter`, `KeyMarker`, `UploadIDMarker`, and `MaxUploads` above the per-set discovery layer.

#### 5. Exact-Key Helper {#exact-helper}

Keep a direct O(1) exact-key lookup helper (`sha256(bucket/object)`) for internal callers and exact-key queries.

#### 6. Cache Synchronization {#cache}

Evict `multipartUploadsCache` entries on `AbortMultipartUpload` and `CompleteMultipartUpload` across peers (retained in `20261018`).

#### 7. Migration and Preflight {#migration}

Provide `/minio/admin/v3/multipart-preflight` for inspecting on-disk multipart directories (retained as a compatibility endpoint in `20261018`).

#### 8. Degraded and Suspended Pools {#suspended-pools}

Skip suspended pools cleanly during multi-pool listing rather than failing the entire request.

### Spike Checklist Used for `#198` {#spike}

1. Verify `MetaSys` MessagePack compatibility with existing `xl.meta` readers.
2. Measure `ListDir` and `readAll` amplification across `N` drives.
3. Verify `cleanupStaleUploads` removes empty `<sha256(bucket/object)>` parent directories (fixed in [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c)).

### Verification Gates {#gates}

#### Unit Tests {#unit-tests}

Validate prefix, delimiter, marker pagination, and `checkUploadID` path-traversal rejection.

#### Handler and End-to-End Tests {#handler-tests}

Verify `ListMultipartUploadsHandler` response XML, URL encoding, and cache vs exact-key behavior across restarts.

#### Failure and Capacity Benchmarks {#failure-tests}

Run `BenchmarkMultipartPublicListingCapacity` across both `4`-drive and `16`-drive erasure-set topologies with up to `10,000` active uploads.

#### Delivery Gates {#delivery-gates}

Document the public `ListMultipartUploads` contract in [S3 API Compatibility](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads) and keep all historical anchors intact.

### Current Engineering Conclusion {#final-recommendation}

Keep the MinIO-compatible public `ListMultipartUploads` path (`4733e1423`) and empty-parent directory cleanup (`0f9199e0c`) as the production default in Server `20261018`. Do not re-enable unindexed `.minio.sys/multipart` disk scans on the public listing path; if full restart-durable prefix listing is required in a future release, design a bucket-scoped multipart index benchmarked on 16-drive erasure sets first.
