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

**Release boundary:** the [Server 20261018 release](/blog/release/silo-20261018/) contains these repairs; its GitHub release and Docker Hub images were verified public on 2026-10-19. Server 20260916 does not contain them. Server 20261015 is a superseded draft, not the upgrade recommendation. Installing standalone Console v2.4.2 or mcli 20261018 does not patch a Server process.

## Object Lock: SN-2026-015 and SN-2026-016 {#object-lock}

The [existing advisory](/blog/security/20260926-governance-retention-bypass/) records the affected retention-write and overwrite paths, reproduction and mitigations. [#234](https://github.com/pgsty/silo/pull/234) and [#235](https://github.com/pgsty/silo/pull/235) require the base retention permission before object lookup, require both bypass intent and permission for weakening active GOVERNANCE, and protect caller-addressed or implicit in-place writes under the object lock. Unreadable lock state fails closed. Their [design](/blog/design/governance-retention-bypass-repair/) explains the trusted replication exception and why every write-accepting site must be upgraded.

Server 20260916 and the tested 20260903 are affected. The candidate prevents the repaired paths from changing protected state; it does not restore an overwritten version or reconstruct an earlier retention date. Review retention changes and unexpected COMPLIANCE locks in your audit records independently.

## SN-2026-017: Admin credential authorization boundaries {#sn-2026-017}

`SN-2026-017` is a SILO-local identifier, not a CVE. It groups the related Admin-handler defects repaired in [#242](https://github.com/pgsty/silo/pull/242), source [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6). The affected behavior is present in Server 20260916. These operations require authenticated credentials; this is not an anonymous Admin API exposure.

| Boundary | Before the repair | Candidate behavior |
| --- | --- | --- |
| Self inspection and cleanup | Ownership could override a policy or plugin denial; self service-account listing could skip authorization | Existing self rights remain, but explicit user/group denies, restricted session policies and plugin denials are enforced |
| Restricted credential delegation | A derived caller allowed the create/update action could obtain broader parent permissions or remove a target service account's restriction | Built-in authorization rejects creation and update by callers with active session policies, including LDAP creation and metadata-only updates |
| Root-derived credentials | A non-root administrator with broad Admin actions could manage root's derived keys | A separate guard requires an authorized root key or unrestricted root-derived identity; the internal site-replication account is not a root administrator |

The actor passed to policy evaluation remains the authenticated key, not its parent. Parent resolution is used for ownership only. Under built-in authorization, ordinary users retain self inspection and cleanup even after their last policy attachment is removed; absence of an Allow is not turned into a new denial for these established self operations. Derived credentials still undergo their session-policy checks. Cross-user operations keep their action requirements.

The root and delegation guards apply under built-in authorization, including LDAP/OIDC identities using local policy evaluation. With an external authorization plugin, that plugin remains the authority; its denial can no longer be overridden by self ownership. Review its rules rather than assuming the built-in guards replace them.

### Compatibility repairs retained alongside the security fix {#compatibility}

- New service-account issuance filters reserved parent policy/expiration claims and normalizes semantic empty policies (`null`, `{}`, `{"Statement":null}`) to inheritance. A versioned or explicitly empty statement-list policy is not normalized merely because it has no statements. This prevents newly issued expiring keys from carrying an unusable empty policy.
- Authorized cleanup uses stored identity metadata for damaged non-root service accounts, including disabled or expired targets. A damaged token cannot conceal a root parent. Missing identity metadata is not reconstructed.
- [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) extends the established self-service helper to bulk access-key listing. Omitted users, the caller's own key, or its parent resolve to the same parent inventory. Explicit denies and cross-user restrictions remain.
- A denied self operation returns 403. Service-account deletion of an unauthorized other-user/root target retains its 404 behavior; the repair does not make all Admin errors uniform.

Routes, action names, request/response formats and IAM storage formats are unchanged. No global policy-engine change, migration, background task or new setting is required. The [design record](/blog/design/iam-admin-authorization/) documents the local checks and their cost. Existing historical credentials are not rewritten.

### Operator action {#operations}

Test administration using the actual ordinary, service-account, STS and external-plugin identities used in production. Replace automation that relied on denied self access, restricted-key delegation or non-root mutation of root credentials with an appropriately authorized identity. Do not broaden all policies to recover the old bypass.

Review child credentials and service-account policy changes from the affected period. Revoke unexpected keys, and reissue previously unusable expiring keys through an authorized parent after verifying their intended policy. An upgrade does not identify or revoke every credential created before the fix. Preserve full IAM backups and revocation history; follow the [IAM recovery guide](/operations/replication/iam-upgrade/). Rolling back to 20260916 restores the defective handler behavior.

## Follow-up: scoped STS revocation {#sts-revocation}

Final candidate `0cd388c66` also repairs cache-only `RevokeTokens` enumeration and incomplete propagation to sibling nodes and sites. It retains tombstones for tokens durably known to the request cluster, selected by parent/type and operation cutoff, and propagates them through existing notification and deletion healing. Tokens not yet replicated from an isolated site are outside this snapshot; a partition does not provide instantaneous global revocation. Keep participating servers on the same coordinated version, retain complete IAM history and verify old-token rejection at each endpoint. See the [design and cost](/blog/design/iam-revocations/#scoped-sts-20261018) and [final artifact acceptance](/blog/release/silo-20261018/#delivery).


## Dependency security and login compatibility {#dependencies}

Server selects Go **1.27.2**, `golang.org/x/net` **v0.61.0**, `x/crypto` **v0.58.0**, `x/text` **v0.43.0** and go-jose **v4.1.6** in the [frozen module file](https://github.com/pgsty/silo/blob/0cd388c666f8211f552604ae73448a066e9c25ce/go.mod). A dependency selection or a clean scan is not proof that every possible deployment is free from vulnerabilities.

go-jose v4.1.6 addresses excessive CPU consumption while parsing crafted RSA JWKs, documented in the [upstream advisory GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q). Server's OIDC path uses this library. Its RSA JWK size limit rejects keys above **4096 bits**: check identity-provider discovery, JWKS and login before upgrading, and rotate incompatible keys at the provider. This dependency advisory alone does not establish an unauthenticated S3 exploit in SILO.

Standalone Console's module graph declares related dependencies through pkg, but go-jose and go-ldap are not linked into that standalone binary; see the [Console release scope](/blog/release/console-2.4.2/). Server's pkg **v3.14.3** adds a policy-performance improvement over v3.14.2 without changing authorization semantics. Neither the optimization nor a client upgrade substitutes for the Server handler repair above.

## Evidence and scope {#evidence}

The candidate contains handler regressions for explicit self denials, session-limited delegation, root targets, empty-policy issuance, damaged-key cleanup and decrypted bulk-list identity contents. Object Lock regressions gate Server release builds. Source and test references are recorded in the [IAM design](/blog/design/iam-admin-authorization/) and [Object Lock design](/blog/design/governance-retention-bypass-repair/).

These source records do not establish public artifact availability or a completed production rollout. Use the [release notes](/blog/release/silo-20261018/#delivery) and [component matrix](/compatibility/versions/) for delivery status. STS revocation still converges asynchronously across sites. The Admin authorization repairs do not promise atomic authorization across concurrent mutations, and the separate #79 / #217 storage limitations remain.
