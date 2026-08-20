---
title: "mc replicate rm"
url: "/reference/minio-mc/mc-replicate-rm/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-replicate-rm.rst
upstream_modified: false
---

<a id="mc-replicate-rm"></a>
<a id="minio-mc-replicate-rm"></a>

<a id="command-mc.replicate.remove"></a>

<a id="command-mc.replicate.rm"></a>

> [!NOTE]
> **Changed: RELEASE.2022-12-24T15-21-38Z**
>
> `mc replicate rm` replaces the `mc admin bucket remote rm` command. Removing the replication automatically removes the underlying remote target.

## Syntax {#syntax}

The [`mc replicate rm`](#command-mc.replicate.rm) command removes a [replication rule](/administration/bucket-replication/#minio-bucket-replication-serverside) from a MinIO bucket.

The [`mc replicate remove`](#command-mc.replicate.remove) command has equivalent functionality to [`mc replicate rm`](#command-mc.replicate.rm).

```shell
mc [GLOBALFLAGS] replicate rm FLAGS [FLAGS] ALIAS
```

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command removes the replication rule with specified id from the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc replicate rm --id "c76um9h4b0t1ijr36mug" myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] replicate rm     \
                 --id "string"    \
                 [--all --force]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.rm.ALIAS}

*mc-cmd*

*Required* the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix from which to remove the replication rule. For example:

```text
mc replicate rm --id "ID" myminio/mybucket
```

##### `--id` {#mc.replicate.rm.-id}

*mc-cmd*

*Required* Specify the unique ID for a configured replication rule.

You can omit this option if specifying [`--all`](#mc.replicate.rm.-all)

##### `--all` {#mc.replicate.rm.-all}

*mc-cmd*

*Optional* Removes all replication rules on the specified bucket. Requires specifying the [`--force`](#mc.replicate.rm.-force) flag.

##### `--force` {#mc.replicate.rm.-force}

*mc-cmd*

*Optional* Required if specifying [`--all`](#mc.replicate.rm.-all) .

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove a Replication Rule from a Bucket {#remove-a-replication-rule-from-a-bucket}

Use [`mc replicate rm`](#command-mc.replicate.rm) to remote a bucket replication rule:

```shell
mc replicate rm --id "ID" ALIAS/PATH
```

- Replace [`ID`](#mc.replicate.rm.-id) with the unique ID of the replication rule to remove. Use [`mc replicate ls`](/reference/minio-mc/mc-replicate-ls/#command-mc.replicate.ls) to list all replication rules for the bucket.
- Replace [`ALIAS`](#mc.replicate.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.rm.ALIAS) with the path to the bucket or bucket prefix.

### Remove All Replication Rules from a Bucket {#remove-all-replication-rules-from-a-bucket}

Use [`mc replicate rm`](#command-mc.replicate.rm) to list bucket replication rules:

```shell
mc replicate rm --all --force ALIAS/PATH
```

- Replace [`ALIAS`](#mc.replicate.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.rm.ALIAS) with the path to the bucket or bucket prefix.

## Behavior {#behavior}

### Removing Replication Rules Does Not Affect Replicated Objects {#removing-replication-rules-does-not-affect-replicated-objects}

Removing one or all replication rule for a bucket does *not* remove any objects already replicated under those rule(s).

Use The command or [`mc rb`](/reference/minio-mc/mc-rb/#command-mc.rb) commands to remove replicated objects on the remote target. You can identify replicated objects using the `X-Amz-Replication-Status` metadata field where the value is `REPLICA`. Buckets which contain objects from multiple replication sources may require additional care and filtering to determine the source prior to removal.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
