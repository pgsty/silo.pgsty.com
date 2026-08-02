---
title: "mc encrypt clear"
url: "/reference/minio-mc/mc-encrypt-clear/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-encrypt-clear"></a>
<a id="minio-mc-encrypt-clear"></a>

<a id="command-mc.encrypt.clear"></a>

## Syntax {#syntax}

The [`mc encrypt clear`](#command-mc.encrypt.clear) command removes the current default encryption settings for a bucket.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes the default encryption settings for the `mydata` bucket on the MinIO deployment associated with the `myminio` [alias](/reference/minio-mc/mc-alias-set/#alias):

```shell
mc encrypt clear myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] encrypt clear ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.encrypt.clear.ALIAS}

*mc-cmd*

The full path to the bucket on which to remove the default SSE mode. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment as the prefix to the ALIAS path. For example:

```shell
mc encrypt clear play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Remove the Automatic Server-Side Encryption Settings for a Bucket {#remove-the-automatic-server-side-encryption-settings-for-a-bucket}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
```shell
 mc encrypt clear myminio/data
```
{{% /tab %}}
{{% tab header="Syntax" %}}
```shell
mc encrypt clear ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to remove automatic server-side bucket encryption.
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

### Modifying Bucket Encryption Settings Does Not Affect Encrypted Objects {#modifying-bucket-encryption-settings-does-not-affect-encrypted-objects}

Disabling automatic bucket encryption does *not* decrypt any objects in the bucket.

To permanently decrypt objects in the bucket, you can perform an in-place copy after disabling object decryption. For versioned buckets, the previous object versions remain encrypted.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
