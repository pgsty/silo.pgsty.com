---
title: "mc batch start"
url: "/reference/minio-mc/mc-batch-start/"
weight: 50
minio_origin: true
silo_modified: true
---

<a id="mc-batch-start"></a>
<a id="minio-mc-batch-start"></a>

<a id="command-mc.batch.start"></a>

{{% alert color="info" %}}
**Changed: MinIO**

RELEASE.2022-10-09T21-10-59Z or later
{{% /alert %}}

## Syntax {#syntax}

The [`mc batch start`](#command-mc.batch.start) command launches a batch job from a job batch YAML file.

The batch job runs to completion (or up to the number of retries specified in the file) one time. To run the batch job again after completion, you must start it again.

{{< tabpane text=true persist=header >}}
{{% tab header="EXAMPLE" %}}
The following command creates a basic YAML file for a replicate job on the `mybucket` bucket of the `myminio` alias.

```shell
mc batch start myminio jobfile.yaml
```

The output of the above command is something similar to:

```shell
Successfully start 'replicate' job `B34HHqnNMcg1taynaPfxu` on '2022-10-24 17:19:06.296974771 -0700 PDT'
```

{{% /tab %}}
{{% tab header="SYNTAX" %}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] batch start    \
                       ALIAS   \
                       JOBFILE
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{% /tab %}}
{{< /tabpane >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.batch.start.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) on which to start the batch job.

For example:

```text
mc batch start myminio replicate.yaml
```

##### `JOBFILE` {#mc.batch.start.JOBFILE}

*mc-cmd*

*Required*

A YAML-defined batch job. The job may have as many tasks as desired; there is no predefined limit.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Example {#example}

### Start a Batch Job {#start-a-batch-job}

The following command starts the batch of job(s) defined in the file `replication.yaml` on the deployment at [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) `myminio`:

```shell
mc batch start myminio ./replication.yaml
```

- Replace `myminio` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment that should run the job.
- Replace `./replication.yaml` with the yaml-formatted file that describes the batch job. Use the file path relative to your current location.

The output of the above command is similar to the following:

```shell
Successfully start 'replicate' job `E24HH4nNMcgY5taynaPfxu` on '2022-09-26 17:19:06.296974771 -0700 PDT'
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.

## Permissions {#permissions}

You must have the [`admin:StartBatchJob`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-StartBatchJob) permission on the deployment to start jobs.
