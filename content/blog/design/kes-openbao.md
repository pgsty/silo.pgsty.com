---
title: "SILO, KES and OpenBao: Key Ownership and Recovery"
linkTitle: "KES and OpenBao"
date: 2026-10-18
lastmod: 2026-10-26
author: "SILO"
description: "Separate object encryption, key-service authorization and persistent root-key storage, with explicit upgrade and recovery checks."
tags: [Design, KES, Security, Operations]
weight: 1
draft: false
url: "/blog/design/kes-openbao/"
---

SILO integrates with external key-management systems through [PGSTY KES](https://github.com/pgsty/kes) (`MINIO_KMS_KES_ENDPOINT`). The current release is **[KES 20261026](/blog/release/silo-20261026/#kes)** (built with Go 1.27.3 and updated cloud dependencies while retaining the API, configuration, and key formats described below); the earlier [PGSTY KES 20261018](/blog/release/kes-20261018/) release (source [`2f7e741db905`](https://github.com/pgsty/kes/commit/2f7e741db905d7ea755967b29666657d819d7ad0)) migrated the KES AWS Secrets Manager backend to AWS SDK for Go v2 while preserving existing SILO/KES key formats and OpenBao KV v2 compatibility.

## Three services, three responsibilities {#architecture}

| Service | Owns | Calls |
| --- | --- | --- |
| SILO | Object bytes and object encryption metadata; encrypts/decrypts object contents | KES over HTTPS (mTLS) to generate/decrypt data keys |
| PGSTY KES | Application identities, key-access policies, and the key API; wraps/unwraps data keys | OpenBao KV v2 to store/retrieve root keys |
| OpenBao | Persistent KES root-key records, backend access control, and its own recovery material | Its configured storage backend |

```text
+-------------+       mTLS (KES API)       +-------------+    AppRole / TLS    +--------------------+
| SILO Server | -------------------------> |  PGSTY KES  | ------------------> | OpenBao (KV v1/v2) |
+-------------+  MINIO_KMS_KES_ENDPOINT    +-------------+   keystore.vault    +--------------------+
```

`MINIO_KMS_KES_ENDPOINT` must point to the **KES endpoint** because OpenBao does not implement the KES key-wrapping API. KES accesses OpenBao through its `keystore.vault` driver (`version: v2` for OpenBao KV v2 mounts). The same `kes` executable provides both the server and the administration CLI, and multiple stateless KES instances can share a single OpenBao backend.

SILO stores the encrypted data encryption key (DEK) alongside the object metadata. Because the object bucket does not contain the external master key, losing the root key in OpenBao renders encrypted objects unrecoverable even when every object shard on disk is intact.

Minimal KES configuration for OpenBao KV v2:

```yaml
address: 0.0.0.0:7373

admin:
  identity: ${KES_ADMIN_IDENTITY}

tls:
  key:  /etc/kes/kes-server.key
  cert: /etc/kes/kes-server.crt
  ca:   /etc/kes/client-ca.crt

policy:
  silo-server:
    allow:
      - /v1/key/create/*
      - /v1/key/generate/*
      - /v1/key/decrypt/*
      - /v1/key/describe/*
      - /v1/key/list/*
      - /v1/status
      - /v1/version
    identities:
      - ${SILO_CLIENT_CERT_IDENTITY}

keystore:
  vault:
    endpoint: https://openbao.internal:8200
    engine:   secret
    version:  v2
    prefix:   kes
    approle:
      engine: approle
      id:     ${OPENBAO_ROLE_ID}
      secret: ${OPENBAO_SECRET_ID}
      retry:  15s
    tls:
      ca: /etc/kes/openbao-ca.crt
```

Minimal OpenBao ACL policy for the KES AppRole on a KV v2 mount named `secret` with prefix `kes`:

```hcl
path "secret/data/kes/*" {
  capabilities = ["create", "read", "delete"]
}

path "secret/metadata/kes/*" {
  capabilities = ["list", "read", "delete"]
}
```

## Authentication and failure behavior {#failure}

Configure TLS trust on SILO → KES and KES → OpenBao separately. KES authorizes the SILO client certificate identity (`kes identity of <cert>`) for the required key names; OpenBao authorizes the KES AppRole backend identity.

| Layer / Configuration | Failure mode | Operational resolution |
| --- | --- | --- |
| OpenBao sealed or unreachable | Warm caches can allow some operations to continue temporarily, but uncached key lookups and fresh SILO restarts fail closed without falling back to plaintext storage. | Unseal OpenBao before starting or rolling SILO nodes, and verify recovery with a fresh process restart and actual object readback. |
| KV v1 vs KV v2 mismatch | Configuring `version: v1` against a KV v2 mount (or omitting `secret/data/...` and `secret/metadata/...` capabilities in the OpenBao ACL policy) returns `403 permission denied` or `404` on key creation and listing. | Set `engine: <mount>`, `version: v2`, and grant ACL capabilities on both `<mount>/data/<prefix>/*` and `<mount>/metadata/<prefix>/*`. |
| Client certificate rotation | Rotating `MINIO_KMS_KES_CERT_FILE` changes the SHA-256 certificate identity. If the new identity is not authorized in the KES policy before rollout, SILO fails KMS startup checks. | Authorize both old and new certificate identities in KES before rotating SILO client certificates, then remove the old identity after rollout completes. |

Keep persistent key-store backups, KES configuration, TLS trust roots, identity/policy definitions, and OpenBao recovery material under strict access control, and verify that backup restores preserve both key names and key material. Development mode keeps keys only in memory and must not be used for durable encrypted storage.

## SDK migration and compatibility {#sdk}

[PGSTY KES 20261018](/blog/release/kes-20261018/) (`2f7e741db905`) migrates `keystore/aws/secretsmanager` from the archived `github.com/aws/aws-sdk-go` (v1) to AWS SDK for Go v2 (`github.com/aws/aws-sdk-go-v2`, `config`, `credentials`, `service/secretsmanager`, and `github.com/aws/smithy-go`).

The migration preserves stored key formats and YAML configuration fields:
- Explicit credentials in the KES YAML configuration retain precedence; empty credential fields delegate to the standard SDK credential provider chain.
- KES does not load `~/.aws/config` implicitly, and the configured `endpoint` in KES configuration remains authoritative over SDK endpoint environment overrides.
- AWS Secrets Manager `ResourceNotFoundException`, `ResourceExistsException`, and invalid-parameter responses map to the same KES keystore errors (`errKeyNotFound`, `errKeyExists`).

The compatibility test matrix ([`testing/kms-compat.sh`](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh)) exercises OpenBao KV v2 and Moto Secrets Manager across `SDK-v1 -> SDK-v2 -> rollback` transitions, restarting SILO on each transition so cached keys are discarded before readback verification.

## Upgrade and recovery checks {#verification}

1. Record the SILO and KES versions, key names, backend endpoint, and client certificate identities. Retain existing keys and backend backups until recovery has been verified.
2. Read an existing encrypted object before upgrading and record its SHA-256 digest. Upgrade KES to the target [PGSTY KES 20261026](/blog/release/silo-20261026/#kes) binary against the same persistent backend.
3. Restart KES and SILO (clearing warm key caches), read the existing encrypted object, write a new encrypted object, and verify both digests using the deployment's production TLS identities and access policies.
4. In an isolated rehearsal, test restoring the prior KES binary against the same key store, restart both services, and repeat encrypted object readback.

For step-by-step configuration commands, see [Configure KES and OpenBao for Server-Side Encryption](/operations/server-side-encryption/configure-minio-kes/), the [KES reference configuration](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/server-config.yaml), and the [KES compatibility test suite](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh).
