---
title: "Monitoring and Alerts"
url: "/operations/monitoring/"
weight: 40
icon: fa-solid fa-chart-line
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/monitoring.rst
upstream_modified: false
---

<a id="monitoring-and-alerts"></a>

- [Monitoring with MinIO and Prometheus: Overview](https://youtu.be/A3vCDaFWNNs?ref=docs)
- [Monitoring with MinIO and Prometheus: Lab](https://youtu.be/Oix9iXndSUY?ref=docs)

## Metrics and Alerts {#metrics-and-alerts}

MinIO publishes point-in-time metrics using the [Prometheus Data Model](https://prometheus.io/docs/concepts/data_model/). You can use any scraping tool which supports that data model to pull those metrics into a database for populating historical views, performing query/analysis of metrics data, or creating alerts on preferred data points.

The following table lists tutorials for integrating MinIO metrics with select third-party monitoring software.

<table>
  <tbody>
    <tr>
      <td><p><a href="/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus">Monitoring and Alerting using Prometheus</a></p></td>
      <td><p>Configure Prometheus to Monitor and Alert for a MinIO deployment</p></td>
    </tr>
    <tr>
      <td><p><a href="/operations/monitoring/monitor-and-alert-using-influxdb/#minio-metrics-influxdb">Monitoring and Alerting using InfluxDB</a></p></td>
      <td><p>Configure InfluxDB to Monitor and Alert for a MinIO deployment.</p></td>
    </tr>
  </tbody>
</table>

Other metrics and analytics software suites which support the Prometheus data model may work regardless of their inclusion on the above list.

## Logging {#logging}

MinIO publishes all [`minio server`](/reference/minio-server/#command-minio.server) operations to the system console. MinIO also supports publishing server logs and audit logs to an HTTP webhook.

- [Server logs](/operations/monitoring/minio-logging/#minio-logging-publish-server-logs) contain the same [`minio server`](/reference/minio-server/#command-minio.server) operations logged to the system console. Server logs support general monitoring and troubleshooting of operations.
- [Audit logs](/operations/monitoring/minio-logging/#minio-logging-publish-audit-logs) are more granular descriptions of each operation on the MinIO deployment. Audit logging supports security standards and regulations which require detailed tracking of operations.

MinIO publishes logs as a JSON document as a `PUT` request to each configured endpoint. The endpoint server is responsible for processing each JSON document. MinIO requires explicit configuration of each webhook endpoint and does *not* publish logs to a webhook by default.

See [Publish Server or Audit Logs to an External Service](/operations/monitoring/minio-logging/#minio-logging) for more complete documentation.

## Healthchecks {#healthchecks}

MinIO exposes unauthenticated endpoints for probing node uptime and cluster [high availability](/operations/concepts/erasure-coding/#minio-ec-parity) for simple healthchecks. These endpoints return only an HTTP status code. See [Healthcheck API](/operations/monitoring/healthcheck-probe/#minio-healthcheck-api) for more information.
