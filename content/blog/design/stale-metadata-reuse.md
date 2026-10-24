---
title: "Clearing Stale Fields in Legacy Metadata and Scanner Responses"
linkTitle: "Stale Metadata Reuse"
date: 2026-10-15
lastmod: 2026-10-19
author: "Ruohang Feng"
summary: >
  PR #233 fixes stale fields carried over when legacy xl.meta headers and namespace-scanner responses are reused. This note documents the triggers, observed behavior, targeted field resets, deterministic regression tests, distributed scanner verification, and operator guidance.
tags: [Design, Reliability, Storage, Scanner]
weight: 95
draft: false
url: "/blog/design/stale-metadata-reuse/"
---

This article records the design and verification of [PR #233](https://github.com/pgsty/silo/pull/233) (tested head [`86c5a92eef3d`](https://github.com/pgsty/silo/commit/86c5a92eef3d5667c83bdbc59a033b955bdbf146), merged as [`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a)), which shipped in [Server 20261018](/blog/release/silo-20261018/). It fixes stale fields carried over when legacy `xl.meta` version headers and remote namespace-scanner responses are reused.

## Overview {#problem}

Two independent code paths reused a Go struct without resetting all of its logical state, allowing fields omitted from the new input to retain values from a previous operation. The fix resets those fields directly in the decoder and response builder that know the schema of each message:

| Path | Trigger | Previous state | Repaired state |
| --- | --- | --- | --- |
| Legacy V2 version header | Decode a V2 header into a reused struct with nonzero EC fields | `EcN` becomes zero, `EcM` retains its old value | Both absent EC fields are zeroed |
| Legacy V1 version header | Reuse a struct containing a signature or EC fields | Fields absent from V1 retain their old values | `Signature`, `EcN`, and `EcM` are zeroed |
| Scanner update response | Reuse an envelope that previously carried a final cache | Both `Update` and the old `Final` are serialized | Only `Update` is present |
| Scanner final response | Reuse an envelope that previously carried a progress update | Both the old `Update` and `Final` are serialized | Only `Final` is present |

## Legacy `xl.meta` Headers {#legacy-headers}

The compact version header inside `xl.meta` has its own version number, distinct from the outer `xl.meta` format version and the SILO release number. The current header version is V3 and includes the erasure-coding fields `EcN` and `EcM`. Legacy V2 headers have five fields and omit both EC fields; the V1 decoder handles an earlier four-field layout without a signature or EC fields (noted in source comments as never released, so clearing V1 fields is defensive hygiene on a retained decoder).

Both V2 decoding entry points — byte-oriented `UnmarshalMsg` and stream-oriented `DecodeMsg` — previously began with:

```go
z.EcN, z.EcN = 0, 0
```

Assigning `z.EcN` twice left `z.EcM` untouched. Decoding into a freshly allocated zero-valued struct masked the typo, but reusing a struct that previously held `EcN=4, EcM=8` yielded `EcN=0, EcM=8` after decoding a V2 header. The fix changes the assignment to `z.EcN, z.EcM = 0, 0` and clears the absent `Signature` field before decoding V1 headers. Current V3 headers continue to populate `EcN` and `EcM` from the wire payload.

In production, `loadIndexed` reuses the backing slice of version headers, so resetting fields only on fresh allocations would leave that path exposed. The regression suite exercises this slice-reuse path directly. See the updated [legacy decoders](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2-legacy.go) and [indexed-header loading and comparison](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2.go).

Without this reset, a decoded V2 header varies depending on the struct's prior contents. Because header equality checks and quorum vote counting compare all struct fields, differing stale `EcM` values can split otherwise identical headers into separate quorum groups (even though `hasEC()` requires both `EcN` and `EcM` to be nonzero).

## Namespace-Scanner Responses {#scanner-responses}

Remote disk scanning streams `nsScannerResp` envelopes over the grid RPC framework. By contract, each envelope carries either a progress `Update` (`*dataUsageEntry`) or a `Final` summary (`*dataUsageCache`). The RPC handler pools `nsScannerResp` structs across requests without zeroing their fields on return.

Previously, `NSScannerHandler` set only the active pointer for the current message. When a pooled struct was reused in a subsequent scan, both pointers could remain non-nil and serialize together over the wire. Because the client receiver inspects both fields independently — forwarding `Update` whenever non-nil and recording `Final` whenever non-nil — a final response could replay a stale progress update into usage aggregation, and a progress response could carry a `Final` cache pointer from an earlier scan.

Although the legitimate `Final` message sent at the end of the stream eventually overwrites the client's cached `Final` pointer, intermediate envelopes violated mutual exclusion and transmitted stale scan data. The fix explicitly clears the inactive pointer when constructing each response:

```go
// Progress response
resp.Update = &update
resp.Final = nil

// Final response
resp.Final = &ui
resp.Update = nil
```

This applies to remote disk scanner responses (local disk scans do not serialize `nsScannerResp`). See the updated [server handler](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server.go), [client receiver](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-client.go), and [bucket-usage aggregation](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/erasure.go).

## Why `grid.Recycler` Is Not Called in the Generic Pool {#pool-ownership}

The initial PR draft also called `Recycler.Recycle()` inside the generic stream handler's `PutResponse` before returning the response wrapper to the handler's `sync.Pool`. That conflated transferring ownership of inner pooled resources with resetting a struct for reuse.

Specifically, `grid.MSS.Recycle()` returns its underlying `map` to a dedicated map pool and sets the struct's map field to `nil`. If the outer response wrapper is then placed back into the handler's response pool, a subsequent `NewResponse` call can retrieve that wrapper from the pool, skip the constructor, and hand the caller a `nil` map. A targeted reproduction test passed on the pre-PR `main` branch and panicked with that generic `PutResponse` change applied.

The maintainer follow-up therefore dropped the generic `PutResponse` change and the `nsScannerResp.Recycle` method, keeping only the explicit field assignments in `NSScannerHandler`. In the merged commit, `internal/grid/handlers.go` and `cmd/storage-rest-common.go` are unchanged relative to pre-PR `main`, preserving the `Recycler` ownership contract documented in [grid types](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/internal/grid/types.go).

## Verification {#verification}

### Deterministic Regression Tests {#regression-tests}

The merged commit adds [`TestXLMetaV2HeaderLegacyUnmarshalResetsEc`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2_test.go) and [`TestNSScannerHandlerClearsStaleResponses`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server_test.go).

The header test covers V2 byte decoding, V2 stream decoding, reused indexed header slices, V1 field clearing, and preservation of V3 EC fields. The scanner test runs the real `NSScannerHandler` across three consecutive scans and inspects the serialized responses to verify that each message carries only its intended field from the current scan.

To make the scanner test deterministic under `sync.Pool`, the test pool's `New` function pre-populates every newly allocated `nsScannerResp` with dirty `Update` and `Final` pointers. Because the Go runtime can evict `sync.Pool` entries at any garbage collection cycle, a test that merely returns a dirty object to the pool and hopes to get it back on the next `Get` can pass vacuously when a fresh zero-valued struct is allocated instead. Pre-populating new allocations guarantees that every `Get` returns a dirty envelope: the test fails deterministically against pre-fix `main` ([`0d3ba5d4cbfd`](https://github.com/pgsty/silo/commit/0d3ba5d4cbfd470946606c4dc7254b36be43c769)) and passes with the fix.

```bash
go test -race ./cmd \
  -run '^Test(XLMetaV2HeaderLegacyUnmarshalResetsEc|NSScannerHandlerClearsStaleResponses)$' \
  -count=1 -timeout=5m
go test -race ./internal/grid -count=1 -timeout=5m
```

### Distributed Scanner Verification {#distributed-check}

End-to-end verification ran the merged binary as **two server processes managing eight data directories** over loopback. The harness created twelve buckets, wrote two differently sized objects into each bucket, and then deleted one object, overwrote the second, and wrote a third object in every bucket.

| Checkpoint | Objects | Total logical bytes | Observed result |
| --- | ---: | ---: | --- |
| Initial writes | 24 | 64,740 | Bucket and cluster totals matched across three consecutive usage updates |
| Delete, overwrite, and add | 24 | 111,960 | Bucket and cluster totals matched across three subsequent usage updates |
| Readback verification | 24 | 111,960 | All 24 object lengths and SHA-256 digests matched |

Both processes logged active bucket scans, with the non-coordinator node executing 119 `ScanBucketDrive` operations over the remote grid RPC stream.

### Remote CI {#ci}

All eight CI workflows passed on PR head `86c5a92eef3d`: DCO, [six Go CI jobs](https://github.com/pgsty/silo/actions/runs/38667624646), and [VulnCheck](https://github.com/pgsty/silo/actions/runs/38667624700). Following merge, the six [Go CI jobs on main](https://github.com/pgsty/silo/actions/runs/38668808660) and [VulnCheck on main](https://github.com/pgsty/silo/actions/runs/38668808668) also passed.

## Compatibility and Operations {#operations}

The fix only updates field assignments during legacy header decoding and scanner response construction. Wire protocols, on-disk formats, dependencies, IAM policies, and configuration flags are unchanged, and no object rewrites or cache deletions are needed.

1. **Upgrade cluster nodes to Server 20261018 or later.** Because the wire format is unchanged, nodes can be upgraded in a normal rolling fashion; see the [component matrix](/compatibility/versions/) for release-level compatibility details.
2. **Allow background scanner cycles to converge.** Check scanner status with `mcli admin scanner status ALIAS -n 1` and verify bucket object counts and logical sizes after a full scan pass completes.
3. **Do not manually edit metadata or caches.** Normal background scanning automatically refreshes derived usage totals without manual changes to `xl.meta` or internal cache files.

## Delivery and Credit {#delivery}

Julien Laurenceau contributed the initial fixes and tests. The maintainer follow-up narrowed the pooling change to preserve `grid.Recycler` ownership semantics and added the deterministic dirty-allocation regression suite; the original commits and DCO sign-offs are preserved in the merge history.
