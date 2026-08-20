---
title: "mc admin user svcacct edit"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-edit/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-edit.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct-edit"></a>
<a id="minio-mc-admin-svcacct-edit"></a>

<a id="command-mc.admin.user.svcacct.edit"></a>

> [!WARNING]
> **Important**
>
> This command has been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey edit`](/reference/minio-mc-admin/mc-admin-accesskey-edit/#command-mc.admin.accesskey.edit) command to modify access keys for built-in MinIO IDP users.
>
> To modify access keys for AD/LDAP users, use the [`mc idp ldap accesskey edit`](/reference/minio-mc/mc-idp-ldap-accesskey-edit/#command-mc.idp.ldap.accesskey.edit) command.

## Syntax {#syntax}

The [`mc admin user svcacct edit`](#command-mc.admin.user.svcacct.edit) command modifies the configuration of an access key associated to the specified user.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command applies a new policy and secret key to the `myuserserviceaccount` access key on the `myminio` deployment:

```shell
mc admin user svcacct edit                                             \
                      --secret-key "myuserserviceaccountnewsecretkey"  \
                      --policy "/path/to/new/policy.json"              \
                      myminio myuserserviceaccount
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct edit            \
                                    [--secret-key]  \
                                    [--policy]      \
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

##### `ALIAS` {#mc.admin.user.svcacct.edit.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `SERVICEACCOUNT` {#mc.admin.user.svcacct.edit.SERVICEACCOUNT}

*mc-cmd*

*Required*

The service account to modify.

##### `--description` {#mc.admin.user.svcacct.edit.-description}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2023-05-18T16-59-00Z**

Add a description for the service account. For example, you might specify the reason the service account exists.

##### `--expiry` {#mc.admin.user.svcacct.edit.-expiry}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2023-05-30T22-41-38Z**

Set an expiration date for the service account. The date must be in the future, you may not set an expiration date that has already passed.

Allowed date and time formats:

- `2023-06-24`
- `2023-06-24T10:00`
- `2023-06-24T10:00:00`
- `2023-06-24T10:00:00Z`
- `2023-06-24T10:00:00-07:00`

##### `--name` {#mc.admin.user.svcacct.edit.-name}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2023-05-18T16-59-00Z**

Add a human-readable name for the service account.

##### `--policy` {#mc.admin.user.svcacct.edit.-policy}

*mc-cmd*

*Optional*

The path to a [policy document](/administration/identity-access-management/policy-based-access-control/#minio-policy) to attach to the new access key, with a maximum size of 2048 characters. The attached policy cannot grant access to any action or resource not explicitly allowed by the parent user’s policies.

The new policy overwrites any previously attached policy.

##### `--secret-key` {#mc.admin.user.svcacct.edit.-secret-key}

*mc-cmd*

*Optional*

The secret key to associate with the new access key. Overwrites the previous secret key. Applications using the access keys *must* update to use the new credentials to continue performing operations.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
