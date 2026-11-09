---
title: "Batch Framework"
url: "/administration/batch-framework/"
weight: 170
icon: fa-solid fa-layer-group
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/batch-framework.rst
upstream_modified: true
---

<a id="batch-framework"></a>
<a id="minio-batch-framework"></a>

## Overview {#overview}

The MinIO Batch Framework allows you to create, manage, monitor, and execute jobs using a YAML-formatted job definition file (a “batch file”). The batch jobs run directly on the MinIO deployment to take advantage of the server-side processing power without constraints of the local machine where you run the [MinIO Client](/reference/minio-mc/#minio-client).

A batch file defines one job task.

Once started, MinIO starts processing the job. Time to completion depends on the resources available to the deployment.

Ordinary job failures use the retry limits in the definition. SILO 20261109 distinguishes authorization refusal from temporary pauses as described below.

The MinIO Batch Framework supports the following job types:

| Job Type | Description |
| --- | --- |
| [replicate](/administration/batch-framework-job-replicate/#minio-batch-framework-replicate-job) | Perform a one-time replication procedure from one MinIO location to another MinIO location. |
| [keyrotate](/administration/batch-framework-job-keyrotate/#minio-batch-framework-keyrotate-job) | Perform a one-time process to cycle the [sse-s3 or sse-kms](/operations/server-side-encryption/#minio-sse-data-encryption) cryptographic keys on objects. |
| [expire](/administration/batch-framework-job-expire/#minio-batch-framework-expire-job) | Perform a one-time immediate expiration of objects in a bucket. |
{.wide .expand}

## SILO 20261109: authorization and retries {#silo-lifecycle}

SILO binds local batch operations to the authenticated submitter at job creation. The credentials in a definition are used for its remote connections; they do not grant local server authority. IAM changes are checked again when actions are taken. An explicit denial, expired or revoked credential, or changed submitter binding ends the job with `failureReason`. Statements that need request context unavailable to a background job refuse the action.

IAM startup, unavailable policy material, and an authorization plugin that cannot return a valid decision are temporary failures. Submission returns `503` when authorization cannot be decided. Expiration and key rotation pause with `pausedReason`, preserve completed progress, and retry in the same process with bounded exponential backoff and jitter. Immediate or streamed listing failures also pause these jobs. Rotation pauses when its selected source is in a moving pool and resumes after the conflict clears. Every retry resolves current identity and policies again. A pending or paused job is not a completed or failed report and is not removed by terminal-report cleanup. Administrator cancellation takes precedence over queued work and retries.

Push, pull, and Snowball replication also pause with `pausedReason` when a required authorization dependency or report read is temporarily unavailable, including an outage that begins during object processing, and restart their source scan from the beginning on retry; see [Batch Replication](/administration/batch-framework-job-replicate/#silo-retry). Other mid-run replication failures follow the existing finite object retry behavior and can end the run as failed.

Startup discovery also retries failed manifest listings and storage reads with bounded backoff. It remembers manifests already admitted during that discovery, so a later scan cannot rerun a job that finished while waiting. Cancellation fences stale discovery results. Missing, malformed, or unsupported manifests are not queued; malformed and unsupported definitions remain on disk for inspection. A storage outage during discovery does not require a restart once storage recovers.

Completed jobs remain completed after restart, including legacy jobs and jobs whose credentials later expire or change. Unfinished jobs from releases without submitter binding require resubmission. New bound definitions and authorized progress reports use formats rejected by older executors. This fences those records on rollback, but does not make a mixed cluster safe: an old node can still accept and execute its own old-format jobs. Stop submissions and drain or cancel old jobs before changing versions, and do not downgrade with pending authorized jobs.

### Upgrading and rolling back 20261109 {#upgrade-20261109}

This release deliberately introduces a batch-record format boundary: new job manifests use the `SILO-BATCH` v2 envelope and authorized progress reports also use v2. The 20261026 executor cannot execute or resume these records. Ordinary S3 object formats are unaffected, but batch jobs cannot follow a binary downgrade transparently.

1. Stop submissions to every node before upgrading. Inventory jobs with `mcli batch list ALIAS` and `mcli batch status ALIAS JOBID`. Drain running, pending and paused jobs, or cancel them with `mcli batch cancel ALIAS JOBID`; preserve their original YAML definitions and records of completed work.
2. Resume submissions only after every node is upgraded. Unfinished legacy jobs do not acquire an authorization binding automatically: resubmit with an identity that has the required data permissions. Reconcile completed work before resubmission to avoid unwanted repeated work. Completed legacy jobs need no resubmission.
3. Do not run batch jobs during a mixed-version upgrade: old nodes can still accept and execute their own old-format jobs without the new submitter authorization checks.
4. Before rollback, stop submissions again and drain or cancel all new jobs, including paused jobs. Do not expect 20261026 to resume their progress, strip the format envelope, or edit authorization records. Preserve the records and reconcile results on a compatible release before deciding whether to resubmit.

Use [mcli batch status](/reference/minio-mc/mc-batch-status/#silo-job-outcomes) (`20261109`) to distinguish pauses, terminal failures, and completion with protected work left in place. `infraAdmin` still has other infrastructure administration capabilities; these job checks do not turn that role into a strict data-isolation boundary.

## MinIO Batch CLI {#minio-batch-cli}

- Install the [MinIO Client](/reference/minio-mc/#minio-client)
- Define an [`alias`](/reference/minio-mc/mc-alias-set/#command-mc.alias.set) for the MinIO deployment

The [`mc batch`](/reference/minio-mc/mc-batch/#command-mc.batch) commands include

<table>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a> command creates a basic YAML-formatted template file for the specified job type.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a> command launches a batch job from a job batch YAML file.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a> command outputs a list of the batch jobs currently in progress on a deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a> command outputs summaries of job events on a MinIO server.</p><aside class="alert alert-info"><p><strong>Changed: mc</strong></p><p>RELEASE.2024-07-03T20-17-25Z</p><p>Batch status displays summaries for active, in-progress jobs or any batch job completed in the previous three (3) days.</p></aside></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a> command outputs the job definition for a specified job ID.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>mc batch cancel</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>mc batch cancel</code></a> stops an ongoing batch job.</p></td>
    </tr>
  </tbody>
</table>

<a id="minio-batch-framework-access"></a>

## Access to `mc batch` {#access-to-mc-batch}

The submitting identity needs the relevant administration action and the local [data permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy) for the job. Credentials in the definition must separately permit its remote operations. See the 20261109 rules above.

The user executing the batch job must have the following permissions. You can alternatively restrict users from accessing these functions by blocking or limiting access to these actions:

**`admin:ListBatchJobs`**

> Grants the user the ability to see batch jobs currently in process.

**`admin:DescribeBatchJobs`**

> Grants the user the ability to see the definition details of batch job currently in process.

**`admin:StartBatchJob`**

> Grants the user the ability to start a batch job. The job may be further restricted by the credentials the job uses to access either the source or target deployments.

**`admin:CancelBatchJob`**

> Allows the user to stop a batch job currently in progress.

You can assign any of these actions to users independently or in any combination.

The built-in `ConsoleAdmin` policy includes sufficient access to perform all of these types of batch job actions.

<a id="minio-batch-local"></a>

## `Local` Deployment {#local-deployment}

You run a batch job against a particular deployment by passing an `alias` to the [`mc batch`](/reference/minio-mc/mc-batch/#command-mc.batch) command. The deployment you specify in the command becomes the `local` deployment within the context of that batch job.
