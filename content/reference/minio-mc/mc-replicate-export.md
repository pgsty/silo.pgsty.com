---
title: "mc replicate export"
url: "/reference/minio-mc/mc-replicate-export/"
weight: 80
minio_origin: true
silo_modified: false
---

<a id="mc-replicate-export"></a>
<a id="minio-mc-replicate-export"></a>

<a id="command-mc.replicate.export"></a>

## Syntax {#syntax}

The [`mc replicate export`](#command-mc.replicate.export) command exports the JSON-formatted [replication rules](/administration/bucket-replication/#minio-bucket-replication-serverside) for a MinIO bucket to `STDOUT`.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command exports the replication configuration for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc replicate export myminio/mydata > mydata-replication.json
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] export ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.export.ALIAS}

*mc-cmd*

*Required* the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix for which to export the replication rules. For example:

```text
mc replicate export myminio/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Export Existing Replication Rules {#export-existing-replication-rules}

Use [`mc replicate export`](#command-mc.replicate.export) to export bucket replication rules:

```shell
mc replicate export ALIAS/PATH > bucket-replication-rules.json
```

- Replace [`ALIAS`](#mc.replicate.export.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.export.ALIAS) with the path to the bucket or bucket prefix.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
