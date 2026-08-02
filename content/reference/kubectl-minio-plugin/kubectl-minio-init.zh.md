---
title: "kubectl minio init"
url: "/zh/reference/kubectl-minio-plugin/kubectl-minio-init/"
weight: 9164
toc_hide: true
minio_origin: true
silo_modified: false
---

<a id="kubectl-minio-init"></a>
<a id="id1"></a>

<a id="command-kubectl.minio.init"></a>

## 说明 {#id3}

[`kubectl minio init`](#command-kubectl.minio.init) 命令用于初始化 MinIO Operator。

如果 Kubernetes 集群中已安装 MinIO Operator，此命令会将 Operator 升级到与 MinIO 插件版本一致。 有关升级 MinIO Operator 的更多信息，请参见 [升级 MinIO Operator](/zh/operations/deployments/k8s-upgrade-minio-operator-kubernetes/#minio-k8s-upgrade-minio-operator)。

## 语法 {#id4}

{{< tabpane text=true persist=header >}}
{{% tab header="示例" %}}
以下命令会初始化一个运行 7.1.1 的新 MinIO Operator 部署。

```shell
kubectl minio init
```
{{% /tab %}}
{{% tab header="语法" %}}
该命令的语法如下：

```shell
kubectl minio init                      \
              [--cluster-domain]        \
              [--console-image]         \
              [--console-tls]           \
              [--default-kes-image]     \
              [--default-minio-image]   \
              [--image]                 \
              [--image-pull-secret]     \
              [--namespace]             \
              [--namespace-to-watch]    \
              [--output]                \
              [--prometheus-name]       \
              [--prometheus-namespace]
```
{{% /tab %}}
{{< /tabpane >}}

## 参数 {#id5}

该命令支持以下参数：

#### `--cluster-domain` {#kubectl.minio.init.-cluster-domain}

*mc-cmd*

*Optional*

配置 operator 的 DNS 主机名时使用的域名。 默认为 `cluster.local`。

#### `--console-image` {#kubectl.minio.init.-console-image}

*mc-cmd*

*Optional*

在 Operator 模式下部署 [Operator Console](https://github.com/minio/operator) 时使用的镜像，管理员可以通过图形用户界面创建和管理 MinIO 租户。 默认为与对应 Operator 发布版本中变量 DefaultOperatorImage 绑定的 [版本](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go)。

#### `--console-tls` {#kubectl.minio.init.-console-tls}

*mc-cmd*

*Optional*

{{% alert color="info" %}}
**新增: 4.5.6**

{{% /alert %}}

为 Operator Console 启用 TLS。

默认禁用。

#### `--default-kes-image` {#kubectl.minio.init.-default-kes-image}

*mc-cmd*

*Optional*

创建新 MinIO 租户时使用的默认 [kes](https://github.com/minio/kes) 镜像。 默认为与对应 Operator 发布版本中变量 DefaultKESImage 绑定的 [版本](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go)。

#### `--default-minio-image` {#kubectl.minio.init.-default-minio-image}

*mc-cmd*

*Optional*

创建新 MinIO 租户时使用的默认 [minio](https://github.com/minio/minio) 镜像。 默认为与对应 Operator 发布版本中变量 DefaultTenantImage 绑定的 [版本](https://github.com/minio/operator/blob/master/kubectl-minio/cmd/helpers/constants.go)。

#### `--image` {#kubectl.minio.init.-image}

*mc-cmd*

*Optional*

用于部署 operator 的镜像。 默认为 [Operator 的最新发布版本](https://github.com/minio/operator/releases/latest)。

#### `--image-pull-secret` {#kubectl.minio.init.-image-pull-secret}

*mc-cmd*

*Optional*

用于拉取 [`--image`](#kubectl.minio.init.-image) 的 Secret 密钥。

由 MinIO 托管的 `minio/operator` 镜像*不*受密码保护。 仅当使用受密码保护的非 MinIO 镜像源时才需要此选项。

#### `--namespace` {#kubectl.minio.init.-namespace}

*mc-cmd*

*Optional*

部署 operator 的命名空间。 默认为 `minio-operator`。

#### `--namespace-to-watch` {#kubectl.minio.init.-namespace-to-watch}

*mc-cmd*

*Optional*

operator 监听 MinIO 租户的命名空间。 默认为 `""`，表示*所有命名空间*。

#### `--output` {#kubectl.minio.init.-output}

*mc-cmd*

*Optional*

执行 dry run，并将生成的 YAML 输出到 `STDOUT`。 使用此选项可自定义 YAML，然后通过 `kubectl apply -f <FILE>` 手动应用。

#### `--prometheus-name` {#kubectl.minio.init.-prometheus-name}

*mc-cmd*

*Optional*

由 Prometheus Operator 管理的 Prometheus 服务名称。 默认为 `PROMETHEUS_NAME`

#### `--prometheus-namespace` {#kubectl.minio.init.-prometheus-namespace}

*mc-cmd*

*Optional*

部署 Prometheus 的命名空间。 默认为 `PROMETHEUS_NAMESPACE`

#### `--sts` {#kubectl.minio.init.-sts}

*mc-cmd*

*Optional*

启用 Operator sts (v1alpha1)

{{% alert color="info" %}}
**新增: 5.0.0**

{{% /alert %}}
