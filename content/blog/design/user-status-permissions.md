---
title: "One Endpoint, Two Privileges: Separating User and Group Status"
linkTitle: "User and Group Status Permissions"
date: 2026-08-26
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Shared user and group status endpoints historically checked their Enable action even for disable requests. This record explains the least-privilege defect, SILO's strict target-state authorization design, the user repair merged through PR #73, the group follow-up, four-way IAM tests, and migration guidance.
tags: [Design, IAM, Security, Compatibility]
weight: 15
draft: false
url: "/blog/design/user-status-permissions/"
---

This article records the authorization design and verification for [upstream issue minio/minio#21478](https://github.com/minio/minio/issues/21478), [SILO PR #73](https://github.com/pgsty/silo/pull/73) (commits [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1) / [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5)), and the `set-group-status` follow-up (`229fe2b3c`), which shipped in [Server 20260903](/blog/release/silo-20260903/).

## Too Long; Didn't Read (TL;DR) {#tldr}

SILO exposes both `admin:EnableUser` and `admin:DisableUser`, but the shared `set-user-status` handler historically authorized every request with `admin:EnableUser`. A policy granting only `admin:DisableUser` could not disable an account; operators had to grant `admin:EnableUser` as well, breaking the least-privilege boundary between the two actions.

The fix selects a single required action from the requested target state before authorization:

| Requested status | Required action |
| --- | --- |
| `enabled` | `admin:EnableUser` |
| `disabled` | `admin:DisableUser` |
| invalid or unknown | `admin:EnableUser`, preserving the previous authorization-before-validation default |

The handler then calls `validateAdminReq` once. A four-way IAM integration test verifies both allowed operations and both denied cross-action operations. Enable-only policies can no longer disable accounts.

The same rule applies to group status:

| Requested group status | Required action |
| --- | --- |
| `enabled` | `admin:EnableGroup` |
| `disabled` | `admin:DisableGroup` |
| invalid or unknown | `admin:EnableGroup`, preserving the previous authorization-before-validation default |

Before the follow-up, an EnableGroup-only principal could disable a group, while a DisableGroup-only principal received `AccessDenied` for that operation. The group repair uses the same single-selector, single-authorization structure.

## The Reported Defect {#defect}

The Admin API uses one route for both state transitions:

```text
PUT /minio/admin/v3/set-user-status
    ?accessKey=<target>
    &status=enabled|disabled
```

Before the repair, the handler checked one fixed action before reading the requested status:

```go
objectAPI, creds := validateAdminReq(ctx, w, r, policy.EnableUserAdminAction)
```

The subsequent call to `SetUserStatus` accepted either `enabled` or `disabled`, but authorization had already treated both requests as Enable operations. `admin:DisableUser` existed in the policy vocabulary and documentation but could not authorize this endpoint on its own.

Issue #21478 demonstrated the operational impact: an operator wanted an incident-response policy that could disable compromised accounts without being able to re-enable them. A policy containing only `admin:DisableUser` failed with `AccessDenied`; adding `admin:EnableUser` allowed the disable call to succeed, but also granted the account-recovery permission the policy was meant to withhold:

```text
policy says:     DisableUser only
request says:    target state = disabled
handler checked: EnableUser
result:          legitimate disable denied
workaround:      grant an unwanted enable capability
```

## Why Two Actions Must Mean Two Capabilities {#policy-contract}

Account state transitions are directional. Disabling is frequently delegated to incident responders, fraud controls, or compliance automation, whereas re-enabling restores access and often requires a separate approver.

The authorization contract therefore enforces strict separation:

| Principal policy | Disable target | Enable target |
| --- | --- | --- |
| `admin:DisableUser` only | allow | deny |
| `admin:EnableUser` only | deny | allow |
| both actions | allow | allow |
| neither action | deny | deny |

The built-in `consoleAdmin` policy grants `admin:*`, so full administrators retain both operations. Only custom restricted policies that relied on `admin:EnableUser` to disable accounts are affected. The public PBAC reference documents the same contract for [`admin:EnableUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-EnableUser) and [`admin:DisableUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-DisableUser).

## Design Goals and Non-Goals {#scope}

### Goals {#goals}

1. Enforce both existing Admin Actions according to their names.
2. Preserve least privilege in both directions.
3. Perform one authorization decision and write at most one authorization error per request.
4. Preserve the route, query parameters, response format, self-mutation guard, IAM storage call, and site-replication hook.
5. Lock in the four-way permission matrix with regression tests.

### Non-Goals {#non-goals}

- split the endpoint into separate enable and disable routes;
- add a new combined action or change policy syntax;
- change user status persistence or replication;
- redesign Console permissions.

## Evaluated and Rejected Alternatives {#alternatives}

### Keep Checking `admin:EnableUser` for Both States {#always-enable}

This leaves `admin:DisableUser` non-functional and forces over-privileged policies.

### Require Both Actions for Either Transition {#require-both}

This prevents delegating disable-only permissions to incident-response roles.

### Try Enable Authorization, Then Retry Disable Authorization {#double-validation}

Upstream PR #21482 attempted this approach for disable requests: it called `validateAdminReq` with `EnableUser`, and if that returned `nil`, called `validateAdminReq` a second time with `DisableUser`.

However, when `validateAdminReq` returns a `nil` object layer, it has already written an HTTP error response. For a Disable-only caller, the first check commits a 403 response before the second check succeeds and mutates account state. Authorization fallback must never mutate state after committing an error response.

### Accept Either Enable or Disable for a Disabled Request {#allow-either}

`validateAdminReq` accepts a variadic action list and succeeds if any listed action is allowed. Passing both actions in a single variadic call would allow Disable-only policies to work while letting Enable-only policies continue to disable users.

SILO rejected this option because allowing Enable-only policies to disable accounts violates least privilege. Roles that manage the full account lifecycle should grant both actions explicitly.

### Validate the Status Before Authenticating {#validate-first}

Rejecting unknown `status` values before calling `validateAdminReq` would change error precedence, allowing unauthenticated or unauthorized callers to probe parameter validation before passing the authorization gate.

Unknown values therefore continue to select `admin:EnableUser` as the default authorization action. Only `disabled` selects `admin:DisableUser`; after authorization succeeds, the existing IAM layer rejects invalid status strings.

## The Selected Implementation {#implementation}

The repair adds a pure selector function:

```go
func setUserStatusAdminAction(status string) policy.AdminAction {
    if madmin.AccountStatus(status) == madmin.AccountDisabled {
        return policy.DisableUserAdminAction
    }
    return policy.EnableUserAdminAction
}
```

The handler reads the route variables, selects the action, and authorizes once:

```go
vars := mux.Vars(r)
accessKey := vars["accessKey"]
status := vars["status"]

objectAPI, creds := validateAdminReq(ctx, w, r, setUserStatusAdminAction(status))
if objectAPI == nil {
    return
}
```

All logic after the authorization gate is unchanged:

- callers still cannot enable or disable their own account;
- `globalIAMSys.SetUserStatus` validates and persists the requested status;
- site replication records the status and timestamp;
- response formatting and audit logging follow the existing path.

The selector inspects only the requested target state in the query string. It does not load the target user before authentication or branch on whether the target exists.

## Why the Repair Is Safe {#safety}

Five invariants hold after the change:

1. Every valid status maps to exactly one Admin Action.
2. `validateAdminReq` is called once, so a failed authorization never proceeds to mutation.
3. State mutation is reachable only after the selected action is authorized.
4. Invalid status values preserve the prior Enable authorization boundary and are rejected afterward by the existing validation path.
5. Storage, replication, wire format, and client SDK contracts remain unchanged.

## Test Design {#tests}

### Pure Action Mapping {#mapping-test}

The unit test covers all three selector outcomes:

| Input | Expected action |
| --- | --- |
| `enabled` | `EnableUser` |
| `disabled` | `DisableUser` |
| invalid | legacy `EnableUser` default |

### Four-Way IAM Authorization Matrix {#iam-test}

The integration test creates dedicated users and policies and exercises the Admin API across all four combinations:

1. a Disable-only client disables a target user;
2. the same client receives `AccessDenied` when attempting to enable that user;
3. an Enable-only client enables the target user;
4. the same client receives `AccessDenied` when attempting to disable that user.

The two cross-action denial checks guard against regressions that might accidentally permit both transitions. The test runs inside the IAM server suite — covering request signing, policy attachment, handler authorization, persistence, and Admin-client error decoding — and cleans up all temporary users and policies on completion.

## Verification Record {#verification}

Local verification commands:

```text
go test ./cmd -run '^TestSetUserStatusAdminAction$' -count=1
go test ./cmd -run '^TestIAMInternalIDPServerSuite$' -count=1
git diff --check
```

Commit `58735ee38` in PR #73 passed all eight remote CI checks (DCO sign-off, format/build/vet, lint and generated files, `cmd/` tests, `internal/` tests, race detector and S3 Select, cross compilation, and vulnerability analysis) and merged as `2e2377d1c`.

## Least-Privilege Policy Examples {#examples}

### Disable-Only Operator {#disable-only}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "admin:DisableUser",
        "admin:GetUser"
      ]
    }
  ]
}
```

This principal can inspect and disable another user, but cannot re-enable it.

### Enable-Only Operator {#enable-only}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "admin:EnableUser",
        "admin:GetUser"
      ]
    }
  ]
}
```

