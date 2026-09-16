---
title: "Multi-Pool Object Consistency"
linkTitle: "Multi-Pool Object Consistency"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: "Select one logical object under a shared lock before evaluating conditions or merging tags and Object Lock state."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/multi-pool-object-consistency/"
---

> **Publication update, 2026-09-17:** The September source repairs discussed here shipped in [Server 20260916](/blog/release/silo-20260916/). Coordinated upgrades, opt-in prerequisites and remaining limitations still apply. Dated source-status and validation records below retain their original scope.


**Source status, 2026-09-16:** [#178](https://github.com/pgsty/silo/pull/178) repairs multi-pool mutation ordering; [#207](https://github.com/pgsty/silo/pull/207) extends current-object selection to conditional PUT. These changes are merged into main and absent from Server 20260903. They close the source defects tracked by [#133](https://github.com/pgsty/silo/issues/133) and [#144](https://github.com/pgsty/silo/issues/144); this does not establish acceptance of a new release artifact.

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

## Evidence and operator impact {#verification}

The [coordinator implementation](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go), [pool entry points](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go), and the two merged PRs identify the source contract. Coverage includes multiple pools, stale copies, delete markers, explicit versions, concurrent writes and failure paths. It is not a claim of atomic rollback or arbitrary fault tolerance.

Upgrade all participants before depending on the shared-lock guarantees. Inventory historical copies, tags and Object Lock state when a deployment may already have encountered the defect; the source repair does not prove historical cleanup. Use the [replica audit runbook](/operations/replication/replica-metadata-audit/) and [component matrix](/compatibility/versions/). The multi-pool repair is separate from the default limitations and scan cost of [multipart upload listing](/blog/design/list-multipart-uploads/).
