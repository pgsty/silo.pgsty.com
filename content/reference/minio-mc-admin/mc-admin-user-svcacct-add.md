---
title: "mc admin user svcacct add"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-add/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-add.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct-add"></a>
<a id="minio-mc-admin-svcacct-add"></a>

<a id="command-mc.admin.user.svcacct.add"></a>

> [!WARNING]
> **Important**
>
> This command has been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey create`](/reference/minio-mc-admin/mc-admin-accesskey-create/#command-mc.admin.accesskey.create) command to add access keys for built-in MinIO IDP users.
>
> To add access keys for AD/LDAP users, use the [`mc idp ldap accesskey create`](/reference/minio-mc/mc-idp-ldap-accesskey-create/#command-mc.idp.ldap.accesskey.create) command.

## Syntax {#syntax}

The [`mc admin user svcacct add`](#command-mc.admin.user.svcacct.add) command adds a new access key to an existing MinIO or AD/LDAP user.

> [!NOTE]
> **Access keys for OpenID Connect users**
>
> To generate service account access keys for [OpenID Connect users](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid), use the [MinIO Console](/administration/minio-console/#minio-console).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command creates a new access key associated to an existing MinIO user:

```shell
mc admin user svcacct add                       \
   --access-key "myuserserviceaccount"          \
   --secret-key "myuserserviceaccountpassword"  \
   --policy "/path/to/policy.json"              \
   myminio myuser
```

The command returns the access key and secret key for the new account.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct add             \
                                    [--access-key]  \
                                    [--secret-key]  \
                                    [--policy]      \
                                    [--comment]     \
                                    ALIAS           \
                                    USER
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.svcacct.add.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `USER` {#mc.admin.user.svcacct.add.USER}

*mc-cmd*

*Required*

The username of the user to which MinIO adds the new access key.

- For [MinIO-managed users](/administration/identity-access-management/minio-user-management/#minio-users), specify the access key for the user.
- For [Active Directory/LDAP users](/administration/identity-access-management/ad-ldap-access-management/#minio-external-identity-management-ad-ldap), specify the Distinguished Name of the user.
- For [OpenID Connect users](/administration/identity-access-management/oidc-access-management/#minio-external-identity-management-openid), use the [MinIO Console](/administration/minio-console/#minio-console) to generate access keys.

##### `--access-key` {#mc.admin.user.svcacct.add.-access-key}

*mc-cmd*

*Optional*

A string to use as the access key for this account. Omit to let MinIO autogenerate a random 20 character value.

Access Key names *must* be unique across all users.

##### `--comment` {#mc.admin.user.svcacct.add.-comment}

*mc-cmd*

*Optional*

> [!NOTE]
> **Changed: RELEASE.2023-05-18T16-59-00Z**
>
> Replaced by [`--description`](#mc.admin.user.svcacct.add.-description) and [`--name`](#mc.admin.user.svcacct.add.-name).
>
> Originally added in version RELEASE.2023-01-28T20-29-38Z.

This option has been removed. Use `--description` or `--name` instead.

##### `--description` {#mc.admin.user.svcacct.add.-description}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2023-05-18T16-59-00Z**

Add a description for the service account. For example, you might specify the reason the service account exists.

##### `--expiry` {#mc.admin.user.svcacct.add.-expiry}

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

##### `--name` {#mc.admin.user.svcacct.add.-name}

*mc-cmd*

*Optional*

> [!NOTE]
> **Added: RELEASE.2023-05-18T16-59-00Z**

Add a human-readable name for the service account.

##### `--policy` {#mc.admin.user.svcacct.add.-policy}

*mc-cmd*

*Optional*

The path to a [policy document](/administration/identity-access-management/policy-based-access-control/#minio-policy) to attach to the new access key, with a maximum size of 2048 characters. The attached policy cannot grant access to any action or resource not explicitly allowed by the parent user’s policies.

##### `--secret-key` {#mc.admin.user.svcacct.add.-secret-key}

*mc-cmd*

*Optional*

The secret key to associate with the new account. Omit to let MinIO autogenerate a random 40-character value.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
