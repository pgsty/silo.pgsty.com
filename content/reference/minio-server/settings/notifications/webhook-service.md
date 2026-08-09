---
title: "Webhook Service Notification Settings"
url: "/reference/minio-server/settings/notifications/webhook-service/"
weight: 100
minio_origin: true
silo_modified: false
---

<a id="webhook-service-notification-settings"></a>
<a id="minio-server-config-bucket-notification-webhook"></a>
<a id="minio-server-envvar-bucket-notification-webhook"></a>
<a id="minio-server-envvar-bucket-notification-webhook-service"></a>

This page documents settings for configuring an Webhook service as a target for [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications). See [Publish Events to Webhook](/administration/monitoring/publish-events-to-webhook/#minio-bucket-notifications-publish-webhook) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Multiple Webhook Service Targets {#multiple-webhook-service-targets}

You can specify multiple Webhook service endpoints by appending a unique identifier `_ID` for each set of related Webhook settings on to the top level key. For example, the following commands set two distinct Webhook service endpoints as `PRIMARY` and `SECONDARY` respectively:

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}

```shell
export MINIO_NOTIFY_WEBHOOK_ENABLE_PRIMARY="on"
export MINIO_NOTIFY_WEBHOOK_ENDPOINT_PRIMARY="https://webhook1.example.net"

export MINIO_NOTIFY_WEBHOOK_ENABLE_SECONDARY="on"
export MINIO_NOTIFY_WEBHOOK_ENDPOINT_SECONDARY="https://webhook1.example.net"
```

{{% /tab %}}
{{% tab header="Configuration Settings" %}}

```shell
mc admin config set notify_webhook:primary \
   endpoint="https://webhook1.example.net"
   [ARGUMENT=VALUE ...]

mc admin config set notify_webhook:secondary \
   endpoint="https://webhook2.example.net
   [ARGUMENT=VALUE ...]
```

{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Enable {#enable}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_ENABLE` {#envvar.MINIO_NOTIFY_WEBHOOK_ENABLE}

*envvar*

Specify `on` to enable publishing bucket notifications to a Webhook service endpoint.

Defaults to `off`.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook` {#mc-conf.notify_webhook}

*mc-conf*

The top-level configuration key for defining an Webhook service endpoint for use with [MinIO bucket notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications).

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update an Webhook service endpoint. The [`endpoint`](#mc-conf.notify_webhook.endpoint) argument is *required* for each target. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set notify_webhook \
  endpoint="https://webhook.example.net"
  [ARGUMENT="VALUE"] ... \
```

{{% /tab %}}
{{< /tabpane >}}

### Endpoint {#endpoint}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_ENDPOINT` {#envvar.MINIO_NOTIFY_WEBHOOK_ENDPOINT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook endpoint` {#mc-conf.notify_webhook.endpoint}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the URL for the webhook service.

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-27T05-56-19Z**

MinIO checks the health of the specified URL (if it is resolvable and reachable) prior to adding the target. MinIO no longer blocks adding new notification targets if existing targets are offline.
{{% /alert %}}

### Auth Token {#auth-token}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN` {#envvar.MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN}

*envvar*

An authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example, for a Bearer token, prepend `Bearer`:

```shell
export MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

```shell
export MINIO_NOTIFY_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
```

Consult the documentation for the desired service for more details.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook auth_token` {#mc-conf.notify_webhook.auth_token}

*mc-conf*

An authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example, for a Bearer token, prepend `Bearer`:

```shell
   mc admin config set myminio notify_webhook   \
   endpoint="https://webhook-1.example.net"  \
      auth_token="Bearer 1a2b3c4f5e"
```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

```shell
   mc admin config set myminio notify_webhook   \
      endpoint="https://webhook-1.example.net"  \
      auth_token="ServiceXYZ 1a2b3c4f5e"
```

Consult the documentation for the desired service for more details.

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

{{% /alert %}}

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /tab %}}
{{< /tabpane >}}

### Queue Directory {#queue-directory}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_QUEUE_DIR` {#envvar.MINIO_NOTIFY_WEBHOOK_QUEUE_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook queue_dir` {#mc-conf.notify_webhook.queue_dir}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the directory path to enable MinIO’s persistent event store for undelivered messages, such as `/opt/minio/events`.

MinIO stores undelivered events in the specified store while the webhook service is offline and replays the stored events when connectivity resumes.

### Queue Limit {#queue-limit}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_QUEUE_LIMIT` {#envvar.MINIO_NOTIFY_WEBHOOK_QUEUE_LIMIT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook queue_limit` {#mc-conf.notify_webhook.queue_limit}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the maximum limit for undelivered messages. Defaults to `100000`.

### Client Certificate {#client-certificate}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_CLIENT_CERT` {#envvar.MINIO_NOTIFY_WEBHOOK_CLIENT_CERT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook client_cert` {#mc-conf.notify_webhook.client_cert}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the path to the client certificate to use for performing mTLS authentication to the webhook service.

### Client Key {#client-key}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_NOTIFY_WEBHOOK_CLIENT_KEY` {#envvar.MINIO_NOTIFY_WEBHOOK_CLIENT_KEY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `notify_webhook client_key` {#mc-conf.notify_webhook.client_key}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the path to the client private key to use for performing mTLS authentication to the webhook service.
