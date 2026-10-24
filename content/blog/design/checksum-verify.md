---
title: "Read-Only Checksum Audit and Reliable CLI Output"
linkTitle: "Checksum Verify"
date: 2026-08-29
lastmod: 2026-09-03
author: "Ruohang Feng"
summary: >
  MCLI can audit stored S3 checksums against logical object bytes without mutating data. Shipped in mcli 20260903 (PR #8, PR #13, #5), this record defines candidate selection, classification, report and exit semantics, and the non-TTY output contract required by pipelines and CI.
tags: [Design, S3, Compatibility, Checksum, mcli]
weight: 28
draft: false
url: "/blog/design/checksum-verify/"
---

This is the design and implementation record for MCLI's read-only checksum verification workflow and [pgsty/mc#5](https://github.com/pgsty/mc/issues/5), the non-TTY output defect discovered during release review. The command merged into [`pgsty/mc`](https://github.com/pgsty/mc) through pull requests [#8](https://github.com/pgsty/mc/pull/8) and [#13](https://github.com/pgsty/mc/pull/13) and shipped in [mcli 20260903](/blog/release/mcli-20260903/) (bundled in [Server 20260903](/blog/release/silo-20260903/) container images).

## Overview {#tldr}

Historical `CopyObject` implementations could calculate a stored additional checksum over transformed storage bytes (such as compressed or encrypted streams) rather than the logical bytes returned by S3 `GET`. `mcli checksum verify` inventories candidate objects and independently streams each logical body through the recorded checksum algorithm. Every candidate is classified into `MATCH`, `MISMATCH`, `NO_CHECKSUM`, `WOULD_VERIFY` (dry run), one of ten `UNKNOWN_*` classifications, or one of three `SKIPPED_*` results.

During release testing, the initial implementation worked in an interactive terminal but printed nothing when stdout was redirected to a file or pipe. MCLI automatically marks non-TTY execution as quiet (`globalQuiet`) to disable interactive progress bars, and the new command initially treated that internal flag as a user request to suppress audit records. The repair in [PR #13](https://github.com/pgsty/mc/pull/13) separates semantic command output from progress-bar suppression without altering global quiet behavior or enabling progress bars in CI.

## Command and Scope {#scope}

```console
mcli checksum verify ALIAS/BUCKET/OBJECT
mcli checksum verify --recursive ALIAS/BUCKET[/PREFIX]
mcli checksum verify --manifest candidates.jsonl ALIAS
```

Version one supports `CRC32`, `CRC32C`, `CRC64NVME`, `SHA1`, and `SHA256` checksums marked as `FULL_OBJECT`. It can select a single object, an exact `VersionID`, current objects under a prefix, all object versions, or exact entries from a JSON Lines manifest. It also supports SSE-C key mappings, modification-time and size filters, `--dry-run` cost estimation, bounded concurrency (`--max-workers`), global download limits, `--json` output, and an optional `--report` JSON Lines file.

The command is strictly read-only: it does not verify `COMPOSITE` multipart checksums, infer checksum types from an `ETag`, inspect raw `xl.meta` on disk, or mutate object metadata. The S3 endpoint must report the checksum type (`x-amz-checksum-type`) alongside the checksum digest; on an endpoint that omits the type header, every checksummed object is classified as `UNKNOWN_CHECKSUM_TYPE` rather than guessed.

`--rewind`, tier restore, server-side batch execution, checkpoint/resume, and repair are outside the current scope.

## Read-Only Data Path {#data-path}

For every selected object, `mcli checksum verify`:

1. Sends `HEAD` with checksum mode enabled and retains every supported `x-amz-checksum-*` digest plus `ChecksumType`.
2. Classifies unsupported or ambiguous metadata states as `UNKNOWN_*` instead of guessing.
3. Streams `GET` logical bytes through bounded in-memory hashers without writing the object body to local disk.
4. Uses `VersionID` pinning for immutable versions, or `If-Match` plus a post-read `HEAD` check for mutable unversioned and `null`-version objects to detect concurrent replacement.
5. Compares the independently calculated digests against the stored digests.

The S3 transport boundary permits `LIST`, `HEAD`, and `GET` only; automated tests fail if any write method reaches the mock endpoint.

A dedicated S3 helper retains all checksums and their type through `StatObject`, then reads logical bytes through `Core.GetObject` without the SDK automatic validator. This avoids changing shared `ClientContent` or the existing contracts for `stat`, copy, mirror, and JSON output.

## Result and Exit Contract {#result-contract}

Every candidate produces one stable classification:

| Result | Meaning |
| :-- | :-- |
| `MATCH` | Every supported stored checksum matches the returned logical object bytes |
| `MISMATCH` | At least one stored checksum differs from the returned logical bytes |
| `NO_CHECKSUM` | No additional checksum exists on the object; the body is not read |
| `WOULD_VERIFY` | `--dry-run` found a supported `FULL_OBJECT` checksum |
| `UNKNOWN_*` | MCLI cannot make a reliable verification statement (for example, `COMPOSITE` or missing `ChecksumType`) |
| `SKIPPED_*` | A filter intentionally excluded the object (`SKIPPED_TOO_LARGE`, time filter, or delete marker) |

The final summary carries `objects`, a `verified` count, the count of every result status, and `incomplete`. `verified` equals `MATCH` plus `MISMATCH`—the only classifications that actually streamed an object body through a hasher. A run that enumerated many objects and verified none is therefore explicitly visible.

`--fail-on` accepts `mismatch`, `unknown`, `no-checksum`, `any`, or `none`:

- The default `any` returns exit code `1` for any `MISMATCH`, `UNKNOWN_*`, or incomplete verification. In particular, `SKIPPED_TOO_LARGE` makes `any` return exit `1` because the size cap leaves the audit incomplete, whereas time-filter and delete-marker skips do not fail by themselves.
- `no-checksum` includes all `any` failures and also returns `1` when a checksum is absent or `verified == 0`.
- `--dry-run` does not evaluate `--fail-on`.
- CLI argument, authentication, listing, and report-write failures remain command errors rather than per-object classifications.

## Output and Automation Contract {#output-contract}

Per-object records and the final summary are semantic command output:

- Unless the caller explicitly sets `--quiet`, `-q`, or `MC_QUIET=true`, stdout receives every object record and the final summary in both TTY and non-TTY execution.
- Non-TTY `--json` emits one compact JSON value per line (JSON Lines); TTY `--json` retains MCLI's pretty-printed presentation.
- Global flags (`--json`, `--quiet`) work when placed at the root `mcli`, `checksum`, or `verify` command level.
- `--report` is independent of stdout: even when explicit `--quiet` suppresses stdout, `--report` still writes all object records and the final summary as JSON Lines.
- Output transport never alters `--fail-on` exit decisions.

This separation is required because MCLI's `globalQuiet` conflates two inputs: an explicit `--quiet` flag and an automatic non-TTY check used to disable interactive progress bars. Mutating `globalQuiet` globally would risk re-enabling progress bar output across `cp`, `get`, `put`, `mirror`, and other commands in CI logs.

Instead, the repair in [PR #13](https://github.com/pgsty/mc/pull/13) is command-local. It walks the full CLI context chain to inspect explicit quiet and JSON flags (because the CLI library's `GlobalBool` stops at the nearest ancestor flag set), and it restores JSON Lines mode inside the `verify` action after nested `Before` hooks run.

## Report, Secrets, and Operational Cost {#operations}

Report files (`--report`) use mode `0600` on POSIX systems and the account’s filesystem ACLs on Windows. They fail if the target path already exists and record only object metadata and verification results, with no object bodies or SSE-C keys. Input manifests (`--manifest`) likewise contain only `bucket`, `key`, and optional `versionId`.

Because verification streams the full logical body of every supported object, operators should use `--dry-run`, `--max-size`, modification-time filters, `--max-workers`, and the global download rate limit to bound network and storage I/O. `NO_CHECKSUM` and `UNKNOWN_*` counts remain explicit in the summary so unverified objects are never conflated with `MATCH`.

## What a Mismatch Proves {#meaning}

A `MISMATCH` result establishes that the additional checksum returned by `HEAD` at verification time does not match the logical bytes returned by `GET` at verification time. By itself, a mismatch does not identify which historical writer path produced the object (for example, whether a historical compressed `CopyObject` computed its checksum over compressed storage bytes or whether storage drift occurred), nor does it compare the object against an external source of truth.

Operators should never overwrite checksum metadata in place on disk. Audit and classify affected objects first. For a confirmed mismatch on an active object, write a replacement object under a new key or new version, verify the replacement with `mcli checksum verify`, and switch downstream consumers to the verified object. Keep `UNKNOWN_*` objects out of automated remediation scripts.

## Verification Record and Schema Contract {#verification}

The acceptance matrix covers TTY human and JSON output, non-TTY pipes, regular-file redirects, root/parent/leaf `--json` and `--quiet` flags, `MC_QUIET=true`, `--report` under quiet mode, report-write failures, `MISMATCH`/`UNKNOWN_*` exit codes, and real `MATCH`, `MISMATCH`, and unsupported `COMPOSITE` objects against a live SILO server ([`mc checksum verify` reference](/reference/minio-mc/mc-checksum-verify/#command-mc.checksum.verify)).

Automated JSON consumers should validate `schemaVersion: 1` and distinguish per-object records (`type: object`) from the final summary (`type: summary`). `--max-workers` defaults to `4` and accepts `1`–`64`, bounding concurrent object verification workers.

Tests also cover mismatches among multiple checksums, fixed and `null` versions, one result per candidate on normal completion, and clean result-stream closure after worker cancellation. `InvalidObjectState` is classified as a restore condition before generic HTTP 403 handling; SSE-C error classification does not depend on URL or object-name text.
