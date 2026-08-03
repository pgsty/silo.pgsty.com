---
title: "Server-Side Encryption of Objects"
url: "/administration/server-side-encryption/"
weight: 150
icon: fa-solid fa-key
minio_origin: true
silo_modified: true
---

<a id="server-side-encryption-of-objects"></a>
<a id="minio-encryption-overview"></a>
<a id="minio-sse"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [MinIO Key Encryption Service (KES)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md) and an external Key Management Service (KMS) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO SSE is feature and API compatible with [AWS Server-Side Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/server-side-encryption.html) and supports the following encryption strategies:

{{< tabpane text=true persist=header >}}
{{% tab header="SSE-KMS Recommended" %}}
MinIO supports enabling automatic SSE-KMS encryption of all objects written to a bucket using a specific External Key (EK) stored on the external <abbr title="Key Management System">KMS</abbr>. Clients can override the bucket-default <abbr title="External Key">EK</abbr> by specifying an explicit key as part of the write operation.

For buckets without automatic SSE-KMS encryption, clients can specify an <abbr title="External Key">EK</abbr> as part of the write operation instead.

MinIO encrypts backend data as part of enabling server-side encryption. You cannot disable SSE-KMS encryption once enabled.

SSE-KMS provides more granular and customizable encryption compared to SSE-S3 and SSE-C and is recommended over the other supported encryption methods.

For a tutorial on enabling SSE-KMS in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-quickstart). For production MinIO deployments, use one of the following guides:

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{% /tab %}}
{{% tab header="SSE-S3" %}}
MinIO supports enabling automatic SSE-S3 encryption of all objects written to a bucket using an <abbr title="External Key">EK</abbr> stored on the external <abbr title="Key Management System">KMS</abbr>. MinIO SSE-S3 supports *one* <abbr title="External Key">EK</abbr> for the entire deployment.

For buckets without automatic SSE-S3 encryption, clients can request SSE encryption as part of the write operation instead.

MinIO encrypts backend data as part of enabling server-side encryption. You cannot disable SSE-KMS encryption once enabled.

For a tutorial on enabling SSE-s3 in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-quickstart). For production MinIO deployments, use one of the following guides:

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{% /tab %}}
{{% tab header="SSE-C" %}}
Clients specify an <abbr title="External Key">EK</abbr> as part of the write operation for an object. MinIO uses the specified <abbr title="External Key">EK</abbr> to perform SSE-S3.

SSE-C does not support bucket-default encryption settings and requires clients perform all key management operations.
{{% /tab %}}
{{< /tabpane >}}

MinIO SSE requires enabling [Network Encryption (TLS)](/operations/network-encryption/#minio-tls).

<a id="minio-encryption-sse-secure-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

MinIO requires access to the Encryption Key (EK) *and* external Key Management System (KMS) used as part of SSE operations to decrypt an object. You can use this dependency to securely erase and lock objects from access by disabling access to the EK or KMS used for encryption.

General strategies include, but are not limited to:

- Seal the <abbr title="Key Management System">KMS</abbr> such that it cannot be accessed by MinIO server anymore. This locks all SSE-KMS or SSE-S3 encrypted objects protected by any <abbr title="External Key">EK</abbr> stored on the KMS. The encrypted objects remain unreadable as long as the KMS remains sealed.
- Seal/Unmount an <abbr title="External Key">EK</abbr>. This locks all SSE-KMS or SSE-S3 encrypted objects protected by that EK. The encrypted objects remain unreadable as long as the CMK(s) remains sealed.
- Delete an <abbr title="External Key">EK</abbr>. This renders all SSE-KMS or SSE-S3 encrypted objects protected by that EK as permanently unreadable. The combination of deleting an EK and deleting the data may fulfill regulatory requirements around secure deletion of data.

  Deleting an <abbr title="External Key">EK</abbr> is typically irreversible. Exercise extreme caution before intentionally deleting a master key.

For more information, see:

- [SSE-KMS Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-erasure-locking)
- [SSE-S3 Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-erasure-locking)
- [SSE-C Secure Erasure and Locking](/administration/server-side-encryption/server-side-encryption-sse-c/#minio-encryption-sse-c-erasure-locking)
