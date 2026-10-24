---
title: "一个端点，两种权限：彻底分离用户与组状态"
linkTitle: "用户与组状态权限"
date: 2026-08-26
lastmod: 2026-09-16
author: "冯若航"
summary: >
  用户与组状态管理端点过去即使处理禁用请求，也固定检查各自的启用权限。本文记录最小权限缺陷、SILO 按目标状态严格选权的设计、PR #73 的用户状态修复、后续组状态修复、四向 IAM 矩阵测试与策略迁移指引。
tags: [设计, IAM, 安全, 兼容性]
weight: 15
draft: false
url: "/zh/blog/design/user-status-permissions/"
---

本文记录 [上游议题 minio/minio#21478](https://github.com/minio/minio/issues/21478)、[SILO PR #73](https://github.com/pgsty/silo/pull/73)（提交 [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1) / [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5)）以及 `set-group-status` 组状态权限善后提交（`229fe2b3c`）的鉴权设计与验证记录。上述修复已随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布。

## 太长不看（TL;DR） {#tldr}

SILO 同时定义了 `admin:EnableUser` 与 `admin:DisableUser` 两项策略权限，但共用的 `set-user-status` 处理函数过去无论目标状态是什么，都固定检查 `admin:EnableUser`。结果，仅授予 `admin:DisableUser` 的策略反而无法禁用账户；要想执行禁用，就必须额外授予 `admin:EnableUser`，直接打破了这两项权限的最小权限边界。

修复方案在鉴权前根据请求的目标状态映射出唯一对应的权限动作：

| 请求状态 | 必须具备的权限 |
| --- | --- |
| `enabled` | `admin:EnableUser` |
| `disabled` | `admin:DisableUser` |
| 非法或未知值 | `admin:EnableUser`，保留原有的“先鉴权、后校验”默认边界 |

随后处理函数仅调用一次 `validateAdminReq`。四向 IAM 集成测试同时验证了两条正向放行路径与两条交叉拒绝路径。这一设计不再允许“仅含 `admin:EnableUser` 的策略也能禁用用户”的历史行为，使两项权限各自严格对应单向操作。

相同的规则也同步应用于组状态端点：

| 请求的组状态 | 必须具备的权限 |
| --- | --- |
| `enabled` | `admin:EnableGroup` |
| `disabled` | `admin:DisableGroup` |
| 非法或未知值 | `admin:EnableGroup`，保留原有的“先鉴权、后校验”默认边界 |

修复前，仅持有 `admin:EnableGroup` 的调用方可以禁用组，而仅持有 `admin:DisableGroup` 的调用方在执行禁用时却会收到 `AccessDenied`。组状态修复同样采用“单一选择函数、单次鉴权调用”的结构。

## 被报告的问题 {#defect}

管理 API 使用同一个路由处理启用与禁用两种状态变更：

```text
PUT /minio/admin/v3/set-user-status
    ?accessKey=<target>
    &status=enabled|disabled
```

修复前，处理函数在读取目标状态参数之前就硬编码检查了启用权限：

```go
objectAPI, creds := validateAdminReq(ctx, w, r, policy.EnableUserAdminAction)
```

后续调用的 `SetUserStatus` 虽然能正确处理 `enabled` 或 `disabled`，但前置鉴权已经将两种操作一律视为启用。`admin:DisableUser` 虽存在于策略语法与公开文档中，却无法独立授权该端点。

议题 #21478 给出了典型的生产场景：安全运维人员在应急响应期间需要一份“只能禁用异常账户、不能恢复账户”的受限策略。然而仅配置 `admin:DisableUser` 时请求会返回 `AccessDenied`；补上 `admin:EnableUser` 后禁用才得以执行，但调用方也同时获得了本应受控的账户恢复权限：

```text
策略声明：      仅授予 DisableUser
请求参数：      目标状态 = disabled
服务端检查：    EnableUser
执行结果：      合法的禁用请求被拒绝
被迫绕过：      额外授予不需要的启用权限
```

## 为什么两个 action 必须代表两种能力 {#policy-contract}

账户状态变更具有明确的方向性。禁用操作通常下放给应急响应值班人员、反欺诈系统或合规自动化流程；而重新启用会恢复访问权限，往往需要更高层级的审批。

因此，两项权限必须严格正交：

| 调用方策略 | 禁用目标 | 启用目标 |
| --- | --- | --- |
| 仅 `admin:DisableUser` | 允许 | 拒绝 |
| 仅 `admin:EnableUser` | 拒绝 | 允许 |
| 两者都有 | 允许 | 允许 |
| 两者都没有 | 拒绝 | 拒绝 |

内置的 `consoleAdmin` 策略授予 `admin:*`，完整管理员仍可执行双向操作；受影响的仅是曾依赖旧缺陷的自定义受限策略。公开的 PBAC 参考文档同样为 [`admin:EnableUser`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-EnableUser) 与 [`admin:DisableUser`](/zh/administration/identity-access-management/policy-based-access-control/#policy-action.admin-DisableUser) 记录了这一契约。

## 设计目标与非目标 {#scope}

### 设计目标 {#goals}

1. 让现有的两项管理权限严格按各自名称生效；
2. 在启用与禁用两个方向上同时满足最小权限原则；
3. 每个请求只执行一次鉴权判定，最多写出一次鉴权错误响应；
4. 保持路由、查询参数、响应格式、禁止修改自身状态保护、IAM 存储调用与站点复制钩子不变；
5. 用自动化测试锁定四向权限矩阵，防止两项权限再次被合并或错位。

### 非目标 {#non-goals}

- 将端点拆分为独立的启用路由与禁用路由；
- 新增合并权限名称或修改 IAM 策略语法；
- 修改用户状态的持久化格式或站点复制机制；
- 重新设计 Console 前端权限模型。

## 讨论过但没有采用的方案 {#alternatives}

### 两种状态继续只检查 `admin:EnableUser` {#always-enable}

这会保留缺陷原状，使 `admin:DisableUser` 持续失效并迫使策略过度授权。

### 任一状态都同时要求两个 action {#require-both}

这会让两项权限失去独立意义，无法下放“仅允许禁用”的最小权限。

### Enable 鉴权失败后，再尝试 Disable 鉴权 {#double-validation}

上游 PR #21482 对禁用请求采用了串联调用方案：先以 `EnableUser` 调用 `validateAdminReq`，若返回 `nil` 再以 `DisableUser` 调用第二次。

然而 `validateAdminReq` 有一项关键副作用：当它返回 `nil` 对象层时，已经向 `http.ResponseWriter` 写出了错误响应。对仅持有 `admin:DisableUser` 的调用方而言，第一次调用已经向客户端提交了 HTTP 403，第二次调用随后通过鉴权并继续修改账户状态。鉴权回退分支绝不能在错误响应已经写出后继续修改状态。

### 禁用请求接受 Enable 或 Disable 任一个 action {#allow-either}

`validateAdminReq` 支持传入可变参数（variadic）权限列表，只要其中任一权限匹配即放行。若想兼容旧行为，只需向单次 `validateAdminReq` 调用同时传入两项权限，即可在放行 `admin:DisableUser` 的同时，保留“仅含 `admin:EnableUser` 也能禁用账户”的历史行为。

SILO 否决了该方案，因为“仅持启用权限即可禁用账户”正是需要修复的越权缺陷。需要管理完整账户生命周期的角色应当显式配置两项权限。

### 先校验 status，再进行鉴权 {#validate-first}

若在鉴权前先拦截非法 `status` 参数，就会改变错误响应优先级：原本未获授权的调用方在鉴权前就能探测参数格式校验结果。

因此，对于非法或未知的 `status` 值，选择函数继续返回默认的 `admin:EnableUser`；仅当 `status` 精确为 `disabled` 时才选择 `admin:DisableUser`。通过鉴权后，仍由既有的 IAM 逻辑拒绝非法状态值。

## 最终实现 {#implementation}

实现新增了一个无副作用的纯选择函数：

```go
func setUserStatusAdminAction(status string) policy.AdminAction {
    if madmin.AccountStatus(status) == madmin.AccountDisabled {
        return policy.DisableUserAdminAction
    }
    return policy.EnableUserAdminAction
}
```

处理函数先读取路由变量，选定所需权限，然后仅执行一次鉴权：

```go
vars := mux.Vars(r)
accessKey := vars["accessKey"]
status := vars["status"]

objectAPI, creds := validateAdminReq(ctx, w, r, setUserStatusAdminAction(status))
if objectAPI == nil {
    return
}
```

鉴权通过后的业务逻辑完全保持不变：

- 调用方仍不能启用或禁用自身账户；
- `globalIAMSys.SetUserStatus` 继续校验并持久化目标状态；
- 站点复制继续同步状态与更新时间；
- 响应格式与审计日志仍走原有路径。

选择函数仅依赖请求传入的目标状态字面量，不在鉴权前读取目标用户当前状态，也不依赖目标账户是否存在，从而保持鉴权判定确定且无前置存储读取。

## 为什么这个修复是安全的 {#safety}

该实现满足五条安全不变量：

1. 每个合法的目标状态严格映射到唯一一项管理权限；
2. `validateAdminReq` 仅调用一次，鉴权失败后立即返回，绝不执行状态修改；
3. 状态修改调用仅在目标状态对应的权限通过校验后可达；
4. 非法状态值保留原有的启用权限鉴权门槛，鉴权通过后仍由既有校验分支拒绝；
5. 存储格式、站点复制、网络协议与客户端 SDK 接口均无变化。

## 测试设计 {#tests}

### 纯 action 映射 {#mapping-test}

单元测试覆盖选择函数的三类输入：

| 输入 | 期望权限 |
| --- | --- |
| `enabled` | `EnableUser` |
| `disabled` | `DisableUser` |
| 非法值 | 保持默认的 `EnableUser` |

### 四向 IAM 鉴权矩阵 {#iam-test}

集成测试创建彼此独立的管理员账户与受限策略，通过真实管理 API 验证完整四向矩阵：

1. 仅持有禁用权限的客户端可以成功禁用目标用户；
2. 同一客户端尝试启用目标用户时收到 `AccessDenied`；
3. 仅持有启用权限的客户端可以成功启用目标用户；
4. 同一客户端尝试禁用目标用户时收到 `AccessDenied`。

两个交叉拒绝断言确保任一策略都不会意外放行反方向操作。测试在既有 IAM 服务端测试套件中运行，完整覆盖请求签名、策略绑定、处理函数鉴权、状态持久化与管理客户端错误解析，并在执行结束后清理所有临时用户与策略。

## 修复与验证记录 {#verification}

本地验证命令：

```text
go test ./cmd -run '^TestSetUserStatusAdminAction$' -count=1
go test ./cmd -run '^TestIAMInternalIDPServerSuite$' -count=1
git diff --check
```

带 DCO 签名的提交 `58735ee38` 推送至 PR #73 后，全部八项远端 CI 检查（DCO 签名、代码格式/编译/`go vet`、静态检查与生成文件、`cmd/` 单元测试、`internal/` 单元测试、并发竞态与 S3 Select、交叉编译、漏洞扫描）均一次通过，并以 `2e2377d1c` 合入主干。

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

持有该策略的调用方可以查看并禁用其他用户，但不能重新启用账户。

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

持有该策略的调用方可以查看并启用其他用户，但不能禁用账户。负责完整账户生命周期管理的角色应同时授予这两项权限。

## 组状态权限善后 {#group-follow-up}

组状态管理端点与用户状态端点结构完全对称：

```text
PUT /minio/admin/v3/set-group-status
    ?group=<target>
    &status=enabled|disabled
```

该端点同样定义了 `admin:EnableGroup` 与 `admin:DisableGroup`，但原有处理函数也在读取 `status` 参数前固定检查了 `EnableGroup`，导致两方向的最小权限同时错位。

善后提交（`229fe2b3c`）新增了与 `setUserStatusAdminAction` 同构的 `setGroupStatusAdminAction`：

```go
func setGroupStatusAdminAction(status string) policy.AdminAction {
    if madmin.GroupStatus(status) == madmin.GroupDisabled {
        return policy.DisableGroupAdminAction
    }
    return policy.EnableGroupAdminAction
}
```

配套集成测试创建了仅持 `EnableGroup`、仅持 `DisableGroup` 的独立管理员账户及目标用户组，验证：

1. 仅持 `DisableGroup` 可以禁用目标组；
2. 仅持 `DisableGroup` 不能启用目标组；
3. 仅持 `EnableGroup` 可以启用目标组；
4. 仅持 `EnableGroup` 不能禁用目标组。

非法 `status` 参数仍先按默认启用权限完成鉴权，再由既有逻辑返回参数校验错误，不会在鉴权前暴露参数校验差异。请求通过后的站点复制钩子保持不变，被拒绝的请求不会触发复制。

## 兼容性与迁移 {#compatibility}

客户端与 API 无需任何改动：路由地址、查询参数、状态字符串、响应格式与管理客户端方法完全保持不变。

自定义受限管理员策略需按以下规则核对：

- 仅负责禁用用户的角色需授予 `admin:DisableUser`；
- 仅负责启用用户的角色需授予 `admin:EnableUser`；
- 需要执行双向操作的角色必须同时授予这两项权限；
- `consoleAdmin` 及其他包含 `admin:*` 的策略不受影响；
- 过去仅配置 `admin:EnableUser` 的自定义策略将无法再禁用用户；若业务确需双向操作，请补充 `admin:DisableUser`。

组管理角色遵循完全对称的规则：

- 仅负责禁用组的角色需授予 `admin:DisableGroup`；
- 仅负责启用组的角色需授予 `admin:EnableGroup`；
- 需要执行双向操作的角色必须同时授予这两项权限；
- 仅配置 `admin:EnableGroup` 的旧策略将无法再禁用组。

## 上游处置与交付 {#upstream}

上游议题 #21478 与 PR #21482 保留在已归档为只读的 `minio/minio` 仓库中作为历史记录。

### 交付状态 {#delivery}

| 里程碑 | 用户状态修复 | 组状态善后 |
| --- | --- | --- |
| 带 DCO 签名的提交 | [`58735ee38`](https://github.com/pgsty/silo/commit/58735ee3829e36e24735587e2212b97c4149e0d1)（合并为 [`2e2377d1c`](https://github.com/pgsty/silo/commit/2e2377d1c6788d31d105c27c462ac542576b00f5)） | `229fe2b3c` |
| 发布版本 | [Server 20260903](/zh/blog/release/silo-20260903/) | [Server 20260903](/zh/blog/release/silo-20260903/) |

## 结论 {#conclusion}

启用与禁用用户或组具有截然相反的安全风险方向。处理函数根据请求的目标状态选择对应的策略权限，并在修改状态前执行单次鉴权，使权限检查与策略定义严格对齐。

本文记录的启停权限修复与后续 `admin:ChangeMyPassword` 权限拆分相互独立；跨九月版本升级时请一并参考[密码迁移指南](/zh/compatibility/password-permissions/)。
