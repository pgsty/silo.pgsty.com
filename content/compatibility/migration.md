---
title: "Migrate from MinIO to Silo"
linkTitle: "Migration"
description: "A single-node migration case, consistent backups, container cutover, data verification, and recovery limits."
url: "/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

**Release scope, reviewed 2026-10-23:** Server 20261018 is the current published target. Review its [upgrade requirements](/blog/release/silo-20261018/#upgrade) and [compatibility delta](/compatibility/server/#october-2026), especially for former strict multipart users. The community case below exercised Server 20260916; it does not establish production acceptance of 20261018 or later builds.

Migrating from MinIO to Silo normally reuses existing object data and volumes without an object-by-object export and import. **Ordinary S3 applications usually need no code changes; administrators still need to check deployment, authorization and state compatibility.** Select the applicable [O01–O08 conditions](/compatibility/#conditional) in the [three-level overview](/compatibility/) before following this guide. RPM/DEB installs are covered in [Native Package Migration](/compatibility/binary/); check the [component matrix](/compatibility/versions/) for version-specific requirements.

## What changes {#scope}

In order of importance:

1. **Container image**: `minio/minio`, `quay.io/minio/minio`, and `pgsty/minio` are all replaced by `docker.io/pgsty/silo`.
2. **Package, systemd service, and server executable**: `minio` → `silo`.
3. **Upstream services**: the in-place updater and MinIO-operated callhome/SUBNET are disabled; upgrades go through packages, images, or your orchestrator.
4. **Default OS service account**: `silo` — fresh installations only; migrations keep running as the existing data owner.
5. **Default local configuration directory**: `~/.minio` → `~/.silo` (fresh processes only; see [server compatibility](/compatibility/server/#config-dir) for the certificate fallback order — an existing `~/.minio/certs` keeps being honored).
6. **Branding**: banners, Console appearance, log wording, and product links say Silo.

## What stays {#unchanged}

- **Object layouts, erasure formats and the `.minio.sys` directory remain, allowing data disks from compatible baselines to be reused.** This does not guarantee arbitrary downgrades; see [rollback scope](#rollback).
- Existing buckets, object versions, users, access keys, policies, lifecycle and encryption configuration remain usable. Authorization decisions, replication state and new metadata have exceptions in [O02](/compatibility/#o02) and [O07](/compatibility/#o07); the target [release notes](/blog/release/silo-20261018/) list the specifics.
- Common S3 APIs, SigV4, SDK, `mc`/`mcli` and presigned URL integration carry over. Validation, conditional requests and error behavior have changes in [O04](/compatibility/#o04).
- Endpoint hostname, API port `9000`, Console port, volume mounts.
- `MINIO_*` environment variables and existing server options.
- `/minio/*` routes, `x-minio-*` headers, `minio_*` metrics.
- Policy-namespace identifiers: `arn:minio:*` ARNs, `minio:s3` and other service namespaces in IAM policies, notifications and audit events keep their spelling. Do not rename these strings with the product; still check authorization semantics under [O02](/compatibility/#o02).

These conclusions apply to the [comparison baseline](/compatibility/#scope) and compatible erasure deployments. For older MinIO versions or historical filesystem/gateway deployments, establish the migration path for that version and deployment mode, then validate it in staging.

Reusing a volume does not mean its metadata is immutable. Startup, background work and later requests can update persistent state. Preserving names and object layouts is not evidence of zero metadata rewrites or of a safe reverse downgrade. SILO maintains best-effort upstream compatibility; the supported product combination is SILO, SILO Console, mcli and silo-pkg.

## Single-node field report {#single-node-case}

Paris Y. ([@yupoet](https://github.com/yupoet)) contributed [SILO #228](https://github.com/pgsty/silo/pull/228), reporting a production upgrade on **2026-09-26**. The [original submission](https://github.com/pgsty/silo/blob/fec1e0804a7493f68ba409345da8e90f0f4d5fbb/docs/upgrade/single-node-from-archived-minio.md) is historical evidence; the terminology and operational guidance below supersede its broader claims.

| Item | Contributor-reported scope |
| --- | --- |
| Source | MinIO `RELEASE.2025-10-15T17-29-55Z` |
| Target | SILO `RELEASE.2026-09-16T00-00-00Z` |
| Deployment | Docker Compose, one node, one drive, `server /data` |
| Identity and integrations | Root credentials only; no IAM sub-users, OIDC, notification targets or reverse proxy |
| Data | About 5,900 objects and 34,000 reported stored chunks; a volume with about 15 months of history |
| Observed result | The existing volume opened without reported errors; application checks covering multipart upload, reads through a parser service, listing and deletion passed |
| Upgrade history | The same volume was reportedly opened by 2025-09, 2025-10 and 2026-09 builds in sequence |

The volume age spans its history; it is not 15 months spent on the October 2025 release. The reported chunk count is not an audited count of S3 objects or versions. The submission provides no image digests, complete object/version read inventory, checksum comparison or reverse-downgrade result. Its observations support a successful forward upgrade for that environment, not a guarantee that every historical object was checked. The report does not include an independent maintainer reproduction.

### Modern single-drive storage and legacy FS {#single-node-storage}

For the stated versions, this is a **single-node/single-drive erasure deployment**, normally using `xl-single`; calling it legacy “FS mode” is incorrect. Check the actual backend in `.minio.sys/format.json` without editing it. The [`20260916` loader](https://github.com/pgsty/silo/blob/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c/cmd/format-erasure.go) accepts `xl` and `xl-single` and rejects the old `fs` backend. The command `server /data` alone does not establish the stored format.

Legacy FS and gateway modes were removed in MinIO 2022-10-29. Such installations require the separate [FS/gateway migration procedure](/operations/deployments/baremetal-migrate-fs-gateway/), not an image swap over the old volume. Single-drive storage also has no drive-level parity redundancy.

A single process does not encounter mixed-node binary checks or the removed private `ReadMultiple` peer call. Using only root credentials avoids the particular sub-user password-policy migration, but does not exempt S3 requests from validation, Object Lock checks or other release-specific changes. Do not generalize this case to shared IAM, replication, external identity providers or a distributed cluster.

## Docker migration {#docker}

For a compatible deployment, the maintained image repository is:

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

Choose an exact published `RELEASE.YYYY-MM-DDTHH-MM-SSZ` tag, preferably recording and deploying its verified digest. Do not use rolling `latest` for a controlled migration. Standard and `-distroless` images have different startup and probe environments. The older `pgsty/minio` repository is a historical distribution, not a redirect to `pgsty/silo`.

The sequence below is for one Compose-managed storage process. Keep application traffic paused until [verification](#verification) passes. Shared IAM, external state and replicated deployments also require their coordinated upgrade procedures.

### 1. Record the deployment and prepare recovery {#docker-preflight}

- Record the actual source image ID and available registry digest, architecture, Compose project/service identity, resolved volume or bind-mount paths, runtime UID/GID, ports and server arguments. Preserve the old image locally or in an accessible archive; a tag alone is not a recovery artifact.
- Save the original Compose configuration, environment/secret sources, certificate mounts and any required KMS/key recovery material securely. Inventory versioning, Object Lock, encryption, lifecycle, IAM, replication and external etcd before deciding which checks apply. A backup of the data directory alone does not contain external services or every key.
- Record representative existing object keys, version IDs, sizes and independent content checksums before the upgrade. Include old, large, multipart and encrypted objects when used. Object ETags are not universally content MD5 checksums.
- Rehearse the exact version combination on an isolated copy. Prevent the copy from writing to production IAM, replication or tiering endpoints. Test the recovery procedure as well as the forward upgrade.

The fragment below illustrates the standard image and a native probe. It is **not a replacement for the existing Compose file**: retain the real project identity, volume declarations, runtime user, secret sources and mounts. Changing a Compose project or volume name can silently select a new, empty volume.

```yaml
services:
  minio:                              # service name may stay "minio"
    image: docker.io/pgsty/silo:RELEASE.2026-10-18T00-00-00Z
    command: server /data --console-address ":9001"
    environment:                      # retain the existing credential sources
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

The sample image is the published planning target, not a claim that the contributor tested it. Replace it only with the specific tag or digest selected and validated for your deployment.

In the standard image, the entrypoint translates an initial `minio` argument to `silo`, so `command: minio server /data` remains usable. A hard-coded `entrypoint: /usr/bin/minio`, shell command or script invoking that path must be updated. The standard 20260916 and 20261018 images include curl and mcli with an `mc` alias; the distroless variant does not. Prefer the [native healthcheck](/compatibility/feature/healthcheck/) when writing a probe for either variant.

### 2. Stop writes and take a consistent backup {#docker-backup}

After preserving the original configuration and old image, prepare the target Compose settings and pull the target while the old process is still available:

```bash
docker compose pull minio
```

Here and below, `minio` is the example storage service name; use the existing service name in your deployment.

Stop application writers, scheduled jobs and other clients, then stop the storage process and prevent an orchestrator from restarting it during the backup:

```bash
docker compose stop minio
```

Confirm that no other process has the volume open for writes. **Now** take an offline volume backup or consistent snapshot. A tar archive of a live, changing data directory is not a consistent backup. Stopping only the application is insufficient because storage background work can still change state. An online snapshot requires a separately validated consistency procedure.

Include the entire volume, including `.minio.sys`, and preserve ownership, permissions and required filesystem attributes. Retain the matching deployment and key material from preflight; validate that the backup can be restored to a separate location. Never use `docker compose down -v` as an upgrade step: it removes named data volumes.

### 3. Start only the replacement storage process {#docker-start}

Confirm that the old process is stopped, the intended existing volume is selected, and the target can access data, certificates and keys under the configured UID/GID. Start the storage service without starting its dependencies:

```bash
docker compose up -d --no-deps minio
docker compose logs --tail=200 minio
docker compose exec -T minio silo healthcheck ready
```

Do not run old and new containers against the same volume simultaneously. Keep applications paused, perform [verification](#verification), then reopen traffic. A successful startup does not establish that every object has been read; startup and background processing can already have changed stored metadata.

### Distroless variant {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` ships the `silo` binary only: no shell, no `mc`, no `curl`, and no shell entrypoint to translate legacy commands. Its entrypoint is `/usr/bin/silo`; use `command: server /data --console-address ":9001"`, without a leading `minio` or `silo` word. Arbitrary UID execution still requires appropriate permissions on existing data, certificates and keys.

It includes a native `HEALTHCHECK`. An existing Compose healthcheck overrides that image default, so remove an inherited curl/`CMD-SHELL` probe or replace it with the exec-form native probe above. `depends_on: condition: service_healthy` uses that health status, but application data-path verification remains necessary before reopening traffic.

The standard and distroless variants of the same release use the same storage format; switching variants does not certify a downgrade between releases. Keep the selected certificate path accessible (the default is `/tmp/.silo/certs`), and set `MINIO_HEALTHCHECK_URL` if the listener address requires it. Use external debugging tools because there is no shell inside.

### Kubernetes {#kubernetes}

Kubelet probes are `httpGet` requests in the pod spec; Docker `HEALTHCHECK` is ignored, so both image variants are probed identically and existing probe configs keep working. For Helm releases, keep the release identity with `nameOverride`/`fullnameOverride` and compare `helm template` output before applying ([details](/compatibility/server/#helm)).

### Rollback {#rollback}

**Establish that state can be recovered before switching back.** Compatible object layouts do not guarantee that old software understands new bucket configuration, IAM revisions or deletion history, or that permissions and replication state remain equivalent after rollback.

Before upgrading, retain the original image digest, deployment configuration and a matching recovery point, and test the exact version combination in isolation. For the new IAM revocation mechanism, follow [IAM upgrade and recovery](/operations/replication/iam-upgrade/) to preserve complete IAM storage and key material; ordinary administration exports omit deletion history. Also check [bucket-configuration deletion state](/blog/design/bucket-metadata-convergence/#rollout) and [password permissions](/compatibility/password-permissions/#coordinated-upgrade-and-rollback).

Use the planned image or binary rollback only when the relevant upgrade instructions permit it and recovery validation passes. Versions with durable IAM revocation do not support rolling downgrade. Do not let old and new nodes access the same data simultaneously. Restoring an older snapshot also requires handling data and authorization changes made after that snapshot.

For the community case, a reverse downgrade was **not exercised**. Sequential forward openings by three builds do not prove that the oldest build understands state written by the newest. If validation fails, keep clients blocked, stop the new process and use the rehearsed recovery plan. Restoration must cover matching data, configuration and keys; reconcile later writes, deletes and credential revocations before exposing the restored endpoint. An image-only change is not a general recovery procedure.

## Behavior checks for a single-node migration {#single-node-behavior}

| Area | What to verify |
| --- | --- |
| TLS | 20260903 and 20260916 changed TLS handshake behavior; 20260916 removes explicit curve overrides in favor of Go defaults. Check inbound clients and applicable outbound identity, notification, replication and tiering connections, including TLS inspection devices. See [TLS compatibility](/blog/design/tls-parameter-pinning/). |
| Conditional deletion | Since 20260916, a nonempty `If-Match` on single-object `DeleteObject` is enforced; an ETag mismatch returns `412`. Do not extend that guarantee to batch deletion. See [conditional DELETE](/blog/design/conditional-delete/). |
| Multipart listing | In 20260916, omitting `max-uploads` selects a default of 1,000, and the strict paginator caps its page size at 1,000. This is not a universal response limit: the default legacy cache path ignores pagination and can return more entries. Optional strict mode belongs to that historical release; 20261018 removes it. Neither an empty list nor a successful abort proves every physical upload is gone. See [20260916 behavior](/blog/release/silo-20260916/#multipart) and the [20261018 requirements](/blog/release/silo-20261018/#upgrade). |
| Proxy trust | Unset `MINIO_API_TRUSTED_PROXIES` preserves historical trust of forwarded source-address headers on the S3 listener. For direct clients, consider `none`; behind a proxy, allow-list its actual IP/CIDR and ensure it overwrites client-supplied headers. Console and LDAP STS have their own trust rules. See [source-address trust](/compatibility/server/#trusted-proxies). |
| Identity and object state | A root-only case does not test sub-user password policies, service accounts, STS, OIDC, Object Lock or replication. Select the applicable checks from the [target release](/blog/release/silo-20261018/#upgrade), [password migration](/compatibility/password-permissions/) and [IAM recovery](/operations/replication/iam-upgrade/). |

## Upgrading from RELEASE.2026-08-06 {#since-20260806}

The release after `RELEASE.2026-08-06T00-00-00Z` tightens several behaviors that 20260806 accepted. Check these before upgrading:

1. **Explicit version deletes need `s3:DeleteObjectVersion`.** `DeleteObject` and `DeleteObjects` entries that carry a `versionId` are authorized as `s3:DeleteObjectVersion`, as on AWS. Grant it to principals that delete specific versions, and add `Deny s3:DeleteObjectVersion` next to any `Deny s3:DeleteObject` that is meant to block permanent deletes.
2. **Enable and disable are separate admin actions.** `admin:EnableUser` / `admin:DisableUser` and the group equivalents are checked against the requested status; a policy that grants only one of them loses the other operation.
3. **New and updated policies reject bare ARN prefixes** such as `arn:aws:s3:::`, and statements that combine `Resource` with `NotResource`. Stored policies keep loading; automation that re-applies such policies fails.
4. **Legacy database notification targets need a connection string.** An enabled pre-KV PostgreSQL or MySQL target without `connection_string` / `dsn_string` stops startup with a credential-free error; 20260806 silently dropped every notification target in that situation.
5. **Checksum requests are validated.** Unknown `x-amz-checksum-*` algorithms, `CRC64NVME` combined with `COMPOSITE`, and checksum-type assertions that contradict the upload are rejected with `400`. The default behavior of the AWS SDKs, `minio-go`, and `mcli` is unaffected.
6. **Per-bucket CORS is real.** A bucket with its own CORS configuration is served by that configuration only; `MINIO_API_CORS_ALLOW_ORIGIN` applies to buckets without one. In a site-replication group, configure bucket CORS only after every site runs the new release: older peers accept but ignore the configuration and keep reporting a CORS mismatch.
7. **Rollback loses new CORS configuration.** 20260806 ignores bucket CORS and drops it when rewriting bucket metadata. Export it before rollback and restore it after upgrading again; check other state separately under [rollback scope](#rollback).

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

Verify the replacement while application traffic remains paused:

1. Confirm the actual running version/image, original volume identity, expected buckets and startup logs. A new empty volume can pass a health probe.
2. Run `silo healthcheck ready` inside the container, or probe the correct published HTTP endpoint from the host. For the default local HTTP listener, a complete command is `curl --fail --silent --show-error http://127.0.0.1:9000/minio/health/ready`. For TLS, use the correct hostname and trusted CA. Probe success is a preliminary signal, not proof of IAM readiness or data integrity.
3. Read the pre-recorded historical objects through the existing application/SDK and compare bytes, sizes and independent checksums. Check versions, tags, encryption, retention and legal hold when used. Full-volume assurance requires a defined inventory and reads of every required object/version; listing counts and a few canaries cannot establish it.
4. Use an approved test bucket/key to exercise upload, read-back and deletion with the real client. Include multipart completion and the application's listing behavior. Respect versioning and retention when cleaning up the test; do not delete production objects as a smoke test.
5. Verify relevant identities and integrations, including expected denied requests. Shared IAM or replication deployments must check every participating endpoint under the [IAM upgrade procedure](/operations/replication/iam-upgrade/).
6. Restart the storage service once while traffic is still paused, then repeat readiness and signed historical-object/canary requests. Reopen applications only after acceptance, and record the versions, coverage, results and any unresolved failures.

If historical metadata or objects are rejected, preserve the error and affected identity, and investigate on a copy. Installing SILO does not repair every historical inconsistency. Report “no rejection observed in these checks” unless a complete audit supports a stronger statement. Avoid introducing optional new state during the migration window; recovery must still satisfy the [rollback requirements](#rollback).
