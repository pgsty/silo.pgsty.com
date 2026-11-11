---
title: "站点复制状态锁：在存储 I/O 与跨站 RPC 之前快照拓扑状态"
linkTitle: "站点复制拓扑快照与死锁消除"
date: 2026-11-11
lastmod: 2026-11-11
author: "PGSTY SILO Maintainers"
summary: >
  为什么在 IAM 自愈、桶自愈、状态采集与同步钩子执行期间持有 SiteReplicationSys.RLock() 会在配置写锁排队时触发 Go sync.RWMutex 永久死锁；以及为什么将状态读锁收敛为纯内存叶节点快照是最小且完整的修复。
tags: [设计, 站点复制, 并发控制, 可用性]
weight: 10
draft: false
url: "/zh/blog/design/site-replication-lock-snapshots/"
---

本文记录 `SiteReplicationSys`（`cmd/site-replication.go`、`cmd/iam-revision.go`、`cmd/site-replication-metadata.go`）中一组继承自上游 MinIO 的递归读锁死锁与共享 Map 数据竞争缺陷及其修复设计，对应 [#341](https://github.com/pgsty/silo/issues/341)。

**状态：** 已通过提交 [`745fbf043`](https://github.com/pgsty/silo/commit/745fbf04376454a3052afb7204856b90cd394f9b)、[`2f228284f`](https://github.com/pgsty/silo/commit/2f228284f31ded34ff34442b239a7e1589caa778) 与 [`ef6efd312`](https://github.com/pgsty/silo/commit/ef6efd3120737506f9dd706e2c8564647b2c5685) 合入 `main`，将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的下一版 Server 发布。`SILO Server 20261109` 及更早版本，以及自 `2022-04-24` 以来的上游原版 MinIO 均受影响。

## 简短回答 {#tldr}

`SiteReplicationSys` 内嵌了一把 `sync.RWMutex`，用于保护内存中的站点复制开关（`c.enabled`）与对端拓扑状态（`c.state`，含 `c.state.Peers`）。在继承自上游 MinIO 的实现中，后台自愈协程（`healIAMSystem`、`healBuckets`、`healUsers`、`healPolicies`、`healUserMappings`、`healGroupMappings`、`healSTSUserMappings`、`healIAMDeletions`）、状态采集（`siteReplicationStatus`）以及在线建桶钩子（`MakeBucketHook`）均在入口处获取 `c.RLock()`，并在持锁期间执行本地磁盘读取、跨站 HTTP RPC，进而调用内部同样会获取 `c.RLock()` 的辅助函数。

Go 标准库的 `sync.RWMutex` 严禁同一协程重入获取读锁：一旦任意写操作（`c.Lock()`——例如 `loadFromDisk` 配置重载、`PeerStateUpdateHandler` 对端状态推送、`SiteReplicationEdit` 编辑或重同步状态更新）到达并排队等待既有读者退出，**后续一切新的 `c.RLock()` 请求都会排在该写者之后阻塞等待**——即便发起第二次 `c.RLock()` 的正是已经持有第一次 `c.RLock()` 的同一个协程。外层读锁等待内层读锁返回，内层读锁等待写锁完成，写锁又等待外层读锁释放，形成无法通过 `ctx` 取消解除的永久死锁，随后整机的 IAM 变更同步、桶元数据同步与站点状态查询全部卡死，直至重启进程。同时，多处对端状态处理路径存在无锁读取或浅拷贝修改 `c.state.Peers` 的并发 Map 读写崩溃隐患。

修复后的自愈、状态查询与钩子路径通过 `cloneState()` 和 `stateSnapshot()` 在内存中复制 `srState` 及其 `Peers` Map，并在存储 I/O、跨站 RPC 和子系统调用前释放 `c.RLock()`。

## 定性 {#assessment}

| 方面         | 评估                                                                                                                                                                                                                                                        |
| :----------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **问题性质** | `sync.RWMutex.RLock()` 同协程重入死锁 + `Peers` Map 浅拷贝/无锁读写竞态；完整继承自上游 MinIO。                                                                                                                                                             |
| **上游来源** | 由上游提交 [`3a6458066`](https://github.com/pgsty/silo/commit/3a6458066331c5c5ed70e41c920fb0046e2e227e)（`2022-04-24`，[minio/minio#14572](https://github.com/minio/minio/pull/14572)，*"Add support for site replication healing"*）引入并沿用至各子模块。 |
| **影响范围** | 启用了多站点复制（Site Replication，`2` 个及以上站点）的所有上游 MinIO（2022 年 4 月后）与 SILO Server `20261109` 及更早版本；未开启站点复制的集群不进入该代码路径。                                                                                        |
| **故障表现** | 节点级永久冻结站点复制相关的全部 IAM 同步、桶创建/配置钩子及管理端复制状态查询（仅重启可恢复）；并发修改站点配置时存在 `concurrent map read and map write` 崩溃风险。                                                                                       |
| **数据安全** | 已落盘的 S3 对象数据不受损坏，但死锁期间跨站 IAM 与桶元数据停止同步。                                                                                                                                                                                       |
{.wide .expand}

---

## 一、上游溯源与死锁调用链剖析 {#root-cause}

上游在 [`3a6458066`](https://github.com/pgsty/silo/commit/3a6458066331c5c5ed70e41c920fb0046e2e227e)（`2022-04-24`）实现站点复制自愈时，采用了“在外层编排函数顶部写 `c.RLock(); defer c.RUnlock()` 以锁定 `c.state.Peers`，再逐一调用各业务同步函数”的模式，而这些下游函数内部又各自对 `c` 加了 `c.RLock()`。

对 `cmd/site-replication.go`、`cmd/iam-revision.go` 与 `cmd/site-replication-metadata.go` 的全图排查确认了四条独立的重入死锁链路及 Map 共享竞态：

1. **IAM 自愈入口与子项同步（`healIAMSystem`）：**
   - `healIAMSystem` 持有 `c.RLock()` 调用 `c.siteReplicationStatus(ctx, ...)` -> `c.SiteReplicationMetaInfo(ctx)` -> 再次请求 `c.RLock()`（第一重死锁点）；
   - 随后依次调用 `healUsers`、`healPolicies`、`healUserMappings`、`healGroupMappings` 与 `healSTSUserMappings`，这五个函数各自持有 `c.RLock()` 并在发现差异时调用 `c.IAMChangeHook(...)` -> `c.isEnabled()` / `c.RLock()`（第二重死锁点）；
   - `healIAMDeletions`（`cmd/iam-revision.go`）同样在持有 `c.RLock()` 期间执行磁盘扫描与跨站 RPC。
2. **存储桶配置自愈（`healBuckets`）：**
   - `healBuckets` 持有 `c.RLock()` 遍历全量本地与远端桶，调用 `c.healBucket(...)` -> `c.healBucketReplicationConfig(...)` -> `c.RLock()` 及 `BucketMetaHook` -> `c.RLock()`。
3. **客户端同步建桶钩子（`MakeBucketHook`）：**
   - `MakeBucketHook` 持有 `c.RLock()` 直接调用 `c.BucketMetaHook(...)` -> `c.RLock()`，一旦赶上后台配置写锁排队，客户端的 S3 `CreateBucket` 请求会当场挂死。
4. **状态采集长耗时持锁与 `Peers` 浅拷贝竞态（`siteReplicationStatus` 与 Peer 处理器）：**
   - `siteReplicationStatus` 在持有 `c.RLock()` 期间并发向所有远端站点发起 HTTP 状态探测并读取本地 IAM / 桶元数据；哪怕没有重入，只要任一对端网络缓慢或超时，写锁 `c.Lock()` 与后续所有业务钩子就会被连带阻塞数十秒；
   - `PeerBucketConfigureReplHandler` 存在嵌套 `RLock`，而多处状态更新路径通过值拷贝 `state := c.state` 后直接修改 `state.Peers[k] = ...`，与并发读者共享底层 Map 哈希表。

### 为什么请求超时与取消（`ctx.Done()`）无法解开死锁 {#why-permanent}

在 Go 运行时的 `sync/rwmutex.go` 实现中，当写者调用 `Lock()` 时，会原子地从 `readerCount` 减去 `rwmutexMaxReaders`（`1 << 30`），使后续所有调用 `RLock()` 的协程直接挂起在信号量 `readerSem` 上等待写者完成。由于协程 A 已经持有了外层 `RLock` 且在等待内层 `RLock` 的 `readerSem`，写者永远等不到活跃读者归零，而阻塞在底层互斥原语上的协程也无法响应 `context.Context` 取消。在开启 `-race` 的确定性测试（`cmd/site-replication-status_test.go`、`cmd/iam-svcacct-replication-snapshot_test.go`）中，只要在两层 `RLock` 之间插入一个写者，毫秒级即可稳定复现永久卡死。

---

## 二、修复方案：为什么叶节点状态快照既必要又充分 {#fix}

### 备选方案对比 {#alternatives}

| 备选思路                                                | 评估结论与取舍理由                                                                                                                                                       |
| :------------------------------------------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. 自研可重入（读优先）读写锁替代 `sync.RWMutex`**    | **否决。** 允许嵌套读锁放行会导致长达数分钟的全量桶/IAM 自愈或慢速跨站超时长期饿死配置写者（`loadFromDisk`、`PeerStateUpdateHandler`），且掩盖跨子系统锁顺序反转风险。   |
| **2. 向所有内部辅助函数透传 `locked bool` 参数**        | **否决。** 涉及跨 3 个文件的二十余个函数，极易在未来新增钩子回调时再次漏传；且依然在持有状态锁期间执行慢速磁盘与网络 I/O。                                               |
| **3. 深拷贝不可变拓扑快照（`stateSnapshot` 叶节点锁）** | **采纳（`745fbf043`、`2f228284f`、`ef6efd312`）。** `c.RLock()` 仅包裹纯内存读取与 `srState` 克隆（不执行 I/O 或子系统回调），所有自愈、探测与钩子在锁外基于值快照运行。 |
{.wide .expand}

### 核心实现机制（`cloneState` 与 `stateSnapshot`） {#implementation}

提交 [`745fbf043`](https://github.com/pgsty/silo/commit/745fbf04376454a3052afb7204856b90cd394f9b)、[`2f228284f`](https://github.com/pgsty/silo/commit/2f228284f31ded34ff34442b239a7e1589caa778) 与 [`ef6efd312`](https://github.com/pgsty/silo/commit/ef6efd3120737506f9dd706e2c8564647b2c5685) 为 `SiteReplicationSys` 确立了统一的锁边界不变量：

1. **独立的拓扑状态快照（`stateSnapshot` / `cloneState`）：**
   `stateSnapshot()` 在 `c.RLock()` 下检查 `c.enabled`，按值复制 `srState`，并用 `maps.Clone` 复制 `Peers` Map，然后释放锁。`srStateV1` 的其余字段为 `Name`、`ServiceAccountAccessKey` 和 `UpdatedAt`；其中没有 `Sites`、`Buckets` 或端点切片。`cloneState()` 使用同样的值复制和 Map 克隆，但不检查开关。
2. **全部存储读取与跨站 RPC 移至锁外执行：**
   - `healIAMSystem`、五个 IAM 子项自愈函数、`healIAMDeletions`、`healBuckets`、`healBucket`、`healBucketReplicationConfig`、`SiteReplicationMetaInfo`、`siteReplicationStatus`、`MakeBucketHook`、`BucketMetaHook` 与 `IAMChangeHook` 全部改为：先取一份 `srState` 值快照，在彻底释放状态锁之后再执行磁盘读取、IAM 查询和远端 HTTP 请求。
   - `siteReplicationStatus` 的请求派发、结果下标、凭据、错误归属、`info.Sites` 和 `info.UpdatedAt` 均使用同一份已获取的拓扑快照；收尾阶段不会重新获取 `c.RLock()` 并把更新的对端拓扑合入这些结果。
3. **写时复制（Copy-on-Write）更新状态：**
   快照读取方持有独立的 `Peers` Map。`SiteReplicationEdit`、`SiteReplicationRemove` 等编辑路径在克隆状态上操作，持久化与重载路径在 `c.Lock()` 下发布状态，使读者持有的 Map 与后续拓扑修改分离。

### 为什么该修改既必要又充分 {#sufficiency}

- **修复范围：** 已改造的自愈、状态查询与对端钩子路径在存储 I/O、跨站 RPC 和子系统调用前释放复制状态锁，消除了这些路径中已复现的嵌套读锁循环；这不代表所有子系统都不可能死锁。
- **必要性：** 只要保留任意一处外层持锁调用（例如仅修掉 5 个 `healUsers` 辅助函数而保留 `healIAMSystem -> siteReplicationStatus -> SiteReplicationMetaInfo` 的嵌套读锁），单次并发配置写入依然足以永久卡死整个自愈协程与后续所有站点复制操作。

---

## 三、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                       | 工程取舍与边界说明                                                                                                                                                                 |
| :----------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **长耗时自愈期间的点时间视图** | 进行中的任务仍可能联系拓扑变更前快照中的对端。结果取决于连通性，以及对端是否仍接受该快照对应的凭据；移除站点本身不保证返回 `403`。下一次快照会看到更新后的拓扑。                   |
| **每次操作的快照内存分配开销** | 快照复制 `srState` 及其 `Peers` Map，复制与分配开销为 `O(站点数)`。临界区仅覆盖这次内存复制，不包含随后的磁盘读取或跨站请求；这里不承诺固定延迟上限。                              |
| **滚动升级兼容性**             | 纯进程内并发控制修复，不改变任何跨节点 RPC 协议或 `.minio.sys` 中的 `srStateFormatVersion1` 磁盘格式，支持平滑滚动升级；建议升级多站点拓扑中的所有节点以消除各节点上已知的锁循环。 |
{.wide .expand}

## 验证 {#verification}

`cmd/site-replication-status_test.go` 与 `cmd/iam-svcacct-replication-snapshot_test.go` 在开启 `-race` 的条件下，使用确定性写锁探针逐一卡入 `healIAMSystem`、五个 IAM 自愈辅助函数、桶自愈、状态采集、并发拓扑变更与请求取消路径，确认全部零死锁、零数据竞争通过。另见 [Server 候选兼容性说明](/zh/compatibility/server/#candidate-after-20261109)与 [IAM 策略重载锁粒度设计（`#251`）](/zh/blog/design/iam-policy-cancellation/)。
