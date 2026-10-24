---
title: "鉴权前不做 I/O，Header 不授予权限"
linkTitle: "CORS 与复制信任边界"
date: 2026-09-01
lastmod: 2026-09-16
author: "冯若航"
summary: >
  CORS 预鉴权查询曾将任意 URL 路径段转化为磁盘元数据读取与缓存条目，而客户端可控的复制标记请求头又能在未鉴权情况下触发 SSE-C 密文读取、源时间戳覆盖、校验和注入、对象锁豁免与事件抑制。本文记录 SILO 的纯内存驻留 CORS 热路径、两级复制信任模型与验签后清洗边界。
tags: [设计, 安全, CORS, Replication, SSE-C, 兼容性]
weight: 12
draft: false
url: "/zh/blog/design/cors-replication-trust/"
---

本文记录通过 [PR #101](https://github.com/pgsty/silo/pull/101)（提交 `938603458` 至 `04b097fd9`）合入 SILO、编号为 [SN-2026-008](/zh/about/security-advisories/#sn-2026-008) 并随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布的 CORS 热路径与复制请求信任边界修复。

## 概览 {#tldr}

两个表面上互不相关的缺陷，实际上源于同一个架构层面的设计失误：

1. 任何携带 `Origin` 请求头的 HTTP 请求都会促使最外层 CORS 中间件把 URL 第一段路径当成存储桶名称，并在身份认证之前同步从磁盘加载该桶的元数据。
2. 任何携带 `X-Minio-Source-Replication-Request` 请求头的请求，仅凭该请求头存在就会让下游处理器将其视为内部复制请求。

两者的共同根因在于：**不可信的请求语法在跨越授权边界之前，就已经获得了高开销或高特权的内部语义**。

本次修复确立了两条核心安全不变量：

```text
鉴权之前：只做廉价语法解析，绝不触发存储层 I/O
鉴权之后：只派生一次信任结论，下游仅消费该结论
```

对于 CORS，最外层中间件现在只读取已驻留在内存中的存储桶元数据。对于复制，处理器先对原始签名请求完成身份认证，再校验对应的复制权限（`s3:ReplicateObject` 或 `s3:ReplicateDelete`），随后将私有的信任结论写入请求上下文（`context.Context`）。不可信的内部请求头仅在 SigV4 验签完成后才被剥离。下游选项构造器、加密路径、Object Lock 检查、事件通知与元数据持久化统一读取上下文中的信任结论，而不再检查原始请求头。

## 缺陷 A：鉴权前的 CORS 元数据放大攻击 {#cors-failure}

`corsHandler` 包裹了整个服务端路由器。任何携带 `Origin` 请求头的请求都会在进入 S3 签名认证、请求合法性检查和常规 API 并发限流器之前先经过该中间件。

在旧实现中，按桶 CORS 检查直接调用了通用的存储桶元数据加载器：

```text
携带 Origin 的请求
  -> URL 第一段被当作 "bucket"
  -> GetCorsConfig
  -> GetConfig 缓存未命中
  -> 读取 .metadata.bin
  -> 依次探测 10 个旧版配置文件路径
  -> 向 metadataMap 写入默认的空 BucketMetadata 记录
```

当磁盘上不存在 `.metadata.bin` 时，加载器会继续探测 10 个历史遗留配置路径；全部未命中后，它不会返回 `NoSuchBucket`，而是构造并返回一条合法的空 `BucketMetadata` 记录，随后由通用读取器插入内存映射表 `metadataMap`。

因此，未认证客户端只需不断变换语法合法但并不存在的存储桶名称，每个新名称都会触发双重放大效应：

- 在进入 API 限流器之前触发未受限的纠删码/存储层元数据读取（1 次 `.metadata.bin` 加 10 次旧路径探测）；
- 导致内存中的 `metadataMap` 持续膨胀（分布式部署每 15 分钟才清理一次过期项，而单节点部署不启动后台刷新循环，伪造条目会一直驻留到进程重启）。

## 缺陷 B：标记请求头被直接当作权限权威 {#replication-failure}

SILO 与兼容 MinIO 的复制客户端在跨站复制时通过内部请求头传递源端状态，其中最核心的标记头是：

```http
X-Minio-Source-Replication-Request: true
```

在本次修复前，多条代码路径只要看到该请求头存在（或其字符串值为 `"true"`），就会直接认定当前请求来自受信任的复制对端，影响范围遍及多个子系统：

- 仅具备普通 `s3:GetObject` 权限的调用方在对 SSE-C 对象发起 `GetObject`、`HeadObject` 或 `GetObjectAttributes` 时，可利用该标记触发 `NoDecryption` 分支，无需提供客户端密钥即可直接读取原始密文；
- 客户端提供的源 ETag 与修改时间（`MTime`）可以覆盖服务端生成的值；
- 源端标签、对象锁保留期与法律保留（Legal Hold）时间戳可渗入“最后写入者胜出”（LWW）冲突比较；
- 对象锁解析器通过检查原始标记头即可放行已经过期的 `RetainUntilDate` 保留时间；
- 调用方可自行指定删除标记（Delete Marker）的 `VersionID` 与修改时间；
- 成功的对象创建与访问通知事件可被静默抑制；
- 分片上传完成（`CompleteMultipartUpload`）阶段可注入实际对象大小与加密校验和元数据；
- 普通 `PutObject`、`CopyObject`、Snowball/PAX 归档解压或浏览器 `POST` 表单策略上传只要附带 `X-Amz-Replication-Status: REPLICA`，就能将该状态直接持久化到对象元数据中。

此前的 [CVE-2026-34204 修复](/zh/blog/security/cve-2026-34204/)已经阻止了普通 `PutObject` 与 `CopyObject` 导入会导致对象不可读的复制 SSE 元数据，但当时尚未为所有读取复制标记、源时间戳、事件状态、对象锁豁免与分片完成元数据的消费者建立统一的授权后信任源。

## 复制信任模型设计 {#design}

### 精确标记解析与两级信任模型 {#trust-levels}

仅当 `X-Minio-Source-Replication-Request` 恰好出现一次且其值严格等于小写 `"true"` 时，解析器才视其为有效标记；重复请求头、大小写混合或任何其他字符串一律视为不可信。

完成身份认证后，处理器派生出两个层次的信任决策：

| 信任级别 | 准入要求 | 允许启用的内部语义 |
| --- | --- | --- |
| `trusted` | 原始请求已通过非匿名身份认证 + 精确标记头 + 对目标资源具备 `s3:ReplicateObject`（或 `s3:ReplicateDelete`）权限 | 保留源端 ETag/MTime 及子系统时间戳；传递分片实际大小与加密校验和；抑制重复事件通知与二次复制；固定复制删除的目标版本与存储池 |
| `replicaTrusted` | 满足 `trusted`，且当前请求携带原始状态 `REPLICA`（或分片上传初始化时已持久化 `REPLICA` 状态） | 持久化 `REPLICA` 状态；导入复制 SSE 密封密钥；启用 SSE-C 免解密原始密文读取路径（`NoDecryption`）；启用副本专用的对象锁豁免规则 |

之所以必须区分 `trusted` 与 `replicaTrusted`，是由真实线缆协议决定的：合法的分片上传（`UploadPart`）、分片完成（`CompleteMultipartUpload`）以及批量复制（Batch Replication）请求只会携带 `X-Minio-Source-Replication-Request: true`，而不会在每个子请求上重复附带 `X-Amz-Replication-Status: REPLICA`。

接收端按以下矩阵处理入站请求：

| 入站请求形态 | 接收端行为 |
| --- | --- |
| 无标记头 | 按普通 S3 请求处理 |
| 携带标记头，但缺少复制权限 | 剥离并忽略内部复制请求头，按普通 S3 语义继续执行 |
| 携带 `X-Amz-Replication-Status: REPLICA`，但缺少复制权限 | 直接返回 `403 AccessDenied` |
| 精确标记头 + 具备复制权限，无 `REPLICA` 状态头 | 仅授予 `trusted` |
| 精确标记头 + 具备复制权限 + `REPLICA` 状态头 | 同时授予 `trusted` 与 `replicaTrusted` |

对未获授权却声称 `REPLICA` 的请求显式返回 `403 AccessDenied`，可以防止配置错误的副本写入被静默降级为普通新对象写入并触发反向复制循环。

### 先验签原始请求，再清洗内部请求头 {#signature-boundary}

由于 AWS SigV4 会将 `x-amz-*` 与 `x-minio-*` 请求头纳入签名计算，若在验签前删除内部请求头，就会破坏规范化请求（Canonical Request）并导致合法签名报 `SignatureDoesNotMatch`。因此处理顺序必须严格固定：

```text
原始 HTTP 请求
  -> SigV4 签名与身份认证
  -> 常规 S3 操作权限检查
  -> 复制操作权限检查（s3:ReplicateObject / s3:ReplicateDelete）
  -> 计算 trusted / replicaTrusted 决策
  -> 将信任决策绑定到请求 context
  -> 克隆请求并剥离不可信内部请求头（共享原始 Trailer 映射）
  -> 选项解析、加密处理、对象锁、存储落盘与事件通知
```

剥离请求头后的克隆请求会与原请求共享底层 `http.Request.Trailer` 映射，确保普通客户端的 `aws-chunked` 流式校验和上传不受影响。Snowball/PAX 批量归档路径则按归档条目独立隔离信任状态（`ff44527a3`），同时在后台工作协程之间保留合法的请求默认属性（`ab3ae99ca`）。

### 将副本状态移出通用用户元数据白名单 {#replica-status}

`X-Amz-Replication-Status` 已从通用的受支持请求元数据提取列表中移除。普通 `PutObject`、`CopyObject`、分片上传初始化、Snowball 归档提取以及浏览器 `POST` 表单策略均无法再通过提交同名字段来持久化 `REPLICA` 状态；服务端仅在通过验证的 `replicaTrusted` 分支中显式写入 `REPLICA`。

### 对象锁显式接收信任决策 {#object-lock}

对象锁解析包不再直接读取 `X-Minio-Source-Replication-Request` 请求头，而是由外层处理器根据 `replicaTrusted` 状态显式传入 `allowPastRetainDate` 参数；外层处理器在判断入站副本是否允许覆盖既有合规模式（Compliance）或法律保留版本时，同样使用同一个 `replicaTrusted` 决策。

## 真实复制线缆协议矩阵 {#wire-matrix}

| 操作类型 | 标记头 | 当前请求是否携带 `REPLICA` | 接收端信任决策 |
| --- | --- | --- | --- |
| 常规复制 `PutObject` | 是 | 是 | `replicaTrusted` |
| 复制 `CreateMultipartUpload` | 是 | 是 | 持久化受信任的分片上传 `REPLICA` 来源状态 |
| 复制 `UploadPart` | 是 | 否 | `trusted`；仅当已保存的分片上传状态为 `REPLICA` 时提升为 `replicaTrusted` |
| 复制 `CompleteMultipartUpload` | 是 | 否 | `trusted`；保留源端 ETag/MTime、实际大小与加密校验和 |
| `CopyObject` 元数据复制 | 是 | 是 | `replicaTrusted` |
| 复制 `DeleteObject` | 是 | 是 | `replicaTrusted`（需具备 `s3:ReplicateDelete` 与 `s3:DeleteObject`，且 `s3:DeleteObjectVersion` 未被显式拒绝） |
| 批量复制 `PUT` / `Complete` | 是 | 否 | `trusted`（目标端凭据必须包含 `s3:ReplicateObject`） |
| 代理转发 / 就绪检查 / 有效性探针 | 独立探针头 | 否 | 保留探针头；有效性探针在规则前缀下校验复制权限（`c9ad74673`、`5db7be4ee`） |

## CORS 纯内存驻留状态机 {#cors-state-machine}

最外层 CORS 中间件现在调用专用的纯内存驻留（resident-only）访问器，仅获取一次内存读锁，绝不触发任何存储层 I/O：

| 存储桶元数据内存状态 | CORS 决策 | 存储层 I/O |
| --- | --- | --- |
| 已驻留，且包含合法的桶级 CORS 配置 | 应用桶级 CORS 规则（后台刷新失败时保留上一次成功加载的配置） | 无 |
| 已驻留，但未配置桶级 CORS | 回退使用全局 CORS 配置 | 无 |
| 已驻留，但持久化的 CORS XML 损坏 | 失败关闭（Fail closed：不输出 CORS 响应头并记录一次日志） | 无 |
| 未驻留，且启动期初始加载尚未完成 | 失败关闭（Fail closed） | 无 |
| 启动完成后未驻留：磁盘上真实存在但元数据加载失败的桶 | 失败关闭（Fail closed） | 无 |
| 启动完成后未驻留：不存在、保留名、非法名或 `.minio.sys` 命名空间 | 回退使用全局 CORS 配置 | 无 |

启动加载期与已知加载失败状态均采用失败关闭（fail closed）策略：由于预签名 URL（Presigned URL）本身已在查询字符串中携带认证签名，存储桶自定义的 CORS 配置是浏览器端唯一能够约束其调用源（Origin）的边界；若在桶元数据加载失败时回退到宽松的全局 CORS 策略，泄露的预签名 URL 就可能被任意网页源跨域调用。

## 被拒绝的替代方案 {#alternatives}

| 被拒绝的替代方案 | 拒绝原因 |
| --- | --- |
| 在调用旧 CORS 加载器前先校验桶名语法 | 攻击者仍可构造无穷多个语法合法但并不存在的桶名，依然会触发鉴权前磁盘 I/O |
| 加载 CORS 前先调用 `GetBucketInfo` | 只是把 11 次元数据探测替换成每个伪造桶名至少 1 次不受限的后端存储探测 |
| 为不存在的桶增加带 TTL 的负缓存 | 只能限制单条缓存存活时间，无法限制攻击者构造海量不同桶名的基数（Cardinality）与初始 I/O 放大 |
| 在 SigV4 验签前直接剥离复制请求头 | 破坏 SigV4 规范化请求计算，导致合法请求报 `SignatureDoesNotMatch` |
| 拒绝所有携带内部复制标记头的请求 | 会使原本应被忽略的多余请求头引发大面积客户端报错，并打断合法的仅标记（marker-only）复制调用 |
| 要求所有受信任复制请求都携带 `REPLICA` | 破坏复制 `UploadPart`、`CompleteMultipartUpload` 与批量复制的真实线缆兼容性 |
| 在 `ObjectOptions` 中保存布尔值，但让事件与对象锁继续读请求头 | 留下两个可能互相矛盾的信任源 |

## 实现分层与验证矩阵 {#implementation}

整体实现划分为七个清晰边界：

1. 独立的请求信任模块负责精确解析标记头、评估复制 IAM 权限、将私有信任结构体写入 `req.Context()`，并生成验签后的清洗版请求克隆；
2. `putOpts`、`copyDstOpts`、`getOpts` 与 `delOpts` 构造器仅在调用方传入受信任状态时才解析源端复制字段；
3. `DecryptObjectInfo`、通知事件参数构造、分片上传完成、删除选项与对象锁统一消费同一份上下文决策；
4. 各 S3 处理器在现有身份认证通过后立即计算复制信任结论；
5. 分片上传（`PutObjectPart`）将当前请求的 `trusted` 状态与分片上传初始化时持久化的 `REPLICA` 来源状态结合判定；
6. 通用用户元数据提取器不再接受 `X-Amz-Replication-Status`；
7. `corsHandler` 使用独立的纯内存驻留访问器，绝不调用缓存未命中即读盘的通用加载器。

### 验证矩阵 {#verification}

自动化回归测试与真实双站点 TLS 黑盒复制测试共同验证了以下场景：

- 数百个不同的合法未创建桶名在预检（preflight）与实际 CORS 请求下，磁盘元数据读取次数为零且 `metadataMap` 大小不增长；
- 最小权限的 SSE-C `GetObject`、`HeadObject` 与 `GetObjectAttributes` 调用方在缺失、大小写错误或未授权复制标记下均无法绕过密钥检查；
- 仅携带标记头的批量风格 `PutObject` 只有在具备 `s3:ReplicateObject` 权限时才保留源端 ETag 与 `MTime`；
- 未获授权的 `REPLICA` `PutObject` 与 `DeleteObject` 稳定返回 `403 AccessDenied`；
- 浏览器 `POST` 表单策略无法伪造 `REPLICA` 状态；
- 对象锁过去保留时间在无 `replicaTrusted` 时被拒绝、在受信任副本写入时正常放行；
- 两个启用 TLS 的 SILO 节点通过真实站点复制同步 SSE-C 4 KiB 单对象、SSE-C 12 MiB 三分片对象、SSE-C `CopyObject` 以及复制删除标记，源端与目标端的 ETag、大小、`VersionID`、SSE-C 密钥 MD5 及解密后 SHA-256 完全一致。

## 兼容性与后续工作 {#impact}

- **普通客户端：** 请求无需任何修改；不可信的内部复制请求头会被安全忽略，不再获得特权语义。
- **批量复制（Batch Replication）：** 目标端凭据必须包含 `s3:ReplicateObject` 权限（详见[批量复制配置文档](/zh/administration/batch-framework-job-replicate/)）；缺少该权限时，接收端会将仅带标记头的写入当作普通写入处理，不再保留源端 ETag 与 `MTime`。
- **滚动升级：** 线缆协议与磁盘格式完全不变。新节点立即执行纯内存 CORS 查询与复制信任边界。

### 后续演进 {#residual-risks}

- **复制执行可靠性（2026-09-09）：** [复制可靠性：删除完成、MRF 可见性与重同步取消](/zh/blog/design/replication-reliability/)记录了 [PR #162](https://github.com/pgsty/silo/pull/162) 对 [#153](https://github.com/pgsty/silo/issues/153)、[#152](https://github.com/pgsty/silo/issues/152) 与 [#137](https://github.com/pgsty/silo/issues/137) 的修复，处理受信任复制请求进入执行流水线后的状态收敛问题。
- **限频诊断日志：** 当携带复制标记头的请求缺少复制权限并回退为普通写入时，接收端会输出限频告警日志，帮助运维人员快速排查缺少 `s3:ReplicateObject` 权限的批量复制任务，避免将其误判为底层 ETag/MTime 不一致。

## 结论 {#conclusion}

该修复于 [`0079723d3`](https://github.com/pgsty/silo/commit/0079723d38b59cc37781523915a60bcfa21c9706)（[PR #159](https://github.com/pgsty/silo/pull/159)）合入主分支并随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布，通过纯内存驻留 CORS 查询与鉴权后统一计算的复制信任边界，彻底消除了未认证桶元数据磁盘探测与未受信任复制请求头注入。
