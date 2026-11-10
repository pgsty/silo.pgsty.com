---
title: "修改 Silo Tenant"
url: "/zh/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/k8s-modify-minio-tenant-on-kubernetes.rst
upstream_modified: true
---

<a id="minio-tenant" data-td-print-local></a>
<a id="modify-a-minio-tenant"></a>
<a id="minio-k8s-modify-minio-tenant-security"></a>
<a id="minio-k8s-modify-minio-tenant"></a>

部署完成后，你可以修改租户以调整可变配置项。 有关 MinIO Custom Resource Definition 中可用设置的完整说明，请参阅 [MinIO 自定义资源定义](/zh/reference/operator-crd/#minio-operator-crd)。

修改租户的方法取决于你最初如何部署该租户：

{{< tabs group="kustomize-helm" >}}
{{< tab label="Kustomize" value="kustomize" >}}
对于使用 Kustomize 部署的租户，你可以修改基础 Kustomization 资源，并在包含 `kustomization.yaml` 的目录上运行 `kubectl apply -k` 进行应用。

```shell
kubectl apply -k ~/kustomization/TENANT-NAME/
```

请根据本地配置修改 Kustomization 目录路径。
{{< /tab >}}
{{< tab label="Helm" value="helm" >}}
对于使用 Helm 部署的租户，你可以修改基础 `values.yaml`，并通过 chart 升级租户：

```shell
helm upgrade TENANT-NAME minio-operator/tenant -f values.yaml -n TENANT-NAMESPACE
```

上述命令默认使用 MinIO Operator Chart 仓库（`v7.1.1`）。请确保 `tenant.image` 保持固定在已验证的 `docker.io/pgsty/silo` 版本，例如 `RELEASE.2026-11-09T00-00-00Z`（[SILO 20261109](/zh/blog/release/silo-20261109/)）。如果你管理的是独立 [`helm/silo` Chart `7.0.4`](https://github.com/pgsty/silo/tree/RELEASE.2026-11-09T00-00-00Z/helm/silo) 部署（[#296](https://github.com/pgsty/silo/issues/296)）并使用 `helm upgrade --reuse-values`，请显式传入 `--set image.tag=RELEASE.2026-11-09T00-00-00Z`，避免 Helm 继续保留此前存储的标签。

分别将 `TENANT-NAME` 和 `TENANT-NAMESPACE` 替换为租户的名称和命名空间。你可以使用 `helm list -n TENANT-NAMESPACE` 验证租户名称。
{{< /tab >}}
{{< /tabs >}}

**添加受信任的证书颁发机构**

> MinIO 租户会使用主机系统的受信任根证书存储，校验每个连接客户端提供的 TLS 证书。 MinIO Operator 可以为租户挂载额外的第三方 Certificate Authorities (CA)，以便校验由这些 CA 签发的客户端 TLS 证书。
>
> 若要自定义挂载到每个租户 MinIO pod 的受信任 CA，请启用 **Custom Certificates** 开关。 点击 **Add CA Certificate +** 按钮即可添加第三方 CA 证书。
>
> 如果 MinIO 租户无法在容器操作系统的信任库 *或* 显式挂载的 CA 中匹配到传入客户端 TLS 证书的签发者，MinIO 会将该连接视为无效并拒绝。

<a id="pool" data-td-print-local></a>

## 管理租户 Pool {#manage-tenant-pools}

<a id="runtime-class" data-td-print-local></a>

### 指定 Runtime Class {#specify-runtime-class}

> [!NOTE]
> **新增: Console**
>
> 0.23.1

在为租户添加新 pool 或修改现有 pool 时，你可以为这些 pool 指定 [Runtime Class Name](https://kubernetes.io/docs/concepts/containers/runtime-class/)。

<a id="id2" data-td-print-local></a>

### 退役租户 服务器池 {#decommission-a-tenant-server-pool}

MinIO Operator 4.4.13 及更高版本支持退役租户中的服务器池。请按照[退役服务器池](/zh/operations/deployments/baremetal-decommission-server-pool/)流程先将该 pool 从租户中排空，再编辑租户 YAML 将该 pool 从 StatefulSet 中移除。移除租户 pool 时，请确保所有剩余 pool 的 `spec.pools[n].name` 字段都具有明确取值。

> [!NOTE]
> **先下线再新增时保持 pool 顺序**
>
> 如果你在多 pool 部署中下线了一个 pool，就不能在新 pool 中复用相同的节点编号序列。 例如，假设某个部署包含以下几个 pool：
>
> ```text
> https://minio-{1...4}.example.net/mnt/drive-{1...4}
> https://minio-{5...8}.example.net/mnt/drive-{1...4}
> https://minio-{9...12}.example.net/mnt/drive-{1...4}
> ```
>
> 如果你下线了 `minio-{5...8}` 这个 pool，就不能再用相同的节点编号新增一个 pool。你必须将新 pool 添加在 `minio-{9...12}` *之后*：
>
> ```text
> https://minio-{1...4}.example.net/mnt/drive-{1...4}
> https://minio-{9...12}.example.net/mnt/drive-{1...4}
> https://minio-{13...16}.example.net/mnt/drive-{1...4}
> ```
