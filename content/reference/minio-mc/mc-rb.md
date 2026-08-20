---
title: "mc rb"
url: "/reference/minio-mc/mc-rb/"
weight: 300
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-rb.rst
upstream_modified: false
---

<a id="mc-rb"></a>

<a id="command-mc.rb"></a>

## Syntax {#syntax}

The [`mc rb`](#command-mc.rb) command removes one or more buckets on MinIO *or* another S3-compatible service.

To remove only the contents of a bucket, use [`mc rm`](/reference/minio-mc/mc-rm/#command-mc.rm) instead.

> [!WARNING]
> **Important**
>
> [`mc rb`](#command-mc.rb) *permanently deletes bucket(s)* on the target deployment, including any and all [object versions](/administration/object-management/object-versioning/#minio-bucket-versioning) and bucket configurations such as [lifecycle management](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management) or [replication](/administration/bucket-replication/#minio-bucket-replication-serverside).

You can also use [`mc rb`](#command-mc.rb) against the local filesystem to produce similar results to the `rm --rf` commandline tool.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command removes the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc rb --force myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] rb             \
                 --force        \
                 [--dangerous]  \
                 ALIAS [ALIAS...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.rb.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO or other S3-compatible service and the full path to the bucket to remove. For example:

```text
mc rb --force myminio/mydata
```

Omit the bucket path to perform a site-wide removal of buckets on the MinIO deployment. This operation *requires* specifying [`--dangerous`](#mc.rb.-dangerous) to explicitly acknowledge the permanent removal of *all* data on the deployment. For example:

```text
mc rb --force --dangerous myminio
```

For removing a directory and its contents on a local filesystem, specify the full path to that directory. The [`--force`](#mc.rb.-force) flag is ignored if specified. For example:

```text
mc rb ~/data/myolddata
```

You can specify multiple `ALIAS` targets consisting of either MinIO or local filesystem directories. The command attempts to remove *all* specified targets. For example:

```text
mc rb --force myminio/mydata ~/data/myolddata
```

##### `--force` {#mc.rb.-force}

*mc-cmd*

*Required* Safety flag to confirm removal of the bucket contents.

##### `--dangerous` {#mc.rb.-dangerous}

*mc-cmd*

*Optional* Directs [`mc rb`](#command-mc.rb) to perform a site-wide removal of all buckets on each specified [`ALIAS`](#mc.rb.ALIAS) (e.g. `myminio/`).

If any `ALIAS` specifies a filesystem directory, this option results in the removal of all subdirectories and files at that directory path similar to `rm --rf`.

> [!CAUTION]
> **Warning**
>
> Running [`mc rb --dangerous`](#mc.rb.-dangerous) is irreversible. Exercise all possible due diligence in ensuring the command applies to only the desired `ALIAS` targets prior to execution.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Remove a Bucket {#remove-a-bucket}

```shell
mc rb --force ALIAS/PATH
```

- Replace [`ALIAS`](#mc.rb.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.rb.ALIAS) with the path to the bucket to remove.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
