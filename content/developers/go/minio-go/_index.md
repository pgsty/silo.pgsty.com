---
title: "Go Quickstart Guide"
description: "Connect a Go application to SILO with the MinIO Go SDK."
url: "/developers/go/minio-go/"
weight: 10
icon: fa-brands fa-golang
minio_origin: true
silo_modified: true
---

## MinIO Go SDK {#go-sdk}

SILO implements the S3-compatible server contract, so Go applications can use the upstream [MinIO Go SDK](https://github.com/minio/minio-go) directly. The current major module path is `github.com/minio/minio-go/v7`.

{{% alert color="info" %}}
SDK releases and Go requirements evolve independently of SILO. Check the [current releases](https://github.com/minio/minio-go/releases) and [package documentation](https://pkg.go.dev/github.com/minio/minio-go/v7) before pinning a version.
{{% /alert %}}

## Install the module {#install}

From an existing Go module:

```shell
go get github.com/minio/minio-go/v7
```

## Configure the connection {#configure}

```shell
export S3_ENDPOINT=127.0.0.1:9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
export S3_USE_SSL=false
```

`S3_ENDPOINT` is a host and optional port, without an `http://` or `https://` prefix. Keep credentials outside source control and set `S3_USE_SSL=true` when the endpoint serves TLS.

## Create a bucket and upload an object {#upload}

Save the following as `main.go`:

```go
package main

import (
	"bytes"
	"context"
	"fmt"
	"log"
	"os"

	"github.com/minio/minio-go/v7"
	"github.com/minio/minio-go/v7/pkg/credentials"
)

func required(name string) string {
	value := os.Getenv(name)
	if value == "" {
		log.Fatalf("%s is required", name)
	}
	return value
}

func main() {
	ctx := context.Background()
	client, err := minio.New(required("S3_ENDPOINT"), &minio.Options{
		Creds: credentials.NewStaticV4(
			required("S3_ACCESS_KEY"),
			required("S3_SECRET_KEY"),
			"",
		),
		Secure: os.Getenv("S3_USE_SSL") == "true",
	})
	if err != nil {
		log.Fatal(err)
	}

	const bucket = "go-quickstart"
	const object = "hello.txt"

	exists, err := client.BucketExists(ctx, bucket)
	if err != nil {
		log.Fatal(err)
	}
	if !exists {
		if err = client.MakeBucket(ctx, bucket, minio.MakeBucketOptions{
			Region: "us-east-1",
		}); err != nil {
			log.Fatal(err)
		}
	}

	payload := []byte("hello from SILO\n")
	info, err := client.PutObject(
		ctx,
		bucket,
		object,
		bytes.NewReader(payload),
		int64(len(payload)),
		minio.PutObjectOptions{ContentType: "text/plain"},
	)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf("Uploaded %s: %d bytes\n", info.Key, info.Size)
}
```

Run it with:

```shell
go run .
```

Use the SDK's [API documentation](https://pkg.go.dev/github.com/minio/minio-go/v7) and [maintained examples](https://github.com/minio/minio-go/tree/master/examples) for presigned URLs, object locking, encryption, notifications, multipart operations, and other APIs.

## Production checklist {#production}

- Use TLS and verify the server certificate.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the SDK and Go versions together.
- Apply request deadlines and handle retries, cancellation, and incomplete multipart uploads explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.
