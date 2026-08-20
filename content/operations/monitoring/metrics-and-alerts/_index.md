---
title: "Metrics and alerts"
url: "/operations/monitoring/metrics-and-alerts/"
weight: 10
icon: fa-solid fa-gauge-high
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/metrics-and-alerts.rst
upstream_modified: false
---

<a id="metrics-and-alerts"></a>
<a id="minio-metrics-and-alerts"></a>
<a id="minio-metrics-and-alerts-alerting"></a>
<a id="minio-metrics-and-alerts-endpoints"></a>

MinIO publishes metrics using the [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/). You can use any scraping tool to pull metrics data from MinIO for further analysis and alerting.

Starting with MinIO Server [RELEASE.2024-07-15T19-02-30Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-07-15T19-02-30Z) and MinIO Client [RELEASE.2024-07-11T18-01-28Z](https://github.com/minio/mc/releases/tag/RELEASE.2024-07-11T18-01-28Z), metrics version 3 provides additional endpoints. MinIO recommends version 3 for new deployments.

> [!NOTE]
> **Metrics version 2**
>
> Existing deployments can continue to use version 2 [metrics](/operations/monitoring/metrics-v2/#minio-metrics-v2) and [Grafana dashboards](/operations/monitoring/grafana/#minio-grafana).

## Version 3 Endpoints {#version-3-endpoints}

For metrics version 3, all metrics are available under the base `/minio/metrics/v3` endpoint. You can scrape the base endpoint to collect all metrics in a single operation, or append an optional path to return a specific category.

> [!WARNING]
> **Important**
>
> The V3 metrics on this page may have gaps, inaccuracies, or incorrect information. Reference the [minio/minio](https://github.com/minio/minio)<a id="minio-minio"></a> repository and review the source code for the most accurate representation of metrics as available.

For example, the following endpoint returns audit metrics:

```shell
http://HOSTNAME:PORT/minio/metrics/v3/audit
```

Replace `HOSTNAME:PORT` with the <abbr title="Fully Qualified Domain Name">FQDN</abbr> and port of the MinIO deployment. For deployments with a load balancer managing connections between MinIO nodes, specify the address of the load balancer.

By default, MinIO requires authentication to scrape the metrics endpoints. To generate the needed bearer tokens, use [`mc admin prometheus generate`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate). You can also disable metrics endpoint authentication by setting [`MINIO_PROMETHEUS_AUTH_TYPE`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_PROMETHEUS_AUTH_TYPE) to `public`.

MinIO provides the following scraping endpoints, relative to the base URL:

<table>
  <thead>
    <tr>
      <th><p>Category</p></th>
      <th><p>Path</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>API</p></td>
      <td><p><code>/api/requests</code></p><p><code>/bucket/api</code></p></td>
    </tr>
    <tr>
      <td><p>Audit</p></td>
      <td><p><code>/audit</code></p></td>
    </tr>
    <tr>
      <td><p>Cluster</p></td>
      <td><p><code>/cluster/config</code></p><p><code>/cluster/erasure-set</code></p><p><code>/cluster/health</code></p><p><code>/cluster/iam</code></p><p><code>/cluster/usage/buckets</code></p><p><code>/cluster/usage/objects</code></p></td>
    </tr>
    <tr>
      <td><p>Debug</p></td>
      <td><p><code>/debug/go</code></p></td>
    </tr>
    <tr>
      <td><p>ILM</p></td>
      <td><p><code>/ilm</code></p></td>
    </tr>
    <tr>
      <td><p>Logger webhook</p></td>
      <td><p><code>/logger/webhook</code></p></td>
    </tr>
    <tr>
      <td><p>Notification</p></td>
      <td><p><code>/notification</code></p></td>
    </tr>
    <tr>
      <td><p>Replication</p></td>
      <td><p><code>/replication</code></p><p><code>/bucket/replication</code></p></td>
    </tr>
    <tr>
      <td><p>Scanner</p></td>
      <td><p><code>/scanner</code></p></td>
    </tr>
    <tr>
      <td><p>System</p></td>
      <td><p><code>/system/drive</code></p><p><code>/system/memory</code></p><p><code>/system/cpu</code></p><p><code>/system/network/internode</code></p><p><code>/system/process</code></p></td>
    </tr>
  </tbody>
</table>

For a complete list of metrics for each endpoint, see [Available version 3 metrics](#minio-metrics-and-alerts-available-metrics).

To enable historical data visualization in MinIO Console, set the following environment variables on each node in the MinIO deployment:

- Set [`MINIO_PROMETHEUS_URL`](/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_URL) to the URL of the Prometheus service
- Set [`MINIO_PROMETHEUS_JOB_ID`](/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_JOB_ID) to the unique job ID assigned to the collected metrics

<a id="minio-metrics-and-alerts-available-metrics"></a>

## Available version 3 metrics {#available-version-3-metrics}

MinIO publishes a number of metrics for clusters, API requests, buckets, and other aspects of the MinIO service:

- [API Metrics](#minio-available-v3-api-metrics)
- [Audit Metrics](#minio-available-v3-audit-metrics)
- [Cluster Metrics](#minio-available-v3-cluster-metrics)
- [Debug Metrics](#minio-available-v3-debug-metrics)
- [ILM Metrics](#minio-available-v3-ilm-metrics)
- [Logger webhook Metrics](#minio-available-v3-logger-webhook-metrics)
- [Notification Metrics](#minio-available-v3-notification-metrics)
- [Replication Metrics](#minio-available-v3-replication-metrics)
- [Scanner Metrics](#minio-available-v3-scanner-metrics)
- [System Metrics](#minio-available-v3-system-metrics)

Many metrics include labels identifying the resource which generated that metric and other relevant details.

<a id="minio-available-v3-api-metrics"></a>

### API metrics {#api-metrics}

Metrics about requests served by the current node.

| Path | Description |
| --- | --- |
| `/api/requests` | Metrics over all requests. |
| `/bucket/api` | Metrics over all requests for a given bucket. |

#### `/api/requests` {#api-requests}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_api_requests_rejected_auth_total` | Total number of requests rejected for auth failure. <br><br>Type: counter | `type`, `pool_index`, `server` |
| `minio_api_requests_rejected_header_total` | Total number of requests rejected for invalid header. <br><br>Type: counter | `type`, `pool_index`, `server` |
| `minio_api_requests_rejected_timestamp_total` | Total number of requests rejected for invalid timestamp. <br><br>Type: counter | `type`, `pool_index`, `server` |
| `minio_api_requests_rejected_invalid_total` | Total number of invalid requests. <br><br>Type: counter | `type`, `pool_index`, `server` |
| `minio_api_requests_waiting_total` | Total number of requests in the waiting queue. <br><br>Type: gauge | `type`, `pool_index`, `server` |
| `minio_api_requests_incoming_total` | Total number of incoming requests. <br><br>Type: gauge | `type`, `pool_index`, `server` |
| `minio_api_requests_inflight_total` | Total number of requests currently in flight. <br><br>Type: gauge | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_total` | Total number of requests. <br><br>Type: counter | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_errors_total` | Total number of requests with 4xx or 5xx errors. <br><br>Type: counter | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_5xx_errors_total` | Total number of requests with 5xx errors. <br><br>Type: counter | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_4xx_errors_total` | Total number of requests with 4xx errors. <br><br>Type: counter | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_canceled_total` | Total number of requests canceled by the client. <br><br>Type: counter | `name`, `type`, `pool_index`, `server` |
| `minio_api_requests_ttfb_seconds_distribution` | Distribution of time to first byte across API calls. <br><br>Type: counter | `name`, `type`, `le`, `pool_index`, `server` |
| `minio_api_requests_traffic_sent_bytes` | Total number of bytes sent. <br><br>Type: counter | `type`, `pool_index`, `server` |
| `minio_api_requests_traffic_received_bytes` | Total number of bytes received. <br><br>Type: counter | `type`, `pool_index`, `server` |

#### `/bucket/api` {#bucket-api}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_bucket_api_traffic_received_bytes` | Total number of bytes sent for a bucket. <br><br>Type: counter | `bucket`, `type`, `server`, `pool_index` |
| `minio_bucket_api_traffic_sent_bytes` | Total number of bytes received for a bucket. <br><br>Type: counter | `bucket`, `type`, `server`, `pool_index` |
| `minio_bucket_api_inflight_total` | Total number of requests currently in flight for a bucket. <br><br>Type: gauge | `bucket`, `name`, `type`, `server`, `pool_index` |
| `minio_bucket_api_total` | Total number of requests for a bucket. <br><br>Type: counter | `bucket`, `name`, `type`, `server`, `pool_index` |
| `minio_bucket_api_canceled_total` | Total number of requests canceled by the client for a bucket. <br><br>Type: counter | `bucket`, `name`, `type`, `server`, `pool_index` |
| `minio_bucket_api_4xx_errors_total` | Total number of requests with 4xx errors for a bucket. <br><br>Type: counter | `bucket`, `name`, `type`, `server`, `pool_index` |
| `minio_bucket_api_5xx_errors_total` | Total number of requests with 5xx errors for a bucket. <br><br>Type: counter | `bucket`, `name`, `type`, `server`, `pool_index` |
| `minio_bucket_api_ttfb_seconds_distribution` | Distribution of time to first byte across API calls for a bucket. <br><br>Type: counter | `bucket`, `name`, `le`, `type`, `server`, `pool_index` |

<a id="minio-available-v3-audit-metrics"></a>

### Audit metrics {#audit-metrics}

Metrics about the MinIO audit functionality.

| Path | Description |
| --- | --- |
| `/audit` | Metrics related to audit functionality. |

#### `/audit` {#audit}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_audit_failed_messages` | Total number of messages that failed to send since start. <br><br>Type: counter | `target_id`, `server` |
| `minio_audit_target_queue_length` | Number of unsent messages in queue for target. <br><br>Type: gauge | `target_id`, `server` |
| `minio_audit_total_messages` | Total number of messages sent since start. <br><br>Type: counter | `target_id`, `server` |

<a id="minio-available-v3-cluster-metrics"></a>

### Cluster metrics {#cluster-metrics}

Metrics about an entire MinIO cluster.

| Path | Description |
| --- | --- |
| `/cluster/config` | Cluster configuration metrics. |
| `/cluster/erasure-set` | Erasure set metrics. |
| `/cluster/health` | Cluster health metrics. |
| `/cluster/iam` | Cluster iam metrics. |
| `/cluster/usage/buckets` | Object statistics by bucket. |
| `/cluster/usage/objects` | Object statistics. |

#### `/cluster/config` {#cluster-config}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_config_rrs_parity` | Reduced redundancy storage class parity. <br><br>Type: gauge | |
| `minio_cluster_config_standard_parity` | Standard storage class parity. <br><br>Type: gauge | |

#### `/cluster/erasure-set` {#cluster-erasure-set}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_erasure_set_overall_write_quorum` | Overall write quorum across pools and sets. <br><br>Type: gauge | |
| `minio_cluster_erasure_set_overall_health` | Overall health across pools and sets (1=healthy, 0=unhealthy). <br><br>Type: gauge | |
| `minio_cluster_erasure_set_read_quorum` | Read quorum for the erasure set in a pool. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_quorum` | Write quorum for the erasure set in a pool. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_online_drives_count` | Count of online drives in the erasure set in a pool. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_healing_drives_count` | Count of healing drives in the erasure set in a pool. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_health` | Health of the erasure set in a pool (1=healthy, 0=unhealthy). <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_read_tolerance` | Number of drive failures that can be tolerated without disrupting read operations. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_tolerance` | Number of drive failures that can be tolerated without disrupting write operations. <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_read_health` | Health of the erasure set in a pool for read operations (1=healthy, 0=unhealthy). <br><br>Type: gauge | `pool_id`, `set_id` |
| `minio_cluster_erasure_set_write_health` | Health of the erasure set in a pool for write operations (1=healthy, 0=unhealthy). <br><br>Type: gauge | `pool_id`, `set_id` |

#### `/cluster/health` {#cluster-health}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_health_drives_offline_count` | Count of offline drives in the cluster. <br><br>Type: gauge | |
| `minio_cluster_health_drives_online_count` | Count of online drives in the cluster. <br><br>Type: gauge | |
| `minio_cluster_health_drives_count` | Count of all drives in the cluster. <br><br>Type: gauge | |
| `minio_cluster_health_nodes_offline_count` | Count of offline nodes in the cluster. <br><br>Type: gauge | |
| `minio_cluster_health_nodes_online_count` | Count of online nodes in the cluster. <br><br>Type: gauge | |
| `minio_cluster_health_capacity_raw_total_bytes` | Total cluster raw storage capacity in bytes. <br><br>Type: gauge | |
| `minio_cluster_health_capacity_raw_free_bytes` | Total cluster raw storage free in bytes. <br><br>Type: gauge | |
| `minio_cluster_health_capacity_usable_total_bytes` | Total cluster usable storage capacity in bytes. <br><br>Type: gauge | |
| `minio_cluster_health_capacity_usable_free_bytes` | Total cluster usable storage free in bytes. <br><br>Type: gauge | |

#### `/cluster/iam` {#cluster-iam}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_iam_last_sync_duration_millis` | Last successful IAM data sync duration in milliseconds. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_failed_requests_minute` | When plugin authentication is configured, returns failed requests count in the last full minute. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_last_fail_seconds` | When plugin authentication is configured, returns time (in seconds) since the last failed request to the service. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_last_succ_seconds` | When plugin authentication is configured, returns time (in seconds) since the last successful request to the service. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_succ_avg_rtt_ms_minute` | When plugin authentication is configured, returns average round-trip time of successful requests in the last full minute. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_succ_max_rtt_ms_minute` | When plugin authentication is configured, returns maximum round-trip time of successful requests in the last full minute. <br><br>Type: counter | |
| `minio_cluster_iam_plugin_authn_service_total_requests_minute` | When plugin authentication is configured, returns total requests count in the last full minute. <br><br>Type: counter | |
| `minio_cluster_iam_since_last_sync_millis` | Time (in milliseconds) since last successful IAM data sync. <br><br>Type: counter | |
| `minio_cluster_iam_sync_failures` | Number of failed IAM data syncs since server start. <br><br>Type: counter | |
| `minio_cluster_iam_sync_successes` | Number of successful IAM data syncs since server start. <br><br>Type: counter | |

#### `/cluster/usage/buckets` {#cluster-usage-buckets}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_usage_buckets_since_last_update_seconds` | Time since last update of usage metrics in seconds. <br><br>Type: gauge | |
| `minio_cluster_usage_buckets_total_bytes` | Total bucket size in bytes. <br><br>Type: gauge | `bucket` |
| `minio_cluster_usage_buckets_objects_count` | Total object count in bucket. <br><br>Type: gauge | `bucket` |
| `minio_cluster_usage_buckets_versions_count` | Total object versions count in bucket, including delete markers. <br><br>Type: gauge | `bucket` |
| `minio_cluster_usage_buckets_delete_markers_count` | Total delete markers count in bucket. <br><br>Type: gauge | `bucket` |
| `minio_cluster_usage_buckets_quota_total_bytes` | Total bucket quota in bytes. <br><br>Type: gauge | `bucket` |
| `minio_cluster_usage_buckets_object_size_distribution` | Bucket object size distribution. <br><br>Type: gauge | `range`, `bucket` |
| `minio_cluster_usage_buckets_object_version_count_distribution` | Bucket object version count distribution. <br><br>Type: gauge | `range`, `bucket` |

#### `/cluster/usage/objects` {#cluster-usage-objects}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_usage_objects_since_last_update_seconds` | Time since last update of usage metrics in seconds. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_total_bytes` | Total cluster usage in bytes. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_count` | Total cluster objects count. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_versions_count` | Total cluster object versions count, including delete markers. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_delete_markers_count` | Total cluster delete markers count. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_buckets_count` | Total cluster buckets count. <br><br>Type: gauge | |
| `minio_cluster_usage_objects_size_distribution` | Cluster object size distribution. <br><br>Type: gauge | `range` |
| `minio_cluster_usage_objects_version_count_distribution` | Cluster object version count distribution. <br><br>Type: gauge | `range` |

<a id="minio-available-v3-debug-metrics"></a>

### Debug metrics {#debug-metrics}

Standard Go runtime metrics from the [Prometheus Go Client base collector](https://github.com/prometheus/client_golang).

| Path | Description |
| --- | --- |
| `/debug/go` | Go runtime metrics. |

<a id="minio-available-v3-ilm-metrics"></a>

### ILM metrics {#ilm-metrics}

Metrics about the MinIO ILM functionality.

| Path | Description |
| --- | --- |
| `/ilm` | Metrics related to ILM functionality. |

#### `/ilm` {#ilm}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_cluster_ilm_expiry_pending_tasks` | Number of pending ILM expiry tasks in the queue. <br><br>Type: gauge | `server` |
| `minio_cluster_ilm_transition_active_tasks` | Number of active ILM transition tasks. <br><br>Type: gauge | `server` |
| `minio_cluster_ilm_transition_pending_tasks` | Number of pending ILM transition tasks in the queue. <br><br>Type: gauge | `server` |
| `minio_cluster_ilm_transition_missed_immediate_tasks` | Number of missed immediate ILM transition tasks. <br><br>Type: counter | `server` |
| `minio_cluster_ilm_versions_scanned` | Total number of object versions checked for ILM actions since server start. <br><br>Type: counter | `server` |

<a id="minio-available-v3-logger-webhook-metrics"></a>

### Logger webhook metrics {#logger-webhook-metrics}

Metrics about MinIO logger webhooks.

| Path | Description |
| --- | --- |
| `/logger/webhook` | Metrics related to logger webhooks. |

#### `/logger/webhook` {#logger-webhook}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_logger_webhook_failed_messages` | Number of messages that failed to send. <br><br>Type: counter | `server`, `name`, `endpoint` |
| `minio_logger_webhook_queue_length` | Webhook queue length. <br><br>Type: gauge | `server`, `name`, `endpoint` |
| `minio_logger_webhook_total_message` | Total number of messages sent to this target. <br><br>Type: counter | `server`, `name`, `endpoint` |

<a id="minio-available-v3-notification-metrics"></a>

### Notification metrics {#notification-metrics}

Metrics about the MinIO notification functionality.

| Path | Description |
| --- | --- |
| `/notification` | Metrics related to notification functionality. |

#### `/notification` {#notification}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_notification_current_send_in_progress` | Number of concurrent async Send calls active to all targets. <br><br>Type: counter | `server` |
| `minio_notification_events_errors_total` | Total number of events that failed to send to the targets. <br><br>Type: counter | `server` |
| `minio_notification_events_sent_total` | Total number of events sent to the targets. <br><br>Type: counter | `server` |
| `minio_notification_events_skipped_total` | Number of events not sent to the targets due to the in-memory queue being full. <br><br>Type: counter | `server` |

<a id="minio-available-v3-replication-metrics"></a>

### Replication metrics {#replication-metrics}

Metrics about MinIO site and bucket replication.

| Path | Description |
| --- | --- |
| `/bucket/replication` | Metrics related to bucket replication. |
| `/replication` | Metrics related to site replication. |

#### `/replication` {#replication}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_replication_average_active_workers` | Average number of active replication workers. <br><br>Type: gauge | `server` |
| `minio_replication_average_queued_bytes` | Average number of bytes queued for replication since server start. <br><br>Type: gauge | `server` |
| `minio_replication_average_queued_count` | Average number of objects queued for replication since server start. <br><br>Type: gauge | `server` |
| `minio_replication_average_data_transfer_rate` | Average replication data transfer rate in bytes/sec. <br><br>Type: gauge | `server` |
| `minio_replication_current_active_workers` | Total number of active replication workers. <br><br>Type: gauge | `server` |
| `minio_replication_current_data_transfer_rate` | Current replication data transfer rate in bytes/sec. <br><br>Type: gauge | `server` |
| `minio_replication_last_minute_queued_bytes` | Number of bytes queued for replication in the last full minute. <br><br>Type: gauge | `server` |
| `minio_replication_last_minute_queued_count` | Number of objects queued for replication in the last full minute. <br><br>Type: gauge | `server` |
| `minio_replication_max_active_workers` | Maximum number of active replication workers seen since server start. <br><br>Type: gauge | `server` |
| `minio_replication_max_queued_bytes` | Maximum number of bytes queued for replication since server start. <br><br>Type: gauge | `server` |
| `minio_replication_max_queued_count` | Maximum number of objects queued for replication since server start. <br><br>Type: gauge | `server` |
| `minio_replication_max_data_transfer_rate` | Maximum replication data transfer rate in bytes/sec since server start. <br><br>Type: gauge | `server` |
| `minio_replication_recent_backlog_count` | Total number of objects seen in replication backlog in the last 5 minutes <br><br>Type: gauge | `server` |

#### `/bucket/replication` {#bucket-replication}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_bucket_replication_last_hour_failed_bytes` | Total number of bytes on a bucket which failed to replicate at least once in the last hour. <br><br>Type: gauge | `bucket`, `server` |
| `minio_bucket_replication_last_hour_failed_count` | Total number of objects on a bucket which failed to replicate in the last hour. <br><br>Type: gauge | `bucket`, `server` |
| `minio_bucket_replication_last_minute_failed_bytes` | Total number of bytes on a bucket which failed at least once in the last full minute. <br><br>Type: gauge | `bucket`, `server` |
| `minio_bucket_replication_last_minute_failed_count` | Total number of objects on a bucket which failed to replicate in the last full minute. <br><br>Type: gauge | `bucket`, `server` |
| `minio_bucket_replication_latency_ms` | Replication latency on a bucket in milliseconds. <br><br>Type: gauge | `bucket`, `operation`, `range`, `targetArn`, `server` |
| `minio_bucket_replication_proxied_delete_tagging_requests_total` | Number of DELETE tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_get_requests_failures` | Number of failures in GET requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_get_requests_total` | Number of GET requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_get_tagging_requests_failures` | Number of failures in GET tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_get_tagging_requests_total` | Number of GET tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_head_requests_failures` | Number of failures in HEAD requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_head_requests_total` | Number of HEAD requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_put_tagging_requests_failures` | Number of failures in PUT tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_put_tagging_requests_total` | Number of PUT tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_sent_bytes` | Total number of bytes replicated to the target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_sent_count` | Total number of objects replicated to the target. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_total_failed_bytes` | Total number of bytes failed to replicate at least once since server start. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_total_failed_count` | Total number of objects that failed to replicate since server start. <br><br>Type: counter | `bucket`, `server` |
| `minio_bucket_replication_proxied_delete_tagging_requests_failures` | Number of failures in DELETE tagging requests proxied to replication target. <br><br>Type: counter | `bucket`, `server` |

<a id="minio-available-v3-scanner-metrics"></a>

### Scanner metrics {#scanner-metrics}

Metrics about the MinIO scanner.

| Path | Description |
| --- | --- |
| `/scanner` | Metrics related to the MinIO scanner. |

#### `/scanner` {#scanner}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_scanner_bucket_scans_finished` | Total number of bucket scans completed since server start. <br><br>Type: counter | `server` |
| `minio_scanner_bucket_scans_started` | Total number of bucket scans started since server start. <br><br>Type: counter | `server` |
| `minio_scanner_directories_scanned` | Total number of directories scanned since server start. <br><br>Type: counter | `server` |
| `minio_scanner_last_activity_seconds` | Time elapsed (in seconds) since last scan activity. <br><br>Type: gauge | `server` |
| `minio_scanner_objects_scanned` | Total number of unique objects scanned since server start. <br><br>Type: counter | `server` |
| `minio_scanner_versions_scanned` | Total number of object versions scanned since server start. <br><br>Type: counter | `server` |

<a id="minio-available-v3-system-metrics"></a>

### System metrics {#system-metrics}

Metrics about the MinIO process and the node.

| Path | Description |
| --- | --- |
| `/system/cpu` | Metrics about CPUs on the system. |
| `/system/drive` | Metrics about drives on the system. |
| `/system/network/internode` | Metrics about internode requests made by the node. |
| `/system/memory` | Metrics about memory on the system. |
| `/system/process` | Standard process metrics. |

#### `/system/drive` {#system-drive}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_system_drive_used_bytes` | Total storage used on a drive in bytes. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_free_bytes` | Total storage free on a drive in bytes. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_total_bytes` | Total storage available on a drive in bytes. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_used_inodes` | Total used inodes on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_free_inodes` | Total free inodes on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_total_inodes` | Total inodes available on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_timeout_errors_total` | Total timeout errors on a drive. <br><br>Type: counter | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_io_errors_total` | Total I/O errors on a drive. <br><br>Type: counter | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_availability_errors_total` | Total availability errors (I/O errors, timeouts) on a drive. <br><br>Type: counter | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_waiting_io` | Total waiting I/O operations on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_api_latency_micros` | Average last minute latency in µs for drive API storage operations. <br><br>Type: gauge | `drive`, `api`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_offline_count` | Count of offline drives. <br><br>Type: gauge | `pool_index`, `server` |
| `minio_system_drive_online_count` | Count of online drives. <br><br>Type: gauge | `pool_index`, `server` |
| `minio_system_drive_count` | Count of all drives. <br><br>Type: gauge | `pool_index`, `server` |
| `minio_system_drive_health` | Drive health (0 = offline, 1 = healthy, 2 = healing). <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_reads_per_sec` | Reads per second on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_reads_kb_per_sec` | Kilobytes read per second on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_reads_await` | Average time for read requests served on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_writes_per_sec` | Writes per second on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_writes_kb_per_sec` | Kilobytes written per second on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_writes_await` | Average time for write requests served on a drive. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |
| `minio_system_drive_perc_util` | Percentage of time the disk was busy. <br><br>Type: gauge | `drive`, `set_index`, `drive_index`, `pool_index`, `server` |

#### `/system/memory` {#system-memory}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_system_memory_used` | Used memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_used_perc` | Used memory percentage on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_free` | Free memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_total` | Total memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_buffers` | Buffers memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_cache` | Cache memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_shared` | Shared memory on the node. <br><br>Type: gauge | `server` |
| `minio_system_memory_available` | Available memory on the node. <br><br>Type: gauge | `server` |

#### `/system/cpu` {#system-cpu}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_system_cpu_avg_idle` | Average CPU idle time. <br><br>Type: gauge | `server` |
| `minio_system_cpu_avg_iowait` | Average CPU IOWait time. <br><br>Type: gauge | `server` |
| `minio_system_cpu_load` | CPU load average 1min. <br><br>Type: gauge | `server` |
| `minio_system_cpu_load_perc` | CPU load average 1min (percentage). <br><br>Type: gauge | `server` |
| `minio_system_cpu_nice` | CPU nice time. <br><br>Type: gauge | `server` |
| `minio_system_cpu_steal` | CPU steal time. <br><br>Type: gauge | `server` |
| `minio_system_cpu_system` | CPU system time. <br><br>Type: gauge | `server` |
| `minio_system_cpu_user` | CPU user time. <br><br>Type: gauge | `server` |

#### `/system/network/internode` {#system-network-internode}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_system_network_internode_errors_total` | Total number of failed internode calls. <br><br>Type: counter | `server`, `pool_index` |
| `minio_system_network_internode_dial_errors_total` | Total number of internode TCP dial timeouts and errors. <br><br>Type: counter | `server`, `pool_index` |
| `minio_system_network_internode_dial_avg_time_nanos` | Average dial time of internodes TCP calls in nanoseconds. <br><br>Type: gauge | `server`, `pool_index` |
| `minio_system_network_internode_sent_bytes_total` | Total number of bytes sent to other peer nodes. <br><br>Type: counter | `server`, `pool_index` |
| `minio_system_network_internode_recv_bytes_total` | Total number of bytes received from other peer nodes. <br><br>Type: counter | `server`, `pool_index` |

#### `/system/process` {#system-process}

| Name | Description | Labels |
| --- | --- | --- |
| `minio_system_process_locks_read_total` | Number of current READ locks on this peer. <br><br>Type: gauge | `server` |
| `minio_system_process_locks_write_total` | Number of current WRITE locks on this peer. <br><br>Type: gauge | `server` |
| `minio_system_process_cpu_total_seconds` | Total user and system CPU time spent in seconds. <br><br>Type: counter | `server` |
| `minio_system_process_go_routine_total` | Total number of go routines running. <br><br>Type: gauge | `server` |
| `minio_system_process_io_rchar_bytes` | Total bytes read by the process from the underlying storage system including cache, /proc/\[pid\]/io rchar. <br><br>Type: counter | `server` |
| `minio_system_process_io_read_bytes` | Total bytes read by the process from the underlying storage system, /proc/\[pid\]/io read_bytes. <br><br>Type: counter | `server` |
| `minio_system_process_io_wchar_bytes` | Total bytes written by the process to the underlying storage system including page cache, /proc/\[pid\]/io wchar. <br><br>Type: counter | `server` |
| `minio_system_process_io_write_bytes` | Total bytes written by the process to the underlying storage system, /proc/\[pid\]/io write_bytes. <br><br>Type: counter | `server` |
| `minio_system_process_start_time_seconds` | Start time for MinIO process in seconds since Unix epoch. <br><br>Type: gauge | `server` |
| `minio_system_process_uptime_seconds` | Uptime for MinIO process in seconds. <br><br>Type: gauge | `server` |
| `minio_system_process_file_descriptor_limit_total` | Limit on total number of open file descriptors for the MinIO Server process. <br><br>Type: gauge | `server` |
| `minio_system_process_file_descriptor_open_total` | Total number of open file descriptors by the MinIO Server process. <br><br>Type: gauge | `server` |
| `minio_system_process_syscall_read_total` | Total read SysCalls to the kernel. /proc/\[pid\]/io syscr. <br><br>Type: counter | `server` |
| `minio_system_process_syscall_write_total` | Total write SysCalls to the kernel. /proc/\[pid\]/io syscw. <br><br>Type: counter | `server` |
| `minio_system_process_resident_memory_bytes` | Resident memory size in bytes. <br><br>Type: gauge | `server` |
| `minio_system_process_virtual_memory_bytes` | Virtual memory size in bytes. <br><br>Type: gauge | `server` |
| `minio_system_process_virtual_memory_max_bytes` | Maximum virtual memory size in bytes. <br><br>Type: gauge | `server` |
