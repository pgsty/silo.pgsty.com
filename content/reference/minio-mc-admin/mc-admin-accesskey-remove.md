---
title: "mc admin accesskey rm"
url: "/reference/minio-mc-admin/mc-admin-accesskey-remove/"
weight: 70
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-rm"></a>
<a id="minio-mc-admin-accesskey-remove"></a>

<a id="command-mc.admin.accesskey.remove"></a>

<a id="command-mc.admin.accesskey.rm"></a>

## Syntax {#syntax}

The [`mc admin accesskey rm`](#command-mc.admin.accesskey.rm) command removes an access key associated to a user on the deployment.

The [`mc admin accesskey remove`](#command-mc.admin.accesskey.remove) command has equivalent functionality to [`mc admin accesskey rm`](#command-mc.admin.accesskey.rm).

{{% alert color="danger" %}}
**Warning**

Applications can no longer authenticate using the access key after its removal.
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command removes the specified access key:

```shell
mc admin accesskey rm myminio myuserserviceaccount
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey rm                \
                                 ALIAS             \
                                 ACCESSKEYTOREMOVE
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.accesskey.rm.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `ACCESSKEYTOREMOVE` {#mc.admin.accesskey.rm.ACCESSKEYTOREMOVE}

*mc-cmd*

*Required*

The access key to remove.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
