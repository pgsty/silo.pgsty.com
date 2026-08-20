---
title: "mc put"
url: "/reference/minio-mc/mc-put/"
weight: 290
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-put.rst
upstream_modified: false
---

<a id="mc-put"></a>

<a id="command-mc.put"></a>

> [!NOTE]
> **Added: mc**
>
> RELEASE.2024-02-24T01-33-20Z

## Syntax {#syntax}

The [`mc put`](#command-mc.put) uploads an object from the local file system to a bucket on a target S3 deployment.

`mc put` provides a simplified interface for uploading files compared to [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) or [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror). `mc put` uses a one-way upload function that trades efficiency for the power and complexity of the other commands.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following uploads the file `logo.png` from the local file system at path `~/images/collateral/` to a bucket called `marketing` on the MinIO deployment with the alias of `minio`.

```shell
mc put ~/images/collateral/logo.png minio/marketing
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] put                            \
                 TARGET                         \
                 [--checksum value]             \
                 [--disable-multipart]          \
                 [--enc-kms value]              \
                 [--enc-s3 value]               \
                 [--enc-c value]                \
                 [--if-not-exists]              \
                 [--parallel, -P integer]       \
                 [--part-size, -s string]       \
                 [--storage-class, -sc string]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.put.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or prefix where the command should run. The TARGET *must* contain an [alias](/reference/minio-mc/mc-alias-set/#alias) and `bucket` name.

The TARGET may also contain the following optional components: - PREFIX where the object should upload to - OBJECT-NAME to use in place of the file names

Valid TARGETs could take any of the following forms: - `ALIAS/BUCKET` - `ALIAS/BUCKET/PREFIX` - `ALIAS/BUCKET/OBJECT-NAME` - `ALIAS/BUCKET/PREFIX/OBJECT-NAME`

##### `--checksum` {#mc.put.-checksum}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2024-10-02T08-27-28Z**

Add a checksum to an uploaded object.

Valid values are: - `MD5` - `CRC32` - `CRC32C` - `SHA1` - `SHA256`

The flag requires server trailing headers and works with AWS or MinIO targets.

##### `--disable-multipart` {#mc.put.-disable-multipart}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2024-10-02T08-27-28Z**

Disables multipart uploads and directs `mc` to send the object in a single `PUT` operation.

##### `--enc-kms` {#mc.put.-enc-kms}

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

##### `--enc-s3` {#mc.put.-enc-s3}

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

##### `--enc-c` {#mc.put.-enc-c}

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

##### `--parallel, --P` {#mc.put.-parallel}

*mc-cmd*

*Optional*

For multi-part uploads, specify the number of parts of the object to upload in parallel.

If not defined, defaults to a value of `4`.

##### `--part-size, -s` {#mc.put.-part-size}

*mc-cmd*

*Optional*

Specify the size to use for each part of a multi-part upload.

If not defined, defaults to a value of `16MiB`.

##### `--storage-class, -sc` {#mc.put.-storage-class}

*mc-cmd*

*Optional*

Set the storage class for the uploaded object.

See [Standard Storage Class](/reference/minio-server/settings/storage-class/#minio-ec-storage-class-standard) for more about storage classes.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Upload a File and Specify the Object Name {#upload-a-file-and-specify-the-object-name}

The following command uploads the file `logo.png` from the local file system to the `business` bucket on the `minio` deployment, uploading it on the destination as `company-logo.png`.

```shell
mc put images/collateral/logo.png minio/business/company-logo.png
```

### Upload a Multipart Object in Parallel with a Specified Part Size {#upload-a-multipart-object-in-parallel-with-a-specified-part-size}

The following command uploads a file in chunks of 20MiB each and uploads 8 parts of the file in parallel. 8 parts are uploaded in succession until all parts of the object have uploaded.

```shell
mc put ~/videos/collateral/splash-page.mp4 minio/business --parallel 8 --part-size 20MiB
```
