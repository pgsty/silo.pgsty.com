---
title: "使用按存储桶划分密钥的服务端加密（SSE-KMS）"
url: "/zh/administration/server-side-encryption/server-side-encryption-sse-kms/"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption/server-side-encryption-sse-kms.rst
upstream_modified: true
---

<a id="sse-kms"></a>
<a id="minio-encryption-sse-kms"></a>

MinIO 服务端加密（SSE）在写入操作过程中保护对象，使客户端能够利用服务端的处理能力在存储层保护对象（静态加密）。 SSE 还为围绕安全锁定和擦除的监管与合规要求提供关键能力。

MinIO SSE 使用 [PGSTY KES](https://github.com/pgsty/kes) 和受支持的 [外部密钥管理服务（KMS）](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/_index.md#supported-kms-targets)，以安全地大规模执行加密操作。 MinIO 还支持由客户端管理密钥的模式，此时应用程序对为 MinIO SSE 创建和管理加密密钥承担全部责任。

MinIO SSE-KMS 使用由密钥管理系统（KMS）管理的外部密钥（EK）对对象进行加密或解密。 每个存储桶和对象都可以拥有单独的 <abbr title="外部密钥">EK</abbr>，从而在部署中支持更细粒度的加密操作。 只有在 MinIO 同时能够访问 KMS *以及* 用于加密该对象的 <abbr title="外部密钥">EK</abbr> 时，才能解密该对象。

你可以使用 [`mcli encrypt set`](/zh/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) 命令启用存储桶默认的 SSE-KMS 加密：

```shell
mcli encrypt set sse-kms EXTERNALKEY mysilo/mybucket
```

- 将 `EXTERNALKEY` 替换为用于加密该存储桶中对象的 <abbr title="外部密钥">EK</abbr> 名称。
- 将 `mysilo/mybucket` 替换为你要启用自动 SSE-KMS 加密的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) 和存储桶。

SILO 通过 KES 提供与 AWS S3 [SSE-KMS 接口](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingKMSEncryption.html) 对应的加密服务。正式维护的集成是 [SILO + PGSTY KES + OpenBao KV v2](/zh/operations/server-side-encryption/configure-minio-kes/)；以下归档上游指南介绍其他继承后端，需要分别验证：

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

<a id="id2" data-td-print-local></a>

## 快速开始 {#minio-encryption-sse-kms-quickstart}

使用由你管理的 PGSTY KES 部署。先完成 [SILO 与 KES 配置](/zh/operations/server-side-encryption/configure-minio-kes/)，包括持久化密钥存储、TLS 信任、SILO 应用策略，以及可用的 `mysilo` 客户端别名。不要用公开演示密钥保护需要保存的数据。

### 1) 为 SSE-KMS 创建加密密钥 {#id3}

KES 配置流程创建 `silo-default` 供后端数据和 SSE-S3 使用，创建 `silo-bucket` 供 SSE-KMS 示例使用。确认 `silo-bucket` 已存在，且 SILO 的 KES 身份有权使用它生成和解密数据密钥。管理员可用 `mcli admin kms key create mysilo KEYNAME` 创建其他已获策略授权的密钥。

### 2) 配置 SILO 的 SSE-KMS {#minio-sse-kms}

每台服务端使用相同的 KES 配置。以下对应 KES 配置流程中的示例：

```shell
MINIO_KMS_KES_ENDPOINT=https://kes.example.net:7373
MINIO_KMS_KES_API_KEY='REPLACE_WITH_SILO_API_KEY'
MINIO_KMS_KES_CAPATH=/etc/silo/certs/kes-ca.crt
MINIO_KMS_KES_KEY_NAME=silo-default
```

妥善保存 API key，并填写各主机上的实际 CA 路径。API key 与显式客户端私钥/证书配置互斥。对已有加密部署，必须保留原默认密钥及现存对象所需的全部密钥。

### 3) 应用服务端配置 {#id4}

修改环境配置后，通过管理该部署的服务管理器重启。若修改 systemd 的 `EnvironmentFile`，应重启 `silo.service`；单独执行管理 API 重启不会重新读取该文件，除非 SILO 另通过 `MINIO_CONFIG_ENV_FILE` 加载它。若已完成 KES 配置且配置没有变化，无需额外重启。

### 4) 配置存储桶默认加密 {#id5}

若示例桶尚不存在，先创建它，再设置默认加密：

```shell
mcli mb mysilo/encryptedbucket
mcli encrypt set sse-kms silo-bucket mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
```

该设置作用于**整个存储桶**，不支持按对象前缀设置。按 KES 配置流程，用 `mcli cp`、`mcli stat` 和读取新对象验证结果。改变默认设置不会重写已有对象。

可用 `mcli encrypt clear mysilo/encryptedbucket` 清除桶默认加密。这不会解密已有对象或后端数据，也不会解除它们对原密钥的依赖。全局自动加密设置或客户端显式加密请求仍可能使新写入加密。

<a id="id6" data-td-print-local></a>

## 安全擦除与锁定 {#minio-encryption-sse-kms-erasure-locking}

