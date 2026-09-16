---
title: "IAM Upgrade and Recovery"
description: "Coordinate the IAM revocation upgrade, preserve complete deletion history, and rehearse recovery."
url: "/operations/replication/iam-upgrade/"
weight: 25
icon: fa-solid fa-user-shield
---

The IAM repairs in [Server #191](https://github.com/pgsty/silo/pull/191) and
[#192](https://github.com/pgsty/silo/pull/192) persist deletion revisions and
parent revocation boundaries. They prevent delayed site events from restoring
revoked identities and older grants. They require a coordinated upgrade of all
participating servers, including nodes without site replication that share an
IAM backend. Mixed old/new nodes on that backend and rolling downgrade are unsupported.

**Release status:** these repairs are in the [September source baseline](/compatibility/versions/#september-reliability),
not Server 20260903. This procedure is preparation for a build containing those
repairs. Isolated upgrade/restore observations and remaining recovery checks are
tracked in [#200](https://github.com/pgsty/silo/issues/200); see the
[validation scope](#validation). Publication of this page does not establish
production upgrade acceptance.

## Prepare the maintenance window {#prepare}

Inventory every node, site, shared IAM backend, offline peer and backup. Record
the old and candidate Server SHA, binary checksum or image digest, deployment
configuration, root-credential source, external identity-provider settings and
KMS dependencies. Select the matching maintained components from the
[component matrix](/compatibility/versions/); a standalone Console update does
not replace the Console embedded in a Server binary.

Use protected, preconfigured `mcli` aliases. These commands read state; run them
for each site and retain the outputs privately. Replace `site-a` with the actual
alias. Do not collect credentials or enable HTTP debug logging in shared evidence.

```bash
umask 077
mkdir -p iam-upgrade-evidence
mcli --version > iam-upgrade-evidence/client.txt
mcli --json admin info site-a > iam-upgrade-evidence/site-a-info.jsonl
mcli --json admin replicate status site-a > iam-upgrade-evidence/site-a-replication.jsonl
mcli ready site-a
```

The replication command applies to sites with site replication configured.
Readiness alone does not verify IAM correctness. Check clock synchronization on
every node (for example, `chronyc tracking` on a chrony-managed Linux host), IAM
load errors and replication failures. Repair clock drift before the upgrade:
ordering uses timestamps, and a trusted peer's future-dated deletion can reject
subsequent older updates until a newer revision is used.

Pause IAM administration and credential issuance, including automation. Isolate
unknown offline peers and prevent automatic restarts of old binaries. Drain
application traffic for the coordinated stop. Establish a list of revoked
identities, recreated parents and credentials requiring reissuance. Missing
deletion history cannot be reconstructed from a missing user record.

**Stop here** if any participating node, backend, backup, required key, unknown
peer or rollback procedure is unaccounted for. Do not admit an old snapshot to a
live replication group merely to inspect its contents.

Before upgrading, follow the [password-policy migration](/compatibility/password-permissions/).
Where an existing `Deny admin:CreateUser` also meant to prohibit changing one's own
password, add `admin:ChangeMyPassword` to the same Deny with its existing scope and
conditions; retain both through rollback. Current main keeps multipart listing in
`legacy` by default. An ordinary upgrade does not require strict mode; only an
explicit opt-in needs the [multipart preflight and drain procedure](/blog/design/list-multipart-uploads/#implementation).

## Preserve a complete recovery point {#backup}

Stop all SILO processes sharing each backend before taking the final recovery
point. For systemd, use the deployment's actual unit, then verify it is inactive
on every node. For an operator-managed deployment, use its tested maintenance
procedure and prevent reconciliation from restarting old Pods.

```bash
SILO_UNIT='silo.service' # replace with the installed unit name
sudo systemctl stop "$SILO_UNIT"
systemctl is-active "$SILO_UNIT" # expected: inactive; nonzero exit is normal
```

| Backend | Required recovery material | Verification before proceeding |
| --- | --- | --- |
| Object storage | A consistent, restorable backup of the complete IAM store, including revisions, deletion records and retained parent boundaries. Use the deployment's tested full-storage snapshot/backup procedure with all required pool/set/drive mappings. | Restore to an isolated clone with the matching topology and confirm IAM loads. Copying a visible user directory or one erasure-coded drive is insufficient. |
| etcd | A complete etcd snapshot, member/topology configuration, certificates and authentication material, plus SILO's endpoint/prefix and encryption configuration. | Check the snapshot, then restore to an isolated etcd cluster using the documented procedure for that etcd version. Do not restore a shared etcd cluster over unrelated workloads. |
| Both | Exact binaries/images, deployment configuration, root-secret references, KMS/key recovery material and the revocation/change ledger since the backup. | Verify access to the required keys independently of the cluster being replaced. Store secret material separately from review logs. |

For etcd, use the deployment's authenticated TLS configuration and a supported
`etcdctl`/`etcdutl` version; see the [etcd recovery guide](https://etcd.io/docs/v3.6/op-guide/recovery/).
The following are backup/check commands; they do not
restore a running cluster:

```bash
etcdctl --endpoints="$ETCD_ENDPOINT" snapshot save iam-upgrade-evidence/etcd.db
etcdutl snapshot status iam-upgrade-evidence/etcd.db --write-out=json
```

A live `mcli admin cluster iam export` contains useful live records but omits
deletion history. It is **not** the recovery point for this upgrade. A snapshot
checksum proves file identity; it does not prove that restore and revocation
checks work. Record the backup's time, scope, checksum and successful clone
restore separately.

## Upgrade and verify {#upgrade}

1. Replace binaries/images on **all** stopped nodes of each shared backend.
   Start only upgraded nodes. Keep unknown/old peers isolated and complete the
   coordinated upgrade across sites before relying on the new guarantees.
2. Repeat `mcli --json admin info site-a`, `mcli ready site-a` and
   `mcli --json admin replicate status site-a`. Verify the actual identity of
   every process, clean IAM loading and working cross-site communication.
   Run the write-readiness check against each process endpoint, not just a load
   balancer. On distributed nodes, confirm `IAM load(startup) finished.` in each process's
   current startup log and, when site replication is configured, also
   `Cluster replication initialized`. `/minio/health/ready` and successful root requests
   can precede these background initializers. Wait for both before issuing STS
   credentials; the startup messages still do not replace the credential checks
   below.
3. Check IAM metrics for revision counts, healing failures and last successful
   healing. A quiet error counter alone does not prove credential revocation.
   The background pass runs periodically; its interval is not a convergence SLA.
4. On every site, use designated canary aliases to read the same pre-existing
   object. An old revoked credential must fail authorization; a deliberately
   reissued credential with the required policy must succeed. A timeout, 5xx or
   missing object is inconclusive. Preserve the error code, site and credential
   label, never its secret.

   ```bash
   mcli --json stat --no-list revoked-canary/upgrade-canary/probe
   mcli --json stat --no-list reissued-canary/upgrade-canary/probe
   ```

5. Reissue service-account/STS credentials belonging to a recreated parent.
   Older credentials lack the retained parent boundary required after
   revocation. Parents with no retained revocation history keep their existing
   credential behavior. Attach only the intended current grants.
6. Explicitly reconcile known pre-upgrade deletions on sites still holding old
   records. Rebuild stale offline peers from approved state before reconnecting
   them. Repeat the credential checks after restart and peer catch-up.

Deleting an explicit override of a built-in policy now leaves a durable deletion;
reload does not recreate that policy. Restore an intended policy through an
explicit policy-create operation. Ordinary legacy group-member removal during
an outage remains outside the durable parent-deletion guarantee.

Reopen access only after version identity, backend recovery, IAM loading,
replication and both credential checks pass. If a stale credential succeeds,
keep affected sites isolated and investigate; restarting until health is green
does not resolve the authorization failure.

## Errors and observability {#observability}

A revocation can persist and then return HTTP 500 with
`IAM revocation committed; cleanup failed` when dependent cleanup fails. This does
not roll back the revocation. Keep IAM writes paused, inspect the identity and
logs, and retry cleanup; do not blindly repeat deletion after a same-name identity
has been recreated. This path publishes to local sibling caches but may skip the
immediate cross-site hook, so verify later site reconciliation. STS fails closed
with `STSInternalError` if it cannot read the parent revocation boundary; that is
neither successful issuance nor proof of a revoked credential.

Collect these from every process at `/minio/metrics/v3/cluster/iam`:

| Metric | Meaning |
| --- | --- |
| `minio_cluster_iam_revocation_records` | Persistent revocation records observed by this process |
| `minio_cluster_iam_revocation_heal_failures` | IAM reconciliation failure count |
| `minio_cluster_iam_revocation_heal_duration_millis` | Latest reconciliation duration |
| `minio_cluster_iam_revocation_heal_last_success_timestamp_seconds` | Unix time of the last successful reconciliation |

These are process metrics, not additive unique-record counts. The three `heal_*`
metrics advance only with site replication enabled and on the node holding the
leader lease. A shared-backend deployment without site replication performs no
such pass; zero healing metrics are expected. Tombstones have no TTL or automatic
compaction: budget for durable capacity and startup reads. Initial reconciliation
may backfill missing revisions and produce a write burst. Neither its interval
nor these metrics establish a convergence SLA.

A deleted access-key canary normally returns `403 InvalidAccessKeyId`; other
revocation mechanisms require their appropriate authorization failure, not a
universal error-code assertion. A 5xx, timeout or missing object is inconclusive.
Live-record export/import omits deletion history and cannot preserve the guarantee
of earlier revocations by itself. See the [IAM design](/blog/design/iam-revocations/)
for ordering and remaining limitations.

## Rollback and restore {#rollback}

Stop and isolate the affected sites first. Record all IAM changes and revocations
since the chosen recovery point. Restore the complete, compatible backend into
an isolated environment with its matching configuration, keys and binary; do
not start old software against a backend already changed by newer software.

An older backup can restore a credential revoked after that backup. Reapply the
revocation ledger or rekey affected identities before exposing the restored
system. If that ledger is incomplete, keep access isolated until the affected
scope is reconciled. Never remove tombstones, truncate revision history or
import only live records to make an old binary start.

After a restore, repeat the IAM/site-replication startup checks on every process
before issuing credentials. Verify temporary sessions separately from ordinary
users and service accounts. Reissue the required STS credentials after startup
and check them against every intended site; an old session failing on one site
does not prove that its parent identity is safely revoked everywhere.

### Reconcile a known recovery group {#reconcile}

One bounded recovery policy is to keep retired parent identities disabled,
remove their recorded service-account keys, detach revoked grants, and issue
replacement credentials under distinct identity names. Use the reviewed ledger
to select the actual users, keys and policies; all known sites must be online
inside the isolated recovery group, with stale or unknown peers excluded.
The isolated object-store and etcd rehearsals passed this policy with the
credential checks below. Apply the same checks to the actual recovery group
before approving access.

The following shows the operations against a protected recovery alias. Replace
the uppercase names with reviewed entries. User creation prompts for a secret;
service-account creation prints credentials, which belong in the approved
secret store rather than the rehearsal log.

```bash
mcli admin user disable recovery-a RETIRED_USER
mcli admin user svcacct rm recovery-a RETIRED_SERVICE_KEY
mcli admin policy detach recovery-a RETIRED_POLICY --user RETIRED_MAPPING_USER
mcli admin user add recovery-a RECOVERED_USER
mcli admin policy attach recovery-a CURRENT_POLICY --user RECOVERED_USER
mcli admin user svcacct add recovery-a RECOVERED_USER
```

Issue designated STS canaries through the application's usual authenticated
flow after startup completes, and verify each new session on every intended
process. If issuance or cross-site reads fail, keep the recovery group isolated,
retain the failure evidence and investigate. A fresh canary may be issued again
within the planned maintenance window; an elapsed timer alone cannot approve
access. Check the retired user, recorded service keys, revoked
mapping and both pre-restore and newly issued sessions of the retired parent.
They must all be denied on every process that will serve clients. The replacement
user, service account and freshly issued STS credentials must work. Repeat these
checks after a complete restore of the reconciled backup. Keep access isolated
if any check fails; this policy does not permit reconnecting a stale old peer or
re-enabling a retired parent on old software.

## Required rehearsal record {#rehearsal}

For **each** supported backend, use isolated old/new multi-process sites and
record exact binary identities and backup/restore commands. Exercise deletion
during peer disconnection, delayed old-event replay, deliberate same-name
recreation and credential reissue. Repeat after restart and full restore; also
test rollback to a recovery point predating a deletion. Old credentials must
remain denied after reconciliation while intended new credentials work.

Source regression evidence in [#192](https://github.com/pgsty/silo/pull/192)
supports the protocol implementation. The rehearsal adds deployment topology,
backup completeness, restart and operator recovery evidence. Link the resulting
redacted observations in [#200](https://github.com/pgsty/silo/issues/200); keep
release-artifact validation and a real production rollout separate.

## Validation scope {#validation}

On 2026-09-16, isolated rehearsals upgraded Server 20260903 (`9b11dc9469e6`)
to build `70c7ec4a9fbf`, whose runtime source matches baseline `40220bd836cb`
(only the changelog differs). Both the object-store and etcd 3.6.13 backends
passed. Each run used three sites with two Server processes and four drives per
site; the etcd run used one independent etcd process per site.

Existing, non-revoked user, service-account and STS credentials survived the
coordinated upgrade. Revocations made while one site was stopped converged after
it returned. Cold restart and full restore from a post-revocation backup kept
old credentials and detached grants denied, while explicitly recreated and
reissued credentials worked. Same-key service-account replacement also retained
the new secret and rejected the old secret. Denial checks used signed reads of
a known object with a successful root control, rather than treating any request
failure as proof of revocation.

Restoring a pre-upgrade backup with its old binary made a subsequently revoked
credential work again, confirming the rollback hazard above. A subsequent
rehearsal applied the [bounded reconciliation policy](#reconcile), then restored
the reconciled backup using the matching old binary:

| Backend | Observed result after reconciliation and full restore |
| --- | --- |
| etcd 3.6.13 | All six processes rejected the retired user, service key, revoked mapping and retired parent's sessions; replacement users, service accounts and newly issued STS credentials worked. The isolated client-access checks passed. |
| Object store | The completed continuation from the same pre-upgrade backup rejected retired users, service keys, revoked grants and the retired parent's STS. Replacement users, service accounts and fresh STS worked on all six processes after reconciliation and full restore. |

The object-store laboratory also observed temporary STS write and cross-site
authentication failures after startup checks passed. A control using only
Server 20260903 also encountered an STS write failure after cold restart; this
does not establish a regression in the new build. The exact cause was not
isolated. Fresh STS probes later passed without changing the binaries or
configuration, and the completed recovery run required those end-to-end checks
before proceeding. Startup messages and a fixed waiting period are insufficient;
preservation of pre-restore STS sessions is outside the accepted recovery scope.

The laboratory used one isolated Linux ARM64 container with a shared clock and
no external peers; the etcd instances were single-member backends. Production
storage snapshots, HA etcd, external identity providers/KMS and clock skew were
not tested. Those deployment-specific checks, the startup observations and
exact artifact identities remain tracked in [#200](https://github.com/pgsty/silo/issues/200).
