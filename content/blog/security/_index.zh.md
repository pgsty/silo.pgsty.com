---
title: SILO 安全编年史
linkTitle: 安全编年史
description: SILO 分支处理过的应用层 CVE 编年史：按照时间顺序，每个 CVE 独立成篇。
weight: 30
icon: fa-solid fa-shield-halved
sidebar_expanded: true
module: [BLOG]
default_featured_image: /images/blog/security.webp
aliases:
  - /security/
---

这里记录 SILO 社区分支自分叉以来处理过的安全事件。文章严格按照发现与修复时间排列，每个 CVE 独立成篇：最初的威胁模型、复核中的转折、被否决的方案、最终恢复的不变量、验证证据与兼容性代价，都留在它自己的故事里。

## 编年表 {#chronicle}

| 日期         | CVE            | 事件                                                                    | 首个包含版本                          |
|:-----------|:---------------|:----------------------------------------------------------------------|:--------------------------------|
| 2026-04-15 | CVE-2026-32285 | [`jsonparser`：最终无需补丁的安全通告](/zh/blog/security/cve-2026-32285/)         | 当前依赖图原本已经修复                     |
| 2026-04-15 | CVE-2026-33322 | [OIDC JWT 算法混淆](/zh/blog/security/cve-2026-33322/)                    | SILO 2026-04-17                 |
| 2026-04-15 | CVE-2026-33419 | [LDAP STS 用户枚举与限流](/zh/blog/security/cve-2026-33419/)                 | SILO 2026-04-17；2026-06-18 完整闭环 |
| 2026-04-15 | CVE-2026-34204 | [复制元数据注入](/zh/blog/security/cve-2026-34204/)                          | SILO 2026-04-17                 |
| 2026-04-15 | CVE-2026-39414 | [S3 Select 超大记录](/zh/blog/security/cve-2026-39414/)                   | SILO 2026-04-17；2026-06-18 完整闭环 |
| 2026-04-16 | CVE-2026-40344 | [Snowball 自动解包认证绕过](/zh/blog/security/cve-2026-40344/)                | SILO 2026-04-17                 |
| 2026-04-16 | CVE-2026-41145 | [Unsigned-Trailer 查询认证绕过](/zh/blog/security/cve-2026-41145/)          | SILO 2026-04-17                 |
| 2026-06-12 | CVE-2026-42600 | [`ReadMultiple` Storage-REST 路径穿越](/zh/blog/security/cve-2026-42600/) | SILO 2026-06-18                 |

下方文章按时间正序排列；同一天的事件按 CVE 编号排列。只涉及 Go 或依赖升级的 CVE 继续留在对应的[发布注记](/zh/blog/release/)中，不把它们包装成应用层漏洞故事。


----------------
