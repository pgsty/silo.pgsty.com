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

> **Released in SILO 20260903.** These fixes are part of [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z). See the [complete release notes](/blog/release/silo-20260903/) for the 20260806-to-20260903 upgrade boundary, components, verification evidence, and known deferrals.

This bulletin collects five related security findings from the final SILO Server review. They cover customer-provided encryption keys, client-controlled replication headers, administrative status changes, and explicit object-version deletion.

The identifiers `SN-2026-006` through `SN-2026-010` are fork-local security-note IDs. They are **not CVEs**, are not registered in a vulnerability database, and should not be represented as such. The individual CVE chronicle remains one article per CVE; this release bulletin groups findings without CVEs so operators can evaluate one upgrade boundary.

All five defects were inherited from the archived `minio/minio` lineage and affect every earlier SILO release. “Inherited” describes provenance, not severity.

## Summary {#summary}

| ID | Required attacker position | Security failure | Released behavior |
| :-- | :-- | :-- | :-- |
| `SN-2026-006` | Read access to a zero-byte SSE-C object | A wrong customer key was accepted because no data block was decrypted | The object key is authenticated; wrong keys return `403 AccessDenied` |
| `SN-2026-007` | Read access to an SSE-C object, or a client-supplied replication marker | `GetObjectAttributes` returned protected metadata without authenticating the customer key | Ordinary requests need the correct key; only an authorized replication peer uses the replica exception |
| `SN-2026-008` | Any authenticated principal able to invoke the affected read/write/delete operation | Internal-looking headers granted replication-only effects without replication authorization | Exact marker plus `s3:ReplicateObject` or `s3:ReplicateDelete` is required |
| `SN-2026-009` | Authenticated admin API principal holding only one status action | The enable action authorized disable, and vice versa | The requested target state selects the required admin action |
| `SN-2026-010` | Authenticated S3 principal with `s3:DeleteObject` but not `s3:DeleteObjectVersion` | A caller could permanently delete an explicit version without the AWS-required action | Explicit version deletion requires `s3:DeleteObjectVersion` |

No finding in this bulletin is an unauthenticated remote-code-execution claim. Each requires an authenticated identity or existing object permission, but each crosses a privilege or cryptographic boundary beyond that identity's intended grant.

## SN-2026-006: zero-byte SSE-C key authentication {#sn-2026-006}

