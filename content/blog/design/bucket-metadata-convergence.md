---
title: "Bucket Configuration Replication: Source Times, Deletions, and Deterministic Convergence"
linkTitle: "Bucket Configuration Convergence"
date: 2026-09-12
lastmod: 2026-09-12
author: "Ruohang Feng"
summary: >
  The research and design record for SILO #77: why source times, deletion records, and the whole-bucket lock are all needed; how six configuration types handle duplicates and reordering; why rollout needs a default-off switch; and what the tests can and cannot establish.
tags: [Design, Replication, S3, Review]
weight: 6
draft: false
url: "/blog/design/bucket-metadata-convergence/"
---

[#77](https://github.com/pgsty/silo/issues/77) is a reproduced site-replication correctness defect. A receiver replaces source time with arrival time and may then reject a genuinely newer deletion. Some configuration types stop exporting their timestamp after deletion, preventing heal from recovering a delete missed during an outage. Adding a DELETE branch alone cannot solve both problems.

> **As of 2026-09-12:** the repair and research archive are in [PR #180](https://github.com/pgsty/silo/pull/180), awaiting successful checks before merge. The baseline is main `5c5765816`; acceptance source `461e9a721` has production code identical to `fcbb93e89`, and `114dc1052` only adds the research archive. All commits carry DCO sign-off. No release or deployment has been performed.<br>
> **Review boundary:** the plan went through four Claude Code Opus 5 Max review rounds, passing the final two. Full implementation review, remediation review, and focused final acceptance returned `GO_WITH_NONBLOCKING_NOTES` in all three rounds. Final blockers are zero; the requested full cmd and final lint checks have now passed.<br>
> **Applicability:** this page describes a repair candidate. It does not establish that existing downloads or running installations provide these behaviors.

## Existing work and scope {#scope}

The earlier [release notes](/blog/release/silo-20260903/), [security hardening record](/blog/security/20260903-server-hardening/), and [Server compatibility page](/compatibility/server/#limits) already document the #77 deletion limitation. They do not provide a complete record of its state model, alternatives, or verification boundaries. This page supplies that reasoning.

The [source repository archive](https://github.com/pgsty/silo/blob/114dc10529f242e1e22bafd0a08b1a096d69d4bc/docs/investigations/issue-77.md) retains the original reproduction, plan versions, final reports and invocation identities for all seven review rounds, finding dispositions, executed test logs, source/binary hashes, and a rerunnable two-site driver. Raw model reasoning streams, binaries, and temporary lab volumes are excluded. Original artifacts and copies with normalized workstation paths and document links have separate hashes.

| Existing work | What it repaired | What it does not establish |
| :-- | :-- | :-- |
| [#91](https://github.com/pgsty/silo/pull/91) | Per-site configuration counts, Policy/Quota reporting, malformed-field isolation | Accurate counts do not prove convergence of values and source times |
| [#103](https://github.com/pgsty/silo/pull/103) | Serialized writes to the whole `.metadata.bin` record | A lock cannot validate an ordering decision made before acquiring it |
| [#76](https://github.com/pgsty/silo/issues/76), [#78](https://github.com/pgsty/silo/issues/78) | Object Lock's replication payload and existing-bucket adoption protection | They do not replace a consistent source-state comparison for six types |
| [CORS replication repair](/blog/design/cors-replication-trust/) | A separate per-bucket CORS deletion register and replication trust boundary | Its semantics cannot be applied blindly to every metadata type |

This repair covers Policy, Tags, SSE, Quota, Versioning, and Object Lock. Lifecycle/expiry has its own merged-payload time semantics; CORS keeps its separate mechanism. Notification, IAM, object replication, MRF, resync, and public counters are not rewritten. [Object replication reliability](/blog/design/replication-reliability/) has a separate record.

The supported release target is the maintained `silo`, `silo-console`, `mc`, and `silo-pkg` stack. Compatibility with unmodified upstream MinIO/MC remains best effort and does not require downgrading maintained components or recreating dependency forks.

## What the reproduction established {#evidence}

The original regression reproduced on both ErasureSD and 16-disk Erasure ObjectLayers. A peer PUT originated at a past time T, but the receiving disk stored current arrival time. A subsequent DELETE carrying T+1 minute was rejected as older. RPC success alone therefore cannot establish correct final state.

| Configuration | Original PUT preserves source time | Established empty-event behavior | Original timestamp export without payload |
| :-- | :-- | :-- | :-- |
| Policy | No | Delete | Yes |
| Tags | No | Delete | No |
| SSE | No | Delete | No |
| Quota | No | Delete; zero-value JSON has separate semantics | No |
| Versioning | No | No operation | Not used as deletion |
| Object Lock | No | No operation | Not used as deletion |

Three further entry-point defects matter: an old bulk event can overwrite a newer field; a request that checks state before queuing for the lock can act on an obsolete decision; and remote Tag heal omits `UpdatedAt`. Each requires a repair at the actual entry point, beyond changing source selection in heal.

## The facts a field needs {#state}

Reuse the existing payload, field `UpdatedAt`, and bucket `Created`. No disk format, SDK field, or persisted deployment ID is added.

| State | Conditions | Eligible source |
| :-- | :-- | :-- |
| Unknown or invalid | Unknown creation time, invalid payload, or field time before creation | No; missing information cannot mean deletion |
| Empty baseline | Empty payload at zero time or Created | No |
| Live baseline | Valid nonempty payload at zero time or Created | Yes, for historical configuration initialization |
| Real update | Valid nonempty payload later than Created | Yes |
| Real deletion | Empty payload for a deletable field, later than Created | Yes; this timestamped empty value is a tombstone |

Empty Versioning and Object Lock events remain no-ops. Sharing a helper must not give these types deletion semantics. Zero field times use Created as a comparison baseline; this does not turn historical emptiness into a new delete.

Ordering first gives real states priority over baselines, then compares source time between real states. At the same time, a deletion wins over a live value. Conflicting live values at the same rank use a stable content key, with the lexicographically greater key winning. An identical effective state causes neither a save nor a notification. Live baselines also use content-key ordering; a later creation default cannot outrank a real change.

This is deterministic conflict resolution. It does not mean a lexicographically greater configuration better expresses business intent. Operators must still choose and resubmit the intended value after conflicting concurrent changes.

### Comparison must match persistence {#canonicalization}

Policy sets are map-backed, so ordinary JSON encoding can depend on iteration order. The Server sorts the complete JSON tree of an already validated policy, including Statement, Action/NotAction, Resource/NotResource, Principal, and Condition. Sid and numeric precision are retained. This adds no syntax unsupported by the existing parser.

That parser accepts `NotAction` and `NotResource`, but the original structure's required Action/Resource encoding can fail on the corresponding empty sets. Explicit field encoding addresses this, and Policy GET/admin export use it too. The purpose is to keep an accepted policy readable, beyond making its comparison key deterministic.

Quota keys use the existing parsed representation encoded as JSON. `{}`, JSON `null`, and valid zero-quota documents remain live documents, not implicit deletion events. An empty Policy instead follows the established peer deletion interpretation: a valid empty-policy PUT succeeds, and a subsequent GET returns the existing NotFound response.

XML configurations use the bytes of a valid document. There is no general XML canonicalization layer. Versioning needs one exception: apply the existing Object Lock constraint before comparing the effective document that will actually be persisted. Otherwise comparison can accept a value that Save rewrites, causing heal to send it again next time.

## Lock the decision as well as the save {#atomicity}

The six fields share one `.metadata.bin` record. Loading raw state, validation, comparison, modification, and saving must all happen under the existing `metadata.lock`. Comparing outside the lock still permits stale decisions; separate field locks would allow whole-record read/modify/write operations to overwrite one another.

A local write allocates its time inside the lock:

```text
max(current UTC time, Created + 1ns, current field time + 1ns)
```

This lets a local correction advance beyond an already stored future field time. Timestamped peer events retain their original time. Identical or older states return without a write.

Bulk processing handles only explicitly supplied fields, validates them, and saves at most once. Omission preserves a field; explicit null follows its type's semantics. An invalid field cannot leave half the bulk update persisted. Import assigns a common time for the selected six-type fields under the final per-bucket commit lock. Disk state and outbound events use that commit's final snapshot, not a later read combined with an earlier time. A normalized empty Policy uses the existing dedicated deletion event so bulk `omitempty` cannot lose it.

The save helper returns its normalized snapshot. Public Update/Delete signatures stay unchanged, while other metadata retains its existing processing and notification behavior.

### Adoption must not manufacture a deletion {#adoption}

Adoption can change Created. Moving it earlier while retaining an empty field's old default timestamp makes an empty baseline appear to be a real deletion. Moving it later can invalidate historical initial values.

The narrow repair, under the existing adoption lock, rebases only these six fields whose previous time was zero or equal to old Created. Actual update and deletion times remain unchanged. An empty payload alone is not proof of a default, and existing-bucket configuration protection is not redesigned. Genuinely different bucket generations still require operator intervention.

## One rule across the real entry points {#entry-points}

| Entry point | Required behavior |
| :-- | :-- |
| Local S3/Admin writes | Monotonic time under the lock; use the committed snapshot for outbound events where needed |
| Typed peer events | Compare and persist original source time under one lock; retain existing types and legacy Object Lock payload compatibility |
| Bulk/import | Explicit field presence and atomic save; allocate import time at final commit |
| Initial synchronization | Preserve historical live baselines; include real deletions after opt-in |
| Local/remote heal | Use the same comparison for selection and apply, with complete source times; unknown IDs and failed peers do not block healthy targets |
| Status export | Value and time belong to one record; gate newly exposed deletion times during rollout |

Initial synchronization retains its existing five-type send path. Versioning is still initialized through MakeBucketHook and aligned through heal. No extra initialization path is added merely to make the table symmetric.

Heal filters valid candidates before selecting the maximum, instead of seeding from the first map entry and only then filtering defaults. Public mismatch counters cannot be the sole gate: equal content with different source times still needs synchronization. Conversely, equal effective states need no further write or RPC.

## Why rollout needs a default-off switch {#rollout}

The startup setting `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES` defaults to `off`. It controls visibility of newly exposed deletion information and does not detect remote capability.

| Behavior | off | on |
| :-- | :-- | :-- |
| Source-time ordering and atomic apply | Active | Active |
| Ordinary deletion events | Still replicated | Still replicated |
| Existing Policy deletion-time export | Preserved | Preserved |
| Real deletion-time export for absent Tags/SSE/Quota | Hidden | Exported |
| Additional real deletions in initial synchronization | Existing behavior | Include all four deletable types |

Old implementations cannot safely consume all newly exposed deletion information. For example, old Quota heal can clear the payload while retaining an already parsed cache value. An instruction to upgrade does not itself isolate this rolling-upgrade window, so the default stays off.

Upgrade every node at every participating site to a build containing the repair, ensure consistent settings within each site, and drain old requests. Then set `on` consistently and restart. Before a downgrade, first set `off` and restart every fixed node, then roll back the software. The old software's original defects return with it.

While off, hidden Tags/SSE/Quota tombstones can cause repeated stale heal RPCs that a fixed receiver rejects. A subsequent heal with zero RPCs is expected only when complete state is visible and stable.

## Retained and rejected alternatives {#minimality}

| Decision | Reason |
| :-- | :-- |
| Retain one internal six-field helper | The same source-time defect was reproduced across all six; shared ordering prevents entry-point drift while preserving type-specific deletion behavior |
| Keep the whole-bucket lock, persistence fields, and heal interval | They provide atomicity, durable deletion state, and missed-event recovery without another coordination service |
| Do more than replace UTCNow with source time | That alone leaves stale lock-external decisions, invisible deletes, equal-time conflicts, and initialization gaps |
| Do more than export tombstone times | Old receivers and Quota cache handling remain unsafe without controlling the rollout window |
| Do not use deployment ID as a tie-breaker or add an HLC/schema | Existing time and content keys suffice for the bounded contract; cross-site causal ordering is not claimed |
| Do not reject all zero-time typed events | Old Tag heal really omits time; preserve inexpensive protocol compatibility with an explicit limitation |
| Do not impose one deletion rule on all metadata | That would delete Versioning/Object Lock or violate separate Lifecycle/CORS rules |

The initial implementation adds 729 and removes 692 production Go lines, a net increase of 37, chiefly replacing duplicated apply and heal branches. Line count does not establish minimality. Necessity must connect each mechanism to a concrete failure; sufficiency must cover every real entry point; minimality asks which failure returns if a mechanism is removed.

## Validation and its limits {#validation}

The environment is local `go1.27.1 darwin/arm64`. Four groups of pre-implementation audit tests failed on the unfixed baseline. The resulting regression suite passes on both ObjectLayers; its main entry points are in `cmd/site-replication-metadata{,-heal,-gate}_test.go`. The [baseline audit log](https://github.com/pgsty/silo/blob/114dc10529f242e1e22bafd0a08b1a096d69d4bc/docs/investigations/issue-77/current-tests.log) retains the original failures alongside the passing existing tests.

| Validation | Observation |
| :-- | :-- |
| Source time, four deletions, duplicate/reordered events, queuing before the lock, different-field writes | Regressions and targeted race checks pass |
| Both equal-time arrival orders, deletion priority, Policy keys and negative-set GET, bulk/import | Boundary regressions and supplemental race checks pass |
| Full cmd package and internal/S3 Select race | Full cmd passes on final production code `fcbb93e89` (492.776 seconds); internal/S3 Select race passed at `62cf066ff` |
| Build, vet, lint, generated files, compatibility checks | Final production build/vet pass; lint reports zero issues at `461e9a721`. Generated-file and compatibility checks passed at `62cf066ff`. Optional typos is unavailable and skipped according to the Makefile |
| Linux/Darwin/Windows × amd64/arm64 | Six cross-compiles pass at `62cf066ff`; this is not runtime acceptance on six platforms |
| Two real site processes, four data directories per site | Initial synchronization preserves Created for six historical live configurations; normal 30-second heal restores consistency after dropping a real PUT's outbound RPC and injecting reordered events |
| Missed deletions and restart | Four deletion states persist across source-process restart and converge after reconnection |
| Quiescence and diagnostics | Two separate 65-second observations contain no metadata RPC across two normal heal cycles; repeated exceptional events deduplicate by bucket/field/reason |
| Fixed and pinned old implementation together | Tags PUT/DELETE smoke passes with all switches off; this does not prove complete mixed-version correctness |
| Review repairs: creation-time recovery, policy status key, heal diagnostics | Real ObjectLayer creation-time and legacy-order policy tests fail with old production code overlaid and pass after repair. Full cmd, internal packages, S3 Select race, lint, generated files, branding checks, and six cross-compiles were rerun at `62cf066ff` |
| Final cleanup regressions | Targeted diagnostic, initial-sync, physical-time boundary, adoption, and CORS race tests pass at `fcbb93e89`; related race tests pass again after test-style changes in `461e9a721` |
| Two-site acceptance repeated on the final binary | The same run passes on binaries built from clean `62cf066ff` and clean `fcbb93e89`; final `461e9a721` only changes test style and has identical production code |

Local evidence contains baseline failures, test logs, a rerunnable two-site driver, metadata snapshots, and source/binary SHA-256 identities. The first two-site binary reports `c8f264f79 + dirty`; its actual Go build-info and SHA-256 have now been recorded. After review repairs and cleanup, runs were repeated on binaries built from clean `62cf066ff` and `fcbb93e89`. Actual `--version`, Go build metadata, and SHA-256 identities are retained with the baseline binary built from `5c5765816`. Final `461e9a721` differs from `fcbb93e89` only in test formatting and equivalent conditional syntax; that diff is recorded separately.

These are local test and isolated-process observations. They do not replace GitHub Actions, real Linux multi-node cluster tests, artifact verification, or production deployment evidence.

## Adversarial review record {#review}

The plan used actual Claude Code `claude-opus-5 --effort max` for four rounds. The first two drove corrections to state comparison, committed snapshots, historical baselines, and import boundaries. The last two returned `GO_WITH_NONBLOCKING_NOTES` with zero pre-implementation blockers. Plan approval is not proof that implementation is correct.

The separate implementation review pinned `4089113e3` and used the same model and effort to inspect the complete diff, production call chains, formal tests, and runtime evidence independently, challenging sufficiency, minimality, rollout safety, and evidence identity. Its verdict was `GO_WITH_NONBLOCKING_NOTES`: no unconditional blocker, one conditional blocker, and nine further findings. It confirmed the core convergence mechanism and found no counterexample to ordering, deletion, or duplicate suppression within the declared contract. Three findings were real defects the change had introduced and were repaired in `62cf066ff`. The subsequent `fcbb93e89` closes the diagnostic gap when no valid source exists and adds an initial-sync regression.

| Finding | Assessment | Disposition |
| :-- | :-- | :-- |
| F1: a bucket with no recorded creation time can no longer write any of the six configurations | Confirmed regression, conditionally blocking | Repaired. `GetBucketInfo` returns the physical probe unchanged for a metadata-free request, as `ListBuckets` already did; initial synchronization recovers the time and passes it to the bucket creation hook |
| F2: replication status compares statement order while heal compares the canonical key | Confirmed; a permanent false mismatch that heal can never resolve | Repaired. Status compares the same key heal compares; per-site presence counting is unchanged |
| F3: one log key for four heal conditions, at error level for a normal transient | Confirmed | Repaired. Each reason keeps its own key at warning level. Empty baselines and missing buckets stay quiet; invalid existing state is still diagnosed when no valid source exists |
| F4: three user-visible semantic changes not written down | Partly valid | The original reviewed README already documented empty Policy and zero Quota at its end; the first review missed them. The addition covers Policy GET/export ordering and negative-set behavior |
| F5: whether the Policy encoder has unnecessary callers | The second review corrected the first assessment | Comparison and status keys must agree. GET/export/peer need the encoder to read or replicate negative-set policies that can already be persisted. PUT/import normalization is optional for comparison, but removing it adds branches and representation differences, so it stays |
| F6: an orphaned helper and a stale ordering comment | Confirmed nits | Comment corrected. The unused `isBucketMetadataEqual` and the obsolete test of that helper have been removed |
| F7: with the switch off, missed Tags/SSE/Quota deletions do not converge | A correct reading of the plan's trade-off | No change; stated in rollout and in the limits below |
| F8: evidence gaps - a stubbed recovery test, no legacy-order policy case, unverifiable binary identity | Confirmed | Recovery now runs on the real ObjectLayer; a permuted legacy policy case was added; the two-site acceptance was repeated on a binary built from the clean final tree, with identities recorded |
| F9: bucket generation conflicts | Declared out of scope, and not a regression | No change; see the limits below |
| F10: adoption moving Created later than a real field time | A coverage gap, not a defect | The case now fixes both sides: preserve historical time, exclude earlier-generation state as a source, and accept a valid adopted-generation input as a target |

A stub is worth calling out separately. The original recovery test injected an object layer whose creation probe returned the expected time, so it passed against code that could never behave that way in production. The replacement stamps the bucket directory on every local drive and drives the real object layer, and it fails on the unrepaired code.

The second review pinned `62cf066ff`, again using actual `claude-opus-5 --effort max`. It returned `GO_WITH_NONBLOCKING_NOTES` with zero conditional or unconditional blockers. It retraced production paths, checked the author's F1/F2 reproduction results from formal tests with old production code overlaid, and revised the first review's assessment of the Policy encoder. The reviewer did not execute the tests.

| Follow-up finding | Final disposition |
| :-- | :-- |
| NB-1: physical Created is an approximation | Retain the generation boundary and document directory-mtime limits. A real-drive test fixes the behavior: an earlier peer event is skipped and a local correction succeeds. One source timestamp cannot lower bucket identity |
| NB-2 and NB-8: silence without a source; lost source time in recovery-error logs | Repaired. Invalid existing states remain visible and recovery failures retain the event time. No source means no RPC; empty baselines stay quiet |
| NB-3: outage logs multiply by bucket and field | Accept and document the existing bucket/field/reason granularity; a site-wide log aggregation framework is outside this correctness repair |
| NB-4: draft logs are not product-failure evidence | Mark `findings-before.log` and `findings-after-1.log` as superseded fixture failures. Formal tests with old production code overlaid reproduce the physical-time, policy-order, initial-sync, and diagnostic defects separately |
| NB-5 and NB-6: unused helper; incomplete recovery-path description | Remove the helper and both tests that only exercised it. Document initial sync's persisted recovery and retain real CORS-path tests |
| NB-7: adoption covered only the source side | Add the target side: valid adopted-generation input replaces invalid earlier-generation state |

Diagnostic regressions now use the existing logger target to check warning level, distinct reasons, repeated calls, and zero RPCs. The initial-sync test drives a real source ObjectLayer and the complete outbound sequence; its peer only acknowledges RPCs. That proves outbound content. The real two-process experiment supplies a separate level of evidence, and the two must not be conflated.

The third focused acceptance pinned final production code `fcbb93e89` and again returned `GO_WITH_NONBLOCKING_NOTES`, with zero blockers. It also inspected the test-only style diff in `461e9a721` and confirmed equivalent semantics. Full cmd and lint were still running when the reviewer read their logs; both subsequently exited with code 0. Test formatting caused lint to fail at `fcbb93e89` itself; corrected `461e9a721` is the delivery baseline that satisfies the required checks.

Three nonblocking improvements remain outside this repair: heal diagnostics can show a zero source time after decode/parse failure; the initial-sync unit test does not execute the local peer branch and therefore does not prove that recovered Created is persisted locally (that production path was reviewed); and strict system-log capture could need isolation if concurrent background logging is introduced. No additional production accessor or test hook was added for these points. A counterfactual failure proves the assertion actually reached, such as empty-baseline noise. Warning-level and per-reason deduplication assertions pass after repair; that is not a claim that each was separately demonstrated failing on old code.

## Operational boundaries that remain {#limits}

1. **Historical timestamp pollution is not reconstructable.** Arrival-time replacement and old untimestamped events have lost source facts. Installing the repair cannot recover their true historical order. Inspect every site and resubmit the intended configuration or deletion at the authoritative site.
2. **Zero-time typed events remain compatible.** They use monotonic local time and emit `legacy-zero`; the existing zero-time constraint for bulk remains. These events are outside the timestamped-source convergence guarantee.
3. **Bucket identity conflicts are not merged automatically.** Resolve generation differences first. Events before target Created are not applied; unknown creation time is recovered only from a real physical bucket. Unknown or missing buckets are not written. The recovered value is a physical approximation from bucket-directory modification time. It can change with top-level entries, differ across drives, and be later than actual creation. Older source events are still skipped; one event is insufficient to lower the bucket identity. A successful configuration write or initial site sync records the recovered value. Until then, status reports the unknown time and periodic healing skips the bucket in both directions.
4. **A physical clock is not a causal clock.** Local correction can advance beyond an already known future field time, but cannot infer the business intent of all concurrent writes.
5. **Diagnostics are bounded; success does not mean applied.** `legacy-zero`, `before-created`, `indeterminate`, `unreachable`, and `peer-error` reuse LogOnceIf with stable keys and error text, details in attributes, and existing hourly cleanup. Each reason keeps its own key, so one condition cannot deduplicate another away. Empty baselines and peers that do not yet have the bucket stay quiet. Invalid existing states emit `indeterminate` even when no valid source can be selected, without causing an RPC. Normal duplicates and older events remain quiet. This is a per-bucket/field/reason bound: both unreachable-peer warnings and indeterminate-state warnings can grow with bucket and populated-field count, not a fixed site-wide limit.
6. **Code, integration, and release require separate acceptance.** Issue state, Server version, images, packages, published documentation, and production settings each need their own evidence. A local repair does not complete those deliverables.
