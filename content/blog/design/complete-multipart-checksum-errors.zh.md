---
title: "BadDigest、InvalidRequest 与 CompleteMultipartUpload 校验和契约"
linkTitle: "分片完成校验和错误"
date: 2026-08-27
lastmod: 2026-09-16
author: "冯若航"
summary: >
  完成上传依据已存储的类型校验并返回操作专用错误。Server 20260903 已拒绝 CRC64NVME 与 COMPOSITE；流式后续修复另行记录。
tags: [设计, S3, 兼容性, 校验和]
weight: 31
draft: false
url: "/zh/blog/design/complete-multipart-checksum-errors/"
---

[#48](https://github.com/pgsty/silo/issues/48) 与 [#50](https://github.com/pgsty/silo/issues/50) 的修复
已包含在 [Server 20260903](/zh/blog/release/silo-20260903/) 中。
本文取代八月提案中“暂时保持 CRC64NVME 规范化”的结论。

## 为什么必须在完成时校验 {#problem}

初始化上传时选择算法和对象校验和类型，各分片保存其校验和值。
完成请求必须依据已存储的契约校验最终值与显式类型断言，不能因为基础算法相同就将 `COMPOSITE` 改为 `FULL_OBJECT`，
也不能通过省略最终摘要绕过类型断言。

修复区分省略类型与显式类型，只规范化内部表示标志，并采用操作专用错误类型，保持 UploadPart 与全局校验和错误映射不变。

## 当前错误契约 {#tests}

下列失败均返回 HTTP 400，不会提交新的已完成对象。

| 请求条件 | S3 错误 |
| --- | --- |
| 整对象或组合对象摘要错误 | `BadDigest` |
| 显式有效类型与初始化类型不同，包括仅提供类型的断言 | `BadDigest` |
| 未知或小写类型 token | `InvalidArgument` |
| 完成时算法不同于初始化算法 | `InvalidArgument` |
| 缺少组合校验和所需的分片值 | `InvalidRequest`，指出算法与分片 |
| 初始化时 CRC64NVME 配合 COMPOSITE | `InvalidArgument` |
| 完成时 CRC64NVME 值与 COMPOSITE 在解析阶段被拒绝 | `InvalidArgument` |
| CRC64NVME FULL_OBJECT 上传在完成时仅断言 COMPOSITE | `BadDigest` |
| UploadPart 的客户端校验和错误 | 保留 `XAmzContentChecksumMismatch` |

`FULL_OBJECT` 可以省略分片校验和，但仍校验已提供的值。允许匹配的仅类型断言。
省略可选类型不等于断言 `COMPOSITE`。SHA1/SHA256 配合 `FULL_OBJECT` 会在算法/类型解析阶段被拒绝，不会进入存储类型比较。

## CRC64NVME 决策与源码证据 {#issue-50}

最初评审因等待证据而推迟 #50，这是历史决策，不是当前契约。
[PR #93](https://github.com/pgsty/silo/pull/93) 在 header 与 trailer 路径拒绝非法算法/类型组合，
[PR #96](https://github.com/pgsty/silo/pull/96) 则移除完成阶段的规范化，两者都早于 20260903 tag。
完成请求可在解析阶段或存储类型比较阶段失败，因此存在上表中两种不同错误码。

最初错误映射位于 [PR #74](https://github.com/pgsty/silo/pull/74)，显式类型后续修复 `7e079ff05` 经
[PR #85](https://github.com/pgsty/silo/pull/85) 合入。
当前[处理器测试](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-multipart-fullobject_test.go)
覆盖整对象与组合不匹配、仅类型断言、非法 token 及 CRC64NVME 两个拒绝阶段。
这是已提交的回归覆盖，不表示本次文档修改重新运行了所有 Server 测试。

## 独立的流式校验和后续修复 {#streaming}

[PR #143](https://github.com/pgsty/silo/pull/143) 跟进 @cbornet 报告的
[#107](https://github.com/pgsty/silo/issues/107)，处理 AWS Java SDK v2 使用的路径：`aws-chunked` 请求通过
`x-amz-trailer` 声明校验和，却在 header 中提供其值。它也拒绝非法的 header 校验和值，避免丢弃校验。
此后续修复已在 main，**不在 Server 20260903 中**，与完成错误映射是独立变化。

## 兼容性与剩余边界 {#impact}

检查错误码的客户端会看到摘要或类型失败变为 `BadDigest`，缺少组合分片值变为 `InvalidRequest`。
成功的无校验和上传与 ETag 语义不变，无需迁移元数据。

仍有较窄的差异：初始化未记录校验和却在完成时提供最终摘要，会返回 `BadDigest`；组合分片数与值不匹配使用相同描述；
整对象校验和的 `-N` 后缀本身不作为分片数验证。这些是已记录的观察，不表示已分别建立公开 issue，也不代表完整 AWS 一致性。

<span id="conclusion"></span>
<span id="contract"></span>
<span id="design"></span>
<span id="evidence"></span>
<span id="gates"></span>
<span id="independent-review"></span>
<span id="issue-50-probe"></span>
<span id="missing-part"></span>
<span id="operation-scoped"></span>
<span id="precise-missing"></span>
<span id="scope"></span>
<span id="symmetric-validation"></span>
<span id="tldr"></span>
<span id="type-mismatch"></span>
<span id="type-only-follow-up"></span>
<span id="upstream"></span>
<span id="value-mismatch"></span>
