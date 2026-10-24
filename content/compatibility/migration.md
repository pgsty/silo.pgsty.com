---
title: "Migrate from MinIO to Silo"
linkTitle: "Migration"
description: "A single-node migration case, consistent backups, container cutover, data verification, and recovery limits."
url: "/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

Migrating from MinIO to Silo reuses existing object data volumes in place without an object-by-object export and import. **Ordinary S3 applications require no code changes; administrators only need to verify deployment settings, authorization rules, and state compatibility.**

The current published target is **Server 20261018** (review its [upgrade requirements](/blog/release/silo-20261018/#upgrade) and [October compatibility delta](/compatibility/server/#october-2026), especially if your deployment used `strict` multipart listing). Check the applicable [O01–O08 conditions](/compatibility/#conditional) in the [three-level compatibility overview](/compatibility/) before following this guide. RPM/DEB installations are covered in [Native Package Migration](/compatibility/binary/), and component pairings are listed in the [version matrix](/compatibility/versions/).

## What changes {#scope}

In order of operational impact:

1. **Container image**: `minio/minio`, `quay.io/minio/minio`, and `pgsty/minio` are replaced by `docker.io/pgsty/silo`.
2. **Package, systemd service, and server executable**: `minio` → `silo`.
3. **Upstream services**: the in-place self-updater (`mc admin update`) and MinIO-operated callhome/SUBNET are disabled; upgrades are managed through packages, container images, or your orchestrator.
4. **Default OS service account**: `silo` (fresh installations only; migrations continue running under the existing data owner).
5. **Default local configuration directory**: `~/.minio` → `~/.silo` (fresh processes only; see [server compatibility](/compatibility/server/#config-dir) for the certificate fallback order — an existing `~/.minio/certs` directory continues to be honored).
6. **Branding**: startup banners, Console UI, log messages, and documentation links identify the product as Silo.

## What stays {#unchanged}

- **Object layouts, erasure formats, and the `.minio.sys` metadata directory remain unchanged**, allowing data drives from compatible baselines to be reused directly (see [rollback scope](#rollback) for downgrade constraints).
- **Existing buckets, object versions, users, access keys, IAM policies, lifecycle rules, and encryption configurations remain active.** Specific authorization, replication, and metadata tightening rules are documented in [O02](/compatibility/#o02), [O07](/compatibility/#o07), and the target [release notes](/blog/release/silo-20261018/).
- **Common S3 APIs, SigV4 signing, SDKs, `mc`/`mcli`, and presigned URLs work as before**; checksum validation, conditional requests, and error-code refinements are listed under [O04](/compatibility/#o04).
- **Network and mounts**: endpoint hostnames, API port `9000`, Console ports, and volume mount paths remain unchanged.
- **Runtime configuration**: `MINIO_*` environment variables and existing server CLI flags remain unchanged.
- **Management and metrics paths**: `/minio/*` HTTP routes, `x-minio-*` headers, and `minio_*` Prometheus metric names remain unchanged.
- **Policy-namespace identifiers**: `arn:minio:*` ARNs, `minio:s3`, and other service namespaces in IAM policies, event notifications, and audit logs keep their exact spelling (verify authorization semantics under [O02](/compatibility/#o02)).

These guarantees apply to the [comparison baseline](/compatibility/#scope) and compatible erasure deployments. Note that while data volumes are reused in place, server startup, background tasks, and subsequent writes can update persistent metadata in `.minio.sys` (such as IAM revocation records or bucket configurations); always take an offline consistent backup before switching binaries.

## Single-node field report {#single-node-case}

Community contributor Paris Y. ([@yupoet](https://github.com/yupoet)) documented a single-node production upgrade on **2026-09-26** in [SILO #228](https://github.com/pgsty/silo/pull/228) ([archived report](https://github.com/pgsty/silo/blob/fec1e0804a7493f68ba409345da8e90f0f4d5fbb/docs/upgrade/single-node-from-archived-minio.md)):

| Item | Reported scope |
| --- | --- |
| Source version | MinIO `RELEASE.2025-10-15T17-29-55Z` |
| Target version | SILO `RELEASE.2026-09-16T00-00-00Z` |
| Deployment topology | Docker Compose, single node, single drive, `server /data` |
| Identity and integrations | Root credentials only; no IAM sub-users, OIDC, notification targets, or reverse proxy |
| Data volume | ~5,900 objects (~34,000 underlying storage chunks); volume opened sequentially across 2025-09, 2025-10, and 2026-09 builds over ~15 months |
| Observed result | Existing volume mounted cleanly without errors; application checks covering multipart uploads, parser-service reads, listing, and deletion passed |

### Modern single-drive storage vs. legacy FS mode {#single-node-storage}

The deployment above uses **single-node, single-drive erasure storage (`xl-single`)**, not the removed legacy `fs` mode. Because the startup command `server /data` looks identical for both, inspect `.minio.sys/format.json` (read-only; do not edit it) before migrating. The [erasure loader](https://github.com/pgsty/silo/blob/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c/cmd/format-erasure.go) accepts `xl` and `xl-single` and rejects the legacy `fs` backend.

Legacy `fs` and `gateway` modes were removed in MinIO `2022-10-29`. Deployments still running those modes must follow the [FS/gateway export migration procedure](/operations/deployments/baremetal-migrate-fs-gateway/) rather than swapping the image in place.

Because a single-process root-only deployment does not exercise peer binary checksums, the removed `ReadMultiple` internode RPC, sub-user password-policy migration, replication, or external identity providers, multi-node or IAM-heavy deployments should also review the sections below.

## Docker migration procedure {#docker}

The maintained container image repository is:

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

Pin an exact published `RELEASE.YYYY-MM-DDTHH-MM-SSZ` tag (and preferably its verified digest) rather than rolling `latest`. The historical `pgsty/minio` repository does not redirect to `pgsty/silo`.

The procedure below covers a single Compose-managed storage process. Keep application writes paused until [verification](#verification) finishes; shared IAM, external etcd, and replicated deployments must also follow their coordinated upgrade procedures.

### 1. Record the deployment and prepare recovery {#docker-preflight}

- **Record runtime identity**: save the current source image ID and registry digest, architecture, Compose project and service names, resolved volume or bind-mount paths, runtime UID/GID, port mappings, and server flags. Keep a local or archived copy of the old image.
- **Back up configuration and keys**: save the original Compose file, environment/secret sources, TLS certificate mounts, and any required KMS/encryption recovery material. Inventory versioning, Object Lock, server-side encryption, lifecycle rules, IAM, replication, and external etcd to determine which post-upgrade checks apply.
- **Record representative baseline objects**: before upgrading, record keys, version IDs, byte sizes, and independent content checksums for representative existing objects (including old, large, multipart, and encrypted objects; note that multipart and encrypted ETags are not plain MD5 hashes).
- **Rehearse in isolation**: test the exact upgrade and recovery steps on an isolated copy with outbound access to production IAM, replication, and tiering endpoints blocked.

The snippet below shows the standard image and native health probe. **Do not blindly overwrite your existing Compose file with this snippet**: preserve your actual Compose project name, volume declarations, runtime user, credential sources, and mounts (changing a Compose project or volume name can silently mount a brand-new empty volume).

```yaml
services:
  minio:                              # service name may stay "minio"
    image: docker.io/pgsty/silo:RELEASE.2026-10-18T00-00-00Z
    command: server /data --console-address ":9001"
    environment:                      # retain existing credential sources
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio-data:/data              # retain the actual existing volume
    healthcheck:
      test: ["CMD", "silo", "healthcheck", "ready"]
      interval: 30s
      timeout: 10s
      start_period: 2m
      retries: 3
volumes:
  minio-data:
```

In the standard image, the entrypoint script translates a leading `minio` argument to `silo`, so `command: minio server /data` continues to work; hard-coded `entrypoint: /usr/bin/minio` overrides or scripts invoking that path must be updated. Standard images include `curl` and `mcli` (with an `mc` alias), whereas `-distroless` images do not. Prefer the [native healthcheck](/compatibility/feature/healthcheck/) across both variants.

### 2. Stop writes and take a consistent backup {#docker-backup}

Pre-pull the target image while the old container is still running to minimize downtime:

```bash
docker compose pull minio
```

(Replace `minio` here and below with your actual Compose storage service name.)

Stop application writers, scheduled jobs, and other clients, then stop the storage container and ensure no orchestrator restarts it during backup:

```bash
docker compose stop minio
```

Confirm that no process has the volume open for writes, **then** take an offline volume backup or storage snapshot. Stopping only application clients is insufficient because background scanner, lifecycle, and healing workers inside the server continue mutating `.minio.sys` and object metadata; archiving a live directory produces an inconsistent backup.

Include the entire volume (including `.minio.sys`), preserve ownership, permissions, and filesystem attributes, and verify that the backup restores cleanly to a separate path. **Never run `docker compose down -v` during an upgrade**, as `-v` deletes named data volumes.

### 3. Start the replacement storage service {#docker-start}

Confirm that the old container is stopped, the existing volume is attached, and the configured UID/GID can access data, certificates, and keys. Start the storage container without starting dependent application containers:

```bash
docker compose up -d --no-deps minio
docker compose logs --tail=200 minio
docker compose exec -T minio silo healthcheck ready
```

Never run old and new containers against the same volume simultaneously. Complete [verification](#verification) before reopening application traffic.

### Distroless variant {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` ships only `/usr/bin/silo` — no shell, `mc`, `curl`, or wrapper entrypoint script. Its `ENTRYPOINT` is `/usr/bin/silo`, so pass server arguments directly (`command: server /data --console-address ":9001"`) without a leading `minio` or `silo` token.

The image includes a built-in native `HEALTHCHECK`. Because an existing Compose `healthcheck` block overrides the image default, remove any inherited `curl` or `CMD-SHELL` probe or replace it with the exec-form `["CMD", "silo", "healthcheck", "ready"]` probe shown above. The default certificate directory is `/tmp/.silo/certs`; set `MINIO_HEALTHCHECK_URL` if the listener requires a custom probe URL. Standard and distroless variants of the same release share the exact same on-disk format and can be swapped freely.

### Kubernetes {#kubernetes}

Kubernetes kubelet executes `httpGet` probes defined in the Pod spec and ignores the Docker `HEALTHCHECK` instruction, so standard and distroless images behave identically under existing Kubernetes probe configurations. For Helm deployments, preserve the release identity and PVC bindings with `nameOverride` / `fullnameOverride`, and diff `helm template` output before applying ([details](/compatibility/server/#helm)).

### Rollback {#rollback}

On-disk object layout compatibility does not mean an older binary understands new metadata written after an upgrade. **Before rolling back an image or binary, verify whether persistent state must be restored as well:**

- **Durable IAM revocation history**: releases with persistent IAM revocations do not support rolling downgrades. Follow [IAM upgrade and recovery](/operations/replication/iam-upgrade/) before upgrading to back up complete IAM storage and key material (standard `mc admin cluster iam export` archives omit deletion/revocation tombstones).
- **Bucket metadata convergence and password permissions**: check [bucket-configuration deletion state](/blog/design/bucket-metadata-convergence/#rollout) and [password permission rollback rules](/compatibility/password-permissions/#coordinated-upgrade-and-rollback).
- **Executing recovery**: if post-upgrade verification fails, keep clients blocked, stop the new server, and restore the pre-upgrade volume backup, configuration, and pinned image digest. Reconcile any writes, deletes, or credential revocations that occurred after the backup before reopening the endpoint.

## Behavior checks for a single-node migration {#single-node-behavior}

| Area | What to verify |
| --- | --- |
| TLS handshakes and CA trust | 20260903 and 20260916 updated TLS behavior; 20260916 removes explicit curve overrides in favor of Go defaults (enabling hybrid post-quantum key exchange) and changes macOS custom CA loading under Go 1.27. Check inbound clients and outbound OIDC, notification, replication, and tiering connections, including TLS-inspecting middleboxes. See [Go 1.27 TLS and OIDC discovery](/blog/design/go127-tls-oidc-discovery/). |
| Conditional deletion | Since 20260916, single-object `DeleteObject` enforces nonempty `If-Match` headers and returns `412 PreconditionFailed` on ETag mismatch (batch `DeleteObjects` is unchanged). See [conditional DELETE](/blog/design/conditional-delete/). |
| Multipart listing | 20260916 offered an optional `MINIO_API_MULTIPART_LISTING=strict` disk-scan mode; 20261018 removes it and restores legacy in-memory cache behavior (omitting `max-uploads` defaults to 1,000, though the legacy cache path does not enforce strict pagination). See [20260916 behavior](/blog/release/silo-20260916/#multipart) and [20261018 upgrade requirements](/blog/release/silo-20261018/#upgrade). |
| Reverse-proxy source-address trust | When `MINIO_API_TRUSTED_PROXIES` is unset, the S3 listener preserves historical trust of forwarded client-IP headers. Set `none` for direct client connections, or explicitly list proxy IPs/CIDRs and ensure proxies overwrite client-supplied headers. Console and LDAP STS follow their own trust rules. See [source-address trust](/compatibility/server/#trusted-proxies). |
| Identity and object state | If your deployment uses IAM sub-user password policies, service accounts, STS, OIDC, Object Lock, or replication, review the [target release notes](/blog/release/silo-20261018/#upgrade), [password permission migration](/compatibility/password-permissions/), and [IAM recovery](/operations/replication/iam-upgrade/). |

## Upgrading from RELEASE.2026-08-06 {#since-20260806}

Releases after `RELEASE.2026-08-06T00-00-00Z` tighten several behaviors that 20260806 accepted. Review this checklist before upgrading:

1. **Explicit version deletes require `s3:DeleteObjectVersion`.** `DeleteObject` and `DeleteObjects` entries carrying a `versionId` are authorized against `s3:DeleteObjectVersion`, matching AWS S3. Grant this action to principals that delete specific versions, and add `Deny s3:DeleteObjectVersion` alongside any `Deny s3:DeleteObject` rule intended to block permanent deletion.
2. **Enable and disable are separate admin actions.** `admin:EnableUser` / `admin:DisableUser` (and their group equivalents) are checked against the requested target state; policies granting only one action can no longer perform the opposite operation.
3. **New and updated policies reject bare ARN prefixes** (such as `arn:aws:s3:::`) and statements combining `Resource` with `NotResource`. Existing stored policies continue loading, but automation that re-applies malformed policies will fail.
4. **Legacy database notification targets require a connection string.** An enabled pre-KV PostgreSQL or MySQL target missing `connection_string` / `dsn_string` halts startup with a credential-redacted error, whereas 20260806 silently dropped all notification targets in that state.
5. **Checksum headers are strictly validated.** Unknown `x-amz-checksum-*` algorithms, `CRC64NVME` combined with `COMPOSITE`, and checksum-type assertions contradicting the upload return `400 BadRequest`. Default AWS SDK, `minio-go`, and `mcli` requests are unaffected.
6. **Per-bucket CORS configurations take precedence.** A bucket with its own CORS rule is served exclusively by that rule; `MINIO_API_CORS_ALLOW_ORIGIN` applies only to buckets without one. In site-replication groups, configure bucket CORS only after all sites run the new release so older peers do not ignore the rule and report CORS drift.
7. **Rollback to 20260806 drops per-bucket CORS.** Because 20260806 ignores bucket CORS and strips it when rewriting bucket metadata, export bucket CORS rules before rolling back and restore them after re-upgrading.

### Console regressions in the September 3 release {#console-0903}

`RELEASE.2026-09-03T13-18-01Z` stopped recognizing forwarded client addresses from unconfigured local proxies and ignored the four `CONSOLE_WS_MAX_*` WebSocket connection limits, affecting client-IP Allow/Deny rules and locking anonymous connections at the default per-IP limit of 8.

`20260916` and later releases ([#147](https://github.com/pgsty/silo/issues/147), [#148](https://github.com/pgsty/silo/issues/148)) restore loopback TCP-peer trust for the embedded Console unless `MINIO_API_TRUSTED_PROXIES=none`/`off`, and honor all four `CONSOLE_WS_MAX_*` limits from the environment or `MINIO_CONFIG_ENV_FILE`. Remote proxies still require an explicit IP/CIDR allowlist. See [Console settings](/reference/minio-server/settings/console/#embedded-compatibility) for full details.

On `20260903`, adding the local proxy peer to `MINIO_API_TRUSTED_PROXIES` restores client-IP attribution, but also switches the port 9000 S3 listener into explicit allowlist mode (requiring all S3 proxies to be listed as well).

## One cluster, one binary {#one-binary}

Distributed nodes verify each other's binary checksum during bootstrap. A node started alongside peers running a different binary stays in `activating` indefinitely and logs:

```text
Expected Silo binary checksum: ..., seen: ...
Waiting for at least 1 remote servers with valid configuration to be online
```

This check applies between any two distinct binaries — whether MinIO next to Silo, or two different Silo releases. **Do not migrate or upgrade a distributed cluster node by node.** Switch all nodes in a single pass: stop the old binary on every node, then start the new binary on every node (in Compose, update the image across all nodes and run `docker compose up -d` once). The same rule applies to rollback.

Single-node deployments are unaffected. Routine rolling restarts of the *same* binary work normally; gate each node restart with `silo healthcheck --maintenance cluster` (exit code `0` confirms the node is safe to stop).

## Verification {#verification}

Verify the upgraded service while application traffic is still paused:

1. **Confirm instance and volume identity**: check the running version/image digest, attached volume identity, expected bucket list, and startup logs to ensure the container did not mount a fresh empty volume.
2. **Run readiness probes**: execute `silo healthcheck ready` inside the container, or probe the HTTP endpoint from the host (`curl --fail --silent --show-error http://127.0.0.1:9000/minio/health/ready` for a default local HTTP listener; supply the proper hostname and CA bundle for TLS).
3. **Verify baseline historical objects**: read back the pre-recorded historical objects through your application or SDK and compare byte contents, sizes, and independent checksums. Verify object versions, tags, encryption, retention, and legal holds where used.
4. **Exercise write and listing paths**: using a dedicated test bucket or key prefix, test single-part uploads, multipart completion, listing, read-back, and deletion with your real client (do not delete production objects as a smoke test, and respect bucket versioning/retention when cleaning up test keys).
5. **Verify identities and integrations**: test sub-users, service accounts, STS/OIDC flows, and expected `AccessDenied` responses. For shared IAM or replicated deployments, verify every participating endpoint following the [IAM upgrade procedure](/operations/replication/iam-upgrade/).
6. **Confirm restart persistence**: restart the storage service once while traffic remains paused, re-verify readiness and signed historical-object reads, and then reopen application traffic.

If any historical metadata or object read fails verification, preserve the error logs and object identifiers for investigation on an isolated copy, and avoid introducing optional new state during the migration window so [rollback](#rollback) remains straightforward.
