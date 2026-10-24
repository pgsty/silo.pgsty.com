---
title: "Object Lock Replication Ordering"
linkTitle: "Object Lock Replication Ordering"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: "Retention, legal hold and their removals are independently ordered state across replica writes and pools."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/object-lock-replication-ordering/"
---

Initial Object Lock replication timestamp ordering ([`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9)) shipped in [SILO Server 20260903](/blog/release/silo-20260903/) (recorded in the [security advisory ledger](/about/security-advisories/#operational)). Subsequent fixes for timestamp-only removals, SSE-C replica retransmission, and multi-pool Object Lock reconciliation ([PR #129](https://github.com/pgsty/silo/pull/129), [PR #134](https://github.com/pgsty/silo/pull/134), and [PR #178](https://github.com/pgsty/silo/pull/178)) shipped in [SILO Server 20260916](/blog/release/silo-20260916/).

## Preserve Stored State Before Rebuilding Destination Metadata {#problem}

Previously, a replica `COPY` rebuilt the destination metadata map from the incoming request before comparing Object Lock retention and legal-hold revision timestamps. Rebuilding the map first wiped out the stored timestamps, causing stale incoming replication requests to overwrite newer destination state. In addition, the handler wrote the legal-hold revision timestamp into the retention timestamp key.

Commit [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9) captures the stored Object Lock state before rebuilding the destination metadata map and tracks each field's revision timestamp under its own dedicated metadata key.

Retention (`mode` + `retain-until-date`) and legal hold (`status`) act as independent state registers:

- A newer retention timestamp never makes an older legal-hold value authoritative (and vice versa).
- The object's payload modification time (`ModTime`) never substitutes for either field's explicit revision timestamp.
- An incoming field update is applied only when its source revision timestamp is strictly newer than the stored timestamp for that field; stale or equal-timestamp updates preserve the stored destination value.

## Treating Removals as Timestamped Tombstones {#removals}

Clearing an object's retention period or legal hold leaves an empty field value on the object while still carrying a source revision timestamp. If that revision timestamp is dropped when the value becomes empty, a delayed replication request carrying an older non-empty retention or legal hold will re-apply the cleared lock.

[PR #129](https://github.com/pgsty/silo/pull/129) and [PR #134](https://github.com/pgsty/silo/pull/134) preserve and compare timestamp-only removals across replication send, receive, and resync paths, distinguishing an uninitialized field (no value and no revision timestamp) from an explicit removal (empty value with a revision timestamp).

The receiver preserves these per-field timestamps across both metadata-only replica `COPY` requests and full SSE-C replica object retransmissions. Rewriting an SSE-C replica's encrypted payload during retransmission cannot clear a newer destination legal hold or overwrite a newer destination retention timestamp.

## Cross-Pool Authority {#pools}

When an object version has physical copies in multiple storage pools (for example, during or after pool expansion or decommissioning), reading a single local erasure set cannot establish the latest Object Lock state. The [multi-pool consistency coordinator](/blog/design/multi-pool-object-consistency/) ([PR #178](https://github.com/pgsty/silo/pull/178), closing [#133](https://github.com/pgsty/silo/issues/133)) gathers all same-version copies across pools under the shared namespace object lock and merges retention and legal-hold fields independently by their respective revision timestamps. An unreadable or quorum-failed pool returns an error rather than being treated as an empty lock state.

## Authorization and Operational Boundaries {#limits}

Timestamp ordering governs conflict resolution on authorized replica writes; it does not grant permission to modify Object Lock settings. Standard replication trust checks and S3/admin permissions (`s3:ReplicateObject`, `s3:BypassGovernanceRetention`, `s3:PutObjectRetention`, `s3:PutObjectLegalHold`) remain enforced. Timestamp comparison establishes per-field ordering across replication hops; it does not compensate for unsynchronized wall clocks across sites or provide distributed rollback across partial drive failures.

Upgrading prevents stale replication events from overwriting newer Object Lock state going forward, but does not automatically reconstruct retention or legal-hold values that were overwritten prior to the upgrade. Operators should verify exact-version retention and legal-hold state against authoritative records before declaring recovery.

## Verification {#verification}

The Object Lock merge logic in [`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) and the replica write paths in `cmd/erasure-object.go` are covered by regression tests exercising stale vs. newer field updates, timestamped empty-value removals, independent retention and legal-hold timestamps, SSE-C full retransmission, and multi-pool reconciliation.

See also the [Replica Metadata Audit runbook](/operations/replication/replica-metadata-audit/), [SSE-C Replica Integrity](/blog/design/ssec-replica-integrity/), and the [component version matrix](/compatibility/versions/). All participating nodes in a replication topology should be upgraded together.
