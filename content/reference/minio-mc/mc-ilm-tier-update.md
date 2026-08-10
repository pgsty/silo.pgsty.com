---
title: "mc ilm tier update"
url: "/reference/minio-mc/mc-ilm-tier-update/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-tier-update"></a>
<a id="minio-mc-ilm-tier-update"></a>

<a id="command-mc.ilm.tier.update"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

[`mc ilm tier update`](#command-mc.ilm.tier.update) replaces `mc admin tier edit`.
{{% /alert %}}

## Description {#description}

The [`mc ilm tier update`](#command-mc.ilm.tier.update) command modifies an existing configured remote tier.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

### Supported S3 Services {#supported-s3-services}

[`mc ilm tier`](/reference/minio-mc/mc-ilm-tier/#command-mc.ilm.tier) supports *only* the following S3-compatible services as a remote target for object tiering:

- MinIO
- Amazon S3
- Google Cloud Storage
- Azure Blob Storage

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

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example updates the credentials for an existing remote tier called `S3TIER` on the `myminio` deployment.

```shell
 mc ilm tier update myminio S3TIER --access-key ACCESS_KEY --secret-key SECRET_KEY
```

After running this command, lifecycle management rules on the `myminio` deployment use the tier’s new credentials to transition objects into the remote location. Options not modified in the command maintain their existing configurations.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc ilm tier update TARGET                         \
                   TIER_NAME                      \
                   [--account-key value]          \
                   [--access-key value]           \
                   [--az-sp-tenant-id value]      \
                   [--az-sp-client-id value]      \
                   [--az-sp-client-secret value]  \
                   [--secret-key value]           \
                   [--use-aws-role]               \
                   [--credentials-file value]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

The command accepts the following arguments:

##### `TARGET` {#mc.ilm.tier.update.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.

##### `TIER_NAME` {#mc.ilm.tier.update.TIER_NAME}

*mc-cmd*

*Required*

The name of the remote tier the command modifies. The value corresponds to the [`mc ilm tier add TIER_NAME`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_NAME) specified when creating the remote tier.

##### `--access-key` {#mc.ilm.tier.update.-access-key}

*mc-cmd*

*Optional*

The access key for a user on the remote S3 or MinIO tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other `TIER_TYPE`.

##### `--secret-key` {#mc.ilm.tier.update.-secret-key}

*mc-cmd*

*Optional*

The secret key for a user on the remote `s3` or `minio` tier.

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other `TIER_TYPE`.

##### `--use-aws-role` {#mc.ilm.tier.update.-use-aws-role}

*mc-cmd*

*Optional*

Use the access permission for the locally configured [AWS Role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html).

This option only applies if [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other value of `TIER_TYPE`.

##### `--account-key` {#mc.ilm.tier.update.-account-key}

*mc-cmd*

*Optional*

The account key for a user on a remote Azure tier.

**Required** for Azure tier types.

Use this option to rotate the credentials for the [`--account-name`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.-account-name) associated to the remote tier.

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other type of login.

##### `--az-sp-tenant-id` {#mc.ilm.tier.update.-az-sp-tenant-id}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-07-03T20-17-25Z
{{% /alert %}}

Directory ID for the Azure service principal account.

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other type of login.

##### `--az-sp-client-id` {#mc.ilm.tier.update.-az-sp-client-id}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-07-03T20-17-25Z
{{% /alert %}}

Client ID of the Azure service principal account.

Requires [`--az-sp-client-secret`](#mc.ilm.tier.update.-az-sp-client-secret).

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other type of login.

##### `--az-sp-client-secret` {#mc.ilm.tier.update.-az-sp-client-secret}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-07-03T20-17-25Z
{{% /alert %}}

The secret for the Azure service principal account.

Requires [`--az-sp-client-id`](#mc.ilm.tier.update.-az-sp-client-id).

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other type of login.

##### `--credentials-file` {#mc.ilm.tier.update.-credentials-file}

*mc-cmd*

*Optional*

**Required** for Google Cloud Storage tier types.

The credential file for a user on the remote GCS tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

This option only applies to remote storage tiers with [`TIER_TYPE`](/reference/minio-mc/mc-ilm-tier-add/#mc.ilm.tier.add.TIER_TYPE) is `gcs`. This option has no effect for any other type of login.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Rotate Credentials for an S3 Remote Tier {#rotate-credentials-for-an-s3-remote-tier}

The following example updates the credentials for an S3 remote tier called `S3TIER` on the `myminio` deployment.

```shell
mc ilm tier update myminio S3TIER --access-key ACCESS_KEY --secret-key SECRET_KEY
```

- Replace `S3TIER` with the name for your Amazon Simple Storage Solution tier.
- Replace `ACCESS_KEY` with the updated access key for your S3 storage.
- Replace `SECRET_KEY` with the updated secret key for the access key provided.

### Rotate Credentials for an Azure Blob Storage Remote Tier {#rotate-credentials-for-an-azure-blob-storage-remote-tier}

The following example updates the credentials for an Azure remote tier called `AXTIER` on the `myminio` deployment.

```shell
mc ilm tier update myminio AZTIER --account-key ACCOUNT-KEY
```

- Replace `AZTIER` with the name for your Azure tier.
- Replace `ACCOUNT-KEY` with the updated key for your Azure storage.

### Rotate Credentials for a Google Cloud Storage Remote Tier {#rotate-credentials-for-a-google-cloud-storage-remote-tier}

The following example updates the credentials for a Google Cloud Storage remote tier called `GCSTIER` on the `myminio` deployment.

```shell
 mc ilm tier update myminio GCSTIER --credentials-file /path/to/credentials.json
```

- Replace `GCSTIER` with the name for your Google Cloud Storage tier.
- Replace `/path/to/credentials.json` with the path of the updated credential file to use to access the remote storage.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Required Permissions {#id1}

For permissions required to modify a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.
