---
title: "IAM Admin API Authorization Boundaries"
linkTitle: "IAM Admin Authorization"
date: 2026-10-16
lastmod: 2026-10-19
author: "SILO"
summary: >
  Enforcing self-service policy decisions, preventing session credentials from
  escaping their restrictions, protecting root credentials, and preserving
  empty-policy and damaged-key cleanup behavior with a small handler-level repair.
tags: [Design, IAM, Security, Compatibility]
weight: 16
draft: false
url: "/blog/design/iam-admin-authorization/"
---

[Server 20261018](/blog/release/silo-20261018/) ships [Server PR #242](https://github.com/pgsty/silo/pull/242) (commit [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6) on baseline [`00a375c4e`](https://github.com/pgsty/silo/commit/00a375c4edbc7590290e53d1636211de64bc7d58), merged as [`4e55fc7db`](https://github.com/pgsty/silo/commit/4e55fc7db4bd0f21ae187517f7438a8625768f6a)) and the bulk self-listing follow-up [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) to close [SN-2026-017](/blog/security/20261018-release-hardening/#sn-2026-017). This design note records the problem scope, handler-level authorization contract, empty-policy claim handling, damaged-key deletion semantics, performance measurements, rejected alternatives, and regression verification.

## Problem and scope {#problem}

Several Admin handlers treated ownership as a fallback after authorization had
already denied a request, and listing one's own service accounts could skip
authorization altogether. Those paths could override an explicit user or group
deny, an inline session-policy restriction, or an external authorization
plugin's denial.

Credential creation and update exposed a second boundary. A derived credential
whose session policy allowed those Admin actions could create a key inheriting
broader parent permissions, or remove a service account's restriction through
an update. A non-root administrator with broad Admin permissions could also
manage root's derived credentials. Under built-in authorization, an action
grant alone is insufficient for these operations.

The repair covers inspection, cleanup, creation, and update handlers, including
bulk key listing and the LDAP creation endpoint. It preserves the policy engine's
global behavior, existing Admin routes and actions, request/response formats,
and IAM storage formats without dependency version changes.

Here, **built-in authorization** means no external authorization plugin is
configured; it includes local IAM evaluation for LDAP/OIDC identities. See
[access management](/administration/identity-access-management/policy-based-access-control/)
and [external authorization](/administration/identity-access-management/pluggable-authorization/)
for the surrounding policy model.

## Authorization contract {#contract}

The authenticated access key remains the actor supplied to IAM. For ownership
comparisons, its effective user is `ParentUser` when present, otherwise
`AccessKey`. Resolving ownership never substitutes the parent for a derived
credential during policy evaluation.

Self inspection and cleanup pass `DenyOnly: true` into authorization.
Ordinary users need no explicit allow for these established self-service
operations, while an applicable explicit deny still takes effect. Derived
credentials continue through full IAM evaluation, where an active session policy
must explicitly allow the operation. An external plugin's denial is final, and
handlers no longer turn a denial into success when the target belongs to the
caller.

| Handler | Existing Admin action | Self behavior and additional boundary |
| --- | --- | --- |
| `InfoServiceAccount` | `admin:ListServiceAccounts` | Compare the effective user with the stored service account parent; authorize before returning information. |
| `ListServiceAccounts` | `admin:ListServiceAccounts` | Empty user, caller access key, and caller parent are self aliases. Authorize every request and list the parent for these aliases. |
| `ListAccessKeysBulk` | `admin:ListServiceAccounts` | Normalize self aliases to the parent and use the same self-service helper; cross-user and `all=true` requests retain their additional authorization requirements. |
| `InfoAccessKey` | `admin:ListServiceAccounts` | Self requires an existing derived target with the same parent. Missing targets do not create a self exception. |
| `DeleteServiceAccount` | `admin:RemoveServiceAccount` | Authorize self cleanup; apply the root boundary; use stored identity metadata even when the target token is damaged. |
| `RevokeTokens` | `admin:RemoveServiceAccount` | Omitted user or the resolved caller parent is self. Authorize before revocation and protect root targets. |
| `AddServiceAccount`, `AddServiceAccountLDAP` | `admin:CreateServiceAccount` | Retain existing self/other-user IAM authorization; then reject active session policies and unauthorized effective root targets. |
| `UpdateServiceAccount` | `admin:UpdateServiceAccount` | Retain the existing action requirement; then reject active session policies and unauthorized root targets. No new self-update privilege. |

Creation and update are denied to session-limited callers even when their
session policy grants the named action. The update restriction also covers
metadata-only requests because the existing update implementation can clear the
old inline policy when the request omits a new policy.

## Three local helpers {#helpers}

Production changes are confined to `cmd/admin-handlers-users.go` and the claim
copy loop in `cmd/admin-handlers-idp-ldap.go`. Three small helpers express the
boundaries while leaving `IAMSys.IsAllowed` unchanged.

`hasActiveSessionPolicy` reuses the existing session-policy evaluators,
checking temporary credentials before service accounts to match IAM dispatch.
An expiring service account satisfies `IsTemp()` and is evaluated as STS.
Consequently, a legacy expiring credential marked `inherited-policy` can still
carry an effective inline restriction; checking the inherited marker first
would permit that credential to create or update broader keys. Non-temporary
service accounts follow the existing service-account evaluator's inherited
marker and empty-policy rules.

`canManageRootCredentials` is an additional guard after successful built-in
authorization. It accepts the root key or an unrestricted root-derived
credential (excluding the internal site replication service account). The
signature verifier's `owner` flag is cleared whenever the raw session-policy
claim key is present, even when the service-account evaluator treats that
policy as empty. Checking for an active restriction preserves management access
for historical root service accounts created with `null`, `{}`, or
`{"Statement":null}` policies.

`isAllowedServiceAccountAction` preserves ordinary users' self inspection and
cleanup after their last policy attachment is removed. For built-in, non-owner,
non-derived callers with `DenyOnly`, it resolves user and group policies and
evaluates the combined policy (allowing an empty combined policy while honoring
explicit denies). All other callers use `IAMSys.IsAllowed`, keeping the engine's
global no-policy behavior unchanged for S3 and other Admin operations.

The creation, update, deletion, and revocation root guards apply only under
built-in authorization. When an external authorization plugin is configured,
it decides these operations — including root targets — and formerly bypassed
self requests now consult the plugin as well.

## Empty policies and claim ownership {#empty-policies}

Code review identified an availability defect in the creation path: copying a
parent service account's empty inline policy into a new inherited key leaves
stale internal policy claims. If the new key has an expiration, STS evaluation
rejects that empty policy because it has no `Version` field, leaving the newly
created key unable to perform its intended operations.

The same failure occurs when a creation request explicitly specifies a semantic
empty policy together with an expiration. Both cases are resolved at the Admin
issuance boundary:

1. Both creation handlers exclude `exp`, `policy.SessionPolicyName`,
   `sessionPolicyNameExtracted`, and `iamPolicyClaimNameSA()` when copying the
   caller's claims. The new key receives its own expiration and requested
   policy, while preserving other identity claims including LDAP/OIDC context.
2. `commonAddServiceAccount` normalizes a parsed policy to inheritance only
   when `Version == "" && Statements == nil && ID == ""`, matching the
   empty-policy definition in the service-account evaluator. It clears both the
   local policy option and the returned request's policy field so the site
   replication create message matches the local key.

| Requested child policy | Result |
| --- | --- |
| Omitted, `null`, `{}`, `{"Statement":null}` | Inherit parent permissions, including when the new key has an expiration. |
| A policy allowing only selected actions | Retain the requested restriction; unrelated actions remain denied. |
| `{"Version":"2012-10-17"}` or `{"Statement":[]}` | Do not normalize to inheritance; the expiring-key regression cases remain denied. |

Normalization checks `Statements == nil` rather than `len(Statements) == 0` so
that only the Console empty-policy placeholder forms are normalized to
inheritance.

`IAMSys.NewServiceAccount` is also called by IAM import and site replication.
Sanitizing claims in that shared constructor could discard an effective
restriction carried only in a historical expiring credential's claims. The
shared constructor and historical record replay therefore remain unchanged; the
fix applies at the Admin issuance boundary.

## Deletion and error behavior {#deletion}

`DeleteServiceAccount` reads stored identity metadata directly via
`globalIAMSys.store.GetUser`, checks the service-account kind, and retains the
stored parent without decoding the target session token. The underlying delete
operation uses the same lookup primitive, bypassing both token parsing and the
public user lookup's disabled/expired credential filter while keeping the
store's parent-revocation checks.

An authorized administrator can clean up a damaged, disabled, or expired
non-root service account, and a non-root administrator cannot use token
corruption to conceal a root parent. Preserving the stored parent also ensures
that the site replication hook sends deletion messages when appropriate.

Denied deletion of another user's key, root-guard rejection, and a missing
service account all return `ErrAdminServiceAccountNotFound` (HTTP 404). A denied
self operation returns `ErrAccessDenied` (HTTP 403). Other endpoints retain
their existing lookup and error ordering.

## Compatibility and limits {#compatibility}

The behavioral changes enforce existing denies on self operations, reject
credential creation or update by session-limited callers, and protect root
credential mutations under built-in authorization. Automation that relied on
the old bypasses must use a properly authorized, unrestricted identity. Ordinary
users retain their self-inspection and cleanup rights (including after policy
detachment), and root's historical empty-policy service accounts retain their
management capabilities.

Newly created empty-policy keys store `inherited-policy` metadata instead of an
embedded empty policy document, removing the evaluation mismatch for expiring
keys. Reserved internal policy claims are no longer copied from the caller to
the newly issued key and reflect only the new credential's own attributes.

`ListAccessKeysBulk` uses the same self-service helper through the October 18 follow-up [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8). Ordinary users without attached policies can inspect themselves, while explicit denies, derived-credential session restrictions, and cross-user authorization remain enforced. Omitted `users`, or a single `users` parameter naming the caller key or parent, resolve to the parent inventory; `all=true` still requires `admin:ListUsers`. Regression tests decrypt responses and verify identity contents across ordinary, service-account, and STS aliases.

Existing unusable expiring credentials are not rewritten in place; an
authorized parent or administrator should reissue the intended key, verify its
access, and remove the old key. Do not bulk-strip policy claims from imported
or replicated historical credentials, as that would remove valid session
restrictions.

For distributed revocation ordering and concurrent administrative mutation boundaries, see
[durable IAM revocations](/blog/design/iam-revocations/).

## Cost and rejected alternatives {#cost}

The `#242` production diff adds 59 net lines across two handler files, and the October 18 bulk-list follow-up reuses the same helper. It introduces no new cache, background worker, lock protocol, storage migration, or S3 data-path change. Claim filtering runs inside existing copy loops, and empty-policy normalization reuses the policy already parsed for creation.

Admin creation and update checks may parse the caller's inline policy (bounded
by the 4 KiB service-account policy limit), reusing the existing evaluators
rather than maintaining a second definition of an active policy. Self-inspection
requests that previously skipped authorization now evaluate policy through the
IAM cache, touching storage only when the combined-policy loader encounters a
missing document. In external-plugin deployments, newly enforced checks issue a
plugin request whose latency depends on that external service.

