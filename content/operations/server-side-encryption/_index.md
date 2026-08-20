---
title: "Data Encryption (SSE)"
url: "/operations/server-side-encryption/"
weight: 60
icon: fa-solid fa-lock
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/server-side-encryption.rst
upstream_modified: false
---

<a id="data-encryption-sse"></a>
<a id="minio-sse-data-encryption"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [MinIO Key Encryption Service (KES)](https://github.com/minio/kes) and an external Key Management Service (KMS) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO supports the following <abbr title="Key Management System">KMS</abbr> as the central key store:

- [HashiCorp KeyVault](/operations/server-side-encryption/configure-minio-kes/#minio-sse-vault)
- [AWS SecretsManager](/operations/server-side-encryption/configure-minio-kes/#minio-sse-aws)
- [Google Cloud SecretManager](/operations/server-side-encryption/configure-minio-kes/#minio-sse-gcp)
- [Azure Key Vault](/operations/server-side-encryption/configure-minio-kes/#minio-sse-azure)
- [Fortanix SDKMS](https://github.com/minio/kes/wiki/Fortanix-SDKMS)
- [Thales Digital Identity and Security (formerly Gemalto)](https://github.com/minio/kes/wiki/Gemalto-KeySecure)

MinIO SSE requires enabling [Network Encryption (TLS)](/operations/network-encryption/#minio-tls).

## Supported Encryption Types {#supported-encryption-types}

MinIO SSE is feature and API compatible with [AWS Server-Side Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/server-side-encryption.html) and supports the following encryption strategies:

{{< tabs group="sse-kms-recommended-sse-s3-sse-c" >}}
{{< tab label="SSE-KMS Recommended" value="sse-kms-recommended" >}}
MinIO supports enabling automatic SSE-KMS encryption of all objects written to a bucket using a specific External Key (EK) stored on the external <abbr title="Key Management System">KMS</abbr>. Clients can override the bucket-default <abbr title="External Key">EK</abbr> by specifying an explicit key as part of the write operation.

For buckets without automatic SSE-KMS encryption, clients can specify an <abbr title="External Key">EK</abbr> as part of the write operation instead.

MinIO encrypts backend data as part of enabling server-side encryption. You cannot disable SSE-KMS encryption once enabled.

SSE-KMS provides more granular and customizable encryption compared to SSE-S3 and SSE-C and is recommended over the other supported encryption methods.

For a tutorial on enabling SSE-KMS in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-quickstart).
{{< /tab >}}
{{< tab label="SSE-S3" value="sse-s3" >}}
MinIO supports enabling automatic SSE-S3 encryption of all objects written to a bucket using an <abbr title="External Key">EK</abbr> stored on the external <abbr title="Key Management System">KMS</abbr>. MinIO SSE-S3 supports *one* <abbr title="External Key">EK</abbr> for the entire deployment.

For buckets without automatic SSE-S3 encryption, clients can request SSE encryption as part of the write operation instead.

MinIO encrypts backend data as part of enabling server-side encryption. You cannot disable SSE-KMS encryption once enabled.

For a tutorial on enabling SSE-s3 in a local (non-production) MinIO Deployment, see [Quickstart](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-quickstart).
{{< /tab >}}
{{< tab label="SSE-C" value="sse-c" >}}
Clients specify an <abbr title="External Key">EK</abbr> as part of the write operation for an object. MinIO uses the specified <abbr title="External Key">EK</abbr> to perform SSE-S3.

SSE-C does not support bucket-default encryption settings and requires clients perform all key management operations.
{{< /tab >}}
{{< /tabs >}}
