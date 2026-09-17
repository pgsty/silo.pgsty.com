---
title: "纠删码设置"
url: "/zh/reference/minio-server/settings/storage-class/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/storage-class.rst
upstream_modified: true
math: true
---

<a id="minio-ec-storage-class"></a>
<a id="minio-server-envvar-storage-class"></a>
<a id="id1"></a>

本页介绍用于配置写入 MinIO 集群对象时所使用 [纠删码](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) [校验](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 的相关设置。 这会影响 MinIO 如何使用驱动器空间，以及 MinIO 如何在驱动器丢失或类似问题发生时恢复已存储对象。

你可以通过以下方式建立或修改设置：

- 在启动或重启 MinIO Server 之前，在宿主机系统上定义 *环境变量*。 如何定义环境变量，请参考所用操作系统的文档。
- 使用 [`mc admin config set`](/zh/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) 定义 *配置项*。

如果同时定义了环境变量和对应的配置项，MinIO 使用环境变量的值。

有些设置只有环境变量或配置项中的一种，而不是两者同时存在。

> [!WARNING]
> **重要**
>
> 每个配置项都会控制 MinIO 的基础行为和功能。 MinIO **强烈建议** 先在 DEV 或 QA 等较低级别环境中测试配置变更，再应用到生产环境。

<a id="id3"></a>

## 标准存储类 {#minio-ec-storage-class-standard}

> [!NOTE]
> **说明**
>
> *MinIO Storage Classes* 与 *AWS Storage Classes* 不同。
>
> AWS Storage Classes 指将给定对象存储到的特定存储层级，例如 `hot` 或 `glacier` 存储。 MinIO Storage Classes 会影响所使用的纠删码校验设置，并与对象的 [可用性与韧性](/zh/operations/concepts/availability-and-resiliency/#minio-availability-resiliency) 相关。
>
> 如需在不同类型存储之间分层（例如用于成本管理），请参见 [对象迁移（”Tiering”）](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering)。

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_STORAGE_CLASS_STANDARD` {#envvar.MINIO_STORAGE_CLASS_STANDARD}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `storage_class standard` {#mc-conf.storage_class.standard}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

该部署的 [parity level](/zh/operations/concepts/erasure-coding/#minio-ec-parity)。 MinIO 会使用该校验值对采用默认 `STANDARD` 存储类写入的对象进行分片。

MinIO 会参考请求元数据中的 `x-amz-storage-class` 头，以确定应为对象分配哪个存储类。 设置该头的具体语法或方式取决于与 MinIO 服务器交互时所使用的方法。

请使用 `EC:M` 记法指定该值，其中 `M` 表示要为对象创建的校验块数量。

下表列出了基于部署中初始服务器池 [erasure set size](/zh/operations/concepts/erasure-coding/#minio-ec-erasure-set) 的默认值：

| 纠删集合大小 | 默认校验 (EC:M) |
| --- | --- |
| 1 | EC:0 |
| 2-3 | EC:1 |
| 4-5 | EC:2 |
| 6 - 7 | EC:3 |
| 8 - 16 | EC:4 |

`2–3` 这一行表示默认校验值相同，不表示写入可用性相同。采用 `EC:1` 时，双盘集合的读仲裁为 1、写仲裁为 2；三盘集合的读写仲裁均为 2。因此，双盘集合失去一盘后无法继续写入。单盘 `EC:0` 不提供纠删码冗余。参见 [纠删码说明](/zh/operations/concepts/erasure-coding/#minio-ec-basics)。

支持的最小值是 `0`，表示不提供纠删码保护。 此类部署的可用性/韧性完全依赖底层存储控制器或存储资源。

最大值取决于部署中初始服务器池的纠删集合大小 `N`，其上限为 `floor(N/2)`。 例如，纠删集合条带大小为 16 的部署，其标准校验最大值为 8。

可在启动后将该值更改为 `0` 与该纠删集合大小上限之间的任意值。 MinIO 只会将变更后的校验值应用于新写入对象。 现有对象会保留其创建时的校验值。

## 降低冗余存储类 {#id4}

> [!NOTE]
> **说明**
>
> *MinIO Storage Classes* 与 *AWS Storage Classes* 不同。
>
> AWS Storage Classes 指将给定对象存储到的特定存储层级，例如 `hot` 或 `glacier` 存储。 MinIO Storage Classes 会影响所使用的纠删码校验设置，并与对象的 [可用性与韧性](/zh/operations/concepts/availability-and-resiliency/#minio-availability-resiliency) 相关。
>
> 如需在不同类型存储之间分层（例如用于成本管理），请参见 [对象迁移（”Tiering”）](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering)。

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_STORAGE_CLASS_RRS` {#envvar.MINIO_STORAGE_CLASS_RRS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `storage_class rrs` {#mc-conf.storage_class.rrs}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

用于以 `REDUCED` 存储类写入对象的 [parity level](/zh/operations/concepts/erasure-coding/#minio-ec-parity)。

MinIO 会参考请求元数据中的 `x-amz-storage-class` 头，以确定应为对象分配哪个存储类。 设置该头的具体语法或方式取决于与 MinIO 服务器交互时所使用的方法。

请使用 `EC:M` 记法指定该值，其中 `M` 表示要为对象创建的校验块数量。

当该值与 [`MINIO_STORAGE_CLASS_STANDARD`](#envvar.MINIO_STORAGE_CLASS_STANDARD) 都非零时，该值 **必须** 小于或等于 `STANDARD` 的校验值；两者允许相等。

对于纠删集合大小小于 2 的部署，不能设置此值。 纠删集合大小大于 1 的部署默认值为 `EC:1`。 纠删集合大小为 1 的部署默认值为 `EC:0`。

## 校验保留优化 {#id5}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_STORAGE_CLASS_OPTIMIZE` {#envvar.MINIO_STORAGE_CLASS_OPTIMIZE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `storage_class optimize` {#mc-conf.storage_class.optimize}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

默认的 `availability` 设置允许 SILO 在目标纠删集合有磁盘离线时提高新对象的校验值；对于 `N` 盘集合，上限为 `floor(N/2)` 个校验分片。写入仍须满足最终分片布局对应的写仲裁。这可以增加新对象的冗余，但不能保证故障前后的可用性不变。尤其是双盘 `EC:1` 集合，失去一盘后无法依靠校验升级继续写入。

将该设置指定为 `capacity`，可指示 MinIO 不为对象创建任何额外校验。 这会优先保障集群总体容量，但代价是当该纠删集合中更多驱动器故障时，对象可用性可能降低。

## 注释 {#id6}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_STORAGE_CLASS_COMMENT` {#envvar.MINIO_STORAGE_CLASS_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
此设置没有对应的配置项。
{{< /tab >}}
{{< /tabs >}}

为存储类设置添加注释。
