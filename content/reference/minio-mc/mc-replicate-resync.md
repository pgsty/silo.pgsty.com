---
title: "mc replicate resync"
url: "/reference/minio-mc/mc-replicate-resync/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-replicate-resync"></a>
<a id="minio-mc-replicate-resync"></a>

<a id="command-mc.replicate.reset"></a>

<a id="command-mc.replicate.resync"></a>

## Syntax {#syntax}

The [`mc replicate resync`](#command-mc.replicate.resync) command resynchronizes all objects in the specified MinIO bucket to a remote [replication](/administration/bucket-replication/#minio-bucket-replication-serverside) target.

This command *requires* first configuring the remote bucket target using the [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) command. You must specify the resulting remote ARN as part of running [`mc replicate resync`](#command-mc.replicate.resync).

This command supports rebuilding a MinIO deployment using an active-active replication remote as the “backup” source. See the following tutorials for more information on active-active replication:

- [Enable Two-Way Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-two-way-bucket-replication/#minio-bucket-replication-serverside-twoway)
- [Enable Multi-Site Server-Side Bucket Replication](/administration/bucket-replication/enable-server-side-multi-site-bucket-replication/#minio-bucket-replication-serverside-multi)

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command resynchronizes the content of the `mydata` bucket on the `myminio` MinIO deployment to the remote MinIO deployment associated to the specified `--remote-bucket`:

```shell
mc replicate resync start \
   --remote-bucket "arn:minio:replication::d3c086c7-1d64-40c2-954b-fe8222907033:mydata" \
   myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] replicate resync start|status  \
                 --remote-bucket "string"       \
                 [--older-than "string"]        \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.resync.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix which MinIO uses as the replication source. For example, the following command starts replication using the `data` bucket on the MinIO deployment associated to the `primary` alias.

```text
mc replicate resync start primary/data --remote-bucket "ARN"
```

##### `start` {#mc.replicate.resync.start}

*mc-cmd*

*Required*

Starts the resynchronization procedure using the specified [`bucket`](#mc.replicate.resync.ALIAS) as the source and the [`--remote-bucket`](#mc.replicate.resync.-remote-bucket) as the remote target.

Mutually exclusive with [`mc replicate resync status`](#mc.replicate.resync.status).

##### `status` {#mc.replicate.resync.status}

*mc-cmd*

*Required*

Returns the status of resynchronization on the specified [`bucket`](#mc.replicate.resync.ALIAS) to all remote targets.

Include the [`--remote-bucket`](#mc.replicate.resync.-remote-bucket) argument to filter the status output to only the specified remote target.

##### `--remote-bucket` {#mc.replicate.resync.-remote-bucket}

*mc-cmd*

*Required*

Specify the ARN for the destination deployment and bucket.

You can retrieve the ARN using [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) with the `--json` option. The `rule.Destination.Bucket` field contains the ARN for any given replication rule.

##### `older-than` {#mc.replicate.resync.older-than}

*mc-cmd*

*Optional*

Specify a duration in days where MinIO only resynchronizes objects older than the specified duration.

Only valid with [`mc replicate resync start`](#mc.replicate.resync.start).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Resynchronize Remote Replication Target from Source Bucket {#resynchronize-remote-replication-target-from-source-bucket}

The following [`mc replicate resync`](#command-mc.replicate.resync) command resynchronizes all objects on the specified source bucket to the remote target regardless of their replication status:

```shell
mc replicate resync start --remote-bucket "arn:minio:replication::UUID:data" primary/data
```

- Replace `primary/data` with the [`ALIAS`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.ALIAS) and full bucket path for which to create the replication configuration.
- Replace the [`--remote-bucket`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.-remote-bucket) value with the ARN of the remote target. Use [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) to list all configured remote replication targets.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
