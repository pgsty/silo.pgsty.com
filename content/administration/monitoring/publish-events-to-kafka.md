---
title: "Publish Events to Kafka"
url: "/administration/monitoring/publish-events-to-kafka/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-kafka"></a>
<a id="minio-bucket-notifications-publish-kafka"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to a [Kafka](https://kafka.apache.org/) service endpoint.

MinIO relies on the [https://github.com/Shopify/sarama](https://github.com/Shopify/sarama) project for Kafka connectivity and shares that project’s Kafka support. See the `sarama` [Compatibility and API stability](https://github.com/Shopify/sarama/#compatibility-and-api-stability) section for more details.

## Add a Kafka Endpoint to a MinIO Deployment {#add-a-kafka-endpoint-to-a-minio-deployment}

The following procedure adds a new Kafka service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### Kafka Minimum Versions and Supported Versions {#kafka-minimum-versions-and-supported-versions}

MinIO relies on the [https://github.com/Shopify/sarama](https://github.com/Shopify/sarama) project for Kafka connectivity and shares that project’s Kafka support. See the `sarama` [Compatibility and API stability](https://github.com/Shopify/sarama/#compatibility-and-api-stability) section for more details.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the Kafka Endpoint to MinIO {#add-the-kafka-endpoint-to-minio}

You can configure a new Kafka service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the Kafka service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/kafka/#minio-server-envvar-bucket-notification-kafka). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring a Kafka service endpoint. The minimum *required* variables are [`MINIO_NOTIFY_KAFKA_ENABLE`](/reference/minio-server/settings/notifications/kafka/#envvar.MINIO_NOTIFY_KAFKA_ENABLE) and [`MINIO_NOTIFY_KAFKA_BROKERS`](/reference/minio-server/settings/notifications/kafka/#envvar.MINIO_NOTIFY_KAFKA_BROKERS):

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_KAFKA_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_KAFKA_BROKERS_<IDENTIFIER>="<ENDPOINT>"
   set MINIO_NOTIFY_KAFKA_TOPIC_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_SASL_USERNAME_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_SASL_PASSWORD_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_SASL_MECHANISM_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_TLS_CLIENT_AUTH_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_SASL_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_TLS_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_CLIENT_TLS_CERT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_CLIENT_TLS_KEY_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_VERSION_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_KAFKA_COMMENT_<IDENTIFIER>="<string>"
```
{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_KAFKA_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_KAFKA_BROKERS_<IDENTIFIER>="<ENDPOINT>"
   export MINIO_NOTIFY_KAFKA_TOPIC_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_SASL_USERNAME_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_SASL_PASSWORD_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_SASL_MECHANISM_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_TLS_CLIENT_AUTH_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_SASL_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_TLS_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_TLS_SKIP_VERIFY_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_CLIENT_TLS_CERT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_CLIENT_TLS_KEY_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_VERSION_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_KAFKA_COMMENT_<IDENTIFIER>="<string>"
```
{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the Kafka service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing Kafka service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_kafka`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Kafka endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with a comma-separated list of Kafka brokers. For example:

  `"kafka1.example.com:2021,kafka2.example.com:2021"`

See [Kafka Service for Bucket Notifications](/reference/minio-server/settings/notifications/kafka/#minio-server-envvar-bucket-notification-kafka) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating Kafka endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_kafka`](/reference/minio-server/settings/notifications/kafka/#mc-conf.notify_kafka) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an Kafka service endpoint. The minimum *required* setting is [`notify_kafka brokers`](/reference/minio-server/settings/notifications/kafka/#mc-conf.notify_kafka.brokers):

```shell
mc admin config set ALIAS/ notify_kafka:IDENTIFIER \
   brokers="<ENDPOINT>" \
   topic="<string>" \
   sasl_username="<string>" \
   sasl_password="<string>" \
   sasl_mechanism="<string>" \
   tls_client_auth="<string>" \
   tls="<string>" \
   tls_skip_verify="<string>" \
   client_tls_cert="<string>" \
   client_tls_key="<string>" \
   version="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the Kafka service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing Kafka service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_kafka`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Kafka endpoints on the MinIO deployment.
- Replace `ENDPOINT` with a comma separated list of Kafka brokers. For example:

  `"kafka1.example.com:2021,kafka2.example.com:2021"`

See [Kafka Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/kafka/#minio-server-config-bucket-notification-kafka) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Kafka target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:kafka
```

You must specify the ARN resource when configuring bucket notifications with the associated Kafka deployment as a target.

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

   For example, `arn:minio:sqs::primary:kafka`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:kafka`
{{% /alert %}}

### 3) Configure Bucket Notifications using the Kafka Endpoint as a Target {#configure-bucket-notifications-using-the-kafka-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured Kafka service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:kafka \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:kafka
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the Kafka service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update a Kafka Endpoint in a MinIO Deployment {#update-a-kafka-endpoint-in-a-minio-deployment}

The following procedure updates an existing Kafka service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### Kafka Minimum Versions and Supported Versions {#id2}

MinIO relies on the [https://github.com/Shopify/sarama](https://github.com/Shopify/sarama) project for Kafka connectivity and shares that project’s Kafka support. See the `sarama` [Compatibility and API stability](https://github.com/Shopify/sarama/#compatibility-and-api-stability) section for more details.

#### MinIO `mc` Command Line Tool {#id3}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured Kafka Endpoints In The Deployment {#list-configured-kafka-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured Kafka service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_kafka
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_kafka:primary tls_skip_verify="off"  queue_dir="" queue_limit="0" sasl="off" sasl_password="" sasl_username="" tls_client_auth="0" tls="off" brokers="" topic="" client_tls_cert="" client_tls_key="" version=""
notify_kafka:secondary tls_skip_verify="off"  queue_dir="" queue_limit="0" sasl="off" sasl_password="" sasl_username="" tls_client_auth="0" tls="off" brokers="" topic="" client_tls_cert="" client_tls_key="" version=""
```

The [`notify_kafka`](/reference/minio-server/settings/notifications/kafka/#mc-conf.notify_kafka) key is the top-level configuration key for an [Kafka Notification Settings](/reference/minio-server/settings/notifications/kafka/#minio-server-config-bucket-notification-kafka). The [`brokers`](/reference/minio-server/settings/notifications/kafka/#mc-conf.notify_kafka.brokers) key specifies the Kafka service endpoint for the given *notify_kafka* key. The `notify_kafka:<IDENTIFIER>` suffix describes the unique identifier for that Kafka service endpoint.

Note the identifier for the Kafka service endpoint you want to update for the next step.

### 2) Update the Kafka Endpoint {#update-the-kafka-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the Kafka service endpoint:

```shell
mc admin config set ALIAS/ notify_kafka:<IDENTIFIER> \
   brokers="https://kafka1.example.net:9200, https://kafka2.example.net:9200" \
   topic="<string>" \
   sasl_username="<string>" \
   sasl_password="<string>" \
   sasl_mechanism="<string>" \
   tls_client_auth="<string>" \
   tls="<string>" \
   tls_skip_verify="<string>" \
   client_tls_cert="<string>" \
   client_tls_key="<string>" \
   version="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The [`notify_kafka brokers`](/reference/minio-server/settings/notifications/kafka/#mc-conf.notify_kafka.brokers) configuration setting is the *minimum* required for a Kafka service endpoint. All other configuration settings are *optional*. See [Kafka Notification Settings](/reference/minio-server/settings/notifications/kafka/#minio-server-config-bucket-notification-kafka) for a complete list of Kafka configuration settings.

### 3) Restart the MinIO Deployment {#id4}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Kafka target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:kafka
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated Kafka service endpoint and check the Kafka service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
