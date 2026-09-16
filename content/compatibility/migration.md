---
title: "Migrate from MinIO to Silo"
linkTitle: "Migration"
description: "What changes, what stays, and how to switch a container deployment. Package installations are covered in Native Package Migration."
url: "/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

Migrating from MinIO to Silo normally reuses existing object data and volumes without an object-by-object export and import. Review deployment, authorization and persistent-state changes; container migrations must account for entrypoints, runtime users, permissions and probes. For RPM/DEB installations, see [Native Package Migration](/compatibility/binary/); check the [component matrix](/compatibility/versions/) for version-specific requirements.

## What changes {#scope}

In order of importance:

1. **Container image**: `minio/minio`, `quay.io/minio/minio`, and `pgsty/minio` are all replaced by `docker.io/pgsty/silo`.
2. **Package, systemd service, and server executable**: `minio` → `silo`.
3. **Upstream services**: the in-place updater and MinIO-operated callhome/SUBNET are disabled; upgrades go through packages, images, or your orchestrator.
4. **Default OS service account**: `silo` — fresh installations only; migrations keep running as the existing data owner.
5. **Default local configuration directory**: `~/.minio` → `~/.silo` (fresh processes only; see [server compatibility](/compatibility/server/#config-dir) for the certificate fallback order — an existing `~/.minio/certs` keeps being honored).
6. **Branding**: banners, Console appearance, log wording, and product links say Silo.

## What stays {#unchanged}

- **Object layouts, erasure formats and the `.minio.sys` directory remain, allowing disks from compatible baselines to be reused.** This does not guarantee arbitrary downgrades; see [rollback scope](#rollback).
- Existing buckets, object versions, identities and configuration remain usable; check authorization, replication-state and new-metadata changes in the target [release notes](/blog/release/silo-20260916/).
- Common S3 APIs, SigV4, SDK, `mc`/`mcli` and presigned-URL interfaces carry over; validation, conditional operations and error behavior can change with repairs.
- Endpoint hostname, API port `9000`, Console port, volume mounts.
- `MINIO_*` environment variables and existing server options.
- `/minio/*` routes, `x-minio-*` headers, `minio_*` metrics.
- Policy-namespace identifiers: `arn:minio:*` ARNs, `minio:s3` and the other service namespaces in IAM policies, notifications, and audit events keep their exact spelling. There is **no `SILO_*` alias namespace** — scripts and policies addressing the identifiers above need no change.

These conclusions apply to compatible erasure deployments. Establish a version-specific migration path for older builds and historical filesystem/gateway modes, then validate it in isolation.

## Docker migration {#docker}

Whichever image you run today, replace it with:

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

Tags: immutable `RELEASE.YYYY-MM-DDTHH-MM-SSZ` (pin these), rolling `latest`, and the `-distroless` variants below. The old `pgsty/minio` repository stays published, frozen at its final tag.

The Compose example retains the original ports, volumes and `MINIO_*` configuration; replace the image after the checks above:

```yaml
services:
  minio:                              # service name may stay "minio"
    image: docker.io/pgsty/silo:<RELEASE-tag>
    command: server /data --console-address ":9001"
    environment:                      # MINIO_* unchanged
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio-data:/data              # same volume, same data
volumes:
  minio-data:
```

```bash
docker compose pull minio && docker compose up -d minio
```

The entrypoint translates the legacy first argument, so an inherited `command: minio server /data` keeps working. A hard-coded `entrypoint: /usr/bin/minio` must change to `/usr/bin/silo`. Existing `mc ready local` healthchecks keep working; the native replacement is `test: ["CMD", "silo", "healthcheck", "ready"]` ([reference](/compatibility/feature/healthcheck/)). Do not run `docker compose down -v` — `-v` deletes the data volume.

### Distroless variant {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` ships the `silo` binary only: no shell, no `mc`, no `curl`. It has a built-in `HEALTHCHECK` (the native probe) and works under any `--user`:

```bash
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=change-me-long-password \
  -v silo-data:/data \
  docker.io/pgsty/silo:<RELEASE-tag>-distroless \
  server /data --console-address ":9001"
```

The same deployment as a Compose file:

```yaml
services:
  silo:
    image: docker.io/pgsty/silo:<RELEASE-tag>-distroless
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: change-me-long-password
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - silo-data:/data
volumes:
  silo-data:
```

`depends_on: condition: service_healthy` works against it with no `healthcheck:` block. The volume format is the same as the classic image and MinIO — the variants are interchangeable over the same data. TLS certificates mount at `/tmp/.silo/certs`. If command-line flags move the listen address, point the built-in probe with `MINIO_HEALTHCHECK_URL`. There is no shell inside; debug with `docker debug` / `kubectl debug`.

### Kubernetes {#kubernetes}

Kubelet probes are `httpGet` requests in the pod spec; Docker `HEALTHCHECK` is ignored, so both image variants are probed identically and existing probe configs keep working. For Helm releases, keep the release identity with `nameOverride`/`fullnameOverride` and compare `helm template` output before applying ([details](/compatibility/server/#helm)).

### Rollback {#rollback}

Rollback depends on the source version, target version and persistent state already written. Retain the original image digest, configuration and a consistent backup, and follow the target release's recovery procedure with the relevant processes stopped. Readable object data does not establish safe IAM, bucket-configuration or replication downgrade. Versions with durable IAM revocation do not support rolling downgrade; follow [IAM upgrade and recovery](/operations/replication/iam-upgrade/).

## Upgrading from RELEASE.2026-08-06 {#since-20260806}

The release after `RELEASE.2026-08-06T00-00-00Z` tightens several behaviors that 20260806 accepted. Check these before upgrading:

1. **Explicit version deletes need `s3:DeleteObjectVersion`.** `DeleteObject` and `DeleteObjects` entries that carry a `versionId` are authorized as `s3:DeleteObjectVersion`, as on AWS. Grant it to principals that delete specific versions, and add `Deny s3:DeleteObjectVersion` next to any `Deny s3:DeleteObject` that is meant to block permanent deletes.
2. **Enable and disable are separate admin actions.** `admin:EnableUser` / `admin:DisableUser` and the group equivalents are checked against the requested status; a policy that grants only one of them loses the other operation.
3. **New and updated policies reject bare ARN prefixes** such as `arn:aws:s3:::`, and statements that combine `Resource` with `NotResource`. Stored policies keep loading; automation that re-applies such policies fails.
4. **Legacy database notification targets need a connection string.** An enabled pre-KV PostgreSQL or MySQL target without `connection_string` / `dsn_string` stops startup with a credential-free error; 20260806 silently dropped every notification target in that situation.
5. **Checksum requests are validated.** Unknown `x-amz-checksum-*` algorithms, `CRC64NVME` combined with `COMPOSITE`, and checksum-type assertions that contradict the upload are rejected with `400`. The default behavior of the AWS SDKs, `minio-go`, and `mcli` is unaffected.
6. **Per-bucket CORS is real.** A bucket with its own CORS configuration is served by that configuration only; `MINIO_API_CORS_ALLOW_ORIGIN` applies to buckets without one. In a site-replication group, configure bucket CORS only after every site runs the new release: older peers accept but ignore the configuration and keep reporting a CORS mismatch.
7. **Rollback keeps the data readable.** 20260806 ignores bucket CORS configuration and drops it when it rewrites that bucket's metadata; recreate the configuration after upgrading again.

### Console regressions in the September 3 release {#console-0903}

`RELEASE.2026-09-03T13-18-01Z` stopped recognizing forwarded client addresses from unconfigured local proxies and discarded the four `CONSOLE_WS_MAX_*` connection settings. This can change IP Allow/Deny decisions and prevent operators from raising the eight-connection anonymous per-address limit.

Builds containing the fixes restore loopback TCP-peer trust for embedded Console unless `MINIO_API_TRUSTED_PROXIES=none`/`off`, and preserve all four limits from the environment or `MINIO_CONFIG_ENV_FILE`. Remote proxies still need an explicit IP/CIDR list. Standalone defaults, forwarded-chain trust rules and connection budgets remain unchanged; invalid configuration becomes a startup error. See [Console settings](/reference/minio-server/settings/console/#embedded-compatibility) for the policy table and configuration constraints. Track availability in [#147](https://github.com/pgsty/silo/issues/147) and [#148](https://github.com/pgsty/silo/issues/148); the 0903 image does not include these fixes.

On 0903, explicitly listing the local proxy peer in `MINIO_API_TRUSTED_PROXIES` restores client attribution, but also switches the S3 listener on port 9000 to listed mode; include its other required proxies too. Custom WebSocket limits require a fixed Server build or standalone Console.

## One cluster, one binary {#one-binary}

Distributed nodes verify each other's binary at bootstrap. A node started among peers running a different binary does not fail — it waits indefinitely in `activating`, logging:

```text
Expected Silo binary checksum: ..., seen: ...
Waiting for at least 1 remote servers with valid configuration to be online
```

This applies to any pair of different binaries: MinIO next to Silo, and one Silo version next to another. So do not migrate — or later upgrade — a cluster node by node. Switch all nodes in one pass: stop the old binary everywhere, start the new one everywhere (in Compose: change the image for all nodes in one edit, `docker compose up -d` once). Single-node deployments are unaffected. The same applies to rollback. Rolling restarts of the same binary work normally; gate them with `silo healthcheck --maintenance cluster` (exit `0` = safe to stop this node).

## Verification {#verification}

Before touching anything, record the artifacts you are leaving behind: the running image digest (or package version and binary checksum), the unit status and enabled state, and the UID/GID that owns the data directory. Rollback is only as precise as that record.

```bash
silo healthcheck ready                   # this node serves; exit 0/1
silo healthcheck cluster                 # cluster-wide write quorum
mc admin info <existing-alias>           # all nodes online, new version, old alias
```

Then download a known object and compare its checksum, exercise one application through its existing SDK, restart the service once, and re-check. One more rollback precondition: do not enable features in the migration window that the old version cannot understand — rolling back means rolling back to what the old binary can parse.
