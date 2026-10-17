---
title: "联邦 CopyObject：保持目标对象契约"
linkTitle: "联邦 CopyObject：保持目标对象契约"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: "旧 etcd 联邦须转发逻辑字节，保留目标加密及 Object Lock 规则，并返回实际提交写入的身份。"
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/zh/blog/design/federated-copy-object/"
---

> **2026-09-17 发布更新：** 本文记录的联邦 CopyObject 修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；协调升级、可选功能启用条件和剩余限制仍按各节执行。下方带日期的源码状态与验证记录保留当时的范围。

**2026-09-16 源码状态：**本文记录 main 中 [#157](https://github.com/pgsty/silo/pull/157)、[#159](https://github.com/pgsty/silo/pull/159)、[#163](https://github.com/pgsty/silo/pull/163)、[#177](https://github.com/pgsty/silo/pull/177) 和 [#179](https://github.com/pgsty/silo/pull/179) 的 CopyObject 修复，Server 20260903 尚未包含。讨论对象是把复制作为 `PutObject` 转发到另一部署的**旧 etcd 存储桶联邦**路径，不是桶/站点复制调度器。

## 转发一次逻辑字节，由目标端加密 {#bytes}

代理读取源的逻辑字节，按需解密和解压，并向目标声明逻辑长度。不能先在本地加密/压缩，又要求远端再做一次。SSE-C 源读取仍需源密钥及安全传输。新对象由客户端显式 SSE 请求头或目标自身的默认加密规则决定存储方式；没有显式选择时，代理不能注入自己的默认值。SSE-KMS context 按预期的 JSON 对象形式转发。

联邦路径明确以 `501 NotImplemented` 拒绝可信原始 SSE-C 副本 CopyObject，并在创建目标前返回。仅附加复制标记不能让这个组合安全。普通的持密钥 SSE-C COPY 与专用副本路径是不同操作。

## 校验和与元数据规则 {#checksums}

普通转发写入应按大小写不敏感规则移除整个保留内部元数据前缀类别。公共元数据与标签通过支持的字段传递，而非内部存储编码。Checksum 必须描述实际写入的逻辑完整对象：

- 显式算法或多段复合 checksum 源要求目标生成完整对象 checksum。
- 非空流使用客户端尾部 checksum，包括 `x-amz-trailer`，目标须读取并验证 trailer。
- 空对象用普通 checksum 请求头，因为没有承载摘要的流式尾部。
- 源已经保存的完整对象 checksum 可以作为普通请求头传给目标验证。
- 必需的远端 checksum 缺失、格式错误或带多段 `-N` 后缀时必须报错，不能冒充有效完整对象结果。

发现错误成功响应时，远端写入可能已经提交。随后返回错误不证明目标不存在；对版本化 COPY，应先检查实际写入版本再决定重试。

## Object Lock 不是用户元数据 {#lock}

通过类型化 `LegalHold` 选项传递 legal hold，使其成为 `x-amz-object-lock-legal-hold`，而不是 `x-amz-meta-*`。保留期时间戳应保持完整精度，转成整秒会削弱请求值。认证与目标 Object Lock 规则仍然适用。

## 返回实际提交的写入 {#result}

响应与 `ObjectCreated:Copy` 事件描述目标键、逻辑大小、ETag 和精确版本 ID。修改时间来自目标本次写入，不能由代理编造，也不能用后续不带版本的 HEAD 获取——那可能看到另一写入方的对象。内部写入时间响应绑定经过认证的联邦请求。显式选定源版本时，源版本响应头仍标识对应源版本。

## 证据与部署边界 {#verification}

源码见[处理器](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go)、[写入时间 transport](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers-common.go)，测试见 `object-copy-federation*_test.go`、`object-federation-time_test.go`。覆盖普通、空、多段、压缩和加密源，远端 checksum 失败，目标默认值、legal hold、响应身份和事件。这些组件测试不构成生产 etcd 联邦或任意 S3 兼容目标的验收。

按[组件矩阵](/compatibility/versions/)同时核对代理与目标构建。升级不会重写历史对象。相关设计见 [SSE-C 副本完整性](/blog/design/ssec-replica-integrity/)和 [Object Lock 排序](/blog/design/object-lock-replication-ordering/)。
