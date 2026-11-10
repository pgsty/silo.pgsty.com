---
title: "mc admin rebalance"
url: "/zh/reference/minio-mc-admin/mc-admin-rebalance/"
weight: 130
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-rebalance.rst
upstream_modified: true
---

<a id="mc-admin-rebalance"></a>
<a id="minio-mc-admin-rebalance"></a>

<a id="command-mc.admin.rebalance"></a>

<a id="id2" data-td-print-local></a>

## 权限 {#permission}

执行此命令的用户必须拥有该部署的 [`admin:Rebalance`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-Rebalance) [策略操作](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)。

<a id="id3" data-td-print-local></a>

## 描述 {#description}

[`mc admin rebalance`](#command-mc.admin.rebalance) 命令可用于在 MinIO 部署上启动、监控或停止再平衡操作。 再平衡会在部署中的所有池之间重新分配对象。

当新增 服务器池 时，MinIO 不会自动对对象执行再平衡。 相反，MinIO 会将 [新对象写入](/zh/operations/deployments/baremetal-expand-minio-deployment/#minio-writing-files) 相较于部署中其他可用池可用空间更多的池。 触发手动再平衡流程会促使 MinIO 扫描整个部署，并按需移动对象，以使所有池的可用空间大致相当。

这是一项开销大且耗时的操作。 建议仅在部署负载较轻或空闲时运行再平衡流程。 如果在再平衡期间发生写操作，这些写操作会并行处理，并写入当前未参与再平衡的池。

你可以停止再平衡，并在之后按需重新启动。

使用以下命令跟踪正在进行的再平衡操作进度：

```shell
mc admin trace --call rebalance ALIAS
```

> [!NOTE]
> **服务端兼容性**
>
> [`mcli admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 正式支持的目标服务端为 SILO。与未修改的上游 MinIO 保持尽最大努力兼容；仅具备通用 S3 兼容性并不提供这些管理 API。

[`mc admin rebalance`](#command-mc.admin.rebalance) 命令具有以下子命令：

| 子命令                                                    | 说明                                 |
| --------------------------------------------------------- | ------------------------------------ |
| [`mc admin rebalance start`](#mc.admin.rebalance.start)   | 在 MinIO 部署上启动再平衡操作。      |
| [`mc admin rebalance status`](#mc.admin.rebalance.status) | 输出正在进行的再平衡操作的当前状态。 |
| [`mc admin rebalance stop`](#mc.admin.rebalance.stop)     | 停止正在进行中的再平衡操作。         |
{.wide .expand}

<a id="id4" data-td-print-local></a>

## 语法 {#syntax}

#### `mc admin rebalance start` {#mc.admin.rebalance.start}

*mc-cmd*

为 MinIO 部署启动再平衡操作。

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
假设一个 MinIO 部署有两个池，并分配了别名 `minio1`。 其中一个池有 250 GB 可用空间，另一个池有 3 TB 可用空间。

[`mc admin rebalance`](#command-mc.admin.rebalance) 命令会将对象从可用空间较少的池迁移到可用空间较多的池，使两个池的可用空间大致相等。

```shell
mc admin rebalance start minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] admin rebalance start ALIAS
```

- 将 ALIAS 替换为要执行再平衡的 MinIO 部署的 [别名](/zh/reference/minio-mc/mc-alias-set/#alias)。
{{< /tab >}}
{{< /tabs >}}

#### `mc admin rebalance status` {#mc.admin.rebalance.status}

*mc-cmd*

查询具有活动再平衡进程的部署，并返回该再平衡进程的状态信息。

状态输出包括再平衡操作 ID、操作时间，以及部署中每个池的详细信息。 对每个池，状态会显示池 ID、该池的再平衡状态、已用空间百分比以及该池的再平衡进度。

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
```shell
mc admin rebalance status minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] admin rebalance ALIAS
```

- 将 ALIAS 替换为 MinIO 部署的 [别名](/zh/reference/minio-mc/mc-alias-set/#alias)。
{{< /tab >}}
{{< /tabs >}}

#### `mc admin rebalance stop` {#mc.admin.rebalance.stop}

*mc-cmd*

结束指定部署上正在进行中的再平衡任务。在 [SILO 20261109](/zh/blog/release/silo-20261109/) 中，当部署不存在再平衡元数据时，`mc admin rebalance stop` 会正常返回而不会触发 panic（[#270](https://github.com/pgsty/silo/issues/270)）。

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
```shell
mc admin rebalance stop minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
该命令的语法如下：

```shell
mc [GLOBALFLAGS] admin rebalance stop ALIAS
```

- 将 ALIAS 替换为 MinIO 部署的 [别名](/zh/reference/minio-mc/mc-alias-set/#alias)。
{{< /tab >}}
{{< /tabs >}}

<a id="id5" data-td-print-local></a>

## 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

<a id="id6" data-td-print-local></a>

## 行为 {#behavior}

<a id="id7" data-td-print-local></a>

### 先备份集群设置 {#back-up-cluster-settings-first}

在开始再平衡操作前，使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 和 [`mc admin cluster iam export`](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) 命令分别对存储桶元数据和 IAM 配置进行快照。必要时可使用这些快照恢复存储桶或 IAM 设置，以便从用户或进程错误中恢复。

<a id="deletemarker"></a>

### 删除标记、已过期版本与多池迁移 {#rebalance-multi-pool-safety}

SILO 再平衡**不会**丢弃删除标记，也不会在跨池生命周期状态尚未确认时静默跳过对象版本。保留删除标记与待确认版本可防止其他存储池中的旧版本在迁移期间或迁移后意外重新显现。

在 [SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）中，再平衡具备以下迁移安全行为：

- 跨存储池保留 `null` 与 UUID [删除标记](/zh/administration/object-management/object-versioning/#minio-bucket-versioning-delete)，而不是将其丢弃。
- 迁移跨池纠删码布局混合的对象（[#261](https://github.com/pgsty/silo/issues/261)）、已被 ILM 判定过期的当前版本（[#265](https://github.com/pgsty/silo/issues/265)）以及因缺少权威仲裁或锁保护状态无法安全执行跨池[生命周期](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration)过期而被拒绝删除的版本（[#278](https://github.com/pgsty/silo/issues/278)）。
- 单个存储桶迁移失败时继续处理其余存储桶，并保持取消能力（[#307](https://github.com/pgsty/silo/issues/307)）。
- 当不存在再平衡元数据时，`mc admin rebalance stop` 可安全处理而不再触发 panic（[#270](https://github.com/pgsty/silo/issues/270)）。
