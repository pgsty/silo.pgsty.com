---
title: "设置概览"
url: "/zh/reference/minio-server/settings/"
weight: 10
icon: fa-solid fa-gears
minio_origin: true
silo_modified: false
---

<a id="minio-server-configuration-settings"></a>
<a id="minio-server-environment-variables"></a>
<a id="minio-environment-variables"></a>
<a id="id1"></a>

[`minio server`](/zh/reference/minio-server/#command-minio.server) 进程将其配置存储在存储后端 [`directory`](/zh/reference/minio-server/#minio.server.DIRECTORIES) 中。

<a id="minio-server-configuration-options"></a>

## MinIO 设置 {#minio}

MinIO 设置定义 MinIO [`server`](/zh/reference/minio-server/#command-minio.server) 进程的运行时行为。

你可以通过以下方式建立或修改设置：

- 在启动或重启 MinIO Server 之前，在宿主机系统上定义 *环境变量*。 如何定义环境变量，请参考所用操作系统的文档。
- 使用 [`mc admin config set`](/zh/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) 定义 *配置项*。

如果同时定义了环境变量和对应的配置项，MinIO 使用环境变量的值。

有些设置只有环境变量或配置项中的一种，而不是两者同时存在。

{{% alert color="warning" %}}
**重要**

每个配置项都会控制 MinIO 的基础行为和功能。 MinIO **强烈建议** 先在 DEV 或 QA 等较低级别环境中测试配置变更，再应用到生产环境。
{{% /alert %}}

其他可用于自定义的设置包括：

- [核心设置](/zh/reference/minio-server/settings/core/#minio-server-envvar-core)
- [Root 凭证](/zh/reference/minio-server/settings/root-credentials/#minio-server-envvar-root)
- [存储类](/zh/reference/minio-server/settings/storage-class/#minio-server-envvar-storage-class)
- [MinIO Console](/zh/reference/minio-server/settings/console/#minio-server-envvar-console)
- [指标与日志](/zh/reference/minio-server/settings/metrics-and-logging/#minio-server-envvar-metrics-logging)
- 用于 [MinIO 存储桶通知](/zh/administration/monitoring/bucket-notifications/#minio-bucket-notifications) 的 [通知目标](/zh/reference/minio-server/settings/notifications/#minio-server-envvar-notifications)
- [身份与访问管理方案](/zh/reference/minio-server/settings/iam/#minio-server-envvar-iam)
- [Key Encryption Service (KES)](/zh/reference/minio-server/settings/kes/#minio-server-envvar-kes)
- [Object Lambda 函数](/zh/reference/minio-server/settings/object-lambda/#minio-server-envvar-object-lambda-webhook)
