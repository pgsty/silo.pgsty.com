---
title: "Durable IAM Revocations"
linkTitle: "Durable IAM Revocations"
date: 2026-09-16
lastmod: 2026-10-23
author: "Ruohang Feng"
summary: "Persistent deletion revisions, signed parent boundaries, safe replay, coordinated upgrades and the limits of IAM recovery."
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/blog/design/iam-revocations/"
---

SILO retains the revision of every deleted IAM record so an offline site cannot resurrect a deleted identity or policy grant when it reconnects. This mechanism covers built-in users, service accounts, groups, policy documents, and policy mappings across the user, STS-parent, and group namespaces. When a built-in user is deleted, older service accounts, STS temporary credentials, and group memberships remain revoked even if an administrator later recreates a built-in user with the same name.

The persistent IAM revocation architecture (PR [`#191`](https://github.com/pgsty/silo/pull/191), [`#192`](https://github.com/pgsty/silo/pull/192), commit `f99ed829b5eba549160725f035156c9e020b6a07`) shipped in [Server 20260916](/blog/release/silo-20260916/) to close [SN-2026-013](/blog/security/20260916-release-hardening/#sn-2026-013); the scoped STS revocation extension for direct `RevokeTokens` operations ([`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce)) shipped in [Server 20261018](/blog/release/silo-20261018/#security). For multi-site rollout procedures, see the [IAM upgrade and recovery runbook](/operations/replication/iam-upgrade/).

## October 18: Scoped STS Revocation {#scoped-sts-20261018}

Commit [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) in [Server 20261018](/blog/release/silo-20261018/#security) extends the September durable revocation mechanism to direct `RevokeTokens` operations.

In earlier releases, a node could miss an issuance notification and revoke only the tokens present in its local memory cache. With this fix, `RevokeTokens` reads persisted STS identity records, merges them with in-memory entries, filters by the target parent identity and optional token type at the operation cutoff, and commits a dedicated tombstone for each matching immutable token key. Even if one key in the batch fails to save, all committed keys are immediately notified to sibling nodes and replicated to peer sites while returning the save error to the caller for retry.

Private IAM replication messages carry the token deletion marker and expiration time. A revocation message that arrives before its corresponding creation message still blocks subsequent replay, and a creation message with a newer event timestamp cannot resurrect an immutable token. Existing deletion healing retries offline delivery. Full IAM refreshes on both object storage and `etcd` rebuild STS revision records and evict revoked entries from the active cache even if concurrent IAM writes defer a full cache swap. Tombstones are retained until the token's natural expiration plus clock-skew allowance, or retained conservatively when expiration is unknown.

A single revocation snapshot covers STS identities known to the requesting cluster prior to the cutoff; tokens issued at an isolated site and never replicated into this cluster fall outside that snapshot. Keys issued after the cutoff, unrelated users, and reusable parent-policy mappings are unaffected. All participating nodes must be upgraded together because older binaries do not implement the private STS replication message.

**Execution cost:** An administrative revocation enumerates persisted STS identities and filters by parent and token type, so read volume and temporary map allocations scale linearly with active token count. The scan releases the authentication-cache lock while holding the IAM write serialization lock (`writeMu`), so concurrent IAM admin writes may briefly wait. `etcd`'s periodic refresh also reads STS records. Ordinary cached S3 authentication incurs zero extra network calls, and no new background timers or external dependencies are introduced.

Regression tests in [`iam-sts-revocation_test.go`](https://github.com/pgsty/silo/blob/0cd388c666f8211f552604ae73448a066e9c25ce/cmd/iam-sts-revocation_test.go) cover three-site outage/restart recovery and four processes sharing IAM storage. After upgrading, verify old-token rejection across endpoints, continued validity of newly issued tokens, and state recovery across restarts as detailed in the [upgrade procedure](/operations/replication/iam-upgrade/).

## Ordering and Persistence {#ordering}

Deletion records are stored at the original IAM configuration paths and contain the originating timestamp, `Deleted`, and any required `RevokedBefore` boundary; identity deletion records never store secret keys or session tokens. Normal IAM listings and policy evaluation hide deleted records automatically. Both object storage and `etcd` serialize version comparisons and writes per path using a distributed lock, persisting the originating source timestamp directly rather than overwriting it with the receiving node's local clock.

Revision ordering follows five deterministic rules:
- Older events never overwrite a newer revision; at an identical timestamp, a deletion wins over a live record.
- A deliberate local same-name recreation receives a revision newer than the stored deletion tombstone.
- If an older user or group deletion message arrives late after a same-name recreation, the server updates and retains its `RevokedBefore` boundary while keeping the newer recreated live record intact.
- Receiving an already-applied tombstone is a no-op that neither rewrites the record nor advances its revision.
- Cold-loading persisted IAM state on startup applies the exact same merge rules.

Writing the user or group revision is the authoritative commit point of a deletion; cleanup of policy mappings and child credentials follows afterward. A failure during dependent cleanup never rolls back the committed parent revocation: the API returns the cleanup error to the caller while still notifying sibling nodes on the same backend to reload the committed revocation state. Consequently, an `HTTP 500` cleanup error on admin delete does **not** mean the old identity remains active. Administrators can safely retry the deletion while keeping IAM writes and same-name recreation paused. When dependent cleanup fails after commit, the admin handler skips the immediate cross-site push hook and lets the background deletion-healing loop propagate the tombstone across sites. Sibling nodes reload current shared state upon notification, so a delayed notification cannot delete a subsequently recreated identity; `etcd` siblings also receive persisted changes via watches.

Operators must keep node clocks synchronized via NTP and monitor clock skew. Revision ordering relies on source wall-clock timestamps with monotonic advancement for consecutive local writes to the same path, without establishing cross-site causal ordering for concurrent writes.

## Users, Child Credentials, and Groups {#identities}

A recreated user retains its historical `RevokedBefore` boundary. Newly created service accounts and built-in STS credentials carry a cryptographically signed `siloParentRevocation` claim recording the parent revocation boundary known at issuance. Editing or replaying an old child credential never updates this signed claim; thus old children remain invalid even if their own `UpdatedAt` timestamp is newer than the parent deletion, whereas children minted for the recreated parent work normally. The claim is extracted from verified tokens during credential load and write.

In site replication, a service-account snapshot with a newer revision can replace an older service account with the same `AccessKey` (including deliberate owner changes or secret rotations), while local duplicate `AccessKey` creation remains rejected. Replicated snapshots preserve the `Disabled` status and the service account's own revocation boundary so older policy mappings cannot reattach to the replacement service account. Equal-revision retries reload the committed identity without rewriting storage. Periodic live healing compares source revisions directly—even when the public status summary is unchanged—and includes disabled identities as healing sources.

Service-account snapshots also preserve their absolute expiration timestamp instead of reapplying the receiving site's minimum lifetime for newly minted credentials. A newer but already-expired snapshot still supersedes the old key, is denied by authentication, and is collected into a durable service-account tombstone during normal loading. If cache or claim loading fails, the receiver returns an error to trigger retry rather than acknowledging prematurely; once a replacement commits, the stale cached secret is evicted immediately. If a replicated snapshot collides with an existing built-in user or cached STS identity of a different credential kind, the server rejects the type conversion and logs an error for explicit administrative resolution.

Each group member carries an individual `MemberGrants` timestamp. Adding or removing other members or toggling the group's enabled status does not refresh existing members' grant timestamps. A membership is effective only when its `MemberGrants` timestamp is newer than both the user's and the group's retained `RevokedBefore` boundaries; both group listings and IAM policy evaluation enforce the same effective-membership check. Peer replication snapshots preserve original grant timestamps (including unknown legacy timestamps) rather than treating a recent snapshot sync time as a fresh grant to a revoked user; only a new explicit administrative group grant restores group access.

The inherited live-group snapshot merge adds members incrementally and does not automatically reconcile an ordinary member removal missed during a site outage; the mechanism here governs user/group deletion boundaries and isolation across same-name recreation.

## Retention and Expiration Reclamation {#retention}

Tombstones for permanent identities (built-in users and service accounts), groups, policy documents, and policy mappings have no automatic TTL. Disconnected remote sites or cold backups may reconnect after arbitrary intervals; peer replay acknowledgements suppress redundant network sends but **never** trigger physical garbage collection of permanent tombstones.

When an immutable STS temporary token expires naturally, the server physically removes its token-key record and any legacy mapping without creating a permanent tombstone. Conversely, an explicitly revoked STS token retains its tombstone until the token's original expiration plus clock-skew allowance, blocking any replay carrying a later event timestamp. The `etcd` backend uses native expiration leases, while the object-storage backend reclaims expired STS tombstones during its existing credential load and purge cycles. Records with unknown expiration are retained conservatively.

Optional expiration-reclamation writes run best-effort under a short lock timeout budget: if a cleanup write fails, that load cycle halts optional reclamation, logs the error, and continues loading active users while leaving expired credentials denied under their existing durable revision until the next cycle retries. External IdP identity disablement is treated as an early revocation rather than natural expiration, so its cached STS tokens and service accounts are included in cleanup. Expiring service accounts retain a durable revision record because their `AccessKey` can be updated and reused and an earlier version might have had no expiration.

In the September `20260916` release, deleting a built-in parent user invalidated all older child credentials via the persisted parent boundary (including children absent from the deleting node's cache); cross-site per-token sync for direct `RevokeTokens` calls was completed by the [October 18 scoped STS extension](#scoped-sts-20261018).

## Healing Loop, Failure Handling, and Operational Cost {#healing}

Each server process starts a single background healing loop. Losing its distributed leader lease pauses the loop until leadership is reacquired rather than terminating it permanently, and configuration hot-reloads do not spawn duplicate loops. A 30-second interval separates leadership acquisition and each completed healing pass.

Normal IAM loaders maintain an in-memory index of deletion records and revocation boundaries (without secrets). The healing loop reads this in-memory index directly, avoiding a repeated full disk walk of `config/iam/` every 30 seconds; persistent storage records (including tombstones) are scanned only on process startup and full IAM refresh.

Healing sends batches of at most 128 records per peer. The sender tracks the highest revision acknowledged per path and peer, and unrelated mutations on either site do not reset existing acknowledgement progress. If a batch fails, it stays pending for retry while subsequent independent batches proceed; a lost response simply triggers a safe idempotent replay. Each pass has a bounded total duration, preserving acknowledgements received before timeout. The sync protocol reports both node name and process instance ID: load-balancer switching across known instances preserves acknowledgements, whereas a newly started process instance conservatively invalidates prior acknowledgements once to re-verify state. Always stop affected server processes before restoring persistent IAM state from backup so a restored node cannot reuse stale in-memory acknowledgements.

In steady state, healing iterates and sorts the retained in-memory set, checks peer protocol status, and suppresses repeated deletion `PUT` requests once acknowledged. Memory usage scales linearly with retained path count and peer count, while cold-start storage reads scale with total historical records. On first upgrade, existing live records that previously received different local timestamps on different receiving sites will trigger a one-time revision-alignment wave; factor those storage writes and sibling notifications into maintenance window planning.

Cached credential lookups check only the in-memory parent-revision index with zero extra storage I/O, while STS issuance and cold credential loads check the persisted parent revision. Revision I/O and distributed lock waits release the IAM cache read/write lock while a dedicated local writer mutex (`writeMu`) preserves per-node write ordering under bounded timeout contexts (see [IAM Policy Reloads: Lock Scope, Cancellation, and Time Budgets](/blog/design/iam-policy-cancellation/)).

## Replication Protocol and Coordinated Upgrade {#upgrade}

The versioned inter-site replication endpoint `/minio/admin/v3/site-replication/peer/iam-revisions` transports source revisions, member grant timestamps, and user/group revocation items without altering public Admin client SDKs or S3 APIs. Older server binaries reject this route, and the sender reports the sync failure directly rather than falling back to legacy routes that would strip revision metadata. Existing legacy IAM routes remain readable for backward compatibility.

All participating nodes—including nodes that share an IAM storage backend without site replication—must be upgraded together; mixed old/new binaries on the same backend and rolling downgrades are unsupported because older binaries do not understand tombstones or signed parent boundaries. Execute coordinated upgrades during a planned maintenance window:

1. Pause all IAM mutations and isolate any offline site or backup whose state is unknown.
2. Back up each site's underlying IAM storage and required KMS/encryption keys; online IAM admin exports omit deletion tombstones and cannot substitute for a storage-level backup.
3. Stop all nodes sharing the same IAM backend, replace the binaries, and start them on the new version. Resume IAM writes only after all participating sites are upgraded.
4. Inspect IAM load logs, site-replication status, and revocation convergence metrics; verify that representative revoked credentials are rejected and newly issued credentials succeed.
5. Explicitly reconcile any revocations lost prior to upgrade: delete surviving stale records on sites that still hold them, and rebuild long-offline peers from approved state before reconnecting them rather than joining an unknown old snapshot to the cluster.

Child credentials issued by pre-upgrade binaries for a recreated parent lack the signed `siloParentRevocation` claim and must be reissued after upgrading; parent identities that have never undergone deletion and same-name recreation keep their existing credential behavior unchanged.

Unmodified built-in policies remain protected against local deletion. If an administrator explicitly overrides a built-in policy and later deletes that override, the durable deletion tombstone prevents reload from automatically recreating the default built-in policy; to restore it, run an explicit policy-create operation. Deleting a non-existent policy locally remains idempotent without creating a tombstone, whereas a replicated deletion for an unknown policy retains its revision record.

To roll back, stop and isolate the affected sites and audit permission changes since the backup before restoring compatible state. Restoring an older backup discards revocations committed after the backup point and requires permission reconciliation and key rotation before reopening traffic. Never manually delete tombstone files online or convert only live records to force an older binary to start.

## Regression and Performance Verification {#verification}

Focused regression suites reside in `iam-revocation_test.go`, `iam-revision_test.go`, `iam-revision-lock_test.go`, `iam-revision-boundary_test.go`, `iam-replication-protocol_test.go`, `iam-credential-retention_test.go`, `iam-peer-reload_test.go`, and `iam-replay_test.go`. Point `SILO_TEST_IAM_REVOCATION_ETCD` at a disposable `etcd` instance to run the `etcd` lifecycle, distributed lock, and boundary suites under isolated key namespaces.

Benchmarks cover:
- `BenchmarkIAMCachedCredential` and `BenchmarkIAMSetTempUser`: baseline latency for cached authentication and temporary user issuance.
- `BenchmarkIAMRevisionConvergedHealing`: steady-state in-memory index traversal and zero-duplicate-`PUT` verification at 1,000 and 10,000 retained records.
- `BenchmarkIAMColdLoadExpiredServices`: cold-start loading and cleanup latency with 100 or 1,000 expired reusable credentials (run with `-benchtime=1x`).

## Error Semantics and Observability {#errors}

**October 23 update ([`pgsty/silo#250`](https://github.com/pgsty/silo/pull/250)):** [LDAP Long DNs](/blog/design/ldap-long-dn/) distinguishes a pure-ASCII path component that exceeds 255 bytes (and therefore could never be persisted on the object IAM backend) from an existing record that cannot currently be read. `loadIAMConfigBytesWithMetadata` translates only the former to `errConfigNotFound`; full-path length errors (`PATH_MAX`) and genuine storage failures still fail closed so an existing revocation record can never be masked. Writing direct user policies or parent-revision tombstones for overlong DNs remains unsupported on the object backend.

When an authoritative revocation revision commits to storage but a subsequent dependent cleanup step fails, the Admin delete endpoint may return `HTTP 500`; the old identity is already revoked. Pause IAM mutations and same-name recreation, retry the delete operation, and verify old-credential rejection across sites. Whenever a persisted parent revision cannot be read or token issuance cannot be committed, STS fails closed via `STSInternalError` rather than minting a credential with a guessed boundary.

Scrape each process's authenticated `/minio/metrics/v3/cluster/iam` endpoint for observability:

| Metric Name | Description |
| :--- | :--- |
| `minio_cluster_iam_revocation_records` | Total deletion tombstones and parent revocation boundaries in this process's in-memory index |
| `minio_cluster_iam_revocation_heal_failures` | Failed healing convergence passes since process startup |
| `minio_cluster_iam_revocation_heal_duration_millis` | Duration of the most recent healing pass in milliseconds |
| `minio_cluster_iam_revocation_heal_last_success_timestamp_seconds` | Unix timestamp (seconds) of the last successful healing pass |

Index metrics are reported per process; summing across sibling nodes sharing a backend double-counts shared records. Healing metrics advance only when site replication is enabled and the node holds the leader lease; in shared-backend deployments without site replication, zero values on the last three metrics are expected.

## Why Simpler Alternatives Fail {#alternatives}

In multi-site deployments with offline reconnection, simpler designs fail closed-world security invariants:

1. **Physical deletion without tombstones**: Deleting configuration files outright destroys the ordering evidence needed when an offline node or delayed replication message reconnects, allowing old snapshots to resurrect deleted identities.
2. **Comparing only the child credential's `UpdatedAt` timestamp**: After a parent user is deleted and recreated, a metadata edit or delayed replay on an old child credential would give it an `UpdatedAt` timestamp newer than the parent deletion and restore access; embedding the signed `siloParentRevocation` boundary at issuance prevents any post-issuance edit from crossing the parent deletion boundary.
3. **Overwriting source event timestamps with receiver local time**: Destroys source causality and turns an idempotent network retry into a new mutation with a newer timestamp. SILO preserves source timestamps and advances revisions monotonically only on deliberate local writes.
4. **Assigning a fixed TTL to permanent identity tombstones or exporting only live records**: Offline sites or cold backups can remain disconnected longer than any fixed TTL; expiring permanent identity tombstones or restoring live-only exports erases the historical boundary that blocks credential replay.

For implementation details, see [`cmd/iam-revision.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/iam-revision.go) and [`cmd/metrics-v3-cluster-iam.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/metrics-v3-cluster-iam.go).
