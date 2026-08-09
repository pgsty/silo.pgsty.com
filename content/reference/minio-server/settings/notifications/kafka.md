---
title: "Kafka Notification Settings"
url: "/reference/minio-server/settings/notifications/kafka/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="kafka-notification-settings"></a>
<a id="minio-server-config-bucket-notification-kafka"></a>
<a id="minio-server-envvar-bucket-notification-kafka"></a>

This page documents settings for configuring an Kafka service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to Kafka](/administration/monitoring/publish-events-to-kafka/#minio-bucket-notifications-publish-kafka) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Multiple Kafka Targets {#multiple-kafka-targets}

You can specify multiple Kafka service endpoints by appending a unique identifier `_ID` for each set of related Kafka settings on to the top level key.

### Examples {#examples}

For example, the following commands set two distinct Kafka service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

```shell
export MINIO_NOTIFY_KAFKA_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_KAFKA_BROKERS_PRIMARY="https://kafka1.example.net:9200, https://kafka2.example.net:9200"

export MINIO_NOTIFY_KAFKA_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_KAFKA_BROKERS_SECONDARY="https://kafka1.example.net:9200, https://kafka2.example.net:9200"
```

{{% /tab %}}
{{% tab header="Configuration Setting" %}}

```shell
mc admin config set notify_kafka:primary \
   brokers="https://kafka1.example.net:9200, https://kafka2.example.net:9200"
   [ARGUMENT=VALUE ...]

mc admin config set notify_kafka:secondary \
   brokers="https://kafka1.example.net:9200, https://kafka2.example.net:9200"
   [ARGUMENT=VALUE ...]
```

Notice that for configuration settings, the unique identifier appends to `notify_kafka` only, not to each individual argument.
{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_ENABLE` {#envvar.MINIO_NOTIFY_KAFKA_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to a Kafka service endpoint.

Defaults to `off`.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka` {#mc-conf.notify_kafka}

*mc-conf*

The top-level configuration key for defining an Kafka service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an Kafka service endpoint. The [`brokers`](#mc-conf.notify_kafka.brokers) argument is *required* for each target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_kafka \
  brokers="https://kafka1.example.net:9200, https://kafka2.example.net:9200"
  [ARGUMENT="VALUE"] ... \
```

{{% /tab %}}
{{< /tabpane >}}

### Brokers {#brokers}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_BROKERS` {#envvar.MINIO_NOTIFY_KAFKA_BROKERS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka brokers` {#mc-conf.notify_kafka.brokers}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comma-separated list of Kafka broker addresses. For example:

`"kafka1.example.com:2021,kafka2.example.com:2021"`

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-27T05-56-19Z**

MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.
{{% /alert %}}

### Topic {#topic}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_TOPIC` {#envvar.MINIO_NOTIFY_KAFKA_TOPIC}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka topic` {#mc-conf.notify_kafka.topic}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the name of the Kafka topic to which MinIO publishes bucket events.

### SASL {#sasl}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_SASL` {#envvar.MINIO_NOTIFY_KAFKA_SASL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka sasl` {#mc-conf.notify_kafka.sasl}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify `on` to enable SASL authentication.

### SASL Username {#sasl-username}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_SASL_USERNAME` {#envvar.MINIO_NOTIFY_KAFKA_SASL_USERNAME}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka sasl_username` {#mc-conf.notify_kafka.sasl_username}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the username for performing SASL/PLAIN or SASL/SCRAM authentication to the Kafka broker(s).

### SASL Password {#sasl-password}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_SASL_PASSWORD` {#envvar.MINIO_NOTIFY_KAFKA_SASL_PASSWORD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka sasl_password` {#mc-conf.notify_kafka.sasl_password}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the password for performing SASL/PLAIN or SASL/SCRAM authentication to the Kafka broker(s).

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /alert %}}

### SASL Mechanism {#sasl-mechanism}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_SASL_MECHANISM` {#envvar.MINIO_NOTIFY_KAFKA_SASL_MECHANISM}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka sasl_mechanism` {#mc-conf.notify_kafka.sasl_mechanism}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the SASL mechanism to use for authenticating to the Kafka broker(s). MinIO supports the following mechanisms:

- `PLAIN` (Default)
- `SHA256`
- `SHA512`

### TLS Client Auth {#tls-client-auth}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_TLS_CLIENT_AUTH` {#envvar.MINIO_NOTIFY_KAFKA_TLS_CLIENT_AUTH}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka tls_client_auth` {#mc-conf.notify_kafka.tls_client_auth}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the client authentication type of the Kafka broker(s). The following table lists the supported values and their mappings

| Value | Authentication Type |
| --- | --- |
| 0 | `NoClientCert` |
| 1 | `RequestClientCert` |
| 2 | `RequireAnyClientCert` |
| 3 | `VerifyClientCertIfGiven` |
| 4 | `RequireAndVerifyClientCert` |

See [ClientAuthType](https://golang.org/pkg/crypto/tls/#ClientAuthType) for more information on each client auth type.

### TLS {#tls}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_TLS` {#envvar.MINIO_NOTIFY_KAFKA_TLS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka tls` {#mc-conf.notify_kafka.tls}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify `on` to enable TLS connectivity to the Kafka broker(s).

### TLS Skip Verify {#tls-skip-verify}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_TLS_SKIP_VERIFY` {#envvar.MINIO_NOTIFY_KAFKA_TLS_SKIP_VERIFY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka tls_skip_verify` {#mc-conf.notify_kafka.tls_skip_verify}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Enables or disables TLS verification of the NATS service endpoint TLS certificates.

- Specify `on` to disable TLS verification *(Default)*.
- Specify `off` to enable TLS verification.

### Client TLS Cert {#client-tls-cert}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_CLIENT_TLS_CERT` {#envvar.MINIO_NOTIFY_KAFKA_CLIENT_TLS_CERT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka client_tls_cert` {#mc-conf.notify_kafka.client_tls_cert}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the path to the client certificate to use for performing mTLS authentication to the Kafka broker(s).

### Client TLS Key {#client-tls-key}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_CLIENT_TLS_KEY` {#envvar.MINIO_NOTIFY_KAFKA_CLIENT_TLS_KEY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka client_tls_key` {#mc-conf.notify_kafka.client_tls_key}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the path to the client private key to use for performing mTLS authentication to the Kafka broker(s).

### Version {#version}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_VERSION` {#envvar.MINIO_NOTIFY_KAFKA_VERSION}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka version` {#mc-conf.notify_kafka.version}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the version of the Kafka cluster to assume when performing operations against that cluster. See the [sarama reference documentation](https://github.com/shopify/sarama/blob/v1.20.1/config.go#L327) for more information on this field’s behavior.

### Batch Size {#batch-size}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_BATCH_SIZE` {#envvar.MINIO_NOTIFY_KAFKA_BATCH_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka batch_size` {#mc-conf.notify_kafka.batch_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the integer value to use as the [batch size](https://kafka.apache.org/documentation/#producerconfigs_batch.size) for sending records to Kafka.

{{% alert color="info" %}}
**Changed: RELEASE.2023-12-02T10-51-33Z**

MinIO previously limited this value to `100`.
{{% /alert %}}

### Queue Directory {#queue-directory}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_QUEUE_DIR` {#envvar.MINIO_NOTIFY_KAFKA_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka queue_dir` {#mc-conf.notify_kafka.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the Kafka server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_KAFKA_QUEUE_LIMIT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka queue_limit` {#mc-conf.notify_kafka.queue_limit}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_COMMENT` {#envvar.MINIO_NOTIFY_KAFKA_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka comment` {#mc-conf.notify_kafka.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate with the Kafka configuration.

### Compression Codec {#compression-codec}

{{% alert color="info" %}}
**Added: MinIO**

Server RELEASE.2023-12-09T18-17-51Z
{{% /alert %}}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_PRODUCER_COMPRESSION_CODEC` {#envvar.MINIO_NOTIFY_KAFKA_PRODUCER_COMPRESSION_CODEC}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka compression_codec` {#mc-conf.notify_kafka.compression_codec}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the compression codec to use when sending records to Kafka.

Supports the following values:

- `none`
- `snappy`
- `gzip`
- `lz4`
- `zstd`

### Compression Level {#compression-level}

{{% alert color="info" %}}
**Added: MinIO**

Server RELEASE.2023-12-09T18-17-51Z
{{% /alert %}}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_KAFKA_PRODUCER_COMPRESSION_LEVEL` {#envvar.MINIO_NOTIFY_KAFKA_PRODUCER_COMPRESSION_LEVEL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_kafka compression_level` {#mc-conf.notify_kafka.compression_level}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Controls the level of compression applied based on the configured compression codec.

Specify an integer value greater than or equal to `0`. The effect of the value depends on the selected codec.
