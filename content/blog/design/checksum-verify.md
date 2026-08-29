---
title: "Read-Only Checksum Audit and Reliable CLI Output"
linkTitle: "Checksum Verify"
date: 2026-08-29
lastmod: 2026-08-29
author: "Ruohang Feng"
summary: >
  MCLI can audit stored S3 checksums against logical object bytes without mutating data. This record defines selection, classification, report and exit semantics, and the non-TTY output contract required by pipelines and CI.
tags: [Design, S3, Compatibility, Checksum, mcli]
weight: 28
draft: true
url: "/blog/design/checksum-verify/"
---

This is the design and implementation record for MCLI's read-only checksum
verification workflow and [pgsty/mc#5](https://github.com/pgsty/mc/issues/5),
the non-TTY output defect found during release review.

> **Status:** implementation, local commits, real-S3 probes, subprocess tests,
> full unit/race, lint, vet, branding, credits, cross-builds, and clean local
> provenance are complete. Push, pull request, hosted CI, release, Server image
> integration, and public documentation deployment remain separate gates.<br>
> **Owner:** [`pgsty/mc`](https://github.com/pgsty/mc).<br>
> **Tracking:** [pgsty/mc#5](https://github.com/pgsty/mc/issues/5).<br>
> **Safety boundary:** verification is read-only; repair is not part of this
> command.

## Too Long; Didn't Read (TL;DR) {#tldr}

Historical CopyObject implementations could calculate a stored additional
checksum over transformed storage bytes instead of the logical bytes returned
by S3. `mcli checksum verify` inventories objects and independently streams the
logical body through the recorded algorithm. Each candidate becomes `MATCH`,
`MISMATCH`, `NO_CHECKSUM`, `UNKNOWN_*`, or `SKIPPED_*`.

The first implementation worked in a terminal but printed nothing when stdout
was redirected. MCLI automatically marked non-TTY execution as quiet to disable
progress UI, and the new command accidentally treated that internal state as a
user request to suppress audit records. The repair separates semantic output
from progress suppression without changing global quiet behavior or enabling
progress bars in CI.

## Command and scope {#scope}

```console
mcli checksum verify ALIAS/BUCKET/OBJECT
mcli checksum verify --recursive ALIAS/BUCKET[/PREFIX]
mcli checksum verify --manifest candidates.jsonl ALIAS
```

Version one supports CRC32, CRC32C, CRC64NVME, SHA1, and SHA256 checksums marked
as `FULL_OBJECT`. It can select one object, an exact VersionID, current objects
under a prefix, all versions, or exact entries from a JSON Lines manifest. It
also supports SSE-C key mappings, time and size filters, dry-run estimation,
bounded workers, download limits, JSON output, and an optional JSON Lines report.

It does not verify `COMPOSITE` checksums, infer type from an ETag, inspect
`xl.meta`, identify the historical writer with certainty, or repair metadata.

## Server checksum compatibility boundary {#server-boundary}

Amazon S3 currently defines ten additional-checksum algorithms. This SILO
release implements CRC32, CRC32C, CRC64NVME, SHA1, and SHA256. MD5, SHA512,
XXHASH64, XXHASH3, and XXHASH128 are not persisted or verified yet.

An unsupported `x-amz-checksum-*` value or trailer is rejected with HTTP 400
`InvalidArgument`; SILO no longer accepts the object while silently discarding
the caller's integrity assertion. This also means cross-vendor replication of
an object carrying one of the five unsupported algorithms fails visibly and
must be retried with a supported algorithm. Supported SDK control headers such
as `x-amz-sdk-checksum-algorithm` remain accepted when paired with a supported
value or trailer.

CRC64NVME is a full-object checksum only. Requests combining CRC64NVME with
`COMPOSITE` are rejected instead of being silently converted to `FULL_OBJECT`.
Comma-separated checksum trailer names are parsed individually; declaring more
than one checksum trailer remains invalid.

The release deliberately rejects rather than adding five new persisted
checksum type identifiers. Older nodes cannot interpret such identifiers
safely during a rolling upgrade. Adding those algorithms requires a separate
storage and mixed-version compatibility design.

## Read-only data path {#data-path}

For every selected object, MCLI:

1. sends `HEAD` with checksum mode enabled and retains every supported checksum
   plus `ChecksumType`;
2. rejects unsupported or ambiguous states as `UNKNOWN_*` instead of guessing;
3. streams `GET` logical bytes through bounded hashers without writing the body
   to disk;
4. uses VersionID pinning, or `If-Match` plus a second `HEAD` for mutable
   unversioned/null objects;
5. compares independently calculated values with the stored values.

The S3 boundary allows LIST, HEAD, and GET only. Tests fail if a write method
reaches the mock endpoint.

## Result and exit contract {#result-contract}

Every candidate produces one stable result:

| Result | Meaning |
|:--|:--|
| `MATCH` | Every supported stored checksum matches the returned logical bytes |
| `MISMATCH` | At least one stored checksum differs |
| `NO_CHECKSUM` | No additional checksum exists; the body is not read |
| `WOULD_VERIFY` | Dry-run found a supported full-object checksum |
| `UNKNOWN_*` | MCLI cannot make a reliable statement |
| `SKIPPED_*` | A filter intentionally excluded the object |

`--fail-on` accepts `mismatch`, `unknown`, `any`, or `none`. The default `any`
returns exit 1 for mismatches and incomplete verification. Dry-run does not
apply `--fail-on`. Argument, authentication, enumeration, and report-write
failures remain command failures rather than object classifications.

In particular, `SKIPPED_TOO_LARGE` makes the default `any` return exit 1 because
the size cap leaves the audit incomplete. Time-filter and delete-marker skips do
not fail by themselves.

## Output and automation contract {#output-contract}

Object records and the final summary are semantic output:

- Unless the caller explicitly sets `--quiet`, `-q`, or `MC_QUIET=true`, stdout
  receives every object record and the final summary in both TTY and non-TTY
  execution.
- Non-TTY `--json` emits exactly one compact JSON value per line. TTY JSON keeps
  MCLI's existing pretty presentation.
- Global flags work at the app, `checksum`, and `verify` levels.
- `--report` is independent of stdout. It still writes object records and the
  final summary as JSON Lines when explicit quiet suppresses stdout.
- Output transport does not change `--fail-on` decisions.

The distinction matters because MCLI's historical `globalQuiet` has two inputs:
an explicit quiet flag and an automatic non-TTY state used to disable progress
UI. Changing that global would risk re-enabling progress output across copy,
get, put, mirror, and other commands.

The selected repair is command-local. It walks the full CLI context chain for
explicit quiet/JSON flags because the CLI library's `GlobalBool` stops at the
nearest ancestor flag set. It also restores JSON Lines mode inside the checksum
action because nested `Before` hooks can reset it after an app-level `--json`.
No other command's progress or output behavior changes.

## Report, secrets, and operational cost {#operations}

On POSIX systems report files are created with mode `0600`; Windows relies on
the account's filesystem ACLs. Reports must not already exist and contain
metadata/results rather than object bodies or SSE-C keys. The manifest likewise
contains only bucket, key, and optional VersionID.

Verification downloads every supported object body. Operators should use
`--dry-run`, `--max-size`, time filters, `--max-workers`, and the global download
limit to bound cost and load. `NO_CHECKSUM` and `UNKNOWN_*` counts must remain
visible; neither may be presented as successful verification.

## What a mismatch proves {#meaning}

A mismatch proves only that the additional checksum returned at verification
time does not describe the logical bytes returned at verification time. It does
not prove that a particular historical compression defect created the object,
and it is not an external source-of-truth comparison.

Do not overwrite checksum metadata in place. Audit and classify first. For a
confirmed, operationally relevant mismatch, prefer a new key or new version,
verify the replacement, then switch consumers deliberately. Leave `UNKNOWN_*`
objects out of automatic repair.

## Verification record and release boundary {#verification}

The local acceptance matrix covers TTY human/JSON, non-TTY pipes, regular-file
redirects, app/parent/leaf JSON and quiet flags, environment quiet, report under
quiet, report-write failure, and MISMATCH/UNKNOWN exit status. It also includes
real historical `MATCH`, `MISMATCH`, and unsupported-composite objects on a local
S3 server.

Local commits are not a release. Close [pgsty/mc#5](https://github.com/pgsty/mc/issues/5)
only after the code and this decision record are merged and hosted `main` CI is
green. A signed tag, packages, container image, bundled Server client, public
deployment, and production audit remain later, separately evidenced gates.
