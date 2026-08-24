---
title: "CopyObject Checksum 必须覆盖逻辑对象字节"
date: 2026-08-24
lastmod: 2026-08-24
author: "冯若航"
summary: >
  目标端启用压缩时，SILO 可能把 S2 存储流的 checksum 当成 CopyObject 逻辑对象 checksum 持久化。本文记录明文 reader 不变量、验证边界、独立后续修复与旧对象处理方法。
tags: [设计, S3, 兼容性, Checksum]
weight: 10
draft: false
url: "/zh/blog/design/copyobject-checksum/"
---

本文是 [SILO #63](https://github.com/pgsty/silo/issues/63) 的设计与验证归档。

**状态：** checksum 数据域修复已通过 [PR #66](https://github.com/pgsty/silo/pull/66) 合并；公开发布待完成。  
**相关修复：** metadata-only transform state [#67](https://github.com/pgsty/silo/issues/67) 已通过 [PR #69](https://github.com/pgsty/silo/pull/69) 合并，CopyObjectResult checksum 字段 [#68](https://github.com/pgsty/silo/issues/68) 已通过 [PR #70](https://github.com/pgsty/silo/pull/70) 合并；公开发布仍待完成。
**上游客户端：** [minio-go #2295](https://github.com/minio/minio-go/pull/2295)。  
**发布边界：** 合并不代表公开 release、软件包或容器镜像已经包含修复。

## 缺陷本质 {#defect}

CopyObject 先把源对象读成逻辑数据，再按目标配置压缩并加密存储流。旧处理器把 server-side checksum 挂在了已经代表压缩字节的 reader 上：

    逻辑对象 -> S2 压缩 -> checksum -> 可选加密 -> 存储

digest 在数学上有效，却覆盖了错误的数据域。客户端下载对象后对逻辑字节独立计算，结果自然不同。API 级复现是确定性的：

    修复前持久化 CRC32：hN7ytg==
    逻辑对象 CRC32：      1WxbLg==

当前基线实现的 CRC32、CRC32C、CRC64NVME、SHA1、SHA256 都会受影响。压缩叠加加密时，S2 加密流填充包含随机值，错误 checksum 甚至会变成非确定值。

## 采用的不变量 {#invariant}

逻辑 checksum reader 现在与存储变换 reader 分离：

    逻辑对象
        -> server-side checksum
        -> 可选 S2 压缩
        -> 存储流 hash
        -> 可选服务端加密
        -> 纠删码与提交

处理器必须在压缩 goroutine 启动前安装 hasher。即使压缩或加密替换活动存储 reader，PutObjReader 仍保存逻辑 reader。读到 EOF 后，对象层要求 checksum 存在、有效并与预期 base algorithm 一致，随后才允许提交 metadata。

该设计直接复用 multipart checksum 的 checksumReader 契约，不创建第二套抽象，不重读对象，也不改变盘上格式。

## 验证边界 {#verification}

永久 API 测试覆盖五种算法与默认 CRC64NVME；不压缩、压缩、仅加密和压缩加密；SSE-C 与 SSE-S3；加密源和压缩源；版本化桶；full 与 multipart-composite 来源；原地复制；零长度、压缩阈值与带索引 S2 流；ETag、正文 round trip、HEAD/GET checksum mode，以及内部不变量失败。

同一条回归在未修复基线上失败，在修复树上通过。合并前还要求定向 race、随机顺序重复运行、全量 cmd、禁用 CGO 的 kqueue/dev CI 形态、lint、vet、交叉编译、兼容性 guard 与远端 CI 全部通过。

## 刻意拆开的邻接缺陷 {#adjacent}

对抗审查又发现两个继承缺陷：

1. metadata/reference-only self-copy 可能在没有重写引用数据时改变压缩标记；版本化 SSE-C 密钥轮换还可能落入非法重写。该问题独立收敛在 [#67](https://github.com/pgsty/silo/issues/67)。
2. 目标 checksum 已提交后，成功的 CopyObject XML 仍不返回 checksum 元素。服务端由 [#68](https://github.com/pgsty/silo/issues/68) 跟踪；minio-go 还会丢弃字段，对应 [#2295](https://github.com/minio/minio-go/pull/2295)。

旧 federation 的 UploadPartCopy checksum 恢复属于另一个 API，继续由 [#64](https://github.com/pgsty/silo/issues/64) 跟踪。

归档的上游 minio/minio 仍保留原始 reader 放置方式。silo-pkg 不拥有该 reader 链。MCLI 在指定 --checksum 时会从 server-side copy 切换为下载再上传，SILO Console 只通过 minio-go 透传 CopyObject，因此两者不需要复制一份服务端修复。

## 已存在对象 {#existing-objects}

修复只影响此后的 CopyObject，不会自动扫描或重写旧版本已经保存的 checksum metadata。

由 CopyObject 创建、当时目标 key 或内容类型命中压缩配置、并带有额外 S3 checksum 的对象值得核验。使用 checksum mode 取回对象与 checksum，再用同一算法独立计算下载后的逻辑字节并比较 Base64 值。

修复时可显式指定 checksum algorithm，把对象复制到新 key。也可以带 x-amz-metadata-directive: REPLACE 做原地复制，但这会重写对象：未版本化桶替换当前值，版本化桶创建新版本。批量处理前必须确认 retention、legal hold、metadata、tag、加密密钥、剩余空间和回滚要求。

SILO 不做自动在线回填，因为那意味着在没有显式 S3 操作的情况下读取并重写用户数据。
