---
title: "Deployment Architecture"
url: "/operations/concepts/architecture/"
description: "Silo production deployment architecture and topology"
weight: 10
minio_origin: true
silo_modified: true
---

<a id="deployment-architecture"></a>
<a id="minio-architecture"></a>

This page provides an overview of MinIO deployment architectures from a production perspective. For information on specific hardware or software configurations, see:

- [Hardware Checklist](/operations/checklists/hardware/#minio-hardware-checklist)
- [Security Checklist](/operations/checklists/security/#minio-security-checklist)
- [Software Checklist](/operations/checklists/software/#minio-software-checklists)
- [Thresholds and Limits](/operations/concepts/thresholds/#minio-server-limits)

## Distributed MinIO Deployments {#distributed-minio-deployments}

**A production MinIO deployment consists of at least 4 MinIO hosts with homogeneous storage and compute resources.**

> MinIO aggregates these resources together as a [pool](/operations/concepts/#minio-intro-server-pool) and presents itself as a single object storage service.
>
> <figure>
>   <img src="/images/architecture/architecture-4-node-deploy.svg" alt="4 Node MinIO deployment with homogeneous storage and compute resources" />
>   <figcaption>Each MinIO host in this pool has matching compute, storage, and network configurations</figcaption>
> </figure>

**MinIO provides best performance when using locally-attached storage, such as NVMe or SSD drives attached to a PCI-E controller board on the host machine.**

> Storage controllers should present XFS-formatted drives in “Just a Bunch of Drives” (JBOD) configurations with no RAID, pooling, or other hardware/software resiliency layers. MinIO recommends against caching, either at the drive or the controller layer. Either type of caching can cause <abbr title="Input / Output">I/O</abbr> spikes as the cache fills and clears, resulting in unpredictable performance.
>
> <figure>
>   <img src="/images/architecture/architecture-one-node-DAS.svg" alt="MinIO Server diagram of Direct-Attached Storage via SAS to a PCI-E Storage Controller" />
>   <figcaption>Each SSD connects by SAS to a PCI-E-attached storage controller operating in HBA mode</figcaption>
> </figure>

**MinIO automatically groups drives in the pool into [erasure sets](/operations/concepts/erasure-coding/#minio-ec-erasure-set).**

> Erasure sets are the foundational component of MinIO [availability and resiliency](/operations/concepts/availability-and-resiliency/#minio-availability-resiliency). MinIO stripes erasure sets symmetrically across the nodes in the pool to maintain even distribution of erasure set drives. MinIO then partitions objects into data and parity shards based on the deployment [parity](/operations/concepts/erasure-coding/#minio-ec-parity) and distributes them across an erasure set.
>
> For a more complete discussion of MinIO redundancy and healing, see [Erasure Coding](/operations/concepts/erasure-coding/#minio-erasure-coding) and [Object Healing](/operations/concepts/healing/#minio-concepts-healing).
>
> <figure>
>   <img src="/images/architecture/architecture-erasure-set-shard.svg" alt="Diagram of object being sharded into eight data and eight parity blocks, distributed across sixteen drives" />
>   <figcaption>With the maximum parity of <code>EC:8</code>, MinIO shards the object into 8 data and 8 parity blocks, distributing them across the drives in the erasure set.
> All erasure sets in this pool have the same stripe size and shard distribution.</figcaption>
> </figure>

**MinIO uses a deterministic hashing algorithm based on object name and path to select the erasure set for a given object.**

> For each unique object namespace `BUCKET/PREFIX/[PREFIX/...]/OBJECT.EXTENSION`, MinIO always selects the same erasure set for read/write operations. MinIO handles all routing within pools and erasure sets, making the select/read/write process entirely transparent to applications.
>
> <figure>
>   <img src="/images/architecture/architecture-erasure-set-retrieve-object.svg" alt="Diagram of object retrieval from only data shards" />
>   <figcaption>MinIO reconstructs objects from data or parity shards transparently before returning the object to the requesting client.</figcaption>
> </figure>

**Each MinIO server has a complete picture of the distributed topology, such that an application can connect and direct operations against any node in the deployment.**

> The MinIO responding node automatically handles routing internal requests to other nodes in the deployment *and* returning the final response to the client.
>
> Applications typically should not manage those connections, as any changes to the deployment topology would require application updates. Production environments should instead deploy a load balancer or similar network control plane component to manage connections to the MinIO deployment. For example, you can deploy an NGINX load balancer to perform “least connections” or “round robin” load balancing against the available nodes in the deployment.
>
> <figure>
>   <img src="/images/architecture/architecture-load-balancer-8-node.svg" alt="Diagram of an eight node MinIO deployment behind a load balancer" />
>   <figcaption>The load balancer routes the request to any node in the deployment.
> The receiving node handles any internode requests thereafter.</figcaption>
> </figure>

**You can expand a MinIO deployment’s available storage through [pool expansion](/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed).**

> Each pool consists of an independent group of nodes with their own erasure sets. MinIO must query each pool to determine the correct erasure set to which it directs read and write operations, such that each additional pool adds increased internode traffic per call. The pool which contains the correct erasure set then responds to the operation, remaining entirely transparent to the application.
>
> If you modify the MinIO topology through pool expansion, you can update your applications by modifying the load balancer to include the new pool’s nodes. Applications can continue using the load balancer address for the MinIO deployment without any updates or modifications. This ensures even distribution of requests across all pools, while applications continue using the single load balancer URL for MinIO operations.
>
> <figure>
>   <img src="/images/architecture/architecture-load-balancer-multi-pool.svg" alt="Diagram of a multi-pool minio deployment behind a load balancer" />
>   <figcaption>The PUT request requires checking each pool for the correct erasure set.
> Once identified, MinIO partitions the object and distributes the data and parity shards across the appropriate set.</figcaption>
> </figure>

**Client applications can use any S3-compatible SDK or library to interact with the MinIO deployment.**

> MinIO publishes its own [SDK](/developers/minio-drivers/#minio-drivers) specifically intended for use with S3-compatible deployments.
>
> <figure>
>   <img src="/images/architecture/architecture-multiple-clients.svg" alt="Diagram of multiple S3-compatible clients using SDKs to connect to MinIO" />
>   <figcaption>Clients using a variety of S3-compatible SDKs can perform operations against the same MinIO deployment.</figcaption>
> </figure>
>
> MinIO uses a strict implementation of the S3 API, including requiring clients to sign all operations using AWS [Signature V4](https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html) or the legacy Signature V2. AWS signature calculation uses the client-provided headers, such that any modification to those headers by load balancers, proxies, security programs, or other components will result in signature mismatch errors and request failure. Ensure any such intermediate components support pass-through of unaltered headers from client to server.
>
> While the S3 API uses HTTP methods like `GET` and `POST` for all operations, applications typically use an SDK for S3 operations. In particular, the complexity of signature calculation typically makes interfacing via `curl` or similar REST clients impractical. MinIO recommends using S3-compatible SDKs or libraries which perform the signature calculation automatically as part of operations.

<a id="minio-deployment-architecture-replicated"></a>

## Replicated MinIO Deployments {#replicated-minio-deployments}

**MinIO [site replication](/operations/replication/multi-site-replication/#minio-site-replication-overview) provides support for synchronizing distinct independent deployments.**

> You can deploy peer sites in different racks, datacenters, or geographic regions to support functions like <abbr title="Business Continuity / Disaster Recovery">BC/DR</abbr> or geo-local read/write performance in a globally distributed MinIO object store.
>
> <figure>
>   <img src="/images/architecture/architecture-multi-site.svg" alt="Diagram of a multi-site deployment with three MinIO peer site" />
>   <figcaption>A MinIO multi-site deployment with three peers.
> Write operations on one peer replicate to all other peers in the configuration automatically.</figcaption>
> </figure>

**Replication performance primarily depends on the network latency between each peer site.**

> With geographically distributed peer sites, high latency between sites can result in significant replication lag. This can compound with workloads that are near or at the deployment’s overall performance capacity, as the replication process itself requires sufficient free <abbr title="Input / Output">I/O</abbr> to synchronize objects.
>
> <figure>
>   <img src="/images/architecture/architecture-multi-site-latency.svg" alt="Diagram of a multi-site deployment with latency between sites" />
>   <figcaption>In this peer configuration, the latency between Site A and its peer sites is 100ms.
> The soonest the object fully synchronizes to all sites is at least 110ms.</figcaption>
> </figure>

**Deploying a global load balancer or similar network appliance with support for site-to-site failover protocols is critical to the functionality of multi-site deployments.**

> The load balancer should support a health probe/check setting to detect the failure of one site and automatically redirect applications to any remaining healthy peer.
>
> <figure>
>   <img src="/images/architecture/architecture-load-balancer-multi-site.svg" alt="Diagram of a site replication deployment with two sites" />
>   <figcaption>The Load Balancer automatically routes client requests using configured logic (geo-local, latency, etc.).
> Data written to one site automatically replicates to the other peer site.</figcaption>
> </figure>
>
> The load balancer should meet the same requirements as single-site deployments regarding connection balancing and header preservation. MinIO replication handles transient failures by queuing objects for replication.
