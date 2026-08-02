---
title: "mc idp openid"
url: "/reference/minio-mc/mc-idp-openid/"
weight: 180
minio_origin: true
silo_modified: false
---

<a id="mc-idp-openid"></a>
<a id="minio-mc-idp-openid"></a>

<a id="command-mc.idp.openid"></a>

{{% alert color="info" %}}
**Added: RELEASE.2023-05-26T23-31-54Z**

[`mc idp openid`](#command-mc.idp.openid) and its subcommands replace `mc admin idp openid`.
{{% /alert %}}

## Description {#description}

The [`mc idp openid`](#command-mc.idp.openid) commands allow you to manage configurations to 3rd party [OpenID Identity and Access Management (IAM) integrations](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).

Define configuration settings as an alternative to using environment variables when [setting up an OpenID connection](/operations/external-iam/configure-openid-external-identity-management/#minio-external-identity-management-openid-configure). The [`mc idp openid`](#command-mc.idp.openid) commands are only supported against MinIO deployments.

{{% alert color="info" %}}
**Note**

MinIO [OpenID environment variables](/reference/minio-server/settings/iam/openid/#minio-server-envvar-external-identity-management-openid) override their corresponding configuration settings as modified or set by this command.
{{% /alert %}}

The [`mc idp openid`](#command-mc.idp.openid) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc idp openid add`](#mc.idp.openid.add) | Create an OpenID IDP server configuration. |
| [`mc idp openid update`](#mc.idp.openid.update) | Modify an existing OpenID IDP server configuration. |
| [`mc idp openid rm`](#mc.idp.openid.rm) | Remove an OpenID IDP server configuration from a deployment. |
| [`mc idp openid ls`](#mc.idp.openid.ls) | Outputs a list of the existing OpenID server configurations for a deployment. |
| [`mc idp openid info`](#mc.idp.openid.info) | Displays details for a specific OpenID server configuration. |
| [`mc idp openid enable`](#mc.idp.openid.enable) | Enables an OpenID server configuration. |
| [`mc idp openid disable`](#mc.idp.openid.disable) | Disables an OpenID server configuration. |

## Configuration Parameters {#configuration-parameters}

The [`mc idp openid`](#command-mc.idp.openid) subcommands support configuration parameters. The parameters define the server’s interaction with the IAM provider.

For a more detailed explanation of the configuration parameters, refer to the [config setting documentation](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings).

## Syntax {#syntax}

#### `add` {#mc.idp.openid.add}

*mc-cmd*

Create a new set of configurations for an OpenID provider.

You can run the command multiple times to set up multiple OpenID providers.

When adding multiple OpenID providers, only one can be a JWT Claim-based provider. All others must be role-based providers.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example creates the configuration settings for the `myminio` deployment as defined in a new `test-config` setup for Dex integration.

```shell
 mc idp openid add myminio test-config                                        \
    client_id=minio-client-app                                                \
    client_secret=minio-client-app-secret                                     \
    config_url="http://localhost:5556/dex/.well-known/openid-configuration"   \
    scopes="openid,groups"                                                    \
    redirect_uri="http://127.0.0.1:10000/oauth_callback"                      \
    role_policy="consoleAdmin"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid add               \
                            ALIAS             \
                            [CFG_NAME]        \
                            [CFG_PARAM1]      \
                            [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command creates default configuration values.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings) key-value pairs in the format of `PARAMETER="value"`.
{{% /tab %}}
{{< /tabpane >}}

#### `update` {#mc.idp.openid.update}

*mc-cmd*

Modify an existing set of configurations for an OpenID provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example changes two of the configuration settings for the `myminio` deployment as defined in the `test-config` setup for Dex integration.

```shell
mc idp openid update                      \
              myminio                     \
              test_config                 \
              scopes="openid,groups"      \
              role_policy="consoleAdmin"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid update           \
                            ALIAS            \
                            [CFG_NAME]       \
                            [CFG_PARAM1]     \
                            [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command updates the default configuration.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings) key-value pairs to update in the format of `PARAMETER="value"`.
{{% /tab %}}
{{< /tabpane >}}

#### `rm, remove` {#mc.idp.openid.rm}

*mc-cmd*

Remove an existing set of configurations for an OpenID provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example removes the `test-config` settings for the `myminio` deployment.

```shell
mc idp openid rm myminio test_config
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid rm          \
                            ALIAS       \
                            [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command removes the default configurations.
{{% /tab %}}
{{< /tabpane >}}

#### `ls, list` {#mc.idp.openid.ls}

*mc-cmd*

Outputs a list of existing configuration sets for OpenID providers.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example outputs a list of all OpenID configuration sets defined for the `myminio` deployment.

```shell
mc idp openid ls myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid ls ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to list OpenID integrations for.
{{% /tab %}}
{{< /tabpane >}}

#### `info` {#mc.idp.openid.info}

*mc-cmd*

Outputs the set of values defined for an existing set of server configurations for an OpenID provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example outputs the configuration settings defined for the `test_config` set of OpenID settings on the `myminio` deployment.

```shell
mc idp openid info myminio test_config
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid info        \
                            ALIAS       \
                            [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the information displays for the default server configuration.
{{% /tab %}}
{{< /tabpane >}}

#### `enable` {#mc.idp.openid.enable}

*mc-cmd*

Begin using an existing set of configurations for an OpenID provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example enables the server configurations defined as `test_config` on the `myminio` deployment.

```shell
mc idp openid enable       \
              myminio      \
              test_config
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid enable     \
                            ALIAS      \
                            [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command enables the default configuration values.
{{% /tab %}}
{{< /tabpane >}}

#### `disable` {#mc.idp.openid.disable}

*mc-cmd*

Stop using a set of configurations for an OpenID provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example disables the server configurations defined as `test_config` on the `myminio` deployment.

```shell
mc idp openid disable      \
              myminio      \
              test_config
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] idp openid disable       \
                            ALIAS         \
                            [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command disables the default configuration values.
{{% /tab %}}
{{< /tabpane >}}

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
