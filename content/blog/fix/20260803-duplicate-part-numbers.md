---
title: "Sorted Is Not Increasing: How One Duplicate Part Number Doubled an Object"
linkTitle: "Duplicate Part Numbers"
date: 2026-08-03
author: "Ruohang Feng"
description: "A 5 MiB part uploaded once, assembled twice, returned as a 10 MiB object with HTTP 200. The predicate was strict; the verb was not. Two refactors over a decade preserved the defect faithfully."
tags: [Security, Multipart Upload]
weight: 100
draft: false
url: "/blog/security/duplicate-part-numbers/"
---

**Status:** Fixed on the local `pgsty/minio` branch as `a0d073c5c`, **unreleased**
**Classification:** Data correctness, **not a vulnerability** — see [Why this is not a CVE](#not-a-cve)
**Affected scope:** All backends, any authenticated S3 client, on its own upload
**Tracking:** `pgsty/minio` issue #49

> One section of this article describes an unfixed process-level panic in a neighbouring code path. Hold publication until that is fixed and released.

## Conclusions first {#summary}

- `sort.SliceIsSorted` with a `<` predicate does not test strict increase. It tests **the absence of an inversion**. Equal neighbours contain no inversion, so `[1,1]` was accepted.
- Upload one 5 MiB part, complete with `[1,1]`, and the server returns **HTTP 200 and a 10 MiB object**. The upload is then consumed: a corrected retry gets `NoSuchUpload`. The client cannot recover.
- **Inherited from upstream, and old.** The check has had this shape since 2016-08. Two refactors — 2017 and 2023 — rewrote it faithfully, because each preserved the predicate, and **the predicate was never the problem**.
- The fix is one loop at the handler layer. The object layer is left undefended **by decision**, and that IOU is written down here rather than left implicit.
- Three independent reviews found **no defect in the fix**. What they found was a comment that misstated why a neighbouring guard exists — and, through that comment, an unrelated node-level panic.

## The verb, not the predicate {#the-defect}

The code, as inherited:

```go
if !sort.SliceIsSorted(complMultipartUpload.Parts, func(i, j int) bool {
	return complMultipartUpload.Parts[i].PartNumber < complMultipartUpload.Parts[j].PartNumber
}) {
	writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
	return
}
```

It reads as "reject unless the part numbers strictly increase." It does not do that. `IsSorted` evaluates the predicate **in the reversed direction only** — for each neighbouring pair it asks `less(i, i-1)`, i.e. "is this element smaller than the one before it," and reports unsorted the moment one such inversion appears. For a pair of equal elements that question is false. No inversion, therefore sorted.

The consequence is worth stating precisely, because it is what makes the misuse survive review: **no strict predicate can make `IsSorted` reject duplicates.** The only spelling that works is the non-strict one — passing `<=` as the `less` function, so that equal neighbours register as an inversion. To ask for *strictly* increasing you would have to write the operator that reads as *not* strict. Every reviewer who checked that the predicate said `<` was checking the right character in the wrong function.

Our replacement drops `IsSorted` rather than trying to spell it correctly:

```go
for i := 1; i < len(complMultipartUpload.Parts); i++ {
	if complMultipartUpload.Parts[i-1].PartNumber >= complMultipartUpload.Parts[i].PartNumber {
		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrInvalidPartOrder), r.URL)
		return
	}
}
```

The rejection-set delta is exactly one class: **lists containing an adjacent equal pair.** Everything previously rejected is still rejected; everything previously accepted, except duplicates, is still accepted. Non-adjacent duplicates come along for free — a strictly increasing sequence is globally distinct, so `[1,2,1]` and `[1,3,2,3]` are caught by the inversion they are forced to contain.

## Two refactors preserved it faithfully {#archaeology}

The archaeology is the most transferable part of this incident.

| When | Shape | What changed |
| :-- | :-- | :-- |
| 2016-08 | `sort.IsSorted(CompletedParts(parts))` | already present at `server: Move all the top level files into cmd folder (#2490)` |
| 2017-11 | same call, `Less` moved onto an exported type | `Add public data-types for easier external loading (#5170)` |
| 2023-04 | `sort.SliceIsSorted(parts, func(i,j) bool { … < … })` | `simplify sort.Sort by using sort.Slice (#17066)` |

Both refactors were correct as refactors: they preserved behaviour exactly, which is what a refactor is supposed to do. The 2023 commit was a repository-wide cleanup with no bearing on multipart semantics at all. It carried the `<` across unchanged, and the `<` was never wrong — `CompletedParts.Less` needs `<` to be a valid `sort.Interface`.

**The defect lived in the relationship between the predicate and the function it was handed to, and a refactor that moves the predicate cannot see that relationship.** A decade, three shapes, one behaviour: an ordering check that answers a question adjacent to the one it appears to answer.

## What it actually did {#impact}

Measured against both erasure backends, through the real signed HTTP handler:

| Uploaded | Completion list | Response | Resulting object | ETag suffix |
| :-- | :-- | :-- | :-- | :-- |
| one 5 MiB part | `[1,1]` | **200 OK** | **10,485,760 bytes** | `-2` |
| two 5 MiB parts | `[1,2,2]` | **200 OK** | **15,728,640 bytes** | `-3` |
| one 5 MiB part at 10000 | `[10000,10000]` | **200 OK** | **10,485,760 bytes** | `-2` |

The ETag suffix is the part count the server believes it assembled. There is no internal disagreement to detect: the metadata, the size, and the ETag are all mutually consistent and all wrong. The object simply is not what was uploaded.

Two properties make this worse than a bad error code.

**The upload is consumed.** Assembly runs to completion and cleans up the multipart upload, so the corrected retry returns `NoSuchUpload`. A client that notices the wrong size cannot fix it by resending the right list; it has to start the whole upload over, if it still has the data.

**It is reachable by accident.** No adversary is required. Any client that appends a part to its completion list twice — a plausible bug in a resumable-upload wrapper, a retry path, or a list built by concatenation — silently gets a doubled part instead of a 400.

## Why this is not a CVE {#not-a-cve}

It belongs in this chronicle because it is a silent server-side correctness failure, and this is where we keep those. It is not a vulnerability, and we are not going to inflate it into one.

The request must carry the caller's own credentials, address the caller's own upload, and the damaged object is the caller's own. There is no cross-tenant effect, no privilege change, no disclosure, and no path to another account's data. What breaks is the guarantee that a completed multipart object equals the bytes you uploaded — serious, but a correctness guarantee, not an access-control boundary.

The entries around this one in this chronicle are authentication bypasses and path traversals. Filing this beside them under the same label would make every label in the table mean less.

## The boundary decision, and what it costs {#boundary}

The object layer has **no duplicate defence at all.** `erasureObjects.CompleteMultipartUpload` sizes its output slice to the *request* (`cmd/erasure-multipart.go:1249`) and then resolves each requested part number against current metadata (`:1255`). The same number resolves twice, writes two identical `ObjectPartInfo` entries, and adds its size twice. `AddObjectPart` does deduplicate by part number, but it deduplicates the metadata slice, not the request. The 5 MiB minimum-size rule cannot help either, because the duplicated part is individually legal.

We fixed the handler and left that alone. The reasoning:

- It is **the only entrance where a client-controlled list exists.** The other four callers — batch, restore, decommission, rebalance — build their lists server-side from `oi.Parts` or `1..n`, and are strictly increasing by construction.
- The required output is an **S3 error code**, which is an API-layer concern. The object layer's error vocabulary maps to a different code, so intercepting lower would hand clients a less accurate diagnosis.
- Minimality. This fork ships narrow fixes, and a change in the assembly loop is not narrow.

The cost, recorded rather than implied: **the uniqueness invariant now has exactly one enforcement point, and nothing enforces the enforcement.** No compiler error and no test failure will greet the person who adds a fifth caller to the object layer; they will get a silently corrupted object. That is the same species of IOU the [previous article](/blog/security/internode-path-containment/) recorded about `getVolDir`, and it is written down for the same reason: an unrecorded deliberate omission is indistinguishable from an oversight six months later.

## What we deliberately did not add {#no-extra-constraints}

Part numbers need not start at 1 and need not be consecutive. `[1,3]`, `[5,9]` and `[3]` are all legal S3, and all still complete successfully.

This matters more than it sounds. "Also require the list to start at part 1" is a one-line addition that looks like tightening, would pass a casual review, and would break legal clients — anything that abandons a part after a failed upload and completes with what it has. The temptation is real precisely because the fix next door is about validating the same list.

So two test cases exist for no purpose other than to make that change fail. We verified they do their job by injecting the constraint and confirming that **exactly those two cases went red and nothing else did.** A guard rail nobody has fired once is a guess.

## The one behaviour change we did not intend {#error-code}

A 14-input differential against the pre-fix build turned up exactly one behavioural change beyond duplicate rejection: `[0,0]` and `[-1,-1]` — lists that are both duplicated *and* out of range — moved from `InvalidPart` to `InvalidPartOrder`. Both are HTTP 400.

We accepted it, on the principle that a format error should outrank a state error: an ordering violation is decidable without reading any storage, while part existence is not. It also only affects requests that were going to fail regardless, so no client that previously succeeded can now fail.

On S3 fidelity itself we are making a documented inference, not a measurement. AWS defines `InvalidPartOrder` as the parts list not being in ascending order, and documents that part numbers may be non-consecutive; duplicates are not ascending. **We did not verify this against a live AWS endpoint**, and two independent reviewers reached the same conclusion by the same documentary route, which is agreement, not evidence.

## Falsification, and a comment that was wrong {#mutations}

Two mutation experiments, in the discipline the previous article argued for — a test you have never watched fail is not yet a test.

**Inject "must start at part 1."** Exactly the two gap cases went red; the four lists starting at 1 stayed green. The guard rail is targeted, not incidental.

**Delete the neighbouring `len(Parts) == 0` guard.** The expected result was that an empty completion would produce some wrong-but-orderly error. The actual result was that **the process panicked**: the empty list reaches a storage decorator that indexes element zero of the part-path slice without a length check, on a goroutine that no `recover` can reach. The S3 face is masked by that one guard line, which has been there since 2022 and is not documented as load-bearing. It is tracked separately as an unfixed node-level defect, which is why this article is held.

And the part worth publishing at our own expense: **the comment we wrote about that guard was wrong.** It said dropping the length check would let an empty completion *succeed* — the opposite direction of the truth, and specifically the direction that understates danger. It was caught in review and corrected before the commit. A comment that misstates why a check exists is exactly how the check gets deleted three years later by someone tidying up.

## Three acceptances, zero blocking findings {#review}

The change went through three independent gates before commit:

| Gate | Method | Outcome |
| :-- | :-- | :-- |
| Author | revert the fix, watch the test go red at the measured 10 MiB, reapply, watch it go green | red/green established |
| Independent reviewer | **rebuilt the red state in its own detached worktree** rather than trusting the report; 14-input differential | no blocking finding |
| External model, different vendor | read-only sandbox, independent derivation of the rejection-set argument and of the AWS reading | conditional accept; the condition was that it could not compile in its own sandbox |

Stated plainly, because the honest version is less flattering than the table: **none of the three found a defect in the fix.** What review produced was the corrected comment and, through the mutation it prompted, the discovery of the unrelated panic. That is still a good return, but it is not the same as catching a bug in the patch, and the record should say which one happened.

The rebuilt-red-state detail is the one worth copying. A reviewer who reruns the author's tests is checking the author's arithmetic; a reviewer who reconstructs the broken state independently is checking the author's claim.

## Declined, and left open {#declined}

Declined, deliberately:

- **Two test additions** — completing onto a pre-existing object, and giving each part distinct content so ordering is verified rather than just total size. Both are real improvements. Both were declined under a standing rule that this fork ships correctness and security fixes rather than test expansion, and the core invariant is already pinned by "the rejected request left no object and the upload still works."
- **XML root element name is not validated.** A document with the wrong root but correct `<Part>` children is accepted. This is not a bypass — the same list still goes through the same check — it is pre-existing, and tightening it risks breaking real SDKs over namespace handling. Recorded, not fixed.

Left open, none of it in a released build as of 2026-08-03:

- Object-layer defence in depth for part uniqueness (see [above](#boundary)).
- The empty-list panic in the storage decorator, tracked as a node-level defect.
- XML strictness, including `<PartNumber>abc</PartNumber>` returning 500 where 400 `MalformedXML` is correct.

The concurrent checksum work on completion (`#46`, `#48`, `#50`) was fenced off from this change entirely and shares no code with it.

## Closing {#closing}

The predicate was strict. The verb was not. A decade of review read the predicate — including the two commits that rewrote the line.

If only one sentence survives: **check what the function does with the comparison, not just what the comparison says**, and when you decide to leave the layer underneath undefended, write it down where the next person will trip over it, rather than trusting that they will re-derive your reasoning.
