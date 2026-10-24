---
title: "ListMultipartUploads 行为契约与设计权衡"
linkTitle: "ListMultipartUploads"
date: 2026-08-30
weight: 20
description: "说明为什么 Server 20261018 将公共 ListMultipartUploads 恢复为 MinIO 兼容行为、16 盘纠删集上的磁盘扫描开销，以及保留下来的分片上传修复。"
url: "/zh/blog/design/list-multipart-uploads/"
---

本文记录 `ListMultipartUploads` 在完整工程生命周期中的设计与演进：Server `20261018` 当前采用的 MinIO 兼容契约、16 盘纠删集容量压测后于 10 月 18 日执行的部分回滚、10 月 17 日无条件磁盘扫描尝试（`#243`，合入提交 [`7e9454456`](https://github.com/pgsty/silo/commit/7e9454456ee7065cd1d782fc4498338324a94894)）、9 月 16 日可选 `strict` 模式（`#198`），以及 8 月 30 日的原始根因分析。

## Server 20261018 当前行为契约 {#implementation}

Server `20261018` 在 `main` 分支上恢复了传统的 MinIO 兼容公共 `ListMultipartUploads` 契约（提交 [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423)，随后由 [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) 补齐空父目录清理修复）：

- 不带 `prefix` 时，`ListMultipartUploads` 返回当前节点内存分片缓存（`multipartUploadsCache`）中跟踪的上传记录。
- 带非空 `prefix` 时，`ListMultipartUploads` 将 `prefix` 视为精确对象键（`sha256(bucket/object)`），直接检查磁盘上该对象对应的分片上传目录。
- `delimiter`、`key-marker`、`upload-id-marker` 与 `encoding-type` 仍由 HTTP 处理器解析并在需要时校验（如 `encoding-type=url`）及回显到 XML 响应中，但候选集选取遵循 MinIO 兼容的“内存缓存 / 精确对象键”路径，不再对 `.minio.sys/multipart` 执行全盘扫描。
- `UploadID`、`GetMultipartInfo`、`PutObjectPart`、`ListObjectParts`、`CompleteMultipartUpload` 与 `AbortMultipartUpload` 在进程重启后仍可凭 `Bucket + Object + UploadID` 正常工作，因为活跃上传持久化在磁盘 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` 下。
- `MINIO_API_MULTIPART_LISTING` 与 `api multipart_listing` 保留为兼容性空操作（no-op），旧脚本或已保存配置无需修改即可继续启动。
- `GET /minio/admin/v3/multipart-preflight` 保持可用，固定返回 `mode: "legacy"` 且不兼容上传数为 `0`。

## 为什么在 2026-10-18 回滚默认磁盘扫描 {#decision-20261018}

在 `2026-10-17`（`#243`，提交 [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6)）至 `2026-10-18`（提交 [`4733e1423`](https://github.com/pgsty/silo/commit/4733e1423)）之间，`main` 曾短暂将所有公共 `ListMultipartUploads` 请求统一切换为对 `.minio.sys/multipart` 的无索引磁盘扫描。针对 16 盘纠删集的容量分析与基准测试表明：将该磁盘扫描设为无条件默认路径，会引入比原有列表限制严重得多的可用性故障模式。

### 为什么进程重启不会删除未完成的分片上传

未完成的分片上传持久化在磁盘路径 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta` 与 `part.*` 下。服务进程重启只会清空内存中的 `multipartUploadsCache`，**不会**删除磁盘上的未完成上传。因此，客户端持有的 `UploadID` 在重启后依然有效，直至完成合并、显式中止（Abort），或被后台过期清理任务回收（默认过期时间 7 天，巡检周期 12 小时）。

由于未完成上传会跨重启和客户端重试不断累积，任何遍历磁盘 `.minio.sys/multipart` 的操作，其开销都取决于纠删集当前存留的未完成上传总数，而非仅取决于本次进程启动后新建的上传数。

### 100,000 目录项保护阈值在 16 盘纠删集上的失效机制

10 月 17 日的磁盘扫描实现在整个纠删集**所有磁盘合计**的粒度上施加了 `maxMultipartWalkEntries = 100000` 上限，将每块磁盘上的 `<sha256(bucket/object)>` 目录项与 `<uploadID>` 目录项一并计入预算。

对于包含 $N$ 块磁盘、跨 $H$ 个不同对象键共有 $U$ 个活跃上传的纠删集，一次未命中缓存的桶级 `ListMultipartUploads` 扫描需要遍历的目录项总数为：

$$\text{entries} = N \times (H + U)$$

当每个上传对应不同对象键（$H = U$）时：

- 在 **4 盘**纠删集上，$4 \times (10{,}000 + 10{,}000) = 80{,}000$ 个目录项，恰好落在 `100,000` 阈值以内。
- 在 **16 盘**纠删集上，$16 \times (3{,}126 + 3{,}126) = 100{,}032$ 个目录项——整个纠删集（所有桶合计）只要累积到 **3,126 个活跃上传**，就会突破 `100,000` 上限，导致所有公共列表请求直接返回 HTTP `503 SlowDown`。
- 即便所有上传都集中在**同一个对象键**（$H = 1$）下，16 盘纠删集在单键累积到 **6,250 个上传**时也会达到 $16 \times (1 + 6{,}250) = 100{,}016$ 个目录项，使精确对象键查询（`prefix=<exact-object-key>`）同样因 `503 SlowDown` 失败。

### 演进脉络与问题定责

| 变更阶段 | 日期 / 提交 | 具体改动 | 工程评估 |
| :--- | :--- | :--- | :--- |
| 引入可选 `strict` 模式（`#198`） | `2026-09-16` / [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc) | 在 `MINIO_API_MULTIPART_LISTING=strict` 后提供磁盘扫描列表，默认保持 `legacy` | 提供了安全的按需启用边界，但最初缺少目录遍历硬上限 |
| 安全加固（`SN-2026-009`..`012`） | `2026-09-16` / [`143f6970d`](https://github.com/pgsty/silo/commit/143f6970d) | 增加 `checkUploadID`、`maxMultipartWalkEntries = 100000`、`503 SlowDown` 映射及 `readQuorum` 过滤 | 为磁盘扫描补齐了必要的 DoS 保护，但按全部 $N$ 块盘的原始目录项总数计费 |
| 无条件统一为磁盘扫描（`#243`） | `2026-10-17` / [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6) | 移除 `legacy` 分支，将所有公共 `ListMultipartUploads` 强制路由到磁盘扫描 | **步子迈得过大**：仅凭 4 盘单键基准测试就将无索引磁盘扫描设为必经路径，在 16 盘纠删集上于 3,126 个上传处触发 `503 SlowDown` |

### 部分回滚方案权衡对比

| 备选方案 | 公共 S3 列表语义完整度 | 16 盘纠删集容量表现 | 存储格式与后台 I/O 影响 | 决策 |
| :--- | :--- | :--- | :--- | :--- |
| 保留 `#243` 无条件磁盘扫描 | 在 16 盘 3,125 个上传以内支持完整前缀/分隔符/游标分页 | 在全集累积 3,126 个不同键上传时立刻触发 `503 SlowDown` | 每次未缓存列表产生 `16 × (1 + H)` 次 `ListDir` RPC | **淘汰** |
| 调高或移除 `maxMultipartWalkEntries` | 超过 3,126 个上传后仍能继续扫描 | 重新打开无索引 `.minio.sys/multipart` 上的无界 $O(N \times U)$ 磁盘遍历与内存分配风险 | 并发 `GET /bucket?uploads` 下延迟与文件描述符/RPC 放大严重 | **淘汰** |
| 构建持久化按桶分片索引 | 无需全盘扫描 `sha256(bucket/object)` 即可支持完整 S3 列表 | 开销仅与匹配前缀的上传数成正比 | 需要全新的分布式元数据索引、自愈协议与崩溃恢复契约 | **延后**（需独立立项设计索引） |
| 对 `#198`、`143f6970d` 与 `#243` 执行完整 `git revert` | 恢复 MinIO 兼容列表行为 | 无 `100,000` 目录项悬崖 | 会连带丢弃 `checkUploadID` 路径穿越防护、Abort 缓存/节点通知清理以及 `xl.meta` 身份元数据 | **淘汰** |
| **外科手术式部分回滚（`4733e1423` + `0f9199e0c`）** | 恢复 MinIO 兼容公共列表（空前缀走缓存、非空前缀走精确键查盘） | 消除跨桶 `100,000` 目录项悬崖；精确键查盘每块盘仅访问 `1` 个哈希目录 | 完整保留 `xl.meta` 身份字段、`checkUploadID`、Abort 清理与空哈希父目录回收 | **采纳** |

### 回滚内容与保留的修复项

1. **在公共列表路径上回滚的部分（`4733e1423`）**：
   - 公共 `ListMultipartUploads` 不再遍历 `.minio.sys/multipart` 下的全部 `<sha256(bucket/object)>` 目录。
   - 空 `prefix` 直接读取内存 `multipartUploadsCache`；非空 `prefix` 直接计算 `bucket/prefix` 的 SHA-256 哈希，仅检查该对象对应的单个 `<sha256(bucket/object)>` 目录。
2. **保留下来的安全加固与存储修复（`4733e1423` + `0f9199e0c`）**：
   - `NewMultipartUpload` 仍在 `xl.meta` 中写入 `x-minio-internal-multipart-v1-bucket` 与 `x-minio-internal-multipart-v1-object`，使落盘上传具备自描述能力，便于诊断及未来构建索引。
   - 所有分片操作继续强制执行 `checkUploadID` 校验（`SN-2026-009`）。
   - `AbortMultipartUpload` 继续同步驱逐本地缓存并通知集群对端节点。
   - `cleanupStaleUploads` 继续在后台清理磁盘上的过期上传，且提交 [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) 确保当 `.minio.sys/multipart/<sha256(bucket/object)>` 下最后一个 `<uploadID>` 因过期清理、合并完成或显式中止而被删除时，空的 `<sha256(bucket/object)>` 父目录也会一并删除，防止空哈希目录长期堆积。

### 排序成本与发现成本的本质冲突

在 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` 布局中，目录名是 `bucket/object` 的 SHA-256 摘要，既打散了对象键的字典序，也抹去了桶边界。在没有二级索引的前提下，要按 S3 字典序回答任意前缀查询（如 `prefix=trips/`），存储引擎必须先打开纠删集内所有桶、所有活跃上传下的 `xl.meta` 才能还原 `(Bucket, Object)` 并排序分页。相比之下，精确对象键查询（`prefix=trips/2026/a.mp4`）只需计算一次 SHA-256 并读取每块盘上的单个目录（将 `ListDir` 次数从 $O(N \times H)$ 降为 $O(N)$）。

### 提交 `4733e1423` 上的容量验证基准 {#rollback-validation}

使用 `go test -run=^$ -bench=BenchmarkMultipartPublicListingCapacity -benchmem -benchtime=1x ./cmd` 实测结果如下：

| 测试场景（`BenchmarkMultipartPublicListingCapacity`） | 回滚前（`4ed86dfe6` 磁盘扫描） | 回滚后（`4733e1423` MinIO 兼容路径） | 延迟（`4733e1423`） | 内存分配 / 次数（`4733e1423`） |
| :--- | :--- | :--- | :--- | :--- |
| `4_drives_10000_distinct_keys/empty_prefix_cached` | `200 OK`（在磁盘上遍历 80,000 个目录项） | `200 OK`（从内存缓存返回 1,000 条上传） | `1.12 ms` | `257,104 B` / `14` allocs |
| `16_drives_3126_distinct_keys/empty_prefix_cached` | **`503 SlowDown`**（100,032 项 > 100,000 上限） | `200 OK`（从内存缓存返回 1,000 条上传） | `0.36 ms` | `90,208 B` / `14` allocs |
| `16_drives_3126_distinct_keys/exact_key_after_cache_clear` | **`503 SlowDown`**（遍历全部 3,126 个哈希目录） | `200 OK`（清空缓存后从磁盘返回 1 条上传） | `0.78 ms` | `30,024 B` / `389` allocs |
| `16_drives_10000_uploads_one_key/exact_key_lookup` | **`503 SlowDown`**（单键在 6,250 个上传处超限） | `200 OK`（从磁盘返回 1,000 条上传） | `383.85 ms` | `13,721,672 B` / `236,704` allocs |

### 关联文档记录 {#related-records}

| 文档 | 说明 |
| :--- | :--- |
| [S3 API 兼容性 — 分片上传 API 差异说明](/zh/reference/s3-api-compatibility/#id5) | Server `20261018` 中 `ListMultipartUploads` 的权威用户侧兼容性说明 |
| [SILO 20260916 发布注记](/zh/blog/release/silo-20260916/) | 记录已发布的 legacy 默认、strict 可选、UploadID 校验和取消边界 |

---

## 历史记录：10 月 17 日统一磁盘扫描尝试（`#243`） {#implementation-20261017}

`2026-10-17` 合并的 PR `#243`（提交 [`4ed86dfe6`](https://github.com/pgsty/silo/commit/4ed86dfe6)）曾短暂移除 `legacy`/`strict` 模式开关，将所有 `ListMultipartUploads` 请求统一路由到 `#198` 引入的磁盘扫描实现。尽管该默认路由在次日由 `4733e1423` 回滚，下文仍完整保留 `#243` 的架构决策记录，以便查阅 `.minio.sys/multipart` 的落盘格式、法定人数判定规则与并发中止竞态分析。

## 10 月 17 日架构决策记录 {#decision-20261017}

### 10 月 17 日实验的目标契约 {#decision-contract}

10 月 17 日的统一尝试旨在不引入外部元数据数据库的前提下，让 `ListMultipartUploads` 同时满足以下三条不变式：

1. **跨重启持久可见**：`ListMultipartUploads` 直接从磁盘 `.minio.sys/multipart` 读取活跃上传，而非仅依赖内存 `multipartUploadsCache`。
2. **完整的 S3 过滤与分页语义**：将 `prefix` 作为对象键前缀匹配，支持 `delimiter` 折叠 `CommonPrefixes`，并按 `(Key, Initiated, UploadID)` 排序及执行 `key-marker` / `upload-id-marker` 分页。
3. **自描述上传元数据**：`NewMultipartUpload` 在每个上传的 `xl.meta` 内写入桶名与对象键，使 `<sha256(bucket/object)>` 目录下的上传可反向还原出 `(Bucket, Object)`。

### 当时尝试统一两种模式的背景 {#decision-background}

在 `#198` 之前，调用方根据 `prefix` 为空、为目录前缀或为完整对象键，会观察到截然不同的行为：

| 请求示例 | 传统 MinIO / `legacy` 行为 | S3 标准 / 磁盘扫描行为 |
| :--- | :--- | :--- |
| `GET /photos?uploads`（`CreateMultipartUpload` 后立即调用） | 返回当前节点内存缓存中记录的上传 | 返回磁盘上达到读法定人数的活跃上传 |
| `GET /photos?uploads`（服务进程重启后） | 返回空列表（重启清空了 `multipartUploadsCache`） | 仍能从 `.minio.sys/multipart` 返回未完成的活跃上传 |
| `GET /photos?uploads&prefix=2026/`（目录前缀） | 除非存在字面名为 `2026/` 的对象（`sha256("photos/2026/")`），否则返回空列表 | 返回对象键以 `2026/` 开头的所有活跃上传 |
| `GET /photos?uploads&prefix=2026/trip.mov`（精确对象键） | 直接查磁盘 `.minio.sys/multipart/<sha256("photos/2026/trip.mov")>`（跨重启可见） | 返回对象键以 `2026/trip.mov` 开头的活跃上传 |

Issue `#198`（`2026-09-16`）与 `#213` 最初通过 `MINIO_API_MULTIPART_LISTING=legacy|strict` 同时保留两种模式，避免升级前遗留的旧上传静默不可见。PR `#243`（`2026-10-17`）在补充惰性回填逻辑后，尝试收敛这一配置分叉。

### `#243` 评估过的备选方案 {#decision-alternatives}

| 候选方案 | 跨重启可见性 | 前缀与游标支持 | 额外索引维护成本 | 当时取舍与后续复盘结论 |
| :--- | :--- | :--- | :--- | :--- |
| 1. 维持 `legacy` + `strict` 双模式 | 仅 `strict` 支持 | 仅 `strict` 支持 | 无 | `#243` 为消除双模式而放弃；`4733e1423` 重新回到兼容路径 |
| 2. 仅使用内存缓存 | 不支持 | 仅在缓存存活期内支持 | 无 | 淘汰：重启后丢失全部列表可见性 |
| 3. 扫描 `.minio.sys/multipart` + `xl.meta` 身份字段（`#243`） | 支持 | 支持 | 无 | `#243` 选中；因 $O(N \times (H+U))$ 遍历在 16 盘 3,126 个上传处触发 100k 上限而于 **`4733e1423` 回滚** |
| 4. 每个上传附加旁路 JSON 文件 | 支持 | 支持 | 每次创建/中止多一次文件读写 | 淘汰：元数据文件 I/O 翻倍 |
| 5. 按桶维护磁盘分片索引树 | 支持 | 支持（仅与匹配前缀成正比） | 需配套分布式索引自愈与清理协议 | 延后：大规模纠删集唯一可行的长期路径，但需独立设计崩溃恢复与自愈 |
| 6. 外部 KV / SQLite 索引 | 支持 | 支持 | 在纠删码体系外引入外部状态 | 淘汰：违背纠删集自包含架构原则 |

### 磁盘存储布局与 `xl.meta` 身份字段 {#decision-storage}

每个活跃分片上传在磁盘上的存储路径为：

```text
.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta
.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/part.1
...
```

由于 `<sha256(bucket/object)>` 是单向哈希摘要，仅凭目录路径无法反推出桶名或对象键。提交 [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc) 扩展了 `cmd/erasure-multipart.go` 中的 `newUploadedObjectMetadata`，在 `xl.meta` 内写入两个内部元数据键（在 `20261018` 中继续保留）：

- `x-minio-internal-multipart-v1-bucket`：明文桶名
- `x-minio-internal-multipart-v1-object`：明文对象键

针对上游 MessagePack `xl.meta` 读取器的兼容性验证（对照提交 `3be10fcc1a44f6620ded0bd303461f9d688cca23`）：`MetaSys` 在 `xl.meta` 中是标准的 `map[string][]byte` 映射，旧版本读取器会自动忽略未知的 `x-minio-internal-*` 键，不会触发反序列化错误。

### 磁盘扫描路径中的发现与法定人数规则 {#decision-read-policy}

当 `#198` 与 `#243` 执行磁盘扫描（`listMultipartUploadsScan`）时，每个纠删集按以下五步工作：

1. 在所有在线磁盘上列出 `.minio.sys/multipart` 下的 `<sha256(bucket/object)>` 目录，要求每个哈希目录至少出现在 `readQuorum = floor(N/2) + 1` 块磁盘上。
2. 列出每个满足法定人数的哈希目录下的 `<uploadID>` 子目录，使用 `checkUploadID` 校验每个 `uploadID` 并要求满足 `readQuorum`。
3. 对每个候选 `uploadID` 从在线磁盘读取 `xl.meta`，要求至少 `readQuorum` 块磁盘对 `(Bucket, Object)` 身份达成一致。
4. 若升级前遗留的旧上传缺少 `x-minio-internal-multipart-v1-*` 键，则在精确前缀或缓存命中提供候选键时验证哈希并惰性回填 `xl.meta`。
5. 按 `Bucket`、`Prefix`、`Delimiter`、`KeyMarker` 与 `UploadIDMarker` 过滤，按 `(Key, Initiated, UploadID)` 排序并跨存储池归并。

### 目录遍历成本与 4 盘基准测试（`#243`） {#decision-cost}

在包含 $N$ 块磁盘、跨所有桶共有 $H$ 个活跃 `<sha256(bucket/object)>` 目录和 $U$ 个活跃 `<uploadID>` 目录的纠删集上：

- 每次未缓存扫描检查的目录项总数：$N \times (H + U)$
- 每次未缓存扫描发起的 `ListDir` 调用总数：$N \times (1 + H)$

在 `#243` 提交时，`BenchmarkMultipartListingCapacity` 仅在 **4 盘**单纠删集夹具（$N = 4$）上针对单个对象键下的 `10,000` 个上传（$H = 1, U = 10{,}000$）进行了测试，总目录项为 $4 \times (1 + 10{,}000) = 40{,}004$：

| 4 盘测试夹具（`4ed86dfe6` 上的 `BenchmarkMultipartListingCapacity`） | 活跃上传数 | 耗时 | 内存分配量 | 分配次数 |
| :--- | ---: | ---: | ---: | ---: |
| 单对象键（$H = 1, U = 10{,}000, N = 4$） | `10,000` | `101.6 ms` | `3.58 MB` | `61,210` |

这一 4 盘单键基准测试掩盖了次日在 16 盘纠删集上暴露的两个乘数因子：$N = 16$ 块磁盘（$4\times$ 倍率）与不同对象键 $H = U$（目录项 $2\times$ 倍率、`ListDir` 次数 $U\times$ 倍率），两者叠加使 `3,126` 个上传即突破 `maxMultipartWalkEntries = 100000`。

### 16 盘 EC:8 纠删集上的 Abort 与延迟创建竞态分析 {#decision-abort}

在 `#243` 评审期间，我们还分析了在固定 `readQuorum = floor(N/2) + 1`（例如 16 盘 `EC:8` 纠删集上为 `9`）下，`AbortMultipartUpload` 是否可能因延迟写入而出现“死而复生”的上传：

1. 假设 `NewMultipartUpload` 先在 `8` 块快盘上完成了 `xl.meta` 写入，另有 `7` 块盘的写入仍在飞行途中阻塞，`1` 块盘离线。
2. 此时并发到达的 `AbortMultipartUpload` 删除了前 `8` 块快盘上的副本并返回成功。
3. 随后那 `7` 个延迟的 `NewMultipartUpload` 写入落盘，且离线的 `1` 块盘恢复或自愈后补齐副本——此时磁盘上重新凑齐了 `8` 份可读副本（达到 `EC:8` 对象读取法定人数），使客户端已中止的上传重新变为可操作状态。

尽管 `4733e1423` 保留的 `AbortMultipartUpload` 缓存驱逐与对端节点通知能够保持内存缓存一致，但要在磁盘层面彻底消除延迟创建复活，仍需引入墓碑（tombstone）或按上传维度的代际锁。

### 10 月 17 日代码改动汇总（后续已部分回滚） {#decision-changes}

- `cmd/object-api-interface.go`、`cmd/server-main.go`、`cmd/config-current.go`：将 `api multipart_listing` 设为兼容性空操作（`4ed86dfe6`；在 `4733e1423` 中继续保留为空操作）。
- `cmd/erasure-multipart.go`：增加精确键解析时的 `xl.meta` 惰性回填，并将全部公共列表路由到磁盘扫描（`4ed86dfe6`；公共扫描路由已在 `4733e1423` 回滚，`xl.meta` 写入元数据与 `0f9199e0c` 空父目录清理予以保留）。

### 10 月 17 日测试证据 {#decision-evidence}

- `go test ./cmd -run 'TestMultipartUploadListing|TestMultipartPreflight|TestMultipartListingConfig'` 在 `4ed86dfe6` 上全部通过。
- `BenchmarkMultipartListingCapacity` 在 4 盘单键夹具上耗时 `101.6 ms`，但未能覆盖 16 盘多键拓扑下的阈值悬崖。

### `#243` 的后续工程教训 {#decision-followup}

未来任何试图提供“跨重启持久且支持任意前缀”的 `ListMultipartUploads` 方案，**必须**按 `(bucket, object, uploadID)` 建立索引，严禁在公共列表路径上跨纠删集所有磁盘扫描 `.minio.sys/multipart/<sha256(bucket/object)>` 目录，且**必须**在 `16` 盘不同对象键（$H = U$）拓扑下完成容量基准验证。

---

## 历史记录：9 月 16 日可选 `strict` 模式（`#198`） {#implementation-20260916}

Issue `#198`（提交 [`4cbb074cc`](https://github.com/pgsty/silo/commit/4cbb074cc)，并由 [`143f6970d`](https://github.com/pgsty/silo/commit/143f6970d) 与 [`0ff5b37fc`](https://github.com/pgsty/silo/commit/0ff5b37fc) 加固）在 Server `20260916` 中交付了最初的按需启用实现：

- 新增 `MINIO_API_MULTIPART_LISTING=legacy|strict`（默认 `legacy`）及 `mcli admin config set/reset ALIAS api multipart_listing`。
- 新增 `GET /minio/admin/v3/multipart-preflight`，供运维人员在开启 `strict` 前检查磁盘 `.minio.sys/multipart` 中是否存在缺少 `x-minio-internal-multipart-v1-bucket` 与 `x-minio-internal-multipart-v1-object` 的历史上传。
- 在 `strict` 模式下实现按 `(Key, Initiated, encoded UploadID)` 的 S3 字典序排列与 `floor(N/2) + 1` 磁盘发现法定人数。
- 9 月 16 日 Docker Desktop 环境实测记录：跨 `4` 个容器的 `10,000` 个活跃上传在虚拟化容器文件系统上因逐盘读取 `xl.meta` 耗时 `18.7 s`（并发度 `10` 下 `p95 = 2.68 s`）。

---

## 原始根因分析（2026-08-30） {#analysis-20260830}

### 问题概述 {#plain-language}

在上游 MinIO 的纠删码存储引擎（`erasureObjects`）中，`CreateMultipartUpload` 将每个分片上传持久化在磁盘路径 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` 下，同时将该上传写入按桶组织的内存缓存（`multipartUploadsCache`）。由于磁盘目录名对 `bucket/object` 做了 SHA-256 哈希，存储层在已知精确 `bucket` 和 `object` 时可以直接定位到对应目录；但在不打开每个活跃上传目录的前提下，无法直接从磁盘按桶或按对象键前缀列出上传。

### 8 月 30 日的原始建议 {#decision}

8 月 30 日的调研建议分两阶段改进 `ListMultipartUploads`：第一步先在 `NewMultipartUpload` 时向 `xl.meta` 写入 `(bucket, object)` 身份元数据并提供按需启用的磁盘扫描模式（`#198`）；第二步再评估是否将磁盘扫描或专用按桶索引设为默认行为。

### 证据与信息来源 {#sources}

#### AWS S3 规范要求 {#source-s3}

AWS S3 `ListMultipartUploads` 规范要求支持 `prefix` 与 `delimiter` 过滤，按 `Key` 与 `Initiated` 时间升序排列（时间相同时按 `UploadId` 排序），并通过 `key-marker` 与 `upload-id-marker` 实现分页续传。

#### 仓库 Issue `#198` {#source-issue}

Issue `#198` 报告：带目录前缀（如 `prefix=dir/`）调用 `ListMultipartUploads` 时，即使刚刚执行完 `CreateMultipartUpload` 也会返回空列表；而不带前缀的 `ListMultipartUploads` 在服务进程重启后同样返回空列表，尽管使用之前保存的 `UploadId` 继续调用 `UploadPart` 和 `CompleteMultipartUpload` 完全正常。

#### 上游 MinIO 历史演进 {#source-upstream}

- **MinIO PR `#5248`**：将早期镜像桶目录结构的分片上传树替换为 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>`，以规避 POSIX 文件系统上的超长路径限制与空父目录清理缺陷。
- **MinIO PR `#20407`**：引入内存 `multipartUploadsCache`，使空 `prefix` 的 `ListMultipartUploads` 无需扫盘即可返回近期创建的上传；同时将非空 `prefix` 直接作为精确对象键传给 `listMultipartUploads(bucket, prefix, ...)`。
- **MinIO Issue `#20989`**：在 `docs/minio-limits.md` 中正式记录了这一上游限制：`ListMultipartUploads` 仅支持空前缀（读内存）或将 `prefix` 设为完整对象键。

#### `pgsty/silo` 代码走查 {#source-code}

- `cmd/bucket-handlers.go`（`ListMultipartUploadsHandler`）：解析了 `prefix`、`keyMarker`、`uploadIDMarker`、`delimiter` 与 `maxUploads`，校验 `encoding-type` 后传给 `objectAPI.ListMultipartUploads`。
- `cmd/erasure-sets.go`（`erasureSets.ListMultipartUploads`）：按 `prefix == ""` 分支——为空时读取 `multipartUploadsCache.List(bucket)`；非空时对 `pathJoin(bucket, prefix)` 计算哈希并调用单哈希目录上的 `set.listMultipartUploads`。
- `cmd/erasure-multipart.go`（`erasureObjects.listMultipartUploads`）：仅列出 `.minio.sys/multipart/<sha256(bucket/object)>` 下的 `<uploadID>` 子目录，忽略了 `delimiter`、`keyMarker` 与 `uploadIDMarker`。
- `cmd/erasure-server-pool.go`（`erasureServerPools.ListMultipartUploads`）：在 `prefix != ""` 时顺序遍历各存储池，并在首个返回非空结果的存储池处提前返回。

#### 设计评审结论 {#source-review}

初步代码评审确认该问题属于存储布局层面的架构取舍，而非简单的参数解析遗漏：HTTP 处理器完整解析了所有 S3 查询参数，但底层存储缺少从 `bucket + key-prefix` 到 `<sha256(bucket/object)>` 的索引映射。

### `#198` 之前的历史行为（即 `20261018` 恢复的默认行为） {#current-behavior}

#### 空 `prefix` 路径 {#empty-prefix}

当 `prefix == ""` 时：

1. `erasureSets.ListMultipartUploads` 直接读取目标桶的内存 `multipartUploadsCache`。
2. 进程重启前创建的上传不在内存缓存中，因此不会出现在返回结果里，尽管磁盘 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>` 目录依然完好。
3. 分布式节点间的缓存同步采用尽力而为机制（`updateMultipartUploadInfo`）。

#### 非空 `prefix` 路径 {#nonempty-prefix}

当 `prefix != ""` 时：

1. `erasureSets.ListMultipartUploads` 将 `prefix` 视为完整对象名（`object = prefix`），计算 `bucket/object` 的 SHA-256 哈希以定位目标纠删集，并读取磁盘上的 `.minio.sys/multipart/<sha256(bucket/object)>`。
2. 若调用方传入的是目录前缀（如 `prefix=photos/2026/`），服务端会对字面字符串 `"bucket/photos/2026/"` 计算哈希，因不存在该精确名称的对象而返回空列表。
3. 若调用方传入精确对象键（如 `prefix=photos/2026/video.mp4`），服务端会定位到 `"bucket/photos/2026/video.mp4"` 对应的哈希目录，从磁盘读取匹配的 `<uploadID>` 子目录，即使经历过服务重启也能返回该对象下的全部活跃上传。

#### 多存储池提前返回机制 {#multiple-pools}

在 `erasureServerPools.ListMultipartUploads` 中，非空 `prefix` 的提前返回对“精确对象键”是自洽的，因为 `sha256(bucket/object)` 确定性地映射到唯一存储池中的唯一纠删集；而若要支持任意前缀列表，则必须归并所有存储池的结果。

### 为什么缺少候选键时无法自动回填历史上传 {#no-backfill}

由于 `20260916` 之前的 `.minio.sys/multipart/<sha256(bucket/object)>/<uploadID>/xl.meta` 既未记录桶名也未记录对象键，磁盘上遗留的历史上传目录仅包含 `bucket/object` 的 SHA-256 摘要。在既不知道候选 `bucket/object` 明文（无法正向计算哈希比对）、`xl.meta` 中又没有 `x-minio-internal-multipart-v1-bucket` 与 `x-minio-internal-multipart-v1-object` 的情况下，服务端无法逆向还原出 `(Bucket, Object)`。

### 结构性复杂度根源 {#complexity}

| 层次 | 隐含假设 | 直接后果 |
| :--- | :--- | :--- |
| S3 HTTP API（`ListMultipartUploadsHandler`） | `prefix` 是对象键前缀；`delimiter` 折叠公共前缀；游标在有序键集合上分页 | 要求底层按桶提供有序的 `(Key, Initiated, UploadID)` 候选集 |
| 磁盘布局（`.minio.sys/multipart/<sha256(bucket/object)>`） | 调用方总是提供精确的 `bucket` 与 `object`（如 `PutObjectPart`、`Complete`、`Abort`） | 精确键查找为 $O(1)$，但既无按桶分区，也无字典序索引 |
| 内存缓存（`multipartUploadsCache`） | 仅跟踪本次进程启动以来观察到的分片上传 | 空 `prefix` 按桶列出速度快，但进程重启即清空 |

### 运维与兼容性影响 {#impact}

#### 协议兼容性影响 {#wire-impact}

使用目录 `prefix` 调用 `ListMultipartUploads` 的 SDK 与备份工具（例如 `aws s3api list-multipart-uploads --bucket B --prefix dir/`）在 `prefix` 不等于完整对象键时会收到空列表。

#### 存储与孤儿上传清理影响 {#storage-impact}

依赖重启后或按目录前缀调用 `ListMultipartUploads` 来发现并中止残留上传的外部工具，无法通过列表接口看到这些上传；但 Silo 内置的后台过期清理任务（`cleanupStaleUploads`）直接按修改时间遍历 `.minio.sys/multipart`，不依赖 `ListMultipartUploads` 即可自动回收过期分片。

#### 运维可用性权衡 {#operational-impact}

正如 `2026-10-18` 所验证的，强制 `ListMultipartUploads` 在每次未命中缓存的公共请求上遍历 `.minio.sys/multipart`，会把一个列表过滤限制变成 16 盘纠删集在 `3,126` 个活跃上传处的 `503 SlowDown` 可用性悬崖。保持 MinIO 兼容路径能够保护集群级 `ListMultipartUploads` 的稳定性，同时继续支持精确对象键查盘与后台过期回收。

#### 严重度分级 {#severity}

- **数据完整性风险**：无（`PutObjectPart`、`CompleteMultipartUpload` 与 `AbortMultipartUpload` 均按精确 `Bucket + Object + UploadID` 寻址）。
- **S3 API 兼容性差异**：已在 [S3 API 兼容性参考](/zh/reference/s3-api-compatibility/#id5)中明确列出。

### 设计备选方案对比 {#options}

#### 方案 0：维持现状且不补充说明 {#option-zero}

会让调用方在 `prefix=dir/` 返回空列表时难以排查。已淘汰，改为明确记录兼容性契约并保留 `xl.meta` 自描述元数据。

#### 方案 1：保持 MinIO 兼容行为并明确记录契约（`20261018` 最终选择） {#option-divergence}

空前缀列表读取内存缓存，非空 `prefix` 读取单对象键磁盘目录，同时保留 `xl.meta` 身份字段并补齐空哈希父目录清理（`0f9199e0c`）。在 16 盘扫描回归验证后于 `20261018` 选定。

#### 方案 2：基于 `xl.meta` 身份字段直接扫描磁盘 `.minio.sys/multipart` {#option-scan}

在 `#198` 中作为可选 `strict` 模式实现，并在 `#243` 中短暂设为默认。在小规模上传下可用，但开销随纠删集内全桶上传数呈 $O(N \times (H + U))$ 增长，在 16 盘纠删集上于 `3,126` 个不同键上传处触及 `100,000` 遍历上限。

#### 方案 3：构建按桶组织的专用分片上传索引 {#option-index}

在 `.minio.sys/multipart` 旁维护按桶隔离、按前缀有序的元数据索引。可避免跨桶扫描 SHA-256 目录，但需要在每次 `CreateMultipartUpload`、`CompleteMultipartUpload`、`AbortMultipartUpload` 与过期清理时同步维护并自愈第二套分布式元数据结构。

#### 方案 4：仅在内存缓存层扩展前缀与分隔符过滤 {#option-cache-only}

仅对内存 `multipartUploadsCache` 执行完整的 S3 `prefix`、`delimiter` 与游标过滤，不扫盘。速度快且开销有界，但重启前创建的上传在被精确键操作触达前依然不可见。

### 磁盘扫描参考架构（于 `#198` 实现，公共路径已于 `4733e1423` 回滚） {#recommended-design}

#### 1. 先行冻结契约 {#contract-first}

在改动存储层前明确定义 `(Key, Initiated, UploadID)` 排序规则与游标续传边界。

#### 2. 写入路径（`xl.meta` 身份写入） {#write-path}

在 `NewMultipartUpload` 中向 `xl.meta` 写入 `x-minio-internal-multipart-v1-bucket` 与 `x-minio-internal-multipart-v1-object`（`20261018` 已保留）。

#### 3. 读取路径 {#read-path}

从磁盘读取分片元数据时要求跨磁盘达到 `readQuorum` 一致。

#### 4. 语义过滤层 {#semantic-layer}

在单纠删集发现层之上统一执行 `Prefix`、`Delimiter`、`KeyMarker`、`UploadIDMarker` 与 `MaxUploads` 过滤。

#### 5. 精确键辅助函数 {#exact-helper}

为内部调用方与精确键查询保留 $O(1)$ 的 `sha256(bucket/object)` 查盘辅助函数。

#### 6. 缓存同步 {#cache}

在 `AbortMultipartUpload` 与 `CompleteMultipartUpload` 时跨对端节点同步驱逐 `multipartUploadsCache` 条目（`20261018` 已保留）。

#### 7. 迁移与预检 {#migration}

提供 `/minio/admin/v3/multipart-preflight` 端点以检查磁盘分片目录状态（`20261018` 保留为兼容端点）。

#### 8. 降级与挂起存储池处理 {#suspended-pools}

在多存储池列表时安全跳过挂起（suspended）的存储池，避免单池挂起导致整体请求失败。

### `#198` 原型验证清单 {#spike}

1. 验证 `MetaSys` MessagePack 字段与既有 `xl.meta` 读取器的前向/后向兼容性。
2. 测量跨 $N$ 块磁盘的 `ListDir` 与 `readAll` I/O 放大倍数。
3. 验证 `cleanupStaleUploads` 在清理最后一个上传后同步删除空的 `<sha256(bucket/object)>` 父目录（已于 [`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) 修复）。

### 验证门禁 {#gates}

#### 单元测试 {#unit-tests}

覆盖前缀、分隔符、游标分页以及 `checkUploadID` 路径穿越拒绝测试。

#### 处理器与端到端测试 {#handler-tests}

验证 `ListMultipartUploadsHandler` 响应 XML、URL 编码以及跨重启的缓存与精确键查盘行为。

#### 故障与容量基准测试 {#failure-tests}

在 `4` 盘与 `16` 盘纠删集拓扑下运行高达 `10,000` 个活跃上传的 `BenchmarkMultipartPublicListingCapacity`。

#### 交付门禁 {#delivery-gates}

在 [S3 API 兼容性参考](/zh/reference/s3-api-compatibility/#id5)中同步记录公共 `ListMultipartUploads` 契约，并保持所有历史锚点完整可用。

### 当前工程结论 {#final-recommendation}

在 Server `20261018` 中，以 MinIO 兼容公共 `ListMultipartUploads` 路径（`4733e1423`）配合空父目录清理修复（`0f9199e0c`）作为生产默认实现。不要在公共列表路径上重新开启无索引的 `.minio.sys/multipart` 全盘扫描；如果未来版本确实需要跨重启持久的任意前缀列表，必须先设计按桶隔离的分片索引并在 16 盘纠删集上完成容量基准验证。
