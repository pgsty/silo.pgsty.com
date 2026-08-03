---
title: "Silo Client Settings"
url: "/reference/minio-mc/minio-client-settings/"
weight: 10
minio_origin: true
silo_modified: true
---

<a id="minio-client-settings"></a>
<a id="minio-server-envvar-mc"></a>

This page covers settings for the [MinIO Client](/reference/minio-mc/#minio-client).

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

## Settings {#settings}

### Host Credentials {#host-credentials}

Use this setting to add a temporary alias to use for *mc* commands. For example, for use with scripting.

The temporary alias uses the [AWS s3v4 signature](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html).

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
<a id="envvar.MC_HOST_&lt;ALIAS&gt;"></a>

##### `MC_HOST_<ALIAS>` {#envvar.MC_HOST_-ALIAS}

*envvar*

Replace `<ALIAS>` at the end of the environment variable with the `alias` to set the host for.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.

Use [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) to configure an [alias](/reference/minio-mc/mc-alias-set/#alias).
{{% /tab %}}
{{< /tabpane >}}

#### Examples {#examples}

**Static Credentials**

{{< tabpane text=true persist=header >}}
{{% tab header="Syntax" %}}
```shell
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>@<YOUR-S3-ENDPOINT>
```
{{% /tab %}}
{{% tab header="Example" %}}
```shell
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG@play.min.io
```
{{% /tab %}}
{{< /tabpane >}}

**Security Token Service (STS) Credentials**

{{< tabpane text=true persist=header >}}
{{% tab header="Syntax" %}}
```shell
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>:<Session Token>@<YOUR-S3-ENDPOINT>
```
{{% /tab %}}
{{% tab header="Example" %}}
```shell
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG:eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJOVUlCT1JaWVRWMkhHMkJNUlNYUiIsImF1ZCI6IlBvRWdYUDZ1Vk80NUlzRU5SbmdEWGo1QXU1WWEiLCJhenAiOiJQb0VnWFA2dVZPNDVJc0VOUm5nRFhqNUF1NVlhIiwiZXhwIjoxNTM0ODk2NjI5LCJpYXQiOjE1MzQ4OTMwMjksImlzcyI6Imh0dHBzOi8vbG9jYWxob3N0Ojk0NDMvb2F1dGgyL3Rva2VuIiwianRpIjoiNjY2OTZjZTctN2U1Ny00ZjU5LWI0MWQtM2E1YTMzZGZiNjA4In0.eJONnVaSVHypiXKEARSMnSKgr-2mlC2Sr4fEGJitLcJF_at3LeNdTHv0_oHsv6ZZA3zueVGgFlVXMlREgr9LXA@play.min.io
```
{{% /tab %}}
{{< /tabpane >}}

### STS Service {#sts-service}

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-11-06T04-19-23Z
{{% /alert %}}

Use this setting to add an STS endpoint to use for *mc* commands.

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Supports adding multiple environment variables by alias.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
<a id="envvar.MC_STS_ENDPOINT_&lt;alias&gt;"></a>

##### `MC_STS_ENDPOINT_<alias>` {#envvar.MC_STS_ENDPOINT_-alias}

*envvar*

```shell
export MC_STS_ENDPOINT_myalias=https://sts.minio-operator.svc.cluster.local:4223/sts/ns-1
```
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Web Token Identity {#web-token-identity}

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-11-06T04-19-23Z
{{% /alert %}}

Use this setting to add a web token identity to use for *mc* commands.

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2023-12-02T02-03-28Z
{{% /alert %}}

Supports adding multiple environment variables by alias.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
<a id="envvar.MC_WEB_IDENTITY_TOKEN_&lt;alias&gt;"></a>

##### `MC_WEB_IDENTITY_TOKEN_<alias>` {#envvar.MC_WEB_IDENTITY_TOKEN_-alias}

*envvar*

```shell
export MC_WEB_IDENTITY_TOKEN_FILE_myalias=/var/run/secrets/kubernetes.io/serviceaccount/token
```
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Configuration Directory {#configuration-directory}

Specify the path to the configuration folder the MinIO Client should use.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_CONFIG_DIR` {#envvar.MC_CONFIG_DIR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Progress Bar {#progress-bar}

Disable the MinIO Client progress bar.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_QUIET` {#envvar.MC_QUIET}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Pager {#pager}

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-04-29T09-56-05Z
{{% /alert %}}

Disable the pager functionality of the MinIO Client in the CLI. When used, output prints to raw `STDOUT` instead.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_DISABLE_PAGER` {#envvar.MC_DISABLE_PAGER}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Color Theme {#color-theme}

Disable the color theme used for MinIO Client output.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_NO_COLOR` {#envvar.MC_NO_COLOR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### JSON {#json}

Enable formatting the output as JSON lines.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_JSON` {#envvar.MC_JSON}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Debug {#debug}

Enable the debug output.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_DEBUG` {#envvar.MC_DEBUG}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Disable SSL {#disable-ssl}

Disable SSL certificate verification.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_INSECURE` {#envvar.MC_INSECURE}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### Limit Download Bandwidth {#limit-download-bandwidth}

Limit the download bandwidth the MinIO Client uses for certain commands.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_LIMIT_DOWNLOAD` {#envvar.MC_LIMIT_DOWNLOAD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

If not specified, the MinIO Client uses all available bandwidth.

Limit client-side download rates to no more than the specified rate in KiB/s, MiB/s, or GiB/s. This affects only the download from the local device running the MinIO Client. Valid units include:

- B for bytes
- K for kilobytes
- M for megabytes
- G for gigabytes
- Ki for kibibytes
- Mi for mibibytes
- Gi for gibibytes

For example, to limit download rates to no more than 1 GiB/s, use the following on a Linux system:

```shell
export MC_LIMIT_DOWNLOAD=1G
```

Refer to your operating system instructions for equivalent commands on non-Linux systems.

### Limit Upload Bandwidth {#limit-upload-bandwidth}

Limit the upload bandwidth the MinIO Client uses for certain commands.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_LIMIT_UPLOAD` {#envvar.MC_LIMIT_UPLOAD}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

If not specified, the MinIO Client uses all available bandwidth.

Limit client-side upload rates to no more than the specified rate in KiB/s, MiB/s, or GiB/s. This affects only the upload from the local device running the MinIO Client. Valid units include:

- B for bytes
- K for kilobytes
- M for megabytes
- G for gigabytes
- Ki for kibibytes
- Mi for mibibytes
- Gi for gibibytes

For example, to limit upload rates to no more than 1 GiB/s, use the following on a Linux system:

```shell
export MC_LIMIT_UPLOAD=1G
```

Refer to your operating system instructions for equivalent commands on non-Linux systems.

### SSE-KMS Encryption {#sse-kms-encryption}

Encrypt and decrypt options using [SSE-KMS](/operations/server-side-encryption/#minio-sse-data-encryption) with server managed keys.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_ENC_KMS` {#envvar.MC_ENC_KMS}

*envvar*

Specify the key with the [`MC_ENC_KMS`](#envvar.MC_ENC_KMS) environment variable.
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}

### SSE-S3 Encryption {#sse-s3-encryption}

Encrypt and decrypt options using [SSE-KMS](/operations/server-side-encryption/#minio-sse-data-encryption) with server managed keys.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" selected=true %}}
##### `MC_ENC_S3` {#envvar.MC_ENC_S3}

*envvar*

Specify the key to use for performing SSE-S3 encryption. The specified value must match the encryption key set in [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME).
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
This setting does not have a configuration setting option.
{{% /tab %}}
{{< /tabpane >}}
