---
title: "Transition Objects from MinIO to GCS"
url: "/administration/object-management/transition-objects-to-gcs/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="transition-objects-from-minio-to-gcs"></a>
<a id="minio-lifecycle-management-transition-to-gcs"></a>

The procedure on this page creates a new object lifecycle management rule that transition objects from a MinIO bucket to a remote storage tier on the Google Cloud Storage backend. This procedure supports use cases like moving aged data to low-cost public cloud storage solutions after a certain time period or calendar date.

## Requirements {#requirements}

### Install and Configure `mc` {#install-and-configure-mc}

This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the MinIO cluster. Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to both source and destination clusters. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

Use the [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) command to create an alias for the source MinIO cluster. Alias creation requires specifying an access key for a user on the source and destination clusters. The specified users must have [permissions](#minio-lifecycle-management-transition-to-gcs-permissions) for configuring and applying transition operations.

<a id="minio-lifecycle-management-transition-to-gcs-permissions"></a>

### Required MinIO Permissions {#required-minio-permissions}

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

<a id="minio-lifecycle-management-transition-to-gcs-permissions-remote"></a>

### Required GCS Permissions {#required-gcs-permissions}

Object transition lifecycle management rules require additional permissions on the remote storage tier. Specifically, MinIO requires the <abbr title="Google Cloud Storage">GCS</abbr> credentials provide read, write, list, and delete permissions for the remote bucket.

Refer to the [GCS IAM permissions](https://cloud.google.com/storage/docs/access-control/iam-permissions) documentation for more complete guidance on configuring the required permissions.

### Remote Bucket Must Exist {#remote-bucket-must-exist}

Create the remote GCS bucket *prior* to configuring lifecycle management tiers or rules using that bucket as the target.

If you set a default GCS [storage class](https://cloud.google.com/storage/docs/storage-classes), MinIO uses that default *if* you do not specify a [`storage class`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-storage-class) when defining the remote tier. Ensure you document the settings of both your GCS bucket and MinIO tiering configuration to avoid any potential confusion, misconfiguration, or other unexpected outcomes.

## Considerations {#considerations}

### Lifecycle Management Object Scanner {#lifecycle-management-object-scanner}

MinIO uses a [scanner process](/operations/concepts/scanner/#minio-concepts-scanner) to check objects against all configured lifecycle management rules. Slow scanning due to high IO workloads or limited system resources may delay application of lifecycle management rules. See [Lifecycle Management Object Scanner](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-scanner) for more information.

### Exclusive Access to Remote Data {#exclusive-access-to-remote-data}

MinIO *requires* exclusive access to the transitioned data on the remote storage tier. Object metadata on the “hot” MinIO source is strongly linked to the object data on the “warm/cold” remote tier. MinIO cannot retrieve object data without access to the remote, nor can the remote be used to restore lost metadata on the source.

All access to the transitioned objects *must* occur through MinIO via S3 API operations only. Manually modifying a transitioned object - whether the metadata on the “hot” MinIO tier *or* the object data on the remote “warm/cold” tier - may result in loss of that object data.

MinIO ignores any objects in the remote bucket or bucket prefix not explicitly managed by the MinIO deployment. Automatic transition and transparent object retrieval depend on the following assumptions:

- No external mutation, migration, or deletion of objects on the remote storage.
- No lifecycle management rules (e.g. transition or expiration) on the remote storage bucket.

MinIO stores all transitioned objects in the remote storage bucket or resource under a unique per-deployment prefix value. This value is not intended to support identifying the source deployment from the backend. MinIO supports an additional optional human-readable prefix when configuring the remote target, which may facilitate operations related to diagnostics, maintenance, or disaster recovery.

MinIO recommends specifying this optional prefix for remote storage tiers which contain other data, including transitioned objects from other MinIO deployments. This tutorial includes the necessary syntax for setting this prefix.

### Availability of Remote Data {#availability-of-remote-data}

MinIO tiering behavior depends on the remote storage returning objects immediately (milliseconds to seconds) upon request. MinIO therefore *cannot* support remote storage which requires rehydration, wait periods, or manual intervention.

MinIO creates metadata for each transitioned object that identifies its location on the remote storage. Applications cannot trivially identify and access a transitioned object independent of MinIO. Availability of the transitioned data therefore depends on the same core protections that [erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) and distributed deployment topologies provide for all objects on the MinIO deployment. Using object transition does not provide any additional business continuity or disaster recovery benefits.

Workloads that require <abbr title="Business Continuity/Disaster Recovery">BC/DR</abbr> protections should implement MinIO [Server-Side replication](/administration/bucket-replication/#minio-bucket-replication-serverside). Replication ensures objects remains preserved on the remote replication site, such that you can resynchronize from the remote in the event of partial or total data loss. See [Resynchronization (Disaster Recovery)](/administration/bucket-replication/#minio-replication-behavior-resync) for more complete documentation on using replication to recover after partial or total data loss.

## Procedure {#procedure}

### 1) Configure User Accounts and Policies for Lifecycle Management {#configure-user-accounts-and-policies-for-lifecycle-management}

This step creates users and policies on the MinIO deployment for supporting lifecycle management operations. You can skip this step if the deployment already has users with the necessary [permissions](#minio-lifecycle-management-transition-to-gcs-permissions).

The following example uses `Alpha` as a placeholder [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for the MinIO deployment. Replace this value with the appropriate alias for the MinIO deployment on which you are configuring lifecycle management rules. Replace the password `LongRandomSecretKey` with a long, random, and secure secret key as per your organizations best practices for password generation.

```shell
wget -O - https://silo.pigsty.io/examples/LifecycleManagementAdmin.json | \
mc admin policy create Alpha LifecycleAdminPolicy /dev/stdin
mc admin user add Alpha alphaLifecycleAdmin LongRandomSecretKey
mc admin policy attach Alpha LifecycleAdminPolicy --user=alphaLifecycleAdmin
```

This example assumes that the specified aliases have the necessary permissions for creating policies and users on the deployment. See [User Management](/administration/identity-access-management/minio-user-management/#minio-users) and [MinIO Policy Based Access Control](/administration/identity-access-management/policy-based-access-control/#minio-policy) for more complete documentation on MinIO users and policies respectively.

### 2) Configure the Remote Storage Tier {#configure-the-remote-storage-tier}

Use the [`mc ilm tier add`](/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add) command to add a new Google Cloud Storage service as the remote storage tier:

```shell
mc ilm tier add gcs TARGET TIER_NAME \
   --bucket BUCKET \
   --prefix PREFIX \
   --credentials-file CREDENTIALS \
   --storage-class STORAGE_CLASS
```

The example above uses the following arguments:

<table>
  <thead>
    <tr>
      <th><p>Argument</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TARGET"><code>TARGET</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-alias/#command-mc.alias"><code>alias</code></a> of the MinIO deployment on which to configure
the GCS remote tier.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_NAME"><code>TIER_NAME</code></a></p></td>
      <td><p>The name to associate with the new GCS
remote storage tier. Specify the name in all-caps, e.g. <code>GCS_TIER</code>.
This value is required in the next step.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-bucket"><code>BUCKET</code></a></p></td>
      <td><p>The name of the bucket on the GCS storage
backend to which MinIO transitions objects.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-prefix"><code>PREFIX</code></a></p></td>
      <td><p>The optional bucket prefix within which MinIO transitions objects.</p><p>MinIO stores all transitioned objects in the specified <code>BUCKET</code> under a
unique per-deployment prefix value. Omit this argument to use only that
value for isolating and organizing data within the remote storage.</p><p>MinIO recommends specifying this optional prefix for remote storage tiers
which contain other data, including transitioned objects from other MinIO
deployments. This prefix should provide a clear reference back to the
source MinIO deployment to facilitate ease of operations related to
diagnostics, maintenance, or disaster recovery.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-credentials-file"><code>CREDENTIALS</code></a></p></td>
      <td><p>The <a href="https://cloud.google.com/docs/authentication/getting-started">credential file</a> for a
user on the remote GCS tier. The specified user credentials <em>must</em>
correspond to a GCS user with the required
<a href="#minio-lifecycle-management-transition-to-gcs-permissions-remote">permissions</a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-storage-class"><code>STORAGE_CLASS</code></a></p></td>
      <td><p>The GCS storage class MinIO applies to objects transitioned to the GCS bucket.</p><p>MinIO tiering behavior depends on the remote storage returning objects immediately (milliseconds to seconds) upon request.
MinIO therefore <em>cannot</em> support remote storage which requires rehydration, wait periods, or manual intervention.</p><p>The following GCS storage classes meet MinIO’s requirements as a remote tier:</p><ul><li><p><code>STANDARD</code></p></li><li><p><code>NEARLINE</code></p></li><li><p><code>COLDLINE</code></p></li></ul><p>For more information, see <a href="https://cloud.google.com/storage/docs/storage-classes">GCS storage class</a>.</p></td>
    </tr>
  </tbody>
</table>

### 3) Create and Apply the Transition Rule {#create-and-apply-the-transition-rule}

Use the [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) command to create a new transition rule for the bucket. The following example configures transition after the specified number of calendar days:

```shell
mc ilm rule add ALIAS/BUCKET \
--transition-tier TIERNAME \
--transition-days DAYS \
--noncurrent-transition-days NONCURRENT_DAYS
--noncurrent-transition-tier TIERNAME
```

The example above specifies the following arguments:

<table>
  <thead>
    <tr>
      <th><p>Argument</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS"><code>ALIAS</code></a></p></td>
      <td><p>Specify the <a href="/reference/minio-mc/mc-alias/#command-mc.alias"><code>alias</code></a> of the MinIO deployment for which
you are creating the lifecycle management rule.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.ALIAS"><code>BUCKET</code></a></p></td>
      <td><p>Specify the full path to the bucket for which you are
creating the lifecycle management rule.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-transition-tier"><code>TIERNAME</code></a></p></td>
      <td><p>The remote storage tier to which MinIO transitions objects.
Specify the remote storage tier name created in the previous step.</p><p>If you want to transition noncurrent object versions to a distinct
remote tier, specify a different tier name for
<a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-transition-tier"><code>--noncurrent-transition-tier</code></a>.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-transition-days"><code>DAYS</code></a></p></td>
      <td><p>The number of calendar days after which MinIO marks an object as
eligible for transition. Specify the number of days as an integer,
e.g. <code>30</code> for 30 days.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-ilm-rule-add/#mc.ilm.rule.add.-noncurrent-transition-days"><code>NONCURRENT_DAYS</code></a></p></td>
      <td><p>The number of calendar days after which MinIO marks a noncurrent
object version as eligible for transition. MinIO specifically measures
the time since an object <em>became</em> non-current instead of the object
creation time. Specify the number of days as an integer,
e.g. <code>90</code> for 90 days.</p><p>Omit this value to ignore noncurrent object versions.</p><p>This option has no effect on non-versioned buckets.</p></td>
    </tr>
  </tbody>
</table>

### 4) Verify the Transition Rule {#verify-the-transition-rule}

Use the [`mc ilm rule ls`](/reference/minio-mc/mc-ilm-rule-ls/#command-mc.ilm.rule.ls) command to review the configured transition rules:

```shell
mc ilm rule ls ALIAS/PATH --transition
```

- Replace [`ALIAS`](/reference/minio-mc/mc-ilm-rule-ls/#mc.ilm.rule.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](/reference/minio-mc/mc-ilm-rule-ls/#mc.ilm.rule.ls.ALIAS) with the name of the bucket for which to retrieve the configured lifecycle management rules.
