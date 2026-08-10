---
title: "SILO: S3-Compatible Object Storage by Pigsty"
description: "S3-compatible object storage, forked from MinIO and maintained by the Pigsty community: versioned releases, signed packages, the full web console, and security fixes with public advisories."
url: "/"
weight: 1
type: home
cascade:
  type: docs
minio_origin: true
silo_modified: true
---

{{% alert color="warning" %}}
**SILO is a MinIO fork maintained by the Pigsty community.** It is not affiliated with, endorsed by, or sponsored by MinIO, Inc. “MinIO” is a trademark of MinIO, Inc., used here only to identify the upstream project. See [Attribution](/about/attribution/) for source and licensing details.
{{% /alert %}}

SILO gives existing MinIO deployments an open release and security-maintenance path while preserving the S3 API, configuration, and operational contracts that make migration practical. This site covers installation, migration, administration, development, releases, and compatibility boundaries.

## Quickstart {#quickstart}

{{< tabpane text=true persist=header >}}
{{% tab header="Docker" %}}

The commands below pin the current SILO server release. Example credentials are suitable only for a local evaluation.

{{% steps %}}

### Start SILO {#quickstart-start}

```shell
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=silo-admin \
  -e MINIO_ROOT_PASSWORD=replace-with-a-strong-secret \
  -v silo-data:/data \
  pgsty/silo:RELEASE.2026-08-06T00-00-00Z \
  server /data --console-address :9001
```

### Check readiness {#quickstart-check}

```shell
docker exec silo silo healthcheck ready
```

Exit code `0` means the local server is ready. The probe is built into every SILO binary and does not require a second client inside the container.

### Open the Console {#quickstart-console}

Visit [http://127.0.0.1:9001](http://127.0.0.1:9001) and sign in with the credentials supplied above. Before production use, enable TLS, choose unique credentials, pin a tested image tag or digest, and test backup restoration.

{{% /steps %}}

See the [container deployment guide](/operations/deployments/baremetal-deploy-minio-as-a-container/) for persistent host paths, service management, and production considerations.

{{% /tab %}}
{{% tab header="Linux packages" %}}

Use [Download & Install](/download/#server) to select the RPM, DEB, APK, or standalone archive for your architecture. Published release assets include SHA-256 checksums and build-provenance attestations.

Native packages install the server as `/usr/bin/silo`; the service keeps the established `MINIO_*` environment-variable contract. Review the [binary and package compatibility notes](/compatibility/binary/) before replacing an existing `minio` package.

{{% /tab %}}
{{% tab header="Existing MinIO" %}}

Read the [migration guide](/compatibility/migration/) before changing images or binaries. Preserve the data volumes and configuration, stop every node running the old binary, and then start every node on the same pinned SILO release. Do not perform a mixed-binary rolling migration, and never use `docker compose down -v` on data you intend to keep.

{{% /tab %}}
{{% tab header="Kubernetes" %}}

The archived MinIO Operator `v7.1.1` can run a SILO Tenant when its image is overridden to `pgsty/silo` with a tested tag or digest. Follow the [Tenant Helm guide](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/) and treat that Operator version as a frozen compatibility baseline, not an actively maintained dependency.

{{% /tab %}}
{{< /tabpane >}}
