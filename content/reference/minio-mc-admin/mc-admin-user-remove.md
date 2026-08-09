---
title: "mc admin user rm"
url: "/reference/minio-mc-admin/mc-admin-user-remove/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-rm"></a>
<a id="minio-mc-admin-user-remove"></a>

<a id="command-mc.admin.user.remove"></a>

<a id="command-mc.admin.user.rm"></a>

## Syntax {#syntax}

The [`mc admin user rm`](#command-mc.admin.user.rm) command removes a [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) on the target MinIO deployment.

The [`mc admin user remove`](#command-mc.admin.user.remove) command has equivalent functionality to [`mc admin user rm`](#command-mc.admin.user.rm).

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes user `myuser` on the `myminio` MinIO deployment:

```shell
mc admin user rm myminio myuser
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
Removes a user on the target MinIO deployment.

The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user remove    \
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

##### `ALIAS` {#mc.admin.user.rm.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the configured MinIO deployment with the user to remove.

##### `USERNAME` {#mc.admin.user.rm.USERNAME}

*mc-cmd*

*Required*

The username of the user to remove.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Remove a User {#remove-a-user}

Use [`mc admin user rm`](#command-mc.admin.user.rm) to remove a user from a MinIO deployment:

```shell
mc admin user rm ALIAS USERNAME
```

- Replace [`ALIAS`](#mc.admin.user.rm.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](#mc.admin.user.rm.USERNAME) with the username of the user to remove.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
