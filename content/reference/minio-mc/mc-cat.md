---
title: "mc cat"
url: "/reference/minio-mc/mc-cat/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-cat"></a>
<a id="minio-mc-cat"></a>

<a id="command-mc.cat"></a>

## Syntax {#syntax}

The [`mc cat`](#command-mc.cat) command concatenates the contents of a file or object to another file or object. You can also use the command to display the contents of the specified file or object to `STDOUT`. [`cat`](#command-mc.cat) has similar functionality to `cat`.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command concatenates the contents of an object on a MinIO deployment to `STDOUT`:

```shell
mc cat play/mybucket/myobject.txt
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc cat`](#command-mc.cat) command has the following syntax:

```shell
mc [GLOBALFLAGS] cat                       \
                 ALIAS [ALIAS ...]         \
                 [--enc-c "value"]         \
                 [--offset "int"]          \
                 [--part-number "int"]     \
                 [--rewind]                \
                 [--tail "int"]            \
                 [--version-id "string"]   \
                 [--zip]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

You can also use [`mc cat`](#command-mc.cat) against a local filesystem to produce similar results to the `cat` commandline tool.

### Parameters {#parameters}

##### `ALIAS` {#mc.cat.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the object. For example:

```shell
mc cat myminio/mybucket/myobject.txt
```

You can specify multiple objects on the same or different MinIO deployment. For example:

```shell
mc cat myminio/mybucket/object.txt myminio/myotherbucket/object.txt
```

For an object on a local filesystem, specify the full path to that object. For example:

```shell
mc cat ~/data/object.txt
```

##### `--enc-c` {#mc.cat.-enc-c}

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

##### `--offset` {#mc.cat.-offset}

*mc-cmd*

*Optional*

Specify an integer that is the number of bytes from which the command offsets the output.

Mutually exclusive with the [`--part-number`](#mc.cat.-part-number) flag.

##### `--part-number` {#mc.cat.-part-number}

*mc-cmd*

*Optional*

Download a specific part number of a multi-part upload. Specify the integer of the part number to download.

Mutually exclusive with the [`--offset`](#mc.cat.-offset) and [`--tail`](#mc.cat.-tail) flags.

##### `--rewind` {#mc.cat.-rewind}

*mc-cmd*

*Optional*

Directs [`mc cat`](#command-mc.cat) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.cat.-rewind) requires that the specified [`ALIAS`](#mc.cat.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--tail` {#mc.cat.-tail}

*mc-cmd*

*Optional*

Specify an integer that is the number of bytes from which the command trims the output.

Mutually exclusive with the [`--part-number`](#mc.cat.-part-number) flag.

##### `--version-id, vid` {#mc.cat.-version-id}

*mc-cmd*

*Optional*

Directs [`mc cat`](#command-mc.cat) to operate only on the specified object version.

[`--version-id`](#mc.cat.-version-id) requires that the specified [`ALIAS`](#mc.cat.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--zip` {#mc.cat.-zip}

*mc-cmd*

*Optional*

Extracts the contents from a zip file on the source to the remote. Requires a MinIO deployment as the source `ALIAS`.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### View an S3 Object {#view-an-s3-object}

Use [`mc cat`](#command-mc.cat) to return the object:

```shell
mc cat ALIAS/PATH
```

- Replace [`ALIAS`](#mc.cat.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.cat.ALIAS) with the path to the object on the S3-compatible host.

### View an S3 Object at a Point-In-Time {#view-an-s3-object-at-a-point-in-time}

Use [`mc cat --rewind`](#mc.cat.-rewind) to return the object at a specific point-in-time in the past:

```shell
mc cat ALIAS/PATH --rewind DURATION
```

- Replace [`ALIAS`](#mc.cat.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.cat.ALIAS) with the path to the object on the S3-compatible host.
- Replace [`DURATION`](#mc.cat.-rewind) with the point-in-time in the past at which the command returns the object. For example, specify `30d` to return the version of the object 30 days prior to the current date.

{{% alert color="info" %}}
**Requires Versioning**

[`mc cat`](#command-mc.cat) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### View an S3 Object with Specific Version {#view-an-s3-object-with-specific-version}

Use [`mc cat --version-id`](#mc.cat.-version-id) to return a specific version of the object:

```shell
mc cat ALIAS/PATH --version-id VERSION
```

- Replace [`ALIAS`](#mc.cat.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.cat.ALIAS) with the path to the object on the S3-compatible host.
- Replace [`VERSION`](#mc.cat.-version-id) with the specific version of the object to return.

{{% alert color="info" %}}
**Requires Versioning**

[`mc cat`](#command-mc.cat) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### Download a particular part {#download-a-particular-part}

Use [`mc cat --part-number`](#mc.cat.-part-number) to download a particular part of a multi-part upload:

```shell
mc cat ALIAS/PATH --part-number=#
```

- Replace [`ALIAS`](#mc.cat.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the S3-compatible host.
- Replace [`PATH`](#mc.cat.ALIAS) with the path to the object on the S3-compatible host.
- Replace `#` with the integer of the part number to download. For example, to download part 3 of at 16-part multi-part file, use `--part-number=3`.

You cannot use the `--part-number` flag if you are using either the `--offset` or the `--tail` flags.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
