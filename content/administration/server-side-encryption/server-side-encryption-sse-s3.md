---
title: "Server-Side Encryption Per-Deployment Key (SSE-S3)"
url: "/administration/server-side-encryption/server-side-encryption-sse-s3/"
weight: 20
minio_origin: true
silo_modified: true
---

<a id="server-side-encryption-per-deployment-key-sse-s3"></a>
<a id="minio-encryption-sse-s3"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [MinIO Key Encryption Service (KES)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md) and an external Key Management Service (KMS) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO SSE-S3 en/decrypts objects using an External Key (EK) managed by a Key Management System (KMS). You must specify the <abbr title="External Key">EK</abbr> using the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) environment variable when starting up the MinIO server. MinIO uses the same EK for *all* SSE-S3 cryptographic operations.

You can enable bucket-default SSE-S3 encryption using the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command:

```shell
mc encrypt set sse-s3 play/mybucket
```

- Replace `play/mybucket` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and bucket on which you want to enable automatic SSE-KMS encryption.

MinIO SSE-S3 is functionally compatible with AWS S3 [Server-Side Encryption with Amazon S3-Managed Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html) while expanding support to include the following KMS providers:

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure KeyVault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

<a id="minio-encryption-sse-s3-quickstart"></a>

## Quickstart {#quickstart}

{{% alert color="warning" %}}
**Important**

Enabling <abbr title="Server-Side Encryption">SSE</abbr> on a MinIO deployment automatically encrypts the backend data for that deployment using the default encryption key.

MinIO *requires* access to KES and the external KMS to decrypt the backend and start normally. The KMS **must** maintain and provide access to the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME). You cannot disable KES later or “undo” the <abbr title="Server-Side Encryption">SSE</abbr> configuration at a later point.
{{% /alert %}}

The following procedure uses the `play` MinIO <abbr title="Key Encryption Service">KES</abbr> sandbox for supporting <abbr title="Server-Side Encryption">SSE</abbr> with SSE-S3 in evaluation and early development environments.

For extended development or production environments, use one of the following supported external Key Management Services (KMS):

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure KeyVault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

{{% alert color="warning" %}}
**Important**

The MinIO KES `Play` sandbox is public and grants root access to all created External Keys (EK). Any <abbr title="External Key">EK</abbr> stored on the `Play` sandbox may be accessed or destroyed at any time, rendering protected data vulnerable or permanently unreadable.

- **Never** use the `Play` sandbox to protect data you cannot afford to lose or reveal.
- **Never** generate <abbr title="External Key">EK</abbr> using names that reveal private, confidential, or internal naming conventions for your organization.
- **Never** use the `Play` sandbox for production environments.
{{% /alert %}}

This procedure requires the following components:

- Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to the source deployment. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.
- Install [MinIO Key Encryption Service (KES)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md) on a machine with internet access. See the KES [Getting Started](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/tutorials/getting-started.md) guide for instructions on downloading, installing, and configuring KES.

### 1) Create an Encryption Key for SSE-S3 Encryption {#create-an-encryption-key-for-sse-s3-encryption}

Use the [kes](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/cli/_index.md) command line tool to create a new External Key (EK) for use with SSE-S3 Encryption.

