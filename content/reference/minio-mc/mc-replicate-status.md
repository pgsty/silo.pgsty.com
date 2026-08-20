---
title: "mc replicate status"
url: "/reference/minio-mc/mc-replicate-status/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-replicate-status.rst
upstream_modified: false
---

<a id="mc-replicate-status"></a>
<a id="minio-mc-replicate-status"></a>

<a id="command-mc.replicate.status"></a>

## Syntax {#syntax}

The [`mc replicate status`](#command-mc.replicate.status) command displays the [replication status](/administration/bucket-replication/#minio-bucket-replication-serverside) of a MinIO bucket. The status also lists the remote target path or location.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays the current replication status of the `mydata` bucket on the `myminio` MinIO deployment:

```shell
mc replicate status myminio/mydata
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] replicate status TARGET
                           [--limit-upload value]
                           [--limit-download value]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.replicate.status.ALIAS}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment and full path to the bucket or bucket prefix for which to display the replication status. For example:

```text
mc replicate status myminio/mybucket
```

##### `--limit-download` {#mc.replicate.status.-limit-download}

*mc-cmd*

*Optional*

Limit download rates to no more than a specified rate in KiB/s, MiB/s, or GiB/s. Valid units include:

- `B` for bytes
- `K` for kilobytes
- `G` for gigabytes
- `T` for terabytes
- `Ki` for kibibytes
- `Gi` for gibibytes
- `Ti` for tebibytes

For example, to limit download rates to no more than 1 GiB/s, use the following:

```text
--limit-download 1G
```

If not specified, MinIO uses an unlimited download rate.

##### `--limit-upload` {#mc.replicate.status.-limit-upload}

*mc-cmd*

*Optional*

Limit upload rates to no more than the specified rate in KiB/s, MiB/s, or GiB/s. Valid units include:

- `B` for bytes
- `K` for kilobytes
- `G` for gigabytes
- `T` for terabytes
- `Ki` for kibibytes
- `Gi` for gibibytes
- `Ti` for tebibytes

For example, to limit upload rates to no more than 1 GiB/s, use the following:

```text
--limit-upload 1G
```

If not specified, MinIO uses an unlimited upload rate.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Display Replication Status {#display-replication-status}

Use [`mc replicate status`](#command-mc.replicate.status) to show bucket replication status:

```shell
mc replicate status ALIAS/PATH
```

- Replace [`ALIAS`](#mc.replicate.status.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace [`PATH`](#mc.replicate.status.ALIAS) with the path to the bucket or bucket prefix.

## Behavior {#behavior}

### Removed and Re-added ARNs {#removed-and-re-added-arns}

> [!NOTE]
> **Changed: mc**
>
> RELEASE.2023-03-20T17-17-53Z

The standard output of this command does not display ARNs previously removed from a replication configuration.

To list all ARNs, including ARNs no longer part of the replication, use the `--json` flag. The `json` output continues to show data replicated under old ARNs. This may be valuable if an ARN was removed and re-added for the same bucket.

New ARNs do **not** cause re-replication of previously synced objects.
