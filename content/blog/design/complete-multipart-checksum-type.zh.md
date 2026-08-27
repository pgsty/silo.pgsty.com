---
title: "为什么 CompleteMultipartUpload 必须返回 ChecksumType：PR #57 评审记录"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-08-26
author: "冯若航"
summary: >
  SILO 已经正确持久化 multipart checksum，也能通过 HEAD 等 API 返回类型，但 CompleteMultipartUpload 会把 ChecksumType 从 XML 结果中丢掉。本文记录缺陷前因后果、PR #57 的两行生产代码为什么有效、评审发现、CI 与合并决策、兼容性影响，以及剩余的发布边界。
tags: [设计, S3, 兼容性, Checksum]
weight: 20
draft: false
url: "/zh/blog/design/complete-multipart-checksum-type/"
---

本文是 [SILO #47](https://github.com/pgsty/silo/issues/47) 与 [PR #57](https://github.com/pgsty/silo/pull/57) 的设计、评审与决策归档。

> **截至 2026-08-26 的状态：** [PR #57](https://github.com/pgsty/silo/pull/57) 已批准并合并为 [`a96116b1`](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee)，[#47](https://github.com/pgsty/silo/issues/47) 随后自动关闭。被测 PR head 的九个检查项全部通过，合并后 `main` 的 Go CI 与 VulnCheck 也全绿。尚未验证任何 tag、release package、container image、deployment 或 production endpoint 已包含本修复。<br>
> **范围：** 让 `CompleteMultipartUploadResult` 返回服务器已经知道的 checksum type；不增加任何新 checksum 算法。<br>
> **归属：** [`pgsty/silo`](https://github.com/pgsty/silo) 服务端仓库。<br>
> **发布边界：** 代码评审、合并、`main` 全绿、tag、软件包、容器镜像、部署与生产验证是相互独立的门槛。

## 太长不看（TL;DR） {#tldr}

SILO 早已为完成后的 multipart 对象计算并持久化正确的 checksum type。`HEAD`、`ListParts` 与 `GetObjectAttributes` 都能返回它，唯独 completion 响应不行，因为对应的 Go response struct 只有各算法 checksum value，没有 `ChecksumType` 字段。

PR #57 增加这个字段，从已有 checksum map 中复制现成值，在 compatibility baseline 中登记新的导出符号，并测试 `FULL_OBJECT`、`COMPOSITE` 和无 checksum 三种情况。它不重新计算数据、不修改 metadata、不迁移对象，也不放松任何完整性检查。

这个修复正确而且范围刻意狭窄。Maintainer 批准了 fork workflow，把陈旧 PR 分支更新到当前 `main`，要求新一轮检查全部通过，提交正式批准评审，并在保留贡献者 sign-off commit 的前提下完成合并。仓库集成已经完成，release delivery 仍是独立门槛。

## 问题从哪里来 {#origin}

这个缺陷是在调查 [#31](https://github.com/pgsty/silo/issues/31) 时发现的。真实 boto3 客户端暴露出一组彼此相邻但边界不同的 multipart checksum 兼容问题。#31 是数据路径故障：`FULL_OBJECT` CRC32 multipart upload 可能在 completion 阶段失败；它由 `0cff48f6c` 与 `75859690b` 独立修复，并在 2026-08-04 关闭。那次审查有意把四个相邻发现拆成 [#46](https://github.com/pgsty/silo/issues/46)、#47、#48 与 #50，而没有把它们混成一个 checksum bug。

对象能够成功完成后，还残留着另一处不一致：

```text
complete_multipart_upload() -> ChecksumType: None
head_object()               -> ChecksumType: FULL_OBJECT
```

AWS S3 在两处都会返回 `FULL_OBJECT`。SILO 的 completion XML 已经返回 checksum value，完成后的对象也保留着正确 type，但 completion 的 SDK 结果却把 type 暴露成 null。

这个观察形成了 #47。它是响应展示缺陷，不是 checksum 计算或存储缺陷；它不能解释 #31 之前的 `InvalidPart`，修复它也不能替代 [#46 的服务端逐 part checksum 工作](/zh/blog/design/uploadpart-checksum/)，后者随后以 `7fea6d5a5` 独立落地。

## S3 响应契约 {#contract}

[AWS CompleteMultipartUpload API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) 把 `ChecksumType` 定义为 `CompleteMultipartUploadResult` 的 XML 元素，合法值只有：

| 值 | 含义 |
| --- | --- |
| `FULL_OBJECT` | 返回的 checksum 覆盖完成后对象的逻辑字节。 |
| `COMPOSITE` | 对象 checksum 由 multipart 各 part checksum 派生。 |

对象没有额外 S3 checksum 时，这个元素应当缺席；服务器不能在没有 checksum value 时凭空制造一个 type。

这个区别对客户端很重要。同名的 Base64 checksum 字段既可能表示完整对象直接摘要，也可能表示 multipart 组合结果。客户端要验证 completion 响应，就需要知道 type，才能正确解释 checksum，并与 `CreateMultipartUpload` 阶段选择的模式比较。

## PR 之前 SILO 做了什么 {#before}

completion handler 已经把提交完成的 `ObjectInfo` 交给 `generateCompleteMultipartUploadResponse`，而 generator 也早已调用：

```go
cs, _ := oi.decryptChecksums(0, h)
```

checksum decoder 返回的 map 同时包含算法值和规范化对象类型：

```text
CRC32                 -> "...Base64..."
x-amz-checksum-type    -> "FULL_OBJECT" 或 "COMPOSITE"
```

response struct 会复制 CRC32、CRC32C、CRC64NVME、SHA1、SHA256，却根本没有位置存放 type：

```text
已提交的 ObjectInfo.Checksum
        -> decryptChecksums
        -> checksum values + x-amz-checksum-type
        -> CompleteMultipartUploadResponse
        -> value 被复制，type 被丢弃
        -> XML 没有 <ChecksumType>
        -> SDK 返回 None / null
```

其他接口使用同一份状态时没有问题。`ListParts` 与 `GetObjectAttributes` 已经返回 `ChecksumType`，`HEAD` 也会报告持久化 type；丢失只发生在 `CompleteMultipartUpload` 的成功 XML。

## PR #57 修改了什么 {#implementation}

贡献者 diff 只有一个已 sign-off 的提交，修改三个文件，新增 60 行、删除 0 行；生产代码只有两行。Maintainer 随后把当前 `main` 合入贡献者分支以刷新 CI 上下文；这次 merge 改变的是历史，不是三文件产品 diff。

### 增加响应字段 {#field}

```go
ChecksumType string `xml:"ChecksumType,omitempty"`
```

`omitempty` 是兼容契约的一部分：没有 checksum 的上传继续保持原来的 XML 形状。

### 复制已经规范化的值 {#mapping}

```go
ChecksumType: cs[xhttp.AmzChecksumType],
```

generator 不会根据 ETag、算法名或 part 数量重新猜测 type，而是使用与其他 checksum value 同源的解码 metadata。

### 测试响应表面 {#tests}

新增测试覆盖：

- 无 checksum：Go 字段为空，XML 不出现 `<ChecksumType>`；
- full-object checksum：字段为 `FULL_OBJECT`，XML tag 存在；
- multipart composite checksum：字段为 `COMPOSITE`，XML tag 存在。

测试先检查 XML 编码前的 response value，再独立检查编码后的省略/出现行为。

### 登记导出兼容符号 {#baseline}

`CompleteMultipartUploadResponse.ChecksumType` 是导出的 Go 字段。SILO rebrand guard 会对导出兼容表面做精确集合比较，因此 PR 正确地把它加入 `buildscripts/rebrand-guard/compat-baseline.json`。这是对有意公共表面变化的确认，不是绕过 guard。

## 为什么这个修复有效 {#why-it-works}

正确性建立在一条很短的既有不变量链上。

1. `ObjectInfo.Checksum` 是已经提交的 checksum metadata；对象层返回已提交 `ObjectInfo` 以后，completion 才生成响应。
2. `decryptChecksums(0, h)` 复用现有 metadata 解密路径，包括 SSE-C 所需的请求 header；没有第二套解密机制。
3. checksum decoder 只有在解出非空 checksum value 时，才写入 `x-amz-checksum-type`。
4. 既有 `ChecksumType.ObjType()` 会把可到达状态规范化成 `FULL_OBJECT` 或 `COMPOSITE`。
5. nil map 或不存在 key 的索引结果是空字符串。
6. XML `omitempty` 会删除空字符串对应的元素。

最终行为完全确定：

| 已提交 checksum 状态 | Map 值 | Completion XML |
| --- | --- | --- |
| 没有额外 checksum | 空 | 没有 `<ChecksumType>` |
| full-object checksum | `FULL_OBJECT` | `<ChecksumType>FULL_OBJECT</ChecksumType>` |
| multipart composite checksum | `COMPOSITE` | `<ChecksumType>COMPOSITE</ChecksumType>` |

所以这次修改只是把已经成立的状态投影到 wire response。它不创建 checksum state，也不能把错误 checksum 变正确；它只是让响应如实描述服务器已经验证并提交的状态。

## 评审与验证 {#review}

评审在贡献者分支更新到当前 `main` 后进行。更新产生 head `c4b9d38d`；其 tree hash `39ec44c6b390c441413e490370f70fbacc4e6a91` 与隔离本地 no-commit merge 完全一致。合并结果干净，并包含 `main` 中间新增的 checksum 工作。

在这份精确 merge result 上完成的本地验证包括：

```text
定向 ChecksumType 回归测试
CGO_ENABLED=0 go test ./cmd/ -count=1 -timeout 30m
go vet ./cmd/
gofmt 与 git diff --check
rebrand compatibility guard
本地 DCO 规则
```

定向回归测试在 2.174 秒内通过，完整 `cmd` package 测试在 168.956 秒内通过。commit author email 与 `Signed-off-by` trailer 完全匹配。Git commit 密码学签名与 DCO 是两件事，本仓库不要求前者。

另一次独立、本机、只读 Claude Code 对抗审查检查了合并 diff、checksum 序列化、XML 路径、当前 `main`、测试、DCO 和 compatibility guard。它的结论是 **COMMENT**：生产修改正确且安全，但倾向于在合并前再加一个 HTTP 级 completion 测试。Maintainer 认同该测试能提升保真度，但不同意把它列为 blocker：handler 直接委托给已经测试的 generator，现有真实 MPU 测试也已经覆盖持久化的 `FULL_OBJECT` 与 `COMPOSITE` 状态。因此正式 GitHub review 记录为 **APPROVED**，HTTP 级测试作为后续项。

### Actions、分支刷新与合并 {#merge-sequence}

最初四个 `action_required` run 创建于 2026-08-09，使用的是 PR 旧 base。批准后 DCO 通过，但旧 [VulnCheck run](https://github.com/pgsty/silo/actions/runs/31306998949) 使用 Go 1.26.5，命中了后来公布、在 Go 1.26.6 修复的标准库漏洞。此时当前 `main` 已经迁移到 Go 1.27.0，最近一次 VulnCheck 也是绿色。把这次陈旧失败解释为产品回归不对，把红灯直接忽略同样不对。

最终决策是刷新测试上下文，而不是重跑或豁免陈旧结果：

1. GitHub update-branch API 把当前 `main`（`8d76a255c`）合入贡献者 head `d014a12cf`，无冲突地产生 `c4b9d38d`。
2. GitHub 为刷新后的 head 新建四个 fork workflow；四个 run 再次被显式批准。
3. 九个检查项全部通过：[DCO](https://github.com/pgsty/silo/actions/runs/32922040560)、[VulnCheck](https://github.com/pgsty/silo/actions/runs/32922040457)、[Go CI](https://github.com/pgsty/silo/actions/runs/32922040467) 的六个 job 与 [Test Release Pipeline](https://github.com/pgsty/silo/actions/runs/32922040567)；其中 release validation 用时 11 分 26 秒。
4. 针对 `c4b9d38d` 提交正式批准评审。
5. 合并使用 expected-head guard 与仓库常规 merge 策略，产生 `a96116b1`；它保留贡献者 sign-off commit，而没有通过 squash 重写。PR 的 `Resolves #47` 在一秒后自动关闭 issue。
6. 合并后 `main` 的 [VulnCheck](https://github.com/pgsty/silo/actions/runs/32922815310) 与 [Go CI](https://github.com/pgsty/silo/actions/runs/32922815278) 六个 job 再次全部通过；最慢的 cross-compile 用时 9 分 54 秒。

这段过程很重要，因为验收标准不是“这份 patch 曾经通过一次”。真正被合入当前 `main` 的精确 tree 必须就是被评审、被测试的 tree，陈旧 CI 环境不能代替这份证据。

## 对这个 PR 的评价 {#evaluation}

### 做得好的地方 {#strengths}

- **范围与缺陷完全匹配。** 两行生产代码恢复一个丢失的响应元素。
- **复用权威状态。** 没有重复推导 type，也没有新增 checksum algorithm 分支。
- **向后兼容明确。** `omitempty` 保持无 checksum 响应不变。
- **测试覆盖两个合法值与缺席状态。** 回归不能再静默恢复成 null。
- **兼容基线有意更新。** CI 没有被削弱。
- **DCO 来源完整。** 唯一提交的 sign-off 匹配。

### 非阻断评审注记 {#notes}

测试对 generator 改动本身是正确的，但 fixture 没有逐字节模拟生产环境的全部 multipart metadata flag：

- `FULL_OBJECT` fixture 通过非 multipart checksum 状态得到正确值，而不是真实完成对象所携带的 `ChecksumMultipart`、`ChecksumIncludesMultipart` 与 `ChecksumFullObject`；
- `COMPOSITE` fixture 带 multipart flag，但没有真实持久化的逐 part checksum block。

现有 API 级测试已经运行真正的 `FULL_OBJECT` 和 `COMPOSITE` completion，并验证提交后的 type；PR #57 补上剩余的“解码状态到 response field/XML”投影测试。给完整 API 测试再加一条 response 断言会提升保真度，但不是这次两行修复的合并前置条件。

PR 把 `ChecksumType` 放在算法字段之前，而 AWS 示例与 SILO 较新的 `CopyObjectResponse` 都把它放在最后。主流 S3 SDK 按元素名解析 XML，所以这属于 parity/style 细节，不是兼容 blocker；是否移动字段是可选项。

最后，贡献者 commit title 使用 `feat:`，但 PR 自己正确标记为 bug fix。最终 merge 保留了这个 sign-off commit，没有重写历史。这是 history/style 瑕疵，不是协议或发布 blocker。

## 为什么不能把新算法塞进这个 PR {#algorithm-scope}

AWS 现在还列出 SHA512、MD5、XXHASH 等字段，但只增加这些 XML 字段会制造虚假兼容性。

SILO 当前 checksum 实现支持 CRC32、CRC32C、CRC64NVME、SHA1、SHA256。真正增加一种算法，需要同时实现：

- request header 解析与校验；
- 流式 checksum 计算；
- multipart `FULL_OBJECT` 或 `COMPOSITE` 语义；
- 盘上 checksum 编码与解码；
- UploadPart、UploadPartCopy、completion、copy、replication、HEAD、GET、ListParts、GetObjectAttributes；
- SDK/client 互操作，以及完整的加密、压缩、版本化测试矩阵。

PR #57 不应为服务器不会计算、不会持久化的算法增加 response-only 占位字段。每一类新算法都需要独立兼容性决策、实现与评审。

## 兼容性与运维影响 {#impact}

- **S3 客户端：** 支持 checksum 的客户端在此后成功完成 MPU 时收到 `ChecksumType`，不再得到 null。
- **Wire format：** 只有存在额外 checksum 时才新增一个 XML 元素；忽略未知元素的旧客户端不受影响。
- **完整性：** 不重新计算 checksum，也不改变接受条件；原有校验语义不变。
- **存储数据：** 对象、part、metadata 与纠删码格式均不变化；无需迁移或回填。
- **既有对象：** 对象状态原本就是正确的；过去的一次性 completion response 无法补发，可用 HEAD 或 GetObjectAttributes 查看 type。
- **加密：** 响应复用既有 checksum metadata 解密路径，不暴露 key material 或新的秘密。
- **性能：** 一次 map lookup 和一个可选 XML 元素；不增加对象读取、hash pass 或与对象大小成比例的分配。
- **滚动升级：** 旧节点省略元素，新节点返回元素；请求与存储兼容，但所有服务节点升级后客户端可见行为才稳定。
- **回滚：** 回滚只会让今后的 completion 再次缺字段，不会破坏修复版本期间创建的对象。
- **其他仓库：** 不需要服务端依赖、silo-pkg、MCLI 或 Console 修改；公共文档归本站所有。

这是一个增量兼容修复，不是要求操作者重写数据的新功能。唯一外部可见变化是成功响应更加完整。

## 合并与发布决策 {#decision}

最终决策包含六部分：

1. 接受狭窄的状态投影修复，不重新计算 checksum，也不改变存储；
2. SHA512、MD5、XXHASH 等算法族在得到服务端全链路支持前不得塞入 #57；
3. HTTP 级 completion 测试是有价值的后续工作，但不是这个直接受测 generator 修复的 blocker；
4. 拒绝把陈旧 CI 当作合并证据，把分支更新到当前 `main` 并批准新创建的 workflow；
5. 刷新后的 head 正式批准且所有检查全绿后，使用 expected-head guard 与普通 merge，保留 DCO sign-off contribution；
6. 让 `Resolves #47` 自动关闭 issue，再独立验证生成的 `main` workflow。

本次不需要 dependency update、storage migration 或跨仓库实现。仓库集成门槛已经完成。

绿色 `main` 仍不能证明 SILO tag、release package、container image、deployment 或 production endpoint 已包含本修复。下一次 release 交付时，仍须分别记录这些尚未验证的门槛。

## 结论 {#conclusion}

PR #57 是一个很好的小型兼容修复范例：它的正确性来自尊重已有单一事实源。checksum type 早已被计算、校验、持久化、解密，并能通过其他 API 看到；completion response 只是漏了把它投影到 XML。

被接受的修复只补上这个投影，不做任何其他事情。它让 wire response 说实话，却不触碰用户数据、checksum 数学、存储布局或算法范围。Fork workflow、刷新 head 评审、合并、自动关闭 issue 与合并后 `main` 验证都已完成。剩余的是交付纪律：必须把这个已合并修复与已 tag、已打包、已构建镜像、已部署和已在生产验证严格区分。
