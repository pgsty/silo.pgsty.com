---
title: "mc du"
url: "/reference/minio-mc/mc-du/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-du.rst
upstream_modified: false
---

<a id="mc-du"></a>
<a id="minio-mc-du"></a>

<a id="command-mc.du"></a>

## Syntax {#syntax}

The [`mc du`](#command-mc.du) command summarizes the disk usage of buckets and folders. You can also use [`du`](#command-mc.du) against the local filesystem to produce similar results as the `du` command.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command prints the disk usage of the `mybucket` bucket on the `myminio` MinIO deployment:

```shell
mc du play/mybucket
```

The output resembles the following:

```shell
825KiB 3 objects        mybucket
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The [`mc du`](#command-mc.du) command has the following syntax:

```shell
mc [GLOBALFLAGS] du                    \
                 [--depth]             \
                 [--recursive]         \
                 [--rewind]            \
                 [--versions]          \
                 ALIAS [ALIAS ...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.du.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the folder. For example:

```shell
mc du myminio/mybucket
```

You can specify multiple buckets and folders on the same or different MinIO deployment. For example:

```shell
mc du myminio/mybucket myminio/myotherbucket/myfolder
```

For a folder on a local filesystem, specify the full path to that folder. For example:

```shell
mc du ~/data/images
```

The time required for [`mc du`](#command-mc.du) to complete depends on the size of the target buckets and folders. A large bucket may take some time to generate a disk usage summary.

##### `--depth, d` {#mc.du.-depth}

*mc-cmd*

*Optional*

Print the total for all folders N or fewer levels below the path specified in the command. Default is 0, for the specified path only.

##### `--recursive, r` {#mc.du.-recursive}

*mc-cmd*

*Optional*

Recursively print the total for each bucket or child folder.

##### `--rewind` {#mc.du.-rewind}

*mc-cmd*

*Optional*

Directs [`mc du`](#command-mc.du) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.du.-rewind) requires that the specified [`ALIAS`](#mc.du.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--rewind`](#mc.du.-rewind) and [`--versions`](#mc.du.-versions) together to show the disk usage for those object versions which existed at a specific point in time.

##### `--versions` {#mc.du.-versions}

*mc-cmd*

*Optional*

Directs [`mc du`](#command-mc.du) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.du.-versions) requires that the specified [`ALIAS`](#mc.du.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.du.-versions) and [`--rewind`](#mc.du.-rewind) together to show the disk usage for those object versions which existed at a specific point in time.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### View the Disk Usage for a Bucket or Folder {#view-the-disk-usage-for-a-bucket-or-folder}

Use [`mc du`](#command-mc.du) to print a summary of the disk usage for a bucket or folder:

```shell
mc du ALIAS/PATH
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket or folder on the S3-compatible host.

### View the Disk Usage at a Point-In-Time {#view-the-disk-usage-at-a-point-in-time}

Use [`mc du --rewind`](#mc.du.-rewind) to print a summary of disk usage at a specific point-in-time in the past:

```shell
mc du --rewind DURATION ALIAS/PATH
```

- Replace `DURATION` with the desired point-in-time in the past. For example, specify `30d` to show the disk usage 30 days prior to the current date.
- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket or folder on the S3-compatible host.

> [!NOTE]
> **Requires Versioning**
>
> [`mc du`](#command-mc.du) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.

### View the Disk Usage Recursively {#view-the-disk-usage-recursively}

Use [`mc du --recursive`](#mc.du.-recursive) to print a summary for each folder recursively:

```shell
mc du --recursive ALIAS/PATH
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace `PATH` with the path to the bucket or folder on the S3-compatible host.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
