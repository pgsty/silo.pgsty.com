---
title: "Conditional DELETE：为什么删除条件只能针对当前对象判断一次"
linkTitle: "Conditional DELETE"
date: 2026-08-26
lastmod: 2026-09-02
author: "冯若航"
summary: >
  SILO PR #12 尝试为 DeleteObject 增加 If-Match，却把条件交给每个存储池分别判断，可能造成 412 后部分删除或成功后旧副本重新可见。本文记录问题真实性、AWS 契约、评审反例、最小修复设计、测试要求，以及批量条件删除和策略条件键的后续边界。
tags: [设计, S3, 兼容性, DELETE]
weight: 10
draft: false
url: "/zh/blog/design/conditional-delete/"
---

本文是 [SILO PR #12](https://github.com/pgsty/silo/pull/12) 的问题分析、设计讨论与修复决策归档。

> **截至 2026-08-26 的状态：** PR #12 仍然 open，原 head 为 `5b71a75e`，落后最新 `main` 118 个提交。原提交没有 DCO sign-off，GitHub 上没有 check run。本文记录的改进方案已在独立本地 worktree 中实现、测试并完成两轮 review，并已提交到本地分支 `codex/pr12-conditional-delete`；尚未推送、合并或发布。<br>
> **本轮范围：** 正确实现单对象 `DeleteObject` 的 `If-Match`；同时在收到尚未支持的 `DeleteObjects` 逐对象 ETag 时 fail closed，避免静默无条件删除。完整批量条件执行与 bucket policy 仍是独立交付。<br>
> **发布边界：** 本地实现、测试、review、commit、push、远端 CI、merge、tag、镜像与生产部署是相互独立的门槛。

## 太长不看（TL;DR） {#tldr}

这个问题是真的。SILO 当前会忽略 `DELETE` 请求的 `If-Match`，让客户端以为自己在执行 compare-and-delete，服务器却实际执行无条件删除。PR #12 试图补上条件检查，目标正确，也意识到必须在持锁、读取新鲜对象状态后判断。

但原实现把同一个 HTTP callback 传给每个 erasure pool。不同 pool 可能保留不同时间的对象副本，于是每个 pool 按自己的 ETag 各判各删。评审用双池测试复现了两个反例：

- 请求最终返回 412，但匹配条件的旧副本已经被删除；
- 请求返回成功，未匹配条件的旧副本保留，随后重新成为可见对象。

选定修复不增加新的条件框架。它复用 SILO 已有 GET 多池路径的模式：在外层 namespace lock 下选出当前对象，只判断一次条件，然后清除下层 callback。条件失败时任何 pool 都不能发生 mutation；条件通过后所有 pool 执行原有清理，不再重新解释客户端条件。

## 问题为什么成立 {#problem}

### 被忽略的条件不是无害扩展 {#silent-downgrade}

[AWS 条件删除文档](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-deletes.html) 已经为通用 bucket 明确支持 `DeleteObject` 和 `DeleteObjects`：

| 请求 | 含义 | 结果与权限 |
| --- | --- | --- |
| `If-Match: <ETag>` | 只有当前对象仍是调用者看到的版本时才删除 | 匹配返回 204，不匹配返回 412；需要 `s3:GetObject` 与 `s3:DeleteObject` |
| `If-Match: *` | 只有当前对象存在时才删除 | 对象存在返回 204；只需要 `s3:DeleteObject` |
| key 不存在 | 无法满足条件 | 返回 Not Found |
| 最新版本是 delete marker | 当前对象不存在 | `If-Match: *` 返回 412 |

因此，服务端收到条件后无条件执行，不是“尚未支持的 header 被忽略”这么简单。它破坏了调用者用于避免并发误删的前提。

严重性取决于调用面：不是每个客户端都会使用条件删除，所以总体出现频率未知；但一旦客户端依赖它，单次失败就可能删除另一写者刚刚提交的新对象。这属于数据正确性问题。

### delete marker 的失败不是 ETag 比较问题 {#delete-marker}

PR #12 复用了通用 `isETagEqual`：右值为 `*` 时直接返回 true，所以 `isETagEqual("", "*")` 也为真。

更根本的问题在更外层。`erasureServerPools.DeleteObject` 看到当前对象已经是 delete marker 时，会在原 PR 新增的内层 callback 执行前直接返回成功。评审测试观察到 callback 调用次数为零，结果却是成功。

这里要区分两种影响：

- delete-marker fast path 在复现中没有删除历史版本，也没有再创建 marker；它是**绕过条件并假报成功**；
- 多池反例确实能在失败请求中删除一个副本，或在成功请求后留下可重新出现的副本；这才是实际存储状态被破坏。

所以不能只把 `isETagEqual("", "*")` 改成 false。那既触及 GET、PUT、COPY 共用的比较器，也无法让 callback 越过外层 fast path。

## 原 PR 哪些思路是对的 {#good-direction}

PR 的高层算法没有错：

1. Handler 发现 `If-Match`；
2. 存储层在持锁后读取新鲜 `ObjectInfo`；
3. 条件不成立则在 mutation 前返回；
4. Handler 把结果编码成 S3 响应。

它避免了先单独 HEAD、再执行 DELETE 的明显 TOCTOU 窗口，也为错误 ETag、匹配 ETag和缺失对象增加了测试。普通单池、当前对象、具体错误 ETag 的路径确实能够返回 412 并保留对象。

问题不在“应该在锁内判断”，而在“哪一层的锁内、针对哪个对象判断”。

## 原子性边界在哪里 {#atomicity-boundary}

SILO 的删除路径分为两层：

```text
DeleteObjectHandler
    -> erasureServerPools.DeleteObject
         持有 namespace write lock
         从所有 pool 选出最新的当前对象 pinfo
         处理 delete marker fast path
         决定单池删除或多池清理
             -> erasureSets / erasureObjects.DeleteObject
```

只有 `erasureServerPools.DeleteObject` 同时知道：

- 哪个副本代表当前对象；
- 哪些 pool 还存在旧副本或不一致 metadata；
- 是否会走 delete-marker fast path；
- 是否要并发删除多个 pool。

所以客户端条件必须在这一层判断。单个 pool 只知道自己的副本，它没有资格重新解释“当前对象的 ETag 是否仍匹配”。

## 双池反例 {#two-pool-counterexamples}

测试构造两个 pool：pool 0 有较旧对象，pool 1 有较新对象，两者 ETag 不同。SILO 的读取选择 pool 1 作为当前对象，但非版本化删除会清理两个 pool。

### 条件匹配旧副本 {#matches-old}

原 PR 会在 pool 0 判定通过并删除旧副本，在 pool 1 判定失败。最终返回值取最新 pool 的 412，但失败请求已经修改了存储状态。

### 条件匹配当前副本 {#matches-current}

原 PR 会在 pool 1 判定通过并删除当前副本，在 pool 0 判定失败并保留旧副本。请求返回成功后，旧副本变成系统可见的最新对象，相当于对象“复活”。

callback 还捕获同一个 `http.ResponseWriter`；在多个 pool 并发执行时，可能并发写同一响应。即使暂时没有触发可见 race，也不应让存储副本并发决定 HTTP 结果。

### 降级旧池的既有局限 {#degraded-pool-limitation}

这里还有一个不由本补丁引入的相关旧限制：如果被选中的当前 pool 可读可写，但保存旧副本的非当前 pool 处于降级状态，现有多池删除路径可能返回当前 pool 的成功，而没有向上暴露旧 pool 的错误。残留副本在恢复后可能重新可见。

新条件检查没有制造这个行为：它先正确判断可读的当前对象，再进入无条件删除也会使用的非版本化多池清理。修复降级旧池的错误聚合与恢复语义会影响所有非版本化多池删除，不只 conditional delete，因此应单独跟踪。

## 选定的最小修复 {#selected-fix}

### 1. 外层只检查一次 {#evaluate-once}

在 `erasureServerPools.DeleteObject` 已经取得 namespace write lock 后：

1. 保存 `opts.CheckPrecondFn`；
2. 立即从传给下层的 `opts` 中清除 callback；
3. 读取所有 pool 并选出当前 `pinfo`；
4. 如果当前对象不可可靠读取，返回 quorum 错误，callback 不运行；
5. 针对 `pinfo.ObjInfo` 调用一次 callback；
6. 条件通过后继续现有删除流程，所有 pool 不再重复判断。

这不是新发明。`GetObjectNInfo` 的多池实现已经使用同样的“外层保存 callback、清除下层 callback、选出 latest 后检查一次”模式。DELETE 复用该模式可以把修改限制在真实原子性边界。

### 2. `*` 显式判断当前 representation {#wildcard}

DELETE 专用条件函数把 `*` 与具体 ETag 分开：

```text
具体 ETag -> 比较当前对象的客户端可见 ETag
*         -> Name 非空并且不是 delete marker
```

缺失 key 在选择当前对象时已经返回 Not Found；delete marker 则进入 callback 并返回 412。通用 `isETagEqual` 保持不变，避免波及其他方法。

### 3. 具体 ETag 增加读权限 {#permission}

Handler 仍先检查 `s3:DeleteObject`。当规范化后的条件不是裸 `*` 时，再检查 `s3:GetObject`。因此：

- Delete-only policy + `*`：允许；
- Delete-only policy + 具体 ETag：403，且对象不变；
- Get + Delete + 正确 ETag：允许。

这是授权前置检查，不会在拒绝后触碰存储。

### 4. 不为 DELETE 强制 SSE-C 解密请求 {#encrypted-etag}

原 PR 直接复用 GET/PUT 的 `DecryptObjectInfo`，但 SSE-C 对象在没有 SSE-C 读取 header 时会被拒绝。DELETE 条件只需要客户端可见 ETag，不需要解密内容或尺寸。

选定实现只在具体 ETag 路径调用既有 `getDecryptedETag`；`*` 不读取 ETag。这样复用 SILO 已有的 ETag 投影逻辑，不为 DELETE 引入内容解密要求。

### 5. 条件针对当前版本 {#current-version}

AWS 规定 conditional delete 评估当前版本。SILO 的外层 pool 选择本来就读取当前对象，再把显式 `versionId` 留给真正的版本删除。因此上移判断后，即使请求携带历史 `versionId`，条件 callback 看到的也是当前 ETag。

测试固定了这一点：请求删除历史版本、条件却匹配历史 ETag而不匹配当前 ETag时，返回 412，历史版本和当前版本都保持不变。

### 6. 在暂不支持的边缘 fail closed {#fail-closed-edges}

两个很小的 guard 防止单对象条件被绕过：

- 空或仅含空白的 `If-Match` 会被拒绝，不会降级成无条件删除；
- `If-Match` 不能与内部递归扩展 `x-minio-force-delete` 组合，因为 prefix 删除语义无法表达单对象 ETag 条件；HTTP Handler 会拒绝，存储层也会拒绝任何内部 prefix-delete + callback 组合。

批量 XML decoder 现在也会识别逐对象 `<ETag>`。在原子化逐项执行完成前，只要 batch 中出现非空 ETag，服务器就在任何删除发生前以 `NotImplemented` 拒绝整个请求。这不是批量条件删除支持，只是防止静默丢弃条件的数据安全护栏。

## 被否决的方案 {#rejected}

### 只修 `isETagEqual` {#reject-comparator}

不能解决外层 delete-marker fast path，也会改变多个 API 共用的比较语义。

### 保留每池 callback，再聚合结果 {#reject-per-pool}

聚合错误无法回滚已经发生的副本删除。客户端条件是对逻辑当前对象的判断，不是对每个物理副本的独立条件。

### 新增复杂的条件对象或事务协调器 {#reject-framework}

当前只支持一个 `If-Match` 条件，现有 `CheckPrecondFn` 足以表达；GET 已经展示了正确的一次性消费模式。新增通用 DSL、状态机或跨池事务抽象没有必要。

### 在同一改动中完成所有 conditional delete {#reject-scope-expansion}

`DeleteObjects` 与 policy condition 是相关但不同的接口和仓库边界。把它们塞进本 PR 会扩大 XML、逐项响应、IAM、quiet mode 和依赖发布的审查面，降低核心删除修复的可信度。

## 测试与验收契约 {#tests}

最小充分测试覆盖：

| 层级 | 验证内容 |
| --- | --- |
| 条件函数 | 正确/错误/带引号 ETag、`*`、delete marker、非 DELETE 方法，以及无需内容解密 header 的 SSE-C 客户端可见 ETag 投影 |
| Handler | 错误 ETag 返回 412 且对象保留；正确 ETag 返回 204；缺失 key 返回 Not Found；空条件与 conditional force-delete 无 mutation 拒绝 |
| 权限 | Delete-only 的具体 ETag 返回 403且对象保留；同一策略下 `*` 成功 |
| 单池存储 | 正确/错误条件、缺失对象、delete marker callback 恰好一次，并拒绝 conditional prefix delete |
| Quorum | 当前对象不可可靠读取时返回 quorum 错误，callback 零次，恢复磁盘后对象仍在 |
| Versioning | 显式历史 `versionId` 的条件仍针对当前版本 |
| 双池 | 412 后每个 pool 都不变；204 后所有 pool 副本都消失；callback 都只运行一次 |
| Batch 安全护栏 | 尚未支持的逐对象 `<ETag>` 返回 `NotImplemented`，所有对象保持不变 |

原 PR 的 quorum 测试只把 16 块盘中的 8 块下线并断言“存在任意错误”。此时删除 write quorum 本来也不足，所以测试放在未实现 conditional delete 的主线上也会通过。新测试要求具体 quorum 错误、callback 未执行，并在恢复磁盘后确认对象仍在，避免同类假阳性。

## 独立对抗评审 {#adversarial-review}

两轮只读本地 Claude Code review 都使用 Fable 模型与 `xhigh` effort，检查精确的服务端差异和两篇设计记录。两轮结论都是 **GO WITH NON-BLOCKING NOTES**；第一轮意见落实后，不再存在 P0、P1 或 P2 finding。

第一轮发现 conditional force-delete 绕过、纯空白条件降级、batch ETag 被静默丢弃、版本化成功路径缺测试，以及降级旧 pool 的既有局限；上文的 guard、测试与限制说明都来自这些 finding。第二轮确认了外层原子性边界、错误处理、权限拆分、batch 字段影响面、response writer、双语一致性和最小复杂度。它剩余的一个可行动 P3 是内部调用者理论上仍可组合 prefix deletion 与 callback；存储层现在也会拒绝这个组合。

评审中有一句认为 SSE-C 未提供 customer-key header 时条件必然失败。直接检查既有实现表明并非如此：`getDecryptedETag` 无需解密对象内容，就会投影后端保存的客户端可见 ETag 后缀；新增定向回归测试已固定这一行为。其余非阻塞备注是多值 header 的规范化和刻意保留的“鉴权前返回 501”错误顺序。若要宣称超出公开文档的逐字节一致性，发布前仍值得用真实 AWS 对“当前 delete marker + 具体 ETag”以及“`versionId` + `If-Match`”做一次差分验证。

## 本轮刻意不做什么 {#follow-up}

### `DeleteObjects` 的逐对象条件 {#delete-objects}

[AWS DeleteObjects API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteObjects.html) 允许每个 `<Object>` 携带 `<ETag>`，并在同一个 200 响应内逐项返回 `<Deleted>` 或 `<Error>`。

安全补丁只为 `ObjectToDelete` 增加 ETag 字段，使 Handler 能识别条件并在 mutation 前拒绝整个请求。这样关闭了原先静默无条件删除的风险，但**没有**实现 AWS 要求的逐对象判断和 mixed `<Deleted>` / `<Error>` 响应。

完整兼容仍是独立且高优先级的工作：每项都要在正确锁下针对逻辑当前对象判断；逐项落实具体 ETag 的权限规则；保持 quiet mode；条件失败不能阻塞其他无关项，并在响应中分别报告。

### `s3:if-match` policy condition key {#policy-key}

[AWS 允许通过 policy 强制 conditional delete](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-delete-enforce.html)。SILO 使用的 `silo-pkg` 尚未定义 `s3:if-match`，完整实现需要：

1. 在 `silo-pkg` 增加 condition key 与 action map；
2. 发布新的 `silo-pkg` 版本；
3. 在 server 提供单删 header 和批删逐对象 condition values；
4. 升级依赖并做策略兼容测试。

这应是独立跨仓库交付，不是单对象原子性修复的前置依赖。

## 复杂度、收益与代价 {#tradeoff}

生产修改仍然很小：一个 DELETE 条件函数、一次附加授权、外层十余行的一次性 callback 消费，以及针对畸形/递归请求和暂未支持 batch 条件的窄幅 fail-closed guard。复杂度主要在测试，因为删除路径横跨多池、版本、marker、quorum 和权限。

| 范围 | 复杂度 | 主要成本 |
| --- | --- | --- |
| 本轮单对象修复与 batch 安全护栏 | 中等 | 删除热路径与多池/版本/权限回归 |
| Batch conditional delete | 中等偏高 | XML、逐对象判断、mixed response、quiet mode |
| Policy condition key | 中等、跨仓库 | `silo-pkg` 发布、server condition values、策略测试 |

收益大于代价。它消除危险的静默无条件删除，并把条件判断放回系统已经存在的全局一致性边界。相比引入新框架，复用当前 outer-lock/latest-object 模式是最小、充分且必要的实现。

## 合并与发布门槛 {#merge-gates}

单对象修复在满足以下条件后可以合并：

1. 定向条件删除、权限、versioning、quorum 与双池测试通过；
2. `go test ./cmd`、`go vet ./cmd`、格式与 diff 检查通过；
3. 独立对抗 review 没有未解决 blocker；
4. 作者在最新主线上整理提交并提供有效 DCO sign-off；
5. DCO、Go CI、VulnCheck 等远端 workflow 全绿；
6. PR 描述明确区分完整的 `DeleteObject` 支持与 batch fail-closed 护栏，并链接完整 batch/policy 后续项。

即使代码合并，仍不能把功能写成已发布。只有对应 release、软件包、`docker.io/pgsty/silo` 镜像、部署和真实 S3 客户端验证分别完成后，生产用户才能依赖它。

## 结论 {#conclusion}

Conditional DELETE 值得实现，PR #12 的目标和“锁内读取新鲜状态”方向也值得保留。真正需要改变的是判断边界：客户端条件属于逻辑当前对象，不能由每个物理副本分别解释。

选定方案只把 callback 上移到已经负责选择当前对象的 `erasureServerPools`，复用现有模式，显式处理 wildcard/delete marker，并补上具体 ETag 的读权限。它不改存储格式、不增加依赖、不引入新条件框架。batch 改动严格限于 mutation 前拒绝尚未支持的条件；完整批量执行与 policy 支持仍保持独立。

这就是本问题所需的最小、充分且必要的复杂度。
