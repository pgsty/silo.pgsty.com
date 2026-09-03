---
title: "mc checksum verify"
url: "/reference/minio-mc/mc-checksum-verify/"
weight: 14
upstream_modified: true
upstream_link: ""
---

<a id="command-mc.checksum.verify"></a>

The [`mc checksum verify`](#command-mc.checksum.verify) command compares the additional checksum stored by an S3 endpoint with a checksum independently calculated from the logical object bytes returned by that endpoint.

This is a **read-only audit command** introduced by [mcli 20260903](/blog/release/mcli-20260903/). It uses only S3 LIST, HEAD, and GET operations. It never repairs metadata, rewrites an object, or identifies which historical writer produced a mismatch.

The command supports stored `FULL_OBJECT` CRC32, CRC32C, CRC64NVME, SHA1, and SHA256 checksums. `COMPOSITE` checksums are reported as unsupported rather than guessed.

When this reference shows `mc`, use `mcli` if that is the installed executable name.

## Syntax {#syntax}

```shell
mc checksum verify [FLAGS] ALIAS/BUCKET/OBJECT
mc checksum verify --recursive [FLAGS] ALIAS/BUCKET[/PREFIX]
mc checksum verify --manifest FILE [FLAGS] ALIAS
```

Use exactly one selection mode:

- an object path verifies one object;
- `--recursive` verifies objects under a bucket or prefix;
- `--version-id` verifies one exact version;
- `--versions` includes every version selected by an object or recursive scan;
- `--manifest` reads exact bucket, key, and optional version identities from a JSON Lines file.

For an unversioned object, the command reads with `If-Match` and performs a second HEAD after the body is consumed. If the object changes during verification, the result is `UNKNOWN_OBJECT_CHANGED`, not a false mismatch.

## Result and exit-status contract {#results}

Every candidate produces one stable status:

| Status | Meaning |
| :-- | :-- |
| `MATCH` | Every supported stored checksum equals the independently calculated value. |
| `MISMATCH` | At least one stored checksum differs from the returned logical object bytes. |
| `NO_CHECKSUM` | The endpoint returned no additional checksum; the body is not downloaded. |
| `WOULD_VERIFY` | A dry run found a supported full-object checksum. |
| `UNKNOWN_*` | The command could not make a reliable statement, for example because the object changed or could not be read. |
| `SKIPPED_*` | A requested filter intentionally excluded the candidate. |

Normal completion exits `0`; a command or selected audit failure exits `1`. The default `--fail-on any` fails on mismatches, `UNKNOWN_*`, and objects skipped by `--max-size`.

`--fail-on` accepts:

- `mismatch` — fail only on a checksum mismatch;
- `unknown` — fail on a mismatch or any `UNKNOWN_*` result;
- `no-checksum` — also fail when a checksum is absent or the run verified zero objects;
- `any` — the default, including incomplete size-capped audits;
- `none` — report findings without turning them into an audit failure.

The final summary contains `objects`, `verified`, per-status counts, and `incomplete`. `verified` is `MATCH + MISMATCH`: use it when automation requires proof that at least one checksum was actually recomputed.

## Important flags {#flags}

| Flag | Purpose |
| :-- | :-- |
| `--recursive`, `-r` | Scan every object below the bucket or prefix. |
| `--versions` | Include all object versions. |
| `--version-id`, `--vid` | Select one exact version. |
| `--manifest FILE` | Read candidates from JSON Lines. Mutually exclusive with scan/version/time selection flags. |
| `--dry-run` | LIST and HEAD candidates without downloading object bodies. |
| `--max-workers N` | Bound concurrent reads; default `4`, range `1` through `64`. |
| `--max-size SIZE` | Skip objects larger than values such as `10GiB`; empty or `0` means unlimited. |
| `--older-than`, `--newer-than` | Filter by relative durations such as `7d10h31s` or supported absolute timestamps. |
| `--enc-c KEY` | Supply one or more SSE-C prefix-to-key mappings in raw Base64 or hexadecimal form. |
| `--report FILE` | Write object records and the summary to a new JSON Lines file. On POSIX systems it is created with mode `0600`. |
| `--json` | Emit compact JSON Lines when stdout is not a terminal. |

`--limit-download` remains available as a global rate limit. Object bodies are streamed through bounded hashers and are neither buffered in full nor written to disk.

## Manifest format {#manifest}

Each non-empty line identifies one candidate. `bucket` and `key` are required; `versionId` is optional:

```json
{"bucket":"archive","key":"2025/report.json","versionId":"optional"}
```

The alias appears once on the command line. The manifest contains neither checksums nor encryption keys.

## Examples {#examples}

Verify one object:

```shell
mc checksum verify mysilo/archive/report.json
```

Estimate the read cost before recursively verifying a prefix:

```shell
mc checksum verify --recursive --dry-run mysilo/archive/2025/
```

Verify all historical versions with four workers and require every selected object to carry a checksum:

```shell
mc checksum verify --recursive --versions --max-workers 4 \
  --fail-on no-checksum mysilo/archive/2025/
```

Verify candidates from an external inventory and keep a private JSON Lines report:

```shell
mc checksum verify --manifest candidates.jsonl \
  --report results.jsonl mysilo
```

> [!NOTE]
> A `MISMATCH` proves only that the checksum returned at verification time differs from the logical bytes returned at that time. It does not identify the historical cause or establish correctness against an external source of truth. If the server's own bitrot protection rejects a damaged shard before returning object bytes, the result is `UNKNOWN_READ_ERROR`, never `MATCH`.
