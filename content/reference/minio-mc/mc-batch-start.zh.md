---
title: "mc batch start"
url: "/zh/reference/minio-mc/mc-batch-start/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-start.rst
upstream_modified: true
---

<a id="mc-batch-start"></a>
<a id="minio-mc-batch-start"></a>

<a id="command-mc.batch.start"></a>

> [!NOTE]
> **变更: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

<a id="id2" data-td-print-local></a>

## 语法 {#syntax}

[`mc batch start`](#command-mc.batch.start) 命令根据批处理作业 YAML 文件启动一个批处理作业。

批处理作业会运行一次直到完成（或达到文件中指定的最大重试次数）。 若要在完成后再次运行该批处理作业，必须重新启动它。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令在 `myminio` 别名对应的部署上从 `jobfile.yaml` 启动一个批处理作业。

```shell
mc batch start myminio jobfile.yaml
```

上述命令的输出类似如下：

```shell
Successfully start 'replicate' job `B34HHqnNMcg1taynaPfxu` on '2022-10-24 17:19:06.296974771 -0700 PDT'
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令具有以下语法：

```shell
mc [GLOBALFLAGS] batch start    \
                       ALIAS   \
                       JOBFILE
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

<a id="id3" data-td-print-local></a>

### 参数 {#parameters}

##### `ALIAS` {#mc.batch.start.ALIAS}

*mc-cmd*

*Required*

用于启动批处理作业的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

例如：

```text
mc batch start myminio replicate.yaml
```

##### `JOBFILE` {#mc.batch.start.JOBFILE}

*mc-cmd*

*Required*

定义一个批处理作业（`replicate`、`keyrotate` 或 `expire`）的 YAML 文件路径。

<a id="id4" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id5" data-td-print-local></a>

## 示例 {#example}

<a id="id6" data-td-print-local></a>

### 启动批处理作业 {#start-a-batch-job}

以下命令会在 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) `myminio` 对应的部署上，启动 `replication.yaml` 文件中定义的批处理作业：

```shell
mc batch start myminio ./replication.yaml
```

- 将 `myminio` 替换为应运行该作业的 MinIO 部署 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `./replication.yaml` 替换为描述批处理作业的 YAML 格式文件。 使用相对于当前位置的文件路径。

上述命令的输出类似如下：

```shell
Successfully start 'replicate' job `E24HH4nNMcgY5taynaPfxu` on '2022-09-26 17:19:06.296974771 -0700 PDT'
```

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 正式支持的服务器；与上游 MinIO 和其他 S3 服务的兼容性遵循[尽最大努力原则](/zh/reference/minio-mc/#command-mc)。

## 权限 {#permissions}

要启动作业，必须在该部署上具有 [`admin:StartBatchJob`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-StartBatchJob) 权限。

[SILO 20261109](/zh/blog/release/silo-20261109/) 还会在作业列举或修改对象时强制校验已认证提交者的本地数据权限。作业定义中的凭据仅另行授权远端操作，详见[授权与重试](/zh/administration/batch-framework/#silo-lifecycle)。
