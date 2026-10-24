---
title: "ListObjects 快捷路径不能把不存在的桶伪装成空桶"
linkTitle: "ListObjects NoSuchBucket"
date: 2026-08-26
lastmod: 2026-09-16
author: "冯若航"
summary: >
  三条 ListObjects 快捷路径会在访问存储前直接返回 EOF，导致不存在的桶被错误地表示为空列表。本文记录 SILO #32 / PR #37 的回归来源、S3 兼容性价值、只在快捷路径检查桶存在性的最小修复、集群扇出代价、衍生边界与验收决策。
tags: [设计, S3, 兼容性, ListObjects]
weight: 25
draft: false
url: "/zh/blog/design/listobjects-nosuchbucket/"
---

随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 发布的 [PR #37](https://github.com/pgsty/silo/pull/37)（PR 提交 [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377)，合并提交 [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef)，关闭 [SILO #32](https://github.com/pgsty/silo/issues/32)），修复了 `ListObjects`、`ListObjectsV2` 与 `ListObjectVersions` 中三条提前返回（early-return）快捷路径在目标桶不存在时错误返回 HTTP `200 OK` 空列表、而非 HTTP `404 NoSuchBucket` 的 S3 兼容性回归。

## 太长不看（TL;DR） {#tldr}

对不存在的桶执行普通 `ListObjects`、`ListObjectsV2` 或 `ListObjectVersions` 请求时，扫描存储层会触发 `BucketNotFound`；但以下三类输入会在访问存储前提前返回：

- `marker`（或 `start-after`）不以 `prefix` 开头；
- `max-keys=0`；
- `prefix` 以 `/` 开头，包括 [#32](https://github.com/pgsty/silo/issues/32) 中 `boto3` 使用的 `Prefix="/"`。

这三个分支原先直接返回 `io.EOF`，上层调用方将其解释为“列表正常结束”，导致客户端收到空的 HTTP 200，而非 S3 标准规定的 HTTP 404 `NoSuchBucket`。同一个不存在的桶，仅因过滤参数不同就从资源不存在错误变成成功响应，既破坏了 S3 兼容性，也阻塞了从回归前版本升级的用户。

修复该问题不能把昂贵的桶存在性检查重新加回每一次列表请求。选定方案仅将这三处裸 `io.EOF` 替换为调用辅助函数 `listPathShortcutEOF`：该函数调用一次 `GetBucketInfo`，当桶不存在或集群无法确认时返回真实错误，当桶存在时仍返回 `io.EOF`。正常列表热路径完全不变，额外的节点与磁盘扇出开销仅由原本会在访问存储前直接退出的快捷请求承担。

## 这是什么问题 {#problem}

### 同一个 API 出现两套桶存在性语义 {#two-semantics}

[#32](https://github.com/pgsty/silo/issues/32) 给出的最小复现是在不存在的桶上调用：

```python
s3.list_objects(Bucket="missing-bucket", Prefix="/")
```

AWS S3 抛出 `NoSuchBucket`，而 SILO 却返回一个成功的空列表。差异源于对象层 `listPath` 的控制流：

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

触发提前返回的不仅限于 `/` 前缀：

| 快捷条件 | 为什么结果必为空 | 修复前的缺陷 |
| --- | --- | --- |
| `marker` 不以 `prefix` 开头 | 当前实现不扫描该不相交区间 | 未确认桶是否存在即返回 `io.EOF` |
| `max-keys=0` | 调用方明确要求返回零个键 | 将“请求零条结果”错误等同于“桶资源有效” |
| `prefix` 以 `/` 开头 | SILO 的扁平键空间不会生成以 `/` 开头的对象名 | 过滤条件在检查桶身份之前发生短路 |

对于已存在的桶，这三个分支直接返回空列表是合理的快路径优化；但对于不存在的桶，同一个 `io.EOF` 会掩盖应当优先返回的资源错误。

### 追溯上游 `#18917` 引入的回归起点 {#regression}

报告者确认 `RELEASE.2024-01-29T03-56-32Z` 行为正确，而从 `RELEASE.2024-01-31T20-20-33Z` 开始出现回归。追溯提交历史可以定位到上游变更 [minio/minio#18917](https://github.com/minio/minio/pull/18917)（[`80ca12008`](https://github.com/minio/minio/commit/80ca120088be9950fa35467975dd9d8dc1bd4176)）：该提交从通用参数检查中移除了 `GetBucketInfo`，改为依赖后续实际的 `Put`、`List` 与 `Multipart` 存储操作自行暴露不存在的桶。

这一优化假设在请求真正进入存储层时成立，却遗漏了“提前返回路径根本不会到达存储层”的边界。#32 并不需要全面回滚 `#18917` 的优化，只需补齐被绕过的三处控制流出口。

## 为什么要修复 {#why-fix}

### S3 契约明确要求返回 `NoSuchBucket` {#s3-contract}

[AWS `ListObjects`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html) 与 [`ListObjectsV2`](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html) 均将 `NoSuchBucket` 定义为 HTTP 404（指定桶不存在）。`prefix`、`marker`、`start-after` 与 `max-keys` 仅用于筛选桶内对象，不能让不存在的桶变成一次成功请求。同时，`ListObjectVersions` 共享同一个对象层列表引擎，在三处快捷入口上统一桶存在性语义可避免 V1、V2 与版本列表行为分化。

### 错误的空列表会改变客户端控制流决策 {#client-impact}

空的 HTTP 200 与 HTTP 404 在客户端逻辑中代表截然不同的分支：

- HTTP 404 会指示部署脚本、SDK 或测试代码先创建桶、修正配置或终止流程；
- 空的 HTTP 200 则声明桶已存在，只是当前没有匹配的对象；
- 使用 SILO 作为本地 S3 替身的集成测试会在本地假性通过，部署到 AWS S3 时却直接报错。

### 修复面极窄且易于验证 {#repair-value}

该缺陷完全集中在 `cmd/metacache-server-pool.go` 的三个相邻提前返回分支中，不涉及对象数据、元数据格式、排序、分页令牌编码、IAM 权限或 XML 结构。

## 为什么不能简单恢复全局检查 {#performance-constraint}

上游在 [#18917](https://github.com/minio/minio/pull/18917) 中移除通用 `GetBucketInfo` 并非随意清理：每次 `Put`、`List` 与 `Multipart` 操作前先检查桶存在性会在所有节点间产生 RPC 扇出；即便经过向量化合并，当集群规模超过 100 个节点后，该开销依然十分显著。

在 SILO 当前实现中，`erasureServerPools.GetBucketInfo` 会调用 `S3PeerSys.GetBucketInfo`，并发向所有节点发起请求并按存储池聚合法定人数，每个节点还需检查本地桶状态。因此两个极端方案均不可取：

- **完全不检查：** 继续在不存在的桶上返回错误的空 HTTP 200；
- **每次 `List` 前都检查：** 恢复了 `404` 语义，却撤销了大型集群上的关键性能优化。

将 `GetBucketInfo` 严格限制在“不会访问存储、因而无法自然发现缺桶”的三条快捷分支上，即可在不影响正常列表热路径的前提下修复该兼容性缺陷。

## 具体修复方案 {#implementation}

### 仅替换三处裸 `io.EOF` 返回 {#three-shortcuts}

在 `cmd/metacache-server-pool.go` 中，三个快捷分支原先均执行：

```go
return entries, io.EOF
```

现统一改为调用 `listPathShortcutEOF`：

```go
return entries, z.listPathShortcutEOF(ctx, o.Bucket)
```

该辅助函数定义如下：

```go
func (z *erasureServerPools) listPathShortcutEOF(ctx context.Context, bucket string) error {
    if _, err := z.GetBucketInfo(ctx, bucket, BucketOptions{}); err != nil {
        return err
    }
    return io.EOF
}
```

其行为分为三类：

- **桶存在：** 返回 `io.EOF`，保留原有的空列表返回行为；
- **桶不存在：** 返回 `BucketNotFound`，交由既有错误映射生成 HTTP 404 `NoSuchBucket`；
- **集群状态无法确认：** 原样向上传播仲裁失败、节点离线、超时或上下文取消错误，不再伪造空成功响应。

正常的 `listMerged`、metacache 扫描、排序、分页与响应生成路径完全不变。

### 为什么辅助函数必须放在 `listPath` {#helper-boundary}

将检查紧贴 `listPath` 的快捷出口放置基于三点原因：

1. 只有 `listPath` 知道当前请求即将绕过所有底层存储访问；
2. 若上移到通用 HTTP 参数校验层，会让所有正常列表请求承担额外扇出开销；
3. 若下移到存储扫描层则完全无效，因为这三个分支根本不会进入扫描层。

### 为什么不引入桶存在性缓存 {#no-cache}

虽然增加 `bucket-existence cache` 可以降低快捷路径的扇出开销，但会立即引入桶创建、删除、跨站点复制、故障恢复与 TTL 过期窗口期的一致性失效问题。为了三个低频快捷分支引入第二套状态源，其复杂度与陈旧数据风险远高于收益。若未来生产遥测表明大型集群存在高频 `max-keys=0` 或 `/` 前缀探测流量，再基于真实观测数据评估限流或专用元数据快路径。

## 测试与评审证据 {#verification}

### 对象层契约测试 {#object-layer-tests}

对象层测试在单盘与多盘纠删码配置下，对以下四类输入逐一验证：

- 以 `/` 开头的 `prefix`（`Prefix="/"` 与 `Prefix="/sub"`）；
- `max-keys=0`；
- 不以 `prefix` 开头的 `marker`；
- 普通 `prefix`（作为由底层存储自然返回 `BucketNotFound` 的对照基准）。

每组测试均覆盖 `ListObjects`、`ListObjectsV2` 与 `ListObjectVersions`，并使用类型化的 `isErrBucketNotFound` 断言。

### HTTP 协议层契约测试 {#http-tests}

Handler 测试使用真实签名请求验证三个公开列表 API：

| API | 请求形态 | 断言 |
| --- | --- | --- |
| `ListObjects` | `GET /missing-bucket?prefix=/` | HTTP 404，XML 错误码为 `NoSuchBucket` |
| `ListObjectsV2` | `GET /missing-bucket?list-type=2&prefix=/` | HTTP 404，XML 错误码为 `NoSuchBucket` |
| `ListObjectVersions` | `GET /missing-bucket?versions&prefix=/` | HTTP 404，XML 错误码为 `NoSuchBucket` |

### 本地与 CI 质量门禁 {#local-gates}

修复通过了完整本地验证（`go test ./cmd -count=1` 耗时 116.2 秒、10 个新增对象层与 HTTP 回归子场景、定向 `go test -race`、`CGO_ENABLED=0 go build ./...`、`go vet ./...` 以及独立设计与代码审查）。在 GitHub Actions 上，带 DCO 签名的 PR 提交 [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377) 通过了 [DCO](https://github.com/pgsty/silo/actions/runs/32961304270)、[VulnCheck](https://github.com/pgsty/silo/actions/runs/32961304271) 及 [Go CI](https://github.com/pgsty/silo/actions/runs/32961304309) 全部 6 个构建测试任务；合并提交 [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef) 随后也独立通过了 [VulnCheck](https://github.com/pgsty/silo/actions/runs/32962256729) 与 [Go CI](https://github.com/pgsty/silo/actions/runs/32962256823)。

## 衍生风险与边界情况 {#derived-risks}

### 快捷路径请求现在会产生集群扇出 {#fanout-cost}

这是本修复唯一刻意接受的运行时成本：针对已存在桶的三类快捷请求过去仅相当于一次本地分支判断，现在需要调用 `GetBucketInfo`。本机微基准测试对比如下：

| 路径 | 本机观测耗时与分配 |
| --- | ---: |
| 修复前快捷路径 | 约 0.55 μs，7 allocs |
| 修复后单盘快捷路径 | 约 7.8–8.1 μs，45–47 allocs |
| 修复后 32 盘快捷路径 | 约 70–81 μs，977 allocs |
| 32 盘正常列表请求 | 约 0.95 ms |

在真实多节点部署中，`GetBucketInfo` 还包含跨节点网络往返与法定人数聚合延迟。这也正是为何绝不能将该检查扩展到正常列表热路径。若存在配置错误的客户端高频轮询 `max-keys=0`、`/` 前缀或不相交 `marker`，可通过 S3 追踪或监控指标识别并按需限流。

### 降级集群会暴露真实的仲裁错误 {#degraded-cluster}

过去当节点离线或桶仲裁不足时，快捷路径由于根本不接触集群状态，仍会返回空的 HTTP 200。修复后，这类请求在集群降级无法确认桶是否存在时会返回仲裁、超时或服务不可用错误，避免了在无法确认资源状态时谎称“存在有效空桶”。

### 桶创建与删除并发仍不具备线性化快照 {#race-window}

`GetBucketInfo` 与返回空列表是两个先后动作：桶可能在检查通过后立即被删除，或在形成缺桶错误后立即被创建。这与其他所有“先校验资源存在性、再执行操作”的 S3 API 属于同一并发模型。

### 依赖旧错误行为的客户端会收到 404 {#behavior-change}

此前误把缺桶上的空 HTTP 200 当成正常状态的客户端在升级后会进入 404 错误分支。这一行为变化恢复了 S3 标准契约以及 2024 年 1 月回归之前的历史行为。

### 刻意留在范围外的两个相邻边界 {#remaining-edges}

设计审查记录了两个不阻塞合并的低优先级边界：

1. **桶删除后的陈旧分页令牌：** 在恢复 metacache 分页续传（continuation）时，`c.fileNotFound` 分支仍直接返回裸 `io.EOF`。如果桶被删除后客户端携带陈旧或手工构造的 continuation token 请求，理论上仍可能收到空 HTTP 200。若在此处加入 `GetBucketInfo` 会影响所有正常分页续传请求的性能，需单独设计。
2. **Handler 层的 `NotImplemented` 校验优先级：** V1 与版本列表的某些 `marker`/`prefix` 组合会在 HTTP handler 参数校验阶段先返回 `NotImplemented`，尚未到达对象层（V2 的 `start-after` 则会进入对象层 `listPath`）。本补丁修复的是存储快捷路径掩盖缺桶错误，不改变畸形参数校验与资源错误之间的既有优先级。

## 评估并否决的替代方案 {#alternatives}

### 保持上游现状 {#keep-upstream}

优点是零性能变化且减少与上游分支的差异；缺点是继续违反 S3 契约、保留已知回归，并导致 SILO 在作为 S3 集成测试环境时给出错误信号。否决。

### 恢复通用 `checkBucketExist` {#restore-global-check}

虽然能一次覆盖所有路径，但会把跨节点扇出重新加回每一个 `Put`、`List` 与 `Multipart` 操作，直接撤销 `#18917` 的大型集群优化。成本与收益严重失衡，否决。

### 只修复 `Prefix="/"` {#slash-only}

仅修补 `/` 前缀虽能通过 `#32` 的单条 `boto3` 复现，但会遗留 `max-keys=0` 与不相交 `marker` 两个同源缺陷。三个分支在 `listPath` 中紧邻且语义完全相同，用同一个辅助函数收敛更完整。否决。

### 增加桶存在性缓存 {#existence-cache}

缓存虽能降低快捷路径延迟，但需要处理创建、删除、复制、自愈与 TTL 窗口期的陈旧状态。当前并无遥测数据表明这三类快捷请求具有足够高的流量来支撑一套新缓存，否决。

## 复杂度与成本收益评估 {#tradeoff}

| 维度 | 评价 | 说明 |
| --- | --- | --- |
| 生产代码复杂度 | 低 | 仅修改三处调用点并新增一个 7 行辅助函数；无新状态、依赖或磁盘格式 |
| 测试复杂度 | 低到中 | 同时覆盖 V1、V2、版本列表、三类快捷条件、正常前缀对照与 HTTP 404 映射 |
| 正常路径风险 | 极低 | `listMerged` 正常列表热路径无任何变更 |
| 快捷路径运行时成本 | 仅快捷路径上升 | 从本地分支返回变为集群级 `GetBucketInfo` 查询 |
| 兼容性收益 | 高 | 恢复 HTTP 404 `NoSuchBucket`、回归前升级兼容性及 S3 测试保真度 |
| 运维复杂度 | 无 | 无需数据迁移、配置项、特性开关或缓存维护 |

## 验收决策 {#decision}

补强后的 PR #37（保留 Jason Lin 在 [`e9c5340be`](https://github.com/pgsty/silo/commit/e9c5340be94044daf3410272af54bc98832dd377) 上的共同作者署名）已合并为 [`49c8aeac4`](https://github.com/pgsty/silo/commit/49c8aeac403916f52f8588bbe8ee42753d86eeef)，包含类型化错误断言、V1/V2/版本列表对象层覆盖及 HTTP 404 `NoSuchBucket` 验证，并随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 正式发布。

## 总结 {#conclusion}

本问题的根源在于列表引擎把 `io.EOF` 同时用于表达两件不同的事：“已存在桶的查询结果为空”以及“从未确认桶是否存在的提前过滤退出”。上游为优化大型集群性能而移除通用存在性检查，依赖的是“后续真实存储操作会自然暴露缺桶错误”这一前提。选定方案仅在三个绕过存储的出口调用 `GetBucketInfo`，在完整保留正常列表热路径性能的同时，恢复了这一前提与 S3 `NoSuchBucket` 协议契约。
