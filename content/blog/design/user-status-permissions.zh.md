---
title: "一个端点，两种权限：彻底分离用户与组状态"
linkTitle: "用户与组状态权限"
date: 2026-08-26
lastmod: 2026-08-28
author: "冯若航"
summary: >
  用户与组状态端点过去即使处理禁用请求，也固定检查各自的 Enable action。本文记录最小权限缺陷、SILO 基于目标状态严格选权的设计、通过 PR #73 合并的用户修复、后续组修复、四向 IAM 测试，以及代码提交与版本交付之间的边界。
tags: [设计, IAM, 安全, 兼容性]
weight: 15
draft: false
url: "/zh/blog/design/user-status-permissions/"
---

本文完整记录 [上游 issue minio/minio#21478](https://github.com/minio/minio/issues/21478) 与 [SILO PR #73](https://github.com/pgsty/silo/pull/73) 的讨论、修复过程和最终鉴权设计。

> **截至 2026-08-26 的状态：** SILO PR #73 已合并为 [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5)，并保留带 DCO sign-off 的修复提交 [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1)；八项远端检查全部通过。上游 #21478 与 PR #21482 仍显示 open，但 `minio/minio` 已归档为只读仓库，无法继续评论或合并。<br>
> **2026-08-28 组权限善后：** 最终发布审查发现 `set-group-status` 存在同样的固定 action 问题。带 sign-off 的服务器提交 `d98250110` 现已根据目标状态选择 `admin:EnableGroup` 或 `admin:DisableGroup`，并加入真实四向 IAM 鉴权测试。本地验证与独立评审完成；push、远端 CI、merge、tag 与交付仍待后续。<br>
> **本轮范围：** 分别使用已有的两个 Admin Action 鉴权用户启用与禁用；不修改路由、状态值、账户存储、复制记录或客户端 API。<br>
> **安全属性：** 持有 `admin:DisableUser` 不能因此获得启用账户的能力，持有 `admin:EnableUser` 也不能因此获得禁用账户的能力。<br>
> **发布边界：** merge、tag、release package、container image、deployment 与 production verification 仍是相互独立的门槛。

## 太长不看（TL;DR） {#tldr}

SILO 同时提供 `admin:EnableUser` 与 `admin:DisableUser`，但共用的 `set-user-status` handler 过去无论目标状态是什么，都只检查 `admin:EnableUser`。因此，只授予 `admin:DisableUser` 的策略反而无法禁用账户；想让它工作，就必须额外授予 `admin:EnableUser`，等于主动破坏这两个 action 承诺的最小权限边界。

最终修复在鉴权前，根据请求的目标状态选择且只选择一个 action：

| 请求状态 | 必须具备的 action |
| --- | --- |
| `enabled` | `admin:EnableUser` |
| `disabled` | `admin:DisableUser` |
| 非法或未知值 | `admin:EnableUser`，保留原有“先鉴权、后校验”的默认边界 |

随后 handler 只调用一次 `validateAdminReq`。四向 IAM 集成测试同时证明两个允许路径与两个交叉拒绝路径。这个选择刻意比“兼容 Enable-only 策略过去也能禁用用户”的方案更严格，因为那种历史能力本身就是本次要修复的鉴权错误。

同一规则现在也适用于组状态：

| 请求的组状态 | 必须具备的 action |
| --- | --- |
| `enabled` | `admin:EnableGroup` |
| `disabled` | `admin:DisableGroup` |
| 非法或未知值 | `admin:EnableGroup`，保留原有“先鉴权、后校验”的默认边界 |

善后修复前，只有 EnableGroup 的 principal 可以禁用组，只有 DisableGroup 的 principal 反而会在执行禁用时收到 `AccessDenied`。组修复沿用“一个 selector、一次鉴权”的设计，不把两个 action 当成别名。

## 被报告的问题 {#defect}

Admin API 用同一个路由处理两个方向的状态变化：

```text
PUT /minio/admin/v3/set-user-status
    ?accessKey=<target>
    &status=enabled|disabled
```

修复前，handler 在读取目标状态之前，就固定检查一个 action：

```go
objectAPI, creds := validateAdminReq(ctx, w, r, policy.EnableUserAdminAction)
```

后面的 `SetUserStatus` 虽然会正确接收 `enabled` 或 `disabled`，鉴权却已经把两种操作都当成 Enable。于是，`admin:DisableUser` 明明存在于策略词汇和公开文档中，却无法独立授权这个端点。

#21478 给出了真实反例：操作员希望在事件处置期间拥有“只能禁用、不能恢复账户”的策略。策略只包含 `admin:DisableUser` 时会收到 `AccessDenied`；加上 `admin:EnableUser` 后禁用才能成功，但操作员也同时获得了策略原本刻意不授予的恢复权限。

这不是少了一个便利权限，而是策略模型与执行点错位：

```text
策略表达：      仅 DisableUser
请求表达：      目标状态 = disabled
Handler 检查：  EnableUser
结果：          合法禁用被拒绝
临时绕过：      额外授予不需要的启用能力
```

## 为什么两个 action 必须代表两种能力 {#policy-contract}

账户状态变化具有方向性。禁用通常可以委派给事件响应人员、反欺诈控制、合规自动化或 break-glass 流程；重新启用意味着恢复访问，完全可能要求另一位审批者。

如果任意一个 action 都能授权两个方向，策略作者就无法表达这种职责分离。服务器表面上公布两个名字，实际却只执行一个合并能力。因此最终契约必须严格：

| Principal 策略 | 禁用目标 | 启用目标 |
| --- | --- | --- |
| 仅 `admin:DisableUser` | 允许 | 拒绝 |
| 仅 `admin:EnableUser` | 拒绝 | 允许 |
| 两者都有 | 允许 | 允许 |
| 两者都没有 | 拒绝 | 拒绝 |

内置 `consoleAdmin` 授予 `admin:*`，完整管理员仍然拥有两个操作。兼容性影响仅限于曾经依赖错误行为的自定义受限策略。

公开 PBAC 参考现在也为 [`admin:EnableUser`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-EnableUser) 与 [`admin:DisableUser`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-DisableUser) 明确写入同一契约。

## 设计目标与非目标 {#scope}

### 设计目标 {#goals}

1. 让两个现有 Admin Action 按照各自名字真正生效；
2. 在两个方向上都满足最小权限；
3. 每个请求只做一次鉴权决策，最多写出一次鉴权错误；
4. 保持路由、请求值、响应格式、自操作保护、IAM 存储调用和站点复制 hook 不变；
5. 用测试锁死契约，防止两个权限再次被扩宽、合并或调换。

### 非目标 {#non-goals}

- 把端点拆成单独的 enable 与 disable 路由；
- 增加新的合并 action 或改变策略语法；
- 修改用户状态持久化或复制机制；
- 重新设计 Console 权限；
- 把 source merge 推断为 release、镜像、部署或生产交付。

## 讨论过但没有采用的方案 {#alternatives}

### 两种状态继续只检查 `admin:EnableUser` {#always-enable}

这能维持旧行为，却继续让 `admin:DisableUser` 失效，并迫使策略过度授权。它就是问题本身，不是值得保留的兼容契约。

### 任一状态都同时要求两个 action {#require-both}

这样两个名字只剩装饰作用，也无法委派 disable-only 操作。它在权限数量上更严格，却在表达能力和最小权限上更差。

### Enable 鉴权失败后，再尝试 Disable 鉴权 {#double-validation}

上游 PR #21482 对禁用请求采用了类似形态：先用 `EnableUser` 调用 `validateAdminReq`，结果为 nil 时再用 `DisableUser` 调用一次。

这个 helper 有一条关键契约：返回 nil object layer 时，它已经向响应写入错误。于是 Disable-only 请求可能先提交 403，第二次鉴权又成功，随后 handler 继续修改账户状态。鉴权 fallback 绝不能在错误响应已经提交后继续执行 mutation。

### 禁用请求接受 Enable 或 Disable 任一个 action {#allow-either}

`validateAdminReq` 本身支持多个 action，只要其中一个允许就成功。因此，如果目标是兼容旧行为，可以通过单次 variadic 调用安全实现：让 Disable-only 策略开始工作，同时保留 Enable-only 策略也能禁用用户的历史能力。

SILO 没有选择它，因为那项历史能力正是鉴权错误。它只能修复报告者的正向用例，却继续保留与双 action 模型冲突的交叉权限。需要完整账户生命周期的角色应显式授予两个 action。

### 先校验 status，再进行鉴权 {#validate-first}

先拒绝未知状态会改变错误优先级：过去必须先通过 Enable 鉴权门槛的调用者，现在可能在鉴权前得到参数校验结果。本次修复不需要扩大行为变化。

因此未知值继续采用 `admin:EnableUser` 作为默认鉴权 action；只有合法的 `disabled` 会选择 `admin:DisableUser`。通过鉴权后，仍由既有 IAM 路径拒绝非法状态值。

## 最终实现 {#implementation}

修复增加一个纯选择函数：

```go
func setUserStatusAdminAction(status string) policy.AdminAction {
    if madmin.AccountStatus(status) == madmin.AccountDisabled {
        return policy.DisableUserAdminAction
    }
    return policy.EnableUserAdminAction
}
```

Handler 先读取路由变量，选择 action，然后只鉴权一次：

```go
vars := mux.Vars(r)
accessKey := vars["accessKey"]
status := vars["status"]

objectAPI, creds := validateAdminReq(ctx, w, r, setUserStatusAdminAction(status))
if objectAPI == nil {
    return
}
```

鉴权门之后的逻辑完全不变：

- 调用者仍不能启用或禁用自己的账户；
- `globalIAMSys.SetUserStatus` 继续校验并持久化目标状态；
- 站点复制继续记录同一状态和更新时间；
- 响应与审计仍走已有路径。

选择函数只依赖请求明确给出的目标状态。它不会读取当前用户，不会根据存储状态猜测 transition，也不会让鉴权结果取决于目标是否存在。这样既保证鉴权确定性，也避免在鉴权前引入读取依赖。

## 为什么这个修复是安全的 {#safety}

正确性由五条不变量组成：

1. 每个合法状态只映射到一个 Admin Action；
2. `validateAdminReq` 只调用一次，鉴权失败后不可能继续 mutation；
3. 只有选定 action 鉴权成功，状态修改调用才可达；
4. 非法状态保留旧的 Enable 鉴权边界，之后仍由已有状态校验路径拒绝；
5. 存储、复制、wire 与 client contract 都不改变，变化的只有进入既有 mutation 所需的权限。

对于曾经用 Enable-only 自定义策略执行禁用操作的调用者，这是一项有意的鉴权收紧。也正是这项收紧，才让 `admin:DisableUser` 成为真正独立的能力。

## 测试设计 {#tests}

### 纯 action 映射 {#mapping-test}

单元测试锁定三个选择结果：

| 输入 | 期望 action |
| --- | --- |
| `enabled` | `EnableUser` |
| `disabled` | `DisableUser` |
| 非法值 | 旧的 `EnableUser` 默认值 |

### 四向 IAM 鉴权矩阵 {#iam-test}

集成测试创建彼此独立的用户和策略，再通过真实 Admin API 执行：

1. Disable-only client 可以成功禁用目标；
2. 同一 client 尝试启用目标时得到 `AccessDenied`；
3. Enable-only client 可以成功启用目标；
4. 同一 client 尝试禁用目标时得到 `AccessDenied`。

只检查两个正向用例不能证明最小权限：如果两个策略意外都能执行两个操作，正向测试仍会通过。两个交叉拒绝断言才是安全回归测试。

测试结束后会删除所有临时用户和策略。它运行在既有 IAM server suite 中，覆盖请求签名、策略挂载、handler 鉴权、状态持久化和 Admin client 错误解码，而不只是测试 helper。

## 修复与验证记录 {#verification}

服务端原工作树中混有依赖升级、生成的 credits、checksum 测试和安全文档修改，本地 `main` 也落后远端。两个用户状态文件因此被隔离到基于最新 `origin/main` 的干净 worktree；无关文件没有进入修复提交。

本地验证通过：

```text
go test ./cmd -run '^TestSetUserStatusAdminAction$' -count=1
go test ./cmd -run '^TestIAMInternalIDPServerSuite$' -count=1
git diff --check
```

带 sign-off 的 `58735ee38` 被推送到 PR #73，八项远端检查全部通过：

- DCO sign-off；
- format、build 与 vet；
- lint 与 generated files；
- `cmd/` tests；
- `internal/` tests；
- race detector 与 S3 Select；
- cross compile；
- vulnerability analysis。

PR 使用仓库常规 merge 策略合并为 `2e2377d1c`。随后只有在原工作树中的两个文件与远端合并结果通过逐字节比较、patch ID 也完全一致后，本地 `main` 才被 fast-forward。其余无关本地改动完整保留；代码已经可以从 `main` 与 PR #73 恢复后，临时 worktree 与任务分支才被删除。

## 最小权限策略示例 {#examples}

### 只能禁用的操作员 {#disable-only}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "admin:DisableUser",
        "admin:GetUser"
      ]
    }
  ]
}
```

该 principal 可以查看并禁用另一用户，但不能重新启用。

### 只能启用的操作员 {#enable-only}

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "admin:EnableUser",
        "admin:GetUser"
      ]
    }
  ]
}
```

