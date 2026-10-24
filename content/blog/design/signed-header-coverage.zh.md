---
title: "SigV4 签名头覆盖边界：拒绝未签名的 x-amz-* 请求头"
linkTitle: "签名头覆盖边界"
date: 2026-09-09
lastmod: 2026-09-16
author: "冯若航"
summary: >
  仅授权写入单个对象的预签名或普通签名 PUT 请求，此前可被转化为读取签名密钥可访问的任意对象的服务端复制——原因在于 SigV4 验签只正向遍历签名头列表，未反向检查实际收到的 x-amz-* 请求头，而路由层又仅凭未签名的 x-amz-copy-source 头将请求分发至 CopyObject。本文记录 SILO 的未签名头拒绝边界、载荷哈希豁免与可信签名年龄计算、PutObjectTagging 注入时序调整、跨签名模式的适用范围与验证证据。
tags: [设计, 安全, SigV4, CopyObject, Presigned, 兼容性]
weight: 6
draft: false
url: "/zh/blog/design/signed-header-coverage/"
---

本文记录 SILO 的未签名请求头覆盖修复（核心提交 [`123325430`](https://github.com/pgsty/silo/commit/123325430)，经 [PR #173](https://github.com/pgsty/silo/pull/173) 合入，安全通告编号 `SN-2026-011`）以及 [PR #177](https://github.com/pgsty/silo/pull/177) 中的后续签名与载荷校验修复（安全通告编号 `SN-2026-012`）。上述修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布。该漏洞由 Oren Yomtov 报告，并在本地预签名与 `Authorization` 请求头两条 SigV4 路径上复现。

## 核心结论（TL;DR） {#tldr}

预签名 `PUT` URL 可以只对 `host` 一个请求头签名。此前 SILO 只校验签名头列表（`SignedHeaders`）中声明的请求头是否已到达，却未反向检查请求实际携带的全部请求头，导致列表之外的 `x-amz-*` 请求头被直接接受并参与业务处理。与此同时，`cmd/api-router.go` 仅凭请求中存在 `x-amz-copy-source` 头，就会将任意 `PUT` 请求分发至 `CopyObjectHandler`。两处逻辑叠加后，原本仅授权写入单个对象的预签名 URL，可被攻击者转化为**以签名者身份读取该密钥可访问的任意对象的服务端复制操作**（混淆代理，confused deputy）。当 `Authorization` 头签名请求未将 `x-amz-copy-source` 纳入 `SignedHeaders` 时，同样会触发该问题。

本次修复确立了一条核心不变式：

```text
在普通签名与预签名 SigV4 路径中，收到的所有 x-amz-* 请求头均须在签名覆盖范围内；
唯一豁免项为通过规范请求单独绑定和校验的 X-Amz-Content-Sha256。
```

这一行为与 AWS S3 一致——AWS S3 对携带未签名 `x-amz-*` 头的同类请求同样返回 `AccessDenied`（“There were headers present in the request which were not signed”）。

## 缺陷机制：单向覆盖缺口 {#failure}

`cmd/signature-v4-utils.go` 中的 `extractSignedHeaders` 遍历*签名头列表*，按名称逐一从请求头（或 query 参数）中提取对应值。这仅验证了签名声明的请求头均已存在，却遗漏了反向检查：*实际收到的每一个 `x-amz-*` 请求头是否都包含在签名头列表中？*

此前代码中唯一遍历实际到达请求头的函数是 `checkMetaHeaders`，但它仅匹配 `X-Amz-Meta-` 前缀，且只在预签名路径（`doesPresignedSignatureMatch`）中调用；`Authorization` 头验签路径（`doesSignatureMatch`）则完全没有对应检查。因此，未签名的 `x-amz-copy-source`（或任何其他影响操作语义的 `x-amz-*` 请求头）在两条路径上均能畅通无阻：

```text
预签名 PUT（SignedHeaders=host）  ->  附加未签名的 x-amz-copy-source: /src/secret
  -> 路由层检测到 x-amz-copy-source  -> 分发至 CopyObjectHandler
  -> 以签名者身份执行服务端复制，读取预签名 URL 从未授权的源存储桶
```

本地复现结果：对照组普通 `PUT` 返回 `200` 且响应体为空；对同一预签名 URL 附加一个未签名的 `x-amz-copy-source` 头后，请求同样返回 `200`，但响应体变为 `CopyObjectResult`（其 ETag 即为源对象的 MD5），从目标对象回读即可拿到源对象的完整内容。若目标存储桶本身允许匿名 `GetObject`，攻击者无需任何凭据即可直接读取被复制出来的私有对象。

## 历史溯源 {#provenance}

该缺陷继承自上游 MinIO。`cmd/signature-v4-utils.go` 中的 SigV4 验签逻辑与 `cmd/signature-v4.go` 中的 `doesSignatureMatch` 可追溯至 2016 年；`cmd/api-router.go` 中基于请求头分发 `CopyObject` 的路由规则可追溯至 2019 年。上游曾在 2023-07-27 通过 [minio/minio#17737](https://github.com/minio/minio/pull/17737)（提交 `535f97ba6`）引入 `checkMetaHeaders`，当时已注意到未签名请求头需与签名集合保持一致，但将该检查局限在 `X-Amz-Meta-` 前缀与预签名路径，遗漏了 `x-amz-copy-source` 等操作控制头以及整条 `Authorization` 头验签路径。

在本次修复前，SILO 对 `cmd/signature-v4-utils.go` 仅做过一行依赖导入路径调整（`9b11dc946` 将 `policy` 包导入迁移至 `pgsty/silo-pkg/v3`）。核心修复（`123325430`）与 [PR #177](https://github.com/pgsty/silo/pull/177) 的后续加固完整闭合了这一边界。

## 修复设计 {#repair}

修复将 `checkMetaHeaders` 重命名为 `checkUnsignedHeaders`，将匹配前缀从 `X-Amz-Meta-` 扩展至整个 `X-Amz-` 命名空间，并在**预签名**与 **`Authorization` 头**两条路径上统一调用。任何未被签名集合覆盖的 `x-amz-*` 请求头，都会在进入业务 handler 之前被直接拒绝并返回 `ErrUnsignedHeaders`。

以下四项设计决策界定了具体的检验边界：

### 检查集合成员资格 {#membership}

原先的 `checkMetaHeaders` 采用 `signedHeadersMap.Get(k) == val[0]` 比较值是否相等。对于不在签名映射表中的请求头，`Get` 会返回空字符串 `""`；一旦攻击者构造首个元素为空串的多值请求头（例如 `X-Amz-Copy-Source: ["", "/src/secret"]`），`val[0]` 同样为空串，就能绕过相等比较并将第二个未签名的复制源路径注入后端。修复改为直接检查键是否存在于 `signedHeadersMap` 中：只要请求头已纳入签名列表，其具体取值自然受签名摘要保护，验签阶段只需判定集合成员资格。

### 豁免 `X-Amz-Content-Sha256` {#exempt-content-sha256}

客户端发送 `X-Amz-Content-Sha256` 时可以不将其列入 `SignedHeaders`，因为有效载荷哈希已作为独立字段写入 SigV4 规范请求（Canonical Request）。预签名请求优先取 query 参数中的哈希值，仅在 query 未提供时回退读取请求头，显式的 `UNSIGNED-PAYLOAD` 同样受支持。[PR #177](https://github.com/pgsty/silo/pull/177) 将 IAM 策略条件求值统一对齐到这一有效哈希值（同时保留判断请求头是否存在的语义），并在通用认证路径中补齐了仅通过请求头携带哈希的预签名请求正文摘要校验，确保签名绑定、策略评估与正文校验使用同一个值。

### 直接从签名日期计算签名年龄 {#exempt-signature-age}

初版修复曾豁免验签后写入内部请求头的临时字段 `x-amz-signature-age`，但 `PUT` 和 `UploadPart` 的授权评估发生在流式验签之前，此时该内部头尚未生成。[PR #177](https://github.com/pgsty/silo/pull/177) 改为直接根据已受签名保护的 `X-Amz-Date` 计算 `s3:signatureAge`，并彻底移除了内部临时头、相关常量及豁免分支。伪造日期会直接导致验签失败，客户端自行传入的同名未签名头则会被拦截；同时验签过程不再修改请求头映射，多次调用保持幂等。

### 将 `X-Amz-Tagging` 注入移至验签之后 {#tagging-reorder}

`PutObjectTaggingHandler` 会从请求正文 XML 中解析并合成 `X-Amz-Tagging` 请求头供 IAM 策略条件评估读取，而原先这一注入发生在调用 `authenticateRequest` *之前*。将未签名头检查扩展到全部 `X-Amz-` 前缀后，这个由服务端合成、客户端从未签名的请求头会被误判为未签名头而遭到拒绝。修复将注入时机调整至签名验证通过之后、策略授权评估之前，既不影响策略条件读取标签，又保持了验签边界的纯净。我们否决了“像豁免 `content-sha256` 一样全局豁免 `X-Amz-Tagging`”的替代方案——因为一旦全局豁免，客户端就能在任意签名或预签名写入请求上附加未签名的 `X-Amz-Tagging` 头来篡改对象标签。

## 跨签名模式的适用范围 {#scope}

- **`Authorization` 头签名与预签名 SigV4：** 两条路径均已强制执行 `checkUnsignedHeaders`。
- **流式 SigV4（Streaming SigV4）：** 种子签名校验器未调用 `checkUnsignedHeaders`。Copy 系列 handler 通过常规认证分发直接拒绝流式认证，而流式 `PUT` / `UploadPart` 的请求头覆盖属于独立边界。
- **SigV2：** 不受影响。SigV2 规范化算法在构造待签字符串（string-to-sign）时默认纳入全部 `x-amz-*` 请求头，任何额外附加的 `x-amz-*` 头都会改变计算出的签名并触发签名不匹配错误。

## 状态码权衡：400 与 403 {#status-code}

AWS S3 对未签名请求头返回 `403 Forbidden`，而 SILO 沿用上游 `ErrUnsignedHeaders` 定义返回 `400 AccessDenied`。两者的 S3 错误码字符串均为 `AccessDenied`，仅 HTTP 状态码不同。若将 `cmd/api-errors.go` 中的状态码改为 `403`，虽然只需修改一行代码，但会同步改变既有的未签名 `x-amz-meta-*` 请求头返回码。为避免在安全补丁中引入额外的状态码兼容变更，此处保持 `400 AccessDenied` 不变。

## 回归测试 {#tests}

代码中原有的若干单元测试会先构造签名请求，*在完成签名之后*再手动追加 `x-amz-copy-source`、`x-amz-copy-source-range` 或 `x-amz-metadata-directive` 请求头。这些测试已更新为在设置完操作控制头后重新调用 `signRequestV4` 签名（`signRequestV4` 会自动将已有的 `Authorization` 头排除在签名集合外，因此可安全重签）。新增单元测试覆盖了 `checkUnsignedHeaders` 的空首值多值头拦截、`X-Amz-Content-Sha256` 豁免、旧版未签名 `x-amz-signature-age` 头拒绝，以及对同一预签名请求连续验签两次的幂等性测试 `TestPresignedVerifyIdempotent`。

## 验证证据 {#evidence}

- 在真实构建的服务端实例上，复现脚本在预签名与 `Authorization` 头两条路径上均确认了修复前的混淆代理行为，并在修复后验证两者均被拒绝；与此同时，对照组的普通 `PUT`、标准 `minio-go` `CopyObject`、携带用户元数据与标签的 `PutObject` 以及基于请求正文的 `PutObjectTagging` 均正常通过。
- `go test ./cmd/` 全量通过，`gofmt`、`gofumpt` 与 `go vet` 检查无告警。
- 首轮代码审查指出的三处边界问题（临时请求头破坏验签幂等性、空首值绕过相等检查、未签名 `x-amz-content-sha256` 误拒）均已修复并通过回归测试验证。
- 第二轮复核确认重签后的既有测试保持原有测试意图：无效 AccessKey 仍返回 `InvalidAccessKeyId`，错误的 SSE-C 密钥在签名校验通过后仍返回 `403`。

## 兼容性与运维影响 {#impact}

- **标准客户端：** 零影响。遵循 SigV4 规范的客户端与 SDK 会自动将发送的非豁免 `x-amz-*` 请求头纳入 `SignedHeaders`。
- **附加未签名 `x-amz-*` 头的客户端：** 请求将被拒绝并返回 `AccessDenied`，与 AWS S3 行为一致。
- **滚动升级：** 线协议与底层存储格式无变化。升级过程中，已升级节点立即强制执行新边界，未升级节点在完成替换前仍存在暴露窗口。
- **版本回滚：** 新版本写入的数据可被旧版本正常读取，但回滚服务端二进制会重新暴露该混淆代理漏洞。

## 关联修复与延伸原则 {#residual-risks}

- **安全通告编号：** 未签名请求头覆盖修复对应 `SN-2026-011`，[PR #177](https://github.com/pgsty/silo/pull/177) 中的相邻签名与载荷校验修复对应 [`SN-2026-012`](/zh/about/security-advisories/#sn-2026-012)。
- **HTTP 状态码：** 上述 `400` 与 `403` 的状态码对齐留待后续大版本评估。
- **相邻签名修复：** [PR #177](https://github.com/pgsty/silo/pull/177) 一并消除了重复 `x-amz-copy-source` 请求头的解析歧义、修正了签名年龄的授权评估时序与载荷哈希策略条件取值，并补齐了仅通过请求头携带哈希的预签名请求正文摘要校验。回归测试覆盖了普通签名与预签名请求、上传验签前的策略评估以及真实 HTTP 存储桶策略防篡改验证。
- **通用设计原则：** 凡是允许请求语法改变服务端操作语义的控制项，都必须在进入路由或业务分发前确认其已受签名保护，且验签所绑定的值与业务处理器实际消费的值必须严格一致。

## 总结 {#conclusion}

SigV4 验签不仅要确认签名头列表声明的请求头悉数到达，还必须反向确认实际收到的每一个 `x-amz-*` 请求头都已纳入签名列表。在业务处理器执行前拒绝未签名的 `x-amz-*` 请求头，从根源上闭合了普通签名与预签名 SigV4 路径上的混淆代理漏洞。虽然签名校验改动本身不涉及存储格式变更，但升级至 [Server 20260916](/zh/blog/release/silo-20260916/) 同时包含[需要协调升级的 IAM 变更](/zh/operations/replication/iam-upgrade/)。
