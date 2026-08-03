---
title: "Bucket notifications"
url: "/administration/monitoring/bucket-notifications/"
weight: 10
icon: fa-solid fa-bell
minio_origin: true
silo_modified: true
---

<a id="bucket-notifications"></a>
<a id="minio-bucket-notifications"></a>

MinIO bucket notifications allow administrators to send notifications to supported external services on certain object or bucket events. MinIO supports bucket and object-level S3 events similar to the [Amazon S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html).

## Supported notification targets {#supported-notification-targets}

MinIO supports publishing event notifications to the following targets:

<table>
  <thead>
    <tr>
      <th><p>Target</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>AMQP (RabbitMQ)</p></td>
      <td><p>Publish notifications to an AMQP service such as
<a href="https://www.rabbitmq.com">RabbitMQ</a>.</p><p>See <a href="/administration/monitoring/publish-events-to-amqp/#minio-bucket-notifications-publish-amqp">Publish Events to AMQP (RabbitMQ)</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>MQTT</p></td>
      <td><p>Publish notifications to an <a href="https://www.mqtt.org/">MQTT</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-mqtt/#minio-bucket-notifications-publish-mqtt">Publish Events to MQTT</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>NATS</p></td>
      <td><p>Publish notifications to a <a href="https://nats.io/">NATS</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-nats/#minio-bucket-notifications-publish-nats">Publish Events to NATS</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>NSQ</p></td>
      <td><p>Publish notifications to a <a href="https://nsq.io/">NSQ</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-nsq/#minio-bucket-notifications-publish-nsq">Publish Events to NSQ</a> for a tutorial</p></td>
    </tr>
    <tr>
      <td><p>Elasticsearch</p></td>
      <td><p>Publish notifications to a <a href="https://www.elastic.co/">Elasticsearch</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-elasticsearch/#minio-bucket-notifications-publish-elasticsearch">Publish Events to Elasticsearch</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>Kafka</p></td>
      <td><p>Publish notifications to a <a href="https://kafka.apache.org/">Kafka</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-kafka/#minio-bucket-notifications-publish-kafka">Publish Events to Kafka</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>MySQL</p></td>
      <td><p>Publish notifications to a <a href="https://www.mysql.com/">MySQL</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-mysql/#minio-bucket-notifications-publish-mysql">Publish Events to MySQL</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>PostgreSQL</p></td>
      <td><p>Publish notifications to a <a href="https://www.postgresql.org/">PostgreSQL</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-postgresql/#minio-bucket-notifications-publish-postgresql">Publish Events to PostgreSQL</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>Redis</p></td>
      <td><p>Publish notifications to a <a href="https://redis.io/">Redis</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-redis/#minio-bucket-notifications-publish-redis">Publish Events to Redis</a> for a tutorial.</p></td>
    </tr>
    <tr>
      <td><p>webhook</p></td>
      <td><p>Publish notifications to a <a href="https://en.wikipedia.org/wiki/Webhook">Webhook</a> service.</p><p>See <a href="/administration/monitoring/publish-events-to-webhook/#minio-bucket-notifications-publish-webhook">Publish Events to Webhook</a> for a tutorial.</p></td>
    </tr>
  </tbody>
</table>

## Asynchronous vs synchronous bucket notifications {#asynchronous-vs-synchronous-bucket-notifications}

{{% alert color="info" %}}
**Added: RELEASE.2023-06-23T20-26-00Z**

MinIO supports either asynchronous (default) or synchronous bucket notifications for *all* remote targets.
{{% /alert %}}

With asynchronous delivery, MinIO fires the event at the configured remote and does *not* wait for a response before continuing to the next event. Asynchronous bucket notification prioritizes sending events with the risk of some events being lost if the remote target has a transient issue during transit or processing.

With synchronous delivery, MinIO fires the event at the configured remote and then waits for the remote to confirm a successful receipt before continuing to the next event. Synchronous bucket notification prioritizes delivery of events with the risk of a slower event-send rate and queue fill.

To enable synchronous bucket notifications for *all configured remote targets*, use either of the following settings:

