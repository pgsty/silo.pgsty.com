---
title: "mc admin prometheus generate"
url: "/reference/minio-mc-admin/mc-admin-prometheus-generate/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-prometheus-generate.rst
upstream_modified: false
---

<a id="mc-admin-prometheus-generate"></a>

<a id="command-mc.admin.prometheus.generate"></a>

## Description {#description}

The [`mc admin prometheus generate`](#command-mc.admin.prometheus.generate) command generates a metrics scraping configuration file for use with [Prometheus](https://prometheus.io/).

For more complete documentation on using MinIO with Prometheus, see [How to monitor MinIO server with Prometheus](/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus)

Starting with MinIO Server [RELEASE.2024-07-15T19-02-30Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-07-15T19-02-30Z) and MinIO Client [RELEASE.2024-07-11T18-01-28Z](https://github.com/minio/mc/releases/tag/RELEASE.2024-07-11T18-01-28Z), [metrics version 3 (v3)](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) provides additional endpoints and metrics. To generate a v3 scrape configuration use the `--api_version v3` option.

MinIO recommends new deployments use [version 3 (v3)](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts). Existing deployments can continue to use [metrics version 2](/operations/monitoring/metrics-v2/#minio-metrics-v2)

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command generates a Prometheus scrape configuration that collects version 2 bucket metrics from the deployment at [alias](/glossary/#term-alias) `myminio`:

```shell
mc admin prometheus generate myminio bucket
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin prometheus generate                                        \
                                  ALIAS                                           \
                                  [TYPE]                                          \
                                  [--api_version v3]                              \
                                  [--bucket <bucket name>]
```

- Brackets `[]` indicate optional parameters.
- Parameters sharing a line are mutually dependent.
- Parameters separated using the pipe `|` operator are mutually exclusive.

Copy the example to a text editor and modify as-needed before running the command in the terminal/shell.
{{< /tab >}}
{{< /tabs >}}

### Parameters {#parameters}

##### `ALIAS` {#mc.admin.prometheus.generate.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment for which the command generates a Prometheus-compatible configuration file.

##### `--api-version` {#mc.admin.prometheus.generate.-api-version}

*mc-cmd*

*Optional*

To generate a scrape configuration for [v3 metrics](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts), include an `--api-version v3` parameter. `v3` is the only accepted value.

Omit `--api-version` to generate a [v2 metrics](/operations/monitoring/metrics-v2/#minio-metrics-v2) configuration.

##### `--bucket` {#mc.admin.prometheus.generate.-bucket}

*mc-cmd*

*Optional*

Only valid for v3 metrics.

For v3 metric types that return bucket-level metrics, specify a bucket name. Requires [`--api-version`](#mc.admin.prometheus.generate.-api-version).

`--bucket` works for the following v3 metric types:

- `api`
- `replication`

The following example generates a configuration for API metrics from the bucket `mybucket`:

```shell
mc admin prometheus generate ALIAS api --bucket mybucket --api-version v3
```

##### `TYPE` {#mc.admin.prometheus.generate.TYPE}

*mc-cmd*

*Optional*

The type of metrics to scrape.

> Valid values for metrics version 3 are:
>
> - `api`
> - `audit`
> - `cluster`
> - `debug`
> - `ilm`
> - `logger`
> - `notification`
> - `replication`
> - `scanner`
> - `system`
>
> If not specified, a `v3` command returns all metrics.
>
> Valid values for metrics version 2 are:
>
> - `bucket`
> - `cluster`
> - `node`
> - `resource`
>
> If not specified, a `v2` command returns cluster metrics. Cluster metrics include rollups of certain node metrics.

### Global flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).

## Examples {#examples}

### Generate a default metrics v3 config {#generate-a-default-metrics-v3-config}

Use [`mc admin prometheus generate --api-version v3`](#mc.admin.prometheus.generate.-api-version) to generate a scrape configuration that collects all v3 metrics for a MinIO deployment:

```shell
mc admin prometheus generate ALIAS --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
scrape_configs:
- job_name: minio-job
  bearer_token: [auth token]
  metrics_path: /minio/metrics/v3
  scheme: http
  static_configs:
  - targets: ['localhost:9000']
```

### Generate a v3 metrics config for another type {#generate-a-v3-metrics-config-for-another-type}

To generate a configuration for another metric type, specify the type. The following generates a scrape configuration for v3 cluster metrics:

```shell
mc admin prometheus generate ALIAS cluster --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
scrape_configs:
- job_name: minio-job-cluster
  bearer_token: [auth token]
  metrics_path: /minio/metrics/v3/cluster
  scheme: http
  static_configs:
  - targets: ['localhost:9000']
```

To generate a configuration for a [`different metric type`](#mc.admin.prometheus.generate.TYPE), replace `cluster` with the desired type.

### Generate a v3 bucket replication metrics config {#generate-a-v3-bucket-replication-metrics-config}

The following example generates a scrape configuration for v3 replication metrics of bucket `mybucket`:

```shell
mc admin prometheus generate ALIAS replication --bucket mybucket --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
scrape_configs:
- job_name: minio-job-replication
  bearer_token: [auth token]
  metrics_path: /minio/metrics/v3/bucket/replication/mybucket
  scheme: https
  static_configs:
  - targets: [`localhost:9000`]
```

### Generate a v3 config for bucket API metrics {#generate-a-v3-config-for-bucket-api-metrics}

The following example generates a scrape configuration for v3 API metrics for bucket `mybucket`:

```shell
mc admin prometheus generate ALIAS api --bucket mybucket --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
scrape_configs:
- job_name: minio-job-api
  bearer_token: [auth token]
  metrics_path: /minio/metrics/v3/bucket/api/mybucket
  scheme: https
  static_configs:
  - targets: [`localhost:9000`]
```

### Generate a default metrics v2 config {#generate-a-default-metrics-v2-config}

By default, [`mc admin prometheus generate`](#command-mc.admin.prometheus.generate) generates a scrape configuration for v2 cluster metrics:

```shell
mc admin prometheus generate ALIAS
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

The output resembles the following:

```shell
scrape_configs:
- job_name: minio-job
  bearer_token: [auth token]
  metrics_path: /minio/v2/metrics
  scheme: http
  static_configs:
  - targets: ['localhost:9000']
```

### Generate a v2 config for other metric types {#generate-a-v2-config-for-other-metric-types}

To generate a configuration for another metric type, specify the type. The following generates a scrape configuration for v2 bucket metrics:

```shell
mc admin prometheus generate ALIAS bucket
```
