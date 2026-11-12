---
title: "SILO Console 2.7.2：SILO 20261112 联合嵌入与发布元数据同步"
linkTitle: "Console 2.7.2"
date: 2026-11-12T12:00:00+08:00
author: "SILO"
description: "Console 2.7.2 同步内嵌发布元数据、嵌入指南文档与优化后的前端静态资源，作为 SILO Server 20261112 的内嵌控制台及最新独立版正式发布，完整包含 2.7.1 的服务账号策略继承保护、严格 JSON 校验与 HTTPS 重定向修复。"
tags: [Release, Console, SILO]
draft: false
weight: 1
url: "/zh/blog/release/console-2.7.2/"
---

**SILO Console 2.7.2 已正式发布**，接续 [2.7.1](/zh/blog/release/console-2.7.1/)，同时作为独立版 Console 与 **[SILO Server 20261112](/zh/blog/release/silo-20261112/)** 内嵌控制台交付。标签：[`v2.7.2`](https://github.com/pgsty/silo-console/releases/tag/v2.7.2)；源码提交：[`0e7953ff59c4`](https://github.com/pgsty/silo-console/commit/0e7953ff59c4a1eb77c7d203b265e6783ff18d01)。

[GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.7.2) · [SILO 20261112 发布说明](/zh/blog/release/silo-20261112/) · [兼容性注记](/zh/compatibility/console/#release-272) · [下载](/zh/download/#console)

## 联合嵌入与发布元数据同步 {#overview}

- **内嵌版本与静态资源同步（`0e7953ff5`）：** 统一对齐 `web-app/package.json`、`web-app/src/version.tsx`（`2.7.2`）、`CHANGELOG.md`、`README.md`、`README_ZH.md`、`docs/Embedding.md` 与 `docs/README.md`，并基于 Node `24.22.1` 重新构建优化后的内嵌前端静态资源包，使独立版 `silo-console` `v2.7.2` 与 [SILO Server 20261112](/zh/blog/release/silo-20261112/)（`v0.0.0-20261112031746-0e7953ff59c4`）展示完全一致的发布版本元数据。
- **完整包含 2.7.1 策略与 TLS 修复：** 延续 [Console 2.7.1](/zh/blog/release/console-2.7.1/) 的服务账号三态内联策略编辑修复（`SN-2026-025`：修改元数据或状态时保留父账号策略继承、仅在关闭 **Restrict beyond user policy** 时发送显式空策略 `{}` 恢复继承、拦截大小写／Unicode 折叠／重复键空内联策略变体，并在编辑弹窗内直接显示保存报错）、后端 IAM 与桶策略严格 JSON 解码，以及 `--host 0.0.0.0`／`CONSOLE_SECURE_TLS_HOST` 下 HTTP→HTTPS 重定向保留请求主机名修复（`github.com/unrolled/secure v1.18.0`）。
- **工具链与组件锁定：** 基于 **Go `1.27.4`**、[silo-pkg v3.16.1](/zh/blog/release/pkg-3.16.1/)（`433f7eefa714`）与 [mcli 20261112](/zh/blog/release/mcli-20261112/)（`RELEASE.2026-11-12T00-00-00Z`，`v0.0.0-20261111180825-a37a9f054fba`）构建，并经 Go 模块代理、校验和数据库与不可变 GitHub Release 元数据核验。

**升级提示：** 升级至 [SILO Server 20261112](/zh/blog/release/silo-20261112/) 即可将内嵌 Console 同步更新至 `v2.7.2` 并完整启用显式重置内联策略恢复继承（`policy: "{}"`）。独立部署的 Console 可直接升级至 `v2.7.2`；从 `2.7.0` 之前版本升级 `console usage-worker` 时，仍须先停止旧版 worker 进程。

## 验证与交付制品 {#verification}

- [必选验证矩阵](https://github.com/pgsty/silo-console/actions/runs/43147244513) · [必选漏洞扫描](https://github.com/pgsty/silo-console/actions/runs/43147244552) · [标签发版与制品校验](https://github.com/pgsty/silo-console/actions/runs/43152386737) · [latest 镜像晋升](https://github.com/pgsty/silo-console/actions/runs/43153492710)
- 容器镜像：`docker.io/pgsty/silo-console:v2.7.2` 与 `docker.io/pgsty/silo-console:latest`（`linux/amd64`、`linux/arm64`），多架构清单摘要 `sha256:41ea21e782475e230fc19f59da6c96373387da2974c3cffea0bd4eebf604cb47`。
- GitHub Release 提供全部 44 个经核验制品（6 个平台可执行文件与归档、9 个 Linux RPM/DEB/APK 软件包、源码包、SPDX SBOM、法律声明，以及经 Cosign 签名并附带 GitHub 构建溯源证明的 SHA-256 校验清单）。
