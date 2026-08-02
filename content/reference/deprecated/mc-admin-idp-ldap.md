---
title: "mc admin idp ldap"
url: "/reference/deprecated/mc-admin-idp-ldap/"
weight: 140
minio_origin: true
silo_modified: false
---

<a id="mc-admin-idp-ldap"></a>
<a id="minio-mc-admin-idp-ldap"></a>

<a id="command-mc.admin.idp.ldap"></a>

{{% alert color="info" %}}
**Changed: RELEASE.2023-05-26T23-31-54Z**

`mc admin idp ldap` and its subcommands replaced by [`mc idp ldap`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).
{{% /alert %}}

## Description {#description}

The [`mc admin idp ldap`](#command-mc.admin.idp.ldap) commands allow you to add, modify, review, list, remove, enable, and disable server configurations to 3rd party [Active Directory or LDAP Identity and Access Management (IAM) integrations](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap).

Define configuration settings as an alternative to using environment variables when [setting up an AD/LDAP connection](/operations/external-iam/configure-ad-ldap-external-identity-management/#minio-authenticate-using-ad-ldap-generic).

{{% alert color="info" %}}
**Note**

Configuration settings do **not** override settings configured as environment variables.
{{% /alert %}}

The [`mc admin idp ldap`](#command-mc.admin.idp.ldap) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc admin idp ldap add`](#mc.admin.idp.ldap.add) | Create an AD/LDAP IDP server configuration. |
| [`mc admin idp ldap update`](#mc.admin.idp.ldap.update) | Modify an existing AD/LDAP IDP server configuration. |
| [`mc admin idp ldap ls`](#mc.admin.idp.ldap.ls) | Lists AD/LDAP server configurations. |
| [`mc admin idp ldap rm`](#mc.admin.idp.ldap.rm) | Remove an AD/LDAP IDP server configuration from a deployment. |
| [`mc admin idp ldap info`](#mc.admin.idp.ldap.info) | Displays details for a specific AD/LDAP server configuration. |
| [`mc admin idp ldap enable`](#mc.admin.idp.ldap.enable) | Enables an AD/LDAP server configuration. |
| [`mc admin idp ldap disable`](#mc.admin.idp.ldap.disable) | Disables an AD/LDAP server configuration. |
| [`mc admin idp ldap policy entities`](/reference/deprecated/mc-admin-idp-ldap-policy/#mc.admin.idp.ldap.policy.entities) | List policy association entities |

## Configuration Parameters {#configuration-parameters}

The [`mc admin idp ldap`](#command-mc.admin.idp.ldap) subcommands support configuration parameters. The parameters define the server’s interaction with the Active Directory or LDAP IAM provider.

For a more detailed explanation of the configuration parameters, refer to the [config setting documentation](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings).

## Syntax {#syntax}

#### `add` {#mc.admin.idp.ldap.add}

*mc-cmd*

Create a new configuration for an AD/LDAP provider. MinIO supports no more than *one* (1) AD/LDAP provider per deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example sets the AD/LDAP configuration settings for the `myminio` deployment.

```shell
 mc admin idp ldap add                                               \
      myminio                                                        \
      server_addr=myldapserver:636                                   \
      lookup_bind_dn=cn=admin,dc=min,dc=io                           \
      lookup_bind_password=somesecret                                \
      user_dn_search_base_dn=dc=min,dc=io                            \
      user_dn_search_filter="(uid=%s)"                               \
      group_search_base_dn=ou=swengg,dc=min,dc=io                    \
      group_search_filter="(&(objectclass=groupofnames)(member=%d))"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap add          \
                           ALIAS             \
                           [CFG_PARAM1]      \
                           [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to create for AD/LDAP integration.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) key-value pairs in the format of `PARAMETER="value"`.
{{% /tab %}}
{{< /tabpane >}}

#### `update` {#mc.admin.idp.ldap.update}

*mc-cmd*

Modify an existing set of configurations for an AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example changes two of the AD/LDAP configuration settings for the `myminio` deployment.

```shell
mc admin idp ldap update                                \
                  myminio                               \
                  lookup_bind_dn=cn=admin,dc=min,dc=io  \
                  lookup_bind_password=somesecret
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap update           \
                                ALIAS            \
                                [CFG_PARAM1]     \
                                [CFG_PARAM2]...
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to update for AD/LDAP integration.
- Replace the `[CFG_PARAM#]` with each of the [configuration setting](/reference/minio-server/settings/iam/ldap/#minio-ldap-config-settings) key-value pairs to update in the format of `PARAMETER="value"`.
{{% /tab %}}
{{< /tabpane >}}

#### `ls, list` {#mc.admin.idp.ldap.ls}

*mc-cmd*

Lists the existing set of configurations for an AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example lists the AD/LDAP configuration settings for the `myminio` deployment.

```shell
mc admin idp ldap ls myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap ls ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to list the AD/LDAP integration.
{{% /tab %}}
{{< /tabpane >}}

#### `rm, remove` {#mc.admin.idp.ldap.rm}

*mc-cmd*

Remove the existing configuration for an AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example removes the AD/LDAP provider settings for the `myminio` deployment.

```shell
mc admin idp ldap rm myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap rm     \
                                ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to remove the AD/LDAP integration.
{{% /tab %}}
{{< /tabpane >}}

#### `info` {#mc.admin.idp.ldap.info}

*mc-cmd*

Outputs the current configuration for an AD/LDAP provider on a specified MinIO deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example outputs the AD/LDAP configuration settings on the `myminio` deployment.

```shell
mc admin idp ldap info myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap info     \
                                ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to retrieve info on the AD/LDAP integration.
{{% /tab %}}
{{< /tabpane >}}

#### `enable` {#mc.admin.idp.ldap.enable}

*mc-cmd*

Enables the currently configured AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example enables the AD/LDAP configuration on the `myminio` deployment.

```shell
mc admin idp ldap enable       \
                  myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap enable     \
                                ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to enable the AD/LDAP integration.
{{% /tab %}}
{{< /tabpane >}}

#### `disable` {#mc.admin.idp.ldap.disable}

*mc-cmd*

Disables the currently configured AD/LDAP provider.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following example disables the AD/LDAP configurations on the `myminio` deployment.

```shell
mc admin idp ldap disable      \
                  myminio
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin idp ldap disable       \
                                ALIAS
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to disable the AD/LDAP integration.
{{% /tab %}}
{{< /tabpane >}}

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
