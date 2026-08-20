---
title: "mc admin prometheus metrics"
url: "/reference/minio-mc-admin/mc-admin-prometheus-metrics/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-prometheus-metrics.rst
upstream_modified: false
---

<a id="mc-admin-prometheus-metrics"></a>

<a id="command-mc.admin.prometheus.metrics"></a>

## Description {#description}

The [`mc admin prometheus metrics`](#command-mc.admin.prometheus.metrics) command prints Prometheus metrics for a cluster.

The output includes additional information about each metric, such as if its value is a `counter` or `gauge`.

For more complete documentation on using MinIO with Prometheus, see [How to monitor MinIO server with Prometheus](/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus)

Starting with MinIO Server [RELEASE.2024-07-15T19-02-30Z](https://github.com/minio/minio/releases/tag/RELEASE.2024-07-15T19-02-30Z) and MinIO Client [RELEASE.2024-07-11T18-01-28Z](https://github.com/minio/mc/releases/tag/RELEASE.2024-07-11T18-01-28Z), [metrics version 3 (v3)](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) provides additional endpoints and metrics. To print v3 metrics use the `--api_version v3` option.

MinIO recommends new deployments use [version 3 (v3)](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts). Existing deployments can continue to use [metrics version 2](/operations/monitoring/metrics-v2/#minio-metrics-v2)

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

{{< tabs group="example-syntax" >}}
{{< tab label="EXAMPLE" value="example" >}}
The following command prints cluster metrics from the deployment at [alias](/glossary/#term-alias) `myminio`:

```shell
mc admin prometheus metrics myminio cluster
```
{{< /tab >}}
{{< tab label="SYNTAX" value="syntax" >}}
The command has the following syntax:

```shell
mc [GLOBALFLAGS] admin prometheus metrics  \
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

##### `ALIAS` {#mc.admin.prometheus.metrics.ALIAS}

*mc-cmd*

*Required*

The [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment for which the command prints metrics.

##### `--api-version` {#mc.admin.prometheus.metrics.-api-version}

*mc-cmd*

*Optional*

To print [version 3 (v3)](/operations/monitoring/metrics-and-alerts/#minio-metrics-and-alerts) metrics, include an `--api-version v3` parameter. `v3` is the only accepted value.

Omit `--api-version` to print [version 2 (v2)](/operations/monitoring/metrics-v2/#minio-metrics-v2) metrics.

##### `--bucket` {#mc.admin.prometheus.metrics.-bucket}

*mc-cmd*

*Optional*

Requires [`--api-version`](#mc.admin.prometheus.metrics.-api-version). For v3 metric types that return bucket-level metrics, specify a bucket name.

`--bucket` works for the following v3 metric types:

- `api`
- `replication`

The following example prints API metrics for the bucket `mybucket`:

```shell
mc admin prometheus metrics ALIAS api --bucket mybucket --api-version v3
```

##### `TYPE` {#mc.admin.prometheus.metrics.TYPE}

*mc-cmd*

*Optional*

The type of metrics to print.

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

### Print v3 metrics {#print-v3-metrics}

Use [`mc admin prometheus metrics --api-version v3`](#mc.admin.prometheus.metrics.-api-version) to print all available v3 metrics and their current values for a MinIO deployment:

```shell
mc admin prometheus metrics ALIAS --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

To print a specific type of metrics, include the [`TYPE`](#mc.admin.prometheus.metrics.TYPE). The following prints all scanner metrics for a deployment:

```shell
mc admin prometheus metrics ALIAS scanner --api-version v3
```

### Print v3 API or bucket replication metrics {#print-v3-api-or-bucket-replication-metrics}

Certain v3 metric types accept a [`--bucket`](#mc.admin.prometheus.metrics.-bucket) parameter to specify the bucket for which to print metrics. The following example prints v3 replication metrics for bucket `mybucket`:

```shell
mc admin prometheus metrics ALIAS replication --bucket mybucket --api-version v3
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

To print API metrics for the bucket, replace `replication` with `api`.

### Print v2 cluster metrics {#print-v2-cluster-metrics}

By default, [`mc admin prometheus metrics`](#command-mc.admin.prometheus.metrics) prints v2 cluster metrics:

```shell
mc admin prometheus metrics ALIAS
```

- Replace `ALIAS` with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

### Print other types of v2 metrics {#print-other-types-of-v2-metrics}

To print another type of v2 metrics, specify the desired [`TYPE`](#mc.admin.prometheus.metrics.TYPE). The following example prints v2 bucket metrics:

```shell
mc admin prometheus metrics ALIAS bucket
```

Accepted values are `bucket`, `cluster`, `node`, and `resource`.
