---
title: "mc get"
url: "/reference/minio-mc/mc-get/"
weight: 120
minio_origin: true
silo_modified: false
---

<a id="mc-get"></a>

<a id="command-mc.get"></a>

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-02-24T01-33-20Z
{{% /alert %}}

## Syntax {#syntax}

The [`mc get`](#command-mc.get) command downloads an object from a target S3 deployment to the local file system.

`mc get` provides a simplified interface for downloading files compared to [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) or [`mc mirror`](/reference/minio-mc/mc-mirror/#command-mc.mirror). `mc get` uses a one-way download function that trades efficiency for the power and complexity of the other commands.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following downloads the file `logo.png` from an s3 source to the local file system at path `~/images/collateral/`.

```shell
mc get minio/marketing/logo.png ~/images/collateral
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] get                      \
                 SOURCE                   \
                 TARGET                   \
                 [--enc-c string]         \
                 [--version-id, --vid value]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `SOURCE` {#mc.get.SOURCE}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias), bucket, prefix (if used), and object to download.

##### `TARGET` {#mc.get.TARGET}

*mc-cmd*

*Required*

The destination path on the local file system where the command should place the downloaded file.

##### `--enc-c` {#mc.get.-enc-c}

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

##### `--version-id, --vid` {#mc.get.-version-id}

*mc-cmd*

*Optional*

Retrieve a specific version of the object. Pass the version ID of the object to retrieve.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Retrieve an object from MinIO to the local file system {#retrieve-an-object-from-minio-to-the-local-file-system}

The following command retrieves the file `myobject.csv` from the bucket `mybucket` at the alias `myminio` and places it on the local file system at the path `/my/local/folder`.

```shell
mc get myminio/mybucket/myobject.csv /my/local/folder
```

### Retrieve an encrypted object from MinIO {#retrieve-an-encrypted-object-from-minio}

The following command retrieves an encrypted file and places it at a local folder path.

```shell
mc get --enc-c "play/mybucket/object=MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTIzNDU2Nzg5MDA" play/mybucket/object path-to/object
```
