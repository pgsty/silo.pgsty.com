---
title: "mc admin bucket remote"
url: "/reference/deprecated/mc-admin-bucket-remote/"
weight: 120
minio_origin: true
silo_modified: false
---

<a id="mc-admin-bucket-remote"></a>

<a id="command-mc.admin.bucket.remote"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

- `mc admin bucket remote add` replaced by [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add)
- `mc admin bucket remote update` replaced by [`mc replicate update`](/reference/minio-mc/mc-replicate-update/#command-mc.replicate.update)
- `mc admin bucket remote rm` replaced by [`mc replicate rm`](/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm)
- `mc admin bucket remote ls` replaced by [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls)
{{% /alert %}}

{{% alert color="info" %}}
**Changed: RELEASE.2023-02-16T19-20-11Z**

- `mc admin bucket remote bandwidth` replaced by [`mc replicate status`](/reference/minio-mc/mc-replicate-status/#command-mc.replicate.status)

  Replication related statistics are moving to the `mc replicate status` command.
{{% /alert %}}

## Description {#description}

The [`mc admin bucket remote`](#command-mc.admin.bucket.remote) command manages the `ARN` resources for use with [`bucket replication`](/reference/minio-mc/mc-replicate/#command-mc.replicate).

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

## Examples {#examples}

### Add a New Replication Target {#add-a-new-replication-target}

Use [`mc admin bucket remote add`](#mc.admin.bucket.remote.add) to create a new replication target ARN for use with [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add):

```shell
mc admin bucket remote add SOURCE/BUCKET DESTINATION/BUCKET
```

- Replace [`SOURCE`](#mc.admin.bucket.remote.add.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment to use as the replication target. Replace `BUCKET` with the full path of the bucket into which MinIO replicates objects from the `DESTINATION`.
- Replace [`DESTINATION`](#mc.admin.bucket.remote.add.DESTINATION) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment to use as the replication source. Replace `BUCKET` with the full path of the bucket from which MinIO replicates objects into the `SOURCE`.

### Remove an Existing Replication Target {#remove-an-existing-replication-target}

Use [`mc admin bucket remote rm`](#mc.admin.bucket.remote.rm) to remove a replication target from a bucket:

```shell
mc admin bucket remote rm SOURCE/BUCKET --arn ARN
```

- Replace [`SOURCE`](#mc.admin.bucket.remote.rm.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment being used as the replication source. Replace `BUCKET` with the full path of the bucket from which MinIO replicates objects.
- Replace [`ARN`](#mc.admin.bucket.remote.rm.ARN) with the ARN of the remote target.

Removing the target halts all in-progress [`bucket replication`](/reference/minio-mc/mc-replicate/#command-mc.replicate) to the target.

<a id="minio-retrieve-remote-bucket-targets"></a>

### Retrieve Configured Replication Targets {#retrieve-configured-replication-targets}

Use [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) to list a bucket’s configured replication targets:

```shell
mc replicate ls ALIAS/PATH
```

- Replace [`ALIAS`](/reference/minio-mc/mc-replicate-ls/#mc.replicate.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment being used as the replication source. Replace `PATH` with the full path of the bucket from which MinIO replicates objects.

## Syntax {#syntax}

#### `mc admin bucket remote add` {#mc.admin.bucket.remote.add}

*mc-cmd*

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

- `mc admin bucket remote add` replaced by [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add)
{{% /alert %}}

Adds a remote target to a bucket on a MinIO deployment. The command has the following syntax:

```shell
mc admin bucket remote add SOURCE DESTINATION --service "replication" [FLAGS]
```

The command accepts the following arguments:

#### `SOURCE` {#mc.admin.bucket.remote.add.SOURCE}

*mc-cmd*

*Required*

The full path to the bucket to which the command adds the remote target. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment as the prefix to the bucket path. For example:

```shell
mc admin bucket remote add play/mybucket
```

#### `DESTINATION` {#mc.admin.bucket.remote.add.DESTINATION}

*mc-cmd*

*Required*

The target MinIO deployment and bucket.

Specify the full URL to the destination MinIO deployment and bucket using the following format:

```shell
http(s)://ACCESSKEY:SECRETKEY@DESTHOSTNAME/DESTBUCKET
```

- **Replace `ACCESSKEY` with the access key for a user on the**

  > destination MinIO deployment.
- **Replace `SECRETKEY` with the secret key for a user on the**

  > destination MinIO deployment.
- **Replace `DESTHOSTNAME` with the hostname and port of the MinIO**

  > deployment (i.e. `minio-server.example.net:9000`).
- **Replace `DESTBUCKET` with the bucket on the**

  > destination.

#### `--service` {#mc.admin.bucket.remote.add.-service}

*mc-cmd*

*Required*

Specify `"replication"`.

#### `--region` {#mc.admin.bucket.remote.add.-region}

*mc-cmd*

The region of the [`DESTINATION`](#mc.admin.bucket.remote.add.DESTINATION).

Mutually exclusive with [`add`](#mc.admin.bucket.remote.add)

#### `--path` {#mc.admin.bucket.remote.add.-path}

*mc-cmd*

The bucket path lookup supported by the destination server. Specify one of the following:

- `on`
- `off`
- `auto` (Default)

Mutually exclusive with [`add`](#mc.admin.bucket.remote.add)

#### `--sync` {#mc.admin.bucket.remote.add.-sync}

*mc-cmd*

Enables synchronous replication, where MinIO attempts to replicate the object *prior* to returning the PUT object response. Synchronous replication may increase the time spent waiting for PUT operations to return successfully.

By default, [`mc admin bucket remote add`](#mc.admin.bucket.remote.add) operates in asynchronous mode, where MinIO attempts replicating objects *after* returning the PUT object response.

#### `mc admin bucket remote ls` {#mc.admin.bucket.remote.ls}

*mc-cmd*

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

- `mc admin bucket remote ls` replaced by [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls)
{{% /alert %}}

Lists all remote targets associated to a bucket on the MinIO deployment. Use `mc admin bucket remote ls --help` for usage syntax.

#### `mc admin bucket remote rm, remove` {#mc.admin.bucket.remote.rm}

*mc-cmd*

{{% alert color="info" %}}
**Changed: RELEASE.2022-12-24T15-21-38Z**

- `mc admin bucket remote rm` replaced by [`mc replicate rm`](/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm)
{{% /alert %}}

Removes a remote target for a bucket on the MinIO deployment. The command has the following syntax:

```shell
mc admin bucket remote rm SOURCE --arn ARN
```

The command accepts the following arguments:

#### `SOURCE` {#mc.admin.bucket.remote.rm.SOURCE}

*mc-cmd*

*Required*

The full path to the bucket from which the command removes the remote target. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment as the prefix to the bucket path. For example:

```shell
mc admin bucket remote rm play/mybucket
```

#### `ARN` {#mc.admin.bucket.remote.rm.ARN}

*mc-cmd*

*Required*

The `ARN` of the remote target for which the command removes from the target bucket. Use [`mc admin bucket remote ls`](#mc.admin.bucket.remote.ls) to list all remote targets and their associated ARNs for a specific bucket.
