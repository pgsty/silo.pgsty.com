---
title: "两把 SSE-C 密钥，一份 CopyObject 响应"
linkTitle: "CopyObject SSE-C Checksum"
date: 2026-08-28
lastmod: 2026-09-16
author: "冯若航"
summary: >
  CopyObject 支持用一把 SSE-C 密钥读取源对象，再用另一把密钥写入目标对象。SILO 正确使用目标密钥加密保存了目标校验和，却在生成响应时误用源密钥解密，导致校验和字段静默缺失。
tags: [设计, S3, SSE-C, Checksum, 兼容性]
weight: 17
draft: false
url: "/zh/blog/design/copyobject-ssec-checksum-response/"
---

本文记录提交 `e73436c99`（已随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布）中的 `CopyObject` SSE-C 校验和响应修复。该修复仅作用于目标对象成功提交后的 `CopyObject` XML 与 HTTP 响应生成阶段；已存储的对象字节、校验和元数据、加密格式、源对象解密、联邦复制与站点复制均保持不变。

## 概览 {#tldr}

一次 SSE-C `CopyObject` 请求可以同时携带两套相互独立的客户端加密密钥：

| 角色 | 请求头 | 用途 |
| --- | --- | --- |
| 源对象 | `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` | 解密源对象及其已存储的元数据 |
| 目标对象 | `X-Amz-Server-Side-Encryption-Customer-*` | 加密并在提交后解释目标对象及其元数据 |

SILO 在写入阶段能够使用目标密钥正确加密目标对象并密封其校验和元数据。但在目标对象提交完成后，`CopyObjectResult` XML 生成器与通用的 PUT 成功响应头辅助函数都直接收到了完整的原始 `CopyObject` 请求头。由于校验和元数据解密函数 `decryptChecksums` 在检测到 `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` 请求头存在时会优先使用该请求头——这一优先级在读取源对象阶段是完全正确的——导致它在解释已提交的目标对象元数据时误用了源密钥。

当源密钥为 `A`、目标密钥为 `B` 时，旧流程表现为：

```text
源对象正文         --用 A 解密--> 逻辑明文字节
逻辑明文字节       --用 B 加密--> 已提交目标对象
目标对象校验和     --用 B 密封--> 已存储校验和元数据
响应解码器         --误用 A----> 密钥不匹配，静默省略校验和字段
```

落盘的目标对象与加密校验和元数据本身完全正确，缺陷仅出现在一次性的成功响应中。修复方案通过克隆请求头并剥离三个 `copy-source` SSE-C 请求头来构造目标响应视图，使用目标密钥 `B` 对目标校验和元数据只执行一次解密，并将得到的映射表同时复用于 `CopyObjectResult` XML 响应体与 HTTP 响应头。

## 可观察故障 {#failure}

当目标对象包含校验和且源、目标使用不同的 SSE-C 密钥上下文时，即可复现该故障：

```http
x-amz-copy-source: /bucket/source
x-amz-copy-source-server-side-encryption-customer-algorithm: AES256
x-amz-copy-source-server-side-encryption-customer-key: <key A>
x-amz-copy-source-server-side-encryption-customer-key-md5: <md5 A>
x-amz-server-side-encryption-customer-algorithm: AES256
x-amz-server-side-encryption-customer-key: <key B>
x-amz-server-side-encryption-customer-key-md5: <md5 B>
x-amz-checksum-algorithm: CRC32
```

在修复前：

- `CopyObject` 返回 HTTP 200；
- 使用密钥 `B` 对目标对象执行 `GetObject` 可读取正确的明文正文；
- 使用密钥 `B` 对目标对象执行 `HeadObject` 可正常解密并返回 `x-amz-checksum-crc32` 与 `x-amz-checksum-type`；
- 但 `CopyObject` 当次返回的 XML 响应体与 HTTP 响应头中却缺失了 `ChecksumCRC32` / `x-amz-checksum-crc32` 与 `ChecksumType` / `x-amz-checksum-type`。

同样的密钥遮蔽问题也会出现在同对象原地换钥（即将对象复制到自身并更换为新 SSE-C 密钥 `B`）场景中：尽管目标元数据已用新密钥 `B` 重新密封，请求中仍保留着代表旧源对象的 `copy-source` 密钥 `A`，导致换钥响应丢失校验和字段。

## 为什么不能修改全局解密器 {#source-boundary}

