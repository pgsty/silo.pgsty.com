---
title: "SN-2026-023：已认证 STREAMING-UNSIGNED-PAYLOAD-TRAILER 无限期重放窗口与 SigV4 条件键缺失"
linkTitle: "SN-2026-023 · 无签名尾标重放"
date: 2026-11-11
author: "冯若航"
description: "通过 Authorization 请求头认证的 STREAMING-UNSIGNED-PAYLOAD-TRAILER 流式上传漏检了 15 分钟 X-Amz-Date 时钟偏差窗口，导致被截获或落盘记录的请求头可在任意未来时刻搭配同长度任意数据无限重放覆写对象，且策略求值时缺失 s3:signatureversion 与 s3:authType。"
tags: [安全, S3, SigV4, Streaming, Authentication, SILO]
weight: 1
draft: false
url: "/zh/blog/security/20261111-streaming-unsigned-trailer-replay/"
---

**发布状态：** 已随 **[SILO 20261112](/zh/blog/release/silo-20261112/)** 发布（[`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697)、[`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555)）\
**安全编号：** `SN-2026-023`（[安全公告台账](/zh/about/security-advisories/#sn-2026-023)，[#338](https://github.com/pgsty/silo/issues/338)）\
**严重程度：** 高危（High）\
**影响范围：** **SILO Server**（`RELEASE.2026-11-09T00-00-00Z` 及更早版本）与自 `2023-05-05`（[`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091)）以来的上游原版 MinIO\
**不受影响组件：** `silo-console`、`mcli`、`silo-pkg` 与 `kes`

在 AWS S3 的 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 协议模式中，客户端仅使用 Signature Version 4（`Authorization: AWS4-HMAC-SHA256 ...`）对初始 HTTP 请求头签名，随后的 `aws-chunked` 数据块与末尾尾标校验和（Trailer Checksum）均不包含逐块加密签名。由于规范请求（Canonical Request）中绑定的只是固定字符串 `"STREAMING-UNSIGNED-PAYLOAD-TRAILER"` 而非请求体的 SHA-256 摘要，校验已签名 `X-Amz-Date` 请求头的 15 分钟有效期窗口（`globalMaxSkewTime = 15 分钟`）是阻止历史请求头被重放的唯一时间边界。

继承自上游 MinIO 的 `setAuthMiddleware`（`cmd/auth-handler.go`）对 `authTypeSigned`、`authTypeStreamingSigned` 与 `authTypeStreamingSignedTrailer` 执行了 `parseAmzDateHeader` 与 15 分钟时钟偏差检查，却**唯独遗漏了 `authTypeStreamingUnsignedTrailer`**。一旦某次已认证上传的请求头在代理日志、调试抓包或明文链路中泄露，只要对应 Access Key 尚未吊销，攻击者就可在数天乃至数月之后重放同一组请求头，并**替换为任意等长（`X-Amz-Decoded-Content-Length` 相同）的恶意载荷**覆写目标对象。此外，`getConditionValuesWithTags`（`cmd/bucket-policy.go`）在两种尾标流式模式下均未填充 `s3:signatureversion` 与 `s3:authType` 策略条件键。

## 摘要 {#summary}

- **问题本质：**
  1. **无限期请求头重放与等长内容替换：** `setAuthMiddleware` 与 `doesSignatureMatch`（`cmd/signature-v4.go`）均未对 `authTypeStreamingUnsignedTrailer` 检查 `X-Amz-Date` 时间偏差。任何携带 `Authorization` 的历史上传请求头在超过 15 分钟后依然永久有效，且可搭配全新的任意等长数据块与自算 CRC 尾标覆写同一 `(bucket, key)`（含 `PutObject`、`PutObjectPart` 与 `PutObjectExtract`）。
  2. **尾标流式请求缺失 SigV4 策略条件键：** `getConditionValuesWithTags` 为早期的 `authTypeStreamingSigned` 填入 `s3:signatureversion = "AWS4-HMAC-SHA256"` 与 `s3:authType = "REST-HEADER"`，却将 `authTypeStreamingSignedTrailer` 和已认证 `authTypeStreamingUnsignedTrailer` 的两个值留空。要求这些值的 `Allow` 会误拒合法尾标上传，要求这些值的 `Deny` 则可能无法命中。
- **上游溯源：** 由上游 MinIO 于 `2023-05-05` 合入的提交 [`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091)（[minio/minio#16484](https://github.com/minio/minio/pull/16484)，*"Signed trailers for signature v4"*）引入；上游在 `2025-04-03` 补加无签名尾标验签的提交 [`8c7097528`](https://github.com/pgsty/silo/commit/8c70975283f9f4ce80f331a25c7475a36279e519)（[minio/minio#21103](https://github.com/minio/minio/pull/21103)）仍未补齐时间窗口检查。
- **修复方式：** 提交 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) 与 [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) 在 `setAuthMiddleware` 中对所有携带 `Authorization` 请求头的 `authTypeStreamingUnsignedTrailer` 请求强制执行 15 分钟 `X-Amz-Date` 偏差校验（同时保留公开桶匿名流式上传），补齐请求头签名与流式种子签名的 `checkUnsignedHeaders` 校验，并为两种尾标流式模式填入与 AWS S3 规范一致的 `s3:signatureversion` 与 `s3:authType` 条件值。

---

## 一、上游溯源与根因分析 {#provenance}

### 为什么 `authTypeStreamingUnsignedTrailer` 漏掉了时间窗口校验 {#skew-gap}

在 SILO 及上游 MinIO 的 SigV4 验证分层中，签名校验与时间戳新鲜度校验分属两处：

1. **`doesSignatureMatch`（`cmd/signature-v4.go`）：** 仅解析 `X-Amz-Date`（或 `Date`）用于派生 `YYYYMMDD` 签名密钥作用域并核对规范请求 HMAC，本身不检查时间戳是否超出 `globalMaxSkewTime`（`15 * time.Minute`），默认前置 HTTP 中间件已完成拦截。
2. **`setAuthMiddleware`（`cmd/auth-handler.go`）：** 调用 `parseAmzDateHeader(r)`，拒绝与服务端当前 `UTCNow()` 相差超过 15 分钟的请求（返回 `ErrRequestTimeTooSkewed`）。

当上游在 [`76913a9fd`](https://github.com/pgsty/silo/commit/76913a9fd5c6e5c2dbd4e8c7faf56ed9e9e24091)（`2023-05-05`）中引入尾标流式模式时，`getRequestAuthType` 将所有携带 `X-Amz-Content-Sha256: STREAMING-UNSIGNED-PAYLOAD-TRAILER` 的请求——无论是否携带 `Authorization` 签名头、还是发往公开可写桶的纯匿名流式上传——统一归类为同一个枚举值 `authTypeStreamingUnsignedTrailer`。由于匿名请求没有 `X-Amz-Date`，上游在 `setAuthMiddleware` 中只把 `authTypeStreamingSignedTrailer` 加入了分支，漏掉了已认证的 `authTypeStreamingUnsignedTrailer`：

```go
// 继承自上游的 setAuthMiddleware 分支（cmd/auth-handler.go）
switch aType {
case authTypeSigned, authTypeStreamingSigned, authTypeStreamingSignedTrailer:
    // 遗漏了携带 Authorization 的 authTypeStreamingUnsignedTrailer！
    amzDate, errCode := parseAmzDateHeader(r)
    if errCode != ErrNone {
        writeErrorResponse(r.Context(), w, errorCodes.ToAPIErr(errCode), r.URL)
        return
    }
    if checkSkewTime(UTCNow(), amzDate) != ErrNone { ... }
}
```

此后无论是上游 [`8c7097528`](https://github.com/pgsty/silo/commit/8c70975283f9f4ce80f331a25c7475a36279e519)（`2025-04-03`），还是后续针对查询参数认证绕过（[`CVE-2026-41145`](/zh/about/security-advisories/#cve-2026-41145)）与 Snowball 解包绕过（[`CVE-2026-40344`](/zh/about/security-advisories/#cve-2026-40344)）的修补，都在 `newUnsignedV4ChunkedReader` 内调用 `reqSignatureV4Verify` -> `doesSignatureMatch`，仅验证了 HMAC 而未检查时钟偏差，导致数月甚至数年前签发的请求头依然能通过验证。

为什么无时间上限在 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 下危害尤为突出？如果签名覆盖的 `X-Amz-Content-Sha256` 包含实际请求体摘要，该摘要会绑定正文内容；规范请求使用无签名载荷标记的模式不具备这项保证。而在 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 模式下，签名仅覆盖 `Host`、`X-Amz-Content-Sha256` 字面量、`X-Amz-Date`、`X-Amz-Decoded-Content-Length` 与 `X-Amz-Trailer` 尾标名，**既不覆盖分块数据，也不覆盖末尾 CRC 校验值本身**。攻击者只要拿到一组历史请求头，即可构造任意等长的新内容并自行重算匹配的 CRC 尾标，在未来任意时间静默篡改目标对象。

### `getConditionValuesWithTags` 遗漏尾标流式条件键 {#condition-gap}

在 `cmd/bucket-policy.go` 的 `getConditionValuesWithTags` 中，填充 `s3:signatureversion` 与 `s3:authType` 的 `switch` 语句停留在尾标流式出现之前的三种枚举（`authTypeSigned`、`authTypePresigned`、`authTypeStreamingSigned`）。由于当前主流 AWS SDK（Go v2、Java v2、Python `boto3`、JS v3）在上传对象时默认开启 `CRC32` / `CRC64NVME` 尾标校验，发出的请求普遍采用 `authTypeStreamingSignedTrailer` 或 `authTypeStreamingUnsignedTrailer`，导致服务端策略引擎读到的这两个条件键始终为空。

---

## 二、影响范围 {#impact}

| 涉及接口 / 策略场景                                        | 具体影响说明                                                                                                                                             |
| :--------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`PutObject`、`PutObjectPart`、`PutObjectExtract` 写入**  | 被日志记录或截获的已认证 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 请求头在密钥有效期内可被无限期重放，并以等长任意内容覆写目标路径（除非目标受对象锁保护）。 |
| **使用 `s3:signatureversion` 或 `s3:authType` 的访问策略** | 以 `AWS4-HMAC-SHA256` / `REST-HEADER` 为匹配条件的规则，在这些条件值为空时无法匹配尾标流式上传。                                                         |
| **发往公开桶的纯匿名 `aws-chunked` 流式上传**              | 修复前后均不受影响（匿名请求不携带 `Authorization` 头）。                                                                                                |
{.wide .expand}

---

## 三、修复方案：设计思考与充分必要性 {#fix}

提交 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) 与 [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555) 在认证入口、流式验签与策略上下文构造处精确补齐了协议契约：

1. **`setAuthMiddleware` 按是否携带认证头执行 15 分钟窗口检查（`cmd/auth-handler.go`）：**
   当 `aType == authTypeStreamingUnsignedTrailer` 且 `r.Header.Get(xhttp.Authorization) != ""` 时，中间件在进入处理器或分块读取器前执行 `parseAmzDateHeader(r)` 与 15 分钟时钟偏差校验。缺失日期返回 `400 AccessDenied`，畸形日期返回 `400 MalformedDate`，超出时间窗返回 `403 RequestTimeTooSkewed`。没有 `Authorization` 的请求仍按匿名请求处理，并须通过 `newUnsignedV4ChunkedReader` 的桶策略鉴权。
2. **`getConditionValuesWithTags` 补齐尾标流式条件键（`cmd/bucket-policy.go`）：**
   - `authTypeStreamingSignedTrailer`：填入 `s3:signatureversion = "AWS4-HMAC-SHA256"` 与 `s3:authType = "REST-HEADER"`；
   - 携带 `Authorization` 的 `authTypeStreamingUnsignedTrailer`：填入 `s3:signatureversion = "AWS4-HMAC-SHA256"` 与 `s3:authType = "REST-HEADER"`；
   - 不携带 `Authorization` 的匿名 `authTypeStreamingUnsignedTrailer`：将 `s3:signatureversion` 与 `s3:authType` 的条件值保持为空，防止匿名请求在策略求值中冒充 SigV4 签名请求。

### 为什么该修改既必要又充分 {#sufficiency}

- **必要性：** 若不区分 `Authorization != ""` 而对全部 `authTypeStreamingUnsignedTrailer` 一刀切调用 `parseAmzDateHeader`，会直接破坏向公开可写桶发送的不带 `X-Amz-Date` 的合法匿名 `aws-chunked` 上传（`cmd/streaming-auth-boundary_test.go` 对此有专门回归覆盖）。而由于 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 搭配 URL 查询参数预签名已在 [`CVE-2026-41145`](/zh/about/security-advisories/#cve-2026-41145) 中明令禁止，因此检查 `Authorization != ""` 已 100% 覆盖所有持凭据的无签名尾标请求。
- **充分性：** 在全局入口中间件 `setAuthMiddleware` 拦截时间偏差，可一次性覆盖 `PutObjectHandler`、`PutObjectPartHandler`、`PutObjectExtractHandler` 等所有接收流式上传的路由，确保超期请求在读取任何主体字节前即被拒绝。

---

## 四、利弊权衡、潜在代价与边界 {#tradeoffs}

| 权衡维度                          | 工程取舍与残余边界说明                                                                                                                                                                                                                                                   |
| :-------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **客户端时钟同步要求**            | 使用 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 的已认证客户端若本机时钟与服务端 UTC 偏差超过 15 分钟，现在会与普通 SigV4 请求及 AWS S3 一致返回 `RequestTimeTooSkewed`。                                                                                                      |
| **显式限定 `s3:authType` 的策略** | 已认证的带签名尾标与无签名尾标请求均使用 `REST-HEADER`；已包含该值的白名单无需添加尾标专用值。区分载荷模式应使用 `s3:x-amz-content-sha256`。                                                                                                                             |
| **15 分钟窗口内的明文传输风险**   | 无签名尾标模式在合法时间窗内也没有逐块密码学签名，应使用 TLS。若要拒绝此模式，对 `s3:PutObject` 添加 `Deny`，以 `StringEquals` 匹配 `s3:x-amz-content-sha256` 的 `STREAMING-UNSIGNED-PAYLOAD-TRAILER` 值。该规则只禁用这一载荷模式，不代表已禁用所有其他无签名载荷模式。 |
{.wide .expand}

---

## 升级与加固建议 {#remediation}

1. **升级 SILO Server** 至 **[SILO 20261112](/zh/blog/release/silo-20261112/)**（`RELEASE.2026-11-12T00-00-00Z`）或更高版本（包含提交 [`14ecb222e`](https://github.com/pgsty/silo/commit/14ecb222e714eaa69e712b7497e500d72854f697) 与 [`296c9710b`](https://github.com/pgsty/silo/commit/296c9710b16467e53fd4d861bf0b01f35fe6e555)）。
2. **强制启用 HTTPS 并脱敏访问日志：** 确保 S3 接入层全程使用 TLS，且反向代理与调试日志不落盘明文 `Authorization` 请求头。
3. **可选策略加固（禁用无签名尾标载荷）：** 在 IAM 或桶策略中为 `s3:PutObject` 添加 `Deny`，条件为 `StringEquals: {"s3:x-amz-content-sha256": "STREAMING-UNSIGNED-PAYLOAD-TRAILER"}`。模式标记属于载荷条件值；已认证尾标请求的 `s3:authType = "REST-HEADER"`。请用实际上传客户端验证策略效果。

更多信息请参阅[安全公告台账](/zh/about/security-advisories/#sn-2026-023)、[`CVE-2026-41145`](/zh/blog/security/cve-2026-41145/)、[`CVE-2026-40344`](/zh/blog/security/cve-2026-40344/) 与[签名头覆盖设计（`SN-2026-011`）](/zh/blog/design/signed-header-coverage/)。
