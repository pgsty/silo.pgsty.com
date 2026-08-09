---
title: "Publish Events to MQTT"
url: "/administration/monitoring/publish-events-to-mqtt/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-mqtt"></a>
<a id="minio-bucket-notifications-publish-mqtt"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to [MQTT](https://www.mqtt.org/) server/broker endpoint.

## Add an MQTT Endpoint to a MinIO Deployment {#add-an-mqtt-endpoint-to-a-minio-deployment}

The following procedure adds a new MQTT service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### MQTT 3.1 or 3.1.1 Server/Broker {#mqtt-3-1-or-3-1-1-server-broker}

This procedure assumes an existing MQTT 3.1 or 3.1.1 server/broker to which the MinIO deployment has connectivity. See the [mqtt.org software listing](https://mqtt.org/software/) for a list of MQTT-compatible server/brokers.

If the MQTT service requires authentication, you *must* provide an appropriate username and password during the configuration process to grant MinIO access to the service.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the MQTT Endpoint to MinIO {#add-the-mqtt-endpoint-to-minio}

You can configure a new MQTT service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the MQTT service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/mqtt/#minio-server-envvar-bucket-notification-mqtt). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an MQTT service endpoint. The minimum *required* variables are:

- [`MINIO_NOTIFY_MQTT_ENABLE`](/reference/minio-server/settings/notifications/mqtt/#envvar.MINIO_NOTIFY_MQTT_ENABLE)
- [`MINIO_NOTIFY_MQTT_BROKER`](/reference/minio-server/settings/notifications/mqtt/#envvar.MINIO_NOTIFY_MQTT_BROKER)
- [`MINIO_NOTIFY_MQTT_TOPIC`](/reference/minio-server/settings/notifications/mqtt/#envvar.MINIO_NOTIFY_MQTT_TOPIC)
- [`MINIO_NOTIFY_MQTT_USERNAME`](/reference/minio-server/settings/notifications/mqtt/#envvar.MINIO_NOTIFY_MQTT_USERNAME) *Required if the MQTT server/broker enforces authentication/authorization*
- [`MINIO_NOTIFY_MQTT_PASSWORD`](/reference/minio-server/settings/notifications/mqtt/#envvar.MINIO_NOTIFY_MQTT_PASSWORD) *Required if the MQTT server/broker enforces authentication/authorization*

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_MQTT_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_MQTT_BROKER_<IDENTIFIER>="ENDPOINT"
   set MINIO_NOTIFY_MQTT_TOPIC_<IDENTIFIER>="TOPIC"
   set MINIO_NOTIFY_MQTT_USERNAME_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_PASSWORD_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_QOS_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_KEEP_ALIVE_INTERVAL_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_RECONNECT_INTERVAL_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_MQTT_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_MQTT_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_MQTT_BROKER_<IDENTIFIER>="ENDPOINT"
   export MINIO_NOTIFY_MQTT_TOPIC_<IDENTIFIER>="TOPIC"
   export MINIO_NOTIFY_MQTT_USERNAME_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_PASSWORD_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_QOS_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_KEEP_ALIVE_INTERVAL_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_RECONNECT_INTERVAL_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_MQTT_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the MQTT service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new MQTT service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing MQTT service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_mqtt`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured MQTT endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the URL of the MQTT service endpoint. For example:

  `tcp://hostname:port`
- Replace `TOPIC` with the MQTT topic to which MinIO associates events published to the server/broker.

See [MQTT Service for Bucket Notifications](/reference/minio-server/settings/notifications/mqtt/#minio-server-envvar-bucket-notification-mqtt) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating MQTT endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_mqtt`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an MQTT service endpoint. The following configuration settings are the *minimum* required for an MQTT server/broker endpoint:

- [`broker`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.broker)
- [`topic`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.topic)
- [`username`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.username) *Required if the MQTT server/broker enforces authentication/authorization*
- [`password`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.password) *Required if the MQTT server/broker enforces authentication/authorization*

```shell
mc admin config set ALIAS/ notify_mqtt:IDENTIFIER \
   broker="ENDPOINT" \
   topic="TOPIC" \
   username="username" \
   password="password" \
   qos="<integer>" \
   keep_alive_interval="60s|m|h|d"
   reconnect_interval="60s|m|h|d"
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the MQTT service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing MQTT service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_mqtt`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured MQTT endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the URL of the MQTT service endpoint. For example:

  `tcp://hostname:port`
- Replace `TOPIC` with the MQTT topic to which MinIO associates events published to the server/broker.

See [MQTT Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/mqtt/#minio-server-config-bucket-notification-mqtt) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured MQTT target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:mqtt
```

You must specify the ARN resource when configuring bucket notifications with the associated MQTT deployment as a target.

{{% alert color="info" %}}
**Identifying the ARN for your bucket notifications**

You defined the `<IDENTIFIER>` to assign to the target ARN for your bucket notifications when creating the endpoint previously. The steps below return the ARNs configured on the deployment. Identify the ARN created previously by looking for the `<IDENTIFIER>` you specified.

**Review the JSON output**

1. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS
   ```

2. In the JSON output, look for the key `info.sqsARN`.

   The ARN you need is the value of that key that matches the `<IDENTIFIER>` you specified.

   For example, `arn:minio:sqs::primary:mqtt`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:mqtt`
{{% /alert %}}

### 1) Configure Bucket Notifications using the MQTT Endpoint as a Target {#configure-bucket-notifications-using-the-mqtt-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured MQTT service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:mqtt \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:MQTT
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the MQTT service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an MQTT Endpoint in a MinIO Deployment {#update-an-mqtt-endpoint-in-a-minio-deployment}

The following procedure updates an existing MQTT service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### MQTT 3.1 or 3.1.1 Server/Broker Endpoint {#mqtt-3-1-or-3-1-1-server-broker-endpoint}

This procedure assumes an existing MQTT 3.1 or 3.1.1 server/broker to which the MinIO deployment has connectivity. See the [mqtt.org software listing](https://mqtt.org/software/) for a list of MQTT-compatible server/brokers.

If the MQTT service requires authentication, you *must* provide an appropriate username and password during the configuration process to grant MinIO access to the service.

#### MinIO `mc` Command Line Tool {#id2}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured MQTT Endpoints In The Deployment {#list-configured-mqtt-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured MQTT service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_mqtt
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_mqtt:primary  broker="tcp://mqtt-primary.example.net:port" password="" queue_dir="" queue_limit="0" reconnect_interval="0s"  keep_alive_interval="0s" qos="0" topic="" username=""
notify_mqtt:secondary  broker="tcp://mqtt-primary.example.net:port" password="" queue_dir="" queue_limit="0" reconnect_interval="0s"  keep_alive_interval="0s" qos="0" topic="" username=""
```

The [`notify_mqtt`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt) key is the top-level configuration key for an [MQTT Notification Settings](/reference/minio-server/settings/notifications/mqtt/#minio-server-config-bucket-notification-mqtt). The [`broker`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.broker) key specifies the MQTT server/broker endpoint for the given *notify_mqtt* key. The `notify_mqtt:<IDENTIFIER>` suffix describes the unique identifier for that MQTT service endpoint.

Note the identifier for the MQTT service endpoint you want to update for the next step.

### 2) Update the MQTT Endpoint {#update-the-mqtt-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the MQTT service endpoint:

```shell
mc admin config set ALIAS/ notify_mqtt:<IDENTIFIER> \
   url="MQTT://user:password@hostname:port" \
   exchange="<string>" \
   exchange_type="<string>" \
   routing_key="<string>" \
   mandatory="<string>" \
   durable="<string>" \
   no_wait="<string>" \
   internal="<string>" \
   auto_deleted="<string>" \
   delivery_mode="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The following configuration settings are the *minimum* required for an MQTT server/broker endpoint:

- [`broker`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.broker)
- [`topic`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.topic)
- [`username`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.username) *Required if the MQTT server/broker enforces authentication/authorization*
- [`password`](/reference/minio-server/settings/notifications/mqtt/#mc-conf.notify_mqtt.password) *Required if the MQTT server/broker enforces authentication/authorization*

All other configuration settings are *optional*. See [MQTT Notification Settings](/reference/minio-server/settings/notifications/mqtt/#minio-server-config-bucket-notification-mqtt) for a complete list of MQTT configuration settings.

### 3) Restart the MinIO Deployment {#id3}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured MQTT target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:mqtt
```

### 3) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated MQTT service endpoint and check the MQTT service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