`decryptChecksums` 优先读取 `copy-source` SSE-C 请求头本身并非缺陷。在 `CopyObject` 的提交前阶段，服务端需要先检查源对象的校验和元数据，以决定是直接沿用源算法、将分片组合校验和重算为整对象校验和，还是为无校验和源对象补充默认的 `CRC64NVME` 校验和。对于 SSE-C 源对象，这份源元数据由源密钥保护，必须使用 `X-Amz-Copy-Source-Server-Side-Encryption-Customer-*` 请求头才能解密。

如果简单地将 `decryptChecksums` 的全局优先级反转为“目标 SSE-C 请求头优先”，虽然能修复提交后的响应，却会破坏提交前的源校验和解析。正确的安全边界必须按时间阶段与操作对象严格区分：

```text
提交前：完整请求头             -> 源对象 SSE-C 上下文
提交后：仅保留目标 SSE-C 请求头 -> 目标对象 SSE-C 上下文
```

## 实现设计 {#implementation}

### 目标响应请求头视图 {#destination-view}

在目标对象提交成功后，处理器克隆请求头映射并精确删除以下三个源端 SSE-C 请求头：

- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Algorithm`
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key`
- `X-Amz-Copy-Source-Server-Side-Encryption-Customer-Key-MD5`

常规的目标端 `X-Amz-Server-Side-Encryption-Customer-*` 请求头保持不变。`SSE-S3` 与 `SSE-KMS` 目标元数据不依赖客户端提供的密钥请求头，继续沿用原有路径。

### 解密一次，投影两次 {#single-decrypt}

修复前，`CopyObject` 在构造 `CopyObjectResult` XML 时调用一次 `decryptChecksums`，随后在 `setPutObjHeaders` 写入成功响应头时又调用一次。对于 `SSE-S3` 或 `SSE-KMS` 对象，这会导致重复执行主密钥或 KMS 解封操作。

修复后的流程只执行一次目标校验和解密，并将结果投影到两处输出：

```text
已提交的 ObjectInfo
  -> 使用目标请求头视图调用一次 decryptChecksums
  -> 填充 CopyObjectResult XML 字段
  -> 填充 x-amz-checksum-* 与 x-amz-checksum-type HTTP 响应头
```

通用的 `setPutObjHeaders` 包装函数仍继续服务于 `PutObject`、`CompleteMultipartUpload` 与 `DeleteObject`；`CopyObject` 则直接调用接收已解密校验和映射表的内部辅助函数，确保 ETag、`VersionID`、删除标记、生命周期预测与校验和响应头共享同一套逻辑。

## 回归测试矩阵 {#tests}

加密与 API 测试套件覆盖了以下组合：

- 明文源对象复制到 SSE-C 目标对象；
- 压缩与未压缩的 SSE-C 目标对象；
- SSE-C 源密钥 `A` 复制到 SSE-C 目标密钥 `B`；
- 同时校验 `CopyObjectResult` XML 与 HTTP 响应头中的校验和摘要及 `ChecksumType`；
- 验证持久化目标校验和可用密钥 `B` 解密且与目标正文匹配；
- 同对象从密钥 `A` 到密钥 `B` 的原地 SSE-C 换钥及换钥后的校验和响应；
- `SSE-S3` 源与目标组合在各纠删码后端上的表现。

## 兼容性与运维影响 {#impact}

- **`CopyObject` 成功响应：** 当已提交的目标对象包含校验和时，此前在跨密钥 SSE-C 复制中缺失的校验和值与 `ChecksumType` 现已在 XML 响应体和 HTTP 响应头中完整返回。
- **已存储对象：** 无需重写数据、无需修改元数据或加密格式，也无需数据迁移；存量对象的持久化校验和原本就是正确的。
- **性能开销：** 每次 `CopyObject` 响应的元数据校验和解密次数从两次减为一次，不增加任何对象数据读取或哈希计算开销。
- **滚动升级与回滚：** 滚动升级窗口内，新节点会返回完整校验和字段，旧节点可能省略该字段，但两端写入的对象数据完全互操作。

## 结论 {#conclusion}

在构造 `CopyObjectResult` XML 响应前对 `ObjectInfo` 执行元数据解密（`21870fa2e`），使 SSE-C 与 KMS 加密对象的 `CopyObject` 响应恢复返回已持久化的校验和字段，且不改变底层存储布局与加密语义。
