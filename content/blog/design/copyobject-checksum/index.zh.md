---
title: "CopyObject Checksum 必须覆盖逻辑对象字节"
date: 2026-08-24
lastmod: 2026-08-24
author: "冯若航"
summary: >
  目标端启用压缩后，SILO 可能把 S2 存储流的 checksum 当成 CopyObject 逻辑对象 checksum 持久化。本文重建故障机理，比较被否决的修复方案，定义明文 reader 不变量，证明最终方案为什么成立，并记录发布与存量对象处置边界。
tags: [设计, S3, 兼容性, Checksum]
weight: 10
draft: false
url: "/zh/blog/design/copyobject-checksum/"
---

本文是 [SILO #63](https://github.com/pgsty/silo/issues/63) 的最终设计与验证归档。

**最终决策：** 所有由服务器生成的 CopyObject checksum 都必须在压缩和加密之前，基于目标对象的逻辑字节计算；逻辑 reader 与存储 reader 分离保存；如果读到 EOF 后仍拿不到预期 checksum，则拒绝发布对象。<br>
**实现：** [PR #66](https://github.com/pgsty/silo/pull/66)，合并提交为 <code>c0e715977</code>。<br>
**相关修复：** transform state 保真 [#67](https://github.com/pgsty/silo/issues/67) / [PR #69](https://github.com/pgsty/silo/pull/69)，CopyObjectResult checksum 字段 [#68](https://github.com/pgsty/silo/issues/68) / [PR #70](https://github.com/pgsty/silo/pull/70)。<br>
**上游客户端：** [minio-go PR #2295](https://github.com/minio/minio-go/pull/2295)。<br>
**发布边界：** 这些修改已经合并到源码，但本文不声称任何具体 release tag、RPM、DEB、APK、归档或容器镜像已经包含它们。

## 一句话决策 {#decision}

checksum 不是“在写入链路上随便找个位置算出的 digest”。它一定是某段明确定义字节序列的函数。对 S3 CopyObject 而言，这段字节必须是客户端最终读到的逻辑对象，而不是 SILO 私有的压缩或加密表示。

因此最终采用的流水线是：

~~~text
逻辑源对象字节
    -> server-side S3 checksum
    -> 可选 S2 压缩
    -> 存储流 hash 与 ETag 委托
    -> 可选服务端加密
    -> 纠删码
    -> EOF checksum 验证
    -> 数据与 metadata 原子提交
~~~

整份设计都可以从这个顺序推出。

## 背景：一个对象存在多个完整性域 {#background}

SILO 中有若干值都会被口语化地称作 checksum，但它们保护的契约并不相同。

| 值 | 字节域 | 用途 |
| --- | --- | --- |
| S3 additional checksum | 逻辑对象字节 | 通过 HEAD、GET、attributes 和复制响应提供客户端可见的端到端完整性 |
| ETag | 普通单 part、兼容未加密场景下代表逻辑内容；其他场景遵循各自协议语义 | 对象身份与条件请求兼容性 |
| 存储 reader 记账 | 压缩或加密后的写入流 | 在写入路径中传递 size、stream 与 ETag 委托 |
| 纠删码 bitrot checksum | 盘上纠删码 shard | 检测 SILO 物理表示损坏 |
| 加密认证 | 密文 framing 与密钥 | 检测篡改并认证加密存储 |
| 压缩 index | S2 存储流偏移 | 支持大压缩对象的高效读取 |

它们可以在同一遍流式写入中计算，却绝不能相互替代。存储流 checksum 完全可能在数学上正确，同时作为 S3 对象 checksum 完全错误。

Amazon S3 明确规定 CopyObject 会产生目标 checksum；multipart 来源在一次 CopyObject 后会成为 full-object checksum。算法可能由请求显式选择、从来源继承，或在来源没有 checksum 时使用默认算法。无论哪一种，结果描述的都是复制后的对象，而不是供应商私有的存储编码。

## #46 如何暴露 #63 {#discovery}

这个缺陷是在修复 multipart checksum 兼容性 [#46](https://github.com/pgsty/silo/issues/46) 时发现的。

#46 为 UploadPart 与 UploadPartCopy 建立了三条内部规则：

1. 为逻辑明文 checksum 保留专用 reader。
2. fallback server hasher 必须由 handler 在压缩或加密消费数据前安装。
3. 对象层负责验证并持久化完成后的结果，但不在对象层决定字节域。

由此引入的私有字段 <code>checksumReader</code> 刻意与活动 <code>Reader</code>、历史 <code>rawReader</code> 分开。<code>WithEncryption</code> 可以替换活动存储 reader，却不能替换逻辑 checksum reader。

沿着普通 CopyObject 检查后，我们发现同一个概念风险出现在另一条 handler 中：代码先创建 <code>newS2CompressReader</code>，把它的输出包装成 <code>srcInfo.Reader</code>，之后才对这个 reader 调用 <code>AddServerSideChecksumHasher</code>。变量名掩盖了关键事实：此时的 <code>srcInfo.Reader</code> 已经代表存储流，不一定代表 S3 对象流。

#46 刻意不修改 CopyObject。把 #63 单独拆出，意味着 P0 multipart 修复可以独立审查、发布或回滚，不必绑定另一套 API 与测试矩阵。

## 故障模型 {#failure-model}

### 旧顺序

旧流程的关键部分是：

~~~text
GetObject 逻辑 reader
    -> 启动 S2 压缩 goroutine
    -> 把压缩输出包装为 hash.Reader
    -> 随后决定目标 checksum algorithm
    -> 把 server-side hasher 挂到压缩 hash.Reader
    -> 把结果当成对象 S3 checksum 持久化
~~~

从存储 writer 的角度看，这个 checksum 并没有漏数据，也不一定损坏；它只是覆盖了错误但完整的流。

### 静态假设与动态结果

最初 Issue 提出了两种可能：

- hasher 覆盖压缩数据；
- 压缩 goroutine 在 hasher 安装前已经消费部分逻辑输入，导致漏掉前缀。

API 复现确认了第一种，没有确认第二种。hasher 实际安装在压缩器输出侧 reader 上，因此会从该输出 reader 的起点观察完整 transformed stream。压缩输入侧提前消费的字节，并不是输出 hash reader 已经消费的字节。

这个区别很重要：根因不是“偶发 race，因此加一把锁即可”，而是确定性的数据域错误。

### 可重复复现

对于永久测试使用的同一份 payload，未修复树保存的是：

~~~text
S2 存储字节 CRC32：hN7ytg==
逻辑对象 CRC32：    1WxbLg==
~~~

前者是合法 CRC32，所以普通 metadata 合法性检查无法发现。只有对下载后的逻辑对象独立计算，才会暴露不一致。

CRC32、CRC32C、CRC64NVME、SHA1、SHA256 在压缩目标上都会失败。当压缩与目标加密组合时，S2 会为加密流加入随机 padding，错误 checksum 不但错误，而且同一份逻辑复制多次可能得到不同结果。

## 需求与非目标 {#requirements}

修复必须同时满足：

1. **字节域正确。** 服务器生成的 checksum 精确覆盖目标逻辑字节。
2. **单遍流式处理。** CopyObject 不能增加第二遍对象读取。
3. **与变换无关。** 压缩和加密不能改变逻辑 checksum。
4. **客户端兼容。** 既有客户端 checksum 校验与算法选择语义不变。
5. **multipart 来源正确。** multipart composite 来源复制为单对象后，必须按 base algorithm 重算 full-object checksum。
6. **默认行为正确。** 来源没有 checksum 时，目标仍获得当前基线的 S3 兼容默认 CRC64NVME。
7. **ETag 不回归。** 移动 checksum reader 不能悄悄改变 CopyObject ETag 契约。
8. **fail closed。** 内部调用者声明要生成 checksum 却没有生成时，不能返回成功并缺少完整性 metadata。
9. **格式兼容。** 继续使用既有 checksum metadata 表示。
10. **回滚边界小。** 不把响应 schema、federation 或 metadata-only transform 缺陷混入核心放置修复。

#63 明确不负责：

- 新增 checksum 算法；
- 修改盘上 checksum 编码；
- 扫描或回填旧对象；
- 修复 legacy federated UploadPartCopy；
- 增加 CopyObjectResult XML 字段；
- 修改 MCLI 或 Console 行为。

## 备选方案与权衡 {#alternatives}

| 方案 | 吸引力 | 否决原因 |
| --- | --- | --- |
| 在对象层安装 hasher | 所有调用者集中 fallback | 对象层拿到的是 handler 变换后的存储 reader，无法可靠重建逻辑字节域，而且安装时点可能过晚 |
| 对 S2 输出做 hash | 代码移动最少 | 这就是已经复现的缺陷：保护存储字节，不保护 S3 对象字节 |
| 对密文做 hash | 加密设置完成后最方便 | IV、framing、认证与 padding 让结果变成供应商私有值，且往往非确定 |
| 写完后重新读取对象 | 推理简单 | I/O 翻倍，破坏单遍流式目标，增加大对象和分层对象延迟 |
| 变换前缓存整个对象 | 顺序直观 | CopyObject 可处理大对象；整对象缓冲带来不可接受的内存与延迟 |
| 永远复制来源 checksum 值 | 避免计算 | 请求可能指定不同算法；来源可能没有 checksum；multipart composite 来源必须转为 full-object |
| 新建 CopyObject 专用 checksum 抽象 | 改动局部 | 重复 #46 已建立的不变量，未来形成两套略有差异的内部契约 |
| 在变换前复用逻辑 checksumReader | 单遍、复用既有格式、共享内部不变量 | 采用 |

选择方案不只是“改动行数最少”，而是它用最少机制把字节域契约显式化，并且能够复用。

## 最终设计 {#design}

### 1. 先构造逻辑 reader

CopyObject 取得的源 <code>GetObjectReader</code> 已经输出逻辑源对象：盘上压缩已经解码，来源加密也已经通过授权的 source options 解开。

SILO 用已知逻辑对象大小把它包装成逻辑 <code>hash.Reader</code>。对压缩目标而言，这还把过去的无限长度收紧为压缩前的逻辑长度硬上限。

此时压缩 goroutine 尚未启动。

### 2. 决定目标 checksum 策略

既有策略保持不变：

1. 请求包含 <code>x-amz-checksum-algorithm</code> 时，计算对应 base algorithm。
2. 否则检查来源 checksum。
3. 来源是 full-object checksum 时，因为逻辑字节不变，可以保留该值。
4. 来源是 multipart composite 时，因为 CopyObject 产生单次 full object，必须用 base algorithm 重算。
5. 来源没有 checksum metadata 时，目标获得默认 CRC64NVME。

只有真正需要计算的分支才调用 <code>AddServerSideChecksumHasher</code>。

### 3. hasher 安装后再启动压缩

目标需要压缩时，逻辑 reader 被捕获为 <code>checksumReader</code>，并作为 <code>newS2CompressReader</code> 的输入。压缩器无法得到任何一个字节，除非该字节先通过逻辑 hasher。

压缩输出拥有独立的存储 <code>hash.Reader</code>。新的 <code>PutObjReader</code> 以存储 reader 为活动 reader，再通过 <code>setChecksumReader</code> 保存逻辑 reader 引用。

~~~text
PutObjReader.Reader          = 压缩或加密后的存储流
PutObjReader.rawReader       = 历史 ETag 路径使用的流
PutObjReader.checksumReader  = 逻辑明文流
~~~

不需要新增导出方法或 package 级抽象。

### 4. 加密阶段继续保持分离

目标加密会包装压缩存储 reader，并可能通过 <code>WithEncryption</code> 替换 <code>PutObjReader.Reader</code>，但不会修改 <code>checksumReader</code>。

因此以下四种存储方式必须得到同一逻辑 checksum：

- 明文；
- 压缩；
- 加密；
- 压缩加密。

checksum metadata 本身需要保护时，既有 metadata encryption function 会在计算完成后加密序列化结果。这保护的是 metadata at rest，不会改变被 hash 的字节。

### 5. EOF 后完成并 fail closed

内部 hash reader 只在来源返回 EOF 后设置 <code>ServerSideChecksumResult</code>。压缩路径中，<code>io.Copy</code> 必须先排空逻辑 checksum reader，随后压缩器才能关闭 pipe。对象 writer 不可能在逻辑 reader 完成 checksum 前观察到压缩流 EOF。

对象层随后验证：

- 结果存在；
- 结果结构有效；
- base algorithm 与 <code>WantServerSideChecksumType</code> 一致。

失败时记录内部不变量错误并中止写入。延迟纠删码清理会在唯一 metadata 发布前删除临时 shard。显式或默认要求 checksum 的操作若返回 HTTP 200 却没有 checksum，是静默正确性损失，不能作为 fallback。

### 6. 不改变盘上格式

验证后的 checksum 继续追加到既有 <code>FileInfo.Checksum</code> 表示。加密目标复用现有 metadata encrypter。HEAD、GET、GetObjectAttributes、复制 metadata 与后续 reader 仍消费同一种表示。

## 为什么这个设计一定成立 {#proof}

### 字节域证明

压缩器接受的每一个字节都来自 <code>checksumReader</code>。hasher 在压缩器构造前安装，所以 digest 输入精确等于压缩器的逻辑输入，而不是输出。

### 完整性证明

压缩器只有在排空逻辑输入并关闭 S2 writer 后，才能关闭输出。对象 writer 必须把输出读到 EOF 才能完成写入。checksum 在逻辑输入 EOF 时完成，而这一时刻先于存储侧可见 EOF。

pipe 自然建立 happens-before 关系，不需要额外 mutex 或旁路信号。定向 race 与随机顺序重复执行验证了实现。

### ETag 证明

压缩 reader 把逻辑 reader 作为 ETag delegate。移动 S3 checksum hasher 不会把 ETag 计算迁到 S2 字节上。永久测试在兼容的未加密场景中，把最终 ETag 与逻辑对象 MD5 独立比较。

### 存储完整性证明

压缩后仍保留存储侧 reader，用于物理流记账与 ETag 委托；纠删码层继续为盘上 shard 写入自己的 bitrot protection。二者都没有被 S3 逻辑 checksum 取代，S3 checksum 也不会被冒充成 shard 完整性机制。

### 加密证明

加密 reader 在逻辑 checksum 之后消费存储流。随机 IV、framing 或 padding 无法影响 checksum。SSE-C 与 SSE-S3 测试同时覆盖仅加密、压缩加密目标；加密来源测试证明 source decryption 也发生在 hash 之前。

### 兼容性证明

对不压缩、不加密的目标，<code>NewPutObjReader</code> 会把 <code>checksumReader</code> 与 <code>rawReader</code> 初始化为同一个 reader，因此 accessor 调整在行为上不变。

补丁没有新增服务端 API，也没有新增存储 marker。生产修改只涉及三个文件，约 30 行新增、15 行删除。较大的测试文件反映兼容性矩阵，不是运行时复杂度。

## 对抗审查拆出的独立修复 {#adjacent}

审查刻意尝试从边界击穿方案，发现了两个真实继承缺陷，但都不属于 checksum 放置本身。

### Metadata-only transform state：#67

CopyObject 在确认是否重写对象字节前，就按当前目标配置推导压缩 metadata。metadata/reference-only self-copy 因而可能给未压缩数据增加压缩标记，或从压缩数据删除标记。

版本化路径还暴露了更深边界：来源 VersionID 未解析时，metadata-only 操作可能落入 <code>PutObject</code>。版本化 SSE-C 密钥轮换随即会写入明文却保留加密 metadata，后续 GET 报 <code>sio: unsupported version</code>。

[PR #69](https://github.com/pgsty/silo/pull/69) 单独修复：

- metadata/reference-only 更新保留来源 transform metadata；
- 只有真实重写字节时才改变压缩标记；
- 版本化 reference copy 使用已经解析的来源版本。

这个问题保持独立，既保护 #63 回滚边界，也避免用一个表面上的三行 guard 掩盖版本化损坏。

### CopyObjectResult checksum 响应：#68

#63 完成后，对象通过 HEAD 与 GET 返回正确 checksum，但成功 CopyObject XML 仍只有 LastModified 与 ETag。

[PR #70](https://github.com/pgsty/silo/pull/70) 增加当前服务端支持的五种 checksum 字段与 ChecksumType，从已提交的目标 ObjectInfo 填充，并把新增导出字段登记到 compatibility baseline。

活跃的 minio-go 已经在 UploadInfo 上拥有 checksum 字段，却会丢弃 CopyObjectResult 值。[上游 PR #2295](https://github.com/minio/minio-go/pull/2295) 连接这些已有字段，不新增公共 API。

## 验证证据 {#verification}

永久测试覆盖：

- CRC32、CRC32C、CRC64NVME、SHA1、SHA256；
- 显式算法与默认 CRC64NVME；
- 明文、压缩、仅加密、压缩加密目标；
- SSE-C 与 SSE-S3；
- 加密来源与压缩来源；
- 未版本化与版本化桶；
- 来源 full-object checksum 保留；
- multipart composite 来源转换为 full-object checksum；
- 原地 self-copy；
- 空数据、精确 4096 字节、4097 字节；
- 超过 8 MiB 的 S2 compression-index 路径；
- 逻辑 ETag 与逐字节正文 round trip；
- 启用 checksum mode 的 HEAD 与 GET；
- 内部 checksum 缺失与算法失配；
- 不变量失败后对象没有发布。

验证门禁包括：

~~~text
聚焦 API 测试
聚焦 race 测试
GOMAXPROCS=8 下 10 轮随机顺序 race
全量 go test ./cmd
禁用 CGO 的 kqueue,dev cmd 测试
go vet
golangci-lint
compatibility 与 rebrand guard
交叉编译
漏洞分析
release-pipeline 快照、SBOM、provenance、包与镜像验证
~~~

同一条回归在未修复基线上为红，在修复树上为绿。

## 运维与发布考虑 {#operations}

### 混合服务器版本

metadata 表示没有变化，所以旧节点能够读取新节点写入的正确 checksum。但滚动升级期间，CopyObject 行为取决于实际处理请求的节点：旧节点仍可能写入错误值，新节点写入正确值。

所有承载 API 的节点都升级后，才能把 CopyObject checksum 行为视为稳定。一次本地构建成功或只升级一个节点，都不构成发布证据。

### 已存在对象

修复只影响此后的复制。SILO 不自动扫描或重写历史 checksum metadata，因为那意味着在没有显式 S3 操作的情况下读取并重写用户数据。

同时满足以下条件的对象值得核验：

- 由受影响版本的 CopyObject 创建；
- 当时目标 key 或内容类型命中压缩配置；
- 对象带有额外 S3 checksum。

使用 checksum mode 取回 checksum，下载逻辑对象，用同一算法独立计算，再比较 Base64 值。

修复时优先把对象复制到新 key，显式指定目标 checksum algorithm，验证完成后再替换原对象。也可以带 <code>x-amz-metadata-directive: REPLACE</code> 做原地复制，但未版本化桶会替换当前值，版本化桶会创建新版本。批量重写前必须确认 retention、legal hold、tag、用户 metadata、加密密钥、容量、复制与回滚要求。

### 合并不等于发布

服务端修复与本文已经合并，文档也已部署，但这仍不能回答“第一个包含修复的二进制版本是什么”。最终 release note 必须明确具体 tag，并独立验证归档、软件包、容器 manifest、checksum、签名、SBOM 与 provenance。

## 跨仓库影响 {#cross-repo}

| 仓库 | 决策 |
| --- | --- |
| pgsty/silo | 拥有 handler、reader 链、对象层不变量、响应 schema 与测试 |
| minio/minio | 已归档上游仍保留原缺陷，无法正常提交服务端上游 PR |
| minio/minio-go | PR #2295 通过已有 UploadInfo 字段返回 CopyObject checksum；等待 maintainer 合并 |
| pgsty/silo-pkg | 无需修改：不拥有 ObjectInfo、PutObjReader 或 CopyObjectHandler |
| pgsty/mc | 无需修改：指定 --checksum 时会主动禁用 server-side copy，改用下载再上传 |
| pgsty/silo-console | 无需直接修改：通过 minio-go 透传 CopyObject，且不解释 checksum 结果 |
| silo.pgsty.com | 负责本文双语设计、发布边界与历史对象指导 |

legacy federated UploadPartCopy checksum 恢复仍由 [#64](https://github.com/pgsty/silo/issues/64) 跟踪。它属于不同 API、响应契约与部署拓扑，绝不能声称已由本次工作解决。

## 最终结果 {#outcome}

修复之所以小，不是因为它省略了问题，而是因为它没有发明新的 checksum 系统，只把原本隐含的职责差异显式化：

~~~text
S3 checksum reader = 逻辑对象契约
storage reader     = 物理表示契约
~~~

一旦二者分离，压缩、加密、ETag、纠删码与 metadata 持久化都可以继续保持流式、独立验证。这就是该方案能够解决已复现缺陷，同时不换来额外 I/O、无界缓冲、新盘上格式或第二套内部抽象的原因。
