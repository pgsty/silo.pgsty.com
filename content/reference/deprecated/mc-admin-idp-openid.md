---
title: "mc admin idp openid"
url: "/reference/deprecated/mc-admin-idp-openid/"
weight: 160
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-admin-idp-openid.rst
upstream_modified: false
---

<a id="mc-admin-idp-openid"></a>
<a id="minio-mc-admin-idp-openid"></a>

<a id="command-mc.admin.idp.openid"></a>

> [!NOTE]
> **Changed: RELEASE.2023-05-26T23-31-54Z**
>
> `mc admin idp openid` and its subcommands replaced by [`mc idp openid`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid).

## Description {#description}

The [`mc admin idp openid`](#command-mc.admin.idp.openid) commands allow you to add, modify, review, list, remove, enable, and disable server configurations to 3rd party [OpenID Identity and Access Management (IAM) integrations](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid).

Define configuration settings as an alternative to using environment variables when [setting up an OpenID connection](/operations/external-iam/configure-openid-external-identity-management/#minio-external-identity-management-openid-configure).

The [`mc admin idp openid`](#command-mc.admin.idp.openid) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc admin idp openid add`](#mc.admin.idp.openid.add) | Create an OpenID IDP server configuration. |
| [`mc admin idp openid update`](#mc.admin.idp.openid.update) | Modify an existing OpenID IDP server configuration. |
| [`mc admin idp openid rm`](#mc.admin.idp.openid.rm) | Remove an OpenID IDP server configuration from a deployment. |
| [`mc admin idp openid ls`](#mc.admin.idp.openid.ls) | Outputs a list of the existing OpenID server configurations for a deployment. |
| [`mc admin idp openid info`](#mc.admin.idp.openid.info) | Displays details for a specific OpenID server configuration. |
| [`mc admin idp openid enable`](#mc.admin.idp.openid.enable) | Enables an OpenID server configuration. |
| [`mc admin idp openid disable`](#mc.admin.idp.openid.disable) | Disables an OpenID server configuration. |

## Configuration Parameters {#configuration-parameters}

The [`mc admin idp openid`](#command-mc.admin.idp.openid) subcommands support configuration parameters. The parameters define the server’s interaction with the IAM provider.

For a more detailed explanation of the configuration parameters, refer to the [config setting documentation](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings).

## Syntax {#syntax}

#### `add` {#mc.admin.idp.openid.add}

*mc-cmd*

Create a new set of configurations for an OpenID provider.

You can run the command multiple times to set up multiple OpenID providers.

When adding multiple OpenID providers, only one can be a JWT Claim-based provider. All others must be role-based providers.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example creates the configuration settings for the `myminio` deployment as defined in a new `test-config` setup for Dex integration.

```shell
 mc admin idp openid add myminio test-config                                  \
    client_id=minio-client-app                                                \
    client_secret=minio-client-app-secret                                     \
    config_url="http://localhost:5556/dex/.well-known/openid-configuration"   \
    scopes="openid,groups"                                                    \
    redirect_uri="http://127.0.0.1:10000/oauth_callback"                      \
    role_policy="consoleAdmin"
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid add        \
                           ALIAS             \
                           [CFG_NAME]        \
                           [CFG_PARAM1]      \
                           [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command creates default configuration values.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings) key-value pairs in the format of `PARAMETER="value"`.
{{< /tab >}}
{{< /tabs >}}

#### `update` {#mc.admin.idp.openid.update}

*mc-cmd*

Modify an existing set of configurations for an OpenID provider.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example changes two of the configuration settings for the `myminio` deployment as defined in the `test-config` setup for Dex integration.

```shell
mc admin idp openid update                      \
                    myminio                     \
                    test_config                 \
                    scopes="openid,groups"      \
                    role_policy="consoleAdmin"
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid update           \
                                  ALIAS            \
                                  [CFG_NAME]       \
                                  [CFG_PARAM1]     \
                                  [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command updates the default configuration.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/openid/#minio-open-id-config-settings) key-value pairs to update in the format of `PARAMETER="value"`.
{{< /tab >}}
{{< /tabs >}}

#### `rm, remove` {#mc.admin.idp.openid.rm}

*mc-cmd*

Remove an existing set of configurations for an OpenID provider.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example removes the `test-config` settings for the `myminio` deployment.

```shell
mc admin idp openid rm myminio test_config
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid rm     \
                                  ALIAS      \
                                  [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command removes the default configurations.
{{< /tab >}}
{{< /tabs >}}

#### `ls, list` {#mc.admin.idp.openid.ls}

*mc-cmd*

Outputs a list of existing configuration sets for OpenID providers.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example outputs a list of all OpenID configuration sets defined for the `myminio` deployment.

```shell
mc admin idp openid ls myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid ls ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to list OpenID integrations for.
{{< /tab >}}
{{< /tabs >}}

#### `info` {#mc.admin.idp.openid.info}

*mc-cmd*

Outputs the set of values defined for an existing set of server configurations for an OpenID provider.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example outputs the configuration settings defined for the `test_config` set of OpenID settings on the `myminio` deployment.

```shell
mc admin idp openid info myminio test_config
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid info     \
                                  ALIAS      \
                                  [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the information displays for the default server configuration.
{{< /tab >}}
{{< /tabs >}}

#### `enable` {#mc.admin.idp.openid.enable}

*mc-cmd*

Begin using an existing set of configurations for an OpenID provider.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example enables the server configurations defined as `test_config` on the `myminio` deployment.

```shell
mc admin idp openid enable       \
                    myminio      \
                    test_config
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid enable     \
                                  ALIAS      \
                                  [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command enables the default configuration values.
{{< /tab >}}
{{< /tabs >}}

#### `disable` {#mc.admin.idp.openid.disable}

*mc-cmd*

Stop using a set of configurations for an OpenID provider.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following example disables the server configurations defined as `test_config` on the `myminio` deployment.

```shell
mc admin idp openid disable      \
                    myminio      \
                    test_config
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp openid disable       \
                                  ALIAS         \
                                  [CFG_NAME]
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to configure for OpenID integration.
- Replace `CFG_NAME` with a unique string for this configuration. If not specified, the command disables the default configuration values.
{{< /tab >}}
{{< /tabs >}}

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
