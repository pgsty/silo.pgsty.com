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

> **Publication update, 2026-09-17:** The September source repairs discussed here shipped in [Server 20260916](/blog/release/silo-20260916/). Coordinated upgrades, opt-in prerequisites and remaining limitations still apply. Dated source-status and validation records below retain their original scope.


**Source status, 2026-09-16:** [#178](https://github.com/pgsty/silo/pull/178) repairs multi-pool mutation ordering; [#207](https://github.com/pgsty/silo/pull/207) extends current-object selection to conditional PUT. These changes are merged into main and absent from Server 20260903. They close the source defects tracked by [#133](https://github.com/pgsty/silo/issues/133) and [#144](https://github.com/pgsty/silo/issues/144); this does not establish acceptance of a new release artifact.

## October 18: preserve data during pool migration {#migration-20261018}

The [20261018 release](/blog/release/silo-20261018/) adds [`60c7179dd`](https://github.com/pgsty/silo/commit/60c7179ddbfcbd41a1fe67707230f5b360a43020), incorporating [#248](https://github.com/pgsty/silo/pull/248), and [`1748f62c7`](https://github.com/pgsty/silo/commit/1748f62c7ec4f2e9afcdce276193ad401719b951). They repair stale payload overwrite and delete-marker loss in rebalance/decommission; the September fixes above do not cover these later repairs.

Before committing a moved version, the pool layer checks current copies under the common object lock. It rejects an absent/replaced source snapshot or a copy superseded by another pool. Conflicting equal timestamps retain the same pool-order winner as reads. The resulting metadata snapshot is reused for reconciliation; multipart completion rechecks after the parts have been copied. Tiered-object movement also uses the guard.

Delete markers are moved even when they are the only version in the source pool, because older data may exist elsewhere. Null and UUID markers retain their intended replacement/retry semantics. Source cleanup now checks and deletes the walker's individual versions under the object write lock. It stops if the source changed or no retained destination copy preserves the read result, rather than deleting a whole prefix that may contain a concurrent write or new marker.

**Cost and limits:** migration adds per-pool metadata reads and per-version cleanup. For P pools and V source versions, cleanup performs at least O(P × V) metadata operations; decoding and rewriting version metadata can add cost as history grows. Measure maintenance duration and same-key lock waiting on representative histories. Ordinary resolved reads are not unconditionally routed through this migration check. No new object disk format, public S3 parameter or dependency is introduced. Previously lost data/tags/markers are not reconstructed, and the cross-site late-marker issue [#217](https://github.com/pgsty/silo/issues/217) remains separate.

The final-source local artifact acceptance ran actual 2/3-pool rebalance and decommission, including ordinary/multipart data, null/UUID versions and markers, concurrent writes/deletes and two-pool interruption/recovery. All four cases passed. These shared-host tests do not establish physical failure-domain resilience or a production throughput target. Before retiring a source pool, compare acknowledged version IDs, bytes, ETags, tags and deletion state through the public API. See the [release evidence and boundaries](/blog/release/silo-20261018/#delivery).


## One key can have several physical copies {#problem}

A pool expansion, decommission or interrupted cleanup can leave copies of one key in different pools. A per-set lock does not serialize an operation with a writer choosing another pool. Nor does reading the first copy prove that its ETag, tags or retention represent the logical object.

The relevant failures include a stale ETag satisfying a conditional write or delete, a newer retention/hold disappearing behind older object metadata, and an older copy becoming visible after deleting the selected copy. Reading each pool independently and combining only its success status does not solve these races.

## Shared selection and lock boundary {#design}

The pool coordinator holds one namespace object lock across selection and mutation. `objectPoolInfos` reads the addressed version in every pool, including draining pools. Unknown/unreadable state is an error, not evidence that the object is absent. Copies are ordered by modification time with pool index as the equal-time tie-breaker.

An unqualified metadata request first resolves the logical current version, then gathers copies of that version. It must not merge metadata from unrelated object versions. Object Lock retention, legal hold and tags have independent source timestamps; `mergedPoolObjectInfo` combines those fields by their own order rather than treating the object's modification time as every field's revision. An ordered removal is state too.

Metadata writers, relevant object writers and healing use the same coordinating lock. The lock is not a transaction that can undo completed disk writes on every pool after a later failure.

## Conditions and deletion {#conditions}

For conditional DELETE, evaluate once before cleanup and clear the callback before invoking lower pools. An explicit `versionId` compares that version. For conditional PUT, select the latest logical representation across eligible pools while holding the outer lock, including the delete-marker state, before installing the replacement. [#207](https://github.com/pgsty/silo/pull/207) addresses the case where a stale destination-pool copy made `If-Match`/`If-None-Match` disagree with the current object.

Cleanup and metadata propagation can still partially modify physical copies before a storage failure is reported. A quorum/cleanup failure must not be interpreted as an unchanged object or as proof every old copy disappeared. Verify state and retry after recovery. Batch XML ETag conditions remain unsupported; see [conditional DELETE](/blog/design/conditional-delete/).

## Object Lock and replication {#replication}

Replica writes reconcile destination retention and legal-hold state against authoritative same-version copies across pools. A stale incoming replica must not shorten a newer retention or turn off a newer hold. Tags similarly travel with their timestamp, including an empty deletion value. See [Object Lock ordering](/blog/design/object-lock-replication-ordering/) and [replicated tags](/blog/design/replicated-tag-ordering/).

## Tags across pool migration {#migration-tags}

Rebalance and decommission read each version as a `FileInfo`, convert it to an `ObjectInfo` — which moves the tag header out of the ordinary metadata map into `UserTags` — and rewrite the object in the destination pool. Since their introduction in 2022 the migration writers copied only the ordinary metadata map, so tags were dropped for ordinary and multipart objects on both entry points; the 2020 field split itself is correct. Commit [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) gives the four migration writers one metadata assembly that clones the map, restores `UserTags` and keeps the tag revision fields exactly as stored, without inventing timestamps, under the existing coordination locks. Regressions cover ordinary and multipart objects, initial tags, updated and cleared tags, and versioned and legacy readers.

The repair only prevents future loss. Tags already dropped by an earlier migration are not recovered; restoring them needs a trusted source of the old values. The post-repair eight-node rebalance and decommission acceptance was not completed at the time of writing.

## Evidence and operator impact {#verification}

The [coordinator implementation](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go), [pool entry points](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go), and the two merged PRs identify the source contract. Coverage includes multiple pools, stale copies, delete markers, explicit versions, concurrent writes and failure paths. It is not a claim of atomic rollback or arbitrary fault tolerance.

Upgrade all participants before depending on the shared-lock guarantees. Inventory historical copies, tags and Object Lock state when a deployment may already have encountered the defect; the source repair does not prove historical cleanup. Use the [replica audit runbook](/operations/replication/replica-metadata-audit/) and [component matrix](/compatibility/versions/). The multi-pool repair is separate from the default limitations and scan cost of [multipart upload listing](/blog/design/list-multipart-uploads/).
