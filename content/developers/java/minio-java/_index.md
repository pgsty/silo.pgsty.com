---
title: "Java Quickstart Guide"
description: "Connect a Java application to SILO with the MinIO Java SDK."
url: "/developers/java/minio-java/"
weight: 40
icon: fa-brands fa-java
minio_origin: true
silo_modified: true
---

## MinIO Java SDK {#java-sdk}

SILO implements the S3-compatible server contract, so Java applications can use the upstream [MinIO Java SDK](https://github.com/minio/minio-java) directly. The SDK supports Java 8 and later; select a runtime that is also supported by your application framework.

{{% alert color="info" %}}
This page was verified with SDK `9.0.3`. Check the [current releases](https://github.com/minio/minio-java/releases) and [Maven Central metadata](https://central.sonatype.com/artifact/io.minio/minio) before pinning a version.
{{% /alert %}}

## Install the package {#install}

Add the dependency to Maven:

```xml
<dependency>
  <groupId>io.minio</groupId>
  <artifactId>minio</artifactId>
  <version>9.0.3</version>
</dependency>
```

Or to Gradle:

```kotlin
implementation("io.minio:minio:9.0.3")
```

## Configure the connection {#configure}

```shell
export S3_ENDPOINT=http://127.0.0.1:9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
```

Unlike some other MinIO SDKs, the Java builder accepts a complete endpoint URL, including the `http://` or `https://` scheme. Keep credentials outside source control.

## Create a bucket and upload an object {#upload}

```java
import io.minio.BucketExistsArgs;
import io.minio.MakeBucketArgs;
import io.minio.MinioClient;
import io.minio.PutObjectArgs;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

public final class Quickstart {
  private static String required(String name) {
    String value = System.getenv(name);
    if (value == null || value.isBlank()) {
      throw new IllegalStateException(name + " is required");
    }
    return value;
  }

  public static void main(String[] args) throws Exception {
    MinioClient client =
        MinioClient.builder()
            .endpoint(required("S3_ENDPOINT"))
            .credentials(required("S3_ACCESS_KEY"), required("S3_SECRET_KEY"))
            .build();

    String bucket = "java-quickstart";
    String object = "hello.txt";
    byte[] payload = "hello from SILO\n".getBytes(StandardCharsets.UTF_8);

    boolean exists =
        client.bucketExists(BucketExistsArgs.builder().bucket(bucket).build());
    if (!exists) {
      client.makeBucket(MakeBucketArgs.builder().bucket(bucket).build());
    }

    try (ByteArrayInputStream stream = new ByteArrayInputStream(payload)) {
      client.putObject(
          PutObjectArgs.builder()
              .bucket(bucket)
              .object(object)
              .stream(stream, payload.length, -1)
              .contentType("text/plain")
              .build());
    }

    System.out.printf("Uploaded %s: %d bytes%n", object, payload.length);
  }
}
```

Use the SDK's [Javadoc](https://javadoc.io/doc/io.minio/minio/latest/index.html) and [maintained examples](https://github.com/minio/minio-java/tree/master/examples) for presigned URLs, encryption, notifications, object locking, multipart operations, and other APIs.

## Production checklist {#production}

- Use TLS and verify the server certificate and trust store.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the JDK, SDK, HTTP client, and framework versions together.
- Configure timeouts and handle SDK exceptions, retries, streams, and incomplete multipart uploads explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.
