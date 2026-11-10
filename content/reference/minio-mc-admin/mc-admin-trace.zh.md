---
title: "mc admin trace"
url: "/zh/reference/minio-mc-admin/mc-admin-trace/"
weight: 170
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/reference/minio-mc-admin/mc-admin-trace.rst
upstream_modified: true
---

<a id="mc-admin-trace"></a>

<a id="command-mc.admin.trace"></a>

<a id="id2" data-td-print-local></a>

## 说明 {#description}

[`mc admin trace`](#command-mc.admin.trace) 命令显示目标 MinIO 部署上发生的 API 操作。

> [!NOTE]
> **服务端兼容性**
>
> [`mcli admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 正式支持的目标服务端为 SILO。与未修改的上游 MinIO 保持尽最大努力兼容；仅具备通用 S3 兼容性并不提供这些管理 API。

<a id="id3" data-td-print-local></a>

## 示例 {#examples}

<a id="api" data-td-print-local></a>

### 监控所有 API 操作 {#monitor-all-api-operations}

使用 [`mc admin trace`](#command-mc.admin.trace) 监控 MinIO 部署上的 API 操作：

```shell
mc admin trace -a ALIAS
```

- 将 [`ALIAS`](#mc.admin.trace.TARGET) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

<a id="id4" data-td-print-local></a>

### 查看返回 503 错误的调用 {#see-calls-that-return-503-errors}

使用 [`mc admin trace`](#command-mc.admin.trace) 监控返回 503 Service Unavailable 错误的 API 操作：

```shell
mc admin trace -v --status-code 503 ALIAS
```

- 将 [`ALIAS`](#mc.admin.trace.TARGET) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

<a id="id5" data-td-print-local></a>

### 查看指定路径的控制台跟踪 {#see-console-trace-for-a-path}

使用 [`mc admin trace`](#command-mc.admin.trace) 监控指定路径的活动：

```shell
mc admin trace --path my-bucket/my-prefix/* ALIAS
```

- 将 [`ALIAS`](#mc.admin.trace.TARGET) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `my-bucket/my-prefix/*` 替换为你要跟踪的存储桶、前缀和对象名称或通配符。

<a id="mb" data-td-print-local></a>

### 查看响应大小大于 1Mb 的控制台跟踪 {#see-console-trace-for-a-response-size-greater-than-1mb}

使用 [`mc admin trace`](#command-mc.admin.trace) 监控超过指定大小的响应：

```shell
mc admin trace --filter-response --filter-size 1Mb ALIAS
```

- 将 [`ALIAS`](#mc.admin.trace.TARGET) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。
- 将 `1Mb` 替换为所需的响应大小。

<a id="ms" data-td-print-local></a>

### 查看请求操作时长大于 5ms 的控制台跟踪 {#see-console-trace-for-a-request-operation-durations-greater-than-5ms}

使用 [`mc admin trace`](#command-mc.admin.trace) 监控耗时较长的操作：

```shell
mc admin trace --response-duration 5ms ALIAS
```

- 将 [`ALIAS`](#mc.admin.trace.TARGET) 替换为 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)。

<a id="id6" data-td-print-local></a>

## 语法 {#syntax}

[`mc admin trace`](#command-mc.admin.trace) 的语法如下：

```shell
mc admin trace [FLAGS] TARGET
```

[`mc admin trace`](#command-mc.admin.trace) 支持以下参数：

#### `TARGET` {#mc.admin.trace.TARGET}

*mc-cmd*

指定已配置 MinIO 部署的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias)，用于监控其 API 操作。

#### `--all, a` {#mc.admin.trace.-all}

*mc-cmd*

返回 MinIO 部署上的所有流量，包括 MinIO 服务器之间的节点间流量。

#### `--call` {#mc.admin.trace.-call}

*mc-cmd*

仅跟踪匹配的客户端操作或调用类型。 例如，以下命令仅跟踪 `scanner` 类型的操作。

```shell
mc admin trace --call scanner TARGET
```

有效的调用类型包括：

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

如果未指定，MinIO 返回 `s3` 类型的调用。

#### `--errors, e` {#mc.admin.trace.-errors}

*mc-cmd*

仅返回失败的 API 操作。

#### `--filter-request` {#mc.admin.trace.-filter-request}

*mc-cmd*

跟踪请求大小大于指定 [`--filter-size`](#mc.admin.trace.-filter-size) 值的客户端操作或调用。

必须与 [`--filter-size`](#mc.admin.trace.-filter-size) 标志一起使用。

#### `--filter-response` {#mc.admin.trace.-filter-response}

*mc-cmd*

跟踪响应大小大于指定 [`--filter-size`](#mc.admin.trace.-filter-size) 值的客户端操作或调用。

必须与 [`--filter-size`](#mc.admin.trace.-filter-size) 标志一起使用。

#### `--filter-size` {#mc.admin.trace.-filter-size}

*mc-cmd*

过滤后的客户端操作或调用的大小限制。

必须与 [`--filter-request`](#mc.admin.trace.-filter-request) 或 [`--filter-response`](#mc.admin.trace.-filter-response) 标志之一一起使用。

有效单位包括：

| 后缀 | 单位大小                        |
| ---- | ------------------------------- |
| `k`  | KB（Kilobyte，1000 Bytes）      |
| `m`  | MB（Megabyte，1000 Kilobytes）  |
| `g`  | GB（Gigabyte，1000 Megabytes）  |
| `t`  | TB（Terrabyte，1000 Gigabytes） |
| `ki` | KiB（Kibibyte，1024 Bites）     |
| `mi` | MiB（Mebibyte，1024 Kibibytes） |
| `gi` | GiB（Gibibyte，1024 Mebibytes） |
| `ti` | TiB（Tebibyte，1024 Gibibytes） |
{.wide .expand}

#### `--funcname` {#mc.admin.trace.-funcname}

*mc-cmd*

返回输入函数名对应的调用。

#### `--method` {#mc.admin.trace.-method}

*mc-cmd*

返回指定 HTTP 方法的调用。

#### `--node` {#mc.admin.trace.-node}

*mc-cmd*

返回指定服务器的调用。

#### `--path` {#mc.admin.trace.-path}

*mc-cmd*

返回指定路径的调用。

#### `--request-header` {#mc.admin.trace.-request-header}

*mc-cmd*

返回与提供的请求头匹配的调用。

#### `--request-query` {#mc.admin.trace.-request-query}

*mc-cmd*

返回与提供的请求查询参数匹配的调用。

#### `--response-duration` {#mc.admin.trace.-response-duration}

*mc-cmd*

跟踪响应时长大于指定值的调用。

<a id="mc.admin.trace.-response-threshold"></a>

`--response-threshold` 不是当前 mcli 支持的标志。请改用 `--response-duration 5ms` 筛选慢于 5 毫秒的调用。未指定该标志时，不会应用响应时长阈值。

#### `--status-code` {#mc.admin.trace.-status-code}

*mc-cmd*

返回指定 HTTP 状态码的调用。

#### `--stats` {#mc.admin.trace.-stats}

*mc-cmd*

在当前跟踪会话期间，为每个被跟踪的函数调用累积聚合统计信息。

输出表包含以下列。

| 列         | 说明                                                                                |
| ---------- | ----------------------------------------------------------------------------------- |
| `Call`     | 捕获到的客户端操作或函数名称。                                                      |
| `Count`    | 客户端操作或调用发生的次数。                                                        |
| `RPM`      | 客户端操作或调用的每分钟速率（Rate Per Minute，RPM）。                              |
| `Avg Time` | 客户端操作或调用完成所需的平均时间。                                                |
| `Min Time` | 客户端操作或调用完成所用的最短时间。                                                |
| `Max Time` | 客户端操作或调用完成所用的最长时间。                                                |
| `Avg TTFB` | 客户端操作或调用响应的平均首字节时间（Time To First Byte，TTFB）。                  |
| `Max TTFB` | 客户端操作或调用响应的最大首字节时间。                                              |
| `Avg Size` | 客户端操作或调用响应的平均大小。                                                    |
| `Errors`   | 因错误失败的客户端操作或调用数量。                                                  |
| `RX Avg`   | 客户端操作或调用的平均接收字节数（Bytes Received，RX）。仅在值不为零（`0`）时显示。 |
| `TX AVG`   | 客户端操作或调用的平均发送字节数（Bytes Sent，TX）。仅在值不为零（`0`）时显示。     |
{.wide .expand}

> [!NOTE]
> **新增: RELEASE.2023-11-15T22-45-58Z**
>
> `Avg TTFB` 与 `Max TTFB` 统计列新增于 `RELEASE.2023-11-15T22-45-58Z`。

累积统计信息，例如名称、计数、持续时间、最短时间、最长时间、首字节时间或错误。 最多累积 15 条统计条目。

#### `--verbose` {#mc.admin.trace.-verbose}

*mc-cmd*

返回详细输出。

<a id="id7" data-td-print-local></a>

### 全局标志 {#global-flags}

此命令支持 [全局标志](/zh/reference/minio-mc/#minio-mc-global-options) 中的任意选项。
