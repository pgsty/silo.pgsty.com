---
title: "SN-2026-015：PutObjectRetention 授权绕过"
linkTitle: "SN-2026-015：保留期授权"
date: 2026-09-26
author: "冯若航"
description: "PutObjectRetention 以 governance bypass 请求头代替授权。影响范围、根因、实测与修复设计。"
tags: [安全, Object Lock, IAM, silo]
weight: 1
url: "/zh/blog/security/20260926-governance-retention-bypass/"
---

**2026-09-26 状态：设计阶段，尚未修复。** 本文是待评审的修复设计。
目前没有任何 SILO 发布修复此缺陷。所有已发布的 Server 版本都受影响，包括
`RELEASE.2026-09-16T00-00-00Z`；Server main
[`b0a540190`](https://github.com/pgsty/silo/commit/b0a540190) 同样受影响。
这段代码继承自上游 MinIO，上游 master 是同样的逻辑。

`PutObjectRetention` 请求带上 `x-amz-bypass-governance-retention: true` 时，
服务端把这个请求头当成了授权，而它本应只表达意图。由此产生三个问题，按严重程度排列：

| 编号 | 谁 | 能做什么 |
| --- | --- | --- |
| **F1** | **任何已认证主体**，包括对 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention` 挂了显式 Deny、在该桶上没有任何授权的主体 | 清除任意启用锁的桶中任意版本的 GOVERNANCE 保留期；把 GOVERNANCE 改为 COMPLIANCE；给没有保留期或保留期已到期的版本加上任意时长的 COMPLIANCE 保留期 |
| **F2** | 持有 `s3:PutObjectRetention`、没有 `s3:BypassGovernanceRetention` 的主体 | 缩短 GOVERNANCE 保留期（报告中的情形） |
| **F3** | 持有 `s3:BypassGovernanceRetention` 的主体 | 无视对 `s3:PutObjectRetention` 的条件 Deny |

F1 与 F2 让 GOVERNANCE 保留期失效：保留期被清除或缩短后的日期一过，
拥有普通删除权限的主体就能删除该版本。F1 还能把对象锁反过来用在数据属主身上：
被加上 COMPLIANCE 保留期的版本，在到期前任何人都删不掉，包括 root，
这段时间里桶的存储空间也一直被占用。匿名请求不受影响，没有访问密钥即被拒绝。

删除路径正确校验了 bypass 权限
（[CVE-2023-25812](https://github.com/minio/minio/security/advisories/GHSA-c8fc-mjj8-fc63)）。

F2 由 szopi00 以
[GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88)
报告。报告提交到了 Pigsty 仓库，因为 `pgsty/silo` 当时没有开启私密漏洞报告。
F1 与 F3 是我们在设计修复、评审设计的过程中发现的。`SN-2026-015` 是暂定的台账编号。
F1 只需要一个有效凭据，因此我们把整体评为 **High**。尚未申请 CVE。

## 应有语义 {#semantics}

对处于未到期 GOVERNANCE 保留期的版本，S3 Object Lock 要求：

| 请求的变更 | 所需权限 | 所需请求头 |
| --- | --- | --- |
| 任何保留期写入 | `s3:PutObjectRetention` | 无 |
| 保持 GOVERNANCE，日期不变或更晚（延长） | `s3:PutObjectRetention` | 无 |
| 日期提前（缩短） | `s3:PutObjectRetention` **且** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| 清除保留期或改变模式 | `s3:PutObjectRetention` **且** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| 删除受锁定的版本 | `s3:DeleteObjectVersion` **且** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |

请求头表达意图，权限负责授权。只有两者都要求时，GOVERNANCE 才有意义：
普通主体可以设置、延长保留期，只有另行授信的主体才能削弱它。
未到期的 COMPLIANCE 保留期不能缩短、不能改模式；现有的 COMPLIANCE 检查不依赖请求头，
但 F1 仍然可以*新建* COMPLIANCE 保留期。

## 实测 {#verification}

全部测试在 Server main（`b0a540190`）的本地构建上进行，请求均为 SigV4 签名。

**F2**，使用报告中的策略：`nobypass` 持有 `s3:PutObjectRetention`、
`s3:DeleteObject` 与 `s3:DeleteObjectVersion`，没有 `s3:BypassGovernanceRetention`。

| 步骤（未注明者均以 `nobypass` 身份） | 结果 |
| --- | --- |
| root 设置 GOVERNANCE 至 2032 年 | 200 |
| 缩短到 2027 年，不带请求头 | 400 `InvalidRequest`（WORM 保护），正确 |
| 缩短到 2027 年，带请求头 | **200**；随后 `GetObjectRetention` 返回 2027 |
| 缩短到 5 秒后，带请求头 | **200** |
| 8 秒后带 `versionId` 做 `DeleteObject`，不带请求头 | **204**；随后 `HEAD` 返回 404 |
| 对照：带请求头的 `DeleteObject` | 被拒绝，正确 |

**F1**，使用 `zeroperm`：它唯一的 Allow 是 `s3:ListAllMyBuckets`，并对
`arn:aws:s3:::*` 显式 Deny 了 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention`。
桶和对象都属于 root。

| 步骤（以 `zeroperm` 身份） | 结果 |
| --- | --- |
| 清除 GOVERNANCE（空 `<Retention/>`），不带请求头 | 400 `InvalidRequest`，正确 |
| 清除 GOVERNANCE，带请求头 | **200**；保留期被清除 |
| 给无保留期的版本加 COMPLIANCE 至 2027 年，不带请求头 | 403 `AccessDenied`，正确 |
| 给无保留期的版本加 COMPLIANCE 至 2027 年，带请求头 | **200** |
| root 带 bypass 删除该版本 | 被拒绝，WORM 保护 |

**F3**：某用户被允许 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention`，
另有一条显式 Deny：`s3:object-lock-remaining-retention-days` 小于 30 时拒绝
`s3:PutObjectRetention`。该用户带请求头把剩余保留期设为 5 天：**200**。

## 根因 {#root-cause}

两处缺陷叠加。

**处理器只做认证。** `PutObjectRetentionHandler`（`cmd/object-handlers.go`）调用
`authenticateRequest(ctx, r, policy.PutObjectRetentionAction)`。尽管带了动作参数，
这个函数只校验签名、记录凭据，不求值任何策略。
全部授权都留给了在 `EvalMetadataFn` 中运行的 `enforceRetentionBypassForPut`
（`cmd/bucket-object-lock.go`）及其辅助函数 `isPutRetentionAllowed`（`cmd/auth-handler.go`）。

**辅助函数见到请求头就放行。**

```go
// enforceRetentionBypassForPut
byPassSet := objectlock.IsObjectLockGovernanceBypassSet(r.Header) // 原始请求头
...
case objectlock.RetGovernance:
    govPerm := isPutRetentionAllowed(..., objRetention.Mode, byPassSet, ...)
    if !byPassSet { // 防缩短/改模式检查，带请求头时被跳过
        if objRetention.Mode != objectlock.RetGovernance ||
            objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time) {
            return ObjectLocked{...}
        }
    }
    if govPerm == ErrAccessDenied { return errAuthentication }
    return nil

