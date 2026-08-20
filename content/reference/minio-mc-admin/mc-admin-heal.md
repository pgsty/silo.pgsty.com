---
title: "mc admin heal"
url: "/reference/minio-mc-admin/mc-admin-heal/"
weight: 70
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-heal.rst
upstream_modified: false
---

<a id="mc-admin-heal"></a>

<a id="command-mc.admin.heal"></a>

## Description {#description}

The [`mc admin heal`](#command-mc.admin.heal) command scans for objects that are damaged or corrupted and heals those objects.

[`mc admin heal`](#command-mc.admin.heal) is resource intensive and typically not required as a manual process, even after drive failures or corruption events.

As a part of normal operations, MinIO:

- automatically heals objects damaged by silent bit rot corruption, drive failure, or other issues on each `POST` or `GET` operation.
- performs periodic background object healing using the [scanner](/operations/concepts/scanner/#minio-concepts-scanner).
- aggressively heals objects after drive replacement.

Refer to [Object Healing](/operations/concepts/healing/#minio-concepts-healing) for more details on how MinIO heals objects.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Syntax {#syntax}

[`mc admin heal`](#command-mc.admin.heal) has the following syntax:

```shell
mc admin heal [FLAGS] TARGET             \
                      [--all-drives, -a] \
                      [--force]          \
                      [--verbose, -v]
```

[`mc admin heal`](#command-mc.admin.heal) supports the following arguments:

#### `TARGET` {#mc.admin.heal.TARGET}

*mc-cmd*

*Required*

The full path to the bucket or bucket prefix on which the command should perform object healing. Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment as the prefix for the path. For example:

```shell
mc admin heal play/mybucket/myprefix
```

If the `TARGET` bucket or bucket prefix has an active healing scan, the command returns the status of that scan.

#### `--all-drives, -a` {#mc.admin.heal.-all-drives}

*mc-cmd*

*Optional*

Select all drives and show verbose information.

#### `--force` {#mc.admin.heal.-force}

*mc-cmd*

*Optional*

Disables warning prompts.

#### `--verbose, -v` {#mc.admin.heal.-verbose}

*mc-cmd*

*Optional*

Show information about offline and faulty healing drives.

<a id="minio-concepts-healing-colors"></a>

## Healing Colors {#healing-colors}

Some versions of MinIO used a color key as a way to differentiate objects with different healing statuses.

> [!NOTE]
> **Changed: mc**
>
> RELEASE.2024-11-17T19-35-25Z

The color meaning has been updated.

- Green indicates the bucket is healthy.
- Yellow indicates the bucket requires healing on one or more drives.
- Red indicates one or more drives are unhealthy.
- Grey indicates an indeterminate healing state.
