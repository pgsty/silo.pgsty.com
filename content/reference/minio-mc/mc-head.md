---
title: "mc head"
url: "/reference/minio-mc/mc-head/"
weight: 130
minio_origin: true
silo_modified: false
---

<a id="mc-head"></a>
<a id="minio-mc-head"></a>

<a id="command-mc.head"></a>

## Syntax {#syntax}

The [`mc head`](#command-mc.head) command displays the first `n` lines of an object, where `n` is an argument specified to the command.

[`mc head`](#command-mc.head) does not perform any transformation or formatting of object contents to facilitate readability. You can also use [`mc head`](#command-mc.head) against the local filesystem to produce similar results to the `head` commandline tool.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command returns the first 10 lines of an object in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc head myminio/mydata/myobject.txt
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] head                     \
                 [--lines int]            \
                 [--rewind "string"]      \
                 [--version-id "string"]  \
                 [--enc-c "string"]       \
                 ALIAS [ALIAS ...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.head.ALIAS}

*mc-cmd*

*Required*

The object or objects to print.

For an object on MinIO, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc head play/mybucket/object.txt
```

You can specify multiple objects on the same or different MinIO deployments. For example:

```text
mc head ~/mydata/object.txt myminio/mydata/object.txt
```

For an object on a local filesystem, specify the full path to that object. For example:

```text
mc head ~/mydata/object.txt
```

##### `--lines, n` {#mc.head.-lines}

*mc-cmd*

*Optional*

The number of lines to print.

Defaults to `10`.

##### `--enc-c` {#mc.head.-enc-c}

*mc-cmd*

*Optional*

Encrypt or decrypt objects using server-side [SSE-C encryption](/administration/server-side-encryption/#minio-sse) with client-managed keys.

The parameter accepts a key-value pair formatted as `KEY=VALUE`

<table>
  <tbody>
    <tr>
      <td><p><code>KEY</code></p></td>
      <td><p>The full path to the object as <code>alias/bucket/path/object.ext</code>.</p><p>You can specify only the top-level path to use a single encryption key for all operations in that path.</p></td>
    </tr>
    <tr>
      <td><p><code>VALUE</code></p></td>
      <td><p>Specify either a 32-byte RawBase64-encoded key <em>or</em> a 64-byte hex-encoded key for use with SSE-C encryption.</p><p>Raw Base64 encoding <strong>rejects</strong> <code>=</code>-padded keys.
Omit the padding or use a Base64 encoder that supports RAW formatting.</p></td>
    </tr>
  </tbody>
</table>

- `KEY` - the full path to the object as `alias/bucket/path/object`.
- `VALUE` - the 32-byte RAW Base64-encoded data key to use for encrypting object(s).

For example:

```shell
# RawBase64-Encoded string "mybucket32byteencryptionkeyssec"
--enc-c "myminio/mybucket/prefix/object.obj=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

You can specify multiple encryption keys by repeating the parameter.

Specify the path to a prefix to apply encryption to all matching objects at that path:

```shell
--enc-c "myminio/mybucket/prefix/=bXlidWNrZXQzMmJ5dGVlbmNyeXB0aW9ua2V5c3NlYwo"
```

{{% alert color="info" %}}
**Note**

MinIO strongly recommends against using SSE-C encryption in production workloads. Use SSE-KMS via the `--enc-kms` or SSE-S3 via `--enc-s3` parameters instead.
{{% /alert %}}

##### `--rewind` {#mc.head.-rewind}

*mc-cmd*

*Optional*

Directs [`mc head`](#command-mc.head) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.head.-rewind) requires that the specified [`ALIAS`](#mc.head.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--version-id, vid` {#mc.head.-version-id}

*mc-cmd*

*Optional*

Directs [`mc head`](#command-mc.head) to operate only on the specified object version.

[`--version-id`](#mc.head.-version-id) requires that the specified [`ALIAS`](#mc.head.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### View Partial Contents of an Object {#view-partial-contents-of-an-object}

Use [`mc head`](#command-mc.head) to return the first 10 lines of an object:

```shell
mc head ALIAS/PATH
```

- Replace [`ALIAS`](#mc.head.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.head.ALIAS) with the path to the object on the S3-compatible host.

### View Partial Contents of an Object at a Point in Time {#view-partial-contents-of-an-object-at-a-point-in-time}

Use [`mc head --rewind`](#mc.head.-rewind) to return the first 10 lines of the object at a specific point-in-time in the past:

```shell
mc head ALIAS/PATH --rewind DURATION
```

- Replace [`ALIAS`](#mc.head.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.head.ALIAS) with the path to the object on the S3-compatible host.
- Replace [`DURATION`](#mc.head.-rewind) with the point-in-time in the past at which the command returns the object. For example, specify `30d` to return the version of the object 30 days prior to the current date.

{{% alert color="info" %}}
**Requires Versioning**

[`mc head`](#command-mc.head) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### View Partial Contents of an Object with Specific Version {#view-partial-contents-of-an-object-with-specific-version}

Use [`mc head --version-id`](#mc.head.-version-id) to return the first 10 lines of the object at a specific point-in-time in the past:

```shell
mc head ALIAS/PATH --version-id VERSION
```

- Replace [`ALIAS`](#mc.head.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.head.ALIAS) with the path to the object on the S3-compatible host.
- Replace [`VERSION`](#mc.head.-version-id) with the version of the object. For example, specify `30d` to return the version of the object 30 days prior to the current date.

{{% alert color="info" %}}
**Requires Versioning**

[`mc head`](#command-mc.head) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
