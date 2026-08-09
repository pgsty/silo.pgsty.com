---
title: "mc tag list"
url: "/reference/minio-mc/mc-tag-list/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-tag-list"></a>
<a id="minio-mc-tag-list"></a>

<a id="command-mc.tag.list"></a>

## Syntax {#syntax}

The [`mc tag list`](#command-mc.tag.list) command lists all tags from a bucket or object.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command lists tags for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc tag list myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] tag set                   \
                 [--rewind "string"]       \
                 [--versions]              \
                 [--version-id "string"]*  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc tag list --version-id`](#mc.tag.list.-version-id) is mutually exclusive with multiple parameters. See the reference documentation for more information.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.tag.list.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for a MinIO deployment and the full path to the object for which to list all tags (e.g. bucket and path to object). For example:

```text
mc tag list myminio/mybucket/object.txt
```

##### `--recursive, r` {#mc.tag.list.-recursive}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2023-05-04T18-10-16Z**

{{% /alert %}}

Recursively lists the tags for all objects at the path specified to [`ALIAS`](#mc.tag.list.ALIAS).

##### `--rewind` {#mc.tag.list.-rewind}

*mc-cmd*

*Optional*

Directs [`mc tag list`](#command-mc.tag.list) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.tag.list.-rewind) requires that the specified [`ALIAS`](#mc.tag.list.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--versions` {#mc.tag.list.-versions}

*mc-cmd*

*Optional*

Directs [`mc tag list`](#command-mc.tag.list) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.tag.list.-versions) requires that the specified [`ALIAS`](#mc.tag.list.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.tag.list.-versions) and [`--rewind`](#mc.tag.list.-rewind) together to list tags from all object versions which existed at a specific point in time.

##### `--version-id, vid` {#mc.tag.list.-version-id}

*mc-cmd*

*Optional*

Directs [`mc tag list`](#command-mc.tag.list) to operate only on the specified object version.

[`--version-id`](#mc.tag.list.-version-id) requires that the specified [`ALIAS`](#mc.tag.list.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with the following parameters:

- [`--rewind`](#mc.tag.list.-rewind)
- [`--versions`](#mc.tag.list.-versions)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Tags for a Bucket or Object {#list-tags-for-a-bucket-or-object}

Use [`mc tag list`](#command-mc.tag.list) to list tags for a bucket or object:

```shell
mc tag list ALIAS/PATH
```

- Replace [`ALIAS`](#mc.tag.list.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.tag.list.ALIAS) with the path to the bucket or object on the MinIO deployment.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