该 principal 可以查看并启用另一用户，但不能禁用。负责完整账户生命周期的角色应显式授予两个 action。

## 组状态权限善后 {#group-follow-up}

组端点与用户端点具有相同结构：

```text
PUT /minio/admin/v3/set-group-status
    ?group=<target>
    &status=enabled|disabled
```

它也公开了 `admin:EnableGroup` 与 `admin:DisableGroup` 两个既有 action，但继承 handler 在读取 `status` 前固定用 `EnableGroup` 鉴权。这不是一个“没有用到的权限”而已，而是同时反转了两个方向的最小权限：不该拥有禁用能力的 principal 可以禁用，真正的 disable-only principal 却不能。

善后提交增加 `setGroupStatusAdminAction`，刻意与 `setUserStatusAdminAction` 同构：

```go
func setGroupStatusAdminAction(status string) policy.AdminAction {
    if madmin.GroupStatus(status) == madmin.GroupDisabled {
        return policy.DisableGroupAdminAction
    }
    return policy.EnableGroupAdminAction
}
```

集成测试创建相互独立的 EnableGroup-only、DisableGroup-only 管理员与真实目标组，证明：

1. DisableGroup-only 可以禁用；
2. DisableGroup-only 不能启用；
3. EnableGroup-only 可以启用；
4. EnableGroup-only 不能禁用。

