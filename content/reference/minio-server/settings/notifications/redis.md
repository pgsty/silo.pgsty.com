---
title: "Redis Notification Settings"
url: "/reference/minio-server/settings/notifications/redis/"
weight: 90
minio_origin: true
silo_modified: false
---

<a id="redis-notification-settings"></a>
<a id="minio-server-config-bucket-notification-redis"></a>
<a id="minio-server-envvar-bucket-notification-redis"></a>

This page documents settings for configuring a Redis service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to Redis](/administration/monitoring/publish-events-to-redis/#minio-bucket-notifications-publish-redis) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Multiple Redis Targets {#multiple-redis-targets}

You can specify multiple Redis service endpoints by appending a unique identifier `_ID` to the end of the top level key for each set of related Redis settings. For example, the following commands set two distinct Redis service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
```shell
export MINIO_NOTIFY_REDIS_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_REDIS_ADDRESS_PRIMARY="redis-endpoint.example.net:9200"
export MINIO_NOTIFY_REDIS_KEY_PRIMARY="bucketevents"
export MINIO_NOTIFY_REDIS_FORMAT_PRIMARY="namespace"


export MINIO_NOTIFY_REDIS_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_REDIS_REDIS_ADDRESS_SECONDARY="redis-endpoint2.example.net:9200"
export MINIO_NOTIFY_REDIS_KEY_SECONDARY="bucketevents"
export MINIO_NOTIFY_REDIS_FORMAT_SECONDARY="namespace"
```
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
```shell
mc admin config set notify_redis:primary              \
   address="redis-endpoint.example.net:9200"  \
   key="bucketevents"                                 \
   format="namespace"                                 \
   [ARGUMENT="VALUE"] ...                             \

mc admin config set notify_redis:secondary            \
   address="redis-endpoint2.example.net:9200" \
   key="bucketevents"                                 \
   format="namespace"                                 \
   [ARGUMENT="VALUE"] ...
```
{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_ENABLE` {#envvar.MINIO_NOTIFY_REDIS_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to a Redis service endpoint.

Defaults to `off`.

Requires specifying the following additional environment variables if set to `on`:

- [`MINIO_NOTIFY_REDIS_ADDRESS`](#envvar.MINIO_NOTIFY_REDIS_ADDRESS)
- [`MINIO_NOTIFY_REDIS_KEY`](#envvar.MINIO_NOTIFY_REDIS_KEY)
- [`MINIO_NOTIFY_REDIS_FORMAT`](#envvar.MINIO_NOTIFY_REDIS_FORMAT)
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis` {#mc-conf.notify_redis}

*mc-conf*

The top-level configuration key for defining an Redis server/broker endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an Redis server/broker endpoint. The following arguments are *required* for each endpoint:

- [`address`](#mc-conf.notify_redis.address)
- [`key`](#mc-conf.notify_redis.key)
- [`format`](#mc-conf.notify_redis.format)

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_redis \
   address="ENDPOINT" \
   key="<string>" \
   format="<string>" \
   [ARGUMENT="VALUE"] ... \
```
{{% /tab %}}
{{< /tabpane >}}

### Address {#address}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_ADDRESS` {#envvar.MINIO_NOTIFY_REDIS_ADDRESS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis address` {#mc-conf.notify_redis.address}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Redis service endpoint to which MinIO publishes bucket events. For example, `redis.example.com:6369`.

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-27T05-56-19Z**

MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.
{{% /alert %}}

### Key {#key}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_KEY` {#envvar.MINIO_NOTIFY_REDIS_KEY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis key` {#mc-conf.notify_redis.key}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Redis key to use for storing and updating events. Redis auto-creates the key if it does not exist.

### Format {#format}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_FORMAT` {#envvar.MINIO_NOTIFY_REDIS_FORMAT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis format` {#mc-conf.notify_redis.format}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the format of event data written to the Redis service endpoint. MinIO supports the following values:

**`namespace`**

> For each bucket event, MinIO creates a JSON document with the bucket and object name from the event as the document ID and the actual event as part of the document body. Additional updates to that object modify the existing index entry for that object. Similarly, deleting the object also deletes the corresponding index entry.

**`access`**

> For each bucket event, MinIO creates a JSON document with the event details and appends it to the key with a Redis-generated random ID. Additional updates to an object result in new index entries, and existing entries remain unmodified.

### Password {#password}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_PASSWORD` {#envvar.MINIO_NOTIFY_REDIS_PASSWORD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis password` {#mc-conf.notify_redis.password}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the password for the Redis server.

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /alert %}}

### User {#user}

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2024-03-21T23-13-43Z**

{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_USER` {#envvar.MINIO_NOTIFY_REDIS_USER}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis user` {#mc-conf.notify_redis.user}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the user for the Redis server.

### Queue Directory {#queue-directory}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_QUEUE_DIR` {#envvar.MINIO_NOTIFY_REDIS_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis queue_dir` {#mc-conf.notify_redis.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the Redis server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_REDIS_QUEUE_LIMIT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis queue_limit` {#mc-conf.notify_redis.queue_limit}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_NOTIFY_REDIS_COMMENT` {#envvar.MINIO_NOTIFY_REDIS_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `notify_redis comment` {#mc-conf.notify_redis.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate with the Redis configuration.
