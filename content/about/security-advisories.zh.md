---
title: "安全公告台账"
linkTitle: "安全公告"
description: "PGSTY SILO 安全公告台账：CVE 与 SN-2026 编号、修复提交、受影响子系统、暴露条件、升级指引与依赖安全更新。"
url: "/zh/about/security-advisories/"
weight: 41
type: docs
icon: fa-solid fa-shield-halved
---

本台账汇总 `pgsty/silo` 软件栈的全部安全修复与影响升级边界的安全变更。每条经过深度排查的公告均链接至[安全编年史](/zh/blog/security/)或[设计笔记](/zh/blog/design/)中的完整技术文章；本页作为编号、修复提交、暴露条件与升级边界的统一权威索引。

已有公开 CVE 编号的漏洞直接使用 CVE 标识。由于上游 `minio/minio` 已归档，不再为继承代码中的新发现分配 CVE，无 CVE 的安全问题统一分配稳定的 `SN-<年份>-<序号>` 编号（`SN-2026-002` 至 `SN-2026-019`），便于发布说明、提交记录与 Issue 稳定引用。`SN-2026-001` 为 `trackingResponseWriter` 流式刷新可靠性回归（非安全问题，见 [Server 20260804 发布说明](/zh/blog/release/silo-20260804/)）。

## 当前发布边界 {#boundary}

当前生产推荐基线为 **[Server 20261018](/zh/blog/release/silo-20261018/)**、**[Console v2.4.2](/zh/blog/release/console-2.4.2/)**、**[mcli 20261025](/zh/blog/release/mcli-20261025/)**；Server 选用 **[silo-pkg v3.14.3](/zh/blog/release/pkg-3.14.3/)**，mcli 选用 **[v3.15.1](/zh/blog/release/silo-20261025/)**（Go 1.27.3 及全栈依赖维护见 [20261025 公告](/zh/blog/release/silo-20261025/)）：