// isPutRetentionAllowed
if retMode == objectlock.RetGovernance && byPassSet {
    byPassSet = globalIAMSys.IsAllowed(BypassGovernanceRetentionAction ...)
}
retSet = globalIAMSys.IsAllowed(PutObjectRetentionAction ...)
if byPassSet || retSet {
    return ErrNone
}
return ErrAccessDenied
```

- 防止削弱的检查只在请求头**缺席**时执行。
- bypass 权限只在**请求的**模式为 GOVERNANCE 时才求值。模式为空（清除）或
  COMPLIANCE 时，`byPassSet` 仍是原始请求头的值；只要带了请求头，
  即使 `retSet` 为假，`byPassSet || retSet` 也为真。这就是 **F1**。
- 请求模式为 GOVERNANCE 时，bypass 结果被求值，但对任何持有
  `s3:PutObjectRetention` 的主体，`|| retSet` 让这个结果失去作用。这就是 **F2**。
- 同一个 `||`，让 bypass 持有者在 `retSet` 被条件键拒绝时仍能通过。这就是 **F3**。

### 历史 {#history}

- 上游 [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45)（#9259，
  MinIO `RELEASE.2020-04-10T03-34-42Z`）之前，GOVERNANCE 分支在请求头存在时返回单独求值的
  bypass 权限。那次提交为了加入策略条件键引入了 `isPutRetentionAllowed`，同时丢掉了这个区分。
- 上游 [#20929](https://github.com/minio/minio/pull/20929)（`437dd4e32`，
  “Fix missing authorization check for `PutObjectRetentionHandler`”，
  MinIO `RELEASE.2025-02-18T16-25-55Z`）在处理器入口加了
  `checkRequestAuthType(..., PutObjectRetentionAction, ...)`，堵住了 F1，F2 与 F3 仍在。
- 上游 [#21103](https://github.com/minio/minio/pull/21103)（`8c7097528`，
  MinIO `RELEASE.2025-04-03T14-56-28Z`）重做签名校验时，把入口检查换成了
  `authenticateRequest`，F1 随之回归。SILO 分叉于此之后，所有 SILO 发布三者俱在。

## 修复设计 {#design}

### 不变量 {#invariants}

1. **先授权，再读状态。** 每个 `PutObjectRetention` 请求，在处理器读取桶或对象之前，
   都必须被允许 `s3:PutObjectRetention`，求值时带上对象锁条件键，显式 Deny 始终生效。
2. **削弱需要意图与授权同时具备。** 对未到期 GOVERNANCE 版本，缩短日期、清除保留期
   或改变模式，只有在请求头存在**且**在同一组条件值下允许 `s3:BypassGovernanceRetention`
   时才接受。
3. **bypass 是附加要求。** `s3:BypassGovernanceRetention` 永远不能替代 `s3:PutObjectRetention`。
4. **只有请求头不授予任何权利。** 没有削弱时忽略请求头，总是带这个头的客户端做延长操作仍然正常。
5. **是否需要 bypass 由现有锁决定。** 看版本当前的保留期以及此次变更是否削弱它，
   不看请求里的 `Mode`。

### 各项检查放在哪里 {#placement}

三个锁条件键（`s3:object-lock-mode`、`s3:object-lock-retain-until-date`、
`s3:object-lock-remaining-retention-days`）全部来自**请求体**，而不是已存储的版本。
处理器在接触对象之前就已解析请求体，因此可以在入口完整地求值 `s3:PutObjectRetention`：

```go
// PutObjectRetentionHandler，在 authenticateRequest 与 ParseObjectRetention 之后：
conds := retentionConditions(r, cred, objRetention) // 来自请求的锁条件键
if !retentionAllowed(policy.PutObjectRetentionAction, bucket, object, cred, owner, conds) {
    writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
    return
}
```

只有“是否削弱”依赖存储状态，所以只有这一项判断留在 `enforceRetentionBypassForPut`：

```go
case objectlock.RetGovernance: // 保留期尚未到期
    weakens := objRetention.Mode != objectlock.RetGovernance ||
        objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time)
    if !weakens {
        return nil
    }
    if !objectlock.IsObjectLockGovernanceBypassSet(r.Header) {
        return ObjectLocked{...}
    }
    if !retentionAllowed(policy.BypassGovernanceRetentionAction, bucket, object, cred, owner, conds) {
        return errAuthentication
    }
    return nil
