---
title: "Automatic Object Expiration"
url: "/administration/object-management/create-lifecycle-management-expiration-rule/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="automatic-object-expiration"></a>
<a id="minio-lifecycle-management-create-expiry-rule"></a>

Each procedure on this page creates a new object lifecycle management rule that expires objects on a MinIO bucket. This procedure supports use cases like removing “old” objects after a certain time period or calendar date.

## Requirements {#requirements}

### Install and Configure `mc` {#install-and-configure-mc}

This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the MinIO cluster. Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to both source and destination clusters. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

Use the [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) command to create an alias for the source MinIO cluster and the destination S3-compatible service. Alias creation requires specifying an access key for a user on the source and destination clusters. The specified users must have [permissions](#minio-lifecycle-management-create-expiry-rule-permissions) for configuring and applying expiry operations.

<a id="minio-lifecycle-management-create-expiry-rule-permissions"></a>

### Required Permissions {#required-permissions}

MinIO requires the following permissions scoped to the bucket or buckets for which you are creating lifecycle management rules.

- [`s3:PutLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-PutLifecycleConfiguration)
- [`s3:GetLifecycleConfiguration`](/administration/identity-access-management/policy-based-access-control/#policy-action.s3-GetLifecycleConfiguration)

MinIO also requires the following administrative permissions on the cluster in which you are creating remote tiers for object transition lifecycle management rules:

- [`admin:SetTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-SetTier)
- [`admin:ListTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListTier)

For example, the following policy provides permission for configuring object transition lifecycle management rules on any bucket in the cluster:.

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
            "Action": [
               "admin:SetTier",
               "admin:ListTier"
            ],
            "Effect": "Allow",
            "Sid": "EnableRemoteTierManagement"
      },
      {
            "Action": [
               "s3:PutLifecycleConfiguration",
               "s3:GetLifecycleConfiguration"
            ],
            "Resource": [
                        "arn:aws:s3:::*"
            ],
            "Effect": "Allow",
            "Sid": "EnableLifecycleManagementRules"
      }
   ]
}
```

## Expire Objects after Number of Days {#expire-objects-after-number-of-days}

Use [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) with [`--expire-days`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) to expire bucket contents a number of days after object creation:

```shell
mc ilm rule add ALIAS/PATH --expire-days "DAYS"
```

- Replace [`ALIAS`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) with the path to the bucket on the S3-compatible host.
- Replace [`DAYS`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-days) with the number of days after which to expire the object. For example, specify `30` to expire the object 30 days after creation.

## Expire Versioned Objects {#expire-versioned-objects}

Use [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) to expiring noncurrent object versions and object delete markers:

- To expire noncurrent object versions after a specific duration in days, include [`--noncurrent-expire-days`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-expire-days).
- To expire delete markers for objects with no remaining versions, include [`--expire-delete-marker`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-delete-marker).

```shell
mc ilm rule add ALIAS/PATH \
   --noncurrent-expire-days NONCURRENT_DAYS \
   --expire-delete-marker
```

- To expire all versions of an object, include [`--expire-all-object-versions`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-expire-all-object-versions). This expiration only applies to objects without a `DeleteMarker` as the latest or current version.

  ```shell
  mc ilm rule add ALIAS/PATH \
     --expire-all-object-versions
  ```
- Replace [`ALIAS`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS) with the path to the bucket on the S3-compatible host.
- Replace [`NONCURRENT_DAYS`](/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-expire-days) with the number of days after which to expire noncurrent object versions. For example, specify `30d` to expire a version after it has been noncurrent for at least 30 days.
