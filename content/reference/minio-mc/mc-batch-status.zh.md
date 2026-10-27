---
title: "mc batch status"
url: "/zh/reference/minio-mc/mc-batch-status/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-status.rst
upstream_modified: true
---

<a id="mc-batch-status"></a>
<a id="minio-mc-batch-status"></a>

<a id="command-mc.batch.status"></a>

> [!NOTE]
> **变更: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

## mcli 20261026 状态与退出码 {#silo-20261026}

`mcli batch status TARGET JOBID` 会观察到任务完成或失败。实时指标暂缺时输出 `pending`（JSON 同样使用 `status: "pending"`），不把排队或缺样本解释为已完成。连续 30 秒没有任务指标，或流提前结束时，客户端查询持久化状态；单次状态请求最长 10 秒。没有可用终态时返回错误，可重新执行状态命令继续观察。

成功取得 `complete` 或 `failed` 终态均退出 0；脚本应检查返回状态判断任务结果。无法取得状态、任务不存在或请求失败时退出非零。大量对象的 IOPs 计算不会因整数中间值溢出。详见[本版变更](/zh/blog/release/silo-20261026/#mcli)。

## 语法 {#id2}

[`mc batch status`](#command-mc.batch.status) 命令会输出 MinIO 服务器上作业事件的汇总信息。

> [!NOTE]
> **变更: mc**
>
> RELEASE.2024-07-03T20-17-25Z
>
> Batch status 会显示活动且正在进行的作业，或前 3（三）天内已完成的任意批处理作业的汇总信息。

{{< tabs group="tab1-tab2" >}}
{{< tab label="示例" value="tab1" >}}
以下命令会输出 `myminio` alias 上当前正在运行、JobID 为 `KwSysDpxcBU9FNhGkn2dCf` 的指定作业状态。

```shell
mcli batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
```
{{< /tab >}}
{{< tab label="语法" value="tab2" >}}
该命令的语法如下：

```shell
mcli [GLOBALFLAGS] batch status TARGET JOBID
```

- 方括号 `[]` 表示可选参数。
- 同一行中的参数彼此相互依赖。
- 使用管道符 `|` 分隔的参数彼此互斥。

请先将示例复制到文本编辑器中并按需修改，再在终端 / shell 中运行命令。
{{< /tab >}}
{{< /tabs >}}

### 参数 {#id3}

##### `TARGET` {#mc.batch.status.TARGET}

*mc-cmd*

*Required*

要显示批处理作业状态的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `JOBID` {#mc.batch.status.JOBID}

*mc-cmd*

*Required*

要汇总的作业的唯一标识符。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

TARGET 与 JOBID 都是必填参数。

### 全局标志 {#id4}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 示例 {#id5}

### 汇总活动复制作业的事件 {#id6}

以下命令会为 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) `myminio` 对应部署上的活动作业提供实时汇总：

```shell
mcli batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
```

- 将 `myminio` 替换为应运行该作业的 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

上述命令的输出如下所示：

```shell
●∙∙
JobType:        replicate
Objects:        28766
Versions:       28766
FailedObjects:  0
Transferred:    406 MiB
Elapsed:        2m14.227222868s
CurrObjName:    share/doc/xml-core/examples/foo.xmlcatalogs
```

### S3 兼容性 {#s3}

**`mc`** 命令行工具以兼容 AWS S3 API 为目标构建，并针对 MinIO 和 AWS S3 进行了测试，以验证预期的功能与行为。

对于其他 S3 兼容服务，MinIO 不提供任何保证，因为这些服务的 S3 API 实现未知， 因此不在支持范围内。虽然 **`mc`** 命令 *可能* 仍能按文档说明工作，但此类 用法需要你自行承担风险。
