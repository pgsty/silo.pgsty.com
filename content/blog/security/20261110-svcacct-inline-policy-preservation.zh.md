---
title: "SN-2026-021：服务账号不带策略的编辑操作静默清空内联策略"
linkTitle: "SN-2026-021 · 服务账号策略丢失"
date: 2026-11-10
author: "冯若航"
description: "UpdateServiceAccount 将请求中未携带或为 null 的 newPolicy 与显式传入的空策略文档合并为同一分支，导致服务账号在执行禁用/启用状态切换、轮换密钥、改名、改描述或修改过期时间后丢失内联限制策略，直接回退为继承父用户的完整权限。"
tags: [安全, IAM, Service Account, Access Control, Site Replication, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261110-svcacct-inline-policy-preservation/"
---

**发布状态：** 主干已修复（[`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27)，经 [PR #331](https://github.com/pgsty/silo/pull/331) 合入为 [`244de7ecc`](https://github.com/pgsty/silo/commit/244de7ecc1ce33f4f3e7ec452395993eb2449f11)），将随 [`20261109`](/zh/blog/release/silo-20261109/) 之后的 Server 热修版本发布\
**安全编号：** `SN-2026-021`（[安全公告台账](/zh/about/security-advisories/#sn-2026-021)）\
**严重程度：** 高危（High）\
**影响范围：** **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与自 `2022-05` 以来的上游原版 MinIO\
**客户端与控制台说明：** `mcli` 与 `silo-pkg` 无需修改；在 **SILO Console v2.7.0** 中，将访问密钥的策略编辑器清空为空白不再移除内联策略（如需移除并恢复继承父用户权限，请输入 `{}` 或 `{"Statement":[]}`）

在 SILO（及上游 MinIO）的 IAM 模型中，服务账号（Service Account / Access Key）挂靠在父用户下，可选附加一份内联会话策略（Inline Session Policy / `sub-policy`），将服务账号的实际权限收敛为父用户权限的子集。在提交 [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) 之前，`POST /minio/admin/v3/update-service-account` 接口将“请求未携带策略字段”与“显式提交空策略文档以清除内联限制”折叠为同一个 `nil` 状态。任何未指定 `--policy` 的日常管理更新——包括禁用后再启用（`disable` + `enable`）、轮换密钥（`--secret-key`）、修改名称（`--name`）、描述（`--description`）或过期时间（`--expiry`）——都会从持久化凭据令牌中删掉内联策略，并将账号改签为 `inherited-policy`（继承父用户策略），使原本受限的服务账号静默提升为父用户的完整权限。

## 摘要 {#summary}

- **漏洞根因：** 存储层的 `updatedServiceAccountCredentials`（`cmd/iam-store.go`）只要看到 `opts.sessionPolicy == nil` 就会删除 JWT 声明中的 `sessionPolicy`；而 HTTP 处理器 `(adminAPIHandlers).UpdateServiceAccount`（`cmd/admin-handlers-users.go`）在请求未带 `newPolicy` 与传入空策略文档（`sp.Version == "" && len(sp.Statements) == 0`）两种情况下均将 `sp` 设为 `nil`。
- **影响范围：** 管理员执行日常运维命令（`mcli admin user svcacct disable` + `enable`，或不带 `--policy` 的 `svcacct edit` / `idp ldap accesskey edit`）时，会在本站点及多站点复制对端上静默抹除服务账号的内联策略，使最小权限密钥（如仅允许读取单一路径前缀 `s3:GetObject` 的密钥）直接获得父用户的全量读写权限。
- **历史溯源：** 源自上游 MinIO 2022 年 5 月提交 [`f0462322f`](https://github.com/pgsty/silo/commit/f0462322fd9944f03ad65ac67897cc76469b4e88)（`minio/minio#14847`），并经 2023 年 10 月 [`33322e663`](https://github.com/pgsty/silo/commit/33322e6638b00869d00a2397084a6e8a87e1e0f6)（`minio/minio#18346`）与 2024 年 9 月 [`5bd27346a`](https://github.com/pgsty/silo/commit/5bd27346ac5518bb8a47f176ae930cf6741be615)（`minio/minio#20432`）延续至今。
- **修复方式：** 提交 [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27)（[PR #331](https://github.com/pgsty/silo/pull/331)）将 `opts.sessionPolicy == nil`（请求未涉及策略变更，保留原内联策略）与非 `nil` 的空策略结构体（`Version == ""` 且 `len(Statements) == 0`，显式清除内联策略）严格区分；JSON 字面量 `null` 视为未传策略。

---

## 一、问题的发现 {#discovery}

我们核对了 `pgsty/silo`、`pgsty/mc`、`pgsty/silo-console` 与 `pgsty/silo-pkg` 下的全部 GitHub 私密安全报告（`GHSA-*`）与公开 Issue：本问题并非来自外部提交的 GHSA 报告，而是于 2026 年 11 月 10 日在对 [SILO Server 20261109](/zh/blog/release/silo-20261109/) 开展内部发布后深度安全审查（与私密 GHSA 队列复核同步进行）时由维护团队检出并端到端复现。

具体而言，在审查 `Server 20261109` 为修复缓存写回竞态（[#320](https://github.com/pgsty/silo/issues/320)、[#321](https://github.com/pgsty/silo/issues/321)）而抽出的持久化凭据更新函数 `updatedServiceAccountCredentials`（`cmd/iam-store.go`）时，我们排查了部分字段更新（partial update）对 `opts.sessionPolicy` 的影响。在 `Server 20261026` 与 `Server 20261109` 上的实机测试确认：在拥有 `readwrite` 权限的父用户下创建一个仅允许 `s3:GetObject` 的只读服务账号后，只要依次执行 `mcli admin user svcacct disable` 与 `mcli admin user svcacct enable`（不带 `--policy`），该服务账号即可立即执行此前被拒绝的 `PutObject` 与 `DeleteObject`。

### 关于 `svcacct info` 输出的核实与订正 {#info-output}

早期内部排查摘要曾写有“状态切换后 `svcacct info` 仍显示 `inline`”。经核对源码与实机输出，准确的可观测行为如下：

1. **`svcacct info` 的实际显示：** 服务端 `InfoServiceAccount`（`cmd/admin-handlers-users.go`）计算 `ImpliedPolicy := sessionPolicy == nil || (sessionPolicy.Version == "" && len(sessionPolicy.Statements) == 0)`，客户端 `mcli admin user svcacct info`（`cmd/admin-user-svcacct-add.go`）在 `ImpliedPolicy == false` 时输出 `Policy: embedded`，在 `ImpliedPolicy == true` 时输出 `Policy: implied`。内联策略被清空后，`svcacct info` 实际上会如实变为 `Policy: implied`（同时 `svcacct info --policy` 会输出父用户的合并策略）。
2. **为什么该提权在日常运维中具有隐蔽性：** 无论是 `mcli admin user svcacct disable`、`enable`，还是仅指定 `--secret-key`、`--name`、`--description` 或 `--expiry` 的 `svcacct edit`，命令执行成功时仅输出 `Disabled/Enabled/Edited service account '...' successfully`，全程没有任何关于策略被重置的提示。运维人员在故障排查或窗口维护期间临时停用再启用某个受限密钥，或定期轮换其 Secret Key 时，不会意识到该命令已经静默抹除了密钥的权限边界。

---

## 二、溯源与根因 {#provenance}

### 服务账号内联策略的存储与鉴权机制 {#storage-model}

在内置 IAM 存储中，服务账号作为一条 `UserIdentity` 记录保存，其 `Credentials.SessionToken` 是一个由服务端签名的 JWT，通过两项声明（Claims）记录策略状态：

- **受限内联模式（`embedded-policy`）：** 当创建或更新服务账号并附带非空内联策略时，服务端将策略 JSON 进行 Base64 编码后存入 `sessionPolicy` 声明，并将 `sa-policy-type` 设为 `"embedded-policy"`。在 S3 或 Admin 接口鉴权时，`IsAllowedServiceAccount`（`cmd/iam.go`）要求请求**同时通过**父用户策略与内联策略的检查（`isAllowedSP && parentAllowed`，即取交集）。
- **继承父用户模式（`inherited-policy`）：** 当服务账号未附加内联策略时，JWT 中不包含 `sessionPolicy` 声明，`sa-policy-type` 设为 `"inherited-policy"`。此时 `IsAllowedServiceAccount` 仅评估父用户（及其所属用户组）绑定的策略。

### 处理器与存储层对“未传策略”和“清空策略”的双重折叠 {#two-layer-collapse}

管理接口 `POST /minio/admin/v3/update-service-account` 接收加密后的 `madmin.UpdateServiceAccountReq` JSON 结构：

```go
type UpdateServiceAccountReq struct {
    NewPolicy      json.RawMessage `json:"newPolicy,omitempty"`
    NewSecretKey   string          `json:"newSecretKey,omitempty"`
    NewName        string          `json:"newName,omitempty"`
    NewDescription string          `json:"newDescription,omitempty"`
    NewStatus      string          `json:"newStatus,omitempty"`
    NewExpiration  *time.Time      `json:"newExpiration,omitempty"`
}
```

在提交 [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) 之前，HTTP 处理器与 IAM 存储层将三种不同语义的输入——(a) 请求未包含 `newPolicy` 字段、(b) `"newPolicy": null`、以及 (c) 显式传入空策略文档（如 `{"Statement":[]}`）——折叠成了同一个 `nil` 指针：

1. **HTTP 处理器层（`cmd/admin-handlers-users.go` 中的 `(adminAPIHandlers).UpdateServiceAccount`）：**
   ```go
   var sp *policy.Policy
   if len(updateReq.NewPolicy) > 0 {
       sp, err = policy.ParseConfigStrict(bytes.NewReader(updateReq.NewPolicy))
       if err != nil {
           writeErrorResponseJSON(ctx, w, toAdminAPIErr(ctx, err), r.URL)
           return
       }
       if sp.Version == "" && len(sp.Statements) == 0 {
           sp = nil
       }
   }
   ```
   当请求未带 `NewPolicy`（`len == 0`）时，`sp` 为 `nil`；当客户端显式传入空策略文档（`{}` 或 `{"Statement":[]}`）以清除内联策略时，`ParseConfigStrict` 解析得到 `&policy.Policy{Version: "", Statements: nil}`，随后第 895 行的判断又将其重新置回 `sp = nil`。

2. **IAM 存储层（`cmd/iam-store.go` 中的 `updatedServiceAccountCredentials`）：**
   ```go
   nosp := opts.sessionPolicy == nil || opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0

   // sessionPolicy is nil and there is embedded policy attached we remove
   // embedded policy at that point.
   if _, ok := m.Lookup(policy.SessionPolicyName); ok && nosp {
       m.Delete(policy.SessionPolicyName)
       m.Set(iamPolicyClaimNameSA(), inheritedPolicyType)
   }
   ```
   由于 `opts.sessionPolicy == nil` 时 `nosp` 直接为 `true`，任何未携带 `newPolicy` 的更新请求都会进入该分支，从 JWT 声明 `m` 中删除 `sessionPolicy`，将 `sa-policy-type` 改写为 `"inherited-policy"`，并用 Secret Key 重新签发 `cr.SessionToken`。

### 上游 Git 演进链路 {#upstream-history}

回溯 `cmd/iam-store.go` 与 `cmd/admin-handlers-users.go` 的提交历史，该缺陷完整继承自上游 `minio/minio` 2022 年的改动：

| 时间    | 提交记录                                                                                                      | 来源仓库                   | 变更内容                                                                                                                                                               |
| :------ | :------------------------------------------------------------------------------------------------------------ | :------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2022-05 | [`f0462322f`](https://github.com/pgsty/silo/commit/f0462322fd9944f03ad65ac67897cc76469b4e88)（`minio#14847`） | 上游 MinIO                 | 为解决 `minio#14784`（支持移除服务账号的内联策略），在 `opts.sessionPolicy == nil` 时直接删除 `sessionPolicy` 并设为 `inherited-policy`，把“未传策略”当成了“清空策略”  |
| 2023-10 | [`33322e663`](https://github.com/pgsty/silo/commit/33322e6638b00869d00a2397084a6e8a87e1e0f6)（`minio#18346`） | 上游 MinIO                 | 在 `UpdateServiceAccount` 处理器中把解析出的空策略（`sp.Version == "" && len(sp.Statements) == 0`）折叠为 `sp = nil`，并在 `InfoServiceAccount` 中引入 `ImpliedPolicy` |
| 2024-09 | [`5bd27346a`](https://github.com/pgsty/silo/commit/5bd27346ac5518bb8a47f176ae930cf6741be615)（`minio#20432`） | 上游 MinIO                 | 在存储层写出 `nosp := opts.sessionPolicy == nil \|\| opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0`，但保留了处理器层的 `sp = nil` 折叠  |
| 2026-09 | [`59989f8`](https://github.com/pgsty/mc/commit/59989f8a0ddf81d9a20329bd411ddf2bed7bbb6c)（`pgsty/mc#27`）     | PGSTY `mcli`（`20260903`） | 在客户端侧明确约定：通过 `mcli admin user svcacct edit --policy` 传入空文档（如 `{"Statement":[]}`）是清除内联策略的显式方式                                           |
| 2026-11 | [`a0de92fcb`](https://github.com/pgsty/silo/commit/a0de92fcb)（`pgsty/silo#321`）                             | PGSTY SILO（`20261109`）   | 将凭据更新逻辑抽为 `updatedServiceAccountCredentials` 以直接基于持久化记录执行修改，原样保留了上游的 `nosp` 判定                                                       |
{.wide .expand}

---

## 三、触发条件 {#triggers}

同时满足以下三项条件即可触发内联策略被清空：

1. **目标账号带有内联会话策略：** 目标凭据是当前处于 `sa-policy-type: "embedded-policy"` 状态的服务账号（或 LDAP / OpenID 访问密钥），其内联策略将权限收窄为父用户权限的子集。
2. **调用方具备管理该服务账号的权限：** 请求由持有 `admin:UpdateServiceAccount` 权限的管理员，或管理自身名下服务账号的父用户发起。（受限服务账号自身无法调用该接口给自己提权，[`CVE-2025-62506`](/zh/blog/security/cve-2025-62506/) 与 [`SN-2026-017`](/zh/about/security-advisories/#sn-2026-017) 已拦截派生凭据的自我提权。）
3. **更新请求未携带新策略：** 执行以下任意日常操作时，客户端发出的 `UpdateServiceAccountReq` 不包含 `newPolicy`（或 `newPolicy` 为 `null`）：
   - **状态切换（禁用/启用）：** `mcli admin user svcacct disable ALIAS ACCESSKEY` 或 `mcli admin user svcacct enable ALIAS ACCESSKEY`（以及对应的 `mcli admin accesskey disable/enable` 和 `mcli idp ldap accesskey disable/enable`）。
   - **不带 `--policy` 的密钥轮换或元数据修改：** 使用 `mcli admin user svcacct edit`（或 `set`）修改 `--secret-key`、`--name`、`--description` 或 `--expiry` 时未同时传入 `--policy`（含 `idp ldap accesskey edit` 同类命令）。
   - **多站点复制对端同步：** 当管理员对非 root 用户的服务账号执行上述任一修改时，`IAMChangeHook` 会向复制对端转发 `SessionPolicy` 为空的 `SRSvcAccUpdate`；对端 `PeerSvcAccChangeHandler`（`cmd/site-replication.go`）以 `sp = nil` 调用 `UpdateServiceAccount`，在所有复制站点上同步抹除内联策略。

---

## 四、影响范围 {#impact}

| 评估维度             | 具体影响说明                                                                                                                                                                                                          |
| :------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **权限边界越界放大** | 服务账号立即失去内联 `sessionPolicy` 的交集过滤限制，直接继承父用户及其所属用户组关联的全部 S3 数据权限与 Admin 管理权限。                                                                                            |
| **受影响的身份类型** | 内置 IDP 服务账号、AD/LDAP 访问密钥（`idp ldap accesskey`）以及挂靠在 OpenID 用户下的服务账号（无论底层使用 `.minio.sys/iam/` 对象存储还是 `etcd`）。临时 STS 凭据（`AssumeRole*`）走独立的不可变令牌路径，不受影响。 |
| **多站点复制扩散**   | 只要服务账号的父用户不是集群 root 账户（`svcAccount.ParentUser != globalActiveCred.AccessKey`），不带策略的编辑操作会复制至所有对端站点，在对端同样清空内联策略。（root 用户的服务账号不参与跨站复制。）              |
| **策略丢失不可逆**   | `m.Delete(policy.SessionPolicyName)` 会将内联策略从持久化的 `SessionToken` JWT 中抹除并重新签名落盘。升级服务端二进制可阻止后续编辑再次抹除策略，但无法自动找回升级前已被抹除的策略内容。                             |
{.wide .expand}

---

## 五、修复方案及其充分性与必要性 {#fix}

提交 [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27)（[PR #331](https://github.com/pgsty/silo/pull/331)）在 `cmd/admin-handlers-users.go` 与 `cmd/iam-store.go` 两处共修改 18 行代码：

```go
// cmd/admin-handlers-users.go — (adminAPIHandlers).UpdateServiceAccount
// A request without a policy, or with a JSON null for one, keeps the
// policy the account has. An empty policy document is passed on as
// such: it is the request to remove the embedded policy.
var sp *policy.Policy
if len(updateReq.NewPolicy) > 0 && !bytes.Equal(updateReq.NewPolicy, []byte("null")) {
    sp, err = policy.ParseConfigStrict(bytes.NewReader(updateReq.NewPolicy))
    if err != nil {
        writeErrorResponseJSON(ctx, w, toAdminAPIErr(ctx, err), r.URL)
        return
    }
}
```

```go
// cmd/iam-store.go — updatedServiceAccountCredentials
// A nil sessionPolicy is an edit that does not concern the policy, and
// the embedded one stays. Only a policy that was given, and is empty,
// removes it: the account then has all its parent is allowed, which is
// usually more.
reset := opts.sessionPolicy != nil && opts.sessionPolicy.Version == "" && len(opts.sessionPolicy.Statements) == 0
if _, ok := m.Lookup(policy.SessionPolicyName); ok && reset {
    m.Delete(policy.SessionPolicyName)
    m.Set(iamPolicyClaimNameSA(), inheritedPolicyType)
}
```

对于原本带有内联策略 `P` 的服务账号，修复前后的状态转换对比如下：

| 请求中的 `newPolicy`                           | 解析后的 `opts.sessionPolicy`                                | 修复前行为                 | 修复后行为（`c11bfda8f`）       |
| :--------------------------------------------- | :----------------------------------------------------------- | :------------------------- | :------------------------------ |
| 未携带（`len == 0`）                           | `nil`                                                        | 清空 `P`（变为 `implied`） | **保留 `P`（保持 `embedded`）** |
| JSON 字面量 `null`                             | `nil`                                                        | 清空 `P`（变为 `implied`） | **保留 `P`（保持 `embedded`）** |
| `{}` 或 `{"Statement":[]}` 或 `{"Version":""}` | 非 `nil` 空结构 `&policy.Policy{Version:"", Statements:nil}` | 清空 `P`（变为 `implied`） | **清空 `P`（变为 `implied`）**  |
| 合法非空策略 `P'`                              | 非 `nil` `&policy.Policy{...}`                               | 替换为 `P'`                | **替换为 `P'`**                 |
| 非法 JSON（`""`、`[]`、`0`、非法 ARN 等）      | 解析报错（HTTP `400`）                                       | 拒绝请求（保留 `P`）       | **拒绝请求（保留 `P`）**        |
{.wide .expand}

### 为什么该修改是必要的 {#necessary}

1. **在处理器与存储层解耦“未指定”与“显式清空”：** 在线协议（`UpdateServiceAccountReq`）中，`disable`/`enable` 状态切换以及仅修改密钥、名称、描述或过期时间的请求均不携带 `newPolicy`。只要处理器把空策略文档折叠成 `sp = nil`、或者存储层把 `opts.sessionPolicy == nil` 当作重置条件，服务端就无法在不破坏“显式清空内联策略”功能的前提下保留已有策略。移除处理器层的 `sp = nil` 折叠并在存储层要求 `opts.sessionPolicy != nil` 才触发 `reset`，是区分这两种语义的最小必要修改。
2. **为什么必须显式特判 `"null"`：** `UpdateServiceAccountReq.NewPolicy` 的类型为 `json.RawMessage`（即 `[]byte`）。当调用方在 JSON 中发送 `"newPolicy": null`，或站点复制的 `SRSessionPolicy`（底层同样为 `json.RawMessage`）将 `nil` 序列化为线上字面量 `null` 时，Go 标准库 `encoding/json` 会去除外围空白并将 4 字节切片 `[]byte("null")` 赋给 `NewPolicy`。而 `policy.ParseConfigStrict` 内部调用的 `json.NewDecoder(...).Decode(&p)` 在遇到 JSON `null` 时不会报错，而是直接返回一个非 `nil` 的零值 `&policy.Policy{}`。若不在处理器入口排除 `bytes.Equal(updateReq.NewPolicy, []byte("null"))`，`"newPolicy": null` 仍会被误判为显式空策略并触发清空。

### 为什么该修改是充分的 {#sufficient}

1. **单一存储层收口覆盖全部后端与入口：** 无论是 `.minio.sys/iam/` 对象存储后端还是 `etcd` 后端，所有针对存量服务账号的本地修改与复制修改最终都汇聚到 `updatedServiceAccountCredentials`（`cmd/iam-store.go`）这一处函数。其余路径均不会意外改写存量服务账号的 `SessionToken` 策略声明：`AddServiceAccount` 已拒绝覆盖已存在的 Access Key（[#322](https://github.com/pgsty/silo/issues/322)），LDAP 组刷新仅更新组映射，STS 临时凭据使用独立的不可变路径。
2. **站点复制对端无需改动协议即可天然适配：** 在 `PeerSvcAccChangeHandler`（`cmd/site-replication.go`）中，`sp` 默认初始化为 `nil`，仅当 `len(u.SessionPolicy) > 0` 时才解析策略。当源站转发不带策略的编辑时，线上 `SessionPolicy` 反序列化后为空切片，对端将 `sessionPolicy: nil` 传入 `UpdateServiceAccount` 并保留内联策略；当源站转发 `{}` 或 `{"Statement":[]}` 时，对端解析出非 `nil` 的空 `&policy.Policy{}` 并正常清除内联策略。
3. **权限单调性保证：** 内置 IAM 将内联策略按交集 `isAllowedSP && parentAllowed` 求值（`cmd/iam.go:2343`）。由于本次修改仅改变了 `newPolicy` 缺省与 `null` 两种输入的行为（由删除内联过滤改为保留内联过滤），在任何请求序列下，修复后的服务端赋予服务账号的权限都不会大于修复前。

---

## 六、设计取舍与利弊权衡 {#tradeoffs}

| 设计议题                                                                                | `c11bfda8f` 采纳的方案                                                              | 收益                                                                                                 | 代价与运维边界                                                                                                                             |
| :-------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------- | :--------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| **如何区分“保留内联策略”与“清空内联策略”**                                              | `nil`/`null` 表示保持不变；显式传入空策略文档（`{}` 或 `{"Statement":[]}`）表示清空 | 无需改动线协议或 `madmin-go` 结构体；已发布的 `mcli admin user svcacct edit --policy` 原生支持该用法 | 此前依赖“不传 `newPolicy` 来清空策略”的自定义 API 客户端需改为发送 `{}` 或 `{"Statement":[]}`                                              |
| **SILO Console v2.7.0 策略编辑器清空保存的行为**                                        | 保持服务端严格语义（Console 将空白编辑器归一化为不传 `newPolicy`，因此保留原策略）  | 消除误清空风险，在 Console 跟进前按 Fail-Closed（保留限制）运行                                      | 在 Console v2.7.0 中删空策略文本框并保存不再清除内联策略；需在编辑器中输入 `{}` 或 `{"Statement":[]}` 才能清除（Console 将在后续版本跟进） |
| **带版本号的空语句策略（`{"Version":"2012-10-17","Statement":[]}`）及无版本号非空策略** | 在本次热修中保持既有更新无操作（no-op）语义不变                                     | 避免破坏 Console 保存继承型（`implied`）账号时的既有流程                                             | 更新时提交不含 `"Version"` 但含 `Statement` 的策略仍会静默忽略并返回 `204`；作为独立校验项跟进                                             |
| **站点复制既有的补丁乱序丢弃与缓存/存储混合读取缺陷**                                   | 将 `c11bfda8f` 严格控制在 18 行本地/对端语义修复；快照复制重构拆分为独立提交        | 保证安全热修最小化、易评审且可无损回滚，不在同一提交中混入复制协议重构                               | 需通过后续独立提交将服务账号复制改为发送完整存储记录快照（`SRSvcAccCreate`），以彻底消除跨站并发/乱序补丁导致的策略或密钥分歧              |
{.wide .expand}

### 为什么不顺手修改另外两种边缘策略形态与复制快照机制 {#boundaries}

在对 [PR #331](https://github.com/pgsty/silo/pull/331) 的对抗式代码审查中，我们重点评估了以下两项相邻问题，并决定将它们与本次 18 行热修解耦：

1. **为什么不在本次提交中改动 `{"Version":"2012-10-17","Statement":[]}` 与“无 `Version` 但有语句”的策略更新行为？**
   在 `updatedServiceAccountCredentials` 中，覆写内联策略的条件为 `if opts.sessionPolicy.Version != "" && len(opts.sessionPolicy.Statements) > 0`。因此在更新存量服务账号时：
   - 传入 `{"Version":"2012-10-17","Statement":[]}` 既不会触发 `reset`（因为 `Version != ""`），也不会覆写原策略（因为 `len(Statements) == 0`），表现为无操作（no-op）。如果在本次热修中将其改为作为内联空策略嵌入（即全拒绝），会导致 Console 在编辑并保存某些父用户无直连策略的继承型密钥时将其锁死；而在已有 `{}` 与 `{"Statement":[]}` 作为明确重置方式的前提下，也无需再增加新的重置变体。
   - 传入不含 `"Version"` 字段但包含 `Statement` 的策略时，`AddServiceAccount`（创建）会接受并嵌入，但 `UpdateServiceAccount`（更新）会静默忽略并返回 `204`。这属于“收紧权限未生效”的易用性隐患，不会放大已有受限账号的权限，宜在独立提交中统一收口。

2. **为什么不把“站点复制改为完整快照”并入本次提交？**
   对抗式审查确认了站点复制中两项独立于本漏洞的既有缺陷：(a) `UpdateServiceAccount` 按字段补丁（`SRSvcAccUpdate`）转发修改，若对端先收到较晚的描述修改（时间戳 $t_2$），后收到较早的策略或密钥修改（$t_1 < t_2$），对端的时间戳检查会丢弃迟到的 $t_1$ 补丁；(b) 初次同步、自愈与 IAM 导出在构造快照时混合读取了持久化记录的 `UpdatedAt` 与节点内存缓存中的策略声明。修复这两项缺陷需要将服务账号复制统一改为从持久化记录构造完整快照（`SRSvcAccCreate`）。将 `c11bfda8f` 严格限定在 18 行 `nil` 与空策略区分上，可使单站点与多站点集群立即阻止日常命令引发的策略抹除，而站点复制快照化则作为独立交付项单独评审与合入。

---

## 升级指引与排查建议 {#remediation}

1. **升级全部 SILO Server 节点与复制站点：** 请将所有节点升级至包含提交 [`c11bfda8f`](https://github.com/pgsty/silo/commit/c11bfda8f48153d6bc42b6eeee4a9fb39bcffd27) 的 `20261109` 后续热修版本（或基于 [`244de7ecc`](https://github.com/pgsty/silo/commit/244de7ecc1ce33f4f3e7ec452395993eb2449f11) 及之后的 `main` 主干构建）。在多站点复制部署中，未升级的对端站点在收到不带策略的更新时仍会清空内联策略，因此必须完成全站点协同升级。
2. **升级后逐站排查存量服务账号：** 由于代码修复无法恢复升级前已被抹除的内联策略，请在全部站点升级完成后，逐站检查所有服务账号，核对本应受限的账号是否显示为 `Policy: implied`：
   ```shell
   mcli admin user svcacct list myminio/ <username>
   mcli admin user svcacct info myminio/ <access-key>
   ```
   凡是原本设计为最小权限受限账号、但当前显示 `Policy: implied` 的服务账号，请重新下发其内联策略文档（或直接轮换重建带 `--policy` 的新密钥）：
   ```shell
   mcli admin user svcacct edit myminio/ <access-key> --policy /path/to/restricted-policy.json
   ```
3. **显式清空内联策略的操作方法：**
   - **使用 `mcli`：** 向 `--policy` 传入空策略文档（`{}` 或 `{"Statement":[]}`）：
     ```shell
     mcli admin user svcacct edit myminio/ <access-key> --policy /path/to/empty-policy.json
     ```
   - **使用 SILO Console v2.7.0：** 在访问密钥的策略编辑器中输入 `{}` 或 `{"Statement":[]}` 并保存（直接清空文本框并保存现在会保留原有内联策略）。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-021)、[`mcli admin user svcacct edit` 命令参考](/zh/reference/minio-mc-admin/mc-admin-user-svcacct-edit/)与[组件版本矩阵](/zh/compatibility/versions/)。
