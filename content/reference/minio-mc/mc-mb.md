---
title: "mc mb"
url: "/reference/minio-mc/mc-mb/"
weight: 230
minio_origin: true
silo_modified: false
---

<a id="mc-mb"></a>

<a id="command-mc.mb"></a>

## Syntax {#syntax}

The [`mc mb`](#command-mc.mb) command creates a new bucket or directory at the specified path.

You can also use [`mc mb`](#command-mc.mb) against the local filesystem to produce similar results to the `mkdir -p` commandline tool.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command creates a new bucket `mydata` on the `myminio` MinIO deployment. The command creates the bucket with [object locking enabled](/administration/object-management/object-retention/#minio-object-locking).

```shell
mc mb --with-locks myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] mb                   \
                 [--ignore-existing]  \
                 [--region "string"]  \
                 [--with-lock]        \
                 [--with-versioning]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.mb.ALIAS}

*mc-cmd*

*Required*

The MinIO or other S3-compatible service on which to create the new bucket.

For creating a bucket on MinIO, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and the name of the bucket. For example:

```text
mc mb play/mybucket
```

For creating a directory on a local filesystem, specify the full path to that directory. For example:

```text
mc mb ~/mydata/mydir
```

##### `--ignore-existing, p` {#mc.mb.-ignore-existing}

*mc-cmd*

*Optional*

Directs [`mc mb`](#command-mc.mb) to do nothing if the bucket or directory already exists.

##### `--region` {#mc.mb.-region}

*mc-cmd*

*Optional*

The region in which to create the specified bucket. Has no effect if the specified [`ALIAS`](#mc.mb.ALIAS) is a filesystem directory.

If not specified, default value is `us-east-1`.

##### `--with-lock, l` {#mc.mb.-with-lock}

*mc-cmd*

*Optional*

Enables [object locking](/administration/object-management/object-retention/#minio-object-locking) on the specified bucket. Object locking requires, and therefore implies, enabling object versioning.

{{% alert color="warning" %}}
**Important**

You can *only* enable object locking when creating the bucket. Buckets created without object locking cannot use [Bucket Lifecycle Management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management) or [Bucket Object Locking](/administration/object-management/object-retention/#minio-object-locking) functionality.
{{% /alert %}}

##### `--with-versioning` {#mc.mb.-with-versioning}

*mc-cmd*

*Optional*

Enables [object versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) on the new bucket. With versioning enabled, by default MinIO allows up to the maximum value of an Int64 versions per object, or over 9.2 quintillion. Define [object expiration](/administration/object-management/create-lifecycle-management-expiration-rule/#minio-lifecycle-management-create-expiry-rule) rules to remove versions of objects no longer needed, such as by the number of versions or the date of versions.

Versioning is required for [bucket replication](/administration/bucket-replication/#minio-bucket-replication) or [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview). Versioning does not imply or require object locking.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Create Bucket with Object Locking {#create-bucket-with-object-locking}

Use [`mc mb`](#command-mc.mb) to create a bucket on an S3-compatible host. The [`--with-lock`](#mc.mb.-with-lock) option creates the bucket with locking enabled:

```shell
mc mb --with-lock ALIAS/BUCKET
```

- Replace [`ALIAS`](#mc.mb.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`BUCKET`](#mc.mb.ALIAS) with the bucket to create.

### Create a New Bucket in a Specific Region {#create-a-new-bucket-in-a-specific-region}

Use [`mc mb`](#command-mc.mb) to create a bucket on an S3-compatible host. The [`--region`](#mc.mb.-region) option creates the bucket in a desired region.

```shell
mc mb --region --region=us-west-2 myminio/mynewbucket
```

The above command creates a new bucket, `mynewbucket` on the `myminio` bucket within the `us-west-2` region.

### Create a New Bucket with Versioning Enabled {#create-a-new-bucket-with-versioning-enabled}

```shell
mc mb --with-versioning myminio/myversionedbucket
```

The above command creates a new bucket, `myversionedbucket`, on the `myminio` alias. The new bucket enables [object versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) for all objects in the bucket.

## Behavior {#behavior}

### Bucket Limits Per Deployment {#bucket-limits-per-deployment}

MinIO does not limit the number of buckets you can create on a deployment. However, MinIO recommends no more than 500,000 buckets per deployment as a general guideline.

### Bucket Limits for Non-MinIO S3 Services {#bucket-limits-for-non-minio-s3-services}

Certain S3 services may restrict the number of buckets a given user or account can create. For example, Amazon S3 limits each account to [100 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/BucketRestrictions.html). [`mc mb`](#command-mc.mb) may return an error if the user has reached bucket limits on the target S3 service.

MinIO Object Storage deployments do not place any limits on the number of buckets each user can create.

### Enable Object Locking at Bucket Creation {#enable-object-locking-at-bucket-creation}

MinIO follows [AWS S3 behavior](https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock-overview.html#object-lock-bucket-config) where you *must* enable [object locking](/administration/object-management/object-retention/#minio-object-locking) at bucket creation. Buckets created without object locking can *never* enable object retention or locking.

Enabling bucket locking does *not* set any object locking or retention settings. Consider enabling bucket locking as standard practice.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