This principal can inspect and enable another user, but cannot disable it. Roles responsible for the full account lifecycle should grant both actions explicitly.

## Group-Status Follow-Up {#group-follow-up}

The group status endpoint shares the same structure as the user endpoint:

```text
PUT /minio/admin/v3/set-group-status
    ?group=<target>
    &status=enabled|disabled
```

It exposes `admin:EnableGroup` and `admin:DisableGroup`, but the inherited handler likewise checked `EnableGroup` before inspecting `status`.

The follow-up commit (`229fe2b3c`) adds `setGroupStatusAdminAction`, mirroring `setUserStatusAdminAction`:

```go
func setGroupStatusAdminAction(status string) policy.AdminAction {
    if madmin.GroupStatus(status) == madmin.GroupDisabled {
        return policy.DisableGroupAdminAction
    }
    return policy.EnableGroupAdminAction
}
```

The accompanying integration test creates isolated EnableGroup-only and DisableGroup-only administrators and a target group, verifying that:

1. DisableGroup-only can disable;
2. DisableGroup-only cannot enable;
3. EnableGroup-only can enable;
4. EnableGroup-only cannot disable.

Invalid `status` values still select the default Enable action before hitting the existing validation error, avoiding any pre-authentication validation oracle. The site-replication hook runs only after a permitted mutation succeeds.

