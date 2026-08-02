---
title: "mc batch"
url: "/reference/minio-mc/mc-batch/"
weight: 40
icon: fa-solid fa-layer-group
minio_origin: true
silo_modified: false
---

<a id="mc-batch"></a>

<a id="command-mc.batch"></a>

{{% alert color="info" %}}
**Added: mc**

RELEASE.2023-03-20T17-17-53Z

Added the ability to cancel jobs with the [`mc batch cancel`](/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel) command.
{{% /alert %}}

## Description {#description}

The [`mc batch`](#command-mc.batch) commands allow you to run one or more job tasks on a MinIO deployment.

## Subcommands {#subcommands}

[`mc batch`](#command-mc.batch) includes the following subcommands:

<table>
  <thead>
    <tr>
      <th><p>Subcommand</p></th>
      <th><p>Description</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>cancel</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel"><code>mc batch cancel</code></a> stops an ongoing batch job.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>describe</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe"><code>mc batch describe</code></a> command outputs the job definition for a specified job ID.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>generate</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate"><code>mc batch generate</code></a> command creates a basic YAML-formatted template file for the specified job type.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>list</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-list/#command-mc.batch.list"><code>mc batch list</code></a> command outputs a list of the batch jobs currently in progress on a deployment.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>start</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-start/#command-mc.batch.start"><code>mc batch start</code></a> command launches a batch job from a job batch YAML file.</p></td>
    </tr>
    <tr>
      <td><p><a href="/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>status</code></a></p></td>
      <td><p>The <a href="/reference/minio-mc/mc-batch-status/#command-mc.batch.status"><code>mc batch status</code></a> command outputs summaries of job events on a MinIO server.</p><aside class="alert alert-info"><p><strong>Changed: mc</strong></p><p>RELEASE.2024-07-03T20-17-25Z</p><p>Batch status displays summaries for active, in-progress jobs or any batch job completed in the previous three (3) days.</p></aside></td>
    </tr>
  </tbody>
</table>
