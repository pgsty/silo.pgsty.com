---
title: "Site Replication State Locks: Snapshot Topology Before Storage I/O and Peer RPCs"
linkTitle: "Site-Replication Lock Snapshots"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  Why holding SiteReplicationSys.RLock() across IAM healing, bucket healing, status collection, and peer hooks deadlocks permanently under Go's sync.RWMutex once a configuration writer queues, and why leaf-only state snapshots are the minimal complete repair.
tags: [Design, Site Replication, Concurrency, Availability]
weight: 10
draft: false
url: "/blog/design/site-replication-lock-snapshots/"
---

This record covers an upstream-inherited concurrency deadlock and map-race family in `SiteReplicationSys` (`cmd/site-replication.go`, `cmd/iam-revision.go`, `cmd/site-replication-metadata.go`), tracked under [#341](https://github.com/pgsty/silo/issues/341).

**Status:** Merged to `main` in [`745fbf043`](https://github.com/pgsty/silo/commit/745fbf04376454a3052afb7204856b90cd394f9b), [`2f228284f`](https://github.com/pgsty/silo/commit/2f228284f31ded34ff34442b239a7e1589caa778), and [`ef6efd312`](https://github.com/pgsty/silo/commit/ef6efd3120737506f9dd706e2c8564647b2c5685); scheduled for the next post-[`20261109`](/blog/release/silo-20261109/) Server release. `SILO Server 20261109` and earlier—as well as upstream MinIO releases since `2022-04-24`—are affected.

## Short Answer {#tldr}

`SiteReplicationSys` embeds a `sync.RWMutex` protecting its in-memory peer configuration (`c.enabled` and `c.state`, including `c.state.Peers`). Inherited from upstream MinIO, background healing routines (`healIAMSystem`, `healBuckets`, `healUsers`, `healPolicies`, `healUserMappings`, `healGroupMappings`, `healSTSUserMappings`, `healIAMDeletions`), status collection (`siteReplicationStatus`), and live mutation hooks (`MakeBucketHook`) acquired `c.RLock()` and held it across local storage reads, peer HTTP RPCs, and helper calls that acquired `c.RLock()` a second time on the same goroutine.

In Go's `sync.RWMutex`, recursive read locking is explicitly forbidden: as soon as any writer (`c.Lock()`—triggered by `loadFromDisk`, `PeerStateUpdateHandler`, `SiteReplicationEdit`, `SiteReplicationAdd`, or resync state updates) arrives and blocks waiting for active readers, **every subsequent `c.RLock()` blocks behind the queued writer**, including a second `c.RLock()` from the goroutine that already holds the first `c.RLock()`. Neither the outer reader nor the queued writer can ever advance, `ctx` cancellation cannot wake a goroutine blocked on `sync.RWMutex`, and every subsequent site-replication hook (`IAMChangeHook`, `BucketMetaHook`, `SiteReplicationInfo`) freezes permanently until process restart. Meanwhile, several peer handlers read or shallow-copied `c.state.Peers` without locking, creating concurrent map read/write panic hazards.

The fix converts `c.RLock()` into a **strict leaf lock**: `cloneState()` and `stateSnapshot()` copy the small `srState` peer topology in memory and release `c.RLock()` *before* performing any storage I/O, network RPC, or helper invocation.

## Classification {#assessment}

| Aspect              | Assessment                                                                                                                                                                                                                               |
| :------------------ | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Nature**          | Recursive `sync.RWMutex.RLock()` deadlock + unguarded `Peers` map reads/shallow copies. Inherited from upstream MinIO.                                                                                                                   |
| **Upstream origin** | Introduced in [`3a6458066`](https://github.com/pgsty/silo/commit/3a6458066331c5c5ed70e41c920fb0046e2e227e) (`2022-04-24`, [minio/minio#14572](https://github.com/minio/minio/pull/14572), *"Add support for site replication healing"*). |
| **Affected scope**  | Any multi-site deployment with site replication enabled (`2+` peer sites), on upstream MinIO since April 2022 and SILO Server `20261109` and earlier. Single-site clusters without site replication do not enter these paths.            |
| **Impact**          | Permanent node-wide freeze of all site-replication hooks, status APIs, IAM sync, and bucket metadata sync until server restart; potential `fatal error: concurrent map read and map write` on peer state edits.                          |
| **Data safety**     | Existing S3 objects remain intact, but IAM/bucket changes stop replicating across sites while deadlocked.                                                                                                                                |
{.wide .expand}

---

## 1. Upstream Provenance and Call-Chain Anatomy {#root-cause}

Upstream commit [`3a6458066`](https://github.com/pgsty/silo/commit/3a6458066331c5c5ed70e41c920fb0046e2e227e) (`2022-04-24`) established a recurring pattern across `cmd/site-replication.go`: acquire `c.RLock(); defer c.RUnlock()` at the top of an orchestration function so `c.enabled` and `c.state.Peers` stay stable throughout a multi-step sync pass, then invoke high-level helpers that also guard `c` with `c.RLock()`.

Auditing every `c.RLock()` call graph in `cmd/site-replication.go`, `cmd/iam-revision.go`, and `cmd/site-replication-metadata.go` identified four distinct re-entrant deadlock chains plus unguarded map sharing:

1. **IAM healing status & sync (`healIAMSystem`):**
   - `healIAMSystem` acquired `c.RLock()` and called `c.siteReplicationStatus(ctx, ...)` -> `c.SiteReplicationMetaInfo(ctx)` -> `c.RLock()` (re-entrant lock #1).
   - Next, `healIAMSystem` called `healUsers`, `healPolicies`, `healUserMappings`, `healGroupMappings`, and `healSTSUserMappings`, each of which held `c.RLock()` while calling `c.IAMChangeHook(...)` -> `c.isEnabled()` / `c.RLock()` (re-entrant lock #2).
   - `healIAMDeletions` (`cmd/iam-revision.go`) likewise held `c.RLock()` across storage scans and peer RPCs.
2. **Bucket healing (`healBuckets`):**
   - `healBuckets` held `c.RLock()` across listing all local and remote buckets and called `c.healBucket(...)`, which called `c.healBucketReplicationConfig(...)` -> `c.RLock()` and `BucketMetaHook` -> `c.RLock()`.
3. **Synchronous bucket creation hook (`MakeBucketHook`):**
   - `MakeBucketHook` acquired `c.RLock()` and called `c.BucketMetaHook(...)` -> `c.RLock()`, blocking client `CreateBucket` requests directly whenever a site-replication config reload or peer update queued `c.Lock()`.
4. **Status collection and peer map races (`siteReplicationStatus`, peer handlers):**
   - `siteReplicationStatus` held `c.RLock()` across concurrent remote peer HTTP status probes *and* local IAM/bucket metadata reads (`SiteReplicationMetaInfo`). Even without re-entrancy, a single slow or unreachable peer held `c.RLock()` for the full HTTP timeout, stalling config writers (`c.Lock()`) and queuing every S3 `MakeBucket` or IAM mutation behind it.
   - `PeerBucketConfigureReplHandler` re-entered `c.RLock()`, while peer state edit paths shallow-copied `srState` (`state := c.state`) and mutated `state.Peers[k] = ...` on the map still referenced by concurrent readers.

### Why Context Cancellation Cannot Break the Deadlock {#why-permanent}

In Go's runtime (`sync/rwmutex.go`), once a goroutine calls `rw.Lock()`, `readerCount` is decremented by `rwmutexMaxReaders` (`1 << 30`), causing all new `rw.RLock()` callers to park on `readerSem` until the writer finishes `rw.Unlock()`. Because Goroutine A already holds `RLock #1` and parks unconditionally on `readerSem` at `RLock #2`, `rw.Lock()` never observes `readerWait == 0`, and `RLock #2` has no `select` on `ctx.Done()`. Deterministic race-enabled tests (`cmd/site-replication-status_test.go`, `cmd/iam-svcacct-replication-snapshot_test.go`) reproduce the permanent hang in milliseconds as soon as a writer contends between `RLock #1` and `RLock #2`.

---

## 2. Solution Design: Why Leaf Snapshots Are Necessary and Sufficient {#fix}

### Evaluated Alternatives {#alternatives}

| Candidate Approach                                       | Why Rejected or Adopted                                                                                                                                                                                                                                                                          |
| :------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Custom re-entrant / reader-preferring RWMutex**     | **Rejected.** Allowing nested readers starves configuration writers (`loadFromDisk`, `PeerStateUpdateHandler`) whenever a multi-minute bucket/IAM heal or slow peer HTTP timeout is running, and masks hidden lock-order inversions with IAM/bucket subsystems.                                  |
| **2. Pass `locked bool` flags down every helper**        | **Rejected.** Error-prone across 20+ cross-file helpers (`cmd/site-replication.go`, `cmd/iam-revision.go`, `cmd/site-replication-metadata.go`), still holds `c.RLock()` across slow network RPCs, and breaks as soon as any future callback invokes `isEnabled()` or `IAMChangeHook`.            |
| **3. Deep-cloned `srState` snapshots (`stateSnapshot`)** | **Adopted (`745fbf043`, `2f228284f`, `ef6efd312`).** `c.RLock()` guards *only* in-memory reads/clones of `c.enabled` and `c.state` (microseconds, zero I/O, zero nested calls). All healing, status probes, storage reads, and peer HTTP calls operate on an immutable value snapshot `srState`. |
{.wide .expand}

### Core Implementation (`cloneState` & `stateSnapshot`) {#implementation}

Commits [`745fbf043`](https://github.com/pgsty/silo/commit/745fbf04376454a3052afb7204856b90cd394f9b), [`2f228284f`](https://github.com/pgsty/silo/commit/2f228284f31ded34ff34442b239a7e1589caa778), and [`ef6efd312`](https://github.com/pgsty/silo/commit/ef6efd3120737506f9dd706e2c8564647b2c5685) enforce a single structural invariant across `SiteReplicationSys`:

1. **Deep-copied topology snapshot (`stateSnapshot` / `cloneState`):**
   `stateSnapshot()` acquires `c.RLock()`, checks `c.enabled`, deep-copies `c.state` (cloning the `Peers` map, `Sites` slice, `Buckets` map, and endpoint slices), and immediately calls `c.RUnlock()`. Typically a deployment has `2`–`8` peer sites, so cloning `srState` copies only a few hundred bytes to a few kilobytes in sub-microsecond time.
2. **Lock-free I/O and RPC execution on `srState`:**
   - `healIAMSystem`, `healUsers`, `healPolicies`, `healUserMappings`, `healGroupMappings`, `healSTSUserMappings`, `healIAMDeletions`, `healBuckets`, `healBucket`, `healBucketReplicationConfig`, `SiteReplicationMetaInfo`, `siteReplicationStatus`, `MakeBucketHook`, `BucketMetaHook`, and `IAMChangeHook` take a snapshot upfront and execute all disk reads, IAM queries, and remote peer RPCs **outside** `c.RLock()`.
   - When `siteReplicationStatus` finishes probing peers against its snapshot, it briefly acquires `c.RLock()` at the end only to merge fresh cached IAM status fields onto a cloned copy of the current peer state—keeping result indexing, credentials, and error attribution strictly bound to the probed snapshot even if peers were added or removed concurrently.
3. **Copy-on-write peer state mutations:**
   Every state edit (`PeerStateUpdateHandler`, `SiteReplicationEdit`, `SiteReplicationRemove`, `loadFromDisk`) clones `c.state` before mutating maps/slices and swaps `c.state` under `c.Lock()`, eliminating all data races between concurrent snapshot readers and configuration writers.

### Why This Is Necessary and Sufficient {#sufficiency}

- **Sufficient:** Because **no** method holding `c.RLock()` or `c.Lock()` now performs storage I/O, network I/O, channel waits, or calls into another subsystem or `SiteReplicationSys` method, lock-order cycles and recursive `RLock()` self-deadlocks are structurally impossible.
- **Necessary:** Leaving even one outer caller holding `c.RLock()` (for example, `healIAMSystem` calling `siteReplicationStatus`, which we caught and closed in [`2f228284f`](https://github.com/pgsty/silo/commit/2f228284f31ded34ff34442b239a7e1589caa778) and [`ef6efd312`](https://github.com/pgsty/silo/commit/ef6efd3120737506f9dd706e2c8564647b2c5685)) was enough for a single concurrent config writer to freeze site replication permanently.

---

## 3. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                                | Engineering Trade-Off                                                                                                                                                                                                                                                                                                                                                                       |
| :------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Point-in-time peer snapshot during in-flight healing** | Because `c.RLock()` is released before peer RPCs begin, an in-flight heal pass or hook that started at $t_0$ finishes dialing the peer list captured at $t_0$ even if an administrator removes or edits a peer at $t_1 > t_0$. A removed peer simply rejects the obsolete replication credential (`403` / connection error), and the next hook or heal pass observes the updated `c.state`. |
| **Per-operation snapshot allocation**                    | Each status query, heal pass, or metadata hook allocates one small `srState` copy (`O(peer count)`). Compared to the disk reads and cross-site HTTPS requests that immediately follow, the allocation cost is negligible (`< 1 µs`) and eliminates multi-second reader blocking on `SiteReplicationSys`.                                                                                    |
| **Rolling upgrade behavior**                             | The fix is purely in-process lock and memory management with zero wire-protocol or `.minio.sys` state-file format changes (`srStateFormatVersion1` is unchanged). Upgraded nodes immediately gain deadlock immunity; upgrade all nodes across all sites so no unpatched node can stall during peer topology updates.                                                                        |
{.wide .expand}

## Verification {#verification}

Regression tests in `cmd/site-replication-status_test.go` and `cmd/iam-svcacct-replication-snapshot_test.go` (executed under `go test -race`) deterministically interleave queued `c.Lock()` writers between snapshot acquisition and every IAM/bucket healing helper, status collector, peer hook, and cancellation path, confirming zero deadlocks and zero data races. See also [Candidate Server Compatibility Notes](/compatibility/server/#candidate-after-20261109) and [IAM Policy Reload Lock Scope (`#251`)](/blog/design/iam-policy-cancellation/).
