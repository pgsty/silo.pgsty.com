---
title: "SN-2026-020: Single-Pool S3 Bulk Delete Cross-Bucket Path Traversal"
linkTitle: "SN-2026-020 · Bulk Delete Traversal"
date: 2026-11-10
author: "Ruohang Feng"
description: "On single-pool deployments, S3 DeleteObjects recorded ObjectNameInvalid for '..' keys but still dispatched them to local drives and cleared the error on completion, enabling cross-bucket version deletion, COMPLIANCE Object Lock bypass, and .minio.sys delete markers."
tags: [Security, S3, Path Containment, Object Lock, WORM, SILO]
weight: 1
draft: false
url: "/blog/security/20261110-bulk-delete-path-traversal/"
---

**Status:** Fixed on `main` ([`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d)); scheduled for the post-[`20261109`](/blog/release/silo-20261109/) Server hotfix release\
**Identifier:** `SN-2026-020` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-020))\
**Severity:** Critical\
**Affected scope:** Single-pool **SILO Server** deployments (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO releases; multi-pool deployments (`2+` pools) are unaffected on SILO `20261026`+\
**Unaffected components:** `silo-console`, `mcli`, `silo-pkg`, and `kes`

On single-pool deployments, `(*erasureServerPools).DeleteObjects` (`cmd/erasure-server-pool.go`) validated every key in an S3 multi-object delete request (`POST /<bucket>?delete`) with `checkDelObjArgs` and stored `ObjectNameInvalid` in `derrs[i]`, but still dispatched the unfiltered slice to the storage pool and overwrote `derrs[i] = nil` whenever a drive reported the target as found. Because local `xlStorage` drives join the object key to the bucket directory via `pathJoin`, keys containing `..` segments resolved outside the request bucket into sibling buckets or `.minio.sys`.

## Summary {#summary}

- **Root cause:** `checkDelObjArgs` rejected `../B/secret` at entry (`derrs[i] = ObjectNameInvalid`), but neither the single-node bulk-lock path nor the distributed single-pool per-set path (`deleteObjectsInSets`) skipped entries with non-nil `derrs[i]`, and the result-merge loop reset `derrs[i] = nil` on disk success.
- **Impact:** A principal holding `s3:DeleteObjectVersion` on an unlocked bucket `A` could permanently delete object versions in another bucket `B`, bypassing `COMPLIANCE` Object Lock retention and legal hold. If bucket `A` had versioning enabled, a principal holding only `s3:DeleteObject` could write delete markers onto objects in bucket `B` or onto `.minio.sys/buckets/B/.metadata.bin`.
- **Provenance:** Inherited from upstream MinIO's 2020 single-zone bulk-delete shortcut ([`bdd094bc3`](https://github.com/pgsty/silo/commit/bdd094bc3)) and 2025 pool-dispatch rewrite ([`079d64c80`](https://github.com/pgsty/silo/commit/079d64c80)). Multi-pool SILO deployments (`2+` pools) were already protected by the `if derrs[i] != nil { continue }` guard added in [`3c82748e1`](https://github.com/pgsty/silo/commit/3c82748e1) (`Server 20261026`).
- **Fix:** Commit [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) partitions out entries with non-nil `derrs[i]` immediately after the `checkDelObjArgs` loop—before namespace locking, metadata lookup, or drive dispatch. Requests whose keys are all valid do not enter the new branch.

---

## 1. Discovery {#discovery}

On October 31, 2026, Denis Babchuk ([`@botdeniska`](https://github.com/botdeniska)) privately reported an Object Lock flaw in `DeleteMultipleObjectsHandler` (`cmd/bucket-handlers.go`), showing that S3 `DeleteObjects` decided whether to enforce version retention and legal hold from the cached `hasLockEnabled` state of the request bucket rather than verifying the target version under the storage write lock. In [SILO Server 20261109](/blog/release/silo-20261109/#authorization), [PR #330](https://github.com/pgsty/silo/pull/330) ([`6ef3a52fc`](https://github.com/pgsty/silo/commit/6ef3a52fc)) routed physical version deletes in Object Lock buckets through the single-object deletion path under the mutation lock.

During post-release verification of `6ef3a52fc` and the private advisory queue, we audited what happens when `hasLockEnabled` is evaluated on an unlocked bucket `A` named in the request URL (`POST /A?delete`) while an `<Object><Key>` in the XML body uses `../B/secret` to address a locked bucket `B`. Testing against `Server 20261026` and `Server 20261109` confirmed that single-pool deployments executed the cross-bucket deletion, and subsequent analysis identified two further variants—cross-bucket delete-marker creation via `s3:DeleteObject` and `.minio.sys` metadata hiding—along with a self-deadlock when a batch contains multiple traversal aliases for the same target. We thank [`@botdeniska`](https://github.com/botdeniska) for the original `DeleteObjects` Object Lock report that prompted this audit.

---

## 2. Provenance and Root Cause {#provenance}

### Request Routing and Handler Authorization {#request-flow}

On single-object S3 operations (`GET /A/key`, `PUT /A/key`, `DELETE /A/key`), the object key is part of the HTTP request URL, where path normalization and generic HTTP middleware reject `..` segments before handler execution.

S3 `DeleteObjects` (`POST /A?delete`) instead carries up to 1,000 `<Key>` elements inside the XML request body:

1. **URL middleware does not inspect the XML body.** Only the bucket name `A` appears in the request URL.
2. **IAM authorization evaluates against bucket `A`.** `DeleteMultipleObjectsHandler` constructs `arn:aws:s3:::A/../B/secret` and checks `s3:DeleteObject` or `s3:DeleteObjectVersion`. Any policy granting delete access on `arn:aws:s3:::A/*` matches the prefix and authorizes the entry.
3. **Bucket-level Object Lock precheck inspects bucket `A`.** `globalBucketObjectLockSys.Get(bucket)` checks whether bucket `A` has Object Lock enabled (`hasLockEnabled`). When bucket `A` is unlocked, the handler bypasses the per-version lock path introduced in `6ef3a52fc` and passes the batch to `erasureServerPools.DeleteObjects`.

### Object-Layer Error Erasure on Single-Pool Paths {#discarded-check}

At the top of `(*erasureServerPools).DeleteObjects` (`cmd/erasure-server-pool.go`), the entry loop validates every object name after directory-object encoding:

```go
for i := range derrs {
    objects[i].ObjectName = encodeDirObject(objects[i].ObjectName)
    ...
    derrs[i] = checkDelObjArgs(ctx, bucket, objects[i].ObjectName)
    objSets.Add(objects[i].ObjectName)
}
```

For `../B/secret`, `checkDelObjArgs` (via `hasBadPathComponent`) returns `ObjectNameInvalid` and records it in `derrs[i]`. On a single-pool deployment, three subsequent steps nullified that check:

1. **Unfiltered dispatch:** Neither the single-node bulk-lock branch nor the distributed single-pool per-set branch (`deleteObjectsInSets`) skipped entries where `derrs[i] != nil`. The full `objects` slice was passed to the pool.
2. **Path joining on local drives:** Local `xlStorage` drives store each bucket as a subdirectory under the drive root (`/data/A`, `/data/B`, `/data/.minio.sys`). Inside `xlStorage.deleteVersions`, `pathJoin(volumeDir, path)` runs `path.Clean` on `/data/A` + `../B/secret`, resolving to `/data/B/secret` and removing the version or writing a delete marker in `xl.meta`.
3. **Error reset during result merge:** When merging per-pool results, `erasureServerPools.DeleteObjects` cleared `derrs[i]` whenever a pool reported the entry found without a drive error:

```go
if dErrsByPool[pool][j] == nil && dObjectsByPool[pool][j].found {
    // A fast exit when the object is found and removed
    dobjects[i] = dObjectsByPool[pool][j]
    derrs[i] = nil
    break
}
```

Because `/data/B/secret` existed on disk and the local drive completed the operation (`found == true`, `err == nil`), `derrs[i] = nil` overwrote the initial `ObjectNameInvalid` error and returned `<Deleted>` with HTTP `200 OK`. In `deleteObjectsInSets`, per-set drive results similarly overwrote `derrs[idx]` directly.

### Upstream Git History {#upstream-history}

Tracing `cmd/xl-zones.go`, `cmd/erasure-server-sets.go`, and `cmd/erasure-server-pool.go` shows how this behavior evolved in upstream `minio/minio`:

| Date    | Commit                                                                        | Origin                  | Change                                                                                                                                                             |
| :------ | :---------------------------------------------------------------------------- | :---------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2020-02 | [`ab7d3cd50`](https://github.com/pgsty/silo/commit/ab7d3cd50) (`minio#8974`)  | Upstream MinIO          | Replaced per-object lock loops (which skipped `derrs[i] != nil`) with a bulk lock and passed the unfiltered `objects` slice to zones                               |
| 2020-11 | [`bdd094bc3`](https://github.com/pgsty/silo/commit/bdd094bc3) (`minio#10994`) | Upstream MinIO          | Added `if z.SingleZone() { return z.serverSets[0].DeleteObjects(...) }`, discarding `derrs` entirely on single-pool deployments                                    |
| 2025-01 | [`079d64c80`](https://github.com/pgsty/silo/commit/079d64c80) (`minio#20821`) | Upstream MinIO          | Unified pool dispatch and set `derrs[i] = nil` in the merge loop whenever any pool reported `found && err == nil`                                                  |
| 2026-10 | [`3c82748e1`](https://github.com/pgsty/silo/commit/3c82748e1)                 | PGSTY SILO (`20261026`) | Added `if derrs[i] != nil { continue }` inside the `!z.SinglePool()` multi-pool branch, protecting `2+`-pool deployments while leaving single-pool paths unchanged |
{.wide .expand}

---

## 3. Trigger Conditions {#triggers}

Exploitation requires all three conditions:

1. **Single-pool topology:** The deployment has a single server pool (`z.SinglePool() == true`), including single-node single-drive, single-node multi-drive erasure, and distributed multi-node clusters with one pool. Multi-pool deployments (`2+` server pools) on `Server 20261026`+ skip entries with `derrs[i] != nil` and are not affected.
2. **Delete permission on at least one bucket:** The caller holds credentials (or a presigned `POST /<bucket>?delete` URL) granted `s3:DeleteObject` or `s3:DeleteObjectVersion` on any bucket `A`.
3. **Relative `..` path segment in the XML body:** The `DeleteObjects` XML body contains a `<Key>` that retains a `..` segment after `encodeDirObject` (for example, `../B/secret` or `a/../../.minio.sys/buckets/B/.metadata.bin`).

---

## 4. Impact Scope {#impact}

Reproduction against single-node single-drive and single-node 16-drive erasure instances using a principal restricted to `arn:aws:s3:::A/*` confirmed four behaviors:

| Request Bucket `A`                  | Permission on `A`                  | XML Request Entry                                                                    | Observed Result                                                                                                                                                                                                                |
| :---------------------------------- | :--------------------------------- | :----------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Unlocked (versioned or unversioned) | `s3:DeleteObjectVersion`           | `<Key>../B/secret</Key>` + `<VersionId>v1</VersionId>` (`B` under `COMPLIANCE` lock) | Version `v1` in bucket `B` is permanently deleted from disk despite active `COMPLIANCE` retention                                                                                                                              |
| Versioning enabled                  | `s3:DeleteObject` (no `VersionId`) | `<Key>../B/doc</Key>` (no `<VersionId>`)                                             | A delete marker is appended to `B/doc`; subsequent `GET`/`HEAD` requests return `404 Object not found`                                                                                                                         |
| Versioning enabled                  | `s3:DeleteObject` (no `VersionId`) | `<Key>../.minio.sys/buckets/B/.metadata.bin</Key>`                                   | A delete marker is appended to bucket `B`'s metadata object in `.minio.sys` (IAM records and server configuration share the same `.minio.sys` storage mechanism)                                                               |
| Versioning disabled                 | `s3:DeleteObject`                  | `<Key>../B/small</Key>` (single-version inline object)                               | Response reports `Deleted`, but `xlStorage.deleteFile`'s `strings.HasPrefix` base-path check returns early before unlinking `xl.meta` (unless `B` starts with `A` as a string prefix or the version has an external `dataDir`) |
{.wide .expand}

### Operational Considerations {#amplifiers}

1. **Delete-marker creation requires neither `s3:DeleteObjectVersion` nor a `versionId`:** `DeleteMultipleObjectsHandler` sets `opts.Versioned` from the versioning configuration of request bucket `A`. When `A` is versioned and `<VersionId>` is omitted, `xlStorage.deleteVersions` appends a delete marker to the target's `xl.meta` via `WriteAll` without entering `deleteFile`.
2. **Single-node vs. distributed single-pool deployments:**
   - **Single-node:** All drives are local `xlStorage` instances without internode RPC guards, so a single request reaches write quorum and completes immediately.
   - **Distributed single-pool:** Remote drives are wrapped by `guardedStorage` ([`SN-2026-002`](/blog/security/internode-path-containment/), `cmd/storage-rest-server-guard.go`), which rejects `..` paths with `errInvalidArgument`. A single request therefore fails write quorum on remote drives, **but still executes on every local drive attached to the handling node**. Repeating the request across enough nodes can corrupt local shards on each node until damaged drives exceed erasure parity.
3. **Cross-bucket lock acquisition and self-deadlock:** `NewNSLock` normalizes paths before acquiring namespace locks, so `../B/secret` acquires the write lock on bucket `B`'s object. If a single request contains two distinct traversal aliases that normalize to the same target (such as `../B/secret` and `x/../../B/secret`), the single-node bulk lock—which locks keys sequentially while holding earlier locks—blocks waiting for the lock it already holds until `globalOperationTimeout` expires.

---

## 5. Fix: Sufficiency and Necessity {#fix}

Commit [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) adds a 22-line filter immediately after the `checkDelObjArgs` loop in `(*erasureServerPools).DeleteObjects` (`cmd/erasure-server-pool.go`):

```go
if slices.ContainsFunc(derrs, func(err error) bool { return err != nil }) {
    valid, at := make([]ObjectToDelete, 0, len(objects)), make([]int, 0, len(objects))
    for i, obj := range objects {
        if derrs[i] == nil {
            valid, at = append(valid, obj), append(at, i)
        }
    }
    if len(valid) > 0 {
        deleted, errs := z.DeleteObjects(ctx, bucket, valid, opts)
        for j, i := range at {
            dobjects[i], derrs[i] = deleted[j], errs[j]
        }
    }
    return dobjects, derrs
}
```

### Why the Fix Is Necessary and Sufficient {#sufficient}

1. **Single chokepoint before locking and storage dispatch:** Filtering immediately after `checkDelObjArgs` precedes `deleteObjectsInSets`, `multiDeleteLock.GetLock`, metadata lookups, and pool fan-out. It covers single-node bulk locks, distributed single-pool per-set locks, and multi-pool deployments in one place across all `ObjectLayer.DeleteObjects` callers.
2. **Prevents cross-bucket locking and alias self-deadlocks:** Entries that fail `checkDelObjArgs` return before `NewNSLock` is called, so invalid keys never lock objects in other buckets or deadlock a batch against itself.
3. **Consistent path validation predicate:** `checkDelObjArgs` uses `hasBadPathComponent`, matching `DeleteObject`, `PutObject`, `GetObject`, HTTP query guards, and `SN-2026-002`'s internode `guardedStorage`. Once `hasBadPathComponent` passes, `pathJoin` (`path.Clean`) folds leading slashes under `<drive>/<bucket>/` and has no `..` segments to escape `<drive>/<bucket>/`. Code review across lifecycle expiry, batch jobs, replication, healing, and `deleteObjectsReconciled` confirmed no other client-controlled delete path bypasses `check*Args`.
4. **Bounded recursion and index preservation:** Because `encodeDirObject` is idempotent and every entry in `valid` has already passed `checkDelObjArgs`, the recursive `z.DeleteObjects` call never re-enters the error branch, processes valid sibling entries (including `dir/` directory objects) normally, and maps results back to their original indices via `at`.

---

## 6. Design Trade-Offs {#tradeoffs}

| Option                                                                                 | Benefit                                                                                              | Cost / Risk                                                                                                                                                        | Decision               |
| :------------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------- |
| **Filter after `checkDelObjArgs` in `erasureServerPools.DeleteObjects` (`a18293d0c`)** | Covers all topologies, lock paths, and callers in 22 lines; zero allocations when all keys are valid | Invalid keys on single-pool deployments now return `XMinioInvalidObjectName` instead of `Deleted`                                                                  | **Adopted**            |
| **Add `checkObjectArgs` in `DeleteMultipleObjectsHandler`**                            | Rejects invalid keys in the HTTP handler                                                             | Redundant once the object layer refuses them; **`checkObjectArgs` rejects trailing slashes and breaks valid `dir/` batch deletes**                                 | **Rejected**           |
| **Add path-containment guards to local `xlStorage` methods in this hotfix**            | Adds storage-layer defense in depth                                                                  | Guarding only two delete methods is asymmetric across `StorageAPI`, while wrapping all local calls touches hot erasure I/O paths and widens the regression surface | **Tracked separately** |
{.wide .expand}

### Implementation Notes and Behavioral Changes {#nuances}

- **Directory objects (`dir/` and `../`):** `encodeDirObject` runs before `checkDelObjArgs` and rewrites trailing slashes into `__XLDIR__` (`dir/` becomes `dir__XLDIR__`, and `../` becomes `..__XLDIR__`). `dir/` continues to delete directory objects normally, while `..__XLDIR__` contains no `..` path segment and resolves to a literal name inside the request bucket without traversing upward.
- **Zero fast-path overhead:** When all keys in a request are valid, `slices.ContainsFunc` scans `derrs` without allocating or branching.
- **Windows path normalization (`.. .`):** During code review, we evaluated whether an intermediate segment such as `.. .` on Windows could pass `hasBadPathComponent` and normalize to `..`. Under Microsoft's *File path formats on Windows systems* rules, Win32 evaluates `.` and `..` segments before stripping a single trailing period from intermediate segments, does not strip trailing spaces from intermediate segments, and does not re-evaluate `..` after trimming, leaving `.. ` as a literal directory name inside the bucket. Because `hasBadPathComponent` is shared across all S3 APIs and automated CI runs on Linux, standalone verification on Windows hosts is tracked separately from this hotfix.
- **API response change:** On single-pool deployments, `DeleteObjects` entries whose post-directory-encoding name fails `checkDelObjArgs` now return per-entry `XMinioInvalidObjectName` in `<Error>` rather than `<Deleted>`, matching single-object `DELETE` and multi-pool deployments.

---

## Remediation and Mitigation {#remediation}

1. **Upgrade SILO Server** on single-pool deployments to the post-`20261109` hotfix release containing [`a18293d0c`](https://github.com/pgsty/silo/commit/a18293d0c309b93fe9c69f45ed8f44fe558fe01d) (or build from `main` at `a18293d0c` or later). Updating `silo-console` or `mcli` alone does not remediate the server issue.
2. **Temporary mitigation prior to upgrade:** No configuration toggle disables this code path on unpatched single-pool servers. Until upgraded, revoke `s3:DeleteObject` and `s3:DeleteObjectVersion` from untrusted principals on single-pool deployments, or isolate untrusted tenants onto separate instances. Multi-pool deployments (`2+` server pools) on [SILO Server 20261026](/blog/release/silo-20261026/) or [20261109](/blog/release/silo-20261109/) are unaffected.
3. **Post-upgrade audit:** Where untrusted principals held delete permissions on a versioned bucket in an unpatched single-pool deployment, check buckets (`mcli ls --versions`) and `.minio.sys/buckets/<bucket>/.metadata.bin` for unexpected delete markers.

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-020), [SN-2026-002 Internode Path Containment](/blog/security/internode-path-containment/), and the [Component Version Matrix](/compatibility/versions/).
