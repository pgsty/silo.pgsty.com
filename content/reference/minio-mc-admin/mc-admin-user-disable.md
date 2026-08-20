---
title: "mc admin user disable"
url: "/reference/minio-mc-admin/mc-admin-user-disable/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-disable.rst
upstream_modified: false
---

<a id="mc-admin-user-disable"></a>
<a id="minio-mc-admin-user-disable"></a>

<a id="command-mc.admin.user.disable"></a>

## Syntax {#syntax}

The [`mc admin user disable`](#command-mc.admin.user.disable) command disables a [MinIO user](/administration/identity-access-management/minio-identity-management/#minio-internal-idp) on the target MinIO deployment.

Clients cannot use the user credentials to authenticate to the MinIO deployment. Disabling a user does *not* remove that user from the deployment. Use [`mc admin user enable`](/reference/minio-mc-admin/mc-admin-user-enable/#command-mc.admin.user.enable) to enable a disabled user on a MinIO deployment.

To manage external Identity Provider users, see [`OIDC`](/reference/minio-mc/mc-idp-openid/#command-mc.idp.openid) or [`AD/LDAP`](/reference/minio-mc/mc-idp-ldap/#command-mc.idp.ldap).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command disables user `myuser` on the `myminio` MinIO deployment:

```shell
mc admin user disable myminio myuser
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user disable   \
                            ALIAS     \
                            USERNAME
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.disable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment with the user to disable.

##### `USERNAME` {#mc.admin.user.disable.USERNAME}

*mc-cmd*

*Required*

The username of the user to disable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Disable a User {#disable-a-user}

Use [`mc admin user disable`](#command-mc.admin.user.disable) to disable a user on a MinIO deployment.

```shell
mc admin user disable ALIAS USERNAME
```

- Replace [`ALIAS`](#mc.admin.user.disable.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`USERNAME`](#mc.admin.user.disable.USERNAME) with the username of the user to disable.

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
