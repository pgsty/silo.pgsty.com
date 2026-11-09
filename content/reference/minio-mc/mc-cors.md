---
title: "mc cors"
url: "/reference/minio-mc/mc-cors/"
weight: 55
---

<a id="command-mc.cors"></a>

`mc cors` manages per-bucket Cross-Origin Resource Sharing (CORS) in SILO. Per-bucket CORS is available from SILO 20260903; the presence of the client command does not imply that an older server implements bucket rules.

## Commands and permissions {#syntax}

```shell
mcli cors set ALIAS/BUCKET cors.xml
mcli cors set ALIAS/BUCKET - < cors.xml
mcli cors get ALIAS/BUCKET
mcli cors remove ALIAS/BUCKET
```

`set` reads XML from a file or standard input (`-`) and replaces the bucket's complete CORS document. `get` displays the current configuration; `remove` deletes it.
All three subcommands support [global flags](/reference/minio-mc/#minio-mc-global-options) and have no additional command-specific flags.

| Command | Required SILO policy action |
| --- | --- |
| `mc cors set` | `s3:PutBucketCors` |
| `mc cors get` | `s3:GetBucketCors` |
| `mc cors remove` | `s3:DeleteBucketCors` |
{.wide .expand}

Grant these actions on a bucket resource, such as `arn:aws:s3:::mybucket`.

## Example configuration {#example}

This configuration lets browsers at `https://app.example.com` read objects and access the response's `ETag` header:

```xml
<CORSConfiguration xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
  <CORSRule>
    <AllowedOrigin>https://app.example.com</AllowedOrigin>
    <AllowedMethod>GET</AllowedMethod>
    <AllowedMethod>HEAD</AllowedMethod>
    <AllowedHeader>*</AllowedHeader>
    <ExposeHeader>ETag</ExposeHeader>
    <MaxAgeSeconds>3600</MaxAgeSeconds>
  </CORSRule>
</CORSConfiguration>
```

The document is limited to 64 KiB and must contain 1 to 100 rules, each with at least one `AllowedOrigin` and `AllowedMethod`.
Allowed methods are `GET`, `PUT`, `HEAD`, `POST`, and `DELETE`; do not list the preflight method `OPTIONS`.
Each `AllowedOrigin` and `AllowedHeader` value may contain at most one `*`, and must not use the `?` wildcard.

## Behavior {#behavior}

When a bucket has a CORS configuration, only its rules apply: a nonmatching rule does not fall back to a broader global policy. After removal, a loaded bucket with no CORS document uses the global `MINIO_API_CORS_ALLOW_ORIGIN` / `api cors_allow_origin` setting. Removing the document therefore does not deny all cross-origin requests.

Buckets not yet loaded during startup, buckets whose metadata failed to load, and invalid bucket configurations do not fall back to the global policy to relax access. CORS preflight and response headers do not grant S3 permissions; an actual object request still needs an anonymous policy, valid credentials, or a presigned URL.

Per-bucket CORS is synchronized by site replication and preserved by [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/) and [`import`](/reference/minio-mc-admin/mc-admin-cluster-bucket-import/). See the [CORS and replication trust boundary](/blog/design/cors-replication-trust/#cors-state-machine) for implementation details.
