---
title: "治理保留与版本覆写修复设计（SN-2026-015 / SN-2026-016）"
linkTitle: "治理保留与版本覆写修复"
date: 2026-10-10
lastmod: 2026-10-14
author: "冯若航"
summary: "SN-2026-015（PutObjectRetention 授权绕过）与 SN-2026-016（版本寻址写入覆写绕过）的问题成因、最小复杂度修复方案、有效性证明与副作用权衡。"
tags: [设计, 安全, Object Lock, IAM, S3]
weight: 7
draft: false
url: "/zh/blog/design/governance-retention-bypass-repair/"
---

> **2026-10-14 状态：修复候选已实现，尚无修复发行。** 公开影响范围与缓解措施见
> [SN-2026-015 安全公告](/zh/blog/security/20260926-governance-retention-bypass/)，
> 修复提交与首个修复发行将在[安全公告台账](/zh/about/security-advisories/#sn-2026-015)登记。

本文围绕“最小复杂度代价、充分且必要”的工程原则，完整说明 **SN-2026-015**（保留期写入路径授权绕过）与 **SN-2026-016**（数据写入路径按版本号原地覆写绕过）四个核心问题：

1. [这是什么问题，怎么来的](#problem)
2. [解决方案是什么](#solution)
3. [这个解决方案为什么有效](#why-it-works)
4. [它是否还会有什么副作用](#side-effects)

---

## 1. 这是什么问题，怎么来的 {#problem}

S3 Object Lock 的核心安全承诺是：处于未到期保留期（`GOVERNANCE` 或 `COMPLIANCE`）或法务保留（`LegalHold`）下的对象版本，其数据内容不可被篡改或删除，其保留期不可被未授权主体缩短、清除或降级。

围绕这一承诺，我们在保留期元数据接口与对象数据写入接口上分别确认了两类继承自上游 MinIO 的防线缺口。

### 1.1 SN-2026-015：`PutObjectRetention` 授权绕过（F1–F3） {#sn-2026-015}

#### 问题表现

客户端调用 `PutObjectRetention`（`PUT /{bucket}/{object}?retention`）并携带 `x-amz-bypass-governance-retention: true` 请求头时，服务端将这个本应只表达“绕过意图”的请求头当成了权限证明，导致三类越权（详见[公告复现记录](/zh/blog/security/20260926-governance-retention-bypass/#verification)）：

| 编号 | 攻击者身份与权限条件 | 可达成的越权结果 |
| --- | --- | --- |
| **F1** | **任意已认证主体**（哪怕在桶上毫无授权，或对 `s3:PutObjectRetention` 与 `s3:BypassGovernanceRetention` 均挂有显式 `Deny`） | 携带 bypass 请求头与空 `<Retention/>`，清除任意启用锁桶内任意版本的 `GOVERNANCE` 保留期；或携带 `<Mode>COMPLIANCE</Mode>`，将 `GOVERNANCE` 改为 `COMPLIANCE`、乃至给无锁/已到期版本施加任意时长的 `COMPLIANCE` 保留期（到期前包括 `root` 在内无人可删） |
| **F2** | 持有 `s3:PutObjectRetention`、但**没有** `s3:BypassGovernanceRetention` 的主体（[GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88) 报告情形） | 携带 bypass 请求头将未到期的 `GOVERNANCE` 保留期缩短至几秒后，待其自然过期后即可凭 `s3:DeleteObjectVersion` 删除该版本 |
| **F3** | 持有 `s3:BypassGovernanceRetention` 的主体 | 携带 bypass 请求头即可无视挂在 `s3:PutObjectRetention` 上的条件 `Deny`（例如限制 `s3:object-lock-remaining-retention-days` 最短保留天数的策略） |

#### 历史成因

1. **2020 年 4 月之前的正确结构**：`PutObjectRetentionHandler` 在入口通过 `checkRequestAuthType` 校验 `s3:PutObjectRetention`，并单独求值 `s3:BypassGovernanceRetention` 后将**授权结果**传入 `enforceRetentionBypassForPut`。请求头仅用于判断是否走绕过分支，从不替代授权。
2. **2020-04 引入缺陷（上游 [#9259](https://github.com/minio/minio/pull/9259)，[`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45)）**：为了支持来自 XML 请求体的三个锁条件键（`s3:object-lock-mode`、`s3:object-lock-retain-until-date`、`s3:object-lock-remaining-retention-days`），上游删掉了处理器入口的 `checkRequestAuthType`，将权限检查下沉到 `enforceRetentionBypassForPut` 内部的新辅助函数 `isPutRetentionAllowed`，同时引入三处逻辑错误：
   - 在 `enforceRetentionBypassForPut` 中，防缩短/改模式守卫写成了 `if !byPassSet`，其中 `byPassSet` 是**原始请求头布尔值**（`IsObjectLockGovernanceBypassSet(r.Header)`），只要客户端发了请求头就直接跳过守卫；
   - 在 `isPutRetentionAllowed` 中，只在**请求体中的目标模式**为 `GOVERNANCE`（`if retMode == objectlock.RetGovernance && byPassSet`）时才向 IAM 求值 `s3:BypassGovernanceRetention`。当请求模式为空（上游 [#9677](https://github.com/minio/minio/pull/9677) 引入空 `<Retention/>` 清除保留期）或 `COMPLIANCE` 时，`byPassSet` 原封不动地保持原始请求头的 `true`；
   - `isPutRetentionAllowed` 末尾用 `if byPassSet || retSet { return ErrNone }` 裁决，把“绕过权限”与“基础写保留期权限”用逻辑或（`||`）并列。
3. **2025-02 部分修复与 2025-04 机械回归**：
   - 上游 [#20929](https://github.com/minio/minio/pull/20929)（[`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32)）在处理器入口加回不带条件键的 `checkRequestAuthType(..., PutObjectRetentionAction, ...)`，临时挡住了 F1（但破坏了依赖锁条件键的 `Allow` 策略，且 F2、F3 仍在）。
   - 50 天后，上游 [#21103](https://github.com/minio/minio/pull/21103)（[`8c7097528`](https://github.com/minio/minio/commit/8c7097528)）重构流式签名校验时，将入口检查机械替换为只验签名、不查策略的 `authenticateRequest`，同时保留了误导性的旧注释 `// Check permissions to perform this object retention operation`，使 F1 重新暴露。SILO 分叉于该提交之后，所有已发布版本均继承了这三处缺陷。

---

### 1.2 SN-2026-016：版本寻址写入覆写绕过及写路径锁缺口（F4 与同源路径） {#sn-2026-016}

#### 问题表现

标准 S3 协议中，公开对象写入操作（`PutObject`、`CopyObject`、`CreateMultipartUpload`、`PostPolicy`）只允许服务端生成新版本号（或在暂停版本控制时写入 `null` 版本），**绝不允许客户端指定目标 `versionId` 去原地改写既有历史版本**。

然而在现有实现中，仅持有普通 `s3:PutObject` 权限（哪怕被显式 `Deny` 了 `s3:PutObjectRetention`、`s3:BypassGovernanceRetention` 与 `s3:DeleteObjectVersion`）的主体，可以通过以下写入路径直接篡改既有版本的数据与保留期：

| 路径编号 | 触发方式 | 安全后果 |
| --- | --- | --- |
| **F4（主路径：显式目标 `versionId` 写入）** | 在 `PutObject`、`CopyObject`、`CreateMultipartUpload`、`PostPolicy` 表单上传或 Snowball 归档解压（PAX `minio.versionId`）请求中传入已有版本的 `versionId`（UUID 或 `null`） | 存储层按指定 `versionId` **原地覆盖该版本的数据载荷与元数据**。对于处于未到期 `GOVERNANCE` 保留期的版本，其数据被直接替换；若桶配置了默认保留期或请求带有锁头，原有的长期 `GOVERNANCE` 保留期还会被一并替换或抹除（仅未到期 `COMPLIANCE` 与 `LegalHoldOn` 能挡住） |
| **同源缺口 A（目录键 `dir/` 隐式 `null` 版本覆写）** | 对启用了对象锁的桶中任意以 `/` 结尾的目录键发起普通 `PUT /{bucket}/dir/`（不带 `?versionId=`） | `putOpts` 将目录键隐式映射为 `opts.VersionID = "null"` 原地覆写，而 `checkPutObjectLockAllowed` 通过 `getOpts` 读到的 `opts.VersionID` 为空，跳过了存量锁检查，导致普通 `PUT dir/` 可原地覆盖已加锁的目录 `null` 版本，并抹除其未到期的 `GOVERNANCE`、**甚至 `COMPLIANCE` 保留期与 `LegalHoldOn`** |
| **同源缺口 B（已持久化目标版本的分段上传完成）** | 分段上传在 `NewMultipartUpload` 时将目标 `VersionID` 持久化到 `xl.meta`，`CompleteMultipartUpload` 通过独立的 `completeMultipartOpts` 提交该版本 | 若升级前已创建了指向既有版本的未完成分段上传，或由复制主体发起分段上传后被仅有 `s3:PutObject` 的普通主体调用 `CompleteMultipartUpload`，完成阶段可在无复制信任的情况下原地覆盖目标版本 |

#### 历史成因

1. **2020-10 为复制开放目标 `versionId`（上游 [#10598](https://github.com/minio/minio/pull/10598)，`RELEASE.2020-10-03`）**：为支持桶复制在目标端用源端原始 UUID 重建版本，上游在 `cmd/object-api-options.go` 的 `putOpts` 中读取请求的 `?versionId=` 并赋给 `opts.VersionID`，但**从未校验请求是否具备复制信任（`trustedReplication`）**。
2. **2020-05 对象锁检查假设公开写入不覆写版本（上游 [#9513](https://github.com/minio/minio/pull/9513)）**：`cmd/bucket-object-lock.go` 的 `checkPutObjectLockAllowed` 在 `if opts.VersionID != "" && !replicaTrusted` 分支中只拦截了未到期的 `COMPLIANCE` 与 `LegalHoldOn`，没有拦截未到期的 `GOVERNANCE`，而是直接放行并用桶默认保留期或新请求头覆盖旧锁。
3. **2023-05 目录对象固定使用 `null` 版本（上游 [#17132](https://github.com/minio/minio/pull/17132)，[`1d0211d39`](https://github.com/minio/minio/commit/1d0211d39)）**：上游在 `putOpts` 和 `delOpts` 中对 `isDirObject(object)` 强制赋予 `nullVersionID` 以避免目录占位符产生多版本和删除标记，但未同步更新 `checkPutObjectLockAllowed` 中的版本解析，留下隐式 `null` 版本漏检。

---

## 2. 解决方案是什么 {#solution}

修复遵循**最小复杂度代价**原则：不新增鉴权机制或跨层状态，只在既有数据流与权限模型的唯一汇合点设置守卫，用最少的代码改动实现充分且必要的闭环。

### 2.1 SN-2026-015 修复方案（保留期写入路径） {#solution-015}

共涉及 3 个文件，净删除冗余分支：

1. **在 `PutObjectRetentionHandler` 入口完成无条件基础鉴权（`cmd/object-handlers.go`）**
   在 `authenticateRequest` 验签并调用 `ParseObjectRetention(r.Body)` 解析完请求体后，**在读取任何桶信息（`GetBucketInfo`）、桶锁配置（`globalBucketObjectLockSys.Get`）或对象版本（`getOpts`）之前**，立即调用 `isRetentionActionAllowed` 校验 `s3:PutObjectRetention`：

   ```go
   // Check permissions to perform this object retention operation. The
   // object-lock condition keys come from the request body, so this is
   // decided before any bucket or object state is read.
   if !isRetentionActionAllowed(policy.PutObjectRetentionAction, bucket, object, objRetention, r, reqInfo.Cred, reqInfo.Owner) {
       writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
       return
   }
   ```

2. **将 `enforceRetentionBypassForPut` 收敛为纯存量状态规则，并修正清除保留期时的剩余天数计算（`cmd/bucket-object-lock.go`）**
   抽出通用的 `isRetentionActionAllowed` 辅助函数，从解析后的请求体构造 `object-lock-mode`、`object-lock-retain-until-date`、`object-lock-remaining-retention-days` 三个条件键并调用 `globalIAMSys.IsAllowed`。同时移除继承自上游的 `math.Abs(objRetention.RetainUntilDate.Sub(t).Hours())` 计算：当请求为清除保留期（空 `<Retention/>`，`RetainUntilDate` 为零值 `0001-01-01`）时，旧代码的时间差先被 Go 截断到 `time.Duration` 的范围，再因取绝对值算出 `106752` 天并写入条件映射，导致 `NumericLessThan` 最短保留天数 `Deny` 策略或 `NumericGreaterThanEquals` 条件 `Allow` 策略被清除操作绕过。修正后对零值或非未来时间统一写入 `"0"` 天，且始终保留该条件键；若省略该键，`NumericLessThan` 的 Deny 仍可能无法命中清除请求。未来日期改用 Unix 秒数差计算，结合纳秒差向上取整为天数，避免 `Time.Sub` 在约 292 年后饱和，从而绕过最长保留天数策略。`enforceRetentionBypassForPut` 在对象写锁下只做与存量版本状态相关的判断：

   ```go
   func enforceRetentionBypassForPut(ctx context.Context, r *http.Request, oi ObjectInfo, objRetention *objectlock.ObjectRetention, cred auth.Credentials, owner bool) error {
       ret := objectlock.GetObjectRetentionMeta(oi.UserDefined)
       if !ret.Mode.Valid() {
           return nil
       }
       t, err := objectlock.UTCNowNTP()
       if err != nil {
           internalLogIf(ctx, err, logger.WarningKind)
           return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
       }
       if ret.RetainUntilDate.Before(t) {
           return nil
       }

       weakens := objRetention.Mode != ret.Mode || objRetention.RetainUntilDate.Before(ret.RetainUntilDate.Time)
       if !weakens {
           return nil
       }
       switch ret.Mode {
       case objectlock.RetGovernance:
           if !objectlock.IsObjectLockGovernanceBypassSet(r.Header) {
               return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
           }
           if !isRetentionActionAllowed(policy.BypassGovernanceRetentionAction, oi.Bucket, oi.Name, objRetention, r, cred, owner) {
               return errAuthentication
           }
           return nil
       default:
           return ObjectLocked{Bucket: oi.Bucket, Object: oi.Name, VersionID: oi.VersionID}
       }
   }
   ```

3. **删除 `isPutRetentionAllowed`（`cmd/auth-handler.go`）**
   彻底移除带有 `byPassSet || retSet` 和请求模式错位判断的旧函数。

### 2.2 SN-2026-016 修复方案（版本寻址写入与同源写路径） {#solution-016}

共涉及 4 处收敛改动：

1. **在 `putOpts` 唯一汇合点拦截非可信复制的 `versionId`（`cmd/object-api-options.go`）**
   所有 HTTP 写入选项构造最终都汇聚到 `putOpts`。在解析 `vid` 前增加 3 行守卫：

   ```go
   vid = strings.TrimSpace(vid)
   // A caller-chosen version ID writes that version in place. Only trusted
   // replication may recreate a source version under its original ID.
   if vid != "" && !trustedReplication {
       return opts, errAuthentication
   }
   ```

2. **补齐 Batch Snowball 归档复制发送端的外层复制标记（`cmd/batch-handlers.go`）**
   SILO 服务端自身的 `batch replicate` 在源与目标均为 SILO/MinIO 时会通过 `writeAsArchive` 发送 Snowball 归档，并在每个 tar PAX 条目中携带 `minio.versionId`。接收端 `PutObjectExtractHandler` 要求外层 HTTP 请求头具备 `X-Minio-Source-Replication-Request: true`（`markerExact`）才会对条目授予 `entryTrusted`。因此在 `writeAsArchive` 中为外层 `PutObjectOptions` 补上复制请求标记：

   ```go
   opts := minio.SnowballOptions{
       Opts: minio.PutObjectOptions{
           Internal: minio.AdvancedPutOptions{
               ReplicationRequest: true,
           },
       },
       InMemory: *r.Source.Snowball.InMemory,
       Compress: *r.Source.Snowball.Compress,
       SkipErrs: *r.Source.Snowball.SkipErrs,
   }
   ```

3. **在预检与对象写锁内双重拦截 `null` 版本锁覆写（`cmd/bucket-object-lock.go`、`cmd/erasure-object.go`、`cmd/erasure-multipart.go`、`cmd/erasure-server-pool.go`）**
   - 在 HTTP 预检阶段，使 `checkPutObjectLockAllowed` 与 `putOpts`/`delOpts` 一致地将目录对象隐式版本解析为 `nullVersionID`，并在 `!replicaTrusted` 时将未到期的 `GOVERNANCE` 与 `COMPLIANCE`、`LegalHoldOn` 一并视为不可覆写（同时在 `PostPolicyBucketHandler` 中对目录对象调用该检查，并在 `CompleteMultipartUploadHandler` 中传入 `trustedReplication`）。
   - 在存储提交阶段（`er.putObject`、`er.CopyObject`、`er.CompleteMultipartUpload` 持有目标对象命名空间写锁 `NewNSLock` 期间），对所有目标版本为 `""` 或 `nullVersionID` 的非复制写入调用 `checkObjectLockedForOverwrite`（多池模式下通过 `replicaObjectInfo` 汇总跨池锁状态）。这样即使并发的 `PutObjectRetention` 或 `PutObjectLegalHold` 在 HTTP 预检之后、存储层获取写锁之前刚刚对 `null` 版本加锁，写锁内的复检也会在落盘前将其拦截并返回 `ObjectLocked`（`400 InvalidRequest`），消除预检到写入之间的 TOCTOU 竞态窗口。桶锁配置读取失败、对象读取失败时同样拒绝写入，只有确认目标版本不存在或未被锁定才放行。内部 `.minio.sys` 存储不使用桶对象锁配置，因此明确排除在此检查之外。跨池读取用于公开写入与已有的复制协调；未指定目标版本号的可信复制回调仍读取所在集合，避免因无关池不可读而新增可用性依赖。

4. **在 `CompleteMultipartUpload` 对象写锁下按持久化 `fi.VersionID` 精确区分 `null` 版本与 UUID 版本覆写（`cmd/erasure-multipart.go`、`cmd/erasure-server-pool.go`）**
   分段上传在初始化与完成之间可能跨越桶版本控制状态的切换（例如未开启版本控制时发起的普通上传在开启版本控制后完成，或开启版本控制时固定了既有 UUID 的上传在暂停版本控制后完成）。因此在对象写锁内不依赖当前 `opts.Versioned` 门控，而是直接依据 `uploadid/xl.meta` 中持久化的 `fi.VersionID` 裁决非复制完成请求（`!opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement`）：
   - 若 `fi.VersionID == "" || fi.VersionID == nullVersionID`（写入 `null` 版本，含版本控制开启前发起的正常在途上传及目录对象上传）：调用 `checkObjectLockedForOverwrite`，在未触发对象锁时正常放行完成，不会误伤版本控制切换期间的正常在途上传；
   - 若 `fi.VersionID` 为非空 UUID：无论当前桶处于 `Enabled` 还是 `Suspended`，通过 `getObjectInfo`（多池经 `replicaObjectInfo`）检查该 UUID 版本是否已存在于磁盘（含普通版本与删除标记）；若已存在则直接返回 `errAuthentication`（`403 AccessDenied`），且不清理未提交的分片文件。

---

## 3. 这个解决方案为什么有效 {#why-it-works}

方案的有效性建立在三条可形式化验证的不变量之上：

### 3.1 不变量一：基础权限与条件键在读取状态前无条件成立（消除 F1、F3 与存在性泄露）

- **单点求值且条件完备**：`PutObjectRetention` 支持的三个对象锁条件键全部派生自请求体 XML 与当前时间，不依赖桶或对象的任何存量元数据。因此在 `ParseObjectRetention` 之后立即调用 `isRetentionActionAllowed(policy.PutObjectRetentionAction, ...)`，既是最早可求值点，也是完全求值点。
- **消除 F1、F3 与清除保留期时的天数条件绕过**：由于不再存在 `byPassSet || retSet` 的短路或逻辑，且清除保留期（空 `<Retention/>`）时 `s3:object-lock-remaining-retention-days` 被精确求值为 `"0"`（而非零值日期取绝对值产生的超大天数），任何缺少 `s3:PutObjectRetention` 授权、或命中 `s3:PutObjectRetention` 条件 `Deny` / 不满足条件 `Allow` 的请求，无论是否携带 bypass 请求头、也无论请求模式是 `GOVERNANCE`、`COMPLIANCE` 还是空模式，都会在第一道关卡被 `403 AccessDenied` 拦截。
- **消除状态泄露**：因为鉴权发生在 `GetBucketInfo`、桶锁配置检查与 `getOpts` 之前，无权限调用者永远只会收到 `403 AccessDenied`，无法通过 `404 NoSuchBucket`/`NoSuchVersion` 或 `400 InvalidBucketObjectLockConfiguration` 探测目标桶或版本是否存在。

### 3.2 不变量二：Bypass 仅由“存量锁未到期且被削弱”触发，且意图与授权必须同时具备（消除 F2）

- **以存量状态而非请求模式为准**：`enforceRetentionBypassForPut` 在对象写锁保护下运行，先检查已存储的 `ret.Mode` 与 `ret.RetainUntilDate`。若存量无锁或已到期，无需 bypass；若请求保持相同模式且日期不早于存量日期（`!weakens`），同样无需 bypass。
- **意图（Header）与授权（IAM）逻辑与（`&&`）**：一旦判定 `weakens == true`（缩短日期、清除为空模式、或改变模式）：
  - 存量为 `COMPLIANCE` 时无条件返回 `ObjectLocked`（线上映射为 `400 InvalidRequest`）；
  - 存量为 `GOVERNANCE` 时，先检查 `IsObjectLockGovernanceBypassSet(r.Header)`（缺头返回 `400 InvalidRequest`），再检查 `isRetentionActionAllowed(policy.BypassGovernanceRetentionAction, ...)`（无权限返回 `403 AccessDenied`）。
- 这既彻底封堵了 F2，又保证了“客户端习惯性附带 bypass 请求头但实际执行保留期延长”的合法调用不会被误杀。

### 3.3 不变量三：公开数据写入不能替换既有 UUID 版本或受锁 null 版本（消除 F4 与同源写路径缺口）

下列数据写入路径遵守这一不变量。未加锁的 null 版本保留正常覆盖语义；可信复制与内部数据迁移继续使用已有的锁状态协调规则：

| 写入路径 | 选项汇合点与复制信任来源 | 修复后的保证 |
| --- | --- | --- |
| `PutObject`（常规 PUT / 桶复制 / 站点复制 / 单对象 Batch 复制） | 验签后经 `evaluateReplicationTrust`（要求 `X-Minio-Source-Replication-Request: true` + `s3:ReplicateObject`）写入上下文，再调用 `putOptsFromReq` -> `putOpts` | 公开客户端（含 `root`）带 `?versionId=` 一律在 `putOpts` 返回 `403`；可信复制正常保留源版本 ID |
| `CopyObject`（含元数据复制） | 源版本走 `srcOpts`，目标版本经 `copyDstOpts` -> `putOptsFromReq` -> `putOpts` | 公开复制源版本正常生成新版本；公开指定目标 `?versionId=` 返回 `403`；可信复制正常覆写/同步目标版本 |
| `PostPolicy`（浏览器表单上传） | 经 `putOptsFromReq` -> `putOpts`（`trustedReplication == false`） | 携带目标 `versionId` 一律返回 `403` |
| `PutObjectExtract`（Snowball / Batch 归档复制） | 外层校验 `markerExact`，逐条目校验 `s3:ReplicateObject` 得出 `entryTrusted`，再传入 `putOpts`；`writeAsArchive` 补齐外层标记 | 未获复制信任的归档条目若带 `minio.versionId` 一律返回 `403`；服务端 `batch replicate` 归档路径正常保留版本 ID |
| `NewMultipartUpload` / `UploadPart` / `UploadPartCopy` | 初始化与加密分片走 `putOptsFromReq` -> `putOpts`；`UploadPartCopy` 强制清除复制信任 | 非可信复制初始化分段上传无法指定目标 `versionId`（返回 `403`） |
| `CompleteMultipartUpload` | 走 `completeMultipartOpts` 并在对象写锁下按 `fi.VersionID` 校验 | 版本控制开启前发起的正常在途上传可正常完成；无论桶是否暂停版本控制，针对既有 UUID 版本的非复制完成请求一律返回 `403` |
| 目录对象 `PUT` / `Copy`（`/{bucket}/dir/`）与持久化目标为 null 的分段上传完成 | `putOpts` 与 `checkPutObjectLockAllowed` 统一映射为 `nullVersionID`，并在对象写锁内执行 `checkObjectLockedForOverwrite` | 未加锁或已过期时保持原行为；一旦目录 `null` 版本存在未到期的 `GOVERNANCE`、`COMPLIANCE` 或 `LegalHoldOn`（含预检后并发提交的锁），非复制覆写立即返回 `400 InvalidRequest`（`ObjectLocked`） |

---

## 4. 它是否还会有什么副作用 {#side-effects}

常规的新版本创建与已获授权的保留期延长保持原有行为。以下变化需要在升级与发布说明中告知运维人员：

1. **仅授予 `s3:BypassGovernanceRetention` 而无 `s3:PutObjectRetention` 的策略不再放行保留期写入（SN-2026-015）**
   - **旧行为**：因 `byPassSet || retSet` 漏洞，仅有 `s3:BypassGovernanceRetention` 的主体带上请求头也能成功调用 `PutObjectRetention`。
   - **新行为**：返回 `403 AccessDenied`。按 AWS S3 规范，`s3:BypassGovernanceRetention` 是削弱治理锁时的附加权限，写保留期始终需要 `s3:PutObjectRetention`。
2. **未授权 `PutObjectRetention` 请求统一返回 `403`，不再返回 `404` 或 `400`（SN-2026-015）**
   - **旧行为**：桶不存在时返回 `404 NoSuchBucket`，桶未开启对象锁时返回 `400 InvalidBucketObjectLockConfiguration`。
   - **新行为**：在读取桶状态前完成鉴权，未授权主体一律收到 `403 AccessDenied`。
3. **清除保留期（空 `<Retention/>`）时 `s3:object-lock-remaining-retention-days` 求值为 `"0"`（SN-2026-015）**
   - **旧行为**：零值日期的时间差经 `time.Duration` 截断与 `math.Abs` 计算后得到 `106752` 天，导致基于 `s3:object-lock-remaining-retention-days` 的最短保留天数策略在清除保留期时失效。
   - **新行为**：清除请求将该条件键求值为 `"0"`，受最短保留天数策略约束的主体无法通过直接清除保留期绕过最小天数限制。
4. **非复制请求（包括 `root`）不能再通过 `?versionId=` 原地覆写对象版本（SN-2026-016）**
   - **旧行为**：任何拥有 `s3:PutObject` 的调用者（含 `root`）带 `?versionId=<id>` 发送 `PUT`、`CopyObject` 或 `NewMultipartUpload` 会原地改写该版本。
   - **新行为**：不带可信复制标记的请求携带目标 `versionId` 时一律返回 `403 AccessDenied`。标准 S3 协议本就不存在公开的按版本号覆写接口。
5. **向 SILO 目标执行 `batch replicate` 时，目标端凭据必须持有 `s3:ReplicateObject`（SN-2026-016）**
   - **旧行为**：若跨集群 `batch replicate` 配置的目标端凭据只有 `s3:PutObject` 而无 `s3:ReplicateObject`，目标端虽然剥离了内部复制头，但 `putOpts` 仍接受了 URL 中的 `?versionId=`，从而静默保留了源版本号。
   - **新行为**：保留源版本号必须通过目标端的复制信任校验（即目标凭据需具备 `s3:ReplicateObject`），否则目标端返回 `403 AccessDenied`。这与桶级复制（Bucket Replication）的权限要求完全一致。
6. **对象锁桶中受锁目录对象（`dir/`）在锁到期前不可被重复 `PUT` 覆写（SN-2026-016）**
   - **旧行为**：目录对象强制共用 `null` 版本且跳过了存量锁检查，重复 `PUT dir/` 会静默覆盖并重置其保留期。
   - **新行为**：当对象锁桶设置了默认保留期、或有人对 `dir/`（`versionId=null`）设置了保留期/法务保留时，在该锁到期前再次写入 `dir/` 会返回 `400 InvalidRequest`（`ObjectLocked`）。
7. **独立跟踪的相邻议题（不并入本次补丁）**
   - `PostRestoreObjectHandler`（归档对象恢复）先读快照再调用 `CopyObject` 回写完整元数据映射的并发竞态属于归档恢复路径的独立问题，另行立项处理。
