---
title: "指标与告警"
url: "/zh/operations/monitoring/metrics-and-alerts/"
weight: 10
icon: fa-solid fa-gauge-high
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/metrics-and-alerts.rst
upstream_modified: true
---

<a id="metrics-and-alerts"></a>
<a id="minio-metrics-and-alerts"></a>
<a id="minio-metrics-and-alerts-alerting"></a>
<a id="minio-metrics-and-alerts-endpoints"></a>
<a id="id1" data-td-print-local></a>

MinIO 使用 [Prometheus 数据模型](https://prometheus.io/docs/concepts/data_model/) 发布指标。你可以使用任意抓取工具从 SILO 拉取指标数据，以执行进一步分析和配置告警。

[SILO 20261109](/zh/blog/release/silo-20261109/)（`RELEASE.2026-11-09T00-00-00Z`）、[Console 2.7.0](/zh/blog/release/console-2.7.0/) 与 [mcli 20261109](/zh/blog/release/mcli-20261109/) 将 Metrics V3（`/minio/metrics/v3`）作为推荐抓取契约。在 SILO 20261109 中，复制工作协程指标在复制工作池不存在时不会触发 panic，并继续保留历史均值和峰值计数（[`099b7ddf3`](https://github.com/pgsty/silo/commit/099b7ddf37b5a5e6d672604f1190fbab26448c20)）；实时批处理作业指标保留暂停原因以及跳过或拒绝计数（[#325](https://github.com/pgsty/silo/issues/325)）。

> [!NOTE]
> **Metrics version 2**
>
> 现有部署可以继续使用 version 2 [指标](/zh/operations/monitoring/metrics-v2/#minio-metrics-v2) 和 [Grafana 仪表板](/zh/operations/monitoring/grafana/#minio-grafana)。

<a id="version-3" data-td-print-local></a>

## Version 3 端点 {#version-3-endpoints}

对于 metrics version 3，所有指标都位于基础端点 `/minio/metrics/v3` 之下。你可以抓取该基础端点一次性收集全部指标，也可以追加可选路径，仅返回特定类别的指标。

> [!WARNING]
> **重要**
>
> 权威的指标定义与 Console 聚合查询逻辑请以 [`pgsty/silo` `RELEASE.2026-11-09T00-00-00Z` 源码](https://github.com/pgsty/silo/tree/d998292387ccf1d2907749e0fb1575ef5fb93fda)<a id="minio-minio"></a> 及 [Console 2.7.0 Metrics V3 映射参考](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/metrics-v3.md)为准。

例如，以下端点会返回 audit 指标：

```shell
http://HOSTNAME:PORT/minio/metrics/v3/audit
```

将 `HOSTNAME:PORT` 替换为 SILO 部署的 <abbr title="Fully Qualified Domain Name">FQDN</abbr> 与端口。对于使用负载均衡器管理节点间连接的部署，请指定负载均衡器地址。

默认情况下，SILO 要求在抓取指标端点时进行身份验证。请使用 [`mcli admin prometheus generate --api-version v3`](/zh/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate)（[mcli 20261109](/zh/blog/release/mcli-20261109/)）生成所需的 bearer token。你也可以将 [`MINIO_PROMETHEUS_AUTH_TYPE`](/zh/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_PROMETHEUS_AUTH_TYPE) 设置为 `public` 以禁用指标端点认证。

相对于基础 URL，SILO 提供以下抓取端点：

<table>
  <thead>
    <tr>
      <th><p>类别</p></th>
      <th><p>路径</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>API</p></td>
      <td><p><code>/api/requests</code></p><p><code>/bucket/api</code></p></td>
    </tr>
    <tr>
      <td><p>审计</p></td>
      <td><p><code>/audit</code></p></td>
    </tr>
    <tr>
      <td><p>集群</p></td>
      <td><p><code>/cluster/config</code></p><p><code>/cluster/erasure-set</code></p><p><code>/cluster/health</code></p><p><code>/cluster/iam</code></p><p><code>/cluster/usage/buckets</code></p><p><code>/cluster/usage/objects</code></p></td>
    </tr>
    <tr>
      <td><p>调试</p></td>
      <td><p><code>/debug/go</code></p></td>
    </tr>
    <tr>
      <td><p>ILM</p></td>
      <td><p><code>/ilm</code></p></td>
    </tr>
    <tr>
      <td><p>日志 Webhook</p></td>
      <td><p><code>/logger/webhook</code></p></td>
    </tr>
    <tr>
      <td><p>通知</p></td>
      <td><p><code>/notification</code></p></td>
    </tr>
    <tr>
      <td><p>复制</p></td>
      <td><p><code>/replication</code></p><p><code>/bucket/replication</code></p></td>
    </tr>
    <tr>
      <td><p>扫描器</p></td>
      <td><p><code>/scanner</code></p></td>
    </tr>
    <tr>
      <td><p>系统</p></td>
      <td><p><code>/system/drive</code></p><p><code>/system/memory</code></p><p><code>/system/cpu</code></p><p><code>/system/network/internode</code></p><p><code>/system/process</code></p></td>
    </tr>
  </tbody>
</table>

各端点对应的完整指标列表，请参见[可用的 version 3 指标](#minio-metrics-and-alerts-available-metrics)。

如需在 Console 中启用历史数据可视化，请在部署的每个节点上设置以下环境变量：

- 将 [`MINIO_PROMETHEUS_URL`](/zh/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_URL) 设置为 Prometheus 服务的 URL
- 将 [`MINIO_PROMETHEUS_JOB_ID`](/zh/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_JOB_ID) 设置为分配给已采集指标的唯一 job ID

<a id="id3" data-td-print-local></a>
<a id="minio-metrics-and-alerts-available-metrics"></a>

## 可用的 version 3 指标 {#available-version-3-metrics}

SILO 为集群、API 请求、存储桶以及系统运行状态发布以下各类 V3 指标：

- [API 指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-api-metrics)
- [审计指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-audit-metrics)
- [集群指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-cluster-metrics)
- [调试指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-debug-metrics)
- [ILM 指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-ilm-metrics)
- [日志 Webhook 指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-logger-webhook-metrics)
- [通知指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-notification-metrics)
- [复制指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-replication-metrics)
- [扫描器指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-scanner-metrics)
- [系统指标](/zh/operations/monitoring/metrics-and-alerts/#minio-available-v3-system-metrics)

许多指标包含标签，用于标识生成该指标的资源及其他维度信息。

<a id="minio-available-v3-api-metrics"></a>

### API 指标 {#api-metrics}

当前节点所服务请求的统计指标。

| 路径            | 说明                     |
| --------------- | ------------------------ |
| `/api/requests` | 所有请求的聚合指标。     |
| `/bucket/api`   | 按存储桶划分的请求指标。 |
{.wide .expand}

#### `/api/requests` {#api-requests}

| 名称                                           | 说明                                                    | 标签                                         |
| ---------------------------------------------- | ------------------------------------------------------- | -------------------------------------------- |
| `minio_api_requests_rejected_auth_total`       | 因身份验证失败而被拒绝的请求总数。<br><br>类型：counter | `type`, `pool_index`, `server`               |
| `minio_api_requests_rejected_header_total`     | 因请求头无效而被拒绝的请求总数。<br><br>类型：counter   | `type`, `pool_index`, `server`               |
| `minio_api_requests_rejected_timestamp_total`  | 因时间戳无效而被拒绝的请求总数。<br><br>类型：counter   | `type`, `pool_index`, `server`               |
| `minio_api_requests_rejected_invalid_total`    | 无效请求总数。<br><br>类型：counter                     | `type`, `pool_index`, `server`               |
| `minio_api_requests_waiting_total`             | 当前等待队列中的请求数。<br><br>类型：gauge             | `type`, `pool_index`, `server`               |
| `minio_api_requests_incoming_total`            | 当前传入请求总数。<br><br>类型：gauge                   | `type`, `pool_index`, `server`               |
| `minio_api_requests_inflight_total`            | 当前正在处理的请求数。<br><br>类型：gauge               | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_total`                     | 请求总数。<br><br>类型：counter                         | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_errors_total`              | 返回 4xx 或 5xx 错误的请求总数。<br><br>类型：counter   | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_5xx_errors_total`          | 返回 5xx 错误的请求总数。<br><br>类型：counter          | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_4xx_errors_total`          | 返回 4xx 错误的请求总数。<br><br>类型：counter          | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_canceled_total`            | 客户端取消的请求总数。<br><br>类型：counter             | `name`, `type`, `pool_index`, `server`       |
| `minio_api_requests_ttfb_seconds_distribution` | 各 API 调用首字节耗时（秒）分布。<br><br>类型：counter  | `name`, `type`, `le`, `pool_index`, `server` |
| `minio_api_requests_traffic_sent_bytes`        | 已发送总字节数。<br><br>类型：counter                   | `type`, `pool_index`, `server`               |
| `minio_api_requests_traffic_received_bytes`    | 已接收总字节数。<br><br>类型：counter                   | `type`, `pool_index`, `server`               |
{.wide .expand}

#### `/bucket/api` {#bucket-api}

| 名称                                         | 说明                                                       | 标签                                                   |
| -------------------------------------------- | ---------------------------------------------------------- | ------------------------------------------------------ |
| `minio_bucket_api_traffic_received_bytes`    | 存储桶接收流量字节总数。<br><br>类型：counter              | `bucket`, `type`, `server`, `pool_index`               |
| `minio_bucket_api_traffic_sent_bytes`        | 存储桶发送流量字节总数。<br><br>类型：counter              | `bucket`, `type`, `server`, `pool_index`               |
| `minio_bucket_api_inflight_total`            | 存储桶当前正在处理的请求数。<br><br>类型：gauge            | `bucket`, `name`, `type`, `server`, `pool_index`       |
| `minio_bucket_api_total`                     | 存储桶请求总数。<br><br>类型：counter                      | `bucket`, `name`, `type`, `server`, `pool_index`       |
| `minio_bucket_api_canceled_total`            | 客户端取消的存储桶请求总数。<br><br>类型：counter          | `bucket`, `name`, `type`, `server`, `pool_index`       |
| `minio_bucket_api_4xx_errors_total`          | 存储桶 4xx 错误请求总数。<br><br>类型：counter             | `bucket`, `name`, `type`, `server`, `pool_index`       |
| `minio_bucket_api_5xx_errors_total`          | 存储桶 5xx 错误请求总数。<br><br>类型：counter             | `bucket`, `name`, `type`, `server`, `pool_index`       |
| `minio_bucket_api_ttfb_seconds_distribution` | 存储桶 API 调用首字节耗时（秒）分布。<br><br>类型：counter | `bucket`, `name`, `le`, `type`, `server`, `pool_index` |
{.wide .expand}

<a id="minio-available-v3-audit-metrics"></a>

### 审计指标 {#audit-metrics}

审计日志发送状态相关指标。

| 路径     | 说明             |
| -------- | ---------------- |
| `/audit` | 审计子系统指标。 |
{.wide .expand}

#### `/audit` {#audit}

| 名称                              | 说明                                                    | 标签                  |
| --------------------------------- | ------------------------------------------------------- | --------------------- |
| `minio_audit_failed_messages`     | 自启动以来发送失败的审计消息总数。<br><br>类型：counter | `target_id`, `server` |
| `minio_audit_target_queue_length` | 目标队列中待发送的审计消息数。<br><br>类型：gauge       | `target_id`, `server` |
| `minio_audit_total_messages`      | 自启动以来已发送的审计消息总数。<br><br>类型：counter   | `target_id`, `server` |
{.wide .expand}

<a id="minio-available-v3-cluster-metrics"></a>

### 集群指标 {#cluster-metrics}

整个集群范围的运行指标。

| 路径                     | 说明                     |
| ------------------------ | ------------------------ |
| `/cluster/config`        | 集群配置指标。           |
| `/cluster/erasure-set`   | 纠删码集合指标。         |
| `/cluster/health`        | 集群健康指标。           |
| `/cluster/iam`           | 集群 IAM 指标。          |
| `/cluster/usage/buckets` | 按存储桶划分的对象统计。 |
| `/cluster/usage/objects` | 集群整体对象统计。       |
{.wide .expand}

#### `/cluster/config` {#cluster-config}

| 名称                                   | 说明                                             | 标签 |
| -------------------------------------- | ------------------------------------------------ | ---- |
| `minio_cluster_config_rrs_parity`      | 低冗余存储类（RRS）校验盘数。<br><br>类型：gauge |      |
| `minio_cluster_config_standard_parity` | 标准存储类校验盘数。<br><br>类型：gauge          |      |
{.wide .expand}

#### `/cluster/erasure-set` {#cluster-erasure-set}

| 名称                                             | 说明                                                                        | 标签                |
| ------------------------------------------------ | --------------------------------------------------------------------------- | ------------------- |
| `minio_cluster_erasure_set_overall_write_quorum` | 跨所有存储池与纠删集的总体写仲裁。<br><br>类型：gauge                       |                     |
| `minio_cluster_erasure_set_overall_health`       | 跨所有存储池与纠删集的总体健康状态（1=健康，0=不健康）。<br><br>类型：gauge |                     |
| `minio_cluster_erasure_set_read_quorum`          | 指定存储池内纠删集的读仲裁。<br><br>类型：gauge                             | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_quorum`         | 指定存储池内纠删集的写仲裁。<br><br>类型：gauge                             | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_online_drives_count`  | 纠删集中在线磁盘数。<br><br>类型：gauge                                     | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_healing_drives_count` | 纠删集中正在自愈的磁盘数。<br><br>类型：gauge                               | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_health`               | 纠删集健康状态（1=健康，0=不健康）。<br><br>类型：gauge                     | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_read_tolerance`       | 不中断读操作可容忍的磁盘故障数。<br><br>类型：gauge                         | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_tolerance`      | 不中断写操作可容忍的磁盘故障数。<br><br>类型：gauge                         | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_read_health`          | 纠删集读健康状态（1=健康，0=不健康）。<br><br>类型：gauge                   | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_health`         | 纠删集写健康状态（1=健康，0=不健康）。<br><br>类型：gauge                   | `pool_id`, `set_id` |
{.wide .expand}

#### `/cluster/health` {#cluster-health}

| 名称                                               | 说明                                          | 标签 |
| -------------------------------------------------- | --------------------------------------------- | ---- |
| `minio_cluster_health_drives_offline_count`        | 集群离线磁盘数。<br><br>类型：gauge           |      |
| `minio_cluster_health_drives_online_count`         | 集群在线磁盘数。<br><br>类型：gauge           |      |
| `minio_cluster_health_drives_count`                | 集群磁盘总数。<br><br>类型：gauge             |      |
| `minio_cluster_health_nodes_offline_count`         | 集群离线节点数。<br><br>类型：gauge           |      |
| `minio_cluster_health_nodes_online_count`          | 集群在线节点数。<br><br>类型：gauge           |      |
| `minio_cluster_health_capacity_raw_total_bytes`    | 集群裸盘总容量（字节）。<br><br>类型：gauge   |      |
| `minio_cluster_health_capacity_raw_free_bytes`     | 集群裸盘剩余容量（字节）。<br><br>类型：gauge |      |
| `minio_cluster_health_capacity_usable_total_bytes` | 集群可用总容量（字节）。<br><br>类型：gauge   |      |
| `minio_cluster_health_capacity_usable_free_bytes`  | 集群可用剩余容量（字节）。<br><br>类型：gauge |      |
{.wide .expand}

#### `/cluster/iam` {#cluster-iam}

| 名称                                                            | 说明                                                                          | 标签 |
| --------------------------------------------------------------- | ----------------------------------------------------------------------------- | ---- |
| `minio_cluster_iam_last_sync_duration_millis`                   | 最近一次成功 IAM 同步耗时（毫秒）。<br><br>类型：counter                      |      |
| `minio_cluster_iam_plugin_authn_service_failed_requests_minute` | 启用插件认证时，上一完整分钟内失败请求数。<br><br>类型：counter               |      |
| `minio_cluster_iam_plugin_authn_service_last_fail_seconds`      | 启用插件认证时，距最近一次失败请求的秒数。<br><br>类型：counter               |      |
| `minio_cluster_iam_plugin_authn_service_last_succ_seconds`      | 启用插件认证时，距最近一次成功请求的秒数。<br><br>类型：counter               |      |
| `minio_cluster_iam_plugin_authn_service_succ_avg_rtt_ms_minute` | 启用插件认证时，上一完整分钟内成功请求平均 RTT（毫秒）。<br><br>类型：counter |      |
| `minio_cluster_iam_plugin_authn_service_succ_max_rtt_ms_minute` | 启用插件认证时，上一完整分钟内成功请求最大 RTT（毫秒）。<br><br>类型：counter |      |
| `minio_cluster_iam_plugin_authn_service_total_requests_minute`  | 启用插件认证时，上一完整分钟内请求总数。<br><br>类型：counter                 |      |
| `minio_cluster_iam_since_last_sync_millis`                      | 距最近一次成功 IAM 同步的时间（毫秒）。<br><br>类型：counter                  |      |
| `minio_cluster_iam_sync_failures`                               | 自启动以来失败的 IAM 同步次数。<br><br>类型：counter                          |      |
| `minio_cluster_iam_sync_successes`                              | 自启动以来成功的 IAM 同步次数。<br><br>类型：counter                          |      |
{.wide .expand}

#### `/cluster/usage/buckets` {#cluster-usage-buckets}

| 名称                                                            | 说明                                                  | 标签              |
| --------------------------------------------------------------- | ----------------------------------------------------- | ----------------- |
| `minio_cluster_usage_buckets_since_last_update_seconds`         | 距上次更新存储桶用量指标的秒数。<br><br>类型：gauge   |                   |
| `minio_cluster_usage_buckets_total_bytes`                       | 存储桶总大小（字节）。<br><br>类型：gauge             | `bucket`          |
| `minio_cluster_usage_buckets_objects_count`                     | 存储桶对象总数。<br><br>类型：gauge                   | `bucket`          |
| `minio_cluster_usage_buckets_versions_count`                    | 存储桶对象版本总数（含删除标记）。<br><br>类型：gauge | `bucket`          |
| `minio_cluster_usage_buckets_delete_markers_count`              | 存储桶删除标记总数。<br><br>类型：gauge               | `bucket`          |
| `minio_cluster_usage_buckets_quota_total_bytes`                 | 存储桶配额（字节）。<br><br>类型：gauge               | `bucket`          |
| `minio_cluster_usage_buckets_object_size_distribution`          | 存储桶对象大小分布。<br><br>类型：gauge               | `range`, `bucket` |
| `minio_cluster_usage_buckets_object_version_count_distribution` | 存储桶对象版本数量分布。<br><br>类型：gauge           | `range`, `bucket` |
{.wide .expand}

#### `/cluster/usage/objects` {#cluster-usage-objects}

| 名称                                                     | 说明                                                  | 标签    |
| -------------------------------------------------------- | ----------------------------------------------------- | ------- |
| `minio_cluster_usage_objects_since_last_update_seconds`  | 距上次更新集群对象用量指标的秒数。<br><br>类型：gauge |         |
| `minio_cluster_usage_objects_total_bytes`                | 集群对象总占用字节数。<br><br>类型：gauge             |         |
| `minio_cluster_usage_objects_count`                      | 集群对象总数。<br><br>类型：gauge                     |         |
| `minio_cluster_usage_objects_versions_count`             | 集群对象版本总数（含删除标记）。<br><br>类型：gauge   |         |
| `minio_cluster_usage_objects_delete_markers_count`       | 集群删除标记总数。<br><br>类型：gauge                 |         |
| `minio_cluster_usage_objects_buckets_count`              | 集群存储桶总数。<br><br>类型：gauge                   |         |
| `minio_cluster_usage_objects_size_distribution`          | 集群对象大小分布。<br><br>类型：gauge                 | `range` |
| `minio_cluster_usage_objects_version_count_distribution` | 集群对象版本数分布。<br><br>类型：gauge               | `range` |
{.wide .expand}

<a id="minio-available-v3-debug-metrics"></a>

### 调试指标 {#debug-metrics}

来自 [Prometheus Go Client 基础收集器](https://github.com/prometheus/client_golang)的标准 Go 运行时指标。

| 路径        | 说明            |
| ----------- | --------------- |
| `/debug/go` | Go 运行时指标。 |
{.wide .expand}

<a id="minio-available-v3-ilm-metrics"></a>

### ILM 指标 {#ilm-metrics}

对象生命周期管理（ILM）子系统指标。

| 路径   | 说明                         |
| ------ | ---------------------------- |
| `/ilm` | ILM 生命周期与分层转移指标。 |
{.wide .expand}

#### `/ilm` {#ilm}

| 名称                                                  | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | 标签               |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| `minio_cluster_ilm_expiry_pending_tasks`              | 队列中等待执行的 ILM 过期任务数。<br><br>类型：gauge                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          | `server`           |
| `minio_cluster_ilm_transition_active_tasks`           | 当前正在执行的 ILM 分层转移任务数。<br><br>类型：gauge                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        | `server`           |
| `minio_cluster_ilm_transition_pending_tasks`          | 队列中等待执行的 ILM 分层转移任务数。<br><br>类型：gauge                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      | `server`           |
| `minio_cluster_ilm_transition_missed_immediate_tasks` | 错过的即时 ILM 转移任务数。<br><br>类型：counter                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              | `server`           |
| `minio_cluster_ilm_versions_scanned`                  | 自启动以来检查 ILM 动作的对象版本总数。<br><br>类型：counter                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | `server`           |
| `minio_ilm_expiry_incomplete_total`                   | 自启动以来未能移除目标而结束的 ILM 过期尝试总数，按 `reason` 区分：`not_applicable`（在对象锁下重验时规则不再适用）、`locked`（受 Object Lock 保护）、`history_unavailable`（无法取得权威版本历史）、`error`（其他故障）。整键清除还会记录 `tier_unsupported`（存在远端分层版本）、`budget`（移除部分版本后达到单轮预算上限，下一轮继续）和 `changed`（匹配的最新版本已变化），见[精确 key 删除](/zh/blog/design/ilm-delete-all-exact-key/)。`tier_unsupported_skipped` 统计扫描器因本池存在远端分层版本而跳过入队的观测次数（每盘每轮扫描计数一次，不等于对象键数或清除次数），见[多池生命周期过期](/zh/blog/design/multi-pool-lifecycle-expiry/#fix)。<br><br>类型：counter | `reason`, `server` |
{.wide .expand}

<a id="minio-available-v3-logger-webhook-metrics"></a>

### 日志 Webhook 指标 {#logger-webhook-metrics}

日志 Webhook 投递指标。

| 路径              | 说明                    |
| ----------------- | ----------------------- |
| `/logger/webhook` | 日志 Webhook 相关指标。 |
{.wide .expand}

#### `/logger/webhook` {#logger-webhook}

| 名称                                   | 说明                                              | 标签                         |
| -------------------------------------- | ------------------------------------------------- | ---------------------------- |
| `minio_logger_webhook_failed_messages` | 发送失败的日志消息数。<br><br>类型：counter       | `server`, `name`, `endpoint` |
| `minio_logger_webhook_queue_length`    | Webhook 待发送队列长度。<br><br>类型：gauge       | `server`, `name`, `endpoint` |
| `minio_logger_webhook_total_message`   | 发送至该目标的日志消息总数。<br><br>类型：counter | `server`, `name`, `endpoint` |
{.wide .expand}

<a id="minio-available-v3-notification-metrics"></a>

### 通知指标 {#notification-metrics}

存储桶事件通知相关指标。

| 路径            | 说明                 |
| --------------- | -------------------- |
| `/notification` | 事件通知子系统指标。 |
{.wide .expand}

#### `/notification` {#notification}

| 名称                                          | 说明                                                        | 标签     |
| --------------------------------------------- | ----------------------------------------------------------- | -------- |
| `minio_notification_current_send_in_progress` | 当前正在向各目标异步发送的并发调用数。<br><br>类型：counter | `server` |
| `minio_notification_events_errors_total`      | 发送至目标失败的事件总数。<br><br>类型：counter             | `server` |
| `minio_notification_events_sent_total`        | 已发送至目标的事件总数。<br><br>类型：counter               | `server` |
| `minio_notification_events_skipped_total`     | 因内存队列已满而跳过的事件数。<br><br>类型：counter         | `server` |
{.wide .expand}

<a id="minio-available-v3-replication-metrics"></a>

### 复制指标 {#replication-metrics}

站点复制与存储桶复制相关指标。

| 路径                  | 说明                           |
| --------------------- | ------------------------------ |
| `/bucket/replication` | 存储桶复制相关指标。           |
| `/replication`        | 站点复制与复制工作池相关指标。 |
{.wide .expand}

#### `/replication` {#replication}

| 名称                                           | 说明                                                          | 标签     |
| ---------------------------------------------- | ------------------------------------------------------------- | -------- |
| `minio_replication_average_active_workers`     | 活跃复制工作协程平均数。<br><br>类型：gauge                   | `server` |
| `minio_replication_average_queued_bytes`       | 自启动以来排队等待复制的平均字节数。<br><br>类型：gauge       | `server` |
| `minio_replication_average_queued_count`       | 自启动以来排队等待复制的平均对象数。<br><br>类型：gauge       | `server` |
| `minio_replication_average_data_transfer_rate` | 平均复制传输速率（字节/秒）。<br><br>类型：gauge              | `server` |
| `minio_replication_current_active_workers`     | 当前活跃复制工作协程数。<br><br>类型：gauge                   | `server` |
| `minio_replication_current_data_transfer_rate` | 当前复制传输速率（字节/秒）。<br><br>类型：gauge              | `server` |
| `minio_replication_last_minute_queued_bytes`   | 上一完整分钟排队复制的字节数。<br><br>类型：gauge             | `server` |
| `minio_replication_last_minute_queued_count`   | 上一完整分钟排队复制的对象数。<br><br>类型：gauge             | `server` |
| `minio_replication_max_active_workers`         | 自启动以来观测到的最大活跃复制工作协程数。<br><br>类型：gauge | `server` |
| `minio_replication_max_queued_bytes`           | 自启动以来排队等待复制的最大字节数。<br><br>类型：gauge       | `server` |
| `minio_replication_max_queued_count`           | 自启动以来排队等待复制的最大对象数。<br><br>类型：gauge       | `server` |
| `minio_replication_max_data_transfer_rate`     | 自启动以来的峰值复制传输速率（字节/秒）。<br><br>类型：gauge  | `server` |
| `minio_replication_recent_backlog_count`       | 最近 5 分钟内复制积压队列中的对象总数。<br><br>类型：gauge    | `server` |
{.wide .expand}

#### `/bucket/replication` {#bucket-replication}

| 名称                                                                | 说明                                                                  | 标签                                                  |
| ------------------------------------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------- |
| `minio_bucket_replication_last_hour_failed_bytes`                   | 最近一小时内存储桶至少复制失败一次的字节总数。<br><br>类型：gauge     | `bucket`, `server`                                    |
| `minio_bucket_replication_last_hour_failed_count`                   | 最近一小时内存储桶复制失败的对象总数。<br><br>类型：gauge             | `bucket`, `server`                                    |
| `minio_bucket_replication_last_minute_failed_bytes`                 | 上一完整分钟内至少复制失败一次的字节总数。<br><br>类型：gauge         | `bucket`, `server`                                    |
| `minio_bucket_replication_last_minute_failed_count`                 | 上一完整分钟内复制失败的对象总数。<br><br>类型：gauge                 | `bucket`, `server`                                    |
| `minio_bucket_replication_latency_ms`                               | 存储桶复制延迟（毫秒）。<br><br>类型：gauge                           | `bucket`, `operation`, `range`, `targetArn`, `server` |
| `minio_bucket_replication_proxied_delete_tagging_requests_total`    | 代理转发至复制目标的 DELETE tagging 请求数。<br><br>类型：counter     | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_get_requests_failures`            | 代理转发至复制目标的 GET 请求失败数。<br><br>类型：counter            | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_get_requests_total`               | 代理转发至复制目标的 GET 请求总数。<br><br>类型：counter              | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_get_tagging_requests_failures`    | 代理转发至复制目标的 GET tagging 请求失败数。<br><br>类型：counter    | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_get_tagging_requests_total`       | 代理转发至复制目标的 GET tagging 请求总数。<br><br>类型：counter      | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_head_requests_failures`           | 代理转发至复制目标的 HEAD 请求失败数。<br><br>类型：counter           | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_head_requests_total`              | 代理转发至复制目标的 HEAD 请求总数。<br><br>类型：counter             | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_put_tagging_requests_failures`    | 代理转发至复制目标的 PUT tagging 请求失败数。<br><br>类型：counter    | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_put_tagging_requests_total`       | 代理转发至复制目标的 PUT tagging 请求总数。<br><br>类型：counter      | `bucket`, `server`                                    |
| `minio_bucket_replication_sent_bytes`                               | 已复制到目标端的总字节数。<br><br>类型：counter                       | `bucket`, `server`                                    |
| `minio_bucket_replication_sent_count`                               | 已复制到目标端的对象总数。<br><br>类型：counter                       | `bucket`, `server`                                    |
| `minio_bucket_replication_total_failed_bytes`                       | 自启动以来至少复制失败一次的总字节数。<br><br>类型：counter           | `bucket`, `server`                                    |
| `minio_bucket_replication_total_failed_count`                       | 自启动以来复制失败的对象总数。<br><br>类型：counter                   | `bucket`, `server`                                    |
| `minio_bucket_replication_proxied_delete_tagging_requests_failures` | 代理转发至复制目标的 DELETE tagging 请求失败数。<br><br>类型：counter | `bucket`, `server`                                    |
{.wide .expand}

<a id="minio-available-v3-scanner-metrics"></a>

### 扫描器指标 {#scanner-metrics}

后台扫描器运行指标。

| 路径       | 说明                 |
| ---------- | -------------------- |
| `/scanner` | 后台扫描器相关指标。 |
{.wide .expand}

#### `/scanner` {#scanner}

| 名称                                  | 说明                                                    | 标签     |
| ------------------------------------- | ------------------------------------------------------- | -------- |
| `minio_scanner_bucket_scans_finished` | 自启动以来已完成的存储桶扫描次数。<br><br>类型：counter | `server` |
| `minio_scanner_bucket_scans_started`  | 自启动以来已启动的存储桶扫描次数。<br><br>类型：counter | `server` |
| `minio_scanner_directories_scanned`   | 自启动以来已扫描的目录总数。<br><br>类型：counter       | `server` |
| `minio_scanner_last_activity_seconds` | 距最近一次扫描活动的秒数。<br><br>类型：gauge           | `server` |
| `minio_scanner_objects_scanned`       | 自启动以来已扫描的唯一对象总数。<br><br>类型：counter   | `server` |
| `minio_scanner_versions_scanned`      | 自启动以来已扫描的对象版本总数。<br><br>类型：counter   | `server` |
{.wide .expand}

<a id="minio-available-v3-system-metrics"></a>

### 系统指标 {#system-metrics}

SILO 进程及所在节点的系统指标。

| 路径                        | 说明                 |
| --------------------------- | -------------------- |
| `/system/cpu`               | 节点 CPU 指标。      |
| `/system/drive`             | 节点磁盘指标。       |
| `/system/network/internode` | 节点间网络请求指标。 |
| `/system/memory`            | 节点内存指标。       |
| `/system/process`           | 进程级资源指标。     |
{.wide .expand}

#### `/system/drive` {#system-drive}

| 名称                                           | 说明                                                          | 标签                                                               |
| ---------------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------ |
| `minio_system_drive_used_bytes`                | 磁盘已用存储空间（字节）。<br><br>类型：gauge                 | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_free_bytes`                | 磁盘剩余存储空间（字节）。<br><br>类型：gauge                 | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_total_bytes`               | 磁盘总存储空间（字节）。<br><br>类型：gauge                   | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_used_inodes`               | 磁盘已用 inode 数。<br><br>类型：gauge                        | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_free_inodes`               | 磁盘剩余 inode 数。<br><br>类型：gauge                        | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_total_inodes`              | 磁盘总 inode 数。<br><br>类型：gauge                          | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_timeout_errors_total`      | 磁盘超时错误总数。<br><br>类型：counter                       | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_io_errors_total`           | 磁盘 I/O 错误总数。<br><br>类型：counter                      | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_availability_errors_total` | 磁盘可用性错误（I/O 错误与超时）总数。<br><br>类型：counter   | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_waiting_io`                | 磁盘上等待中的 I/O 操作数。<br><br>类型：gauge                | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_api_latency_micros`        | 最近一分钟磁盘存储操作平均延迟（微秒）。<br><br>类型：gauge   | `drive`, `api`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_offline_count`             | 离线磁盘数。<br><br>类型：gauge                               | `pool_index`, `server`                                             |
| `minio_system_drive_online_count`              | 在线磁盘数。<br><br>类型：gauge                               | `pool_index`, `server`                                             |
| `minio_system_drive_count`                     | 磁盘总数。<br><br>类型：gauge                                 | `pool_index`, `server`                                             |
| `minio_system_drive_health`                    | 磁盘健康状态（0=离线，1=健康，2=自愈中）。<br><br>类型：gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_reads_per_sec`             | 磁盘每秒读次数。<br><br>类型：gauge                           | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_reads_kb_per_sec`          | 磁盘每秒读取千字节数。<br><br>类型：gauge                     | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_reads_await`               | 磁盘读请求平均等待时间。<br><br>类型：gauge                   | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_writes_per_sec`            | 磁盘每秒写次数。<br><br>类型：gauge                           | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_writes_kb_per_sec`         | 磁盘每秒写入千字节数。<br><br>类型：gauge                     | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_writes_await`              | 磁盘写请求平均等待时间。<br><br>类型：gauge                   | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
| `minio_system_drive_perc_util`                 | 磁盘繁忙时间占比。<br><br>类型：gauge                         | `drive`, `set_index`, `drive_index`, `pool_index`, `server`        |
{.wide .expand}

#### `/system/memory` {#system-memory}

| 名称                            | 说明                                           | 标签     |
| ------------------------------- | ---------------------------------------------- | -------- |
| `minio_system_memory_used`      | 节点已用内存。<br><br>类型：gauge              | `server` |
| `minio_system_memory_used_perc` | 节点内存使用百分比。<br><br>类型：gauge        | `server` |
| `minio_system_memory_free`      | 节点空闲内存。<br><br>类型：gauge              | `server` |
| `minio_system_memory_total`     | 节点总内存。<br><br>类型：gauge                | `server` |
| `minio_system_memory_buffers`   | 节点缓冲区（buffers）内存。<br><br>类型：gauge | `server` |
| `minio_system_memory_cache`     | 节点页缓存（cache）内存。<br><br>类型：gauge   | `server` |
| `minio_system_memory_shared`    | 节点共享内存。<br><br>类型：gauge              | `server` |
| `minio_system_memory_available` | 节点可用内存。<br><br>类型：gauge              | `server` |
{.wide .expand}

#### `/system/cpu` {#system-cpu}

| 名称                          | 说明                                           | 标签     |
| ----------------------------- | ---------------------------------------------- | -------- |
| `minio_system_cpu_avg_idle`   | CPU 平均空闲时间占比。<br><br>类型：gauge      | `server` |
| `minio_system_cpu_avg_iowait` | CPU 平均 IOWait 时间占比。<br><br>类型：gauge  | `server` |
| `minio_system_cpu_load`       | 1 分钟 CPU 平均负载。<br><br>类型：gauge       | `server` |
| `minio_system_cpu_load_perc`  | 1 分钟 CPU 平均负载百分比。<br><br>类型：gauge | `server` |
| `minio_system_cpu_nice`       | CPU nice 时间占比。<br><br>类型：gauge         | `server` |
| `minio_system_cpu_steal`      | CPU steal 时间占比。<br><br>类型：gauge        | `server` |
| `minio_system_cpu_system`     | CPU 内核态时间占比。<br><br>类型：gauge        | `server` |
| `minio_system_cpu_user`       | CPU 用户态时间占比。<br><br>类型：gauge        | `server` |
{.wide .expand}

#### `/system/network/internode` {#system-network-internode}

| 名称                                                 | 说明                                                 | 标签                   |
| ---------------------------------------------------- | ---------------------------------------------------- | ---------------------- |
| `minio_system_network_internode_errors_total`        | 失败的节点间调用总数。<br><br>类型：counter          | `server`, `pool_index` |
| `minio_system_network_internode_dial_errors_total`   | 节点间 TCP 建连超时与错误总数。<br><br>类型：counter | `server`, `pool_index` |
| `minio_system_network_internode_dial_avg_time_nanos` | 节点间 TCP 建连平均耗时（纳秒）。<br><br>类型：gauge | `server`, `pool_index` |
| `minio_system_network_internode_sent_bytes_total`    | 发送给其他对端节点的总字节数。<br><br>类型：counter  | `server`, `pool_index` |
| `minio_system_network_internode_recv_bytes_total`    | 从其他对端节点接收的总字节数。<br><br>类型：counter  | `server`, `pool_index` |
{.wide .expand}

#### `/system/process` {#system-process}

| 名称                                               | 说明                                                                                          | 标签     |
| -------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------- |
| `minio_system_process_locks_read_total`            | 当前节点持有的读锁数量。<br><br>类型：gauge                                                   | `server` |
| `minio_system_process_locks_write_total`           | 当前节点持有的写锁数量。<br><br>类型：gauge                                                   | `server` |
| `minio_system_process_cpu_total_seconds`           | 进程累计消耗的用户态与内核态 CPU 秒数。<br><br>类型：counter                                  | `server` |
| `minio_system_process_go_routine_total`            | 当前运行中的 Goroutine 总数。<br><br>类型：gauge                                              | `server` |
| `minio_system_process_io_rchar_bytes`              | 进程从存储子系统（含缓存）读取的总字节数（`/proc/[pid]/io` `rchar`）。<br><br>类型：counter   | `server` |
| `minio_system_process_io_read_bytes`               | 进程从底层存储读取的总字节数（`/proc/[pid]/io` `read_bytes`）。<br><br>类型：counter          | `server` |
| `minio_system_process_io_wchar_bytes`              | 进程向存储子系统（含页缓存）写入的总字节数（`/proc/[pid]/io` `wchar`）。<br><br>类型：counter | `server` |
| `minio_system_process_io_write_bytes`              | 进程向底层存储写入的总字节数（`/proc/[pid]/io` `write_bytes`）。<br><br>类型：counter         | `server` |
| `minio_system_process_start_time_seconds`          | 进程启动时间（自 Unix 纪元起的秒数）。<br><br>类型：gauge                                     | `server` |
| `minio_system_process_uptime_seconds`              | 进程运行时长（秒）。<br><br>类型：gauge                                                       | `server` |
| `minio_system_process_file_descriptor_limit_total` | 进程可打开文件描述符总数上限。<br><br>类型：gauge                                             | `server` |
| `minio_system_process_file_descriptor_open_total`  | 进程当前打开的文件描述符总数。<br><br>类型：gauge                                             | `server` |
| `minio_system_process_syscall_read_total`          | 读系统调用总数（`/proc/[pid]/io` `syscr`）。<br><br>类型：counter                             | `server` |
| `minio_system_process_syscall_write_total`         | 写系统调用总数（`/proc/[pid]/io` `syscw`）。<br><br>类型：counter                             | `server` |
| `minio_system_process_resident_memory_bytes`       | 常驻内存（RSS）大小（字节）。<br><br>类型：gauge                                              | `server` |
| `minio_system_process_virtual_memory_bytes`        | 虚拟内存大小（字节）。<br><br>类型：gauge                                                     | `server` |
| `minio_system_process_virtual_memory_max_bytes`    | 最大虚拟内存限制（字节）。<br><br>类型：gauge                                                 | `server` |
{.wide .expand}
