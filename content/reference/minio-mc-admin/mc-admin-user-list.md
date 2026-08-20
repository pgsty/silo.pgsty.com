---
title: "mc admin user ls"
url: "/reference/minio-mc-admin/mc-admin-user-list/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-list.rst
upstream_modified: false
---

<a id="mc-admin-user-ls"></a>
<a id="minio-mc-admin-user-list"></a>

<a id="command-mc.admin.user.list"></a>

<a id="command-mc.admin.user.ls"></a>

## Syntax {#syntax}

The [`mc admin user ls`](#command-mc.admin.user.ls) command lists all [MinIO users](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) on the target MinIO deployment.

The [`mc admin user list`](#command-mc.admin.user.list) command has equivalent functionality to [`mc admin user ls`](#command-mc.admin.user.ls).

[`mc admin user ls`](#command-mc.admin.user.ls) does *not* return the access key or secret key associated to a user. Use [`mc admin user info`](/reference/minio-mc-admin/mc-admin-user-info/#command-mc.admin.user.info) to retrieve detailed user information, including the user access key.

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command lists all users on the `myminio` MinIO deployment:

```shell
mc admin user ls myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user list   \
                            ALIAS
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.ls.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command lists users.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### List Available Users {#list-available-users}

Use [`mc admin user ls`](#command-mc.admin.user.ls) to list all users on a MinIO deployment:

```shell
mc admin user ls ALIAS
```

- Replace [`ALIAS`](#mc.admin.user.ls.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
enabled    devadmin              readwrite
enabled    devtest               readonly
enabled    newuser
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
