---
title: "Bucket Quota in the Console: List Display and Numeric Validation"
linkTitle: "Console Quota Validation"
date: 2026-11-04
lastmod: 2026-11-10
author: "PGSTY SILO Maintainers"
summary: >
  Why a quota set in the web Console showed as a dash in the bucket list, why the bucket-creation form turned 1000 Ei into a one-byte quota and rejected 0.5 Gi, which releases carried each defect, and why one shared conversion and one shared quota reader are the minimum complete repair.
tags: [Design, Console, Quota, Retention]
weight: 10
draft: false
url: "/blog/design/console-quota-numeric-validation/"
---

This record covers [silo-console#72](https://github.com/pgsty/silo-console/issues/72) (a quota set in the web Console shows as a dash in the bucket list) and [silo-console#73](https://github.com/pgsty/silo-console/issues/73) (numeric validation in the bucket-creation form). It is evaluated against the Console source before the fix, [3d264aea9](https://github.com/pgsty/silo-console/commit/3d264aea9b67aa40baf706f3e13c8d4145671ea1), and the fix commits [a85665814](https://github.com/pgsty/silo-console/commit/a85665814ff74d8a9d0cbd42a51f518c79c9a227) through [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd).

**Status:** [PR #74](https://github.com/pgsty/silo-console/pull/74) ([`3d1dd56eb`](https://github.com/pgsty/silo-console/commit/3d1dd56ebaacf219191ed92d351a27bddd653838), 2026-11-04) shipped in standalone [Console 2.6.0](/blog/release/console-2.6.0/) ([`f8ab14669`](https://github.com/pgsty/silo-console/commit/f8ab146695fd1df74e4b84128a286d552921bf00)). PR `#74` and all numeric follow-ups ([#75](https://github.com/pgsty/silo-console/issues/75) [`2b18ff854`](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49), [#76](https://github.com/pgsty/silo-console/issues/76) [`4da296098`](https://github.com/pgsty/silo-console/commit/4da296098), and [PR #79](https://github.com/pgsty/silo-console/pull/79)) shipped in standalone [Console 2.7.0](/blog/release/console-2.7.0/) ([`4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505)) and embedded in [SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`).

## Short answer {#tldr}

Both reports are real, and neither affects stored data or quota enforcement.

- **#72 is a display defect.** Since the Console started writing the modern `Size` field (2025-09-16), a quota set from the web Console is stored with `size` set and the legacy `quota` zero. The bucket list handler and the list UI read only `quota`, so they show nothing. The server enforces the quota correctly.
- **#73 is an input-validation defect with one write-affecting case.** `parseInt(getBytes(...))` turns any amount from 868 Ei upward into a quota of 1 byte, and the server accepts and enforces it, so every non-empty write to that bucket is refused. The other cases are rejections or missing checks: `0.5 Gi` is rejected, changing the unit does not revalidate, and the retention validity is neither checked for being an integer nor bounded to 32 bits.

Neither defect was introduced by SILO. #72 comes from the community Console line that SILO forked: its quota writer changed in 2025-09-16 and its list reader did not. #73 is original minio/console code from 2020 to 2022. SILO shipped both in every Console-bearing release listed below, and its list redesign in Console v2.5.0 kept the stale reader.

The repair is small. The bucket list uses the same quota reader as the Summary, and the creation and edit forms share one conversion and bounds check.

## Classification {#assessment}

| Aspect              | Assessment                                                                                                                                                                                                                                                                     |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Nature              | #72: a representation change in the Console writer left a reader behind. #73: input validation that predates the fork. Both inherited, not SILO regressions.                                                                                                                   |
| Affected components | The web Console only: `api/user_buckets.go`, the bucket list UI, and the bucket-creation and quota-edit forms. The server, `madmin-go`, and `mcli` are not defective.                                                                                                          |
| #72 impact          | Display only. The quota is stored, enforced, and shown correctly in Summary and by `mcli`. The list shows a dash (Console v2.5.x) or omits the quota (v2.0.0 to v2.4.2).                                                                                                       |
| #73 impact          | One write-affecting case: amounts of 868 Ei and more become a 1-byte hard quota that blocks writes of any non-empty object. Amounts from 8 Ei to 867 Ei exceed the signed 64-bit range and are refused by the API. The remaining cases are false rejections or missing checks. |
| Severity            | Low for #72. Low to moderate for #73: reaching the damaging case needs a deliberate amount of at least 868 Ei, but the result is a bucket that silently refuses writes. No data loss, no security impact.                                                                      |
| Affected releases   | See [Where the behavior came from](#history). #72: Console from the community v1.9.0 through SILO Console v2.5.1; SILO Server 20260314 through 20261026. #73: Console releases through v2.5.1 and SILO Server through 20261026.                                                |
| Release urgency     | Shipped in standalone Console 2.6.0 and Console 2.7.0, and embedded in SILO Server 20261109. Not a data-safety blocker.                                                                                                                                                        |
| Remaining effort    | Complete; standalone Console 2.6.0/2.7.0 and embedded SILO Server 20261109 are published.                                                                                                                                                                                      |
{.wide .expand}

## When it happens {#trigger}

**#72.** Create a bucket and set its quota with `mcli quota set`, which writes the legacy `quota` field. The list shows it. Open the bucket in the Console, change the quota, and save. The Console writes `size` and the server stores a configuration with `quota` equal to zero. The admin API now returns `size=118111600640, quota=0` for a 110 GiB quota. The Summary page prefers `size`, so it shows 110 GiB; the list reads `quota`, so it shows a dash. The same happens for a quota set in the creation form.

**#73.** Open the bucket-creation form with quota enabled.

1. Enter `1000` and choose `Ei`. The form converts it to the string `1.152921504606847e+21`. `parseInt` stops at the `e` and returns `1`. The request carries `amount: 1`.
2. Enter `0.5` and choose `Gi`. `parseInt("0.5")` is `0`, so the form marks the field invalid, although the input pattern allows two decimals.
3. Enter `1000` with `Gi`, then change the unit to `Ei`. The field is not revalidated on a unit change, so the earlier valid state stays and case 1 is reachable without typing again.
4. Enable retention and enter `1.5` or `3000000000`. The input is read with `valueAsNumber`, and the only check is `NaN` or below 1. The API model is a signed 32-bit integer.

The existing-bucket quota editor has the same `parseInt(getBytes(...))` conversion; the retention editor has the same missing integer and upper-bound checks.

## Root cause {#root-cause}

**#72.** In the pre-fix source, the bucket list response is built in `getAccountBuckets` (`api/user_buckets.go`, lines 409 to 414), which copies `bucket.Details.Quota.Quota` and ignores `Size`. The list UI then renders `details.quota.quota` only: `BucketsTable.tsx` lines 387 to 390 in v2.5.x, and `BucketListItem.tsx` line 144 in earlier versions. The single-bucket quota handler `getBucketQuota` (`api/user_bucket_quota.go`, lines 118 to 125) already prefers a positive `Size` and falls back to `Quota`. Two readers of the same configuration used two rules.

The server did not change the representation. It stores and returns the configuration as the client wrote it, and it enforces `Size` first and `Quota` second (`getBucketQuotaSize` in `cmd/bucket-quota.go`; the same precedence exists in the last upstream MinIO master). The `madmin-go` structure already marks `Quota` as deprecated since August 2023 and carries `Size`. `mcli quota set` still writes the legacy `Quota` field, which is why a quota set from the command line displays correctly in the list.

**#73.** The creation form has four independent gaps:

- `addBucketThunks.ts` line 80 sends `parseInt(getBytes(quotaSize, quotaUnit, true))`. `getBytes` returns a number as a string, and JavaScript prints numbers of 1e21 and above in exponent form.
- `addBucketsSlice.ts` line 122 rejects the field when `parseInt(state.quotaSize) === 0`. The pattern on the next line was widened to two decimals later, and the `parseInt` test stayed.
- `setQuotaUnit` (line 133) only stores the unit and leaves `invalidFields` untouched.
- `setRetentionValidity` (lines 170 to 183) and `SetRetentionConfig.tsx` (line 87) test `NaN` and `< 1` only.

At the server, the quota request accepts any non-negative amount and stores it as `Size`. With a stored size of 1, `enforceQuotaHard` refuses every write of one byte or more (`uint64(size) >= quotaSize`, `cmd/bucket-quota.go`).

## Where the behavior came from {#history}

Provenance was established from the Console history. The upstream project `minio/console` is no longer publicly reachable. The community continuation [georgmangold/console](https://github.com/georgmangold/console), which the SILO Console forked, still is. `pgsty/silo-console` `main` descends from its commit [feff71e48](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563) (2026-04-16), the fork point. Commits below are on `main` of `pgsty/silo-console`; PR numbers refer to the repository the commit came from. Of the pre-fork Console release tags only the community tags v1.7.7 and later are retrievable, so the first minio/console release tag is not given for older commits.

### #72: a reader the writer change left behind {#reader-left-behind}

| Ingredient                                                                                     | Commit                                                                                                                                                                                                                                                      | Origin                                  | Date       | First release                                       |
| ---------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------- | ---------- | --------------------------------------------------- |
| List handler copies only `Quota`                                                               | [64e38ca8d](https://github.com/pgsty/silo-console/commit/64e38ca8d3) "List buckets re-design" (minio/console #1058), `api/user_buckets.go`                                                                                                                  | Upstream                                | 2021-09-20 | Tag not retrievable; present in every later release |
| List UI reads only `details.quota.quota`                                                       | [10539929e](https://github.com/pgsty/silo-console/commit/10539929e1) "Added quota metric to buckets list & objects list" (minio/console #1595), `BucketListItem.tsx`                                                                                        | Upstream                                | 2022-02-16 | Tag not retrievable; present in every later release |
| **Console writer switches to `Size`; Summary reader updated, list reader not**                 | [6c54a55d5](https://github.com/pgsty/silo-console/commit/6c54a55d5285986eeeb4df00544f1aaa8c8db05d) "use Quota Size field instead of the deprecated Quota field" ([georgmangold/console#28](https://github.com/georgmangold/console/pull/28), Georg Mangold) | Community Console line, before the fork | 2025-09-16 | georgmangold/console v1.9.0 (2025-11-16)            |
| List redesigned as a table; the quota column keeps the stale reader and prints a dash for zero | [2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77) "modernize buckets, object browser, safe previews, and task center" (Feng Ruohang)                                                                       | SILO                                    | 2026-10-25 | Console v2.5.0 (2026-10-25)                         |
{.wide .expand}

The defect needs the last-but-one row: before 2025-09-16 the Console wrote the legacy field, which the list could read. The change in [6c54a55d5](https://github.com/pgsty/silo-console/commit/6c54a55d5285986eeeb4df00544f1aaa8c8db05d) is the representation change, and it updated one of the two readers. It is not a server or `madmin-go` change: `madmin-go` has carried both fields since August 2023, and the server's storage and enforcement of them is unchanged by it. SILO did not introduce the defect.

**What SILO changed.** No SILO commit between the fork and the fix touched the list handler or the quota writer. The SILO web redesign ([23ae6e8e6](https://github.com/pgsty/silo-console/commit/23ae6e8e6), Console v2.0.0) and the list rebuild in [2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77) re-implemented the list UI and carried the old reader over. In v2.0.0 to v2.4.2 the list simply omitted the quota. In v2.5.0 and v2.5.1 the new table column prints a dash, which reads as "no quota" and made the defect visible enough to be reported. That change widened the visible symptom, not the cause.

**Console releases containing the defect.** The writer change and the stale readers are both present in georgmangold/console v1.9.0 and v1.9.1, and in every SILO Console tag, v2.0.0 to v2.5.1. The first SILO Console tag is v2.0.0 (2026-08-04). Console releases that wrote the legacy field, up to minio/console v1.7.6 and the community v1.8.1, do not show the defect.

**Embedded Console across SILO Server releases** (from the `replace github.com/minio/console` line of the Server `go.mod`):

| Server release                                   | Embedded Console                              | Defect present             |
| ------------------------------------------------ | --------------------------------------------- | -------------------------- |
| 20251203, 20260214                               | minio/console v1.7.x, writes the legacy field | No                         |
| 20260314, 20260321, 20260325, 20260417, 20260618 | georgmangold/console v1.9.1                   | Yes (list omits the quota) |
| 20260804, 20260806                               | SILO Console v2.0.0, v2.1.x                   | Yes (omits)                |
| 20260903                                         | A build between Console v2.3.0 and v2.4.0     | Yes (omits)                |
| 20260916, 20261015                               | Console v2.4.1                                | Yes (omits)                |
| 20261018                                         | Console v2.4.2                                | Yes (omits)                |
| 20261025, 20261026                               | Console v2.5.0, v2.5.1                        | Yes (dash)                 |
| 20261109                                         | Console v2.7.0                                | No                         |
{.wide .expand}

[SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`) embeds [Console 2.7.0](/blog/release/console-2.7.0/) ([`4e91ae506e70`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505)) and resolves both defects in the embedded UI (superseding the intermediate `main` bump to `v2.6.0` in [`e24831f53`](https://github.com/pgsty/silo/commit/e24831f53)). The Server tags 20260304, 20260323, and 20260330 embed a Console build from before the writer change and are not affected.

### #73: original minio/console code {#original-code}

| Ingredient                                                                                 | Commit                                                                                                                                      | Origin   | Date       | Notes                                                                                                           |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------- |
| `parseInt(getBytes(...))` in the creation request                                          | [28eb8784a](https://github.com/pgsty/silo-console/commit/28eb8784a) "Set Bucket Quota on Creation" (minio/console #308)                     | Upstream | 2020-10-01 | `getBytes` returns `Number.toString(10)`; the exponent form exists from 1e21 up                                 |
| Field check `parseInt(quotaSize) === 0`, no unit revalidation, retention `NaN`/`< 1` check | [41e1b4a5d](https://github.com/pgsty/silo-console/commit/41e1b4a5d) "Add Bucket slice refactor to reduce re-renders" (minio/console #2087)  | Upstream | 2022-06-03 | Moved the form logic into `addBucketsSlice.ts`; the checks already existed in `AddBucket.tsx`                   |
| Decimal quotas added to the pattern, `parseInt` test kept                                  | [7ecc1022b](https://github.com/pgsty/silo-console/commit/7ecc1022b) "Added decimal support to bucket quota selectors" (minio/console #2126) | Upstream | 2022-06-15 | This made `0.5` pass the pattern and fail the `parseInt` test; the upstream "Release v0.19.0" commit follows it |
{.wide .expand}

All of this is in the community line and in `feff71e48`. SILO commits that touched the same files before the fix ([23ae6e8e6](https://github.com/pgsty/silo-console/commit/23ae6e8e6), [14b1c2de2](https://github.com/pgsty/silo-console/commit/14b1c2de2), [2611a4d11](https://github.com/pgsty/silo-console/commit/2611a4d11a9e22282847bfa5b8b239a84b4b5d77)) changed link targets, translations, and a command preview; none changed the validation or the conversion. SILO neither introduced nor widened #73. It is present in every Console release and so in every SILO Server release that embeds one.

Reasoned, not executed: the `main`-line history. The first minio/console release tags for the 2020 to 2022 commits could not be retrieved, so only the commit subjects and dates are given.

## Options {#options}

### Option 1: one shared quota reader for list and detail {#option-1}

Move the `Size`-then-`Quota` rule into one helper and use it in the list handler and in `getBucketQuota`. Both readers always agree, and the API schema does not change.

### Option 2: change the writer to send both fields {#option-2}

Writing `Quota` as well as `Size` would make the old reader work again, but it reintroduces a deprecated field for one consumer, and quotas written by other tools would still break the list. Rejected.

### Option 3: change the UI to also read `size` {#option-3}

The list response model has only `quota`. Reading a second field in the browser duplicates the rule in a third place. Rejected.

### Option 4: validate the amount in one function and use it everywhere {#option-4}

One function converts a text amount and a unit to a byte count and rejects anything outside `1` to `2^63 - 1`. The creation form, the quota editor, and the thunk all call it, and a unit change revalidates. Retention gets an integer and `1..2147483647` check.

### Option 5: leave the server to reject {#option-5}

The server accepts any non-negative `Size`, including 1. The bad value is a valid configuration, so the server cannot tell it from intent. Rejected as the only defense, kept as a backstop for negative amounts.

## Proposed fix {#fix}

Option 1 and Option 4, in six commits of the branch (all in PR #74):

1. [a85665814](https://github.com/pgsty/silo-console/commit/a85665814ff74d8a9d0cbd42a51f518c79c9a227) extracts `bucketQuotaSize` and uses it in both the list handler and `getBucketQuota`: a positive `Size` wins, otherwise `Quota`. Handler JSON tests cover modern, legacy, conflicting, empty, zero, and nil values. Quota writes and the schema are unchanged.
2. [35cf4aae7](https://github.com/pgsty/silo-console/commit/35cf4aae7f7cea46e99c95400894b0dc21c664f0) makes the quota editor keep the exact byte value, skip a save when nothing changed, validate before converting, and reject a negative amount at the API.
3. [fb2c9e71c](https://github.com/pgsty/silo-console/commit/fb2c9e71c) parses complete byte values and bounds the display units, so large numbers no longer print in exponent form for display.
4. [d878dbf88](https://github.com/pgsty/silo-console/commit/d878dbf88) adds `addBucketValidation.ts` with `getQuotaBytes` and `isValidQuota`. The amount must match the two-decimal pattern, convert to a finite whole number above zero and below `2^63`, and be revalidated when the unit changes. The creation thunk repeats the check before sending.
5. [9fb0b0627](https://github.com/pgsty/silo-console/commit/9fb0b0627) and [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd) require retention validity to be an integer between 1 and 2147483647 in the creation form, its thunk, and the retention editor. The first also makes the API refuse a retention validity of zero or less.
{.steps}

The branch also carries two unrelated display commits (API request widgets and syscall rate labels). They are not part of these issues.

**Follow-ups after PR #74 (shipped in Console 2.6.0, Console 2.7.0, and SILO Server 20261109).** They refine the same code outside the PR #74 branch:

- [2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49) (#75) scales decimal quotas with integer arithmetic and rejects browser writes of 8 PiB and more, so a value is never sent in an inexact form.
- [4da296098](https://github.com/pgsty/silo-console/commit/4da296098) (#76) moves the other `calculateBytes` and display paths to one bounded parser.
- [9107a8281](https://github.com/pgsty/silo-console/commit/9107a8281) (#77, #78, merged in [PR #79](https://github.com/pgsty/silo-console/pull/79)) validates quota and retention before the bucket is created. Before it, `makeBucket` tolerated a failed quota call and returned success, so a bucket could be created without the requested quota.

## Why it is sufficient and necessary {#sufficiency}

**Sufficient for #72.** The list handler and the single-bucket handler now call the same function, so they agree for every combination of the two fields, including a legacy quota written by `mcli` and a modern one written by the Console. The UI reads the `quota` value the handler returns and needs no change.

**Sufficient for #73.** Every path that turns text into a quota amount now goes through the same bounded conversion: `0.5 Gi` becomes 536870912, an amount of 868 Ei or more is refused before it can become 1, and a unit change revalidates. The retention check closes the fractional and over-range cases in both forms. The thunk check protects against a stale form state.

**Necessary.** Without the shared reader, any further consumer of the list response repeats the mistake. Without validation before conversion, `parseInt` of a number string stays unsafe for any large value.

**Deliberately excluded.** These stay out of this record's fix:

- arbitrary 64-bit precision: on the PR #74 branch a decimal amount is converted through a JavaScript number, so a value such as `7 Ei` is sent as 8070450532247929000 instead of 8070450532247928832. Tracked in [silo-console#75](https://github.com/pgsty/silo-console/issues/75) and resolved in Console 2.6.0/2.7.0 ([2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)) by refusing browser writes of 8 PiB and above;
- the other uses of `calculateBytes`, tracked in [silo-console#76](https://github.com/pgsty/silo-console/issues/76) and resolved in Console 2.6.0/2.7.0 ([4da296098](https://github.com/pgsty/silo-console/commit/4da296098));
- the three replication bandwidth forms, which have the same conversion pattern and are repaired in PR #74 by a separate commit ([facbf3bab](https://github.com/pgsty/silo-console/commit/facbf3bab));
- the server: no change to quota storage, enforcement, or the admin API.

## Cost and compatibility {#cost}

- No API schema, server, or `madmin-go` change. The list response keeps the field name `quota`; only the value it carries is now the effective quota.
- Existing quotas, legacy or modern, are unchanged on the server. A legacy quota is shown as before; a modern quota that used to be hidden is now shown.
- Inputs that were accepted before and are now rejected are the 868 Ei and larger amounts (which meant 1 byte) and non-integer or over-range retention. Inputs that were rejected and are now accepted are decimals below one, such as `0.5 Gi`.
- Buckets already created with a 1-byte quota stay as they are. See [Residual limits](#limits).
- Rollback to the previous Console restores the old behavior with no migration.

## Residual limits {#limits}

- **A bucket already given a 1-byte quota stays blocked.** Find it with `mcli quota info ALIAS/BUCKET` (a size of 1 byte is the sign) and set the intended quota or clear it with `mcli quota clear ALIAS/BUCKET`.
- **Older Server releases retain the embedded defects.** Standalone [Console 2.6.0](/blog/release/console-2.6.0/) and [Console 2.7.0](/blog/release/console-2.7.0/) (`4e91ae506e70`), as well as [SILO Server 20261109](/blog/release/silo-20261109/) (`d998292387cc`), include the repairs. Embedded Console UI in SILO Server releases from `20260314` through `20261026` retains both defects.
- **Large quotas stay with `mcli`.** In Console `2.6.0` and `2.7.0` (and embedded in `SILO Server 20261109`), the browser refuses quota writes of 8 PiB (`2^53` bytes) and more, because a JSON number is exact only up to that point ([#75](https://github.com/pgsty/silo-console/issues/75), closed by [2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)). The initial PR #74 branch allowed up to `2^63` through a JavaScript number.
- **Narrow screens.** The existing responsive layout hides the quota column of the bucket list below 1200 px; the Summary still shows the quota.

## Verification {#verification}

Executed on the fix branch tip [5a34232e7](https://github.com/pgsty/silo-console/commit/5a34232e72162274d621c57342c75c06fc35befd) in the Console repository:

- **Playwright unit project.** `e2e/bucket-quota.unit.ts`, `e2e/bucket-retention.unit.ts`, `e2e/add-bucket-numeric.unit.ts`, and `e2e/size-format.unit.ts`: 49 tests, all passed. They cover `1000 Ei` and `8 Ei` rejected, `0.5 Gi` written as 536870912 bytes, a unit change revalidating, an unchanged quota not written, and the retention bounds.
- **Go tests.** `go test -mod=readonly ./api -run 'Quota|Retention|AccountBuckets|ListBuckets'` passed (the list and detail responses for modern, legacy, conflicting, empty, zero, and nil quotas).
- **The conversion defect itself.** A small script of the pre-fix formula gives `1000 Ei` as `"1.152921504606847e+21"` and `parseInt` of it as `1`; `867 Ei` is `999582944494136300000` and `868 Ei` is the exponent form, so the 1-byte case starts at 868 Ei. `parseInt("0.5") === 0` is true.
- **Merged result (reported, not rerun here).** The issue discussion reports the merged change validated with a real SILO, `mcli`, and Console run (100 GiB set with `mcli`, changed to 110 GiB in the Console, list, detail, and `mcli` agreeing at 118111600640 bytes; a 0.5 GiB creation quota stored as exactly 536870912 bytes).

Reasoned from code, not executed here:

- the server enforcing a 1-byte `Size` (`cmd/bucket-quota.go`);
- the refusal of out-of-range amounts by the API for 8 Ei to 867 Ei and of fractional or over-range retention by the 32-bit model;
- which Server releases embedded affected Console builds before `SILO Server 20261109`, from the `go.mod` history;
- the pre-fork history, from commit subjects and dates.

## References {#references}

- Issues: [silo-console#72](https://github.com/pgsty/silo-console/issues/72), [silo-console#73](https://github.com/pgsty/silo-console/issues/73)
- Fix: [PR #74](https://github.com/pgsty/silo-console/pull/74), merge commit [3d1dd56eb](https://github.com/pgsty/silo-console/commit/3d1dd56ebaacf219191ed92d351a27bddd653838)
- Writer change: [georgmangold/console#28](https://github.com/georgmangold/console/pull/28)
- Follow-ups (shipped in Console 2.6.0, Console 2.7.0, and SILO Server 20261109): [silo-console#75](https://github.com/pgsty/silo-console/issues/75) (64-bit precision, [2b18ff854](https://github.com/pgsty/silo-console/commit/2b18ff854f81b08080094f0f3231f6b249c64d49)), [silo-console#76](https://github.com/pgsty/silo-console/issues/76) (`calculateBytes`, [4da296098](https://github.com/pgsty/silo-console/commit/4da296098)), [PR #79](https://github.com/pgsty/silo-console/pull/79) (creation-time validation)
- Release pages: [SILO 20261109](/blog/release/silo-20261109/), [Console 2.7.0](/blog/release/console-2.7.0/), [Console 2.6.0](/blog/release/console-2.6.0/), [Console 2.5.1](/blog/release/console-2.5.1/), [SILO 20261026](/blog/release/silo-20261026/)
