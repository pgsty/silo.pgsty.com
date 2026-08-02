---
title: "Rust 快速入门指南"
url: "/zh/developers/rust/minio-rust/"
weight: 70
icon: fa-brands fa-rust
minio_origin: true
silo_modified: false
---

<a id="rust"></a>
<a id="minio-rust-quickstart"></a>

## 用于 Amazon S3 兼容云存储的 MinIO Rust SDK {#amazon-s3-minio-rust-sdk}

[![CI](https://github.com/minio/minio-rs/actions/workflows/rust.yml/badge.svg?branch=master)](https://github.com/minio/minio-rs/actions/workflows/rust.yml) [![docs.rs](https://docs.rs/minio/badge.svg)](https://docs.rs/minio/latest/minio/) [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) [![Sourcegraph](https://sourcegraph.com/github.com/minio/minio-rs/-/badge.svg)](https://sourcegraph.com/github.com/minio/minio-rs?badge) [![crates.io](https://img.shields.io/crates/v/minio)](https://crates.io/crates/minio) [![Apache V2 License](https://img.shields.io/badge/license-Apache%20V2-blue.svg)](https://github.com/minio/minio-rs/blob/master/LICENSE)

MinIO Rust SDK 是一个 Simple Storage Service（即 S3）客户端，可用于在任意 Amazon S3 兼容对象存储服务上执行存储桶和对象操作。 它为 MinIO 和 Amazon S3 兼容对象存储 API 提供了强类型、异步优先的接口。

每个受支持的 S3 操作都对应一个请求构建器（例如：\[`BucketExists`\]、\[`PutObject`\]、\[`UploadPartCopy`\]），用户可通过 fluent builder 模式配置请求参数。

所有请求构建器都实现了 \[`S3Api`\] trait，该 trait 提供异步 [`send`](https://docs.rs/minio/latest/minio/) 方法，用于执行请求并返回强类型响应。

### 基本用法 {#id1}

```no_run
use minio::s3::Client;
use minio::s3::types::S3Api;
use minio::s3::response::BucketExistsResponse;

#[tokio::main]
async fn main() {
    let client: Client = Default::default(); // configure your client

    let exists: BucketExistsResponse = client
        .bucket_exists("my-bucket")
        .send()
        .await
        .expect("request failed");

    println!("Bucket exists: {}", exists.exists);
}

```

### 功能特性 {#id2}

- 采用请求构建器模式，提升 API 使用体验
- 通过 \[`tokio`\] 完整支持 async/await
- 强类型响应
- 通过 `Result<T, Error>` 提供透明的错误处理

### 设计 {#id3}

- \[`Client`\] 上的每个 API 方法都会返回一个 builder 结构体
- builder 实现 \[`ToS3Request`\] 用于请求转换，并实现 \[`S3Api`\] 用于执行请求
- 响应实现 \[`FromS3Response`\]，以实现一致的反序列化

### 示例 {#id4}

你可以通过以下命令在命令行运行示例：

`cargo run --example <example_name>`

下面的示例覆盖了几个常见操作。 你可以在 `examples` 目录中找到完整示例列表。

#### file_uploader.rs {#file-uploader-rs}

- [上传文件到 MinIO](#file-uploader-rs)
- [使用 CLI 上传文件到 MinIO](#file-uploader-rs)

#### file_downloader.rs {#file-downloader-rs}

- [从 MinIO 下载文件](#file-downloader-rs)

#### object_prompt.rs {#object-prompt-rs}

- [在 MinIO 上提示一个文件](#object-prompt-rs)

### 许可证 {#id5}

该 SDK 基于 [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0) 发布，更多信息请参见 [LICENSE](https://github.com/minio/minio-rs/blob/master/LICENSE)。
