---
title: "mc tag set"
url: "/reference/minio-mc/mc-tag-set/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-tag-set"></a>
<a id="minio-mc-tag-set"></a>

<a id="command-mc.tag.set"></a>

## Syntax {#syntax}

The [`mc tag set`](#command-mc.tag.set) command sets one or more tags to a bucket or object.

MinIO supports adding up to 10 custom tags to an object.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command sets tags for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc tag set myminio/mydata "tag1=value1&tag2=value2"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] tag set                   \
                 [--rewind "string"]       \
                 [--versions]              \
                 [--version-id "string"]*  \
                 ALIAS                     \
                 "TAGS"
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc tag set --version-id`](#mc.tag.set.-version-id) is mutually exclusive with multiple parameters. See the reference documentation for more information.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.tag.set.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for a MinIO deployment and the full path to the object on which to apply the tag (e.g. bucket and path to object). For example:

```text
mc tag set myminio/mybucket/object.txt
```

##### `TAGS` {#mc.tag.set.TAGS}

*mc-cmd*

*Required*

An ampersand-seperated (`&`) list of key-value pairs (`KEY=VALUE`), where each pair represents one tag to assign to the object. For example:

```text
mc tag set myminio/mybucket/object.txt "key1=value1&key2=value2"
```

##### `--exclude-folders` {#mc.tag.set.-exclude-folders}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2024-01-11T05-49-32Z**

{{% /alert %}}

When used with [`--recursive`](#mc.tag.set.-recursive), causes [`mc tag set`](#command-mc.tag.set) to **not** traverse child prefixes. Tags are only applied to objects at the specified path. Requires [`--recursive`](#mc.tag.set.-recursive).

The following example applies the tag `destination=international` to objects at `vacation-photos/cancun/` but not `vacation-photos/cancun/ocean/` or other prefixes.

For example, the above would add the tags to the object at``vacation-photos/cancun/pretty-beach.jpg`` but not to the object at``vacation-photos/cancun/ocean/tropical-fish.jpg``.

```shell
mc tag set myminio/vacation-photos/cancun "destination=international" --exclude-folders --recursive
```

##### `--recursive, r` {#mc.tag.set.-recursive}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2023-05-04T18-10-16Z**

{{% /alert %}}

Recursively applies the tag to all objects at the path specified to [`ALIAS`](#mc.tag.set.ALIAS).

##### `--rewind` {#mc.tag.set.-rewind}

*mc-cmd*

*Optional*

Directs [`mc tag set`](#command-mc.tag.set) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.tag.set.-rewind) requires that the specified [`ALIAS`](#mc.tag.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--versions` {#mc.tag.set.-versions}

*mc-cmd*

*Optional*

Directs [`mc tag set`](#command-mc.tag.set) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.tag.set.-versions) requires that the specified [`ALIAS`](#mc.tag.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.tag.set.-versions) and [`--rewind`](#mc.tag.set.-rewind) together to apply the tag all object versions which existed at a specific point in time.

##### `--version-id, --vid` {#mc.tag.set.-version-id}

*mc-cmd*

*Optional*

Directs [`mc tag set`](#command-mc.tag.set) to operate only on the specified object version.

[`--version-id`](#mc.tag.set.-version-id) requires that the specified [`ALIAS`](#mc.tag.set.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with the following parameters:

- [`--rewind`](#mc.tag.set.-rewind)
- [`--versions`](#mc.tag.set.-versions)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Apply Tags to a Bucket or Object {#apply-tags-to-a-bucket-or-object}

Use [`mc tag set`](#command-mc.tag.set) to apply tags to a bucket or object:

```shell
mc tag set ALIAS/PATH "TAGS"
```

- Replace [`ALIAS`](#mc.tag.set.ALIAS) with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
- Replace [`PATH`](#mc.tag.set.ALIAS) with the path to the bucket or object on the MinIO deployment.
- Replace [`TAGS`](#mc.tag.set.TAGS) with one or more ampersand-separated (`&`) key-value pairs for each tag and its corresponding value.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
