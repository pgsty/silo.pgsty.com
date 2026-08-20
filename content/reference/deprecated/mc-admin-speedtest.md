---
title: "mc admin speedtest"
url: "/reference/deprecated/mc-admin-speedtest/"
weight: 180
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/deprecated/mc-admin-speedtest.rst
upstream_modified: false
---

<a id="mc-admin-speedtest"></a>

<a id="command-mc.admin.speedtest"></a>

> [!NOTE]
> **Changed: RELEASE.2022-07-24T02-25-13Z**
>
> `mc admin speedtest` replaced by [`mc support perf`](/reference/minio-mc/mc-support-perf/#command-mc.support.perf).

## Description {#description}

The [`mc admin speedtest`](#command-mc.admin.speedtest) command tests throughputs per host with `PUT` and `GET` operations.

[`speedtest`](#command-mc.admin.speedtest) is available starting with `mc` [RELEASE.2021-09-02T09-21-27Z](https://github.com/minio/mc/releases/tag/RELEASE.2021-09-02T09-21-27Z) and supports distributed MinIO deployments running [RELEASE.2021-07-30T00-02-00Z](https://github.com/minio/minio/releases/tag/RELEASE.2021-07-30T00-02-00Z) or later.

[`speedtest`](#command-mc.admin.speedtest) does not support standalone or MinIO Gateway deployments.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Syntax {#syntax}

[`mc admin speedtest`](#command-mc.admin.speedtest) has the following syntax:

```shell
mc admin speedtest [FLAGS] TARGET
```

[`mc admin speedtest`](#command-mc.admin.speedtest) supports the following arguments:

#### `TARGET` {#mc.admin.speedtest.TARGET}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment to run the speedtest against.

#### `--duration` {#mc.admin.speedtest.-duration}

*mc-cmd*

The duration the entire speedtests are run. Defaults to `10s`.

#### `--size` {#mc.admin.speedtest.-size}

*mc-cmd*

The size of the objects used for uploads/downloads. Defaults to `64MiB`.

#### `--concurrent` {#mc.admin.speedtest.-concurrent}

*mc-cmd*

The number of concurrent requests per server. Defaults to `32`.
