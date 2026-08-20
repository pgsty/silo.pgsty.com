---
title: "mc support top disk"
url: "/reference/minio-mc/mc-support-top-disk/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-top-disk.rst
upstream_modified: false
---

<a id="mc-support-top-disk"></a>

<a id="command-mc.support.top.disk"></a>

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Syntax {#syntax}

The [`mc support top disk`](#command-mc.support.top.disk) command displays current drive statistics.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays the current in-progress S3 API calls on the [alias](/glossary/#term-alias) `myminio`.

```shell
mc support top disk myminio/
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] support top disk                     \
                             [--count, -c "integer"]  \
                             TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.support.top.disk.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or [prefix](/glossary/#term-prefix) where the command should run.

##### `--count, -c` {#mc.support.top.disk.-count}

*mc-cmd*

*Optional*

Display statistics for up to the entered number of drives.

If no entry is made, the command returns statistics for up to 10 drives.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
