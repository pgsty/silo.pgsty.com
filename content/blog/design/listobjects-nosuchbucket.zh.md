---
title: "ListObjects 快捷路径不能把不存在的桶伪装成空桶"
linkTitle: "ListObjects NoSuchBucket"
date: 2026-08-26
lastmod: 2026-08-26
author: "冯若航"
summary: >
  三条 ListObjects 快捷路径会在访问存储前直接返回 EOF，导致不存在的桶被错误地表示为空列表。本文记录 SILO #32 / PR #37 的回归来源、S3 兼容性价值、只在快捷路径检查桶存在性的最小修复、集群扇出代价、衍生边界与验收决策。
tags: [设计, S3, 兼容性, ListObjects]
weight: 25
draft: false
url: "/zh/blog/design/listobjects-nosuchbucket/"
---

本文是 [SILO #32](https://github.com/pgsty/silo/issues/32) 与 [PR #37](https://github.com/pgsty/silo/pull/37) 的问题分析、设计讨论与修复决策归档。

> **截至 2026-08-26 的状态：** [PR #37](https://github.com/pgsty/silo/pull/37) 已更新为带 DCO sign-off 的 head [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377)，通过正式批准并合并为 [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef)；[#32](https://github.com/pgsty/silo/issues/32) 随后自动关闭。精确 PR head 的 DCO、VulnCheck 与六项 Go CI 全部通过，合并后 `main` 的 VulnCheck 与六项 Go CI 也全部通过。尚未验证任何 tag、软件包、容器镜像、部署或生产端点已经包含本修复。<br>
> **范围：** 只为三条绕过存储的列表快捷路径补上桶存在性检查；不恢复通用 `checkBucketExist`，不改变正常列表路径，也不增加存在性缓存。<br>
> **发布边界：** 本地提交、push、远端 CI、merge、tag、软件包、容器镜像、部署与生产验证是相互独立的门槛。

## 太长不看（TL;DR） {#tldr}

这个问题是真的，而且值得修。对不存在的桶执行 `ListObjects`、`ListObjectsV2` 或 `ListObjectVersions` 时，普通请求会在扫描存储时得到 `BucketNotFound`；但以下三种输入会提前结束：

- marker 不属于 prefix；
- `max-keys=0`；
- prefix 以 `/` 开头，包括 #32 中 boto3 使用的 `Prefix="/"`。

这些分支直接返回 `io.EOF`，上层将它解释为“列表正常结束”，于是客户端收到空的 200，而不是 S3 的 404 `NoSuchBucket`。同一个不存在的资源，仅仅因为过滤参数不同就从错误变成成功，这既破坏 S3 兼容性，也阻塞了从回归前版本升级的真实用户。

修复不应把昂贵的桶检查放回每一次列表请求。选定方案只把三个裸 `io.EOF` 改为调用一个小 helper：helper 调用一次 `GetBucketInfo`；桶不存在或集群无法确认时返回真实错误，桶存在时仍返回 `io.EOF`。因此正常列表热路径完全不变，额外的 peer/disk 扇出只由原本会在访问存储前结束的请求承担。

这项决策现已执行完成：**补强修复通过本地评审，精确 PR head 通过全部远端检查，并通过 expected-head guard 合入绿色 `main`。**

## 这是什么问题 {#problem}

### 同一个 API 出现两套桶存在性语义 {#two-semantics}

#32 给出的最小复现是在不存在的桶上调用：

```python
s3.list_objects(Bucket="missing-bucket", Prefix="/")
```

AWS S3 抛出 `NoSuchBucket`，SILO 却返回一个成功的空列表。差异不在认证、路由或 XML 编码，而在对象层 `listPath` 的控制流：

```text
普通 prefix
  -> 进入 listMerged
  -> 访问存储
  -> 不存在的 volume/bucket 变成 BucketNotFound
  -> HTTP 404 NoSuchBucket

快捷输入
  -> listPath 提前返回 io.EOF
  -> 完全没有访问存储
  -> 上层把 EOF 当成正常结束
  -> HTTP 200 + 空列表
```

触发提前返回的不是只有 `/` prefix：

| 快捷条件 | 为什么结果必为空 | 修复前的缺陷 |
| --- | --- | --- |
| marker 不以 prefix 开头 | 当前实现不扫描这个不相交区间 | 未确认桶是否存在就返回 EOF |
| `max-keys=0` | 调用者明确要求返回零个 key | 把“零结果”错误地等同于“资源有效” |
| prefix 以 `/` 开头 | SILO 的扁平 key 空间不会生成这种列表项 | 过滤条件在桶身份之前短路 |

对存在的桶，这三个分支返回空列表是合理优化；对不存在的桶，同一个 EOF 会掩盖应该优先返回的资源错误。

### 这是一个有明确起点的回归 {#regression}

报告者确认 `RELEASE.2024-01-29T03-56-32Z` 行为正确，从 `RELEASE.2024-01-31T20-20-33Z` 开始出现回归。对应上游变更是 [minio/minio#18917](https://github.com/minio/minio/pull/18917) / [`80ca12008`](https://github.com/minio/minio/commit/80ca120088be9950fa35467975dd9d8dc1bd4176)：它从通用参数检查中删除了 `GetBucketInfo`，让实际 Put、List 与 Multipart 存储操作自行暴露不存在的桶。

这个优化对正常路径成立，但留下一个边角：提前返回的路径根本不会到达能够暴露错误的存储操作。#32 不是要求全面撤销上游优化，而是补上优化后遗漏的控制流分支。

## 为什么要修复 {#why-fix}

### S3 契约明确要求 `NoSuchBucket` {#s3-contract}

[AWS ListObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html) 与 [ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html) 都把 `NoSuchBucket` 定义为 404：指定桶不存在。`prefix`、marker、`start-after` 与 `max-keys` 是结果选择条件，不应让不存在的 bucket identity 变成一次成功请求。

`ListObjectVersions` 共享同一个对象层列表引擎。让三个公开列表 API 在同样的 shortcut 输入上遵守同一桶存在性语义，可以避免 V1、V2 与版本列表继续分叉。

### 错误的空列表会改变调用者决策 {#client-impact}

空 200 与 404 不是可互换的展示细节：

- 404 告诉 provisioning 或测试代码先创建桶、修正配置或终止流程；
- 空 200 声称桶存在，只是暂时没有匹配对象；
- SDK、同步工具和集成测试会沿两条不同的控制流继续执行；
- 使用 SILO 模拟 S3 的测试可能在本地通过，却在 AWS 上失败。

#32 还给出了直接升级影响：依赖旧有正确行为的应用无法升级到回归后的版本。修复因此同时恢复 S3 parity 和版本升级兼容性。

### 修复面很窄，也容易建立强回归契约 {#repair-value}

问题集中在三个相邻的 early return，不涉及对象数据、元数据格式、排序、分页 token 编码、权限或 wire schema。可以用很少的生产代码修复，并在对象层与 HTTP 层精确锁定行为，收益明显高于实现风险。

## 为什么不能简单恢复全局检查 {#performance-constraint}

上游删除通用 `GetBucketInfo` 不是随意清理。[#18917 的动机](https://github.com/minio/minio/pull/18917) 明确指出：Put、List 与 Multipart 每次先检查桶会在所有 server 间扇出；即使做过向量化，超过 100 个节点后成本仍明显可见。

在 SILO 当前实现中，`erasureServerPools.GetBucketInfo` 会调用 `S3PeerSys.GetBucketInfo`：请求并发发往所有 peer，再按 pool 聚合 quorum。每个 peer 还要检查本地 bucket 状态。它不是一次廉价的内存 map 查询。

因此存在两个都不应接受的极端：

- **完全不检查：** 保留错误的空 200；
- **每次 List 都先检查：** 恢复正确语义，却撤销大型集群上的关键优化。

真正的设计问题是：能否只给“不会访问存储、因此无法自然发现缺桶”的分支补检查。答案是可以。

## 怎么修复 {#implementation}

### 只替换三个裸 EOF {#three-shortcuts}

在 `cmd/metacache-server-pool.go` 中，三个 shortcut 原来都执行：

```go
return entries, io.EOF
```

改为：

```go
return entries, z.listPathShortcutEOF(ctx, o.Bucket)
```

helper 的契约只有两类结果：

```go
func (z *erasureServerPools) listPathShortcutEOF(ctx context.Context, bucket string) error {
    if _, err := z.GetBucketInfo(ctx, bucket, BucketOptions{}); err != nil {
        return err
    }
    return io.EOF
}
```

- 桶存在：保留原有空列表行为；
- 桶不存在：把 `BucketNotFound` 交给既有错误映射，HTTP 返回 404 `NoSuchBucket`；
- 集群无法可靠确认：传播 quorum、offline、timeout 或 context 错误，不再伪造成功。

正常的 `listMerged`、metacache 扫描、排序、分页和响应生成全部不变。

### 为什么 helper 放在这里 {#helper-boundary}

检查必须紧贴 shortcut，原因有三点：

1. 只有这一层知道自己即将绕过全部存储访问；
2. 上移到通用参数校验会让所有调用付费；
3. 下移到扫描层对这些分支无效，因为它们永远不会进入扫描。

helper 名称也刻意表达边界：它不是新的通用 `checkBucketExist`，而是“在 shortcut 返回 EOF 前补齐缺失的存在性语义”。

### 不引入缓存 {#no-cache}

用 bucket-existence cache 可以降低扇出，但会立即引入创建、删除、site replication、恢复与过期策略的一致性问题。为了三个低频 shortcut 增加一套新的事实源，复杂度与失效风险都高于收益。

当前选择使用已有 `GetBucketInfo` 作为事实源。如果未来遥测证明大型集群频繁收到 `max-keys=0` 或 slash-prefix 探测，再基于数据考虑专用元数据快路、限流或安全缓存，而不是在这个兼容修复中预先设计。

## 测试与评审证据 {#verification}

### 对象层契约 {#object-layer-tests}

对象层测试在单盘与多盘 erasure setup 上，对以下四类输入逐一调用：

- slash-prefixed prefix；
- zero limit；
- marker outside prefix；
- regular prefix，作为仍由存储自然报错的控制组。

每组都覆盖 `ListObjects`、`ListObjectsV2` 与 `ListObjectVersions`，并使用类型化的 `isErrBucketNotFound` 判断，而不是比较易碎的英文错误文本。

### HTTP 契约 {#http-tests}

Handler 测试使用真实签名请求验证三个公开 API：

| API | 请求形态 | 断言 |
| --- | --- | --- |
| ListObjects | `GET /missing-bucket?prefix=/` | HTTP 404，XML code 为 `NoSuchBucket` |
| ListObjectsV2 | 加 `list-type=2` | HTTP 404，XML code 为 `NoSuchBucket` |
| ListObjectVersions | 加 `versions` | HTTP 404，XML code 为 `NoSuchBucket` |

HTTP 测试选择 #32 的真实 slash-prefix 复现；另外两个 shortcut 已在对象层穷举。这样既证明最终 wire behavior，又避免把同一矩阵在较慢的 handler fixture 中重复三遍。

### 本地质量门槛 {#local-gates}

本地改进提交完成了以下验证：

```text
go test ./cmd -count=1
新对象层与 HTTP 回归测试（10 个子场景）
定向 go test -race
相关既有列表测试
CGO_ENABLED=0 go build ./...
go vet ./...
CI 范围 gofmt 与 git diff --check
提交后的定向回归复验
```

本地完整 `cmd` 测试用时 116.215 秒。独立本机 Claude Code 使用 Fable 模型与 Max effort 审查了精确代码树、调用路径、错误映射、测试、性能边界和本轮决策，给出 **GO**，没有 mandatory pre-merge change。

带 DCO sign-off 的 PR head `e9c5340be` 随后通过八项远端检查：[DCO](https://github.com/pgsty/silo/actions/runs/32961304270)、[VulnCheck](https://github.com/pgsty/silo/actions/runs/32961304271) 与 [Go CI](https://github.com/pgsty/silo/actions/runs/32961304309) 六个 job。合并后生成的 `main@49c8aeac4` 又独立通过 [VulnCheck](https://github.com/pgsty/silo/actions/runs/32962256729) 和 [Go CI](https://github.com/pgsty/silo/actions/runs/32962256823) 六个 job。最慢的 PR cross-compile 用时 9 分 47 秒，合并后 cross-compile 用时 9 分 30 秒。

## 会不会引入新问题 {#derived-risks}

### Shortcut 现在会产生集群扇出 {#fanout-cost}

这是本修复最重要、也是刻意接受的代价。存在桶上的三类请求过去约等于一次本地分支判断，现在需要 `GetBucketInfo`。本机方向性 microbenchmark 得到：

| 路径 | 观察到的量级 |
| --- | ---: |
| 修复前 shortcut | 约 0.55 μs，7 allocs |
| 修复后单盘 shortcut | 约 7.8–8.1 μs，45–47 allocs |
| 修复后 32 盘 shortcut | 约 70–81 μs，977 allocs |
| 32 盘正常列表 | 约 0.95 ms |

这些数字只说明本地相对关系，不是 100+ 节点生产延迟预测。真实分布式环境还包含 peer 网络、quorum 与最慢节点尾延迟，可能比本机差得多。也正因为如此，检查绝不能扩展到正常列表路径。

风险集中在异常或探测式流量：如果某个错误配置的客户端高频轮询 `max-keys=0`、slash prefix 或不相交 marker，它会把原本廉价的请求放大成 peer/disk 工作。合并后值得从 S3 trace 或 metrics 观察这些输入的实际频率；有证据时再限流或优化。

### 降级集群会暴露更多真实错误 {#degraded-cluster}

过去 shortcut 在 peer 离线或 bucket quorum 不足时也可能返回空 200，因为它根本不接触集群状态。修复后，这些请求可能返回 quorum、timeout 或 service error。

这属于更诚实的行为，不是可用性回归：服务器无法确认桶存在时，不应声称它是一个有效的空桶。但依赖“无论集群状态如何都空成功”的客户端会观察到变化。

### 创建与删除并发仍不具备线性化快照 {#race-window}

`GetBucketInfo` 与返回空列表是两个动作。桶可能在检查后立即删除，或在缺桶结果形成后立即创建。本补丁没有也不应该为列表 shortcut 引入跨 bucket lifecycle 的事务。

这与其他先验证资源、再执行操作的 API 属于同一并发类别。修复保证请求不会在**没有任何存在性证据**时直接成功，不承诺一个跨节点、跨生命周期的线性化空列表快照。

### 依赖旧错误行为的客户端会看到 404 {#behavior-change}

有客户端可能已经把缺桶的空 200 当作事实使用。修复会让它们进入错误分支。这是可见兼容变化，但它恢复的是 S3 文档契约与回归前行为；保留 bug 只会把迁移成本留给正确依赖 404 的用户。

### 两个相邻边缘仍不在本轮范围 {#remaining-edges}

对抗评审记录了两个非阻塞的 P3 边界：

1. 恢复 metacache continuation 时，`c.fileNotFound` 分支仍直接返回 `io.EOF`。一个陈旧或构造的 continuation token 遇上已经删除的桶，理论上仍可能得到空 200。把 `GetBucketInfo` 放到这里会影响正常分页 continuation，性能与错误语义需要单独设计。
2. V1 与版本列表的某些 marker/prefix 组合会在 HTTP handler 参数校验中先返回 `NotImplemented`，尚未到对象层；V2 的 `start-after` 能进入对象层。本补丁修复的是存储 shortcut 掩盖缺桶，不重新定义畸形参数与资源错误的优先级。

它们都不是合并 blocker：第一项不在 #32 的普通初始列表复现中，第二项是既有 handler 行为。文档保留它们，是为了避免把“已覆盖三个 shortcut”误写成“所有可能的参数组合都已实现逐字节 AWS parity”。

## 讨论过的替代方案 {#alternatives}

### 保持上游现状 {#keep-upstream}

优点是零性能变化并减少与上游差异。缺点是继续违反 S3 契约、保留有版本边界的回归，并让 SILO 作为集成测试替身时给出错误信号。对一个范围清楚、测试充分的兼容修复，这个取舍不再合理。

### 恢复通用 `checkBucketExist` {#restore-global-check}

它能一次覆盖所有路径，却把 peer fan-out 加回每个 Put、List 与 Multipart 操作，直接撤销 #18917 的大型集群优化。收益与成本不成比例，应明确拒绝。

### 只修 `Prefix="/"` {#slash-only}

这会通过 issue 的单个复现，却留下 `max-keys=0` 与 marker-outside-prefix 两个同根缺陷。三个分支相邻、语义相同，用同一个 helper 收敛更简单，也更不容易再次遗漏。

### 增加 bucket-existence cache {#existence-cache}

它可以让 shortcut 便宜，但需要定义创建、删除、复制、故障恢复和 TTL 期间的陈旧语义。当前没有遥测证明这些 shortcut 的流量足以支撑这种复杂度，因此不采用。

## 复杂度与成本收益 {#tradeoff}

| 维度 | 评价 | 说明 |
| --- | --- | --- |
| 生产代码复杂度 | 低 | 三处调用点与一个 7 行 helper；无新状态、依赖或格式 |
| 测试复杂度 | 低到中 | 要同时覆盖 V1、V2、versions、三类 shortcut、控制组与 HTTP 映射 |
| 正常路径风险 | 很低 | `listMerged` 热路径没有新增检查 |
| Shortcut 运行时成本 | 明显上升 | 从本地 EOF 变成 cluster-wide `GetBucketInfo` |
| 兼容收益 | 高 | 恢复 404 `NoSuchBucket`、回归前行为和 S3 测试保真度 |
| 运维复杂度 | 低 | 无迁移、配置、feature flag、缓存或跨仓库依赖 |

成本收益比总体良好，关键原因不是 `GetBucketInfo` 很便宜——它并不便宜——而是额外成本被严格限制在原本无法自然发现缺桶的三条 shortcut。用窄幅性能成本换取明确的协议正确性，比全局回退或长期保留错误行为都更合理。

## 接受决策与后续门槛 {#decision}

最终决策是：**接受并合并补强后的 PR #37，不继续扩大生产修改范围。**

实际执行顺序是：

1. 用基于当前 `main`、带 DCO sign-off 的版本替换陈旧 fork head，同时保留 Jason Lin 的 co-author 归属；
2. 保留类型化错误判断、V1/V2/版本列表对象层覆盖与 HTTP 级 404 / `NoSuchBucket` 断言；
3. 更新 PR 描述，明确 shortcut 扇出成本与正常路径不变的边界；
4. 批准 fork workflow，并要求精确 head `e9c5340be` 的八项检查全部通过；
5. 针对该 head 提交正式批准评审；
6. 使用 expected-head guard 合并为 `49c8aeac4`，让 #32 自动关闭，再独立要求生成的 `main` Go CI 与 VulnCheck 全绿。

本轮不需要新增缓存、feature flag、更多抽象或修改 continuation-token 语义。高频 shortcut 流量与大型集群尾延迟仍是后续可观测项，不是继续凭假设扩代码的理由。

仓库集成已经完成。只有 tag、软件包、`docker.io/pgsty/silo` 镜像、部署与真实 S3 客户端验证分别完成后，才能宣称用户已经获得修复。

## 结论 {#conclusion}

问题的本质不是“prefix 为 `/` 时少报了一个错误”，而是列表引擎把 `io.EOF` 同时当成了两件不同的事：存在桶的空结果，以及从未确认桶存在的提前结束。上游为大型集群移除通用存在性检查是合理优化，但 shortcut 绕过了“让真实存储操作自然报错”的前提。

选定修复恢复这条前提，只在三个绕过存储的出口调用已有 `GetBucketInfo`。它会让这些请求变贵，也会在降级集群上暴露真实错误；这两点都是明确成本。作为交换，SILO 恢复 S3 404 语义、升级兼容性与测试保真度，同时完整保留正常列表热路径的上游优化。

这个值得接受、范围受控的兼容修复现已合入绿色 `main`；release delivery 仍是独立门槛。
