---
title: "Governance Retention Bypass: Origin Record and Repair"
linkTitle: "Governance Retention Bypass Repair"
date: 2026-10-10
lastmod: 2026-10-10
author: "Ruohang Feng"
summary: >
  The research and repair record for SN-2026-015: where the authorization flaw
  was introduced upstream and how a 2025 refactor regressed the partial fix, how
  a subsequent external report's claims verified against the code, which fix
  shapes work and which cannot, what the branch tests establish, and the
  companion version-addressed-write fix recorded as SN-2026-016.
tags: [Design, Security, Object Lock, IAM]
weight: 7
draft: true
url: "/blog/design/governance-retention-bypass-repair/"
---

> **Draft, 2026-10-10 — not published.** This is the internal research and
> repair record for [`SN-2026-015`](/blog/security/20260926-governance-retention-bypass/).
> The security advisory there owns the public scope (F1–F3), fix design and
> mitigation guidance; this page adds the origin record, the verification of a
> subsequent external report, the fix-shape comparison and the implemented
> tests. The fix lives on Server branch `fix/sn-2026-015-016`, uncommitted as
> of this date. Keep this draft unpublished until the fixing release is out and
> the companion finding (SN-2026-016, below) has its own disclosure.

## What this record adds {#scope}

The [advisory](/blog/security/20260926-governance-retention-bypass/) fixed the
scope and the fix design. Four things were not, and are not intended to be, in
that page:

