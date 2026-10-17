---
title: "Object Lock Retention Bypass and Version-Overwrite Repair Design (SN-2026-015 / SN-2026-016)"
date: 2026-10-14
lastmod: 2026-10-15
summary: "Report verification, Git provenance, entry and write-lock defense-in-depth design, fail-closed preflight hardening, and adversarial trade-off evaluation for SN-2026-015 and SN-2026-016."
tags: ["Silo", "Security", "Object Lock", "WORM", "S3", "IAM"]
---

> [!WARNING]
> **Release-status correction (2026-10-17):** SILO `RELEASE.2026-10-15T00-00-00Z` was returned to Draft and is not the current public release; the published Server remains 20260916. Historical statements below that 20261015 is published or downloadable are superseded, and its fixes must not be treated as delivered in a public release. 20261018 is being prepared as a tag and draft only. See the [component matrix](/compatibility/versions/) and [download page](/download/).

**Status on 2026-10-15:** The complete repair in [PR #234](https://github.com/pgsty/silo/pull/234) (`14042b5aa`) and [PR #235](https://github.com/pgsty/silo/pull/235) (`0d3ba5d4c`) first shipped in [RELEASE.2026-10-15T00-00-00Z](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-10-15T00-00-00Z). The previously published `RELEASE.2026-09-16T00-00-00Z` remains affected. See the [advisory](/blog/security/20260926-governance-retention-bypass/) and [release notes](/blog/release/silo-20261015/) for upgrade requirements and artifact acceptance.

This document records the verification, Git provenance, repair design, critical-path evaluation, and adversarial candidate trade-offs for two Object Lock (WORM) security vulnerabilities identified through external reports and an internal write-path audit: **`SN-2026-015` (`PutObjectRetention` bypass header authorization and condition-key short-circuit)** and **`SN-2026-016` (version-addressed write overwrite bypass and write-path lock gaps)**.

Companion public security advisory:
- [SN-2026-015 / SN-2026-016: Object Lock Retention Authorization Bypass and Versioned Write Overwrite](/blog/security/20260926-governance-retention-bypass/)

---

## 1. Problem Verification and External Report Cross-Check {#problem}

### 1.1 Two Independent External Reports and Internal Audit

This repair addresses two independent external vulnerability reports alongside an internal audit of adjacent write paths:

1. **Initial Report (F2 primary path)**: Privately reported by security researcher **szopi00** via GitHub Security Advisory ([GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88)), showing that a principal holding `s3:PutObjectRetention` without `s3:BypassGovernanceRetention` could shorten unexpired `GOVERNANCE` retention by sending `x-amz-bypass-governance-retention: true`.
2. **Independent External Report (F1 / F2 / F3)**: A separate external report independently reproduced three attack paths: unauthorized changes from `GOVERNANCE` to multi-year `COMPLIANCE`, bypasses of request-body condition-key `Deny` policies on `s3:PutObjectRetention`, and shortening unexpired `GOVERNANCE` retention without bypass authorization.
3. **Internal Companion Audit (`SN-2026-016` / F4 and directory `null`-version overwrites)**: Auditing all write paths for callers holding `s3:PutObject` without bypass permission uncovered three related gaps: in-place overwrites via `?versionId=` without replication trust (`putOpts`), implicit `null`-version overwrites on directory keys (`dir/`), and completion of persisted multipart uploads (`CompleteMultipartUpload`).

### 1.2 Claim-by-Claim Verification of the Independent Report

The following findings and line numbers refer to the pre-fix [`bcb5fc956`](https://github.com/pgsty/silo/commit/bcb5fc956) snapshot:

| Reported Claim | Verification | Code Evidence & Impact |
| --- | --- | --- |
| **Impact 1 (Unauthorized COMPLIANCE retention)**: Attackers without `s3:BypassGovernanceRetention` (or subject to a conditional `Deny`) can turn `GOVERNANCE` into `COMPLIANCE` or set `COMPLIANCE` directly | **Confirmed** | `cmd/bucket-object-lock.go:205` checks only the raw header `!byPassSet`; `cmd/auth-handler.go:773-781` skips IAM evaluation when the requested mode is `COMPLIANCE`, leaving `byPassSet == true` and returning `ErrNone` at `if byPassSet \|\| retSet`. Under `COMPLIANCE`, not even the S3 `root` account can delete the version through the S3 API before expiry |
| **Impact 2 (Weakening GOVERNANCE lock)**: A credential without `s3:BypassGovernanceRetention` can shorten a `GOVERNANCE` lock using the raw header | **Confirmed** | When the requested mode is `GOVERNANCE`, `isPutRetentionAllowed` evaluates `byPassSet` as `false` but evaluates `retSet` (`s3:PutObjectRetention`) as `true`; `byPassSet \|\| retSet` still returns `ErrNone` |
| **Blast-radius difference between SILO and upstream MinIO on `DeleteObjectVersion`**: SILO requires explicit `s3:DeleteObjectVersion` to delete a specific version; upstream MinIO checks `s3:DeleteObjectVersion` with `DenyOnly: true` | **Confirmed** | SILO commit [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) (2026-09-02) introduced `deleteObjectAction` requiring `s3:DeleteObjectVersion`, whereas upstream MinIO's `cmd/auth-handler.go` still uses `DenyOnly: true` |
| **Affected versions and locations**: Bug is in server `cmd/`, not `silo-pkg`; affects SILO `RELEASE.2026-09-03T13-18-01Z` ([`9b11dc94`](https://github.com/pgsty/silo/commit/9b11dc94)), `RELEASE.2026-09-16T00-00-00Z`, pre-fix SILO `main` (`bcb5fc956`), and the upstream `minio/minio` snapshot checked at that time | **Confirmed** | `silo-pkg` evaluates policy `Deny` rules accurately; the flaw is in `cmd/object-handlers.go`, `cmd/bucket-object-lock.go`, and `cmd/auth-handler.go` |
| **Why unconditional `Deny s3:PutObjectRetention` cannot be used as a workaround**: Unconditionally denying `s3:PutObjectRetention` breaks uploads using retention headers or default-retention workflows | **Confirmed** | Application credentials often require `s3:PutObjectRetention` with condition keys (`s3:object-lock-mode`, `s3:object-lock-remaining-retention-days`) rather than an unconditional `Deny` |

---

## 2. Vulnerability Breakdown and Git Provenance {#provenance}

### 2.1 SN-2026-015: `PutObjectRetention` Authorization Short-Circuit (F1 / F2 / F3) {#sn-2026-015}

Before the fix, `PUT /{bucket}/{object}?retention` suffered from two structural defects:
1. **Signature-only check at handler entry**: `PutObjectRetentionHandler` called `authenticateRequest(ctx, r, policy.PutObjectRetentionAction)`, which verifies request authentication (signature/token) without evaluating IAM policies;
2. **Conflated bypass check and inverted boolean logic**: Inside `enforceRetentionBypassForPut` and `isPutRetentionAllowed`, the server trusted the raw header `x-amz-bypass-governance-retention: true` and combined bypass permission with base retention permission using logical OR (`byPassSet || retSet`).

This produced three distinct authorization failures (F1–F3) plus a day-count arithmetic bug when clearing retention:

| ID | Attacker's Granted Permissions | Trigger & Security Impact |
| --- | --- | --- |
| **F1** | Authenticated principal with **no Object Lock permissions at all** (neither `s3:PutObjectRetention` nor `s3:BypassGovernanceRetention`) | Sending `x-amz-bypass-governance-retention: true` with: (1) an empty `<Retention/>` body **clears unexpired `GOVERNANCE` retention to zero**; or (2) `<Mode>COMPLIANCE</Mode>` **locks the version into `COMPLIANCE`** |
| **F2** | Principal with `s3:PutObjectRetention` but **without** `s3:BypassGovernanceRetention` (covered by both external reports) | Sending `x-amz-bypass-governance-retention: true` shortens unexpired `GOVERNANCE` retention or converts it to `COMPLIANCE` |
| **F3** | Principal with `s3:PutObjectRetention` (subject to conditional `Deny`) or with `s3:BypassGovernanceRetention` | (1) When the requested mode is `COMPLIANCE` or empty `<Retention/>`, the raw bypass header skips IAM evaluation in `isPutRetentionAllowed`, **bypassing any conditional `Deny` on `s3:PutObjectRetention`**; (2) when holding `s3:BypassGovernanceRetention`, `byPassSet \|\| retSet` bypasses conditional `Deny` rules on `s3:PutObjectRetention` even for `GOVERNANCE` mode |
| **Day-Count Arithmetic Bug** | Principal subject to `s3:object-lock-remaining-retention-days` conditions | Sending an empty `<Retention/>` body sets `RetainUntilDate` to zero time (`0001-01-01`). `math.Abs(objRetention.RetainUntilDate.Sub(t).Hours())` clamped at Go's 292-year `time.Duration` limit and evaluated to **`106,752` days**, bypassing `NumericLessThan` minimum-retention policies |

#### Exact Git Commit Provenance

1. **Correct initial design (Nov 2019 – Mar 2020)**:
   - [`ca96560d5`](https://github.com/minio/minio/commit/ca96560d5) (2019-11-20, Poorna Krishnamoorthy), [`f931fc7bf`](https://github.com/minio/minio/commit/f931fc7bf) (2019-11-25), and [#9030](https://github.com/minio/minio/pull/9030) ([`97cbac604`](https://github.com/minio/minio/commit/97cbac604), 2020-03-04): `PutObjectRetentionHandler` enforced `checkRequestAuthType` for `s3:PutObjectRetention` at entry and evaluated `s3:BypassGovernanceRetention` via IAM before passing the **authorization boolean** into `enforceRetentionBypassForPut`.
2. **Defect introduction (Apr 2020 — upstream [#9259](https://github.com/minio/minio/pull/9259), [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45), 2020-04-06, Harshavardhana)**:
   - To support the three XML body condition keys (`s3:object-lock-mode`, `s3:object-lock-retain-until-date`, `s3:object-lock-remaining-retention-days`), this commit removed `checkRequestAuthType` at handler entry and pushed policy evaluation into `isPutRetentionAllowed` inside `enforceRetentionBypassForPut`, introducing three bugs at once:
     - `enforceRetentionBypassForPut` checked the raw header `if !byPassSet`;
     - `isPutRetentionAllowed` only evaluated IAM when `retMode == objectlock.RetGovernance && byPassSet`, leaving `byPassSet == true` for `COMPLIANCE`;
     - `isPutRetentionAllowed` concluded with `if byPassSet || retSet { return ErrNone }`.
3. **Expansion to empty `<Retention/>` clear requests (May 2020 — upstream [#9677](https://github.com/minio/minio/pull/9677), [`bede525dc`](https://github.com/minio/minio/commit/bede525dc), 2020-05-22, Ashish Kumar Sinha)**:
   - Allowed clearing `GOVERNANCE` retention via an empty `<Retention/>` body (`Mode == ""`), which also took the `retMode != RetGovernance` branch and introduced the `106,752`-day zero-date calculation bug.
4. **Partial fix in Feb 2025 and mechanical regression in Apr 2025**:
   - Upstream [#20929](https://github.com/minio/minio/pull/20929) ([`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32), 2025-02-12, Ramon de Klein) added an unconditional `checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object)` at handler entry, masking F1 (while breaking condition-key `Allow` policies and leaving F2/F3 open).
   - Just 50 days later, upstream [#21103](https://github.com/minio/minio/pull/21103) ([`8c7097528`](https://github.com/minio/minio/commit/8c7097528), 2025-04-03, Harshavardhana) mechanically replaced `checkRequestAuthType` with signature-only `authenticateRequest` while keeping the stale `// Check permissions to perform this object retention operation` comment, reopening F1. SILO forked after this commit and inherited all three flaws.

---

### 2.2 SN-2026-016: Version-Addressed Write Overwrite Bypass and Write-Path Lock Gaps {#sn-2026-016}

In standard S3 semantics, public write APIs (`PutObject`, `CopyObject`, `CreateMultipartUpload`, `PostPolicy`) never allow callers to specify a target `versionId` to overwrite an existing version in place. Three related write-path flaws broke this invariant:

| Path ID | Trigger | Security Impact |
| --- | --- | --- |
| **F4 (Explicit target `versionId` on write)** | A caller with `s3:PutObject` passes an existing version's `versionId` (UUID or `null`) to `PutObject`, `CopyObject`, `CreateMultipartUpload`, `PostPolicy`, or Snowball archive extraction (PAX `minio.versionId`) | The storage layer **overwrites that version's payload and metadata in place**. For an unexpired `GOVERNANCE`-locked version, its payload and retention metadata are replaced or cleared |
| **Companion Gap A (Implicit `null` version on directory keys `dir/` and slow-body TOCTOU race)** | A caller sends a normal `PUT /{bucket}/dir/` (without `?versionId=`) to an Object Lock bucket | (1) `putOpts` maps `isDirObject(object)` to `opts.VersionID = "null"`, while `checkPutObjectLockAllowed` sees `opts.VersionID == ""` via `getOpts`, skipping the existing-lock check and allowing a normal `PUT dir/` to overwrite and erase unexpired `GOVERNANCE`, **`COMPLIANCE`, and `LegalHoldOn`** locks on the directory object; (2) even with HTTP preflight fixed, preflight runs before reading `r.Body`, so a writer can pass preflight, pause streaming the HTTP body while an admin sets `COMPLIANCE` on `dir/`, and then finish streaming to overwrite the locked `null` version; (3) `checkPutObjectLockAllowed` only inspects locks when `getObjectInfoFn` returns `err == nil`, failing open on storage read errors |
| **Companion Gap B (Persisted target version in `CompleteMultipartUpload`)** | `NewMultipartUpload` persists `fi.VersionID` in `.minio.sys/multipart/.../uploadID/xl.meta`, and `CompleteMultipartUpload` uses `completeMultipartOpts` rather than `putOpts` | A multipart upload initiated before the upgrade, initiated by a replication credential, or recovered from an older staging snapshot after a surviving replica has already committed and `COMPLIANCE`-locked that same UUID version has its target `fi.VersionID` persisted on disk; without an unconditional write-lock existence check during `CompleteMultipartUpload`, an ordinary `s3:PutObject` caller can complete that upload and overwrite the `COMPLIANCE`-locked version |

#### Exact Git Commit Provenance

1. **May 2020 — `GOVERNANCE` omitted from `checkPutObjectLockAllowed` (upstream [#9513](https://github.com/minio/minio/pull/9513), [`9b3b04ece`](https://github.com/minio/minio/commit/9b3b04ece), 2020-05-04)**: `checkPutObjectLockAllowed` only blocked unexpired `COMPLIANCE` and `LegalHoldOn` in `if opts.VersionID != "" && !replicaTrusted`, omitting `GOVERNANCE` and ignoring non-`nil` errors from `getObjectInfoFn`.
2. **Sep 2020 — Unauthenticated `?versionId=` accepted in `putOpts` (upstream [#10598](https://github.com/minio/minio/pull/10598), [`56d1b227c`](https://github.com/minio/minio/commit/56d1b227c), 2020-09-30, Poorna Krishnamoorthy)**: `putOpts` accepted `?versionId=` from the query string to support replication without checking `trustedReplication`.
3. **May 2023 — Directory objects forced to `nullVersionID` (upstream [#17132](https://github.com/minio/minio/pull/17132), [`1d0211d39`](https://github.com/minio/minio/commit/1d0211d39), 2023-05-04, Harshavardhana)**: `putOpts` and `delOpts` forced `opts.VersionID = nullVersionID` for `isDirObject(object)` without updating `checkPutObjectLockAllowed` or the storage commit path.

---

## 3. Final Repair Plan: What Code Changes and How {#solution}

The final repair combines **Core Plan A (`SN-2026-015`)** with **Entry + Storage Write-Lock Defense-in-Depth + Fail-Closed Preflight (`SN-2026-016`)** across 11 production files under `cmd/`:

| Issue | File | Summary of Change |
| --- | --- | --- |
| **SN-2026-015**<br>(Core Plan A, 3 files) | `cmd/object-handlers.go` | In `PutObjectRetentionHandler`, evaluate `isRetentionActionAllowed(PutObjectRetentionAction)` immediately after `ParseObjectRetention(r.Body)` and before reading any bucket or object state |
| | `cmd/bucket-object-lock.go` | Add `isRetentionActionAllowed` (evaluating zero/past dates as `"0"` days and ceiling future days via Unix second/nanosecond arithmetic); rewrite `enforceRetentionBypassForPut` to require both the bypass header and `s3:BypassGovernanceRetention` only when weakening an unexpired stored `GOVERNANCE` lock |
| | `cmd/auth-handler.go` | Delete the flawed 45-line `isPutRetentionAllowed` helper (`byPassSet \|\| retSet`) |
| **SN-2026-016**<br>(Entry & Write-Lock Guards, 8 files) | `cmd/object-api-options.go` | In `putOpts` (the single convergence point for HTTP write options), return `errAuthentication` (`403 AccessDenied`) whenever `vid != "" && !trustedReplication` |
| | `cmd/batch-handlers.go` | In `BatchJobReplicateV1.writeAsArchive`, set `ReplicationRequest: true` on outer `SnowballOptions` so server-side `batch replicate` archives pass the outer replication marker check |
| | `cmd/bucket-object-lock.go` | (1) In preflight `checkPutObjectLockAllowed`, resolve `nullVersionID` for `isDirObject(object)`, block unexpired `GOVERNANCE` in addition to `COMPLIANCE` and `LegalHoldOn`, and fail closed immediately on non-NotFound read errors; (2) add fail-closed `checkObjectLockedForOverwrite` for `null`-version re-checks under the storage write lock |
| | `cmd/bucket-handlers.go` | Call `checkPutObjectLockAllowed` for directory objects (`isDirObject(object)`) in `PostPolicyBucketHandler` |
| | `cmd/object-multipart-handlers.go` | Pass `trustedReplication` to `checkPutObjectLockAllowed` in `CompleteMultipartUploadHandler` |
| | `cmd/erasure-object.go` | Under the destination object write lock (`NewNSLock`) in `erasureObjects.putObject` and `erasureObjects.CopyObject`, call `checkObjectLockedForOverwrite` when writing to `""` or `nullVersionID` |
| | `cmd/erasure-multipart.go` | In `CompleteMultipartUpload` under the destination write lock, run `checkObjectLockedForOverwrite` for `null` versions and check whether any non-empty `fi.VersionID` already exists via `getObjectInfo` (or `replicaObjectInfo` across pools) |
| | `cmd/erasure-server-pool.go`<br>`cmd/erasure-sets.go` | Supply cross-pool `z.replicaObjectInfo` for public writes and multipart completions in multi-pool deployments, and forward versioning/replication flags in `CopyObject` |

---

### 3.1 SN-2026-015 Detailed Code Changes (Core Plan A) {#solution-015}

#### (1) `cmd/object-handlers.go`: Unconditional Base Authorization at `PutObjectRetentionHandler` Entry

Immediately after `authenticateRequest` and `ParseObjectRetention(r.Body)`—and **before** `GetBucketInfo`, `globalBucketObjectLockSys.Get`, or `getOpts`—enforce `s3:PutObjectRetention` via `isRetentionActionAllowed`:

```go
// cmd/object-handlers.go: PutObjectRetentionHandler
objRetention, err := objectlock.ParseObjectRetention(r.Body)
if err != nil {
	apiErr := errorCodes.ToAPIErr(ErrMalformedXML)
	apiErr.Description = err.Error()
	writeErrorResponse(ctx, w, apiErr, r.URL)
	return
}

reqInfo := logger.GetReqInfo(ctx)
reqInfo.SetTags("retention", objRetention.String())

// Check permissions to perform this object retention operation. The
// object-lock condition keys come from the request body, so this is
// decided before any bucket or object state is read.
if !isRetentionActionAllowed(policy.PutObjectRetentionAction, bucket, object, objRetention, r, reqInfo.Cred, reqInfo.Owner) {
	writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
	return
}
```

#### (2) `cmd/bucket-object-lock.go`: `isRetentionActionAllowed` and `enforceRetentionBypassForPut`

`isRetentionActionAllowed` constructs `object-lock-mode`, `object-lock-retain-until-date`, and `object-lock-remaining-retention-days` from the parsed request body and calls `globalIAMSys.IsAllowed`:
- When clearing retention (empty `<Retention/>`, zero `RetainUntilDate`) or for non-future dates, `object-lock-remaining-retention-days` is set to `"0"` (fixing the `106,752`-day bug caused by `time.Duration` clamping and `math.Abs`, while keeping the key present so `NumericLessThan` `Deny` policies match clear requests);
- For future dates, ceiling days are computed from Unix seconds and nanoseconds to avoid 292-year `time.Duration` saturation.

Inside the object write lock, `enforceRetentionBypassForPut` evaluates only stored retention state:

```go
// cmd/bucket-object-lock.go
func isRetentionActionAllowed(action policy.Action, bucketName, objectName string, objRetention *objectlock.ObjectRetention, r *http.Request, cred auth.Credentials, owner bool) bool {
	if objRetention == nil {
		return false
	}
	t, err := objectlock.UTCNowNTP()
	if err != nil {
		internalLogIf(r.Context(), err, logger.WarningKind)
		return false
	}

	conditionValues := getConditionValues(r, "", cred.AccessKey, nil)
	conditionValues["object-lock-mode"] = []string{string(objRetention.Mode)}
	conditionValues["object-lock-retain-until-date"] = []string{objRetention.RetainUntilDate.Format(time.RFC3339)}

	var days int64
	if !objRetention.RetainUntilDate.IsZero() && objRetention.RetainUntilDate.After(t) {
		sec := objRetention.RetainUntilDate.Unix() - t.Unix()
		nsec := int64(objRetention.RetainUntilDate.Nanosecond() - t.Nanosecond())
		if nsec < 0 {
			sec--
			nsec += int64(time.Second)
		}
		days = sec / (24 * 60 * 60)
		if sec%(24*60*60) > 0 || nsec > 0 {
			days++
		}
	}
	conditionValues["object-lock-remaining-retention-days"] = []string{strconv.FormatInt(days, 10)}

	return globalIAMSys.IsAllowed(policy.Args{
		AccountName:     cred.AccessKey,
		Groups:          cred.Groups,
		Action:          action,
		BucketName:      bucketName,
		ConditionValues: conditionValues,
		IsOwner:         owner,
		ObjectName:      objectName,
		Claims:          cred.GetClaims(),
	})
}

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

#### (3) `cmd/auth-handler.go`: Remove `isPutRetentionAllowed`

Delete the 45-line `isPutRetentionAllowed` function from `cmd/auth-handler.go`, eliminating the `byPassSet || retSet` short-circuit.

---

### 3.2 SN-2026-016 Detailed Code Changes (Entry Guards + Write-Lock Re-Checks + Fail-Closed Preflight) {#solution-016}

Why must `SN-2026-016` retain storage write-lock checks in addition to HTTP entry guards and preflight checks? Four concrete scenarios cannot be prevented by entry or provenance markers alone:
1. **Slow-body `PUT dir/` TOCTOU race (`TestPlanReviewSlowDirectoryPut`)**: In `PutObjectHandler`, `checkPutObjectLockAllowed` runs before streaming `r.Body` to disk, whereas the namespace write lock (`er.NewNSLock`) is acquired only after `r.Body` finishes streaming to a temporary file. A writer with `s3:PutObject` can initiate `PUT /bucket/dir/`, pass preflight while `dir/` is unlocked, pause streaming the request body while an administrator applies `COMPLIANCE` retention (`200 OK`), and then finish sending the body. Without re-checking under `er.NewNSLock`, the paused `PUT` overwrites the `null` version and erases the committed `COMPLIANCE` lock.
2. **Pre-existing or replication-initiated persisted `uploadId` completion (`TestPlanReviewLegacyMPUCompliance`)**: `putOpts` runs only during `NewMultipartUpload`; `CompleteMultipartUpload` uses `completeMultipartOpts` and takes the target `fi.VersionID` from `.minio.sys/multipart/.../uploadID/xl.meta`. For any upload created before the upgrade (or initiated by a replication principal), completing the upload after the target UUID version is locked under `COMPLIANCE` requires no concurrency and only `s3:PutObject` unless `CompleteMultipartUpload` validates the target under the write lock.
3. **Recovered multipart staging state colliding with a replicated `COMPLIANCE` version (`TestRecoveredMultipartUploadAfterReplica`)**: Even when a multipart upload's `fi.VersionID` was originally generated by the server at `NewMultipartUpload` time, if an older multipart staging snapshot is restored after a surviving replica has already re-synced and `COMPLIANCE`-locked that completed UUID version, a provenance marker only proves where the UUID came from at initiation—not that the version does not already exist at completion time. Therefore, `CompleteMultipartUpload` must unconditionally check under the destination write lock whether `fi.VersionID` already exists.
4. **Fail-closed read error handling (`TestPlanReviewPreflightReadFailure`)**: Only an explicit non-existence result (`ObjectNotFound`, `VersionNotFound`, or delete marker `MethodNotAllowed`) may be treated as unlocked; bucket lock configuration errors or storage read quorum failures (`InsufficientReadQuorum`) must reject the write immediately at preflight as well as at commit time.

The four components of the `SN-2026-016` repair are:

#### (1) Reject Untrusted `versionId` at the `putOpts` Convergence Point (`cmd/object-api-options.go`)

All HTTP write option builders (`PutObject`, `CopyObject`, `NewMultipartUpload`, `PostPolicy`, `PutObjectExtract`) converge at `putOpts`:

```go
// cmd/object-api-options.go: putOpts
vid = strings.TrimSpace(vid)
// A caller-chosen version ID writes that version in place. Only trusted
// replication may recreate a source version under its original ID.
if vid != "" && !trustedReplication {
	return opts, errAuthentication
}
```

#### (2) Set the Outer Replication Marker on Batch Snowball Archives (`cmd/batch-handlers.go`)

When SILO's `batch replicate` streams a Snowball archive via `writeAsArchive` to another SILO/MinIO target, each tar PAX entry carries `minio.versionId`. `PutObjectExtractHandler` requires `X-Minio-Source-Replication-Request: true` (`markerExact`) on the outer request before granting `entryTrusted`:

```go
// cmd/batch-handlers.go: writeAsArchive
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

#### (3) Enforce Fail-Closed `null`-Version Lock Checks at Both HTTP Preflight and Storage Write Lock (`cmd/bucket-object-lock.go`, `cmd/erasure-object.go`, `cmd/erasure-server-pool.go`, `cmd/erasure-sets.go`)

- **HTTP preflight (`checkPutObjectLockAllowed`)**: Resolve `nullVersionID` for directory objects (`isDirObject(object)`), block unexpired `GOVERNANCE` alongside `COMPLIANCE` and `LegalHoldOn` when `!replicaTrusted`, and fail closed immediately on any read error other than `ObjectNotFound` / `VersionNotFound` / `MethodNotAllowed`:

```go
// cmd/bucket-object-lock.go: checkPutObjectLockAllowed
if isDirObject(object) && opts.VersionID == "" {
	opts.VersionID = nullVersionID
}

if opts.VersionID != "" && !replicaTrusted {
	objInfo, err := getObjectInfoFn(ctx, bucket, object, opts)
	if err != nil {
		if !isErrObjectNotFound(err) && !isErrVersionNotFound(err) && !errors.As(err, &MethodNotAllowed{}) {
			return mode, retainDate, legalHold, toAPIErrorCode(ctx, err)
		}
	} else {
		r := objectlock.GetObjectRetentionMeta(objInfo.UserDefined)
		t, err := objectlock.UTCNowNTP()
		if err != nil {
			internalLogIf(ctx, err, logger.WarningKind)
			return mode, retainDate, legalHold, ErrObjectLocked
		}
		if (r.Mode == objectlock.RetCompliance || r.Mode == objectlock.RetGovernance) && r.RetainUntilDate.After(t) {
			return mode, retainDate, legalHold, ErrObjectLocked
		}
		mode = r.Mode
		retainDate = r.RetainUntilDate
		legalHold = objectlock.GetObjectLegalHoldMeta(objInfo.UserDefined)
		if legalHold.Status == objectlock.LegalHoldOn {
			return mode, retainDate, legalHold, ErrObjectLocked
		}
	}
}
```

- **Storage write-lock commit (`checkObjectLockedForOverwrite`)**: Inside `er.putObject`, `er.CopyObject`, and `er.CompleteMultipartUpload` while holding `er.NewNSLock(bucket, object)`, any non-replication write targeting `""` or `nullVersionID` calls `checkObjectLockedForOverwrite` (using `z.replicaObjectInfo` across pools) and fails closed on config or read errors:

```go
// cmd/bucket-object-lock.go: checkObjectLockedForOverwrite
func checkObjectLockedForOverwrite(ctx context.Context, bucket, object string, getObjectInfoFn GetObjectInfoFn) error {
	if isMinioMetaBucketName(bucket) {
		return nil
	}
	retentionCfg, err := globalBucketObjectLockSys.Get(bucket)
	if err != nil {
		return err
	}
	if !retentionCfg.LockEnabled {
		return nil
	}
	objInfo, err := getObjectInfoFn(ctx, bucket, object, ObjectOptions{
		VersionID:  nullVersionID,
		NoLock:     true,
		NoAuditLog: true,
	})
	if err != nil {
		if isErrObjectNotFound(err) || isErrVersionNotFound(err) || errors.As(err, &MethodNotAllowed{}) {
			return nil
		}
		return err
	}
	if objectlock.GetObjectLegalHoldMeta(objInfo.UserDefined).Status == objectlock.LegalHoldOn {
		return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
	}
	r := objectlock.GetObjectRetentionMeta(objInfo.UserDefined)
	if r.Mode == objectlock.RetCompliance || r.Mode == objectlock.RetGovernance {
		t, err := objectlock.UTCNowNTP()
		if err != nil {
			internalLogIf(ctx, err, logger.WarningKind)
			return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
		}
		if r.RetainUntilDate.After(t) {
			return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
		}
	}
	return nil
}
```

#### (4) Check Persisted `fi.VersionID` Under the Object Write Lock in `CompleteMultipartUpload` (`cmd/erasure-multipart.go`)

Under `er.NewNSLock(bucket, object)`, non-replication multipart completions (`!opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement`) check the persisted `fi.VersionID` from `uploadid/xl.meta`:
- If `fi.VersionID == "" || fi.VersionID == nullVersionID`: call `checkObjectLockedForOverwrite`;
- If `fi.VersionID` is a non-empty UUID: query `getObjectInfo` (or `replicaObjectInfo` across pools) and reject with `errAuthentication` (`403 AccessDenied`) if that version already exists on disk (including delete markers), failing closed on read errors without deleting staged parts.

```go
// cmd/erasure-multipart.go: CompleteMultipartUpload
if !opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement {
	getObjectInfo := er.getObjectInfo
	if opts.replicaObjectInfo != nil {
		getObjectInfo = opts.replicaObjectInfo
	}
	if fi.VersionID == "" || fi.VersionID == nullVersionID {
		if err := checkObjectLockedForOverwrite(ctx, bucket, object, getObjectInfo); err != nil {
			return oi, toObjectErr(err, bucket, object)
		}
	} else {
		_, gerr := getObjectInfo(ctx, bucket, object, ObjectOptions{
			VersionID:        fi.VersionID,
			Versioned:        opts.Versioned,
			VersionSuspended: opts.VersionSuspended,
			NoLock:           true,
		})
		switch {
		case gerr == nil, errors.As(gerr, &MethodNotAllowed{}):
			return oi, toObjectErr(errAuthentication, bucket, object)
		case isErrVersionNotFound(gerr) || isErrObjectNotFound(gerr):
		default:
			return oi, toObjectErr(gerr, bucket, object)
		}
	}
}
```

---

## 4. Critical-Path and Performance Impact Analysis {#performance-and-critical-path}

| Operation Path | Execution Path & Overhead After Repair |
| --- | --- |
| **`GetObject` / `HeadObject` / `ListObjects` / `DeleteObject`** | **Untouched**; read and delete paths do not traverse any modified code |
| **`PutObject` / `CopyObject` in regular buckets (Object Lock disabled)** | `putOpts` checks `vid != ""`; under the write lock, `checkObjectLockedForOverwrite` checks in-memory `globalBucketObjectLockSys.Get(bucket)` (`!retentionCfg.LockEnabled`) and returns immediately with **no extra disk I/O or cross-pool calls** |
| **Regular `PutObject` / `CopyObject` in Object Lock buckets (non-`/` keys)** | Object Lock buckets are always versioned; normal single-request writes generate a non-empty UUID `fi.VersionID` (`fi.VersionID != "" && fi.VersionID != nullVersionID`), so **neither preflight nor write-lock commit performs an extra `getObjectInfo` read** |
| **Directory object writes (`PUT dir/`) or `null`-version overwrites in Object Lock buckets** | Both preflight and the storage write lock read the `null` version's metadata and fail closed on read errors, preventing slow-body TOCTOU overwrites and read-failure bypasses |
| **Multipart upload completions (`CompleteMultipartUpload`) in versioned buckets** | Performs one fail-closed `getObjectInfo` (or `replicaObjectInfo` across pools) lookup under the destination write lock during final multipart commit (`NewMultipartUpload` and `UploadPart` are unaffected). Any future optimization to skip this lookup for newly generated uploads must account for snapshot-recovery collisions and be validated separately |
| **`PutObjectRetention` (valid extensions and unauthorized requests)** | Base `s3:PutObjectRetention` authorization runs before reading bucket/object state, rejecting unauthorized requests in memory without disk I/O or lock contention; valid retention extensions return immediately at `!weakens` inside the write lock without repeating IAM evaluation |

---

## 5. Why It Works and Upgrade Notes {#why-it-works}

### 5.1 Three Core Security Invariants

1. **Invariant 1: Base permission and lock condition keys must hold before any state is read (closes F1, F3, zero-date clear bypass, and existence probing)**
   - All three Object Lock condition keys on `PutObjectRetention` derive solely from the XML request body and current time. Evaluating `isRetentionActionAllowed(policy.PutObjectRetentionAction, ...)` immediately after `ParseObjectRetention` rejects unauthorized or policy-denied requests with `403 AccessDenied` before any bucket or object lookup.
2. **Invariant 2: Bypass is triggered strictly by weakening an unexpired stored lock and requires both header intent and IAM permission (closes F2)**
   - `enforceRetentionBypassForPut` runs under the object write lock and inspects stored `ret.Mode` and `ret.RetainUntilDate`. If no lock exists, the lock is expired, or `!weakens`, no bypass is required. When `weakens == true`, stored `COMPLIANCE` unconditionally returns `400 ObjectLocked`, and stored `GOVERNANCE` requires both `IsObjectLockGovernanceBypassSet(r.Header)` and `isRetentionActionAllowed(BypassGovernanceRetentionAction, ...)`.
3. **Invariant 3: Public writes cannot overwrite an existing UUID version or a locked `null` version at either entry or commit, failing closed on read errors (closes F4 and companion gaps)**
   - At entry, `putOpts` rejects any untrusted target `versionId`, and `checkPutObjectLockAllowed` fails closed immediately on locked directory `null` versions or read errors.
   - Under the destination write lock (`NewNSLock`), `checkObjectLockedForOverwrite` re-verifies `null`-version writes (closing the slow-body TOCTOU window), and `CompleteMultipartUpload` verifies that any non-empty `fi.VersionID` does not already exist on disk (closing legacy uploads, cross-principal completions, and post-recovery UUID collisions).

#### `PutObjectRetention` Decision Matrix

`retOK` denotes `s3:PutObjectRetention` allowed with the request's lock condition keys; `bypassOK` denotes `s3:BypassGovernanceRetention` allowed with those same keys:

| Stored Version State | Requested Change | Bypass Header | `retOK` | `bypassOK` | Previous Behavior | Repaired Behavior |
| --- | --- | --- | --- | --- | --- | --- |
| Any | Any | Any | **No** | Any | Often **200** (F1, F3) or 404/400 | Entry **403 AccessDenied** |
| Unexpired `GOVERNANCE` | Extend retention | Any | Yes | Any | 200 | **200 OK** |
| Unexpired `GOVERNANCE` | Shorten / clear / change mode | No | Yes | Any | 400 `InvalidRequest` (`ObjectLocked`) | **400 `InvalidRequest` (`ObjectLocked`)** |
| Unexpired `GOVERNANCE` | Shorten / clear / change mode | Yes | Yes | **No** | **200** (F2 bug) | **403 AccessDenied** |
| Unexpired `GOVERNANCE` | Shorten / clear / change mode | Yes | Yes | **Yes** | 200 | **200 OK** |
| Unexpired `COMPLIANCE` | Shorten / clear / change mode | Any | Yes | Any | 400 `InvalidRequest` (`ObjectLocked`) | **400 `InvalidRequest` (`ObjectLocked`)** |
| Unlocked or expired | Any | Any | Yes | Any | 200 | **200 OK** |

#### Write-Path Invariant Coverage

| Write Path | Option Convergence & Write-Lock Guard | Post-Repair Guarantee |
| --- | --- | --- |
| `PutObject` (regular PUT / bucket replication / site replication / single-object batch replication) | `evaluateReplicationTrust` -> `putOpts`; `null` versions run `checkObjectLockedForOverwrite` under write lock | Public callers (including `root`) passing `?versionId=` receive `403` at `putOpts`; trusted replication preserves source version IDs |
| `CopyObject` (including metadata copy) | Source uses `srcOpts`, destination uses `copyDstOpts` -> `putOpts`; `null` versions run `checkObjectLockedForOverwrite` under write lock | Public callers specifying destination `?versionId=` receive `403`; trusted replication synchronizes target versions |
| `PostPolicy` (browser form upload) | `putOptsFromReq` -> `putOpts`; directory objects checked at preflight and write lock | Target `versionId` receives `403`; locked directory objects cannot be overwritten |
| `PutObjectExtract` (Snowball / batch archive replication) | Outer `markerExact` + per-entry `s3:ReplicateObject` -> `entryTrusted` -> `putOpts`; `writeAsArchive` sets outer marker | Untrusted archive entries with `minio.versionId` receive `403`; server-side `batch replicate` archives preserve version IDs |
| `NewMultipartUpload` / `UploadPart` / `UploadPartCopy` | Initiation passes through `putOpts`; `UploadPartCopy` clears replication trust | Untrusted callers cannot initiate multipart uploads with `?versionId=` (`403`) |
| `CompleteMultipartUpload` | `completeMultipartOpts` + write-lock check keyed on `fi.VersionID` | In-flight uploads from before versioning was enabled complete normally; non-replication completions targeting any existing UUID version (including legacy, replication-initiated, or recovered uploads) receive `403`; `null` versions run `checkObjectLockedForOverwrite` |
| Directory object `PUT` / `Copy` (`/{bucket}/dir/`) | Fail-closed preflight `checkPutObjectLockAllowed` + write-lock `checkObjectLockedForOverwrite` | Overwriting a directory `null` version with unexpired `GOVERNANCE`, `COMPLIANCE`, or `LegalHoldOn` (including locks applied during slow body transfer) returns `400 InvalidRequest` (`ObjectLocked`); read errors abort the write at both preflight and commit |

---

### 5.2 Upgrade and Compatibility Notes {#side-effects}

Normal new-version writes, object reads, and authorized retention extensions are unchanged. Operators should note the following tightened behaviors:

1. **Policies granting `s3:BypassGovernanceRetention` without `s3:PutObjectRetention` no longer allow retention writes (`SN-2026-015`)**
   - **Previous behavior**: Due to `byPassSet || retSet`, a principal with only `s3:BypassGovernanceRetention` could call `PutObjectRetention` by including the bypass header.
   - **New behavior**: Returns `403 AccessDenied`. Per AWS S3 semantics, `s3:BypassGovernanceRetention` is an additional permission when weakening governance locks; `s3:PutObjectRetention` is always required.
2. **Unauthorized `PutObjectRetention` requests uniformly return `403` instead of `404` or `400` (`SN-2026-015`)**
   - **Previous behavior**: Returned `404 NoSuchBucket` or `400 InvalidBucketObjectLockConfiguration` before checking policy.
   - **New behavior**: Policy evaluation runs before reading bucket state, returning `403 AccessDenied`.
3. **Clearing retention (empty `<Retention/>`) evaluates `s3:object-lock-remaining-retention-days` as `"0"` (`SN-2026-015`)**
   - **Previous behavior**: Zero-time duration clamping and `math.Abs` produced `106,752` days, allowing clear requests to bypass minimum-retention-day policies.
   - **New behavior**: Evaluates to `"0"`, enforcing minimum-retention-day policies on clear requests.
4. **Non-replication requests (including `root`) can no longer overwrite a version in place via `?versionId=` (`SN-2026-016`)**
   - **Previous behavior**: Any caller with `s3:PutObject` could pass `?versionId=<id>` on `PUT`, `CopyObject`, or `NewMultipartUpload` to overwrite that version in place.
   - **New behavior**: Returns `403 AccessDenied` at `putOpts` unless the request is authenticated replication.
5. **`batch replicate` to a SILO target requires `s3:ReplicateObject` on the target credentials (`SN-2026-016`)**
   - **Previous behavior**: A target credential with only `s3:PutObject` had internal replication headers stripped, yet `putOpts` still accepted `?versionId=` from the query string.
   - **New behavior**: Preserving source version IDs requires target replication trust (`s3:ReplicateObject`), matching bucket replication requirements.
6. **Locked directory objects (`dir/`) in Object Lock buckets cannot be overwritten until lock expiry (`SN-2026-016`)**
   - **Previous behavior**: Directory objects shared the `null` version and skipped existing-lock checks, allowing repeated `PUT dir/` calls to overwrite and reset retention.
   - **New behavior**: Returns `400 InvalidRequest` (`ObjectLocked`) while the directory `null` version holds an unexpired `GOVERNANCE`/`COMPLIANCE` retention or `LegalHoldOn`.
7. **Separately tracked adjacent item (not bundled in this patch)**
   - `PostRestoreObjectHandler` (archive restore) reading a snapshot before writing back metadata via `CopyObject` is tracked separately as an archive-restore concurrency item.

---

## 6. Adversarial Evaluation Across Candidate Designs {#tradeoffs}

During design review, four candidate write-path designs were evaluated against adversarial reproducers:

| Dimension | Candidate 1: HTTP Entry & Preflight Only<br>(Rejected) | Candidate 2: Skipping Write-Lock UUID Check via Multipart Origin Marker<br>(Rejected) | Candidate 3: `fe3935476` Full Write-Lock Checks<br>(Without Fail-Closed Preflight) | **Final Adopted Design**: `fe3935476` Full Write-Lock Checks + Fail-Closed Preflight |
| --- | --- | --- | --- | --- |
| **`SN-2026-015` Retention Authz (F1 / F2 / F3 / Zero-Date)** | Passes | Passes | Passes | **Passes** |
| **Slow-body `PUT dir/` concurrent lock race (`TestPlanReviewSlowDirectoryPut`)** | **Fails (P1)**: paused body stream overwrites committed `COMPLIANCE` lock | Passes | Passes | **Passes** |
| **Pre-upgrade or replication-initiated `uploadId` overwrite (`TestPlanReviewLegacyMPUCompliance`)** | **Fails (P1)**: `CompleteMultipartUpload` bypasses `putOpts` and overwrites `COMPLIANCE` version | Passes | Passes | **Passes** |
| **Recovered multipart upload colliding with replicated `COMPLIANCE` UUID (`TestRecoveredMultipartUploadAfterReplica`)** | **Fails (P1)** | **Fails (P1)**: origin marker only proves how the UUID was generated at initiation, not that the version is still absent at completion | Passes (unconditional `fi.VersionID` existence check under write lock) | **Passes (unconditional `fi.VersionID` existence check under write lock)** |
| **Preflight read quorum failure behavior (`TestPlanReviewPreflightReadFailure`)** | **Fails (P1)**: preflight ignores read error and overwrites object | Passes | Write lock blocks overwrite, but preflight ignores read error and streams body | **Passes (preflight immediately fails closed before streaming body)** |
| **`CompleteMultipartUpload` lookup behavior** | No extra lookup | Skips lookup on generated marker (introduces recovery collision flaw) | Runs `getObjectInfo` under write lock | **Retains strict `getObjectInfo` check under write lock; any future performance optimization is deferred for separate validation** |

### Conclusion

We adopt the **`fe3935476` full write-lock defense + fail-closed preflight hardening** as the final implementation, and incorporate all four adversarial regression tests (`TestPlanReviewSlowDirectoryPut`, `TestPlanReviewPreflightReadFailure`, `TestPlanReviewLegacyMPUCompliance`, and `TestRecoveredMultipartUploadAfterReplica`) into `cmd/object-retention-overwrite_test.go`.
