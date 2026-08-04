---
title: "Internode Path Containment Audit: Paying Off What CVE-2026-42600 Left Owing"
linkTitle: "Internode Path Containment Audit"
date: 2026-08-02
author: "Ruohang Feng"
description: "The previous entry said plainly that deleting an endpoint is not the same as closing a defect class. This is that audit: four protocol surfaces, twelve defects, and four regressions we caused ourselves while fixing them."
tags: [Security, Path Containment]
weight: 90
draft: false
url: "/blog/security/internode-path-containment/"
---

**Status:** Fixed on the local `pgsty/minio` branch, **unreleased and not disclosed** (no CVE/GHSA requested; the upstream repository is archived)
**Affected scope:** Distributed erasure only; cluster-root / internode JWT required
**Prerequisite reading:** [CVE-2026-42600 · ReadMultiple](/blog/security/cve-2026-42600/)

> This article contains complete exploitation vectors and measurements. Publishing it constitutes disclosure. Hold it until the fixed release ships.

[The previous entry](/blog/security/cve-2026-42600/) closed with this sentence:

> Deleting the endpoint proves only that `ReadMultiple` no longer exists. It cannot be extrapolated into a completed containment audit of every internode body path.

That was an IOU, written down in plain sight. This is the record of paying it — and a not-very-flattering construction log.

## Conclusions first {#summary}

- Twelve defects, **all inherited from upstream**. Verified by per-function md5 comparison: the fork's diff against upstream on the affected files is pure deletion, zero added lines.
- This is not a new vulnerability. It is **the remainder of CVE-2026-42600** — three more protocol surfaces under the same root cause.
- Our failure is not in the code. It is in the **record**: a point fix was written up as a closure.
- While fixing it we introduced **four regressions of our own**, every one of them in a rule we invented rather than reused.

## "N endpoints" was the wrong frame {#four-surfaces}

Earlier audits kept counting endpoints, arriving at 19, then 21, then 22 — and missing an entire protocol surface each time. The real structure is four surfaces:

| Protocol surface | Entries | Covered by the global HTTP middleware |
| :-- | :-- | :-- |
| storage-REST HTTP **query arguments** | 9 | **Yes** — previously misreported as unprotected |
| storage-REST HTTP **msgpack body** | 4 | No; `r.Form` never comes from a body |
| **storage Grid RPC** | 18 | No; after one upgrade, frames never re-enter the HTTP chain |
| **peer-S3 Grid RPC** | 5 | No, and it bypasses `getStorage()` to reach drives directly |

The first row matters as much as the rest: it overturns the earlier "all 21 endpoints escapable" claim. Those audits grepped for the validation helper inside handler bodies, found nothing, and concluded there was no protection — **missing that the protection lives in the middleware layer.**

The fourth row is the one no amount of hardening in storage-REST handlers can reach.

## The root cause is three layers, not one bug {#root-cause}

Three design facts, none wrong on its own:

1. **Validation happens only at the HTTP surface.** `r.Form` is populated from `url.ParseQuery(RawQuery)` and **never from a body** (introduced 2017).
2. **Grid RPC bypasses the middleware.** `/minio/grid/v1` upgrades once; subsequent msgpack frames never re-enter the HTTP chain (introduced 2023).
3. **The storage layer performs no containment.** `getVolDir` rejects a volume only when it is exactly `""`/`.`/`..`, and `pathJoin` runs `Clean` (settled 2018).

In one sentence: **the upper layer assumes the lower one validates, the lower assumes the upper already did, and neither can see the channel in between.**

`ReadMultiple` was merely one endpoint that exercised that structure. Removing it left the structure intact.

One line of the timeline deserves singling out. The divide-by-zero in `ShardFileSize` has been present since 2020, but only when it moved inside `xioutil.WithDeadline` in 2024-10 — a change meant to fix large-object timeouts — did it escalate from "one failed request" to "the whole process exits", because `WithDeadline` runs its work function on a bare goroutine that no `recover()` can reach. That escalation was not visible at the time.

## Vectors, confirmed by execution {#vectors}

Every one reproduced against a real `xlStorage` through the real REST/grid client, with planted sentinel files. None of this is static inference.

| Vector | Surface | Observed |
| :-- | :-- | :-- |
| `WriteAll("vol","../../x")` | storage grid | **arbitrary file write** outside the drive root |
| `RenameFile(".minio.sys","","bucket","x")` | storage grid | **the entire system volume** (IAM, config) relocated into a readable bucket, **with no `..` anywhere** |
| `DeleteBucket("../victim", force)` | peer-S3 grid | **recursive deletion of a tree** outside the drive root |
| `DeleteBulk("vol","")` | HTTP body | whole volume moved to trash |
| `ReadAll(volume:"../")` | any | `getVolDir`'s check **defeated by a trailing slash** |
| `CheckParts` with a zero `Erasure` | storage grid | **process terminates** |
| `AppendFile` declaring `Content-Length: 64 GiB` | HTTP | **68,719,574,840 bytes allocated for an empty body** |
| `DeleteVersions` declaring 100M entries | HTTP | a ten-byte parameter **reserved 10.4 GB** |
| part `Size = -2` | storage grid | **a truncated shard reported healthy**; heal silently skipped |

