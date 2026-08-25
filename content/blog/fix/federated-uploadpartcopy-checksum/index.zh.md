(B[m---
title: "修复 Federation UploadPartCopy 校验和响应"
linkTitle: "Federation UploadPartCopy 校验和"
date: 2026-08-24
author: "Ruohang Feng"
description: "Silo 如何在不改变普通 UploadPart 响应的前提下，让旧式 etcd federation 返回远端本次 part 写入的精确校验和，以及哪些版本必须协同升级。"
tags: [Fix, silo, S3, Checksum]
weight: 10
draft: true
url: "/zh/blog/fix/federated-uploadpartcopy-checksum/"
---

> **发布状态：** 本文仍是草稿。它描述 [Silo #64](https://github.com/pgsty/silo/issues/64) 的修复，但不表示包含该修复的版本已经发布。

旧式 etcd federation 处理跨部署的 `UploadPartCopy` 时，会在源端读取对象，再把复制出的字节作为普通 `UploadPart` 发送到目标部署。[#46](https://github.com/pgsty/silo/issues/46) 增加服务器端 checksum fallback 后，这个转换暴露出一个响应缺口：目标端已经计算并持久化了缺失的 part checksum，但普通 `UploadPart` 按协议不会返回请求中没有提供的 checksum；代理因此拿不到应写入 `CopyPartResult` 的值。

修复不会改变外部 S3 契约。现有 federation 客户端已经用 minio-go application token `minio-federated/<version>` 标识远端请求。目标端成功提交该请求后，会从同一个内部 `PartInfo` 返回非空 checksum 字段；响应 ETag 也来自这次写入。普通 `UploadPart` 调用者仍然只有在请求中提供 checksum 时才会收到 checksum 响应。

这个 application token 只是响应形状提示，不是授权边界。服务端不会信任 `User-Agent` 来决定访问权限、对象可见性或 checksum 校验。主动使用该 token 的调用者最多只能得到自己已经获准上传的数据的 checksum。

## 为什么直接返回写入结果 {#direct-response}

代理不会在写入后调用 `ListParts` 恢复 checksum。额外查询不仅需要新的权限和网络往返，还可能扫描大量 part metadata，并与另一个覆盖相同 part number 的写入发生竞争。直接返回本次已完成写入的 checksum，能让 ETag 与 checksum 绑定在同一个结果上，也不增加存储读取。

响应只包含实际存在的 `x-amz-checksum-crc32`、`x-amz-checksum-crc32c`、`x-amz-checksum-sha1`、`x-amz-checksum-sha256` 或 `x-amz-checksum-crc64nvme`。`UploadPart` 响应不会新增 `x-amz-checksum-type`。

## 升级兼容性 {#upgrade-compatibility}

应把本修复视为一次 federation 协同升级：

| 代理 / 源部署 | 目标部署 | 结果 |
|:--|:--|:--|
| 包含 #46 的 `CopyPartResult` checksum 映射 | 同时包含 #46 的计算修复与 #64 的响应修复 | `FULL_OBJECT` 与 `COMPOSITE` 的 `UploadPartCopy` 都能返回 checksum |
| 包含 #46 映射 | 包含 #46、但没有 #64 | 远端 part 写入成功并持久化 checksum，但 federation `CopyPartResult` 仍可能没有 checksum |
| 任意版本 | 早于 #46 | 目标端可能因为转发请求没有 checksum 而拒绝 checksum-enabled part |
| 早于 #46 映射 | 包含 #64 | 目标端可以返回值，但旧代理不保证把它暴露到 `CopyPartResult` |

在依赖 federated `UploadPartCopy` checksum 响应之前，请升级所有可能充当源端代理或目标端的部署。混合版本继续保持旧行为；本修复不声称建立了新的跨版本 federation 协议。

## 验证范围 {#verification}

回归测试覆盖 `CRC32` + `FULL_OBJECT`、`SHA256` + `COMPOSITE`、精确与相似 application token、真实 minio-go `Core.PutObjectPart` 响应解析，以及并发覆盖同一个 part number。原有“普通 `UploadPart` 未提供请求 checksum 时不返回服务器计算值”的断言也继续保留。

本次只修复 checksum 响应。旧式 federation 路径中独立存在的零值 `LastModified` 响应问题不在此次修改范围内。
