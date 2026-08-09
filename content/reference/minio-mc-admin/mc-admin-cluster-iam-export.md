---
title: "mc admin cluster iam export"
url: "/reference/minio-mc-admin/mc-admin-cluster-iam-export/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="command-mc.admin.cluster.iam.export"></a>
<a id="mc-admin-cluster-iam-export"></a>
<a id="minio-mc-admin-cluster-iam-export"></a>

## Description {#description}

{{% alert color="info" %}}
**Added: RELEASE.2022-06-26T18-51-48Z**

{{% /alert %}}

The [`mc admin cluster iam export`](#command-mc.admin.cluster.iam.export) command exports [IAM](/administration/identity-access-management/#minio-authentication-and-identity-management) metadata for use with the [`mc admin cluster iam import`](/reference/minio-mc-admin/mc-admin-cluster-iam-import/#command-mc.admin.cluster.iam.import) command.

The command saves the output as `ALIAS-iam-metadata.zip`, where `ALIAS` is the [`alias`](#mc.admin.cluster.iam.export.ALIAS) of the MinIO deployment.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command exports all IAM metadata for the `myminio` deployment.

```shell
mc admin cluster iam export myminio
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin cluster iam export ALIAS  \
                 [--output, -o <string>]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

Starting with [RELEASE.2023-05-04T18-10-16Z](https://github.com/minio/mc/releases/tag/RELEASE.2023-05-04T18-10-16Z), [`mc admin cluster iam export`](#command-mc.admin.cluster.iam.export) adds support for aliases ending with a trailing forward slash `ALIAS/`. Prior to this release, the command would fail when provided a trailing forward slash.

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.cluster.iam.export.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment to export IAM metadata for.

##### `--output, --o` {#mc.admin.cluster.iam.export.-output}

*mc-cmd*

*Optional*

Specify a custom file and path to use when exporting the IAM data.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Download all IAM metadata for a cluster to a ZIP file {#download-all-iam-metadata-for-a-cluster-to-a-zip-file}

The following command downloads all IAM metadata for the cluster at alias `myminio`, then stores the metadata to a ZIP file.

```shell
mc admin cluster iam export myminio
```

The ZIP file is named `<alias>-iam-info.zip` where `<alias>` is the alias of the cluster. For the above example, the file is named `myminio-iam-info.zip`.

The file is placed in the current active directory path.

### Download all IAM metadata for a cluster and specify the name and path of the ZIP file {#download-all-iam-metadata-for-a-cluster-and-specify-the-name-and-path-of-the-zip-file}

The following command downloads all IAM metadata for the cluster at alias `myminio`, then stores the metadata to a ZIP file at `/tmp/myminio-iam.zip`.

```shell
mc admin cluster iam export myminio --output /tmp/myminio-iam.zip
```
