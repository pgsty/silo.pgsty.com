---
title: "Silo Console 设置"
url: "/zh/reference/minio-server/settings/console/"
weight: 50
minio_origin: true
silo_modified: true
---

<a id="minio-console"></a>
<a id="minio-server-envvar-console"></a>

{{% alert color="info" %}}
**变更: RELEASE.2025-05-24T17-08-30Z**

Console 现在仅提供对象浏览能力，类似于通过 [`mc`](/zh/reference/minio-mc/#command-mc) 工具可用的能力。 对于用户管理等管理类交互，请使用 [`mc admin`](/zh/reference/minio-mc-admin/#command-mc.admin) 命令。

本页中的部分设置可能已不再适用于较新的部署。
{{% /alert %}}

本页介绍用于管理 MinIO Console 访问与行为的设置。

你可以通过以下方式建立或修改设置：

- 在启动或重启 MinIO Server 之前，在宿主机系统上定义 *环境变量*。 如何定义环境变量，请参考所用操作系统的文档。
- 使用 [`mc admin config set`](/zh/reference/minio-mc-admin/mc-admin-config/#mc.admin.config.set) 定义 *配置项*。

如果同时定义了环境变量和对应的配置项，MinIO 使用环境变量的值。

有些设置只有环境变量或配置项中的一种，而不是两者同时存在。

{{% alert color="warning" %}}
**重要**

每个配置项都会控制 MinIO 的基础行为和功能。 MinIO **强烈建议** 先在 DEV 或 QA 等较低级别环境中测试配置变更，再应用到生产环境。
{{% /alert %}}

## 浏览器设置 {#id2}

以下设置用于控制内嵌 MinIO Console 的行为。

### MinIO Console {#id3}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER` {#envvar.MINIO_BROWSER}

*envvar*

指定 `off` 以禁用内嵌 MinIO Console。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 动画 {#id4}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_LOGIN_ANIMATION` {#envvar.MINIO_BROWSER_LOGIN_ANIMATION}

*envvar*

{{% alert color="info" %}}
**新增: MinIO**

Server RELEASE.2023-05-04T21-44-30Z
{{% /alert %}}

指定 `off` 以禁用 MinIO Console 的动画登录界面。 默认为 `on`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 浏览器重定向 {#id5}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_REDIRECT` {#envvar.MINIO_BROWSER_REDIRECT}

*envvar*

{{% alert color="info" %}}
**新增: MinIO**

Server RELEASE.2023-09-16T01-01-47Z
{{% /alert %}}

指定是否将来自 Web 浏览器的请求自动重定向到 Console 地址。 默认为 `true`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 浏览器重定向 URL {#url}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_REDIRECT_URL` {#envvar.MINIO_BROWSER_REDIRECT_URL}

*envvar*

指定 MinIO Console 监听传入连接的 Fully Qualified Domain Name (FQDN)。

如果你希望 MinIO Console 仅通过反向代理服务对外提供，必须指定由该服务管理的主机名。

例如，假设某个反向代理被配置为将 `https://example.net/minio/` 路由到 MinIO Console。 你必须将此环境变量设置为与该主机名一致，这样 Console 才会使用该主机名进行监听并响应请求。

如果省略此变量，Console 会在运行 MinIO Server 的主机所关联的所有 IP 地址或主机名上监听并响应。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 会话时长 {#id6}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_SESSION_DURATION` {#envvar.MINIO_BROWSER_SESSION_DURATION}

*envvar*

{{% alert color="info" %}}
**新增: MinIO**

Server RELEASE.2023-08-23T10-07-06Z
{{% /alert %}}

指定使用 MinIO Console 时浏览器会话的持续时间。

MinIO 支持以下时间单位：

- `s` - 秒，”60s”
- `m` - 分钟，”60m”
- `h` - 小时，”24h”
- `d` - 天，”7d”

默认为 `12h`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 日志查询 URL {#id7}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_LOG_QUERY_URL` {#envvar.MINIO_LOG_QUERY_URL}

*envvar*

指定 PostgreSQL 服务的 URL，MinIO 会将 [Audit logs](/zh/operations/monitoring/minio-logging/#minio-logging-publish-audit-logs) 写入该服务。 内嵌 MinIO Console 提供日志搜索工具，可查询 PostgreSQL 服务中收集的日志。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### 内容安全策略 {#id8}

*可选*

将 MinIO Console 配置为在 HTTP 响应中生成 [Content-Security-Policy](https://en.wikipedia.org/wiki/Content_Security_Policy) 头。 默认为 `default-src 'self' 'unsafe-eval' 'unsafe-inline';`

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_CONTENT_SECURITY_POLICY` {#envvar.MINIO_BROWSER_CONTENT_SECURITY_POLICY}

*envvar*

```shell
export MINIO_BROWSER_CONTENT_SECURITY_POLICY="default-src 'self' 'unsafe-eval' 'unsafe-inline';"
```

{{% /tab %}}
{{% tab header="配置项" %}}

##### `browser csp_policy` {#mc-conf.browser.csp_policy}

*mc-conf*

```shell
mc admin config set browser \
   csp_policy="default-src 'self' 'unsafe-eval' 'unsafe-inline';" \
   [ARGUMENT=VALUE ...]
```

{{% /tab %}}
{{< /tabpane >}}

### 严格传输安全 {#id9}

*可选*

将 MinIO Console 配置为在 HTTP 响应中生成 [Strict-Transport-Security](https://en.wikipedia.org/wiki/HTTP_Strict_Transport_Security) 头。

要生成该头，你 **必须** 使用 [`MINIO_BROWSER_HSTS_SECONDS`](#envvar.MINIO_BROWSER_HSTS_SECONDS) 或 [`hsts_seconds`](#mc-conf.browser.hsts_seconds) 设置持续时间。 其他 HSTS 设置是可选的。

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_HSTS_SECONDS` {#envvar.MINIO_BROWSER_HSTS_SECONDS}

*envvar*

已配置策略生效的 `max_age`（秒）。 默认为 `0`，即禁用。 你 **必须** 配置 *非零* 时长，才能启用 `Strict-Transport-Security` 头。

```shell
export MINIO_BROWSER_HSTS_SECONDS=31536000
```

##### `MINIO_BROWSER_HSTS_INCLUDE_SUB_DOMAINS` {#envvar.MINIO_BROWSER_HSTS_INCLUDE_SUB_DOMAINS}

*envvar*

设置为 `on` 可将已配置的 HSTS 策略同时应用到所有 MinIO Console 子域名。 默认为 `off`。

```shell
export MINIO_BROWSER_HSTS_INCLUDE_SUB_DOMAINS="on"
```

##### `MINIO_BROWSER_HSTS_PRELOAD` {#envvar.MINIO_BROWSER_HSTS_PRELOAD}

*envvar*

设置为 `on` 可指示客户端浏览器将 MinIO Console 域名加入其 HSTS 预加载列表。 默认为 `off`。

```shell
export MINIO_BROWSER_HSTS_PRELOAD="on"
```

{{% /tab %}}
{{% tab header="配置项" %}}
以下配置项需要重启服务后才会生效。 要重启服务，请使用 [`mc admin service restart`](/zh/reference/minio-mc-admin/mc-admin-service/#mc.admin.service.restart)。

##### `browser hsts_seconds` {#mc-conf.browser.hsts_seconds}

*mc-conf*

已配置策略生效的 `max_age`（秒）。 默认为 `0`，即禁用。 你 **必须** 配置 *非零* 时长，才能启用 `Strict-Transport-Security` 头。

```shell
mc admin config set browser \
   hsts_seconds="31536000" \
   [ARGUMENT=VALUE ...]
```

##### `browser hsts_include_subdomains` {#mc-conf.browser.hsts_include_subdomains}

*mc-conf*

设置为 `on` 可将已配置的 HSTS 策略同时应用到所有 MinIO Console 子域名。 默认为 `off`。

```shell
mc admin config set browser \
   hsts_include_subdomains="on" \
   hsts_seconds="31536000" \
   [ARGUMENT=VALUE ...]
```

##### `browser hsts_preload` {#mc-conf.browser.hsts_preload}

*mc-conf*

设置为 `on` 可指示客户端浏览器将 MinIO Console 域名加入其 HSTS 预加载列表。 默认为 `off`。

```shell
mc admin config set browser \
   hsts_preload="on" \
   hsts_seconds="31536000" \
   [ARGUMENT=VALUE ...]
```

{{% /tab %}}
{{< /tabpane >}}

#### 示例 {#id10}

以下示例展示了给定配置项对应的渲染后响应头。 等价的环境变量会生成相同结果。 所有示例均使用 `31536000`，即一个自然年（365 天）的秒数。

`hsts_seconds`

> ```shell
> mc admin config set ALIAS browser hsts_seconds=31536000
> ```
>
> ```shell
> Strict-Transport-Security: max-age=31536000
> ```

`hsts_include_subdomains`

> ```shell
> mc admin config set ALIAS browser hsts_seconds=31536000 hsts_include_subdomains=on
> ```
>
> ```shell
> Strict-Transport-Security: max-age=31536000; includeSubDomains
> ```

`hsts_preload`

> ```shell
> mc admin config set ALIAS browser hsts_seconds=31536000 hsts_include_subdomains=on hsts_preload=on
> ```
>
> ```shell
> Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
> ```

### 来源策略 {#id11}

*可选*

将 MinIO Console 配置为在 HTTP 响应中生成 [Referrer-Policy](https://www.w3.org/TR/referrer-policy/) 头。 默认为 `strict-origin-when-cross-origin`。

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_BROWSER_REFERRER_POLICY` {#envvar.MINIO_BROWSER_REFERRER_POLICY}

*envvar*

```shell
export MINIO_BROWSER_REFERRER_POLICY="strict-origin-when-cross-origin"
```

{{% /tab %}}
{{% tab header="配置项" %}}

##### `browser referrer_policy` {#mc-conf.browser.referrer_policy}

*mc-conf*

```shell
mc admin config set browser \
   referrer_policy="strict-origin-when-cross-origin" \
   [ARGUMENT=VALUE ...]
```

{{% /tab %}}
{{< /tabpane >}}

## Prometheus 设置 {#prometheus}

以下设置用于管理 MinIO 与你的 Prometheus 服务之间的交互方式。

### Prometheus URL {#prometheus-url}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_PROMETHEUS_URL` {#envvar.MINIO_PROMETHEUS_URL}

*envvar*

指定已配置为 [抓取 MinIO 指标](/zh/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus) 的 Prometheus 服务 URL。

MinIO Console 使用 `minio-job` Prometheus 抓取作业，将集群指标填充到 **Dashboard**。

如果你使用独立的 MinIO Console 进程，则该变量对应 `CONSOLE_PROMETHEUS_URL`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### Prometheus Job ID {#prometheus-job-id}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_PROMETHEUS_JOB_ID` {#envvar.MINIO_PROMETHEUS_JOB_ID}

*envvar*

指定用于 [抓取 MinIO 指标](/zh/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus) 的自定义 Prometheus job ID。

MinIO 默认为 `minio-job`。

如果你使用独立的 MinIO Console 进程，则该变量对应 `CONSOLE_PROMETHEUS_JOB_ID`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}

### Prometheus Auth Token {#prometheus-auth-token}

*可选*

{{< tabpane text=true persist=header >}}
{{% tab header="环境变量" %}}

##### `MINIO_PROMETHEUS_AUTH_TOKEN` {#envvar.MINIO_PROMETHEUS_AUTH_TOKEN}

*envvar*

指定 Console 连接 Prometheus 服务时应使用的 [basic auth token](https://prometheus.io/docs/guides/basic-auth/)。

例如，你使用的 basic auth token 可能如下所示：

```text
eyJhbGciOiJIUzUxMiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJwcm9tZXRoZXVzIiwic3ViIjoibWluaW8iLCJleHAiOjQ4NTAwMzg0MDJ9.GZCKR3d0FH2TCvNHSd39HaVfSuQVVV0s8glICBDmhT51V6CQ_hw8gTYlKHJmcpR8aHkqiJwCqcYJhaMmqwe00XY
```

如果你使用独立的 MinIO Console 进程，则该变量对应 `CONSOLE_PROMETHEUS_AUTH_TOKEN`。
{{% /tab %}}
{{% tab header="配置项" %}}
此设置没有对应的配置变量。 请改用环境变量。
{{% /tab %}}
{{< /tabpane >}}
