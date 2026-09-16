---
title: "安全公告台账"
linkTitle: "安全公告"
description: "SILO 安全公告台账：CVE 与 SN 编号、修复提交、受影响面、发布边界与依赖安全更新。"
url: "/zh/about/security-advisories/"
weight: 41
type: docs
icon: fa-solid fa-shield-halved
---

本台账汇总 `pgsty/silo` 的 fork 专属安全修复及密切相关的升级影响说明。它有意比
changelog 更窄，只关注影响发布的安全行为。每个经过完整调查的公告在[安全编年史](/zh/blog/security/)另有独立文章；本页是编号、修复与发布边界的稳定索引。

条目在有 CVE 编号时使用 CVE。没有 CVE 的发现使用 fork 本地
`SN-<年份>-<序号>` 编号，使其仍能被发布说明、提交与 issue 稳定引用。`SN-`
编号**不是** CVE，也未登记到任何漏洞数据库；它刻意不写成 CVE 形式，避免被扫描器误认。上游
`minio/minio` 已归档，继承代码中的发现没有上游维护者可以协调 CVE
分配。`SN-2026-001` 是 `trackingResponseWriter` 的流式刷新回归，属于可靠性缺陷而非安全问题，记录在发布说明而非本页。

## 当前发布边界 {#boundary}

**核验于 2026-09-16。** 最新已发布 Server 为
[`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z)。
[SN-2026-011](#sn-2026-011) 已在 main 修复，但该版本及之前所有公开 Server 版本仍受影响。升级
mcli、pkg 或独立 Console 不会修补已安装的 Server。源码钉定见[组件版本矩阵](/zh/compatibility/versions/)。

## 继承自上游的公告基线 {#inherited}

Silo 首个社区版本切自已包含以下安全修复的上游历史。上游与 Silo 链接同时记录——即使
fork 保留了同一提交对象与 SHA；该同一性是继承证据，不表示 Silo 独立重新实现了补丁。

| 编号 | 上游修复 | Silo 继承 | 发布说明 |
| :-- | :-- | :-- | :-- |
| [CVE-2025-62506](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr) | [minio/minio#21642](https://github.com/minio/minio/pull/21642)，合入为 [`c1a49490`](https://github.com/minio/minio/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | 同一提交对象存在于 [`pgsty/silo@c1a49490`](https://github.com/pgsty/silo/commit/c1a49490c78e9c3ebcad86ba0662319138ace190) | 在评估受限会话策略时重置 `DenyOnly`，使服务账号或 STS 账号无法铸造无限制的子服务账号。上游首次修复于 [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)；Silo 每个社区版本（自 [`RELEASE.2025-12-03T12-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2025-12-03T12-00-00Z) 起）均包含。从更旧上游构建迁移的用户应升级并审计受限 service/STS 身份创建的服务账号。见[编年史文章](/zh/blog/security/cve-2025-62506/)。 |

## `RELEASE.2026-03-21T00-00-00Z` 之后的公告 {#advisories}

