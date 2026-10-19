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

**20261018 release:** The [selected source](/blog/release/silo-20261018/) contains #242 and the bulk self-listing follow-up `995439260`. The Server release is public; October 16 verification below applies to its recorded source. See [SN-2026-017](/blog/security/20261018-release-hardening/#sn-2026-017) for security impact.

**Decision, 2026-10-16: GO; source acceptance and merge complete.**
[Server PR #242](https://github.com/pgsty/silo/pull/242) merged the signed repair
commit [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)
into `main` as [`4e55fc7db`](https://github.com/pgsty/silo/commit/4e55fc7db4bd0f21ae187517f7438a8625768f6a).
The final candidate was verified directly on main's `00a375c4e` baseline,
independently of the pending LIST repair. All eight hosted checks and the
complete local IAM/STS integration selection passed.

This records source integration. A tag, published package, container release,
and production deployment remain separate deliverables; the merge does not
establish that an existing released image contains the repair.

## Problem and scope {#problem}

Several Admin handlers treated ownership as a fallback after authorization had
already denied a request. Listing one's own service accounts could also skip
authorization altogether. These paths could override an explicit user or group
deny, an inline session-policy restriction, or an external authorization
plugin's denial.

Credential creation and update exposed a second boundary. A derived credential
whose session policy allowed those Admin actions could create a key inheriting
broader parent permissions, or remove a service account's restriction through
an update. A non-root administrator with broad Admin permissions could also
manage root's derived credentials. An action grant alone is insufficient for
these operations under built-in authorization.

The repair covers inspection/cleanup and creation/update handlers, including
bulk key listing and the LDAP creation endpoint. It preserves the policy engine's
global behavior, existing Admin routes and actions, request/response formats,
and IAM storage formats. No dependency version changes are required.

Here, **built-in authorization** means no external authorization plugin is
configured; it includes local IAM evaluation for LDAP/OIDC identities. It does
not mean that the identity must be a built-in user. See
[access management](/administration/identity-access-management/policy-based-access-control/)
and [external authorization](/administration/identity-access-management/pluggable-authorization/)
for the surrounding policy model.

## Authorization contract {#contract}

The authenticated access key remains the actor supplied to IAM. For ownership
comparisons, its effective user is `ParentUser` when present, otherwise
`AccessKey`. Resolving ownership never changes the actor into the parent during
policy evaluation.

Self inspection and cleanup use `DenyOnly: true` as input to authorization.
Ordinary users need no explicit allow for these established self-service
operations, but an applicable explicit deny still wins. Derived credentials
continue through full IAM evaluation; an active session policy must explicitly
allow the operation. An external plugin's denial is final. No handler turns a
denial into success merely because the target belongs to the caller.

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
session policy grants the named action. Supporting safe delegation would need
a separate design for preserving or comparing policy restrictions. This patch
does not attempt that. The update restriction also covers metadata-only
requests: the existing update implementation can clear the old inline policy
when the request omits a new policy.

## Three local helpers {#helpers}

Production changes are confined to `cmd/admin-handlers-users.go` and the claim
copy loop in `cmd/admin-handlers-idp-ldap.go`. Three small helpers express the
boundaries; `IAMSys.IsAllowed` is unchanged.

`hasActiveSessionPolicy` reuses the existing session-policy evaluators. It
checks temporary credentials before service accounts, matching IAM dispatch.
An expiring service account satisfies `IsTemp()` and is evaluated as STS.
Consequently, a legacy expiring credential marked `inherited-policy` can still
have an effective inline restriction. Checking the inherited marker first
would incorrectly permit that credential to create or update broader keys.
For a non-temporary service account, the inherited marker and empty-policy
behavior follow the existing service-account evaluator.

`canManageRootCredentials` is an additional guard after successful built-in
authorization. It accepts the root key or an unrestricted root-derived
credential, excluding the internal site replication service account. It does
not grant an action by itself. The signature's `owner` flag is insufficient:
the mere presence of the raw session-policy claim clears that flag, even when
the service-account evaluator treats the policy as empty. Checking the actual
restriction preserves historical root service accounts with `null`, `{}`, or
`{"Statement":null}` policies.

`isAllowedServiceAccountAction` preserves ordinary users' existing self
inspection and cleanup after their last policy attachment is removed. For
built-in, non-owner, non-derived callers using `DenyOnly`, it resolves user and
group policies and evaluates the combined policy, including an empty one.
Explicit denies remain effective. All other callers use `IAMSys.IsAllowed`.
Changing the engine's global no-policy behavior would affect unrelated S3 and
Admin operations, so that behavior remains unchanged.

The creation, update, deletion, and revocation root guards apply only under
built-in authorization. External authorization continues to decide these
operations, including root targets; the repair makes formerly bypassed self
requests consult that authority as well.

## Empty policies and claim ownership {#empty-policies}

Review identified an availability defect in the creation path. Copying a
parent service account's empty inline policy into a new inherited key leaves
stale internal policy claims. If the new key expires, STS evaluation rejects
that empty policy because it has no version. The create request succeeds, but
the resulting key cannot perform its intended operations.

The same failure occurs when the new request itself specifies a semantic empty
policy together with an expiration. Both cases are repaired at the Admin
issuance boundary:

1. Both creation handlers exclude `exp`, `policy.SessionPolicyName`,
   `sessionPolicyNameExtracted`, and `iamPolicyClaimNameSA()` when copying the
   caller's claims. The new key receives its own expiration and requested
   policy. Other identity claims, including LDAP/OIDC context, remain available.
2. `commonAddServiceAccount` normalizes a parsed policy to inheritance only
   when `Version == "" && Statements == nil && ID == ""`. This is the same
   empty-policy definition used by the service-account evaluator. It clears
   both the local policy option and the returned request's policy, so the
   replication create message describes the same policy as the local key.

| Requested child policy | Result |
| --- | --- |
| Omitted, `null`, `{}`, `{"Statement":null}` | Inherit parent permissions, including when the new key has an expiration. |
| A policy allowing only selected actions | Retain the requested restriction; unrelated actions remain denied. |
| `{"Version":"2012-10-17"}` or `{"Statement":[]}` | Do not normalize to inheritance; the expiring-key regression cases remain denied. |

Normalization deliberately does not use `len(Statements) == 0`: a policy can
have no statements without being the special Console empty-policy form.

`IAMSys.NewServiceAccount` is also used by import and site replication.
Sanitizing claims there could discard an effective restriction carried only
in a historical expiring credential's claims. The shared constructor and
historical record replay are therefore unchanged. This patch fixes new Admin
issuance; it does not rewrite stored credentials.

## Deletion and error behavior {#deletion}

Deletion needs trustworthy identity metadata, not a successfully decoded target
session token. `DeleteServiceAccount` reads `globalIAMSys.store.GetUser`, checks
the service-account kind, and retains the stored parent. This is also the
lookup used by the underlying delete operation. It avoids both token parsing
and the public user lookup's disabled/expired credential filter, while keeping
the store's existing parent-revocation checks.

An authorized administrator can clean a damaged non-root service account even
when it is disabled or expired. A non-root administrator cannot use token
corruption to conceal a root parent. The preserved parent also determines
whether the normal site replication hook must send the deletion. This does
not recover arbitrary records whose identity metadata is missing or no longer
identifies a service account.

Denied deletion of another user's key, root-guard rejection, and a missing
service account return `ErrAdminServiceAccountNotFound` (HTTP 404). A denied
self operation returns `ErrAccessDenied` (HTTP 403). Other endpoints retain
their existing lookup/error ordering; this is not a redesign of all Admin
enumeration behavior.

## Compatibility and limits {#compatibility}

The intended behavior changes are enforcement of existing denies on self
operations, rejection of session-limited creation/update, and protection of
root credential mutations under built-in authorization. Automation relying on
those bypasses must use a properly authorized, unrestricted identity. Ordinary
users retain their existing inspection and cleanup rights, including after
policy detachment. Root's historical empty-policy service accounts retain
their management behavior.

New empty-policy keys have inherited-policy metadata instead of an embedded
empty policy. A client inspecting the policy representation may observe this
normalization; effective service-account inheritance is intentional, and the
expiring-key evaluation mismatch is removed. Reserved internal policy claims
are no longer copied from the caller to the newly issued key. External plugins
that inspect those internal fields should treat them as properties of the new
credential, rather than a copy of the caller's session restriction.

`ListAccessKeysBulk` now uses the same self-service helper through the October 18 follow-up [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8). Ordinary users without attached policies can inspect themselves; explicit denies, derived-credential session restrictions and cross-user authorization remain effective. Omitted users, or a single users parameter naming the caller key or parent, resolve to exactly the parent inventory. `all=true` still additionally requires `admin:ListUsers` and is not a self alias. Regressions decrypt responses and check identity contents for ordinary, service-account and STS aliases.

Existing unusable expiring credentials are not automatically repaired. An
authorized parent or administrator should reissue the intended key, verify its
access, and remove the old key. Do not erase policy claims from imported or
replicated historical credentials as a bulk migration. Existing valid session
restrictions remain in force.

The supported product graph is SILO, SILO Console, mcli, and silo-pkg.
Compatibility with unmodified upstream MinIO/MC remains best effort. This
patch does not change dependency selection or establish a new upstream release
gate. It also does not change distributed revocation ordering or guarantee
atomic authorization across concurrent administrative mutations; see
[durable IAM revocations](/blog/design/iam-revocations/) for those boundaries.

## Cost and rejected alternatives {#cost}

The original #242 production delta was 59 net added lines across two handler files; the October 18 bulk-list follow-up reuses its helper. There is
no new cache, background worker, lock protocol, storage migration, or S3 data
path change. Claim filtering uses existing copy loops; normalization reuses
the policy already parsed for creation.

Admin creation/update checks can parse the caller's inline policy again.
Service-account policies already have a 4 KiB limit. The reuse of the existing
evaluators avoids introducing a second definition of an active policy. Self
inspection now performs necessary policy evaluation where some requests
previously skipped it. Policy lookup normally uses the IAM cache, but the
existing combined-policy loader can access storage when documents are missing.
In plugin deployments, newly enforced checks can add a plugin request; their
latency depends on that service.

A local diagnostic benchmark on Darwin/arm64, Apple M5 Max, Go 1.27.2 used
three 200 ms samples. Ordinary/inherited session checks cost roughly 11–16 ns
with no allocations; an empty service policy about 0.30–0.32 microseconds; a
roughly 3 KiB policy about 10 microseconds. Cached ordinary-user self evaluation
was in the same sub-microsecond range as the existing IAM path, with the same
800 bytes and 15 allocations per operation. These are narrow local measurements,
not an endpoint latency or S3 throughput guarantee. They provide no reason to
add a cache or a more complex policy representation for these Admin paths.

Rejected alternatives were a global `IsAllowed` change, treating raw claim
presence as a restriction, central claim removal in `NewServiceAccount`, policy
containment analysis for delegation, and unconditional denial of damaged-key
cleanup. Each would either widen the scope or break behavior that the local
checks can preserve.

## Regression evidence {#validation}

The final source candidate `2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6` passed the following checks on 2026-10-16:

| Check | Result |
| --- | --- |
| Complete `TestIAM*` / `TestSTS*` selection with real etcd, LDAP, two OIDC providers, and an authorization plugin | 57 top-level tests; 380 passing records including parent tests and subtests; 0 failures, 0 skips. |
| Ten `TestIAMAdmin*` regression tests using signed requests and encrypted Admin payloads | Passed. |
| Focused race run for `TestIAMAdmin*` and the peer delete/reload test | Passed. |
| Authentication, identity configuration, and policy configuration packages | Passed; packages without tests reported as such. |
| `make verifiers` | Passed: lint, generated-file checks, and rebrand/compatibility checks. Optional `typos` was unavailable and skipped. |
| `make build` | Passed; produced the `silo` executable. |
| Hosted checks on the final PR head | All eight passed: DCO, vulnerability analysis, format/build/vet, lint/generated files, race, cross compilation, internal tests, and cmd tests. |

The regression file `cmd/admin-handlers-users-authz_test.go` covers root empty
policies, policyless self operations, parent/group/session/plugin denials,
legacy expiring inherited credentials, non-root access to root targets,
disabled/expired damaged-key cleanup, deletion replication, self aliases, and
empty-policy child issuance with positive and negative access checks. The LDAP
suite also issues expiring child keys through `AddServiceAccountLDAP` and
performs real S3 access. Additional local adversarial probes verified damaged
root-key cleanup and STS explicit/implicit denials across the five self handlers.

Two existing test corrections are included. The peer reload test explicitly
clears a stale etcd client before constructing its object-storage fixture. The
IAM import test derives default policy names from `policy.DefaultPolicies`
instead of a fixed list. Neither changes production authorization or weakens
the assertions; a separate fixture-order run also passed.

Core verification commands are:

```sh
go test ./cmd -run '^TestIAMAdmin' -count=1 -v
go test -race ./cmd -run '^(TestIAMAdmin|TestIAMPeerDeleteNotificationReloadsCommittedState)' -count=1
go test -tags kqueue,dev ./cmd -run '^(TestIAM|TestSTS)' -count=1 -timeout=30m -v
go test ./internal/auth ./internal/config/identity/... ./internal/config/policy/...
make verifiers
make build
```

The complete suite requires working fixture endpoints in
`_MINIO_ETCD_TEST_SERVER`, `SILO_TEST_IAM_REVOCATION_ETCD`,
`_MINIO_LDAP_TEST_SERVER`, `_MINIO_OPENID_TEST_SERVER`,
`_MINIO_OPENID_TEST_SERVER_2`, and `_MINIO_POLICY_PLUGIN_ENDPOINT`. A run without
them may skip integrations and is not equivalent to the recorded result.
The complete run used `CGO_ENABLED=0` and `MINIO_API_REQUESTS_MAX=10000`.
The separate race run used the normal race-capable build environment.

## Acceptance and delivery {#delivery}

The adversarial review found no remaining blocking issue in the described
scope. The patch is sufficient to close the identified authorization paths,
preserves the tested compatibility boundaries, and has a reasonable cost for
Admin operations. The decision is **GO for this source candidate**.

The signed source commit and merge are recorded above. Release notes must
identify the eventual release that contains the repair. Upgrade every server that accepts Admin traffic: a mixed-version
deployment can still route a request through an old handler. No new on-disk
format or bulk credential rewrite is required by this patch. Rolling back
restores the earlier authorization defects, so rollback is not a security fix.
Server release, documentation publication, and deployment verification remain
separate steps; source acceptance does not mark those steps complete.
