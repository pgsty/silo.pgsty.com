---
title: "Deploy Silo as a Container"
url: "/operations/deployments/baremetal-deploy-minio-as-a-container/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-deploy-minio-as-a-container.rst
upstream_modified: true
---

<a id="deploy-minio-as-a-container"></a>
<a id="deploy-minio-container"></a>

This page documents deploying Silo as a container on an operating system that supports containerized processes.

This documentation assumes installation of Docker, Podman, or a similar runtime that supports the OCI container image format. Published `docker.io/pgsty/silo` releases provide two multi-architecture (`linux/amd64`, `linux/arm64`) image variants:

- **Standard image (`docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z`):** Built on [Red Hat Universal Base Image 9 Micro](https://catalog.redhat.com/software/container-stacks/detail/609560d9e2b160d361d24f98). Bundles `silo`, `mcli` (with an `mc` symlink), static `curl`, the POSIX entrypoint script, SILO legal files under `/licenses/`, and `mcli` legal files under `/licenses/mcli` ([#295](https://github.com/pgsty/silo/pull/295)).
- **Distroless image (`docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`):** Built on `gcr.io/distroless/static-debian12` with only the `silo` binary and `/licenses/` (no shell, `mcli`, `curl`, or entrypoint script). It ships the same UBI-derived CA root bundle (`/etc/ssl/certs/ca-certificates.crt`) as the standard UBI image ([#295](https://github.com/pgsty/silo/pull/295)) and configures a built-in `HEALTHCHECK` that runs `/usr/bin/silo healthcheck ready` (see [Healthcheck API](/operations/monitoring/healthcheck-probe/#native-probe)). Standard image deployments can also invoke `silo healthcheck` directly as a container probe.

Functionality and performance of the Silo container may be constrained by the base OS.

The procedure includes guidance for deploying Single-Node Multi-Drive (SNMD) and Single-Node Single-Drive (SNSD) topologies in support of early development and evaluation environments.

> [!WARNING]
> **Important**
>
> These examples cover Single-Node Single-Drive and Single-Node Multi-Drive development or evaluation deployments. They do not define a production Multi-Node Multi-Drive topology or an upgrade contract for Docker Compose, Docker Swarm, or another container orchestrator. For a production distributed deployment, use a tested [Kubernetes tenant workflow](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/) and validate persistence, networking, failure domains, and upgrades for your environment.
>
> The examples target [Server 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`). Validate the version with your workload and record the image digest for rollback.
>
> SILO disables in-place self-update; `MINIO_UPDATE=off` does not re-enable it. Upgrade containers by replacing the image with a verified SILO tag or digest, not with `mc admin update`.

## Considerations {#considerations}

### Review Checklists {#review-checklists}

Ensure you have reviewed our published Hardware, Software, and Security checklists before attempting this procedure.

### Erasure Coding Parity {#erasure-coding-parity}

SILO selects default parity from the number of drives **in each erasure set**, not the cluster-wide drive count. Sets with 8–16 drives default to `EC:4`; smaller sets have different defaults. See [storage-class settings](/reference/minio-server/settings/storage-class/) for the full table and configurable ranges. Parity is stored per object, so evaluate availability against that object’s set and actual layout.

Parity controls the relationship between object availability and storage on disk. The upstream MinIO [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) can help compare parity levels; treat it as an upstream planning aid rather than a Silo support contract.

While you can change erasure parity settings at any time, objects written with a given parity do **not** automatically update to the new parity settings.

### Container Storage {#container-storage}

This procedure assumes you mount one or more dedicated storage devices to the container to act as persistent storage for Silo.

Data stored on ephemeral container paths is lost when the container restarts or is deleted. Use any such paths at your own risk.

## Procedure {#procedure}

### 1. Start the Container {#start-the-container}

This procedure provides instructions for Podman and Docker in rootful mode. For rootless deployments, consult your container runtime documentation for user-namespace and volume ownership settings. In the `-distroless` image, `ENTRYPOINT` is `/usr/bin/silo`, `/data` is pre-created with mode `0777`, and privilege dropping uses `--user` rather than `MINIO_USERNAME`.

For all other container runtimes, follow the documentation for that runtime and specify the equivalent options, parameters, or configurations.

{{< tabs group="podman-docker" >}}
{{< tab label="Podman" value="podman" >}}
The following command creates a local data directory in your home folder and starts the Silo container with Podman:

```shell
mkdir -p ~/silo/data

podman run \
   -p 9000:9000 \
   -p 9001:9001 \
   --name silo \
   -v ~/silo/data:/data \
   -e "MINIO_UPDATE=off" \
   -e "MINIO_ROOT_USER=ROOTNAME" \
   -e "MINIO_ROOT_PASSWORD=CHANGEME123" \
   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z server /data --console-address ":9001"
```

The command binds port `9000` for the S3 API and port `9001` for the Web Console. To run the distroless image instead, replace the image reference with `docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`.

The host directory `~/silo/data` mounts to `/data` inside the container. Change [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) and [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) to set your root credentials.

For multi-drive deployments, mount each host drive or directory to a sequentially numbered path in the container, and pass the ellipsis range to [`silo server`](/reference/minio-server/#command-minio.server):

```shell
mkdir -p ~/silo/data-{1..4}

podman run \
   -p 9000:9000 \
   -p 9001:9001 \
   --name silo \
   -v ~/silo/data-1:/mnt/drive-1 \
   -v ~/silo/data-2:/mnt/drive-2 \
   -v ~/silo/data-3:/mnt/drive-3 \
   -v ~/silo/data-4:/mnt/drive-4 \
   -e "MINIO_UPDATE=off" \
   -e "MINIO_ROOT_USER=ROOTNAME" \
   -e "MINIO_ROOT_PASSWORD=CHANGEME123" \
   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z server /mnt/drive-{1...4} --console-address ":9001"
```

Replace `~/silo/data-1` through `~/silo/data-4` with dedicated mounted host drives (such as `/mnt/drive-1:/mnt/drive-1`) when testing drive-level isolation. For Windows hosts, use Windows path syntax for the host directory, such as `C:\silo\data:/data`.
{{< /tab >}}
{{< tab label="Docker" value="docker" >}}
The following command creates a local data directory in your home folder and starts the Silo container with Docker:

```shell
mkdir -p ~/silo/data

docker run \
   -p 9000:9000 \
   -p 9001:9001 \
   --name silo \
   -v ~/silo/data:/data \
   -e "MINIO_UPDATE=off" \
   -e "MINIO_ROOT_USER=ROOTNAME" \
   -e "MINIO_ROOT_PASSWORD=CHANGEME123" \
   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z server /data --console-address ":9001"
```

The command binds port `9000` for the S3 API and port `9001` for the Web Console. To run the distroless image instead, replace the image reference with `docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`.

The host directory `~/silo/data` mounts to `/data` inside the container. Change [`MINIO_ROOT_USER`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) and [`MINIO_ROOT_PASSWORD`](/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) to set your root credentials.

For multi-drive deployments, mount each host drive or directory to a sequentially numbered path in the container, and pass the ellipsis range to [`silo server`](/reference/minio-server/#command-minio.server):

```shell
mkdir -p ~/silo/data-{1..4}

docker run \
   -p 9000:9000 \
   -p 9001:9001 \
   --name silo \
   -v ~/silo/data-1:/mnt/drive-1 \
   -v ~/silo/data-2:/mnt/drive-2 \
   -v ~/silo/data-3:/mnt/drive-3 \
   -v ~/silo/data-4:/mnt/drive-4 \
   -e "MINIO_UPDATE=off" \
   -e "MINIO_ROOT_USER=ROOTNAME" \
   -e "MINIO_ROOT_PASSWORD=CHANGEME123" \
   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z server /mnt/drive-{1...4} --console-address ":9001"
```

Replace `~/silo/data-1` through `~/silo/data-4` with dedicated mounted host drives (such as `/mnt/drive-1:/mnt/drive-1`) when testing drive-level isolation. For Windows hosts, use Windows path syntax for the host directory, such as `C:\silo\data:/data`.
{{< /tab >}}
{{< /tabs >}}

### 2. Connect to the Deployment {#connect-to-the-deployment}

{{< tabs group="console-cli" >}}
{{< tab label="Console" value="console" >}}
Open your browser to [http://localhost:9001](http://localhost:9001) to open the [Silo Console](/administration/minio-console/#minio-console) login page.

Log in with the **MINIO_ROOT_USER** and **MINIO_ROOT_PASSWORD** from the previous step.

![Silo Console Login Page](/images/silo-console/console-login.webp){width="600"}

You can use the embedded Console for general administration tasks like Identity and Access Management, Metrics and Log Monitoring, or Server Configuration.
{{< /tab >}}
{{< tab label="CLI" value="cli" >}}
Follow the [Silo client installation instructions](/reference/minio-mc/#mc-install) for `mcli` on your local host. Run `mcli --version` to verify the installation. Published standalone archives and Linux packages install `mcli`; source builds and the client container retain the `mc` executable name.

Once installed, create an alias for the Silo deployment:

```shell
mcli alias set silo http://localhost:9000 USERNAME PASSWORD
```

Change the hostname, username, and password to reflect your deployment.
{{< /tab >}}
{{< /tabs >}}
