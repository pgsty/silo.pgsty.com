---
title: "SN-2026-025: IAM Cluster Import Re-Enabling Disabled Credentials and Console Inherited-Policy Freezing"
linkTitle: "SN-2026-025 · IAM Import & Console Policy"
date: 2026-11-11
author: "Ruohang Feng"
description: "Importing an IAM archive via ImportIAM silently re-enabled every disabled service account and user group; meanwhile, editing an inherited-policy service account in Console froze a static copy of its parent user's policy onto the key."
tags: [Security, IAM, Service Account, Console, Access Control, SILO]
weight: 1
draft: false
url: "/blog/security/20261111-iam-import-status-and-console-policy/"
---

**Status:** Shipped in **[SILO Console 2.7.1](/blog/release/console-2.7.1/)** ([`1be8a74bf`](https://github.com/pgsty/silo-console/commit/1be8a74bfb86ba3f417204551099fd8a3788f0e2), [`a1a84cab4`](https://github.com/pgsty/silo-console/commit/a1a84cab4d96814af6572f7dce40ad537aa2f81e), [`1fdb279fd`](https://github.com/pgsty/silo-console/commit/1fdb279fd98845b66d7218b2159b434fe76351eb), [`3825ebc44`](https://github.com/pgsty/silo-console/commit/3825ebc44451fdc8eefda3d4ec523a79dfecb236)) and fixed on Server `main` ([`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed), [`34ba7cc1f`](https://github.com/pgsty/silo/commit/34ba7cc1ff3ef8f55888933921ab1e69e2182bf8), pending Server publication)\
**Identifier:** `SN-2026-025` ([Security Advisory Ledger](/about/security-advisories/#sn-2026-025), [#339](https://github.com/pgsty/silo/issues/339), [#345](https://github.com/pgsty/silo/issues/345))\
**Severity:** High\
**Affected scope:** **SILO Server** (`RELEASE.2026-11-09T00-00-00Z` and earlier) and inherited upstream MinIO since `2022-06-23` ([`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f)); **SILO Console** (`v2.7.0` and earlier, standalone and embedded) and inherited upstream MinIO Console since `2024-02-29` ([`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d))\
**Client & UI notes:** Pair the repaired Server and **[Console 2.7.1](/blog/release/console-2.7.1/)** together (**[mcli 20261112](/blog/release/mcli-20261112/)** [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf) also aligns explicit empty-policy resets on `accesskey edit`)

Following the audit of service-account policy updates in [`SN-2026-021`](/blog/security/20261110-svcacct-inline-policy-preservation/), we reviewed the full lifecycle of service accounts and IAM groups across backup/restore (`ExportIAM` / `ImportIAM`), the Web Console, and expiring credentials. That review uncovered two inherited privilege-state defects:

1. **Cluster IAM import (`mcli admin cluster iam import`) silently reactivated disabled credentials and groups:** `importIAM` (`cmd/admin-handlers-users.go`) omitted the exported `Status` field when recreating service accounts and ignored disabled group status when importing `groups.json`, turning every disabled/revoked service account and disabled group back `"on"` during disaster recovery or cluster migration.
2. **Console metadata edits froze inherited parent policies and blocked disabling keys under large parent policies:** Because `InfoServiceAccount` returns the parent user's effective policy text alongside `ImpliedPolicy: true`, Console's `EditServiceAccount` modal populated its inline policy editor with the parent's policy and submitted it back on any metadata save—converting an `inherited-policy` key into a static `embedded-policy` copy, and failing outright (`400 errSessionPolicyTooLarge`, with the error hidden behind the modal) when an operator tried to disable an inherited service account whose parent policy exceeded 4 KiB.

## Summary {#summary}

- **What went wrong:**
  1. **`ImportIAM` dropped `Status` on service accounts and groups (`#345`):** In `cmd/admin-handlers-users.go`, `importIAM` built `newServiceAccountOpts` without `status: svcAcctReq.Status` (causing `NewServiceAccount` to default every imported key to `AccountOn = "on"`), never called `SetGroupStatus(ctx, grp, false)` when `grpInfo.Status == statusDisabled`, and recorded `Error: err` (`nil`) instead of `gerr` in `failed.Groups` when `AddUsersToGroup` failed.
  2. **Console `EditServiceAccount` conflated `ImpliedPolicy` display text with an inline restriction (`#339`):** Whenever an operator renamed, described, set expiry on, or toggled status for an `inherited-policy` access key in Console, the UI sent the parent user's combined policy JSON as `newPolicy`, permanently embedding a point-in-time copy of the parent's policy. When the parent's combined policy exceeded `maxSVCSessionPolicySize` (4096 bytes after whitespace compaction), operators could not even disable or edit the inherited key in Console—and the modal swallowed the API error notification.
  3. **Expiring service accounts omitting `"Version"` failed authorization at runtime:** `NewServiceAccount` accepted inline policies without `"Version"`, which worked for non-expiring keys (`isAllowedLocally`) because `Policy.IsAllowed` ignores `Version`, whereas `isAllowedBySessionPolicy` (`cmd/iam.go`, used whenever `cred.IsTemp()` is true—including any service account with an `Expiration` timestamp) required `subPolicy.Version != ""` and denied every S3/Admin request with `403`.
- **Upstream provenance:**
  - `ImportIAM` status omission and `nil` group error reporting: upstream MinIO [`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f) (`2022-06-23`, [minio/minio#15014](https://github.com/minio/minio/pull/15014)).
  - Expiring service-account `"Version"` mismatch: upstream MinIO [`eae9c2f65`](https://github.com/pgsty/silo/commit/eae9c2f65bade4d9de2aac42f188114bf6dbe555) (`2021-07-15`, [minio/minio#12716](https://github.com/minio/minio/pull/12716)) combined with [`4d708cebe`](https://github.com/pgsty/silo/commit/4d708cebe9f9d15169b28d54e7adbd4150933622) (`2023-02-27`, [minio/minio#16430](https://github.com/minio/minio/pull/16430)).
  - Console inherited-policy submission: upstream MinIO Console [`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d) (`2024-02-29`, `#3221`).
- **Fix:** Server commit [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed) passes `status: svcAcctReq.Status` during `importIAM`, applies disabled group status after group creation, records the real `gerr` on group import failure, and normalizes non-empty versionless inline policies to `policy.DefaultVersion` (`"2012-10-17"`). Console commits [`1be8a74bf`](https://github.com/pgsty/silo-console/commit/1be8a74bfb86ba3f417204551099fd8a3788f0e2), [`a1a84cab4`](https://github.com/pgsty/silo-console/commit/a1a84cab4d96814af6572f7dce40ad537aa2f81e), and [`1fdb279fd`](https://github.com/pgsty/silo-console/commit/1fdb279fd98845b66d7218b2159b434fe76351eb) track `ImpliedPolicy` separately from inline restrictions and surface save errors directly inside the modal.

---

## 1. Upstream Provenance and Root Cause {#provenance}

### `ImportIAM` Reactivating Disabled Service Accounts and Groups {#import-iam}

`ExportIAM` (`GET /minio/admin/v3/export-iam`) serializes every service account (including `"accountStatus": "off"`) into `svcaccts.json` and every group (including `"status": "disabled"`) into `groups.json`. When upstream introduced `importIAM` in [`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f) (`2022-06-23`), the user import loop checked `u.Status == AccountOff` and persisted disabled users accurately—but both the service-account loop and the group loop dropped status:

1. **Service accounts:** `importIAM` decoded `svcAcctReq.Status`, yet omitted `status:` when constructing `newServiceAccountOpts`. Inside `NewServiceAccount` (`cmd/iam.go`), an empty `opts.status` defaults to `auth.AccountOn` (`"on"`). Every service account that an administrator had disabled (`mcli admin user svcacct disable`)—for example, to quarantine a leaked key while preserving audit history—became active again immediately upon `mcli admin cluster iam import`.
2. **Groups:** `AddUsersToGroup` always creates or updates groups in `"enabled"` status unless `SetGroupStatus(ctx, grp, false)` is called. Because `importIAM` never checked `grpInfo.Status == statusDisabled`, every disabled group resumed granting all of its attached `Allow` policies to member users after an IAM import. Furthermore, when `AddUsersToGroup` returned an error `gerr`, the handler appended `madmin.IAMErrEntity{Name: grp, Error: err}`—where outer `err` was `nil` from `json.Unmarshal`—reporting a failed group import with an empty error reason.

### Console `EditServiceAccount` Freezing Parent Policy and Blocking Disable {#console-freeze}

On the server, `InfoServiceAccount` (`cmd/admin-handlers-users.go`) sets `ImpliedPolicy: true` when an access key inherits its parent's permissions, and populates `Policy` with the JSON rendering of the parent user's (and groups') combined policies for read-only display.

In upstream Console ([`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d), `2024-02-29`), `EditServiceAccount.tsx` initialized its **Restrict beyond user policy** toggle to `false` when `impliedPolicy` was `true`, yet pre-filled the backing `policy` state string with `account.policy` and unconditionally sent `policy` whenever `policy !== ""` on save:

- **Silent conversion from inherited to frozen inline policy:** Editing only an access key's name, description, expiration, or enabled/disabled toggle in Console sent the parent's current policy text as `newPolicy`, turning `sa-policy-type` from `inherited-policy` into `embedded-policy`. Later policy grants added to the parent user or parent groups silently failed to apply to that key.
- **Inability to disable inherited keys under `> 4 KiB` parent policies:** Service-account inline session policies are capped at `maxSVCSessionPolicySize = 4096` compacted bytes (because they live inside the JWT `SessionToken`), whereas parent user/group combined policies have no 4 KiB ceiling. Whenever a parent user had more than 4 KiB of combined policy statements, clicking **Save** in Console to **disable** an inherited service account sent the oversized parent policy as `newPolicy`, failed on the server with `400 session policy size exceeds 4KiB limit`, and—because the modal lacked an inline error alert—left the key enabled without telling the operator why Save failed.

---

## 2. Impact Scope {#impact}

| Workflow / Component                            | Security & Operational Impact                                                                                                                                         |
| :---------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`mcli admin cluster iam import`**             | Silently re-enables every disabled service account (`accountStatus: "off"` -> `"on"`) and every disabled IAM group (`status: "disabled"` -> `"enabled"`).             |
| **Console `EditServiceAccount` (`<= 4 KiB`)**   | Any metadata or status edit on an inherited access key converts it to a static embedded policy snapshot, causing silent permission drift when parent policies change. |
| **Console `EditServiceAccount` (`> 4 KiB`)**    | Operators cannot disable, rename, or set expiry on an inherited access key via Console (`400` error swallowed by the modal).                                          |
| **Expiring service accounts without `Version`** | Inline policies omitting `"Version"` succeed on creation (`200`), work on non-expiring keys, and fail every request (`403`) whenever `Expiration` is set.             |
{.wide .expand}

---

## 3. Solution Design: Why It Is Necessary and Sufficient {#fix}

### Server Repairs (`1d714834c`) {#server-fix}

1. **Exact state restoration in `importIAM` (`cmd/admin-handlers-users.go`):**
   - Passes `status: svcAcctReq.Status` in `newServiceAccountOpts` (defaulting to `AccountOn` only when an older or handcrafted JSON omits `accountStatus`), preserving `"off"` credentials in both `.minio.sys/iam/` and `etcd`.
   - Calls `globalIAMSys.SetGroupStatus(ctx, grp, false)` whenever `strings.EqualFold(grpInfo.Status, statusDisabled)` after `AddUsersToGroup` succeeds, and records `Error: gerr` (or the status error) in `failed.Groups`.
2. **Version normalization at credential write boundaries (`normalizeServiceAccountPolicy` in `cmd/iam.go`):**
   - Clones any non-empty `sessionPolicy` whose `Version` is `""` and sets `Version = policy.DefaultVersion` (`"2012-10-17"`) before storing or updating the credential, while leaving empty policy documents (`Version == ""` and `len(Statements) == 0`) untouched as the explicit reset-to-inheritance signal established in [`SN-2026-021`](/blog/security/20261110-svcacct-inline-policy-preservation/).

### Console Repairs (`1be8a74bf`, `a1a84cab4`, `1fdb279fd`) {#console-fix}

1. **Separate `impliedPolicy` state from inline editor text (`EditServiceAccount.tsx`, `api/users.go`):**
   - When **Restrict beyond user policy** remains off on an `inherited-policy` key, Console omits `policy` from the `PUT` payload, preserving inheritance across name, description, expiry, and status edits regardless of parent policy size (even `> 4 KiB`).
   - When an operator turns **Restrict beyond user policy** off on an existing `embedded-policy` key (or enters `{}` / `{"Statement":[]}`), Console sends `{}` to explicitly reset the key back to `inherited-policy`.
   - If **Restrict beyond user policy** is toggled on while the editor is blank, Console blocks submission with clear inline validation instead of sending an ambiguous empty string; backend errors (such as invalid JSON/ARN or `> 4 KiB` inline policy) render inside the modal via `ModalErrorAlert`.

### Sufficiency and Necessity {#sufficiency}

- **Necessary:** Fixing only `SN-2026-021` on the server could not prevent Console from sending a 3 KiB parent policy string as `newPolicy` (because to the server, a valid non-empty JSON policy in `newPolicy` is indistinguishable from an intentional inline restriction), nor could it prevent `importIAM` from dropping `svcAcctReq.Status` and `grpInfo.Status`.
- **Sufficient:** Together with [`SN-2026-021`](/blog/security/20261110-svcacct-inline-policy-preservation/) and `mcli` [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf), the tri-state policy contract (`omitted/null` = preserve, `{}` / `{"Statement":[]}` = reset to inherited, non-empty = embed with normalized `Version`) and status fidelity hold uniformly across Server Admin APIs, site replication, IAM export/import, Console, and `mcli` (`cmd/iam-import-state_test.go`, `cmd/iam-svcacct-policy-edit_test.go`).

---

## 4. Trade-Offs, Caveats, and Operational Costs {#tradeoffs}

| Dimension                                           | Engineering Trade-Off & Upgrade Boundary                                                                                                                                                                                                                                                                                                                                                |
| :-------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Coordinated Server + Console upgrade required**   | Upgrading standalone Console without upgrading SILO Server would cause Console's omitted-policy save on an `embedded-policy` key (or `{}` reset) to hit pre-`SN-2026-021` Server behavior; conversely, upgrading Server without updating embedded/standalone Console leaves Console v2.7.0 freezing inherited policies on edit. Deploy the matched Server and Console release together. |
| **Historical `iam import` reactivation is durable** | Like `SN-2026-021`, upgrading the binary prevents future reactivation during `iam import`, but cannot distinguish credentials that were intentionally enabled from credentials accidentally re-enabled by an earlier `mcli admin cluster iam import`.                                                                                                                                   |
{.wide .expand}

---

## Remediation and Audit Guidance {#remediation}

1. **Upgrade SILO Server, [SILO Console 2.7.1](/blog/release/console-2.7.1/), and [mcli 20261112](/blog/release/mcli-20261112/) together** when the post-`20261109` Server release is published (Server `main`: [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed), [`34ba7cc1f`](https://github.com/pgsty/silo/commit/34ba7cc1ff3ef8f55888933921ab1e69e2182bf8); standalone Console `v2.7.1`: [`3825ebc44`](https://github.com/pgsty/silo-console/commit/3825ebc44451fdc8eefda3d4ec523a79dfecb236); `mcli 20261112`: [`a37a9f05`](https://github.com/pgsty/mc/commit/a37a9f054fba828a0bbbceb4e9ff247ccf09c28d)).
2. **Audit clusters populated or restored via `mcli admin cluster iam import`:** If you previously ran `iam import` from an export bundle containing disabled service accounts or disabled groups, inspect `svcaccts.json` and `groups.json` in that archive and re-disable any unintended active entries:
   ```shell
   mcli admin user svcacct disable myminio/ <access-key>
   mcli admin group disable myminio <group-name>
   ```
3. **Audit Console-edited access keys for unintended `embedded` policies:** If an access key was meant to track its parent user's policies dynamically (`Policy: implied`) but was previously edited in Console, check `mcli admin user svcacct info myminio/ <access-key>` and reset it to inheritance if needed by toggling off **Restrict beyond user policy** in the updated Console (or passing `{}` to `mcli admin user svcacct edit --policy`).

See the [Security Advisory Ledger](/about/security-advisories/#sn-2026-025), [`SN-2026-021`](/blog/security/20261110-svcacct-inline-policy-preservation/), and [Console Compatibility Notes](/compatibility/console/#candidate-policy-edit).
