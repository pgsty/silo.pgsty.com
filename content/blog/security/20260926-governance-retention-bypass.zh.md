---
title: "SN-2026-015 与 SN-2026-016：S3 Object Lock 治理模式保留锁绕过与指定版本号原地覆盖漏洞分析"
linkTitle: "SN-2026-015：保留锁绕过分析"
date: 2026-09-26
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "深入解析 PutObjectRetention 治理保留锁绕过（SN-2026-015）与指定版本号原地覆盖漏洞（SN-2026-016）的根因、复现路径与修复设计，已于 SILO Server 20261018 完整修复。"
tags: ["Security", "Object Lock", "S3", "WORM", "Compliance", "Governance", "IAM", "SILO"]
weight: 1
url: "/zh/blog/security/20260926-governance-retention-bypass/"
---

**`SN-2026-015`** 与 **`SN-2026-016`** 涵盖了在 [SILO Server 20261018](/zh/blog/release/silo-20261018/) 中通过 PR [`#234`](https://github.com/pgsty/silo/pull/234)（`14042b5aa`）与 PR [`#235`](https://github.com/pgsty/silo/pull/235)（`0d3ba5d4c`）修复的两组 S3 Object Lock 合规保留与不可变性漏洞（配套[修复设计方案](/zh/blog/design/governance-retention-bypass-repair/)）。虽然删除路径此前已按 [CVE-2023-25812](https://github.com/minio/minio/security/advisories/GHSA-c8fc-mjj8-fc63) 正确校验 `s3:BypassGovernanceRetention`，但保留期修改路径（`PutObjectRetention`）与四条原地版本覆写路径仍存在绕过缺陷。

## 漏洞范围：`SN-2026-015` 与 `SN-2026-016`

### SN-2026-015：`PutObjectRetention` 鉴权失效与治理保留锁绕过（`#231`） {#sn-2026-015}

在 `PutObjectRetentionHandler`（`cmd/object-handlers.go`）中，`enforceRetentionBypassForPut` 与 `isPutRetentionAllowed` 存在三处相互叠加的逻辑缺陷，彻底击穿了 S3 Object Lock 的保留锁修改鉴权：
- **F1（携带绕过请求头即可无权限调用 `PutObjectRetention`）**：当请求携带 `x-amz-bypass-governance-retention: true` 且目标对象尚未加锁（或保留期已过）时，代码直接跳过了权限检查——导致一个**既没有 `s3:PutObjectRetention` 也没有 `s3:BypassGovernanceRetention` 权限**的普通已认证账号，只需加上该请求头就能对任意未加锁对象施加不可逆的 `COMPLIANCE` 合规保留锁！
- **F2（无 `s3:BypassGovernanceRetention` 权限即可缩短或清空 `GOVERNANCE` 保留锁）**：由于 `isPutRetentionAllowed` 返回了 `byPass || retSet`，仅拥有 `s3:PutObjectRetention`（`retSet == true`）但**没有任何 `s3:BypassGovernanceRetention` 权限**（`byPass == false`）的调用方，只需在请求头中加上 `x-amz-bypass-governance-retention: true`，即可将处于有效 `GOVERNANCE` 保留期内的对象锁直接清空（`<Retention/>`）或缩短到期时间，随后将该受保护版本彻底删除（对应社区报告 `GHSA-67mv-7hc9-wj88`，由 `szopi00` 披露）。
- **F3（绕过 `s3:PutObjectRetention` 上的 `s3:object-lock-remaining-retention-days` 条件限制）**：对已处于 `GOVERNANCE` 锁定的对象携带 `x-amz-bypass-governance-retention: true` 时，只要 `s3:BypassGovernanceRetention` 通过（`byPass == true`），即便 `s3:PutObjectRetention` 因不满足 `NumericGreaterThanEquals: {"s3:object-lock-remaining-retention-days": 30}` 等最短保留天数条件而失败（`retSet == false`），`byPass || retSet` 依然返回 `true`，从而绕过保留期下限策略。

### SN-2026-016：指定版本号与 `null` 版本原地覆盖绕过（`#234`） {#sn-2026-016}

在全面排查所有能够原地改写已有对象版本的写入路径时，我们进一步发现并封堵了四条写路径不可变性绕过通道（`14042b5aa`）：
1. **在 `PutObject` 与 `CopyObject` 中由客户端指定 `?versionId=`**：非复制流量的普通客户端可在 `PutObject` 或 `CopyObject` 的查询参数中传入 `?versionId=<existing-uuid>`（或在 Snowball `PutObjectExtract` 的 tar PAX 头中传入 `minio.versionId`），直接原地覆盖已有历史版本，而未对目标版本执行 WORM 保留期与法律冻结（Legal Hold）拦截。
2. **目录对象（`key/`）覆盖 `null` 版本**：上传以 `/` 结尾的目录对象时，即使在开启了版本控制与 Object Lock 的桶中也会固定写入 `nullVersionID`，从而在未检查 `null` 版本现有保留锁的情况下原地覆盖数据。
3. **`CompleteMultipartUpload` 原地覆盖 `null` 版本**：当桶挂起版本控制（Versioning Suspended）且存在受保护的 `null` 版本对象时，通过 `CompleteMultipartUpload` 完成分段上传会原地覆盖该 `null` 版本而未检查其 WORM 锁状态。
4. **内部复制请求头伪造**：未持有 `s3:ReplicateObject` 权限的普通 `s3:PutObject` 调用方不应被允许伪造 `X-Minio-Source-Replication-Request` 等内部复制头。

---

## S3 Object Lock 的标准权限语义 {#semantics}

按照 AWS S3 Object Lock 规范，`PutObjectRetention` 必须同时守护两条相互正交的权限边界：

| 目标对象当前状态 | 请求提交的 `<Retention>` 变更 | 必需的 IAM 权限 | 必需的请求头 |
|---|---|---|---|
| 未加锁，或原保留期已过期 | 设置未来的 `GOVERNANCE` 或 `COMPLIANCE` 保留期 | `s3:PutObjectRetention` | 无 |
| 处于有效 `GOVERNANCE` 锁定期 | 在同模式下将 `RetainUntilDate` 延长至更晚时间 | `s3:PutObjectRetention` | 无 |
| 处于有效 `GOVERNANCE` 锁定期 | 清空（`<Retention/>`）、缩短 `RetainUntilDate`，或将模式改为 `COMPLIANCE` | `s3:PutObjectRetention` **且** `s3:BypassGovernanceRetention` | `x-amz-bypass-governance-retention: true` |
| 处于有效 `COMPLIANCE` 锁定期 | 在 `COMPLIANCE` 模式下将 `RetainUntilDate` 延长至更晚时间 | `s3:PutObjectRetention` | 无 |
| 处于有效 `COMPLIANCE` 锁定期 | 清空、缩短保留期，或降级为 `GOVERNANCE` | **任何身份均绝对禁止** | 禁止（返回 `AccessDenied`） |

---

## 复现路径与验证对比 {#verification}

在 `20261018` 之前的版本上（基线提交 `b0a540190`），F1～F3 均可稳定复现：

### 复现 1：无 `s3:BypassGovernanceRetention` 权限清空治理锁并删库（F2）

假设用户 `nobypass` 仅被授予 `s3:PutObjectRetention` 与 `s3:DeleteObjectVersion`，**没有** `s3:BypassGovernanceRetention` 权限：

| 步骤 | `nobypass` 发起的请求 | `20261018` 之前结果 | Server `20261018` 结果 |
|---|---|---|---|
| 1 | 对象 `doc.txt`（版本 `v1`）处于 `GOVERNANCE` 锁定状态，保留至 `2030-01-01` | 受保护状态 | 受保护状态 |
| 2 | `DELETE /bucket/doc.txt?versionId=v1` | `403 AccessDenied` | `403 AccessDenied` |
| 3 | `PUT /bucket/doc.txt?retention&versionId=v1`，附带请求头 `x-amz-bypass-governance-retention: true` 与空请求体 `<Retention/>` | **`200 OK`（治理锁被直接清空！）** | `403 AccessDenied` |
| 4 | 再次执行 `DELETE /bucket/doc.txt?versionId=v1` | **`204 No Content`（受保护版本被永久删除！）** | 对象保持锁定，拒绝删除 |

### 复现 2：零保留权限账号对未加锁对象强加合规锁（F1）

假设用户 `zeroperm` **既没有** `s3:PutObjectRetention` **也没有** `s3:BypassGovernanceRetention` 权限：

| 步骤 | `zeroperm` 发起的请求 | `20261018` 之前结果 | Server `20261018` 结果 |
|---|---|---|---|
| 1 | `PUT /bucket/unlocked.txt?retention`（不带 bypass 头），请求体设为 `<Mode>COMPLIANCE</Mode><RetainUntilDate>2099-01-01T00:00:00Z</RetainUntilDate>` | `403 AccessDenied` | `403 AccessDenied` |
| 2 | 发送完全相同的请求，仅**额外附带请求头 `x-amz-bypass-governance-retention: true`** | **`200 OK`（成功打上不可撤销的 2099 年合规死锁！）** | `403 AccessDenied` |

### 复现 3：绕过 `s3:object-lock-remaining-retention-days` 最短保留天数条件（F3）

假设用户 `govadmin` 拥有无条件的 `s3:BypassGovernanceRetention`，但其 `s3:PutObjectRetention` 权限带有条件限制 `NumericGreaterThanEquals: {"s3:object-lock-remaining-retention-days": 30}`（要求设置的保留期至少为 30 天）。在已加 `GOVERNANCE` 锁的对象上携带 `x-amz-bypass-governance-retention: true` 并将保留期改为 5 天，修复前由于 `byPass == true` 直接满足了 `byPass || retSet`，30 天下限条件被完全绕过。

---

## 根本原因剖析 {#root-cause}

在 `cmd/object-handlers.go` 中，`PutObjectRetentionHandler` 在入口处仅调用了验证签名的 `authenticateRequest`，而将**全部**权限判断委托给了 `enforceRetentionBypassForPut` 及其内部调用的 `isPutRetentionAllowed`：

```go
// 20261018 之前存在缺陷的 isPutRetentionAllowed
func isPutRetentionAllowed(ctx context.Context, r *http.Request, bucket, object string,
    retDays int, retDate time.Time, retMode RetentionMode, byPassSet bool,
    cred auth.Credentials, owner bool, claims map[string]interface{}) (retSet, byPass bool) {

    if !byPassSet {
        return isReqAuthenticated(ctx, r, iampolicy.PutObjectRetentionAction, ...), false
    }

    byPass = isReqAuthenticated(ctx, r, iampolicy.BypassGovernanceRetentionAction, ...)
    retSet = isReqAuthenticated(ctx, r, iampolicy.PutObjectRetentionAction, ...)
    return retSet, byPass || retSet
}
```

而在 `enforceRetentionBypassForPut` 中：
1. 当目标对象当前**没有**有效保留锁（`opts.Mode == ""`）时，代码未正确要求 `retSet` 必须为真，只要请求头带了 `x-amz-bypass-governance-retention: true` 就会放行（触发 **F1**）；
2. 当目标对象处于 `GOVERNANCE` 模式且请求携带了 `x-amz-bypass-governance-retention: true` 时，`isPutRetentionAllowed` 的第二个返回值竟被写成了 `byPass || retSet`（逻辑或）！于是只要 `retSet == true`（仅有 `s3:PutObjectRetention`），第二个返回值就成了 `true`（触发 **F2**）；反过来只要 `byPass == true`（仅有 `s3:BypassGovernanceRetention`），即便 `retSet == false` 也会放行（触发 **F3**）。

### 上游五年演进历史 {#history}

通过 `git log` 追溯历史可以清楚看到这三个漏洞是如何在五年间的三次提交中逐步成型的：
- **2020-04（[`43a3778b4`](https://github.com/minio/minio/commit/43a3778b4)，`minio/minio#9259`）**：首次引入 `enforceRetentionBypassForPut` 与 `isPutRetentionAllowed`，埋下了 `byPass || retSet` 将两项正交权限做逻辑或运算的隐患。
- **2025-02（[`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32)，`minio/minio#20929`）**：重构了 `PutObjectRetentionHandler` 中的保留锁检查分支。
- **2025-04（[`8c7097528`](https://github.com/minio/minio/commit/8c7097528)，`minio/minio#21103`）**：将 `PutObjectRetentionHandler` 入口的 `checkRequestAuthType` 替换为了仅验签不鉴权的 `authenticateRequest`，使 `enforceRetentionBypassForPut` 成为唯一的鉴权关口，从而让 **F1** 彻底暴露给任何零权限的已认证用户。

---

## 修复方案设计 {#design}

### 五条核心安全不变量 {#invariants}

我们的修复方案在 `PutObjectRetention`（`0d3ba5d4c`）与全部对象写入路径（`14042b5aa`）上严格建立并锁死了五条安全不变量：
1. **不变量 1（`s3:PutObjectRetention` 必检）**：任何 `PutObjectRetention` 请求，无论是否携带 `x-amz-bypass-governance-retention` 请求头，都必须通过 `s3:PutObjectRetention` 权限校验（包含 `s3:object-lock-remaining-retention-days`、`s3:object-lock-retention-mode`、`s3:object-lock-retain-until-date` 与 `s3:ExistingObjectTag/<key>` 条件）。
2. **不变量 2（削弱有效 `GOVERNANCE` 锁必须叠加 `s3:BypassGovernanceRetention`）**：若目标版本当前处于未过期的 `GOVERNANCE` 锁定期，且请求试图清空保留锁（`Mode == ""`）、缩短保留截止时间（`!RetainUntilDate.After(existing.RetainUntilDate)`）或跨模式变更，则请求必须**同时**携带 `x-amz-bypass-governance-retention: true` 并通过 `s3:BypassGovernanceRetention` 权限校验。
3. **不变量 3（`COMPLIANCE` 绝对不可削弱）**：处于未过期 `COMPLIANCE` 锁定期的对象版本，任何身份均不可清空、缩短保留期或降级为 `GOVERNANCE`。
4. **不变量 4（禁止非复制请求指定 `?versionId=` 覆盖写）**：非复制 S3 客户端不得在 `PutObject`、`CopyObject` 或 `PutObjectExtract` 中指定已有或自定义的 `versionId` 原地覆写对象。
5. **不变量 5（原地覆盖 `null` 版本必须执行写锁检查）**：任何会原地替换已有 `null` 版本的写入路径（挂起版本控制桶上的 `PutObject`、目录对象 `key/`、以及 `CompleteMultipartUpload`），在覆写前必须对已有 `null` 版本执行完整的 WORM 保留期与法律冻结检查。

### 鉴权检查的位置与职责划分 {#placement}

在 `PutObjectRetentionHandler` 与 `enforceRetentionBypassForPut` 中：
- `s3:PutObjectRetention`（`retOK`）始终基于解析后的目标保留参数（`retDays`、`retDate`、`retMode`）与对象现有标签求值，若为 `false` 立即返回 `ErrAccessDenied`；
- `s3:BypassGovernanceRetention`（`bypassOK`）独立求值，且仅在修改动作确实需要突破现有 `GOVERNANCE` 锁时作为附加必要条件强制要求。

### `PutObjectRetention` 完整判定真值表 {#decision-table}

| 行号 | 现有锁状态 | 请求的变更动作 | `x-amz-bypass-governance-retention` | `retOK` (`s3:PutObjectRetention`) | `bypassOK` (`s3:BypassGovernanceRetention`) | 最终结果 |
|---|---|---|---|---|---|---|
| 1 | 任意状态 | 任意变更 | `false` 或 `true` | `false` | 任意 | **`403 AccessDenied`**（封堵 F1 与 F3） |
| 2 | 未加锁或已过期 | 设置未来保留期 | `false` 或 `true` | `true` | 不要求 | **`200 OK`** |
| 3 | 有效 `GOVERNANCE` | 延长 `RetainUntilDate` | `false` 或 `true` | `true` | 不要求 | **`200 OK`** |
| 4 | 有效 `GOVERNANCE` | 清空（`<Retention/>`）或缩短 `RetainUntilDate` | `false` | `true` | 任意 | **`403 AccessDenied`** |
| 5 | 有效 `GOVERNANCE` | 清空（`<Retention/>`）或缩短 `RetainUntilDate` | `true` | `true` | `false` | **`403 AccessDenied`**（封堵 F2） |
| 6 | 有效 `GOVERNANCE` | 清空（`<Retention/>`）或缩短 `RetainUntilDate` | `true` | `true` | `true` | **`200 OK`** |
| 7 | 有效 `COMPLIANCE` | 清空、缩短或降级为 `GOVERNANCE` | `false` 或 `true` | 任意 | 任意 | **`403 AccessDenied`** |

### 五个被否决的替代方案 {#alternatives}

在设计复核阶段，我们评估并否决了五个看似更简单的改法：
1. **仅把 `isPutRetentionAllowed` 中的 `byPass || retSet` 改成 `byPass && retSet`**：这样虽能修掉 F2 与 F3，但未加锁分支上的 **F1** 依然存在；而且如果一个仅有 `s3:PutObjectRetention` 的用户在正常**延长**保留期时顺手带上了 `x-amz-bypass-governance-retention: true`，`byPass && retSet` 会错误地拒绝该合法延长请求。
2. **直接在 `PutObjectRetentionHandler` 最顶部加一行 `checkRequestAuthType(..., PutObjectRetentionAction)`**：在 Handler 入口处，请求体 XML（`<Retention>`）尚未解析，磁盘上的对象现有标签也尚未读取，此时求值会导致所有依赖 `s3:object-lock-remaining-retention-days`、`s3:object-lock-retain-until-date`、`s3:object-lock-retention-mode` 与 `s3:ExistingObjectTag/<key>` 的 IAM 策略条件全部失效！
3. **只要请求头带了 `x-amz-bypass-governance-retention: true` 就一律要求 `s3:BypassGovernanceRetention`**：不符合 S3 规范——只有当操作确实需要突破有效 `GOVERNANCE` 锁时才需要检查 `s3:BypassGovernanceRetention`。
4. **直接禁止传入空 `<Retention/>` 请求体**：通过 `<Retention/>` 清空治理锁是 `mcli retention clear` 长期依赖的公开扩展能力；只要调用方同时具备 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention` 且显式传入 `x-amz-bypass-governance-retention: true`，就应当继续支持。
5. **仅在开启了 Object Lock 的桶上拦截 `?versionId=` 写入（`SN-2026-016`）**：允许普通客户端通过 `?versionId=` 原地篡改已有历史版本违背了所有版本化桶的不可变语义，因此在所有桶上统一拦截非复制流量的 `?versionId=` 写入。

### 实现细节补充 {#notes}

- **空 `<Retention/>` 与超长年份下的 `s3:object-lock-remaining-retention-days` 计算**：当调用方发送 `<Retention/>` 清空治理锁时，`retDate` 为零值 `time.Time{}`。旧代码直接对零值时间调用耗时差计算，由于 `time.Duration` 最多只能表示约 290 年，算出了约 `-106751` 天的荒谬负数！提交 `0d3ba5d4c` 将零值 `retDate` 的剩余天数明确归零，并使用不溢出的日历秒差计算未来保留天数，使 `2400` 年等远期保留时间也不会因 `time.Duration` 290 年上限而发生饱和截断。
- **`s3:ExistingObjectTag/<key>` 完整透传**：`s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention` 两次鉴权均完整传入目标版本的现有对象标签。

---

## 兼容性影响 {#compatibility}

- **标准 S3 客户端与 `mcli retention` 工作流**：完全兼容。使用 `mcli retention clear --governance` 清空或缩短治理模式保留锁的账号，必须按规范同时具备 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention` 权限。
- **跨站点/双向桶复制（Replication）**：需要保留源端 `versionId` 的合法复制流量必须持有 `s3:ReplicateObject` 权限（标准复制策略已默认包含）。

---

## 回归测试矩阵 {#tests}

PR [`#234`](https://github.com/pgsty/silo/pull/234) 与 PR [`#235`](https://github.com/pgsty/silo/pull/235) 在 `cmd/object-handlers-lock_test.go` 与 `cmd/bucket-versioning_test.go` 中固化了完整回归测试矩阵：
- 覆盖 `PutObjectRetention` 判定真值表的全部 7 行组合（含 F1 零权限调用方、F2 仅 `PutObjectRetention` 调用方、F3 仅 `BypassGovernanceRetention` 且带最短保留天数条件的调用方）；
- 覆盖超过 `time.Duration` 290 年上限的远期保留时间（如 `2400-01-01T00:00:00Z`）；
- 覆盖 `PutObject`、`CopyObject` 与 `PutObjectExtract` 携带 `?versionId=` / `minio.versionId` 的拦截；
- 覆盖目录对象（`key/`）与 `CompleteMultipartUpload` 针对受锁 `null` 版本的原地覆盖拦截。

---

## 缓解措施与版本升级 {#mitigation}

### 交付状态 {#delivery}

**`SN-2026-015`**（`0d3ba5d4c`，PR `#235`）与 **`SN-2026-016`**（`14042b5aa`，PR `#234`）均已随 [SILO Server 20261018](/zh/blog/release/silo-20261018/) 正式发布。所有依赖 S3 Object Lock WORM 治理模式或合规模式保护数据的生产环境应尽快升级至 `20261018`。
