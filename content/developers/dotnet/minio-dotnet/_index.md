---
title: ".NET Quickstart Guide"
url: "/developers/dotnet/minio-dotnet/"
weight: 30
icon: fa-brands fa-microsoft
minio_origin: true
silo_modified: true
---

<a id="net-quickstart-guide"></a>
<a id="minio-dotnet-quickstart"></a>

## 适用于 .NET 的 MinIO Client SDK {#net-minio-client-sdk}

MinIO Client SDK 为 MinIO 和兼容 Amazon S3 的对象存储服务提供高级 API。有关完整 API 列表和示例，请参阅 [Dotnet Client API Reference](https://github.com/minio/minio-dotnet/blob/master/README.md)。本文档假设你已具备可用的 Visual Studio 开发环境。

[![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) [![Github Actions](https://github.com/minio/minio-dotnet/actions/workflows/minio-dotnet.yml/badge.svg)](https://github.com/minio/minio-dotnet/actions) [![Nuget](https://img.shields.io/nuget/dt/Minio?logo=nuget&label=nuget&link=https%3A%2F%2Fwww.nuget.org%2Fpackages%2FMinio)](https://www.nuget.org/packages/Minio/) [![GitHub tag (with filter)](https://img.shields.io/github/v/tag/minio/minio-dotnet?label=latest%20release)](https://github.com/minio/minio-dotnet/releases)

### 从 NuGet 安装 {#nuget}

要安装 [MinIO .NET package](https://www.nuget.org/packages/Minio/)，请在 NuGet Package Manager Console 中运行以下命令。

```powershell
PM> Install-Package Minio

```

### ASP.NET 的 MinIO Client 示例 {#asp-net-minio-client}

使用 `AddMinio` 将 Minio 添加到 `ServiceCollection` 时，Minio 还会使用你已添加的任何自定义 Logging provider（例如 Serilog），并在启用时输出跟踪信息。

```cs
using Minio;
using Minio.DataModel.Args;

public static class Program
{
    var endpoint = "play.min.io";
    var accessKey = "minioadmin";
    var secretKey = "minioadmin";

    public static void Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder();

        // Add Minio using the default endpoint
        builder.Services.AddMinio(accessKey, secretKey);

        // Add Minio using the custom endpoint and configure additional settings for default MinioClient initialization
        builder.Services.AddMinio(configureClient => configureClient
            .WithEndpoint(endpoint)
            .WithCredentials(accessKey, secretKey)
            .Build());

        // NOTE: SSL and Build are called by the build-in services already.

        var app = builder.Build();
        app.Run();
    }
}

[ApiController]
public class ExampleController : ControllerBase
{
    private readonly IMinioClient minioClient;

    public ExampleController(IMinioClient minioClient)
    {
        this.minioClient = minioClient;
    }

    [HttpGet]
    [ProducesResponseType(typeof(string), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetUrl(string bucketID)
    {
        return Ok(await minioClient.PresignedGetObjectAsync(new PresignedGetObjectArgs()
                .WithBucket(bucketID))
            .ConfigureAwait(false));
    }
}

[ApiController]
public class ExampleFactoryController : ControllerBase
{
    private readonly IMinioClientFactory minioClientFactory;

    public ExampleFactoryController(IMinioClientFactory minioClientFactory)
    {
        this.minioClientFactory = minioClientFactory;
    }

    [HttpGet]
    [ProducesResponseType(typeof(string), StatusCodes.Status200OK)]
    public async Task<IActionResult> GetUrl(string bucketID)
    {
        var minioClient = minioClientFactory.CreateClient(); //Has optional argument to configure specifics

        return Ok(await minioClient.PresignedGetObjectAsync(new PresignedGetObjectArgs()
                .WithBucket(bucketID))
            .ConfigureAwait(false));
    }
}


```

### MinIO Client 示例 {#minio-client}

要连接到兼容 Amazon S3 的对象存储服务，你需要以下信息：

| 变量名 | 说明 |
| --- | --- |
| endpoint | 对象存储的 &lt;Domain-name&gt; 或 &lt;ip:port&gt; |
| accessKey | 用于唯一标识账户的用户 ID |
| secretKey | 账户密码 |
| secure | 用于启用/禁用 HTTPS 支持的布尔值（默认值为 `true`） |

以下示例使用免费托管的公共 MinIO 服务 “play.min.io” 进行开发。

```cs
using Minio;

var endpoint = "play.min.io";
var accessKey = "minioadmin";
var secretKey = "minioadmin";
var secure = true;
// Initialize the client with access credentials.
private static IMinioClient minio = new MinioClient()
                                    .WithEndpoint(endpoint)
                                    .WithCredentials(accessKey, secretKey)
                                    .WithSSL(secure)
                                    .Build();

// Create an async task for listing buckets.
var getListBucketsTask = await minio.ListBucketsAsync().ConfigureAwait(false);

// Iterate over the list of buckets.
foreach (var bucket in getListBucketsTask.Result.Buckets)
{
    Console.WriteLine(bucket.Name + " " + bucket.CreationDateDateTime);
}


```

### 完整的 *File Uploader* 示例 {#file-uploader}

该示例程序连接到对象存储服务器，创建存储桶，并将文件上传到该存储桶。 要运行以下示例，请点击 \[Link\] 并启动该项目。

```cs
using System;
using Minio;
using Minio.Exceptions;
using Minio.DataModel;
using Minio.Credentials;
using Minio.DataModel.Args;
using System.Threading.Tasks;

namespace FileUploader
{
    class FileUpload
    {
        static void Main(string[] args)
        {
            var endpoint  = "play.min.io";
            var accessKey = "minioadmin";
            var secretKey = "minioadmin";
            try
            {
                var minio = new MinioClient()
                                    .WithEndpoint(endpoint)
                                    .WithCredentials(accessKey, secretKey)
                                    .WithSSL()
                                    .Build();
                FileUpload.Run(minio).Wait();
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }
            Console.ReadLine();
        }

        // File uploader task.
        private async static Task Run(IMinioClient minio)
        {
            var bucketName = "mymusic";
            var location   = "us-east-1";
            var objectName = "golden-oldies.zip";
            var filePath = "C:\\Users\\username\\Downloads\\golden_oldies.mp3";
            var contentType = "application/zip";

            try
            {
                // Make a bucket on the server, if not already present.
                var beArgs = new BucketExistsArgs()
                    .WithBucket(bucketName);
                bool found = await minio.BucketExistsAsync(beArgs).ConfigureAwait(false);
                if (!found)
                {
                    var mbArgs = new MakeBucketArgs()
                        .WithBucket(bucketName);
                    await minio.MakeBucketAsync(mbArgs).ConfigureAwait(false);
                }
                // Upload a file to bucket.
                var putObjectArgs = new PutObjectArgs()
                    .WithBucket(bucketName)
                    .WithObject(objectName)
                    .WithFileName(filePath)
                    .WithContentType(contentType);
                await minio.PutObjectAsync(putObjectArgs).ConfigureAwait(false);
                Console.WriteLine("Successfully uploaded " + objectName );
            }
            catch (MinioException e)
            {
                Console.WriteLine("File Upload Error: {0}", e.Message);
            }
        }
    }
}

```

### 运行 MinIO Client 示例 {#id1}

#### 在 Windows 上 {#windows}

- 克隆此仓库，并在 Visual Studio 2017 中打开 Minio.Sln。
- 在 Minio.Examples/Program.cs 中填写你的凭据、存储桶名称、对象名称等信息。
- 取消注释 Program.cs 中如下所示的示例测试用例以运行示例。

```cs
  //Cases.MakeBucket.Run(minioClient, bucketName).Wait();

```

- 在 Visual Studio 中运行 Minio.Client.Examples 项目。

#### 在 Linux 上 {#linux}

##### 在 Linux 上设置 .NET SDK（Ubuntu 22.04） {#linux-net-sdk-ubuntu-22-04}

<blockquote> 注意：minio-dotnet 在 Linux 上构建需要 .NET 6.x SDK。 </blockquote>

- 安装 [.NET SDK](https://docs.microsoft.com/en-us/dotnet/core/install/linux-ubuntu#2204)。

```
wget https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i packages-microsoft-prod.deb
rm packages-microsoft-prod.deb

```

```
sudo apt-get update; \
  sudo apt-get install -y apt-transport-https && \
  sudo apt-get update && \
  sudo apt-get install -y dotnet-sdk-6.0

```

##### 运行 Minio.Examples {#minio-examples}

- 克隆此项目。

```
$ git clone https://github.com/minio/minio-dotnet && cd minio-dotnet

```

- 在 Minio.Examples/Program.cs 中填写你的凭据、存储桶名称、对象名称等信息。 取消注释 Program.cs 中如下所示的示例测试用例以运行示例。

```cs
  //Cases.MakeBucket.Run(minioClient, bucketName).Wait();

```

```
dotnet build --configuration Release --no-restore
dotnet pack ./Minio/Minio.csproj --no-build --configuration Release --output ./artifacts
dotnet test ./Minio.Tests/Minio.Tests.csproj

```

##### 存储桶操作 {#id2}

- [MakeBucket.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/MakeBucket.cs)
- [ListBuckets.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/ListBuckets.cs)
- [BucketExists.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/BucketExists.cs)
- [RemoveBucket.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/RemoveBucket.cs)
- [ListObjects.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/ListObjects.cs)
- [ListIncompleteUploads.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/ListIncompleteUploads.cs)
- [ListenBucketNotifications.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/ListenBucketNotifications.cs)

##### 存储桶策略操作 {#id3}

- [GetBucketPolicy.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/GetBucketPolicy.cs)
- [SetBucketPolicy.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/SetBucketPolicy.cs)

##### 存储桶通知操作 {#id4}

- [GetBucketNotification.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/GetBucketNotification.cs)
- [SetBucketNotification.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/SetBucketNotification.cs)
- [RemoveAllBucketNotifications.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/RemoveAllBucketNotifications.cs)

##### 文件对象操作 {#id5}

- [FGetObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/FGetObject.cs)
- [FPutObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/FPutObject.cs)

##### 对象操作 {#id6}

- [GetObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/GetObject.cs)
- [GetPartialObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/GetPartialObject.cs)
- [SelectObjectContent.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/SelectObjectContent.cs)
- [PutObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/PutObject.cs)
- [StatObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/StatObject.cs)
- [RemoveObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/RemoveObject.cs)
- [RemoveObjects.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/RemoveObjects.cs)
- [CopyObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/CopyObject.cs)
- [CopyObjectMetadata.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/CopyObjectMetadata.cs)
- [RemoveIncompleteUpload.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/RemoveIncompleteUpload.cs)

##### 预签名操作 {#id7}

- [PresignedGetObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/PresignedGetObject.cs)
- [PresignedPutObject.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/PresignedPutObject.cs)
- [PresignedPostPolicy.cs](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Cases/PresignedPostPolicy.cs)

##### 客户端自定义设置 {#id8}

- [SetAppInfo](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Program.cs)
- [SetTraceOn](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Program.cs)
- [SetTraceOff](https://github.com/minio/minio-dotnet/blob/master/Minio.Examples/Program.cs)

### 进一步了解 {#id9}

- [.NET SDK 源码与当前文档](https://github.com/minio/minio-dotnet)
- [MinIO .NET SDK API 参考](https://github.com/minio/minio-dotnet/blob/master/README.md)
