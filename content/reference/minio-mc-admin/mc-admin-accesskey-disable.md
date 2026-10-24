---
title: "mc admin accesskey disable"
url: "/reference/minio-mc-admin/mc-admin-accesskey-disable/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-accesskey-disable.rst
upstream_modified: true
---

<a id="mc-admin-accesskey-disable"></a>
<a id="minio-mc-admin-accesskey-disable"></a>

<a id="command-mc.admin.accesskey.disable"></a>

## Syntax {#syntax}

The [`mc admin accesskey disable`](#command-mc.admin.accesskey.disable) command disables an existing access key for a MinIO IDP user.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command disables the specified access key:

```shell
mc admin accesskey disable myminio myuserserviceaccount
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin accesskey disable         \
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

##### `ALIAS` {#mc.admin.accesskey.disable.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `SERVICEACCOUNT` {#mc.admin.accesskey.disable.SERVICEACCOUNT}

*mc-cmd*

*Required*

The access key to disable.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

SILO is the supported server for PGSTY mcli; compatibility with upstream MinIO and other S3 services is [best effort](/reference/minio-mc/#command-mc).
