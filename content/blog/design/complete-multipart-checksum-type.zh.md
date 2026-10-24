---
title: "为什么 CompleteMultipartUpload 必须返回 ChecksumType：PR #57 评审记录"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-09-16
author: "冯若航"
summary: >
  CompleteMultipartUpload 现已在 XML 响应体中返回已存储的 ChecksumType；该修复已随 Server 20260903 发布。
tags: [设计, S3, 兼容性, 校验和]
weight: 20
draft: false
url: "/zh/blog/design/complete-multipart-checksum-type/"
---

Shooks（`@Dansyuqri`）贡献的 [PR #57](https://github.com/pgsty/silo/pull/57) 修复了 [#47](https://github.com/pgsty/silo/issues/47)，并已随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布。当对象保存了附加 S3 校验和时，`CompleteMultipartUpload` 的 XML 响应现在会一并返回已存储的 `ChecksumType` 元素。

## 缺陷与范围 {#origin}

对 `@cbornet` 报告的 [#31](https://github.com/pgsty/silo/issues/31) 的调查拆出了两个独立缺陷。CRC32 分片上传完成阶段的数据计算路径已由提交 `c8590413f` 与 `3e14733f1` 修复。但在分片上传成功完成后，虽然底层对象元数据保存了校验和类型且 `HeadObject` 与 `GetObject` 均可正常返回该字段，`CompleteMultipartUpload` 的 XML 响应却遗漏了 `ChecksumType`。这导致 S3 SDK 调用方在完成响应中收到了有效的校验和摘要，却拿不到对应的 `ChecksumType`。

这一遗漏虽然不会损坏已存储的对象数据，却使客户端无法仅凭完成响应区分整对象校验和（`FULL_OBJECT`）与分片组合校验和（`COMPOSITE`）。对于同一种校验和算法，两种模式生成的 Base64 摘要长度完全相同，下游校验方无法仅凭摘要字符串判断应当复现哪一种计算方式。

## 响应契约 {#contract}

| 已存储的校验和状态 | `CompleteMultipartUpload` 响应 |
| --- | --- |
| 整对象校验和 | `ChecksumType=FULL_OBJECT` 及对应算法摘要元素 |
| 分片组合校验和 | `ChecksumType=COMPOSITE` 及对应算法摘要元素 |
| 无附加校验和 | 不输出 `ChecksumType` 元素，也不伪造校验和 |

[S3 `CompleteMultipartUpload` API 规范](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)定义了 `FULL_OBJECT` 与 `COMPOSITE` 两种校验和类型。对象 `ETag` 是独立的响应字段，不能替代附加 S3 校验和元数据。

## 实现与证据 {#implementation}

生产代码在 `CompleteMultipartUploadResponse` 结构体中新增带 `xml:"ChecksumType,omitempty"` 标签的 `ChecksumType string` 字段，并在解码已存储的校验和元数据后将 `cs[xhttp.AmzChecksumType]` 填入响应。响应生成器直接复用 `HeadObject` 与 `GetObject` 所读取的同一份已存储状态，既不会重新扫描对象内容，也不会根据分片数量猜测校验和类型。

[合并提交（`a96116b12`）](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee)包含了针对整对象、分片组合与无校验和三种完成响应的单元测试。

## 兼容性与相邻改动 {#impact}

忽略未知 XML 元素的客户端保持完全兼容，而检查 `ChecksumType` 的 SDK（如 `silo-go` [`bc3b35f97`](https://github.com/pgsty/silo-go/commit/bc3b35f973d981920cd83e8b5d2b30a45ec1b6dc)）则能在分片完成响应中直接获取已存储的类型值。本次修复未引入新算法、未修改磁盘元数据格式，也无需迁移存量对象。

另外两项相邻的分片校验和修复同样随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布：[UploadPart 校验和推断修复](/zh/blog/design/uploadpart-checksum/)与 [CompleteMultipartUpload 校验和错误映射](/zh/blog/design/complete-multipart-checksum-errors/)（其中 `CRC64NVME + COMPOSITE` 会被显式拒绝，不再静默规范化）。
