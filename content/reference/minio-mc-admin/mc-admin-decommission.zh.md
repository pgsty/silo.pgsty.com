---
title: "mc admin decommission"
url: "/zh/reference/minio-mc-admin/mc-admin-decommission/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-decommission.rst
upstream_modified: true
---

<a id="mc-admin-decommission"></a>
<a id="minio-mc-admin-decommission"></a>

<a id="command-mc.admin.decommission"></a>

<a id="id1" data-td-print-local></a>

## 语法 {#syntax}

[`mc admin decommission`](#command-mc.admin.decommission) 命令用于启动 MinIO [服务器池](/zh/operations/concepts/#minio-intro-server-pool) 的下线流程。下线流程适用于移除较旧的服务器池，这些服务器池的硬件能力或性能已不再满足要求， 或相较部署中的其他池表现不足。MinIO 会根据每个池可用空闲空间的比例，自动将数据从被下线 的池迁移到部署中其余的池。

有关服务器池下线的完整操作流程，请参阅 [退役 服务器池](/zh/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning)。

> [!NOTE]
> **下线是永久性的**
>
> 一旦 SILO 开始下线某个池，就会将该池标记为 *永久* 非活动状态（“draining”）。取消或以其他方式中断下线流程都 **不会** 将该池恢复为活动状态。
>
> 下线是一项重要的管理操作，执行前需要谨慎规划并核验目标容量。[`mcli admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 正式支持的目标服务端为 SILO；与未修改的上游 MinIO 保持尽最大努力兼容。

```shell
mc admin [GLOBALFLAGS] decommission start|status|cancel ALIAS TARGET
```

<a id="id2" data-td-print-local></a>

### 参数 {#parameters}

##### `start` {#mc.admin.decommission.start}

*mc-cmd*

*必需* 启动 [`TARGET`](#mc.admin.decommission.TARGET) 指定服务器池的下线流程。

必须指定 [`TARGET`](#mc.admin.decommission.TARGET)

##### `status` {#mc.admin.decommission.status}

*mc-cmd*

*必需* 返回指定 [`ALIAS`](#mc.admin.decommission.ALIAS) 上所有服务器池的下线状态：

- **Active** - 该池处于活动状态，且未计划下线。
- **Draining** - 该池当前正在下线。
- **Draining (Failed)** - 下线流程失败，需要手动重启流程。
- **Draining (Cancelled)** - 下线流程已被手动取消。

如果命令包含 [`TARGET`](#mc.admin.decommission.TARGET)，则在下线进行中时， 命令输出会包含数据迁移速率。

##### `cancel` {#mc.admin.decommission.cancel}

*mc-cmd*

*必需* 取消 [`TARGET`](#mc.admin.decommission.TARGET) 指定池上的进行中下线流程。

必须指定 [`TARGET`](#mc.admin.decommission.TARGET)。

取消下线流程不会使该池恢复为活动状态。最终仍必须完成下线流程并将该池从部署中移除。 可以再次对该池运行 [`mc admin decommission start`](#mc.admin.decommission.start) 以恢复流程。

##### `ALIAS` {#mc.admin.decommission.ALIAS}

*mc-cmd*

*必需* 要启动下线流程的 MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

##### `TARGET` {#mc.admin.decommission.TARGET}

*mc-cmd*

命令所操作服务器池的完整描述。例如：

```shell
https://minio-{01...04}.example.net:9000/mnt/disk{1...4}
```

<a id="id3" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。

## 行为说明 {#behavior}

在 [SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）中，存储池退役具备以下迁移安全保障：

- 迁移跨池纠删码布局不同的对象（[#261](https://github.com/pgsty/silo/issues/261)）、已被 ILM 判定过期的当前版本（[#265](https://github.com/pgsty/silo/issues/265)）以及跨池生命周期过期无法安全完成的版本（[#278](https://github.com/pgsty/silo/issues/278)）。
- 当其他存储池仍引用远端分层载荷时保留远端对象（[#306](https://github.com/pgsty/silo/issues/306)、[#308](https://github.com/pgsty/silo/issues/308)）；在存储池退役全部完成之前，必须保持已配置的远端存储层可用。
- 当单个存储桶无法完成迁移时，继续处理后续存储桶并保留显式取消能力（[#307](https://github.com/pgsty/silo/issues/307)）。

<a id="id4" data-td-print-local></a>

## 示例 {#examples}

有关服务器池下线的完整操作流程，请参阅 [退役 服务器池](/zh/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning)。
