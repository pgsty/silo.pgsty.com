---
title: "Java Quickstart Guide"
url: "/developers/java/minio-java/"
weight: 40
icon: fa-brands fa-java
minio_origin: true
silo_modified: true
---

<a id="java-quickstart-guide"></a>
<a id="minio-java-quickstart"></a>

## 适用于 Amazon S3 兼容对象存储的 MinIO Java SDK [![Slack](https://slack.min.io/slack?type=svg)](https://slack.min.io) {#amazon-s3-minio-java-sdk}

MinIO Java SDK 是一个 Simple Storage Service（即 S3）客户端，可用于在任意兼容 Amazon S3 的对象存储服务上执行存储桶和对象操作。

有关完整的 API 和示例列表，请参阅 [Java Client API Reference](https://github.com/minio/minio-java/blob/master/docs/API.md) 文档。

### 最低要求 {#id1}

Java 1.8 或更高版本。

### Maven 用法 {#maven}

```xml
<dependency>
    <groupId>io.minio</groupId>
    <artifactId>minio</artifactId>
    <version>8.6.0</version>
</dependency>

```

### Gradle 用法 {#gradle}

```text
dependencies {
    implementation("io.minio:minio:8.6.0")
}

```

### JAR 下载 {#jar}

可从 [Maven Central](https://repo1.maven.org/maven2/io/minio/minio/8.6.0/) 下载 JAR。

### 快速开始示例 - 文件上传器 {#id2}

该示例程序会连接到对象存储服务器，在服务器上创建一个存储桶，然后将文件上传到该存储桶。

连接对象存储服务器需要以下三个参数。

| 参数 | 说明 |
| --- | --- |
| Endpoint | 指向 S3 服务的 URL。 |
| Access Key | S3 服务中某个账户的访问密钥（即用户 ID）。 |
| Secret Key | S3 服务中某个账户的 Secret Key（相当于密码）。 |

本示例使用 MinIO Server Playground [https://play.min.io](https://play.min.io)。可使用该服务进行测试和开发。

#### FileUploader.java {#fileuploader-java}

```java
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.UploadObjectArgs;
import io.minio.errors.MinioException;
import java.io.IOException;
import java.security.InvalidKeyException;
import java.security.NoSuchAlgorithmException;

public class FileUploader {
  public static void main(String[] args)
      throws IOException, NoSuchAlgorithmException, InvalidKeyException {
    try {
      // Create a minioClient with the MinIO server playground, its access key and secret key.
      MinioClient minioClient =
          MinioClient.builder()
              .endpoint("https://play.min.io")
              .credentials("Q3AM3UQ867SPQQA43P2F", "zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG")
              .build();

      // Make 'asiatrip' bucket if not exist.
      boolean found =
          minioClient.bucketExists(BucketExistsArgs.builder().bucket("asiatrip").build());
      if (!found) {
        // Make a new bucket called 'asiatrip'.
        minioClient.makeBucket(MakeBucketArgs.builder().bucket("asiatrip").build());
      } else {
        System.out.println("Bucket 'asiatrip' already exists.");
      }

      // Upload '/home/user/Photos/asiaphotos.zip' as object name 'asiaphotos-2015.zip' to bucket
      // 'asiatrip'.
      minioClient.uploadObject(
          UploadObjectArgs.builder()
              .bucket("asiatrip")
              .object("asiaphotos-2015.zip")
              .filename("/home/user/Photos/asiaphotos.zip")
              .build());
      System.out.println(
          "'/home/user/Photos/asiaphotos.zip' is successfully uploaded as "
              + "object 'asiaphotos-2015.zip' to bucket 'asiatrip'.");
    } catch (MinioException e) {
      System.out.println("Error occurred: " + e);
      System.out.println("HTTP trace: " + e.httpTrace());
    }
  }
}

```

##### 编译 FileUploader {#fileuploader}

```sh
$ javac -cp minio-8.6.0-all.jar FileUploader.java

```

##### 运行 FileUploader {#id3}

```sh
$ java -cp minio-8.6.0-all.jar:. FileUploader
'/home/user/Photos/asiaphotos.zip' is successfully uploaded as object 'asiaphotos-2015.zip' to bucket 'asiatrip'.

$ mc ls play/asiatrip/
[2016-06-02 18:10:29 PDT]  82KiB asiaphotos-2015.zip

```

### 更多参考 {#id4}

- [Java Client API Reference](https://github.com/minio/minio-java/blob/master/docs/API.md)
- [Javadoc](https://minio-java.min.io/)
- [示例](https://github.com/minio/minio-java/tree/release/examples)

### 深入了解 {#id5}

- [Java SDK 源码与当前文档](https://github.com/minio/minio-java)
- [构建自己的 Photo API 服务 - 完整应用示例](https://github.com/minio/minio-java-rest-example)

### 贡献 {#id6}

请参阅 [贡献指南](https://github.com/minio/minio-java/blob/release/CONTRIBUTING.md)。
