---
title: "silo-pkg 3.7.0 发布"
linkTitle: "silo-pkg 3.7.0 发布"
date: 2026-08-03
author: "冯若航"
description: "silo-pkg 以新仓库名发布的首个版本：修复策略条件键解析顺序导致的策略绕过，修复 LDAP 连接路径的三个缺陷，并降低模块的最低 Go 版本要求。"
tags: [发布, pkg]
weight: 5
url: "/zh/blog/release/pkg-3.7.0/"
aliases:
  - /blog/pkg-3.7.0/
  - /releases/pkg-3.7.0/
---

**发布日期：** 2026-08-03 · **版本：** [v3.7.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.7.0) · **仓库：** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

这是 `pgsty/silo-pkg` 以新仓库名发布的第一个版本。该版本修复了一处策略条件键解析顺序导致的策略绕过，修复了 LDAP 连接路径上的三个缺陷（其中两个由本分支自己在 v3.6.2/v3.6.3 中引入），清理了证书文件监听器泄漏，并把模块的最低 Go 版本要求从 `1.26.1` 降回到实际需要的 `1.25.0`。

{{% alert color="warning" %}}
**完整修复需要服务端配套更新**

本版本中的策略条件键改动与服务端 `getConditionValues` 中保留内部条件键名、按真实来源构造条件值的改动各自覆盖问题的一半，**单独升级任何一侧都不完整**。服务端配套改动目前存在于本地 `pgsty/minio` 提交 `1a6d5b415`；截至 2026-08-03，它尚未进入公开 `origin/master`，也没有任何已发布 Silo 服务端版本包含它。请勿把 v3.7.0 单独视为完整修复；应确认后续服务端发布说明明确包含该配套改动。具体兼容行为见[条件值来源与优先级](/zh/administration/identity-access-management/policy-based-access-control/#condition-value-sources)。
{{% /alert %}}

## 这个仓库是什么 {#what-is-this}

`silo-pkg` 是 [minio/pkg](https://github.com/minio/pkg) 的维护分支，为社区版 MinIO 分支提供上游（现由闭源产品驱动）不会再接纳的修复。仓库于 2026-08-02 由 `pgsty/minio-pkg` 改名而来。

**模块路径刻意保持不变**，仍然是 `github.com/minio/pkg/v3`，因此所有 `import "github.com/minio/pkg/v3/..."` 无需改动，只有 `replace` 指令的右侧需要更新：

```
replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.7.0
```

`/v3` 后缀是模块的主版本号，不是目录名，不能省略。GitHub 会对旧仓库名做重定向，但请直接固定到新路径。

版本号沿用上游编号，以便一眼看出某个版本基于哪个上游版本；但**不承诺内容一致**：本分支会跳过仅服务于闭源产品的改动，也会携带上游不接纳的修复。

## 策略条件键解析顺序 {#policy-condition-key}

`getValuesByKey()` 在解析策略条件键时，先尝试名字的规范 MIME 形式（`http.CanonicalHeaderKey`），再尝试原始名字。它读取的那张 map 混合了两个来源：服务端为本次请求自己算出的值（`SourceIp`、`SecureTransport`、`CurrentTime`、`username` 等，以条件键本身的拼写为键），以及请求携带的全部 HTTP 头（以规范 MIME 形式为键）。

**先查规范形式，就让客户端可以用自己发送的请求头覆盖服务端算出的值。**

对 MinIO 服务端而言这是一次策略绕过。最直观的是 `s3:prefix`：一个 `Prefix` 请求头就能满足家目录策略里的前缀条件，而实际的 `?prefix=` 查询参数照样列出整个存储桶。以同样方式可达的还有 `aws:SourceIp`、`aws:SecureTransport`、`aws:CurrentTime`、`aws:EpochTime`、`aws:username`、`aws:userid`、`aws:principaltype`、`aws:UserAgent`、`aws:groups`、`ldap:username`、`ldap:groups`、`jwt:groups`、`s3:versionid`、`s3:signatureversion`、`s3:signatureAge`、`s3:authType` 与 `s3:LocationConstraint`。匿名桶策略直接暴露；SigV4 也挡不住，因为签名只覆盖 `SignedHeaders` 中列出的请求头，多带一个未签名的头即可搭车。

还有第二个后果：当服务端把某个值存在一种拼写下、而策略键读取另一种拼写时，赢的是错的那个。`s3:object-lock-mode` 会解析到调用方发送的 `X-Amz-Object-Lock-Mode` 请求头，而不是服务端**实际将要应用**的保留模式——于是一条本用于约束保留策略的条件，读到的是调用方自己选的值。

修复是把顺序反过来：先精确匹配条件键本身的拼写，规范形式仅作为回退，供真正命名请求头的条件键（`s3:x-amz-*` 一族）使用。这是上游 [minio/pkg#226](https://github.com/minio/pkg/pull/226) 的移植，并补充了上游没有携带的回归测试。

在库的原始 map 查找层，如果生产者同时以“条件键原名”和“规范 MIME 名”存入同一个逻辑字段，现在精确名称会优先。这只是库级查找规则，不应被理解为 S3 协议规定“查询参数优先”。Silo 服务端会先按字段的真实来源归一化条件值：对于仍兼容 Header 与 query 两种形式的存储类别和上传标签，**Header 只要存在就优先（包括空值）**，否则才回退到 query。

## LDAP 连接路径 {#ldap}

本轮修复了 `connect()` 上的三个缺陷。其中两个由本分支在 `b0c08a7` 中引入、随 v3.6.2 与 v3.6.3 一同发布，**建议使用这两个版本的用户尽快升级**。

**StartTLS 在 `ServerInsecure` 打开时被跳过。** 上游在外层代码块中调用 `StartTLS`，只由 `ServerStartTLS` 决定，因此两个开关同时打开时会先明文连接、再升级。`b0c08a7` 把该调用挪进了 `else` 分支，于是 `ServerInsecure` 一旦打开就永远够不到它：连接保持明文，随后的 bind 把凭据明文发到线路上。MinIO 通过 `MINIO_IDENTITY_LDAP_SERVER_INSECURE` 与 `MINIO_IDENTITY_LDAP_SERVER_STARTTLS` 独立暴露这两个开关且独立解析，`Validate()` 不拒绝任何组合，所以这个组合是可达的。

本版本恢复上游的语义：两个开关是**叠加**而非冲突——`ServerInsecure` 表示不使用隐式 `ldaps://`，`ServerStartTLS` 依然执行升级。因此暴露窗口仅限 v3.6.2 和 v3.6.3 两个版本。

**未设置 TLS 段的 Config 会在 `ldaps://` 路径上 panic。** `l.TLS.Clone()` 被移出 StartTLS 分支后，普通 `ldaps://` 也会走到它；`Clone()` 对 nil 接收者返回 nil，下一行却给 `ServerName` 赋值。MinIO 服务端总是填充 TLS，但这是个库，`mc` 也在用。现在回退到空的 `tls.Config`，即 `DialURL` 本来会构造的那个。

**StartTLS 没有 deadline。** go-ldap 仅在 `requestTimeout > 0` 时才启动请求计时器，而 `StartTLS` 自身没有超时，因此一个完成 TCP 握手后再不应答扩展请求的服务器会永久占住 connect 协程。计时器现在在调用 `StartTLS` 之前武装。

**StartTLS 失败时泄漏连接。**（继承自上游，非本分支引入）拨号失败不会返回连接，所以 StartTLS 失败是 `connect()` 唯一可能同时返回连接和错误的路径。所有调用方都只在错误为 nil 时接管连接，于是每一次针对升级异常的服务器的登录尝试，都会遗留一个套接字。现在失败即关闭并返回 nil。

## 其他修复 {#other-fixes}

- **certs：文件监听器从未被停止。** `Manager.AddCertificate()` 注册两个 `notify.Watch()` 且从不停止：第二个失败时第一个泄漏，管理器关闭后两个都会驻留至进程结束。`Certificate.Watch()` 与 `watchFile()` 同样如此。现在四处统一走返回 stop 函数的 `watchDirSafe()`，错误路径与 `ctx.Done()` 都会调用。移植自上游 [minio/pkg#228](https://github.com/minio/pkg/pull/228) 的 `certs/` 部分。注意 Windows 上该函数并非在失败时才回退到轮询，而是直接取代文件系统通知，因此证书重载延迟最长为一个 `symlinkReloadInterval`（10 秒）；本分支没有 Windows CI，该平台仅做过交叉编译验证。
- **rng：读取器子密钥来自一个归零的局部变量。** `init()` 把 32 字节熵读进 `r.tmp`，却从同名的归零局部变量派生四个子密钥，导致子密钥恒为零，四条 per-block 通道塌缩成一条，`Reset()` 与 `ResetSize()` 会逐字节重放上一段流。MinIO 经由 `randreader.New()` 使用它，每次调用新建读取器且从不 reset，因此实际影响有限；该问题由 warp 暴露。移植自上游 [minio/pkg#230](https://github.com/minio/pkg/pull/230)。
- **xtime：`Duration` 有 `UnmarshalJSON` 却没有 `MarshalJSON`。** 编码时输出纳秒整数，而解码器无条件剥掉首尾各一个字节、期待一个带引号的字符串，于是往返在两个方向上都失败。现在按 `time.Duration` 自身的字符串形式编码，两者对称。移植自上游 [minio/pkg#242](https://github.com/minio/pkg/pull/242)。

## 兼容性影响 {#compatibility}

- **最低 Go 版本从 `1.26.1` 降到 `1.25.0`。** go 指令中的补丁号是对每个消费者的硬性下限，而不是"本模块用什么构建"的记录；后者的惯用写法是 `go` 行写语言版本、`toolchain` 行单独写开发版本。`1.25.0` 是依赖实际要求的版本，也是上游声明的版本。CI 中新增了一个在 `GOTOOLCHAIN=local` 下用 Go 1.25 构建全量测试的任务，这个下限是被验证过的，而不是口头声明。
- **`xtime.Duration` 的 JSON 线格式发生变化**，从纳秒整数变成时长字符串（如 `"2h"`、`"30m"`）。此前以数字形式持久化过这些字段的数据将无法读回。MinIO 与 `mc` 中未发现此类用法：批处理作业定义以 YAML 持久化，msgp 路径仍是 int64。
- **同时打开 `ServerInsecure` 与 `ServerStartTLS`、且 LDAP 服务端不支持 StartTLS 的部署**，此前（仅在 v3.6.2/v3.6.3 上）以明文连接成功，现在会连接失败。这是正确结果，但它在 connect 时才暴露，而非配置校验时。请为这类服务端关闭 `ServerStartTLS`。

## 服务端配套行为 {#server-side}

- 本版本的策略改动**必须**与服务端保留内部条件键名、按语义来源填值的改动配套，见文首提示。
- `s3:signatureAge` 只在 SigV4 预签名请求校验器完成计算后提供；其他请求类型中客户端自行提供的 `x-amz-signature-age` Header 会被忽略。
- `s3:prefix`、`s3:delimiter`、`s3:max-keys` 只来自 query；内容哈希、复制源、元数据指令、SSE 与对象锁条件只来自对应 Header。预签名校验消费的 `X-Amz-Content-Sha256` query 值不会进入策略条件。
- `s3:x-amz-storage-class` 继续兼容 query；`PutObject` 与 `CreateMultipartUpload` 的请求标签也保留既有 query 形式。两类字段均以 Header 是否存在为优先级，只有 Header 不存在时才回退到 query。
- `s3:ExistingObjectTag/*` 只来自服务端读取到的已有对象标签，请求自己的 `X-Amz-Tagging` 不能再冒充已有对象状态。`PutObject`、`CreateMultipartUpload` 与 `PutObjectTagging` 会把 `s3:RequestObjectTag/*` 绑定到各自实际消费的标签输入；无关 query 标签会被忽略。为了兼容，其他 action 路径仍保留历史 `X-Amz-Tagging` Header 回退，因此只能在 API 确实消费标签时把请求标签条件当作约束。完整矩阵见[条件值来源与优先级](/zh/administration/identity-access-management/policy-based-access-control/#condition-value-sources)。
- `aws:SourceIp` 由 `X-Forwarded-For`、`X-Real-IP` 与 `Forwarded` 计算得出，没有受信代理边界，其中第一个默认启用、后两个完全不设限。因此在可被直接访问的部署上，`IpAddress` 条件是**不可强制执行**的。请把 MinIO 放在会覆写这些请求头的反向代理之后。

## 依赖与工程 {#deps-and-tooling}

依赖更新清除了 govulncheck 报告的九个**可达**漏洞：经由 `sftp` 到达的七个 `x/crypto/ssh` 问题、经由 etcd 到达 gRPC 的 GO-2026-6061、经由 oidc 到达 go-jose 的 GO-2026-4945。仅剩一个模块级提示 GO-2026-5932（`x/crypto/openpgp`），该模块已停止维护、没有修复版本，且本仓库并未导入。

`minio-go`、`minio/mux`、`etcd client/v3`、`go-oidc`、`lestrrat-go/jwx` 五个依赖**刻意不升**：MinIO 通过 `replace` 消费本模块，而 MVS 取整个依赖图中的最大值，这里升一步会把服务端一起拖走，而它们都没有已报告的漏洞。

工程方面：三个 workflow 此前都在向 `setup-go` 索要比 `go.mod` 要求更低的 Go 版本，每次运行都在第一条 go 命令上失败——CI 是红的，不是静默的，现在已修正。linter 此前从 master 分支拉取安装脚本，等于每次构建都执行当天的远端脚本，且每次都重装；现在脚本 URL 与版本一并固定到 `v2.11.3`，已安装正确版本时跳过下载，`make test` 恢复为可完整跑通的入口。

## 有意不从上游采纳的内容 {#not-taken}

- AIStor 的策略词表（Memory/cortex、Tables/Iceberg、KMS、压缩、annotations）以及带类型的 action 常量重构——社区版服务端均未实现。
- `securityAuditAdmin`：它授予 `admin:ExportIAM`，因而会泄露全部 secret key，与名字给人的印象相反。
- rng 的 AVX2/NEON 汇编：该路径本就快过任何磁盘，收益为零，且无法在本项目的硬件与 CI 上验证。
- `net` 的 `BandwidthBytesPerSec`（上游只声明未读取）、`replicationAdmin`、`DistJobStatusAction`。
- 上游的 golangci-lint `tool` 指令：它会把约 200 个 lint 依赖拖进每一个下游消费者的模块图。
- 曾经采纳、复审后撤回的两项：`consolereadonly` 预置策略与 `GetAllGlobalCertificates`，两者都没有消费者。预置策略一旦被运维绑定到用户身上就几乎无法撤回——策略映射按名字持久化，名字解析不到时会合并成空策略，而空策略拒绝一切；且它继承的 `admin:CreateUser` Deny 与 `iamAdmin` 无法组合。证书辅助函数则清点了一个社区版服务端从不填充的缓存。

## 关联提交 {#related-commits}

- [5c4bf50](https://github.com/pgsty/silo-pkg/commit/5c4bf503d5d5701327527f030a3c755266d741f1)：fix(policy): prefer the exact key name over the canonical header form
- [045d10f](https://github.com/pgsty/silo-pkg/commit/045d10fd974760153024cd7d519919440c28c5cb)：fix(ldap): guard a nil TLS config and arm the StartTLS deadline
- [424c3d0](https://github.com/pgsty/silo-pkg/commit/424c3d06057b579631a4a8a81ffae9985875f477)：fix(ldap): close the connection when StartTLS fails
- [74dd36e](https://github.com/pgsty/silo-pkg/commit/74dd36e78a829782b6f04ad09fd908386e13c693)：fix(ldap): keep StartTLS when ServerInsecure is also set
- [88b37ac](https://github.com/pgsty/silo-pkg/commit/88b37ace8a14a511e09b9b30567cde8e5bfa2398)：fix(certs): stop file watchers on every exit path
- [13c26cd](https://github.com/pgsty/silo-pkg/commit/13c26cda3db1e36bb3b7904217271a32b73039b7)：fix(rng): initialize the reader subkeys from the seeded entropy
- [4055b2f](https://github.com/pgsty/silo-pkg/commit/4055b2f7d5a33948004ac13a933aa978b57399e6)：fix(xtime): marshal Duration as a duration string
- [802539f](https://github.com/pgsty/silo-pkg/commit/802539f36d723802c80dea3c18c88da33c5d87d4)：chore(deps): refresh the dependency set and declare the real minimum Go
- [e4ec64a](https://github.com/pgsty/silo-pkg/commit/e4ec64a9453d9ad469f6fd4ece93b2462bd118ef)：ci: build on the Go version go.mod requires, and prove the declared minimum
- [747d8b8](https://github.com/pgsty/silo-pkg/commit/747d8b865ca937f227b0f70aeec9f8b49d05f55d)：build: pin the golangci-lint installer and skip a matching install
- [da6a22a](https://github.com/pgsty/silo-pkg/commit/da6a22a10143f2e23764c59f39306e9ac3282da5)：docs: say what this fork is and how to depend on it
