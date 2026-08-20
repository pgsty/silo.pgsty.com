---
title: "NSQ Notification Settings"
url: "/reference/minio-server/settings/notifications/nsq/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications/nsq.rst
upstream_modified: false
---

<a id="nsq-notification-settings"></a>
<a id="minio-server-config-bucket-notification-nsq"></a>
<a id="minio-server-envvar-bucket-notification-nsq"></a>

This page documents settings for configuring an NSQ service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to NSQ](/administration/monitoring/publish-events-to-nsq/#minio-bucket-notifications-publish-nsq) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Multiple NSQ Targets {#multiple-nsq-targets}

You can specify multiple NSQ service endpoints by appending a unique identifier `_ID` to the end of the top level key for each set of related NSQ settings. For example, the following commands set two distinct NSQ service endpoints as `PRIMARY` and `SECONDARY` respectively:

```shell {tab="Environment Variables" group="environment-variables-configuration-settings" value="environment-variables"}
export MINIO_NOTIFY_NSQ_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_NSQ_NSQD_ADDRESS_PRIMARY="https://user:password@nsq-endpoint.example.net:9200"
export MINIO_NOTIFY_NSQ_TOPIC_PRIMARY="bucketevents"

export MINIO_NOTIFY_NSQ_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_NSQ_NSQD_ADDRESS_SECONDARY="https://user:password@nsq-endpoint.example.net:9200"
export MINIO_NOTIFY_NSQ_TOPIC_SECONDARY="bucketevents"
```

```shell {tab="Configuration Settings" value="configuration-settings"}
mc admin config set notify_nsq:primary \
   nsqd_address="ENDPOINT" \
   topic="<string>" \
   [ARGUMENT="VALUE"] ... \

mc admin config set notify_nsq:secondary \
   nsqd_address="ENDPOINT" \
   topic="<string>" \
   [ARGUMENT="VALUE"] ... \
```

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_ENABLE` {#envvar.MINIO_NOTIFY_NSQ_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to an NSQ endpoint.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq` {#mc-conf.notify_nsq}

*mc-conf*

The top-level configuration key for defining an NSQ server/broker endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an NSQ server/broker endpoint. The following arguments are *required* for each endpoint:

- [`nsqd_address`](#mc-conf.notify_nsq.nsqd_address)
- [`topic`](#mc-conf.notify_nsq.topic)

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_nsq                          \
   nsqd_address="https://nsq-endpoint.example.net:4150" \
   topic="<string>"                                     \
   [ARGUMENT="VALUE"] ...
```
{{< /tab >}}
{{< /tabs >}}

### NSQ Daemon Server Address {#nsq-daemon-server-address}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_NSQD_ADDRESS` {#envvar.MINIO_NOTIFY_NSQ_NSQD_ADDRESS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq nsqd_address` {#mc-conf.notify_nsq.nsqd_address}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the NSQ server address where the NSQ Daemon runs. For example:

`https://nsq-endpoint.example.net:4150`

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.

### Topic {#topic}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_TOPIC` {#envvar.MINIO_NOTIFY_NSQ_TOPIC}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq topic` {#mc-conf.notify_nsq.topic}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the name of the NSQ topic MinIO uses when publishing events to the broker.

### TLS {#tls}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_TLS` {#envvar.MINIO_NOTIFY_NSQ_TLS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq tls` {#mc-conf.notify_nsq.tls}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable TLS connectivity to the NSQ service broker.

### TLS Skip Verify {#tls-skip-verify}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_TLS_SKIP_VERIFY` {#envvar.MINIO_NOTIFY_NSQ_TLS_SKIP_VERIFY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq tls_skip_verify` {#mc-conf.notify_nsq.tls_skip_verify}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Enables or disables TLS verification of the NSQ service broker TLS certificates.

- Specify `on` to disable TLS verification (Default).
- Specify `off` to enable TLS verification.

### Queue Directory {#queue-directory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_QUEUE_DIR` {#envvar.MINIO_NOTIFY_NSQ_QUEUE_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq queue_dir` {#mc-conf.notify_nsq.queue_dir}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the NSQ server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_NSQ_QUEUE_LIMIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq queue_limit` {#mc-conf.notify_nsq.queue_limit}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NSQ_COMMENT` {#envvar.MINIO_NOTIFY_NSQ_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nsq comment` {#mc-conf.notify_nsq.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate with the NSQ configuration.
