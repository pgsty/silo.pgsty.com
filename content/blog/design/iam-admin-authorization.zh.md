---
title: "IAM Admin API 授权边界修复"
linkTitle: "IAM Admin 授权边界"
date: 2026-10-16
lastmod: 2026-10-19
author: "SILO"
summary: >
  通过 Handler 层局部修补落实自管理授权，阻止受限会话凭据越权，保护 root 凭据，
  同时保留空策略兼容性和损坏密钥的清理能力；记录授权契约、性能开销、被否决方案与回归验证。
tags: [Design, IAM, Security, Compatibility]
weight: 16
draft: false
url: "/zh/blog/design/iam-admin-authorization/"
---

[Server 20261018](/zh/blog/release/silo-20261018/) 包含了 [PR #242](https://github.com/pgsty/silo/pull/242)（基于基线 [`00a375c4e`](https://github.com/pgsty/silo/commit/00a375c4edbc7590290e53d1636211de64bc7d58) 的修复提交 [`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)，合并提交 [`4e55fc7db`](https://github.com/pgsty/silo/commit/4e55fc7db4bd0f21ae187517f7438a8625768f6a)）以及批量自查询后续修复 [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8)，用于修复 [SN-2026-017](/zh/blog/security/20261018-release-hardening/#sn-2026-017)。本文记录问题范围、Handler 级授权契约、空策略与 claims 归属处理、损坏密钥清理语义、性能开销、被否决的候选方案以及回归验证结果。

## 问题与范围 {#problem}

此前部分 Admin Handler 在授权拒绝后仍以“目标属于调用者”为由放行，列出自身服务账号时甚至可能直接跳过授权检查。这些路径会绕过用户或组策略的显式 Deny、内联会话策略限制以及外部授权插件的拒绝结果。

凭据创建和更新还存在另一类越权路径：获准执行相应 Admin Action 的受限派生凭据，可以创建继承父账号更大权限的新密钥，或通过更新操作移除服务账号原有的限制；拥有广泛 Admin 权限的非 root 管理员也能操作 root 的派生凭据。在内置授权模式下，仅凭单个 Action 许可不足以放行这些操作。

本次修复覆盖服务账号与访问密钥的查询、清理、创建和更新 Handler（含批量密钥查询和 LDAP 创建入口），同时保持策略引擎全局语义、现有 Admin 路由与 Action、请求响应格式及 IAM 存储格式不变，无需调整依赖版本。

文中的**内置授权**指未配置外部授权插件的模式，包括由本地 IAM 评估 LDAP/OIDC 身份权限的场景。相关策略模型见[访问管理](/zh/administration/identity-access-management/policy-based-access-control/)与[外部授权](/zh/administration/identity-access-management/pluggable-authorization/)。

## 授权契约 {#contract}

传给 IAM 的操作主体始终是已认证的调用者 AccessKey。比对归属关系时，若存在 `ParentUser` 则取父账号，否则取 `AccessKey`；归属归一化不会在策略评估阶段将派生凭据替换为父账号身份。

自查询和自清理在调用授权前设置 `DenyOnly: true`：普通用户无需额外 Allow 策略即可执行既有的自管理操作，但显式 Deny 依然生效；派生凭据继续执行完整 IAM 评估，其有效会话策略必须明确允许目标操作；外部插件的拒绝结果始终生效。任何 Handler 都不会再因目标属于调用者而覆盖拒绝决定。

| Handler | 现有 Admin Action | 自管理语义与附加边界 |
| --- | --- | --- |
| `InfoServiceAccount` | `admin:ListServiceAccounts` | 比对有效用户与服务账号存储的父账号，授权通过后返回详情。 |
| `ListServiceAccounts` | `admin:ListServiceAccounts` | 空用户参数、调用者 AccessKey、调用者父账号均视为自身别名；每次请求均执行授权，并列出父账号名下的密钥。 |
| `ListAccessKeysBulk` | `admin:ListServiceAccounts` | 自身别名统一按父身份归一化并复用同一自管理授权辅助函数；跨用户查询和 `all=true` 保持原有权限要求。 |
| `InfoAccessKey` | `admin:ListServiceAccounts` | 仅当目标存在、属于派生凭据且父账号相同时才视为自身；不存在的目标不触发自管理分支。 |
| `DeleteServiceAccount` | `admin:RemoveServiceAccount` | 自清理先执行授权再检查 root 边界；目标 token 损坏时直接读取存储的身份元数据。 |
| `RevokeTokens` | `admin:RemoveServiceAccount` | 省略用户参数或解析后等于调用者父账号时视为自身；先执行授权并保护 root 目标。 |
| `AddServiceAccount`、`AddServiceAccountLDAP` | `admin:CreateServiceAccount` | 完成既有自身或跨用户 IAM 授权后，拒绝受有效会话策略限制的调用者及无权管理 root 的调用者。 |
| `UpdateServiceAccount` | `admin:UpdateServiceAccount` | 完成既有 Action 授权后，拒绝受有效会话策略限制的调用者及无权管理 root 的调用者；不引入自更新特权。 |

即使会话策略允许创建或更新 Action，受该策略限制的调用者也不能执行这些操作。更新守卫同样拦截仅修改名称等元数据的请求，因为现有更新实现会在请求未提供新策略时清除原有内联策略。

## 三个局部辅助函数 {#helpers}

生产代码改动集中在 `cmd/admin-handlers-users.go` 以及 `cmd/admin-handlers-idp-ldap.go` 的 claims 复制循环，通过三个局部辅助函数收敛边界，`IAMSys.IsAllowed` 保持不变。

`hasActiveSessionPolicy` 复用现有会话策略评估函数，按 IAM 派发顺序先检查临时凭据，再检查服务账号。设置了过期时间的服务账号同样满足 `IsTemp()`，会走 STS 评估路径。因此，带有 `inherited-policy` 标记且含过期时间的历史凭据仍可能携带有效的内联限制；若先检查继承标记，会误放行此类凭据去创建或更新权限更大的密钥。非临时服务账号则沿用现有服务账号评估器对继承标记与空策略的处理逻辑。

`canManageRootCredentials` 作为内置授权通过后的附加守卫，仅放行 root 自身或不受会话策略限制的 root 派生凭据（排除内部站点复制服务账号）。签名验证阶段的 `owner` 标记在原始会话策略 claim 存在时就会被清除，即便服务账号评估器判定该策略为空。直接检查实际限制可保留历史上使用 `null`、`{}` 或 `{"Statement":null}` 创建的 root 服务账号的管理能力。

`isAllowedServiceAccountAction` 保留普通用户在解绑最后一个策略后既有的自查询与自清理能力。仅当调用满足内置授权、非 owner、非派生凭据且设置 `DenyOnly` 时，该函数直接解析用户与组策略并评估合并结果（允许合并结果为空，显式 Deny 仍生效）；其余调用继续走 `IAMSys.IsAllowed`，从而避免修改全局“无绑定策略”行为而波及无关的 S3 与 Admin 操作。

创建、更新、删除和吊销操作上的 root 守卫仅在内置授权下生效。配置外部授权插件时，包括 root 目标在内的所有请求均交由插件裁决，此前被自身分支跳过的请求现在同样经过插件检查。

## 空策略与 claims 的归属 {#empty-policies}

代码复核还发现创建路径上一处可用性缺陷：将父服务账号的空内联策略复制给新的继承型子密钥时，会残留旧的内部策略 claim。一旦新密钥设置了过期时间，STS 评估器会因空策略缺少 `Version` 字段而拒绝访问，导致密钥创建成功却无法使用。

在创建请求中显式传入语义空策略并同时设置过期时间，也会触发相同故障。两类问题统一在 Admin 签发入口处理：

1. 两个创建 Handler 在复制调用者 claims 时跳过 `exp`、`policy.SessionPolicyName`、`sessionPolicyNameExtracted` 和 `iamPolicyClaimNameSA()`。新密钥使用自身的过期时间和请求策略，其余身份信息（含 LDAP/OIDC 上下文）原样保留。
2. `commonAddServiceAccount` 仅当解析后的策略满足 `Version == "" && Statements == nil && ID == ""` 时将其归一化为继承策略，与现有服务账号评估器的空策略定义保持一致；同时清空本地策略选项和返回请求中的 Policy 字段，确保站点复制发出的创建消息与本地落盘密钥一致。

| 新密钥请求中的策略 | 结果 |
| --- | --- |
| 省略、`null`、`{}`、`{"Statement":null}` | 继承父账号权限（含设置过期时间的密钥）。 |
| 仅允许特定 Action 的策略 | 保留所请求的限制，未授权操作继续拒绝。 |
| `{"Version":"2012-10-17"}` 或 `{"Statement":[]}` | 不归一化为继承策略；带过期时间的回归用例继续拒绝访问。 |

归一化判断条件使用 `Statements == nil` 而非 `len(Statements) == 0`，以区分 Console 特有的空策略占位形态与显式传入空语句列表的策略。

`IAMSys.NewServiceAccount` 同时供 IAM 导入与站点复制调用。若在该公共构造函数中清洗 claims，会抹掉历史过期凭据仅保存在 claims 中的有效限制。因此公共构造函数与历史记录重放逻辑保持不变，仅在 Admin 签发入口规范化新凭据。

## 删除与错误语义 {#deletion}

`DeleteServiceAccount` 直接通过 `globalIAMSys.store.GetUser` 读取存储的身份元数据，校验服务账号类型并保留存储的父账号，无需解码目标 session token。底层删除操作使用同一查找原语，既避开了 token 解析，又绕开了公开用户查询对禁用或过期凭据的过滤，同时保留 store 原有的父账号吊销检查。

具备权限的管理员可正常清理 token 损坏、已禁用或已过期的非 root 服务账号，而非 root 管理员无法利用 token 损坏掩盖目标的 root 归属。保留下来的父账号也保证了站点复制钩子能准确判断是否同步删除消息。

无权删除他人密钥、被 root 守卫拦截或目标服务账号不存在时，统一返回 `ErrAdminServiceAccountNotFound`（HTTP 404）；自身操作被策略拒绝时返回 `ErrAccessDenied`（HTTP 403）。其余端点保持原有的查询与报错顺序。

## 兼容性与边界 {#compatibility}

行为收紧集中在三处：自管理操作必须遵守显式拒绝策略、受会话限制的凭据不得创建或更新密钥、内置授权下保护 root 凭据免受非 root 修改。依赖旧旁路逻辑的自动化任务需改用具备相应权限且不受会话策略限制的身份。普通用户（含解绑策略后）原有的自查询与自清理能力不变，历史 root 空策略服务账号的管理能力不变。

新建空策略密钥的元数据统一保存为 `inherited-policy`，不再写入内嵌空策略文档。这消除了带有效期密钥在两条评估路径上的行为分歧；策略内部保留字段也不再从调用者复制给新密钥，仅反映新凭据自身的属性。

2026-10-18 的后续提交 [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) 将 `ListAccessKeysBulk` 接入同一自管理授权辅助函数。无绑定策略的普通用户可正常自查询，显式 Deny、派生凭据会话限制与跨用户授权照常生效。省略 `users` 参数，或唯一 `users` 参数为调用者自身 AccessKey／父账号时，统一查询解析后的父账号密钥列表；`all=true` 仍需 `admin:ListUsers` 权限。回归测试会解密响应负载并校验普通用户、服务账号与 STS 别名下的身份内容。

此前已生成且无法使用的过期历史凭据不会自动改写，应由父账号或管理员重新签发新密钥并在验证后删除旧密钥。切勿通过批量清除导入或复制凭据的策略 claims 来做迁移，以免破坏存量凭据上的有效会话限制。

关于分布式吊销顺序与并发管理变更边界，参见[持久化 IAM 撤销](/zh/blog/design/iam-revocations/)。

## 成本与被否决的候选方案 {#cost}

PR `#242` 在两个生产 Handler 文件中净增 59 行代码，10 月 18 日的批量查询修复直接复用同一辅助函数。改动未引入新缓存、后台任务、锁协议或存储迁移，也未触及 S3 数据路径；claims 过滤在既有复制循环中完成，空策略归一化直接复用创建请求已解析的策略对象。

Admin 创建与更新检查可能需要额外解析一次调用者的内联策略（服务账号策略上限为 4 KiB），复用现有评估器避免维护第二套“有效策略”判定逻辑。原先跳过授权的部分自查询请求现在会执行必要的策略评估，通常直接命中 IAM 内存缓存；仅当合并策略加载器发现文档缺失时才会访问底层存储。在启用外部授权插件的部署中，补齐的授权检查会向插件发起一次请求，耗时取决于外部插件服务。

在 Darwin/arm64（Apple M5 Max，Go 1.27.2，三次 200 ms 采样）上的基准测试结果如下：
- 普通或继承型会话检查：约 11–16 ns，0 次内存分配；
- 空服务账号策略检查：约 0.30–0.32 µs；
- 约 3 KiB 的内联策略检查：约 10 µs；
- 缓存命中的普通用户自管理授权：与现有 IAM 路径同处亚微秒量级（800 B / op，15 allocs / op）。

上述开销无需在 Admin 路径上额外引入专用缓存或策略表示。

设计复核评估并否决了以下五种方案：
1. **全局修改 `IAMSys.IsAllowed`**：会改变全局“无绑定策略”或自归属语义，波及无关的 S3 与 Admin 操作。
2. **仅凭原始会话策略 claim 键存在即判定受限**：历史上使用 `null`、`{}` 或 `{"Statement":null}` 创建的 root 服务账号同样带有原始 claim 键，按存在性拦截会破坏其管理能力。
3. **在 `IAMSys.NewServiceAccount` 公共构造函数中统一剔除策略字段**：该函数同时被 IAM 导入和站点复制调用，在公共构造函数中清洗 claims 会丢失历史过期凭据仅保存在 claims 内的有效限制。
4. **为会话受限凭据实现通用委派策略包含关系求解**：会话受限凭据的设计定位是受限叶节点凭据而非子签发者，直接禁止有效会话策略持有者创建或更新子密钥即可用 59 行代码闭合越权路径。
5. **一律拒绝损坏密钥的清理**：会导致管理员无法利用存储的身份元数据清理 token 已损坏、已禁用或已过期的非 root 服务账号。

## 回归证据 {#validation}

提交 `2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6` 与后续提交 `9954392605827b213877c45262c741e638598dd8` 通过了以下测试套件：

| 检查 | 结果 |
| --- | --- |
| 完整 `TestIAM*` / `TestSTS*`（连接真实 etcd、LDAP、两个 OIDC Provider 和外部授权插件） | 57 个顶层测试；含子测试共 380 条通过记录；0 失败、0 跳过。 |
| `TestIAMAdmin*` 回归测试（使用签名请求及加密 Admin 请求体） | 通过。 |
| `TestIAMAdmin*` 与 peer 删除/重载测试的定向 `-race` 检查 | 通过。 |
| 认证、身份配置与策略配置相关包测试 | 通过。 |
| `make verifiers` 与 `make build` | lint、生成文件、品牌与兼容性检查通过，成功构建 `silo` 二进制文件。 |
| PR `#242` 云端 CI 检查 | DCO、漏洞扫描、格式/构建/Vet、lint/生成文件、race、交叉编译、internal 与 cmd 测试共 8 项全部通过。 |

`cmd/admin-handlers-users-authz_test.go` 覆盖了 root 空策略、无绑定策略用户自管理、父用户/组/会话/插件拒绝、带过期时间的历史 inherited 凭据、非 root 操作 root 目标、禁用或过期的损坏密钥清理、删除复制、自身别名，以及空策略子密钥签发的正反向访问验证。LDAP 测试套件额外通过 `AddServiceAccountLDAP` 签发带过期时间的子密钥并验证 S3 访问。补充边界测试验证了损坏 root 密钥的清理拦截，以及五个自管理 Handler 对 STS 显式与隐式拒绝的处理。

验证过程中同时修正了两处既有测试夹具问题：peer 重载测试在构造对象存储夹具前显式清理残留的 etcd 客户端状态；IAM 导入测试改为从 `policy.DefaultPolicies` 动态获取默认策略名。

复现验证命令：

```sh
go test ./cmd -run '^TestIAMAdmin' -count=1 -v
go test -race ./cmd -run '^(TestIAMAdmin|TestIAMPeerDeleteNotificationReloadsCommittedState)' -count=1
go test -tags kqueue,dev ./cmd -run '^(TestIAM|TestSTS)' -count=1 -timeout=30m -v
go test ./internal/auth ./internal/config/identity/... ./internal/config/policy/...
make verifiers
make build
```

## 交付与升级说明 {#delivery}

- 发行版本：[Server 20261018](/zh/blog/release/silo-20261018/#security)（PR [`#242`](https://github.com/pgsty/silo/pull/242)，提交 `2616d43fb`、`4e55fc7db` 与 `995439260`）。
- 安全通告：[SN-2026-017](/zh/blog/security/20261018-release-hardening/#sn-2026-017)。
- 请升级所有接收 Admin 流量的服务端节点，避免混合版本部署将请求路由至未修补的 Handler。本次变更不涉及磁盘格式变更，无需批量重写存量凭据。
