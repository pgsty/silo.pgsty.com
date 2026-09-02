---
title: "鉴权前不做 I/O，Header 不授予权限"
linkTitle: "CORS 与复制信任边界"
date: 2026-09-01
lastmod: 2026-09-02
author: "冯若航"
summary: >
  CORS 预鉴权查询曾把任意 URL 路径段变成 metadata I/O 与缓存条目；客户端可控的 replication marker 又会影响 SSE-C 读取、源时间戳、checksum、对象锁、事件与删除语义。本文记录 SILO 的 resident-only CORS 热路径、两级复制信任模型、验签后清洗边界、真实 wire 兼容矩阵与发布前证据。
tags: [设计, 安全, CORS, Replication, SSE-C, 兼容性]
weight: 12
draft: false
url: "/zh/blog/design/cors-replication-trust/"
---

本文记录以 [PR #101](https://github.com/pgsty/silo/pull/101)（`938603458` 至 `04b097fd9`）合并进 SILO 的 CORS 热路径与复制请求信任边界修复。

> **截至 2026-09-02 的状态：** PR #101 已于 2026-09-01 合并进 `main`，并带四个后续提交：Snowball 逐条目信任隔离（`ff44527a3`）、Snowball worker 间保留请求默认值（`ab3ae99ca`）、复制有效性探针校验复制权限（`c9ad74673`）且合成 key 置于规则前缀下（`5db7be4ee`）。随后的发布前清理简化了 CORS 查找：不驻留的桶一律使用全局策略（下文原有的启动期与加载失败 fail-closed 状态已移除），剥头后的请求克隆与原请求共享 trailer，使不可信请求的流式校验和上传照常工作。tag、软件包、镜像、部署与生产验证仍是独立门槛。<br>
> **范围：** S3 handler 之前与内部的 HTTP 请求解释。不修改 S3 wire field、对象格式、bucket metadata 格式、复制协议、加密格式或客户端命令。<br>
> **安全属性：** CORS 预鉴权处理不执行对象层 I/O；header 本身永远不授予复制语义；SSE-C 密文路径与 replica-only metadata 必须同时通过身份认证与对应复制权限检查。

## 太长不看（TL;DR） {#tldr}

两个问题表面上互不相干：

1. `Origin` header 会让最外层 CORS middleware 把 URL 第一段当成桶，在鉴权前同步加载它的 metadata；
2. `X-Minio-Source-Replication-Request` 只要存在，下游代码就会把请求当作内部复制。

它们共享同一个设计错误：**不可信的请求形态在越过授权边界之前，就获得了昂贵或特权化的内部含义。**

修复建立了两个不变量：

```text
鉴权之前：只做廉价解析，绝不加载 bucket metadata
鉴权之后：只计算一次信任结论，下游只消费这个结论
```

对于 CORS，外层 middleware 只读已经 resident 的内存 metadata。对于复制，handler 先认证原始签名请求，再检查对应复制权限，最后把私有信任结论写入 request context。不可信内部 header 只在验签完成后剥离。真正的权威是 context 中的决定，而不是“是否成功删掉了某个 header”；option builder、加密路径、对象锁、事件与 metadata 持久化都只读取这一决定。

## 故障 A：CORS 预鉴权资源放大 {#cors-failure}

`corsHandler` 包在完整服务器 router 的最外层。任何携带 `Origin` 的请求都会在 S3 鉴权、请求有效性检查与普通 API 限流之前到达这里。

Per-bucket CORS 最初调用普通 bucket metadata getter：

```text
携带 Origin 的请求
  -> URL 第一段变成“桶名”
  -> GetCorsConfig
  -> GetConfig cache miss
  -> 读取 .metadata.bin
  -> 探测十个 legacy config 路径
  -> 缓存一条默认 BucketMetadata
```

`.metadata.bin` 不存在时，loader 会按兼容要求继续寻找 legacy 配置；什么都没找到后，它返回一条合法的空 metadata，而不是 `NoSuchBucket`。通用 getter 随后把这条记录写入 `metadataMap`。

未认证客户端只需不断变化看似合理的名字，就能让每个新值产生两种代价：

- 在普通 limiter 之前反复执行纠删码/对象 metadata 读取；
- 增长内存中的 bucket metadata map。

只校验桶名不能修复：攻击者可以生成近乎无限的、语法合法但不存在的桶名。分布式部署会在 15 分钟 metadata refresh 中最终清理 stale entry；单节点不会启动这条 refresh loop，因此合成条目会一直存在到重启。

## 故障 B：marker header 变成了权威 {#replication-failure}

SILO 及其 MinIO-compatible 客户端使用内部 header，在复制期间保留源状态。其中最重要的 marker 是：

```text
X-Minio-Source-Replication-Request: true
```

修复前，多条路径把 header 存在，或未经授权的原始字符串值，当成复制请求证明。影响远不止 metadata extraction：

- SSE-C 对象的 `GET` 可以设置 `NoDecryption`，让只有普通读取权限、没有 customer key 的调用者取得密文；
- source ETag 与 modification time 可以覆盖服务器生成值；
- source tagging、retention、legal-hold timestamp 可以进入 last-writer-wins 比较；
- 仅凭 marker 就可以接受已经过去的 object-lock retention date；
- delete marker 的 identity 与 modification time 可以由调用者提供；
- 成功对象事件可以被抑制；
- multipart completion 可以注入 actual size 与加密 checksum metadata；
- 普通 PUT、COPY 或 POST-policy metadata extraction 可以持久化 `X-Amz-Replication-Status`。

此前的 [CVE-2026-34204 修复](/zh/blog/security/cve-2026-34204/) 已经正确阻止普通 PUT/COPY 导入可能让对象不可读的 replication SSE metadata。但它尚未为 marker、source field、event state、object-lock exception 与 multipart completion metadata 的所有消费者提供同一个权威。

## 最终设计 {#design}

### 一个精确 marker，两级信任 {#trust-levels}

只有 marker 恰好出现一次、且值恰好为小写 `true` 时，才承认其形态。重复值、大小写变化与任何其他值都不可信。

Handler 随后派生两个相关结论：

| 决定 | 必须满足 | 可以启用的语义 |
| --- | --- | --- |
| `trusted` | 原始请求完成认证；非匿名主体；精确 marker；目标资源上具有 `s3:ReplicateObject` 或 `s3:ReplicateDelete` | source ETag/MTime 与 source timestamp；actual size 与加密 checksum 传递；event 与重复复制抑制；复制删除的 pool/version pinning |
| `replicaTrusted` | `trusted`，再加原始请求状态为 `REPLICA`，或 multipart upload 已保存 `REPLICA` 状态 | replica status 持久化；replication SSE sealed-key 导入；SSE-C 密文/NoDecryption 路径；replica-only 对象锁行为 |

必须拆成两级，因为真实 wire 并不会在每个合法复制请求上重复 `X-Amz-Replication-Status: REPLICA`。

接收端遵守以下矩阵：

| 输入形态 | 结果 |
| --- | --- |
| 没有 marker | 普通 S3 操作 |
| marker 但没有复制权限 | 忽略内部字段，按普通语义继续执行 |
| `REPLICA` 但没有复制权限 | `403 AccessDenied` |
| 精确 marker + 复制权限，没有 `REPLICA` | 只有 `trusted` |
| 精确 marker + 复制权限 + `REPLICA` | 同时获得 `trusted` 与 `replicaTrusted` |

未授权 `REPLICA` 必须明确返回 `403`，不能静默降级成一个会再次被复制的新普通对象。

### 先认证原始请求，再做清洗 {#signature-boundary}

SigV4 会签名请求 header。如果在鉴权前删除内部 header，canonical request 会发生变化，原本有效的签名将变成 `SignatureDoesNotMatch`。

因此顺序是硬约束：

```text
原始请求
  -> 既有 signature/authentication path
  -> 普通 S3 action 授权
  -> replication action 授权
  -> 计算 trusted / replicaTrusted
  -> 把决定写入 request context
  -> clone 并剥离不可信内部字段
  -> option 解析、加密、对象锁、存储、事件
```

Audit logger 仍保留原始请求。Effective request clone 保留公开 S3、SSE、checksum、object-lock、copy-source、proxy 与 replication validity header；只剥离内部 source/replication control，包括 source ETag/MTime/delete-marker/timestamp、replication SSE state、actual object size、加密 checksum 传递，以及作为内部请求控制使用的 `X-Amz-Replication-Status`。

Header stripping 只是纵深防御。所有特权消费者都读取私有 context 决定或显式 Boolean，不会再靠检查 clone 来猜测信任。

### Replica status 不是普通用户 metadata {#replica-status}

`X-Amz-Replication-Status` 是一个 S3 response header，MinIO-compatible server 同时把它用作内部请求控制。它不再属于通用 supported-request-metadata 列表。

普通 PUT、COPY、multipart initiation、Snowball/PAX extraction 与 POST policy 不能仅凭提交字段就持久化它。接收端只在 `replicaTrusted` 分支显式写入 `REPLICA`。

这同时关闭了一条隐蔽的 POST-policy 路径：form field 曾经可以写入 `REPLICA`，让对象绕开正常复制调度，而 POST principal 根本没有复制权限。

### 对象锁接收显式决定 {#object-lock}

Object-lock parser 过去只要看到原始 marker header，就会接受已经过去的 retention date。现在它从 `replicaTrusted` 接收显式的 `allowPastRetainDate`。

外围 handler 在判断 replica 能否覆盖既有 compliance/legal-hold version 时也使用同一个决定。可复用的 object-lock package 不再依赖内部 HTTP header。

## 真实复制 wire 矩阵 {#wire-matrix}

设计核对的是服务器 `go.mod` 实际选择的 silo-go v7.3.1 emitter，而不是注释或上游文档中的假设。

| 操作 | Marker | 本请求携带 `REPLICA` | 接收端决定 |
| --- | --- | --- | --- |
| 普通对象复制 `PutObject` | 是 | 是 | `replicaTrusted` |
| 复制 `NewMultipartUpload` | 是 | 是 | 保存可信 MPU replica provenance |
| 复制 `PutObjectPart` | 是 | 否 | `trusted`；只有已存 MPU 状态为 `REPLICA` 才获得 `replicaTrusted` |
| 复制 `CompleteMultipartUpload` | 是 | 否 | `trusted`；保留 source ETag/MTime、actual size 与加密 checksum |
| CopyObject metadata replication | 是 | 是 | `replicaTrusted` |
| 复制 `RemoveObject` | 是 | 是 | 具有 `s3:ReplicateDelete` 的 `replicaTrusted` |
| Batch replication PUT/Complete | 是 | 否 | `trusted`；目标凭据必须拥有 `s3:ReplicateObject` |
| Proxy/readiness/validity probe | 独立 probe header | marker 不授予权限 | 保持 probe 行为；本修复不会剥离这些 header |

如果要求所有可信请求都带 `REPLICA`，PutPart、multipart completion 与 batch replication 会立即回归；如果相信所有 marker，则漏洞会原样重现。已保存的 multipart provenance 在加密 raw part 上连接了这两个要求。

## CORS resident-only 状态机 {#cors-state-machine}

最外层 CORS middleware 必须比即将进入的请求更便宜。它现在调用专用 resident-only getter，只拿一次读锁并读取内存状态。

| Bucket metadata 状态 | CORS 结果 | 对象层工作 |
| --- | --- | --- |
| resident，per-bucket CORS 合法 | 应用桶级规则 | 无 |
| resident，没有 CORS 文档 | 使用 global CORS fallback | 无 |
| resident，持久化 CORS 非法 | fail closed；继续处理请求但不加 CORS header，并只记一次日志 | 无 |
| 不驻留：启动加载中、metadata 加载失败、reserved、非法、内部或未知名字 | global fallback | 无 |

除驻留 map 之外不查任何状态。一个尚未驻留的真实桶——启动加载仍在进行，或其 metadata 加载失败——在下一轮 refresh 加载它之前使用全局策略。本修复的第一版在这些状态下 fail closed；发布前清理移除了它：CORS 是浏览器响应策略而非授权边界，普通 S3 认证与 bucket policy 仍然生效，fail closed 只会在启动期弄坏浏览器客户端。

## 被否决的方案 {#alternatives}

| 方案 | 为什么否决 |
| --- | --- |
| 在旧 CORS getter 前校验桶名 | 合法但不存在的名字仍提供无限攻击空间，且继续触发预鉴权 I/O |
| 加载 CORS 前调用 `GetBucketInfo` | 只是把十一轮 metadata 读取换成每个攻击者名字至少一次未限流 backend operation |
| 给每个 negative result 做 TTL cache | 只限制持续时间，不限制攻击者 cardinality 与第一次 I/O 放大 |
| 鉴权前剥离 replication header | 破坏 SigV4 canonical request 验证 |
| 拒绝任何携带内部 marker 的请求 | 把过去被忽略的多余 header 扩大成普遍客户端失败，并破坏合法 marker-only 复制调用 |
| 要求所有可信调用都携带 `REPLICA` | 破坏复制 PutPart、CompleteMultipartUpload 与 batch replication wire |
| 每个 handler 各自重新检查 raw header | 重建不一致信任规则，未来新增消费者也极易漏掉 |
| 只在 `ObjectOptions` 放 Boolean，event/object lock 仍看 header | 产生两个可能互相矛盾的权威，原漏洞类别仍然存在 |

## 实现边界 {#implementation}

最终改动按层组织：

1. 一个小型 request-trust 模块定义精确 marker 解析、复制授权、私有 context state 与鉴权后的 effective request；
2. object option builder 只有在调用方提供可信状态时才解析 source field；
3. `DecryptObjectInfo`、event request parameter、multipart completion、delete option 与 object lock 消费同一个决定；
4. handler 在既有 authentication path 之后立即计算信任；
5. multipart part 把当前请求信任与已保存 MPU replica provenance 结合；
6. 通用 metadata extraction 不再接受 replica status；
7. CORS middleware 使用独立的 resident-only accessor，永远不调用 load-on-miss getter。

对象层 API 无需再猜测 HTTP trust。内部程序化调用者直接构造的 `ObjectOptions{ReplicationRequest: true}` 不受影响。

## 验证与对抗审查 {#verification}

回归覆盖包括：

- 数百个不同的合法缺失桶名，actual/preflight 两类 CORS 请求，metadata read 为零且 map 不增长；
- Console、reserved、invalid、startup、内部 namespace 与非法持久化 CORS；
- 最小权限 SSE-C GET、HEAD、GetObjectAttributes，对正确、缺失、大小写错误与未授权 marker 的处理；
- marker-only batch 风格 PUT 只有在具备 `s3:ReplicateObject` 时才保留 source ETag/MTime；
- 未授权 `REPLICA` PUT/DELETE 返回 `403`；
- POST policy 无法伪造 replica status；
- object-lock past-date 在有无 replica trust 时的差异；
- marker-only CopyObject 携带 SSE-C source header 时复制明文而不是密文；
- 普通 SSE-C MPU 上的伪 marker 失败，不会写入 raw byte；
- 一条真实的进程内 SSE-C multipart 复制链：加密源、raw ciphertext part、可信 replica initiation、marker-only PutPart/Complete，以及用原密钥精确恢复明文。

最终本地 tree 通过定向与 race 测试、完整 `cmd` suite、对象锁测试、vet、build 与 diff check。

另一轮黑盒测试用候选二进制启动两个 TLS-enabled SILO 实例并启用真实 site replication，验证：

- SSE-C 4 KiB 对象；
- SSE-C 12 MiB、三个 part 的 multipart 对象；
- SSE-C CopyObject；
- replicated delete marker。

源/目标 ETag、size、version ID、SSE-C key MD5、解密后 SHA-256 与 delete-marker version ID 均一致，目标报告 `REPLICA`。

前两轮 Fable 5 评审先纠正 marker-only batch 与 multipart 调用的信任模型，再审计实现。最终独立 Claude Code Opus 5 给出 **GO**，没有 P0/P1，并独立重跑 build、vet、race、object-lock 与完整 `cmd` 测试。

## 兼容性与运维影响 {#impact}

- **普通客户端：** 请求无需改变；不可信内部 header 现在会被忽略，而不是获得内部语义。
- **未授权 replica 声明：** 携带 `X-Amz-Replication-Status: REPLICA` 的请求现在统一返回 `403`；过去部分 multipart 子路径没有这条一致检查。
- **Batch replication：** 目标凭据必须包含 `s3:ReplicateObject`，参见 [batch replication requirements](/zh/administration/batch-framework-job-replicate/)。缺失权限时，接收端会把 marker-only write 当作普通写入，不保留 source ETag/MTime。
- **SSE-C：** 普通读取仍需要 customer key；授权 replica read 可以使用保留加密字节所需的 raw ciphertext path。
- **事件：** 只有可信复制才抑制 replica creation/access event；伪 marker 不再让事件静默消失。
- **对象锁：** replica exception 来自权限决定，不再来自 header。
- **性能：** CORS 移除了预鉴权 backend work。可信写入增加的是复制契约本来就要求的 policy check，不增加对象数据 pass。
- **滚动升级：** wire 与 storage format 不变。新 receiver 执行信任边界；旧 receiver 在升级前仍保留旧 header 漏洞。滚动窗口中节点的 per-bucket CORS 行为可能不同。
- **回滚：** 修复版本写入的数据仍可被旧版本读取，但 rollback 会重新打开两个信任缺陷并恢复预鉴权 metadata load。

## 残余风险与后续 {#residual-risks}

- 当 marker-bearing request 缺少复制权限时记录限频诊断；安全的 ordinary fallback 否则容易被误诊为 ETag/MTime 不一致。
- Replication validity probe 现在会校验目标凭据所需的复制权限，并把合成的校验 key 放在规则前缀之下（`c9ad74673`、`5db7be4ee`）。
- 本次覆盖已命名的 source/replication header。未来任何内部控制都仍需回答同一个问题：哪一个认证后的决定允许这个客户端值获得内部含义？

## 结论 {#conclusion}

看起来像内部字段的 header 仍然是客户端输入；看起来像桶名的 URL 段也仍然是攻击者输入。耐久修复是阻止两者意外成为权威：

> 鉴权之前不做 backend work；鉴权之后只派生一次 trust，并把决定而不是声明传给下游。

这条规则并不只属于 CORS 或 replication。当廉价的公开请求语法与昂贵或特权化的内部状态相遇时，未来 SILO handler 都应该保持这条边界。
