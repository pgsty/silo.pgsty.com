---
title: "十月安全更新：Object Lock、管理凭据与 JWK 解析"
linkTitle: "20261018 安全更新"
date: 2026-10-18
lastmod: 2026-10-19
author: "SILO"
description: "SN-2026-015/016 交付边界、SN-2026-017 管理授权、依赖更新及 Server 20261018 的具体升级影响。"
tags: [安全, IAM, Object Lock, silo]
weight: 1
url: "/zh/blog/security/20261018-release-hardening/"
---

**发布边界：** [Server 20261018 正式版](/zh/blog/release/silo-20261018/)包含这些修复，截至 2026-10-18 其 GitHub Release 已正式发布。正式 Server 20260916 不包含这些修复；20261015 是已被替代的草稿，不是推荐升级目标。安装独立 Console v2.4.2 或 mcli 20261018 不会修复 Server 进程。

## Object Lock：SN-2026-015 与 SN-2026-016 {#object-lock}

[已有公告](/zh/blog/security/20260926-governance-retention-bypass/)记录了受影响的保留期写入与覆盖路径、复现和缓解措施。[#234](https://github.com/pgsty/silo/pull/234) 与 [#235](https://github.com/pgsty/silo/pull/235) 要求在查询对象前检查基本保留期权限，削弱未到期 GOVERNANCE 时同时检查绕过意图与权限，并在对象锁内保护指定版本或隐式原位写入。无法读取锁状态时拒绝操作。[设计文档](/zh/blog/design/governance-retention-bypass-repair/)解释了可信复制例外，以及为什么必须升级所有接受写入的站点。

Server 20260916 和已测试的 20260903 受影响。本版阻止已修复路径修改受保护状态，但不能恢复被覆盖版本或重建此前的保留日期。应独立检查审计记录中的保留期变化与异常 COMPLIANCE 锁。

## SN-2026-017：管理凭据授权边界 {#sn-2026-017}

`SN-2026-017` 是 SILO 本地编号，不是 CVE。它归纳 [#242](https://github.com/pgsty/silo/pull/242) 修复的相关 Admin handler 缺陷，源码为 [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)。Server 20260916 包含受影响行为。这些操作要求已经认证的凭据，并非匿名开放 Admin API。

| 边界 | 修复前 | 本版行为 |
| --- | --- | --- |
| 自助查询与清理 | 所有权可能覆盖策略或插件的拒绝；查询自己的服务账户可能跳过授权 | 保留既有自助权利，但落实用户／组显式 Deny、受限会话策略与插件拒绝 |
| 受限凭据委派 | 获准 create/update action 的派生调用者可能获得更宽的父权限，或移除目标服务账户的限制 | 内置授权拒绝带有效会话限制的调用者创建与更新服务账户，包括 LDAP 创建和仅修改元数据的请求 |
| root 派生凭据 | 拥有宽泛 Admin action 的非 root 管理员可能管理 root 的派生密钥 | 独立检查要求经过授权的 root 密钥或不受限的 root 派生身份；内部站点复制账户不被视为 root 管理员 |

策略评估中的 actor 仍是经过认证的密钥，而非它的父身份；父身份只用于比较所有权。内置授权下，普通用户即使解绑最后一条策略，也保留既有自查询与清理权利，不会仅因缺少 Allow 而遭到新的拒绝。派生凭据仍须接受会话策略检查，跨用户操作继续要求相应 action。

root 与委派限制适用于内置授权，包括使用本地策略评估的 LDAP/OIDC 身份。配置外部授权插件时，插件仍是授权依据，其拒绝不再被自身所有权覆盖。应检查插件规则，不要以为内置额外检查会取代它。

### 与安全修复一同保留的兼容行为 {#compatibility}

- 新服务账户签发会过滤父凭据保留的策略／到期 claim，并将语义为空的策略（`null`、`{}`、`{"Statement":null}`）规范为继承。带版本号或显式空 statement 列表的策略不会仅因没有语句而被改为继承，避免新到期密钥携带不可用的空策略。
- 授权后的清理使用存储中的身份元数据处理损坏的非 root 服务账户，包括禁用或已到期目标。损坏 token 不能隐藏 root 父身份；缺失的身份元数据不会被重建。
- [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) 将既有自助授权 helper 用于批量 Access Key 列表。省略 users、指定调用者自己的 key 或父身份，均查询同一父身份清单；显式 Deny 与跨用户限制保留。
- 被拒绝的自助操作返回 403；删除无权管理的其他用户／root 服务账户继续返回 404。此次修复不统一所有 Admin 错误。

路由、action 名称、请求／响应格式和 IAM 存储格式不变，无需全局策略引擎修改、迁移、后台任务或新设置。[设计记录](/zh/blog/design/iam-admin-authorization/)说明了局部检查与成本，历史凭据不会被重写。

### 运维操作 {#operations}

使用生产中实际的普通用户、服务账户、STS 和外部插件身份测试管理操作。依赖被拒绝自助访问、受限密钥委派或非 root 修改 root 凭据的自动化，应改用适当授权的身份，不要通过放宽所有策略恢复旧绕过。

检查受影响时期签发的子凭据与服务账户策略修改，撤销异常密钥。历史不可用的到期密钥，应在核对目标策略后由授权父身份重新签发。升级不会识别或撤销修复前创建的全部凭据。保留完整 IAM 备份与撤销历史，遵循 [IAM 恢复指南](/zh/operations/replication/iam-upgrade/)。降级到 20260916 会恢复有缺陷的 handler 行为。

## STS 撤销的后续修复 {#sts-revocation}

发行源码 `0cd388c66` 还修复了 `RevokeTokens` 只枚举本地缓存，以及撤销未完整传播到同集群节点和站点的问题。它为请求集群已持久保存、符合父身份／类型及操作截点的令牌保留删除记录，并通过既有通知与删除恢复传播。孤立站点尚未复制来的令牌不在快照中，网络分区下不保证瞬时全局撤销。保持所有参与服务器版本一致，保留完整 IAM 历史并逐端点验证旧令牌失效。参见[设计与成本](/zh/blog/design/iam-revocations/#scoped-sts-20261018)和[最终制品验收](/zh/blog/release/silo-20261018/#delivery)。


## 依赖安全与登录兼容性 {#dependencies}

Server 在[固定源码的模块文件](https://github.com/pgsty/silo/blob/0cd388c666f8211f552604ae73448a066e9c25ce/go.mod)中选择 Go **1.27.2**、`golang.org/x/net` **v0.61.0**、`x/crypto` **v0.58.0**、`x/text` **v0.43.0** 和 go-jose **v4.1.6**。依赖选择或扫描通过，不证明所有部署都不存在漏洞。

go-jose v4.1.6 修复解析恶意 RSA JWK 时可能过量消耗 CPU 的问题，见[上游公告 GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)。Server 的 OIDC 路径使用此库；其 RSA JWK 大小限制会拒绝超过 **4096 位**的密钥。升级前检查身份提供者 discovery、JWKS 与登录，并在提供者侧轮换不兼容密钥。仅凭此依赖公告不能认定 SILO 存在未经认证的 S3 利用路径。

独立 Console 的模块图通过 pkg 声明相关依赖，但 go-jose 与 go-ldap 不链接进该独立二进制，见 [Console 发布范围](/zh/blog/release/console-2.4.2/)。Server 使用的 pkg **v3.14.3** 在 v3.14.2 基础上优化策略性能，不改变授权语义。该优化和客户端升级均不能替代上文的 Server handler 修复。

## 证据与范围 {#evidence}

候选源码包含 handler 回归，覆盖自助操作显式拒绝、受限会话委派、root 目标、空策略签发、损坏密钥清理，以及解密后的批量列表身份内容。Object Lock 回归是 Server 发行构建前置检查。源码与测试出处见 [IAM 设计](/zh/blog/design/iam-admin-authorization/)和 [Object Lock 设计](/zh/blog/design/governance-retention-bypass-repair/)。

这些源码记录不证明公开制品可用或生产升级已完成，交付状态以[发布说明](/zh/blog/release/silo-20261018/#delivery)和[组件矩阵](/zh/compatibility/versions/)为准。STS 撤销在站点之间仍以异步方式收敛。Admin 授权修复不承诺并发修改操作的原子授权，独立的 #79 / #217 存储边界仍然存在。
