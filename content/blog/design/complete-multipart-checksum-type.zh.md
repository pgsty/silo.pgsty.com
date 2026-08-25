---
title: "为什么 CompleteMultipartUpload 必须返回 ChecksumType：PR #57 评审记录"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-08-26
author: "冯若航"
summary: >
  SILO 已经正确持久化 multipart checksum，也能通过 HEAD 等 API 返回类型，但 CompleteMultipartUpload 会把 ChecksumType 从 XML 结果中丢掉。本文记录缺陷前因后果、PR #57 的两行生产代码为什么有效、评审发现、兼容性影响，以及剩余的合并与发布门槛。
tags: [设计, S3, 兼容性, Checksum]
weight: 20
draft: false
url: "/zh/blog/design/complete-multipart-checksum-type/"
---

本文是 [SILO #47](https://github.com/pgsty/silo/issues/47) 与 [PR #57](https://github.com/pgsty/silo/pull/57) 的设计、评审与决策归档。

> **截至 2026-08-26 的状态：** PR #57 仍然 open，当前可干净合并。代码评审结论为 **GO WITH NON-BLOCKING NOTES**，置信度 high。四组 fork workflow 仍在等待 maintainer 批准，因此 PR 尚未合并，也没有任何 release artifact 包含该修改。<br>
> **范围：** 让 `CompleteMultipartUploadResult` 返回服务器已经知道的 checksum type；不增加任何新 checksum 算法。<br>
> **归属：** [`pgsty/silo`](https://github.com/pgsty/silo) 服务端仓库。<br>
> **发布边界：** 代码评审、合并、`main` 全绿、tag、软件包、容器镜像、部署与生产验证是相互独立的门槛。

## 太长不看（TL;DR） {#tldr}

SILO 早已为完成后的 multipart 对象计算并持久化正确的 checksum type。`HEAD`、`ListParts` 与 `GetObjectAttributes` 都能返回它，唯独 completion 响应不行，因为对应的 Go response struct 只有各算法 checksum value，没有 `ChecksumType` 字段。

PR #57 增加这个字段，从已有 checksum map 中复制现成值，在 compatibility baseline 中登记新的导出符号，并测试 `FULL_OBJECT`、`COMPOSITE` 和无 checksum 三种情况。它不重新计算数据、不修改 metadata、不迁移对象，也不放松任何完整性检查。

这个修复正确而且范围刻意狭窄。合并前，maintainer 仍须批准并运行所有待处理的 GitHub Actions，要求每个 workflow 全绿，并在最终 squash commit 中保留贡献者的 DCO trailer。

## 问题从哪里来 {#origin}

这个缺陷是在调查 [#31](https://github.com/pgsty/silo/issues/31) 时发现的。真实 boto3 客户端暴露出一组彼此相邻但边界不同的 multipart checksum 兼容问题。#31 是数据路径故障：`FULL_OBJECT` CRC32 multipart upload 可能在 completion 阶段失败；该问题已经独立修复。

对象能够成功完成后，还残留着另一处不一致：

```text
complete_multipart_upload() -> ChecksumType: None
head_object()               -> ChecksumType: FULL_OBJECT
```

AWS S3 在两处都会返回 `FULL_OBJECT`。SILO 的 completion XML 已经返回 checksum value，完成后的对象也保留着正确 type，但 completion 的 SDK 结果却把 type 暴露成 null。

这个观察形成了 #47。它是响应展示缺陷，不是 checksum 计算或存储缺陷；它不能解释 #31 之前的 `InvalidPart`，修复它也不能替代 [#46 的服务端逐 part checksum 工作](/zh/blog/design/uploadpart-checksum/)。

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

这个 PR 只有一个已 sign-off 的提交，修改三个文件，新增 60 行、删除 0 行；生产代码只有两行。

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

评审基于 GitHub 当前 synthetic merge commit 进行，它的两个父提交分别是最新 `main` 和 PR head。虽然贡献者分支相对最初 base 落后 12 个提交，但当前合并结果干净，并能与 `main` 中间新增的 checksum 工作共同编译。

在这份精确 merge result 上完成的本地验证包括：

```text
定向 ChecksumType 回归测试
CGO_ENABLED=0 go test ./cmd/ -count=1 -timeout 30m
go vet ./cmd/
gofmt 与 git diff --check
rebrand compatibility guard
本地 DCO 规则
```

完整 `cmd` 测试在 137.598 秒内通过。commit author email 与 `Signed-off-by` trailer 完全匹配。Git commit 密码学签名与 DCO 是两件事，本仓库不要求前者。

另一次独立、本机、只读 Claude Code 对抗审查检查了合并 diff、checksum 序列化、XML 路径、当前 `main`、测试、DCO 和 compatibility guard。结论为 **GO WITH NON-BLOCKING NOTES**；对正确性、兼容性、安全性与可合并性的置信度 high。

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

最后，commit title 使用 `feat:`，但 PR 自己正确标记为 bug fix。最终 squash subject 应改用 `fix:`；不需要贡献者为此修改代码或重写提交。

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

最终代码评审决策是：**远端 CI 全绿后接受 PR #57**。

合并前必须：

1. 审查 fork diff，并批准待处理 GitHub Actions；
2. 要求 DCO、Go CI、Test Release Pipeline、VulnCheck 全部通过；
3. 如果 `main` 再次前进，确认被测 merge ref 仍包含当前 `main`；
4. 使用 bug-fix subject squash，例如 `fix: return ChecksumType from CompleteMultipartUpload`；
5. 在最终 squash commit body 中保留 `Signed-off-by: Shooks <justanormalme@gmail.com>`。

合并本 PR 不需要扩代码、不需要 rebase、不需要升级依赖、不需要存储迁移，也不需要跨仓库实现。PR 的 `Resolves #47` 关系应在合并后自动关闭 issue。

合并后，`main` 全绿只能证明仓库集成成功，不能证明 SILO release、软件包、容器镜像、部署或生产端点已经包含修复；这些门槛必须分别记录。

## 结论 {#conclusion}

PR #57 是一个很好的小型兼容修复范例：它的正确性来自尊重已有单一事实源。checksum type 早已被计算、校验、持久化、解密，并能通过其他 API 看到；completion response 只是漏了把它投影到 XML。

被接受的修复只补上这个投影，不做任何其他事情。它让 wire response 说实话，却不触碰用户数据、checksum 数学、存储布局或算法范围。剩余工作是操作纪律：运行来自 fork 的 workflow、在 squash 中保留 DCO 来源、只在全绿后合并，并把“已合并”与“已发布”严格分开。
