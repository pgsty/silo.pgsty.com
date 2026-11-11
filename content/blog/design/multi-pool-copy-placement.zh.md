---
title: "多存储池 CopyObject：跨池历史版本回滚复制、迁移池权威副本绑定与压缩索引保留"
linkTitle: "多池复制放置与历史版本回滚"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  为什么将多存储池桶中的历史版本复制回同一键名会报 404 NoSuchVersion，为什么放置与重写判定必须在加密和压缩流水线之前完成，以及跨池重写如何保留 S2 多分块压缩寻址索引。
tags: [设计, 多存储池, CopyObject, 加密, 压缩]
weight: 10
draft: false
url: "/zh/blog/design/multi-pool-copy-placement/"
---

本文记录 `cmd/erasure-server-pool.go` 与 `cmd/object-handlers.go` 中一组继承自上游 MinIO 的多存储池 `CopyObject` 缺陷及其修复设计，对应 [#343](https://github.com/pgsty/silo/issues/343)。

**状态：** 已通过提交 [`a8824b341`](https://github.com/pgsty/silo/commit/a8824b341fce071cdd48356caaed37d76580c39e)、[`e36ea51d9`](https://github.com/pgsty/silo/commit/e36ea51d9c3a28df7d60f1d105226b1d0049342e) 与 [`cd3e46a2b`](https://github.com/pgsty/silo/commit/cd3e46a2b7dee00b64c323d35ebdd32aab0fe644) 合入 `main`，将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的下一版 Server 发布。`SILO Server 20261109` 及更早版本，以及自 `2020-08-03` 以来的上游原版 MinIO 均受影响。

## 简短回答 {#tldr}

在开启版本控制的 S3 存储桶中，将某个历史版本复制回当前键名（发送 `PUT /bucket/key` 并携带 `x-amz-copy-source: /bucket/key?versionId=<旧版本>`）是业务回滚对象内容的标准做法。在单存储池内，`CopyObject` 会启用零拷贝引用优化（`srcInfo.versionOnly = true`）：仅在 `xl.meta` 中追加一条指向旧版本既有 `DataDir` 的新版本记录，避免重复搬运底层数据块。

继承自上游 MinIO 的 `(*erasureServerPools).CopyObject` 错误地假设：只要源路径与目标路径的 `bucket/key` 相同，被指定的历史版本就一定存放在目标选中的那个存储池（`poolIdx`，通常为最新版本所在的池）内。一旦集群经历过扩容加池、再平衡或部分退役，出现“当前版本 `v2` 在 Pool 1、历史版本 `v1` 在 Pool 0”的正常跨池分布时，把 `versionOnly = true` 下发给 Pool 1 就会因在 Pool 1 磁盘上找不到 `v1` 而直接返回 **`404 NoSuchVersion`**；并且对于加密或压缩对象，`CopyObjectHandler` 早在外层就按单池零拷贝跳过了数据流构造（`metadataOnly = true`），底层想退回流式重写也无流可用。此外，当跨池重写走 `PutObject` 落盘分支时，上游漏传了 `IndexCB: dstOpts.IndexCB`，导致大于 8 MiB 的 S2 多分块压缩对象丢失 `Parts[0].Index` 随机寻址索引。

修复方案引入了锁内预规划函数 `prepareCopyObject`（`copyObjectPlan`）：**在 HTTP 层执行加密解封、校验和与 S2 压缩变换之前**先确定目标存储池及是否必须流式重写数据；对真正的原地元数据更新严格绑定至持有权威副本的存储池（即便该池正在退役或再平衡），对跨池版本回滚或强制数据重写则走完整流式管线写入活跃池，并在落盘时透传 `IndexCB`。

## 定性 {#assessment}

| 方面         | 评估                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| :----------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **问题性质** | 将仅在单存储池内成立的 `DataDir` 共享假设直接套用至多存储池，且跨池 `PutObject` 回退分支遗漏 `IndexCB`；继承自上游 MinIO。                                                                                                                                                                                                                                                                                                                                             |
| **上游来源** | 由上游提交 [`5ce82b45d`](https://github.com/pgsty/silo/commit/5ce82b45da652d93ed670f6072a2ada4939a8e03)（`2020-08-03`，[minio/minio#10170](https://github.com/minio/minio/pull/10170)，*"add CopyObject optimization when source and destination are same"*）引入，并在 [`ad726b49b`](https://github.com/pgsty/silo/commit/ad726b49b4799cdb878ca0a6cdf06ea2dd3c19e7)（`2020-10-15`，[minio/minio#10679](https://github.com/minio/minio/pull/10679)）多池化演进中沿用。 |
| **影响范围** | 多存储池（`2+` pools）集群在扩容、再平衡或池退役后，同一键的历史版本与最新版本分布在不同存储池时的自复制回滚，以及大于 8 MiB 的 S2 压缩对象跨池重写。                                                                                                                                                                                                                                                                                                                  |
| **故障表现** | 合法的 S3 指定历史版本自复制返回 `404 NoSuchVersion`；跨池重写的 S2 大压缩对象丢失块级范围读取（Range GET）O(1) 寻址索引。                                                                                                                                                                                                                                                                                                                                             |
| **数据安全** | 原故障表现为误报 `404`；但若在修补时错误地把普通写入选池结果直接用于迁移池上的原地更新，则会把另一池中的陈旧残留副本提升为最新并删掉正确副本（已在 `e36ea51d9` 严格拦截）。                                                                                                                                                                                                                                                                                            |
{.wide .expand}

---

## 一、上游溯源与根因分析 {#root-cause}

### 1.1 跨独立存储池无法成立的 `versionOnly` 假设（`5ce82b45d`） {#version-only}

上游在 [`5ce82b45d`](https://github.com/pgsty/silo/commit/5ce82b45da652d93ed670f6072a2ada4939a8e03)（`2020-08-03`）中将同键名复制（`cpSrcDstSame`）分成了两类免数据搬运优化：

1. **原地元数据更新：** 在未开启版本控制的对象（或指定相同目标版本的复制同步请求 `srcOpts.VersionID == dstOpts.VersionID`）上仅替换自定义元数据、标签或重封 SSE-C 密钥头。
2. **同键历史版本回滚提升（`srcInfo.versionOnly = true`）：** 从指定的旧版本 `srcOpts.VersionID` 生成一个新当前版本，新旧版本在同一个 `xl.meta` 中共享同一个底层 `DataDir`。

显然，共享 `DataDir` **只有在源版本与新版本位于同一个存储池、同一个纠删集时在物理上才可能成立**——不同存储池拥有完全独立的物理磁盘集合。然而，上层 `CopyObjectHandler`（`cmd/object-handlers.go`）在尚未知晓源版本与目标池归属时，仅凭 `bucket/key` 字符串相等就提前置了 `metadataOnly = true` 并跳过了构造解密/重加密/压缩读取流（`PutObjReader`）；下层 `(*erasureServerPools).CopyObject` 又把请求路由到了当前版本所在的 Pool 1 并置 `srcInfo.versionOnly = true`，结果在 Pool 1 查找实际位于 Pool 0 的历史版本，必然触发 `404 NoSuchVersion`。

### 1.2 退役/再平衡池场景下“原地更新”与“重写新数据”的严格边界 {#moving-pools}

在多存储池集群中，当某个池正处于**退役（`decommissioning`）或再平衡（`rebalancing`）**状态时，同键名复制存在一个极易踩中的一致性陷阱：

- **情形 A —— 真正的原地元数据更新**（如未版本化对象的 `REPLACE` 元数据修改、原地轮换 SSE-C 密钥，或 `srcOpts.VersionID == dstOpts.VersionID` 的副本更新）：
  假设权威最新数据 `current-body` 位于正在退役的 Pool 0，而活跃的 Pool 1 上恰好留有一份早期未清理干净的同名旧副本 `stale-body`。普通新写入选池函数 `getPoolIdxNoLock` 会跳过退役中的 Pool 0 而返回 Pool 1！如果原地元数据更新直接使用 `getPoolIdxNoLock` 的结果去更新 Pool 1，并在收尾时清理其他池上的同名副本，就会把 Pool 1 上的旧内容 `stale-body` 刷成最新时间戳，反过来把 Pool 0 上唯一正确的 `current-body` 删掉，造成静默数据错乱。
- **情形 B —— 需要改写底层字节的同键复制**（如未版本化对象变更为 SSE-S3 加密、重算校验和，或跨池生成新版本）：
  反过来，如果未版本化对象仅存在于正在退役的 Pool 0，而客户端发起了要求重写加密或校验和的复制请求（`copyRewritesObjectData == true`），服务端**必须**将新加密后的数据流写入**活跃池** Pool 1，而不能按原地更新去查或禁写退役池。

### 1.3 跨池 `PutObject` 分支遗漏压缩块寻址回调 `IndexCB` {#index-cb}

对于未压缩大小超过 `compMinIndexSize`（`8 MiB`）的可压缩对象，`newS2CompressReader` 会在流式压缩完毕后通过 `dstOpts.IndexCB` 生成多分块偏移量索引（持久化于 `Parts[0].Index`），使后续 `Range GET` 可直接定位到对应的 1 MiB 压缩块而无需从头解压。上游 `(*erasureServerPools).CopyObject` 在跨池回退调用 `z.PutObject` 构造 `putOpts` 时漏填了 `IndexCB: dstOpts.IndexCB`，导致跨池复制生成的压缩对象静默丢失随机寻址表。

---

## 二、修复方案：为什么锁内前置规划 `prepareCopyObject` 既必要又充分 {#fix}

提交 [`a8824b341`](https://github.com/pgsty/silo/commit/a8824b341fce071cdd48356caaed37d76580c39e)、[`e36ea51d9`](https://github.com/pgsty/silo/commit/e36ea51d9c3a28df7d60f1d105226b1d0049342e) 与 [`cd3e46a2b`](https://github.com/pgsty/silo/commit/cd3e46a2b7dee00b64c323d35ebdd32aab0fe644) 将多池复制拆分为职责清晰的两步契约：

1. **在对象锁内、变换管线启动前完成放置与重写规划（`prepareCopyObject`）：**
   `CopyObjectHandler` 获取跨池源/目标命名空间锁（`lockObjects`）后，在决定是否启用原地 SSE-C 密钥重封快路径、以及构造解密/压缩/重加密流**之前**，先调用 `prepareCopyObject` 生成确定性的 `copyObjectPlan{poolIdx, rewrite}`：
   - 首先通过 `copyRewritesObjectData` 判定加密模式、旧格式或校验和变更是否强制要求重写底层字节（`reference = sameObject && !copyRewritesObjectData(...)`）。
   - **原地元数据更新（`inPlace == true`）：** 当 `reference` 成立且操作精确作用于原版本自身（`dstOpts.VersionID != "" && srcOpts.VersionID == dstOpts.VersionID`，或未开启版本控制且未指定历史版本）时，调用 `getLatestObjectInfoWithIdx` 严格定位到**权威源副本所在的存储池**——即使该池处于退役或再平衡状态，也绝不切换到持有陈旧副本的其他池。
   - **生成新版本或强制重写数据（`inPlace == false`）：** 通过 `getPoolIdxNoLock` 选择健康的活跃写入池 `idx`。若原本满足同键引用条件（`reference && !z.SinglePool()`），再核对源版本所在的 `sourcePool`：若 `sourcePool == idx`，保留池内零拷贝 `versionOnly` 引用；若 `sourcePool != idx`，置 `plan.rewrite = true`，通知 `CopyObjectHandler` 取消 `metadataOnly` 并拉起完整的源版本读取 -> 解密 -> 压缩 -> 重加密流水线写入活跃池 `idx`。
2. **补齐跨池重写分支的 `IndexCB` 透传（`cd3e46a2b`）：**
   在 `(*erasureServerPools).CopyObject` 的 `putOpts` 中显式传递 `IndexCB: dstOpts.IndexCB`，完整保留多分块 S2 压缩索引。

### 为什么该设计既必要又充分 {#sufficiency}

- **必要性：**
  - 如果把跨池判定留在底层 `erasureServerPools.CopyObject` 内部才做，上层 `CopyObjectHandler` 早已跳过了 KMS/SSE-C 解封与 `PutObjReader` 构造，存储层根本无法凭空拼出明文或重加密流；
  - 如果不严格区分 `inPlace` 与 `rewrite`，要么在退役池场景下误把另一池的陈旧副本刷成最新（破坏数据正确性），要么使退役池上的加密/校验和重写复制误报 `404`。
- **充分性：** 在同一把对象锁保护下，`prepareCopyObject` 与随后的 `CopyObject` 共享完全一致的版本视图，全面覆盖单池/多池、活跃池/退役再平衡池、无版本/UUID 版本/`null` 版本，以及明文、SSE-S3、带 AAD 上下文的 SSE-KMS、SSE-C 与 `> 8 MiB` S2 压缩的全部组合（见 `cmd/object-copy-pools_test.go`）。

---

## 三、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                                 | 工程取舍与运维代价                                                                                                                                                                                                                                                                                                                               |
| :--------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **跨存储池同键回滚时的物理字节重写开销** | 当历史版本位于 Pool 0 而新版本分配至 Pool 1 时，服务端会实际流式读取并向 Pool 1 写入一份完整对象数据（消耗常规复制 I/O 与新池空间），不再共享 `DataDir`。由于两个独立存储池不共享任何底层硬盘，跨池物理重写在客观上不可避免，且将原先必现的 `404 NoSuchVersion` 恢复为符合 S3 语义的正确复制；源与目标落在同一池内的情况仍保持 O(1) 零拷贝引用。 |
| **退役池上的原地元数据修改行为**         | 当权威副本仍位于正在排空的退役池上时，纯原地元数据更新（如 `REPLACE` 元数据或原地轮换 SSE-C 包装密钥）会就地更新退役池上的权威副本，随后由后台退役扫描器将该最新状态完整迁往活跃池。                                                                                                                                                             |
{.wide .expand}

## 验证 {#verification}

`cmd/object-copy-pools_test.go` 针对跨池历史版本自复制（覆盖明文、SSE-S3、带加密上下文的 SSE-KMS、SSE-C 及大于 8 MiB 的 S2 多分块压缩 `Parts[0].Index` 校验）以及退役/再平衡池存在跨池同名陈旧副本、同秒时间戳并列和强制重写场景进行了端到端回归验证。另见[多存储池对象一致性设计](/zh/blog/design/multi-pool-object-consistency/)与 [Server 候选兼容性说明](/zh/compatibility/server/#candidate-after-20261109)。
