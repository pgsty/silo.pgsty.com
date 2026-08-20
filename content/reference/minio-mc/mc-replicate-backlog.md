---
title: "mc replicate backlog"
url: "/reference/minio-mc/mc-replicate-backlog/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-replicate-backlog.rst
upstream_modified: false
---

<a id="mc-replicate-backlog"></a>
<a id="minio-mc-replicate-backlog"></a>
<a id="minio-mc-replicate-diff"></a>

<a id="command-mc.replicate.diff"></a>

<a id="command-mc.replicate.backlog"></a>

> [!NOTE]
> **Changed: mc.RELEASE.2023-07-18T21-05-38Z**
>
> `mc replicate diff` has been renamed `mc replicate backlog`. No functionality has changed.

## Description {#description}

The [`mc replicate backlog`](#command-mc.replicate.backlog) shows a list of unreplicated new or deleted objects.

You can list the replication status of objects for a particular remote target. To do so, you must have the ARN of the remote target. You can use [retrieve the remote targets configured for a bucket](/reference/deprecated/mc-admin-bucket-remote/#minio-retrieve-remote-bucket-targets) to find the ARN.

## Syntax {#syntax}

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command shows new or deleted objects in the `notes` bucket of the `teamorange/projects` prefix on the `myminio` alias that have not yet replicated to a specific remote target bucket. The remote target’s ARN is `arn:minio:replication::3bb8c736-4014-42c5-b3cb-d64e3ebaa75e:notes`.

```shell
mc replicate backlog myminio/notes/teamorange/projects --arn arn:minio:replication::3bb8c736-4014-42c5-b3cb-d64e3ebaa75e:notes
```

If any new or deleted objects have not yet replicated, the command outputs something similar to the following:

```shell
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:59 UTC]          478efe49-aa9d-46ab-8268-45b70cc4c341 PUT agenda.docx
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:15 UTC]          b283bf43-319f-455a-a779-3c2e669fad88 PUT budget-meeting.docx
```

In the output, `PUT` corresponds to a new object. Deleted objects or versions would show `DEL`.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] replicate backlog   \
                 [--arn "string"]    \
                 TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.replicate.backlog.TARGET}

*mc-cmd*

*Required*

The path to the alias, prefix, or object.

##### `arn` {#mc.replicate.backlog.arn}

*mc-cmd*

*Optional*

The ARN of the remote bucket to check for new or deleted objects that have not yet replicated.

When specified, the command returns a list of any new or deleted objects that have not replicated to the remote target. If not specified, the command returns a list of new or deleted objects on the source deployment that have not replicated to any remote target.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### View Unreplicated Versions of Objects at a Prefix {#view-unreplicated-versions-of-objects-at-a-prefix}

Display unreplicated `PUT` and `DELETE` actions for a prefix:

```shell
mc replicate backlog myminio/mybucket/path/to/prefix
```

- Replace `myminio/mybucket` with the [`ALIAS`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.ALIAS) and full bucket path for which to create the replication configuration.
- Replace `path/to/prefix` with the prefix or object to use for the request.

If unreplicated objects exist, the output returns a list of the actions that created or removed objects at the prefix that have not replicated to a remote target:

```shell
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:59 UTC]          478efe49-aa9d-46ab-8268-45b70cc4c341 PUT agenda.docx
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:15 UTC]          b283bf43-319f-455a-a779-3c2e669fad88 PUT budget-meeting.docx
```

### View Unreplicated Objects at a Specific Remote Target {#view-unreplicated-objects-at-a-specific-remote-target}

The following [`mc replicate backlog`](#command-mc.replicate.backlog) command shows unreplicated objects at an alias/bucket/prefix path for a specific remote target:

```shell
mc replicate backlog myminio/mybucket/path/to/prefix --arn <remote-arn>
```

- Replace `myminio/mybucket` with the [`ALIAS`](/reference/minio-mc/mc-replicate-add/#mc.replicate.add.ALIAS) and full bucket path for which to show unreplicated objects.
- Replace the `path/to/prefix` with the desired prefix or object path.
- Replace `<remote-arn>` with the resource number for a specific remote target.

If unreplicated objects exist, the output returns a list of the actions that created or removed objects that have not replicated to the remote target:

```shell
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:59 UTC]          478efe49-aa9d-46ab-8268-45b70cc4c341 PUT agenda.docx
[0001-01-01 00:00:00 UTC] [2022-10-06 17:18:15 UTC]          b283bf43-319f-455a-a779-3c2e669fad88 PUT budget-meeting.docx
```

### S3 Compatibility {#s3-compatibility}

The **`mc`** commandline tool is built for compatibility with the AWS S3 API and is tested with MinIO and AWS S3 for expected functionality and behavior.

MinIO provides no guarantees for other S3-compatible services, as their S3 API implementation is unknown and therefore unsupported. While **`mc`** commands *may* work as documented, any such usage is at your own risk.
