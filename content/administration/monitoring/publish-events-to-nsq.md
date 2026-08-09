---
title: "Publish Events to NSQ"
url: "/administration/monitoring/publish-events-to-nsq/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-nsq"></a>
<a id="minio-bucket-notifications-publish-nsq"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to [NSQ](https://nsq.io/) service endpoint.

## Add a NSQ Endpoint to a MinIO Deployment {#add-a-nsq-endpoint-to-a-minio-deployment}

The following procedure adds a new NSQ service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the NSQ Endpoint to MinIO {#add-the-nsq-endpoint-to-minio}

You can configure a new NSQ service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the NSQ service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/nsq/#minio-server-envvar-bucket-notification-nsq). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an NSQ service endpoint. The minimum *required* variables are [`MINIO_NOTIFY_NSQ_NSQD_ADDRESS`](/reference/minio-server/settings/notifications/nsq/#envvar.MINIO_NOTIFY_NSQ_NSQD_ADDRESS) and [`MINIO_NOTIFY_NSQ_TOPIC`](/reference/minio-server/settings/notifications/nsq/#envvar.MINIO_NOTIFY_NSQ_TOPIC):

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_NSQ_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_NSQ_NSQD_ADDRESS_<IDENTIFIER>="<ENDPOINT>"
   set MINIO_NOTIFY_NSQ_TOPIC_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_NSQ_TLS_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_NSQ_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_NSQ_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_NSQ_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_NSQ_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_NSQ_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_NSQ_NSQD_ADDRESS_<IDENTIFIER>="<ENDPOINT>"
   export MINIO_NOTIFY_NSQ_TOPIC_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_NSQ_TLS_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_NSQ_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_NSQ_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_NSQ_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_NSQ_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the TARGET service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing NSQ service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_nsq`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured NSQ endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the URL of the NSQ service endpoint. For example, `https://nsq-service.example.com:4150`.

See [NSQ Service for Bucket Notifications](/reference/minio-server/settings/notifications/nsq/#minio-server-envvar-bucket-notification-nsq) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating NSQ endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_nsq`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an NSQ service endpoint. The minimum *required* setting is [`notify_nsq nsqd_address`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq.nsqd_address) and [`notify_nsq topic`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq.topic):

```shell
mc admin config set ALIAS/ notify_nsq:IDENTIFIER \
  nsqd_address="ENDPOINT" \
  topic="<string>" \
  tls="<string>" \
  tls_skip_verify="<string>" \
  queue_dir="<string>" \
  queue_limit="<string>" \
  comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the NSQ service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing NSQ service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_nsq`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured NSQ endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the URL of the NSQ service endpoint. For example:

  `NSQ://user:password@hostname:port`

See [NSQ Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/nsq/#minio-server-config-bucket-notification-nsq) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured NSQ target similar to the following:

```shell
SQS ARNs: |ARN|
```

You must specify the ARN resource when configuring bucket notifications with the associated NSQ deployment as a target.

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

   For example, `arn:minio:sqs::primary:nsq`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:nsq`
{{% /alert %}}

### 3) Configure Bucket Notifications using the NSQ Endpoint as a Target {#configure-bucket-notifications-using-the-nsq-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured NSQ service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:nsq \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:nsq
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the NSQ service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an NSQ Endpoint in a MinIO Deployment {#update-an-nsq-endpoint-in-a-minio-deployment}

The following procedure updates an existing NSQ service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### MinIO `mc` Command Line Tool {#id2}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured NSQ Endpoints In The Deployment {#list-configured-nsq-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured NSQ service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_nsq
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_nsq:primary nsqd_address="https://nsq.example.com" queue_dir="" queue_limit="0"  tls="off" tls_skip_verify="off" topic=""
notify_nsq:secondary nsqd_address="https://nsq.example.com" queue_dir="" queue_limit="0"  tls="off" tls_skip_verify="off" topic=""
```

The [`notify_nsq`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq) key is the top-level configuration key for an [NSQ Notification Settings](/reference/minio-server/settings/notifications/nsq/#minio-server-config-bucket-notification-nsq). The [`nsqd_address`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq.nsqd_address) key specifies the NSQ service endpoint for the given *notify_nsq* key. The `notify_nsq:<IDENTIFIER>` suffix describes the unique identifier for that NSQ service endpoint.

Note the identifier for the NSQ service endpoint you want to update for the next step.

### 2) Update the NSQ Endpoint {#update-the-nsq-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the NSQ service endpoint:

```shell
mc admin config set ALIAS/ notify_nsq:<IDENTIFIER> \
   nsqd_address="NSQ://user:password@hostname:port" \
   topic="<string>" \
   tls="<string>" \
   tls_skip_verify="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The [`notify_nsq nsqd_address`](/reference/minio-server/settings/notifications/nsq/#mc-conf.notify_nsq.nsqd_address) configuration setting is the *minimum* required for an NSQ service endpoint. All other configuration settings are *optional*. See [NSQ Notification Settings](/reference/minio-server/settings/notifications/nsq/#minio-server-config-bucket-notification-nsq) for a complete list of NSQ configuration settings.

### 3) Restart the MinIO Deployment {#id3}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured NSQ target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:NSQ
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated NSQ service endpoint and check the NSQ service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
