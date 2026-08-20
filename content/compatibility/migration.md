---
title: "Migrate from MinIO to Silo"
linkTitle: "Migration"
description: "What changes, what stays, and how to switch a container deployment. Package installations are covered in Native Package Migration."
url: "/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

Migrating from MinIO to Silo is an in-place binary replacement, not a data migration. Nothing is exported or re-imported. In a container deployment the only required change is the image name. For RPM/DEB installations, see [Native Package Migration](/compatibility/binary/).

## What changes {#scope}

In order of importance:

1. **Container image**: `minio/minio`, `quay.io/minio/minio`, and `pgsty/minio` are all replaced by `docker.io/pgsty/silo`.
2. **Package, systemd service, and server executable**: `minio` → `silo`.
3. **Upstream services**: the in-place updater and MinIO-operated callhome/SUBNET are disabled; upgrades go through packages, images, or your orchestrator.
4. **Default OS service account**: `silo` — fresh installations only; migrations keep running as the existing data owner.
5. **Branding**: banners, Console appearance, log wording, and product links say Silo.

## What stays {#unchanged}

- **Object data and the `.minio.sys` metadata directory — the on-disk format is unchanged and remains interoperable with MinIO in both directions.**
- Buckets, versions, users, access keys, policies, lifecycle rules, replication state, encryption metadata.
- S3 API, SigV4 signing, SDKs, `mc`/`mcli`, presigned URL behavior.
- Endpoint hostname, API port `9000`, Console port, volume mounts.
- `MINIO_*` environment variables and existing server options.
- `/minio/*` routes, `x-minio-*` headers, `minio_*` metrics.

There is no data-conversion step. If your MinIO build is years old, validate the version distance itself in staging; it is a large software upgrade, not a format change.

## Docker migration {#docker}

Whichever image you run today, replace it with:

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

Tags: immutable `RELEASE.YYYY-MM-DDTHH-MM-SSZ` (pin these), rolling `latest`, and the `-distroless` variants below. The old `pgsty/minio` repository stays published, frozen at its final tag.

In Compose, change only the image line:

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

The disk format is unchanged and works with both servers: set `image:` back to the recorded MinIO tag and `docker compose up -d`. The same volume stays attached, and data written by Silo remains readable by MinIO.

## One cluster, one binary {#one-binary}

Distributed nodes verify each other's binary at bootstrap. A node started among peers running a different binary does not fail — it waits indefinitely in `activating`, logging:

```text
Expected Silo binary checksum: ..., seen: ...
Waiting for at least 1 remote servers with valid configuration to be online
```

This applies to any pair of different binaries: MinIO next to Silo, and one Silo version next to another. So do not migrate — or later upgrade — a cluster node by node. Switch all nodes in one pass: stop the old binary everywhere, start the new one everywhere (in Compose: change the image for all nodes in one edit, `docker compose up -d` once). Single-node deployments are unaffected. The same applies to rollback. Rolling restarts of the same binary work normally; gate them with `silo healthcheck --maintenance cluster` (exit `0` = safe to stop this node).

## Verification {#verification}

```bash
silo healthcheck ready                   # this node serves; exit 0/1
silo healthcheck cluster                 # cluster-wide write quorum
mc admin info <existing-alias>           # all nodes online, new version, old alias
```

Then download a known object and compare its checksum, exercise one application through its existing SDK, restart the service once, and re-check.
