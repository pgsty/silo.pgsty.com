---
title: "MQTT Notification Settings"
url: "/reference/minio-server/settings/notifications/mqtt/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications/mqtt.rst
upstream_modified: false
---

<a id="mqtt-notification-settings"></a>
<a id="minio-server-config-bucket-notification-mqtt"></a>
<a id="minio-server-envvar-bucket-notification-mqtt"></a>

This page documents settings for configuring an MQTT service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to MQTT](/administration/monitoring/publish-events-to-mqtt/#minio-bucket-notifications-publish-mqtt) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Multiple MQTT Targets {#multiple-mqtt-targets}

You can specify multiple MQTT service endpoints by appending a unique identifier `_ID` for each set of related MQTT settings to the top level key. For example, the following commands set two distinct MQTT service endpoints as `PRIMARY` and `SECONDARY`, respectively:

```shell {tab="Environment Variables" group="environment-variables-configuration-setting" value="environment-variables"}
export MINIO_NOTIFY_MQTT_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_MQTT_BROKER_PRIMARY="tcp://user:password@mqtt-endpoint.example.net:1883"

export MINIO_NOTIFY_MQTT_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_MQTT_BROKER_SECONDARY="tcp://user:password@mqtt-endpoint.example.net:1883"
```

```shell {tab="Configuration Setting" value="configuration-setting"}
mc admin config set notify_mqtt:primary \
   broker="tcp://endpoint:port" \
   topic="minio/bucket-name/events/" \
   username="username" \
   password="password" \
   [ARGUMENT="VALUE"] ... \

mc admin config set notify_mqtt:secondary \
   broker="tcp://endpoint:port" \
   topic="minio/bucket-name/events/" \
   username="username" \
   password="password" \
   [ARGUMENT="VALUE"] ... \
```

With these settings, [`MINIO_NOTIFY_MQTT_ENABLE_PRIMARY`](#envvar.MINIO_NOTIFY_MQTT_ENABLE) indicates the environment variable is associated to an MQTT service endpoint with an ID of `PRIMARY`.

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_ENABLE` {#envvar.MINIO_NOTIFY_MQTT_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to an MQTT endpoint.

Defaults to `off`.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt` {#mc-conf.notify_mqtt}

*mc-conf*

The top-level configuration key for defining an MQTT server/broker endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an MQTT server/broker endpoint. The following arguments are *required* for each endpoint:

- [`broker`](#mc-conf.notify_mqtt.broker)
- [`topic`](#mc-conf.notify_mqtt.topic)
- [`username`](#mc-conf.notify_mqtt.username) *Optional if MQTT server/broker does not enforce authentication/authorization*
- [`password`](#mc-conf.notify_mqtt.password) *Optional if MQTT server/broker does not enforce authentication/authorization*

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_mqtt \
   broker="tcp://endpoint:port" \
   topic="minio/bucket-name/events/" \
   username="username" \
   password="password" \
   [ARGUMENT="VALUE"] ... \
```
{{< /tab >}}
{{< /tabs >}}

### Broker {#broker}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_BROKER` {#envvar.MINIO_NOTIFY_MQTT_BROKER}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt broker` {#mc-conf.notify_mqtt.broker}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the MQTT server/broker endpoint. MinIO supports TCP, TLS, or Websocket connections to the server/broker URL. For example:

- `tcp://mqtt.example.net:1883`
- `tls://mqtt.example.net:1883`
- `ws://mqtt.example.net:1883`

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.

### Topic {#topic}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_TOPIC` {#envvar.MINIO_NOTIFY_MQTT_TOPIC}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt topic` {#mc-conf.notify_mqtt.topic}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the name of the MQTT topic to associate with events published by MinIO to the MQTT endpoint.

### Username {#username}

*Required if the MQTT server/broker enforces authentication/authorization*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_USERNAME` {#envvar.MINIO_NOTIFY_MQTT_USERNAME}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt username` {#mc-conf.notify_mqtt.username}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the MQTT username MinIO should use to authenticate to the MQTT server/broker.

### Password {#password}

*Required if the MQTT server/broker enforces authentication/authorization*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_PASSWORD` {#envvar.MINIO_NOTIFY_MQTT_PASSWORD}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt password` {#mc-conf.notify_mqtt.password}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the password for the MQTT username MinIO uses to authenticate to the MQTT server/broker.

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).

### Quality of Service {#quality-of-service}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_QOS` {#envvar.MINIO_NOTIFY_MQTT_QOS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt qos` {#mc-conf.notify_mqtt.qos}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the Quality of Service priority for the published events.

Defaults to `0`.

### Keep Alive Interval {#keep-alive-interval}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_KEEP_ALIVE_INTERVAL` {#envvar.MINIO_NOTIFY_MQTT_KEEP_ALIVE_INTERVAL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt keep_alive_interval` {#mc-conf.notify_mqtt.keep_alive_interval}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the keep-alive interval for the MQTT connections. MinIO supports the following units of time measurement:

- `s` - seconds, “60s”
- `m` - minutes, “60m”
- `h` - hours, “24h”
- `d` - days, “7d”

### Reconnect Interval {#reconnect-interval}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_RECONNECT_INTERVAL` {#envvar.MINIO_NOTIFY_MQTT_RECONNECT_INTERVAL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt reconnect_interval` {#mc-conf.notify_mqtt.reconnect_interval}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the reconnect interval for the MQTT connections. MinIO supports the following units of time measurement:

- `s` - seconds, “60s”
- `m` - minutes, “60m”
- `h` - hours, “24h”
- `d` - days, “7d”

### Queue Directory {#queue-directory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_QUEUE_DIR` {#envvar.MINIO_NOTIFY_MQTT_QUEUE_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt queue_dir` {#mc-conf.notify_mqtt.queue_dir}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the MQTT server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_MQTT_QUEUE_LIMIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt queue_limit` {#mc-conf.notify_mqtt.queue_limit}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_MQTT_COMMENT` {#envvar.MINIO_NOTIFY_MQTT_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_mqtt comment` {#mc-conf.notify_mqtt.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate with the MQTT configuration.
