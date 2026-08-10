---
title: "Silo Pkg 3.11.0 发布"
linkTitle: "silo/pkg 3.11.0"
date: 2026-08-04
author: "冯若航"
description: "本分支的首个定版：恢复被打破的 IAM 桶/对象资源边界——一条只该管对象的授权曾能触及桶级写操作；同时包含策略条件键绕过与三个 LDAP 连接缺陷的修复；并在发现旧标签与上游同号版本撞车后，重新编号到上游的 3.11 线。"
tags: [发布, pkg]
weight: 5
url: "/zh/blog/release/pkg-3.11.0/"
aliases:
  - /releases/pkg-3.11.0/
---

**发布日期：** 2026-08-04 · **版本：** [v3.11.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.11.0) · **提交：** [`d8b1fa7`](https://github.com/pgsty/silo-pkg/commit/d8b1fa7) · **仓库：** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

这是本分支的 **第一个定版**。它恢复了上游 [minio/minio#20449](https://github.com/minio/minio/issues/20449) 所报告的 IAM 桶/对象资源边界：策略条件键绕过修复、三个 LDAP 连接缺陷、证书监听器泄漏、有种子 RNG 的缺陷，以及模块真实的最低 Go 版本。

{{% alert color="warning" %}}
**升级前需要确认两件事**

1. **本版本收紧了鉴权。** 十二个桶级写操作不再能通过 `arn:aws:s3:::bucket/*` 这样的对象级资源模式被授权。如果你自己编写桶级策略，请阅读 [IAM 桶/对象边界](#bucket-boundary)——受影响者只需改一行策略，而 `MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` 可完整恢复原有行为。
2. **条件键修复仍需服务端另一半。** 本版本的策略解析改动与服务端"保留内部条件键名"的改动各自覆盖问题的一半。服务端配套改动位于 `pgsty/minio` 提交 `2f55347f7`，但尚未进入公开的 `origin/master`，也没有任何已发布的 Silo 服务端版本包含它。请确认后续服务端发布说明明确包含该改动。
{{% /alert %}}

## 这个仓库是什么 {#what-is-this}

`silo-pkg` 是 [minio/pkg](https://github.com/minio/pkg) 的维护分支，为社区版 MinIO 分支提供上游（现由闭源产品驱动）不会再接纳的修复。仓库于 2026-08-02 由 `pgsty/minio-pkg` 改名而来。

**模块路径刻意保持不变**，仍然是 `github.com/minio/pkg/v3`，因此所有 `import "github.com/minio/pkg/v3/..."` 无需改动，只有 `replace` 指令的右侧需要更新：

```go
replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.11.0
```

`/v3` 后缀是模块的主版本号，不是目录名，不可省略。这也正是本次发布编号为 `v3.11.0` 而非 `v4.0.0` 的原因：Go 要求标签的主版本必须与 `go.mod` 中声明的主版本后缀一致，因此在一个 `.../v3` 模块上打 `v4.0.0` 会被工具链直接拒绝。真要发布 `v4`，就必须修改模块路径，并改写服务端、`mc` 与 Console 中约 395 处 import——那等于放弃"保留上游路径"所换来的直接替换能力，而这正是保持上游路径的意义所在。

## IAM 桶/对象边界 {#bucket-boundary}

每一个桶级 S3 操作，鉴权时对象名都是空的。IAM 匹配器把它拼成资源串，而对空对象名的情况补了一个尾斜杠：

```go
resource.WriteString(args.BucketName)
if args.ObjectName != "" {
    // "bucket/object"
} else {
    resource.WriteByte('/') // "bucket/"  <-- 缺陷所在
}
```

`"bucket/"` 会被通配模式 `"bucket/*"` 命中，因为 `*` 匹配空串。于是一条把 `s3:*` 授在 `arn:aws:s3:::bucket/*` 上的策略——读起来是 *"任意操作，但只作用于这个桶里的对象"*——也连带授予了桶级操作。在多租户集群里，只持有这条授权的租户可以调用 `PutBucketPolicy` 装上 `{"Principal":"*"}`，把桶变成匿名公网可读或可写，或者给自己授予桶级控制权；它也可以直接把桶删掉，而这正是上游 issue 中的复现步骤。

匿名访问所走的桶策略评估路径从来没有这个斜杠，是正确参照。只有 IAM 这条路径错了，而且只错在一个地方。

### 为何不修正整条边界 {#why-narrow}

对所有桶级请求都不再补斜杠，是显而易见的修法，上游也试过：那次改动当天就因打破依赖旧行为的策略而被回滚。有两个性质让"完整修正"成为一次迁移，而不是一个补丁。

**它会撤销真实部署所依赖的授权。** 它撤销的不只是危险的桶写入——通过 `bucket/*` 授予的 `ListBucket`、`GetBucketLocation`、`ListBucketMultipartUploads` 同样会被撤销。证据就是上游自己的测试套件：11 个 STS 集成测试把 `s3:ListBucket` 授在 `bucket/*` 上，然后断言列举能成功。连写服务端的项目都这么写，生产策略里只会更多。

**它切的是两个方向。** 匹配器对 `Allow` 和 `Deny` 拼的是同一套资源串，所以删掉斜杠在收紧过度授予的 `Allow` 的 *同时*，也放松了过度阻断的 `Deny`。一个用 `Deny s3:* on bucket/*` 锁死某个桶的管理员，会悄无声息地失去那层保护。

### 保护集合是如何确定的 {#protected-set}

范围由一个问题决定：**够到这个动作，能让调用者拿到它的对象级授权本来就给不了的东西吗？**

之所以该问这个问题，取决于缺陷的触发条件。资源匹配发生在动作匹配 *之后*，所以这个 bug 只有在语句本身已经授予了那个桶级动作时才会咬人——现实中这意味着 `s3:*`。因此受影响的主体本就对这个桶里的每个对象拥有完整的读、写、删权限。有用的问题不是"这个动作抽象地看有多危险"，而是"在一个已经握有全部数据的位置上，够到它还能多拿到什么"。

**不再接受对象级授权的十二个动作：**

| 动作                                                                            | 入选理由                                                                                        |
|:------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------|
| `PutBucketPolicy`、`DeleteBucketPolicy`                                        | 能把访问权发给别的主体（包括匿名），也能给调用者自己补上从未授予的桶级动作。自我提权与公开暴露。                                            |
| `PutBucketObjectLockConfiguration`、`PutBucketVersioning`                      | 击穿的恰恰是专门用来"防住有写权限的人销毁数据"的保护。                                                                |
| `PutReplicationConfiguration`、`PutLifecycleConfiguration`                     | 以服务端凭据运行，并在调用者权限被吊销后继续生效。                                                                   |
| `DeleteBucket`、`ForceDeleteBucket`                                            | 不可逆地销毁桶实体及其配置。上游 issue 的原始复现动作。                                                             |
| `PutBucketCors`、`DeleteBucketCors`、`PutBucketQOS`、`PutInventoryConfiguration` | 在今天的服务端没有挂任何行为——要么根本没有 handler，要么 handler 在鉴权之后直接返回 `NotImplemented`。收走它们不影响任何能用的东西，并且提前覆盖。 |

**刻意不予保护**，并且有测试对此做出断言——于是把其中任何一个加回去，都是一次带可见代价的明确决定，而不是往列表里添一行：

- **`PutBucketTagging`、`PutBucketEncryption`、`PutBucketNotification`。** 它们都是桶级写入，早期草案确实纳入过保护。三者都不给调用者任何它还没有的访问权——受损的是所有者的合规姿态，不是访问边界；而一个拿到 `s3:*` on `bucket/*`、并被告知"这个桶归你"的租户，完全合理地会去给它打标签、设默认加密、配事件通知。用很低的安全收益去换实打实的兼容成本，在维护版本里是个错误的交易。
- **`CreateBucket`。** 它作用于一个还不存在的桶，没有东西可篡改、可摧毁；而供应流程常用租户自己的 `bucket/*` 凭据去创建租户的桶。
- **读/列举族**（`ListBucket`、`GetBucketLocation`、各类配置读取）。打破它们正是上游那次完整修复被回滚的原因，它们要等一次带迁移路径的发布。

改动只作用于 `Allow` 语句。`Deny` 语句保持历史资源串，因此任何桶级封锁都不会被削弱，`NotResource` 排除也保持完整覆盖范围。

### 单调性，以及那个错了两次的论断 {#monotonicity}

上面这一切都建立在一条性质上：**这个变更可以收走权限，但绝不能新增权限。** 而这条性质被断言过两次，两次都是凭推理而非凭测试，也两次都是错的。把"怎么错的"记录下来，比只记录最终状态更有价值。

第一次尝试让省略的斜杠同样作用在了 **`NotResource`** 匹配上——而 `NotResource` 是 *排除*。`Allow s3:* NotResource bucket/*` 这样的语句，历史上不会作用于该桶的桶级请求；把排除拿去和裸桶名匹配，排除就不再命中，于是它所限定的那条 `Allow` 反而变宽了，而且恰恰是在受保护的那些写入上。

第二次尝试修好了这一处，并在发布时写着结论"可证明地单调"。对该版本做的独立对抗性复核给出了反例。省略斜杠并不只是"少了一次匹配"——它改变了 *模式所匹配的那个字符串*，而一个模式完全可能匹配 `"mybucket"`，却从来匹配不上 `"mybucket/"`。定长通配是最干净的例子：

```text
Allow s3:PutBucketPolicy on arn:aws:s3:::mybucke?
```

`?` 恰好匹配一个字符。对九字符的 `"mybucket/"` 它匹配不上，所以这条语句从来没有授予过那个桶级写入；而对八字符的 `"mybucket"` 它匹配上了，于是这次加固 *授予了* 有缺陷的匹配器都拒绝的东西。

修法不是再加一个特例。在受保护路径上，匹配器现在要求 **两种形式同时命中**——裸桶名，以及历史的 `"bucket/"`。结果是与历史判定取交集，于是它 **在构造上** 就是单调的：不存在任何它能新满足的模式，也不再有下一次会推理错的论证。`mybucket*` 照旧授予（它本来两种形式都匹配），`mybucket/*` 照旧被收走，`mybucke?` 被拒绝——和它一直以来的行为一样。

有两点值得带走。**鉴权路径上的正确性修复，绝不能让任何东西变成新允许的**——而确认它的唯一办法是把两个方向都测一遍，因为在这两次里，推理给人的感觉都是无懈可击的。以及：当一条安全性质是承重的，就 **用一个不可能违反它的操作把它构造出来**，而不是用一份你认为已经穷尽的分情况讨论。

### 证据 {#bucket-boundary-evidence}

这条性质是被验证的，不是被论证的。我们生成了一份 **27000 条鉴权判定** 的语料——15 种资源模式 × 3 个桶 × 5 种对象名 × 20 个动作 × 6 种语句形式——分别在加固前基线与本版本上执行，并逐条比对：

| 迁移方向               |    条数 |
|:-------------------|------:|
| `false → true`（变宽） | **0** |
| `true → false`（收窄） |   144 |
| 不变                 | 26856 |

那 144 条收窄全部落在设计意图之内，没有一条溢出：动作恰好是受保护的十二个；语句形式只有三种 `Allow`，`Deny`、`NotResource` 排除与 deny-`NotResource` 三种形式 **零变化**；资源模式只有四种对象级模式；请求只有桶级请求，对象级请求完全未被触碰。12 × 4 × 3 = 144，严丝合缝。

两个层次都有回归测试。本仓库有十二条匹配器测试钉死每个方向，其中包括一条不变量测试，确保受保护动作个个都是纯桶级动作——`ResetBucketReplicationState` 名字唬人，实为对象动作，不入集合。服务端有三条端到端测试驱动真实 handler，分别位于客户端、内联会话策略与 S3 路由三个层次；三条在修复前的构建上全部失败，在本版本上全部通过。

### 需要改什么 {#bucket-boundary-upgrade}

只有当你的存量策略把十二个动作之一（或 `s3:*`）授在含 `/` 的资源模式上、且同一个桶没有裸桶 ARN 时，你才会受影响。修法是在对象模式旁边补上裸桶 ARN：

```json
"Resource": ["arn:aws:s3:::bucket", "arn:aws:s3:::bucket/*"]
```

这种配对写法是惯例形式，也是上游自己的测试所采用的写法，在本版本之前同样有效。内置策略不受影响——`readwrite`、`readonly`、`writeonly`、`diagnostics` 全部使用 `Resource: "*"`。

`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH=on` 在启动时读取一次，可完整恢复历史匹配行为——过度授予与过度阻断两个方向一并恢复。它目前是单一的全局开关，按动作粒度的作用域[已列入待办](#deferred)。

## 策略条件键解析顺序 {#policy-condition-key}

`getValuesByKey()` 此前会先按规范 MIME 拼写（`http.CanonicalHeaderKey`）查找策略条件键，再尝试原始名称。而它读取的那张表里，混放着服务端为当前请求计算出的值（`SourceIp`、`SecureTransport`、`CurrentTime`、`username` 等，以条件键拼写存储）和请求自带的 HTTP 头（以规范 MIME 拼写存储）。

**先查规范拼写，就让客户端的请求头能够覆盖服务端算出来的值。**

对 MinIO 服务端而言这是一次策略绕过。最简单的例子是 `s3:prefix`：一个 `Prefix` 请求头可以满足家目录前缀条件，而真正的 `?prefix=` 查询参数仍然列举整个桶。同一条路径还能触及 `aws:SourceIp`、`aws:SecureTransport`、`aws:CurrentTime`、`aws:EpochTime`、`aws:username`、`aws:userid`、`aws:principaltype`、`aws:UserAgent`、`aws:groups`、`ldap:username`、`ldap:groups`、`jwt:groups`、`s3:versionid`、`s3:signatureversion`、`s3:signatureAge`、`s3:authType` 与 `s3:LocationConstraint`。匿名桶策略直接暴露。SigV4 也拦不住，因为客户端可以添加不在 `SignedHeaders` 列表里的头。

还有第二重后果：当服务端以一种拼写存值、而策略键解析到另一种拼写时，错误的条目会胜出。`s3:object-lock-mode` 可能解析到调用者的 `X-Amz-Object-Lock-Mode` 请求头，而不是服务端实际会施加的保留模式。

修复反转了查找顺序：先精确匹配条件键本身的名字，只对确实指代请求头的条件键（例如 `s3:x-amz-*` 家族）才回退到规范拼写。这移植了 [minio/pkg#226](https://github.com/minio/pkg/pull/226)，并补上了上游那次改动没有携带的回归测试。

在库的原始映射层面，如果生产者把同一个逻辑字段同时以精确条件名和规范 MIME 名存入，现在精确名胜出。这是一条库层查找规则，不是"查询参数优先"的 S3 线缆协议规则。Silo 服务端会先按真实来源规范化条件值。对于存储类别与上传标签这两处 Header 与查询形式都保持兼容的字段，**Header 只要出现就胜出，包括空值**，查询参数仅作回退。

## LDAP 连接路径 {#ldap}

`connect()` 中的三个缺陷，其中两个由本分支自己在 `b0c08a7` 中引入，随 v3.6.2 与 v3.6.3 发布。**使用这两个版本的用户应尽快升级。**

**`ServerInsecure` 开启时 StartTLS 被跳过。** 上游把 `StartTLS` 调用放在只由 `ServerStartTLS` 控制的外层块里，因此同时开启两个选项时，会先建立明文连接再升级。`b0c08a7` 把该调用移进了 `else` 分支，导致只要 `ServerInsecure` 为真，StartTLS 就不可达。连接保持明文，随后的 bind 就在这条连接上发送了凭据。MinIO 的 `MINIO_IDENTITY_LDAP_SERVER_INSECURE` 与 `MINIO_IDENTITY_LDAP_SERVER_STARTTLS` 是独立开关，`Validate()` 不拒绝任何组合，所以这个状态是可达的。

本版本恢复了上游语义：两个开关是 **叠加关系，而非互斥**。`ServerInsecure` 关闭隐式 `ldaps://`；`ServerStartTLS` 仍然执行升级。暴露窗口仅限 v3.6.2 与 v3.6.3。

**没有 TLS 配置段的 Config 可能在 `ldaps://` 路径上 panic。** `l.TLS.Clone()` 移出 StartTLS 分支之后，普通 `ldaps://` 连接也会调用它。`Clone()` 对 nil 接收者返回 nil，而下一行却给 `ServerName` 赋值。MinIO 服务端总会提供 TLS 设置，但这是一个库，`mc` 同样在消费它。现在代码会回退到空的 `tls.Config`，与 `DialURL` 本来会构造的一致。

**StartTLS 没有超时。** go-ldap 只在 `requestTimeout > 0` 时才启动请求计时器，而 `StartTLS` 本身没有超时。一台完成了 TCP 建连、随后对扩展请求不再响应的服务器，可以让连接 goroutine 永久挂住。现在计时器在 `StartTLS` 之前就已武装。

**StartTLS 失败会泄漏连接。** 这一条继承自上游。拨号失败不会返回连接，因此 StartTLS 失败是 `connect()` 里唯一可能同时返回连接与错误的路径。调用方只在错误为 nil 时接管所有权，于是对一台升级功能损坏的服务器，每次登录尝试都会遗留一个 socket。失败路径现在会关闭连接并返回 nil。

## 其它修复 {#other-fixes}

- **certs：文件监听器从未被停止。** `Manager.AddCertificate()` 注册了两个 `notify.Watch()` 却一个都不停：如果第二个失败，第一个就泄漏；而且两个都会在 manager 关闭后一直存活到进程退出。`Certificate.Watch()` 与 `watchFile()` 有同样的问题。四条路径现在统一使用 `watchDirSafe()`，它返回一个在出错与 `ctx.Done()` 时被调用的停止函数。这移植了 [minio/pkg#228](https://github.com/minio/pkg/pull/228) 的 `certs/` 部分。在 Windows 上该函数用轮询替代文件系统通知，而不是把轮询仅作为失败回退，因此证书重载可能滞后一个 `symlinkReloadInterval`（10 秒）。本分支没有 Windows CI，该平台仅做了交叉编译。
- **rng：reader 的子密钥取自一个被清零的局部变量。** `init()` 把 32 字节熵读进 `r.tmp`，却从一个同名的、已清零的局部变量派生出四个子密钥，把四条按块划分的流坍缩成了一条。随后 `Reset()` 与 `ResetSize()` 会逐字节重放上一条流。MinIO 每次 `randreader.New()` 都创建新的 reader 且从不 reset，因此实际服务端影响有限；这个缺陷是 warp 暴露出来的。这移植了 [minio/pkg#230](https://github.com/minio/pkg/pull/230)。
- **xtime：`Duration` 实现了 `UnmarshalJSON` 却没有 `MarshalJSON`。** 编码产出的是纳秒整数，而解码无条件剥掉首尾各一个字节并期待带引号的字符串，两个方向都无法往返。现在它使用 `time.Duration` 的字符串形式编码。这移植了 [minio/pkg#242](https://github.com/minio/pkg/pull/242)。

## 兼容性影响 {#compatibility}

- **十二个桶级写操作不再能通过对象级资源模式获得授权。** 见[需要改什么](#bucket-boundary-upgrade)。对象访问、`ListBucket`、`CreateBucket`、桶标签、默认加密与事件通知均不受影响，`Deny` 语句与 `NotResource` 排除同样不受影响。
- **最低 Go 版本从 `1.26.1` 降回 `1.25.0`。** `go` 指令里的补丁号对每一个消费者都是硬性下限，而不是构建该模块所用工具链的记录。惯例做法是 `go` 行写语言版本、单独的 `toolchain` 行写开发版本。`1.25.0` 才是依赖图实际要求的版本，也是上游声明的版本。CI 会在 `GOTOOLCHAIN=local` 下用 Go 1.25 构建完整测试套件，因此这个下限是被证明的，而不是宣称的。
- **`xtime.Duration` 的 JSON 线缆格式变更**，从纳秒整数改为 `"2h"`、`"30m"` 这样的时长字符串。已持久化的数值形式无法再读回。在 MinIO 与 `mc` 中未发现此类用法：批处理作业定义以 YAML 持久化，msgp 路径仍为 int64。
- **同时开启 `ServerInsecure` 与 `ServerStartTLS`、且 LDAP 服务器不支持 StartTLS 的部署**，在 v3.6.2/v3.6.3 上会以明文成功连接，现在则连接失败。这是正确结果，但它暴露在连接阶段而非配置校验阶段。对这类服务器请关闭 `ServerStartTLS`。
- **`Policy.IsAllowedActions` 对那十二个受保护动作可能与直接判定不一致。** 它遍历 `SupportedActions`，其中包含 `s3:*` 这个模式本身，因此返回的集合可能包含 `s3:*`——从而看起来允许某个受保护动作——而直接求值却是拒绝。服务端没有任何地方调用它，Console 调用时传的是空桶名，永远走不到加固分支。此处选择记录而非修改：在维护版本里改变一个公开 API 的输出，风险更大。

## 与上游 v3.11.0 的差异 {#divergence}

版本号跟随上游的线，不声称内容一致。以 `policy/` 下的动作字符串常量为口径，实测差异如下：

|                        |  数量 |
|:-----------------------|----:|
| 上游 `minio/pkg` v3.11.0 | 291 |
| `silo-pkg` v3.11.0     | 270 |

**有 24 个动作只存在于上游：** 6 个 `s3:*ObjectAnnotation*`、5 个 `admin:` 动作（`DistJobStatus`、`Get`/`SetBucketCompression`、两个 `TablesReplication*`），以及 13 个覆盖函数 CRUD 与打标签的 `s3tables:` 动作。它们属于本分支刻意不采纳的 AIStor 词表，因为社区版服务端并不实现这些功能。

**有 3 个动作在两侧名称不同。** 上游对它们做了改名与拆分，本分支保留较早的名称：

| `silo-pkg` v3.11.0             | 上游 `minio/pkg` v3.11.0                                      |
|:-------------------------------|:------------------------------------------------------------|
| `s3tables:TagResource`         | `s3tables:TagTable`、`s3tables:TagWarehouse`                 |
| `s3tables:UntagResource`       | `s3tables:UntagTable`、`s3tables:UntagWarehouse`             |
| `s3tables:ListTagsForResource` | `s3tables:ListTagsForTable`、`s3tables:ListTagsForWarehouse` |

因此，一条写了这六个动作名之一的策略，在两者之间 **只有一个** 能通过校验。Silo 服务端、`mc` 与 Console 都没有引用它们，所以在本生态内没有影响；但从上游 v3.11.0 切换过来的消费者应当知道，动作词表并不可互换。

**rng 没有 arm64 汇编。** 上游在本分支分叉点之后加入了 `rng/xor_arm64.{go,s}`，本版本在 arm64 上回退到纯 Go 的 `xor_noasm.go` 路径。结果正确、交叉编译干净，但在该架构上比上游慢。它是未来同步的一个干净候选：纯性能改动，不牵涉词表分歧。

## 服务端配套行为 {#server-side}

- 本版本的条件键改动 **必须** 与服务端"保留内部条件键名、按语义来源填充取值"的改动配对，见文首提示。
- `s3:signatureAge` 只有在 SigV4 预签名请求校验器算出它之后才会暴露。在其它任何请求类型上，客户端提供的 `x-amz-signature-age` 头都会被忽略。
- `s3:prefix`、`s3:delimiter`、`s3:max-keys` 只来自查询参数。内容哈希、拷贝源、元数据指令、SSE 与对象锁条件只来自对应的请求头。校验预签名请求时消费的 `X-Amz-Content-Sha256` 查询值不会成为策略条件。
- `s3:x-amz-storage-class` 保留其兼容的查询形式，`PutObject` 与 `CreateMultipartUpload` 上的请求标签同样保留。这两个字段都是 Header 出现即胜出，只有 Header 缺失时才使用查询参数。
- `s3:ExistingObjectTag/*` 只来自从已存储对象加载的标签，因此请求自带的 `X-Amz-Tagging` 不能再冒充既有对象状态。`PutObject`、`CreateMultipartUpload` 与 `PutObjectTagging` 把 `s3:RequestObjectTag/*` 绑定到这些 handler 实际消费的标签输入。其余动作路径出于兼容保留了历史的 `X-Amz-Tagging` 头回退，因此只在 API 确实消费标签的地方，才把请求标签条件当作约束使用。
- `aws:SourceIp` 由转发头计算得出。它是否可强制执行，取决于服务端的可信代理配置；参见服务端自己关于 `MINIO_API_TRUSTED_PROXIES` 的发布说明。

## 验证 {#verification}

以下全部在打标签的那个提交上执行，工作树干净，标签与 `HEAD` 一致：

- `make test`——golangci-lint 加 `go test -race -tags kqueue ./...`，全部包通过。
- `go mod tidy -diff` 干净；`gofmt -l` 为空；`go vet ./...` 干净。
- `linux/amd64`、`linux/arm64`、`darwin/arm64`、`windows/amd64` 四个组合的交叉编译。
- `govulncheck ./...`——零个可达漏洞。仅剩一条模块级提示 GO-2026-5932（`x/crypto/openpgp`）：该包已停止维护、没有修复版本，且本仓库并未 import 它。
- 从空模块缓存经公共 proxy 解析，确认发布出去的版本确实可获取。
- [上文所述](#bucket-boundary-evidence)的 27000 条鉴权判定语料。

## 依赖与工具链 {#deps-and-tooling}

依赖更新清除了 `govulncheck` 此前报告的九项 **可达** 问题：经 `sftp` 触达的七个 `x/crypto/ssh` 问题、经 etcd 触达的 gRPC GO-2026-6061，以及经 oidc 触达的 go-jose GO-2026-4945。

有五个依赖——`minio-go`、`minio/mux`、`etcd client/v3`、`go-oidc`、`lestrrat-go/jwx`——刻意未升级。MinIO 通过 `replace` 消费本模块，而最小版本选择会取整个依赖图中的最高版本，因此在这里升级它们会连带把服务端也拽着往前走。这五个都没有必须升级的已报告漏洞。

三个工作流此前都向 `setup-go` 索要低于 `go.mod` 要求的 Go 版本，并在第一条 Go 命令上失败，现已对齐。linter 此前还从 master 分支拉取安装脚本并每次重装；URL 与版本现已固定到 `v2.11.3`，且当已安装版本匹配时会跳过下载。

## 刻意未采纳的上游改动 {#not-taken}

- AIStor 策略词表（Memory/cortex、Tables/Iceberg、KMS、压缩与注解）以及带类型的动作常量重构，社区版服务端均不实现。这也是[动作词表差异](#divergence)的来源。
- `securityAuditAdmin`：它授予 `admin:ExportIAM`，因而会暴露每一个密钥，与名字给人的印象相反。
- rng 的 AVX2/NEON 汇编。其中 arm64 那一半已在上文列为未来同步候选。
- `net.BandwidthBytesPerSec`（上游声明了却从未读取）、`replicationAdmin` 与 `DistJobStatusAction`。
- 两项先采纳、复核后又移除的改动：`consolereadonly` 内置策略与 `GetAllGlobalCertificates`，两者都没有消费者。一旦运维把内置策略名绑定到用户身上，再撤回就格外危险：策略映射按名字持久化，而无法解析的名字会并入一个拒绝一切的空策略；它继承的 `admin:CreateUser` Deny 也无法与 `iamAdmin` 组合使用。那个证书辅助函数清点的是社区版服务端从不填充的缓存。
- 上游的 golangci-lint `tool` 指令，它会给每个下游消费者的模块图增加约 200 个 linter 依赖。

## 刻意推迟的部分 {#deferred}

minio/minio#20449 的一般性问题——`bucket/*` 仍会触及 `ListBucket`、`GetBucketLocation`、各类配置读取、`CreateBucket` 以及上述三个租户可能合理使用的写入——在这里 **没有** 被关闭。彻底关掉它意味着撤销真实部署所依赖的授权，因此它属于一次带迁移路径的发布。

那次发布欠运维的东西，比"一份更长的动作清单"要多，因为没有人能穷举所有部署的存量策略——这给"靠猜来划定保护集合"的做法设了一个硬上限。有三件事能抬高它：

- **启动时的策略审计**：遍历存量策略，逐条点名哪一条的含义会改变，授予与拒绝两个方向都点。它是只读的，甚至可以 **先于** 强制生效单独发布，从而把"升级后的意外"变成"升级前的清单"。
- **会自我解释的拒绝**：当一个请求因为"只有对象级授权匹配上"而被拒时，就把这句话说出来，并点名那个兼容开关。一次 30 秒能自诊断的破坏，成本比静默破坏低一个数量级。
- **带作用域的开关**：`MINIO_API_LEGACY_BUCKET_RESOURCE_MATCH` 今天是全有全无，只想要回一个动作的运维，被迫连自我提权那条路一起重新打开。

## 相关提交 {#related-commits}

- [d8b1fa7](https://github.com/pgsty/silo-pkg/commit/d8b1fa7)：fix(policy): settle the bucket-write hardening's scope and monotonicity
- [1f97549](https://github.com/pgsty/silo-pkg/commit/1f97549)：fix(policy): extend the bucket-write hardening to every bucket-only write
- [3c24ad1](https://github.com/pgsty/silo-pkg/commit/3c24ad1)：fix(policy): withhold object-only grants from sensitive bucket writes
- [da6a22a](https://github.com/pgsty/silo-pkg/commit/da6a22a10143f2e23764c59f39306e9ac3282da5)：docs: say what this fork is and how to depend on it
- [4055b2f](https://github.com/pgsty/silo-pkg/commit/4055b2f7d5a33948004ac13a933aa978b57399e6)：fix(xtime): marshal Duration as a duration string
- [13c26cd](https://github.com/pgsty/silo-pkg/commit/13c26cda3db1e36bb3b7904217271a32b73039b7)：fix(rng): initialize the reader subkeys from the seeded entropy
- [88b37ac](https://github.com/pgsty/silo-pkg/commit/88b37ace8a14a511e09b9b30567cde8e5bfa2398)：fix(certs): stop file watchers on every exit path
- [74dd36e](https://github.com/pgsty/silo-pkg/commit/74dd36e78a829782b6f04ad09fd908386e13c693)：fix(ldap): keep StartTLS when ServerInsecure is also set
- [424c3d0](https://github.com/pgsty/silo-pkg/commit/424c3d06057b579631a4a8a81ffae9985875f477)：fix(ldap): close the connection when StartTLS fails
- [045d10f](https://github.com/pgsty/silo-pkg/commit/045d10fd974760153024cd7d519919440c28c5cb)：fix(ldap): guard a nil TLS config and arm the StartTLS deadline
- [5c4bf50](https://github.com/pgsty/silo-pkg/commit/5c4bf503d5d5701327527f030a3c755266d741f1)：fix(policy): prefer the exact key name over the canonical header form
- [802539f](https://github.com/pgsty/silo-pkg/commit/802539f36d723802c80dea3c18c88da33c5d87d4)：chore(deps): refresh the dependency set and declare the real minimum Go
- [e4ec64a](https://github.com/pgsty/silo-pkg/commit/e4ec64a9453d9ad469f6fd4ece93b2462bd118ef)：ci: build on the Go version go.mod requires, and prove the declared minimum
- [747d8b8](https://github.com/pgsty/silo-pkg/commit/747d8b865ca937f227b0f70aeec9f8b49d05f55d)：build: pin the golangci-lint installer and skip a matching install
