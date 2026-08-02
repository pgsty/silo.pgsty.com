---
title: "Server-Side Encryption with Per-Bucket Keys (SSE-KMS)"
url: "/administration/server-side-encryption/server-side-encryption-sse-kms/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="server-side-encryption-with-per-bucket-keys-sse-kms"></a>
<a id="minio-encryption-sse-kms"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [MinIO Key Encryption Service (KES)](https://docs.min.io/community/minio-kes/) and a [supported external Key Management Service (KMS)](https://docs.min.io/community/minio-kes/#supported-kms-targets) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO SSE-KMS encrypts or decrypts objects using an External Key (EK) managed by a Key Management System (KMS). Each bucket and object can have a separate <abbr title="External Key">EK</abbr>, supporting more granular cryptographic operations in the deployment. MinIO can only decrypt an object if it can access both the KMS *and* the <abbr title="External Key">EK</abbr> used to encrypt that object.

You can enable bucket-default SSE-KMS encryption using the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command:

```shell
mc encrypt set sse-kms EXTERNALKEY play/mybucket
```

- Replace `EXTERNALKEY` with the name of the <abbr title="External Key">EK</abbr> to use for encrypting objects in the bucket.
- Replace `play/mybucket` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and bucket on which you want to enable automatic SSE-KMS encryption.

MinIO SSE-KMS is functionally compatible with AWS S3 [Server-Side Encryption with KMS keys stored in AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html) while expanding support to include the following KMS providers:

- [AWS Secrets Manager](https://docs.min.io/community/minio-kes/integrations/aws-secrets-manager/)
- [Azure Key Vault](https://docs.min.io/community/minio-kes/integrations/azure-keyvault/)
- [Entrust KeyControl](https://docs.min.io/community/minio-kes/integrations/entrust-keycontrol/)
- [Fortanix SDKMS](https://docs.min.io/community/minio-kes/integrations/fortanix-sdkms/)
- [Google Cloud Secret Manager](https://docs.min.io/community/minio-kes/integrations/google-cloud-secret-manager/)
- [HashiCorp Vault Keystore](https://docs.min.io/community/minio-kes/integrations/hashicorp-vault-keystore/)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://docs.min.io/community/minio-kes/integrations/thales-ciphertrust/)

<a id="minio-encryption-sse-kms-quickstart"></a>

## Quickstart {#quickstart}

{{% alert color="warning" %}}
**Important**

Enabling <abbr title="Server-Side Encryption">SSE</abbr> on a MinIO deployment automatically encrypts the backend data for that deployment using the default encryption key.

MinIO *requires* access to KES and the external KMS to decrypt the backend and start normally. The KMS **must** maintain and provide access to the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME). You cannot disable KES later or “undo” the <abbr title="Server-Side Encryption">SSE</abbr> configuration at a later point.
{{% /alert %}}

The following procedure uses the `play` MinIO <abbr title="Key Encryption Service">KES</abbr> sandbox for supporting <abbr title="Server-Side Encryption">SSE</abbr> with SSE-KMS in evaluation and early development environments.

For extended development or production environments, use one of the following supported external Key Management Services (KMS):

- [AWS Secrets Manager](https://docs.min.io/community/minio-kes/integrations/aws-secrets-manager/)
- [Azure Key Vault](https://docs.min.io/community/minio-kes/integrations/azure-keyvault/)
- [Entrust KeyControl](https://docs.min.io/community/minio-kes/integrations/entrust-keycontrol/)
- [Fortanix SDKMS](https://docs.min.io/community/minio-kes/integrations/fortanix-sdkms/)
- [Google Cloud Secret Manager](https://docs.min.io/community/minio-kes/integrations/google-cloud-secret-manager/)
- [HashiCorp Vault Keystore](https://docs.min.io/community/minio-kes/integrations/hashicorp-vault-keystore/)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://docs.min.io/community/minio-kes/integrations/thales-ciphertrust/)

{{% alert color="warning" %}}
**Important**

The MinIO KES `Play` sandbox is public and grants root access to all created External Keys (EK). Any <abbr title="External Key">EK</abbr> stored on the `Play` sandbox may be accessed or destroyed at any time, rendering protected data vulnerable or permanently unreadable.

- **Never** use the `Play` sandbox to protect data you cannot afford to lose or reveal.
- **Never** generate <abbr title="External Key">EK</abbr> using names that reveal private, confidential, or internal naming conventions for your organization.
- **Never** use the `Play` sandbox for production environments.
{{% /alert %}}

This procedure requires the following components:

- Install [`mc`](/reference/minio-mc/#command-mc) on a machine with network access to the source deployment. See the `mc` [Installation Quickstart](/reference/minio-mc/#mc-install) for instructions on downloading and installing `mc`.
- Install [MinIO Key Encryption Service (KES)](https://docs.min.io/community/minio-kes/) on a machine with internet access. See the `kes` [Getting Started](https://docs.min.io/community/minio-kes/tutorials/getting-started/) guide for instructions on downloading, installing, and configuring KES.

### 1) Create an Encryption Key for SSE-KMS Encryption {#create-an-encryption-key-for-sse-kms-encryption}

Use the [kes](https://docs.min.io/community/minio-kes/cli/) command line tool to create a new External Key (EK) for use with SSE-KMS Encryption.

The following command retrieves the root [identity](https://docs.min.io/community/minio-kes/concepts/#authorization) for the `play` KES server:

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
      <td><p>The private key for an <a href="https://docs.min.io/community/minio-kes/concepts/#authorization">identity</a> on the KES server.
The identity must grant access to at minimum the <code>/v1/create</code>, <code>/v1/generate</code>, and <code>/v1/list</code> <a href="https://docs.min.io/community/minio-kes/concepts/server-api/">API endpoints</a>.
This step uses the <code>root</code> identity for the MinIO <code>play</code> KES sandbox, which provides access to all operations on the KES server.</p></td>
    </tr>
    <tr>
      <td><p><code>KES_CLIENT_CERT</code></p></td>
      <td><p>The corresponding certificate for the <a href="https://docs.min.io/community/minio-kes/concepts/#authorization">identity</a> on the KES server.
This step uses the <code>root</code> identity for the MinIO <code>play</code> KES sandbox, which provides access to all operations on the KES server.</p></td>
    </tr>
  </tbody>
</table>

The following command creates a new <abbr title="External Key">EK</abbr> through KES.

```shell
kes key create my-minio-sse-kms-key
```

This tutorial uses the example `my-minio-sse-kms-key` name for ease of reference. Specify a unique key name to prevent collision with existing keys.

### 2) Configure MinIO for SSE-KMS Object Encryption {#configure-minio-for-sse-kms-object-encryption}

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
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_API_KEY"><code>MINIO_KMS_KES_API_KEY</code></a></p></td>
      <td><p>The API key <a href="https://docs.min.io/community/minio-kes/tutorials/kes-for-minio/#kes-server-setup">generated by KES</a> for the MinIO deployment.
The identity of the API key must grant permission to create, generate, and decrypt keys.</p><p>The API key is the preferred way to authenticate with the KES server.
If circumstances require it, specify the <a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_FILE"><code>MINIO_KMS_KES_KEY_FILE</code></a> and <a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_CERT_FILE"><code>MINIO_KMS_KES_CERT_FILE</code></a> instead.
Specify <em>either</em> the API key <em>or</em> the Key File and Cert File.
Do <em>not</em> populate all three environment variables.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME"><code>MINIO_KMS_KES_KEY_NAME</code></a></p></td>
      <td><p>The name of the External Key (EK) to use for performing SSE encryption operations.
KES retrieves the EK from the configured Key Management Service (KMS).
Specify the name of the key created in the previous step.</p></td>
    </tr>
  </tbody>
</table>

### 3) Restart the MinIO Deployment to Enable SSE-KMS {#restart-the-minio-deployment-to-enable-sse-kms}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

### 4) Configure Automatic Bucket Encryption {#configure-automatic-bucket-encryption}

Use the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command to enable automatic SSE-KMS protection of all objects written to a specific bucket.

```shell
mc encrypt set sse-kms my-minio-sse-kms-key ALIAS/BUCKET
```

- Replace [`ALIAS`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment on which you enabled SSE-KMS.
- Replace [`BUCKET`](/reference/minio-mc/mc-encrypt-set/#mc.encrypt.set.ALIAS) with the full path to the bucket or bucket prefix on which you want to enable automatic SSE-KMS.

Objects written to the specified bucket are automatically encrypted using the specified <abbr title="External Key">EK</abbr>.

Repeat this step for each bucket on which you want to enable automatic SSE-KMS encryption. You can generate additional keys per bucket or bucket prefix, such that the scope of each <abbr title="External Key">EK</abbr> is limited to a subset of objects.

<a id="minio-encryption-sse-kms-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

SSE-KMS protects objects using an <abbr title="External Key">EK</abbr> specified either as part of the bucket automatic encryption settings *or* as part of the write operation. MinIO therefore *requires* access to that <abbr title="External Key">EK</abbr> for decrypting that object.

- Disabling the <abbr title="External Key">EK</abbr> temporarily locks objects encrypted with that <abbr title="External Key">EK</abbr> by rendering them unreadable. You can later enable the <abbr title="External Key">EK</abbr> to resume normal read operations on those objects.
- Deleting the <abbr title="External Key">EK</abbr> renders all objects encrypted by that <abbr title="External Key">EK</abbr> *permanently* unreadable. If the KMS does not have or support backups of the <abbr title="External Key">EK</abbr>, this process is *irreversible*.

The scope of a single <abbr title="External Key">EK</abbr> depends on:

- Which buckets specified that <abbr title="External Key">EK</abbr> for automatic SSE-KMS encryption, *and*
- Which write operations specified that <abbr title="External Key">EK</abbr> when requesting SSE-KMS encryption.

For example, consider a MinIO deployment using one <abbr title="External Key">EK</abbr> per bucket. Disabling a single <abbr title="External Key">EK</abbr> renders all objects in the associated bucket unreadable without affecting other buckets. If the deployment instead used one <abbr title="External Key">EK</abbr> for all objects and buckets, disabling that <abbr title="External Key">EK</abbr> renders all objects in the deployment unreadable.

<a id="minio-encryption-sse-kms-encryption-process"></a>

## Encryption Process {#encryption-process}

{{% alert color="info" %}}
**Note**

This section describes MinIO internal logic and functionality. This information is purely educational and is not a prerequisite for configuring or implementing any MinIO feature.
{{% /alert %}}

SSE-KMS uses an External Key (EK) managed by the configured Key Management System (KMS) for performing cryptographic operations and protecting objects. The table below describes each stage of the encryption process:

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
      <td><p>MinIO receives a write operation requesting SSE-KMS encryption.
The write operation <em>must</em> have an associated External Key (EK) to use
for encrypting the object.</p><ul><li><p>For write operations in buckets with automatic SSE-KMS enabled,
MinIO uses the bucket EK. If the write operation includes an
explicit EK, MinIO uses that <em>instead</em> of the bucket EK.</p></li><li><p>For write operations in buckets <em>without</em> automatic SSE-KMS enabled,
MinIO uses the EK specified to the write operation.</p></li></ul></td>
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
object to the drive. MinIO then encrypts the OEK with the KEK.</p><p>MinIO stores the encrypted representation of the OEK and DEK as part
of the metadata.</p></td>
    </tr>
  </tbody>
</table>

For read operations, MinIO decrypts the object by retrieving the <abbr title="External Key">EK</abbr> to decrypt the <abbr title="Data Encryption Key">DEK</abbr>. MinIO then regenerates the <abbr title="Key Encryption Key">KEK</abbr>, decrypts the <abbr title="Object Encryption Key">OEK</abbr>, and decrypts the object.
