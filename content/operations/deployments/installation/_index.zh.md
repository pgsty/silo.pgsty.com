---
title: "安装与管理"
url: "/zh/operations/deployments/installation/"
description: "MinIO Deployment Topologies and Installation Instructions"
weight: 10
icon: fa-solid fa-download
minio_origin: true
silo_modified: false
---

<a id="minio-snsd"></a>
<a id="minio-snmd"></a>
<a id="minio-installation"></a>
<a id="minio-mnmd"></a>
<a id="deploy-minio-distributed"></a>
<a id="id1"></a>

本节介绍如何在 [Kubernetes](/zh/operations/deployments/kubernetes/#minio-kubernetes) 和 [裸金属](/zh/operations/deployments/baremetal/#minio-baremetal) 基础设施上安装和管理采用 AGPLv3 许可的 Community MinIO 对象存储。

- [Installing and Running MinIO on Linux](https://www.youtube.com/watch?v=74usXkZpNt8&list=PLFOIsHSSYIK1BnzVY66pCL-iJ30Ht9t1o)
- [Object Storage Essentials](https://www.youtube.com/playlist?list=PLFOIsHSSYIK3WitnqhqfpeZ6fRFKHxIr7)
- [How to Connect to MinIO with JavaScript](https://www.youtube.com/watch?v=yUR4Fvx0D3E&list=PLFOIsHSSYIK3Dd3Y_x7itJT1NUKT5SxDh&index=5)

MinIO 是一个软件定义的高性能分布式对象存储服务器。 你可以在消费级或企业级硬件上，以及多种操作系统和架构上运行 MinIO。

所有 MinIO 部署都实现了 [纠删码](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) 后端。 你可以使用以下拓扑之一部署 MinIO：

**[单机单盘](#minio-snsd) （SNSD，即”单机”模式）**

> 适用于本地开发与评估，可靠性有限或无冗余

**[单机多盘](#minio-snmd) （SNMD，即”单机多盘”模式）**

> 适用于对性能、规模和容量要求较低的工作负载
>
> 提供驱动器级可靠性，可配置为最多容忍 1/2 驱动器丢失
>
> 适合评估多驱动器拓扑和故障切换行为。

**[多机多盘](#minio-mnmd) （MNMD，即”分布式”模式）**

> 企业级高性能对象存储
>
> 提供节点/驱动器级可靠性，可配置为最多容忍 1/2 节点/驱动器丢失
>
> 可作为 AI/ML、分布式查询、分析及其他数据湖组件的主存储
>
> 可扩展到 PB+ 级工作负载，同时扩展存储容量与性能

## Kubernetes {#kubernetes}

MinIO 提供 Kubernetes 原生的 Operator 框架，用于在你的托管基础设施上管理和部署 Tenant。

MinIO 完全支持上游 Kubernetes，以及多数基于上游构建的发行版。 其中包括但不限于 RedHat Openshift、SUSE Rancher 和 VMWare Tanzu。 MinIO 也完全支持云厂商提供的 Kubernetes 引擎，例如 Elastic Kubernetes Engine、Google Kubernetes Service 和 Azure Kubernetes Service。

请选择最适合你的 Kubernetes 基础设施的链接。 如果你的提供商未列出，请以上游 Kubernetes 文档为基线，并根据提供商的指导或其与上游语义和行为的差异进行调整。

- [在 Kubernetes (Upstream) 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-kubernetes)
- [在 Openshift Kubernetes 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-openshift)
- [在 SUSE Rancher Kubernetes 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-rancher)
- [在 Elastic Kubernetes Service 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-eks)
- [在 Google Kubernetes Engine 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-gke)
- [在 Azure Kubernetes Service 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-aks)

## 裸金属 {#id3}

MinIO 支持部署到裸机基础设施上，包括运行 Linux、MacOS 和 Windows 的物理机或虚拟化主机。 你也可以在受支持的操作系统上以容器方式部署 MinIO。

- [在 RedHat Linux 上部署 MinIO](/zh/operations/deployments/baremetal-deploy-minio-on-redhat-linux/#deploy-minio-rhel)
- [在 Ubuntu Linux 上部署 MinIO](/zh/operations/deployments/baremetal-deploy-minio-on-ubuntu-linux/#deploy-minio-ubuntu)
- [以容器方式部署 MinIO](/zh/operations/deployments/baremetal-deploy-minio-as-a-container/#deploy-minio-container)
- [在 MacOS 上部署 MinIO](/zh/operations/deployments/baremetal-deploy-minio-on-macos/#deploy-minio-macos)
- [在 Windows 上部署 MinIO](/zh/operations/deployments/baremetal-deploy-minio-on-windows/#deploy-minio-windows)

{{% alert color="warning" %}}
**重要**

MinIO 强烈建议在长期开发和生产环境中使用 [Linux (RHEL, Ubuntu)](https://silo.pigsty.cc/minio/linux/index.html) 或 [Kubernetes (Upstream, OpenShift)](https://silo.pigsty.cc/minio/kubernetes/upstream/index.html)。

对于 MacOS、Windows 或容器化部署上的 <abbr title="单机多盘">SNMD</abbr> 和 <abbr title="多机多盘">MNMD</abbr> 拓扑，MinIO 不保证提供支持。
{{% /alert %}}
