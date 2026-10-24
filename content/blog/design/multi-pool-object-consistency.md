---
title: "Multi-Pool Object Consistency"
linkTitle: "Multi-Pool Object Consistency"
date: 2026-09-16
lastmod: 2026-10-19
author: "Ruohang Feng"
summary: "Select one logical object under a shared lock before evaluating conditions or merging tags and Object Lock state."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/multi-pool-object-consistency/"
---

Shipped in [SILO Server 20260916](/blog/release/silo-20260916/), [PR #178](https://github.com/pgsty/silo/pull/178) repairs multi-pool mutation ordering, [PR #207](https://github.com/pgsty/silo/pull/207) extends current-object selection to conditional `PUT` (closing [#133](https://github.com/pgsty/silo/issues/133) and [#144](https://github.com/pgsty/silo/issues/144)), and commit [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) preserves object tags across pool rebalance and decommission. [SILO Server 20261018](/blog/release/silo-20261018/) further adds [`60c7179dd`](https://github.com/pgsty/silo/commit/60c7179ddbfcbd41a1fe67707230f5b360a43020) (incorporating [PR #248](https://github.com/pgsty/silo/pull/248)) and [`1748f62c7`](https://github.com/pgsty/silo/commit/1748f62c7ec4f2e9afcdce276193ad401719b951) to guard pool migration against stale payload overwrites and delete-marker loss.

## October 18: Preserving Data and Delete Markers During Pool Migration {#migration-20261018}

Commits [`60c7179dd`](https://github.com/pgsty/silo/commit/60c7179ddbfcbd41a1fe67707230f5b360a43020) ([PR #248](https://github.com/pgsty/silo/pull/248)) and [`1748f62c7`](https://github.com/pgsty/silo/commit/1748f62c7ec4f2e9afcdce276193ad401719b951) in [SILO Server 20261018](/blog/release/silo-20261018/) close two rebalance and decommission race windows that remained after the September fixes: stale payload overwrite and delete-marker loss.

Before committing a moved version to the destination pool, the pool layer inspects current copies across all pools under the common namespace object lock. It aborts the move if the source snapshot has disappeared or been replaced, or if another pool already holds a newer copy of the key. Equal-timestamp ties use the same deterministic pool-index tie-breaker as reads. The verified metadata snapshot is reused for field reconciliation; multipart completion re-verifies the snapshot after copying all parts, and tiered-object movement applies the same guard.

Delete markers are now migrated even when a delete marker is the only version present in the source pool, because older live versions of that key may still reside in other pools. Both `null` and UUID-versioned delete markers preserve their replacement and retry semantics. During source cleanup, the migration worker re-verifies and deletes only the specific versions observed by the walker while holding the object write lock. Cleanup stops immediately if the source version changed or if no retained destination copy preserves the externally visible read result, rather than deleting an entire key prefix that might now contain a concurrent write or a newer delete marker.

**Runtime cost and boundaries:** Migration now performs per-pool metadata reads and per-version source cleanup. Across $P$ pools and $V$ source versions, cleanup executes at least $\mathcal{O}(P \times V)$ metadata operations, and decoding/rewriting `xl.meta` version histories scales with version count. Ordinary resolved reads do not pay this migration check cost. No new on-disk format, S3 parameter, or external dependency is introduced. Data, tags, or delete markers lost during migrations on older releases cannot be reconstructed automatically, and cross-site late-arriving delete markers ([#217](https://github.com/pgsty/silo/issues/217)) remain a separate topic.

Release verification exercised live 2-pool and 3-pool rebalance and decommission runs covering single-part and multipart objects, `null` and UUID versions and delete markers, concurrent writes and deletes, and interrupted/resumed two-pool migrations (see the [20261018 release verification record](/blog/release/silo-20261018/#delivery)). Before retiring a decommissioned source pool in production, compare acknowledged version IDs, byte counts, ETags, tags, and deletion state through the S3 API.

## Why One Key Can Have Multiple Physical Copies {#problem}

Pool expansion, decommissioning, or an interrupted cleanup can leave physical copies of the same object key in more than one storage pool. Taking a lock on a single erasure set does not serialize against a concurrent writer that hashes or routes to another pool, and reading the first responding pool does not prove that its ETag, tags, or Object Lock retention state represent the current logical object.

Without cross-pool coordination, three classes of anomalies occur:

1. A stale ETag in one pool falsely satisfies a conditional write (`If-Match` / `If-None-Match`) or conditional delete.
2. A newer Object Lock retention date or legal hold in one pool is shadowed by older object metadata in another pool.
3. Deleting the winning copy in one pool uncovers an older copy in another pool, resurrecting deleted data.

Operating on each pool independently and combining only their success statuses cannot prevent these races.

## Shared Selection and Lock Boundary {#design}

In [`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) and [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go), the pool coordinator holds a single namespace-level object lock across both candidate selection and mutation. `objectPoolInfos` queries the target version across every pool, including draining pools. An unreadable or quorum-failed pool is treated as an error rather than evidence of absence. Candidate copies are ordered by `ModTime`, with the pool index breaking exact timestamp ties.

An unversioned metadata request first resolves the logical current version across pools and then gathers physical copies of that exact version, never mixing metadata from distinct object versions. Because Object Lock retention, legal hold, and user tags each carry their own revision timestamps, `mergedPoolObjectInfo` merges each field by its own revision timestamp rather than using the object's payload `ModTime` as a blanket version for all metadata fields. A timestamped tag or hold removal is preserved as an explicit state transition.

Metadata updates, object writes, and background healing share this coordinating lock. Note that the lock serializes concurrent callers but does not act as a multi-pool rollback transaction if a disk failure occurs midway through multi-pool cleanup.

## Conditional Writes and Deletions {#conditions}

For conditional `DELETE`, the coordinator evaluates the precondition once against the resolved logical object before starting multi-pool cleanup, and clears the precondition callback before invoking individual pool deletes. When an explicit `versionId` is supplied, the condition is evaluated against that specific version.

For conditional `PUT`, [PR #207](https://github.com/pgsty/silo/pull/207) selects the latest logical representation across all eligible pools—including delete-marker state—while holding the outer namespace lock before writing the new version. This prevents a stale copy in the destination pool from causing `If-Match` or `If-None-Match` to disagree with the cluster's current logical object.

If a storage failure occurs partway through multi-pool cleanup or metadata propagation, operators should re-verify object state and retry after drive recovery. Batch `DeleteObjects` XML ETag conditions remain unsupported (see [Conditional DELETE](/blog/design/conditional-delete/)).

## Object Lock and Bucket Replication {#replication}

Incoming replica writes reconcile destination Object Lock retention and legal-hold state against authoritative same-version copies across all pools, ensuring that an out-of-order replica write cannot shorten a newer retention period or clear a newer legal hold. Replicated object tags likewise travel with their revision timestamps, including empty-string deletion markers. See [Object Lock Replication Ordering](/blog/design/object-lock-replication-ordering/) and [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/) for details.

## Preserving Object Tags Across Pool Migration {#migration-tags}

Pool rebalance and decommission read each version from disk as a `FileInfo`, convert it into an `ObjectInfo`—which moves `X-Amz-Meta-Minio-Internal-Tagging` out of the general `UserDefined` metadata map into the dedicated `ObjectInfo.UserTags` field—and then write the object into the destination pool. Because the migration writers introduced in 2022 copied only the `UserDefined` map when constructing the destination write, both rebalance and decommission silently dropped user tags on single-part and multipart objects.

Commit [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) routes all four migration write paths through a shared metadata assembly helper that clones the metadata map, restores `UserTags`, and preserves existing tag revision timestamps verbatim under the coordination lock. Regression tests cover single-part and multipart objects, initial tags, updated tags, cleared tags, versioned objects, and legacy metadata records. Tags dropped by migrations on earlier releases must be restored from source buckets or backups.

## Verification and Operational Guidance {#verification}

The multi-pool consistency implementation in [`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) and [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go) is covered by multi-pool unit and functional tests exercising stale pool copies, delete markers, explicit version IDs, concurrent writes, and partial failure paths.

All nodes in a multi-pool cluster must be upgraded together so every peer participates in the shared namespace lock. Clusters that previously ran multi-pool migrations or concurrent multi-pool writes should audit existing copies, tags, and Object Lock state using the [Replica Metadata Audit runbook](/operations/replication/replica-metadata-audit/) and check the [component version matrix](/compatibility/versions/).
