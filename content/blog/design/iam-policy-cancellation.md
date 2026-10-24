---
title: "IAM Policy Reloads: Lock Scope, Cancellation, and Time Budgets"
linkTitle: "IAM Reloads & Cancellation"
date: 2026-10-23
lastmod: 2026-10-23
author: "Ruohang Feng"
summary: "Why a slow policy list blocked ordinary S3 authentication, how request cancellation was lost before reaching KES, and why fixing context propagation required separating etcd read timeouts from decryption budgets."
tags: [Design, IAM, KMS, S3, Review]
weight: 8
draft: false
url: "/blog/design/iam-policy-cancellation/"
---

Commit [`1b5477f3d`](https://github.com/pgsty/silo/commit/1b5477f3df87924712ad8dc580c8f8eac63eda2d) ([`pgsty/silo#251`](https://github.com/pgsty/silo/issues/251)) resolves two coupled failure modes under slow KMS/KES responses:

1. **Authentication-cache lock contention**: `ListPolicies` and `ListPolicyDocs` now load and decrypt policy replacements outside the in-memory authentication-cache lock while retaining IAM write serialization (`writeMu`).
2. **End-to-end request cancellation**: IAM configuration decryption and SSE-S3 list key unsealing now propagate the caller's request context all the way to outbound `KES.Decrypt` calls, while keeping backend RPC timeouts scoped strictly to their storage operations rather than truncating legitimate long-running queries at 30 seconds.

## Two Symptoms, Two Mechanisms {#symptoms}

During incident investigation of [`pgsty/silo#251`](https://github.com/pgsty/silo/issues/251), controlled reproduction isolated two distinct server behaviors when KES responses are slow:

1. When an administrator lists IAM policies while KES is slow, the policy listing takes several seconds, and ordinary users' unrelated `GET`, `HEAD`, and `PUT` object requests stall behind it.
2. When a client abandons an SSE-S3 object listing (`ListObjects` with encrypted metadata), the server continues sending `Decrypt` requests to KES for subsequent objects that the disconnected client will never receive.

| Observation | Root-Cause Mechanism | Fix Component |
| :--- | :--- | :--- |
| Ordinary S3 `GET`, `HEAD`, or `PUT` requests stall behind a slow policy list | `ListPolicies` / `ListPolicyDocs` hold the in-memory authentication-cache write lock while reading and decrypting every stored policy document | **A**: Move slow backend loading and decryption outside the authentication-cache lock |
| KMS/KES decryption continues after the HTTP client cancels the request | Intermediate helpers substitute `context.Background()`, severing cancellation propagation before the outbound KES request | **B**: Thread the caller's `context.Context` through the entire decryption call chain |
| A legitimate slow policy query (> 30 s) fails with HTTP 503 in the first repair candidate | Reusing `withIAMStorage` and reusing etcd's 30-second `Get` child context inadvertently imposed a 30-second ceiling on total decryption work | **R1**: Scope each timeout strictly to the storage operation it originally bounded |

Shrinkage of the lock scope (**A**) and cancellation propagation (**B**) solve complementary problems: releasing the cache lock keeps healthy S3 traffic flowing during a slow admin query, while context propagation stops wasted KMS calls after a client disconnects.

## How the Coupling Arose {#cause}

`ListPolicies` and `ListPolicyDocs` reload persisted policies from the backing store and replace the in-memory policy map. In the original implementation, `store.lock()` (the write lock on `IAMCache`) remained held from the start of the backend scan until every policy document was read and decrypted. On the object-storage IAM backend, each KMS-encrypted policy document requires a separate KES decryption call. Because every ordinary S3 request acquires the read lock on the same `IAMCache` to authenticate the caller and evaluate permissions, multi-second KES latency during an admin policy listing directly blocked data-plane S3 requests.

Separately, the request cancellation chain was broken at three layers:

1. IAM configuration decryption invoked KMS with a background context unrelated to the incoming HTTP request.
2. SSE-S3 object listing (`UnsealObjectKeys`) called a single-object helper (`UnsealObjectKey`) that did not accept a `context.Context`.
3. The KES client adapter invoked `Decrypt` with `context.Background()`.

Because the lowest layer replaced the context with `context.Background()`, passing a request context into a top-level handler had no effect on outbound KES traffic.

## A: Release the Cache Lock, Retain Write Ordering {#cache}

The IAM subsystem uses two locks with distinct responsibilities:

- **The cache lock (`store.lock()` / `store.rlock()`)**: protects the in-memory maps read by S3 authentication on every request.
- **The IAM write mutex (`writeMu`)**: serializes administrative IAM mutations and full cache replacements so concurrent updates cannot interleave.

With fix **A**, policy reloading keeps `writeMu` held to preserve mutation ordering, but releases the cache lock while performing slow storage I/O and KMS decryption:

```text
Acquire IAM write serialization (writeMu) and the cache lock (store.lock)
  Release only the cache lock
  Load and decrypt policies into a private map using the caller's context
  Reacquire the cache lock
  Check the load result and caller context cancellation again
  On success, merge built-in policies and publish the complete replacement map
Release the cache lock and IAM write serialization (writeMu)
```

While the private map is being populated and decrypted, ordinary S3 requests continue reading the existing committed cache without waiting on KES. Concurrent IAM administrative writes still wait on `writeMu`. Releasing both locks during loading was rejected because a slow policy reload that started before an IAM policy update or deletion could finish afterward and overwrite the newer state with a stale snapshot.

The new policy map is published only if the backend load succeeds and `ctx.Err()` is still `nil` *after* reacquiring the cache lock. Checking for cancellation only before reacquiring the lock would miss a cancellation that occurred while waiting for the lock. If any backend error, partial load, or cancellation occurs prior to publication, both the existing in-memory policy map and its `updatedAt` timestamp remain untouched.

Background IAM refresh follows the same merge and revocation invariants. Regression tests exercise the concrete `IAMObjectStore` refresh path directly alongside concurrent policy updates, deletions, and [durable IAM revocations](/blog/design/iam-revocations/).

## B: Propagate Cancellation to KMS and KES {#cancellation}

Both affected decryption chains now thread the caller's `context.Context` end-to-end into the KMS and KES layers:

```text
IAM / configuration request
  -> object or etcd configuration decoder
  -> configuration decryption (with request ctx)
  -> KMS.Decrypt(ctx, ...) -> KES.Decrypt(ctx, ...)

SSE-S3 list request
  -> UnsealObjectKeys(ctx, ...)
  -> context-aware single-key helper
  -> KMS.Decrypt(ctx, ...) -> KES.Decrypt(ctx, ...)
```

To avoid churning unrelated call sites that do not carry a request context, the existing single-object `UnsealObjectKey` function keeps its original signature, while `UnsealObjectKeys` calls an internal context-aware helper.

Cancellation is checked at each loop iteration, before fallback branches, and before cache publication. In particular, when an IAM decryption call fails due to context cancellation, the loader immediately aborts rather than triggering the legacy associated-data (AAD) compatibility fallback. For active (non-canceled) requests, the legacy AAD fallback, ciphertext format handling, key ordering, and non-cancellation KES error mappings remain unchanged.

## R1: Keep Timeouts Scoped to Their Original Operations {#budgets}

The first candidate implementation of **A** and **B** reused `withIAMStorage` to release the cache lock around slow backend work. `withIAMStorage` was introduced in the September 15 revocation-persistence commit ([`709d50a916`](https://github.com/pgsty/silo/commit/709d50a916bf3311eda2b3882ac5f2a0251f4223)) to bound single-record storage I/O, distributed lock acquisition, and cleanup to 30 seconds. Reusing that helper for full policy listing inadvertently attached a 30-second total deadline to an operation that previously had no whole-query time limit.

Adversarial testing exposed the regression immediately:

- On the baseline server, a slow policy query across 61 encrypted policies completed in **32.74 seconds** with `HTTP 200`.
- On the first repair candidate, the same query failed after **31.22 seconds** with `HTTP 503` because the 30-second `withIAMStorage` deadline expired before all policies finished decrypting.

Simply removing the outer `withIAMStorage` wrapper was still not sufficient for the `etcd` backend. In the `etcd` IAM store, `Get` operations create a 30-second child context to bound the `etcd` RPC. Previously, post-read KMS decryption ignored the context parameter altogether; once fix **B** wired context propagation through decryption, passing the `etcd` read child context into decryption caused the 30-second `etcd` RPC deadline to govern subsequent KMS decryption as well. A fast `etcd` read followed by 32 seconds of KES decryption therefore failed with a deadline error.

Correction **R1** separates the caller's request budget from individual `etcd` RPC budgets across both policy documents and policy mappings:

| Time Budget | Scope and Behavior |
| :--- | :--- |
| **Caller deadline or cancellation** | Governs the entire HTTP request and all associated KMS/KES decryption calls |
| **Existing `etcd` read budget (30 s)** | Bounds only the `etcd` `Get` RPC; post-read decryption switches back to the caller's parent request context |
| **Existing revision-write, revocation, lock, and cleanup budgets** | Retain `withIAMStorage` and their existing bounded timeouts |
| **Whole-policy-list 30 s timeout (from first candidate)** | Removed from both `ListPolicies` and `ListPolicyDocs` |

Because the `etcd` read context is derived as a child of the caller's request context, a shorter caller deadline still preempts `etcd` reads immediately. Once the `etcd` read succeeds, decryption proceeds under the caller's remaining time budget—allowing legitimate slow queries beyond 30 seconds to succeed when the caller permits.

## Alternatives Considered {#alternatives}

| Candidate Approach | Why It Was Rejected |
| :--- | :--- |
| **Keep the cache lock held and shorten the list timeout** | Healthy S3 requests still stall until the timeout expires, and legitimate slow policy queries fail |
| **Release both `writeMu` and the cache lock during loading** | A slow list can finish after a concurrent IAM write and overwrite newer state with a stale snapshot |
| **Return cached policies without reloading from storage** | Breaks the freshness contract of administrative policy listing and masks backend issues |
| **Raise the whole-list timeout to a larger fixed constant** | Merely shifts the regression threshold to a larger policy count or higher KES latency |
| **Remove only the outer `withIAMStorage` timeout** | Leaves the `etcd` post-read decryption deadline regression intact |
| **Remove all backend storage timeouts** | Weakens existing bounds on single-record reads, writes, distributed lock acquisition, and cleanup |
| **Parallelize policy decryptions or add a second ciphertext cache** | Introduces new KES concurrency spikes and cache invalidation complexity not required to fix the lock and cancellation bugs |
| **Rewrite KES SDK internal retry behavior** | Expands the blast radius into third-party SDK semantics |

Relative to baseline [`a07d655dc`](https://github.com/pgsty/silo/commit/a07d655dc69cf04b130c2634d9fa5301078af546), the final implementation touches 8 production files (`+83 / -29` lines) and 5 test files, with no wire-protocol, ciphertext-format, or permission-model changes.

## Verification and Regression Benchmarks {#verification}

Process-level benchmarks against baseline [`a07d655dc`](https://github.com/pgsty/silo/commit/a07d655dc69cf04b130c2634d9fa5301078af546) and final commit [`1b5477f3d`](https://github.com/pgsty/silo/commit/1b5477f3df87924712ad8dc580c8f8eac63eda2d) demonstrate the exact behavioral shift:

| Scenario | Before / First Candidate | Final Implementation (`1b5477f3d`) |
| :--- | :--- | :--- |
| 4 ordinary S3 object requests during a 5.23 s policy list | Mean **5,284 ms** (blocked behind policy list) | Mean **2.25 ms** (policy list still takes 5.23 s in parallel) |
| Same 4 ordinary S3 requests with a 200 ms client timeout | All 4 time out | All 4 return `200 OK` in **1.11–1.82 ms** |
| SSE-S3 object list abandoned by client at 200 ms | **21** additional KES decryptions start after client exit | **0** additional decryptions start after exit (4 total before cancel) |
| Object-backed policy query taking > 30 s (61 policies) | Baseline: `200 OK` in 32.74 s; First candidate: `503` at 31.22 s | `200 OK` in **32.75 s** with all 61 policies returned |
| Fast `etcd` read + 32 s KES decryption (60 s caller budget) | First candidate fails during post-read decryption | Both policy-list entry points and policy-mapping loader succeed |
| 51 normal and denied HTTP control cases | Baseline status codes, error codes, and item counts | All 51 controls match (including pagination, KMS denial, and SigV4 checks) |

During test construction, two subtleties in the KES client surfaced:

1. **Non-cancelable SDK retry sleeps**: The KES SDK can perform up to two backoff sleeps of up to `999 ms` that do not select on `ctx.Done()`. A 2-second test window was too tight to cover a `300 ms` request deadline plus two backoff sleeps; widening the post-cancel observation window to 3 seconds confirmed that no new outbound decryptions are initiated after cancellation.
2. **Periodic `DescribeKey` health probes**: Running a real 32-second test required the mock KES fixture to answer periodic background `DescribeKey` requests alongside `Decrypt`.

Regression tests are committed in:
- [`cmd/iam-policy-reload_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-reload_test.go)
- [`cmd/iam-policy-refresh_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-refresh_test.go)
- [`cmd/iam-policy-budget_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-budget_test.go)
- [`cmd/kms-cancellation_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/kms-cancellation_test.go)

## Operational Boundaries {#limits}

- **Concurrent IAM admin writes**: Because `writeMu` remains held during a policy reload to preserve write serialization, administrative IAM mutations (such as creating or deleting a policy) still wait for an in-progress policy reload to finish or be canceled. Ordinary S3 authentication does not wait on `writeMu`.
- **KES SDK backoff return latency**: Cancellation immediately aborts in-flight HTTP requests to KES and prevents subsequent keys or AAD fallback branches from starting, but if the KES SDK is mid-backoff sleep (`<= 999 ms`), the local Go function returns once that sleep finishes.

### Engineering Takeaways {#lessons}

1. **Audit every side effect of a reused helper**: Reusing `withIAMStorage` for its lock-release behavior silently imported a 30-second timeout into an operation that previously had no total-duration cap.
2. **Trace context deadlines across layer boundaries**: Wiring context propagation into previously context-free helpers can activate child deadlines (such as `etcd` RPC timeouts) that were previously ignored by downstream calls.
3. **Pair cancellation tests with slow-success tests**: Verifying that canceled requests stop early must be paired with verifying that uncanceled slow requests beyond 30 seconds still succeed.

Related design records:
- [Durable IAM Revocations](/blog/design/iam-revocations/)
- [Request-Header Deadlines](/blog/design/request-header-timeouts/)
- [KES & OpenBao Integration](/blog/design/kes-openbao/)
