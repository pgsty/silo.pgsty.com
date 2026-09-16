---
title: "S3 API 兼容性"
url: "/zh/reference/s3-api-compatibility/"
weight: 250
icon: fa-solid fa-cloud
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/s3-api-compatibility.rst
upstream_modified: true
---

<a id="s3-api"></a>

本页面记录 MinIO 对象存储支持的 S3 API。 如需查看任意 API 的参考文档，请参阅 Amazon S3 的对应文档。

> [!WARNING]
> **重要**
>
> MinIO 强烈建议使用 [S3 兼容 SDK](/zh/developers/minio-drivers/#minio-drivers) 执行对象存储操作。

## 对象 API {#api}

- [CopyObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html)
- [DeleteObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html)
- [DeleteObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html)
  - **条件 DELETE：**已发布的 Server 20260903 忽略 `If-Match`。Server 20260916 通过 #145/#178 支持单个 `DeleteObject` 的非空 `If-Match`，显式版本比较指定版本。批量 `DeleteObjects` 仍忽略 `<Object><ETag>`，没有逐项条件保护。详见[范围与限制](/blog/design/conditional-delete/)。
- [DeleteObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjectTagging.html)
- [GetObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObject.html)
- [GetObjectAttributes](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectAttributes.html)
- [GetObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectTagging.html)
- [HeadObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_HeadObject.html)
- [ListObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjects.html)
- [ListObjectsV2](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectsV2.html)
- [ListObjectVersions](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListObjectVersions.html)
- [PutObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObject.html)
- [PutObjectTagging](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectTagging.html)
- [RestoreObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_RestoreObject.html)
- [SelectObjectContent](https://docs.aws.amazon.com/AmazonS3/latest/API/API_SelectObjectContent.html)

### 对象锁定 {#id2}

- [GetObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html)
- [PutObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectRetention.html)
- [GetObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLegalHold.html)
- [PutObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLegalHold.html)
- [GetObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLockConfiguration.html)
- [PutObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLockConfiguration.html)

### 不支持的 API 对象端点 {#id3}

```text
GetObjectAcl
PutObjectAcl
```

### 多部分上传 {#id4}

- [AbortMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_AbortMultipartUpload.html)
- [CompleteMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)
- [CreateMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateMultipartUpload.html)
- [ListMultipartUploads](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html)
- [ListParts](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html)
- [UploadPart](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html)
- [UploadPartCopy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html)

#### 与 S3 API 在多部分上传方面的差异 {#id5}

- 已发布的 Server 20260903：`ListMultipartUploads` 将非空 `prefix` 当成精确对象名；空 prefix 使用节点本地易失缓存，不具备完整分页、marker 和 delimiter 语义。
- Server 20260916 通过 [PR #198](https://github.com/pgsty/silo/pull/198) 增加持久扫描与全局分页，并在原生 marker 对应上传被删除后继续翻页。经 #213 的兼容性修复，默认使用保留旧限制的 `legacy` 模式；严格模式仅通过 `MINIO_API_MULTIPART_LISTING=strict` 显式启用。启用严格模式前需要所有 writer 升级、旧上传排空、只读预检及容量验收；严格模式在覆盖不足、旧格式或资源超限时返回 503。普通升级不要求切换模式或强制排空上传。排序、扫描容量与迟到创建写入的取消边界见[实现与升级契约](/zh/blog/design/list-multipart-uploads/#implementation)。发布不代表严格模式已通过各部署的容量验收。
- `PutBucketLifecycle` 不支持 `AbortIncompleteMultipartUpload` 生命周期动作。

## 存储桶 API {#id6}

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

### 存储桶复制 {#id7}

- [GetBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketReplication.html)
- [PutBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketReplication.html)
- [DeleteBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketReplication.html)

### 存储桶生命周期 {#id8}

- [GetBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycle.html)
- [GetBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycleConfiguration.html)
- [PutBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycle.html)
- [PutBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)
- [DeleteBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketLifecycle.html)

### 存储桶通知 {#id9}

- [GetBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotification.html)
- [GetBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotificationConfiguration.html)
- [PutBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotification.html)
- [PutBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotificationConfiguration.html)

### 存储桶策略 {#id10}

- [GetBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicy.html)
- [GetBucketPolicyStatus](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicyStatus.html)
- [PutBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketPolicy.html)
- [DeleteBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketPolicy.html)
- [GetBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketCors.html)
- [PutBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketCors.html)
- [DeleteBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketCors.html)

### 不支持的 API 存储桶操作 {#id11}

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

### MinIO 针对不支持的存储桶资源的替代方案 {#minio}

- 对于 `BucketACL` 或 `ObjectACL` 操作调用，请使用 [Policies](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。
- 自 `RELEASE.2026-09-03T13-18-01Z` 起支持 `BucketCORS` 操作。设置了自身 CORS 配置的存储桶只按该配置响应；未设置的存储桶使用服务端全局的 `MINIO_API_CORS_ALLOW_ORIGIN` 策略，默认允许所有来源。
- 对于 `BucketWebsite` 操作调用，请使用 `caddy` 或 `nginx`。
- 对于 `BucketAnalytics`、`BucketMetrics` 或 `BucketLogging` 操作调用，请使用 [存储桶通知](/zh/administration/monitoring/bucket-notifications/#minio-bucket-notifications)。