```

已到期、无保留期与 COMPLIANCE 分支保留现有的状态规则，不再承载权限逻辑。
删除 `isPutRetentionAllowed` 及其 `||`。匿名请求与现在一样被拒绝。

### 判定表 {#decision-table}

`retOK` 表示带请求中的锁条件键时 `s3:PutObjectRetention` 被允许，
`bypassOK` 表示同一组条件键下 `s3:BypassGovernanceRetention` 被允许。

| 目标版本 | 变更 | 请求头 | `retOK` | `bypassOK` | 现状 | 修复后 |
| --- | --- | --- | --- | --- | --- | --- |
| 任意 | 任意 | 任意 | 否 | 任意 | 常为 200（F1、F3） | 入口 **403** |
| 未到期 GOVERNANCE | 延长 | 任意 | 是 | 任意 | 200 | 200 |
| 未到期 GOVERNANCE | 削弱 | 无 | 是 | 任意 | 400 `ObjectLocked` | 400 `ObjectLocked` |
| 未到期 GOVERNANCE | 削弱 | 有 | 是 | 否 | **200**（F2） | **403** |
| 未到期 GOVERNANCE | 削弱 | 有 | 是 | 是 | 200 | 200 |
| 未到期 COMPLIANCE | 缩短或改模式 | 任意 | 是 | 任意 | 400 `ObjectLocked` | 400 `ObjectLocked` |
| 无保留期或已到期 | 任意 | 任意 | 是 | 任意 | 200 | 200 |

持有 `retOK` 的调用者，除 F2 那一行外看不到变化。未授权削弱返回 403，
与删除路径对无权限 bypass 请求返回 `AccessDenied` 一致。属主（root）与现在一样，
由 IAM 系统放行两个动作。

把权限检查移到入口后，未授权调用者会先得到 403，无从得知桶或版本是否存在；
现在这类请求可能返回 404 或 400。

### 考虑过的替代方案 {#alternatives}

- **只把检查里的 `byPassSet` 换成 bypass 求值结果。** 能修 F2，修不了 F1：
  清除与 COMPLIANCE 请求根本走不到那个检查，而且仍凭原始请求头通过
  `byPassSet || retSet`。F3 也仍在。
- **恢复上游 #20929 的入口 `checkRequestAuthType`。** 那次检查不带锁条件键。
  多数条件运算符在键缺失时不匹配，于是依赖这些键的 Allow 会在入口失败；
  依赖这些键的 Deny 在入口同样不匹配，只有后面的检查才看得到。
  在入口用来自请求的条件键求值，只需一次判断，而且判断正确。
- **所有检查都留在 `EvalMetadataFn` 里。** 只有对象层每条路径都在写入前调用回调时才正确，
  而且会向无权限的调用者泄露桶和版本是否存在。与状态无关的判断应该放在入口。
- **对没有 bypass 权限的调用者，一律拒绝该请求头。** 会打断每次写保留期都带这个头的客户端，
  包括延长操作。协议把请求头视作意图，没有削弱时不能把它当错误。
- **像删除路径一样复用 `authorizeRequest(..., BypassGovernanceRetentionAction)`。**
  这个调用不带锁条件键，依赖这些键的 bypass 策略在保留期路径上会得到不同结果。
  删除路径是否也应带上这些键，留给另一项改动。

### 附注 {#notes}

- `ParseObjectRetention` 拒绝过去的日期（`ErrPastObjectLockRetainDate`），
  并要求空 `Mode` 不带日期，所以清除保留期总是空的 `<Retention/>`。
- `s3:object-lock-remaining-retention-days` 按 `ceil(|date − now| / 24h)` 计算。
  清除时日期为零，该键会是一个非常大的值（见[缓解措施](#mitigation)）。
  修复后清除需要 bypass 权限，但该键在清除请求上的取值仍有误导性，另行跟进。
- 目前 `PutObjectRetention` 不求值基于现有对象标签的条件（`s3:ExistingObjectTag/<key>`），
  本设计不改变这一点。

## 兼容性 {#compatibility}

- 持有 `s3:PutObjectRetention` 的调用者没有变化，只有削弱 GOVERNANCE 时现在还需要
  `s3:BypassGovernanceRetention`。
- 没有 `s3:PutObjectRetention` 的调用者现在在入口收到 403。此前带请求头可以得到 200（F1），
  或者得到暴露对象状态的 400/404。
- `s3:PutObjectRetention` 被锁条件键拒绝的调用者，即使持有 bypass 也收到 403（F3）。
  请检查是否有策略依赖 bypass 绕开此类 Deny。
- **混合版本与复制。** 保留期变更作为元数据更新复制，经复制信任路径应用，
  不经过这个处理器。已修复站点不会复查未修复对端已经接受的变更。
  对复制桶而言，所有接受 S3 写入的站点都升级之后，这一保证才成立。

## 测试 {#tests}

测试在处理器层进行，使用真实 IAM 子系统，覆盖[判定表](#decision-table)每一行，另加：

- F1，分别在未修复构建与修复后构建上：无任何授权的主体、挂显式 Deny 的主体，
  尝试清除、GOVERNANCE→COMPLIANCE、新建 COMPLIANCE，分别带与不带请求头、
  带与不带 `versionId`。修复后每一项都应得到 403，已存储的保留期保持不变。
- F2：报告者的脚本运行结束时版本仍在。
- F3：即使允许 bypass，对 `s3:PutObjectRetention` 的条件 Deny 仍返回 403；
  基于锁条件键的条件 Allow 能通过入口检查。
- 对 `s3:*` Allow，同时显式 Deny `s3:BypassGovernanceRetention`：削弱返回 403。
- 属主、服务账号、STS 凭据：各自按有效策略判定。
- 未授权调用者对不存在的桶、未启用锁的桶、不存在的版本都得到 403，
  从响应上无法区分是哪一种。
- 未到期 COMPLIANCE：缩短与改模式仍被拒绝，响应不变。

## 修复发布前的缓解措施 {#mitigation}

F1 无法用 IAM 策略挡住，因为服务端在接受请求前不求值任何策略。在修复发布之前：

- 视所有能向该部署签名请求的凭据，都能在所有启用锁的桶中清除 GOVERNANCE 保留期、
  加上 COMPLIANCE 保留期。不要把凭据发给你不愿赋予这种能力的一方。
- 需要对这类主体保证保留期时，使用 COMPLIANCE 模式：F1 能新建 COMPLIANCE 保留期，
  但不能清除或缩短它。
- 如果 Server 前面有反向代理，可以拒绝来自不受信客户端、带
  `x-amz-bypass-governance-retention` 的 `PUT ?retention` 请求。
  拒绝比剥掉请求头更好，因为已签名的请求头删掉后签名就会失效。
  没有这个请求头，三个问题都无法触发；代价是经由该代理的正当 governance 覆盖也无法进行。
- 不要依赖以 `s3:object-lock-remaining-retention-days` 为条件的 Deny：
  F1 根本不求值它，清除时该键的值也非常大（见[附注](#notes)）。
- 对象元数据只保存当前保留期，无法反映此前的变更。如果审计日志记录请求头，
  请排查带 `x-amz-bypass-governance-retention` 的 `PutObjectRetention` 请求，
  并检查版本上是否出现了意料之外的 COMPLIANCE 保留期。

## 交付计划 {#delivery}

1. 本设计先经对抗性评审，然后提交带上述测试的 Server 补丁。
2. 发布包含修复的 Server，然后在台账登记 `SN-2026-015` 的修复提交与首个包含版本。
3. 在 GHSA-67mv-7hc9-wj88 回复修复情况、扩大后的范围并致谢，然后申请 CVE。
4. 在 `pgsty/silo` 开启私密漏洞报告。
5. 按尽力而为原则通知上游 MinIO：F1 随 #21103 在上游回归。
