---
title: "SSE-C 副本完整性"
linkTitle: "SSE-C 副本完整性"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: "原始密文、逻辑分段大小、重传与压缩排除共同构成副本契约。"
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/zh/blog/design/ssec-replica-integrity/"
---

**2026-09-16 源码状态：**[#122](https://github.com/pgsty/silo/pull/122)、[#123](https://github.com/pgsty/silo/pull/123)、[#124](https://github.com/pgsty/silo/pull/124)、[#126](https://github.com/pgsty/silo/pull/126) 和 [#134](https://github.com/pgsty/silo/pull/134) 已在 main，但不在已发布的 Server 20260903 中。此前零字节/属性读取认证与目标密钥 checksum 响应修复已随 20260903 发布；不能把所有 SSE-C 修复当作同一次发布。

## 密文与信任 {#ciphertext}

普通 SSE-C 请求提供客户密钥，操作明文。经过授权的副本传输可以携带原始密文和保留原对象所需的密封对象密钥元数据。目标必须原样存储这些字节，再加密一次会产生不可读的双重加密对象。内部标记本身不是授权：仍需精确复制标记和要求的复制权限。

该路径不会泄露客户密钥，也不会允许普通无密钥读取。普通 GET/HEAD 与 `GetObjectAttributes` 保留各自密钥/权限检查。[联邦原始 SSE-C 副本 COPY](/blog/design/federated-copy-object/#bytes) 明确不支持。

## 分段大小与校验和 {#multipart}

加密分段大小与逻辑明文分段大小不同。副本多段记录必须保留每段实际逻辑大小，使覆盖后的 `partNumber` 读取、范围读取和 `GetObjectAttributes` 与源一致。Checksum 必须保留正确加密上下文和逻辑含义；对象已用另一把目标密钥提交后，不能仍用源密钥解密响应 checksum。

普通 SSE-C 密钥轮换在当前 main 中，只要显式请求 checksum 算法，就走完整重写，即使算法与原值相同。多段源成为单段目标，ETag 可能变化，复制重传对象字节。不带该请求且满足元数据原位更新条件时，保留原 checksum 状态，包括缺失状态。详见[操作步骤](/administration/server-side-encryption/server-side-encryption-sse-c/#rotate-the-sse-c-key-of-an-object)。

## 重传与 Object Lock {#retransmission}

目标无密钥 HEAD 可能把已存在的 SSE-C 对象报告为不可访问，而不是不存在。发送方须区分它与 `NoSuchKey`，不能假设普通元数据 COPY 能修好副本。已存在 SSE-C 副本走对象重传。旧副本状态无法解码时，可通过修复后的重传路径替换，同时保留目标更新的 Object Lock 状态，并正确排序删除时间戳。

升级 Server 不会自动证明旧副本已修好。应使用批准的密钥访问流程重新读取精确源/副本版本，比较逻辑字节和分段边界，另行检查保留期及 legal hold。不能仅凭元数据 HEAD 成功推断完整性。

## 压缩与历史对象 {#compression}

当前 main 排除所有新 SSE-C 写入的压缩，包括普通 PUT、多段初始化、COPY 和 Snowball。SSE-S3/SSE-KMS 仍服从加密压缩选项。这避免生成传送密文却缺少所需压缩元数据的副本格式。

历史压缩 SSE-C 对象不会自动重写。保留密钥和精确版本身份，清点影响范围并演练受支持的重写/恢复路径。该变更是预防措施，不是后台迁移，也不保证任意旧密文都能恢复。

## 验证边界 {#verification}

[压缩判定](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-api-utils.go)、`replication-trust-ssec-replica_test.go`、`erasure-multipart-ssec-replica_test.go`、`replication-ssec-retransmit_test.go` 和 `compression-ssec_test.go` 保留相关源码及回归契约。测试包含错误密钥/未授权对照、多段字节比较和重传情况，不能替代部署的历史状态清点。

相关内容见 [Object Lock 排序](/blog/design/object-lock-replication-ordering/)、[多池一致性](/blog/design/multi-pool-object-consistency/)及[副本恢复](/operations/replication/replica-metadata-audit/)。依赖组合行为前须升级所有参与 Server。
