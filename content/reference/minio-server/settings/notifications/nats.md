---
title: "NATS Notification Settings"
url: "/reference/minio-server/settings/notifications/nats/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/notifications/nats.rst
upstream_modified: false
---

<a id="nats-notification-settings"></a>
<a id="minio-server-config-bucket-notification-nats"></a>
<a id="minio-server-envvar-bucket-notification-nats"></a>

> [!NOTE]
> **NATS Streaming Deprecated**
>
> NATS Streaming is deprecated. Migrate to [JetStream](https://docs.nats.io/nats-concepts/jetstream) instead.
>
> The related MinIO configuration options and environment variables are deprecated.

This page documents settings for configuring an NATS service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to NATS](/administration/monitoring/publish-events-to-nats/#minio-bucket-notifications-publish-nats) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Multiple NATS Targets {#multiple-nats-targets}

You can specify multiple NATS service endpoints by appending a unique identifier `_ID` for each set of related NATS settings on to the top level key.

### Example {#example}

For example, the following commands set two distinct NATS service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
```shell
export MINIO_NOTIFY_NATS_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_NATS_ADDRESS_PRIMARY="nats-endpoint.example.net:4222"

export MINIO_NOTIFY_NATS_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_NATS_ADDRESS_SECONDARY="nats-endpoint.example.net:4222"
```

With these settings, [`MINIO_NOTIFY_NATS_ENABLE_PRIMARY`](#envvar.MINIO_NOTIFY_NATS_ENABLE) indicates the environment variable is associated to an NATS service endpoint with ID of `PRIMARY`.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
```shell
mc admin config set notify_nats:primary \
   address="nats-endpoint.example.com:4222" \
   subject="minioevents" \
   [ARGUMENT=VALUE ...]

mc admin config set notify_nats:secondary \
   address="nats-endpoint.example.com:4222" \
   subject="minioevents" \
   [ARGUMENT=VALUE ...]
```
{{< /tab >}}
{{< /tabs >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_ENABLE` {#envvar.MINIO_NOTIFY_NATS_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to an NATS service endpoint.

Defaults to `off`.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats` {#mc-conf.notify_nats}

*mc-conf*

The top-level configuration key for defining an NATS service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an NATS service endpoint. The [`address`](#mc-conf.notify_nats.address) and [`subject`](#mc-conf.notify_nats.subject) arguments are *required* for each target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_nats \
  address="nats-endpoint.example.com:4222" \
  subject="minioevents" \
  [ARGUMENT="VALUE"] ... \
```
{{< /tab >}}
{{< /tabs >}}

### Address {#address}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_ADDRESS` {#envvar.MINIO_NOTIFY_NATS_ADDRESS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats address` {#mc-conf.notify_nats.address}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the NATS service endpoint to which MinIO publishes bucket events. For example, `nats-endpoint.example.com:4222`.

> [!NOTE]
> **Changed: RELEASE.2023-05-27T05-56-19Z**
>
> MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.

### Subject {#subject}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_SUBJECT` {#envvar.MINIO_NOTIFY_NATS_SUBJECT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats subject` {#mc-conf.notify_nats.subject}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the subscription to which MinIO associates events published to the NATS endpoint.

### Username {#username}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_USERNAME` {#envvar.MINIO_NOTIFY_NATS_USERNAME}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats username` {#mc-conf.notify_nats.username}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the username for connecting to the NATS service endpoint.

### Password {#password}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_PASSWORD` {#envvar.MINIO_NOTIFY_NATS_PASSWORD}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats password` {#mc-conf.notify_nats.password}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the passport for connecting to the NATS service endpoint.

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).

### Token {#token}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_TOKEN` {#envvar.MINIO_NOTIFY_NATS_TOKEN}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats token` {#mc-conf.notify_nats.token}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the token for connecting to the NATS service endpoint.

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).

### User Credentials File {#user-credentials-file}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_USER_CREDENTIALS` {#envvar.MINIO_NOTIFY_NATS_USER_CREDENTIALS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats user_credentials` {#mc-conf.notify_nats.user_credentials}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the [user credentials file](https://docs.nats.io/using-nats/developer/connecting/creds) to use to connect to the NATS service endpoint.

### TLS {#tls}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_TLS` {#envvar.MINIO_NOTIFY_NATS_TLS}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats tls` {#mc-conf.notify_nats.tls}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable TLS connectivity to the NATS service endpoint.

### TLS Skip Verify {#tls-skip-verify}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_TLS_SKIP_VERIFY` {#envvar.MINIO_NOTIFY_NATS_TLS_SKIP_VERIFY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats tls_skip_verify` {#mc-conf.notify_nats.tls_skip_verify}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Enables or disables TLS verification of the NATS service endpoint TLS certificates.

- Specify `on` to disable TLS verification (Default).
- Specify `off` to enable TLS verification.

### Ping Interval {#ping-interval}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_PING_INTERVAL` {#envvar.MINIO_NOTIFY_NATS_PING_INTERVAL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats ping_interval` {#mc-conf.notify_nats.ping_interval}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the duration interval for client pings to the NATS server. MinIO supports the following time units:

- `s` - seconds, `"60s"`
- `m` - minutes, `"5m"`
- `h` - hours, `"1h"`
- `d` - days, `"1d"`

### Jetstream {#jetstream}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_JETSTREAM` {#envvar.MINIO_NOTIFY_NATS_JETSTREAM}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats jetstream` {#mc-conf.notify_nats.jetstream}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable JetStream support for streaming events to a NATS JetStream service endpoint.

### Streaming {#streaming}

*Deprecated*

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_STREAMING` {#envvar.MINIO_NOTIFY_NATS_STREAMING}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats streaming` {#mc-conf.notify_nats.streaming}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable asynchronous publishing of events to the NATS service endpoint.

### Streaming Async {#streaming-async}

*Deprecated*

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_STREAMING_ASYNC` {#envvar.MINIO_NOTIFY_NATS_STREAMING_ASYNC}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats streaming_async` {#mc-conf.notify_nats.streaming_async}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify `on` to enable asynchronous publishing of events to the NATS service endpoint.

### Max ACK Responses In Flight {#max-ack-responses-in-flight}

*Deprecated*

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_STREAMING_MAX_PUB_ACKS_IN_FLIGHT` {#envvar.MINIO_NOTIFY_NATS_STREAMING_MAX_PUB_ACKS_IN_FLIGHT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats streaming_max_pub_acks_in_flight` {#mc-conf.notify_nats.streaming_max_pub_acks_in_flight}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the number of messages to publish without waiting for an ACK response from the NATS service endpoint.

### Streaming Cluster ID {#streaming-cluster-id}

*Deprecated*

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_STREAMING_CLUSTER_ID` {#envvar.MINIO_NOTIFY_NATS_STREAMING_CLUSTER_ID}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats streaming_cluster_id` {#mc-conf.notify_nats.streaming_cluster_id}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the unique ID for the NATS streaming cluster.

### Cert Authority {#cert-authority}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_CERT_AUTHORITY` {#envvar.MINIO_NOTIFY_NATS_CERT_AUTHORITY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats cert_authority` {#mc-conf.notify_nats.cert_authority}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the path to the Certificate Authority chain used to sign the NATS service endpoint TLS certificates.

### Client Cert {#client-cert}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_CLIENT_CERT` {#envvar.MINIO_NOTIFY_NATS_CLIENT_CERT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats client_cert` {#mc-conf.notify_nats.client_cert}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the path to the client certificate to use for performing mTLS authentication to the NATS service endpoint.

### Client Key {#client-key}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_CLIENT_KEY` {#envvar.MINIO_NOTIFY_NATS_CLIENT_KEY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats client_key` {#mc-conf.notify_nats.client_key}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the path to the client private key to use for performing mTLS authentication to the NATS service endpoint.

### Queue Directory {#queue-directory}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_QUEUE_DIR` {#envvar.MINIO_NOTIFY_NATS_QUEUE_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats queue_dir` {#mc-conf.notify_nats.queue_dir}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the NATS server/broker is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_NATS_QUEUE_LIMIT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats queue_limit` {#mc-conf.notify_nats.queue_limit}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_NOTIFY_NATS_COMMENT` {#envvar.MINIO_NOTIFY_NATS_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `notify_nats comment` {#mc-conf.notify_nats.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate with the NATS configuration.
