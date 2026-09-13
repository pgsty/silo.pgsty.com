---
title: "密码权限迁移"
linkTitle: "密码权限迁移"
description: "ChangeMyPassword 与 CreateUser 拆分的适用版本、策略迁移与回滚限制。"
url: "/zh/compatibility/password-permissions/"
weight: 6
type: docs
icon: fa-solid fa-code-branch
---

> **适用范围，2026-09-13：** 本页描述 Server 主分支与 pkg v3.14.0、Console 源码 `417559bb2c97` 的配套行为。
> 最新已发布的 Server 20260903 与 Console v2.4.0 **尚未包含此拆分**。
> 单独升级 pkg 或 mcli 不会改变旧 Server 的权限判断。见[组件版本矩阵](/zh/compatibility/versions/)。

**这是授权语义的破坏性变化。** 同一份已保存策略，在升级前后可能作出不同的允许/拒绝决定。
这来自采用 [minio/pkg #262](https://github.com/minio/pkg/pull/262)，与 SDK 更新独立；不是透明的依赖刷新。

## 新旧行为 {#behavior}

服务端保留原来的 `add-user` 管理端点与 mcli 命令，按调用者和目标访问密钥是否相同选择权限：

| 请求 | 新权限 | 判断规则 |
| --- | --- | --- |
| 修改调用者自己的密码 | `admin:ChangeMyPassword` | 已附加策略的内部用户隐式允许，显式 Deny 优先 |
| 创建其他用户或重置其密码 | `admin:CreateUser` | 必须显式 Allow，显式 Deny 优先 |

Console 的修改密码按钮使用 ChangeMyPassword，用户管理继续使用 CreateUser。
修改自己的密码仍需当前密码。STS、服务账号不能借此修改父用户密码；root 与外部身份提供商密码不属于此端点。

下表假定内部用户已附加策略、条件匹配，且没有其他 Allow/Deny：

| 现有策略 | 升级前修改自己的密码 | 升级后修改自己的密码 | 创建/重置其他用户，升级前后 |
| --- | --- | --- | --- |
| 只有 S3 读取授权 | 允许 | 允许 | 拒绝 |
| `Deny admin:CreateUser` | 拒绝 | **允许** | 拒绝 |
| `Deny admin:ChangeMyPassword` | 允许 | **拒绝** | 拒绝 |
| `Allow admin:CreateUser` | 允许 | 允许 | 允许 |
| `Allow admin:CreateUser` 加 `Deny admin:ChangeMyPassword` | 允许 | **拒绝** | 允许 |
| 同时 Deny 两个动作，或 `Deny admin:*` | 拒绝 | 拒绝 | 拒绝 |

只匹配 CreateUser 的通配 Deny（如 `admin:Create*`）也存在相同变化。
Allow 不能覆盖匹配的 Deny；只授予 ChangeMyPassword 不会授予用户管理权限。
策略 JSON 格式、已保存文档与端点保留，但语义已经变化；没有恢复旧动作映射的开关。

## 保留旧限制 {#migration}

如果原策略通过拒绝 CreateUser 来锁定用户自己的密码，**升级前在同一个 Deny 语句中加入 ChangeMyPassword**：

```json
{
  "Effect": "Deny",
  "Action": ["admin:CreateUser", "admin:ChangeMyPassword"]
}
```

这只是语句片段，不能替换整份策略。保留原语句的其他动作、资源范围、条件和其余所有语句。
同时检查用户直接附加与通过组继承的策略。前一版本 pkg 已识别这两个动作名，可以提前准备。
已保存策略不会自动重写，需要管理员在确实希望维持旧限制的地方应用变更。

若要禁止修改自己的密码、同时允许独立授权的用户管理，只拒绝 ChangeMyPassword。
该区别只有包含新实现的 Server 才会执行。

## 内置只读策略 {#readonly}

新 `readonly` 保留原 S3 读取权限，移除旧 CreateUser Deny，因此：

- 用户可以修改自己的密码，除非其他适用语句拒绝 ChangeMyPassword。
- 另一个策略的 CreateUser Allow 不再被内置只读策略压住；同时拥有这两份策略的用户可能获得更广权限。

新增 `consolereadonly` 还授予 Console 浏览所需的 ListBucket，并采用相同拆分。
这两种只读策略自身都不授予用户管理或 S3 写入权限，S3 只读不再隐含锁定密码。

升级保留已保存策略和同名内置策略的用户覆盖。旧 `readonly` 副本仍有 CreateUser Deny，继续拒绝其他用户管理，
但在新 Server 上不再拒绝修改自己的密码。没有保存覆盖时，Server 才使用新版内置定义。
应检查实际策略内容，不应仅根据名字判断。要保留两个旧限制，可另附双 Deny 策略，或给旧 readonly 覆盖增加 ChangeMyPassword Deny。

## 程序调用者 {#callers}

pkg 的 `Policy.IsAllowedActions` 现在隐式返回 ChangeMyPassword（除非被拒绝），只在明确授权时返回 CreateUser。
Go 函数签名与最低 Go 版本未变，但返回能力发生变化。Console 及其他调用者不能继续用 CreateUser 代替修改密码权限。

## 配套升级与回滚 {#rollback}

Server、pkg 与 Console（包括嵌入版本）应协调升级；mcli 同步共享包与 SDK。
混用新旧版本可能出现按钮与服务端决策不一致，或旧 Server 不执行密码专用 Deny。

升级前导出受影响用户/组策略，按上表检查，并在需要维持旧限制的地方保留双 Deny。
整个升级与回滚窗口内保留这两个拒绝动作，实际验证自己的密码修改、其他用户创建与密码重置。
完成全部 Server 与 Console 更新后，才能依赖新的独立权限。

回滚二进制不会转换策略。旧 Server 忽略此端点的 ChangeMyPassword Deny，必须恢复或保留 CreateUser Deny 才能锁定密码；
它也会同时禁止管理其他用户。旧 Server 无法表达“允许用户管理、仅禁止修改自己的密码”的新组合。

[Server 原始迁移指南](https://github.com/pgsty/silo/blob/main/docs/iam/password-permissions.md) 是实现侧的依据。
与上游 MinIO 的兼容仍为尽力保留；正式集成目标是 `pgsty/silo`。