测试覆盖签名 Admin 请求、策略挂载、handler 鉴权、IAM mutation、错误解码与清理。非法 status 仍先选择历史默认的 Enable action，再由既有逻辑返回校验错误，因此没有新增鉴权前信息泄漏。成功后的 site-replication hook 保持不变，被拒绝请求不会触发。

这个善后不改变用户状态行为，也没有新增 policy action；它只是让两个早已公开的组 action，执行与用户 action 相同的按目标状态严格选权契约。

## 兼容性与迁移 {#compatibility}

客户端和 API 都不需要迁移：endpoint、query parameter、status string、成功响应与 Admin client method 全部不变。

但受限管理员角色需要检查策略：

- 只负责禁用用户的角色需要 `admin:DisableUser`；
- 只负责启用用户的角色需要 `admin:EnableUser`；
- 两种操作都需要的角色必须同时授予两个 action；
- `consoleAdmin` 与其他 `admin:*` 策略不受影响；
- 旧的自定义策略若只包含 `admin:EnableUser`，将不能再借此禁用用户；确实需要两个操作时，应增加 `admin:DisableUser`。

组管理角色现在遵循完全对称的规则：

- 只负责禁用组的角色需要 `admin:DisableGroup`；
- 只负责启用组的角色需要 `admin:EnableGroup`；
- 两个方向都需要时，必须同时授予两个 action；
- 旧 EnableGroup-only 角色不能再借此禁用组。

