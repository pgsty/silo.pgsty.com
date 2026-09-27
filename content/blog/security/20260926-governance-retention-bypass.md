---
title: "SN-2026-015: PutObjectRetention Authorization Bypass"
linkTitle: "SN-2026-015: Retention Authorization"
date: 2026-09-26
author: "Vonng"
description: "PutObjectRetention trusts the governance-bypass header in place of authorization. Scope, root cause, verification and the proposed fix design."
tags: [Security, Object Lock, IAM, silo]
weight: 1
url: "/blog/security/20260926-governance-retention-bypass/"
---

**Status on 2026-09-26: design, not fixed.** This is a fix design for review.
No SILO release fixes this defect yet. Every published Server release is
affected, including `RELEASE.2026-09-16T00-00-00Z`, and so is Server main at
[`b0a540190`](https://github.com/pgsty/silo/commit/b0a540190). The code came
from upstream MinIO, and upstream master has the same logic.

When a `PutObjectRetention` request carries
`x-amz-bypass-governance-retention: true`, the server treats that header as
authorization. It should be only a declaration of intent. Three results follow,
in decreasing severity:

| ID | Who | What they can do |
| --- | --- | --- |
| **F1** | **Any authenticated principal**, including one with an explicit Deny on `s3:PutObjectRetention` and `s3:BypassGovernanceRetention` and no grant on the bucket | Remove GOVERNANCE retention from any version in any lock-enabled bucket; change GOVERNANCE to COMPLIANCE; apply COMPLIANCE retention of any length to a version that has no retention or whose retention has expired |
| **F2** | A principal with `s3:PutObjectRetention` but not `s3:BypassGovernanceRetention` | Shorten GOVERNANCE retention (the reported case) |
| **F3** | A principal with `s3:BypassGovernanceRetention` | Ignore a conditional Deny on `s3:PutObjectRetention` |

F1 and F2 defeat GOVERNANCE retention. After the retention is gone, or its
shortened date has passed, a principal with ordinary delete permission can
remove the version. F1 also turns object lock against the data owner. A version
put under COMPLIANCE retention cannot be deleted by anyone, including root,
until the date passes, and the bucket's storage stays consumed for that time.
Anonymous requests are not affected: they are rejected because they carry no
access key.

The delete path enforces the bypass permission correctly
([CVE-2023-25812](https://github.com/minio/minio/security/advisories/GHSA-c8fc-mjj8-fc63)).

szopi00 reported F2 as
[GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88).
The report went to the Pigsty repository because private vulnerability
reporting was disabled on `pgsty/silo`. We found F1 and F3 while designing the
fix and reviewing that design. `SN-2026-015` is the provisional ledger
identifier. We assess the combined issue as **High**, because F1 requires only
a valid credential. A CVE has not been requested yet.

## Expected semantics {#semantics}

For a version under unexpired GOVERNANCE retention, S3 Object Lock requires:

| Requested change | Required permission | Required header |
| --- | --- | --- |
| Any retention write | `s3:PutObjectRetention` | none |
| Keep GOVERNANCE with the same or a later date (extend) | `s3:PutObjectRetention` | none |
| Earlier date (shorten) | `s3:PutObjectRetention` **and** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| Remove retention, or change the mode | `s3:PutObjectRetention` **and** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| Delete the locked version | `s3:DeleteObjectVersion` **and** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |

The header declares intent, and the permissions authorize the change.
GOVERNANCE is only meaningful when both are required: routine principals may
set and extend retention, and only a separately trusted principal may weaken it.
Unexpired COMPLIANCE retention can never be shortened or have its mode changed.
The existing COMPLIANCE checks do not depend on the header, but F1 can still
*create* COMPLIANCE retention.

## Verification {#verification}

All tests ran on a local build of Server main (`b0a540190`), with SigV4-signed
requests.

**F2**, with the reporter's policy: `nobypass` holds `s3:PutObjectRetention`,
`s3:DeleteObject` and `s3:DeleteObjectVersion`, but not
`s3:BypassGovernanceRetention`.

| Step, as `nobypass` unless noted | Result |
| --- | --- |
| Root sets GOVERNANCE until 2032 | 200 |
| Shorten to 2027, no header | 400 `InvalidRequest` (WORM protected), correct |
| Shorten to 2027, with header | **200**; `GetObjectRetention` then returns 2027 |
| Shorten to 5 seconds ahead, with header | **200** |
| After 8 seconds, `DeleteObject` with `versionId` and no header | **204**; `HEAD` then returns 404 |
| Control: `DeleteObject` with header | refused, correct |

**F1**, with `zeroperm`: its only Allow is `s3:ListAllMyBuckets`, and it has an
explicit Deny on `s3:PutObjectRetention` and `s3:BypassGovernanceRetention` for
`arn:aws:s3:::*`. The bucket and objects belong to root.

| Step, as `zeroperm` | Result |
| --- | --- |
| Remove GOVERNANCE (empty `<Retention/>`), no header | 400 `InvalidRequest`, correct |
| Remove GOVERNANCE, with header | **200**; retention is gone |
| COMPLIANCE until 2027 on a version without retention, no header | 403 `AccessDenied`, correct |
| COMPLIANCE until 2027 on a version without retention, with header | **200** |
| Root: `DeleteObject` with bypass on that version | refused, WORM protected |

**F3**: a user is allowed `s3:PutObjectRetention` and
`s3:BypassGovernanceRetention`, with an explicit Deny on `s3:PutObjectRetention`
when `s3:object-lock-remaining-retention-days` is less than 30. With the
header, that user set the remaining retention to 5 days: **200**.

## Root cause {#root-cause}

Two defects combine.

**The handler only authenticates.** `PutObjectRetentionHandler`
(`cmd/object-handlers.go`) calls `authenticateRequest(ctx, r,
policy.PutObjectRetentionAction)`. Despite its action argument, that function
verifies the signature and records the credential. It does not evaluate any
policy. All authorization is left to `enforceRetentionBypassForPut`
(`cmd/bucket-object-lock.go`), which runs from `EvalMetadataFn`, and to its
helper `isPutRetentionAllowed` (`cmd/auth-handler.go`).

**The helper fails open on the header.**

```go
// enforceRetentionBypassForPut
byPassSet := objectlock.IsObjectLockGovernanceBypassSet(r.Header) // raw header
...
case objectlock.RetGovernance:
    govPerm := isPutRetentionAllowed(..., objRetention.Mode, byPassSet, ...)
    if !byPassSet { // shortening / mode-change guard, skipped when the header is present
        if objRetention.Mode != objectlock.RetGovernance ||
            objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time) {
            return ObjectLocked{...}
        }
    }
    if govPerm == ErrAccessDenied { return errAuthentication }
    return nil

// isPutRetentionAllowed
if retMode == objectlock.RetGovernance && byPassSet {
    byPassSet = globalIAMSys.IsAllowed(BypassGovernanceRetentionAction ...)
}
retSet = globalIAMSys.IsAllowed(PutObjectRetentionAction ...)
if byPassSet || retSet {
    return ErrNone
}
return ErrAccessDenied
```

- The guard that prevents weakening runs only when the header is **absent**.
- The bypass permission is evaluated only when the **requested** mode is
  GOVERNANCE. For an empty mode (removal) or COMPLIANCE, `byPassSet` is still
  the raw header value. `byPassSet || retSet` is then true for any caller that
  sent the header, even when `retSet` is false. That is **F1**.
- When the requested mode is GOVERNANCE, the bypass result is evaluated, but
  `|| retSet` discards it for any holder of `s3:PutObjectRetention`. That is
  **F2**.
- The same `||` lets a bypass holder pass when `retSet` is denied by a
  condition key. That is **F3**.

### History {#history}

- Before upstream
  [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45) (#9259,
  MinIO `RELEASE.2020-04-10T03-34-42Z`), the GOVERNANCE branch returned a
  separately computed bypass permission whenever the header was set. That
  commit added the policy condition keys, introduced `isPutRetentionAllowed`,
  and dropped the distinction.
- Upstream [#20929](https://github.com/minio/minio/pull/20929)
  (`437dd4e32`, "Fix missing authorization check for
  `PutObjectRetentionHandler`", MinIO `RELEASE.2025-02-18T16-25-55Z`) added a
  handler-entry `checkRequestAuthType(..., PutObjectRetentionAction, ...)`.
  That closed F1, but not F2 or F3.
- Upstream [#21103](https://github.com/minio/minio/pull/21103)
  (`8c7097528`, MinIO `RELEASE.2025-04-03T14-56-28Z`) replaced that entry check
  with `authenticateRequest` while reworking signature validation, and F1
  returned. SILO forked after this change, so every SILO release has all three.

## Fix design {#design}

### Invariants {#invariants}

1. **Authorize before reading state.** Every `PutObjectRetention` request must
   be allowed `s3:PutObjectRetention` before the handler reads the bucket or
   object. The object-lock condition keys are included, and an explicit Deny
   always wins.
2. **Weakening needs intent and authorization.** For a version under unexpired
   GOVERNANCE retention, a change that shortens the date, removes retention or
   changes the mode is accepted only if the header is present **and**
   `s3:BypassGovernanceRetention` is allowed with the same condition values.
3. **Bypass is additive.** `s3:BypassGovernanceRetention` never replaces
   `s3:PutObjectRetention`.
4. **The header alone grants nothing.** Without a weakening, the header is
   ignored, so clients that always send it keep working for extensions.
5. **The existing lock decides whether bypass is needed.** The version's
   current retention, and whether the change weakens it, decide whether the
   bypass permission is required. The requested `Mode` does not.

### Where each check lives {#placement}

The three lock condition keys (`s3:object-lock-mode`,
`s3:object-lock-retain-until-date`, `s3:object-lock-remaining-retention-days`)
are all derived from the **request body**, not from the stored version. The
handler parses that body before it touches the object, so it can evaluate the
full `s3:PutObjectRetention` decision at entry:

```go
// PutObjectRetentionHandler, after authenticateRequest and ParseObjectRetention:
conds := retentionConditions(r, cred, objRetention) // request-derived lock keys
if !retentionAllowed(policy.PutObjectRetentionAction, bucket, object, cred, owner, conds) {
    writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
    return
}
```

Only the weakening decision depends on stored state, so only that decision stays
in `enforceRetentionBypassForPut`:

```go
case objectlock.RetGovernance: // retention not yet expired
    weakens := objRetention.Mode != objectlock.RetGovernance ||
        objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time)
    if !weakens {
        return nil
    }
    if !objectlock.IsObjectLockGovernanceBypassSet(r.Header) {
        return ObjectLocked{...}
    }
    if !retentionAllowed(policy.BypassGovernanceRetentionAction, bucket, object, cred, owner, conds) {
        return errAuthentication
    }
    return nil
```

Branches for expired retention, for versions without retention, and for
COMPLIANCE keep their existing state rules and no longer carry permission
logic. `isPutRetentionAllowed` and its `||` are removed. Anonymous requests stay
rejected, as they are today.

### Decision table {#decision-table}

`retOK` means `s3:PutObjectRetention` is allowed with the request's lock
condition keys. `bypassOK` means `s3:BypassGovernanceRetention` is allowed with
the same keys.

| Target version | Change | Header | `retOK` | `bypassOK` | Today | Proposed |
| --- | --- | --- | --- | --- | --- | --- |
| any | any | any | no | any | often 200 (F1, F3) | **403** at entry |
| unexpired GOVERNANCE | extend | any | yes | any | 200 | 200 |
| unexpired GOVERNANCE | weaken | absent | yes | any | 400 `ObjectLocked` | 400 `ObjectLocked` |
| unexpired GOVERNANCE | weaken | present | yes | no | **200** (F2) | **403** |
| unexpired GOVERNANCE | weaken | present | yes | yes | 200 | 200 |
| unexpired COMPLIANCE | shorten or mode change | any | yes | any | 400 `ObjectLocked` | 400 `ObjectLocked` |
| no retention, or expired | any | any | yes | any | 200 | 200 |

A caller with `retOK` sees no change except in the F2 row. A 403 for an
unauthorized weakening matches the delete path, which returns `AccessDenied`
for a bypass request without the permission. The owner (root) is allowed both
actions by the IAM system, as today.

Moving the permission check to entry also means an unauthorized caller now gets
403 before learning whether the bucket or version exists. Today it can get 404
or 400 for such requests.

### Alternatives considered {#alternatives}

- **Only replace the guard's `byPassSet` with the bypass result.** This fixes
  F2 but not F1: the removal and COMPLIANCE requests never reach the guard, and
  they still pass `byPassSet || retSet` on the raw header. It also leaves F3.
- **Restore upstream #20929's entry `checkRequestAuthType`.** That check runs
  without the lock condition keys. Most condition operators do not match a
  missing key, so an Allow that depends on those keys fails at entry. A Deny
  that depends on them does not match at entry either, and only the later check
  sees it. Evaluating
  with the request-derived keys at entry gives a single, correct decision.
- **Keep all checks inside `EvalMetadataFn`.** This is correct only if every
  object-layer path reaches the callback before it writes. It also leaks the
  existence of buckets and versions to callers without permission. The
  state-independent decision belongs at entry.
- **Reject the header for callers without the bypass permission.** This breaks
  clients that send the header on every retention write, including extensions.
  The protocol treats the header as intent, so it must not be an error when no
  weakening is requested.
- **Reuse `authorizeRequest(..., BypassGovernanceRetentionAction)` as the
  delete path does.** That call lacks the lock condition keys, so bypass
  policies conditioned on them would be evaluated differently on the retention
  path. Whether the delete path should also receive those keys is left to a
  separate change.

### Notes {#notes}

- `ParseObjectRetention` rejects dates in the past (`ErrPastObjectLockRetainDate`)
  and requires an empty `Mode` to come with no date. Removal is therefore always
  an empty `<Retention/>` body.
- `s3:object-lock-remaining-retention-days` is computed as
  `ceil(|date − now| / 24h)`. For a removal the date is zero, so the key takes a
  very large value (see [mitigation](#mitigation)). After the fix, removal
  needs the bypass permission, but the key's value for removal is still
  misleading. It is tracked as a follow-up.
- Conditions on existing object tags (`s3:ExistingObjectTag/<key>`) are not
  evaluated for `PutObjectRetention` today. That limitation is unchanged by
  this design.

## Compatibility {#compatibility}

- Callers that hold `s3:PutObjectRetention` see no change, except that
  weakening GOVERNANCE now also requires `s3:BypassGovernanceRetention`.
- Callers without `s3:PutObjectRetention` now receive 403 at entry. Before,
  they could get 200 by sending the header (F1), or a 400/404 that revealed
  object state.
- A caller whose `s3:PutObjectRetention` is denied by a lock condition key
  receives 403 even when it holds bypass (F3). Review any policy that relied on
  bypass to get around such a Deny.
- **Mixed versions and replication.** Retention changes replicate as metadata
  updates and are applied through the replication trust path, not through this
  handler. A fixed site does not re-check a change that an unpatched peer
  already accepted. Every site that accepts S3 writes must be upgraded before
  the guarantee holds for a replicated bucket.

## Tests {#tests}

The tests run at handler level against a real IAM subsystem. They cover every
row of the [decision table](#decision-table), plus these cases:

- F1 against an unpatched build and the fix: a principal with no grant, and one
  with explicit Denies, attempting removal, GOVERNANCE→COMPLIANCE and a new
  COMPLIANCE lock, with and without the header, with and without `versionId`.
  Each must get 403 without changing the stored retention.
- F2: the reporter's script ends with the version still present.
- F3: a conditional Deny on `s3:PutObjectRetention` returns 403 even when
  bypass is allowed. A conditional Allow on the lock keys passes at entry.
- An explicit Deny on `s3:BypassGovernanceRetention` together with an Allow on
  `s3:*`: weakening returns 403.
- Owner, service-account and STS credentials: each follows its effective
  policy.
- An unauthorized caller gets 403 for a nonexistent bucket, a bucket without
  lock enabled, and a nonexistent version, and the response does not reveal
  which one it was.
- Unexpired COMPLIANCE: shortening and mode changes are still refused with the
  same response.

## Mitigation before a fixed release {#mitigation}

No IAM policy blocks F1, because the server evaluates no policy before
accepting the request. Until the fix ships:

- Treat every credential that can sign requests to the deployment as able to
  remove GOVERNANCE retention and to apply COMPLIANCE retention in every
  lock-enabled bucket. Do not issue credentials to parties you do not trust
  with that ability.
- Where retention must hold against such principals, use COMPLIANCE mode. F1
  can create COMPLIANCE retention but cannot remove or shorten it.
- If a reverse proxy sits in front of the Server, it can reject
  `PUT ?retention` requests that carry `x-amz-bypass-governance-retention`
  from untrusted clients. Rejecting works better than stripping the header,
  because a signed header cannot be removed without breaking the signature.
  Without the header, none of the three findings can be reached. The cost is that legitimate governance overrides through that
  proxy stop working.
- Do not rely on a Deny conditioned on
  `s3:object-lock-remaining-retention-days`. It is not evaluated for F1. For
  removal, the key's value is very large (see [notes](#notes)).
- Object metadata keeps only the current retention, so it cannot show an
  earlier change. If your audit log records request headers, review
  `PutObjectRetention` requests that carry
  `x-amz-bypass-governance-retention`. Also check for unexpected COMPLIANCE
  retention on versions.

## Delivery plan {#delivery}

1. Adversarial review of this design, then the Server patch with the tests
   above.
2. A Server release containing the fix, then a ledger entry for `SN-2026-015`
   with the fixing commit and first release.
3. A reply on GHSA-67mv-7hc9-wj88 with the fix, the widened scope and credit,
   then a CVE request.
4. Enable private vulnerability reporting on `pgsty/silo`.
5. Notify upstream MinIO on a best-effort basis: F1 reappeared there with #21103.
