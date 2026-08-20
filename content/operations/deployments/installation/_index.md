---
title: "Installation and Management"
url: "/operations/deployments/installation/"
description: "Silo deployment topologies and installation instructions"
weight: 10
icon: fa-solid fa-download
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/installation.rst
upstream_modified: true
---

<a id="installation-and-management"></a>
<a id="minio-snsd"></a>
<a id="minio-snmd"></a>
<a id="minio-installation"></a>
<a id="minio-mnmd"></a>
<a id="deploy-minio-distributed"></a>

This section documents installing and managing the AGPLv3-licensed Silo object storage server on [Kubernetes](/operations/deployments/kubernetes/#minio-kubernetes) and [bare-metal or virtualized](/operations/deployments/baremetal/#minio-baremetal) infrastructure.

The `minio` executable, `MINIO_*` environment variables, S3 and Admin APIs, on-disk format, and MinIO Operator resource names are compatibility contracts. The prose uses the Silo brand, while commands and identifiers retain their compatible names.

Silo is an S3-compatible, software-defined distributed object storage server. The [download page](/download/) is the source of truth for currently published operating-system and architecture artifacts.

Silo uses [Erasure Coding](/operations/concepts/erasure-coding/#minio-erasure-coding) for object data. You can deploy it using one of the following topologies:

**[Single-Node Single-Drive](#minio-snsd) (SNSD or “Standalone”)**

> Local development and evaluation with no/limited reliability

**[Single-Node Multi-Drive](#minio-snmd) (SNMD or “Standalone Multi-Drive”)**

> Workloads with lower performance, scale, and capacity requirements
>
> Drive-level reliability with configurable tolerance for loss of up to 1/2 all drives
>
> Evaluation of multi-drive topologies and failover behavior.

**[Multi-Node Multi-Drive](#minio-mnmd) (MNMD or “Distributed”)**

> Enterprise-grade high-performance object storage
>
> Multi Node/Drive level reliability with configurable tolerance for loss of up to 1/2 all nodes/drives
>
> Primary storage for AI/ML, Distributed Query, Analytics, and other Data Lake components
>
> Scalable for Petabyte+ workloads - both storage capacity and performance

## Kubernetes {#kubernetes}

The archived MinIO Kubernetes Operator `v7.1.1` can manage Tenant resources that run a Silo server image. The Operator, its charts, CRDs, and `Tenant` kind retain their upstream names; its upstream release lifecycle is now frozen.

These retained Operator guides describe a compatibility snapshot. The upstream repository was archived on 2026-03-20, so verify `v7.1.1` against your Kubernetes distribution and override the Tenant image to `pgsty/minio`; the Silo project does not claim the former upstream vendor's platform support matrix.

- [Deploy a Silo Tenant with Helm](/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/)
- [Deploy the MinIO Operator](/operations/deployments/k8s-deploy-operator-helm-on-kubernetes/)
- [Review Kubernetes deployment guidance](/operations/deployments/kubernetes/)

## Baremetal {#baremetal}

Silo can run on physical machines, virtualized hosts, or in a container. Consult the current download matrix and each platform page for the verified artifact and scope.

- [Deploy Silo on Red Hat Linux](/operations/deployments/baremetal-deploy-minio-on-redhat-linux/#deploy-minio-rhel)
- [Deploy Silo on Ubuntu Linux](/operations/deployments/baremetal-deploy-minio-on-ubuntu-linux/#deploy-minio-ubuntu)
- [Deploy Silo as a Container](/operations/deployments/baremetal-deploy-minio-as-a-container/#deploy-minio-container)
- [Deploy Silo on macOS](/operations/deployments/baremetal-deploy-minio-on-macos/#deploy-minio-macos)
- [Deploy Silo on Windows](/operations/deployments/baremetal-deploy-minio-on-windows/#deploy-minio-windows)

> [!WARNING]
> **Important**
>
> Published artifacts do not establish equal production validation across platforms. Prefer a tested Linux or Kubernetes deployment for long-running workloads, pin exact package/image versions, and validate storage, failure domains, upgrade, and recovery behavior for the chosen topology.
