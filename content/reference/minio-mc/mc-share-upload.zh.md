---
title: "mc share upload"
url: "/zh/reference/minio-mc/mc-share-upload/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-share-upload.rst
upstream_modified: true
---

<a id="mc-share-upload"></a>

<a id="command-mc.share.upload"></a>

## 语法 {#id2}

[`mc share upload`](#command-mc.share.upload) 命令会生成一个临时的预签名 URL，并集成用于将对象上传到 MinIO 存储桶的访问凭证。该临时 URL 会在可配置的时间限制后过期。

应用程序使用生成的策略字段，通过 multipart 表单 `POST` 上传对象。

有关可共享对象 URL 的更多信息，请参阅 Amazon S3 文档中的 [Pre-Signed URLs](https://docs.aws.amazon.com/AmazonS3/latest/dev/ShareObjectPreSignedURL.html)。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令会为 `myminio` MinIO 部署上的 `mydata` 存储桶生成一个新的预签名上传 URL：

```shell
mc share upload --recursive myminio/mydata
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] share upload               \
                 [--content-type "string"]  \
                 [--expire "string"]        \
                 [--recursive]              \
                 ALIAS
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

### 参数 {#id3}

##### `ALIAS` {#mc.share.upload.ALIAS}

*mc-cmd*

*Required* MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias) 以及要为其生成上传 URL 的对象完整路径。例如：

```shell
mc share upload play/mybucket/object.txt
```

你可以在同一个或不同的 MinIO 部署上指定多个对象。例如：

```shell
mc share upload play/mybucket/object.txt play/mybucket/otherobject.txt
```

如果指定的是存储桶路径或存储桶前缀路径，则你 **必须** 同时指定 [`--recursive`](#mc.share.upload.-recursive) 参数。例如：

```shell
mc share upload --recursive play/mybucket/

mc share upload --recursive play/mybucket/myprefix/
```

##### `--content-type, T` {#mc.share.upload.-content-type}

*mc-cmd*

*Optional* 将上传限制为仅接受带有特定 [Content-Type](https://www.w3.org/Protocols/rfc1341/4_Content-Type.html) 头的请求。

指定一个字符串作为可接受的 `Content-Type` 值。 例如，`video/mp4`。

配置后，使用该生成 URL 的客户端必须包含指定类型的 `Content-Type` 头。 MinIO 会拒绝未携带正确 `Content-Type` 头的请求。

Content types 也称为 [media types](https://www.iana.org/assignments/media-types/media-types.xhtml)。

##### `--expire, E` {#mc.share.upload.-expire}

*mc-cmd*

*Optional* 为所有生成的 URL 设置过期时限。

指定格式为 `##h##m##s` 的字符串。例如： `12h34m56s` 表示在 URL 生成后 12 小时 34 分 56 秒过期。

默认值为 `168h`，即 168 小时（7 天）。

##### `--recursive, r` {#mc.share.upload.-recursive}

*mc-cmd*

*Optional* 修改 CURL URL 以支持将对象上传到存储桶或存储桶前缀。 如果任意 `ALIAS` 指定的是存储桶路径或存储桶前缀路径，则该选项为必需。修改后的 CURL 输出如下所示：

```shell
curl 'https://silo.example.com/mybucket/' ... --form-string 'key=<NAME>' --form 'file=@<FILE>'
```

将 `<FILE>` 替换为要上传的文件路径。

将 `<NAME>` 替换为上传后的对象名称。 该名称可以包含 [prefixes](/zh/glossary/#term-prefix)。

### 全局参数 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id5}

### 生成用于上传对象的 URL {#url}

{{< tabs group="tab1-tab2" >}}
{{< tab label="上传单个对象" value="tab1" >}}
使用 [`mc share upload`](#command-mc.share.upload) 生成一个支持 `POST` 请求的 URL， 用于将文件上传到 MinIO 部署上的特定对象位置：

```shell
mc share upload --expire DURATION ALIAS/PATH
```

- 将 [`ALIAS`](#mc.share.upload.ALIAS) 替换为 MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。
- 将 [`PATH`](#mc.share.upload.ALIAS) 替换为 MinIO 部署中对象的路径。
- 将 [`DURATION`](#mc.share.upload.-expire) 替换为 URL 过期前的时长。 例如，要设置 30 天过期时间，指定 `30d`。
{{< /tab >}}
{{< tab label="上传多个对象" value="tab2" >}}
使用 [`mc share upload`](#command-mc.share.upload) 并结合 [`--recursive`](#mc.share.upload.-recursive) 与 [`--expire`](#mc.share.upload.-expire) 选项，生成一个临时 URL， 该 URL 支持 `POST` 请求，用于将文件上传到 MinIO 部署上的存储桶：

```shell
mc share upload --recursive --expire DURATION ALIAS/PATH
```

- 将 [`ALIAS`](#mc.share.upload.ALIAS) 替换为 MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。
- 将 [`PATH`](#mc.share.upload.ALIAS) 替换为 MinIO 部署中的存储桶或存储桶前缀路径。
- 将 [`DURATION`](#mc.share.upload.-expire) 替换为 URL 过期前的时长。 例如，要设置 30 天过期时间，指定 `30d`。

该命令会返回一个用于向指定存储桶前缀上传对象的 CURL 命令。

- 将返回的 CURL 命令中的 `<FILE>` 字符串替换为要上传的文件路径。
- 将返回的 CURL 命令中的 `<NAME>` 字符串替换为存储桶中的对象名称。 该名称可以包含 [prefixes](/zh/glossary/#term-prefix)。

你可以使用 shell 脚本循环将文件系统目录中的内容递归上传到兼容 S3 的服务：

```shell
#!/bin/sh

for file in "$HOME"/Documents/photos/*
do
   [ -f "$file" ] || continue
   curl 'https://silo.example.com/mybucket/' \
   --form-string 'policy=AAAAA' \
   --form-string 'x-amz-algorithm=AWS4-HMAC-SHA256' \
   --form-string 'x-amz-credential=AAAA/us-east-1/s3/aws4_request' \
   --form-string 'x-amz-date=20200812T202556Z' \
   --form-string 'x-amz-signature=AAAA' \
   --form-string 'bucket=mybucket' \
   --form-string "key=photos/${file##*/}" --form "file=@${file}"
done
```

此示例会将 `~/Documents/photos/` 目录中的每个文件上传到 `mybucket` 存储桶下的 `photos` 前缀。 对于如何遍历目录中的文件，请遵循你所选脚本语言文档中的最佳实践。
{{< /tab >}}
{{< /tabs >}}

## 行为 {#id6}

### 生成命令与 shell 兼容性 {#shell-compatibility}

自 [mcli 20261109](/zh/blog/release/mcli-20261109/)（见[兼容性说明](/zh/compatibility/mcli/#current-release)）起，生成的命令会按 POSIX shell 语法引用完整参数，文本字段使用 `--form-string`。替换 `<FILE>` 和 `<NAME>` 时保留这些引号；替换值自身含引号时也需要正确转义。若编辑后的命令保存在 `upload` 变量中，使用 `sh -c "$upload"` 执行。直接执行 `$upload` 只会分词，不会解释其中的引号，可能导致失败。Windows 上应在 Git Bash 或 WSL 中执行；输出不是 `cmd.exe` 语法。

上面的循环直接向 curl 传递各个参数。使用时将端点和示例策略字段替换成当前生成命令中的值；示例凭证与签名只是占位内容。

### S3 兼容性 {#s3}

PGSTY mcli 正式支持的服务端是 SILO；对上游 MinIO 和其他 S3 服务的兼容属于[尽最大努力](/zh/reference/minio-mc/#command-mc)。
