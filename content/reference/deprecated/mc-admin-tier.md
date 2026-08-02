---
title: "mc admin tier"
url: "/reference/deprecated/mc-admin-tier/"
weight: 190
minio_origin: true
silo_modified: false
---

<a id="mc-admin-tier"></a>

<a id="command-mc.admin.tier"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

`mc admin tier` replaced by [`mc ilm tier`](/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier).
{{% /alert %}}

## Description {#description}

The [`mc admin tier`](#command-mc.admin.tier) command configures a remote supported S3-compatible service for supporting MinIO [Lifecycle Management: Object Transition (“Tiering”)](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration).

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

### Supported S3 Services {#supported-s3-services}

[`mc admin tier`](#command-mc.admin.tier) supports *only* the following S3-compatible services as a remote target for object tiering:

- Amazon S3
- Google Cloud Storage
- Azure Blob Storage

### Required Permissions {#required-permissions}

MinIO requires the following permissions scoped to to the bucket or buckets for which you are creating lifecycle management rules.

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

#### Transition Permissions {#transition-permissions}

Object transition lifecycle management rules require additional permissions on the remote storage tier. Specifically, MinIO requires the remote tier credentials provide read, write, list, and delete permissions.

For example, if the remote storage tier implements AWS IAM policy-based access control, the following policy provides the necessary permission for transitioning objects into and out of the remote tier:

```json
{
   "Version": "2012-10-17",
   "Statement": [
      {
            "Action": [
               "s3:ListBucket"
            ],
            "Effect": "Allow",
            "Resource": [
               "arn:aws:s3:::MyDestinationBucket"
            ],
            "Sid": ""
      },
      {
            "Action": [
               "s3:GetObject",
               "s3:PutObject",
               "s3:DeleteObject"
            ],
            "Effect": "Allow",
            "Resource": [
               "arn:aws:s3:::MyDestinationBucket/*"
            ],
            "Sid": ""
      }
   ]
}

```

Modify the `Resource` for the bucket into which MinIO tiers objects.

Defer to the documentation for the supported tiering targets for more complete information on configuring users and permissions to support MinIO tiering:

- [Amazon S3 Permissions](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazons3.html#amazons3-actions-as-permissions)
- [Google Cloud Storage Access Control](https://cloud.google.com/storage/docs/access-control)
- [Authorizing access to data in Azure storage](https://docs.microsoft.com/en-us/azure/storage/common/storage-auth?toc=/azure/storage/blobs/toc.json)

## Syntax {#syntax}

#### `mc admin tier add` {#mc.admin.tier.add}

*mc-cmd*

Creates a new remote storage tier for transitioning objects using MinIO lifecycle management rules.

{{% alert color="warning" %}}
**Important**

MinIO does not support removing remote storage tiers. Ensure the storage backend supports the intended workload *prior* to adding it as a remote tier target.
{{% /alert %}}

The command has the following syntax:

```shell
mc admin tier add TIER_TYPE TARGET TIER_NAME [FLAGS]
```

The command accepts the following arguments:

#### `TIER_TYPE` {#mc.admin.tier.add.TIER_TYPE}

*mc-cmd*

*Required*

The Cloud Service Provider storage backend (“Tier”) to which MinIO transitions objects. Specify *one* of the following supported values:

<table>
  <tbody>
    <tr>
      <td><p><code>s3</code></p></td>
      <td><p>Use AWS S3 <em>or</em> a remote MinIO deployment as the storage
backend for the new Tier.</p><p>Requires specifying the following additional options:</p><ul><li><p><a href="#mc.admin.tier.add.-access-key"><code>--access-key</code></a></p></li><li><p><a href="#mc.admin.tier.add.-secret-key"><code>--secret-key</code></a></p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>azure</code></p></td>
      <td><p>Use Azure Blob Storage as the storage
backend for the new Tier.</p><p>Requires specifying the following additional options:</p><ul><li><p><a href="#mc.admin.tier.add.-account-name"><code>--account-name</code></a></p></li><li><p><a href="#mc.admin.tier.add.-account-key"><code>--account-key</code></a></p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>gcs</code></p></td>
      <td><p>Use GCP Cloud Storage as the
storage backend for the new Tier.</p><p>Requires specifying the following additional option:</p><ul><li><p><a href="#mc.admin.tier.add.-credentials-file"><code>--credentials-file</code></a></p></li></ul></td>
    </tr>
  </tbody>
</table>

#### `TARGET` {#mc.admin.tier.add.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the command creates the new remote tier.

#### `TIER_NAME` {#mc.admin.tier.add.TIER_NAME}

*mc-cmd*

*Required*

The name to associate with the new remote tier. The name *must* be unique across all configured tiers on the MinIO cluster.

You **must** specify the tier in all-caps, e.g. `WARM_TIER`.

#### `--endpoint` {#mc.admin.tier.add.-endpoint}

*mc-cmd*

*Required*

The URL endpoint for the cloud service provider. The URL endpoint *must* resolve to the provider specified to [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE).

#### `--access-key` {#mc.admin.tier.add.-access-key}

*mc-cmd*

*Required*

The access key for a user on the remote S3 tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

Required if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other value of `TIER_TYPE`.

#### `--secret-key` {#mc.admin.tier.add.-secret-key}

*mc-cmd*

*Required*

The secret key for a user on the remote S3 tier.

Required if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other value of `TIER_TYPE`.

#### `--account-name` {#mc.admin.tier.add.-account-name}

*mc-cmd*

*Required*

The account name for a user on the remote Azure tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

Required if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other value of `TIER_TYPE`.

MinIO does *not* support changing the account name associated to an Azure remote tier. Azure storage backends are tied to the account, such that changing the account would change the storage backend and prevent access to any objects transitioned to the original account/backend.

#### `--account-key` {#mc.admin.tier.add.-account-key}

*mc-cmd*

*Required*

The account key for the [`--account-name`](#mc.admin.tier.add.-account-name) associated to the remote Azure tier.

Required if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other value of `TIER_TYPE`.

#### `--credentials-file` {#mc.admin.tier.add.-credentials-file}

*mc-cmd*

*Required*

The [credential file](https://cloud.google.com/docs/authentication/getting-started) for a user on the remote GCS tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

Required if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `gcs`. This option has no effect for any other value of `TIER_TYPE`.

#### `--bucket` {#mc.admin.tier.add.-bucket}

*mc-cmd*

*Required*

The bucket on the remote tier to which MinIO transitions objects.

#### `--prefix` {#mc.admin.tier.add.-prefix}

*mc-cmd*

*Optional*

The prefix path for the specified [`--bucket`](#mc.admin.tier.add.-bucket) to which MinIO transitions objects.

Omit this field to transition objects into the bucket root.

#### `--storage-class` {#mc.admin.tier.add.-storage-class}

*mc-cmd*

*Optional*

The AWS storage class to use for objects transitioned by MinIO. MinIO supports only the following storage classes:

- `STANDARD`
- `REDUCED_REDUNDANCY`

Defaults to `S3_STANDARD` if omitted.

This option only applies if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other value of `TIER_TYPE`.

#### `--region` {#mc.admin.tier.add.-region}

*mc-cmd*

*Optional*

The S3 backend region for the specified [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE), such as `us-west-1`.

This option only applies if [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other value of `TIER_TYPE`.

#### `mc admin tier edit` {#mc.admin.tier.edit}

*mc-cmd*

Modify or remove a remote storage tier from a MinIO cluster. Remote storage tiers support transitioning objects using MinIO lifecycle management rules.

The command has the following syntax:

```shell
mc admin tier edit TARGET TIER_NAME [FLAGS]
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.tier.edit.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

#### `TIER_NAME` {#mc.admin.tier.edit.TIER_NAME}

*mc-cmd*

*Required*

The name of the remote tier the command modifies. The value corresponds to the [`mc admin tier add TIER_NAME`](#mc.admin.tier.add.TIER_NAME) specified when creating the remote tier.

#### `--access-key` {#mc.admin.tier.edit.-access-key}

*mc-cmd*

*Optional*

The access key for a user on the remote S3 tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

This option only applies to remote storage tiers with [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other `TIER_TYPE`.

#### `--secret-key` {#mc.admin.tier.edit.-secret-key}

*mc-cmd*

*Optional*

The secret key for a user on the remote S3 tier.

This option only applies to remote storage tiers with [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `s3`. This option has no effect for any other `TIER_TYPE`.

#### `--account-key` {#mc.admin.tier.edit.-account-key}

*mc-cmd*

*Required*

The account key for a user on the remote Azure tier. Use this option to rotate the credentials for the [`--account-name`](#mc.admin.tier.add.-account-name) associated to the remote tier.

This option only applies to remote storage tiers with [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other `TIER_TYPE`.

#### `--credentials-file` {#mc.admin.tier.edit.-credentials-file}

*mc-cmd*

*Required*

The credential file for a user on the remote GCS tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

This option only applies to remote storage tiers with [`TIER_TYPE`](#mc.admin.tier.add.TIER_TYPE) is `gcs`. This option has no effect for any other `TIER_TYPE`.

#### `mc admin tier ls` {#mc.admin.tier.ls}

*mc-cmd*

List all remote storage tiers on a MinIO cluster. Remote storage tiers support transitioning objects using MinIO lifecycle management rules.

The command has the following syntax:

```shell
mc admin tier ls TARGET [FLAGS]
```

The command accepts the following arguments:

#### `TARGET` {#mc.admin.tier.ls.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
