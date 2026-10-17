---
title: "Server-Side Encryption with Client-Managed Keys (SSE-C)"
url: "/administration/server-side-encryption/server-side-encryption-sse-c/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption/server-side-encryption-sse-c.rst
upstream_modified: true
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

> [!NOTE]
> **Changed: Server**
>
> RELEASE.2024-03-30T09-41-56Z
>
> Objects encrypted with SSE-C can replicate through both site replication or bucket replication. Previous versions of MinIO Object Store did not replicate SSE-C encrypted objects.

Published Server 20260903 retains the inherited limitation for compressed SSE-C replicas. Server 20260916, after [#126](https://github.com/pgsty/silo/pull/126), excludes **all new SSE-C writes from compression**, including PUT, multipart, COPY and Snowball. This is independent of the encrypted-compression setting for SSE-S3/SSE-KMS. It prevents new compressed SSE-C objects; it does not rewrite historical objects. Inventory old compressed SSE-C data and verify recovery or replication with the original keys before depending on it. See [SSE-C replica integrity](/blog/design/ssec-replica-integrity/) and the [release matrix](/compatibility/versions/).

### SSE-C Overrides SSE-S3 and SSE-KMS {#sse-c-overrides-sse-s3-and-sse-kms}

Encrypting an object using SSE-C prevents MinIO from applying [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) or [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3) encryption to that object.

## Quickstart {#quickstart}

MinIO SSE-C requires the client to perform all key creation and storage operations.

This procedure uses [`mc`](/reference/minio-mc/#command-mc) for performing operations on the source MinIO deployment. Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to the source deployment. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.

The SSE-C key *must* be a 256-bit raw encoded string or a hex encoded string. The client application is responsible for generation and storage of the encryption key. MinIO does *not* store SSE-C encryption keys and cannot decrypt SSE-C encrypted objects without the client-managed key.

> [!NOTE]
> **Note**
>
> Support for hex encoded keys was added in MinIO Client `RELEASE.2024-06-20T14-50-54Z`.

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

The MinIO [`mc`](/reference/minio-mc/#command-mc) commandline tool S3-compatible SDKs include specific syntax for setting headers. Certain [`mc`](/reference/minio-mc/#command-mc) commands like [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) include specific arguments for enabling SSE-C encryption:

```shell
mc cp ~/data/mydata.json ALIAS/BUCKET/mydata.json \
   --encrypt-key "ALIAS/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo="
```

- Replace [`ALIAS`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment on which you want to write the SSE-C encrypted object.
- Replace [`BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the full path to the bucket or bucket prefix to which you want to write the SSE-C encrypted object.

### 3) Copy an SSE-C Encrypted Object {#copy-an-sse-c-encrypted-object}

MinIO supports the following AWS S3 headers for copying an SSE-C encrypted object to another S3-compatible service:

- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Algorithm` set to `AES256`
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key` set to the encryption key value. The copy operation will fail if the specified key does not match the key used to SSE-C encrypt the object.
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key-MD5` set to the 128-bit MD5 digest of the encryption key.

When source and destination use different SSE-C keys, provide both header sets: the `Copy-Source-*` headers identify the source key, while the ordinary `Server-Side-Encryption-Customer-*` headers identify the destination key. SILO keeps these contexts separate after commit, so CopyObject checksum fields in XML and HTTP headers are decrypted with the destination key. See [Two SSE-C Keys, One CopyObject Response](/blog/design/copyobject-ssec-checksum-response/).

The MinIO [`mc`](/reference/minio-mc/#command-mc) commandline tool S3-compatible SDKs include specific syntax for setting headers. Certain [`mc`](/reference/minio-mc/#command-mc) commands like [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) include specific arguments for enabling SSE-C encryption:

```shell
mc cp SOURCE/BUCKET/mydata.json TARGET/BUCKET/mydata.json  \
--encrypt-key "SOURCE/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo=,TARGET/BUCKET/=c2VjcmV0ZW5jcnlwdGlvbmtleWNoYW5nZW1lMTIzNAo="
```

- Replace [`SOURCE/BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment from which you are reading the encrypted object and the full path to the bucket or bucket prefix from which you want to read the SSE-C encrypted object.
- Replace [`TARGET/BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment to which you are writing the encrypted object and the full path to the bucket or bucket prefix to which you want to write the SSE-C encrypted object.

### 4) Rotate the SSE-C Key of an Object {#rotate-the-sse-c-key-of-an-object}

An S3 client can change the client-provided key of an existing object without
re-uploading it: issue an S3 COPY operation where the copy source and the copy
destination are the same object, and provide both keys in the request headers:

- `X-Amz-Server-Side-Encryption-Customer-Key`: Base64-encoded **new** key (the
  key the object will have after the operation).
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key`: Base64-encoded
  **current** key (the key the object is encrypted with now).

Also supply the matching `Customer-Algorithm: AES256` and `Customer-Key-MD5`
headers for both source and destination, normally through an S3 SDK.

This self-COPY is known as SSE-C key rotation. When the metadata-only path is
eligible, the server unwraps the object encryption key with the old customer
key and rewraps it with the new one; stored object bytes are not rewritten.
Copies that require new object data (for example, some versioning or checksum
changes) use the regular decrypt-and-re-encrypt path instead. Client-provided
keys are not persisted in object metadata. Normal COPY permissions and
versioning behavior still apply; this is not a general in-place version editor.

In Server 20260916, [#123](https://github.com/pgsty/silo/pull/123) sends an ordinary client self-COPY with **any requested checksum algorithm** through the full decrypt-and-re-encrypt path, even when it names the stored algorithm. That rewrite can change the ETag, produces a single-part object from a multipart source, and replicates full object data rather than a metadata-only update. Without that header, an eligible in-place rotation preserves the existing checksum state, including the absence of a checksum. Versioning and legacy-format constraints can independently require a rewrite.
