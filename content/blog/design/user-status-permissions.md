---
title: "One Endpoint, Two Privileges: Separating User Enable and Disable"
linkTitle: "User Status Permissions"
date: 2026-08-26
lastmod: 2026-08-26
author: "Ruohang Feng"
summary: >
  A single user-status endpoint always checked admin:EnableUser, making admin:DisableUser unusable by itself. This record explains the least-privilege defect reported in minio/minio#21478, SILO's strict target-state authorization design, the rejected compatibility fallbacks, the implementation and four-way IAM tests, and the boundary between a merged repair and a delivered release.
tags: [Design, IAM, Security, Compatibility]
weight: 15
draft: false
url: "/blog/design/user-status-permissions/"
---

This document records the discussion, repair, and final authorization design for [upstream issue minio/minio#21478](https://github.com/minio/minio/issues/21478) and [SILO PR #73](https://github.com/pgsty/silo/pull/73).

> **Status on 2026-08-26:** SILO PR #73 was merged as [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5), preserving the signed-off repair commit [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1). All eight reported checks passed. Upstream issue #21478 and PR #21482 remain open, but `minio/minio` is archived and read-only, so no further issue comment or merge can be made there.<br>
> **Scope:** authorize enabling and disabling a user with their respective existing Admin Actions. Do not change the route, status values, account storage, replication record, or client API.<br>
> **Security property:** possessing `admin:DisableUser` must not grant the ability to enable an account, and possessing `admin:EnableUser` must not grant the ability to disable one.<br>
> **Release boundary:** merge, tag, release package, container image, deployment, and production verification remain separate gates.

## Too Long; Didn't Read (TL;DR) {#tldr}

SILO exposes both `admin:EnableUser` and `admin:DisableUser`, but the shared `set-user-status` handler historically authorized every request with `admin:EnableUser`. A policy that granted only `admin:DisableUser` therefore could not disable an account. The workaround was to grant `admin:EnableUser` as well, which destroyed the least-privilege boundary that the two action names promised.

The selected repair derives exactly one required action from the requested target state before authorization:

| Requested status | Required action |
| --- | --- |
| `enabled` | `admin:EnableUser` |
| `disabled` | `admin:DisableUser` |
| invalid or unknown | `admin:EnableUser`, preserving the previous authorization-before-validation default |

The handler then calls `validateAdminReq` once. A four-way IAM test proves both positive operations and both denied cross-action operations. This is intentionally stricter than preserving the accidental historical behavior in which an Enable-only policy could also disable users.

## The reported defect {#defect}

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

The later call to `SetUserStatus` correctly received either `enabled` or `disabled`, but authorization had already treated both as Enable operations. `admin:DisableUser` existed in the policy vocabulary and documentation while being ineffective for this endpoint on its own.

Issue #21478 supplied the practical counterexample: an operator wanted a policy that could disable accounts during an incident without being able to restore them. A policy containing `admin:DisableUser` received `AccessDenied`; adding `admin:EnableUser` made the request work, but also gave the operator the more powerful recovery transition that the policy intentionally withheld.

This is not a missing convenience permission. It is a mismatch between the policy model and the enforcement point:

```text
policy says:     DisableUser only
request says:    target state = disabled
handler checked: EnableUser
result:          legitimate disable denied
workaround:      grant an unwanted enable capability
```

## Why two actions must mean two capabilities {#policy-contract}

An account state transition has direction. Disabling is commonly delegated to incident responders, fraud controls, compliance automation, or a break-glass process. Enabling restores access and may require a separate approver.

If either action authorizes both transitions, a policy author cannot express that separation. The server would publish two names while enforcing one combined capability. The design contract is therefore strict:

| Principal policy | Disable target | Enable target |
| --- | --- | --- |
| `admin:DisableUser` only | allow | deny |
| `admin:EnableUser` only | deny | allow |
| both actions | allow | allow |
| neither action | deny | deny |

The built-in `consoleAdmin` policy grants `admin:*`, so full administrators retain both operations. The compatibility impact is limited to custom restricted policies that relied on the old accidental behavior.

The public PBAC reference now states the same contract for [`admin:EnableUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-EnableUser) and [`admin:DisableUser`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-DisableUser).

## Design goals and non-goals {#scope}

### Goals {#goals}

1. Make both existing Admin Actions enforceable according to their names.
2. Preserve least privilege in both directions.
3. Perform one authorization decision and write at most one authorization error.
4. Preserve the route, request values, response format, self-mutation guard, IAM storage call, and site-replication hook.
5. Encode the contract in tests that fail if the two permissions are broadened or swapped again.

### Non-goals {#non-goals}

- split the endpoint into separate enable and disable routes;
- add a new combined action or change policy syntax;
- change user status persistence or replication;
- redesign Console permissions;
- infer release, image, deployment, or production delivery from a source merge.

## Alternatives considered {#alternatives}

### Keep checking `admin:EnableUser` for both states {#always-enable}

This preserves behavior but leaves `admin:DisableUser` unusable and forces over-privileged policies. It is the defect, not a compatibility contract worth retaining.

### Require both actions for either transition {#require-both}

This makes the two labels decorative and prevents delegated disable-only operation. It is stricter in quantity but weaker in expressiveness and least privilege.

### Try Enable authorization, then retry Disable authorization {#double-validation}

Upstream PR #21482 attempted this shape for a disabled request. It first called `validateAdminReq` with `EnableUser`, then called it again with `DisableUser` if the first result was nil.

That helper has an important contract: when it returns a nil object layer, it has already written an error response. A Disable-only request can therefore commit a 403 response before the second authorization succeeds and the handler proceeds to mutate account state. Authorization fallback must never continue after an error response has been committed.

### Accept either Enable or Disable for a disabled request {#allow-either}

`validateAdminReq` already accepts multiple actions and succeeds if any one is allowed, so compatibility behavior could be implemented safely with one variadic call. That would let Disable-only policies work while preserving the historical ability of Enable-only policies to disable.

SILO rejected this option because the historical ability was the enforcement bug. It would solve the reporter's positive case but retain a cross-action privilege that contradicts the two-action model. Operators who want both transitions can grant both actions explicitly.

### Validate the status before authenticating {#validate-first}

Rejecting unknown status values first would change error precedence: a caller that previously had to pass the Enable authorization gate could now receive a validation result before authorization. The repair does not need that broader behavioral change.

Unknown values therefore retain `admin:EnableUser` as the authorization default. Valid `disabled` is the only value that selects `admin:DisableUser`; the existing IAM layer remains responsible for rejecting invalid status values after authorization.

## The selected implementation {#implementation}

The repair adds a pure selector:

```go
func setUserStatusAdminAction(status string) policy.AdminAction {
    if madmin.AccountStatus(status) == madmin.AccountDisabled {
        return policy.DisableUserAdminAction
    }
    return policy.EnableUserAdminAction
}
```

The handler reads the route variables, selects the action, and authorizes exactly once:

```go
vars := mux.Vars(r)
accessKey := vars["accessKey"]
status := vars["status"]

objectAPI, creds := validateAdminReq(ctx, w, r, setUserStatusAdminAction(status))
if objectAPI == nil {
    return
}
```

Everything after the gate remains unchanged:

- a caller still cannot enable or disable its own account;
- `globalIAMSys.SetUserStatus` validates and persists the requested status;
- site replication records the same status and timestamp;
- response and audit behavior use the existing path.

The selector depends only on the requested target state. It does not load the current user, infer a transition from stored state, or make authorization depend on whether the target exists. This keeps authorization deterministic and avoids a read-before-authentication dependency.

## Why the repair is safe {#safety}

The correctness argument consists of five invariants:

1. Every valid status maps to exactly one Admin Action.
2. `validateAdminReq` is invoked once, so a failed authorization cannot be followed by mutation.
3. The mutation call is reachable only after the selected action succeeds.
4. Invalid status values preserve the old Enable authorization boundary and are still rejected by the existing status-validation path.
5. No storage, replication, wire, or client contract changes; only the permission required to reach the existing mutation changes.

The change is a deliberate authorization tightening for Enable-only custom policies that used the disable operation. That tightening is the mechanism that makes `admin:DisableUser` a real independent capability.

## Test design {#tests}

### Pure action mapping {#mapping-test}

The unit test fixes three selector cases:

| Input | Expected action |
| --- | --- |
| `enabled` | `EnableUser` |
| `disabled` | `DisableUser` |
| invalid | legacy `EnableUser` default |

### Four-way IAM authorization matrix {#iam-test}

The integration test creates separate users and policies, then exercises the real Admin API:

1. a Disable-only client successfully disables a target;
2. the same client receives `AccessDenied` when enabling it;
3. an Enable-only client successfully enables the target;
4. the same client receives `AccessDenied` when disabling it.

Positive assertions alone would not prove least privilege: both policies could accidentally authorize both states and still pass. The two negative cross-action assertions are the security regression tests.

The test removes every temporary user and policy after execution. It runs inside the existing IAM server suite, so it covers request signing, policy attachment, handler authorization, persistence, and Admin-client error decoding rather than testing only the helper.

## Repair and verification record {#verification}

The server checkout originally contained unrelated dependency, generated-credit, checksum-test, and security-document changes, while local `main` was behind the remote. The two user-status files were isolated into a clean worktree based on current `origin/main`; no unrelated file entered the repair commit.

Local verification passed:

```text
go test ./cmd -run '^TestSetUserStatusAdminAction$' -count=1
go test ./cmd -run '^TestIAMInternalIDPServerSuite$' -count=1
git diff --check
```

The signed-off commit `58735ee38` was pushed in PR #73. Its eight remote checks all passed:

- DCO sign-off;
- format, build, and vet;
- lint and generated files;
- `cmd/` tests;
- `internal/` tests;
- race detector and S3 Select;
- cross compilation;
- vulnerability analysis.

The PR was merged with the repository's normal merge strategy as `2e2377d1c`. Local `main` was then fast-forwarded only after the two original working files were byte-for-byte and patch-ID identical to the merged result. The unrelated local changes remained intact, and the temporary worktree and task branch were removed after the code became recoverable from `main` and PR #73.

## Least-privilege policy examples {#examples}

### Disable-only operator {#disable-only}

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

This principal can inspect and disable another user, but cannot enable it.

### Enable-only operator {#enable-only}

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

This principal can inspect and enable another user, but cannot disable it. Grant both actions explicitly to roles responsible for the complete account lifecycle.

## Compatibility and migration {#compatibility}

No client or API migration is required. The endpoint, query parameters, status strings, success response, and Admin-client method are unchanged.

Policy review is required for restricted administrative roles:

- a role that should only disable users needs `admin:DisableUser`;
- a role that should only enable users needs `admin:EnableUser`;
- a role that must do both needs both actions;
- `consoleAdmin` and other `admin:*` policies are unaffected;
- a legacy custom policy containing only `admin:EnableUser` can no longer use that permission to disable users and must add `admin:DisableUser` if both operations are intended.

This is a source-level compatibility change in authorization behavior, not a wire-protocol break.

## Upstream disposition {#upstream}

As of this record, upstream issue #21478 and PR #21482 are still displayed as open. The upstream repository is archived and read-only. An attempt to leave the single-authorization analysis on the PR was rejected by GitHub because archived, locked discussions cannot accept comments.

The upstream artifacts remain useful provenance but are no longer an actionable delivery path. SILO owns its implemented semantics, tests, merge, release note, and eventual production verification.

## Delivery state {#delivery}

| Gate | State on 2026-08-26 |
| --- | --- |
| Design decision | complete |
| Implementation and local tests | complete |
| Signed-off commit and push | complete |
| PR CI and merge into SILO `main` | complete |
| Tagged SILO release | not established |
| Release package or container image | not established |
| Deployment | not established |
| Production behavior | not established |
| Upstream merge | unavailable; repository archived |

## Conclusion {#conclusion}

The repair makes the authorization model tell the truth. Enabling and disabling are opposite state transitions with different operational risk, and SILO already exposes different policy actions for them. The handler must therefore select the action from the requested target state and authorize once before mutation.

The code change is small because the design boundary is clear. The durable result is larger: an explicit permission matrix, rejected compatibility alternatives, an invalid-input rule, a four-way integration test, a clean merge record, migration guidance, and an honest release boundary.
