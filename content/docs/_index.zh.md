---
title: "PGSTY SILO 文档"
linkTitle: "文档"
description: "pgsty/silo 20261018 文档手册"
url: "/zh/docs/"
weight: 1
type: docs
icon: fa-solid fa-book
upstream_link: ""
sidebar_expanded: true
---

**本手册以 [SILO Server 20261018](/zh/blog/release/silo-20261018/) 为目标版本，现已正式发布。** 重点变化包括 Object Lock 与 IAM 授权修复、普通 LIST 恢复、分片清理和 strict 分片列表退役。当前正式 Server 为 20261018。

Server 20261018 嵌入 Console v2.4.2，选用 mcli 20261018、pkg v3.14.3 和 minio-go v7.4.1。较新的独立 [Console v2.5.0](/zh/blog/release/silo-20261025/#console-250) 与 [mcli 20261025](/zh/blog/release/mcli-20261025/) 使用 Go 1.27.3 和 pkg v3.15.1；安装它们不会更新 Server。开始升级前，阅读[组件矩阵](/zh/compatibility/versions/)、[本版升级要求](/zh/blog/release/silo-20261018/#upgrade)和[安全更新](/zh/blog/security/20261018-release-hardening/)。

{{< home-docs >}}
