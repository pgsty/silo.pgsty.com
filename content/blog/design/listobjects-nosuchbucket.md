---
title: "A ListObjects Shortcut Must Not Turn a Missing Bucket into an Empty One"
linkTitle: "ListObjects NoSuchBucket"
date: 2026-08-26
lastmod: 2026-08-26
author: "Ruohang Feng"
summary: >
  Three ListObjects shortcuts return EOF before touching storage, causing a missing bucket to appear as an empty listing. This record explains the SILO #32 / PR #37 regression, S3 compatibility value, minimal shortcut-only existence check, cluster fan-out cost, derived risks, and acceptance decision.
tags: [Design, S3, Compatibility, ListObjects]
weight: 25
draft: false
url: "/blog/design/listobjects-nosuchbucket/"
---

This document records the problem analysis, design discussion, and repair decision for [SILO #32](https://github.com/pgsty/silo/issues/32) and [PR #37](https://github.com/pgsty/silo/pull/37).

> **Status on 2026-08-26:** [PR #37](https://github.com/pgsty/silo/pull/37) was updated to the DCO-signed head [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377), formally approved, and merged as [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef); [#32](https://github.com/pgsty/silo/issues/32) closed automatically. DCO, VulnCheck, and all six Go CI jobs passed on the exact PR head; the post-merge `main` VulnCheck and all six Go CI jobs also passed. No tagged release, package, container image, deployment, or production endpoint has yet been verified to contain the repair.<br>
> **Scope:** verify bucket existence only for three listing shortcuts that bypass storage; do not restore the generic `checkBucketExist`, change the normal listing path, or introduce an existence cache.<br>
> **Release boundary:** local commit, push, remote CI, merge, tag, package, container image, deployment, and production verification are independent gates.

## Too Long; Didn't Read (TL;DR) {#tldr}

The problem is real and worth fixing. A normal `ListObjects`, `ListObjectsV2`, or `ListObjectVersions` request against a missing bucket reaches storage and receives `BucketNotFound`. Three inputs, however, return early:

- a marker outside the prefix;
- `max-keys=0`;
- a prefix beginning with `/`, including the `Prefix="/"` boto3 reproduction from #32.

Those branches return `io.EOF` directly. The caller treats EOF as a successful end of listing, so the client receives an empty 200 rather than S3's 404 `NoSuchBucket`. The identity of the same missing resource changes from an error to success solely because the selection parameters differ. That breaks S3 compatibility and blocks a real user's upgrade from the pre-regression release.

The repair must not put an expensive bucket check back in every listing. The selected design replaces only the three bare `io.EOF` returns with a small helper. The helper calls `GetBucketInfo` once: it returns the real error if the bucket is absent or cannot be confirmed, and preserves `io.EOF` when the bucket exists. The normal listing hot path is untouched. Only requests that would otherwise exit before storage pay the extra peer-and-disk fan-out.

That decision has now been executed: **the strengthened repair passed local review, the exact PR head passed every remote check, and the expected-head-guarded merge entered a green `main`.**

## What is the problem? {#problem}

### One API exposes two bucket-existence semantics {#two-semantics}

#32 reproduces the defect by calling the following against a missing bucket:

```python
s3.list_objects(Bucket="missing-bucket", Prefix="/")
```

AWS S3 raises `NoSuchBucket`; SILO returns a successful empty listing. The difference is not in authentication, routing, or XML serialization. It comes from the object-layer `listPath` control flow:

```text
regular prefix
  -> enter listMerged
  -> consult storage
  -> missing volume/bucket becomes BucketNotFound
  -> HTTP 404 NoSuchBucket

shortcut input
  -> listPath returns io.EOF early
  -> storage is never consulted
  -> the caller treats EOF as normal completion
  -> HTTP 200 with an empty listing
```

`/` is not the only trigger:

| Shortcut condition | Why the result must be empty | Defect before the repair |
| --- | --- | --- |
| Marker does not begin with the prefix | The implementation does not scan this disjoint range | Returns EOF without confirming the bucket |
| `max-keys=0` | The caller asks for zero keys | Incorrectly equates “zero results” with “valid resource” |
| Prefix begins with `/` | SILO's flat key space produces no entries for this form | The filter short-circuits before bucket identity |

For an existing bucket, returning an empty listing from these branches is a reasonable optimization. For a missing bucket, the same EOF masks the resource error that should take precedence.

### The regression has a known origin {#regression}

The reporter confirmed correct behavior in `RELEASE.2024-01-29T03-56-32Z` and the regression beginning with `RELEASE.2024-01-31T20-20-33Z`. The corresponding upstream change is [minio/minio#18917](https://github.com/minio/minio/pull/18917) / [`80ca12008`](https://github.com/minio/minio/commit/80ca120088be9950fa35467975dd9d8dc1bd4176). It removed `GetBucketInfo` from generic argument checks and relied on actual Put, List, and Multipart storage operations to expose a missing bucket.

That optimization works on normal paths but leaves a gap: an early-return path never reaches the storage operation that is now responsible for producing the error. #32 does not require a broad rollback of the upstream optimization. It repairs the overlooked control-flow exits.

## Why fix it? {#why-fix}

### The S3 contract explicitly requires `NoSuchBucket` {#s3-contract}

Both [AWS ListObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html) and [ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html) define `NoSuchBucket` as HTTP 404 when the specified bucket does not exist. `prefix`, marker, `start-after`, and `max-keys` select listing results; they must not turn a missing bucket identity into a successful request.

`ListObjectVersions` shares the same object-layer listing engine. Giving V1, V2, and version listings the same existence behavior on the same shortcut inputs prevents the three public APIs from diverging further.

### An empty 200 changes client decisions {#client-impact}

An empty 200 and a 404 are not interchangeable presentation details:

- 404 tells provisioning or test code to create the bucket, fix configuration, or stop;
- an empty 200 asserts that the bucket exists but has no matching objects;
- SDKs, synchronization tools, and integration tests continue down different branches;
- a test using SILO as an S3 substitute can pass locally and fail against AWS.

#32 also establishes a direct upgrade impact: an application relying on the older correct behavior cannot upgrade past the regression. The repair restores both S3 parity and upgrade compatibility.

### The repair surface is narrow and testable {#repair-value}

The bug is confined to three adjacent early returns. It does not involve object data, metadata formats, sorting, pagination-token encoding, permissions, or wire schemas. A very small production change can be pinned down with object-layer and HTTP-level contracts, so the benefit clearly exceeds the implementation risk.

## Why not restore the global check? {#performance-constraint}

Upstream did not remove generic `GetBucketInfo` as incidental cleanup. [The motivation for #18917](https://github.com/minio/minio/pull/18917) states that checking the bucket before every Put, List, and Multipart operation fans out across servers; even after vectorization, the cost becomes visible beyond 100 nodes.

In current SILO, `erasureServerPools.GetBucketInfo` calls `S3PeerSys.GetBucketInfo`. That operation concurrently asks every peer and reduces quorum per pool, while each peer checks its local bucket state. It is not a cheap in-memory map lookup.

Two extremes are therefore unacceptable:

- **never check:** keep the incorrect empty 200;
- **check before every List:** restore semantics while undoing a critical large-cluster optimization.

The actual design question is whether the check can be confined to branches that never touch storage and therefore cannot discover the missing bucket naturally. It can.

## How is it fixed? {#implementation}

### Replace only three bare EOF returns {#three-shortcuts}

In `cmd/metacache-server-pool.go`, each shortcut previously executed:

```go
return entries, io.EOF
```

It now executes:

```go
return entries, z.listPathShortcutEOF(ctx, o.Bucket)
```

The helper has only two classes of outcome:

```go
func (z *erasureServerPools) listPathShortcutEOF(ctx context.Context, bucket string) error {
    if _, err := z.GetBucketInfo(ctx, bucket, BucketOptions{}); err != nil {
        return err
    }
    return io.EOF
}
```

- existing bucket: preserve the previous empty-list behavior;
- missing bucket: pass `BucketNotFound` into the existing error mapping, producing HTTP 404 `NoSuchBucket`;
- state cannot be confirmed: propagate quorum, offline, timeout, or context errors instead of fabricating success.

The normal `listMerged`, metacache scan, sorting, pagination, and response-generation paths do not change.

### Why the helper belongs here {#helper-boundary}

The check must sit next to the shortcut for three reasons:

1. only this layer knows that it is about to bypass every storage access;
2. moving it into generic argument validation charges every call;
3. moving it into the scan layer cannot help because these branches never scan.

The name intentionally states the boundary. This is not a new generic `checkBucketExist`; it restores missing existence semantics immediately before a shortcut returns EOF.

### Do not add a cache {#no-cache}

A bucket-existence cache could reduce fan-out but immediately creates invalidation questions for create, delete, site replication, recovery, and expiry. Adding a second source of truth for three low-frequency shortcuts costs more complexity and consistency risk than it saves.

The selected implementation uses the existing `GetBucketInfo` source of truth. If future telemetry shows that large clusters receive frequent `max-keys=0`, slash-prefix, or disjoint-marker probes, the project can evaluate a dedicated metadata fast path, rate limiting, or a carefully invalidated cache using real data rather than speculative machinery in this compatibility patch.

## Test and review evidence {#verification}

### Object-layer contract {#object-layer-tests}

The object-layer test runs against single-drive and multi-drive erasure setups and exercises four inputs:

- slash-prefixed prefix;
- zero limit;
- marker outside prefix;
- a regular prefix as a control that still receives the error naturally from storage.

Each case covers `ListObjects`, `ListObjectsV2`, and `ListObjectVersions`, using the typed `isErrBucketNotFound` predicate rather than brittle English error-string comparison.

### HTTP contract {#http-tests}

The handler test sends genuine signed requests for all three public APIs:

| API | Request shape | Assertion |
| --- | --- | --- |
| ListObjects | `GET /missing-bucket?prefix=/` | HTTP 404 and XML code `NoSuchBucket` |
| ListObjectsV2 | Add `list-type=2` | HTTP 404 and XML code `NoSuchBucket` |
| ListObjectVersions | Add `versions` | HTTP 404 and XML code `NoSuchBucket` |

The HTTP test uses the real slash-prefix reproduction from #32. The other two shortcuts are enumerated at the object layer. This proves final wire behavior without repeating the full matrix in the slower handler fixture.

### Local quality gates {#local-gates}

The improved local commit passed:

```text
go test ./cmd -count=1
the new object-layer and HTTP regressions (10 subcases)
focused go test -race
related existing listing tests
CGO_ENABLED=0 go build ./...
go vet ./...
CI-scope gofmt and git diff --check
post-commit focused regression rerun
```

The full local `cmd` test completed in 116.215 seconds. An independent local Claude Code review used the Fable model at Max effort to inspect the exact tree, call paths, error mapping, tests, performance boundary, and this decision. Its verdict was **GO**, with no mandatory pre-merge change.

The DCO-signed PR head `e9c5340be` then passed eight remote checks: [DCO](https://github.com/pgsty/silo/actions/runs/32961304270), [VulnCheck](https://github.com/pgsty/silo/actions/runs/32961304271), and six jobs in [Go CI](https://github.com/pgsty/silo/actions/runs/32961304309). After merge, the resulting `main` commit `49c8aeac4` independently passed [VulnCheck](https://github.com/pgsty/silo/actions/runs/32962256729) and all six [Go CI](https://github.com/pgsty/silo/actions/runs/32962256823) jobs. The slowest checks were PR cross-compile at 9 minutes 47 seconds and post-merge cross-compile at 9 minutes 30 seconds.

## Can it introduce new problems? {#derived-risks}

### Shortcut requests now fan out across the cluster {#fanout-cost}

This is the most important and deliberately accepted cost. A shortcut on an existing bucket used to be little more than a local branch; it now calls `GetBucketInfo`. Directional local microbenchmarks observed:

| Path | Observed magnitude |
| --- | ---: |
| Shortcut before the repair | about 0.55 μs, 7 allocations |
| Repaired single-drive shortcut | about 7.8–8.1 μs, 45–47 allocations |
| Repaired 32-drive shortcut | about 70–81 μs, 977 allocations |
| Normal 32-drive listing | about 0.95 ms |

These numbers show local relative cost only; they are not a latency prediction for a 100+ node deployment. Real distributed execution adds peer networks, quorum, and slowest-node tail latency, potentially making the gap much larger. That is precisely why the check must not expand into the normal listing path.

The risk concentrates in malformed or probe-style traffic. A misconfigured client polling `max-keys=0`, a slash prefix, or disjoint markers at high frequency can amplify what was a cheap request into peer-and-disk work. After merge, the actual frequency of these inputs should be observed through S3 traces or metrics; rate limiting or optimization should follow evidence.

### A degraded cluster exposes more real errors {#degraded-cluster}

Previously, a shortcut could return an empty 200 while peers were offline or bucket quorum was unavailable because it never consulted cluster state. The repair can return quorum, timeout, or service errors in those conditions.

That is more honest behavior, not an availability regression: if the server cannot establish that the bucket exists, it must not assert a valid empty bucket. Clients depending on unconditional empty success will nevertheless observe a behavior change.

### Bucket create/delete races are not linearizable {#race-window}

`GetBucketInfo` and returning the empty result are two actions. The bucket can be deleted immediately after the check, or created immediately after a missing-bucket result is formed. This patch does not and should not add a transaction spanning bucket lifecycle to a listing shortcut.

This is the same concurrency class as other APIs that validate a resource before acting. The repair guarantees that the request no longer succeeds with **no existence evidence at all**; it does not promise a cross-node, cross-lifecycle linearizable snapshot of an empty listing.

### Clients relying on the bug will receive 404 {#behavior-change}

Some clients may have adopted the missing bucket's empty 200 as fact. They will now enter an error branch. This is a visible compatibility change, but it restores the documented S3 contract and the pre-regression behavior. Preserving the bug merely transfers upgrade cost to clients that correctly rely on 404.

### Two adjacent edges remain out of scope {#remaining-edges}

The adversarial review recorded two non-blocking P3 boundaries:

1. When resuming a metacache continuation, the `c.fileNotFound` branch still returns bare `io.EOF`. A stale or crafted continuation token used after bucket deletion could theoretically receive an empty 200. Adding `GetBucketInfo` there would affect normal continuation traffic and needs a separate performance and error-precedence design.
2. Some V1 and version-list marker/prefix combinations return `NotImplemented` during HTTP handler validation before reaching the object layer; the V2 `start-after` route can reach it. This patch fixes storage shortcuts masking a missing bucket; it does not redefine precedence between malformed parameters and resource errors.

Neither blocks merge. The first is outside #32's ordinary initial-list reproduction; the second is inherited handler behavior. Recording them prevents “all three shortcuts are covered” from being overstated as byte-for-byte AWS parity for every possible parameter combination.

## Alternatives considered {#alternatives}

### Keep upstream behavior {#keep-upstream}

This has zero performance change and minimizes fork divergence. It also keeps a documented S3 incompatibility, a regression with a known release boundary, and a misleading result when SILO is used as an integration-test substitute. For a narrow and well-tested compatibility repair, that tradeoff is no longer justified.

### Restore generic `checkBucketExist` {#restore-global-check}

This covers every path at once but reintroduces peer fan-out into every Put, List, and Multipart operation, directly undoing the large-cluster optimization from #18917. The cost is disproportionate and the option is rejected.

### Fix only `Prefix="/"` {#slash-only}

That passes the single issue reproduction but leaves the same root defect in `max-keys=0` and marker-outside-prefix. The branches are adjacent and share the same semantics, so one helper is simpler and less likely to regress.

### Add a bucket-existence cache {#existence-cache}

This makes shortcuts cheaper but requires semantics for create, delete, replication, recovery, and stale TTL windows. There is no telemetry showing enough shortcut traffic to justify that complexity, so it is not selected.

## Complexity and cost-benefit {#tradeoff}

| Dimension | Assessment | Rationale |
| --- | --- | --- |
| Production-code complexity | Low | Three call sites and a seven-line helper; no new state, dependency, or format |
| Test complexity | Low to medium | V1, V2, versions, three shortcuts, a control, and HTTP mapping all need coverage |
| Normal-path risk | Very low | No check is added to the `listMerged` hot path |
| Shortcut runtime cost | Materially higher | A local EOF becomes cluster-wide `GetBucketInfo` |
| Compatibility value | High | Restores 404 `NoSuchBucket`, pre-regression behavior, and S3 test fidelity |
| Operational complexity | Low | No migration, configuration, feature flag, cache, or cross-repository dependency |

The overall cost-benefit is favorable. The reason is not that `GetBucketInfo` is cheap—it is not—but that its cost is strictly limited to three shortcuts that otherwise cannot discover the missing bucket. A narrow performance cost in exchange for explicit protocol correctness is better than either a global rollback or indefinitely preserving the incorrect behavior.

## Acceptance decision and remaining gates {#decision}

The final decision was: **accept and merge the strengthened PR #37 revision without expanding the production scope.**

The accepted sequence was:

1. replace the old fork head with the current-`main`, DCO-signed revision while preserving Jason Lin as a co-author;
2. retain typed error predicates, V1/V2/version-list object-layer coverage, and HTTP-level 404 / `NoSuchBucket` assertions;
3. update the PR description with the shortcut fan-out cost and unchanged normal-path boundary;
4. approve the fork workflows and require all eight reported checks to pass on exact head `e9c5340be`;
5. submit a formal approving review against that head;
6. merge with an expected-head guard, producing `49c8aeac4`, automatically close #32, and require the resulting `main` Go CI and VulnCheck to pass independently.

No cache, feature flag, additional abstraction, or continuation-token redesign was required. High-frequency shortcut traffic and large-cluster tail latency remain observability follow-ups, not reasons for speculative code expansion.

Repository integration is complete. A tag, package, `docker.io/pgsty/minio` image, deployment, and real S3-client verification must still complete before the repair can be described as delivered to users.

## Conclusion {#conclusion}

The issue is not merely “a slash prefix reports the wrong error.” The listing engine uses `io.EOF` to mean two different things: an empty result from an existing bucket and an early exit that never established whether the bucket exists. Removing generic existence checks for large-cluster performance was a sound upstream optimization, but the shortcuts violate its premise that a real storage operation will naturally surface a missing bucket.

The selected repair restores that premise by calling the existing `GetBucketInfo` only at three storage-bypassing exits. It makes those requests more expensive and exposes real errors on degraded clusters; both are explicit costs. In return, SILO restores S3's 404 semantics, upgrade compatibility, and test fidelity while preserving the upstream optimization on the normal listing hot path.

This worthwhile, controlled compatibility fix is now merged and green on `main`; release delivery remains a separate gate.
