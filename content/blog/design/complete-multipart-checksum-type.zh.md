---
title: "为什么 CompleteMultipartUpload 必须返回 ChecksumType：PR #57 评审记录"
linkTitle: "CompleteMultipart ChecksumType"
date: 2026-08-25
lastmod: 2026-09-16
author: "冯若航"
summary: >
  完成响应返回存储的校验和类型；已进入 Server 20260903。本文说明范围、证据及相邻校验变化。
tags: [设计, S3, 兼容性, Checksum]
weight: 20
draft: false
url: "/zh/blog/design/complete-multipart-checksum-type/"
---

Shooks（@Dansyuqri）贡献的 [PR #57](https://github.com/pgsty/silo/pull/57) 修复了
[#47](https://github.com/pgsty/silo/issues/47)，已包含在 [Server 20260903](/zh/blog/release/silo-20260903/) 中。
本文记录响应契约；具体生产部署是否包含修复，仍取决于实际运行的制品与安装。

## 缺陷与范围 {#origin}

对 @cbornet 报告的 [#31](https://github.com/pgsty/silo/issues/31) 的调查拆出了两个问题。
CRC32 分段上传完成的数据路径由 `c8590413f` 与 `3e14733f1` 修复。
成功完成后，对象保存了校验和类型，HEAD 也可返回，但完成响应的 XML 丢弃了这个类型，
导致 SDK 获得有效校验和值，却没有 `ChecksumType`。

这不会破坏存储的数据，但使客户端无法直接区分整对象校验和与组合校验和。
仅凭 Base64 编码，消费者不能确定应该复现哪一种计算。

## 响应契约 {#contract}

| 存储状态 | 完成响应 |
| --- | --- |
| 整对象校验和 | `ChecksumType=FULL_OBJECT` 及对应算法值 |
| 分段组合校验和 | `ChecksumType=COMPOSITE` 及对应算法值 |
| 没有额外校验和 | 不输出 `ChecksumType` 元素，也不伪造校验和 |

[S3 完成上传 API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CompleteMultipartUpload.html)定义了这两种类型。
ETag 是独立字段，不能替代额外的 S3 校验和。

## 实现与证据 {#implementation}

生产代码在 `CompleteMultipartUploadResponse` 中添加带 `xml:"ChecksumType,omitempty"` 的
`ChecksumType string` 字段，并在解码存储校验和元数据后赋值为 `cs[xhttp.AmzChecksumType]`。
生成器复用其他校验和 API 使用的同一份状态，不重新计算内容，也不根据分片数量推断类型。

[合并提交](https://github.com/pgsty/silo/commit/a96116b128bbf2aa42f85eafbf75eb6636cd36ee)包含整对象、组合与无校验和三种响应测试。
原改动还在当时的 rebrand 清单登记了导出字段；该清单的导出符号部分随后由 `bc3b35f97` 删除，不能视为当前公开 API 兼容性保证。

## 兼容性与相邻改动 {#impact}

忽略未知 XML 元素的客户端继续兼容。本修复没有增加算法、修改存储元数据格式、迁移对象或绕过校验。
[UploadPart 修复](/zh/blog/design/uploadpart-checksum/)与[完成时校验](/zh/blog/design/complete-multipart-checksum-errors/)
属于独立改动，也已进入 Server 20260903。其中 `CRC64NVME + COMPOSITE` 会被拒绝，不再静默规范化。

<span id="algorithm-scope"></span>
<span id="baseline"></span>
<span id="before"></span>
<span id="conclusion"></span>
<span id="decision"></span>
<span id="evaluation"></span>
<span id="field"></span>
<span id="mapping"></span>
<span id="merge-sequence"></span>
<span id="notes"></span>
<span id="review"></span>
<span id="strengths"></span>
<span id="tests"></span>
<span id="tldr"></span>
<span id="why-it-works"></span>
