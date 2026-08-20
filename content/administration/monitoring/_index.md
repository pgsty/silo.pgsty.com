---
title: "Monitoring Bucket and Object Events"
url: "/administration/monitoring/"
weight: 130
icon: fa-solid fa-bell
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/monitoring.rst
upstream_modified: false
---

<a id="monitoring-bucket-and-object-events"></a>

## Bucket Notifications {#bucket-notifications}

MinIO bucket notifications allow administrators to send notifications to supported external services on certain object or bucket events. MinIO supports bucket and object-level S3 events similar to the [Amazon S3 Event Notifications](https://docs.aws.amazon.com/AmazonS3/latest/userguide/NotificationHowTo.html).

MinIO supports publishing bucket or object events to the following supported targets on certain supported events.

- [Publish Events to AMQP (RabbitMQ)](/administration/monitoring/publish-events-to-amqp/#minio-bucket-notifications-publish-amqp)
- [Publish Events to MQTT](/administration/monitoring/publish-events-to-mqtt/#minio-bucket-notifications-publish-mqtt)
- [Publish Events to NATS](/administration/monitoring/publish-events-to-nats/#minio-bucket-notifications-publish-nats)
- [Publish Events to NSQ](/administration/monitoring/publish-events-to-nsq/#minio-bucket-notifications-publish-nsq)
- [Publish Events to Elasticsearch](/administration/monitoring/publish-events-to-elasticsearch/#minio-bucket-notifications-publish-elasticsearch)
- [Publish Events to Kafka](/administration/monitoring/publish-events-to-kafka/#minio-bucket-notifications-publish-kafka)
- [Publish Events to MySQL](/administration/monitoring/publish-events-to-mysql/#minio-bucket-notifications-publish-mysql)
- [Publish Events to PostgreSQL](/administration/monitoring/publish-events-to-postgresql/#minio-bucket-notifications-publish-postgresql)
- [Publish Events to Redis](/administration/monitoring/publish-events-to-redis/#minio-bucket-notifications-publish-redis)
- [Publish Events to Webhook](/administration/monitoring/publish-events-to-webhook/#minio-bucket-notifications-publish-webhook)

See [Bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for more complete documentation on MinIO Bucket Notifications.

## Deployment Metrics {#deployment-metrics}

MinIO provides a Prometheus-compatible endpoint for supporting time-series querying of metrics.

## Server Logs {#server-logs}

MinIO provides the following interfaces for remotely reading server logs:

- The [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) command returns the specified server’s console output.
- MinIO supports pushing server logs to an HTTP webhook for further ingestion. See [Publish Server Logs to HTTP Webhook](/operations/monitoring/minio-logging/#minio-logging-publish-server-logs) for more information.
