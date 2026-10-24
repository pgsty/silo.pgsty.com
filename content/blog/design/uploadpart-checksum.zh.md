---
title: "可选校验和，强制失败：修复 UploadPart 与 UploadPartCopy 兼容性"
linkTitle: "Multipart Checksum 兼容性"
date: 2026-08-24
lastmod: 2026-09-16
author: "冯若航"
summary: >
  SILO 曾要求开启校验和的分片上传在每次 UploadPart 请求中都必须携带分片级校验和，导致省略可选请求头的普通分片上传报错，并使 UploadPartCopy 完全不可用。本文记录问题排查、AWS 与 AIStor 行为比对、备选方案取舍、明文流单遍计算设计、兼容性基线守卫处理及完整验证证据。
tags: [设计, S3, 兼容性, Checksum]
weight: 30
draft: false
url: "/zh/blog/design/uploadpart-checksum/"
---

本文记录 [SILO #46](https://github.com/pgsty/silo/issues/46)（合并提交 [`7fea6d5a5`](https://github.com/pgsty/silo/commit/7fea6d5a5)，随 [Server 20260903](/zh/blog/release/silo-20260903/) 发布，后续延伸修复见 [#63](https://github.com/pgsty/silo/issues/63) 与 [#64](https://github.com/pgsty/silo/issues/64)）的设计与实现：如何围绕 S3 分片上传的可选校验和请求头，同时理顺分片合并（completion）语义、复制响应、压缩与加密数据流以及兼容性基线守卫。

## 太长不看（TL;DR） {#tldr}

分片上传（Multipart Upload，简称 MPU）会将大对象切分为多个分片（part）分别上传。AWS S3 允许客户端在上传每个分片时附带校验和（checksum），但将其定义为可选请求头。SILO 过去却将其作为必填项强制校验：普通 `UploadPart` 请求一旦省略校验和就会返回 400 错误，而本身不包含请求体的 `UploadPartCopy` 则必然失败。

修复后，若客户端提供了分片校验和，SILO 继续严格校验；若客户端未提供，SILO 则在读取原始明文流的同一遍过程中自行计算校验和并写入分片元数据。计算发生在压缩与加密变换之前，无需二次读取磁盘，也不改变磁盘存储格式。

## 最终决策 {#decision}

当分片上传在 `CreateMultipartUpload` 阶段声明了校验和算法后，SILO 遵循以下处理规则：

1. 若客户端在请求中提供了分片级校验和，服务端继续按原逻辑校验；校验值不匹配或算法不一致时直接报错拒绝，绝不用服务端计算结果掩盖客户端错误。
2. 若客户端省略了分片级校验和，服务端使用该 MPU 记录的算法，在压缩与加密之前的逻辑明文字节流上单遍计算校验和并持久化到分片元数据。
3. 普通 `UploadPart` 仅在客户端请求携带了校验和时才在响应头中回显；服务端自行补算的校验和不在 `UploadPart` 响应头中返回。
4. `UploadPartCopy` 没有客户端请求体校验和，统一由服务端计算并在 `CopyPartResult` XML 响应体中返回对应字段。
5. `ListParts` 返回已持久化的各分片校验和。
6. `FULL_OBJECT` 模式的合并操作继续从各分片校验和线性推导完整对象校验和；`COMPOSITE` 模式的合并操作继续要求客户端提交各分片的校验和（客户端可通过 `ListParts` 查询获取）。
7. 校验和计算在首次读取数据流时同步完成，合并阶段绝不重新读取整个对象。

## 我们如何发现问题 {#discovery}

该缺陷在排查另一个分片上传校验和议题 [#31](https://github.com/pgsty/silo/issues/31) 时暴露。

#31 处理的是 `CompleteMultipartUpload`：当校验和类型为 `FULL_OBJECT` 时，客户端只需提交分片编号、ETag 及可选的完整对象校验和，无需在合并 XML 中逐一列出所有分片的校验和。在向上游回溯数据流时，我们发现 `erasureObjects.PutObjectPart` 在写入任何分片前有一处硬性拦截：

```go
if cs := fi.Metadata[hash.MinIOMultipartChecksum]; cs != "" {
    if r.ContentCRCType().String() != cs {
        return InvalidArgument{/* checksum missing */}
    }
}
```

只要 MPU 在创建时声明了校验和算法，后续每个 `UploadPart` 请求都必须携带匹配的 `x-amz-checksum-*` 请求头，否则直接返回：

```text
400 InvalidArgument:
checksum missing, want "CRC32", got ""
```

API 探针在单盘与纠删码后端上均复现了该错误。

进一步核查 `CopyObjectPartHandler` 后，这一兼容性问题直接升级为 P0 级缺陷：`UploadPartCopy` 请求根本没有可供客户端计算校验和的请求体。处理函数从源对象读取字节并构造内部读取器，最终同样调用 `PutObjectPart`。客户端既无法通过补充请求头绕过，也无法通过调整 SDK 配置规避，导致所有开启校验和的 MPU 都无法使用 `UploadPartCopy`。

## AWS 契约到底是什么 {#aws-contract}

AWS S3 接口文档对三类相关操作的输入与输出有明确界定：

- [AWS UploadPart API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html) 将各算法对应的校验和请求头定义为可选的数据完整性检查，并明确规定：仅当请求中提供了校验和时，响应头才会返回对应的校验和字段。
- [AWS UploadPartCopy API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html) 则规定：若创建 MPU 时指定了校验和算法，`CopyPartResult` 响应中将包含目标分片的校验和。由于复制请求不含数据体，该值必然由服务端计算生成。
- [AWS ListParts API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html) 用于查询未完成 MPU 中各已上传分片的校验和。

算法与校验和类型的支持矩阵如下：

| 算法 | `FULL_OBJECT` | `COMPOSITE` |
| --- | --- | --- |
| CRC64NVME | 支持 | 不支持 |
| CRC32 / CRC32C | 支持 | 支持 |
| SHA1 / SHA256 | 不支持 | 支持 |

`FULL_OBJECT` 仅支持可线性合并的 CRC 算法；而 SHA1 与 SHA256 虽不支持线性合并，仍需在每个分片中记录正确的摘要（digest），才能在 `COMPOSITE` 模式下完成合并校验。

在实际使用中，尽管新版 AWS SDK 默认倾向于为支持校验和的请求自动计算摘要，但用户一旦配置 `request_checksum_calculation = when_required`，或通过底层 API 在发起 MPU 时指定算法、而在上传分片时省略校验和请求头，就会在旧版 SILO 上触发 400 错误。

## 为什么不能只删除强制检查 {#completion-invariant}

最直观的改法是直接删掉 `PutObjectPart` 中的校验条件，放行不带校验和的分片写入。但这只会把报错推迟到 `CompleteMultipartUpload` 阶段。

SILO 在合并分片时不会重新读取并拼接所有分片的数据字节，而是直接读取每个 `part.N.meta` 中的 `ObjectPartInfo.Checksums`：

- 若分片元数据缺少对应算法的校验和，立即返回 `InvalidPart`；
- `FULL_OBJECT` 模式调用 `Checksum.AddPart`，按各分片字节长度线性合并 CRC；
- `COMPOSITE` 模式将各分片摘要的原始字节依次拼接，再对拼接结果计算一次对象级哈希。

因此，存储层依赖的核心不变量是：

```text
checksum-enabled MPU
        => every committed part has a checksum for the MPU algorithm
```

如果只删除入口检查而不补齐分片元数据，就会导致 `UploadPart` 表面返回成功、`ListParts` 缺失校验和字段、`UploadPartCopy` 响应缺值，最终在合并阶段因 `InvalidPart` 失败。

## 我们研究过的方案 {#alternatives}

| 方案 | 优点 | 致命问题 | 结论 |
| --- | --- | --- | --- |
| 仅删除入口强制检查 | 改动最少 | 分片元数据缺少校验和，合并阶段必然报错 | 否决 |
| 仅对 `FULL_OBJECT` 放宽限制 | 可兼容部分默认 CRC 客户端 | `COMPOSITE` 与 SHA1/SHA256 依然报错，无法完整修复 #46 | 否决 |
| 合并阶段重新读取所有分片计算 | 上传阶段无需保存摘要 | 引入 $O(\text{对象大小})$ 的额外磁盘与网络读取，且无法修复 `ListParts` 与复制响应 | 否决 |
| 普通 `UploadPart` 始终返回服务端计算值 | 易于旧版联邦转发 | 违反 AWS“仅在请求提供时回显”的响应规范 | 否决 |
| 照搬 AIStor 实现 | 有商业版先例可循 | 仅支持可线性合并的 CRC，且哈希器挂载位置在压缩/加密路径下存在读取变换后字节的风险 | 否决 |
| 在逻辑明文流上单遍计算并持久化 | 完全符合 S3 规范、无二次 I/O、同时覆盖 CRC 与 SHA | 需在内部显式分离明文校验和读取器与底层存储读取器 | 采用 |

### 商业版 AIStor 给了什么线索 {#aistor}

我们对当时最新的 MinIO AIStor `RELEASE.2026-08-07T18-34-35Z` 二进制执行了 Go `pclntab` 符号还原与 ARM64 反汇编分析。静态分析显示，AIStor 已实现了以下机制：

- 当客户端未提供校验和时挂载服务端哈希计算器；
- 将计算结果写入分片元数据；
- 在 `CopyPartResult` 结构体中新增校验和字段。

但 AIStor 的回退计算仅对满足 `CanMerge()` 的 CRC 算法（CRC32、CRC32C、CRC64NVME）生效，SHA1 与 SHA256 的 `COMPOSITE` 上传仍会触发 `checksum missing` 错误。更重要的是，AIStor 在对象层直接将哈希计算器挂载到当前的 `r.Reader` 上；而在开启服务端压缩或加密的路径中，传入对象层的 `r.Reader` 已经是经过压缩或加密变换后的存储流。因此，SILO 需要在更上游的明文边界挂载计算器，并同时覆盖 SHA1 与 SHA256。

## 设计审查如何推翻第一版设计 {#adversarial-review}

初版方案曾计划将所有逻辑收口到 `erasureObjects.PutObjectPart`：由对象层读取 MPU 元数据，发现客户端未提供校验和时，直接在传入的读取器上挂载服务端哈希计算器。

然而代码审查发现，这一方案在启用服务端压缩时会产生并发竞态与数据截断。`newS2CompressReader` 并非惰性包装器，其构造函数在调用瞬间就会启动后台压缩协程：

```go
go func() {
    _, err := io.Copy(comp, r)
    // ...
}()
```

底层 S2 编码器还会并发预读多个数据块。HTTP 处理函数在创建压缩读取器之后，还需依次执行选项解析、加密封装，最后才进入对象层 `PutObjectPart`。等到 `PutObjectPart` 尝试挂载哈希计算器时，底层明文流往往已经被后台压缩协程消费了数 MiB：

- 较大分片计算出的校验和会丢失开头已读走的数据块；
- 较小分片可能在挂载前就已被全部读完（到达 EOF），导致无法生成任何校验和；
- 在后台协程并发调用 `Read` 的同时修改 `ServerSideHasher` 字段，还会触发直接的数据竞争（data race）。

这一发现决定了最终的职责划分：

- **HTTP 处理函数**负责在启动任何立即消费数据的流变换（如并发压缩或加密封装）之前，在逻辑明文流上挂载哈希计算器；
- **对象层**负责复核算法配置、验证校验和计算结果已就绪，并将其原子写入分片元数据。

## 最终实现 {#implementation}

### 独立的逻辑 checksum reader {#checksum-reader}

`PutObjReader` 原本包含两个读取器字段：

- `Reader`：最终交付给底层存储的字节流（可能已经过压缩或加密）；
- `rawReader`：供 ETag 计算等既有逻辑使用的原始读取器。

在压缩路径下，`rawReader` 也并非始终直接读取明文字节，有时仅通过 `etag.Tagger` 接口透传 ETag。为避免破坏既有 ETag 语义，我们在 `PutObjReader` 中新增了未导出字段：

```go
checksumReader *hash.Reader
```

`checksumReader` 始终绑定未经变换的 S3 逻辑分片明文流。后续调用 `WithEncryption` 包装存储流 `Reader` 时，会原样保留 `checksumReader`。

同时，`PutObjReader` 新增了未导出的访问方法：

- 获取最终生效的校验和类型（客户端提供或服务端补算）；
- 若客户端提供了校验和，优先返回客户端校验结果；
- 若客户端未提供，则返回读取到达 EOF 时由服务端哈希器生成的计算结果。

将该字段与方法保持为包内未导出，既避免了扩大公共 Go API 表面，也为后续 [#63](https://github.com/pgsty/silo/issues/63) 修复普通 `CopyObject` 预留了同一套底层机制。

### 在 transform 之前准备 hasher {#prepare-reader}

辅助函数 `prepareMultipartChecksumReader` 负责读取 MPU 元数据中记录的算法与校验和类型：

1. 若 MPU 未声明校验和算法，直接返回；
2. 若客户端已提供校验和，比对其基础算法是否与 MPU 声明一致；
3. 若算法不匹配，按原逻辑返回 `InvalidArgument`；
4. 若客户端未提供校验和，则在明文 `hash.Reader` 上挂载对应算法的服务端哈希计算器。

对于普通 `UploadPart`：

- 压缩路径在完成请求校验和解析（`actualReader.AddChecksum`）之后、调用 `newS2CompressReader` 启动并发压缩之前完成挂载；
- 非压缩路径在请求校验和解析之后、构造加密读取器之前完成挂载。

对于 `UploadPartCopy`：

- 开启校验和的 MPU 先在源对象的目标读取区间上构造内层明文 `hash.Reader`；
- 字节范围复制（range copy）仅对所选区间内的明文字节计算校验和；
- 内层读取器挂载就绪后，再依次包裹压缩与目标端加密流。

### 对象层仍然是最终权威 {#object-layer}

在 HTTP 处理函数层提前挂载哈希器并未削弱对象层的守卫职责。`erasureObjects.PutObjectPart` 依然执行完整校验：

- 重新解析 MPU 元数据中要求的校验和算法；
- 验证传入读取器的有效校验和类型存在且与 MPU 算法一致；
- 在纠删码编码写入完成后提取校验和结果映射；
- 若 MPU 启用了校验和但未能取到计算结果，立即记录内部错误并中止提交；
- 将校验和连同 ETag、分片大小与编号一并写入 `part.N.meta`，最后原子重命名提交该分片。

因此，任何绕过 HTTP 处理函数的内部调用方若未按要求准备合法校验和，仍会被对象层拦截，不会写入缺少校验和元数据的损坏分片。

### CopyPart 响应 {#copy-response}

`CopyObjectPartResponse` 结构体新增了当前支持的五种校验和字段：

```text
ChecksumCRC32
ChecksumCRC32C
ChecksumCRC64NVME
ChecksumSHA1
ChecksumSHA256
```

所有字段均带有 `omitempty` 标签，未启用校验和的 MPU 仍输出与原先完全一致的 XML。普通 `UploadPart` 继续仅通过 `TransferChecksumHeader` 回显客户端传入的校验和请求头，服务端自动补算的结果不会写入响应头。

## 为什么这个修改能解决问题 {#why-it-works}

修复后的分片上传数据流如下：

```text
logical plaintext part
        |
        +--> client checksum verifier (if supplied)
        |         or
        +--> server-side hasher (if omitted)
        |
        v
compression (optional)
        |
        v
encryption (optional)
        |
        v
erasure encode / storage
        |
        v
persist ETag + size + logical part checksum atomically
```

这一管线同时满足四项核心要求：

1. **协议兼容：** 客户端省略可选的分片校验和请求头时，上传与复制均能正常完成。
2. **完整性校验不降级：** 客户端提供校验和时仍执行端到端比对，错误校验值不会被服务端重算结果覆盖。
3. **字节语义准确：** 校验和始终针对 S3 逻辑明文字节计算，不受底层压缩或加密变换影响。
4. **单遍流式处理：** 哈希计算随原有的单遍读取同步完成，无需在内存中缓存完整分片，也无需在合并阶段二次读取磁盘。

此外，`hash.Reader` 仅在读取到达 EOF 时生成最终的 `ServerSideChecksumResult`。在压缩路径下，压缩管道（pipe）的关闭操作天然同步了后台压缩协程与底层存储读取；对象层在纠删码写入返回后读取校验和结果时，计算已确定完成。定向 `-race` 测试验证了这一并发同步边界。

## 兼容性基线守卫处理 {#compat-baseline}

`CopyObjectPartResponse` 新增的五个字段属于导出 Go 符号。SILO 的 `buildscripts/rebrand-guard` 工具会自动扫描导入路径、环境变量、HTTP 头、路由、存储标记及导出符号，并与 `buildscripts/rebrand-guard/compat-baseline.json` 进行双向精确集合比对；任何未登记的新增导出符号都会阻断 CI。

将 #46 新增的五个字段写入基线后，守卫脚本仍报告两项未登记符号：

```text
internal/config/notify:notify:type:LegacyDatabaseTargetError
internal/config/notify:notify:method:LegacyDatabaseTargetError.Error
```

排查确认，这两个符号来自 `main` 分支更早合入的数据库通知修复提交 `f1ba68358`：`cmd` 启动流程需要通过 `errors.As` 匹配该导出错误类型，但原提交漏更新了 `compat-baseline.json`，导致后续基于该分支的所有 PR 都会在兼容性守卫检查处失败。

我们将这两项通知错误符号与 #46 的五个响应字段一并补入基线，最终基线差异为精确的 7 项新增、0 项删除：

```text
exported=9021
Silo rebrand compatibility baseline is unchanged
```

## 验证证据 {#verification}

新增回归测试套件共包含 76 个子测试，完整覆盖以下矩阵：

- CRC32、CRC32C 与 CRC64NVME 的 `FULL_OBJECT` 模式；
- CRC32、SHA1 与 SHA256 的 `COMPOSITE` 模式；
- 客户端提供正确校验和、错误算法与错误校验值；
- 验证服务端补算值不出现在普通 `UploadPart` 响应头中；
- 验证 `UploadPartCopy` 响应体与 `ListParts` 正确返回服务端计算值；
- 5 MiB + 1 KiB 双分片的真实对象线性合并；
- 零字节分片与同分片编号覆盖上传；
- 指定字节区间的 `UploadPartCopy`（验证 SHA256 仅覆盖所选区间）；
- 单盘与 16 盘纠删码两种存储后端；
- 普通桶、版本控制、压缩、加密，以及“压缩 + 加密”组合模式；
- 显式 SSE-C 与 SSE-S3 服务端加密。

本地验证命令：

```text
go test -race ./cmd -run '^TestAPIUploadPartServerSideChecksum' -count=1
go test ./cmd -count=1
go test ./... -count=1
go vet ./cmd
git diff --check
go run ./buildscripts/rebrand-guard
```

## 成本、风险与滚动升级取舍 {#tradeoffs}

当客户端省略分片校验和时，服务端需在读取数据流时额外执行一次哈希计算。CRC 系列算法的 CPU 开销极小，SHA1/SHA256 的 CPU 开销相对较高，但均在既有的数据读取流上单遍完成，不增加全分片内存缓冲，也不产生额外磁盘 I/O。

在集群滚动升级窗口内，新旧节点对省略了校验和的分片上传请求会表现出不同行为：已升级节点正常接收，未升级节点仍返回 400 错误。由于磁盘上 `ObjectPartInfo.Checksums` 的存储格式并未改变，已落盘数据完全向后兼容；待集群所有节点完成升级后，客户端可见行为即全面收敛。

## 为什么拆出两个独立后续 {#follow-ups}

代码审查期间还识别出两项同源但边界独立的问题，分别拆分为独立议题跟进：

### #63：CopyObject + Compression {#follow-up-copy}

普通 `CopyObject` 在启用服务端校验和与服务端压缩时，哈希计算器同样可能被挂载到压缩变换之后的字节流上。该问题与 #46 共享根因及新增的 `checksumReader` 机制，但涉及不同的 API 入口与测试矩阵，因此在 [#63](https://github.com/pgsty/silo/issues/63) 中复用同一明文读取器契约独立修复。

### #64：Legacy Federation {#follow-up-federation}

旧式 etcd 联邦代理会将 `UploadPartCopy` 转换为发往远端集群的普通 `UploadPart` 请求。由于普通 `UploadPart` 遵循 AWS 规范不在响应头中返回服务端补算的校验和，代理节点无法直接从远端 `UploadPart` 响应头中拿到填充 `CopyPartResult` 所需的校验和。[#64](https://github.com/pgsty/silo/issues/64) 在不破坏外部 `UploadPart` 响应合规性的前提下，单独处理联邦代理路径的校验和获取。

这两项后续修复均遵循本次确立的流式处理契约：

> 所有由服务端计算的 S3 校验和都必须绑定在逻辑明文流上，在启动任何并发或流式变换之前完成挂载，并由对象层在落盘前复核与持久化。

## 工程要点总结 {#lessons}

1. **客户端可选输入不代表服务端可省略内部状态。** 当协议允许客户端省略分片校验和时，服务端必须在写入阶段自行补算，以满足合并阶段的元数据不变量。
2. **区分请求处理与响应回显规则。** 普通 `UploadPart` 可在内部补算校验和，但按 S3 规范不得在响应头中回显该值；而 `UploadPartCopy` 则必须在响应体中返回服务端计算值。
3. **流式管线的挂载位置取决于字节语义与并发时机。** 哈希计算器必须挂载在未经压缩和加密的逻辑明文流上，且必须在 `newS2CompressReader` 启动并发预读协程之前完成安装。
4. **外部实现反汇编仅作参考，不能替代完整路径验证。** AIStor 二进制分析验证了服务端补算的方向，但也暴露了仅覆盖 CRC 以及在对象层挂载流读取器的局限。
5. **通过符号基线守卫显式管理导出表面。** `compat-baseline.json` 的双向精确比对确保每次导出符号变更都有明确的提交归属。
6. **共享底层不变量，按独立边界拆分交付。** [#63](https://github.com/pgsty/silo/issues/63) 与 [#64](https://github.com/pgsty/silo/issues/64) 复用本文建立的 `checksumReader` 契约，但各自保持独立的测试矩阵与回归边界。
