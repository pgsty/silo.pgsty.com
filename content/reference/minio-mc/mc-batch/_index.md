---
title: "mc batch"
url: "/reference/minio-mc/mc-batch/"
weight: 40
icon: fa-solid fa-layer-group
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-batch.rst
upstream_modified: true
---

<a id="mc-batch"></a>

<a id="command-mc.batch"></a>

> [!NOTE]
> **Added: mc**
>
> RELEASE.2023-03-20T17-17-53Z
>
> Added the ability to cancel jobs with the [`mc batch cancel`](/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel) command.

## Description {#description}

The [`mc batch`](#command-mc.batch) commands allow you to run one or more job tasks on a MinIO deployment.

## Subcommands {#subcommands}

[`mc batch`](#command-mc.batch) includes the following subcommands:

| Subcommand                                                                     | Description                                                              |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------ |
| [`cancel`](/reference/minio-mc/mc-batch-cancel/#command-mc.batch.cancel)       | Stops an ongoing batch job.                                              |
| [`describe`](/reference/minio-mc/mc-batch-describe/#command-mc.batch.describe) | Outputs the job definition for a specified job ID.                       |
| [`generate`](/reference/minio-mc/mc-batch-generate/#command-mc.batch.generate) | Creates a basic YAML-formatted template file for the specified job type. |
| [`list`](/reference/minio-mc/mc-batch-list/#command-mc.batch.list)             | Outputs a list of batch jobs currently in progress on a deployment.      |
| [`start`](/reference/minio-mc/mc-batch-start/#command-mc.batch.start)          | Starts a batch job from a YAML job definition file.                      |
| [`status`](/reference/minio-mc/mc-batch-status/#command-mc.batch.status)       | Outputs summaries of job events on a server.                             |
{.wide .expand}

> [!NOTE]
> **Changed: mc `RELEASE.2024-07-03T20-17-25Z`**
>
> [`mc batch status`](/reference/minio-mc/mc-batch-status/#command-mc.batch.status) displays summaries for active, in-progress jobs and for batch jobs completed within the previous three (3) days.
