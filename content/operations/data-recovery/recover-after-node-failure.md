---
title: "Node Failure Recovery"
url: "/operations/data-recovery/recover-after-node-failure/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/data-recovery/recover-after-node-failure.rst
upstream_modified: false
---

<a id="node-failure-recovery"></a>
<a id="minio-restore-hardware-failure-node"></a>

If a MinIO node suffers complete hardware failure (e.g. loss of all drives, data, etc.), the node begins [healing operations](/operations/concepts/healing/#minio-concepts-healing) once it rejoins the deployment. MinIO healing occurs only on the replaced hardware and does not typically impact deployment performance.

MinIO healing ensures consistency and correctness of all data restored onto the drive.

> [!NOTE]
> **Exclusive access to drives**
>
> MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.
>
> Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.

The replacement node hardware should be substantially similar to the failed node. There are no negative performance implications to using improved hardware.

The replacement drive hardware should be substantially similar to the failed drive. For example, replace a failed SSD with another SSD drive of the same capacity. While you can use drives with larger capacity, MinIO uses the *smallest* drive’s capacity as the ceiling for all drives in the [Server Pool](/operations/concepts/#minio-intro-server-pool).

The following steps provide a more detailed walkthrough of node replacement. These steps assume a MinIO deployment where each node has a DNS hostname as per the [documented prerequisites](/operations/deployments/installation/#minio-installation).

## 1) Start the Replacement Node {#start-the-replacement-node}

Ensure the new node has received all necessary security, firmware, and OS updates as per industry, regulatory, or organizational standards and requirements.

The new node software configuration *must* match that of the other nodes in the deployment, including but not limited to the OS and Kernel versions and configurations. Heterogeneous software configurations may result in unexpected or undesired behavior in the deployment.

## 2) Update Hostname for the New Node {#update-hostname-for-the-new-node}

*Optional* This step is only required if the replacement node has a different IP address from the failed host.

Ensure the hostname associated to the failed node now resolves to the new node.

For example, if `https://minio-1.example.net` previously resolved to the failed host, it should now resolve to the new host.

## 3) Download and Prepare the MinIO Server {#download-and-prepare-the-minio-server}

Follow the [deployment procedure](/operations/deployments/installation/#minio-installation) to download and run the MinIO server using a matching configuration as all other nodes in the deployment.

- The MinIO server version *must* match across all nodes
- The MinIO service and environment file configurations *must* match across all nodes.

## 4) Rejoin the node to the deployment {#rejoin-the-node-to-the-deployment}

Start the MinIO server process on the node and monitor the process output using [`mc admin logs`](/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) or by monitoring the MinIO service logs using `journalctl -u minio` for `systemd` managed installations.

The server output should indicate that it has detected the other nodes in the deployment and begun [healing operations](/operations/concepts/healing/#minio-concepts-healing).

Use [`mc admin heal`](/reference/minio-mc-admin/mc-admin-heal/#command-mc.admin.heal) to monitor overall healing status on the deployment. MinIO aggressively heals the node to ensure rapid recovery from the degraded state.

## 5) Next Steps {#next-steps}

Continue monitoring the deployment until healing completes. Deployments with persistent and repeated node failures should schedule dedicated maintenance to identify the root cause. Consider using [MinIO SUBNET](https://min.io/pricing?jmp=docs) to coordinate with MinIO engineering around guidance for any such operations.
