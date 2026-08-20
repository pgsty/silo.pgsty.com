---
title: "mc admin trace"
url: "/reference/minio-mc-admin/mc-admin-trace/"
weight: 170
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-trace.rst
upstream_modified: false
---

<a id="mc-admin-trace"></a>

<a id="command-mc.admin.trace"></a>

## Description {#description}

The [`mc admin trace`](#command-mc.admin.trace) command displays API operations occurring on the target MinIO deployment.

> [!NOTE]
> **Use `mc admin` on MinIO Deployments Only**
>
> MinIO does not support using [`mc admin`](/reference/minio-mc-admin/#command-mc.admin) commands with other S3-compatible services, regardless of their claimed compatibility with MinIO deployments.

## Examples {#examples}

### Monitor All API operations {#monitor-all-api-operations}

Use [`mc admin trace`](#command-mc.admin.trace) to monitor API operations on a MinIO deployment:

```shell
mc admin trace -a ALIAS
```

- Replace [`ALIAS`](#mc.admin.trace.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

### See Calls that Return 503 Errors {#see-calls-that-return-503-errors}

Use [`mc admin trace`](#command-mc.admin.trace) to monitor API operations that return a service unavailable 503 error:

```shell
mc admin trace -v --status-code 503 ALIAS
```

- Replace [`ALIAS`](#mc.admin.trace.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

### See Console Trace for a Path {#see-console-trace-for-a-path}

Use [`mc admin trace`](#command-mc.admin.trace) to monitor activity for a specific path:

```shell
mc admin trace --path my-bucket/my-prefix/* ALIAS
```

- Replace [`ALIAS`](#mc.admin.trace.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace `my-bucket/my-prefix/*` with the bucket, prefix, and object name or wildcard you wish to trace.

### See Console Trace for a Response Size Greater than 1Mb {#see-console-trace-for-a-response-size-greater-than-1mb}

Use [`mc admin trace`](#command-mc.admin.trace) to monitor responses over a specific size:

```shell
mc admin trace --filter-response --filter-size 1Mb ALIAS
```

- Replace [`ALIAS`](#mc.admin.trace.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.
- Replace `1Mb` with the desired response size.

### See Console Trace for a Request Operation Durations Greater than 5ms {#see-console-trace-for-a-request-operation-durations-greater-than-5ms}

Use [`mc admin trace`](#command-mc.admin.trace) to monitor long operations:

```shell
mc admin trace --filter-duration --filter-size 5ms ALIAS
```

- Replace [`ALIAS`](#mc.admin.trace.TARGET) with the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of the MinIO deployment.

## Syntax {#syntax}

[`mc admin trace`](#command-mc.admin.trace) has the following syntax:

```shell
mc admin trace [FLAGS] TARGET
```

[`mc admin trace`](#command-mc.admin.trace) supports the following argument:

#### `TARGET` {#mc.admin.trace.TARGET}

*mc-cmd*

Specify the [`alias`](/reference/minio-mc/mc-alias/#command-mc.alias) of a configured MinIO deployment for which to monitor API operations.

#### `--all, a` {#mc.admin.trace.-all}

*mc-cmd*

Returns all traffic on the MinIO deployment, including internode traffic between MinIO servers.

#### `--call` {#mc.admin.trace.-call}

*mc-cmd*

Traces only matching client operation or call types. For example, the following command only traces operations of the type `scanner`.

```shell
mc admin trace --call scanner TARGET
```

Valid call types include:

- `batch-keyrotation`
- `batch-replication`
- `bootstrap`
- `decommission`
- `ftp`
- `healing`
- `ilm`
- `internal`
- `os`
- `rebalance`
- `replication-resync`
- `s3`
- `scanner`
- `storage`

If not specified, MinIO returns call types of `s3`.

#### `--errors, e` {#mc.admin.trace.-errors}

*mc-cmd*

Returns failed API operations only.

#### `--filter-request` {#mc.admin.trace.-filter-request}

*mc-cmd*

Trace client operations or calls with request size greater than the specified [`--filter-size`](#mc.admin.trace.-filter-size) value.

Must be used with [`--filter-size`](#mc.admin.trace.-filter-size) flag.

#### `--filter-response` {#mc.admin.trace.-filter-response}

*mc-cmd*

Trace client operations or calls with response size greater than the specified [`--filter-size`](#mc.admin.trace.-filter-size) value.

Must be used with [`--filter-size`](#mc.admin.trace.-filter-size) flag.

#### `--filter-size` {#mc.admin.trace.-filter-size}

*mc-cmd*

Size limit of a filtered client operation or call.

Must be used with either [`--filter-request`](#mc.admin.trace.-filter-request) or [`--filter-response`](#mc.admin.trace.-filter-response) flag.

Valid units include:

| Suffix | Unit Size |
| --- | --- |
| `k` | KB (Kilobyte, 1000 Bytes) |
| `m` | MB (Megabyte, 1000 Kilobytes) |
| `g` | GB (Gigabyte, 1000 Megabytes) |
| `t` | TB (Terrabyte, 1000 Gigabytes) |
| `ki` | KiB (Kibibyte, 1024 Bites) |
| `mi` | MiB (Mebibyte, 1024 Kibibytes) |
| `gi` | GiB (Gibibyte, 1024 Mebibytes) |
| `ti` | TiB (Tebibyte, 1024 Gibibytes) |

#### `--funcname` {#mc.admin.trace.-funcname}

*mc-cmd*

Returns calls for the entered function name.

#### `--method` {#mc.admin.trace.-method}

*mc-cmd*

Returns call of the specified HTTP method.

#### `--node` {#mc.admin.trace.-node}

*mc-cmd*

Returns calls for the specified server.

#### `--path` {#mc.admin.trace.-path}

*mc-cmd*

Returns calls for the specified path.

#### `--request-header` {#mc.admin.trace.-request-header}

*mc-cmd*

Returns calls matching the supplied request header.

#### `--request-query` {#mc.admin.trace.-request-query}

*mc-cmd*

Returns calls matching the supplied request query parameter. This debug option should only be used at the direction of MinIO Support.

#### `--response-duration` {#mc.admin.trace.-response-duration}

*mc-cmd*

Trace calls with response duration greater than the specified value.

#### `--response-threshold` {#mc.admin.trace.-response-threshold}

*mc-cmd*

Takes a time string as a value, such as `5ms`. Returns only calls with a response time greater than the supplied threshold.

If not specified, MinIO returns calls with a response time greater than 5ms.

#### `--status-code` {#mc.admin.trace.-status-code}

*mc-cmd*

Returns calls of the specified HTTP status code.

#### `--stats` {#mc.admin.trace.-stats}

*mc-cmd*

Accumulates aggregated statistics for each traced function call during the current trace session.

The output table includes the following columns.

<table>
  <tbody>
    <tr>
      <td><p>Call</p></td>
      <td><p>The name of the captured client operation or function.</p></td>
    </tr>
    <tr>
      <td><p>Count</p></td>
      <td><p>The number of times the client operation or call occurred.</p></td>
    </tr>
    <tr>
      <td><p>RPM</p></td>
      <td><p>The Rate Per Minute (RPM) of the client operation or call.</p></td>
    </tr>
    <tr>
      <td><p>Avg Time</p></td>
      <td><p>The average time required for the client operation or call to complete.</p></td>
    </tr>
    <tr>
      <td><p>Min Time</p></td>
      <td><p>The minimum time spent for the client operation or call to complete.</p></td>
    </tr>
    <tr>
      <td><p>Max Time</p></td>
      <td><p>The maximum time spent for the client operation or call to complete.</p></td>
    </tr>
    <tr>
      <td><p>Avg TTFB</p></td>
      <td><aside class="alert alert-info"><p><strong>Added: RELEASE.2023-11-15T22-45-58Z</strong></p></aside><p>The average Time To First Byte (TTFB) for the client operation or call response.</p></td>
    </tr>
    <tr>
      <td><p>Max TTFB</p></td>
      <td><aside class="alert alert-info"><p><strong>Added: RELEASE.2023-11-15T22-45-58Z</strong></p></aside><p>The maximum Time To First Byte for the client operation or call response.</p></td>
    </tr>
    <tr>
      <td><p>Avg Size</p></td>
      <td><p>Average size of client operation or call responses.</p></td>
    </tr>
    <tr>
      <td><p>Errors</p></td>
      <td><p>The number of client operations or calls that failed with an error.</p></td>
    </tr>
    <tr>
      <td><p>RX Avg</p></td>
      <td><p>The average number of Bytes Received (RX) for the client operation or call.
This stat only displays if not zero (0).</p></td>
    </tr>
    <tr>
      <td><p>TX AVG</p></td>
      <td><p>The average number of Bytes Sent (TX) for the client operation or call.
This stat only displays if not zero (0).</p></td>
    </tr>
  </tbody>
</table>

Accumulate stats, such as name, count, duration, min time, max time, time to first byte, or errors. Accumulates up to 15 stat entries.

#### `--verbose` {#mc.admin.trace.-verbose}

*mc-cmd*

Returns verbose output.

### Global Flags {#global-flags}

This command supports any of the [global flags](/reference/minio-mc/#minio-mc-global-options).
