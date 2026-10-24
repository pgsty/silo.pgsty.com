---
title: "旧版元数据与扫描响应复用时的残留字段修复"
linkTitle: "元数据复用残留"
date: 2026-10-15
lastmod: 2026-10-19
author: "冯若航"
summary: >
  PR #233 修复旧版 xl.meta 头部与命名空间扫描响应在结构体复用时的字段残留。本文记录触发条件、故障表现、局部清零方案、确定性回归测试、分布式扫描验证与运维指引。
tags: [设计, 可靠性, 存储, 扫描器]
weight: 95
draft: false
url: "/zh/blog/design/stale-metadata-reuse/"
---

本文记录 [PR #233](https://github.com/pgsty/silo/pull/233)（验证提交 [`86c5a92eef3d`](https://github.com/pgsty/silo/commit/86c5a92eef3d5667c83bdbc59a033b955bdbf146)，合并提交 [`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a)，随 [Server 20261018](/zh/blog/release/silo-20261018/) 发布）的设计与验证。该补丁修复了旧版 `xl.meta` 版本头部与远程命名空间扫描响应在复用结构体时带入残留字段的问题。

## 问题概述 {#problem}

两处独立代码路径在复用 Go 结构体时未完整重置其逻辑状态，导致新输入中未出现的字段沿用了上一轮留下的旧值。修复直接落在明确知晓当前输入字段布局的解码器与响应构造处：

| 路径 | 触发条件 | 修复前状态 | 修复后状态 |
| --- | --- | --- | --- |
| 旧版 V2 版本头部 | 将旧版头部解码至 EC 字段非零的复用结构体 | `EcN` 归零，`EcM` 残留旧值 | 两个缺失的 EC 字段均归零 |
| 旧版 V1 版本头部 | 复用带有签名或 EC 字段的结构体 | V1 布局中不存在的字段继续残留 | `Signature`、`EcN`、`EcM` 均归零 |
| 扫描进度响应 | 复用上一轮携带最终缓存的响应信封 | 同时包含新 `Update` 与旧 `Final` | 仅包含 `Update` |
| 扫描最终响应 | 复用上一轮携带进度更新的响应信封 | 同时包含旧 `Update` 与新 `Final` | 仅包含 `Final` |

## 旧版 `xl.meta` 版本头部 {#legacy-headers}

`xl.meta` 内部的紧凑版本头部（version header）拥有独立的版本号，与外层 `xl.meta` 文件格式版本及 SILO 发行版本号相互独立。当前版本头部为 V3，包含纠删码分片参数 `EcN` 与 `EcM`；旧版 V2 头部仅有 5 个字段，不含这两个 EC 字段；V1 解码器对应更早的四字段布局，既无签名也无 EC 字段（源码注释标明 V1 布局从未正式发布，此处属于对保留解码路径的防御性清理）。

此前 V2 的字节切片解码入口 `UnmarshalMsg` 与流式解码入口 `DecodeMsg` 均写成了：

```go
z.EcN, z.EcN = 0, 0
```

由于对 `z.EcN` 重复赋值，`z.EcM` 从未被清零。当调用方传入新分配的零值结构体时该缺陷不会暴露；一旦复用此前存有 `EcN=4, EcM=8` 的结构体，解码 V2 头部后便会得到 `EcN=0, EcM=8`。修复将其更正为 `z.EcN, z.EcM = 0, 0`，并在 V1 解码入口同步清空缺失的 `Signature` 字段。当前 V3 头部则正常保留线上编码中的 EC 字段。

在实际运行中，`loadIndexed` 会直接复用版本头部切片的底层数组空间，因此仅在新建结构体时初始化无法覆盖该路径；合入的回归测试专门针对这一切片复用路径进行了验证。具体改动见[旧版解码器实现](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2-legacy.go)与[索引头部加载及比对逻辑](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2.go)。

若不清零残留字段，同一份二进制头部的解码结果会随复用结构体原先的内容而变化。由于头部相等比对与法定票数（quorum）统计均包含这些字段，不同的残留值会将本应一致的头部拆入不同分组（即便 `hasEC()` 本身要求 `EcN` 与 `EcM` 同时非零才判定为有效 EC 布局）。

## 命名空间扫描响应 {#scanner-responses}

远程磁盘扫描通过 grid RPC 流持续发送 `nsScannerResp` 响应信封。按协议契约，每条消息只能在两个指针字段中二选一：`Update` 携带单次进度更新 `dataUsageEntry`，或 `Final` 携带扫描完成后的汇总缓存 `dataUsageCache`。服务端处理器的对象池会跨扫描周期复用 `nsScannerResp` 实例，但不会在归还时自动清空字段。

此前 `NSScannerHandler` 仅对当次发送所需的字段赋值，未显式清空另一个指针。当后续扫描复用到同一个信封对象时，两个指针字段可能同时非空并被一并序列化发送。而客户端接收循环对两个字段分别独立判断：`Update != nil` 时转发进度更新，`Final != nil` 时记录最终缓存。其结果是，本应只发最终汇总的响应可能夹带上一轮残留的进度更新进入用量聚合，而中间进度消息也可能夹带上一轮扫描遗留的最终缓存。

尽管扫描结束前的最后一条合法 `Final` 消息会覆盖客户端保存的最终缓存指针，但中间消息破坏了字段互斥不变式并在节点间传输了陈旧数据。修复在服务端构造响应时显式清空另一侧指针：

```go
// 进度响应
resp.Update = &update
resp.Final = nil

// 最终响应
resp.Final = &ui
resp.Update = nil
```

该修复作用于跨节点远程磁盘扫描响应（本地磁盘扫描直接调用内部接口，不经过该 RPC 响应信封）。相关代码见[服务端扫描处理器](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server.go)、[客户端接收逻辑](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-client.go)与[存储桶用量聚合](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/erasure.go)。

## 为什么不在通用 RPC 对象池中调用 `Recycle` {#pool-ownership}

原始 PR 最初尝试在通用流式 RPC 处理器的 `PutResponse` 中调用 `Recycler.Recycle()`，随后再将同一响应对象放回处理器自身的 `sync.Pool`。这一做法混淆了“转移底层资源所有权”与“重置结构体字段”两种语义。

以 `grid.MSS` 为例，其 `Recycle()` 方法会将内部底层 `map` 归还给专门的 map 池，并将外层结构体的 map 字段置为 `nil`。如果紧接着把外层包装对象又放回响应池，下一次 `NewResponse` 从池中取出该对象时就会跳过构造函数，直接向调用方返回一个无法写入的 `nil` map。我们编写的补充复现用例在修复前主分支上正常通过，而在引入该通用池改动后会触发失败。

因此，维护者补丁撤回了通用 `PutResponse` 改动以及新加的 `nsScannerResp.Recycle` 方法，仅保留扫描处理器构造响应时的显式字段赋值。最终合入的 `internal/grid/handlers.go` 与 `cmd/storage-rest-common.go` 相对合并前主分支保持零改动，完整保留了 [grid 类型定义](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/internal/grid/types.go)中的 `Recycler` 资源所有权契约。

## 验证证据 {#verification}

### 确定性回归测试 {#regression-tests}

合入代码包含两项回归测试：[`TestXLMetaV2HeaderLegacyUnmarshalResetsEc`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2_test.go) 与 [`TestNSScannerHandlerClearsStaleResponses`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server_test.go)。

版本头部测试覆盖了 V2 字节切片解码、V2 流式解码、`loadIndexed` 切片复用、V1 残留字段清零以及当前 V3 格式的 EC 字段保留。扫描器测试连续三轮调用真实 `NSScannerHandler`，在消息经序列化与反序列化后逐条校验两类响应的互斥性及各轮扫描数据归属。

值得强调的是，测试中通过池构造函数新分配的每个响应对象都会预先填入非空的旧 `Update` 与 `Final` 指针。这是因为 Go 的 `sync.Pool` 随时可能回收池中缓存的对象；如果测试仅依赖“上一轮归还的脏对象一定会在下一轮被取出”，在垃圾回收介入时就会退化为分配全新零值对象，导致测试在未触发缺陷的情况下假性通过。直接在构造函数中预置脏字段保证了测试的确定性：该用例在修复前主分支（[`0d3ba5d4cbfd`](https://github.com/pgsty/silo/commit/0d3ba5d4cbfd470946606c4dc7254b36be43c769)）上稳定失败，在应用修复后稳定通过。

```bash
go test -race ./cmd \
  -run '^Test(XLMetaV2HeaderLegacyUnmarshalResetsEc|NSScannerHandlerClearsStaleResponses)$' \
  -count=1 -timeout=5m
go test -race ./internal/grid -count=1 -timeout=5m
```

### 分布式集群扫描实测 {#distributed-check}

端到端验证在本地回环网络上启动了**两个服务进程、共八个数据目录**的分布式实例，创建 12 个存储桶，每桶先写入两个不同大小的对象，随后在每个桶内执行删除一个对象、覆盖一个对象、新增一个对象的组合操作。

| 检查点 | 对象总数 | 逻辑总字节数 | 验证结果 |
| --- | ---: | ---: | --- |
| 首轮写入后 | 24 | 64,740 | 连续三次扫描刷新后，各桶及集群汇总用量均完全匹配 |
| 删除、覆盖与新增后 | 24 | 111,960 | 连续三次扫描刷新后，各桶及集群汇总用量均完全匹配 |
| 对象回读校验 | 24 | 111,960 | 全部 24 个对象的字节长度与 SHA-256 摘要完全一致 |

两个节点均产生了真实的存储桶扫描记录，其中非协调节点通过远程 RPC 流累计执行了 119 次 `ScanBucketDrive` 操作。

### 远端 CI 检查 {#ci}

PR 分支提交 `86c5a92eef3d` 通过了全部 8 项 CI 检查：DCO、[6 项 Go CI 任务](https://github.com/pgsty/silo/actions/runs/38667624646)以及 [VulnCheck](https://github.com/pgsty/silo/actions/runs/38667624700)。合入主分支后，主干上的 [6 项 Go CI 任务](https://github.com/pgsty/silo/actions/runs/38668808660)与 [VulnCheck](https://github.com/pgsty/silo/actions/runs/38668808668) 亦全部独立通过。

## 兼容性与运维指引 {#operations}

本次修复仅修正既有解码器与扫描响应构造处的字段赋值，不涉及存储格式、RPC 协议字段、依赖版本、IAM 策略或配置开关变更，无需重写存量对象或手动清理用量缓存。

1. **将集群节点升级至 Server 20261018 或更高版本。** 节点间线协议完全兼容，可按常规流程滚动升级；跨组件版本配套要求参见[组件版本矩阵](/zh/compatibility/versions/)。
2. **等待后台扫描自然收敛。** 可通过 `mcli admin scanner status ALIAS -n 1` 查看扫描进度，待完整扫描周期结束后核对各存储桶的对象计数与逻辑容量。
3. **无需人工干预底层元数据。** 切勿手动编辑磁盘上的 `xl.meta`、删除内部缓存对象或批量重写数据；常规后台扫描周期会自动刷新派生的用量统计。

## 致谢与交付记录 {#delivery}

感谢 Julien Laurenceau 提交初始修复与测试用例。维护者在此基础上收窄了对象池改动范围，保持了 `grid.Recycler` 的资源所有权契约，并补充了确定性脏分配回归测试；原作者提交记录与 DCO 签名完整保留在合并历史中。
