---
title: "Should SILO Fix ListMultipartUploads? Design Review of Issue #79"
linkTitle: "ListMultipartUploads Compatibility"
date: 2026-08-30
lastmod: 2026-08-30
author: "Ruohang Feng"
summary: >
  SILO treats ListMultipartUploads prefix as an exact object key and uses a node-local volatile cache for bucket-wide listing. This record explains the defect and its sources, evaluates the compatibility and operational impact, compares four response and storage options, and recommends a staged metadata-plus-scan repair rather than either a cosmetic cache patch or an immediate durable index.
tags: [Design, S3, Compatibility, Multipart]
weight: 35
draft: false
url: "/blog/design/list-multipart-uploads/"
---

This is the problem, design, and decision record for [SILO issue #79](https://github.com/pgsty/silo/issues/79).

> **Status on 2026-08-30:** confirmed compatibility defect; design proposal only. No server implementation, release artifact, deployment, or production verification is claimed by this record.<br>
> **Recommendation:** fix it as a planned P1 compatibility project, not as a small cache patch. If the project declines full compatibility, reject unsupported requests explicitly instead of returning a successful response that did not honor them.<br>
> **Scope:** `ListMultipartUploads` for S3 general-purpose buckets. This record does not add directory-bucket behavior or `AbortIncompleteMultipartUpload` lifecycle support.<br>
> **Owner:** [`pgsty/silo`](https://github.com/pgsty/silo), the SILO server repository.<br>
> **Release boundary:** design, specification capture, prototype, implementation, source QA, commit, release artifact, documentation, deployment, and live verification are separate gates.

## The problem in plain language {#plain-language}

Imagine that four large files are still being uploaded:

```text
tables/a/part-1
tables/a/part-2
tables/b/part-1
other/file
```

An S3 client asks, "show me every unfinished upload below `tables/`." AWS S3 returns the first three. SILO currently treats `tables/` as if it were the complete name of one object, looks for exactly that object, and returns an empty list.

If the client removes the prefix and asks for every unfinished upload in the bucket, SILO takes a different shortcut: it reads a process-local memory cache. That cache may contain all four uploads on the node that created them, but it does not survive a restart and is not authoritative across nodes. The upload data is still on disk; the list is wrong.

This is why the defect is more serious than one ignored query parameter. Cleanup tools can receive `200 OK`, conclude that no unfinished uploads exist, and report success while uploads remain on disk. The server is not losing committed objects, but it is giving callers a false view of unfinished work.

## Executive decision {#decision}

SILO should fix this behavior if it intends to keep advertising practical S3 compatibility.

The repair is justified because the current endpoint silently claims success, behaves differently after restart or node switching, and breaks standard prefix-based cleanup and pagination. The default 24-hour stale-upload collector limits storage accumulation on default configurations, but it does not make the API result truthful.

The repair is not a small change. Existing upload directories contain only a one-way hash of the bucket and object key, and the original key is not stored in their `xl.meta`. A correct implementation must begin persisting that identity for new uploads, discover candidates with erasure-aware quorum rules, apply S3 semantics globally across pools and sets, and handle legacy uploads during a rolling upgrade.

The recommended direction is therefore:

1. record the bucket and object key in the upload's existing quorum-written metadata;
2. build a bounded on-demand scan as the durable correctness path;
3. keep any cache only as a rebuildable optimization;
4. enable strict S3 behavior only after every writer has upgraded and all keyless legacy uploads have drained;
5. consider a durable secondary index only if measurements prove that scanning cannot meet a product-approved service-level objective.

## Sources and provenance {#sources}

The problem statement and proposed design are grounded in five kinds of evidence.

### The S3 contract {#source-s3}

The [AWS ListMultipartUploads API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) defines the public contract for general-purpose buckets:

- `prefix` selects every upload whose key starts with that string;
- `delimiter` groups matching keys into `CommonPrefixes`;
- `max-uploads` limits a page, with 1,000 as the documented maximum;
- `key-marker` and `upload-id-marker` continue a truncated listing;
- `upload-id-marker` is ignored when `key-marker` is absent;
- results are ordered by object key, then by initiation time for uploads with the same key.

AWS documentation does not settle every implementation edge unambiguously. Equal timestamps, invalid or out-of-range `max-uploads`, URL encoding, marker boundaries, and the way `CommonPrefixes` consume a page should be captured once against AWS and stored as fixtures before implementation.

### The reported defect {#source-issue}

[Issue #79](https://github.com/pgsty/silo/issues/79) supplied a self-contained signed reproducer against `pgsty/silo:latest` and compared SILO with AWS, RustFS, SeaweedFS, and Garage. Its four central observations reproduce:

| Request | Required behavior | Observed SILO behavior |
| --- | --- | --- |
| `prefix=t/` | return the three keys beginning with `t/` | returns no uploads |
| `max-uploads=1` | return one item and continuation markers | returns every cached upload |
| `key-marker=t/a_b/p2` | continue after that key | returns every cached upload |
| `prefix=t/&delimiter=/` | return grouped `CommonPrefixes` | returns neither uploads nor prefixes |

The issue correctly identifies a compatibility failure, but its statement that `max-uploads` is always ignored and `IsTruncated` is always false is broader than the implementation. Those claims hold on the empty-prefix cache path used by the reproducer; the exact-object path can honor `max-uploads` and `upload-id-marker` and can set `IsTruncated`.

### The upstream design history {#source-upstream}

The behavior was inherited rather than invented by SILO:

- MinIO [PR #5248](https://github.com/minio/minio/pull/5248) deliberately removed prefix-based listing from the erasure backend in 2017 "to simplify" multipart support.
- MinIO [PR #20407](https://github.com/minio/minio/pull/20407) added the empty-prefix multipart cache in 2024, mainly for Alluxio tests.
- A 2025 report of the same exact-key behavior, [MinIO issue #20989](https://github.com/minio/minio/issues/20989), was closed as working as intended.
- SILO's current [S3 compatibility reference](/reference/s3-api-compatibility/#differences-from-s3-apis-for-multipart-uploads) already records the exact-object-name divergence, although it did not explain the cache, pagination, marker, delimiter, or restart limitations before this design record.

This history explains why the code looks deliberate. It does not make the endpoint compatible with the AWS contract.

### Source review {#source-code}

The current source has two mutually exclusive listing paths:

```text
erasureServerPools.ListMultipartUploads
  prefix == ""  -> return entries from node-local mpCache
  prefix != ""  -> hash prefix as a complete object key
                    -> select one set
                    -> list one sha256(bucket/object) directory
```

The important locations are:

- [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/main/cmd/erasure-server-pool.go): empty-prefix `mpCache`, per-pool concatenation, and the internal exact-object lookup used by `NewMultipartUpload`;
- [`cmd/erasure-multipart.go`](https://github.com/pgsty/silo/blob/main/cmd/erasure-multipart.go): exact-object listing, upload directory construction, stale-upload cleanup, and the quorum write for a new upload's `xl.meta`;
- [`cmd/erasure-sets.go`](https://github.com/pgsty/silo/blob/main/cmd/erasure-sets.go): hashing a supplied object name to one erasure set;
- [`cmd/bucket-handlers.go`](https://github.com/pgsty/silo/blob/main/cmd/bucket-handlers.go): public request validation, including a `501 NotImplemented` guard when `key-marker` does not share the request prefix;
- [`cmd/object-api-multipart_test.go`](https://github.com/pgsty/silo/blob/main/cmd/object-api-multipart_test.go): a large expected-results table whose final assertion block checks only echoed scalar fields, not the returned uploads, prefixes, markers, or truncation state.

### Independent reproduction and adversarial review {#source-review}

The issue scenario was independently reproduced against the reviewed SILO source with a single-node server and SigV4 requests. Additional probes established that:

- an exact object key can paginate its own uploads;
- `upload-id-marker` currently affects that exact-key path even without `key-marker`, contrary to AWS;
- `NextKeyMarker` remains empty on an exact-key truncated page;
- `max-uploads=0` behaves as unlimited in the current path;
- a plain server restart empties the bucket-wide view while exact-key lookup still finds the on-disk uploads.

A second adversarial architecture review challenged the storage, quorum, migration, suspended-pool, mixed-version, and performance assumptions. The corrections from that review are incorporated below; this record does not treat an AI review as a substitute for code tests or an AWS conformance capture.

## What the code actually does {#current-behavior}

### Empty prefix: a volatile node-local view {#empty-prefix}

With no prefix, the pool layer returns every `MultipartInfo` for the bucket from `mpCache`, sorted only by initiation time. It does not apply `max-uploads`, `key-marker`, `upload-id-marker`, or `delimiter`, and it does not compute continuation markers or `IsTruncated`.

The cache is initialized empty at process startup. Creation populates only the node that handles the request. Completion and abort delete cache entries, including peer notifications in some paths, but creation has no equivalent durable cluster-wide population or startup rebuild. Consequently:

- a restart can change a non-empty listing into an empty one;
- two nodes can return different answers for the same bucket;
- a successful response is not evidence that the server has enumerated durable upload state.

### Non-empty prefix: an exact object lookup {#nonempty-prefix}

With a non-empty prefix, the string is passed through object hashing as though it were a complete object name. One erasure set is selected, and listing reads the directory derived from `sha256(bucket/object)`.

This path can enumerate multiple upload IDs for that exact object. It sorts them by initiation time, applies its `upload-id-marker`, stops at `max-uploads`, and sets `IsTruncated`. It still does not implement lexical prefix matching, `CommonPrefixes`, general key-marker semantics, or `NextKeyMarker`.

### Multiple pools make pagination less correct {#multiple-pools}

For a non-empty request on a multi-pool deployment, the pool layer invokes each active pool with the same maximum and concatenates the results. It does not perform a global ordered merge or recompute page boundaries and next markers. A request for `N` items can therefore collect up to `N` from each pool.

Suspended pools are skipped by listing and by the other public multipart verbs. In-progress uploads left on a suspended or decommissioning pool are therefore inaccessible, not merely unlisted. That is a related lifecycle defect, but listing alone must not advertise handles that `PutObjectPart`, `ListParts`, `CompleteMultipartUpload`, and `AbortMultipartUpload` cannot use. Pool drain or forced abort should be designed as a separate cross-verb change.

## Why current uploads cannot be backfilled {#no-backfill}

The multipart namespace is flat:

```text
.minio.sys/multipart/<sha256(bucket/object)>/<upload-id>/xl.meta
```

The hash is one-way. The original bucket and key are not encoded in the path. They are also not stored as a name field in the current multipart `xl.meta`; the supplied object name only influences the erasure distribution during `newFileInfo` construction.

Therefore an all-directory scan can discover that an upload exists, but it cannot determine which bucket or key it belongs to. The current node-local cache cannot repair this reliably because it is incomplete across nodes and disappears on restart.

This rules out a tempting "small" fix: scanning every existing `xl.meta` and applying prefix filters. New identity metadata or a durable index is required, and old keyless uploads need an explicit migration policy.

## Complexity assessment {#complexity}

The semantic algorithm is not the hardest part. The hard part is obtaining a complete, quorum-valid, globally ordered input set without turning a listing call into an uncontrolled cluster-wide metadata storm.

| Area | Complexity | Why |
| --- | --- | --- |
| Pure S3 filtering and pagination | Medium | Rules are finite, but marker and delimiter edge cases need captured AWS evidence. |
| Persisting bucket/key in new upload metadata | Medium | It reuses an existing quorum write, but completion, rollback, healing, and replication compatibility must be tested. |
| Candidate discovery | High | The namespace mixes every bucket and duplicates each upload across erasure drives. One-disk discovery can miss quorum-valid uploads. |
| Quorum and concurrent deletion | High | A scan must reject minority ghosts while tolerating abort, completion, GC rename-to-trash, and transient `ENOENT`. |
| Multi-pool global pagination | High | Results must be merged, sorted, truncated, and marked once across all accessible pools and sets. |
| Rolling migration | High | Old writers keep creating keyless uploads; old completers may preserve unknown internal metadata. |
| Performance and resource control | High | A bucket request may require inspecting every active upload in the cluster, not only that bucket. |

Overall, this is a high-complexity compatibility project with medium wire-compatibility risk and high implementation-correctness risk. It is not a destructive object-format migration: the recommended design adds internal metadata for new incomplete uploads and leaves the existing directory scheme in place.

## Compatibility and operational impact {#impact}

### Wire behavior changes {#wire-impact}

A correct implementation deliberately changes observable results:

- `prefix=foo` will match `foo`, `foobar`, and `foo/...`, not only the exact key `foo`;
- bucket-wide results will be ordered by key and initiation time rather than only initiation time;
- `max-uploads` will actually limit a page;
- the default and maximum will move from SILO's current 10,000 constant toward the AWS limit of 1,000, subject to the captured edge-case contract;
- clients must follow `NextKeyMarker` and `NextUploadIdMarker` instead of assuming one response contains everything;
- delimiter requests will return `CommonPrefixes`;
- the current handler-side `501` for a marker outside the prefix will be replaced by the captured AWS semantics.

These are compatibility fixes, but they can break software that accidentally depends on SILO's old non-S3 behavior. In particular, a client that ignores pagination may see fewer entries after the repair. Strict behavior should therefore be introduced through an explicit release and rollout contract, not silently slipped into an unrelated patch.

### Storage-format compatibility {#storage-impact}

The recommended write path adds the bucket and object key as reserved internal metadata inside the new upload's existing quorum-written `xl.meta`. It does not rename multipart directories or create a second transactional write.

Before `CompleteMultipartUpload` renames upload metadata into the completed object, the new upload-only fields must be removed alongside the multipart checksum fields that are already stripped there.

An old binary completing an upload created by a new binary will not know to remove the new internal keys. They would remain inert and hidden from S3 user metadata, but persist in the completed object's internal metadata. Rolling-upgrade tests must prove that unknown reserved keys do not disturb healing, replication, metadata comparison, or downgrade reads. The product must then choose between tolerating that residue and adding a scrubber; it must not assume the keys disappear.

### Operational cost {#operational-impact}

Because all buckets share one flat hash namespace, an on-demand scan is `O(all active multipart uploads in the cluster)`, not `O(uploads in the requested bucket)`. Bounded parallelism, cancellation, memory limits, and failure behavior are part of correctness, not optional tuning.

Default SILO configuration expires stale multipart uploads after 24 hours and runs cleanup every 6 hours. Once the last old writer has been upgraded, the keyless population should normally drain within roughly 30 hours. Operators with a larger custom expiry have a longer migration window. A zero value is mapped back to the 24-hour default in the current code; no supported "disabled" expiry value was identified in this review.

The collector bounds default storage accumulation, but does not repair a false listing response. It also does not remove the need to test sustained legitimate multipart activity, failure modes, and custom expiry settings.

### Severity {#severity}

The recommended classification is **P1 / high compatibility**, not P0:

- no committed object data loss was demonstrated;
- no security boundary is bypassed;
- unfinished uploads remain on disk until completed, aborted, or collected;
- default stale-upload cleanup bounds accumulation in the ordinary configuration.

It remains high rather than medium because the server returns fabricated success, the answer changes after restart or node switching, and cleanup or quiescence tooling can be misled into false confidence.

## Options considered {#options}

### Option 0: leave the current behavior unchanged {#option-zero}

This has no engineering cost and preserves every accidental behavior. It also preserves false `200 OK` responses, node-local inconsistency, restart volatility, broken prefix cleanup, and an inaccurate impression of S3 support.

This option is acceptable only if SILO deliberately downgrades the public compatibility claim and treats the endpoint as unsupported. Even then, silently returning an incomplete success is inferior to explicit rejection.

**Decision: reject as a long-term position.**

### Option 1: explicit documented divergence {#option-divergence}

Reject combinations that SILO cannot honor with a stable `NotImplemented`-class error and document the exact supported subset. This is operationally honest and much smaller than full compatibility.

It is still a breaking change: tools that currently receive an empty or unbounded `200 OK` may begin failing jobs. It also does not produce an S3-compatible endpoint. The error behavior and default release policy must be deliberate.

**Decision: acceptable short-term containment if full compatibility is declined or deferred; not a compatibility fix.**

### Option 2: persist identity, scan durable state, optionally cache {#option-scan}

For each new upload, store the bucket and key in reserved internal metadata in the upload's existing `xl.meta`. For listing, discover upload directories across accessible pools and sets, validate candidates with erasure read quorum, then run one global S3 semantic layer. A cache may accelerate this path only if it can be rebuilt and reconciled from durable state.

This avoids a second write transaction and keeps the directory layout stable. Its principal cost is the cluster-wide scan.

**Decision: recommended, subject to a performance and failure-mode spike.**

### Option 3: durable bucket-scoped ordered index {#option-index}

Maintain a secondary index ordered by bucket, key, and upload identity. Listing becomes scalable and naturally paginable, but create, complete, abort, healing, rollback, and reconciliation must keep two locations consistent across failures. The design resembles multipart index structures that upstream MinIO deliberately removed while simplifying this subsystem.

**Decision: no-go unless measurements show that Option 2 cannot meet the product-approved service-level objective.**

### Rejected variant: repair only `mpCache` {#option-cache-only}

Filtering, sorting, paginating, broadcasting creates, or rebuilding the current cache would improve symptoms but would not by itself establish a durable quorum-valid source of truth. A cache-only patch risks producing a more convincing but still incorrect answer.

**Decision: reject. A cache can optimize a correct read path, never define it.**

## Recommended design {#recommended-design}

### 1. Freeze the public contract first {#contract-first}

Create a recorded AWS fixture suite for general-purpose buckets covering:

- ordering across keys and multiple uploads of one key;
- equal initiation times and a deterministic total-order tie-break;
- prefix and exact-key overlap;
- key-marker with and without upload-id-marker;
- upload-id-marker without key-marker;
- delimiter, `CommonPrefixes`, and page accounting;
- `max-uploads` omitted, 0, 1, 1,000, and greater than 1,000;
- `encoding-type=url`;
- empty pages, final pages, and next-marker values.

The captured responses should become repository fixtures. CI should not depend on live AWS access.

### 2. Persist recoverable identity in the existing write {#write-path}

At `NewMultipartUpload`, add reserved internal metadata for the canonical bucket and object key before the existing `writeAllMetadata` quorum write. The exact key names are an implementation detail, but they must be versioned, unambiguous, size-bounded by the existing object-key limits, and excluded from client-visible metadata.

At successful completion, delete those upload-only keys before copying `fi.Metadata` into the final object metadata and before `renameData`. Abort and stale cleanup already delete the entire upload directory and need no separate index operation.

### 3. Separate discovery from validation {#read-path}

Candidate discovery and candidate validity are different questions.

For every accessible, non-suspended pool and set:

1. list candidate hash and upload directories from all online drives required by the configured list-quorum policy;
2. union and deduplicate those names;
3. read the candidate `xl.meta` through the normal erasure metadata machinery;
4. include the upload only when its metadata is quorum-valid and contains a valid bucket/key identity;
5. tolerate a candidate disappearing during abort, completion, or stale cleanup;
6. under strict list quorum, fail the request rather than return a partial `200 OK` when a required set cannot be evaluated.

Using the first healthy disk for discovery is insufficient: that disk may have been offline when a still-quorum-valid upload was created.

### 4. Apply semantics once, globally {#semantic-layer}

Feed the validated candidates from all pools and sets into a pure semantic layer. The layer owns bucket filtering, prefix, delimiter grouping, ordering, markers, maximum-page accounting, URL encoding, `IsTruncated`, and next markers.

Pool-local limits and markers must not be applied before the global merge. The result should be deterministic under duplicate discovery and independent of which node handles the request.

### 5. Preserve the internal exact-object operation {#exact-helper}

`erasureServerPools.NewMultipartUpload` currently calls `ListMultipartUploads(bucket, object, ...)` to keep another upload for the same object in the same pool. If the public function starts treating that argument as a lexical prefix, `foo` could match `foobar` and select the wrong pool.

Introduce a narrowly named internal helper such as `FindMultipartUploadPool` or `ListMultipartUploadsExact`. It should use the existing object hash path and must not share the public prefix semantics.

### 6. Treat cache as an optimization {#cache}

The existing `mpCache` may be removed. If retained, it must satisfy all of the following:

- durable state remains authoritative;
- startup can rebuild it;
- create, complete, and abort updates are propagated consistently;
- reconciliation detects missed events and stale entries;
- a cold or divergent cache falls back to the quorum-valid scan;
- correctness tests pass with the cache disabled.

### 7. Gate strict behavior through rolling migration {#migration}

Legacy upload records lack bucket/key identity and cannot be reconstructed reliably. Use two externally meaningful modes:

- **legacy mode**, the initial upgrade default: new writers persist identity; keyless uploads are counted and drained; the documented response policy for a mixed keyed/keyless population must be selected explicitly;
- **strict mode**: activation requires every writer node to advertise the new metadata capability and the observed keyless count to be zero. Discovering a keyless upload afterward is an error with anomaly telemetry, not a silent omission.

A short shadow comparison can help validate the new scanner, but a permanent third operating mode is unnecessary unless the spike finds a need. With default expiry, the expected legacy drain is about one day plus one cleanup interval after the last old writer stops.

There is one unresolved product choice in legacy mode:

| Policy | Advantage | Cost |
| --- | --- | --- |
| return the complete keyed subset with documented telemetry | keeps tools operating during the bounded drain | still returns an incomplete `200 OK` that ordinary clients cannot see is incomplete |
| fail listing while any keyless upload exists | never fabricates completeness | can block cleanup and existing jobs throughout the drain window |

This choice belongs in the ADR. Strict mode has no such ambiguity: it must fail loud if its precondition is violated.

### 8. Keep suspended-pool lifecycle separate {#suspended-pools}

Listing should initially mirror the accessibility contract of the other multipart verbs and scan non-suspended pools. Adding suspended-pool entries to listing alone would expose uploads that cannot be extended, completed, or aborted.

Open a separate lifecycle design for in-progress uploads when a pool drains: either keep all multipart verbs available until the uploads finish, migrate them, or force-abort them under a documented policy. Do not hide that problem inside #79.

## Performance spike and decision rule {#spike}

Option 2 is preferred because it has one durable write location, but its scan cost must be measured rather than assumed.

Generate 1,000, 10,000, and 100,000 active uploads across a matrix of pools, sets, and drive counts. Measure:

- cold and warm p50/p95/p99 latency;
- total and per-drive `ListDir` operations;
- metadata-read and internode RPC counts;
- peak memory and allocation volume;
- cancellation latency;
- behavior with slow, offline, healing, and intermittently disappearing drives;
- simultaneous create, complete, abort, and stale cleanup;
- first-page and deep-page cost with selective and empty prefixes.

The acceptance threshold is a product decision and must be recorded before interpreting the result. A guessed one- or two-second target is not evidence. If the scan meets the approved target with bounded resource use, reject Option 3. If it does not, use the measurements to design the smallest durable index that solves the demonstrated bottleneck.

## Test and release gates {#gates}

### Semantic and unit tests {#unit-tests}

- pure table tests generated from recorded AWS fixtures;
- ordering, marker, delimiter, encoding, truncation, and maximum-edge coverage;
- property tests ensuring pagination returns each logical upload exactly once;
- deterministic behavior with duplicate candidates and equal timestamps.

### Object and handler tests {#handler-tests}

- strengthen the existing object-layer table to assert uploads, common prefixes, markers, and truncation;
- parse and validate handler XML bodies instead of checking only status codes;
- verify default and invalid `max-uploads` handling;
- test exact-helper pool selection independently of public prefix semantics.

### Distributed and failure tests {#failure-tests}

- restart equivalence and node-switch equivalence;
- multiple sets and pools with a single global page boundary;
- candidate missing from one drive but present at quorum;
- minority ghost after partial abort;
- concurrent completion and GC rename-to-trash;
- unavailable set under every supported `list_quorum` policy;
- rolling upgrade, old-writer reintroduction, downgrade completion, and strict-mode gating;
- unknown internal metadata under healing and replication.

### Delivery gates {#delivery-gates}

1. approve the ADR, including product mode and performance SLO;
2. commit the captured conformance fixtures;
3. complete and review the storage spike;
4. implement and pass focused, full, race, and failure QA;
5. update the S3 compatibility reference and operational guidance;
6. commit and merge the source change;
7. build and identify the release artifact or container image;
8. canary a rolling upgrade and observe keyless-drain telemetry;
9. enable strict mode only after its gates hold;
10. verify the live endpoint before closing #79.

Passing an earlier gate is not evidence that a later gate happened.

## Final recommendation: fix it, but do not rush it {#final-recommendation}

Leaving the current endpoint indefinitely is the wrong trade-off. This is not an obscure response-field mismatch: it affects discovery and cleanup of unfinished data, returns successful but false answers, and changes behavior across nodes and restarts. Those properties undermine the practical meaning of S3 compatibility.

At the same time, a direct implementation patch is also the wrong trade-off. The current disk layout cannot identify legacy uploads, a correct scan needs erasure-aware discovery and quorum, and wire-correct pagination changes observable client behavior.

The balanced decision is:

- **GO** for the ADR, AWS fixture capture, metadata-plus-scan prototype, and performance/failure spike;
- **GO conditionally** for Option 2 after the product SLO and legacy response policy are approved;
- **NO-GO** for a cache-only repair, an immediate durable secondary index, strict-by-default behavior in a patch release, or closing the issue before rolling-upgrade reachability is demonstrated;
- if implementation capacity is unavailable, **GO** for an explicit documented divergence and stable error behavior rather than continuing to fabricate successful listings.

This preserves compatibility discipline without pretending that a high-risk distributed listing change is a two-line bug fix.
