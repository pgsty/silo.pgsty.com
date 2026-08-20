---
title: "mc admin user svcacct enable"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-enable/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-enable.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct-enable"></a>
<a id="minio-mc-admin-svcacct-enable"></a>

<a id="command-mc.admin.user.svcacct.enable"></a>

> [!WARNING]
> **Important**
>
> This command has been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey enable`](/reference/minio-mc-admin/mc-admin-accesskey-enable/#command-mc.admin.accesskey.enable) command to enable an access key for a built-in MinIO IDP user.
>
> To enable access keys for AD/LDAP users, use the [`mc idp ldap accesskey enable`](/reference/minio-mc/mc-idp-ldap-accesskey-enable/#command-mc.idp.ldap.accesskey.enable) command.

## Syntax {#syntax}

The [`mc admin user svcacct enable`](#command-mc.admin.user.svcacct.enable) command enables an existing access key.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command enables the specified access key:

```shell
mc admin user svcacct enable myminio myuserserviceaccount
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct enable          \
                                    ALIAS           \
                                    SERVICEACCOUNT
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.svcacct.enable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `SERVICEACCOUNT` {#mc.admin.user.svcacct.enable.SERVICEACCOUNT}

*mc-cmd*

*Required*

The service account access key to enable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
