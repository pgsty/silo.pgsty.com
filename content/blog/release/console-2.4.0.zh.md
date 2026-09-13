---
title: "SILO Console 2.4.0 发布"
linkTitle: "SILO Console 2.4.0 发布"
date: 2026-09-08T22:51:37+08:00
author: "Vonng"
description: "对象浏览器有界分页，以及 v2.3.0 以来积累的正确性修复。"
tags: [Release, console]
weight: 1
url: "/zh/blog/release/console-2.4.0/"
---

[v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) 于 2026-09-08 发布，
源码为 [`c103d08e`](https://github.com/pgsty/silo-console/commit/c103d08ec36aab8e08ba091d77b639158ce9f18f)。
截至 2026-09-13，它仍是独立 Console 最新发行版。

## 已发布行为 {#changes}

- 对象目录默认每页 100 条，可选 50、100、250、500、1000。每页只发一次 S3 continuation-token 请求；排序、筛选和选择作用于当前页，不扫描整个目录，没有无限制的“全部”模式。
- 版本删除绑定选定对象，目录删除限制在其前缀内。生命周期编辑保留独立动作和界面未暴露的字段，复制规则删除统一保存。
- 暂时网络故障不清空会话；处理空版本控制状态、损坏的侧栏偏好与过时的下拉选择。
- Server 显式启用嵌入信任策略时恢复 Console loopback 代理行为，独立部署信任默认值不变。最新 Server 20260903 仍需自己的后续代理/WebSocket 修复。
- 依赖 pkg **v3.13.3**、MC 源码 **`v0.0.0-20260908140805-c8aa5d25a63a`** 与上游 SDK **`0e78d3f18efe`**。本版只引用 MC 源码，本身没有发布新的 mcli 标签。

修复后的 Deny/NotResource 语句保留行为可能拒绝曾因去重缺陷而成功的请求。
已经丢失的语句需要从原始策略恢复。嵌入方必须复制[标签对应 README](https://github.com/pgsty/silo-console/blob/v2.4.0/README.md) 的 MC replacement。

## 仍未发布的变化 {#unreleased}

Console 主分支已选择 pkg **v3.14.0**、mcli **20260913**、SDK **`60bd07042d49`**，
并包含密码权限拆分、流式 ZIP、浏览器恢复/文本改进及更严格的发布晋级门槛。
**这些不属于 v2.4.0。** v2.4.0 的多对象 ZIP 仍在浏览器内存中缓冲，大文件传输应使用 mcli。

Server 主分支选择了更新的 Console 源码；已发布 Server 20260903 仍内嵌 `464a59d73ada`，版本标识为 v2.3.0。
见[组件版本矩阵](/zh/compatibility/versions/)与[密码权限迁移](/zh/compatibility/password-permissions/)。

v2.4.0 精确发布源码通过完整 Console CI。历史依据见
[标签 changelog](https://github.com/pgsty/silo-console/blob/v2.4.0/CHANGELOG.md)、
[对象浏览器指南](https://github.com/pgsty/silo-console/blob/v2.4.0/docs/ObjectBrowser.md)与
[发布附件](https://github.com/pgsty/silo-console/releases/tag/v2.4.0)。后续新增的签名/溯源门槛不会追溯应用到旧制品。