- **Server 20261018** 修复了 [SN-2026-015](#sn-2026-015)（`PutObjectRetention` 治理保留期授权绕过）、[SN-2026-016](#sn-2026-016)（指定版本与原地写入覆写对象锁）以及 [SN-2026-017](#sn-2026-017)（委派 IAM Admin 凭据授权边界），并新增按主体/按令牌范围吊销 STS 会话的能力（`0cd388c66`）。Server 20260916 及更早版本仍受 `SN-2026-015` 至 `SN-2026-017` 影响；请将修复部署至每一个接受写入的 Server 节点与复制站点。详见[十月安全公告](/zh/blog/security/20261018-release-hardening/)与[组件版本矩阵](/zh/compatibility/versions/)。
- **Server 20260916** 与 **Console v2.4.1** 包含 [SN-2026-011](#sn-2026-011) 至 [SN-2026-014](#sn-2026-014) 的修复（Server 20260903 不包含）。
- **Server 20260903** 包含 [SN-2026-006](#sn-2026-006) 至 [SN-2026-010](#sn-2026-010) 的修复。
- **Server 20260804** 与 **silo-pkg v3.11.0 / v3.12.0** 包含 [SN-2026-002](#sn-2026-002) 至 [SN-2026-005](#sn-2026-005)、[SN-2026-018](#sn-2026-018) 及 [SN-2026-019](#sn-2026-019) 的修复。

## 继承自上游的公告基线 {#inherited}

SILO 首个社区版本（`RELEASE.2025-12-03T12-00-00Z`）切自已包含 `CVE-2025-62506` 修复的上游源码历史。

| 编号 | 上游修复 | SILO 继承提交 | 摘要与发布说明 |
| :-- | :-- | :-- | :-- |
| [`CVE-2025-62506`](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr) | [minio/minio#21642](https://github.com/minio/minio/pull/21642)，合入提交 [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | [`pgsty/silo@c1a49490`](https://github.com/pgsty/silo/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | 在评估受限会话策略（sub-policy）前重置 `DenyOnly` 标志，防止受限服务账号或 STS 会话派生出继承父级全量权限的不受限子服务账号。上游最早于 [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z) 修复；SILO 自 [`RELEASE.2025-12-03T12-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2025-12-03T12-00-00Z) 起的所有版本均已包含。从更早期上游版本迁移的管理员在升级后应审计由受限服务账号或 STS 身份创建的子服务账号。见[编年史文章](/zh/blog/security/cve-2025-62506/)。 |
| `CVE-2026-32285` | 同一上游提交 [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190)（[pgsty/silo#26](https://github.com/pgsty/silo/issues/26)） | 已包含（`buger/jsonparser v1.1.2`） | 外部漏洞源将 `CVE-2025-62506` 的会话策略修复提交（`c1a49490`）误标为 `buger/jsonparser` 漏洞；SILO `go.mod` 已选用包含修复的 `v1.1.2`，且 `govulncheck` 确认不存在可达漏洞符号，无需修改代码。见[研判记录](/zh/blog/security/cve-2026-32285/)。 |

## 自 `RELEASE.2026-03-21T00-00-00Z` 以来的安全公告 {#advisories}

| 编号 | 修复提交 | 受影响模块 | 编年史 / 发布说明 |
| :-- | :-- | :-- | :-- |
| [`CVE-2026-33322`](#cve-2026-33322) | [`d24f449e0`](https://github.com/pgsty/silo/commit/d24f449e0) | OIDC STS（`AssumeRoleWithWebIdentity`、`AssumeRoleWithClientGrants`） | [编年史](/zh/blog/security/cve-2026-33322/) |
| [`CVE-2026-33419`](#cve-2026-33419) | [`3b950f8fa`](https://github.com/pgsty/silo/commit/3b950f8fa) 及后续提交 | LDAP STS 认证与并发限流 | [编年史](/zh/blog/security/cve-2026-33419/) |
| [`CVE-2026-34204`](#cve-2026-34204) | [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd) | 复制元数据请求头清洗 | [编年史](/zh/blog/security/cve-2026-34204/) |
| [`CVE-2026-39414`](#cve-2026-39414) | [`3252d5b7f`](https://github.com/pgsty/silo/commit/3252d5b7f)、[`5dc705936`](https://github.com/pgsty/silo/commit/5dc705936) | S3 Select 超大 CSV 与 JSON Lines 记录处理 | [编年史](/zh/blog/security/cve-2026-39414/) |
| [`CVE-2026-41145`](https://github.com/advisories/GHSA-hv4r-mvr4-25vw) | [`f444b6f37`](https://github.com/pgsty/silo/commit/f444b6f37) | `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 预签名查询参数认证 | [编年史](/zh/blog/security/cve-2026-41145/) |
| [`CVE-2026-40344`](https://github.com/advisories/GHSA-9c4q-hq6p-c237) | [`efb6e5b00`](https://github.com/pgsty/silo/commit/efb6e5b00) | Snowball `PutObjectExtract` 无签名尾标流式认证 | [编年史](/zh/blog/security/cve-2026-40344/) |
| [`CVE-2026-42600`](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7) | [`73ac52472`](https://github.com/pgsty/silo/commit/73ac52472)（`73ac5244d`） | 节点间 `ReadMultiple`（`/rmpl`）路径穿越 | [编年史](/zh/blog/security/cve-2026-42600/) |
| [`SN-2026-002`](#sn-2026-002) | [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) .. [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff) | 节点间 RPC、`peerREST` 与 `xlStorage` 路径及内存边界收口 | [编年史](/zh/blog/security/internode-path-containment/) |
| [`SN-2026-003`](#sn-2026-003) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0)、[`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f78352aed8e08866d370c9426c73362cf)、[`7a8fa5bc2`](https://github.com/pgsty/silo/commit/7a8fa5bc2)、[`eb74f7e40`](https://github.com/pgsty/silo/commit/eb74f7e40) | S3 策略条件值来源（`s3:VersionId`、对象标签、`signatureAge`） | [编年史](/zh/blog/security/s3-versionid-conditions/) |
| [`SN-2026-004`](#sn-2026-004) | `silo-pkg` [`v3.11.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0)（`d8b1fa7`）、[`97b7d2804`](https://github.com/pgsty/silo/commit/97b7d2804) | 禁止纯对象级授权（`arn:aws:s3:::bucket/*`）越界执行桶级写操作 | [编年史](/zh/blog/security/object-grant-bucket-reach/) |
| [`SN-2026-005`](#sn-2026-005) | `silo-pkg` [`v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0)（`2b087a1`）、[`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c) | 策略写入路径拒绝空资源裸 ARN 前缀（`arn:aws:s3:::`） | [编年史](/zh/blog/security/s3-versionid-conditions/#sn-2026-005) · [pkg v3.12.0](/zh/blog/release/pkg-3.12.0/) |
| [`SN-2026-006`](#sn-2026-006) | [`b73581b05`](https://github.com/pgsty/silo/commit/b73581b05)、[`c4fd97d0b`](https://github.com/pgsty/silo/commit/c4fd97d0b)、[`e2b0cf32f`](https://github.com/pgsty/silo/commit/e2b0cf32f)（[#82](https://github.com/pgsty/silo/issues/82)） | 零字节 SSE-C 对象读取与复制密钥校验 | [编年史](/zh/blog/security/20260903-server-hardening/#sn-2026-006) |
| [`SN-2026-007`](#sn-2026-007) | [`474cd5801`](https://github.com/pgsty/silo/commit/474cd5801)、[`74c97d005`](https://github.com/pgsty/silo/commit/74c97d005)、[`21870fa2e`](https://github.com/pgsty/silo/commit/21870fa2e)、[`e2b0cf32f`](https://github.com/pgsty/silo/commit/e2b0cf32f)（[#84](https://github.com/pgsty/silo/issues/84)） | SSE-C 对象 `GetObjectAttributes` 密钥校验 | [编年史](/zh/blog/security/20260903-server-hardening/#sn-2026-007) |
| [`SN-2026-008`](#sn-2026-008) | [`938603458`](https://github.com/pgsty/silo/commit/938603458) .. [`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9) | 内部复制请求头（`X-Minio-Source-*`）鉴权后信任边界 | [编年史](/zh/blog/security/20260903-server-hardening/#sn-2026-008) · [设计](/zh/blog/design/cors-replication-trust/) |
| [`SN-2026-009`](#sn-2026-009) | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee38)、[`229fe2b3c`](https://github.com/pgsty/silo/commit/229fe2b3c)、[`0c8b02344`](https://github.com/pgsty/silo/commit/0c8b02344)、[`4dbeb15d8`](https://github.com/pgsty/silo/commit/4dbeb15d8) | 用户与组启用/禁用按目标状态分别鉴权 | [编年史](/zh/blog/security/20260903-server-hardening/#sn-2026-009) · [设计](/zh/blog/design/user-status-permissions/) |
| [`SN-2026-010`](#sn-2026-010) | [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) .. [`d2d47a41f`](https://github.com/pgsty/silo/commit/d2d47a41f)、[`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9)（[#58](https://github.com/pgsty/silo/issues/58)） | 显式对象版本删除强制要求 `s3:DeleteObjectVersion` | [编年史](/zh/blog/security/20260903-server-hardening/#sn-2026-010) · [发布说明](/zh/blog/release/delete-object-version-authorization/) |
| [`SN-2026-011`](#sn-2026-011) | [`123325430`](https://github.com/pgsty/silo/commit/123325430)、[#173](https://github.com/pgsty/silo/pull/173)、[#177](https://github.com/pgsty/silo/pull/177) | SigV4 `SignedHeaders` 全量 `X-Amz-` 请求头覆盖校验 | [编年史](/zh/blog/security/20260913-signed-header-status/) · [设计](/zh/blog/design/signed-header-coverage/) |
| [`SN-2026-012`](#sn-2026-012) | [`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4)、[#177](https://github.com/pgsty/silo/pull/177) | 仅通过请求头携带哈希时的预签名载荷 SHA-256 校验 | [编年史](/zh/blog/security/20260916-release-hardening/#sn-2026-012) |
| [`SN-2026-013`](#sn-2026-013) | [`f99ed829b`](https://github.com/pgsty/silo/commit/f99ed829b5eba549160725f035156c9e020b6a07)、[`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce) | 持久化 IAM 吊销注册表与按范围 STS 吊销 | [编年史](/zh/blog/security/20260916-release-hardening/#sn-2026-013) · [设计](/zh/blog/design/iam-revocations/) |
| [`SN-2026-014`](#sn-2026-014) | [`silo-console#56`](https://github.com/pgsty/silo-console/pull/56)、[#209](https://github.com/pgsty/silo/pull/209) | Console 匿名分享下载代理路径收紧 | [编年史](/zh/blog/security/20260916-release-hardening/#sn-2026-014) · [Console v2.4.1](/zh/blog/release/console-2.4.1/) |
| [`SN-2026-015`](#sn-2026-015) | [`14042b5aa`](https://github.com/pgsty/silo/commit/14042b5aa3cbda79eb7aa79aa2ae6931e026e270)、[#234](https://github.com/pgsty/silo/pull/234)、[#235](https://github.com/pgsty/silo/pull/235) | `PutObjectRetention` 鉴权与治理保留期绕过修复 | [编年史](/zh/blog/security/20260926-governance-retention-bypass/) · [设计](/zh/blog/design/governance-retention-bypass-repair/#sn-2026-015) |
| [`SN-2026-016`](#sn-2026-016) | [`14042b5aa`](https://github.com/pgsty/silo/commit/14042b5aa3cbda79eb7aa79aa2ae6931e026e270)、[`0d3ba5d4c`](https://github.com/pgsty/silo/commit/0d3ba5d4cb1245b9f950f491ab0827c9d25fd338) | 指定版本与原地写入的对象锁覆写拦截 | [编年史](/zh/blog/security/20261018-release-hardening/#object-lock) · [设计](/zh/blog/design/governance-retention-bypass-repair/#sn-2026-016) |
| [`SN-2026-017`](#sn-2026-017) | [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fb29fa0e97b875948f6e595163a72f56b)、[`995439260`](https://github.com/pgsty/silo/commit/995439260)、[#242](https://github.com/pgsty/silo/pull/242) | 委派 IAM Admin 凭据与策略包含性授权边界 | [编年史](/zh/blog/security/20261018-release-hardening/#sn-2026-017) · [设计](/zh/blog/design/iam-admin-authorization/) |
| [`SN-2026-018`](#sn-2026-018) | [`fe6dc4780`](https://github.com/pgsty/silo/commit/fe6dc4780) | 转发客户端源地址信任边界（`MINIO_API_TRUSTED_PROXIES`） | [编年史](/zh/blog/security/source-address-trust/) |
| [`SN-2026-019`](#sn-2026-019) | [`672c07a0f`](https://github.com/pgsty/silo/commit/672c07a0f)、[`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) | 通知配置键注册与 `config.HasSensitiveKeys` 敏感凭据脱敏 | [编年史](/zh/blog/security/notify-keyspace-registration/) · [设计](/zh/blog/design/notify-url/) |

## 暴露条件与升级指引 {#exposure}

### CVE-2025-62506 — 会话策略权限提升 {#cve-2025-62506}

支持远程利用（需持有附加了内联会话策略的服务账号或 STS 临时凭据）。上游在 `c1a49490`（`RELEASE.2025-10-15T17-29-55Z`）中修复了评估子策略时的 `DenyOnly` 重置遗漏；SILO 自首个版本 `RELEASE.2025-12-03T12-00-00Z` 起已继承该修复。从更旧上游版本迁移的集群应升级并审计曾由受限父会话创建的子服务账号。详见 [CVE-2025-62506 公告](/zh/blog/security/cve-2025-62506/)。

### CVE-2026-32285 — 误标为 `jsonparser` 的重复公告 {#cve-2026-32285}

公开漏洞源将 `CVE-2026-32285` 描述为 `buger/jsonparser` 漏洞，但其引用的上游修复提交（`c1a49490`）实为修复会话策略提权的 `CVE-2025-62506`。SILO 已选用 `github.com/buger/jsonparser v1.1.2`，且 `govulncheck` 确认无可达漏洞符号。详见 [CVE-2026-32285 研判记录](/zh/blog/security/cve-2026-32285/)。

### CVE-2026-33322 — OIDC JWT 算法混淆 {#cve-2026-33322}

支持远程利用（前提为启用了 OIDC `AssumeRoleWithWebIdentity` 或 `AssumeRoleWithClientGrants`，且攻击者获知或猜中 `client_secret` 以伪造 `HS256`/`HS384`/`HS512` 令牌）。提交 `d24f449e0` 将 JWT 验签严格绑定至身份提供方的非对称 JWKS 公钥集，并从 `token.Parse` 中移除了 `client_secret` 对称 HMAC 回退。依赖对称 HMAC 签名 `id_token` 的非标准部署需在升级前将 IdP 切换为非对称签名算法（如 `RS256`、`ES256`）。

### CVE-2026-33419 — LDAP STS 枚举与拒绝服务 {#cve-2026-33419}

支持远程利用（启用 `AssumeRoleWithLDAPIdentity` 时）。修复后认证失败统一返回 `400 InvalidParameterValue`，不再泄露底层目录错误；通过预留/提交/取消/退还（reserve/commit/cancel/refund）生命周期限制并发 LDAP bind 数量；并在 `RELEASE.2026-06-18` 中移除了按用户名共享的限流桶（此前攻击者只要知道受害者的 `LDAPUsername`，即可从轮换 IP 发送错误密码长期锁死该用户）。详见 [LDAP STS 编年史](/zh/blog/security/cve-2026-33419/)。

### CVE-2026-34204 — 复制元数据注入 {#cve-2026-34204}

支持远程利用。阻止普通客户端在 `PutObject` 或 `CopyObject` 请求中夹带未授权的 `X-Minio-Replication-*` 请求头写入内部复制元数据（此前会导致对象无法读取）。任何接受非授信写入的生产服务端均应升级。后续对复制请求头边界的完整收口见 [SN-2026-008](#sn-2026-008) 与[副本元数据规范化设计](/zh/blog/design/replica-metadata-normalization/)。

### CVE-2026-39414 — S3 Select 超大记录内存耗尽 {#cve-2026-39414}

支持远程利用（需 `s3:SelectObjectContent` 权限）。对超过 1 MiB（`maxCharsPerRecord`）的 CSV 与 JSON Lines 单条记录返回 `OverMaxRecordSize`，防止无界读入耗尽节点内存。四月补丁（`3252d5b7f`）收口了 CSV 与标准 JSON 读取器；六月后续补丁（`5dc705936`）在支持 AVX2/AVX-512 的 CPU 上同样将 JSON Lines 路由至有界 `json.PReader`（停用无行长上限的 `simdj.NewReader`），堵住了硬件相关的 SIMD 绕过路径。详见 [S3 Select 编年史](/zh/blog/security/cve-2026-39414/)。

### CVE-2026-41145 — 无签名尾标流式请求查询参数认证绕过 {#cve-2026-41145}

支持远程利用。修复了在 `PutObject` 或 `PutObjectPart` 请求中同时使用 `X-Amz-Content-Sha256: STREAMING-UNSIGNED-PAYLOAD-TRAILER` 与 URL 查询参数 SigV4 凭据时的认证绕过漏洞。

### CVE-2026-40344 — Snowball 自动解包无签名尾标认证绕过 {#cve-2026-40344}

支持远程利用。在 `newUnsignedV4ChunkedReader()` 构造阶段即完成 SigV4 认证校验，确保 `PutObjectExtract`（Snowball 批量归档上传）在未通过认证前绝不向 `untar()` 解包器提供任何字节。

### CVE-2026-42600 — 节点间 `ReadMultiple` 路径穿越 {#cve-2026-42600}

支持远程利用（需持有集群内部 JWT）。直接删除了未使用的 `/rmpl`（`xlStorage.ReadMultiple`）内部 RPC 端点，消除通过 msgpack 请求体逃逸磁盘根目录读取任意文件的路径。单节点部署不注册该路由；分布式纠删码集群应升级。

### SN-2026-002 — 节点间载荷路径与内存边界收口 {#sn-2026-002}

支持远程利用（需持有集群内部 JWT）。作为 `CVE-2026-42600` 的全面后续排查，覆盖其余全部节点间协议面（`storageREST`、`peerREST`、`grid` WebSocket 帧与 `xlStorage`）：在存储层两处必经收口点（`getVolDir`/`NSScanner` 与 `getStorage()` 的 `guardPaths`、`hasBadPathComponent`、`isVolumeRootAlias`）拦截卷名与路径穿越，为调用方声明的切片分配加上硬上限（`maxDeleteVersions = 1000` 及 `BitrotVerifier` 上限），在除法前校验纠删码 `DataBlocks`/`ParityBlocks` 防止单帧除零崩溃，并在返回前核对分片实际长度。单节点部署不注册相关路由，S3 API 外部行为不变。详见[节点间路径收口编年史](/zh/blog/security/internode-path-containment/)。

### SN-2026-003 — S3 策略条件值来源隔离 {#sn-2026-003}

支持远程利用（取决于策略配置）。禁止客户端通过同名查询参数或请求头覆盖或伪造服务端内部条件键；将 `s3:signatureAge` 严格限制在经验证的 SigV4 预签名请求中；分离仅限查询参数的列表条件键与基于请求头的 `x-amz-*` 条件键；禁止请求标签冒充已存储对象的 `ExistingObjectTag`；并确保仅当请求显式携带 `?versionId` 时才按去除首尾空白后的实际版本评估 `s3:VersionId`。详见 [SN-2026-003 编年史](/zh/blog/security/s3-versionid-conditions/)与[策略条件值来源文档](/zh/administration/identity-access-management/policy-based-access-control/#condition-value-sources)。

### SN-2026-004 — 桶级写操作与纯对象级授权隔离 {#sn-2026-004}

支持远程利用（取决于策略配置）。禁止纯对象级资源通配模式（`arn:aws:s3:::bucket/*`）越界匹配 12 项敏感桶级写操作：`PutBucketPolicy`、`DeleteBucketPolicy`、`PutBucketObjectLockConfiguration`、`PutBucketVersioning`、`PutReplicationConfiguration`、`PutBucketLifecycle`、`DeleteBucket`、`ForceDeleteBucket`、`PutBucketCors`、`DeleteBucketCors`、`PutBucketQOS` 与 `PutInventoryConfiguration`，并要求同一条 `Allow` 语句同时匹配操作与资源（单调交集语义）。**若您编写了自定义桶级 IAM 策略，升级前请阅读 [SN-2026-004 编年史](/zh/blog/security/object-grant-bucket-reach/)：** 确需授予上述 12 项桶级写操作的语句，需在 `arn:aws:s3:::bucket/*` 旁显式加上桶 ARN（`arn:aws:s3:::bucket`）。内置预设策略、`Deny` 语句与 `NotResource` 均不受影响。在进程启动环境变量中设置 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` 可恢复旧版匹配行为（该开关在包初始化阶段读取，仅写入 `MINIO_CONFIG_ENV_FILE` 不会生效）。

### SN-2026-005 — 策略写入拒绝空资源裸 ARN 前缀 {#sn-2026-005}

策略收紧变更（`silo-pkg v3.12.0` / Server `eee05a17c`）。在创建命名策略以及创建/更新服务账号会话策略时，拒绝 `Resource` 与 `NotResource` 中不包含任何资源名的 S3、S3 Tables 与 KMS 裸 ARN 命名空间前缀（如 `arn:aws:s3:::` 及其历史序列化形式 `*arn:aws:s3:::`）。已持久化的存量策略继续正常加载、匹配、导入与复制；但重新提交包含裸前缀的策略时，必须替换为具体桶/对象 ARN 或显式全通配符（`arn:aws:s3:::*`）。注意区分无资源的“裸 ARN 前缀”（`arn:aws:s3:::`）与 `SN-2026-004` 中合法的“裸桶 ARN”（`arn:aws:s3:::bucket`）。详见 [SN-2026-003 / SN-2026-005 编年史](/zh/blog/security/s3-versionid-conditions/#sn-2026-005)与 [silo-pkg v3.12.0 发布说明](/zh/blog/release/pkg-3.12.0/)。

### SN-2026-006 — 零字节 SSE-C 对象密钥认证 {#sn-2026-006}

支持远程利用（需具备目标对象读取权限）。零字节 SSE-C 对象此前未执行客户端密钥解封校验，导致提供错误 SSE-C 密钥的请求也能收到 `200 OK`，或以攻击者自选的新密钥复制/覆盖该对象。修复后，零字节 SSE-C 读取与复制均强制解封验证客户密钥，密钥错误时与 AWS S3 一致返回 `403 AccessDenied`。已随 [Server 20260903](/zh/blog/security/20260903-server-hardening/#sn-2026-006) 发布。

### SN-2026-007 — SSE-C 对象 `GetObjectAttributes` 密钥校验 {#sn-2026-007}

支持远程利用（需具备目标对象读取权限）。`GetObjectAttributes` 此前未校验 SSE-C 客户密钥即可返回对象属性，且客户端只要附带 `X-Minio-Source-Replication-Request` 请求头即可直接跳过检查。修复后，错误密钥返回 `403 AccessDenied`，未授权复制标记返回 `400 InvalidArgument`；持有 `s3:ReplicateObject` 权限的复制对端不受影响。已随 [Server 20260903](/zh/blog/security/20260903-server-hardening/#sn-2026-007) 发布。

### SN-2026-008 — 内部复制请求头鉴权后信任边界 {#sn-2026-008}

支持远程利用（任意具备对象读写权限的已认证主体）。完成 `CVE-2026-34204` 的后续收口：此前多个处理器仅凭请求头存在即信任 `X-Minio-Source-Etag`、`X-Minio-Source-Mtime`、`X-Minio-Source-Replication-Request`、`X-Minio-Source-DeleteMarker`、复制 SSE 密钥头及 `X-Amz-Bucket-Replication-Status`。Server 20260903 在验签通过后构造的请求克隆上统一剥离这些内部请求头，仅当请求携带精确标记值且调用方通过 `s3:ReplicateObject` 或 `s3:ReplicateDelete` 鉴权时才予保留。站点复制服务账号与持有复制权限的桶复制目标不受影响。详见[九月安全公告](/zh/blog/security/20260903-server-hardening/#sn-2026-008)与 [CORS 及复制信任设计](/zh/blog/design/cors-replication-trust/)。

### SN-2026-009 — 用户与组状态变更按目标状态鉴权 {#sn-2026-009}

支持远程利用（已认证 Admin API）。`SetUserStatus` 与 `UpdateGroupStatus` 此前无论目标状态是启用还是禁用，一律只检查 `admin:EnableUser` 与 `admin:EnableGroup`，导致仅获授启用权限的操作员也能禁用账户（反之亦然）。修复后按请求的目标状态分别检查 `admin:EnableUser` / `admin:DisableUser` 与 `admin:EnableGroup` / `admin:DisableGroup`。持有 `admin:*` 或内置 `consoleAdmin` 策略的管理员不受影响；仅授予单向权限的最小权限策略将严格限制在对应方向。详见[九月安全公告](/zh/blog/security/20260903-server-hardening/#sn-2026-009)与[用户状态权限设计](/zh/blog/design/user-status-permissions/)。

### SN-2026-010 — 显式对象版本删除强制要求 `s3:DeleteObjectVersion` {#sn-2026-010}

支持远程利用（已认证 S3 API）。携带 `versionId` 的 `DeleteObject` 与 `DeleteObjects` 请求此前按 `s3:DeleteObject` 鉴权（仅检查是否显式 `Deny s3:DeleteObjectVersion`），与 AWS S3 规范不符。修复后显式删除指定版本必须持有 `s3:DeleteObjectVersion`。**两项策略影响：** 仅持有 `s3:DeleteObject` 的主体仍可发起不带版本的删除（创建删除标记），但不能再永久删除指定版本；原先依赖 `Allow s3:*` 配合 `Deny s3:DeleteObject` 来阻止永久删除版本的策略，必须同步加上 `Deny s3:DeleteObjectVersion`。复制目标保持 `s3:ReplicateDelete` 契约不变。详见[显式版本删除鉴权说明](/zh/blog/release/delete-object-version-authorization/)。

### SN-2026-011 — 未签名 `X-Amz-*` 操作请求头拦截 {#sn-2026-011}

支持远程利用（持有预签名 `PUT` URL 或截获普通签名 `PUT` 请求的攻击者）。由于 `cmd/api-router.go` 在检测到 `x-amz-copy-source` 请求头时会将 `PUT` 请求优先路由至 `CopyObjectHandler`，持有预签名 `PUT` URL 的攻击者无需知道签名密钥，即可追加未签名的 `x-amz-copy-source: /src/secret`，诱使服务端以签名者的读取权限将源对象复制到目标路径。若目标路径可读，私有对象内容即遭泄露。由 Oren Yomtov 报告。

已随 **[Server 20260916](/zh/blog/release/silo-20260916/)**（[状态公告](/zh/blog/security/20260913-signed-header-status/)、`123325430`、PR #173、#177）修复。普通 SigV4 与预签名验证路径现在统一调用 `checkUnsignedHeaders`，拒绝任何携带未签名 `X-Amz-*` 请求头的请求（返回 `400 AccessDenied` / `ErrUnsignedHeaders`）。`X-Amz-Content-Sha256` 是唯一豁免列入 `SignedHeaders` 的请求头，其有效值已由规范请求单独绑定并由 `SN-2026-012` 校验；PR #177 同时移除了内部合成的 `X-Amz-Signature-Age` 请求头，直接从已签名的 `X-Amz-Date` 无状态推导签名年龄。标准 AWS SDK、`mcli` 与 `minio-go` 无需改动；自定义客户端若在发送预签名请求时附带 `X-Amz-*` 请求头，必须在生成预签名 URL 时将其纳入 `X-Amz-SignedHeaders`。详见[签名头覆盖设计](/zh/blog/design/signed-header-coverage/)。

### SN-2026-012 — 仅通过请求头携带哈希的预签名载荷校验 {#sn-2026-012}

支持远程利用（持有通过 `X-Amz-Content-Sha256` 请求头绑定载荷哈希的预签名 URL）。`PutBucketPolicy` 等通用认证处理器此前在预签名验签时使用了请求头中的 SHA-256 值，但在消费请求体时未核对该哈希，使预签名 URL 持有者可在保持签名有效的前提下篡改请求体。提交 `c4b5e1cb4`（随 [Server 20260916](/zh/blog/security/20260916-release-hardening/#sn-2026-012) 发布）使通用请求体校验与验签阶段使用完全一致的有效载荷哈希（优先取查询参数，其次回退至请求头），篡改绑定了校验和的请求体将返回 `XAmzContentSHA256Mismatch`。

### SN-2026-013 — 持久化 IAM 吊销与按范围 STS 吊销 {#sn-2026-013}

需持有曾有效签发的凭据并结合节点重启、跨站同步延迟或同名父账户重建场景。在 [Server 20260916](/zh/blog/security/20260916-release-hardening/#sn-2026-013)（`#191`、`#192`、`f99ed829b`）之前，禁用/删除用户、轮换密钥或重建同名父用户后，此前签发的 STS 令牌或子服务账号可能在 JWT 过期前继续有效，或被延迟到达的旧站点复制状态重新激活。Server 20260916 在 `.minio.sys/iam/revocations/` 下持久化删除墓碑、父身份吊销边界与组授权版本；[Server 20261018](/zh/blog/security/20261018-release-hardening/#sts-revocation)（`0cd388c66`）进一步提供 `POST /minio/admin/v3/sts-revoke`，支持按主体或单令牌（`jti`）精确吊销 STS 会话而不影响其他会话。共享同一 IAM 后端的所有节点与站点需协调升级；详见 [IAM 吊销设计](/zh/blog/design/iam-revocations/)与 [IAM 升级手册](/zh/operations/replication/iam-upgrade/)。

### SN-2026-014 — Console 匿名分享下载代理路径收紧 {#sn-2026-014}

支持远程利用（匿名访问 Console `/api/v1/download-shared-object` 接口）。Console 公开分享下载代理此前可转发配置源站上的任意非对象路径，使未登录调用者能够跨越 Console 网络边界访问原本隔离在后端的公开指标等端点（如 `/minio/v2/metrics/cluster`）。由 Jiri Pejchal（`@jiri-pejchal`）报告。已在 **[Console v2.4.1](/zh/blog/release/console-2.4.1/)**（`silo-console#56`）及内嵌该版本的 **[Server 20260916](/zh/blog/security/20260916-release-hardening/#sn-2026-014)**（`#209`）中修复：代理仅允许向源站发起单对象内容 `GET` 请求，在发起连接前拒绝 `/minio/*` 系统路径与非下载类子资源查询参数，并拒绝一切 HTTP 重定向。

### SN-2026-015 — `PutObjectRetention` 鉴权与治理保留期绕过 {#sn-2026-015}

支持远程利用（已认证 S3 调用方）。`PutObjectRetentionHandler`（`cmd/object-handlers.go`）中的三处缺陷使已认证调用方能够：(1) 在未持有 `s3:PutObjectRetention` 权限时，仅凭 `s3:BypassGovernanceRetention` 并附带 `X-Amz-Bypass-Governance-Retention: true` 请求头短路基础动作鉴权并修改对象保留期；(2) 仅凭 `s3:PutObjectRetention`（无 `s3:BypassGovernanceRetention`）通过提交空模式（`Mode: ""`）清空或缩短处于有效期的 `GOVERNANCE` 锁；(3) 在清空保留期时绕过针对 `s3:object-lock-remaining-retention-days` 的 IAM `Deny` 策略。已在 **[Server 20261018](/zh/blog/security/20261018-release-hardening/#object-lock)**（PR #234、#235、`14042b5aa`）中修复：在读取对象前无条件强制校验 `s3:PutObjectRetention`；缩短、清空或降级有效 `GOVERNANCE` 锁必须同时携带 `X-Amz-Bypass-Governance-Retention: true` 并通过 `s3:BypassGovernanceRetention` 鉴权；清空保留期时将剩余天数按 `0` 注入策略上下文。详见 [SN-2026-015 / SN-2026-016 安全公告](/zh/blog/security/20260926-governance-retention-bypass/)与[修复架构设计](/zh/blog/design/governance-retention-bypass-repair/#sn-2026-015)。

### SN-2026-016 — 指定版本与原地写入的对象锁覆写 {#sn-2026-016}

支持远程利用（已认证 S3 写入方）。调用方在 `PutObject`、`CopyObject`、`CompleteMultipartUpload` 或 `PutObjectExtract` 请求中显式传入 `?versionId=<已有版本 UUID>`，或在未启用版本控制/挂起版本控制的桶上原地覆写 `null` 版本对象（含目录对象与分段上传完成路径）时，可绕过对象锁检查直接覆写受 `COMPLIANCE`、`GOVERNANCE` 保留期或 `LegalHold` 保护的对象版本。已在 **[Server 20261018](/zh/blog/security/20261018-release-hardening/#object-lock)**（`14042b5aa`、`0d3ba5d4c`）中修复：S3 入口拒绝任何非授权复制请求（`!isReplicationRequest`）显式指定目标 `versionId`；预检读取元数据失败时采取 Fail-Closed 拒绝；存储层写入路径（`PutObject`、`CopyObject`、`CompleteMultipartUpload`、`PutObjectDir`）在持有命名空间写锁后再次复检目标版本的对象锁状态（`checkObjectLockForOverwrite`）。请升级所有接受写入的 Server 节点与复制站点。详见[修复架构设计](/zh/blog/design/governance-retention-bypass-repair/#sn-2026-016)。

### SN-2026-017 — 委派 IAM Admin 凭据授权边界 {#sn-2026-017}

支持远程利用（已认证的委派 IAM 管理员或受限派生凭据）。在 Server 20260916 及更早版本中，持有 `admin:CreateUser`、`admin:AttachUserOrGroupPolicy` 或 `admin:UpdateServiceAccount` 等权限的非 root 管理员可以分配超出自身有效权限范围的策略、修改更高权限的用户/组/服务账号，或通过自助管理路由逃逸会话策略与显式 `Deny` 限制。已在 **[Server 20261018](/zh/blog/security/20261018-release-hardening/#sn-2026-017)**（`2616d43fb`、`995439260`、PR #242）中修复：委派 IAM 写操作全面执行目标策略包含性校验（`authorizePolicyChange`、`authorizeGroupTargets`、`authorizeTargetUser`），并拦截非 root 主体对自身权限的变更（`ErrAdminChangeUserSelfPermission`）。详见[委派 IAM 管理授权设计](/zh/blog/design/iam-admin-authorization/)。

### SN-2026-018 — 客户端源地址信任边界（`MINIO_API_TRUSTED_PROXIES`） {#sn-2026-018}

#### 转发头信任策略 {#source-address-trust}

可选启用的安全加固（`fe6dc4780`，随 [Server 20260804](/zh/blog/release/silo-20260804/) 发布）。继承自上游的默认实现无条件信任任意直连对端发来的 `X-Forwarded-For` 与 `X-Real-IP` 请求头，导致可直连 Server（或经由追加式反向代理访问）的客户端能够伪造 `aws:SourceIp` IAM 条件值并绕过按 IP 计数的 LDAP 限流。`MINIO_API_TRUSTED_PROXIES` 提供了可强制执行的代理信任边界：设为 `none` 时完全忽略转发头，仅使用 TCP 对端地址；设为逗号分隔的代理 IP 或 CIDR 列表时，仅信任来自白名单对端（及本机 loopback sidecar）的转发头，并从右向左跳过可信跳数提取首个非可信客户端 IP。启用该变量的多节点集群必须将集群自身节点 IP/CIDR 一并列入白名单，以便节点间转发请求保留原始客户端 IP。详见[来源地址信任编年史](/zh/blog/security/source-address-trust/)与[核心配置参考](/zh/reference/minio-server/settings/core/#client-source-address-trust)。

### SN-2026-019 — 通知配置键注册与敏感凭据脱敏 {#sn-2026-019}

配置子系统加固（`672c07a0f` 随 [Server 20260804](/zh/blog/release/silo-20260804/) 发布，后续 `f1ba68358` 随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布）。对 `notify_postgres` 与 `notify_mysql` 的审计发现，`config.HasSensitiveKeys` 未将 `password`、`dsn_string` 与 `connection_string` 标记为敏感字段（导致配置校验报错或 `GetConfigKV` 可能回显明文凭据），且 5 个离散连接参数未注册进 `Keyspace`。提交 `672c07a0f` 补齐了 `config.HasSensitiveKeys` 凭据脱敏与跨子系统键注册结构化测试；[Server 20260903](/zh/blog/design/notify-url/) 随后退役了 5 个离散字段并统一收敛至 `connection_string` 与 `dsn_string`，消除了两套配置表示在启动迁移时的静默覆盖隐患。详见[通知键空间编年史](/zh/blog/security/notify-keyspace-registration/)与[数据库通知连接串设计](/zh/blog/design/notify-url/)。

## 依赖安全更新 {#dependencies}

[Server 20261018](/zh/blog/release/silo-20261018/) 使用 Go 1.27.2 构建，并升级至 `golang.org/x/net v0.61.0`、`golang.org/x/crypto v0.58.0`、`golang.org/x/text v0.43.0` 与 `github.com/go-jose/go-jose/v4 v4.1.6`（注意 [`go-jose` RSA JWK 解析修复](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)同时拒绝大于 4096 位的 RSA 密钥，升级前请核验 OIDC/JWKS 身份提供方密钥长度）。全栈 Go 1.27.3 与静态 `curl 8.23.0` 维护记录见 [SILO 20261025](/zh/blog/release/silo-20261025/)。

| 公告 / 范围 | 修复提交 | 摘要 |
| :-- | :-- | :-- |
| `CVE-2026-39883` | `1869bd30b`、`e4fa06394` | 更新 OpenTelemetry 依赖（`RELEASE.2026-03-21`）。 |
| 2026-03-25 发布 | [`RELEASE.2026-03-25`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-03-25T00-00-00Z) | 更新 OTel SDK、Paho MQTT 与 `x/crypto`，涵盖 `CVE-2026-24051`、`CVE-2025-10543` 与 `CVE-2025-58181`。 |
| `CVE-2026-34986` | [`68e0ba997`](https://github.com/pgsty/silo/commit/68e0ba997) | 升级 `go-jose` 至 `v4.1.4`。 |
| Go 1.26.2 标准库 | [`db4c0fd5e`](https://github.com/pgsty/silo/commit/db4c0fd5e) | 修复 `CVE-2026-32280`、`CVE-2026-32281`（`crypto/x509`）与 `CVE-2026-32283`（`crypto/tls`）。 |
| Go 1.26.4 与依赖刷新 | `df627ff89`、`3e61b1d3a` | 修复 `CVE-2026-32952`（Azure NTLM）、`CVE-2026-41602`（Thrift）并更新 NATS/Prometheus 依赖（`RELEASE.2026-06-18`）。 |
| Go 1.26.5 标准库 | [Go 1.26.5](https://go.dev/doc/devel/release#go1.26.5)（[Server 20260806](/zh/blog/release/silo-20260806/)） | 修复 `crypto/tls` 与 `os` 中的 `GO-2026-4946`、`GO-2026-4947`、`GO-2026-4948`。 |
| [GO-2026-6061](https://pkg.go.dev/vuln/GO-2026-6061) / [GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf) | [`4dfc27ce3`](https://github.com/pgsty/silo/commit/4dfc27ce3) | 升级 gRPC 至 `v1.82.1`（修复 xDS RBAC 引擎与 HTTP/2 传输层问题）及 `golang.org/x/text` 至 `v0.39.0`（[GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852`）。 |
| [GO-2026-5841](https://pkg.go.dev/vuln/GO-2026-5841) | [`c1aec0518`](https://github.com/pgsty/silo/commit/c1aec0518) | 升级 `github.com/klauspost/compress` 至 `v1.18.7`。 |
| Go 1.27.1 与九月依赖刷新 | [Go 1.27.1](https://go.dev/doc/devel/release#go1.27.1) 经 [`43f4bb7ed`](https://github.com/pgsty/silo/commit/43f4bb7ed)、[`edc8be6ed`](https://github.com/pgsty/silo/commit/edc8be6ed)、[`4d6e1ea8e`](https://github.com/pgsty/silo/commit/4d6e1ea8e) | 迁移至 Go 1.27.1，更新 `etcd` 客户端（`v3.7.1`）、`jwx`（`v3.0.13`）与 `klauspost/compress`（`v1.19.2`），并回归上游 `minio-go v7.3.1`（[Server 20260903](/zh/blog/release/silo-20260903/)）。 |
| [GO-2026-6354](https://pkg.go.dev/vuln/GO-2026-6354) / [GO-2026-6355](https://pkg.go.dev/vuln/GO-2026-6355) | [`edf36bcbf`](https://github.com/pgsty/silo/commit/edf36bcbf) | 升级 `golang.org/x/crypto` 至 `v0.56.0`，修复通过 SFTP/SSH 通道死锁触发的拒绝服务（`startSFTPServer` → `sftp.Server.Listen` → `ssh.NewServerConn`）。 |
| [CVE-2026-84304](https://github.com/advisories/GHSA-vp52-pcj8-j9qc) | gRPC `v1.83.1` | 修复 gRPC-Go 在高分片 HTTP/2 `DATA` 帧下的未认证堆内存耗尽问题。 |
| [CVE-2026-79921 / GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp) | [`d63c92e39`](https://github.com/pgsty/silo/commit/d63c92e39)（[Server 20260916](/zh/blog/release/silo-20260916/)） | 升级 `amqp091-go` 至 `v1.14.0`，防止恶意 AMQP broker 发送超大帧耗尽客户端内存。 |
| Go 1.27.2 与十月依赖刷新 | [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce)（[Server 20261018](/zh/blog/security/20261018-release-hardening/#dependencies)） | 升级至 Go 1.27.2、`x/net v0.61.0`、`x/crypto v0.58.0`、`x/text v0.43.0` 与 `go-jose/v4 v4.1.6`（`GHSA-mgcc-cww5-fp2q`）。 |

## 运维相关的安全修复 {#operational}

| 变更 | 修复提交 | 摘要 |
| :-- | :-- | :-- |
| 复制 Object Lock 更新时间戳顺序 | [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9)（[Server 20260903](/zh/blog/release/silo-20260903/)） | 复制 `CopyObject` 此前在比较复制时间戳前就从请求重建元数据，且将法务保留（legal-hold）时间戳误写入保留期键下，导致乱序到达的旧副本事件可能关闭更新的法务保留或缩短保留期。修复后先读取磁盘已有状态，仅当副本时间戳更新时才应用变更，并将两类时间戳分别存储在各自键下。见[对象锁复制顺序设计](/zh/blog/design/object-lock-replication-ordering/)。 |
| `ldaps://` TLS 配置传递回归 | [`ce1c537eb`](https://github.com/pgsty/silo/commit/ce1c537eb1dd6c4efa1cf75cf5df0e2c489c947a)（`RELEASE.2026-03-25`） | 恢复 `ldaps://` `DialURL()` 连接的 TLS 配置传递，使 `MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY` 与自定义根 CA 重新生效。 |
| 签名字段与策略输入对齐 | [#177](https://github.com/pgsty/silo/pull/177)、[`87d8b5967`](https://github.com/pgsty/silo/commit/87d8b5967)（[Server 20260916](/zh/blog/release/silo-20260916/)） | 拒绝有歧义的重复 `x-amz-copy-source` 值，从已签名 `X-Amz-Date` 无状态推导 `s3:signatureAge`，并将 `s3:x-amz-content-sha256` 策略条件绑定至经验证的载荷哈希。 |
| 跨存储池条件 `PUT` 与 `DELETE` | [#207](https://github.com/pgsty/silo/pull/207)、[`5e7d60308`](https://github.com/pgsty/silo/commit/5e7d60308)（[Server 20260916](/zh/blog/release/silo-20260916/)） | 在共享跨池锁下针对当前权威逻辑对象评估写入与删除前置条件（`If-Match`、`If-None-Match`），防止旧存储池中的陈旧副本越权放行覆盖写入。见[多存储池对象一致性设计](/zh/blog/design/multi-pool-object-consistency/)。 |

## 台账归属 {#attribution}

本页由原 `pgsty/silo` 安全台账（`docs/security/advisories.md`，更新至 `f99ed829b5eba` / `40220bd836cb`）维护演进而来，发布状态与[组件版本矩阵](/zh/compatibility/versions/)保持同步。各漏洞的排查链路、被否决方案对比与验证命令见对应的[安全编年史](/zh/blog/security/)与[设计笔记](/zh/blog/design/)文章。
