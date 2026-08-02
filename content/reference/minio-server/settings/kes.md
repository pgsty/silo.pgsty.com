---
title: "Key Encryption Service Settings"
url: "/reference/minio-server/settings/kes/"
weight: 100
minio_origin: true
silo_modified: false
---

<a id="key-encryption-service-settings"></a>
<a id="minio-server-envvar-kes"></a>

MinIO Server includes three groups of environment variables to manage how the MinIO Server interacts with the Key Encryption Service (KES), Key Management Service (KMS), or static key files. You may only define one of the three sets. If more than one type of environment variable sets is defined, MinIO returns an error.

{{% alert color="info" %}}
**Note**

These settings do not have configuration setting options for use with [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).
{{% /alert %}}

Define any one set of these environment variables in the host system prior to starting or restarting the MinIO process. Refer to your operating system’s documentation for how to define an environment variable.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Key Encryption Service {#key-encryption-service}

Define the following variables to use the Key Encryption Service (KES) to connect to a [supported 3rd party Key Management Service provider](https://docs.min.io/community/minio-kes/#supported-kms-targets).

#### `MINIO_KMS_KES_ENDPOINT` {#envvar.MINIO_KMS_KES_ENDPOINT}

*envvar*

The endpoint(s) for the MinIO Key Encryption Service (KES) process to use for supporting SSE-S3 and MinIO backend encryption operations. Separate multiple KES endpoints with a `,`.

#### `MINIO_KMS_KES_KEY_NAME` {#envvar.MINIO_KMS_KES_KEY_NAME}

*envvar*

The name of an external key on the Key Management system (KMS) configured on the KES server and used for performing en/decryption operations. MinIO uses this key for the following:

- Encrypting backend data ([IAM](/administration/identity-access-management/#minio-authentication-and-identity-management), server configuration).
- The default encryption key for Server-Side Encryption with [SSE-KMS](/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms).
- The encryption key for Server-Side Encryption with [SSE-S3](/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3).

{{% alert color="warning" %}}
**Important**

Enabling <abbr title="Server-Side Encryption">SSE</abbr> on a MinIO deployment automatically encrypts the backend data for that deployment using the default encryption key.

MinIO *requires* access to KES and the external KMS to decrypt the backend and start normally. The KMS **must** maintain and provide access to the [`MINIO_KMS_KES_KEY_NAME`](#envvar.MINIO_KMS_KES_KEY_NAME). You cannot disable KES later or “undo” the <abbr title="Server-Side Encryption">SSE</abbr> configuration at a later point.
{{% /alert %}}

#### `MINIO_KMS_KES_API_KEY` {#envvar.MINIO_KMS_KES_API_KEY}

*envvar*

Preferred method for authenticating with the encryption service using the KES API key obtained from the [kes identity new](https://docs.min.io/community/minio-kes/cli/kes-identity/new/) command.

This environment variable is mutually exclusive with the [`MINIO_KMS_KES_KEY_FILE`](#envvar.MINIO_KMS_KES_KEY_FILE) and [`MINIO_KMS_KES_CERT_FILE`](#envvar.MINIO_KMS_KES_CERT_FILE) environment variables.

#### `MINIO_KMS_KES_KEY_FILE` {#envvar.MINIO_KMS_KES_KEY_FILE}

*envvar*

The private key associated to the the [`MINIO_KMS_KES_CERT_FILE`](#envvar.MINIO_KMS_KES_CERT_FILE) x.509 certificate to use when authenticating to the KES server. The KES server requires clients to present their certificate for performing mutual TLS (mTLS).

See the [KES wiki](https://github.com/minio/kes/wiki/Configuration#policy-configuration) for more complete documentation on KES access control.

You must also set the [`MINIO_KMS_KES_CERT_FILE`](#envvar.MINIO_KMS_KES_CERT_FILE). This variable is mutually exclusive with [`MINIO_KMS_KES_API_KEY`](#envvar.MINIO_KMS_KES_API_KEY).

#### `MINIO_KMS_KES_CERT_FILE` {#envvar.MINIO_KMS_KES_CERT_FILE}

*envvar*

The x.509 certificate to present to the KES server. The KES server requires clients to present their certificate for performing mutual TLS (mTLS).

The KES server computes an [identity](https://github.com/minio/kes/wiki/Configuration#policy-configuration) from the certificate and compares it to its configured policies. The KES server grants the [`minio`](/reference/minio-server/#command-minio) server access to only those operations explicitly granted by the policy.

See the [KES wiki](https://github.com/minio/kes/wiki/Configuration#policy-configuration) for more complete documentation on KES access control.

You must also set the [`MINIO_KMS_KES_KEY_FILE`](#envvar.MINIO_KMS_KES_KEY_FILE). This variable is mutually exclusive with [`MINIO_KMS_KES_API_KEY`](#envvar.MINIO_KMS_KES_API_KEY).

#### `MINIO_KMS_KES_CAPATH` {#envvar.MINIO_KMS_KES_CAPATH}

*envvar*

*Optional*

Allows validation of the KES Server Certificate for a Self-Signed or Third-Party <abbr title="Certificate Authority">CA</abbr>. Specify the path to the location of the <abbr title="Certificate Authority">CA</abbr> certificate for your KES deployment.

This variable is not required if you use a public certificate authority.

#### `MINIO_KMS_KES_KEY_PASSWORD` {#envvar.MINIO_KMS_KES_KEY_PASSWORD}

*envvar*

*Optional*

The password used to encrypt and decrypt the TLS private key, if used.

## MinIO Key Management Server (KMS) {#minio-key-management-server-kms}

Define the following variables to use [MinIO KMS](https://min.io/product/enterprise/key-management-server?ref=docs) to manage keys.

#### `MINIO_KMS_SERVER` {#envvar.MINIO_KMS_SERVER}

*envvar*

The endpoint(s) for the MinIO Key Management Service (KMS) process to use for supporting SSE-S3 and MinIO backend encryption operations. Separate multiple KMS endpoints with a `,`.

#### `MINIO_KMS_ENCLAVE` {#envvar.MINIO_KMS_ENCLAVE}

*envvar*

The MinIO KMS Enclave where the key and identity exist.

#### `MINIO_KMS_SSE_KEY` {#envvar.MINIO_KMS_SSE_KEY}

*envvar*

The default key to use for SSE-S3 encryption when a call does not specify a key identity.

#### `MINIO_KMS_API_KEY` {#envvar.MINIO_KMS_API_KEY}

*envvar*

The credential used to authenticate with the MinIO KMS service.

## Static Key Files {#static-key-files}

{{% alert color="danger" %}}
**Warning**

These settings support early development and evaluation of Server-Side Encryption of Objects without depending on an external KMS. Do not use these settings in any extended development, QA, or production environments. See [Server-Side Object Encryption with KES](/operations/server-side-encryption/configure-minio-kes/#minio-sse-vault) for guidance on deploying SSE using MinIO Key Encryption Service (KES) and an external KMS.
{{% /alert %}}

Provide a static KMS key or key file to use for encryption.

#### `MINIO_KMS_SECRET_KEY` {#envvar.MINIO_KMS_SECRET_KEY}

*envvar*

The base64 form of the static KMS key in the form `<key-name>:<base64-32byte-key>`. Implements a subset of KMS APIs.

#### `MINIO_KMS_SECRET_KEY_FILE` {#envvar.MINIO_KMS_SECRET_KEY_FILE}

*envvar*

Path to the file to read the static KMS key from.
