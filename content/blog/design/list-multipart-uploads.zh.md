---
title: "SILO 应该修复 ListMultipartUploads 吗？Issue #79 兼容性设计评审"
linkTitle: "ListMultipartUploads 兼容性"
date: 2026-08-30
lastmod: 2026-09-16
author: "冯若航"
summary: >
  SILO 把 ListMultipartUploads 的 prefix 当成精确对象键，并用节点本地的易失内存缓存回答存储桶级查询。本文解释问题及其来源，评估兼容性与运维影响，比较四种响应和存储方案，并建议分阶段采用“上传元数据加全局扫描”，而不是只修缓存或立刻引入持久化二级索引。
tags: [设计, S3, 兼容性, 分段上传]
weight: 35
draft: false
url: "/zh/blog/design/list-multipart-uploads/"
---

这是 [SILO Issue #79](https://github.com/pgsty/silo/issues/79) 的问题说明、设计分析与决策记录。

## 9 月 16 日实现与升级契约 {#implementation}

[PR #198](https://github.com/pgsty/silo/pull/198) 保留 mr javad seydi 的原始元数据与扫描实现，并追加维护者对 marker 消失、发现覆盖不足、取消确认和升级诊断的修复。本节说明这项源码变更。**Server 20260903 不包含此修复；源码实现也不代表生产性能与部署验收完成。** 下方 8 月 30 日的分析保留为历史设计记录。

### 列表与取消语义

新上传将 bucket 与原始对象键写入既有 `xl.meta`，完成时删除这些上传专用字段。严格列表跨 pool/set 发现持久上传，以既有读取 quorum 验证元数据，再全局处理 prefix、delimiter、`CommonPrefixes` 和最多 1,000 项的分页。节点重启或切换入口无需等待上传缓存重建。

排序为 `(key, 原生上传 ID 中的发起时间, 编码后的 upload ID)`。即使 marker 对应的上传已完成或取消，返回的 marker 仍然表示这个边界。该契约支持客户端回传服务端 marker，不承诺对随机上传 ID 做任意字典序比较。并发变更下，跨页遍历不是快照。没有 `key-marker` 时忽略 `upload-id-marker`；有 key marker 时，非法 base64 保留既有 404 行为，可解码但不支持的原生 ID 返回 400。不能解析的持久 ID 属于旧格式，不会用当前时间伪造发起时间。

每个 set 的目录枚举需要 `floor(N/2)+1` 块盘成功。例如四盘只有两盘可扫描时返回 503，即使两份元数据仍可读取。只有验证 bucket/key 与目录哈希一致后，单来源盘身份读取才能排除其他 bucket；不确定时升级为 quorum 读取。严格模式遇到旧格式返回 `MultipartListingNotReady`（503），身份不合法返回 `MultipartListingMetadataInvalid`（503），不会让整个请求悄悄退回缓存列表。

Abort 检查每个相关 pool，每 set 需要 `floor(N/2)+1` 份确定的不存在确认。部分删除导致元数据低于读取 quorum 后仍可重试。任一 pool 状态未知返回 503；全部确定不存在且本轮未找到上传则返回 `NoSuchUpload`（404）。逻辑取消成功后，离线盘上的分片数据仍可能等待后续清理。

**尚未解决的创建写入边界：** 如果创建上传的物理写入在调用方收到存储超时后继续执行，以上确认不能阻止它迟到提交。故障注入已复现 16 盘/EC:8 场景：取消成功后，七份迟到写入加上七份离线旧副本，可以恢复出可继续写入的上传。测试保留了这个已知限制；测试通过不表示此问题已修复。持久创建屏障需要独立的存储一致性设计。

### 协调升级

新增配置为 `api multipart_listing=strict|legacy`，默认 `strict`；环境变量 `MINIO_API_MULTIPART_LISTING` 优先。在迁移期间若需要旧行为，明确在所有服务端启用临时兼容模式：

```bash
mcli admin config set ALIAS api multipart_listing=legacy
```

Legacy 模式保留原有精确键与缓存限制。先升级**所有 writer**，停止产生旧格式上传，再使用已知 key/ID 完成或取消旧上传。切换模式后，应从头开始分页遍历。检查每台服务器的生效配置；环境变量覆盖存储的配置值。

只读预检接口为 `GET /minio/admin/v3/multipart-preflight`，使用 SigV4 签名，要求 `admin:StorageInfo` 权限。例如，由操作者提供凭据与地址：

```bash
curl --aws-sigv4 'aws:amz:us-east-1:s3' \
  --user "$SILO_ACCESS_KEY:$SILO_SECRET_KEY" \
  "$SILO_ENDPOINT/minio/admin/v3/multipart-preflight"
```

报告包含 `mode`、`ready`、`complete`、`scannedEntries`、`legacyUploads`，以及各 pool/set 的盘覆盖、未覆盖盘序号与最老旧上传的发起时间。它绕过上传缓存，检查包括暂停 pool 在内的持久状态，并识别只剩少数副本的旧上传。`ready=true` 要求全部盘可检查、候选元数据没有不可读状态、且未发现旧格式副本。它无法证明所有 writer 都已升级，也不能阻止并发旧 writer 再引入旧格式。离线盘、扫描错误、超时和预算耗尽均不能报告就绪；不完整计数不能当作零。磁盘恢复后以及切换严格模式前应重新预检：

```bash
mcli admin config set ALIAS api multipart_listing=strict
```

丢失原始 key/ID 的旧上传由既有 stale-upload 清理器处理，各服务器扫描自己的本地盘。年龄按创建时间计算，**不会被最近上传分片的活动刷新**。默认 24 小时过期、6 小时清理间隔不等于保证已经排空。临时降低 `api stale_uploads_expiry` 或 `api stale_uploads_cleanup_interval`，也会删除仍在进行的长上传和新格式上传。只能在维护窗口暂停或排空相关负载、记录原值并接受取消范围后操作；验证实际排空，恢复配置后再恢复业务。本次不新增按任意路径删除的管理接口。

### 扫描容量与证据边界

每个进程最多同时接受两个扫描，每扫描使用 16 个身份读取 worker 和四个全盘元数据读取 worker。目录读取传递有限 count 并检测溢出。请求合计预算为 100,000 个返回的目录条目，包含不同盘上的重复条目和哈希目录，**不代表支持列出 100,000 个唯一上传**。合计超限时，其他并发目录请求可能已经发出；超限返回 `SlowDown`（503），不能返回成功的局部页面。30 秒 context 预算停止后续调度，扫描 worker 退出前仍占用并发名额。这不是精确内存上限，也不保证已进入系统调用的物理 I/O 立即停止。

每一页仍需重扫持久状态，遍历成本随存储候选数与页数共同增长。测试覆盖 marker 消失、多 pool 覆盖、部分删除重试、身份读取回退、RPC 目录边界、取消后并发名额，以及已知迟到写入反例。临时多节点与维护客户端测试只证明记录环境中的功能行为；生产规模延迟和前台负载影响仍需按部署验收，源码合并不等于性能认证。

9 月 16 日的临时 Docker Desktop arm64 测试使用两节点、四个 APFS 绑定卷，两个 bucket 共 11,000 个上传，期间还有其他本地验证负载。目标 bucket 有 10,000 个上传，单次返回 1,000 项耗时 18.7 秒；两个并发请求约 25–27 秒后返回可重试的 `SlowDownRead`。这组观察没有达到暂定的单页五秒目标，也不是隔离的 SSD 基准。容量和前台负载验收仍未完成，不能把有界扫描宣传为大规模性能修复。

## 先用最简单的话说明问题 {#plain-language}

假设现在有四个大文件还没传完：

```text
tables/a/part-1
tables/a/part-2
tables/b/part-1
other/file
```

S3 客户端问：“把 `tables/` 下面所有没传完的上传列出来。”AWS S3 会返回前三个。SILO 目前却把 `tables/` 当成一个完整对象名，只查找是否存在一个名字恰好等于 `tables/` 的上传，于是返回空列表。

如果客户端去掉 prefix，要求列出整个存储桶里的所有未完成上传，SILO 又会走另一条捷径：读取当前进程里的内存缓存。创建这些上传的节点也许能看到四个结果，但缓存重启就消失，不同节点之间也不是权威一致的。上传数据仍然在磁盘上，只是列表说错了。

所以这不是“少支持了一个查询参数”那么简单。清理工具可能收到 `200 OK`，认定不存在未完成上传并报告成功，而磁盘上其实还有这些上传。服务端没有丢失已经提交的对象，但它向调用者展示了一个错误的未完成工作视图。

## 决策摘要 {#decision}

只要 SILO 仍希望宣称具有实用的 S3 兼容性，就应该修复这个行为。

修复的理由很明确：当前接口静默返回虚假的成功结果；重启或切换节点会改变答案；标准的 prefix 清理与分页流程无法工作。默认 24 小时的 stale-upload 清理器可以限制默认配置下的空间累积，却不能让 API 响应变得真实。

但这也不是一个小改动。现有上传目录只保存了 bucket 与 object key 的单向哈希，原始对象键没有写入 `xl.meta`。正确实现必须从新上传开始持久化这份身份信息，按纠删码 quorum 规则发现候选项，在所有 pool/set 之上统一执行 S3 语义，并处理滚动升级期间的 legacy 上传。

因此建议的方向是：

1. 把 bucket 与 object key 写进上传现有的 quorum 元数据；
2. 以有界的按需扫描作为持久化正确性路径；
3. 缓存只能是可重建的优化，不能是真相来源；
4. 只有所有 writer 都完成升级、无键 legacy 上传全部排空后，才能启用严格 S3 行为；
5. 只有测量证明扫描达不到产品批准的服务目标时，才考虑持久化二级索引。

## 问题描述与证据来源 {#sources}

本文的问题判断与方案建立在五类证据之上。

### S3 正式契约 {#source-s3}

[AWS ListMultipartUploads API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) 定义了通用存储桶的公开契约：

- `prefix` 选择所有 key 以该字符串开头的上传；
- `delimiter` 把匹配的 key 汇总成 `CommonPrefixes`；
- `max-uploads` 限制单页数量，文档规定上限为 1,000；
- `key-marker` 与 `upload-id-marker` 用来继续被截断的列表；
- 没有 `key-marker` 时必须忽略 `upload-id-marker`；
- 结果先按对象键排序，同一对象键的上传再按发起时间升序排列。

AWS 文档并没有无歧义地覆盖所有实现边角。同一时间戳、非法或越界的 `max-uploads`、URL 编码、marker 边界，以及 `CommonPrefixes` 如何占用分页名额，都应该在实现前对 AWS 做一次取证，并把结果保存成固定 fixture。

### Issue 的原始报告 {#source-issue}

[Issue #79](https://github.com/pgsty/silo/issues/79) 提供了一个自包含、自己签名请求的复现程序，在 `pgsty/silo:latest` 上运行，并与 AWS、RustFS、SeaweedFS 和 Garage 比较。它的四个核心观察都可以复现：

| 请求 | 应有行为 | SILO 实际行为 |
| --- | --- | --- |
| `prefix=t/` | 返回三个以 `t/` 开头的 key | 一个上传也不返回 |
| `max-uploads=1` | 返回一项和续页 marker | 返回缓存中的全部上传 |
| `key-marker=t/a_b/p2` | 从这个 key 之后继续 | 返回缓存中的全部上传 |
| `prefix=t/&delimiter=/` | 返回汇总后的 `CommonPrefixes` | upload 与 prefix 都不返回 |

Issue 正确识别了兼容性失败，但“`max-uploads` 总是被忽略、`IsTruncated` 永远为 false”的表述覆盖面过大。这些结论在复现程序经过的无 prefix 缓存路径成立；精确对象路径能够处理 `max-uploads` 和 `upload-id-marker`，也能够设置 `IsTruncated`。

### 上游设计历史 {#source-upstream}

这个行为是继承来的，并非 SILO 独自发明：

- MinIO 在 2017 年通过 [PR #5248](https://github.com/minio/minio/pull/5248) 有意删除纠删码后端的 prefix listing，理由是“简化” multipart 支持；
- MinIO 在 2024 年通过 [PR #20407](https://github.com/minio/minio/pull/20407) 增加了无 prefix multipart 缓存，主要为了满足 Alluxio 测试；
- 2025 年报告相同 exact-key 行为的 [MinIO Issue #20989](https://github.com/minio/minio/issues/20989) 被以 working as intended 关闭；
- SILO 当前的 [S3 兼容性参考](/zh/reference/s3-api-compatibility/#id5) 已经记录“必须使用精确对象名”的差异，但在本文之前没有解释缓存、分页、marker、delimiter 与重启限制。

这些历史可以解释代码为什么是有意如此，却不能让接口符合 AWS 契约。

### 源码审查 {#source-code}

当前源码存在两条互斥的 listing 路径：

```text
erasureServerPools.ListMultipartUploads
  prefix == ""  -> 返回节点本地 mpCache 中的条目
  prefix != ""  -> 把 prefix 当成完整对象键做哈希
                    -> 只选择一个 set
                    -> 只列一个 sha256(bucket/object) 目录
```

关键位置包括：

- [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-server-pool.go)：无 prefix 的 `mpCache`、逐 pool 拼接，以及 `NewMultipartUpload` 内部使用的精确对象查询；
- [`cmd/erasure-multipart.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-multipart.go)：精确对象 listing、上传目录构造、stale-upload 清理，以及新上传 `xl.meta` 的 quorum 写入；
- [`cmd/erasure-sets.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-sets.go)：把传入的对象名哈希到单个 erasure set；
- [`cmd/bucket-handlers.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/bucket-handlers.go)：公开请求校验，其中包括 `key-marker` 不属于 prefix 时返回 `501 NotImplemented` 的保护；
- [`cmd/object-api-multipart_test.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/object-api-multipart_test.go)：虽然有大型期望结果表，但最后的断言只检查回显的标量，没有验证 uploads、prefixes、markers 或截断状态。

### 独立复现与对抗性审查 {#source-review}

审查者用单节点服务和 SigV4 请求，在被审查的 SILO 源码上独立复现了 Issue 场景。额外探针确认：

- 精确对象键能够给该对象自己的多个上传分页；
- 当前精确键路径即使没有 `key-marker` 也会使用 `upload-id-marker`，与 AWS 不符；
- 精确键被截断时，`NextKeyMarker` 仍为空；
- 当前路径把 `max-uploads=0` 当成无限制；
- 普通服务重启会让 bucket-wide 视图变空，而精确键查询仍能找到磁盘上的上传。

第二轮对抗性架构审查进一步挑战了存储、quorum、迁移、suspended pool、混合版本与性能假设。相关修正已经进入下文；本文不会把 AI 审查当作代码测试或 AWS 兼容性取证的替代品。

## 当前代码到底做了什么 {#current-behavior}

### 空 prefix：易失的节点本地视图 {#empty-prefix}

没有 prefix 时，pool 层从 `mpCache` 返回该 bucket 的全部 `MultipartInfo`，并且只按发起时间排序。它不应用 `max-uploads`、`key-marker`、`upload-id-marker` 或 `delimiter`，也不计算续页 marker 或 `IsTruncated`。

进程启动时缓存为空。创建上传只填充处理该请求的节点。完成和中止会删除缓存项，部分路径还会通知 peer 删除，但创建没有等价的持久化集群广播，也没有启动重建。因此：

- 重启可以让非空列表变成空列表；
- 两个节点可以对同一存储桶返回不同答案；
- 成功响应不能证明服务端已经枚举了持久化上传状态。

### 非空 prefix：精确对象查询 {#nonempty-prefix}

存在非空 prefix 时，这个字符串会像完整对象名一样进入对象哈希。系统选择一个 erasure set，然后读取由 `sha256(bucket/object)` 派生的目录。

这条路径可以枚举同一精确对象的多个 upload ID。它按发起时间排序，应用自己的 `upload-id-marker`，在 `max-uploads` 处停止并设置 `IsTruncated`。但它仍然没有实现词法 prefix 匹配、`CommonPrefixes`、通用 key-marker 语义或 `NextKeyMarker`。

### 多 pool 让分页更加不正确 {#multiple-pools}

多 pool 部署收到非空请求时，pool 层会用相同上限分别调用每个活动 pool，然后直接拼接结果。它不会做全局有序归并，也不会重新计算分页边界和 next markers。请求 `N` 个结果时，可能从每个 pool 各取 `N` 个。

Listing 与其他公开 multipart 动词都会跳过 suspended pool。因此，留在 suspended 或 decommissioning pool 上的未完成上传不只是“没有列出来”，而是完全无法访问。这是相关的生命周期缺陷，但 listing 不能单独展示 `PutObjectPart`、`ListParts`、`CompleteMultipartUpload` 和 `AbortMultipartUpload` 都无法操作的句柄。pool drain 或强制 abort 应当作为覆盖所有动词的独立设计。

## 为什么现有上传无法回填 {#no-backfill}

Multipart 命名空间是平的：

```text
.minio.sys/multipart/<sha256(bucket/object)>/<upload-id>/xl.meta
```

哈希是单向的，路径里没有原始 bucket 和 key。当前 multipart `xl.meta` 里也没有保存名称字段；传入的对象名只在 `newFileInfo` 构造过程中影响 erasure distribution。

因此，全目录扫描可以知道“这里有一个上传”，却无法知道它属于哪个 bucket 或 key。当前节点本地缓存也无法可靠修复这件事，因为它跨节点不完整，重启后还会消失。

这否决了一个很诱人的“小修复”：扫描所有现有 `xl.meta` 再应用 prefix 过滤。系统必须为新上传增加可恢复的身份元数据或持久化索引，同时为旧的 keyless 上传制定明确迁移策略。

## 复杂度评估 {#complexity}

纯语义算法不是最难的部分。真正困难的是：如何在不把一次 listing 变成失控的全集群元数据风暴的前提下，得到完整、满足 quorum、能够全局排序的输入集合。

| 领域 | 复杂度 | 原因 |
| --- | --- | --- |
| 纯 S3 过滤与分页 | 中 | 规则数量有限，但 marker 和 delimiter 边角需要 AWS 取证。 |
| 把 bucket/key 写入新上传元数据 | 中 | 复用现有 quorum 写入，但要验证完成、回退、healing 与复制兼容性。 |
| 候选发现 | 高 | 命名空间混合所有 bucket，并且每个上传在 erasure drives 上重复；只查一块盘会漏掉仍满足 quorum 的上传。 |
| Quorum 与并发删除 | 高 | 扫描既要拒绝少数盘残留的幽灵项，又要容忍 abort、complete、GC rename-to-trash 与瞬时 `ENOENT`。 |
| 多 pool 全局分页 | 高 | 必须在所有可访问 pool/set 之上统一归并、排序、截断并生成 marker。 |
| 滚动迁移 | 高 | 旧 writer 会继续创建 keyless 上传，旧 completer 可能保留未知内部元数据。 |
| 性能与资源控制 | 高 | 一个 bucket 请求可能需要检查全集群的所有活动上传，而不只是该 bucket。 |

总体判断：这是一个高复杂度兼容性项目，wire 兼容风险为中，正确实现的风险为高。它不是破坏性的对象格式迁移：推荐方案只给新的未完成上传增加内部元数据，并保持现有目录结构不变。

## 兼容性与运维影响 {#impact}

### Wire 行为变化 {#wire-impact}

正确实现会有意改变外部可见结果：

- `prefix=foo` 将匹配 `foo`、`foobar` 与 `foo/...`，不再只匹配精确键 `foo`；
- bucket-wide 结果将按 key 与发起时间排序，而不是只按发起时间；
- `max-uploads` 会真正限制单页；
- 默认值与最大值会从 SILO 当前的 10,000 常量向 AWS 的 1,000 收敛，具体边角以取证契约为准；
- 客户端必须跟随 `NextKeyMarker` 和 `NextUploadIdMarker`，不能再假设一个响应包含全部结果；
- delimiter 请求会返回 `CommonPrefixes`；
- 当前 handler 在 marker 不属于 prefix 时返回的 `501`，将被取证后的 AWS 语义替代。

这些是兼容性修复，但可能破坏意外依赖 SILO 旧行为的软件。特别是忽略分页的客户端，修复后可能只看到更少的首屏结果。因此严格行为应通过明确的发布和 rollout 契约引入，不能偷偷混进一个无关 patch。

### 存储格式兼容性 {#storage-impact}

推荐写路径是在新上传现有的 quorum `xl.meta` 中加入保留的内部 bucket 与 object key 元数据。它不重命名 multipart 目录，也不创建第二个事务写入位置。

在 `CompleteMultipartUpload` 把上传元数据 rename 成最终对象之前，必须删除这些只属于上传的字段，位置与当前已经删除 multipart checksum 字段的逻辑相同。

旧二进制完成由新二进制创建的上传时，不知道要删除新内部键。这些键不会暴露成 S3 用户元数据，但会惰性地留在已完成对象的内部元数据中。滚动升级测试必须证明未知保留键不会影响 healing、复制、元数据比较或降级读取。随后产品需要在“容忍残留”和“增加 scrubber”之间选择，不能假设它会自动消失。

### 运维成本 {#operational-impact}

因为所有 bucket 共用同一个平坦哈希命名空间，按需扫描的复杂度是 `O(全体活动 multipart uploads)`，而不是 `O(目标 bucket 的 uploads)`。有界并行、取消、内存限制与失败行为属于正确性要求，不是可有可无的调优。

SILO 默认在 24 小时后过期 stale multipart upload，每 6 小时清理一次。最后一个旧 writer 升级后，keyless population 在通常情况下应当在大约 30 小时内排空。配置了更大自定义 expiry 的运维方会有更长迁移窗口。当前代码把零值映射回默认 24 小时，本次审查没有找到受支持的“禁用 expiry”取值。

清理器能限制默认空间累积，却不能修复虚假的 listing 响应，也不能替代对持续合法 multipart 活动、故障模式和自定义 expiry 的测试。

### 严重度 {#severity}

建议定级为 **P1 / 高兼容性问题**，而不是 P0：

- 没有发现已经提交的对象数据丢失；
- 没有绕过安全边界；
- 未完成上传在 complete、abort 或被清理前仍在磁盘上；
- 默认 stale-upload 清理可以限制普通配置下的累积。

之所以仍然是高而不是中，是因为服务端返回了伪造的成功结果，答案会在重启或切换节点后变化，并且会让清理与静默期检查工具产生错误信心。

## 候选方案 {#options}

### 方案 0：保持现状 {#option-zero}

没有工程成本，也保留所有偶然行为；同时继续保留虚假的 `200 OK`、节点本地不一致、重启易失、prefix 清理失败，以及对 S3 支持范围不准确的印象。

只有当 SILO 明确降低公开兼容性承诺、把该接口视为不支持时，这个选择才勉强成立。即便如此，明确拒绝也优于静默返回不完整成功。

**决策：不能作为长期方案。**

### 方案 1：明确且有文档的差异 {#option-divergence}

对 SILO 无法正确处理的参数组合返回稳定的 `NotImplemented` 类错误，并准确记录支持子集。这比完整兼容小得多，也在运维上更诚实。

它仍然是破坏性行为变化：现在拿到空列表或无界 `200 OK` 的工具可能会开始让作业失败；它也没有得到一个 S3 兼容接口。错误行为和默认发布策略必须有意识地确定。

**决策：如果完整兼容被拒绝或推迟，可以作为短期止血；它不是兼容性修复。**

### 方案 2：持久化身份、扫描持久状态、可选缓存 {#option-scan}

每次创建新上传时，把 bucket 与 key 写入上传现有 `xl.meta` 的保留内部元数据。Listing 时遍历可访问 pool/set 的上传目录，按 erasure read quorum 验证候选，再执行一个全局 S3 语义层。缓存只有在能够从持久化状态重建和对账时才允许加速这条路径。

它不增加第二个写事务，也不改变目录布局。主要代价是全集群扫描。

**决策：推荐，但必须先通过性能与故障模式原型。**

### 方案 3：持久化的 bucket 级有序索引 {#option-index}

维护一个按 bucket、key 与 upload identity 排序的二级索引。Listing 可扩展且天然支持分页，但 create、complete、abort、healing、回退与 reconciliation 必须在各种失败下维持两个位置的一致性。这个设计类似 MinIO 在简化该子系统时有意移除的 multipart 索引结构。

**决策：除非测量证明方案 2 无法满足产品批准的服务目标，否则 NO-GO。**

### 被否决的变体：只修 `mpCache` {#option-cache-only}

给当前缓存增加过滤、排序、分页、create 广播或启动重建可以改善表象，却不能单独建立一个持久化、满足 quorum 的真相来源。只修缓存很可能得到一个“看起来更可信、实质仍不正确”的答案。

**决策：否决。缓存可以优化正确读路径，不能定义它。**

## 推荐设计 {#recommended-design}

### 1. 先冻结公开契约 {#contract-first}

为通用存储桶建立一套有记录的 AWS fixture，覆盖：

- 跨 key 排序，以及同 key 多个上传的排序；
- 相同发起时间与确定性的全序 tie-break；
- prefix 与 exact-key 重叠；
- key-marker 单独使用和配合 upload-id-marker；
- 没有 key-marker 时的 upload-id-marker；
- delimiter、`CommonPrefixes` 与分页计数；
- 省略、0、1、1,000 和大于 1,000 的 `max-uploads`；
- `encoding-type=url`；
- 空页、末页与 next-marker 的取值。

把取证响应保存成仓库 fixture，CI 不应依赖实时 AWS 访问。

### 2. 在现有写入中持久化可恢复身份 {#write-path}

在 `NewMultipartUpload` 中，在现有 `writeAllMetadata` quorum 写入之前，为规范化 bucket 与 object key 增加保留内部元数据。具体键名属于实现细节，但必须带版本、无歧义、受现有 object-key 大小限制约束，并且不能暴露到客户端元数据。

成功完成时，在把 `fi.Metadata` 复制到最终对象元数据、执行 `renameData` 之前删除这些 upload-only 键。Abort 与 stale cleanup 已经删除整个上传目录，不需要额外索引操作。

### 3. 分开“发现候选”与“验证有效” {#read-path}

候选发现和候选有效性是两个不同问题。

对于每个可访问、非 suspended 的 pool 与 set：

1. 按配置的 list-quorum 策略，从所需的所有在线盘列出 hash 与 upload 候选目录；
2. 对目录名做 union 和去重；
3. 通过正常 erasure 元数据路径读取候选 `xl.meta`；
4. 只有元数据满足 quorum 且包含合法 bucket/key identity 时才纳入结果；
5. 容忍候选在 abort、complete 或 stale cleanup 过程中消失；
6. strict list quorum 下，如果所需 set 无法评估，应让请求失败，而不是返回部分成功的 `200 OK`。

只用第一块健康盘做候选发现是不够的：那块盘可能在一个仍满足 quorum 的上传创建时处于离线状态。

### 4. 只做一次全局语义处理 {#semantic-layer}

把所有 pool/set 的有效候选送进一个纯语义层。它统一负责 bucket 过滤、prefix、delimiter 汇总、排序、markers、最大页计数、URL encoding、`IsTruncated` 与 next markers。

在全局归并前不能应用 pool-local limit 和 marker。相同候选被重复发现时结果必须确定，而且无论请求落到哪个节点都应该得到同一答案。

### 5. 保留内部精确对象操作 {#exact-helper}

`erasureServerPools.NewMultipartUpload` 当前调用 `ListMultipartUploads(bucket, object, ...)`，目的是让同一对象的另一个上传进入相同 pool。如果公开函数开始把参数解释为词法 prefix，`foo` 可能匹配 `foobar` 并选错 pool。

增加一个命名收敛的内部 helper，例如 `FindMultipartUploadPool` 或 `ListMultipartUploadsExact`。它应继续使用现有对象哈希路径，不能共享公开 prefix 语义。

### 6. 缓存只能是优化 {#cache}

可以直接删除现有 `mpCache`。如果保留，它必须满足：

- 持久化状态始终是权威；
- 启动时能够重建；
- create、complete 与 abort 更新能够一致传播；
- reconciliation 能发现漏掉的事件与过期条目；
- 冷缓存或分歧缓存会回退到 quorum 扫描；
- 关闭缓存时所有 correctness 测试仍然通过。

### 7. 通过滚动迁移门槛启用严格行为 {#migration}

Legacy 上传记录缺少 bucket/key identity，无法可靠反推。使用两个对外有意义的模式：

- **legacy mode**，升级后的初始默认：新 writer 持久化身份；统计并排空 keyless 上传；混合 keyed/keyless population 的响应策略必须明确选择；
- **strict mode**：只有所有 writer 节点都声明支持新元数据、观测到的 keyless count 为零时才能启用。此后重新发现 keyless 上传必须报错并产生异常遥测，不能静默遗漏。

短期 shadow 对比可以验证新 scanner，但除非原型发现必要性，否则不需要永久的第三种运行模式。在默认 expiry 下，最后一个旧 writer 停止后，预计用一天再加一个清理周期排空 legacy。

Legacy mode 仍有一个未决产品选择：

| 策略 | 优点 | 代价 |
| --- | --- | --- |
| 返回完整的 keyed 子集，并用文档和遥测说明 | 有界排空期间工具仍可运行 | 普通客户端看不到“不完整”事实，仍会收到不完整 `200 OK` |
| 只要存在 keyless 上传就让 listing 失败 | 永远不伪造完整性 | 整个排空窗口会阻塞清理和现有作业 |

这个选择必须写进 ADR。Strict mode 没有这种歧义：前提被破坏时必须显式失败。

### 8. 把 suspended-pool 生命周期拆开处理 {#suspended-pools}

Listing 的第一版应与其他 multipart 动词的可访问性契约一致，只扫描非 suspended pool。单独把 suspended-pool 条目加入 listing，会暴露无法继续上传、完成或中止的句柄。

为 pool drain 期间的未完成上传另开生命周期设计：可以在上传结束前保持全部 multipart 动词可用、迁移上传，或按文档策略强制 abort。不要把它偷偷塞进 #79。

## 性能原型与决策规则 {#spike}

方案 2 只有一个持久写入位置，因此是首选；但它的扫描成本必须测量，不能假设。

在不同 pool、set 与 drive 数量组合下生成 1,000、10,000 与 100,000 个活动上传，测量：

- 冷热状态下的 p50/p95/p99 延迟；
- 总体与逐盘 `ListDir` 操作数；
- 元数据读取和节点间 RPC 数；
- 峰值内存与分配量；
- 取消延迟；
- 慢盘、离线盘、healing 与间歇消失磁盘下的行为；
- 同时发生 create、complete、abort 与 stale cleanup；
- 高选择性 prefix、空 prefix、首页与深页成本。

验收阈值是产品决策，必须在解释结果前记录。猜测的一两秒目标不是证据。如果扫描能在有界资源下满足批准的目标，就否决方案 3；如果不能，就用测量结果设计解决已证明瓶颈的最小持久化索引。

## 测试与发布关卡 {#gates}

### 语义与单元测试 {#unit-tests}

- 根据记录的 AWS fixture 生成纯表格测试；
- 覆盖排序、marker、delimiter、encoding、截断与 maximum 边角；
- 用属性测试保证分页后每个逻辑上传恰好出现一次；
- 重复候选和相同时间戳下保持确定性。

### Object 与 handler 测试 {#handler-tests}

- 强化现有 object-layer 表格，断言 uploads、common prefixes、markers 与截断；
- 解析并验证 handler XML body，而不是只检查状态码；
- 验证默认和非法 `max-uploads`；
- 独立测试 exact helper 的 pool 选择，不与公开 prefix 语义混用。

### 分布式与故障测试 {#failure-tests}

- 重启等价性与切换节点等价性；
- 多 set、多 pool 下只有一个全局页边界；
- 候选在一块盘缺失但整体满足 quorum；
- 部分 abort 后少数盘残留的幽灵条目；
- 并发 complete 与 GC rename-to-trash；
- 每种受支持 `list_quorum` 策略下的 set 不可用；
- 滚动升级、旧 writer 重新加入、降级 complete 与 strict mode 门槛；
- healing 与 replication 对未知内部元数据的处理。

### 交付关卡 {#delivery-gates}

1. 批准 ADR，包括产品模式与性能 SLO；
2. 提交兼容性 fixture；
3. 完成并评审存储原型；
4. 实现并通过定向、全量、race 与故障 QA；
5. 更新 S3 兼容性参考与运维说明；
6. 提交并合并源码变更；
7. 构建并标识 release artifact 或容器镜像；
8. 对滚动升级做 canary，观察 keyless-drain 遥测；
9. 只有所有门槛满足时才启用 strict mode；
10. 验证线上端点后再关闭 #79。

前一个关卡通过，不代表后一个关卡已经发生。

## 最终建议：应该改，但不能急着改 {#final-recommendation}

无限期保留当前接口是错误的权衡。这不是一个冷门响应字段不一致：它影响未完成数据的发现与清理，返回成功但错误的答案，而且会随节点与重启变化。这些性质损害了 S3 兼容性在实践中的含义。

但直接写一个实现补丁同样是错误的权衡。当前磁盘布局无法识别 legacy 上传；正确扫描必须具备 erasure-aware discovery 与 quorum；wire-correct 分页又会改变客户端可见行为。

平衡后的决策是：

- **GO**：ADR、AWS fixture 取证、metadata-plus-scan 原型，以及性能/故障原型；
- **有条件 GO**：产品 SLO 与 legacy 响应策略批准后采用方案 2；
- **NO-GO**：只修缓存、立刻引入持久化二级索引、在 patch release 中默认 strict，或在证明滚动升级门槛可达之前关闭 Issue；
- 如果没有实现资源，**GO**：采用明确、有文档、稳定报错的差异行为，而不是继续伪造成功 listing。

这样既守住兼容性纪律，也不会假装一个高风险的分布式 listing 变更只是两行 bug fix。
