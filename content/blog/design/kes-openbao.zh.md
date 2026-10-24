---
title: "SILO、KES 与 OpenBao：密钥归属和恢复"
linkTitle: "KES 与 OpenBao"
date: 2026-10-18
lastmod: 2026-10-18
author: "SILO"
description: "区分对象加密、密钥服务授权与根密钥持久存储，并明确升级和恢复的验证方法。"
tags: [设计, KES, 安全, 运维]
weight: 1
draft: false
url: "/zh/blog/design/kes-openbao/"
---

SILO 通过 [PGSTY KES](https://github.com/pgsty/kes)（`MINIO_KMS_KES_ENDPOINT`）接入外部密钥管理系统。[PGSTY KES 20261018](/zh/blog/release/kes-20261018/)（源码 [`2f7e741db905`](https://github.com/pgsty/kes/commit/2f7e741db905d7ea755967b29666657d819d7ad0)）独立于 SILO 四组件构建图按需部署，在保持既有密钥存储格式与 OpenBao KV v2 兼容性的同时，将 KES 的 AWS Secrets Manager 后端迁移至 AWS SDK for Go v2。

## 三个服务的职责边界 {#architecture}

| 服务 | 负责内容 | 调用对象 |
| --- | --- | --- |
| SILO | 对象字节流与对象加密元数据；加解密对象内容 | 通过 HTTPS（mTLS）调用 KES 生成或解密数据加密密钥（DEK） |
| PGSTY KES | 应用身份认证、密钥访问策略与密钥 API；封装或解封装数据密钥 | 通过 OpenBao KV v2 保存或读取根主密钥 |
| OpenBao | KES 根主密钥的持久化记录、后端访问控制与自身恢复材料 | 所配置的持久化存储后端 |

```text
+-------------+       mTLS (KES API)       +-------------+    AppRole / TLS    +--------------------+
| SILO Server | -------------------------> |  PGSTY KES  | ------------------> | OpenBao (KV v1/v2) |
+-------------+  MINIO_KMS_KES_ENDPOINT    +-------------+   keystore.vault    +--------------------+
```

`MINIO_KMS_KES_ENDPOINT` 必须指向 **KES 服务端点**，因为 OpenBao 本身不实现 KES 密钥封装 API。KES 通过内置的 `keystore.vault` 配置访问 OpenBao（针对 OpenBao KV v2 挂载点需设置 `version: v2`）。同一个 `kes` 可执行文件同时提供服务端与管理 CLI，多个无状态 KES 实例可共享同一个外部 OpenBao 密钥存储。

SILO 将加密后的数据密钥（DEK）随对象元数据保存在存储桶中。对象存储桶本身不包含外部根密钥备份；一旦丢失 OpenBao 中的根密钥，即便磁盘上的所有对象纠删分片完好无损，已加密对象也将无法解密恢复。

对接 OpenBao KV v2 的最小 KES 配置示例：

```yaml
address: 0.0.0.0:7373

admin:
  identity: ${KES_ADMIN_IDENTITY}

tls:
  key:  /etc/kes/kes-server.key
  cert: /etc/kes/kes-server.crt
  ca:   /etc/kes/client-ca.crt

policy:
  silo-server:
    allow:
      - /v1/key/create/*
      - /v1/key/generate/*
      - /v1/key/decrypt/*
      - /v1/key/describe/*
      - /v1/key/list/*
      - /v1/status
      - /v1/version
    identities:
      - ${SILO_CLIENT_CERT_IDENTITY}

keystore:
  vault:
    endpoint: https://openbao.internal:8200
    engine:   secret
    version:  v2
    prefix:   kes
    approle:
      engine: approle
      id:     ${OPENBAO_ROLE_ID}
      secret: ${OPENBAO_SECRET_ID}
      retry:  15s
    tls:
      ca: /etc/kes/openbao-ca.crt
```

针对名为 `secret`、前缀为 `kes` 的 KV v2 挂载点，KES AppRole 所需的最小 OpenBao ACL 策略：

```hcl
path "secret/data/kes/*" {
  capabilities = ["create", "read", "delete"]
}

path "secret/metadata/kes/*" {
  capabilities = ["list", "read", "delete"]
}
```

## 身份认证与故障行为 {#failure}

部署时应分别配置 SILO → KES 与 KES → OpenBao 两段链路的 TLS 信任。KES 依据客户端证书的 SHA-256 摘要（`kes identity of <cert>`）授权 SILO 访问指定密钥名；OpenBao 则通过 AppRole 授权 KES 后端身份。

| 层级 / 配置项 | 故障表现 | 运维处置 |
| --- | --- | --- |
| OpenBao 处于封存（Sealed）或中断状态 | 内存热缓存可能允许部分操作短暂继续，但未命中缓存的密钥请求或重启后的新 SILO 进程会立即失败（Fail-Closed），绝不会降级为明文存储。 | 在启动或滚动重启依赖 KMS 的 SILO 节点前先解封 OpenBao；执行恢复验证时必须重启进程清空热缓存并实际回读对象。 |
| KV v1 与 KV v2 配置不匹配 | 对 KV v2 挂载点配置 `version: v1`（或 OpenBao ACL 策略未同时授权 `data/` 与 `metadata/` 路径）会在创建或列举密钥时返回 `403 permission denied` 或 `404`。 | 显式设置 `engine: <mount>`、`version: v2`，并在 OpenBao 策略中同时授权 `<mount>/data/<prefix>/*` 与 `<mount>/metadata/<prefix>/*`。 |
| 客户端证书轮换 | 轮换 `MINIO_KMS_KES_CERT_FILE` 会改变客户端证书的 SHA-256 Identity。若新 Identity 未提前加入 KES 策略，SILO 启动自检将失败。 | 轮换证书前先在 KES 策略中同时保留旧、新两个 Identity；待所有 SILO 节点切换至新证书后再移除旧 Identity。 |

请妥善保管持久化密钥库备份、KES 配置、TLS 信任根、身份与策略配置以及 OpenBao 解封恢复材料，并在演练中验证恢复后的密钥名称与密钥值完全一致。KES 开发模式（内存模式）仅将密钥保存在进程内存中，严禁用于持久化加密存储。

## SDK 迁移与兼容性 {#sdk}

[PGSTY KES 20261018](/zh/blog/release/kes-20261018/)（`2f7e741db905`）将 `keystore/aws/secretsmanager` 从已归档的 `github.com/aws/aws-sdk-go`（v1）迁移至模块化的 AWS SDK for Go v2（`github.com/aws/aws-sdk-go-v2`、`config`、`credentials`、`service/secretsmanager` 与 `github.com/aws/smithy-go`）。

迁移保持以下兼容性不变量：
- 完整保留既有密钥存储格式与 YAML 配置字段。
- KES YAML 中显式配置的凭据继续优先；留空时回退至 SDK 标准凭据链。
- KES 不会隐式加载 `~/.aws/config`，且配置文件中的 `endpoint` 始终优先于 SDK 端点环境变量覆盖。
- AWS Secrets Manager 的 `ResourceNotFoundException`、`ResourceExistsException` 与参数错误保持与原内部错误（`errKeyNotFound`、`errKeyExists`）相同的映射语义。

兼容性验收矩阵（[`testing/kms-compat.sh`](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh)）覆盖了 OpenBao KV v2 与 Moto Secrets Manager 的 `SDK-v1 -> SDK-v2 -> 回滚` 全流程切换，每次切换均重启 SILO 以清空内存密钥缓存并验证加密对象回读。

## 升级与恢复检查 {#verification}

1. 记录当前 SILO 与 KES 版本、主密钥名称、后端端点及客户端证书 Identity，并在确认恢复成功前保留既有密钥与后端备份。
2. 变更前读取一个既有加密对象并记录其预期摘要（Digest）；基于同一持久化后端将 KES 升级为 [PGSTY KES 20261018](/zh/blog/release/kes-20261018/#delivery) 二进制。
3. 重启 KES 与 SILO（清空热缓存），读取旧加密对象、写入新加密对象并校验两者摘要，验证生产环境实际使用的 TLS 身份与访问策略。
4. 在隔离演练环境中，基于同一密钥存储恢复旧版 KES 二进制，重启两项服务并重复验证加密对象回读。

分步配置与运维命令详见[配置 KES 与 OpenBao 服务端加密指南](/zh/operations/server-side-encryption/configure-minio-kes/)、[KES 参考配置](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/server-config.yaml)以及 [KES 兼容性测试脚本](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh)。
