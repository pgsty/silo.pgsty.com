---
title: "mc support top drive (disk alias)"
url: "/reference/minio-mc/mc-support-top-disk/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-top-disk.rst
upstream_modified: true
---

<a id="mc-support-top-disk"></a>

<a id="command-mc.support.top.disk"></a>

> [!NOTE]
> **Local diagnostics**
>
> PGSTY mcli runs these diagnostics against SILO without SUBNET registration. Online registration, uploads, and call-home are disabled; see [client compatibility](/compatibility/mcli/#subnet).

## Syntax {#syntax}

The current command is `mcli support top drive`; `disk` remains a compatibility alias. It displays current drive statistics.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays current drive metrics on the [alias](/glossary/#term-alias) `myminio`.

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
