---
title: "mc ilm tier add"
url: "/reference/minio-mc/mc-ilm-tier-add/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-ilm-tier-add"></a>
<a id="minio-mc-ilm-tier-add"></a>

<a id="command-mc.ilm.tier.add"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

[`mc ilm tier add`](#command-mc.ilm.tier.add) replaces `mc admin tier add`.
{{% /alert %}}

## Description {#description}

The [`mc ilm tier add`](#command-mc.ilm.tier.add) command creates a new remote storage tier to a supported storage services.

See [Object Transition](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) for a complete list.

### Supported S3 Services {#supported-s3-services}

[`mc ilm tier add`](#command-mc.ilm.tier.add) supports *only* the following S3-compatible services as a remote target for object tiering:

- MinIO
- Amazon S3
- Google Cloud Storage
- Azure Blob Storage

### Permissions {#permissions}

MinIO requires the following administrative permissions on the cluster in which you create remote tiers for object transition lifecycle management rules:

- [`admin:SetTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-SetTier)
- [`admin:ListTier`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListTier)

For example, the following policy provides permission for configuring object transition lifecycle management rules on any bucket in the cluster:

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

## Syntax {#syntax}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example creates a new remote tier called `WARM-MINIO-TIER` on the `myminio` deployment. The command creates a tier for a remote MinIO deployment located at the hostname `https://warm-minio.com`.

```shell
 mc ilm tier add minio myminio WARM-MINIO-TIER                     \
                               --endpoint https://warm-minio.com   \
                               --access-key ACCESSKEY              \
                               --secret-key SECRETKEY              \
                               --bucket mybucket                   \
                               --prefix myprefix/
```

Lifecycle management rules on the `myminio` deployment can use the new tier to transition objects into the remote location’s `myprefix/` prefix in the `mybucket` bucket.
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc ilm tier add TIER_TYPE                    \
                TARGET                       \
                TIER_NAME                    \
                --bucket value               \
                [--endpoint string]          \
                [--region string]            \
                [--access-key value^]        \
                [--secret-key value^]        \
                [--use-aws-role^]            \
                [--aws-role-arn^]            \
                [--aws-web-identity-file^]   \
                [--azure-sp-tenant-id^]      \
                [--azure-sp-client-id^]      \
                [--azure-sp-client-secret^]  \
                [--account-name value^]      \
                [--account-key value^]       \
                [--credentials-file value^]  \
                [--prefix value]             \
                [--storage-class value]
```

**^Note:** Each supported storage vendor authenticates with different methods. The flags to use for authentication vary by storage vendor. See details under [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) below.

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

The command accepts the following arguments:

##### `TIER_TYPE` {#mc.ilm.tier.add.TIER_TYPE}

*mc-cmd*

*Required*

The Cloud Service Provider storage backend (“Tier”) to which MinIO transitions objects. Specify *one* of the following supported values:

<table>
  <tbody>
    <tr>
      <td><p><code>minio</code></p></td>
      <td><p>Use a remote MinIO deployment as the storage backend for the new Tier.</p><p>Requires also specifying the following parameters:</p><ul><li><p><a href="#mc.ilm.tier.add.-access-key"><code>--access-key</code></a></p></li><li><p><a href="#mc.ilm.tier.add.-secret-key"><code>--secret-key</code></a></p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>s3</code></p></td>
      <td><p>Use AWS S3 as the storage backend for the new Tier.</p><p>Requires also specifying the following parameters:</p><ul><li><p><a href="#mc.ilm.tier.add.-access-key"><code>--access-key</code></a></p></li><li><p><a href="#mc.ilm.tier.add.-secret-key"><code>--secret-key</code></a></p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>azure</code></p></td>
      <td><p>Use Azure Blob Storage as the storage backend for the new Tier.</p><p>Requires also specifying the following parameters:</p><ul><li><p><a href="#mc.ilm.tier.add.-account-name"><code>--account-name</code></a></p></li><li><p><a href="#mc.ilm.tier.add.-account-key"><code>--account-key</code></a></p></li></ul></td>
    </tr>
    <tr>
      <td><p><code>gcs</code></p></td>
      <td><p>Use GCP Cloud Storage as the storage backend for the new Tier.</p><p>Requires also specifying the following parameter:</p><ul><li><p><a href="#mc.ilm.tier.add.-credentials-file"><code>--credentials-file</code></a></p></li></ul></td>
    </tr>
  </tbody>
</table>

##### `TARGET` {#mc.ilm.tier.add.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment on which the command creates the new remote tier. You can then create new rules with [`mc ilm rule add`](/reference/minio-mc/mc-ilm-rule-add/#command-mc.ilm.rule.add) specifying the new remote tier.

##### `TIER_NAME` {#mc.ilm.tier.add.TIER_NAME}

*mc-cmd*

*Required*

The name to associate with the new remote tier. The name **must** be unique across all configured tiers on the MinIO cluster.

You **must** specify the tier in all-caps, e.g. `WARM_TIER`.

##### `--endpoint` {#mc.ilm.tier.add.-endpoint}

*mc-cmd*

*Optional*

The URL endpoint for the S3 or MinIO storage. The URL endpoint **must** resolve to the provider specified to [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE).

Required for `s3` or `minio` tier types, optional for `azure`. This option has no effect for any other value of `TIER_TYPE`.

##### `--access-key` {#mc.ilm.tier.add.-access-key}

*mc-cmd*

*Optional*

The access key for a user on the remote `S3` or `minio` tier types. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

Required if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other value of `TIER_TYPE`.

##### `--secret-key` {#mc.ilm.tier.add.-secret-key}

*mc-cmd*

*Optional*

The secret key for a user on the remote `s3` or `minio` tier types.

Required if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other value of `TIER_TYPE`.

##### `--account-name` {#mc.ilm.tier.add.-account-name}

*mc-cmd*

*Optional*

The [Storage Account](https://learn.microsoft.com/en-us/azure/storage/common/storage-account-overview) to use as the remote storage resource.

Required if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other value of `TIER_TYPE`.

MinIO does *not* support changing the storage account name associated to an Azure remote tier. Azure storage backends are tied to the storage account, such that changing this value would change the storage backend and prevent access to any objects transitioned to the original account/backend.

##### `--account-key` {#mc.ilm.tier.add.-account-key}

*mc-cmd*

*Optional*

The corresponding shared account key for the [`--account-name`](#mc.ilm.tier.add.-account-name) associated to the remote Azure tier.

The account key must have an assigned Azure policy with the required [permissions](/administration/object-management/transition-objects-to-azure/#minio-lifecycle-management-transition-to-azure-permissions-remote).

Required if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `azure`. This option has no effect for any other value of `TIER_TYPE`.

##### `--credentials-file` {#mc.ilm.tier.add.-credentials-file}

*mc-cmd*

*Optional*

The [credential file](https://cloud.google.com/docs/authentication/getting-started) for a user on the remote Google Cloud Storage tier. The user must have permission to perform read/write/list/delete operations on the remote bucket or bucket prefix.

Required if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `gcs`. This option has no effect for any other value of `TIER_TYPE`.

##### `--bucket` {#mc.ilm.tier.add.-bucket}

*mc-cmd*

*Required*

The bucket on the remote tier to which MinIO transitions objects.

For `azure` remote tiers, this value corresponds to the [Container name](https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-introduction#containers)

##### `--prefix` {#mc.ilm.tier.add.-prefix}

*mc-cmd*

*Optional*

The prefix path for the specified [`--bucket`](#mc.ilm.tier.add.-bucket) to which MinIO transitions objects.

Omit this field to transition objects into the bucket root.

##### `--storage-class` {#mc.ilm.tier.add.-storage-class}

*mc-cmd*

*Optional*

The storage class (“access tier” for Microsoft Azure) MinIO applies to objects transitioned to the remote bucket.

The storage class to apply to objects transitioned by MinIO to the remote bucket. MinIO tiering behavior depends on the remote storage returning objects immediately (milliseconds to seconds) upon request. MinIO therefore *cannot* support remote storage which requires rehydration, wait periods, or manual intervention.

Select the tab corresponding to the `TIER_TYPE` for a list of supported values for each tier:

{{< tabpane text=true persist=header >}}
{{% tab header="minio" %}}

- `STANDARD` *Recommended*
- `REDUCED`

For more information, see [Erasure Coding storage class](/reference/minio-server/settings/storage-class/#minio-ec-storage-class).
{{% /tab %}}
{{% tab header="s3" %}}

- `STANDARD`
- `STANDARD-IA`
- `ONEZONE-IA`

For more information, see [Using Amazon S3 storage classes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-class-intro.html).
{{% /tab %}}
{{% tab header="gcs" %}}

- `STANDARD`
- `NEARLINE`
- `COLDLINE`

For more information, see [GCS storage class](https://cloud.google.com/storage/docs/storage-classes).
{{% /tab %}}
{{% tab header="azure" %}}

- `Hot`
- `Cool`

For more information, see [Hot, cool, and archive access tiers for blob data](https://learn.microsoft.com/en-us/azure/storage/blobs/access-tiers-overview).
{{% /tab %}}
{{< /tabpane >}}

If omitted, objects use the default storage class defined for the remote bucket.

##### `--region` {#mc.ilm.tier.add.-region}

*mc-cmd*

*Optional*

The S3 backend region for the specified [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE), such as `us-west-1`.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other value of `TIER_TYPE`.

##### `--use-aws-role` {#mc.ilm.tier.add.-use-aws-role}

*mc-cmd*

*Optional*

Use the access permission for the locally configured [AWS Role](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html).

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` or `minio`. This option has no effect for any other value of `TIER_TYPE`.

##### `--aws-role-arn` {#mc.ilm.tier.add.-aws-role-arn}

*mc-cmd*

*Optional*

The AWS S3 role name to use when transitioning objects.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` **and** the source is a MinIO pod on Amazon EKS.

##### `--aws-web-identity-file` {#mc.ilm.tier.add.-aws-web-identity-file}

*mc-cmd*

*Optional*

Specify the web identity token file to use when transitioning objects.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `s3` **and** the source is a MinIO pod on Amazon EKS.

##### `--azure-sp-tenant-id` {#mc.ilm.tier.add.-azure-sp-tenant-id}

*mc-cmd*

*Optional*

Tenant ID for the [service principal account](https://learn.microsoft.com/en-us/cli/azure/azure-cli-sp-tutorial-1) to use to log in to Azure storage.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `azure` and you log in using a service principal identity. This option has no effect for any other value of `TIER_TYPE`.

##### `--azure-sp-client-id` {#mc.ilm.tier.add.-azure-sp-client-id}

*mc-cmd*

*Optional*

Client ID for the [service principal account](https://learn.microsoft.com/en-us/cli/azure/azure-cli-sp-tutorial-1) to use to log in to Azure storage.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `azure` and you log in using a service principal identity. This option has no effect for any other value of `TIER_TYPE`.

##### `--azure-sp-client-secret` {#mc.ilm.tier.add.-azure-sp-client-secret}

*mc-cmd*

*Optional*

The client secret for the [service principal account](https://learn.microsoft.com/en-us/cli/azure/azure-cli-sp-tutorial-1) to use to log in to Azure storage.

This option only applies if [`TIER_TYPE`](#mc.ilm.tier.add.TIER_TYPE) is `azure` and you log in using a service principal identity. This option has no effect for any other value of `TIER_TYPE`.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Configure a Tier to Transition Objects to a MinIO Deployment {#configure-a-tier-to-transition-objects-to-a-minio-deployment}

The following example creates a new tier on a local deployment that a configured rule can use to transition objects to a separate, remote MinIO deployment.

```shell
mc ilm tier add minio myminio WARM-MINIO-TIER --endpoint https://warm-minio.com \
     --access-key ACCESSKEY --secret-key SECRETKEY --bucket mybucket --prefix myprefix/
```

This command creates a new tier called `WARM-MINIO-TIER` for a `minio` type of remote storage on the `myminio` deployment.

- The remote MinIO storage is located at `https://warm-minio.com`.
- The command includes credentials for a user with read, write, list, and delete privileges to the bucket and prefix.
- The tier transitions objects to the `mybucket` bucket and the `myprefix` prefix on the remote MinIO storage.

### Configure a Tier to Transition Objects to an Azure Blob Storage Location {#configure-a-tier-to-transition-objects-to-an-azure-blob-storage-location}

The following example creates a new tier on a local deployment that a configured rule can use to transition objects to Azure Blob Storage.

```shell
mc ilm tier add azure myminio AZTIER --account-name ACCOUNT-NAME --account-key ACCOUNT-KEY \
     --bucket myazurebucket --prefix myazureprefix/
```

This command creates a new tier called `AZTIER` for an `azure` type of remote storage on the `myminio` deployment.

- The remote Azure storage is accessed by the provided account name and key.
- The tier transitions objects to the `myazurebucket` bucket and the `myazureprefix` prefix on the Azure storage.

### Configure a Tier to Transition Objects to Google Cloud Storage {#configure-a-tier-to-transition-objects-to-google-cloud-storage}

The following example creates a new tier on a local deployment that a configured rule can use to transition objects to Google Cloud Storage.

```shell
 mc ilm tier add gcs myminio GCSTIER --credentials-file /path/to/credentials.json \
     --bucket mygcsbucket  --prefix mygcsprefix/
```

This command creates a new tier called `GCSTIER` for a `gcs` type of remote storage on the `myminio` deployment.

- The remote GCS storage is accessed by the provided credentials file.
- The tier transitions objects to the `mygcsbucket` bucket and the `mygcsprefix` prefix on the GCS storage.

### Configure a Tier to Transition Objects to Amazon Simple Storage Service (S3) {#configure-a-tier-to-transition-objects-to-amazon-simple-storage-service-s3}

The following example creates a new tier on a local deployment that a configured rule can use to transition objects to a STANDARD storage on S3.

```shell
 mc ilm tier add s3 myminio S3TIER --endpoint https://s3.amazonaws.com \
     --access-key ACCESSKEY --secret-key SECRETKEY --bucket mys3bucket --prefix mys3prefix/ \
     --storage-class "STANDARD" --region us-west-2
```

This command creates a new tier called `S3TIER` for a `s3` type of remote storage on the `myminio` deployment.

- The S3 storage is located at the provided endpoint.
- The remotes S3 storage is accessed by the provided access key and secret key.
- The tier transitions objects to the `mys3bucket` bucket and the `mys3prefix` prefix on the GCS storage.
- The tier utilizes S3 `STANDARD` storage class located in the `us-west-2` S3 region.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Required Permissions {#required-permissions}

For permissions required to add a tier, refer to the [required permissions](/reference/minio-mc/mc-ilm-tier/#minio-mc-ilm-tier-permissions) on the parent command.