1. The complete origin record: the correct pre-2020 design, the commit that
   broke it, the mechanical decade in between, the 2025 partial fix, and the
   unrelated refactor that regressed it — with the evidence for each step
   ([below](#origin)).
2. A claim-by-claim verification of a further external report received after
   the advisory ([below](#report)): every claim checked against the code and,
   where relevant, against a release binary.
3. The fix-shape comparison in construction terms — what was built, what the
   reporter proposed, and two shapes that cannot work
   ([below](#shapes)).
4. The implemented repair and its test matrix, including what the branch tests
   do **not** yet cover from the advisory's plan, and the companion
   version-addressed-write fix recorded as [SN-2026-016](#companion).

Analysis baseline: Server `main` at [`4f62e8f19`](https://github.com/pgsty/silo/commit/4f62e8f19)
(2026-10-10), full git history, and upstream `minio/minio` master pulled the
same day. The reporter's pinned release was
[`9b11dc94`](https://github.com/pgsty/silo/commit/9b11dc94)
(`RELEASE.2026-09-03T13-18-01Z`); every mechanism is identical on both, and on
`RELEASE.2026-09-16T00-00-00Z`.

## The October report, verified {#report}

A further external report (signed "Nik"; analyzed 2026-10-10) independently
described the bypass and added claims about upstream impact. Its three symptoms
match F1/F2 as scoped in the advisory. Verified claim by claim:

| Report claim | Verdict |
| --- | --- |
| A principal with `s3:PutObjectRetention` but no bypass can flip GOVERNANCE to COMPLIANCE using the raw header, with no Deny involved | **Confirmed** (F1 shape) |
| A conditional Deny on `s3:PutObjectRetention` (lock condition keys) is bypassed by the header | **Confirmed** (F3 shape) |
| A principal without the bypass permission can shorten GOVERNANCE retention | **Confirmed** (F2, the originally reported case) |
| "An unconditional Deny does stop the request, at entry auth" | **Wrong — the impact is larger.** `authenticateRequest` verifies the signature only; an unconditional Deny, and principals with no grant at all, are also bypassed when the header is present (advisory F1). Reproduced on the 2026-09-16 release binary. |
| In SILO, version deletes need `s3:DeleteObjectVersion`, limiting F2; upstream checks it deny-only, so the ransomware chain completes there | **Confirmed**: [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) (2026-09-02) made explicit version deletes a full permission; upstream master evaluates it with `DenyOnly: true` (`cmd/auth-handler.go:475` as of 2026-10-10) |
| Existing COMPLIANCE retention cannot be shortened even with the header | **Confirmed** — the only boundary that held |
| The same code exists in `minio/minio` master (`cmd/auth-handler.go:677-717`) | **Confirmed byte-for-byte** (handler entry, `enforceRetentionBypassForPut`, `isPutRetentionAllowed`), pulled 2026-10-10 |
| The flaw is in the server `cmd/`, not in `silo-pkg`; the policy engine evaluates Denies correctly | **Confirmed** |
| Suggested fix: authorize the bypass once, use the authorized result everywhere, make the base permission mandatory | **Adopted** — subsumed by the implemented shape ([below](#shapes)) |

The report's line references (`auth-handler.go:743-783`,
`object-handlers.go:3164/3205`) match `9b11dc94`; on the analysis baseline the
same code sits at `:736-777` and `:3439/:3480` after unrelated commits.

## Origin record {#origin}

### The design before the flaw {#origin-before}

Until April 2020 the authorization shape was correct. The handler authorized
the base permission at entry, and the bypass permission was evaluated
separately and passed down **as an already-authorized result**:

```go
// 43a3778b4^ : cmd/object-handlers.go (PutObjectRetentionHandler entry)
	// Check permissions to perform this governance operation
	if s3Err := checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object); s3Err != ErrNone {
		...
	}

// 43a3778b4^ : cmd/object-handlers.go:2549 — bypass pre-authorized, then passed down
	govBypassPerms := checkRequestAuthType(ctx, r, policy.BypassGovernanceRetentionAction, bucket, object)

// 43a3778b4^ : cmd/object-lock.go:87 — receives an authorization result, not a header
	func enforceRetentionBypassForPut(..., govBypassPerm APIErrorCode, ...) (oi ObjectInfo, s3Err APIErrorCode)
```

The raw header decided only *whether the bypass branch was needed*; it never
entered an authorization decision. This lineage starts with
[`ca96560d5`](https://github.com/minio/minio/commit/ca96560d5) (per-object
retention, 2019-11-20) and
[`f931fc7bf`](https://github.com/minio/minio/commit/f931fc7bf)
(`enforceRetentionBypassForPut`, 2019-11-25), with the entry call refined by
[#9030](https://github.com/minio/minio/pull/9030) (2020-03-04).

### Introduction: #9259, 2020-04-06 {#origin-intro}

Upstream [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45)
([#9259](https://github.com/minio/minio/pull/9259), Harshavardhana, "fix:
support object-remaining-retention-days policy condition") introduced the
authorization flaw in one rewrite. The commit's own message says it "fixed a
couple of bugs related to how policy should have been honored when
ByPassGovernance is provided" — it was itself a fix. What it did:

1. **Removed the entry authorization**, replacing `checkRequestAuthType` with
   signature-only `validateSignature`.
2. **Dropped the pre-authorized parameter** (`govBypassPerm`), passing the
   **raw header** `byPassSet` into the new helper instead.
3. **Created `isPutRetentionAllowed`** with the two load-bearing mistakes
   documented in the advisory: the bypass permission is only evaluated when the
   *requested* mode is GOVERNANCE (removal and COMPLIANCE never validate it),
   and the final `byPassSet || retSet` makes the bypass result advisory.

There was no permission-matrix regression test for `PutObjectRetention` to
catch any of this — there never had been.

### Mechanical decade {#origin-mechanical}

- [#9513](https://github.com/minio/minio/pull/9513) (2020-05) and
  [#9377](https://github.com/minio/minio/pull/9377) (2020-06) moved the
  enforcement into `cmd/bucket-object-lock.go`; shapes unchanged.
- [#12947](https://github.com/minio/minio/pull/12947)
  ([`8f2a3efa8`](https://github.com/minio/minio/commit/8f2a3efa8), 2021-08)
  cleaned up sub-credential handling in the helper and deleted its anonymous
  branch; the `||` survived. Blame on the analysis baseline still attributes 31
  of the helper's 43 lines to `43a3778b4`.

### Partial fix, then regression (2025) {#origin-regression}

- [#20929](https://github.com/minio/minio/pull/20929)
  ([`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32), Ramon de
  Klein, 2025-02-12) added the entry `checkRequestAuthType` back — "Fix missing
  authorization check for `PutObjectRetentionHandler`". This closed F1 at entry
  for about fifty days. F2 and F3 lived on inside the helper.
- [#21103](https://github.com/minio/minio/pull/21103)
  ([`8c7097528`](https://github.com/minio/minio/commit/8c7097528), 2025-04-03)
  was a security fix for unsigned-payload trailer signature validation. While
  reworking signature validation across handlers it **mechanically replaced**
  the entry check with `authenticateRequest` (signature-only, born in
  [#15777](https://github.com/minio/minio/pull/15777), 2022-10) — and kept the
  old comment:

  ```diff
  -	if s3Err := checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object); s3Err != ErrNone {
  -		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Err), r.URL)
  -		return
  -	}
  -
  -	cred, owner, s3Err := validateSignature(getRequestAuthType(r), r)
  -	if s3Err != ErrNone {
  -		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Err), r.URL)
  +	if s3Error := authenticateRequest(ctx, r, policy.PutObjectRetentionAction); s3Error != ErrNone {
  +		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Error), r.URL)
   		return
   	}
  ```

  The retained "Check permissions to perform this object retention operation"
  comment hid the semantic loss. No test noticed. F1 returned, and upstream
  master is still in this state as of 2026-10-10.

### SILO inheritance {#origin-fork}

The fork point [`27742d469`](https://github.com/pgsty/silo/commit/27742d469)
(2025-12-03) postdates the regression, so every SILO release inherited the full
flaw: `RELEASE.2026-04-17`, `2026-06-18`, `2026-08-04`, `2026-08-06`,
`2026-09-03` and `2026-09-16`. The only SILO-side commit that touched this
area, [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4)
(2026-09-02), *tightened* version-delete authorization; nothing in SILO
modified the vulnerable chain.

## Why the design failed {#cause}

Condensed from the advisory's root cause; three defects, one per layer:

1. **Intent conflated with authorization.** One variable (`byPassSet`) carries
   the client's header, then sometimes an authorization result, and finally
   gates both the weakening guard (`if !byPassSet`) and the helper's verdict.
2. **The guard conditions on the wrong mode.** Bypass is about the *stored*
   GOVERNANCE lock; the code conditions on the *requested* mode, so removal and
   COMPLIANCE requests never validate the bypass permission at all.
3. **No state-independent authorization at entry.** Once #9259 removed the
   entry check, the only policy evaluation for this API lived inside the
   function the header short-circuits — and the lock condition keys, which come
   from the request body, could be evaluated nowhere else.

The systemic cause across all six years: no permission-matrix test for
`PutObjectRetention` ever existed, so introduction (2020), partial fix (2025)
and regression (2025) all shipped without CI resistance.

## Fix shapes {#shapes}

- **A — adopted (advisory design, implemented on the branch).** Evaluate
  `s3:PutObjectRetention` with request-derived lock condition keys at entry,
  before any bucket or object read; reduce `enforceRetentionBypassForPut` to
  the stored-state weakening rule (header + authorized
  `s3:BypassGovernanceRetention` for weakening unexpired GOVERNANCE;
  COMPLIANCE extend-only); delete `isPutRetentionAllowed`. This is the
  advisory's design verbatim.
- **B — the October report's suggestion.** Authorize the bypass once inside
  `enforceRetentionBypassForPut` when the header is set, use that result for
  both the weakening rule and the downstream decision, and make the base
  permission mandatory. Equivalent to A for all three findings; A additionally
  rejects unauthorized callers before any state read. Absorbed.
- **C — minimal patch.** Keep the old helper; fix its guard (condition on the
  stored mode), consume `byPassSet` after use, and change the `||` to require
  the base permission plus, when weakening, the authorized bypass. Rejected for
  the same state-read-before-reject leak as keeping checks in `EvalMetadataFn`
  (advisory alternatives), but this is the shape to offer upstream as a
  backport.
- **D — middleware authorization.** Route `PutObjectRetention` through the
  auth handler's default authorization. Not viable: the lock condition keys
  come from the request body, which no middleware can parse without breaking
  the stream; evaluating without them would silently never match conditional
  Denies — the report's symptom, relocated.

## What landed on the branch {#implemented}

Branch `fix/sn-2026-015-016`, uncommitted at this date:

- `cmd/object-handlers.go`: after `ParseObjectRetention`, and before
  `GetBucketInfo` or lock-config reads, the base permission is evaluated via
  the new `isRetentionActionAllowed(PutObjectRetentionAction, ...)`. The
  misleading entry comment is gone.
- `cmd/bucket-object-lock.go`: new `isRetentionActionAllowed` builds the three
  lock condition keys from the request and evaluates any action once;
  `enforceRetentionBypassForPut` rewritten to the stored-state rule with the
  authorized bypass check; the raw header is read only to decide whether the
  intent is declared.
- `cmd/auth-handler.go`: `isPutRetentionAllowed` deleted.

`cmd/object-retention-authz_test.go` runs 15 decision-table cases plus a
missing-bucket 403 against a real IAM subsystem, across five principals (no
grant, base-only, base+bypass, bypass-only, owner), on ErasureSD and Erasure:
**50 subtests, all passing** (2026-10-10). Key semantics pinned: extending
GOVERNANCE needs no bypass; bypass-only without the base permission is denied;
COMPLIANCE refuses shortening even with bypass; an unauthorized caller gets 403
before learning whether the bucket exists.

Not yet covered from the advisory's test plan, to add before release: a
conditional Deny on the lock keys as an explicit test user (F3 is covered
today by construction, through the same `IsAllowed` path, but not named), STS
and service-account credential variants, and the end-to-end
shorten-then-delete chain from the original report.

## Companion fix: version-addressed writes {#companion}

The same branch carries a second repair, recorded as **SN-2026-016**: `putOpts`
honored a caller-chosen `versionId` on `PutObject`, `CopyObject` and multipart
initiation, letting any writer replace an existing version — including a
locked one — in place, which defeats object lock from the write side. The fix
(`cmd/object-api-options.go`) rejects a caller-supplied destination version ID
unless the request comes through the trusted replication path; the existing
conditional-PUT pool test now expects 403 for version-addressed public writes,
and `TestAPIVersionAddressedWriteRequiresReplicationTrust` covers
PUT/CopyObject/multipart/null-version for writer and owner, plus the trusted
replication exemption keeping its version ID. This finding has no public
advisory yet; it is one reason this record stays a draft.

## Delivery checklist {#delivery}

1. Complete the missing test coverage above, adversarial review, then commit
   the branch (`git commit -s`) and merge after CI.
2. Release, then update the
   [advisory](/blog/security/20260926-governance-retention-bypass/) status and
   the ledger; bump `security_fixes` only after the release is out.
3. Publish this record (drop `draft: true`) once SN-2026-016 has its own
   disclosure; credit the October reporter alongside the advisory's credits.
4. Reply on GHSA-67mv-7hc9-wj88, request the CVE, and notify upstream MinIO:
   F1 is live there again since #21103 and master still carries it
   (2026-10-10).
