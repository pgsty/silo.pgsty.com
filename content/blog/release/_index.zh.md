---
title: 发布注记
linkTitle: 发布注记
description: SILO 各个正式版本的详细发布说明，按时间从新到旧排列。
weight: 20
icon: fa-solid fa-tag
sidebar_expanded: true
module: [BLOG]
# 发布注记的用途是快速扫读，索引页整个渲染成一张表：日期、标题、标签，
# 不分页。参见 params.ui.blog_index。
blog_index: table
cascade:
  images: [/images/blog/silo-release.webp]
aliases:
  - /releases/
---

每个 SILO 正式版本均有独立页面，记录发布日期、主要变更、安全修复、依赖更新与相关提交。

[20261025](/zh/blog/release/silo-20261025/) 是 SILO、mcli、SILO Console、silo-pkg 与 KES 共用的 Go 与依赖维护公告。silo-pkg v3.15.1 已发布；[mcli 20261025](/zh/blog/release/mcli-20261025/) 正在准备发布；其余组件尚待各自完成发布。
