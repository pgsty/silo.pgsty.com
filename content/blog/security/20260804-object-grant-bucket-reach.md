---
title: "Object Grant, Bucket Reach: When 'bucket/*' Could Rewrite the Bucket Itself"
linkTitle: "Object Grant, Bucket Reach"
date: 2026-08-04
author: "Ruohang Feng"
description: "A trailing slash let an object-only IAM grant of 'arn:aws:s3:::bucket/*' reach bucket-level actions — including PutBucketPolicy, the one that can make a bucket public, and DeleteBucket, the issue's own reproduction. We shipped a narrow, deny-safe fix, then chose its final size by one question: does reaching this action give the caller anything its object access does not already provide?"
tags: [Security, Object Grant]
weight: 100
draft: false
url: "/blog/security/object-grant-bucket-reach/"
---

**Status:** Fixed on `pgsty/silo-pkg` `main` (`3c24ad1`, extended by `1f97549`, scoped to its final twelve actions in `d8b1fa7`), **released as `silo-pkg v3.11.0`**; consumed by `pgsty/minio`
**Classification:** Access-control hardening — a privilege boundary, narrowly restored
**Affected scope:** IAM users/roles/service accounts granted only object-scoped (`arn:aws:s3:::bucket/*`) access, in deployments that share a cluster across tenants
**Tracking:** upstream `minio/minio` issue [#20449](https://github.com/minio/minio/issues/20449) (public since 2024, still open)

## Conclusions first {#summary}

- In IAM policy matching, a bucket-level request carries an **empty object name**, and the matcher built its resource string as `"bucket/"`. An object-only policy pattern — `"arn:aws:s3:::bucket/*"` — then matched that string, so a grant that should cover only objects **also authorized bucket-level actions.**
- The dangerous one is **`PutBucketPolicy`**. A tenant holding only `s3:*` on `bucket/*` could install a bucket policy with `Principal:"*"` — making the bucket **publicly readable or writable** — or grant itself bucket-level control. Same mechanism, same class: `DeleteBucket`/`ForceDeleteBucket` (the issue's own reproduction), `PutReplicationConfiguration` (exfiltration), `PutBucketLifecycle` (mass deletion), `PutBucketVersioning`, `PutBucketObjectLockConfiguration`, and the rest of the bucket-configuration writes.
- The **full** correction is a two-directional behavior change: it tightens over-granting `Allow` statements **and** loosens over-blocking `Deny` statements, and it would revoke `ListBucket`/`GetBucketLocation` grants that **many real deployments write as `bucket/*` today**. That is a compatibility break, not a clean patch.
- So we shipped a **narrow** fix — first six sensitive bucket-configuration writes, then, in a second pass, **twelve**: the bucket-level writes that hand the caller something its object access does not already give it, plus four that no handler implements. Only on `Allow` statements, so no `Deny` and no `NotResource` exclusion is ever weakened, with an environment-variable escape hatch. The compatibility-sensitive read/list family, `CreateBucket`, and three bucket writes with plausible tenant use are **left unchanged, by decision**.
- Twice we claimed the change could only remove permissions, and twice an untested case said otherwise — the second time found by an independent review of a shipped release. The protected path now requires the resource to match **both** the bare and the historical form, which makes the property hold by construction rather than by argument.
- The fix is **red/green proven** at the matcher layer and end to end through the real handlers; the object-scoped hot path is untouched.

## The slash, and the empty object name {#the-defect}

Every bucket-level S3 operation authorizes with an empty object name — `checkRequestAuthType(ctx, r, policy.PutBucketPolicyAction, bucket, "")`. The IAM matcher turned that into a resource string, and for the empty-object case it appended a trailing slash:

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object"
} else {
    resource.WriteByte('/') // "bucket/"  <-- the defect
}
```

`"bucket/"` is matched by the wildcard pattern `"bucket/*"`, because `*` matches the empty string. So a policy that grants `s3:*` on `arn:aws:s3:::bucket/*` — which reads as *"anything, but only on the objects in `bucket`"* — was evaluated as granting bucket-level actions too. The bucket-policy evaluation path (for anonymous/public access) never had this slash and is the reference-correct behavior; only the IAM path was wrong, and there was exactly one place it went wrong.

This is upstream `minio/minio` #20449, filed in 2024. An early upstream attempt deleted the slash outright and was reverted the same day for breaking policies that relied on the old behavior. The lesson we took from that revert shaped the fix below.

## What it actually enables {#impact}

`PutBucketPolicyHandler` has a single authorization gate and nothing behind it. Once the IAM check passes, the caller may store **any** well-formed bucket policy for that bucket.

The concrete chain, in a multi-tenant cluster:

1. An administrator grants tenant *A* the policy `Allow s3:* on arn:aws:s3:::bucket-a/*`, intending *"A may work with the objects in `bucket-a`, nothing more."*
2. Because of the slash, *A* may call `PutBucketPolicy` on `bucket-a`.
3. *A* installs `{ "Principal": "*", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::bucket-a/*" }`. Every object in `bucket-a` is now **readable by the anonymous internet.** `s3:*` makes it world-writable. Pointing `Principal` at an account *A* controls exfiltrates the data; granting itself bucket-level actions in that policy is self-escalation.

The same object-only grant reaches other bucket-configuration writes with comparable consequences: replication to an attacker's target, a one-day lifecycle expiry that deletes the bucket's contents, disabling versioning, tampering with object-lock retention. None of these should be reachable from a grant scoped to objects.

This is not remotely exploitable and requires no missing credential — the caller is an authenticated principal you deliberately gave a scoped policy to. In a single-tenant deployment, that principal is your own trusted user and the practical risk is low. In a shared, multi-tenant cluster it is a real cross-tenant boundary failure.

## Why a narrow fix, not the whole boundary {#why-narrow}

The obvious fix is to stop appending the slash for every bucket-level request. We did not do that, for two reasons that matter more than the one-line diff suggests.

**It breaks common, benign usage.** The correction does not only revoke the dangerous bucket writes — it also revokes `ListBucket`, `GetBucketLocation`, and `ListBucketMultipartUploads` when they were granted through `bucket/*`. Many deployments write exactly that and rely on it. The evidence is upstream's own test suite: **eleven** STS integration tests grant `s3:ListBucket` on `bucket/*` and then assert that listing works. If the projects that wrote the server write it this way, production policies do too. A maintenance upgrade that turns those into `AccessDenied` is precisely the kind of surprise we refuse to ship.

**It cuts both directions.** The matcher builds the same resource string for `Allow` and `Deny`. So the full correction tightens over-granting `Allow` statements **and** simultaneously loosens over-blocking `Deny` statements: an administrator who locked a bucket with `Deny s3:* on bucket/*` would silently lose that protection for bucket-level actions. A clean-looking fix that moves security in two directions at once is not a maintenance patch — it is a migration.

So we narrowed the change to where it is unambiguously right and effectively free of compatibility cost:

- **Only bucket-level writes** are protected. The first pass covered six sensitive configuration writes: `PutBucketPolicy`, `DeleteBucketPolicy`, `PutReplicationConfiguration`, `PutBucketLifecycle`, `PutBucketVersioning`, `PutBucketObjectLockConfiguration`. The second pass (below) extended that to twelve. Almost nobody grants these through an object-only pattern on purpose — you do not accidentally rely on an object grant being able to rewrite a bucket's policy or delete the bucket — so revoking that path breaks essentially no one.
- **Only on `Allow` statements.** `Deny` statements keep the historical resource string, so no existing `Deny` is ever weakened. The narrow fix only ever *adds* a denial.
- **The read/list family is left exactly as it was.** `ListBucket` on `bucket/*` still works. That is the compatibility-sensitive part, and it waits.

## The fix {#the-fix}

The matcher keeps the trailing slash in every case except one: a bucket-level `Allow` statement being evaluated for a protected action, with the compatibility shim off.

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object" — unchanged
} else if args.BucketName == "" {
    resource.WriteByte('/') // KMS two-phase sentinel — unchanged
} else if legacyBucketResourceMatch.Load() ||
    statement.Effect != Allow ||
    !isSensitiveBucketMutation(args.Action) {
    resource.WriteByte('/') // historical behavior for Deny / non-sensitive / shim-on
}
// else: bare "bucket" — an object-only "bucket/*" no longer authorizes it
```

Because `args.Action` is the concrete request action, a wildcard grant (`s3:*`) is covered too: the wildcard matches at the action step, and by the time the resource string is built the action is the specific `PutBucketPolicy`. A bare-bucket resource (`arn:aws:s3:::bucket`) and the `*` resource still match, so correctly scoped grants — including the built-in `readwrite` policy — are untouched.

The escape hatch is `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on`, read once at startup. It restores the full historical behavior — both the over-grant and the over-block — for any operator who needs the old semantics while they adjust their policies.

## The second pass, and the question that decided its size {#second-pass}

The first round protected six configuration writes and stopped. Reviewing it against the original issue showed that was not enough: the action **reproduced in #20449 itself — `DeleteBucket` — was still reachable** through an object-only grant. An end-to-end test against the first-pass build confirmed it: a user holding nothing but `s3:*` on `arn:aws:s3:::bucket/*` called `RemoveBucket` and the bucket was gone.

Extending the set raised the real question — how far? The first instinct was "every bucket-only write except `CreateBucket`," fifteen actions. That was the wrong instinct, and the reason is a detail of how the bug fires.

**The bug only triggers when the statement already grants the bucket-level action.** Resource matching runs after action matching, so a read-only tenant holding `s3:GetObject` on `bucket/*` never reaches `DeleteBucket` — the action never matched. In practice the affected principal holds `s3:*`, which means **they already have full read, write, and delete over every object in the bucket.** That reframes the severity of each candidate action, because the question is not "how dangerous is this action in the abstract" but "what does reaching it add to a position that already includes all the data?"

By that test, three groups fall out:

**Protected — reaching these grants something the object access does not.** `PutBucketPolicy` and `DeleteBucketPolicy` hand access to other principals, anonymous included, and can grant the caller bucket-level actions it was never given: self-escalation and public exposure. `PutBucketObjectLockConfiguration` and `PutBucketVersioning` defeat protections that exist *precisely* to stop a holder of write access from destroying data. `PutReplicationConfiguration` and `PutBucketLifecycle` act under server credentials and keep acting after the caller's access is revoked. `DeleteBucket` and `ForceDeleteBucket` destroy the bucket entity and its configuration irreversibly.

**Protected at zero cost.** `PutBucketCors`, `DeleteBucketCors`, `PutBucketQOS`, and `PutInventoryConfiguration` have no MinIO server behavior attached today — no handler at all, or a handler that returns `NotImplemented` after the authorization check. Withholding them changes nothing that works, and covers them in advance if a handler is ever wired.

**Deliberately not protected.** `PutBucketTagging`, `PutBucketEncryption`, and `PutBucketNotification` are bucket-level writes, and the first draft of this pass did protect them. They came back out. None of the three gives the caller access it does not already hold — the harm is to the owner's posture, not to the access boundary — while a tenant handed `s3:*` on `bucket/*` and told "this bucket is yours" may quite reasonably tag it, set default encryption, or wire up event notifications. Low security gain against a real compatibility cost is the wrong trade for a maintenance release. They keep the historical matching, and a test now asserts that they are unprotected, so putting any of them back is a deliberate act with a visible cost rather than an edit to a list.

That leaves twelve actions, shipped as `silo-pkg v3.11.0`. Two older boundaries stand unchanged: **`CreateBucket`** keeps the historical matching (it targets a bucket that does not exist yet, and provisioning flows commonly create a tenant's bucket with that tenant's own credentials), and the **read/list family** still waits for the migration-gated change.

The choice of what to break, in other words, was made by asking *would an administrator ever write this on purpose* — not by ranking the actions by how dangerous they sound. The first question predicts which upgrades break; the second only sets urgency.

## The claim that was wrong twice {#monotonicity}

Everything above rests on one property: **this change may remove permissions and must never add one.** Both times we asserted it, we were asserting it about a mechanism we had reasoned through rather than tested through. Both times it was false.

The first pass withheld the slash from the **`NotResource`** match as well — and `NotResource` is an *exclusion*. An `Allow s3:* NotResource bucket/*` statement historically did not apply to bucket-level requests on that bucket; matching the exclusion against the bare bucket name made it stop matching, so the `Allow` it qualified **grew**, for exactly the writes being protected. Restoring the historical form for `NotResource` fixed that, and the second pass shipped saying the result was "provably monotone."

An independent adversarial review of that release produced a counterexample within the hour. Withholding the slash does not merely remove a match — it changes *which string patterns are matched against*, and a pattern can match `"mybucket"` without ever having matched `"mybucket/"`. The clean case is a fixed-width wildcard:

```text
Allow s3:PutBucketPolicy on arn:aws:s3:::mybucke?
```

`?` matches exactly one character. Against the historical nine-character `"mybucket/"` it does not match, so this statement never authorized the bucket-level write. Against the new eight-character `"mybucket"` it matches, so the hardening **granted** something the buggy matcher refused. Small in reach — you have to write a length-sensitive pattern — but it is precisely the class of defect the property was supposed to exclude, shipped in a release whose notes claimed the property held.

The fix is not another special case. On the protected path the matcher now requires **both** forms to match: the bare bucket name *and* the historical `"bucket/"`. The result is an intersection with the historical decision, so it is monotone **by construction** — there is no pattern it can newly satisfy, and no argument to get wrong next time. `mybucket*` still grants (it matched both all along); `mybucket/*` is still withheld; `mybucke?` is refused exactly as it always was. That shipped as `silo-pkg v3.11.0`.

Two things are worth taking from this beyond the patch itself. **A correctness fix in an authorization path must never make anything newly allowed** — and the only way to know is to test both directions, because the reasoning feels airtight in both cases where it wasn't. And when a security property is load-bearing, **build it out of an operation that cannot violate it** rather than out of a case analysis you believe is complete.

Regression tests now pin each direction: grants narrowed, `Deny` untouched, `NotResource` exclusions untouched, fixed-width wildcards not broadened, the three unprotected writes still reachable, plus an invariant test that every protected action really is bucket-only (`ResetBucketReplicationState`, despite its name, is an object action and stays out). In the server they run end to end through the real handlers — client, inline session policy, and the S3 router — and every one of them fails against the release that had the bug.

## What you will notice {#user-facing}

For nearly everyone: **nothing.** Object access is unchanged, `ListBucket` via `bucket/*` is unchanged, and correctly written bucket policies are unchanged.

The one visible change: a request that tries to **delete the bucket, or change its policy, replication, lifecycle, versioning, or object-lock configuration** using credentials whose only matching grant is an object-only `bucket/*` pattern now returns `AccessDenied`. Bucket tagging, default encryption, and event notification are **not** affected. That is the boundary being enforced. If a deployment genuinely depends on the old behavior, set `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` and grant those actions on the bare bucket ARN (`arn:aws:s3:::bucket`) at your own pace.

## What we deliberately left open {#left-open}

The general problem in #20449 — that `bucket/*` reaches the remaining bucket-level actions: `ListBucket`, `GetBucketLocation`, the configuration *reads*, `CreateBucket`, and the three tenant-plausible writes above — is **not** fixed here. Closing it fully means revoking grants that real deployments depend on, so it belongs to a future release that carries a migration path.

What that release owes operators is more than a wider action list, because **no one can enumerate every deployment's policies** — which means shrinking or growing the protected set by guessing is an exercise with a hard ceiling. Three things raise it:

- **A startup policy audit.** Walk the stored policies and name each one whose meaning changes, in both the grant and the deny direction. That turns an upgrade surprise into a pre-upgrade checklist, it is read-only, and it can ship *before* the enforcement change rather than with it.
- **A denial that explains itself.** When a request is refused because only an object-scoped grant matched, say exactly that, and name the compatibility switch. A break an operator can diagnose in thirty seconds costs an order of magnitude less than a silent one.
- **A switch with a scope.** `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH` is all-or-nothing today: an operator who needs one action back has to reopen the self-escalation path along with it. Per-action scoping is what makes the change safe to adopt.

Recording the boundary rather than implying it: today twelve bucket-level writes are corrected. Everything else — the read/list family, `CreateBucket`, and bucket tagging, encryption, and notification — still honors `bucket/*` as a bucket-level grant, by decision, until that migration-gated change lands.

## Closing {#closing}

A single appended slash turned *"only the objects"* into *"and the bucket too."* The tempting fix removes the slash everywhere and, in doing so, breaks a listing pattern half the world relies on and quietly weakens every `Deny` written against `bucket/*`. The fix we shipped removes it in exactly the place where an object-scoped grant should never have reached — the writes that can make a bucket public, and the ones that can delete it — and nowhere else. The rest is written down, waiting for a release where breaking it is something users are told to expect rather than something that happens to them.
