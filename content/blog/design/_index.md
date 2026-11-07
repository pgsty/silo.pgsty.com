---
title: Design Records
linkTitle: Design
description: Architecture notes, S3 compatibility contracts, replication invariants, and engineering decisions for PGSTY SILO.
weight: 40
icon: fa-solid fa-pen-ruler
sidebar_expanded: true
module: [BLOG]
blog_index: list
cascade:
  images: [/images/blog/silo-design.webp]
---

Design records document the engineering decisions behind PGSTY SILO: root causes, S3 and IAM protocol invariants, trade-offs against rejected alternatives, operational limits, and regression coverage.

## November 6: Found in Release Acceptance

- [A Partial View Must Not Report an Existing Object as Missing](/blog/design/partial-view-read-404/): Why a node that reaches only some drives can answer 404 for an object that exists, and why "not found" must require an answer from every drive.
- [A Failed Multipart Completion Can Strand the Upload](/blog/design/multipart-complete-retry/): Why a completion that misses write quorum can strand the upload until stale-upload cleanup, and why the repair waits for fencing of storage operations.

## November 4: Release-Blocking Lifecycle Fixes

- [Multi-Pool Lifecycle Expiry: Decide on the Whole Object](/blog/design/multi-pool-lifecycle-expiry/) ([#278](https://github.com/pgsty/silo/issues/278), [#279](https://github.com/pgsty/silo/pull/279)): Why an expiry decided on the versions of one pool hides, deletes, or resurrects versions in another pool, and why a recheck on the merged version list under the object lock is the minimum complete repair.
- [Restored Copies: Expire the Copy, Not the Object](/blog/design/restored-copy-expiry/) ([#281](https://github.com/pgsty/silo/issues/281), [#282](https://github.com/pgsty/silo/pull/282)): Why the expiry of a restored current version hid the object or stripped an older null version, and which storage and native-restore safeguards ship with the exact-version fix.
- [Native Restore in Two Phases](/blog/design/native-restore-two-phase/) ([#284](https://github.com/pgsty/silo/issues/284)): Why a native restore held the object lock for its whole tier download, why the first #281 safeguards also stranded failed ordinary uploads, and how staging outside the lock with a short, checked commit replaces the private upload.
- [Audit Webhooks After a Peer Reload](/blog/design/audit-webhook-peer-reload/) ([#259](https://github.com/pgsty/silo/issues/259)): Why a runtime audit_webhook change leaves every server but the serving one with a stopped target, which logger subsystems share it, and why building logger targets on the server context plus opening the queue store first is the minimum complete repair.
- [Failed Writes and Phantom Empty Prefixes](/blog/design/failed-rename-empty-prefix/) ([#285](https://github.com/pgsty/silo/issues/285), [#286](https://github.com/pgsty/silo/pull/286)): Why a write whose staged data vanished before the remote rename leaves an empty object directory that later lists as an empty prefix, and why removing it on both rename failure paths is sufficient.
- [Heal Dry Run Must Not Delete Data](/blog/design/heal-dry-run-safety/) (from [#280](https://github.com/pgsty/silo/pull/280)): Why a dry-run heal could delete the last metadata copies of a dangling object and run a real bucket heal on remote nodes, and why an early return plus forwarding the dry-run flag to peers closes both paths.
- [Lifecycle Delete-All Must Stay on One Key](/blog/design/ilm-delete-all-exact-key/) (found during review of [#278](https://github.com/pgsty/silo/issues/278)): Why ExpiredObjectAllVersions, DelMarkerExpiration, and the default batch-expiration purge delete every other key under the expired key's name, and why purging the key's own versions by ID after a recheck is the minimum safe repair.
- [Bucket Quota in the Console: List Display and Numeric Validation](/blog/design/console-quota-numeric-validation/) ([silo-console#72](https://github.com/pgsty/silo-console/issues/72), [silo-console#73](https://github.com/pgsty/silo-console/issues/73)): Why a Console-set quota showed as "-" in the bucket list, why bucket creation could turn a huge quota into one byte, where both came from, and what the merged Console fix covers.
- [Lock Domains of Large Single-Pool Clusters](/blog/design/single-pool-lock-domains/): Why DELETE and CopyObject fail to exclude PUT on the same key in single-pool clusters of 18 or more hosts, which layouts that covers, and the routing change that closes it.

## November 1: Pool Migration Integrity Review

- [Pool Migration Integrity Review: #261, #263, and #265](/blog/design/pool-migration-integrity-review/): A maintainer review of three reports and their fixes, including the contributor merge of #266 and maintainer follow-up #276.
- [Mixed EC Layouts and Migration Listing](/blog/design/mixed-ec-migration-listing/) ([#261](https://github.com/pgsty/silo/issues/261), [#262](https://github.com/pgsty/silo/pull/262)): Why a readable object can disappear from decommission and rebalance listings after an interrupted degraded overwrite, and why the narrow recount in #262 is sufficient.
- [Tier Free Versions Are Internal Cleanup Records](/blog/design/tier-free-version-semantics/) ([#263](https://github.com/pgsty/silo/issues/263), [#264](https://github.com/pgsty/silo/pull/264)): Why a free version must stay visible to healing but must not become a user-visible delete marker or a migration version.
- [ILM Expiry and Pool Migration Ordering](/blog/design/ilm-migration-ordering/) ([#265](https://github.com/pgsty/silo/issues/265), [#266](https://github.com/pgsty/silo/pull/266), [#276](https://github.com/pgsty/silo/pull/276)): Why a versioned Expiration marker must not cause the current version to be skipped, and how the maintainer follow-up preserves tier cleanup and completion semantics.

## October 24: FULL_OBJECT Checksum Replication

- [FULL_OBJECT Checksum Replication: Preserve the Type at Upload Initiation](/blog/design/replication-full-object-checksum/) (`#254`, `#255`): Why dropping the checksum type makes valid multipart CRC objects fail replication, how one shared header fix also restores the existing CopyObject path, and the source-upgrade and acceptance boundaries.

## October 24: Multi-Pool Deletion and Placement

- [Multi-Pool Deletion: Preserve the Latest Copy on Failure](/blog/design/multi-pool-delete-safety/) (`#256`, `#257`): Why an online-drive preflight cannot protect against later I/O failures, how staged cleanup preserves each item's authoritative copy, and the retry, tier-reference, performance, and compatibility boundaries of the merged fix.

- [Overwrite Pool Affinity: Why #245 Was Not Adopted](/blog/design/overwrite-pool-affinity/) (`#245`): The original placement problem, request-aware quorum and health improvements, unversioned-only scope, two rounds of m3 performance measurements, and the decision to stop after small-object overwrite regressions remained. The experimental changes were not merged.

## October 23 IAM & KMS Design Notes

- [LDAP Long DNs: Restoring Login Without Hiding Revocation Errors](/blog/design/ldap-long-dn/) (`#250`): How `\xx` hex escaping in `NormalizeDN` triggers the 255-byte single-component filename limit on the object IAM backend, and why `loadIAMConfigBytesWithMetadata` classifies only impossible pure-ASCII path components (`> 255` bytes) as `errConfigNotFound`.
- [IAM Policy Reloads: Lock Scope, Cancellation, and Time Budgets](/blog/design/iam-policy-cancellation/) (`#251`): Moving policy reload and KMS decryption outside the authentication-cache lock while retaining `writeMu`, threading request cancellation end-to-end to `KES.Decrypt`, and keeping `etcd` 30-second RPC deadlines separate from total decryption budgets.

## Server 20261018 Key Design Notes

For the [Server 20261018 release](/blog/release/silo-20261018/), see these core architecture notes:

- [Object Lock Governance & Overwrite Protection](/blog/design/governance-retention-bypass-repair/) (`SN-2026-015`, `SN-2026-016`)
- [IAM Admin Credential Authorization](/blog/design/iam-admin-authorization/) (`SN-2026-017`)
- [Durable IAM & Scoped STS Revocations](/blog/design/iam-revocations/#scoped-sts-20261018) (`SN-2026-013`)
- [LIST Recovery Lock Cost](/blog/design/listing-recovery-lock-cost/)
- [ListMultipartUploads Rollback & Capacity Boundaries](/blog/design/list-multipart-uploads/#implementation)
- [Multi-Pool Consistency & Rebalance Protection](/blog/design/multi-pool-object-consistency/#migration-20261018)
- [KES & OpenBao Integration](/blog/design/kes-openbao/)
