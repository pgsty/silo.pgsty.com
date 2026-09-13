---
title: "组件版本"
linkTitle: "组件版本"
description: "SILO 已发布组件、9 月 13 日主分支依赖关系与协调升级顺序。"
url: "/zh/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

**核对日期：2026-09-13。** SILO 的四个组件独立发布。依赖更新合入主分支，不会改变已经发布的二进制或镜像。

## 已发布组件 {#published}

| 组件 | 发行版本 | 实际包含内容 |
| --- | --- | --- |
| Server | <a href="https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z" style="white-space:nowrap">20260903</a> | pkg v3.13.2；上游 SDK `0e78d3f18efe`；mcli 20260903；内嵌 Console 源码 `464a59d73ada`，版本标识为 v2.3.0 |
| <span style="white-space:nowrap">独立<br>Console</span> | [v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) | pkg v3.13.3；MC 源码 `c8aa5d25a63a`；上游 SDK `0e78d3f18efe`；对象浏览器分页 |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-13T00-00-00Z" style="white-space:nowrap">20260913</a> | pkg v3.14.0；上游 SDK `60bd07042d49`；软件包版本 `20260913000000.0.0` |
| 共享 pkg | [v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) | 独立模块路径 `github.com/pgsty/silo-pkg/v3`；密码能力拆分；上游 SDK `60bd07042d49` |

发布说明：[Server 20260903](/zh/blog/release/silo-20260903/)、
[Console v2.4.0](/zh/blog/release/console-2.4.0/)、
[mcli 20260913](/zh/blog/release/mcli-20260913/)、[pkg v3.14.0](/zh/blog/release/pkg-3.14.0/)。
已发布的 Server 镜像仍捆绑原来的客户端与 Console。安装独立组件的新版本不会替换 Server 内嵌的组件。
软件包仓库镜像可能晚于 GitHub 更新；[下载页](/zh/download/)直接链接已发布的制品。

## 主分支协调后的源码 {#source}

9 月 13 日更新通过 [pkg #7](https://github.com/pgsty/silo-pkg/pull/7)、
[MC #42](https://github.com/pgsty/mc/pull/42)、
[Console #53](https://github.com/pgsty/silo-console/pull/53) 与 [#54](https://github.com/pgsty/silo-console/pull/54)、
[Server #181](https://github.com/pgsty/silo/pull/181) 合入。

- **pkg：** `v3.14.0` → `827f8109ff11bf6239a35d8d6d137cb5738539c3`。
- **MC：** `v0.0.0-20260913012246-4f609a4da3bb` → 已发布的 20260913 标签。
- **Server 选择的 Console：** `v0.0.0-20260913015128-417559bb2c97`；经 `449c185a8d14` 合入 main，源码树相同。
- **Server 集成提交：** `5d955b5b7444f8a3ab550ce92713607998f89c0d`。
- **上游 minio-go：** `v7.3.1-0.20260910142817-60bd07042d49`。

**Server 与 Console 最新标签之后的改动尚未发布。** 其中包括[密码权限拆分](/zh/compatibility/password-permissions/)、
Console 流式 ZIP 下载与新版镜像发布门槛，以及 Server 后续的存储、复制和签名头修复。
Server 主分支现在构建 curl 8.22.0、捆绑 mcli 20260913；现有 Server 镜像保留发布时的内容。
[Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md) 与
[Console changelog](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md) 将这些改动列为 Unreleased。

最新已发布的 Server 受 [SN-2026-011](/zh/blog/security/20260913-signed-header-status/) 影响。
修复已在 main；只升级 pkg、mcli 或独立 Console 无法修补已安装的 Server。
源码验证和漏洞扫描通过，不代表修复版 Server 二进制已经发布。

## 依赖与发布顺序 {#order}

1. 核验上游 SDK 提交与需要的修复，继续使用 `github.com/minio/minio-go/v7`；退役的 `silo-go` 不再属于维护依赖图。
2. 验证并以 `github.com/pgsty/silo-pkg/v3` 发布 pkg，同时提供迁移说明；通过 Go proxy 与校验和数据库解析标签。
3. MC 更新到该 pkg/SDK，验证后发布日历标签的 mcli。Go 消费者引用其规范伪版本。
4. Console 更新直接 pkg 依赖与 MC replacement，验证嵌入前端和集成；需要正式发布时单独发布 Console，也可明确选择已合入的不可变源码提交。
5. Server 更新直接 pkg/SDK 依赖、两个 PGSTY replacement、客户端归档哈希、镜像和 Helm 客户端版本。验证完整依赖图后，再分别完成 Server 发布、镜像发布与集群升级。

Go 不继承依赖模块的 `replace`。即使 Console 已选择 MC，Server 仍必须显式选择受维护的 Console 与 MC。
Console 和 MC 保留历史 MinIO 模块路径，pkg 直接使用自己的路径。
`colorjson`/`dperf` 带入的旧 `minio/pkg/v3` 传递依赖与维护中的策略实现相互独立。

主分支栈使用 Go **1.27.1**；pkg 保留 Go **1.26** 库兼容下限，并通过 Go **1.26.8** race 测试。
Go x/* 依赖已刷新。go-systemd 实际仍选 **v22.6.0**，因为 v22.7.0 在 NetBSD 编译失败；
Console 保留 tablewriter **v0.0.5** replacement 以兼容所用 MC API。这些是有原因的兼容性固定版本。

其他依赖按具体 CVE/BUG 更新，不机械追逐新主版本。
9 月 13 日 Go 扫描没有发现可达或已导入的易受攻击包，但未使用的 OpenPGP 代码仍有模块级 **GO-2026-5932** 告警。
可达性扫描通过，不等于整个依赖图没有任何漏洞通告。

正式支持的集成对象是协调后的 PGSTY 栈；与原版上游 MinIO/MC 和其他 S3 实现的兼容属于尽力保留。
