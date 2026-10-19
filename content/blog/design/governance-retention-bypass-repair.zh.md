---
title: "对象锁保留期越权与版本覆写漏洞修复设计（SN-2026-015 / SN-2026-016）"
date: 2026-10-14
lastmod: 2026-10-19
summary: "梳理对象锁保留期鉴权短路缺陷（SN-2026-015）与版本寻址写入覆写缺陷（SN-2026-016）的外部报告验证、完整历史溯源、入口与存储写锁双重防线设计、预检 Fail-Closed 加固，以及候选方案的对抗评测与取舍。"
tags: ["Silo", "Security", "Object Lock", "WORM", "S3", "IAM"]
---

**2026-10-19 核验状态：** PR #234 与 #235 的完整修复包含于 [Server 20261018 正式版](/zh/blog/release/silo-20261018/)，GitHub Release 已正式发布。20261015 为已被替代的草稿，Server 20260916 仍受影响。本文保留原始设计与源码验证，升级要求见[安全公告](/zh/blog/security/20260926-governance-retention-bypass/)。

本文档完整记录针对外部报告与内部关联排查发现的两处对象锁（Object Lock / WORM）安全缺陷——**`SN-2026-015`（`PutObjectRetention` 绕过请求头越权与条件策略失灵）**与 **`SN-2026-016`（版本寻址写入覆写绕过及写路径锁缺口）**——的事实核验、Git 历史溯源、修复设计、关键路径影响评估与候选方案的对抗验证取舍。

关联公开安全公告：
- [SN-2026-015 / SN-2026-016：对象锁保留期授权绕过与带版本写入覆写漏洞](/zh/blog/security/20260926-governance-retention-bypass/)

---

## 1. 问题确认与外部报告核验 {#problem}

### 1.1 两条独立外部报告来源

本次修复覆盖两条独立报告链及一次内部同源排查：

