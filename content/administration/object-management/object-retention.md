---
title: "Silo Object Locking"
url: "/administration/object-management/object-retention/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/object-management/object-retention.rst
upstream_modified: true
---

<a id="minio-object-retention"></a>
<a id="minio-object-locking"></a>
<a id="id1"></a>

- [Object locking and retention overview](https://youtu.be/Hk9Z-sltUu8?ref=docs)
- [Object locking and retention lab](https://youtu.be/thNus-DL1u4?ref=docs)

## Overview {#overview}

MinIO Object Locking (“Object Retention”) enforces Write-Once Read-Many (WORM) immutability to protect [versioned objects](/administration/object-management/object-versioning/#minio-bucket-versioning) from deletion. MinIO supports both [duration based object retention](#minio-object-locking-retention-modes) and [indefinite legal hold retention](#minio-object-locking-legalhold).

MinIO Object Locking provides key data retention compliance and meets SEC17a-4(f), FINRA 4511(C), and CFTC 1.31(c)-(d) requirements as per [Cohasset Associates](https://min.io/cohasset?ref-docs).

{{< cards >}}
{{< card title="Bucket Without Locking" image="/images/retention/minio-versioning-delete-object.svg" image_alt="Deleting an Object" >}}
MinIO versioning preserves the full history of object mutations. However, applications can explicitly delete specific object versions.
{{< /card >}}
{{< card title="Bucket With Locking" image="/images/retention/minio-object-locking.svg" image_alt="30 Day Locked Objects" >}}
Applying a default 30 Day WORM lock to objects in the bucket ensures a minimum period of retention and protection for all object versions.
{{< /card >}}
{{< card title="Delete Operations in Locked Bucket" image="/images/retention/minio-object-locking-delete.svg" image_alt="Delete Operation in Locked Bucket" >}}
[Delete operations](/administration/object-management/object-delete/#minio-object-delete) follow normal behavior in [versioned buckets](/administration/object-management/object-versioning/#minio-bucket-versioning-delete), where MinIO creates a `DeleteMarker` for the object. However, non-Delete Marker versions of the object remain under the retention rules and are protected from any specific deletion or overwrite attempts.
{{< /card >}}
{{< card title="Versioned Delete Operations in Locked Bucket" image="/images/retention/minio-object-locking-delete-version.svg" image_alt="Versioned Delete Operation in a Locked Bucket" >}}
MinIO blocks any attempt to [delete](/administration/object-management/object-delete/#minio-object-delete) a specific object version held under WORM lock. The earliest possible time after which a client may delete the version is when the lock expires.
{{< /card >}}
{{< /cards >}}

MinIO object locking is [feature and API compatible with AWS S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html). This page summarizes Object Locking / Retention concepts as implemented by MinIO. See the AWS S3 documentation on [How S3 Object Lock works](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html) for additional resources.

You can only enable object locking during bucket creation as per [S3 behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html#object-lock-bucket-config). You cannot enable object locking on a bucket created without locking enabled. You can then configure object retention rules at any time. Object locking requires [versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) and enables the feature implicitly.

<a id="minio-bucket-locking-interactions-versioning"></a>

### Interaction with Versioning {#interaction-with-versioning}

Objects held under WORM locked are immutable until the lock expires or is explicitly lifted. Locking is per-object version, where each version is independently immutable.

If an application performs an unversioned delete operation on a locked object, the operation produces a [delete marker](/administration/object-management/object-versioning/#minio-bucket-versioning-delete). Attempts to explicitly delete any WORM-locked object fail with an error. Delete Markers are *not* eligible for protection under WORM locking. See the S3 documentation on [Managing delete markers and object lifecycles](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-managing.html#object-lock-managing-lifecycle) for more information.

For example, consider the following bucket with [GOVERNANCE Mode](#minio-object-locking-governance) locking enabled by default:

```shell
$ mc ls --versions play/locking-guide

  [DATETIME]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [DATETIME]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [DATETIME]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

Attempting to perform a delete on a *specific version* of `data.csv` fails due to the object locking settings:

```shell
$ mc rm --version-id 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 play/data.csv

  Removing `play/locking-guide/data.csv` (versionId=62429eb1-9cb7-4dc5-b507-9cc23d0cc691).
  mc: <ERROR> Failed to remove `play/locking-guide/data.csv`.
      Object, 'data.csv (Version ID=62429eb1-9cb7-4dc5-b507-9cc23d0cc691)' is
      WORM protected and cannot be overwritten
```

Attempting to perform an unversioned delete on `data.csv` succeeds and creates a new `DeleteMarker` for the object:

```shell
$ mc rm play/locking-guide/data.csv

  [DATETIME]     0B acce329f-ad32-46d9-8649-5fe8bf4ec6e0 v4 DEL data.csv
  [DATETIME]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [DATETIME]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [DATETIME]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

### Interaction with Lifecycle Management {#interaction-with-lifecycle-management}

MinIO [object expiration](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) respects any active object lock and retention settings for objects covered by the expiration rule.

- For expiration rules operating on only the *current* object version, MinIO creates a Delete Marker for the locked object.
- For expiration rules operating on *non-current object versions*, MinIO can only expire the non-current versions *after* the retention period has passed *or* has been explicitly lifted (e.g. legal holds).

For example, consider the following bucket with [GOVERNANCE Mode](#minio-object-locking-governance) locking enabled by default for 45 days:

```shell
$ mc ls --versions play/locking-guide

  [7D]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [30D]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [60D]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

Creating an expiration rule for *current* objects older than 7 days results in a Delete Marker for the object:

```shell
$ mc ls --versions play/locking-guide

  [0D]     0B acce329f-ad32-46d9-8649-5fe8bf4ec6e0 v4 DEL data.csv
  [7D]    29B 62429eb1-9cb7-4dc5-b507-9cc23d0cc691 v3 PUT data.csv
  [30D]    32B 78b3105a-02a1-4763-8054-e66add087710 v2 PUT data.csv
  [60D]    23B c6b581ca-2883-41e2-9905-0a1867b535b8 v1 PUT data.csv
```

However, an expiration rule for *non-current* objects older than 7 days would only take effect *after* the configured WORM lock expires. Since the bucket has a 45 day `GOVERNANCE` retention set, only the `v1` version of `data.csv` is unlocked and therefore eligible for deletion.

## Tutorials {#tutorials}

### Create Bucket with Object Locking Enabled {#create-bucket-with-object-locking-enabled}

You must enable object locking during bucket creation as per S3 behavior. You can create a bucket with object locking enabled using the MinIO [`mc`](/reference/minio-mc/#command-mc) CLI or using an S3-compatible SDK.

Use the [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb) command with the [`--with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) option to create a bucket with object locking enabled:

```shell
mc mb --with-lock ALIAS/BUCKET
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace `BUCKET` with the [`name`](/reference/minio-mc/mc-mb/#mc.mb.ALIAS) of the bucket to create.

### Configure Bucket-Default Object Retention {#configure-bucket-default-object-retention}

You can configure object locking rules (“object retention”) using the MinIO [`mc`](/reference/minio-mc/#command-mc) CLI, or using an S3-compatible SDK.

MinIO supports setting both bucket-default *and* per-object retention rules. The following examples set bucket-default retention. For per-object retention settings, defer to the documentation for the `PUT` operation used by your preferred SDK.

Use the [`mc retention set`](/reference/minio-mc/mc-retention-set/#command-mc.retention.set) command with the [`--recursive`](/reference/minio-mc/mc-retention-set/#mc.retention.set.-recursive) and [`--default`](/reference/minio-mc/mc-retention-set/#mc.retention.set.-default) options to set the default retention mode for a bucket:

```shell
mc retention set --recursive --default MODE DURATION ALIAS/BUCKET
```

- Replace [`MODE`](/reference/minio-mc/mc-retention-set/#mc.retention.set.MODE) with either either [COMPLIANCE](#minio-object-locking-compliance) or [GOVERNANCE](#minio-object-locking-governance).
- Replace [`DURATION`](/reference/minio-mc/mc-retention-set/#mc.retention.set.VALIDITY) with the duration for which the object lock remains in effect.
- Replace [`ALIAS`](/reference/minio-mc/mc-retention-set/#mc.retention.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace [`BUCKET`](/reference/minio-mc/mc-retention-set/#mc.retention.set.ALIAS) with the name of the bucket on which to set the default retention rule.

### Enable Legal Hold Retention {#enable-legal-hold-retention}

You can enable or disable indefinite legal hold retention for an object using the MinIO [`mc`](/reference/minio-mc/#command-mc) CLI or using an S3-compatible SDK.

You can place a legal hold on an object already held under a [COMPLIANCE](#minio-object-locking-compliance) or [GOVERNANCE](#minio-object-locking-governance) lock. The object remains WORM locked under the legal hold even when the retention lock expires. You or another user with the necessary permissions must explicitly lift the legal hold to remove the WORM lock.

Use the **mc legalhold set** command to toggle the legal hold status on an object.

```shell
mc legalhold set ALIAS/PATH
```

- Replace [`ALIAS`](/reference/minio-mc/mc-legalhold-set/#mc.legalhold.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace [`PATH`](/reference/minio-mc/mc-legalhold-set/#mc.legalhold.set.ALIAS) with the path to the object for which to enable the legal hold.

<a id="minio-object-locking-retention-modes"></a>

## Object Retention Modes {#object-retention-modes}

MinIO implements the following [S3 Object Locking Modes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html):

<table>
  <thead>
    <tr>
      <th><p>Mode</p></th>
      <th><p>Summary</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="#minio-object-locking-governance">GOVERNANCE Mode</a></p></td>
      <td><p>Prevents any operation that would mutate or modify the object or its
locking settings by non-privileged users.</p><p>Users with the <a href="/administration/identity-access-management/policy-based-access-control/#policy-action.s3-BypassGovernanceRetention"><code>s3:BypassGovernanceRetention</code></a> permission
on the bucket or object can modify the object or its locking settings.</p><p>MinIO lifts the lock automatically after the configured retention rule
duration has passed.</p></td>
    </tr>
    <tr>
      <td><p><a href="#minio-object-locking-compliance">COMPLIANCE Mode</a></p></td>
      <td><p>Prevents any operation that would mutate or modify the object or its
locking settings.</p><p>No MinIO user can modify the object or its settings, including the
<a href="/administration/identity-access-management/minio-user-management/#minio-users-root">MinIO root</a> user.</p><p>MinIO lifts the lock automatically after the configured retention rule
duration has passed.</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-object-locking-governance"></a>

### GOVERNANCE Mode {#governance-mode}

An object under `GOVERNANCE` lock is protected from write operations by non-privileged users.

`GOVERNANCE` locked objects enforce managed-immutability for locked objects, where users with the [`s3:BypassGovernanceRetention`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-BypassGovernanceRetention) action can modify the locked object, change the retention duration, or lift the lock entirely. Bypassing `GOVERNANCE` retention also requires setting the `x-amz-bypass-governance-retention:true` header as part of the request.

The MinIO `GOVERNANCE` lock is functionally identical to the [S3 GOVERNANCE mode](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-retention-modes).

<a id="minio-object-locking-compliance"></a>

### COMPLIANCE Mode {#compliance-mode}

An object under `COMPLIANCE` lock is protected from write operations by *all* users, including the [MinIO root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

`COMPLIANCE` locked objects enforce complete immutability for locked objects. You cannot change or remove the lock before the configured retention duration has passed.

The MinIO `COMPLIANCE` lock is functionally identical to the [S3 COMPLIANCE mode](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html#object-lock-retention-modes).

<a id="minio-object-locking-legalhold"></a>

## Legal Hold {#legal-hold}

An object under legal hold is protected from write operations by *all* users, including the [MinIO root](/administration/identity-access-management/minio-user-management/#minio-users-root) user.

Legal holds are indefinite and enforce complete immutability for locked objects. Only privileged users with the [`s3:PutObjectLegalHold`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutObjectLegalHold) permission can set or lift the legal hold.

Legal holds apply at the object level. If you enable legal hold for a group of objects, such as the contents of a bucket, subsequently created objects in that bucket are not affected.

Legal holds are complementary to both [GOVERNANCE Mode](#minio-object-locking-governance) and [COMPLIANCE Mode](#minio-object-locking-compliance) retention settings. An object held under both legal hold *and* a `GOVERNANCE/COMPLIANCE` retention rule remains WORM locked until the legal hold is lifted *and* the rule expires.

For `GOVERNANCE` locked objects, the legal hold prevents mutating the object *even if* the user has the necessary privileges to bypass retention.
