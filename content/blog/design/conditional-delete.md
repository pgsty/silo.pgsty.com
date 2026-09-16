---
title: "Conditional DELETE: One Condition, One Logical Object"
linkTitle: "Conditional DELETE"
date: 2026-08-26
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Single-object If-Match DELETE is implemented on main, with addressed-version semantics and a shared multi-pool lock. Batch ETags, the additional GetObject permission check, and malformed or recursive-request guards from the early proposal are not implemented. This record separates the merged contract from that proposal.
tags: [Design, S3, Compatibility, DELETE]
weight: 10
draft: false
url: "/blog/design/conditional-delete/"
---

**Status, 2026-09-16:** [PR #145](https://github.com/pgsty/silo/pull/145) added single-object conditional deletion; [PR #178](https://github.com/pgsty/silo/pull/178) subsequently repaired multi-pool serialization and reconciliation. Neither change is in published Server 20260903. Check the [component matrix](/compatibility/versions/) before relying on this behavior.

The August proposal around [PR #12](https://github.com/pgsty/silo/pull/12) was broader than the code that merged. In particular, its proposed batch rejection, extra read authorization and current-version-only rule are **not implemented guarantees**. This page describes the maintained source at [`f99ed829b`](https://github.com/pgsty/silo/tree/f99ed829b5eba549160725f035156c9e020b6a07).

## Implemented contract {#tldr}

| Request | Current main behavior |
| --- | --- |
| Single `DeleteObject`, nonempty `If-Match: <ETag>` | Check the client-visible ETag under the deletion lock; mismatch returns 412 before deletion |
| `If-Match: *` | Require an existing, non-delete-marker representation |
| Explicit `versionId` | Evaluate the **addressed version**, not an unrelated current version |
| No `If-Match`, or an empty header value | No conditional callback is installed; ordinary deletion applies |
| Batch `DeleteObjects` with per-item `<ETag>` | The request model has no ETag field; the XML field supplies **no deletion protection** |
| Internal recursive `x-minio-force-delete` | Prefix deletion returns before the object-condition path; do not use it as conditional deletion |

These conditions do not add an `s3:GetObject` authorization check. Ordinary deletion authorization still applies, including `s3:DeleteObjectVersion` for an explicitly addressed version, Object Lock checks and the separate trusted-replication path.

## Why the condition belongs above individual pools {#problem}

<a id="silent-downgrade"></a><a id="good-direction"></a><a id="atomicity-boundary"></a>

An object can have copies of different ages in more than one pool. A request condition concerns the logical object selected for the operation. Evaluating and mutating independently in each pool can delete one copy and then return 412 from another, or delete the latest copy and expose an older one.

The multi-pool path therefore acquires the shared namespace write lock, gathers the relevant states, evaluates the condition once, clears the callback for lower layers, and reconciles the selected deletion across pools. The same lock boundary must cover concurrent writes and metadata updates. This is the purpose of the later multi-pool repair, not a claim that every physical disk is atomically updated.

### Counterexamples from the early design {#two-pool-counterexamples}

<a id="partial-delete-on-412"></a><a id="stale-copy-after-success"></a>

With old ETag A in one pool and current ETag B in another:

- `If-Match: A` must not delete A first and only then fail against B.
- `If-Match: B` must not remove B while leaving A to become visible again.

A per-pool HTTP callback also risks concurrent writes to one response writer. Consume the request condition at the coordinating layer instead.

### Failure boundaries {#degraded-pool-limitation}

The reconciliation path reads pool state before evaluating the condition and surfaces failures instead of treating an unknown pool as empty. Cleanup errors can still follow a partial physical mutation: a failed request is not a distributed rollback guarantee. Retrying and checking actual state remain necessary after a storage failure. See [multi-pool consistency](/blog/design/multi-pool-object-consistency/).

## Selection and evaluation {#selected-fix}

### Evaluate once {#evaluate-once}

`erasureServerPools.DeleteObject` holds the outer lock. Multiple pools use `deleteObjectReconciled`; the single-pool path reads the selected representation and invokes `CheckPrecondFn` before its delete-marker shortcut. Lower layers do not reinterpret the condition per copy.

### Wildcards and delete markers {#wildcard}

<a id="delete-marker"></a>

The DELETE helper treats `*` as representation existence. A delete marker does not satisfy it. A missing key or addressed version follows the corresponding not-found path; it is not manufactured into an empty ETag match.

### Authorization {#permission}

The handler authorizes deletion using the effective version. It does **not** perform the additional `s3:GetObject` check described in the original proposal for a specific ETag. Do not treat the proposal's permission matrix as implemented AWS parity.

### SSE-C ETags {#encrypted-etag}

Conditional deletion compares the established client-visible ETag projection; it does not read or decrypt the object's payload. SSE-C read-key authentication is a separate contract from deleting an object.

### Explicit versions {#current-version}

An explicit `versionId` selects that version for comparison and deletion. A matching historical ETag can therefore allow deletion of the historical version even if the current version has another ETag. This differs from the early proposal's current-version-only rule.

### Unsupported edges {#fail-closed-edges}

An empty `If-Match` installs no condition. The recursive prefix-delete extension bypasses object preconditions. Batch XML ETags are not recognized by `ObjectToDelete`; there is no request-wide `NotImplemented` guard. Callers needing compare-and-delete must use the supported single-object path with a nonempty condition and verify their selected release.

## Alternatives and scope {#rejected}

<a id="reject-comparator"></a><a id="reject-per-pool"></a><a id="reject-framework"></a><a id="reject-scope-expansion"></a>

Changing a shared ETag comparator cannot fix pool selection or mutation ordering. Aggregating errors after per-pool callbacks cannot undo deletions already performed. A new transaction framework is unnecessary for consuming one callback at the existing namespace lock, but batch execution and policy enforcement require separate implementation.

## Evidence and release boundary {#tests}

<a id="adversarial-review"></a><a id="merge-gates"></a>

The source evidence is the [handler](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go), [pool coordinator](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go), and [batch request model](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/api-datatypes.go). Relevant coverage includes ETag mismatch, wildcard/delete markers, explicit versions, quorum failures and multiple pools. Earlier local review or test claims for a different implementation do not establish these missing guards. A merged implementation and a released, deployed binary remain separate facts.

## Follow-up work {#follow-up}

### Batch conditions {#delete-objects}

Implementing per-item ETags requires parsing them, evaluating each logical object under the correct lock, preserving quiet mode and reporting each failed condition in the per-item response. Until then, a batch ETag is ignored and must not be used as a concurrency guard.

### Policy enforcement {#policy-key}

The maintained policy package does not define `s3:if-match`. Supporting it requires a package change and release, correct request condition values, a Server dependency update and authorization tests. Existing `If-Match` execution does not by itself provide policy enforcement.

## Design cost {#tradeoff}

<a id="conclusion"></a>

Single-object execution reuses the established object-selection and locking boundary. Full batch conditions and policy enforcement cross additional interfaces and remain separate work. The useful invariant is narrow: a false supported single-object condition must be decided before deletion, once for the selected logical representation.