1. **首报（F2 主路径）**：由外部安全研究者 **szopi00** 通过 GitHub Security Advisory 私密报告（[GHSA-67mv-7hc9-wj88](https://github.com/pgsty/pigsty/security/advisories/GHSA-67mv-7hc9-wj88)），指出持有 `s3:PutObjectRetention` 但无 `s3:BypassGovernanceRetention` 的主体可通过发送原始 `x-amz-bypass-governance-retention: true` 请求头缩短未到期的 `GOVERNANCE` 保留期。
2. **独立外部报告（F1 / F2 / F3）**：另一份外部报告独立复现了三类攻击向量：未经授权将 `GOVERNANCE` 改为多年 `COMPLIANCE`、绕过基于请求体条件键的 `s3:PutObjectRetention` Deny 策略，以及无 bypass 授权缩短未到期的 `GOVERNANCE` 保留期。
3. **内部同源关联排查（`SN-2026-016` / F4 与目录对象 `null` 版本覆写）**：在收到上述报告后，我们对“拥有写权限但无 bypass 权限的调用者还能通过哪些入口破坏受锁版本”进行了全量写路径审计，定位到非可信复制请求携带 `?versionId=` 原地覆写历史版本、目录键 `dir/` 隐式 `null` 版本覆写以及已持久化目标版本的分段上传完成三条同源缺口。

### 1.2 独立报告逐项核验结论

以下核验与代码行号针对修复前的 [`bcb5fc956`](https://github.com/pgsty/silo/commit/bcb5fc956) 快照：

| 邮件报告论断 | 核验结果 | 代码证据与定性说明 |
| --- | --- | --- |
| **危害 1（未经授权设置 COMPLIANCE 保留期）**：无 `s3:BypassGovernanceRetention`（甚至无 `s3:PutObjectRetention` 或被条件 `Deny`）的攻击者可将 `GOVERNANCE` 改为 `COMPLIANCE` 或直接写入超长 `COMPLIANCE` | **完全属实** | `cmd/bucket-object-lock.go` 第 205 行仅检查原始请求头 `!byPassSet`；`cmd/auth-handler.go` 第 773–781 行在目标模式为 `COMPLIANCE` 时跳过 IAM 求值，保持 `byPassSet == true`，并于 `if byPassSet \|\| retSet` 直接返回 `ErrNone`。一旦写成 `COMPLIANCE`，即使 S3 `root` 管理员也无法通过 S3 API 在到期前删除 |
| **危害 2（削弱保留期 / 勒索软件擦除前置）**：无 `s3:BypassGovernanceRetention` 的凭据可携带请求头缩短未到期 `GOVERNANCE` 保留期 | **完全属实** | 请求体模式为 `GOVERNANCE` 时，虽然 `isPutRetentionAllowed` 把 `byPassSet` 更新为 `false`，但紧接着求值 `retSet`（`s3:PutObjectRetention`）为 `true`，末尾 `byPassSet \|\| retSet` 依然放行 |
| **SILO 与上游 MinIO 在 `DeleteObjectVersion` 上的爆炸半径差异**：SILO 限制了无 `s3:DeleteObjectVersion` 时的历史版本删除；上游 MinIO 将 `s3:DeleteObjectVersion` 设为 `DenyOnly: true`，仅凭 `s3:DeleteObject` 即可等锁到期后删空历史版本 | **完全属实** | SILO 在提交 [`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4)（2026-09-02）引入 `deleteObjectAction` 显式要求 `s3:DeleteObjectVersion`；而上游 MinIO `cmd/auth-handler.go` 至今对指定 `versionId` 的删除使用 `DenyOnly: true` |
| **受影响范围与代码行号**：缺陷位于服务端 `cmd/` 而非 `silo-pkg`；SILO `RELEASE.2026-09-03T13-18-01Z`（[`9b11dc94`](https://github.com/pgsty/silo/commit/9b11dc94)）、`RELEASE.2026-09-16T00-00-00Z`、修复前的 SILO `main`（`bcb5fc956`）及当时核验的上游 `minio/minio` 快照均受影响 | **完全属实** | `silo-pkg` 的 IAM 策略引擎对 `Deny` 求值完全正确；问题纯粹出在 `cmd/object-handlers.go`、`cmd/bucket-object-lock.go` 与 `cmd/auth-handler.go` 的调用编排与布尔短路逻辑 |
| **复现脚本中无法用无条件 `Deny s3:PutObjectRetention` 规避**：若对应用账号无条件 `Deny s3:PutObjectRetention`，则连向配置了默认保留期（Default Retention）的桶执行普通 `PutObject` 也会失败 | **完全属实** | 普通 `PutObject` 在相关对象锁检查路径中依赖 `s3:PutObjectRetention`，无条件 `Deny` 会阻断正常业务写入，因此生产策略只能使用带条件键的 `Deny`——而这正是被 F3 绕过的场景 |

---

## 2. 缺陷全景与 Git 历史溯源 {#provenance}

### 2.1 SN-2026-015：`PutObjectRetention` 鉴权短路与绕过漏洞（F1 / F2 / F3） {#sn-2026-015}

在修复前的实现中，`PUT /{bucket}/{object}?retention` 存在两处结构性错位：
1. **处理器入口只做签名认证，不做策略鉴权**：`PutObjectRetentionHandler` 调用 `authenticateRequest(ctx, r, policy.PutObjectRetentionAction)`，该函数只验证签名/令牌有效性，不查询 IAM 策略；
2. **存量锁绕过检查与 IAM 策略裁决混杂且布尔方向写反**：在对象写锁回调 `enforceRetentionBypassForPut` 及辅助函数 `isPutRetentionAllowed` 中，服务端直接信任了客户端请求头 `x-amz-bypass-governance-retention: true`，并用 `byPassSet || retSet` 将“绕过权限”与“写保留期基础权限”做逻辑或（`||`）短路。

由此产生三类具体漏洞（F1–F3）及一处清除保留期时的剩余天数计算缺陷：

| 编号 | 攻击者拥有的权限 | 触发方式与安全后果 |
| --- | --- | --- |
| **F1** | 仅通过身份认证、**没有任何对象锁权限**（无 `s3:PutObjectRetention`、无 `s3:BypassGovernanceRetention`） | 携带 `x-amz-bypass-governance-retention: true` 发送：① 空 `<Retention/>` 直接**清零**未到期的 `GOVERNANCE` 保留期；② `<Mode>COMPLIANCE</Mode>` 将任意对象（含已有 `GOVERNANCE` 锁的对象）直接**设为到期前不可解除的 `COMPLIANCE` 保留期** |
| **F2** | 持有 `s3:PutObjectRetention`、但**没有** `s3:BypassGovernanceRetention`（两份报告均覆盖） | 携带 `x-amz-bypass-governance-retention: true` 将未到期的 `GOVERNANCE` 保留期缩短至几秒后，或原地改为 `COMPLIANCE` |
| **F3** | 持有 `s3:PutObjectRetention`（受条件 `Deny` 限制）或持有 `s3:BypassGovernanceRetention` | ① 目标模式为 `COMPLIANCE` 或空 `<Retention/>` 时，携带 bypass 请求头直接跳过 `isPutRetentionAllowed` 中的策略求值，**完全绕过挂在 `s3:PutObjectRetention` 上的条件 `Deny`**（独立报告症状 2）；② 持有 `s3:BypassGovernanceRetention` 时，在 `GOVERNANCE` 模式下同样因 `byPassSet \|\| retSet` 绕过 `s3:PutObjectRetention` 条件 `Deny` |
| **附带算术缺陷** | 持有受 `s3:object-lock-remaining-retention-days` 条件限制的 `s3:PutObjectRetention` | 发送空 `<Retention/>` 清除保留期时，`RetainUntilDate` 为零值 `0001-01-01`，旧代码 `math.Abs(objRetention.RetainUntilDate.Sub(t).Hours())` 因 `time.Duration` 292 年上限截断后取绝对值算出 **`106,752` 天**，导致“禁止剩余保留期小于 N 天”的 `NumericLessThan` 策略被清除操作直接绕过 |

#### 精确 Git 提交溯源

1. **2019-11 至 2020-03 的正确初始设计**：
   - [`ca96560d5`](https://github.com/minio/minio/commit/ca96560d5)（2019-11-20，Poorna Krishnamoorthy）与 [`f931fc7bf`](https://github.com/minio/minio/commit/f931fc7bf)（2019-11-25）、[#9030](https://github.com/minio/minio/pull/9030)（[`97cbac604`](https://github.com/minio/minio/commit/97cbac604)，2020-03-04）：`PutObjectRetentionHandler` 在入口通过 `checkRequestAuthType` 强制校验 `s3:PutObjectRetention`，并单独向 IAM 求值 `s3:BypassGovernanceRetention` 后将**授权结果布尔值**传入 `enforceRetentionBypassForPut`。请求头从不替代 IAM 授权。
2. **2020-04 引入核心缺陷（上游 [#9259](https://github.com/minio/minio/pull/9259)，[`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45)，2020-04-06，Harshavardhana）**：
   - 为支持来自 XML 请求体的三个锁条件键（`s3:object-lock-mode`、`s3:object-lock-retain-until-date`、`s3:object-lock-remaining-retention-days`），该提交删掉了 handler 入口的 `checkRequestAuthType`，将鉴权下沉到 `enforceRetentionBypassForPut` 内部的新函数 `isPutRetentionAllowed`，一举引入三处错误：
     - `enforceRetentionBypassForPut` 直接读取原始请求头 `byPassSet := IsObjectLockGovernanceBypassSet(r.Header)`，并用 `if !byPassSet` 包裹防缩短守卫；
     - `isPutRetentionAllowed` 仅在 `if retMode == objectlock.RetGovernance && byPassSet` 时才向 IAM 求值 `s3:BypassGovernanceRetention`，导致 `retMode == COMPLIANCE` 时 `byPassSet` 保持原始请求头的 `true` 不变；
     - 函数末尾写成 `if byPassSet || retSet { return ErrNone }`，造成 `||` 短路。
3. **2020-05 扩大 F1 爆炸半径（上游 [#9677](https://github.com/minio/minio/pull/9677)，[`bede525dc`](https://github.com/minio/minio/commit/bede525dc)，2020-05-22，Ashish Kumar Sinha）**：
   - 允许发送空 `<Retention/>`（`Mode == ""`）清除 `GOVERNANCE` 锁，同样落在 `retMode != RetGovernance` 分支，使零权限攻击者不但能锁死 `COMPLIANCE`，还能直接清零 `GOVERNANCE` 锁，同时引入了零值日期 `math.Abs` 算出 `106,752` 天的算术缺陷。
4. **2025-02 临时遮蔽 F1 与 2025-04 机械回归**：
   - 上游 [#20929](https://github.com/minio/minio/pull/20929)（[`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32)，2025-02-12，Ramon de Klein）发现零权限用户可调用 `PutObjectRetention`，于是在 handler 入口加回不带条件键的 `checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object)`，临时挡住了 F1（但破坏了带锁条件键的 `Allow` 策略，且完全未修 F2、F3）。
   - 仅 50 天后，上游 [#21103](https://github.com/minio/minio/pull/21103)（[`8c7097528`](https://github.com/minio/minio/commit/8c7097528)，2025-04-03，Harshavardhana）在重构流式签名验证时，把入口的 `checkRequestAuthType` 机械替换为**只验签名、不查策略**的 `authenticateRequest`，却保留了上方的旧注释 `// Check permissions to perform this object retention operation`，导致 F1 重新彻底暴露。SILO 分叉自该提交之后，完整继承了 F1–F3。

---

### 2.2 SN-2026-016：版本寻址写入覆写绕过及写路径锁缺口（F4 与同源路径） {#sn-2026-016}

标准 S3 协议中，公开对象写入操作（`PutObject`、`CopyObject`、`CreateMultipartUpload`、`PostPolicy`）只允许服务端生成新版本号（或在未开启/暂停版本控制时写入 `null` 版本），**绝不允许客户端指定目标 `versionId` 去原地改写既有历史版本**。然而现有实现存在三处同源写路径缺口：

| 路径编号 | 触发方式 | 安全后果 |
| --- | --- | --- |
| **F4（显式目标 `versionId` 写入）** | 普通 `s3:PutObject` 主体在 `PutObject`、`CopyObject`、`CreateMultipartUpload`、`PostPolicy` 或 Snowball 归档解压（PAX `minio.versionId`）中传入既有版本的 `versionId`（UUID 或 `null`） | 存储层按指定 `versionId` **原地覆盖该版本的数据载荷与元数据**。对于处于未到期 `GOVERNANCE` 保留期的版本，其数据与保留期被直接替换或抹除 |
| **同源缺口 A（目录键 `dir/` 隐式 `null` 版本覆写与慢速请求体竞态）** | 对启用了对象锁的桶中任意以 `/` 结尾的目录键发起普通 `PUT /{bucket}/dir/`（不带 `?versionId=`） | ① `putOpts` 将目录键隐式映射为 `opts.VersionID = "null"` 原地覆写，而 `checkPutObjectLockAllowed` 通过 `getOpts` 读到的 `opts.VersionID` 为空，跳过存量锁检查，导致普通 `PUT dir/` 可原地覆盖并抹除目录 `null` 版本的 `GOVERNANCE`、**`COMPLIANCE` 保留期与 `LegalHoldOn`**；② 即便修补了 HTTP 预检，由于预检发生在读取 HTTP 请求体之前，写入者仍可通过预检后暂停发送请求体字节流，待管理员对 `dir/` 加上 `COMPLIANCE` 锁后再发完请求体，在存储层覆盖已加锁的 `null` 版本；③ 预检阶段 `checkPutObjectLockAllowed` 仅在 `getObjectInfoFn` 返回 `err == nil` 时检查锁状态，遇到读仲裁失败等错误时直接跳过检查放行写入 |
| **同源缺口 B（已持久化目标版本的分段上传完成）** | 分段上传在 `NewMultipartUpload` 时将目标 `fi.VersionID` 持久化到 `.minio.sys/multipart/.../uploadID/xl.meta`，`CompleteMultipartUpload` 通过独立的 `completeMultipartOpts` 提交该版本 | 升级前已创建的遗留分段上传任务、由复制主体发起的任务、或旧上传状态恢复后与已复制落盘的同 UUID 版本发生碰撞的任务，其目标版本号保存在 `uploadID/xl.meta` 中且不经过 `putOpts`；若完成阶段不在对象写锁下对 `fi.VersionID` 执行存量版本查重，仅有 `s3:PutObject` 的调用者即可在目标版本被加上 `COMPLIANCE` 锁后完成上传并覆写该版本 |

#### 精确 Git 提交溯源

1. **2020-05 对象锁检查遗漏 `GOVERNANCE`（上游 [#9513](https://github.com/minio/minio/pull/9513)，[`9b3b04ece`](https://github.com/minio/minio/commit/9b3b04ece)，2020-05-04）**：`cmd/bucket-object-lock.go` 的 `checkPutObjectLockAllowed` 在 `if opts.VersionID != "" && !replicaTrusted` 分支中只拦截了未到期的 `COMPLIANCE` 与 `LegalHoldOn`，漏掉了未到期的 `GOVERNANCE`，且仅在 `getObjectInfoFn` 返回 `err == nil` 时才进入检查。
2. **2020-09 为桶复制开放目标 `versionId` 却未校验复制信任（上游 [#10598](https://github.com/minio/minio/pull/10598)，[`56d1b227c`](https://github.com/minio/minio/commit/56d1b227c)，2020-09-30，Poorna Krishnamoorthy）**：在 `cmd/object-api-options.go` 的 `putOpts` 中读取 `?versionId=` 并赋给 `opts.VersionID`，但**从未检查 `trustedReplication`**，导致任何拥有 `s3:PutObject` 的客户端都能直接寻址覆写既有版本。
3. **2023-05 目录对象强制使用 `null` 版本（上游 [#17132](https://github.com/minio/minio/pull/17132)，[`1d0211d39`](https://github.com/minio/minio/commit/1d0211d39)，2023-05-04，Harshavardhana）**：在 `putOpts` 和 `delOpts` 中对 `isDirObject(object)` 强制设置 `opts.VersionID = nullVersionID`，但未同步更新 `checkPutObjectLockAllowed` 与存储提交阶段，留下目录对象隐式 `null` 版本锁覆写缺口。

---

## 3. 最终修复方案：要修改哪些代码、怎么改 {#solution}

最终修复方案由**核心方案 A（`SN-2026-015`）**与**入口 + 存储写锁双重防线 + 预检 Fail-Closed（`SN-2026-016`）**两部分组成，共涉及 `cmd/` 下 11 个生产文件：

| 所属问题 | 修改文件 | 核心改动内容 |
| --- | --- | --- |
| **SN-2026-015**<br>（核心方案 A，3 个文件） | `cmd/object-handlers.go` | 在 `PutObjectRetentionHandler` 解析请求体 XML 后、读取任何桶/对象状态前，立即调用 `isRetentionActionAllowed` 无条件校验 `s3:PutObjectRetention` |
| | `cmd/bucket-object-lock.go` | 新增 `isRetentionActionAllowed`（修正零值日期为 `"0"` 天、超远日期用秒差向上取整）；重写 `enforceRetentionBypassForPut`，仅在削弱未到期存量 `GOVERNANCE` 锁时同时要求 bypass 请求头与 `s3:BypassGovernanceRetention` 授权 |
| | `cmd/auth-handler.go` | 删除存在 `byPassSet \|\| retSet` 短路漏洞的 `isPutRetentionAllowed` 函数（净删 45 行） |
| **SN-2026-016**<br>（入口与写锁双重防线，8 个文件） | `cmd/object-api-options.go` | 在所有 HTTP 写入选项的唯一汇合点 `putOpts` 中，对 `vid != "" && !trustedReplication` 一律返回 `errAuthentication`（`403 AccessDenied`） |
| | `cmd/batch-handlers.go` | 在 `BatchJobReplicateV1.writeAsArchive` 中为外层 `SnowballOptions` 补齐 `ReplicationRequest: true` 标记，使服务端 `batch replicate` 归档复制正常通过外层复制信任校验 |
| | `cmd/bucket-object-lock.go` | ① 在预检 `checkPutObjectLockAllowed` 中补齐 `isDirObject(object)` 的 `nullVersionID` 解析，将未到期 `GOVERNANCE` 纳入不可覆写条件，并在 `getObjectInfoFn` 返回非“不存在”错误时立即 Fail-Closed；② 新增 `checkObjectLockedForOverwrite` 供存储写锁内复检 `null` 版本锁状态（同样 Fail-Closed） |
| | `cmd/bucket-handlers.go` | 在 `PostPolicyBucketHandler` 中对目录对象（`isDirObject(object)`）补充调用 `checkPutObjectLockAllowed` |
| | `cmd/object-multipart-handlers.go` | 在 `CompleteMultipartUploadHandler` 调用 `checkPutObjectLockAllowed` 时传入实际的 `trustedReplication` 状态 |
| | `cmd/erasure-object.go` | 在 `erasureObjects.putObject` 与 `erasureObjects.CopyObject` 持有目标对象命名空间写锁（`NewNSLock`）期间，对目标版本为 `""` 或 `nullVersionID` 的非复制写入调用 `checkObjectLockedForOverwrite` |
| | `cmd/erasure-multipart.go` | 在 `CompleteMultipartUpload` 持有目标对象写锁期间，对 `null` 版本调用 `checkObjectLockedForOverwrite`，对非空 UUID 版本执行 `getObjectInfo`（多池下为 `replicaObjectInfo`）存量版本查重 |
| | `cmd/erasure-server-pool.go`<br>`cmd/erasure-sets.go` | 在多池模式下为公开写入与分段上传完成注入跨池 `z.replicaObjectInfo`，并在 `CopyObject` 中透传版本与复制协调选项 |

---

### 3.1 SN-2026-015 修复代码详解（核心方案 A） {#solution-015}

#### （1）`cmd/object-handlers.go`：`PutObjectRetentionHandler` 入口无条件基础鉴权

在 `authenticateRequest` 验签并调用 `ParseObjectRetention(r.Body)` 解析完请求体后，**在读取任何桶信息（`GetBucketInfo`）、桶锁配置（`globalBucketObjectLockSys.Get`）或对象版本（`getOpts`）之前**，立即调用 `isRetentionActionAllowed` 校验 `s3:PutObjectRetention`：

```go
// cmd/object-handlers.go: PutObjectRetentionHandler
objRetention, err := objectlock.ParseObjectRetention(r.Body)
if err != nil {
	apiErr := errorCodes.ToAPIErr(ErrMalformedXML)
	apiErr.Description = err.Error()
	writeErrorResponse(ctx, w, apiErr, r.URL)
	return
}

reqInfo := logger.GetReqInfo(ctx)
reqInfo.SetTags("retention", objRetention.String())

// Check permissions to perform this object retention operation. The
// object-lock condition keys come from the request body, so this is
// decided before any bucket or object state is read.
if !isRetentionActionAllowed(policy.PutObjectRetentionAction, bucket, object, objRetention, r, reqInfo.Cred, reqInfo.Owner) {
	writeErrorResponse(ctx, w, errorCodes.ToAPIErr(ErrAccessDenied), r.URL)
	return
}
```

#### （2）`cmd/bucket-object-lock.go`：`isRetentionActionAllowed` 与 `enforceRetentionBypassForPut`

抽出统一的 `isRetentionActionAllowed` 辅助函数，从解析后的请求体构造 `object-lock-mode`、`object-lock-retain-until-date`、`object-lock-remaining-retention-days` 三个条件键并调用 `globalIAMSys.IsAllowed`：
- 当请求为清除保留期（空 `<Retention/>`，`RetainUntilDate` 为零值 `0001-01-01`）或非未来时间时，将 `object-lock-remaining-retention-days` 精确求值为 `"0"`（修复旧代码因 `time.Duration` 截断与 `math.Abs` 算出 `106,752` 天的漏洞，且始终保留该条件键以确保 `NumericLessThan` 的 `Deny` 策略能够命中清除请求）；
- 当日期为未来时间时，改用 Unix 秒数差与纳秒差向上取整计算天数，避免 `Time.Sub` 在约 292 年后发生 `time.Duration` 饱和。

同时，将对象写锁内的 `enforceRetentionBypassForPut` 收敛为纯粹基于存量版本状态的规则：

```go
// cmd/bucket-object-lock.go
func isRetentionActionAllowed(action policy.Action, bucketName, objectName string, objRetention *objectlock.ObjectRetention, r *http.Request, cred auth.Credentials, owner bool) bool {
	if objRetention == nil {
		return false
	}
	t, err := objectlock.UTCNowNTP()
	if err != nil {
		internalLogIf(r.Context(), err, logger.WarningKind)
		return false
	}

	conditionValues := getConditionValues(r, "", cred.AccessKey, nil)
	conditionValues["object-lock-mode"] = []string{string(objRetention.Mode)}
	conditionValues["object-lock-retain-until-date"] = []string{objRetention.RetainUntilDate.Format(time.RFC3339)}

	var days int64
	if !objRetention.RetainUntilDate.IsZero() && objRetention.RetainUntilDate.After(t) {
		sec := objRetention.RetainUntilDate.Unix() - t.Unix()
		nsec := int64(objRetention.RetainUntilDate.Nanosecond() - t.Nanosecond())
		if nsec < 0 {
			sec--
			nsec += int64(time.Second)
		}
		days = sec / (24 * 60 * 60)
		if sec%(24*60*60) > 0 || nsec > 0 {
			days++
		}
	}
	conditionValues["object-lock-remaining-retention-days"] = []string{strconv.FormatInt(days, 10)}

	return globalIAMSys.IsAllowed(policy.Args{
		AccountName:     cred.AccessKey,
		Groups:          cred.Groups,
		Action:          action,
		BucketName:      bucketName,
		ConditionValues: conditionValues,
		IsOwner:         owner,
		ObjectName:      objectName,
		Claims:          cred.GetClaims(),
	})
}

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

#### （3）`cmd/auth-handler.go`：删除 `isPutRetentionAllowed`

直接删除 `cmd/auth-handler.go` 中 45 行的 `isPutRetentionAllowed` 函数，消除 `byPassSet || retSet` 短路逻辑。

---

### 3.2 SN-2026-016 修复代码详解（入口守卫 + 存储写锁复检 + 预检 Fail-Closed） {#solution-016}

为什么 `SN-2026-016` 必须在 HTTP 入口守卫之外保留存储写锁内的复检？原因在于以下四类场景无法仅靠入口或来源标记拦截：
1. **慢速请求体导致的 `PUT dir/` 覆写竞态（`TestPlanReviewSlowDirectoryPut`）**：`PutObjectHandler` 的预检 `checkPutObjectLockAllowed` 运行在流式读取 HTTP 请求体 `r.Body` 之前，而存储写锁 `er.NewNSLock` 在请求体写完临时文件后才获取。仅持有 `s3:PutObject` 的写入者可以先发起 `PUT /bucket/dir/` 通过预检，随后暂停发送请求体字节流，等管理员对 `dir/` 设置 `COMPLIANCE` 保留期并收到 `200 OK` 响应后，再继续发完请求体。因此必须在对象写锁内复检 `null` 版本锁状态。
2. **升级遗留或复制发起的已持久化 `uploadId` 完成请求（`TestPlanReviewLegacyMPUCompliance`）**：`putOpts` 只在 `NewMultipartUpload` 创建上传任务时运行；而 `CompleteMultipartUpload` 使用 `completeMultipartOpts`，目标版本号直接读取自 `.minio.sys/multipart/.../uploadID/xl.meta` 中持久化的 `fi.VersionID`。对于升级前已创建的遗留分段上传任务（或由复制凭据初始化的任务），必须在完成阶段的对象写锁下校验目标版本。
3. **旧上传状态恢复后与已复制落盘的 `COMPLIANCE` 版本碰撞（`TestRecoveredMultipartUploadAfterReplica`）**：即便分段上传在初始化时由服务端生成了新 UUID（甚至带有服务端来源标记），在旧上传状态快照恢复且存活副本已将该完成版本及 `COMPLIANCE` 锁重新同步回本地后，暂存目录中的 `fi.VersionID` 与已落盘的受锁版本具有相同 UUID。来源标记只能证明 UUID 生成时的来源，不能证明完成上传时该版本仍不存在。因此必须在 `CompleteMultipartUpload` 的对象写锁内直接查重目标 `fi.VersionID` 是否已存在。
4. **预检与写锁复检的读取失败必须 Fail-Closed（`TestPlanReviewPreflightReadFailure`）**：只有明确确认目标版本不存在（`ObjectNotFound`、`VersionNotFound` 或删除标记 `MethodNotAllowed`）时才能按“无锁”放行；当桶锁配置读取失败或底层存储发生读仲裁错误（如 `InsufficientReadQuorum`）时，预检与写锁复检都必须拒绝写入。

完整改动分为以下四步：

#### （1）在 `putOpts` 唯一汇合点拦截非可信复制的 `versionId`（`cmd/object-api-options.go`）

所有 HTTP 写入选项构造（`PutObject`、`CopyObject`、`NewMultipartUpload`、`PostPolicy`、`PutObjectExtract`）最终都汇聚到 `putOpts`。在解析 `vid` 前增加 3 行守卫：

```go
// cmd/object-api-options.go: putOpts
vid = strings.TrimSpace(vid)
// A caller-chosen version ID writes that version in place. Only trusted
// replication may recreate a source version under its original ID.
if vid != "" && !trustedReplication {
	return opts, errAuthentication
}
```

#### （2）补齐 Batch Snowball 归档复制发送端的外层复制标记（`cmd/batch-handlers.go`）

SILO 服务端自身的 `batch replicate` 在源与目标均为 SILO/MinIO 时会通过 `writeAsArchive` 发送 Snowball 归档，并在每个 tar PAX 条目中携带 `minio.versionId`。接收端 `PutObjectExtractHandler` 要求外层 HTTP 请求头具备 `X-Minio-Source-Replication-Request: true`（`markerExact`）才会对条目授予 `entryTrusted`。因此在 `writeAsArchive` 中为外层 `PutObjectOptions` 补上复制请求标记：

```go
// cmd/batch-handlers.go: writeAsArchive
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

#### （3）在 HTTP 预检与存储对象写锁内双重拦截 `null` 版本锁覆写，且读取失败时一律 Fail-Closed（`cmd/bucket-object-lock.go`、`cmd/erasure-object.go`、`cmd/erasure-server-pool.go`、`cmd/erasure-sets.go`）

- **HTTP 预检阶段（`checkPutObjectLockAllowed`）**：使目录对象（`isDirObject(object)`）与 `putOpts`/`delOpts` 一致地将空版本解析为 `nullVersionID`；在 `!replicaTrusted` 时将未到期的 `GOVERNANCE` 与 `COMPLIANCE`、`LegalHoldOn` 一并视为不可覆写；并且当 `getObjectInfoFn` 返回非 `ObjectNotFound` / `VersionNotFound` / `MethodNotAllowed` 的错误时立即返回错误（Fail-Closed）：

```go
// cmd/bucket-object-lock.go: checkPutObjectLockAllowed
if isDirObject(object) && opts.VersionID == "" {
	opts.VersionID = nullVersionID
}

if opts.VersionID != "" && !replicaTrusted {
	objInfo, err := getObjectInfoFn(ctx, bucket, object, opts)
	if err != nil {
		if !isErrObjectNotFound(err) && !isErrVersionNotFound(err) && !errors.As(err, &MethodNotAllowed{}) {
			return mode, retainDate, legalHold, toAPIErrorCode(ctx, err)
		}
	} else {
		r := objectlock.GetObjectRetentionMeta(objInfo.UserDefined)
		t, err := objectlock.UTCNowNTP()
		if err != nil {
			internalLogIf(ctx, err, logger.WarningKind)
			return mode, retainDate, legalHold, ErrObjectLocked
		}
		if (r.Mode == objectlock.RetCompliance || r.Mode == objectlock.RetGovernance) && r.RetainUntilDate.After(t) {
			return mode, retainDate, legalHold, ErrObjectLocked
		}
		mode = r.Mode
		retainDate = r.RetainUntilDate
		legalHold = objectlock.GetObjectLegalHoldMeta(objInfo.UserDefined)
		if legalHold.Status == objectlock.LegalHoldOn {
			return mode, retainDate, legalHold, ErrObjectLocked
		}
	}
}
```

- **存储提交写锁阶段（`checkObjectLockedForOverwrite`）**：在 `er.putObject`、`er.CopyObject`、`er.CompleteMultipartUpload` 持有目标对象命名空间写锁（`NewNSLock`）期间，对所有目标版本为 `""` 或 `nullVersionID` 的非复制写入调用 `checkObjectLockedForOverwrite`（多池模式下通过 `z.replicaObjectInfo` 汇总跨池锁状态）。桶锁配置读取失败或对象读取失败时同样拒绝写入，只有确认目标 `null` 版本不存在或未被锁定才放行：

```go
// cmd/bucket-object-lock.go: checkObjectLockedForOverwrite
func checkObjectLockedForOverwrite(ctx context.Context, bucket, object string, getObjectInfoFn GetObjectInfoFn) error {
	if isMinioMetaBucketName(bucket) {
		return nil
	}
	retentionCfg, err := globalBucketObjectLockSys.Get(bucket)
	if err != nil {
		return err
	}
	if !retentionCfg.LockEnabled {
		return nil
	}
	objInfo, err := getObjectInfoFn(ctx, bucket, object, ObjectOptions{
		VersionID:  nullVersionID,
		NoLock:     true,
		NoAuditLog: true,
	})
	if err != nil {
		if isErrObjectNotFound(err) || isErrVersionNotFound(err) || errors.As(err, &MethodNotAllowed{}) {
			return nil
		}
		return err
	}
	if objectlock.GetObjectLegalHoldMeta(objInfo.UserDefined).Status == objectlock.LegalHoldOn {
		return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
	}
	r := objectlock.GetObjectRetentionMeta(objInfo.UserDefined)
	if r.Mode == objectlock.RetCompliance || r.Mode == objectlock.RetGovernance {
		t, err := objectlock.UTCNowNTP()
		if err != nil {
			internalLogIf(ctx, err, logger.WarningKind)
			return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
		}
		if r.RetainUntilDate.After(t) {
			return ObjectLocked{Bucket: bucket, Object: decodeDirObject(object), VersionID: nullVersionID}
		}
	}
	return nil
}
```

#### （4）在 `CompleteMultipartUpload` 对象写锁下按持久化 `fi.VersionID` 精确区分 `null` 版本与 UUID 版本覆写（`cmd/erasure-multipart.go`）

分段上传在初始化与完成之间可能跨越桶版本控制状态的切换，或涉及升级遗留任务、跨主体完成及旧上传状态恢复。因此在对象写锁（`NewNSLock`）内直接依据 `uploadid/xl.meta` 中持久化的 `fi.VersionID` 裁决非复制完成请求（`!opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement`）：
- 若 `fi.VersionID == "" || fi.VersionID == nullVersionID`（写入 `null` 版本，含版本控制开启前发起的正常在途上传及目录对象上传）：调用 `checkObjectLockedForOverwrite`，在未触发对象锁时正常放行完成；
- 若 `fi.VersionID` 为非空 UUID：无论当前桶处于 `Enabled` 还是 `Suspended`，通过 `getObjectInfo`（多池经 `replicaObjectInfo`）检查该 UUID 版本是否已存在于磁盘（含普通版本与删除标记）；若已存在则直接返回 `errAuthentication`（`403 AccessDenied`），读取失败则按 Fail-Closed 返回对应错误，且不清理未提交的分片文件。

```go
// cmd/erasure-multipart.go: CompleteMultipartUpload
if !opts.ReplicationRequest && !opts.ReplicaLockReconcile && !opts.DataMovement {
	getObjectInfo := er.getObjectInfo
	if opts.replicaObjectInfo != nil {
		getObjectInfo = opts.replicaObjectInfo
	}
	if fi.VersionID == "" || fi.VersionID == nullVersionID {
		if err := checkObjectLockedForOverwrite(ctx, bucket, object, getObjectInfo); err != nil {
			return oi, toObjectErr(err, bucket, object)
		}
	} else {
		_, gerr := getObjectInfo(ctx, bucket, object, ObjectOptions{
			VersionID:        fi.VersionID,
			Versioned:        opts.Versioned,
			VersionSuspended: opts.VersionSuspended,
			NoLock:           true,
		})
		switch {
		case gerr == nil, errors.As(gerr, &MethodNotAllowed{}):
			return oi, toObjectErr(errAuthentication, bucket, object)
		case isErrVersionNotFound(gerr) || isErrObjectNotFound(gerr):
		default:
			return oi, toObjectErr(gerr, bucket, object)
		}
	}
}
```

---

## 4. 关键路径与性能影响分析 {#performance-and-critical-path}

| 操作路径 | 修改后的执行路径与开销说明 |
| --- | --- |
| **`GetObject` / `HeadObject` / `ListObjects` / `DeleteObject`** | **完全不经过任何修改点**，读路径与删除路径无任何变更 |
| **普通桶（未开启对象锁）的 `PutObject` / `CopyObject`** | `putOpts` 增加一次内存空串判断 `vid != ""`；写锁内 `checkObjectLockedForOverwrite` 读取进程内 `globalBucketObjectLockSys.Get(bucket)` 缓存发现 `!retentionCfg.LockEnabled` 后立即返回，**无额外磁盘 I/O 或跨池请求** |
| **对象锁桶中的常规对象 `PutObject` / `CopyObject`（非 `/` 结尾）** | 对象锁桶强制开启版本控制，常规单次对象写入生成的 `fi.VersionID` 为非空 UUID，不满足 `fi.VersionID == "" \|\| fi.VersionID == nullVersionID`，**既不在预检也不在写锁内触发额外的 `getObjectInfo` 磁盘读取** |
| **对象锁桶中的目录对象写入（`PUT dir/`）或暂停版本控制下的 `null` 版本覆写** | 在预检与对象写锁内读取 `null` 版本元数据进行锁校验，并在读取失败时立即拒绝写入，防止慢速请求体竞态与读仲裁故障下的锁覆写 |
| **版本化桶中的分段上传完成（`CompleteMultipartUpload`）** | 在 `CompleteMultipartUpload` 最终提交写锁内执行一次 `getObjectInfo`（多池下为 `replicaObjectInfo`）核验 `fi.VersionID` 是否已存在。该检查仅在分段上传最终合并提交时发生一次（`NewMultipartUpload` 与各 `UploadPart` 均不受影响）；针对常规新建上传跳过该查询的优化需另行设计能抵御快照恢复重放的机制并独立验证，不在本次安全修复中强行并入 |
| **`PutObjectRetention` 合法延长保留期与未授权请求** | 基础权限 `s3:PutObjectRetention` 前移至读取桶/对象状态之前：未授权请求在入口即被内存态 IAM 求值拒绝（消除原有的磁盘读取与写锁争用）；合法延长保留期请求在对象写锁内判定 `!weakens` 后立即返回，无需在写锁内重复执行 IAM 求值 |

---

## 5. 为什么这个方案有效，以及有哪些兼容性注意事项 {#why-it-works}

### 5.1 三条核心安全不变量

1. **不变量一：基础权限与锁条件键在读取任何状态前无条件成立（消除 F1、F3、清锁天数绕过与存在性探测）**
   - `PutObjectRetention` 支持的三个对象锁条件键全部派生自请求体 XML 与当前时间，不依赖桶或对象的任何存量元数据。因此在 `ParseObjectRetention` 之后立即调用 `isRetentionActionAllowed(policy.PutObjectRetentionAction, ...)`，既是最早可求值点，也是完全求值点。
   - 删除 `byPassSet || retSet` 并将清除保留期（空 `<Retention/>`）的剩余天数精确求值为 `"0"` 后，任何缺少 `s3:PutObjectRetention` 授权、或命中条件 `Deny` / 不满足条件 `Allow` 的请求，无论是否携带 bypass 请求头、也无论请求何种模式，一律在入口被 `403 AccessDenied` 拦截。
2. **不变量二：Bypass 仅由“存量锁未到期且被削弱”触发，且意图与授权必须同时具备（消除 F2）**
   - `enforceRetentionBypassForPut` 在对象写锁保护下检查已存储的 `ret.Mode` 与 `ret.RetainUntilDate`。若存量无锁、已到期、或请求未削弱存量锁（`!weakens`），无需 bypass；一旦 `weakens == true`，存量 `COMPLIANCE` 无条件返回 `400 ObjectLocked`，存量 `GOVERNANCE` 必须同时满足请求头（`IsObjectLockGovernanceBypassSet`）与 IAM 授权（`isRetentionActionAllowed(BypassGovernanceRetentionAction, ...)`）。
3. **不变量三：公开数据写入在入口与提交写锁下均不能替换既有 UUID 版本或受锁 `null` 版本，且读取失败一律 Fail-Closed（消除 F4 与同源写路径缺口）**
   - 入口层：`putOpts` 拒绝一切非可信复制指定的目标 `versionId`；`checkPutObjectLockAllowed` 拦截对受锁目录 `null` 版本的写入并在读取错误时立即拒绝放行。
   - 提交写锁层：在与实际重命名提交相同的对象命名空间写锁（`NewNSLock`）下，对 `null` 版本覆写再次执行 Fail-Closed 的 `checkObjectLockedForOverwrite`（闭合慢速请求体 TOCTOU 窗口），对分段上传的非空 `fi.VersionID` 执行存量版本查重（闭合升级遗留任务、跨主体完成与旧上传状态恢复重放窗口）。

#### `PutObjectRetention` 完整判定表

`retOK` 表示带请求中的锁条件键时 `s3:PutObjectRetention` 被允许，`bypassOK` 表示同一组条件键下 `s3:BypassGovernanceRetention` 被允许：

| 目标版本存量状态 | 请求变更类型 | Bypass 请求头 | `retOK` | `bypassOK` | 修复前行为 | 修复后行为 |
| --- | --- | --- | --- | --- | --- | --- |
| 任意 | 任意 | 任意 | **否** | 任意 | 常为 **200**（F1、F3）或 404/400 | 入口 **403 AccessDenied** |
| 未到期 `GOVERNANCE` | 延长保留期 | 任意 | 是 | 任意 | 200 | **200 OK** |
| 未到期 `GOVERNANCE` | 缩短 / 清除 / 改模式 | 无 | 是 | 任意 | 400 `InvalidRequest`（`ObjectLocked`） | **400 `InvalidRequest`（`ObjectLocked`）** |
| 未到期 `GOVERNANCE` | 缩短 / 清除 / 改模式 | 有 | 是 | **否** | **200**（F2 漏洞） | **403 AccessDenied** |
| 未到期 `GOVERNANCE` | 缩短 / 清除 / 改模式 | 有 | 是 | **是** | 200 | **200 OK** |
| 未到期 `COMPLIANCE` | Shorten / 清除 / 改模式 | 任意 | 是 | 任意 | 400 `InvalidRequest`（`ObjectLocked`） | **400 `InvalidRequest`（`ObjectLocked`）** |
| 无保留期或已到期 | 任意 | 任意 | 是 | 任意 | 200 | **200 OK** |

#### 写路径不变量覆盖表

| 写入路径 | 选项汇合点与写锁防线 | 修复后的保证 |
| --- | --- | --- |
| `PutObject`（常规 PUT / 桶复制 / 站点复制 / 单对象 Batch 复制） | 验签后经 `evaluateReplicationTrust` 写入上下文，再调用 `putOptsFromReq` -> `putOpts`；`null` 版本在写锁下执行 `checkObjectLockedForOverwrite` | 公开客户端（含 `root`）带 `?versionId=` 一律在 `putOpts` 返回 `403`；可信复制正常保留源版本 ID |
| `CopyObject`（含元数据复制） | 源版本走 `srcOpts`，目标版本经 `copyDstOpts` -> `putOpts`；`null` 版本在写锁下执行 `checkObjectLockedForOverwrite` | 公开复制源版本正常生成新版本；公开指定目标 `?versionId=` 返回 `403`；可信复制正常同步目标版本 |
| `PostPolicy`（浏览器表单上传） | 经 `putOptsFromReq` -> `putOpts`；目录对象预检与写锁内双重执行锁检查 | 携带目标 `versionId` 一律返回 `403`；受锁目录对象不可被表单覆写 |
| `PutObjectExtract`（Snowball / Batch 归档复制） | 外层校验 `markerExact`，逐条目校验 `s3:ReplicateObject` 得出 `entryTrusted` 再传入 `putOpts`；`writeAsArchive` 补齐外层标记 | 未获复制信任的归档条目若带 `minio.versionId` 一律返回 `403`；服务端 `batch replicate` 归档路径正常保留版本 ID |
| `NewMultipartUpload` / `UploadPart` / `UploadPartCopy` | 初始化与加密分片走 `putOptsFromReq` -> `putOpts`；`UploadPartCopy` 强制清除复制信任 | 非可信复制初始化分段上传无法指定目标 `versionId`（返回 `403`） |
| `CompleteMultipartUpload` | 走 `completeMultipartOpts`，并在对象写锁下按 `fi.VersionID` 执行 `null` 版本锁检查或 UUID 存量版本查重 | 版本控制开启前发起的正常在途上传可正常完成；针对既有 UUID 版本（含升级遗留任务、指定版本任务与恢复重放任务）的非复制完成请求一律返回 `403` |
| 目录对象 `PUT` / `Copy`（`/{bucket}/dir/`） | 预检 `checkPutObjectLockAllowed` 与写锁内 `checkObjectLockedForOverwrite` 双重 Fail-Closed 校验 | 一旦目录 `null` 版本存在未到期的 `GOVERNANCE`、`COMPLIANCE` 或 `LegalHoldOn`（含预检后慢速传输期间并发提交的锁），非复制覆写返回 `400 InvalidRequest`（`ObjectLocked`）；读取失败时在预检与写锁均拒绝写入 |

---

### 5.2 可能产生的业务与兼容性副作用（Upgrade Notes） {#side-effects}

常规的新版本创建、普通对象读写与已获授权的保留期延长保持原有行为。以下收紧的边界行为需在升级与发布说明中提示运维人员：

1. **仅授予 `s3:BypassGovernanceRetention` 而无 `s3:PutObjectRetention` 的策略不再放行保留期写入（`SN-2026-015`）**
   - **旧行为**：因 `byPassSet || retSet` 漏洞，仅有 `s3:BypassGovernanceRetention` 的主体带上请求头也能成功调用 `PutObjectRetention`。
   - **新行为**：返回 `403 AccessDenied`。按 AWS S3 规范，`s3:BypassGovernanceRetention` 是削弱治理锁时的附加权限，写保留期始终需要 `s3:PutObjectRetention`。
2. **未授权 `PutObjectRetention` 请求在入口统一返回 `403`，不再返回 `404` 或 `400`（`SN-2026-015`）**
   - **旧行为**：桶不存在时返回 `404 NoSuchBucket`，桶未开启对象锁时返回 `400 InvalidBucketObjectLockConfiguration`。
   - **新行为**：在读取桶状态前完成鉴权，未授权主体一律收到 `403 AccessDenied`。
3. **清除保留期（空 `<Retention/>`）时 `s3:object-lock-remaining-retention-days` 求值为 `"0"`（`SN-2026-015`）**
   - **旧行为**：零值日期经 `time.Duration` 截断与 `math.Abs` 计算后得到 `106,752` 天，导致基于 `s3:object-lock-remaining-retention-days` 的最短保留天数策略在清除保留期时失效。
   - **新行为**：清除请求将该条件键求值为 `"0"`，受最短保留天数策略约束的主体无法通过直接清除保留期绕过最小天数限制。
4. **非复制请求（包括 `root`）不能再通过 `?versionId=` 原地覆写对象版本（`SN-2026-016`）**
   - **旧行为**：任何拥有 `s3:PutObject` 的调用者（含 `root`）带 `?versionId=<id>` 发送 `PUT`、`CopyObject` 或 `NewMultipartUpload` 会原地改写该版本。
   - **新行为**：不带可信复制标记的请求携带目标 `versionId` 时一律在 `putOpts` 返回 `403 AccessDenied`。标准 S3 协议本就不存在公开的按版本号覆写接口。
5. **向 SILO 目标执行 `batch replicate` 时，目标端凭据必须持有 `s3:ReplicateObject`（`SN-2026-016`）**
   - **旧行为**：若跨集群 `batch replicate` 配置的目标端凭据只有 `s3:PutObject` 而无 `s3:ReplicateObject`，目标端虽然剥离了内部复制头，但 `putOpts` 仍接受了 URL 中的 `?versionId=`，从而静默保留了源版本号。
   - **新行为**：保留源版本号必须通过目标端的复制信任校验（即目标凭据需具备 `s3:ReplicateObject`），否则目标端返回 `403 AccessDenied`，与桶级复制（Bucket Replication）的权限要求一致。
6. **对象锁桶中受锁目录对象（`dir/`）在锁到期前不可被重复 `PUT` 覆写（`SN-2026-016`）**
   - **旧行为**：目录对象强制共用 `null` 版本且跳过了存量锁检查，重复 `PUT dir/` 会静默覆盖并重置其保留期。
   - **新行为**：当对象锁桶设置了默认保留期、或有人对 `dir/`（`versionId=null`）设置了保留期/法务保留时，在该锁到期前再次写入 `dir/` 会返回 `400 InvalidRequest`（`ObjectLocked`）。
7. **独立跟踪的相邻议题（不并入本次补丁）**
   - `PostRestoreObjectHandler`（归档对象恢复）先读快照再调用 `CopyObject` 回写完整元数据映射的并发竞态属于归档恢复路径的独立问题，另行立项处理。

---

## 6. 候选方案对抗评测与最终取舍 {#tradeoffs}

在设计评审期间，我们针对写路径防护评估并实际构造测试检验了以下四套候选方案：

| 评估维度 | 候选一：仅保留 HTTP 入口与预检守卫<br>（已否决） | 候选二：凭分段上传“服务端生成版本标记”跳过写锁 UUID 查重<br>（已否决） | 候选三：`fe3935476` 完整写锁复检<br>（无预检 Fail-Closed） | **最终落地方案**：`fe3935476` 完整写锁复检 + 预检 Fail-Closed |
| --- | --- | --- | --- | --- |
| **`SN-2026-015` 保留期鉴权（F1 / F2 / F3 / 清锁 0 天计算）** | 通过 | 通过 | 通过 | **通过** |
| **慢速请求体 `PUT dir/` 竞态覆写 `COMPLIANCE`（`TestPlanReviewSlowDirectoryPut`）** | **失败（P1）**：暂停请求体即可覆写已提交的 `COMPLIANCE` 锁 | 通过 | 通过 | **通过** |
| **升级遗留或复制发起的 `uploadId` 覆写（`TestPlanReviewLegacyMPUCompliance`）** | **失败（P1）**：`CompleteMultipartUpload` 不经 `putOpts`，直接覆写 `COMPLIANCE` 版本 | 通过 | 通过 | **通过** |
| **旧上传状态恢复后与已复制落盘的同 UUID `COMPLIANCE` 版本碰撞（`TestRecoveredMultipartUploadAfterReplica`）** | **失败（P1）** | **失败（P1）**：生成标记只能证明初始化时的来源，不能证明完成时该版本仍不存在 | 通过（写锁内无条件按 `fi.VersionID` 查重） | **通过（写锁内无条件按 `fi.VersionID` 查重）** |
| **预检阶段读仲裁失败时的行为（`TestPlanReviewPreflightReadFailure`）** | **失败（P1）**：预检忽略读错误并覆写对象 | 通过 | 写锁内拦截，但预检忽略读错误并继续接收请求体 | **通过（预检即刻 Fail-Closed 拒绝，不进入存储写入）** |
| **分段上传完成阶段查询开销** | 无额外查询 | 新上传跳过查询（但引入恢复重放漏洞） | 每次完成在写锁内执行一次 `getObjectInfo` | **保持写锁内 `getObjectInfo` 严格查重；性能优化留待后续单独设计验证** |

### 最终结论

采用**`fe3935476` 完整写锁防线 + 预检 Fail-Closed 加固**作为最终落地实现，并将慢速目录写入（`TestPlanReviewSlowDirectoryPut`）、预检读故障（`TestPlanReviewPreflightReadFailure`）、遗留分段上传（`TestPlanReviewLegacyMPUCompliance`）及恢复后分段上传碰撞（`TestRecoveredMultipartUploadAfterReplica`）四组对抗复现测试全部纳入 `cmd/object-retention-overwrite_test.go` 回归测试集。
