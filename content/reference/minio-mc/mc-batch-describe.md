---
title: "mc batch describe"
url: "/reference/minio-mc/mc-batch-describe/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="mc-batch-describe"></a>
<a id="minio-mc-batch-describe"></a>

<a id="command-mc.batch.describe"></a>

{{% alert color="info" %}}
**Changed: MinIO**

RELEASE.2022-10-08T20-11-00Z or later
{{% /alert %}}

## Syntax {#syntax}

The [`mc batch describe`](#command-mc.batch.describe) command outputs the job definition for a specified job ID.

You must specify the job ID. To find the job ID, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command outputs the job definition for the job identified as `KwSysDpxcBU9FNhGkn2dCf`.

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] batch describe TARGET           \
                                JOBID
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.batch.describe.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for the MinIO deployment to look for the Job ID.

##### `JOBID` {#mc.batch.describe.JOBID}

*mc-cmd*

*Required*

The unique identifier of a job to describe. To find the ID of a job, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Show the Definition of an In Progress Batch Job {#show-the-definition-of-an-in-progress-batch-job}

The following command provides the full job definition of a specific job at [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`:

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
```

- Replace `myminio` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment that should run the job.
- Replace `KwSysDpxcBU9FNhGkn2dCf` with the ID of the job to define.

The output of the above command is similar to the following:

```shell
mc batch describe myminio KwSysDpxcBU9FNhGkn2dCf
replicate:
  apiVersion: v1
...
```

Note, this example is truncated. The output is the full job definition for the specified job.

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Permissions {#permissions}

You must have the `admin:DescribeBatchJobs` permission to describe jobs on the deployment.
