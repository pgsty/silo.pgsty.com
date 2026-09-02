---
title: "Conditional DELETE: Why the Condition Must Be Evaluated Once"
linkTitle: "Conditional DELETE"
date: 2026-08-26
lastmod: 2026-09-02
author: "Ruohang Feng"
summary: >
  SILO PR #12 attempted to add If-Match to DeleteObject, but evaluated the condition independently in every storage pool, allowing a 412 response after a partial deletion or a stale copy to reappear after success. This record documents the defect, AWS contract, counterexamples, minimal repair, test requirements, and follow-up boundary for batch conditions and policy enforcement.
tags: [Design, S3, Compatibility, DELETE]
weight: 10
draft: false
url: "/blog/design/conditional-delete/"
---

This document records the analysis, design discussion, and repair decision for [SILO PR #12](https://github.com/pgsty/silo/pull/12).

> **Status on 2026-08-26:** PR #12 remains open at head `5b71a75e`, 118 commits behind the latest `main`. Its commit has no DCO sign-off and GitHub reports no check runs. The improved design described here has been implemented, tested, and reviewed twice in an isolated local worktree, and committed on the local branch `codex/pr12-conditional-delete`; it has not been pushed, merged, or released.<br>
> **Scope:** correctly support `If-Match` for the single-object `DeleteObject` API, and fail closed instead of silently deleting when an unsupported per-object `DeleteObjects` ETag is received. Full batch-condition execution and bucket-policy enforcement remain separate deliverables.<br>
> **Release boundary:** local implementation, tests, review, commit, push, remote CI, merge, tag, image publication, and production deployment are independent gates.

## Too Long; Didn't Read (TL;DR) {#tldr}

The underlying problem is real. SILO currently ignores `If-Match` on DELETE, so a client can believe it is performing compare-and-delete while the server performs an unconditional deletion. PR #12 targets the right problem and correctly recognizes that the condition must be evaluated against fresh object state while holding a lock.

The original implementation puts the same HTTP callback into every erasure pool. Different pools can retain copies from different points in time, so each pool evaluates and mutates against its own ETag. A two-pool test reproduced both failures:

- the request ultimately returns 412 after the older matching copy has already been deleted;
- the request succeeds after deleting the current copy, while an older non-matching copy remains and becomes visible again.

The selected repair introduces no new condition framework. It follows the established multi-pool GET pattern: select the current object under the outer namespace lock, evaluate the condition exactly once, then clear the callback before calling lower pools. A false condition mutates no pool. A true condition allows the existing cleanup to run without reinterpreting the client condition per copy.

## Why this is a real problem {#problem}

### Silently dropping the condition is unsafe {#silent-downgrade}

[AWS conditional-delete documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-deletes.html) now defines the behavior for general-purpose buckets and both `DeleteObject` and `DeleteObjects`:

| Request | Meaning | Result and permission |
| --- | --- | --- |
| `If-Match: <ETag>` | Delete only if the current object is still the state observed by the caller | 204 on match, 412 otherwise; requires `s3:GetObject` and `s3:DeleteObject` |
| `If-Match: *` | Delete only if a current object exists | 204 when it exists; requires only `s3:DeleteObject` |
| Missing key | No condition can be satisfied | Not Found |
| Current delete marker | No current object exists | `If-Match: *` returns 412 |

Ignoring the header is therefore not a harmless unsupported extension. It removes the concurrency guard the caller used to avoid deleting another writer's newer object.

Not every S3 client sends conditional deletes, so prevalence is unknown. Severity for each relying caller is high: one silent downgrade can remove newly committed data.

### A delete marker is not merely an ETag comparison case {#delete-marker}

PR #12 reuses the generic `isETagEqual`, which returns true whenever the right-hand value is `*`. Consequently, `isETagEqual("", "*")` is also true.

The more fundamental bypass occurs one layer above. `erasureServerPools.DeleteObject` returns success immediately when the current object is already a delete marker. That happens before the callback added by the PR. A diagnostic test observed zero callback calls and a successful result.

The impact needs precise wording:

- the delete-marker fast path did not remove a historical version or create another marker in the reproduced case; it bypassed the condition and falsely reported success;
- the multi-pool counterexamples do mutate storage on a failed request or leave a stale copy after success.

Changing only `isETagEqual("", "*")` cannot cross the outer fast path and risks altering a comparator shared by GET, PUT, and COPY.

## What the original PR got right {#good-direction}

Its high-level algorithm is sound:

1. detect `If-Match` in the handler;
2. read fresh `ObjectInfo` after acquiring the storage lock;
3. return before mutation when the condition is false;
4. encode the result as an S3 response.

This avoids the obvious TOCTOU window of a separate HEAD followed by DELETE. The PR also adds handler, helper, and erasure-layer tests. Its ordinary single-pool path correctly returns 412 and preserves the object for a wrong specific ETag.

The defect is not the decision to evaluate under a lock. It is choosing the wrong layer and therefore the wrong object state.

## Where the atomicity boundary lives {#atomicity-boundary}

The deletion path has two layers:

```text
DeleteObjectHandler
    -> erasureServerPools.DeleteObject
         holds the namespace write lock
         selects the latest current pinfo across pools
         handles the delete-marker fast path
         selects a single-pool or all-pool deletion
             -> erasureSets / erasureObjects.DeleteObject
```

Only `erasureServerPools.DeleteObject` knows:

- which copy represents the current object;
- which pools still contain older copies or inconsistent metadata;
- whether the delete-marker fast path applies;
- whether multiple pools will be mutated concurrently.

The client condition therefore belongs at this layer. A single pool knows only its local copy and cannot reinterpret a condition on the logical current object.

## Two-pool counterexamples {#two-pool-counterexamples}

The test places an older object in pool 0 and a newer object with a different ETag in pool 1. Reads select pool 1 as current, while an unversioned delete cleans both pools.

### Condition matches the old copy {#matches-old}

The original PR lets pool 0 pass and delete its copy while pool 1 fails. The aggregate result follows the current pool and returns 412, even though storage changed.

### Condition matches the current copy {#matches-current}

Pool 1 passes and deletes the current copy. Pool 0 fails and retains the old copy. The request returns success, after which the old object becomes visible again.

The callback also captures a single `http.ResponseWriter`. Calling it concurrently from multiple pools can make multiple goroutines write the same HTTP response. Storage replicas should not concurrently decide wire-level output.

### A pre-existing degraded-pool limitation {#degraded-pool-limitation}

There is one related but inherited limitation outside this patch. If the selected current pool is readable and writable but an older, non-current pool is degraded, the existing all-pool delete path can return the selected pool's success while an error from the older pool is not surfaced. That copy can remain and reappear after recovery.

The new condition does not create this behavior: it evaluates the readable current object correctly and then enters the same unversioned multi-pool cleanup used by an unconditional delete. Repairing error aggregation and recovery for partially degraded old pools should be tracked separately because it changes the guarantees of every unversioned multi-pool delete, not only conditional requests.

## The selected minimal repair {#selected-fix}

### 1. Evaluate exactly once at the outer layer {#evaluate-once}

After `erasureServerPools.DeleteObject` acquires the namespace write lock:

1. save `opts.CheckPrecondFn`;
2. remove it from options passed to lower layers;
3. inspect all pools and select the current `pinfo`;
4. if the current object cannot be read reliably, return a quorum error without calling the callback;
5. call the saved callback exactly once with `pinfo.ObjInfo`;
6. on success, continue through the existing deletion path with no lower-layer reinterpretation.

This pattern already exists in multi-pool `GetObjectNInfo`: save the callback, clear it below, select the latest object, and evaluate once. Reusing it limits the DELETE change to the real atomicity boundary.

### 2. Treat `*` as current-representation existence {#wildcard}

The DELETE-specific check separates wildcard and ETag semantics:

```text
specific ETag -> compare the client-visible ETag of the current object
*             -> require a non-empty object name and no delete marker
```

A missing key already returns Not Found during object selection. A current delete marker reaches the callback and returns 412. The generic `isETagEqual` remains unchanged.

### 3. Require read permission for a specific ETag {#permission}

The handler first checks `s3:DeleteObject`. When the normalized condition is not a bare `*`, it additionally checks `s3:GetObject`:

- delete-only policy plus `*`: allowed;
- delete-only policy plus a specific ETag: 403 and no mutation;
- Get plus Delete and a matching ETag: allowed.

Authorization completes before any storage mutation.

### 4. Do not require SSE-C content decryption for DELETE {#encrypted-etag}

The original PR invokes the GET/PUT-oriented `DecryptObjectInfo`, which rejects an SSE-C object when SSE-C read headers are absent. Conditional DELETE needs the client-visible ETag, not plaintext content or decrypted size.

The selected implementation uses the established `getDecryptedETag` projection only for a specific ETag. Wildcard requests do not read the ETag. This reuses existing ETag behavior without imposing content-decryption requirements on DELETE.

### 5. Evaluate the current version {#current-version}

AWS specifies that conditional-delete evaluation applies to the current version. SILO's outer pool selection already reads the current object, while preserving an explicit `versionId` for the eventual version deletion.

A regression test requests deletion of a historical version while matching that historical ETag rather than the current ETag. It must return 412 and preserve both versions.

### 6. Reject silent downgrades at unsupported edges {#fail-closed-edges}

Two small guards keep the single-object feature from being bypassed:

- an empty or whitespace-only `If-Match` is rejected instead of becoming an unconditional delete;
- `If-Match` cannot be combined with the internal recursive `x-minio-force-delete` extension, whose prefix semantics cannot represent one object's ETag condition; the HTTP handler rejects it and the storage layer also refuses any internal prefix-delete plus callback combination.

The batch XML decoder now also recognizes per-object `<ETag>` values. Until atomic per-item execution is implemented, any non-empty batch ETag rejects the entire request with `NotImplemented` before deletion begins. This is not batch conditional-delete support; it is a narrow data-safety guard against silently discarding a condition.

## Rejected alternatives {#rejected}

### Change only `isETagEqual` {#reject-comparator}

It does not address the outer delete-marker fast path and risks changing several APIs that share the comparator.

### Keep per-pool callbacks and aggregate the result {#reject-per-pool}

An aggregate error cannot roll back a copy already deleted by another pool. The condition applies to the logical current object, not independently to every physical copy.

### Introduce a new condition object or transaction coordinator {#reject-framework}

The current feature has one `If-Match` condition, and `CheckPrecondFn` already expresses it. GET demonstrates the correct one-shot consumption pattern. A new DSL, state machine, or cross-pool transaction abstraction is unnecessary.

### Complete every conditional-delete feature in one PR {#reject-scope-expansion}

`DeleteObjects` and policy conditions cross different API and repository boundaries. Combining XML parsing, per-item responses, IAM, quiet mode, and dependency publication with the core deletion repair would make the change harder to validate.

## Test and acceptance contract {#tests}

The minimally sufficient matrix is:

| Layer | Evidence |
| --- | --- |
| Condition helper | matching, mismatching, quoted ETag, wildcard, delete marker, non-DELETE method, and SSE-C client-visible ETag projection without content-decryption headers |
| Handler | wrong ETag returns 412 and preserves the object; matching ETag returns 204; missing key returns Not Found; blank conditions and conditional force-delete are rejected without mutation |
| Permission | delete-only plus specific ETag returns 403 and preserves the object; the same policy plus `*` succeeds |
| Single-pool storage | matching/mismatching condition, missing object, delete marker, one callback call, and refusal of a conditional prefix delete |
| Quorum | unreadable current object returns a quorum error, calls the callback zero times, and remains after disks recover |
| Versioning | a historical `versionId` condition still evaluates the current version |
| Two pools | 412 changes no pool; 204 removes all copies; one callback call in both cases |
| Batch safety guard | an unsupported per-object `<ETag>` returns `NotImplemented` and preserves every object |

The original PR's quorum test merely took 8 of 16 disks offline and asserted that some error occurred. Delete write quorum was already unavailable, so the same test passed on main without conditional DELETE. The replacement asserts the specific quorum result, zero callback calls, and object survival after restoring the disks.

## Independent adversarial review {#adversarial-review}

Two read-only local Claude Code reviews used the Fable model at `xhigh` effort against the exact server diff and both design records. Both verdicts were **GO WITH NON-BLOCKING NOTES**, with no P0, P1, or P2 findings after the first round's changes were applied.

The first review found the conditional force-delete bypass, whitespace-only downgrade, silent batch-ETag discard, missing versioned-success coverage, and the inherited degraded-old-pool limitation. Those findings produced the guards, tests, and limitation text above. The second review confirmed the outer atomicity boundary, error handling, auth split, batch-field blast radius, response-writer behavior, bilingual parity, and minimality. Its remaining actionable P3 was a hypothetical internal caller combining prefix deletion with a callback; the storage layer now rejects that combination too.

One reviewer sentence suggested that SSE-C without customer-key headers would necessarily fail the condition. Direct inspection showed the opposite established behavior: `getDecryptedETag` projects the stored client-visible suffix without asking to decrypt object contents. A focused regression test now pins that behavior. Remaining non-blocking notes are multiple-header normalization and the deliberate 501-before-auth error-ordering nuance. A live-AWS differential check for specific ETag versus a current delete marker and `versionId` plus `If-Match` would still be useful before claiming byte-for-byte behavioral parity beyond the published contract.

## Deliberate follow-up scope {#follow-up}

### Per-object conditions in `DeleteObjects` {#delete-objects}

The [AWS DeleteObjects API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html) accepts an `<ETag>` per `<Object>` and returns each outcome under `<Deleted>` or `<Error>` in the same 200 response.

The safety patch adds an ETag field to `ObjectToDelete` only so the handler can detect the condition and reject the entire request before mutation. This closes the previous silent unconditional-delete behavior, but it does **not** implement AWS's required per-object evaluation or mixed `<Deleted>` / `<Error>` response.

Full compatibility remains a separate high-priority change: evaluate every item against the logical current object under the correct lock, apply the exact-ETag permission rule per item, preserve quiet-mode behavior, and report each failed condition without blocking unrelated items.

### The `s3:if-match` policy condition key {#policy-key}

[AWS policies can enforce conditional deletes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-delete-enforce.html). SILO's `silo-pkg` does not yet define `s3:if-match`. Full support requires:

1. the condition key and action map in `silo-pkg`;
2. a new `silo-pkg` release;
3. correct condition values for a single-delete header and batch per-item ETags;
4. a server dependency update and policy compatibility tests.

That is a separate cross-repository deliverable, not a prerequisite for making single-object execution correct.

## Complexity, benefit, and cost {#tradeoff}

Production code remains small: one DELETE-specific condition helper, one extra authorization check, roughly a dozen lines that consume the callback once at the outer layer, and narrow fail-closed guards for malformed/recursive and as-yet unsupported batch conditions. Most complexity belongs in tests because deletion spans pools, versions, markers, quorum, and permissions.

| Scope | Complexity | Main cost |
| --- | --- | --- |
| This single-object repair plus batch safety guard | Medium | Regression coverage across the destructive hot path |
| Batch conditional delete | Medium-high | XML, per-item conditions, mixed responses, quiet mode |
| Policy condition key | Medium and cross-repository | `silo-pkg` release, server condition values, policy tests |

The benefit exceeds the cost. It removes a dangerous silent unconditional delete and places the condition at an existing global consistency boundary. Reusing the current outer-lock/latest-object pattern is the minimal, sufficient, and necessary design.

## Merge and release gates {#merge-gates}

The single-object repair becomes mergeable only after:

1. targeted condition, permission, versioning, quorum, and two-pool tests pass;
2. `go test ./cmd`, `go vet ./cmd`, formatting, and diff checks pass;
3. an independent adversarial review has no unresolved blocker;
4. the contribution is organized on current `main` with a valid author DCO sign-off;
5. DCO, Go CI, VulnCheck, and other required remote workflows are green;
6. the PR description distinguishes complete `DeleteObject` support from the batch fail-closed guard and links the full batch/policy follow-ups.

A merge is still not a release. Users can rely on the behavior only after a corresponding SILO release, package, `docker.io/pgsty/silo` image, deployment, and real-client verification have independently completed.

## Conclusion {#conclusion}

Conditional DELETE is worth implementing. PR #12 has the right goal and the useful insight that fresh state must be checked under a lock. The required correction is the boundary: a client condition belongs to the logical current object and cannot be interpreted independently by every physical copy.

The selected design moves one callback to the `erasureServerPools` layer that already selects the current object, preserves the generic comparator, handles wildcard/delete-marker semantics explicitly, and adds the specific-ETag read permission. It changes no storage format, dependency, or public condition framework. The batch change is deliberately limited to refusing an unsupported condition before mutation; full batch execution and policy support remain separate work.

That is the minimum complexity needed to make the feature sufficient and safe.
