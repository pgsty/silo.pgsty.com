---
title: "Bucket Notifications Settings"
url: "/reference/minio-server/settings/notifications/"
weight: 70
icon: fa-solid fa-bell
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications.rst
upstream_modified: false
---

<a id="bucket-notifications-settings"></a>
<a id="minio-server-config-logging-logs"></a>
<a id="minio-server-envvar-notifications"></a>

This page covers settings that control behavior related to [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Sync Events {#sync-events}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_API_SYNC_EVENTS` {#envvar.MINIO_API_SYNC_EVENTS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `api sync_events` {#mc-conf.api.sync_events}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Enables synchronous [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Specify `on` to direct MinIO to wait until the remote target returns success on receipt of an event before processing further events.

Defaults to `off`, or asynchronous bucket notifications where MinIO does not wait for the remote target to return success on receipt of an event.

## Supported Notification Targets {#supported-notification-targets}

Notifications require a target to receive the events. MinIO supports a variety of possible targets. Settings for each target type have their own pages. Select the appropriate link below for the type of target you use for notifications.

- [AMQP Notification Settings](/reference/minio-server/settings/notifications/amqp/#minio-server-envvar-bucket-notification-amqp)
- [Elasticsearch Notification Settings](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-envvar-bucket-notification-elasticsearch)
- [Kafka Notification Settings](/reference/minio-server/settings/notifications/kafka/#minio-server-envvar-bucket-notification-kafka)
- [MQTT Notification Settings](/reference/minio-server/settings/notifications/mqtt/#minio-server-envvar-bucket-notification-mqtt)
- [MySQL Notification Settings](/reference/minio-server/settings/notifications/mysql/#minio-server-envvar-bucket-notification-mysql)
- [NATS Notification Settings](/reference/minio-server/settings/notifications/nats/#minio-server-envvar-bucket-notification-nats)
- [NSQ Notification Settings](/reference/minio-server/settings/notifications/nsq/#minio-server-envvar-bucket-notification-nsq)
- [PostgreSQL Notification Settings](/reference/minio-server/settings/notifications/postgresql/#minio-server-envvar-bucket-notification-postgresql)
- [Redis Notification Settings](/reference/minio-server/settings/notifications/redis/#minio-server-envvar-bucket-notification-redis)
- [Webhook Service Notification Settings](/reference/minio-server/settings/notifications/webhook-service/#minio-server-envvar-bucket-notification-webhook)
