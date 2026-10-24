---
title: "Replicated Tag Ordering: Revision Timestamps, Tombstones, and Resurrection"
linkTitle: "Replicated Tag Ordering"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The decision record for the replicated-tag repairs merged as PR #193 and #196: SSE-KMS destination copies silently dropped tag revision timestamps, and an empty tag value had no representable revision, so a delayed replication event could resurrect deleted tags. Covers the tombstone semantics, the stored-wins tie change, the two-ended upgrade requirement, and the cost of extra metadata copies during resync.
tags: [Design, Replication, S3, Review]
weight: 8
draft: false
url: "/blog/design/replicated-tag-ordering/"
---

Shipped in [SILO Server 20260916](/blog/release/silo-20260916/) (`40220bd836cbd066ca424fa4dc5dbb90057fb55a`), [PR #193](https://github.com/pgsty/silo/pull/193) (commit [`03027727d`](https://github.com/pgsty/silo/commit/03027727d)) and [PR #196](https://github.com/pgsty/silo/pull/196) (commit [`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)) fix two defects in how object tags preserve ordering across bucket replication: SSE-KMS destination copies silently dropping tag revision timestamps (`R4`), and empty tag values lacking a revision timestamp so delayed replication events could resurrect deleted tags (`R5`).

## The Shared Model: A Tag Value and Its Revision Form One State {#model}

Object tags replicate alongside an internal revision timestamp (transmitted over the wire as `X-Minio-Source-Tagging-Timestamp` and stored in `xl.meta` as `x-minio-internal-tagging-timestamp`). On the receiving cluster, `reconcileStoredObjectTags` enforces a simple ordering rule under the object write lock: an incoming replicated tag state wins only when its revision timestamp is strictly newer than the stored revision timestamp.

Both defects broke that invariant by dropping the revision timestamp rather than the tag value:

- **R4 ([PR #193](https://github.com/pgsty/silo/pull/193)):** Dropped `ReplicationSourceTaggingTimestamp` when constructing `ObjectOptions` on an SSE-KMS destination, causing newer incoming tag updates to lose to older stored state during storage-layer reconciliation.
- **R5 ([PR #196](https://github.com/pgsty/silo/pull/196)):** Treated an empty tag string (a tag deletion) as having no revision timestamp at all, leaving the replication protocol unable to express *"tags deleted at time $T$"* and allowing delayed pre-delete replication events to resurrect deleted tags.

## R4: SSE-KMS Destination Copies Dropped Tag Revision Timestamps {#r4}

**Failure mode:** A trusted replication `COPY` to an SSE-KMS encrypted destination returned HTTP `200 OK`, encrypted the object properly, and served plaintext `GET` requests—yet the destination object's tags and tag revision timestamp remained stuck at their previous values. Because the HTTP request succeeded, no replication error or MRF retry was triggered. Inside `reconcileStoredObjectTags`, the missing incoming timestamp caused the older stored tag state to win every comparison.

**Trigger surface:** This path is entered not only when a request carries explicit SSE-KMS headers, but also whenever the destination bucket has default SSE-KMS configured or the cluster enables global auto-encryption.

**Root cause:** In `putOptsFromReq`, the option builder parsed the trusted `X-Minio-Source-Tagging-Timestamp` header into `ObjectOptions`. Immediately afterward, the SSE-KMS branch constructed and returned a fresh `ObjectOptions` struct literal copying `MTime`, `ETag`, replication trust flags, and the two Object Lock timestamps—while omitting `ReplicationSourceTaggingTimestamp`. That omission originated in upstream commit `c4373ef290` (2021) and survived a 2026 Object Lock patch that added two retention/legal-hold timestamps to the same struct literal.

**Fix ([`03027727d`](https://github.com/pgsty/silo/commit/03027727d)):** Forwards `ReplicationSourceTaggingTimestamp: opts.ReplicationSourceTaggingTimestamp` in the SSE-KMS `ObjectOptions` literal. Regression tests verify the full cartesian matrix of destination encryption modes (none, SSE-S3, SSE-KMS with and without key context, SSE-C), trusted vs. untrusted callers, missing/valid/malformed timestamps, and 50 signed ordered `COPY`+`GET` cycles with 1–3 ns spacing across single-drive and 16-drive erasure backends.

*Note on adjacent SSE-KMS struct fields:* The same SSE-KMS `ObjectOptions` literal also omits the `ProxyRequest` and `Speedtest` fields; that separate observation is tracked independently outside this replication fix.

## R5: Empty Tag Values Carried No Revision, Allowing Deleted Tags to Resurrect {#r5}

**Failure mode:** Baseline testing uncovered nine distinct failure cases across single-pool and multi-pool storage backends:

1. `DeleteObjectTagging` never minted a new revision timestamp, so a delayed metadata `COPY` carrying an older tag snapshot overwrote the deletion and restored the old tags.
2. An incoming replication `COPY` carrying an empty tag set was treated as "no tag update supplied" rather than "tags cleared at timestamp $T$."
3. An initial replica `PUT` parsed `X-Minio-Source-Tagging-Timestamp` from the wire but never persisted it to `xl.meta`.
4. When source and target visible tag strings were both empty (or equal), the replication sender skipped metadata replication because `HEAD` does not expose the internal tag revision timestamp, leaving newer deletions or re-additions unreplicated.
5. When a queued replication event completed, its local status callback wrote the snapshot's old tags back into local metadata over a newer committed `DeleteObjectTagging`—and because the deletion had minted a timestamp in early prototypes or lacked one, the resurrected tags inherited the wrong revision state.

**Root cause:** A tag set and its revision timestamp (including the timestamp of an empty tag set) form a single versioned register. The legacy implementation only stamped, transmitted, and reconciled timestamps when the tag string was non-empty.

**Fix ([`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)):**

1. **Every tagging mutation mints a monotonic revision:** `PutObjectTagging` and `DeleteObjectTagging` unconditionally stamp a UTC `RFC3339Nano` revision timestamp regardless of whether replication is currently active on the bucket. Under the object write lock, the storage layer enforces strict monotonicity: if a new local timestamp is $\le$ the stored revision, it advances to $\text{stored} + 1\text{ ns}$; on multi-pool clusters, the coordinator computes a unified timestamp strictly greater than the maximum revision across all pools.
2. **Sender transmits tombstones:** Empty tag sets with a recorded revision timestamp transmit `X-Minio-Source-Tagging-Timestamp` as a deletion tombstone. Objects that never had tags (empty value and no recorded revision) do not fabricate a tombstone. If a stored timestamp is malformed on disk, the sender fails closed and retries via MRF until an explicit tag write replaces it.
3. **Receiver reconciles tombstones:** Replication `COPY` captures the existing `(tags, timestamp)` pair before rebuilding metadata so a timestamped empty value participates in `reconcileStoredObjectTags` and clears older stored tags. Internal duplicate-version suppression (`412 PreconditionFailed`) is relaxed when the incoming trusted tag revision is strictly newer than the stored revision (while client `If-Match` and `If-None-Match` headers remain strictly enforced). Multipart completion orders tags using the persisted upload metadata, the replication completion callback no longer writes snapshot tags back over local state, and ordinary SSE-C key rotation strips old tag timestamps from copied encryption metadata so a rotation mints a clean local revision.

### Operator-Visible Changes and Upgrade Requirements

- **Equal-timestamp ties resolve to stored-wins:** Both unversioned and explicit `null`-version `COPY` requests now keep the stored destination state when incoming and stored tag timestamps are identical.
- **Ordinary `COPY` with `X-Amz-Tagging-Directive: REPLACE` and empty tags:** Now clears destination tags as required by S3, instead of falling back to copying source tags.
- **Coordinated two-ended upgrade required:** Both source and target clusters in a replication pair must be upgraded to [SILO Server 20260916](/blog/release/silo-20260916/) (see also the [IAM and replication upgrade guide](/operations/replication/iam-upgrade/)). An unupgraded peer still ignores empty-value revision headers.
- **One additional metadata `COPY` per tagged object during resync/heal:** Because `HEAD` does not expose internal tag revision headers through `minio-go`, explicit resync/heal issues one metadata `COPY` for objects that carry a recorded tag revision. On destination buckets with default or global SSE-KMS encryption, that metadata `COPY` rewrites the object payload—account for this I/O when scheduling bulk resyncs.
- **Scope boundaries:** Historical missing or overwritten deletion timestamps are not reconstructed automatically; repair affected objects by issuing a fresh `PutObjectTagging` or `DeleteObjectTagging` on the authoritative source. Tag-filtered replication rules continue to evaluate target eligibility against the post-mutation tag set, and per-hop timestamp comparison relies on synchronized wall clocks (NTP) across sites.

## Rejected Alternatives {#rejected}

- **Synthesize a tombstone from `ModTime` for untagged objects:** Would assign a synthetic tag revision to every object ever written, forcing every untagged object through an extra metadata `COPY` on every replication hop.
- **Transmit the revision header only when the tag value is empty:** Withdrawn during review because the sequence *"set tag `X` at $T_1$ $\to$ delete at $T_2$ $\to$ re-add identical tag `X` at $T_3$"* loses the $T_3$ revision if non-empty updates omit the timestamp when visible values match (`TestTaggingRepeatedValueNeedsRevisionDelivery`).
- **Extend the `HEAD` wire protocol to return internal tag revisions:** The pinned `minio-go` metadata reader strips internal `X-Minio-*` response headers, so exposing revisions on `HEAD` would require a cross-SDK wire change while still needing a metadata `COPY` whenever revisions differ.
- **Introduce vector clocks or regenerate timestamps at storage commit:** A wall-clock `RFC3339Nano` timestamp paired with the `+1 ns` monotonic floor under the object write lock achieves per-key monotonicity without changing on-disk formats.
- **Enforce monotonicity per pool instead of across all pools:** Because ordinary reads can return metadata from a single pool, per-pool monotonic counters could still emit a timestamp older than a sibling pool's copy; computing the maximum across all pools under the namespace lock prevents cross-pool regression.

## Verification {#verification}

`R4` and `R5` regression suites cover the full encryption $\times$ trust $\times$ timestamp matrix across single-drive, 16-drive erasure, and multi-pool erasure backends (with all 11 CI checks passing on [PR #196](https://github.com/pgsty/silo/pull/196)).

See the [component version matrix](/compatibility/versions/#september-reliability) for release alignment and [Replica Metadata Normalization](/blog/design/replica-metadata-normalization/) for the companion metadata extraction fix. Related records: [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/) · [Replica Metadata Normalization](/blog/design/replica-metadata-normalization/) · [Request Header Timeouts](/blog/design/request-header-timeouts/) · [Replica Metadata Audit](/operations/replication/replica-metadata-audit/).
