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
