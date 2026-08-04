---
title: "Object Grant, Bucket Reach: When 'bucket/*' Could Rewrite the Bucket Itself"
linkTitle: "Object Grant, Bucket Reach"
date: 2026-08-04
author: "Ruohang Feng"
description: "A trailing slash let an object-only IAM grant of 'arn:aws:s3:::bucket/*' reach bucket-level actions — including PutBucketPolicy, the one that can make a bucket public. We shipped a narrow, deny-safe fix for the dangerous writes and deliberately left the rest for a migration-gated change."
tags: [Security, Object Grant]
weight: 100
draft: false
url: "/blog/security/object-grant-bucket-reach/"
---

**Status:** Fixed on `pgsty/silo-pkg` `main` as `3c24ad1`, **unreleased** (not yet published or bumped into a server build)
**Classification:** Access-control hardening — a privilege boundary, narrowly restored
**Affected scope:** IAM users/roles/service accounts granted only object-scoped (`arn:aws:s3:::bucket/*`) access, in deployments that share a cluster across tenants
**Tracking:** upstream `minio/minio` issue [#20449](https://github.com/minio/minio/issues/20449) (public since 2024, still open)

## Conclusions first {#summary}

- In IAM policy matching, a bucket-level request carries an **empty object name**, and the matcher built its resource string as `"bucket/"`. An object-only policy pattern — `"arn:aws:s3:::bucket/*"` — then matched that string, so a grant that should cover only objects **also authorized bucket-level actions.**
- The dangerous one is **`PutBucketPolicy`**. A tenant holding only `s3:*` on `bucket/*` could install a bucket policy with `Principal:"*"` — making the bucket **publicly readable or writable** — or grant itself bucket-level control. Same mechanism, same class: `PutReplicationConfiguration` (exfiltration), `PutBucketLifecycle` (mass deletion), `PutBucketVersioning`, `PutBucketObjectLockConfiguration`.
- The **full** correction is a two-directional behavior change: it tightens over-granting `Allow` statements **and** loosens over-blocking `Deny` statements, and it would revoke `ListBucket`/`GetBucketLocation` grants that **many real deployments write as `bucket/*` today**. That is a compatibility break, not a clean patch.
- So we shipped a **narrow** fix: only a small set of **sensitive bucket-configuration writes** stop being reachable through `bucket/*`, only on `Allow` statements (so no `Deny` is ever weakened), with an environment-variable escape hatch. The compatibility-sensitive read/list family is **left unchanged, by decision**.
- The fix is **red/green proven** at the matcher layer; the object-scoped hot path is untouched.

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

- **Only sensitive bucket-configuration writes** are protected: `PutBucketPolicy`, `DeleteBucketPolicy`, `PutReplicationConfiguration`, `PutBucketLifecycle`, `PutBucketVersioning`, `PutBucketObjectLockConfiguration`. Almost nobody grants these through an object-only pattern on purpose — you do not accidentally rely on an object grant being able to rewrite a bucket's policy — so revoking that path breaks essentially no one.
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

## What you will notice {#user-facing}

For nearly everyone: **nothing.** Object access is unchanged, `ListBucket` via `bucket/*` is unchanged, and correctly written bucket policies are unchanged.

The one visible change: a request that tries to **change a bucket's policy, replication, lifecycle, versioning, or object-lock configuration** using credentials whose only matching grant is an object-only `bucket/*` pattern now returns `AccessDenied`. That is the boundary being enforced. If a deployment genuinely depends on the old behavior, set `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` and grant those actions on the bare bucket ARN (`arn:aws:s3:::bucket`) at your own pace.

## What we deliberately left open {#left-open}

The general problem in #20449 — that `bucket/*` reaches *any* bucket-level action, including `ListBucket`, `DeleteBucket`, and the lifecycle/versioning *reads* — is **not** fixed here. Closing it fully means revoking grants that real deployments depend on, so it belongs to a future release that carries a migration path: a startup audit that names every stored policy about to change (in both the grant and the deny direction), the same compatibility switch, and release notes that tell operators what to fix before they upgrade.

Recording the boundary rather than implying it: today only the six sensitive writes are corrected. The read/list/delete-bucket family still honors `bucket/*` as a bucket-level grant, by decision, until that migration-gated change lands.

## Closing {#closing}

A single appended slash turned *"only the objects"* into *"and the bucket too."* The tempting fix removes the slash everywhere and, in doing so, breaks a listing pattern half the world relies on and quietly weakens every `Deny` written against `bucket/*`. The fix we shipped removes it in exactly the place where an object-scoped grant should never have reached — the writes that can make a bucket public — and nowhere else. The rest is written down, waiting for a release where breaking it is something users are told to expect rather than something that happens to them.
