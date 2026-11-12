---
title: 发布注记
linkTitle: 发布注记
description: SILO 正式发布日志与历史版本记录。
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

发布日志记录各版本的功能演进、安全修复、依赖更新、兼容性要求与交付制品。

当前的 **[20261112 联合发布](/zh/blog/release/silo-20261112/)** 基于 Go 1.27.4 交付 SILO Server 20261112，配套内嵌及独立版 **[Console 2.7.2](/zh/blog/release/console-2.7.2/)**（接续 **[2.7.1](/zh/blog/release/console-2.7.1/)**）、**[mcli 20261112](/zh/blog/release/mcli-20261112/)** 与 **[silo-pkg 3.16.1](/zh/blog/release/pkg-3.16.1/)**，涵盖 `SN-2026-020` 至 `SN-2026-025` 安全加固、服务账号三态内联策略保护、严格策略 JSON 校验、Object Lock `null` 版本与副本保护，以及多存储池和压缩加密对象区间读取修复。

此前的 **[20261109 联合发布](/zh/blog/release/silo-20261109/)** 交付 SILO Server 20261109 与 **[Console 2.7.0](/zh/blog/release/console-2.7.0/)**、**[mcli 20261109](/zh/blog/release/mcli-20261109/)**、**[silo-pkg 3.16.0](/zh/blog/release/pkg-3.16.0/)**；**[20261026 联合发布](/zh/blog/release/silo-20261026/)** 汇总了 SILO Server、mcli 与可选外部 **KES 20261026** 自 20261018 以来的更新，配套 **[Console 2.5.1](/zh/blog/release/console-2.5.1/)** 与 **[silo-pkg 3.15.2](/zh/blog/release/pkg-3.15.2/)**（10 月 24—25 日的阶段性维护记录已并入正式发布日志并自动重定向）。
