---
title: "mc support top net"
url: "/reference/minio-mc/mc-support-top-net/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-top-net.rst
upstream_modified: false
---

<a id="mc-support-top-net"></a>

<a id="command-mc.support.top.net"></a>

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Syntax {#syntax}

The [`mc support top net`](#command-mc.support.top.net) command displays realtime network metrics.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command displays the current realtime network metrics for the [alias](/glossary/#term-alias) `myminio` deployment.

```shell
mc support top net myminio/
```

The output returns information such as the server URL, network interface, receive rate, transmit rate, and system messages.
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] support top disk                \
                             [--interval value]  \
                             TARGET
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `TARGET` {#mc.support.top.net.TARGET}

*mc-cmd*

*Required*

The full path to the [alias](/reference/minio-mc/mc-alias-set/#minio-mc-alias) or [prefix](/glossary/#term-prefix) where the command should run.

##### `--interval` {#mc.support.top.net.-interval}

*mc-cmd*

*Optional*

The interval in seconds between metric requests.

By default, the command requests metrics every second.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
