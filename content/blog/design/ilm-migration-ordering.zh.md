---
title: "ILM 过期与存储池迁移顺序"
linkTitle: "ILM 迁移顺序"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO 维护团队"
summary: >
  解释生命周期过期与存储池迁移为何对版本桶当前对象产生不同判断、#266 修复了什么，以及 #276 如何补齐复制、tier 和生命周期安全边界。
tags: [设计, 生命周期, 存储池, 复制]
weight: 13
draft: false
url: "/zh/blog/design/ilm-migration-ordering/"
---

本文记录 [issue #265](https://github.com/pgsty/silo/issues/265)、贡献者修复 [PR #266](https://github.com/pgsty/silo/pull/266) 与维护者后续修复 [#276](https://github.com/pgsty/silo/pull/276)，并说明已经合入的 [#264](https://github.com/pgsty/silo/pull/264) 与 [#267](https://github.com/pgsty/silo/pull/267) 是相关前置修复。本文已于 2026-11-02 按 #276 合入后的 main 更新。#266 的 decommission 提交是 [19910230a](https://github.com/pgsty/silo/commit/19910230a)，rebalance 提交是 [a995921e5](https://github.com/pgsty/silo/commit/a995921e5)。

## 先说结论 {#tldr}

问题成立。在版本桶中，当前版本到期时 Expiration 会创建删除标记，并把数据版本保留为 noncurrent。decommission 与 rebalance 却把所有 lifecycle DeleteAction 都当成“该版本已经被删除”，于是跳过了复制。

结果有两种：

- decommission 可能报告 Complete，旧池移除后当前版本丢失；也可能因为 expiry worker 的时序竞争而失败。
- rebalance 可能已经复制了一部分版本，却把源端副本永久留下。

PR #266 让迁移代码区分这些 action。为了保留贡献者正确的本地修复，我们先合入了它；维护者后续 PR [#276](https://github.com/pgsty/silo/pull/276) 再让 ILM 选中的删除复用既有 expiry 合同，并补上必要的安全栅栏。两者合在一起已经覆盖 decommission 与普通 hot-tier 生命周期迁移。rebalance 仍有意跳过 transitioned version，这是独立的范围边界。

#276 之前，本地算法对普通 hot-tier 版本的搬迁是正确的，但还缺少四条安全边界：

- 直接删除源版本可能绕过桶复制；
- transitioned version 可能失去唯一的远端清理记录；
- 必须明确迁移扫描与清理之间生命周期配置发生变化时的规则；
- 删除整个对象的 action 可能在 decommission 报告 Complete 后仍把当前版本留在源池。

这些边界与原始的本地迁移问题是分开的；#276 用小范围边界调整和回归测试补齐了它们，不需要重写整个存储池迁移。

## 时间线与来源 {#history}

上游首次引入“decommission 跳过生命周期过期对象”的提交是 [236ef03db](https://github.com/pgsty/silo/commit/236ef03db)，时间为 2022-07-14。池级 rebalance 在 [4523da654](https://github.com/pgsty/silo/commit/4523da654) 中引入，时间为 2022-10-25，也采用了类似的生命周期跳过思路。之后上游在 [3637aad36](https://github.com/pgsty/silo/commit/3637aad36) 中调整跳过项计数，在 [9af6c6cee](https://github.com/pgsty/silo/commit/9af6c6cee) 中让 rebalance 与 decommission 对齐，分别发生在 2023-05-11 和 2023-06-21。

SILO 在 [1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7) 中明显收紧了迁移清理，时间为 2026-10-18：从宽泛的前缀清理改为只删除经过源端与目标端检查的具体版本。这样能更好地防止并发删除，但也意味着“被 ILM 跳过的版本”不能再因为前缀删除而顺带消失。

所以问题是旧的 lifecycle skip 语义与新的逐版本安全检查发生交互。两部分单独看都合理，合在一起却对版本状态得出了不同结论。

## 什么条件会触发 {#trigger}

最常见的触发方式是规则在两次 scanner 之间到期，或在迁移前刚刚新增/修改规则：

1. 版本桶中有 v1、v2 和当前 v3。
2. Expiration 规则已经对 v3 到期。
3. expiry worker 尚未执行，迁移 walker 先评估了规则。
4. evaluator 返回 DeleteAction。

对版本桶来说，DeleteAction 的含义是“在当前版本上方新增删除标记”，不是“立刻删除 v3”。同一次迁移也可能看到真正只删除一个版本的 DeleteVersionAction，例如 NoncurrentVersionExpiration。这两个 action 不能使用相同的迁移处理。

expiry queue 越慢，风险越明显。当前版本可能被跳过，而且目的池没有副本；旧池删除后它就丢了。处于 COMPLIANCE 保留期的版本也会暴露，因为删除标记仍然可以创建，而保留的数据版本本应继续存在。transitioned current version 也是 decommission 的特殊情况。

## 根因，用简单的话说 {#root-cause}

旧代码使用一个布尔过滤器：

~~~text
如果 lifecycle action 会删除某些东西：
    排队 expiry
    跳过这个版本
~~~

这个布尔值抹掉了几个不同语义：

- 版本桶上的 DeleteAction：增加标记，保留当前数据版本；
- DeleteVersionAction：删除一个 noncurrent 版本；
- DeleteAllVersionsAction：删除整个对象历史；
- delete-restored action：删除恢复副本，而 tier 元数据有另一套规则。

于是 decommission 把跳过项计为完成，末尾检查也忽略它；rebalance 则不计跳过项，所以“所有版本已搬迁”的条件永远无法满足，源副本会留下。

新的 removeMovedVersions 又增加了一个必要规则：只有当目标副本仍然保留读取结果时，才能删除源版本。这个规则对已经搬迁的版本是正确的，但不能原样用于“ILM 会删除、且不会产生目标副本”的版本。如果跳过版本留在源池，其他新版本搬走后，它可能成为源池中的最新版本；expiry 重新评估时反而得到“不需要删除”。

为处理这个情况加入的直接 purge 还有自己的边界。它用版本 ID 和 SkipFreeVersion 调用源池的 DeleteObject，这是一项存储清理操作，不是普通的 S3 删除路径。它不会自动执行复制决策、写入 VersionPurgePending，也不会删除远端 tier 对象。

## 维护者后续修复如何补齐这些边界 {#boundaries}

#266 中加入的 direct purge 本质上是本地存储清理。单独看，它不会自动执行复制决策、写入 `VersionPurgePending`，也不会删除远端 tier 对象。#276 保留 #266 的 action 区分，同时让迁移遵守普通 ILM expiry 已经拥有的合同。

### 复制仍然是第二项义务

如果删除复制规则适用，删除源端过期版本并不等于操作完成，目标端还必须收到 version purge。#276 让 ILM 选中的版本删除在源端清理前先走普通 expiry 路径，因此复制状态和 purge 队列会先建立，源端副本之后才会退役。回归测试使用双池、延迟 expiry，并验证目标端最终收敛。

这是最小的安全边界，因为它复用了已有复制路径，只在迁移与 expiry 之间补了一次必要的交接，不需要把复制决策复制到 `removeMovedVersions` 中，也不会让延迟的 expiry task 因为源端已经消失而得到 `VersionNotFound`。

### transitioned version 必须保留清理义务

transitioned version 同时需要清理 hot-tier 元数据和远端 tier 对象。如果远端删除失败，hot-tier 中必须留下持久的 free version，让后续 scanner 可以重试。#276 先处理 hot-tier 状态，并在远端删除失败时保留可重试的 free-version 记录；decommission 只有在普通版本和 free version 都清理干净后才报告完成。

这保持了 #264 的双视图模型：free version 继续是内部清理记录，普通生命周期和迁移视图仍然排除它。#266 中 rebalance 仍然跳过 transitioned version；让 rebalance 搬迁它们应作为单独的范围决策处理。

### 生命周期配置变化采用 fail-closed 语义

迁移遍历开始时记录生命周期配置更新时间。源端清理执行不可逆决定前会重新比较这个值；如果配置发生变化，迁移停止并保留源端数据，等待按新规则重试。

这是最小的安全语义：它不会静默执行过期的删除判断，代价只是操作员在迁移期间修改生命周期配置时多执行一次迁移。

### 整对象过期需要可观察的完成栅栏

`DeleteAllVersionsAction` 与 `DelMarkerDeleteAllVersionsAction` 必须在旧池退役前删除整个历史。#276 在源端清理前执行整对象 expiry，并确认普通版本与 free version 都已经消失，再让 decommission 报告完成。这样不会出现旧池仍独占当前版本、而旧版本已经搬到新池的状态。

这个栅栏使用已有的源端状态检查，而不是引入新的异步事务。它保留当前 expiry worker 和重试模型，同时让 `Complete` 真正表示源池已经不再拥有该对象。

## 影响 {#impact}

操作员可能看到：

- decommission 报告 Complete，旧池移除后当前版本消失；
- decommission 报 PreConditionFailed，需要第二次运行；
- rebalance 报告有进展，却把源副本留下；
- object lock 保护的版本或 tier 中的版本从源端迁移路径丢失；
- 源端 purge 后，复制目标仍保留旧版本；
- transitioned version 被直接 purge 后，远端 tier 数据变成孤儿；
- 已经进入迁移的源端清理忽略生命周期规则变化；
- 后续 scanner 也不会删除这些重复副本。

即使迁移前 GET 正常，这仍是迁移正确性问题，因为丢失发生在旧池退役的边界。

## 备选方案 {#options}

### 只要 lifecycle 到期就阻塞迁移

安全但不可用。scanner 的正常延迟会变成迁移故障，规则变更后还需要正确重扫。

### 迁移前同步执行 lifecycle

可以降低竞争，但不能定义 expiry queue、tier 或目的地不可用时怎么办，还会增加迁移延迟，并且仍需让迁移 walker 正确解释生成的元数据。

### 跳过所有 ILM action，再删除源端整个前缀

接近旧的宽泛清理逻辑，但可能在目的池尚未创建删除标记前就删除版本桶当前对象，也绕过 SILO 特意加入的逐版本并发保护。

### 区分 action 语义，只清理安全的内容

这是最小的必要设计：

- Expiration 只产生标记时，搬迁当前版本；
- ILM 真正删除一个版本时可以跳过，但允许源端清理不要求目的池有副本；
- 删除整个对象历史的 action 保留现有语义，等 expiry 在所有池中执行；
- rebalance 把跳过项计为已处理，从而可以清理已搬迁的源副本。

PR #266 实现了这个设计。

### 当删除带有外部副作用时先搬迁版本

复制和 tier 清理让直接源端 purge 不再只是本地元数据操作。先搬迁版本，再让普通 ILM worker 执行删除，可以复用已有的复制和 tier 合同。它可能会短时间保留一份额外副本，但不需要在迁移清理中重新实现这些合同。

## PR 判断 {#pr}

#266 是对原始本地问题正确的贡献修复：

1. 不再把版本桶当前 Expiration 产生的删除标记，当成数据版本已经被删除；
2. 区分只删除一个版本与删除整个对象；
3. 让 decommission 和 rebalance 正确计算 ILM 真正会删除的版本；
4. 保留新版迁移清理加入的逐版本源端与目标端检查。

我们先合入 #266 以承认这项贡献。维护者后续 PR [#276](https://github.com/pgsty/silo/pull/276) 再补上必要的组合边界：

- 源端清理前先建立复制状态并排队 purge；
- 远端 tier 删除失败时保留可重试的 transitioned-version 清理记录；
- 生命周期配置变化会使旧遍历结果失效；
- 整对象 action 在 decommission 报告成功前完成并验证；
- decommission 与 rebalance 使用独立的生命周期审计来源；
- 回归测试覆盖延迟 expiry、复制、tier 清理、配置变化、整对象过期和可恢复 decommission。

合并后的结果对报告的 decommission 问题充分且必要，也是合理的最小改动：action 语义留在迁移 worker 中，复制和 tier 清理复用已有路径，完成判断使用系统已有的持久化元数据检查。没有引入新的元数据格式，也没有重写存储池迁移。

代价主要是少量额外元数据操作，以及某些情况下多一次迁移重试或短时间保留额外副本。相比静默丢版本、让复制目标停留在旧状态或产生远端 tier 孤儿，这些代价是必要且可接受的。

这个修复有意不扩展 rebalance 对 transitioned version 的支持。该问题需要单独的 tier 所有权测试和范围决策，不应在 #276 中顺手扩大。

## 合并顺序与冲突 {#merge}

最终顺序是有意安排的：#264 先建立真实版本视图，#266 保留贡献者的 action 区分，#276 再在两者之上补齐维护者负责的复制、tier、生命周期代数和完成检查。#266 的原始提交仍保留在合并历史中。

组合测试覆盖 free version 位于生命周期过期版本上方、被选中删除的 transitioned version、启用复制的 version purge、生命周期配置变化、整对象过期，以及复制完成后的可恢复 decommission。

## 剩余边界 {#limits}

rebalance 仍会有意跳过 transitioned version。这个修复也不会自动修复仍然离线的磁盘、恢复旧版本错误 decommission 已经丢失的数据，或清理已经失去 free-version 记录的旧孤儿 tier 对象。这些是独立的运维或范围决策。迁移期间生命周期配置变化现在采用 fail-closed 语义，旧扫描结果必须按新配置重试。

## 验证参考 {#verification}

- Issue: [#265](https://github.com/pgsty/silo/issues/265)
- PR: [#266](https://github.com/pgsty/silo/pull/266)
- 审查所用当前 main：[0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b)
- 已合入的 free-version 修复：[#264](https://github.com/pgsty/silo/pull/264)
- 已合入的 mixed-EC 迁移修复：[#267](https://github.com/pgsty/silo/pull/267)
- decommission 修复：[19910230a](https://github.com/pgsty/silo/commit/19910230a)
- rebalance 修复：[a995921e5](https://github.com/pgsty/silo/commit/a995921e5)
- 相关 ILM 复制提案：[#240](https://github.com/pgsty/silo/pull/240)
- 原始 decommission 跳过：[236ef03db](https://github.com/pgsty/silo/commit/236ef03db)
- 池级 rebalance 引入：[4523da654](https://github.com/pgsty/silo/commit/4523da654)
- SILO 逐版本清理改动：[1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7)
