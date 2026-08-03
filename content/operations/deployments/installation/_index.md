---
title: "Installation and Management"
url: "/operations/deployments/installation/"
description: "MinIO Deployment Topologies and Installation Instructions"
weight: 10
icon: fa-solid fa-download
minio_origin: true
silo_modified: true
---

<a id="installation-and-management"></a>
<a id="minio-snsd"></a>
<a id="minio-snmd"></a>
<a id="minio-installation"></a>
<a id="minio-mnmd"></a>
<a id="deploy-minio-distributed"></a>

This section documents steps for installing and managing the AGPLv3-licensed Community MinIO Object Storage on [Kubernetes](/operations/deployments/kubernetes/#minio-kubernetes) and [Baremetal](/operations/deployments/baremetal/#minio-baremetal) infrastructures.

- [Installing and Running MinIO on Linux](https://www.youtube.com/watch?v=74usXkZpNt8&list=PLFOIsHSSYIK1BnzVY66pCL-iJ30Ht9t1o)
- [Object Storage Essentials](https://www.youtube.com/playlist?list=PLFOIsHSSYIK3WitnqhqfpeZ6fRFKHxIr7)
- [How to Connect to MinIO with JavaScript](https://www.youtube.com/watch?v=yUR4Fvx0D3E&list=PLFOIsHSSYIK3Dd3Y_x7itJT1NUKT5SxDh&index=5)

MinIO is a software-defined high performance distributed object storage server. You can run MinIO on consumer or enterprise-grade hardware and a variety of operating systems and architectures.

All MinIO deployments implement [Erasure Coding](/operations/concepts/erasure-coding/#minio-erasure-coding) backends. You can deploy MinIO using one of the following topologies:

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

MinIO provides a Kubernetes-native Operator framework for managing and deploying Tenants onto your managed infrastructure.

MinIO fully supports upstream Kubernetes and most flavors which inherit from the upstream as a base. This includes, but is not limited to, RedHat Openshift, SUSE Rancher, VMWare Tanzu. MinIO also fully supports cloud-based Kubernetes engines such as Elastic Kubernetes Engine, Google Kubernetes Service, and Azure Kubernetes Service.

Select the link most appropriate for your Kubernetes infrastructure. If your provider is not listed, use the Kubernetes Upstream documentation as a baseline and modify as needed based on your provider’s guidance or divergence from upstream semantics and behavior.

- [Deploy MinIO on Kubernetes (Upstream)](/operations/deployments/kubernetes/#deploy-operator-kubernetes)
- [Deploy MinIO on Openshift Kubernetes](/operations/deployments/kubernetes/#deploy-operator-openshift)
- [Deploy MinIO on SUSE Rancher Kubernetes](/operations/deployments/kubernetes/#deploy-operator-rancher)
- [Deploy MinIO on Elastic Kubernetes Service](/operations/deployments/kubernetes/#deploy-operator-eks)
- [Deploy MinIO on Google Kubernetes Engine](/operations/deployments/kubernetes/#deploy-operator-gke)
- [Deploy MinIO on Azure Kubernetes Service](/operations/deployments/kubernetes/#deploy-operator-aks)

## Baremetal {#baremetal}

MinIO supports deploying onto baremetal infrastructure - physical machines or virtualized hosts - running Linux, MacOS, and Windows. You can also deploy MinIO as a container onto supported Operating Systems.

- [Deploy MinIO onto RedHat Linux](/operations/deployments/baremetal-deploy-minio-on-redhat-linux/#deploy-minio-rhel)
- [Deploy MinIO onto Ubuntu Linux](/operations/deployments/baremetal-deploy-minio-on-ubuntu-linux/#deploy-minio-ubuntu)
- [Deploy MinIO as a Container](/operations/deployments/baremetal-deploy-minio-as-a-container/#deploy-minio-container)
- [Deploy MinIO onto MacOS](/operations/deployments/baremetal-deploy-minio-on-macos/#deploy-minio-macos)
- [Deploy MinIO onto Windows](/operations/deployments/baremetal-deploy-minio-on-windows/#deploy-minio-windows)

{{% alert color="warning" %}}
**Important**

MinIO strongly recommends [Linux (RHEL, Ubuntu)](https://silo.pgsty.com/operations/deployments/baremetal/) or [Kubernetes (Upstream, OpenShift)](https://silo.pgsty.com/operations/deployments/kubernetes/) for long-term development and production environments.

MinIO provides no guarantee of support for <abbr title="Single-Node Multi-Drive">SNMD</abbr> or <abbr title="Multi-Node Multi-Drive">MNMD</abbr> topologies on MacOS, Windows, or Containerized deployments.
{{% /alert %}}
