---
title: "Decommission Server Pools"
url: "/operations/deployments/baremetal-decommission-server-pool/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="decommission-server-pools"></a>
<a id="minio-decommissioning"></a>

MinIO supports decommissioning and removing [server pools](/operations/concepts/#minio-intro-server-pool) from a deployment with two or more pools. To decommission, there must be at least one remaining pool with sufficient available space to receive the objects from the decommissioned pools.

Starting with `RELEASE.2023-01-18T04-36-38Z`, MinIO supports queueing [multiple pools](#minio-decommission-multiple-pools) in a single decommission command. Each listed pool immediately enters a read-only status, but draining occurs one pool at a time.

Decommissioning is designed for removing an older server pool whose hardware is no longer sufficient or performant compared to the pools in the deployment. MinIO automatically migrates data from the decommissioned pools to the remaining pools in the deployment based on the ratio of free space available in each pool.

During the decommissioning process, MinIO routes read operations (e.g. `GET`, `LIST`, `HEAD`) normally. MinIO routes write operations (e.g. `PUT`, versioned `DELETE`) to the remaining “active” pools in the deployment. Versioned objects maintain their ordering throughout the migration process.

The procedures on this page decommission and remove one or more server pools from a [distributed](/operations/deployments/installation/#deploy-minio-distributed) MinIO deployment with *at least* two server pools.

{{% alert color="info" %}}
**Decommissioning is Permanent**

Once MinIO begins decommissioning a pool, it marks that pool as *permanently* inactive (“draining”). Cancelling or otherwise interrupting the decommissioning procedure does **not** restore the pool to an active state. Use extra caution when decommissioning multiple pools.

Decommissioning is a major administrative operation that requires care in planning and execution, and is not a trivial or ‘daily’ task.

[MinIO SUBNET](https://min.io/pricing?jmp=docs) users can [log in](https://subnet.min.io/) and create a new issue related to decommissioning. Coordination with MinIO Engineering via SUBNET can ensure successful decommissioning, including performance testing and health diagnostics.

Community users can seek support on the [MinIO Community Slack](https://slack.min.io). Community Support is best-effort only and has no SLAs around responsiveness.
{{% /alert %}}

<a id="minio-decommissioning-prereqs"></a>

## Prerequisites {#prerequisites}

### Back Up Cluster Settings First {#back-up-cluster-settings-first}

Use the [`mc admin cluster bucket export`](/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) and [`mc admin cluster iam export`](/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) commands to take a snapshot of the bucket metadata and IAM configurations respectively prior to starting decommissioning. You can use these snapshots to restore bucket/IAM settings to recover from user or process errors as necessary.

### Networking and Firewalls {#networking-and-firewalls}

Each node should have full bidirectional network access to every other node in the deployment. For containerized or orchestrated infrastructures, this may require specific configuration of networking and routing components such as ingress or load balancers. Certain operating systems may also require setting firewall rules. For example, the following command explicitly opens the default MinIO server API port `9000` on servers using `firewalld`:

```shell
firewall-cmd --permanent --zone=public --add-port=9000/tcp
firewall-cmd --reload
```

If you set a static [MinIO Console](/administration/minio-console/#minio-console) port (e.g. `:9001`) you must *also* grant access to that port to ensure connectivity from external clients.

MinIO **strongly recomends** using a load balancer to manage connectivity to the cluster. The Load Balancer should use a “Least Connections” algorithm for routing requests to the MinIO deployment, since any MinIO node in the deployment can receive, route, or process client requests.

The following load balancers are known to work well with MinIO:

- [NGINX](https://www.nginx.com/products/nginx/load-balancing/)
- [HAProxy](https://cbonte.github.io/haproxy-dconv/2.3/intro.html#3.3.5)

Configuring firewalls or load balancers to support MinIO is out of scope for this procedure.

### Deployment Must Have Sufficient Storage {#deployment-must-have-sufficient-storage}

The decommissioning process migrates objects from the target pool to other pools in the deployment. The total available storage on the deployment *must* exceed the total storage of the decommissioned pool.

Use the [Erasure Code Calculator](https://min.io/product/erasure-code-calculator) to determine the usable storage capacity. Then reduce that by the size of the objects already on the deployment.

For example, consider a deployment with the following distribution of used and free storage:

<table>
  <tbody>
    <tr>
      <td><p>Pool 1</p></td>
      <td><p>100TB Used</p></td>
      <td><p>200TB Total</p></td>
    </tr>
    <tr>
      <td><p>Pool 2</p></td>
      <td><p>100TB Used</p></td>
      <td><p>200TB Total</p></td>
    </tr>
    <tr>
      <td><p>Pool 3</p></td>
      <td><p>100TB Used</p></td>
      <td><p>200TB Total</p></td>
    </tr>
  </tbody>
</table>

Decommissioning Pool 1 requires distributing the 100TB of used storage across the remaining pools. Pool 2 and Pool 3 each have 100TB of unused storage space and can safely absorb the data stored on Pool 1.

However, if Pool 1 were full (e.g. 200TB of used space), decommissioning would completely fill the remaining pools and potentially prevent any further write operations.

## Considerations {#considerations}

### Replacing a Server Pool {#replacing-a-server-pool}

For hardware upgrade cycles where you replace old pool hardware with a new pool, you should [add the new pool through expansion](/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed) before starting the decommissioning of the old pool. Adding the new pool first allows the decommission process to transfer objects in a balanced way across all available pools, both existing and new.

Complete any planned [hardware expansion](/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed) prior to decommissioning older hardware pools.

Decommissioning requires that a cluster’s topology remain stable throughout the pool draining process. Do **not** attempt to perform expansion and decommission changes in a single step.

### Decommissioning is Resumable {#decommissioning-is-resumable}

MinIO resumes decommissioning if interrupted by transient issues such as deployment restarts or network failures.

For manually cancelled or failed decommissioning attempts, MinIO resumes only after you manually re-initiate the decommissioning operation.

The pool remains in the decommissioning state *regardless* of the interruption. A pool can *never* return to active status after decommissioning begins.

### Decommissioning is Non-Disruptive {#decommissioning-is-non-disruptive}

Removing a decommissioned server pool requires restarting *all* MinIO nodes in the deployment at around the same time.

MinIO strongly recommends restarting all MinIO Server processes in a deployment simultaneously. MinIO operations are atomic and strictly consistent. As such the restart procedure is non-disruptive to applications and ongoing operations.

Do **not** perform “rolling” (e.g. one node at a time) restarts.

### Decommissioning Ignores Expired Objects and Trailing `DeleteMarker` {#decommissioning-ignores-expired-objects-and-trailing-deletemarker}

Starting with [RELEASE.2023-05-27T05-56-19Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-05-27T05-56-19Z), decommissioning ignores objects where the only remaining version is a `DeleteMarker`. This avoids creating empty metadata on the remaining server pool(s) for objects that are effectively fully deleted.

Starting with [RELEASE.2023-06-23T20-26-00Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-06-23T20-26-00Z), decommissioning also ignores object versions which have expired based on the configured [lifecycle rules](/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration) for the parent bucket. Starting with [RELEASE.2023-06-29T05-12-28Z](https://github.com/minio/minio/releases/tag/RELEASE.2023-06-29T05-12-28Z), you can monitor ignored delete markers and expired objects during the decommission process with [`mc admin trace --call decommission`](/reference/minio-mc-admin/mc-admin-trace/#mc.admin.trace.-call).

Once the decommissioning process completes, you can safely shut down that pool. Since the only remaining data was scheduled for deletion *or* was only a `DeleteMarker`, you can safely clear or destroy those drives as per your internal procedures.

## Behavior {#behavior}

### Final Listing Check {#final-listing-check}

At the end of the decommission process, MinIO checks for a list of items on the pool. If the list returns empty, MinIO marks the decommission as successfully completed. If any objects return, MinIO returns an error that the decommission process failed.

If the decommission fails, customers should open a [MinIO SUBNET](https://min.io/pricing?jmp=docs) issue for further assistance before retrying the decommission. Community users without a SUBNET subscription can retry the decommission process or seek additional support through the [MinIO Community Slack](https://slack.min.io/). MinIO provides Community Support at best-effort only and provides no <abbr title="Service Level Agreement">SLA</abbr> around responsiveness.

### Decommissioning a Server with Tiering Enabled {#decommissioning-a-server-with-tiering-enabled}

{{% alert color="info" %}}
**Changed: RELEASE.2023-03-20T20-16-18Z**

{{% /alert %}}

For deployments with tiering enabled and active, decommissioning moves the object references to a new active pool. Applications can continue issuing GET requests against those objects where MinIO handles transparently retrieving them from the remote tier.

In older MinIO versions, tiering configurations prevent decommissioning.

<a id="minio-decommissioning-server-pool"></a>

## Decommission a Server Pool {#decommission-a-server-pool}

### 1) Review the MinIO Deployment Topology {#review-the-minio-deployment-topology}

The [`mc admin decommission`](/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission) command returns a list of all pools in the MinIO deployment:

```shell
mc admin decommission status myminio
```

The command returns output similar to the following:

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Active │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  60 TiB (used) / 100 TiB (total) │ Active │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 100 TiB (total) │ Active │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴────────┘
```

The example deployment above has three pools. Each pool has four servers with four drives each.

Identify the target pool for decommissioning and review the current capacity. The remaining pools in the deployment *must* have sufficient total capacity to migrate all object stored in the decommissioned pool.

In the example above, the deployment has 210TiB total storage with 110TiB used. The first pool (`minio-{01...04}`) is the decommissioning target, as it was provisioned when the MinIO deployment was created and is completely full. The remaining newer pools can absorb all objects stored on the first pool without significantly impacting total available storage.

### 2) Start the Decommissioning Process {#start-the-decommissioning-process}

{{% alert color="info" %}}
**Decommissioning is Permanent**

Once MinIO begins decommissioning a pool, it marks that pool as *permanently* inactive (“draining”). Cancelling or otherwise interrupting the decommissioning procedure does **not** restore the pool to an active state.

Review and validate that you are decommissioning the correct pool *before* running the following command.
{{% /alert %}}

Use the [`mc admin decommission start`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) command to begin decommissioning the target pool. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment and the full description of the pool to decommission, including all hosts, disks, and file paths.

```shell
mc admin decommission start myminio/ https://minio-{01...04}.example.net:9000/mnt/disk{1...4}/minio
```

The example command begins decommissioning the matching server pool on the `myminio` deployment.

During the decommissioning process, MinIO continues routing read operations (`GET`, `LIST`, `HEAD`) to the pool for those objects not yet migrated. MinIO routes all new write operations (`PUT`) to the remaining pools in the deployment.

Load balancers, reverse proxy, or other network control components which manage connections to the deployment do not need to modify their configurations at this time.

### 3) Monitor the Decommissioning Process {#monitor-the-decommissioning-process}

Use the [`mc admin decommission status`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) command to monitor the decommissioning process.

```shell
mc admin decommission status myminio
```

The command returns output similar to the following:

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬──────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status   │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Draining │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  60 TiB (used) / 100 TiB (total) │ Active   │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 100 TiB (total) │ Active   │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴──────────┘
```

You can retrieve more detailed information by specifying the description of the server pool to the command:

```shell
mc admin decommission status myminio https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio
```

The command returns output similar to the following:

```shell
Decommissioning rate at 100MiB/sec [1TiB/10TiB]
Started: 30 minutes ago
```

[`mc admin decommission status`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) marks the **Status** as **Complete** once decommissioning is completed. You can move on to the next step once decommissioning is completed.

If **Status** reads as failed, you can re-run the [`mc admin decommission start`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) command to resume the process. For persistent failures, use [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) or review the `systemd` logs (e.g. `journalctl -u minio`) to identify more specific errors.

### 4) Remove the Decommissioned Pool from the Deployment Configuration {#remove-the-decommissioned-pool-from-the-deployment-configuration}

As each pool completes decommissioning, you can safely remove it from the deployment configuration. Modify the startup command for each remaining MinIO server in the deployment and remove the decommissioned pool.

The `.deb` or `.rpm` packages install a [systemd](https://www.freedesktop.org/wiki/Software/systemd/) service file to `/lib/systemd/system/minio.service`. For binary installations, this procedure assumes the file was created manually as per the [Installation and Management](/operations/deployments/installation/#deploy-minio-distributed) procedure.

The `minio.service` file uses an environment file located at `/etc/default/minio` for sourcing configuration settings, including the startup. Specifically, the `MINIO_VOLUMES` variable sets the startup command:

```shell
cat /etc/default/minio | grep "MINIO_VOLUMES"
```

The command returns output similar to the following:

```shell
MINIO_VOLUMES="https://minio-{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio-{5...8}.example.net:9000/mnt/disk{1...4}/minio https://minio-{9...12}.example.net:9000/mnt/disk{1...4}/minio"
```

Edit the environment file and remove the decommissioned pool from the `MINIO_VOLUMES` value.

### 5) Update Network Control Plane {#update-network-control-plane}

Update any load balancers, reverse proxies, or other network control planes to remove the decommissioned server pool from the connection configuration for the MinIO deployment.

Specific instructions for configuring network control plane components is out of scope for this procedure.

### 6) Restart the MinIO Deployment {#restart-the-minio-deployment}

Issue the following commands on each node **simultaneously** in the deployment to restart the MinIO service:

```shell
sudo systemctl restart minio.service
```

Use the following commands to confirm the service is online and functional:

```shell
sudo systemctl status minio.service
journalctl -f -u minio.service
```

MinIO may log an increased number of non-critical warnings while the server processes connect and synchronize. These warnings are typically transient and should resolve as the deployment comes online.

MinIO strongly recommends restarting all MinIO Server processes in a deployment simultaneously. MinIO operations are atomic and strictly consistent. As such the restart procedure is non-disruptive to applications and ongoing operations.

Do **not** perform “rolling” (e.g. one node at a time) restarts.

Once the deployment is online, use [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) to confirm the uptime of all remaining servers in the deployment.

<a id="minio-decommission-multiple-pools"></a>

## Decommission Multiple Server Pools {#decommission-multiple-server-pools}

{{% alert color="info" %}}
**Changed: RELEASE.2023-01-18T04-36-38Z**

{{% /alert %}}

You can start the decommission process for multiple server pools when issuing a decommission command.

After entering the command:

- MinIO immediately stops write access to all pools to be decommissioned.
- Decommissioning happens one pool at a time.
- Each pool completes the decommission draining process before MinIO begins draining the next pool.

To decommission multiple server pools from one command, add the full description of each server pool to decommission as a comma-separated list.

All other considerations about decommissioning apply when performing the process on multiple servers.

- Decommissioning is permanent.
- Once you mark the pools as decommissioned, you **cannot** restore them.
- Confirm you select the intended pools.

### 1) Review the MinIO Deployment Topology {#id1}

The [`mc admin decommission`](/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission) command returns a list of all pools in the MinIO deployment:

```shell
mc admin decommission status myminio
```

The command returns output similar to the following:

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Active │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  95 TiB (used) / 100 TiB (total) │ Active │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 500 TiB (total) │ Active │
│ 4th │ https://minio-{13...16}.example.com:9000/mnt/disk{1...4}/minio │  0  TiB (used) / 500 TiB (total) │ Active │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴────────┘
```

The example deployment above has three pools. Each pool has four servers with four drives each.

Identify the target pool for decommissioning and review the current capacity. The remaining pools in the deployment *must* have sufficient total capacity to migrate all object stored in the decommissioned pool.

In the example above, the deployment has 1110TiB total storage with 145TiB used.

- The first pool (`minio-{01...04}`) is the first decommissioning target, as it was provisioned when the MinIO deployment was created and is completely full.
- The second pool (`minio-{05...08}`) is the second decommissioning target, as it was also provisioned when the MinIO deployment was created and is nearly full.
- The fourth pool (`minio-{13...16}`) is a newly added pool with new hardware from a completed server expansion.

The third and fourth pools can absorb all objects stored on the first pool without significantly impacting total available storage.

{{% alert color="warning" %}}
**Important**

Complete any server expansion to add new storage resources *before* beginning a decommission process.
{{% /alert %}}

### 2) Start the Decommissioning Process {#id2}

{{% alert color="info" %}}
**Decommissioning is Permanent**

Once MinIO begins decommissioning the pools, it marks those pools as *permanently* inactive (“draining”). Cancelling or otherwise interrupting the decommissioning procedure does **not** restore the pools to an active state.

Review and validate that you are decommissioning the correct pools *before* running the following command.
{{% /alert %}}

Use the [`mc admin decommission start`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) command to begin decommissioning the target pool. Specify the [alias](/reference/minio-mc/mc-alias-set/#alias) of the deployment and a comma-separated list of the full description of each pool to decommission, including all hosts, disks, and file paths.

```shell
mc admin decommission start myminio/ https://minio-{01...04}.example.net:9000/mnt/disk{1...4}/minio,https://minio-{05...08}.example.net:9000/mnt/disk{1...4}/minio
```

The example command begins decommissioning the two listed matching server pools on the `myminio` deployment.

During the decommissioning process, MinIO continues routing read operations (`GET`, `LIST`, `HEAD`) operations to the pools for those objects not yet migrated. MinIO routes all new write operations (`PUT`) to the remaining pools in the deployment not scheduled for decommissioning.

Draining of decommissioned pools happens one pool at a time, completing the decommission of each pool in sequence. Draining does *not* happen concurrently for all decommissioning pools.

Load balancers, reverse proxy, or other network control components which manage connections to the deployment do not need to modify their configurations at this time.

### 3) Monitor the Decommissioning Process {#id3}

Use the [`mc admin decommission status`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) command to monitor the decommissioning process.

```shell
mc admin decommission status myminio
```

The command returns output similar to the following:

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬──────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status   │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Draining │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  95 TiB (used) / 100 TiB (total) │ Pending  │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 500 TiB (total) │ Active   │
│ 4th │ https://minio-{13...16}.example.com:9000/mnt/disk{1...4}/minio │  0  TiB (used) / 500 TiB (total) │ Active   │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴──────────┘
```

You can retrieve more detailed information by specifying the description of the server pool to the command:

```shell
mc admin decommission status myminio https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio
```

The command returns output similar to the following:

```shell
Decommissioning rate at 100MiB/sec [1TiB/10TiB]
Started: 30 minutes ago
```

[`mc admin decommission status`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) marks the **Status** as **Complete** once decommissioning is completed. You can move on to the next step once MinIO completes decommissioning for all pools.

If **Status** reads as failed, you can re-run the [`mc admin decommission start`](/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) command to resume the process. For persistent failures, use [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) or review the `systemd` logs (e.g. `journalctl -u minio`) to identify more specific errors.

### 4) Remove the Decommissioned Pools from the Deployment Configuration {#remove-the-decommissioned-pools-from-the-deployment-configuration}

Once decommissioning completes, you can safely remove the pools from the deployment configuration. Modify the startup command for each remaining MinIO server in the deployment and remove the decommissioned pool.

The `.deb` or `.rpm` packages install a [systemd](https://www.freedesktop.org/wiki/Software/systemd/) service file to `/lib/systemd/system/minio.service`. For binary installations, this procedure assumes the file was created manually as per the [Installation and Management](/operations/deployments/installation/#deploy-minio-distributed) procedure.

The `minio.service` file uses an environment file located at `/etc/default/minio` for sourcing configuration settings, including the startup. Specifically, the `MINIO_VOLUMES` variable sets the startup command:

```shell
cat /etc/default/minio | grep "MINIO_VOLUMES"
```

The command returns output similar to the following:

```shell
MINIO_VOLUMES="https://minio-{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio-{5...8}.example.net:9000/mnt/disk{1...4}/minio https://minio-{9...12}.example.net:9000/mnt/disk{1...4}/minio"
```

Edit the environment file and remove the decommissioned pools from the `MINIO_VOLUMES` value.

### 5) Update Network Control Plane {#id4}

Update any load balancers, reverse proxies, or other network control planes to remove the decommissioned server pools from the connection configuration for the MinIO deployment.

Specific instructions for configuring network control plane components is out of scope for this procedure.

### 6) Restart the MinIO Deployment {#id5}

Issue the following commands on each node **simultaneously** in the deployment to restart the MinIO service:

```shell
sudo systemctl restart minio.service
```

Use the following commands to confirm the service is online and functional:

```shell
sudo systemctl status minio.service
journalctl -f -u minio.service
```

MinIO may log an increased number of non-critical warnings while the server processes connect and synchronize. These warnings are typically transient and should resolve as the deployment comes online.

MinIO strongly recommends restarting all MinIO Server processes in a deployment simultaneously. MinIO operations are atomic and strictly consistent. As such the restart procedure is non-disruptive to applications and ongoing operations.

Do **not** perform “rolling” (e.g. one node at a time) restarts.

Once the deployment is online, use [`mc admin info`](/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) to confirm the uptime of all remaining servers in the deployment.
