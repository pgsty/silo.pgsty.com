---
title: "LIST Recovery: Confirm Only Uncertain Names and Bound the Waiting Cost"
linkTitle: "LIST Recovery and Lock Cost"
date: 2026-10-17
lastmod: 2026-10-17
author: "Ruohang Feng"
summary: >
  The final #218 / #239 decision keeps ordinary listings on their fast path, confirms eligible disagreements, distinguishes deletion from failure, covers existing writer lock domains and limits short-conflict waiting. Alternatives, compatibility and verification limits are explicit.
tags: [Design, S3, ListObjects, Performance, Review]
weight: 96
draft: false
url: "/blog/design/listing-recovery-lock-cost/"
---

> **Source merged; no new production release:** [PR #239](https://github.com/pgsty/silo/pull/239) merged into main on 2026-10-17 as [`fbcb51197`](https://github.com/pgsty/silo/commit/fbcb5119782a3ec0f2198fd9f42891a11dc4183f), closing #218 and retaining the original author commits. Merging source does not update installed software.

This is the current design decision for [#218](https://github.com/pgsty/silo/issues/218) and [#239](https://github.com/pgsty/silo/pull/239). It follows the [September null-version quorum repair](/blog/design/list-null-version-quorum/) and supersedes the earlier recovery proposal that called the ordinary GET metadata path directly. #239 retains mr javad seydi's original signed commits from [#221](https://github.com/pgsty/silo/pull/221). Source integration, a production release and deployment are separate deliveries. This page is not a production release announcement.

## A successful directory can be missing a file {#problem}

Suppose `reports/a.csv` can be downloaded with GET, but a LIST returns HTTP 200 without that name. Backup and inventory tools can report a missing file. A synchronization tool configured to delete destination objects absent from the source list can remove a correct destination copy. This does not establish server-side data loss, but a successful incomplete answer can cause more downstream harm than an explicit failure.

LIST combines directory and metadata records collected from different drives at different times. During overwrites, deletion, rolling restarts or pool migration, some records can be old, others new and others temporarily missing. A quorum requires enough mutually compatible evidence; unrelated generations or erasure layouts cannot simply add their votes together. An unresolved directory record could previously be dropped while the overall request still succeeded.

This concerns `ListObjects` and `ListObjectsV2`, for example `GET /bucket?list-type=2&prefix=reports/`. It is separate from #79's `ListMultipartUploads`. The repair introduces no `prefix=true`, environment variable or client parameter.

## The selected design {#decision}

First apply the existing directory merge. Already resolved entries retain their ordinary path. Recovery admits only an unresolved latest-only entry with at least one decodable object record and enough decodable records plus failed reader streams to reach the original listing threshold. Failed streams only justify trying recovery; they never count as proof that the object exists or meets read quorum. Below-threshold inputs and full version-history listings retain their previous behavior. This is a bounded repair, not a claim to eliminate every possible LIST omission.

Carry an eligible unresolved name to the pool merger and confirm its complete same-name group there. Acquire an object read lock to exclude same-name mutations during confirmation, then read current metadata. There are three outcomes:

- **Present:** select current metadata using the object's actual erasure layout and unchanged read quorum. Preserve delete markers until the cross-pool merge can discard older live copies.
- **Deleted:** every configured source-set drive slot must return native `FileNotFound` in this raw read. Check the name's current target set in every pool before omitting the whole group.
- **Unknown:** return the existing failure, such as HTTP 503 `SlowDownRead`, so the client cannot mistake this attempt for a complete successful list. Offline drives, corruption, missing volumes and decode errors do not prove deletion.

A full page can still return before the entire bucket scan finishes. Clients must consume all continuation pages; if any page fails, the preceding pages are not a complete inventory. This preserves streaming pagination's latency and memory advantages.

Why inspect other pools after source absence? Pool A's old directory can contain `a.csv`, while B's earlier directory is empty. A migration then publishes the object in B and removes A's copy. Omitting the name merely because A is now empty would miss B's current object. After strict source absence, current pool results replace the entire stale same-name group. Each distinct set is reread at most once per recovery.

Legitimate DELETE is another concrete case: six of sixteen directory inputs contain old records, six new records and four no record, so the directory cannot resolve quorum. But DELETE has returned 204, GET returns 404 and all sixteen current drive reads say absent. Early #239 turned even this healthy deletion into a 503. The final design confirms deletion while preserving errors for genuinely unknown results.

## What metadata is stored {#metadata}

No persistent file, `xl.meta` field, index or migration is added. One source-set pointer is added to the in-memory entry:

```text
ordinary: name="reports/a.csv", metadata=<existing metadata>, listingSet=nil
pending:  name="reports/a.csv", metadata=nil, listingSet=<source set>
```

Pending state travels only through internal channels and is consumed by the pool merger. Both cache encoders reject unresolved entries. The pointer is never serialized to a pagination cache or client, so older servers need no new field decoder. Disk and wire encodings remain unchanged.

The reread uses a read-only metadata helper and existing version selection and read-quorum rules, avoiding the ordinary GET path's opportunistic repair or dangling cleanup. A separate narrow in-memory recount applies only after original selection fails for eligible latest null versions with known erasure layouts. Compatible groups are counted separately against the original threshold; strict resolution and version histories are not expanded.

## Which code changes, and why {#changes}

| Surface | Necessary change |
|---|---|
| Directory resolution and pool merge | Carry a pending name to the complete same-name group; confirm there to prevent private per-pool decisions from dropping or resurrecting objects |
| Metadata reading | Separate native all-drive absence from errors; reuse version and quorum selection without GET's write side effects |
| Object locking | Use the pool lock for multiple pools; in a single pool with distinct sets, take first-set and target-set read locks in that order to cover existing DELETE/COPY and PUT routing; identical domains require one lock |
| Pagination cache | Publish the terminal scan error before cache completion; an HTTP error need not wait for a failed remote cache update. Keep the original local cache ID and error if that update fails |
| Waiting for missing cache blocks | Check producer state promptly after failure and rotate one online-disk probe per retry; a successful probe still precedes the ordinary quorum read. Healthy reads add no status RPC |
| Cancellation and contention | Allow cancellation to interrupt retry waits; give positively identified listing recovery lock conflicts one short opportunity to resolve |
| Regression tests and CI | Cover legitimate deletion, migration ordering, lock routes, pagination termination, failed RPCs, cancellation and late lock grants under the race detector |

The low-level directory callback keeps its existing signature. Recovery errors now originate in the merger, so scanner, healing, rebalance and decommission callers need no interface change. Ordinary writer lock routing is unchanged.

When single-pool recovery needs two distinct lock domains, holding the first while waiting for the second can temporarily delay first-domain DELETE/COPY calls. Failure to establish either lock quorum fails that name's recovery. This availability and waiting cost applies only to names that actually enter recovery.

Recovery initiates unlock before result encoding, channel sends and cache RPCs. A slow consumer cannot extend this critical section. Distributed unlock notifications can finish asynchronously, so calling unlock is not an exact physical-release timestamp. Failure or cancellation during the second single-pool acquisition releases the first lock; regression tests enforce this cleanup.

## Alternatives and tradeoffs {#alternatives}

| Option | Benefit | Reason not selected |
|---|---|---|
| Keep current behavior | No additional work | Successful omissions remain unsafe inputs to inventory and synchronization |
| Return 503 for every disagreement | Smallest patch; no metadata reread | Rejects recoverable objects and can repeatedly fail on healthy deletion |
| Lock and reread every object | Straightforward rule | Charges all listings for disk and lock work, including large buckets and ordinary writes |
| Confirm only the source pool, or omit locking | Fewer reads or acquisitions | Overwrite, deletion and migration counterexamples still produce omissions |
| Reduce every writer's retry interval | Can lower some tails | Expands the change to global write scheduling and adds lock traffic and contention |
| **Confirm eligible disagreements, with a selective short wait** | Keeps normal requests light; returns confirmed results or explicit uncertainty | Recovery still incurs real I/O and contention and needs more code and verification than unconditional failure |

The last option is selected. Minimality means each behavior change answers a reproduced failure or cost while preserving existing interfaces and fast paths. Patch length alone is insufficient if a smaller patch merely transfers errors to callers.

## Costs, including the uncommon path {#cost}

| Trigger | Additional cost |
|---|---|
| Ordinary listing | On the measured 64-bit build, an entry grows from 56 to 64 bytes: one 8-byte pointer and a few branches; no additional object read lock or metadata reread |
| Eligible disagreement | Read current metadata for pending source sets, concurrently across drives within each set. Single-pool distinct lock domains require two acquisitions; multiple pools use one pool-level acquisition |
| Strict source absence | Inspect each pool's current target set, reusing prior reads. Count the distinct union of source and target sets; this is not a bucket scan |
| Many unresolved names | The ordered merger confirms groups serially. A high recovery fraction can slow the entire scan |
| Recovery-reader/writer conflict | Each eligible lock RPC gets one nominal 2 ms wait and recheck; each local locker shares a cap of 64 admitted waits, outside its internal mutex |
| Ordinary backoff after a failed acquisition | A cancelable timer/select adds a small allocation cost; retry intervals are unchanged and a first-attempt success avoids this cost |

For 1,000 simultaneously resident entries, the field itself adds about 8 KB; it does not create a resident index of the entire bucket. The extra pointer also participates in garbage-collector scanning, so whole-process memory and CPU cannot be inferred from structure size alone.

The short wait is neither a priority queue nor a two-millisecond HTTP limit. Scheduling, networking, subsequent retries and persistent writers can still produce long tails. Identification reuses the existing diagnostic Source field. Unknown or older formats fall back to the ordinary rejection/retry behavior; correctness and wire compatibility do not depend on recognizing it. Measurements found about 264 additional bytes and four allocations per newly waiting RPC, with unchanged ordinary uncontended lock allocations. Cancelable ordinary backoff retains its existing intervals and quorum thresholds.

Ordinary lock acquisition shares the cancellation loop, so this timer cost is not limited to LIST. It applies after an acquisition has failed and needs backoff. Heavy ordinary lock contention also belongs in deployment-specific load assessment.

Each name's recovery has a five-second context budget, not a hard real-time bound on the complete HTTP response. Partial and late lock grants after cancellation still require cleanup; tests check remaining lock records and waiter admissions as well as return values.

## Evidence and its limits {#validation}

The final source integrates current main's IAM and Multipart changes. Regressions check both returned values and mechanism boundaries: no extra read or lock on the ordinary path, no lock held across blocked output, and no serialization of pending state. Mixed-erasure inputs retain differential comparisons with original behavior; version-history and strict resolution retain their contracts.

Local `make test` passed, including verifiers, build and all-package tests: 1,773 top-level passes and 12 inherited skips. Focused race tests also passed for recovery, pagination caches, lock routing, distributed/local lock cancellation and late grants.

At [`87c1c6b3d`](https://github.com/pgsty/silo/commit/87c1c6b3dc189799912f748572364e319676a7fc), all eight PR checks pass, including [Go CI](https://github.com/pgsty/silo/actions/runs/38998274157), [DCO](https://github.com/pgsty/silo/actions/runs/38998274090) and [vulnerability analysis](https://github.com/pgsty/silo/actions/runs/38998274173). The [nonpublishing snapshot pipeline](https://github.com/pgsty/silo/actions/runs/38998490360) also passes; its release command skips publishing, Docker publication and signing.

p95 is the latency at or below which approximately 95% of requests finish. The comparison measures candidate/main ratios under the same test conditions, not an absolute production-latency promise.

The independent current-source comparison against main `7e9454456` completed ten runs: two identical-main controls followed by four alternating main/candidate pairs. Each run had a 20-second warmup and 120-second measurement. Eight processes and two pools used 32 logical drive directories on one NVMe device, loopback networking and a fixed-rate small-object workload. Load phases completed 22,410 full scans with no omissions, duplicates, corrupt contents or healthy-state HTTP failures. No environment or scheduler alerts were recorded.

| Metric | Paired candidate/main p95 change | 95% interval |
|---|---:|---:|
| Full LIST page | +0.82% | −3.53% to +5.36% |
| Same-name DELETE | −0.38% | −1.80% to +1.05% |
| Different-name DELETE | −0.55% | −4.74% to +3.84% |

**The strict statistical target of at most 5% degradation remains unconfirmed.** LIST's upper bound is 5.36%, and the two identical-main controls differ by about 12% for different-name DELETE p95. The overall result is therefore recorded as inconclusive, not as a passed performance gate. Point estimates support small changes in the main steady-state metrics; they do not guarantee a sub-5% change in every scenario. The threshold is unchanged, and no extra runs are added to select a favorable result.

Secondary results are retained: complete paginated-scan p95 was about +0.47%, PUT p95 +2.82%, and GET p95 −0.51%; middle continuation-page p95 at a seven-entry limit was +12.60% and same-name DELETE p99 +18.95%. The candidate also recorded one 327.248 ms same-name DELETE. The four paired baseline runs peaked at 24.153 ms, while the additional A/A baseline controls included a 148.186 ms request. This isolated tail has not been causally attributed; it cannot be described as eliminated. Aggregate eight-process CPU changed by about −0.07% and summed RSS by +0.11% across pairs. Summed RSS counts shared pages repeatedly and is not physical memory consumption.

An initial attempt was stopped by the seed identity check before any candidate measurement: copying a seed-directory symlink had preserved the link. The failed attempt is retained; the original seed was restored from another copy matching the complete original manifest. The results above come from the complete fixed matrix using independent physical directories, without mixing in the failed attempt.

The identical candidate binary completed sequential graceful restarts of all eight processes. Load phases had 5,235 successful full scans, including 4,754 in the measurement window, with no omissions, duplicates or corrupt contents. All 139 failed HTTP attempts fell within their respective endpoint's stop-to-ready window. The 46 failed scan summaries refer to failed page requests and are not counted again. All 80 final object states, pagination through all eight endpoints at limits 1/7/1000, 416 successful final GETs and 512 expected absent GETs matched the last acknowledged mutation. This passes scoped rolling functional acceptance, not uninterrupted availability, and does not change the performance classification above.

The source-merge engineering decision accepts this bounded correctness repair: the main steady-state metrics show small measured changes, ordinary entries add no object I/O or lock, and deterministic tests cover the deletion and lock-domain gaps. Strict performance qualification remains inconclusive and individual tails remain visible. This merge must not be described as completed production performance acceptance.

The earlier frozen candidate's eighteen-run result keeps its original classification. LIST, same-name DELETE and different-name DELETE had paired p95 ratios of about 1.0042, 0.9963 and 0.9966, with all latency confidence-interval upper bounds below 1.05. But one measurement interval had sustained external CPU activity: **the overall performance result remains inconclusive, not a pass**. That candidate's rolling run retained 124 failed HTTP attempts within node-stop/readiness windows and recorded no omissions, duplicates or corrupt contents. It supports scoped functionality and recovery, not uninterrupted rolling availability.

Earlier forced-recovery/same-key-contention experiments improved some DELETE and LIST requests but retained a roughly 303 ms maximum LIST latency, and some PUT tail metrics worsened. The short wait reduces the chance that a short conflict incurs a long retry; it does not eliminate sustained contention. Healthy-path measurements are not fault-path performance guarantees.

Current-source acceptance is kept separate from those historical measurements. Slow samples are not discarded, and measurements of earlier binaries are not relabeled as current-source results. A single host with multiple processes cannot establish cross-host, mixed-version, large-bucket or prolonged-fault production behavior. Natural production recovery frequency is unmeasured. Explicit failure under uncertainty is an intentional availability tradeoff.

## Compatibility and delivery decision {#compatibility}

S3 parameters, continuation-token encoding, storage formats, configuration, dependencies and client calls remain unchanged. No object rewrite or new switch is required. Eligible entries that remain unconfirmed can now fail LIST using existing errors; correcting successful omissions does not promise that every previously successful request still returns 200.

The change does not make an entire bucket a point-in-time snapshot and does not address #79's cancellation race or capacity work. Downgrading needs no data conversion but restores the previous omission risk; in-flight requests and caches retain the existing retry lifecycle.

The decision has been executed: #239 is merged and #218 is closed. The original signed commits from #221 entered main through #239, and GitHub marks #221 merged as well. Unconfirmed strict performance qualification remains part of release assessment, rather than being relabeled as passed. Production releases, image pushes and deployments remain separate actions; merging does not authorize them.
