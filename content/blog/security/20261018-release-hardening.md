---
title: "October Security Update: Object Lock, Admin Credentials and JWK Parsing"
linkTitle: "20261018 Security Update"
date: 2026-10-18
lastmod: 2026-10-19
author: "SILO"
description: "SN-2026-015/016 delivery, SN-2026-017 Admin authorization, dependency updates and the concrete upgrade impact of Server 20261018."
tags: [Security, IAM, Object Lock, silo]
weight: 1
url: "/blog/security/20261018-release-hardening/"
---

[SILO Server 20261018](/blog/release/silo-20261018/) delivers the fixes for **`SN-2026-015`**, **`SN-2026-016`**, and **`SN-2026-017`**, scoped STS token revocation, and Go toolchain and dependency updates across `silo`, `mcli`, and `silo-console`. Server `20260916` and `20260903` are affected (and `20261015` was a superseded pre-release draft).

## Object Lock: SN-2026-015 and SN-2026-016 {#object-lock}

The [SN-2026-015 & SN-2026-016 advisory](/blog/security/20260926-governance-retention-bypass/) and [repair design note](/blog/design/governance-retention-bypass-repair/) document the affected `PutObjectRetention` and in-place version overwrite paths, reproductions, and mitigations. [PR #234](https://github.com/pgsty/silo/pull/234) (`14042b5aa`) and [PR #235](https://github.com/pgsty/silo/pull/235) (`0d3ba5d4c`) enforce `s3:PutObjectRetention` before object lookup, require both `x-amz-bypass-governance-retention: true` and `s3:BypassGovernanceRetention` when weakening active `GOVERNANCE` retention, and reject caller-addressed `?versionId=` overwrites while enforcing WORM checks under the object write lock for `null`-version overwrites.

Every cluster and replication site that accepts S3 writes must be upgraded to `20261018`.

## SN-2026-017: Admin credential authorization boundaries {#sn-2026-017}

`SN-2026-017` groups the authenticated Admin API handler authorization defects fixed in [PR #242](https://github.com/pgsty/silo/pull/242) (commit [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)) and its bulk access-key listing follow-up [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8).

| Boundary | Before `20261018` | `20261018` Behavior |
| --- | --- | --- |
| Self inspection and cleanup | Ownership could override an explicit policy or plugin denial; self service-account listing could skip authorization | Preserves self-service access for ordinary users (`DenyOnly`), while enforcing explicit user/group `Deny` rules, inline session policies, and external plugin denials |
| Restricted credential delegation | A derived credential allowed the create/update action could mint a key inheriting broader parent permissions or strip a target service account's session policy | Under built-in authorization, callers constrained by an active inline session policy cannot create or update service accounts (including LDAP creation and metadata-only updates) |
| Root-derived credentials | A non-root administrator with broad `admin:*` grants could inspect, modify, or delete root's derived service accounts | Only an authorized root credential or an unrestricted root-derived identity can manage root-owned credentials (the internal site-replication account is excluded) |

The actor passed to IAM policy evaluation is always the authenticated access key (`cred.AccessKey`), while parent resolution (`ParentUser`) is used only for comparing ownership. Full handler contracts and benchmark measurements are recorded in [IAM Admin API Authorization Boundaries](/blog/design/iam-admin-authorization/).

### Compatibility repairs retained alongside the security fix {#compatibility}

- **Semantic empty policy normalization on issuance**: Creating a service account filters reserved parent policy/expiration claims and normalizes semantic empty policy documents (`null`, `{}`, `{"Statement":null}`) to parent inheritance, while preserving explicit empty statement arrays (`{"Version":"2012-10-17","Statement":[]}`).
- **Damaged non-root key cleanup**: Deleting or inspecting a damaged non-root service account falls back to stored identity metadata so operators can clean up corrupted or expired keys without allowing a damaged token to mask a root parent.
- **Bulk access-key listing ([`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8))**: Applies the same self-service authorization helper to bulk key listing (`ListAccessKeysBulk`), resolving omitted users, the caller's own key, or its parent to the caller's parent inventory while enforcing explicit denies and cross-user restrictions.
- **Error codes**: Denied self-service operations return `403 AccessDenied`; unauthorized attempts to delete another user's or root's service account retain their `404` response.

### Operator action {#operations}

1. Verify administrative automation using your production user, service-account, STS, and external-plugin identities. Any script that relied on a session-restricted credential to create further child service accounts, or a non-root admin to manage root service accounts, must switch to an unrestricted parent or root identity.
2. Audit child service accounts and policy updates created prior to upgrading, revoke unexpected keys, and follow the [IAM upgrade and recovery guide](/operations/replication/iam-upgrade/).

## Follow-up: scoped STS revocation {#sts-revocation}

Release commit [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) fixes cache-only `RevokeTokens` enumeration and incomplete propagation across peer nodes and sites. It persists deletion tombstones for tokens durably known to the cluster—scoped by parent identity, token type, and operation cutoff timestamp—and propagates them through peer notification and deletion healing. See [Scoped STS Revocation](/blog/design/iam-revocations/#scoped-sts-20261018) and the [Server 20261018 release notes](/blog/release/silo-20261018/#delivery).

## Dependency security and login compatibility {#dependencies}

Server `20261018` builds with Go **1.27.2**, `golang.org/x/net` **v0.61.0**, `golang.org/x/crypto` **v0.58.0**, `golang.org/x/text` **v0.43.0**, `silo-pkg` **v3.14.3**, and `go-jose` **v4.1.6** in [`go.mod`](https://github.com/pgsty/silo/blob/0cd388c666f8211f552604ae73448a066e9c25ce/go.mod):

- **`go-jose` v4.1.6 ([GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q))**: Bounds CPU consumption when parsing crafted RSA JWKs on the OIDC path and rejects RSA JWKs larger than **4096 bits**. Verify OIDC discovery, JWKS endpoints, and login flows before upgrading if your identity provider uses oversized RSA keys.
- **Standalone Console**: See [Console v2.4.2](/blog/release/console-2.4.2/) for standalone Console dependency updates.

## Verification and scope {#evidence}

Handler regressions in `cmd/` cover explicit self denials, session-restricted delegation, root-credential protection, empty-policy issuance, damaged-key cleanup, decrypted bulk-list identity contents, and Object Lock WORM invariants. See the [IAM authorization design note](/blog/design/iam-admin-authorization/), [Object Lock repair design note](/blog/design/governance-retention-bypass-repair/), and [component version matrix](/compatibility/versions/).
