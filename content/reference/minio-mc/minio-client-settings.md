---
title: "Silo Client Settings"
url: "/reference/minio-mc/minio-client-settings/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/minio-client-settings.rst
upstream_modified: true
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

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
<a id="envvar.MC_HOST_&lt;ALIAS&gt;"></a>

##### `MC_HOST_<ALIAS>` {#envvar.MC_HOST_-ALIAS}

*envvar*

Replace `<ALIAS>` at the end of the environment variable with the `alias` to set the host for.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.

Use [`mc alias set`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) to configure an [alias](/reference/minio-mc/mc-alias-set/#alias).
{{< /tab >}}
{{< /tabs >}}

#### Examples {#examples}

**Static Credentials**

```shell {tab="Syntax" group="syntax-example" value="syntax"}
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>@<YOUR-S3-ENDPOINT>
```

```shell {tab="Example" value="example"}
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG@play.min.io
```

**Security Token Service (STS) Credentials**

```shell {tab="Syntax" group="syntax-example" value="syntax"}
export MC_HOST_<alias>=https://<Access Key>:<Secret Key>:<Session Token>@<YOUR-S3-ENDPOINT>
```

```shell {tab="Example" value="example"}
export MC_HOST_myalias=https://Q3AM3UQ867SPQQA43P2F:zuf+tfteSlswRu7BJ86wekitnifILbZam1KYY3TG:eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3NLZXkiOiJOVUlCT1JaWVRWMkhHMkJNUlNYUiIsImF1ZCI6IlBvRWdYUDZ1Vk80NUlzRU5SbmdEWGo1QXU1WWEiLCJhenAiOiJQb0VnWFA2dVZPNDVJc0VOUm5nRFhqNUF1NVlhIiwiZXhwIjoxNTM0ODk2NjI5LCJpYXQiOjE1MzQ4OTMwMjksImlzcyI6Imh0dHBzOi8vbG9jYWxob3N0Ojk0NDMvb2F1dGgyL3Rva2VuIiwianRpIjoiNjY2OTZjZTctN2U1Ny00ZjU5LWI0MWQtM2E1YTMzZGZiNjA4In0.eJONnVaSVHypiXKEARSMnSKgr-2mlC2Sr4fEGJitLcJF_at3LeNdTHv0_oHsv6ZZA3zueVGgFlVXMlREgr9LXA@play.min.io
```

### STS Service {#sts-service}

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-11-06T04-19-23Z

Use this setting to add an STS endpoint to use for *mc* commands.

> [!NOTE]
> **Changed: mc**
>
> RELEASE.2023-12-02T02-03-28Z

Supports adding multiple environment variables by alias.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
<a id="envvar.MC_STS_ENDPOINT_&lt;alias&gt;"></a>

##### `MC_STS_ENDPOINT_<alias>` {#envvar.MC_STS_ENDPOINT_-alias}

*envvar*

```shell
export MC_STS_ENDPOINT_myalias=https://sts.minio-operator.svc.cluster.local:4223/sts/ns-1
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Web Token Identity {#web-token-identity}

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-11-06T04-19-23Z

Use this setting to add a web token identity to use for *mc* commands.

> [!NOTE]
> **Changed: mc**
>
> RELEASE.2023-12-02T02-03-28Z

Supports adding multiple environment variables by alias.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
<a id="envvar.MC_WEB_IDENTITY_TOKEN_&lt;alias&gt;"></a>

##### `MC_WEB_IDENTITY_TOKEN_<alias>` {#envvar.MC_WEB_IDENTITY_TOKEN_-alias}

*envvar*

```shell
export MC_WEB_IDENTITY_TOKEN_FILE_myalias=/var/run/secrets/kubernetes.io/serviceaccount/token
```
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Configuration Directory {#configuration-directory}

Specify the path to the configuration folder the MinIO Client should use.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_CONFIG_DIR` {#envvar.MC_CONFIG_DIR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Progress Bar {#progress-bar}

Disable the MinIO Client progress bar.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_QUIET` {#envvar.MC_QUIET}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Pager {#pager}

> [!NOTE]
> **Added: mc**
>
> RELEASE.2024-04-29T09-56-05Z

Disable the pager functionality of the MinIO Client in the CLI. When used, output prints to raw `STDOUT` instead.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_DISABLE_PAGER` {#envvar.MC_DISABLE_PAGER}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Color Theme {#color-theme}

Disable the color theme used for MinIO Client output.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_NO_COLOR` {#envvar.MC_NO_COLOR}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### JSON {#json}

Enable formatting the output as JSON lines.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_JSON` {#envvar.MC_JSON}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Debug {#debug}

Enable the debug output.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_DEBUG` {#envvar.MC_DEBUG}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Disable SSL {#disable-ssl}

Disable SSL certificate verification.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_INSECURE` {#envvar.MC_INSECURE}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### Limit Download Bandwidth {#limit-download-bandwidth}

Limit the download bandwidth the MinIO Client uses for certain commands.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_LIMIT_DOWNLOAD` {#envvar.MC_LIMIT_DOWNLOAD}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

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

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_LIMIT_UPLOAD` {#envvar.MC_LIMIT_UPLOAD}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

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

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_ENC_KMS` {#envvar.MC_ENC_KMS}

*envvar*

Specify the key with the [`MC_ENC_KMS`](#envvar.MC_ENC_KMS) environment variable.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}

### SSE-S3 Encryption {#sse-s3-encryption}

Encrypt and decrypt options using [SSE-KMS](/operations/server-side-encryption/#minio-sse-data-encryption) with server managed keys.

{{< tabs group="environment-variable-configuration-setting" default="environment-variable" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MC_ENC_S3` {#envvar.MC_ENC_S3}

*envvar*

Specify the key to use for performing SSE-S3 encryption. The specified value must match the encryption key set in [`MINIO_KMS_KES_KEY_NAME`](/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME).
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
This setting does not have a configuration setting option.
{{< /tab >}}
{{< /tabs >}}
