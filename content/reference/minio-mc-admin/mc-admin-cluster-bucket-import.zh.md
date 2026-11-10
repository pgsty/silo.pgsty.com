---
title: "mc admin cluster bucket import"
url: "/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-import/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-cluster-bucket-import.rst
upstream_modified: true
---

<a id="command-mc.admin.cluster.bucket.import"></a>
<a id="mc-admin-cluster-bucket-import"></a>
<a id="minio-mc-admin-cluster-bucket-import"></a>

<a id="id1" data-td-print-local></a>

## 描述 {#description}

> [!NOTE]
> **新增: RELEASE.2022-06-17T02-52-50Z**

[`mc admin cluster bucket import`](#command-mc.admin.cluster.bucket.import) 命令用于导入由 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 命令生成的存储桶元数据。

你可以使用此命令将元数据手动恢复到 MinIO 部署中的指定存储桶。

如果仅将部署指定为目标，此命令会将元数据对象应用到目标上所有匹配的存储桶。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令将指定的元数据导入到 `myminio` 部署。

```shell
mc admin cluster bucket import myminio ~/minio-metadata-backup/myminio-cluster.zip
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
命令语法如下：

```shell
mc [GLOBALFLAGS] admin cluster bucket import  \
                                    ALIAS[/BUCKET] \
                                    METADATA.ZIP
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

<a id="id2" data-td-print-local></a>

### 参数 {#parameters}

##### `ALIAS` {#mc.admin.cluster.bucket.import.ALIAS}

*mc-cmd*

*Required*

MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

##### `METADATA.ZIP` {#mc.admin.cluster.bucket.import.METADATA.ZIP}

*mc-cmd*

*Required*

要导入的元数据文件路径。

使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 导出存储桶元数据，以供此命令使用。

##### `BUCKET` {#mc.admin.cluster.bucket.import.BUCKET}

*mc-cmd*

*Optional*

应用导入元数据的存储桶。

<a id="id3" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 行为 {#behavior}

### 逐项导入失败时的退出码（`mcli 20261109`） {#exit-status}

在 [`mcli 20261109`](/zh/blog/release/mcli-20261109/) 中，当逐存储桶或逐功能项元数据导入失败时，`mc admin cluster bucket import` 会在保留详细错误报告的同时返回退出码 `1`。
