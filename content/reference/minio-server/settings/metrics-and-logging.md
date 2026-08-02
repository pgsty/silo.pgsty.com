---
title: "Metrics and Logging Settings"
url: "/reference/minio-server/settings/metrics-and-logging/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="metrics-and-logging-settings"></a>
<a id="minio-server-envvar-metrics-logging"></a>

This page covers settings that control behavior related to MinIO metrics and logging. See [Metrics and alerts](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) for more information.

These settings configure publishing regular [`minio server`](/reference/minio-server/#command-minio.server) logs and audit logs to an HTTP webhook. See [Publish Server or Audit Logs to an External Service](/operations/monitoring/minio-logging/#minio-logging) for more complete documentation.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

- [Server Logs](#minio-server-envvar-logging-regular)
- [Webhook Audit Logs](#minio-server-envvar-logging-audit)
- [Kafka Audit Logs](#minio-server-envvar-logging-audit-kafka)

## Prometheus Authentication {#prometheus-authentication}

This setting controls how MinIO authenticates to Prometheus.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
#### `MINIO_PROMETHEUS_AUTH_TYPE` {#envvar.MINIO_PROMETHEUS_AUTH_TYPE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

Specifies the authentication mode for the Prometheus [scraping endpoints](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts).

- **`jwt` - *Default* MinIO requires that the scraping client specify a JWT token for authenticating requests.**

  > Use [`mc admin prometheus generate`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate) to generate the necessary JWT bearer tokens.
- `public` MinIO does not require that scraping clients authenticate their requests.

<a id="minio-server-config-logging-regular"></a>
<a id="minio-server-envvar-logging-regular"></a>

## Server Logs {#server-logs}

The following section documents settings for configuring MinIO to publish [`minio server`](/reference/minio-server/#command-minio.server) logs to an HTTP webhook endpoint. See [Publish Server Logs to HTTP Webhook](/operations/monitoring/minio-logging/#minio-logging-publish-server-logs) for more complete documentation and tutorials on using these settings.

### Defining Multiple Endpoints {#defining-multiple-endpoints}

You can specify multiple webhook endpoints as log targets by appending a unique identifier `_ID` for each set of related logging environment variables. For example, the following settings define two distinct server logs webhook endpoints:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
```shell
export MINIO_LOGGER_WEBHOOK_ENABLE_PRIMARY="on"
export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_PRIMARY="TOKEN"
export MINIO_LOGGER_WEBHOOK_ENDPOINT_PRIMARY="http://webhook-1.example.net"

export MINIO_LOGGER_WEBHOOK_ENABLE_SECONDARY="on"
export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_SECONDARY="TOKEN"
export MINIO_LOGGER_WEBHOOK_ENDPOINT_SECONDARY="http://webhook-2.example.net"
```
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
```shell
mc admin config set logger_webhook:primary \
   endpoint="http://webhook-01.example.net" [ARGUMENTS=VALUE ...]

mc admin config set logger_webhook:secondary \
   endpoint="http://webhook-02.example.net" [ARGUMENTS=VALUE ...]
```
{{% /tab %}}
{{< /tabpane >}}

### Settings {#settings}

#### Enable {#enable}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
###### `MINIO_LOGGER_WEBHOOK_ENABLE` {#envvar.MINIO_LOGGER_WEBHOOK_ENABLE}

*envvar*

Specify `"on"` to enable publishing [`minio server`](/reference/minio-server/#command-minio.server) logs to the HTTP webhook endpoint.

Requires specifying [`MINIO_LOGGER_WEBHOOK_ENDPOINT`](#envvar.MINIO_LOGGER_WEBHOOK_ENDPOINT).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook` {#mc-conf.logger_webhook}

*mc-conf*

The top level key for the configuration settings to configure logging to an HTTP webhook endpoint.
{{% /tab %}}
{{< /tabpane >}}

#### Endpoint {#endpoint}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_ENDPOINT` {#envvar.MINIO_LOGGER_WEBHOOK_ENDPOINT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook endpoint` {#mc-conf.logger_webhook.endpoint}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The HTTP endpoint of the webhook.

#### Auth Token {#auth-token}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_AUTH_TOKEN` {#envvar.MINIO_LOGGER_WEBHOOK_AUTH_TOKEN}

*envvar*

An authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example: for a Bearer token, prepend `Bearer`:

```shell
export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

```shell
export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
```

Consult the documentation for the desired service for more details.

This environment variable corresponds with the [`logger_webhook auth_token`](#mc-conf.logger_webhook.auth_token) configuration setting.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook auth_token` {#mc-conf.logger_webhook.auth_token}

*mc-conf*

An authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example: for a Bearer token, prepend `Bearer`:

```shell
   mc admin config set myminio logger_webhook   \
      endpoint="https://webhook-1.example.net"  \
      auth_token="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

```shell
   mc admin config set myminio logger_webhook   \
        endpoint="https://webhook-1.example.net"  \
      auth_token="ServiceXYZ 1a2b3c4f5e"
```

Consult the documentation for the desired service for more details.
{{% /tab %}}
{{< /tabpane >}}

#### Batch Size {#batch-size}

{{% alert color="info" %}}
**Added: MinIO**

Server RELEASE.2024-03-10T02-53-48Z
{{% /alert %}}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_BATCH_SIZE` {#envvar.MINIO_LOGGER_WEBHOOK_BATCH_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook batch_size` {#mc-conf.logger_webhook.batch_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Collect and send the specified number of events to the webhook as a batch. If not set, MinIO sends one event per request.

#### Client Certificate {#client-certificate}

*Optional*

Requires also setting the *Client Key*.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_CLIENT_CERT` {#envvar.MINIO_LOGGER_WEBHOOK_CLIENT_CERT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook client_cert` {#mc-conf.logger_webhook.client_cert}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The path to the mTLS certificate to use for authenticating to the webhook logger.

#### Client Key {#client-key}

*Optional*

Required if you define the *Client Certificate*.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_CLIENT_KEY` {#envvar.MINIO_LOGGER_WEBHOOK_CLIENT_KEY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook client_key` {#mc-conf.logger_webhook.client_key}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The path to the mTLS certificate key to use to authenticate with the webhook logger service.

#### Proxy {#proxy}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_PROXY` {#envvar.MINIO_LOGGER_WEBHOOK_PROXY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook proxy` {#mc-conf.logger_webhook.proxy}

*mc-conf*

{{% alert color="info" %}}
**Added: MinIO**

RELEASE.2023-02-22T18-23-45Z
{{% /alert %}}
{{% /tab %}}
{{< /tabpane >}}

Define a proxy to use for the webhook logger when communicating from MinIO to external webhooks.

#### Queue Directory {#queue-directory}

*Optional*

{{% alert color="info" %}}
**Added: RELEASE.2023-05-18T00-05-36Z**

{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_QUEUE_DIR` {#envvar.MINIO_LOGGER_WEBHOOK_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook queue_dir` {#mc-conf.logger_webhook.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path, such as `/opt/minio/events`, to enable MinIO’s persistent event store for undelivered messages. The MinIO process must have read, write, and list access on the specified directory.

MinIO stores undelivered events in the specified store while the webhook service is offline and replays the stored events when connectivity resumes.

#### Queue Size {#queue-size}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_LOGGER_WEBHOOK_QUEUE_SIZE` {#envvar.MINIO_LOGGER_WEBHOOK_QUEUE_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `logger_webhook queue_size` {#mc-conf.logger_webhook.queue_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

An integer value to use for the queue size for logger webhook targets.

<a id="minio-server-config-logging-audit"></a>
<a id="minio-server-envvar-logging-audit"></a>

## Webhook Audit Logs {#webhook-audit-logs}

The following section documents environment variables for configuring MinIO to publish audit logs to an HTTP webhook endpoint. See [Publish Audit Logs to HTTP Webhook](/operations/monitoring/minio-logging/#minio-logging-publish-audit-logs) for more complete documentation and tutorials on using these environment variables.

### Multiple Targets {#multiple-targets}

You can specify multiple webhook endpoints as audit log targets by appending a unique identifier `_ID` for each set of related logging settings.

For example, the following commands set two distinct audit log webhook endpoints:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
```shell
export MINIO_AUDIT_WEBHOOK_ENABLE_PRIMARY="on"
export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_PRIMARY="TOKEN"
export MINIO_AUDIT_WEBHOOK_ENDPOINT_PRIMARY="http://webhook-1.example.net"
export MINIO_AUDIT_WEBHOOK_CLIENT_CERT_SECONDARY="/tmp/cert.pem"
export MINIO_AUDIT_WEBHOOK_CLIENT_KEY_SECONDARY="/tmp/key.pem"

export MINIO_AUDIT_WEBHOOK_ENABLE_SECONDARY="on"
export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_SECONDARY="TOKEN"
export MINIO_AUDIT_WEBHOOK_ENDPOINT_SECONDARY="http://webhook-1.example.net"
export MINIO_AUDIT_WEBHOOK_CLIENT_CERT_SECONDARY="/tmp/cert.pem"
export MINIO_AUDIT_WEBHOOK_CLIENT_KEY_SECONDARY="/tmp/key.pem"
```
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `audit_webhook` {#mc-conf.audit_webhook}

*mc-conf*

The top-level configuration key for defining an HTTP webhook target for publishing [MinIO audit logs](/operations/monitoring/minio-logging/#minio-logging).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an HTTP webhook target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set audit_webhook \
   endpoint="http://webhook.example.net" [ARGUMENTS=VALUE ...]
```

You can specify multiple HTTP webhook targets by appending `[:name]` to the top-level key. For example, the following commands set two distinct HTTP webhook targets as `primary` and `secondary` respectively:

```shell
mc admin config set audit_webhook:primary \
   endpoint="http://webhook-01.example.net" [ARGUMENTS=VALUE ...]


mc admin config set audit_webhook:secondary \
   endpoint="http://webhook-02.example.net" [ARGUMENTS=VALUE ...]
```
{{% /tab %}}
{{< /tabpane >}}

### Settings {#id1}

#### Enable {#id2}

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
###### `MINIO_AUDIT_WEBHOOK_ENABLE` {#envvar.MINIO_AUDIT_WEBHOOK_ENABLE}

*envvar*

Specify `"on"` to enable publishing audit logs to the HTTP webhook endpoint.

Requires specifying [`MINIO_AUDIT_WEBHOOK_ENDPOINT`](#envvar.MINIO_AUDIT_WEBHOOK_ENDPOINT).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
Configure an audit webhook to enable it. There is *not* a separate `enable` configuration setting.
{{% /tab %}}
{{< /tabpane >}}

#### Endpoint {#id3}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_ENDPOINT` {#envvar.MINIO_AUDIT_WEBHOOK_ENDPOINT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook endpoint` {#mc-conf.audit_webhook.endpoint}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The HTTP endpoint of the webhook.

#### Auth Token {#id4}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_AUTH_TOKEN` {#envvar.MINIO_AUDIT_WEBHOOK_AUTH_TOKEN}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook auth_token` {#mc-conf.audit_webhook.auth_token}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

An authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
For example, for a Bearer token, prepend `Bearer`:

```shell
export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements.

A custom authentication format could resemble the following:

```shell
export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
```
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
```shell
mc admin config set myminio audit_webhook       \
         endpoint="http://webhook.example.net"  \
         auth_token="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements.

A command for a custom authentication format could resemble the following:

```shell
mc admin config set myminio audit_webhook       \
         endpoint="http://webhook.example.net"  \
         auth_token="ServiceXYZ 1a2b3c4f5e"
```
{{% /tab %}}
{{< /tabpane >}}

Consult the documentation for the desired service for more details.

#### Batch Size {#id5}

{{% alert color="info" %}}
**Added: MinIO**

Server RELEASE.2024-03-10T02-53-48Z
{{% /alert %}}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_BATCH_SIZE` {#envvar.MINIO_AUDIT_WEBHOOK_BATCH_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook batch_size` {#mc-conf.audit_webhook.batch_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Collect and send the specified number of events to the webhook as a batch. If not set, MinIO sends one event per request.

#### Client Certificate {#id6}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_CLIENT_CERT` {#envvar.MINIO_AUDIT_WEBHOOK_CLIENT_CERT}

*envvar*

Requires also specifying [`MINIO_AUDIT_WEBHOOK_CLIENT_KEY`](#envvar.MINIO_AUDIT_WEBHOOK_CLIENT_KEY).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook client_cert` {#mc-conf.audit_webhook.client_cert}

*mc-conf*

Requires also specifying [`client_key`](#mc-conf.audit_webhook.client_key).
{{% /tab %}}
{{< /tabpane >}}

The x.509 client certificate to present to the HTTP webhook. Omit for webhooks which do not require clients to present a known TLS certificate.

#### Client Key {#id7}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_CLIENT_KEY` {#envvar.MINIO_AUDIT_WEBHOOK_CLIENT_KEY}

*envvar*

Requires also specifying [`MINIO_AUDIT_WEBHOOK_CLIENT_CERT`](#envvar.MINIO_AUDIT_WEBHOOK_CLIENT_CERT).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook client_key` {#mc-conf.audit_webhook.client_key}

*mc-conf*

Requires specifying [`client_cert`](#mc-conf.audit_webhook.client_cert).
{{% /tab %}}
{{< /tabpane >}}

The x.509 private key to present to the HTTP webhook. Omit for webhooks which do not require clients to present a known TLS certificate.

#### Queue Directory {#id8}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_QUEUE_DIR` {#envvar.MINIO_AUDIT_WEBHOOK_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook queue_dir` {#mc-conf.audit_webhook.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="info" %}}
**Added: RELEASE.2023-05-18T00-05-36Z**

{{% /alert %}}

Specify the directory path, such as `/opt/minio/events`, to enable MinIO’s persistent event store for undelivered messages. The MinIO process must have read, write, and list access on the specified directory.

MinIO stores undelivered events in the specified store while the webhook service is offline and replays the stored events when connectivity resumes.

#### Queue Size {#id9}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_WEBHOOK_QUEUE_SIZE` {#envvar.MINIO_AUDIT_WEBHOOK_QUEUE_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_webhook queue_size` {#mc-conf.audit_webhook.queue_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

An integer value to use for the queue size for audit webhook targets. The default is `100000` events.

<a id="minio-server-config-logging-kafka-audit"></a>
<a id="minio-server-envvar-logging-audit-kafka"></a>

## Kafka Audit Logs {#kafka-audit-logs}

The following section documents environment variables for configuring MinIO to publish audit logs to a Kafka broker.

#### `audit_kafka` {#mc-conf.audit_kafka}

*mc-conf*

The top-level configuration key for defining a Kafka broker target for publishing [MinIO audit logs](/operations/monitoring/minio-logging/#minio-logging).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update a Kafka audit target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set audit_kafka \
   brokers="https://kafka-endpoint.example.net:9092" [ARGUMENTS=VALUE ...]
```

### Settings {#id10}

#### Enable {#id11}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
###### `MINIO_AUDIT_KAFKA_ENABLE` {#envvar.MINIO_AUDIT_KAFKA_ENABLE}

*envvar*

Set to `"on"` to enable the target.

Set to `"off"` to disable the target.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
There is not a configuration setting for this value. Use the environment variable to disable a configured audit webhook target.
{{% /tab %}}
{{< /tabpane >}}

#### Brokers {#brokers}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_BROKERS` {#envvar.MINIO_AUDIT_KAFKA_BROKERS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka brokers` {#mc-conf.audit_kafka.brokers}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

A comma-separated list of Kafka broker addresses:

```shell
brokers="https://kafka-1.example.net:9092,https://kafka-2.example.net:9092"
```

At least one broker must be online and reachable by the MinIO server to initialize and send audit log events. MinIO checks each specified broker in order of specification.

#### Topic {#topic}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_TOPIC` {#envvar.MINIO_AUDIT_KAFKA_TOPIC}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka topic` {#mc-conf.audit_kafka.topic}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The name of the Kafka topic to associate to MinIO audit log events.

#### TLS {#tls}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_TLS` {#envvar.MINIO_AUDIT_KAFKA_TLS}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka tls` {#mc-conf.audit_kafka.tls}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Set to `"on"` to enable TLS connectivity to the specified Kafka brokers.

Defaults to `"off"`.

#### TLS Skip Verify {#tls-skip-verify}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_TLS_SKIP_VERIFY` {#envvar.MINIO_AUDIT_KAFKA_TLS_SKIP_VERIFY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka tls_skip_verify` {#mc-conf.audit_kafka.tls_skip_verify}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Set to `"on"` to direct MinIO to skip verification of the Kafka broker TLS certificates.

You can use this option for enabling connectivity to Kafka brokers using TLS certificates signed by unknown parties, such as self-signed or corporate-internal Certificate Authorities (CA).

MinIO by default uses the system trust store *and* the contents of the MinIO [CA directory](/operations/network-encryption/#minio-tls) for verifying remote client TLS certificates.

Defaults to `"off"` for strict verification of TLS certificates.

#### SASL {#sasl}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_SASL` {#envvar.MINIO_AUDIT_KAFKA_SASL}

*envvar*

Requires specifying [`MINIO_AUDIT_KAFKA_SASL_USERNAME`](#envvar.MINIO_AUDIT_KAFKA_SASL_USERNAME) and [`MINIO_AUDIT_KAFKA_SASL_PASSWORD`](#envvar.MINIO_AUDIT_KAFKA_SASL_PASSWORD).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka sasl` {#mc-conf.audit_kafka.sasl}

*mc-conf*

Requires specifying [`sasl_username`](#mc-conf.audit_kafka.sasl_username) and [`sasl_password`](#mc-conf.audit_kafka.sasl_password).
{{% /tab %}}
{{< /tabpane >}}

Set to `"on"` to direct MinIO to use SASL to authenticate against the Kafka brokers.

#### SASL Username {#sasl-username}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_SASL_USERNAME` {#envvar.MINIO_AUDIT_KAFKA_SASL_USERNAME}

*envvar*

Requires specifying [`MINIO_AUDIT_KAFKA_SASL`](#envvar.MINIO_AUDIT_KAFKA_SASL) and [`MINIO_AUDIT_KAFKA_SASL_PASSWORD`](#envvar.MINIO_AUDIT_KAFKA_SASL_PASSWORD).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka sasl_username` {#mc-conf.audit_kafka.sasl_username}

*mc-conf*

Requires specifying [`sasl`](#mc-conf.audit_kafka.sasl) and [`sasl_password`](#mc-conf.audit_kafka.sasl_password).
{{% /tab %}}
{{< /tabpane >}}

The SASL username MinIO uses for authentication against the Kafka brokers.

#### SASL Password {#sasl-password}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_SASL_PASSWORD` {#envvar.MINIO_AUDIT_KAFKA_SASL_PASSWORD}

*envvar*

Requires specifying [`MINIO_AUDIT_KAFKA_SASL`](#envvar.MINIO_AUDIT_KAFKA_SASL) and [`MINIO_AUDIT_KAFKA_SASL_USERNAME`](#envvar.MINIO_AUDIT_KAFKA_SASL_USERNAME).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka sasl_password` {#mc-conf.audit_kafka.sasl_password}

*mc-conf*

Requires specifying [`sasl`](#mc-conf.audit_kafka.sasl) and [`sasl_username`](#mc-conf.audit_kafka.sasl_username).
{{% /tab %}}
{{< /tabpane >}}

The SASL password MinIO uses for authentication against the Kafka brokers.

#### SASL Mechanism {#sasl-mechanism}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_SASL_MECHANISM` {#envvar.MINIO_AUDIT_KAFKA_SASL_MECHANISM}

*envvar*

{{% alert color="warning" %}}
**Important**

The `PLAIN` authentication mechanism sends credentials in plain text over the network. Use [`MINIO_AUDIT_KAFKA_TLS`](#envvar.MINIO_AUDIT_KAFKA_TLS) or to enable TLS connectivity to the Kafka brokers and ensure secure transmission of SASL credentials.
{{% /alert %}}
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka sasl_mechanism` {#mc-conf.audit_kafka.sasl_mechanism}

*mc-conf*

{{% alert color="warning" %}}
**Important**

The `PLAIN` authentication mechanism sends credentials in plain text over the network. Use [`tls`](#mc-conf.audit_kafka.tls) to enable TLS connectivity to the Kafka brokers and ensure secure transmission of SASL credentials.
{{% /alert %}}
{{% /tab %}}
{{< /tabpane >}}

The SASL mechanism MinIO uses for authentication against the Kafka brokers.

Defaults to `plain`.

#### TLS Client Auth {#tls-client-auth}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_TLS_CLIENT_AUTH` {#envvar.MINIO_AUDIT_KAFKA_TLS_CLIENT_AUTH}

*envvar*

Requires specifying [`MINIO_AUDIT_KAFKA_CLIENT_TLS_CERT`](#envvar.MINIO_AUDIT_KAFKA_CLIENT_TLS_CERT) and [`MINIO_AUDIT_KAFKA_CLIENT_TLS_KEY`](#envvar.MINIO_AUDIT_KAFKA_CLIENT_TLS_KEY).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka tls_client_auth` {#mc-conf.audit_kafka.tls_client_auth}

*mc-conf*

Requires specifying [`client_tls_cert`](#mc-conf.audit_kafka.client_tls_cert) and [`client_tls_key`](#mc-conf.audit_kafka.client_tls_key).
{{% /tab %}}
{{< /tabpane >}}

Set to `"on"` to direct MinIO to use mTLS to authenticate against the Kafka brokers.

#### Client TLS Certificate {#client-tls-certificate}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_CLIENT_TLS_CERT` {#envvar.MINIO_AUDIT_KAFKA_CLIENT_TLS_CERT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka client_tls_cert` {#mc-conf.audit_kafka.client_tls_cert}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The path to the TLS client certificate to use for mTLS authentication.

#### Client TLS Key {#client-tls-key}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_CLIENT_TLS_KEY` {#envvar.MINIO_AUDIT_KAFKA_CLIENT_TLS_KEY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka client_tls_key` {#mc-conf.audit_kafka.client_tls_key}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The path to the TLS client private key to use for mTLS authentication.

#### Version {#version}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_VERSION` {#envvar.MINIO_AUDIT_KAFKA_VERSION}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka version` {#mc-conf.audit_kafka.version}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The version of the Kafka broker MinIO expects at the specified endpoints.

MinIO returns an error if the Kakfa broker version does not match those specified to this setting.

#### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_COMMENT` {#envvar.MINIO_AUDIT_KAFKA_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka comment` {#mc-conf.audit_kafka.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

A comment to associate with the configuration.

#### Queue Directory {#id12}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_QUEUE_DIR` {#envvar.MINIO_AUDIT_KAFKA_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka queue_dir` {#mc-conf.audit_kafka.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the Kafka service is offline and replays the stored events when connectivity resumes.

#### Queue Size {#id13}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
###### `MINIO_AUDIT_KAFKA_QUEUE_SIZE` {#envvar.MINIO_AUDIT_KAFKA_QUEUE_SIZE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
###### `audit_kafka queue_size` {#mc-conf.audit_kafka.queue_size}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.
