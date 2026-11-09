---
title: "Silo 客户端设置"
url: "/zh/reference/minio-mc/minio-client-settings/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/minio-client-settings.rst
upstream_modified: true
---

<a id="minio" data-td-print-local></a>
<a id="minio-server-envvar-mc"></a>

本页面介绍 [MinIO Client](/zh/reference/minio-mc/#minio-client) 的设置。

你可以通过以下方式建立或修改设置：

- 在启动或重启 MinIO Server 之前，在宿主机系统上定义 *环境变量*。 如何定义环境变量，请参考所用操作系统的文档。
- 使用 [`mc admin config set`](/zh/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) 定义 *配置项*。

如果同时定义了环境变量和对应的配置项，MinIO 使用环境变量的值。

有些设置只有环境变量或配置项中的一种，而不是两者同时存在。

## 设置 {#id2}

### 主机凭证 {#id3}

使用此设置可为 *mc* 命令添加一个临时别名。 例如，可用于脚本场景。

该临时别名使用 [AWS s3v4 signature](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html)。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
<a id="envvar.MC_HOST_&lt;ALIAS&gt;"></a>

##### `MC_HOST_<ALIAS>` {#envvar.MC_HOST_-ALIAS}

*envvar*

将环境变量末尾的 `<ALIAS>` 替换为要设置主机的 `alias`。
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。

使用 [`mc alias set`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set) 配置 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。
{{< /tab >}}
{{< /tabs >}}

#### 示例 {#id4}

**静态凭证**

```shell {tab="语法" group="tab1-tab2" value="tab1"}
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>@<YOUR-S3-ENDPOINT>
```

```shell {tab="示例" value="tab2"}
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG@play.min.io
```

**Security Token Service (STS) 凭证**

```shell {tab="语法" group="tab1-tab2" value="tab1"}
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>:<Session Token>@<YOUR-S3-ENDPOINT>
```

```shell {tab="示例" value="tab2"}
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG:eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJOVUlCT1JaWVRWMkhHMkJNUlNYUiIsImF1ZCI6IlBvRWdYUDZ1Vk80NUlzRU5SbmdEWGo1QXU1WWEiLCJhenAiOiJQb0VnWFA2dVZPNDVJc0VOUm5nRFhqNUF1NVlhIiwiZXhwIjoxNTM0ODk2NjI5LCJpYXQiOjE1MzQ4OTMwMjksImlzcyI6Imh0dHBzOi8vbG9jYWxob3N0Ojk0NDMvb2F1dGgyL3Rva2VuIiwianRpIjoiNjY2OTZjZTctN2U1Ny00ZjU5LWI0MWQtM2E1YTMzZGZiNjA4In0.eJONnVaSVHypiXKEARSMnSKgr-2mlC2Sr4fEGJitLcJF_at3LeNdTHv0_oHsv6ZZA3zueVGgFlVXMlREgr9LXA@play.min.io
```

### STS 服务 {#sts}

> [!NOTE]
> **新增: mc**
>
> RELEASE.2023-11-06T04-19-23Z

使用此设置可添加一个用于 *mc* 命令的 STS endpoint。

> [!NOTE]
> **变更: mc**
>
> RELEASE.2023-12-02T02-03-28Z

支持按 alias 添加多个环境变量。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
<a id="envvar.MC_STS_ENDPOINT_&lt;alias&gt;"></a>

##### `MC_STS_ENDPOINT_<alias>` {#envvar.MC_STS_ENDPOINT_-alias}

*envvar*

```shell
export MC_STS_ENDPOINT_myalias=https://sts.minio-operator.svc.cluster.local:4223/sts/ns-1
```
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### Web Token Identity {#web-token-identity}

> [!NOTE]
> **新增: mc**
>
> RELEASE.2023-11-06T04-19-23Z

使用此设置可添加一个用于 *mc* 命令的 Web Token Identity。

> [!NOTE]
> **变更: mc**
>
> RELEASE.2023-12-02T02-03-28Z

支持按 alias 添加多个环境变量。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
<a id="envvar.MC_WEB_IDENTITY_TOKEN_&lt;alias&gt;"></a>

##### `MC_WEB_IDENTITY_TOKEN_<alias>` {#envvar.MC_WEB_IDENTITY_TOKEN_-alias}

*envvar*

```shell
export MC_WEB_IDENTITY_TOKEN_FILE_myalias=/var/run/secrets/kubernetes.io/serviceaccount/token
```
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### 配置目录 {#id5}

指定 MinIO Client 应使用的配置目录路径。在 `pgsty/mc` 容器镜像（`20261109+`）中，`/.mc` 目录预创建为 `1777` 权限，支持任意非 root UID 初始化配置。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_CONFIG_DIR` {#envvar.MC_CONFIG_DIR}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### S3 区域（Region）覆盖 {#s3-region}

可通过环境变量固定 S3 签名区域，并覆盖 `config.json` 中别名的 `region`。固定区域会跳过 SDK 的桶区域发现；详见 [Alias 区域设计](/zh/blog/design/alias-region/)。

生效优先级：`MC_REGION` > `AWS_REGION` > `config.json` 中别名的 `region` 字段 > SDK 自动发现区域。S3 客户端缓存键包含实际生效的 `region`，切换 `MC_REGION` 或 `AWS_REGION` 时不会复用旧区域的签名客户端。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_REGION` / `AWS_REGION` {#envvar.MC_REGION}

*envvar*

```shell
export MC_REGION=ap-southeast-1
```
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
在 `~/.mc/config.json` 的对应别名条目中设置 `"region": "<region-name>"`。
{{< /tab >}}
{{< /tabs >}}

### 进度条 {#id6}

禁用 MinIO Client 进度条。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_QUIET` {#envvar.MC_QUIET}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### Pager {#pager}

> [!NOTE]
> **新增: mc**
>
> RELEASE.2024-04-29T09-56-05Z

在 CLI 中禁用 MinIO Client 的分页器功能。 使用该设置后，输出将改为直接打印到原始 `STDOUT`。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_DISABLE_PAGER` {#envvar.MC_DISABLE_PAGER}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### 颜色主题 {#id7}

禁用 MinIO Client 输出使用的颜色主题。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_NO_COLOR` {#envvar.MC_NO_COLOR}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### JSON {#json}

启用将输出格式化为 JSON lines。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_JSON` {#envvar.MC_JSON}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### 调试 {#id8}

启用调试输出。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_DEBUG` {#envvar.MC_DEBUG}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### 禁用 SSL {#ssl}

禁用 SSL 证书校验。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_INSECURE` {#envvar.MC_INSECURE}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### 限制下载带宽 {#id9}

限制 MinIO Client 在某些命令中使用的下载带宽。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_LIMIT_DOWNLOAD` {#envvar.MC_LIMIT_DOWNLOAD}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

若未指定，MinIO Client 使用全部可用带宽。

将客户端侧下载速率限制为不超过指定值（KiB/s、MiB/s 或 GiB/s）。该设置仅影响运行 MinIO Client 的本地设备发起的下载。支持的单位包括：

- B 表示 bytes
- K 表示 kilobytes
- M 表示 megabytes
- G 表示 gigabytes
- Ki 表示 kibibytes
- Mi 表示 mibibytes
- Gi 表示 gibibytes

例如，要将下载速率限制为不超过 1 GiB/s，可在 Linux 系统上使用以下命令：

```shell
export MC_LIMIT_DOWNLOAD=1G
```

在非 Linux 系统上，请参考你的操作系统文档使用等效命令。

### 限制上传带宽 {#id10}

限制 MinIO Client 在某些命令中使用的上传带宽。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_LIMIT_UPLOAD` {#envvar.MC_LIMIT_UPLOAD}

*envvar*
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

若未指定，MinIO Client 使用全部可用带宽。

将客户端侧上传速率限制为不超过指定值（KiB/s、MiB/s 或 GiB/s）。该设置仅影响运行 MinIO Client 的本地设备发起的上传。支持的单位包括：

- B 表示 bytes
- K 表示 kilobytes
- M 表示 megabytes
- G 表示 gigabytes
- Ki 表示 kibibytes
- Mi 表示 mibibytes
- Gi 表示 gibibytes

例如，要将上传速率限制为不超过 1 GiB/s，可在 Linux 系统上使用以下命令：

```shell
export MC_LIMIT_UPLOAD=1G
```

在非 Linux 系统上，请参考你的操作系统文档使用等效命令。

### SSE-KMS 加密 {#sse-kms}

使用服务端管理密钥通过 [SSE-KMS](/zh/operations/server-side-encryption/#minio-sse-data-encryption) 对对象进行加密和解密。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_ENC_KMS` {#envvar.MC_ENC_KMS}

*envvar*

使用 `ALIAS/BUCKET/PREFIX=KEY_NAME` 映射格式，例如 `MC_ENC_KMS=mysilo/encryptedbucket/=silo-bucket`。多个映射之间以逗号分隔。密钥名称标识由服务端 KMS 管理的密钥，而非密钥材料本身。
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

### SSE-S3 加密 {#sse-s3}

请求使用服务端管理密钥的 [SSE-S3](/zh/operations/server-side-encryption/#minio-sse-data-encryption) 加密。

{{< tabs group="tab1-tab2" default="tab1" >}}
{{< tab label="环境变量" value="tab1" >}}
##### `MC_ENC_S3` {#envvar.MC_ENC_S3}

*envvar*

指定目标别名、存储桶或对象前缀，例如 `MC_ENC_S3=mysilo/encryptedbucket/`。多个前缀之间以逗号分隔。该变量仅选择请求 SSE-S3 的路径，请勿传入 KMS 密钥名称或密钥材料；SILO 会自动选用其配置的默认密钥（例如 KES 部署中的 `MINIO_KMS_KES_KEY_NAME`）。
{{< /tab >}}
{{< tab label="配置项" value="tab2" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}
