---
title: "SN-2026-015 & SN-2026-016: S3 Object Lock Governance Retention Bypass and Version-Addressed Overwrites"
linkTitle: "SN-2026-015: Retention Bypass"
date: 2026-09-26
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "Root-cause analysis, reproduction, and repair design for the PutObjectRetention governance bypass (SN-2026-015) and version-addressed object overwrite vulnerabilities (SN-2026-016), fixed in SILO Server 20261018."
tags: ["Security", "Object Lock", "S3", "WORM", "Compliance", "Governance", "IAM", "SILO"]
weight: 1
url: "/blog/security/20260926-governance-retention-bypass/"
---

**`SN-2026-015`** and **`SN-2026-016`** cover two S3 Object Lock retention and immutability vulnerabilities fixed in [SILO Server 20261018](/blog/release/silo-20261018/) via PR [`#234`](https://github.com/pgsty/silo/pull/234) (`14042b5aa`) and PR [`#235`](https://github.com/pgsty/silo/pull/235) (`0d3ba5d4c`), as detailed in the companion [repair design note](/blog/design/governance-retention-bypass-repair/). While the delete path already enforced `s3:BypassGovernanceRetention` ([CVE-2023-25812](https://github.com/minio/minio/security/advisories/GHSA-c8fc-mjj8-fc63)), the retention-write path (`PutObjectRetention`) and four in-place version overwrite paths remained bypassable.

## Advisory Scope: `SN-2026-015` and `SN-2026-016`

### SN-2026-015: `PutObjectRetention` Authorization and Governance Bypass (`#231`) {#sn-2026-015}

In `PutObjectRetentionHandler` (`cmd/object-handlers.go`), three interacting flaws in `enforceRetentionBypassForPut` and `isPutRetentionAllowed` broke S3 Object Lock authorization:
- **F1 (Unconditional `s3:PutObjectRetention` bypass via header)**: Passing `x-amz-bypass-governance-retention: true` caused `isPutRetentionAllowed` to check **only** `s3:BypassGovernanceRetention` (`!byPassSet`), allowing an authenticated principal with **zero** `s3:PutObjectRetention` and **zero** `s3:BypassGovernanceRetention` permissions to place or extend retention on any unlocked object!
- **F2 (Governance retention shortening/clearing without `s3:BypassGovernanceRetention`)**: Because `isPutRetentionAllowed` evaluated `byPassSet || retSet`, a caller who held `s3:PutObjectRetention` (`retSet == true`) but **lacked** `s3:BypassGovernanceRetention` (`byPassSet == false`) could pass `x-amz-bypass-governance-retention: true` to clear (`<Retention/>`) or shorten an active `GOVERNANCE` retention lock, and then delete the object (`GHSA-67mv-7hc9-wj88`, reported by `szopi00`).
- **F3 (`s3:object-lock-remaining-retention-days` condition bypass on governance bypass)**: When `x-amz-bypass-governance-retention: true` was set on an existing governance-locked object, `s3:PutObjectRetention` was skipped whenever `s3:BypassGovernanceRetention` succeeded, bypassing IAM policy conditions such as `NumericGreaterThanEquals: {"s3:object-lock-remaining-retention-days": 30}` attached to `s3:PutObjectRetention`.

### SN-2026-016: Version-Addressed and In-Place Object Overwrites (`#234`) {#sn-2026-016}

While auditing every write path that can mutate an existing object version in place, we found and closed four write-path bypasses (`14042b5aa`):
1. **Caller-supplied `?versionId=` on `PutObject` and `CopyObject`**: Non-replication callers could pass `?versionId=<existing-uuid>` on `PutObject` or `CopyObject` (or `minio.versionId` in Snowball `PutObjectExtract` PAX headers) to overwrite an existing version in place without checking WORM retention or legal hold on that target version.
2. **Directory object (`key/`) `null`-version overwrite**: Creating or overwriting a directory object (`strings.HasSuffix(object, "/")`) wrote to `nullVersionID` even in versioned/Object-Lock buckets without checking existing retention or legal hold on the `null` version.
3. **`CompleteMultipartUpload` in-place `null`-version overwrite**: In an Object-Lock-enabled bucket with versioning suspended (or targeting an existing `null` version), `CompleteMultipartUpload` did not enforce retention/legal-hold checks on an existing `null` version before replacing it.
4. **Replication header trust**: Unprivileged callers with `s3:PutObject` could spoof `X-Minio-Source-Replication-Request` headers unless gated by `s3:ReplicateObject`.

---

## Expected S3 Object Lock Semantics {#semantics}

Under the AWS S3 Object Lock specification, `PutObjectRetention` must enforce two independent orthogonal boundaries:

| Target Object State | Proposed `<Retention>` Change | Required IAM Permissions | Required Request Header |
|---|---|---|---|
| Unlocked, or retention expired | Set `GOVERNANCE` or `COMPLIANCE` with future date | `s3:PutObjectRetention` | None |
| Active `GOVERNANCE` lock | Extend `RetainUntilDate` to a strictly later date (same mode) | `s3:PutObjectRetention` | None |
| Active `GOVERNANCE` lock | Clear (`<Retention/>`), shorten `RetainUntilDate`, or switch `GOVERNANCE` -> `COMPLIANCE` | `s3:PutObjectRetention` **AND** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| Active `COMPLIANCE` lock | Extend `RetainUntilDate` to a strictly later date (`COMPLIANCE` mode) | `s3:PutObjectRetention` | None |
| Active `COMPLIANCE` lock | Clear, shorten, or switch `COMPLIANCE` -> `GOVERNANCE` | **Forbidden for all principals** | Forbidden (`AccessDenied`) |

---

## Reproduction and Verification {#verification}

The three `SN-2026-015` failures can be reproduced directly against pre-`20261018` builds (verified against baseline `b0a540190`):

### Reproduction 1: Clearing an Active Governance Lock Without `s3:BypassGovernanceRetention` (F2)

Assume user `nobypass` has `Allow` on `s3:PutObjectRetention` and `s3:DeleteObjectVersion`, and **no** `s3:BypassGovernanceRetention` grant:

| Step | Action by `nobypass` | Pre-`20261018` Result | Server `20261018` Result |
|---|---|---|---|
| 1 | Object `doc.txt` (version `v1`) is locked in `GOVERNANCE` mode until `2030-01-01` | Locked | Locked |
| 2 | `DELETE /bucket/doc.txt?versionId=v1` | `403 AccessDenied` | `403 AccessDenied` |
| 3 | `PUT /bucket/doc.txt?retention&versionId=v1` with header `x-amz-bypass-governance-retention: true` and body `<Retention/>` | **`200 OK` (lock cleared!)** | `403 AccessDenied` |
| 4 | `DELETE /bucket/doc.txt?versionId=v1` | **`204 No Content` (version permanently deleted!)** | Object remains locked and protected |

### Reproduction 2: Locking an Object with Zero Retention Permissions (F1)

Assume user `zeroperm` has an empty/unrelated policy with **neither** `s3:PutObjectRetention` **nor** `s3:BypassGovernanceRetention`:

| Step | Action by `zeroperm` | Pre-`20261018` Result | Server `20261018` Result |
|---|---|---|---|
| 1 | `PUT /bucket/unlocked.txt?retention` (without bypass header), body `<Mode>COMPLIANCE</Mode><RetainUntilDate>2099-01-01T00:00:00Z</RetainUntilDate>` | `403 AccessDenied` | `403 AccessDenied` |
| 2 | Repeat the exact same `PUT /bucket/unlocked.txt?retention` **adding header `x-amz-bypass-governance-retention: true`** | **`200 OK` (irreversible 2099 COMPLIANCE lock applied!)** | `403 AccessDenied` |

### Reproduction 3: Bypassing `s3:object-lock-remaining-retention-days` Conditions (F3)

Assume user `govadmin` holds `s3:BypassGovernanceRetention` unconditionally, and holds `s3:PutObjectRetention` conditioned on `NumericGreaterThanEquals: {"s3:object-lock-remaining-retention-days": 30}`. On an object already under `GOVERNANCE` lock, sending `x-amz-bypass-governance-retention: true` with a 5-day retention period previously succeeded (`byPassSet == true` satisfied `byPassSet || retSet` even though `retSet` was `false`), bypassing the 30-day minimum policy condition.

---

## Root Cause Analysis {#root-cause}

In `cmd/object-handlers.go`, `PutObjectRetentionHandler` authenticated the caller (`authenticateRequest`) and delegated **all** authorization to `enforceRetentionBypassForPut`, which called `isPutRetentionAllowed`:

```go
// Pre-20261018 isPutRetentionAllowed (broken)
func isPutRetentionAllowed(ctx context.Context, r *http.Request, bucket, object string,
    retDays int, retDate time.Time, retMode RetentionMode, byPassSet bool,
    cred auth.Credentials, owner bool, claims map[string]interface{}) (retSet, byPass bool) {

    if !byPassSet {
        return isReqAuthenticated(ctx, r, iampolicy.PutObjectRetentionAction, ...), false
    }

    byPass = isReqAuthenticated(ctx, r, iampolicy.BypassGovernanceRetentionAction, ...)
    retSet = isReqAuthenticated(ctx, r, iampolicy.PutObjectRetentionAction, ...)
    return retSet, byPass || retSet
}
```

And in `enforceRetentionBypassForPut`:
1. When the existing object had **no** active retention (`opts.Mode == ""`), the function checked `if !retSet && !govBypass` and returned `nil` whenever `byPassSet` (`x-amz-bypass-governance-retention: true`) was true—because on the unlocked path it never even called `isPutRetentionAllowed` properly, or trusted the header boolean directly (**F1**)!
2. When the existing object was in `GOVERNANCE` mode and the caller passed `x-amz-bypass-governance-retention: true`, `isPutRetentionAllowed` returned `byPass || retSet` as the second return value (`govBypass`). Thus `retSet == true` (`s3:PutObjectRetention` alone) made `govBypass == true` (**F2**), and conversely `byPass == true` (`s3:BypassGovernanceRetention` alone) made `govBypass == true` even when `retSet == false` (**F3**).

### Upstream History {#history}

Tracing `git log` shows how three separate changes over five years combined to create F1–F3:
- **2020-04 ([`43a3778b4`](https://github.com/minio/minio/commit/43a3778b4), `minio/minio#9259`)**: Introduced `enforceRetentionBypassForPut` and `isPutRetentionAllowed` with the `byPass || retSet` boolean conflation.
- **2025-02 ([`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32), `minio/minio#20929`)**: Refactored retention checks in `PutObjectRetentionHandler`.
- **2025-04 ([`8c7097528`](https://github.com/minio/minio/commit/8c7097528), `minio/minio#21103`)**: Replaced the entry `checkRequestAuthType` call in `PutObjectRetentionHandler` with `authenticateRequest` (which only checks SigV4 signature validity, not `s3:PutObjectRetention`), leaving `enforceRetentionBypassForPut` as the sole authorization gate and exposing **F1** to any authenticated user with zero permissions.

---

## Repair Design {#design}

### Five Security Invariants {#invariants}

Our repair enforces five explicit invariants across `PutObjectRetention` (`0d3ba5d4c`) and object write paths (`14042b5aa`):
1. **Invariant 1 (Mandatory `s3:PutObjectRetention`)**: Every `PutObjectRetention` request must satisfy `s3:PutObjectRetention` (including all policy conditions such as `s3:object-lock-remaining-retention-days`, `s3:object-lock-retention-mode`, and `s3:object-lock-retain-until-date`), regardless of whether `x-amz-bypass-governance-retention` is present.
2. **Invariant 2 (Additional `s3:BypassGovernanceRetention` on governance weakening)**: If the target version has an active (unexpired) `GOVERNANCE` lock and the request clears retention (`Mode == ""`) or shortens `RetainUntilDate` (`!RetainUntilDate.After(existing.RetainUntilDate)`), the request must **additionally** carry `x-amz-bypass-governance-retention: true` and satisfy `s3:BypassGovernanceRetention` (including its `s3:ExistingObjectTag/<key>` conditions).
3. **Invariant 3 (`COMPLIANCE` immutability)**: An active (unexpired) `COMPLIANCE` lock can never be cleared, shortened, or downgraded to `GOVERNANCE` by any principal.
4. **Invariant 4 (No caller-specified version overwrite)**: Non-replication S3 clients cannot supply `?versionId=` on `PutObject`, `CopyObject`, or `PutObjectExtract` to overwrite an existing version ID.
5. **Invariant 5 (In-place `null`-version write-lock enforcement)**: Any write path that replaces an existing `null` version in place (`PutObject` on a suspended-versioning bucket, directory object `key/`, or `CompleteMultipartUpload`) must enforce existing WORM retention and legal-hold checks on that `null` version.

### Where Each Check Lives {#placement}

In `PutObjectRetentionHandler` and `enforceRetentionBypassForPut`:
- `s3:PutObjectRetention` (`retOK`) is always evaluated against the proposed retention parameters (`retDays`, `retDate`, `retMode`) and existing object tags.
- `s3:BypassGovernanceRetention` (`bypassOK`) is evaluated independently and required whenever an active `GOVERNANCE` lock is cleared or shortened (or when switching an active `GOVERNANCE` lock to `COMPLIANCE` with a shorter date).

### Complete Decision Table for `PutObjectRetention` {#decision-table}

| Row | Existing Lock State | Requested Mutation | `x-amz-bypass-governance-retention` | `retOK` (`s3:PutObjectRetention`) | `bypassOK` (`s3:BypassGovernanceRetention`) | Outcome |
|---|---|---|---|---|---|---|
| 1 | Any | Any | `false` or `true` | `false` | Any | **`403 AccessDenied`** (closes F1 & F3) |
| 2 | Unlocked or expired | Set future retention | `false` or `true` | `true` | Not required | **`200 OK`** |
| 3 | Active `GOVERNANCE` | Extend `RetainUntilDate` (same mode or upgrade to `COMPLIANCE` with `>=` date) | `false` or `true` | `true` | Not required | **`200 OK`** |
| 4 | Active `GOVERNANCE` | Clear (`<Retention/>`) or shorten `RetainUntilDate` | `false` | `true` | Any | **`403 AccessDenied`** |
| 5 | Active `GOVERNANCE` | Clear (`<Retention/>`) or shorten `RetainUntilDate` | `true` | `true` | `false` | **`403 AccessDenied`** (closes F2) |
| 6 | Active `GOVERNANCE` | Clear (`<Retention/>`) or shorten `RetainUntilDate` | `true` | `true` | `true` | **`200 OK`** |
| 7 | Active `COMPLIANCE` | Clear, shorten, or downgrade to `GOVERNANCE` | `false` or `true` | Any | Any | **`403 AccessDenied`** |

### Five Rejected Alternatives {#alternatives}

During design review we evaluated and rejected five simpler-looking patches:
1. **Changing only `byPass || retSet` to `byPass && retSet` inside `isPutRetentionAllowed`**: Would fix F2 and F3, but would still leave **F1** open on unlocked objects (where `isPutRetentionAllowed` was bypassed) and would wrongly require `s3:BypassGovernanceRetention` when a user with `s3:PutObjectRetention` extends a lock while happening to pass `x-amz-bypass-governance-retention: true`.
2. **Adding a `checkRequestAuthType(..., PutObjectRetentionAction)` call at the top of `PutObjectRetentionHandler`**: At handler entry, the XML body (`<Retention>`) has not been parsed yet and the existing object's tags have not been read from disk, so policy conditions on `s3:object-lock-remaining-retention-days`, `s3:object-lock-retain-until-date`, `s3:object-lock-retention-mode`, and `s3:ExistingObjectTag/<key>` would all fail!
3. **Requiring `s3:BypassGovernanceRetention` whenever `x-amz-bypass-governance-retention: true` is present on the request**: S3 only requires `s3:BypassGovernanceRetention` when the operation actually **needs** governance bypass (clearing or shortening an active `GOVERNANCE` lock), not when locking an unlocked object or extending an existing lock.
4. **Blocking `<Retention/>` empty XML payloads**: Clearing an active `GOVERNANCE` lock via `<Retention/>` is a documented MinIO/SILO extension used by `mcli retention clear`; it must remain supported when the caller holds **both** `s3:PutObjectRetention` and `s3:BypassGovernanceRetention` and sends `x-amz-bypass-governance-retention: true`.
5. **Enforcing `SN-2026-016` `?versionId=` rejection only on Object-Lock-enabled buckets**: Allowing arbitrary clients to overwrite historical versions in place via `?versionId=` violates S3 versioning immutability on **all** versioned buckets, not just Object Lock buckets.

### Implementation Notes {#notes}

- **`ParseObjectRetention` and empty `<Retention/>` (`s3:object-lock-remaining-retention-days`)**: When a caller sends `<Retention/>` to clear governance retention, `retDate` is the zero `time.Time{}`. Previously, `getRetentionDays` computed a negative integer from `time.Until(zeroTime)` (~`-106751` days due to `time.Duration` 290-year saturation!). Commit `0d3ba5d4c` normalizes zero `retDate` to `0` days and computes future remaining days using non-saturating calendar/seconds arithmetic so dates beyond year 2316 do not overflow `time.Duration`.
- **`s3:ExistingObjectTag/<key>` propagation**: Both the `s3:PutObjectRetention` and `s3:BypassGovernanceRetention` checks receive the target version's stored tags so tag-based IAM policies evaluate accurately.

---

## Compatibility {#compatibility}

- **Standard S3 and `mcli retention` workflows**: Fully compatible. Callers that clear or shorten governance retention via `mcli retention clear --governance` must hold both `s3:PutObjectRetention` and `s3:BypassGovernanceRetention`.
- **Active-active / site replication**: Legitimate replication requests that preserve source version IDs must hold `s3:ReplicateObject` (included in standard replication policies).

---

## Regression Test Matrix {#tests}

PR [`#234`](https://github.com/pgsty/silo/pull/234) and PR [`#235`](https://github.com/pgsty/silo/pull/235) lock down the full matrix in `cmd/object-handlers-lock_test.go` and `cmd/bucket-versioning_test.go`:
- All 7 rows of the `PutObjectRetention` decision table (F1 zero-permission caller, F2 `PutObjectRetention`-only caller, F3 `BypassGovernanceRetention`-only caller with `s3:object-lock-remaining-retention-days` conditions),
- Far-future retention dates (`2400-01-01T00:00:00Z`) exceeding `time.Duration`'s 290-year limit,
- `PutObject`, `CopyObject`, and `PutObjectExtract` with caller-supplied `?versionId=` / `minio.versionId`,
- Directory object (`key/`) and `CompleteMultipartUpload` in-place overwrites against locked `null` versions.

---

## Mitigation and Upgrade {#mitigation}

### Delivery Status {#delivery}

Both **`SN-2026-015`** (`0d3ba5d4c`, PR `#235`) and **`SN-2026-016`** (`14042b5aa`, PR `#234`) are shipped in [SILO Server 20261018](/blog/release/silo-20261018/). Operators relying on S3 Object Lock WORM governance or compliance retention should upgrade to `20261018` immediately.
