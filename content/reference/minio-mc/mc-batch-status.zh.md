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

`mcli batch status TARGET JOBID` 会持续观察批处理作业直至完成或失败。当实时指标暂未生成时，命令输出 `pending`（JSON 模式下为 `status: "pending"`），避免将排队中或暂缺采样点的任务误判为已完成。若连续 30 秒未收到任务指标或指标流提前中断，客户端会主动回查服务端持久化状态（单次查询超时为 10 秒）；若仍无法获取终态则返回错误，此时可重新运行命令继续观察。

只要成功获取到 `complete` 或 `failed` 终态，命令均以退出码 `0` 结束，自动化脚本应根据返回的 `status` 字段判断作业成败；当状态无法获取、任务不存在或请求出错时则返回非零退出码。此外，本版修复了海量对象下 IOPs 中间计算整数溢出的问题，详见[本版变更](/zh/blog/release/silo-20261026/#mcli)。

<a id="silo-status-details"></a>

## mcli 20261109 与 SILO 20261109：暂停与跳过结果 {#silo-job-outcomes}

[mcli 20261109](/zh/blog/release/mcli-20261109/) 与 [SILO 20261109](/zh/blog/release/silo-20261109/) 增加 `paused` 和 `complete-with-skips`。`paused` 是非终态：服务器正在等待重试，实时指标仍可用时客户端继续观察。`complete-with-skips` 表示本轮已经结束，但仍保留了受保护版本或整 key 被拒绝的对象，不代表所有选中对象都已删除。与 `complete`、`failed` 一样，成功取得它时退出码为 `0`；脚本必须检查状态与计数。

文本输出按需显示 `VersionsSkippedLocked`、`KeysRefused`、`FailureReason` 和 `PausedReason`。JSON 保留原有 `metric` 对象，在新增的 `details` 下提供 `versionsSkippedLocked`、`keysRefused`、`failureReason`、`pausedReason`。两个计数的单位不同，分别是跳过的版本数和整 key 拒绝数，不能相加当作已删除对象数。

实时指标包含完整详情时，客户端直接使用该快照，其中显式的零计数可清除此前的暂停或跳过状态。服务端或 peer 不支持实时扩展时，客户端在观察期间每五秒刷新持久化详情，实时指标到达终态时再查询一次（单次请求以十秒为超时）。早于实时进度的快照不能把旧暂停状态带回来，也不能把旧计数拼接到更新的结果上。无法确认终态详情时，保留实时结果，JSON 增加 `detailsUnavailable`，文本给出说明；详情缺失不能理解为跳过数为零。未提供新增字段的旧服务器保留原有输出。

若实时流结束时持久状态仍为暂停，命令会输出暂停原因并以非零退出码结束，因为还没有终态。重新运行命令即可继续观察，不会取消或重新提交作业。

实时流结束后同样检查状态的新旧：保存的终态如果早于已经观察到的进度，命令会拒绝采用并以非零退出码结束。延迟到达的实时采样不能使进度倒退，同时声称完成和失败的报告也会被拒绝。

<a id="id2" data-td-print-local></a>

## 语法 {#syntax}

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

<a id="id3" data-td-print-local></a>

### 参数 {#parameters}

##### `TARGET` {#mc.batch.status.TARGET}

*mc-cmd*

*Required*

要显示批处理作业状态的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `JOBID` {#mc.batch.status.JOBID}

*mc-cmd*

*Required*

要汇总的作业的唯一标识符。 要查找作业 ID，请使用 [`mc batch list`](/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list)。

TARGET 与 JOBID 都是必填参数。

<a id="id4" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id5" data-td-print-local></a>

## 示例 {#example}

<a id="id6" data-td-print-local></a>

### 汇总活动复制作业的事件 {#summarize-the-events-of-an-active-replicate-job}

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

<a id="s3" data-td-print-local></a>

### S3 兼容性 {#s3-compatibility}

SILO 是 PGSTY mcli 支持的服务端；与上游 MinIO 及其他 S3 服务的兼容性属于[尽力而为](/zh/reference/minio-mc/#command-mc)。