## Compatibility and Migration {#compatibility}

No client or API changes are required; the endpoint, query parameters, status strings, response format, and Admin-client methods are unchanged.

Administrators should review custom restricted policies:

- roles that only disable users require `admin:DisableUser`;
- roles that only enable users require `admin:EnableUser`;
- roles that perform both operations require both actions;
- `consoleAdmin` and other `admin:*` policies are unaffected;
- legacy custom policies granting only `admin:EnableUser` can no longer disable users and must add `admin:DisableUser` if both operations are intended.

The same rules apply to group-management roles:

- roles that only disable groups require `admin:DisableGroup`;
- roles that only enable groups require `admin:EnableGroup`;
- roles that perform both operations require both actions;
- legacy EnableGroup-only roles can no longer disable groups.

## Upstream Disposition and Delivery {#upstream}

Upstream issue #21478 and PR #21482 remain on the archived `minio/minio` repository as historical context.

### Delivery State {#delivery}

| Milestone | User repair | Group follow-up |
| --- | --- | --- |
| Signed-off commit | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1) (merged as [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5)) | `229fe2b3c` |
| Shipped release | [Server 20260903](/blog/release/silo-20260903/) | [Server 20260903](/blog/release/silo-20260903/) |

## Conclusion {#conclusion}

Enabling and disabling users or groups carry opposite operational risks. Selecting the required action from the target state and authorizing once before mutation aligns handler enforcement with the IAM policy vocabulary.

This enable/disable repair is independent of the later `admin:ChangeMyPassword` split; see the [password migration guide](/compatibility/password-permissions/) when upgrading across September releases.
