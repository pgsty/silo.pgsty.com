---
title: "两把 SSE-C 密钥，一份 CopyObject 响应"
linkTitle: "CopyObject SSE-C Checksum"
date: 2026-08-28
lastmod: 2026-09-02
author: "冯若航"
summary: >
  CopyObject 可以用一把 SSE-C 密钥读取源对象，再用另一把密钥写入目标对象。SILO 会正确保存目标 checksum，却在生成响应时误用源密钥解密，导致 checksum 字段静默缺失。本文记录密钥上下文边界、纯响应修复、单次解密设计和回归矩阵。
tags: [设计, S3, SSE-C, Checksum, 兼容性]
weight: 17
draft: false
url: "/zh/blog/design/copyobject-ssec-checksum-response/"
---

本文记录 SILO 提交 `e73436c99` 中的 CopyObject SSE-C checksum 响应修复。

> **截至 2026-08-28 的状态：** 实现、加密与换钥测试、完整服务器套件、race、静态检查、构建和 Fable Max 独立验收均已完成。该提交已于 2026-08-29 以 `e73436c99` 合并进 `main`；tag、软件包、镜像、部署和生产验证仍是独立门槛。<br>
> **范围：** 只处理目标对象提交成功后的 CopyObject XML 与 HTTP 响应。存储对象字节、checksum metadata、加密格式、源对象解密、federation、replication 与历史对象均不改变。<br>
> **安全属性：** source SSE-C header 只能解密源状态；destination SSE-C header 只能解释已提交的目标状态。

## 太长不看（TL;DR） {#tldr}

一次 SSE-C 复制可以同时使用两把相互独立的密钥：

| 角色 | 请求头 | 用途 |
| --- | --- | --- |
| 源对象 | `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` | 解密源对象 |
| 目标对象 | `X-Amz-Server-Side-Encryption-Customer-*` | 加密并解释已提交目标对象 |

SILO 会用目标密钥正确写入目标对象。但提交完成后，XML generator 与通用 PUT 成功响应 helper 都收到了完整 CopyObject request。Checksum metadata decrypter 在 copy-source SSE-C header 存在时会优先使用它：读取源对象时这个优先级是正确的，解释已提交目标对象时却是错误的。

源 key A、目标 key B 时，旧流程是：

```text
源对象 body       --用 A 解密--> 逻辑字节
逻辑字节          --用 B 加密--> 已提交目标对象
目标 checksum     --用 B 密封--> 已存 checksum metadata
响应 decoder      --误用 A----> key mismatch，省略 checksum
```

对象与持久化 checksum 都是正确的；缺陷只发生在成功响应上。最终修复复制请求头、删除恰好三个 copy-source SSE-C customer header，以此形成目标响应视图；随后只解密一次目标 checksum，并把同一个 map 同时用于 XML 和 HTTP response header。

## 可观察故障 {#failure}

触发条件是目标对象带 checksum，并且源/目标使用不同 SSE-C 上下文。代表性请求包含：

```text
x-amz-copy-source: /bucket/source
x-amz-copy-source-server-side-encryption-customer-algorithm: AES256
x-amz-copy-source-server-side-encryption-customer-key: <key A>
x-amz-copy-source-server-side-encryption-customer-key-md5: <md5 A>
x-amz-server-side-encryption-customer-algorithm: AES256
x-amz-server-side-encryption-customer-key: <key B>
x-amz-server-side-encryption-customer-key-md5: <md5 B>
x-amz-checksum-algorithm: CRC32
```

修复前：

- CopyObject 返回 HTTP 200；
- 用 key B 读取目标对象得到正确 body；
- 用 B 解密的持久化 checksum 与逻辑字节匹配；
- CopyObject XML 与 HTTP response 却没有 CRC32 和 `ChecksumType`。

所以这是 response contract 缺陷，不是对象数据已经损坏的证据。

同样的歧义也出现在同对象 SSE-C 换钥。Metadata 已经用 B 重新密封后，请求中仍带着表示旧源对象的 copy-source key A；响应描述的是换钥后的对象，因此必须使用 B。

