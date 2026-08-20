---
title: "mc pipe"
url: "/reference/minio-mc/mc-pipe/"
weight: 280
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-pipe.rst
upstream_modified: false
---

<a id="mc-pipe"></a>

<a id="command-mc.pipe"></a>

## Syntax {#syntax}

The [`mc pipe`](#command-mc.pipe) command streams content from [STDIN](https://www.gnu.org/software/libc/manual/html_node/Standard-Streams.html) to a target object.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command writes contents of `STDIN` to an S3 compatible storage.

```shell
echo "My Meeting Notes" | mc pipe s3/engineering/meeting-notes.txt
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] pipe                              \
                 TARGET                            \
                 [--attr "string"]                 \
                 [--checksum "string"]             \
                 [--enc-kms "string"]              \
                 [--enc-s3 "string"]               \
                 [--enc-c "string"]                \
                 [--storage-class, --sc "string"]  \
                 [--tags "string"]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

> [!NOTE]
> **Changed: RELEASE.2023-01-11T03-14-16Z**
>
> `mc pipe` now supports concurrent uploads for better throughput of large streams.

### Parameters {#parameters}

##### `TARGET` {#mc.pipe.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or prefix where the command should run.

##### `--attr` {#mc.pipe.-attr}

*mc-cmd*

*Optional*

Add custom metadata for the object.

Specify key-value pairs as `KEY=VALUE\;`, separating each pair with a back slash and semicolon (`\;`). For example, `--attr key1=value1\;key2=value2\;key3=value3`.

##### `--checksum` {#mc.pipe.-checksum}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2024-10-02T08-27-28Z**

Add a checksum to an uploaded object.

Valid values are: - `MD5` - `CRC32` - `CRC32C` - `SHA1` - `SHA256`

The flag requires server trailing headers and works with AWS or MinIO targets.

##### `--enc-kms` {#mc.pipe.-enc-kms}

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

##### `--enc-s3` {#mc.pipe.-enc-s3}

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

##### `--enc-c` {#mc.pipe.-enc-c}

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

##### `--storage-class, --sc` {#mc.pipe.-storage-class}

*mc-cmd*

*Optional*

Set the storage class for the new object at the [`TARGET`](#mc.pipe.TARGET).

See [Amazons documentation](https://docs.aws.amazon.com/AmazonS3/latest/dev/storage-class-intro.html) for more information on S3 storage classes.

##### `--tags` {#mc.pipe.-tags}

*mc-cmd*

*Optional*

Applies one or more tags to the TARGET.

Specify an ampersand-separated list of key-value pairs as `KEY1=VALUE1&KEY2=VALUE2`, where each pair represents one tag to assign to the objects.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Write Contents of `STDIN` to the Local Filesystem {#write-contents-of-stdin-to-the-local-filesystem}

The following command writes the contents of STDIN to the `/tmp` folder on the local filesystem.

```shell
mc pipe /tmp/hello-world.go
```

### Copy an ISO Image to S3 Storage {#copy-an-iso-image-to-s3-storage}

The following command first streams the contents of an iso image for Debian and then uses the stream to create the object at an S3 path.

```shell
cat debian-live-11.5.0-amd64-mate.iso | mc pipe s3/opensource-isos/debian-11-5.iso
```

### Stream MySQL Database Dump to S3 {#stream-mysql-database-dump-to-s3}

The following command first streams a MySQL database and uses the stream to create a backup on S3 with [`mc pipe`](#command-mc.pipe):

```shell
mysqldump -u root -p ******* accountsdb | mc pipe s3/sql-backups/backups/accountsdb-sep-28-2022.sql
```

### Write a File to a Reduced Redundancy Storage Class {#write-a-file-to-a-reduced-redundancy-storage-class}

The following command takes the STDIN stream and creates an object on the Reduced Redundancy storage class on S3.

```shell
 mc pipe --storage-class REDUCED_REDUNDANCY s3/personalbuck/meeting-notes.txt
```

### Copy a File to a MinIO Deployment with Metadata {#copy-a-file-to-a-minio-deployment-with-metadata}

The following command uploads an MP3 file to a MinIO deployment with an ALIAS of `myminio` and a `music` bucket. The object writes with some metadata for `Cache-Control` and `Artist`.

```shell
cat music.mp3 | mc pipe --attr "Cache-Control=max-age=90000,min-fresh=9000;Artist=Unknown" myminio/music/guitar.mp3
```

### Set Tags on Uploaded Objects {#set-tags-on-uploaded-objects}

The following command creates an object on a MinIO deployment with an ALIAS of `myminio` in bucket `mybucket` with two tags. MinIO supports adding up to 10 custom tags to an object.

```shell
tar cvf - . | mc pipe --tags "category=prod&type=backup" myminio/mybucket/backup.tar
```
