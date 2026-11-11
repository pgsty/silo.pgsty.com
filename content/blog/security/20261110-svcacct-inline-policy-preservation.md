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
**Client & UI notes:** Policy-less edits preserve inline policies without client changes; **[mcli 20261112](/blog/release/mcli-20261112/)** ([`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf), [`pgsty/mc#78`](https://github.com/pgsty/mc/issues/78)) extends explicit empty-policy resets from `admin user svcacct set --policy` to `svcacct edit`, `admin accesskey edit`, `idp ldap accesskey edit`, and `idp openid accesskey edit`, and **[SILO Console 2.7.1](/blog/release/console-2.7.1/)** ([`SN-2026-025`](/blog/security/20261111-iam-import-status-and-console-policy/)) resets inline restrictions by turning off **Restrict beyond user policy** (whereas in Console v2.7.0, enter `{}` or `{"Statement":[]}`)

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

| Date    | Commit                                                                                                       | Origin                    | Change                                                                                                                                                                                                                                                                                                                                                                |
| :------ | :----------------------------------------------------------------------------------------------------------- | :------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2022-05 | [`f0462322f`](https://github.com/pgsty/silo/commit/f0462322fd9944f03ad65ac67897cc76469b4e88) (`minio#14847`) | Upstream MinIO            | To fix `minio#14784` ("allow removing an embedded policy"), deleted `sessionPolicy` and set `inherited-policy` whenever `opts.sessionPolicy == nil`, conflating "policy omitted" with "remove policy"                                                                                                                                                                 |
| 2023-10 | [`33322e663`](https://github.com/pgsty/silo/commit/33322e6638b00869d00a2397084a6e8a87e1e0f6) (`minio#18346`) | Upstream MinIO            | Folded parsed empty policy documents (`sp.Version == "" && len(sp.Statements) == 0`) into `sp = nil` in `UpdateServiceAccount` and updated `InfoServiceAccount` to report `ImpliedPolicy`                                                                                                                                                                             |
| 2024-09 | [`5bd27346a`](https://github.com/pgsty/silo/commit/5bd27346ac5518bb8a47f176ae930cf6741be615) (`minio#20432`) | Upstream MinIO            | Defined `nosp := opts.sessionPolicy == nil \|\| opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0` in `UpdateServiceAccount` while keeping the handler's `sp = nil` collapse                                                                                                                                                                |
| 2026-09 | [`59989f8`](https://github.com/pgsty/mc/commit/59989f8a0ddf81d9a20329bd411ddf2bed7bbb6c) (`pgsty/mc#27`)     | PGSTY `mcli` (`20260903`) | Allowed `mcli admin user svcacct set --policy` with an empty document (`{"Statement":[]}`) to reset an inline policy (extended to `svcacct edit`, `admin accesskey edit`, and `idp ldap/openid accesskey edit` in [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf) / [`pgsty/mc#78`](https://github.com/pgsty/mc/issues/78)) |
| 2026-11 | [`a0de92fcb`](https://github.com/pgsty/silo/commit/a0de92fcb) (`pgsty/silo#321`)                             | PGSTY SILO (`20261109`)   | Extracted `updatedServiceAccountCredentials` in `cmd/iam-store.go` so edits mutate stored records directly, carrying over the upstream `nosp` check unchanged                                                                                                                                                                                                         |
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

| Design Question                                                                                                   | Chosen Approach in `c11bfda8f`                                                                                | Benefit                                                                                                                                                                                                                                                                           | Trade-Off / Operational Cost                                                                                                                                                                                                                                                                                                                                                                                      |
| :---------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **How to express "clear inline policy" vs. "keep inline policy"**                                                 | Keep `nil`/`null` as "no change"; use an explicit empty policy document (`{}` or `{"Statement":[]}`) to clear | Zero wire-protocol or `madmin-go` struct changes; `mcli admin user svcacct set --policy` already supported `{"Statement":[]}` (and [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf) extends this to `svcacct edit` and `accesskey edit`) | Custom API clients that omitted `newPolicy` expecting to clear an inline policy must send `{}` or `{"Statement":[]}` instead                                                                                                                                                                                                                                                                                      |
| **SILO Console v2.7.0 policy editor blank submission**                                                            | Leave server strict (`""` normalized to omitted `newPolicy` by Console keeps the policy)                      | Prevents accidental policy erasure; fails closed (preserving restrictions) until Console is updated                                                                                                                                                                               | In Console v2.7.0, deleting all text in the policy editor and saving no longer clears the inline policy; operators must type `{}` or `{"Statement":[]}` (resolved in Console `main` via [`SN-2026-025`](/blog/security/20261111-iam-import-status-and-console-policy/) by turning off **Restrict beyond user policy**)                                                                                            |
| **Versioned empty policy (`{"Version":"2012-10-17","Statement":[]}`) and versionless non-empty policy on update** | Kept existing update no-op behavior untouched in `c11bfda8f`                                                  | Avoided coupling policy-normalization changes into the initial 18-line hotfix                                                                                                                                                                                                     | Resolved on `main` in follow-up [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed) ([#339](https://github.com/pgsty/silo/issues/339)): versioned empty policies now also reset inheritance, versionless non-empty updates receive the default `Version`, and historical pre-`20261111` empty `embedded-policy` deny-all accounts stay deny-all across policy-less edits |
| **Pre-existing site-replication patch ordering and mixed cache/storage reads**                                    | Kept `c11bfda8f` scoped to the 18-line nil/empty fix; addressed snapshot replication in a separate commit     | Kept the initial security fix minimal, reviewable, and rollback-safe without altering replication item types in one commit                                                                                                                                                        | Resolved on `main` in follow-up [`da8d8a54b`](https://github.com/pgsty/silo/commit/da8d8a54b1f0128c9f89b3ee5c6845cf05490440) (`SRSvcAccCreate` full stored-record snapshots)                                                                                                                                                                                                                                      |
{.wide .expand}

### Why Adjacent Policy Shapes and Replication Snapshots Were Kept Separate in `#331` {#boundaries}

During adversarial code review of [PR #331](https://github.com/pgsty/silo/pull/331), two adjacent questions were evaluated and deliberately separated from `c11bfda8f` (both have since landed on `main` ahead of the next release):

1. **Why `c11bfda8f` did not change `{"Version":"2012-10-17","Statement":[]}` or versionless non-empty policies in the same commit:**
   In `c11bfda8f`, `updatedServiceAccountCredentials` still checked `if opts.sessionPolicy.Version != "" && len(opts.sessionPolicy.Statements) > 0` for the overwrite branch:
   - `{"Version":"2012-10-17","Statement":[]}` acted as a no-op in `c11bfda8f` alone, and a policy document with statements but no `"Version"` field was accepted by `AddServiceAccount` while ignored on `UpdateServiceAccount`. Follow-up commit [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed) ([#339](https://github.com/pgsty/silo/issues/339), [`SN-2026-025`](/blog/security/20261111-iam-import-status-and-console-policy/)) subsequently unified all empty policy documents (`{}`, `{"Statement":[]}`, and `{"Version":"2012-10-17","Statement":[]}`) to reset inline restrictions, populated the default `Version` on non-empty versionless updates, and preserved historical pre-`20261111` empty `embedded-policy` deny-all accounts across policy-less edits.

2. **Why `c11bfda8f` did not bundle site-replication snapshot refactoring:**
   Adversarial review noted two pre-existing site-replication issues: (a) `UpdateServiceAccount` replicated partial field patches (`SRSvcAccUpdate`), so if a metadata-only edit at timestamp $t_2$ arrived at a peer before a policy or secret-key edit at $t_1 < t_2$, the peer's timestamp check rejected the late $t_1$ patch; and (b) initial sync, heal, and IAM export read the identity timestamp from storage but read claims/policy from the local node cache. Follow-up commit [`da8d8a54b`](https://github.com/pgsty/silo/commit/da8d8a54b1f0128c9f89b3ee5c6845cf05490440) subsequently replaced partial service-account replication patches with authoritative stored-record snapshots (`SRSvcAccCreate`).

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
   - **Via `mcli`:** Pass an empty policy document (`{}` or `{"Statement":[]}`, or `{"Version":"2012-10-17","Statement":[]}` on `1d714834c`+) to `--policy` (supported in `mcli 20261109` via `admin user svcacct set --policy`, and in **[mcli 20261112](/blog/release/mcli-20261112/)** across `svcacct edit`, `admin accesskey edit`, `idp ldap accesskey edit`, and `idp openid accesskey edit` via [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf)):
     ```shell
     mcli admin user svcacct edit myminio/ <access-key> --policy /path/to/empty-policy.json
     ```
   - **Via SILO Console:** In **[Console 2.7.1](/blog/release/console-2.7.1/)** ([`SN-2026-025`](/blog/security/20261111-iam-import-status-and-console-policy/)), turn off **Restrict beyond user policy** and save (while the toggle remains on, empty policy documents are rejected to prevent accidental resets). On older Console v2.7.0 builds, enter `{}` or `{"Statement":[]}` in the access-key policy editor and save.

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-021), [`mcli admin user svcacct edit`](/reference/minio-mc-admin/mc-admin-user-svcacct-edit/), and the [Component Version Matrix](/compatibility/versions/).