- Set the [`MINIO_API_SYNC_EVENTS`](/reference/minio-server/settings/notifications/#envvar.MINIO_API_SYNC_EVENTS) environment variable to `on` and restart the MinIO deployment.
- Set the [`api.sync_events`](/reference/minio-server/settings/notifications/#mc-conf.api.sync_events) configuration setting to `on` and restart the MinIO deployment.

{{% alert color="info" %}}
**Note**

For synchronous and asynchronous events, MinIO maintains a per-remote queue where it stores unsent and pending events. The queue limit defaults to `100000`.

MinIO discards new events when the queue is full.

You can increase the queue size as necessary to better accommodate the rate of event send and processing of the MinIO deployment and remote target. Use the `QUEUE_LIMIT` environment variable or configuration setting for your notification method to modify this limit.

For asynchronous events, MinIO allows a maximum of `50000` concurrent `send` calls.
{{% /alert %}}

<a id="minio-bucket-notifications-event-types"></a>

## Supported S3 event types {#supported-s3-event-types}

MinIO bucket notifications are compatible with [Amazon S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html). This section lists all supported events.

### Object events {#object-events}

MinIO supports triggering notifications on the following S3 object events:

<a id="data.s3:ObjectAccessed:Get"></a>

##### `s3:ObjectAccessed:Get` {#data.s3-ObjectAccessed-Get}

*data*

<a id="data.s3:ObjectAccessed:GetLegalHold"></a>

##### `s3:ObjectAccessed:GetLegalHold` {#data.s3-ObjectAccessed-GetLegalHold}

*data*

<a id="data.s3:ObjectAccessed:GetRetention"></a>

##### `s3:ObjectAccessed:GetRetention` {#data.s3-ObjectAccessed-GetRetention}

*data*

<a id="data.s3:ObjectAccessed:Head"></a>

##### `s3:ObjectAccessed:Head` {#data.s3-ObjectAccessed-Head}

*data*

<a id="data.s3:ObjectCreated:CompleteMultipartUpload"></a>

##### `s3:ObjectCreated:CompleteMultipartUpload` {#data.s3-ObjectCreated-CompleteMultipartUpload}

*data*

<a id="data.s3:ObjectCreated:Copy"></a>

##### `s3:ObjectCreated:Copy` {#data.s3-ObjectCreated-Copy}

*data*

<a id="data.s3:ObjectCreated:DeleteTagging"></a>

##### `s3:ObjectCreated:DeleteTagging` {#data.s3-ObjectCreated-DeleteTagging}

*data*

<a id="data.s3:ObjectCreated:Post"></a>

##### `s3:ObjectCreated:Post` {#data.s3-ObjectCreated-Post}

*data*

<a id="data.s3:ObjectCreated:Put"></a>

##### `s3:ObjectCreated:Put` {#data.s3-ObjectCreated-Put}

*data*

<a id="data.s3:ObjectCreated:PutLegalHold"></a>

##### `s3:ObjectCreated:PutLegalHold` {#data.s3-ObjectCreated-PutLegalHold}

*data*

<a id="data.s3:ObjectCreated:PutRetention"></a>

##### `s3:ObjectCreated:PutRetention` {#data.s3-ObjectCreated-PutRetention}

*data*

<a id="data.s3:ObjectCreated:PutTagging"></a>

##### `s3:ObjectCreated:PutTagging` {#data.s3-ObjectCreated-PutTagging}

*data*

<a id="data.s3:ObjectRemoved:Delete"></a>

##### `s3:ObjectRemoved:Delete` {#data.s3-ObjectRemoved-Delete}

*data*

<a id="data.s3:ObjectRemoved:DeleteMarkerCreated"></a>

##### `s3:ObjectRemoved:DeleteMarkerCreated` {#data.s3-ObjectRemoved-DeleteMarkerCreated}

*data*

Specify the wildcard `*` character to select all events related to a prefix:

<a id="data.s3:ObjectAccessed:*"></a>

##### `s3:ObjectAccessed:*` {#data.s3-ObjectAccessed}

*data*

Selects all `s3:ObjectAccessed` -prefixed events.

<a id="data.s3:ObjectCreated:*"></a>

##### `s3:ObjectCreated:*` {#data.s3-ObjectCreated}

*data*

Selects all `s3:ObjectCreated` -prefixed events.

<a id="data.s3:ObjectRemoved:*"></a>

##### `s3:ObjectRemoved:*` {#data.s3-ObjectRemoved}

*data*

Selects all `s3:ObjectRemoved` -prefixed events.

### Replication events {#replication-events}

MinIO supports triggering notifications on the following S3 replication events:

<a id="data.s3:Replication:OperationCompletedReplication"></a>

##### `s3:Replication:OperationCompletedReplication` {#data.s3-Replication-OperationCompletedReplication}

*data*

<a id="data.s3:Replication:OperationFailedReplication"></a>

##### `s3:Replication:OperationFailedReplication` {#data.s3-Replication-OperationFailedReplication}

*data*

<a id="data.s3:Replication:OperationMissedThreshold"></a>

##### `s3:Replication:OperationMissedThreshold` {#data.s3-Replication-OperationMissedThreshold}

*data*

<a id="data.s3:Replication:OperationNotTracked"></a>

##### `s3:Replication:OperationNotTracked` {#data.s3-Replication-OperationNotTracked}

*data*

<a id="data.s3:Replication:OperationReplicatedAfterThreshold"></a>

##### `s3:Replication:OperationReplicatedAfterThreshold` {#data.s3-Replication-OperationReplicatedAfterThreshold}

*data*

Specify the wildcard `*` character to select all `s3:Replication` events:

<a id="data.s3:Replication:*"></a>

##### `s3:Replication:*` {#data.s3-Replication}

*data*

### ILM transition events {#ilm-transition-events}

MinIO supports triggering notifications on the following S3 ILM transition events:

<a id="data.s3:ObjectRestore:Post"></a>

##### `s3:ObjectRestore:Post` {#data.s3-ObjectRestore-Post}

*data*

<a id="data.s3:ObjectRestore:Completed"></a>

##### `s3:ObjectRestore:Completed` {#data.s3-ObjectRestore-Completed}

*data*

<a id="data.s3:ObjectTransition:Failed"></a>

##### `s3:ObjectTransition:Failed` {#data.s3-ObjectTransition-Failed}

*data*

<a id="data.s3:ObjectTransition:Complete"></a>

##### `s3:ObjectTransition:Complete` {#data.s3-ObjectTransition-Complete}

*data*

Specify the wildcard `*` character to select all events related to a prefix:

<a id="data.s3:ObjectTransition:*"></a>

##### `s3:ObjectTransition:*` {#data.s3-ObjectTransition}

*data*

Selects all `s3:ObjectTransition` -prefixed events.

<a id="data.s3:ObjectRestore:*"></a>

##### `s3:ObjectRestore:*` {#data.s3-ObjectRestore}

*data*

Selects all `s3:ObjectRestore` -prefixed events.

### Scanner events {#scanner-events}

MinIO supports triggering notifications on the following S3 [scanner](/operations/concepts/scanner/#minio-concepts-scanner) transition events:

<a id="data.s3:Scanner:ManyVersions"></a>

##### `s3:Scanner:ManyVersions` {#data.s3-Scanner-ManyVersions}

*data*

[Scanner](/operations/concepts/scanner/#minio-concepts-scanner) finds objects with more than 1,000 versions.

<a id="data.s3:Scanner:BigPrefix"></a>

##### `s3:Scanner:BigPrefix` {#data.s3-Scanner-BigPrefix}

*data*

[Scanner](/operations/concepts/scanner/#minio-concepts-scanner) finds prefixes with more than 50,000 sub-folders.

### Global events {#global-events}

MinIO supports triggering notifications on the following global events. You can only listen to these events through the [ListenNotification](https://pkg.go.dev/github.com/minio/minio-go/v7#Client.ListenNotification) API:

<a id="data.s3:BucketCreated"></a>

##### `s3:BucketCreated` {#data.s3-BucketCreated}

*data*

<a id="data.s3:BucketRemoved"></a>

##### `s3:BucketRemoved` {#data.s3-BucketRemoved}

*data*

## Payload schema {#payload-schema}

All notification payloads use the same overall schema. Depending on the type of notification, some fields may be omitted or have null values.

```json
{
    "eventVersion": "string",
    "eventSource": "string",
    "awsRegion": "string",
    "eventTime": "string",
    "eventName": "string",
    "userIdentity": {
        "principalId": "string"
    },
    "requestParameters": {
        "key": "value"
    },
    "responseElements": {
        "key": "value"
    },
    "s3": {
        "s3SchemaVersion": "string",
        "configurationId": "string",
        "bucket": {
            "name": "string",
            "ownerIdentity": {
                "principalId": "string"
            },
            "arn": "string"
        },
        "object": {
            "key": "string",
            "size": 10000,
            "eTag": "string",
            "contentType": "string",
            "userMetadata": {
                "key": "string"
            },
            "versionId": "string",
            "sequencer": "string"
        }
    },
    "source": {
        "host": "string",
        "port": "string",
        "userAgent": "string"
    }
}
```

### Example {#example}

The following example is a notification for an `s3:ObjectCreated:Put` event:

```json
{
  "EventName": "s3:ObjectCreated:Put",
  "Key": "test-bucket/image.jpg",
  "Records": [
    {
      "eventVersion": "2.0",
      "eventSource": "minio:s3",
      "awsRegion": "",
      "eventTime": "2025-02-06T01:04:31.998Z",
      "eventName": "s3:ObjectCreated:Put",
      "userIdentity": {
        "principalId": "access_key"
      },
      "requestParameters": {
        "principalId": "access_key",
        "region": "",
        "sourceIPAddress": "192.168.1.10"
      },
      "responseElements": {
        "x-amz-id-2": "dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8",
        "x-amz-request-id": "182178E8B36AC9DF",
        "x-minio-deployment-id": "2369dcb4-348b-4d30-8fc9-61ab089ba4bc",
        "x-minio-origin-endpoint": "https://minio.test.svc.cluster.local"
      },
      "s3": {
        "s3SchemaVersion": "1.0",
        "configurationId": "Config",
        "bucket": {
          "name": "test-bucket",
          "ownerIdentity": {
            "principalId": "access_key"
          },
          "arn": "arn:aws:s3:::test-bucket"
        },
        "object": {
          "key": "image.jpg",
          "size": 84452,
          "eTag": "eb52f8e46f60a27a8a1a704e25757f30",
          "contentType": "image/jpeg",
          "userMetadata": {
            "content-type": "image/jpeg"
          },
          "sequencer": "182178E8B3728CAC"
        }
      },
      "source": {
        "host": "192.168.1.10",
        "port": "",
        "userAgent": "MinIO (linux; amd64) minio-go/v7.0.83"
      }
    }
  ]
}
```
