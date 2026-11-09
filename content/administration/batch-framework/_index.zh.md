---
title: "批处理框架"
url: "/zh/administration/batch-framework/"
weight: 170
icon: fa-solid fa-layer-group
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/batch-framework.rst
upstream_modified: true
---

<a id="minio-batch-framework"></a>
<a id="id1" data-td-print-local></a>

## 概述 {#overview}

MinIO 批处理框架允许使用 YAML 格式的作业定义文件（“batch file”）来创建、管理、监控和执行作业。 批处理作业直接在 MinIO 部署上运行，从而利用服务端处理能力，而不受运行 [MinIO Client](/zh/reference/minio-mc/#minio-client) 的本地机器限制。

一个批处理文件定义一个作业任务。

启动后，MinIO 会开始处理该作业。 完成所需时间取决于部署可用的资源。

普通作业故障遵循定义中的重试次数上限。下一个 SILO 版本会区分授权拒绝与临时暂停，详见下文。

MinIO 批处理框架支持以下作业类型：

| 作业类型 | 说明 |
| --- | --- |
| [replicate](/zh/administration/batch-framework-job-replicate/#minio-batch-framework-replicate-job) | 执行一次性复制流程，将数据从一个 MinIO 位置复制到另一个 MinIO 位置。 |
| [keyrotate](/zh/administration/batch-framework-job-keyrotate/#minio-batch-framework-keyrotate-job) | 执行一次性流程，轮换对象上的 [sse-s3 or sse-kms](/zh/operations/server-side-encryption/#minio-sse-data-encryption) 加密密钥。 |
| [expire](/zh/administration/batch-framework-job-expire/#minio-batch-framework-expire-job) | 对存储桶中的对象执行一次性立即过期操作。 |
{.wide .expand}

## SILO 下一个版本：授权与重试 {#silo-lifecycle}

SILO 创建作业时，把本地批处理操作绑定到经过认证的提交者。定义中的凭据用于远端连接，不会授予本地服务器权限；执行动作时再次检查当时的 IAM 权限。显式拒绝、凭据过期或撤销、提交者绑定发生变化，都会以 `failureReason` 结束作业。策略依赖后台作业无法取得的请求上下文时，也会拒绝相应动作。

IAM 尚未加载、策略资料暂时不可用、授权插件无法给出有效决定，都属于临时故障。提交阶段无法决定授权时返回 `503`。过期和密钥轮换作业通过 `pausedReason` 记录暂停，保留已完成进度，并在当前进程内通过有上限的指数退避与随机抖动重试。列举在开始时或流中途失败，也会暂停这两类作业。轮换选中的源位于正在迁移的池时先暂停，冲突解除后继续。每次重试重新解析当前身份与权限。等待或暂停的作业不是完成或失败报告，不会被终态报告清理器删除。管理员取消优先于队列和重试。

Push、Pull 和 Snowball 复制作业在必要的授权依赖或报告读取暂时不可用时（包括对象处理过程中发生的故障）也会通过 `pausedReason` 进入暂停，并在重试时从头重新扫描源端；详见[批量复制](/zh/administration/batch-framework-job-replicate/#silo-retry)。复制中途的其他故障仍遵循原有的有限对象重试，可能以失败结束。

启动发现作业时，清单列举或存储读取失败也会按有上限的退避重试。发现过程会记住已经入队的清单，避免后续扫描重新执行在等待期间已经结束的作业；取消状态会阻止旧扫描结果重新入队。已经不存在、格式损坏或版本不受支持的清单不会入队，后两类保留在磁盘上供检查。启动发现期间的存储故障恢复后，无需再次重启即可继续发现作业。

已完成作业在重启后仍保持完成，包括旧格式作业和完成后凭据过期或变更的作业。来自不记录提交者绑定的旧版本、且尚未完成的作业需要重新提交。新绑定定义和已授权进度报告采用旧执行器会拒绝的格式。这可以阻止旧程序接管这些记录，但不能保证混合版本集群安全：旧节点仍能接收和执行自己的旧格式作业。切换版本前停止提交，并排空或取消旧作业；仍有等待执行的授权作业时不要降级。

使用 [mcli batch status](/zh/reference/minio-mc/mc-batch-status/#silo-job-outcomes)（`20261109`）区分暂停、终态失败和仍有受保护工作未处理的完成结果。`infraAdmin` 仍有其他基础设施管理能力，这些作业检查不把该角色变成严格的数据隔离边界。

## MinIO 批处理 CLI {#minio-cli}

- 安装 [MinIO Client](/zh/reference/minio-mc/#minio-client)
- 为 MinIO 部署定义一个 [`alias`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set)

[`mc batch`](/zh/reference/minio-mc/mc-batch/#command-mc.batch) 命令包括：

<table>
  <tbody>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a> 命令会为指定作业类型创建一个基础的 YAML 格式模板文件。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a> 命令根据批处理作业 YAML 文件启动一个批处理作业。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a> 命令会输出部署中当前正在进行的批处理作业列表。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a> 命令会输出 MinIO 服务器上作业事件的汇总信息。</p><aside class="alert alert-info"><p><strong>变更: mc</strong></p><p>RELEASE.2024-07-03T20-17-25Z</p><p>Batch status 会显示活动且正在进行的作业，或前 3（三）天内已完成的任意批处理作业的汇总信息。</p></aside></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a> 命令会输出指定作业 ID 的作业定义。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>mc batch cancel</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>mc batch cancel</code></a> 可停止正在进行的批处理作业。</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-batch-framework-access"></a>

## `mc batch` 的访问权限 {#access-to-mc-batch}

提交身份需要相应的管理动作权限，以及作业需要的本地 [数据权限](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。定义中的凭据还必须具备远端操作所需的权限。下一个版本的具体规则见上文。

执行批处理作业的用户必须具有以下权限。 也可以通过阻止或限制对这些操作的访问，来限制用户使用这些功能：

**`admin:ListBatchJobs`**

> 授予用户查看当前正在处理的批处理作业的能力。

**`admin:DescribeBatchJobs`**

> 授予用户查看当前正在处理的批处理作业定义详情的能力。

**`admin:StartBatchJob`**

> 授予用户启动批处理作业的能力。 该作业还可能受到其用于访问源部署或目标部署的凭证进一步限制。

**`admin:CancelBatchJob`**

> 允许用户停止当前正在进行的批处理作业。

可以将这些操作中的任意一个单独分配给用户，也可以任意组合分配。

内置的 `ConsoleAdmin` 策略包含执行所有这些类型批处理作业操作所需的充分访问权限。

<a id="minio-batch-local"></a>

## `Local` 部署 {#local}

可通过向 [`mc batch`](/zh/reference/minio-mc/mc-batch/#command-mc.batch) 命令传递一个 `alias`，对特定部署运行批处理作业。 命令中指定的部署会在该批处理作业的上下文中成为 `local` 部署。
