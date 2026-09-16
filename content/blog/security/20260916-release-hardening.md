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

This record covers three repairs and their delivery boundaries as of September 16.
The identifiers are SILO-local advisory numbers, not CVEs or assigned CVSS scores.
The [security ledger](/about/security-advisories/) is the maintained index.

| Finding | Fixed source | Published delivery on September 16 |
| --- | --- | --- |
| SN-2026-012: presigned payload integrity | Server `c4b5e1cb4`, PR #177 | Not in Server `RELEASE.2026-09-03T13-18-01Z`; awaiting a later Server release |
| SN-2026-013: durable IAM revocation | Server PR #191 / #192 | Not in Server 20260903; coordinated upgrade required |
| SN-2026-014: anonymous Console share proxy | Console PR #56; Server PR #209 selects the repair | Standalone Console v2.4.1 is published; the embedded copy still requires a new Server binary |

## Presigned payload integrity — SN-2026-012 {#sn-2026-012}

The generic authenticated path could verify a presigned request using a payload
hash supplied only in `X-Amz-Content-Sha256`, yet omit checking the actual body
against that hash. A holder of a suitably signed write URL could replace its
body. The committed regression demonstrates this with `PutBucketPolicy`;
this is not a claim that an anonymous caller can write arbitrary bucket policies.

[`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4) in
[PR #177](https://github.com/pgsty/silo/pull/177) binds body validation to the
effective signed hash; mismatches fail with `XAmzContentSHA256Mismatch` (400).
An explicit signed `UNSIGNED-PAYLOAD` retains its intended meaning. The adjacent
signed-field fixes align policy conditions with authenticated values and remove
the `X-Amz-Signature-Age` scratch header. They complement
[SN-2026-011](/blog/design/signed-header-coverage/); they do not establish complete
unsigned-header coverage for streaming SigV4.

Review custom signing clients before upgrading. Query hash values take precedence
over the fallback header, so changing an unsigned header must not change what
policy evaluation or body validation sees.

## Durable IAM revocation — SN-2026-013 {#sn-2026-013}

Delayed replication events, parent recreation and lost deletion history could
restore identities or grants an operator had revoked. [PR #191](https://github.com/pgsty/silo/pull/191)
and [PR #192](https://github.com/pgsty/silo/pull/192) retain source revisions,
deletion tombstones and signed parent-revocation boundaries. Older events and
child credentials cannot silently cross a retained revocation boundary.

This is a persistent-state change. Upgrade all sites and all nodes sharing an
IAM backend together; mixed old/new nodes and rolling downgrade are unsupported.
`mcli admin cluster iam export` omits deletion history and is not a complete
recovery backup. Preserve a tested full-backend recovery point and reconcile
known earlier revocations. Tombstones have no TTL or automatic compaction.

The [design record](/blog/design/iam-revocations/) documents ordering, remaining
group-membership limitations and metrics. Follow the
[upgrade and recovery procedure](/operations/replication/iam-upgrade/), including
the password-policy pre-step. A revocation can commit and then return HTTP 500
if cleanup fails; the response alone does not prove that the old credential is valid.

## Anonymous Console share proxy — SN-2026-014 {#sn-2026-014}

Jiri Pejchal reported that the unauthenticated shared-download proxy accepted
URLs beyond the intended object-download surface on its configured Server
origin. This is a same-origin proxy-boundary issue; it is not evidence of
arbitrary-host SSRF or bypass of the Server's S3 authorization.

[Console #56](https://github.com/pgsty/silo-console/pull/56) constrains scheme,
host and port, requires a valid bucket/object path, rejects system and traversal
paths and operation-changing query selectors, disables redirects, and propagates
caller cancellation. Accepted object URLs retain their original signed bytes.

Upgrade a standalone installation to [Console v2.4.1](/blog/release/console-2.4.1/).
[Server #209](https://github.com/pgsty/silo/pull/209) selects the fixed Console
source on main, but installing a separate Console cannot patch the UI and proxy
compiled into Server 20260903. Until an appropriate Server artifact is available,
limit exposure of the affected Console share endpoint according to the deployment.

## Adjacent dependency hardening {#dependencies}

Server main upgrades `amqp091-go` to v1.14.0 for
[GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp), fixed
upstream in v1.13.0. A malicious AMQP peer can trigger excessive allocation;
the SILO path requires a configured AMQP notification target. This Server change
also awaits a release after 20260903. [pkg v3.14.1](/blog/release/pkg-3.14.1/)
separately ships the JWX JSON encoding update. Component publication and Server
dependency adoption are separate facts.
