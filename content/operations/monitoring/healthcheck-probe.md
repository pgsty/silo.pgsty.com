---
title: "Healthcheck API"
url: "/operations/monitoring/healthcheck-probe/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/healthcheck-probe.rst
upstream_modified: true
---

<a id="healthcheck-api"></a>
<a id="minio-healthcheck-api"></a>

MinIO exposes unauthenticated endpoints for probing node uptime and cluster [high availability](/operations/concepts/erasure-coding/#minio-ec-parity) for simple healthchecks. These endpoints return an HTTP status code indicating whether the underlying resource is healthy or satisfies read/write quorum. MinIO exposes no other data through these endpoints.

## Native Probes and Application Startup {#native-probe}

SILO includes a built-in `silo healthcheck` subcommand that probes the local `/minio/health/*` HTTP endpoints without requiring `curl`, `mc`, or a shell inside the container:

```shell
silo healthcheck [FLAGS] [live|ready|cluster|cluster-read]
```

- `CHECK` selects the target endpoint: `live` (default), `ready`, `cluster`, or `cluster-read`.
- `--address` (or `MINIO_ADDRESS`, default `:9000` with an empty host resolved to `127.0.0.1`) sets the target `HOST:PORT` and switches to HTTPS automatically when `public.crt` and `private.key` exist in `--certs-dir`.
- `--url` (or `MINIO_HEALTHCHECK_URL`) overrides `--address` and TLS auto-detection with an explicit `http[s]://HOST:PORT` base URL.
- `--maintenance` applies to `cluster` only, appends `?maintenance=true`, and exits `1` when the server returns HTTP `412 Precondition Failed`.
- `--timeout` sets the probe deadline (`5s` by default for `live` and `ready`; `15s` by default for `cluster` and `cluster-read`).
- Global flags `--certs-dir`, `--json`, and `--quiet` control certificate lookup and output formatting. The command exits `0` when healthy and `1` otherwise.

`silo healthcheck ready` calls `/minio/health/ready`. That endpoint checks HTTP queue capacity plus configured KMS and `etcd` reachability, and can return `200 OK` before storage and IAM finish loading. This behavior preserves distributed peer bootstrap; Kubernetes headless services must keep `publishNotReadyAddresses: true`. Do not configure `cluster` as a container liveness probe or as a prerequisite for peer connectivity.

The `-distroless` container image sets its built-in `HEALTHCHECK` to `/usr/bin/silo healthcheck ready`. Docker Compose `depends_on: condition: service_healthy` therefore confirms only that readiness probe, not S3 data-path availability. Switching to `cluster` still leaves the remote-drive reconnection window described below. Any dependent application that immediately accesses objects must run a bounded signed S3 write and readback check and stop startup or rollout on failure. Use a dedicated bucket and unique probe keys, and delete them after verification.

## Node Liveness {#node-liveness}

Use the following endpoint to test whether a SILO server HTTP listener is serving requests:

```shell
curl -I https://minio.example.net:9000/minio/health/live
```

Replace `https://minio.example.net:9000` with the DNS hostname and port of the server to check.

`/minio/health/live` returns `200 OK` as soon as the HTTP listener starts, even before the object layer loads. While storage initializes, the response includes `x-minio-server-status: offline`. The endpoint returns `503 Service Unavailable` when queued requests exceed the API request pool capacity. Because a failed liveness check restarts pods in Kubernetes, `/minio/health/live` contacts no external systems (neither KMS nor `etcd`), preventing restarts during slow drive initialization or external service outages.

The liveness probe checks only whether the current client can reach the server HTTP listener and whether its request queue has capacity. Configure a Prometheus [alert](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) using `minio_cluster_health_nodes_offline_count` for [metrics v3](/operations/monitoring/metrics-and-alerts/#minio-available-v3-cluster-metrics) or `minio_cluster_nodes_offline_total` for [metrics v2](/operations/monitoring/metrics-v2/#minio-available-cluster-metrics) to detect offline cluster nodes.

## Node Readiness {#node-readiness}

Use the following endpoint to test process readiness and configured external dependencies:

```shell
curl -I https://minio.example.net:9000/minio/health/ready
```

Replace `https://minio.example.net:9000` with the DNS hostname and port of the server to check.

`/minio/health/ready` checks the same HTTP request queue capacity as `/minio/health/live`, and also verifies KMS key generation and `etcd` health when KMS or `etcd` is configured. When neither KMS nor `etcd` is configured, `/minio/health/ready` follows the same check path as `/minio/health/live`. Like `/minio/health/live`, `/minio/health/ready` can return `200 OK` (with `x-minio-server-status: offline`) before the object layer or IAM finishes loading, so peer discovery can proceed during cluster startup.

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

[SILO 20261109](/blog/release/silo-20261109/) retains this behavior: the [cluster health implementation](https://github.com/pgsty/silo/blob/d998292387ccf1d2907749e0fb1575ef5fb93fda/cmd/erasure-server-pool.go#L3162) evaluates reported drive quorum across peers. Check both cluster endpoints, then verify actual S3 reads and writes before you resume application workloads. For the full probe specification, see [Healthcheck Probe Semantics](/compatibility/feature/healthcheck/).

None of the HTTP health endpoints proves that the receiving node can serve object I/O immediately after a restart. Each node connects to remote peer drives in a background monitor loop. If a remote drive is unreachable at startup, it remains uninstalled on that node until a later monitor pass. The monitor waits 15 seconds after each completed pass, so 15 seconds is a minimum interval between retries rather than an upper bound on recovery.

While remote drives remain uninstalled on a restarted node, `/minio/health/live`, `/minio/health/ready`, both `/minio/health/cluster*` endpoints, `mc admin info`, and `mcli ready` can all report healthy. The cluster endpoints aggregate each peer's report of its own local drives rather than checking which remote drives the receiving node has mounted. During this window, a `PUT` through that node can fail with `503 SlowDownWrite`, and a `GET` for a newly written object on another node can fail until remote drives reconnect.

Upgrade and failover automation must gate traffic on a bounded S3 data-path check rather than on HTTP health endpoints alone:

1. Set one fixed overall deadline and disable automatic SDK retries.
2. Write one small signed test object through each restarted node, budgeting each request timeout from the remaining deadline.
3. Read every acknowledged test object back through every node and verify both payload bytes and version IDs.
4. Record the time to first usable S3 I/O separately from HTTP probe readiness, and remove the test objects after verification.

This check confirms sampled S3 read and write paths for the erasure sets reached by those keys. It does not prove that every erasure set has all drives online or can tolerate another node loss. Use the HTTP health endpoints for process liveness, external-dependency readiness, and reported quorum checks.
