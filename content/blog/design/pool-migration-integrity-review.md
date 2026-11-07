---
title: "Pool Migration Integrity Review: #261, #263, and #265"
linkTitle: "Pool Migration Integrity Review"
date: 2026-10-27
lastmod: 2026-11-06
author: "PGSTY SILO Maintainers"
summary: >
  A maintainer review of three storage-pool migration reports: mixed erasure-code layouts, tier free versions, and lifecycle expiry ordering. It records root causes, minimum safe fixes, evidence, and merge order.
tags: [Design, Storage Pools, Lifecycle, Compatibility]
weight: 10
draft: false
url: "/blog/design/pool-migration-integrity-review/"
---

This record reviews [#261](https://github.com/pgsty/silo/issues/261), [#263](https://github.com/pgsty/silo/issues/263), and [#265](https://github.com/pgsty/silo/issues/265), together with their fixes [#262](https://github.com/pgsty/silo/pull/262), [#264](https://github.com/pgsty/silo/pull/264), and [#266](https://github.com/pgsty/silo/pull/266). It also records the maintainer follow-up [#276](https://github.com/pgsty/silo/pull/276). It is a design and review record, not a release note. The review was updated against the post-#276 main branch on 2026-11-02. #264, #266, and #276 are merged; #262 is closed as superseded.

## Decision at a glance {#decision}

| Report | Is the problem real? | PR assessment | Recommended action |
| --- | --- | --- | --- |
| [#261](https://github.com/pgsty/silo/issues/261) | Yes. A readable mixed-EC object can be omitted from migration and lost when its old pool is removed. | The narrow fix was merged through maintainer PR [#267](https://github.com/pgsty/silo/pull/267); [#262](https://github.com/pgsty/silo/pull/262) was superseded. | Merged in #267; issue closed as completed. |
| [#263](https://github.com/pgsty/silo/issues/263) | Yes. An internal tier cleanup entry is treated as a real version by lifecycle, listing, and migration paths. | [#264](https://github.com/pgsty/silo/pull/264) fixes the whole boundary while keeping healing visibility. | Merged; issue closed as completed. |
| [#265](https://github.com/pgsty/silo/issues/265) | Yes. ILM and migration disagree about whether a version still exists and who removes it. | [#266](https://github.com/pgsty/silo/pull/266) fixes the contributor-reported local ordering bug. Maintainer follow-up [#276](https://github.com/pgsty/silo/pull/276) preserves tier cleanup, lifecycle-generation, and whole-object completion contracts. The replication of lifecycle deletes that #276 also added is removed before the next release; see the [2026-11-06 update](/blog/design/ilm-migration-ordering/). | Merged #266 to recognize the contribution, then merged #276 as the required completeness patch. |
{.wide .expand}

The practical order was: merge the mixed-EC fix, merge #264, merge #266 to preserve the contributor's change, and immediately follow it with #276. The first three changes are now in main, and #276 supplies the maintainer-owned safety boundaries that the original PR could not safely implement in isolation.

## What was verified {#evidence}

The three reports reproduce against the pre-fix main with focused tests and the supplied native-server scenarios. The merged #264 and #267 code was checked before #266. The merged #266 plus #276 tree passed the focused migration and replication tests, `go vet ./cmd`, `make build`, the repository CI lint and generated-file checks, and the full `go test ./cmd -count=1` run. The companion site checks pass after this document update.

The important behavioral evidence is:

- On main, the #261 mixed-EC migration tests return no entry for cases where latest-only GET and ListObjectsV2 already find a readable object. The same tests pass with #262.
- On main, the #263 tests show a free entry as a latest delete marker, hide a readable key from ListObjectsV2, queue the wrong version for lifecycle expiry, and move a plain delete marker during decommission. The full #264 suite fails on main and passes on the PR.
- On main, the #265 tests either leave the current version in the source pool or leave duplicate moved copies. The #266 suite passes on the PR, including decommission and rebalance cases with a delayed expiry queue.

The test evidence proves the reported failures and the local migration fixes. It does not by itself prove that the direct source purge in #266 preserves bucket replication, remote-tier ownership, lifecycle-configuration changes, or a safe completion fence for whole-object expiry. Those are separate acceptance conditions.

## Why these reports arrived together {#common-pattern}

All three problems are variations of the same rule: a storage-pool worker must use the same logical object view as GET, and it must preserve the object until a safe destination or a deliberate deletion is known.

The failures were hidden because different workers read the same xl.meta through different projections:

1. A latest-only read selected a readable majority across mixed EC layouts, while an all-versions walk used a stricter path.
2. GET already ignored tier free versions, while list, lifecycle, and migration code still saw them.
3. ILM knew that some actions would delete data eventually, while decommission and rebalance treated the queued action as if the deletion had already completed.

The right repairs are local boundary repairs. They do not require a new metadata format or a broad rewrite of pool migration.

## Affected release scope and advisory {#advisory}

The three issue fixes should be treated as a storage-integrity advisory. The latest published tag, [RELEASE.2026-10-26](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-10-26T00-00-00Z), predates the fixes. The repaired behavior is now in main through [#264](https://github.com/pgsty/silo/pull/264), [#267](https://github.com/pgsty/silo/pull/267), [#266](https://github.com/pgsty/silo/pull/266), and [#276](https://github.com/pgsty/silo/pull/276); operators need a release containing all applicable fixes.

The code-level windows are different:

- The free-version listing and migration behavior entered through upstream [29a25a538](https://github.com/pgsty/silo/commit/29a25a538) on 2024-06-07. Releases containing that change can hold the latent problem. Actual user-visible damage still requires a tiered version to leave a free record pending while lifecycle, listing, or migration observes it.
- The mixed-EC discrepancy became especially visible after [e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067) on 2026-10-16: latest-only reads recovered a readable majority while all-version migration walks could still omit it. The released 20261018, 20261025, and 20261026 tags contain that behavior; #267 fixes it.

This is a compound-condition problem, not a statement that every installation or every object is damaged. A free version by itself is normal pending-cleanup state. Mixed EC metadata by itself is a recoverable result of an availability-optimized degraded write. The damaging outcomes require a second operation while that state exists:

| State and operation | Result | Recovery position |
| --- | --- | --- |
| A free version exists briefly and the scanner completes | No user-visible corruption; the record and remote object are cleaned. | Normal after upgrade; do not edit metadata by hand. |
| A tiered free version is seen by lifecycle or ordinary listing before cleanup | Wrong noncurrent decision, hidden key, or misleading delete marker. | Future scans are corrected by #264; already deleted real versions need backup or another authoritative copy. |
| A free version is moved by old decommission/rebalance | A plain delete marker can be created and the remote reference can be lost. | The marker cannot be identified automatically; compare source copies, replication targets, backups, and audit history. |
| Mixed EC metadata is scanned by old decommission/rebalance | The readable object can be omitted; removing the source pool can lose it. | If the source remains, run the fixed migration path and heal; if it was removed, recover from a copy or backup. |
{.wide .expand}

An immediate operational advisory is appropriate. It should tell operators using an affected build to pause pool decommission and rebalance, especially while drives are degraded, tier cleanup is pending, or lifecycle rules are active. It should preserve the old pool and backups, upgrade to a release containing the relevant fixes, and verify GET, ListObjectsV2, ListObjectVersions, and object counts after migration. It should state that the advisory is conditional and identify the separate rebalance limitation for transitioned versions. A CVE-style security label is unnecessary unless the project classifies storage-integrity failures that way; a high-priority storage-integrity release note and operator advisory are sufficient.

Before publishing an “all clear,” we still need a patch release and a historical audit runbook. Main now contains the complete decommission path for these three reports; a release containing only #264 and #267 would still be insufficient for lifecycle-aware migration.

## Merge and follow-up plan {#plan}

1. Keep the merged #264, #267, #266, and #276 changes together in the next patch release. They establish the logical object view, mixed-EC migration listing, lifecycle action semantics, and external cleanup contracts.
2. Preserve the distinction between a versioned current Expiration, a version-only purge, and a whole-object deletion. Do not replace it with a generic “skip every ILM action” rule.
3. Retain the new regression coverage for lifecycle deletes with replication configured, which must queue no replication, and for transitioned-version cleanup, lifecycle configuration changes, whole-object expiry, and resumable decommission.
4. Publish the storage-integrity advisory with the patch release and provide a historical-audit runbook for installations that migrated pools on affected builds.
5. Track rebalance support for transitioned versions separately; #276 deliberately does not broaden that scope.

The detailed records are:

- [Mixed EC Layouts and Migration Listing](/blog/design/mixed-ec-migration-listing/)
- [Tier Free Versions Are Internal Cleanup Records](/blog/design/tier-free-version-semantics/)
- [ILM Expiry and Pool Migration Ordering](/blog/design/ilm-migration-ordering/)

## Residual limits {#limits}

These repairs do not heal a disk that is still unavailable, recreate historical data already lost by an earlier completed decommission, or distinguish a plain delete marker created by an older buggy build from a client-created marker. #264 can make decommission fail when a tier is unavailable, because that is safer than dropping a cleanup record whose remote object may still exist. Rebalance still skips transitioned versions by design; that is a separate scope decision from the completed decommission fix. Lifecycle configuration changes are fail-closed during migration, so a stale walk must be retried under the new configuration.
