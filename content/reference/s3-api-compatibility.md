---
title: "S3 API Compatibility"
url: "/reference/s3-api-compatibility/"
weight: 250
icon: fa-solid fa-cloud
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/s3-api-compatibility.rst
upstream_modified: true
---

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

- `ListMultipartUploads` currently treats a non-empty `prefix` as an exact object name instead of a lexical key prefix.
- With an empty prefix, its result comes from node-local volatile state and does not provide AWS-compatible pagination, marker, or delimiter behavior. See the [issue #79 design and decision record](/blog/design/list-multipart-uploads/) for the verified impact and proposed repair.
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

### Unsupported API Bucket Operations {#unsupported-api-bucket-operations}

```text
GetBucketInventoryConfiguration
PutBucketInventoryConfiguration
DeleteBucketInventoryConfiguration
PutBucketCors
DeleteBucketCors
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
- Calls to `BucketCORS` operations are not needed because CORS is enabled by default on all buckets for all HTTP verbs.
- For calls to `BucketWebsite` operations, use `caddy` or `nginx`.
- For calls to `BucketAnalytics`, `BucketMetrics`, or `BucketLogging` operations, use [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).
