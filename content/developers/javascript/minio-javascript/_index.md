---
title: "JavaScript Quickstart Guide"
url: "/developers/javascript/minio-javascript/"
weight: 50
icon: fa-brands fa-js
minio_origin: true
silo_modified: true
---

<a id="javascript-quickstart-guide"></a>
<a id="minio-javascript-quickstart"></a>

## 适用于 Amazon S3 兼容对象存储的 MinIO JavaScript 库 [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) {#amazon-s3-minio-javascript}

[![NPM](https://nodei.co/npm/minio.png)](https://nodei.co/npm/minio/)

MinIO JavaScript Client SDK 提供了高级 API，可用于访问任何兼容 Amazon S3 的对象存储服务器。

本指南介绍如何安装 client SDK 并执行一个 JavaScript 示例程序。 如需完整的 API 与示例列表，请参阅 [JavaScript Client API Reference](https://github.com/minio/minio-js/blob/master/docs/API.md) 文档。

本文档假定你已具备可用的 [Node.js](http://nodejs.org/) 开发环境，支持的 LTS 版本为 v16、v18 或 v20。

### 从 NPM 下载 {#npm}

```sh
npm install --save minio

```

### 从源码下载 {#id1}

```sh
git clone https://github.com/minio/minio-js
cd minio-js
npm install
npm run build
npm install -g

```

### 与 TypeScript 搭配使用 {#typescript}

`minio>7.1.0` 已内置类型定义，不再需要 `@types/minio`。

### 初始化 MinIO Client {#minio-client}

连接到 MinIO 对象存储服务器需要以下参数：

| Parameter | Description |
| --- | --- |
| `endPoint` | 对象存储服务的主机名。 |
| `port` | TCP/IP 端口号。可选；默认为 HTTP 的 `80` 和 HTTPS 的 `443`。 |
| `accessKey` | S3 服务中某个账户的访问密钥（用户 ID）。 |
| `secretKey` | S3 服务中某个账户的 Secret Key（相当于密码）。 |
| `useSSL` | 可选，将其设置为 `true` 以启用安全（HTTPS）访问。 |

```js
import * as Minio from 'minio'

const minioClient = new Minio.Client({
  endPoint: 'play.min.io',
  port: 9000,
  useSSL: true,
  accessKey: 'Q3AM3UQ867SPQQA43P2F',
  secretKey: 'zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG',
})

```

### 快速开始示例 - 文件上传器 {#id2}

该示例连接到对象存储服务器，创建一个存储桶，并将文件上传到该存储桶。 它使用 MinIO `play` 服务器，即位于 [https://play.min.io](https://play.min.io) 的公开 MinIO 集群。

`play` 服务器运行 MinIO 的最新稳定版本，可用于测试和开发。 本示例中展示的访问凭据对公众开放。 上传到 `play` 的所有数据都应视为公开且不受保护。

#### file-uploader.mjs {#file-uploader-mjs}

```js
import * as Minio from 'minio'

// Instantiate the MinIO client with the object store service
// endpoint and an authorized user's credentials
// play.min.io is the MinIO public test cluster
const minioClient = new Minio.Client({
  endPoint: 'play.min.io',
  port: 9000,
  useSSL: true,
  accessKey: 'Q3AM3UQ867SPQQA43P2F',
  secretKey: 'zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG',
})

// File to upload
const sourceFile = '/tmp/test-file.txt'

// Destination bucket
const bucket = 'js-test-bucket'

// Destination object name
const destinationObject = 'my-test-file.txt'

// Check if the bucket exists
// If it doesn't, create it
const exists = await minioClient.bucketExists(bucket)
if (exists) {
  console.log('Bucket ' + bucket + ' exists.')
} else {
  await minioClient.makeBucket(bucket, 'us-east-1')
  console.log('Bucket ' + bucket + ' created in "us-east-1".')
}

// Set the object metadata
var metaData = {
  'Content-Type': 'text/plain',
  'X-Amz-Meta-Testing': 1234,
  example: 5678,
}

// Upload the file with fPutObject
// If an object with the same name exists,
// it is updated with new data
await minioClient.fPutObject(bucket, destinationObject, sourceFile, metaData)
console.log('File ' + sourceFile + ' uploaded as object ' + destinationObject + ' in bucket ' + bucket)

```

#### 运行文件上传器 {#id3}

```sh
node file-uploader.mjs
Bucket js-test-bucket created successfully in "us-east-1".
File /tmp/test-file.txt uploaded successfully as my-test-file.txt to bucket js-test-bucket

```

使用 [`mc`](/reference/minio-mc/#command-mc) 验证对象已创建：

```text
mc ls play/js-test-bucket
[2023-11-10 17:52:20 UTC]  20KiB STANDARD my-test-file.txt

```

### API 参考 {#api}

完整的 API 参考可在此查看：

- [MinIO JavaScript API Reference](https://github.com/minio/minio-js/blob/master/docs/API.md)

#### 存储桶操作 {#id4}

- [`makeBucket`](https://github.com/minio/minio-js/blob/master/docs/API.md#makeBucket)
- [`listBuckets`](https://github.com/minio/minio-js/blob/master/docs/API.md#listBuckets)
- [`bucketExists`](https://github.com/minio/minio-js/blob/master/docs/API.md#bucketExists)
- [`removeBucket`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeBucket)
- [`listObjects`](https://github.com/minio/minio-js/blob/master/docs/API.md#listObjects)
- [`listObjectsV2`](https://github.com/minio/minio-js/blob/master/docs/API.md#listObjectsV2)
- [`listObjectsV2WithMetadata`](https://github.com/minio/minio-js/blob/master/docs/API.md#listObjectsV2WithMetadata) (Extension)
- [`listIncompleteUploads`](https://github.com/minio/minio-js/blob/master/docs/API.md#listIncompleteUploads)
- [`getBucketVersioning`](https://github.com/minio/minio-js/blob/master/docs/API.md#getBucketVersioning)
- [`setBucketVersioning`](https://github.com/minio/minio-js/blob/master/docs/API.md#setBucketVersioning)
- [`setBucketLifecycle`](https://github.com/minio/minio-js/blob/master/docs/API.md#setBucketLifecycle)
- [`getBucketLifecycle`](https://github.com/minio/minio-js/blob/master/docs/API.md#getBucketLifecycle)
- [`removeBucketLifecycle`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeBucketLifecycle)
- [`getObjectLockConfig`](https://github.com/minio/minio-js/blob/master/docs/API.md#getObjectLockConfig)
- [`setObjectLockConfig`](https://github.com/minio/minio-js/blob/master/docs/API.md#setObjectLockConfig)

#### 文件对象操作 {#id5}

- [`fPutObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#fPutObject)
- [`fGetObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#fGetObject)

#### 对象操作 {#id6}

- [`getObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#getObject)
- [`putObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#putObject)
- [`copyObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#copyObject)
- [`statObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#statObject)
- [`removeObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeObject)
- [`removeObjects`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeObjects)
- [`removeIncompleteUpload`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeIncompleteUpload)
- [`selectObjectContent`](https://github.com/minio/minio-js/blob/master/docs/API.md#selectObjectContent)

#### Presigned 操作 {#presigned}

- [`presignedUrl`](https://github.com/minio/minio-js/blob/master/docs/API.md#presignedUrl)
- [`presignedGetObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#presignedGetObject)
- [`presignedPutObject`](https://github.com/minio/minio-js/blob/master/docs/API.md#presignedPutObject)
- [`presignedPostPolicy`](https://github.com/minio/minio-js/blob/master/docs/API.md#presignedPostPolicy)

#### 存储桶通知操作 {#id7}

- [`getBucketNotification`](https://github.com/minio/minio-js/blob/master/docs/API.md#getBucketNotification)
- [`setBucketNotification`](https://github.com/minio/minio-js/blob/master/docs/API.md#setBucketNotification)
- [`removeAllBucketNotification`](https://github.com/minio/minio-js/blob/master/docs/API.md#removeAllBucketNotification)
- [`listenBucketNotification`](https://github.com/minio/minio-js/blob/master/docs/API.md#listenBucketNotification) (MinIO Extension)

#### 存储桶策略操作 {#id8}

- [`getBucketPolicy`](https://github.com/minio/minio-js/blob/master/docs/API.md#getBucketPolicy)
- [`setBucketPolicy`](https://github.com/minio/minio-js/blob/master/docs/API.md#setBucketPolicy)

### 示例 {#id9}

#### 存储桶操作 {#id10}

- [list-buckets.mjs](https://github.com/minio/minio-js/blob/master/examples/list-buckets.mjs)
- [list-objects.js](https://github.com/minio/minio-js/blob/master/examples/list-objects.js)
- [list-objects-v2.js](https://github.com/minio/minio-js/blob/master/examples/list-objects-v2.js)
- [list-objects-v2-with-metadata.js](https://github.com/minio/minio-js/blob/master/examples/list-objects-v2-with-metadata.js) (Extension)
- [bucket-exists.mjs](https://github.com/minio/minio-js/blob/master/examples/bucket-exists.mjs)
- [make-bucket.mjs](https://github.com/minio/minio-js/blob/master/examples/make-bucket.js)
- [remove-bucket.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-bucket.mjs)
- [list-incomplete-uploads.js](https://github.com/minio/minio-js/blob/master/examples/list-incomplete-uploads.js)
- [get-bucket-versioning.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-versioning.js)
- [set-bucket-versioning.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-versioning.js)
- [set-bucket-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-tagging.js)
- [get-bucket-versioning.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-versioning.js)
- [set-bucket-versioning.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-versioning.js)
- [set-bucket-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-tagging.js)
- [get-bucket-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-tagging.mjs)
- [remove-bucket-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-bucket-tagging.js)
- [set-bucket-lifecycle.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-lifecycle.mjs)
- [get-bucket-lifecycle.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-lifecycle.mjs)
- [remove-bucket-lifecycle.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-bucket-lifecycle.mjs)
- [get-object-lock-config.mjs](https://github.com/minio/minio-js/blob/master/examples/get-object-lock-config.mjs)
- [set-object-lock-config.mjs](https://github.com/minio/minio-js/blob/master/examples/set-object-lock-config.mjs)
- [set-bucket-replication.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-replication.mjs)
- [get-bucket-replication.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-replication.mjs)
- [remove-bucket-replication.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-bucket-replication.mjs)
- [set-bucket-encryption.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-encryption.mjs)
- [get-bucket-encryption.mjs](https://github.com/minio/minio-js/blob/master/examples/get-bucket-encryption.mjs)
- [remove-bucket-encryption.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-bucket-encryption.mjs)

#### 文件对象操作 {#id11}

- [fput-object.mjs](https://github.com/minio/minio-js/blob/master/examples/fput-object.js)
- [fget-object.mjs](https://github.com/minio/minio-js/blob/master/examples/fget-object.mjs)

#### 对象操作 {#id12}

- [put-object.js](https://github.com/minio/minio-js/blob/master/examples/put-object.js)
- [get-object.mjs](https://github.com/minio/minio-js/blob/master/examples/get-object.mjs)
- [copy-object.js](https://github.com/minio/minio-js/blob/master/examples/copy-object.js)
- [get-partialobject.mjs](https://github.com/minio/minio-js/blob/master/examples/get-partialobject.mjs)
- [remove-object.js](https://github.com/minio/minio-js/blob/master/examples/remove-object.js)
- [remove-incomplete-upload.js](https://github.com/minio/minio-js/blob/master/examples/remove-incomplete-upload.js)
- [stat-object.mjs](https://github.com/minio/minio-js/blob/master/examples/stat-object.mjs)
- [get-object-retention.mjs](https://github.com/minio/minio-js/blob/master/examples/get-object-retention.mjs)
- [put-object-retention.mjs](https://github.com/minio/minio-js/blob/master/examples/put-object-retention.mjs)
- [put-object-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/put-object-tagging.js)
- [get-object-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/get-object-tagging.mjs)
- [remove-object-tagging.mjs](https://github.com/minio/minio-js/blob/master/examples/remove-object-tagging.js)
- [set-object-legal-hold.mjs](https://github.com/minio/minio-js/blob/master/examples/set-object-legalhold.mjs)
- [get-object-legal-hold.mjs](https://github.com/minio/minio-js/blob/master/examples/get-object-legal-hold.mjs)
- [compose-object.mjs](https://github.com/minio/minio-js/blob/master/examples/compose-object.js)
- [select-object-content.mjs](https://github.com/minio/minio-js/blob/master/examples/select-object-content.mjs)

#### Presigned 操作 {#id13}

- [presigned-getobject.mjs](https://github.com/minio/minio-js/blob/master/examples/presigned-getobject.js)
- [presigned-putobject.mjs](https://github.com/minio/minio-js/blob/master/examples/presigned-putobject.js)
- [presigned-postpolicy.mjs](https://github.com/minio/minio-js/blob/master/examples/presigned-postpolicy.js)

#### 存储桶通知操作 {#id14}

- [get-bucket-notification.js](https://github.com/minio/minio-js/blob/master/examples/get-bucket-notification.js)
- [set-bucket-notification.js](https://github.com/minio/minio-js/blob/master/examples/set-bucket-notification.js)
- [remove-all-bucket-notification.js](https://github.com/minio/minio-js/blob/master/examples/remove-all-bucket-notification.js)
- [listen-bucket-notification.js](https://github.com/minio/minio-js/blob/master/examples/minio/listen-bucket-notification.js) (MinIO Extension)

#### 存储桶策略操作 {#id15}

- [get-bucket-policy.js](https://github.com/minio/minio-js/blob/master/examples/get-bucket-policy.js)
- [set-bucket-policy.mjs](https://github.com/minio/minio-js/blob/master/examples/set-bucket-policy.mjs)

### 自定义设置 {#id16}

- [setAccelerateEndPoint](https://github.com/minio/minio-js/blob/master/examples/set-accelerate-end-point.js)

### 深入了解 {#id17}

- [JavaScript SDK source and current documentation](https://github.com/minio/minio-js)
- [MinIO JavaScript Client SDK API Reference](https://github.com/minio/minio-js/blob/master/docs/API.md)

### 贡献 {#id18}

- [Contributors Guide](https://github.com/minio/minio-js/blob/master/CONTRIBUTING.md)

![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/minio/minio-js/nodejs.yml)
