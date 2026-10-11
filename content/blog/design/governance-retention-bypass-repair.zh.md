---
title: "治理保留绕过：溯源记录与修复"
linkTitle: "治理保留绕过修复"
date: 2026-10-10
lastmod: 2026-10-10
author: "冯若航"
summary: >
  SN-2026-015 的研究与修复记录：授权缺陷在上游的引入点与 2025 年的回归经过、
  后续外部报告各论断的逐条核验、可行与不可行的修复形状、分支上已落地的测试，
  以及同分支的版本寻址写入修复（SN-2026-016）。
tags: [设计, 安全, Object Lock, IAM]
weight: 7
draft: true
url: "/zh/blog/design/governance-retention-bypass-repair/"
---

> **草稿，2026-10-10 —— 未发布。** 本文是
> [`SN-2026-015`](/zh/blog/security/20260926-governance-retention-bypass/)
> 的内部研究与修复记录。公开的影响范围（F1–F3）、修复设计与缓解指引以该公告为准；
> 本文补充溯源记录、对后续外部报告的核验、修复形状对比与已实现的测试。修复位于
> Server 分支 `fix/sn-2026-015-016`，截至本文日期尚未提交。在修复版本发布、且
> 关联发现（SN-2026-016，见下文）完成自己的披露之前，本文保持草稿状态。

## 本文补充什么 {#scope}

[公告](/zh/blog/security/20260926-governance-retention-bypass/)已经固定了影响
范围与修复设计。以下四部分内容不在、也不应放在公告里：

