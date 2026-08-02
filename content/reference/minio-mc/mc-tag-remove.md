---
title: "mc tag remove"
url: "/reference/minio-mc/mc-tag-remove/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-tag-remove"></a>
<a id="minio-mc-tag-remove"></a>

<a id="command-mc.tag.remove"></a>

## Syntax {#syntax}

The [`mc tag remove`](#command-mc.tag.remove) command removes all tags from a bucket or object.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes tags for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc tag remove myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] tag remove                \
                 [--rewind "string"]       \
                 [--versions]              \
                 [--version-id "string"]*  \
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc tag remove --version-id`](#mc.tag.remove.-version-id) is mutually exclusive with multiple parameters. See the reference documentation for more information.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.tag.remove.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for a MinIO deployment and the full path to the object on which to remove all tags (e.g. bucket and path to object). For example:

```text
mc tag remove myminio/mybucket/object.txt
```

##### `--recursive, r` {#mc.tag.remove.-recursive}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2023-05-04T18-10-16Z**

{{% /alert %}}

Recursively removes all tags from all objects at the specified [`ALIAS`](#mc.tag.remove.ALIAS).

##### `--rewind` {#mc.tag.remove.-rewind}

*mc-cmd*

*Optional*

Directs [`mc tag remove`](#command-mc.tag.remove) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.tag.remove.-rewind) requires that the specified [`ALIAS`](#mc.tag.remove.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--versions` {#mc.tag.remove.-versions}

*mc-cmd*

*Optional*

Directs [`mc tag remove`](#command-mc.tag.remove) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.tag.remove.-versions) requires that the specified [`ALIAS`](#mc.tag.remove.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.tag.remove.-versions) and [`--rewind`](#mc.tag.remove.-rewind) together to remove tags from all object versions which existed at a specific point in time.

##### `--version-id, vid` {#mc.tag.remove.-version-id}

*mc-cmd*

*Optional*

Directs [`mc tag remove`](#command-mc.tag.remove) to operate only on the specified object version.

[`--version-id`](#mc.tag.remove.-version-id) requires that the specified [`ALIAS`](#mc.tag.remove.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with the following parameters:

- [`--rewind`](#mc.tag.remove.-rewind)
- [`--versions`](#mc.tag.remove.-versions)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove Tags from a Bucket or Object {#remove-tags-from-a-bucket-or-object}

Use [`mc tag remove`](#command-mc.tag.remove) to remove tags from a bucket or object:

```shell
mc tag remove ALIAS/PATH
```

- Replace [`ALIAS`](#mc.tag.remove.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.tag.remove.ALIAS) with the path to the bucket or object on the MinIO deployment.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
