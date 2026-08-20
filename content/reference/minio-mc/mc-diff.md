---
title: "mc diff"
url: "/reference/minio-mc/mc-diff/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-diff.rst
upstream_modified: false
---

<a id="mc-diff"></a>
<a id="minio-mc-diff"></a>

<a id="command-mc.diff"></a>

## Syntax {#syntax}

The [`mc diff`](#command-mc.diff) mc computes the differences between two filesystem directories or MinIO buckets. [`mc diff`](#command-mc.diff) lists only those objects which are missing or which differ in size. [`mc diff`](#command-mc.diff) does **not** compare the contents of objects.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command computes the difference between an object on a local filesystem and an object in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc diff ~/mydata/myobject.txt myminio/mydata/myobject.txt
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The [`mc diff`](#command-mc.diff) command has the following syntax:

```shell
mc [GLOBALFLAGS] diff SOURCE TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `SOURCE` {#mc.diff.SOURCE}

*mc-cmd*

*Required* The object to compare to the `TARGET`.

For an object from MinIO, specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc diff play/mybucket/object.txt ~/mydata/object.txt
```

For an object from a local filesystem, specify the full path to that object. For example:

```text
mc diff ~/mydata/object.txt play/mybucket/object.txt
```

##### `TARGET` {#mc.diff.TARGET}

*mc-cmd*

*Required* The object to compare to the `SOURCE`.

For an object from MinIO, specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc diff play/mybucket/object.txt ~/mydata/object.txt
```

For an object from a local filesystem, specify the full path to that object. For example:

```text
mc diff ~/mydata/object.txt play/mybucket/object.txt
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

The following example assumes that the `play` alias exists in the [`mc`](/reference/minio-mc/#command-mc) [configuration file](/reference/minio-mc/#mc-configuration). You can replace `play` with the alias for your preferred S3-compatible deployment.

See [`mc alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for more information on aliases.

```shell
mc diff play/bucket1 play/bucket2
```

## Behavior {#behavior}

### Output Legend {#output-legend}

[`mc diff`](#command-mc.diff) uses the following legend when formatting the diff output:

```text
FIRST < SECOND - object exists only in FIRST
FIRST > SECOND - object exists only in SECOND
FIRST ! SECOND - Newer object exists in FIRST
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
