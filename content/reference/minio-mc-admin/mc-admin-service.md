---
title: "mc admin service"
url: "/reference/minio-mc-admin/mc-admin-service/"
weight: 160
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-service.rst
upstream_modified: false
---

<a id="mc-admin-service"></a>

<a id="command-mc.admin.service"></a>

## Description {#description}

The [`mc admin service`](#command-mc.admin.service) command can restart or unfreeze MinIO servers.

[`mc admin service`](#command-mc.admin.service) affects *all* MinIO servers in the target deployment at the same time. The command interrupts in-progress API operations on the MinIO deployment. Use caution when issuing this command to a deployment.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Examples {#examples}

### Restart MinIO Servers in Target Deployment {#restart-minio-servers-in-target-deployment}

The following example uses the default `myminio` alias. The `myminio` alias points to a local `minio` server running on port `9000`. See &lt;installation instructions&gt; for more information on installing and running a local `minio` server instance.

See [`mc alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for more information on aliases.

```shell
mc admin service restart myminio
```

### Resume S3 Calls on a Target Deployment {#resume-s3-calls-on-a-target-deployment}

The following example uses the default `myminio` alias. The `myminio` alias points to a local `minio` server running on port `9000`. See &lt;installation instructions&gt; for more information on installing and running a local `minio` server instance.

See [`mc alias`](/reference/minio-mc/mc-alias/#command-mc.alias) for more information on aliases.

```shell
mc admin service unfreeze myminio
```

## Syntax {#syntax}

[`mc admin service`](#command-mc.admin.service) has the following syntax:

```shell
mc admin service COMMAND [ARGUMENTS]
```

[`mc admin service`](#command-mc.admin.service) supports the following commands:

#### `restart` {#mc.admin.service.restart}

*mc-cmd*

Restarts MinIO servers. If needed, the command may suggest restarting the node based on the status.

[`mc admin service restart`](#mc.admin.service.restart) has the following syntax:

```shell
mc admin service restart ALIAS
```

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment. [`restart`](#mc.admin.service.restart) restarts *all* MinIO servers in the deployment.

#### `unfreeze` {#mc.admin.service.unfreeze}

*mc-cmd*

Restart S3 API calls on a MinIO cluster.

[`mc admin service unfreeze`](#mc.admin.service.unfreeze) has the following syntax:

```shell
mc admin service unfreeze ALIAS
```

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment.
