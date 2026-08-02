---
title: "mc encrypt set"
url: "/reference/minio-mc/mc-encrypt-set/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-encrypt-set"></a>
<a id="minio-mc-encrypt-set"></a>

<a id="command-mc.encrypt.set"></a>

## Syntax {#syntax}

The [`mc encrypt set`](#command-mc.encrypt.set) encrypt command sets or updates the default bucket [Server-Side Encryption (SSE) mode](/administration/server-side-encryption/#minio-sse). MinIO automatically encrypts objects written to that bucket using the specified SSE mode.

[`mc encrypt set`](#command-mc.encrypt.set) only supports [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) and [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command sets the default [SSE-KMS encryption key](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) for the bucket `mydata` on the `myminio` MinIO deployment:

```shell
mc encrypt set sse-kms "minio-encryption-key" myminio/mydata
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] encrypt set  ENCRYPTION [KMSKEY] ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ENCRYPTION` {#mc.encrypt.set.ENCRYPTION}

*mc-cmd*

Specify the server-side encryption type to use as the default SSE mode. Supports the following values:

- `sse-kms` - Encrypt objects using the key specified in [`KMSKEY`](#mc.encrypt.set.KMSKEY). MinIO must have access to the specified key on the external KMS to successfully encrypt or decrypt objects protected using SSE-KMS.
- `sse-s3` - Encrypt objects using the key specified to [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME). MinIO must have access to the specified key on the external KMS to successfully encrypt or decrypt objects protected using SSE-S3.

##### `KMSKEY` {#mc.encrypt.set.KMSKEY}

*mc-cmd*

Specify the KMS Master Key to use for performing SSE object encryption. This option only applies if [`ENCRYPTION`](#mc.encrypt.set.ENCRYPTION) is `sse-kms`.

Omit this option to direct MinIO to use the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME).

##### `ALIAS` {#mc.encrypt.set.ALIAS}

*mc-cmd*

The full path to the bucket on which to set the default SSE mode. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment as the prefix to the TARGET path. For example:

```shell
mc encrypt set ENCRYPTION [KMSKEY] play/mybucket
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Enable Automatic Server-Side Bucket Encryption {#enable-automatic-server-side-bucket-encryption}

{{< tabpane text=true persist=header >}}
{{% tab header="Example" %}}
The following commands assumes that:

- The MinIO server configuration supports [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms)
- The root has an encryption key `minio-encryption-key`.

```shell
 mc encrypt set sse-kms minio-encryption-key myminio/data
```
{{% /tab %}}
{{% tab header="Syntax" %}}
```shell
mc encrypt set ENCRYPTION KMSKEY TARGET
```

- Replace `ENCRYPTION` with `sse-kms` or `sse-s3` depending on the preferred encryption mode.
- Replace `KMSKEY` with the name of the encryption key on the configured root KMS. This argument has no effect with `sse-s3`.
- Replace `TARGET` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to configure automatic server-side bucket encryption.
{{% /tab %}}
{{< /tabpane >}}

## Behavior {#behavior}

[`mc encrypt set`](#command-mc.encrypt.set) makes no assumptions about the MinIO server’s current encryption state. Specifying default encryption settings which the server cannot support may result in undesired behavior.

Setting or modifying the default server-side encryption settings does *not* automatically encrypt or decrypt the existing bucket contents. If the bucket contents *must* have consistent encryption, use the [`mc mv`](/reference/minio-mc/mc-mv/#command-mc.mv) command with [`--enc-kms`](/reference/minio-mc/mc-mv/#mc.mv.-enc-kms), [`--enc-s3`](/reference/minio-mc/mc-mv/#mc.mv.-enc-s3), or [`--enc-c`](/reference/minio-mc/mc-mv/#mc.mv.-enc-c) to specify the type of encryption to use for the moved contents. This manually modifies the encryption settings or encrypted state of the bucket contents *before* changing the bucket default.
