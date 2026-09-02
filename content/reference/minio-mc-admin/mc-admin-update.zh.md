---
title: "mc admin update"
url: "/zh/reference/minio-mc-admin/mc-admin-update/"
weight: 180
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-update.rst
upstream_modified: true
---

<a id="mc-admin-update"></a>

<a id="command-mc.admin.update"></a>

## 描述 {#id2}

[`mc admin update`](#command-mc.admin.update) 命令会调用 MinIO 兼容的服务端原地更新 API。客户端可传入可选的发布镜像 URL，由服务端把选定的二进制分发到所有节点。

运行该命令后，会显示确认更新的提示。 输入 `y` 并按 `[ENTER]`，即可确认并继续更新。

用户 **必须** 对二进制安装目标位置具有 `write` 权限。

> [!CAUTION]
> **不要在 Silo 上使用默认更新路径**
>
> 自 `RELEASE.2026-08-06T00-00-00Z` 起，Silo 服务端禁用了原地更新器：`mc admin update ALIAS` 无法替换二进制，也不再访问上游 `dl.min.io` 发布源。仍在 `RELEASE.2026-08-04T00-00-00Z` 或更早版本的服务端在省略 `MIRROR_URL` 时会解析到该发布源并保留上游 MinIO 签名密钥，对其运行 `mc admin update` 可能把 Silo 替换成上游 MinIO 二进制。请通过软件包、镜像或编排器滚动发布新版本。