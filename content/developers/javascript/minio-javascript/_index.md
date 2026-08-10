---
title: "JavaScript Quickstart Guide"
description: "Connect a Node.js application to SILO with the MinIO JavaScript SDK."
url: "/developers/javascript/minio-javascript/"
weight: 50
icon: fa-brands fa-js
minio_origin: true
silo_modified: true
---

## MinIO JavaScript SDK {#javascript-sdk}

SILO implements the S3-compatible server contract, so Node.js applications can use the upstream [MinIO JavaScript SDK](https://github.com/minio/minio-js) directly. Use a maintained Node.js release supported by the package version you select.

## Install the package {#install}

```shell
npm install minio
```

The package includes TypeScript declarations; do not install the old `@types/minio` package.

## Configure the connection {#configure}

```shell
export S3_ENDPOINT=127.0.0.1
export S3_PORT=9000
export S3_ACCESS_KEY=silo-admin
export S3_SECRET_KEY=replace-with-a-strong-secret
export S3_USE_SSL=false
```

Keep credentials outside source control. Set `S3_USE_SSL=true` and use the TLS service port when connecting to a secured deployment.

## Create a bucket and upload an object {#upload}

Save the following as `quickstart.mjs`:

```js
import * as Minio from 'minio'

const required = (name) => {
  const value = process.env[name]
  if (!value) throw new Error(`${name} is required`)
  return value
}

const client = new Minio.Client({
  endPoint: required('S3_ENDPOINT'),
  port: Number(process.env.S3_PORT || 9000),
  useSSL: process.env.S3_USE_SSL === 'true',
  accessKey: required('S3_ACCESS_KEY'),
  secretKey: required('S3_SECRET_KEY'),
})

const bucket = 'javascript-quickstart'
const objectName = 'hello.txt'

if (!(await client.bucketExists(bucket))) {
  await client.makeBucket(bucket, 'us-east-1')
}

await client.putObject(
  bucket,
  objectName,
  Buffer.from('hello from SILO\n'),
  { 'Content-Type': 'text/plain' },
)

const stat = await client.statObject(bucket, objectName)
console.log(`Uploaded ${objectName}: ${stat.size} bytes`)
```

Run it with:

```shell
node quickstart.mjs
```

Use the repository's [API reference](https://github.com/minio/minio-js/blob/master/docs/API.md) and [maintained examples](https://github.com/minio/minio-js/tree/master/examples) for bucket policy, notifications, object lock, presigned URLs, multipart operations, and other APIs. Prefer directory-level links over copying assumptions about individual example filenames into long-lived documentation.

## Production checklist {#production}

- Use TLS and verify the server certificate.
- Load credentials from a secret manager or protected environment.
- Grant the application only the bucket and object permissions it needs.
- Pin and test the SDK version, Node.js runtime, timeout behavior, and retry policy together.
- Handle streams, request errors, incomplete multipart uploads, and shutdown explicitly.

See [Identity and Access Management](/administration/identity-access-management/) for server-side policy configuration.
