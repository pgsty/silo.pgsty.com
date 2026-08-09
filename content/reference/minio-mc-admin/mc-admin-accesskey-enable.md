---
title: "mc admin accesskey enable"
url: "/reference/minio-mc-admin/mc-admin-accesskey-enable/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="mc-admin-accesskey-enable"></a>
<a id="minio-mc-admin-accesskey-enable"></a>

<a id="command-mc.admin.accesskey.enable"></a>

## Syntax {#syntax}

The [`mc admin accesskey enable`](#command-mc.admin.accesskey.enable) command enables an existing access key.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command enables the specified access key:

```shell
mc admin accesskey enable myminio myuserserviceaccount
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey enable          \
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

##### `ALIAS` {#mc.admin.accesskey.enable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `SERVICEACCOUNT` {#mc.admin.accesskey.enable.SERVICEACCOUNT}

*mc-cmd*

*Required*

The access key to enable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
