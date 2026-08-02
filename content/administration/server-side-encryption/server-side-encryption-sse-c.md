---
title: "Server-Side Encryption with Client-Managed Keys (SSE-C)"
url: "/administration/server-side-encryption/server-side-encryption-sse-c/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="server-side-encryption-with-client-managed-keys-sse-c"></a>
<a id="minio-encryption-sse-c"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

The procedure on this page configures and enables Server-Side Encryption with Client-Managed Keys (SSE-C). MinIO SSE-C supports client-driven encryption of objects *before* writing the object to the drive. Clients must specify the correct key to decrypt objects for read operations.

MinIO SSE-C is functionally compatible with Amazon [Server-Side Encryption with Customer-Provided Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ServerSideEncryptionCustomerKeys.html).

<a id="minio-encryption-sse-c-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

SSE-C protects objects using an <abbr title="External Key">EK</abbr> specified by the client as part of the write operation. Assuming the client-side key management supports disabling or deleting these keys:

- **Disabling the <abbr title="External Key">EK</abbr> temporarily locks any objects encrypted using that**

  > <abbr title="External Key">EK</abbr> by rendering them unreadable. You can later enable the <abbr title="External Key">EK</abbr> to resume normal read operations on those objects.
- **Deleting the <abbr title="External Key">EK</abbr> renders all objects encrypted by that <abbr title="External Key">EK</abbr>**

  > *permanently* unreadable. If the client-side KMS does not support backups of the <abbr title="External Key">EK</abbr>, this process is *irreversible*.

The scope of a single <abbr title="External Key">EK</abbr> depends on the number of write operations which specified that <abbr title="External Key">EK</abbr> when requesting SSE-C encryption.

## Considerations {#considerations}

### SSE-C with Replication {#sse-c-with-replication}

{{% alert color="info" %}}
**Changed: Server**

RELEASE.2024-03-30T09-41-56Z

Objects encrypted with SSE-C can replicate through both site replication or bucket replication. Previous versions of MinIO Object Store did not replicate SSE-C encrypted objects.
{{% /alert %}}

SSE-C encrypted objects that are compressed are not compatible with MinIO [bucket replication](/administration/bucket-replication/#minio-bucket-replication) or [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview). Use [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) or [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3) to ensure encrypted objects are compatible with replication.

### SSE-C Overrides SSE-S3 and SSE-KMS {#sse-c-overrides-sse-s3-and-sse-kms}

Encrypting an object using SSE-C prevents MinIO from applying [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) or [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3) encryption to that object.

## Quickstart {#quickstart}

MinIO SSE-C requires the client to perform all key creation and storage operations.

This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the source MinIO deployment. Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to the source deployment. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

The SSE-C key *must* be a 256-bit raw encoded string or a hex encoded string. The client application is responsible for generation and storage of the encryption key. MinIO does *not* store SSE-C encryption keys and cannot decrypt SSE-C encrypted objects without the client-managed key.

{{% alert color="info" %}}
**Note**

Support for hex encoded keys was added in MinIO Client `RELEASE.2024-06-20T14-50-54Z`.
{{% /alert %}}

### 1) Generate the Encryption Key {#generate-the-encryption-key}

Generate the 256-bit base64 raw encoded string or a hex encoded string for use as the encryption key.

The following example generates a string that meets the encryption key requirements. The resulting string is appropriate for non-production environments:

```shell
cat /dev/urandom | head -c 32 | base64 -
```

Defer to your organizations requirements for generating cryptographically secure encryption keys.

Copy the encryption key for use in the next step.

### 2) Encrypt an Object using SSE-C {#encrypt-an-object-using-sse-c}

MinIO supports the following AWS S3 headers for specifying SSE-C encryption:

- `X-Amz-Server-Side-Encryption-Customer-Algorithm` set to `AES256`.
- `X-Amz-Server-Side-Encryption-Customer-Key` set to the encryption key value.
- `X-Amz-Server-Side-Encryption-Customer-Key-MD5` to the 128-bit MD5 digest of the encryption key.

The MinIO [`mc`](/reference/minio-mc/#command-mc) commandline tool S3-compatible SDKs include specific syntax for setting headers. Certain [`mc`](/reference/minio-mc/#command-mc) commands like [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) include specific arguments for enabling SSE-S3 encryption:

```shell
mc cp ~/data/mydata.json ALIAS/BUCKET/mydata.json \
   --encrypt-key "ALIAS/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo="
```

- Replace [`ALIAS`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment on which you want to write the SSE-C encrypted object.
- Replace [`BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the full path to the bucket or bucket prefix to which you want to write the SSE-C encrypted object.

### 3) Copy an SSE-C Encrypted Object {#copy-an-sse-c-encrypted-object}

MinIO supports the following AWS S3 headers for copying an SSE-C encrypted object to another S3-compatible service:

- `X-Amz-Copy-Source-Server-Side-Encryption-Algorithm` set to `AES256`
- `X-Amz-Copy-Source-Server-Side-Encryption-Key` set to the encryption key value. The copy operation will fail if the specified key does not match the key used to SSE-C encrypt the object.
- `X-Amz-Copy-Source-Server-Side-Encryption-Key-MD5` set to the 128-bit MD5 digest of the encryption key.

The MinIO [`mc`](/reference/minio-mc/#command-mc) commandline tool S3-compatible SDKs include specific syntax for setting headers. Certain [`mc`](/reference/minio-mc/#command-mc) commands like [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) include specific arguments for enabling SSE-S3 encryption:

```shell
mc cp SOURCE/BUCKET/mydata.json TARGET/BUCKET/mydata.json  \
--encrypt-key "SOURCE/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo=,TARGET/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo="
```

- Replace [`SOURCE/BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment from which you are reading the encrypted object and the full path to the bucket or bucket prefix from which you want to read the SSE-C encrypted object.
- Replace [`TARGET/BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment from which you are writing the encrypted object and the full path to the bucket or bucket prefix to which you want to write the SSE-C encrypted object.
