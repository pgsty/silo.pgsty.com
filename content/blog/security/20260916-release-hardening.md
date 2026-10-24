---
title: "September Security Repairs: Payload Integrity, IAM Revocation and Console Sharing"
linkTitle: "September security repairs"
date: 2026-09-16
author: "Vonng"
description: "SN-2026-012 through SN-2026-014, with distinct Server source and Console release boundaries."
tags: [Security, SigV4, IAM, Console]
weight: 1
url: "/blog/security/20260916-release-hardening/"
---

This bulletin covers three security repairs (`SN-2026-012` through `SN-2026-014`) and adjacent dependency updates shipped in [Server 20260916](/blog/release/silo-20260916/) and [Console v2.4.1](/blog/release/console-2.4.1/). See the [security advisory ledger](/about/security-advisories/) for the complete index.

| Finding | Fixed source | Delivery status |
| --- | --- | --- |
| `SN-2026-012`: presigned payload integrity | Server `c4b5e1cb4`, [PR #177](https://github.com/pgsty/silo/pull/177) | Shipped in [Server 20260916](/blog/release/silo-20260916/) (affected in `RELEASE.2026-09-03T13-18-01Z` and earlier) |
| `SN-2026-013`: durable IAM revocation | Server [PR #191](https://github.com/pgsty/silo/pull/191) / [PR #192](https://github.com/pgsty/silo/pull/192) | Shipped in [Server 20260916](/blog/release/silo-20260916/); requires coordinated multi-node/multi-site upgrade |
| `SN-2026-014`: anonymous Console share proxy | [Console PR #56](https://github.com/pgsty/silo-console/pull/56); [Server PR #209](https://github.com/pgsty/silo/pull/209) | Shipped in standalone [Console v2.4.1](/blog/release/console-2.4.1/) and embedded in [Server 20260916](/blog/release/silo-20260916/) |

## Presigned payload integrity — SN-2026-012 {#sn-2026-012}

The generic authenticated handler path could verify a presigned request using a payload digest supplied via the `X-Amz-Content-Sha256` header without verifying the actual request body bytes against that digest. A caller holding a presigned write URL could therefore substitute a different request body (the regression suite reproduces this against presigned `PutBucketPolicy`).

Commit [`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4) in [PR #177](https://github.com/pgsty/silo/pull/177) binds body digest verification to the effective signed payload hash; any mismatch fails with `XAmzContentSHA256Mismatch` (`400 Bad Request`). An explicitly signed `UNSIGNED-PAYLOAD` token retains its standard meaning. The same PR also ensures IAM policy condition evaluation reads the authenticated signed values (with signed query parameters taking precedence over fallback headers) and removes the internal `X-Amz-Signature-Age` scratch header, complementing [SN-2026-011](/blog/design/signed-header-coverage/).

Before upgrading, verify that custom SigV4 presigning clients send body payloads matching any signed `X-Amz-Content-Sha256` digest.

## Durable IAM revocation — SN-2026-013 {#sn-2026-013}

Previously, delayed site-replication events, parent account recreation, or missing deletion history could resurrect identities or policy grants that an administrator had already deleted or revoked. [PR #191](https://github.com/pgsty/silo/pull/191) and [PR #192](https://github.com/pgsty/silo/pull/192) persist monotonic source revisions, deletion tombstones, and parent-revocation epochs embedded in child credentials so stale replication events and pre-revocation child tokens are rejected.

Because this change introduces persistent IAM revision and tombstone records:

- Upgrade all nodes sharing an IAM backend and all participating replication sites together; mixed-version operation and rolling downgrades are not supported.
- `mcli admin cluster iam export` exports active records only and omits deletion tombstones; maintain a full backend snapshot and follow the [IAM upgrade and recovery guide](/operations/replication/iam-upgrade/).
- See the [IAM revocation design note](/blog/design/iam-revocations/) for revision ordering, metrics, and group-membership scope.

## Anonymous Console share proxy — SN-2026-014 {#sn-2026-014}

Jiri Pejchal reported that the unauthenticated Console shared-download proxy accepted URLs pointing to the configured Server origin outside the intended presigned object-download surface.

[Console PR #56](https://github.com/pgsty/silo-console/pull/56) restricts scheme, host, and port to the configured S3 origin, requires a valid `/{bucket}/{object}` path, rejects reserved system prefixes, path traversal segments, and operation-changing query parameters, disables upstream HTTP redirects, and forwards caller context cancellation while preserving the exact signed URL bytes for valid object downloads.

Upgrade standalone Console deployments to [Console v2.4.1](/blog/release/console-2.4.1/), and upgrade SILO Server deployments (which embed Console via [Server PR #209](https://github.com/pgsty/silo/pull/209)) to [Server 20260916](/blog/release/silo-20260916/).

## Adjacent dependency hardening {#dependencies}

[Server 20260916](/blog/release/silo-20260916/) upgrades `github.com/rabbitmq/amqp091-go` to `v1.14.0` to address [GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp) (fixed upstream in `v1.13.0`), where a malicious AMQP broker could trigger excessive memory allocation when an AMQP bucket notification target is configured. It also adopts [silo-pkg v3.14.1](/blog/release/pkg-3.14.1/) with the updated JWX JSON encoding dependency.
