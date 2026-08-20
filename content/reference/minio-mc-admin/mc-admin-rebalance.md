---
title: "mc admin rebalance"
url: "/reference/minio-mc-admin/mc-admin-rebalance/"
weight: 130
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-rebalance.rst
upstream_modified: false
---

<a id="mc-admin-rebalance"></a>
<a id="minio-mc-admin-rebalance"></a>

<a id="command-mc.admin.rebalance"></a>

## Permission {#permission}

This command requires that the user performing it have the [`admin:Rebalance`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-Rebalance) [policy action](/administration/identity-access-management/policy-based-access-control/#minio-policy) for the deployment.

## Description {#description}

The [`mc admin rebalance`](#command-mc.admin.rebalance) command allows starts, monitors, or stops a rebalancing operation on a MinIO deployment. Rebalancing redistributes objects across all pools in the deployment.

MinIO does not automatically rebalance objects when adding a new server pool. Instead, MinIO [writes new objects](/operations/deployments/baremetal-expand-minio-deployment/#minio-writing-files) to the pool with relatively more free space compared to the other available pools on the deployment. Triggering a manual rebalancing procedure prompts MinIO to scan the entire deployment and move objects as necessary to achieve a similar available free space across all pools.

This is an expensive and time consuming operation. Consider only running a rebalance procedure during light or no use of the deployment. If write operations do occur during a rebalance operation, they process in parallel and write to a pool not actively in rebalancing.

You can stop a rebalance and start it again later as needed.

Follow the progress of an ongoing rebalance operation using the following command:

```shell
mc admin trace --call rebalance ALIAS
```

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

The [`mc admin rebalance`](#command-mc.admin.rebalance) command has the following subcommands:

| Subcommand | Description |
| --- | --- |
| [`mc admin rebalance start`](#mc.admin.rebalance.start) | Starts a rebalance operation on a MinIO deployment. |
| [`mc admin rebalance status`](#mc.admin.rebalance.status) | Outputs the current status of an in-progress rebalance operation. |
| [`mc admin rebalance stop`](#mc.admin.rebalance.stop) | Stops an in-progress rebalance operation. |

## Syntax {#syntax}

#### `mc admin rebalance start` {#mc.admin.rebalance.start}

*mc-cmd*

Start a rebalance operation for a MinIO deployment.

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
Consider a MinIO deployment with two pools with an assigned alias of `minio1`. One pool has 250 GB of free space while the other pool has 3 TB of free space.

The [`mc admin rebalance`](#command-mc.admin.rebalance) command shifts objects from the pool with less free space to the pool with more free space so that there is roughly equal free space on both pools.

```shell
mc admin rebalance start minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin rebalance start ALIAS
```

- Replace ALIAS with the [alias](/reference/minio-mc/mc-alias-set/#alias) of a MinIO deployment to rebalance.
{{< /tab >}}
{{< /tabs >}}

#### `mc admin rebalance status` {#mc.admin.rebalance.status}

*mc-cmd*

Queries the deployment with an active rebalance process and returns information about the status of the rebalance process.

The status returns the ID of the rebalance operation, the time of the operation, and details for each pool on the deployment. For each pool, the status shows the pool ID, the pool’s rebalance status, the percentage of used space, and rebalance progress for the pool.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
```shell
mc admin rebalance status minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin rebalance ALIAS
```

- Replace ALIAS with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
{{< /tab >}}
{{< /tabs >}}

#### `mc admin rebalance stop` {#mc.admin.rebalance.stop}

*mc-cmd*

Ends an in-progress rebalance job on the specified deployment.

{{< tabs group="examples-syntax" >}}
{{< tab label="EXAMPLES" value="examples" >}}
```shell
mc admin rebalance stop minio1
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin rebalance stop ALIAS
```

- Replace ALIAS with the [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment.
{{< /tab >}}
{{< /tabs >}}

## Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Behavior {#behavior}

### Back Up Cluster Settings First {#back-up-cluster-settings-first}

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations respectively prior to starting decommissioning. You can use these snapshots to restore bucket/IAM settings to recover from user or process errors as necessary.

### Rebalancing Ignores Expired Objects and Trailing `DeleteMarker` {#rebalancing-ignores-expired-objects-and-trailing-deletemarker}

Starting with [RELEASE.2023-06-23T20-26-00Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-06-23T20-26-00Z), rebalancing ignores object versions which have expired based on the configured [lifecycle rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) for the parent bucket.

Rebalancing also ignores objects where the only remaining version is a [delete marker](/administration/object-management/object-versioning/#minio-bucket-versioning-delete). This avoids inter-pool <abbr title="Input/Output">I/O</abbr> for objects already considered fully deleted.

MinIO relies on the [scanner](/operations/concepts/scanner/#minio-concepts-scanner) to capture and remove those expired objects or trailing `DeleteMarker` objects.
