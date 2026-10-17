---
title: "Clearing Stale Fields in Legacy Metadata and Scanner Responses"
linkTitle: "Stale Metadata Reuse"
date: 2026-10-15
lastmod: 2026-10-15
author: "Ruohang Feng"
summary: >
  PR #233 fixes fields carried over when legacy xl.meta headers and namespace-scanner responses are reused. This record explains the triggers, observed impact, local reset strategy, deterministic regression tests, distributed scanner verification, and release boundary.
tags: [Design, Reliability, Storage, Scanner]
weight: 95
draft: false
url: "/blog/design/stale-metadata-reuse/"
---

> [!WARNING]
> **Release-status correction (2026-10-17):** SILO `RELEASE.2026-10-15T00-00-00Z` was returned to Draft and is not the current public release; the published Server remains 20260916. Historical statements below that 20261015 is published or downloadable are superseded, and its fixes must not be treated as delivered in a public release. 20261018 is being prepared as a tag and draft only. See the [component matrix](/compatibility/versions/) and [download page](/download/).

**Release follow-up (2026-10-15):** This repair first shipped in [Server 20261015](/blog/release/silo-20261015/). The source acceptance below records the earlier pre-release verification.

**Verified on 2026-10-15: merged on main, not yet in a published Server release.**
[PR #233](https://github.com/pgsty/silo/pull/233) was merged as
[`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a).
The tested PR head is
[`86c5a92eef3d`](https://github.com/pgsty/silo/commit/86c5a92eef3d5667c83bdbc59a033b955bdbf146);
its source tree is identical to the merge commit. The latest published Server
at this check remains
[20260916](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-16T00-00-00Z),
whose source still contains both defects. A source merge does not update an
installed binary, package or container image.

## What went wrong {#problem}

Two independent paths reused a Go object without replacing all of its logical
state. Fields omitted from the next input retained values from the previous
use. The repair belongs at the point that knows which fields the new value
can contain.

| Path | Trigger | Incorrect state | Required state |
| --- | --- | --- | --- |
| Legacy V2 version header | Decode an old header into a structure with nonzero EC fields | `EcN` becomes zero, but `EcM` survives | Both absent EC fields are zero |
| Legacy V1 version header | Reuse a structure with a signature or EC fields | Fields absent from V1 survive | `Signature`, `EcN` and `EcM` are zero |
| Scanner update response | Reuse an envelope that previously held a final cache | Both `Update` and old `Final` are present | Only `Update` is present |
| Scanner final response | Reuse an envelope that previously held an update | Both old `Update` and `Final` are present | Only `Final` is present |

Here, **stale metadata** means a value carried over between uses. The evidence
establishes a correctness defect; it does not establish object-content loss,
cross-tenant disclosure or an unbounded memory leak. A usage discrepancy alone
does not identify this particular cause.

## Legacy xl.meta headers {#legacy-headers}

The version of the compact header inside `xl.meta` is distinct from the outer
file format version and the SILO release number. At the fixed commit, the
current header version is 3 and includes `EcN` and `EcM`. Legacy header V2 has
five fields and carries neither EC field. The V1 decoder handles a four-field
layout without a signature or EC fields; its source explicitly labels that
layout **never released**. V1 is therefore defensive coverage of a retained
decoder, not evidence of an affected released V1 deployment.

Both V2 entry points, byte-oriented `UnmarshalMsg` and stream-oriented
`DecodeMsg`, previously started with:

```go
z.EcN, z.EcN = 0, 0
```

The repeated destination left `EcM` untouched. A fresh zero-valued structure
hid the defect; reusing one with `EcN=4, EcM=8` produced `0,8` after a V2 decode.
The repair assigns `z.EcN, z.EcM = 0, 0`. The V1 path additionally clears its
absent `Signature` before decoding. Current V3 headers retain the EC fields
actually present on the wire.

This matters beyond a standalone decoder: `loadIndexed` can reuse the backing
slice of version headers. Resetting only a new allocation would leave that
path exposed. The committed regression explicitly exercises this reuse.
See the fixed [legacy decoders](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2-legacy.go)
and [indexed-header loading and comparison](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2.go).

The demonstrated result is a header that depends on its previous contents.
Header equality and vote counting include these fields, so differing stale
values can split otherwise identical headers into separate groups. That is a
reason to repair the invariant, not proof that every old object suffers an
incorrect quorum or heal. In particular, `hasEC()` requires **both** EC fields
to be nonzero; the V2 typo already zeroed `EcN`, so a claim that stale `EcM`
alone always enables the EC comparison would be incorrect. No production data
loss was reproduced in this review.

## Namespace-scanner responses {#scanner-responses}

Remote disk scanning streams `nsScannerResp` envelopes through the grid RPC
framework. Each message is either a progress `Update` containing a
`dataUsageEntry`, or a `Final` containing the resulting `dataUsageCache`.
The handler's pool reuses envelopes without automatically resetting fields.

Previously, `NSScannerHandler` assigned only the active field. A later scan
could therefore serialize both pointers. The receiver checks the two fields
independently: it forwards an update and remembers a final cache when each is
present. An extra stale update can enter usage aggregation; an update message
can also carry a cache belonging to an earlier scan.

The receiver does not stop at the first `Final`. A later legitimate final
message replaces the cached pointer, and a successful scan submits its final
bucket result after draining updates. Thus malformed intermediate responses
do **not** prove that every completed scan persists an incorrect total. The
deterministic failure is the broken response invariant and transmission of
obsolete data. The fix removes that ambiguity at its source:

```go
// Progress response
resp.Update = &update
resp.Final = nil

// Final response
resp.Final = &ui
resp.Update = nil
```

This targets remote scanner responses. Local disk scanning does not serialize
this envelope, and the legacy-header defect has its own trigger. Neither
requires the other. See the fixed
[server handler](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server.go),
[client receiver](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-client.go),
and [bucket-result aggregation](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/erasure.go).

## Why the fix stays out of the generic pool {#pool-ownership}

The initial PR also called `Recycler.Recycle()` inside the generic stream
handler's `PutResponse`, then put the same object into its own pool. That
treated a resource-ownership operation as if it were a reset hook.

For example, `grid.MSS.Recycle()` returns its map to another pool and sets the
map to nil. Pooling the wrapper again can make the next `NewResponse` skip
its constructor and return an unusable map. A supplemental reproducer passed
on the pre-PR main branch and failed with this proposed change.

The maintainer follow-up removed the generic change and `nsScannerResp`'s new
`Recycle` method, keeping the explicit scanner assignments. The merged
`internal/grid/handlers.go` and `cmd/storage-rest-common.go` are unchanged
relative to the pre-PR main branch. The existing `Recycler` ownership contract
is documented in [grid types](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/internal/grid/types.go).

Existing Console-log and event streams do use the `*grid.Bytes` recycler.
Their supplemental tests passed, including forwarded buffers and race checks.
The rejected change was a generic contract regression; this review did not
observe a Console or event-stream outage.

## Verification {#verification}

### Permanent regression tests {#regression-tests}

The merged source includes
[`TestXLMetaV2HeaderLegacyUnmarshalResetsEc`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2_test.go)
and
[`TestNSScannerHandlerClearsStaleResponses`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server_test.go).

The header test covers V2 byte decoding, stream decoding, reused indexed
headers, V1 clearing and preservation of current-format EC fields. The scanner
test invokes the real handler for three scans and checks both variants after
serialization, including their per-scan values.

Every newly allocated test response already contains dirty `Update` and
`Final` fields. This is deliberate: `sync.Pool` may discard entries, so a test
that assumes its next allocation returns a particular dirty object can pass
without exercising the bug. Making new allocations dirty as well makes the
test deterministic. The tests fail when the affected production files are
replaced with those from pre-fix main
[`0d3ba5d4cbfd`](https://github.com/pgsty/silo/commit/0d3ba5d4cbfd470946606c4dc7254b36be43c769),
and pass with the repaired files.

Run the permanent checks from the fixed checkout:

```bash
go test -race ./cmd \
  -run '^Test(XLMetaV2HeaderLegacyUnmarshalResetsEc|NSScannerHandlerClearsStaleResponses)$' \
  -count=1 -timeout=5m
go test -race ./internal/grid -count=1 -timeout=5m
```

Related metadata, scanner, data-usage, healing, directory-walk and response
serialization tests also passed under `-race`. Local `make verifiers` and
`make build` passed on Go 1.27.2, darwin/arm64. A later spelling check passed
for all four PR files; the full-repository spelling run reported 30 existing
diagnostics, all confirmed present before this PR. Those unrelated diagnostics
are not a clean full-repository spelling result.

### Real distributed scanner {#distributed-check}

A follow-up test ran the merged server as **two processes with eight data
directories**, all on loopback on one macOS host. It created twelve buckets
with two differently sized objects each, then deleted one object, overwrote
another and added a new object in every bucket.

| Checkpoint | Objects | Total logical bytes | Observed result |
| --- | ---: | ---: | --- |
| Initial writes | 24 | 64,740 | Every bucket and cluster total matched across three distinct usage updates |
| Delete, overwrite and add | 24 | 111,960 | Every bucket and cluster total matched across three further usage updates |
| Readback | 24 | 111,960 | All object lengths and SHA-256 digests matched |

Both processes recorded actual bucket scanning; the non-leader recorded
119 `ScanBucketDrive` operations. This exercised remote work rather than only
a local-disk mock. Test processes were stopped after verification.

This is a functional integration check of the fixed build. It is not a
benchmark, a physical-drive fault test, a proof of production deployment or a
deterministic reproduction of pool reuse on the old build. The permanent
regression test supplies the deterministic before/after evidence. Usage
`lastUpdate` timestamps indicate refreshed results, not proof that every
prefix in a production bucket has completed a full rescan.

### Remote CI {#ci}

All eight checks passed on head `86c5a92eef3d`: DCO,
[six Go CI jobs](https://github.com/pgsty/silo/actions/runs/38667624646),
and [VulnCheck](https://github.com/pgsty/silo/actions/runs/38667624700).
The Go jobs cover formatting/build/vet, lint/generated files, race/S3 Select,
cross-compilation, `internal/` tests and `cmd/` tests. After merge, the same
six [Go CI jobs on main](https://github.com/pgsty/silo/actions/runs/38668808660)
and [VulnCheck on main](https://github.com/pgsty/silo/actions/runs/38668808668)
passed independently.

## Compatibility and operator action {#operations}

The fix changes assignments in existing decoders and response construction.
It introduces no new storage format, RPC field, dependency version, policy,
configuration switch or client requirement. It does not require rewriting
objects or deleting usage caches. The supported stack remains coordinated
SILO, SILO Console, mcli and silo-pkg; compatibility with unmodified upstream
MinIO/MC remains best effort.

1. **Identify the running server build.** Server 20260916 does not include
   this repair. Select a future release that explicitly includes it, or a
   verified custom build containing the fixed code. Checking a repository
   branch alone does not establish the running artifact's identity.
2. **Upgrade every scanner-serving node.** Wire compatibility is unchanged,
   but an old node still produces the old responses. This patch adds no new
   coordination requirement; the selected release may contain other changes
   with their own upgrade requirements. Consult the
   [component matrix](/compatibility/versions/).
3. **Allow usage statistics to converge.** Check scanner health and activity
   with `mcli admin scanner status ALIAS -n 1`. Compare stable bucket counts
   and logical sizes with an independent inventory using the same version,
   delete-marker and time boundaries. A single updated timestamp is
   insufficient to conclude that all affected paths have been rescanned.
4. **Investigate persistent discrepancies separately.** Preserve the build
   identity, scanner errors and a small reproducible inventory. Concurrent
   writes, versioning, incomplete scans or offline drives can also explain
   differences. Do not hand-edit `xl.meta`, remove internal caches, run a
   destructive repair or rewrite all objects solely because of this PR.

The patch prevents new stale-field carry-over. It does not reconstruct
historical usage observations or certify pre-existing data health. A normal
successful scan can replace derived usage results; neither the source merge
nor this local fixture proves recovery of every existing installation.

## Delivery and credit {#delivery}

Julien Laurenceau contributed the original fixes and initial tests. The
maintainer follow-up narrowed the pooling change and strengthened validation;
the original commits and DCO sign-offs remain in the merge history. The final
PR changes four files, with 194 additions and two deletions, mostly tests.

The code repair, permanent tests, PR acceptance and post-merge CI are complete.
This record supplies the bilingual explanation and operating boundary. As of
the date above, publishing a new Server release and upgrading production
installations remain separate deliverables; no package, image or production
rollout is claimed by this record.
