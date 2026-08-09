---
title: "mc legalhold clear"
url: "/reference/minio-mc/mc-legalhold-clear/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-legalhold-clear"></a>
<a id="minio-mc-legalhold-clear"></a>

<a id="command-mc.legalhold.clear"></a>

## Syntax {#syntax}

The [`mc legalhold clear`](#command-mc.legalhold.clear) command removes the current [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold) setting for an object or objects.

Removing the legal hold on object(s) does *not* remove any other [GOVERNANCE Mode](/administration/object-management/object-retention/#minio-object-locking-governance) and [COMPLIANCE Mode](/administration/object-management/object-retention/#minio-object-locking-compliance) retention settings in place for the object(s)

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes the legal hold on all objects in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc legalhold clear --recursive myminio/mydata
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] legalhold clear \
                 [--recursive]   \
                 [--rewind]      \
                 [--version-id]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.legalhold.clear.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias) and path to the object or objects on which to remove the legal hold. For example:

```shell
mc legalhold clear play/mybucket/myobjects/objects.txt
```

##### `--recursive, r` {#mc.legalhold.clear.-recursive}

*mc-cmd*

*Optional*

Removes the legal hold on all objects in the [`ALIAS`](#mc.legalhold.clear.ALIAS) bucket or bucket prefix.

##### `--rewind` {#mc.legalhold.clear.-rewind}

*mc-cmd*

*Optional*

Directs [`mc legalhold clear`](#command-mc.legalhold.clear) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.legalhold.clear.-rewind) requires that the specified [`ALIAS`](#mc.legalhold.clear.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, vid` {#mc.legalhold.clear.-version-id}

*mc-cmd*

*Optional*

Directs [`mc legalhold clear`](#command-mc.legalhold.clear) to operate only on the specified object version.

[`--version-id`](#mc.legalhold.clear.-version-id) requires that the specified [`ALIAS`](#mc.legalhold.clear.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Retrieve the Legal Hold Status Objects {#retrieve-the-legal-hold-status-objects}

Use [`mc legalhold clear`](#command-mc.legalhold.clear) to retrieve the legal hold status of an object. Include [`--recursive`](#mc.legalhold.clear.-recursive) to return the legal hold status of the contents of a bucket:

```shell
mc legalhold clear [--recursive] ALIAS/PATH
```

- Replace [`ALIAS`](#mc.legalhold.clear.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the S3-compatible host.
- Replace [`PATH`](#mc.legalhold.clear.ALIAS) with the path to the bucket or object on the S3-compatible host. If specifying the path to a bucket or bucket prefix, include the [`--recursive`](#mc.legalhold.clear.-recursive) option.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
