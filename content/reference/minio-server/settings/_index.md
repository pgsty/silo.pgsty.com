---
title: "Settings Overview"
url: "/reference/minio-server/settings/"
weight: 10
icon: fa-solid fa-gears
minio_origin: true
silo_modified: false
---

<a id="settings-overview"></a>
<a id="minio-server-configuration-settings"></a>
<a id="minio-server-environment-variables"></a>
<a id="minio-environment-variables"></a>

The [`minio server`](/reference/minio-server/#command-minio.server) process stores its configuration in the storage backend [`directory`](/reference/minio-server/#minio.server.DIRECTORIES).

<a id="minio-server-configuration-options"></a>

## MinIO Settings {#minio-settings}

MinIO settings define runtime behavior of the MinIO [`server`](/reference/minio-server/#command-minio.server) process.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

Additional settings include those to customize:

- [Core settings](/reference/minio-server/settings/core/#minio-server-envvar-core)
- [Root credentials](/reference/minio-server/settings/root-credentials/#minio-server-envvar-root)
- [Storage class](/reference/minio-server/settings/storage-class/#minio-server-envvar-storage-class)
- [MinIO Console](/reference/minio-server/settings/console/#minio-server-envvar-console)
- [Metrics and logging](/reference/minio-server/settings/metrics-and-logging/#minio-server-envvar-metrics-logging)
- [Notification targets](/reference/minio-server/settings/notifications/#minio-server-envvar-notifications) for use with [MinIO Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications)
- [Identity and access management solutions](/reference/minio-server/settings/iam/#minio-server-envvar-iam)
- [Key Encryption Service (KES)](/reference/minio-server/settings/kes/#minio-server-envvar-kes)
- [Object Lambda functions](/reference/minio-server/settings/object-lambda/#minio-server-envvar-object-lambda-webhook)
