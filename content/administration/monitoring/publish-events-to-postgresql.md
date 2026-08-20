---
title: "Publish Events to PostgreSQL"
url: "/administration/monitoring/publish-events-to-postgresql/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/monitoring/publish-events-to-postgresql.rst
upstream_modified: false
---

<a id="publish-events-to-postgresql"></a>
<a id="minio-bucket-notifications-publish-postgresql"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to [PostgreSQL](https://www.postgresql.org/). MinIO supports PostgreSQL 9.5 and later *only*.

## Add a PostgreSQL Endpoint to a MinIO Deployment {#add-a-postgresql-endpoint-to-a-minio-deployment}

The following procedure adds a new PostgreSQL service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### PostgreSQL 9.5 and later {#postgresql-9-5-and-later}

MinIO relies on features introduced with PostgreSQL 9.5.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the PostgreSQL Endpoint to MinIO {#add-the-postgresql-endpoint-to-minio}

You can configure a new PostgreSQL service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
MinIO supports specifying the PostgreSQL service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/postgresql/#minio-server-envvar-bucket-notification-postgresql). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring a PostgreSQL service endpoint. The minimum *required* variables are:

- [`MINIO_NOTIFY_POSTGRES_CONNECTION_STRING`](/reference/minio-server/settings/notifications/postgresql/#envvar.MINIO_NOTIFY_POSTGRES_CONNECTION_STRING)
- [`MINIO_NOTIFY_POSTGRES_TABLE`](/reference/minio-server/settings/notifications/postgresql/#envvar.MINIO_NOTIFY_POSTGRES_TABLE)
- [`MINIO_NOTIFY_POSTGRES_FORMAT`](/reference/minio-server/settings/notifications/postgresql/#envvar.MINIO_NOTIFY_POSTGRES_FORMAT)

> [!NOTE]
> **Windows**
>
> ```shell
>    set MINIO_NOTIFY_POSTGRES_ENABLE_<IDENTIFIER>="on"
>    set MINIO_NOTIFY_POSTGRES_CONNECTION_STRING_<IDENTIFIER>="host=postgresql-endpoint.example.net port=4222"
>    set MINIO_NOTIFY_POSTGRES_TABLE_<IDENTIFIER>="minioevents"
>    set MINIO_NOTIFY_POSTGRES_FORMAT_<IDENTIFIER>="namespace|access"
>    set MINIO_NOTIFY_POSTGRES_MAX_OPEN_CONNECTIONS_<IDENTIFIER>="2"
>    set MINIO_NOTIFY_POSTGRES_QUEUE_DIR_<IDENTIFIER>="/opt/minio/events"
>    set MINIO_NOTIFY_POSTGRES_QUEUE_LIMIT_<IDENTIFIER>="100000"
>    set MINIO_NOTIFY_POSTGRES_COMMENT_<IDENTIFIER>="PostgreSQL Notification Event Logging for MinIO"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
>    export MINIO_NOTIFY_POSTGRES_ENABLE_<IDENTIFIER>="on"
>    export MINIO_NOTIFY_POSTGRES_CONNECTION_STRING_<IDENTIFIER>="host=postgresql-endpoint.example.net port=4222"
>    export MINIO_NOTIFY_POSTGRES_TABLE_<IDENTIFIER>="minioevents"
>    export MINIO_NOTIFY_POSTGRES_FORMAT_<IDENTIFIER>="namespace|access"
>    export MINIO_NOTIFY_POSTGRES_MAX_OPEN_CONNECTIONS_<IDENTIFIER>="2"
>    export MINIO_NOTIFY_POSTGRES_QUEUE_DIR_<IDENTIFIER>="/opt/minio/events"
>    export MINIO_NOTIFY_POSTGRES_QUEUE_LIMIT_<IDENTIFIER>="100000"
>    export MINIO_NOTIFY_POSTGRES_COMMENT_<IDENTIFIER>="PostgreSQL Notification Event Logging for MinIO"
> ```

- Replace `<IDENTIFIER>` with a unique descriptive string for the PostgreSQL service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing PostgreSQL service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_postgres`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured PostgreSQL endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the [PostgreSQL Connection String](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) for PostgreSQL service endpoint. MinIO supports `key=value` format for the connection string. For example:

  `"host=https://postgresql.example.com port=5432 ..."`

  For more complete documentation on supported PostgreSQL connection string parameters, see [PostgreSQL Connection String](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING).

See [PostgreSQL Service for Bucket Notifications](/reference/minio-server/settings/notifications/postgresql/#minio-server-envvar-bucket-notification-postgresql) for complete documentation on each environment variable.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
MinIO supports adding or updating PostgreSQL endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_postgres`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an PostgreSQL service endpoint. The minimum *required* setting are:

- [`notify_postgres connection_string`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.connection_string)
- [`notify_postgres table`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.table)
- [`notify_postgres format`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.format)

```shell
mc admin config set ALIAS/ notify_postgres:IDENTIFIER \
   connection_string="ENDPOINT" \
   table="<string>" \
   format="<string>" \
   max_open_connections="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the PostgreSQL service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing PostgreSQL service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_postgres`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured PostgreSQL endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the [PostgreSQL URI connection string](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) of the PostgreSQL service endpoint. MinIO supports `key=value` format for the PostgreSQL connection string. For example:

  `"host=https://postgresql.example.com port=5432 ..."`

  For more complete documentation on supported PostgreSQL connection string parameters, see [PostgreSQL Connection String](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING).

See [PostgreSQL Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/postgresql/#minio-server-config-bucket-notification-postgresql) for complete documentation on each setting.
{{< /tab >}}
{{< /tabs >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured PostgreSQL target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:postgresql
```

You must specify the ARN resource when configuring bucket notifications with the associated PostgreSQL deployment as a target.

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
>    For example, `arn:minio:sqs::primary:postgresql`.
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
>    This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:postgresql`

### 3) Configure Bucket Notifications using the PostgreSQL Endpoint as a Target {#configure-bucket-notifications-using-the-postgresql-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured PostgreSQL service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:postgresql \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the ßevent.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:postgresql
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the PostgreSQL service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update a PostgreSQL Endpoint in a MinIO Deployment {#update-a-postgresql-endpoint-in-a-minio-deployment}

The following procedure updates an existing PostgreSQL service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### PostgreSQL 9.5 and later {#id2}

MinIO relies on features introduced with PostgreSQL 9.5.

#### MinIO `mc` Command Line Tool {#id3}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured PostgreSQL Endpoints In The Deployment {#list-configured-postgresql-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured PostgreSQL service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_postgres
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_postgres:primary queue_dir="" connection_string="postgresql://" queue_limit="0"  table="" format="namespace"
notify_postgres:secondary queue_dir="" connection_string="" queue_limit="0"  table="" format="namespace"
```

The [`notify_postgres`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres) key is the top-level configuration key for an [PostgreSQL Notification Settings](/reference/minio-server/settings/notifications/postgresql/#minio-server-config-bucket-notification-postgresql). The [`connection_string`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.connection_string) key specifies the PostgreSQL service endpoint for the given *notify_postgres* key. The `notify_postgres:<IDENTIFIER>` suffix describes the unique identifier for that PostgreSQL service endpoint.

Note the identifier for the PostgreSQL service endpoint you want to update for the next step.

### 2) Update the PostgreSQL Endpoint {#update-the-postgresql-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the PostgreSQL service endpoint:

```shell
mc admin config set ALIAS/ notify_postgres:IDENTIFIER \
   connection_string="ENDPOINT" \
   table="<string>" \
   format="<string>" \
   max_open_connections="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The following configuration settings are the *minimum* required for a PostgreSQL service endpoint:

- [`notify_postgres connection_string`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.connection_string)
- [`notify_postgres table`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.table)
- [`notify_postgres format`](/reference/minio-server/settings/notifications/postgresql/#mc-conf.notify_postgres.format)

All other configuration settings are *optional*. See [PostgreSQL Notification Settings](/reference/minio-server/settings/notifications/postgresql/#minio-server-config-bucket-notification-postgresql) for a complete list of PostgreSQL configuration settings.

### 3) Restart the MinIO Deployment {#id4}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured PostgreSQL target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:postgresql
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated PostgreSQL service endpoint and check the PostgreSQL service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
