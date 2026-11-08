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

`mcli batch status TARGET JOBID` follows a batch job until it completes or fails. When live metrics are not yet available, it reports `pending` (`status: "pending"` in JSON) rather than treating a queued job or missing metric sample as complete. If no job metrics arrive for 30 seconds or the stream ends early, the client queries persisted job status (with a 10-second timeout per request) and returns an error if no terminal state is available; re-run the command to resume observation.

Successfully retrieving either a `complete` or `failed` terminal state exits `0`—automation scripts should inspect the returned `status` field to determine whether the job succeeded. Unavailable status, missing jobs, and request errors exit non-zero. IOPs calculations also no longer overflow at large object counts; see the [release changes](/blog/release/silo-20261026/#mcli).

## Changes after 20261026 (unreleased) {#silo-status-details}

The coordinated SILO and mcli versions expose `versionsSkippedLocked`, `keysRefused`, `failureReason`, and `pausedReason` in both live metrics and saved status. Terminal output shows these details; JSON output keeps the existing `metric` and adds a `details` object when there are counts or reasons to report.

A completed job with skipped versions or refused keys is labeled `complete-with-skips`. A paused job is labeled `paused` and remains under observation while the server waits to retry. Retrieving `complete-with-skips`, like retrieving `complete` or `failed`, exits `0`; scripts must check the status and counters.

The client uses a complete live snapshot when available, including explicit zero counts to clear a previous pause or skip count. For servers or peers without the live extension, it continues to refresh saved details every five seconds and at completion. If terminal details cannot be confirmed, it reports `detailsUnavailable` instead of implying that the skip counts are zero. Use the matching maintained mcli build with the new server; the released 20261026 client does not display these details.

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
