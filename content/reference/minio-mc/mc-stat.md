---
title: "mc stat"
url: "/reference/minio-mc/mc-stat/"
weight: 370
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-stat.rst
upstream_modified: false
---

<a id="mc-stat"></a>

<a id="command-mc.stat"></a>

## Syntax {#syntax}

The [`mc stat`](#command-mc.stat) command displays information on objects in a MinIO bucket, including object metadata. You can also use it to retrieve bucket metadata.

You can use [`mc stat`](#command-mc.stat) against the local filesystem to produce similar results to the `stat` commandline tool.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays information on all objects in the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc stat --recursive myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] stat                      \
                 [--enc-c "value"]         \
                 [--no-list]               \
                 [--recursive]             \
                 [--rewind "string"]       \
                 [--versions]              \
                 [--version-id "string"]*  \
                 ALIAS [ALIAS ...]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.

[`mc stat --version-id`](#mc.stat.-version-id) is mutually exclusive with multiple parameters. See the reference documentation for more information.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.stat.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment and the full path to the object for which to retrieve detailed information. For example:

```shell
mc stat myminio/mybucket/myobject.txt
```

You can specify multiple objects on the same or different MinIO deployments:

```shell
mc stat myminio/mybucket/myobject.txt myminio/mybucket/myobject.txt
```

If specifying the path to a bucket or bucket prefix, you **must** include the [`mc stat --recursive`](#mc.stat.-recursive) flag:

```shell
mc stat --recursive myminio/mybucket/
```

For retrieving information on a file from a local filesystem, specify the full path to that file:

```shell
mc stat ~/data/myobject.txt
```

##### `--enc-c` {#mc.stat.-enc-c}

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

##### `--no-list` {#mc.stat.-no-list}

*mc-cmd*

*Optional*

Disable all `LIST` operations if the target does not exist.

##### `--recursive, r` {#mc.stat.-recursive}

*mc-cmd*

*Optional*

Recursively [`mc stat`](#command-mc.stat) the contents of the MinIO bucket specified to [`ALIAS`](#mc.stat.ALIAS).

##### `--rewind` {#mc.stat.-rewind}

*mc-cmd*

*Optional*

Directs [`mc stat`](#command-mc.stat) to operate only on the object version(s) that existed at specified point-in-time.

- To rewind to a specific date in the past, specify the date as an ISO8601-formatted timestamp. For example: `--rewind "2020.03.24T10:00"`.
- To rewind a duration in time, specify the duration as a string in `#d#hh#mm#ss` format. For example: `--rewind "1d2hh3mm4ss"`.

[`--rewind`](#mc.stat.-rewind) requires that the specified [`ALIAS`](#mc.stat.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

##### `--versions` {#mc.stat.-versions}

*mc-cmd*

*Optional*

Directs [`mc stat`](#command-mc.stat) to operate on all object versions that exist in the bucket.

[`--versions`](#mc.stat.-versions) requires that the specified [`ALIAS`](#mc.stat.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Use [`--versions`](#mc.stat.-versions) and [`--rewind`](#mc.stat.-rewind) together to remove all object versions which existed at a specific point in time.

##### `--version-id, vid` {#mc.stat.-version-id}

*mc-cmd*

*Optional*

Directs [`mc stat`](#command-mc.stat) to operate only on the specified object version.

[`--version-id`](#mc.stat.-version-id) requires that the specified [`ALIAS`](#mc.stat.ALIAS) be an S3-compatible service that supports [Bucket Versioning](/administration/object-management/object-versioning/#minio-bucket-versioning). For MinIO deployments, use [`mc version`](/reference/minio-mc/mc-version/#command-mc.version) to enable or disable bucket versioning.

Mutually exclusive with any of the following flags:

- [`--versions`](#mc.stat.-versions)
- [`--rewind`](#mc.stat.-rewind)
- [`--recursive`](#mc.stat.-recursive)

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display Object Details {#display-object-details}

The following example displays details of the object `myfile.txt` in the bucket `mybucket`:

```shell
mc stat myminio/mybucket/myfile.txt
```

The output resembles the following:

```shell
Name      : myfile.txt
Date      : 2024-07-16 15:40:02 MDT
Size      : 6.0 KiB
ETag      : 3b38f7b05a0c42acdc377e60b2a74ddf
Type      : file
Metadata  :
  Content-Type: text/plain
```

You can specify more than one object by adding multiple paths:

```shell
mc stat myminio/mybucket/file1.txt myminio/yourbucket/file2.txt
```

To display detail for all objects in a bucket, use [`--recursive`](#mc.stat.-recursive). The following example displays details for all objects in bucket `mybucket`:

```shell
mc stat --recursive myminio/mybucket
```

The output resembles the following:

```shell
Name      : file1.txt
Date      : 2024-07-16 15:40:02 MDT
Size      : 6.0 KiB
ETag      : 3b38f7b05a0c42acdc377e60b2a74ddf
Type      : file
Metadata  :
  Content-Type: text/plain

Name      : file2.txt
Date      : 2024-07-26 10:45:19 MDT
Size      : 6.0 KiB
ETag      : 3b38f7b05a0c42acdc377e60b2a74ddf
Type      : file
Metadata  :
  Content-Type: text/plain
```

### Display Bucket Details {#display-bucket-details}

The following example displays information about the bucket `mybucket` on the `myminio` MinIO deployment:

```shell
mc stat myminio/mybucket
```

The output resembles the following:

```shell
Name      : mybucket
Date      : 2024-07-26 10:56:43 MDT
Size      : N/A
Type      : folder

Properties:
  Versioning: Un-versioned
  Location: us-east-1
  Anonymous: Disabled
  ILM: Disabled

Usage:
      Total size: 6.0 KiB
   Objects count: 1
  Versions count: 0

Object sizes histogram:
   1 object(s) BETWEEN_1024B_AND_1_MB
   1 object(s) BETWEEN_1024_B_AND_64_KB
   0 object(s) BETWEEN_10_MB_AND_64_MB
   0 object(s) BETWEEN_128_MB_AND_512_MB
   0 object(s) BETWEEN_1_MB_AND_10_MB
   0 object(s) BETWEEN_256_KB_AND_512_KB
   0 object(s) BETWEEN_512_KB_AND_1_MB
   0 object(s) BETWEEN_64_KB_AND_256_KB
   0 object(s) BETWEEN_64_MB_AND_128_MB
   0 object(s) GREATER_THAN_512_MB
   0 object(s) LESS_THAN_1024_B
```

### Count of Objects in a Bucket {#count-of-objects-in-a-bucket}

To show the number of objects in a bucket, use `--json` and extract the value of `objectsCount` with a JSON parser:

The following example uses the [jq](https://jqlang.github.io/jq/) utility:

```shell
mc stat myminio/mybucket --json | jq '.Usage.objectsCount'
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
