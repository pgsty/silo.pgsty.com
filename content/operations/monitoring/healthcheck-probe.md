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
