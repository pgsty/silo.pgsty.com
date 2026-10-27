---
title: "Monitoring and Alerting using Prometheus"
url: "/operations/monitoring/collect-minio-metrics-using-prometheus/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring/collect-minio-metrics-using-prometheus.rst
upstream_modified: true
---

**SILO 20261026 / Console 2.5.1:** The Console Metrics page queries Metrics V3, aggregating across nodes while distinguishing true zero values from missing data. Overview capacity shows the raw capacity reported by the Server (rather than an erasure-coded usable capacity estimate); the bucket list is read live, whereas object counts and usage statistics come from the background scanner. See the [Console release notes](/blog/release/console-2.5.1/#interface) and [metric mapping reference](https://github.com/pgsty/silo-console/blob/v2.5.1/docs/metrics-v3.md).

<a id="monitoring-and-alerting-using-prometheus"></a>
<a id="minio-metrics-collect-using-prometheus"></a>

- [Monitoring with MinIO and Prometheus: Overview](https://youtu.be/A3vCDaFWNNs?ref=docs)
- [Monitoring with MinIO and Prometheus: Lab](https://youtu.be/Oix9iXndSUY?ref=docs)

MinIO publishes cluster, node, bucket, and resource metrics using the [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/#data-model). The procedure on this page documents the following:

- Configuring a Prometheus service to scrape and display metrics from a MinIO deployment
- Configuring an Alert Rule on a MinIO Metric to trigger an AlertManager action

## Recommended Metrics V3 scraping for 20261026 {#metrics-v3}

New deployments and the Console 2.5 Metrics page should scrape Metrics V3. Pass `--api-version v3` explicitly with mcli 20261026:

```shell
mcli admin prometheus generate mysilo --api-version v3
```

The generated configuration scrapes `/minio/metrics/v3` and includes the required bearer token. Merge it into your Prometheus configuration, set `targets` to the SILO nodes being monitored, keep the bearer token secret, and verify that scrapes succeed before enabling alert rules. You can restrict collection to specific categories such as `cluster` or `system`, though the full Console dashboard requires its corresponding metric families; see the [command reference](/reference/minio-mc-admin/mc-admin-prometheus-generate/).

- **Cluster metric deduplication:** Multiple nodes export identical `cluster` metrics for the same cluster. Deduplicate within each cluster using `max` or `min` while preserving cluster identity labels—do not sum these series across nodes.
- **Zero values vs. missing data:** Some legitimate zero values omit samples. Fill in zero only when a companion metric with the same lifecycle is present; failed scrapes or scanner usage metrics that have not yet been populated should remain no-data.
- **Labels and units:** V3 API metrics use the `name` label, node metrics carry `server`, drive metrics carry `pool`/`set`/`drive` indexes, and durations are reported in seconds. Update PromQL queries and alert thresholds accordingly when migrating from V2 dashboards.

The [V2 metric](/operations/monitoring/metrics-v2/#minio-metrics-v2) scraping and alerting procedure below is retained for existing dashboards (omitting `--api-version` still generates a V2 scrape configuration).

> [!NOTE]
> **Prerequisites**
>
> This procedure requires the following:
>
> - An existing [Prometheus deployment](https://prometheus.io/docs/prometheus/latest/installation/) with backing [Alert Manager](https://prometheus.io/docs/alerting/latest/overview/)
> - An existing MinIO deployment with network access to the Prometheus deployment
> - An [`mc`](/reference/minio-mc/#command-mc) installation on your local host configured to [access](/reference/minio-mc/mc-alias-set/#alias) the MinIO deployment

## Configure Prometheus to Collect and Alert using MinIO Metrics {#configure-prometheus-to-collect-and-alert-using-minio-metrics}

### 1) Generate the Scrape Configuration {#generate-the-scrape-configuration}

Use the [`mc admin prometheus generate`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate) command to generate the scrape configuration for use by Prometheus in making scraping requests:

{{< tabs group="minio-server-nodes-buckets-resources" >}}
{{< tab label="MinIO Server" value="minio-server" >}}
The following command scrapes metrics for the MinIO cluster.

```shell
mc admin prometheus generate ALIAS
```

Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#mc.admin.prometheus.generate.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The command returns output similar to the following:

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/cluster
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< tab label="Nodes" value="nodes" >}}
The following command scrapes metrics for a node on the MinIO Server.

```shell
mc admin prometheus generate ALIAS node
```

Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#mc.admin.prometheus.generate.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-node
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/node
     scheme: https
     static_configs:
     - targets: [minio-1.example.net, minio-2.example.net, minio-N.example.net]
```
{{< /tab >}}
{{< tab label="Buckets" value="buckets" >}}
The following command scrapes metrics for buckets on the MinIO Server.

```shell
mc admin prometheus generate ALIAS bucket
```

Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#mc.admin.prometheus.generate.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-bucket
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/bucket
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< tab label="Resources" value="resources" >}}
> [!NOTE]
> **Added: RELEASE.2023-10-07T15-07-38Z**

The following command scrapes metrics for resources on the MinIO Server.

```shell
mc admin prometheus generate ALIAS resource
```

Replace [`ALIAS`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#mc.admin.prometheus.generate.ALIAS) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-resource
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/resource
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< /tabs >}}

- Set an appropriate `scrape_interval` value to ensure each scraping operation completes before the next one begins. The recommended value is 60 seconds.

  Some deployments require a longer scrape interval due to the number of metrics being scraped. To reduce the load on your MinIO and Prometheus servers, choose the longest interval that meets your monitoring requirements.
- Set the `job_name` to a value associated to the MinIO deployment.

  Use a unique value to ensure isolation of the deployment metrics from any others collected by that Prometheus service.
- MinIO deployments started with [`MINIO_PROMETHEUS_AUTH_TYPE`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_PROMETHEUS_AUTH_TYPE) set to `"public"` can omit the `bearer_token` field.
- Set the `scheme` to http for MinIO deployments not using TLS.
- Set the `targets` array with a hostname that resolves to the MinIO deployment.

  This can be any single node, or a load balancer/proxy which handles connections to the MinIO nodes.

  For MinIO Tenants on Kubernetes infrastructure, when using a Prometheus cluster in that same cluster you can specify the service DNS name for the `minio` service. You can otherwise specify the ingress or load balancer endpoint configured to route connections to and from the MinIO Tenant.

### 2) Restart Prometheus with the Updated Configuration {#restart-prometheus-with-the-updated-configuration}

Append the desired `scrape_configs` job generated in the previous step to the configuration file:

{{< tabs group="cluster-nodes-bucket-resource" >}}
{{< tab label="Cluster" value="cluster" >}}
Cluster metrics aggregate node-level metrics and, where appropriate, attach labels to metrics for the originating node.

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/cluster
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< tab label="Nodes" value="nodes" >}}
Node metrics are specific for node-level monitoring. You need to list all MinIO nodes for this configuration.

```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-node
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/node
     scheme: https
     static_configs:
     - targets: [minio-1.example.net, minio-2.example.net, minio-N.example.net]
```
{{< /tab >}}
{{< tab label="Bucket" value="bucket" >}}
```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-bucket
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/bucket
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< tab label="Resource" value="resource" >}}
```yaml
global:
   scrape_interval: 60s

scrape_configs:
   - job_name: minio-job-resource
     bearer_token: TOKEN
     metrics_path: /minio/v2/metrics/resource
     scheme: https
     static_configs:
     - targets: [minio.example.net]
```
{{< /tab >}}
{{< /tabs >}}

Start the Prometheus cluster using the configuration file:

```shell
prometheus --config.file=prometheus.yaml
```

### 3) Analyze Collected Metrics {#analyze-collected-metrics}

Prometheus includes an [expression browser](https://prometheus.io/docs/prometheus/latest/getting_started/#using-the-expression-browser). You can execute queries here to analyze the collected metrics.

{{< tabs group="examples-recommended-metrics" >}}
{{< tab label="Examples" value="examples" >}}
The following query examples return metrics collected by Prometheus every five minutes for a scrape job named `minio-job`:

```shell
minio_node_drive_free_bytes{job="minio-job"}[5m]
minio_node_drive_free_inodes{job="minio-job"}[5m]

minio_node_drive_latency_us{job="minio-job"}[5m]

minio_node_drive_offline_total{job="minio-job"}[5m]
minio_node_drive_online_total{job="minio-job"}[5m]

minio_node_drive_total{job="minio-job"}[5m]

minio_node_drive_total_bytes{job="minio-job"}[5m]
minio_node_drive_used_bytes{job="minio-job"}[5m]

minio_node_drive_errors_timeout{job="minio-job"}[5m]
minio_node_drive_errors_availability{job="minio-job"}[5m]

minio_node_drive_io_waiting{job="minio-job"}[5m]
```
{{< /tab >}}
{{< tab label="Recommended Metrics" value="recommended-metrics" >}}
MinIO recommends the following as a basic set of metrics to monitor.

See [Metrics and alerts](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) for information about all available metrics.

| Metric | Description |
| --- | --- |
| `minio_node_drive_free_bytes` | Total storage available on a drive. |
| `minio_node_drive_free_inodes` | Total free inodes. |
| `minio_node_drive_latency_us` | Average last minute latency in µs for drive API storage operations. |
| `minio_node_drive_offline_total` | Total drives offline in this node. |
| `minio_node_drive_online_total` | Total drives online in this node. |
| `minio_node_drive_total` | Total drives in this node. |
| `minio_node_drive_total_bytes` | Total storage on a drive. |
| `minio_node_drive_used_bytes` | Total storage used on a drive. |
| `minio_node_drive_errors_timeout` | Total number of drive timeout errors since server start. |
| `minio_node_drive_errors_availability` | Total number of drive I/O errors, permission denied and timeouts since server start. |
| `minio_node_drive_io_waiting` | Total number of I/O operations waiting on drive. |
{{< /tab >}}
{{< /tabs >}}

### 4) Configure an Alert Rule using MinIO Metrics {#configure-an-alert-rule-using-minio-metrics}

You must configure [Alert Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) on the Prometheus deployment to trigger alerts based on collected MinIO metrics.

The following example alert rule files provide a baseline of alerts for a MinIO deployment. You can modify or otherwise use these examples as guidance in building your own alerts.

```yaml
groups:
- name: minio-alerts
  rules:
  - alert: NodesOffline
    expr: avg_over_time(minio_cluster_nodes_offline_total{job="minio-job"}[5m]) > 0
    for: 10m
    labels:
      severity: warn
    annotations:
      summary: "Node down in MinIO deployment"
      description: "Node(s) in cluster {{ $labels.instance }} offline for more than 5 minutes"

  - alert: DisksOffline
    expr: avg_over_time(minio_cluster_drive_offline_total{job="minio-job"}[5m]) > 0
    for: 10m
    labels:
      severity: warn
    annotations:
      summary: "Disks down in MinIO deployment"
      description: "Disks(s) in cluster {{ $labels.instance }} offline for more than 5 minutes"
```

In the Prometheus configuration, specify the path to the alert file in the `rule_files` key:

```yaml
rule_files:
- minio-alerting.yml
```

Once triggered, Prometheus sends the alert to the configured AlertManager service.

## Dashboards {#dashboards}

MinIO provides Grafana Dashboards to display metrics collected by Prometheus. For more information, see [Monitor a MinIO Server with Grafana](/operations/monitoring/grafana/#minio-grafana)
