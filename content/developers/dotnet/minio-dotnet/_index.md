---
title: ".NET Quickstart Guide"
description: "Connect a .NET application to SILO with the MinIO .NET SDK."
url: "/developers/dotnet/minio-dotnet/"
weight: 30
icon: fa-brands fa-microsoft
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/developers/dotnet/minio-dotnet.rst
upstream_modified: true
---

## MinIO SDK for .NET {#dotnet-sdk}

SILO implements the S3-compatible server contract, so applications can use the upstream [MinIO .NET SDK](https://github.com/minio/minio-dotnet) without a SILO-specific client fork. This guide uses the stable NuGet package and environment variables for credentials.

> [!NOTE]
> SDK release requirements and APIs can change independently of SILO. Check the [current NuGet package](https://www.nuget.org/packages/Minio/) and [SDK releases](https://github.com/minio/minio-dotnet/releases) before choosing a version for your application.

## Install the package {#install}

From an existing .NET project, add the `Minio` package:

```shell
dotnet add package Minio
```

## Configure the connection {#configure}

Set the endpoint and credentials for your SILO deployment. Keep secrets outside source control.

```shell
export S3_ENDPOINT=127.0.0.1:9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
export S3_USE_SSL=false
```

`S3_ENDPOINT` is a host and optional port, without an `http://` or `https://` prefix. Set `S3_USE_SSL=true` when the endpoint serves TLS.

## Create a bucket and upload an object {#upload}

```csharp
using Minio;
using Minio.DataModel.Args;

var endpoint = Environment.GetEnvironmentVariable("S3_ENDPOINT")
    ?? throw new InvalidOperationException("S3_ENDPOINT is required");
var accessKey = Environment.GetEnvironmentVariable("S3_ACCESS_KEY")
    ?? throw new InvalidOperationException("S3_ACCESS_KEY is required");
var secretKey = Environment.GetEnvironmentVariable("S3_SECRET_KEY")
    ?? throw new InvalidOperationException("S3_SECRET_KEY is required");
var useSsl = bool.TryParse(Environment.GetEnvironmentVariable("S3_USE_SSL"), out var ssl)
    && ssl;

var client = new MinioClient()
    .WithEndpoint(endpoint)
    .WithCredentials(accessKey, secretKey)
    .WithSSL(useSsl)
    .Build();

const string bucket = "dotnet-quickstart";
const string objectName = "hello.txt";
const string filePath = "hello.txt";

var exists = await client.BucketExistsAsync(
    new BucketExistsArgs().WithBucket(bucket));

if (!exists)
{
    await client.MakeBucketAsync(
        new MakeBucketArgs().WithBucket(bucket));
}

await client.PutObjectAsync(
    new PutObjectArgs()
        .WithBucket(bucket)
        .WithObject(objectName)
        .WithFileName(filePath)
        .WithContentType("text/plain"));

Console.WriteLine($"Uploaded {objectName} to {bucket}");
```

Create `hello.txt`, then run the project:

```shell
dotnet run
```

For ASP.NET Core dependency injection and additional operations, use the SDK's [current README](https://github.com/minio/minio-dotnet#readme). The maintained repository also contains [simple](https://github.com/minio/minio-dotnet/tree/master/Minio.Examples.Simple) and [host-based](https://github.com/minio/minio-dotnet/tree/master/Minio.Examples.Host) example projects; review their target branch and package version before copying code into a pinned application.

## Production checklist {#production}

- Use TLS and verify the server certificate.
- Load credentials from a secret manager or protected environment, not source code.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the SDK version as part of the application's dependency lifecycle.
- Handle SDK exceptions, request cancellation, retries, and multipart-upload cleanup explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.
