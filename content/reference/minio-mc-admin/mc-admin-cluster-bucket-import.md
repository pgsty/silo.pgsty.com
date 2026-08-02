---
title: "mc admin cluster bucket import"
url: "/reference/minio-mc-admin/mc-admin-cluster-bucket-import/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="command-mc.admin.cluster.bucket.import"></a>
<a id="mc-admin-cluster-bucket-import"></a>
<a id="minio-mc-admin-cluster-bucket-import"></a>

## Description {#description}

{{% alert color="info" %}}
**Added: RELEASE.2022-06-17T02-52-50Z**

{{% /alert %}}

The [`mc admin cluster bucket import`](#command-mc.admin.cluster.bucket.import) command imports bucket metadata as created by the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) command.

You can use this command to manually restore the metadata to the specified bucket on a MinIO deployment.

If you specify only the deployment as the target, this command applies the metadata objects to all matching buckets on the target.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command imports the specified metadata to the `myminio` deployment.

```shell
mc admin cluster bucket import myminio ~/minio-metadata-backup/myminio-cluster.zip
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin cluster bucket import  \
                                    ALIAS[/BUCKET] \
                                    METADATA.ZIP
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.cluster.bucket.import.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `METADATA.ZIP` {#mc.admin.cluster.bucket.import.METADATA.ZIP}

*mc-cmd*

*Required*

The path to the metadata file to import.

Use [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) to export bucket metadata for use with this command.

##### `BUCKET` {#mc.admin.cluster.bucket.import.BUCKET}

*mc-cmd*

*Optional*

The bucket to apply the imported metadata to.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
