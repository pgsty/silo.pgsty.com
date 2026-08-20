---
title: "AMQP Notification Settings"
url: "/reference/minio-server/settings/notifications/amqp/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications/amqp.rst
upstream_modified: false
---

<a id="amqp-notification-settings"></a>
<a id="minio-server-config-bucket-notification-amqp"></a>
<a id="minio-server-envvar-bucket-notification-amqp"></a>

This page documents settings for configuring an AMQP service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to AMQP (RabbitMQ)](/administration/monitoring/publish-events-to-amqp/#minio-bucket-notifications-publish-amqp) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Multiple AMQP Targets {#multiple-amqp-targets}

You can specify multiple AMQP service endpoints by appending a unique identifier `_ID` for each set of related AMQP settings to the top level key.

### Examples {#examples}

For example, the following commands set two distinct AMQP service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
```shell
export MINIO_NOTIFY_AMQP_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_AMQP_URL_PRIMARY="amqp://user:password@amqp-endpoint.example.net:5672"

export MINIO_NOTIFY_AMQP_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_AMQP_URL_SECONDARY="amqp://user:password@amqp-endpoint.example.net:5672"
```

For example, [`MINIO_NOTIFY_AMQP_ENABLE_PRIMARY`](#envvar.MINIO_NOTIFY_AMQP_ENABLE) indicates the environment variable is associated to an AMQP service endpoint with ID of `PRIMARY`.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
```shell
mc admin config set notify_amqp:primary \
   url="user:password@amqp://amqp-endpoint.example.net:5672" [ARGUMENT=VALUE ...]

mc admin config set notify_amqp:secondary \
   url="user:password@amqp://amqp-endpoint.example.net:5672" [ARGUMENT=VALUE ...]
```

Notice that for configuration settings, the unique identifier appends to `amqp` only, not to each individual argument.
{{< /tab >}}
{{< /tabs >}}

## Settings {#settings}

### Enable {#enable}

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_ENABLE` {#envvar.MINIO_NOTIFY_AMQP_ENABLE}

*envvar*

Requires specifying [`MINIO_NOTIFY_AMQP_URL`](#envvar.MINIO_NOTIFY_AMQP_URL) if set to `on`.

Specify `on` to enable publishing bucket notifications to an AMQP endpoint.

Defaults to `off`.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp` {#mc-conf.notify_amqp}

*mc-conf*

The top-level configuration key for defining an AMQP service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an AMQP service endpoint. The [`url`](#mc-conf.notify_amqp.url) argument is *required* for each target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_amqp \
  url="amqp://user:password@endpoint:port" \
  [ARGUMENT="VALUE"] ...
```
{{< /tab >}}
{{< /tabs >}}

### URL {#url}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_URL` {#envvar.MINIO_NOTIFY_AMQP_URL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp url` {#mc-conf.notify_amqp.url}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the AMQP server endpoint to which MinIO publishes bucket events. For example, `amqp://myuser:mypassword@localhost:5672`.

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.

### Exchange {#exchange}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_EXCHANGE` {#envvar.MINIO_NOTIFY_AMQP_EXCHANGE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp exchange` {#mc-conf.notify_amqp.exchange}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the name of the AMQP exchange to use.

### Exchange Type {#exchange-type}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_EXCHANGE_TYPE` {#envvar.MINIO_NOTIFY_AMQP_EXCHANGE_TYPE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp exchange_type` {#mc-conf.notify_amqp.exchange_type}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the type of the AMQP exchange.

### Routing Key {#routing-key}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_ROUTING_KEY` {#envvar.MINIO_NOTIFY_AMQP_ROUTING_KEY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp routing_key` {#mc-conf.notify_amqp.routing_key}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the routing key for publishing events.

### Mandatory {#mandatory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_MANDATORY` {#envvar.MINIO_NOTIFY_AMQP_MANDATORY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp mandatory` {#mc-conf.notify_amqp.mandatory}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `off` to ignore undelivered messages errors. Defaults to `on`.

### Durable {#durable}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_DURABLE` {#envvar.MINIO_NOTIFY_AMQP_DURABLE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp durable` {#mc-conf.notify_amqp.durable}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to persist the message queue across broker restarts. Defaults to `off`.

### No Wait {#no-wait}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_NO_WAIT` {#envvar.MINIO_NOTIFY_AMQP_NO_WAIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp no_wait` {#mc-conf.notify_amqp.no_wait}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable non-blocking message delivery. Defaults to `off`.

### Internal {#internal}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_INTERNAL` {#envvar.MINIO_NOTIFY_AMQP_INTERNAL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp internal` {#mc-conf.notify_amqp.internal}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to use the exchange only if it is bound to other exchanges. See the RabbitMQ documentation on [Exchange to Exchange Bindings](https://www.rabbitmq.com/e2e.html) for more information on AMQP exchange binding.

### Auto Deleted {#auto-deleted}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_AUTO_DELETED` {#envvar.MINIO_NOTIFY_AMQP_AUTO_DELETED}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp auto_deleted` {#mc-conf.notify_amqp.auto_deleted}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to automatically delete the message queue if there are no consumers. Defaults to `off`.

### Delivery Mode {#delivery-mode}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_DELIVERY_MODE` {#envvar.MINIO_NOTIFY_AMQP_DELIVERY_MODE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp delivery_mode` {#mc-conf.notify_amqp.delivery_mode}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `1` for set the delivery mode to non-persistent queue.

Specify `2` to set the delivery mode to persistent queue.

### Queue Directory {#queue-directory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_QUEUE_DIR` {#envvar.MINIO_NOTIFY_AMQP_QUEUE_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp queue_dir` {#mc-conf.notify_amqp.queue_dir}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the AMQP service is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_AMQP_QUEUE_LIMIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp queue_limit` {#mc-conf.notify_amqp.queue_limit}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_AMQP_COMMENT` {#envvar.MINIO_NOTIFY_AMQP_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_amqp comment` {#mc-conf.notify_amqp.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment for the AMQP configuration.
