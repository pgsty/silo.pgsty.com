---
title: "Overwrite Pool Affinity: Why #245 Was Not Adopted"
linkTitle: "Overwrite Pool Affinity"
date: 2026-10-24
lastmod: 2026-10-24
author: "Ruohang Feng"
summary: "The design, correctness fixes, two rounds of m3 benchmarks, and decision to stop the overwrite-affinity experiment: fewer stale copies did not justify the remaining small-object write cost."
tags: [Design, S3, Storage, Performance, Review]
weight: 9
draft: false
url: "/blog/design/overwrite-pool-affinity/"
---

**Decision, October 24, 2026: do not merge the tested pool-affinity changes ([PR #245](https://github.com/pgsty/silo/pull/245)).** The experiment addressed a real space-efficiency problem, but neither the broad policy nor the narrower unversioned-only policy achieved an acceptable performance trade-off. Both experimental branches (`codex/healthy-pool-affinity` and `codex/unversioned-pool-affinity`) were retained for reference while keeping `main` unchanged.

Denis Babchuk proposed keeping overwrites in the pool that already holds the object. Review identified and fixed a request-specific write-quorum bug, tightened the health policy, and validated the behavior. Performance measurements then changed the recommendation: the broad policy made deep version histories substantially more expensive, and a second iteration restricted to ordinary unversioned overwrites still regressed small-object writes.

The subsequent [multi-pool deletion fix (#257)](/blog/design/multi-pool-delete-safety/) was merged independently on October 24: while retaining capacity-weighted allocation, it cleans up non-authoritative copies before deleting the authoritative copy so a mid-delete failure cannot expose an overwritten value.

## The problem: an overwrite can leave its old copy in another pool {#problem}

Consider an unversioned key, `reports/latest.json`, in pool A. A subsequent `PUT` writes its replacement to pool B. Reads select the newest logical object, while the old physical copy in A continues to occupy space because ordinary overwrites do not clean up obsolete copies across other pools.

The baseline looks up the existing object and then sends a readable result through capacity-weighted pool selection again. Depending on pool usage, repeated writes can eventually leave a pool-local record (`xl.meta`) in both pools.

This behavior has a specific history:

- Upstream [MinIO issue #21087](https://github.com/minio/minio/issues/21087) reported that single-pool uploads could bypass the minimum free-space threshold. [PR #21115](https://github.com/minio/minio/pull/21115), merged on July 19, 2025 as [`83b2ad418b`](https://github.com/minio/minio/commit/83b2ad418b15ff0fa78175e2014d78d02046edd8), enforced capacity checks by reselecting a pool for readable existing objects, which dropped their earlier placement affinity.
- SILO [issue #199](https://github.com/pgsty/silo/issues/199) and [PR #207](https://github.com/pgsty/silo/pull/207) evaluate conditional writes against the current logical object across pools while keeping the capacity-weighted allocation policy.
- Pool migration uses separate safeguards against stale payloads and delete-marker loss; see [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/#migration-20261018).

The space benefit of overwrite affinity applies specifically to **multi-pool deployments with repeated overwrites of the same unversioned keys**. Single-pool deployments have no cross-pool duplicates, new keys still require capacity-weighted allocation across pools, and versioned buckets must retain their historical versions regardless of which pool stores them.

## What the original PR changed {#original-design}

The proposal reused the existing object lookup and lock boundary. If the latest readable object was already present, its pool became the preferred destination, subject to write quorum and the existing hard free-space check. New keys retained capacity-weighted allocation. When the existing object's set could not accept a write, allocation excluded that pool before considering the remaining pools.

The production change in `cmd/erasure-server-pool.go` added 73 lines and removed 3 lines, accompanied by 331 lines of placement tests, covering `PUT` and multipart initialization on the shared allocation path.

Two capacity rules apply during selection:
- **Soft allocation reserve (15%)**: when alternative pools exist, the allocator filters out pools above roughly 85% usage so emptier pools fill first.
- **Hard space check (`hasSpaceFor`)**: checks write size, per-drive capacity, and other constraints against `diskFillFraction` (`0.99`).

Affinity bypasses the soft reserve when the existing object's pool is healthy and has room, while preserving the hard capacity check. After a pool expansion, existing keys continue updating in their older, fuller pool rather than migrating to the new pool on overwrite.

Simply deleting the condition that reselects existing objects would lose the capacity checks and fallback introduced in [`83b2ad418b`](https://github.com/minio/minio/commit/83b2ad418b15ff0fa78175e2014d78d02046edd8). Checking space alone is also insufficient: an erasure set can still have read quorum for an old object while lacking enough online drives to reach write quorum for its replacement. Because pool selection runs before consuming the request body, an unreplayable upload stream cannot be transparently retried in another pool after a write failure.

## Correctness review and implementation improvements {#correctness}

### Write quorum must match the request

The original helper inferred quorum from the `STANDARD` storage class for every write. A controlled two-pool test exposed a regression when overwriting an object with `REDUCED_REDUNDANCY` (RRS):

| Condition | Test setup |
| --- | --- |
| Storage policy | `optimize=capacity`; `STANDARD=EC:4`, `REDUCED_REDUNDANCY=EC:2` |
| Existing object | Created with ordinary `STANDARD` parity |
| Existing object's set | 13 of 16 drives online; reported usage 90% |
| Other pool | 16 drives online, ample space; an actual RRS probe write succeeded |
| New request | Overwrite using RRS, through `PUT` or new multipart initialization |

The helper required 12 writers for `EC:4` and selected the original pool, whereas the actual `EC:2` write required 14 online drives and failed with `InsufficientWriteQuorum` (HTTP 503). Because lower parity leaves more data shards, RRS requires **more** online drives for a write. The baseline's reserve filter skipped the 90%-full pool, selected the healthy second pool, and succeeded across all four pool/entry-point combinations (12/12 attempts failed on the unpatched PR).

The inverse mismatch occurred with `PUT`'s internal `MaxParity` option: a write eligible for `EC:8` was evaluated against `EC:4` and unnecessarily moved to another pool.

### A healthy preference, with explicit fallback

The updated implementation passed the request's storage class and `PUT` `MaxParity` into placement, matching the writer's availability/capacity parity rules (including the extra drive required when data and parity shard counts are equal) while preserving multipart initialization parity semantics:

| Existing object's target set | Action |
| --- | --- |
| Fully healthy, writable for this request, and enough space | Prefer that pool |
| Degraded but still writable, with space | Use the existing capacity allocator; the original pool remains a candidate |
| Known to be unwritable or lacking space | Exclude it before reserve filtering, then select another pool |
| No alternative has space, but the original set has space and lacks write quorum | Let the original set report `InsufficientWriteQuorum` rather than misreporting `StorageFull` |
| No usable space | Preserve the `StorageFull` result |

Health and capacity checks shared a single set-level `DiskInfo` snapshot. A drive counted as a usable writer only if it was online and returned a positive capacity result; drives with a failed `DiskInfo` call were treated as unhealthy.

Regression tests were added for request parity, known disk faults, degraded sets, scan counts, heterogeneous set sizes, latest-object selection, and existing multipart sessions. The multipart fallback test was also updated to seed its own initial object rather than reusing a prior `PUT` target that had already moved pools.

## The second design: only ordinary unversioned overwrites {#narrow-scope}

After the first performance round showed high version-history rewrite costs, a second branch (`codex/unversioned-pool-affinity`) narrowed the policy to ordinary unversioned overwrites:

| Request or bucket state | Narrowed behavior |
| --- | --- |
| Ordinary unversioned `PUT` replacing a readable object | Apply the healthy-pool preference above |
| New multipart upload over an ordinary unversioned object | Apply it only when initialization reaches pool selection; preserve existing upload binding |
| Versioning enabled or suspended | Retain baseline allocation |
| Explicit version ID, including `null` | Exclude from affinity |
| Replication, replica-lock reconciliation, or data movement | Exclude from affinity |
| Internal metadata buckets | Exclude from affinity |
| New keys or a single pool | Retain the original path and capacity behavior |
| Existing multipart sessions, ordinary COPY routing, latest delete markers, or read-quorum-error routing | Preserve their existing paths |

Eligibility checked both the bucket's versioning configuration and the request options. A version-enabled bucket with prefix-excluded unversioned writes, or a version-suspended bucket with mixed history, remained on the baseline allocator.

## Functional validation, separated by revision {#validation}

| Stage | Evidence | Scope |
| --- | --- | --- |
| Initial PR review | Base/head comparison reproduced normal affinity, `STANDARD` fallback, the RRS failure, and the `MaxParity` mismatch | Object-layer unit tests on macOS |
| Improved full implementation | Full Go test suite: 52 packages, 1,823 top-level tests (8,233 with subtests) passed, 12 skipped; targeted `-race` suite: 35 top-level tests (201 with subtests) passed | Full-affinity branch on an isolated APFS test volume |
| Full implementation through mcli | `mcli` `20261018` verified ordinary overwrite/readback, 4 distinct retained versions with historical reads, and multipart overwrite/checksum | Single-host local-directory deployment |
| Narrowed implementation | Linux targeted suite: 37 top-level tests (209 with subtests) passed across placement, parity, health/capacity fallback, version-state exclusions, `PUT`/MPU, and conditional writes | Targeted placement and overwrite suite |
| Build and static checks | Linux `amd64` build, `make verifiers`, lint (0 issues), and whitespace checks passed | Repository static verification |

The targeted regression filter was:

```text
^(TestPoolsOverwrite|TestPoolsMultipartOverwrite|TestSinglePoolOverwrite|TestPoolsConditionalPut|TestSinglePoolConditionalPut|TestPoolsMultipartCondition)
```

## Benchmark method and what the numbers mean {#method}

Both performance rounds ran on **m3** (AMD Ryzen AI MAX+ 395, 32 logical CPUs, 61 GiB RAM, Linux 7.0.0-38, CT2000P310SSD8 NVMe with XFS). Two pools each used 16 directories and one erasure set (`EC 12+4`), all backed by the same XFS filesystem on the shared NVMe SSD.

Both variants were built with Go 1.27.3 (`linux/amd64`, `CGO_ENABLED=0`). The server ran on CPUs 4–11 (`GOMAXPROCS=8`), and the `minio-go` `v7.4.1` benchmark client ran on CPUs 12–15 (`GOMAXPROCS=4`) over loopback HTTP.

- **Throughput**: completed object operations per second (for multipart, one operation includes initialization, two part uploads, and completion).
- **P50 / P99**: medians across runs of each run's 50th and 99th percentile request latencies.
- **CPU cost**: server CPU time per completed operation.
- **Block I/O**: process-accounted reads and writes from `/proc/PID/io`.
- **Active-bucket space**: object files, metadata, and directory overhead excluding temporary files.

## Round one: the full policy cost more than expected {#full-results}

Round one compared the full candidate (`0aa870115d7d`) against the baseline (`789a2327ba8c`) across 54 measured runs (243,718 completed operations, 0 failures). Basic workloads ran 3 pairs of 15-second runs, with 2 additional 60-second pairs for new-key and 4 KiB overwrite workloads, 3 fixed-count runs of 4,000 versions on a single seeded object, and a 4-run ABBA binary-switch sequence on existing dual-copy data:

| Workload | Baseline → full candidate, operations/s | Change | P50, ms | P99, ms | Sample |
| --- | --- | --- | --- | --- | --- |
| Two pools, 4 KiB overwrite; 256 keys, concurrency 16 | 236.9 → 174.5 | **−26.3%** | 30.4 → 74.4 | 277.9 → 307.4 | 2 × 60 s per variant |
| Two pools, 1 MiB overwrite; 64 keys, concurrency 8 | 140.9 → 132.2 | −6.2% | 34.2 → 41.3 | 169.3 → 176.2 | 3 × 15 s |
| Two pools, 16 MiB multipart overwrite; 16 keys, concurrency 4 | 25.8 → 26.4 | +2.1% | 144.0 → 141.7 | 265.3 → 272.7 | 3 × 15 s |
| Two pools, one 4 KiB key; concurrency 1 | 135.2 → 136.4 | +1.0% | 6.9 → 6.8 | 12.0 → 10.6 | 3 × 15 s |
| Two pools, 4 KiB new keys; concurrency 16 | 290.7 → 296.8 | +2.1% | 46.9 → 48.7 | 170.2 → 165.9 | 2 × 60 s |
| Single pool, 4 KiB overwrite; concurrency 16 | 166.2 → 159.2 | −4.2% | 83.9 → 89.4 | 296.8 → 293.2 | 3 × 15 s |
| Two pools, one 4 KiB key, 4,000 new versions | 76.6 → 53.0 | **−30.8%** | 11.4 → 17.8 | 47.7 → 59.5 | 3 fixed-count runs |
| Existing dual-copy data, binary-switch ABBA | 198.6 → 202.0 | +1.7% | — | 291.2 → 290.9 | 2 × 20 s |

For ordinary 4 KiB overwrites, both 60-second pairs were slower (−30.7% and −21.8%), as were all three 15-second pairs, even though CPU per operation fell from 5.85 to 5.33 ms and block writes stayed near 128 KiB per operation.

The −30.8% version-history regression had a direct structural cause. A pool-local `xl.meta` stores the object's version metadata and inline payload for small objects, and adding a version reserializes and rewrites the entire file. Capacity allocation split the 4,000 versions roughly evenly across both pools (~2,000 versions per `xl.meta`), whereas affinity concentrated all 4,001 versions into a single pool, doubling the `xl.meta` rewrite size on every `PUT`:

- **CPU per write**: 26.61 ms → 39.29 ms
- **Block reads per write**: 12.20 MiB → 24.42 MiB
- **Block writes per write**: 12.27 MiB → 24.49 MiB (cumulative block writes over 4,000 operations rose from **47.9 GiB to 95.7 GiB** for ~15.6 MiB of uploaded payload)
- **Active data at 4,001 versions**: ~48.90 MiB in both variants
- **Mean latency over the final 1,000 writes**: 18.4 ms → 28.5 ms

Because versioned buckets must keep all historical versions, concentrating them in one pool doubled the metadata rewrite amplification without saving disk space. This motivated narrowing the policy to unversioned overwrites.

## Round two: narrowing fixed one cost, but not the acceptance problem {#narrow-results}

Before running round two (`codex/unversioned-pool-affinity` vs. `789a2327ba8c`), the acceptance threshold for the experiment was set at **≤ 5% ordinary-overwrite throughput loss and ≤ 10% P99 latency growth**, with no material P50 or excluded-scope regression.

Four workloads ran 5 pairs each in alternating AB/BA order (5-second warmup and 60-second measurement for timed workloads; 4,000 operations for versioned control; fresh server and data directories per run, no profilers attached):

| Workload | Baseline → narrowed, operations/s | Change | P50, ms | P99, ms |
| --- | --- | --- | --- | --- |
| Fresh 4 KiB overwrite; 256 keys, concurrency 16 | 167.9 → 158.2 | **−5.7%** | 66.2 → 75.8 | 470.2 → 428.7 |
| Fresh 1 MiB overwrite; 64 keys, concurrency 8 | 79.45 → 79.58 | +0.2% | 94.0 → 95.6 | 521.5 → 483.2 |
| One 4 KiB key, 4,000 new versions; control | 48.5 → 59.6 | +22.8% | 12.7 → 12.4 | 180.9 → 135.4 |
| New 4 KiB keys; concurrency 16; control | 289.8 → 243.1 | −16.1% | 40.4 → 49.2 | 314.9 → 170.0 |

On the primary 4 KiB overwrite workload, pairwise throughput changes across the five pairs were **+11.9%, −14.9%, −1.4%, −10.3%, and −12.8%** (median paired change −10.3%; ratio of variant medians −5.7%; P50 +14.4%). Baseline throughput ranged from 141.4 to 202.6 ops/s (CV 13.0%) and narrowed throughput from 146.3 to 176.6 ops/s.

Excluding versioned buckets eliminated the round-one `xl.meta` write amplification: block writes per version were **12.272 → 12.268 MiB**, block reads **12.201 → 12.197 MiB**, and CPU **26.98 → 27.26 ms** (in the versioned control, the second run of each pair was faster regardless of binary order, and new-key control pairs varied from −44.3% to +15.3% due to shared-SSD order effects).

### Restore the same starting data before each run

Because fresh runs let the two placement policies build different on-disk layouts over time, an additional 8-run fixture test restored an identical snapshot before each run—either one pool-local copy per key (256 records) or copies in both pools (512 records)—followed by a 30-second settle period, 5-second warmup, and 60-second measurement:

| Starting state, 256 keys | Baseline → narrowed, operations/s | Change | P50, ms | P99, ms | Ending pool-local records, baseline → narrowed |
| --- | --- | --- | --- | --- | --- |
| One copy per key | 188.0 → 160.1 | **−14.9%** | 51.9 → 68.0 | 521.0 → 466.4 | 512 → 256 |
| Two copies per key | 185.7 → 140.1 | **−24.5%** | 37.6 → 79.7 | 460.0 → 629.9 | 512 → 512 |

The single-copy pairs changed by −0.9% and −23.5%. The dual-copy pairs declined by **−22.6% and −26.5%**, with P50 rising **+111.9%** and P99 rising **+36.9%**, while leaving all 512 existing records on disk. On clusters that already have cross-pool duplicates, the narrowed policy paid a steep write penalty without reclaiming any existing space.

## Diagnosis and the I/O optimization attempt {#diagnosis}

Phase timing measured the new health check at **0.014–0.016 ms** per call, compared with milliseconds for existing-object lookup and tens of milliseconds for erasure writes. In round two, 4 KiB overwrite CPU time fell from **5.75 to 5.36 ms** per operation while throughput dropped, pointing to I/O and scheduling wait rather than CPU overhead.

Go execution traces showed syscall waits concentrated in `RenameData → writeAllInternal → write`, alongside read and goroutine scheduling waits.

A follow-up experiment routed small metadata writes (~791 bytes, below the 4 KiB alignment threshold where `CopyAligned` disables `O_DIRECT`) from the Linux `O_DSYNC` path to `writeAllDirect`, turning the write into a buffered write followed by `fdatasync`. Across five runs, narrowed affinity plus the I/O change averaged 179.4 ops/s versus the baseline's 167.9 ops/s (+6.9%, P99 −1.5%, pairwise range −19.2% to +35.9%). However, when the same I/O change was applied to both baseline and candidate in two exploratory pairs, baseline-plus-I/O reached 212.5 ops/s versus 185.2 ops/s for affinity-plus-I/O (−12.8%, pairwise +37.7% and −49.1%). Because changing small-metadata sync paths affects the entire storage engine and did not isolate the affinity regression, the overlay was discarded.

## What it buys, and what it costs {#tradeoffs}

In fresh two-pool tests, 256 ordinary 4 KiB keys ended with **512 → 256** pool-local records and active logical size of **6.18 → 3.09 MiB**. The 1 MiB workload ended with **128 → 64** records and **171.56 → 85.78 MiB**.

At the cluster level, if a fraction $f$ of logical data would otherwise accumulate two copies across two pools, avoiding the second copy reduces steady-state space by $f / (1 + f)$ (for example, ~9.1% at $f = 10\%$). Per-request write volume is unchanged: ordinary 4 KiB overwrites generated ~**128 KiB of block writes per operation** in both variants.

| Aspect | Benefit | Cost or limit |
| --- | --- | --- |
| Capacity | Prevents new stale copies during eligible unversioned overwrites | Does not reclaim existing copies; fallback can still leave copies across pools |
| Write performance | A healthy preferred pool skips a full capacity-selection pass | Placement alters I/O contention; small-object overwrite regressions remained (−5.7% fresh, −24.5% dual-copy fixture) |
| Expansion and hot keys | Existing objects keep a stable pool location | Older pools retain growing/hot keys after expansion instead of shedding overwrites to newer pools |
| API and format compatibility | No wire, configuration, dependency, or disk-format change | Pool distribution changes operational balance under the same S3 interface |
| Availability and correctness | Request-aware quorum and fault checks avoid unsafe pool preference | Preflight state can change before write completion |
| Maintenance | Narrow scope avoids versioned `xl.meta` amplification | Parity, bucket state, internal writes, reserve rules, `PUT`, and multipart routing must stay synchronized |
| Rollback | Returning to baseline requires no format conversion | Stale copies created before or during rollout remain on disk |

## Final decision and conditions for revisiting it {#decision}

1. **Full affinity (`codex/healthy-pool-affinity`)**: rejected because concentrating version histories in one pool doubled `xl.meta` rewrite I/O and cut 4,000-version throughput by 30.8% without saving space.
2. **Narrowed unversioned affinity (`codex/unversioned-pool-affinity`)**: rejected because ordinary 4 KiB overwrites still regressed by 5.7% on fresh data (median paired change −10.3%) and by 24.5% (P50 +111.9%) on restored dual-copy fixtures.

We therefore kept the mainline allocator unchanged and archived the benchmark records (54 runs / 243,718 operations in round one; 53 runs / 495,745 operations in round two). Any future revisit should start from production duplicate-space measurements and multi-disk hardware benchmarks, and evaluate whether background stale-copy cleanup or an opt-in placement policy better addresses the workload.

## Source and evidence identification {#evidence}

Public references: [PR #245](https://github.com/pgsty/silo/pull/245), upstream [PR #21115](https://github.com/minio/minio/pull/21115), [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/), and the baseline storage implementation in [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/b91e1c6f2afbaed6dacbd796a60344978b6c8547/cmd/erasure-server-pool.go), [`cmd/xl-storage-format-v2.go`](https://github.com/pgsty/silo/blob/b91e1c6f2afbaed6dacbd796a60344978b6c8547/cmd/xl-storage-format-v2.go), and [`cmd/xl-storage.go`](https://github.com/pgsty/silo/blob/b91e1c6f2afbaed6dacbd796a60344978b6c8547/cmd/xl-storage.go).

| Artifact | Exact identity |
| --- | --- |
| Initial independently reviewed base / PR head | `856f8f4c5580d1c5adacbd8ef2aedf3a4fbc507c` / `3a9cdc731528e31bc4f9e61256025a1baae863e8` |
| PR head observed when documenting, after rebase | `0a6cad318409451b52dfcef18efb476c3927b6f8` |
| Baseline for both m3 rounds | `789a2327ba8c2283cda7192eb65f8374a7f919ba` |
| Full local branch | `codex/healthy-pool-affinity` at `0aa870115d7d0904791104b25ad66f3430579de4` |
| Narrowed local branch | `codex/unversioned-pool-affinity` at `76db3626eb9068b29e4565e78ad22f7720012e65` |
| Narrowed benchmark's production semantics | `bb4b987825985481e5047f94c60f560be85b9c19` |
| Round-two `results/analysis.json` SHA-256 | `68eec465749b625c691abcace90fc71f103b5826ccab4c40a120f39e29ded368` |
| Complete candidate patch SHA-256 | `af833ec4b7bbbc22fca8539a6da40f4fe5fa93d61febabbd5b08a63ae1ecbe1c` |
