---
title: "Publish Events to NATS"
url: "/administration/monitoring/publish-events-to-nats/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/monitoring/publish-events-to-nats.rst
upstream_modified: false
---

<a id="publish-events-to-nats"></a>
<a id="minio-bucket-notifications-publish-nats"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to a [NATS](https://nats.io/) service endpoint.

> [!NOTE]
> **NATS Streaming Deprecated**
>
> NATS Streaming is deprecated. Migrate to [JetStream](https://docs.nats.io/nats-concepts/jetstream) instead.
>
> The related MinIO configuration options and environment variables are deprecated.

## Add a NATS Endpoint to a MinIO Deployment {#add-a-nats-endpoint-to-a-minio-deployment}

The following procedure adds a new NATS service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the NATS Endpoint to MinIO {#add-the-nats-endpoint-to-minio}

You can configure a new NATS service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
MinIO supports specifying the NATS service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/nats/#minio-server-envvar-bucket-notification-nats). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an NATS service endpoint. The minimum *required* variables are [`MINIO_NOTIFY_NATS_ADDRESS`](/reference/minio-server/settings/notifications/nats/#envvar.MINIO_NOTIFY_NATS_ADDRESS) and [`MINIO_NOTIFY_NATS_SUBJECT`](/reference/minio-server/settings/notifications/nats/#envvar.MINIO_NOTIFY_NATS_SUBJECT):

> [!NOTE]
> **Windows**
>
> ```shell
>    set MINIO_NOTIFY_NATS_ENABLE_<IDENTIFIER>="on"
>    set MINIO_NOTIFY_NATS_ADDRESS_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_SUBJECT_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_USERNAME_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_PASSWORD_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_TOKEN_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_TLS_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_PING_INTERVAL_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_QUEUE_DIR_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_QUEUE_LIMIT_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_CERT_AUTHORITY_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_CLIENT_CERT_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_CLIENT_KEY_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_COMMENT_<IDENTIFIER>="<string>"
>    set MINIO_NOTIFY_NATS_JETSTREAM_<IDENTIFIER>="<string>"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
>    export MINIO_NOTIFY_NATS_ENABLE_<IDENTIFIER>="on"
>    export MINIO_NOTIFY_NATS_ADDRESS_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_SUBJECT_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_USERNAME_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_PASSWORD_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_TOKEN_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_TLS_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_PING_INTERVAL_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_QUEUE_DIR_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_QUEUE_LIMIT_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_CERT_AUTHORITY_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_CLIENT_CERT_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_CLIENT_KEY_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_COMMENT_<IDENTIFIER>="<string>"
>    export MINIO_NOTIFY_NATS_JETSTREAM_<IDENTIFIER>="<string>"
> ```

- Replace `<IDENTIFIER>` with a unique descriptive string for the NATS service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing NATS service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_nats`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured NATS endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the hostname and port of the NATS service endpoint. For example: `nats-endpoint.example.com:4222`

See [NATS Service for Bucket Notifications](/reference/minio-server/settings/notifications/nats/#minio-server-envvar-bucket-notification-nats) for complete documentation on each environment variable.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
MinIO supports adding or updating NATS endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_nats`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an NATS service endpoint. The minimum *required* setting are [`notify_nats address`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats.address) and [`notify_nats subject`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats.subject):

```shell
mc admin config set ALIAS/ notify_nats:IDENTIFIER \
   address="HOSTNAME" \
   subject="<string>" \
   username="<string>" \
   password="<string>" \
   token="<string>" \
   nats_jetstream="<string>" \
   tls="<string>" \
   tls_skip_verify="<string>" \
   ping_interval="<string>" \
   cert_authority="<string>" \
   client_cert="<string>" \
   client_key="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the NATS service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing NATS service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_nats`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured NATS endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the hostname and port of the NATS service endpoint. For example: `nats-endpoint.example.com:4222`.

See [NATS Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/nats/#minio-server-config-bucket-notification-nats) for complete documentation on each setting.
{{< /tab >}}
{{< /tabs >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured NATS target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:nats
```

You must specify the ARN resource when configuring bucket notifications with the associated NATS deployment as a target.

> [!NOTE]
> **Identifying the ARN for your bucket notifications**
>
> You defined the `<IDENTIFIER>` to assign to the target ARN for your bucket notifications when creating the endpoint previously. The steps below return the ARNs configured on the deployment. Identify the ARN created previously by looking for the `<IDENTIFIER>` you specified.
>
> **Review the JSON output**
>
> 1. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.
>
>    ```shell
>    mc admin info --json ALIAS
>    ```
>
> 2. In the JSON output, look for the key `info.sqsARN`.
>
>    The ARN you need is the value of that key that matches the `<IDENTIFIER>` you specified.
>
>    For example, `arn:minio:sqs::primary:nats`.
>
> **Use jq to parse the JSON for the value**
>
> 1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
> 2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.
>
>    ```shell
>    mc admin info --json ALIAS | jq  .info.sqsARN
>    ```
>
>    This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:nats`

### 3) Configure Bucket Notifications using the NATS Endpoint as a Target {#configure-bucket-notifications-using-the-nats-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured NATS service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:nats \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:nats
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the NATS service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an NATS Endpoint in a MinIO Deployment {#update-an-nats-endpoint-in-a-minio-deployment}

The following procedure updates an existing NATS service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### MinIO `mc` Command Line Tool {#id2}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured NATS Endpoints In The Deployment {#list-configured-nats-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured NATS service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_nats
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_nats:primary password="yoursecret" subject="" address="nats-endpoint.example.com:4222"  token="" username="yourusername" ping_interval="0" queue_limit="0" tls="off" tls_skip_verify="off" queue_dir="" streaming_enable="on" nats_jetstream="on"
notify_nats:secondary password="yoursecret" subject="" address="nats-endpoint.example.com:4222"  token="" username="yourusername" ping_interval="0" queue_limit="0" tls="off" tls_skip_verify="off" queue_dir="" streaming_enable="on" nats_jetstream="on"
```

The [`notify_nats`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats) key is the top-level configuration key for an [NATS Notification Settings](/reference/minio-server/settings/notifications/nats/#minio-server-config-bucket-notification-nats). The [`address`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats.address) key specifies the NATS service endpoint for the given `notify_nats` key. The `notify_nats:<IDENTIFIER>` suffix describes the unique identifier for that NATS service endpoint.

Note the identifier for the NATS service endpoint you want to update for the next step.

### 2) Update the NATS Endpoint {#update-the-nats-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the NATS service endpoint:

```shell
mc admin config set ALIAS/ notify_nats:IDENTIFIER \
   address="HOSTNAME" \
   subject="<string>" \
   username="<string>" \
   password="<string>" \
   token="<string>" \
   tls="<string>" \
   tls_skip_verify="<string>" \
   ping_interval="<string>" \
   nats_jetstream="<string>" \
   cert_authority="<string>" \
   client_cert="<string>" \
   client_key="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The [`notify_nats address`](/reference/minio-server/settings/notifications/nats/#mc-conf.notify_nats.address) configuration setting is the *minimum* required for an NATS service endpoint. All other configuration settings are *optional*. See [NATS Notification Settings](/reference/minio-server/settings/notifications/nats/#minio-server-config-bucket-notification-nats) for a complete list of NATS configuration settings.

### 3) Restart the MinIO Deployment {#id3}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured NATS target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:nats
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated NATS service endpoint and check the NATS service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
