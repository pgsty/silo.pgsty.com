---
title: "mc batch"
url: "/zh/reference/minio-mc/mc-batch/"
weight: 40
icon: fa-solid fa-layer-group
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch.rst
upstream_modified: true
---

<a id="mc-batch"></a>

<a id="command-mc.batch"></a>

> [!NOTE]
> **新增: mc**
>
> RELEASE.2023-03-20T17-17-53Z
>
> 新增了通过 [`mc batch cancel`](/zh/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel) 命令取消作业的能力。

<a id="id2" data-td-print-local></a>

## 描述 {#description}

[`mc batch`](#command-mc.batch) 命令允许您在 MinIO 部署上运行一个或多个作业任务。

<a id="id3" data-td-print-local></a>

## 子命令 {#subcommands}

[`mc batch`](#command-mc.batch) 包含以下子命令：

| 子命令                                                                            | 描述                                         |
| --------------------------------------------------------------------------------- | -------------------------------------------- |
| [`cancel`](/zh/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel)       | 停止正在进行的批处理作业。                   |
| [`describe`](/zh/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe) | 输出指定作业 ID 的作业定义。                 |
| [`generate`](/zh/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate) | 为指定作业类型创建基础 YAML 格式模板文件。   |
| [`list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)             | 输出部署上当前正在进行的批处理作业列表。     |
| [`start`](/zh/reference/minio-mc/mc-batch-start/#command-mc.batch.start)          | 根据批处理作业 YAML 定义文件启动批处理作业。 |
| [`status`](/zh/reference/minio-mc/mc-batch-status/#command-mc.batch.status)       | 输出服务器上作业事件的汇总信息。             |
{.wide .expand}

> [!NOTE]
> **变更: mc `RELEASE.2024-07-03T20-17-25Z`**
>
> [`mc batch status`](/zh/reference/minio-mc/mc-batch-status/#command-mc.batch.status) 会显示活动且正在进行的作业，以及过去三（3）天内完成的任意批处理作业的汇总信息。
