---
title: "Monitoring and Alerting using InfluxDB"
url: "/operations/monitoring/monitor-and-alert-using-influxdb/"
weight: 20
minio_origin: true
silo_modified: false
---

<a id="monitoring-and-alerting-using-influxdb"></a>
<a id="minio-metrics-influxdb"></a>

MinIO publishes cluster and node metrics using the [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/). [InfluxDB](https://www.influxdata.com/?ref=minio) supports scraping MinIO metrics data for monitoring and alerting.

The procedure on this page documents the following:

- Configuring an InfluxDB service to scrape and display metrics from a MinIO deployment
- Configuring an Alert on a MinIO metric

{{% alert color="info" %}}
**Prerequisites**

This procedure requires the following:

- An existing InfluxDB deployment configured with one or more [notification endpoints](https://docs.influxdata.com/influxdb/v2.4/notification-endpoints/)
- An existing MinIO deployment with network access to the InfluxDB deployment
- An [`mc`](/reference/minio-mc/#command-mc) installation on your local host configured to [access](/reference/minio-mc/mc-alias-set/#alias) the MinIO deployment

These instructions use [version 2 metrics.](/operations/monitoring/metrics-v2/#minio-metrics-v2) For more about metrics API versions, see [Metrics and alerts.](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)
{{% /alert %}}

For MinIO Deployments on Kubernetes, this procedure assumes all necessary network control components, such as Ingress or Load Balancers, to facilitate access between the MinIO Tenant and the InfluxDB service.

## Configure InfluxDB to Collect and Alert using MinIO Metrics {#configure-influxdb-to-collect-and-alert-using-minio-metrics}

{{% alert color="warning" %}}
**Important**

This procedure specifically uses the InfluxDB UI to create a scraping endpoint.

The InfluxDB UI does not provide the same level of configuration as using [Telegraf](https://docs.influxdata.com/telegraf/v1.24/) and the corresponding [Prometheus plugin](https://github.com/influxdata/telegraf/blob/release-1.24/plugins/inputs/prometheus/README.md). Specifically:

- You cannot enable authenticated access to the MinIO metrics endpoint via the InfluxDB UI
- You cannot set a tag for collected metrics (e.g. `url_tag`) for uniquely identifying the metrics for a given MinIO deployment

The Telegraf Prometheus plugin also supports Kubernetes-specific features, such as scraping the `minio` service for a given MinIO Tenant.

Configuring Telegraf is out of scope for this procedure. You can use this procedure as general guidance for configuring Telegraf to scrape MinIO metrics.
{{% /alert %}}

1. Configure Public Access to MinIO Metrics

   Set the [`MINIO_PROMETHEUS_AUTH_TYPE`](/reference/minio-server/settings/metrics-and-logging/#envvar.MINIO_PROMETHEUS_AUTH_TYPE) environment variable to `"public"` for all nodes in the MinIO deployment. You can then restart the deployment to allow public access to MinIO metrics.

   You can validate the change by attempting to `curl` the metrics endpoint:

   ```shell
   curl https://HOSTNAME/minio/v2/metrics/cluster
   ```

   Replace `HOSTNAME` with the URL of the load balancer or reverse proxy through which you access the MinIO deployment. You can alternatively specify any single node as `HOSTNAME:PORT`, specifying the MinIO server API port in addition to the node hostname.

   The response body should include a list of collected MinIO metrics.
2. Log into the InfluxDB UI and Create a Bucket

   Select the [Organization](https://docs.influxdata.com/influxdb/v2.4/organizations/view-orgs/) under which you want to store MinIO metrics.

   Create a [New Bucket](https://docs.influxdata.com/influxdb/v2.4/organizations/buckets/create-bucket/) in which to store metrics for the MinIO deployment.
3. Create a new Scraping Source

   Create a [new InfluxDB Scraper](https://docs.influxdata.com/influxdb/v2.4/write-data/no-code/scrape-data/manage-scrapers/create-a-scraper/).

   Specify the full URL to the MinIO deployment, including the metrics endpoint:

   ```shell
   https://HOSTNAME/minio/v2/metrics/cluster
   ```

   Replace `HOSTNAME` with the URL of the load balancer or reverse proxy through which you access the MinIO deployment. You can alternatively specify any single node as `HOSTNAME:PORT`, specifying the MinIO server API port in addition to the node hostname.
4. Validate the Data

   Use the [DataExplorer](https://docs.influxdata.com/influxdb/v2.4/query-data/execute-queries/data-explorer/) to visualize the collected MinIO data.

   For example, you can set a filter on `minio_cluster_capacity_usable_total_bytes` and `minio_cluster_capacity_usable_free_bytes` to compare the total usable against total free space on the MinIO deployment.
5. Configure a Check

   Create a [new Check](https://docs.influxdata.com/influxdb/v2.4/https://docs.influxdata.com/influxdb/v2.4/monitor-alert/checks/create/) on a MinIO metric.

   The following example check rules provide a baseline of alerts for a MinIO deployment. You can modify or otherwise use these examples for guidance in building your own checks.

   - Create a **Threshold Check** named `MINIO_NODE_DOWN`.

     Set the filter for the `minio_cluster_nodes_offline_total` key.

     Set the **Thresholds** to **WARN** when the value is greater than **1**
   - Create a **Threshold Check** named `MINIO_QUORUM_WARNING`.

     Set the filter for the `minio_cluster_drive_offline_total` key.

     Set the **Thresholds** to **CRITICAL** when the value is one less than your configured [Erasure Code Parity](/operations/concepts/erasure-coding/#minio-erasure-coding) setting.

     For example, a deployment using EC:4 should set this value to `3`.

   Configure your [Notification endpoints](https://docs.influxdata.com/influxdb/v2.4/monitor-alert/notification-endpoints/) and [Notification rules](https://docs.influxdata.com/influxdb/v2.4/monitor-alert/notification-rules/) such that checks of each type trigger an appropriate response.