KES 和 SILO 可以缓存密钥材料。封存密钥存储或撤销访问权限不保证立即使缓存失效；验证撤销效果时应考虑缓存过期与仍在运行的进程。

SSE-KMS 使用在存储桶自动加密设置中指定的 <abbr title="外部密钥">EK</abbr>，或在写入操作中指定的 <abbr title="外部密钥">EK</abbr> 来保护对象。 因此，MinIO 在解密该对象时 *必须* 能够访问该 <abbr title="外部密钥">EK</abbr>。

- 禁用对 <abbr title="外部密钥">EK</abbr> 的访问，并且可用的缓存密钥材料也已失效时，依赖该密钥的对象将无法解密。恢复对原密钥的访问后可以重新解密。
- 永久丢失 <abbr title="外部密钥">EK</abbr> 的所有可用副本（包括缓存和备份），会使仍依赖该密钥的对象无法恢复。

单个 <abbr title="外部密钥">EK</abbr> 的作用范围取决于：

- 哪些存储桶将该 <abbr title="外部密钥">EK</abbr> 指定为自动 SSE-KMS 加密所用密钥， *以及*
- 哪些写入操作在请求 SSE-KMS 加密时指定了该 <abbr title="外部密钥">EK</abbr>。

例如，仅供一个桶使用的密钥丢失时，影响限于仍依赖它的对象；多个桶共用密钥时，恢复要求也会相互关联。桶默认设置可能变化，客户端也可以指定其他密钥，因此应检查实际对象版本，不能仅凭当前桶设置推断密钥使用情况。

<a id="id7" data-td-print-local></a>

## 加密过程 {#minio-encryption-sse-kms-encryption-process}

> [!NOTE]
> **说明**
>
> 本节介绍 MinIO 的内部逻辑和功能。 这些信息仅用于帮助理解，并不是配置或实现任何 MinIO 功能的前提条件。

SSE-KMS 使用由已配置密钥管理系统（KMS）管理的外部密钥（EK） 来执行加密操作并保护对象。下表描述了加密过程的各个阶段：

<table>
  <thead>
    <tr>
      <th><p>阶段</p></th>
      <th><p>说明</p></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><p>启用 SSE 的写入操作</p></td>
      <td><p>MinIO 接收到一个请求使用 SSE-KMS 加密的写入操作。
该写入操作 <em>必须</em> 关联一个用于加密对象的外部密钥（EK）。</p><ul><li><p>对于位于已启用自动 SSE-KMS 的存储桶中的写入操作，
MinIO 使用该存储桶的 EK。如果写入操作包含显式指定的 EK，
MinIO 会使用它来 <em>替代</em> 存储桶 EK。</p></li><li><p>对于位于 <em>未</em> 启用自动 SSE-KMS 的存储桶中的写入操作，
MinIO 使用该写入操作指定的 EK。</p></li></ul></td>
    </tr>
    <tr>
      <td><p>生成数据加密密钥（DEK）</p></td>
      <td><p>MinIO 使用 EK 生成数据加密密钥（DEK）。
具体来说，<a href="https://github.com/pgsty/kes">PGSTY Key Encryption Service (KES)</a> 会以 EK
作为“根”密钥，向 KMS 请求新的加密密钥。</p><p>KES 会返回 DEK 的明文形式 <em>以及</em> 其经过 EK 加密后的表示。
MinIO 将加密后的表示作为对象元数据的一部分进行存储。</p></td>
    </tr>
    <tr>
      <td><p>生成密钥加密密钥（KEK）</p></td>
      <td><p>MinIO 使用确定性算法生成唯一的 256 位密钥加密密钥（KEK）。
该密钥派生算法使用伪随机函数，并以明文 DEK、随机生成的初始化向量以及由
存储桶名称、对象名称等值构成的上下文作为输入。</p><p>MinIO 会在每次加密或解密操作时生成 KEK，并且 <em>绝不会</em> 将 KEK 存储到磁盘上。</p></td>
    </tr>
    <tr>
      <td><p>生成对象加密密钥（OEK）</p></td>
      <td><p>MinIO 会生成随机且唯一的 256 位对象加密密钥（OEK），并使用该密钥加密对象。
MinIO 不会将 OEK 的明文形式存储到磁盘上。
在加密或解密操作期间，OEK 的明文仅驻留在 RAM 中。</p></td>
    </tr>
    <tr>
      <td><p>加密对象</p></td>
      <td><p>MinIO 在将对象写入驱动器 <em>之前</em> 使用 OEK 对对象进行加密。
然后，MinIO 再使用 KEK 对 OEK 进行加密。</p><p>MinIO 将 OEK 和 DEK 的加密表示作为元数据的一部分存储。</p></td>
    </tr>
  </tbody>
</table>

对于读取操作，MinIO 会先获取 <abbr title="外部密钥">EK</abbr> 以解密 <abbr title="数据加密密钥">DEK</abbr>。 随后 MinIO 会重新生成 <abbr title="密钥加密密钥">KEK</abbr>、解密 <abbr title="对象加密密钥">OEK</abbr>，并解密该对象。
