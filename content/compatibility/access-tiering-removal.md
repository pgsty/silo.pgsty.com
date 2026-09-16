---
title: "Access-Tiering Removal"
linkTitle: "Access-Tiering Removal"
description: "Why the opt-in GET-frequency pool-tiering feature was removed, how to migrate builds that contained it, and what the upgrade acceptance did and did not prove."
url: "/compatibility/access-tiering-removal/"
weight: 7
type: docs
icon: fa-solid fa-code-compare
---

> **Release boundary:** the opt-in GET-frequency pool-tiering feature (community
> [PR #60](https://github.com/pgsty/silo/pull/60)) existed only in main/snapshot
> builds. The published Server 20260903 predates it, and upgrading from the
> published version needs **no** access-tier configuration cleanup. The removal
> merged as [PR #188](https://github.com/pgsty/silo/pull/188); only deployments
> that ran a build containing the feature need this page.

## Why it was removed {#why}

Access tiering was a default-off, opt-in scheduler that moved objects between
local server pools according to GET frequency. As shipped it dragged a
disproportionate maintenance surface across configuration, lifecycle parsing,
the usage cache, statistics, and the core multi-pool write path — for a
benefit that was never measured or claimed (no throughput, latency, or
lock-traffic numbers existed). The removal decision kept everything that was
independently correct:

- ordinary lifecycle expiration and transitions to remote tiers;
- rebalance and decommission;
- the general multi-pool write, metadata, healing and conditional-deletion
  fixes from PR #178, including shared remote-tier reference protection.

The keep/remove split was validated by isolation controls: reverting the PR
#178-era fixes wholesale failed 10 of 13 grouped checks, so they were
deliberately preserved while the tiering feature itself went.

## Before upgrading a build with access tiering {#before-upgrading}

1. Save a copy of the server ILM configuration and each affected bucket's
   lifecycle XML. Use an API client that preserves the nonstandard XML; do not
   rely on a client model that silently omits unknown elements.
2. On the old server, set `ilm access_tiering=off` and remove or disable any
   access-tier environment overrides. Let in-progress moves finish before
   replacing nodes. This reduces movement intermediate states; the removal
   itself changes no storage RPC protocol.
3. Remove top-level `AccessTierQuota` and rule-level `AccessTransition`
   elements. **Delete rules whose only action was `AccessTransition`.** For a
   mixed rule, retain its filter, status, ID, and ordinary
   expiration/transition actions. An access-only rule loads harmlessly after
   upgrade, but becomes an actionless rule and fails validation on the next
   lifecycle edit. If no rules remain, delete the lifecycle configuration
   through the S3 API.
4. Use a **coordinated maintenance window**: stop the deployment, install the
   same new binary on every node, then restart all nodes. The bootstrap check
   compares binary checksums *and* server environment settings — in a
   four-node test the first new node could not finish starting among three
   old nodes, and removing an old environment override on only some nodes can
   block startup even with matching binaries. Do not assume that an unchanged
   RPC protocol permits replacing one node at a time. The check runs only
   during startup; it is not a safety guarantee for nodes already running
   different binaries.
5. After restarting, verify object reads, bucket listing, ILM worker
   settings, and a lifecycle edit. Check storage access from **every
   request-serving node to each pool's drives**: successful reads or bucket
   listing establish less than complete drive reachability, and admin disk
   summaries only aggregate server-local state. Startup connection times
   vary, so a fixed sleep is insufficient.

## What happens to stored state {#stored-state}

| State | Behavior after removal |
| --- | --- |
| Ten old ILM keys | `access_tiering`, `access_pools`, `access_max_size`, `access_promote_watermark`, `access_bin_width`, `access_bins`, `access_flush`, `access_min_residency`, `access_workers`, `access_max_tracked` are accepted but ignored. Existing transition/expiration worker settings are preserved. |
| Admin configuration | Deprecated keys may still appear in `mcli admin config get ilm`; setting them may succeed but has no effect, even with `access_tiering=on`. Remove obsolete environment settings from deployment manifests. |
| Lifecycle XML | `AccessTierQuota` and `AccessTransition` are ignored when read and omitted when re-encoded. The same parser handles new PUT requests, so these extensions are also silently discarded there; access-only rules still fail action validation. |
| Data-usage cache | Both v8 and v9 caches are read, preserving ordinary counts, sizes, histograms, and remote-tier statistics. The retired hot-tier byte count is discarded; subsequent writes use v8. No feature-driven full statistics rebuild is required. |
| Objects already moved | Remain in their current pools with the same versions and timestamps. There is no bulk move-back or object metadata rewrite. |
| Internal leftovers | `x-minio-internal-ilm-atier` and `.minio.sys/config/ilm/access/` counter objects may remain unused. They need no cleanup service or object scan. |

Interrupted rebalance/decommission can leave the same version in more than
one pool independently of access tiering; removing the scheduler does not
remove such existing copies.

## What the upgrade acceptance did and did not prove {#acceptance}

The coordinated-upgrade procedure was validated **in a local four-node,
dual-pool experiment** (single Docker Linux host, tmpfs drives): three full
upgrade acceptances passed after a readiness-check correction, binding the
production code at `41aa84609`. The readiness method is reusable and is the
part worth copying: from each request-serving node, probe a unique,
never-written object key with `GetObjectTagging` — a path that waits for all
drives — and match the responses against real storage trace entries
(`storage.ReadVersion` returns the expected missing-object/version response),
requiring a real response on every node-to-drive path for three consecutive
rounds: 32 responses per round in this four-node, eight-drive topology.
`drive not found`, timeouts, and missing trace entries fail this check; an
unreachable drive is not a healthy drive reporting an absent object. Plain
per-node 404s or admin disk summaries do not establish this.

Two earlier upgrade attempts in the same series **failed** (a DELETE returned
204, then a node answered HEAD/GET with 503); those instances remain **open
and unattributed** — they were neither explained away nor converted into
passing results by the later successes. Distributed production upgrades
(cross-host, formal tags, packages, images) were **not** proven by these
experiments. Treat the acceptance as: the procedure is validated in the
tested topology, not that any distributed rollout is guaranteed.

## Version deletion scope {#version-deletion-scope}

The removal rode together with a repair of ordinary single-object
`DELETE ?versionId=...`, which now reconciles the addressed UUID, null
version, or delete marker across pools (including unqualified DELETE of a
directory marker). A successful request applies the deletion to every resolved
pool copy under existing per-pool quorum rules; pending outbound delete
replication retains `VersionPurgePending` until the replication worker
completes the purge — success does not guarantee immediate physical removal
from every drive. If a pool is unreadable these requests can return
`503 SlowDownRead` (or retain other error codes) even when another pool has a
readable copy; retry after recovery. Batch `DeleteObjects` already fans out
across pools. Incoming replicated deletes, lifecycle expiration, free-version
cleanup, and movement-internal calls keep their existing contracts — the
ordinary DELETE repair is not a guarantee for every source of deletion.

## Historical record {#record}

The feature's introduction, subsequent fixes, rollback scope, review history,
and the unresolved validation findings are preserved in the archived decision
record at pinned commit
[`40220bd836cb`](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/access-tiering-revert.md)
and in the repository's
[`docs/bucket/lifecycle/access-tiering-removal.md`](https://github.com/pgsty/silo/blob/main/docs/bucket/lifecycle/access-tiering-removal.md);
this page carries the operator-facing contract so neither is required
reading. Component status lives in the [version matrix](/compatibility/versions/).
