---
title: "旧版元数据与扫描响应复用时的残留字段修复"
linkTitle: "元数据复用残留"
date: 2026-10-15
lastmod: 2026-10-15
author: "Ruohang Feng"
summary: >
  PR #233 修复旧版 xl.meta 头部与命名空间扫描响应复用时的字段残留。本文说明触发条件、已证实影响、局部清理方案、确定性回归测试、分布式扫描验证，以及版本发布边界。
tags: [设计, 可靠性, 存储, 扫描器]
weight: 95
draft: false
url: "/zh/blog/design/stale-metadata-reuse/"
---

> [!WARNING]
> **发布状态更正（2026-10-17）：** SILO `RELEASE.2026-10-15T00-00-00Z` 已恢复为 Draft，未作为当前正式版本提供；正式 Server 仍为 20260916。下文关于 20261015 已发布或可下载的历史表述已失效，其中修复尚不能视为正式版已交付。20261018 仅准备标签和草稿，尚未正式发布。请以[组件版本表](/zh/compatibility/versions/)和[下载页](/zh/download/)为准。

**发布更新（2026-10-15）：** 本修复首次随 [Server 20261015](/zh/blog/release/silo-20261015/) 交付。下文源码验收记录保留此前发布前的验证结论。

**2026-10-15 核验状态：已合入 main，尚未进入已发布的 Server 版本。**
修复通过 [PR #233](https://github.com/pgsty/silo/pull/233) 合入，合并提交为
[`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a)。
通过验证的 PR 头部是
[`86c5a92eef3d`](https://github.com/pgsty/silo/commit/86c5a92eef3d5667c83bdbc59a033b955bdbf146)，
其源码树与合并提交完全一致。本次核验时，最新发布的 Server 仍为
[20260916](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-16T00-00-00Z)，
其源码仍包含两处缺陷。源码合并不会更新用户已经安装的二进制、软件包或容器镜像。

## 问题是什么 {#problem}

两条独立路径在复用 Go 对象时，没有完整替换其逻辑状态。新输入不包含的字段保留了上一次使用时的值。
修复应放在知道“这次输入允许包含哪些字段”的位置。

| 路径 | 触发条件 | 错误状态 | 应有状态 |
| --- | --- | --- | --- |
| 旧版 V2 版本头部 | 将旧头部解码到 EC 字段非零的结构体 | `EcN` 归零，`EcM` 残留 | 两个缺失的 EC 字段都归零 |
| 旧版 V1 版本头部 | 复用带有签名或 EC 字段的结构体 | V1 不包含的字段继续残留 | `Signature`、`EcN`、`EcM` 都归零 |
| 扫描进度响应 | 复用曾经携带最终缓存的响应对象 | 同时包含 `Update` 与旧 `Final` | 只包含 `Update` |
| 扫描最终响应 | 复用曾经携带进度更新的响应对象 | 同时包含旧 `Update` 与 `Final` | 只包含 `Final` |

这里的 **stale metadata** 指复用时带入的旧值。现有证据确认了正确性缺陷，
没有证明对象正文丢失、跨租户信息泄露或无界内存泄漏。仅凭一处用量统计偏差，不能断定触发了这个问题。

## 旧版 xl.meta 头部 {#legacy-headers}

`xl.meta` 内部紧凑头部的版本，与外层文件格式版本、SILO 发布版本号不同。
修复提交中的当前头部版本是 3，包含 `EcN` 和 `EcM`。旧 V2 头部只有五个字段，不包含这两个 EC 字段。
V1 解码器处理四字段布局，既没有签名，也没有 EC 字段；源码明确标注这个布局**从未发布**。
因此，V1 修复是对保留解码路径的防御性覆盖，不代表发现了受影响的已发布 V1 部署。

V2 的字节解码入口 `UnmarshalMsg` 与流式解码入口 `DecodeMsg` 原先都写成：

```go
z.EcN, z.EcN = 0, 0
```

重复赋值使 `EcM` 没有被清空。使用新建的零值结构体时问题不显现；
复用一个 `EcN=4, EcM=8` 的结构体，V2 解码后就会得到 `0,8`。
修复将赋值改为 `z.EcN, z.EcM = 0, 0`，并在 V1 解码前额外清空缺失的 `Signature`。
当前 V3 头部仍然保留编码中实际存在的 EC 字段。

这不只是单独调用解码器时的问题：`loadIndexed` 会复用版本头部切片的底层空间。
只在新建结构体时清理，覆盖不到这条路径；提交中的回归测试直接验证了这种复用。
参见固定提交中的[旧版解码器](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2-legacy.go)
与[索引头部加载和比较逻辑](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2.go)。

已复现的结果是：同一份编码的解码结果受结构体先前内容影响。
头部相等判断和票数统计包含这些字段，不同残留值可以把本应相同的头部分成不同组。
这说明有必要恢复字段不变量，但不证明每个旧对象都会发生错误仲裁或错误修复。
尤其是 `hasEC()` 要求**两个** EC 字段都非零，而原来的 V2 代码已经清空了 `EcN`；
不能声称仅凭残留 `EcM` 就一定会启用 EC 比较。本次审查没有复现生产数据丢失。

## 命名空间扫描响应 {#scanner-responses}

远程磁盘扫描通过 grid RPC 流传输 `nsScannerResp`。
每条消息应当二选一：`Update` 携带 `dataUsageEntry` 进度更新，或 `Final` 携带最终的 `dataUsageCache`。
处理器的对象池会复用响应对象，但不会自动清空字段。

原来的 `NSScannerHandler` 只赋值当前需要的字段。后续扫描复用对象时，两个指针可能同时被序列化。
接收端分别检查这两个字段：存在 `Update` 就转发更新，存在 `Final` 就记住最终缓存。
因此，旧的更新可能进入用量聚合，一条进度消息也可能夹带上一次扫描的缓存。

接收端不会在第一个 `Final` 处停止。后续合法的最终响应会替换已记录的缓存指针；
成功扫描也会在排空进度更新之后提交最终桶结果。因此，错误的中间响应**不等于**每次扫描完成后都会持久化错误总量。
确定性复现的是响应互斥约束被破坏、旧数据被传输了出去。修复在发送端消除这种歧义：

```go
// 进度响应
resp.Update = &update
resp.Final = nil

// 最终响应
resp.Final = &ui
resp.Update = nil
```

这项修复针对远程扫描响应。本地磁盘扫描不序列化这种响应对象，旧版头部问题也有独立的触发条件，
两个问题不需要同时发生。参见固定提交中的
[服务端处理器](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server.go)、
[客户端接收逻辑](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-client.go)
与[桶结果聚合](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/erasure.go)。

## 为什么不修改通用对象池 {#pool-ownership}

PR 最初还在通用流式处理器的 `PutResponse` 中调用 `Recycler.Recycle()`，
随后又把同一个对象放回处理器自己的池。这把“交还资源所有权”的操作当成了普通清零钩子。

例如，`grid.MSS.Recycle()` 会把底层 map 还给另一个池，再将 map 设为 nil。
如果又把外层对象放回池，下次 `NewResponse` 就可能绕过构造器，返回一个不可写的 nil map。
补充复现用例在合并前的 main 上通过，在这个拟议改动上失败。

维护者补丁撤回了通用改动和新加的 `nsScannerResp.Recycle` 方法，只保留扫描器构造响应时的显式赋值。
最终合并的 `internal/grid/handlers.go` 与 `cmd/storage-rest-common.go` 相对合并前主线没有变化。
既有 `Recycler` 资源所有权约定见 [grid 类型定义](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/internal/grid/types.go)。

已有 Console 日志流和事件流确实使用 `*grid.Bytes` 的回收机制。
补充测试覆盖了它们的回收与缓冲区转交，并通过竞态检查。
本次否决的是通用接口约定的回归，没有观察到现有 Console 或事件流故障。

## 验证证据 {#verification}

### 已入库的回归测试 {#regression-tests}

合并源码包含
[`TestXLMetaV2HeaderLegacyUnmarshalResetsEc`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/xl-storage-format-v2_test.go)
和
[`TestNSScannerHandlerClearsStaleResponses`](https://github.com/pgsty/silo/blob/d94b3b3c9251af5a9dbdb2d178e892c4de75204a/cmd/storage-rest-server_test.go)。

头部测试覆盖 V2 字节解码、流式解码、索引头部复用、V1 字段清理，以及当前格式 EC 字段保留。
扫描器测试连续三轮调用真实处理器，序列化后检查两种响应及其所属扫描轮次的数据。

测试中新分配的响应对象也预先填入旧 `Update` 和 `Final`。这是必要的：
`sync.Pool` 可以丢弃池中对象，假设“下次一定拿到刚放回的脏对象”的测试可能根本没触发问题就通过。
把新分配对象也设为脏状态，才能得到确定性的检查。
将受影响的生产文件替换成修复前 main
[`0d3ba5d4cbfd`](https://github.com/pgsty/silo/commit/0d3ba5d4cbfd470946606c4dc7254b36be43c769)
中的版本时，这些测试会失败；使用修复文件时通过。

在包含修复的工作目录中运行：

```bash
go test -race ./cmd \
  -run '^Test(XLMetaV2HeaderLegacyUnmarshalResetsEc|NSScannerHandlerClearsStaleResponses)$' \
  -count=1 -timeout=5m
go test -race ./internal/grid -count=1 -timeout=5m
```

相关元数据、扫描、用量、修复、目录遍历和响应序列化测试也通过了 `-race`。
本地 Go 1.27.2、darwin/arm64 环境中的 `make verifiers`、`make build` 均通过。
后续补跑的拼写检查通过了本 PR 的全部四个文件；全仓库检查报告 30 处已有诊断，
逐项确认均在本 PR 之前存在。不能将这项结果表述为全仓库拼写检查通过。

### 真实分布式扫描 {#distributed-check}

后续验证在同一台 macOS 主机上启动**两个服务进程、八个数据目录**，仅监听回环地址。
创建十二个桶，每桶写入两个不同大小的对象，再对每个桶执行删除一个对象、覆盖另一个对象、新增一个对象。

| 检查点 | 对象数 | 逻辑总字节数 | 观察结果 |
| --- | ---: | ---: | --- |
| 首轮写入 | 24 | 64,740 | 每桶与集群总量连续三次刷新都符合预期 |
| 删除、覆盖与新增 | 24 | 111,960 | 每桶与集群总量又连续三次刷新都符合预期 |
| 回读校验 | 24 | 111,960 | 所有对象长度与 SHA-256 均匹配 |

两端都有实际桶扫描记录，其中非协调端记录了 119 次 `ScanBucketDrive` 操作。
因此验证确实覆盖了远程执行，不只是本地磁盘模拟。验证结束后已停止测试进程。

这是修复版本的功能集成检查，不是性能基准、物理磁盘故障测试、生产部署证明，
也不是对旧版本对象池复用的确定性复现。修复前后的确定性证据来自已入库的回归测试。
用量的 `lastUpdate` 时间戳代表结果刷新，不能据此认定生产桶的所有前缀都已完成一轮全量扫描。

### 远端 CI {#ci}

PR 头部 `86c5a92eef3d` 的八项检查全部通过：DCO、
[六项 Go CI](https://github.com/pgsty/silo/actions/runs/38667624646)
和 [VulnCheck](https://github.com/pgsty/silo/actions/runs/38667624700)。
Go CI 覆盖格式、构建与 vet，lint 与生成文件，竞态与 S3 Select，交叉编译，以及 `internal/`、`cmd/` 测试。
合并后的主线又独立通过了
[六项 Go CI](https://github.com/pgsty/silo/actions/runs/38668808660)
与 [VulnCheck](https://github.com/pgsty/silo/actions/runs/38668808668)。

## 兼容性与运维处置 {#operations}

修复只调整既有解码器和响应构造中的赋值，没有新增存储格式、RPC 字段、依赖版本、权限、配置开关或客户端要求。
不需要为此重写对象或删除用量缓存。正式支持的组合仍是协调维护的 SILO、SILO Console、mcli 与 silo-pkg；
与未修改的上游 MinIO/MC 兼容性维持“尽最大努力”。

1. **确认实际运行的服务端版本。** Server 20260916 不含这项修复。
   选择明确包含修复的后续发布版本，或已经验证包含修复代码的自构建制品。
   仅查看仓库分支，不能确认正在运行的二进制身份。
2. **升级所有提供扫描服务的节点。** 线协议没有变化，但旧节点仍会生成原来的响应。
   本补丁没有新增协同升级约束；所选完整版本中的其他改动可能有自己的要求，参见[组件版本矩阵](/zh/compatibility/versions/)。
3. **等待用量统计收敛。** 用 `mcli admin scanner status ALIAS -n 1` 检查扫描健康与活动。
   对稳定桶使用独立清单核对数量与逻辑大小，统一版本、删除标记和统计时间口径。
   不能凭一次更新时间变化，就认定所有受影响路径已经重新扫描。
4. **持续偏差需要单独诊断。** 保留运行版本、扫描错误和小规模可复现清单。
   并发写入、版本控制、扫描未完成或磁盘离线，也可能造成差异。
   不应仅因这个 PR 就手工修改 `xl.meta`、删除内部缓存、执行破坏性修复或重写全部对象。

补丁阻止后续复用时再次带入旧字段，不会还原历史用量观测，也不证明存量数据原本健康。
正常成功扫描可以替换派生的用量结果；源码合并和本地测试都不能替代对每个实际部署的恢复验收。

## 交付与贡献 {#delivery}

Julien Laurenceau 提交了原始修复与初始测试。维护者补丁缩小了对象池改动范围并加强验证，
原作者提交及 DCO 签名均保留在合并历史中。最终 PR 修改四个文件，增加 194 行、删除两行，新增内容主要是测试。

代码修复、永久回归测试、PR 验收与合并后 CI 已完成。本文补齐中英文问题说明与运维边界。
截至上述核验日期，新 Server 版本发布和生产安装升级仍是独立交付项；
本文不宣称已完成软件包、镜像发布或生产部署。
