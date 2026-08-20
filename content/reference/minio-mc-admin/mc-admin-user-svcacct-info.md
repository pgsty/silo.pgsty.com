---
title: "mc admin user svcacct info"
url: "/reference/minio-mc-admin/mc-admin-user-svcacct-info/"
weight: 50
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-user-svcacct-info.rst
upstream_modified: false
---

<a id="mc-admin-user-svcacct-info"></a>
<a id="minio-mc-admin-svcacct-info"></a>

<a id="command-mc.admin.user.svcacct.info"></a>

> [!WARNING]
> **Important**
>
> This command has been replaced and will be deprecated in a future MinIO Client release.
>
> As of MinIO Client RELEASE.2024-10-08T09-37-26Z, use the [`mc admin accesskey info`](/reference/minio-mc-admin/mc-admin-accesskey-info/#command-mc.admin.accesskey.info) command to display information about access keys for built-in MinIO IDP users.
>
> For access keys for AD/LDAP users, use the [`mc idp ldap accesskey info`](/reference/minio-mc/mc-idp-ldap-accesskey-info/#command-mc.idp.ldap.accesskey.info) command.

## Syntax {#syntax}

The [`mc admin user svcacct info`](#command-mc.admin.user.svcacct.info) command returns a description of the specified [access key](/administration/identity-access-management/minio-user-management/#minio-id-access-keys).

“Access Keys” have equivalent functionality to and replace the concept of “Service Accounts” in MinIO.

The description output includes the following details, as available:

- Access Key
- Parent user of the specified access key
- Access key status (`on` or `off`)
- Policy or policies
- Comment
- Expiration

Use [`--policy`](#mc.admin.user.svcacct.info.-policy) to view the attached policies.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command returns information on the specified access key:

```shell
mc admin user svcacct info myminio myuseraccesskey
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin user svcacct info           \
                                    [--policy]     \
                                    ALIAS          \
                                    ACCESSKEY
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.user.svcacct.info.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `ACCESSKEY` {#mc.admin.user.svcacct.info.ACCESSKEY}

*mc-cmd*

*Required*

The service account access key to display.

##### `--policy` {#mc.admin.user.svcacct.info.-policy}

*mc-cmd*

*Optional*

Displays policies attached to the specified service account.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display Service Account Details {#display-service-account-details}

Use [`mc admin user svcacct info`](#command-mc.admin.user.svcacct.info) to display details of a service account on a MinIO deployment:

```shell
   mc admin user svcacct info ALIAS ACCESSKEY
```

- Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`ACCESSKEY`](#mc.admin.user.svcacct.info.ACCESSKEY) with the service account access key.

The output resembles the following:

```shell
AccessKey: myuserserviceaccount
ParentUser: myuser
Status: on
Comment:
Policy: implied
Expiration: no-expiry
```

### Display Service Account Policy Details {#display-service-account-policy-details}

Use [`mc admin user svcacct info`](#command-mc.admin.user.svcacct.info) to display the policies attached to service account:

```shell
   mc admin user svcacct info --policy ALIAS ACCESSKEY
```

- Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-user-add/#mc.admin.user.add.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`ACCESSKEY`](#mc.admin.user.svcacct.info.ACCESSKEY) with the service account access key.

The output resembles the following:

```shell
{
 "Version": "2012-10-17",
 "Statement": [
  {
   "Effect": "Allow",
   "Action": [
    "s3:*"
   ],
   "Resource": [
    "arn:aws:s3:::*"
   ]
  }
 ]
}
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
