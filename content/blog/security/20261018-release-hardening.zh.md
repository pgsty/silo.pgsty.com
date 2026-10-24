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

[SILO Server 20261018](/zh/blog/release/silo-20261018/) 正式交付了 **`SN-2026-015`**、**`SN-2026-016`** 与 **`SN-2026-017`** 三项安全修复、细粒度 STS 令牌撤销机制，以及跨 `silo`、`mcli` 与 `silo-console` 的 Go 工具链与依赖库安全更新。Server `20260916` 与 `20260903` 均受影响（`20261015` 为已被替代的预发布草稿）。

## Object Lock：SN-2026-015 与 SN-2026-016 {#object-lock}

[SN-2026-015 与 SN-2026-016 专题公告](/zh/blog/security/20260926-governance-retention-bypass/)及配套[修复设计方案](/zh/blog/design/governance-retention-bypass-repair/)详细记录了受影响的保留期修改与原地覆盖路径、复现步骤与缓解措施。[PR #234](https://github.com/pgsty/silo/pull/234)（`14042b5aa`）与 [PR #235](https://github.com/pgsty/silo/pull/235)（`0d3ba5d4c`）要求在读取对象前完成 `s3:PutObjectRetention` 入口鉴权，在削弱未到期 `GOVERNANCE` 锁时同时校验绕过请求头与 `s3:BypassGovernanceRetention` 权限，拒绝非复制请求传入 `?versionId=` 覆写版本，并在对象写锁内保护 `null` 版本原地覆写。

所有接收 S3 写入的集群节点与复制站点均须升级至 `20261018`。

## SN-2026-017：管理凭据授权边界 {#sn-2026-017}

`SN-2026-017` 涵盖 [PR #242](https://github.com/pgsty/silo/pull/242)（提交 [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)）及批量访问密钥列举后续提交 [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) 修复的管理端（Admin API）凭据授权边界缺陷。

| 权限边界 | `20261018` 修复前 | `20261018` 修复后行为 |
| --- | --- | --- |
| 自助查询与清理 | “目标归属调用者”可覆盖显式 Deny 或插件拒绝；查询自身服务账号甚至可能跳过鉴权 | 保留普通用户的自助管理能力（`DenyOnly`），但严格执行用户/组显式 `Deny`、受限会话策略与外部授权插件的拒绝决定 |
| 受限凭据二次委派 | 获准执行 create/update 的受限派生凭据可创建继承父账号更宽权限的子密钥，或移除目标服务账号的策略限制 | 在内置授权模式下，带有效内联会话策略限制的调用者不得创建或更新服务账号（含 LDAP 创建及仅修改元数据的请求） |
| root 派生凭据保护 | 拥有宽泛 `admin:*` 权限的非 root 管理员可操作 root 账号派生的服务账号 | 仅经过授权的 root 凭据或不受限的 root 派生身份可管理 root 归属的派生密钥（内部站点复制专用账号除外） |

传入 IAM 策略评估的操作主体始终为当前已认证的访问密钥（`cred.AccessKey`），父账号解析（`ParentUser`）仅用于归属关系比对。各 Handler 的完整契约与性能基准数据见 [IAM Admin API 授权边界修复](/zh/blog/design/iam-admin-authorization/)。

### 与安全修复同步落地的兼容性改进 {#compatibility}

- **新签发服务账号的语义空策略归一化**：创建服务账号时会过滤父凭据保留的策略/过期声明，并将语义为空的策略文档（`null`、`{}`、`{"Statement":null}`）归一化为“继承父账号权限”，同时保留带版本号或显式空语句列表（`{"Version":"2012-10-17","Statement":[]}`）的封禁语义，防止新签发的带过期时间密钥因携带空策略而无法使用。
- **损坏的非 root 服务账号清理**：授权通过后的删除与查询路径利用已持久化的身份元数据处理损坏、禁用或已过期的非 root 服务账号，同时防止损坏的令牌隐藏 root 父身份。
- **批量访问密钥列举（[`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8)）**：将统一的自助授权辅助函数扩展至批量访问密钥列表接口（`ListAccessKeysBulk`）；省略 `users`、传入调用者自身密钥或父账号均解析为同一父账号清单，同时严格保留显式 `Deny` 与跨用户校验。
- **错误码约定**：被拒绝的自助操作返回 `403 AccessDenied`；无权删除其他用户或 root 服务账号的请求保持返回 `404`。

### 运维操作建议 {#operations}

1. 使用生产环境中的真实普通用户、服务账号、STS 会话与外部插件身份验证管理操作。若自动化脚本此前依赖受限子凭据继续派生下级服务账号，或使用非 root 管理员管理 root 派生密钥，请改用具备相应权限的父身份或 root 身份。
2. 审查受影响版本期间创建的子服务账号与策略变更，撤销异常密钥；多站点 IAM 维护请遵循 [IAM 升级与恢复指南](/zh/operations/replication/iam-upgrade/)。

## STS 撤销的后续修复 {#sts-revocation}

最终发布提交 [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) 修复了 `RevokeTokens` 仅枚举本地内存缓存以及撤销状态未完整传播至同集群兄弟节点与远端站点的问题。服务端现为集群已持久掌握、匹配父身份/类型及操作时间截点的令牌保留删除墓碑，并通过节点通知与删除自愈机制同步传播。详情参见[细粒度 STS 撤销设计说明](/zh/blog/design/iam-revocations/#scoped-sts-20261018)与 [Server 20261018 发布说明](/zh/blog/release/silo-20261018/#delivery)。

## 依赖安全与登录兼容性 {#dependencies}

Server `20261018` 在 [`go.mod`](https://github.com/pgsty/silo/blob/0cd388c666f8211f552604ae73448a066e9c25ce/go.mod) 中采用 Go **1.27.2**、`golang.org/x/net` **v0.61.0**、`golang.org/x/crypto` **v0.58.0**、`golang.org/x/text` **v0.43.0**、`silo-pkg` **v3.14.3** 与 `go-jose` **v4.1.6**：

- **`go-jose` v4.1.6（[GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)）**：修复解析恶意构造的 RSA JWK 时消耗过多 CPU 的问题，并在 OIDC 路径上拒绝超过 **4096 位**的 RSA JWK 密钥。若外部身份提供者（IdP）使用了超过 4096 位的 RSA 签名密钥，请在升级前检查 OIDC 发现端点、JWKS 与登录流程并在 IdP 侧轮换密钥。
- **独立 Console**：独立部署版 Console 的依赖更新见 [Console v2.4.2 发布说明](/zh/blog/release/console-2.4.2/)。

## 验证与覆盖范围 {#evidence}

`cmd/` 下的回归测试覆盖了自助操作显式拒绝、受限会话委派拦截、root 凭据保护、空策略签发归一化、损坏密钥清理、解密后的批量列表身份内容以及 Object Lock WORM 不变量。源码与测试索引详见 [IAM 授权设计笔记](/zh/blog/design/iam-admin-authorization/)、[Object Lock 修复设计笔记](/zh/blog/design/governance-retention-bypass-repair/)及[组件版本矩阵](/zh/compatibility/versions/)。
