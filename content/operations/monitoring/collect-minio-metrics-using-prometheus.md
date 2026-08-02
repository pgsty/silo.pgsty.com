---
title: "Monitoring and Alerting using Prometheus"
url: "/operations/monitoring/collect-minio-metrics-using-prometheus/"
weight: 10
minio_origin: true
silo_modified: false
---

<a id="monitoring-and-alerting-using-prometheus"></a>
<a id="minio-metrics-collect-using-prometheus"></a>

- [Monitoring with MinIO and Prometheus: Overview](https://youtu.be/A3vCDaFWNNs?ref=docs)
- [Monitoring with MinIO and Prometheus: Lab](https://youtu.be/Oix9iXndSUY?ref=docs)

MinIO publishes cluster, node, bucket, and resource metrics using the [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/#data-model). The procedure on this page documents the following:

- Configuring a Prometheus service to scrape and display metrics from a MinIO deployment
- Configuring an Alert Rule on a MinIO Metric to trigger an AlertManager action

These instructions use [version 2 metrics.](/operations/monitoring/metrics-v2/#minio-metrics-v2) For more about metrics API versions, see [Metrics and alerts.](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)

{{% alert color="info" %}}
**Prerequisites**

This procedure requires the following:

- An existing [Prometheus deployment](https://prometheus.io/docs/prometheus/latest/installation/) with backing [Alert Manager](https://prometheus.io/docs/alerting/latest/overview/)
- An existing MinIO deployment with network access to the Prometheus deployment
- An [`mc`](/reference/minio-mc/#command-mc) installation on your local host configured to [access](/reference/minio-mc/mc-alias-set/#alias) the MinIO deployment
{{% /alert %}}

## Configure Prometheus to Collect and Alert using MinIO Metrics {#configure-prometheus-to-collect-and-alert-using-minio-metrics}

### 1) Generate the Scrape Configuration {#generate-the-scrape-configuration}

Use the [`mc admin prometheus generate`](/reference/minio-mc-admin/mc-admin-prometheus-generate/#command-mc.admin.prometheus.generate) command to generate the scrape configuration for use by Prometheus in making scraping requests:

{{< tabpane text=true persist=header >}}
{{% tab header="MinIO Server" %}}
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
{{% /tab %}}
{{% tab header="Nodes" %}}
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
{{% /tab %}}
{{% tab header="Buckets" %}}
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
{{% /tab %}}
{{% tab header="Resources" %}}
{{% alert color="info" %}}
**Added: RELEASE.2023-10-07T15-07-38Z**

{{% /alert %}}

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
{{% /tab %}}
{{< /tabpane >}}

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

{{< tabpane text=true persist=header >}}
{{% tab header="Cluster" %}}
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
{{% /tab %}}
{{% tab header="Nodes" %}}
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
{{% /tab %}}
{{% tab header="Bucket" %}}
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
{{% /tab %}}
{{% tab header="Resource" %}}
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
{{% /tab %}}
{{< /tabpane >}}

Start the Prometheus cluster using the configuration file:

```shell
prometheus --config.file=prometheus.yaml
```

### 3) Analyze Collected Metrics {#analyze-collected-metrics}

Prometheus includes an [expression browser](https://prometheus.io/docs/prometheus/latest/getting_started/#using-the-expression-browser). You can execute queries here to analyze the collected metrics.

{{< tabpane text=true persist=header >}}
{{% tab header="Examples" %}}
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
{{% /tab %}}
{{% tab header="Recommended Metrics" %}}
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
{{% /tab %}}
{{< /tabpane >}}

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
