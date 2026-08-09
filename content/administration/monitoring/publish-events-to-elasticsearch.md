---
title: "Publish Events to Elasticsearch"
url: "/administration/monitoring/publish-events-to-elasticsearch/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-elasticsearch"></a>
<a id="minio-bucket-notifications-publish-elasticsearch"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to an [Elasticsearch](https://www.elastic.co/) service endpoint.

MinIO relies on the [https://github.com/elastic/go-elasticsearch](https://github.com/elastic/go-elasticsearch) v7 project for Elastic connectivity.

## Add a Elasticsearch Endpoint to a MinIO Deployment {#add-a-elasticsearch-endpoint-to-a-minio-deployment}

The following procedure adds a new Elasticsearch service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### Elasticsearch v7.0 and later {#elasticsearch-v7-0-and-later}

MinIO relies on the [https://github.com/olivere/elastic](https://github.com/olivere/elastic) v7 project for Elastic connectivity. The `elastic/v7` library specifically targets Elasticsearch v7.0 and is *not compatible with earlier Elasticsearch versions*.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the Elasticsearch Endpoint to MinIO {#add-the-elasticsearch-endpoint-to-minio}

You can configure a new Elasticsearch service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the Elasticsearch service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-envvar-bucket-notification-elasticsearch). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring an Elasticsearch service endpoint. The minimum *required* variables are:

- [`MINIO_NOTIFY_ELASTICSEARCH_ENABLE`](/reference/minio-server/settings/notifications/elasticsearch/#envvar.MINIO_NOTIFY_ELASTICSEARCH_ENABLE)
- [`MINIO_NOTIFY_ELASTICSEARCH_URL`](/reference/minio-server/settings/notifications/elasticsearch/#envvar.MINIO_NOTIFY_ELASTICSEARCH_URL)
- [`MINIO_NOTIFY_ELASTICSEARCH_INDEX`](/reference/minio-server/settings/notifications/elasticsearch/#envvar.MINIO_NOTIFY_ELASTICSEARCH_INDEX)
- [`MINIO_NOTIFY_ELASTICSEARCH_FORMAT`](/reference/minio-server/settings/notifications/elasticsearch/#envvar.MINIO_NOTIFY_ELASTICSEARCH_FORMAT)

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_ELASTICSEARCH_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_ELASTICSEARCH_URL_<IDENTIFIER>="<ENDPOINT>"
   set MINIO_NOTIFY_ELASTICSEARCH_INDEX_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_FORMAT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_USERNAME_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_PASSWORD_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_QUEUE_DIR_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   set MINIO_NOTIFY_ELASTICSEARCH_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_ELASTICSEARCH_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_ELASTICSEARCH_URL_<IDENTIFIER>="<ENDPOINT>"
   export MINIO_NOTIFY_ELASTICSEARCH_INDEX_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_FORMAT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_USERNAME_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_PASSWORD_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_QUEUE_DIR_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_QUEUE_LIMIT_<IDENTIFIER>="<string>"
   export MINIO_NOTIFY_ELASTICSEARCH_COMMENT_<IDENTIFIER>="<string>"
```

{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the TARGET service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing Elasticsearch service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_elasticsearch`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Elasticsearch endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the URL of the Elasticsearch service endpoint. For example:

See [Elasticsearch Service for Bucket Notifications](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-envvar-bucket-notification-elasticsearch) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating Elasticsearch endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_elasticsearch`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an Elasticsearch service endpoint. The minimum *required* settings are:

- [`url`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch.url)
- [`index`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch.index)
- [`format`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch.format)

```shell
mc admin config set ALIAS/ notify_elasticsearch:IDENTIFIER \
   url="ENDPOINT" \
   index="<string>" \
   format="<string>" \
   username="<string>" \
   password="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the Elasticsearch service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing Elasticsearch service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_elasticsearch`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured Elasticsearch endpoints on the MinIO deployment.
- Replace `ENDPOINT` with the URL of the Elasticsearch service endpoint. For example:

  `https://user:password@hostname:port`

See [Elasticsearch Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-config-bucket-notification-elasticsearch) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Elasticsearch target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:elasticsearch
```

You must specify the ARN resource when configuring bucket notifications with the associated Elasticsearch deployment as a target.

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

   For example, `arn:minio:sqs::primary:elasticsearch`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:elasticsearch`
{{% /alert %}}

### 3) Configure Bucket Notifications using the Elasticsearch Endpoint as a Target {#configure-bucket-notifications-using-the-elasticsearch-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured Elasticsearch service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:elasticsearch \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:elasticsearch
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the Elasticsearch service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update an Elasticsearch Endpoint in a MinIO Deployment {#update-an-elasticsearch-endpoint-in-a-minio-deployment}

The following procedure updates an existing Elasticsearch service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### Elasticsearch v7.0 and later {#id2}

MinIO relies on the [https://github.com/olivere/elastic](https://github.com/olivere/elastic) v7 project for Elastic connectivity. The `elastic/v7` library specifically targets Elasticsearch v7.0 and is *not compatible with earlier Elasticsearch versions*.

#### MinIO `mc` Command Line Tool {#id3}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured Elasticsearch Endpoints In The Deployment {#list-configured-elasticsearch-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured Elasticsearch service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_elasticsearch
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_elasticsearch:primary  queue_dir="" queue_limit="0"  url="https://user:password@hostname:port" format="namespace" index=""
notify_elasticsearch:secondary queue_dir="" queue_limit="0"  url="https://user:password@hostname:port" format="namespace" index=""
```

The [`notify_elasticsearch`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch) key is the top-level configuration key for an [Elasticsearch Notification Settings](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-config-bucket-notification-elasticsearch). The [`url`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch.url) key specifies the Elasticsearch service endpoint for the given *notify_elasticsearch* key. The `notify_elasticsearch:<IDENTIFIER>` suffix describes the unique identifier for that Elasticsearch service endpoint.

Note the identifier for the Elasticsearch service endpoint you want to update for the next step.

### 2) Update the Elasticsearch Endpoint {#update-the-elasticsearch-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the Elasticsearch service endpoint:

```shell
mc admin config set ALIAS/ notify_elasticsearch:<IDENTIFIER> \
   url="https://user:password@hostname:port" \
   index="<string>" \
   format="<string>" \
   username="<string>" \
   password="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The [`notify_elasticsearch url`](/reference/minio-server/settings/notifications/elasticsearch/#mc-conf.notify_elasticsearch.url) configuration setting is the *minimum* required for an Elasticsearch service endpoint. All other configuration settings are *optional*. See [Elasticsearch Notification Settings](/reference/minio-server/settings/notifications/elasticsearch/#minio-server-config-bucket-notification-elasticsearch) for a complete list of Elasticsearch configuration settings.

### 3) Restart the MinIO Deployment {#id4}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured Elasticsearch target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:elasticsearch
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated Elasticsearch service endpoint and check the Elasticsearch service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
