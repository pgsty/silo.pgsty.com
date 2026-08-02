---
title: "MinIO 管理客户端"
url: "/zh/reference/minio-mc-admin/"
weight: 20
icon: fa-solid fa-user-gear
minio_origin: true
silo_modified: false
---

<a id="minio"></a>

<a id="command-mc.admin"></a>

MinIO 客户端 [`mc`](/zh/reference/minio-mc/#command-mc) 命令行工具提供 [`mc admin`](#command-mc.admin) 命令， 用于在 MinIO 部署上执行管理任务。

虽然 [`mc`](/zh/reference/minio-mc/#command-mc) 支持任意兼容 S3 的服务， [`mc admin`](#command-mc.admin) *仅* 支持 MinIO 部署。

[`mc admin`](#command-mc.admin) 语法如下：

```shell
mc admin [FLAGS] COMMAND [ARGUMENTS]
```

## 命令速查 {#id2}

下表列出了 [`mc admin`](#command-mc.admin) 命令：

<table>
  <thead>
    <tr>
      <th><p>命令</p></th>
      <th><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey"><code>mc admin accesskey</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-accesskey/#command-mc.admin.accesskey"><code>mc admin accesskey</code></a> 命令及其子命令用于为 MinIO 部署中内部管理的用户创建和管理 <a href="/zh/administration/identity-access-management/minio-user-management/#minio-idp-service-account">Access Keys</a>。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-cluster-bucket/#command-mc.admin.cluster.bucket"><code>mc admin cluster bucket</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-cluster-bucket/#command-mc.admin.cluster.bucket"><code>mc admin cluster bucket</code></a> 命令及其子命令提供了用于手动导入和导出 MinIO 存储桶元数据的工具。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-cluster-iam/#command-mc.admin.cluster.iam"><code>mc admin cluster iam</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-cluster-iam/#command-mc.admin.cluster.iam"><code>mc admin cluster iam</code></a> 命令及其子命令提供了用于手动导入和导出 MinIO <a href="/zh/administration/identity-access-management/#minio-authentication-and-identity-management">身份与访问管理（IAM）</a> 元数据的工具。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission"><code>mc admin decommission</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission"><code>mc admin decommission</code></a> 命令用于启动 MinIO <a href="/zh/operations/concepts/#minio-intro-server-pool">服务器池s</a>
的下线流程。下线流程适用于移除较旧的服务器池，这些服务器池的硬件能力或性能已不再满足要求，
或相较部署中的其他池表现不足。MinIO 会根据每个池可用空闲空间的比例，自动将数据从被下线
的池迁移到部署中其余的池。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-group/#command-mc.admin.group"><code>mc admin group</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-group/#command-mc.admin.group"><code>mc admin group</code></a> 命令用于管理 MinIO 部署上的组。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-heal/#command-mc.admin.heal"><code>mc admin heal</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-heal/#command-mc.admin.heal"><code>mc admin heal</code></a> 命令会扫描受损或损坏的对象，并对这些对象执行自愈。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a> 命令显示 MinIO 服务器的信息。
对于分布式 MinIO 部署，<a href="/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info"><code>mc admin info</code></a> 会显示部署中每个 MinIO
服务器的信息。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-kms-key/#command-mc.admin.kms.key"><code>mc admin kms key</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-kms-key/#command-mc.admin.kms.key"><code>mc admin kms key</code></a> 命令通过 MinIO Key Encryption Service (KES)
执行加密密钥管理操作。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs"><code>mc admin logs</code></a></p></td>
      <td><p>使用 <a href="/zh/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs"><code>mc admin logs</code></a> 命令显示 MinIO 服务器日志。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy"><code>mc admin policy</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-policy/#command-mc.admin.policy"><code>mc admin policy</code></a> 命令用于管理可与 <a href="/zh/administration/identity-access-management/policy-based-access-control/#minio-policy">MinIO 基于策略的访问控制</a> (PBAC) 配合使用的策略。
MinIO PBAC 使用与 IAM 兼容的策略 JSON 文档来定义访问 MinIO 服务器资源的规则。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-prometheus/#command-mc.admin.prometheus"><code>mc admin prometheus</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-prometheus/#command-mc.admin.prometheus"><code>mc admin prometheus</code></a> 命令及其子命令用于访问 MinIO Prometheus 指标。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance"><code>mc admin rebalance</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance"><code>mc admin rebalance</code></a> 命令可用于在 MinIO 部署上启动、监控或停止再平衡操作。
再平衡会在部署中的所有池之间重新分配对象。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate"><code>mc admin replicate</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-replicate/#command-mc.admin.replicate"><code>mc admin replicate</code></a> 命令用于为一组 MinIO 对等站点创建并管理 <a href="/zh/operations/replication/multi-site-replication/#minio-site-replication-overview">站点复制</a>。</p><p>站点复制类似于 active-active 存储桶复制，但适用于多个 MinIO 部署。
在这组站点中，无论 IAM 设置、存储桶或对象发生何种变更，该变更都会在站点复制组中的所有站点间复制。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-scanner/#command-mc.admin.scanner"><code>mc admin scanner</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-scanner/#command-mc.admin.scanner"><code>mc admin scanner</code></a> 命令提供有关 <a href="/zh/operations/concepts/scanner/#minio-concepts-scanner">scanner</a> 进程的信息。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-service/#command-mc.admin.service"><code>mc admin service</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-service/#command-mc.admin.service"><code>mc admin service</code></a> 命令可用于重启或解除冻结 MinIO 服务器。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-trace/#command-mc.admin.trace"><code>mc admin trace</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-trace/#command-mc.admin.trace"><code>mc admin trace</code></a> 命令显示目标 MinIO 部署上发生的 API 操作。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update"><code>mc admin update</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-update/#command-mc.admin.update"><code>mc admin update</code></a> 命令会更新部署中的所有 MinIO 服务器。
该命令还支持使用私有镜像服务器，适用于部署环境无法访问公网的场景。</p></td>
    </tr>
    <tr>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user"><code>mc admin user</code></a></p></td>
      <td><p><a href="/zh/reference/minio-mc-admin/mc-admin-user/#command-mc.admin.user"><code>mc admin user</code></a> 命令及其子命令用于管理 <a href="/zh/administration/identity-access-management/minio-identity-management/#minio-internal-idp">MinIO 用户</a>。</p></td>
    </tr>
  </tbody>
</table>

<a id="id3"></a>

## 安装 {#mc-admin-install}

{{< tabpane text=true persist=header >}}
{{% tab header="Linux" %}}
以下命令会向系统 PATH *临时* 追加一项，以便运行 `mc` 工具。 若要永久修改系统 PATH，请遵循你的操作系统说明。

或者，你也可以进入 `mc` 所在目录并运行 `./mc --help`。

**64 位 Intel**

```shell
curl https://dl.min.io/client/mc/release/linux-amd64/mc \
  --create-dirs \
  -o $HOME/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**64 位 PPC**

```shell
curl https://dl.min.io/client/mc/release/linux-ppc64le/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

**ARM64**

```shell
curl https://dl.min.io/client/mc/release/linux-arm64/mc \
  --create-dirs \
  -o ~/minio-binaries/mc

chmod +x $HOME/minio-binaries/mc
export PATH=$PATH:$HOME/minio-binaries/

mc --help
```

{{% alert color="info" %}}
**从 MinIO 下载页面安装**

MinIO 不会通过常见 Linux 软件仓库或包管理器 （Ubuntu、RHEL、Archlinux/AUR）正式发布其二进制文件。 MinIO 二进制文件唯一的官方来源是 [MinIO Download Page](https://dl.min.io/client/mc/release/)。

MinIO 不建议通过包管理器安装，因为上游仓库可能会安装错误的软件包， 或安装被重命名的软件包。

所有文档都假定你 *仅* 通过下载页面安装 *官方* `mc` 客户端二进制文件， 且二进制名称未做任何修改。
{{% /alert %}}
{{% /tab %}}
{{% tab header="macOS" %}}
```shell
brew install minio/stable/mc
mc --help
```
{{% /tab %}}
{{% tab header="Windows" %}}
在浏览器中打开以下文件：

[https://dl.min.io/client/mc/release/windows-amd64/mc.exe](https://dl.min.io/client/mc/release/windows-amd64/mc.exe)

双击该文件即可执行，*或者* 在命令提示符或 PowerShell 中运行以下命令：

```powershell
\path\to\mc.exe --help
```
{{% /tab %}}
{{% tab header="Source" %}}
从源码安装适用于开发者和高级用户，并要求具备可用的 Golang 环境。请参阅 [How to install Golang](https://golang.org/doc/install).

在终端环境中运行以下命令，从源码安装 `mc`：

```shell
go install github.com/minio/mc@latest
```

[`mc update`](/zh/reference/minio-mc/mc-update/#command-mc.update) 不支持源码安装方式。
{{% /tab %}}
{{< /tabpane >}}

## 快速开始 {#id4}

开始此流程前，请确保主机已 [安装](#mc-admin-install) [`mc`](/zh/reference/minio-mc/#command-mc)。

{{% alert color="warning" %}}
**重要**

以下示例会临时禁用 bash 历史记录，以降低认证凭据明文泄露的风险。 这是一项基础安全措施，无法缓解所有可能的攻击向量。请遵循你所用操作系统的 安全最佳实践，在命令行中输入敏感信息。
{{% /alert %}}

使用 [`mc alias set`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set) 命令将该部署添加到 **`mc`** 配置中。

```shell
bash +o history
mc config host add <ALIAS> <ENDPOINT> ACCESS_KEY SECRET_KEY
bash -o history
```

将各参数替换为所需值。仅指定 `mc config host add` 命令会启动输入提示， 用于录入所需值。

使用 [`mc admin info`](/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) 命令测试与新添加 MinIO 部署的连接：

```shell
mc admin info <ALIAS>
```

## 全局选项 {#id5}

[`mc admin`](#command-mc.admin) 支持与 [`mc`](/zh/reference/minio-mc/#command-mc) 相同的全局选项。 参见 [全局选项](/zh/reference/minio-mc/#minio-mc-global-options)。
