---
title: "Go Quickstart Guide"
url: "/developers/go/minio-go/"
weight: 10
icon: fa-brands fa-golang
minio_origin: true
silo_modified: true
---

<a id="go-quickstart-guide"></a>
<a id="minio-go-quickstart"></a>

## 面向兼容 Amazon S3 的云对象存储的 MinIO Go Client SDK [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) [![Sourcegraph](https://sourcegraph.com/github.com/minio/minio-go/-/badge.svg)](https://sourcegraph.com/github.com/minio/minio-go?badge) [![Apache V2 License](https://img.shields.io/badge/license-Apache%20V2-blue.svg)](https://github.com/minio/minio-go/blob/master/LICENSE) {#amazon-s3-minio-go-client-sdk}

MinIO Go Client SDK 提供简洁直观的 API，用于访问任何兼容 Amazon S3 的对象存储。

本快速入门指南介绍如何安装 MinIO Client SDK、连接 MinIO，并创建一个示例文件上传器。完整 API 列表和示例请参见 [godoc 文档](https://pkg.go.dev/github.com/minio/minio-go/v7) 或 [Go Client API 参考](https://pkg.go.dev/github.com/minio/minio-go/v7)。

这些示例假定你已具备可用的 [Go 开发环境](https://go.dev/doc/install) 和 [Silo `mc`/`mcli` 命令行工具](/reference/minio-mc/#command-mc)。

### 从 GitHub 下载 {#github}

在你的项目目录中执行：

```sh
go get github.com/minio/minio-go/v7

```

### 初始化 MinIO Client 对象 {#minio-client}

MinIO Client 连接兼容 Amazon S3 的对象存储时需要以下参数：

| 参数 | 说明 |
| --- | --- |
| `endpoint` | 对象存储服务 URL。 |
| `_minio.Options_` | 所有选项，例如凭证、自定义传输等。 |

```go
package main

import (
        "log"

        "github.com/minio/minio-go/v7"
        "github.com/minio/minio-go/v7/pkg/credentials"
)

func main() {
        endpoint := "play.min.io"
        accessKeyID := "Q3AM3UQ867SPQQA43P2F"
        secretAccessKey := "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
        useSSL := true

        // Initialize minio client object.
        minioClient, err := minio.New(endpoint, &minio.Options{
                Creds:  credentials.NewStaticV4(accessKeyID, secretAccessKey, ""),
                Secure: useSSL,
        })
        if err != nil {
                log.Fatalln(err)
        }

        log.Printf("%#v\n", minioClient) // minioClient is now set up
}

```

### 示例：文件上传器 {#id1}

此示例代码会连接到对象存储服务器、创建存储桶，并将文件上传到该存储桶。它使用 MinIO `play` 服务器，即位于 [https://play.min.io](https://play.min.io) 的公共 MinIO 集群。

`play` 服务器运行 MinIO 最新稳定版本，可用于测试和开发。此示例中展示的访问凭证对公众开放，上传到 `play` 的所有数据都应视为公开且不受保护。

#### FileUploader.go {#fileuploader-go}

此示例将执行以下操作：

- ```text
    使用提供的凭证连接到 MinIO `play` 服务器。

  ```
- ```text
    创建一个名为 `testbucket` 的存储桶。

  ```
- ```text
    从 `/tmp` 上传名为 `testdata` 的文件。

  ```
- ````text
    使用 `mc ls` 验证文件已创建。

    ```go
    // FileUploader.go MinIO example
    package main

    import (
            "context"
            "log"

            "github.com/minio/minio-go/v7"
            "github.com/minio/minio-go/v7/pkg/credentials"
    )

    func main() {
            ctx := context.Background()
            endpoint := "play.min.io"
            accessKeyID := "Q3AM3UQ867SPQQA43P2F"
            secretAccessKey := "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG"
            useSSL := true

            // Initialize minio client object.
            minioClient, err := minio.New(endpoint, &minio.Options{
                    Creds:  credentials.NewStaticV4(accessKeyID, secretAccessKey, ""),
                    Secure: useSSL,
            })
            if err != nil {
                    log.Fatalln(err)
            }

            // Make a new bucket called testbucket.
            bucketName := "testbucket"
            location := "us-east-1"

            err = minioClient.MakeBucket(ctx, bucketName, minio.MakeBucketOptions{Region: location})
            if err != nil {
                    // Check to see if we already own this bucket (which happens if you run this twice)
                    exists, errBucketExists := minioClient.BucketExists(ctx, bucketName)
                    if errBucketExists == nil && exists {
                            log.Printf("We already own %s\n", bucketName)
                    } else {
                            log.Fatalln(err)
                    }
            } else {
                    log.Printf("Successfully created %s\n", bucketName)
            }

            // Upload the test file
            // Change the value of filePath if the file is in another location
            objectName := "testdata"
            filePath := "/tmp/testdata"
            contentType := "application/octet-stream"

            // Upload the test file with FPutObject
            info, err := minioClient.FPutObject(ctx, bucketName, objectName, filePath, minio.PutObjectOptions{ContentType: contentType})
            if err != nil {
                    log.Fatalln(err)
            }

            log.Printf("Successfully uploaded %s of size %d\n", objectName, info.Size)
    }
    ```

  ````

**1. 创建一个包含数据的测试文件：**

在 Linux 或 macOS 系统上，你可以使用 `dd`：

```sh
dd if=/dev/urandom of=/tmp/testdata bs=2048 count=10

```

或者在 Windows 上使用 `fsutil`：

```sh
fsutil file createnew "C:\Users\<username>\Desktop\sample.txt" 20480

```

**2. 使用以下命令运行 FileUploader：**

```sh
go mod init example/FileUploader
go get github.com/minio/minio-go/v7
go get github.com/minio/minio-go/v7/pkg/credentials
go run FileUploader.go

```

输出如下所示：

```sh
2023/11/01 14:27:55 Successfully created testbucket
2023/11/01 14:27:55 Successfully uploaded testdata of size 20480

```

**3. 使用 `mc ls` 验证已上传的文件：**

```sh
mc ls play/testbucket
[2023-11-01 14:27:55 UTC]  20KiB STANDARD testdata

```

### API 参考 {#api}

完整 API 参考可在此处查看。

- ```text
    [完整 API 参考](https://pkg.go.dev/github.com/minio/minio-go/v7)

  ```

#### API 参考：存储桶操作 {#id2}

- ```text
    [`MakeBucket`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.MakeBucket)

  ```
- ```text
    [`ListBuckets`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListBuckets)

  ```
- ```text
    [`BucketExists`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.BucketExists)

  ```
- ```text
    [`RemoveBucket`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.RemoveBucket)

  ```
- ```text
    [`ListObjects`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListObjects)

  ```
- ```text
    [`ListIncompleteUploads`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListIncompleteUploads)

  ```

#### API 参考：存储桶策略操作 {#id3}

- ```text
    [`SetBucketPolicy`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.SetBucketPolicy)

  ```
- ```text
    [`GetBucketPolicy`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.GetBucketPolicy)

  ```

#### API 参考：存储桶通知操作 {#id4}

- ```text
    [`SetBucketNotification`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.SetBucketNotification)

  ```
- ```text
    [`GetBucketNotification`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.GetBucketNotification)

  ```
- ```text
    [`RemoveAllBucketNotification`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.RemoveAllBucketNotification)

  ```
- ```text
    [`ListenBucketNotification`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListenBucketNotification) (MinIO 扩展)

  ```
- ```text
    [`ListenNotification`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListenNotification) (MinIO 扩展)

  ```

#### API 参考：文件对象操作 {#id5}

- ```text
    [`FPutObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.FPutObject)

  ```
- ```text
    [`FGetObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.FGetObject)

  ```

#### API 参考：对象操作 {#id6}

- ```text
    [`GetObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.GetObject)

  ```
- ```text
    [`PutObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PutObject)

  ```
- ```text
    [`StatObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.StatObject)

  ```
- ```text
    [`CopyObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.CopyObject)

  ```
- ```text
    [`RemoveObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.RemoveObject)

  ```
- ```text
    [`RemoveObjects`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.RemoveObjects)

  ```
- ```text
    [`RemoveIncompleteUpload`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.RemoveIncompleteUpload)

  ```
- ```text
    [`SelectObjectContent`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.SelectObjectContent)

  ```

#### API 参考：预签名操作 {#id7}

- ```text
    [`PresignedGetObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedGetObject)

  ```
- ```text
    [`PresignedPutObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedPutObject)

  ```
- ```text
    [`PresignedHeadObject`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedHeadObject)

  ```
- ```text
    [`PresignedPostPolicy`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.PresignedPostPolicy)

  ```

#### API 参考：客户端自定义设置 {#id8}

- ```text
    [`SetAppInfo`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.SetAppInfo)

  ```
- ```text
    [`TraceOn`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.TraceOn)

  ```
- ```text
    [`TraceOff`](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.TraceOff)

  ```

### 完整示例 {#id9}

#### 完整示例：存储桶操作 {#id10}

- ```text
    [makebucket.go](https://github.com/minio/minio-go/blob/master/examples/s3/makebucket.go)

  ```
- ```text
    [listbuckets.go](https://github.com/minio/minio-go/blob/master/examples/s3/listbuckets.go)

  ```
- ```text
    [bucketexists.go](https://github.com/minio/minio-go/blob/master/examples/s3/bucketexists.go)

  ```
- ```text
    [removebucket.go](https://github.com/minio/minio-go/blob/master/examples/s3/removebucket.go)

  ```
- ```text
    [listobjects.go](https://github.com/minio/minio-go/blob/master/examples/s3/listobjects.go)

  ```
- ```text
    [listobjectsV2.go](https://github.com/minio/minio-go/blob/master/examples/s3/listobjectsV2.go)

  ```
- ```text
    [listincompleteuploads.go](https://github.com/minio/minio-go/blob/master/examples/s3/listincompleteuploads.go)

  ```

#### 完整示例：存储桶策略操作 {#id11}

- ```text
    [setbucketpolicy.go](https://github.com/minio/minio-go/blob/master/examples/s3/setbucketpolicy.go)

  ```
- ```text
    [getbucketpolicy.go](https://github.com/minio/minio-go/blob/master/examples/s3/getbucketpolicy.go)

  ```
- ```text
    [listbucketpolicies.go](https://github.com/minio/minio-go/blob/master/examples/s3/listbucketpolicies.go)

  ```

#### 完整示例：存储桶生命周期管理操作 {#id12}

- ```text
    [setbucketlifecycle.go](https://github.com/minio/minio-go/blob/master/examples/s3/setbucketlifecycle.go)

  ```
- ```text
    [getbucketlifecycle.go](https://github.com/minio/minio-go/blob/master/examples/s3/getbucketlifecycle.go)

  ```

#### 完整示例：存储桶加密操作 {#id13}

- ```text
    [setbucketencryption.go](https://github.com/minio/minio-go/blob/master/examples/s3/setbucketencryption.go)

  ```
- ```text
    [getbucketencryption.go](https://github.com/minio/minio-go/blob/master/examples/s3/getbucketencryption.go)

  ```
- ```text
    [removebucketencryption.go](https://github.com/minio/minio-go/blob/master/examples/s3/removebucketencryption.go)

  ```

#### 完整示例：存储桶复制操作 {#id14}

- ```text
    [setbucketreplication.go](https://github.com/minio/minio-go/blob/master/examples/s3/setbucketreplication.go)

  ```
- ```text
    [getbucketreplication.go](https://github.com/minio/minio-go/blob/master/examples/s3/getbucketreplication.go)

  ```
- ```text
    [removebucketreplication.go](https://github.com/minio/minio-go/blob/master/examples/s3/removebucketreplication.go)

  ```

#### 完整示例：存储桶通知操作 {#id15}

- ```text
    [setbucketnotification.go](https://github.com/minio/minio-go/blob/master/examples/s3/setbucketnotification.go)

  ```
- ```text
    [getbucketnotification.go](https://github.com/minio/minio-go/blob/master/examples/s3/getbucketnotification.go)

  ```
- ```text
    [removeallbucketnotification.go](https://github.com/minio/minio-go/blob/master/examples/s3/removeallbucketnotification.go)

  ```
- ```text
    [listenbucketnotification.go](https://github.com/minio/minio-go/blob/master/examples/minio/listenbucketnotification.go) (MinIO 扩展)

  ```
- ```text
    [listennotification.go](https://github.com/minio/minio-go/blob/master/examples/minio/listen-notification.go) (MinIO 扩展)

  ```

#### 完整示例：文件对象操作 {#id16}

- ```text
    [fputobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/fputobject.go)

  ```
- ```text
    [fgetobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/fgetobject.go)

  ```

#### 完整示例：对象操作 {#id17}

- ```text
    [putobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/putobject.go)

  ```
- ```text
    [getobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/getobject.go)

  ```
- ```text
    [statobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/statobject.go)

  ```
- ```text
    [copyobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/copyobject.go)

  ```
- ```text
    [removeobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/removeobject.go)

  ```
- ```text
    [removeincompleteupload.go](https://github.com/minio/minio-go/blob/master/examples/s3/removeincompleteupload.go)

  ```
- ```text
    [removeobjects.go](https://github.com/minio/minio-go/blob/master/examples/s3/removeobjects.go)

  ```

#### 完整示例：加密对象操作 {#id18}

- ```text
    [put-encrypted-object.go](https://github.com/minio/minio-go/blob/master/examples/s3/put-encrypted-object.go)

  ```
- ```text
    [get-encrypted-object.go](https://github.com/minio/minio-go/blob/master/examples/s3/get-encrypted-object.go)

  ```
- ```text
    [fput-encrypted-object.go](https://github.com/minio/minio-go/blob/master/examples/s3/fputencrypted-object.go)

  ```

#### 完整示例：预签名操作 {#id19}

- ```text
    [presignedgetobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/presignedgetobject.go)

  ```
- ```text
    [presignedputobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/presignedputobject.go)

  ```
- ```text
    [presignedheadobject.go](https://github.com/minio/minio-go/blob/master/examples/s3/presignedheadobject.go)

  ```
- ```text
    [presignedpostpolicy.go](https://github.com/minio/minio-go/blob/master/examples/s3/presignedpostpolicy.go)

  ```

### 进一步探索 {#id20}

- ```text
    [Godoc 文档](https://pkg.go.dev/github.com/minio/minio-go/v7)

  ```
- ```text
    [Go SDK 源码与当前文档](https://github.com/minio/minio-go)

  ```
- ```text
    [MinIO Go Client SDK API 参考](https://pkg.go.dev/github.com/minio/minio-go/v7)

  ```

### 贡献 {#id21}

[贡献者指南](https://github.com/minio/minio-go/blob/master/CONTRIBUTING.md)

### 许可证 {#id22}

此 SDK 在 [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0) 下分发，更多信息请参见 [LICENSE](https://github.com/minio/minio-go/blob/master/LICENSE) 和 [NOTICE](https://github.com/minio/minio-go/blob/master/NOTICE)。
