---
title: "存储池退役与再平衡：同名父子键遮蔽、并发兄弟版本删除与坏盘仲裁容错"
linkTitle: "存储池退役物理进展与坏盘容错"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  为什么继承自上游的存储池退役会漏掉被同名父对象遮蔽的子键、在兄弟版本被并发删除时滞留已迁移副本，以及如何在保证每块在线盘零残留的前提下容忍纠删码读仲裁范围内的离线坏盘。
tags: [设计, 多存储池, 池退役, 再平衡, 纠删码]
weight: 10
draft: false
url: "/zh/blog/design/pool-decommission-physical-progress/"
---

本文记录 `cmd/erasure-server-pool-decom.go`、`cmd/erasure-server-pool-rebalance.go` 与 `cmd/erasure-server-pool-migration.go` 中三项继承自上游 MinIO 的存储池迁移与退役缺陷及其修复设计（[#293](https://github.com/pgsty/silo/issues/293)、[#340](https://github.com/pgsty/silo/issues/340)），作为 [11 月 1 日存储池迁移完整性审查](/zh/blog/design/pool-migration-integrity-review/)的延续。

**状态：** 已通过提交 [`5dc4bd6a1`](https://github.com/pgsty/silo/commit/5dc4bd6a1d286608783529ba871e5eadd76a03c9) 与 [`8587e061b`](https://github.com/pgsty/silo/commit/8587e061bb7a407e6c98f7020f6475a96500e700) 合入 `main`，将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的下一版 Server 发布。

## 简短回答 {#tldr}

退役一个存储池（`mcli admin decommission start`）必须同时守住两条方向相反的底线：**只要源池磁盘上仍有未迁走的用户数据或未完成的远端冷存（Tier）清理责任，就绝不能误标为 `Complete`**；同时**在真实生产负载下必须能够可靠收敛完成**（包括父子同名嵌套键、客户端并发删除历史版本，以及纠删容错范围内已损坏下线的物理硬盘）。

继承自上游 MinIO 的实现在这两端同时存在缺陷：

1. **同名父对象遮蔽下层子键（`#293`）：** 在底层磁盘上，名为 `a/b` 的对象存为 `<bucket>/a/b/xl.meta`，而名为 `a/b/c` 的子对象存为同一目录下的 `<bucket>/a/b/c/xl.meta`。列举扫描器遇到 `a/b/xl.meta` 时会将 `a/b` 当作叶子对象返回，不再向下递归 `a/b/c`。单趟退役迁走并删掉源端 `a/b/xl.meta` 后直接进入收尾检查，导致 `a/b/c` 被遗留在待下线池中。
2. **并发删除兄弟版本导致已迁移副本滞留源池（`#340`）：** 退役与再平衡均要求 `已迁移版本数 == len(fivs.Versions)` 才清理源池版本。只要业务客户端或生命周期在迁移期间并发删除了同一对象名下的某一个兄弟版本，等式即告失败，**其余已成功复制到目标池的所有版本都会原封不动滞留在源池**。
3. **收尾清空检查的仲裁盲区与坏盘死结：** 上游 `checkAfterDecomBucket` 依赖普通仲裁列举，可能放过在线盘上损坏或分裂的残留 `xl.meta`；但如果改为机械要求“所有槽位磁盘 100% 在线且为空”，一旦老旧存储池中已有 `1`–`2` 块硬盘物理损坏（`errDiskNotFound`，这恰恰是生产环境发起硬件池退役的最常见原因），退役就会永远卡在最后一步报错退出。

修复方案建立了三项协同机制：**按实际完成迁移的候选版本（`candidates`）独立清理源端副本**、**仅在确认源端发生真实物理删除后触发有界重扫以显露被遮蔽子键**，以及**在核验每块在线盘零残留的前提下，允许纠删集读仲裁（`readQuorum`）容错范围内的离线坏盘通过收尾检查**（涉及远端冷存清理所有权的 `FreeVersion` 记录除外，仍保持全盘严格门禁）。

## 定性 {#assessment}

| 方面         | 评估                                                                                                                                                                                                                                                                                                               |
| :----------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **问题性质** | 单趟目录遍历遮蔽子键（`#293`）、全有或全无的兄弟版本清理门禁（`#340`），以及收尾物理清空核验与坏盘容错失衡；均继承自上游 MinIO。                                                                                                                                                                                   |
| **上游来源** | 父子键遮蔽源自上游 `listObjectsToDecommission` 单趟扫描模型；兄弟版本全等门禁 `decommissioned == len(fivs.Versions)` 由上游提交 [`9af6c6cee`](https://github.com/pgsty/silo/commit/9af6c6ceeff5d63dc90c8e0fe356c4d91f8e6795)（`2023-06-21`，[minio/minio#17482](https://github.com/minio/minio/pull/17482)）引入。 |
| **影响范围** | 运行上游 MinIO 或 SILO Server `20261109` 及更早版本、执行 `decommission` 或 `rebalance` 的多存储池（`2+` pools）集群。                                                                                                                                                                                             |
| **故障表现** | 池退役在最终检查阶段报错失败、遗留深层子键或重复滞留已迁移版本；带坏盘的老池无法正常走完退役流程。                                                                                                                                                                                                                 |
{.wide .expand}

---

## 一、上游溯源与根因分析 {#root-cause}

### 1.1 同名父对象的目录遮蔽效应（`#293`） {#nested-keys}

S3 的扁平键空间允许同一个桶内同时存在对象 `logs/2026` 与对象 `logs/2026/11.gz`。但在 `xlStorage` 文件系统布局中，两者共享同一棵目录树：

- `logs/2026` -> `<bucket>/logs/2026/xl.meta`
- `logs/2026/11.gz` -> `<bucket>/logs/2026/11.gz/xl.meta`

在单趟物理列举中，当扫描器在 `<bucket>/logs/2026/` 下发现 `xl.meta` 时，会将其识别为对象条目返回，而不会继续向下遍历其子目录 `11.gz/`。当第一趟退役把 `logs/2026` 迁往新池并从源盘删除 `logs/2026/xl.meta` 后，磁盘上的 `<bucket>/logs/2026/` 才退化为普通目录并显露出里面的 `11.gz/xl.meta`。由于上游 `decommissionBucket` 每个桶只扫描一趟便直接调用 `checkAfterDecomBucket`，下层子键要么导致退役最终检查失败，要么在不足仲裁时被直接遗漏。

### 1.2 兄弟版本“全成才删”的僵化门禁（`9af6c6cee`） {#sibling-gate}

上游在 [`9af6c6cee`](https://github.com/pgsty/silo/commit/9af6c6ceeff5d63dc90c8e0fe356c4d91f8e6795)（`2023-06-21`）中规定，只有当 `decommissioned == len(fivs.Versions)`（或 `rebalanced == len(fivs.Versions)`）时才删除源池版本。

在线生产桶的 `fivs.Versions` 只是列举瞬间的快照。假设某对象列举出 `[v3, v2, v1]` 三个版本，迁移协程顺利把 `v3` 和 `v2` 复制到了目标池（计数为 `2`），恰在此时客户端并发执行 `DELETE ?versionId=v1` 删掉了 `v1`。尽管 `v3`、`v2` 已安全落入新池、`v1` 已被用户主动删除，但因为 `2 != 3`，源池清理被整体跳过，`v3` 与 `v2` 成为留在待退役池上的孤立残留副本。

### 1.3 物理级零残留校验与老池离线坏盘的现实矛盾 {#offline-drives}

为防止不足读仲裁的分裂元数据或损坏 `xl.meta` 逃过高层 S3 列举并在撤池后丢失，收尾核验必须直接检查底层纠删集的物理磁盘目录。然而，如果要求纠删集的**全部 `N` 块盘 100% 在线**，一旦待下线的老旧服务器池已经坏了 1 块盘（例如 8 盘或 16 盘 `EC:4` 中离线 1 块盘，完全处于纠删容错能力之内），管理员就永远无法将该池退役下线。

---

## 二、修复方案：设计思考与充分必要性 {#fix}

提交 [`5dc4bd6a1`](https://github.com/pgsty/silo/commit/5dc4bd6a1d286608783529ba871e5eadd76a03c9) 与 [`8587e061b`](https://github.com/pgsty/silo/commit/8587e061bb7a407e6c98f7020f6475a96500e700) 通过三条严格耦合的不变量一次性解决了上述问题：

1. **按已迁移候选集独立退役源版本（`retireMigratedSourceVersions`）：**
   - 将每一个实际完成目标池写入的版本精确记入 `candidates` 列表，不再与 `len(fivs.Versions)` 快照总数捆绑；即使同键下的兄弟版本被客户端并发删除，已成功迁移的版本仍会在对象锁保护下核实目标池副本与冷存引用后从源池安全清除（`deleteIfMigrated`）。
   - 对远端分层数据已被回收的无主 `FreeVersion` 记录，通过 `retireDrainedFreeVersions` 安全清理；对仍承担远端冷存清理责任的 `FreeVersion` 记录则严格保留。
2. **仅由真实物理移除驱动的有界重扫（`countAbsentMigrationVersions`）：**
   - 一趟桶扫描结束后，**当且仅当本趟确实在源盘上物理删除了至少一个版本或 `FreeVersion`**，才触发下一趟重扫，从而逐层剥离同名父对象并迁移显露出的子键（`a/b/c`）。
   - 严禁把高层逻辑 `NotFound` 当作物理进展：`countAbsentMigrationVersions` 直接在纠删集各在线盘上读取原始 `xl.meta`（`ReadXL`）核实目标版本已真正从所有在线盘消失。若磁盘上存在损坏或分裂且无法迁移的 `xl.meta`，物理移除数为 `0`，循环立即停止而绝不死循环空转，交由收尾核验明确报错；上下文取消（`ctx.Err()`）亦直接原样向上返回错误。
3. **在线盘零容忍 + 读仲裁范围内离线盘容错（`8587e061b`）：**
   - `countAbsentMigrationVersions` 与收尾核验 `checkAfterDecomBucket`（`hasPhysicalMetaOnSet`）逐一检查纠删集中的**每一块在线磁盘**：
     - 只要**任意一块在线盘**上仍存在 `xl.meta`、损坏元数据或非预期目录读取错误，立即拒绝标记完成（哪怕该残留仅存在于单块在线盘上、低于读仲裁）。
     - 对于物理离线的磁盘（`errors.Is(err, errDiskNotFound)`），只要当前纠删集的在线盘数仍满足该集配置的**读仲裁（`online >= readQuorum`）**，允许通过清空校验；一旦离线盘数超出容错阈值（`online < readQuorum`），立即以 `errErasureReadQuorum` 拒绝完成，防止仅存于多数派离线盘上的对象被漏迁。
     - **冷存所有权保持全盘严格门禁：** 在判定是否可以免除远端冷存清理责任的 `readTierHistory` 路径上，继续要求纠删集全部磁盘应答，确保绝不会因为某块离线盘上藏有最后一条 `FreeVersion` 记录而提前误删远端对象或丢失清理凭据。

### 为什么该设计既必要又充分 {#sufficiency}

- **必要性：**
  - 不做父键移除后的重扫，深度 $\ge 2$ 的同名父子键必有遗漏；
  - 若不按底层 `ReadXL` 物理消失而按逻辑 `404` 判定进展，遇到分裂或已过期但未落盘清理的元数据就会陷入无限重扫死循环；
  - 若不在收尾核验中容忍 `len(disks) - readQuorum` 范围内的 `errDiskNotFound`，任何带单块坏盘的老池都无法退役；反之若放宽对**在线盘**残留的检查，则会放走单盘残留元数据。
- **充分性：** 任意最大嵌套深度为 $D$ 的有限桶至多经过 $D + 1$ 趟扫描即可收敛（每趟重扫均对应至少一个磁盘版本的不可逆物理删除），并发删除不再阻碍兄弟版本清理，常规坏盘容错范围内的老池退役恢复顺畅。

---

## 三、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                                        | 工程取舍与运维代价                                                                                                                                                                                        |
| :---------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **源池额外的元数据 `ReadXL` 与目录核验开销**    | 核实版本物理消失（`countAbsentMigrationVersions`）及收尾逐在线盘 `ListDir` 会在待退役池上增加纯元数据 RPC。由于退役本身是后台排空任务且不触碰活跃业务池的数据读写路径，前端 S3 延迟不受影响。             |
| **存在父子同名对象时的多趟扫描**                | 仅当桶内确实同时存在 `p`（对象）与 `p/child`（子对象）且本趟发生了物理移除时才会重扫；纯目录前缀的常规桶排空后不会产生多余扫描。                                                                          |
| **离线坏盘叠加未决 `FreeVersion` 时的故意阻断** | 若待退役池既有离线坏盘，又恰好在该纠删集上存有尚未完成远端冷存清理的 `FreeVersion` 记录，`readTierHistory` 仍会阻止直接丢弃清理记录，宁可阻塞退役等待人工介入或磁盘恢复，也绝不冒误删远端分层数据的风险。 |
{.wide .expand}

## 验证 {#verification}

`cmd/erasure-server-pool-migration-progress_test.go` 完整覆盖了同名父子键逐层显露迁移、并发兄弟版本删除、损坏/分裂元数据有界终止、取消错误传播、单盘离线（`errDiskNotFound`）正常完成退役以及超容错阈值离线盘拦截。另见[裸金属存储池退役操作手册](/zh/operations/deployments/baremetal-decommission-server-pool/#candidate-progress)与[存储池迁移完整性审查](/zh/blog/design/pool-migration-integrity-review/)。
