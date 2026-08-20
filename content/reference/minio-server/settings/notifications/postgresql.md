---
title: "PostgreSQL Notification Settings"
url: "/reference/minio-server/settings/notifications/postgresql/"
weight: 80
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications/postgresql.rst
upstream_modified: false
---

<a id="postgresql-notification-settings"></a>
<a id="minio-server-config-bucket-notification-postgresql"></a>
<a id="minio-server-envvar-bucket-notification-postgresql"></a>

This page documents settings for configuring an POSTGRES service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to PostgreSQL](/administration/monitoring/publish-events-to-postgresql/#minio-bucket-notifications-publish-postgresql) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Multiple PostgreSQL Targets {#multiple-postgresql-targets}

You can specify multiple PostgreSQL service endpoints by appending a unique identifier `_ID` for each set of related PostgreSQL settings on to the top level key. For example, the following commands set two distinct PostgreSQL service endpoints as `PRIMARY` and `SECONDARY` respectively:

```shell {tab="Environment Variables" group="environment-variables-configuration-settings" value="environment-variables"}
export MINIO_NOTIFY_POSTGRES_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_POSTGRES_CONNECTION_STRING_PRIMARY="host=postgresql-endpoint.example.net port=4222..."
export MINIO_NOTIFY_POSTGRES_TABLE_PRIMARY="minioevents"
export MINIO_NOTIFY_POSTGRES_FORMAT_PRIMARY="namespace"

export MINIO_NOTIFY_POSTGRES_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_POSTGRES_CONNECTION_STRING_SECONDARY="host=postgresql-endpoint.example.net port=4222..."
export MINIO_NOTIFY_POSTGRES_TABLE_SECONDARY="minioevents"
export MINIO_NOTIFY_POSTGRES_FORMAT_SECONDARY="namespace"
```

```shell {tab="Configuration Settings" value="configuration-settings"}
mc admin config set notify_postgres:primary \
   connection_string="host=postgresql.example.com port=5432..."
   table="minioevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]

mc admin config set notify_postgres:secondary \
   connection_string="host=postgresql.example.com port=5432..."
   table="minioevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]
```

With these settings, [`MINIO_NOTIFY_POSTGRES_ENABLE_PRIMARY`](#envvar.MINIO_NOTIFY_POSTGRES_ENABLE) indicates the environment variable is associated to an PostgreSQL service endpoint with ID of `PRIMARY`.

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_ENABLE` {#envvar.MINIO_NOTIFY_POSTGRES_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to a PostgreSQL service endpoint.

Defaults to `off`.

Requires specifying the following additional environment variables if set to `on`:

- [`MINIO_NOTIFY_POSTGRES_CONNECTION_STRING`](#envvar.MINIO_NOTIFY_POSTGRES_CONNECTION_STRING)
- [`MINIO_NOTIFY_POSTGRES_TABLE`](#envvar.MINIO_NOTIFY_POSTGRES_TABLE)
- [`MINIO_NOTIFY_POSTGRES_FORMAT`](#envvar.MINIO_NOTIFY_POSTGRES_FORMAT)
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres` {#mc-conf.notify_postgres}

*mc-conf*

The top-level configuration key for defining an PostgreSQL service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an PostgreSQL service endpoint. The following arguments are *required* for each target:

- [`connection_string`](#mc-conf.notify_postgres.connection_string)
- [`table`](#mc-conf.notify_postgres.table)
- [`format`](#mc-conf.notify_postgres.format)

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_postgres                            \
  connection_string="host=postgresql.example.com port=5432..." \
  table="minioevents"                                          \
  format="namespace"                                           \
  [ARGUMENT="VALUE"] ...
```
{{< /tab >}}
{{< /tabs >}}

### Connection String {#connection-string}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_CONNECTION_STRING` {#envvar.MINIO_NOTIFY_POSTGRES_CONNECTION_STRING}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres connection_string` {#mc-conf.notify_postgres.connection_string}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the [URI connection string](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING) of the PostgreSQL service endpoint. MinIO supports `key=value` format for the PostgreSQL connection string. For example:

`"host=https://postgresql.example.com port=5432 ..."`

For more complete documentation on supported PostgreSQL connection string parameters, see the [PostgreSQL Connection Strings documentation](https://www.postgresql.org/docs/current/libpq-connect.html#LIBPQ-CONNSTRING).

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.

### Table {#table}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_TABLE` {#envvar.MINIO_NOTIFY_POSTGRES_TABLE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres table` {#mc-conf.notify_postgres.table}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the name of the PostgreSQL table to which MinIO publishes event notifications.

### Format {#format}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_FORMAT` {#envvar.MINIO_NOTIFY_POSTGRES_FORMAT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres format` {#mc-conf.notify_postgres.format}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the format of event data written to the PostgreSQL service endpoint. MinIO supports the following values:

**`namespace`**

> For each bucket event, MinIO creates a JSON document with the bucket and object name from the event as the document ID and the actual event as part of the document body. Additional updates to that object modify the existing table entry for that object. Similarly, deleting the object also deletes the corresponding table entry.

**`access`**

> For each bucket event, MinIO creates a JSON document with the event details and appends it to the table with a PostgreSQL-generated random ID. Additional updates to an object result in new index entries, and existing entries remain unmodified.

### Max Open Connections {#max-open-connections}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_MAX_OPEN_CONNECTIONS` {#envvar.MINIO_NOTIFY_POSTGRES_MAX_OPEN_CONNECTIONS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres max_open_connections` {#mc-conf.notify_postgres.max_open_connections}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum number of open connections to the PostgreSQL database.

Defaults to `2`.

### Queue Directory {#queue-directory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_QUEUE_DIR` {#envvar.MINIO_NOTIFY_POSTGRES_QUEUE_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres queue_dir` {#mc-conf.notify_postgres.queue_dir}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the PostgreSQL server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_POSTGRES_QUEUE_LIMIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres queue_limit` {#mc-conf.notify_postgres.queue_limit}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_POSTGRES_COMMENT` {#envvar.MINIO_NOTIFY_POSTGRES_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_postgres comment` {#mc-conf.notify_postgres.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate with the PostgreSQL configuration.
