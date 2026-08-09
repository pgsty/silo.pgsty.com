---
title: "mc admin user enable"
url: "/reference/minio-mc-admin/mc-admin-user-enable/"
weight: 30
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-enable"></a>
<a id="minio-mc-admin-user-enable"></a>

<a id="command-mc.admin.user.enable"></a>

## Syntax {#syntax}

The [`mc admin user enable`](#command-mc.admin.user.enable) command enables a [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) on the target MinIO deployment.

Clients can only use enabled users to authenticate to the MinIO deployment. Users created using [`mc admin user add`](/reference/minio-mc-admin/mc-admin-user-add/#command-mc.admin.user.add) are enabled by default.

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command enables user `myuser` on the `myminio` MinIO deployment:

```shell
mc admin user enable myminio myuser
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user enable    \
                            ALIAS     \
                            USERNAME
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.enable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment with the user to enable.

##### `USERNAME` {#mc.admin.user.enable.USERNAME}

*mc-cmd*

*Required*

The username of the user to enable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Enable a User {#enable-a-user}

Use [`mc admin user enable`](#command-mc.admin.user.enable) to enable a user on a MinIO deployment.

```shell
mc admin user enable ALIAS USERNAME
```

- Replace [`ALIAS`](#mc.admin.user.enable.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](#mc.admin.user.enable.USERNAME) with the username of the user to enable.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
