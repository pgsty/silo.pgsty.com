---
title: "安装 Silo Server"
url: "/zh/operations/deployments/baremetal-deploy-minio-server/"
weight: 10
icon: fa-solid fa-hard-drive
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-deploy-minio-server.rst
upstream_modified: true
---

<a id="minio-server"></a>
<a id="install-the-minio-server"></a>
<a id="deploy-minio-standalone"></a>

请使用当前的 [服务端制品](/zh/download/#server) 与本节的平台说明，在物理机或虚拟化主机上安装 Silo。SILO 的服务端可执行文件（`silo`）、Linux 软件包（`silo`）、`systemd` 服务单元（`silo.service`）和容器镜像（`docker.io/pgsty/silo`）统一采用 `silo` 名称；`MINIO_*` 环境变量、`/etc/default/silo` 不存在时的 `/etc/default/minio` 兼容回退、S3 与 Admin 线协议 API 以及磁盘纠删码格式则保留 MinIO 兼容名称。
