---
title: "Publish Events to Webhook"
url: "/administration/monitoring/publish-events-to-webhook/"
weight: 100
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-webhook"></a>
<a id="minio-bucket-notifications-publish-webhook"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to a [Webhook](https://en.wikipedia.org/wiki/Webhook) service endpoint.

## Add a Webhook Endpoint to a MinIO Deployment {#add-a-webhook-endpoint-to-a-minio-deployment}

The following procedure adds a new Webhook service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the Webhook Endpoint to MinIO {#add-the-webhook-endpoint-to-minio}

You can configure a new Webhook service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the Webhook service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/webhook-service/#minio-server-envvar-bucket-notification-webhook). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an Webhook service endpoint. The minimum *required* variables are [`MINIO_NOTIFY_WEBHOOK_ENABLE`](/reference/minio-server/settings/notifications/webhook-service/#envvar.MINIO_NOTIFY_WEBHOOK_ENABLE) and [`MINIO_NOTIFY_WEBHOOK_ENDPOINT`](/reference/minio-server/settings/notifications/webhook-service/#envvar.MINIO_NOTIFY_WEBHOOK_ENDPOINT):

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_WEBHOOK_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_WEBHOOK_ENDPOINT_<IDENTIFIER>="ENDPOINT"
   set MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_WEBHOOK_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_WEBHOOK_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_WEBHOOK_CLIENT_CERT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_WEBHOOK_CLIENT_KEY_<IDENTIFIER>="<string>"
```

{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_WEBHOOK_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_WEBHOOK_ENDPOINT_<IDENTIFIER>="ENDPOINT"
   export MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_WEBHOOK_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_WEBHOOK_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_WEBHOOK_CLIENT_CERT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_WEBHOOK_CLIENT_KEY_<IDENTIFIER>="<string>"
```

{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the Webhook service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing Webhook service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Webhook endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the URL of the Webhook service endpoint. For example:

  `https://webhook.example.com`

See [Webhook Service for Bucket Notifications](/reference/minio-server/settings/notifications/webhook-service/#minio-server-envvar-bucket-notification-webhook) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating Webhook endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_webhook`](/reference/minio-server/settings/notifications/webhook-service/#mc-conf.notify_webhook) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an Webhook service endpoint. The minimum *required* setting is [`notify_webhook endpoint`](/reference/minio-server/settings/notifications/webhook-service/#mc-conf.notify_webhook.endpoint):

```shell
mc admin config set ALIAS/ notify_webhook:IDENTIFIER \
   endpoint="<ENDPOINT>" \
   auth_token="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   client_cert="<string>" \
   client_key="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the Webhook service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing Webhook service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Webhook endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the URL of the Webhook service endpoint. For example:

  `https://webhook.example.com`

See [Webhook Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/webhook-service/#minio-server-config-bucket-notification-webhook) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Webhook target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:webhook
```

You must specify the ARN resource when configuring bucket notifications with the associated Webhook deployment as a target.

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

   For example, `arn:minio:sqs::primary:webhook`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:webhook`
{{% /alert %}}

### 3) Configure Bucket Notifications using the Webhook Endpoint as a Target {#configure-bucket-notifications-using-the-webhook-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured Webhook service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:webhook \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:webhook
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the Webhook service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an Webhook Endpoint in a MinIO Deployment {#update-an-webhook-endpoint-in-a-minio-deployment}

The following procedure updates an existing Webhook service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### MinIO `mc` Command Line Tool {#id2}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured Webhook Endpoints In The Deployment {#list-configured-webhook-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured Webhook service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_webhook
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_webhook:primary endpoint="https://webhook.example.com" auth_token="" queue_limit="0" queue_dir="" client_cert="" client_key=""
notify_webhook:secondary endpoint="https://webhook.example.com" auth_token="" queue_limit="0" queue_dir="" client_cert="" client_key=""
```

The [`notify_webhook`](/reference/minio-server/settings/notifications/webhook-service/#mc-conf.notify_webhook) key is the top-level configuration key for an [Webhook Service Notification Settings](/reference/minio-server/settings/notifications/webhook-service/#minio-server-config-bucket-notification-webhook). The [`endpoint`](/reference/minio-server/settings/notifications/webhook-service/#mc-conf.notify_webhook.endpoint) key specifies the Webhook service endpoint for the given *notify_webhook* key. The `notify_webhook:<IDENTIFIER>` suffix describes the unique identifier for that Webhook service endpoint.

Note the identifier for the Webhook service endpoint you want to update for the next step.

### 2) Update the Webhook Endpoint {#update-the-webhook-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the Webhook service endpoint:

```shell
mc admin config set ALIAS/ notify_webhook:IDENTIFIER \
   endpoint="<ENDPOINT>" \
   auth_token="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   client_cert="<string>" \
   client_key="<string>"
```

The [`notify_webhook endpoint`](/reference/minio-server/settings/notifications/webhook-service/#mc-conf.notify_webhook.endpoint) configuration setting is the *minimum* required for an Webhook service endpoint. All other configuration settings are *optional*. See [Webhook Service Notification Settings](/reference/minio-server/settings/notifications/webhook-service/#minio-server-config-bucket-notification-webhook) for a complete list of Webhook configuration settings.

### 3) Restart the MinIO Deployment {#id3}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Webhook target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:webhook
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated Webhook service endpoint and check the Webhook service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
