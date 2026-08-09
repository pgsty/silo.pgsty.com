---
title: "MySQL Notification Settings"
url: "/reference/minio-server/settings/notifications/mysql/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mysql-notification-settings"></a>
<a id="minio-server-config-bucket-notification-mysql"></a>
<a id="minio-server-envvar-bucket-notification-mysql"></a>

This page documents settings for configuring a MYSQL service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to MySQL](/administration/monitoring/publish-events-to-mysql/#minio-bucket-notifications-publish-mysql) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Multiple MYSQL Targets {#multiple-mysql-targets}

You can specify multiple MySQL service endpoints by appending a unique identifier `_ID` for each set of related MySQL settings on to the top level key.

### Examples {#examples}

The following commands set two distinct MySQL service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}

```shell
export MINIO_NOTIFY_MYSQL_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_MYSQL_DSN_STRING_PRIMARY="username:password@tcp(mysql.example.com:3306)/miniodb"
export MINIO_NOTIFY_MYSQL_TABLE_PRIMARY="minioevents"
export MINIO_NOTIFY_MYSQL_FORMAT_PRIMARY="namespace"

export MINIO_NOTIFY_MYSQL_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_MYSQL_DSN_STRING_SECONDARY="username:password@tcp(mysql.example.com:3306)/miniodb"
export MINIO_NOTIFY_MYSQL_TABLE_SECONDARY="minioevents"
export MINIO_NOTIFY_MYSQL_FORMAT_SECONDARY="namespace"
```

With these settings, [`MINIO_NOTIFY_MYSQL_ENABLE_PRIMARY`](#envvar.MINIO_NOTIFY_MYSQL_ENABLE) indicates the environment variable is associated to a MySQL service endpoint with ID of `PRIMARY`.
{{% /tab %}}
{{% tab header="Configuration Settings" %}}

```shell
mc admin config set notify_mysql:primary \
   dsn_string="username:password@tcp(mysql.example.com:3306)/miniodb"
   table="minioevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]

mc admin config set notify_mysql:secondary \
   dsn_string="username:password@tcp(mysql.example.com:3306)/miniodb"
   table="minioevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]
```

{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}

##### `MINIO_NOTIFY_MYSQL_ENABLE` {#envvar.MINIO_NOTIFY_MYSQL_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to a MySQL service endpoint.

Defaults to `off`.

Requires specifying the following additional environment variables if set to `on`:

- [`MINIO_NOTIFY_MYSQL_DSN_STRING`](#envvar.MINIO_NOTIFY_MYSQL_DSN_STRING)
- [`MINIO_NOTIFY_MYSQL_TABLE`](#envvar.MINIO_NOTIFY_MYSQL_TABLE)
- [`MINIO_NOTIFY_MYSQL_FORMAT`](#envvar.MINIO_NOTIFY_MYSQL_FORMAT)
{{% /tab %}}
{{% tab header="Configuration Settings" %}}

##### `notify_mysql` {#mc-conf.notify_mysql}

*mc-conf*

The top-level configuration key for defining an MySQL service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an MySQL service endpoint. The following arguments are *required* for each target:

- [`dsn_string`](#mc-conf.notify_mysql.dsn_string)
- [`table`](#mc-conf.notify_mysql.table)
- [`format`](#mc-conf.notify_mysql.format)

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_mysql \
  dsn_string="username:password@tcp(mysql.example.com:3306)/miniodb"
  table="minioevents" \
  format="namespace" \
  [ARGUMENT="VALUE"] ... \
```

{{% /tab %}}
{{< /tabpane >}}

### Data Source Name (DSN) String {#data-source-name-dsn-string}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_DSN_STRING` {#envvar.MINIO_NOTIFY_MYSQL_DSN_STRING}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql dsn_string` {#mc-conf.notify_mysql.dsn_string}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the data source name (DSN) of the MySQL service endpoint. MinIO expects the following format:

`<user>:<password>@tcp(<host>:<port>)/<database>`

For example:

`"username:password@tcp(mysql.example.com:3306)/miniodb"`

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-27T05-56-19Z**

MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.
{{% /alert %}}

### Table {#table}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_TABLE` {#envvar.MINIO_NOTIFY_MYSQL_TABLE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql table` {#mc-conf.notify_mysql.table}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the name of the MySQL table to which MinIO publishes event notifications.

### Format {#format}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_FORMAT` {#envvar.MINIO_NOTIFY_MYSQL_FORMAT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql format` {#mc-conf.notify_mysql.format}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the format of event data written to the MySQL service endpoint. MinIO supports the following values:

**`namespace`**

> For each bucket event, MinIO creates a JSON document with the bucket and object name from the event as the document ID and the actual event as part of the document body. Additional updates to that object modify the existing table entry for that object. Similarly, deleting the object also deletes the corresponding table entry.

**`access`**

> For each bucket event, MinIO creates a JSON document with the event details and appends it to the table with a MySQL-generated random ID. Additional updates to an object result in new index entries, and existing entries remain unmodified.

### Max Open Connections {#max-open-connections}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_MAX_OPEN_CONNECTIONS` {#envvar.MINIO_NOTIFY_MYSQL_MAX_OPEN_CONNECTIONS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql max_open_connections` {#mc-conf.notify_mysql.max_open_connections}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum number of open connections to the MySQL database.

Defaults to `2`.

### Queue Directory {#queue-directory}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_QUEUE_DIR` {#envvar.MINIO_NOTIFY_MYSQL_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql queue_dir` {#mc-conf.notify_mysql.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the MySQL server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_MYSQL_QUEUE_LIMIT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql queue_limit` {#mc-conf.notify_mysql.queue_limit}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_MYSQL_COMMENT` {#envvar.MINIO_NOTIFY_MYSQL_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_mysql comment` {#mc-conf.notify_mysql.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate with the MySQL configuration.
