---
title: "Silo 控制台"
url: "/zh/administration/minio-console/"
weight: 110
icon: fa-solid fa-display
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/minio-console.rst
upstream_modified: true
---

<a id="minio" data-td-print-local></a>
<a id="minio-console"></a>
<a id="id1" data-td-print-local></a>

MinIO Console 是一个功能丰富的图形用户界面，提供与 [`mc`](/zh/reference/minio-mc/#command-mc) 命令行工具类似的功能。

![Silo Console 登录页为已认证用户提供 Object Browser 视图](/images/silo-console/console-object-browser.webp){width="600"}

本页面概述了 MinIO Console，并说明其配置选项和登录方法。

<a id="id2" data-td-print-local></a>

## 概述 {#overview}

您可以使用 MinIO Console 执行多种管理任务，例如身份与访问管理、指标与日志监控或服务器配置。

[SILO 20261109](/zh/blog/release/silo-20261109/) 在服务端内嵌 [Console v2.7.0](/zh/blog/release/console-2.7.0/)（`4e91ae506e70`）。[Silo Console 仓库](https://github.com/pgsty/silo-console)记录下游源码、版本发布与兼容性变化；独立部署属于高级集成路径，必须选择与目标服务端版本兼容的 Console 版本。

在 [Console v2.7.0](/zh/blog/release/console-2.7.0/) 中，Console 界面提供十种语言（英语、简体中文、法语、德语、俄语、西班牙语、巴西葡萄牙语、日语、带从右向左布局的阿拉伯语与土耳其语），可通过语言菜单或命令面板切换（详见[设计记录](/zh/blog/design/console-languages/)）。Console 在 `/api/v1/docs` 提供基于 Redoc 3 的交互式 API 文档，其中 `/swagger.json` 直接路由至后端 API 而非前端 SPA 回退页。独立容器镜像 `docker.io/pgsty/silo-console:v2.7.0` 内置 UBI 系统根证书包（`/etc/ssl/certs/ca-certificates.crt`）与可写 `/tmp` 目录（权限 `1777`），支持出站 HTTPS 连接与大请求临时文件落盘。

<a id="id3" data-td-print-local></a>

### 支持的浏览器 {#supported-browsers}

MinIO Console 可运行于多种当前稳定版本的浏览器。

为获得最佳使用体验，请使用您所选浏览器的最新稳定版本。 支持的浏览器包括：

- Chrome
- Edge
- Safari
- Firefox
- Opera

此列表 *并不完整*，后续可能发生变化。

如需查看运行 MinIO Console 所支持的完整浏览器及版本列表，请参见 [Browserslist](https://browsersl.ist/#q=%3E0.2%25%2Cnot+dead+and+not+op_mini+all) 网站。

> [!NOTE]
> **提示**
>
> MinIO Console *不支持* Opera Mini。

<a id="id4" data-td-print-local></a>

## 配置 {#configuration}

MinIO Console 的大部分配置设置继承自 MinIO Server。以下环境变量用于启用 MinIO Console 中的特定行为：

<table>
  <thead>
    <tr>
      <th><p>环境变量</p></th>
      <th><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/zh/reference/minio-server/settings/console/#envvar.MINIO_PROMETHEUS_URL"><code>MINIO_PROMETHEUS_URL</code></a></p></td>
      <td><p>配置为从 MinIO 部署抓取指标的 Prometheus 服务器 URL。
MinIO Console 使用该服务器填充指标仪表板。</p><p>有关如何配置 Prometheus 以从 MinIO 收集指标的教程，请参见
<a href="/zh/operations/monitoring/collect-minio-metrics-using-prometheus/#minio-metrics-collect-using-prometheus">使用 Prometheus 进行监控与告警</a>。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-server/settings/console/#envvar.MINIO_BROWSER_REDIRECT_URL"><code>MINIO_BROWSER_REDIRECT_URL</code></a></p></td>
      <td><p>MinIO Console 对外可解析的主机名，供已配置的
<a href="/zh/administration/identity-access-management/#minio-authentication-and-identity-management">external identity manager</a> 返回认证响应时使用。</p><p>使用反向代理、负载均衡器或类似系统将 MinIO Console 暴露到公网时，
通常需要设置该变量。请指定一个可从外部访问并解析到 MinIO Console
的主机名。</p></td>
    </tr>
  </tbody>
</table>

<a id="id5" data-td-print-local></a>

<a id="minio-console-port-assignment" data-td-print-local></a>

### 静态端口分配与动态端口分配 {#static-vs-dynamic-port-assignment}

默认情况下，MinIO 会在每次服务器启动时为 MinIO Console 随机选择一个端口。 访问 MinIO Server 的浏览器客户端会被自动重定向到动态选定端口上的 MinIO Console。此行为模拟了旧版 Web 浏览器访问方式，同时降低了在 嵌入式 Console 更新前已运行 MinIO 的系统上发生端口冲突的风险。

您可以在启动部署中的每个 MinIO Server 时，通过传递 [`silo server --console-address`](/zh/reference/minio-server/#minio.server.-console-address) 命令行选项来显式指定静态端口。

例如，以下命令启动一个分布式 MinIO 部署，并为 MinIO Console 静态分配 `9001` 端口。该部署将在默认 MinIO 服务器端口 `:9000` 上响应 S3 API 操作，并在 MinIO Console 端口 `:9001` 上响应浏览器访问。

```shell
silo server https://minio-{1...4}.example.net/mnt/drive-{1...4} \
      --console-address ":9001"
```

位于网络路由组件之后且其路由规则要求使用静态端口的部署，可能需要为 MinIO Console 设置静态端口。例如，负载均衡器、反向代理或 Kubernetes ingress 可能会默认阻止动态重定向行为，或在该行为下表现异常。

您还必须确保主机系统防火墙允许访问已配置的 Console 端口。

<a id="id6" data-td-print-local></a>

<a id="minio-console-play-login" data-td-print-local></a>

## 登录 {#logging-in}

> [!NOTE]
> **变更: RELEASE.2023-03-09T23-16-13Z**

MinIO Console 会向未认证用户显示登录页面。 默认情况下，Console 为 [MinIO-managed user](/zh/administration/identity-access-management/minio-identity-management/#minio-internal-idp) 提供用户名和密码登录提示。

对于配置了多个 [identity managers](/zh/administration/identity-access-management/#minio-authentication-and-identity-management) 的部署， 请选择 **Other Authentication Methods** 下拉菜单，以选择其他已配置的身份提供商之一。 您也可以使用通过 [Security Token Service (STS)](/zh/developers/security-token-service/#minio-security-token-service) API 生成的凭证登录。

> [!NOTE]
> **使用本地 `docker.io/pgsty/silo` 容器评估体验 Console**
>
> 运行一次性本地容器即可体验内嵌 Console：
>
> ```shell
> docker run --rm -p 9000:9000 -p 9001:9001 \
>   -e MINIO_ROOT_USER=silo-admin \
>   -e MINIO_ROOT_PASSWORD=change-me-strong-secret \
>   docker.io/pgsty/silo:RELEASE.2026-11-09T00-00-00Z \
>   server /data --console-address ":9001"
> ```
>
> 在浏览器中打开 `http://127.0.0.1:9001`，使用配置的 root 凭证登录；也可以通过 [`mc`](/zh/reference/minio-mc/#command-mc)（`mcli`）连接 `http://127.0.0.1:9000`。

<a id="id7" data-td-print-local></a>

## 文档 {#documentation}

**Documentation** 链接会在新浏览器标签页中按界面语言打开本文档站点：当界面选择简体中文时打开 `/zh/` 中文文档，其余界面语言均打开英文文档。Console 同时在 `/api/v1/docs` 提供基于 Redoc 3 的 API 文档（由 `/swagger.json` 驱动）。

<a id="id8" data-td-print-local></a>

## 可用任务 {#available-tasks}

登录 MinIO Console 后，用户可以执行多种任务。

- [管理对象](/zh/administration/console/managing-objects/#minio-console-managing-objects)，包括浏览或上传对象、管理存储桶设置或创建层。
- [查看或修改身份与安全配置](/zh/administration/console/security-and-access/#minio-console-security-access)，包括访问密钥、策略和身份提供商设置。
- [监控健康状态与活动](/zh/administration/console/managing-deployment/#minio-console-managing-deployment)，包括指标、通知或站点复制。
- [运行本地诊断并下载健康报告](/zh/administration/console/subnet-registration/#minio-console-subscription)，无需上传外部遥测数据或注册商业许可证。
