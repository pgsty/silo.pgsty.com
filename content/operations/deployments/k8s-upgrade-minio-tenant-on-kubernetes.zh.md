---
title: "升级 Silo Tenant"
url: "/zh/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/k8s-upgrade-minio-tenant-on-kubernetes.rst
upstream_modified: true
---

**版本说明：** 本页命令与输出示例以 [Server 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）为基准；下载与升级要求见[下载页](/zh/download/)和[发布说明](/zh/blog/release/silo-20261109/#upgrade)。

<a id="minio-tenant" data-td-print-local></a>
<a id="upgrade-a-minio-tenant"></a>
<a id="minio-k8s-upgrade-minio-tenant"></a>

以下步骤说明如何使用 Kustomize 或 Helm 升级单个 Silo Tenant，并涵盖独立 [`helm/silo` Chart `7.0.4`](https://github.com/pgsty/silo/tree/RELEASE.2026-11-09T00-00-00Z/helm/silo) 的升级要点。请先在非生产集群中测试确切的服务端镜像、Operator/Chart 版本与回滚流程。

> [!CAUTION]
> 服务端镜像必须保持为 `pgsty/silo`，并仅使用 [Silo 下载页](/zh/download/#server) 已发布的标签或摘要。上游 Tenant 默认值使用 MinIO 镜像。SILO 已禁用原地自更新；`MINIO_UPDATE=off` 不会重新启用它。请通过更新 Tenant 或 StatefulSet 的镜像版本执行升级。

如果集群仍运行非常早期的上游版本，切换至 SILO 前请先核对历史上游迁移要求。

> [!WARNING]
> **旧版 AD/LDAP 迁移要求**
>
> 对于运行早于 [RELEASE.2024-03-30T09-41-56Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-03-30T09-41-56Z) 的上游 MinIO 镜像且启用了 [AD/LDAP](/zh/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) 的 Tenant，升级到 SILO 前 **必须** 阅读 [RELEASE.2024-04-18T19-09-19Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-04-18T19-09-19Z) 发布说明并完成其中的迁移步骤。

## 升级到 20261109 之前 {#prerequisites}

将任何 Kubernetes Tenant 或独立 `helm/silo` 部署升级到 [SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）之前，请完成以下五项检查：

1. **18 Pod 及以上单池布局必须排空停机重启。** 若单个存储池内的各纠删集不全共享同一组 Pod/主机（自动布局下通常为 18 个及以上 Pod），必须采用排空全停重启（先将 StatefulSet 缩容至 `0` 并确认全部旧 Pod 终止，再启动 `20261109` Pod），**切勿**直接执行 StatefulSet 滚动更新，因为旧版与新版的单池删除和复制锁域（[#298](https://github.com/pgsty/silo/issues/298)）在跨纠删集时无法互斥。
2. **混合版本期间暂停归档恢复请求。** 只要仍有对端 Pod 运行旧版本或不可达，已升级的 Pod 会对 `POST ?restore` 返回 `503 Service Unavailable`。请暂停发起新的恢复请求，直至全部 Pod 升级到 `20261109`。完整的多池生命周期保护与 S3 批量删除 Object Lock 保护同样要求所有服务 Pod 完成升级。
3. **升级前排空批处理作业。** 切换版本前停止提交批处理作业，并排空或取消所有运行中、等待中和暂停中的作业。未完成的旧格式作业需在全部 Pod 升级后重新提交，已完成的作业保持完成状态；在仍有未完成的 `20261109` 作业时切勿降级。请按[批处理升级与回退清单](/zh/administration/batch-framework/#upgrade-20261109)操作。
4. **保留无头服务启动发现并执行数据面校验。** 对端发现无头服务（`*-hl`）必须保留 `publishNotReadyAddresses: true`，以便各 Pod 在启动阶段发现对端。Pod 重启后，恢复业务流量前须对每个 Pod 执行有界超时的签名 S3 写入与回读校验——单凭 `ready` 和 `cluster` 探针无法证明每个远端磁盘已完成重连，详见[重启后的就绪窗口](/zh/operations/monitoring/healthcheck-probe/#startup-readiness-window)。
5. **使用 Helm `--reuse-values` 时显式固定镜像标签。** 独立 `helm/silo` Chart **`7.0.4`**（[#296](https://github.com/pgsty/silo/issues/296)）默认部署 SILO 与 `mcli` `RELEASE.2026-11-09T00-00-00Z`，但 `helm upgrade --reuse-values` 会保留此前存储的 `image.tag`。复用已存 values 升级时，必须显式传入 `--set image.tag=RELEASE.2026-11-09T00-00-00Z`（对于 Operator Tenant Chart 则为 `--set tenant.image.tag=RELEASE.2026-11-09T00-00-00Z`）。

<a id="minio-upgrade-tenant-kustomize"></a>
<a id="minio-upgrade-tenant-plugin"></a>
<a id="kustomize-tenant" data-td-print-local></a>

## 使用 Kustomize 升级 Tenant {#upgrade-a-tenant-using-kustomize}

以下步骤使用 Kustomize 和 `kubectl` CLI 升级 MinIO Tenant。如果你是通过 [Helm](/zh/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/#deploy-tenant-helm) 部署 Tenant，请改用[使用 MinIO Helm Chart 升级 Tenant](#minio-upgrade-tenant-helm)步骤。

若 Tenant 最初通过 Operator Console 部署，升级前需先导出基础配置文件；若最初通过 Kustomize 部署，直接使用原部署的 `kustomization` 文件作为基础配置。

请根据 Tenant 的部署方式选择下方标签页：

{{< tabs group="tabs-ff01f39e" default="operator-console-deployed-tenant" >}}
{{< tab label="Operator Console-Deployed Tenant" value="operator-console-deployed-tenant" >}}
1. 创建基础配置文件：

   1. 在工作目录中，使用 `kubectl get` 将当前 Tenant 配置保存到文件：

      ```shell
      kubectl get tenant/my-tenant -n my-tenant-ns -o yaml > my-tenant-base.yaml
      ```

      将 `my-tenant` 和 `my-tenant-ns` 替换为待升级 Tenant 的名称和命名空间。

      编辑该文件，删除集群自动生成的元数据字段：

      - `creationTimestamp:`
      - `resourceVersion:`
      - `uid:`
      - `selfLink:`（如果存在）

      例如，从 `metadata` 中移除上述字段：

      ```yaml
      metadata:
        creationTimestamp: "2024-05-29T21:22:20Z"
        generation: 1
        name: my-tenant
        namespace: my-tenant-ns
        resourceVersion: "4699"
        uid: d5b8e468-3bed-4aa3-8ddb-dfe1ee0362da
      ```

   2. 在同一目录中，创建一个 `kustomization.yaml` 文件，其内容类似如下：

      ```yaml
      apiVersion: kustomize.config.k8s.io/v1beta1
      kind: Kustomization

      resources:
      - my-tenant-base.yaml

      patches:
      - path: upgrade-minio-tenant.yaml
      ```

      如果你在上一步为 `kubectl get` 输出使用了不同的文件名，请将 `my-tenant-base.yaml` 替换为对应文件名。
{{< /tab >}}
{{< tab label="现有 Kustomize 部署 Tenant" value="existing-kustomized-deployed-tenant" >}}
1. 使用原始部署中的 `kustomization` 文件作为基础配置来升级 Tenant。如果已经没有这些文件，请按照 Operator Console-Deployed Tenant 标签页中的说明操作。
{{< /tab >}}
{{< /tabs >}}

2. 创建一个 `upgrade-minio-tenant.yaml` 文件，其内容类似如下：

```yaml
apiVersion: minio.min.io/v2
kind: Tenant

metadata:
  name: my-tenant
  namespace: my-tenant-ns

spec:
  image: docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z
  env:
    - name: MINIO_UPDATE
      value: "off"
```

该文件会指示 Kustomize 使用指定镜像升级 Tenant。该文件名 `upgrade-minio-tenant.yaml` 必须与上一步创建的 `kustomization.yaml` 中 `patches.path` 指定的文件名一致。

将 `my-tenant` 和 `my-tenant-ns` 替换为待升级 Tenant 的名称和命名空间。仅当目标 Silo 版本已公开发布且经过验证时，才替换示例镜像标签。

或者，你也可以按照本地流程直接更新基础配置。更多信息请参阅 [Kustomize Documentation](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization)。

3. 在与上述文件相同的目录中，使用 `kubectl apply` 将更新后的配置应用到 Tenant：

```shell
kubectl apply -k ./
```

输出类似如下：

```text
tenant.minio.min.io/my-tenant configured
```

<a id="minio-upgrade-tenant-helm"></a>
<a id="minio-helm-chart-tenant" data-td-print-local></a>

## 使用 MinIO Helm Chart 升级 Tenant {#upgrade-the-tenant-using-the-minio-helm-chart}

本步骤使用 Helm Charts 升级现有 MinIO Tenant。

如果你是通过 Kustomize 部署 Tenant，请改用 [使用 Kustomize 升级 Tenant](#minio-upgrade-tenant-kustomize) 步骤。

1. 验证现有 Silo Tenant 安装。

   使用 `kubectl get all -n TENANT_NAMESPACE` 验证所有 Tenant pod 和 service 的健康状态。

   使用 `helm list` 命令查看该命名空间中已安装的 chart：

   ```shell
   helm list -n TENANT_NAMESPACE
   ```

   结果应类似如下：

   ```shell
   NAME            NAMESPACE         REVISION        UPDATED                                 STATUS          CHART           APP VERSION
   CHART_NAME      TENANT_NAMESPACE  1               2023-11-01 15:49:58.810412732 -0400 EDT deployed        tenant-5.0.x   v5.0.x
   ```

2. 更新 Operator 仓库

   使用 `helm repo update minio-operator` 更新 MinIO Operator 仓库。 如果你为 MinIO Operator 仓库设置了不同的别名，请在命令中指定该别名。 你可以使用 `helm repo list` 查看已安装的仓库列表。

   在更新 Operator 仓库后，使用 `helm search` 检查最新可用的 chart 版本：

   ```shell
   helm search repo minio-operator
   ```

   返回结果应类似如下：

   ```shell
   NAME                            CHART VERSION   APP VERSION     DESCRIPTION
   minio-operator/minio-operator   4.3.7           v4.3.7          A Helm chart for MinIO Operator
   minio-operator/operator         7.1.1          v7.1.1         A Helm chart for MinIO Operator
   minio-operator/tenant           7.1.1          v7.1.1         A Helm chart for MinIO Operator
   ```

   `minio-operator/minio-operator` 是旧版 chart，正常情况下 **不应** 安装。
3. 保留并审查 Tenant values

   导出当前发布由用户提供的 values，然后确认该文件保留了所有拓扑、存储、TLS、凭据与调度设置：

   ```shell
   helm get values CHART_NAME -n TENANT_NAMESPACE -o yaml > values.yaml
   ```

   将 `tenant.image.repository` 设为 `docker.io/pgsty/silo`，将 `tenant.image.tag` 固定为 `RELEASE.2026-11-09T00-00-00Z`（或其他经测试的已发布 Silo 版本），并确保 `tenant.env` 包含 `MINIO_UPDATE=off`。不得让 Chart 升级恢复上游镜像默认值。

4. 运行已固定的 `helm upgrade`

   Chart 版本与 Silo 服务端镜像应分别固定，并传入经过审查的 values 文件：

   ```shell
   helm upgrade -n TENANT_NAMESPACE \
     --version 7.1.1 \
     --values values.yaml \
     CHART_NAME minio-operator/tenant
   ```

   对于不使用 MinIO Operator 的独立 [`helm/silo` Chart `7.0.4`](https://github.com/pgsty/silo/tree/RELEASE.2026-11-09T00-00-00Z/helm/silo) 部署，Chart `7.0.4` 默认将 `image.tag` 与 `mcImage.tag` 设为 `RELEASE.2026-11-09T00-00-00Z`（[#296](https://github.com/pgsty/silo/issues/296)）。若执行 `helm upgrade --reuse-values`，请显式传入 `--set image.tag=RELEASE.2026-11-09T00-00-00Z`，避免 Helm 继续保留旧镜像标签。

   命令成功执行后，`REVISION` 值会递增。
5. 验证 Tenant 升级

   检查所有 Service 和 Pod 是否在线，核对实际运行的镜像摘要，并在恢复业务流量前对每个 Pod 执行有界超时的签名 S3 写入与回读检查，详见[重启后的就绪窗口](/zh/operations/monitoring/healthcheck-probe/#startup-readiness-window)。
