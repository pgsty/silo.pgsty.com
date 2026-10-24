---
title: "A ListObjects Shortcut Must Not Turn a Missing Bucket into an Empty One"
linkTitle: "ListObjects NoSuchBucket"
date: 2026-08-26
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  Three ListObjects shortcuts return EOF before touching storage, causing a missing bucket to appear as an empty listing. This record explains the SILO #32 / PR #37 regression, S3 compatibility value, minimal shortcut-only existence check, cluster fan-out cost, derived risks, and acceptance decision.
tags: [Design, S3, Compatibility, ListObjects]
weight: 25
draft: false
url: "/blog/design/listobjects-nosuchbucket/"
---

Shipped in [SILO Server 20260903](/blog/release/silo-20260903/), [PR #37](https://github.com/pgsty/silo/pull/37) (commit [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377), merged as [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef), closing [SILO #32](https://github.com/pgsty/silo/issues/32)) fixes an S3 compatibility regression where three early-return shortcuts in `ListObjects`, `ListObjectsV2`, and `ListObjectVersions` returned HTTP `200 OK` with an empty listing instead of HTTP `404 NoSuchBucket` when called against a non-existent bucket.

## Too Long; Didn't Read (TL;DR) {#tldr}

A normal `ListObjects`, `ListObjectsV2`, or `ListObjectVersions` request against a missing bucket reaches the storage layer and receives `BucketNotFound`. Three shortcut inputs, however, return early before touching storage:

- a `marker` (or `start-after`) that does not begin with `prefix`;
- `max-keys=0`;
- a `prefix` beginning with `/`, including the `Prefix="/"` `boto3` reproduction from [#32](https://github.com/pgsty/silo/issues/32).

Those three branches returned `io.EOF` directly. Because the caller treats `io.EOF` as the normal end of a listing, the client received an empty HTTP 200 response instead of S3's HTTP 404 `NoSuchBucket`. The same missing bucket changed from a `404` resource error to a `200` success solely because the query filter parameters differed, breaking S3 compatibility and blocking upgrades from pre-regression releases.

Restoring a bucket-existence check on every listing request would reintroduce cluster-wide RPC fan-out on the normal hot path. Instead, PR #37 replaces only the three bare `io.EOF` returns with a helper (`listPathShortcutEOF`) that calls `GetBucketInfo` once: it returns the underlying error when the bucket is absent or cannot be confirmed, and returns `io.EOF` when the bucket exists. Normal listings pay zero extra cost; only requests that would otherwise exit before touching storage pay the `GetBucketInfo` fan-out.

## What Is the Problem? {#problem}

### One API Exposes Two Bucket-Existence Semantics {#two-semantics}

Issue [#32](https://github.com/pgsty/silo/issues/32) reproduces the defect with a single call against a missing bucket:

```python
s3.list_objects(Bucket="missing-bucket", Prefix="/")
```

AWS S3 raises `NoSuchBucket`; SILO returned a successful empty listing. The divergence originates in the object-layer `listPath` control flow:

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

`Prefix="/"` is only one of three triggers:

| Shortcut Condition | Why the Result Must Be Empty | Defect Before the Fix |
| --- | --- | --- |
| `marker` does not begin with `prefix` | The listing engine does not scan a disjoint range | Returns `io.EOF` without confirming bucket existence |
| `max-keys=0` | The caller explicitly requests zero keys | Equates "zero keys requested" with "valid bucket resource" |
| `prefix` begins with `/` | SILO's flat key space never produces keys with a leading `/` | Short-circuits on the filter before checking bucket identity |

For an existing bucket, returning an empty listing from these branches is a valid fast path. For a missing bucket, returning bare `io.EOF` masks the resource error that must take precedence.

### Tracing the Regression to Upstream `#18917` {#regression}

The reporter confirmed that `RELEASE.2024-01-29T03-56-32Z` returned `NoSuchBucket` and that the regression started in `RELEASE.2024-01-31T20-20-33Z`. Tracing git history pinpoints upstream [minio/minio#18917](https://github.com/minio/minio/pull/18917) ([`80ca12008`](https://github.com/minio/minio/commit/80ca120088be9950fa35467975dd9d8dc1bd4176)), which removed `GetBucketInfo` from generic handler argument checks and relied on the underlying `Put`, `List`, and `Multipart` storage operations to surface `BucketNotFound`.

That assumption holds whenever the request reaches storage, but breaks on early-return branches that exit before touching any drive. Fixing [#32](https://github.com/pgsty/silo/issues/32) therefore requires closing the three control-flow exits that bypass storage, rather than reverting `#18917`.

## Why Fix It? {#why-fix}

### The S3 Contract Requires `NoSuchBucket` {#s3-contract}

Both [AWS `ListObjects`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html) and [`ListObjectsV2`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html) specify HTTP 404 `NoSuchBucket` when the target bucket does not exist. Selection parameters (`prefix`, `marker`, `start-after`, and `max-keys`) filter objects inside an existing bucket; they cannot make a non-existent bucket succeed. Because `ListObjectVersions` shares the same object-layer listing engine, applying the fix across all three APIs keeps V1, V2, and version listings consistent.

### An Empty HTTP 200 Alters Client Control Flow {#client-impact}

An empty HTTP 200 and an HTTP 404 drive opposite decisions in client applications:

- HTTP 404 tells provisioning scripts, SDKs, or test harnesses to create the bucket, report a configuration error, or abort;
- an empty HTTP 200 asserts that the bucket exists and currently holds no matching keys;
- integration test suites using SILO as a local S3 target pass against a missing bucket locally and then fail against AWS S3.

### The Repair Surface Is Narrow and Verifiable {#repair-value}

The defect is confined to three adjacent early returns in `cmd/metacache-server-pool.go` and does not touch object data, metadata formats, sorting, continuation-token encoding, IAM evaluation, or XML schemas.

## Why We Cannot Simply Restore a Global Check {#performance-constraint}

Upstream [#18917](https://github.com/minio/minio/pull/18917) removed generic `GetBucketInfo` checks because calling `GetBucketInfo` before every `Put`, `List`, and `Multipart` operation fans out across all servers in the cluster; even after request vectorization, that overhead becomes pronounced past 100 nodes.

In SILO, `erasureServerPools.GetBucketInfo` invokes `S3PeerSys.GetBucketInfo`, which queries every peer concurrently and reduces quorum across pools while each peer inspects its local bucket state. Neither extreme is acceptable:

- **Never check on shortcuts:** preserves the bogus HTTP 200 on missing buckets.
- **Check before every `List`:** restores `404` semantics at the cost of undoing the large-cluster optimization on every normal listing.

Confining the `GetBucketInfo` call to the three branches that bypass storage solves the compatibility bug without taxing normal `ListObjects` traffic.

## Implementation {#implementation}

### Replace Only the Three Bare `io.EOF` Returns {#three-shortcuts}

In `cmd/metacache-server-pool.go`, each of the three shortcut branches previously executed:

```go
return entries, io.EOF
```

Each branch now calls `listPathShortcutEOF`:

```go
return entries, z.listPathShortcutEOF(ctx, o.Bucket)
```

where `listPathShortcutEOF` is defined as:

```go
func (z *erasureServerPools) listPathShortcutEOF(ctx context.Context, bucket string) error {
    if _, err := z.GetBucketInfo(ctx, bucket, BucketOptions{}); err != nil {
        return err
    }
    return io.EOF
}
```

This helper produces three possible outcomes:

- **Bucket exists:** returns `io.EOF`, preserving the empty listing response.
- **Bucket does not exist:** returns `BucketNotFound`, which maps to HTTP 404 `NoSuchBucket`.
- **Cluster state cannot be confirmed:** propagates quorum, offline, timeout, or context cancellation errors rather than fabricating an empty success.

The normal `listMerged`, metacache scan, sorting, pagination, and XML rendering paths remain untouched.

### Why the Helper Belongs in `listPath` {#helper-boundary}

Placing the check directly at the shortcut exits in `listPath` satisfies three constraints:

1. Only `listPath` knows that it is about to return early without consulting any storage drive.
2. Moving the check up into HTTP handler validation would charge every listing request.
3. Moving the check down into the scanner cannot work because these three branches never enter the scanner.

### Why We Do Not Add an Existence Cache {#no-cache}

Caching bucket existence would reduce shortcut fan-out, but immediately introduces cache-invalidation hazards across bucket creation, deletion, site replication, healing, and TTL expiration. Introducing a second source of truth for three low-frequency shortcut paths adds more consistency risk than it saves. If production telemetry ever shows high-volume `max-keys=0` or leading-slash probing on large clusters, rate limiting or a dedicated metadata fast path can be evaluated with real traffic data.

## Verification Evidence {#verification}

### Object-Layer Contract {#object-layer-tests}

Object-layer regression tests run against both single-drive and multi-drive erasure setups across four inputs:

- leading-slash `prefix` (`Prefix="/"` and `Prefix="/sub"`),
- `max-keys=0`,
- `marker` outside `prefix`,
- a regular `prefix` as a control case that naturally receives `BucketNotFound` from storage.

Every case exercises `ListObjects`, `ListObjectsV2`, and `ListObjectVersions` and asserts `isErrBucketNotFound`.

### HTTP Wire Contract {#http-tests}

The HTTP handler test sends signed S3 requests across all three public listing APIs:

| API | Request Shape | Assertion |
| --- | --- | --- |
| `ListObjects` | `GET /missing-bucket?prefix=/` | HTTP 404 and XML code `NoSuchBucket` |
| `ListObjectsV2` | `GET /missing-bucket?list-type=2&prefix=/` | HTTP 404 and XML code `NoSuchBucket` |
| `ListObjectVersions` | `GET /missing-bucket?versions&prefix=/` | HTTP 404 and XML code `NoSuchBucket` |

### Local and CI Quality Gates {#local-gates}

The change passed the full local verification suite (`go test ./cmd -count=1` in 116.2 s, the 10 new object-layer and HTTP regression subcases under `-race`, `CGO_ENABLED=0 go build ./...`, `go vet ./...`, and independent design and code review). On GitHub Actions, DCO-signed PR head [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377) passed [DCO](https://github.com/pgsty/silo/actions/runs/32961304270), [VulnCheck](https://github.com/pgsty/silo/actions/runs/32961304271), and all six [Go CI](https://github.com/pgsty/silo/actions/runs/32961304309) jobs, and merge commit [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef) passed post-merge [VulnCheck](https://github.com/pgsty/silo/actions/runs/32962256729) and [Go CI](https://github.com/pgsty/silo/actions/runs/32962256823).

## Derived Risks and Edge Cases {#derived-risks}

### Shortcut Requests Now Fan Out Across the Cluster {#fanout-cost}

On an existing bucket, a shortcut request previously executed a purely local branch; it now calls `GetBucketInfo`. Local microbenchmarks illustrate the relative shift:

| Path | Observed Local Magnitude |
| --- | ---: |
| Shortcut before the fix | ~0.55 μs, 7 allocs |
| Repaired single-drive shortcut | ~7.8–8.1 μs, 45–47 allocs |
| Repaired 32-drive shortcut | ~70–81 μs, 977 allocs |
| Normal 32-drive listing | ~0.95 ms |

In multi-node deployments, `GetBucketInfo` includes peer network round-trips and quorum reduction. That cost is why the check is strictly confined to the three storage-bypassing shortcuts. If a misconfigured client polls `max-keys=0` or `Prefix="/"` at high frequency, S3 audit traces and metrics will surface the pattern.

### Degraded Clusters Surface Real Quorum Errors {#degraded-cluster}

Previously, a shortcut could return an empty HTTP 200 even when peers were offline and bucket read quorum was lost, because it never inspected cluster state. Calling `GetBucketInfo` means a degraded cluster that cannot establish bucket existence now returns a quorum or timeout error rather than asserting that a valid empty bucket exists.

### Bucket Create/Delete Races Remain Non-Linearizable {#race-window}

`GetBucketInfo` and returning the empty response are two sequential steps: a bucket can be deleted immediately after `GetBucketInfo` succeeds, or created immediately after `BucketNotFound` is observed. This matches the concurrency model of all other S3 APIs that validate resource existence before acting.

### Clients Relying on the Bug Will Now Receive HTTP 404 {#behavior-change}

Callers that inadvertently depended on `Prefix="/"` or `max-keys=0` returning HTTP 200 against a non-existent bucket will now receive HTTP 404 `NoSuchBucket`, matching AWS S3 and pre-2024 behavior.

### Two Adjacent Edge Cases Left Out of Scope {#remaining-edges}

Design review noted two low-severity boundaries intentionally left outside this change:

1. **Stale continuation token after bucket deletion:** When resuming a metacache continuation, the `c.fileNotFound` branch still returns bare `io.EOF`. A stale or crafted continuation token presented after its bucket was deleted could theoretically receive an empty HTTP 200. Calling `GetBucketInfo` on that branch would penalize normal paginated continuations and requires a separate design.
2. **Handler-level `NotImplemented` checks:** Certain V1 and version-list `marker`/`prefix` combinations return `NotImplemented` during HTTP handler parameter validation before reaching the object layer (whereas V2 `start-after` reaches `listPath`). PR #37 repairs storage shortcuts masking missing buckets without altering HTTP parameter validation precedence.

## Rejected Alternatives {#alternatives}

### Keep Upstream Behavior {#keep-upstream}

Keeping the bare `io.EOF` returns avoids any shortcut overhead, but preserves a known S3 regression and causes integration tests against SILO to diverge from AWS S3. Rejected.

### Restore Generic `checkBucketExist` {#restore-global-check}

Checking bucket existence before every `Put`, `List`, and `Multipart` call fixes all paths at once, but reintroduces cluster-wide peer fan-out on the normal hot path, undoing upstream `#18917`. Rejected.

### Fix Only `Prefix="/"` {#slash-only}

Patching only the leading-slash branch passes the single `boto3` snippet from `#32` while leaving the identical bug in `max-keys=0` and disjoint `marker` inputs. Because all three branches sit in `listPath` and share the same root cause, routing all three through `listPathShortcutEOF` is cleaner and complete. Rejected.

### Add a Bucket-Existence Cache {#existence-cache}

Adding a TTL cache for bucket existence reduces shortcut latency, but requires invalidation rules across bucket creation, deletion, replication, and healing without any evidence that shortcut traffic warrants a second metadata cache. Rejected.

## Complexity and Cost-Benefit Summary {#tradeoff}

| Dimension | Assessment | Rationale |
| --- | --- | --- |
| Production code complexity | Low | Three call sites and a 7-line helper; no new state, dependency, or on-disk format |
| Test complexity | Low–Medium | Covers V1, V2, version listings, all three shortcuts, a regular-prefix control, and HTTP 404 XML mapping |
| Normal-path risk | None | Zero changes on the `listMerged` hot path |
| Shortcut runtime cost | Higher on shortcuts only | Replaces a local branch with `GetBucketInfo` when a shortcut triggers |
| Compatibility value | High | Restores HTTP 404 `NoSuchBucket`, pre-regression upgrade compatibility, and S3 test fidelity |
| Operational complexity | None | No migration, configuration knob, feature flag, or cache invalidation |

## Acceptance Decision {#decision}

PR #37 was accepted and merged as [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef) (retaining Jason Lin as co-author on [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377)) with typed error predicates and full V1/V2/version-list object-layer and HTTP-level coverage, and shipped in [SILO Server 20260903](/blog/release/silo-20260903/).

## Summary {#conclusion}

The listing engine previously overloaded `io.EOF` to represent both "an existing bucket produced zero matching keys" and "an early filter exit returned before touching storage." Removing generic bucket-existence checks in `#18917` relied on the premise that a subsequent storage operation would surface `BucketNotFound`. Calling `GetBucketInfo` at the three storage-bypassing exits in `listPath` restores that invariant and S3 `NoSuchBucket` compatibility while keeping the normal listing path unchanged.
