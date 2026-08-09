---
title: "ILM Settings"
url: "/reference/minio-server/settings/ilm/"
weight: 90
minio_origin: true
silo_modified: false
---

<a id="ilm-settings"></a>
<a id="minio-server-envvar-ilm"></a>

This page covers settings that control Information Lifecycle Management (ILM) for the MinIO process.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Expiration Workers {#expiration-workers}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

#### `MINIO_ILM_EXPIRATION_WORKERS` {#envvar.MINIO_ILM_EXPIRATION_WORKERS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

#### `ilm expiration_workers` {#mc-conf.ilm.expiration_workers}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="info" %}}
**Added: MinIO**

Server RELEASE.2024-03-03T17-50-39Z
{{% /alert %}}

Set the number of workers to use for [expiring objects](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration). Valid values are `1` to `500`.

The default value is `100`.
