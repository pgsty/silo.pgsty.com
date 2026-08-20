---
title: "mc event ls"
url: "/reference/minio-mc/mc-event-list/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-event-list.rst
upstream_modified: false
---

<a id="mc-event-ls"></a>
<a id="minio-mc-event-list"></a>

<a id="command-mc.event.list"></a>

<a id="command-mc.event.ls"></a>

## Syntax {#syntax}

The [`mc event ls`](#command-mc.event.ls) command lists all event notification triggers for a bucket.

The alias [`mc event list`](#command-mc.event.list) has equivalent functionality to [`mc event ls`](#command-mc.event.ls).

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command lists all configured event notifications for the specified [bucket notification target](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc event ls myminio myminio/mydata arn:aws:sqs::primary:target
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

```shell
mc [GLOBALFLAGS] event ls [FLAGS] ALIAS ARN
```

### Parameters {#parameters}

##### `ALIAS` {#mc.event.ls.ALIAS}

*mc-cmd*

*Required*

The S3 service [alias](/reference/minio-mc/mc-alias-set/#alias) and bucket to which the command lists event notification. For example:

```shell
mc event ls play/mybucket ARN...
```

##### `ARN` {#mc.event.ls.ARN}

*mc-cmd*

*Required*

The [Amazon Resource Name (ARN)](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns) of the bucket resource.

The MinIO server outputs an ARN at startup for each configured notification target. See [Bucket Notifications](/administration/monitoring/bucket-notifications/#minio-bucket-notifications) for more information.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### List Event Notifications on a Bucket {#list-event-notifications-on-a-bucket}

{{< tabs group="example-syntax" >}}
{{< tab label="Example" value="example" >}}
The following command lists all event notification triggers on a bucket.

```shell
mc event ls myminio/mydata
```
{{< /tab >}}
{{< tab label="Syntax" value="syntax" >}}
```shell
mc event ls ALIAS ARN
```

- Replace `ALIAS` with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to add the bucket notification event. For example:

  `myminio/mydata`
- Replace `ARN` with the notification target [`ARN`](/reference/minio-mc/mc-event-add/#mc.event.add.ARN).
{{< /tab >}}
{{< /tabs >}}

## Behavior {#behavior}

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
