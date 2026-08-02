---
title: "mc admin console"
url: "/reference/deprecated/mc-admin-console/"
weight: 130
minio_origin: true
silo_modified: false
---

<a id="mc-admin-console"></a>

<a id="command-mc.admin.console"></a>

{{% alert color="warning" %}}
**Important**

This command has been replaced by [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) in [mc RELEASE.2022-12-02T23-48-47Z](https://github.com/minio/mc/releases/tag/RELEASE.2022-12-02T23-48-47Z).

The command was previously replaced by `mc support logs show` in [mc RELEASE.2022-06-26T18-51-48Z](https://github.com/minio/mc/tree/RELEASE.2022-06-26T18-51-48Z).
{{% /alert %}}

## Description {#description}

The [`mc admin console`](#command-mc.admin.console) command returns server log entries for each MinIO server in the deployment.

{{% alert color="info" %}}
**Use `mc admin` on MinIO Deployments Only**

MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.
{{% /alert %}}

## Syntax {#syntax}

[`mc admin console`](#command-mc.admin.console) has the following syntax:

```shell
mc admin console [FLAGS] TARGET NODENAME
```

[`mc admin console`](#command-mc.admin.console) supports the following:

#### `TARGET` {#mc.admin.console.TARGET}

*mc-cmd*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment from which the command retrieves server logs.

#### `NODENAME` {#mc.admin.console.NODENAME}

*mc-cmd*

The specific MinIO server node from which the command retrieves server logs.

#### `--limit, l` {#mc.admin.console.-limit}

*mc-cmd*

The number of most recent log entries to show. Defaults to `10`.

#### `--type, t` {#mc.admin.console.-type}

*mc-cmd*

The type of errog logs to return. Specify one or more of the following options as a comma-seperated `,` list:

- `minio`
- `application`
- `all` (Default)
