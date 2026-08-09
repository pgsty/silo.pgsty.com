---
title: "mc admin info"
url: "/reference/minio-mc-admin/mc-admin-info/"
weight: 80
minio_origin: true
silo_modified: false
---

<a id="mc-admin-info"></a>

<a id="command-mc.admin.info"></a>

## Description {#description}

The [`mc admin info`](#command-mc.admin.info) command displays information on a MinIO server. For distributed MinIO deployments, [`mc admin info`](#command-mc.admin.info) displays information for each MinIO server in the deployment.

{{% alert color="info" %}}
**Added: mc**

RELEASE.2024-05-03T11-21-07Z

The command output includes information about the [erasure code](/operations/concepts/erasure-coding/#minio-ec-erasure-set) setting for the cluster. This displays in the output in the format `EC:#`.
{{% /alert %}}

The output of the command resembles the following:

```text
●  play.min.io
   Uptime: 2 hours
   Version: 2024-05-10T08:24:14Z
   Network: 1/1 OK
   Drives: 4/4 OK
   Pool: 1

Pools:
   1st, Erasure sets: 1, Drives per erasure set: 4

0 B Used, 3 Buckets, 0 Objects
4 drives online, 0 drives offline, EC:1
```

## Examples {#examples}

The following example assumes that the `play` alias exists in the [`mc`](/reference/minio-mc/#command-mc) [configuration file](/reference/minio-mc/#mc-configuration). You can replace `play` with the alias for your preferred S3-compatible deployment.

See [`mc alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for more information on aliases.

```shell
mc admin info play
```

## Syntax {#syntax}

[`mc admin info`](#command-mc.admin.info) has the following syntax:

```shell
mc admin info TARGET      \
              [--offline]
```

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment as the `TARGET`.

### Parameters {#parameters}

##### `TARGET` {#mc.admin.info.TARGET}

*mc-cmd*

*Required*

The [alias](/reference/minio-mc/mc-alias-set/#alias) about which you want to display information.

##### `--offline` {#mc.admin.info.-offline}

*mc-cmd*

*Optional*

Show only offline drives or nodes.
