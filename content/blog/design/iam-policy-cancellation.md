---
title: "IAM Policy Reloads: Lock Scope, Cancellation, and Time Budgets"
linkTitle: "IAM Reloads & Cancellation"
date: 2026-10-23
lastmod: 2026-10-23
author: "Ruohang Feng"
summary: "Why a slow policy list blocked ordinary authentication, how cancellation was lost before KES, and why the repair must preserve successful queries longer than 30 seconds."
tags: [Design, IAM, KMS, S3, Review]
weight: 8
draft: false
url: "/blog/design/iam-policy-cancellation/"
---

**Decision, 2026-10-23:** load policy replacements outside the authentication-cache
lock while retaining IAM write ordering; propagate request cancellation to actual
decryption; preserve the caller's time budget without adding a 30-second limit to
the entire query. The implementation is recorded in
[`1b5477f3d`](https://github.com/pgsty/silo/commit/1b5477f3df87924712ad8dc580c8f8eac63eda2d).
This is a source design and acceptance record, not a release announcement or proof
that a production deployment has been repaired.

The work followed [Server #251](https://github.com/pgsty/silo/issues/251).
Controlled reproduction separated two server mechanisms. It did not establish
that every reported Console symptom had the same cause.

## Two symptoms, two mechanisms {#symptoms}

An administrator lists policies while KES is slow. The policy request takes
several seconds, and ordinary users' unrelated object requests also stall.
Separately, a client abandons an SSE-S3 object listing, but the server continues
asking KES to decrypt keys for objects the client will never receive.

| Observation | Verified mechanism | Required change |
| --- | --- | --- |
| An ordinary user's GET, HEAD, or PUT waits behind a slow policy list | The list holds the authentication-cache write lock while loading and decrypting policy documents | A: move slow loading outside that cache lock |
| Decryption continues after a request is canceled | Intermediate layers substitute a background context, disconnecting the request from KES | B: carry the request context through the entire affected chain |
| A previously successful slow query fails around 30 seconds in the first repair candidate | Reused helpers and newly connected contexts impose the wrong time budget on a larger operation | R1: keep each deadline scoped to the operation it originally bounded |

The first two defects need separate repairs. Faster lock handling does not stop
abandoned work. Cancellation alone does not let healthy requests use the cache
while a slow but still valid policy query is running.

## How the coupling arose {#cause}

`ListPolicies` and `ListPolicyDocs` reload stored policies and replace the cached
policy map. Originally, `store.lock()` remained held throughout backend reads and
decryption. The object backend loads policy documents individually; encrypted
documents can require a KES call each. Authentication reads the same cache under
its read lock, so backend latency becomes unrelated request latency.

The cancellation chain had separate breaks. Configuration decryption called KMS
with a context unrelated to the request, SSE-S3 list decryption used a
context-free single-object helper, and the KES adapter invoked `Decrypt` with
`context.Background()`. Passing a context into a top-level function was therefore
not enough: the outbound operation did not inherit it.

These findings concern lock ownership and context propagation. They do not show
that policy parsing or the cryptographic algorithm itself needs replacement.

## A: release the cache lock, retain write ordering {#cache}

The two locks serve different purposes:

- The cache lock protects the in-memory data read by authentication.
- `writeMu` orders IAM writes and cache replacement. It remains held while the
  list prepares its replacement.

The final sequence is:

```text
Acquire IAM write serialization and the cache lock
  Release only the cache lock
  Load and decrypt policies into a private map using the caller's context
  Reacquire the cache lock
  Check the load result and cancellation again
  On success, add built-in policies and publish the complete replacement
Release the cache lock and IAM write serialization
```

Authentication can continue using the committed cache during loading. Other IAM
writes still wait their turn. Releasing both locks would allow a delayed list to
overwrite a newer update or deletion with an older snapshot. Avoiding that would
require a new version-validation or retry protocol, which this repair does not
need.

The replacement is published only after a successful load and the final context
check under the cache lock. A backend error, partial load, or cancellation
observed before publication leaves both the old policy map and its update time
unchanged. Checking only before reacquiring the lock would miss cancellation
while waiting for that lock. This is a cancellation boundary, not a promise of an
atomic global ordering between cancellation and every subsequent instruction.

Background refresh must also preserve its existing merge and revocation rules.
Tests exercise the actual `IAMObjectStore` refresh path, rather than relying only
on a wrapper that could bypass concrete-backend type checks. Successful and
canceled reloads run alongside updates, policy deletion, and scoped STS
revocation. The [durable revocation design](/blog/design/iam-revocations/) remains
the authority for persisted versions and replay protection.

## B: make cancellation reach the work {#cancellation}

The affected chains now retain the caller's context:

```text
IAM / configuration request
  -> object or etcd configuration decoder
  -> configuration decryption
  -> KMS.Decrypt -> KES.Decrypt

SSE-S3 list request
  -> UnsealObjectKeys
  -> context-aware single-key helper
  -> KMS.Decrypt -> KES.Decrypt
```

The existing single-object `UnsealObjectKey` entry point remains available with
its original signature. The list uses an internal context-aware helper, keeping
this change out of callers that have no request context to pass.

Cancellation is also checked at iteration and publication boundaries. In
particular, canceled IAM decryption must not launch the historical
associated-data fallback. That fallback remains available for old ciphertext
when the request is still valid; compatibility and cancellation are separate
decisions. The repair retains ciphertext formats, associated data, object-key
ordering, and the existing non-cancellation KES error mappings.

Cancellation cannot undo remote work that already completed. The acceptance
condition is that cancellation reaches the in-flight request, prevents subsequent
decryptions and fallback work, and returns the appropriate context error. It is
not a guarantee of zero elapsed time between cancellation and local return.

## R1: a timeout must retain its original scope {#budgets}

The first A/B candidate reused `withIAMStorage` to release the cache lock around
slow work. That helper also creates a timeout. It was introduced by the
September 15 revocation-persistence repair
[`709d50a916`](https://github.com/pgsty/silo/commit/709d50a916bf3311eda2b3882ac5f2a0251f4223),
where bounded storage work, lock waiting, and cleanup have a purpose. The mistake
was treating its lock behavior and timeout behavior as an inseparable contract
for a policy-list operation that previously had no such total-duration limit.

The adversarial counterexample was concrete: the original server completed a
slow policy query in 32.74 seconds with HTTP 200; the first candidate returned
503 after 31.22 seconds. The added deadline expired at 30 seconds, while unwind
and existing retry behavior could delay the response. The timeout was neither
necessary for A nor necessary for B.

Removing that outer limit was still insufficient for etcd. Its existing child
context bounded the `Get` RPC. Previously, decryption ignored that context;
connecting it during B made the same deadline apply to decryption after a
successful read. A fast `Get` followed by a 32-second decrypt then became a new
failure. Policy documents and policy mappings both needed the correct parent
context after the read.

| Budget | Final owner and behavior |
| --- | --- |
| Caller deadline or cancellation | Governs the whole request and its decryption work |
| Existing etcd read budget, normally 30 seconds | Bounds `Get`; it does not become an extra deadline for subsequent decryption |
| Existing revision-write, revocation, distributed-lock, and cleanup budgets | Keep their original helper and behavior |
| New whole-policy-list limit in the rejected candidate | Removed from both public policy-list entry points |

A shorter caller deadline still wins: the etcd read context is a child of the
request context. A completed etcd read does not grant the rest of the request an
unlimited lifetime; decryption continues under the caller's remaining budget.
Conversely, a caller that permits a longer query can still receive a successful
result after 30 seconds.

The general lesson is that fixing context propagation can change behavior even
when the timeout constant is untouched. Review the meaning of every context
along the path, including contexts whose deadlines were previously ignored.

## Alternatives and why they were rejected {#alternatives}

| Alternative | Reason for rejection |
| --- | --- |
| Keep the cache lock and shorten the list timeout | Healthy requests still wait behind the list, and legitimate slow queries now fail |
| Release every IAM lock during loading | A stale result can overwrite a later write; a correct optimistic replacement protocol is a separate, larger design |
| Return cached policies without reloading | Changes the administrative query's freshness semantics and conceals the loading problem |
| Increase the whole-list limit to a larger fixed number | Moves the compatibility failure to a different policy count or KES latency |
| Remove only the two outer timeouts | Leaves the etcd post-read decryption deadline regression |
| Remove all backend timeouts | Unnecessarily weakens existing bounded reads, writes, lock waiting, and cleanup |
| Add parallel decryptions or a new cache | Addresses throughput with new scheduling, consistency, and resource-control questions; it is not required for A/B/R1 |
| Rewrite KES SDK retries as part of this fix | Expands dependency behavior beyond the demonstrated server defect; test the existing retry envelope and document its limit instead |

The final A/B/R1 production change is eight files, 83 added lines and 29 removed
lines relative to the tested baseline. Most of the spread comes from passing a
context through internal call sites. The R1 correction itself changes only two
production files, adding 12 lines and removing seven from the first candidate.
Five test files accompany the repair. No dependency, wire protocol, ciphertext
format, or permission model changes are required. These counts describe the
scope; necessity comes from the counterexamples, not from line count alone.

## Evidence and regression contract {#verification}

The controlled baseline was
[`a07d655dc`](https://github.com/pgsty/silo/commit/a07d655dc69cf04b130c2634d9fa5301078af546).
The same process-level experiments were reused against the final source.
Measurements are samples from a local fixture, not production latency guarantees.

| Scenario | Before / rejected candidate | Final implementation |
| --- | --- | --- |
| Four ordinary-user object requests during a slow policy list | Mean 5,284 ms | Mean 2.25 ms; the list itself still takes 5.23 seconds |
| The same ordinary requests with a 200 ms client budget | All four time out | All four return 200 in 1.11–1.82 ms |
| SSE-S3 list abandoned at 200 ms | 21 additional decryptions start after the client exits | No additional decryption starts; four in total, with none active at the end of the observation window |
| Object-backed policy query longer than 30 seconds | Baseline: 200 in 32.74 s; first candidate: 503 in 31.22 s | 200 in 32.75 s, with all 61 policies |
| Fast etcd read, 32-second decryption, 60-second caller budget | Candidate incorrectly constrains post-read decryption | Both policy-list entry points and policy-mapping loading succeed; the read still has its 30-second budget |
| Normal and denied HTTP controls | Baseline statuses, error codes, and result counts | All 51 controls agree, including paging, KMS denial, and signature checks |

The final local acceptance included:

- 36 focused regression scenarios and 23 additional adversarial scenarios, each
  repeated three times with the race detector and no skips or race reports.
- 29 existing IAM revision/revocation scenarios and 64 configuration/crypto/KMS
  scenarios under the race detector.
- Five negative controls: replacing only the two R1 production files with the
  first candidate makes all five budget checks fail. Earlier removal of A or KES
  cancellation propagation also made their corresponding checks fail.
- Full-suite completion across 52 packages: 8,227 passing test records and 168
  existing skips. These are Go test event counts, including parent tests, not a
  count of independent scenarios. The new target regressions did not skip.
- A separate run of the existing etcd concurrency, IAM administration, and STS
  suites across 12 backend/server combinations, with no failures or skips.
- `make verifiers` and `make build`; the optional `typos` tool was unavailable.

The first full run hit `example.com` DNS timeouts in unchanged endpoint tests.
The original source reproduced the identical six failing leaf cases. The full
rerun used process-local `GODEBUG=netdns=go` and passed without changing tests,
assertions, system DNS, or product timeouts. Existing SIMD and external
LDAP/OpenID/plugin skips remain explicit acceptance limits. The older etcd
suites use `_MINIO_ETCD_TEST_SERVER`, while the revision fixtures use
`SILO_TEST_IAM_REVOCATION_ETCD`; starting etcd is not sufficient unless the
intended test suite receives its own configuration.

Two fixture corrections also matter. The KES SDK can perform two non-cancelable
backoff sleeps of up to 999 ms; a 2-second test guard did not cover those sleeps
plus a 300 ms request deadline. The finite guard became three seconds while the
no-additional-decryption assertions stayed strict. The real 32-second probe also
required the KES fixture to answer the legitimate periodic `DescribeKey` request.
After that fixture correction, the focused/adversarial tests and all three long
etcd cases were rerun successfully.

The durable regression entry points are
[`iam-policy-reload_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-reload_test.go),
[`iam-policy-refresh_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-refresh_test.go),
[`iam-policy-budget_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/iam-policy-budget_test.go),
and [`kms-cancellation_test.go`](https://github.com/pgsty/silo/blob/1b5477f3df87924712ad8dc580c8f8eac63eda2d/cmd/kms-cancellation_test.go).
Run the etcd-backed tests with a disposable etcd instance; a skipped backend does
not prove that backend's behavior. Raw investigation logs and private fixtures
remain outside the public source and documentation repositories.

## Sufficiency and remaining boundaries {#limits}

The repair is sufficient for the reproduced cache-lock coupling, lost
cancellation, and both R1 deadline paths. It preserves the checked concurrency
and compatibility contracts without introducing a broader scheduling or timeout
policy. The evidence supports acceptance of this source change; it cannot prove
that no unrelated defect exists.

IAM management writes can still wait behind a slow policy list because `writeMu`
is retained. There is no new fixed-time revocation guarantee. A caller with no
deadline that never cancels can still wait a long time. Existing lower-level
budgets remain in force, and ordinary cached authentication can proceed during
the policy load.

SSE-S3 listing still performs its existing decryption work for a live request.
The fix stops work after cancellation; it does not make that work intrinsically
faster or convert every KMS method to request-scoped cancellation. KES retry
backoff can delay local return even after outbound cancellation is effective.

Multi-node production behavior, hosted CI, publication, and deployment remain
separate verification steps. The supported product graph is the maintained
PGSTY stack; retained MinIO interfaces do not establish a guarantee for every
unmodified upstream component.

## Review lessons {#lessons}

1. **Review every behavior of a reused helper.** Reusing the right lock behavior
   can silently import the wrong deadline.
2. **Cancellation needs a complete path.** Inspect the actual outbound call,
   fallback branches, iteration boundaries, and final cache publication.
3. **Preserve successful slow operations.** A cancellation test is not a
   substitute for a test that must succeed beyond an unrelated backend budget.
4. **Test ordering with real loaders.** A mock that changes concrete backend
   selection can accidentally remove the race the test is meant to cover.
5. **Use counterexamples to establish necessity.** Removing A, cancellation
   propagation, or the R1 correction should reintroduce the corresponding
   observable failure.
6. **Separate product defects from validation defects.** Preserve failures,
   compare the baseline, and fix an incomplete fixture without weakening the
   behavioral assertion or claiming unexecuted coverage.

Related designs:
[Durable IAM Revocations](/blog/design/iam-revocations/),
[Request-Header Deadlines](/blog/design/request-header-timeouts/), and
[KES & OpenBao](/blog/design/kes-openbao/).
