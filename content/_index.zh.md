---
title: "SILO：Pigsty 持续维护的 S3 兼容对象存储"
description: "由 Pigsty 持续维护的 S3 兼容对象存储，提供安全更新、版本化发行、完整控制台与现有部署的运维连续性。"
url: "/zh/"
weight: 1
type: home
cascade:
  type: docs
minio_origin: true
silo_modified: true
---

{{% alert color="warning" %}}
**重要提醒**：SILO 是由 PIGSTY 社区维护的 MinIO 分支，
本项目 **并非** MinIO, Inc. 的关联项目，也未获得其认可、赞助与背书。 “MinIO” 是 MinIO, Inc. 的商标，此处仅用于标识上游项目。
本文档仓库地址为 [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com)，
文档内容分叉自上游 MinIO 文档项目 [`minio/docs`](https://github.com/minio/docs)。

{{% /alert %}}

- [在 Docker 上安装和运行 MinIO：概览](https://youtu.be/mg9NRR6Js1s?ref=docs)
- [在 Docker 上安装和运行 MinIO：安装实验](https://youtu.be/Z0FtabDUPtU?ref=docs)
- [对象存储基础](https://www.youtube.com/playlist?list=PLFOIsHSSYIK3WitnqhqfpeZ6fRFKHxIr7)
- [如何使用 JavaScript 连接到 MinIO](https://www.youtube.com/watch?v=yUR4Fvx0D3E&list=PLFOIsHSSYIK3Dd3Y_x7itJT1NUKT5SxDh&index=5)

Silo 是由 Pigsty 社区持续维护的 S3 兼容对象存储，为需要开放发布与安全维护路径的现有部署提供连续性。本站记录 Silo 的运维、管理、开发、下载、发布边界与兼容契约。

## 快速开始 {#id2}

{{< tabpane text=true persist=header >}}
{{% tab header="沙盒" %}}
MinIO 在 [https://play.min.io](https://play.min.io) 维护了一个社区服务器沙盒实例。 你可以在本地系统上使用该实例进行实验或评估 MinIO。

按照 [`mc`](/zh/reference/minio-mc/#command-mc) CLI 的 [安装指南](/zh/reference/minio-mc/#mc-install) 在本地主机上安装该工具。

[`mc`](/zh/reference/minio-mc/#command-mc) 内置了一个预配置的 `play` 别名，用于连接该沙盒实例。 例如，你可以使用以下命令创建存储桶并将对象复制到 `play`：

```shell
mc mb play/mynewbucket

mc cp /path/to/file play/mynewbucket/prefix/filename.extension

mc stat play/mynewbucket/prefix/filename.extension
```

{{% alert color="warning" %}}
**重要提醒**：MinIO Play 沙盒是一个临时性的公开部署，其访问凭证是众所周知的。 上传到 Play 的任何私有、机密、内部、受保护或其他重要数据，实际上都会变成公开数据。 请谨慎判断并自行承担上传到 Play 的数据风险。
{{% /alert %}}
{{% /tab %}}
{{% tab header="裸金属" %}}
1. 下载适用于你的操作系统的 Silo 服务端

   从[下载与安装](/zh/download/#server)选择已经公开发布的 Silo 软件包或归档，并校验摘要。可执行文件刻意保留 [`minio server`](/zh/reference/minio-server/#command-minio.server) 命令契约。
2. 创建对象数据目录

   例如，在 Linux/MacOS 上创建 `~/minio` 文件夹，或在 Windows 上创建 `C:\minio`。
3. 启动 MinIO Server

   运行 [`minio server`](/zh/reference/minio-server/#command-minio.server)，指定目录路径以及 [`--console-address`](/zh/reference/minio-server/#minio.server.-console-address) 参数，以设置静态的 Console 监听地址：

   ```shell
   minio server ~/minio --console-address :9001
   # Windows 请使用 minio.exe server ~/minio --console-address :9001
   ```

   输出中会包含 [`mc`](/zh/reference/minio-mc/#command-mc) 的连接说明，以及如何通过浏览器连接到 Console 的说明。
{{% /tab %}}
{{% tab header="Kubernetes" %}}
使用 [`pgsty/minio`](https://hub.docker.com/r/pgsty/minio) 镜像，并遵循 [Silo Tenant 部署指南](/zh/operations/deployments/k8s-deploy-minio-tenant-helm-on-kubernetes/)。生产环境应固定经过测试的发布标签或摘要，不要把 `latest` 当作版本契约。
{{% /tab %}}
{{< /tabpane >}}
