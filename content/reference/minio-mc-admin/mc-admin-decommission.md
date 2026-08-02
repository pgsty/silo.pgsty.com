---
title: "mc admin decommission"
url: "/reference/minio-mc-admin/mc-admin-decommission/"
weight: 50
minio_origin: true
silo_modified: false
---

<a id="mc-admin-decommission"></a>
<a id="minio-mc-admin-decommission"></a>

<a id="command-mc.admin.decommission"></a>

## Syntax {#syntax}

The [`mc admin decommission`](#command-mc.admin.decommission) command starts the decommissioning process for a MinIO [server pools](/operations/concepts/#minio-intro-server-pool). Decommissioning is designed for removing an older server pool whose hardware is no longer sufficient or performant compared to the pools in the deployment. MinIO automatically migrates data from the decommissioned pool to the remaining pools in the deployment based on the ratio of free space available in each pool.

See [Decommission Server Pools](/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning) for a complete procedure on decommissioning a server pool.

{{% alert color="info" %}}
**Decommissioning is Permanent**

Once MinIO begins decommissioning a pool, it marks that pool as *permanently* inactive (“draining”). Cancelling or otherwise interrupting the decommissioning procedure does **not** restore the pool to an active state.

Decommissioning is a major administrative operation that requires care in planning and execution, and is not a trivial or ‘daily’ task.

[MinIO SUBNET](https://min.io/pricing?jmp=docs) users can [log in](https://subnet.min.io/) and create a new issue related to decommissioning. Coordination with MinIO Engineering via SUBNET can ensure successful decommissioning, including performance testing and health diagnostics.

Community users can seek support on the [MinIO Community Slack](https://slack.min.io). Community Support is best-effort only and has no SLAs around responsiveness.
{{% /alert %}}

```shell
mc admin [GLOBALFLAGS] decommission start|status|cancel ALIAS TARGET
```

### Parameters {#parameters}

##### `start` {#mc.admin.decommission.start}

*mc-cmd*

*Required* Starts the decommissioning process for the server pool specified to [`TARGET`](#mc.admin.decommission.TARGET).

Requires specifying [`TARGET`](#mc.admin.decommission.TARGET)

##### `status` {#mc.admin.decommission.status}

*mc-cmd*

*Required* Returns the decommissioning status of all server pools on the specified [`ALIAS`](#mc.admin.decommission.ALIAS):

- **Active** - The pool is active and not scheduled for decommissioning.
- **Draining** - The pool is currently decommissioning.
- **Draining (Failed)** - The decommissioning process failed and requires manually restart.
- **Draining (Cancelled)** - The decommissioning process was manually cancelled.

If the command includes a [`TARGET`](#mc.admin.decommission.TARGET), the command output includes the rate of data migration *if* decommissioning is in progress.

##### `cancel` {#mc.admin.decommission.cancel}

*mc-cmd*

*Required* Cancels an ongoing decommissioning process on the pool specified to [`TARGET`](#mc.admin.decommission.TARGET).

Requires specifying [`TARGET`](#mc.admin.decommission.TARGET).

Cancelling a decommissioning process does not return the pool to an active state. You must eventually complete the decommissioning process and remove the pool from the deployment. You can resume the process by running [`mc admin decommission start`](#mc.admin.decommission.start) again against the pool.

##### `ALIAS` {#mc.admin.decommission.ALIAS}

*mc-cmd*

*Required* The [alias](/reference/minio-mc/mc-alias-set/#alias) of the MinIO deployment on which to start the decommissioning process.

##### `TARGET` {#mc.admin.decommission.TARGET}

*mc-cmd*

The full description of the server pool on which the command operates. For example:

```shell
https://minio-{01...04}.example.net:9000/mnt/disk{1...4}
```

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

See [Decommission Server Pools](/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning) for a complete procedure on decommissioning a server pool.
