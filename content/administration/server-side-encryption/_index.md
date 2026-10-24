---
title: "Server-Side Encryption of Objects"
url: "/administration/server-side-encryption/"
weight: 150
icon: fa-solid fa-key
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption.rst
upstream_modified: true
---

<a id="server-side-encryption-of-objects"></a>
<a id="minio-encryption-overview"></a>
<a id="minio-sse"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [PGSTY KES](https://github.com/pgsty/kes) and an external Key Management Service (KMS) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

SILO implements the S3 encryption request interfaces described in [AWS Server-Side Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/server-side-encryption.html) and supports the following encryption strategies:

{{< tabs group="sse-kms-recommended-sse-s3-sse-c" >}}
{{< tab label="SSE-KMS Recommended" value="sse-kms-recommended" >}}
MinIO supports enabling automatic SSE-KMS encryption of all objects written to a bucket using a specific External Key (EK) stored on the external <abbr title="Key Management System">KMS</abbr>. Clients can override the bucket-default <abbr title="External Key">EK</abbr> by specifying an explicit key as part of the write operation.

For buckets without automatic SSE-KMS encryption, clients can specify an <abbr title="External Key">EK</abbr> as part of the write operation instead.

SILO can encrypt backend IAM/configuration data through the configured KMS. You can clear a bucket default with `mcli encrypt clear`, but existing encrypted data still requires its original keys. Do not remove the key service while that data depends on it.

SSE-KMS provides more granular and customizable encryption compared to SSE-S3 and SSE-C and is recommended over the other supported encryption methods.

For a tutorial on enabling SSE-KMS in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-quickstart). For persistent deployments, use [PGSTY KES with OpenBao](/operations/server-side-encryption/configure-minio-kes/). These archived upstream guides cover other inherited backends and are not a certification of those services:

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{< /tab >}}
{{< tab label="SSE-S3" value="sse-s3" >}}
MinIO supports enabling automatic SSE-S3 encryption of all objects written to a bucket using an <abbr title="External Key">EK</abbr> stored on the external <abbr title="Key Management System">KMS</abbr>. MinIO SSE-S3 supports *one* <abbr title="External Key">EK</abbr> for the entire deployment.

For buckets without automatic SSE-S3 encryption, clients can request SSE encryption as part of the write operation instead.

SILO can encrypt backend IAM/configuration data through the configured KMS. You can clear a bucket default with `mcli encrypt clear`, but existing encrypted data still requires its original keys. Do not remove the key service while that data depends on it.

For a tutorial on enabling SSE-s3 in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-quickstart). For persistent deployments, use [PGSTY KES with OpenBao](/operations/server-side-encryption/configure-minio-kes/). These archived upstream guides cover other inherited backends and are not a certification of those services:

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{< /tab >}}
{{< tab label="SSE-C" value="sse-c" >}}
Clients specify an <abbr title="External Key">EK</abbr> as part of the write operation for an object. SILO uses the client-supplied key for SSE-C. SSE-C does not require KES or a server-side KMS.

SSE-C does not support bucket-default encryption settings and requires clients perform all key management operations.
{{< /tab >}}
{{< /tabs >}}

MinIO SSE requires enabling [Network Encryption (TLS)](/operations/network-encryption/#minio-tls).

<a id="minio-encryption-sse-secure-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

KES and SILO can cache key material. Sealing a key store or revoking access is not guaranteed to invalidate cached keys immediately; account for cache expiry and active processes when testing revocation.

SSE-KMS and SSE-S3 objects require the external key (EK) recorded in their metadata. Key availability affects access as follows:

- Sealing the key store or disabling access to an EK prevents decryption only once usable cached key material is also unavailable. Verify revocation across all SILO and KES instances; sealing the backend alone is not proof that reads have stopped.
- Permanently losing every usable copy of an EK, including cached copies and backups, makes objects that still depend on it unrecoverable.

Preserve the original keys until all required object versions have been migrated and their decryption verified.

For more information, see:

- [SSE-KMS Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-erasure-locking)
- [SSE-S3 Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-erasure-locking)
- [SSE-C Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-c/#minio-encryption-sse-c-erasure-locking)

## Cryptographic Construction {#cryptographic-construction}

The following facts describe the construction shared by the SSE schemes. They
are audit-level reference material: not necessary for configuring or using
SSE, but useful when reviewing what is actually stored and in what form. The
description originates from the encryption design notes inherited from
upstream MinIO and retained by Silo.

- Object content is en/decrypted with an authenticated encryption scheme
  (AEAD) organized as a *Secure Channel*: the plaintext is split into
  fixed-size chunks, and each chunk is sealed separately with a unique
  key-nonce combination. The last chunk may be smaller and is treated
  specially to prevent truncation attacks.
- For multi-part objects, each part is sealed with its own key derived from
  the Object Encryption Key (OEK) and the part number through a PRF — so the
  OEK itself is never used directly as a part key.
- The PRF is HMAC-SHA-256. The pinned `sio` implementation prefers
  AES-256-GCM when hardware acceleration is available (including supported
  x86 and ARM64 CPUs), and ChaCha20-Poly1305 otherwise.
- Object encryption keys are 256 bits. The content-encryption format uses
  96-bit nonces; the separate key-sealing metadata carries a 256-bit IV.
  These are different fields and must not be confused.
- The chunk size is 65536 bytes, which bounds a single encrypted object or
  part at `65536 * 2^32 = 256 TiB` of plaintext at the cryptographic-format
  level. This is not the supported S3 object or multipart-part size limit.
- Object-key derivation and key-sealing IV generation use `crypto/rand`;
  `sio` also defaults to that cryptographically secure random source.
  Neither keys nor nonces should be replaced with merely unique counters.
