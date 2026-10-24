---
title: "SN-2026-011：修复与发布状态"
linkTitle: "SN-2026-011：修复与发布状态"
date: 2026-09-13
author: "Vonng"
description: "SN-2026-011 签名头校验修复（123325430），已随 Server 20260916 正式发布。"
tags: [Security, silo]
weight: 1
url: "/zh/blog/security/20260913-signed-header-status/"
---

`SN-2026-011` 于 2026-09-13 在 Server 主分支修复（起始提交 [`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e)），并已随 [Server 20260916](/zh/blog/release/silo-20260916/) 正式发布。Server `RELEASE.2026-09-03T13-18-01Z` 及更早版本均受影响（同期发布的 `silo-pkg v3.14.0` 与 `mcli 20260913` 属于依赖库与客户端版本，不包含服务端二进制修复）。

在未修复版本中，持有合法签名 `PUT` 请求的调用方可以追加未签名的 `x-amz-copy-source` 请求头，将该写入操作转化为复制签名密钥有权读取的其他对象。若目标位置允许匿名读取，被复制对象的私有内容便会对外暴露。预签名 URL 与 `Authorization` 请求头签名均受影响，攻击者无需获知签名密钥本身。

修复方案在分发请求前校验实际收到的 `x-amz-*` 请求头是否均已包含在签名头集合中（仅保留协议规范明确允许的例外项）。后续的签名与校验和边界补强详见[签名头评审笔记](/zh/blog/design/signed-header-coverage/)。

## 修复建议

请将 **SILO Server** 升级至 [Server 20260916](/zh/blog/release/silo-20260916/) 或更高版本。在完成升级前，应将签发上传请求的凭据限制在必要的最小对象前缀范围内，避免为签发公开桶上传链接的凭据授予过宽的读取权限。

感谢 Oren Yomtov 报告此问题。更多详情请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-011)、[9 月 16 日版本加固公告](/zh/blog/security/20260916-release-hardening/)及[组件版本矩阵](/zh/compatibility/versions/)。