The following command retrieves the root [identity](https://github.com/minio/kes/wiki/Configuration#policy-configuration) for the KES server connected to the KES `play` sandbox:

```shell
curl -sSL --tlsv1.2 \
  -O 'https://raw.githubusercontent.com/minio/kes/master/root.key' \
  -O 'https://raw.githubusercontent.com/minio/kes/master/root.cert'
```

Set the following environment variables in the terminal or shell:

```shell
export KES_CLIENT_KEY=root.key
export KES_CLIENT_CERT=root.cert
```

<table>
  <tbody>
    <tr>
      <td><p><code>KES_CLIENT_KEY</code></p></td>
      <td><p>The private key for an <a href="https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/concepts/_index.md#authorization">identity</a> on the KES server.
The identity must grant access to at minimum the <code>/v1/create</code>, <code>/v1/generate</code>, and <code>/v1/list</code> <a href="https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/concepts/server-api.md">API endpoints</a>.
This step uses the <code>root</code> identity for the MinIO <code>play</code> KES sandbox, which provides access to all operations on the KES server.</p></td>
    </tr>
    <tr>
      <td><p><code>KES_CLIENT_CERT</code></p></td>
      <td><p>The corresponding certificate for the <a href="https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/concepts/_index.md#authorization">identity</a> on the KES server.
This step uses the <code>root</code> identity for the MinIO <code>play</code> KES sandbox, which provides access to all operations on the KES server.</p></td>
    </tr>
  </tbody>
</table>

The following command creates a new <abbr title="External Key">EK</abbr> through the [KES CLI](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/cli/kes-key/create.md):

```shell
kes key create my-minio-sse-s3-key
```

This tutorial uses the example `my-minio-sse-s3-key` name for ease of reference. Specify a unique key name to prevent collision with existing keys.

### 2) Configure MinIO for SSE-S3 Object Encryption {#configure-minio-for-sse-s3-object-encryption}

Specify the following environment variables in the shell or terminal on each MinIO server host in the deployment:

```shell
export MINIO_KMS_KES_ENDPOINT=https://play.min.io:7373
export MINIO_KMS_KES_API_KEY=<API-key-identity-string-from-KES> # Replace with the key string for your credentials
export MINIO_KMS_KES_KEY_NAME=my-minio-sse-s3-key
```

{{% alert color="info" %}}
**Note**

- An API key is the preferred way to authenticate with the KES server, as it provides a streamlined and secure authentication process to the KES server.
- Alternatively, specify the [`MINIO_KMS_KES_KEY_FILE`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_FILE) and [`MINIO_KMS_KES_CERT_FILE`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_CERT_FILE) instead of [`MINIO_KMS_KES_API_KEY`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_API_KEY).

  API keys are mutually exclusive with certificate-based authentication. Specify *either* the API key variable *or* the Key File and Cert File variables.
- The documentation on this site uses API keys.
{{% /alert %}}

<table>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_ENDPOINT"><code>MINIO_KMS_KES_ENDPOINT</code></a></p></td>
      <td><p>The endpoint for the MinIO <code>Play</code> KES service.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_FILE"><code>MINIO_KMS_KES_KEY_FILE</code></a></p></td>
      <td><p>The private key file corresponding to an
<a href="https://github.com/minio/kes/wiki/Configuration#policy-configuration">identity</a>
on the KES service. The identity must grant permission to
create, generate, and decrypt keys. Specify the same
identity key file as the <code>KES_KEY_FILE</code> environment variable
in the previous step.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_CERT_FILE"><code>MINIO_KMS_KES_CERT_FILE</code></a></p></td>
      <td><p>The public certificate file corresponding to an
<a href="https://github.com/minio/kes/wiki/Configuration#policy-configuration">identity</a>
on the KES service. The identity must grant permission to
create, generate, and decrypt keys. Specify the same
identity certificate as the <code>KES_CERT_FILE</code> environment
variable in the previous step.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME"><code>MINIO_KMS_KES_KEY_NAME</code></a></p></td>
      <td><p>The name of the External Key (EK) to use for
performing SSE encryption operations. KES retrieves the EK from
the configured Key Management System (KMS). Specify the name of the
key created in the previous step.</p></td>
    </tr>
  </tbody>
</table>

### 3) Restart the MinIO Deployment to Enable SSE-S3 {#restart-the-minio-deployment-to-enable-sse-s3}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

### 4) Configure Automatic Bucket Encryption {#configure-automatic-bucket-encryption}

*Optional*

You can skip this step if you intend to use only client-driven SSE-S3.

Use the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command to enable automatic SSE-S3 protection of all objects written to a specific bucket.

```shell
mc encrypt set sse-s3 ALIAS/BUCKET
```

- Replace [`ALIAS`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment on which you enabled SSE-S3.
- Replace [`BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the full path to the bucket or bucket prefix on which you want to enable automatic SSE-S3.

<a id="minio-encryption-sse-s3-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

SSE-S3 protects objects using an <abbr title="External Key">EK</abbr> specified at server startup using the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) environment variable. MinIO therefore *requires* access to that <abbr title="External Key">EK</abbr> for decrypting that object.

- Disabling the <abbr title="External Key">EK</abbr> temporarily locks SSE-S3-encrypted objects in the deployment by rendering them unreadable. You can later enable the <abbr title="External Key">EK</abbr> to resume normal read operations.
- Deleting the <abbr title="External Key">EK</abbr> renders all SSE-S3-encrypted objects in the deployment *permanently* unreadable. If the KMS does not have or support backups of the <abbr title="External Key">EK</abbr>, this process is *irreversible*.

The scope of the <abbr title="External Key">EK</abbr> depends on:

- Which buckets specified automatic SSE-S3 encryption, *and*
- Which write operations requested SSE-S3 encryption.

<a id="minio-encryption-sse-s3-encryption-process"></a>

## Encryption Process {#encryption-process}

{{% alert color="info" %}}
**Note**

The following section describes MinIO internal logic and functionality. This information is purely educational and is not necessary for configuring or implementing any MinIO feature.
{{% /alert %}}

SSE-S3 uses an External Key (EK) managed by the configured Key Management System (KMS) for performing cryptographic operations and protecting objects. The table below describes each stage of the encryption process:

<table>
  <thead>
    <tr>
      <th><p>Stage</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>SSE-Enabled Write Operation</p></td>
      <td><p>MinIO receives a write operation requesting SSE-S3 encryption.
MinIO uses the key name specified to
<a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME"><code>MINIO_KMS_KES_KEY_NAME</code></a> as the External Key (EK).</p></td>
    </tr>
    <tr>
      <td><p>Generate the Data Encryption Key (DEK)</p></td>
      <td><p>MinIO generates a Data Encryption Key (DEK) using the EK.
Specifically, <a href="https://github.com/minio/kes">MinIO Key Encryption Service (KES)</a> requests a new cryptographic key from the KMS using the EK as the “root” key.</p><p>KES returns both the plain-text <em>and</em> an EK-encrypted representation of the DEK.
MinIO stores the encrypted representation as part of the object metadata.</p></td>
    </tr>
    <tr>
      <td><p>Generate the Key Encryption Key (KEK)</p></td>
      <td><p>MinIO uses a deterministic algorithm to generate a 256-bit unique Key Encryption Key (KEK).
The key-derivation algorithm uses a pseudo-random function that takes the plain-text DEK, a randomly generated initialization vector, and a context consisting of values like the bucket and object name.</p><p>MinIO generates the KEK at the time of each cryptographic encryption or decryption operation and <em>never</em> stores the KEK to a drive.</p></td>
    </tr>
    <tr>
      <td><p>Generate the Object Encryption Key (OEK)</p></td>
      <td><p>MinIO generates a random 256-bit unique Object Encryption Key (OEK) and uses that key to encrypt the object.
MinIO never stores the plaintext representation of the OEK on a drive.
The plaintext OEK resides in RAM during cryptographic operations.</p></td>
    </tr>
    <tr>
      <td><p>Encrypt the Object</p></td>
      <td><p>MinIO uses the OEK to encrypt the object <em>prior</em> to storing the
object to a drive. MinIO then encrypts the OEK with the KEK.</p><p>MinIO stores the encrypted representation of the OEK and DEK as part
of the metadata.</p></td>
    </tr>
  </tbody>
</table>
