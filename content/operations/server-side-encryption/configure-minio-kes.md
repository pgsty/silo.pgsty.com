---
title: "Server-Side Object Encryption with KES"
url: "/operations/server-side-encryption/configure-minio-kes/"
description: "Deploy Silo with server-side object encryption"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/server-side-encryption/configure-minio-kes.rst
upstream_modified: true
---

<a id="server-side-object-encryption-with-kes"></a>

Use **PGSTY KES** as a separate key encryption service for SILO. Upstream MinIO KES is deprecated, but the maintained [`pgsty/kes`](https://github.com/pgsty/kes) fork has a published [20261026 release](/blog/release/silo-20261026/#kes). KES is optional, independently released, and not embedded in the SILO binary.

The maintained integration is **SILO → PGSTY KES → OpenBao KV v2**. SILO encrypts object data; KES authenticates SILO and generates or decrypts data keys; OpenBao persists KES root keys. OpenBao uses KES's `keystore.vault` configuration. See the [integration design](/blog/design/kes-openbao/) for the tested scope and upgrade boundaries.

## Prerequisites {#prerequisites}

### Access to the SILO Cluster {#access-to-minio-cluster}

- Install `silo`, `mcli`, and `kes` from [Download & Install](/download/) and verify their release checksums.
- Configure an administrative [mcli alias](/reference/minio-mc/mc-alias-set/) for SILO. Examples use `mysilo`.
- Provide TLS certificates and trusted CA certificates for SILO, KES, and the key store. SILO must reach every configured KES endpoint; KES must reach the key store.
- Back up existing data, configuration, and encryption keys before changing an established deployment.

<a id="minio-sse-vault-prereq-vault"></a>
<a id="minio-sse-vault"></a>

### Prepare the Persistent Key Store {#ensure-kes-access-to-a-supported-kms-target}

Provision an OpenBao KV v2 mount and an AppRole with access to the KES key prefix; the [OpenBao ACL example](/blog/design/kes-openbao/#architecture) shows the required data and metadata paths. Configure these before starting KES. The following is a **fragment** of `server-config.yaml`, assuming a mount named `kv` and prefix `kes`:

```yaml
keystore:
  vault:
    endpoint: https://openbao.example.net:8200
    engine: kv
    version: v2
    prefix: kes
    approle:
      id: "REPLACE_WITH_APPROLE_ID"
      secret: "REPLACE_WITH_APPROLE_SECRET"
```

Use the [PGSTY KES configuration reference](https://github.com/pgsty/kes/blob/RELEASE.2026-10-26T00-00-00Z/server-config.yaml) for the complete configuration, including TLS trust for the key store. Protect the configuration file and provision real credentials outside source control. Keep OpenBao unsealed and test its backup and recovery procedure.

<a id="minio-sse-aws"></a>
<a id="minio-sse-azure"></a>
<a id="minio-sse-gcp"></a>

Other inherited backends remain in the configuration reference. Archived guides cover [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md), [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md), and [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md). Validate the chosen backend and authentication method separately.

## Procedure {#procedure}

### 1. Configure KES Identities and TLS

Generate an application identity for SILO:

```shell
kes identity new
```

Keep the generated **API key** secret. Place the corresponding **identity hash**, not the API key, in the KES policy. Use a separate administrator identity to manage KES.

This policy fragment permits SILO to use keys whose names start with `silo-`:

```yaml
policy:
  silo:
    allow:
      - /v1/key/create/silo-*
      - /v1/key/generate/silo-*
      - /v1/key/decrypt/silo-*
    identities:
      - "REPLACE_WITH_SILO_IDENTITY_HASH"
```

Combine the key store and policy fragments with `address`, `admin.identity`, and the `tls.key`/`tls.cert` settings from the configuration reference. The TLS certificate must cover the hostname SILO uses. API-key authentication and an explicitly supplied client key/certificate are alternative SILO authentication methods; do not configure both.

Start the configured service:

```shell
kes server --config /etc/kes/server-config.yaml
```

For containers, mount the configuration and certificates where the KES process can read them. The PGSTY KES image runs as UID/GID `1000:1000`. KES packages provide the executable; provision configuration and service management separately.

### 2. Create the Keys

On an administrative host that trusts the KES server certificate, set the KES CLI credentials and create the default key and an optional bucket key:

```shell
export MINIO_KES_SERVER=https://kes.example.net:7373
export MINIO_KES_API_KEY='REPLACE_WITH_KES_ADMIN_API_KEY'
kes key create silo-default
kes key create silo-bucket
```

For an existing deployment, retain its original key names and key material. Creating a new key with an old name does not recover data encrypted under the original key.

### 3. Configure SILO

Set these values in the environment used by **every** SILO server process. With the supplied systemd unit, use `/etc/default/silo`:

```shell
MINIO_KMS_KES_ENDPOINT=https://kes.example.net:7373
MINIO_KMS_KES_API_KEY='REPLACE_WITH_SILO_API_KEY'
MINIO_KMS_KES_CAPATH=/etc/silo/certs/kes-ca.crt
MINIO_KMS_KES_KEY_NAME=silo-default
```

`MINIO_KMS_KES_CAPATH` is a CA file or directory on the SILO host, not a path inside the KES container. It can be omitted when the KES certificate chains to a CA already trusted by SILO. Multiple KES endpoints are comma-separated and must expose the same keys and policies.

The supplied unit reads `/etc/default/minio` first for migration compatibility and `/etc/default/silo` second. Use the file actually configured by your service manager. SILO itself loads an environment file only when `MINIO_CONFIG_ENV_FILE` selects one; see the [environment-file reference](/reference/minio-server/settings/core/#envvar.MINIO_CONFIG_ENV_FILE).

Do not also set the `MINIO_KMS_SERVER` or static-key variable groups. See [KES settings](/reference/minio-server/settings/kes/) for mutually exclusive authentication and backend settings.

### 4. Restart and Check the Deployment

Ensure KES and its key store are available, then apply the environment changes through your service manager on every node. For systemd, restart `silo.service` as part of a coordinated deployment restart. `mcli admin service restart` reuses the process environment; it does not make systemd reread an edited `EnvironmentFile`.

> [!WARNING]
> Once SILO has encrypted backend IAM/configuration data or objects, preserve the keys and a working decryption path. Removing the KES settings or losing the key store can make the deployment or its objects unreadable. Clearing a bucket's default encryption does not decrypt existing data.

### 5. Enable Bucket Encryption and Verify a Read

Using the configured `mysilo` alias and the keys above:

```shell
mcli mb mysilo/encryptedbucket
mcli encrypt set sse-kms silo-bucket mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
printf 'SILO encryption check\n' > encryption-check.txt
mcli cp encryption-check.txt mysilo/encryptedbucket/
mcli stat mysilo/encryptedbucket/encryption-check.txt
mcli cat mysilo/encryptedbucket/encryption-check.txt
```

Use `mcli encrypt set sse-s3 mysilo/encryptedbucket` to use the deployment's default key instead. Bucket defaults apply to new writes and do not retroactively encrypt existing objects. Test decryption again after restarting SILO and KES to avoid relying only on cached keys.

## Kubernetes Deployments

Run PGSTY KES as a separately managed service and expose its endpoint, credentials, and CA to the SILO pods using your platform's configuration and Secret mechanisms. Pin the SILO and KES images independently.

The retained [MinIO Operator guides](/operations/deployments/kubernetes/) describe the archived upstream `v7.1.1` compatibility snapshot. Operator Console was removed in `v6.0.0`; do not follow old Console encryption screens. The historical `TenantSpec.kes` examples do not by themselves validate PGSTY KES image permissions, certificate paths, or your Kubernetes deployment.
