---
title: "健康检查 API"
url: "/zh/operations/monitoring/healthcheck-probe/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/healthcheck-probe.rst
upstream_modified: true
---

<a id="api"></a>
<a id="healthcheck-api"></a>
<a id="minio-healthcheck-api"></a>

MinIO 提供无需身份验证的端点，用于探测节点在线状态以及集群 [高可用性](/zh/operations/concepts/erasure-coding/#minio-ec-parity)，从而执行简单健康检查。这些端点返回一个 HTTP 状态码，用于表示底层资源是否健康，或是否满足读写仲裁。MinIO 不会通过这些端点暴露任何其他数据。

<a id="id2" data-td-print-local></a>

## 原生探针与应用启动 {#native-probe}

SILO 内置 `silo healthcheck` 子命令，可直接探测本地 `/minio/health/*` HTTP 端点，无需在容器内提供 `curl`、`mc` 或 shell：

```shell
silo healthcheck [FLAGS] [live|ready|cluster|cluster-read]
```

- `CHECK` 选择探测目标端点：`live`（默认）、`ready`、`cluster` 或 `cluster-read`。
- `--address`（或 `MINIO_ADDRESS`，默认 `:9000`，空主机名解析为 `127.0.0.1`）指定目标 `HOST:PORT`；当 `--certs-dir` 中存在 `public.crt` 与 `private.key` 时自动切换为 HTTPS。
- `--url`（或 `MINIO_HEALTHCHECK_URL`）使用显式 `http[s]://HOST:PORT` 基址覆盖 `--address` 与 TLS 自动判定。
- `--maintenance` 仅适用于 `cluster`，附加 `?maintenance=true`，并在服务端返回 HTTP `412 Precondition Failed` 时以退出码 `1` 结束。
- `--timeout` 设置探测总超时（`live` 与 `ready` 默认 `5s`；`cluster` 与 `cluster-read` 默认 `15s`）。
- 全局参数 `--certs-dir`、`--json` 与 `--quiet` 控制证书查找与输出格式。探测健康时退出码为 `0`，其余情况均为 `1`。

`silo healthcheck ready` 调用 `/minio/health/ready`。该端点检查 HTTP 请求队列容量以及已配置的 KMS 和 `etcd` 可达性，在存储层和 IAM 完成加载前也可能返回 `200 OK`。这一行为保证了分布式节点的启动互联；Kubernetes 无头服务必须保留 `publishNotReadyAddresses: true`。不要将 `cluster` 配置为容器存活探针或节点互联的前置条件。

`-distroless` 容器镜像将内置 `HEALTHCHECK` 配置为 `/usr/bin/silo healthcheck ready`。因此，Docker Compose 的 `depends_on: condition: service_healthy` 仅确认该就绪探针通过，不代表 S3 数据面已可读写。即使改查 `cluster`，仍存在下文说明的远端磁盘重连窗口。需要立即访问对象的依赖应用必须执行有界超时的签名 S3 写入与回读检查，并在失败时中止启动或升级流程。请使用专用存储桶和唯一探测对象键，并在校验完成后清理。

## 节点存活 {#node-liveness}

使用以下端点测试 SILO 服务端 HTTP 监听器是否正在处理请求：

```shell
curl -I https://minio.example.net:9000/minio/health/live
```

将 `https://minio.example.net:9000` 替换为待检查服务端的 DNS 主机名和端口。

HTTP 监听器启动后，即使对象层尚未完成加载，`/minio/health/live` 也会立即返回 `200 OK`（存储初始化期间响应头包含 `x-minio-server-status: offline`）。当排队请求数超过 API 请求池容量上限时，该端点返回 `503 Service Unavailable`。由于存活检查失败在 Kubernetes 中会触发 Pod 重启，`/minio/health/live` 不访问任何外部系统（不访问 KMS，也不访问 `etcd`），避免在磁盘初始化缓慢或外部服务故障期间误重启容器。

存活探针仅检查当前客户端能否连通服务端 HTTP 监听器以及请求队列是否有余量。建议配置 Prometheus [告警](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)，使用 [指标 v3](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-cluster-metrics) 的 `minio_cluster_health_nodes_offline_count` 或 [指标 v2](/zh/operations/monitoring/metrics-v2/#minio-available-cluster-metrics) 的 `minio_cluster_nodes_offline_total` 检测集群离线节点。

## 节点就绪 {#node-readiness}

使用以下端点测试进程就绪状态及已配置的外部依赖：

```shell
curl -I https://minio.example.net:9000/minio/health/ready
```

将 `https://minio.example.net:9000` 替换为待检查服务端的 DNS 主机名和端口。

`/minio/health/ready` 检查与 `/minio/health/live` 相同的 HTTP 请求队列容量，并在配置了 KMS 或 `etcd` 时进一步验证 KMS 密钥生成与 `etcd` 健康读写。未配置 KMS 和 `etcd` 时，`/minio/health/ready` 与 `/minio/health/live` 走相同的检查路径。与 `/minio/health/live` 一样，`/minio/health/ready` 在对象层或 IAM 完成加载前也可返回 `200 OK`（附带 `x-minio-server-status: offline`），以便集群启动阶段完成对端节点发现。

<a id="id3" data-td-print-local></a>

<a id="minio-cluster-write-quorum"></a>

## 集群写仲裁 {#cluster-write-quorum}

使用以下端点测试 MinIO 集群是否具备 [写仲裁](/zh/operations/concepts/erasure-coding/#minio-ec-parity)：

```shell
curl -I https://minio.example.net:9000/minio/health/cluster
```

将 `https://minio.example.net:9000` 替换为待检查 MinIO 集群中某个节点的 DNS 主机名。 对于使用负载均衡器管理传入连接的集群，请指定负载均衡器的主机名。

返回 `200 OK` 表示 MinIO 集群当前有足够的 MinIO server 在线，可满足写仲裁。 返回 `503 Service Unavailable` 表示集群当前不具备写仲裁。

单靠 healthcheck probe 无法判断某个 MinIO server 是否离线，也无法判断其是否正在正常处理写操作。 它只能根据配置的 [纠删码校验值](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 判断当前是否有足够的 MinIO server 在线，以满足写仲裁要求。 建议配置 Prometheus [告警](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)，使用以下指标检测 MinIO 集群中的潜在问题或错误：

- `minio_cluster_nodes_offline_total`：在一个或多个 MinIO 节点离线时触发告警。
- `minio_node_drive_free_bytes`：在集群可用磁盘空间不足时触发告警。

<a id="id4" data-td-print-local></a>

## 集群读仲裁 {#cluster-read-quorum}

使用以下端点测试 MinIO 集群是否具备 [读仲裁](/zh/operations/concepts/erasure-coding/#minio-ec-parity)：

```shell
curl -I https://minio.example.net:9000/minio/health/cluster/read
```

将 `https://minio.example.net:9000` 替换为待检查 MinIO 集群中某个节点的 DNS 主机名。 对于使用负载均衡器管理传入连接的集群，请指定负载均衡器的主机名。

返回 `200 OK` 表示 MinIO 集群当前有足够的 MinIO server 在线，可满足读仲裁。 返回 `503 Service Unavailable` 表示集群当前不具备读仲裁。

单靠 healthcheck probe 无法判断某个 MinIO server 是否离线，也无法判断其是否正在正常处理读操作。 它只能根据配置的 [纠删码校验值](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 判断当前是否有足够的 MinIO server 在线，以满足读仲裁要求。 建议配置 Prometheus [告警](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)，使用 `minio_cluster_nodes_offline_total` 指标检测一个或多个 MinIO 节点是否离线。

<a id="id5" data-td-print-local></a>

## 集群维护检查 {#cluster-maintenance-check}

使用以下端点测试在将指定 MinIO server 下线维护时， MinIO 集群是否仍能同时维持 [读](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 和 [写](/zh/operations/concepts/erasure-coding/#minio-ec-parity)：

```shell
curl -I https://minio.example.net:9000/minio/health/cluster?maintenance=true
```

将 `https://minio.example.net:9000` 替换为待检查 MinIO 集群中某个节点的 DNS 主机名。 对于使用负载均衡器管理传入连接的集群，请指定负载均衡器的主机名。

返回 `200 OK` 表示 MinIO 集群当前有足够的 MinIO server 在线，可满足写仲裁。 返回 `412 Precondition Failed` 表示如果该 MinIO server 离线，集群将失去仲裁。

单靠 healthcheck probe 无法判断某个 MinIO server 是否离线。 它只能判断在该节点因维护而下线后，是否仍有足够的 MinIO server 在线，以根据配置的 [纠删码校验值](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 满足读写仲裁要求。 建议配置 Prometheus [告警](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)，使用 `minio_cluster_nodes_offline_total` 指标检测一个或多个 MinIO 节点是否离线。

## 重启后的就绪窗口 {#startup-readiness-window}

[SILO 20261109](/zh/blog/release/silo-20261109/) 保留这一机制：[集群健康检查实现](https://github.com/pgsty/silo/blob/d998292387ccf1d2907749e0fb1575ef5fb93fda/cmd/erasure-server-pool.go#L3162)根据各对端节点上报的磁盘状态评估仲裁。恢复业务流量前，请先检查两个集群端点，再验证真实 S3 读写。完整的探针规格见[健康检查探针语义](/zh/compatibility/feature/healthcheck/)。

上述 HTTP 健康端点均不能证明收到请求的节点在重启后已能立即服务对象读写。每个节点通过后台监控循环连接对端节点的远端纠删码磁盘。启动时未能连上的远端磁盘会在本节点保持未挂载状态，直到后续轮次重连成功。监控循环在每轮结束后等待 15 秒，因此 15 秒只是两次重连尝试之间的最短间隔，而非恢复耗时上限。

在远端磁盘尚未重连期间，该节点的 `/minio/health/live`、`/minio/health/ready`、两个 `/minio/health/cluster*` 端点、`mc admin info` 与 `mcli ready` 都可能报告健康。这是因为集群端点汇总各节点对自身本地磁盘的上报结果，而不检查当前接收节点已挂载哪些远端磁盘。在此窗口内，经由该节点的 `PUT` 可能返回 `503 SlowDownWrite`，读取其他节点刚写入的对象也可能在远端磁盘重连完成前失败。

升级与故障切换自动化流程必须以有界超时的 S3 数据面检查作为放行门槛，而不能仅依赖 HTTP 健康端点：

1. 设置固定的总截止时间，并禁用 SDK 自动重试。
2. 经由每个重启节点各写入一个签名探测小对象，按剩余截止时间分配单次请求超时。
3. 经由每个节点回读所有已确认写入的探测对象，校验字节内容和版本 ID。
4. 将“首次可用 S3 I/O 耗时”与 HTTP 探针就绪状态分开记录，并在校验完成后清理探测对象。

该检查可验证探测对象键所命中纠删集在当时的抽样 S3 读写路径，但不证明所有纠删集磁盘均已齐全或具备再次容忍节点丢失的余量。HTTP 健康端点仍应用于其设计用途：进程存活、外部依赖就绪与上报仲裁检查。