1. 完整溯源：2020 年之前原本正确的设计、破坏它的提交、其后十年的机械搬运、
   2025 年的部分修复、以及把它回归掉的一次无关重构——每一步都有证据
   （[见下](#origin)）。
2. 对公告发布之后收到的一份外部报告的逐条核验（[见下](#report)）：每条论断
   对照代码、必要处对照发布二进制。
3. 以实现视角展开的修复形状对比——采用了什么、报告人建议了什么、哪两种形状
   不可行（[见下](#shapes)）。
4. 分支上已实现的修复与测试矩阵，包括相对公告测试计划**尚未**覆盖的部分，
   以及同分支记录为 [SN-2026-016](#companion) 的版本寻址写入修复。

分析基线：Server `main` 的
[`4f62e8f19`](https://github.com/pgsty/silo/commit/4f62e8f19)（2026-10-10）、
完整 git 历史、以及同日直接拉取的上游 `minio/minio` master。报告人所钉版本为
[`9b11dc94`](https://github.com/pgsty/silo/commit/9b11dc94)
（`RELEASE.2026-09-03T13-18-01Z`）；两版机制完全一致，
`RELEASE.2026-09-16T00-00-00Z` 同样受影响。

## 十月报告的核验 {#report}

公告发布后又收到一份外部报告（署名 "Nik"；2026-10-10 完成核验），独立描述了
这一绕过，并补充了关于上游影响的论断。其三个症状与公告的 F1/F2 对应。逐条核验：

| 报告论断 | 结论 |
| --- | --- |
| 持有 `s3:PutObjectRetention`、无 bypass 权限的主体，可借原始请求头把 GOVERNANCE 改为 COMPLIANCE（无需任何 Deny 参与） | **成立**（F1 形态） |
| 对 `s3:PutObjectRetention` 的条件 Deny（锁条件键）被同一请求头绕过 | **成立**（F3 形态） |
| 无 bypass 权限的主体可缩短 GOVERNANCE 保留期 | **成立**（F2，最初报告的情形） |
| "无条件 Deny 在入口能拦住请求" | **不成立——实际影响更大。** `authenticateRequest` 只验签名；带请求头时，无条件 Deny、乃至完全没有授权的主体同样被绕过（公告 F1）。已在 2026-09-16 发布二进制上复现。 |
| SILO 中删除版本还需 `s3:DeleteObjectVersion`，F2 影响受限；上游只做 deny-only 检查，勒索链在上游完整成立 | **成立**：[`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4)（2026-09-02）将显式版本删除改为完整权限要求；上游 master 以 `DenyOnly: true` 求值（2026-10-10 时 `cmd/auth-handler.go:475`） |
| 已有 COMPLIANCE 保留即使带请求头也无法缩短 | **成立**——全链路唯一守住的边界 |
| 同一代码存在于 `minio/minio` master（`cmd/auth-handler.go:677-717`） | **逐字节成立**（handler 入口、`enforceRetentionBypassForPut`、`isPutRetentionAllowed`），2026-10-10 拉取核对 |
| 缺陷在服务端 `cmd/`，不在 `silo-pkg`；策略引擎对 Deny 的求值本身正确 | **成立** |
| 修复建议：bypass 授权只做一次、授权结果贯穿使用、基础权限必需 | **采纳**——被实现方案完全吸收（[见下](#shapes)） |

报告的行号引用（`auth-handler.go:743-783`、`object-handlers.go:3164/3205`）与
`9b11dc94` 对应；在分析基线上因无关提交平移为 `:736-777` 与 `:3439/:3480`，
机制相同。

## 溯源记录 {#origin}

### 缺陷之前的正确设计 {#origin-before}

直到 2020 年 4 月，授权形状是正确的：handler 在入口完成基础权限判定，bypass
权限单独求值后**以已授权的结果**向下传递：

```go
// 43a3778b4^ : cmd/object-handlers.go（PutObjectRetentionHandler 入口）
	// Check permissions to perform this governance operation
	if s3Err := checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object); s3Err != ErrNone {
		...
	}

// 43a3778b4^ : cmd/object-handlers.go:2549 —— bypass 预先授权，再传入
	govBypassPerms := checkRequestAuthType(ctx, r, policy.BypassGovernanceRetentionAction, bucket, object)

// 43a3778b4^ : cmd/object-lock.go:87 —— 接收的是授权结果，不是请求头
	func enforceRetentionBypassForPut(..., govBypassPerm APIErrorCode, ...) (oi ObjectInfo, s3Err APIErrorCode)
```

原始请求头只决定"是否需要走 bypass 分支"，从不进入授权判定。这一脉络起自
[`ca96560d5`](https://github.com/minio/minio/commit/ca96560d5)（对象级保留，
2019-11-20）与
[`f931fc7bf`](https://github.com/minio/minio/commit/f931fc7bf)
（`enforceRetentionBypassForPut`，2019-11-25），入口调用由
[#9030](https://github.com/minio/minio/pull/9030)（2020-03-04）细化。

### 引入：#9259，2020-04-06 {#origin-intro}

上游 [`43a3778b4`](https://github.com/minio/minio/commit/43a3778b45)
（[#9259](https://github.com/minio/minio/pull/9259)，Harshavardhana，
"fix: support object-remaining-retention-days policy condition"）在一次重写中
引入了授权缺陷。该提交自己的说明写着它"fixed a couple of bugs related to how
policy should have been honored when ByPassGovernance is provided"——它本身就是
一次修复。它做了三件事：

1. **删除入口授权**，以仅验签名的 `validateSignature` 取代
   `checkRequestAuthType`。
2. **废弃预授权参数**（`govBypassPerm`），改为把**原始请求头** `byPassSet`
   传入新建的辅助函数。
3. **创建 `isPutRetentionAllowed`**，带着公告已记录的两处要害错误：bypass 权限
   只在*请求的*模式为 GOVERNANCE 时才求值（清除与 COMPLIANCE 请求永远不校验），
   而结尾的 `byPassSet || retSet` 让 bypass 结果沦为参考值。

当时不存在 `PutObjectRetention` 的权限矩阵回归测试，任何一处都拦不住——
此前也从未存在过。

### 机械搬运的十年 {#origin-mechanical}

- [#9513](https://github.com/minio/minio/pull/9513)（2020-05）与
  [#9377](https://github.com/minio/minio/pull/9377)（2020-06）把 enforcement
  代码迁入 `cmd/bucket-object-lock.go`，形状未变。
- [#12947](https://github.com/minio/minio/pull/12947)
  （[`8f2a3efa8`](https://github.com/minio/minio/commit/8f2a3efa8)，2021-08）
  清理辅助函数的子凭据处理并删除匿名分支；`||` 原样保留。在分析基线上做
  blame，该函数 43 行中仍有 31 行归属于 `43a3778b4`。

### 部分修复与回归（2025） {#origin-regression}

- [#20929](https://github.com/minio/minio/pull/20929)
  （[`437dd4e32`](https://github.com/minio/minio/commit/437dd4e32)，Ramon de
  Klein，2025-02-12）把入口 `checkRequestAuthType` 加了回来——"Fix missing
  authorization check for `PutObjectRetentionHandler`"。F1 在入口被关闭了约
  五十天；F2、F3 仍在辅助函数内部。
- [#21103](https://github.com/minio/minio/pull/21103)
  （[`8c7097528`](https://github.com/minio/minio/commit/8c7097528)，2025-04-03）
  是修复未签名 payload trailer 签名验证的安全提交。它在各 handler 间重排签名
  验证时，**机械地**把入口检查替换成了仅验签名的 `authenticateRequest`
  （该函数诞生于 [#15777](https://github.com/minio/minio/pull/15777)，
  2022-10）——而且保留了旧注释：

  ```diff
  -	if s3Err := checkRequestAuthType(ctx, r, policy.PutObjectRetentionAction, bucket, object); s3Err != ErrNone {
  -		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Err), r.URL)
  -		return
  -	}
  -
  -	cred, owner, s3Err := validateSignature(getRequestAuthType(r), r)
  -	if s3Err != ErrNone {
  -		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Err), r.URL)
  +	if s3Error := authenticateRequest(ctx, r, policy.PutObjectRetentionAction); s3Error != ErrNone {
  +		writeErrorResponse(ctx, w, errorCodes.ToAPIErr(s3Error), r.URL)
   		return
   	}
  ```

  留下的 "Check permissions to perform this object retention operation" 注释
  掩盖了语义退化，测试没有察觉，F1 回来了。截至 2026-10-10，上游 master 仍是
  这个状态。

### SILO 的继承 {#origin-fork}

fork 点 [`27742d469`](https://github.com/pgsty/silo/commit/27742d469)
（2025-12-03）晚于回归，因此所有 SILO 发布都完整继承了该缺陷：
`RELEASE.2026-04-17`、`2026-06-18`、`2026-08-04`、`2026-08-06`、
`2026-09-03` 与 `2026-09-16`。SILO 侧唯一触及此区域的提交
[`75a6734e4`](https://github.com/pgsty/silo/commit/75a6734e4)（2026-09-02）
是收紧版本删除授权；SILO 没有任何改动修改过漏洞链本身。

## 设计为何失效 {#cause}

自公告根因浓缩而来，三层各一处缺陷：

1. **意图与授权混同。** 同一个变量（`byPassSet`）先装客户端请求头，有时再装
   授权结果，最终同时决定弱化守卫（`if !byPassSet`）与辅助函数的裁决。
2. **守卫条件用错对象。** bypass 针对的是*存量* GOVERNANCE 锁；代码却按
   *请求的*模式做条件，导致清除与 COMPLIANCE 请求根本不校验 bypass 权限。
3. **入口缺少与状态无关的授权。** #9259 删除入口检查后，这个 API 唯一的策略
   求值点落在会被请求头短路的函数内部——而来自请求体的锁条件键又只能在
   handler 里求值，别无他处。

贯穿六年的系统性原因：`PutObjectRetention` 从未有过权限矩阵测试，因此
引入（2020）、部分修复（2025）与回归（2025）都在没有 CI 阻力的情况下发布。

## 修复形状 {#shapes}

- **A —— 已采纳（公告设计，分支已实现）。** 在入口以请求派生的锁条件键求值
  `s3:PutObjectRetention`，先于任何桶或对象读取；`enforceRetentionBypassForPut`
  收缩为存量状态弱化规则（弱化未过期 GOVERNANCE 需请求头 + 已授权的
  `s3:BypassGovernanceRetention`；COMPLIANCE 只能延长）；删除
  `isPutRetentionAllowed`。与公告设计逐字对应。
- **B —— 十月报告的建议。** 请求头存在时在 `enforceRetentionBypassForPut`
  内对 bypass 授权一次，用该结果同时驱动弱化规则与下游判定，并使基础权限必需。
  对三个发现与 A 等价；A 额外让未授权主体在任何状态读取前被拒。已被吸收。
- **C —— 最小补丁。** 保留旧辅助函数；修正其守卫（按存量模式做条件）、
  `byPassSet` 用后即弃、把 `||` 改为"基础权限必需，弱化时另需已授权 bypass"。
  因与"把检查留在 `EvalMetadataFn`"相同的先读状态后拒绝的信息泄露问题而未
  采用（见公告备选方案），但这是适合提供给上游的 backport 形状。
- **D —— 中间件授权。** 让 `PutObjectRetention` 走认证中间件的默认授权路径。
  不可行：锁条件键来自请求体，中间件在不破坏请求流的前提下无法解析；缺键求值
  会让条件 Deny 永不匹配——等于把报告中的症状换个位置重现。

## 分支上已落地的内容 {#implemented}

分支 `fix/sn-2026-015-016`，截至本文日期未提交：

- `cmd/object-handlers.go`：`ParseObjectRetention` 之后、`GetBucketInfo` 与锁
  配置读取之前，经新的 `isRetentionActionAllowed(PutObjectRetentionAction,
  ...)` 完成基础权限判定；误导性的入口注释已删除。
- `cmd/bucket-object-lock.go`：新增 `isRetentionActionAllowed`，从请求构造三个
  锁条件键并对任意 action 求值一次；`enforceRetentionBypassForPut` 重写为
  存量状态规则并以授权结果检查 bypass；原始请求头只在"是否声明了意图"处读取。
- `cmd/auth-handler.go`：删除 `isPutRetentionAllowed`。

`cmd/object-retention-authz_test.go` 以真实 IAM 子系统运行 15 个判定表用例，
外加缺失桶 403 检查，覆盖五类主体（无授权、仅基础权限、基础+bypass、仅
bypass、owner），在 ErasureSD 与 Erasure 双后端执行：**50 个子测试全部通过**
（2026-10-10）。被钉死的关键语义：延长 GOVERNANCE 无需 bypass；仅 bypass 而无
基础权限被拒；COMPLIANCE 即使有 bypass 也拒绝缩短；未授权主体在得知桶是否
存在之前即得到 403。

相对公告测试计划尚未覆盖、发布前需补齐的部分：以显式测试用户覆盖锁条件键上的
条件 Deny（F3 目前经由同一 `IsAllowed` 路径在构造上被覆盖，但没有以命名用例
固定）、STS 与服务账号凭据变体、以及原始报告的"缩短后删除"端到端链路。

## 关联修复：版本寻址写入 {#companion}

同一分支还携带第二项修复，记录为 **SN-2026-016**：`putOpts` 此前接受
`PutObject`、`CopyObject` 与分段上传初始化中调用方自选的 `versionId`，任何
写入者都能原地替换既有版本——包括上了锁的版本——从写入侧击穿对象锁。修复
（`cmd/object-api-options.go`）拒绝调用方提供的目标版本 ID，除非请求来自受信
复制路径；既有的条件 PUT 池测试改为期望版本寻址公开写入一律 403，
`TestAPIVersionAddressedWriteRequiresReplicationTrust` 覆盖 writer 与 owner 的
PUT/CopyObject/分段/null 版本，以及受信复制保留原版本 ID 的豁免。该发现尚无
公开公告，这也是本文保持草稿的原因之一。

## 交付清单 {#delivery}

1. 补齐上述缺失测试、完成对抗评审，然后提交分支（`git commit -s`），CI 通过后
   合入。
2. 发布版本，更新[公告](/zh/blog/security/20260926-governance-retention-bypass/)
   状态与台账；`security_fixes` 计数只在发布之后递增。
3. 待 SN-2026-016 完成自己的披露后，去掉本文的 `draft: true` 发布；十月报告的
   报告人与公告既有致谢一并列入。
4. 在 GHSA-67mv-7hc9-wj88 回复、申请 CVE，并通知上游 MinIO：F1 自 #21103 起
   在上游再度成立，master 至今未修（2026-10-10）。