A local benchmark on Darwin/arm64 (Apple M5 Max, Go 1.27.2, three 200 ms
samples) measured:
- Ordinary/inherited session checks: ~11–16 ns with 0 allocations.
- Empty service policy check: ~0.30–0.32 µs.
- ~3 KiB inline policy check: ~10 µs.
- Cached ordinary-user self evaluation: sub-microsecond range matching the existing IAM path (800 B, 15 allocs/op).

These costs require no additional cache or specialized policy representation on the Admin path.

Five alternative approaches were evaluated and rejected:
1. **Modifying global `IAMSys.IsAllowed` behavior**: Rejected because changing global no-policy or self-ownership rules would alter unrelated S3 and Admin operations.
2. **Treating raw session-policy claim presence as a restriction**: Rejected because historical root service accounts created with `null`, `{}`, or `{"Statement":null}` carry the raw claim key while having no effective restriction.
3. **Stripping policy claims centrally in `IAMSys.NewServiceAccount`**: Rejected because `NewServiceAccount` is shared with IAM import and site replication, where stripping claims could discard an effective restriction carried in a historical expiring credential's claims.
4. **General policy-containment solver for session-limited delegation**: Rejected because session-limited credentials are designed as leaf credentials rather than sub-issuers, and disallowing creation/update from active session policies closes the escape path in 59 lines.
5. **Unconditional denial of damaged-key cleanup**: Rejected because administrators need a way to delete corrupted, disabled, or expired non-root service accounts using stored identity metadata.

