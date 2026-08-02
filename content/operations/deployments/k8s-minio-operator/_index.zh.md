---
title: "MinIO Kubernetes Operator"
url: "/zh/operations/deployments/k8s-minio-operator/"
weight: 10
icon: fa-solid fa-dharmachakra
minio_origin: true
silo_modified: false
---

<a id="minio-kubernetes-operator"></a>
<a id="deploy-minio-operator"></a>

MinIO 是一个 Kubernetes 原生的高性能对象存储，提供兼容 S3 的 API。 MinIO Kubernetes Operator 支持将 MinIO Tenant 部署到私有云和公有云基础设施（“Hybrid” Cloud）上。

MinIO Operator 会安装一个 [Custom Resource Definition (CRD)](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions)，以支持将 MinIO Tenant 描述为 Kubernetes [object](https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/)。

MinIO Operator 运行在自己的命名空间中。 在该命名空间内，MinIO Operator 使用两个 pod：

- Operator pod：用于执行部署、管理、修改和维护 Tenant 的基础 Operator 功能。
- Console pod：用于承载 Operator 的图形界面，也就是 Operator Console。

有关 MinIO CRD 的完整文档，请参阅 MinIO Operator [CRD Reference](https://github.com/minio/operator/blob/master/docs/tenant_crd.adoc)。

<a id="minio-operator-prerequisites"></a>

## Operator 前提条件 {#operator}

### Kubernetes 版本 {#kubernetes}

MinIO 支持使用 [受维护的 Kubernetes API](https://kubernetes.io/releases/) 来部署 Operator。

如果 Kubernetes 基础设施运行的是生命周期已结束的 API 版本，在部署 Operator 时可能出现意料之外或不期望的行为。

### Kustomize 和 `kubectl` {#kustomize-kubectl}

[Kustomize](https://kubernetes.io/docs/tasks/manage-kubernetes-objects/kustomization) 是一个基于 YAML 的模板工具，可让你以声明式、可重复的方式定义 Kubernetes 资源。 Kustomize 已内置在 [kubectl](https://kubernetes.io/docs/reference/kubectl) 命令行工具中。

本步骤默认你的本地主机既安装了与 Kubernetes 集群版本匹配的 `kubectl`，也具备在该集群中创建新资源所需的访问权限。

[默认的 MinIO Operator Kustomize 模板](https://github.com/minio/operator/blob/master/kustomization.yaml) 为本地环境定制配置提供了一个起点。 你可以修改默认的 Kustomization 文件，或应用自己的 [patches](https://datatracker.ietf.org/doc/html/rfc6902)，以针对 Kubernetes 集群定制 Operator 部署。

<a id="minio-k8s-deploy-operator-tls"></a>

### Kubernetes TLS Certificate API {#kubernetes-tls-certificate-api}

MinIO Operator 使用 Kubernetes `certificates.k8s.io` [TLS certificate management API](https://kubernetes.io/docs/tasks/tls/managing-tls-in-a-cluster/) 管理 TLS Certificate Signing Requests (CSR)，并在以下场景中创建已签名的 TLS 证书：

- 当启用 `autoCert` 时。
- 当 [`MINIO_CONSOLE_TLS_ENABLE`](/zh/reference/operator-environment-variables/#envvar.MINIO_CONSOLE_TLS_ENABLE) 环境变量设置为 `on` 时，用于 MinIO Console。
- 当 [`OPERATOR_STS_ENABLED`](/zh/reference/operator-environment-variables/#envvar.OPERATOR_STS_ENABLED) 环境变量设置为 `on` 时，用于 [STS service](/zh/developers/security-token-service/#minio-security-token-service)。
- 用于获取集群健康状态。

MinIO Operator 会读取 `operator-ca-tls` secret 中的证书，并在 tenant 命名空间内同步该 secret，以信任私有证书颁发机构，例如使用 cert-manager 时的场景。

在上述任一场景下，MinIO Operator 都 *要求* Kubernetes `kube-controller-manager` 的配置中包含以下 [配置项](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/#options)：

- `--cluster-signing-key-file` - 指定用于签发集群级证书的 PEM 编码 RSA 或 ECDSA 私钥。
- `--cluster-signing-cert-file` - 指定用于签发集群级证书的 PEM 编码 x.509 Certificate Authority 证书。

Kubernetes TLS API 会使用 CA 的签名算法生成新的 TLS 证书。 与 RSA 相比，ECDSA（例如 [NIST P-256 curve](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf)）或 EdDSA（例如 <a id="index-0"></a>[**Curve25519**](https://datatracker.ietf.org/doc/html/rfc7748.html)）对计算资源的需求更低，因此 MinIO 推荐使用这类 TLS 私钥/证书。 有关受支持 TLS Cipher Suites 的完整列表，请参阅 [支持的 TLS Cipher Suite](/zh/operations/network-encryption/#minio-tls-supported-cipher-suites)。

如果 Kubernetes 集群未配置为对生成的 <abbr title="Certificate Signing Request">CSR</abbr> 作出响应，Operator 将无法完成初始化。 某些 Kubernetes 提供方默认不会指定这些配置值。

若要检查 `kube-controller-manager` 是否指定了集群签名密钥和证书文件，请使用以下命令：

```shell
kubectl get pod kube-controller-manager-$CLUSTERNAME-control-plane \
  -n kube-system -o yaml
```

- 将 `$CLUSTERNAME` 替换为 Kubernetes 集群名称。

确认输出中包含高亮标出的行。 上例命令的输出可能与你终端中的实际输出不同：

```shell
 spec:
 containers:
 - command:
     - kube-controller-manager
     - --allocate-node-cidrs=true
     - --authentication-kubeconfig=/etc/kubernetes/controller-manager.conf
     - --authorization-kubeconfig=/etc/kubernetes/controller-manager.conf
     - --bind-address=127.0.0.1
     - --client-ca-file=/etc/kubernetes/pki/ca.crt
     - --cluster-cidr=10.244.0.0/16
     - --cluster-name=my-cluster-name
     - --cluster-signing-cert-file=/etc/kubernetes/pki/ca.crt
     - --cluster-signing-key-file=/etc/kubernetes/pki/ca.key
 ...
```

{{% alert color="warning" %}}
**重要**

MinIO Operator 会使用指定的 Certificate Authority (CA) 为所有 MinIO Tenant pod 自动生成 TLS 证书。 Kubernetes 集群外部的客户端必须信任该 Kubernetes 集群 CA，才能连接到 MinIO Operator 或 MinIO Tenant。

若客户端无法信任 Kubernetes 集群 CA，可以对连接到 MinIO Operator 或 MinIO Tenant 的请求禁用 TLS 校验。

另一种方式是生成由已知且受信任 CA 签发的 x.509 TLS 证书，并将这些证书提供给 MinIO Tenant。 更完整的文档请参阅 [网络加密（TLS）](/zh/operations/network-encryption/#minio-tls)。
{{% /alert %}}
