---
title: "未签名的 Header 不属于请求"
linkTitle: "签名头覆盖边界"
date: 2026-09-09
lastmod: 2026-09-11
author: "冯若航"
summary: >
  一个只授权写单个对象的 presigned/签名 PUT，可被转化为读取签名密钥可及的任意对象的服务端复制——因为 SigV4 验签只遍历"签名头名单"，从不检查真正到达的 x-amz-* 头，而路由又仅凭一个未签名的 x-amz-copy-source 头就派发到 CopyObject。本文记录 SILO 的未签名头拒绝边界、载荷哈希豁免与可信签名年龄的计算、PutObjectTagging 注入时序调整、跨签名模式的适用范围与发布前证据。
tags: [设计, 安全, SigV4, CopyObject, Presigned, 兼容性]
weight: 6
draft: false
url: "/zh/blog/design/signed-header-coverage/"
---

本文记录 SILO 的未签名头覆盖修复，核心提交为 [`123325430`](https://github.com/pgsty/silo/commit/123325430)，已通过 [PR #173](https://github.com/pgsty/silo/pull/173) 合并，台账编号 `SN-2026-011`。该问题由 Oren Yomtov 针对已发布版本报告，并在本地两条签名路径上均已复现。

> **2026-09-11 状态：** 原始修复已推送，并通过 [PR #173](https://github.com/pgsty/silo/pull/173) 合并。下文的后续签名与正文校验修复也已通过 [PR #177](https://github.com/pgsty/silo/pull/177) 合并，8 项 PR 检查全部通过。源码验证与正式发布分别计数：当前已发布的 9 月 3 日 Server 版本尚未包含这些修复。<br>
> **范围：** SigV4 请求头覆盖、策略输入一致性与正文摘要校验。不改变 S3 字段名称、对象或桶元数据格式、复制协议、加密格式和客户端命令。<br>
> **安全性质：** 客户端未签名的 `x-amz-*` 操作头不能改变已授权请求；策略求值与正文校验使用实际参与签名的有效输入。

## 太长不看（TL;DR） {#tldr}

一个 presigned `PUT` URL 只签一个头：`host`。SILO 会确认签名头名单里点名的每个头都已到达，却从不遍历*真正*到达的头，于是名单之外的 `x-amz-*` 头被照单接受并使用。`cmd/api-router.go` 仅凭 `x-amz-copy-source` 头就把任意 `PUT` 派发到 `CopyObjectHandler`。两者相加，把"只能写某个对象"的授权，变成了**以签名者身份读取签名密钥可及的任意对象的服务端复制**——一个混淆代理（confused deputy）。当该头被排除在 `SignedHeaders` 之外时，Authorization 头路径也是同样的行为。

修复只确立一条不变式：

```text
就 x-amz-* 语义而言，签名头名单“就是”整个请求。
任何不被它覆盖的 x-amz-* 头，都在 handler 运行前被拒绝。
```

这与 AWS S3 一致——AWS 对同一请求返回 `AccessDenied`（“There were headers present in the request which were not signed”）。签名代码是逐字节继承自上游 `minio/minio` 的，因此每个更早的 SILO 发布版本、以及上游本身，都带有这个缺口。

## 缺陷：覆盖缺口 {#failure}

`cmd/signature-v4-utils.go` 里的 `extractSignedHeaders` 遍历*签名头名单*，逐个从请求（或 query string）里取值。它证明了"承诺过的头都在"，却从不问反方向的问题——*到达的每个 `x-amz-*` 头，是否都在名单里*？

唯一遍历到达头的地方 `checkMetaHeaders`，只匹配 `X-Amz-Meta-` 前缀，且只被 presigned 路径（`doesPresignedSignatureMatch`）调用。Authorization 头验签器（`doesSignatureMatch`）没有任何等价调用。于是未签名的 `x-amz-copy-source`——或任何其它塑造操作的 `x-amz-*` 头——在两条路径上都能通过：

```text
presigned PUT（SignedHeaders=host）  ->  加一个未签名的  x-amz-copy-source: /src/secret
  -> 路由看到 x-amz-copy-source  -> CopyObjectHandler
  -> 复制以签名者身份运行，读取了 URL 从未点名的桶
```

本地复现：对照组 `PUT` 返回 `200` 且响应体为空；同一 URL 加上那一个未签名头返回 `200`，响应是一个 `CopyObjectResult`，其 ETag 正是受害对象的 md5，且目标处回读出的就是受害者的字节。若目标桶本就允许匿名 `GetObject`，被复制进去的私有字节此后无需任何凭据即可读取。

## 溯源 {#provenance}

这个缺口继承自上游 MinIO，并非 SILO 引入。`cmd/signature-v4-utils.go` 里的 SigV4 验签器、以及 `cmd/signature-v4.go` 里的 Authorization 头路径 `doesSignatureMatch`，都是可追溯到 2016 年的原始 MinIO 代码；`cmd/api-router.go` 里由头驱动的 CopyObject 派发可追溯到 2019 年。唯一遍历到达头的例程 `checkMetaHeaders`，是上游在 2023-07-27 通过 [minio/minio#17737](https://github.com/minio/minio/pull/17737)（`535f97ba6`）加入的。也就是说，上游其实已经意识到了这一类问题——未签名的头必须与签名集合相符——却把检查限定在 `X-Amz-Meta-` 前缀和 presigned 路径上，把 `x-amz-copy-source` 和整条 Authorization 头路径都漏在外面。这个窗口在 MinIO 的 S3 层里一直开着。

在未签名头修复之前，SILO 对 `cmd/signature-v4-utils.go` 的改动是一行依赖路径迁移：`9b11dc946` 将 `policy` 导入改为 `pgsty/silo-pkg/v3`。存在缺陷的验签行为来自上游。原始修复（`123325430`）以及 [PR #177](https://github.com/pgsty/silo/pull/177) 的后续修复改变了这条边界。存在缺陷的代码早于 SILO 的分叉基线——即上游 2025-12-03 的 “maintenance mode” 提交，第一个 SILO 发布版本正是从那里切出的。

上游 `minio/minio` 自那次交接起即处于归档状态，没有上游维护者能接收补丁。SILO 原样继承了这份代码，也是唯一修复它的地方——正如安全台账对其它继承性发现的记录方式。

## 修复 {#repair}

`checkMetaHeaders` 更名为 `checkUnsignedHeaders`，把匹配前缀从 `X-Amz-Meta-` 拓宽到整个 `X-Amz-`，并在**两条**路径（presigned 与 Authorization 头）上都调用。不被签名集合覆盖的头，会在任何 handler 逻辑运行前以 `ErrUnsignedHeaders` 拒绝。

有四个决策界定了这条边界的确切位置。每个都有一个看似合理、但因具体理由被否掉的替代方案。

### 判成员资格，而非判值相等 {#membership}

继承来的检查比较的是 `signedHeadersMap.Get(k) == val[0]`。对一个不在签名集合里的头，`Get` 返回空串，于是*首值*为空的头会比出相等而通过。像 `X-Amz-Copy-Source: ["", "/src/secret"]` 这样的多值头，就能借此把未签名的 copy-source 从值相等检查下夹带过去。修复改为判**成员资格**（该头是否在签名集合中）。签名头的值本就被签名绑定，所以值相等从来不是关键性质；在名单里才是。

### 豁免 `X-Amz-Content-Sha256` {#exempt-content-sha256}

`X-Amz-Content-Sha256` 可以不列入 `SignedHeaders`，因为有效载荷哈希已被单独绑定到规范请求。预签名请求优先使用 query 值，仅在 query 缺失时回退到 header；显式的 `UNSIGNED-PAYLOAD` 仍然有效。[PR #177](https://github.com/pgsty/silo/pull/177) 让策略条件使用同一个有效值，同时保留 header 存在性的语义，并补齐通用认证路径中 header-only 预签名请求的正文摘要校验。这项豁免不允许策略求值或正文校验另取一个不同的值。

### 从签名日期计算签名年龄 {#exempt-signature-age}

原始修复曾豁免验签后写入的内部 scratch 头 `x-amz-signature-age`，但 PUT 和 UploadPart 的授权发生在验签之前，这个值建立得太晚。[PR #177](https://github.com/pgsty/silo/pull/177) 改为直接从已签名的 `X-Amz-Date` 计算 `s3:signatureAge`，并删除 scratch 头、对应常量和豁免。伪造日期会导致验签失败；客户端提交旧名称的未签名头会被拒绝。验签不再修改请求头，重复验签仍然幂等。

### 把 `X-Amz-Tagging` 注入挪到鉴权之后 {#tagging-reorder}

`PutObjectTaggingHandler` 会从请求*体*派生出一个 `X-Amz-Tagging` 头供策略条件读取，此前是在 `authenticateRequest` *之前*注入的。有了拓宽后的检查，这个服务端合成、客户端从不签名的头，会被当作未签名而拒绝。注入现在改到验签之后、授权之前——授权仍然拿得到它来做策略条件。**否掉的替代方案：** 像豁免 content-sha256 那样，直接整体豁免 `X-Amz-Tagging`。那会允许客户端在任意签名/presigned 写请求上，通过一个未签名头设置对象标签，重新打开这一类缺陷的一个缩小版本。

## 跨签名模式的适用范围 {#scope}

- **Authorization 头（签名）与 presigned SigV4：** 两者现均已强制。这是可达的路径。
- **Streaming SigV4：** 对复制不可达。`authenticateRequest` 对 streaming 鉴权类型返回 `ErrSignatureVersionNotSupported`，因此 `CopyObjectHandler` 的 `checkRequestAuthType` 会在任何复制发生前就拒绝一个 streaming 签名的复制。检查没有加到 streaming 验签器上，因为派发根本到不了那里；有回归测试钉住这一拒绝。
- **SigV2：** 不受影响。V2 的规范化本就把 `x-amz-*` 头折进 string-to-sign，因此新增一个 `x-amz-*` 头会改变算出的签名，被当作签名不匹配拒绝。

## 状态码：400 还是 403 {#status-code}

AWS 对未签名头返回 `403 Forbidden`；SILO 返回 `400 AccessDenied`（`ErrUnsignedHeaders`），继承自上游。两种方式都拒绝了攻击，错误 `Code` 字符串也一致，仅 HTTP 状态码不同。把它提升到 `403` 是 `cmd/api-errors.go` 里一行的改动，同时也会改变既有的 meta 头拒绝路径。此处把它留作一个刻意的、可逆的选择，而非在安全修复里悄悄夹带，因为它对既有的未签名 meta 头路径是一个行为变更，且并非关闭该漏洞所必需。

## 测试 {#tests}

有几个既有测试先构造一个签名请求，然后*在签名之后*才设置 `x-amz-copy-source`、`x-amz-copy-source-range` 或 `x-amz-metadata-directive`——也就是说，它们依赖的正是本修复所移除的行为。它们现在改为在设置这些头之后用 `signRequestV4` 重新签名，这正是每个真实 S3 客户端的做法。`signRequestV4` 会把 `Authorization` 头排除在自己的签名集合之外，因此重签是安全的。新增覆盖包括 `checkUnsignedHeaders` 的单元用例（含空首值与两处豁免用例）以及 `TestPresignedVerifyIdempotent`——对同一个 presigned 请求验签两次。

## 证据 {#evidence}

- 一个构建出的服务端在 presigned 与 Authorization 头两条路径上复现了混淆代理，修复后两者均被拒绝，而对照组 `PUT`、真实的 `minio-go` `CopyObject`、带用户元数据与标签的 `PutObject`、以及基于请求体的 `PutObjectTagging` 全部照常工作。
- `go test ./cmd/` 在修复树上通过；`gofmt`、`gofumpt`、`vet` 干净。
- 对抗性评审（第一轮）独立发现了初稿中的三个缺陷——scratch 头导致的验签不幂等、空首值绕过、以及对未签名 `x-amz-content-sha256` 的过度拒绝——均在上文处理，并通过把评审方自建的对抗测试套件跑在最终树上得到确认。
- 对抗性评审（第二轮，针对已提交的修复）未发现回归，并确认重签后的测试保留了原意：无效 access key 仍返回 `InvalidAccessKeyId`，错误 SSE-C key 在签名通过后仍返回 `403`。它另外发现了三处*相邻的、既有的*缺口——在父提交上同样失败，且不在本次改动范围内——记录在下文后续项。

## 兼容性与运维 {#impact}

- **普通客户端：** 请求无变化。每个 AWS SDK、`minio-go`、`mc` 本就会对它发送的 `x-amz-*` 头签名。
- **未签名的 `x-amz-*` 头：** 现在以 `AccessDenied` 拒绝，与 AWS 一致。一个不签名就加上此类头的客户端，本就在 SigV4 契约之外。
- **滚动升级：** wire 与存储格式不变。已升级节点强制该边界；仍跑旧版本的节点在升级前仍然暴露，因此滚动窗口内不同节点行为可能不同。
- **回滚：** 修复版本写入的数据仍可被旧版本读取，但回滚会重新打开混淆代理。

## 残余风险与后续 {#residual-risks}

- **发布交付：** 源码修复与公开工程记录不代表已发布的二进制或镜像包含修复；需要单独核对所选发布版本与制品。
- **CVE：** 报告人申请了一个；在 CVE 分配前，该发现以稳定的 fork 本地编号 `SN-2026-011` 追踪。
- **状态码选择：** 上文 `400` 与 `403` 的取舍仍开放。
- **相邻签名修复：** [PR #177](https://github.com/pgsty/silo/pull/177) 处理重复复制源头的歧义、签名年龄的授权时序和载荷哈希策略有效值，并补齐另行复现的 header-only 预签名正文摘要校验缺口。回归覆盖普通签名与预签名、上传验签前的策略求值，以及真实 HTTP 桶策略篡改。这些后续项与原始 `SN-2026-011` 分开记录；合并和发布状态见页首。
- **通用问题：** 本次修复覆盖的是 `x-amz-*` 请求头。任何未来让请求语法去选择操作的控制项，都必须回答这次同样的问题——*在这个值被允许具有任何含义之前，它是否被签名覆盖了？* 上面那处重复头缺口是同一问题的另一副面孔：签名所绑定的值，与处理器所消费的值，必须是同一个。

## 结语 {#conclusion}

签名即请求。`x-amz-*` 头所声称的一切，在签名覆盖它之前都只是声称：

> 确认"承诺过的头都到了"，不等于确认"到了的头都被承诺过"。在 handler 运行前，在 handler 可被到达的每一条签名路径上，拒绝任何未签名的 `x-amz-*` 头。
