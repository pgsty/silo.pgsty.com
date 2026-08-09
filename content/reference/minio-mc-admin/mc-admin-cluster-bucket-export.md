---
title: "mc admin cluster bucket export"
url: "/reference/minio-mc-admin/mc-admin-cluster-bucket-export/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="command-mc.admin.cluster.bucket.export"></a>
<a id="mc-admin-cluster-bucket-export"></a>
<a id="minio-mc-admin-cluster-bucket-export"></a>

## Description {#description}

{{% alert color="info" %}}
**Added: RELEASE.2022-06-17T02-52-50Z**

{{% /alert %}}

The [`mc admin cluster bucket export`](#command-mc.admin.cluster.bucket.export) command exports bucket metadata for use with the [`mc admin cluster bucket import`](/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#command-mc.admin.cluster.bucket.import) command.

You can use this command to manually back up the metadata for the specified MinIO bucket. The command always saves the output as `cluster-metadata.zip`.

If you specify only the deployment as the target, this command backs up all bucket metadata on the target deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command exports all bucket metadata for the `myminio` deployment.

```shell
mc admin cluster bucket export myminio
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin cluster bucket export  \
                                      ALIAS[/BUCKET]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.cluster.bucket.export.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `BUCKET` {#mc.admin.cluster.bucket.export.BUCKET}

*mc-cmd*

*Optional*

The bucket to export metadata for.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
