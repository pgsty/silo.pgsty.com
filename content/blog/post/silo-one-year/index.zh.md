---
title: "SILO 一年回顾：相比上游 MinIO，我们到底干了什么？"
linkTitle: "SILO 一年回顾"
date: 2026-10-26
lastmod: 2026-10-27
author: 冯若航
description: "从 MinIO 最后公开发布的 2025-10-15 到 SILO 20261026：376 天、604 次提交、7 个 CVE 与 18 项安全边界加固、S3 协议与校验和补齐、复制与多池存储修复，以及完整管理控制台与客户端工具链的工程账本。"
summary: >
  从 MinIO 最后公开发布的 2025-10-15 到 SILO 20261026：376 天、604 次提交。本文用一张完整的工程账本说清楚：过去一年里，SILO 在安全边界、S3 协议与校验和、复制与生命周期、存储写入与多池保护、Console 与 mcli 以及运维交付上到底干了什么，又有哪些边界仍未改变。
tags: [post, minio, silo]
weight: 5
url: "/zh/blog/post/silo-one-year/"
---

2025 年 10 月 15 日，MinIO 发布了最后一个公开开源版本 [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)（提交 `9e49d5e7a648`）。随后两个月里，上游先宣布进入“维护模式”，接着删除了 `minio/console` 仓库，最终在 2026 年 2 月将主仓库彻底归档，把所有后续 CVE 修复与维护留在商业版 AIStor 中。

