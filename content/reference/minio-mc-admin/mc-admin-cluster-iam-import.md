---
title: "mc admin cluster iam import"
url: "/reference/minio-mc-admin/mc-admin-cluster-iam-import/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-cluster-iam-import.rst
upstream_modified: false
---

<a id="command-mc.admin.cluster.iam.import"></a>
<a id="mc-admin-cluster-iam-import"></a>
<a id="minio-mc-admin-cluster-iam-import"></a>

## Description {#description}

> [!NOTE]
> **Added: RELEASE.2022-06-17T02-52-50Z**

The [`mc admin cluster iam import`](#command-mc.admin.cluster.iam.import) command imports [IAM](/administration/identity-access-management/#minio-authentication-and-identity-management) metadata as created by the [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) command.

You can use this command to manually restore IAM metadata settings for a MinIO deployment.

> [!NOTE]
> **Added: mc**
>
> RELEASE.2024-09-09T07-53-10Z
>
> The command outputs the results of the import, including the following:
>
> - count of individual entities imported by entity type
> - list of policies imported by entity type they imported to
> - list of entities that failed to import

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command imports the IAM metadata of the specified file onto the `myminio` deployment.

```shell
mc admin cluster iam import myminio ~/minio-metadata-backup/myminio-cluster.zip
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin cluster iam import  \
                                   ALIAS \
                                   IAM-METADATA.ZIP
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

Starting with [RELEASE.2023-05-04T18-10-16Z](https://github.com/minio/mc/releases/tag/RELEASE.2023-05-04T18-10-16Z), [`mc admin cluster iam import`](#command-mc.admin.cluster.iam.import) adds support for aliases ending with a trailing forward slash `ALIAS/`. Prior to this release, the command would fail when provided a trailing forward slash.

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.cluster.iam.import.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

##### `IAM-METADATA.ZIP` {#mc.admin.cluster.iam.import.IAM-METADATA.ZIP}

*mc-cmd*

*Required*

The path to the IAM metadata file to import.

Use the [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) to export IAM metadata for use with this command.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
