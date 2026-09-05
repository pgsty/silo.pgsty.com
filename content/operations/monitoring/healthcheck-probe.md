---
title: "Healthcheck API"
url: "/operations/monitoring/healthcheck-probe/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/healthcheck-probe.rst
upstream_modified: false
---

<a id="healthcheck-api"></a>
<a id="minio-healthcheck-api"></a>

MinIO exposes unauthenticated endpoints for probing node uptime and cluster [high availability](/operations/concepts/erasure-coding/#minio-ec-parity) for simple healthchecks. These endpoints return an HTTP status code indicating whether the underlying resource is healthy or satisfies read/write quorum. MinIO exposes no other data through these endpoints.

## Node Liveness {#node-liveness}

Use the following endpoint to test if a MinIO server is online:

```shell
curl -I https://minio.example.net:9000/minio/health/live
```

Replace `https://minio.example.net:9000` with the DNS hostname of the MinIO server to check.

A response code of `200 OK` indicates the MinIO server is online and functional. Any other HTTP codes indicate an issue with reaching the server, such as a transient network issue or potential downtime.

The healthcheck probe alone cannot determine if a MinIO server is offline. Instead, the probe determines whether the current host machine can reach the server. Consider configuring a Prometheus [alert](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) using `minio_cluster_health_nodes_offline_count` for [metrics v3](/operations/monitoring/metrics-and-alerts/#minio-available-v3-cluster-metrics) or `minio_cluster_nodes_offline_total` for [metrics v2](/operations/monitoring/metrics-v2/#minio-available-cluster-metrics) to detect whether one or more MinIO nodes are offline.

<a id="minio-cluster-write-quorum"></a>

## Cluster Write Quorum {#cluster-write-quorum}

Use the following endpoint to test if a MinIO cluster has [write quorum](/operations/concepts/erasure-coding/#minio-ec-parity):

```shell
curl -I https://minio.example.net:9000/minio/health/cluster
```

Replace `https://minio.example.net:9000` with the DNS hostname of a node in the MinIO cluster to check. For clusters using a load balancer to manage incoming connections, specify the hostname for the load balancer.

A response code of `200 OK` indicates that the MinIO cluster has sufficient MinIO servers online to meet write quorum. A response code of `503 Service Unavailable` indicates the cluster does not currently have write quorum.

The healthcheck probe alone cannot determine if a MinIO server is offline or processing write operations normally - only whether enough MinIO servers are online to meet write quorum requirements based on the configured [erasure code parity](/operations/concepts/erasure-coding/#minio-ec-parity). Consider configuring a Prometheus [alert](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) using one of the following metrics to detect potential issues or errors on the MinIO cluster:

- `minio_cluster_nodes_offline_total` to alert if one or more MinIO nodes are offline.
- `minio_node_drive_free_bytes` to alert if the cluster is running low on free drive space.

## Cluster Read Quorum {#cluster-read-quorum}

Use the following endpoint to test if a MinIO cluster has [read quorum](/operations/concepts/erasure-coding/#minio-ec-parity):

```shell
curl -I https://minio.example.net:9000/minio/health/cluster/read
```

Replace `https://minio.example.net:9000` with the DNS hostname of a node in the MinIO cluster to check. For clusters using a load balancer to manage incoming connections, specify the hostname for the load balancer.

A response code of `200 OK` indicates that the MinIO cluster has sufficient MinIO servers online to meet read quorum. A response code of `503 Service Unavailable` indicates the cluster does not currently have read quorum.

The healthcheck probe alone cannot determine if a MinIO server is offline or processing read operations normally - only whether enough MinIO servers are online to meet read quorum requirements based on the configured [erasure code parity](/operations/concepts/erasure-coding/#minio-ec-parity). Consider configuring a Prometheus [alert](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) using the `minio_cluster_nodes_offline_total` metric to detect whether one or more MinIO nodes are offline.

## Cluster Maintenance Check {#cluster-maintenance-check}

Use the following endpoint to test if the MinIO cluster can maintain both [read](/operations/concepts/erasure-coding/#minio-ec-parity) and [write](/operations/concepts/erasure-coding/#minio-ec-parity) if the specified MinIO server is taken down for maintenance:

```shell
curl -I https://minio.example.net:9000/minio/health/cluster?maintenance=true
```

Replace `https://minio.example.net:9000` with the DNS hostname of a node in the MinIO cluster to check. For clusters using a load balancer to manage incoming connections, specify the hostname for the load balancer.

A response code of `200 OK` indicates that the MinIO cluster has sufficient MinIO servers online to meet write quorum. A response code of `412 Precondition Failed` indicates the cluster will lose quorum if the MinIO server goes offline.

The healthcheck probe alone cannot determine if a MinIO server is offline - only whether enough MinIO servers will be online after taking the node down for maintenance to meet read and write quorum requirements based on the configured [erasure code parity](/operations/concepts/erasure-coding/#minio-ec-parity). Consider configuring a Prometheus [alert](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) using the `minio_cluster_nodes_offline_total` metric to detect whether one or more MinIO nodes are offline.

## Startup Readiness Window {#startup-readiness-window}

None of the endpoints above proves that the node which received the request can already serve the data path after a restart. Each node connects its erasure drives to its peers in a monitor loop: a remote drive that could not be connected during startup stays uninstalled on that node until a later pass, and the monitor waits 15 seconds after each completed pass, so that interval is a floor between attempts, not a bound on recovery. While a drive is uninstalled, the node's liveness endpoint answers `200 OK`, both cluster endpoints, `mc admin info` and `mcli ready` can report healthy as well, because the cluster endpoints aggregate every peer's report of its own local drives rather than the drives this node has installed. Yet a PUT through that node can fail with `503 SlowDownWrite` for lack of write quorum, and a GET through it of an object another node just wrote can answer `404 NoSuchKey`. In the review runs that established this, sampled I/O began succeeding roughly 13 to 15 seconds after the administrative views became healthy on a four-node loopback cluster, consistent with the reconnect interval, and every object acknowledged by other nodes during the window was readable afterwards; these are observations, not guarantees, since reconnection can keep failing.

Automation that restarts a cluster and then immediately writes to it, such as an upgrade or failover runbook, should gate on a bounded data-path check rather than on these endpoints: one small PUT through each node followed by a read of each object through every node, repeated until every request returns the correct bytes and the acknowledged version within one fixed deadline, with each request budgeted from the remaining deadline and SDK retries disabled, and with the acknowledged objects re-read afterwards. Record the time to first usable I/O separately from the endpoint result. Such a check proves sampled I/O at that moment for the erasure sets those keys hash to; it proves neither that every set is complete nor that there is headroom for a further node loss, since a set can admit writes with fewer than all of its drives installed. The endpoints remain the right signal for their stated purpose, process liveness and quorum membership.
