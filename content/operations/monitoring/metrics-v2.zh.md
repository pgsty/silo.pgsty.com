---
title: "Metrics version 2"
url: "/zh/operations/monitoring/metrics-v2/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/metrics-v2.rst
upstream_modified: true
---

<a id="metrics-version-2"></a>
<a id="minio-metrics-v2"></a>

MinIO 使用 [Prometheus 数据模型](https://prometheus.io/docs/concepts/data_model/) 发布集群和节点指标。你可以使用任意抓取工具从 SILO 拉取指标数据，以执行分析和配置告警。

**[SILO 20261109](/zh/blog/release/silo-20261109/) / [Console 2.7.0](/zh/blog/release/console-2.7.0/)：** 新部署以及 Console 2.7.0 的 Metrics 页面建议抓取 [Metrics V3](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)（通过 [mcli 20261109](/zh/blog/release/mcli-20261109/) 执行 `mcli admin prometheus generate ALIAS --api-version v3` 生成配置；参见 [Console 2.7.0 Metrics V3 映射参考](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/metrics-v3.md)）。在 SILO 20261109 中，复制工作协程指标在复制工作池不存在时不会触发 panic，并继续保留历史均值和峰值计数（[`099b7ddf3`](https://github.com/pgsty/silo/commit/099b7ddf37b5a5e6d672604f1190fbab26448c20)）；实时批处理作业指标保留暂停原因以及跳过或拒绝计数（[#325](https://github.com/pgsty/silo/issues/325)）。

<a id="version-2" data-td-print-local></a>

## Version 2 端点 {#version-2-endpoints}

Metrics version 2 将指标划分为以下三个类别：

- [集群指标](/zh/operations/monitoring/metrics-v2/#minio-available-cluster-metrics)
- [存储桶指标](/zh/operations/monitoring/metrics-v2/#minio-available-bucket-metrics)
- [资源指标](/zh/operations/monitoring/metrics-v2/#minio-available-resource-metrics)

每个 v2 端点都会返回其所属类别的全部指标。例如，抓取以下端点会返回所有集群指标：

```shell
http://HOSTNAME:PORT/minio/v2/metrics/cluster
```

仅访问基础端点 `/minio/v2/metrics/` 也会返回集群指标。

**如需更灵活的抓取方式和更完整的指标集合，请使用 [metrics version 3](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)。**

> 现有部署仍可继续使用 version 2 [指标](#minio-metrics-v2) 和 [Grafana 仪表板](/zh/operations/monitoring/grafana/#minio-grafana)。

<a id="minio-grafana" data-td-print-local></a>

## MinIO Grafana 仪表板 {#minio-grafana-dashboard}

MinIO 提供两个 [Grafana 仪表板](/zh/operations/monitoring/grafana/#minio-grafana)，用于可视化 v2 指标。有关为 Grafana 配置兼容 Prometheus 数据源的完整说明，请参见 [Prometheus 关于 Grafana 支持的文档](https://prometheus.io/docs/visualization/grafana/)。

<a id="id2" data-td-print-local></a>

## 可用的 version 2 指标 {#available-version-2-metrics}

以下各节描述 version 2 的端点与指标。

{{< tabs group="tab1-tab2-tab3" >}}
{{< tab label="集群指标" value="tab1" >}}
你可以使用以下 URL 端点抓取[集群级指标](/zh/operations/monitoring/metrics-v2/#minio-available-cluster-metrics)：

```shell
http://HOSTNAME:PORT/minio/v2/metrics/cluster
```

将 `HOSTNAME:PORT` 替换为部署的 <abbr title="Fully Qualified Domain Name">FQDN</abbr> 与端口。对于使用负载均衡器管理节点间连接的部署，请指定负载均衡器地址。
{{< /tab >}}
{{< tab label="存储桶指标" value="tab2" >}}
> [!NOTE]
> **存储桶端点变更与上限**
>
> - **RELEASE.2023-07-21T21-12-44Z / RELEASE.2023-08-31T15-31-16Z：** 存储桶指标迁移至独立端点。
> - **RELEASE.2025-03-12T17-29-24Z：** 出于性能原因，v2 存储桶指标最多返回 100 个存储桶。存储桶数量超过 100 时，请改用 [v3 指标](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts-available-metrics)。

使用以下 URL 端点抓取[存储桶级指标](/zh/operations/monitoring/metrics-v2/#minio-available-bucket-metrics)：

```shell
http://HOSTNAME:PORT/minio/v2/metrics/bucket
```

将 `HOSTNAME:PORT` 替换为部署的 <abbr title="Fully Qualified Domain Name">FQDN</abbr> 与端口。对于使用负载均衡器管理节点间连接的部署，请指定负载均衡器地址。
{{< /tab >}}
{{< tab label="资源指标" value="tab3" >}}
> [!NOTE]
> **新增: RELEASE.2023-10-07T15-07-38Z**

你可以使用以下 URL 端点抓取[资源指标](/zh/operations/monitoring/metrics-v2/#minio-available-resource-metrics)：

```shell
http://HOSTNAME:PORT/minio/v2/metrics/resource
```

将 `HOSTNAME:PORT` 替换为部署的 <abbr title="Fully Qualified Domain Name">FQDN</abbr> 与端口。对于使用负载均衡器管理节点间连接的部署，请指定负载均衡器地址。
{{< /tab >}}
{{< /tabs >}}

- [集群指标](/zh/operations/monitoring/metrics-v2/#minio-available-cluster-metrics)
- [存储桶指标](/zh/operations/monitoring/metrics-v2/#minio-available-bucket-metrics)
- [资源指标](/zh/operations/monitoring/metrics-v2/#minio-available-resource-metrics)

<a id="minio-available-cluster-metrics"></a>

### 集群指标 {#cluster-metrics}

SILO 在集群级别采集以下指标。指标可能带有一个或多个标签（例如计算该指标的节点标识）。

每次采集可从任意一个 SILO 节点通过以下 URL 拉取：

```shell
https://HOSTNAME:PORT/minio/v2/metrics/cluster
```

将 `HOSTNAME:PORT` 替换为部署的主机名和端口；部署前存在负载均衡器时，请填写负载均衡器地址。

#### 审计指标 {#audit-metrics}

| 名称                              | 说明                               |
| --------------------------------- | ---------------------------------- |
| `minio_audit_failed_messages`     | 自启动以来发送失败的审计消息总数。 |
| `minio_audit_target_queue_length` | 目标队列中待发送的审计消息数。     |
| `minio_audit_total_messages`      | 自启动以来已发送的审计消息总数。   |
{.wide .expand}

#### 集群容量指标 {#cluster-capacity-metrics}

| 名称                                         | 说明                             |
| -------------------------------------------- | -------------------------------- |
| `minio_cluster_capacity_raw_free_bytes`      | 集群在线裸盘剩余容量（字节）。   |
| `minio_cluster_capacity_raw_total_bytes`     | 集群在线裸盘总容量（字节）。     |
| `minio_cluster_capacity_usable_free_bytes`   | 集群在线可用剩余容量（字节）。   |
| `minio_cluster_capacity_usable_total_bytes`  | 集群在线可用总容量（字节）。     |
| `minio_cluster_objects_size_distribution`    | 集群对象大小分布。               |
| `minio_cluster_objects_version_distribution` | 集群对象版本数分布。             |
| `minio_cluster_usage_object_total`           | 集群对象总数。                   |
| `minio_cluster_usage_total_bytes`            | 集群已用字节总数。               |
| `minio_cluster_usage_version_total`          | 集群对象版本总数（含删除标记）。 |
| `minio_cluster_usage_deletemarker_total`     | 集群删除标记总数。               |
| `minio_cluster_bucket_total`                 | 集群存储桶总数。                 |
{.wide .expand}

#### 集群磁盘指标 {#cluster-drive-metrics}

| 名称                                | 说明               |
| ----------------------------------- | ------------------ |
| `minio_cluster_drive_offline_total` | 集群离线磁盘总数。 |
| `minio_cluster_drive_online_total`  | 集群在线磁盘总数。 |
| `minio_cluster_drive_total`         | 集群磁盘总数。     |
{.wide .expand}

#### 集群 ILM 指标 {#cluster-ilm-metrics}

| 名称                                      | 说明                                   |
| ----------------------------------------- | -------------------------------------- |
| `minio_cluster_ilm_transitioned_bytes`    | 已分层转移到远端存储层的总字节数。     |
| `minio_cluster_ilm_transitioned_objects`  | 已分层转移到远端存储层的对象总数。     |
| `minio_cluster_ilm_transitioned_versions` | 已分层转移到远端存储层的对象版本总数。 |
{.wide .expand}

#### 集群 KMS 指标 {#cluster-kms-metrics}

| 名称                                | 说明                                      |
| ----------------------------------- | ----------------------------------------- |
| `minio_cluster_kms_online`          | KMS 是否在线（1=在线，0=离线）。          |
| `minio_cluster_kms_request_error`   | 返回客户端错误（HTTP 4xx）的 KMS 请求数。 |
| `minio_cluster_kms_request_failure` | 返回内部错误（HTTP 5xx）的 KMS 请求数。   |
| `minio_cluster_kms_request_success` | 成功的 KMS 请求数。                       |
| `minio_cluster_kms_uptime`          | KMS 运行时长（秒）。                      |
{.wide .expand}

#### 集群健康指标 {#cluster-health-metrics}

| 名称                                              | 说明                               |
| ------------------------------------------------- | ---------------------------------- |
| `minio_cluster_nodes_offline_total`               | 离线节点总数。                     |
| `minio_cluster_nodes_online_total`                | 在线节点总数。                     |
| `minio_cluster_write_quorum`                      | 所有存储池与纠删集中的最大写仲裁。 |
| `minio_cluster_health_status`                     | 当前集群健康状态。                 |
| `minio_cluster_health_erasure_set_healing_drives` | 纠删集中正在自愈的磁盘数。         |
| `minio_cluster_health_erasure_set_online_drives`  | 纠删集中在线磁盘数。               |
| `minio_cluster_health_erasure_set_read_quorum`    | 纠删集读仲裁。                     |
| `minio_cluster_health_erasure_set_write_quorum`   | 纠删集写仲裁。                     |
| `minio_cluster_health_erasure_set_status`         | 纠删集当前健康状态。               |
{.wide .expand}

#### 集群复制指标 {#cluster-replication-metrics}

标注为“仅站点复制”的指标仅在配置了[站点复制](/zh/operations/replication/multi-site-replication/)的部署上产出；对于配置了[存储桶复制](/zh/administration/bucket-replication/)或[批量复制](/zh/administration/batch-framework-job-replicate/)的部署，相应指标会在[存储桶指标](#bucket-metrics)端点下产出。

| 名称                                                                 | 说明                                                           |
| -------------------------------------------------------------------- | -------------------------------------------------------------- |
| `minio_cluster_replication_last_hour_failed_bytes`                   | （仅站点复制）最近一完整小时内至少复制失败一次的字节总数。     |
| `minio_cluster_replication_last_hour_failed_count`                   | （仅站点复制）最近一完整小时内复制失败的对象总数。             |
| `minio_cluster_replication_last_minute_failed_bytes`                 | 上一完整分钟内至少复制失败一次的字节总数。                     |
| `minio_cluster_replication_last_minute_failed_count`                 | 上一完整分钟内复制失败的对象总数。                             |
| `minio_cluster_replication_total_failed_bytes`                       | （仅站点复制）自启动以来至少复制失败一次的字节总数。           |
| `minio_cluster_replication_total_failed_count`                       | （仅站点复制）自启动以来复制失败的对象总数。                   |
| `minio_cluster_replication_received_bytes`                           | （仅站点复制）从其他源集群复制到本集群的总字节数。             |
| `minio_cluster_replication_received_count`                           | （仅站点复制）从其他源集群复制到本集群的对象总数。             |
| `minio_cluster_replication_sent_bytes`                               | （仅站点复制）已复制到目标集群的总字节数。                     |
| `minio_cluster_replication_sent_count`                               | （仅站点复制）已复制到目标集群的对象总数。                     |
| `minio_cluster_replication_credential_errors`                        | （仅站点复制）自启动以来的复制凭据错误总数。                   |
| `minio_cluster_replication_proxied_get_requests_total`               | （仅站点复制）代理转发至复制目标的 GET 请求总数。              |
| `minio_cluster_replication_proxied_head_requests_total`              | （仅站点复制）代理转发至复制目标的 HEAD 请求总数。             |
| `minio_cluster_replication_proxied_delete_tagging_requests_total`    | （仅站点复制）代理转发至复制目标的 DELETE tagging 请求总数。   |
| `minio_cluster_replication_proxied_get_tagging_requests_total`       | （仅站点复制）代理转发至复制目标的 GET tagging 请求总数。      |
| `minio_cluster_replication_proxied_put_tagging_requests_total`       | （仅站点复制）代理转发至复制目标的 PUT tagging 请求总数。      |
| `minio_cluster_replication_proxied_get_requests_failures`            | （仅站点复制）代理转发至复制目标的 GET 请求失败数。            |
| `minio_cluster_replication_proxied_head_requests_failures`           | （仅站点复制）代理转发至复制目标的 HEAD 请求失败数。           |
| `minio_cluster_replication_proxied_delete_tagging_requests_failures` | （仅站点复制）代理转发至复制目标的 DELETE tagging 请求失败数。 |
| `minio_cluster_replication_proxied_get_tagging_requests_failures`    | （仅站点复制）代理转发至复制目标的 GET tagging 请求失败数。    |
| `minio_cluster_replication_proxied_put_tagging_requests_failures`    | （仅站点复制）代理转发至复制目标的 PUT tagging 请求失败数。    |
{.wide .expand}

#### 节点复制指标 {#node-replication-metrics}

在配置了[站点复制](/zh/operations/replication/multi-site-replication/)、[存储桶复制](/zh/administration/bucket-replication/)或[批量复制](/zh/administration/batch-framework-job-replicate/)时反映节点级复制队列与链路状态。

| 名称                                                    | 说明                                       |
| ------------------------------------------------------- | ------------------------------------------ |
| `minio_node_replication_current_active_workers`         | 当前活跃复制工作协程数。                   |
| `minio_node_replication_average_active_workers`         | 活跃复制工作协程平均数。                   |
| `minio_node_replication_max_active_workers`             | 自启动以来观测到的最大活跃复制工作协程数。 |
| `minio_node_replication_link_online`                    | 复制链路是否在线（1=在线，0=离线）。       |
| `minio_node_replication_link_offline_duration_seconds`  | 自上次离线事件以来复制链路持续离线秒数。   |
| `minio_node_replication_link_downtime_duration_seconds` | 自启动以来复制链路累计停机秒数。           |
| `minio_node_replication_average_link_latency_ms`        | 复制链路平均延迟（毫秒）。                 |
| `minio_node_replication_max_link_latency_ms`            | 自启动以来复制链路最大延迟（毫秒）。       |
| `minio_node_replication_current_link_latency_ms`        | 当前复制链路延迟（毫秒）。                 |
| `minio_node_replication_current_transfer_rate`          | 当前复制传输速率（字节/秒）。              |
| `minio_node_replication_average_transfer_rate`          | 平均复制传输速率（字节/秒）。              |
| `minio_node_replication_max_transfer_rate`              | 自启动以来的最大复制传输速率（字节/秒）。  |
| `minio_node_replication_last_minute_queued_count`       | 上一完整分钟排队复制的对象总数。           |
| `minio_node_replication_last_minute_queued_bytes`       | 上一完整分钟排队复制的字节总数。           |
| `minio_node_replication_average_queued_count`           | 自启动以来排队等待复制的平均对象数。       |
| `minio_node_replication_average_queued_bytes`           | 自启动以来排队等待复制的平均字节数。       |
| `minio_node_replication_max_queued_bytes`               | 自启动以来排队等待复制的最大字节数。       |
| `minio_node_replication_max_queued_count`               | 自启动以来排队等待复制的最大对象数。       |
| `minio_node_replication_recent_backlog_count`           | 最近 5 分钟内复制积压队列中的对象总数。    |
{.wide .expand}

#### 自愈指标 {#healing-metrics}

| 名称                                         | 说明                               |
| -------------------------------------------- | ---------------------------------- |
| `minio_heal_objects_errors_total`            | 当前自愈轮次中自愈失败的对象数。   |
| `minio_heal_objects_heal_total`              | 当前自愈轮次中已完成自愈的对象数。 |
| `minio_heal_objects_total`                   | 当前自愈轮次中已扫描的对象总数。   |
| `minio_heal_time_last_activity_nano_seconds` | 距最近一次自愈活动的时间（纳秒）。 |
{.wide .expand}

#### 节点间网络指标 {#inter-node-metrics}

| 名称                                      | 说明                            |
| ----------------------------------------- | ------------------------------- |
| `minio_inter_node_traffic_dial_avg_time`  | 节点间 TCP 建连平均耗时。       |
| `minio_inter_node_traffic_dial_errors`    | 节点间 TCP 建连超时与错误总数。 |
| `minio_inter_node_traffic_errors_total`   | 失败的节点间调用总数。          |
| `minio_inter_node_traffic_received_bytes` | 从其他对端节点接收的总字节数。  |
| `minio_inter_node_traffic_sent_bytes`     | 发送给其他对端节点的总字节数。  |
{.wide .expand}

#### 存储桶通知指标 {#bucket-notification-metrics}

| 名称                                           | 说明                                                                                            |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `minio_notify_current_send_in_progress`        | 向所有目标并发发送中的调用数（已弃用，请改用 `minio_notify_target_current_send_in_progress`）。 |
| `minio_notify_events_errors_total`             | 发送至目标失败的事件数（已弃用，请改用 `minio_notify_target_failed_events`）。                  |
| `minio_notify_events_sent_total`               | 已发送至目标的事件总数（已弃用，请改用 `minio_notify_target_total_events`）。                   |
| `minio_notify_events_skipped_total`            | 因内存队列已满而跳过发送的事件数。                                                              |
| `minio_notify_target_current_send_in_progress` | 向指定目标并发发送中的异步调用数。                                                              |
| `minio_notify_target_queue_length`             | 指定目标 `queue_dir` 中当前暂存的事件数。                                                       |
| `minio_notify_target_total_events`             | 已发送或已入队至指定目标的事件总数。                                                            |
{.wide .expand}

#### S3 API 请求指标 {#s3-api-request-metrics}

| 名称                                          | 说明                                   |
| --------------------------------------------- | -------------------------------------- |
| `minio_s3_requests_4xx_errors_total`          | 返回 4xx 错误的 S3 请求总数。          |
| `minio_s3_requests_5xx_errors_total`          | 返回 5xx 错误的 S3 请求总数。          |
| `minio_s3_requests_canceled_total`            | 客户端取消的 S3 请求总数。             |
| `minio_s3_requests_errors_total`              | 返回 4xx 和 5xx 错误的 S3 请求总数。   |
| `minio_s3_requests_incoming_total`            | 当前传入 S3 请求数。                   |
| `minio_s3_requests_inflight_total`            | 当前正在处理的 S3 请求总数。           |
| `minio_s3_requests_rejected_auth_total`       | 因身份验证失败而被拒绝的 S3 请求总数。 |
| `minio_s3_requests_rejected_header_total`     | 因请求头无效而被拒绝的 S3 请求总数。   |
| `minio_s3_requests_rejected_invalid_total`    | 无效 S3 请求总数。                     |
| `minio_s3_requests_rejected_timestamp_total`  | 因时间戳无效而被拒绝的 S3 请求总数。   |
| `minio_s3_requests_total`                     | S3 请求总数。                          |
| `minio_s3_requests_waiting_total`             | 等待队列中的 S3 请求数。               |
| `minio_s3_requests_ttfb_seconds_distribution` | 各 API 调用首字节耗时（秒）分布。      |
| `minio_s3_traffic_received_bytes`             | S3 接收字节总数。                      |
| `minio_s3_traffic_sent_bytes`                 | S3 发送字节总数。                      |
{.wide .expand}

#### 软件版本指标 {#software-metrics}

| 名称                          | 说明                        |
| ----------------------------- | --------------------------- |
| `minio_software_commit_info`  | 服务端发布的 Git 提交哈希。 |
| `minio_software_version_info` | 服务端发布版本标签。        |
{.wide .expand}

#### 磁盘指标 {#drive-metrics}

| 名称                                   | 说明                                     |
| -------------------------------------- | ---------------------------------------- |
| `minio_node_drive_free_bytes`          | 磁盘可用存储空间（字节）。               |
| `minio_node_drive_free_inodes`         | 磁盘空闲 inode 总数。                    |
| `minio_node_drive_latency_us`          | 最近一分钟磁盘存储操作平均延迟（微秒）。 |
| `minio_node_drive_offline_total`       | 本节点离线磁盘总数。                     |
| `minio_node_drive_online_total`        | 本节点在线磁盘总数。                     |
| `minio_node_drive_total`               | 本节点磁盘总数。                         |
| `minio_node_drive_total_bytes`         | 磁盘总存储空间（字节）。                 |
| `minio_node_drive_used_bytes`          | 磁盘已用存储空间（字节）。               |
| `minio_node_drive_errors_timeout`      | 自启动以来磁盘超时错误总数。             |
| `minio_node_drive_errors_ioerror`      | 自启动以来磁盘 I/O 错误总数。            |
| `minio_node_drive_errors_availability` | 自启动以来磁盘 I/O 错误与超时总数。      |
| `minio_node_drive_io_waiting`          | 磁盘上等待中的 I/O 操作总数。            |
{.wide .expand}

#### 身份与访问管理（IAM）指标 {#identity-and-access-management-iam-metrics}

| 名称                                       | 说明                                    |
| ------------------------------------------ | --------------------------------------- |
| `minio_node_iam_last_sync_duration_millis` | 最近一次成功 IAM 同步耗时（毫秒）。     |
| `minio_node_iam_since_last_sync_millis`    | 距最近一次成功 IAM 同步的时间（毫秒）。 |
| `minio_node_iam_sync_failures`             | 自启动以来失败的 IAM 同步次数。         |
| `minio_node_iam_sync_successes`            | 自启动以来成功的 IAM 同步次数。         |
{.wide .expand}

#### 信息生命周期管理（ILM）指标 {#information-lifecycle-management-ilm-metrics}

| 名称                                                         | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| ------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `minio_node_ilm_expiry_pending_tasks`                        | 队列中等待执行的 ILM 过期任务数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `minio_node_ilm_transition_active_tasks`                     | 当前正在执行的 ILM 分层转移任务数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `minio_node_ilm_transition_pending_tasks`                    | 队列中等待执行的 ILM 分层转移任务数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `minio_node_ilm_transition_missed_immediate_tasks`           | 错过的即时 ILM 分层转移任务数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `minio_node_ilm_versions_scanned`                            | 自启动以来检查 ILM 动作的对象版本总数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `minio_node_ilm_expiry_incomplete_total`                     | 自启动以来未能移除目标而结束的 ILM 过期尝试总数，按 `reason` 标签区分：`not_applicable`（在对象锁下重验时规则不再适用）、`locked`（受 Object Lock 保护）、`history_unavailable`（无法取得权威版本历史）、`error`（其他故障）。整键清除还会记录 `tier_unsupported`（存在远端分层版本）、`budget`（移除部分版本后达到单轮预算上限，下一轮继续）和 `changed`（匹配的最新版本已变化），见[精确 key 删除](/zh/blog/design/ilm-delete-all-exact-key/)。`tier_unsupported_skipped` 统计扫描器因本池存在远端分层版本而跳过入队的观测次数（每盘每轮扫描计数一次，不等于对象键数或清除次数），见[多池生命周期过期](/zh/blog/design/multi-pool-lifecycle-expiry/#fix)。 |
| `minio_node_ilm_action_count_delete_action`                  | 自启动以来删除对象的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `minio_node_ilm_action_count_delete_version_action`          | 自启动以来删除指定版本的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `minio_node_ilm_action_count_transition_action`              | 自启动以来分层转移对象的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| `minio_node_ilm_action_count_transition_version_action`      | 自启动以来分层转移指定对象版本的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `minio_node_ilm_action_count_delete_restored_action`         | 自启动以来删除临时恢复对象副本的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `minio_node_ilm_action_count_delete_restored_version_action` | 自启动以来删除临时恢复版本副本的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| `minio_node_ilm_action_count_delete_all_versions_action`     | 自启动以来删除全部版本的生命周期检查结果计数。                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
{.wide .expand}

#### 远端分层指标 {#tier-metrics}

| 名称                                             | 说明                                           |
| ------------------------------------------------ | ---------------------------------------------- |
| `minio_node_tier_tier_ttlb_seconds_distribution` | 从远端存储层下载对象至末字节的耗时分布（秒）。 |
| `minio_node_tier_requests_success`               | 从远端存储层成功下载对象的请求数。             |
| `minio_node_tier_requests_failure`               | 从远端存储层下载对象失败的请求数。             |
{.wide .expand}

#### 系统指标 {#system-metrics}

| 名称                                       | 说明                                                                   |
| ------------------------------------------ | ---------------------------------------------------------------------- |
| `minio_node_file_descriptor_limit_total`   | 进程可打开文件描述符总数上限。                                         |
| `minio_node_file_descriptor_open_total`    | 进程当前打开的文件描述符总数。                                         |
| `minio_node_go_routine_total`              | 当前运行中的 Goroutine 总数。                                          |
| `minio_node_io_rchar_bytes`                | 进程从底层存储（含缓存）读取的总字节数（`/proc/[pid]/io` `rchar`）。   |
| `minio_node_io_read_bytes`                 | 进程从底层存储读取的总字节数（`/proc/[pid]/io` `read_bytes`）。        |
| `minio_node_io_wchar_bytes`                | 进程向底层存储（含页缓存）写入的总字节数（`/proc/[pid]/io` `wchar`）。 |
| `minio_node_io_write_bytes`                | 进程向底层存储写入的总字节数（`/proc/[pid]/io` `write_bytes`）。       |
| `minio_node_process_cpu_total_seconds`     | 进程累计消耗的用户态与内核态 CPU 秒数。                                |
| `minio_node_process_resident_memory_bytes` | 常驻内存（RSS）大小（字节）。                                          |
| `minio_node_process_virtual_memory_bytes`  | 虚拟内存大小（字节）。                                                 |
| `minio_node_process_starttime_seconds`     | 节点进程启动时间（自 Unix 纪元起的秒数）。                             |
| `minio_node_process_uptime_seconds`        | 节点进程运行时长（秒）。                                               |
{.wide .expand}

#### 扫描器指标 {#scanner-metrics}

| 名称                                       | 说明                                         |
| ------------------------------------------ | -------------------------------------------- |
| `minio_node_scanner_bucket_scans_finished` | 自启动以来已完成的存储桶扫描次数。           |
| `minio_node_scanner_bucket_scans_started`  | 自启动以来已启动的存储桶扫描次数。           |
| `minio_node_scanner_directories_scanned`   | 自启动以来已扫描的目录总数。                 |
| `minio_node_scanner_objects_scanned`       | 自启动以来已扫描的唯一对象总数。             |
| `minio_node_scanner_versions_scanned`      | 自启动以来已扫描的对象版本总数。             |
| `minio_node_syscall_read_total`            | 读系统调用总数（`/proc/[pid]/io` `syscr`）。 |
| `minio_node_syscall_write_total`           | 写系统调用总数（`/proc/[pid]/io` `syscw`）。 |
| `minio_usage_last_activity_nano_seconds`   | 距最近一次扫描活动的时间（纳秒）。           |
{.wide .expand}

> [!NOTE]
> **变更: RELEASE.2025-03-12T17-29-24Z**
>
> 出于性能原因，v2 指标最多返回 100 个存储桶。如果需要覆盖更多存储桶的指标，请改用 [v3 指标](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts-available-metrics)。

<a id="minio-available-bucket-metrics"></a>

### 存储桶指标 {#bucket-metrics}

SILO 在存储桶级别采集以下指标。每个指标包含 `bucket` 标签用于标识存储桶，并可能包含计算节点等附加标签。

每次采集可从任意一个 SILO 节点通过以下 URL 拉取：

```shell
https://HOSTNAME:PORT/minio/v2/metrics/bucket
```

将 `HOSTNAME:PORT` 替换为部署的主机名和端口；部署前存在负载均衡器时，请填写负载均衡器地址。

#### 分布指标 {#distribution-metrics}

| 名称                                        | 说明                                       |
| ------------------------------------------- | ------------------------------------------ |
| `minio_bucket_objects_size_distribution`    | 存储桶内对象大小分布（含存储桶名称标签）。 |
| `minio_bucket_objects_version_distribution` | 存储桶内对象按版本数量的分布。             |
{.wide .expand}

#### 复制指标 {#replication-metrics}

以下指标仅在配置了[存储桶复制](/zh/administration/bucket-replication/)或[批量复制](/zh/administration/batch-framework-job-replicate/)的部署上产出；对于配置了[站点复制](/zh/operations/replication/multi-site-replication/)的部署，对应指标在[集群指标](#cluster-metrics)端点下产出。

| 名称                                                                | 说明                                             |
| ------------------------------------------------------------------- | ------------------------------------------------ |
| `minio_bucket_replication_last_minute_failed_bytes`                 | 上一完整分钟内至少复制失败一次的字节总数。       |
| `minio_bucket_replication_last_minute_failed_count`                 | 上一完整分钟内复制失败的对象总数。               |
| `minio_bucket_replication_last_hour_failed_bytes`                   | 最近一完整小时内至少复制失败一次的字节总数。     |
| `minio_bucket_replication_last_hour_failed_count`                   | 最近一完整小时内复制失败的对象总数。             |
| `minio_bucket_replication_total_failed_bytes`                       | 自启动以来至少复制失败一次的字节总数。           |
| `minio_bucket_replication_total_failed_count`                       | 自启动以来复制失败的对象总数。                   |
| `minio_bucket_replication_latency_ms`                               | 复制延迟（毫秒）。                               |
| `minio_bucket_replication_received_bytes`                           | 从其他源存储桶复制到本桶的总字节数。             |
| `minio_bucket_replication_received_count`                           | 从其他源存储桶复制到本桶的对象总数。             |
| `minio_bucket_replication_sent_bytes`                               | 已复制到目标存储桶的总字节数。                   |
| `minio_bucket_replication_sent_count`                               | 已复制到目标存储桶的对象总数。                   |
| `minio_bucket_replication_credential_errors`                        | 自启动以来的复制凭据错误总数。                   |
| `minio_bucket_replication_proxied_get_requests_total`               | 代理转发至复制目标的 GET 请求总数。              |
| `minio_bucket_replication_proxied_head_requests_total`              | 代理转发至复制目标的 HEAD 请求总数。             |
| `minio_bucket_replication_proxied_delete_tagging_requests_total`    | 代理转发至复制目标的 DELETE tagging 请求总数。   |
| `minio_bucket_replication_proxied_get_tagging_requests_total`       | 代理转发至复制目标的 GET tagging 请求总数。      |
| `minio_bucket_replication_proxied_put_tagging_requests_total`       | 代理转发至复制目标的 PUT tagging 请求总数。      |
| `minio_bucket_replication_proxied_get_requests_failures`            | 代理转发至复制目标的 GET 请求失败数。            |
| `minio_bucket_replication_proxied_head_requests_failures`           | 代理转发至复制目标的 HEAD 请求失败数。           |
| `minio_bucket_replication_proxied_delete_tagging_requests_failures` | 代理转发至复制目标的 DELETE tagging 请求失败数。 |
| `minio_bucket_replication_proxied_get_tagging_requests_failures`    | 代理转发至复制目标的 GET tagging 请求失败数。    |
| `minio_bucket_replication_proxied_put_tagging_requests_failures`    | 代理转发至复制目标的 PUT tagging 请求失败数。    |
{.wide .expand}

#### 流量指标 {#traffic-metrics}

| 名称                                  | 说明                             |
| ------------------------------------- | -------------------------------- |
| `minio_bucket_traffic_received_bytes` | 该存储桶接收的 S3 流量总字节数。 |
| `minio_bucket_traffic_sent_bytes`     | 该存储桶发送的 S3 流量总字节数。 |
{.wide .expand}

#### 用量指标 {#usage-metrics}

| 名称                                    | 说明                         |
| --------------------------------------- | ---------------------------- |
| `minio_bucket_usage_object_total`       | 对象总数。                   |
| `minio_bucket_usage_version_total`      | 对象版本总数（含删除标记）。 |
| `minio_bucket_usage_deletemarker_total` | 删除标记总数。               |
| `minio_bucket_usage_total_bytes`        | 存储桶总大小（字节）。       |
| `minio_bucket_quota_total_bytes`        | 存储桶配额大小（字节）。     |
{.wide .expand}

#### 请求指标 {#requests-metrics}

| 名称                                              | 说明                              |
| ------------------------------------------------- | --------------------------------- |
| `minio_bucket_requests_4xx_errors_total`          | 存储桶 4xx 错误 S3 请求总数。     |
| `minio_bucket_requests_5xx_errors_total`          | 存储桶 5xx 错误 S3 请求总数。     |
| `minio_bucket_requests_inflight_total`            | 存储桶当前正在处理的 S3 请求数。  |
| `minio_bucket_requests_total`                     | 存储桶 S3 请求总数。              |
| `minio_bucket_requests_canceled_total`            | 客户端取消的存储桶 S3 请求总数。  |
| `minio_bucket_requests_ttfb_seconds_distribution` | 存储桶各 API 调用首字节耗时分布。 |
{.wide .expand}

<a id="minio-available-resource-metrics"></a>

### 资源指标 {#resource-metrics}

SILO 在节点级别采集以下资源指标。每个指标包含 `server` 标签用于标识所属节点，并可能包含磁盘路径、网卡名称等附加标签。

每次采集可从任意一个 SILO 节点通过以下 URL 拉取：

```shell
https://HOSTNAME:PORT/minio/v2/metrics/resource
```

将 `HOSTNAME:PORT` 替换为部署的主机名和端口；部署前存在负载均衡器时，请填写负载均衡器地址。

#### 磁盘资源指标 {#drive-resource-metrics}

| 名称                                 | 说明                           |
| ------------------------------------ | ------------------------------ |
| `minio_node_drive_total_bytes`       | 磁盘总字节数。                 |
| `minio_node_drive_used_bytes`        | 磁盘已用字节数。               |
| `minio_node_drive_total_inodes`      | 磁盘总 inode 数。              |
| `minio_node_drive_used_inodes`       | 磁盘已用 inode 数。            |
| `minio_node_drive_reads_per_sec`     | 磁盘每秒读次数。               |
| `minio_node_drive_reads_kb_per_sec`  | 磁盘每秒读取千字节数。         |
| `minio_node_drive_reads_await`       | 磁盘读请求平均服务时间。       |
| `minio_node_drive_writes_per_sec`    | 磁盘每秒写次数。               |
| `minio_node_drive_writes_kb_per_sec` | 磁盘每秒写入千字节数。         |
| `minio_node_drive_writes_await`      | 磁盘写请求平均服务时间。       |
| `minio_node_drive_perc_util`         | 自启动以来磁盘繁忙时间百分比。 |
{.wide .expand}

#### 网络接口指标 {#network-interface-metrics}

| 名称                          | 说明                             |
| ----------------------------- | -------------------------------- |
| `minio_node_if_rx_bytes`      | 60 秒内网卡接收字节数。          |
| `minio_node_if_rx_bytes_avg`  | 自启动以来 60 秒接收字节均值。   |
| `minio_node_if_rx_bytes_max`  | 自启动以来 60 秒接收字节最大值。 |
| `minio_node_if_rx_errors`     | 60 秒内接收错误数。              |
| `minio_node_if_rx_errors_avg` | 60 秒接收错误均值。              |
| `minio_node_if_rx_errors_max` | 60 秒接收错误最大值。            |
| `minio_node_if_tx_bytes`      | 60 秒内网卡发送字节数。          |
| `minio_node_if_tx_bytes_avg`  | 60 秒发送字节均值。              |
| `minio_node_if_tx_bytes_max`  | 60 秒发送字节最大值。            |
| `minio_node_if_tx_errors`     | 60 秒内发送错误数。              |
| `minio_node_if_tx_errors_avg` | 60 秒发送错误均值。              |
| `minio_node_if_tx_errors_max` | 60 秒发送错误最大值。            |
{.wide .expand}

#### CPU 指标 {#cpu-metrics}

| 名称                                 | 说明                               |
| ------------------------------------ | ---------------------------------- |
| `minio_node_cpu_avg_user`            | CPU 用户态时间占比。               |
| `minio_node_cpu_avg_user_avg`        | CPU 用户态时间占比均值。           |
| `minio_node_cpu_avg_user_max`        | CPU 用户态时间占比最大值。         |
| `minio_node_cpu_avg_system`          | CPU 内核态时间占比。               |
| `minio_node_cpu_avg_system_avg`      | CPU 内核态时间占比均值。           |
| `minio_node_cpu_avg_system_max`      | CPU 内核态时间占比最大值。         |
| `minio_node_cpu_avg_idle`            | CPU 空闲时间占比。                 |
| `minio_node_cpu_avg_idle_avg`        | CPU 空闲时间占比均值。             |
| `minio_node_cpu_avg_idle_max`        | CPU 空闲时间占比最大值。           |
| `minio_node_cpu_avg_iowait`          | CPU IOWait 时间占比。              |
| `minio_node_cpu_avg_iowait_avg`      | CPU IOWait 时间占比均值。          |
| `minio_node_cpu_avg_iowait_max`      | CPU IOWait 时间占比最大值。        |
| `minio_node_cpu_avg_nice`            | CPU nice 时间占比。                |
| `minio_node_cpu_avg_nice_avg`        | CPU nice 时间占比均值。            |
| `minio_node_cpu_avg_nice_max`        | CPU nice 时间占比最大值。          |
| `minio_node_cpu_avg_steal`           | CPU steal 时间占比。               |
| `minio_node_cpu_avg_steal_avg`       | CPU steal 时间占比均值。           |
| `minio_node_cpu_avg_steal_max`       | CPU steal 时间占比最大值。         |
| `minio_node_cpu_avg_load1`           | 1 分钟 CPU 平均负载。              |
| `minio_node_cpu_avg_load1_avg`       | 1 分钟 CPU 平均负载均值。          |
| `minio_node_cpu_avg_load1_max`       | 1 分钟 CPU 平均负载最大值。        |
| `minio_node_cpu_avg_load1_perc`      | 1 分钟 CPU 平均负载百分比。        |
| `minio_node_cpu_avg_load1_perc_avg`  | 1 分钟 CPU 平均负载百分比均值。    |
| `minio_node_cpu_avg_load1_perc_max`  | 1 分钟 CPU 平均负载百分比最大值。  |
| `minio_node_cpu_avg_load5`           | 5 分钟 CPU 平均负载。              |
| `minio_node_cpu_avg_load5_avg`       | 5 分钟 CPU 平均负载均值。          |
| `minio_node_cpu_avg_load5_max`       | 5 分钟 CPU 平均负载最大值。        |
| `minio_node_cpu_avg_load5_perc`      | 5 分钟 CPU 平均负载百分比。        |
| `minio_node_cpu_avg_load5_perc_avg`  | 5 分钟 CPU 平均负载百分比均值。    |
| `minio_node_cpu_avg_load5_perc_max`  | 5 分钟 CPU 平均负载百分比最大值。  |
| `minio_node_cpu_avg_load15`          | 15 分钟 CPU 平均负载。             |
| `minio_node_cpu_avg_load15_avg`      | 15 分钟 CPU 平均负载均值。         |
| `minio_node_cpu_avg_load15_max`      | 15 分钟 CPU 平均负载最大值。       |
| `minio_node_cpu_avg_load15_perc`     | 15 分钟 CPU 平均负载百分比。       |
| `minio_node_cpu_avg_load15_perc_avg` | 15 分钟 CPU 平均负载百分比均值。   |
| `minio_node_cpu_avg_load15_perc_max` | 15 分钟 CPU 平均负载百分比最大值。 |
{.wide .expand}

#### 内存指标 {#memory-metrics}

| 名称                           | 说明                         |
| ------------------------------ | ---------------------------- |
| `minio_node_mem_available`     | 节点可用内存。               |
| `minio_node_mem_available_avg` | 节点可用内存均值。           |
| `minio_node_mem_available_max` | 节点可用内存最大值。         |
| `minio_node_mem_buffers`       | 节点缓冲区内存。             |
| `minio_node_mem_buffers_avg`   | 节点缓冲区内存均值。         |
| `minio_node_mem_buffers_max`   | 节点缓冲区内存最大值。       |
| `minio_node_mem_cache`         | 节点页缓存内存。             |
| `minio_node_mem_cache_avg`     | 节点页缓存内存均值。         |
| `minio_node_mem_cache_max`     | 节点页缓存内存最大值。       |
| `minio_node_mem_free`          | 节点空闲内存。               |
| `minio_node_mem_free_avg`      | 节点空闲内存均值。           |
| `minio_node_mem_free_max`      | 节点空闲内存最大值。         |
| `minio_node_mem_shared`        | 节点共享内存。               |
| `minio_node_mem_shared_avg`    | 节点共享内存均值。           |
| `minio_node_mem_shared_max`    | 节点共享内存最大值。         |
| `minio_node_mem_total`         | 节点总内存。                 |
| `minio_node_mem_total_avg`     | 节点总内存均值。             |
| `minio_node_mem_total_max`     | 节点总内存最大值。           |
| `minio_node_mem_used`          | 节点已用内存。               |
| `minio_node_mem_used_avg`      | 节点已用内存均值。           |
| `minio_node_mem_used_max`      | 节点已用内存最大值。         |
| `minio_node_mem_used_perc`     | 节点内存使用率百分比。       |
| `minio_node_mem_used_perc_avg` | 节点内存使用率百分比均值。   |
| `minio_node_mem_used_perc_max` | 节点内存使用率百分比最大值。 |
{.wide .expand}
