---
title: "SN-2026-002: Internode Path Containment Audit — Paying Off What CVE-2026-42600 Left Owing"
linkTitle: "SN-2026-002 · Internode Path Containment"
date: 2026-08-02
author: "Ruohang Feng"
description: "SN-2026-002 audits all four internode protocol surfaces after CVE-2026-42600, closing twelve inherited path-traversal, volume-root alias, divide-by-zero, and unbounded allocation defects while documenting four regressions caught before release."
tags: [Security, Path Containment]
weight: 90
draft: false
url: "/blog/security/internode-path-containment/"
---

**Status:** Released in [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) ([release notes](/blog/release/silo-20260804/#sn-2026-002))\
**Identifier:** `SN-2026-002` ([Security Advisories](/about/security-advisories/#sn-2026-002))\
**Fix commits:** [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670), [`b6f70ab08`](https://github.com/pgsty/silo/commit/b6f70ab08), [`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42), [`1af351a70`](https://github.com/pgsty/silo/commit/1af351a70), [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff)\
**Affected scope:** Distributed erasure deployments only; cluster-root / internode JWT required\
**Prerequisite reading:** [CVE-2026-42600 · ReadMultiple](/blog/security/cve-2026-42600/)

Following the removal of `/rmpl` (`ReadMultiple`) in [CVE-2026-42600](/blog/security/cve-2026-42600/), **SN-2026-002** audits every remaining internode endpoint carrying filesystem paths inside msgpack request bodies or Grid RPC frames. This advisory records that audit across all four internode protocol surfaces, the twelve inherited defects it uncovered, and the four regressions we introduced and caught while building the fix.

## Conclusions first {#summary}

- **Twelve defects across three unprotected protocol surfaces**, all inherited unchanged from upstream (verified by per-function checksum comparison across the affected storage files).
- **Same architectural root cause as CVE-2026-42600**: `ReadMultiple` was one endpoint on one surface; three protocol surfaces remained exposed to the same gap.
- **Four regressions introduced and caught during development**: every regression occurred in a rule we invented from scratch (`isVolumeRootAlias` and `guardErasureParams`), while reusing the object layer's existing `hasBadPathComponent` rule produced zero regressions.

## Why counting endpoints was the wrong frame {#four-surfaces}

Earlier spot checks kept counting individual handlers—arriving at 19, then 21, then 22—while missing an entire protocol surface each time. Grouping internode calls by how their arguments reach `xlStorage` reveals four distinct surfaces:

| Protocol surface | Entries | Covered by global HTTP query middleware |
| :-- | :-- | :-- |
| Storage-REST HTTP **query arguments** | 9 | **Yes** — previously misclassified as unprotected |
| Storage-REST HTTP **msgpack body** | 4 | No; `r.Form` is never populated from a msgpack body |
| **Storage Grid RPC** (`/minio/grid/v1`) | 18 | No; after the initial WebSocket upgrade, frames never re-enter the HTTP middleware chain |
| **Peer-S3 Grid RPC** | 5 | No; and it bypasses `getStorage()` to call `xlStorage` drives directly |

The first row corrects an earlier misconception: audits that grepped exclusively inside handler functions missed that the 9 query-parameter endpoints are already guarded by the global HTTP middleware (`url.ParseQuery(RawQuery)` in `r.Form`). Conversely, the fourth row (`peer-S3 Grid RPC`) bypasses `storageRESTServer.getStorage()` completely, meaning no amount of hardening limited to `storage-rest-server.go` could protect `DeleteBucket` or peer bucket metadata calls.

## Three stacked layers in the storage path {#root-cause}

Three independent design choices combined to create the vulnerability class:

1. **Path validation ran only on HTTP query strings**: The HTTP middleware inspects `r.Form`, which is populated from `url.ParseQuery(RawQuery)` and never from a request body (introduced in 2017).
2. **Grid RPC bypassed the HTTP middleware chain**: `/minio/grid/v1` performs a single HTTP upgrade; all subsequent msgpack RPC frames dispatch directly to registered handlers without re-entering HTTP middleware (introduced in 2023).
3. **`xlStorage` assumed callers had already validated paths**: `getVolDir` rejected a volume only when it equaled exact `""`, `.`, or `..`, and `pathJoin` ran `path.Clean` against the joined path (settled in 2018).

Each layer relied on another layer to validate paths, and none of them inspected the msgpack or Grid RPC channels in between.

One timeline interaction escalated a DoS bug from a failed request into a full process crash: `ShardFileSize` has contained an unguarded division by `DataBlocks` since 2020, but when `CheckParts` was wrapped inside `xioutil.WithDeadline` in October 2024 to bound slow disk operations, that division moved onto a bare goroutine where the HTTP server's `recover()` middleware could no longer catch a divide-by-zero panic.

## Vectors confirmed by execution {#vectors}

Every vector below was reproduced against a live `xlStorage` instance through the storage-REST and Grid RPC clients using planted sentinel files:

| Vector | Surface | Observed effect |
| :-- | :-- | :-- |
| `WriteAll("vol", "../../x")` | Storage Grid RPC | **Arbitrary file write** outside the drive root |
| `RenameFile(".minio.sys", "", "bucket", "x")` | Storage Grid RPC | **Relocates the entire `.minio.sys` system volume** (IAM, cluster config) into a readable S3 bucket **with no `..` sequence** |
| `DeleteBucket("../victim", force)` | Peer-S3 Grid RPC | **Recursive deletion of a directory tree** outside the drive root |
| `DeleteBulk("vol", "")` | Storage-REST body | Moves an entire volume into the drive trash directory |
| `ReadAll(volume: "../")` | Any surface | Trailing slash bypasses `getVolDir`'s exact `".."` check |
| `CheckParts` with zero `Erasure` (`DataBlocks = 0`) | Storage Grid RPC | Divide-by-zero panic in `WithDeadline` **terminates the server process** |
| `AppendFile` declaring `Content-Length: 64 GiB` | Storage-REST HTTP | **Allocates 68,719,574,840 bytes** for an empty request body |
| `DeleteVersions` declaring `100,000,000` entries | Storage-REST body | A 10-byte msgpack header **allocates a 10.4 GB slice** |
| Part metadata with `Size = -2` | Storage Grid / `AddVersion` | **Truncated shard is reported healthy**; healing silently skips repair |

Two vectors deserve specific attention:

- **`RenameFile` with an empty source path (`""`)**: An empty `srcPath` resolves to the volume directory itself. When pointed at `.minio.sys`, `RenameFile(".minio.sys", "", "bucket", "x")` moves the entire system metadata volume into a normal bucket, where an ordinary `GetObject` can read cluster IAM and configuration files—without using `..` anywhere in the payload.
- **Negative part size (`Size = -2`)**: A negative part size causes `ShardFileSize` to floor both terms to `0`. Because `checkPart` checks only `st.Size() < expectedSize`, any existing shard file (even a 0-byte truncated file) satisfies `0 < 0 == false` and is reported intact. Because `FileInfo.IsValid()` did not reject negative part sizes, poisoned `xl.meta` metadata caused background healing to skip corrupted shards silently.

## The fix: two chokepoints across 36 endpoints {#fix}

The security invariant has two parts: **every file path in an internode payload must resolve strictly inside its target volume, and every volume must resolve strictly inside the drive root.**

Because `pathJoin` folds leading slashes and backslashes under `volumeDir` via `path.Clean`, only `..` segments can escape a volume directory, and only volume-root aliases (`""`, `"/"`, `"."`, and Windows trailing-space/period components) can target the volume directory itself. Commit [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) enforces those two rules at two chokepoints:

| Chokepoint | Location | Coverage |
| :-- | :-- | :-- |
| **Volume axis** | `getVolDir` + explicit guard in `NSScanner` | Every `xlStorage` caller, **including peer-S3 Grid RPC** |
| **Path axis** | `getStorage()` decorator (`guardPaths`, `isVolumeRootAlias`) | All 31 remote storage-REST and Storage Grid RPC methods plus nested struct slices |

Two implementation details are critical to preserve during future refactors:

- **Checks must run on the raw argument before `pathJoin`**: `pathJoin` calls `path.Clean` on the concatenated absolute path (`/drive` + `volume` + `filePath`), which silently collapses `/drive/../../etc` into `/etc`. A check placed after `pathJoin` sees a clean path with no `..` and allows the escape.
- **`NSScanner` requires its own volume guard**: `NSScanner` is the only `xlStorage` method that constructs a volume path without calling `getVolDir`, making its explicit `checkPath` guard load-bearing.

We evaluated placing containment checks inside all 33 `pathJoin(volumeDir, ...)` call sites in `xl-storage.go`, which would require deciding at each of the 33 sinks whether the volume root itself is a valid target. Enforcing the invariant at `getVolDir` and the `getStorage()` decorator—backed by reflection guardrail tests on `StorageAPI`—covers all remote entry points without touching local erasure hot paths.

## Construction log: four regressions we caused ourselves {#regressions}

During development and review, our own drafts introduced four regressions before shipping:

1. **Rejecting whitespace object keys (`" "` and `"  "`)**: Our first draft of the path guard treated whitespace as an invalid path character, rejecting `" "` and `"  "`—which are valid S3 object keys. Because `PutObject` commits writes across drives via `RenameData`, uploading an object named `" "` failed on every remote drive and broke write quorum.
2. **Rejecting backslash-only keys (`"\\"`) on Unix**: The same draft rejected `"\\"`. On Unix, `path.Clean` treats `\` as an ordinary filename character rather than a directory separator. Rejecting `"\\"` in the internode decorator caused distributed clusters to reject a valid S3 key that single-node deployments accepted.
3. **Windows trailing spaces and periods (`" "` and `"..."`)**: The Win32 path normalizer strips trailing spaces and periods from path components, meaning a component composed solely of spaces or periods disappears and resolves to its parent directory. On Windows, both `" "` and `"..."` alias the volume root—and `"..."` was sitting inside our own positive test list of "valid object names" until review caught it.
4. **Negative part sizes (`Size < 0`)**: Our initial `guardErasureParams` check rejected zero `DataBlocks` only when `part.Size > 0`, equating "non-zero" with "positive" and missing that negative sizes floor `ShardFileSize` to zero even when `DataBlocks` is valid.

## Two false-green tests and a fuzzer blind spot {#false-greens}

Writing the reproduction and regression tests exposed three testing pitfalls:

1. **`storageRESTClient` silently overrode `Content-Length`**: When testing `AppendFile` with a forged `Content-Length: 64 GiB` over an empty `*bytes.Reader`, the client library inspected the `*bytes.Reader` type and overwrote `Content-Length` with `0`.
2. **Go's `http.Client` refused mismatched body lengths**: Switching to an opaque `io.Reader` caused Go's standard HTTP client transport to abort the request locally before sending it because the body closed before 64 GiB. Reproducing the server-side 64 GiB allocation required driving the handler directly via `httptest` (or a raw socket).
3. **An early return in the fuzzer hid the backslash bug**: Our first fuzz property test skipped strings composed solely of `/` and `\` via an early `return`. That early return blinded the fuzzer to `"\\"` across millions of executions until we rewrote the property test to assert strict inclusion against `IsValidObjectName`.

## Reused semantics vs. invented rules {#pattern}

| Guard component | Source of semantics | Regressions introduced during development |
| :-- | :-- | :-- |
| `guardPaths` | Reused existing `hasBadPathComponent` (`IsValidObjectPrefix`) | **0** |
| `getVolDir` guard | Reused existing `hasBadPathComponent` | **0** |
| `isVolumeRootAlias` | Newly written predicate | **3** |
| `guardErasureParams` | Newly written predicate | **1** |

`hasBadPathComponent` had already been exercised by production S3 traffic via `IsValidObjectPrefix` for years and structurally cannot reject any object key creatable through the S3 API. Every regression came from newly invented predicates where edge cases (`" "`, `"\\"`, `"..."`, `Size = -2`) diverged from S3 or OS semantics.

## Guardrail tests {#guardrails}

To ensure future changes to `StorageAPI` cannot silently reintroduce unguarded paths (avoiding the point-fix regression pattern previously seen with `CVE-2026-39414`), the test suite enforces three guardrails:

- **Falsifiability (mutation verification)**: Temporarily removing the path and volume guards causes 191 subtests to fail; removing the allocation guards reproduces the 64 GiB and 10.4 GB allocations.
- **Legal-traffic fuzz equivalence**: Fuzz tests verify that every object key accepted by `IsValidObjectName` passes `guardPaths` (1.96M executions) and every valid bucket name passes `getVolDir` (810K executions).
- **`StorageAPI` reflection guardrail**: A reflection test inspects every method on `StorageAPI` and fails CI by method name if a new method accepting path or volume arguments is added without an explicit entry in the decorator guard table.

```bash
go test ./cmd -run 'Test.*Containment.*|Test.*Guard.*|Fuzz.*' -count=1
```

## Independent review rounds {#adversarial}

Five successive rounds of independent code review each uncovered one real flaw before release: whitespace keys -> backslash keys -> the `AppendFile` 64 GiB allocation -> Windows trailing spaces/periods -> negative part sizes. Separating implementation from review caught all four S3 compatibility and integrity regressions before release.

## Follow-up fixes in Server 20260804 {#open}

Five companion commits shipped alongside [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) in [Server 20260804](/blog/release/silo-20260804/#sn-2026-002):

- **`ReadFileHandler` read-length cap (`b6f70ab08`)**: Commit [`b6f70ab08`](https://github.com/pgsty/silo/commit/b6f70ab08) rejects declared read lengths above 5 GiB (the maximum size of a single S3 part on this legacy whole-file bitrot path), preventing arbitrary caller-declared multi-tens-of-GiB allocations.
- **Negative part size rejection (`80e8eaa42`)**: Commit [`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42) rejects negative part sizes at the `AddVersion` write funnel and again in `CheckParts`, `VerifyFile`, and internode `guardErasureParams`, protecting both new writes and already-stored metadata.
- **Non-positive erasure block size rejection (`80e8eaa42`)**: Commit [`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42) validates `blockSize > 0` in `NewErasure` and guards rebalance division boundaries.
- **`ReadParts` storage error propagation (`1af351a70`)**: Commit [`1af351a70`](https://github.com/pgsty/silo/commit/1af351a70) fixes a pre-existing bug where `ReadPartsHandler` called `done(nil)` before the storage call completed, which had caused storage errors (`errFileNotFound` as well as new guard rejections) to be written as plain text into a msgpack keep-alive stream (`msgp: attempted to decode type "int" with method for "map"`).
- **Panic recovery in `xioutil.WithDeadline` (`a36fd8fff`)**: Commit [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff) recovers panics inside `WithDeadline`, logs `panic in deadline-bounded work: ...` with a stack trace to `stderr` (rate-limited to 10 stack dumps per process lifetime), and fails only the in-flight request. Operators who monitor node health should add a log alert for `panic in deadline-bounded work:`.

## Known limitations {#closing}

Two platform boundaries remain:

- **Windows test environment**: SILO publishes Windows binaries while automated CI runs on Linux; the Windows volume-root alias rule (`" "` and `"..."`) is derived from documented Win32 path normalization behavior.
- **Lexical symlink handling**: Path containment is lexical (`hasBadPathComponent` and `isVolumeRootAlias`), matching upstream `xlStorage` semantics, and does not resolve OS symlinks placed inside a drive root.
