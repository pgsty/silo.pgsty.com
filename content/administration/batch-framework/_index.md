---
title: "Batch Framework"
url: "/administration/batch-framework/"
weight: 170
icon: fa-solid fa-layer-group
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/batch-framework.rst
upstream_modified: false
---

<a id="batch-framework"></a>
<a id="minio-batch-framework"></a>

## Overview {#overview}

The MinIO Batch Framework allows you to create, manage, monitor, and execute jobs using a YAML-formatted job definition file (a “batch file”). The batch jobs run directly on the MinIO deployment to take advantage of the server-side processing power without constraints of the local machine where you run the [MinIO Client](/reference/minio-mc/#minio-client).

A batch file defines one job task.

Once started, MinIO starts processing the job. Time to completion depends on the resources available to the deployment.

If any portion of the job fails, MinIO retries the job up to the number of times defined in the job definition.

The MinIO Batch Framework supports the following job types:

| Job Type | Description |
| --- | --- |
| [replicate](/administration/batch-framework-job-replicate/#minio-batch-framework-replicate-job) | Perform a one-time replication procedure from one MinIO location to another MinIO location. |
| [keyrotate](/administration/batch-framework-job-keyrotate/#minio-batch-framework-keyrotate-job) | Perform a one-time process to cycle the [sse-s3 or sse-kms](/operations/server-side-encryption/#minio-sse-data-encryption) cryptographic keys on objects. |
| [expire](/administration/batch-framework-job-expire/#minio-batch-framework-expire-job) | Perform a one-time immediate expiration of objects in a bucket. |

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

Each batch job executes using the credentials specified in the batch definition. The success of a given batch job depends on those credentials having the appropriate [permissions](/administration/identity-access-management/policy-based-access-control/#minio-policy) to perform all requested actions.

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
