---
title: "LIST Recovery: Confirm Only Uncertain Names and Bound the Waiting Cost"
linkTitle: "LIST Recovery and Lock Cost"
date: 2026-10-17
lastmod: 2026-10-19
author: "Ruohang Feng"
summary: >
  The #218 / #239 design keeps ordinary listings on their fast path, confirms eligible disagreements across pools, distinguishes confirmed deletion from drive or decode failures, covers existing writer lock domains, and bounds short-conflict lock waiting.
tags: [Design, S3, ListObjects, Performance, Review]
weight: 96
draft: false
url: "/blog/design/listing-recovery-lock-cost/"
---

Shipped in [SILO Server 20261018](/blog/release/silo-20261018/), [PR #239](https://github.com/pgsty/silo/pull/239) (merged as [`fbcb51197`](https://github.com/pgsty/silo/commit/fbcb5119782a3ec0f2198fd9f42891a11dc4183f), closing [#218](https://github.com/pgsty/silo/issues/218) and retaining mr javad seydi's original signed commits from [#221](https://github.com/pgsty/silo/pull/221)) and the October 18 directory/common-prefix follow-ups ([`3dd53eb81`](https://github.com/pgsty/silo/commit/3dd53eb81) and [`2080b3d03`](https://github.com/pgsty/silo/commit/2080b3d03)) resolve silent object omissions during concurrent `ListObjects` and `ListObjectsV2` scans. This design builds on the [September null-version quorum repair](/blog/design/list-null-version-quorum/) and replaces an earlier recovery proposal that invoked the ordinary `GET` metadata path directly.

## A Successful Directory Scan Can Omit a Live Object {#problem}

Suppose `reports/a.csv` can be downloaded with `GET`, but a `LIST` request returns HTTP `200 OK` without that object name. Backup and inventory tools treat an HTTP 200 listing as authoritative and report the file as missing; a synchronization tool configured to delete destination objects absent from the source listing can delete a valid destination copy. A successful but incomplete listing causes more downstream harm than an explicit error response.

`LIST` combines directory and metadata records collected from different drives at slightly different times. During concurrent overwrites, deletions, rolling restarts, or pool migrations, some drives return older records, others return newer records, and others temporarily lack a record. Reaching listing quorum requires enough mutually compatible records; unrelated object generations or incompatible erasure layouts cannot simply sum their votes together. Previously, when a directory entry failed to reach quorum, the listing merger could silently drop the entry while returning HTTP 200 for the overall request.

This repair applies to `ListObjects` and `ListObjectsV2` (for example, `GET /bucket?list-type=2&prefix=reports/`), which is separate from [`ListMultipartUploads` (#79)](/blog/design/list-multipart-uploads/). It introduces no new S3 query parameters, environment variables, or client flags.

## Selected Recovery Design {#decision}

The listing pipeline first runs the existing directory merge so resolved entries stay on the fast path. Recovery admits only an unresolved latest-only entry that has at least one decodable object record and enough decodable records plus failed reader streams to reach the original listing quorum threshold. Failed streams only justify attempting recovery; they never count as proof that an object exists or satisfies read quorum. Inputs below the threshold and full version-history listings (`ListObjectVersions`) keep their existing behavior.

An eligible unresolved name is carried to the pool merger, where its complete same-name group is confirmed as a unit. The merger acquires an object read lock to exclude concurrent same-name mutations during confirmation, then re-reads current metadata from disk. Confirmation produces one of three outcomes:

- **Present:** Select current metadata using the object's actual erasure layout and standard read quorum. Preserve delete markers until the cross-pool merge can discard older live copies in other pools.
- **Deleted:** Every configured source-set drive slot must return native `FileNotFound` during the raw metadata read, and the merger must also inspect the name's current placement target set in every pool before omitting the group.
- **Unknown:** Return the existing error (such as HTTP 503 `SlowDownRead`) so the caller never mistakes an unconfirmable state for a complete listing. Offline drives, corrupted metadata, missing volumes, and decode errors never count as proof of deletion.

Streaming pagination still returns completed pages before the full bucket scan finishes. Clients must consume all continuation pages; if any page fails, the preceding pages do not form a complete inventory.

Asynchronous cache cleanup also preserves the original request identity: commit [`2a4db6a4f`](https://github.com/pgsty/silo/commit/2a4db6a4f9d0dedf7229a3b1c5866d2a1bbb22ab) captures the cache peer before launching the background cleanup goroutine and passes listing options by value, preventing foreground cache-ID resets from racing with cleanup RPCs. Neither the cache format nor the continuation-token encoding changes.

Why inspect other pools after confirming source-set absence? Consider a two-pool cluster where Pool A's cached directory scan saw `a.csv` while Pool B's earlier scan was empty, and a concurrent migration then moved `a.csv` to Pool B and removed Pool A's copy. Omitting the key solely because Pool A is now empty would miss the live object in Pool B. After confirming strict source absence, the merger queries the current target set across pools and replaces the stale same-name group with the live result. Each distinct erasure set is re-read at most once per recovery.

Legitimate `DELETE` traffic provides a second counterexample: out of 16 directory inputs, suppose 6 hold an older generation, 6 hold a newer generation, and 4 already reflect deletion, so the directory scan cannot form a quorum. Meanwhile, `DELETE` has already returned HTTP 204, `GET` returns HTTP 404, and all 16 drives now report `FileNotFound`. An early iteration of #239 treated that healthy post-delete state as unresolvable and returned HTTP 503. Checking for unanimous native `FileNotFound` across the source set confirms legitimate deletion while still failing closed on genuine drive or decode errors.

### Object Absence Must Not Swallow a Coexisting Directory {#directory-followup}

Commit [`3dd53eb81`](https://github.com/pgsty/silo/commit/3dd53eb81) handles a same-name group where an object is confirmed absent while a coexisting directory entry remains valid: recovery drops only the absent object and retains the directory / common prefix. Commit [`2080b3d03`](https://github.com/pgsty/silo/commit/2080b3d03) preserves ordering when pending objects, resolved objects, and directories appear together: duplicate directories collapse into a single common prefix while live objects remain object entries.

## In-Memory Metadata Representation {#metadata}

The repair adds no persistent files, `xl.meta` fields, on-disk indexes, or migrations. It adds a single source-set pointer to the in-memory `metacache` entry:

```text
ordinary: name="reports/a.csv", metadata=<existing metadata>, listingSet=nil
pending:  name="reports/a.csv", metadata=nil, listingSet=<source set>
```

Pending entries travel only through internal in-memory channels and are consumed by the pool merger. Both metacache encoders explicitly reject unresolved entries, so `listingSet` is never serialized into a pagination cache or transmitted over the wire.

The recovery re-read uses a read-only metadata helper with standard version selection and read-quorum rules, avoiding the opportunistic healing and dangling-object cleanup side effects of the full `GET` path. A narrow in-memory recount applies only after initial quorum selection fails on eligible latest null versions with known erasure layouts: compatible layout groups are counted separately against the original quorum threshold without lowering quorum or mixing votes across layouts.

## Code Changes Across Subsystems {#changes}

| Subsystem | Change and Rationale |
|---|---|
| Directory resolution and pool merge | Carry pending names to the complete same-name group and confirm at the pool merger so per-pool decisions cannot drop live objects or resurrect shadowed copies. |
| Metadata reading | Distinguish unanimous native `FileNotFound` from read/decode errors; reuse read-quorum and version selection without `GET` write side effects. |
| Object locking | Acquire the pool-level lock on multi-pool clusters; on single-pool clusters with distinct source and target sets, acquire first-set and target-set read locks in fixed order to cover both `DELETE`/`COPY` and `PUT` lock domains. |
| Pagination cache | Publish terminal scan errors before marking the cache complete so HTTP error responses do not wait on a failing remote cache RPC, and preserve the local cache ID and error if remote update fails. |
| Waiting for missing cache blocks | Check producer state promptly after a block read failure and rotate a single online-disk probe per retry before issuing the full quorum read. |
| Cancellation and lock contention | Make lock-acquisition retry waits context-cancelable, and grant positively identified listing-recovery lock conflicts one short 2 ms wait-and-recheck window. |
| Regression tests and CI | Cover confirmed deletion, cross-pool migration ordering, dual-set lock routing, pagination termination, failed RPCs, context cancellation, and late lock grants under `-race`. |

The low-level directory-walk callback keeps its existing signature because recovery errors originate in the merger, leaving scanner, healing, rebalance, and decommission callers unchanged.

When single-pool recovery spans two distinct lock domains, holding the first read lock while acquiring the second can briefly delay `DELETE` or `COPY` operations routed to the first set. Recovery releases all locks before result encoding, channel sends, and cache RPCs so slow clients cannot extend the lock hold time. If the second lock acquisition fails or the context is canceled, the first lock is released immediately.

## Evaluated and Rejected Alternatives {#alternatives}

| Option | Benefit | Reason Rejected |
|---|---|---|
| Keep existing behavior | Zero additional runtime cost | HTTP 200 listings can silently omit live objects, breaking backup and sync tools. |
| Return HTTP 503 on every disagreement | Smallest patch; no metadata re-read | Fails requests that a single re-read can resolve and repeatedly fails after healthy concurrent `DELETE`s. |
| Lock and re-read every listed object | Uniform rule | Imposes per-object lock and disk I/O overhead on all listings, degrading large-bucket scans. |
| Confirm only the source pool or skip locking | Fewer reads and lock acquisitions | Concurrent overwrites, deletions, and cross-pool migrations still produce silent omissions. |
| Shorten retry intervals for all writers globally | Reduces some contention tails | Alters global write scheduling and increases cluster-wide lock RPC traffic. |
| **Confirm eligible disagreements with a bounded short wait (selected)** | Keeps normal scans on the fast path; returns confirmed state or an explicit error | Adds targeted re-read I/O and lock handling on contended entries. |

## Runtime Cost Profile {#cost}

| Trigger | Additional Cost |
|---|---|
| Ordinary listing entry | On 64-bit builds, the in-memory entry struct grows from 56 to 64 bytes (one 8-byte pointer) plus a branch check; zero extra locks or disk reads. |
| Eligible disagreement | Concurrent per-drive metadata re-read across pending source sets; two read-lock acquisitions on single-pool split domains, or one pool-level lock on multi-pool setups. |
| Confirmed source-set absence | Queries each pool's current target set (reusing sets already read), bounded by the deduplicated union of source and target sets rather than a bucket scan. |
| High fraction of unresolved names | The ordered merger confirms same-name groups serially, which slows the overall scan when many keys are simultaneously under mutation. |
| Recovery reader vs. writer lock conflict | Each identified recovery lock RPC waits once for a nominal 2 ms before rechecking, capped at 64 concurrent waiters per local locker outside its internal mutex (~264 B and 4 allocs per waiting RPC). |
| Ordinary backoff after failed lock acquisition | Replacing `time.Sleep` with a cancelable timer/select adds a small allocation only after a lock attempt has already failed. |

For 1,000 simultaneously resident entries, the pointer field adds roughly 8 KiB of heap memory. Each name's recovery runs under a 5-second context budget, and any partial or late lock grants after cancellation are cleaned up immediately.

## Verification and Benchmark Evidence {#validation}

Local `make test` passed all 1,773 top-level tests alongside targeted `-race` suites covering recovery, pagination caches, lock routing, and lock cancellation. On PR commit [`87c1c6b3d`](https://github.com/pgsty/silo/commit/87c1c6b3dc189799912f748572364e319676a7fc), all eight CI checks passed ([Go CI](https://github.com/pgsty/silo/actions/runs/38998274157), [DCO](https://github.com/pgsty/silo/actions/runs/38998274090), [vulnerability analysis](https://github.com/pgsty/silo/actions/runs/38998274173), and the [snapshot pipeline](https://github.com/pgsty/silo/actions/runs/38998490360)).

An independent 10-run paired benchmark against `main` (`7e9454456`)—two identical-`main` A/A controls followed by four alternating `main`/candidate pairs (20 s warmup, 120 s measurement across 8 processes, 2 pools, and 32 logical drive directories on NVMe loopback)—completed 22,410 full scans with zero omissions, duplicates, corruptions, or healthy-state HTTP errors:

| Metric | Paired Candidate / Main p95 Change | 95% Confidence Interval |
|---|---:|---:|
| Full `LIST` page | +0.82% | −3.53% to +5.36% |
| Same-name `DELETE` | −0.38% | −1.80% to +1.05% |
| Different-name `DELETE` | −0.55% | −4.74% to +3.84% |

Secondary paired p95 deltas were +0.47% for complete paginated scans, +2.82% for `PUT`, −0.51% for `GET`, +12.60% for middle continuation pages (`max-keys=7`), and +18.95% for same-name `DELETE` p99 (with one isolated 327.248 ms same-name `DELETE` sample on the candidate vs. 148.186 ms in the A/A control). Aggregate 8-process CPU changed by −0.07% and summed RSS by +0.11%. Because the 95% confidence interval upper bound for full `LIST` page p95 reached +5.36% (above the strict 5.00% gate) and the two identical-`main` controls varied by ~12% on different-name `DELETE` p95, the statistical 5% gate is recorded as **inconclusive** rather than passed, while point estimates confirm minimal steady-state overhead.

Sequential graceful restarts of all 8 processes completed 5,235 successful full scans (4,754 inside the measurement window) with zero omissions, duplicates, or corruptions; all 139 failed HTTP requests fell within the stopped node's stop-to-ready window, and all 80 final object states, pagination checks (`max-keys` of 1, 7, and 1000), 416 present `GET`s, and 512 absent `GET`s matched the last acknowledged write or delete.

## Compatibility {#compatibility}

S3 request parameters, continuation-token encoding, on-disk formats, configuration keys, and client SDK behavior remain unchanged. Entries that enter recovery and cannot be confirmed now fail the `LIST` request with existing S3 error codes (such as `503 SlowDownRead`) rather than returning an incomplete HTTP 200 inventory. Downgrading requires no data migration.
