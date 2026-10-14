---
title: "Governance Retention and Version-Overwrite Repair Design (SN-2026-015 / SN-2026-016)"
linkTitle: "Governance Retention & Version-Overwrite Repair"
date: 2026-10-10
lastmod: 2026-10-14
author: "Vonng"
summary: "Problem origin, minimal-complexity fix design, proof of effectiveness, and compatibility trade-offs for SN-2026-015 (PutObjectRetention authorization bypass) and SN-2026-016 (version-addressed write overwrite)."
tags: [Design, Security, Object Lock, IAM, S3]
weight: 7
draft: false
url: "/blog/design/governance-retention-bypass-repair/"
---

> **Status on 2026-10-14: fix candidate implemented; no fixed release yet.** For public impact and mitigations, see the
> [SN-2026-015 security advisory](/blog/security/20260926-governance-retention-bypass/).
> Fixing commits and the first fixed release will be recorded in the
> [security ledger](/about/security-advisories/).

Following the engineering standard of minimal complexity cost, sufficiency, and necessity, this document explains **SN-2026-015** (`PutObjectRetention` authorization bypass) and **SN-2026-016** (in-place version overwrite via data write paths) across four questions:

1. [What the problem is and where it came from](#problem)
2. [What the solution is](#solution)
3. [Why this solution works](#why-it-works)
4. [What side effects and trade-offs it has](#side-effects)

---

## 1. What the problem is and where it came from {#problem}

The core guarantee of S3 Object Lock is that an object version under unexpired retention (`GOVERNANCE` or `COMPLIANCE`) or `LegalHold` cannot have its data overwritten or deleted, and its retention cannot be shortened, cleared, or downgraded by an unauthorized principal.

We confirmed two distinct classes of defects inherited from upstream MinIO that break this guarantee: one on the retention-metadata path (`SN-2026-015`) and one on the object-data write paths (`SN-2026-016`).

### 1.1 SN-2026-015: `PutObjectRetention` Authorization Bypass (F1–F3) {#sn-2026-015}

#### Symptoms

When a `PutObjectRetention` (`PUT /{bucket}/{object}?retention`) request carries `x-amz-bypass-governance-retention: true`, the server treats that header—which should only express intent—as proof of authorization. Three privilege escalations follow (see the [advisory verification](/blog/security/20260926-governance-retention-bypass/#verification)):

| ID | Caller position and permissions | Unauthorized effect |
| --- | --- | --- |
| **F1** | **Any authenticated principal**, even one with no grant on the bucket or an explicit `Deny` on both `s3:PutObjectRetention` and `s3:BypassGovernanceRetention` | By sending the bypass header with an empty `<Retention/>` body, clears `GOVERNANCE` retention on any version in any lock-enabled bucket; or with `<Mode>COMPLIANCE</Mode>`, converts `GOVERNANCE` to `COMPLIANCE` or locks any unlocked/expired version under `COMPLIANCE` until an arbitrary future date (undeletable even by `root`) |
| **F2** | A principal granted `s3:PutObjectRetention` **without** `s3:BypassGovernanceRetention` (reported in [GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88)) | By sending the bypass header, shortens unexpired `GOVERNANCE` retention to a few seconds ahead, waits for it to expire, and deletes the version with `s3:DeleteObjectVersion` |
| **F3** | A principal granted `s3:BypassGovernanceRetention` | By sending the bypass header, bypasses a conditional `Deny` on `s3:PutObjectRetention` (such as a minimum retention period enforced via `s3:object-lock-remaining-retention-days`) |

#### Historical Origin

1. **Correct structure before April 2020**: `PutObjectRetentionHandler` checked `s3:PutObjectRetention` at handler entry via `checkRequestAuthType`, and pre-evaluated `s3:BypassGovernanceRetention` before passing the **authorization result** into `enforceRetentionBypassForPut`. The raw header only selected the bypass branch; it never replaced policy evaluation.
2. **Defect introduced in 2020-04 (upstream [#9259](https://github.com/minio/minio/pull/9259), [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45))**: To support the three Object Lock policy condition keys (`s3:object-lock-mode`, `s3:object-lock-retain-until-date`, `s3:object-lock-remaining-retention-days`) derived from the XML request body, upstream removed the entry `checkRequestAuthType` call and moved authorization into a new helper `isPutRetentionAllowed` called by `enforceRetentionBypassForPut`, introducing three compounding flaws:
   - In `enforceRetentionBypassForPut`, the shortening/mode-change guard was gated on `if !byPassSet`, where `byPassSet` held the **raw request header** (`IsObjectLockGovernanceBypassSet(r.Header)`). Sending the header skipped the guard unconditionally.
   - In `isPutRetentionAllowed`, `s3:BypassGovernanceRetention` was evaluated only when the **requested mode** was `GOVERNANCE` (`if retMode == objectlock.RetGovernance && byPassSet`). When the requested mode was empty (upstream [#9677](https://github.com/minio/minio/pull/9677) added empty `<Retention/>` to clear retention) or `COMPLIANCE`, `byPassSet` remained `true` from the raw header.
   - `isPutRetentionAllowed` concluded with `if byPassSet || retSet { return ErrNone }`, combining bypass and base retention permission with logical `OR` (`||`).
3. **Partial fix in 2025-02 and mechanical regression in 2025-04**:
   - Upstream [#20929](https://github.com/minio/minio/pull/20929) ([`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32)) re-added `checkRequestAuthType(..., PutObjectRetentionAction, ...)` at handler entry without condition keys, temporarily blocking F1 (while breaking condition-key-dependent `Allow` policies and leaving F2 and F3 open).
   - Fifty days later, upstream [#21103](https://github.com/minio/minio/pull/21103) ([`8c7097528`](https://github.com/minio/minio/commit/8c7097528)) mechanically replaced that entry check with signature-only `authenticateRequest` during a trailer-signature refactor, leaving the old `// Check permissions to perform this object retention operation` comment intact and reopening F1. SILO forked after `#21103` and inherited all three flaws.

---

### 1.2 SN-2026-016: Version-Addressed Write Overwrite and Write-Path Lock Gaps (F4 & Related Paths) {#sn-2026-016}

#### Symptoms

In standard S3, public object write operations (`PutObject`, `CopyObject`, `CreateMultipartUpload`, `PostPolicy`) always generate a fresh version ID in a versioned bucket (or write the `null` version when versioning is suspended); **clients cannot supply a destination `versionId` to overwrite an existing version in place**.

In the inherited implementation, however, a caller holding only ordinary `s3:PutObject` permission (even with explicit `Deny` on `s3:PutObjectRetention`, `s3:BypassGovernanceRetention`, and `s3:DeleteObjectVersion`) can overwrite existing versions and defeat retention through the data write paths:

| Path | Vector | Security impact |
| --- | --- | --- |
| **F4 (Primary: explicit destination `versionId` on writes)** | Supplying an existing `versionId` (UUID or `null`) on `PutObject`, `CopyObject`, `CreateMultipartUpload`, `PostPolicy`, or Snowball archive extraction (PAX `minio.versionId`) | The storage layer **overwrites that version's payload and metadata in place**. If the version is under unexpired `GOVERNANCE` retention, its bytes are replaced; if the bucket has default retention configured or the request carries lock headers, its existing long-term `GOVERNANCE` retention is also replaced or cleared (only unexpired `COMPLIANCE` and `LegalHoldOn` block the write) |
| **Gap A (Implicit `null` version overwrite on directory keys `dir/`)** | Sending an ordinary `PUT /{bucket}/dir/` (without `?versionId=`) to a key ending in `/` in an Object Lock bucket | `putOpts` implicitly maps directory keys to `opts.VersionID = "null"` to overwrite in place, whereas `checkPutObjectLockAllowed` reads `opts` via `getOpts` (where `opts.VersionID` is empty) and skips the existing-lock check. An ordinary `PUT dir/` therefore overwrites a locked `null` directory version in place and erases unexpired `GOVERNANCE` or **even `COMPLIANCE` retention and `LegalHoldOn`** |
| **Gap B (Completing a multipart upload targeting an existing version)** | `NewMultipartUpload` persists `fi.VersionID` in `xl.meta`, and `CompleteMultipartUpload` commits `fi.VersionID` via `completeMultipartOpts` rather than `putOpts` | If a pending upload targeting an existing version was created before the upgrade, or was initiated by a replication principal and completed by an ordinary `s3:PutObject` caller, completion overwrites the existing version without replication trust |

#### Historical Origin

1. **2020-10 client-supplied `versionId` added for replication (upstream [#10598](https://github.com/minio/minio/pull/10598), `RELEASE.2020-10-03`)**: To let active-active bucket replication recreate a source version under its original UUID on the target, `putOpts` in `cmd/object-api-options.go` began accepting `?versionId=` from the request and assigning `opts.VersionID = vid`, **without checking whether the request came from trusted replication (`trustedReplication`)**.
2. **2020-05 Object Lock check assumed public writes always create new versions (upstream [#9513](https://github.com/minio/minio/pull/9513))**: `checkPutObjectLockAllowed` in `cmd/bucket-object-lock.go` only blocked unexpired `COMPLIANCE` and `LegalHoldOn` inside `if opts.VersionID != "" && !replicaTrusted`, ignoring unexpired `GOVERNANCE` retention.
3. **2023-05 directory objects pinned to `nullVersionID` (upstream [#17132](https://github.com/minio/minio/pull/17132), [`1d0211d39`](https://github.com/minio/minio/commit/1d0211d39))**: Upstream forced `opts.VersionID = nullVersionID` for `isDirObject(object)` in `putOpts` and `delOpts` to avoid creating versions or delete markers for folder placeholders, without updating `checkPutObjectLockAllowed`.

---

## 2. What the solution is {#solution}

The fix minimizes complexity by introducing no new authorization subsystem or state machine; instead, it enforces the invariants at the single convergence point of each path.

### 2.1 SN-2026-015 Fix Design (Retention Write Path) {#solution-015}

Three files are touched, with a net reduction in code:

1. **Unconditional entry authorization in `PutObjectRetentionHandler` (`cmd/object-handlers.go`)**
   Immediately after `authenticateRequest` and `ParseObjectRetention(r.Body)`—and **before** `GetBucketInfo`, `globalBucketObjectLockSys.Get`, or `getOpts` reads any bucket or object state—evaluate `s3:PutObjectRetention` with the request-derived lock condition keys:

   ```go
   // Check permissions to perform this object retention operation. The
   // object-lock condition keys come from the request body, so this is
   // decided before any bucket or object state is read.
   if !isRetentionActionAllowed(policy.PutObjectRetentionAction, bucket, object, objRetention, r, reqInfo.Cred, reqInfo.Owner) {
       writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
       return
   }
   ```

2. **State-only weakening rules in `enforceRetentionBypassForPut` and non-negative remaining-days evaluation (`cmd/bucket-object-lock.go`)**
   A single helper `isRetentionActionAllowed` populates `object-lock-mode`, `object-lock-retain-until-date`, and `object-lock-remaining-retention-days` from the parsed request and evaluates `globalIAMSys.IsAllowed`. It also removes the inherited `math.Abs(objRetention.RetainUntilDate.Sub(t).Hours())` calculation: when clearing retention (`<Retention/>`, where `RetainUntilDate` is zero `0001-01-01`), taking the absolute value produced `106,752` days after Go saturated the time difference to a `time.Duration` and allowed clearing retention to bypass `NumericLessThan` minimum-retention `Deny` policies or `NumericGreaterThanEquals` conditional `Allow` policies. Zero or non-future dates now evaluate as `"0"` remaining days. The key is always present: omitting it would let a `NumericLessThan` Deny miss the clear request. Future dates use the difference in Unix seconds, rounded up to whole days with nanosecond precision, rather than `Time.Sub`; dates more than about 292 years away must not saturate and bypass a maximum-retention-days policy. Under the object write lock, `enforceRetentionBypassForPut` enforces only state-dependent transitions:

   ```go
   func enforceRetentionBypassForPut(ctx context.Context, r *http.Request, oi ObjectInfo, objRetention *objectlock.ObjectRetention, cred auth.Credentials, owner bool) error {
       ret := objectlock.GetObjectRetentionMeta(oi.UserDefined)
       if !ret.Mode.Valid() {
           return nil
       }
       t, err := objectlock.UTCNowNTP()
       if err != nil {
           internalLogIf(ctx, err, logger.WarningKind)
           return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
       }
       if ret.RetainUntilDate.Before(t) {
           return nil
       }

       weakens := objRetention.Mode != ret.Mode || objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time)
       if !weakens {
           return nil
       }
       switch ret.Mode {
       case objectlock.RetGovernance:
           if !objectlock.IsObjectLockGovernanceBypassSet(r.Header) {
               return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
           }
           if !isRetentionActionAllowed(policy.BypassGovernanceRetentionAction, oi.Bucket, oi.Name, objRetention, r, cred, owner) {
               return errAuthentication
           }
           return nil
       default:
           return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
       }
   }
   ```

3. **Remove `isPutRetentionAllowed` (`cmd/auth-handler.go`)**
   Delete the flawed helper and its `byPassSet || retSet` logic altogether.

### 2.2 SN-2026-016 Fix Design (Version-Addressed Writes & Write-Path Locks) {#solution-016}

Four surgical changes close the write-path vectors:

1. **Gate caller-supplied `versionId` on `trustedReplication` in `putOpts` (`cmd/object-api-options.go`)**
   Every HTTP write option builder converges on `putOpts`. A 3-line guard rejects any caller-supplied `vid` unless the request has earned replication trust:

   ```go
   vid = strings.TrimSpace(vid)
   // A caller-chosen version ID writes that version in place. Only trusted
   // replication may recreate a source version under its original ID.
   if vid != "" && !trustedReplication {
       return opts, errAuthentication
   }
   ```

2. **Set the outer replication marker on Batch Snowball archive uploads (`cmd/batch-handlers.go`)**
   When both source and target are SILO/MinIO, `BatchJobReplicateV1.writeAsArchive` uploads a Snowball tar archive whose PAX entries carry `minio.versionId`. Because `PutObjectExtractHandler` derives `markerExact` from the outer HTTP request header (`X-Minio-Source-Replication-Request: true`) before computing per-entry `entryTrusted`, `writeAsArchive` sets `ReplicationRequest: true` on the outer `SnowballOptions.Opts`:

   ```go
   opts := minio.SnowballOptions{
       Opts: minio.PutObjectOptions{
           Internal: minio.AdvancedPutOptions{
               ReplicationRequest: true,
           },
       },
       InMemory: *r.Source.Snowball.InMemory,
       Compress: *r.Source.Snowball.Compress,
       SkipErrs: *r.Source.Snowball.SkipErrs,
   }
   ```

3. **Enforce `null`-version Object Lock checks both at preflight and under the object write lock (`cmd/bucket-object-lock.go`, `cmd/erasure-object.go`, `cmd/erasure-multipart.go`, `cmd/erasure-server-pool.go`)**
   - At HTTP preflight, align `checkPutObjectLockAllowed` with `putOpts`/`delOpts` so directory objects check `nullVersionID`, and reject overwriting unexpired `GOVERNANCE` retention alongside `COMPLIANCE` and `LegalHoldOn` (also invoking `checkPutObjectLockAllowed` for directory objects in `PostPolicyBucketHandler` and passing `trustedReplication` in `CompleteMultipartUploadHandler`).
   - At storage commit time—while holding the destination object's `NewNSLock` in `er.putObject`, `er.CopyObject`, and `er.CompleteMultipartUpload`—invoke `checkObjectLockedForOverwrite` (using `replicaObjectInfo` across multi-pool deployments) whenever an untrusted write targets `""` or `nullVersionID`. This closes the TOCTOU window where a concurrent `PutObjectRetention` or `PutObjectLegalHold` locks the `null` version after the handler's preflight read and before the write acquires the object lock. Bucket-lock configuration errors and object-read errors also reject the write; only a confirmed missing version or absent lock permits it. Internal `.minio.sys` storage is excluded because it does not use bucket Object Lock configuration. Cross-pool reads are added for public writes and existing replication reconciliation; an unaddressed trusted replication callback keeps its set-local read so an unrelated unreadable pool does not introduce a new availability dependency.

4. **Prevent untrusted `CompleteMultipartUpload` from overwriting an existing UUID version across versioning transitions (`cmd/erasure-multipart.go`, `cmd/erasure-server-pool.go`)**
   Bucket versioning state can change between `NewMultipartUpload` and `CompleteMultipartUpload` (an ordinary upload initiated before versioning is enabled has `fi.VersionID == ""`, whereas an addressed upload initiated while versioning was enabled retains its target UUID even if versioning is later suspended). Under the object write lock in `CompleteMultipartUpload`, untrusted completions (`!opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement`) are therefore checked based on the persisted `fi.VersionID` rather than gated on `opts.Versioned`:
   - If `fi.VersionID == "" || fi.VersionID == nullVersionID` (writing the `null` version, including ordinary uploads initiated before versioning was enabled): call `checkObjectLockedForOverwrite`, allowing normal in-flight uploads to complete unless the `null` version is locked;
   - Otherwise (`fi.VersionID` is a non-null UUID): regardless of whether versioning is currently `Enabled` or `Suspended`, query `getObjectInfo` (via `replicaObjectInfo` on multi-pool) and reject the completion with `errAuthentication` (`403 AccessDenied`) if that UUID version already exists on disk (as an object version or delete marker).

---

## 3. Why this solution works {#why-it-works}

The effectiveness of the fix rests on three invariants:

### 3.1 Invariant 1: Base permission with request-derived condition keys is decided before reading state (closes F1, F3, and existence leaks)

- **Complete single-point evaluation**: All three Object Lock condition keys depend exclusively on the parsed XML request body and current NTP time, never on stored bucket or object metadata. Evaluating `isRetentionActionAllowed(policy.PutObjectRetentionAction, ...)` immediately after `ParseObjectRetention` is both the earliest possible point and a complete policy evaluation.
- **Eliminates F1, F3, and clear-retention minimum-days bypass**: With `byPassSet || retSet` removed and `s3:object-lock-remaining-retention-days` evaluated as `"0"` when clearing retention (`<Retention/>`), no request lacking `s3:PutObjectRetention`—or matching a conditional `Deny` / failing a conditional `Allow` on `s3:PutObjectRetention`—can ever pass the entry check, regardless of whether the bypass header is present or what `Mode` is requested.
- **Eliminates state probing**: Because authorization runs before `GetBucketInfo`, `globalBucketObjectLockSys.Get`, and `getOpts`, unauthorized callers always receive `403 AccessDenied` and cannot distinguish missing buckets (`404`), unlocked buckets (`400`), or missing versions (`404`).

### 3.2 Invariant 2: Bypass is required if and only if an unexpired stored GOVERNANCE lock is weakened, and requires both intent and authorization (closes F2)

- **Keyed on stored lock state**: Under the object write lock, `enforceRetentionBypassForPut` inspects the stored version's `ret.Mode` and `ret.RetainUntilDate`. Absent or expired locks require no bypass; requests that keep the same mode and do not move the date earlier (`!weakens`) require no bypass either.
- **Conjunction of intent and permission**: When `weakens == true`:
  - Stored `COMPLIANCE` unconditionally returns `ObjectLocked` (HTTP `400 InvalidRequest`);
  - Stored `GOVERNANCE` requires **both** `IsObjectLockGovernanceBypassSet(r.Header)` (otherwise `400 InvalidRequest`) **and** `isRetentionActionAllowed(policy.BypassGovernanceRetentionAction, ...)` (otherwise `403 AccessDenied`).
- This closes F2 while preserving compatibility for clients that attach the bypass header on retention extensions.

### 3.3 Invariant 3: Public data writes cannot replace an existing UUID version or a locked null version (closes F4 and write-path gaps)

The following data-write paths enforce this invariant. Unlocked null versions retain their normal overwrite semantics. Trusted replication and internal data movement retain their existing lock-reconciliation rules:

| Write path | Option convergence & replication trust | Guarantee after fix |
| --- | --- | --- |
| `PutObject` (ordinary PUT, bucket/site replication, single-object batch replication) | Signature verified before `evaluateReplicationTrust` (`X-Minio-Source-Replication-Request: true` + `s3:ReplicateObject`), then `putOptsFromReq` -> `putOpts` | Public callers (including `root`) passing `?versionId=` get `403` in `putOpts`; trusted replication preserves source version IDs |
| `CopyObject` (including metadata copy) | Source version in `srcOpts`; destination version via `copyDstOpts` -> `putOptsFromReq` -> `putOpts` | Copying from a source version creates a new destination version; public destination `?versionId=` gets `403`; trusted replication updates target versions |
| `PostPolicy` (browser POST upload) | Reaches `putOptsFromReq` -> `putOpts` with `trustedReplication == false` | Any destination `versionId` is rejected with `403` |
| `PutObjectExtract` (Snowball / Batch archive replication) | Outer `markerExact` + per-entry `s3:ReplicateObject` yields `entryTrusted` passed to `putOpts`; `writeAsArchive` sets the outer marker | Untrusted archive entries carrying `minio.versionId` get `403`; server `batch replicate` archives preserve version IDs |
| `NewMultipartUpload` / `UploadPart` / `UploadPartCopy` | Initiation and encrypted parts call `putOptsFromReq` -> `putOpts` | Untrusted multipart initiation with `?versionId=` gets `403` |
| `CompleteMultipartUpload` | Uses `completeMultipartOpts` and checks `fi.VersionID` under the object write lock | Ordinary uploads initiated before versioning is enabled complete normally; pre-upgrade or suspended-bucket uploads targeting an existing UUID version are rejected with `403` |
| Directory object `PUT` / `Copy` (`/{bucket}/dir/`) and multipart completion with a persisted null version | Mapped to `nullVersionID` in `putOpts`/`checkPutObjectLockAllowed` and re-verified under the object write lock via `checkObjectLockedForOverwrite` | Unlocked/expired directory objects behave as before; if the `null` version has unexpired `GOVERNANCE`, `COMPLIANCE`, or `LegalHoldOn` (including locks committed after preflight), untrusted overwrites fail with `400 InvalidRequest` (`ObjectLocked`) |

---

## 4. What side effects and trade-offs it has {#side-effects}

Ordinary creation of new versions and permitted retention extensions keep their existing behavior. The following intentional behavioral tightenings should be noted in release and upgrade notes:

1. **Policies granting `s3:BypassGovernanceRetention` without `s3:PutObjectRetention` can no longer write retention (`SN-2026-015`)**
   - **Previous behavior**: Due to `byPassSet || retSet`, a principal with only `s3:BypassGovernanceRetention` could call `PutObjectRetention` by including the bypass header.
   - **New behavior**: Returns `403 AccessDenied`. In AWS S3, `s3:BypassGovernanceRetention` is an additive override permission, never a substitute for `s3:PutObjectRetention`.
2. **Unauthorized `PutObjectRetention` calls return `403` before bucket/object lookup (`SN-2026-015`)**
   - **Previous behavior**: Could return `404 NoSuchBucket` or `400 InvalidBucketObjectLockConfiguration`.
   - **New behavior**: Always returns `403 AccessDenied` at entry.
3. **Clearing retention (`<Retention/>`) evaluates `s3:object-lock-remaining-retention-days` as `"0"` (`SN-2026-015`)**
   - **Previous behavior**: The zero date produced `106,752` days via a saturated `time.Duration` and `math.Abs`, allowing a retention clear to bypass minimum-retention-days policies.
   - **New behavior**: Evaluates as `"0"`, so principals constrained by minimum retention days cannot clear retention to bypass that floor.
4. **Non-replication requests (including `root`) can no longer overwrite a version via `?versionId=` (`SN-2026-016`)**
   - **Previous behavior**: Any caller with `s3:PutObject` (including `root`) could pass `?versionId=<id>` on `PUT`, `CopyObject`, or `NewMultipartUpload` to overwrite that version in place.
   - **New behavior**: Returns `403 AccessDenied` unless the request carries a valid replication marker and `s3:ReplicateObject` permission. Standard S3 has no public version-overwrite API.
5. **Cross-cluster `batch replicate` to a SILO target requires `s3:ReplicateObject` on the target credential (`SN-2026-016`)**
   - **Previous behavior**: A target credential with only `s3:PutObject` had its internal headers stripped, but `putOpts` still accepted `?versionId=` from the query string and silently preserved source version IDs.
   - **New behavior**: Preserving source version IDs requires replication trust on the target (`s3:ReplicateObject`); otherwise the target returns `403 AccessDenied`, matching Bucket Replication requirements.
6. **Locked directory placeholder objects (`dir/`) cannot be overwritten in place until their lock expires (`SN-2026-016`)**
   - **Previous behavior**: Repeated `PUT dir/` calls overwrote the `null` version in place and reset or wiped its lock.
   - **New behavior**: In a bucket with default retention enabled (or when `dir/` has explicit retention or legal hold), overwriting `dir/` while the lock is active returns `400 InvalidRequest` (`ObjectLocked`).
7. **Separate follow-up items (kept out of this patch for minimal scope)**
   - `PostRestoreObjectHandler` (archive restore) updates restore metadata by copying a pre-read metadata map snapshot, which can race with a concurrent retention extension. That archive-restore concurrency issue is independent of `PutObjectRetention` authorization and version-addressed writes, and is tracked separately.
