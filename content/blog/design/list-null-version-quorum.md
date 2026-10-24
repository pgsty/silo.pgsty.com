---
title: "A Listing Must Not Drop a Null Version That Still Has Quorum"
linkTitle: "Listing Null-Version Quorum"
date: 2026-09-16
lastmod: 2026-10-19
author: "Ruohang Feng"
summary: >
  A successful ListObjects omitted keys that existed and were readable. One cause is an order-sensitive version selection inherited from upstream healing tolerance; it is repaired in Server 20260916. A second, rolling-restart omission reproduced on the repaired build and was subsequently closed in Server 20261018.
tags: [Design, S3, ListObjects, Review]
weight: 25
draft: false
url: "/blog/design/list-null-version-quorum/"
---

This record covers the listing omission investigated on 2026-09-16: an unversioned bucket under concurrent overwrites returned HTTP 200 listings that lacked keys the same endpoint could still `GET`. It describes the confirmed mechanism, the targeted repair in commit [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1) (shipped in [Server 20260916](/blog/release/silo-20260916/)), what that repair proves, and the rolling-restart counterexample tracked in [`#218`](https://github.com/pgsty/silo/issues/218) that was subsequently closed by PR [`#239`](https://github.com/pgsty/silo/pull/239) in [Server 20261018](/blog/release/silo-20261018/#listing) (see the [LIST recovery design](/blog/design/listing-recovery-lock-cost/)).

## The defect {#defect}

Listing merges the version streams of the drives that were queried. When drives disagree, `mergeXLV2Versions` picks a top version and counts the streams that agree with it. A 2022 upstream change ([PR #14125](https://github.com/minio/minio/pull/14125)) made that count tolerant of signature differences left by healing, which is necessary, but the way it selects and counts is sensitive to input order. With one ordinary null version per drive, a newer minority that sorts last resets the count for the older generation. The older generation that actually has quorum is then discarded, the merge returns nothing, and the resolver reports the key as absent. The request still succeeds, so the client sees a complete-looking listing with a missing key. Reads of the key succeed because the read path resolves quorum independently.

Nine drive orderings on the pre-fix code failed this way with complete signed `LIST` evidence, while the same content in other drive orderings listed accurately.

## The repair {#fix}

The recount in commit [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1) runs only where the original selection ends without quorum, and only for inputs where it can be exact: every non-empty drive stream holds a single ordinary null version, none is a free version, and all share the same erasure parameters, judged on the original inputs before any stream is pruned. In that case the versions are regrouped by header and a group is returned only if it reaches the original effective quorum. Mixed histories, explicit version IDs, delete markers, free versions, and mixed erasure layouts keep their previous behavior; the strictness, signature, tie-break, and representative-entry rules are unchanged, and shared callers of the merge see the same result for every previously successful input.

Validation of `8d06424b1`:
- All 9 old-order and 7 new-order counterexamples pass, and 5,620 differential inputs keep the contracted result.
- Full signed HTTP listings, object reads, normal and race runs, and the scanner, healing, and migration consumers of the merge passed (6 top-level and 23 nested cases in normal and `-race` mode).
- A steady-state run of 20,000 successful `LIST` calls under concurrent overwrites on a 4-node, 16-drive cluster omitted zero keys.

## Rolling-restart boundary (`#218`, closed by `#239` in 20261018) {#boundary}

On the same 4-node, 16-drive cluster, a rolling restart of the four nodes under concurrent overwrites on the `20260916` build returned 27,966 successful `LIST` responses, of which 2,624 omitted one to four keys. The omitted keys remained readable: 8,186 of 8,192 same-endpoint `GET`/`HEAD` checks returned `200 OK` with the last confirmed content. The strongest sample started 17.6 s after the last node's health check returned and omitted a key whose last successful `PUT` had been confirmed 11.5 s earlier with no subsequent write. Raw XML, HTTP correlation, and body hashes were verified independently, ruling out pagination or client parsing.

That rolling-restart failure occurred before or around `mergeXLV2Versions`, where the `20260916` build still had exits that turned transient read or lock failures into silent omissions:
- `listPathRaw` read-lock acquisition (`NSLock`) timing out after 1 second under write contention and skipping or failing the path;
- a resolver with fewer valid entries than quorum or no cached metadata when a peer drive disconnected mid-stream;
- the partial-resolution callback dropping an entry when individual readers failed without crossing the set-wide failure threshold.

Issue [`#218`](https://github.com/pgsty/silo/issues/218) tracked that rolling-restart investigation, and PR [`#239`](https://github.com/pgsty/silo/pull/239) in [Server 20261018](/blog/release/silo-20261018/#listing) resolved it by removing the 1-second `listPathRaw` read-lock timeout and adding bounded metacache stream recovery. See [LIST Recovery Under Node Restart and NSLock Contention](/blog/design/listing-recovery-lock-cost/) for the complete `#239` design and benchmarks.
