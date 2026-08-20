---
title: "mc admin top"
url: "/reference/deprecated/mc-admin-top/"
weight: 200
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-admin-top.rst
upstream_modified: false
---

<a id="mc-admin-top"></a>

<a id="command-mc.admin.top"></a>

> [!NOTE]
> **Changed: RELEASE.2022-08-11T00-30-48Z**
>
> `mc admin top` replaced by [`mc support top`](/reference/minio-mc/mc-support-top/#command-mc.support.top).

## Description {#description}

The [`mc admin top`](#command-mc.admin.top) command returns statistics for distributed MinIO deployments, similar to the output of the `top` command.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Syntax {#syntax}

#### `mc admin top locks` {#mc.admin.top.locks}

*mc-cmd*

Returns the 10 oldest locks on the MinIO deployment.

The command has the following syntax:

```shell
mc admin top locks TARGET
```

The command supports the following arguments:

#### `TARGET` {#mc.admin.top.locks.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command retrieves statistics.

The alias *must* correspond to a distributed (multi-node) MinIO deployment. The command returns an error for [single-node single-drive](/glossary/#term-single-node-single-drive) deployments.
