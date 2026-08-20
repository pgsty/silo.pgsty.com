---
title: "mc legalhold info"
url: "/reference/minio-mc/mc-legalhold-info/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-legalhold-info.rst
upstream_modified: false
---

<a id="mc-legalhold-info"></a>
<a id="minio-mc-legalhold-info"></a>

<a id="command-mc.legalhold.info"></a>

## Syntax {#syntax}

The [`mc legalhold info`](#command-mc.legalhold.info) command returns the current [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold) setting for an object or objects.

[`mc legalhold`](/reference/minio-mc/mc-legalhold/#command-mc.legalhold) *requires* that the specified bucket has object locking enabled. You can **only** enable object locking at bucket creation. See [`mc mb --with-lock`](/reference/minio-mc/mc-mb/#mc.mb.-with-lock) for documentation on creating buckets with object locking enabled.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command retrieves the current legalhold status for objects in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc legalhold info --recursive myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] legalhold info  \
                 [--recursive]   \
                 [--rewind]      \
                 [--version-id]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.legalhold.info.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias) and path to the object or objects on which to enable the legal hold. For example:

```shell
mc legalhold info play/mybucket/myobjects/objects.txt
```

##### `--recursive, r` {#mc.legalhold.info.-recursive}

*mc-cmd*

*Optional*

Returns the legal hold status of all objects in the [`ALIAS`](#mc.legalhold.info.ALIAS) bucket or bucket prefix.

##### `--rewind` {#mc.legalhold.info.-rewind}

*mc-cmd*

*Optional*

Directs [`mc legalhold info`](#command-mc.legalhold.info) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.legalhold.info.-rewind) requires that the specified [`ALIAS`](#mc.legalhold.info.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, vid` {#mc.legalhold.info.-version-id}

*mc-cmd*

*Optional*

Directs [`mc legalhold info`](#command-mc.legalhold.info) to operate only on the specified object version.

[`--version-id`](#mc.legalhold.info.-version-id) requires that the specified [`ALIAS`](#mc.legalhold.info.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Retrieve the Legal Hold Status Objects {#retrieve-the-legal-hold-status-objects}

Use [`mc legalhold info`](#command-mc.legalhold.info) to retrieve the legal hold status of an object. Include [`--recursive`](#mc.legalhold.info.-recursive) to return the legal hold status of the contents of a bucket:

```shell
mc legalhold clear [--recursive] ALIAS/PATH
```

- Replace [`ALIAS`](#mc.legalhold.info.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the S3-compatible host.
- Replace [`PATH`](#mc.legalhold.info.ALIAS) with the path to the bucket or object on the S3-compatible host. If specifying the path to a bucket or bucket prefix, include the [`--recursive`](#mc.legalhold.info.-recursive) option.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
