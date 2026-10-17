---
title: "Replicated Tag Ordering: Revision Timestamps, Tombstones, and Resurrection"
linkTitle: "Replicated Tag Ordering"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  The decision record for the replicated-tag repairs merged as PR #193 and #196:
  SSE-KMS destination copies silently dropped tag revision timestamps, and an
  empty tag value had no representable revision, so a delayed replication event
  could resurrect deleted tags. Covers the tombstone semantics, the
  stored-wins tie change, the two-ended upgrade requirement, and the cost of
  extra metadata copies during resync.
tags: [Design, Replication, S3, Review]
weight: 8
draft: false
url: "/blog/design/replicated-tag-ordering/"
---

> **Publication update, 2026-09-17:** The September source repairs discussed here shipped in [Server 20260916](/blog/release/silo-20260916/). Coordinated upgrades, opt-in prerequisites and remaining limitations still apply. Dated source-status and validation records below retain their original scope.

This page records the analysis and repair of two defects in how object tags
keep their ordering across replication, merged into Server main as
[PR #193](https://github.com/pgsty/silo/pull/193) (fix
[`03027727d`](https://github.com/pgsty/silo/commit/03027727d)) and
[PR #196](https://github.com/pgsty/silo/pull/196) (fix
[`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)).

> **As of 2026-09-16:** both fixes are on verified main
> [`40220bd836cb`](https://github.com/pgsty/silo/commit/40220bd836cbd066ca424fa4dc5dbb90057fb55a).
> They are **not** in the published Server 20260903; use the linked PRs to
> identify a build containing them.<br>
> **Delivery boundary:** source acceptance (regression tests plus the R4–R8
> integration run whose PR #196 checks passed) only. No tag, package, image,
> or production rollout is established by this record.<br>
> **Evidence class:** synthetic signed HTTP tests use real single-drive, 16-drive and multi-pool erasure backends; sender, wire-shape and precondition checks also include function-level tests. No customer incident is attributed to these paths.

## The shared model: a tag value and its revision are one state {#model}

Tags replicate with an internal revision timestamp
(wire header `X-Minio-Source-Tagging-Timestamp`, stored as `x-minio-internal-tagging-timestamp`). The ordering rule on the receiving
side is simple: a replicated tagging state wins only when its revision is
newer than the stored one. Both defects in this family break that rule by
making the revision — not the value — the part that gets lost:

- **R4** dropped the timestamp on the way *into* an SSE-KMS destination, so
  newer tag updates lost to stale stored state inside the storage-layer
  reconciliation.
- **R5** meant an *empty* value (a deletion) carried no revision at all, so
  the protocol could not express "deleted at time T" — and a delayed event
  could resurrect what a client had already deleted.

## R4: SSE-KMS destination copies dropped tag revision timestamps {#r4}

**Failure form.** A trusted replication COPY to an SSE-KMS encrypted
destination returned `200`, the object was correctly encrypted, plaintext GETs
worked — and the destination's tags and their timestamps stayed at the old
values. Because the HTTP request succeeded, nothing surfaced the loss. The
storage-layer reconciliation (`reconcileStoredObjectTags`) compares revisions
under the object write lock; without the incoming timestamp, the old stored
state won.

**Trigger surface.** Not only explicit SSE-KMS headers. Bucket-default KMS
and global automatic encryption hit the same code path, so the defect could
fire with no KMS header in the request at all.

**Root cause.** The option builder for PUT-like requests parsed the trusted
source-tagging timestamp into `ObjectOptions`, then the SSE-KMS branch
constructed and returned a *different* `ObjectOptions` carrying mtime, ETag,
replication trust, and two Object Lock timestamps — but not
`ReplicationSourceTaggingTimestamp`. The omission dated back to upstream
`c4373ef290` (2021); a 2026 Object Lock repair added two more timestamps to
that literal and still missed this one. Before R5, the consuming path was COPY ordering. R5 adds timestamp persistence for replica PUT and multipart initiation, as well as the duplicate-precondition consumer. Those SSE-KMS paths also depend on R4 preserving the option, so backports must consider the pair together.

**Fix.** One field added to the existing SSE-KMS `ObjectOptions` literal
([`03027727d`](https://github.com/pgsty/silo/commit/03027727d)), nothing
else. Regression tests cover every destination encryption (none, SSE-S3,
SSE-KMS with and without key context, SSE-C) crossed with trusted/untrusted
source, missing/valid/malformed timestamps, and 50 signed ordered COPY+GET
cycles across two single-pool backends (single-drive and 16-drive erasure)
with 1–3 ns event spacing. The KMS cases use a test stub.

**No backfill.** A lost source-tagging timestamp cannot be reconstructed at
the destination. After upgrading, *new* tag events replicate in order; replay
of old events still follows the timestamp comparison: an incoming event must
be strictly newer; the stored value wins ties and rejects older events.

**Deferred observation.** The same SSE-KMS literal also omits the proxy and
speedtest option fields; the speedtest flag is read on the storage path, so
global auto-encryption would drop it on a speedtest PUT. Recorded here as a separate follow-up, without asserting a public issue exists; deliberately not bundled into this repair.

## R5: empty tag values had no revision, so deletions could resurrect {#r5}

**Failure form.** Nine baseline regressions across real-storage and function-level tests:

- A successful `DeleteObjectTagging` never minted a new revision, so a
  *later-arriving* trusted metadata COPY with an older view of the tags
  re-instated them.
- A newer COPY carrying an *empty* tagging state was ignored — empty meant
  "nothing to say" instead of "deleted".
- The first replica PUT parsed the source tag timestamp and never persisted
  it.
- Equal visible tag values collapsed to "no replication needed". HEAD does not expose a tag revision, so a newer deletion or re-addition was invisible and ordering was not restored.
- A queued replication event's completion callback wrote the old tags from its
  snapshot back over an already-committed deletion — and without a timestamp,
  the resurrected set inherited the deletion's newer revision, which is worse
  than the originally-reported symptom.

**Root cause.** A tag value and its timestamp (including the empty value's
timestamp) constitute one state. The old protocol could only represent
non-empty states: DELETE-tagging never minted a revision, the sender only
attached timestamps in the non-empty branch, and the receiver only made
decisions in the non-empty branch.

**Fix** ([`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)):

1. **Every tagging mutation mints one revision.** PUT/DELETE tagging handlers
   unconditionally stamp a single UTC RFC3339Nano revision, whether or not
   replication selects the object. The storage layer enforces monotonicity
   under the write lock: a local revision that is not strictly newer is
   advanced to stored+1 ns, and multi-pool backends compute one value that
   strictly exceeds every pool's copy.
2. **The sender transmits tombstones.** Empty values carry their recorded
   revision; empty-without-revision is not fabricated; a malformed recorded
   timestamp fails closed rather than being silently repaired.
3. **The receiver accepts tombstones.** Replication COPY captures the stored
   tag pair before rebuilding, so an empty value with a timestamp enters the
   existing reconciliation as a state that can win. Duplicate suppression is
   relaxed only for a strictly newer source revision. Multipart completion
   orders tags from the persisted upload metadata. The delete-acknowledgement
   path no longer writes snapshot tags back. Ordinary SSE-C rotation drops the old tag timestamp from copied encryption metadata so it cannot overwrite the new local revision.

**Operator-visible changes:**

- **Equal timestamps now resolve to stored-wins** on unqualified and explicit
  null COPY requests. The old handler let the incoming state win ties on the
  unqualified path; the change is a compatibility-visible tightening in the
  correct direction.
- An ordinary COPY with `tagging REPLACE` and no tags now genuinely clears
  destination tags. The old default-metadata path carried source tags over —
  an S3 consistency improvement, but a behavior change.
- Every ordinary COPY (including key rotations that change nothing) records
  one new local revision.
- **Both ends of a replication pair must upgrade together.** An old peer
  still drops empty-value revisions, so a new sender's tombstones are
  invisible to it.
- Objects with recorded revisions incur **one extra metadata COPY per object**
  during explicit resync/heal. When the destination has bucket-default or
  automatic KMS encryption, that "metadata" COPY rewrites the object data —
  budget accordingly for bulk resync.

A nonempty legacy tag set without a revision uses object ModTime as its sender fallback; an empty set without a revision does not acquire a fabricated tombstone. A strictly newer trusted tag revision bypasses only the internal ETag/version duplicate guard (otherwise 412 `PreconditionFailed`); client `If-Match` and `If-None-Match` remain enforced.

The tag repair adds no wire field or storage format and has no capability negotiation. Both endpoints are needed for ordered deletions; an old hop retains the old behavior. This statement does not authorize rolling upgrade or downgrade of the entire September candidate, which also contains the separate [IAM migration](/operations/replication/iam-upgrade/). Reconcile already-damaged tags from an authoritative source by a new explicit tag change; the lost historical order cannot be reconstructed.

**Limits, stated as limits:**

- No migration: history with missing or wrong deletion timestamps cannot be
  reconstructed, and no historical tombstones are fabricated.
- Replication rules with tag filters evaluate target eligibility against the
  post-deletion (empty) tagging state, so a rule filtered on the deleted tag
  never sees the deletion. This is a pre-existing scoping decision, unchanged
  here.
- Arbitrary clock skew is not a total order. The repair establishes
  per-hop ordering, not multi-site causality.
- A malformed *recorded* timestamp makes the sender's construction fail
  permanently and the event retry through MRF until an explicit, correct tag
  change replaces it — deliberately fail-closed.

## Rejected alternatives {#rejected}

- **Synthesize a tombstone from ModTime for empty-without-revision objects.**
  Every object that never carried tags would gain a revision; combined with
  forced metadata replication, every object would take the metadata-COPY path
  on every hop.
- **Transmit only when the value is empty.** Withdrawn by its own proposer
  during review: the equal-value re-add sequence (set X at T1, delete at T2,
  re-add X at T3) loses the re-add's revision under that condition. A
  regression test (`TestTaggingRepeatedValueNeedsRevisionDelivery`) pins the
  counterexample.
- **A new HEAD revision protocol.** The pinned `minio-go` metadata extractor
  discards internal response headers, so this needs a new wire contract for
  marginal benefit; the worst case is still a forced metadata COPY.
- **A distributed causal clock, or regenerating timestamps at commit.** The
  wall-clock model plus the in-lock monotonic guard is the minimal correct
  fix.
- **Per-pool monotonic guards only.** Ordinary reads return single-pool
  object info, so a sender could emit a stale primary-pool revision; the
  unified multi-pool value is required.

## Verification and what it does not prove {#verification}

R4 regressions cover the encryption × trust × timestamp matrix and the ordered
sequence on two single-pool backends (single-drive and 16-drive erasure), with
a stub KMS. R5 separately has a multi-pool tagging-deletion regression. The
R4–R8 integration run repeated targeted tests on the merged tree, including
the isolated R5 multi-pool test; all eleven PR #196 checks passed.
These establish the tested ordering cases. They do not establish
multi-site scheduling under real clock skew, cross-region failover, or
behavior of deployments that upgrade one end of a pair only.

The upgrade summary and release boundary live in the
[component matrix](/compatibility/versions/#september-reliability); the
sibling repair that stops normalized replica metadata from being re-injected
is recorded separately in [Replica Metadata
Normalization](/blog/design/replica-metadata-normalization/).

Related records: [tags](/blog/design/replicated-tag-ordering/) · [metadata](/blog/design/replica-metadata-normalization/) · [HTTP](/blog/design/request-header-timeouts/) · [audit](/operations/replication/replica-metadata-audit/)
