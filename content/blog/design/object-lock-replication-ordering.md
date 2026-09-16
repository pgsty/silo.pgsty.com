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

**Release boundary, 2026-09-16:** [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9) shipped in Server 20260903. The later timestamp-only removal, SSE-C retransmission and cross-pool repairs in [#129](https://github.com/pgsty/silo/pull/129), [#134](https://github.com/pgsty/silo/pull/134) and [#178](https://github.com/pgsty/silo/pull/178) are on main and not in that release. The [advisory ledger](/about/security-advisories/#operational) records the original ordering defect.

## Preserve the old state before rebuilding metadata {#problem}

A replica COPY used to rebuild metadata from the incoming request before comparing retention and legal-hold timestamps. The old timestamps were therefore lost, so a stale request could appear authoritative. The legal-hold timestamp also went into the retention timestamp key. The first fix captures the stored state before rebuilding the destination map and keeps each field's revision under its own key.

Retention and legal hold are independent registers. A later retention does not make an older legal hold authoritative, and the object's modification time is not a substitute for either field's revision. Apply an incoming field only when its timestamp is newer than that field's stored timestamp; retain the stored value for a stale or equal update.

## Removal is an ordered value {#removals}

Removing retention or a hold can leave no live value but still carries a source timestamp. Dropping that timestamp would let a delayed old value return. The later repair recognizes timestamp-only removals during receive, comparison and resend. An absent value with no ordering evidence is different from a recorded removal.

The receiver must preserve these distinctions through ordinary metadata copies and full SSE-C replica retransmission. A retransmitted object cannot erase a newer destination hold or resurrect an older retention just because its body is being rewritten.

## Cross-pool authority {#pools}

If one version has copies in multiple pools, one local set cannot decide the latest field state. The [multi-pool coordinator](/blog/design/multi-pool-object-consistency/) gathers same-version copies under the shared object lock and merges retention and hold independently by their timestamps. Unknown pool state is not an empty value. This closes the source-level boundary originally left open as #133.

## Authorization and limitations {#limits}

Ordering does not grant permission to change Object Lock. The replication trust checks and the relevant S3/admin permissions still apply. It is not a new user API for bypassing governance or compliance retention. It also does not create causal ordering between unsynchronized source clocks or a distributed rollback after partial storage failure.

A historical stale update may already have changed stored state. Upgrading only prevents the repaired paths from accepting the same error again; it does not reconstruct missing retention history. Verify exact-version retention and legal hold at each site against authoritative records before declaring recovery.

## Evidence {#verification}

See the [Object Lock merge implementation](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go), the replica write paths in `erasure-object.go`, and the linked PRs. The tested cases include stale/newer field updates, empty-value removals, distinct field timestamps, SSE-C retransmission and multiple pools. These source tests do not prove every historical replica has converged.

Use the [replica audit runbook](/operations/replication/replica-metadata-audit/), [SSE-C integrity record](/blog/design/ssec-replica-integrity/) and [release matrix](/compatibility/versions/) together. Upgrade all participating nodes before relying on the combined ordering contract.
