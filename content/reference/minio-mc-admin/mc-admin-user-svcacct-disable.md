---
title: "mc admin user svcacct disable"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-disable/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-admin-user-svcacct-disable"></a>
<a id="minio-mc-admin-svcacct-disable"></a>

<a id="command-mc.admin.user.svcacct.disable"></a>

{{% alert color="warning" %}}
**Important**

This command has been replaced and will be deprecated in a future MinIO Client release.

As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey disable`](/reference/minio-mc-admin/mc-admin-accesskey-disable/#command-mc.admin.accesskey.disable) command to disable an access key for a built-in MinIO IDP user.

To disable access keys for AD/LDAP users, use the [`mc idp ldap accesskey disable`](/reference/minio-mc/mc-idp-ldap-accesskey-disable/#command-mc.idp.ldap.accesskey.disable) command.
{{% /alert %}}

## Syntax {#syntax}

The [`mc admin user svcacct disable`](#command-mc.admin.user.svcacct.disable) command disables an existing access key.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command disables the specified access key:

```shell
mc admin user svcacct disable myminio myuserserviceaccount
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct disable         \
                                    ALIAS           \
                                    SERVICEACCOUNT
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.svcacct.disable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `SERVICEACCOUNT` {#mc.admin.user.svcacct.disable.SERVICEACCOUNT}

*mc-cmd*

*Required*

The service account access key to disable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
