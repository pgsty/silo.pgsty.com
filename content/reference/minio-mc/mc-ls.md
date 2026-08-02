---
title: "mc ls"
url: "/reference/minio-mc/mc-ls/"
weight: 220
minio_origin: true
silo_modified: false
---

<a id="mc-ls"></a>

<a id="command-mc.ls"></a>

## Syntax {#syntax}

The [`mc ls`](#command-mc.ls) command lists buckets and objects on MinIO or another S3-compatible service.

You can also use [`mc ls`](#command-mc.ls) against the local filesystem to produce similar results as the `ls` command.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists all objects *and* object versions in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc ls --recursive --versions myminio/mydata
```

The output resembles the following:

```shell
[2022-11-08 11:30:24 PST]    52MB  STANDARD log-data.csv
[2022-11-09 12:20:18 PST]    120MB WARM videos/event-2022-11-09.mp4
```

- `STANDARD` marks objects stored on the MinIO deployment
- `WARM` marks objects stored on the remote tier with matching name
- `videos/` indicates the prefix for the object
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ls              \
                 [--incomplete]  \
                 [--recursive]   \
                 [--rewind]      \
                 [--versions]    \
                 [--summarize]   \
                 ALIAS [ALIAS ...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ls.ALIAS}

*mc-cmd*

*Required* The object or objects to copy.

For listing objects on MinIO, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc ls play/mybucket/object.txt
```

For listing objects on a local filesystem, specify the full path to that object. For example:

```text
mc ls ~/mydata/object.txt
```

If you specify a directory or bucket to [`ALIAS`](#mc.ls.ALIAS), you must also specify [`--recursive`](#mc.ls.-recursive) to recursively list the contents of that directory or bucket. If you omit the `--recursive` argument, [`ls`](#command-mc.ls) only lists objects in the top level of the specified directory or bucket.

##### `incomplete, -I` {#mc.ls.incomplete}

*mc-cmd*

*Optional* Returns any incomplete uploads on the specified [`ALIAS`](#mc.ls.ALIAS) bucket.

##### `--recursive, r` {#mc.ls.-recursive}

*mc-cmd*

*Optional* Recursively lists the contents of each bucket or directory in the [`ALIAS`](#mc.ls.ALIAS).

##### `--rewind` {#mc.ls.-rewind}

*mc-cmd*

*Optional*

Directs [`mc ls`](#command-mc.ls) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.ls.-rewind) requires that the specified [`ALIAS`](#mc.ls.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--rewind`](#mc.ls.-rewind) and [`--versions`](#mc.ls.-versions) together to display on those object versions which existed at a specific point in time.

##### `--versions` {#mc.ls.-versions}

*mc-cmd*

*Optional*

Directs [`mc ls`](#command-mc.ls) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.ls.-versions) requires that the specified [`ALIAS`](#mc.ls.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.ls.-versions) and [`--rewind`](#mc.ls.-rewind) together to display on those object versions which existed at a specific point in time.

##### `--summarize` {#mc.ls.-summarize}

*mc-cmd*

*Optional* Displays summarized information for the specified `ALIAS` path.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Bucket Contents {#list-bucket-contents}

Use [`mc ls`](#mc.ls.ALIAS) to list the contents of a bucket:

```shell
mc ls [--recursive] ALIAS/PATH
```

- Replace [`ALIAS`](#mc.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ls.ALIAS) with the path to the bucket on the S3-compatible host.

  If specifying the path to the S3 root (`ALIAS` only), include the [`--recursive`](#mc.ls.-recursive) option.

### List Object Versions {#list-object-versions}

Use [`mc ls --versions`](#mc.ls.-versions) to list all versions of an object:

```shell
mc ls --versions ALIAS/PATH
```

- Replace [`ALIAS`](#mc.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ls.ALIAS) with the path to the bucket or object on the S3-compatible host.

{{% alert color="info" %}}
**Requires Versioning**

[`mc ls`](#command-mc.ls) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### List Bucket Contents at Point in Time {#list-bucket-contents-at-point-in-time}

Use [`mc ls --versions`](#mc.ls.-versions) to list all versions of an object:

```shell
mc ls --rewind DURATION ALIAS/PATH
```

- Replace [`ALIAS`](#mc.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.ls.ALIAS) with the path to the bucket or object on the S3-compatible host.
- Replace [`DURATION`](#mc.ls.-rewind) with the point-in-time in the past at which the command returns the object. For example, specify `30d` to return the version of the object 30 days prior to the current date.

{{% alert color="info" %}}
**Requires Versioning**

[`mc ls`](#command-mc.ls) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
