---
title: "删除 MinIO Tenant"
url: "/zh/operations/deployments/k8s-delete-minio-tenant-on-kubernetes/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="minio-tenant"></a>
<a id="minio-k8s-delete-minio-tenant"></a>

## 前提条件 {#id2}

### MinIO Kubernetes Operator {#minio-kubernetes-operator}

本页步骤 *要求* 已正确安装 MinIO Kubernetes Operator，并假定本地主机也安装了与之匹配的 MinIO Kubernetes Operator。 本步骤默认使用最新稳定版 Operator，即版本 7.1.1。

有关部署 MinIO Operator 的完整文档，请参阅 [在 Kubernetes 上部署 MinIO](/zh/operations/deployments/kubernetes/#deploy-operator-kubernetes)。

## Tenant 持久卷声明 {#tenant}

Tenant 生成的每个 Persistent Volume Claim（`PVC`）在删除时的行为，取决于其绑定的 Persistent Volume（`PV`）所配置的 [Reclaim Policy](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#reclaim-policy)：

- 对于 `recycle` 或 `delete` 策略，命令会删除 `PVC`。
- 对于 `retain` 策略，命令会保留 `PVC`。

{{% alert color="danger" %}}
**警告**

无论是自动还是手动删除底层 `PV`，都会导致 MinIO Tenant 上存储的对象丢失。

在删除 Tenant *之前*，请充分确认已存储数据的安全性。
{{% /alert %}}

## 步骤 {#id3}

{{< tabpane text=true persist=header >}}
{{% tab header="Kustomization" %}}
你可以通过删除命名空间来删除使用 Kustomization 安装的 Tenant：

```shell
kubectl delete namespace TENANT-NAMESPACE
```

将 `TENANT-NAMESPACE` 替换为要删除的命名空间名称。

{{% alert color="warning" %}}
**重要**

在运行命令前，请确认你指定的是正确的待删除命名空间。 命名空间删除发生在 Kubernetes 层，因此 MinIO Operator 无法干预或撤销该操作。
{{% /alert %}}
{{% /tab %}}
{{% tab header="Helm" %}}
你可以使用 `helm uninstall` 命令删除通过 Helm 安装的 Tenant：

```shell
helm uninstall --namespace MINIO-TENANT TENANT-NAME minio-operator/tenant
```

上述命令默认使用的是 MinIO Operator Chart 仓库。 如果你是手动安装 Chart，或使用了不同的仓库名称，请在命令中指定相应的 chart 或名称。

分别将 `TENANT-NAME` 和 `TENANT-NAMESPACE` 替换为 Tenant 的名称和命名空间。 你可以使用 `helm list -n TENANT-NAMESPACE` 验证 Tenant 名称。
{{% /tab %}}
{{< /tabpane >}}
