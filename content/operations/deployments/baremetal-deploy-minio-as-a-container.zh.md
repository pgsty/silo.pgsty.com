---
title: "以容器方式部署 Silo"
url: "/zh/operations/deployments/baremetal-deploy-minio-as-a-container/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-deploy-minio-as-a-container.rst
upstream_modified: true
---

<a id="minio" data-td-print-local></a>
<a id="deploy-minio-as-a-container"></a>
<a id="deploy-minio-container"></a>

本页说明如何在支持容器化进程的操作系统上以容器方式部署 Silo。

本文档假定已安装 Docker、Podman 或其他支持 OCI 容器镜像格式的类似 runtime。已发布的 `docker.io/pgsty/silo` 提供两种多架构（`linux/amd64`、`linux/arm64`）发行镜像变体：

- **标准镜像（`docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z`）：** 基于 [Red Hat Universal Base Image 9 Micro](https://catalog.redhat.com/software/container-stacks/detail/609560d9e2b160d361d24f98) 构建，内置 `silo`、`mcli`（含 `mc` 符号链接）、静态 `curl`、POSIX 入口脚本，并在 `/licenses/` 下附带 SILO 许可文件、在 `/licenses/mcli` 下附带 `mcli` 许可文件（[#295](https://github.com/pgsty/silo/pull/295)）。
- **Distroless 镜像（`docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`）：** 基于 `gcr.io/distroless/static-debian12` 构建，仅包含 `silo` 二进制与 `/licenses/`（不含 shell、`mcli`、`curl` 或入口脚本）。该镜像携带与标准 UBI 镜像完全一致的 UBI 系统 CA 根证书束（`/etc/ssl/certs/ca-certificates.crt`，[#295](https://github.com/pgsty/silo/pull/295)），并配置内置 `HEALTHCHECK` 执行 `/usr/bin/silo healthcheck ready`（见[健康检查 API](/zh/operations/monitoring/healthcheck-probe/#native-probe)）。标准镜像部署同样可直接调用 `silo healthcheck` 作为容器探针。

Silo 容器的功能和性能可能会受到基础操作系统的限制。

本步骤包含对单机多盘 (SNMD) 和单机单盘 (SNSD) 拓扑的指导，适用于早期开发和评估环境。

> [!WARNING]
> **重要**
>
> 下面的示例仅覆盖用于开发或评估的单机单盘和单机多盘部署；它们不构成 Docker Compose、Docker Swarm 或其他容器编排器上的生产级多机多盘拓扑或升级契约。生产环境的分布式部署应使用经过验证的 [Kubernetes Tenant 流程](/zh/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/)，并针对实际环境验证持久化、网络、故障域与升级。
>
> 示例以 [Server 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）为目标。生产部署还需验证实际负载，并记录镜像摘要以便回滚。
>
> SILO 禁止原地自更新，`MINIO_UPDATE=off` 不会重新启用它。容器升级应替换为经过验证的 SILO 标签或摘要，不应调用 `mc admin update`。

<a id="id2" data-td-print-local></a>

## 注意事项 {#considerations}

<a id="id3" data-td-print-local></a>

### 检查清单 {#review-checklists}

在执行本步骤前，请先阅读我们发布的硬件、软件和安全检查清单。

<a id="id4" data-td-print-local></a>

### 纠删码校验 {#erasure-coding-parity}

SILO 根据**每个纠删集合的盘数**选择默认校验块数量，而非按集群总盘数计算；8–16 盘集合默认 `EC:4`，较小集合使用不同默认值。完整对应关系与可配置范围见[存储类设置](/zh/reference/minio-server/settings/storage-class/)。校验布局按对象保存，可用性须按该对象所在集合和实际布局评估。

校验值决定了对象可用性与磁盘存储占用之间的关系。可使用上游 MinIO [纠删码计算器](https://min.io/product/erasure-code-calculator) 比较校验级别，但应将它视为上游规划工具，而不是 Silo 支持契约。

虽然你可以随时更改纠删码校验设置，但以既有校验值写入的对象 **不会** 自动更新为新的校验设置。

<a id="id5" data-td-print-local></a>

### 容器存储 {#container-storage}

本步骤假定你会将一个或多个专用存储设备挂载到容器中，作为 Silo 的持久化存储。

存储在容器临时路径上的数据会在容器重启或删除时丢失。使用此类路径的风险需自行承担。

<a id="id6" data-td-print-local></a>

## 步骤 {#procedure}

### 1. 启动容器 {#start-the-container}

本步骤提供 Podman 和 Docker 在 rootful 模式下的说明。对于 rootless 部署，请参考各容器 runtime 文档配置用户命名空间与卷权限。在 `-distroless` 镜像中，`ENTRYPOINT` 为 `/usr/bin/silo`，镜像层已预创建权限为 `0777` 的 `/data` 目录，降权运行请使用 `--user` 而非 `MINIO_USERNAME`。

对于其他容器 runtime，请参阅对应文档，并使用等效的选项、参数或配置。

{{< tabs group="podman-docker" >}}
{{< tab label="Podman" value="podman" >}}
以下命令先在主目录中创建本地数据目录，再使用 Podman 启动 Silo 容器：

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

该命令将端口 `9000` 绑定到 S3 API，将端口 `9001` 绑定到 Web Console。若要改用 Distroless 镜像，请将镜像引用替换为 `docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`。

宿主机目录 `~/silo/data` 会挂载到容器内的 `/data` 目录。可按需修改 [`MINIO_ROOT_USER`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) 和 [`MINIO_ROOT_PASSWORD`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) 设置 root 登录凭据。

对于多盘部署，请将宿主机上的每个驱动器或目录挂载到容器内按顺序编号的路径，并在 [`silo server`](/zh/reference/minio-server/#command-minio.server) 启动命令中传入省略号展开范围：

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

测试磁盘级故障隔离时，请将 `~/silo/data-1` 至 `~/silo/data-4` 替换为独立挂载的宿主机磁盘路径（例如 `/mnt/drive-1:/mnt/drive-1`）。在 Windows 宿主机上，请使用 Windows 路径语法指定本地目录，例如 `C:\silo\data:/data`。
{{< /tab >}}
{{< tab label="Docker" value="docker" >}}
以下命令先在主目录中创建本地数据目录，再使用 Docker 启动 Silo 容器：

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

该命令将端口 `9000` 绑定到 S3 API，将端口 `9001` 绑定到 Web Console。若要改用 Distroless 镜像，请将镜像引用替换为 `docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z-distroless`。

宿主机目录 `~/silo/data` 会挂载到容器内的 `/data` 目录。可按需修改 [`MINIO_ROOT_USER`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_USER) 和 [`MINIO_ROOT_PASSWORD`](/zh/reference/minio-server/settings/root-credentials/#envvar.MINIO_ROOT_PASSWORD) 设置 root 登录凭据。

对于多盘部署，请将宿主机上的每个驱动器或目录挂载到容器内按顺序编号的路径，并在 [`silo server`](/zh/reference/minio-server/#command-minio.server) 启动命令中传入省略号展开范围：

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

测试磁盘级故障隔离时，请将 `~/silo/data-1` 至 `~/silo/data-4` 替换为独立挂载的宿主机磁盘路径（例如 `/mnt/drive-1:/mnt/drive-1`）。在 Windows 宿主机上，请使用 Windows 路径语法指定本地目录，例如 `C:\silo\data:/data`。
{{< /tab >}}
{{< /tabs >}}

<a id="id7" data-td-print-local></a>

### 2. 连接到部署 {#connect-to-the-deployment}

{{< tabs group="tab1-cli" >}}
{{< tab label="控制台" value="tab1" >}}
在浏览器中打开 [http://localhost:9001](http://localhost:9001) 以访问 [Silo Console](/zh/administration/minio-console/#minio-console) 登录页。

使用上一步中的 **MINIO_ROOT_USER** 和 **MINIO_ROOT_PASSWORD** 进行登录。

![Silo Console 登录页](/images/silo-console/console-login.webp){width="600"}

你可以使用内嵌 Console 执行常规管理任务，例如身份与访问管理、指标和日志监控，或 Server 配置。
{{< /tab >}}
{{< tab label="CLI" value="cli" >}}
请按照 [Silo 客户端安装说明](/zh/reference/minio-mc/#mc-install) 安装 `mcli`，并运行 `mcli --version` 验证。已发布的独立归档与 Linux 软件包安装 `mcli`；源码构建和客户端容器则保留 `mc` 可执行文件名。

安装完成后，为该 Silo 部署创建一个别名：

```shell
mcli alias set silo http://localhost:9000 USERNAME PASSWORD
```

请根据你的部署修改主机名、用户名和密码。
{{< /tab >}}
{{< /tabs >}}
