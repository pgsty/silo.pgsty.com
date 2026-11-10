---
title: "Tier free version 是内部清理记录"
linkTitle: "Tier free version 语义"
date: 2026-10-27
lastmod: 2026-11-10
author: "PGSTY SILO 维护团队"
summary: >
  解释 tier free version 是什么、为何把它当作普通版本会破坏生命周期与存储池迁移，以及 PR #264 为何是最小完整修复。
tags: [设计, Tier, 生命周期, 存储池, 兼容性]
weight: 12
draft: false
url: "/zh/blog/design/tier-free-version-semantics/"
---

本文记录 [issue #263](https://github.com/pgsty/silo/issues/263) 与 [PR #264](https://github.com/pgsty/silo/pull/264) 的审查结论（#276 后续更新基线 [0fc5a0b5](https://github.com/pgsty/silo/commit/0fc5a0b5278980b0960abf26566ce3272f85227b)），#264 的合入提交记录为 [0cfca29c](https://github.com/pgsty/silo/commit/0cfca29cb2f16e43cb8266d9259f0dc5298c53b3)。这个 PR 的三个提交是一组相互配合的修复，不是三个互不相关的 workaround。

**状态：** 已连同下文的 free version 清理归属与 decommission 取消后续修复一并随 [SILO Server 20261109](/zh/blog/release/silo-20261109/)（`d998292387cc`）正式发布。

## 先说结论 {#tldr}

问题成立。free version 是 SILO 在删除 tier 远端对象期间留在 xl.meta 中的内部清理记录。它带有 delete-marker 类型和被删除版本的时间，但它不是用户版本。GET 已经忽略它，若干批处理路径却没有。

于是出现四类问题：

- 生命周期把 free entry 下方的真实版本当成 noncurrent，可能删错版本；
- ListObjectVersions 在一个 GET 可读的对象上方显示最新删除标记；
- ListObjectsV2 隐藏这个 key；
- decommission 与 rebalance 把 free record 当成真实删除标记搬走，旧池删除后对象变得不可读。

PR #264 同时修复生命周期视图、latest marker 判断、普通列表和池清理，并保留 healing 所需的全量视图。该 PR 已作为继续审查 #266 的必要基础合入，并随 [SILO Server 20261109](/zh/blog/release/silo-20261109/) 发布。

## free version 到底是什么 {#meaning}

tier 对象有两部分：

1. hot pool 中的元数据；
2. 配置的远端 tier 中的对象。

删除数据版本时，SILO 可能暂时无法删除远端对象。于是写入一个 free version，记录远端对象名、远端版本、tier 和删除时间。scanner 后续先删除远端对象，再删除这条本地记录。

客户端按 version ID 删除 tier 版本可能产生它；覆写 tiered null version 可能产生它；ILM 远端删除失败时也可能产生它。这个记录对 healing 和 tier 清理有用，但不属于 S3 版本历史。

## 引入时间与历史 {#history}

free-version 机制由上游 [a1df23051](https://github.com/pgsty/silo/commit/a1df23051) 引入，时间是 2021-06-30，用来跟踪 tier 内容删除。普通读路径长期以来已经在计算 IsLatest 和 successor time 时跳过 free entry。

之后，上游在 [29a25a538](https://github.com/pgsty/silo/commit/29a25a538) 中把 free version 放进版本列表，并显示为删除标记，时间为 2024-06-07。原意是为了可观测性，让使用版本列表的操作员能看到 xl.meta 的所有条目。但这样就把内部清理记录暴露给了 S3 API，也让其他批处理调用方依赖“是否请求 free entry”。

因此这不是一个新引入的存储格式回归，而是同一表示被当成了两种东西：

- GET 把它当内部清理状态。
- scanner、list、Walk、decommission、rebalance 把它当对象版本。

## 根因，用简单的话说 {#root-cause}

假设对象有真实版本 v1、v2，最新的 tier 版本 v3 被删除。元数据可能近似如下：

~~~text
free(v3 的远端对象、v3 的删除时间)
v2
v1
~~~

free entry 带着 v3 的时间，所以排在 v2 之上。GET 跳过第一条并返回 v2。scanner 和版本列表没有跳过它：

- v2 被认为有 free entry 作为 successor，所以变成 noncurrent；
- free entry 被编码成删除标记；
- 迁移把这个标记搬到新池。

旧池移除后，新池中的标记遮住了 v2。远端对象引用也离开了 tier 清理路径。

## 影响 {#impact}

这是数据正确性与 API 正确性同时出问题：

- NoncurrentVersionExpiration 可能删除实际最新的真实版本。
- NewerNoncurrentVersions 可能保留错误数量的版本。
- ListObjectVersions 显示 DM 为 latest，但 GET 对下方真实版本返回 200。
- ListObjectsV2 可能漏掉一个可读 key。
- decommission 可能在把 free record 变成永久删除标记后报告完成。
- 如果远端对象尚未删除，搬走 free record 可能让 tier 数据失去清理引用。
- tier 不可用时，静默完成 decommission 是不安全的。

这会在正常的版本化 tier 工作流中发生：删除 tier 版本后，在 scanner 完成清理前启动迁移即可触发。

## 备选方案 {#options}

### 只修 scanner {#option-scanner}

从非 free 版本重新计算 IsLatest 和 successor time，可以阻止最危险的误过期，但不能修复 S3 列表和迁移。decommission 仍可能产生删除标记。

### 只修列表与迁移 {#option-listings}

这会让 API 和迁移看起来正确，但 scanner 仍可能在 free entry 存在时删除错误版本，仍然不完整。

### 到处都保留 free entry {#option-visible}

这能保留 #19878 的上游可观测性行为，但会把内部清理记录暴露为公共删除标记，让 GET、生命周期、列表和迁移互相矛盾。SILO 的维护目标是维护栈的逻辑对象行为，内部 tier 账本不应定义 S3 历史。

### 删除时立即清理 free entry {#option-delete-time}

远端 tier 暂时不可用时会失败。free record 正是远端清理仍未完成的持久提醒，过早删除可能让远端数据永久失去引用。

### 建立两个明确视图 {#option-two-views}

这是最小的完整设计：

- 普通列表、生命周期计算、Walk、decommission、rebalance 只看真实版本；
- healing 和 tier cleanup 可以请求全量条目；
- decommission 先删除 free entry 指向的远端对象，再删本地记录；tier 无法访问时失败并支持重试。

PR #264 实现了这个方案。

## PR 判断 {#pr}

#264 的三个提交顺序是有逻辑的：

1. getFileInfoVersions 在分离 free entry 后重新计算 IsLatest、SuccessorModTime 和 LatestModTime。
2. latest-delete-marker 判断跳过 free entry。
3. 普通 FileInfoVersions 排除 free entry；healing 使用显式的全量 helper；分页跳过只有 free entry 的 key；decommission 执行 tier cleanup 并使失败可重试。
{.steps}

新增测试在 main 上除有意保留的 healing guard 外都会失败，在 PR 上通过。覆盖了生命周期选择、ListObjectsV2、ListObjectVersions 分页、Walk、healing、decommission、rebalance 和 tier 不可用场景。

用户可见的变化是明确的：ListObjectVersions 不再把 free record 暴露成删除标记。这与 2024 上游行为存在兼容差异，但它恢复了对象的一致逻辑视图，阻止内部清理状态变成持久公共墓碑。SILO 的上游兼容目标是尽最大努力，维护栈本身才是发布门禁。

原审查建议采纳 #264 的整体方案，该决策已经落实到 main。它必须整体合入；只拿第一个或第二个提交，会把独立的正确性漏洞留到下一个批处理路径。

## 运维边界 {#operations}

decommission 遇到 free entry 时可能需要访问 tier。远端对象已经不存在时可以忽略，因为本地记录已经过时；tier 故障则不同：free record 必须保留，decommission 应失败，等待重试完成清理。这个行为比 main 更容易显露故障，但避免了悄悄丢失清理义务。

如果 free version 仍指向某个 tier，而该 tier 已经**从配置中删除**，这同样不是 tier 故障。free version 是其远端对象的唯一记录，因此会被保留；在以相同名称重新配置该 tier（`mcli ilm tier add`）之前，它所在存储池的 decommission 无法完成。自 `SILO Server 20261109` 起，decommission 会先搬迁其他所有桶，然后以失败结束，错误信息会指出该 free version、它的远端对象和 tier；重试时从剩下的桶继续。在此之前，decommission 会停在第一个这样的桶上，之后的所有桶都留在该池中。

自 `SILO Server 20261109` 起，远端清理与本地 free 记录的删除还会和 scanner 共用该对象的写者锁；本地删除只有在磁盘句柄、本地版本 ID、tier、远端对象和远端版本都与已删除远端对象的那条记录完全一致时，才会移除这条 free 记录。远端删除在独立于调用方、带自身超时的上下文中执行，因此即使 decommission 被取消，只要远端删除已经成功，本地记录仍会被移除。同样，当 decommission 遇到一个恢复副本移除被拒绝的分层版本时（例如对象受锁保护或规则已不再适用），它会连同 tier 元数据和恢复截止时间一起迁移该版本，而不是报错或丢失 tier 链接（[5cb91e7d7](https://github.com/pgsty/silo/commit/5cb91e7d7)）。

自 `SILO Server 20261109` 起，`mcli admin decommission cancel` 在返回之前还会先把取消状态持久写入磁盘，因此正处在搬迁完桶、保存集群配置阶段的 decommission 会以 `Canceled` 结束，而不是 `Complete`。

这个修复无法识别或恢复旧版本错误 decommission 已经产生的普通删除标记，因为这些标记已经没有 free-version 标志。受影响对象需要从备份或其他权威副本恢复。

## 验证参考 {#verification}

- Issue: [#263](https://github.com/pgsty/silo/issues/263)
- PR: [#264](https://github.com/pgsty/silo/pull/264)
- 合并提交：[0cfca29c](https://github.com/pgsty/silo/commit/0cfca29cb2f16e43cb8266d9259f0dc5298c53b3)
- free-version 引入：[a1df23051](https://github.com/pgsty/silo/commit/a1df23051)
- 上游列表变更：[29a25a538](https://github.com/pgsty/silo/commit/29a25a538)
- PR head：[7ce7fc8d1](https://github.com/pgsty/silo/commit/7ce7fc8d1)
- free version 清理归属与 decommission 取消：[ade15ea5d](https://github.com/pgsty/silo/commit/ade15ea5d)、[96b3a19d0](https://github.com/pgsty/silo/commit/96b3a19d0)、[5cb91e7d7](https://github.com/pgsty/silo/commit/5cb91e7d7)
