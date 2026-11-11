---
title: "SILO: S3-Compatible Object Storage by Pigsty"
description: "S3-compatible object storage, forked from MinIO and maintained by the Pigsty community: versioned releases, signed packages, the full web console, and security fixes with public advisories."
url: "/"
weight: 1
type: home
cascade:
  type: docs
upstream_link: https://github.com/minio/docs
upstream_modified: true
body_class: landing-page
---

This site documents **[SILO 20261109](/blog/release/silo-20261109/)** (with embedded [Console 2.7.0](/blog/release/console-2.7.0/), Go 1.27.3), standalone **[Console 2.7.1](/blog/release/console-2.7.1/)**, **[mcli 20261112](/blog/release/mcli-20261112/)**, **[silo-pkg 3.16.1](/blog/release/pkg-3.16.1/)** (Go 1.27.4), and the optional external key service **[KES 20261026](/blog/release/silo-20261026/#kes)**. Review the [component matrix](/compatibility/versions/) and [20261109 upgrade checks](/compatibility/server/#maintenance-20261109) before upgrading (updating standalone `mcli` or Console does not replace components embedded in an older Server binary).

> [!WARNING]
> **SILO is a MinIO fork maintained by the Pigsty community.** It is not affiliated with, endorsed by, or sponsored by MinIO, Inc. “MinIO” is a trademark of MinIO, Inc., used here only to identify the upstream project. See [Attribution](/about/attribution/) for source and licensing details.

SILO gives existing MinIO deployments an open release and security-maintenance path while preserving the S3 API, configuration, and on-disk storage contracts that make migration practical. This site covers installation, migration, administration, development, releases, and compatibility boundaries.

## Quickstart {#quickstart}

{{< tabs group="quickstart" >}}
{{< tab label="Docker" value="docker" >}}
The commands below pin [Server 20261109](/blog/release/silo-20261109/#delivery). Example credentials are for local evaluation only.

{{% steps %}}

### Start SILO {#quickstart-start}

```shell
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=silo-admin \
  -e MINIO_ROOT_PASSWORD=replace-with-a-strong-secret \
  -v silo-data:/data \
  docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z \
  server /data --console-address :9001
```

### Check readiness {#quickstart-check}

```shell
docker exec silo silo healthcheck ready
docker exec silo mcli alias set local http://127.0.0.1:9000 silo-admin replace-with-a-strong-secret
docker exec silo mcli mb local/demo
```

`silo healthcheck ready` confirms the local HTTP listener (plus KMS and etcd when configured), and can return `0` before storage or IAM finishes loading; see [healthcheck probes](/operations/monitoring/healthcheck-probe/#native-probe). Creating or reading a bucket through `mcli` confirms the S3 data path.

### Open the Console {#quickstart-console}

Open [http://127.0.0.1:9001](http://127.0.0.1:9001) and sign in with the root credentials above. Before production use, enable TLS, configure unique credentials, pin a verified image tag or digest, and test backup restoration.

{{% /steps %}}

See the [container deployment guide](/operations/deployments/baremetal-deploy-minio-as-a-container/) for persistent host paths, distroless images, service management, and production considerations.
{{< /tab >}}
{{< tab label="Linux packages" value="linux" >}}
Use [Download & Install](/download/#server) to select the RPM, DEB, APK, or standalone archive for your architecture. Published release assets include SHA-256 checksums, SPDX SBOMs, Sigstore bundles, and build-provenance attestations.

Native packages install the server as `/usr/bin/silo`; the service retains the `MINIO_*` environment-variable contract. Review the [binary and package compatibility notes](/compatibility/binary/) before replacing an existing `minio` package.
{{< /tab >}}
{{< tab label="Existing MinIO" value="minio" >}}
Read the [migration guide](/compatibility/migration/) and [20261109 upgrade checks](/compatibility/server/#maintenance-20261109) before changing images or binaries. Preserve data volumes and configuration, drain active batch jobs, stop every node running the old binary, and start every node on the same pinned SILO release. Never run `docker compose down -v` on volumes you intend to keep.
{{< /tab >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
Deploy SILO with the maintained standalone [`helm/silo` chart (`7.0.4`)](https://github.com/pgsty/silo/tree/RELEASE.2026-11-09T00-00-00Z/helm/silo), which defaults to `pgsty/silo:RELEASE.2026-11-09T00-00-00Z` and `pgsty/mc:RELEASE.2026-11-09T00-00-00Z` (pass `--set image.tag=RELEASE.2026-11-09T00-00-00Z` explicitly when running `helm upgrade --reuse-values`). Alternatively, override the tenant image in the archived MinIO Operator `v7.1.1` chart following the [Tenant Helm guide](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/), treating that Operator release as a frozen compatibility baseline.
{{< /tab >}}
{{< /tabs >}}
