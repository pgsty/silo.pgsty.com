---
title: "混合 EC 布局与迁移列表"
linkTitle: "混合 EC 迁移列表"
date: 2026-10-27
lastmod: 2026-11-02
author: "PGSTY SILO 维护团队"
summary: >
  解释同一个对象存在两种可读纠删码布局时，为何会从 decommission 与 rebalance 列表中消失，以及 PR #262 为何是最小且安全的修复。
tags: [设计, 存储池, 纠删码, 迁移]
weight: 11
draft: false
url: "/zh/blog/design/mixed-ec-migration-listing/"
---

本文记录 [issue #261](https://github.com/pgsty/silo/issues/261) 与 [PR #262](https://github.com/pgsty/silo/pull/262) 的审查结论，本文已按 #276 后的 main [0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b) 更新。实际修复通过维护者 PR [#267](https://github.com/pgsty/silo/pull/267) 合入，#262 是后来被取代的重复 PR。

## 先说结论 {#tldr}

问题成立。一次成功的降级覆写可能让一个无版本对象同时存在两种 EC 布局：在线磁盘上有更新的副本，离线磁盘上保留旧副本。GET 与 ListObjectsV2 能选出更新的可读多数；decommission 与 rebalance 使用 all-versions 遍历，此时元数据合并可能以旧布局为参考，只统计旧布局。旧布局低于 quorum 后，对象就从迁移列表中消失。迁移报告成功，旧池被移除后对象丢失。

PR #262 的修复方向正确。它只放宽已有 mixed-EC recount 的一个过窄条件，仍把 recount 限制在“每个非空流都只有一个普通 null version”的安全范围，并增加 quorum、流顺序、迁移和排除场景测试。该修复已经通过 #267 合入，#267 还增加了完整的池移除回归测试。

## 什么条件会触发 {#trigger}

需要同时满足以下条件：

1. 对象存储在纠删码集合中。
2. 写入或覆写发生时有一个或多个磁盘不可用。
3. 可用性优先的写入在在线磁盘上使用了不同的 parity 或 layout。
4. 离线磁盘仍保留旧元数据。
5. 在 decommission 或 rebalance 扫描前，修复没有完成。

只要某个 EC 组达到 quorum，对象仍然可读。问题是否出现还取决于旧、新元数据流到达的顺序，所以不同磁盘组合下表现会有差异，但底层状态本身是确定的。

## 什么时候引入 {#history}

混合布局是可用性优先降级写入的自然结果。SILO 相关的列表修复在 2026-10-16 的 [e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067) 中引入，用于处理更广泛的列表一致性问题。该修复只为 latest-only 读取打开了 recount；all-versions 的迁移调用仍使用旧选择路径。

于是出现了分裂契约：

| 调用方 | 请求模式 | main 上的行为 |
| --- | --- | --- |
| GET 与 ListObjectsV2 | latest-only | 对符合条件的混合 EC 组重新计数，选出可读 quorum。 |
| ListObjectVersions、decommission、rebalance 及部分 Walk 调用 | all versions | 普通合并失败后停止，可读多数被少数旧布局遮住。 |
{.wide .expand}

所以这个缺陷来自 2026-10-16 修复的范围没有覆盖完整调用链。底层降级元数据状态可以更早存在；真正暴露数据丢失路径的是只有一类调用方学会了恢复。

## 根因，用简单的话说 {#root-cause}

假设有 16 个磁盘：4 个磁盘仍保存旧的 12+4 元数据，12 个磁盘保存新的 8+8 元数据。两组都描述同一个 null version，但 EC header 不同。

合并逻辑按顺序查看元数据流。看到差异后，它可能以当前 EC 作为参考，只统计匹配该 EC 的条目。旧组只有 4 个，达不到 8 的 quorum，于是返回空结果。latest-only 读取已有的第二次 recount 会发现新组有 12 个，能够达到 quorum。

迁移路径传入的 requestedVersions 是 0，而 mixed-EC fallback 原来被 requestedVersions 等于 1 的条件保护。于是同一份元数据对 GET 是“可读对象”，对 decommission 却是“没有对象”。

这个保护条件不能简单删除所有安全边界。不能把任意 EC 组、版本历史、UUID 冲突、删除标记、free version，或 legacy/partial header 混在一起。安全范围是：每个非空流只有一个普通 null version，并且有现代 EC header。此时列最新版本与列全部版本实际上是在问同一个逻辑对象。

## 影响 {#impact}

操作员在移除存储池前看到的都是正常的：

- GET 返回新数据。
- ListObjectsV2 返回对象。
- decommission 和末尾检查都看不到对象。
- rebalance 把对象留在源池。
- 无版本或 suspended bucket 的 ListObjectVersions 也可能漏掉对象。
- 旧池移除后，GET 和两个列表都找不到对象。

问题严重之处在于迁移状态会错误地报告成功。旧池一旦删除，通常无法再重试恢复。

## 备选方案 {#options}

### 方案一：迁移前必须先成功 heal

这可以作为运维缓解，但不是完整修复。磁盘可能一直不可用，MRF 可能放弃；旧元数据虽然有效，GET 也不一定会排队 heal。如果把所有迁移都阻塞到布局统一，池退役就会依赖无关的磁盘恢复。

### 方案二：让迁移调用方统一使用 latest-only 列表

这会把列表策略复制到 decommission 和 rebalance 中，并可能改变它们处理版本历史的方式，还会留下 ListObjectVersions 与 Walk 的不一致。

### 方案三：合并所有 EC 组或降低 quorum

不安全。两个都低于 quorum 的组不能因为对象名相同就合票；降低 quorum 可能选出无法重建的数据。

### 方案四：扩展现有的窄范围 recount

这是最小的安全改动。recount 只在普通选择失败后运行，只对非 strict 读取生效，并且只处理每个流一个普通 null version。PR #262 正是这个方案。

## PR 判断 {#pr}

PR #262 去掉 mixed-EC 条件对 latest-only 模式的依赖，并增加：

- requestedVersions 为 1 与 0 时相同的选择断言；
- strict、UUID、delete marker、free version、history、legacy、partial EC 等排除场景；
- decommission 与 rebalance 的迁移回归测试；
- 将新回归测试加入 race workflow。

聚焦基线测试在 main 上会在可读混合 EC 场景失败，在 PR 上通过。新增测试也保留了重要的负面断言：低于 quorum 的组不能被错误合并。该补丁不改变 API、配置、磁盘格式、指标或依赖。

合入后的实现符合原建议：这个窄范围 recount 充分解决 #261，同时没有引入可能掩盖不安全元数据状态的广泛修复机制。原 issue 已标记完成，#262 已因被 #267 取代而关闭。

## 剩余边界 {#limits}

补丁只负责选出可读组，不负责修复旧组。离线磁盘恢复后仍应执行 heal。它也无法恢复旧版本中已经完成错误 decommission 后丢失的对象。其他畸形或混合版本历史仍按保守方式处理，这是刻意保留的安全边界。

## 验证参考 {#verification}

- Issue: [#261](https://github.com/pgsty/silo/issues/261)
- PR: [#262](https://github.com/pgsty/silo/pull/262)
- 实际合入的维护者 PR：[#267](https://github.com/pgsty/silo/pull/267)
- 合并提交：[a7310d59f](https://github.com/pgsty/silo/commit/a7310d59fe307ae7fc4b57dc190b5e0c3de1a56a)
- 修复提交：[5eb6433f0](https://github.com/pgsty/silo/commit/5eb6433f0)
- 更早的混合 EC 列表修复：[e90cb2067](https://github.com/pgsty/silo/commit/e90cb2067)
