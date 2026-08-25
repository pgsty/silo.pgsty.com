---
title: "可选校验和，强制失败：修复 UploadPart 与 UploadPartCopy 兼容性"
linkTitle: "Multipart Checksum 兼容性"
date: 2026-08-24
author: "冯若航"
summary: >
  SILO 曾要求 checksum-enabled multipart upload 的每个 UploadPart 都携带逐 part checksum，导致省略可选 header 的普通上传失败，并让 UploadPartCopy 完全不可用。本文记录问题发现、AWS 与 AIStor 调研、被否决的方案、明文单遍计算设计、兼容基线 blocker、对抗审查，以及后续修复必须遵守的一致性边界。
tags: [设计, S3, 兼容性, Checksum]
weight: 30
draft: false
url: "/zh/blog/design/uploadpart-checksum/"
---

本文是 [SILO #46](https://github.com/pgsty/silo/issues/46) 的完整设计与实现归档。它记录的并不只是一个 `if` 条件如何修改，而是一个看似简单的 S3 可选 header，如何一路牵动 multipart 完成语义、复制响应、压缩与加密数据流、兼容基线和发布验证。

> **状态：** 服务端实现与本地验证完成；commit、PR、远端 CI、发布与线上验证待完成。<br>
> **归属：** [`pgsty/silo`](https://github.com/pgsty/silo) 服务端仓库。<br>
> **跟踪：** [#46](https://github.com/pgsty/silo/issues/46)。<br>
> **独立后续：** [#63 CopyObject + compression checksum](https://github.com/pgsty/silo/issues/63)、[#64 federated UploadPartCopy checksum](https://github.com/pgsty/silo/issues/64)。<br>
> **对抗审查：** 本机 Claude Code、Fable 5、`--effort max`，最终结论 **GO**，无阻断项。

## 太长不看（TL;DR） {#tldr}

Multipart upload 会把大文件切成多个 part 再上传。客户端可以给每个 part 附上 checksum，帮助服务器确认传输没有出错，但 AWS 规定这个 checksum 是可选的。SILO 原来却把它当成必填项：普通 `UploadPart` 没带 checksum 就会失败，而 `UploadPartCopy` 根本没有 checksum 可以提供，所以一定失败。

修复后，客户端提供 checksum 时，SILO 仍然认真校验；客户端没提供时，SILO 就在读取原始数据的同时自己计算，并把结果保存下来。计算发生在压缩和加密之前，不需要重读文件，也不改变盘上格式。这样既兼容 AWS，也没有放松数据完整性检查。

## 最终决策 {#decision}

当 multipart upload 在 `CreateMultipartUpload` 阶段声明 checksum algorithm 后，SILO 采用以下契约：

1. 客户端若提供逐 part checksum，服务器继续校验它；错误值与错误算法必须失败，绝不能被 fallback 掩盖。
2. 客户端若省略逐 part checksum，服务器使用 MPU 记录的算法，在压缩与加密之前的逻辑明文流上单遍计算并持久化结果。
3. 普通 `UploadPart` 只在客户端提供 checksum 时回显响应 header；服务器自行计算的值不回显。
4. `UploadPartCopy` 没有客户端请求体 checksum，服务器必须计算，并在 `CopyPartResult` 中返回对应值。
5. `ListParts` 返回持久化的 part checksum。
6. `FULL_OBJECT` completion 继续从各 part checksum 线性合并完整对象 checksum；`COMPOSITE` completion 继续要求客户端提交每个 part checksum，客户端可从 `ListParts` 取回。
7. 计算必须发生在现有数据读取过程中，不得在 completion 阶段重新读取整个对象。

一句话概括：

> 可选的是客户端提供的校验值，不是服务器维护 checksum-enabled MPU 内部一致性的责任。

## 我们如何发现问题 {#discovery}

问题是在排查另一个 multipart checksum 缺陷 [#31](https://github.com/pgsty/silo/issues/31) 时发现的。

#31 处理的是 `CompleteMultipartUpload`：当 checksum type 为 `FULL_OBJECT` 时，客户端可以只提交 part number、ETag 和可选的完整对象 checksum，而不必在 completion XML 中重复保存所有 part checksum。沿着完成路径向前追踪时，我们发现 `erasureObjects.PutObjectPart` 在写入任何 part 前有一条更早、更强的约束：

```go
if cs := fi.Metadata[hash.MinIOMultipartChecksum]; cs != "" {
    if r.ContentCRCType().String() != cs {
        return InvalidArgument{/* checksum missing */}
    }
}
```

也就是说，只要 MPU 声明了 checksum algorithm，每个普通 `UploadPart` 请求都必须携带匹配的 `x-amz-checksum-*`，否则返回：

```text
400 InvalidArgument:
checksum missing, want "CRC32", got ""
```

API 级探针在单盘和纠删码后端上都复现了这一行为。

进一步审查 `CopyObjectPartHandler` 后，问题从“部分客户端不兼容”升级成了 P0：`UploadPartCopy` 没有可供调用方校验的请求体。处理器从源对象读取字节，构造内部 reader，然后进入同一个 `PutObjectPart`。客户端没有 header 可以补上，也没有 SDK 配置可以绕开。这使得 checksum-enabled MPU 上的 `UploadPartCopy` 成为必然失败，而不是偶发失败。

## AWS 契约到底是什么 {#aws-contract}

这个问题不能靠“MinIO 一直这么做”来裁决，必须回到 S3 协议。

[AWS UploadPart API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPart.html) 把算法特定的 checksum header 描述为 “can be used as a data integrity check”。更关键的是，响应字段明确说明：只有请求提供了 checksum，响应才返回对应 checksum header。

[AWS UploadPartCopy API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_UploadPartCopy.html) 的规则不同：如果创建 MPU 时声明了算法，复制结果中会出现该 part 的 checksum。复制请求没有 part body，因此这是服务器计算的结果。

[AWS ListParts API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListParts.html) 则提供恢复进行中 MPU 各 part checksum 的标准接口。

算法与 checksum type 的矩阵也决定了实现不能只考虑一个布尔开关：

| Algorithm | `FULL_OBJECT` | `COMPOSITE` |
| --- | --- | --- |
| CRC64NVME | 支持 | 不支持 |
| CRC32 / CRC32C | 支持 | 支持 |
| SHA1 / SHA256 | 不支持 | 支持 |

`FULL_OBJECT` 只适用于可线性合并的 CRC；但 SHA1/SHA256 仍然需要正确的逐 part digest 才能完成 `COMPOSITE` 上传。

这也解释了为什么 SDK 配置会暴露问题。新版 AWS SDK 默认倾向于为支持 checksum 的请求自动计算值，但用户可以选择 `request_checksum_calculation = when_required`，也可以直接使用低级 API 而不在每个 part 上重复声明算法。S3 服务端接受这些请求；SILO 当时不接受。

## 为什么不能只删除强制检查 {#completion-invariant}

最诱人的修复是删除上面的比较，让没有 checksum 的 part 继续写入。但这只会把失败推迟到 completion。

SILO 完成 MPU 时不会重新读取并组装全部对象字节。它读取每个 `part.N.meta` 中的 `ObjectPartInfo.Checksums`：

- 若该值不存在，立即返回 `InvalidPart`；
- `FULL_OBJECT` 使用 `Checksum.AddPart` 按 part 长度线性合并；
- `COMPOSITE` 拼接各 part digest 的原始字节，再对它们计算对象级 checksum。

因此内部不变量是：

```text
checksum-enabled MPU
        => every committed part has a checksum for the MPU algorithm
```

删除入口检查却不填充 metadata，会让 `UploadPart` 表面成功、`ListParts` 缺字段、`UploadPartCopy` 缺响应、completion 再失败。这比立即失败更难诊断。

## 我们研究过的方案 {#alternatives}

| 方案 | 优点 | 致命问题 | 结论 |
| --- | --- | --- | --- |
| 只删除 strict check | 改动最少 | part metadata 仍缺 checksum，completion 必然失败 | 否决 |
| 只放宽 `FULL_OBJECT` | 能覆盖部分默认 CRC 客户端 | `COMPOSITE` 与 SHA 仍不兼容，不能关闭 #46 | 否决 |
| completion 时重读全部 part | 不必在上传时保存 digest | 增加 O(object size) 二次 I/O，复制响应与 `ListParts` 仍然错误 | 否决 |
| 普通 `UploadPart` 总是返回服务器值 | federation 容易转发 | 违反 AWS “仅在请求提供时返回”的响应契约 | 否决 |
| 原样复制 AIStor 实现 | 有商业产品先例 | 只 fallback 可合并 CRC，且 hasher 挂载层次存在 transformed-byte 风险 | 否决 |
| 在逻辑明文流上单遍计算并持久化 | 协议完整，无二次 I/O，覆盖 CRC 与 SHA | 需要明确区分明文 checksum reader 与存储 reader | 采用 |

### 商业版给了什么线索 {#aistor}

我们下载并校验了当时最新的 MinIO AIStor `RELEASE.2026-08-07T18-34-35Z`。没有商业许可证时服务器会进入 offline mode 并拒绝 S3 操作，因此只能基于 Go pclntab 与 ARM64 反汇编做静态分析，不能把结果包装成黑盒兼容性测试。

静态分析显示，AIStor 已经：

- 在缺少客户端 checksum 时使用服务器 hasher；
- 把计算结果写入 part metadata；
- 在 `CopyPartResult` 中加入 checksum 字段。

但它只为 `CanMerge()` 算法启用 fallback，也就是 CRC32、CRC32C、CRC64NVME；SHA1/SHA256 `COMPOSITE` 仍会走 `checksum missing`。更重要的是，hasher 在对象层附着到当前 `r.Reader`；在压缩或加密路径中，该 reader 可能已经是变换后的存储流。

AIStor 因此证明了“服务器计算并保存”这个方向，但没有提供一个可以无条件照搬的最终设计。

## 对抗审查如何推翻第一版设计 {#adversarial-review}

第一版计划希望把所有决定集中到 `erasureObjects.PutObjectPart`：对象层读取 MPU metadata，发现客户端没有 checksum 后，再为 reader 安装服务器 hasher。这样看起来最统一，因为所有内部调用者都会遵守同一规则。

Fable 5 Max 的第一次对抗审查指出，这个方案在压缩路径上是错的。

`newS2CompressReader` 并不是惰性包装器。构造函数会立即启动 goroutine：

```go
go func() {
    _, err := io.Copy(comp, r)
    // ...
}()
```

S2 writer 还会并发预读多个 block。处理器创建 compressor 后，才会经过更多选项解析、加密准备和对象层调用。等 `PutObjectPart` 安装 hasher 时，明文 reader 可能已经被消费了数 MiB：

- 大 part 得到缺少前缀的 checksum；
- 小 part 可能在 hasher 安装前已经读完，根本没有结果；
- 对 `ServerSideHasher` 的写入与 `Read` 并发，形成数据竞争。

这个发现改变了责任划分：

> Handler 负责在任何 eager transform 启动前安装 hasher；object layer 负责复核算法、确认结果存在并原子持久化。

这是本次设计中最关键的转折。把逻辑集中在更低层并不天然更正确；对于流式系统，**何时开始消费字节**和**在哪一层看到哪种字节**同样是接口契约。

## 最终实现 {#implementation}

### 独立的逻辑 checksum reader {#checksum-reader}

`PutObjReader` 原本有两个概念：

- `Reader`：真正交给存储层的流，可能已压缩或加密；
- `rawReader`：用于 ETag 等旧逻辑的 reader。

压缩路径中的 `rawReader` 也不一定直接看到明文，它可能只是通过 `etag.Tagger` 透传 ETag。因此本次没有重载它，而是新增未导出的：

```go
checksumReader *hash.Reader
```

该 reader 永远代表 S3 逻辑 part 的明文字节。`WithEncryption` 可以替换存储 `Reader`，但不能替换 `checksumReader`。

`PutObjReader` 同时提供未导出的 accessor：

- 取得客户端提供或服务器计算的 effective checksum type；
- 客户端值存在时优先返回客户端值；
- 否则返回服务器在 EOF 处生成的结果。

保持方法未导出有两个目的：缩小公共 Go API 变化，也为后续 [#63](https://github.com/pgsty/silo/issues/63) 保留统一内部机制，而不提前改变普通 `CopyObject` 行为。

### 在 transform 之前准备 hasher {#prepare-reader}

`prepareMultipartChecksumReader` 读取 MPU 保存的 algorithm 与 checksum type：

1. 没有声明算法时不做任何事；
2. 客户端已有 checksum 时比较 base algorithm；
3. 算法错误时延续 `InvalidArgument`；
4. 客户端没有 checksum 时，为明文 reader 安装对应 server-side hasher。

普通 `UploadPart`：

- 压缩路径在 `actualReader.AddChecksum` 之后、`newS2CompressReader` 之前准备；
- 非压缩路径在 request checksum 解析之后、加密 reader 构造之前准备。

`UploadPartCopy`：

- checksum-enabled MPU 先在源对象的逻辑范围上构造内层 `hash.Reader`；
- range copy 只覆盖指定字节范围；
- 内层 reader 准备完成后才进入压缩和目标加密。

### 对象层仍然是最终权威 {#object-layer}

Handler 的提前准备不能替代对象层不变量。`erasureObjects.PutObjectPart` 仍然：

- 重新解析 MPU 的期望算法；
- 要求 effective checksum type 存在且匹配；
- 完成 erasure encode 后取得 checksum map；
- 如果算法已启用但结果缺失，记录 internal error 并拒绝提交；
- 把 checksum 与 ETag、size、index 一起写入 `part.N.meta`，随后原子 rename part。

于是内部调用者若绕过 handler，又没有准备合法 checksum，仍然得到旧的拒绝行为，不会静默写入破坏不变量的 part。

### CopyPart 响应 {#copy-response}

`CopyObjectPartResponse` 增加了当前代码树支持的五个字段：

```text
ChecksumCRC32
ChecksumCRC32C
ChecksumCRC64NVME
ChecksumSHA1
ChecksumSHA256
```

字段使用 `omitempty`，所以没有启用 checksum 的 MPU 保持旧 XML。普通 `UploadPart` 仍只通过原有 `TransferChecksumHeader` 回显客户端请求值；服务器 fallback 不改变它的响应。

## 为什么这个修改能解决问题 {#why-it-works}

修复后数据流变成：

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

它同时满足四个以前冲突的目标：

1. **协议兼容：** 可选 header 省略后上传成功。
2. **完整性不降级：** 客户端给值时仍做端到端比对；服务器不会用自己的计算结果掩盖错误客户端值。
3. **对象语义正确：** checksum 覆盖逻辑 S3 字节，而不是压缩数据或密文。
4. **性能可控：** checksum 与原有读取同一遍完成，只增加 hash CPU，不增加第二遍磁盘或网络 I/O。

EOF 也有明确作用：`hash.Reader` 只有在读到 EOF 后才固定 `ServerSideChecksumResult`。压缩 pipe 的关闭同步了 goroutine 与存储读取；对象层只在 encode 返回后读取结果。定向 `-race` 测试验证了这个并发边界。

## 兼容基线 blocker {#compat-baseline}

`CopyObjectPartResponse` 的五个新字段是导出的 Go API。SILO 的 `buildscripts/rebrand-guard` 会重新扫描 import、环境变量、header、route、存储 marker 与导出符号，并与 `buildscripts/rebrand-guard/compat-baseline.json` 做双向精确集合比较。新增符号若没有显式登记，CI 会失败。

我们先登记了 #46 的五个字段，guard 随后仍报告两个新增符号：

```text
internal/config/notify:notify:type:LegacyDatabaseTargetError
internal/config/notify:notify:method:LegacyDatabaseTargetError.Error
```

它们不是 #46 引入的，而是本地 `main` 上更早的数据库通知修复 `f1ba68358` 有意导出的类型：`cmd` 启动路径需要通过 `errors.As` 识别它。此前提交没有同步 baseline，因此任何建立在当前 HEAD 上的改动都会在 CI guard 处失败。

最终采用“方案 A”：把两条 notification 符号登记归属到原修复，同时保留 #46 五条字段。最终 baseline diff 恰好是七条新增、零删除，guard 输出：

```text
exported=9021
Silo rebrand compatibility baseline is unchanged
```

这不是把检查关闭。guard 的精确集合比较意味着多登记一个不存在的符号也不能通过。它只是显式确认两组有意的兼容表面变化。

`golangci-lint` 尚未在本地执行；它仍是远端 `go.yml` 的发布前检查之一。`go test`、`go vet`、race 与 rebrand guard 的本地通过，不能替代远端 CI 全绿。

## 验证证据 {#verification}

新增测试实际执行 76 个子测试，覆盖：

- CRC32、CRC32C、CRC64NVME `FULL_OBJECT`；
- CRC32、SHA1、SHA256 `COMPOSITE`；
- 正确客户端 checksum、错误算法、错误值；
- 服务器计算值不出现在普通 `UploadPart` 响应；
- `UploadPartCopy` 响应和 `ListParts` 返回服务器值；
- 真实的 5 MiB + 1 KiB 两 part 合并；
- 零长度 part、覆盖同一 part number；
- range copy，只对复制区间计算 SHA256；
- 单盘与 16 盘纠删码；
- default、versioned、compressed、encrypted、compressed + encrypted；
- 显式 SSE-C 与 SSE-S3。

本地验证包括：

```text
go test -race ./cmd -run '^TestAPIUploadPartServerSideChecksum' -count=1
go test ./cmd -count=1
go test ./... -count=1
go vet ./cmd
git diff --check
go run ./buildscripts/rebrand-guard
```

全部通过。随后两次 Claude Code Fable 5 Max 实现审查与最终验收都给出 **GO**，无 blocking finding。

## 成本、风险与发布边界 {#tradeoffs}

服务器为省略 checksum 的 part 增加一次 hash CPU 成本。CRC 成本很低，SHA 的成本更高，但仍在本来就要经过的字节流上完成，不增加内存中完整 part 缓冲，也不增加完成阶段的第二遍读取。

滚动升级期间，新旧节点可能对同一个省略 checksum 的请求给出不同结果：新节点接受，旧节点返回 400。盘上 `ObjectPartInfo.Checksums` 格式没有变化，降级读取是兼容的；但客户端可见行为要到所有服务节点升级后才稳定。发布说明必须提示完成滚动升级。

本记录描述的是本地 `main` 工作树。实现尚未 commit、push 或进入远端 CI，也没有形成发布包。SILO 文档属于 `silo.pgsty.com`，不能因为本地 Hugo 构建成功就宣称 [pgsty.com](https://pgsty.com) 生态中的产品版本已经发布。

## 为什么拆出两个独立后续 {#follow-ups}

对抗审查还发现两个相关但独立的问题。

### #63：CopyObject + compression {#follow-up-copy}

普通 `CopyObject` 的 server-side checksum 也可能挂在 transformed stream 上。它与本次共享根因和 `checksumReader` 机制，但属于不同 API、测试矩阵和回滚边界。我们决定单独修复，并要求后续 PR 复用本次明文 reader 契约，不建立第二套抽象。

### #64：legacy federation {#follow-up-federation}

旧式 etcd federation 会把 `UploadPartCopy` 转成远端普通 `UploadPart`。按照本次坚持的 AWS 语义，远端普通 UploadPart 不应返回服务器 fallback 值，因此代理仍可能拿不到 `CopyPartResult` 所需 checksum。后续要在远端响应与经 ETag 校验的 `ListParts` fallback 之间做独立设计，不能通过破坏所有外部 UploadPart 响应来取巧。

把它们拆开并不是忽略一致性，而是让一致性通过一个明确的共享原则维持：

> 所有服务器计算的 S3 checksum 都必须绑定逻辑明文流，在任何 eager transform 之前安装，并由拥有存储不变量的对象层复核和持久化。

## 沉淀下来的经验 {#lessons}

这次修复留下了几条比具体代码更重要的经验：

1. **“header 可选”不等于服务器可以缺少内部数据。** 协议允许客户端省略，服务器就必须补足自身完成流程需要的状态。
2. **接受请求与返回响应是两个契约。** 普通 UploadPart 可以在内部计算，却仍须按 AWS 规则不返回该值；UploadPartCopy 则必须返回。
3. **流式系统的层次由字节语义决定。** 最低层最统一，但不一定还能看到正确的逻辑字节；eager goroutine 还会让“稍后安装”变成竞态。
4. **商业实现是证据，不是规范。** AIStor 展示了方向，也展示了不能照抄的边界。
5. **兼容 guard 是变更确认机制。** `compat-baseline.json` 不是为了让 CI 闭嘴，而是要求每一个新兼容表面都有明确归属。
6. **独立问题应独立交付，但要共享设计不变量。** #63 与 #64 分开做，仍然必须引用并遵守本记录建立的 checksum reader 契约。

最终得到的不是一次宽松化，而是一条更严格也更准确的边界：客户端可以省略可选信息；服务器不能省略正确性。
