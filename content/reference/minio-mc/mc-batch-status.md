---
title: "mc batch status"
url: "/reference/minio-mc/mc-batch-status/"
weight: 60
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch-status.rst
upstream_modified: true
---

<a id="mc-batch-status"></a>
<a id="minio-mc-batch-status"></a>

<a id="command-mc.batch.status"></a>

> [!NOTE]
> **Changed: MinIO**
>
> RELEASE.2022-10-09T21-10-59Z or later

## mcli 20261026 status and exit codes {#silo-20261026}

`mcli batch status TARGET JOBID` observes a job until completion or failure. Missing live metrics produce `pending` (also `status: "pending"` in JSON), rather than treating a queued job or missing sample as complete. After 30 seconds without job metrics, or when the stream ends early, the client queries persisted status; each status request has a 10-second timeout. Without an available terminal result it returns an error. Run the command again to resume observation.

Retrieving either a `complete` or `failed` terminal result exits 0; inspect the returned status for the job outcome. Unavailable status, missing jobs and request failures exit nonzero. Large object counts no longer overflow the IOPs calculation. See the [release changes](/blog/release/silo-20261026/#mcli).

## Syntax {#syntax}

The [`mc batch status`](#command-mc.batch.status) command outputs summaries of job events on a MinIO server.

> [!NOTE]
> **Changed: mc**
>
> RELEASE.2024-07-03T20-17-25Z
>
> Batch status displays summaries for active, in-progress jobs or any batch job completed in the previous three (3) days.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command outputs the status of the specified job with JobID `KwSysDpxcBU9FNhGkn2dCf` currently in progress on the `myminio` alias.

```shell
mcli batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mcli [GLOBALFLAGS] batch status TARGET JOBID
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.batch.status.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) for which to display batch job statuses.

##### `JOBID` {#mc.batch.status.JOBID}

*mc-cmd*

*Required*

The unique identifier of a job to summarize. To find the ID of a job, use [`mc batch list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list).

Both TARGET and JOBID are required.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Summarize the Events of an Active Replicate Job {#summarize-the-events-of-an-active-replicate-job}

The following command provides the real-time summary of an active job on the deployment at [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`:

```shell
mcli batch status myminio "KwSysDpxcBU9FNhGkn2dCf"
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

SILO is the supported server for PGSTY mcli; compatibility with upstream MinIO and other S3 services is [best effort](/reference/minio-mc/#command-mc).
