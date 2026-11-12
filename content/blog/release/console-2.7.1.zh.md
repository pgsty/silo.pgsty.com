---
title: "SILO Console 2.7.1：服务账号策略继承保护与严格 JSON 校验"
linkTitle: "Console 2.7.1"
date: 2026-11-12T03:00:00+08:00
author: "SILO"
description: "Console 2.7.1 在元数据编辑时保留服务账号策略继承关系，拦截各类空内联策略变体，在编辑弹窗内直接提示保存错误，并升级至 Go 1.27.4、silo-pkg 3.16.1 与 mcli 20261112。"
tags: [Release, Security, Console]
draft: false
weight: 1
url: "/zh/blog/release/console-2.7.1/"
---

**SILO Console 2.7.1 已正式发布**，接续 [2.7.0](/zh/blog/release/console-2.7.0/)。标签：[`v2.7.1`](https://github.com/pgsty/silo-console/releases/tag/v2.7.1)；源码提交：[`3825ebc44451`](https://github.com/pgsty/silo-console/commit/3825ebc44451fdc8eefda3d4ec523a79dfecb236)。这是独立 Console 发布；在下一版 Server 正式发布前，已公开的 [SILO Server 20261109](/zh/blog/release/silo-20261109/) 仍内嵌 Console 2.7.0。

[GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.7.1) · [兼容性注记](/zh/compatibility/console/#release-271) · [SN-2026-025 安全编年史](/zh/blog/security/20261111-iam-import-status-and-console-policy/) · [下载](/zh/download/#console)

## 服务账号策略继承保护（`SN-2026-025`） {#policy-inheritance}

- **分离跟踪继承策略与内联策略（`1be8a74bf`）：** 此前服务账号编辑界面会填入父账号的有效策略，并在修改元数据或状态时将该文本一并回传（`silo-console#89`），导致仅修改名称、备注、过期时间或启用状态也会将继承关系固化为静态内联策略；当父账号策略超过 4 KiB 内联会话策略上限时，连紧急禁用访问密钥的操作也会被服务端拒绝。Console 2.7.1 显式区分继承与内联策略，在未切换限制开关且未改动内联文档时省略 `policy` 字段。
- **显式恢复策略继承：** 关闭 **Restrict beyond user policy** 开关会发送显式空策略（`{}`），配合包含[`20261109` 之后候选修复](/zh/compatibility/server/#candidate-after-20261109)的 SILO Server 即可清除已有内联限制并恢复继承。
- **空内联策略拦截与弹窗内错误反馈（`a1a84cab4`、`1fdb279fd`、`3825ebc44`）：** 开启 **Restrict beyond user policy** 创建或替换策略时，前端与后端同步拦截空编辑器、`{}`、`{"Statement":[]}`、`{"Statement":null}` 以及后端可识别的大小写、Unicode 折叠或重复键空文档变体；未修改历史空内联策略的账号仍可正常保存纯元数据改动。保存失败信息现在直接在编辑弹窗内展示。

## 严格策略 JSON 校验、HTTPS 重定向修复与依赖升级 {#dependencies}

- **后端严格 JSON 校验（`3825ebc44`）：** Console 策略校验接口对齐 [silo-pkg v3.16.1](/zh/blog/release/pkg-3.16.1/)，拒绝未知 JSON 字段、尾部多余 token、非对象载荷、空 `Principal: {}` / 未实现的 `NotPrincipal` 以及空命名策略。
- **HTTPS 重定向主机名保留（`3825ebc44`）：** 启用 TLS 重定向（`CONSOLE_SECURE_TLS_REDIRECT=on`）且未配置 `CONSOLE_SECURE_TLS_HOST` 时，HTTP 至 HTTPS 浏览器跳转保留请求 `Host` 与配置的 TLS 端口（不再将 `--host 0.0.0.0` 或 `[::]` 通配监听跳转至 `https://0.0.0.0:<tls-port>`）；显式配置 `CONSOLE_SECURE_TLS_HOST` 时优先于 `X-Forwarded-Host`，并升级至 `github.com/unrolled/secure v1.18.0`。
- **工具链与组件锁定：** 基于 **Go `1.27.4`**、`github.com/pgsty/silo-pkg/v3 v3.16.1` 与 `pgsty/mc RELEASE.2026-11-12T00-00-00Z`（[mcli 20261112](/zh/blog/release/mcli-20261112/)，`v0.0.0-20261111180825-a37a9f054fba`）构建，并经 Go 模块代理、校验和数据库与不可变 GitHub Release 元数据核验。

**升级提示：** 独立部署 Console `v2.7.1` 可立即避免纯元数据编辑破坏策略继承；显式重置内联策略恢复继承（`policy: "{}"`）需配合 `20261109` 之后的 SILO Server 更新生效。从 `2.7.0` 之前版本升级 `console usage-worker` 时，仍须先停止旧版 worker 进程。

## 验证与交付制品 {#verification}

- [必选验证矩阵](https://github.com/pgsty/silo-console/actions/runs/43076284524) · [必选漏洞扫描](https://github.com/pgsty/silo-console/actions/runs/43076283437) · [标签发版与制品校验](https://github.com/pgsty/silo-console/actions/runs/43083874312) · [latest 镜像晋升](https://github.com/pgsty/silo-console/actions/runs/43085474259)
- 容器镜像：`docker.io/pgsty/silo-console:v2.7.1` 与 `docker.io/pgsty/silo-console:latest`（`linux/amd64`、`linux/arm64`），多架构清单摘要 `sha256:2afef06f8505eadb24d657acd0f68c78bce8b148b1d9b74981454560fa3b055f`。
- GitHub Release 提供全部 44 个经核验制品（6 个平台可执行文件与归档、9 个 Linux RPM/DEB/APK 软件包、源码包、SPDX SBOM、法律声明，以及经 Cosign 签名并附带 GitHub 构建溯源证明的 SHA-256 校验清单）。
