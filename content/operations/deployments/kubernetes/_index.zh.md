---
title: "在 Kubernetes 上部署 MinIO"
url: "/zh/operations/deployments/kubernetes/"
weight: 10
icon: fa-solid fa-dharmachakra
minio_origin: true
silo_modified: false
---

<a id="kubernetes-minio"></a>
<a id="minio-operator-installation"></a>
<a id="deploy-operator-aks"></a>
<a id="deploy-operator-gke"></a>
<a id="deploy-operator-eks"></a>
<a id="deploy-operator-rancher"></a>
<a id="deploy-operator-openshift"></a>
<a id="deploy-operator-kubernetes"></a>
<a id="minio-kubernetes"></a>

MinIO 是一个 Kubernetes 原生的高性能对象存储，提供兼容 S3 的 API。 MinIO Kubernetes Operator 支持将 MinIO 租户部署到私有云和公有云基础设施（“Hybrid” Cloud）上。

所有文档都默认你已经熟悉所引用的 Kubernetes 概念、工具和操作流程。 虽然 MinIO 文档 *可能* 会以 best-effort 方式提供 Kubernetes 相关资源的配置或部署指导，但它不能替代官方 [Kubernetes Documentation](https://kubernetes.io/docs/)。

MinIO Operator 是 MinIO 官方提供的 Kubernetes 原生 Operator，用于管理 MinIO 租户在 Kubernetes 基础设施上的部署。

该 Operator 提供以 MinIO 为核心的租户管理功能，包括对所有 MinIO 核心特性的配置支持。

你可以通过 MinIO 的 [Custom Resource Definition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions) 或 Operator Console UI 与 Operator 交互。

CRD 为使用 Kustomize 等工具部署租户提供了高度可定制的入口。 你也可以使用 MinIO Operator Console 这一功能完整的 Web UI 来部署和配置 MinIO 租户。

{{% alert color="warning" %}}
**重要**

MinIO Operator Console UI 已被弃用，并在 MinIO Operator 6.0.0 中移除。

你仍可继续使用标准 Kubernetes 方式管理 MinIO 租户，例如 Kustomize 模板、Helm Charts，以及用于查看租户命名空间和资源的 `kubectl` 命令。
{{% /alert %}}
