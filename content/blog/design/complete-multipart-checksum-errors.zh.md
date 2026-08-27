---
title: "BadDigest、InvalidRequest 与 CompleteMultipartUpload 校验和契约"
linkTitle: "分片完成校验和错误"
date: 2026-08-27
author: "Ruohang Feng"
summary: >
  SILO 能拒绝三类非法 CompleteMultipartUpload 请求，却返回了错误的 S3 错误码，并漏掉了一个校验和类型不匹配方向。本文完整记录 AWS 证据、上游历史、根因、操作域修复、回归矩阵，以及 CRC64NVME + COMPOSITE 的独立证据门槛。
tags: [设计, S3, 兼容性, 校验和]
weight: 31
draft: false
url: "/zh/blog/design/complete-multipart-checksum-errors/"
---

本文是 [SILO #48](https://github.com/pgsty/silo/issues/48) 的完整设计、调查与验证记录，同时划清它与相关问题 [SILO #50](https://github.com/pgsty/silo/issues/50) 的决策边界。

> **状态：** 服务端实现、完整本地包级验证与独立最终复审均已完成；提交、PR、远端 CI、发布与部署尚未进行。<br>
> **归属：** [`pgsty/silo`](https://github.com/pgsty/silo)，即 SILO 服务端仓库。<br>
> **实现范围：** 仅调整 `CompleteMultipartUpload` 的错误语义；不改变存储格式、校验和数学、依赖、Console、软件包或客户端。<br>
> **独立决策：** #50 仍需 AWS 探针证明，不纳入本次修复。

## 摘要 {#tldr}

#48 是成立且应该修复的问题，但原始描述需要两点校正。

第一，校验和类型比较比 Issue 描述的更严重。SILO 使用了位掩码包含关系，而不是相等比较。因此“创建为 `FULL_OBJECT`、完成时声明 `COMPOSITE`”会失败，反过来“创建为 `COMPOSITE`、完成时声明 `FULL_OBJECT`”却可能绕过类型检查。修复必须把基础算法和规范化后的分片对象类型分开、双向对称比较。

第二，“缺少分片校验和”这一行原本没有直接 AWS 响应证据。现在官方 boto/s3transfer 项目提供了足够强的证据：[Issue #241](https://github.com/boto/s3transfer/issues/241) 记录了真实 S3 响应——错误码为 `InvalidRequest`，消息点名 `sha256` 与缺失的第 1 个分片；[PR #242](https://github.com/boto/s3transfer/pull/242) 随后修复客户端并加入测试。因此无需再等待新的 AWS 账号探针，就可以实现这条响应契约。

本次接受的行为如下：

| `CompleteMultipartUpload` 失败条件 | 修复前 SILO | 正确行为 |
| --- | --- | --- |
| 客户端提供的对象校验和与组装结果不一致 | `XAmzContentChecksumMismatch` | `BadDigest` |
| 完成时的校验和类型与创建时不同，无论哪个方向 | 一个方向为 `InvalidArgument`；反方向可能放行 | `BadDigest` |
| 组合式上传的某个分片缺少校验和 | `InvalidPart` | `InvalidRequest`，并点名算法与分片号 |

修复采用“完成操作专用错误类型”。它明确不修改 `hash.ChecksumMismatch` 的全局映射，因此 `PutObject`、`UploadPart`、流式 Trailer 等操作仍保持现有的 `XAmzContentChecksumMismatch` 契约。

#50 是另一个问题。AWS 明确说 CRC64NVME 只支持完整对象校验和，但当前证据无法证明：当客户端显式请求 `CRC64NVME + COMPOSITE` 时，S3 一定拒绝，而不是接受后规范化。上游 MinIO 有意实现了规范化，并且在创建响应中返回 `FULL_OBJECT`，所以这也不是“静默”替换。改变它之前必须先做真实 AWS 原始请求探针。

## 范围与决策 {#scope}

本文回答两个不同问题：

1. #48 中的错误码偏差，是否是可观察、证据充分、应当修复的兼容性缺陷？
2. 同一批证据是否足以授权修改 #50 描述的 CRC64NVME 规范化行为？

结论是：

- **#48：修正描述后接受并实现。** S3 错误码属于线上协议契约。即使两边都拒绝请求，不同错误码仍会导致 SDK 分支、重试逻辑和运维诊断偏离。
- **#50：暂不实现。** 能力矩阵只能证明结果必须是完整对象校验和，不能证明非法请求应被拒绝、忽略还是规范化。这三种线上行为并不等价。

本次修复严格收口：不增加算法、不重算历史数据、不改变成功请求，也不重新解释 [#31](https://github.com/pgsty/silo/issues/31) 与 [#46](https://github.com/pgsty/silo/issues/46) 已修复的可选性规则。

## 证据台账 {#evidence}

不同来源的证明力并不相同，本次实现按以下层级作出判断。

| 等级 | 来源 | 能证明什么 | 局限 |
| --- | --- | --- | --- |
| A | [AWS 校验和上传指南](https://docs.aws.amazon.com/AmazonS3/latest/userguide/checking-object-integrity-upload.html) | 完整对象校验和不一致返回 `BadDigest`；算法/类型能力矩阵 | 不展示所有响应消息 |
| A | [AWS CompleteMultipartUpload API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) 与 [AWS CLI 参考](https://docs.aws.amazon.com/cli/latest/reference/s3api/complete-multipart-upload.html) | 完成时类型与创建时不同返回 `BadDigest` | 没有公布精确消息文本 |
| B+ | [boto/s3transfer #241](https://github.com/boto/s3transfer/issues/241) | 真实 AWS S3 响应：SHA256 的第 1 个分片缺少校验和时返回 `InvalidRequest`，并点名算法与分片 | 证据位于官方 SDK 项目 Issue，而不是 AWS API 参考页 |
| B+ | [boto/s3transfer #242](https://github.com/boto/s3transfer/pull/242) 与 0.6.1 变更记录 | 官方传输客户端改为把 UploadPartCopy 校验和传入完成请求，并用功能测试防止回归 | 主要是客户端侧证据 |
| B | 本地 API 探针与回归测试 | SILO 旧有三个错误码与反向绕过，在两个对象层后端上都可复现 | 只能证明 SILO，不能证明 AWS |
| C | MinIO 上游历史 | 解释现有行为如何进入代码谱系、为何一直存在 | 上游意图不等于 AWS 兼容性证明 |

这个区分很重要。#48 后来的校正评论在第三行只有二手资料时，正确地下调了其证据等级。现在，boto 的真实响应记录与已经合并的客户端修复补齐了缺口。

## 可观察协议契约 {#contract}

### 对象校验和不匹配 {#value-mismatch}

对于 `FULL_OBJECT` 分片上传，SILO 会合并已保存的分片校验和，再与完成请求中可选的对象级校验和比较。旧代码返回 `hash.ChecksumMismatch`，随后被全局 API 映射为：

```text
400 XAmzContentChecksumMismatch
```

AWS 明确规定，相应的完成阶段完整性失败应返回 `BadDigest`。但如果只复用现有通用 `ErrBadDigest`，静态消息仍会说 `Content-MD5`；CRC32、CRC32C、CRC64NVME 都不是 Content-MD5，因此依旧具有误导性。

新响应改为操作域专用消息：

```text
400 BadDigest
The CRC32 checksum you specified did not match the calculated checksum.
```

响应不会泄露期望值或客户端提供的摘要值。

### 校验和类型不匹配 {#type-mismatch}

`CreateMultipartUpload` 保存的校验和类型属于本次上传契约。完成时不能在 `COMPOSITE` 和 `FULL_OBJECT` 之间切换。

旧比较逻辑是：

```go
!provided.Type.Is(expectedType)
```

`ChecksumType.Is` 是位掩码包含判断，不是相等判断。以 CRC32 为例：

```text
创建 FULL_OBJECT + 完成 COMPOSITE => 被拒绝
创建 COMPOSITE   + 完成 FULL_OBJECT => 包含判断通过
```

第二种请求会继续按照持久化的组合式规则执行。如果调用方在 `FULL_OBJECT` 声明下提供的其实是组合校验和值，完成甚至可能成功。这不仅是错误标签不对，而是协议校验绕过。

修复先把双方都规范化为分片校验和类型，再分别比较：

1. 基础算法是否相同；
2. 对象类型是否相同（`COMPOSITE` 与 `FULL_OBJECT`）。

两个方向现在都返回 `400 BadDigest`。算法不匹配仍保留独立的 `InvalidArgument` 路径，因为 #48 与引用的 AWS 类型契约不足以授权扩大修改范围。

### 组合式分片缺少校验和 {#missing-part}

组合式上传的完成 XML 必须为每个列出的分片提供选定算法的校验和。SILO 过去把空客户端值与已保存值比较，然后返回 `InvalidPart`。

这混淆了三种不同状态：

- 分片或 ETag 不存在；
- 客户端提供了校验和，但值或算法错误；
- 必需的校验和元素完全缺失。

第三种状态现在拥有专用错误，线上消息遵循 boto/s3transfer 记录的 AWS 响应：

```text
400 InvalidRequest
The upload was created using a sha256 checksum. The complete request must include
the checksum for each part. It was missing for part 1 in the request.
```

服务端在遇到第一个缺失分片时返回错误，并携带真实分片号。`FULL_OBJECT` 行为不变：完成请求可以省略逐分片校验和，但一旦提供，仍必须正确。

## 上游真实情况 {#upstream}

这些行为来自继承代码，而非 SILO 有意重新设计。

- [MinIO PR #15433](https://github.com/minio/minio/pull/15433) 引入扩展校验和与全局 `hash.ChecksumMismatch -> XAmzContentChecksumMismatch` 映射。该映射适合上传数据流验证，却过度覆盖了完成阶段语义。
- [MinIO PR #20855](https://github.com/minio/minio/pull/20855) 增加完整对象校验和与 CRC64NVME，并引入类型比较。它还通过“看起来 AWS 会忽略模式并自行假设”的注释，有意把 CRC64NVME 规范化为完整对象。
- [MinIO PR #20953](https://github.com/minio/minio/pull/20953) 收紧非法算法/类型组合，却保留 CRC64NVME 特例。这证明它是上游的明确行为，而非偶然漏掉一个分支。
- [MinIO Issue #20944](https://github.com/minio/minio/issues/20944) 报告过 AWS `BadDigest` 与 MinIO `InvalidPart` 的差异。上游承认偏差，但没有修复。

MinIO 上游仓库现在已经归档。SILO 必须自行承担兼容性判断、测试和后续维护，不能再等待上游修正。

## 修复设计 {#design}

### 操作域专用错误 {#operation-scoped}

如果修改 `hash.ChecksumMismatch` 的全局映射，就会改变所有使用它的操作，形成一个证据不足、范围更大的兼容性变更。

本次在服务端 `cmd` 包中新增三个包内私有、由哨兵错误支撑的错误辅助函数。辅助函数与“请求头是否出现”标记均保持私有，避免扩大 SILO 对外 Go 兼容符号面：

- `completeMultipartChecksumMismatch`：映射到 `BadDigest`，并提供校验和语义正确的描述；
- `completeMultipartChecksumTypeMismatch`：映射到 `BadDigest`，并点名请求类型与创建类型；
- `missingPartChecksum`：映射到 `InvalidRequest`，携带算法与分片号。

只有 `CompleteMultipartUpload` 会产生它们。全局映射保持：

```text
hash.ChecksumMismatch => XAmzContentChecksumMismatch
```

因此 `PutObject` 与 `UploadPart` 行为不变，而且兼容性边界在代码中清晰可见。

### 双向对称类型验证 {#symmetric-validation}

比较前，持久化类型与请求类型都要加上分片上下文标志。原因是：裸 CRC 类型在 `ObjType()` 中表示非分片的完整对象校验和；同一个基础值进入分片上下文后则代表组合式类型。只有完成请求显式携带 `x-amz-checksum-type` 时才比较对象类型；省略一个可选头不能被解释为主动声明 `COMPOSITE`。

最终不变量是：

```text
请求基础算法 == 创建时基础算法
并且
请求分片对象类型 == 创建时分片对象类型
```

第二个条件只在类型头显式出现时生效。该比较是对称的，同时继续兼容现有 CRC64NVME 规范化。它修复 #48，却不会暗中替 #50 作出决定。

### 精确识别“缺失” {#precise-missing}

服务端原本就会为每个分片建立“完成 XML 中所有校验和字段”的映射。本次把行为拆成：

```text
COMPOSITE + 没有任何校验和字段 => missingPartChecksum / InvalidRequest
存在期望字段但值错误             => InvalidPart
只提供了另一种算法               => InvalidPart
FULL_OBJECT + 没有校验和字段      => 允许
FULL_OBJECT + 提供任意校验和字段  => 必须验证
```

这里没有把所有分片校验和失败都改成 `InvalidRequest`；只修改 AWS 证据直接覆盖的“字段缺失”状态。

同一处修改还纠正了内部 `InvalidPart` 的 expected/actual 字段顺序。通用 S3 `InvalidPart` 响应不会把摘要值发送给客户端，但内部错误文本与日志仍应描述正确。

## 回归与检测矩阵 {#tests}

API 级测试通过签名 HTTP 请求运行，并覆盖单盘与纠删码两个对象层后端。

| 测试 | 请求 | 必须断言 |
| --- | --- | --- |
| 完整对象摘要错误 | 分片正确、对象 CRC32 错误 | HTTP 400、`BadDigest`、正确消息、对象未提交 |
| 组合式对象摘要错误 | CRC32 分片值正确、组合对象值错误 | HTTP 400、`BadDigest`，覆盖独立的“校验和之校验和”路径 |
| 类型错误：完整到组合 | 创建 `FULL_OBJECT`，完成 `COMPOSITE` | HTTP 400、`BadDigest`，消息点名请求/期望类型 |
| 类型错误：组合到完整 | 创建 `COMPOSITE`，完成 `FULL_OBJECT` | HTTP 400、`BadDigest`，关闭旧包含关系绕过 |
| 省略可选类型头 | 创建 `FULL_OBJECT`，完成时只有摘要值、没有类型头 | 成功；省略不被视为显式 `COMPOSITE` |
| 算法不匹配护栏 | 创建 CRC32，完成时使用 CRC32C | 仍为 `InvalidArgument` |
| CRC64NVME #50 护栏 | CRC64NVME 创建与完成都显式写 `COMPOSITE` | 仍通过现有完整对象规范化成功 |
| 组合式缺失校验和 | CRC32 与 SHA256 组合上传；先全部省略，再只省略第 2 片 | HTTP 400、`InvalidRequest`，点名小写算法与真实缺失分片 |
| 全局映射护栏 | 直接映射 `hash.ChecksumMismatch` | 仍为 `XAmzContentChecksumMismatch` |
| UploadPart 护栏 | 客户端分片校验和值错误 | 仍为 `XAmzContentChecksumMismatch` |

聚焦验证命令：

```bash
go test ./cmd -run 'TestAPIErrCode$|TestAPICompleteMultipart(FullObjectChecksumMismatch|CompositeStillRequiresPartChecksums|CompositeChecksumMismatch|ChecksumTypeMismatch)$|TestAPIUploadPartServerSideChecksumDoesNotMaskClientErrors$' -count=1
```

2026-08-27 的实测结果：

```text
ok  github.com/minio/minio/cmd
```

吸收审查建议后，又重新执行完整本地包门禁：

```bash
go test ./cmd ./internal/hash -count=1
```

```text
ok  github.com/minio/minio/cmd           121.462s
ok  github.com/minio/minio/internal/hash   0.566s
```

`git diff --check` 同样通过。最终 diff 的独立审查仍是单独门禁。本地通过不等于远端 CI，通过合并不等于发布，发布也不等于生产部署。

## 独立对抗审查 {#independent-review}

本地 Claude Code 以只读 safe mode 对真实服务端 diff 完成了第一轮审查，结论为 **GO、无阻断项**。它独立确认了操作域映射、位掩码双向规范化、逐分片缺失检测、两个对象层后端覆盖，以及 UploadPart 行为保持不变。

审查指出四个有价值的缺口，并在第二次完整测试之前全部吸收：

- 区分“省略可选类型头”和“显式声明 `COMPOSITE`”；
- 把摘要值不匹配与类型不匹配拆成两个错误类型；
- 覆盖组合式“校验和之校验和”错误路径；
- 固定缺少第 2 片、算法不匹配与 CRC64NVME 规范化保持不变。

第一轮有一条审查疑问被一手资料否决：它怀疑校验和**类型**不匹配应返回 `InvalidRequest`。但 [AWS CompleteMultipartUpload 参考](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html) 与 [AWS CLI 参考](https://docs.aws.amazon.com/cli/latest/reference/s3api/complete-multipart-upload.html) 明确规定，完成类型与创建类型不一致时返回 `BadDigest`。

最终复审结论为 **FINAL GO、无阻断项**。Claude 明确撤回了先前的错误码疑问，同意接受 #48、推迟 #50，确认新增护栏保持了所有有意不变的行为，并确认中英文不存在漂移。

仍有三个修复前就存在、且不阻断本次工作的观察：

- 组合式分片数不匹配与摘要值不匹配都会成为 `BadDigest`，并使用同一描述；
- 完整对象校验和值如果带 `-N` 后缀，后缀会被忽略，但摘要本身仍会验证；
- 未知且非空的 `x-amz-checksum-type` 会被解析成组合式，而不是直接拒绝。

它们都不是本补丁引入的，也不改变 #48 结论。如果未来要追求更严格的消息或非法请求头兼容性，应分别立项处理。

## 为什么不顺便修 #50 {#issue-50}

#50 认为，应当在创建阶段拒绝 `CRC64NVME + COMPOSITE`。目前可以确认三件事：

1. AWS 算法矩阵只允许 CRC64NVME 作为完整对象校验和；
2. SILO 与 MinIO 上游会把请求规范化为完整对象状态；
3. 服务端在 `CreateMultipartUpload` 响应中返回 `x-amz-checksum-type: FULL_OBJECT`，因此替换是外部可见的，并非静默发生。

真正决定是否改代码的线上行为尚未确认：AWS 对显式非法组合究竟是拒绝，还是接受并返回/保存完整对象状态？能力矩阵无法回答。

上游历史也要求我们不要猜。PR #20855 有意加入规范化；PR #20953 在收紧其他非法组合时仍保留它。这可能来自真实 AWS 观察，但一句注释不是可复现的原始响应。

`PutObject` 也不应捆绑在这里。其 API 参考并未定义 `x-amz-checksum-type`，因此接受、拒绝还是忽略这个头，属于另一个“未文档化请求头”问题。

### 必需的 AWS 探针 {#issue-50-probe}

修改 #50 之前，应对普通 AWS S3 Bucket 捕获一组原始 SigV4 请求与响应：

1. 发送带 `x-amz-checksum-algorithm: CRC64NVME` 与 `x-amz-checksum-type: COMPOSITE` 的 `CreateMultipartUpload`；
2. 记录 HTTP 状态、错误码/消息、请求 ID 与全部校验和响应头；
3. 如果创建成功，上传一个分片并完成，记录 S3 是否要求逐分片值，以及 `HeadObject` 报告的类型；
4. 使用 `FULL_OBJECT` 作为控制组重复；
5. `PutObject` 单独测试，并明确标记为“未文档化请求头实验”。

只有捕获到 AWS 拒绝响应，才足以授权把规范化改成参数校验。如果 AWS 接受并规范化，就应修正或关闭 #50，而不是实现它。

## 兼容性与运维影响 {#impact}

- **成功请求：** 不变。
- **失败请求：** HTTP 状态仍为 400；S3 错误码与消息改为 AWS 兼容语义。
- **完整性：** 不减弱，并关闭反向类型绕过；任何失败完成都不会提交对象。
- **存储数据：** 不改变格式、编码、元数据、纠删码布局；无需迁移或回填。
- **性能：** 只有常数时间比较与错误构造；不增加数据读取或哈希遍历。
- **安全/隐私：** 新消息不返回摘要值，也不会额外加入 Bucket 或对象名。
- **滚动升级：** 全部节点升级前，失败请求可能得到不同错误码；成功对象仍完全兼容。
- **回滚：** 会恢复旧错误码和非对称比较；无需回滚数据。
- **其他仓库：** 不需要 Console、共享包、MCLI 或 SDK 修改；跨仓库交付只有这份公共设计记录。

## 合并与发布门禁 {#gates}

合并之前：

1. 完成包级测试矩阵与格式检查；
2. 对真实服务端 diff 和本文证据记录进行独立审查；
3. 除非 AWS 原始响应改变结论，否则不得把 #50 混入补丁；
4. 对最终提交运行远端 DCO、Go CI、漏洞与发布流水线检查；
5. 合并前确认分支仍基于最新 SILO `main`。

合并之后，仓库集成、发布制品、容器镜像、部署与生产探针必须分别记录。任何一项都不能由本地测试或文档构建结果推导出来。

## 结论 {#conclusion}

#48 是正确的兼容性问题，现在三行行为都有足够证据。最安全的修复不是全局重命名校验和错误，而是让 `CompleteMultipartUpload` 报告自己的协议错误：对称比较校验和类型，并把真正缺少组合式分片校验和的状态与“分片不存在”“值错误”区分开。

#50 只是在发现历史上相关，证明链并不相同。当前 CRC64NVME 规范化是有意且可见的。没有 AWS 精确响应之前，贸然修改只会用一个未经验证的假设替换另一个。

这就是本次设计的核心边界：实现官方契约与官方测试能够证明的内容；把代码审查发现的隐藏后果纳入回归；剩余策略问题必须通过明确、可重复的证据门禁。
