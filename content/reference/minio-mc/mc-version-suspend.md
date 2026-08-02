---
title: "mc version suspend"
url: "/reference/minio-mc/mc-version-suspend/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-version-suspend"></a>
<a id="minio-mc-version-suspend"></a>

<a id="command-mc.version.suspend"></a>

## Syntax {#syntax}

The [`mc version suspend`](#command-mc.version.suspend) command disables versioning on the specified bucket.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command disables versioning for the `mybucket` bucket on the `myminio` MinIO deployment:

```shell
mc version suspend myminio/mybucket
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] version suspend ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.version.suspend.ALIAS}

*mc-cmd*

The full path to the bucket on which to disable versioning. For example:

```shell
mc version suspend myminio/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Disable Bucket Versioning {#disable-bucket-versioning}

Use [`mc version suspend`](#command-mc.version.suspend) to disable versioning for a bucket:

```shell
mc version suspend ALIAS/PATH
```

- Replace [`ALIAS`](#mc.version.suspend.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
- Replace [`PATH`](#mc.version.suspend.ALIAS) with the bucket on which to disable versioning.

## Behavior {#behavior}

### Bucket Versioning with Existing Data {#bucket-versioning-with-existing-data}

Disabling bucket versioning on a bucket with existing versioned data does *not* remove any versioned objects. Applications can continue to access versioned data after disabling bucket versioning. Use [`mc rm --versions ALIAS/BUCKET/OBJECT`](/reference/minio-mc/mc-rm/#mc.rm.-versions) to delete an object *and* all its versions.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
