---
title: "mc admin heal"
url: "/zh/reference/minio-mc-admin/mc-admin-heal/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-heal.rst
upstream_modified: true
---

<a id="mc-admin-heal"></a>

<a id="command-mc.admin.heal"></a>

<a id="id2" data-td-print-local></a>

## 说明 {#description}

[`mc admin heal`](#command-mc.admin.heal) 命令会扫描受损或损坏的对象，并对这些对象执行自愈。

[`mc admin heal`](#command-mc.admin.heal) 资源开销较大，通常不需要手动执行，即使在驱动器故障或数据损坏事件之后也是如此。

作为正常运行的一部分，MinIO 会：

- 在每次 `POST` 或 `GET` 操作时，自动修复因静默位腐坏、驱动器故障或其他问题而受损的对象。
- 使用 [scanner](/zh/operations/concepts/scanner/#minio-concepts-scanner) 周期性执行后台对象自愈。
- 在更换驱动器后积极执行对象自愈。

有关 MinIO 如何执行对象自愈的更多详细信息，请参阅 [对象自愈](/zh/operations/concepts/healing/#minio-concepts-healing)。

> [!NOTE]
> **服务端兼容性**
>
> [`mcli admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 正式支持的目标服务端为 SILO。与未修改的上游 MinIO 保持尽最大努力兼容；仅具备通用 S3 兼容性并不提供这些管理 API。

<a id="id3" data-td-print-local></a>

## 语法 {#syntax}

[`mc admin heal`](#command-mc.admin.heal) 使用以下语法：

```shell
mc admin heal [FLAGS] TARGET             \
                      [--all-drives, -a] \
                      [--dry-run, -n]    \
                      [--force]          \
                      [--verbose, -v]
```

[`mc admin heal`](#command-mc.admin.heal) 支持以下参数：

#### `TARGET` {#mc.admin.heal.TARGET}

*mc-cmd*

*Required*

执行对象自愈的存储桶或存储桶前缀的完整路径。 指定已配置的 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) 作为该路径的前缀。 例如：

```shell
mc admin heal play/mybucket/myprefix
```

如果 `TARGET` 存储桶或存储桶前缀存在活动的自愈扫描，命令将返回该扫描的状态。

#### `--all-drives, -a` {#mc.admin.heal.-all-drives}

*mc-cmd*

*Optional*

选择所有驱动器并显示详细信息。

#### `--dry-run, -n` {#mc.admin.heal.-dry-run}

*mc-cmd*

*Optional*

仅检查对象并报告驱动器与分片的健康状态，不修改或删除磁盘上的任何数据。

#### `--force` {#mc.admin.heal.-force}

*mc-cmd*

*Optional*

禁用警告提示。

#### `--verbose, -v` {#mc.admin.heal.-verbose}

*mc-cmd*

*Optional*

显示离线和故障驱动器的自愈信息。

## 行为说明 {#behavior}

在 [SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）与 [mcli 20261109](/zh/blog/release/mcli-20261109/) 中：

- `mc admin heal --dry-run`（`-n`）严格保持只读，不会删除磁盘上悬空或损坏的数据（[PR #280](https://github.com/pgsty/silo/pull/280)）。
- 服务端将 `xl.meta` 校验和错误归类为可自愈状态，使受损元数据分片能够得到修复（[#309](https://github.com/pgsty/silo/issues/309)）。
- 当排队中的生命周期过期因版本历史不完整或损坏而被拒绝时，服务端会将相应对象版本加入自愈队列（[#303](https://github.com/pgsty/silo/issues/303)）。
- `mcli` 可将自愈字节进度清晰格式化至 `EiB` 量级。

<a id="id4" data-td-print-local></a>

<a id="minio-concepts-healing-colors" data-td-print-local></a>

## 自愈颜色 {#healing-colors}

某些版本的 MinIO 使用颜色标识来区分不同自愈状态的对象。

> [!NOTE]
> **变更: mc**
>
> RELEASE.2024-11-17T19-35-25Z

颜色含义已更新。

- 绿色表示存储桶健康。
- 黄色表示存储桶在一个或多个驱动器上需要执行自愈。
- 红色表示一个或多个驱动器处于不健康状态。
- 灰色表示自愈状态不确定。
