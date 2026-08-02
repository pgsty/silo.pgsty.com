---
title: "Core Operational Concepts"
url: "/operations/concepts/"
weight: 30
icon: fa-solid fa-diagram-project
minio_origin: true
silo_modified: false
math: true
---

<a id="core-operational-concepts"></a>

## What are the components of a MinIO Deployment? {#what-are-the-components-of-a-minio-deployment}

A MinIO deployment consists of a set of storage and compute resources running one or more [`minio server`](/reference/minio-server/#command-minio.server) nodes that together act as a single object storage repository.

A standalone instance of MinIO consists of a single Server Pool with a single [`minio server`](/reference/minio-server/#command-minio.server) node. Standalone instances are best suited for initial development and evaluation.

A MinIO deployment can run directly on a physical device in a `bare metal` or non-virtualized infrastructure. Or, MinIO might run within a virtual machine on a cloud service, such as using Docker, Podman, or Kubernetes. MinIO can run locally, on a private cloud, or in any of the many public clouds available on the market.

The specific way you design, architect, and build your system is called the system’s `topology`.

## What system topologies does MinIO support? {#what-system-topologies-does-minio-support}

MinIO can deploy to three types of topologies:

1. [Single Node Single Drive](/operations/deployments/installation/#minio-snsd), one MinIO server with a single drive or folder for data

   For example, testing on a local PC using a folder on the computer’s hard drive.
2. [Single Node Multi Drive](/operations/deployments/installation/#minio-snmd), one MinIO server with multiple mounted drives or folders for data

   For example, a single container with two or more mounted volumes.
3. [Multi Node Multi Drive](/operations/deployments/installation/#minio-mnmd), multiple MinIO servers with multiple mounted drives or volumes for data

   For Baremetal infrastructure, you can install and manage distributed MinIO deployments using Ansible, Terraform, or manual processes

   For Kubernetes infrastructure, use the MinIO Operator to manage and deploy distributed MinIO Tenants.

## How does a distributed MinIO deployment work? {#how-does-a-distributed-minio-deployment-work}

A distributed deployment makes use of the resources of more than one physical or virtual machine’s compute and storage resources. In modern situations, this often means running MinIO in a private or public cloud environment, such as with Amazon Web Services, the Google Cloud Platform, Microsoft’s Azure platform, or many others.

<a id="minio-intro-server-pool"></a>

### How does MinIO manage multiple virtual or physical servers? {#how-does-minio-manage-multiple-virtual-or-physical-servers}

While testing MinIO may only involve a single drive on a single computer, most production MinIO deployments use multiple compute and storage devices to create a high availability environment. A server pool is a set of [`minio server`](/reference/minio-server/#command-minio.server) nodes that pool their drives and resources to support object storage write and retrieval requests.

MinIO supports adding one or more server pools to existing MinIO deployments for horizontal expansion. When MinIO has multiple server pools available, an individual object always writes to the same erasure set in the same server pool.

If one server pool goes down, MinIO halts I/O to all pools until the cluster resumes normal operations. You must restore the pool to working operation to resume I/O to the deployment. Objects written to other pools remain safe on disk while you perform repair operations.

The [`HOSTNAME`](/reference/minio-server/#minio.server.HOSTNAME) argument passed to the [`minio server`](/reference/minio-server/#command-minio.server) command represents a Server Pool:

Consider the following example startup command, which creates a single Server Pool with 4 [`minio server`](/reference/minio-server/#command-minio.server) nodes of 4 drives each for a total of 16 drives.

```shell
minio server https://minio{1...4}.example.net/mnt/disk{1...4}

             |                    Server Pool                |
```

Starting server pools in the same [`minio server`](/reference/minio-server/#command-minio.server) startup command enables awareness of all server pool peers.

See [`minio server`](/reference/minio-server/#command-minio.server) for complete syntax and usage.

<a id="minio-intro-cluster"></a>

### How does MinIO link multiple server pools into a single MinIO cluster? {#how-does-minio-link-multiple-server-pools-into-a-single-minio-cluster}

A cluster refers to an entire MinIO deployment consisting of one or more Server Pools.

Consider the command below that creates a cluster consisting of two Server Pools, each with 4 [`minio server`](/reference/minio-server/#command-minio.server) nodes and 4 drives per node for a total of 32 drives.

```shell
minio server https://minio{1...4}.example.net/mnt/disk{1...4} \
             https://minio{5...8}.example.net/mnt/disk{1...4}

             |                    Server Pool                |
```

Each server pool has one or more [erasure sets](/operations/concepts/erasure-coding/#minio-ec-erasure-set) depending on the number of drives and nodes in the pool.

MinIO strongly recommends production clusters consist of a *minimum* of 4 [`minio server`](/reference/minio-server/#command-minio.server) nodes in a Server Pool for proper high availability and durability guarantees.

### Can I change the size of an existing MinIO deployment? {#can-i-change-the-size-of-an-existing-minio-deployment}

MinIO [distributed deployments](/operations/deployments/installation/#minio-mnmd) support expansion and decommissioning as functions to increase or decrease the available storage.

Expansion consists of adding one or more [server pools](#minio-intro-server-pool) to an existing deployment. Each server pool consists of dedicated nodes and storage that contribute to the overall capacity of the deployment. Once you create a server pool you cannot change its size, but you can add or remove capacity at any time by adding or decommissioning pools.

See [Baremetal: Expand a MinIO deployment](/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed) and [Kubernetes: Expand a MinIO Tenant](/operations/deployments/k8s-expand-minio-tenant-on-kubernetes/#minio-k8s-expand-minio-tenant) for more information on expansion in Baremetal and Kubernetes infrastructures respectively.

For deployments which have multiple server pools, you can [decommission](/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning) the older pools and migrate that data to the newer pools in the deployment. Once started, decommissioning cannot be stopped. MinIO intends decommissioning for use with removing older pools with aged hardware, and not as an operation performed regularly within any deployment.

{{% alert color="info" %}}
**Maintain pool order when decommissioning and then adding**

If you decommission one pool in a multiple pool deployment, you cannot use the same node sequence for a new pool. For example, consider a deployment with the following pools:

```
https://minio-{1...4}.example.net/mnt/drive-{1...4}
https://minio-{5...8}.example.net/mnt/drive-{1...4}
https://minio-{9...12}.example.net/mnt/drive-{1...4}
```

If you decommission the `minio-{5...8}` pool, you cannot add a new pool with the same node numbering. You must add the new pool *after* `minio-{9...12}`:

```
https://minio-{1...4}.example.net/mnt/drive-{1...4}
https://minio-{9...12}.example.net/mnt/drive-{1...4}
https://minio-{13...16}.example.net/mnt/drive-{1...4}
```
{{% /alert %}}

### How do I manage one or more MinIO instances or clusters? {#how-do-i-manage-one-or-more-minio-instances-or-clusters}

There are several options to manage your MinIO deployments and clusters:

- Use the command line with [`mc`](/reference/minio-mc/#command-mc) and [`mc admin`](/reference/minio-mc-admin/#command-mc.admin)
- The [MinIO Console](/administration/minio-console/#minio-console) graphical user interface for individual instances

<a id="minio-rebalance"></a>

### How do I manage object distribution across a MinIO deployment? {#how-do-i-manage-object-distribution-across-a-minio-deployment}

MinIO optimizes storage of objects across available pools by writing new objects (that is, objects with no existing versions) to the server pool with the most free space compared total amount of free space on all available server pools. MinIO does not perform the costly action of rebalancing objects from older pools to newer pools. Instead, new objects typically route to the new pool as it has the most free space. As that pool fills, new write operations eventually balance out across all pools in the deployment. For more information on write preference calculation logic, see [Writing Files](/operations/deployments/baremetal-expand-minio-deployment/#minio-writing-files) below.

Rebalancing data across all pools after an expansion is an expensive operation that requires scanning the entire deployment and moving objects between pools. This may take a long time to complete depending on the amount of data to move.

Starting with MinIO Client version RELEASE.2022-11-07T23-47-39Z, you can manually initiate a rebalancing operation across all server pools using [`mc admin rebalance`](/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance).

Rebalancing does not block ongoing operations and runs in parallel to all other I/O. This can result in reduced performance of regular operations. Consider scheduling rebalancing operations during non-peak periods to avoid impacting production workloads. You can start and stop rebalancing at any time

## How do I upload objects to MinIO? {#how-do-i-upload-objects-to-minio}

You can use any S3-compatible SDK to upload objects to a MinIO deployment. Each SDK performs the equivalent of a PUT operation which transmits the object to MinIO for storage.

MinIO also implements support for [multipart uploads](https://docs.aws.amazon.com/AmazonS3/latest/userguide/mpuoverview.html), where clients can split an object into multiple parts for better throughput and reliability of transmission. MinIO reassembles these parts until it has a completed object, then stores that object at the specified path.

## How does MinIO provide availability, redundancy, and reliability? {#how-does-minio-provide-availability-redundancy-and-reliability}

### MinIO Uses [Erasure Coding](/operations/concepts/erasure-coding/#minio-erasure-coding) for Data Redundancy and Reliability {#minio-uses-erasure-coding-for-data-redundancy-and-reliability}

MinIO Erasure Coding is a data redundancy and availability feature that allows MinIO deployments with multiple drives to automatically reconstruct objects on-the-fly despite the loss of multiple drives or nodes in the cluster. Erasure Coding provides object-level [healing](/operations/concepts/healing/#minio-concepts-healing) with significantly less overhead than adjacent technologies such as RAID or replication.

### MinIO Implements Bit Rot Healing to Protect Data At Rest {#minio-implements-bit-rot-healing-to-protect-data-at-rest}

Bit rot is the random, silent corruption to data that can happen on any storage device. Bit rot corruption is not prompted by any activity from a user, nor does the system’s operating system alone have awareness of the corruption to notify a user or administrator about a change to the data.

Some common reasons for bit rot include:

- ageing drives
- current spikes
- bugs in drive firmware
- phantom writes
- misdirected reads/writes
- driver errors
- accidental overwrites

MinIO uses a hashing algorithm to confirm the integrity of an object. This algorithm automatically applies at the time of any `GET` and `HEAD` operations for an object. For objects in a versioned bucket, a `PUT` operation can also trigger healing if MinIO identifies version inconsistencies. If an object becomes corrupted by bit rot, MinIO can automatically [heal](/operations/concepts/healing/#minio-concepts-healing) the object depending on the availability of parity shards for the object.

MinIO can also perform bit rot checks and healing using the [MinIO Scanner](/operations/concepts/scanner/#minio-concepts-scanner). However, scanner bit rot checking is **off** by default. Active bit rot healing during scanner has a high performance impact in comparison to the low probability of bit rot affecting multiple object shards distributed across multiple drives and nodes. The automatic checks during normal operations is generally sufficient for bit rot, and MinIO does not recommend using the scanner for this type of health check.

### MinIO Distributes Data Across [Erasure Sets](/operations/concepts/erasure-coding/#minio-ec-erasure-set) for High Availability and Resiliency {#minio-distributes-data-across-erasure-sets-for-high-availability-and-resiliency}

An erasure set is a group of multiple drives that supports MinIO [Erasure Coding](/operations/concepts/erasure-coding/#minio-erasure-coding). Erasure Coding provides high availability, reliability, and redundancy of data stored on a MinIO deployment.

MinIO divides objects into chunks — called *shards* — and evenly distributes them among each drive in the Erasure Set. MinIO can continue seamlessly serving read and write requests despite the loss of any single drive. At the highest redundancy levels, MinIO can serve read requests with minimal performance impact despite the loss of up to half (\(N / 2\)) of the total drives in the deployment.

MinIO calculates the size and number of Erasure Sets in a Server Pool based on the total number of drives in the set *and* the number of [`minio`](/reference/minio-server/#command-minio) servers in the set. See [Erasure Coding Basics](/operations/concepts/erasure-coding/#minio-ec-erasure-set) for more information.

### MinIO Automatically Heals Corrupt or Missing Data On-the-fly {#minio-automatically-heals-corrupt-or-missing-data-on-the-fly}

[Healing](/operations/concepts/healing/#minio-concepts-healing) is MinIO’s ability to restore data after some event causes data loss. Data loss can come from bit rot, drive loss, or node loss.

[Erasure coding](/operations/concepts/erasure-coding/#minio-erasure-coding) provides continued read and write access if an object has been partially lost.

{{% alert color="info" %}}
**Exclusive access to drives**

MinIO **requires** *exclusive* access to the drives or volumes provided for object storage. No other processes, software, scripts, or persons should perform *any* actions directly on the drives or volumes provided to MinIO or the objects or files MinIO places on them.

Unless directed by MinIO Engineering, do not use scripts or tools to directly modify, delete, or move any of the data shards, parity shards, or metadata files on the provided drives, including from one drive or node to another. Such operations are very likely to result in widespread corruption and data loss beyond MinIO’s ability to heal.
{{% /alert %}}

### MinIO Writes Data Protection at the Object Level with Parity {#minio-writes-data-protection-at-the-object-level-with-parity}

A MinIO deployment with multiple drives divides the available drives into data drives and parity drives. MinIO Erasure Coding adds additional hashing information about the contents of an object to the parity drives when writing an object. MinIO uses the parity information to confirm the integrity of an object and, if necessary, to restore a lost, missing, or corrupted object shard on a given drive or set of drives.

MinIO can tolerate losing up to the total number of drives equal to the number of parity devices available in the erasure set while still providing full access to an object.

### Deliver Read and Write Functions with Quorum {#deliver-read-and-write-functions-with-quorum}

A minimum number of drives that must be available to perform a task. MinIO has one quorum for reading data and a separate quorum for writing data.

Typically, MinIO requires a higher number of available drives to maintain the ability to write objects than what is required to read objects.
