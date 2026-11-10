---
title: "SN-2026-021: Service-Account Inline Policy Stripped by Policy-Less Updates"
linkTitle: "SN-2026-021 · Service Account Policy Reset"
date: 2026-11-10
author: "Ruohang Feng"
description: "UpdateServiceAccount treated an omitted or null newPolicy field identically to an explicit empty policy document, stripping a service account's inline restriction and elevating it to its parent user's full permissions on any status toggle, secret rotation, rename, description change, or expiry update."
tags: [Security, IAM, Service Account, Access Control, Site Replication, SILO]
weight: 1
draft: false
url: "/blog/security/20261110-svcacct-inline-policy-preservation/"
---

**Status:** Fixed on `main` ([`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27), merged via [PR #331](https://github.com/pgsty/silo/pull/331) as [`244de7ecc`](https://github.com/pgsty/silo/commit/244de7ecc1ce33f4f3e7ec452395993eb2449f11)); scheduled for the post-[`20261109`](/blog/release/silo-20261109/) Server hotfix release\
**Identifier:** `SN-2026-021` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-021))\
**Severity:** High\
**Affected scope:** **SILO Server** (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO releases since `2022-05`\
**Client & UI notes:** `mcli` and `silo-pkg` require no changes; in **SILO Console v2.7.0**, clearing the access-key policy editor to blank no longer removes an inline policy (enter `{}` or `{"Statement":[]}` to clear it)

In SILO (and inherited MinIO), a service account (access key) is derived from a parent user and can optionally carry an inline session policy (`sub-policy`) that restricts the access key to a subset of its parent user's permissions. Before [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27), `POST /minio/admin/v3/update-service-account` collapsed "no policy field provided in the update request" and "an empty policy document provided to clear the inline restriction" into a single `nil` state. Any administrative update that omitted `--policy`—including disabling and re-enabling a service account, rotating its secret key, or updating its name, description, or expiration—deleted the embedded policy from the stored credential token and re-signed the account as `inherited-policy`, silently elevating the key to its parent user's full permissions.

## Summary {#summary}

- **Root cause:** `updatedServiceAccountCredentials` (`cmd/iam-store.go`) deleted `sessionPolicy` from the credential's JWT claims whenever `opts.sessionPolicy == nil`, and `(adminAPIHandlers).UpdateServiceAccount` (`cmd/admin-handlers-users.go`) set `sp = nil` both when `updateReq.NewPolicy` was absent and when it parsed to an empty policy (`sp.Version == "" && len(sp.Statements) == 0`).
- **Impact:** Routine administrative lifecycle operations (`mcli admin user svcacct disable` + `enable`, or `svcacct edit` / `idp ldap accesskey edit` without `--policy`) silently stripped a service account's inline restriction on the local cluster and across replication peers, promoting a least-privilege key (such as read-only `s3:GetObject` on one prefix) to the parent user's full permissions.
- **Provenance:** Inherited from upstream MinIO's May 2022 commit [`f0462322f`](https://github.com/pgsty/silo/commit/f0462322fd9944f03ad65ac67897cc76469b4e88) (`minio/minio#14847`), compounded by October 2023 commit [`33322e663`](https://github.com/pgsty/silo/commit/33322e6638b00869d00a2397084a6e8a87e1e0f6) (`minio/minio#18346`) and September 2024 commit [`5bd27346a`](https://github.com/pgsty/silo/commit/5bd27346ac5518bb8a47f176ae930cf6741be615) (`minio/minio#20432`).
- **Fix:** Commit [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) ([PR #331](https://github.com/pgsty/silo/pull/331)) separates `opts.sessionPolicy == nil` (no policy change requested; keep the embedded policy) from a non-nil empty policy struct (`Version == ""` and `len(Statements) == 0`, which removes the embedded policy). Literal JSON `null` in `newPolicy` is treated as no policy change.

---

## 1. Discovery {#discovery}

We verified all private GitHub Security Advisories (`GHSA-*`) and public issues across `pgsty/silo`, `pgsty/mc`, `pgsty/silo-console`, and `pgsty/silo-pkg` to confirm the reporting source: this issue did not originate from an external GHSA submission. Instead, it was uncovered on November 10, 2026 during our internal post-release security audit of [SILO Server 20261109](/blog/release/silo-20261109/), conducted alongside the verification of the private GHSA queue.

Specifically, while auditing the stored-record IAM mutation helpers introduced in `Server 20261109` ([#320](https://github.com/pgsty/silo/issues/320), [#321](https://github.com/pgsty/silo/issues/321))—which moved service-account credential updates into `updatedServiceAccountCredentials` (`cmd/iam-store.go`)—we inspected how `opts.sessionPolicy` handled partial metadata updates. Live testing against both `Server 20261026` and `Server 20261109` confirmed that creating a service account restricted to `s3:GetObject` under a `readwrite` parent user and then running `mcli admin user svcacct disable` followed by `mcli admin user svcacct enable` immediately allowed the service account to `PutObject` and `DeleteObject`.

### Clarification on `svcacct info` Output {#info-output}

An early internal triage note stated that `svcacct info` still displayed `"inline"` after the status toggle. Code inspection and live reproduction clarified the exact observability behavior:

1. **What `svcacct info` displays:** `InfoServiceAccount` (`cmd/admin-handlers-users.go`) computes `ImpliedPolicy := sessionPolicy == nil || (sessionPolicy.Version == "" && len(sessionPolicy.Statements) == 0)`, and `mcli admin user svcacct info` (`cmd/admin-user-svcacct-add.go`) prints `Policy: embedded` when `ImpliedPolicy` is `false` and `Policy: implied` when `ImpliedPolicy` is `true`. Once the inline policy is stripped, `mcli admin user svcacct info` reports `Policy: implied` (and `svcacct info --policy` prints the parent user's combined policy).
2. **Why the escalation goes unnoticed in practice:** Neither `mcli admin user svcacct disable`, `enable`, nor `edit` (when called with `--secret-key`, `--name`, `--description`, or `--expiry`) mentions or prints policy state—each command simply outputs `Disabled/Enabled/Edited service account '...' successfully`. An operator temporarily disabling a restricted key during maintenance or rotating its secret key has no indication that the command also erased its access boundary.

---

## 2. Provenance and Root Cause {#provenance}

### How Service-Account Inline Policies Are Stored and Evaluated {#storage-model}

A service account is stored as a `UserIdentity` record whose `Credentials.SessionToken` is a server-signed JWT containing the account's claims:

- **Restricted (`embedded-policy`):** When created or updated with a non-empty inline policy, the server base64-encodes the policy JSON into the `sessionPolicy` claim and sets `sa-policy-type: "embedded-policy"`. During S3 or Admin request authorization, `IsAllowedServiceAccount` (`cmd/iam.go`) requires **both** the parent user's policies and the decoded `sessionPolicy` to allow the request (`isAllowedSP && parentAllowed`).
- **Unrestricted (`inherited-policy`):** When no inline policy is attached, the JWT omits `sessionPolicy` and sets `sa-policy-type: "inherited-policy"`. `IsAllowedServiceAccount` evaluates only the parent user's (and parent groups') attached policies.

### Two-Layer Collapse of "Omitted" and "Empty" {#two-layer-collapse}

The Admin API endpoint `POST /minio/admin/v3/update-service-account` accepts an encrypted JSON payload matching `madmin.UpdateServiceAccountReq`:

```go
type UpdateServiceAccountReq struct {
    NewPolicy      json.RawMessage `json:"newPolicy,omitempty"`
    NewSecretKey   string          `json:"newSecretKey,omitempty"`
    NewName        string          `json:"newName,omitempty"`
    NewDescription string          `json:"newDescription,omitempty"`
    NewStatus      string          `json:"newStatus,omitempty"`
    NewExpiration  *time.Time      `json:"newExpiration,omitempty"`
}
```

Before [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27), the HTTP handler and the IAM store collapsed three distinct inputs—(a) `newPolicy` omitted, (b) `"newPolicy": null`, and (c) an explicit empty policy document such as `{"Statement":[]}`—into the same internal representation:

1. **Handler layer (`(adminAPIHandlers).UpdateServiceAccount` in `cmd/admin-handlers-users.go`):**
   ```go
   var sp *policy.Policy
   if len(updateReq.NewPolicy) > 0 {
       sp, err = policy.ParseConfigStrict(bytes.NewReader(updateReq.NewPolicy))
       if err != nil {
           writeErrorResponseJSON(ctx, w, toAdminAPIErr(ctx, err), r.URL)
           return
       }
       if sp.Version == "" && len(sp.Statements) == 0 {
           sp = nil
       }
   }
   ```
   When `NewPolicy` was omitted (`len == 0`), `sp` remained `nil`. When `NewPolicy` was an explicit empty policy document (`{}` or `{"Statement":[]}`) or JSON `null`, `ParseConfigStrict` returned `&policy.Policy{Version: "", Statements: nil}`, and the handler immediately overwrote `sp = nil`.

2. **Store layer (`updatedServiceAccountCredentials` in `cmd/iam-store.go`):**
   ```go
   nosp := opts.sessionPolicy == nil || opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0

   // sessionPolicy is nil and there is embedded policy attached we remove
   // embedded policy at that point.
   if _, ok := m.Lookup(policy.SessionPolicyName); ok && nosp {
       m.Delete(policy.SessionPolicyName)
       m.Set(iamPolicyClaimNameSA(), inheritedPolicyType)
   }
   ```
   Because `nosp` evaluated to `true` whenever `opts.sessionPolicy == nil`, every update request that left `sp == nil` deleted `sessionPolicy` from the JWT claims `m`, changed `sa-policy-type` to `"inherited-policy"`, and re-signed `cr.SessionToken`.

### Upstream Git Lineage {#upstream-history}

Tracing `cmd/iam-store.go` and `cmd/admin-handlers-users.go` shows that this behavior originated in upstream `minio/minio` in May 2022:

| Date    | Commit                                                                                                       | Origin                    | Change                                                                                                                                                                                                 |
| :------ | :----------------------------------------------------------------------------------------------------------- | :------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2022-05 | [`f0462322f`](https://github.com/pgsty/silo/commit/f0462322fd9944f03ad65ac67897cc76469b4e88) (`minio#14847`) | Upstream MinIO            | To fix `minio#14784` ("allow removing an embedded policy"), deleted `sessionPolicy` and set `inherited-policy` whenever `opts.sessionPolicy == nil`, conflating "policy omitted" with "remove policy"  |
| 2023-10 | [`33322e663`](https://github.com/pgsty/silo/commit/33322e6638b00869d00a2397084a6e8a87e1e0f6) (`minio#18346`) | Upstream MinIO            | Folded parsed empty policy documents (`sp.Version == "" && len(sp.Statements) == 0`) into `sp = nil` in `UpdateServiceAccount` and updated `InfoServiceAccount` to report `ImpliedPolicy`              |
| 2024-09 | [`5bd27346a`](https://github.com/pgsty/silo/commit/5bd27346ac5518bb8a47f176ae930cf6741be615) (`minio#20432`) | Upstream MinIO            | Defined `nosp := opts.sessionPolicy == nil \|\| opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0` in `UpdateServiceAccount` while keeping the handler's `sp = nil` collapse |
| 2026-09 | [`59989f8`](https://github.com/pgsty/mc/commit/59989f8a0ddf81d9a20329bd411ddf2bed7bbb6c) (`pgsty/mc#27`)     | PGSTY `mcli` (`20260903`) | Documented and preserved `mcli admin user svcacct edit --policy` with an empty document (`{"Statement":[]}`) as the explicit client contract for resetting an inline policy                            |
| 2026-11 | [`a0de92fcb`](https://github.com/pgsty/silo/commit/a0de92fcb) (`pgsty/silo#321`)                             | PGSTY SILO (`20261109`)   | Extracted `updatedServiceAccountCredentials` in `cmd/iam-store.go` so edits mutate stored records directly, carrying over the upstream `nosp` check unchanged                                          |
{.wide .expand}

---

## 3. Trigger Conditions {#triggers}

The inline policy reset is triggered whenever all three conditions hold:

1. **Target account has an inline session policy:** The target credential is a service account (or LDAP/OpenID access key) currently configured with `sa-policy-type: "embedded-policy"` that narrows its parent user's permissions.
2. **Authorized administrative caller:** The request is made by a principal holding `admin:UpdateServiceAccount` or by the parent user managing their own service accounts. (A restricted service account cannot call `UpdateServiceAccount` to strip its own policy; [`CVE-2025-62506`](/blog/security/cve-2025-62506/) and [`SN-2026-017`](/about/security-advisories/#sn-2026-017) block self-escalation.)
3. **Update request omits a replacement policy:** Any of the following routine operations sends `UpdateServiceAccountReq` without `newPolicy` (or with `"newPolicy": null`):
   - **Status toggle:** `mcli admin user svcacct disable ALIAS ACCESSKEY` or `mcli admin user svcacct enable ALIAS ACCESSKEY` (and `mcli admin accesskey disable/enable` or `mcli idp ldap accesskey disable/enable`).
   - **Secret rotation or metadata edit without `--policy`:** `mcli admin user svcacct edit` (or `set`) with `--secret-key`, `--name`, `--description`, or `--expiry` and without `--policy` (and the `idp ldap accesskey edit` equivalents).
   - **Site replication peer reception:** When an administrator performs any of the edits above on a non-root user's service account, `IAMChangeHook` forwards `SRSvcAccUpdate` (with an empty `SessionPolicy`) to all replication peers, where `PeerSvcAccChangeHandler` (`cmd/site-replication.go`) invokes `UpdateServiceAccount` with `sp = nil`.

---

## 4. Impact Scope {#impact}

| Dimension                         | Impact Details                                                                                                                                                                                                                                                               |
| :-------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Permission boundary widening**  | The service account immediately loses its embedded `sessionPolicy` intersection filter and inherits every S3 and Admin permission attached to its parent user and the parent user's groups.                                                                                  |
| **Identity providers affected**   | Built-in IDP service accounts, AD/LDAP access keys (`idp ldap accesskey`), and OpenID-parented service accounts stored in `.minio.sys/iam/` or `etcd`. Temporary STS tokens (`AssumeRole*`) use an immutable token path and are unaffected.                                  |
| **Multi-site replication reach**  | For any non-root parent user (`svcAccount.ParentUser != globalActiveCred.AccessKey`), the policy-less update is replicated to peer sites and strips the inline policy on every peer. (Service accounts owned by the cluster root user are not replicated across sites.)      |
| **Durability of the policy loss** | Deleting `sessionPolicy` from the JWT claims and re-signing `cr.SessionToken` overwrites the stored credential record in `.minio.sys/iam/` (or `etcd`). Upgrading the server binary prevents future stripping but cannot reconstruct an inline policy that was already lost. |
{.wide .expand}

---

## 5. Fix: Sufficiency and Necessity {#fix}

Commit [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) ([PR #331](https://github.com/pgsty/silo/pull/331)) changes 18 lines across `cmd/admin-handlers-users.go` and `cmd/iam-store.go`:

```go
// cmd/admin-handlers-users.go — (adminAPIHandlers).UpdateServiceAccount
// A request without a policy, or with a JSON null for one, keeps the
// policy the account has. An empty policy document is passed on as
// such: it is the request to remove the embedded policy.
var sp *policy.Policy
if len(updateReq.NewPolicy) > 0 && !bytes.Equal(updateReq.NewPolicy, []byte("null")) {
    sp, err = policy.ParseConfigStrict(bytes.NewReader(updateReq.NewPolicy))
    if err != nil {
        writeErrorResponseJSON(ctx, w, toAdminAPIErr(ctx, err), r.URL)
        return
    }
}
```

```go
// cmd/iam-store.go — updatedServiceAccountCredentials
// A nil sessionPolicy is an edit that does not concern the policy, and
// the embedded one stays. Only a policy that was given, and is empty,
// removes it: the account then has all its parent is allowed, which is
// usually more.
reset := opts.sessionPolicy != nil && opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0
if _, ok := m.Lookup(policy.SessionPolicyName); ok && reset {
    m.Delete(policy.SessionPolicyName)
    m.Set(iamPolicyClaimNameSA(), inheritedPolicyType)
}
```

The resulting state transition table for an account that currently has an embedded policy `P` is:

| `newPolicy` in Request                         | Parsed `opts.sessionPolicy`                          | Behavior Before Fix         | Behavior After Fix (`c11bfda8f`) |
| :--------------------------------------------- | :--------------------------------------------------- | :-------------------------- | :------------------------------- |
| Omitted (`len == 0`)                           | `nil`                                                | Strips `P` (`implied`)      | **Keeps `P` (`embedded`)**       |
| Literal JSON `null`                            | `nil`                                                | Strips `P` (`implied`)      | **Keeps `P` (`embedded`)**       |
| `{}` or `{"Statement":[]}` or `{"Version":""}` | Non-nil `&policy.Policy{Version:"", Statements:nil}` | Strips `P` (`implied`)      | **Strips `P` (`implied`)**       |
| Valid non-empty policy `P'`                    | Non-nil `&policy.Policy{...}`                        | Replaces `P` with `P'`      | **Replaces `P` with `P'`**       |
| Malformed JSON (`""`, `[]`, `0`, invalid ARN)  | Parse error (`400`)                                  | Rejects request (`Keeps P`) | **Rejects request (`Keeps P`)**  |
{.wide .expand}

### Why the Fix Is Necessary {#necessary}

1. **Separating "not specified" from "clear" in the store and handler:** On the wire, status changes (`disable`/`enable`) and metadata edits (`--secret-key`, `--name`, `--description`, `--expiry`) omit `newPolicy`. As long as the handler folds empty policy documents into `sp = nil` and the store treats `opts.sessionPolicy == nil` as a reset, the server cannot preserve an inline policy across metadata edits while still supporting intentional resets. Removing the handler's `sp = nil` collapse and requiring `opts.sessionPolicy != nil` for `reset` in the store is the minimal two-point change that separates the two states.
2. **Why the explicit `"null"` check is required:** `UpdateServiceAccountReq.NewPolicy` has type `json.RawMessage` (`[]byte`). When a JSON caller sends `"newPolicy": null`—or when `SRSessionPolicy` (which also wraps `json.RawMessage`) serializes a `nil` slice as `null` on the wire—`encoding/json` strips surrounding whitespace and populates `updateReq.NewPolicy` with the 4-byte slice `[]byte("null")`. Because `json.NewDecoder(bytes.NewReader([]byte("null"))).Decode(&p)` inside `policy.ParseConfigStrict` succeeds as a no-op and returns a non-nil zero `&policy.Policy{}`, omitting `!bytes.Equal(updateReq.NewPolicy, []byte("null"))` would misclassify `"newPolicy": null` as an explicit empty policy document and still strip the policy.

### Why the Fix Is Sufficient {#sufficient}

1. **Single store chokepoint across all backends and callers:** Both the object-store backend (`.minio.sys/iam/`) and the `etcd` backend update service accounts exclusively through `updatedServiceAccountCredentials` (`cmd/iam-store.go`). No other local handler mutates an existing service account's `SessionToken` claims: `AddServiceAccount` rejects existing access keys ([#322](https://github.com/pgsty/silo/issues/322)), LDAP group refresh modifies only group memberships, and STS credentials use a separate immutable path.
2. **Replication peer handler works without wire-format changes:** In `PeerSvcAccChangeHandler` (`cmd/site-replication.go`), `sp` starts as `nil` and is parsed only when `len(u.SessionPolicy) > 0`. When an origin site forwards a policy-less edit, `u.SessionPolicy` unmarshals to `nil` (empty slice), so the peer passes `sessionPolicy: nil` to `UpdateServiceAccount` and preserves the embedded policy. When an origin site forwards `{}` or `{"Statement":[]}`, `u.SessionPolicy` is non-empty, `ParseConfig` returns a non-nil empty `&policy.Policy{}`, and the peer resets the policy to `inherited-policy`.
3. **Monotone permission invariant:** Built-in IAM evaluates an embedded policy as `isAllowedSP && parentAllowed` (`cmd/iam.go:2343`). Because the fix only changes the outcome for `nil` and `null` policies—by keeping the existing embedded filter instead of deleting it—a patched server can never grant broader permissions than an unpatched server for any request sequence.

---

## 6. Design Trade-Offs and Boundaries {#tradeoffs}

| Design Question                                                                                                   | Chosen Approach in `c11bfda8f`                                                                                | Benefit                                                                                                                       | Trade-Off / Operational Cost                                                                                                                                                |
| :---------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ | :---------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **How to express "clear inline policy" vs. "keep inline policy"**                                                 | Keep `nil`/`null` as "no change"; use an explicit empty policy document (`{}` or `{"Statement":[]}`) to clear | Zero wire-protocol or `madmin-go` struct changes; `mcli admin user svcacct edit --policy` already supports `{"Statement":[]}` | Custom API clients that omitted `newPolicy` expecting to clear an inline policy must send `{}` or `{"Statement":[]}` instead                                                |
| **SILO Console v2.7.0 policy editor blank submission**                                                            | Leave server strict (`""` normalized to omitted `newPolicy` by Console keeps the policy)                      | Prevents accidental policy erasure; fails closed (preserving restrictions) until Console is updated                           | In Console v2.7.0, deleting all text in the policy editor and saving no longer clears the inline policy; operators must type `{}` or `{"Statement":[]}` (Console follow-up) |
| **Versioned empty policy (`{"Version":"2012-10-17","Statement":[]}`) and versionless non-empty policy on update** | Keep existing update no-op behavior untouched in this hotfix                                                  | Avoids breaking Console saves on inherited-policy accounts (where Console may echo an empty versioned policy)                 | Updating an account with a versionless statement list still returns `204` without applying the change; tracked as a separate validation item                                |
| **Pre-existing site-replication patch ordering and mixed cache/storage reads**                                    | Keep `c11bfda8f` scoped to the 18-line nil/empty fix; address snapshot replication in a separate commit       | Keeps the security hotfix minimal, reviewable, and rollback-safe without altering replication item types in the same commit   | Requires a separate follow-up to replicate full stored-record snapshots so out-of-order replication patches or stale caches cannot lose earlier edits                       |
{.wide .expand}

### Why Adjacent Policy Shapes and Replication Snapshots Were Kept Separate {#boundaries}

During adversarial code review of [PR #331](https://github.com/pgsty/silo/pull/331), two adjacent questions were evaluated and deliberately separated from this commit:

1. **Why not change `{"Version":"2012-10-17","Statement":[]}` or versionless non-empty policies in the same commit?**
   In `updatedServiceAccountCredentials`, the overwrite branch checks `if opts.sessionPolicy.Version != "" && len(opts.sessionPolicy.Statements) > 0`. Consequently, on an update:
   - `{"Version":"2012-10-17","Statement":[]}` neither triggers `reset` (because `Version != ""`) nor overwrites the embedded policy (because `len(Statements) == 0`), acting as a no-op. Treating it as an embedded empty policy (deny-all) would break existing Console flows when saving an inherited-policy account whose parent has no attached policies; treating it as `reset` is unnecessary when `{}` and `{"Statement":[]}` already provide an unambiguous reset.
   - A policy document with statements but no `"Version"` field is accepted by `AddServiceAccount` on creation, but ignored as a no-op on `UpdateServiceAccount`. While that is a usability trap (failing to narrow permissions on update), it never widens an already-restricted account's permissions, and rejecting or embedding it belongs in a dedicated follow-up.

2. **Why not bundle site-replication snapshot refactoring into `c11bfda8f`?**
   Adversarial review noted two pre-existing site-replication issues: (a) `UpdateServiceAccount` replicates partial field patches (`SRSvcAccUpdate`), so if a metadata-only edit at timestamp $t_2$ arrives at a peer before a policy or secret-key edit at $t_1 < t_2$, the peer's timestamp check rejects the late $t_1$ patch; and (b) initial sync, heal, and IAM export read the identity timestamp from storage but read claims/policy from the local node cache. Fixing those requires replacing partial service-account replication patches with authoritative stored-record snapshots (`SRSvcAccCreate`). Keeping `c11bfda8f` strictly focused on the 18-line `nil`-vs-empty semantics ensures that single-site and multi-site nodes stop stripping policies on routine edits immediately, while the replication snapshot change is reviewed and delivered as its own commit.

---

## Remediation and Operator Guidance {#remediation}

1. **Upgrade every SILO Server node and replication peer** to the post-`20261109` hotfix release containing [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) (or build from `main` at [`244de7ecc`](https://github.com/pgsty/silo/commit/244de7ecc1ce33f4f3e7ec452395993eb2449f11) or later). In a multi-site replication deployment, an unpatched peer site will still strip the inline policy when it receives a policy-less update until that peer is also upgraded.
2. **Audit existing service accounts on every site after upgrading:** Because the fix cannot recover inline policies that were erased prior to the upgrade, inspect all service accounts across each site and check whether accounts that were intended to be restricted now report `Policy: implied`:
   ```shell
   mcli admin user svcacct list myminio/ <username>
   mcli admin user svcacct info myminio/ <access-key>
   ```
   For any service account that should carry an inline restriction but shows `Policy: implied`, reapply its policy document on the upgraded deployment (or rotate and recreate the service account with `--policy`):
   ```shell
   mcli admin user svcacct edit myminio/ <access-key> --policy /path/to/restricted-policy.json
   ```
3. **Clearing an inline policy intentionally:**
   - **Via `mcli`:** Pass an empty policy document (`{}` or `{"Statement":[]}`) to `--policy`:
     ```shell
     mcli admin user svcacct edit myminio/ <access-key> --policy /path/to/empty-policy.json
     ```
   - **Via SILO Console v2.7.0:** Enter `{}` or `{"Statement":[]}` in the access-key policy editor and save (clearing the editor to blank now preserves the existing inline policy).

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-021), [`mcli admin user svcacct edit`](/reference/minio-mc-admin/mc-admin-user-svcacct-edit/), and the [Component Version Matrix](/compatibility/versions/).
