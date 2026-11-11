---
title: "对象的服务器端加密"
url: "/zh/administration/server-side-encryption/"
weight: 150
icon: fa-solid fa-key
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/server-side-encryption.rst
upstream_modified: true
---

<a id="minio-encryption-overview"></a>
<a id="minio-sse"></a>
<a id="id1" data-td-print-local></a>

MinIO 服务器端加密（SSE）在写入操作期间保护对象，使客户端能够利用服务器的处理能力在存储层保障对象安全（静态加密）。 SSE 还为与安全锁定和擦除相关的监管与合规要求提供关键能力。

MinIO SSE 使用 [PGSTY KES](https://github.com/pgsty/kes) 和外部密钥管理服务（KMS）来大规模执行安全的加密操作。 MinIO 也支持客户端管理的密钥管理模式，由应用程序全权负责创建和管理供 MinIO SSE 使用的加密密钥。

MinIO SSE 在功能和 API 上与 [AWS Server-Side Encryption](https://docs.aws.amazon.com/AmazonS3/latest/userguide/server-side-encryption.html) 兼容，并支持以下加密策略：

{{< tabs group="sse-kms-sse-s3-sse-c" >}}
{{< tab label="SSE-KMS 推荐" value="sse-kms" >}}
MinIO 支持使用存储在外部 <abbr title="密钥管理系统">KMS</abbr> 上的特定外部密钥（EK），为写入某个存储桶的所有对象启用自动 SSE-KMS 加密。 客户端可以在写入操作中指定显式密钥，以覆盖存储桶默认的 <abbr title="外部密钥">EK</abbr>。

对于未启用自动 SSE-KMS 加密的存储桶，客户端也可以在写入操作时指定一个 <abbr title="外部密钥">EK</abbr>。

SILO 可通过配置的 KMS 加密后端 IAM/配置数据。可用 `mcli encrypt clear` 清除桶默认加密，但已有加密数据仍需要原密钥。在这些数据仍依赖密钥服务时，不要移除它。

与 SSE-S3 和 SSE-C 相比，SSE-KMS 提供更细粒度且可定制的加密能力，因此更推荐使用这种方式，而不是其他受支持的加密方法。

如需在本地（非生产）MinIO 部署中启用 SSE-KMS 的教程，请参阅 [快速开始](/zh/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-quickstart)。 持久化部署请使用 [PGSTY KES 与 OpenBao](/zh/operations/server-side-encryption/configure-minio-kes/)。以下归档上游指南介绍其他继承后端，不代表这些服务已通过 SILO 集成验收：

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{< /tab >}}
{{< tab label="SSE-S3" value="sse-s3" >}}
MinIO 支持使用存储在外部 <abbr title="密钥管理系统">KMS</abbr> 上的一个 <abbr title="外部密钥">EK</abbr>，为写入某个存储桶的所有对象 启用自动 SSE-S3 加密。MinIO SSE-S3 在整个部署范围内仅支持 *一个* <abbr title="外部密钥">EK</abbr>。

对于未启用自动 SSE-S3 加密的存储桶，客户端也可以在写入操作中请求 SSE 加密。

SILO 可通过配置的 KMS 加密后端 IAM/配置数据。可用 `mcli encrypt clear` 清除桶默认加密，但已有加密数据仍需要原密钥。在这些数据仍依赖密钥服务时，不要移除它。

如需在本地（非生产）MinIO 部署中启用 SSE-s3 的教程，请参阅 [快速开始](/zh/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-quickstart)。持久化部署请使用 [PGSTY KES 与 OpenBao](/zh/operations/server-side-encryption/configure-minio-kes/)。以下归档上游指南介绍其他继承后端，不代表这些服务已通过 SILO 集成验收：

- [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)
- [Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md)
- [Entrust KeyControl](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/entrust-keycontrol.md)
- [Fortanix SDKMS](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/fortanix-sdkms.md)
- [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)
- [HashiCorp Vault Keystore](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/hashicorp-vault-keystore.md)
- [Thales CipherTrust Manager (formerly Gemalto KeySecure)](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/thales-ciphertrust.md)
{{< /tab >}}
{{< tab label="SSE-C" value="sse-c" >}}
客户端在对象写入操作中指定一个 <abbr title="外部密钥">EK</abbr>。 SILO 使用客户端提供的密钥执行 SSE-C，无需 KES 或服务端 KMS。

SSE-C 不支持存储桶默认加密设置，并要求客户端执行所有密钥管理操作。
{{< /tab >}}
{{< /tabs >}}

MinIO SSE 需要启用 [网络加密（TLS）](/zh/operations/network-encryption/#minio-tls)。

<a id="id3" data-td-print-local></a>

## 安全擦除与锁定 {#minio-encryption-sse-secure-erasure-locking}

KES 和 SILO 可以缓存密钥材料。封存密钥存储或撤销访问权限不保证立即清除缓存；测试撤销效果时需要考虑缓存过期和仍在运行的进程。

SSE-KMS 和 SSE-S3 对象依赖其元数据记录的外部密钥（EK）：

- 封存密钥存储或禁用 EK 访问，只会在可用的缓存密钥材料也不可用后阻止解密。应验证所有 SILO 与 KES 实例；仅封存后端不能证明读取已停止。
- 永久丢失 EK 的全部可用副本（包括缓存和备份），会使仍依赖它的对象无法恢复。

应保留原密钥，直到所有需要保留的对象版本均已迁移且验证能够解密。

如需了解更多信息，请参阅：

- [SSE-KMS 安全擦除与锁定](/zh/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms-erasure-locking)
- [SSE-S3 安全擦除与锁定](/zh/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3-erasure-locking)
- [SSE-C 安全擦除与锁定](/zh/administration/server-side-encryption/server-side-encryption-sse-c/#minio-encryption-sse-c-erasure-locking)

## 密码学构造 {#cryptographic-construction}

以下事实描述各 SSE 方案共享的构造。它们属于审计级参考材料：配置和使用 SSE 并不需要，但在审视"实际存储了什么、以什么形式存储"时有用。该描述源自从上游 MinIO 继承并由 Silo 保留的加密设计说明。

- 对象内容以认证加密方案（AEAD）加解密，组织为 *Secure Channel*：明文被切分为固定大小的分块，每个分块以唯一的 key-nonce 组合单独封装。最后一个分块可以更小，并被特殊处理以防止截断攻击。
- 对多部分对象，每个 part 使用由对象加密密钥（OEK）与 part 编号经 PRF 派生的独立密钥封装——OEK 本身从不直接作为 part 密钥使用。
- PRF 为 HMAC-SHA-256。固定版本的 `sio` 在硬件加速可用时优先选择 AES-256-GCM（包括符合条件的 x86 和 ARM64 CPU），否则优先选择 ChaCha20-Poly1305。
- 对象加密密钥为 256 位。内容加密格式使用 96 位 nonce，另有用于封装密钥的 256 位 IV；二者是不同字段，不能混淆。
- 分块大小为 65536 字节，因此密码学格式层面的单个对象或 part 明文上限为 `65536 * 2^32 = 256 TiB`；这不是 S3 API 支持的对象或 multipart part 大小上限。
- 对象密钥派生和密钥封装 IV 生成使用 `crypto/rand`，`sio` 默认也使用该密码学安全随机源。不要以仅保证唯一的计数器替换密钥或随机 nonce。
