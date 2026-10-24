---
title: "联邦 CopyObject：保持目标对象契约"
linkTitle: "联邦 CopyObject：保持目标对象契约"
date: 2026-09-16
lastmod: 2026-09-17
author: "冯若航"
summary: >
  Server 20260916（PR #157、#159、#163、#177、#179）修复了旧版 etcd 存储桶联邦 CopyObject 路径：转发源对象逻辑字节、保持目标端加密与 Object Lock 规则、校验整对象校验和，并返回目标端实际提交的版本身份。
tags: [设计, S3, 运维]
weight: 7
draft: false
url: "/zh/blog/design/federated-copy-object/"
---

[Server 20260916](/zh/blog/release/silo-20260916/) 通过 [PR #157](https://github.com/pgsty/silo/pull/157)、[PR #159](https://github.com/pgsty/silo/pull/159)、[PR #163](https://github.com/pgsty/silo/pull/163)、[PR #177](https://github.com/pgsty/silo/pull/177) 与 [PR #179](https://github.com/pgsty/silo/pull/179) 修复了旧版 etcd 存储桶联邦（bucket federation）的 `CopyObject` 转发路径。当代理节点将跨集群复制作为远端 `PutObject` 转发到目标集群时，代理节点流式读取并发送源对象的逻辑字节，由目标端执行加密与 Object Lock 规则，校验完整对象校验和，并原样返回目标端实际提交的写入元数据。

## 转发一次逻辑字节，由目标端执行加密 {#bytes}

代理节点在本地按需解密并解压源对象，读取其逻辑字节流，并在向目标集群发起的 `PutObject` 请求中声明逻辑字节长度：

- **禁止双重转换：** 代理节点绝不在本地预先加密或压缩后再转发给远端重复处理。
- **SSE-C 与 SSE-KMS 边界：** 读取 SSE-C 源对象仍要求提供源客户密钥并使用安全传输。新对象的加密方式完全由客户端显式携带的目标 SSE 请求头或目标桶自身的默认加密配置决定；当客户端未指定加密头时，代理节点不会注入本地默认加密配置。SSE-KMS 上下文按标准 JSON 对象格式转发。
- **拒绝原始 SSE-C 副本复制：** 联邦路径在创建目标对象前以 `501 NotImplemented` 显式拒绝可信原始 SSE-C 副本的 `CopyObject` 请求。

## 校验和与元数据过滤规则 {#checksums}

普通转发写入按大小写不敏感规则剥离所有保留的内部元数据前缀，仅通过标准 S3 字段转发公开的用户元数据与对象标签。转发写入的校验和必须描述实际写入目标端的完整逻辑对象：

- **整对象校验和转换：** 当请求显式指定校验和算法，或源对象携带分段复合校验和（`COMPOSITE`）时，目标端必须生成并保存整对象校验和（`FULL_OBJECT`）。
- **流式 trailer 与请求头传递：** 非空对象流通过 `x-amz-trailer` 传递尾部校验和并由目标端验证；零字节对象无流式尾部，改用普通 `x-amz-checksum-*` 请求头；源对象已有的 `FULL_OBJECT` 校验和可直接作为普通校验和请求头转发给目标端验证。
- **远端响应校验：** 若远端 `PutObject` 响应缺失必需的校验和、格式非法或仍带有分段 `-N` 后缀，代理节点直接报错，不会将其包装成合法的整对象结果。由于报错时远端写入可能已经落盘，针对版本化桶重试前应先检查目标端实际生成的版本。

## Object Lock 头部类型与时间精度 {#lock}

代理节点通过类型化的 `LegalHold` 客户端选项转发法律保留状态，确保请求发送标准的 `x-amz-object-lock-legal-hold` 请求头，而非误转为 `x-amz-meta-*` 用户元数据。对象保留期（Retention）时间戳完整保留亚秒级精度，不再截断为整秒。目标端继续独立执行权限认证与桶级 Object Lock 校验。

## 返回实际提交的目标写入身份 {#result}

`CopyObjectResult` XML 响应与 `ObjectCreated:Copy` 事件均直接采用目标端本次写入返回的键名、逻辑大小、ETag、精确 `VersionID` 与修改时间。代理节点既不在本地伪造修改时间，也不通过后续不带版本号的 `HEAD` 请求二次读取（避免并发写入下读到其他版本的元数据）。当请求指定了源 `versionId` 时，源版本响应头继续标识所选中的源版本。

## 源码与测试索引 {#verification}

- **实现源码：** [`cmd/object-handlers.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers.go)、[`cmd/object-handlers-common.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/object-handlers-common.go)（[PR #157](https://github.com/pgsty/silo/pull/157)、[PR #159](https://github.com/pgsty/silo/pull/159)、[PR #163](https://github.com/pgsty/silo/pull/163)、[PR #177](https://github.com/pgsty/silo/pull/177)、[PR #179](https://github.com/pgsty/silo/pull/179)）
- **回归测试：** `cmd/object-copy-federation*_test.go`、`cmd/object-federation-time_test.go`
- **关联记录：** [SSE-C 副本完整性](/zh/blog/design/ssec-replica-integrity/) · [Object Lock 复制排序](/zh/blog/design/object-lock-replication-ordering/) · [组件版本矩阵](/zh/compatibility/versions/)
