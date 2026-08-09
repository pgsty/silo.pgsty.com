---
title: "OpenID Identity Management Settings"
url: "/reference/minio-server/settings/iam/openid/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="openid-identity-management-settings"></a>
<a id="minio-open-id-config-settings"></a>
<a id="minio-server-envvar-external-identity-management-openid"></a>

This page documents settings for enabling external identity management using an OpenID Connect (OIDC)-compatible provider. See [OpenID Connect Access Management](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid) for a tutorial on using these settings.

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

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variables" %}}

```shell
MINIO_IDENTITY_OPENID_CONFIG_URL="https://openid-provider.example.net/.well-known/openid-configuration"
```

{{% /tab %}}
{{% tab header="Configuration Settings" %}}

#### `identity_openid` {#mc-conf.identity_openid}

*mc-conf*

Use [`mc admin config set`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) to set or update the OpenID configuration. The [`config_url`](#mc-conf.identity_openid.config_url) argument is *required*. Specify additional optional arguments as a whitespace (`" "`)-delimited list.

```shell
mc admin config set identity_openid                                               \
  config_url="https://openid-provider.example.net/.well-known/openid-configuration" \
  [ARGUMENT="VALUE"] ...
```

{{% /tab %}}
{{< /tabpane >}}

## Settings {#settings}

### Config URL {#config-url}

*Required*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CONFIG_URL` {#envvar.MINIO_IDENTITY_OPENID_CONFIG_URL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid config_url` {#mc-conf.identity_openid.config_url}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the URL for the <abbr title="OpenID Connect">OIDC</abbr> compatible provider [discovery document](https://openid.net/specs/openid-connect-discovery-1_0.html#ProviderConfig).

The <abbr title="OpenID Connect">OIDC</abbr> Discovery URL typically resembles the following:

`https://openid-provider.example.net/.well-known/openid-configuration`

### Enabled {#enabled}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}
This setting does not have an environment variable option. Use the Configuration Setting instead.
{{% /tab %}}
{{% tab header="Configuration Setting" selected=true %}}

##### `identity_openid enabled` {#mc-conf.identity_openid.enabled}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Set to `false` to disable the OpenID configuration.

Applications cannot generate STS credentials or otherwise authenticate to MinIO using the configured provider if set to `false`.

Defaults to `true` or “enabled”.

### Client ID {#client-id}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CLIENT_ID` {#envvar.MINIO_IDENTITY_OPENID_CLIENT_ID}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid client_id` {#mc-conf.identity_openid.client_id}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the unique public identifier MinIO uses when authenticating user credentials against the <abbr title="OpenID Connect">OIDC</abbr> compatible provider.

### Client Secret {#client-secret}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CLIENT_SECRET` {#envvar.MINIO_IDENTITY_OPENID_CLIENT_SECRET}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid client_secret` {#mc-conf.identity_openid.client_secret}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the client secret MinIO uses when authenticating user credentials against the <abbr title="OpenID Connect">OIDC</abbr> compatible provider. This field may be optional depending on the provider.

{{% alert color="info" %}}
**Changed: RELEASE.2023-06-23T20-26-00Z**

MinIO redacts this value when returned as part of [`mc admin config get`](/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.get).
{{% /alert %}}

### Role Policy {#role-policy}

*Optional*

This setting is mutually exclusive with the `Claim Name` setting.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_ROLE_POLICY` {#envvar.MINIO_IDENTITY_OPENID_ROLE_POLICY}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid role_policy` {#mc-conf.identity_openid.role_policy}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comma-separated list of [policy names](/administration/identity-access-management/policy-based-access-control/#minio-policy) to use for the request’s `RoleArn` for all authentication requests for the provider. The specified policy or policies must already exist on the MinIO Server.

To use this OIDC configuration, you must specify the corresponding [RoleArn](/developers/security-token-service/AssumeRoleWithWebIdentity/#minio-assumerolewithwebidentity-query-parameters) in the STS request body.

### Claim Name {#claim-name}

*Optional*

This setting is mutually exclusive with the `Role Policy` setting.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CLAIM_NAME` {#envvar.MINIO_IDENTITY_OPENID_CLAIM_NAME}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid claim_name` {#mc-conf.identity_openid.claim_name}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the name of the [JWT Claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) MinIO uses to identify the [policies](/administration/identity-access-management/policy-based-access-control/#minio-policy) to attach to the authenticated user.

The claim can contain one or more comma-separated policy names to attach to the user. The claim must contain *at least* one policy for the user to have any permissions on the MinIO server.

Defaults to `policy`.

### Claim Prefix {#claim-prefix}

*Optional*

This setting is deprecated and has been removed as of [RELEASE.2024-07-13T01-46-15Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-07-13T01-46-15Z). Use [`MINIO_IDENTITY_OPENID_CLAIM_NAME`](#envvar.MINIO_IDENTITY_OPENID_CLAIM_NAME) instead.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CLAIM_PREFIX` {#envvar.MINIO_IDENTITY_OPENID_CLAIM_PREFIX}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid claim_prefix` {#mc-conf.identity_openid.claim_prefix}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the [JWT Claim](https://datatracker.ietf.org/doc/html/rfc7519#section-4) namespace prefix to apply to the specified claim name.

### Display Name {#display-name}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_DISPLAY_NAME` {#envvar.MINIO_IDENTITY_OPENID_DISPLAY_NAME}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid display_name` {#mc-conf.identity_openid.display_name}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the user-facing name the MinIO Console displays on the login screen.

### Scopes {#scopes}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_SCOPES` {#envvar.MINIO_IDENTITY_OPENID_SCOPES}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid scopes` {#mc-conf.identity_openid.scopes}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comma-separated list of [scopes](https://datatracker.ietf.org/doc/html/rfc6749#section-3.3). Defaults to those scopes advertised in the discovery document.

### Redirect URI {#redirect-uri}

*Optional*

This setting is deprecated and has been removed as of [RELEASE.2024-07-13T01-46-15Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-07-13T01-46-15Z). Use [`MINIO_BROWSER_REDIRECT_URL`](/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL) instead.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_REDIRECT_URI` {#envvar.MINIO_IDENTITY_OPENID_REDIRECT_URI}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid redirect_uri` {#mc-conf.identity_openid.redirect_uri}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

{{% alert color="warning" %}}
**Important**

This parameter was removed in [RELEASE.2023-02-27T18-10-45Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-02-27T18-10-45Z). Use the [`MINIO_BROWSER_REDIRECT_URL`](/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL) [environment variable](/reference/minio-server/settings/#minio-server-environment-variables) instead.
{{% /alert %}}

The MinIO Console defaults to using the hostname of the node making the authentication request. For MinIO deployments behind a load balancer or reverse proxy, specify this field to ensure the OIDC provider returns the authentication response to the correct MinIO Console URL. Include the Console hostname, port, and `/oauth_callback`:

```shell
http://minio.example.net:consoleport/oauth_callback
```

Ensure you start the MinIO Server with the [`--console-address`](/reference/minio-server/#minio.server.-console-address) option to set a static Console listen port. The default behavior with that option omitted is to select a random port number at startup.

The specified URI *must* match one of the approved redirect / callback URIs on the provider. See the OpenID [Authentication Request](https://openid.net/specs/openid-connect-core-1_0.html#AuthRequest) for more information.

### Dynamic URI Redirect {#dynamic-uri-redirect}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC` {#envvar.MINIO_IDENTITY_OPENID_REDIRECT_URI_DYNAMIC}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid redirect_uri_dynamic` {#mc-conf.identity_openid.redirect_uri_dynamic}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

The MinIO Console defaults to using the hostname of the node making the authentication request as part of the redirect URI provided to the OIDC provider. For MinIO deployments behind a load balancer using a round-robin protocol, this may result in the load balancer returning the response to a different MinIO Node than the originating client.

Specify this option as `on` to direct the MinIO Console to use the `Host` header of the originating request to construct the redirect URI passed to the OIDC provider. Defaults to `off`.

### User Info {#user-info}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_CLAIM_USERINFO` {#envvar.MINIO_IDENTITY_OPENID_CLAIM_USERINFO}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid claim_userinfo` {#mc-conf.identity_openid.claim_userinfo}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Allow MinIO to fetch claims from the [UserInfo Endpoint](https://openid.net/specs/openid-connect-core-1_0.html#UserInfo) for the authenticated user.

Valid values are `on` or `off`.

### Vendor {#vendor}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_VENDOR` {#envvar.MINIO_IDENTITY_OPENID_VENDOR}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid vendor` {#mc-conf.identity_openid.vendor}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the OIDC Vendor to enable specific supported behaviors for that vendor.

Supports the following value:

- `keycloak`

### Keycloak Realm {#keycloak-realm}

*Optional*

This setting requires that the `OpenID Vendor` setting be defined as `keycloak`.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_KEYCLOAK_REALM` {#envvar.MINIO_IDENTITY_OPENID_KEYCLOAK_REALM}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid keycloak_realm` {#mc-conf.identity_openid.keycloak_realm}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Keycloak Realm to use as part of Keycloak Admin API Operations, such as `main`.

### Keycloak Admin URL {#keycloak-admin-url}

*Optional*

This setting requires that the `OpenID Vendor` setting be defined as `keycloak`.

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_KEYCLOAK_ADMIN_URL` {#envvar.MINIO_IDENTITY_OPENID_KEYCLOAK_ADMIN_URL}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid keycloak_admin_url` {#mc-conf.identity_openid.keycloak_admin_url}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify the Keycloak Admin API URL. MinIO can use this URL if configured to periodically validate authenticated Keycloak users as active/existing. For example, `https://keycloak-endpoint:port/admin/`.

### Comment {#comment}

*Optional*

{{< tabpane text=true persist=header >}}
{{% tab header="Environment Variable" %}}

##### `MINIO_IDENTITY_OPENID_COMMENT` {#envvar.MINIO_IDENTITY_OPENID_COMMENT}

*envvar*
{{% /tab %}}
{{% tab header="Configuration Setting" %}}

##### `identity_openid comment` {#mc-conf.identity_openid.comment}

*mc-conf*
{{% /tab %}}
{{< /tabpane >}}

Specify a comment to associate with the <abbr title="OpenID Connect">OIDC</abbr> compatible provider configuration.
