---
title: "网络加密（TLS）"
url: "/zh/operations/network-encryption/"
weight: 70
icon: fa-solid fa-shield-halved
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/network-encryption.rst
upstream_modified: true
---

<a id="tls"></a>
<a id="minio-tls-user-generated"></a>
<a id="minio-tls-third-party-ca"></a>
<a id="minio-tls" data-td-print-local></a>

> [!NOTE]
> **SSL 已弃用**
>
> TLS 是 Secure Socket Layer（SSL）加密的后继方案。 自 2018 年 6 月 30 日起，SSL 已被完全 [弃用](https://tools.ietf.org/html/rfc7568)。

## 概览 {#id2}

MinIO 支持使用 Transport Layer Security (TLS) 1.2+ 对入站和出站流量进行加密。 MinIO 可以自动检测默认或自定义搜索路径中的证书，并为所有连接启用 TLS。 MinIO 支持客户端发起的 Server Name Indication (SNI) 请求，此时 MinIO 会尝试为客户端指定的主机名定位合适的 TLS 证书。

MinIO *至少* 需要一张默认 TLS 证书，并且可以通过多张 TLS 证书支持 SNI 连接。 MinIO 使用 TLS Subject Alternative Name (SAN) 列表来判断应向客户端返回哪张证书。 如果 MinIO 找不到 SAN 覆盖客户端请求主机名的 TLS 证书，则会使用默认证书并尝试完成握手。

你可以指定一张 TLS 证书，覆盖 MinIO 部署可接受连接的所有 SAN。

这种配置所需设置最少，但会向连接客户端暴露 TLS SAN 中配置的全部主机名。 根据你的 TLS 配置，这些主机名可能包含内部或私有 SAN 域名。

你也可以按域名拆分配置多张 TLS 证书，并为所有未匹配主机名请求保留一张默认证书。 这种配置需要更多设置，但只会暴露返回证书的 TLS SAN 数组中所配置的主机名。

<a id="minio-tls-kubernetes"></a>

## Kubernetes 上的 MinIO TLS {#kubernetes-minio-tls}

MinIO Kubernetes Operator 为 MinIO 租户提供三种 TLS 配置方式：

**使用 Cluster Signing API 自动启用 TLS**

> 对于具备有效 [TLS Cluster Signing Certificate](/zh/operations/deployments/k8s-minio-operator/#minio-k8s-deploy-operator-tls) 的 Kubernetes 集群，MinIO Kubernetes Operator 可以在 [部署](/zh/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant-security) 或 [修改](/zh/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant-security) MinIO 租户时自动生成 TLS 证书。
>
> Kubernetes TLS API 在生成新的 TLS 证书时，会使用 Kubernetes 集群 Certificate Authority (CA) 的签名算法。 MinIO 支持的 TLS Cipher Suite 和推荐签名算法完整列表，请参见 [支持的 TLS Cipher Suite](#minio-tls-supported-cipher-suites)。
>
> 使用 `/var/run/secrets/kubernetes.io/serviceaccount/ca.crt` 中的 CA bundle 连接租户前，先确认它确实包含租户 TLS 证书的签发 CA；不要假定两者始终相同。如果签发 CA 不同，应向客户端单独提供正确的 CA 证书，并确保证书覆盖客户端使用的 [Service DNS 名称](https://kubernetes.io/docs/concepts/services-networking/dns-pod-service/)。
>
> > [!NOTE]
> > **Subject Alternative Name 证书**
> >
> > 如果你使用的是自定义 Subject Alternative Name (SAN) 证书，并且它 *不是* 通配符证书，那么 TLS 证书的 SAN **必须** 覆盖其父节点主机名。 在没有通配符的情况下，SAN 必须精确匹配，才能成功连接到该租户。

**cert-manager 证书管理**

> MinIO Operator 支持使用 [cert-manager](https://cert-manager.io/) 作为其内置自动证书管理或用户手动证书管理的完整替代方案。 关于如何使用 cert-manager 部署 MinIO Operator 和租户，请参见 [cert-manager 页面](/zh/operations/network-encryption/cert-manager/#minio-certmanager)。

**手动证书管理**

> Tenant CRD 字段 `spec.externalCertsSecret` 引用 TLS 证书 [Secret](https://kubernetes.io/docs/concepts/configuration/secret/#secret-types)。请按所用 Operator 版本的要求选择 Secret 类型和证书、私钥文件名。
>
> 你可以指定多张证书，以支持分配了多个主机名的租户。

<a id="self-signed-internal-private-certificates-and-public-cas-with-intermediate-certificates"></a>

### 自签名、内部、私有证书以及带中间证书的公共 CA {#ca}

如果你为 MinIO 租户部署的是由非全球或非公共 Certificate Authority 签发的证书，*或者* 使用了需要中间证书的公共 CA，则必须将这些 CA 提供给 Operator，以确保它能够信任这些证书。

对于使用不受信任证书部署的租户，Operator 可能会记录与 TLS 证书校验相关的警告。

以下过程会将一个包含 Certificate Authority `public.crt` 的 secret 挂载到 MinIO Operator。 你可以在同一证书文件中放入多个 CA，只要保持 `BEGIN` 和 `END` 分隔符原样不变即可。

1. 创建 `operator-ca-tls` secret

   以下命令会在 MinIO Operator 命名空间（`minio-operator`）中创建一个 Kubernetes secret。

   ```shell
   kubectl create secret generic operator-ca-tls \
      --from-file=public.crt -n minio-operator
   ```

   `public.crt` 文件必须是包含一个或多个 CA 定义的有效 TLS 证书。
2. 重启 Operator

   创建完成后，你必须重启 Operator 以加载新的 CA：

   ```shell
   kubectl rollout restart deployments.apps/minio-operator -n minio-operator
   ```

### 第三方 Certificate Authority {#certificate-authority}

MinIO Kubernetes Operator 可以在 [部署](/zh/operations/deployments/k8s-deploy-minio-tenant-on-kubernetes/#minio-k8s-deploy-minio-tenant-security) 或 [修改](/zh/operations/deployments/k8s-modify-minio-tenant-on-kubernetes/#minio-k8s-modify-minio-tenant-security) MinIO 租户时自动挂载第三方 Certificate Authority。

你可以随时为租户添加、更新或删除 CA。 要让配置中的 CA 变更生效，必须重启 MinIO 租户。

Operator 会将指定的 CA 放置到每个 MinIO Server pod 上，从而确保所有 pod 拥有一致的受信任 CA 集合。

如果 MinIO Server 无法将传入客户端的 TLS 证书签发者与任一可用 CA 匹配，则会将该连接视为无效并拒绝。

<a id="id3" data-td-print-local></a>

## 裸金属上的 MinIO TLS {#minio-tls-baremetal}

MinIO Server 会为每个节点搜索 TLS 私钥和证书，并使用这些凭据启用 TLS。 MinIO 会在发现并验证证书后自动启用 TLS。 搜索位置取决于你的 MinIO 配置：

{{< tabs group="tab1-tab2" >}}
{{< tab label="默认路径" value="tab1" >}}
默认情况下，MinIO server 会在以下目录中查找每个节点的 TLS 私钥和证书：

```shell
${HOME}/.silo/certs
```

其中 `${HOME}` 是运行 SILO 服务端进程的用户主目录。新安装使用 `.silo/certs`；只有旧 `.minio` 目录存在时才沿用 `.minio/certs`，两者都存在时优先使用 `.silo` 并输出警告。服务账户建议显式设置 `--certs-dir`。详见[证书目录规则](/zh/reference/minio-server/#minio.server.-certs-dir)。

对于由 `systemd` 管理的部署，该路径必须对应运行 MinIO 进程的 `USER`。 如果该用户没有主目录，请改用 **自定义路径** 选项。
{{< /tab >}}
{{< tab label="自定义路径" value="tab2" >}}
你可以通过 [`silo server --certs-dir`](/zh/reference/minio-server/#minio.server.-certs-dir) 或 `-S` 参数指定 MinIO server 搜索证书的路径。

例如，以下命令片段指示 MinIO 进程使用 `/opt/minio/certs` 目录存放 TLS 证书。

```shell
silo server --certs-dir /opt/minio/certs ...
```

运行 MinIO service 的用户 *必须* 对该目录拥有读写权限。
{{< /tab >}}
{{< /tabs >}}

请将默认域名（例如 `minio.example.net`）对应的 TLS 证书放入 `/certs` 目录，其中私钥命名为 `private.key`，公钥证书命名为 `public.crt`。

对于分布式 MinIO 部署，部署中的每个节点都必须具有一致的 TLS 证书配置。

### 自签名、内部、私有证书以及带中间证书的公共 CA {#id4}

如果你使用的是由非全球或非公共 Certificate Authority 签发的证书，*或者* 使用了需要中间证书的公共 CA，则必须将这些 CA 提供给 MinIO Server。 如果 MinIO server 不具备这些必要 CA，在连接其他服务时可能会返回与 TLS 校验相关的警告或错误。

请将 CA 证书放入 `/certs/CAs` 目录。 该目录的根路径取决于你使用的是默认证书路径，还是自定义证书路径（[`silo server --certs-dir`](/zh/reference/minio-server/#minio.server.-certs-dir) 或 `-S`）。

{{< tabs group="tab1-tab2" >}}
{{< tab label="默认证书路径" value="tab1" >}}
```shell
mv myCA.crt ${HOME}/.silo/certs/CAs
```
{{< /tab >}}
{{< tab label="自定义证书路径" value="tab2" >}}
以下示例假设 MinIO Server 以 `--certs-dir /opt/minio/certs` 启动：

```shell
mv myCA.crt /opt/minio/certs/CAs/
```
{{< /tab >}}
{{< /tabs >}}

信任自签名证书时，应安装对应的 **X.509 公共证书**；内部 CA 则安装其 CA 公共证书。不要将签名私钥放入 `CAs` 目录或分发给客户端。

对于由内部、私有或其他非全球 Certificate Authority 签发的证书，请使用签发该证书的同一 CA。 非全球 CA 必须包含从中间证书到根证书的完整信任链。

如果提供的文件不是 X.509 证书，MinIO 会忽略它，并可能在校验由该 CA 签发的证书时返回错误。

### 第三方 Certificate Authority {#id5}

SILO 使用主机系统的受信任根证书和 `CAs` 目录中的证书，校验其连接的对等节点及外部服务的 TLS 服务端证书。添加 CA 证书本身不会启用 S3 客户端证书认证。

请将 CA 证书放入 `/certs/CAs` 目录。 该目录的根路径取决于你使用的是默认证书路径，还是自定义证书路径（[`silo server --certs-dir`](/zh/reference/minio-server/#minio.server.-certs-dir) 或 `-S`）。

{{< tabs group="tab1-tab2" >}}
{{< tab label="默认证书路径" value="tab1" >}}
```shell
mv myCA.crt ${HOME}/.silo/certs/CAs
```
{{< /tab >}}
{{< tab label="自定义证书路径" value="tab2" >}}
以下示例假设 MinIO Server 以 `--certs-dir /opt/minio/certs` 启动：

```shell
mv myCA.crt /opt/minio/certs/CAs/
```
{{< /tab >}}
{{< /tabs >}}

请将每个 CA 的证书文件放入 `/CAs` 子目录。 确保 MinIO 部署中的所有主机在该目录下拥有一致的受信任 CA 集合。 如果 MinIO Server 无法将传入客户端的 TLS 证书签发者与任一可用 CA 匹配，则会将该连接视为无效并拒绝。

<a id="minio-tls-supported-cipher-suites"></a>

### 支持的 TLS Cipher Suite {#tls-cipher-suite}

与 RSA 相比，MinIO 更推荐生成 ECDSA（例如 [NIST P-256 曲线](https://nvlpubs.nist.gov/nistpubs/FIPS/NIST.FIPS.186-4.pdf)）或 EdDSA（例如 <a id="index-0" data-td-print-local></a>[**Curve25519**](https://datatracker.ietf.org/doc/html/rfc7748.html)）TLS 私钥/证书，因为它们的计算开销更低。

MinIO 支持以下由 [Go](https://cs.opensource.google/go/go/+/refs/tags/go1.17.1:src/crypto/tls/cipher_suites.go;l=52) 支持的 TLS 1.2 和 TLS 1.3 cipher suite。列表中使用 <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg> 标记推荐算法：

{{< tabs group="tls-13-tls-12" >}}
{{< tab label="TLS 1.3" value="tls-13" >}}
- `TLS_CHACHA20_POLY1305_SHA256` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_AES_128_GCM_SHA256`
- `TLS_AES_256_GCM_SHA384`
{{< /tab >}}
{{< tab label="TLS 1.2" value="tls-12" >}}
- `TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384` <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-star-fill" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z"></path></svg>
- `TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305`
- `TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256`
- `TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384`
{{< /tab >}}
{{< /tabs >}}