| 编号 | 修复 | 受影响面 | 编年史 / 发布说明 |
| :-- | :-- | :-- | :-- |
| `CVE-2026-33322` | [`d24f449e0`](https://github.com/pgsty/silo/commit/d24f449e0) | OIDC STS（`AssumeRoleWithWebIdentity`、`AssumeRoleWithClientGrants`） | [编年史](/zh/blog/security/cve-2026-33322/) |
| `CVE-2026-33419` | [`3b950f8fa`](https://github.com/pgsty/silo/commit/3b950f8fa) 及后续 | LDAP STS 认证 | [编年史](/zh/blog/security/cve-2026-33419/) |
| `CVE-2026-34204` | [`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd) | 复制元数据处理 | [编年史](/zh/blog/security/cve-2026-34204/) |
| `CVE-2026-39414` | [`3252d5b7f`](https://github.com/pgsty/silo/commit/3252d5b7f) | S3 Select 超大记录处理 | [编年史](/zh/blog/security/cve-2026-39414/) |
| [CVE-2026-41145](https://github.com/advisories/GHSA-hv4r-mvr4-25vw) | [`f444b6f37`](https://github.com/pgsty/silo/commit/f444b6f37) | Unsigned-trailer PUT 与分块上传认证 | [编年史](/zh/blog/security/cve-2026-41145/) |
| [CVE-2026-40344](https://github.com/advisories/GHSA-9c4q-hq6p-c237) | [`efb6e5b00`](https://github.com/pgsty/silo/commit/efb6e5b00) | Snowball 自动解包认证 | [编年史](/zh/blog/security/cve-2026-40344/) |
| [CVE-2026-42600](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7) | [`73ac52472`](https://github.com/pgsty/silo/commit/73ac52472) | 内部节点 `ReadMultiple` storage-REST 端点 | [编年史](/zh/blog/security/cve-2026-42600/) |
| [`SN-2026-002`](#sn-2026-002) | [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) 及后续 | 内部节点 storage-REST 与 Grid RPC 载荷 | [编年史](/zh/blog/security/internode-path-containment/) · [发布说明](/zh/blog/release/silo-20260804/#sn-2026-002) |
| [`SN-2026-003`](#sn-2026-003) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) 与 [`2f55347f7`](https://github.com/pgsty/silo/commit/2f55347f78352aed8e08866d370c9426c73362cf) | S3/IAM 桶策略条件值 | [发布说明](/zh/blog/release/silo-20260804/#sn-2026-003) |
| [非漏洞](#source-address-trust) | [`fe6dc4780`](https://github.com/pgsty/silo/commit/fe6dc4780) | 客户端源地址（`aws:SourceIp`、审计 `remotehost`、事件 `Host`） | [编年史](/zh/blog/security/source-address-trust/) |
| [`SN-2026-004`](#sn-2026-004) | [silo-pkg v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) 与 [`97b7d2804`](https://github.com/pgsty/silo/commit/97b7d28040d109061c0a46a4c01bfc7800a97cc1) | IAM 策略对桶级动作的评估 | [编年史](/zh/blog/security/object-grant-bucket-reach/) · [发布说明](/zh/blog/release/silo-20260804/#sn-2026-004) |
| [`SN-2026-005`](#sn-2026-005) | [silo-pkg v3.12.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0) 与 [`eee05a17c`](https://github.com/pgsty/silo/commit/eee05a17c34a07cebb27220d12697be74c8bd617) | IAM 具名策略与服务账号策略写入 | [发布说明](/zh/blog/release/pkg-3.12.0/) |
| [`SN-2026-006`](#sn-2026-006) | [`b73581b05`](https://github.com/pgsty/silo/commit/b73581b05)、[`c4fd97d0b`](https://github.com/pgsty/silo/commit/c4fd97d0b)（[#82](https://github.com/pgsty/silo/issues/82)） | 零字节对象的 SSE-C 读取 | [编年史](/zh/blog/security/20260903-server-hardening/) |
| [`SN-2026-007`](#sn-2026-007) | [`474cd5801`](https://github.com/pgsty/silo/commit/474cd5801)、[`74c97d005`](https://github.com/pgsty/silo/commit/74c97d005)、[`21870fa2e`](https://github.com/pgsty/silo/commit/21870fa2e)（[#84](https://github.com/pgsty/silo/issues/84)） | SSE-C 对象的 `GetObjectAttributes` | [编年史](/zh/blog/security/20260903-server-hardening/) |
| [`SN-2026-008`](#sn-2026-008) | [PR #101](https://github.com/pgsty/silo/pull/101)（[`938603458`](https://github.com/pgsty/silo/commit/938603458) 至 [`04b097fd9`](https://github.com/pgsty/silo/commit/04b097fd9)） | 内部复制请求头 | [编年史](/zh/blog/security/20260903-server-hardening/) |
| [`SN-2026-009`](#sn-2026-009) | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee38)、[`229fe2b3c`](https://github.com/pgsty/silo/commit/229fe2b3c)（[PR #73](https://github.com/pgsty/silo/pull/73)） | Admin `SetUserStatus` / `SetGroupStatus` | [编年史](/zh/blog/security/20260903-server-hardening/) |
| [`SN-2026-010`](#sn-2026-010) | [PR #104](https://github.com/pgsty/silo/pull/104)（[`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4) 至 [`d2d47a41f`](https://github.com/pgsty/silo/commit/d2d47a41f)，[#58](https://github.com/pgsty/silo/issues/58)） | 显式 `versionId` 的 `DeleteObject`/`DeleteObjects` | [编年史](/zh/blog/security/20260903-server-hardening/) |
| [`SN-2026-011`](#sn-2026-011) | [`123325430`](https://github.com/pgsty/silo/commit/1233254309b15571f101b2b26d531951ceaeef1e) | SigV4 签名头覆盖；`x-amz-copy-source` 分发 | [编年史](/zh/blog/security/20260913-signed-header-status/) |

各条目的升级与兼容性说明如下。有编年史文章的条目在此只做摘要；威胁模型、被否决方案与验证细节请 follow 链接。

### CVE-2026-33322 — OIDC STS JWT 算法混淆 {#cve-2026-33322}

可远程利用。移除 HMAC/共享密钥验证并强制 JWKS 支持的验证密钥，关闭 JWT
算法混淆。**破坏性变更：** 为这些 STS 流程签发 `HS256`/`HS384`/`HS512` 令牌的提供方必须在升级前切换到
JWKS 支持的 RSA 或 ECDSA 签名。`PS256` 与 `EdDSA` 暂不支持。

### CVE-2026-33419 — LDAP STS 用户名枚举 {#cve-2026-33419}

可远程利用。统一未知用户与错误密码的响应（均返回 `400 InvalidParameterValue`）并增加内存登录限流，关闭用户名枚举。六月最终方案只保留来源 IP 限流，移除了可被攻击者用来锁死特定账户的共享用户名桶。限流状态按节点保存在内存中，来源地址信任策略可单独配置。各轮修复见 [LDAP STS 编年史](/zh/blog/security/cve-2026-33419/)。

### CVE-2026-34204 — 复制元数据注入 {#cve-2026-34204}

可远程利用。阻止不可信的 `X-Minio-Replication-*` 头被偷渡进内部复制元数据并导致对象不可读。任何接受不可信 `PutObject`/`CopyObject` 请求的服务器都应升级——实践中即几乎所有接受写入的生产服务器。

### CVE-2026-39414 — S3 Select 超大记录 {#cve-2026-39414}

可远程利用。对超大 CSV 与行分隔 JSON 记录返回 `OverMaxRecordSize`，而非无界缓冲。四月修复最初遗漏了 SIMD JSON 路径；六月后续修复让所有 JSON Lines 走有界的 `json.PReader`，关闭了该绕过。详见 [S3 Select 编年史](/zh/blog/security/cve-2026-39414/)。

### CVE-2026-41145 — unsigned-trailer 认证绕过 {#cve-2026-41145}

可远程利用。关闭 unsigned-trailer 流式请求中的查询串认证绕过。若客户端能以 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` content-sha256 模式加查询串 SigV4 凭据到达对象写入端点，应升级。

### CVE-2026-40344 — Snowball 自动解包认证 {#cve-2026-40344}

可远程利用。在 Snowball unsigned-trailer 流程中先验证请求认证再解包 tar。使用 `PutObjectExtract` 或 Snowball 上传的用户应升级。

### CVE-2026-42600 — 内部节点 `ReadMultiple` 路径穿越 {#cve-2026-42600}

可远程利用；需 cluster-root JWT。移除允许路径穿越到盘根之外的未使用端点。分布式纠删部署应升级；单节点部署不注册此路由。

### SN-2026-002 — 内部节点载荷遏制 {#sn-2026-002}

可远程利用；需 cluster-root / 内部节点 JWT。补完 CVE-2026-42600：该修复只移除了触发缺口的一个端点；缺口本身——请求体与 grid 帧从未到达有效性中间件、存储层无遏制——仍存在于另外三个协议面。在卷与路径两轴上关闭路径穿越（包括完全绕过 storage-REST 包装的 peer-S3 桶 RPC）、一个每帧杀死节点的不可恢复除零、把截断分片报为完整的元数据，以及三个按调用方声明值定大小的分配。分布式纠删部署应升级；单节点部署不注册这些路由。S3 API 行为无变化；含 `.` 或 `..` 路径段的对象键本已在 S3 边界拒绝。

### SN-2026-003 — 策略条件值来源 {#sn-2026-003}

可利用性取决于策略。阻止原始请求条目拼写出条件键名从而遮蔽或伪造内部条件值；将 `s3:signatureAge` 限定于已验证的 SigV4 预签名请求；把仅查询串的列表字段与来自头的 `x-amz-*` 字段分离；阻止客户端请求标签冒充已存储的对象标签。兼容的查询串形式在消费它的 handler 上对存储类与上传标签仍然保留；显式出现的头优先，包括空头。请求标签条件只应用于消费标签的操作。仅头的 `x-amz-*` 策略键不再接受查询串替代。见[条件值来源与优先级](/zh/administration/identity-access-management/policy-based-access-control/#condition-value-sources)。

### 客户端源地址信任 — 主动加固，非漏洞 {#source-address-trust}

修复于 `fe6dc4780`；未分配 CVE（默认行为与上游一致，且上游立场是：没有可靠的源 IP 可见性，基于 IP 的限制不可实施）。新增可执行的转发头信任边界 `MINIO_API_TRUSTED_PROXIES`。设为地址或 CIDR 列表时，只相信来自这些 peer 的转发头，并从右向左越过已列出的跳数读取转发链——同时挡住追加型代理留下的客户端可写最左项。设为 `none` 时完全不相信任何转发头。这是 `_MINIO_API_XFF_HEADER=off` 从未提供过的保证。**对既有部署无任何行为变化**；该变量为可选，未设置时不起作用。若使用 `IpAddress`/`NotIpAddress` 条件，注意它们在此变更之前不可执行；运维契约——包括允许列表为何必须列代理而非子网、多节点部署为何必须包含自身节点地址——见[编年史文章](/zh/blog/security/source-address-trust/)与[设置参考](/zh/reference/minio-server/settings/core/#client-source-address-trust)。

### SN-2026-004 — 对象授权触达桶动作 {#sn-2026-004}

可利用性取决于策略。把十二个敏感桶级写入从对象形式资源模式（`arn:aws:s3:::bucket/*`）中扣留：`PutBucketPolicy`、`DeleteBucketPolicy`、`PutBucketObjectLockConfiguration`、`PutBucketVersioning`、`PutReplicationConfiguration`、`PutBucketLifecycle`、`DeleteBucket`、`ForceDeleteBucket`、`PutBucketCors`、`DeleteBucketCors`、`PutBucketQOS`、`PutInventoryConfiguration`。**这是授权收紧；自写桶域策略的用户升级前请读[编年史文章](/zh/blog/security/object-grant-bucket-reach/)。** 在合法授予上述动作之一的语句中，把裸桶 ARN（`arn:aws:s3:::bucket`）与通配形式并列添加。内置 canned 策略不受影响；`Deny` 语句与 `NotResource` 排除不动。`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` 可完整恢复历史行为，启动时读取一次。

### SN-2026-005 — 裸 ARN 前缀拒绝 {#sn-2026-005}

无直接远程利用；取决于策略。在创建具名策略与创建/更新服务账号会话策略时，拒绝不指向任何资源的 S3、S3 Tables 与 KMS ARN 命名空间前缀（含历史 `*arn:...` 序列化），`Resource` 与 `NotResource` 均适用。既有策略的加载、匹配、导入与复制行为不变，但含此类前缀的策略无法原样再次提交；请替换为具体资源，或在确实指全部资源时使用显式通配如 `arn:aws:s3:::*`。“裸 ARN 前缀”（`arn:aws:s3:::`）不同于 SN-2026-004 中合法的“裸桶 ARN”（`arn:aws:s3:::bucket`）。IAM 导入、站点复制接收路径、已存策略加载与 STS 内联策略在本版本仍走宽松兼容路径。见 [pkg v3.12.0 发布说明](/zh/blog/release/pkg-3.12.0/)。

### SN-2026-006 — SSE-C 零字节读取 {#sn-2026-006}

可远程利用；需对象读权限。零字节 SSE-C 对象从不解封客户提供的密钥，错误密钥会以 `200` 而非 `403` 被接受，并可在不知当前密钥的情况下以调用方选择的密钥创建副本或新版本。现在错误密钥与 AWS 一致返回 `403 AccessDenied`；正确密钥行为不变，客户端无需改动。继承自上游；更早版本均受影响。

### SN-2026-007 — SSE-C 对象的 `GetObjectAttributes` {#sn-2026-007}

可远程利用；需对象读权限。SSE-C 对象的属性在返回时未认证客户密钥，且单独一个 `X-Minio-Source-Replication-Request` 头即可完全跳过检查。现在错误密钥返回 `403`，无密钥的复制标记返回 `400`；持有 `s3:ReplicateObject` 的复制对端不受影响。继承自上游。

### SN-2026-008 — 内部复制请求头 {#sn-2026-008}

可远程利用；任何能读写该对象的已认证主体。补完 CVE-2026-34204：`X-Minio-Source-Etag`、`X-Minio-Source-Mtime`、`X-Minio-Source-Replication-Request`、复制 SSE 密钥头与对象读写上的 `X-Amz-Bucket-Replication-Status` 在多数 handler 中仍按“存在即信任”处理。现在复制语义要求精确标记值与 `s3:ReplicateObject` 或 `s3:ReplicateDelete` 同时成立；其他请求的这些头在签名验证后被移除。已持有复制权限的站点复制服务账号与桶复制目标不受影响。继承自上游。

### SN-2026-009 — 用户/组状态授权 {#sn-2026-009}

可远程利用；已认证 admin API。状态变更无论目标状态如何都按 `admin:EnableUser`/`admin:EnableGroup` 授权，只被允许 enable 的主体也能 disable，反之亦然。现在启用与禁用要求与目标状态匹配的动作。只授予二者之一的策略失去另一操作；`admin:*` 与内置 `consoleAdmin` 策略不受影响。继承自上游。

### SN-2026-010 — 显式版本删除授权 {#sn-2026-010}

可远程利用；已认证 S3 API。显式版本删除此前按 `s3:DeleteObject` 授权，仅对 `s3:DeleteObjectVersion` 做拒绝检查，与 AWS 不一致。现在显式版本删除要求 `s3:DeleteObjectVersion`。**两个策略影响：** 只被授予 `s3:DeleteObject` 的主体不能再删除特定版本；依赖 `Deny s3:DeleteObject` 阻止永久删除的策略必须同时 deny `s3:DeleteObjectVersion`，因为 `Allow s3:*` 现在允许显式版本删除。复制目标保持 `s3:ReplicateDelete` 契约。继承自上游。

### SN-2026-011 — 未签名 `x-amz-*` 头与 `x-amz-copy-source` {#sn-2026-011}

可远程利用；只持有一个预签名 PUT URL 或任意已签名 PUT 的方无需自有凭据。SigV4 验证只检查每个被命名签名头是否存在，从不检查实际到达的 `x-amz-*` 头，而路由把任何携带 `x-amz-copy-source` 的 PUT 分发给 `CopyObjectHandler`。未签名的 `x-amz-copy-source` 因此把单对象写授权变成以签名者身份执行的服务端复制，可复制签名密钥能读到的任意对象；预签名与 Authorization 头两条路径均受影响，且当目的桶允许匿名 `GetObject` 时，被复制的私有字节可被匿名读取。现在两条路径上任何未签名的 `x-amz-*` 请求头都会被以 `AccessDenied` 拒绝，与 AWS S3 对齐（AWS 返回 `403`；Silo 返回 `400 AccessDenied`，其余一致）。所有 AWS SDK、`minio-go` 与 `mc` 本就签名其 `x-amz-*` 头，合法客户端无需改动。原样继承自上游 `minio/minio`；包括最新已发布 Server 20260903 在内的更早版本均受影响。报告人 Oren Yomtov；CVE 已申请。见[编年史文章](/zh/blog/security/20260913-signed-header-status/)与[签名头设计记录](/zh/blog/design/signed-header-coverage/)。

## 依赖安全更新 {#dependencies}

各行列出吸收的修复与首个携带它的提交或发布。可达性与部署暴露面仍需按发布单独判断：吸收了依赖修复不等于该漏洞在 Silo 中可达。

| 编号 / 日期 | 修复方式 | 摘要 |
| :-- | :-- | :-- |
| 2026-03-25 发布 | [`RELEASE.2026-03-25`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-03-25) | OTel SDK、Paho MQTT 与 `x/crypto` 更新吸收 `CVE-2026-24051`、`CVE-2025-10543`、`CVE-2025-58181`；与下述 LDAP TLS 回归修复一同发布。该发布中的依赖升级并非全部为可达漏洞。 |
| `CVE-2026-34986` | [`68e0ba997`](https://github.com/pgsty/silo/commit/68e0ba997) | 升级 `go-jose` 至 `v4.1.4`。 |
| `CVE-2026-39883` | `1869bd30b`、`e4fa06394` | 更新 OpenTelemetry 依赖。 |
| Go 1.26.2 标准库 | [`db4c0fd5e`](https://github.com/pgsty/silo/commit/db4c0fd5e)（发布 lineage `9a4b3cd92`） | `CVE-2026-32280`、`CVE-2026-32281`（`crypto/x509`）、`CVE-2026-32283`（`crypto/tls`）；仅升级 toolchain/stdlib，不顺带滚动无关依赖。 |
| Go 1.26.4 刷新 | `df627ff89`、`3e61b1d3a` | `CVE-2026-32952`（Azure NTLM）、`CVE-2026-41602`（Thrift）及 NATS/Prometheus 多项安全修复，作为 06-18 发布的依赖维护层。 |
| 上游 Go 安全修复 | [Go 1.26.5](https://go.dev/doc/devel/release#go1.26.5) | 所需 toolchain 提升至 Go 1.26.5，包含 `crypto/tls` 与 `os` 的安全修复。 |
| [GO-2026-6061](https://pkg.go.dev/vuln/GO-2026-6061) / [GHSA-hrxh-6v49-42gf](https://github.com/advisories/GHSA-hrxh-6v49-42gf) | `4dfc27ce3`：gRPC `v1.82.1` 与 `x/text` `v0.39.0` | gRPC xDS RBAC 引擎与 HTTP/2 传输修复（[GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852`，`x/text` 对非法输入的死循环，同一刷新落地）。保留既有 MVS 钉定；未借安全升级滚动无关依赖。 |
| [GO-2026-5841](https://pkg.go.dev/vuln/GO-2026-5841) | `f1357853d`：`klauspost/compress` `v1.18.7` | `govulncheck` 判定受影响字典符号不可达，但已知受影响的直接依赖仍不应继续携带；升级到首个修复版本。 |
| 工具链与依赖刷新 | [Go 1.27.1](https://go.dev/doc/devel/release#go1.27.1) 经 [`43f4bb7ed`](https://github.com/pgsty/silo/commit/43f4bb7ed)、[`edc8be6ed`](https://github.com/pgsty/silo/commit/edc8be6ed)、[`4d6e1ea8e`](https://github.com/pgsty/silo/commit/4d6e1ea8e) | 工具链迁移到 Go 1.27（发布时为 1.27.1）并刷新依赖栈（etcd client v3.7.1、`jwx` v3.0.13、`klauspost/compress` v1.19.2）。发布前清理回归上游 `minio-go`（v7.3.1 预发布）并退役 `silo-go` fork；`govulncheck` 在候选版本上无可达漏洞。 |
| [GO-2026-6354](https://pkg.go.dev/vuln/GO-2026-6354) / [GO-2026-6355](https://pkg.go.dev/vuln/GO-2026-6355) | `golang.org/x/crypto` `v0.56.0`（[`edf36bcbf`](https://github.com/pgsty/silo/commit/edf36bcbf)） | 更新 `x/crypto/ssh` 至首个修复版本，修复死锁 undecided/established channel 的拒绝服务。经 SFTP 服务器可达（`startSFTPServer` → `sftp.Server.Listen` → `ssh.NewServerConn`）；启用 SFTP 的更早版本均受影响。 |
| [CVE-2026-84304](https://github.com/advisories/GHSA-vp52-pcj8-j9qc) | gRPC `v1.83.1` | 更新 gRPC-Go 至首个修复版本，修复高度碎片化 HTTP/2 DATA 帧导致的未认证堆耗尽。Silo 以传递方式引入 gRPC 而非自身注册 gRPC 服务器，但仍为完整模块图选择修复版本。 |
| [GO-2026-5970](https://pkg.go.dev/vuln/GO-2026-5970) / `CVE-2026-56852` | `x/text` `v0.39.0` | 更新 `x/text` 至首个修复版本，修复非法输入上的无限循环。 |

## 运维相关的安全修复 {#operational}

| 变更 | 修复状态 | 摘要 |
| :-- | :-- | :-- |
| 复制 Object Lock 更新忽略时间戳 | [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9)，已包含在 [Server 20260903](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) 中 | 复制 `CopyObject` 在比较复制时间戳之前先从请求重建元数据，导致存储的保留与 legal-hold 时间戳从未被看到：任何副本更新无论先后都被应用，legal-hold 时间戳被写在保留键下。过期副本因此可以关掉更新的 legal hold 或缩短更新的保留。现在先捕获存储状态，仅当副本时间戳更新时应用，过期更新不影响存储状态，且各时间戳保存在各自键下。继承自上游；修复前的构建受影响。 |
| LDAP TLS 回归 | [`ce1c537eb`](https://github.com/pgsty/silo/commit/ce1c537eb1dd6c4efa1cf75cf5df0e2c489c947a)，随 `RELEASE.2026-03-25` 发布 | 恢复 `ldaps://` `DialURL()` 连接的 TLS 配置传递，使 `MINIO_IDENTITY_LDAP_TLS_SKIP_VERIFY` 与自定义根 CA 重新生效。 |

## 台账归属 {#attribution}

本页由仓库内原 `docs/security/advisories.md` 台账维护而来，更新至已核验的 main
`40220bd836cb`（2026-09-16）。发布状态表述与[组件版本矩阵](/zh/compatibility/versions/)对齐；每个修复的调查、评审与验证细节见链接的编年史文章或发布说明。