## 为什么不能修改全局 decrypter {#source-boundary}

Metadata decrypter 的 source 优先级本身没有错。CopyObject 在更早阶段需要读取源 checksum metadata，决定是保留算法、把 composite 重算成 full-object，还是为无 checksum 源增加默认 CRC64NVME。SSE-C 源对象的这份 metadata 由源对象密钥保护，必须使用 copy-source header。

如果把全局优先级改成“目标 SSE-C 优先”，最终响应会恢复，源 checksum 解释却会被破坏。安全边界必须按对象和时间区分：

```text
提交前：完整请求头，源对象上下文
提交后：仅目标 SSE-C 头，目标对象上下文
```

最终修复只作用于提交后的响应边界。

## 最终实现 {#implementation}

### 目标响应视图 {#destination-view}

Handler clone 请求头并精确删除：

- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Algorithm`；
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key`；
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key-MD5`。

普通目标 SSE-C header 保留。SSE-S3 与 SSE-KMS 的目标 metadata 不需要 customer key，继续走原有路径。

### 解密一次，投影两次 {#single-decrypt}

修复前，CopyObject 构造 XML 时调用一次 `decryptChecksums`，写成功 response header 时又调用一次。对于 SSE-S3 或 SSE-KMS，这可能重复执行 KMS unseal。

修复后：

```text
已提交 ObjectInfo
  -> 使用目标 header 调用一次 decryptChecksums
  -> 填充 CopyObjectResult XML
  -> 填充 x-amz-checksum-* 与 x-amz-checksum-type header
```

通用 `setPutObjHeaders` wrapper 仍服务于 PutObject、CompleteMultipartUpload 与 DeleteObject；CopyObject 调用一个接收已解密 checksum map 的窄 helper。ETag、VersionID、delete marker、lifecycle prediction 与 checksum header 仍共享同一份实现。

## 回归矩阵 {#tests}

测试覆盖：

- 明文源到 SSE-C 目标；
- 压缩与未压缩 SSE-C 目标；
- SSE-C 源 key A 到目标 key B；
- CopyObject XML 与 HTTP header 中的 checksum value/type；
- 用目标 key B 解密持久化 checksum；
- 用 B 读取目标 body；
- 同对象从 A 换钥到 B；
- 换钥后的 checksum 响应；
- SSE-S3 源/目标组合；
- API test harness 使用的全部对象层后端。

最终组合 tree 通过了定向加密测试、完整 `cmd`/`internal` 套件、项目 tagged test 配置、全量 `go test -race ./...`、vet、lint、生成物检查、rebrand 守卫和本地构建。Fable Max 镜像评审没有发现 P0–P2，并独立确认：源对象解密仍接收完整请求，目标响应解密只接收过滤后的视图。

## 兼容性与运维影响 {#impact}

- **成功响应：** 已提交目标带 checksum 时，过去缺失的字段现在会出现。
- **存储对象：** 不重写数据，不修改 metadata format 或 encryption format，不需要迁移。
- **既有对象：** 不受影响；缺陷只存在于一次性的成功响应中。
- **客户端：** 请求无需改变；已经同时提供源/目标 SSE-C key 的客户端会得到更完整的 S3 兼容结果。
- **性能：** metadata checksum 从解密两次降为一次；不增加对象读取或 hash pass。
- **滚动升级：** 旧节点可能省略字段，新节点会返回；存储对象仍互相可读。
- **回滚：** 只恢复响应省略，不会损坏修复版本期间创建的对象。
- **安全：** 不向日志或错误响应增加 key/digest；只返回该成功写入本来就授权可见的 checksum。

本修复不处理另行保留的 legacy federation CopyObject 分支，也不审计或修改历史压缩对象 checksum；它们具有不同的数据与运维边界。

## 结论 {#conclusion}

CopyObject 是一条请求，但涉及两个对象身份。提交后继续复用完整请求，会抹掉这种区别：描述目标 metadata 时，源 key 仍能遮蔽目标 key。真正耐久的修复不是新增加密机制，而是建立明确上下文边界，然后只做一次解密、两次如实响应投影。
