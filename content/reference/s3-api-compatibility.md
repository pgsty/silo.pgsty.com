---
title: "S3 API Compatibility"
url: "/reference/s3-api-compatibility/"
weight: 250
icon: fa-solid fa-cloud
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/s3-api-compatibility.rst
upstream_modified: true
---

> [!WARNING]
> **Release-status correction (2026-10-17):** SILO `RELEASE.2026-10-15T00-00-00Z` was returned to Draft and is not the current public release; the published Server remains 20260916. Historical statements below that 20261015 is published or downloadable are superseded, and its fixes must not be treated as delivered in a public release. 20261018 is being prepared as a tag and draft only. See the [component matrix](/compatibility/versions/) and [download page](/download/).

<a id="s3-api-compatibility"></a>

This page documents S3 APIs supported by MinIO Object Storage. For reference documentation on any given API, see the corresponding documentation for Amazon S3.

> [!WARNING]
> **Important**
>
> MinIO strongly recommends using an [S3-Compatible SDK](/developers/minio-drivers/#minio-drivers) for performing object storage operations.

## Object APIs {#object-apis}

- [CopyObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CopyObject.html)
- [DeleteObject](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObject.html)
- [DeleteObjects](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html)
  - **Conditional DELETE:** published Server 20260903 ignores `If-Match`. Server 20260916 supports nonempty `If-Match` on single `DeleteObject` (#145/#178), including addressed-version comparison. Batch `DeleteObjects` still ignores `<Object><ETag>` and provides no per-item conditional guard. See [scope and limitations](/blog/design/conditional-delete/).
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

### Write commit errors {#write-commit-errors}

[PR #232](https://github.com/pgsty/silo/pull/232), targeting the next Server
release after 20261015, returns HTTP 503 `SlowDownWrite` when staged `xl.meta`
disappears at the final commit of PUT or multipart completion. Earlier code
could report `400 IncompleteBody` for PUT or `404 NoSuchKey` for completion.
Actual incomplete client uploads retain their existing error handling. This
classification allows SDK retries; it does not restore lost staging data.
See the [source and release boundary](/compatibility/versions/#post-20261015).

### Object Locking {#object-locking}

- [GetObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectRetention.html)
- [PutObjectRetention](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectRetention.html)
- [GetObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLegalHold.html)
- [PutObjectLegalHold](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLegalHold.html)
- [GetObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetObjectLockConfiguration.html)
- [PutObjectLockConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutObjectLockConfiguration.html)

### Unsupported API Object Endpoints {#unsupported-api-object-endpoints}

```text
GetObjectAcl
PutObjectAcl
```

### Multipart Uploads {#multipart-uploads}

- [AbortMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_AbortMultipartUpload.html)
- [CompleteMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)
- [CreateMultipartUpload](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CreateMultipartUpload.html)
- [ListMultipartUploads](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html)
- [ListParts](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html)
- [UploadPart](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html)
- [UploadPartCopy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html)

#### Differences from S3 APIs for Multipart Uploads {#differences-from-s3-apis-for-multipart-uploads}

- Published Server 20260903 treats a non-empty `ListMultipartUploads` prefix as an exact object name. An empty prefix uses node-local volatile state without complete pagination, marker or delimiter semantics.
- Server 20260916 adds persistent scanning as an opt-in strict mode while retaining legacy exact-key/cache behavior by default. Its [historical upgrade contract](/blog/design/list-multipart-uploads/#implementation-20260916) still applies to those binaries.
- **Unreleased #79 follow-up:** persistent listing becomes the only path, with global prefix, delimiter and pagination semantics. The mode environment variable is ignored. Readable old uploads missing both identity fields are omitted without blocking new uploads; the old exact-key shortcut is removed. This historical-record omission is an explicit S3 compatibility exception. Metadata errors, insufficient coverage and resource limits still return errors. Preflight becomes diagnostic, and cancellation keeps its previous default read-quorum/best-effort behavior. Every page still scans storage; delayed creation writes can still restore an upload after cancellation. See the [candidate contract, capacity and limits](/blog/design/list-multipart-uploads/#implementation).
- The `AbortIncompleteMultipartUpload` lifecycle action is not supported with `PutBucketLifecycle`.

## Bucket APIs {#bucket-apis}

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

### Bucket Replication {#bucket-replication}

- [GetBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketReplication.html)
- [PutBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketReplication.html)
- [DeleteBucketReplication](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketReplication.html)

### Bucket Lifecycle {#bucket-lifecycle}

- [GetBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycle.html)
- [GetBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketLifecycleConfiguration.html)
- [PutBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycle.html)
- [PutBucketLifecycleConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketLifecycleConfiguration.html)
- [DeleteBucketLifecycle](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketLifecycle.html)

### Bucket Notifications {#bucket-notifications}

- [GetBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotification.html)
- [GetBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketNotificationConfiguration.html)
- [PutBucketNotification](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotification.html)
- [PutBucketNotificationConfiguration](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketNotificationConfiguration.html)

### Bucket Policies {#bucket-policies}

- [GetBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicy.html)
- [GetBucketPolicyStatus](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketPolicyStatus.html)
- [PutBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketPolicy.html)
- [DeleteBucketPolicy](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketPolicy.html)
- [GetBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketCors.html)
- [PutBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketCors.html)
- [DeleteBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketCors.html)

### Unsupported API Bucket Operations {#unsupported-api-bucket-operations}

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

### MinIO alternatives for unsupported Bucket resources {#minio-alternatives-for-unsupported-bucket-resources}

- For calls to `BucketACL` or `ObjectACL` operations, use [Policies](/administration/identity-access-management/policy-based-access-control/#minio-policy).
- `BucketCORS` operations are supported since `RELEASE.2026-09-03T13-18-01Z`. A bucket with its own CORS configuration is served only by that configuration; buckets without one use the server-wide `MINIO_API_CORS_ALLOW_ORIGIN` policy, which allows every origin by default.
- For calls to `BucketWebsite` operations, use `caddy` or `nginx`.
- For calls to `BucketAnalytics`, `BucketMetrics`, or `BucketLogging` operations, use [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).
