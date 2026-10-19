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

**已发布实现：**[PGSTY KES 20261018](/zh/blog/release/kes-20261018/)，源码 [`2f7e741db905`](https://github.com/pgsty/kes/commit/2f7e741db905d7ea755967b29666657d819d7ad0)。KES 按需部署，独立于 SILO 四组件构建图。现有 SILO/KES 用户可以采用该版本，无需重写对象或迁移密钥。

## 三个服务的职责 {#architecture}

| 服务 | 负责内容 | 调用对象 |
| --- | --- | --- |
| SILO | 对象字节与加密元数据；加解密对象内容 | 通过 HTTPS 调用 KES，生成或解密数据密钥 |
| PGSTY KES | 应用身份、密钥访问策略与密钥 API；封装或解封装数据密钥 | 通过 OpenBao KV v2 保存或读取根密钥 |
| OpenBao | KES 根密钥的持久记录、后端访问控制与自身恢复材料 | 配置的存储后端 |

`MINIO_KMS_KES_ENDPOINT` 必须指向 **KES 端点**，OpenBao 不实现该 API。KES 通过既有 `keystore.vault` 配置访问 OpenBao；OpenBao 不能替代 KES 进程。同一个 `kes` 可执行程序同时提供服务和管理 CLI。多个 KES 实例可以使用同一个外部密钥存储，但须配置适当的身份和策略。

SILO 将加密后的数据密钥随对象元数据保存。对象桶不是外部根密钥的备份。即便所有对象分片完好，丢失所需根密钥仍可能使加密对象无法恢复。

## 身份认证与故障行为 {#failure}

分别配置 SILO → KES 和 KES → OpenBao 两段链路的 TLS 信任。KES 授权 SILO 身份访问所需密钥名，OpenBao 授权 KES 的后端身份。OpenBao 后端凭据属于 KES 配置，不属于 S3 客户端。

后端中断时，缓存可能让部分操作暂时继续成功。缓存未清空时读成功，不证明密钥存储可用，也不证明新进程能够解密。操作需要的密钥不可用时，加解密会失败，不会降级为明文存储。恢复验证应使用新进程并实际读取对象。

妥善保管持久密钥存储备份、KES 配置、TLS 信任、身份与策略配置，以及 OpenBao 恢复材料，并施加适当访问控制。恢复测试须确认密钥值和名称均保持一致。开发模式只在内存中保存密钥，不适合需要持久保存的加密数据。

## SDK 迁移与兼容性 {#sdk}

十月 KES 版本将 Secrets Manager 迁至 AWS SDK for Go v2，保留密钥存储格式和 YAML 字段。显式凭据继续优先；留空时使用 SDK 凭据提供链。KES 不会开始加载 `~/.aws/config`，配置端点仍优先于 SDK 端点环境变量覆盖。现有配置无需新增 AWS 端点设置。

验收矩阵覆盖 OpenBao KV v2 与 Moto Secrets Manager，包括 SDK v1 → SDK v2 → 回滚。每次切换均重启 SILO，清除密钥缓存。Moto 证明本地协议与存储兼容，不代表真实 AWS IAM、端点策略或服务行为通过认证。其他继承的 KES 后端不在该矩阵内。

## 升级与恢复检查 {#verification}

1. 记录 SILO 和 KES 版本、密钥名、后端端点及备份身份。在证明恢复可用前，保留原密钥和备份。
2. 变更前读取一个既有加密对象并记录预期摘要。使用同一持久后端，将 KES 替换为固定版本的 PGSTY 程序。
3. 重启 KES 和 SILO，读取旧对象、写入新加密对象并核验两者摘要。使用部署实际配置的 TLS 身份与访问策略。
4. 在隔离演练中恢复旧 KES 二进制，继续使用兼容的同一密钥存储，重启两个服务后重复读取。二进制回滚不能恢复已删除的密钥，也不能替代密钥存储恢复流程。

KES 发布矩阵测试了 SILO 20260903 与 20260916。最终 Server 20261018 的本机加密测试使用测试 KMS key，与这套外部 KES 矩阵分开；部署前仍应验证所选的完整版本组合。依据：[KES 兼容性测试](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/testing/kms-compat.sh)、[配置](https://github.com/pgsty/kes/blob/2f7e741db905d7ea755967b29666657d819d7ad0/server-config.yaml)、[发布验收范围](/zh/blog/release/kes-20261018/#delivery)。
