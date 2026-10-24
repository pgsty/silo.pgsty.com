---
title: "Server-Side Encryption Per-Deployment Key (SSE-S3)"
url: "/administration/server-side-encryption/server-side-encryption-sse-s3/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption/server-side-encryption-sse-s3.rst
upstream_modified: true
---

<a id="server-side-encryption-per-deployment-key-sse-s3"></a>
<a id="minio-encryption-sse-s3"></a>

MinIO Server-Side Encryption (SSE) protects objects as part of write operations, allowing clients to take advantage of server processing power to secure objects at the storage layer (encryption-at-rest). SSE also provides key functionality to regulatory and compliance requirements around secure locking and erasure.

MinIO SSE uses the [PGSTY KES](https://github.com/pgsty/kes) and an external Key Management Service (KMS) for performing secured cryptographic operations at scale. MinIO also supports client-managed key management, where the application takes full responsibility for creating and managing encryption keys for use with MinIO SSE.

MinIO SSE-S3 en/decrypts objects using an External Key (EK) managed by a Key Management System (KMS). You must specify the <abbr title="External Key">EK</abbr> using the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) environment variable when starting up the MinIO server. MinIO uses the same EK for *all* SSE-S3 cryptographic operations.

You can enable bucket-default SSE-S3 encryption using the [`mc encrypt set`](/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) command:

```shell
mc encrypt set sse-s3 play/mybucket
```

- Replace `play/mybucket` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) and bucket on which you want to enable automatic SSE-S3 encryption.

MinIO SSE-S3 is functionally compatible with AWS S3 [Server-Side Encryption with Amazon S3-Managed Keys](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html) using KES as the key service. The following archived upstream integration guides describe inherited backends; the maintained integration is [SILO + PGSTY KES + OpenBao KV v2](/operations/server-side-encryption/configure-minio-kes/):

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure KeyVault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

<a id="minio-encryption-sse-s3-quickstart"></a>

## Quickstart {#quickstart}

Use a PGSTY KES deployment you control. Complete [Configure SILO with KES](/operations/server-side-encryption/configure-minio-kes/) first, including persistent key storage, TLS trust, a SILO application policy, and a working `mysilo` client alias. Do not use public demonstration keys for stored data.

### 1) Create an Encryption Key for SSE-S3 {#create-an-encryption-key-for-sse-s3-encryption}

The KES procedure creates `silo-default` for backend data and SSE-S3, and `silo-bucket` for the SSE-KMS example. Ensure `silo-default` exists and that SILO's KES identity may generate and decrypt data keys with it. An administrator can provision additional permitted keys with `mcli admin kms key create mysilo KEYNAME`.

### 2) Configure SILO for SSE-S3 {#configure-minio-for-sse-s3-object-encryption}

Every server needs the same KES configuration. For the example from the KES procedure:

```shell
MINIO_KMS_KES_ENDPOINT=https://kes.example.net:7373
MINIO_KMS_KES_API_KEY='REPLACE_WITH_SILO_API_KEY'
MINIO_KMS_KES_CAPATH=/etc/silo/certs/kes-ca.crt
MINIO_KMS_KES_KEY_NAME=silo-default
```

Keep the API key secret and use the actual CA path on each SILO host. The API key and explicit client key/certificate settings are mutually exclusive. For an existing encrypted deployment, preserve the original default key and all keys needed by existing objects.

### 3) Apply the Server Configuration {#restart-the-minio-deployment-to-enable-sse-s3}

If you changed the environment, restart the deployment through the service manager that owns it. For systemd `EnvironmentFile` changes, restart `silo.service`; an administrative restart alone does not reload that file unless SILO separately loads it through `MINIO_CONFIG_ENV_FILE`. If the KES procedure is already complete and the configuration is unchanged, no additional restart is needed.

### 4) Configure Automatic Bucket Encryption {#configure-automatic-bucket-encryption}

Create the example bucket if it does not exist, then set its default encryption:

```shell
mcli mb mysilo/encryptedbucket
mcli encrypt set sse-s3 mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
```

This setting applies to a **bucket**, not a prefix. Verify a new object with `mcli cp`, `mcli stat`, and a read as shown in the KES procedure. Existing objects are not rewritten by changing the default.

You can remove the bucket default with `mcli encrypt clear mysilo/encryptedbucket`. This does not decrypt existing objects or backend data, and does not remove the need to retain their keys. A server-wide automatic encryption setting or an explicit encryption request may still encrypt new writes.

<a id="minio-encryption-sse-s3-erasure-locking"></a>

## Secure Erasure and Locking {#secure-erasure-and-locking}

KES and SILO can cache key material. Sealing a key store or revoking access is not guaranteed to invalidate cached keys immediately; account for cache expiry and active processes when testing revocation.

SSE-S3 protects objects using an <abbr title="External Key">EK</abbr> specified at server startup using the [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) environment variable. MinIO therefore *requires* access to that <abbr title="External Key">EK</abbr> for decrypting that object.

- Disabling access to the <abbr title="External Key">EK</abbr> prevents decryption of dependent objects once usable cached key material is also unavailable. Restoring access to the original key permits decryption again.
- Permanently losing every usable copy of the <abbr title="External Key">EK</abbr>, including cached copies and backups, makes objects that still depend on it unrecoverable.

The scope of the <abbr title="External Key">EK</abbr> depends on:

- Which buckets specified automatic SSE-S3 encryption, *and*
- Which write operations requested SSE-S3 encryption.

<a id="minio-encryption-sse-s3-encryption-process"></a>

## Encryption Process {#encryption-process}

> [!NOTE]
> **Note**
>
> The following section describes MinIO internal logic and functionality. This information is purely educational and is not necessary for configuring or implementing any MinIO feature.

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

## Key Rotation {#key-rotation}

SSE-S3 encrypted objects can be re-keyed without rewriting object data. The
server assumes only two services from the KMS — `GenerateKey` (return a new
data key in plain and master-key-encrypted form) and `DecryptKey` (unwrap an
encrypted data key) — and rotation is built from them:

1. The server decrypts the object's OEK using the encrypted data key and
   master key ID stored in the object's own metadata.
2. It requests a new data key from the KMS using the master key ID of the
   **current** KMS configuration.
3. It derives a new KEK from the new data key, re-encrypts the OEK with it,
   and stores the new encrypted OEK, encrypted data key, and master key ID in
   the object metadata.

The object content itself does not change: only the key hierarchy wrapping the
OEK is re-created under the currently configured master key. This is how
objects encrypted under an old master key are brought under a new one. The
old key must remain decryptable until all required object versions have been
rotated and verified; deleting it first prevents the initial unwrap.

Use a [batch `keyrotate` job](/administration/batch-framework-job-keyrotate/)
to rotate stored object keys. Starting the job requires the corresponding
batch administration permission, and the server needs KMS permission to
decrypt the old data key and generate a new one. Ordinary S3 self-COPY is a
different path and can rewrite object data. The
[`mc admin kms key`](/reference/minio-mc-admin/mc-admin-kms-key/) commands
manage KMS keys; they do not themselves rotate every stored object's key.
