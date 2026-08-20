---
title: "mc version info"
url: "/reference/minio-mc/mc-version-info/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-version-info.rst
upstream_modified: false
---

<a id="mc-version-info"></a>
<a id="minio-mc-version-info"></a>

<a id="command-mc.version.info"></a>

## Syntax {#syntax}

The [`mc version info`](#command-mc.version.info) command returns the versioning status for the specified bucket.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command returns the versioning status for the `mybucket` bucket on the `myminio` MinIO deployment:

```shell
mc version info myminio/mybucket
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] version info ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.version.info.ALIAS}

*mc-cmd*

The full path to the bucket on which to retrieve the versioning status. For example:

```shell
mc version info myminio/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Get Bucket Versioning Status {#get-bucket-versioning-status}

Use [`mc version info`](#command-mc.version.info) to retrieve the versioning status for a bucket:

```shell
mc version info ALIAS/PATH
```

- Replace [`ALIAS`](#mc.version.info.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace [`PATH`](#mc.version.info.ALIAS) with the bucket on which to retrieve the versioning status.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
