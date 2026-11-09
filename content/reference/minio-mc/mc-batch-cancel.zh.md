---
title: "mc batch cancel"
url: "/zh/reference/minio-mc/mc-batch-cancel/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-cancel.rst
upstream_modified: true
---

<a id="mc-batch-cancel"></a>
<a id="minio-mc-batch-cancel"></a>

<a id="command-mc.batch.cancel"></a>

> [!NOTE]
> **新增: mc**
>
> RELEASE.2023-03-20T17-17-53Z

<a id="id1" data-td-print-local></a>

## 语法 {#syntax}

[`mc batch cancel`](#command-mc.batch.cancel) 可停止正在进行的批处理作业。

您必须指定作业 ID。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令会输出标识为 `KwSysDpxcBU9FNhGkn2dCf` 的作业定义。

```shell
mc batch cancel myminio KwSysDpxcBU9FNhGkn2dCf
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令使用以下语法：

```shell
mc [GLOBALFLAGS] batch cancel ALIAS JOBID
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

<a id="id2" data-td-print-local></a>

### 参数 {#parameters}

##### `ALIAS` {#mc.batch.cancel.ALIAS}

*mc-cmd*

*Required*

当前运行该作业的 MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `JOBID` {#mc.batch.cancel.JOBID}

*mc-cmd*

*Required*

要取消的批处理作业的唯一标识符。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

<a id="id3" data-td-print-local></a>

### 全局参数 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id4" data-td-print-local></a>

## 示例 {#example}

<a id="id5" data-td-print-local></a>

### 取消正在进行的批处理作业 {#cancel-an-ongoing-batch-job}

以下命令会取消别名为 `myminio` 的部署上 ID 为 `KwSysDpxcBU9FNhGkn2dCf` 的作业：

```shell
mc batch cancel myminio KwSysDpxcBU9FNhGkn2dCf
```

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 支持的服务端；与上游 MinIO 及其他 S3 服务的兼容性属于[尽力而为](/zh/reference/minio-mc/#command-mc)。
