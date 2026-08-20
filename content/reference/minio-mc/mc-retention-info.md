---
title: "mc retention info"
url: "/reference/minio-mc/mc-retention-info/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-retention-info.rst
upstream_modified: false
---

<a id="mc-retention-info"></a>

<a id="command-mc.retention.info"></a>

## Syntax {#syntax}

The [`mc retention info`](#command-mc.retention.info) command configures the [Write-Once Read-Many (WORM) locking](/administration/object-management/object-retention/#minio-object-locking) settings for an object or object(s) in a bucket. You can also set the default object lock settings for a bucket, where all objects without explicit object lock settings inherit the bucket default.

To lock an object under [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold), use [`mc legalhold set`](/reference/minio-mc/mc-legalhold-set/#command-mc.legalhold.set).

[`mc retention info`](#command-mc.retention.info) *requires* that the specified bucket has object locking enabled. You can **only** enable object locking at bucket creation. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for documentation on creating buckets with object locking enabled.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command returns the default object lock configuration for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc retention info --default myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] retention info            \
                 [--default]               \
                 [--recursive]             \
                 [--rewind "string"]       \
                 [--version-id "string"]*  \
                 [--versions]              \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc retention info --version-id`](#mc.retention.info.-version-id) is mutually exclusive with multiple other parameters. See the reference documentation for more information.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.retention.info.ALIAS}

*mc-cmd*

*Required*

The full path to the object for which to retrieve the object lock configuration. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of a configured S3-compatible service as the prefix to the `ALIAS` bucket path. For example:

```shell
mc retention info play/mybucket/object.txt
```

- **If the `ALIAS` specifies a bucket or bucket prefix, include**

  > [`--recursive`](#mc.retention.info.-recursive) to return the object lock settings for all objects in the bucket or bucket prefix.
- **If the `ALIAS` bucket has versioning enabled,**

  > [`mc retention info`](#command-mc.retention.info) by default applies to only the latest object version. Use [`--version-id`](#mc.retention.info.-version-id) or [`--versions`](#mc.retention.info.-versions) to return the object lock settings for a specific version or for all versions of the object.

##### `--default` {#mc.retention.info.-default}

*mc-cmd*

*Optional*

Returns the default object lock settings for the bucket specified to [`ALIAS`](#mc.retention.info.ALIAS).

If specifying [`--default`](#mc.retention.info.-default), [`mc retention info`](#command-mc.retention.info) ignores all other flags.

##### `--recursive, r` {#mc.retention.info.-recursive}

*mc-cmd*

*Optional*

Recursively returns the object lock settings for all objects in the specified [`ALIAS`](#mc.retention.info.ALIAS) path.

Mutually exclusive with [`--version-id`](#mc.retention.info.-version-id).

##### `--rewind` {#mc.retention.info.-rewind}

*mc-cmd*

*Optional*

Directs [`mc retention info`](#command-mc.retention.info) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.retention.info.-rewind) requires that the specified [`ALIAS`](#mc.retention.info.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, vid` {#mc.retention.info.-version-id}

*mc-cmd*

*Optional*

Directs [`mc retention info`](#command-mc.retention.info) to operate only on the specified object version.

[`--version-id`](#mc.retention.info.-version-id) requires that the specified [`ALIAS`](#mc.retention.info.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with any of the following flags:

- [`--versions`](#mc.retention.info.-versions)
- [`--rewind`](#mc.retention.info.-rewind)
- [`--recursive`](#mc.retention.info.-recursive)

##### `--versions` {#mc.retention.info.-versions}

*mc-cmd*

*Optional*

Directs [`mc retention info`](#command-mc.retention.info) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.retention.info.-versions) requires that the specified [`ALIAS`](#mc.retention.info.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.retention.info.-versions) and [`--rewind`](#mc.retention.info.-rewind) together to retrieve the retention settings for all object versions that existed at a specific point-in-time.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Retrieve Object Lock Settings for an Object or Object(s) {#retrieve-object-lock-settings-for-an-object-or-object-s}

{{< tabs group="specific-object-multiple-objects" >}}
{{< tab label="Specific Object" value="specific-object" >}}
```shell
mc retention info ALIAS/PATH
```

- Replace [`ALIAS`](#mc.retention.info.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.info.ALIAS) with the path to the object.
{{< /tab >}}
{{< tab label="Multiple Objects" value="multiple-objects" >}}
Use [`mc retention info`](#command-mc.retention.info) with [`--recursive`](#mc.retention.info.-recursive) to retrieve the retention settings for all objects in a bucket:

```shell
mc retention info --recursive ALIAS/PATH
```

- Replace [`ALIAS`](#mc.retention.info.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.info.ALIAS) with the path to the bucket.
{{< /tab >}}
{{< /tabs >}}

> The bucket *must* have object locking enabled to use this command. You can only enable object locking when creating a bucket. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for more information on creating buckets with object locking enabled.

### Retrieve Default Object Lock Settings for a Bucket {#retrieve-default-object-lock-settings-for-a-bucket}

Use [`mc retention info`](#command-mc.retention.info) with [`--default`](#mc.retention.info.-default) to retrieve the default object lock settings for a bucket:

```shell
mc retention info --default ALIAS/PATH
```

- **Replace [`ALIAS`](#mc.retention.info.ALIAS) with the**

  > [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.retention.info.ALIAS) with the path to the bucket.

> The bucket *must* have object locking enabled to use this command. You can only enable object locking when creating a bucket. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for more information on creating buckets with object locking enabled.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
