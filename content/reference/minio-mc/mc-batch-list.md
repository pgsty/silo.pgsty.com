---
title: "mc batch list"
url: "/reference/minio-mc/mc-batch-list/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-list.rst
upstream_modified: true
---

<a id="mc-batch-list"></a>
<a id="minio-mc-batch-list"></a>

<a id="command-mc.batch.list"></a>

> [!NOTE]
> **Changed: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

## Syntax {#syntax}

The [`mc batch list`](#command-mc.batch.list) command outputs a list of the batch jobs currently in progress on a deployment.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command outputs a list of all jobs currently in progress on the `myminio` alias.

```shell
mc batch list myminio
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] batch list TARGET           \
                            --type "string"
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.batch.list.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment for which you want to list jobs in progress.

##### `--type` {#mc.batch.list.-type}

*mc-cmd*

*Optional*

List batch jobs only of a certain type.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### List all `replicate` type batch jobs {#list-all-replicate-type-batch-jobs}

The following command lists the `replicate` type job(s) on the deployment at [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`:

```shell
mc batch list myminio --type "replicate"
```

- Replace `myminio` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment that should run the job.
- Replace `replicate` with the job type to output.

  Currently, [`mc batch`](/reference/minio-mc/mc-batch/#command-mc.batch) only supports the `replicate` job type.

The output of the above command is similar to the following:

```shell
ID                      TYPE            USER            STARTED
E24HH4nNMcgY5taynaPfxu  replicate       minioadmin      1 minute ago
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Permissions {#permissions}

You must have the [`admin:ListBatchJobs`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-ListBatchJobs) permission to list jobs on the deployment.
