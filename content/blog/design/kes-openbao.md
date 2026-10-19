---
title: "SILO, KES and OpenBao: Key Ownership and Recovery"
linkTitle: "KES and OpenBao"
date: 2026-10-18
lastmod: 2026-10-18
author: "SILO"
description: "Separate object encryption, key-service authorization and persistent root-key storage, with explicit upgrade and recovery checks."
tags: [Design, KES, Security, Operations]
weight: 1
draft: false
url: "/blog/design/kes-openbao/"
---

**Released implementation:** [PGSTY KES 20261018](/blog/release/kes-20261018/), source [`2f7e741db905`](https://github.com/pgsty/kes/commit/2f7e741db905d7ea755967b29666657d819d7ad0). KES is optional and deployed independently of the four-component SILO build graph. Existing SILO/KES users can adopt it without rewriting objects or migrating keys.

## Three services, three responsibilities {#architecture}

| Service | Owns | Calls |
| --- | --- | --- |
| SILO | Object bytes and object encryption metadata; encrypts/decrypts object contents | KES over HTTPS to generate/decrypt data keys |
| PGSTY KES | Application identities, key-access policies and the key API; wraps/unwraps data keys | OpenBao KV v2 to store/retrieve root keys |
| OpenBao | Persistent KES root-key records, backend access control and its own recovery material | Its configured storage backend |

`MINIO_KMS_KES_ENDPOINT` must name the **KES endpoint**. OpenBao does not implement that API. KES accesses OpenBao through its existing `keystore.vault` configuration; OpenBao is not a replacement for the KES process. The same `kes` executable provides the service and administration CLI. Multiple KES instances can use the same external key store, with suitable identities and policies.

SILO stores the encrypted data key with the object metadata. The object bucket is not a backup of the external root key. Losing the required root key can make encrypted objects unrecoverable even when every object shard remains intact.

## Authentication and failure behavior {#failure}

Configure TLS trust on SILO → KES and KES → OpenBao separately. KES authorizes the SILO identity for the required key names; OpenBao authorizes the KES backend identity. The OpenBao backend credentials belong to KES configuration, not to an S3 client.

Caches can allow some operations to continue temporarily during a backend interruption. A successful read while caches are warm does not prove that the key store is available or that a fresh process can decrypt the data. When an operation requires an unavailable key, encryption/decryption fails; it does not fall back to storing plaintext. Verify recovery with new processes and actual object readback.

Keep persistent key-store backups, KES configuration, TLS trust, identity/policy configuration and OpenBao recovery material under appropriate access control. Test that recovery preserves the same key values and names. Development mode keeps keys in memory and is unsuitable for durable encrypted storage.

## SDK migration and compatibility {#sdk}

The October KES release moves Secrets Manager to AWS SDK for Go v2. It preserves stored key formats and YAML fields. Explicit credentials retain precedence; empty credentials use the SDK credential providers. KES does not start loading `~/.aws/config`, and the configured endpoint remains authoritative over SDK endpoint environment overrides. No new AWS endpoint setting is required for existing configurations.

The acceptance matrix exercises OpenBao KV v2 and Moto Secrets Manager, including SDK-v1 → SDK-v2 → rollback transitions. Each transition restarts SILO to discard cached keys. Moto demonstrates local protocol and storage compatibility; it does not certify real AWS IAM, endpoint policies or service behavior. Other inherited KES backends are outside this matrix.

## Upgrade and recovery checks {#verification}

1. Record the SILO and KES versions, key names, backend endpoint and backup identity. Keep the existing keys and backup until recovery has been demonstrated.
2. Read an existing encrypted object before the change and retain its expected digest. Replace KES with the fixed PGSTY version using the same persistent backend.
3. Restart KES and SILO, read the old object, write a new encrypted object and verify both digests. Exercise the actual TLS identities and access policies used by the deployment.
4. In an isolated rehearsal, restore the prior KES binary against the same compatible key store, restart both services and repeat readback. A binary rollback does not restore deleted keys or replace a key-store recovery procedure.

The KES release tested SILO 20260903 and 20260916. The final Server 20261018 local encryption tests used a test KMS key, so they are separate from this external-KES matrix. Validate the complete versions selected for your deployment. Source: [KES compatibility tests](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh), [configuration](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/server-config.yaml), [release scope](/blog/release/kes-20261018/#delivery).