到 2026 年 10 月 26 日，SILO 打下 [`RELEASE.2026-10-26T00-00-00Z`](https://github.com/pgsty/silo/commit/c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3) 标签（提交 `c3ad836aed0d`）。整整一年（376 天），服务端主仓库合入了 **604 次提交**，连同配套的 `silo-console`、`mcli` 与 `silo-pkg` 一起，走完了一轮完整的工程演进。

很多用户问过同一个问题：**从 MinIO 分叉出来的这一年，SILO 到底只是换了个名字打安全补丁，还是真的在修底层问题？跟上游最后那个版本相比，实质差异到底在哪？**

先把核心结论摊在桌面上：**SILO 没有改动 MinIO 的纠删码存储引擎、`xl.meta` 磁盘格式与基本读写仲裁规则；这一年的全部工程火力，都花在安全边界、S3 协议与校验和正确性、复制与生命周期收敛、失败写入与多池保护，以及恢复完整的管理控制台与客户端体验上。**

| 领域 | 最重要的实质变化（`2025-10-15` → `2026-10-26`） |
| --- | --- |
| **安全与授权边界** | 修复分叉后披露的 **7 个 CVE**（OIDC 算法混淆、LDAP STS 枚举爆破、复制头注入、S3 Select 内存耗尽、无符号 Trailer 漏验签、Snowball 越权解压、`/rmpl` 路径穿越），并完成 **18 项 `SN-2026-*` 安全边界加固**（SigV4 操作头强制签名、策略条件键防伪造、桶级写权限收紧、服务账户授权上限、Object Lock 绕过校验、IAM 持久化撤销与防旧事件复活） |
| **S3 协议与校验和** | 将上游返回 `NotImplemented` 的桶级 CORS 补齐为完整持久化与预检实现；支持条件 `DELETE`（`If-Match`）与跨池条件 `PUT`/`CompleteMultipartUpload`；补齐分段上传、`CopyObject`、SSE-C 与压缩对象的明文逻辑校验和及分片逻辑大小；将加密元数据篡改错误从 HTTP `206` 修正为 `500` |
| **复制与生命周期** | 修复分片上传复制丢失 `FULL_OBJECT` 校验和类型（`#255`）；支持可信对端 SSE-C 原始密文与封套复制；为对象标签与 Object Lock 保留期引入修改时间戳以保证乱序与删除收敛；版本桶生命周期过期仅写入删除标记时保留远端分层数据（`#253`） |
| **存储正确性与多池** | 实现两阶段多池批量删除（`#257`）、迁移版本保护与盘间分歧下的 `LIST` 恢复（`#239`），转发覆盖回滚所需的存储 RPC 删除选项；保留既有超时与取消语义，迟到提交、延迟回滚和陈旧读取仍是故障边界 |
| **Console 与 mcli** | 恢复并重写完整管理控制台 **SILO Console v2.5.1**（`<3 MB` 零遥测前端、中英双语、游标分页、任务中心、Metrics V3、高延迟诊断流修复）；发布 **mcli 20261026**，新增只读 `checksum verify`，修正 `admin info --json`、`mirror`、`mv`、`retention`、`legalhold`、`sql` 的错误退出码与重启行为 |
| **参数、运维与分发** | 让 `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` 真正生效（默认 30 秒绝对请求头期限）；新增可信代理配置（`MINIO_API_TRUSTED_PROXIES`）与原生 `silo healthcheck` 子命令；彻底移除原地自更新与 `SUBNET`/call-home；构建 Go 1.27.3、UBI 9.8 / distroless 镜像、RPM/DEB/APK、Windows ZIP 归档及 GPG/SBOM/Sigstore 完整供应链 |
{.wide .expand}

同时，有一说一，下面这些边界我们同样在文档与发布验收里写得明明白白：

1. **没有引入分布式 fencing，也不能宣称解决了全部一致性问题。** 租约过期或网络分区下的迟到写入仍可能发生；严格代际拒读、自动跨池读恢复、公开持久分段上传枚举（`#79`）、访问频率池间分层与多池覆盖亲和（`#245`）在实测暴露容量或可用性代价后均已撤回或延期。
2. **没有跑过两个固定版本的全集群对等性能基准。** 我们有局部热路径的微基准与摊销开销实测，但绝不凭空编造“整体吞吐提升 X%”的数字。
3. **磁盘格式兼容不等于支持任意混跑或无脑降级。** 新的 IAM 持久化撤销状态（`siloParentRevocation`）与复制墓碑需要参与节点协调升级。

下面按模块逐一拆解这一年里 SILO 具体改了什么、为什么这么改，以及每项改动背后的代码证据与使用边界。

---

## 1. 基线与产品栈：什么变了，什么没变 {#baseline-and-stack}

本次对比的精确基线是上游 MinIO 最后一次公开发布与 SILO 2026 年 10 月统一维护批次：

- **上游基线**：`minio/minio` [`RELEASE.2025-10-15T17-29-55Z`](https://github.com/minio/minio/releases/tag/RELEASE.2025-10-15T17-29-55Z)（提交 `9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a`，2025-10-15）。注：上游在停发 Release 到 2026-02-02 归档前还合入过 9 个未发版提交（如 `fa18589d1c` 的 POST Policy 标签约束、`18f97e70b1` 的条件写读仲裁调整），这些提交不在 `2025-10-15` 正式版内，SILO 也通过独立路径完成了对应修复。
- **SILO 目标版本**：`pgsty/silo` [`RELEASE.2026-10-26T00-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-10-26T00-00-00Z)（源码 `c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3`），与 mcli / KES 20261026、Console v2.5.1、silo-pkg v3.15.2 联合发布。详见[本批次发布日志](/zh/blog/release/silo-20261026/)与[组件矩阵](/zh/compatibility/versions/)。

在 `9e49d5e7a648..c3ad836aed0d` 区间内，`pgsty/silo` 共有 **604 个可达提交**（涵盖功能与安全修复、回归测试、构建打包与文档工程）。下文按实际交付的运行时行为逐一归纳。

### 四组件协调维护栈

上游归档后，单靠一个服务端仓库无法交付完整的对象存储系统——因为服务端内嵌了 Console 前端与 `mc` 管理模块，又直接依赖共享策略与加密库。SILO 将维护范围收敛为四个协同演进的核心仓库（加可选外部密钥服务 KES）：

| 组件 | 上游 `2025-10-15` 状态 | SILO `20261026` 状态 | 关键演进说明 |
| --- | --- | --- | --- |
| **Server (`pgsty/silo`)** | Go 1.24.0，`minio` 二进制 | **Go 1.27.3**，`silo` 二进制（[`c3ad836aed0d`](https://github.com/pgsty/silo/commit/c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3)） | 模块路径保留 `github.com/minio/minio`；修复 7 个 CVE + 18 项安全边界加固与多项存储/复制缺陷 |
| **Console (`pgsty/silo-console`)** | 内嵌裁剪版 `v1.7.7`（仅剩对象浏览器） | **[v2.5.1](https://github.com/pgsty/silo-console/releases/tag/v2.5.1)**（[`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed)） | 上游已删除 `minio/console` 仓库；SILO 恢复完整管理台，重构为 `<3 MB` 零遥测双语前端 |
| **Client (`pgsty/mc`)** | `mc` `cf909e1063a9` | **[mcli 20261026](https://github.com/pgsty/mc/releases/tag/RELEASE.2026-10-26T00-00-00Z)**（[`0ceb298cdcd0`](https://github.com/pgsty/mc/commit/0ceb298cdcd05f2ffdc4ea62d7d01a3666c3e8cc)） | 产物命名为 `mcli`（避免与 Midnight Commander `mc` 冲突），新增 `checksum verify` 并修复退出码 |
| **Shared Pkg (`pgsty/silo-pkg`)** | `minio/pkg/v3 v3.1.3` | **[v3.15.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2)**（[`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0)） | 独立模块路径 `github.com/pgsty/silo-pkg/v3`，承载 IAM 策略判定、条件键隔离、证书与 KMS 客户端 |
| **S3 SDK (`minio/minio-go/v7`)** | `v7.0.91` | **`v7.4.2-0.20261025165926-320af050c445`** | 唯一直接沿用上游的模块，固定在经验证的提交（含分片截短流、负偏移与批量删除修复） |
| **KMS (`pgsty/kes`)** | 外部可选依赖 | **[KES 20261026](/zh/blog/release/silo-20261026/#kes)**（[`e9b4f1acebc1`](https://github.com/pgsty/kes/commit/e9b4f1acebc11d61b42f876da8df48f548750cc9)） | Go 1.27.3，验证 OpenBao KV v2 与本地 Moto Secrets Manager 协议；更新 AWS/GCP 客户端 |
{.wide .expand}

### 刻意保持不变的底层基石

为了确保现有 MinIO 部署能够原地替换为 `pgsty/silo` 而不触发数据重算或客户端改造，以下核心架构与协议层保持不变：

- **纠删码与 Bitrot 保护**：底层仍采用 Reed-Solomon 纠删码与 HighwayHash256 分块校验。
- **基本读写仲裁规则**：读仲裁仍为数据分片数 $K$；写仲裁在数据分片与校验分片不等时为 $K$，相等（如 8+8）时为 $K+1$（例如 16 盘 12+4 配置下读写仲裁均为 12，8+8 配置下读仲裁为 8、写仲裁为 9）。
- **磁盘格式与系统命名空间**：`xl.meta` 格式版本保持 `1.3`，系统元数据目录仍为 `.minio.sys`，已有数据盘无需格式转换即可直接挂载。
- **线上协议与配置兼容**：完整保留 `MINIO_*`、`MC_*`、`CONSOLE_*` 环境变量、`/minio/health/*` 健康探针、`/minio/v2/metrics/*` 与 `/minio/metrics/v3` 监控路径，以及 `X-Minio-*` 头部兼容（详情见[兼容性总览](/zh/compatibility/)与[迁移指南](/zh/compatibility/migration/)）。

---

## 2. 安全、认证与授权：7 个 CVE 与 18 项安全边界加固 {#security}

接手维护的第一道硬仗是安全漏洞。由于 SILO 保留了 `github.com/minio/minio` 模块路径，而上游发布 GHSA/CVE 时往往将受影响版本写成开放区间，许多安全扫描器会把所有历史漏洞一股脑报在 SILO 头上。

我们先把账算清楚：诸如 `CVE-2025-62506`（服务账户绕过）、`CVE-2025-31489`、`CVE-2025-27414` 在上游 `2025-10-15` 基线中**已经修复**；而以下 **7 个 CVE** 是在 `2025-10-15` 之后才披露、上游拒绝为开源版提供补丁、由 SILO 独立修复并验证的真实漏洞：

| CVE / 公告 | 严重度 | 漏洞本质与攻击后果 | SILO 修复方案与源码证据 |
| --- | --- | --- | --- |
| **[CVE-2026-33322](/zh/blog/security/cve-2026-33322/)** | Critical (9.8) | OIDC JWT 算法混淆：当 JWT 头部声明 `HS256` 等对称算法时，上游将 OIDC `ClientSecret` 当作 HMAC 密钥验签，知道 `ClientSecret` 的攻击者可伪造任意身份（含 `consoleAdmin`） | 严格限定 JWKS 非对称公钥验签，彻底拒绝 HMAC 对称算法（`cmd/jwt.go`、`internal/config/identity/openid/`） |
| **[CVE-2026-33419](/zh/blog/security/cve-2026-33419/)** | High | LDAP STS 接口可枚举有效用户名，且无登录速率限制，可被直接爆破换取 STS 凭据 | 统一绑定失败的认证错误响应，并按“可信源 IP + 归一化用户名”双维度施加滑动窗口限流，成功登录不消耗配额（`cmd/sts-handlers.go`） |
| **[CVE-2026-34204](/zh/blog/security/cve-2026-34204/)** | High | 普通客户端在 `PUT`/`COPY` 请求中夹带未授权的 `X-Minio-Replication-*` 头，可污染加密元数据导致对象永久不可读 | 在请求入口剥离未获复制授权的内部复制头与 SSE 复制元数据（`cmd/auth-handler.go`、`cmd/object-handlers-common.go`） |
| **[CVE-2026-39414](/zh/blog/security/cve-2026-39414/)** | High | S3 Select 处理无换行符的超大 CSV 或 JSON Lines 流时无界累积单条记录，单请求即可打穿进程内存（OOM） | 为 CSV 与 JSON 解析器设置严格的单记录最大字节上限，超限立即终止流并返回规范错误（`internal/s3select/`） |
| **[CVE-2026-41145](/zh/blog/security/cve-2026-41145/)** | High | `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 流式写入路径在特定处理分支漏掉签名校验，允许未授权或伪造签名请求写入对象 | 在所有 `aws-chunked` 与 unsigned-trailer 入口强制执行完整的请求认证与权限检查（`cmd/auth-handler.go`） |
| **[CVE-2026-40344](/zh/blog/security/cve-2026-40344/)** | High | Snowball 归档批量解压上传接口存在入口认证缺失与归档内部条目越权写入 | 强制校验入口身份，并对归档内展开的每一个目标对象键逐一执行目标路径与桶策略鉴权（`cmd/bucket-handlers.go`、`cmd/object-handlers.go`） |
| **[CVE-2026-42600](/zh/blog/security/cve-2026-42600/)** | High | 节点间内部存储接口 `/rmpl`（`ReadMultiple`）缺少磁盘根目录路径边界约束，存在路径穿越读取风险 | 直接从内部存储 REST 路由与协议中移除未使用的 `ReadMultiple` 接口，并对全部保留的内部磁盘 RPC 实施严格的盘内路径校验（`cmd/storage-rest-server.go`） |
{.wide .expand}

### 18 项 `SN-2026-*` 安全边界加固

除了公开披露的 CVE，我们在对抗性代码审查与真实多节点验收中，还系统性地挖掘并修复了 **18 项安全边界缺陷**（完整索引见[安全公告总表](/zh/about/security-advisories/)）：

1. **SigV4 签名头完整性与策略条件键隔离（[SN-2026-011](/zh/blog/security/20260913-signed-header-status/)、[SN-2026-003](/zh/blog/security/s3-versionid-conditions/)）**：
   - 上游允许攻击者在已签名的 SigV4 请求外附加未签名的 `X-Amz-*` 业务头（如篡改保留期绕过、对象标签或校验和）。SILO 强制要求请求中出现的全部 `X-Amz-*` 业务头必须包含在 `SignedHeaders` 中。
   - 上游在构造 IAM 策略评估参数时，会把客户端请求头和查询参数混入条件字典，导致客户端能伪造 `s3:prefix`、`s3:versionid`、`s3:ExistingObjectTag/*` 或 `aws:PrincipalType` 等服务端权威条件键。SILO 在 `silo-pkg` 中将服务端权威条件键与客户端输入彻底隔离，并在 `DeleteObjects` 与 `GetObject` 中将 `s3:VersionId` 严格绑定到实际操作的目标版本。
2. **桶级写权限收紧、指定版本删除授权与管理动作拆分（[SN-2026-004](/zh/blog/security/object-grant-bucket-reach/)、[SN-2026-005](/zh/blog/security/s3-versionid-conditions/#sn-2026-005)、[SN-2026-009 与 010](/zh/blog/security/20260903-server-hardening/)、[SN-2026-017](/zh/blog/design/iam-admin-authorization/)）**：
   - 收紧 12 项桶级写操作（如 `s3:CreateBucket`、`s3:DeleteBucket`、`s3:PutBucketPolicy`、`s3:PutLifecycleConfiguration` 等）的资源匹配规则，拒绝仅授予 `arn:aws:s3:::bucket/*`（对象通配符）或裸 `arn:aws:s3:::` 的策略越权修改桶级配置。
   - 显式指定版本 ID（包括 `null`）进行永久删除时，要求 `s3:DeleteObjectVersion`；不指定版本、只创建删除标记时仍使用 `s3:DeleteObject`，批量删除逐项检查。
   - 将启停用户的权限从 `admin:CreateUser` 中拆出为独立的 `admin:EnableUser` / `admin:DisableUser`；将用户自改密码拆分为独立的 `admin:ChangeMyPassword`（详见[密码权限迁移](/zh/compatibility/password-permissions/)）；修复 IAM 管理接口创建、查看、列举访问密钥时的父账户归属校验。
3. **服务账户授权上限与 Object Lock 治理绕过校验（[SN-2026-015 与 016](/zh/blog/security/20260926-governance-retention-bypass/)）**：
   - 修复内联会话策略（session policy）在没有同名 `Allow` 语句时丢失父身份 `Deny` 规则的漏洞，并在临时 STS 凭据与服务账户每次鉴权时实时复核父账户当前权限上限。
   - 修复 `PutObject` 覆盖受 `GOVERNANCE` 模式保护的对象时未要求 `x-amz-bypass-governance-retention: true` 请求头的漏洞；在 `PutObjectRetention` 放行治理模式绕过前先完成 XML 请求体合法性校验。
4. **IAM 持久化撤销、策略重载锁隔离与 LDAP 长 DN（[SN-2026-013](/zh/blog/security/20260916-release-hardening/#sn-2026-013)）**：
   - 在多节点与多站点复制下，过去删除用户、策略或服务账户后，迟到的站点复制事件或漏掉的对端通知会让已删除的身份和旧权限“死而复生”。SILO 引入持久化修订号、删除墓碑与父身份撤销截止线（`siloParentRevocation`），并在收到对端删除通知时强制重载已提交的持久状态，彻底封堵旧事件重放恢复权限的路径。
   - 将慢速的 IAM 策略加载与 KMS 解密移出全局内存鉴权缓存锁，贯通 KMS 请求取消信号（[设计记录](/zh/blog/design/iam-policy-cancellation/)）；修复 LDAP `StartTLS` 优先级与超长 DN 转义导致的 255 字节文件名越界问题（[设计记录](/zh/blog/design/ldap-long-dn/)）。

---

## 3. S3 协议补齐与端到端校验和 {#s3-and-checksums}

在 S3 协议层，SILO 这一年重点解决了三件事：**把上游留下的空壳 API 补齐、把多池条件读写语义拉齐、把分片与加密场景下的校验和及逻辑大小算准。**

| 特性 / 场景 | 上游 MinIO (`2025-10-15`) | SILO (`20261026`) | 相关设计记录 |
| --- | --- | --- | --- |
| **桶级 CORS 配置** | `GetBucketCors`/`PutBucketCors`/`DeleteBucketCors` 直接返回 `NotImplemented` | 完整实现桶级 CORS XML 持久化（最多 100 条规则、64 KiB）、`OPTIONS` 预检匹配、跨站复制与桶元数据导入导出 | [按桶配置 CORS](/zh/blog/release/silo-20260903/#cors-trust) |
| **条件 `DELETE`** | 不支持 `If-Match` 条件删除 | 单对象 `DELETE` 支持 `If-Match: "<etag>"` 与 `If-Match: *`，在共享对象锁内校验；批量 `DeleteObjects` 尚不支持逐项 ETag 条件 | [条件删除设计](/zh/blog/design/conditional-delete/) |
| **多池条件 `PUT` 与分片完成** | 只检查目标写入池，可能被旧池的过期 ETag 误放行或误拒绝 | 跨所有存储池（含正在退役/排空的池）解析逻辑当前对象后再校验 `If-Match` / `If-None-Match` | [多池对象一致性](/zh/blog/design/multi-pool-object-consistency/) |
| **服务端分片校验和** | 已声明校验和算法的分片上传在分片请求省略校验和头时失败，复制分片也受影响 | 按上传初始化时声明的算法，在压缩或加密前计算明文分片校验和，并持久化到 `xl.meta`；未声明算法的上传不会因此默认启用 `CRC32C` | [分片校验和](/zh/blog/design/uploadpart-checksum/) |
| **`CompleteMultipartUpload` 校验** | 对重复 part 号、缺失校验和或 `FULL_OBJECT` 类型匹配检查不严 | 严格要求 part 号单调递增（重复返回 `InvalidPartOrder`），严格校验分片校验和与 `FULL_OBJECT`/`COMPOSITE` 汇总值 | [校验和完整性修复](/zh/blog/design/complete-multipart-checksum-errors/) |
| **`CopyObject` / `UploadPartCopy` 校验和** | 服务端复制加密或压缩对象时可能直接拷贝底层密文 bitrot 哈希，且响应漏返 `ChecksumType` | 统一按明文逻辑字节重算或验证校验和，并在 `CopyObjectResult` / `CopyPartResult` 中返回准确的 `ChecksumType` | [校验和完整性修复](/zh/blog/design/copyobject-ssec-checksum-response/) |
| **SSE-C 同对象密钥轮换与零字节** | 用新 SSE-C 密钥原地 `CopyObject` 只改元数据不重加密数据，导致对象损坏；零字节 SSE-C 对象与分片属性未解封校验 | 同对象换钥时强制重写底层密文；零字节 SSE-C 对象及 `GetObjectAttributes` 分片列表均执行完整密钥解封验证 | [SSE-C 密钥轮换](/zh/blog/release/silo-20260903/#copyobject-ssec)、[零字节验证](/zh/blog/security/20260903-server-hardening/#sn-2026-006) |
| **加密/压缩分片逻辑大小** | `GetObjectAttributes` 与 `?partNumber=N` 可能返回含加密/压缩开销的物理分片大小 | 解密/解压路径与元数据属性统一返回真实的明文逻辑分片大小 | [分片逻辑大小](/zh/blog/release/silo-20260916/#encryption) |
| **加密元数据篡改状态码** | `ObjectTampered` 被映射为 HTTP `206 Partial Content` | 修正为 HTTP `500` (`XMinioObjectTampered`)，避免客户端把损坏对象当成正常部分响应缓存或续传 | [ObjectTampered 500](/zh/blog/release/silo-20260916/#encryption) |
| **DNS 联邦 `CopyObject`** | 跨集群联邦复制可能直接流式传输 `.minio.sys` 底层密文导致目标对象无法解密 | 改为通过标准 S3 客户端流式读取明文并在目标端重新封存 | [联邦 CopyObject](/zh/blog/design/federated-copy-object/) |
{.wide .expand}

---

## 4. 跨站复制与生命周期 {#replication-and-lifecycle}

在开启了跨站复制（Bucket / Site Replication）或远端分层（ILM Tiering）的生产集群中，最危险的缺陷往往不是“请求直接报错”，而是**源端与备端静默不一致**，或者**生命周期规则误删了仍在引用的底层数据**。过去一年里，SILO 围绕复制与生命周期修复了六类核心问题：

| 问题领域 | 上游旧行为与风险 | SILO 修复后的行为 |
| --- | --- | --- |
| **分片对象 `FULL_OBJECT` 校验和复制（`#255`）** | 源端分片上传使用 `CRC32`/`CRC32C` `FULL_OBJECT` 校验和时，复制发起端调用 `NewMultipartUpload` 漏传 `x-amz-checksum-type: FULL_OBJECT`，导致目标端按 `COMPOSITE` 校验并在 `CompleteMultipartUpload` 时以 `BadDigest` 失败 | 在 `putReplicationOpts` 中显式携带 `ChecksumType`，使分片复制与 `CopyObject` 共享完整的 `FULL_OBJECT` 校验和头（[设计记录](/zh/blog/design/replication-full-object-checksum/)） |
| **SSE-C 加密对象复制** | 复制 SSE-C 对象时重新生成随机 KMS/DARE 封套或破坏原始客户密钥封存，导致备端副本无法用原 SSE-C 密钥读取 | 在受信任的复制通道上原样保留 SSE-C 原始密文、随机 IV 与加密封套元数据（[设计记录](/zh/blog/design/ssec-replica-integrity/)） |
| **对象标签删除与乱序复制** | 删除对象标签时旧版本只传空字符串而不推进修订时间，迟到的旧复制事件会把已删除的标签重新写回；SSE-KMS 复制还会丢失标签修订时间 | 引入 `replication-tag-modtime` 时间戳与删除墓碑，SSE-KMS 复制保留标签修订时间，乱序到达的旧标签事件自动被高水位时间戳拦截（[设计记录](/zh/blog/design/replicated-tag-ordering/)） |
| **Object Lock 保留期复制排序** | 跨站并发更新同一对象版本的 Object Lock 保留期时，缺乏统一顺序判定，旧保留期可能覆盖新保留期 | 引入 `replication-retention-modtime` 时间戳并在持久化锁保护下按时间戳收敛（[设计记录](/zh/blog/design/object-lock-replication-ordering/)） |
| **删除标记复制与版本清除（Purge）** | 指定版本永久删除（Purge）在缺盘时可能反而在盘上新建删除标记；MRF 重试队列可能混淆“新建删除标记”与“永久清除版本” | 严格区分删除标记创建与指定版本清除，排队的创建任务在发送前先在复制锁内复核源端状态，缺版本清除需写仲裁多数确认（[设计记录](/zh/blog/design/replication-reliability/)） |
| **版本桶生命周期过期与远端分层（`#253`）** | 启用版本控制（或暂停版本控制但含非 `null` 历史版本）的桶触发 `Expiration` 规则时，若操作仅仅是追加一个删除标记，旧逻辑仍可能连带删除已分层到远端存储的底层数据，导致历史版本永久无法读回 | 明确区分“仅创建删除标记的当前版本过期”与“真正销毁历史版本的过期动作”；前者完整保留远端分层数据，只有真正清除对应版本时才回收远端对象 |
{.wide .expand}

此外，在复制重同步（Resync）与站点桶配置同步上，SILO 为每个 Resync 任务与目标端拆分了独立的取消上下文并修正了 `ReplicatedCount`/`FailedCount` 统计（[复制重同步正确性](/zh/blog/design/replication-reliability/#resync)），同时为桶级元数据（CORS、生命周期、加密、复制、锁配置）重载加装了逐桶互斥锁与可选的字段级删除墓碑（[桶配置收敛](/zh/blog/design/bucket-metadata-convergence/)）。

---

## 5. 存储写入、回滚与多池一致性 {#storage-and-multipool}

在纠删码存储引擎中，正常路径很容易写对，真正的坑全在**慢盘、部分写失败回滚、并发覆盖写与多存储池（Multi-Pool）扩缩容**的交叉地带。20261026 正式版收敛并交付了以下三组底层存储保护：

### 1. 存储提交错误分类与覆盖回滚 RPC 透传

- **暂存 `xl.meta` 缺失归类为 `503 SlowDownWrite`**：在提交阶段，若个别慢盘因并发清理或时序竞争导致 `.minio.sys/tmp` 中的暂存 `xl.meta` 缺失，SILO 将其归类为 `errFileNotFound` 并向客户端返回 HTTP `503 SlowDownWrite` 触发安全重试，而不是像过去那样误报 `404 ObjectNotFound`（[错误分类设计记录](/zh/blog/design/stale-metadata-reuse/)）。
- **覆盖写回滚选项透传与超时边界**：转发存储 RPC 的删除选项（包括覆盖写回滚所需的旧数据目录），同时保持既有的磁盘/RPC 超时、请求取消、对象锁、读仲裁与自愈规则。需要明确的是：**客户端收到请求超时并不代表底层磁盘或 RPC I/O 已经停止，也不代表写入一定未提交**——在部分磁盘故障、租约丢失或网络分区下，迟到提交或延迟 `UndoWrite` 仍可能发生（10 月维护候选中曾尝试的已接纳 I/O 排空等待与逐盘变更锁已在 [`dcc2f20ba`](https://github.com/pgsty/silo/commit/dcc2f20ba81c51a11dab047bb65c86e0dc6a6038) 中撤回，详见[最终维护边界](/zh/blog/design/multi-pool-object-consistency/#maintenance-20261026)）。

### 2. 多池并发锁、两阶段批量删除与跨池迁移保护

在多存储池（Multi-Pool）集群中：

- **跨池共享对象锁**：修复了多池集群中不同存储池各自维护局部锁导致并发写入、删除与元数据更新互不感知的问题。
- **多池批量删除保住最新副本（`#257`）**：过去多池 `DeleteObjects` 对所有存储池并行下发删除，一旦保存最新版本的池删除成功、而保存旧副本的池因磁盘故障删除失败，旧池里的过期数据就会“复活”成当前可见对象。SILO 将多池删除改为两阶段执行：先定位每个对象的权威版本所在池，优先清理非权威池中的旧副本，待旧副本清理确认后再删除权威池副本，并在部分失败时保护仍被引用的远端分层对象（[多池删除设计记录](/zh/blog/design/multi-pool-delete-safety/)）。
- **Rebalance 与 Decommission 迁移保护**：修复了跨池再平衡（Rebalance）与池退役（Decommission）过程中丢失对象标签、覆盖目标池更新版本或漏处理删除标记的问题（[多池对象一致性](/zh/blog/design/multi-pool-object-consistency/#migration-20261018)）。

### 3. 盘间分歧下的 `LIST` 恢复（`#239`）

在滚动重启叠加并发覆盖写时，部分磁盘排在前面的少数派新状态或未决条目可能导致 `ListObjects` 漏掉实际上可读的对象。SILO 在保持无锁快路径的前提下，对盘间出现分歧的候选条目执行按需确认，严格区分“对象已删除”与“磁盘读取故障”，并将终端错误正确传递到分页响应中（[LIST 恢复设计记录](/zh/blog/design/listing-recovery-lock-cost/)）。

---

## 6. 完整管理面回归：SILO Console v2.5.1 与 mcli 20261026 {#console-and-mcli}

对日常运维人员来说，SILO 与上游 MinIO 最直观的差异体现在管理控制台（Console）和命令行客户端（`mcli`）上。

### SILO Console v2.5.1：从被阉割的浏览器回到完整管理台

2025 年中，上游将社区版 MinIO 内嵌的 Console 裁剪到了 `v1.7.7`，砍掉了所有集群管理、IAM、策略、生命周期、复制、诊断与监控界面，只留下一层简陋的对象浏览器；随后更是直接删除了 `github.com/minio/console` 仓库。

SILO 在社区开发者 Georg Mangold（`@gmangold`）恢复的历史分支基础上，从 `v2.0.0` 持续迭代至 `v2.5.1`，交出了一份不仅恢复全功能、而且比原版更轻量可靠的管理控制台：

| 维度 | 上游 `2025-10-15` 内嵌 Console (`v1.7.7`) | SILO Console `v2.5.1` |
| --- | --- | --- |
| **管理功能范围** | 仅剩基础桶与对象浏览，移除全部管理面板 | **完整管理面**：Overview 概览、存储桶、对象浏览器、生命周期、跨站复制、分层存储、事件通知、IAM（用户/组/服务账号/策略及内置策略 Reset）、IDP（OIDC/LDAP）、KMS、集群诊断（Health/Trace/Logs/Watch/Speedtest/Profile）与后台任务中心（Tasks） |
| **前端体积与遥测** | 约 10 MB，含外部字体/脚本与运营服务调用 | **`< 3 MB`**，逐字节可复现构建，零遥测、零外部网络依赖，响应式明暗主题 |
| **多语言支持** | 仅英文 | **原生中英双语切换**（含界面、错误提示与文档跳转） |
| **监控指标体系** | 旧版接口或缺失 | 原生对接 **Metrics V3**，区分“真实零值”与“节点未上报数据” |
| **大桶浏览与文件预览** | 易在大目录下全量拉取卡死 | **游标分页**（默认 100 项，最高 1,000 项）、1 MiB 有界文本/Markdown/CSV/代码预览、原生流式 ZIP 批量下载 |
| **高延迟网络诊断（`#63`）** | 跨地域或高延迟链路下下载健康报告易触发 WebSocket `1006` / `1011` 截断 | 修复六类诊断流的 WebSocket 关闭握手与 `madmin v3` 帧解码器预读吞字节缺陷，双向叠加 250 ms 延迟仍稳定输出完整健康报告 |
{.wide .expand}

Console 2.5.1 进一步修复切换组状态时丢失成员、OIDC 组权限、TLS 代理会话 Cookie、凭据导出及键盘焦点问题，完整变化见 [Console 2.5 系列发布说明](/zh/blog/release/console-2.5.1/)。

### mcli 20261026：说真话的退出码与只读校验和核验

在客户端侧，`pgsty/mc` 以 `mcli` 作为二进制与包名称发布（同时保留 `MC_*` 环境变量与配置格式兼容），重点解决了自动化脚本最头疼的“表面成功、实际失败”问题：

- **新增只读 `mcli checksum verify` 命令**：无需下载落盘或修改对象，直接对存储桶、前缀或指定对象版本执行端到端 `FULL_OBJECT` 校验和核验，支持 `--versions`、`--Algo` 与 `--json` 输出。
- **修复一系列静默返回 `0` 的错误退出码**：
  - `mcli admin info --json` 在权限被拒绝或节点报错时输出 `status: error` 的同时返回**非零退出码**（上游仍以 `0` 退出）；
  - `mcli mirror`、`mcli mv`、`mcli retention`、`mcli legalhold`、`mcli sql` 在遇到部分对象失败、源删除失败或权限拒绝时，均确保返回非零退出码；
  - 下载流中途断开时直接报错返回，绝不把截短文件当作成功下载。
- **安全的 `mirror` 删除传播与服务重启预演**：修复 `mirror --remove` 在源端列举异常时的误删风险；为 `mcli admin service restart` 增加 `--dry-run` 预演模式；支持在别名配置中持久化可选的 `region` 字段。

20261026 还加入客户端身份缓存隔离、复制重同步 JSON 终态输出和速率溢出修复、start/cancel 部分失败的非零退出码，以及缺少实时指标时的 batch `pending` 状态与有界回退。完整命令与脚本迁移说明见 [mcli 更新](/zh/blog/release/silo-20261026/#mcli)。

---

## 7. 运维配置、供应链与二进制分发 {#operations-and-delivery}

在服务端运维配置与交付链路上，SILO 做了四类贴近生产环境的改造：

1. **让请求头超时真正生效，并补齐可信代理边界**：
   - 上游虽然定义了 `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT`，但并未真正传给底层 `http.Server`，导致 HTTP/1 连接在慢速滴灌请求头（Slowloris）下可以无限期挂住。SILO 将该参数真正接入 HTTP 服务（默认 30 秒绝对读取期限，[设计记录](/zh/blog/design/request-header-timeouts/)）。
   - 新增 `MINIO_API_TRUSTED_PROXIES` 与 `MINIO_IDENTITY_LDAP_STS_TRUSTED_PROXIES`，默认不再盲目信任客户端伪造的 `X-Forwarded-For`；新增 `CONSOLE_WS_MAX_MESSAGE_BYTES` 与 `CONSOLE_WS_MAX_DECOMPRESSED_BYTES` 限制内嵌控制台 WebSocket 帧大小。
   - 新增原生 `silo healthcheck` 子命令，使无 shell 的 distroless 容器也能直接执行就绪与存活探针；收紧 `MINIO_CONFIG_ENV_FILE` 解析器，拒绝畸形配置行。
2. **修复事件通知目标（Notification Targets）连接管理**：
   - 修复 NATS 断线重连与 JetStream 异步发布回复主题冲突、AMQP 确认锁竞争、PostgreSQL/MySQL TLS 配置加载，并显式保留 Kafka 通知目标的默认协议版本 `2.1`。
3. **彻底移除自更新与后台外联（Call-Home）**：
   - 永久移除二进制原地自更新（`MINIO_UPDATE`）以及全部 `SUBNET` 注册、遥测、许可证检查与后台外联代码。软件升级完全交还给操作系统的包管理器（RPM/DEB/APK）与容器编排系统。
4. **重建可验证的多架构发行供应链**：
   - 全栈升至 **Go 1.27.3**（内置 `crypto/x509` 失信中间证书拦截），容器基础镜像采用 UBI 9.8 与 distroless 双变体，内置静态编译的 `curl 8.23.0` 并应用 Red Hat `RHSB-2026-012` 根证书封禁列表。
   - 每个正式版本均提供 Linux（`amd64`/`arm64`/`ppc64le`/`s390x`）、macOS（`amd64`/`arm64`）、Windows（`amd64`/`arm64` ZIP 归档）二进制、RPM/DEB/APK 软件包、Docker Hub 多架构镜像（`pgsty/silo`、`pgsty/silo-console`、`pgsty/mc`、`pgsty/kes`），并附带 GPG 签名、SPDX SBOM 与 GitHub Sigstore 构建证明（详见[下载与安装](/zh/download/)）。

---

## 8. 诚实的边界：撤回的尝试与尚未解决的问题 {#boundaries-and-lessons}

维护一个生产级存储系统，不仅要看合并了什么，更要看**试过之后因为代价过高而主动撤回了什么**。这一年里，有四项改动我们在做完实现、跑完压测或故障注入后，最终决定撤回或关闭：

1. **撤回公开持久化的 `ListMultipartUploads` 磁盘扫描（[#79](https://github.com/pgsty/silo/issues/79)）**：
   - **初衷**：上游的 `ListMultipartUploads` 只查单节点内存缓存，节点重启后未完成的分段上传在列表中就会消失。我们曾在 9 月版本中尝试扫描底层存储池/纠删集上的持久化上传目录。
   - **撤回原因**：容量实测表明，持久扫描的延迟随前缀深度与残留未完成上传数量呈线性恶化，在 20,000 个未完成上传规模下会直接触发请求超时并拖慢磁盘 I/O。因此在 Server 20261018 中，我们果断撤回了公开持久扫描并退役了可选 `strict` 模式，恢复为节点本地缓存加精确 key 查询（详见 [ListMultipartUploads 设计与容量证据](/zh/blog/design/list-multipart-uploads/#implementation)）。
2. **撤回默认路径上的严格代际拒读与自动跨池读恢复**：
   - **初衷**：当部分覆盖写失败导致不同磁盘或不同存储池之间出现版本代际分裂（split generation）时，曾尝试在读取路径上直接拒绝存在代际分歧的读取，或在 `GET` 时自动跨池恢复。
   - **撤回原因**：故障注入表明，在部分覆盖写失败后直接拒读会破坏 MinIO 原有的可用性契约（即部分覆盖失败后旧版本仍应可读）。因此我们将严格拒读诊断降级放入非默认的 `consistency_strict` 构建标签中，默认生产构建继续保留原有的读取仲裁与自愈行为。
3. **放弃多池覆盖亲和性方案（[#245](https://github.com/pgsty/silo/pull/245)）**：
   - **初衷**：在多存储池集群中，同名对象的无版本覆盖写可能落到新池，从而在旧池留下过期副本。`#245` 尝试把覆盖写强制路由回对象原先所在的存储池。
   - **放弃原因**：当历史存储池因为坏盘失去写仲裁、而集群中其他健康存储池仍有充足空间时，强制亲和会让覆盖写直接失败；且两轮 `m3` 多节点压测显示小对象覆盖延迟仍未达标。最终我们选择关闭 `#245` 不予合并（详见[多池覆盖亲和设计记录](/zh/blog/design/overwrite-pool-affinity/)）。
4. **移除实验性的访问频率池间分层（`ilm access_*`）**：
   - 该实验特性从未达到生产可靠性标准，已在 Server 20260916 中彻底清理（详见[访问频率分层移除说明](/zh/compatibility/access-tiering-removal/)）。

### 当前仍需注意的工程与升级边界

最后，把当前版本的客观边界再次汇总如下，供评估与升级时参考：

- **没有分布式锁 fencing**：当节点因 GC 停顿、网络抖动或慢盘导致锁租约过期后，失去租约的节点上已经在途的提交仍可能晚于新写入落地；部分元数据更新在故障窗口下仍可能短暂暴露旧标签或旧属性。本版保持既有超时语义，不能把请求返回当作底层 I/O 已结束的证明。
- **不宣称未经对等验证的全集群吞吐百分比**：我们在单点热路径上有明确的微基准（例如 `silo-pkg v3.14.3` 将 `ContainsAdminAction` 从每次调用分配 24 次内存、`742.5 ns/op` 优化为零分配、`5.53 ns/op`），但尚未在固定硬件上对 `2025-10-15` 与 `2026-10-26` 运行完整的端到端多节点吞吐基准。
- **协调升级要求**：虽然底层磁盘格式保持 `xl.meta` v1.3 兼容，但启用持久化 IAM 撤销（`siloParentRevocation`）、站点复制元数据墓碑时，集群中的所有参与节点应协调升级至相同版本，不支持新旧节点长期混跑或滚动降级（详见[组件版本矩阵](/zh/compatibility/versions/)与 [IAM 升级指南](/zh/operations/replication/iam-upgrade/)）。
- **已知待修细节**：当前仓库内 Helm Chart（`7.0.3`）的默认服务端镜像标签仍停留在 `RELEASE.2026-09-16T00-00-00Z`（部署新版本时需通过 `values.yaml` 显式指定目标标签）。

---

## 结语 {#conclusion}

一年前按下 fork 按钮时，我们的目标很朴素：不造噱头、不画大饼，让还在跑开源 MinIO 的生产环境有安全补丁可打、有完整控制台可用、有干净的二进制包和镜像可拉。

一年下来，604 次提交、7 个 CVE 补丁、18 项安全边界加固、几十篇公开在[设计归档](/zh/blog/design/)与[安全归档](/zh/blog/security/)里的根因分析与取舍记录，就是 SILO 交出的第一年答卷。

如果你正在使用开源版 MinIO，可以直接查阅[迁移指南](/zh/compatibility/migration/)与[下载页面](/zh/download/)；如果你在生产环境中遇到任何可复现的协议、复制或存储问题，欢迎直接到 [`pgsty/silo`](https://github.com/pgsty/silo) 提 Issue。

路还长，我们继续维护。
