---
title: "Elasticsearch Notification Settings"
url: "/reference/minio-server/settings/notifications/elasticsearch/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="elasticsearch-notification-settings"></a>
<a id="minio-server-config-bucket-notification-elasticsearch"></a>
<a id="minio-server-envvar-bucket-notification-elasticsearch"></a>

This page documents settings for configuring an Elasticsearch service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to Elasticsearch](/administration/monitoring/publish-events-to-elasticsearch/#minio-bucket-notifications-publish-elasticsearch) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Multiple Elasticsearch Targets {#multiple-elasticsearch-targets}

You can specify multiple Elasticsearch service endpoints by appending a unique identifier `_ID` for each set of related settings. For example, the following commands set two distinct Elasticsearch service endpoints as `PRIMARY` and `SECONDARY`, respectively:

### Examples {#examples}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}

```shell
export MINIO_NOTIFY_ELASTICSEARCH_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_ELASTICSEARCH_URL_PRIMARY="https://user:password@elasticsearch-endpoint.example.net:9200"
export MINIO_NOTIFY_ELASTICSEARCH_INDEX_PRIMARY="bucketevents"
export MINIO_NOTIFY_ELASTICSEARCH_FORMAT_PRIMARY="namespace"

export MINIO_NOTIFY_ELASTICSEARCH_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_ELASTICSEARCH_URL_SECONDARY="https://user:password@elasticsearch-endpoint.example.net:9200"
export MINIO_NOTIFY_ELASTICSEARCH_INDEX_SECONDARY="bucketevents"
export MINIO_NOTIFY_ELASTICSEARCH_FORMAT_SECONDARY="namespace"
```

{{% /tab %}}
{{% tab header="Configuration Settings" %}}

```shell
mc admin config set notify_elasticsearch:primary \
   url="user:password@https://elasticsearch-endpoint.example.net:9200" \
   index="bucketevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]

mc admin config set notify_elasticsearch:secondary \
   url="user:password@https://elasticsearch-endpoint.example.net:9200" \
   index="bucketevents" \
   format="namespace" \
   [ARGUMENT=VALUE ...]
```

Notice that for configuration settings, the unique identifier appends to `notify_elasticsearch` only, not to each individual argument.
{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_ENABLE` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to an Elasticsearch service endpoint.

Defaults to `off`.

Requires specifying the following additional environment variables if set to `on`:

- [`MINIO_NOTIFY_ELASTICSEARCH_URL`](#envvar.MINIO_NOTIFY_ELASTICSEARCH_URL)
- [`MINIO_NOTIFY_ELASTICSEARCH_INDEX`](#envvar.MINIO_NOTIFY_ELASTICSEARCH_INDEX)
- [`MINIO_NOTIFY_ELASTICSEARCH_FORMAT`](#envvar.MINIO_NOTIFY_ELASTICSEARCH_FORMAT)
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch` {#mc-conf.notify_elasticsearch}

*mc-conf*

The top-level configuration key for defining an Elasticsearch service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an Elasticsearch service endpoint. The following arguments are *required* for each target:

- [`url`](#mc-conf.notify_elasticsearch.url)
- [`index`](#mc-conf.notify_elasticsearch.index)
- [`format`](#mc-conf.notify_elasticsearch.format)

Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_elasticsearch \
  url="https://user:password@elasticsearch.example.com:9200" \
  [ARGUMENT="VALUE"] ... \
```

{{% /tab %}}
{{< /tabpane >}}

### URL {#url}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_URL` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_URL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch url` {#mc-conf.notify_elasticsearch.url}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Elasticsearch service endpoint to which MinIO publishes bucket events. For example, `https://elasticsearch.example.com:9200`.

MinIO supports passing authentication information using as URL parameters using the format `PROTOCOL://USERNAME:PASSWORD@HOSTNAME:PORT`.

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-27T05-56-19Z**

MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.
{{% /alert %}}

### Index {#index}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_INDEX` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_INDEX}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch index` {#mc-conf.notify_elasticsearch.index}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the name of the Elasticsearch index in which to store or update MinIO bucket events. Elasticsearch automatically creates the index if it does not exist.

### Format {#format}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_FORMAT` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_FORMAT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch format` {#mc-conf.notify_elasticsearch.format}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the format of event data written to the Elasticsearch index. MinIO supports the following values:

**`namespace`**

> For each bucket event, MinIO creates a JSON document with the bucket and object name from the event as the document ID and the actual event as part of the document body. Additional updates to that object modify the existing index entry for that object. Similarly, deleting the object also deletes the corresponding index entry.

**`access`**

> For each bucket event, MinIO creates a JSON document with the event details and appends it to the index with an Elasticsearch-generated random ID. Additional updates to an object result in new index entries, and existing entries remain unmodified.

### Username {#username}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_USERNAME` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_USERNAME}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch username` {#mc-conf.notify_elasticsearch.username}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The username for connecting to an Elasticsearch service endpoint which enforces authentication.

### Password {#password}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_PASSWORD` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_PASSWORD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch password` {#mc-conf.notify_elasticsearch.password}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The password for connecting to an Elasticsearch service endpoint which enforces authentication.

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /alert %}}

### Queue Directory {#queue-directory}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_QUEUE_DIR` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch queue_dir` {#mc-conf.notify_elasticsearch.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the Elasticsearch service is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_QUEUE_LIMIT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch queue_limit` {#mc-conf.notify_elasticsearch.queue_limit}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_ELASTICSEARCH_COMMENT` {#envvar.MINIO_NOTIFY_ELASTICSEARCH_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_elasticsearch comment` {#mc-conf.notify_elasticsearch.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate with the Elasticsearch configuration.
