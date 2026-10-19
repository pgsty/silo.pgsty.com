---
title: "IAM Admin API 授权边界修复"
linkTitle: "IAM Admin 授权边界"
date: 2026-10-16
lastmod: 2026-10-19
author: "SILO"
summary: >
  用局部 Handler 修补落实自管理授权，阻止会话凭据逃逸限制，保护 root 凭据，
  同时保留空策略兼容性和损坏密钥的清理能力；记录设计、成本、回归证据与交付边界。
tags: [Design, IAM, Security, Compatibility]
weight: 16
draft: false
url: "/zh/blog/design/iam-admin-authorization/"
---

**20261018 正式发布：** [选定源码](/zh/blog/release/silo-20261018/)包含 #242 与批量自查询后续修复 `995439260`。Server Release 已正式发布；下文 10 月 16 日验证记录仅对应当时源码。安全影响见 [SN-2026-017](/zh/blog/security/20261018-release-hardening/#sn-2026-017)。

**2026-10-16 决策：GO，源码验收与合并已完成。**
[服务端 PR #242](https://github.com/pgsty/silo/pull/242) 已将带 DCO 签署的修复提交
[`2616d43fb`](https://github.com/pgsty/silo/commit/2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6)
合入 `main`，合并提交为
[`4e55fc7db`](https://github.com/pgsty/silo/commit/4e55fc7db4bd0f21ae187517f7438a8625768f6a)。
最终候选直接基于 main 的 `00a375c4e` 验证，与待处理的 LIST 修复独立。
八项云端检查及完整本地 IAM/STS 集成测试全部通过。

本文记录源码集成状态。打标签、发布软件包或容器、生产部署仍是独立事项；
合并不代表已有发行镜像已经包含修复。

## 问题与范围 {#problem}

部分 Admin Handler 在授权已经拒绝后，仍以“目标属于自己”为由放行；列出自己的
服务账号还可能完全跳过授权。这些路径会覆盖用户或组策略的显式 Deny、内联会话
策略限制，以及外部授权插件的拒绝结果。

创建和更新凭据还存在另一类边界问题：拥有相应 Admin Action 的受限派生凭据，
可能创建一个继承父账号更大权限的新密钥，或通过更新移除服务账号的限制。
拥有广泛 Admin 权限的非 root 管理员也可能管理 root 的派生凭据。
在内置授权下，仅获准执行某个 Action，不足以放行这些操作。

修复覆盖查询／清理与创建／更新 Handler，包括批量密钥查询和 LDAP 创建入口。
保留策略引擎的全局语义、现有 Admin 路由和 Action、请求响应格式及 IAM 存储格式，
不需要修改依赖版本。

本文的**内置授权**指没有配置外部授权插件，包括由本地 IAM 评估 LDAP/OIDC 身份
权限的情况，不等于调用者必须是内置用户。相关策略模型见
[访问管理](/zh/administration/identity-access-management/policy-based-access-control/)
与[外部授权](/zh/administration/identity-access-management/pluggable-authorization/)。

## 授权契约 {#contract}

传给 IAM 的操作主体始终是已认证的调用者 AccessKey。比较归属时，有 `ParentUser`
就使用父账号，否则使用 `AccessKey`。归一化归属不会在策略评估时把派生凭据替换
成父账号身份。

自查询和自清理通过 `DenyOnly: true` 表达既有的自管理语义，并在授权之前设置。
普通用户不需要额外的 Allow，但适用的显式 Deny 仍然有效。派生凭据继续完整经过
IAM 评估，有效会话策略必须明确允许相应操作。外部插件的拒绝结果不可被覆盖。
Handler 不再因为目标属于调用者，就把拒绝改成成功。

| Handler | 现有 Admin Action | 自管理语义与附加边界 |
| --- | --- | --- |
| `InfoServiceAccount` | `admin:ListServiceAccounts` | 比较有效用户与服务账号的存储父账号，授权通过后返回信息。 |
| `ListServiceAccounts` | `admin:ListServiceAccounts` | 空用户参数、调用者 AccessKey、调用者父账号均为自身别名；每次请求都授权，并为这些别名列出父账号的密钥。 |
| `ListAccessKeysBulk` | `admin:ListServiceAccounts` | 自身别名按父身份规范化并调用同一自助授权 helper；跨用户和 `all=true` 保留额外权限要求。 |
| `InfoAccessKey` | `admin:ListServiceAccounts` | 目标必须存在、属于派生凭据且父账号相同才算自身；不存在的目标不能形成自身例外。 |
| `DeleteServiceAccount` | `admin:RemoveServiceAccount` | 自清理先授权，再检查 root 边界；目标 token 损坏时仍使用存储身份元数据。 |
| `RevokeTokens` | `admin:RemoveServiceAccount` | 省略用户或解析后的用户等于调用者父账号时视为自身；先授权，且保护 root 目标。 |
| `AddServiceAccount`、`AddServiceAccountLDAP` | `admin:CreateServiceAccount` | 保留既有自身/其他用户的 IAM 授权，再拒绝有效会话策略调用者及无权管理的实际 root 目标。 |
| `UpdateServiceAccount` | `admin:UpdateServiceAccount` | 保留现有 Action 要求，再拒绝有效会话策略调用者及无权管理的 root 目标；不新增自更新权限。 |

即使会话策略允许创建或更新 Action，受该策略限制的调用者也不能执行这些操作。
安全委派需要另行设计限制的传递或策略包含关系判定，本次不实现这一能力。
更新守卫也覆盖仅修改名称等元数据的请求：现有更新实现可能在请求未提供新策略时
清除原有内联策略。

## 三个局部辅助函数 {#helpers}

生产修改集中在 `cmd/admin-handlers-users.go` 和
`cmd/admin-handlers-idp-ldap.go` 的 claims 复制循环。
三个小型辅助函数表达边界，`IAMSys.IsAllowed` 保持不变。

`hasActiveSessionPolicy` 复用现有会话策略评估函数，先判断临时凭据，再判断服务
账号，与 IAM 的派发顺序一致。带过期时间的服务账号也满足 `IsTemp()`，会按 STS
路径评估。因此，标记为 `inherited-policy`、带过期时间的历史凭据仍可能携带有效的内联
限制。如果先检查 inherited 标记，就可能错误地放行它创建或更新更大权限的密钥。
非临时服务账号则遵循现有服务账号评估器对继承标记与空策略的处理。

`canManageRootCredentials` 是内置授权成功之后的附加守卫，接受 root 本身或不受
会话策略限制的 root 派生凭据，并排除内部站点复制服务账号。它自身不授予 Action。
签名验证的 `owner` 标记不足以完成这项判断：只要原始会话策略 claim 存在，该标记
就可能被清除，即使服务账号评估器认为策略为空。检查实际限制，才能保留历史上
使用 `null`、`{}` 或 `{"Statement":null}` 的 root 服务账号管理能力。

`isAllowedServiceAccountAction` 保留普通用户在最后一个绑定策略被移除后，既有的
自查询、自清理能力。仅对内置授权、非 owner、非派生、`DenyOnly` 的调用者，直接
解析用户和组的策略并评估合并结果，允许合并结果为空；显式 Deny 仍然有效。
其他调用者继续使用 `IAMSys.IsAllowed`。修改引擎全局的“无绑定策略”行为会影响
无关的 S3 与 Admin 操作，因此不在此处修改。

创建、更新、删除和吊销操作的 root 守卫仅作用于内置授权。外部授权插件继续决定
这些操作，包括 root 目标；此前被自身旁路跳过的请求，现在也必须尊重插件结果。

## 空策略与 claims 的归属 {#empty-policies}

复核发现创建路径还有一项可用性缺陷：把父服务账号的空内联策略复制给新的继承型
密钥，会留下过时的策略内部 claim。若新密钥带过期时间，STS 评估因空策略没有
Version 而拒绝请求，造成“创建成功，但密钥不能执行预期操作”。

新请求自己显式指定语义空策略并附带过期时间，也会产生同样的故障。
两种情况都在 Admin 签发入口解决：

1. 两个创建 Handler 复制调用者 claims 时，跳过 `exp`、
   `policy.SessionPolicyName`、`sessionPolicyNameExtracted` 和
   `iamPolicyClaimNameSA()`。新密钥使用自己的过期时间和请求策略，其他身份信息，
   包括 LDAP/OIDC 上下文，继续保留。
2. `commonAddServiceAccount` 仅在解析结果满足
   `Version == "" && Statements == nil && ID == ""` 时规范化为继承策略。
   这与现有服务账号评估器的空策略定义一致。同时清空本地策略选项和返回请求的
   Policy，使站点复制的创建消息与本地生成的密钥保持一致。

| 新密钥请求中的策略 | 结果 |
| --- | --- |
| 省略、`null`、`{}`、`{"Statement":null}` | 继承父账号权限，包括设置了过期时间的情况。 |
| 只允许特定 Action 的策略 | 保留请求限制，未允许的操作继续被拒绝。 |
| `{"Version":"2012-10-17"}` 或 `{"Statement":[]}` | 不规范化为继承；带过期时间的回归用例继续拒绝访问。 |

这里刻意不使用 `len(Statements) == 0` 判断：没有语句的策略不一定属于 Console
空策略的特殊情况。

`IAMSys.NewServiceAccount` 同时服务于导入和站点复制。如果在这一公共构造函数中
清洗 claims，可能丢掉仅存在于带过期时间的历史凭据 claims 内的有效限制。因此不修改公共
构造函数和历史记录的重放语义。本次修复新 Admin 签发行为，不重写已存储凭据。

## 删除与错误语义 {#deletion}

删除需要可信的身份元数据，不需要目标 session token 能被成功解码。
`DeleteServiceAccount` 直接读取 `globalIAMSys.store.GetUser`，检查服务账号类型，
并保留存储的父账号。底层删除操作也使用同一查找原语。这样既避开 token 解析，
也避开公开用户查找对禁用/过期凭据的过滤，同时保留 store 已有的父账号撤销检查。

有权限的管理员仍能清理损坏、禁用或过期的非 root 服务账号；非 root 管理员不能
借 token 损坏隐藏 root 归属。保留下来的父账号也让站点复制钩子正确判断是否应发送
删除消息。这不意味着可以恢复身份元数据缺失或已无法识别为服务账号的任意记录。

无权删除他人的密钥、被 root 守卫拒绝、以及服务账号不存在时，返回
`ErrAdminServiceAccountNotFound`（HTTP 404）。自身操作被策略拒绝时返回
`ErrAccessDenied`（HTTP 403）。其他端点保留已有的查询与报错顺序；本次不重新设计
所有 Admin 接口的防枚举行为。

## 兼容性与边界 {#compatibility}

预期收紧包括：自身操作也必须尊重既有拒绝；会话受限凭据不能创建或更新密钥；
内置授权下保护 root 凭据变更。依赖旧旁路的自动化需要改用具备相应权限、且不受
会话限制的身份。普通用户仍保留既有查询与清理能力，包括解绑策略后；历史 root
空策略服务账号仍保留管理能力。

新空策略密钥的元数据规范化为 inherited policy，而不再保存嵌入式空策略。
检查策略表示的客户端可能观察到这一变化；服务账号继承权限的含义保持一致，
带有效期的密钥在两种评估路径上不一致的问题得到修复。策略内部保留字段也不再从调用者复制给新密钥。
检查这些内部字段的外部插件应将其视为新凭据自身的属性，而不是调用者会话限制的
副本。

`ListAccessKeysBulk` 已由 2026-10-18 后续提交 [`995439260`](https://github.com/pgsty/silo/commit/9954392605827b213877c45262c741e638598dd8) 纳入同一自助授权 helper。普通用户没有策略绑定时可自查询；显式 Deny、派生凭据的会话限制和跨用户授权仍生效。省略 users，或唯一 users 参数是调用者自己的 key／父身份时，统一只查询解析后的父身份。`all=true` 仍要求额外的 `admin:ListUsers`，不会变成自查询。回归会解密响应并核对身份内容，覆盖普通用户、服务账户与 STS 别名。

已经不可用、带过期时间的历史凭据不会被自动修复。应由有权限的父账号或管理员重新签发
预期密钥，验证访问后移除旧密钥。不要通过批量擦除导入或复制凭据的策略 claims
进行迁移；历史凭据已有的有效限制必须保留。

正式支持的产品组合为 SILO、SILO Console、mcli 和 silo-pkg；与未修改的上游
MinIO/MC 保持尽最大努力的兼容。本次不改变依赖选择，也不新增上游发布门禁。
同样不改变分布式撤销顺序，也不保证并发管理变更与授权之间形成原子事务；这些
边界见[持久化 IAM 撤销](/zh/blog/design/iam-revocations/)。

## 成本与替代方案 {#cost}

原 #242 在两个生产 Handler 文件中合计净增 59 行；10 月 18 日的批量查询修复复用其 helper。没有新增缓存、后台任务、锁协议、存储迁移，
也没有修改 S3 数据路径。字段过滤使用已有复制循环，空策略规范化复用创建请求
已经解析的策略。

Admin 创建/更新检查可能额外解析调用者的内联策略；服务账号策略已有 4 KiB
上限。复用现有评估器避免了维护第二套“有效策略”定义。部分原先跳过授权的自查询
现在增加了必要的策略评估。策略查找通常使用 IAM 缓存，但合并策略的现有加载器在
文档缺失时仍可能访问存储。插件部署中，新增的授权检查可能产生插件请求，其延迟
取决于插件服务。

在 Darwin/arm64、Apple M5 Max、Go 1.27.2 上进行的局部诊断基准，使用三次 200 ms
采样：普通/继承型会话检查约 11–16 ns，无分配；空服务策略约 0.30–0.32 微秒；
约 3 KiB 的策略约 10 微秒。缓存命中的普通用户自身授权与现有 IAM 路径同处于
亚微秒量级，每次均为 800 字节、15 次分配。这些只是局部测量，不是端点延迟或
S3 吞吐承诺；没有证据表明需要为这些 Admin 路径引入缓存或更复杂的策略表示。

未采用的方案包括：全局修改 `IsAllowed`、仅凭原始 claim 存在就判断受限、在
`NewServiceAccount` 统一删除策略字段、实现委派策略包含关系分析，以及一律拒绝
损坏密钥的清理。这些方案要么扩大改动范围，要么破坏局部检查可以保留的既有行为。

## 回归证据 {#validation}

最终候选提交 `2616d43fbc3400a02cc1e6f9299e26ae8b2e71a6` 于 2026-10-16 通过以下检查：

| 检查 | 结果 |
| --- | --- |
| 完整 `TestIAM*` / `TestSTS*`，使用真实 etcd、LDAP、两个 OIDC Provider 和授权插件 | 57 个顶层测试；380 条包含父测试和子测试的通过记录；0 失败、0 跳过。 |
| 十个 `TestIAMAdmin*` 回归测试，使用签名请求及加密 Admin 请求体 | 通过。 |
| `TestIAMAdmin*` 与 peer 删除/重载测试的定向 race 检查 | 通过。 |
| 认证、身份配置、策略配置相关包 | 通过；无测试文件的包如实报告。 |
| `make verifiers` | lint、生成文件、品牌与兼容性检查通过；可选的 `typos` 未安装，已跳过。 |
| `make build` | 通过，生成 `silo` 可执行文件。 |
| 最终 PR 提交的云端检查 | DCO、漏洞扫描、格式/构建/Vet、lint/生成文件、race、交叉编译、internal 与 cmd 测试，共八项全部通过。 |

`cmd/admin-handlers-users-authz_test.go` 覆盖 root 空策略、无绑定策略用户自管理、
父用户/组/会话/插件拒绝、带过期时间的历史 inherited 凭据、非 root 操作 root 目标、
禁用/过期损坏密钥清理、删除复制、自身别名，以及空策略子密钥签发的正反向访问
检查。LDAP 套件还通过 `AddServiceAccountLDAP` 签发带过期时间的子密钥并实际访问 S3。
另有本地对抗性探针验证损坏 root 密钥的清理边界，以及五个自管理 Handler 对 STS
显式/隐式拒绝的处理。

同时修正两处既有测试问题：peer 重载测试在构造对象存储 fixture 前明确清空残留
的 etcd 客户端；IAM 导入测试从 `policy.DefaultPolicies` 获取默认策略名称，替代
固定名单。两者都不改变生产授权，也不弱化断言；额外的 fixture 顺序检查同样通过。

主要验证命令如下：

```sh
go test ./cmd -run '^TestIAMAdmin' -count=1 -v
go test -race ./cmd -run '^(TestIAMAdmin|TestIAMPeerDeleteNotificationReloadsCommittedState)' -count=1
go test -tags kqueue,dev ./cmd -run '^(TestIAM|TestSTS)' -count=1 -timeout=30m -v
go test ./internal/auth ./internal/config/identity/... ./internal/config/policy/...
make verifiers
make build
```

完整集成验证需要为 `_MINIO_ETCD_TEST_SERVER`、`SILO_TEST_IAM_REVOCATION_ETCD`、
`_MINIO_LDAP_TEST_SERVER`、`_MINIO_OPENID_TEST_SERVER`、
`_MINIO_OPENID_TEST_SERVER_2` 和 `_MINIO_POLICY_PLUGIN_ENDPOINT` 配置可用服务。
缺少这些环境变量的运行可能跳过集成测试，不能等同于本次结果。
完整运行设置了 `CGO_ENABLED=0` 和 `MINIO_API_REQUESTS_MAX=10000`；独立的 race
检查使用支持 race 的正常构建环境。

## 验收与交付 {#delivery}

对抗性复核在上述范围内未发现剩余阻塞问题。补丁足以关闭已识别的授权路径，保留
经过验证的兼容边界，且 Admin 操作的复杂度和执行成本合理。
结论为**本次代码候选版本 GO**。

带签署的源码提交与合并记录见本文开头，发行说明仍需标明最终包含修复的版本。所有接受 Admin 流量
的服务端都需要升级，混合版本环境仍可能把请求路由到旧 Handler。本次没有新的
磁盘格式，也不需要批量重写凭据。回滚会恢复之前的授权缺陷，因此回滚不能作为
安全修复。服务端发布、文档发布和部署验证仍是独立步骤，源码验收不等于这些步骤完成。