## Regression evidence {#validation}

Commit `2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6` and follow-up `9954392605827b213877c45262c741e638598dd8` were verified with the following suites:

| Check | Result |
| --- | --- |
| Complete `TestIAM*` / `TestSTS*` selection with real etcd, LDAP, two OIDC providers, and an authorization plugin | 57 top-level tests; 380 passing records including parent tests and subtests; 0 failures, 0 skips. |
| `TestIAMAdmin*` regression tests using signed requests and encrypted Admin payloads | Passed. |
| Focused race run for `TestIAMAdmin*` and the peer delete/reload test | Passed. |
| Authentication, identity configuration, and policy configuration packages | Passed. |
| `make verifiers` and `make build` | Passed lint, generated-file checks, rebrand/compatibility checks, and binary build. |
| Hosted CI checks on PR `#242` | All 8 checks passed (DCO, vulnerability analysis, format/build/vet, lint/generated files, race, cross compilation, internal tests, and cmd tests). |

`cmd/admin-handlers-users-authz_test.go` covers root empty
policies, policyless self operations, parent/group/session/plugin denials,
legacy expiring inherited credentials, non-root access to root targets,
disabled/expired damaged-key cleanup, deletion replication, self aliases, and
empty-policy child issuance with positive and negative access checks. The LDAP
suite also issues expiring child keys through `AddServiceAccountLDAP` and
verifies S3 access. Additional boundary probes verified damaged
root-key cleanup boundaries and STS explicit/implicit denials across the five self handlers.

Two existing test fixtures were also tightened: the peer reload test clears stale etcd client state before constructing its object-storage fixture, and the IAM import test derives default policy names from `policy.DefaultPolicies` instead of a hardcoded list.

Verification commands:

```sh
go test ./cmd -run '^TestIAMAdmin' -count=1 -v
go test -race ./cmd -run '^(TestIAMAdmin|TestIAMPeerDeleteNotificationReloadsCommittedState)' -count=1
go test -tags kqueue,dev ./cmd -run '^(TestIAM|TestSTS)' -count=1 -timeout=30m -v
go test ./internal/auth ./internal/config/identity/... ./internal/config/policy/...
make verifiers
make build
```

## Rollout and upgrade notes {#delivery}

- Shipped in: [Server 20261018](/blog/release/silo-20261018/#security) (PR [`#242`](https://github.com/pgsty/silo/pull/242), commits `2616d43fb`, `4e55fc7db`, and `995439260`).
- Advisory: [SN-2026-017](/blog/security/20261018-release-hardening/#sn-2026-017).
- Upgrade every server node that accepts Admin traffic so mixed-version routing cannot send a request through an unpatched handler. No new on-disk format or bulk credential rewrite is required.
