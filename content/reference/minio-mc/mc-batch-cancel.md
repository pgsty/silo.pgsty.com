---
title: "mc batch cancel"
url: "/reference/minio-mc/mc-batch-cancel/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="mc-batch-cancel"></a>
<a id="minio-mc-batch-cancel"></a>

<a id="command-mc.batch.cancel"></a>

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-03-20T17-17-53Z
{{% /alert %}}

## Syntax {#syntax}

The [`mc batch cancel`](#command-mc.batch.cancel) stops an ongoing batch job.

You must specify the job ID. To find the job ID, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command outputs the job definition for the job identified as `KwSysDpxcBU9FNhGkn2dCf`.

```shell
mc batch cancel myminio KwSysDpxcBU9FNhGkn2dCf
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] batch cancel ALIAS JOBID
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.batch.cancel.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for the MinIO deployment on which the job is currently running.

##### `JOBID` {#mc.batch.cancel.JOBID}

*mc-cmd*

*Required*

The unique identifier of the batch job to cancel. To find the ID of a job, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Cancel an ongoing batch job {#cancel-an-ongoing-batch-job}

The following command cancels the job with ID `KwSysDpxcBU9FNhGkn2dCf` on the deployment at alias `myminio`:

```shell
mc batch cancel myminio KwSysDpxcBU9FNhGkn2dCf
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
