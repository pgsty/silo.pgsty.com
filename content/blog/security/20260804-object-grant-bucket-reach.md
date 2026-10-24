---
title: "SN-2026-004: Object-Scoped Policy Grants Reaching Bucket Mutations"
linkTitle: "SN-2026-004: Object-Grant Reach"
date: 2026-08-04
author: "[Ruohang Feng](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "Why arn:aws:s3:::bucket/* matched bucket-level mutations when ObjectName was empty, and how SN-2026-004 closes the escalation path."
url: "/blog/security/object-grant-bucket-reach/"
tags: ["Security", "IAM", "Bucket Policy", "S3", "Authorization", "SILO"]
---

**`SN-2026-004`** fixes an IAM resource-matching flaw in [silo-pkg `v3.11.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) (`3c24ad1`, `1f97549`, `d8b1fa7`) and [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`97b7d2804`; upstream reference [`minio/minio#20449`](https://github.com/minio/minio/issues/20449)): when evaluating bucket-level S3 requests (`args.ObjectName == ""`), `Statement.IsAllowed` synthesized `"bucket/"` as the target resource string, allowing object-scoped wildcard grants such as `Allow s3:* on arn:aws:s3:::bucket/*` to authorize sensitive bucket-level mutations including `s3:PutBucketPolicy` and `s3:DeleteBucket`.

## Conclusions first {#summary}

1. **Root cause**: When `args.ObjectName` was empty, `Statement.IsAllowed` appended `'/'` to the bucket name (`"bucket/"`), which matched the glob `"arn:aws:s3:::bucket/*"`.
2. **Privilege escalation**: A tenant principal given `Allow s3:* on arn:aws:s3:::tenant/*` (a common shorthand for "all object operations inside this bucket") could call `PutBucketPolicy` to grant `Principal: "*"` on the bucket, or call `DeleteBucket`, `PutReplicationConfiguration`, `PutBucketLifecycle`, `PutBucketVersioning`, or `PutBucketObjectLockConfiguration`.
3. **Why a targeted fix was required**: Simply dropping the trailing `'/'` for all empty-object checks broke 11 existing STS `ListBucket` tests and weakened `Deny s3:* on arn:aws:s3:::bucket/*` policies.
4. **Targeted boundary**: For the 12 sensitive bucket-mutation actions on `Allow` statements (`!legacyBucketResourceMatch && statement.Effect == Allow && isSensitiveBucketMutation(args.Action)`), the resource pattern must match **both** `"bucket"` and `"bucket/"`. Setting `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` restores pre-`20260804` matching if a deployment temporarily relies on legacy policies.

---

## Why `arn:aws:s3:::bucket/*` Matched Bucket Requests {#the-defect}

In `silo-pkg/bucket/policy/statement.go` (and `iam/policy/statement.go`), `Statement.IsAllowed(args Args)` constructed the resource string to test against `Statement.Resources` as follows:

```go
resource := args.BucketName
if args.ObjectName != "" {
    if !strings.HasPrefix(args.ObjectName, "/") {
        resource += "/"
    }
    resource += args.ObjectName
} else {
    resource += "/"
}
```

Because the `else` branch unconditionally appended `"/"`, every bucket-level request (`args.ObjectName == ""`) was evaluated as `resource = "mybucket/"`. When matched against a resource pattern of `"arn:aws:s3:::mybucket/*"`, the glob wildcard `*` matched the empty suffix after `"/"` and returned `true`.

---

## Multi-Tenant Escalation Impact {#impact}

In AWS IAM and S3 bucket policies, `arn:aws:s3:::mybucket` identifies the bucket itself, whereas `arn:aws:s3:::mybucket/*` identifies objects inside the bucket. Administrators routinely write policies that grant a tenant or application team full object access using a wildcard action on the object ARN:

```json
{
  "Effect": "Allow",
  "Action": ["s3:*"],
  "Resource": ["arn:aws:s3:::tenant-a/*"]
}
```

Because `s3:*` includes both object actions and bucket actions, and `"arn:aws:s3:::tenant-a/*"` matched `resource = "tenant-a/"`, a caller holding this object-scoped policy could execute bucket-control mutations on `tenant-a`:
- **`s3:PutBucketPolicy` / `s3:DeleteBucketPolicy`**: Replace the bucket policy with `"Principal": "*"` to expose the bucket publicly or grant themselves explicit bucket-level permissions.
- **`s3:DeleteBucket` / `s3:ForceDeleteBucket`**: Delete the bucket outright.
- **`s3:PutReplicationConfiguration`**: Point bucket replication at an attacker-controlled destination to exfiltrate objects.
- **`s3:PutBucketLifecycle`**: Expire all objects and historical versions in the bucket.
- **`s3:PutBucketVersioning` / `s3:PutBucketObjectLockConfiguration`**: Suspend versioning or alter retention defaults.

---

## Why We Did Not Drop the Trailing Slash Globally {#why-narrow}

Our first prototype simply removed the `else { resource += "/" }` branch so that `args.ObjectName == ""` always evaluated against `"mybucket"`. Running the test suite and code review exposed two major regressions with a blanket change:

1. **Historical `ListBucket` compatibility**: Eleven upstream STS and IAM tests in `cmd/sts-handlers_test.go` intentionally granted `s3:ListBucket` (or `s3:*`) on `arn:aws:s3:::mybucket/*` without listing the bare bucket ARN `arn:aws:s3:::mybucket`. Dropping `"/"` for read/list actions would break existing deployments whose application policies only list `arn:aws:s3:::mybucket/*`.
2. **`Deny` statement weakening**: If an administrator wrote `Deny s3:* on arn:aws:s3:::mybucket/*` expecting it to block all operations on that bucket, evaluating `args.ObjectName == ""` against `"mybucket"` instead of `"mybucket/"` would cause the `Deny` statement to **stop matching** bucket-level calls—turning a security tightening patch into a `Deny` bypass!

---

## The Fix: Action-Scoped Dual Matching {#the-fix}

To close the escalation path without breaking `ListBucket` or weakening `Deny` statements, `Statement.IsAllowed` restricts the stricter check to `Allow` statements on sensitive bucket-level mutations (`silo-pkg v3.11.0`, wired into the server in `97b7d2804`):

```go
resource := args.BucketName
if args.ObjectName != "" {
    if !strings.HasPrefix(args.ObjectName, "/") {
        resource += "/"
    }
    resource += args.ObjectName
} else {
    resource += "/"
}

if args.ObjectName == "" && !legacyBucketResourceMatch &&
    statement.Effect == Allow && isSensitiveBucketMutation(args.Action) {
    return statement.Resources.Match(args.BucketName, args.ConditionValues) &&
        statement.Resources.Match(resource, args.ConditionValues)
}
return statement.Resources.Match(resource, args.ConditionValues)
```

For those actions on an `Allow` statement, the resource set must match `"mybucket"` (so `arn:aws:s3:::mybucket/*` alone is rejected, while `arn:aws:s3:::mybucket` or `arn:aws:s3:::*` is accepted) **and** match `"mybucket/"` (see [Why Monotonicity Required Matching Both](#monotonicity)).

---

## Second-Pass Action Audit: Which Bucket Writes Are Covered {#second-pass}

Our initial draft only gated `PutBucketPolicy` and `DeleteBucketPolicy`, overlooking `DeleteBucket` and lifecycle/replication mutations. In the second pass, we audited every bucket-level write action (`args.ObjectName == ""`) and divided them into two explicit groups.

The **12 protected sensitive bucket mutations** (`isSensitiveBucketMutation`) are:
1. `s3:PutBucketPolicy`
2. `s3:DeleteBucketPolicy`
3. `s3:DeleteBucket`
4. `s3:ForceDeleteBucket`
5. `s3:PutBucketLifecycle`
6. `s3:PutReplicationConfiguration`
7. `s3:PutBucketVersioning`
8. `s3:PutBucketObjectLockConfiguration`
9. `s3:PutBucketQuotaConfig`
10. `s3:PutBucketRetentionConfig`
11. `s3:PutBucketCors`
12. `s3:DeleteBucketCors`

*(Note: when Server `20260804` shipped, per-bucket CORS handlers were not yet active; when [Server 20260903](/blog/security/20260903-server-hardening/) implemented per-bucket CORS in [`#71`](https://github.com/pgsty/silo/issues/71) / [`#80`](https://github.com/pgsty/silo/issues/80), `s3:PutBucketCors` and `s3:DeleteBucketCors` were already protected in `isSensitiveBucketMutation`.)*

Four lower-risk or provisioning bucket actions were intentionally kept on historical matching to avoid breaking existing automation pipelines that scope credentials to `arn:aws:s3:::app-bucket/*`:
- `s3:CreateBucket` (creating the bucket itself when provisioned with a prefix-scoped policy),
- `s3:PutBucketTagging` / `s3:DeleteBucketTagging`,
- `s3:PutBucketEncryption`,
- `s3:PutBucketNotification`.

---

## Why Monotonicity Required Matching Both `"bucket"` and `"bucket/"` {#monotonicity}

We wanted a strict monotonicity guarantee: **when `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=off` (the default), no `Allow` statement may authorize a request that would have been denied under legacy matching.**

Proving that invariant took two iterations during code review:

1. **Attempt 1 (`NotResource` failure)**: When we simply tested `statement.Resources.Match(args.BucketName, ...)` instead of `"mybucket/"`, a policy using `NotResource: ["arn:aws:s3:::mybucket/*"]` flipped from **denied** (because `"mybucket/"` was inside the excluded `NotResource` set) to **allowed** (because `"mybucket"` did not match the excluded pattern).
2. **Attempt 2 (single-character `?` wildcard failure)**: Even without `NotResource`, testing only `args.BucketName` failed monotonicity on fixed-width wildcards! Consider `Allow s3:PutBucketPolicy on Resource: ["arn:aws:s3:::mybucke?"]`. Under legacy matching, `"mybucket/"` is 9 characters long, so `mybucke?` (8 characters) did **not** match and the request was denied. If the new check tested only `"mybucket"` (8 characters), `mybucke?` would suddenly match and **allow** a request that legacy mode denied (`1f97549`).

Requiring `statement.Resources.Match(args.BucketName, ...)` **and** `statement.Resources.Match(resource, ...)` (`"mybucket"` and `"mybucket/"`) guarantees mathematical monotonicity for all `Resource` and `NotResource` patterns: the new check is a pure subset (`NewAllow = LegacyAllow ∧ MatchesBareBucket`) of legacy `Allow` evaluation (`d8b1fa7`). Note that this means a synthetic pattern like `arn:aws:s3:::mybucke?` (which matches `"mybucket"` but not `"mybucket/"`) will not authorize sensitive bucket mutations; administrators should write `arn:aws:s3:::mybucket` or `arn:aws:s3:::mybucket*`.

---

## Operator Impact and Compatibility Escape Hatch {#user-facing}

- **Standard policies need no changes**: Any policy that grants bucket administration on `arn:aws:s3:::mybucket`, `arn:aws:s3:::mybucket*`, or `arn:aws:s3:::*` continues to work unchanged.
- **Object-only policies (`arn:aws:s3:::mybucket/*`)**: Can still read/write objects and call `ListBucket`, `CreateBucket`, `PutBucketEncryption`, `PutBucketTagging`, and `PutBucketNotification`, but will now receive `AccessDenied` on the 12 sensitive bucket mutations unless `arn:aws:s3:::mybucket` is explicitly added to `Resource`.
- **Escape hatch**: If an existing automation workflow requires `arn:aws:s3:::mybucket/*` to authorize one of the 12 sensitive bucket mutations during migration, set `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` until the policy is updated.

---

## Follow-Ups Left Open {#left-open}

- **Startup policy audit**: SILO does not rewrite stored IAM or bucket policies on upgrade; operators can inspect policies with `mcli admin policy info` to check whether any administrative role relied on `arn:aws:s3:::bucket/*` for bucket mutations.
- **Self-explaining denial diagnostics**: S3 `AccessDenied` responses intentionally do not disclose which statement or ARN shape failed to match.

## Summary {#closing}

Shipped in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) (`5ff00073a` and `silo-pkg` `d8b1fa7` / `v3.12.0`), the 12 sensitive bucket-mutation actions require the policy `Resource` to match the bucket ARN itself unless `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` is explicitly set.
