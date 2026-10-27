---
title: "多池对象一致性"
linkTitle: "多池对象一致性"
date: 2026-09-16
lastmod: 2026-10-26
author: "冯若航"
summary: "先在共享锁下选择一个逻辑对象，再判断条件或合并标签和 Object Lock 状态。"
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/zh/blog/design/multi-pool-object-consistency/"
---

随 [SILO Server 20260916](/zh/blog/release/silo-20260916/) 发布的 [PR #178](https://github.com/pgsty/silo/pull/178) 修复了多存储池修改顺序问题，[PR #207](https://github.com/pgsty/silo/pull/207) 将当前逻辑对象选择扩展至条件 `PUT`（关闭 [#133](https://github.com/pgsty/silo/issues/133) 与 [#144](https://github.com/pgsty/silo/issues/144)），提交 [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) 则修复了跨池再平衡（rebalance）与退役（decommission）迁移丢失对象标签的缺陷。随后的 [SILO Server 20261018](/zh/blog/release/silo-20261018/) 进一步合入 [`60c7179dd`](https://github.com/pgsty/silo/commit/60c7179ddbfcbd41a1fe67707230f5b360a43020)（纳入 [PR #248](https://github.com/pgsty/silo/pull/248)）与 [`1748f62c7`](https://github.com/pgsty/silo/commit/1748f62c7ec4f2e9afcdce276193ad401719b951)，修复了跨池迁移期间旧数据覆盖新副本以及删除标记（Delete Marker）丢失的问题。

<span id="maintenance-20261025"></span>

## 10 月 26 日：存储超时与回滚边界 {#maintenance-20261026}

[Server 20261026](/zh/blog/release/silo-20261026/#server-20261026) 完整保留了下文的多池删除保护，并转发覆盖写回滚所需的存储 RPC 删除选项（旧数据目录）。在最终发版前，提交 [`dcc2f20ba`](https://github.com/pgsty/silo/commit/dcc2f20ba81c51a11dab047bb65c86e0dc6a6038) 撤回了 10 月维护草稿中的已接纳 I/O 排空等待、逐对象变更锁（mutation guard）、回滚所有权校验与备份互斥方案，维持既有的磁盘/RPC 超时、请求取消、对象锁、读仲裁与自愈行为。

需要注意：**客户端收到超时响应并不代表底层磁盘或 RPC I/O 已经停止，也不代表写入未提交。** 在部分磁盘故障、锁租约失效或网络分区后，仍可能出现迟到提交、延迟回滚，或在部分元数据更新后短暂读到旧值与旧标签；对象锁本身不提供跨节点分布式 fencing，升级也不会自动修复存量不一致对象（更严格的诊断检查仍保留在非默认的 `consistency_strict` 构建标签下）。

## 10 月 24 日更新：删除失败时保护最新副本 {#delete-20261024}

[PR #257](https://github.com/pgsty/silo/pull/257)（提交 [`aafe4f8886`](https://github.com/pgsty/silo/commit/aafe4f8886a060ec698400043bee2f60e22140fd)）将多池删除保护扩展到普通无条件删除与批量删除入口。批量数据删除复用既有共享锁与解析器，先清理非权威池中的旧副本，再删除每项的权威副本，同时完整保留请求项的响应身份、支持部分物理删除后的 quorum 重试，并保护共享远端分层引用。该修改直接作用于现有的容量加权分配器，不依赖 [#245](https://github.com/pgsty/silo/pull/245)。详见[多池删除：失败时保住最新副本](/zh/blog/design/multi-pool-delete-safety/)。

## 10 月 18 日更新：在池迁移期间保护数据与删除标记 {#migration-20261018}

[SILO Server 20261018](/zh/blog/release/silo-20261018/) 新增的 [`60c7179dd`](https://github.com/pgsty/silo/commit/60c7179ddbfcbd41a1fe67707230f5b360a43020)（[PR #248](https://github.com/pgsty/silo/pull/248)）与 [`1748f62c7`](https://github.com/pgsty/silo/commit/1748f62c7ec4f2e9afcdce276193ad401719b951)，补齐了九月修复尚未覆盖的两类 rebalance / decommission 迁移竞态：旧载荷覆盖新副本以及删除标记丢失。

在向目标池提交迁移版本前，池协调层会在共享命名空间对象锁内检查所有池中的当前副本，拒绝源快照已消失、已被替换或其他存储池中已存在更新副本的搬迁操作。若修改时间戳完全相同，则沿用读取路径的池索引决胜规则。验证通过的元数据快照会直接复用于后续字段协调，避免重复读取；多段上传（Multipart）完成阶段会在复制完所有分片后再次复核，分层对象（Tiered Object）搬迁同样启用该保护。

即便删除标记是源池中的唯一版本，迁移流程也会将其迁移至目标池，因为其他存储池中可能仍存有该键的更旧数据版本。`null` 版本与 UUID 版本的删除标记均保留各自的替换与重试语义。源池清理改为在对象写锁内逐一复核并仅删除遍历快照中确认过的具体版本；若源版本已发生变化，或没有任何目标池副本能继续维持当前外部读取结果，则立即中止源清理，不再盲目删除可能已包含并发新写入或新删除标记的整个对象前缀。

**运行时成本与边界：** 迁移流程增加了逐池元数据读取与逐版本清理。对于 $P$ 个存储池和 $V$ 个源版本，清理阶段至少执行 $\mathcal{O}(P \times V)$ 次元数据操作，且解码与重写版本元数据的开销随版本历史长度增长。普通已解析的读取请求不会进入该迁移检查路径；本修复未引入新的磁盘格式、公开 S3 参数或外部依赖。历史版本迁移中已经丢失的数据、标签或删除标记无法自动重建，跨站点延迟到达的删除标记问题（[#217](https://github.com/pgsty/silo/issues/217)）仍属独立议题。

版本验收测试实际运行了 2 池与 3 池的 rebalance 和 decommission，完整覆盖普通对象、多段对象、`null`/UUID 版本与删除标记、并发写删以及双池迁移中断恢复四组场景（详见 [20261018 发布验证记录](/zh/blog/release/silo-20261018/#delivery)）。在生产环境正式退役源池前，应通过公开 S3 API 核对已确认的版本 ID、字节数、ETag、标签及删除状态。

## 为什么同一个键会存在多份物理副本 {#problem}

扩容存储池、退役旧池或清理中途中断，都可能在不同存储池中留下同一个对象键的多份物理副本。单纠删集（per-set）锁无法与路由到另一存储池的并发写入串行化；仅读取第一个响应的副本也无法证明其 ETag、标签或 Object Lock 保留期代表当前的逻辑对象。

缺乏跨池协调会导致三类典型故障：

1. 某个池中的陈旧 ETag 错误地满足了条件写入（`If-Match` / `If-None-Match`）或条件删除；
2. 某个池中较新的保留期（Retention）或法务锁定（Legal Hold）被另一池中较旧的对象元数据遮蔽；
3. 删除当前选中的副本后，另一池中的旧副本重新暴露，导致已删除数据“复活”。

孤立地操作每个存储池并在最后仅汇总成功状态，无法消除上述并发竞争。

## 共享选择与锁边界 {#design}

在 [`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) 与 [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go) 中，池协调层在“选择候选对象”到“完成修改”的全过程中持有同一把命名空间对象锁。`objectPoolInfos` 会读取每个池（包括正在排空的退役池）中的指定版本；未知或不可读状态会被直接判定为错误，而不会当作“对象不存在”的证据。各池副本按修改时间（`ModTime`）排序，时间戳相同时以存储池索引决胜。

不带 `versionId` 的元数据请求会先选定逻辑当前版本，再收集所有池中属于该特定版本的物理副本，绝不混合不同对象版本的元数据。Object Lock 保留期、法务锁定和用户标签各自拥有独立的源修订时间戳；`mergedPoolObjectInfo` 按各字段自身的修订时间戳顺序合并，而非把对象数据本体的修改时间当作所有元数据字段的版本号。带时间戳的标签清空或锁定解除同样作为显式状态参与排序。

元数据修改、相关对象写入与后台自愈（healing）共用同一把协调锁。需注意，该锁用于串行化并发访问，但并非跨池回滚事务——若在多池落盘中途遭遇底层磁盘故障，已完成写入的池不会自动回滚。

## 条件请求与删除 {#conditions}

对于条件 `DELETE`，协调层在执行跨池清理前针对选定的逻辑对象统一校验一次前置条件，并在调用下层各池删除接口前清除条件回调；若请求指定了显式 `versionId`，则针对该特定版本进行比对。

对于条件 `PUT`，[PR #207](https://github.com/pgsty/silo/pull/207) 在外层命名空间锁保护下先跨所有可用池选出最新的逻辑对象表示（包括删除标记状态），再写入新内容。这修复了目标池中残留的陈旧副本导致 `If-Match` / `If-None-Match` 判断结果与集群当前逻辑对象不一致的缺陷。

若跨池清理或元数据传播在修改了部分物理副本后遇到存储错误，恢复后应重新核对对象状态并重试。批量 XML `DeleteObjects` 的 ETag 条件仍不受支持，详见[条件 DELETE 设计说明](/zh/blog/design/conditional-delete/)。

## Object Lock 与桶复制 {#replication}

副本写入会跨所有存储池与同版本的权威副本协调目标端保留期和法务锁定状态，防止乱序到达的旧副本缩短较新的保留期或关闭较新的法务锁定。对象标签同样携其修订时间戳（包括表示删除的空值）一同传递与比对。详见 [Object Lock 复制顺序保护](/zh/blog/design/object-lock-replication-ordering/)与[复制标签顺序一致性](/zh/blog/design/replicated-tag-ordering/)。

## 跨池迁移中的对象标签保持 {#migration-tags}

rebalance 与 decommission 会将每个对象版本读取为 `FileInfo`，再转换为 `ObjectInfo`——这一步会将内部标签头从普通 `UserDefined` 元数据映射表移至独立的 `UserTags` 字段——随后再将对象写入目标池。自 2022 年引入迁移写入逻辑以来，四个迁移写入入口仅复制了普通 `UserDefined` 元数据映射表，导致普通对象与多段对象在 rebalance 和 decommission 过程中均会丢失用户标签（2020 年引入的字段拆分本身并无问题）。

提交 [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) 让四个迁移写入入口共用统一的元数据组装函数：在既有协调锁保护下克隆元数据映射表、写回 `UserTags`，并原样保留已落盘的标签修订时间戳字段而不伪造新时间戳。回归测试覆盖了普通对象与多段对象、初始标签、更新后标签、清空标签以及版本化与旧格式读取。此前在旧版本迁移中已丢失的标签需从源端或备份恢复。

## 验证与运维指引 {#verification}

[`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) 与 [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go) 中的多池协调实现已通过多存储池、陈旧副本、删除标记、显式版本、并发写入及故障路径测试验证。

在依赖共享锁一致性保证前，请协同升级集群中的所有参与节点。对于此前曾执行过跨池迁移或多池并发写入的存量部署，建议结合[副本元数据审计手册](/zh/operations/replication/replica-metadata-audit/)与[组件版本矩阵](/zh/compatibility/versions/)盘点存量副本、标签及 Object Lock 状态。
