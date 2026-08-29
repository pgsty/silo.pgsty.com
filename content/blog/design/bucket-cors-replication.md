---
title: "Per-Bucket CORS: Making Deletes and Recovery Converge"
linkTitle: "Bucket CORS Replication"
date: 2026-08-28
lastmod: 2026-08-28
author: "Ruohang Feng"
summary: >
  SILO accepted per-bucket CORS through PR #71, then found that a missed or reordered site-replication event could restore a deleted browser-origin rule. This record explains the problem in plain language, the merge decision, two rounds of adversarial review, the source-timestamp and tombstone repair, S3 response cleanup, costs, rejected alternatives, historical follow-ups, and the release gate tracked by issue #75.
tags: [Design, S3, CORS, Replication, Compatibility]
weight: 32
draft: false
url: "/blog/design/bucket-cors-replication/"
---

This document records the problem, review, merge decision, adversarial debate, and final implementation contract for [SILO PR #71](https://github.com/pgsty/silo/pull/71) and the release-hardening work tracked by [SILO #75](https://github.com/pgsty/silo/issues/75).

> **Status:** PR #71 merged as [`e4e3007da`](https://github.com/pgsty/silo/commit/e4e3007da6d7d1198a6a050e34f84566d40a9654). The B2 convergence repair is commit [`724f8703d`](https://github.com/pgsty/silo/commit/724f8703d83f4c51859c7650b7f1da2c2a55548c) in [PR #80](https://github.com/pgsty/silo/pull/80), whose initial eight DCO, CI, race, cross-compile, and vulnerability checks passed. The final B2+B3 code is signed commit `0eebc928f`; combined Opus findings are fixed, full tagged/race/build/vet/lint/compatibility gates pass, and a real local two-site offline-DELETE/heal/restart test plus raw SigV4 B3 probes pass. The EN/ZH records pass a warning-fatal Hugo build, rendered link checking, and local browser QA. Issue #75 remains a release gate: nothing is merged, tagged, packaged, published as an image, deployed, or production-verified.<br>
> **Owner:** [`pgsty/silo`](https://github.com/pgsty/silo) owns the server changes. This public design record belongs to [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com). Console UI remains a separate deliverable.<br>
> **Decision:** accept the useful feature, preserve the contributor's work, and block release until site-replication deletes, recovery, wildcard responses, and the narrow protocol follow-ups converge correctly.

## The problem and solution in plain language {#plain-language}

Before PR #71, SILO could set CORS only for the whole cluster. A browser application could not say, “allow this website to use bucket A, but not bucket B.” Standard S3 calls for reading, writing, and deleting a bucket's CORS configuration existed as stubs and returned `NotImplemented`.

PR #71 added the missing feature. A bucket can now store its own allowed websites, HTTP methods, request headers, exposed response headers, and preflight cache time. Standard S3 clients can manage the configuration, and buckets without one keep the old global behavior.

The core feature works. The remaining problem appears when the same bucket is replicated between sites.

Imagine an administrator allows `https://old.example.com`, then removes that permission. SILO correctly deletes the rule on the first site. If another site temporarily misses that delete, the recovery process must later learn that “deleted at 10:05” is newer than “configured at 10:00.” The current code sometimes forgets the deletion time or replaces the source time with the time at which a peer received the message. Recovery can then mistake the old live rule for the newest state and restore it.

The fix is not a new replication system. A deleted configuration is represented by the data SILO already has:

```text
configuration = absent
updated time  = time of DELETE
```

That pair is a deletion **tombstone**. The repair preserves the source timestamp for both PUT and DELETE, carries the timestamp even when no XML remains, and makes recovery use the same CORS apply path as normal peer delivery. Older events can no longer revive a newer deletion.

The direct cost is bounded: a CORS-specific distributed namespace lock and monotone state transition, focused ObjectLayer tests, strict wire validation, response-compatibility fixes, and operational documentation. There is no new storage field, dependency, feature flag, distributed clock, or general replication framework. The continuing cost is that SILO owns these tests and the bucket-CORS compatibility contract. Site replication still relies on synchronized wall clocks, as it already did.

CORS is not IAM authorization. A stale CORS rule does not grant an S3 permission that a principal lacks. It can, however, let a browser origin continue reading an already-authorized cross-origin response after an administrator intended to revoke that browser access. That is why convergence is a release blocker rather than cosmetic polish.

## What PR #71 added {#feature}

PR #71 replaced the inherited Bucket CORS stubs with a cohesive feature:

- standard `PutBucketCors`, `GetBucketCors`, and `DeleteBucketCors` APIs;
- Content-MD5 or supported checksum validation on PUT;
- XML parsing and validation for origins, methods, allowed headers, exposed headers, rule IDs, and max age;
- raw XML persistence in `BucketMetadata` with a CORS update timestamp;
- per-bucket OPTIONS preflight handling and actual-response CORS headers;
- the existing global CORS policy as a fallback only for buckets without a per-bucket configuration;
- normal site-replication send, receive, initial-sync, status, and heal wiring;
- unit, handler, middleware, metadata, and transport tests.

The local review rebased the feature onto the then-current `main`, built it, ran focused normal and race tests, full `cmd` tests, pinned lint, generated-file checks, compatibility checks, and a real `minio-go` smoke test. PUT, GET, DELETE, allowed and rejected preflights, `Vary`, and actual response headers all worked in the single-site path.

This evidence justified accepting the feature. It did not prove every failure-recovery path.

## The reproduced convergence failures {#reproductions}

Review-only tests against the real ObjectLayer reproduced the three failures
below. A later release review also proved that payload-only status comparison
kept different source-time barriers hidden, and that equal-timestamp conflicts
depended on arrival and map-iteration order.

### A newer DELETE can be ignored {#ignored-delete}

The peer handler used the ordinary metadata `Update` and `Delete` methods. Those methods assign `UTCNow()` on the receiving site. If an older PUT arrives late, its locally generated arrival time can appear newer than a later source DELETE, so the DELETE is discarded.

### An older PUT can revive a deletion {#resurrected-put}

`GetCorsConfig` returns not-found and a zero timestamp once the live config is nil. The deletion time still exists in raw bucket metadata, but the handler cannot see it through that getter. A stale PUT therefore passes the staleness check and restores the rule.

### Heal can select the stale live rule {#heal-resurrection}

`SiteReplicationMetaInfo` currently exports `CorsConfigUpdatedAt` only when CORS XML is present. After DELETE, the site reports nil configuration and zero time. A peer that still has the old XML reports a non-zero older time. Heal selects that old rule as “latest” and writes it back.

These are the same failure expressed at three seams: peer apply, metadata status, and recovery.

## The intended state model {#state-model}

Per-bucket CORS needs only the state already present in `BucketMetadata`:

| Logical state | XML | Timestamp | Meaning |
| --- | --- | --- | --- |
| Never configured | nil | zero | baseline; it is never transmitted or selected as a winner |
| Configured | non-nil | source PUT time | live per-bucket rule |
| Deleted | nil | source DELETE time | tombstone; newer than any earlier live rule |

The selected register uses a deterministic total order:

```text
1. source UpdatedAt
2. baseline < live < tombstone
3. equal-time live/live: lexicographic decoded payload bytes
```

Peer apply is a monotone join: it applies only a strictly greater state, so
retry and duplicate delivery are idempotent. A tombstone wins an equal-time
PUT/DELETE conflict, while two live values choose the same bytewise winner at
every site. `CreatedAt` is not the baseline marker; it is only the bucket-lineage
floor that rejects an event from an older bucket incarnation and emits a
bucket-scoped diagnostic.

## How the decision was made {#decision-history}

### Initial review {#initial-review}

The first review agreed that the need was real and the single-site architecture was reasonable, but found that site replication emitted CORS events without completing every receive, status, and recovery path. The contributor added the missing wiring, checksum validation, wildcard/ID limits, cache variation, and focused tests.

A second runtime review confirmed the normal single-site and direct replication paths, then reproduced the tombstone and source-time failures above. The feature was close enough to accept, but not safe enough to release as complete.

### Merge versus release {#merge-versus-release}

The maintainer chose to merge PR #71 and own the remaining hardening. This separated two decisions that are often confused:

1. Is the contribution valuable and structurally sound enough to accept? **Yes.**
2. Is the resulting feature ready to tag, package, publish, and deploy? **Not until #75 closes.**

The merge triggered full `main` CI, which passed. Release and Docker publication remain manual, independent gates.

### Self-adversarial plan review {#self-review}

The first follow-up plan was intentionally comprehensive, then reviewed against four failure modes: overdesign, new problems introduced by the fix, failure to reuse existing infrastructure, and disproportionate maintenance cost.

That review removed or deferred:

- a new general metadata-apply abstraction;
- a custom wildcard matcher;
- broad policy/tag/SSE/quota refactoring;
- a multi-process site-replication test lab;
- method-case, Unicode-ID, and trailing-XML strictness without differential evidence;
- a no-Origin hot-path optimization that could alter existing `Vary` behavior;
- vector clocks, a new tombstone field, and a global timestamp redesign.

### Independent Claude Opus 5 reviews {#claude-review}

Four read-only local Claude Code reviews used canonical `claude-opus-5` at
maximum effort. They moved the design from a timestamp-only patch to the final
zero-baseline, deterministic C-prime register; required the distributed CORS
lock and monotonic local barrier; made status and heal compare full state; and
closed strict base64, semantic validation, cache, `Vary`, wildcard credentials,
and initial-sync tombstone gaps.

The combined B2+B3 review then checked the strict parser, exact method and
Unicode-ID contract, MaxAge presence, Origin-null forwarding marker, checksum
classification, and replication/restart behavior together. It found a test
helper conflict and the upgrade risk that a document accepted by a lenient
development build could make all bucket metadata unavailable. The helper was
corrected. Legacy-invalid CORS now leaves other bucket metadata readable,
fails browser behavior closed, rejects new invalid saves, and remains
repairable by a valid CORS PUT or DELETE.

## Design goals and non-goals {#scope}

### Goals {#goals}

- make CORS PUT and DELETE converge under duplicate, delayed, reordered, and missed events;
- preserve exact source timestamps on peer apply and heal;
- let a newer nil tombstone beat an older live config;
- avoid widening a configured bucket to global CORS on metadata failure;
- align literal wildcard, credentials, exposed headers, and cache variation with S3 behavior;
- correct the new CORS status count and the narrow validation gaps proven by existing matcher behavior;
- keep the repair independently reviewable and reversible.

### Non-goals {#non-goals}

- redesign every bucket metadata replication handler;
- solve distributed clock skew or same-timestamp multi-writer conflicts globally;
- add a new metadata schema, event log, queue, general metadata lock, or feature flag;
- build a permanent multi-site process lab;
- tighten unrelated XML or validation paths without evidence;
- add Console UI;
- mix historical Object Lock, tag, SSE, policy, quota, or versioning repairs into this branch.

## Final repair design {#design}

### Commit 1: preserve tombstones and source order {#commit-1}

The CORS replication handler remains the single place for explicit peer CORS events.

Under a CORS-specific distributed namespace lock it will:

1. require a non-empty bucket and non-zero source timestamp;
2. require existing bucket metadata rather than fabricating it;
3. read raw `CorsConfigUpdatedAt`, including a timestamp whose live config is nil;
4. reject an event before the bucket lineage and ignore any state not strictly greater under the total order;
5. strictly decode and validate a non-nil CORS payload or treat nil as DELETE;
6. set `CorsConfigXML` and `CorsConfigUpdatedAt` directly from the source event, preserving the exact source barrier;
7. persist through `BucketMetadataSys.save`, preserving the existing disk, cache, notification, and peer-node refresh path.

The legacy/default multi-field path may carry a non-nil CORS snapshot, so it
uses the same lock, strict validation, and join; typed deletes continue through
the CORS-specific handler. `SiteReplicationMetaInfo` always exports the source
timestamp and encodes XML only when present. Status compares kind, decoded
payload, and timestamp. Heal chooses the deterministic maximum and pushes it
through the same transition, including when only the timestamp differs.

The zero baseline is deliberately not defaulted to bucket creation. Initial
sync sends live and tombstone states but omits baseline. Local PUT and DELETE
choose a timestamp strictly after `max(UTCNow, CreatedAt, current barrier)`.

### Commit 2: fail closed and match S3 responses {#commit-2}

The middleware currently falls back to global CORS for every `GetCorsConfig` error. The repair distinguishes two cases:

- true no-config: use the global policy, preserving existing behavior;
- another metadata error on a request with `Origin`: log once and call the underlying S3 handler without global CORS headers.

This is fail-closed for browsers without converting a metadata problem into a new server-wide 500 contract. A failed preflight reaches the router's ordinary non-CORS error response. Requests without `Origin` keep the existing middleware path; there is no speculative hot-path optimization.

Successful preflights also return configured `Access-Control-Expose-Headers`, which the [S3 OPTIONS contract](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/RESTOPTIONSobject.html) lists explicitly.

Origin matching will return the actual matched pattern. Response behavior is:

| Matched origin element | `Access-Control-Allow-Origin` | `Access-Control-Allow-Credentials` |
| --- | --- | --- |
| `*` | `*` | omitted |
| exact origin | request origin | `true` |
| pattern such as `https://*` | request origin | `true` |

This matters when a rule contains both a specific origin and `*`: response semantics follow the first origin element that actually matched, rather than merely noticing that the rule contains a wildcard somewhere.

The three cache dimensions are set before the preflight match result, so both 200 and 403 responses vary by Origin, requested method, and requested headers.

### Commit 3: narrow validation and status cleanup {#commit-3}

The site summary increments `TotalCorsConfigCount` from the current site's `s.CorsConfig != nil`, not from a cumulative count that may already include an earlier site.

Validation rejects:

- an empty allowed origin;
- `?`, because the reused generic matcher treats it as a wildcard while S3 documents only a single `*` wildcard.

The implementation keeps the existing matcher and at-most-one-`*` rule. It does not change method case handling, ID character counting, or trailing XML behavior.

The handler test suite adds missing and mismatched Content-MD5 cases. That test exposed another concrete bug: the handler wrapped the checksum reader in an exact-`ContentLength` `LimitReader`, which returned EOF before the checksum wrapper could report a mismatched digest. After the existing positive and 64 KiB ContentLength guards, the handler now reads the wrapped request body to EOF directly. This preserves the shared `validateLengthAndChecksum` implementation and makes `BadDigest` observable without adding a second checksum path.

### Commit 4: operator notes {#commit-4}

The in-repository note records:

- bucket CORS overrides rather than merges with global CORS;
- DELETE restores global fallback;
- an older binary does not enforce the new configuration;
- an older binary rewriting bucket metadata may drop the unknown CORS fields;
- an older peer harmlessly no-ops an unknown CORS event, then converges through heal after upgrade;
- site replication still depends on synchronized clocks.

Public operational documentation remains a separate documentation-repository deliverable, represented by this record and any later task-oriented reference updates.

## Test design {#tests}

The tests exercise real state transitions without creating a permanent multi-process lab.

| Test seam | Required cases |
| --- | --- |
| Peer apply with ObjectLayer | delayed PUT then newer DELETE; stale PUT after tombstone; duplicate delivery; exact source timestamps; missing metadata returns an error and creates no record |
| Transport-to-apply | retain the existing JSON nil/non-nil round trip; feed at least one JSON-decoded event into the real peer handler |
| SiteReplicationMetaInfo | nil config still carries the DELETE timestamp; pre-feature zero timestamp defaults to Created |
| Heal | newer nil tombstone beats older live XML; local state becomes nil with the exact tombstone time |
| Middleware errors | no-config uses global fallback; another metadata error gives actual and preflight responses no global CORS headers |
| Origin responses | exact, literal `*`, patterned, and mixed-origin rules; credentials only when permitted |
| Preflight | expose headers; allowed headers; max age; three `Vary` fields on success and rejection |
| Validation and handler | empty origin, `?`, missing Content-MD5, mismatched Content-MD5 |

The full admin-auth dispatch is not given its own integration fixture. It is a two-line switch already covered by compilation and review; the wire and real handler seams carry the meaningful state-machine risk. Startup's concrete `errBucketMetadataNotInitialized` value is not frozen in a dedicated test; a representative non-not-found metadata error covers the middleware decision.

## Rejected alternatives {#rejected}

### Put CORS tombstone logic in the generic metadata merger {#reject-generic-handler}

Rejected because it would give one field special nil, staleness, and early-return semantics inside a seven-field merge function. The CORS-specific handler already exists and is the smaller boundary.

### Add a new timestamp-aware metadata abstraction {#reject-helper}

Rejected until at least two metadata types demonstrate identical requirements. A general helper today would encode assumptions about delete semantics that differ across policy, tag, SSE, object lock, quota, and versioning.

### Add a physical tombstone field or event journal {#reject-schema}

Rejected because `(nil config, DELETE timestamp)` already represents the required state. A new schema increases downgrade and migration cost without adding information.

### Replace wall clocks with a distributed ordering system {#reject-clock-redesign}

Rejected as disproportionate and inconsistent with existing site replication. Correctly preserving source time restores the current contract; it does not solve global clock skew.

### Build a full multi-site test lab {#reject-lab}

Rejected because the failures are local state-machine defects and every important seam is directly testable in process. A lab would be slower, more brittle, and harder to diagnose.

### Write a custom CORS wildcard matcher {#reject-matcher}

Rejected because input validation can constrain the existing matcher to the S3-supported single-`*` language. Reimplementing matching creates more boundary cases than it removes.

### Tighten every validation edge now {#reject-strictness}

Rejected because uppercase-only methods, Unicode ID counting, and trailing-document rejection could change accepted inputs without evidence that they affect security or real client compatibility.

### Fix every neighboring replication issue in the same branch {#reject-scope-expansion}

Rejected because shared-looking code does not prove shared semantics. Historical problems receive their own reproduction, issue, review, and release boundary.

## Costs, benefits, and remaining risks {#tradeoffs}

### Benefits {#benefits}

- standard S3 Bucket CORS works for browser applications and common SDKs;
- buckets can use narrower origin policies than the cluster-wide fallback;
- normal delivery, missed events, reorder, retry, and heal converge on the same state;
- a revoked browser origin cannot be restored merely because a peer missed DELETE;
- error handling cannot silently widen a configured bucket to global CORS;
- wildcard and credentials behavior matches the established S3 client expectations.

### Implementation and maintenance cost {#costs}

The production changes remain local to bucket metadata timestamps, CORS peer apply/heal/status, CORS middleware, and CORS validation. The largest addition is regression coverage, because state convergence must be proven on both supported ObjectLayer test backends.

No new dependency, service, configuration key, storage field, background worker, or cross-repository server dependency is introduced. The ongoing cost is maintaining the S3 compatibility matrix, source-timestamp tests, and documentation.

### Remaining risks accepted by design {#remaining-risks}

- wall-clock ordering assumes synchronized site clocks;
- equal timestamps use a CORS-local deterministic tie-breaker rather than a global replication redesign;
- mixed-version operation is unsupported for CORS writes; all sites must upgrade before the feature is enabled;
- an old binary may ignore or later drop CORS metadata during rollback writes;
- full Console management remains absent;
- inherited replication defects outside CORS remain separate work.

These are visible constraints, not hidden claims of perfect parity.

## Historical follow-ups kept separate {#follow-ups}

Adversarial review confirmed one unrelated defect in the existing initial-sync path: an Object Lock event is constructed with `SRBucketMetaTypeObjectLockConfig` but stores its payload in `Tags` instead of `ObjectLockConfig`. That requires a dedicated issue and fix.

Neighboring site summaries also use cumulative counters, and policy/tag/SSE/quota/versioning peer handlers may share source-time or tombstone weaknesses. The follow-up policy is:

1. reproduce each behavior independently;
2. open a focused issue with the affected metadata contract;
3. do not modify it in the CORS branch;
4. consider a shared helper only after at least two types require the same semantics.

This keeps historical cleanup honest without turning a bounded CORS repair into a site-replication rewrite.

An event earlier than local `CreatedAt` is ignored as belonging to an older
bucket incarnation and logged once with a bucket-scoped key. Status keeps the
mismatch visible; removing the floor would risk applying an old CORS grant to
a newly recreated bucket.

## Compatibility impact {#compatibility}

| Existing user or deployment | Expected impact |
| --- | --- |
| No bucket CORS configured | existing global CORS behavior remains |
| Single-site bucket CORS | standard control plane and enforcement remain; response fidelity improves |
| Site replication without bucket CORS | no behavioral change |
| Site replication with bucket CORS | source ordering, DELETE, retry, and heal become reliable |
| Raw PUT caller | must send the S3-required Content-MD5 or supported checksum |
| Older peer | no-ops unknown CORS events until upgrade; heal converges afterwards |
| Downgrade | bucket CORS is not enforced; metadata may be lost if an old binary rewrites the record |
| Console-only operator | no CORS editor yet; use SDK, CLI, or S3 API |

The stricter empty-origin and `?` validation lands before any SILO release containing PR #71, so there is no released SILO bucket-CORS configuration population to migrate across that change.

## Verification and release gates {#release-gates}

The repair is complete only when all of the following are independently true:

1. focused replication, middleware, validation, and handler tests pass;
2. focused race tests pass;
3. full `cmd` tests pass;
4. `go build ./...`, pinned lint, generated-file checks, and compatibility checks pass;
5. the standard `minio-go` PUT/GET/DELETE and preflight smoke test passes;
6. an independent adversarial review finds no unresolved blocker;
7. the follow-up server PR is committed, pushed, reviewed, and merged;
8. its PR CI and the resulting `main` CI are green;
9. the documentation build and bilingual link checks pass;
10. release tag, packages, image publication, deployment, and production verification are completed as separate gates.

Until then, issue #75 remains open and no release or Docker image should advertise per-bucket CORS as release-ready.

## Conclusion {#conclusion}

Per-bucket CORS solves a real compatibility and browser-isolation problem, and PR #71's core implementation was worth accepting. The remaining defect is not a reason to discard the feature; it is a reason to state the replication model precisely and finish it before release.

The final design preserves the source timestamp and nil tombstone through normal peer apply, status, and heal; fails closed without turning CORS metadata errors into a new S3 outage; fixes literal wildcard and cache behavior; and keeps validation changes evidence-based. It reuses the existing CORS handler, bucket metadata, save path, matcher, and ObjectLayer tests. It adds no general framework and does not pull unrelated historical repairs into the branch.

That is the minimum complexity needed to make the merged feature sufficient, safe, and maintainable.
