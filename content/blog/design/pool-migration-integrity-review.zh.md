---
title: "存储池迁移完整性审查：#261、#263 与 #265"
linkTitle: "存储池迁移完整性审查"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO 维护团队"
summary: >
  对三个存储池迁移问题的维护者审查：混合纠删码布局、tier free version，以及生命周期过期顺序。本文记录根因、最小安全修复、验证证据与合并顺序。
tags: [设计, 存储池, 生命周期, 兼容性]
weight: 10
draft: false
url: "/zh/blog/design/pool-migration-integrity-review/"
---

本文审查 [#261](https://github.com/pgsty/silo/issues/261)、[#263](https://github.com/pgsty/silo/issues/263)、[#265](https://github.com/pgsty/silo/issues/265) 及其对应的修复 [#262](https://github.com/pgsty/silo/pull/262)、[#264](https://github.com/pgsty/silo/pull/264)、[#266](https://github.com/pgsty/silo/pull/266)，并记录维护者后续修复 [#276](https://github.com/pgsty/silo/pull/276)。这是设计与审查记录，不是发布说明。本文已更新到 2026-11-02 的 #276 合入后 main。#264、#266、#276 已合入，#262 已被取代并关闭。

## 先看结论 {#decision}

| 问题 | 是否成立 | 对应 PR 的判断 | 建议处理 |
| --- | --- | --- | --- |
| [#261](https://github.com/pgsty/silo/issues/261) | 成立。可读的混合 EC 对象可能从迁移列表消失，旧池删除后丢失。 | 窄范围修复已通过维护者 PR [#267](https://github.com/pgsty/silo/pull/267) 合入；[#262](https://github.com/pgsty/silo/pull/262) 已被取代。 | 已由 #267 合入，issue 已完成关闭。 |
| [#263](https://github.com/pgsty/silo/issues/263) | 成立。内部 tier 清理记录被生命周期、列表和迁移路径当成真实版本。 | [#264](https://github.com/pgsty/silo/pull/264) 处理了完整边界，同时保留 healing 所需的可见性。 | 已合入，issue 已完成关闭。 |
| [#265](https://github.com/pgsty/silo/issues/265) | 成立。ILM 与迁移对“版本是否还存在、谁负责删除”的判断不一致。 | [#266](https://github.com/pgsty/silo/pull/266) 修复了贡献者报告的本地顺序问题；维护者后续 PR [#276](https://github.com/pgsty/silo/pull/276) 补齐复制、tier 清理、生命周期代数和整对象完成合同。 | 为承认贡献先合入 #266，再立即合入维护者的完整性修复 #276。 |
{.wide .expand}

实际顺序是：先合入 mixed-EC 修复，再合并 #264，合并 #266 以保留贡献，然后立即合入 #276。前三步和维护者后续修复现在都已进入 main；#276 补齐了原始 PR 无法单独安全承担的外部清理合同。

## 验证了什么 {#evidence}

三个问题都能在修复前的 main 上用聚焦测试和 issue 中提供的原生服务端场景复现。#264 与 #267 合入后先完成了基础验证；#266 与 #276 合入后的代码又通过了迁移与复制聚焦测试、`go vet ./cmd`、`make build`、仓库 CI 的 lint 与生成文件检查，以及完整的 `go test ./cmd -count=1`。本文更新后会再次运行伴生站检查。

关键的行为证据是：

- 在 main 上，#261 的混合 EC 迁移测试返回空结果，但 latest-only GET 与 ListObjectsV2 已经能找到可读对象；加上 #262 后同一组测试通过。
- 在 main 上，#263 测试显示 free entry 被列为最新删除标记、让可读对象从 ListObjectsV2 消失、让生命周期选择错误版本，并在 decommission 时被搬成普通删除标记；完整 #264 测试在 main 失败，在 PR 上通过。
- 在 main 上，#265 测试会把当前版本留在源池，或留下已经搬走版本的重复副本；延迟 expiry queue 的 decommission/rebalance 测试在 #266 上通过。

这些证据足以证明问题和本地迁移修复成立。但它们还不能证明 #266 的直接源端 purge 保留了桶复制语义、远端 tier 清理语义、生命周期配置变化语义，或为整对象过期提供了安全的完成栅栏，这些都是单独的验收条件。

## 三个问题为什么会同时出现 {#common-pattern}

三者都违反了同一条规则：存储池 worker 必须使用与 GET 相同的逻辑对象视图，并且在确认安全目的地或明确删除之前，必须保留对象。

问题被隐藏，是因为不同 worker 对同一份 xl.meta 使用了不同投影：

1. latest-only 读取可以跨混合 EC 布局选择可读多数，但 all-versions 遍历仍走更严格的旧路径。
2. GET 已经跳过 tier free version，但列表、生命周期和迁移代码仍然看见它。
3. ILM 知道某些 action 最终会删除数据，decommission/rebalance 却把“已经排队的删除”当成了“已经完成的删除”。

因此正确的修复是补齐这些边界，而不是重写整个存储池迁移或新增元数据格式。

## 受影响的发布范围与公告 {#advisory}

这三个问题应按存储完整性公告处理。最新已发布 tag [RELEASE.2026-10-26](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-10-26T00-00-00Z) 早于这些修复；修复现在已经通过 [#264](https://github.com/pgsty/silo/pull/264)、[#267](https://github.com/pgsty/silo/pull/267)、[#266](https://github.com/pgsty/silo/pull/266) 和 [#276](https://github.com/pgsty/silo/pull/276) 进入 main，用户需要升级到包含适用修复的版本。

两类问题的代码窗口不同：

- free version 的列表和迁移行为来自 2024-06-07 的上游提交 [29a25a538](https://github.com/pgsty/silo/commit/29a25a538)。包含该改动的版本都可能带有潜在问题，但真正产生用户可见影响，还需要 tiered version 在 free record 尚未清理时被生命周期、列表或迁移路径观察到。
- mixed-EC 的不一致在 2026-10-16 的 [e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067) 之后尤其明显：latest-only 读取已经能恢复可读多数，但 all-version 迁移遍历仍可能漏掉对象。已发布的 20261018、20261025 和 20261026 都包含这段行为；#267 修复了它。

这不是“所有部署或所有对象都已经损坏”，而是需要多个条件同时满足的问题。free version 单独存在是正常的待清理状态；混合 EC 元数据单独存在也是可用性优先降级写入产生的可恢复状态。真正的损坏需要在这些状态存在时再发生第二个操作：

| 状态与操作 | 结果 | 恢复位置 |
| --- | --- | --- |
| free version 短暂存在，scanner 及时完成 | 没有用户可见损坏，记录和远端对象都会被清理。 | 升级后按正常 scanner 运行；不要手工改元数据。 |
| free version 在清理前被生命周期或普通列表看到 | 可能错误判断 noncurrent、隐藏 key 或显示误导性的 delete marker。 | #264 会修正后续扫描；已经误删的真实版本需要备份或其他权威副本。 |
| 旧版 decommission/rebalance 搬运了 free version | 可能生成普通 delete marker，并丢失远端引用。 | 无法自动识别该 marker；需要比较源端副本、复制目标、备份和审计记录。 |
| 旧版 decommission/rebalance 扫描到混合 EC 元数据 | 可读对象可能被漏掉；旧池删除后对象可能丢失。 | 源池仍在时用修复版重新迁移并执行 heal；源池已删除时只能从副本或备份恢复。 |
{.wide .expand}

应该立即发布操作公告。公告应告诉使用受影响版本的操作员暂停 pool decommission 和 rebalance，尤其是在磁盘降级、tier 清理未完成或生命周期规则生效时；保留旧池和备份；升级到包含相关修复的版本；迁移后核对 GET、ListObjectsV2、ListObjectVersions 和对象数量。公告要明确这是复合条件触发的潜在问题，并单独说明 rebalance 对 transitioned version 的限制。除非项目把存储完整性问题统一归入安全漏洞，否则不需要 CVE 风格的安全标签；高优先级存储完整性 release note 和运维公告已经足够。

在发布“全部解除风险”的说明之前，还需要完成 patch release 和历史数据审计 runbook。当前 main 已经包含这三个问题的完整 decommission 修复；只发布包含 #264 与 #267 的版本，仍不足以让所有带生命周期的迁移场景安全。

## 合并与后续计划 {#plan}

1. 让已经合入的 #264、#267、#266 和 #276 一起进入下一个 patch release，覆盖普通对象视图、mixed-EC 迁移列表、生命周期 action 语义和外部清理合同。
2. 保留“版本桶当前 Expiration”“只删除一个版本的 purge”“删除整个对象”三类 action 的区分，不能退化成“一律跳过所有 ILM action”。
3. 保留复制 purge、transitioned version 清理、生命周期配置变化、整对象过期和可恢复 decommission 的回归测试。
4. 随 patch release 发布存储完整性公告，并为受影响版本上执行过池迁移的安装提供历史数据审计 runbook。
5. 单独跟踪 rebalance 对 transitioned version 的支持；#276 有意没有扩大这个范围。

三篇专题记录如下：

- [混合 EC 布局与迁移列表](/zh/blog/design/mixed-ec-migration-listing/)
- [Tier free version 是内部清理记录](/zh/blog/design/tier-free-version-semantics/)
- [ILM 过期与存储池迁移顺序](/zh/blog/design/ilm-migration-ordering/)

## 剩余边界 {#limits}

这些修复不会自动修复仍然离线的磁盘，不会恢复旧版本中已经完成错误 decommission 后丢失的数据，也无法区分旧版本错误产生的普通删除标记与客户端创建的删除标记。当 tier 不可用时，#264 可能让 decommission 失败；这是保住仍可能存在的清理记录所需的安全行为。rebalance 仍会有意跳过 transitioned version，这是独立于本次 decommission 修复的范围决策。迁移期间生命周期配置变化采用 fail-closed 语义，旧扫描结果必须在新配置下重试。
