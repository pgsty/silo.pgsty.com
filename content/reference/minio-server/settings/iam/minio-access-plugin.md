---
title: "Silo Access Management Plugin Settings"
url: "/reference/minio-server/settings/iam/minio-access-plugin/"
weight: 40
minio_origin: true
silo_modified: true
---

<a id="minio-access-management-plugin-settings"></a>
<a id="minio-server-envvar-external-access-management-plugin"></a>

This page documents settings for enabling external authorization management using the MinIO Access Management Plugin. See [MinIO External Access Management Plugin](/administration/identity-access-management/pluggable-authorization/#minio-external-access-management-plugin) for a tutorial on using these settings.

You can establish or modify settings by defining:

- an *environment variable* on the host system prior to starting or restarting the MinIO Server. Refer to your operating system’s documentation for how to define an environment variable.
- a *configuration setting* using [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set).

If you define both an environment variable and the similar configuration setting, MinIO uses the environment variable value.

Some settings have only an environment variable or a configuration setting, but not both.

{{% alert color="warning" %}}
**Important**

Each configuration setting controls fundamental MinIO behavior and functionality. MinIO **strongly recommends** testing configuration changes in a lower environment, such as DEV or QA, before applying to production.
{{% /alert %}}

## Examples {#examples}

When setting up the MinIO Access Management plugin, you must define at minimum all *required* settings. The examples here represent the minimum required setting.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}
```shell
MINIO_POLICY_PLUGIN_URL="https://authzservice.example.net:8080/authz"
```
{{% /tab %}}
{{% tab header="Configuration Settings" %}}
#### `policy_plugin` {#mc-conf.policy_plugin}

*mc-conf*

Use the [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) command to create or update the access management plugin configuration. The `policy_plugin url` argument is required. Specify additional optional arguments as a whitespace (” “)-delimited list.

```shell
mc admin config set policy_plugin                     \
   url="https://authzservice.example.net:8080/authz"  \
   [ARGUMENT=VALUE] ...
```
{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### URL {#url}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_POLICY_PLUGIN_URL` {#envvar.MINIO_POLICY_PLUGIN_URL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `policy_plugin url` {#mc-conf.policy_plugin.url}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The webhook endpoint for the external access management service (`https://authzservice.example.net:8080/authz`).

### Auth Token {#auth-token}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_POLICY_PLUGIN_AUTH_TOKEN` {#envvar.MINIO_POLICY_PLUGIN_AUTH_TOKEN}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `policy_plugin auth_token` {#mc-conf.policy_plugin.auth_token}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

An authentication token to present to the configured webhook endpoint.

Specify a supported HTTP [Authentication scheme](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes) as a string value, such as `"Bearer TOKEN"`. MinIO sends the token using the HTTP [Authorization](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization) header.

### HTTP2 {#http2}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_POLICY_PLUGIN_ENABLE_HTTP2` {#envvar.MINIO_POLICY_PLUGIN_ENABLE_HTTP2}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `policy_plugin enable_http2` {#mc-conf.policy_plugin.enable_http2}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Enable experimental HTTP2 support for connecting to the configure webhook service.

Defaults to off

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
##### `MINIO_POLICY_PLUGIN_COMMENT` {#envvar.MINIO_POLICY_PLUGIN_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}
##### `policy_plugin comment` {#mc-conf.policy_plugin.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate to the external access management configuration.
