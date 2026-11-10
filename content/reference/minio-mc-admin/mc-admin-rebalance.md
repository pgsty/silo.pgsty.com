---
title: "mc admin rebalance"
url: "/reference/minio-mc-admin/mc-admin-rebalance/"
weight: 130
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-rebalance.rst
upstream_modified: true
---

<a id="mc-admin-rebalance"></a>
<a id="minio-mc-admin-rebalance"></a>

<a id="command-mc.admin.rebalance"></a>

## Permission {#permission}

This command requires that the user performing it have the [`admin:Rebalance`](/administration/identity-access-management/policy-based-access-control/#policy-action.admin-Rebalance) [policy action](/administration/identity-access-management/policy-based-access-control/#minio-policy) for the deployment.

## Description {#description}

The [`mc admin rebalance`](#command-mc.admin.rebalance) command starts, monitors, or stops a rebalancing operation on a MinIO deployment. Rebalancing redistributes objects across all pools in the deployment.

MinIO does not automatically rebalance objects when adding a new server pool. Instead, MinIO [writes new objects](/operations/deployments/baremetal-expand-minio-deployment/#minio-writing-files) to the pool with relatively more free space compared to the other available pools on the deployment. Triggering a manual rebalancing procedure prompts MinIO to scan the entire deployment and move objects as necessary to achieve a similar available free space across all pools.

This is an expensive and time consuming operation. Consider only running a rebalance procedure during light or no use of the deployment. If write operations do occur during a rebalance operation, they process in parallel and write to a pool not actively in rebalancing.

You can stop a rebalance and start it again later as needed.

Follow the progress of an ongoing rebalance operation using the following command:

```shell
mc admin trace --call rebalance ALIAS
```

> [!NOTE]
> **Server compatibility**
>
> The supported server for [`mcli admin`](/reference/minio-mc-admin/#command-mc.admin) is SILO. Compatibility with unmodified upstream MinIO is best effort; general S3 compatibility alone does not provide these administrative APIs.

The [`mc admin rebalance`](#command-mc.admin.rebalance) command has the following subcommands:

| Subcommand                                                | Description                                                       |
| --------------------------------------------------------- | ----------------------------------------------------------------- |
| [`mc admin rebalance start`](#mc.admin.rebalance.start)   | Starts a rebalance operation on a MinIO deployment.               |
| [`mc admin rebalance status`](#mc.admin.rebalance.status) | Outputs the current status of an in-progress rebalance operation. |
| [`mc admin rebalance stop`](#mc.admin.rebalance.stop)     | Stops an in-progress rebalance operation.                         |
{.wide .expand}

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

Ends an in-progress rebalance job on the specified deployment. In [SILO 20261109](/blog/release/silo-20261109/), `mc admin rebalance stop` returns cleanly instead of panicking when rebalance metadata is absent ([#270](https://github.com/pgsty/silo/issues/270)).

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

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations before starting a rebalance operation. You can use these snapshots to restore bucket or IAM settings to recover from user or process errors.

<a id="rebalancing-ignores-expired-objects-and-trailing-deletemarker"></a>

### Delete Markers, Expired Versions, and Multi-Pool Migration {#rebalance-multi-pool-safety}

SILO rebalance does **not** drop delete markers or silently skip versions whose lifecycle state is uncertain across pools. Preserving delete markers and unconfirmed versions prevents older object versions in other pools from reappearing during or after migration.

In [SILO 20261109](/blog/release/silo-20261109/) (`RELEASE.2026-11-09T00-00-00Z`), rebalancing enforces the following guarantees:

- Preserves `null` and UUID [delete markers](/administration/object-management/object-versioning/#minio-bucket-versioning-delete) across pools instead of dropping them.
- Moves objects whose copies use mixed erasure layouts across pools ([#261](https://github.com/pgsty/silo/issues/261)), ILM-expired current versions ([#265](https://github.com/pgsty/silo/issues/265)), and versions whose cross-pool [lifecycle](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) expiry is refused because authoritative quorum or lock state cannot be confirmed ([#278](https://github.com/pgsty/silo/issues/278)).
- Continues rebalancing across remaining buckets when an individual bucket fails, while preserving cancellation ([#307](https://github.com/pgsty/silo/issues/307)).
- Handles `mc admin rebalance stop` safely without panicking when no rebalance metadata exists ([#270](https://github.com/pgsty/silo/issues/270)).
