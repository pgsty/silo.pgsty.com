---
title: "SILO：Pigsty 持续维护的 S3 兼容对象存储"
description: "由 Pigsty 持续维护的 S3 兼容对象存储，提供安全更新、版本化发行、完整控制台与现有部署的运维连续性。"
url: "/zh/"
weight: 1
type: home
cascade:
  type: docs
upstream_link: https://github.com/minio/docs
upstream_modified: true
body_class: landing-page
---

本站面向 **[SILO 20261109](/zh/blog/release/silo-20261109/)**（内嵌 [Console 2.7.0](/zh/blog/release/console-2.7.0/)，Go 1.27.3）、独立版 **[Console 2.7.1](/zh/blog/release/console-2.7.1/)**、**[mcli 20261112](/zh/blog/release/mcli-20261112/)**、**[silo-pkg 3.16.1](/zh/blog/release/pkg-3.16.1/)**（Go 1.27.4），以及可选外部密钥服务 **[KES 20261026](/zh/blog/release/silo-20261026/#kes)**。升级前请核对[组件版本矩阵](/zh/compatibility/versions/)与 [20261109 升级检查](/zh/compatibility/server/#maintenance-20261109)（单独升级独立版 `mcli` 或 Console 不会替换旧版 Server 内嵌的组件）。

> [!WARNING]
> **SILO 是由 Pigsty 社区维护的 MinIO 分支。** 本项目并非 MinIO, Inc. 的关联项目，也未获得其认可、赞助或背书。“MinIO” 是 MinIO, Inc. 的商标，此处仅用于标识上游项目。源码与许可信息详见[归属与署名](/zh/about/attribution/)。

SILO 在保留 S3 API、配置与磁盘存储契约的同时，为现有 MinIO 部署提供开放的发行与安全维护路径。本站覆盖安装、迁移、管理、开发、版本发布与兼容边界。

## 快速开始 {#quickstart}

{{< tabs group="quickstart" >}}
{{< tab label="Docker" value="docker" >}}
以下命令固定使用已公开发布的 [Server 20261109](/zh/blog/release/silo-20261109/#delivery)。示例凭据仅用于本地评估。

{{% steps %}}

### 启动 SILO {#quickstart-start}

```shell
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=silo-admin \
  -e MINIO_ROOT_PASSWORD=replace-with-a-strong-secret \
  -v silo-data:/data \
  docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z \
  server /data --console-address :9001
```

### 检查就绪状态 {#quickstart-check}

```shell
docker exec silo silo healthcheck ready
docker exec silo mcli alias set local http://127.0.0.1:9000 silo-admin replace-with-a-strong-secret
docker exec silo mcli mb local/demo
```

`silo healthcheck ready` 检查本地 HTTP 监听与已配置的 KMS / etcd 状态，可能在存储或 IAM 完成加载前返回 `0`，详见[健康检查探针](/zh/operations/monitoring/healthcheck-probe/#native-probe)。通过内置 `mcli` 创建或读取存储桶可进一步确认 S3 数据路径已就绪。

### 打开管理控制台 {#quickstart-console}

访问 [http://127.0.0.1:9001](http://127.0.0.1:9001)，使用上面的 root 凭据登录。投入生产前，请启用 TLS、配置独立强凭据、固定经过验证的镜像标签或摘要，并测试备份恢复。

{{% /steps %}}

持久化宿主机路径、Distroless 镜像变体、服务管理与生产注意事项见[容器部署指南](/zh/operations/deployments/baremetal-deploy-minio-as-a-container/)。
{{< /tab >}}
{{< tab label="Linux 软件包" value="linux" >}}
在[下载与安装](/zh/download/#server)页面选择对应架构的 RPM、DEB、APK 或独立归档。正式发布制品附带 SHA-256 校验和、SPDX SBOM、Sigstore 签名包与构建溯源证明。

原生软件包将服务端安装为 `/usr/bin/silo`，并沿用 `MINIO_*` 环境变量契约。替换现有 `minio` 软件包前，请阅读[二进制与软件包兼容说明](/zh/compatibility/binary/)。
{{< /tab >}}
{{< tab label="现有 MinIO" value="minio" >}}
替换镜像或二进制前，请先阅读[迁移指南](/zh/compatibility/migration/)与 [20261109 升级检查](/zh/compatibility/server/#maintenance-20261109)。保留数据卷与配置，排空未完成的批处理任务，停止所有运行旧二进制的节点，再统一启动同一固定版本的 SILO。切勿对需要保留的数据卷执行 `docker compose down -v`。
{{< /tab >}}
{{< tab label="Kubernetes" value="kubernetes" >}}
可使用仓库维护的独立 [`helm/silo` Chart（`7.0.4`）](https://github.com/pgsty/silo/tree/RELEASE.2026-11-09T00-00-00Z/helm/silo)直接部署，默认拉取 `pgsty/silo:RELEASE.2026-11-09T00-00-00Z` 与 `pgsty/mc:RELEASE.2026-11-09T00-00-00Z`（执行 `helm upgrade --reuse-values` 时请显式传入 `--set image.tag=RELEASE.2026-11-09T00-00-00Z`）。若使用已归档的 MinIO Operator `v7.1.1`，请遵循 [Tenant Helm 指南](/zh/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/)覆盖租户镜像，并将该 Operator 版本视为冻结的兼容基线。
{{< /tab >}}
{{< /tabs >}}
