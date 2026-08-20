---
title: "Publish Server or Audit Logs to an External Service"
url: "/operations/monitoring/minio-logging/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/minio-logging.rst
upstream_modified: false
---

<a id="publish-server-or-audit-logs-to-an-external-service"></a>
<a id="minio-logging"></a>

MinIO publishes all [`minio server`](/reference/minio-server/#command-minio.server) operations to the system console. Reading these logs depends on how the server process is managed. For example, if the server is managed through a `systemd` script, you can read the logs using `journalctl -u SERVICENAME.service`. Replace `SERVICENAME` with the name of the MinIO service.

MinIO also supports publishing server logs and audit logs to an HTTP webhook.

- [Server logs](#minio-logging-publish-server-logs) contain the same [`minio server`](/reference/minio-server/#command-minio.server) operations logged to the system console. Server logs support general monitoring and troubleshooting of operations.
- [Audit logs](#minio-logging-publish-audit-logs) are more granular descriptions of each operation on the MinIO deployment. Audit logging supports security standards and regulations which require detailed tracking of operations.

MinIO publishes logs as a JSON document as a `PUT` request to each configured endpoint. The endpoint server is responsible for processing each JSON document. MinIO requires explicit configuration of each webhook endpoint and does *not* publish logs to a webhook by default.

<a id="minio-logging-publish-server-logs"></a>

## Publish Server Logs to HTTP Webhook {#publish-server-logs-to-http-webhook}

You can configure a new HTTP webhook endpoint to which MinIO publishes [`minio server`](/reference/minio-server/#command-minio.server) logs using either environment variables *or* by setting runtime configuration settings.

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
MinIO supports specifying the [`minio server`](/reference/minio-server/#command-minio.server) log HTTP webhook endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/metrics-and-logging/#minio-server-envvar-logging-regular).

The following example code sets *all* environment variables related to configuring a log HTTP webhook endpoint. The minimum *required* variables are:

- [`MINIO_LOGGER_WEBHOOK_ENABLE`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_LOGGER_WEBHOOK_ENABLE)
- [`MINIO_LOGGER_WEBHOOK_ENDPOINT`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_LOGGER_WEBHOOK_ENDPOINT)

> [!NOTE]
> **Windows**
>
> ```shell
>    set MINIO_LOGGER_WEBHOOK_ENABLE_<IDENTIFIER>="on"
>    set MINIO_LOGGER_WEBHOOK_ENDPOINT_<IDENTIFIER>="https://webhook-1.example.net"
>    set MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="TOKEN"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
>    export MINIO_LOGGER_WEBHOOK_ENABLE_<IDENTIFIER>="on"
>    export MINIO_LOGGER_WEBHOOK_ENDPOINT_<IDENTIFIER>="https://webhook-1.example.net"
>    export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="TOKEN"
> ```

- Replace `<IDENTIFIER>` with a unique descriptive string for the HTTP webhook endpoint. Use the same `<IDENTIFIER>` for all environment variables related to the new log HTTP webhook.

  If the specified `<IDENTIFIER>` matches an existing log endpoint, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get logger_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured log HTTP webhook endpoints.
- Replace `https://webhook-1.example.net` with the URL of the HTTP webhook endpoint.
- Replace `TOKEN` with an authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example: for a Bearer token, prepend `Bearer`:

> [!NOTE]
> **Windows**
>
> ```shell
> set MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
> export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
> ```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

> [!NOTE]
> **Windows**
>
> ```shell
> set MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
> export MINIO_LOGGER_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
> ```

Consult the documenation for the desired service for more details.

Restart the MinIO server to apply the new configuration settings. You must specify the same environment variables and settings on *all* MinIO servers in the deployment.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
MinIO supports adding or updating log HTTP webhook endpoints on a MinIO deployment using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`logger_webhook`](/reference/minio-server/settings/metrics-and-logging/#mc-conf.logger_webhook) configuration key. You must restart the MinIO deployment to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring a log HTTP webhook endpoint. The minimum *required* setting is [`logger_webhook endpoint`](/reference/minio-server/settings/metrics-and-logging/#mc-conf.logger_webhook.endpoint):

```shell
mc admin config set ALIAS/ logger_webhook:IDENTIFIER  \
   endpoint="https://webhook-1.example.net"           \
   auth_token="TOKEN"
```

- Replace `<IDENTIFIER>` with a unique descriptive string for the HTTP webhook endpoint. Use the same `<IDENTIFIER>` for all environment variables related to the new log HTTP webhook.

  If the specified `<IDENTIFIER>` matches an existing log endpoint, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get logger_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured log HTTP webhook endpoints.
- Replace `https://webhook-1.example.net` with the URL of the HTTP webhook endpoint.
- Replace `TOKEN` with an authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

  To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

  For example: for a Bearer token, prepend `Bearer`:

  ```shell
   mc admin config set ALIAS/ logger_webhook    \
      endpoint="https://webhook-1.example.net"  \
      auth_token="Bearer 1a2b3c4f5e"
  ```

  Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

  ```shell
  mc admin config set ALIAS/ logger_webhook    \
     endpoint="https://webhook-1.example.net"  \
     auth_token="ServiceXYZ 1a2b3c4f5e"
  ```

  Consult the documenation for the desired service for more details.
{{< /tab >}}
{{< /tabs >}}

<a id="minio-logging-publish-audit-logs"></a>

## Publish Audit Logs to HTTP Webhook {#publish-audit-logs-to-http-webhook}

You can configure a new HTTP webhook endpoint to which MinIO publishes audit logs using either environment variables *or* by setting runtime configuration settings:

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
MinIO supports specifying the audit log HTTP webhook endpoint and associated configuration settings using [environment variables](/reference/minio-server/settings/metrics-and-logging/#minio-server-envvar-logging-audit).

The following example code sets *all* environment variables related to configuring a audit log HTTP webhook endpoint. The minimum *required* variables are:

- [`MINIO_AUDIT_WEBHOOK_ENABLE`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_AUDIT_WEBHOOK_ENABLE)
- [`MINIO_AUDIT_WEBHOOK_ENDPOINT`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_AUDIT_WEBHOOK_ENDPOINT)

> [!NOTE]
> **Windows**
>
> ```shell
> set MINIO_AUDIT_WEBHOOK_ENABLE_<IDENTIFIER>="on"
> set MINIO_AUDIT_WEBHOOK_ENDPOINT_<IDENTIFIER>="https://webhook-1.example.net"
> set MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="TOKEN"
> set MINIO_AUDIT_WEBHOOK_CLIENT_CERT_<IDENTIFIER>="cert.pem"
> set MINIO_AUDIT_WEBHOOK_CLIENT_KEY_<IDENTIFIER>="cert.key"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
> export MINIO_AUDIT_WEBHOOK_ENABLE_<IDENTIFIER>="on"
> export MINIO_AUDIT_WEBHOOK_ENDPOINT_<IDENTIFIER>="https://webhook-1.example.net"
> export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_<IDENTIFIER>="TOKEN"
> export MINIO_AUDIT_WEBHOOK_CLIENT_CERT_<IDENTIFIER>="cert.pem"
> export MINIO_AUDIT_WEBHOOK_CLIENT_KEY_<IDENTIFIER>="cert.key"
> ```

- Replace `<IDENTIFIER>` with a unique descriptive string for the HTTP webhook endpoint. Use the same `<IDENTIFIER>` for all environment variables related to the new audit log HTTP webhook.

  If the specified `<IDENTIFIER>` matches an existing log endpoint, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get audit_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured audit log HTTP webhook endpoints.
- Replace `https://webhook-1.example.net` with the URL of the HTTP webhook endpoint.
- Replace `TOKEN` with an authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

For example: for a Bearer token, prepend `Bearer`:

> [!NOTE]
> **Windows**
>
> ```shell
> set MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
> export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_myendpoint="Bearer 1a2b3c4f5e"
> ```

Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

> [!NOTE]
> **Windows**
>
> ```shell
> set MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
> ```

> [!NOTE]
> **Linux and macOS**
>
> ```shell
> export MINIO_AUDIT_WEBHOOK_AUTH_TOKEN_xyz="ServiceXYZ 1a2b3c4f5e"
> ```

Consult the documenation for the desired service for more details.
- Replace `cert.pem` and `cert.key` with the public and private key of the x.509 TLS certificates to present to the HTTP webhook server. Omit for endpoints which do not require clients to present TLS certificates.

Restart the MinIO server to apply the new configuration settings. You must specify the same environment variables and settings on *all* MinIO servers in the deployment.
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
MinIO supports adding or updating audit log HTTP webhook endpoints on a MinIO deployment using the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command and the [`audit_webhook`](/reference/minio-server/settings/metrics-and-logging/#mc-conf.audit_webhook) configuration key. You must restart the MinIO deployment to apply any new or updated configuration settings.

The following example code sets *all* settings related to configuring a audit log HTTP webhook endpoint. The minimum *required* setting is [`audit_webhook endpoint`](/reference/minio-server/settings/metrics-and-logging/#mc-conf.audit_webhook.endpoint):

```shell
mc admin config set ALIAS/ audit_webhook:IDENTIFIER  \
   endpoint="https://webhook-1.example.net"          \
   auth_token="TOKEN"                                \
   client_cert="cert.pem"                            \
   client_key="cert.key"
```

- Replace `<IDENTIFIER>` with a unique descriptive string for the HTTP webhook endpoint. Use the same `<IDENTIFIER>` for all environment variables related to the new audit log HTTP webhook.

  If the specified `<IDENTIFIER>` matches an existing log endpoint, the new settings *override* any existing settings for that endpoint. Use [`mc admin config get audit_webhook`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get) to review the currently configured audit log HTTP webhook endpoints.
- Replace `https://webhook-1.example.net` with the URL of the HTTP webhook endpoint.
- Replace `TOKEN` with an authentication token of the appropriate type for the endpoint. Omit for endpoints which do not require authentication.

  To allow for a variety of token types, MinIO creates the request authentication header using the value *exactly as specified*. Depending on the endpoint, you may need to include additional information.

  For example: for a Bearer token, prepend `Bearer`:

  ```shell
   mc admin config set ALIAS/ audit_webhook     \
      endpoint="https://webhook-1.example.net"  \
      auth_token="Bearer 1a2b3c4f5e"
  ```

  Modify the value according to the endpoint requirements. A custom authentication format could resemble the following:

  ```shell
  mc admin config set ALIAS/ audit_webhook     \
     endpoint="https://webhook-1.example.net"  \
     auth_token="ServiceXYZ 1a2b3c4f5e"
  ```

  Consult the documenation for the desired service for more details.
- Replace `cert.pem` and `cert.key` with the public and private key of the x.509 TLS certificates to present to the HTTP webhook server. Omit for endpoints which do not require clients to present TLS certificates.
{{< /tab >}}
{{< /tabs >}}

### Audit Log Structure {#audit-log-structure}

MinIO audit logs resemble the following JSON document:

- The `api.timeToFirstByte` and `api.timeToResponse` fields are expressed in nanoseconds.
- For [erasure coded setups](/operations/concepts/erasure-coding/#minio-erasure-coding) `tags.objectErasureMap` provides per-object details on the following:

  - The [Server Pool](/operations/concepts/#minio-intro-server-pool) on which the object operation was performed.
  - The [erasure set](/operations/concepts/erasure-coding/#minio-ec-erasure-set) on which the object operation was performed.
  - The list of drives in the erasure set which participated in the object operation.

```json
{
   "version": "1",
   "deploymentid": "8ca2b7ad-20cf-4d07-9efb-28b2f519f4a5",
   "time": "2024-02-29T19:39:25.744431903Z",
   "event": "",
   "trigger": "incoming",
   "api": {
      "name": "CompleteMultipartUpload",
      "bucket": "data",
      "object": "test-data.csv",
      "status": "OK",
      "statusCode": 200,
      "rx": 267,
      "tx": 358,
      "txHeaders": 387,
      "timeToFirstByte": "2096989ns",
      "timeToFirstByteInNS": "2096989",
      "timeToResponse": "2111986ns",
      "timeToResponseInNS": "2111986"
   },
   "remotehost": "127.0.0.1",
   "requestID": "17B86CB0ED88EBE9",
   "userAgent": "MinIO (linux; amd64) minio-go/v7.0.67 mc/RELEASE.2024-02-24T01-33-20Z",
   "requestPath": "/data/test-data.csv",
   "requestHost": "minio.example.net:9000",
   "requestQuery": {
      "uploadId": "OGNhMmI3YWQtMjBjZi00ZDA3LTllZmItMjhiMmY1MTlmNGE1LmU3MjNlNWI4LTNiYWYtNDYyNy1hNzI3LWMyNDE3NTVjMmMzNw"
   },
   "requestHeader": {
      "Accept-Encoding": "zstd,gzip",
      "Authorization": "AWS4-HMAC-SHA256 Credential=minioadmin/20240229/us-east-1/s3/aws4_request, SignedHeaders=content-type;host;x-amz-content-sha256;x-amz-date, Signature=ccb3acdc1763509a88a7e4a3d7fe431ef0ee5ca3f66ccb430d5a09326e87e893",
      "Content-Length": "267",
      "Content-Type": "application/octet-stream",
      "User-Agent": "MinIO (linux; amd64) minio-go/v7.0.67 mc/RELEASE.2024-02-24T01-33-20Z",
      "X-Amz-Content-Sha256": "d61969719ee94f43c4e87044229b7a13b54cab320131e9a77259ad0c9344f6d3",
      "X-Amz-Date": "20240229T193925Z"
   },
   "responseHeader": {
      "Accept-Ranges": "bytes",
      "Content-Length": "358",
      "Content-Type": "application/xml",
      "ETag": "1d9fdc88af5e74f5eac0a3dd750ce58e-2",
      "Server": "MinIO",
      "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
      "Vary": "Origin,Accept-Encoding",
      "X-Amz-Id-2": "dd9025bab4ad464b049177c95eb6ebf374d3b3fd1af9251148b658df7ac2e3e8",
      "X-Amz-Request-Id": "17B86CB0ED88EBE9",
      "X-Content-Type-Options": "nosniff",
      "X-Xss-Protection": "1; mode=block"
   },
   "tags": {
      "objectLocation": {
            "name": "Mousepad Template-v03final.jpg",
            "poolId": 1,
            "setId": 1,
            "disks": [
               "/mnt/drive-1",
               "/mnt/drive-2",
               "/mnt/drive-3",
               "/mnt/drive-4"
            ]
      }
   },
   "accessKey": "minioadmin"
}
```
