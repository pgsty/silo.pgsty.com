---
title: "复制可靠性：删除完成、MRF 可见性与 resync 取消"
linkTitle: "复制可靠性"
date: 2026-09-09
lastmod: 2026-09-09
author: "冯若航"
summary: >
  SILO #153、#152、#137 的设计与决策归档：区分外部报告与本地复现，修正删除标记 purge 分类，公开有界 MRF 队列的丢弃信息，以任务自有 context 完成可靠取消，并记录 Fable 5.1 Max 评审、被否决的方案和最终验收证据。
tags: [设计, 复制, S3, 评审]
weight: 7
draft: false
url: "/zh/blog/design/replication-reliability/"
---

本文记录 [#153](https://github.com/pgsty/silo/issues/153)、[#152](https://github.com/pgsty/silo/issues/152)、[#137](https://github.com/pgsty/silo/issues/137) 的分析、方案取舍、评审与实施结论。三者属于同一组复制可靠性问题，但分别发生在操作分类、后台恢复可见性和任务生命周期上，不能靠一个统一的重试补丁解决。

> **截至 2026-09-09：** [PR #162](https://github.com/pgsty/silo/pull/162) 已合并为 [`d1105bbb`](https://github.com/pgsty/silo/commit/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e)，三个 issue 均已关闭。被测 PR head 的八项检查与合并后主干的 Go CI、VulnCheck 全部通过。<br>
> **评审：** 与环境中的 Claude Code Fable 5.1 Max 商榷方案，并在实施后复核；最终结论为 **GO**。<br>
> **交付边界：** 本轮完成代码、测试和主干合并，没有创建 Server tag 或正式 release。本文不据此宣称现有软件包、镜像或生产部署已包含修复。

## 整体判断与系列边界 {#decision}

选择方案的标准是：在错误发生的最小边界修复已复现的不变量，保留现有恢复机制，用确定性测试证明它能够收尾。增加复杂度必须有具体反例支持。

| 问题 | 当前 SILO 中确认的缺陷 | 选定修复 |
| :-- | :-- | :-- |
| #153：删除标记 purge | 单对象 DELETE 把永久删除误归类为删除标记复制，远端已删而源端 purge 仍为 PENDING | 按 purge 状态分类，与批量删除、scanner/heal、resync 对齐 |
| #152：MRF 丢弃不可见 | 队列已有限额，但内部丢弃计数没有进入管理接口和监控；对象与删除的 worker 参数次序不一致 | 输出现有计数、在实际丢弃处记录去重警告、统一 worker 分配 |
| #137：resync 取消不可靠 | 单个共享 token 无法取消多个任务；阻塞阶段不响应取消；旧任务可能覆盖终态 | 每个运行拥有 context，按 resync ID 取消，并约束注册、收尾和状态写回 |

这一系列此前已经区分了三个容易混淆的概念：

- [#136](https://github.com/pgsty/silo/issues/136) / [PR #138](https://github.com/pgsty/silo/pull/138) 修复的是**计数完整性**：先接收并应用最后一个结果，再持久化终态，不能等一分钟后的周期刷新补齐。
- [#139](https://github.com/pgsty/silo/issues/139) 修复的是**结果真实性**：目标对象存在，不代表这次更新成功；必须依据目标的实际复制结果统计成功和失败。
- #137 修复的是**取消与资源生命周期**：任务能够停止，walker、worker 和结果消费者能够退出，旧任务不能污染新任务状态。本次延续前两项契约，没有另建一套计数机制。

复制请求是否有权使用内部语义，属于此前的 [CORS 与复制信任边界](/zh/blog/design/cors-replication-trust/)；跨池 Object Lock 的权威状态选择仍由 [#133](https://github.com/pgsty/silo/issues/133) 单独跟踪，截至本文归档时仍未关闭。本次三个 issue 关闭不等于所有复制问题都已解决。

正式验收对象是维护中的 `pgsty/silo` 及配套的 Console、mcli、silo-pkg。上游 MinIO/MC 兼容性保持尽最大努力；不能直接把上游报告的机制或实验结果当成当前 SILO 的实测结论。

## #153：先分清复制删除标记，还是永久删除版本 {#delete-marker}

### 报告与复现不完全相同 {#reported-vs-observed}

原 issue 描述 ILM 与复制共同触发持续的 HTTP 405 请求风暴，并建议把删除标记的 405 探测一律作为完成。当前 SILO 的源码和实测不支持直接采用这个解释和补丁。

基线为 [`450dcb848`](https://github.com/pgsty/silo/commit/450dcb8484bc1337deba0cf608cc893a6691d794)。实验使用两个本地构建的 SILO Server、独立临时数据目录，以及维护中的 mcli / minio-go 客户端。一个关键发现是：**mcli 即使只删除一个 key，也会走批量 DELETE；这个路径原本就是正确的。** 因而必须另发单对象 S3 DELETE 才能覆盖错误入口。

| 检查点 | 修复前的单对象 DELETE | 修复后 |
| :-- | :-- | :-- |
| 目标端对应删除标记版本 | 已删除 | 已删除 |
| 源端 `xl.meta` 中同一版本的 purge 状态 | 仍为 PENDING，普通复制状态却已完成 | 首次复制后完成清理 |
| 原始数据版本 | 保留 | 保留 |
| 是否需要等待 scanner 补做清理 | 需要后续恢复 | 本次验证无需 scanner 帮助 |

仅观察“远端版本消失”会误判修复成功，必须同时检查源端 metadata。当前复现证明的是首次 purge 的分类与完成状态错误，以及一次多余探测；**没有复现原报告的持续 405 风暴或请求量数字**。现有 scanner/heal 与 resync 已按 purge 状态选择正确路径，不能把它们描述成每轮必然重复错误探测。

### 一处分类修正为什么足够 {#purge-classification}

删除一个现有 delete marker 时，对象层可以同时返回 `DeleteMarker=true` 和非空 `VersionPurgeStatus`。前者说明被操作的版本是什么，后者说明现在要做什么，二者并不冲突。

旧的单删 handler 只看 `DeleteMarker`，把版本放入 `DeleteMarkerVersionID`。复制完成因此更新了普通 `ReplicationStatus`，而不是应当完成的 purge 状态。最终条件是：

```go
if objInfo.DeleteMarker && objInfo.VersionPurgeStatus.Empty() {
    dmVersionID = objInfo.VersionID
} else {
    versionID = objInfo.VersionID
}
```

这与其他生产者已有的分类一致，修复落在 [DeleteObject handler](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/object-handlers.go#L3173)。不需要改变存储格式、放松 replica 删除保护，也不需要新增恢复任务；存量 PENDING 继续由现有 scanner/heal 的 purge 路径回收。

### 为什么不把 405 一律视为成功 {#why-not-405}

版本化 HEAD 的 405 可以证明“目标上这个删除标记存在”。对**复制一个删除标记**来说，这可以是幂等完成；对**永久删除该版本**来说，它恰好说明仍有工作要做。

若仅因 405 就写入 `VersionPurgeComplete`，源端可能清理 metadata，而目标端仍保留本该删除的版本。最终实现保留原有 405 语义；真正的远端 403、405、503 等失败也不能被伪装成删除成功。

历史定位显示，按 delete marker 分类的代码可追溯到上游 [2020-11-19 的提交](https://github.com/pgsty/silo/commit/9a34fd5c4a1e1e9f3de050f49c00edea8e32b4b5)。[2023-07-10 的优化](https://github.com/pgsty/silo/commit/e8c98c32464361dd7643b55e028d5735a48ebefc) 把调度判断从 `dsc.ReplicateAny()` 改为对象返回的复制/PENDING purge 状态，同时保留了只看 `DeleteMarker` 的分类。[2025-04-02 的提交](https://github.com/pgsty/silo/commit/01447d2438c46cb4658c1e5a13f21f56b7f05a92) 在此处只是把 `Pending` 迁移为 `replication.VersionPurgePending`，并非首次引入该调度条件。以上是源码谱系定位，不是跨所有历史版本的二分验证，也不能据此给外部报告的整个请求风暴确定引入日期。

## #152：让已有有界队列的丢弃行为可见 {#mrf}

MRF（Most Recent Failures）用于记录近期失败、等待后台再次处理的复制任务。它并非没有容量限制：`mrfSaveCh` 上限为 **100000**，`mrfRetryLimit` 为 **3**；代码在 `RetryCount > mrfRetryLimit` 或保存通道已满时放弃该条队列记录。

源对象及其待复制状态仍在，丢弃队列条目不等于源数据丢失。不过后续恢复依赖 scanner，原本快速的重试可能退化为等待扫描，无法据此承诺固定的恢复时延。

真正的缺陷是 `TotalDroppedCount` / `TotalDroppedBytes` 在内部递增，却没有复制进两处对外统计快照，也没有 v2/v3 Prometheus 指标。容量为 1 的回归夹具能稳定证明：一个条目成功入队，20 字节的溢出条目和 30 字节的超限条目被丢弃；内部为 **2 / 50**，管理接口却显示 **0 / 0**。

### 选定的最小改动 {#mrf-fix}

1. 两处管理统计快照原子读取现有丢弃计数。
2. v2 与 v3 注册并加载累计 counter，文档同步说明计量含义。
3. 在重试超限、MRF 通道已满这两个**实际丢弃点**记录去重警告，使用固定的消息和 key，避免计数变化绕开去重而刷屏。普通 worker 队列转交 MRF 还不等于丢弃，不在那里增加警告。
4. 正常对象、heal 和删除路径统一以 `(bucket, objectName)` 选择 worker，恢复同一对象的分配一致性。

| 接口 | 新增指标 |
| :-- | :-- |
| Prometheus v2 | `minio_node_replication_mrf_dropped_operations_total` |
| Prometheus v2 | `minio_node_replication_mrf_dropped_bytes_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_operations_total` |
| Prometheus v3 | `minio_replication_mrf_dropped_bytes_total` |

它们是自 Server 启动以来的累计值，重启后重置。**操作数统计条目而非唯一对象**，同一对象可重复计数；字节数统计已知大小，删除条目按零字节计算。它们既不是数据丢失量，也不是完整积压量，运维应关注增量并结合复制积压与目标健康状况判断。

本轮没有扩大队列、提高重试次数、增加持久化重试调度器或另建退避框架。已有上限继续限制内存成本，scanner 继续承担最终恢复；本次解决的是“发生了什么却看不到”，而不是许诺任意故障下的恢复时限。

## #137：把取消作为一次运行的生命周期 {#resync}

### 一个 token 无法取消一组任务 {#cancel-failure}

原实现把一个未按任务标识区分的 token 放进共享 channel。一个站点 resync 可以对应多个桶，最多有 10 个桶任务并发；dispatcher 和 worker 又竞争消费同一个 token。结果可能只有一个桶停止、无关任务消费取消，或残留 token 影响后来任务。

还有两个独立的阻塞点：裸读 Walk 输出不检查取消；向已满的 worker 通道发送也不检查取消。worker 退出后，dispatcher 可能永久堵在无人接收的通道上。Walk 沿用父 context，函数提前返回时也无法结束自己的 walker。

状态层另有配套缺陷：站点 `updateState` 修改局部值却未写回 map；桶级 Canceled 缺少完整处理；旧 finalizer 可能把取消状态覆盖为 Completed。

### 注册、取消与状态使用同一个写入边界 {#cancel-design}

每个 `resyncBucket` 创建自己的 `context.WithCancelCause`，在等待并发槽位**之前**注册。注册和 `cancelResyncID` 共用 resyncer 的状态锁：

- 注册时校验目标仍存在、resync ID 仍匹配，并读取当前取消状态。
- 取消时先把同 ID 的 Pending / Started 标为 Canceled，再取消全部已注册的对应 context。
- 先注册、尚在排队的任务能收到取消；先取消、后注册的任务也会看到已取消状态。
- Walk、dispatcher、worker 和结果发送共同观察本次运行的 context；无关 ID 不受影响，也没有可被后来任务消费的残留 token。

站点 start/cancel 的配置准备由专用操作锁串行化。即使目标配置循环部分失败，取消运行中任务的动作仍会执行。桶级 finalizer 和计数更新同时检查当前目标与 resync ID，忽略已删除、已替换或已取消运行的迟到结果；站点状态实际写回 map，Canceled 不再被后到的 Completed 覆盖。

### 成功与失败的收尾顺序不同 {#finish-order}

这里必须保留 #136 建立的“结果消费者结束后再持久化”契约：

```text
正常完成：关闭 worker 输入 → 等 worker 结束 → 排空结果
          → 持久化终态 → 归还槽位 → 取消自有 context 并注销

失败/取消：先取消 context，解除阻塞 → 等 worker 和结果消费者退出
          → 持久化相应终态 → 归还槽位 → 注销
```

若正常完成时先 cancel，再等待 worker，尚未处理的工作可能被丢弃，原本成功的任务会变成 Failed。最终代码只在一个 defer 中调用一次 `finish`，利用 defer 顺序完成收尾，因此不需要额外 `sync.Once`。

`WithCancelCause` 区分用户主动取消与父 context 中断：用户取消成为 Canceled；收尾时若观察到父 context 中断，不能把中断的运行记为 Completed；仍在等待槽位时发生关机则保留原有 Pending 状态，供重启恢复。

### 取消终态与恢复任务也必须受保护 {#terminal-and-recovery}

context 检查与终态保存之间仍可能发生取消。因此 `markStatus` 在锁内遇到已有 Canceled 时必须保存 Canceled，即使 finalizer 先前算出了 Completed；旧 resync ID 也不能覆盖新运行。

这不是跨文件事务。如果一个桶已经先于取消完成并持久化，随后发生的站点取消可能保留“桶 Completed、站点 Canceled”的不同记录；这表示完成发生在取消之前。保证的是**已经被取消的运行不能被迟到的完成结果翻回 Completed**，不是抹掉取消前已经完成的工作。

恢复路径的 `loadResync` 原本启动 goroutine 后立即执行 `defer cancel()`。核对 SILO 实际 shared-lock 实现后确认，这里的 cancel 确实会结束合并后的 leader context，并非空操作。最终用一个 WaitGroup 让该 context 活到恢复任务退出；失去 leader 时仍按原 context 取消，不能换成全局 context 来绕过 leader 约束。加载磁盘状态时也不能覆盖内存中较新的 start/cancel 状态。

## 与 Fable 的评审和复杂度取舍 {#review}

评审实际使用环境中的 Claude Code，模型参数为 `claude-fable-5-1[1m]`、`--effort max`。先提供基线复现和最小方案，形成三项执行共识；实施后再提供最终补丁与验证结果，获得 GO。这个结论建立在代码和证据上，而不是仅凭模型赞同。

| 方案或评审意见 | 最终判断 |
| :-- | :-- |
| 对 purge 的 405 探测直接判完成 | 否决：marker 存在不是永久删除完成的证据 |
| MRF 新增有界重试、退避与持久化调度层 | 本轮不引入：现有队列与 scanner 已提供恢复机制，已证实缺口是可见性 |
| 增加共享 cancel token 数量 | 否决：仍不能保证身份路由、广播和后来任务隔离 |
| 为取消增加独立墓碑注册表 | 不需要：已有目标状态与 resync ID 在同一锁下足以关闭注册竞争 |
| 每个任务持有 context，并使阻塞操作可取消 | 保留：满队列死锁与 walker 泄漏已有确定性复现 |
| `finish` 使用 `sync.Once` | 初评要求防止双重关闭；最终改成唯一 defer 调用点，复核认可省去 Once |
| 恢复任务等待后才释放 leader context | 初评要求先核实是否必要；实际 SILO cancel 有效，故保留 WaitGroup，并补测失去 leader 的行为 |

终审还接受了两个实现边界：罕见的 resync start 管理操作在状态锁内完成配置读写，与现有终态保存方式一致；活动注册表复用包含 `resyncBefore` 的 `resyncOpts` 作为 key，现有调用传递相同内存值，没有复现身份不一致。若未来改变时间值重建或任务恢复的方式，应重新核对身份等价性，而不是未经证据立即增加另一套注册机制。

## 验收证据与可复验入口 {#evidence}

先在未改生产代码的基线上加入回归测试，确认错误能够失败，再实施修复。新增用例直接覆盖生产 handler、真实 erasure 存储、实际指标注册和 `resyncBucket`，不是只验证抽出来的同构 helper。

| 验收范围 | 结果与证据 |
| :-- | :-- |
| 单删 purge | ErasureSD 与 Erasure 均覆盖源/目标清理；覆盖存量 PENDING 恢复、删除标记幂等，以及真实 403/405/503 失败语义 |
| MRF | 容量 1 的实际队列溢出与重试超限；检查管理 JSON、v2/v3 注册后的 counter 类型和值、对象/删除 worker 分配 |
| resync | `testing/synctest` 覆盖 Walk 阻塞、满 worker 队列、主动取消、排队取消、异 ID 隔离、后续任务、终态竞争、旧 ID、槽位释放与 leader 恢复 |
| 本地完整套件 | `go test ./... -count=1 -timeout=30m` 通过，共 50 个有测试的 package |
| 并发与重复 | 复制相关定向 race 通过；取消回归重复 100 次通过 |
| 工具与契约 | 本地 build、vet、lint、生成文件检查、rebrand compatibility guard、`git diff --check` 通过；未更改依赖和兼容基线 |
| 原生双 Server | 使用本地源码构建，直接单对象 DELETE；目标 marker 消失，源端 `xl.meta` 清理，原始数据版本保留；没有使用下载的 Server Docker 镜像 |
| 远端集成 | PR 八项检查通过；合并后主干 Go CI 六项任务及 VulnCheck 通过 |

固定版本的回归用例：[删除标记](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-delete-marker_test.go)、[MRF 可见性](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-mrf-observability_test.go)、[取消生命周期](https://github.com/pgsty/silo/blob/d1105bbb3d4a0afa33b3a4ac11b821235038ed0e/cmd/replication-resync-cancel_test.go)。在该提交、Go 1.27.1 下可复跑：

```bash
go test ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test -race ./cmd -run '^(TestReplication|TestReplicateDeleteMarker|TestResync|TestSiteResync)' -count=1
go test ./cmd -run '^TestResyncCancel' -count=100
go test ./... -count=1 -timeout=30m
```

完整本地验证后仅调整了新测试的格式和夹具：复用既有 ARN、通过 collector 取得指标前缀，避免兼容性扫描器把测试字符串当成新协议标识；没有放宽 guard。调整后重跑相关测试、lint 与兼容检查，远端 CI 验证最终提交。

| 证据点 | 精确标识 |
| :-- | :-- |
| 修复前基线 | `450dcb8484bc1337deba0cf608cc893a6691d794` |
| 最终 PR head | `66fe61ff65c83d68b74baa637a11623015c7aa21` |
| 合并主干 | `d1105bbb3d4a0afa33b3a4ac11b821235038ed0e`，代码树与最终 PR head 相同 |
| PR Go CI | [34320440012](https://github.com/pgsty/silo/actions/runs/34320440012) |
| 主干 Go CI | [34321319278](https://github.com/pgsty/silo/actions/runs/34321319278) |
| 主干 VulnCheck | [34321319274](https://github.com/pgsty/silo/actions/runs/34321319274) |

## 后续维护与发布判断 {#follow-up}

后续改动必须继续分别证明：操作类型正确、失败可见、逐对象结果真实、终态计数完整、取消能够结束自己的资源。任何一项都不能由“接口返回 Completed”或“目标上对象存在”代替。

本次代码结论是 GO，交付事实是主干合并及 CI 通过。正式发布仍需另行选定 tag，验证软件包与镜像，并确认实际部署包含修复。既有 MRF scanner 恢复时延、未关闭的跨池问题，以及外部 405 风暴尚未在当前 SILO 复现的边界，都应随这份决策一起保留。
