---
title: "mc ilm restore"
url: "/reference/minio-mc/mc-ilm-restore/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-ilm-restore.rst
upstream_modified: false
---

<a id="mc-ilm-restore"></a>
<a id="minio-mc-ilm-restore"></a>

<a id="command-mc.ilm.restore"></a>

## Syntax {#syntax}

The [`mc ilm restore`](#command-mc.ilm.restore) command creates a temporary copy of an object archived on a remote tier. The copy automatically expires after 1 day by default.

Use this command to allow applications to access a tiered object through the MinIO deployment (e.g. “hot tier”). The archived object remains on the remote tier, while the temporary copy becomes `HEAD` for that object.

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-04-12T02-21-51Z
>
> Use [`mc stat`](/reference/minio-mc/mc-stat/#command-mc.stat) to display whether a restored object reads from the local temporary copy or the remote tier. Objects currently in the process of restoration from the remote tier show a status of `Ongoing : true`.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command restores a copy of a transitioned object from the remote tier back to the `myminio` MinIO deployment:

```shell
mc ilm restore myminio/mybucket/object.txt
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] ilm restore         \
                 [--days "int" ]     \
                 [--recursive]       \
                 [--vid "string"]    \
                 [--versions]        \
                 [--enc-c "string"]  \
                 ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.ilm.restore.ALIAS}

*mc-cmd*

*Required*

The MinIO [alias](/reference/minio-mc/mc-alias-set/#alias), bucket, and path to the archived object to restore.

```shell
mc ilm restore myminio/mybucket/object.txt
```

##### `--days` {#mc.ilm.restore.-days}

*mc-cmd*

*Optional*

The number of days after which MinIO expires the restored copy of the archived object.

##### `--enc-c` {#mc.ilm.restore.-enc-c}

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

##### `--recursive, r` {#mc.ilm.restore.-recursive}

*mc-cmd*

*Optional*

Restores all objects under the specified prefix.

##### `--versions` {#mc.ilm.restore.-versions}

*mc-cmd*

*Optional*

Restores all versions of the object on the remote tier.

##### `--version-id, vid` {#mc.ilm.restore.-version-id}

*mc-cmd*

*Optional*

Restores the specified version of the object on the remote tier.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Restore an Archived Object {#restore-an-archived-object}

The following command restores an object archived to a remote tier:

```shell
mc ilm restore myminio/mybucket/object.txt
```

### Restore a Specific Archived Object Version {#restore-a-specific-archived-object-version}

The following command restore a specific object version archived to a remote tier:

```shell
mc ilm restore --vid "VERSIONID" myminio/mybucket/object.txt
```

### Restore All Archived Objects at a Bucket Prefix {#restore-all-archived-objects-at-a-bucket-prefix}

The following command restores all objects archived under a specified prefix on the remote tier:

```shell
mc ilm restore --recursive myminio/mybucket/data/
```

## Behavior {#behavior}

### Restored Objects Expire Automatically {#restored-objects-expire-automatically}

MinIO automatically expires the restored object copy after the specified number of days (Default: 1 day).

### Restored Objects Become HEAD {#restored-objects-become-head}

The restored object copy becomes HEAD for that object namespace *regardless* of it’s versioning history. This can result in applications returning “stale” data while the local copy exists.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
