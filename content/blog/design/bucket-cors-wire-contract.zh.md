---
title: "桶级 CORS Wire 契约：严格 XML、Checksum 与浏览器响应"
linkTitle: "桶级 CORS Wire 契约"
date: 2026-08-29
lastmod: 2026-08-29
author: "冯若航"
summary: >
  SILO 第一版桶级 CORS 会接受第二个 XML root、把 UTF-8 字节数当作规则 ID 字符数，并把 S3 枚举之外的小写方法规范化成有效值。本文记录 B3 对 wire/parser/validation 契约的最终修复、AWS 与浏览器证据、被否决方案，以及与 site-replication 明确分离的实现边界。
tags: [设计, S3, CORS, XML, 兼容性]
weight: 33
draft: false
url: "/zh/blog/design/bucket-cors-wire-contract/"
---

本文记录 [SILO PR #71](https://github.com/pgsty/silo/pull/71) 以 [`e4e3007da`](https://github.com/pgsty/silo/commit/e4e3007da6d7d1198a6a050e34f84566d40a9654) 合并后，桶级 CORS 的 B3 协议加固决策。范围只包括 S3 请求体、校验、checksum、匹配和浏览器响应契约。站点复制顺序、tombstone、heal、状态计数与通用 metadata 重构仍是 [SILO #75](https://github.com/pgsty/silo/issues/75) 下的独立工作。

> **状态：** B3 实现已存在于隔离本地 `codex/issue-75-b3-cors-wire` 工作树。Parser、Validate、签名 Handler、定向 race、完整 `cmd`、构建、vet、固定版本 lint、生成文件、兼容性/rebrand 以及真实 `minio-go`/boto3 检查全部通过。较早一轮 Claude Code Opus 5 max-effort 实现评审结论为 **GO**；本设计与代码的发布前终审结论为 **GO WITH FIXES**，没有 P0 或 P1。纳入其 `Origin: null` finding 与文档修正后，同一会话复审精确文件并给出 **GO**，没有 P0–P2 finding。修改仍未提交、推送、合并、打标、发布、部署或完成生产验证。<br>
> **决策：** 在第一个包含桶级 CORS 的 SILO 正式版本之前完成严格 B3 wire 契约。不能把无效输入规范化成有效配置，不能把补丁扩大成 site replication 重构，也不能用本地 B3 证据宣称整体发布 GO。

## 为什么这是发布阻断 {#problem}

Bucket CORS 是标准 S3 控制面。输入不只是“看起来像配置的文本”：原始客户端会对精确 XML 请求体签名，现代 AWS SDK 会附带必需的 payload checksum，SILO 会原样保存接受的字节，`GetBucketCors` 随后又会把这些字节返回给严格 XML 客户端。

三个对抗用例暴露了合并实现的缺口：

1. 合法 `<CORSConfiguration>` 后追加第二个 XML root 仍被接受并保存；
2. 恰好包含 255 个 Unicode 字符的 ID 会被拒绝，因为 Go `len(string)` 统计 UTF-8 字节；
3. `<AllowedMethod>get</AllowedMethod>` 会被接受，因为校验先把它转成大写再检查 S3 枚举。

这些是服务端 wire 问题。AWS 官方 SDK 模型不会在客户端完整校验规则 ID 或方法字符串，原始签名客户端也始终可以绕过 typed SDK 构造。因此必须由服务端执行契约。

第二个 root 的后果尤其严重。SILO 保存的是完整 body，而不是第一个已解码元素。一次成功 PUT 因此可能让后续 GET 返回含两个 root 的文档，标准 XML 客户端会直接拒绝它。

## 权威契约 {#contract}

实现以当前 AWS 文档与生成 SDK 模型作为协议基线：

- [PutBucketCors](https://docs.aws.amazon.com/AmazonS3/latest/API/API_PutBucketCors.html) 定义 XML root、64 KB 文档上限、Content-MD5 与 SDK checksum header、最多 100 条规则，以及 Origin、Method、所有请求 Header 必须同时匹配的规则条件。
- [CORSRule](https://docs.aws.amazon.com/AmazonS3/latest/API/API_CORSRule.html) 定义大写方法值与包含端点的 255 字符 ID 上限。
- [CORS 配置元素](https://docs.aws.amazon.com/AmazonS3/latest/userguide/ManageCorsUsing.html)规定每个 AllowedOrigin 或 AllowedHeader 最多包含一个 `*`。
- [测试 CORS](https://docs.aws.amazon.com/AmazonS3/latest/userguide/testing-cors.html)展示成功预检返回命中规则的完整方法列表、请求且允许的 Header、ExposeHeader、credentials 与缓存变化 Header。
- [S3 错误响应](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/ErrorResponses.html)把不符合 S3 schema 的 XML 定义为 `MalformedXML`，把 Content-MD5 或 checksum 不匹配定义为 `BadDigest`。
- 生成的 [AWS SDK for Go v2 PutBucketCors 操作](https://github.com/aws/aws-sdk-go-v2/blob/main/service/s3/api_op_PutBucketCors.go)把请求 checksum 标记为 required；其 [CORS 类型](https://github.com/aws/aws-sdk-go-v2/blob/main/service/s3/types/types.go)使用 `int32` MaxAgeSeconds，并把大多数语义校验留给服务端。
- [WHATWG Fetch Standard](https://fetch.spec.whatwg.org/)禁止在 `Access-Control-Allow-Origin` 为 `*` 时共享带 credentials 的响应。

对公开 AWS `landsat-pds` bucket 的只读 OPTIONS 请求又独立确认了当前响应行为：字面 wildcard 规则返回 `Access-Control-Allow-Origin: *`、完整 `GET, HEAD` 方法列表，并且不返回 `Access-Control-Allow-Credentials`。

## 复现分类 {#classification}

| 行为 | 结论 | 证据与决策 |
| --- | --- | --- |
| 接受第二个 XML root | **REAL** | 修复前 Parser、进程内签名 Handler 与真实 TCP SigV4 均接受 |
| 拒绝 255 个 Unicode 字符的 ID | **REAL** | Parser/Validate、签名 Handler 与真实 boto3 请求复现了 SILO 的拒绝；接受 255 个 code point 依据 AWS 的字符表述与 SDK 模型，而不是 AWS 授权 PUT |
| 接受小写 Method | **REAL** | Parser/Validate、签名 Handler 与真实 boto3 请求均复现 |
| 64 KiB 边界 | **NOT REAL** | 65,536 字节原本就通过，65,537 失败；保留回归测试 |
| 100-rule 边界 | **NOT REAL** | 恰好 100 原本就通过，101 失败；保留回归测试 |
| 第一条完全匹配规则 | **NOT REAL** | 现有匹配会越过 Header 受限的较早规则；保持该行为 |
| Checksum EOF 绕过 | **CONDITIONAL** | 内存 Reader 可能让 checksum wrapper 看不到 EOF，真实 TCP 原本已拒绝坏摘要；仍消除 reader-dependent 行为 |
| 空与未知 XML member | **CONDITIONAL，按 strict 解决** | AWS schema/error 文档支持拒绝，但没有可用的 AWS 授权 PUT 黑盒结果 |
| wildcard Origin + credentials | **REAL** | 合并版 SILO 会对 `*` 回显 Origin 并开启 credentials；真实 AWS 与 Fetch 要求 `*` 且不带 credentials |
| `Origin: null` 被改写成 wildcard | **REAL，终审发现** | 内层 forwarding middleware 把明确命中的 `null` 改成 `*`，却保留 credentials；B3 现在标记专属响应，让旧 rewrite 跳过它 |
| 拒绝负 MaxAge | **CONDITIONAL，原有行为** | 因浏览器 max-age 非负而保留；没有可用的 AWS 授权 PUT 差分结果 |

## 目标与非目标 {#scope}

### 目标 {#goals}

- 只接受一个 S3 CORS 文档元素，之后仅允许 XML Misc；
- 执行文档定义的 64 KiB、100-rule、ID、Method、wildcard 与 MaxAge 契约；
- 让 Content-MD5 与现代 SDK checksum 校验不依赖 Reader 分块方式；
- 保留第一条完全匹配规则的语义；
- 返回兼容 S3 且对浏览器安全的成功预检与实际请求 Header；
- 通过 Parser、Validate、签名 Handler 与真实客户端测试让每个变化可审阅；
- 保持 exported compatibility manifest 不变。

### 非目标 {#non-goals}

- 修改 site-replication 交付、tombstone、heal 或状态计数；
- 重构全局 CORS fallback 或 metadata 错误处理；
- 增加 Console UI；
- 引入通用 XML schema 框架；
- 校验任意 XML 属性或强制唯一 namespace 写法；
- 在缺少更强当前证据时强制跨规则 ID 唯一；
- 重构无关 Lifecycle、Tagging、Policy、SSE、Quota 或 Versioning parser；
- 在本工作项中 commit、push、tag、发布镜像、部署或宣称生产一致。

## 方案比较 {#alternatives}

### A. 只修报告的三行 {#alternative-three-lines}

可以补 EOF 检查、改用 rune count、删除 Method 大写转换。这个方案很诱人，但并不完整：Unknown Element、重复 singleton、空数值、int32 overflow、通用 `?` wildcard、依赖 Reader 的 checksum 校验，以及错误的 wildcard/preflight 响应仍然存在。

**否决：** 对已经明确要求核验的 B3 契约过窄。

### B. 把输入规范化成 canonical 配置 {#alternative-normalize}

服务端可以把 Method 转成大写、trim value、丢弃 unknown element，只保留第一个 XML root。对友好客户端很方便，却会把无效的已签名 wire 输入变成另一份有效配置，也会保留无法通过 `GetBucketCors` 干净 round-trip 的字节。

**否决：** S3 兼容要求校验，而不是静默修复。

### C. 增加 B3 专用 strict wire 表示 {#alternative-strict-wire}

解码到私有 XML wire struct，捕获直接文本、unknown element、重复 singleton 与 MaxAge presence。只有 XML shape 合法后才转换成现有公开 `Config` 与 `Rule`；语义检查继续留在 `Validate` 和 matcher。

**采用：** 在有证据处严格、元素顺序无关、namespace 宽容、局限于 CORS，且不增加 exported compatibility symbol。

### D. 校验所有可能 XML 与 Header 细节 {#alternative-full-schema}

这会强制 namespace URI、拒绝所有 unknown attribute、按 RFC token 校验所有响应 Header，并强制跨规则 ID 唯一。

**暂不采用：** 这些约束缺少足够差分证据，可能制造无必要不兼容。

## 最终设计 {#design}

### 1. XML wire parser {#parser}

`ParseBucketCorsConfig` 解码到私有 wire-only 类型：

- `CORSConfiguration` 是唯一 root；
- root 与 rule 层拒绝非空白直接字符数据；
- 拒绝 unknown root、rule 与 leaf 内嵌元素；
- 每条规则最多一个 `ID` 与 `MaxAgeSeconds`；
- 列表成员仍可重复，元素顺序不受限制；
- MaxAge 文本必须能解析为有符号 32 位整数；
- root 关闭后允许空白、Comment 与 Processing Instruction；拒绝另一个 root、文本、Directive 或 malformed token。

Namespace prefix 与标准 namespace 声明仍然可用，因为匹配使用 XML local name；本次不新增 unknown attribute 拒绝。现有 `Config` 与 `Rule` XML tag 为序列化兼容继续保留，但生产请求和 metadata 解析使用 `ParseBucketCorsConfig`。

这个 parser 也用于加载已保存 bucket metadata。这是明确的发布前选择：PR #71 之后没有 SILO tag，因此不存在已经发布的桶级 CORS 配置群需要迁移。曾经保存 malformed CORS XML 的开发版本会让整个 bucket metadata record 无法加载，而不只是 CORS view；必须先替换或删除已保存的 CORS 文档。

### 2. 语义校验 {#validation}

`Validate` 执行：

- 1 到 100 条规则；
- ID 是有效 UTF-8，且不超过 255 个 Unicode code point；
- 每条规则至少一个非空 AllowedOrigin 和一个 Method；
- Method 必须精确等于 `GET`、`PUT`、`HEAD`、`POST` 或 `DELETE`；
- AllowedOrigin 与 AllowedHeader 不得包含 `?`，因为继承 matcher 会把它当 wildcard，而 S3 只定义 `*`；
- 每个 AllowedOrigin 与 AllowedHeader 最多一个 `*`；
- AllowedHeader 与 ExposeHeader 元素非空；
- MaxAgeSeconds 位于 0 到 `2^31-1`。

空 ID 继续允许，因为 ID 本身可选，当前 AWS 文档也没有发布非空约束；跨规则 ID 唯一仍不在本补丁范围。

### 3. 匹配 {#matching}

本路径用小型单 `*` matcher 替代通用 matcher：

```text
没有 *  -> 精确匹配
一个 *  -> Prefix 与 Suffix 都必须匹配；* 可以匹配零字节
```

AllowedHeader 匹配继续忽略大小写，响应保留请求 Header 原始拼写。S3 PUT 路径会校验 canonical 保存值，因此 Method 匹配按大小写精确进行；合并基线中的直接 site-replication 与 heal 写入会绕过该校验，它们仍是独立集成要求，否则可能保存一条 B3 matcher 不会执行的方法。

`MatchPreflight` 会越过 Origin 与 Method 匹配、但拒绝某个请求 Header 的规则；最终选中的因此是满足三项文档条件的第一条规则。它还返回真正命中的 Origin 元素与 MaxAgeSeconds 是否出现，从而保留“缺失”与“显式 0”的差别。

### 4. 请求大小与 checksum {#checksums}

Handler 保留现有正 Content-Length 与 64 KiB guard。`validateLengthAndChecksum` 继续用共享 checker 包装 body，但 CORS handler 现在把包装后的 body 读到 EOF，不再在外面套另一个长度恰好的 `LimitReader`。

这样无论底层 Reader 是在同一次调用中返回最后字节与 `io.EOF`，还是下一次调用才返回 EOF，checksum 校验都一致。格式合法但内容不匹配的 Content-MD5 或 full-header SDK checksum 返回 `BadDigest`；缺少 checksum material 继续返回现有 required-checksum 错误。共享 helper 可能把 malformed checksum syntax 归类为 missing，本小 body 路径也不实现 aws-chunked trailing-checksum 解码；这些 fidelity 缺口保持在 B3 之外。不新增第二套 checksum 实现。

现代 boto3 流量是实质兼容门，因为当前 botocore 对这个 required-checksum 操作发送的是 `x-amz-sdk-checksum-algorithm: CRC32` 与 `x-amz-checksum-crc32`，而不是 Content-MD5。

### 5. 浏览器响应 {#responses}

命中的 Origin 元素决定响应：

| 命中元素 | `Access-Control-Allow-Origin` | `Access-Control-Allow-Credentials` |
| --- | --- | --- |
| `*` | `*` | 不发送 |
| `null` | `null` | `true` |
| 精确 Origin | 请求 Origin | `true` |
| `https://*` 等 pattern | 请求 Origin | `true` |

成功预检返回：

- 命中规则的完整 `AllowedMethods` 列表；
- 规则允许且请求实际提出的 Header；
- 配置的 `ExposeHeaders`；
- MaxAgeSeconds，包括显式 0；
- 现有成功预检的三个 `Vary` 维度。

实际请求保持现有 continue-through 行为；规则匹配时增加 Origin、credentials、Expose 与 `Vary: Origin` Header。请求 context marker 会阻止内层旧 forwarding middleware 把明确允许的 `null` Origin 改写成 `*`；没有 marker 的全局响应继续保留历史 workaround。由于 sandbox document 与 `file://` Origin 共享 `null`，只有在确实要允许所有这些上下文携带 credentials 时才应配置它。

AllowedOrigin 元素按文档顺序求值。如果同一规则同时包含具体 Origin 与 `*`，而具体 Origin 需要保留反射 Origin + credentials 语义，应把具体 Origin 放在前面。

拒绝预检在 B3 中继续返回现有空 body 403。生成完整 AWS `AccessForbidden` XML，以及调整拒绝响应缓存/audit 行为，需要独立 wire 决策，不能偷偷混入 parser 加固。

## 实现映射 {#implementation}

| 区域 | 文件 | 职责 |
| --- | --- | --- |
| Parser 与 Validate | `internal/bucket/cors/cors.go` | 私有 wire struct、严格 trailing token、rune/enum/wildcard/MaxAge 校验、匹配 |
| Parser 测试 | `internal/bucket/cors/cors_test.go`、`cors_adversarial_test.go` | Root、XML Misc、unknown/nested/duplicate、边界与匹配 |
| PUT Handler | `cmd/bucket-cors-handlers.go` | 大小/checksum guard、EOF 消费、S3 error mapping |
| 签名 Handler 测试 | `cmd/bucket-cors-adversarial_test.go` | 三个报告用例、64 KiB、100 rules、MD5/CRC32 正反例 |
| 浏览器响应 | `cmd/api-router.go`、`cmd/generic-handlers.go` | 命中 Origin 语义、`null` marker、完整 Method、Expose、显式 MaxAge 0 |
| 响应测试 | `cmd/bucket-cors-middleware_test.go` | 精确/pattern/wildcard/`null` Origin、第一条完全匹配规则、Header、Method、Expose、MaxAge、credentials |

任何 site-replication 源文件都不属于本实现边界。

## 测试与证据矩阵 {#tests}

| 层次 | 必须证据 |
| --- | --- |
| Parser | 拒绝第二 root/文本/悬空关闭；接受 trailing 空白/Comment/PI；拒绝 unknown/nested/duplicate |
| Validate | 255 个 Unicode 字符接受、256 拒绝；拒绝小写与不支持 Method；wildcard 与空值用例 |
| 边界 | 恰好 64 KiB 与 100 rules 接受；多一个字节/规则拒绝；MaxAge 缺失/0/负数/int32 overflow |
| 签名 Handler | 三个报告失败的原始 SigV4 PUT；缺失/错误 MD5；有效/错误 SDK CRC32 |
| Middleware | 第一条完全匹配规则；wildcard、pattern 与 `null` credentials；无 marker 的旧 `null` rewrite；完整 Method；请求 Header；Expose；显式 MaxAge 0 |
| 定向 race | race detector 下的 CORS package 与 CORS Handler/Middleware 测试 |
| 完整本地门 | 无 tag 与 `kqueue,dev` 完整 `cmd`；build；vet；固定 lint；generated/rebrand；diff check |
| 真实客户端 | `minio-go` v7.3.1 PUT/GET/preflight/DELETE；boto3/botocore CRC32 PUT/GET/preflight/DELETE 与对抗拒绝 |
| 外部行为 | 对公开 AWS bucket 的只读 OPTIONS，确认 wildcard、Methods、credentials 与 Vary |

## 对抗评审裁决 {#review}

Claude Code Opus 5 以 max effort 依次评审证据、实现，以及这份双语设计与最终代码。较早的实现评审结论为 **GO**；发布前终审结论为 **GO WITH FIXES**，没有 P0/P1，共有五项 P2 finding。纳入接受的代码与文档修改后，同一会话给出 **GO**，没有 P0–P2 finding。

其非阻断意见经过独立裁决：

- 唯一行为 P2 已接受：实际请求中明确允许的 `Origin: null` 现在能穿过内层旧 forwarding middleware；
- metadata load 影响范围与 replication 校验例外现在已精确说明；
- 返回内部 MaxAge pointer 仅供读取，且选中 Rule 原本就是内部 pointer；没有新增写入；
- 保留 `BadDigest`，因为当前 AWS S3 错误参考明确把它用于 Content-MD5 或 checksum 不匹配；
- malformed checksum syntax、trailing-checksum 解码、no-match `Vary`、完整 `AccessForbidden` XML 与外层 Middleware audit 行为被记录，但保持在 B3 之外；
- 不启用非 UTF-8 XML declaration，因为 S3 请求语法是 UTF-8，当前 SDK 也生成 UTF-8；
- Method 空白保持无效，Integer 空白继续接受，符合不同 XML lexical domain；
- 在缺少 AWS 差分证据时，延后用 RFC token 校验每个 ExposeHeader。

## 兼容性与上线 {#compatibility}

| 现有用法 | 影响 |
| --- | --- |
| Typed `minio-go` 或 boto3 CORS | 合法配置继续 round-trip；现代 CRC32 请求得到校验 |
| 原始合法 XML | 在相同大小与规则上限内继续接受 |
| 小写 Method | 不再规范化，直接拒绝 |
| 255 个非 ASCII ID 字符 | 现在接受；超过 255 拒绝 |
| 第二 root、unknown element、重复 singleton、空/overflow MaxAge | 作为 malformed XML 拒绝 |
| 字面 wildcard Origin | 现在返回 `*` 且不带 credentials |
| Pattern Origin | 继续反射具体请求 Origin 并带 credentials |
| 含 malformed CORS XML 的旧开发 metadata | 整个 bucket metadata record 可能无法加载，直到替换或删除 CORS XML |
| Site replication | B3 不改代码；其收敛修复与测试保持独立 |

严格化发生在任何带桶级 CORS 的 SILO tag 之前，这就是兼容窗口。一旦发布，该 wire 契约即成为稳定接口；今后放宽或收紧都必须另有差分证据。

## 验证结果与剩余门槛 {#gates}

最终本地实现通过：

- 定向 Parser、Validate、签名 Handler 与 Middleware 测试；
- `internal/bucket/cors` 与 CORS `cmd` 路径的定向 race；
- `go test ./cmd -count=1` 与完整 `kqueue,dev` `cmd` lane；
- `go build ./...` 与 `go vet ./...`；
- golangci-lint 2.13.1，零 issue；
- generated、compatibility/rebrand、entrypoint 与 diff check；
- 对新构建本地 server 执行真实 boto3/botocore 1.43.58 与 `minio-go` v7.3.1 回归；
- Claude Code Opus 5 max effort 最终复审。

这些结果只建立 **B3 IMPLEMENTATION GO**。整体发布仍被独立 replication 工作、服务端/文档 commit 与 push、PR 与 merged-main CI、release artifact、部署和生产验证分别阻断。

## 结论 {#conclusion}

最终 B3 设计把 Bucket CORS 当作已签名 S3 wire 契约，而不是宽容的配置文件。它在持久化前拒绝 malformed 或非 canonical 输入，按字符统计 ID，校验现代 SDK checksum，保留文档定义的第一条完全匹配规则，并生成对浏览器安全的 S3 响应。

补丁只涉及 CORS Parser、Validate、Handler、Matcher、响应代码与测试。不增加新服务、schema、依赖、exported compatibility symbol 或 site-replication 重构。这是协议和真实证据支持的最小完整方案。