**Affected operations:** `GetObject`, `HeadObject`, `CopyObject` source processing, and `GetObjectAttributes` for zero-byte objects encrypted with SSE-C.<br>
**Tracking:** [issue #82](https://github.com/pgsty/silo/issues/82).<br>
**Fixes:** `b73581b05` and `c4fd97d0b`.

SSE-C stores a sealed object key and requires the caller to provide the customer key again on reads. Normal reads authenticate that key while preparing the encrypted stream. A zero-byte object has no payload block, and the old fast path returned before unsealing the stored object key.

Consequently, an incorrect customer key could receive a successful response. A copy or new version could also be created under a key chosen by the caller without proving knowledge of the current key. The caller still needed read access to the object; the failure was that object permission replaced the separate cryptographic proof.

The fix authenticates the key independent of payload length. Correct keys behave as before. Wrong keys fail with `403 AccessDenied`, including null-version and key-rotation cases.

## SN-2026-007: SSE-C GetObjectAttributes {#sn-2026-007}

**Affected operation:** `GetObjectAttributes` on SSE-C objects.<br>
**Tracking:** [issue #84](https://github.com/pgsty/silo/issues/84).<br>
**Fixes:** `474cd5801`, `74c97d005`, and `21870fa2e`.

`GetObjectAttributes` exposes object size, ETag, checksums, storage class, and multipart part metadata. The inherited handler returned those attributes without authenticating the supplied SSE-C key. It also treated the presence of `X-Minio-Source-Replication-Request` as permission to skip key handling.

The repair separates two cases:

- an ordinary S3 caller must supply the correct SSE-C key;
- a real replication peer may use the replica path only after authentication and `s3:ReplicateObject` authorization.

A wrong key now returns `403`. A bare marker without the required key and permission cannot create the replica exception. Existing replication identities that already hold the required action keep working.

## SN-2026-008: replication headers are not authority {#sn-2026-008}

**Affected surface:** object reads and writes, multipart completion, object and version deletion, Snowball extraction, Object Lock timestamps, checksum metadata, and bucket events.<br>
**Tracking:** [PR #101](https://github.com/pgsty/silo/pull/101).<br>
**Primary fix range:** `938603458` through `04b097fd9`, followed by Snowball and rule-prefix hardening.

[CVE-2026-34204](/blog/security/cve-2026-34204/) stopped ordinary PUT and COPY requests from importing a subset of replication SSE metadata. The wider audit found that many other consumers still treated header presence as proof that a request was internal replication.

Depending on the operation, a client holding ordinary read or write permission could:

- request an SSE-C ciphertext/no-decryption path without the customer key;
- preserve a supplied source ETag or modification time;
- inject source checksum, actual-size, retention, legal-hold, or replica-state metadata;
- choose replication-only delete semantics;
- suppress successful object events;
- carry trust from one Snowball archive entry into another.

The repair defines one receiver-wide authority:

1. authenticate the original request in its signed form;
2. require exactly one marker with the exact lowercase value `true`;
3. authorize `s3:ReplicateObject` or `s3:ReplicateDelete` on the addressed resource;
4. derive a narrower replica-trusted state only where replica status also proves it;
5. store the decision in private request context;
6. strip untrusted internal headers from a clone after authentication.

The context decision is authoritative. Stripping protects older consumers but cannot itself grant trust. The clone preserves the original trailer map so streaming checksum authentication remains correct.

The detailed protocol matrix, CORS interaction, black-box replication test, and rejected alternatives are in [No I/O Before Auth, No Privilege From Headers](/blog/design/cors-replication-trust/).

## SN-2026-009: user and group status authorization {#sn-2026-009}

**Affected operations:** admin `SetUserStatus` and `SetGroupStatus`.<br>
**Tracking:** [PR #73](https://github.com/pgsty/silo/pull/73).<br>
**Fixes:** `58735ee38` and `229fe2b3c`.

The inherited handlers checked `admin:EnableUser` or `admin:EnableGroup` regardless of the target state. A narrowly delegated administrator permitted to enable an identity could therefore disable it too; an identity intended to hold only the disable action could fail or be evaluated against the wrong grant.

The requested state now determines the required action:

| Target | Required action |
| :-- | :-- |
| Enable user | `admin:EnableUser` |
| Disable user | `admin:DisableUser` |
| Enable group | `admin:EnableGroup` |
| Disable group | `admin:DisableGroup` |

`admin:*` and the built-in `consoleAdmin` policy remain sufficient. Only custom least-privilege policies that accidentally relied on one action for both directions need adjustment.

## SN-2026-010: explicit object-version deletion {#sn-2026-010}

**Affected operations:** `DeleteObject` and each `DeleteObjects` entry carrying an explicit `versionId`.<br>
**Tracking:** [issue #58](https://github.com/pgsty/silo/issues/58) and [PR #104](https://github.com/pgsty/silo/pull/104).<br>
**Fix range:** `75a6734e4` through `d2d47a41f`.

The inherited S3 path authorized explicit version deletion as ordinary `s3:DeleteObject` and used `s3:DeleteObjectVersion` only as a secondary deny check. This diverged from AWS and let a principal with ordinary delete permission permanently remove a selected historical version.

The release requires `s3:DeleteObjectVersion` for explicit versions. A delete without `versionId` continues to use `s3:DeleteObject`. Replication targets keep their `s3:ReplicateDelete` contract.

There are two policy effects:

1. a principal granted only `s3:DeleteObject` can no longer delete explicit versions;
2. a policy using `Allow s3:*` together with `Deny s3:DeleteObject` to block permanent deletion must also deny `s3:DeleteObjectVersion`.

The multi-delete repair preserves authentication and audit context for every entry and has least-privilege tests for ordinary and replication deletes.

## Operator actions {#operator-actions}

Before upgrading:

1. identify policies and applications that delete explicit versions; grant or deny `s3:DeleteObjectVersion` intentionally;
2. inspect custom admin policies for enable/disable user and group operations;
3. confirm that replication service accounts have only the required `s3:ReplicateObject` / `s3:ReplicateDelete` actions and that ordinary application identities do not;
4. verify SSE-C integrations send the same customer key for GET, HEAD, attributes, and copy-source operations, including zero-byte objects;
5. if an application was relying on a wrong SSE-C key returning success, treat that as a latent client defect and correct it before rollout.

After upgrading:

- exercise a wrong-key negative test and a correct-key positive test on a disposable SSE-C object;
- test one normal replication and one delete replication operation;
- test each delegated admin direction independently;
- test version deletion with a principal that has only `s3:DeleteObject` and with one that also has `s3:DeleteObjectVersion`;
- review audit logs for unexpected denied operations instead of widening policies immediately.

## Verification boundary {#verification}

The fixes have focused unit, handler, authorization, streaming-trailer, Snowball, and site-replication tests. Full local acceptance on `ebac0ca73` included the complete `cmd` race suite and six deployment shapes with 174 PASS / 0 FAIL. The final line adds one CORS state-clear fix after that run and passes targeted race, compatibility, generation, diff, and lint gates.

The final [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) publication completed the gates recorded in the [pre-release review](/blog/design/server-release-readiness/#decision): exact-SHA CI and Test Release, signed packages, checksums, SBOMs, provenance, and public classic/distroless container images. This bulletin still scopes its claims to the five fixes above and the residual risks below.

## Residual risks outside this bulletin {#residual-risks}

- Conditional deletion is still unsupported: `DeleteObject` ignores `If-Match` and `DeleteObjects` ignores per-object ETag ([#10](https://github.com/pgsty/silo/issues/10)).
- Non-CORS policy/SSE/tag/quota deletions may not converge across site-replication peers ([#77](https://github.com/pgsty/silo/issues/77)).
- The trust audit focused on known replication and SSE-C fields. New internal headers must still answer the same provenance-and-authorization question during review.

The release notes contain the full [known-issue and deployment boundary](/blog/release/silo-20260903/#known-issues).
