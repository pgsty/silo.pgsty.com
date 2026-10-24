---
title: "SILO 20260903 Security Notes: SN-2026-006 through 010"
linkTitle: "20260903 · SN-006–010"
date: 2026-09-03
author: "Ruohang Feng"
description: "Five inherited server authorization and encryption findings fixed by SILO 20260903: SSE-C key authentication, replication-header trust, admin status authorization, and explicit-version deletion."
tags: [Security, S3, SSE-C, Replication, IAM]
weight: 8
draft: false
url: "/blog/security/20260903-server-hardening/"
---

This bulletin covers five security findings fixed in [SILO Server 20260903](/blog/release/silo-20260903/) ([`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z)), spanning customer-provided encryption keys (SSE-C), client-supplied replication headers, administrative status transitions, and explicit object-version deletion. `SN-2026-006` through `SN-2026-010` are SILO security-note identifiers grouping the pre-release audit findings inherited from the upstream `minio/minio` codebase.

## Summary {#summary}

| ID | Required attacker position | Security failure | Released behavior |
| :-- | :-- | :-- | :-- |
| `SN-2026-006` | Read access to a zero-byte SSE-C object | A wrong customer key was accepted because no data block was decrypted | The object key is authenticated; wrong keys return `403 AccessDenied` |
| `SN-2026-007` | Read access to an SSE-C object, or a client-supplied replication marker | `GetObjectAttributes` returned protected metadata without authenticating the customer key | Ordinary requests need the correct key; only an authorized replication peer uses the replica exception |
| `SN-2026-008` | Any authenticated principal able to invoke the affected read/write/delete operation | Internal-looking headers granted replication-only effects without replication authorization | Exact marker plus `s3:ReplicateObject` or `s3:ReplicateDelete` is required |
| `SN-2026-009` | Authenticated admin API principal holding only one status action | The enable action authorized disable, and vice versa | The requested target state selects the required admin action |
| `SN-2026-010` | Authenticated S3 principal with `s3:DeleteObject` but not `s3:DeleteObjectVersion` | A caller could permanently delete an explicit version without the AWS-required action | Explicit version deletion requires `s3:DeleteObjectVersion` |

## SN-2026-006: zero-byte SSE-C key authentication {#sn-2026-006}

**Affected operations:** `GetObject`, `HeadObject`, `CopyObject` source processing, and `GetObjectAttributes` for zero-byte objects encrypted with SSE-C.<br>
**Tracking:** [issue #82](https://github.com/pgsty/silo/issues/82).<br>
**Fixes:** `b73581b05` and `c4fd97d0b`.

SSE-C stores a sealed object key and requires the caller to supply the matching customer key on reads. Normal reads authenticate that key while preparing the encrypted payload stream. Because a zero-byte object has no payload block, the legacy fast path returned before unsealing the stored object key.

As a result, an authenticated caller with read access to a zero-byte SSE-C object could receive a successful response while supplying an incorrect customer key, or copy the object under a newly chosen key without proving knowledge of the original key.

The fix authenticates the stored SSE-C key regardless of payload length. Valid keys succeed as before; wrong keys fail with `403 AccessDenied`, including null-version and key-rotation paths.

## SN-2026-007: SSE-C GetObjectAttributes {#sn-2026-007}

**Affected operation:** `GetObjectAttributes` on SSE-C objects.<br>
**Tracking:** [issue #84](https://github.com/pgsty/silo/issues/84).<br>
**Fixes:** `474cd5801`, `74c97d005`, and `21870fa2e`.

`GetObjectAttributes` exposes object size, ETag, checksums, storage class, and multipart part metadata. The inherited handler returned those attributes without authenticating the supplied SSE-C key, and also treated the raw `X-Minio-Source-Replication-Request` header as permission to skip key verification.

The fix enforces two distinct rules:

- an ordinary S3 caller must supply the valid SSE-C customer key (wrong or missing keys return `403 AccessDenied`);
- a replication peer may use the replica metadata path only after passing authentication and `s3:ReplicateObject` authorization.

## SN-2026-008: replication headers are not authority {#sn-2026-008}

**Affected surface:** object reads and writes, multipart completion, object and version deletion, Snowball extraction, Object Lock timestamps, checksum metadata, and bucket events.<br>
**Tracking:** [PR #101](https://github.com/pgsty/silo/pull/101).<br>
**Primary fix range:** `938603458` through `04b097fd9`, followed by Snowball and rule-prefix hardening.

While [CVE-2026-34204](/blog/security/cve-2026-34204/) blocked ordinary `PUT` and `COPY` requests from importing a subset of replication SSE metadata, a wider audit showed that several downstream handlers still treated the presence of internal replication headers as proof of a trusted replication request.

Depending on the operation, a caller holding ordinary read or write permissions could:

- trigger an SSE-C no-decryption read path without supplying the customer key;
- preserve a client-supplied source ETag or `MTime`;
- inject source checksum, actual-size, retention, legal-hold, or `REPLICA` status metadata;
- invoke replication-only delete semantics;
- suppress bucket notification events;
- carry replication trust across Snowball archive entries.

The fix establishes a single receiver-wide trust calculation:

1. authenticate the incoming request in its original signed form;
2. require a single `X-Minio-Source-Replication-Request` header with the exact lowercase value `true`;
3. authorize `s3:ReplicateObject` or `s3:ReplicateDelete` on the target resource;
4. grant `replicaTrusted` only when the authenticated replication status also equals `REPLICA`;
5. bind the trust decision to a private `req.Context()` key;
6. strip untrusted internal replication headers on a post-authentication request clone while preserving the trailer map for streaming checksum verification.

See [No I/O Before Auth, No Privilege From Headers](/blog/design/cors-replication-trust/) for the full protocol matrix, CORS interaction, black-box two-site replication verification, and rejected alternatives.

## SN-2026-009: user and group status authorization {#sn-2026-009}

**Affected operations:** admin `SetUserStatus` and `SetGroupStatus`.<br>
**Tracking:** [PR #73](https://github.com/pgsty/silo/pull/73) / [PR #85](https://github.com/pgsty/silo/pull/85).<br>
**Fixes:** `58735ee38` and `229fe2b3c`.

The inherited handlers checked `admin:EnableUser` or `admin:EnableGroup` before inspecting the requested `status` parameter. A delegated administrator permitted only to enable accounts could therefore disable them as well, while an administrator granted only `admin:DisableUser` or `admin:DisableGroup` was rejected.

The requested target state now selects the required admin action:

| Target | Required action |
| :-- | :-- |
| Enable user | `admin:EnableUser` |
| Disable user | `admin:DisableUser` |
| Enable group | `admin:EnableGroup` |
| Disable group | `admin:DisableGroup` |

`admin:*` and the built-in `consoleAdmin` policy remain unchanged; only custom least-privilege policies that relied on `EnableUser`/`EnableGroup` to perform both transitions require updating.

## SN-2026-010: explicit object-version deletion {#sn-2026-010}

**Affected operations:** `DeleteObject` and each `DeleteObjects` entry carrying an explicit `versionId`.<br>
**Tracking:** [issue #58](https://github.com/pgsty/silo/issues/58) and [PR #104](https://github.com/pgsty/silo/pull/104).<br>
**Fix range:** `75a6734e4` through `d2d47a41f`.

Previously, the S3 delete handlers authorized explicit-version deletion under `s3:DeleteObject` and checked `s3:DeleteObjectVersion` only as a secondary deny filter, allowing callers with `s3:DeleteObject` alone to permanently delete historical versions.

Server `20260903` requires `s3:DeleteObjectVersion` whenever a `versionId` is specified. Unversioned `DELETE` requests continue to check `s3:DeleteObject`, and replication targets continue to check `s3:ReplicateDelete`. Callers granted only `s3:DeleteObject` can no longer delete explicit versions, and policies that pair `Allow s3:*` with `Deny s3:DeleteObject` to prevent permanent deletion must also deny `s3:DeleteObjectVersion`.

## Operator actions {#operator-actions}

Before upgrading:

1. identify policies and applications that delete explicit object versions and grant or deny `s3:DeleteObjectVersion` explicitly;
2. inspect custom admin policies for user and group enable/disable operations;
3. confirm that replication service accounts hold `s3:ReplicateObject` / `s3:ReplicateDelete` and that ordinary application identities do not;
4. verify that SSE-C clients send the matching customer key on `GET`, `HEAD`, `GetObjectAttributes`, and `CopyObject` source reads, including zero-byte objects.

After upgrading:

- verify both wrong-key (`403 AccessDenied`) and valid-key responses on a test SSE-C object;
- test object and delete replication across paired sites;
- test delegated user/group enable and disable permissions independently;
- verify explicit-version deletion with principals holding `s3:DeleteObject` alone vs. `s3:DeleteObjectVersion`.

## Verification boundary {#verification}

All five fixes are covered by unit, handler, authorization, streaming-trailer, Snowball, and site-replication regression tests. Full local acceptance on `ebac0ca73` passed the `cmd` race suite and 174 test cases across six deployment topologies (174 PASS / 0 FAIL), followed by the [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) release gates documented in the [pre-release review](/blog/design/server-release-readiness/#decision).

## Residual risks outside this bulletin {#residual-risks}

- Conditional deletion (`If-Match` on `DeleteObject` and per-object ETag on `DeleteObjects`, [#10](https://github.com/pgsty/silo/issues/10)) and bucket-metadata deletion convergence across site-replication peers ([#77](https://github.com/pgsty/silo/issues/77)) are tracked separately; see the [Server 20260903 release notes](/blog/release/silo-20260903/#known-issues) and [Server 20260916 release notes](/blog/release/silo-20260916/).
