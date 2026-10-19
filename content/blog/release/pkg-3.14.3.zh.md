---
title: "silo-pkg 3.14.3 发布"
linkTitle: "silo-pkg 3.14.3"
date: 2026-10-18T07:29:13+08:00
author: "冯若航"
description: "降低策略判定开销，保持授权行为不变。"
tags: [发布, pkg]
weight: 1
url: "/zh/blog/release/pkg-3.14.3/"
---

**源码：**[`e9d585ba1e7a`](https://github.com/pgsty/silo-pkg/commit/e9d585ba1e7a30ee5eb85b992d883820b83768f5)。依赖基线见 [v3.14.2 发布说明](/zh/blog/release/pkg-3.14.2/)。

[silo-pkg v3.14.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.3)
降低了策略判定中识别 admin action 的开销。这是
`github.com/pgsty/silo-pkg/v3` 的纯源码模块发布。

`AdminAction.IsValid` 和 `HasResource` 现在优先精确查表，再按需扫描 action 集合。
不含通配符且未命中的 action 直接返回；无法匹配 `admin:` 命名空间的通配符模式
跳过合法性扫描。`adm*`、`a*d*m*i*n*` 等模式保持原有语义。

## 性能与验证 {#validation}

在 Apple M5 Max、Go 1.27.2 上进行六轮交替单 CPU 基准测试：遍历 100 条不匹配桶的授权，
最后命中一条授权的场景，单次判定耗时中位数从 **303.2 微秒降至 54.4 微秒**，
减少约 **82%**，没有新增内存分配。这是策略判定耗时，不代表端到端 S3 吞吐量。

验证包括 Go 1.26、1.27 race 测试、lint、LDAP 集成、漏洞扫描、60 秒等价性模糊测试，
以及对 50,000 份策略、970,020 次策略判定进行的新旧版本独立对照。已发布的 mcli
分别连接使用旧包和新包构建的 server，结果一致。

## 采用方式 {#adoption}

公开 API、策略格式、权限判定结果、依赖和 Go 1.26 最低要求均未改变。
应用需要升级依赖并重新构建，才能采用这项优化。Server 可以使用 v3.14.3，
已发布的 mcli 20261018 和独立 Console v2.4.2 继续使用 v3.14.2；本补丁不要求组件同步发版。

发布这个模块不会更新现有 Server 草稿或已安装的二进制。各组件实际选择的依赖见
[组件版本表](/zh/compatibility/versions/)。

感谢 [Denis Babchuk（@botdeniska）](https://github.com/botdeniska) 提交
[PR #11](https://github.com/pgsty/silo-pkg/pull/11)，以及
[Klaus Post（@klauspost）](https://github.com/klauspost) 的原始工作。

[相对 v3.14.2 的完整变更](https://github.com/pgsty/silo-pkg/compare/v3.14.2...v3.14.3)