这是 source-level 的鉴权行为兼容性变化，不是 wire-protocol break。

## 上游处置 {#upstream}

在本文记录时，上游 #21478 与 PR #21482 仍显示 open，但上游仓库已经归档为只读。我们尝试把“只做一次鉴权”的分析留在 PR 上，GitHub 因归档、锁定的讨论不能新增评论而拒绝了请求。

上游 issue 与 PR 仍然是有价值的来源证据，但已经不再是可执行的交付路径。SILO 必须独立拥有自己的语义、测试、merge、release note 与最终生产验证。

## 交付状态 {#delivery}

| 门槛 | 用户修复 | 2026-08-28 组善后 |
| --- | --- | --- |
| 设计决策 | 完成 | 完成 |
| 实现与本地测试 | 完成 | 完成 |
| 独立对抗评审 | 完成 | 完成，GO |
| 带 sign-off 的提交 | 完成 | 本地 `d98250110` |
| Push、PR CI 与 merge | 完成 | 尚未确认 |
| SILO tag | 尚未确认 | 尚未确认 |
| Release package 或 container image | 尚未确认 | 尚未确认 |
| 部署 | 尚未确认 | 尚未确认 |
| 生产行为 | 尚未确认 | 尚未确认 |
| 上游合并 | 不可用；仓库已归档 | 不适用 |

## 结论 {#conclusion}

这些修复让鉴权模型说真话。启用和禁用用户或组，都是风险方向相反的状态变化，SILO 也早已为每个方向提供不同 policy action；每个 handler 都应该从请求的目标状态选择 action，并在 mutation 前只鉴权一次。

代码很小，是因为设计边界足够清晰。真正需要长期保留的是更完整的结果：明确的权限矩阵、被否决的兼容方案、非法输入规则、四向集成测试、干净的合并证据、迁移指引，以及不把“已合并”误报成“已发布”的交付边界。
