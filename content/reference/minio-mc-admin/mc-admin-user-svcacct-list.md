---
title: "mc admin user svcacct ls"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-list/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-list.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct-ls"></a>
<a id="minio-mc-admin-svcacct-list"></a>

<a id="command-mc.admin.user.svcacct.list"></a>

<a id="command-mc.admin.user.svcacct.ls"></a>

> [!WARNING]
> **Important**
>
> This command has been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey ls`](/reference/minio-mc-admin/mc-admin-accesskey-list/#command-mc.admin.accesskey.ls) command to list access keys for built-in MinIO IDP users.
>
> For access keys for AD/LDAP users, use the [`mc idp ldap accesskey ls`](/reference/minio-mc/mc-idp-ldap-accesskey-ls/#command-mc.idp.ldap.accesskey.ls) command.

## Syntax {#syntax}

The [`mc admin user svcacct ls`](#command-mc.admin.user.svcacct.ls) command lists all access keys associated to the specified user.

The alias [`mc admin user svcacct list`](#command-mc.admin.user.svcacct.list) has equivalent functionality to [`mc admin user svcacct ls`](#command-mc.admin.user.svcacct.ls).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command lists all access keys associated to the user with username `admin1`:

```shell
mc admin user svcacct ls myminio admin1
```

The output resembles the following:

```shell
   Access Key        | Expiry
5XF3ZHNZK6FBDWH9JMLX | 2023-06-24 07:00:00 +0000 UTC
F4V2BBUZSWY7UG96ED70 | 2023-12-24 18:00:00 +0000 UTC
FZVSEZ8NM9JRBEQZ7B8Q | no-expiry
HOXGL8ON3RG0IKYCHCUD | no-expiry
```

> [!NOTE]
> **Added: RELEASE.2023-05-26T23-31-54Z**
>
> The list of access keys includes the expiry date, or `no-expiry` for keys that do not expire.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct ls   \
                                    ALIAS  \
                                    USER
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.svcacct.ls.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `USER` {#mc.admin.user.svcacct.ls.USER}

*mc-cmd*

*Required*

The username of the user to display access keys for.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
