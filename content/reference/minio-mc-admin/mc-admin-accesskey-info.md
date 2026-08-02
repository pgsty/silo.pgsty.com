---
title: "mc admin accesskey info"
url: "/reference/minio-mc-admin/mc-admin-accesskey-info/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-info"></a>
<a id="minio-mc-admin-accesskey-info"></a>

<a id="command-mc.admin.accesskey.info"></a>

## Syntax {#syntax}

The [`mc admin accesskey info`](#command-mc.admin.accesskey.info) command returns a description of the specified [access key(s)](/administration/identity-access-management/minio-user-management/#minio-id-access-keys).

The description output includes the following details, as available:

- Access Key
- Parent user of the specified access key
- Access key status (`on` or `off`)
- Policy or policies
- Comment
- Expiration

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command returns information on the specified access key:

```shell
mc admin accesskey info myminio myuseraccesskey
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey info      \
                                 ALIAS     \
                                 ACCESSKEY
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.accesskey.info.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `ACCESSKEY` {#mc.admin.accesskey.info.ACCESSKEY}

*mc-cmd*

*Required*

The access key to display.

Return information for multiple access keys by separating each access key with a space.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display access key details {#display-access-key-details}

Use [`mc admin accesskey info`](#command-mc.admin.accesskey.info) to display details of an access key on a MinIO deployment:

```shell
   mc admin accesskey info myminio myaccesskey
```

- Replace `myminio` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`myaccesskey`](/reference/minio-mc-admin/mc-admin-user-svcacct-info/#mc.admin.user.svcacct.info.ACCESSKEY) with the access key for which to display information. List multiple keys by separating each with a space.

The output resembles the following:

```shell
AccessKey: myuserserviceaccount
ParentUser: myuser
Status: on
Comment:
Policy: implied
Expiration: no-expiry
```

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
