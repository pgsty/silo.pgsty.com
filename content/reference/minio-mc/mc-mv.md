---
title: "mc mv"
url: "/reference/minio-mc/mc-mv/"
weight: 250
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-mv.rst
upstream_modified: false
---

<a id="mc-mv"></a>

<a id="command-mc.mv"></a>

## Syntax {#syntax}

The [`mc mv`](#command-mc.mv) command moves an object from source to the target, such as between MinIO deployments *or* between buckets on the same MinIO deployment. [`mc mv`](#command-mc.mv) also supports moving objects between a local filesystem and MinIO.

You can also use [`mc mv`](#command-mc.mv) against the local filesystem to produce similar results to the `mv` commandline tool.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command moves objects from the `mydata` bucket to the `archive` bucket on the `myminio` MinIO deployment:

```shell
mc mv --recursive myminio/mydata myminio/archive
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] mv         \
[--attr "string"]           \
[--disable-multipart]       \
[--enc-kms "string"]        \
[--enc-s3 "string"]         \
[--enc-c "string"]          \
[--limit-download string]   \
[--limit-upload string]     \
[--newer-than "string"]     \
[--older-than "string"]     \
[--preserve]                \
[--recursive]               \
[--storage-class "string"]  \
SOURCE [SOURCE...]          \
TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `SOURCE` {#mc.mv.SOURCE}

*mc-cmd*

##### `:required:` {#mc.mv.-required}

*mc-cmd*

The object or objects to move.

> For moving an object from a MinIO bucket, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and the full path to the object(s) (e.g. bucket and path to objects). For example:
>
> ```shell
> mc mv play/mybucket/object.txt play/myotherbucket/object.txt
> ```
>
> For moving an object from a local filesystem, specify the full path to that object. For example:
>
> ```shell
> mc mv ~/mydata/object.txt play/mybucket/object.txt
> ```
>
> Specify multiple `SOURCE` paths to move multiple objects to the specified [`TARGET`](#mc.mv.TARGET). [`mc rm`](/reference/minio-mc/mc-rm/#command-mc.rm) treats the *last* specified alias or filesystem path as the `TARGET`. For example:
>
> ```shell
> mc mv ~/mydata/object.txt play/mydata/otherobject.txt myminio/mydata
> ```
>
> If you specify a directory or bucket to [`SOURCE`](#mc.mv.SOURCE), you must also specify [`--recursive`](#mc.mv.-recursive) to recursively move the contents of that directory. If you omit the [`--recursive`](#mc.mv.-recursive) argument, [`mv`](#command-mc.mv) only moves objects in the top level of the specified directory or bucket.

##### `TARGET` {#mc.mv.TARGET}

*mc-cmd*

*Required*

The full path to the bucket to which the command moves the object(s) at the specified [`SOURCE`](#mc.mv.SOURCE). Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of a configured S3 service as the prefix to the [`TARGET`](#mc.mv.TARGET) path.

For moving an object from MinIO, specify the [alias](/reference/minio-mc/mc-alias-set/#alias) and hte full path to the object(s) (e.g. bucket and path to objects). For example:

```shell
mc mv play/mybucket/object.txt play/myotherbucket/object.txt
```

For moving an object from a local filesystem, specify the full path to that object. For example:

```shell
mc mv ~/mydata/object.txt play/mybucket/object.txt
```

The `TARGET` object name can differ from the `SOURCE` to “rename” the object as part of the move operation.

If running [`mc mv`](#command-mc.mv) with the [`--recursive`](#mc.mv.-recursive) option, [`mc mv`](#command-mc.mv) treats the `TARGET` as the bucket prefix for all objects at the `SOURCE`.

##### `--attr` {#mc.mv.-attr}

*mc-cmd*

*Optional*

Add custom metadata for the object. Specify key-value pairs as `KEY=VALUE\;`. For example, `--attr key1=value1\;key2=value2\;key3=value3`.

##### `--disable-multipart` {#mc.mv.-disable-multipart}

*mc-cmd*

*Optional*

Disables the multipart upload feature.

Multipart upload breaks an object into a set of separate parts. Each part uploads individually and in any order. If any individual part upload fails, MinIO retries that part without affecting the other parts. After upload completes, the parts combine to restore the original object.

MinIO recommends using multipart upload for any object larger than 100 MB. For more information on multipart upload, refer to the [Amazon S3 documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html)

##### `--enc-kms` {#mc.mv.-enc-kms}

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

##### `--enc-s3` {#mc.mv.-enc-s3}

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

##### `--enc-c` {#mc.mv.-enc-c}

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

> [!NOTE]
> **Note**
>
> MinIO strongly recommends against using SSE-C encryption in production workloads. Use SSE-KMS via the `--enc-kms` or SSE-S3 via `--enc-s3` parameters instead.

##### `--limit-download` {#mc.mv.-limit-download}

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

```text
--limit-download 1G
```

If not specified, MinIO uses an unlimited download rate.

##### `--limit-upload` {#mc.mv.-limit-upload}

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

```text
--limit-upload 1G
```

If not specified, MinIO uses an unlimited upload rate.

##### `--newer-than` {#mc.mv.-newer-than}

*mc-cmd*

*Optional*

Remove object(s) newer than the specified number of days. Specify a string in `##d#hh#mm#ss` format. For example: `--newer-than 1d2hh3mm4ss`.

Defaults to `0` (all objects).

##### `--older-than` {#mc.mv.-older-than}

*mc-cmd*

*Optional*

Remove object(s) older than the specified time limit. Specify a string in `#d#hh#mm#ss` format. For example: `--older-than 1d2hh3mm4ss`.

Defaults to `0` (all objects).

##### `--preserve, a` {#mc.mv.-preserve}

*mc-cmd*

*Optional*

Preserve file system attributes and bucket policy rules of the [`SOURCE`](#mc.mv.SOURCE) directories, buckets, and objects on the [`TARGET`](#mc.mv.TARGET) bucket(s).

##### `--recursive, r` {#mc.mv.-recursive}

*mc-cmd*

*Optional*

Recursively move the contents of each bucket or directory [`SOURCE`](#mc.mv.SOURCE) to the [`TARGET`](#mc.mv.TARGET) bucket.

##### `--storage-class` {#mc.mv.-storage-class}

*mc-cmd*

*Optional*

Set the storage class for the new object(s) on the [`TARGET`](#mc.mv.TARGET).

See the Amazon documentation on [Storage Classes](https://docs.aws.amazon.com/AmazonS3/latest/dev/storage-class-intro.html) for more information on S3 storage classses.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Move Files from Filesystem to S3-Compatible Host {#move-files-from-filesystem-to-s3-compatible-host}

```shell
mc mv [--recursive] FILEPATH ALIAS/PATH
```

- Replace [`FILEPATH`](#mc.mv.SOURCE) with the full file path to the file to move.

  If specifying the path to a directory, include the [`--recursive`](#mc.mv.-recursive) flag.

  [`mc mv`](#command-mc.mv) *removes* the files from the source after successfully moving it to the destination.
- Replace [`ALIAS`](#mc.mv.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.mv.TARGET) with the destination bucket.

### Move a File from Filesystem to S3-Compatible Host with Custom Metadata {#move-a-file-from-filesystem-to-s3-compatible-host-with-custom-metadata}

Use [`mc mv`](#command-mc.mv) with the [`--attr`](#mc.mv.-attr) option to set custom attributes on file(s).

```shell
mc mv --attr "ATTRIBUTES" FILEPATH ALIAS/PATH
```

- Replace [`FILEPATH`](#mc.mv.SOURCE) with the full file path to the file to move. [`mc mv`](#command-mc.mv) *removes* the file from the source after successfully moving it to the destination.
- Replace [`ALIAS`](#mc.mv.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.mv.TARGET) with the destination bucket.
- Replace [`ATTRIBUTES`](#mc.mv.-attr) with one or more comma-separated key-value pairs `KEY=VALUE`. Each pair represents one attribute key and value.

### Move Bucket Between S3-Compatible Services {#move-bucket-between-s3-compatible-services}

```shell
 mc mv --recursive SRCALIAS/SRCPATH TGTALIAS/TGTPATH
```

- Replace [`SRCALIAS`](#mc.mv.SOURCE) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`SRCPATH`](#mc.mv.SOURCE) with the path to the bucket. [`mc mv`](#command-mc.mv) *removes* the bucket and its contents from the source after successfully moving it to the destination.
- Replace [`TGTALIAS`](#mc.mv.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`TGTPATH`](#mc.mv.TARGET) with the path to the bucket.

### Move File to S3-Compatible Host with Specific Storage Class {#move-file-to-s3-compatible-host-with-specific-storage-class}

Use [`mc mv`](#command-mc.mv) with the [`--storage-class`](#mc.mv.-storage-class) option to set the storage class on the destination S3-compatible host.

```shell
mc mv --storage-class CLASS FILEPATH ALIAS/PATH
```

- Replace [`CLASS`](#mc.mv.-storage-class) with the storage class to associate to the files.
- Replace [`FILEPATH`](#mc.mv.SOURCE) with the full file path to the file to move. [`mc mv`](#command-mc.mv) *removes* the file from the source after successfully moving it to the destination.
- Replace [`ALIAS`](#mc.mv.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured S3-compatible host.
- Replace [`PATH`](#mc.mv.TARGET) with the destination bucket.
- Replace [`ATTRIBUTES`](#mc.mv.-attr) with one or more comma-separated key-value pairs `KEY=VALUE`. Each pair represents one attribute key and value.

  > mc mv –storage-class REDUCED_REDUNDANCY myobject.txt play/mybucket

## Behavior {#behavior}

### Object Names on Move {#object-names-on-move}

MinIO uses the [`SOURCE`](#mc.mv.SOURCE) object name when moving the object to the [`TARGET`](#mc.mv.TARGET) if no explicit target object name is specified.

You can specify a different object name for the [`TARGET`](#mc.mv.TARGET) with the same object path to “rename” an object. For example:

```shell
mc mv play/mybucket/object.txt play/mybucket/myobject.txt
```

For recursive move operations ([`mc mv --recursive`](#mc.mv.-recursive)), MinIO treats the `TARGET` path as a prefix for objects on the `SOURCE`.

### Checksum Verification {#checksum-verification}

[`mc mv`](#command-mc.mv) verifies all move operations to object storage using MD5SUM checksums.

### MinIO Trims Empty Prefixes on Object Removal {#minio-trims-empty-prefixes-on-object-removal}

[`mc mv`](#command-mc.mv) relies on the [`mc`](/reference/minio-mc/#command-mc) removal API for deleting objects. As part of removing the last object in a bucket prefix, [`mc`](/reference/minio-mc/#command-mc) also recursively removes each empty part of the prefix up to the bucket root. [`mc`](/reference/minio-mc/#command-mc) only applies the recursive removal to prefixes created *implicitly* as part of object write operations - that is, the prefix was not created using an explicit directory creation command such as [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb).

For example, consider a bucket `photos` with the following object prefixes:

- `photos/2021/january/myphoto.jpg`
- `photos/2021/february/myotherphoto.jpg`
- `photos/NYE21/NewYears.jpg`

`photos/NYE21` is the *only* prefix explicitly created using [`mc mb`](/reference/minio-mc/mc-mb/#command-mc.mb). All other prefixes were *implicitly* created as part of writing the object located at that prefix.

If an [`mc`](/reference/minio-mc/#command-mc) command removes `myphoto.jpg`, the removal API automatically trims the empty `/january` prefix. If a subsequent [`mc`](/reference/minio-mc/#command-mc) command removes `myotherphoto.jpg`, the removal API automatically trims both the `/february` prefix *and* the now-empty `/2021` prefix. If an [`mc`](/reference/minio-mc/#command-mc) command removes `NewYears.jpg`, the `/NYE21` prefix remains in place since it was *explicitly* created.

If using [`mc mv`](#command-mc.mv) for operations on a filesystem, [`mc`](/reference/minio-mc/#command-mc) applies this same behavior by recursively trimming empty directory paths up to the root. However, the [`mc`](/reference/minio-mc/#command-mc) remove API cannot distinguish between an explicitly created directory path and an implicitly created one. If [`mc mv`](#command-mc.mv) deletes the last object at a filesystem path, [`mc`](/reference/minio-mc/#command-mc) recursively deletes all empty directories within that path up to the root as part of the removal operation.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
