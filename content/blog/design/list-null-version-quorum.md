---
title: "A Listing Must Not Drop a Null Version That Still Has Quorum"
linkTitle: "Listing Null-Version Quorum"
date: 2026-09-16
lastmod: 2026-09-16
author: "Ruohang Feng"
summary: >
  A successful ListObjects omitted keys that existed and were readable. One cause is an order-sensitive version selection inherited from upstream healing tolerance; it is repaired on main. A second, rolling-restart omission reproduced on the repaired build and is tracked separately.
tags: [Design, S3, ListObjects, Review]
weight: 25
draft: false
url: "/blog/design/list-null-version-quorum/"
---

This record covers the listing omission investigated on 2026-09-16: an unversioned bucket under concurrent overwrites returned HTTP 200 listings that lacked keys the same endpoint could still GET. It describes the confirmed mechanism, the narrow repair in commit [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1), what that repair proves, and the counterexample that remains open in [#218](https://github.com/pgsty/silo/issues/218).

> **Status:** on main after the published Server 20260903. The repair was reviewed in three external review rounds before implementation and validated with deterministic order counterexamples, signed HTTP listings and differential inputs. It does not close the listing problem; see [the boundary](#boundary).

## The defect {#defect}

Listing merges the version streams of the drives that were asked. When the drives disagree, `mergeXLV2Versions` picks a top version and counts the streams that agree with it. A 2022 upstream change ([PR #14125](https://github.com/minio/minio/pull/14125)) made that count tolerant of signature differences left by healing, which is necessary, but the way it selects and counts is sensitive to input order. With one ordinary null version per drive, a newer minority that sorts last resets the count for the older generation. The older generation that actually has quorum is then discarded, the merge returns nothing, and the resolver reports the key as absent. The request still succeeds, so the client sees a complete-looking listing with a hole. Reads of the key succeed because the read path resolves quorum on its own.

Nine drive orders on the old code failed this way, with complete signed LIST evidence, while the same content in other orders listed correctly. The defect also exists in the published Server 20260903.

## The repair {#fix}

The recount is added only where the original selection ends without quorum, and only for inputs where it can be exact: every non-empty drive stream holds exactly one ordinary null version, none is a free version, and all share the same erasure parameters, judged on the original inputs before any stream is pruned. In that case the versions are regrouped by header and a group is returned only if it reaches the original effective quorum. Mixed histories, explicit version IDs, delete markers, free versions and mixed erasure layouts keep their previous behavior; the strictness, signature, tie-break and representative-entry rules are unchanged, and shared callers of the merge see the same result for every previously successful input.

Validation: the nine old-order and seven new-order counterexamples pass; 5,620 differential inputs keep the contracted result; full signed HTTP listings, object reads, normal and race runs, and the scanner, healing and migration consumers of the merge were checked. Before integration into main, six top-level and 23 nested cases passed in normal and race mode. A stable-state run of 20,000 successful LISTs under concurrent overwrites on a four-node, sixteen-drive cluster omitted nothing.

## What remains open {#boundary}

On the same cluster, a rolling restart of the four nodes under concurrent overwrites returned 27,966 successful LISTs, of which 2,624 omitted one to four keys. The keys were readable: 8,186 of 8,192 same-endpoint GET/HEAD checks returned 200 with the last confirmed content. The strongest sample started 17.6 s after the last node's health check returned and omitted a key whose last successful PUT had been confirmed 11.5 s earlier with no later write. Raw XML, HTTP correlation and body hashes were re-verified independently, so pagination and parsing do not explain it.

The repaired build still has exits that turn "cannot decide" into "absent" without failing the request: a merge in which no generation reaches quorum, a resolver with fewer valid entries than quorum or no cached metadata, the partial-resolution callback that drops the entry and only fails the listing when more readers have failed than the quorum allows, and a walker that skips an entry whose metadata read fails unexpectedly. The listing quorum is computed from the number of drives asked and does not follow readers that fail mid-listing. Which of these the sample hit cannot be told from HTTP evidence; the per-drive streams, effective quorum, recount eligibility and cache state of the failing request were not captured, and metadata recovered after the run is not the failing input.

The next step is a bounded diagnostic capture of one failing LIST, then a deterministic regression built from that input, and only then a decision on whether the contract changes to fail the request or return a three-state result. Until then, do not run tools that delete destination objects missing from a source listing during rolling restarts, and list again once the cluster is stable.