Two of these had never been found before and are worth calling out.

**`RenameFile` with an empty source path** hits the volume-root alias and relocates the whole volume. Aimed at `.minio.sys`, one ordinary S3 GET afterwards yields the cluster's IAM and configuration. It requires **no traversal sequence at all** — so any audit that greps for `..` misses it by construction.

**A negative part size** floors both terms of `ShardFileSize` to zero. `checkPart`'s only integrity test is `st.Size() < expectedSize`, so **every file that exists is reported intact, including a truncated shard.** Worse, this holds whether or not the erasure parameters are valid: metadata that passes `FileInfo.IsValid()` — the very check healing trusts — is affected. That is not an input-validation problem but a **data-integrity** one: a legitimate heal reading poisoned metadata concludes the shard is fine and skips the repair.

## The fix: two chokepoints, not twenty patches {#fix}

The invariant to restore is one sentence: **a path from an internode payload must resolve inside the volume it names, and a volume must resolve inside the drive root.**

Only `..` can break the first half (absolute and backslash-prefixed paths are folded under `volumeDir` by `pathJoin`'s `Clean`), and the second half has one independent break: paths that **alias the volume root**. Two rules, therefore — not a policy matrix.

| Chokepoint | Location | Coverage |
| :-- | :-- | :-- |
| **Volume axis** | `getVolDir` (4 lines) | every caller, **including peer-S3** |
| **Path axis** | decorator at `getStorage()` | 31 remote entries plus nested fields |

Under 40 lines of core logic. **No handler is modified, no call site in `xl-storage.go` is touched, and the local erasure path is left alone.**

Two details worth recording:

- The check **must** run before the join, on the raw argument. `pathJoin` runs `Clean` against an absolute `drivePath`, which **erases** a leading `..` entirely — `/drive/../../etc` becomes `/etc`, so a check placed after the join reads clean and passes everything. This is the most likely way a future refactor silently undoes the fix.
- `NSScanner` is the one method that reaches the filesystem without `getVolDir`. Its guard line is **load-bearing**, not decorative.

Among the rejected alternatives, the notable one is adding containment at all 33 `pathJoin(volumeDir, …)` sinks. That would be genuine defence in depth, but it means 33 edits in the most performance-sensitive file in the tree, each needing its own judgement about whether the volume root is a legitimate target. The guard rails buy most of the same resistance to drift for a fraction of the risk. **This is an explicitly recorded IOU: if a code path is ever added that reaches the filesystem without `getVolDir`, the decision must be revisited.**

## Construction log: four regressions we caused ourselves {#regressions}

This section is unflattering and more informative than the fix.

**First: whitespace.** The initial rule treated whitespace as a separator, refusing `" "` and `"  "` — **legal S3 object keys**. `PutObject` commits through `RenameData`, so such a key would fail on every remote drive simultaneously and **break write quorum**. The irony: the vulnerability needs root credentials; this bug needs a user to send a space.

**Second: backslash-only keys.** Same function, same root cause. `path.Clean` never treats `\` as a separator, so on Unix `"\\"` is an ordinary filename. Refusing it made **a distributed cluster reject a write a single-node server accepts** — the same S3 API behaving differently by deployment topology.

**Third: spaces and periods on Windows.** The Win32 normalisation layer strips trailing spaces and periods from a path component, so a component made only of those vanishes and the path resolves to its parent. That makes both `" "` and `"..."` volume-root aliases on Windows — and `"..."` **was sitting in our own list of legal object names at the time.** We had not merely missed the vector; we had asserted it was safe.

**Fourth: negative part sizes.** The new guard rejected only "positive size with unusable parameters", equating "non-zero" with "positive". Negative values take a different route to the same zero.

## Two false greens {#false-greens}

Writing the `AppendFile` acceptance test produced two meaningless green runs in a row:

1. Driving it through the REST client — which **special-cases `*bytes.Reader` and derives Content-Length from it**, silently overriding the forged value.
2. Switching to an opaque reader — at which point **Go's own HTTP client refuses** to send a request whose body is shorter than the declared length.

Only driving the handler directly through `httptest` reproduced it. The lesson: **a client's self-protection is not a server's defence**, and an attacker with a raw socket has no such scruples.

A third was a design failure. We built a per-field reflection poisoner, **then discarded it**: it cannot distinguish "should have rejected but delegated" from "correctly allowed a non-path field" (`ETag`, `Algorithm`, …), so it reports correct behaviour as failure.

The subtlest lived in the fuzzer. The first property test treated separator-only strings as an **exception with an early return**. That is not an exception, it is a **blind spot** — the fuzzer had been shut out of the entire category by hand and could never have found the backslash key in a million executions. **A wrong exception is more dangerous than no fuzzer at all, because it creates the impression the space has been searched.**

## A very concentrated pattern {#pattern}

| Component | Where its semantics came from | Regressions |
| :-- | :-- | :-- |
| `guardPaths` | reused existing `hasBadPathComponent` | **0** |
| `getVolDir` guard | reused existing `hasBadPathComponent` | **0** |
| `isVolumeRootAlias` | **invented** | **3** |
| `guardErasureParams` | **invented** | **1** |

**The reused semantics produced zero regressions; the invented rules produced all of them.**

This is not coincidence. `hasBadPathComponent` is already the object layer's own rule via `IsValidObjectPrefix`, validated by real S3 traffic for years, and structurally cannot reject anything creatable through the S3 API. An invented rule has nothing behind it but the author's imagination.

The actionable form: **reuse rather than invent; and when you must invent, write the property test by exclusion rather than enumeration, express exceptions with a predicate independent of the implementation, and keep them as few as possible.**

## The guard rails matter more than the patch {#guardrails}

The final test suite pulls in two directions, and neither alone is enough:

- **Falsifiability** — remove each guard in turn and confirm the tests actually go red (191 failing subtests with the traversal guards removed; 64 GiB and 10.4 GB reappearing with the allocation guards removed). This is precisely what the rejected community PR lacked: its test asserted `err != nil` against a target that did not exist, so it **passes with the vulnerability fully intact**.
- **Legal-traffic fuzzing** — asserting that any key `IsValidObjectName` accepts, the guards accept (1.96M executions, no violations), and that any legal bucket name survives `getVolDir` (810K). This is what our own first two attempts lacked.

Plus a method-level reflection rail that **fails by name** when a path-taking method is added to `StorageAPI` unguarded.

History states the case for these rails bluntly: `CVE-2026-39414` was also point-fixed on 2026-04-15 and only received a `fix: complete ...` **two months later**. Counting this one, "point fix → recorded as closure → completed months later" has now happened twice in this fork. **The problem is not that someone was careless. It is that nothing in the tree could tell you a class was still open.** Guard rails turn "someone must remember" into "CI fails".

## On adversarial review {#adversarial}

This fix went through five rounds of independent adversarial review. **Each round found one missed defect, and all five stood**: whitespace keys → backslash keys → the `AppendFile` allocation → Windows spaces and periods → negative part sizes.

Our own review did find two in the same period (the `WithDeadline` log amplification and `ReadParts` using the wrong rule), but only after being pushed to that standard.

The hit rate says something plain: **the last gate before merge should be independent acceptance, not the author's own conclusion.** During this work the author judged the change ready to ship four times and was overturned three.

## Follow-up status {#open}

The first draft listed two implementation gaps. Both are now closed on the local branch, but none of these follow-up commits is in a published server release as of 2026-08-03:

- **`ReadFileHandler` is bounded.** Commit `5e11208cb` rejects a declared read length above 5 GiB, the maximum size of the S3 part represented by this legacy whole-file bitrot path. Legitimate GiB-scale reads can still allocate on that scale; the change removes caller-controlled allocation above the format's real ceiling rather than pretending large reads are cheap.
- **Negative part sizes cannot be persisted or trusted.** Commit `ef565d013` rejects them at the `AddVersion` write funnel and again in `CheckParts` and `VerifyFile`, so both new poison and already-written metadata are covered. The internode boundary check uses the same predicate.
- **Non-positive erasure block sizes are rejected at construction.** Commit `052d2a11b` validates `blockSize` in `NewErasure`, covering the other offset and decode divisions that a single downstream `ShardFileSize` guard could not. Rebalance's separate division is guarded at its own boundary.

Two limitations remain and should not be folded into a stronger claim:

- **No Windows CI.** Windows builds are published; tests run on Ubuntu only. The Windows rule is reasoned from documented Win32 behaviour and has not been verified on the platform.
- **Symlinks.** The containment check is lexical, as upstream's is.

## Closing {#closing}

The previous entry said that closing an endpoint and closing a defect class are two different conclusions. This time the known sinks are closed on the local branch, at the cost of four self-inflicted regressions and three overturned declarations that it was ready to ship. Publication remains a separate gate: the fixes above are not in a released server build yet.

If only one sentence survives: **the vulnerability was upstream's; our mistake was treating a point fix as a closure.** And what prevents a third occurrence is not a more careful person — it is a test that fails.
