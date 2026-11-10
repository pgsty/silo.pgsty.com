---
title: "mc batch describe"
url: "/zh/reference/minio-mc/mc-batch-describe/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-describe.rst
upstream_modified: true
---

<a id="mc-batch-describe"></a>
<a id="minio-mc-batch-describe"></a>

<a id="command-mc.batch.describe"></a>

> [!NOTE]
> **变更: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

<a id="id1" data-td-print-local></a>

## 语法 {#syntax}

[`mc batch describe`](#command-mc.batch.describe) 命令会输出指定作业 ID 的作业定义。

必须指定作业 ID。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令会输出标识为 `KwSysDpxcBU9FNhGkn2dCf` 的作业定义。

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
此命令的语法如下：

```shell
mc [GLOBALFLAGS] batch describe TARGET           \
                                JOBID
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

<a id="id2" data-td-print-local></a>

### 参数 {#parameters}

##### `TARGET` {#mc.batch.describe.TARGET}

*mc-cmd*

*Required*

用于查找作业 ID 的 MinIO 部署 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `JOBID` {#mc.batch.describe.JOBID}

*mc-cmd*

*Required*

要描述的作业的唯一标识符。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

<a id="id3" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id4" data-td-print-local></a>

## 示例 {#example}

<a id="id5" data-td-print-local></a>

### 显示进行中批处理作业的定义 {#show-the-definition-of-an-in-progress-batch-job}

以下命令会输出 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) `myminio` 上特定作业的完整作业定义：

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
```

- 将 `myminio` 替换为应运行该作业的 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `KwSysDpxcBU9FNhGkn2dCf` 替换为要定义的作业 ID。

上述命令的输出类似如下：

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
replicate:
  apiVersion: v1
...
```

注意，此示例已截断。 输出结果是指定作业的完整作业定义。

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 支持的服务端；与上游 MinIO 及其他 S3 服务的兼容性属于[尽力而为](/zh/reference/minio-mc/#command-mc)。

<a id="id6" data-td-print-local></a>

## 权限 {#permissions}

你必须具有 `admin:DescribeBatchJob` 权限，才能描述该部署上的作业。
