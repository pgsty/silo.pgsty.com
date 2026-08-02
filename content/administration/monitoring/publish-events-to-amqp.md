---
title: "Publish Events to AMQP (RabbitMQ)"
url: "/administration/monitoring/publish-events-to-amqp/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-amqp-rabbitmq"></a>
<a id="minio-bucket-notifications-publish-amqp"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to a [AMQP 0-9-1](https://www.amqp.org/) service endpoint such as [RabbitMQ](https://www.rabbitmq.com).

MinIO relies on the [https://github.com/streadway/amqp](https://github.com/streadway/amqp) project for AMQP connectivity. The project is primarily tested against [RabbitMQ](https://www.rabbitmq.com/) deployments, though other [AMQP 0-9-1-compatible](https://www.amqp.org/) services *may* also work. The procedures on this page assume a RabbitMQ deployment using the AMQP 0-9-1 protocol as the service endpoint.

## Add an AMQP Endpoint to a MinIO Deployment {#add-an-amqp-endpoint-to-a-minio-deployment}

The following procedure adds a new AMQP service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### AMQP 0-9-1 Service Endpoint {#amqp-0-9-1-service-endpoint}

MinIO relies on the [https://github.com/streadway/amqp](https://github.com/streadway/amqp) project for AMQP connectivity. The project is primarily tested against [RabbitMQ](https://www.rabbitmq.com/) deployments, though other [AMQP 0-9-1-compatible](https://www.amqp.org/) services *may* also work. This procedure assumes a RabbitMQ deployment using the 0-9-1 protocol as the service endpoint.

If the AMQP service requires authentication, you *must* provide an appropriate username and password during the configuration process to grant MinIO access to the service.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the AMQP Endpoint to MinIO {#add-the-amqp-endpoint-to-minio}

You can configure a new AMQP service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the AMQP service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/amqp/#minio-server-envvar-bucket-notification-amqp). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an AMQP service endpoint. The minimum *required* variables are [`MINIO_NOTIFY_AMQP_ENABLE`](/reference/minio-server/settings/notifications/amqp/#envvar.MINIO_NOTIFY_AMQP_ENABLE) and [`MINIO_NOTIFY_AMQP_URL`](/reference/minio-server/settings/notifications/amqp/#envvar.MINIO_NOTIFY_AMQP_URL):

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_AMQP_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_AMQP_URL_<IDENTIFIER>="<ENDPOINT>"
   set MINIO_NOTIFY_AMQP_EXCHANGE_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_EXCHANGE_TYPE_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_ROUTING_KEY_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_MANDATORY_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_DURABLE_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_NO_WAIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_INTERNAL_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_AUTO_DELETED_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_DELIVERY_MODE_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_AMQP_COMMENT_<IDENTIFIER>="<string>"
```
{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_AMQP_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_AMQP_URL_<IDENTIFIER>="<ENDPOINT>"
   export MINIO_NOTIFY_AMQP_EXCHANGE_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_EXCHANGE_TYPE_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_ROUTING_KEY_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_MANDATORY_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_DURABLE_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_NO_WAIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_INTERNAL_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_AUTO_DELETED_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_DELIVERY_MODE_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_AMQP_COMMENT_<IDENTIFIER>="<string>"
```
{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the AMQP service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new AMQP service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing AMQP service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_amqp`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured AMQP endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the URL of the AMQP service endpoint. For example:

  `amqp://user:password@hostname:port`

See [AMQP Service for Bucket Notifications](/reference/minio-server/settings/notifications/amqp/#minio-server-envvar-bucket-notification-amqp) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating AMQP endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_amqp`](/reference/minio-server/settings/notifications/amqp/#mc-conf.notify_amqp) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an AMQP service endpoint. The minimum *required* setting is [`notify_amqp url`](/reference/minio-server/settings/notifications/amqp/#mc-conf.notify_amqp.url):

```shell
mc admin config set ALIAS/ notify_amqp:IDENTIFIER \
  url="ENDPOINT" \
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

- Replace `IDENTIFIER` with a unique descriptive string for the AMQP service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing AMQP service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_amqp`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured AMQP endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the URL of the AMQP service endpoint. For example:

  `amqp://user:password@hostname:port`

See [AMQP Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/amqp/#minio-server-config-bucket-notification-amqp) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured AMQP target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:amqp
```

You must specify the ARN resource when configuring bucket notifications with the associated AMQP deployment as a target.

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

   For example, `arn:minio:sqs::primary:amqp`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:amqp`
{{% /alert %}}

### 3) Configure Bucket Notifications using the AMQP Endpoint as a Target {#configure-bucket-notifications-using-the-amqp-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured AMQP service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:amqp \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:amqp
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the AMQP service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an AMQP Endpoint in a MinIO Deployment {#update-an-amqp-endpoint-in-a-minio-deployment}

The following procedure updates an existing AMQP service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### AMQP 0-9-1 Service Endpoint {#id2}

MinIO relies on the [https://github.com/streadway/amqp](https://github.com/streadway/amqp) project for AMQP connectivity. The project is primarily tested against [RabbitMQ](https://www.rabbitmq.com/) deployments, though other [AMQP 0-9-1-compatible](https://www.amqp.org/) services *may* also work. This procedure *assumes* a RabbitMQ deployment as the service endpoint.

If the AMQP service requires authentication, you *must* provide an appropriate username and password during the configuration process to grant MinIO access to the service.

#### MinIO `mc` Command Line Tool {#id3}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured AMQP Endpoints In The Deployment {#list-configured-amqp-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured AMQP service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_amqp
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_amqp:primary delivery_mode="0" exchange_type="" no_wait="off" queue_dir="" queue_limit="0"  url="amqp://user:password@hostname:port" auto_deleted="off" durable="off" exchange="" internal="off" mandatory="off" routing_key=""
notify_amqp:secondary delivery_mode="0" exchange_type="" no_wait="off" queue_dir="" queue_limit="0"  url="amqp://user:password@hostname:port" auto_deleted="off" durable="off" exchange="" internal="off" mandatory="off" routing_key=""
```

The [`notify_amqp`](/reference/minio-server/settings/notifications/amqp/#mc-conf.notify_amqp) key is the top-level configuration key for an [AMQP Notification Settings](/reference/minio-server/settings/notifications/amqp/#minio-server-config-bucket-notification-amqp). The [`url`](/reference/minio-server/settings/notifications/amqp/#mc-conf.notify_amqp.url) key specifies the AMQP service endpoint for the given *notify_amqp* key. The `notify_amqp:<IDENTIFIER>` suffix describes the unique identifier for that AMQP service endpoint.

Note the identifier for the AMQP service endpoint you want to update for the next step.

### 2) Update the AMQP Endpoint {#update-the-amqp-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the AMQP service endpoint:

```shell
mc admin config set ALIAS/ notify_amqp:<IDENTIFIER> \
   url="amqp://user:password@hostname:port" \
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

The [`notify_amqp url`](/reference/minio-server/settings/notifications/amqp/#mc-conf.notify_amqp.url) configuration setting is the *minimum* required for an AMQP service endpoint. All other configuration settings are *optional*. See [AMQP Notification Settings](/reference/minio-server/settings/notifications/amqp/#minio-server-config-bucket-notification-amqp) for a complete list of AMQP configuration settings.

### 3) Restart the MinIO Deployment {#id4}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured AMQP target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:amqp
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated AMQP service endpoint and check the AMQP service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
