---
title: "SN-2026-025：IAM 集群导入重启用已禁用凭据及 Console 编辑固化继承策略"
linkTitle: "SN-2026-025 · IAM 导入与控制台策略"
date: 2026-11-11
author: "冯若航"
description: "通过 ImportIAM 导入集群 IAM 归档会静默将所有已禁用的服务账号与已禁用用户组重新启用；同时在 Console 中编辑继承型服务账号会将父用户当前策略静态固化为内联策略，并在父策略超过 4 KiB 时导致无法禁用密钥。"
tags: [安全, IAM, Service Account, Console, Access Control, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261111-iam-import-status-and-console-policy/"
---

**发布状态：** Server 主干（[`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed)）与 Console 主干（[`1be8a74bf`](https://github.com/pgsty/silo-console/commit/1be8a74bfb86ba3f417204551099fd8a3788f0e2)、[`a1a84cab4`](https://github.com/pgsty/silo-console/commit/a1a84cab4d96814af6572f7dce40ad537aa2f81e)、[`1fdb279fd`](https://github.com/pgsty/silo-console/commit/1fdb279fd98845b66d7218b2159b434fe76351eb)）均已修复，将随下一轮协同版本发布\
**安全编号：** `SN-2026-025`（[安全公告台账](/zh/about/security-advisories/#sn-2026-025)，[#339](https://github.com/pgsty/silo/issues/339)，[#345](https://github.com/pgsty/silo/issues/345)）\
**严重程度：** 高危（High）\
**影响范围：** **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与自 `2022-06-23`（[`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f)）以来的上游原版 MinIO；**SILO Console**（独立版与内嵌版 `v2.7.0` 及更早版本）与自 `2024-02-29`（[`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d)）以来的上游原版 MinIO Console\
**客户端与控制台配套：** 需协同升级配套的 Server 与 Console（`mcli` [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf) 同步对齐了 `accesskey edit` 传入显式空策略文档重置继承的能力）

继 [`SN-2026-021`](/zh/blog/security/20261110-svcacct-inline-policy-preservation/) 排查服务账号策略更新链路后，我们进一步对 IAM 备份恢复（`ExportIAM` / `ImportIAM`）、Web 控制台（Console）编辑表单与带过期时间的服务账号开展了端到端联动审查，确认了另外两处继承自上游的凭据状态与权限边界缺陷：

1. **集群 IAM 导入（`mcli admin cluster iam import`）静默重新启用已禁用凭据与用户组：** `importIAM`（`cmd/admin-handlers-users.go`）在重建服务账号时漏传了导出的 `Status` 字段，在导入 `groups.json` 时忽略了禁用组状态，导致灾备恢复或集群迁移后**所有曾被禁用隔离的服务账号密钥与禁用组全部恢复为启用（`"on"` / `"enabled"`）状态**。
2. **Console 编辑继承型服务账号时静态固化父策略，且父策略超 4 KiB 时无法在界面禁用密钥：** 服务端 `InfoServiceAccount` 在返回 `ImpliedPolicy: true` 的同时会附带父用户的合并策略文本供展示；上游 Console 的 `EditServiceAccount` 弹窗将该父策略文本载入编辑器并在保存任意属性修改时作为 `newPolicy` 回传，静默将“动态继承父策略”的密钥固化为一份静态内联策略拷贝，且在父策略超过 4 KiB 时直接阻塞禁用操作并吞掉弹窗报错。

## 摘要 {#summary}

- **问题本质：**
  1. **`ImportIAM` 丢失服务账号与用户组的禁用状态（`#345`）：** `importIAM` 构造 `newServiceAccountOpts` 时未填入 `status: svcAcctReq.Status`（导致 `NewServiceAccount` 一律默认设为 `AccountOn = "on"`）；导入组时从未检查 `grpInfo.Status == statusDisabled` 并调用 `SetGroupStatus(ctx, grp, false)`；且在 `AddUsersToGroup` 失败时把外层为 `nil` 的 `err`（而非真实错误 `gerr`）记入 `failed.Groups`。
  2. **Console `EditServiceAccount` 混淆只读继承展示与内联限制策略（`#339`）：** 在 Console 中对继承型（`ImpliedPolicy: true`）访问密钥执行改名、改描述、改过期时间或禁用/启用切换时，前端均会将父用户当前策略作为 `newPolicy` 提交，使其变为 `embedded-policy`；当父用户合并策略压缩后超过 `maxSVCSessionPolicySize`（4096 字节）时，管理员在 Console 中甚至无法禁用该密钥（服务端返回 `400`，而弹窗遮罩吞掉了错误提示）。
  3. **带过期时间的无 `"Version"` 内联策略在运行时鉴权恒被拒：** `NewServiceAccount` 允许创建省略 `"Version"` 字段的内联策略，永不过期密钥（走 `isAllowedLocally`）可正常工作，但设置了 `Expiration` 的服务账号（`cred.IsTemp() == true`，走 `isAllowedBySessionPolicy`）因强制要求 `subPolicy.Version != ""` 而在每次请求时返回 `403`。
- **上游溯源：**
  - `ImportIAM` 丢失禁用状态与组错误记录为空：源自上游 MinIO `2022-06-23` 提交 [`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f)（[minio/minio#15014](https://github.com/minio/minio/pull/15014)）。
  - 带过期时间服务账号 `"Version"` 校验不一致：源自上游 MinIO `2021-07-15` 提交 [`eae9c2f65`](https://github.com/pgsty/silo/commit/eae9c2f65bade4d9de2aac42f188114bf6dbe555)（[minio/minio#12716](https://github.com/minio/minio/pull/12716)）与 `2023-02-27` 提交 [`4d708cebe`](https://github.com/pgsty/silo/commit/4d708cebe9f9d15169b28d54e7adbd4150933622)（[minio/minio#16430](https://github.com/minio/minio/pull/16430)）的叠加。
  - Console 写回继承策略：源自上游 MinIO Console `2024-02-29` 提交 [`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d)（`#3221`）。
- **修复方式：** Server 提交 [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed) 在 `importIAM` 中透传服务账号与用户组状态、记录真实组导入错误，并在写入凭据前将省略 `"Version"` 的非空内联策略规范化补齐默认版本 `"2012-10-17"`；Console 提交 [`1be8a74bf`](https://github.com/pgsty/silo-console/commit/1be8a74bfb86ba3f417204551099fd8a3788f0e2)、[`a1a84cab4`](https://github.com/pgsty/silo-console/commit/a1a84cab4d96814af6572f7dce40ad537aa2f81e) 与 [`1fdb279fd`](https://github.com/pgsty/silo-console/commit/1fdb279fd98845b66d7218b2159b434fe76351eb) 分离跟踪继承态与内联限制态，并在弹窗内部显式展示保存错误。

---

## 一、上游溯源与根因分析 {#provenance}

### `ImportIAM` 重新激活已禁用服务账号与用户组 {#import-iam}

`ExportIAM`（`GET /minio/admin/v3/export-iam`）会将每个服务账号（含 `"accountStatus": "off"`）写入 `svcaccts.json`，将每个用户组（含 `"status": "disabled"`）写入 `groups.json`。当上游在 [`580d9db85`](https://github.com/pgsty/silo/commit/580d9db85e04f1b63cc2909af50f0ed08afa965f)（`2022-06-23`）中实现 `importIAM` 时，仅在导入普通用户（`users.json`）时处理了禁用状态，却遗漏了服务账号和用户组：

1. **服务账号被无条件启用：** `importIAM` 虽然从 JSON 解出了 `svcAcctReq.Status`，但在构造 `newServiceAccountOpts` 时未赋值 `status:` 字段。`NewServiceAccount`（`cmd/iam.go`）遇到空 `opts.status` 一律回退为 `auth.AccountOn`（`"on"`）。管理员此前为应急止损或离职审计而禁用（`svcacct disable`）的所有历史 Access Key，一旦经历一次 `mcli admin cluster iam import` 就会全部静默复活。
2. **用户组被无条件启用且报错丢失：** `AddUsersToGroup` 创建的新组默认处于 `"enabled"` 状态，由于 `importIAM` 从未在 `grpInfo.Status == statusDisabled` 时调用 `SetGroupStatus(ctx, grp, false)`，所有已禁用的权限组在导入后立即重新向组内成员赋予权限。同时，当 `AddUsersToGroup` 返回错误 `gerr` 时，代码误写了 `Error: err`（此时外层 `json.Unmarshal` 的 `err` 恒为 `nil`），导致返回给客户端的失败清单中错误原因为空。

### Console 编辑继承型密钥固化父策略并阻塞超长父策略禁用 {#console-freeze}

在服务端，`InfoServiceAccount`（`cmd/admin-handlers-users.go`）在服务账号处于继承模式时返回 `ImpliedPolicy: true`，同时把父用户（及所属组）当前的合并策略序列化到 `Policy` 字段供界面预览。

上游 Console（[`0afea6399`](https://github.com/pgsty/silo-console/commit/0afea639940920f5124369132faa1cb4efef195d)，`2024-02-29`）在 `EditServiceAccount.tsx` 中虽然根据 `impliedPolicy` 将“**Restrict beyond user policy**（在用户策略之外进一步限制）”开关默认置为关闭，却仍把 `account.policy` 填入了底层 `policy` 状态变量，并在点击保存时只要 `policy !== ""` 就原样随 `PUT` 请求发出：

- **继承态被静默改写为内联快照：** 管理员仅在 Console 中修改密钥名称、描述、有效期或切换启用/禁用开关，就会把父用户那一刻的策略永久写入 JWT 的 `sessionPolicy` 中，使密钥从 `inherited-policy` 变为 `embedded-policy`，后续给父用户新增的授权均不再对该密钥生效。
- **父策略超过 4 KiB 时无法在 Console 中禁用密钥：** 内联会话策略受限于 JWT 体积，上限为压缩后 4096 字节（`maxSVCSessionPolicySize`），而父用户及多组叠加策略并无 4 KiB 限制。一旦父用户合并策略超过 4 KiB，管理员在 Console 中尝试**禁用**某个继承型密钥时，前端附带的超长父策略会被服务端以 `400 session policy size exceeds 4KiB limit` 拒绝，且错误提示渲染在模态框遮罩后方不可见，导致密钥维持启用而界面无反应。

---

## 二、影响范围 {#impact}

| 操作路径 / 组件                                 | 安全与运维影响                                                                                                  |
| :---------------------------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| **`mcli admin cluster iam import`**             | 所有已禁用服务账号（`accountStatus: "off"`）与已禁用组（`status: "disabled"`）在导入后被静默重新启用。          |
| **Console 编辑继承型密钥（父策略 `<= 4 KiB`）** | 任意改名、改描述、改过期时间或状态切换均会将继承型密钥固化为静态内联策略，导致后续权限演进偏离预期。            |
| **Console 编辑继承型密钥（父策略 `> 4 KiB`）**  | 管理员无法通过 Console 禁用或修改该继承型密钥（触发 `400` 超长报错且弹窗内无报错提示）。                        |
| **带过期时间且省略 `"Version"` 的内联策略**     | 创建成功（`200`），但在设置了 `Expiration` 的服务账号上每次请求均因 `subPolicy.Version == ""` 被拒绝（`403`）。 |
{.wide .expand}

---

## 三、修复方案：设计思考与充分必要性 {#fix}

### Server 侧修复（`1d714834c`） {#server-fix}

1. **`importIAM` 完整还原禁用状态与真实错误（`cmd/admin-handlers-users.go`）：**
   - 在 `newServiceAccountOpts` 中传入 `status: svcAcctReq.Status`（仅当旧格式归档未包含状态字段时默认 `"on"`），在 `.minio.sys/iam/` 与 `etcd` 后端一致保留 `"off"` 禁用态；
   - 在 `AddUsersToGroup` 成功后检查 `strings.EqualFold(grpInfo.Status, statusDisabled)` 并调用 `SetGroupStatus(ctx, grp, false)`，同时将组创建或状态设置阶段的真实错误记入 `failed.Groups`。
2. **凭据写入边界统一补齐策略默认 `"Version"`（`cmd/iam.go` 中的 `normalizeServiceAccountPolicy`）：**
   - 对包含语句但 `Version == ""` 的非空内联策略克隆副本并补齐 `policy.DefaultVersion`（`"2012-10-17"`），消除永不过期密钥与带过期时间密钥之间的鉴权分歧；同时严格保持显式空策略文档（`{}` 或 `{"Statement":[]}`，`Version == ""` 且 `len(Statements) == 0`）不变，继续作为 [`SN-2026-021`](/zh/blog/security/20261110-svcacct-inline-policy-preservation/) 定义的“清除内联策略、恢复继承”信号。

### Console 侧修复（`1be8a74bf`、`a1a84cab4`、`1fdb279fd`） {#console-fix}

1. **分离跟踪 `impliedPolicy` 与内联策略文本（`EditServiceAccount.tsx`、`api/users.go`）：**
   - 当继承型密钥的 **Restrict beyond user policy** 开关保持关闭时，保存请求省略 `policy` 字段，无论父策略是否超过 4 KiB 均可正常改名、设置过期时间或禁用密钥，且严格保持 `inherited-policy`；
   - 当管理员在已有限制策略的密钥上主动关闭 **Restrict beyond user policy** 开关（或填入 `{}` / `{"Statement":[]}`）时，Console 显式发送 `{}` 将其恢复为继承父策略；
   - 当开启限制开关但策略文本框为空时，前端直接给出校验提示并阻止提交；后端返回的任何错误均通过 `ModalErrorAlert` 直接显示在弹窗内部。

### 为什么该设计既必要又充分 {#sufficiency}

- **必要性：** 仅靠服务端 [`SN-2026-021`](/zh/blog/security/20261110-svcacct-inline-policy-preservation/) 无法阻止旧版 Console 把合法的父策略 JSON 当作 `newPolicy` 发往服务端（对服务端接口而言，客户端显式发来的非空策略 JSON 与管理员故意配置的内联策略在语法上完全一致），也无法修复 `importIAM` 丢弃 `Status` 字段的问题。
- **充分性：** 结合 [`SN-2026-021`](/zh/blog/security/20261110-svcacct-inline-policy-preservation/) 与 `mcli` [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf)，三态策略契约（缺省/`null` 保留、显式空文档重置继承、非空文档补齐 `Version` 嵌入）与启用/禁用状态在 Server Admin API、站点复制、IAM 导入导出、Console 及 `mcli` 全栈保持完全一致（见 `cmd/iam-import-state_test.go` 与 `cmd/iam-svcacct-policy-edit_test.go`）。

---

## 四、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                                   | 工程取舍与升级边界                                                                                                                                                                                                                     |
| :----------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Server 与 Console 需配套升级**           | 若仅升级独立版 Console 而不升级 SILO Server（早于 `SN-2026-021`），省略 `newPolicy` 的编辑仍会触发旧服务端清空策略；反之若仅升级 Server 而不更新独立/内嵌 Console，旧版 Console 仍会在编辑继承型密钥时写回父策略。请配套升级两个组件。 |
| **历史 `iam import` 已复活凭据需人工复核** | 升级代码可保证今后的 `iam import` 严格保留禁用状态，但无法自动区分存量集群中哪些账号是正常启用、哪些是被历史导入操作意外重新启用的。                                                                                                   |
{.wide .expand}

---

## 升级与排查建议 {#remediation}

1. **协同升级 SILO Server、SILO Console 与 `mcli`** 至 `20261109` 之后的下一轮配套版本（或基于当前各仓库 `main` 构建：Server [`1d714834c`](https://github.com/pgsty/silo/commit/1d714834c5457d0485f5ebd9e4b0aaff8a454eed)、Console [`1fdb279fd`](https://github.com/pgsty/silo-console/commit/1fdb279fd98845b66d7218b2159b434fe76351eb)、`mcli` [`d7262c2a`](https://github.com/pgsty/mc/commit/d7262c2a5fbdf2b9503cc0283f1d37ae8da41baf)）。
2. **核查曾执行过 `mcli admin cluster iam import` 的集群：** 若集群此前曾从包含禁用服务账号或禁用组的备份包执行过 `iam import`，请对照当时备份包内的 `svcaccts.json` 与 `groups.json` 检查并重新禁用不应启用的条目：
   ```shell
   mcli admin user svcacct disable myminio/ <access-key>
   mcli admin group disable myminio <group-name>
   ```
3. **核查曾在 Console 编辑过的继承型密钥：** 若某些原本应动态跟随父用户权限的服务账号曾通过旧版 Console 编辑过属性并意外变为 `Policy: embedded`，可在升级后于新版 Console 中关闭 **Restrict beyond user policy**（或使用 `mcli admin user svcacct edit --policy` 传入 `{}`）恢复继承模式。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-025)、[`SN-2026-021`](/zh/blog/security/20261110-svcacct-inline-policy-preservation/) 与 [Console 兼容性说明](/zh/compatibility/console/#candidate-policy-edit)。
