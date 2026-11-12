---
title: "S3 API 兼容性"
url: "/zh/reference/s3-api-compatibility/"
weight: 250
icon: fa-solid fa-cloud
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/s3-api-compatibility.rst
upstream_modified: true
---

**SILO 20261109 契约：** 本页继承 S3 API 目录，当前目标为 [SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`），包括持锁批量版本清除、两阶段恢复、跨池生命周期仲裁检查以及按当前对象求值的分片条件。[普通 LIST](/zh/blog/design/listing-recovery-lock-cost/)、[Object Lock](/zh/blog/release/silo-20261109/#authorization) 和[分片列表](/zh/blog/design/list-multipart-uploads/#implementation)仍有文档列出的限定与错误行为。校验和消息可能改变，错误码契约见[校验和说明](/zh/blog/design/complete-multipart-checksum-errors/#october-errors)。

<a id="s3-api"></a>

本页面记录 MinIO 对象存储支持的 S3 API。 如需查看任意 API 的参考文档，请参阅 Amazon S3 的对应文档。

> [!WARNING]
> **重要**
>
> MinIO 强烈建议使用 [S3 兼容 SDK](/zh/developers/minio-drivers/#minio-drivers) 执行对象存储操作。

<a id="api" data-td-print-local></a>

## 对象 API {#object-apis}

- [CopyObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html)
  - **SILO 20261109：** 单池写入与删除统一在对象所属纠删码集合内加锁（[#298](https://github.com/pgsty/silo/issues/298)），修复规范化路径别名导致的自锁死锁（[#299](https://github.com/pgsty/silo/issues/299)），并消除等待源对象期间的目标锁饥饿（[#300](https://github.com/pgsty/silo/issues/300)）。
- [DeleteObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html)
- [DeleteObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html)
  - **条件 DELETE：**已发布的 Server 20260903 忽略 `If-Match`。Server 20260916 通过 #145/#178 支持单个 `DeleteObject` 的非空 `If-Match`，显式版本比较指定版本。批量 `DeleteObjects` 仍忽略 `<Object><ETag>`，没有逐项条件保护。详见[范围与限制](/zh/blog/design/conditional-delete/)。
  - **SILO 20261109：** 在变更锁内跨所有存储池串行核验物理版本删除（`6ef3a52fc`），防止并发修改法定保留或保留期时绕过锁定保护；删除目录对象 `null` 版本前检查 Object Lock（`aa2d79daf`）；普通批量删除按纠删码集合分组并发执行（[#301](https://github.com/pgsty/silo/issues/301)）。
- [DeleteObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjectTagging.html)
- [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html)
  - **SILO 20261109：** 当节点仅看到已存在对象的部分驱动器视图时，返回可重试的 `503 ServiceUnavailable` 而非 `404 NoSuchKey`（[#302](https://github.com/pgsty/silo/issues/302)）。20261109 已知限制（[#293](https://github.com/pgsty/silo/issues/293)，`main` 已由 [PR #294](https://github.com/pgsty/silo/pull/294) 修复）：仅通过对象标签授权的读取在底层对象不可读时仍返回 `403 AccessDenied`。
- [GetObjectAttributes](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectAttributes.html)
- [GetObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectTagging.html)
- [HeadObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html)
  - **SILO 20261109：** 已知部分驱动器视图场景下返回可重试的 `503 ServiceUnavailable` 而非 `404 NoSuchKey`（[#302](https://github.com/pgsty/silo/issues/302)）；仅通过对象标签授权且对象不可读时在 20261109 中仍返回 `403`（[#293](https://github.com/pgsty/silo/issues/293)，`main` 已由 [PR #294](https://github.com/pgsty/silo/pull/294) 修复）。
- [ListObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html)
- [ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html)
- [ListObjectVersions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectVersions.html)
- [PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)
- [PutObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectTagging.html)
- [RestoreObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_RestoreObject.html)
  - **SILO 20261109（`POST ?restore`）：** 采用两阶段就地恢复，从远端存储层下载期间不持有对象写锁（[#284](https://github.com/pgsty/silo/issues/284)、[#289](https://github.com/pgsty/silo/issues/289)）。恢复取消或失败时先尝试 `100 ms` 标记清理并立即返回，未完成的标记转入后台受限重试清理。混合版本滚动升级期间，只要存在旧版本或不可达对端节点，新节点对 `POST ?restore` 返回 `503 ServiceUnavailable`。
- [SelectObjectContent](https://docs.aws.amazon.com/AmazonS3/latest/API/API_SelectObjectContent.html)

### 写入提交错误 {#write-commit-errors}

[PR #232](https://github.com/pgsty/silo/pull/232) 包含于 Server 20261018 正式版：PUT 或分片上传完成操作在最终提交时丢失暂存的 `xl.meta`，返回 HTTP 503
`SlowDownWrite`。原代码可能对 PUT 返回 `400 IncompleteBody`，对分片完成返回
`404 NoSuchKey`。真正的客户端上传不完整仍保留原有错误处理。这项分类修复允许 SDK
重试，但不会恢复丢失的暂存数据。见[源码与发布边界](/zh/compatibility/versions/#post-20261015)。

<a id="id2" data-td-print-local></a>

### 对象锁定 {#object-locking}

- [GetObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html)
- [PutObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectRetention.html)
- [GetObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLegalHold.html)
- [PutObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLegalHold.html)
- [GetObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLockConfiguration.html)
- [PutObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLockConfiguration.html)

<a id="id3" data-td-print-local></a>

### 不支持的 API 对象端点 {#unsupported-api-object-endpoints}

```text
GetObjectAcl
PutObjectAcl
```

<a id="id4" data-td-print-local></a>

### 多部分上传 {#multipart-uploads}

- [AbortMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_AbortMultipartUpload.html)
- [CompleteMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)
  - **SILO 20261109：** 普通分段上传完成（`CompleteMultipartUpload`）尝试失败后，原上传仍保持可用并可继续重试（[#327](https://github.com/pgsty/silo/issues/327)）。
- [CreateMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateMultipartUpload.html)
  - **SILO 20261109：** 多存储池部署下，`If-Match` 与 `If-None-Match` 条件统一针对跨池当前对象求值（[#291](https://github.com/pgsty/silo/issues/291)、[PR #292](https://github.com/pgsty/silo/pull/292)）。
- [ListMultipartUploads](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html)
- [ListParts](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html)
- [UploadPart](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html)
- [UploadPartCopy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html)

<a id="id5" data-td-print-local></a>

#### 与 S3 API 在多部分上传方面的差异 {#differences-from-s3-apis-for-multipart-uploads}

- 已发布的 Server 20260903：`ListMultipartUploads` 将非空 `prefix` 当成精确对象名；空 prefix 使用节点本地易失缓存，不具备完整分页、marker 和 delimiter 语义。
- Server 20260916 以可选 strict 模式增加持久扫描，默认仍保留 legacy 精确键／缓存行为。运行该版本时仍适用其[历史升级契约](/zh/blog/design/list-multipart-uploads/#implementation-20260916)。
- **[SILO 20261109](/zh/blog/release/silo-20261109/)（自 Server 20261018 起）：** 撤回默认持久扫描，公开列表恢复无 prefix 的节点缓存和非空 prefix 的精确对象查找（[#79](https://github.com/pgsty/silo/issues/79)）；重启漏项、真正前缀筛选及缓存分页缺陷仍然存在。模式开关被忽略并告警，旧共享配置键被容忍；已有 strict 用户会失去可选持久列表和严格取消。诊断扫描保留资源限制但不控制业务入口。身份字段、安全校验、默认尽力取消和后台清理修复保留。见[决策、容量与限制](/zh/blog/design/list-multipart-uploads/#decision-20261018)。
- `PutBucketLifecycle` 不支持 `AbortIncompleteMultipartUpload` 生命周期动作。

<a id="id6" data-td-print-local></a>

## 存储桶 API {#bucket-apis}

- [CreateBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateBucket.html)
- [DeleteBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucket.html)
- [DeleteBucketEncryption](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketEncryption.html)
- [DeleteBucketTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketTagging.html)
- [GetBucketEncryption](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketEncryption.html)
- [GetBucketLocation](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLocation.html)
- [GetBucketTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketTagging.html)
- [GetBucketVersioning](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketVersioning.html)
- [HeadBucket](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadBucket.html)
- [ListBuckets](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListBuckets.html)
- [ListDirectoryBuckets](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListDirectoryBuckets.html)
- [PutBucketEncryption](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketEncryption.html)
- [PutBucketTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketTagging.html)
- [PutBucketVersioning](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketVersioning.html)

<a id="id7" data-td-print-local></a>

### 存储桶复制 {#bucket-replication}

- [GetBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketReplication.html)
- [PutBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketReplication.html)
  - **SILO 20261109：** 复制删除保留目标端的 Object Lock 保留期与法定保留（`7e9ee6bef`）；源端通过绕过 `GOVERNANCE` 保留期发起的版本清除在目标端仍受锁保护时会被拒绝，源端持续重试直至目标锁允许删除。
- [DeleteBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketReplication.html)

<a id="id8" data-td-print-local></a>

### 存储桶生命周期 {#bucket-lifecycle}

- [GetBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycle.html)
- [GetBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycleConfiguration.html)
- [PutBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycle.html)
  - **SILO 20261109：** 生命周期过期在对象锁内跨所有存储池评估权威版本历史与 Object Lock 保护状态（[#278](https://github.com/pgsty/silo/issues/278)），将 `ExpiredObjectAllVersions` 与 `DelMarkerExpiration` 严格限定在过期精确键而不误删子键（[#297](https://github.com/pgsty/silo/issues/297)），执行仅含 `DelMarkerExpiration` 动作的规则（[#268](https://github.com/pgsty/silo/issues/268)），仅使已分层当前版本的本地临时恢复副本过期而保留底层对象（[#281](https://github.com/pgsty/silo/issues/281)），且不再复制由生命周期生成的删除标记或版本清除（`1bd0b1b04`）。
- [PutBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)
- [DeleteBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketLifecycle.html)

<a id="id9" data-td-print-local></a>

### 存储桶通知 {#bucket-notifications}

- [GetBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotification.html)
- [GetBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotificationConfiguration.html)
- [PutBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotification.html)
- [PutBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotificationConfiguration.html)

<a id="id10" data-td-print-local></a>

### 存储桶策略 {#bucket-policies}

- [GetBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicy.html)
- [GetBucketPolicyStatus](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicyStatus.html)
- [PutBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketPolicy.html)
- [DeleteBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketPolicy.html)
- [GetBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketCors.html)
- [PutBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketCors.html)
- [DeleteBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketCors.html)

<a id="id11" data-td-print-local></a>

### 不支持的 API 存储桶操作 {#unsupported-api-bucket-operations}

```text
GetBucketInventoryConfiguration
PutBucketInventoryConfiguration
DeleteBucketInventoryConfiguration
GetBucketMetricsConfiguration
PutBucketMetricsConfiguration
DeleteBucketMetricsConfiguration
PutBucketWebsite
GetBucketLogging
PutBucketLogging
PutBucketAccelerateConfiguration
DeleteBucketAccelerateConfiguration
PutBucketRequestPayment
DeleteBucketRequestPayment
PutBucketAcl
HeadBucketAcl
GetPublicAccessBlock
PutPublicAccessBlock
DeletePublicAccessBlock
GetBucketOwnershipControls
PutBucketOwnershipControls
DeleteBucketOwnershipControls
GetBucketIntelligentTieringConfiguration
PutBucketIntelligentTieringConfiguration
ListBucketIntelligentTieringConfigurations
DeleteBucketIntelligentTieringConfiguration
GetBucketAnalyticsConfiguration
PutBucketAnalyticsConfiguration
ListBucketAnalyticsConfigurations
DeleteBucketAnalyticsConfiguration
CreateSession
```

<a id="minio" data-td-print-local></a>

### MinIO 针对不支持的存储桶资源的替代方案 {#minio-alternatives-for-unsupported-bucket-resources}

- 对于 `BucketACL` 或 `ObjectACL` 操作调用，请使用 [Policies](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。
- 自 `RELEASE.2026-09-03T13-18-01Z` 起支持 `BucketCORS` 操作。设置了自身 CORS 配置的存储桶只按该配置响应；未设置的存储桶使用服务端全局的 `MINIO_API_CORS_ALLOW_ORIGIN` 策略，默认允许所有来源。
- 对于 `BucketWebsite` 操作调用，请使用 `caddy` 或 `nginx`。
- 对于 `BucketAnalytics`、`BucketMetrics` 或 `BucketLogging` 操作调用，请使用 [存储桶通知](/zh/administration/monitoring/bucket-notifications/#minio-bucket-notifications)。
