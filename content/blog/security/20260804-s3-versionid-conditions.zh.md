---
title: "缺失不是空：一个空 versionid，和它诱发的 fail-open"
linkTitle: "s3:versionid 条件"
date: 2026-08-04
author: "冯若航"
description: "一条只允许删除未指定版本对象的策略，把这类删除全都拒绝了。而那个显而易见的一行修复，会把这个 fail-closed 的麻烦，变成 Multi-Delete 上的 fail-open 绕过。条件值必须变成服务端真正据以操作的那个版本。"
tags: [安全, Version ID]
weight: 100
draft: false
url: "/zh/blog/security/s3-versionid-conditions/"
---

**状态：** 已在本地 `pgsty/minio` 分支修复，提交 `744a9dcd7`，**尚未发布**
**定级：** 策略执行正确性——一个 fail-**closed** 的报告、一个被避免的 fail-**open** 陷阱、以及顺手关掉的一处窄绕过。**不是重点 CVE**——见[我们如何定级](#not-a-cve)
**影响范围：** 任何在 `s3:versionid` 上使用 `Null` 或 `StringEquals` 的桶/IAM 策略；报告中的失效发生在 `DeleteObject`/`DeleteObjects`
**跟踪：** 上游 `minio/minio` issue #21735（报告者 iTrooz，2026-01-10）；上游仓库自 2026-04-25 起归档只读

> 本文记录了一个尚未发布的修复，以及相邻路径上两个尚未修复的同类残留（[治理绕过与 Snowball](#boundary)）。请在修复发布、残留完成分诊之后再上线。

## 结论先行 {#summary}

- 策略引擎判定 `Null` 看的是**切片长度**，不是内容。MinIO **无条件**往条件 map 里写了 `"versionid": {""}`，于是一个未指定版本的请求仍然呈现出一个长度为 1 的切片。`Null:{s3:versionid:true}`——"仅当键不存在时命中"——因此**永远不可能**命中，而 `Null:false` **永远**命中。报告者那条"只允许删除当前对象"的策略，把每一次当前对象删除都拒了（HTTP 200 外壳，逐对象 `AccessDenied`）。
- **那一行修复是个陷阱。** "只在非空时写入这个键"修好了报告，同时打开了一个更糟的口子。`DeleteObjects` 把每个对象的版本放在 **XML body** 里；条件构造器只读**查询串**。去掉那个空键，body 里的版本就直接从 map 里消失了——被读成不存在，也就是 null——于是一条本意保护旧版本的策略会**授权删除某个指定版本**。fail-closed 的缺陷，遇上 fail-open 的绕过。
- 真正的修复有两部分：只在指定了版本时写入这个键，**并且**对 `DeleteObject` 把它绑定到**服务端解析出的有效版本**（`ReqInfo.VersionID`）——即 DeleteObjects 循环里已经逐对象解析好的 body 值——而不是查询串里碰巧带的任何东西。
- 顺路关掉的第三个相邻口子：构造器读版本时**没有 trim**，而对象层会 trim，于是一个带尾空格的 `?versionId=V%20` 能在读/打标签/复制这些路径上绕过 `Deny StringEquals s3:versionid "V"`。
- **继承自上游，且无法在上游修。** `minio/minio` 已归档只读，修复只能落在 fork 里；这正是我们在[条件来源加固](#source)里加固过的那个 `getConditionValues`。

## 缺失不是空 {#the-defect}

MinIO 策略里的一个条件键，会解析成一个 `map[string][]string` 里的小写名；引擎回答 `Null` 的方式，是去问那个切片有多长（`silo-pkg .../policy/condition/nullfunc.go`）：

```go
func (f nullFunc) evaluate(values map[string][]string) bool {
	rvalues := getValuesByKey(values, f.k)
	if f.value { // Null:true —— "这个键必须不存在"
		return len(rvalues) == 0
	}
	return len(rvalues) != 0 // Null:false —— "这个键必须存在"
}
```

字符串的内容从不被读取。切片 `{""}` 的长度是 1。对这个函数来说，一个**存在但为空**的值，与一个真实版本 ID 无从区分，而两者都是**不存在**的反面。

再看喂给它的那个值，继承下来的样子（`cmd/bucket-policy.go`，`getConditionValues`）：

```go
args := map[string][]string{
	// ...
	"versionid": {vid}, // 任何未指定版本的请求，vid 都是 ""
	// ...
}
```

`vid` 是请求的 `?versionId`，在绝大多数调用里都是空的。于是每个请求——不论有没有版本——到达引擎时都带着 `versionid: [""]`，永远长度为 1，永远"存在"。

于是 `Null` 的两个方向都反了：

| 请求 | map 状态 | `Null:true`（要求不存在） | `Null:false`（要求存在） |
| :-- | :-- | :-- | :-- |
| 未指定版本 | `{""}`（长度 1） | **false**——永不命中 | **true**——永远命中 |
| `?versionId=abc` | `{"abc"}`（长度 1） | false | true |
| *（正确行为）* 未指定版本 | *不存在*（长度 0） | **true** | **false** |

报告者写的是那条经典的"允许客户端删除当前对象、但不能回滚版本"策略——`Allow s3:DeleteObject` 配 `Condition {"Null": {"s3:versionid": "true"}}`——然后看着每一次未指定版本的删除都返回 `AccessDenied`。那条 `Allow` 从未生效，因为它的条件测的是"没有指定版本"，而 map 坚称永远指定了版本。`StringEquals` 同样看不出区别（`{""}` 和不存在都无法与一个非空策略值相交）；只有 `Null` 和 `ForAllValues:*` 对它敏感，这就是它为什么在 `Null` 上浮现。

## 隔壁的 fail-open {#the-trap}

显而易见的修复是只在非空时写入这个键，对单个 `DeleteObject` 这完全正确：没有版本 → 不存在 → `Null:true` 命中。但只发这一条，Multi-Delete 就会把它变成一个授权绕过。

`DeleteObjects`（`POST /{bucket}?delete`）不把版本放在查询串里。每个对象各自把它可选的版本放在**请求体**里：

```xml
<Delete>
  <Object><Key>photo.jpg</Key><VersionId>a1b2…</VersionId></Object>
  <Object><Key>notes.txt</Key></Object>
</Delete>
```

条件构造器读的是 `r.Form`——**查询串**——而没有任何地方把 XML body 并进去。于是在那个天真的修复下，一个在 body 里指定了版本 `a1b2…` 的条目，产出的是**空的**查询版本，键被省略，引擎看到的是**不存在**——null。一条本意只允许删除 null 版本的策略现在命中了，运维本想保护的那个特定旧版本被删掉。报告里那个 fail-closed 的小麻烦，变成了 fail-open——而且恰好发生在最需要逐对象限定的那个操作上。

这正是报告者那个简单例子掩盖的关键：条件值必须是**服务端将要为这个对象实际操作的那个版本**，而对 Multi-Delete 来说，那个值待在一条构造器从没看过的通道上。

## 修复：有效版本，而非顺手的版本 {#the-fix}

两个机制，因为单独任何一个都是错的。

**其一——诚实地表达"不存在"**（`cmd/bucket-policy.go`）。只在请求指定了版本时写入这个键，让"没有版本"成为一次长度为 0 的读取：

```go
if vid != "" {
	args["versionid"] = []string{vid}
}
```

**其二——把 DeleteObject 绑定到有效版本**（`cmd/auth-handler.go`，`authorizeRequestWithTags`）。DeleteObjects 循环已经把每个条目的 body 版本解析进了 `ReqInfo.VersionID`（经 `checkRequestAuthTypeWithVID`，`cmd/bucket-handlers.go:502`，一个顺序循环——不存在共享状态竞争）。授权把条件值重新绑定到那个服务端解析出的字符串，并在它为空时删除该键：

```go
conditionValuesForAuth := func(lc string, cred auth.Credentials) map[string][]string {
	values := getConditionValuesWithTags(r, lc, cred, existingTags, requestTags)
	if action == policy.DeleteObjectAction {
		// DeleteObjects 把有效版本放在每个 XML object 里，
		// 而不是请求查询串里。把授权限定到该条目。
		if versionID == "" {
			delete(values, "versionid")
		} else {
			values["versionid"] = []string{versionID}
		}
	}
	return values
}
```

一个端到端测试在 DeleteObjects 的 URL 上挂了一个 **`&versionId=query-level-decoy`**，并断言它绝不进入任何条目的判定——逐对象的 body 值胜出，诱饵被剥掉。

**为什么只对 `DeleteObjectAction`，而不是无差别地用 `ReqInfo` 重绑。** 那个诱人的简化——"永远用 `ReqInfo.VersionID`"——会弄坏复制。对 `CopyObject`，源读取是以 `GetObject` 针对源的版本来授权的，而那个版本走在 `x-amz-copy-source` 头里，`getConditionValues` 已经从那里提取；复制时的 `ReqInfo.VersionID` 装的是*目标*查询串（通常为空）。无差别重绑会用错误的版本覆盖掉正确的源版本。每一个非删除的版本相关操作（Get、Head、打标签、保留、复制源读取）都把版本放在查询串或复制源头里，两者构造器都读，而对单个对象来说两者*就是*有效版本。只有 Multi-Delete 会分叉。所以这个覆盖恰好和分叉一样宽，不多一分。

## 服务端据以操作的，是 trim 过的那个版本 {#trim}

删除路径正确之后，还剩一个口子。构造器读版本时是原样读的：

```go
vid := r.Form.Get(xhttp.VersionID) // 未 trim
```

而每一条真正*使用*版本的路径都会先 trim——`newContext`（`cmd/utils.go:806`）和 `getOpts`（`cmd/object-api-options.go:101`）都 `strings.TrimSpace`。于是在非删除的版本相关操作上，一个带尾空格的 `?versionId=V%20` 把 `"V "` 呈给策略引擎，而对象层读取/打标签/保留的是版本 `"V"`。一条以 `StringEquals s3:versionid "V"` 为键的 `Deny`——"保护这个确切版本"——看到的是 `"V "`，匹配不上，不生效；对 `"V"` 的操作照常进行。窄绕过（攻击者必须知道版本、且知道一个空格在下游不改变任何东西），但确实存在。

修复对两处读取都 trim，让条件值与有效版本对齐：

```go
vid := strings.TrimSpace(r.Form.Get(xhttp.VersionID))
// …… 复制源回退同理
```

`DeleteObjectAction` 本就免疫，因为它用的是已经 trim 过的 `ReqInfo.VersionID`。trim 不引入任何新的放行：它只能让条件值等于实际操作的那个版本，从而在同一个方向上收紧 `Deny`、修正 `Allow`。我们通过只去掉 trim、看着 padded 用例转红，证明了它是承重的。

## 它影响了什么 {#impact}

报告里的失效在删除上，但底层这个键被许多动作读取。修复之后，每一条版本相关的调用链都以服务端为该操作解析出的版本来评估 `s3:versionid`：

| 调用链 | `s3:versionid` 来源 | 有效 |
| :-- | :-- | :-- |
| 单个 `DeleteObject` | `ReqInfo.VersionID` = trim 后的查询串，经覆盖 | ✓ |
| `DeleteObjects`，逐条目 | `ReqInfo.VersionID` = XML body 版本，经覆盖 | ✓——fail-open 已关 |
| `GetObject` / `HeadObject` / Select | 查询串，现已 trim | ✓ |
| 对象打标签 / 保留 / legal-hold | 查询串，现已 trim | ✓ |
| `CopyObject` / `CopyObjectPart` 源读取 | `x-amz-copy-source` 版本，现已 trim | ✓ |
| 匿名 404-vs-403 探测 | 查询串（只读） | ✓ |
| Admin / KMS / metrics / STS | 无版本概念 | ✓ |

有一条伪造路径此前已被条件来源那次工作关掉，值得重述：`versionid` 是一个保留的内部键（`versionid` 与规范化的 `Versionid` 两种拼写都保留），所以客户端无法通过头/查询串合并循环注入第二份。线上参数拼作 `versionId`（大写 I），会落进一个引擎从不读取的惰性 `args["versionId"]`。

两个方向的影响，因严重程度不同而分开陈述：

- **功能性（报告本身）：** 未指定版本的删除被错误地*拒绝*。fail-closed——一个可用性与易用性缺陷，不是放行。
- **安全性（陷阱与 trim）：** 那个天真的修复会在 Multi-Delete 上*放行*对受保护版本的删除（fail-open）；而未 trim 的值在读/标签/复制上放过了一处窄的 `Deny` 绕过。修复在第一个能存在之前就关掉了它，在第二个已存在的地方关掉了它。

## 我们如何定级 {#not-a-cve}

我们不为此签发 CVE，诚实的理由值得写出来。

报告者提交的行为是 fail-**closed**：MinIO 拒绝了策略本意允许的操作。一个过于严格的系统不泄露任何东西，也不放行任何东西；它是正确性与易用性缺陷，把一次误拒膨胀成漏洞，会让[这个编年史](/zh/blog/security/)里每一条真实条目贬值——它左右两边是认证绕过和路径穿越。

真正带安全分量的不是报告，而是它的邻近区域。Multi-Delete 上的 fail-open 是真实的，但那是我们**本会引入**的隐患，不是已发布的——两段式设计的价值，正在于那个危险版本从未存在于任何构建中。trim 绕过*确实*存在过，但很窄：它要求一条以确切 `s3:versionid` 为键的 `Deny`、一个知道版本的攻击者，且只影响非删除路径。我们关掉它，是因为它触手可及，而不是因为它是头条。

所以：策略执行正确性，归档在这里，因为我们把静默的执行失效记在这里；安全意义如实记录，而非包装。

## 我们没有越过的边界 {#boundary}

两个同类残留仍在，记录下来而非静默留置：

- **Multi-Delete 里的治理绕过。** 当某个条目带对象锁时，`enforceRetentionBypassForDelete` 会以 `BypassGovernanceRetentionAction` 重新授权（`cmd/bucket-object-lock.go:153`）。那个动作不是 `DeleteObjectAction`，所以有效版本覆盖不生效，它的 `s3:versionid` 仍是查询值——在正常 Multi-Delete 里为空——而不是被绕过锁的那个逐条目版本。
- **Snowball tar 解包。** `PutObjectExtract` 在逐文件授权**之后**才从 tar PAX 记录 `minio.versionId` 取每个成员的版本，于是一个从未出现在任何条件值里的指定版本可能被写入。

两者都窄、都是既有行为，且都会把改动从"修好报告里的那个键"扩大成"把每个动作的版本都重新接进 `ReqInfo`"。我们限定在报告的这个面上，把欠条写在这里，理由和[上一篇](/zh/blog/security/duplicate-part-numbers/)记录它对象层省略时一样：**一个没有记录的刻意省略，半年后与疏忽无法区分。**

一个相关的、被否决的决定：`username`、`userid`、`signatureversion`、`authType` 这几个同类键仍然被**无条件写空**，带着 `versionid` 刚摆脱的那个存在但为空的缺陷——`Null:{aws:username:true}` 永远为 false，包括对它本该命中的匿名调用者。修它们每个都是一行，却是四十个调用方的影响面，而且有些（`principaltype` 从不为空）根本不带这个 bug。我们没有把一次广泛的存在性清理塞进一个 versionid 修复里；它作为下一根要拉的线头，记在这里。

## 证伪 {#verification}

三个实验，遵循那条纪律：一个你从没看它失败过的测试，还不算测试。

- **把两个源文件回退到 `HEAD`。** 端到端 DeleteObjects 测试转红，每一个未指定版本的条目都返回 `AccessDenied`——对 issue #21735 的忠实复现——而单测直接抓住了 `{""}` 键（"一个不存在的 versionId 被暴露给了策略评估"）。打回，转绿。
- **只去掉 `TrimSpace`。** padded 用例在那条确切断言上转红——`got [7f4b6b5f-…dd8 ]`——证明这个 trim 不是装饰。恢复，转绿。
- **那个诱饵。** Multi-Delete 测试在 URL 上挂 `&versionId=query-level-decoy`，并断言它抵达不了任何条目的判定，这正是"读查询串"与"读逐条目有效版本"之间的分水岭。

改动只碰了五个文件（`cmd/bucket-policy.go`、`cmd/auth-handler.go`、两个测试、一处文档示例），在一个同时存在无关并发工作的工作树里用显式路径提交，所以邻近那些工作的任何改动都没有被卷进来。

## 起因与来源 {#source}

报告是上游 `minio/minio#21735`，2026-01-10 针对 `RELEASE.2025-09-07T16-13-09Z` 提出：一条 `Null:{s3:versionid:true}` 策略拒绝了未指定版本的 `DeleteObjects`。上游仓库于 2026-04-25 归档只读，所以没有上游修复可等，也没有维护者可协调——fork 是唯一的去处，这里的记录就是结案。

这个缺陷很老，且是继承来的。只要这个键存在，`getConditionValues` 就一直无条件写 `versionid`；基于长度的 `Null` 语义是上游的，在 fork 经由 `silo-pkg` 消费的那个 policy 包里。这与此前那次"阻止客户端输入影子化服务端派生条件值"的条件来源加固，是同一个函数、同一条脉络——一次关于"一条策略条件被允许相信关于请求的什么"的相关阅读，在这里延续为"它必须相信服务端将要实际操作的那个版本"。

## 结语 {#closing}

缺失不是空。一个无法通过"不放这个键"来表达"没有版本"的 map，会用"把值留空"来表达它；而一个数长度的 `Null`，会在每一个没有指定版本的请求上相信有版本被指定了。

如果只留下一句：**fail-closed 的 bug 才是危险的那种，因为显而易见的修复会把它翻成 fail-open**——所以把条件绑定到服务端实际操作的那个值，从操作实际读取的那条通道取，而不是那条顺手的通道；而当你止步于报告的这个面时，把你留在错误通道上的那些版本写下来，别指望下一个人自己找到它们。
