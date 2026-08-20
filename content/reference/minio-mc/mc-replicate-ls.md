---
title: "mc replicate ls"
url: "/reference/minio-mc/mc-replicate-ls/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-replicate-ls.rst
upstream_modified: false
---

<a id="mc-replicate-ls"></a>
<a id="minio-mc-replicate-ls"></a>

<a id="command-mc.replicate.list"></a>

<a id="command-mc.replicate.ls"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> `mc replicate ls` replaces the `mc admin bucket remote ls` command.

## Syntax {#syntax}

The [`mc replicate ls`](#command-mc.replicate.ls) command lists all [replication rules](/administration/bucket-replication/#minio-bucket-replication-serverside) on a MinIO bucket.

The [`mc replicate list`](#command-mc.replicate.list) command has equivalent functionality to [`mc replicate ls`](#command-mc.replicate.ls).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command lists all enabled replication rules for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc replicate ls --status "enabled" myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] replicate ls         \
                 [--status "string"]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.ls.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix for which to list the replication rules. For example:

```text
mc replicate ls myminio/mybucket
```

##### `--status` {#mc.replicate.ls.-status}

*mc-cmd*

*Optional*

Filter replication rules on the bucket based on their status. Specify one of the following values:

- `enabled` - Show only enabled replication rules.
- `disabled` - Show only disabled replication rules.

If omitted, [`mc replicate ls`](#command-mc.replicate.ls) defaults to showing all replication rules.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Existing Replication Rules {#list-existing-replication-rules}

Use [`mc replicate ls`](#command-mc.replicate.ls) to list bucket replication rules:

```shell
mc replicate ls ALIAS/PATH
```

- Replace [`ALIAS`](#mc.replicate.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.ls.ALIAS) with the path to the bucket or bucket prefix.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
