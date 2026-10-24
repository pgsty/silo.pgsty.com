---
title: "Bucket Configuration Replication: Source Times, Deletions, and Deterministic Convergence"
linkTitle: "Bucket Configuration Convergence"
date: 2026-09-12
lastmod: 2026-09-17
author: "Ruohang Feng"
summary: >
  The engineering and design record for SILO #77 (shipped in Server 20260916, PR #180): why source timestamps, deletion tombstones, and the whole-bucket metadata lock are all required; how six configuration types handle duplicates and reordering; why rollout requires a default-off switch; and which alternatives were rejected.
tags: [Design, Replication, S3]
weight: 6
draft: false
url: "/blog/design/bucket-metadata-convergence/"
---

[#77](https://github.com/pgsty/silo/issues/77) is a site-replication correctness defect repaired in [Server 20260916](/blog/release/silo-20260916/) ([PR #180](https://github.com/pgsty/silo/pull/180), commit [`48ec10312`](https://github.com/pgsty/silo/commit/48ec10312f98b494f75989615a5d24eae3207e44)). Before this repair, a receiving site overwrote the peer's source timestamp with local arrival time (`UTCNow`) and could then reject a genuinely newer deletion. In addition, several configuration types stopped exporting their timestamp once deleted, preventing heal from recovering a deletion missed during an outage. Adding a `DELETE` branch alone cannot solve both problems; convergence requires preserved source times, durable deletion tombstones, canonical comparison keys, and whole-record locking.

## Existing Work and Scope {#scope}

Earlier [release notes](/blog/release/silo-20260903/), the [20260903 hardening record](/blog/security/20260903-server-hardening/), and the [Server compatibility page](/compatibility/server/#limits) noted the [#77](https://github.com/pgsty/silo/issues/77) deletion limitation. This page records the state model, design trade-offs, and verification evidence (archived in [`docs/investigations/issue-77.md`](https://github.com/pgsty/silo/blob/114dc10529f242e1e22bafd0a08b1a096d69d4bc/docs/investigations/issue-77.md)).

| Prior work | What it repaired | Remaining gap addressed by #77 |
| :-- | :-- | :-- |
| [PR #91](https://github.com/pgsty/silo/pull/91) | Per-site configuration counts, Policy/Quota reporting, malformed-field isolation | Accurate counts do not establish convergence of field values and source times |
| [PR #103](https://github.com/pgsty/silo/pull/103) | Serialized writes to the whole `.metadata.bin` record | A write lock cannot validate an ordering decision made before acquiring the lock |
| [#76](https://github.com/pgsty/silo/issues/76), [#78](https://github.com/pgsty/silo/issues/78) | Object Lock replication payload and existing-bucket adoption protection | Does not provide a unified source-state comparison across all six configuration types |
| [CORS replication repair](/blog/design/cors-replication-trust/) | Dedicated per-bucket CORS deletion register and replication trust boundary | Specific to CORS; its semantics cannot be applied blindly to every metadata type |

This repair covers Policy, Tags, SSE, Quota, Versioning, and Object Lock. Lifecycle/expiry has its own merged-payload time semantics, and CORS retains its separate mechanism. Notification, IAM, [object replication reliability](/blog/design/replication-reliability/), MRF, resync, and public counters are separate subsystems.

## What the Reproduction Established {#evidence}

The original regression reproduced on both `ErasureSD` and 16-disk `Erasure` ObjectLayers. A peer `PUT` originated at a past time $T$, but the receiving disk stored its local arrival time. A subsequent `DELETE` carrying $T + 1\text{ minute}$ was rejected as older than the arrival timestamp. RPC success alone therefore did not produce the intended final state.

| Configuration | Pre-fix PUT preserves source time | Empty-event behavior | Pre-fix timestamp export when empty |
| :-- | :-- | :-- | :-- |
| Policy | No | Delete | Yes |
| Tags | No | Delete | No |
| SSE | No | Delete | No |
| Quota | No | Delete; zero-value JSON has separate semantics | No |
| Versioning | No | No operation | Not used as deletion |
| Object Lock | No | No operation | Not used as deletion |

Three further entry-point defects surfaced during investigation:

1. An older bulk event could overwrite a newer individual field.
2. A request that checked state before queuing for `metadata.lock` could act on an obsolete decision once it acquired the lock.
3. Remote Tag heal omitted `UpdatedAt` on outbound repair calls.

Each defect required a repair at its entry point in addition to fixing source selection in heal.

## The Facts a Field Needs {#state}

The state model reuses the existing payload, field `UpdatedAt`, and bucket `Created` fields in `.metadata.bin` without adding new disk formats, SDK fields, or persisted deployment IDs.

| State | Conditions | Eligible source |
| :-- | :-- | :-- |
| Unknown or invalid | Unknown creation time, invalid payload, or field time before creation | No; missing information cannot mean deletion |
| Empty baseline | Empty payload at zero time or `Created` | No |
| Live baseline | Valid nonempty payload at zero time or `Created` | Yes, for historical configuration initialization |
| Real update | Valid nonempty payload later than `Created` | Yes |
| Real deletion | Empty payload for a deletable field, later than `Created` | Yes; this timestamped empty value is a tombstone |

Empty Versioning and Object Lock events remain no-ops; sharing an ordering helper must not give those two types deletion semantics. Zero field times use `Created` as their comparison baseline without turning historical emptiness into a deletion.

Ordering applies four deterministic rules:

1. Real states (`UpdatedAt > Created`) outrank baselines.
2. Between real states, the later source `UpdatedAt` wins.
3. At equal timestamps, a deletion tombstone outranks a live value.
4. Conflicting live values at the same rank and timestamp resolve by comparing a canonical content key, with the lexicographically greater key winning.

For timestamped peer events and heal, an identical effective state triggers neither a disk save nor an event notification. A local write always allocates a new monotonic revision even when the visible payload is unchanged. Live baselines also use content-key ordering so a later creation default cannot outrank a real modification. Lexicographic tie-breaking guarantees deterministic convergence across sites; after conflicting concurrent edits, operators should still verify and resubmit the intended business configuration.

### Comparison Must Match Persistence {#canonicalization}

Replication status, heal source selection, and peer apply must compare the exact representation that persistence writes:

- **Policy:** Policy sets are map-backed in Go, so ordinary JSON encoding depends on map iteration order. The server recursively sorts the complete JSON tree of a validated policy—including `Statement`, `Action`/`NotAction`, `Resource`/`NotResource`, `Principal`, and `Condition`—while retaining `Sid` and numeric precision. Because the policy parser accepts `NotAction` and `NotResource` while the legacy struct's required `Action`/`Resource` marshaling could fail on empty sets, the server uses explicit field encoding across `GetBucketPolicy`, admin export, and peer replication. This prevents accepted negative-set policies from failing on subsequent reads or replication and ensures replication status and heal compare identical keys.
- **Quota:** Quota keys use the parsed quota configuration encoded as JSON. `{}`, JSON `null`, and valid zero-quota documents remain live documents rather than implicit deletions. Older senders converted a zero-quota `PUT` into a peer deletion while retaining a local document; with `mcli quota clear` sending a zero quota, upgraded peers retain that live zero document with capacity enforcement disabled on all sites. An empty Policy payload instead follows the established peer deletion rule: a valid empty-policy `PUT` clears the policy, and a subsequent `GET` returns `NoSuchBucketPolicy`.
- **XML configurations (Tags, SSE, Versioning, Object Lock):** XML types compare the validated document bytes directly without a general XML canonicalizer. Versioning requires one specific rule: apply the existing Object Lock constraint (`Enabled` required when Object Lock is active) before comparing the effective document. Otherwise, the comparator would accept a Versioning payload that `Save` immediately rewrites, causing heal to resend it on every cycle.

## Lock the Decision as Well as the Save {#atomicity}

All six fields share a single `.metadata.bin` record. Loading raw state, validating payloads, comparing timestamps, mutating fields, and saving to disk must all execute inside the existing `metadata.lock`. Comparing outside the lock permits stale decisions under concurrent writes, while splitting `metadata.lock` into per-field locks would allow whole-record read-modify-write operations to overwrite one another.

A local write allocates its revision timestamp inside `metadata.lock`:

```text
max(current UTC time, Created + 1ns, current field time + 1ns)
```

This monotonic rule lets a local operator correction advance beyond a previously stored future field timestamp. Timestamped peer events retain their originating `UpdatedAt` time, and identical or older timestamped peer states return early inside the lock without writing to disk.

Bulk processing validates all explicitly supplied fields and saves at most once. Omitting a field preserves its current state; an explicit `null` follows that type's deletion semantics, and any invalid field aborts the entire bulk update before persistence. Import assigns a single shared commit timestamp for the selected fields under the final per-bucket commit lock. Both disk persistence and outbound replication events use the normalized snapshot returned by that commit rather than re-reading storage after unlocking. Normalized empty Policies emit the dedicated policy deletion event so bulk JSON `omitempty` tags cannot drop them.

### Adoption Must Not Manufacture a Deletion {#adoption}

Bucket adoption can change `Created`. Moving `Created` earlier while retaining an empty field's old default timestamp would make an empty baseline look like a real deletion (`UpdatedAt > Created`). Moving `Created` later could invalidate historical initial values (`UpdatedAt < Created`).

Under the existing adoption lock, the server rebases only those six fields whose previous timestamp was zero or equal to the old `Created` timestamp. Real update and deletion timestamps remain untouched.

## One Rule Across Entry Points {#entry-points}

| Entry point | Required behavior |
| :-- | :-- |
| Local S3/Admin writes | Allocate monotonic `UpdatedAt` under `metadata.lock`; build outbound events from the committed snapshot |
| Typed peer events | Compare and persist original source `UpdatedAt` under `metadata.lock`; retain legacy Object Lock payload compatibility |
| Bulk/import | Track explicit field presence, validate all fields, and allocate the import timestamp under the final commit lock |
| Initial synchronization | Recover missing `Created` from physical disk probe; preserve live baselines; include real deletions when tombstones are enabled |
| Local/remote heal | Filter valid candidates before selecting the maximum; compare canonical keys; isolate failed peers |
| Status export | Pair value and `UpdatedAt` from one snapshot; gate newly exposed deletion timestamps behind the rollout switch |

Initial synchronization retains its existing five-type send path, while Versioning is initialized through `MakeBucketHook` and aligned through heal. When a bucket has no recorded `Created` time in `.metadata.bin`, `GetBucketInfo` returns the physical directory probe (matching `ListBuckets`), and initial synchronization passes that recovered timestamp to the bucket creation hook so configuration writes do not fail on metadata-free buckets.

Heal filters valid candidates before selecting the maximum state rather than seeding the winner from the first map entry and filtering defaults afterward. Public mismatch counters are not used as the sole heal gate: identical content with different source timestamps still requires synchronization, whereas identical effective states require neither a disk write nor an RPC.

## Why Rollout Needs a Default-Off Switch {#rollout}

The startup environment variable `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES` defaults to `off`. It controls whether newly exposed tombstone timestamps for absent Tags, SSE, and Quota payloads are exported in status and initial sync.

| Behavior | `off` (default) | `on` |
| :-- | :-- | :-- |
| Source-time ordering and atomic apply under `metadata.lock` | Active | Active |
| Live deletion RPC events | Replicated | Replicated |
| Existing Policy deletion-time export | Preserved | Preserved |
| Real deletion-time export for absent Tags/SSE/Quota | Hidden | Exported |
| Real deletions included in initial synchronization | Policy only | Policy, Tags, SSE, and Quota |

Unupgraded peers cannot safely consume all newly exposed deletion timestamps. For example, legacy Quota heal clears the raw payload while retaining an already parsed in-memory cache value. Keeping the switch `off` by default isolates rolling upgrades from that legacy behavior.

### Coordinated Upgrade and Rollback

1. Upgrade every node at every participating site to [Server 20260916](/blog/release/silo-20260916/) or later, verify consistent settings within each site, and drain in-flight requests.
2. Set `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES=on` across all sites and restart.
3. Before rolling back to an earlier release, set `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES=off` on every node, restart, and only then downgrade the binary.

While the switch is `off`, hidden Tags, SSE, and Quota tombstones can cause peers to send stale heal RPCs that upgraded receivers reject. Steady-state heal with zero metadata RPCs is reached once `on` is enabled across all sites.

## Kept and Rejected Alternatives {#minimality}

| Decision | Engineering reason |
| :-- | :-- |
| Retain one internal six-field ordering helper | All six types suffered the same arrival-time defect; one shared comparator prevents entry-point drift while preserving per-type deletion rules |
| Keep the whole-bucket lock, persistence fields, and heal interval | Provides atomicity, durable tombstone state, and missed-event recovery without introducing an external coordination service |
| Do more than replace `UTCNow` with source time | Replacing the timestamp alone leaves lock-external decision races, invisible deletes, equal-time ties, and initial-sync gaps unresolved |
| Gate newly exported tombstone times behind a switch | Legacy receivers and legacy Quota cache handling remain unsafe during a mixed-version rolling upgrade |
| Do not use deployment ID as a tie-breaker or add an HLC/schema | Existing timestamps and canonical content keys suffice for deterministic convergence without changing on-disk schemas |
| Do not reject all zero-time typed events | Legacy Tag heal omits `UpdatedAt`; accepting zero-time events with local monotonic time preserves backward wire compatibility |
| Do not impose one deletion rule across all bucket metadata | Versioning and Object Lock cannot be deleted, while Lifecycle and CORS have distinct merge and deletion structures |

The production change adds 729 lines and removes 692 lines of Go (+37 net lines), replacing duplicated per-type apply and heal branches with the shared state comparator. Every retained mechanism maps to a reproduced failure mode: removing whole-record locking reopens read-modify-write races, removing canonical Policy keys reintroduces permanent status/heal mismatches on negative-set policies, and removing the rollout switch exposes unupgraded Quota caches during rolling upgrades.

## Validation and Test Evidence {#validation}

Regression suites in `cmd/site-replication-metadata_test.go`, `cmd/site-replication-metadata-heal_test.go`, and `cmd/site-replication-metadata-gate_test.go` verify the contract across both `ErasureSD` and 16-disk `Erasure` backends:

| Test scope | Verified behavior |
| :-- | :-- |
| Source time, four deletable types, duplicate/reordered events, pre-lock queuing, cross-field writes | Regressions and `-race` checks pass on both ObjectLayers |
| Equal-time arrival in both orders, deletion priority over live values, canonical Policy keys, negative-set `GET`, bulk/import atomicity | Deterministic convergence regardless of event arrival order |
| Creation-time recovery and legacy-order Policy status | Real-drive ObjectLayer tests stamp bucket directory mtimes and verify that metadata-free buckets recover `Created` and converge without false status mismatches |
| Two-site process experiments (four drives per site) | Initial sync preserves `Created` across all six types; dropping an outbound `PUT` RPC and injecting reordered events converges on the next 30-second heal cycle |
| Missed deletions across source restart | Tombstones for Policy, Tags, SSE, and Quota survive source process restart and converge after reconnection |
| Steady-state quiescence and diagnostic deduplication | Two consecutive 65-second windows emit zero metadata RPCs after convergence; exceptional warnings deduplicate by bucket, field, and reason |

During test review, an early creation-time recovery test that used a stubbed ObjectLayer probe was replaced with a real-drive test that stamps bucket directories on disk—ensuring the test fails against unfixed `GetBucketInfo` code and passes only with the production repair.

### Implementation Review Progression {#review}

Across the review sequence from baseline `5c5765816` and initial implementation `1ee64a8d8`, three review findings (creation-time recovery on disk, legacy-order Policy status keys, and heal diagnostic deduplication) were fixed in `62cf066ff` and `fcbb93e89`, with final test formatting and lint validation completed at `461e9a721`.

## Operational Boundaries That Remain {#limits}

1. **Historical timestamp pollution cannot be reconstructed automatically.** Arrival-time overwrites and untimestamped legacy events have already lost their original source timestamps. After upgrading, inspect divergent buckets and resubmit the intended configuration or deletion at the authoritative site.
2. **Zero-time typed events remain compatible.** Untimestamped typed peer events allocate monotonic local time and emit a rate-limited `legacy-zero` warning; bulk imports still require valid timestamps.
3. **Bucket generation conflicts are not merged automatically.** Events with `UpdatedAt < Created` are skipped (`before-created`). Missing recorded `Created` timestamps are approximated from the bucket directory modification time on disk during configuration writes or initial sync. If physical creation time is still zero for an existing bucket, writes return `500 InternalError` (`404 NoSuchBucket` when the bucket is absent). Until a write or initial sync persists the recovered `Created` value, periodic heal skips the bucket in both directions.
4. **Physical clocks are not causal clocks.** Monotonic local allocation allows an operator correction to advance past a future field timestamp, but concurrent conflicting writes across sites still require operator review if business intent differs from lexicographic tie-breaking.
5. **Diagnostics are bounded per bucket, field, and reason.** `legacy-zero`, `before-created`, `indeterminate`, `unreachable`, and `peer-error` reuse `LogOnceIf` at warning level with hourly cleanup. Empty baselines and peers that do not yet have the bucket stay silent, while invalid stored payloads emit `indeterminate` without triggering outbound RPCs.

Related records: [Replicated Tag Ordering](/blog/design/replicated-tag-ordering/) · [Replica Metadata Normalization](/blog/design/replica-metadata-normalization/) · [Request Header Timeouts](/blog/design/request-header-timeouts/) · [Replica Metadata Audit](/operations/replication/replica-metadata-audit/)
