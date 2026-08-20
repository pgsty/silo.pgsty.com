---
title: "Rust Quickstart Guide"
description: "Connect a Rust application to SILO with the MinIO Rust SDK."
url: "/developers/rust/minio-rust/"
aliases:
  - "/developers/rust/quickstart/"
  - "/developers/rust/API/"
weight: 70
icon: fa-brands fa-rust
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/rust/minio-rust.rst
upstream_modified: true
---

## MinIO Rust SDK {#rust-sdk}

SILO implements the S3-compatible server contract, so Rust applications can use the upstream [MinIO Rust SDK](https://github.com/minio/minio-rs) directly. The crate provides an asynchronous, strongly typed request-builder API.

> [!NOTE]
> This page was verified with the `minio` crate `0.4.0`. The crate does not currently declare a minimum supported Rust version, so check the [current package metadata](https://crates.io/crates/minio) and [API documentation](https://docs.rs/minio/latest/minio/) and test it with your pinned toolchain.

## Install the package {#install}

Add the SDK and Tokio runtime to `Cargo.toml`:

```toml
[dependencies]
minio = "0.4.0"
tokio = { version = "1", features = ["macros", "rt-multi-thread"] }
```

## Configure the connection {#configure}

```shell
export S3_ENDPOINT=http://127.0.0.1:9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
```

`S3_ENDPOINT` is a complete URL, including the `http://` or `https://` scheme. Keep credentials outside source control.

## Create a bucket and upload an object {#upload}

```rust
use minio::s3::builders::ObjectContent;
use minio::s3::creds::StaticProvider;
use minio::s3::http::BaseUrl;
use minio::s3::response::BucketExistsResponse;
use minio::s3::types::{BucketName, ObjectKey, S3Api};
use minio::s3::{MinioClient, MinioClientBuilder};
use std::env;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let endpoint = env::var("S3_ENDPOINT")?;
    let access_key = env::var("S3_ACCESS_KEY")?;
    let secret_key = env::var("S3_SECRET_KEY")?;

    let base_url = endpoint.parse::<BaseUrl>()?;
    let provider = StaticProvider::new(&access_key, &secret_key, None);
    let client: MinioClient = MinioClientBuilder::new(base_url)
        .provider(Some(provider))
        .build()?;

    let bucket = BucketName::new("rust-quickstart")?;
    let object = ObjectKey::new("hello.txt")?;

    let exists: BucketExistsResponse = client
        .bucket_exists(bucket.clone())?
        .build()
        .send()
        .await?;

    if !exists.exists() {
        client
            .create_bucket(bucket.clone())?
            .build()
            .send()
            .await?;
    }

    client
        .put_object_content(
            bucket,
            object,
            ObjectContent::from("hello from SILO\n"),
        )?
        .build()
        .send()
        .await?;

    println!("Uploaded hello.txt");
    Ok(())
}
```

Run it with `cargo run`. The repository's [maintained examples](https://github.com/minio/minio-rs/tree/master/examples) and [API documentation](https://docs.rs/minio/latest/minio/) cover file uploads, streaming, encryption, notifications, object locking, and other operations.

## Production checklist {#production}

- Use TLS and verify the server certificate.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the Rust toolchain, SDK, Tokio, HTTP, TLS, and crypto features together.
- Define timeouts and handle errors, retries, task cancellation, and incomplete multipart uploads explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.
