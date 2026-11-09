---
title: "mc cors"
url: "/zh/reference/minio-mc/mc-cors/"
weight: 55
---

<a id="command-mc.cors"></a>

`mc cors` 管理 SILO 存储桶的跨域资源共享（CORS）配置。桶级 CORS 自 SILO 20260903 起可用；旧服务端即使接受客户端命令，也不代表实现了桶级规则。

## 命令与权限 {#syntax}

```shell
mcli cors set ALIAS/BUCKET cors.xml
mcli cors set ALIAS/BUCKET - < cors.xml
mcli cors get ALIAS/BUCKET
mcli cors remove ALIAS/BUCKET
```

`set` 从 XML 文件或标准输入 `-` 读取配置，并替换该桶的整份 CORS 文档。`get` 显示当前配置；`remove` 删除桶级配置。
这三个子命令均支持[全局参数](/zh/reference/minio-mc/#minio-mc-global-options)，没有额外的命令专用标志。

| 命令 | SILO 所需策略动作 |
| --- | --- |
| `mc cors set` | `s3:PutBucketCors` |
| `mc cors get` | `s3:GetBucketCors` |
| `mc cors remove` | `s3:DeleteBucketCors` |
{.wide .expand}

将这些动作授予桶资源，例如 `arn:aws:s3:::mybucket`。

## 配置示例 {#example}

下面允许 `https://app.example.com` 上的浏览器读取对象，并读取响应中的 `ETag`：

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

配置文档最大为 64 KiB，必须包含 1 至 100 条规则；每条规则至少包含一个 `AllowedOrigin` 和 `AllowedMethod`。
允许的方法为 `GET`、`PUT`、`HEAD`、`POST`、`DELETE`，不要把预检请求使用的 `OPTIONS` 写成允许方法。
`AllowedOrigin` 与 `AllowedHeader` 每项最多含一个 `*`，不接受 `?` 通配符。

## 生效边界 {#behavior}

已有桶级配置时，只匹配桶级规则；规则不匹配不会退回更宽松的全局规则。删除桶级配置后，已加载且没有 CORS 文档的桶使用全局 `MINIO_API_CORS_ALLOW_ORIGIN` / `api cors_allow_origin` 配置。因此，删除配置不等于禁止所有跨域请求。

启动期间尚未加载的桶、元数据加载失败的桶或无效的桶级配置不会回退到全局规则放宽访问。CORS 预检和响应头不授予 S3 权限；浏览器实际访问对象仍需匿名策略、有效凭证或预签名 URL。

桶级 CORS 随站点复制的桶元数据同步，并由 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/) 与 [`import`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-import/) 保留。更多实现边界见 [CORS 与复制信任边界](/zh/blog/design/cors-replication-trust/#cors-state-machine)。
