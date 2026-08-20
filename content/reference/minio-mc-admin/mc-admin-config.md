---
title: "mc admin config"
url: "/reference/minio-mc-admin/mc-admin-config/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-config.rst
upstream_modified: false
---

<a id="mc-admin-config"></a>
<a id="minio-mc-admin-config"></a>

<a id="command-mc.admin.config"></a>

## Description {#description}

The [`mc admin config`](#command-mc.admin.config) command manages configuration settings for the [`minio`](/reference/minio-server/#command-minio) server.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Examples {#examples}

## Syntax {#syntax}

#### `mc admin config set` {#mc.admin.config.set}

*mc-cmd*

Sets a [configuration key](/reference/minio-server/settings/#minio-server-configuration-settings) on the MinIO deployment. Configurations defined by environment variables override configurations defined by this command.

#### `mc admin config get` {#mc.admin.config.get}

*mc-cmd*

Gets a [configuration key](/reference/minio-server/settings/#minio-server-configuration-settings) on the MinIO deployment created using *mc admin config set*.

#### `mc admin config export` {#mc.admin.config.export}

*mc-cmd*

Exports any configuration settings created using *mc admin config set*.

#### `mc admin config history` {#mc.admin.config.history}

*mc-cmd*

Lists the history of changes made to configuration keys by *mc admin config*.

Configurations defined by environment variables do not show.

#### `mc admin config import` {#mc.admin.config.import}

*mc-cmd*

Imports configuration settings exported using *mc admin config export*.

#### `mc admin config reset` {#mc.admin.config.reset}

*mc-cmd*

Resets config to defaults. Configurations defined in environment variables are not affected.

#### `mc admin config restore` {#mc.admin.config.restore}

*mc-cmd*

Roll back changes to configuration keys to a previous point in history.

Does not affect configurations defined by environment variables.

## Configuration Settings {#configuration-settings}

For a list of available configuration settings, see [Settings Overview](/reference/minio-server/settings/#minio-server-configuration-settings).
