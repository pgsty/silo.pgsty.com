---
title: "Publish Events to MySQL"
url: "/administration/monitoring/publish-events-to-mysql/"
weight: 70
minio_origin: true
silo_modified: false
---

<a id="publish-events-to-mysql"></a>
<a id="minio-bucket-notifications-publish-mysql"></a>

MinIO supports publishing [bucket notification](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) events to a [MySQL](https://www.mysql.com/) service endpoint. MinIO supports MySQL 5.7.8 and later *only*.

## Add a MySQL Endpoint to a MinIO Deployment {#add-a-mysql-endpoint-to-a-minio-deployment}

The following procedure adds a new MySQL service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#prerequisites}

#### MySQL 5.7.8 and later {#mysql-5-7-8-and-later}

MinIO relies on features introduced with MySQL 5.7.8.

#### MinIO `mc` Command Line Tool {#minio-mc-command-line-tool}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) Add the MySQL Endpoint to MinIO {#add-the-mysql-endpoint-to-minio}

You can configure a new MySQL service endpoint using either environment variables *or* by setting runtime configuration settings.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
MinIO supports specifying the MySQL service endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/notifications/mysql/#minio-server-envvar-bucket-notification-mysql). The [`minio server`](/reference/minio-server/#command-minio.server) process applies the specified settings on its next startup.

The following example code sets *all* environment variables related to configuring a MySQL service endpoint. The minimum *required* variables are:

- [`MINIO_NOTIFY_MYSQL_ENABLE`](/reference/minio-server/settings/notifications/mysql/#envvar.MINIO_NOTIFY_MYSQL_ENABLE)
- [`MINIO_NOTIFY_MYSQL_DSN_STRING`](/reference/minio-server/settings/notifications/mysql/#envvar.MINIO_NOTIFY_MYSQL_DSN_STRING)
- [`MINIO_NOTIFY_MYSQL_TABLE`](/reference/minio-server/settings/notifications/mysql/#envvar.MINIO_NOTIFY_MYSQL_TABLE)
- [`MINIO_NOTIFY_MYSQL_FORMAT`](/reference/minio-server/settings/notifications/mysql/#envvar.MINIO_NOTIFY_MYSQL_FORMAT)

{{% alert color="info" %}}
**Windows**

```shell
   set MINIO_NOTIFY_MYSQL_ENABLE_<IDENTIFIER>="on"
   set MINIO_NOTIFY_MYSQL_DSN_STRING_<IDENTIFIER>="user:password@tcp(hostname:port)/database"
   set MINIO_NOTIFY_MYSQL_TABLE_<IDENTIFIER>="minio-events"
   set MINIO_NOTIFY_MYSQL_FORMAT_<IDENTIFIER>="namespace|access"
   set MINIO_NOTIFY_MYSQL_MAX_OPEN_CONNECTIONS_<IDENTIFIER>="2"
   set MINIO_NOTIFY_MYSQL_QUEUE_DIR_<IDENTIFIER>="/opt/minio/events"
   set MINIO_NOTIFY_MYSQL_QUEUE_LIMIT_<IDENTIFIER>="100000"
   set MINIO_NOTIFY_MYSQL_COMMENT_<IDENTIFIER>="MySQL Event Notification Logging for MinIO"
```
{{% /alert %}}

{{% alert color="info" %}}
**Linux and macOS**

```shell
   export MINIO_NOTIFY_MYSQL_ENABLE_<IDENTIFIER>="on"
   export MINIO_NOTIFY_MYSQL_DSN_STRING_<IDENTIFIER>="user:password@tcp(hostname:port)/database"
   export MINIO_NOTIFY_MYSQL_TABLE_<IDENTIFIER>="minio-events"
   export MINIO_NOTIFY_MYSQL_FORMAT_<IDENTIFIER>="namespace|access"
   export MINIO_NOTIFY_MYSQL_MAX_OPEN_CONNECTIONS_<IDENTIFIER>="2"
   export MINIO_NOTIFY_MYSQL_QUEUE_DIR_<IDENTIFIER>="/opt/minio/events"
   export MINIO_NOTIFY_MYSQL_QUEUE_LIMIT_<IDENTIFIER>="100000"
   export MINIO_NOTIFY_MYSQL_COMMENT_<IDENTIFIER>="MySQL Event Notification Logging for MinIO"
```
{{% /alert %}}

- Replace `<IDENTIFIER>` with a unique descriptive string for the MySQL service endpoint. Use the same `<IDENTIFIER>` value for all environment variables related to the new target service endpoint. The following examples assume an identifier of `PRIMARY`.

  If the specified `<IDENTIFIER>` matches an existing MySQL service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_mysql`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured MySQL endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the DSN of the MySQL service endpoint. MinIO expects the following format:

  `<user>:<password>@tcp(<host>:<port>)/<database>`

  For example:

  `"username:password@tcp(mysql.example.com:3306)/miniodb"`

See [MySQL Service for Bucket Notifications](/reference/minio-server/settings/notifications/mysql/#minio-server-envvar-bucket-notification-mysql) for complete documentation on each environment variable.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
MinIO supports adding or updating MySQL endpoints on a running [`minio server`](/reference/minio-server/#command-minio.server) process using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`notify_mysql`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql) configuration key. You must restart the [`minio server`](/reference/minio-server/#command-minio.server) process to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring an MySQL service endpoint. The minimum *required* settings are:

- [`notify_mysql dsn_string`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.dsn_string)
- [`notify_mysql table`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.table)
- [`notify_mysql format`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.format)

```shell
mc admin config set ALIAS/ notify_mysql:IDENTIFIER \
   dsn_string="<ENDPOINT>" \
   table="<string>" \
   format="<string>" \
   max_open_connections="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

- Replace `IDENTIFIER` with a unique descriptive string for the MySQL service endpoint. The following examples in this procedure assume an identifier of `PRIMARY`.

  If the specified `IDENTIFIER` matches an existing MySQL service endpoint on the MinIO deployment, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get notify_mysql`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured MySQL endpoints on the MinIO deployment.
- Replace `<ENDPOINT>` with the DSN of the MySQL service endpoint. MinIO expects the following format:

  `<user>:<password>@tcp(<host>:<port>)/<database>`

  For example:

  `"username:password@tcp(mysql.example.com:3306)/miniodb"`

See [MySQL Bucket Notification Configuration Settings](/reference/minio-server/settings/notifications/mysql/#minio-server-config-bucket-notification-mysql) for complete documentation on each setting.
{{% /tab %}}
{{< /tabpane >}}

### 1) Restart the MinIO Deployment {#restart-the-minio-deployment}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured MySQL target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:mysql
```

You must specify the ARN resource when configuring bucket notifications with the associated MySQL deployment as a target.

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

   For example, `arn:minio:sqs::primary:mysql`.

**Use jq to parse the JSON for the value**

1. [Install jq](https://stedolan.github.io/jq/)<a id="install-jq"></a>
2. Copy and run the following command, replacing `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment.

   ```shell
   mc admin info --json ALIAS | jq  .info.sqsARN
   ```

   This returns the ARN to use for notifications, such as `arn:minio:sqs::primary:mysql`
{{% /alert %}}

### 3) Configure Bucket Notifications using the MySQL Endpoint as a Target {#configure-bucket-notifications-using-the-mysql-endpoint-as-a-target}

Use the [`mc event add`](/reference/minio-mc/mc-event-add/#command-mc.event.add) command to add a new bucket notification event with the configured MySQL service as a target:

```shell
mc event add ALIAS/BUCKET arn:minio:sqs::primary:mysql \
  --event EVENTS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment.
- Replace `BUCKET` with the name of the bucket in which to configure the event.
- Replace `EVENTS` with a comma-separated list of [events](/reference/minio-mc/mc-event-add/#mc-event-supported-events) for which MinIO triggers notifications.

Use [`mc event ls`](/reference/minio-mc/mc-event-list/#command-mc.event.ls) to view all configured bucket events for a given notification target:

```shell
mc event ls ALIAS/BUCKET arn:minio:sqs::primary:mysql
```

### 4) Validate the Configured Events {#validate-the-configured-events}

Perform an action on the bucket for which you configured the new event and check the MySQL service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```

## Update a MySQL Endpoint in a MinIO Deployment {#update-a-mysql-endpoint-in-a-minio-deployment}

The following procedure updates an existing MySQL service endpoint for supporting [bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) in a MinIO deployment.

### Prerequisites {#id1}

#### MySQL 5.7.8 and later {#id2}

MinIO relies on features introduced with MySQL 5.7.8.

#### MinIO `mc` Command Line Tool {#id3}

This procedure uses the [`mc`](/reference/minio-mc/#command-mc) command line tool for certain actions. See the `mc` [Quickstart](/reference/minio-mc/#mc-install) for installation instructions.

### 1) List Configured MySQL Endpoints In The Deployment {#list-configured-mysql-endpoints-in-the-deployment}

Use the [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) command to list the currently configured MySQL service endpoints in the deployment:

```shell
mc admin config get ALIAS/ notify_mysql
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.

The command output resembles the following:

```shell
notify_mysql:primary format="namespace" table="minio_images" dsn_string="user:pass@tcp(mysql.example.com:3306)/miniodb"
notify_mysql:secondary format="namespace" table="minio_images" dsn_string="user:pass@tcp(mysql.example.com:3306)/miniodb"
```

The [`notify_mysql`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql) key is the top-level configuration key for an [MySQL Notification Settings](/reference/minio-server/settings/notifications/mysql/#minio-server-config-bucket-notification-mysql). The [`dsn_string`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.dsn_string) key specifies the MySQL service endpoint for the given *notify_mysql* key. The `notify_mysql:<IDENTIFIER>` suffix describes the unique identifier for that MySQL service endpoint.

Note the identifier for the MySQL service endpoint you want to update for the next step.

### 2) Update the MySQL Endpoint {#update-the-mysql-endpoint}

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to set the new configuration for the MySQL service endpoint:

```shell
mc admin config set ALIAS/ notify_mysql:IDENTIFIER \
   dsn_string="<ENDPOINT>" \
   table="<string>" \
   format="<string>" \
   max_open_connections="<string>" \
   queue_dir="<string>" \
   queue_limit="<string>" \
   comment="<string>"
```

The following configuration settings are the *minimum required* for a MySQL service endpoint:

- [`notify_mysql dsn_string`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.dsn_string)
- [`notify_mysql table`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.table)
- [`notify_mysql format`](/reference/minio-server/settings/notifications/mysql/#mc-conf.notify_mysql.format)

All other configuration settings are *optional*. See [MySQL Notification Settings](/reference/minio-server/settings/notifications/mysql/#minio-server-config-bucket-notification-mysql) for a complete list of MySQL configuration settings.

### 3) Restart the MinIO Deployment {#id4}

You must restart the MinIO deployment to apply the configuration changes. Use the [`mc admin service restart`](/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart) command to restart the deployment.

```shell
mc admin service restart ALIAS
```

Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment to restart.

The [`minio server`](/reference/minio-server/#command-minio.server) process prints a line on startup for each configured MySQL target similar to the following:

```shell
SQS ARNs: arn:minio:sqs::primary:mysql
```

### 4) Validate the Changes {#validate-the-changes}

Perform an action on a bucket which has an event configuration using the updated MySQL service endpoint and check the MySQL service for the notification data. The action required depends on which [`events`](/reference/minio-mc/mc-event-add/#mc.event.add.-event) were specified when configuring the bucket notification.

For example, if the bucket notification configuration includes the `s3:ObjectCreated:Put` event, you can use the [`mc cp`](/reference/minio-mc/mc-cp/#command-mc.cp) command to create a new object in the bucket and trigger a notification.

```shell
mc cp ~/data/new-object.txt ALIAS/BUCKET
```
