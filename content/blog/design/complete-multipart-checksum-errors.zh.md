---
title: "BadDigest、InvalidRequest 与 CompleteMultipartUpload 校验和契约"
linkTitle: "分片完成校验和错误"
date: 2026-08-27
lastmod: 2026-10-19
author: "冯若航"
summary: >
  CompleteMultipartUpload 依据已存储的校验和类型执行校验并返回操作专用错误。Server 20260903 已拒绝 CRC64NVME 与 COMPOSITE 组合；流式校验和后续修复随 Server 20260916 发布。
tags: [设计, S3, 兼容性, 校验和]
weight: 31
draft: false
url: "/zh/blog/design/complete-multipart-checksum-errors/"
---

[#48](https://github.com/pgsty/silo/issues/48) 与 [#50](https://github.com/pgsty/silo/issues/50) 的修复已随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布，流式校验和后续修复（[PR #143](https://github.com/pgsty/silo/pull/143)）已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布。本文取代八月早期提案中“暂时保留 `CRC64NVME` 静默规范化”的结论。

## 20261018：消息文字与提交失败 {#october-errors}

[Server 20261018](/zh/blog/release/silo-20261018/#reliability) 包含 [#225](https://github.com/pgsty/silo/issues/225)、[#229](https://github.com/pgsty/silo/issues/229) 与 [#238](https://github.com/pgsty/silo/issues/238) 的消息格式修复：`Content-MD5` 大小写对齐 S3 规范、`PutObject` 与 `UploadPart` 校验失败时显示已知算法名，以及移除 `CompleteMultipartUpload` 错误消息中重复的 `"checksum"` 字样。未知算法仍保留通用描述，各操作对应的 S3 错误码与校验条件保持不变。下文提及的“保持 `UploadPart` 错误映射器不变”对应八月修复范围；十月版本更新了其消息文本生成。客户端应依据 HTTP 状态码与 S3 错误码判断失败原因，而非解析完整的英文消息字符串。

此外，[#232](https://github.com/pgsty/silo/issues/232) 将最终提交阶段暂存 `xl.meta` 丢失归类为 `503 SlowDownWrite`。该状态与下表中客户端提供错误校验和导致的 HTTP 400 不同，也不改变请求体不完整时的原有处理逻辑。详见 [S3 写入提交错误参考](/zh/reference/s3-api-compatibility/#write-commit-errors)。

## 为什么必须在完成阶段执行校验 {#problem}

`CreateMultipartUpload` 在初始化上传时确定校验和算法与对象校验和类型，每次 `UploadPart` 调用分别记录对应分片的校验和。`CompleteMultipartUpload` 必须依据已保存的上传契约，同时校验最终对象摘要与任何显式声明的校验和类型断言：请求既不能因为基础算法相同而在完成阶段将 `COMPOSITE` 篡改为 `FULL_OBJECT`，也不能通过省略最终摘要来绕过不匹配的类型断言。

修复方案严格区分“省略校验和类型”与“显式声明校验和类型”，仅规范化内部表示标志；同时为分片完成路径引入操作专用错误类型，保持 `UploadPart` 及全局校验和不匹配错误映射器的原有行为不变。

## 当前错误契约 {#tests}

下表列出的所有校验失败均返回 HTTP 400，且不会提交新的已完成对象。

| 请求条件 | S3 错误码 |
| --- | --- |
| 整对象（`FULL_OBJECT`）或组合对象（`COMPOSITE`）摘要不匹配 | `BadDigest` |
| 显式声明的合法类型与初始化类型不一致（包括仅提供类型的断言） | `BadDigest` |
| 未知或小写的校验和类型 token | `InvalidArgument` |
| 完成阶段提供的校验和算法与初始化算法不一致 | `InvalidArgument` |
| 缺少组合校验和所需的分片校验和 | `InvalidRequest`（指明算法与分片编号） |
| 初始化时将 `CRC64NVME` 与 `COMPOSITE` 组合 | `InvalidArgument` |
| 完成时同时提供 `CRC64NVME` 摘要与 `COMPOSITE` 类型（在解析阶段被拒绝） | `InvalidArgument` |
| 对 `CRC64NVME` `FULL_OBJECT` 上传在完成时仅断言 `COMPOSITE` 类型 | `BadDigest` |
| `UploadPart` 期间客户端提供的分片校验和错误 | `XAmzContentChecksumMismatch` |

对于 `FULL_OBJECT` 上传，完成请求 XML 中可以省略分片级校验和，但凡是显式提供的分片校验和仍会与已存储的分片元数据逐一比对。与初始化类型一致的纯类型断言允许通过；省略可选的校验和类型请求头不会隐式断言 `COMPOSITE`。将 `SHA1` 或 `SHA256` 与 `FULL_OBJECT` 组合的请求会在算法与类型解析阶段直接被拒绝，不会进入已存储类型比对阶段。

## CRC64NVME 决策与源码证据 {#issue-50}

早期评审曾考虑在收集更多 SDK 兼容性证据前暂缓处理 [#50](https://github.com/pgsty/silo/issues/50)（此前代码会将 `CRC64NVME + COMPOSITE` 静默规范化为 `FULL_OBJECT`）。然而静默规范化会掩盖非法的客户端请求，违背快速失败原则。[PR #93](https://github.com/pgsty/silo/pull/93) 在请求头与 trailer 解析路径中直接拒绝 `CRC64NVME + COMPOSITE` 组合，[PR #96](https://github.com/pgsty/silo/pull/96) 则移除了 `CompleteMultipartUpload` 阶段的静默规范化。由于完成请求既可能在请求头解析阶段失败（同时携带 `CRC64NVME` 摘要与 `COMPOSITE` 类型），也可能在已存储类型比对阶段失败（对已初始化为 `CRC64NVME` `FULL_OBJECT` 的上传仅发送裸 `COMPOSITE` 类型请求头），上表分别记录了对应的两种错误码（`InvalidArgument` 与 `BadDigest`）。

最初的完成阶段错误映射由 [PR #74](https://github.com/pgsty/silo/pull/74) 引入，显式类型断言后续修复（`7e079ff05`）经由 [PR #85](https://github.com/pgsty/silo/pull/85) 合入。[`cmd/erasure-multipart-fullobject_test.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-multipart-fullobject_test.go) 中的处理器测试覆盖了整对象与组合摘要不匹配、纯类型断言、非法 token 以及 `CRC64NVME` 的两个拒绝阶段。

## 独立的流式校验和后续修复 {#streaming}

[PR #143](https://github.com/pgsty/silo/pull/143) 修复了 `@cbornet` 报告的 [#107](https://github.com/pgsty/silo/issues/107)，专门处理 AWS Java SDK v2 使用的混合请求模式：`aws-chunked` 流式请求在 `x-amz-trailer` 中声明了校验和请求头，但实际通过普通 HTTP 请求头直接发送该校验和值。该修复同时拒绝格式非法的请求头校验和值，防止因解析失败而静默跳过校验。此项修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布，与分片完成阶段的错误映射相互独立。

## 兼容性与剩余边界 {#impact}

检查 S3 错误码的客户端在完成阶段遇到摘要或类型不匹配时会收到 `BadDigest`，遇到缺失组合分片校验和时会收到 `InvalidRequest`。不带校验和的常规分片上传与 ETag 语义保持不变，无需迁移磁盘元数据。相邻的分片上传校验契约详见 [CompleteMultipartUpload ChecksumType 响应契约](/zh/blog/design/complete-multipart-checksum-type/)、[UploadPart 校验和设计](/zh/blog/design/uploadpart-checksum/) 与 [重复分片编号安全公告](/zh/blog/security/duplicate-part-numbers/)。

目前仍保留三项较窄的边界行为：

- 若 `CreateMultipartUpload` 初始化时未记录任何校验和算法，但在完成阶段提供了最终校验和摘要，请求会以 `BadDigest` 拒绝。
- 组合校验和的分片数量不匹配与摘要值不匹配共用同一条 `BadDigest` 错误描述。
- 附加在 `FULL_OBJECT` 校验和请求头末尾的 `-N` 分片数后缀会被忽略，不作为分片数断言进行校验。
