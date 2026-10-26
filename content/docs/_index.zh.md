---
title: "PGSTY SILO 文档"
linkTitle: "文档"
description: "SILO 20261025 源码变化与正式版文档"
url: "/zh/docs/"
weight: 1
type: docs
icon: fa-solid fa-book
upstream_link: ""
upstream_modified: true
sidebar_expanded: true
---

**本手册已同步 [SILO Server 20261025 的源码变更](/zh/compatibility/server/#maintenance-20261025)（截至 2026-10-26 为 Draft Release，当前公开下载版本仍为 [Server 20261018](/zh/blog/release/silo-20261018/)）。** 安装示例采用已发布的正式版制品，涉及 20261025 的章节均明确标注其版本要求。

Server 20261025 源码基于 Go 1.27.3 构建，集成 Console v2.5.0、mcli 20261025、pkg v3.15.1 与上游 `minio-go` 提交 `ab93db7ba435`；已发布的 Server 20261018 则内嵌 Console v2.4.2，选用 mcli 20261018、pkg v3.14.3 与 `minio-go` v7.4.1（单独更新独立 Console 或 mcli 不会替换旧版 Server 的内嵌组件或服务端逻辑）。升级前请查阅[组件版本矩阵](/zh/compatibility/versions/)、[20261025 升级说明](/zh/blog/release/silo-20261025/#server-20261025)与 [20261018 升级要求](/zh/blog/release/silo-20261018/#upgrade)。

{{< home-docs >}}
