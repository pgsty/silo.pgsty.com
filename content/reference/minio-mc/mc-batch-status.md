---
title: "mc batch status"
url: "/reference/minio-mc/mc-batch-status/"
weight: 60
minio_origin: true
silo_modified: false
---

<a id="mc-batch-status"></a>
<a id="minio-mc-batch-status"></a>

<a id="command-mc.batch.status"></a>

{{% alert color="info" %}}
**Changed: MinIO**

RELEASE.2022-10-08T20-11-00Z or later
{{% /alert %}}

## Syntax {#syntax}

The [`mc batch status`](#command-mc.batch.status) command outputs summaries of job events on a MinIO server.

{{% alert color="info" %}}
**Changed: mc**

RELEASE.2024-07-03T20-17-25Z

Batch status displays summaries for active, in-progress jobs or any batch job completed in the previous three (3) days.
{{% /alert %}}

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command outputs the status of the specified job with JobID `KwSysDpxcBU9FNhGkn2dCf` currently in progress on the `myminio` alias.

```shell
mc batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
```
{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] batch list TARGET           \
                            ["JOBID"]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `TARGET` {#mc.batch.status.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for which to display batch job statuses.

##### `JOBID` {#mc.batch.status.JOBID}

*mc-cmd*

*Optional*

The unique identifier of a job to summarize. To find the ID of a job, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

If not specified, the command returns a summary for the current active batch job.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Summarize the Events of an Active Replicate Job {#summarize-the-events-of-an-active-replicate-job}

The following command provides the real-time summary of an active job on the deployment at [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`:

```shell
mc batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
```

- Replace `myminio` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment that should run the job.

The output of the above command is similar to the following:

```shell
●∙∙
JobType:        replicate
Objects:        28766
Versions:       28766
FailedObjects:  0
Transferred:    406 MiB
Elapsed:        2m14.227222868s
CurrObjName:    share/doc/xml-core/examples/foo.xmlcatalogs
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
