---
title: "Object Lambda function settings"
url: "/reference/minio-server/settings/object-lambda/"
weight: 110
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/object-lambda.rst
upstream_modified: false
---

<a id="object-lambda-function-settings"></a>
<a id="minio-server-envvar-object-lambda-webhook"></a>

This page describes the settings available to configure MinIO to publish data to an HTTP webhook endpoint and trigger an Object Lambda function. See [Transforms with Object Lambda](/developers/transforms-with-object-lambda/#developers-object-lambda) for more complete documentation and tutorials on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Enable {#enable}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_LAMBDA_WEBHOOK_ENABLE` {#envvar.MINIO_LAMBDA_WEBHOOK_ENABLE}

*envvar*

Specify `"on"` to enable the Object Lambda webhook endpoint for a handler function.

Requires specifying [`MINIO_LAMBDA_WEBHOOK_ENDPOINT`](#envvar.MINIO_LAMBDA_WEBHOOK_ENDPOINT).

You can specify multiple webhooks as Lambda targets by appending a unique identifier for each Object Lambda function. For example, the following command enables two distinct Object Lambda webhook endpoints:

```shell
export MINIO_LAMBDA_WEBHOOK_ENABLE_myfunction="on"
export MINIO_LAMBDA_WEBHOOK_ENABLE_yourfunction="on"
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `lambda_webhook enable` {#mc-conf.lambda_webhook.enable}

*mc-conf*

*Optional*

Specify `"on"` to enable the Object Lambda webhook endpoint for a handler function. Requires specifying [`endpoint`](#mc-conf.lambda_webhook.endpoint).

Example:

```shell
mc admin config set myminio lambda_webhook:myfunction endpoint="https://example.com/" enable=on
```
{{< /tab >}}
{{< /tabs >}}

## Endpoint {#endpoint}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_LAMBDA_WEBHOOK_ENDPOINT` {#envvar.MINIO_LAMBDA_WEBHOOK_ENDPOINT}

*envvar*

The HTTP endpoint of the lambda webhook for the handler function.

You can specify multiple webhook endpoints as Lambda targets by appending a unique identifier for each Object Lambda function. For example, the following command sets two distinct Object Lambda webhook endpoints:

```shell
export MINIO_LAMBDA_WEBHOOK_ENDPOINT_myfunction="http://webhook-1.example.com"
export MINIO_LAMBDA_WEBHOOK_ENDPOINT_yourfunction="http://webhook-2.example.com"
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `lambda_webhook endpoint` {#mc-conf.lambda_webhook.endpoint}

*mc-conf*

*Optional*

The HTTP endpoint of the lambda webhook for the handler function.
{{< /tab >}}
{{< /tabs >}}

## Auth token {#auth-token}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN` {#envvar.MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN}

*envvar*

Specify the opaque string or JWT authorization token to use for authenticating to the lambda webhook service.

You can specify the token for multiple Lambda targets by appending a unique identifier for each Object Lambda function. For example, the following command configures a token for two distinct Object Lambda webhook endpoints:

```shell
export MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN_myfunction="1a2b3c4d5e"
export MINIO_LAMBDA_WEBHOOK_AUTH_TOKEN_yourfunction="1a2b3c4d5e"
```

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `lambda_webhook auth_token` {#mc-conf.lambda_webhook.auth_token}

*mc-conf*

*Optional*

Specify the opaque string or JWT authorization token to use for authenticating to the lambda webhook service.

> [!NOTE]
> **Changed: RELEASE.2023-06-23T20-26-00Z**
>
> MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{< /tab >}}
{{< /tabs >}}

## Client cert {#client-cert}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_LAMBDA_WEBHOOK_CLIENT_CERT` {#envvar.MINIO_LAMBDA_WEBHOOK_CLIENT_CERT}

*envvar*

Specify the path to the client certificate to use for performing mTLS authentication to the lambda webhook service.

You can specify the client cert for multiple Lambda targets by appending a unique identifier for each Object Lambda function. For example, the following command configures a cert for two distinct Object Lambda webhook endpoints:

```shell
export MINIO_LAMBDA_WEBHOOK_CLIENT_CERT_myfunction="/path/to/cert1"
export MINIO_LAMBDA_WEBHOOK_CLIENT_CERT_yourfunction="/path/to/cert2"
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `lambda_webhook client_cert` {#mc-conf.lambda_webhook.client_cert}

*mc-conf*

*Optional*

Specify the path to the client certificate to use for performing mTLS authentication to the lambda webhook service.
{{< /tab >}}
{{< /tabs >}}

## Client key {#client-key}

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
#### `MINIO_LAMBDA_WEBHOOK_CLIENT_KEY` {#envvar.MINIO_LAMBDA_WEBHOOK_CLIENT_KEY}

*envvar*

Specify the path to the private key to use for performing mTLS authentication to the lambda webhook service.

You can specify the client key for multiple Lambda targets by appending a unique identifier for each Object Lambda function. For example, the following command configures a key for two distinct Object Lambda webhook endpoints:

```shell
export MINIO_LAMBDA_WEBHOOK_CLIENT_KEY_myfunction="/path/to/key1"
export MINIO_LAMBDA_WEBHOOK_CLIENT_KEY_yourfunction="/path/to/key2"
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
#### `lambda_webhook client_key` {#mc-conf.lambda_webhook.client_key}

*mc-conf*

*Optional*

Specify the path to the private key to use for performing mTLS authentication to the lambda webhook service.
{{< /tab >}}
{{< /tabs >}}
