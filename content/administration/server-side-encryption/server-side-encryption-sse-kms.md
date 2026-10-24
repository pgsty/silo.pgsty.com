---
title: "Server-Side Encryption with Per-Bucket Keys (SSE-KMS)"
url: "/administration/server-side-encryption/server-side-encryption-sse-kms/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption/server-side-encryption-sse-kms.rst
upstream_modified: true
---

<a id="server-side-encryption-with-per-bucket-keys-sse-kms"></a>
<a id="minio-encryption-sse-kms"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [PGSTY KES](https://github.com/pgsty/kes) and a [supported external Key Management Service (KMS)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md#supported-kms-targets) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO SSE-KMS encrypts or decrypts objects using an External Key (EK) managed by a Key Management System (KMS). Each bucket and object can have a separate <abbr title="External Key">EK</abbr>, supporting more granular cryptographic operations in the deployment. MinIO can only decrypt an object if it can access both the KMS *and* the <abbr title="External Key">EK</abbr> used to encrypt that object.

You can enable bucket-default SSE-KMS encryption using the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command:

```shell
mc encrypt set sse-kms EXTERNALKEY play/mybucket
```

- Replace `EXTERNALKEY` with the name of the <abbr title="External Key">EK</abbr> to use for encrypting objects in the bucket.
- Replace `play/mybucket` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and bucket on which you want to enable automatic SSE-KMS encryption.

MinIO SSE-KMS is functionally compatible with AWS S3 [Server-Side Encryption with KMS keys stored in AWS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html) using KES as the key service. The following archived upstream integration guides describe inherited backends; the maintained integration is [SILO + PGSTY KES + OpenBao KV v2](/operations/server-side-encryption/configure-minio-kes/):

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

<a id="minio-encryption-sse-kms-quickstart"></a>

## Quickstart {#quickstart}

Use a PGSTY KES deployment you control. Complete [Configure SILO with KES](/operations/server-side-encryption/configure-minio-kes/) first, including persistent key storage, TLS trust, a SILO application policy, and a working `mysilo` client alias. Do not use public demonstration keys for stored data.

### 1) Create an Encryption Key for SSE-KMS {#create-an-encryption-key-for-sse-kms-encryption}

The KES procedure creates `silo-default` for backend data and SSE-S3, and `silo-bucket` for the SSE-KMS example. Ensure `silo-bucket` exists and that SILO's KES identity may generate and decrypt data keys with it. An administrator can provision additional permitted keys with `mcli admin kms key create mysilo KEYNAME`.

### 2) Configure SILO for SSE-KMS {#configure-minio-for-sse-kms-object-encryption}

Every server needs the same KES configuration. For the example from the KES procedure:

```shell
MINIO_KMS_KES_ENDPOINT=https://kes.example.net:7373
MINIO_KMS_KES_API_KEY='REPLACE_WITH_SILO_API_KEY'
MINIO_KMS_KES_CAPATH=/etc/silo/certs/kes-ca.crt
MINIO_KMS_KES_KEY_NAME=silo-default
```

Keep the API key secret and use the actual CA path on each SILO host. The API key and explicit client key/certificate settings are mutually exclusive. For an existing encrypted deployment, preserve the original default key and all keys needed by existing objects.

### 3) Apply the Server Configuration {#restart-the-minio-deployment-to-enable-sse-kms}

If you changed the environment, restart the deployment through the service manager that owns it. For systemd `EnvironmentFile` changes, restart `silo.service`; an administrative restart alone does not reload that file unless SILO separately loads it through `MINIO_CONFIG_ENV_FILE`. If the KES procedure is already complete and the configuration is unchanged, no additional restart is needed.

### 4) Configure Automatic Bucket Encryption {#configure-automatic-bucket-encryption}

Create the example bucket if it does not exist, then set its default encryption:

```shell
mcli mb mysilo/encryptedbucket
mcli encrypt set sse-kms silo-bucket mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
```

This setting applies to a **bucket**, not a prefix. Verify a new object with `mcli cp`, `mcli stat`, and a read as shown in the KES procedure. Existing objects are not rewritten by changing the default.

You can remove the bucket default with `mcli encrypt clear mysilo/encryptedbucket`. This does not decrypt existing objects or backend data, and does not remove the need to retain their keys. A server-wide automatic encryption setting or an explicit encryption request may still encrypt new writes.

<a id="minio-encryption-sse-kms-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

KES and SILO can cache key material. Sealing a key store or revoking access is not guaranteed to invalidate cached keys immediately; account for cache expiry and active processes when testing revocation.

SSE-KMS protects objects using an <abbr title="External Key">EK</abbr> specified either as part of the bucket automatic encryption settings *or* as part of the write operation. MinIO therefore *requires* access to that <abbr title="External Key">EK</abbr> for decrypting that object.

- Disabling access to the <abbr title="External Key">EK</abbr> prevents decryption of dependent objects once usable cached key material is also unavailable. Restoring access to the original key permits decryption again.
- Permanently losing every usable copy of the <abbr title="External Key">EK</abbr>, including cached copies and backups, makes objects that still depend on it unrecoverable.

The scope of a single <abbr title="External Key">EK</abbr> depends on:

- Which buckets specified that <abbr title="External Key">EK</abbr> for automatic SSE-KMS encryption, *and*
- Which write operations specified that <abbr title="External Key">EK</abbr> when requesting SSE-KMS encryption.

For example, a key used only by one bucket limits key-loss effects to objects that still depend on that key. A key shared across buckets couples their recovery requirements. Bucket defaults can change and clients can select other keys, so check object versions rather than inferring key use from the current bucket setting.

<a id="minio-encryption-sse-kms-encryption-process"></a>

## Encryption Process {#encryption-process}

> [!NOTE]
> **Note**
>
> This section describes MinIO internal logic and functionality. This information is purely educational and is not a prerequisite for configuring or implementing any MinIO feature.

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
