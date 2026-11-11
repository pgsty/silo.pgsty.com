---
title: "部署级服务端加密密钥（SSE-S3）"
url: "/zh/administration/server-side-encryption/server-side-encryption-sse-s3/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption/server-side-encryption-sse-s3.rst
upstream_modified: true
---

<a id="sse-s3"></a>
<a id="minio-encryption-sse-s3"></a>

MinIO 服务端加密（SSE）在写入操作期间保护对象，使客户端能够利用服务端的处理能力， 在存储层保护对象（静态加密）。SSE 还为围绕安全锁定和擦除的监管与合规要求提供关键能力。

MinIO SSE 使用 [PGSTY KES](https://github.com/pgsty/kes) 和外部 Key Management Service (KMS) 以安全方式大规模执行加密操作。MinIO 还支持 客户端自主管理密钥，即由应用全权负责创建和管理供 MinIO SSE 使用的加密密钥。

MinIO SSE-S3 使用由 Key Management System (KMS) 管理的 <abbr title="External Key">EK</abbr> 对对象进行加/解密。 你必须在启动 MinIO 服务器时通过 [`MINIO_KMS_KES_KEY_NAME`](/zh/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) 环境变量指定 该 <abbr title="External Key">EK</abbr>。对于 *所有* SSE-S3 加密操作，MinIO 都使用同一个 EK。

你可以使用 [`mcli encrypt set`](/zh/reference/minio-mc/mc-encrypt-set/#command-mc.encrypt.set) 命令启用存储桶默认 SSE-S3 加密：

```shell
mcli encrypt set sse-s3 mysilo/mybucket
```

- 将 `mysilo/mybucket` 替换为你要启用自动 SSE-S3 加密的 [`alias`](/zh/reference/minio-mc/mc-alias/#command-mc.alias) 和存储桶。

SILO 通过 KES 提供与 AWS S3 [SSE-S3 接口](https://docs.aws.amazon.com/AmazonS3/latest/userguide/UsingServerSideEncryption.html) 对应的加密服务。正式维护的集成是 [SILO + PGSTY KES + OpenBao KV v2](/zh/operations/server-side-encryption/configure-minio-kes/)；以下归档上游指南介绍其他继承后端，需要分别验证：

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure KeyVault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)

<a id="id2" data-td-print-local></a>

## 快速开始 {#minio-encryption-sse-s3-quickstart}

使用由你管理的 PGSTY KES 部署。先完成 [SILO 与 KES 配置](/zh/operations/server-side-encryption/configure-minio-kes/)，包括持久化密钥存储、TLS 信任、SILO 应用策略，以及可用的 `mysilo` 客户端别名。不要用公开演示密钥保护需要保存的数据。

### 1) 为 SSE-S3 创建加密密钥 {#id3}

KES 配置流程创建 `silo-default` 供后端数据和 SSE-S3 使用，创建 `silo-bucket` 供 SSE-KMS 示例使用。确认 `silo-default` 已存在，且 SILO 的 KES 身份有权使用它生成和解密数据密钥。管理员可用 `mcli admin kms key create mysilo KEYNAME` 创建其他已获策略授权的密钥。

### 2) 配置 SILO 的 SSE-S3 {#minio-sse-s3}

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
mcli encrypt set sse-s3 mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
```

该设置作用于**整个存储桶**，不支持按对象前缀设置。按 KES 配置流程，用 `mcli cp`、`mcli stat` 和读取新对象验证结果。改变默认设置不会重写已有对象。

可用 `mcli encrypt clear mysilo/encryptedbucket` 清除桶默认加密。这不会解密已有对象或后端数据，也不会解除它们对原密钥的依赖。全局自动加密设置或客户端显式加密请求仍可能使新写入加密。

<a id="id6" data-td-print-local></a>

## 安全擦除与锁定 {#minio-encryption-sse-s3-erasure-locking}

KES 和 SILO 可以缓存密钥材料。封存密钥存储或撤销访问权限不保证立即使缓存失效；验证撤销效果时应考虑缓存过期与仍在运行的进程。

SSE-S3 使用服务器启动时通过 [`MINIO_KMS_KES_KEY_NAME`](/zh/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME) 环境变量指定的 <abbr title="External Key">EK</abbr> 来保护对象。因此，MinIO *必须* 访问该 <abbr title="External Key">EK</abbr> 才能解密该对象。

- 禁用对 <abbr title="外部密钥">EK</abbr> 的访问，并且可用的缓存密钥材料也已失效时，依赖该密钥的对象将无法解密。恢复对原密钥的访问后可以重新解密。
- 永久丢失 <abbr title="外部密钥">EK</abbr> 的所有可用副本（包括缓存和备份），会使仍依赖该密钥的对象无法恢复。

该 <abbr title="External Key">EK</abbr> 的作用范围取决于：

- 哪些存储桶指定了自动 SSE-S3 加密，*以及*
- 哪些写入操作请求了 SSE-S3 加密。

<a id="id7" data-td-print-local></a>

## 加密过程 {#minio-encryption-sse-s3-encryption-process}

> [!NOTE]
> **说明**
>
> 以下部分描述 MinIO 的内部逻辑和功能。 这些信息仅用于帮助理解，并非配置或实现任何 MinIO 功能所必需。

SSE-S3 使用由已配置的 Key Management System (KMS) 管理的 <abbr title="External Key">EK</abbr> 来执行加密操作并 保护对象。下表描述了加密过程的各个阶段：

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
      <td><p>MinIO 接收到一个请求执行 SSE-S3 加密的写入操作。
MinIO 将 <a href="/zh/reference/minio-server/settings/kes/#envvar.MINIO_KMS_KES_KEY_NAME"><code>MINIO_KMS_KES_KEY_NAME</code></a> 中指定的密钥名称用作 EK。</p></td>
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
      <td><p>MinIO 在将对象写入磁盘 <em>之前</em> 使用 OEK 对对象进行加密。
随后，MinIO 使用 KEK 对 OEK 进行加密。</p><p>MinIO 将 OEK 和 DEK 的加密表示形式作为元数据的一部分进行存储。</p></td>
    </tr>
  </tbody>
</table>

## 密钥轮换 {#key-rotation}

SSE-S3 加密的对象可以在不重写对象数据的情况下换钥。服务器只假定 KMS 提供两个服务——`GenerateKey`（返回新 data key 的明文与主密钥加密形式）和 `DecryptKey`（解包已加密的 data key）——轮换即由它们构成：

1. 服务器使用对象自身元数据中存储的加密 data key 与主密钥 ID，解密该对象的 OEK。
2. 使用**当前** KMS 配置中的主密钥 ID 向 KMS 请求新的 data key。
3. 从新 data key 派生新的 KEK，用它重新加密 OEK，并把新的加密 OEK、加密 data key 与主密钥 ID 写入对象元数据。

对象内容本身不变：只是包裹 OEK 的密钥层级在当前配置的主密钥下重建。这就是把用旧主密钥加密的对象迁移到新主密钥之下的方式。所有需要保留的对象版本完成轮换并验证之前，旧密钥必须仍可用于解密；提前删除它会使第一步解封失败。

使用 [batch `keyrotate` 作业](/zh/administration/batch-framework-job-keyrotate/) 轮换存量对象密钥。启动作业需要相应的批处理管理权限，服务器需要 KMS 的旧 data key 解密与新 data key 生成权限。普通 S3 自 COPY 是另一条路径，可能重写对象数据。[`mc admin kms key`](/zh/reference/minio-mc-admin/mc-admin-kms-key/) 命令管理 KMS 密钥，本身不会轮换所有存量对象的密钥。
