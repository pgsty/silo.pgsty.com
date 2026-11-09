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

<a id="silo-status-details"></a>

## mcli 20261109 and next SILO release: pauses and skipped work {#silo-job-outcomes}

[mcli 20261109](/blog/release/mcli-20261109/) and the next coordinated SILO release add `paused` and `complete-with-skips`. `paused` is nonterminal: the server is waiting to retry, and the client keeps observing while live metrics remain available. `complete-with-skips` means the run finished but left protected versions or refused keys in place. It does not mean every selected object was removed. Like `complete` and `failed`, retrieving it exits `0`; scripts must inspect the status and counters.

The text display includes `VersionsSkippedLocked`, `KeysRefused`, `FailureReason`, and `PausedReason` when present. JSON preserves the existing `metric` object and adds those fields under `details` as `versionsSkippedLocked`, `keysRefused`, `failureReason`, and `pausedReason`. The counters have different units: skipped versions and refused whole keys. They must not be added to get a count of deleted objects.

The client uses a complete live snapshot when available, including explicit zero counts to clear a previous pause or skip count. For servers or peers without the live extension, it refreshes saved details every five seconds during observation and once when live metrics report a terminal result (with a ten-second timeout per request). A saved snapshot older than live progress cannot restore a stale pause or attach old counters to a newer outcome. If terminal details cannot be confirmed, the live outcome remains visible with `detailsUnavailable` in JSON and an explanation in text; absent details must not be read as zero skips. Older servers without the added fields retain their existing output.

If the live stream ends while the saved state is still paused, the command prints the pause reason and exits nonzero because it has no terminal result. Re-run the command to continue observation; this does not cancel or resubmit the job.

The same freshness check applies after the stream ends: a saved terminal result older than the progress already observed is rejected with a nonzero exit status. Delayed live samples cannot move progress backward, and a report that claims both complete and failed is rejected.

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
