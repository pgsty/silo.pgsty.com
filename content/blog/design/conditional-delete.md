---
title: "Conditional DELETE: One Condition, One Logical Object"
linkTitle: "Conditional DELETE"
date: 2026-08-26
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Single-object If-Match DELETE evaluates the addressed version once under the outer multi-pool lock before mutating storage. Batch DeleteObjects ETags, extra GetObject checks, and recursive prefix guards remain outside this contract.
tags: [Design, S3, Compatibility, DELETE]
weight: 10
draft: false
url: "/blog/design/conditional-delete/"
---

Single-object conditional deletion (`If-Match` on `DeleteObject`) landed in [PR #145](https://github.com/pgsty/silo/pull/145), and [PR #178](https://github.com/pgsty/silo/pull/178) repaired multi-pool serialization and reconciliation. Both changes shipped in [Server 20260916](/blog/release/silo-20260916/).

An earlier August proposal around [PR #12](https://github.com/pgsty/silo/pull/12) sketched a broader scope—including batch `DeleteObjects` rejection, an extra `s3:GetObject` authorization check, and a current-version-only rule—that was not adopted in the merged implementation. This note documents the shipped behavior in [`f99ed829b`](https://github.com/pgsty/silo/tree/f99ed829b5eba549160725f035156c9e020b6a07) and why precondition evaluation must sit above individual storage pools.

## Implemented Contract {#tldr}

| Request | Shipped Behavior |
| --- | --- |
| Single `DeleteObject`, non-empty `If-Match: <ETag>` | Evaluates the client-visible ETag under the outer deletion lock; mismatch returns `412 PreconditionFailed` before any deletion |
| `If-Match: *` | Requires an existing, non-delete-marker representation |
| Explicit `versionId` | Evaluates the **addressed version**, not an unrelated current version |
| No `If-Match`, or an empty header value | Installs no conditional callback; ordinary deletion applies |
| Batch `DeleteObjects` with per-item `<ETag>` | `ObjectToDelete` has no ETag field; the XML element supplies **no deletion protection** |
| Internal recursive `x-minio-force-delete` | Prefix deletion returns before the object-condition path; do not use it as conditional deletion |

These preconditions do not add an `s3:GetObject` authorization check. Ordinary deletion authorization applies—including `s3:DeleteObjectVersion` for an explicitly addressed version, Object Lock checks, and the separate trusted-replication path.

## Why the Condition Belongs Above Individual Pools {#problem}

In a multi-pool deployment, an object can have copies of different ages in more than one pool. A request precondition applies to the single logical object selected for the operation. Evaluating and mutating independently inside each pool can delete one copy and then return `412 PreconditionFailed` from another, or delete the newest copy and uncover a stale one.

The multi-pool coordinator (`erasureServerPools.DeleteObject`) therefore acquires the shared namespace write lock, gathers the relevant pool states, evaluates the condition once, clears the callback for lower layers, and reconciles the selected deletion across pools. The same lock boundary covers concurrent object writes and metadata updates.

### Counterexamples from the Early Design {#two-pool-counterexamples}

Suppose Pool 1 holds an older copy with ETag `A` and Pool 2 holds the current copy with ETag `B`:

- **`If-Match: A` (partial delete on `412`):** Per-pool evaluation deletes copy `A` in Pool 1 and only then fails with `412 PreconditionFailed` against `B` in Pool 2, mutating storage on a rejected request.
- **`If-Match: B` (stale copy exposure after `204`):** Per-pool evaluation deletes `B` in Pool 2 while failing or skipping Pool 1, leaving stale copy `A` visible as the current object.

Executing an HTTP precondition callback inside per-pool workers also risks concurrent writes to a single `http.ResponseWriter`. Consuming the request condition once at the coordinating layer eliminates both hazards.

### Failure Boundaries {#degraded-pool-limitation}

The reconciliation path reads pool state before evaluating the condition and surfaces read quorum failures instead of treating an unreachable pool as empty. Physical cleanup errors can still occur after a partial mutation: a failed request is not a distributed multi-pool rollback transaction. Retrying and verifying object state remain necessary after a storage failure; see [Multi-Pool Object Consistency](/blog/design/multi-pool-object-consistency/).

## Selection and Evaluation {#selected-fix}

### Evaluate Once {#evaluate-once}

`erasureServerPools.DeleteObject` holds the outer namespace lock. Multi-pool deployments call `deleteObjectReconciled`; single-pool deployments read the selected representation and invoke `CheckPrecondFn` before taking the delete-marker shortcut. Lower storage layers never reinterpret the precondition per copy.

### Wildcards and Delete Markers {#wildcard}

The `DELETE` precondition helper treats `If-Match: *` as requiring an active object representation. A delete marker does not satisfy `*`. A missing key or missing addressed version follows the normal not-found path and is never coerced into an empty-ETag match.

### Authorization {#permission}

The handler authorizes deletion against the effective target version (`s3:DeleteObject` or `s3:DeleteObjectVersion`). It does not require `s3:GetObject` when a specific ETag is supplied in `If-Match`.

### SSE-C ETags {#encrypted-etag}

Conditional deletion compares the established client-visible ETag projection stored in metadata; it does not read or decrypt the object payload. SSE-C read-key authentication remains separate from object deletion.

### Explicit Versions {#current-version}

Supplying an explicit `versionId` selects that exact version for both ETag comparison and deletion. A matching historical ETag allows deleting that historical version even when the current version has a different ETag.

### Fail-Closed and Unsupported Edges {#fail-closed-edges}

An empty `If-Match` header installs no precondition. The internal recursive prefix-delete extension (`x-minio-force-delete`) bypasses object preconditions. Batch XML `<ETag>` elements in `DeleteObjects` are not parsed by `ObjectToDelete`, and there is no request-wide `NotImplemented` rejection guard. Callers requiring compare-and-delete semantics must use single-object `DeleteObject` with a non-empty `If-Match` header.

## Rejected Alternatives and Scope {#rejected}

- **Modifying a shared ETag comparator:** Changing low-level string comparison cannot fix multi-pool winner selection or prevent mutations before a precondition check.
- **Aggregating errors after per-pool callbacks:** Returning `412` after one pool has already deleted its copy cannot undo the physical deletion.
- **Introducing a new distributed transaction framework:** Consuming one precondition callback under the existing outer namespace lock is sufficient for single-object `DeleteObject`; batch execution and policy keys require separate surface changes.

## Source Evidence {#tests}

The implementation lives in [`cmd/object-handlers.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go), [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go), and [`cmd/api-datatypes.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/api-datatypes.go), with regression tests covering ETag mismatches, wildcard and delete-marker handling, explicit `versionId` targeting, quorum failures, and multi-pool reconciliation.

## Follow-Up Work {#follow-up}

### Batch Conditions {#delete-objects}

Supporting per-item `<ETag>` preconditions in `DeleteObjects` requires unmarshaling the XML field, evaluating each logical object under its outer lock, honoring `Quiet` mode, and reporting per-item precondition failures in the XML result. Until that path is implemented, batch `<ETag>` elements are ignored and must not be used as a concurrency guard.

### Policy Enforcement {#policy-key}

The IAM policy package does not yet define the `s3:if-match` condition key. Supporting policy-enforced conditional deletes requires adding the condition key in `silo-pkg`, populating request condition values in the server handler, and adding policy evaluation tests.

## Design Trade-Off {#tradeoff}

Single-object conditional `DELETE` reuses the existing multi-pool object-selection and locking boundary without inventing a new transaction layer. Full batch preconditions and IAM policy condition keys cross additional API and package boundaries and remain separate work. The core invariant is strict: a false single-object `If-Match` precondition is decided once against the selected logical representation before any pool deletes data.
