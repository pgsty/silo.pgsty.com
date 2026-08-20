---
title: "Silo Identity Management Plugin Settings"
url: "/reference/minio-server/settings/iam/minio-identity-plugin/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-server/settings/iam/minio-identity-plugin.rst
upstream_modified: true
---

<a id="minio-identity-management-plugin-settings"></a>
<a id="minio-server-envvar-external-identity-management-plugin"></a>

This page documents settings for enabling external identity management using the MinIO Identity Management Plugin. See [MinIO External Identity Management Plugin](/administration/identity-access-management/pluggable-authentication/#minio-external-identity-management-plugin) for a tutorial on using these settings.

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

When setting up the MinIO Identity Management Plugin, you must define at a minimum all of the *required* settings. The examples here represent the minimum required settings.

{{< tabs group="environment-variables-configuration-settings" >}}
{{< tab label="Environment Variables" value="environment-variables" >}}
```shell
MINIO_IDENTITY_PLUGIN_URL="https://authservice.example.net:8080/auth"
MINIO_IDENTITY_PLUGIN_ROLE_POLICY="ConsoleUser"
```
{{< /tab >}}
{{< tab label="Configuration Settings" value="configuration-settings" >}}
#### `identity_plugin` {#mc-conf.identity_plugin}

*mc-conf*

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to create or update the identity plugin configuration. The `identity_plugin url` argument is required. Specify additional optional arguments as a whitespace (” “)-delimited list.

```shell
mc admin config set identity_plugin                  \
   url="https://external-auth.example.net:8080/auth" \
   role_policy="consoleAdmin"                        \
   [ARGUMENT=VALUE] ...
```
{{< /tab >}}
{{< /tabs >}}

## Settings {#settings}

### URL {#url}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_IDENTITY_PLUGIN_URL` {#envvar.MINIO_IDENTITY_PLUGIN_URL}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin url` {#mc-conf.identity_plugin.url}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

The webhook endpoint for the external identity management service (`https://authservice.example.net:8080/auth`).

### Role Policy {#role-policy}

*Required*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_IDENTITY_PLUGIN_ROLE_POLICY` {#envvar.MINIO_IDENTITY_PLUGIN_ROLE_POLICY}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin role_policy` {#mc-conf.identity_plugin.role_policy}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comma-separated list of MinIO [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to assign to authenticated users.

### Enable {#enable}

*Optional*

{{< tabs group="environment-variable-configuration-setting" default="configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
This setting does not have an environment variable option.
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin enabled` {#mc-conf.identity_plugin.enabled}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Set to `false` to disable the identity provider configuration.

Applications cannot generate STS credentials or otherwise authenticate to MinIO using the configured provider if set to `false`.

Defaults to `true` or “enabled”.

### Token {#token}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_IDENTITY_PLUGIN_TOKEN` {#envvar.MINIO_IDENTITY_PLUGIN_TOKEN}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin token` {#mc-conf.identity_plugin.token}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

An authentication token to present to the configured webhook endpoint.

Specify a supported HTTP [Authentication scheme](https://developer.mozilla.org/en-US/docs/Web/HTTP/Authentication#authentication_schemes) as a string value, such as `"Bearer TOKEN"`. MinIO sends the token using the HTTP [Authorization](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Authorization) header.

### Role ID {#role-id}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_IDENTITY_PLUGIN_ROLE_ID` {#envvar.MINIO_IDENTITY_PLUGIN_ROLE_ID}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin role_id` {#mc-conf.identity_plugin.role_id}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a unique ID MinIO uses to generate an ARN for this identity manager. MinIO automatically adds an `idmp-` prefix to the specified ID when generating the ARN.

If omitted, MinIO automatically generates the ID and prints the full ARN to the server log.

### Comment {#comment}

*Optional*

{{< tabs group="environment-variable-configuration-setting" >}}
{{< tab label="Environment Variable" value="environment-variable" >}}
##### `MINIO_IDENTITY_PLUGIN_COMMENT` {#envvar.MINIO_IDENTITY_PLUGIN_COMMENT}

*envvar*
{{< /tab >}}
{{< tab label="Configuration Setting" value="configuration-setting" >}}
##### `identity_plugin comment` {#mc-conf.identity_plugin.comment}

*mc-conf*
{{< /tab >}}
{{< /tabs >}}

Specify a comment to associate to the identity configuration.
