---
title: "复制可靠性：删除完成、MRF 可见性与 resync 取消"
linkTitle: "复制可靠性"
date: 2026-09-09
lastmod: 2026-09-16
author: "冯若航"
summary: >
  SILO #153、#152、#137 的设计与实现归档：修正删除标记 purge 分类，公开有界 MRF 队列的丢弃指标，以任务专属上下文实现可靠的 resync 取消；并记录第二轮 worker 侧 purge 分类与持久 MRF 标记恢复（PR #196），以及第三轮指定版本清除、删除标记自愈与过期排队创建修复。
tags: [设计, 复制, S3, 评审]
weight: 7
draft: false
url: "/zh/blog/design/replication-reliability/"
---

本文记录随 [Server 20260916](/zh/blog/release/silo-20260916/) 交付的三轮复制可靠性修复的问题分析、方案取舍与验收结论：

- **第一轮（[PR #162](https://github.com/pgsty/silo/pull/162)，合并为 [`d1105bbb`](https://github.com/pgsty/silo/commit/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e)）：** 修复 [#153](https://github.com/pgsty/silo/issues/153)、[#152](https://github.com/pgsty/silo/issues/152) 与 [#137](https://github.com/pgsty/silo/issues/137)，分别涉及请求入口的操作分类、后台恢复队列的可观测性以及任务取消生命周期。
- **第二轮（[PR #196](https://github.com/pgsty/silo/pull/196)，提交 [`0c61128d2`](https://github.com/pgsty/silo/commit/0c61128d2)）：** 修复复制工作协程（worker）的删除出口、外层状态聚合与持久化 MRF 标记恢复路径（见[第二轮小节](#second-round)）。
- **第三轮（提交 [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3)、[`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0) 与 [`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb)）：** 修复指定版本清除（purge）的磁盘写回与仲裁语义、删除标记自愈元数据保留，以及清除后排队创建任务的过期复核（见[第三轮小节](#third-round)）。

## 整体判断与系列边界 {#decision}

本系列修复遵循同一工程准则：在拥有对应不变量的最小模块边界内修复已复现的缺陷，复用现有后台恢复机制，并用确定性测试验证收敛。

| 问题 | SILO 中确认的缺陷 | 选定修复 |
| :-- | :-- | :-- |
| #153：删除标记 purge | 单对象 DELETE 将永久删除误判为删除标记复制，导致远端已删除而源端 purge 状态长期停留在 `PENDING` | 按 purge 状态分类，与批量删除、scanner/heal、resync 保持一致 |
| #152：MRF 丢弃不可见 | 队列已设容量上限，但内部丢弃计数未输出到管理接口与监控指标；对象与删除的 worker 路由参数顺序不一致 | 暴露现有丢弃计数、在实际丢弃点输出去重告警、统一 worker 路由键 |
| #137：resync 取消不可靠 | 单个共享 token 无法取消并发的多桶任务；阻塞阶段不响应取消；旧任务收尾可能覆盖新状态 | 为每次运行分配专属 context，按 resync ID 取消，并串行化注册、收尾与状态写回 |

这一系列此前已分别闭合另外两项复制不变量：

- [#136](https://github.com/pgsty/silo/issues/136) / [PR #138](https://github.com/pgsty/silo/pull/138) 修复了**计数完整性**：先接收并累加最后一个结果，再持久化终态，不再依赖一分钟一次的周期性刷新。
- [#139](https://github.com/pgsty/silo/issues/139) 修复了**结果真实性**：仅当目标端本次复制请求实际成功时才计入成功，不再因目标端已有同名对象而误判。
- #137 修复了**取消与资源生命周期**：取消指令下达后，目录遍历器（walker）、工作协程与结果收集器均能及时退出，且已终止的旧任务不会覆盖新任务状态。

复制请求是否有权使用内部特权语义，由[鉴权前不做 I/O，Header 不产生权限](/zh/blog/design/cors-replication-trust/)定义；跨存储池的 Object Lock 权威状态选择由 [#133](https://github.com/pgsty/silo/issues/133) 跟踪并在 #178 中修复，详见[多池对象一致性](/zh/blog/design/multi-pool-object-consistency/)。

## #153：先分清复制删除标记，还是永久删除版本 {#delete-marker}

### 报告与复现为什么不完全相同 {#reported-vs-observed}

原议题报告称生命周期管理（ILM）与复制共同触发了持续的 HTTP 405 请求风暴，并建议将删除标记探测返回的 405 一律视作完成。源码核查与本地复现表明，这一归因并不准确，直接采纳该补丁会破坏删除一致性。

以 [`450dcb848`](https://github.com/pgsty/silo/commit/450dcb8484bc1337deba0cf608cc893a6691d794) 为基线，测试启动两个本地构建的 SILO 服务端实例，配合 `mcli` 与 `minio-go` 客户端进行验证。排查发现：**`mcli` 即使只删除单个对象键，也会调用批量 DELETE 接口；而批量删除的分类逻辑原本就是正确的。** 因此必须直接发送单对象 S3 DELETE 请求才能触发故障路径。

| 检查点 | 修复前的单对象 DELETE | 修复后 |
| :-- | :-- | :-- |
| 目标端对应删除标记版本 | 已删除 | 已删除 |
| 源端 `xl.meta` 中同一版本的 purge 状态 | 仍为 `PENDING`，普通复制状态却被标为完成 | 首次复制后即完成清理 |
| 原始数据版本 | 保留 | 保留 |
| 是否需要等待 scanner 补做清理 | 依赖后续后台恢复 | 无需 scanner 介入 |

如果只检查远端版本是否消失，就会漏掉源端 `xl.meta` 残留的 `PENDING` 状态。本地实验复现了首次 purge 的分类错误、完成状态误写以及一次多余的 `HEAD` 探测；但由于现有的 scanner/heal 与 resync 已经按 purge 状态走正确分支，并不会产生持续的 405 风暴。

### 一处分类修正为什么足够 {#purge-classification}

永久删除一个已有的删除标记时，对象层会同时返回 `DeleteMarker=true` 和非空的 `VersionPurgeStatus`：前者表示被操作版本的对象类型，后者表示当前正在执行永久清除，二者并不矛盾。

旧版单对象删除处理函数仅检查 `DeleteMarker`，直接将版本 ID 填入 `DeleteMarkerVersionID`。复制完成后，工作协程随之更新了普通的 `ReplicationStatus`，而非待完成的 `VersionPurgeStatus`。[`DeleteObject` 处理函数](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/object-handlers.go#L3173)中的修复逻辑如下：

```go
if objInfo.DeleteMarker && objInfo.VersionPurgeStatus.Empty() {
    dmVersionID = objInfo.VersionID
} else {
    versionID = objInfo.VersionID
}
```

这一判断条件与批量删除、scanner/heal 及 resync 的既有逻辑完全对齐，无需调整磁盘存储格式或新增后台恢复任务；历史遗留的 `PENDING` 记录仍由现有的 scanner/heal 清除路径自动回收。

### 为什么不把 405 一律视为成功 {#why-not-405}

对带版本号的对象发送 `HEAD` 请求收到 HTTP 405，仅说明“目标端存在该版本的删除标记”。对于**复制删除标记**，这代表目标端已就位，可按幂等成功处理；但对于**永久删除该版本**，405 恰恰说明目标端的删除标记尚未清除。

如果在收到 `HEAD` 405 时直接写入 `VersionPurgeComplete`，源端就会清理本地元数据，而目标端仍残留本应删除的标记版本。同理，远端返回的 403、405、503 等错误均代表删除未完成，必须按失败重试处理。

追溯提交历史可以看到，仅按 `DeleteMarker` 分类的逻辑源于上游 [2020-11-19 的提交](https://github.com/pgsty/silo/commit/9a34fd5c4a1e1e9f3de050f49c00edea8e32b4b5)。[2023-07-10 的优化](https://github.com/pgsty/silo/commit/e8c98c32464361dd7643b55e028d5735a48ebefc)将入队判断条件从 `dsc.ReplicateAny()` 改为检查返回对象的复制状态与 `PENDING` 清除状态，但保留了仅按 `DeleteMarker` 赋值的分支；[2025-04-02 的提交](https://github.com/pgsty/silo/commit/01447d2438c46cb4658c1e5a13f21f56b7f05a92)又在该处将 `Pending` 枚举替换为 `replication.VersionPurgePending`。

## #152：让有界 MRF 队列的丢弃行为可见 {#mrf}

MRF（Most Recent Failures）队列用于暂存近期失败的复制任务，以便后台快速重试。该队列设有明确容量上限：`mrfSaveCh` 容量为 **100000**，单条任务最大重试次数 `mrfRetryLimit` 为 **3**；当 `RetryCount > mrfRetryLimit` 或通道已满时，队列会淘汰该条目。源对象及其待复制状态仍保留在磁盘上，被内存队列淘汰的条目后续由后台 scanner 扫描并重新发起恢复。

此前的缺陷在于：`TotalDroppedCount` 与 `TotalDroppedBytes` 虽在内部原子递增，却未写入两处管理统计快照，也未注册到 Prometheus v2/v3 指标中。使用容量为 1 的确定性测试夹具可以稳定复现：1 条任务成功入队，20 字节的通道溢出条目与 30 字节的超限重试条目被淘汰后，内部计数为 **2 / 50**，而管理接口仍返回 **0 / 0**。

### 选定的最小改动 {#mrf-fix}

1. 在两处管理统计快照中原子读取并填充现有的丢弃计数。
2. 在 Prometheus v2 与 v3 中注册并导出对应的累计计数器。
3. 在重试超限与 MRF 通道已满这两个**实际丢弃点**记录去重警告，使用固定的日志消息与去重键，避免因计数值变化使日志去重失效。普通工作队列溢出转入 MRF 时并未丢弃任务，不在该处触发丢弃告警。
4. 普通对象复制、自愈与删除路径统一按 `(bucket, objectName)` 计算工作协程哈希，保证同一对象的操作路由到同一个 worker。

| 接口 | 新增指标 |
| :-- | :-- |
| Prometheus v2 | `minio_node_replication_mrf_dropped_operations_total` |
| Prometheus v2 | `minio_node_replication_mrf_dropped_bytes_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_operations_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_bytes_total` |

这组指标统计服务端启动以来的累计丢弃量，重启后归零。**操作数按队列条目计数**，同一对象的多次失败会重复累加；字节数统计已知的对象大小，删除条目记为零字节。运维监控应关注其增长速率，并结合复制积压量与目标站点健康状态综合判断。

本次修复保持原有队列容量与重试次数上限不变，由有界队列控制内存占用，由后台 scanner 承担最终兜底恢复。

## #137：绑定单次运行的 resync 取消生命周期 {#resync}

### 一个共享 token 无法取消一组多桶任务 {#cancel-failure}

原实现在取消 resync 时，仅向全局共享通道写入一个不带任务标识的 token。而一次站点级 resync 可能涵盖多个桶（最多 10 个桶并发执行），分发器（dispatcher）与多个工作协程又会竞争消费同一个通道。这会导致只有单个桶停止、无关任务误消费取消信号，或者残留的 token 错误中止后续发起的新任务。

此外还存在两处阻塞死锁：从目录遍历器 `Walk` 的输出通道读取时未监听取消信号；向已满的 worker 通道发送任务时同样未监听取消信号。一旦 worker 先行退出，dispatcher 就会永久阻塞在无人接收的通道上。同时，`Walk` 直接复用了父级 context，函数提前返回时无法通知底层的遍历协程退出。

状态管理同样存在漏洞：站点级 `updateState` 修改了栈上局部变量却未写回 map；桶级 `Canceled` 分支处理缺失；已取消任务的延迟收尾（finalizer）还可能将状态重新覆盖为 `Completed`。

### 注册、取消与状态使用同一个写入边界 {#cancel-design}

修复后，每个 `resyncBucket` 任务在等待并发槽位**之前**先创建专属的 `context.WithCancelCause` 并完成注册。注册与 `cancelResyncID` 共用 resyncer 的状态互斥锁：

- 注册时校验复制目标仍然有效、resync ID 仍然匹配，并立即检查当前是否已处于取消状态。
- 取消时先将同一 resync ID 下所有处于 `Pending` 或 `Started` 的记录标记为 `Canceled`，随后逐一取消已注册的对应 context。
- 已注册但仍在等待并发槽位的任务能立即收到取消信号；取消发生后才尝试注册的任务也会直接读到已取消状态并退出。
- `Walk`、任务分发、worker 执行与结果发送全程监听当前运行专属的 context；不同 resync ID 之间互不干扰，也不会在通道中残留取消 token。

站点级启动与取消的配置准备阶段由专用操作锁串行化；即使部分桶的目标配置更新失败，已启动任务的取消动作仍会照常执行。桶级收尾函数与进度更新均会核对当前目标与 resync ID，自动忽略已被移除、替换或取消的旧任务结果；站点级状态正确写回 map，`Canceled` 终态不会再被迟到的 `Completed` 覆盖。

### 成功与失败的收尾顺序不同 {#finish-order}

任务收尾必须严格保持 #136 建立的契约——待结果收集协程处理完最后一条结果后再持久化终态：

```text
正常完成：关闭 worker 输入 → 等待 worker 退出 → 排空结果通道
          → 持久化终态 → 归还并发槽位 → 取消专属 context 并注销

失败/取消：先取消 context 解除阻塞 → 等待 worker 与结果收集器退出
          → 持久化对应终态 → 归还并发槽位 → 注销
```

如果在正常完成路径上先取消 context 再等待 worker，尚未处理完的任务就会被提前中断，导致原本成功的运行变成 `Failed`。最终实现通过单一 `defer` 调用 `finish`，按固定顺序完成清理，无需额外引入 `sync.Once`。

借助 `WithCancelCause`，代码能够区分用户主动取消与服务关闭导致的父级 context 中断：用户取消记录为 `Canceled`；父级中断则不会将未跑完的任务误记为 `Completed`；若任务在等待并发槽位期间遇到服务关闭，则保留原有的 `Pending` 状态，以便重启后自动恢复。

### 取消终态与恢复任务也必须受保护 {#terminal-and-recovery}

在检查 context 状态与落盘保存终态之间仍可能并发到达取消请求。因此 `markStatus` 在持有状态锁时，若发现内存状态已变为 `Canceled`，即使收尾流程此前计算出的结果是 `Completed`，也必须保持 `Canceled`；同时拒绝旧 resync ID 覆盖新任务的状态。

若某个桶在站点级取消到达前已完成并落盘，最终状态会记录为该桶 `Completed`、站点整体 `Canceled`。锁内状态检查确保**已进入 `Canceled` 状态的任务不会被迟到的完成信号改写为 `Completed`**。

在重启恢复路径上，`loadResync` 原本在启动后台恢复协程后立即执行 `defer cancel()`。核查 SILO 的分布式共享锁实现确认，该 `cancel()` 会直接终止合并后的 leader context，导致恢复协程被立即取消。修复方案引入 `WaitGroup`，保持该 context 存活至所有恢复协程退出；当节点失去 leader 身份时，底层 context 仍会按预期触发取消。此外，从磁盘加载历史状态时也不会覆盖内存中更新的启动或取消状态。

## 设计审查与复杂度取舍 {#review}

针对基线复现与备选方案的评审结论汇总如下：

| 方案或评审意见 | 最终判断 |
| :-- | :-- |
| 将 purge 的 405 探测响应直接判为完成 | 否决：删除标记存在不代表永久删除已完成 |
| 为 MRF 新增持久化的退避重试调度器 | 不引入：现有队列与后台 scanner 已提供完整恢复链路，实际缺口在于可观测性 |
| 向共享通道发送更多取消 token | 否决：无法解决按 ID 路由、多桶广播及后续任务串扰问题 |
| 为取消操作维护独立的墓碑注册表 | 不引入：在同一把状态锁下结合目标状态与 resync ID 即可闭合注册竞态 |
| 为每次运行分配专属 context 并改造阻塞点 | 采用：满队列死锁与遍历器泄漏均有确定性复现用例 |
| 用 `sync.Once` 保护 `finish` | 收窄：合并为单一 `defer` 调用点后，无需额外引入 `sync.Once` |
| 等待恢复任务结束后再释放 leader context | 采用：SILO 的 leader context 取消会立即生效，需通过 `WaitGroup` 延长生命周期并补齐失主测试 |

此外，低频的 resync 启动操作在状态锁内完成配置读写，与终态落盘保持同一锁边界；活跃任务注册表直接复用包含 `resyncBefore` 的 `resyncOpts` 作为键。

## 验收证据与可复验入口 {#evidence}

所有修复均遵循“先在未修改基线上编写失败回归测试，再提交生产修复”的流程。新增测试直接驱动生产环境处理函数、纠删码存储层、Prometheus 指标注册表与 `resyncBucket` 完整流程。

| 验收范围 | 结果与证据 |
| :-- | :-- |
| 单对象删除 purge | 在单盘（ErasureSD）与多盘纠删码（Erasure）下验证源端与目标端同步清理；覆盖存量 `PENDING` 恢复、删除标记幂等，以及 403/405/503 错误处理 |
| MRF 可观测性 | 容量为 1 的队列溢出与重试超限测试；校验管理接口 JSON、Prometheus v2/v3 注册计数器的类型与数值、对象与删除的 worker 路由一致性 |
| resync 取消 | 使用 `testing/synctest` 覆盖 `Walk` 阻塞、满 worker 队列、主动取消、排队期取消、跨 ID 隔离、后续任务启动、终态并发竞争、过期 ID 忽略、槽位释放与 leader 恢复 |
| 本地完整套件 | `go test ./... -count=1 -timeout=30m` 全量通过（共 50 个含测试的包） |
| 并发与重复测试 | 复制相关定向 `-race` 测试通过；取消回归用例连续运行 100 次全部通过 |
| 工具与契约守卫 | 本地编译、`go vet`、静态检查、生成文件检查、`rebrand-guard` 与 `git diff --check` 全部通过 |
| 双实例联调 | 基于本地源码构建两个服务端实例，直接发送单对象 DELETE：目标端删除标记消失，源端 `xl.meta` 完成清理，原始数据版本完整保留 |
| 远端 CI | PR 八项检查通过；合入主干后 Go CI 六项任务与 VulnCheck 全部通过 |

固定提交上的回归测试文件：[删除标记](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-delete-marker_test.go)、[MRF 可见性](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-mrf-observability_test.go)、[取消生命周期](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-resync-cancel_test.go)。复现与验证命令：

```bash
go test ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test -race ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test ./cmd -run '^TestResyncCancel' -count=100
go test ./... -count=1 -timeout=30m
```

| 证据点 | 精确标识 |
| :-- | :-- |
| 修复前基线 | `450dcb8484bc1337deba0cf608cc893a6691d794` |
| 最终 PR head | `66fe61ff65c83d68b74baa637a11623015c7aa21` |
| 合并主干 | `d1105bbb3d4a0afa33b3a4ac11b821235038ed0e` |
| PR Go CI | [34320440012](https://github.com/pgsty/silo/actions/runs/34320440012) |
| 主干 Go CI | [34321319278](https://github.com/pgsty/silo/actions/runs/34321319278) |
| 主干 VulnCheck | [34321319274](https://github.com/pgsty/silo/actions/runs/34321319274) |

## 后续维护原则 {#follow-up}

复制与 resync 的回归测试需分别断言五项独立不变量：操作类型判定准确、队列淘汰可观测、单对象复制结果真实、终态计数完整、取消后协程与并发槽位完全释放。

## 第二轮（2026-09-16）：worker 侧 purge 分类与持久 MRF 恢复 {#second-round}

第一轮在 **HTTP 请求入口**修正了删除分类（#153）、公开了 MRF 队列丢弃计数（#152）并闭合了 resync 取消生命周期（#137）。第二轮——[PR #196](https://github.com/pgsty/silo/pull/196)，提交 [`0c61128d2`](https://github.com/pgsty/silo/commit/0c61128d2)，集成验证记录 `aea3882c9`——深入到后台复制链路，修复了 **worker 自身的删除出口**、外层状态聚合，以及删除标记的**持久化 MRF 恢复路径**。

### 第二轮排查出的遗留缺陷 {#second-round-defects}

- **旧形态任务被整体跳过。** 当任务的 `VersionID` 为空、`DeleteMarkerVersionID` 非空、目标端创建状态为 `COMPLETED` 且清除（purge）状态为 `PENDING` 时，目标侧的“创建已完成”早退分支会直接跳过该任务，导致永不发出 DELETE 请求。
- **仅修复内层目标函数会导致外层状态误报。** 外层状态聚合原本以 `VersionID` 与创建状态为键；若仅放行内层函数，执行失败的旧形态清除任务会被外层汇总为 `COMPLETED`，触发 `ObjectReplicationComplete` 事件并**跳过持久化 MRF 入队**。
- **持久化 MRF 恢复路径丢弃了所有删除标记的 405 响应。** 重放磁盘 MRF 中针对删除标记版本的条目时，本地读取会返回真实的删除标记元数据与 `MethodNotAllowed` 错误；原错误处理分支直接将其丢弃，导致删除标记无法通过持久化 MRF 恢复。
- **状态覆盖与重复发送。** 失败的清除操作会覆盖已成功的 resync 标记，已完成的清除操作被重复发送，而尚未就绪的 `HEAD` 探测也会无条件覆盖创建状态。
- **多目标空状态解析错误会破坏创建元数据。** 当磁盘上的删除标记仅含创建元数据、而内存任务携带清除状态时，正则解析会将两个空的目标状态误判为 `Pending`；随后的已删除标志守卫会将整个创建元数据块重写为带新时间戳的空记录。

根因在于三处缺失：首先，worker 缺少**任务级**的清除判定（社区 PR [#184](https://github.com/pgsty/silo/pull/184) 提出的按单目标判定谓词存在缺陷，复合清除状态经该分支处理后永远无法收敛为 `COMPLETE`，但 Julien Laurenceau 的问题排查与提案为本轮修复提供了重要参考）；其次，MRF 恢复路径缺少识别**合法删除标记 405 响应**的准入条件；最后，删除任务未携带重试计数，导致 `mrfRetryLimit` 上限在删除路径上形同虚设。

### 第二轮修复方案 {#second-round-fix}

- **统一出口的清除判定。** 新增 `isVersionPurge()`（当 `VersionID` 非空，或 `DeleteMarkerVersionID` 非空且携带复合清除状态时为真），同时驱动内层单目标执行函数与外层状态聚合。清除路径退出时仅更新 `VersionPurgeStatus`，并将 `ReplicationStatus` 留空（存储层将其视作“不修改创建复制状态”）。
- **三字段清空守卫。** 在清除路径上显式清空创建复制相关的三个状态字段，彻底阻断多目标空状态在落盘时触发正则误判的可能。
- **发送规范的永久删除请求。** 清除操作统一携带显式 `versionId` 与 `ReplicationDeleteMarker=false`，不再执行前置 `HEAD` 就绪探测（权限校验直接由 DELETE 请求完成），同时防止网络丢包重试在无版本回退路径上**意外重建删除标记**。
- **MRF 恢复的 405 身份校验。** 重放 MRF 收到 `MethodNotAllowed` 时，仅当返回对象确系删除标记、桶名/对象名/版本号完全匹配且修改时间非零时，才重新入队调度恢复。
- **有界重试预算。** 删除任务新增重试计数器，在全部三个持久化 MRF 入口（聚合失败、获取锁失败、内存队列满回退）递增并受 `mrfRetryLimit` 约束；超过上限淘汰后，仍可由后台 scanner 重新发起自愈。
- **审计与事件状态兼容映射。** 仅在统计与事件通知边界将 `COMPLETE` 映射为 `COMPLETED`，复用既有常量定义。

### 405 的准确含义 {#second-round-405}

对于**创建操作**（将删除标记复制到目标端），对目标标记版本发起 `HEAD` 收到 405 意味着目标标记*已经存在*，可视作幂等完成。对于**清除操作**（永久删除指定版本），MRF 恢复阶段探测本地版本收到带完整标记身份的 405 意味着*本地标记仍在、尚待清除*；清除操作本身的成败完全取决于远端 DELETE 请求的响应，DELETE 返回 403、405 或 503 均计为真实失败。空版本或 `null` 版本的标记返回的是 `ObjectNotFound` 而非 405，不会进入该分支。

### 实现边界 {#second-round-limits}

旧形态内存任务不会跨重启持久化，当前代码也已不再生成该形态，保留其兼容分支主要作为防御性保护。未配置远端客户端的目标站点仍仅记录日志；单目标级 resync 覆盖部分清除状态属于既有行为，不在本轮修改范围内。同系列可靠性修复中的标签排序与副本元数据归一化，另见[复制标签排序](/zh/blog/design/replicated-tag-ordering/)与[副本元数据归一化](/zh/blog/design/replica-metadata-normalization/)。

## 第三轮（2026-09-16）：指定版本清除、标记 heal 与过期的排队创建 {#third-round}

第二轮确保了 worker 的清除出口如实反映执行结果。第三轮——提交 [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3)、[`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0) 与 [`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb)，随 [Server 20260916](/zh/blog/release/silo-20260916/)（`40220bd836cbd066ca424fa4dc5dbb90057fb55a`，配合 `silo-pkg` `6f27ee6`）发布——进一步修复了指定版本清除在底层磁盘上的写回与仲裁逻辑，以及排队中的创建任务在版本清除之后乱序执行的问题。该问题由三站点容器集群测试（三个站点，每站点 4 进程 16 盘，EC 12+4）暴露：一个已被永久清除的删除标记在两个目标站点上死灰复燃，而源站点却仍返回正常的数据版本。

### 第三轮排查出的遗留缺陷 {#third-round-defects}

- **清除操作反而会在缺盘上创建待删标记。** 查找层为了标记版本可见性，将待清除版本打上了已删除标志；而清除写回路径把该标志当成了“写入删除标记”的落盘指令。结果原本没有该标记的磁盘反而被写入了新标记，使清除了一半的磁盘组在反复重试中来回翻转、无法收敛。
- **过早确认版本缺失。** 读取路径只要看到半数磁盘报告版本不存在，就判定该版本已缺失；导致清除重试直接返回 204 成功，而实际上仍有最多一半的磁盘残留着该删除标记。
- **自愈（heal）删除标记会抹掉其复制元数据。** 自愈路径在重建删除标记时传入了空的元数据映射。修复后的删除标记丢失了原有的复制与清除状态，重新退化为待复制状态，随后被当作全新创建的标记再次复制到远端。
- **排队中的创建任务在清除完成后延迟执行。** 针对处于 pending 状态的删除标记，每次 GET/HEAD/LIST 请求、后台 scanner 以及 MRF 都会入队一个携带当时标记快照的创建任务；来自多个前端节点的任务在单对象复制锁前排队串行执行。在复现时序中，用户的永久清除请求先在两个目标站点完成确认；约 85 毫秒后，排队中的创建任务携带相同的 `VersionID` 与原始修改时间抵达两个目标站点。由于目标站点此时已无该版本，且请求报文中没有任何字段能区分“首次创建”与“过期的乱序创建”，两个目标站点各自重新创建了 16/16 份删除标记，而源站点为 0/16 份。

### 第三轮修复方案 {#third-round-fix}

- **单点判定清除意图（`isVersionPurge`）。** 仅当请求携带合法的显式 `VersionID`，不含创建删除标记、前缀匹配、数据迁移、免版本控制、过期或生命周期转换选项，且复制状态为“清除已完成”、“无复制状态”或“可信副本请求”之一时，才判定为永久清除。清除路径绝不设置创建删除标记的落盘标志，并将“磁盘已完成物理删除”与“磁盘确认版本不存在”两类响应合并计入成功票数。仅当实际删除了磁盘上存储的删除标记时，响应才标识为删除标记；此前清除仍处于 pending 状态的数据版本则按正常数据版本返回。
- **确认版本缺失必须满足写仲裁多数（`N/2+1`）。** 当重试清除在查找阶段发现版本缺失时，会重新读取每一块磁盘。若明确报告“版本不存在”的磁盘不足 `N/2+1` 块，则按写仲裁不足返回失败；只要任意磁盘仍残留副本，就触发 MRF 自愈。离线、损坏或读取报错的磁盘绝不计入“版本不存在”票数。多存储池层对查找阶段跳过的存储池执行同样的多数派核查，副本接收端则按版本号跨存储池解析清除请求。
- **自愈删除标记保留完整持久化元数据。** 自愈路径完整复制删除标记原有的持久化元数据表，仅剔除自愈、数据迁移与分层相关的临时操作键。类型化状态生成逻辑仅用于不带存量元数据的新建写入，且不再伪造时间戳。
- **发送前在复制锁内复核源端状态。** 删除复制 worker 在向远端发送创建请求前，先在对象复制锁内重读源端对应版本。若该版本已不存在、不再是删除标记或已进入清除流程，则判定该排队任务已过期并直接丢弃，不修改源端状态；若重读因临时故障无法得出确定结论，则交由 MRF 重试，而不直接视为版本缺失。

### 证据与边界 {#third-round-limits}

在两组三站点分批故障恢复测试（涵盖源站点重启与不重启、单个目标站点分两批恢复上线）中，集群均在约 15 秒内完成收敛，并在随后 450 秒的观测窗口内保持完全一致。过期排队创建乱序复现用例在未合入修复的 `main` 分支上稳定复现失败，合入修复后在单盘与 16 盘纠删码夹具上全部通过。

源端复制锁内的发送前复核无法拦截已经发往网络的数据包，也无法拦截其他站点重放的创建请求；彻底消除这一跨站点乱序窗口需要在接收端持久化清除记录或引入单调序号，已由 [#217](https://github.com/pgsty/silo/issues/217) 独立跟踪。此外，若某次清除刚达成多数派确认、所有服务端进程随即同时崩溃，此前离线磁盘上残留的少数派副本最多会保留七个后台扫描周期，在此期间所有前端读取仍一致返回正确的数据版本。
