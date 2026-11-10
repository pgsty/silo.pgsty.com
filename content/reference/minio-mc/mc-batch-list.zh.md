---
title: "mc batch list"
url: "/zh/reference/minio-mc/mc-batch-list/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-list.rst
upstream_modified: true
---

<a id="mc-batch-list"></a>
<a id="minio-mc-batch-list"></a>

<a id="command-mc.batch.list"></a>

> [!NOTE]
> **变更: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

<a id="id2" data-td-print-local></a>

## 语法 {#syntax}

[`mc batch list`](#command-mc.batch.list) 命令会输出部署中当前正在进行的批处理作业列表。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令会输出 `myminio` alias 上当前正在进行的所有作业列表。

```shell
mc batch list myminio
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] batch list TARGET           \
                            [--type "string"]
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

<a id="id3" data-td-print-local></a>

### 参数 {#parameters}

##### `TARGET` {#mc.batch.list.TARGET}

*mc-cmd*

*Required*

要列出进行中作业的目标部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `--type` {#mc.batch.list.-type}

*mc-cmd*

*Optional*

仅列出指定类型的批处理作业。有效值为 `replicate`、`keyrotate` 和 `expire`。

<a id="id4" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id5" data-td-print-local></a>

## 示例 {#example}

<a id="replicate" data-td-print-local></a>

### 列出所有 `replicate` 类型的批处理作业 {#list-all-replicate-type-batch-jobs}

以下命令列出 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) `myminio` 所对应部署上的 `replicate` 类型作业：

```shell
mc batch list myminio --type "replicate"
```

- 将 `myminio` 替换为应运行该作业的 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `replicate` 替换为要输出的作业类型。[`mc batch`](/zh/reference/minio-mc/mc-batch/#command-mc.batch) 支持 `replicate`、`keyrotate` 和 `expire` 三种作业类型。

上述命令的输出类似如下：

```shell
ID                      TYPE            USER            STARTED
E24HH4nNMcgY5taynaPfxu  replicate       minioadmin      1 minute ago
```

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 支持的服务端；与上游 MinIO 及其他 S3 服务的兼容性属于[尽力而为](/zh/reference/minio-mc/#command-mc)。

<a id="id6" data-td-print-local></a>

## 权限 {#permissions}

你必须具有 [`admin:ListBatchJobs`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListBatchJobs) 权限，才能列出该部署上的作业。
