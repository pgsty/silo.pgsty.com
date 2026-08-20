---
title: "mc support top"
url: "/reference/minio-mc/mc-support-top/"
weight: 70
icon: fa-solid fa-ranking-star
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc/mc-support-top.rst
upstream_modified: false
---

<a id="mc-support-top"></a>

<a id="command-mc.support.top"></a>

> [!NOTE]
> **Note**
>
> > [!NOTE]
> > **Changed: RELEASE.2022-08-11T00-30-48Z**
>
> `mc support top` replaces the `mc admin top` command.

> [!NOTE]
> **SUBNET Registration Required**
>
> The `mc support` commands are designed for MinIO deployments registered with [MinIO SUBNET](https://min.io/pricing?jmp=docs) to ensure optimal outcome of diagnostics and performance testing. Deployments not registered with SUBNET cannot use the `mc support` commands.

## Description {#description}

The [`mc support top`](#command-mc.support.top) command returns statistics for distributed MinIO deployments, similar to the output of the `top` command in a shell.

> [!NOTE]
> **Note**
>
> [`mc support top`](#command-mc.support.top) is not supported on single-node single-drive MinIO deployments.

[`mc support top`](#command-mc.support.top) has the following subcommands:

- [`api`](/reference/minio-mc/mc-support-top-api/#command-mc.support.top.api)
- [`locks`](/reference/minio-mc/mc-support-top-locks/#command-mc.support.top.locks)
- [`disk`](/reference/minio-mc/mc-support-top-disk/#command-mc.support.top.disk)
- [`net`](/reference/minio-mc/mc-support-top-net/#command-mc.support.top.net)
- [`rpc`](/reference/minio-mc/mc-support-top-rpc/#command-mc.support.top.rpc)

Refer to the pages linked above for each subcommand for details.

## Syntax {#syntax}

The command has the following syntax:

```shell
mc support top COMMAND [COMMAND FLAGS] [ARGUMENTS ...]
```
