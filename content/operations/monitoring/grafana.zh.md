---
title: "使用 Grafana 监控 MinIO Server"
url: "/zh/operations/monitoring/grafana/"
weight: 40
minio_origin: true
silo_modified: false
---

<a id="grafana-minio-server"></a>
<a id="minio-grafana"></a>

无论指标存储在何处，[Grafana](https://grafana.com/) 都允许你对其进行查询、可视化、告警和分析。

## 前提条件 {#id2}

- 已有 [Prometheus 部署](https://prometheus.io/docs/prometheus/latest/installation/)，并配置 [Alert Manager](https://prometheus.io/docs/alerting/latest/overview/)
- 已有可通过网络访问 Prometheus 部署的 MinIO 部署
- [已安装 Grafana](https://grafana.com/grafana/download)

{{% alert color="info" %}}
**Grafana 仪表板使用 metrics version 2**

MinIO 的 Grafana 仪表板使用 [metrics version 2](/zh/operations/monitoring/metrics-v2/#minio-metrics-v2)。 关于指标 API 版本的更多信息，请参见 [指标与告警](/zh/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts)。

对于 version 3 指标，你需要自行创建仪表板。 关于仪表板的更多信息，请参见 [Grafana 文档](https://grafana.com/docs/grafana/latest/dashboards/)。
{{% /alert %}}

## MinIO Grafana 仪表板 {#id3}

MinIO 提供了若干官方 Grafana 仪表板，可从 Grafana Dashboard 门户下载。

1. [MinIO Server 指标](#minio-server-grafana-metrics)
2. [MinIO 存储桶指标](#minio-buckets-grafana-metrics)
3. [MinIO 复制指标](#minio-replication-grafana-metrics)

若要跟踪 Grafana 仪表板的变更，可以查看 MinIO Server GitHub 仓库中 [server](https://github.com/minio/minio/blob/master/docs/metrics/prometheus/grafana/minio-dashboard.json) 或 [bucket](https://github.com/minio/minio/blob/master/docs/metrics/prometheus/grafana/minio-bucket.json) 仪表板对应的 JSON 文件。

<a id="minio-server-grafana-metrics"></a>

### MinIO Server 指标仪表板 {#minio-server}

可以使用 [Grafana dashboard portal](https://grafana.com/grafana/dashboards/13502-minio-dashboard/) 上提供的 MinIO 官方 Grafana 仪表板来可视化 MinIO Server 指标。

MinIO 为 MinIO Server 指标提供了专用的 Grafana 仪表板。 关于该仪表板配置的详细信息，请参见 [GitHub 上的 JSON 文件](https://raw.githubusercontent.com/minio/minio/master/docs/metrics/prometheus/grafana/minio-dashboard.json)。

对于启用了 [服务端加密](/zh/operations/server-side-encryption/#minio-sse-data-encryption) 的 MinIO 部署（包括 SSE-KMS 或 SSE-S3），该仪表板还包含 KMS 指标。 这些指标包括状态、请求错误率和请求成功率。

<img src="/images/grafana-minio.png" alt="MinIO Grafana 仪表板示例，展示了 MinIO Server 上采集的多种指标。" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />

<a id="minio-buckets-grafana-metrics"></a>

### MinIO 存储桶指标仪表板 {#minio}

可以使用 [Grafana dashboard portal](https://grafana.com/grafana/dashboards/19237-minio-bucket-dashboard/) 上提供的 MinIO 官方 Grafana 仪表板来可视化 MinIO 存储桶指标。

存储桶指标可以通过 [GitHub 上的 bucket JSON 文件](https://raw.githubusercontent.com/minio/minio/master/docs/metrics/prometheus/grafana/bucket/minio-bucket.json) 在 Grafana 仪表板中查看。

<img src="/images/grafana-bucket.png" alt="MinIO Grafana 仪表板示例，展示了 MinIO 存储桶的多种采集指标。" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />

<a id="id4"></a>

### MinIO 节点指标仪表板 {#minio-node-grafana-metrics}

节点指标可以通过 [GitHub 上的 node JSON 文件](https://raw.githubusercontent.com/minio/minio/master/docs/metrics/prometheus/grafana/node/minio-node.json) 在 Grafana 仪表板中查看。

<img src="/images/grafana-node.png" alt="MinIO Grafana 仪表板示例，展示了 MinIO 节点的多种采集指标。" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />

<a id="id5"></a>

### MinIO 复制指标仪表板 {#minio-replication-grafana-metrics}

可以使用 [Grafana dashboard portal](https://grafana.com/grafana/dashboards/15305-minio-replication-dashboard/) 上提供的 MinIO 官方复制仪表板来可视化复制指标。

集群复制指标可以通过 [GitHub 上的 cluster replication JSON 文件](https://raw.githubusercontent.com/minio/minio/master/docs/metrics/prometheus/grafana/replication/minio-replication-cluster.json) 在 Grafana 仪表板中查看。

<img src="/images/grafana-replication.png" alt="MinIO Grafana 仪表板示例，展示了复制相关的多种采集指标。" style="max-width: (&#x27;600px&#x27;, &#x27;auto&#x27;);" />
