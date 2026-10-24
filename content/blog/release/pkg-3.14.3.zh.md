---
title: "silo-pkg 3.14.3 发布"
linkTitle: "silo-pkg 3.14.3"
date: 2026-10-18T07:29:13+08:00
author: "冯若航"
description: "降低策略判定中识别 admin action 的开销，保持授权行为不变。"
tags: [发布, pkg]
weight: 1
url: "/zh/blog/release/pkg-3.14.3/"
---

**发行版：** [v3.14.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.3) · **源码：** [`e9d585ba1e7a`](https://github.com/pgsty/silo-pkg/commit/e9d585ba1e7a30ee5eb85b992d883820b83768f5)。依赖基线见 [v3.14.2 发布说明](/zh/blog/release/pkg-3.14.2/)。

`github.com/pgsty/silo-pkg/v3 v3.14.3` 优化了 IAM 策略判定期间识别 `admin:` 动作的开销，被 [Server 20261018](/zh/blog/release/silo-20261018/) 选用。

`AdminAction.IsValid` 与 `HasResource` 现在优先执行精确查表，再按需扫描动作集合：不含通配符且未命中的字面量动作直接返回；前缀无法匹配 `admin:` 命名空间的通配符模式直接跳过合法性扫描，而 `adm*`、`a*d*m*i*n*` 等通配模式保持原有匹配语义不变。

## 性能与验证 {#validation}

在 Apple M5 Max（Go 1.27.2）上进行的 6 轮交替单核基准测试表明：在先遍历 100 条不匹配桶授权、最后命中目标授权的策略场景下，单次策略判定中位耗时从 **303.2 µs 降至 54.4 µs**（降低约 **82%**），且零新增堆内存分配。

验证覆盖 Go 1.26 与 1.27 race 测试、lint、LDAP 集成测试、漏洞扫描、60 秒等价性模糊测试（fuzzing），以及针对 50,000 份策略、970,020 次策略判定的新旧版本全量结果比对；使用 `mcli 20261018` 连接基于新旧包构建的 Server 结果完全一致。

## 采用方式 {#adoption}

公开 API、策略格式、权限判定结果、外部依赖与 `go 1.26` 最低版本要求均无变化。Server 20261018 采用 `v3.14.3`，而独立发布的 `mcli 20261018` 与 `Console v2.4.2` 继续使用 `v3.14.2`（各组件依赖版本见[组件矩阵](/zh/compatibility/versions/)）。

感谢 [Denis Babchuk（@botdeniska）](https://github.com/botdeniska) 提交 [PR #11](https://github.com/pgsty/silo-pkg/pull/11)，以及 [Klaus Post（@klauspost）](https://github.com/klauspost) 的原始优化工作。

[相对 v3.14.2 的完整变更](https://github.com/pgsty/silo-pkg/compare/v3.14.2...v3.14.3)
