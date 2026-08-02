---
title: "mc cp"
url: "/reference/minio-mc/mc-cp/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-cp"></a>
<a id="minio-mc-cp"></a>

<a id="command-mc.cp"></a>

## Syntax {#syntax}

The [`mc cp`](#command-mc.cp) command copies objects to or from a MinIO deployment, where the source can MinIO *or* a local filesystem.

You can also use [`mc cp`](#command-mc.cp) against the local filesystem to produce similar results to the `cp` commandline tool.

{{% alert color="info" %}}
**Note**

[`mc cp`](#command-mc.cp) only copies the latest version or the specified version of an object without any version information or modification date. To copy all versions, version information, and related metadata, use [`mc replicate add`](/reference/minio-mc/mc-replicate-add/#command-mc.replicate.add) or [`mc admin replicate`](/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate).
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command copies files from a local filesystem directory to the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc cp --recursive ~/mydata/ myminio/mydata/
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The [`mc cp`](#command-mc.cp) command has the following syntax:

```shell
mc [GLOBALFLAGS] cp                                                        \
                 [--attr "string"]                                         \
                 [--disable-multipart]                                     \
                 [--enc-kms "string"]                                      \
                 [--enc-s3 "string"]                                       \
                 [--enc-c "string"]                                        \
                 [--legal-hold "on"]                                       \
                 [--limit-download string]                                 \
                 [--limit-upload string]                                   \
                 [--md5]                                                   \
                 [--newer-than "string"]                                   \
                 [--older-than "string"]                                   \
                 [--preserve]                                              \
                 [--recursive]                                             \
                 [--retention-mode "string" --retention-duration "string"] \
                 [--rewind "string"]                                       \
                 [--storage-class "string"]                                \
                 [--tags "string"]                                         \
                 [--version-id "string"]                                   \
                 [--zip]                                                   \
                 SOURCE [SOURCE ...]                                       \
                 TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `SOURCE` {#mc.cp.SOURCE}

*mc-cmd*

*Required*

The object or objects to copy.

For copying an object from MinIO, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc cp play/mybucket/object.txt ~/mydata/object.txt
```

Specify multiple `SOURCE` paths to copy multiple objects to the specified [`TARGET`](#mc.cp.TARGET). [`mc cp`](#command-mc.cp) treats the *last* specified alias or filesystem path as the `TARGET`. For example:

```text
mc cp ~/data/object.txt myminio/mydata/object.txt play/mydata/
```

For copying an object from a local filesystem, specify the full path to that object. For example:

```text
mc cp ~/mydata/object.txt play/mybucket/object.txt
```

If you specify a directory or bucket to [`SOURCE`](#mc.cp.SOURCE), you must also specify [`--recursive`](#mc.cp.-recursive) to recursively copy the contents of that directory or bucket. If you omit the `--recursive` argument, [`cp`](#command-mc.cp) only copies objects in the top level of the specified directory or bucket.

##### `TARGET` {#mc.cp.TARGET}

*mc-cmd*

*Required*

The full path to which [`mc cp`](#command-mc.cp) copies the object.

For copying an object to MinIO, specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and the full path to that object (e.g. bucket and path to object). For example:

```text
mc cp ~/mydata/object.txt play/mybucket/object.txt
```

For copying an object from a local filesystem, specify the full path to that object. For example:

```text
mc cp play/mybucket/object.txt ~/mydata/object.txt
```

##### `--attr` {#mc.cp.-attr}

*mc-cmd*

*Optional*

Add custom metadata for the object. Specify key-value pairs as `KEY=VALUE\;`. For example, `--attr key1=value1\;key2=value2\;key3=value3`.

##### `--checksum` {#mc.cp.-checksum}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2024-10-02T08-27-28Z**

{{% /alert %}}

Add a checksum to an uploaded object.

Valid values are: - `MD5` - `CRC32` - `CRC32C` - `SHA1` - `SHA256`

The flag requires server trailing headers and works with AWS or MinIO targets.

##### `--disable-multipart` {#mc.cp.-disable-multipart}

*mc-cmd*

*Optional*

Disables multipart upload for the copy session.

##### `--enc-kms` {#mc.cp.-enc-kms}

*mc-cmd*

Encrypt or decrypt objects using server-side [SSE-KMS encryption](/administration/server-side-encryption/#minio-sse) with client-managed keys.

The parameter accepts a key-value pair formatted as `KEY=VALUE`

<table>
  <tbody>
    <tr>
      <td><p><code>KEY</code></p></td>
      <td><p>The full path to the object as <code>alias/bucket/path/object.ext</code>.</p><p>You can specify only the top-level path to use a single encryption key for all operations in that path.</p></td>
    </tr>
    <tr>
      <td><p><code>VALUE</code></p></td>
      <td><p>Specify an existing data key on the external KMS.</p><p>See the <a href="/reference/minio-mc-admin/mc-admin-kms-key/#mc.admin.kms.key.create"><code>mc admin kms key create</code></a> reference for creating data keys.</p></td>
    </tr>
  </tbody>
</table>

For example:

```shell
--enc-kms "myminio/mybucket/prefix/object.obj=mybucketencryptionkey"
```

You can specify multiple encryption keys by repeating the parameter.

Specify the path to a prefix to apply encryption to all matching objects at that path:

```shell
--enc-kms "myminio/mybucket/prefix/=mybucketencryptionkey"
```

##### `--enc-s3` {#mc.cp.-enc-s3}

*mc-cmd*

*Optional*

Encrypt or decrypt objects using server-side [SSE-S3 encryption](/administration/server-side-encryption/#minio-sse) with KMS-managed keys. Specify the full path to the object as `alias/bucket/prefix/object`.

For example:

```shell
--enc-s3 "myminio/mybucket/prefix/object.obj"
```

You can specify the parameter multiple times to denote different object(s) to encrypt:

```shell
--enc-s3 "myminio/mybucket/foo/fooobject.obj" --enc-s3 "myminio/mybucket/bar/barobject.obj"
```

Specify the path to a prefix to apply encryption to all matching objects at that path:

```shell
--enc-s3 "myminio/mybucket/foo"
```

##### `--enc-c` {#mc.cp.-enc-c}

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

##### `--legal-hold` {#mc.cp.-legal-hold}

*mc-cmd*

*Optional*

Enables indefinite [legal hold](/administration/object-management/object-retention/#minio-object-locking-legalhold) object locking on the copied objects.

Specify `on`.

##### `--limit-download` {#mc.cp.-limit-download}

*mc-cmd*

*Optional*

Limit client-side download rates to no more than a specified rate in KiB/s, MiB/s, or GiB/s. This affects only the download to the local device running the MinIO Client. Valid units include:

- `B` for bytes
- `K` for kilobytes
- `M` for megabytes
- `G` for gigabytes
- `T` for terabytes
- `Ki` for kibibytes
- `Mi` for mibibytes
- `Gi` for gibibytes
- `Ti` for tebibytes

For example, to limit download rates to no more than 1 GiB/s, use the following:

```
--limit-download 1G
```

If not specified, MinIO uses an unlimited download rate.

##### `--limit-upload` {#mc.cp.-limit-upload}

*mc-cmd*

*Optional*

Limit client-side upload rates to no more than the specified rate in KiB/s, MiB/s, or GiB/s. This affects only the upload from the local device running the MinIO Client. Valid units include:

- `B` for bytes
- `K` for kilobytes
- `M` for megabytes
- `G` for gigabytes
- `T` for terabytes
- `Ki` for kibibytes
- `Mi` for mibibytes
- `Gi` for gibibytes
- `Ti` for tebibytes

For example, to limit upload rates to no more than 1 GiB/s, use the following:

```
--limit-upload 1G
```

If not specified, MinIO uses an unlimited upload rate.

##### `--md5` {#mc.cp.-md5}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**Changed: RELEASE.2024-10-02T08-27-28Z**

Replaced by the [`--checksum`](#mc.cp.-checksum) flag.
{{% /alert %}}

Forces all uploads to calculate MD5 checksums.

##### `--newer-than` {#mc.cp.-newer-than}

*mc-cmd*

*Optional*

Copy object(s) newer than the specified number of days. Specify a string in `#d#hh#mm#ss` format. For example: `--older-than 1d2hh3mm4ss`

Defaults to `0` (all objects).

##### `--older-than` {#mc.cp.-older-than}

*mc-cmd*

*Optional*

Copy object(s) older than the specified time limit. Specify a string in `#d#hh#mm#ss` format. For example: `--older-than 1d2hh3mm4ss`

Defaults to `0` (all objects).

##### `--preserve, a` {#mc.cp.-preserve}

*mc-cmd*

*Optional*

Preserve file system attributes and bucket policy rules of the [`SOURCE`](#mc.cp.SOURCE) directories, buckets, and objects on the [`TARGET`](#mc.cp.TARGET) bucket(s).

##### `--recursive, r` {#mc.cp.-recursive}

*mc-cmd*

*Optional*

Recursively copy the contents of each bucket or directory [`SOURCE`](#mc.cp.SOURCE) to the [`TARGET`](#mc.cp.TARGET) bucket.

##### `--retention-duration` {#mc.cp.-retention-duration}

*mc-cmd*

*Optional*

The duration of the [WORM retention mode](/administration/object-management/object-retention/#minio-object-locking-retention-modes) to apply to the copied object(s).

Specify the duration as a string in `#d#hh#mm#ss` format. For example: `--retention-duration "1d2hh3mm4ss"`.

Requires specifying [`--retention-mode`](#mc.cp.-retention-mode).

##### `--retention-mode` {#mc.cp.-retention-mode}

*mc-cmd*

*Optional*

Enables [object locking mode](/administration/object-management/object-retention/#minio-object-locking-retention-modes) on the copied object(s). Supports the following values:

- `GOVERNANCE`
- `COMPLIANCE`

Requires specifying [`--retention-duration`](#mc.cp.-retention-duration).

##### `--rewind` {#mc.cp.-rewind}

*mc-cmd*

*Optional*

Directs [`mc cp`](#command-mc.cp) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.cp.-rewind) requires that the specified [`SOURCE`](#mc.cp.SOURCE) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--storage-class, sc` {#mc.cp.-storage-class}

*mc-cmd*

*Optional*

Set the storage class for the new object(s) on the [`TARGET`](#mc.cp.TARGET).

See [https://docs.aws.amazon.com/AmazonS3/latest/dev/storage-class-intro.html](https://docs.aws.amazon.com/AmazonS3/latest/dev/storage-class-intro.html) for more information on S3 storage classes.

##### `--tags` {#mc.cp.-tags}

*mc-cmd*

*Optional*

Applies one or more tags to the copied objects.

Specify an ampersand-separated list of key-value pairs as `KEY1=VALUE1&KEY2=VALUE2`, where each pair represents one tag to assign to the objects.

##### `--version-id, vid` {#mc.cp.-version-id}

*mc-cmd*

*Optional*

Directs [`mc cp`](#command-mc.cp) to operate only on the specified object version.

[`--version-id`](#mc.cp.-version-id) requires that the specified [`SOURCE`](#mc.cp.SOURCE) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--zip` {#mc.cp.-zip}

*mc-cmd*

*Optional*

During copy, extract files from a *.zip* archive. Only functional when the source archive file exists on a MinIO deployment.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Copy Object to S3 {#copy-object-to-s3}

Use [`mc cp`](#command-mc.cp) to copy an object to an S3-compatible host:

{{< tabpane text=true persist=header >}}
{{% tab header="Filesystem to S3" %}}
```shell
mc cp SOURCE ALIAS/PATH
```

- Replace [`SOURCE`](#mc.cp.SOURCE) with the filesystem path to the object.
- Replace [`ALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.cp.TARGET) with the path to the object on the S3-compatible host. You can specify a different object name to “rename” the object on copy.
{{% /tab %}}
{{% tab header="S3 to S3" %}}
```shell
mc cp SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace [`SRCALIAS`](#mc.cp.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a source S3-compatible host.
- Replace [`SRCPATH`](#mc.cp.SOURCE) with the path to the object on the S3-compatible host.
- Replace [`TGTALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a target S3-compatible host.
- Replace [`TGTPATH`](#mc.cp.TARGET) with the path to the object on a target S3-compatible host. Omit the object name to use the `SRCPATH` object name.
{{% /tab %}}
{{< /tabpane >}}

### Recursively Copy Objects to S3 {#recursively-copy-objects-to-s3}

Use [`mc cp --recursive`](#mc.cp.-recursive) to recursively copy objects to an S3-compatible host:

{{< tabpane text=true persist=header >}}
{{% tab header="Filesystem to S3" %}}
```shell
mc cp --recursive SOURCE ALIAS/PATH
```

- Replace [`SOURCE`](#mc.cp.SOURCE) with the filesystem path to the directory containing the file(s).
- Replace [`ALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.cp.TARGET) with the path to the object on the S3-compatible host. [`mc cp`](#command-mc.cp) uses the `SOURCE` filenames when creating the objects on the target host.
{{% /tab %}}
{{% tab header="S3 to S3" %}}
```shell
mc cp --recursive SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace [`SRCALIAS`](#mc.cp.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a source S3-compatible host.
- Replace [`SRCPATH`](#mc.cp.SOURCE) with the path to the bucket or bucket prefix on the source S3-compatible host.
- Replace [`TGTALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a target S3-compatible host.
- Replace [`TGTPATH`](#mc.cp.TARGET) with the path to the object on the target S3-compatible host. [`mc cp`](#command-mc.cp) uses the `SRCPATH` object names when creating objects on the target host.
{{% /tab %}}
{{< /tabpane >}}

### Copy Point-In-Time Version of Object {#copy-point-in-time-version-of-object}

Use [`mc cp --rewind`](#mc.cp.-rewind) to copy an object as it existed at a specific point in time. This command only applies to S3-to-S3 copy.

```shell
mc cp --rewind DURATION SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace [`DURATION`](#mc.cp.-rewind) with the point-in-time in the past at which the command copies the object. For example, specify `30d` to copy the version of the object 30 days prior to the current date.
- Replace [`SRCALIAS`](#mc.cp.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a source S3-compatible host.
- Replace [`SRCPATH`](#mc.cp.SOURCE) with the path to the object on the source S3-compatible host.
- Replace [`TGTALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a target S3-compatible host.
- Replace [`TGTPATH`](#mc.cp.TARGET) with the path to the object on the target S3-compatible host. Omit the object name to use the `SRCPATH` object name.

{{% alert color="info" %}}
**Requires Versioning**

[`mc cp`](#command-mc.cp) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### Copy Specific Version of Object {#copy-specific-version-of-object}

Use [`mc cp --version-id`](#mc.cp.-version-id) to copy a specific version of an object. This command only applies to S3-to-S3 copy.

```shell
mc cp --version-id VERSION SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace [`VERSION`](#mc.cp.-rewind) with the version of the object to copy.
- Replace [`SRCALIAS`](#mc.cp.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a source S3-compatible host.
- Replace [`SRCPATH`](#mc.cp.SOURCE) with the path to the object on the source S3-compatible host.
- Replace [`TGTALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a target S3-compatible host.
- Replace [`TGTPATH`](#mc.cp.TARGET) with the path to the object on the target S3-compatible host. Omit the object name to use the `SRCPATH` object name.

{{% alert color="info" %}}
**Requires Versioning**

[`mc cp`](#command-mc.cp) requires [bucket versioning](/administration/object-management/object-versioning/#minio-bucket-versioning) to use this feature. Use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable versioning on a bucket.
{{% /alert %}}

### Add a `content-type` Value {#add-a-content-type-value}

Use [`mc cp --attr`](#mc.cp.-attr) to add a `content-type` value. This command only applies to S3-to-S3 copy.

```shell
mc cp --attr="content-type=CONTENT-TYPE" SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace `CONTENT-TYPE` with the desired content type (also called a [media type](https://www.iana.org/assignments/media-types/media-types.xhtml)).
- Replace [`SRCALIAS`](#mc.cp.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a source S3-compatible host.
- Replace [`SRCPATH`](#mc.cp.SOURCE) with the path to the object on the source S3-compatible host.
- Replace [`TGTALIAS`](#mc.cp.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a target S3-compatible host.
- Replace [`TGTPATH`](#mc.cp.TARGET) with the path to the object on the target S3-compatible host. Omit the object name to use the `SRCPATH` object name.

The following example sets a `content-type` of `application/json`:

```
 mc cp data.ndjson --attr="content-type=application/json" myminio/mybucket
```

## Behavior {#behavior}

[`mc cp`](#command-mc.cp) verifies all copy operations to object storage using MD5SUM checksums.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
