---
title: "Silo Access Management Plugin Settings"
url: "/reference/minio-server/settings/iam/minio-access-plugin/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/iam/minio-access-plugin.rst
upstream_modified: true
---

<a id="minio-access-management-plugin-settings"></a>
<a id="minio-server-envvar-external-access-management-plugin"></a>

This page documents settings for enabling external authorization management using the MinIO Access Management Plugin. See [MinIO External Access Management Plugin](/administration/identity-access-management/pluggable-authorization/#minio-external-access-management-plugin) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

> [!WARNING]
> **Important**
>
> Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.

## Examples {#examples}

When setting up the MinIO Access Management plugin, you must define at minimum all *required* settings. The examples here represent the minimum required setting.

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
```shell
MINIO_POLICY_PLUGIN_URL="https://authzservice.example.net:8080/authz"
```
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
#### `policy_plugin` {#mc-conf.policy_plugin}

*mc-conf*

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to create or update the access management plugin configuration. The `policy_plugin url` argument is required. Specify additional optional arguments as a whitespace (” “)-delimited list.

```shell
mc admin config set policy_plugin                     \
   url="https://authzservice.example.net:8080/authz"  \
   [ARGUMENT=VALUE] ...
```
{{< /tab >}}
{{< /tabs >}}

## Settings {#settings}

### URL {#url}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_POLICY_PLUGIN_URL` {#envvar.MINIO_POLICY_PLUGIN_URL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `policy_plugin url` {#mc-conf.policy_plugin.url}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

The webhook endpoint for the external access management service (`https://authzservice.example.net:8080/authz`).

### Auth Token {#auth-token}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_POLICY_PLUGIN_AUTH_TOKEN` {#envvar.MINIO_POLICY_PLUGIN_AUTH_TOKEN}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `policy_plugin auth_token` {#mc-conf.policy_plugin.auth_token}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

An authentication token to present to the configured webhook endpoint.

Specify a supported HTTP [Authentication scheme](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes) as a string value, such as `"Bearer TOKEN"`. MinIO sends the token using the HTTP [Authorization](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization) header.

### HTTP2 {#http2}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_POLICY_PLUGIN_ENABLE_HTTP2` {#envvar.MINIO_POLICY_PLUGIN_ENABLE_HTTP2}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `policy_plugin enable_http2` {#mc-conf.policy_plugin.enable_http2}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Enable experimental HTTP2 support for connecting to the configure webhook service.

Defaults to off

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_POLICY_PLUGIN_COMMENT` {#envvar.MINIO_POLICY_PLUGIN_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `policy_plugin comment` {#mc-conf.policy_plugin.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate to the external access management configuration.
