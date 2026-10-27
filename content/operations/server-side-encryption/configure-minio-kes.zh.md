---
title: "使用 KES 进行服务端对象加密"
url: "/zh/operations/server-side-encryption/configure-minio-kes/"
description: "为 Silo 部署服务端对象加密"
weight: 10
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/server-side-encryption/configure-minio-kes.rst
upstream_modified: true
---

<a id="kes"></a>
<a id="server-side-object-encryption-with-kes"></a>

使用 **PGSTY KES** 作为 SILO 的独立密钥加密服务。上游 MinIO KES 已弃用，但持续维护的 [`pgsty/kes`](https://github.com/pgsty/kes) 分支已正式发布 [20261026](/zh/blog/release/silo-20261026/#kes)。KES 是可选的独立服务，不内嵌于 SILO 二进制。

维护的集成路径为 **SILO → PGSTY KES → OpenBao KV v2**：SILO 加密对象数据，KES 验证 SILO 身份并生成或解密数据密钥，OpenBao 持久保存 KES 根密钥。OpenBao 使用 KES 的 `keystore.vault` 配置。验证范围与升级边界见[集成设计](/zh/blog/design/kes-openbao/)。

<span id="id2" data-td-print-local></span>
## 前提条件 {#prerequisites}

<span id="minio"></span>
### 访问 SILO 集群 {#access-to-minio-cluster}

- 从[下载与安装](/zh/download/)获取 `silo`、`mcli` 和 `kes`，核验发行版校验和。
- 为 SILO 配置管理员权限的 [mcli 别名](/zh/reference/minio-mc/mc-alias-set/)，下文使用 `mysilo`。
- 为 SILO、KES 和密钥存储提供 TLS 证书与受信任的 CA。SILO 必须能访问每个配置的 KES 端点，KES 必须能访问密钥存储。
- 修改既有部署前，备份数据、配置与加密密钥。

<a id="minio-sse-vault-prereq-vault"></a>
<a id="minio-sse-vault"></a>
<span id="kes-kms"></span>
### 准备持久密钥存储 {#ensure-kes-access-to-a-supported-kms-target}

准备 OpenBao KV v2 挂载点，并为 KES 密钥前缀配置 AppRole 访问权限；所需 data 与 metadata 路径见 [OpenBao ACL 示例](/zh/blog/design/kes-openbao/#architecture)。在启动 KES 前完成配置。以下是 `server-config.yaml` 的**配置片段**，假定挂载点名为 `kv`、前缀为 `kes`：

```yaml
keystore:
  vault:
    endpoint: https://openbao.example.net:8200
    engine: kv
    version: v2
    prefix: kes
    approle:
      id: "REPLACE_WITH_APPROLE_ID"
      secret: "REPLACE_WITH_APPROLE_SECRET"
```

完整配置（包括密钥存储的 TLS 信任）见 [PGSTY KES 配置参考](https://github.com/pgsty/kes/blob/RELEASE.2026-10-26T00-00-00Z/server-config.yaml)。保护配置文件，将真实凭据保存在源码管理之外。保持 OpenBao 解封，并演练其备份恢复流程。

<a id="minio-sse-aws"></a>
<a id="minio-sse-azure"></a>
<a id="minio-sse-gcp"></a>

配置参考仍保留其他继承的后端。历史指南包括 [AWS Secrets Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/aws-secrets-manager.md)、[Azure Key Vault](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/azure-keyvault.md) 和 [Google Cloud Secret Manager](https://github.com/minio/kes-docs/blob/67cc5e56909035aad851f2d031a295a8ad9efe57/content/integrations/google-cloud-secret-manager.md)。请分别验证所选后端与认证方式。

<span id="id3" data-td-print-local></span>
## 配置步骤 {#procedure}

### 1. 配置 KES 身份与 TLS

为 SILO 生成应用身份：

```shell
kes identity new
```

妥善保管生成的 **API key**。KES 策略中填写对应的 **identity hash**，不要填写 API key。使用单独的管理员身份管理 KES。

以下策略片段允许 SILO 使用以 `silo-` 开头的密钥：

```yaml
policy:
  silo:
    allow:
      - /v1/key/create/silo-*
      - /v1/key/generate/silo-*
      - /v1/key/decrypt/silo-*
    identities:
      - "REPLACE_WITH_SILO_IDENTITY_HASH"
```

将密钥存储、策略片段与配置参考中的 `address`、`admin.identity`、`tls.key` / `tls.cert` 合并。TLS 证书必须包含 SILO 访问 KES 时使用的主机名。API key 和显式客户端私钥／证书是两种互斥的 SILO 认证方式，不要同时配置。

启动已配置的服务：

```shell
kes server --config /etc/kes/server-config.yaml
```

容器部署需要将配置与证书挂载到 KES 进程可读的位置。PGSTY KES 镜像以 UID/GID `1000:1000` 运行。KES 软件包提供可执行文件，配置与服务管理需要单独准备。

### 2. 创建密钥

在信任 KES 服务证书的管理主机上设置 KES CLI 凭据，创建默认密钥与可选的桶密钥：

```shell
export MINIO_KES_SERVER=https://kes.example.net:7373
export MINIO_KES_API_KEY='REPLACE_WITH_KES_ADMIN_API_KEY'
kes key create silo-default
kes key create silo-bucket
```

既有部署必须保留原密钥名与原密钥材料。以旧名字创建新密钥不能恢复由原密钥加密的数据。

### 3. 配置 SILO

在**每个** SILO 服务进程的环境中设置以下变量。使用项目附带的 systemd unit 时，写入 `/etc/default/silo`：

```shell
MINIO_KMS_KES_ENDPOINT=https://kes.example.net:7373
MINIO_KMS_KES_API_KEY='REPLACE_WITH_SILO_API_KEY'
MINIO_KMS_KES_CAPATH=/etc/silo/certs/kes-ca.crt
MINIO_KMS_KES_KEY_NAME=silo-default
```

`MINIO_KMS_KES_CAPATH` 指向 SILO 主机上的 CA 文件或目录，不是 KES 容器内部路径。KES 证书由 SILO 已信任的 CA 签发时可以省略。多个 KES 端点以逗号分隔，并且必须提供相同的密钥与策略。

项目附带的 unit 为迁移兼容先读取 `/etc/default/minio`，再读取 `/etc/default/silo`。请以实际服务管理器的配置为准。SILO 本身仅在 `MINIO_CONFIG_ENV_FILE` 指定文件时加载环境文件，详见[环境文件参考](/zh/reference/minio-server/settings/core/#envvar.MINIO_CONFIG_ENV_FILE)。

不要同时设置 `MINIO_KMS_SERVER` 或静态密钥变量组。互斥的认证与后端配置见 [KES 设置](/zh/reference/minio-server/settings/kes/)。

### 4. 重启并检查部署

确认 KES 及其密钥存储可用，再通过每个节点的服务管理器应用环境变更。systemd 部署应在协调重启过程中重启 `silo.service`。`mcli admin service restart` 复用进程已有环境，不会让 systemd 重新读取修改后的 `EnvironmentFile`。

> [!WARNING]
> SILO 一旦加密后端 IAM／配置数据或对象，就必须保留密钥及可用的解密路径。移除 KES 设置或丢失密钥存储，可能使部署或对象不可读。清除桶的默认加密设置不会解密已有数据。

### 5. 启用桶加密并验证读取

使用已配置的 `mysilo` 别名与上述密钥：

```shell
mcli mb mysilo/encryptedbucket
mcli encrypt set sse-kms silo-bucket mysilo/encryptedbucket
mcli encrypt info mysilo/encryptedbucket
printf 'SILO encryption check\n' > encryption-check.txt
mcli cp encryption-check.txt mysilo/encryptedbucket/
mcli stat mysilo/encryptedbucket/encryption-check.txt
mcli cat mysilo/encryptedbucket/encryption-check.txt
```

若要使用部署的默认密钥，改用 `mcli encrypt set sse-s3 mysilo/encryptedbucket`。桶默认设置只影响后续写入，不会追溯加密既有对象。重启 SILO 与 KES 后再次验证解密，避免测试仅依赖缓存中的密钥。

## Kubernetes 部署

在 Kubernetes 环境中，建议将 PGSTY KES 作为独立服务部署管理，通过平台的 ConfigMap 与 Secret 将 KES 端点、凭据与 CA 证书注入 SILO Pod，并分别为 SILO 与 KES 固定镜像版本标签。

站点保留的 [MinIO Operator 指南](/zh/operations/deployments/kubernetes/)对应已归档的上游 `v7.1.1` 兼容快照（其中 Operator Console 已于 `v6.0.0` 移除，请勿参照旧版 Console 加密界面操作）。若沿用历史 `TenantSpec.kes` 示例，请根据 PGSTY KES 镜像的运行 UID/GID（`1000:1000`）与实际证书挂载路径核对配置。
