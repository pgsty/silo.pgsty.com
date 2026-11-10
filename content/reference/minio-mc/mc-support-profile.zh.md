---
title: "mc support profile"
url: "/zh/reference/minio-mc/mc-support-profile/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-profile.rst
upstream_modified: true
---

**SILO 行为：** `mc support` 诊断在本地直接对 SILO 运行，不要求 SUBNET 订阅，也不会自动上传。`mc license info` 与 `unregister` 仅操作本地状态，`license update` 保留显式文件方式；在线注册、续订与上传均已禁用。下文保留的上游语法不会启用这些在线服务。见 [mcli 兼容性](/zh/compatibility/mcli/#subnet)。

<a id="mc-support-profile"></a>

<a id="command-mc.support.profile"></a>

<a id="id2" data-td-print-local></a>

## 描述 {#description}

[`mc support profile`](#command-mc.support.profile) 为你的部署运行系统性能剖析。 剖析结果可帮助了解给定节点上运行的 MinIO 服务端进程状态。

诊断产物保存在本地；SUBNET 在线服务已禁用。兼容参数不会启用上传。

<a id="id3" data-td-print-local></a>

## 示例 {#examples}

<a id="cpu" data-td-print-local></a>

### 获取 CPU 剖析 {#fetch-cpu-profiling}

此命令从别名为 `minio1` 的 MinIO 部署中获取 CPU 剖析数据。 剖析按默认时长运行 10 秒。

```shell
mc support profile --type cpu minio1/
```

<a id="cpu-block" data-td-print-local></a>

### 并发获取 CPU、内存和 block 剖析 {#fetch-cpu-memory-and-block-profiling-concurrently}

此命令从别名 `minio2` 获取 CPU、内存和 block 使用情况的剖析数据。 剖析按默认时长运行 10 秒。

```shell
mc support profile --type cpu,mem,block minio2/
```

<a id="cpu-block-10" data-td-print-local></a>

### 并发获取 CPU、内存和 block 剖析（持续 10 分钟） {#fetch-cpu-memory-and-block-profiling-concurrently-for-10-minutes}

此命令从别名 `minio3` 获取 CPU、内存和 block 的剖析数据。 剖析运行 10 分钟（600 秒）。

```shell
mc support profile --type cpu,mem,block --duration 600 minio3/
```

<a id="id4" data-td-print-local></a>

## 语法 {#syntax}

[`mc support profile`](#command-mc.support.profile) 命令语法如下：

```shell
mc [GLOBALFLAGS] support profile       \
                         COMMAND       \
                         [--type]      \
                         [--airgap]    \
                         [--duration]  \
                         ALIAS
```

<a id="id5" data-td-print-local></a>

### 参数 {#parameters}

##### `--duration` {#mc.support.profile.-duration}

*mc-cmd*

*Optional*

按指定时长运行剖析，单位为秒。

使用 `--duration <value>`，其中 `<value>` 为剖析运行的秒数。

如果未指定，命令将收集 10 秒的数据。

##### `--type` {#mc.support.profile.-type}

*mc-cmd*

*Optional*

指定要收集数据的剖析类型。

使用 `--type <value>`，其中 `<value>` 为一个或多个以逗号分隔的数据类型。

有效类型包括：

- `cpu`
- `cpuio`
- `mem`
- `block`
- `mutex`
- `trace`
- `threads`
- `goroutines`

如果未指定，命令将收集 CPU、memory、block、mutex、threads 和 goroutines 的数据。

> [!WARNING]
> **重要**
>
> 在生产部署上请谨慎使用 `cpuio` 与 `trace` 剖析类型。这两种剖析会消耗大量 CPU 与 I/O 资源，运行期间可能导致集群性能下降。

##### `--airgap` {#mc.support.profile.-airgap}

*mc-cmd*

*Optional*

诊断产物保存在本地；SUBNET 在线服务已禁用。兼容参数不会启用上传。

如果部署是 airgapped，但你运行 [minio client](/zh/reference/minio-mc/#minio-client) 的本地设备具有网络访问能力，则无需使用 `--airgap` 标志。

##### `ALIAS` {#mc.support.profile.ALIAS}

*mc-cmd*

*Required*

MinIO 部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。

<a id="id6" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。
