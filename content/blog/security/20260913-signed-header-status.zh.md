---
title: "SN-2026-011：修复与发布状态"
linkTitle: "SN-2026-011：修复与发布状态"
date: 2026-09-13
author: "Vonng"
description: "签名头修复已合入 Server；最新公开 Server 仍受影响。"
tags: [Security, silo]
weight: 1
url: "/zh/blog/security/20260913-signed-header-status/"
---

**截至 2026-09-13：** SN-2026-011 已在 Server 主分支修复，起始提交为
[`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e)。
最新公开 Server `RELEASE.2026-09-03T13-18-01Z` 及此前公开版本仍受影响。
pkg v3.14.0、mcli 20260913 发布不代表已经发布修复版 Server。

持有签名 PUT 请求的一方可以添加未签名的 `x-amz-copy-source`，将获准写入变成对签名密钥有权读取的其他对象的复制。
如果目标允许匿名读取，被复制的私有内容可能因此泄露。预签名和 Authorization 头请求均受影响，持有者不需要知道签名凭据。

修复在执行请求前检查实际收到的 `x-amz-*` 是否属于签名头集合，仅保留协议明确允许的例外。
后续签名、校验和回归覆盖见[签名头评审](/zh/blog/design/signed-header-coverage/)。

管理员需要更新 **Server** 至包含修复的源码，或未来明确包含该修复的发行版。
安排更新期间，应把写入签名凭据限制到必要对象，避免不必要的读取授权与可匿名读取的上传目标。
只升级客户端或 Console 不会消除 Server 缺陷。

问题由 Oren Yomtov 报告。[权威安全台账](https://github.com/pgsty/silo/blob/main/docs/security/advisories.md)
记录 SN-2026-011 与修复提交，并记载已申请 CVE。不能用依赖扫描的可达性通过结果替代此应用层漏洞状态。
[组件版本矩阵](/zh/compatibility/versions/)区分已发布与 main 源码，
[Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md)列出待发布内容。
