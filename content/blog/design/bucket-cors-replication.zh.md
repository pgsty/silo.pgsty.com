---
title: "桶级 CORS：让删除与恢复正确收敛"
linkTitle: "桶级 CORS 复制"
date: 2026-08-28
lastmod: 2026-08-28
author: "冯若航"
summary: >
  SILO 通过 PR #71 接纳了桶级 CORS，随后发现遗漏或乱序的站点复制事件可能恢复已经删除的浏览器来源规则。本文先用浅显语言说明问题、收益与代价，再完整记录合并决策、两轮对抗评审、来源时间戳与删除墓碑修复、S3 响应收尾、被否决方案、历史后续项，以及 Issue #75 定义的发布门槛。
tags: [设计, S3, CORS, 复制, 兼容性]
weight: 32
draft: false
url: "/zh/blog/design/bucket-cors-replication/"
---

本文完整记录 [SILO PR #71](https://github.com/pgsty/silo/pull/71) 与发布善后任务 [SILO #75](https://github.com/pgsty/silo/issues/75) 的问题、评审、合并决策、对抗辩论和最终实现契约。

> **状态：** PR #71 已合并为 [`e4e3007da`](https://github.com/pgsty/silo/commit/e4e3007da6d7d1198a6a050e34f84566d40a9654)。B2 收敛修复是 [PR #80](https://github.com/pgsty/silo/pull/80) 中的 [`724f8703d`](https://github.com/pgsty/silo/commit/724f8703d83f4c51859c7650b7f1da2c2a55548c)，其 DCO、CI、race、cross-compile 与漏洞检查共八项全部通过。B2+B3 组合方案是本地 signed commit `0eebc928f`；Opus 5 Max 组合终审 finding 已解决，parser、middleware、replication、namespace 与 legacy-repair 定向测试通过。完整组合验收刻意等方案与文档冻结后再安排。Issue #75 仍是发布阻断：尚未 merge、tag、打包、发布镜像、部署或完成生产验证。<br>
> **归属：** [`pgsty/silo`](https://github.com/pgsty/silo) 负责服务端修改；这份公共设计记录归 [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com) 所有；Console UI 仍是独立交付。<br>
> **决策：** 接受有价值的功能并保留贡献者成果，但在站点复制删除、恢复、通配符响应和窄幅协议善后正确收敛前，不允许发布。

## 用浅显语言说明问题与方案 {#plain-language}

PR #71 之前，SILO 只能为整个集群设置一份 CORS。浏览器应用无法表达：“允许这个网站使用桶 A，但不允许它使用桶 B。”标准 S3 的桶级 CORS 读取、写入和删除接口虽然有路由，却只是返回 `NotImplemented` 的占位实现。

PR #71 补上了这项能力。每个桶现在都可以保存自己的允许网站、HTTP 方法、请求头、开放响应头和预检缓存时间。标准 S3 客户端可以管理配置；没有专属配置的桶继续使用原来的全局行为。

核心功能已经可以工作。剩余问题出现在同一个桶跨站点复制时。

假设管理员先允许 `https://old.example.com`，随后撤销这个权限。第一个站点正确删除了规则。如果另一个站点临时漏收 DELETE，恢复过程必须知道“10:05 的删除”比“10:00 的配置”更新。当前代码有时会忘掉删除时间，或把来源时间替换成对端收到消息的时间。恢复过程于是可能误把仍然存活的旧规则当成最新状态，再把它写回来。

修复不需要新的复制系统。删除后的配置可以用 SILO 已有的数据表示：

```text
配置内容 = 不存在
更新时间 = DELETE 发生的时间
```

这对状态就是删除**墓碑（tombstone）**。修复会为 PUT 和 DELETE 保留来源时间；即使 XML 已经不存在，也传播这个时间；并让 heal 与普通 peer 交付复用同一条 CORS 应用路径。旧事件因此不能再复活更新的删除。

直接代价有清晰边界：一个 CORS 专用分布式 namespace lock 与单调状态转换、穿透真实 ObjectLayer 的测试、严格 wire 校验、响应兼容收尾和运维文档。它不增加存储字段、依赖、功能开关、分布式时钟或通用复制框架。长期代价是 SILO 需要维护这些测试和桶级 CORS 兼容契约；站点复制仍像原来一样依赖时钟同步。

CORS 不是 IAM 鉴权。过期 CORS 规则不会让无权访问 S3 的主体获得权限，但它可能让管理员本想撤销的浏览器来源继续读取原本已获授权的跨域响应。因此复制收敛是发布阻断，而不是外观问题。

## PR #71 增加了什么 {#feature}

PR #71 把继承而来的 Bucket CORS 占位实现替换成了一项完整功能：

- 标准 `PutBucketCors`、`GetBucketCors`、`DeleteBucketCors` API；
- PUT 的 Content-MD5 或受支持 checksum 校验；
- Origin、Method、AllowedHeader、ExposeHeader、规则 ID 和 MaxAge 的 XML 解析与校验；
- 原始 XML 与 CORS 更新时间写入 `BucketMetadata`；
- 桶级 OPTIONS 预检与实际响应 CORS 头；
- 仅在桶没有专属配置时继续使用现有全局 CORS；
- 站点复制的正常发送、接收、初始同步、状态和 heal 接线；
- 单元、Handler、Middleware、Metadata 与传输测试。

本地评审把功能合入当时最新的 `main`，执行了构建、定向普通与 race 测试、完整 `cmd`、固定版本 lint、生成文件检查、兼容性检查，以及真实 `minio-go` 冒烟测试。单站路径上的 PUT、GET、DELETE、允许与拒绝预检、`Vary` 和实际响应头全部正常。

这些证据足以接纳功能，但不能证明所有失败恢复路径。

## 已复现的收敛错误 {#reproductions}

评审使用真实 ObjectLayer 的临时测试稳定复现了下面三个问题。后续发布审查还证明：只比较 payload 的 status 会隐藏不同来源时间屏障；同时间戳冲突则依赖事件到达与 map 迭代顺序。

### 更新的 DELETE 可能被忽略 {#ignored-delete}

Peer handler 使用普通 metadata `Update` 与 `Delete`。这些方法会在接收站点无条件写入 `UTCNow()`。如果旧 PUT 延迟到达，它生成的本地接收时间可能看起来比后续来源 DELETE 更晚，结果 DELETE 被当成旧事件丢弃。

### 旧 PUT 可能复活删除 {#resurrected-put}

活跃配置为 nil 后，`GetCorsConfig` 会返回 not-found 与零时间戳。删除时间仍保存在原始 bucket metadata 中，但 handler 通过这个 getter 看不到。旧 PUT 因此通过 staleness 判断并恢复规则。

### Heal 可能选择仍存活的旧规则 {#heal-resurrection}

当前 `SiteReplicationMetaInfo` 只有在 CORS XML 非空时才输出 `CorsConfigUpdatedAt`。DELETE 后，站点报告 nil 配置与零时间；仍保留旧 XML 的 peer 则报告非零旧时间。Heal 于是把旧规则选成“最新”，重新写回。

这三个现象其实是同一个缺陷在三个边界上的表现：peer apply、metadata status 与 recovery。

## 预期状态模型 {#state-model}

桶级 CORS 只需要 `BucketMetadata` 中已经存在的状态：

| 逻辑状态 | XML | 时间戳 | 含义 |
| --- | --- | --- | --- |
| 从未配置 | nil | 零时间 | baseline；既不发送，也不作为 winner |
| 已配置 | 非 nil | 来源 PUT 时间 | 生效中的桶级规则 |
| 已删除 | nil | 来源 DELETE 时间 | tombstone；比任何更早的活跃规则更新 |

选定 register 使用确定性总序：

```text
1. 来源 UpdatedAt
2. baseline < live < tombstone
3. 同时间 live/live：按解码后的 payload 字节字典序
```

Peer apply 是单调 join：只有严格更大的状态才会落盘，因此 retry 与重复交付天然幂等。同时间 PUT/DELETE 由 tombstone 胜出；两个 live 值则在每个站点选择相同的字节 winner。`CreatedAt` 不再表示 baseline，只作为 bucket lineage 下界，拒绝旧 bucket incarnation 的事件并输出按桶去重的诊断。

## 决策是如何形成的 {#decision-history}

### 初始评审 {#initial-review}

第一次评审确认需求真实、单站架构合理，但发现站点复制虽然发出了 CORS 事件，却没有完成所有接收、状态和恢复路径。贡献者随后补齐接线、checksum 校验、通配符/ID 限制、缓存变化维度与定向测试。

第二次运行时评审确认单站和正常直接复制路径，同时复现了上述 tombstone 与来源时间问题。功能已经足够接近，可以接纳，但还不够安全，不能当作完成状态发布。

### 合并不等于发布 {#merge-versus-release}

维护者决定合并 PR #71，并接手剩余加固。这个决策明确分开了两个经常被混淆的问题：

1. 贡献是否有价值、结构是否足够合理，可以接纳？**可以。**
2. 结果是否已经可以打 tag、打包、发布镜像和部署？**必须等 #75 关闭。**

合并触发的完整 `main` CI 已经通过；正式发布和 Docker 发布仍是手工、独立门槛。

### 自我对抗性方案评审 {#self-review}

最初的善后方案刻意写得很全面，随后按四种失败模式自审：是否过度设计、是否为修一个问题引入更多问题、是否没有复用现有基础设施，以及维护成本是否不成比例。

这次自审删除或延后了：

- 新的通用 metadata apply 抽象；
- 自定义 wildcard matcher；
- Policy/Tag/SSE/Quota 的广泛重构；
- 多进程站点复制测试实验室；
- 没有差分证据的方法大小写、Unicode ID、trailing XML 严格化；
- 可能改变现有 `Vary` 行为的无 Origin 热路径优化；
- vector clock、新 tombstone 字段和全局时间戳重构。

### 独立 Claude Opus 5 评审 {#claude-review}

四轮只读本地 Claude Code 评审使用 canonical `claude-opus-5` 与 maximum effort。评审把方案从 timestamp-only 补丁推进成最终 zero-baseline、确定性 C-prime register；要求分布式 CORS lock 与单调本地 barrier；让 status/heal 比较完整状态；并关闭 strict base64、语义校验、缓存、`Vary`、wildcard credentials 与 initial-sync tombstone 缺口。

B2+B3 组合终审又同时检查 strict parser、精确 Method 与 Unicode ID 契约、MaxAge presence、Origin-null forwarding marker、checksum 分类以及复制/重启行为。它发现一处测试 helper 冲突，以及宽松开发版本接受的文档可能导致整份 bucket metadata 不可用的升级风险。Helper 已修；legacy-invalid CORS 现在保持其他 bucket metadata 可读，对浏览器 fail closed，拒绝新 invalid save，并允许通过有效 CORS PUT/DELETE 修复。

## 设计目标与非目标 {#scope}

### 设计目标 {#goals}

- 让 CORS PUT/DELETE 在重复、延迟、乱序、漏发后正确收敛；
- Peer apply 与 heal 都保留精确来源时间；
- 更新的 nil tombstone 能打败更旧的活跃配置；
- metadata 故障不能把已配置桶静默放宽到全局 CORS；
- 字面通配符、credentials、expose headers 和缓存变化符合 S3 行为；
- 修正新加入的 CORS 状态计数，以及现有 matcher 已证明的窄幅校验缺口；
- 保持修复可独立评审、可单独回滚。

### 非目标 {#non-goals}

- 重构所有 bucket metadata 复制 handler；
- 全局解决分布式时钟偏差或同时间戳多写者冲突；
- 新增 metadata schema、事件日志、队列、通用 metadata lock 或功能开关；
- 建设长期多站点进程实验室；
- 在没有证据时收紧无关 XML 或校验路径；
- 增加 Console UI；
- 把历史 Object Lock、Tag、SSE、Policy、Quota 或 Versioning 修复混入本分支。

## 最终修复设计 {#design}

### Commit 1：保留 tombstone 与来源顺序 {#commit-1}

CORS 复制 handler 继续作为显式 peer CORS 事件的唯一应用边界。

它在 CORS 专用分布式 namespace lock 内执行：

1. 要求非空 bucket 与非零来源时间；
2. 要求 bucket metadata 已经存在，而不是凭空创建；
3. 读取原始 `CorsConfigUpdatedAt`，包括活跃配置为 nil 时保留的时间；
4. 拒绝早于 bucket lineage 的事件，并忽略总序中不严格大于本地状态的事件；
5. 严格解码并校验非 nil CORS payload，或把 nil 解释为 DELETE；
6. 从来源事件设置 `CorsConfigXML` 与 `CorsConfigUpdatedAt`，保留精确来源屏障；
7. 通过 `BucketMetadataSys.save` 持久化，保留现有磁盘、缓存、通知和 peer-node 刷新路径。

Legacy/default multi-field 路径可能携带非 nil CORS snapshot，因此也使用同一把锁、严格校验与 join；typed delete 继续走 CORS 专用 handler。`SiteReplicationMetaInfo` 无条件输出来源时间，只在 XML 存在时编码内容。Status 比较 kind、解码 payload 与时间；heal 选择确定性最大状态并通过同一 transition 传播，包括只差时间戳的场景。

Zero baseline 明确不默认成 bucket 创建时间。Initial sync 发送 live 与 tombstone，但不发送 baseline。本地 PUT/DELETE 生成严格晚于 `max(UTCNow, CreatedAt, current barrier)` 的时间。

### Commit 2：Fail closed，并对齐 S3 响应 {#commit-2}

当前 middleware 会在所有 `GetCorsConfig` 错误上回退到全局 CORS。修复区分两种情况：

- 确实没有配置：继续使用全局策略，保持现有行为；
- 请求带 `Origin` 且出现其他 metadata 错误：log once，然后调用底层 S3 handler，不附加全局 CORS 头。

这样对浏览器 fail closed，又不会把 metadata 问题变成新的全局 500 契约。失败预检会进入 router 的普通非 CORS 错误响应。无 Origin 请求保持现有 middleware 路径，不做投机热路径优化。

成功预检还会返回配置的 `Access-Control-Expose-Headers`；[S3 OPTIONS 契约](https://docs.aws.amazon.com/AmazonS3/latest/developerguide/RESTOPTIONSobject.html)明确列出了这个响应头。

Origin 匹配将返回真正命中的 pattern。响应行为是：

| 命中的 Origin 元素 | `Access-Control-Allow-Origin` | `Access-Control-Allow-Credentials` |
| --- | --- | --- |
| `*` | `*` | 不发送 |
| 精确 Origin | 请求 Origin | `true` |
| `https://*` 等模式 | 请求 Origin | `true` |

当同一规则同时包含具体 Origin 和 `*` 时，响应语义跟随第一个实际命中的 Origin 元素，而不是事后发现规则里某处存在 wildcard 就统一处理。

三个缓存变化维度会在预检匹配前设置，因此 200 和 403 都按 Origin、请求方法和请求头区分缓存。

### Commit 3：窄幅校验与状态善后 {#commit-3}

站点摘要使用当前站点的 `s.CorsConfig != nil` 增加 `TotalCorsConfigCount`，而不是使用可能已经累计早先站点的总数。

校验拒绝：

- 空 AllowedOrigin；
- `?`，因为复用的通用 matcher 会把它当成 wildcard，而 S3 只定义单个 `*` 通配符。

实现保留现有 matcher 与最多一个 `*` 的限制；不修改方法大小写、ID 字符计数或 trailing XML 行为。

Handler 测试补上缺失与不匹配的 Content-MD5。这个测试又暴露了一个真实问题：handler 在 checksum reader 外套了长度恰好等于 `ContentLength` 的 `LimitReader`，后者会在 checksum wrapper 报摘要不匹配前先返回 EOF。完成既有正数与 64 KiB ContentLength guard 后，handler 现在直接把包装后的请求体读到 EOF。这样既继续复用共享 `validateLengthAndChecksum`，又能真正返回 `BadDigest`，不增加第二条 checksum 路径。

### Commit 4：运维说明 {#commit-4}

仓库内说明记录：

- 桶级 CORS 覆盖而不是合并全局 CORS；
- DELETE 恢复全局 fallback；
- 老版本不会执行新配置；
- 老版本重写 bucket metadata 时可能丢弃未知 CORS 字段；
- 老 peer 对未知 CORS 事件会无害 no-op，升级后通过 heal 收敛；
- 站点复制继续依赖时钟同步。

公共运维文档仍是独立文档仓库交付；本文以及后续面向任务的参考更新共同承担这个边界。

## 测试设计 {#tests}

测试验证真实状态转换，但不建立长期多进程实验室。

| 测试边界 | 必须覆盖的场景 |
| --- | --- |
| Peer apply + ObjectLayer | 延迟 PUT 后较新 DELETE；tombstone 后旧 PUT；重复交付；精确来源时间；metadata 不存在时返回错误且不创建记录 |
| Transport 到 apply | 保留现有 nil/非 nil JSON 往返；至少把一个 JSON 解码事件送入真实 peer handler |
| SiteReplicationMetaInfo | nil 配置仍携带 DELETE 时间；功能前的零时间默认成 Created |
| Heal | 更新的 nil tombstone 打败旧活跃 XML；本地变为 nil，时间精确等于 tombstone |
| Middleware 错误 | 无配置使用全局 fallback；其他 metadata 错误的 actual/preflight 都不附加全局 CORS |
| Origin 响应 | 精确、字面量 `*`、模式和混合规则；仅在允许时发送 credentials |
| Preflight | ExposeHeader、AllowedHeader、MaxAge；成功与拒绝都携带三个 `Vary` |
| 校验与 Handler | 空 Origin、`?`、缺失 Content-MD5、不匹配 Content-MD5 |

完整 admin-auth dispatch 不新增独立 fixture。它只是一个两行 switch，编译与评审已经覆盖；wire 与真实 handler 才承载有意义的状态机风险。也不固定 startup 的具体 `errBucketMetadataNotInitialized` 值；一个代表性非 not-found metadata 错误足以覆盖 middleware 决策。

## 被否决的方案 {#rejected}

### 把 CORS tombstone 逻辑塞进通用 metadata merger {#reject-generic-handler}

否决，因为这会让一个七字段 merge 函数中的单个字段拥有特殊 nil、staleness 和提前返回语义。CORS 专用 handler 已经存在，是更小的边界。

### 新建 timestamp-aware metadata 抽象 {#reject-helper}

在至少两个 metadata 类型证明需求完全一致前否决。今天创建通用 helper 会提前编码 Policy、Tag、SSE、Object Lock、Quota、Versioning 之间并不相同的删除语义。

### 新增物理 tombstone 字段或事件日志 {#reject-schema}

否决，因为 `(nil 配置, DELETE 时间戳)` 已经表达全部所需信息。新 schema 只会增加降级与迁移成本。

### 用分布式顺序系统替换 wall clock {#reject-clock-redesign}

否决，因为代价不成比例，也与现有 Site Replication 不一致。正确保留来源时间可以恢复现有契约，但不能全局解决时钟偏差。

### 建设完整多站点测试实验室 {#reject-lab}

否决，因为问题属于本地状态机缺陷，所有重要边界都可进程内直接测试。实验室更慢、更脆弱，也更难诊断。

### 编写自定义 CORS wildcard matcher {#reject-matcher}

否决，因为输入校验可以把现有 matcher 限制到 S3 支持的单 `*` 语言。重新实现匹配只会制造更多边缘。

### 现在收紧所有校验 {#reject-strictness}

否决，因为强制方法大写、Unicode ID 计数与 trailing document 拒绝可能改变已接受输入，却没有安全或真实客户端兼容证据。

### 在同一分支修复所有相邻复制问题 {#reject-scope-expansion}

否决，因为代码看起来相似不代表语义相同。每个历史问题都必须有独立复现、Issue、评审和发布边界。

## 成本、收益与剩余风险 {#tradeoffs}

### 收益 {#benefits}

- 浏览器应用与常见 SDK 获得标准 S3 Bucket CORS；
- 每个桶可使用比集群全局 fallback 更窄的 Origin 策略；
- 正常交付、漏发、乱序、重试和 heal 最终收敛到同一状态；
- Peer 漏收 DELETE 不会导致已撤销浏览器来源被恢复；
- metadata 错误不能把已配置桶静默扩大到全局 CORS；
- wildcard 与 credentials 行为符合既有 S3 客户端预期。

### 实现与维护代价 {#costs}

生产修改只涉及 bucket metadata 时间戳、CORS peer apply/heal/status、CORS middleware 和 CORS 校验。最大的新增量是回归测试，因为必须在两个受支持 ObjectLayer 测试后端证明状态收敛。

不增加依赖、服务、配置键、存储字段、后台 worker 或跨仓库服务端依赖。长期成本是维护 S3 兼容矩阵、来源时间测试与文档。

### 设计上接受的剩余风险 {#remaining-risks}

- wall-clock 顺序依赖站点时钟同步；
- 同时间戳使用 CORS 局部确定性 tie-breaker，而不是全局复制重构；
- CORS 写入不支持混合版本运行；启用功能前必须升级所有站点；
- 降级写入时老版本可能忽略或丢弃 CORS metadata；
- 完整 Console 管理仍不存在；
- CORS 之外继承的复制缺陷仍是独立工作。

这些是可见约束，不是隐藏的“完全一致”宣传。

## 保持独立的历史善后 {#follow-ups}

对抗评审确认了现有初始同步路径中的一个无关缺陷：Object Lock 事件虽然使用 `SRBucketMetaTypeObjectLockConfig`，却把 payload 放进 `Tags` 而不是 `ObjectLockConfig`。它需要独立 Issue 与修复。

相邻站点摘要也存在累计计数模式，Policy/Tag/SSE/Quota/Versioning peer handler 还可能共享来源时间或 tombstone 弱点。后续规则是：

1. 分别复现每个行为；
2. 按受影响的 metadata 契约建立聚焦 Issue；
3. 不在 CORS 分支修改；
4. 只有至少两个类型证明语义完全相同后，才考虑共享 helper。

这样既诚实清理历史问题，又不会把有边界的 CORS 修复变成 Site Replication 大重构。

早于本地 `CreatedAt` 的事件被视为旧 bucket incarnation 并忽略，同时使用按桶去重的日志记录。Status 会继续暴露 mismatch；删除这个 floor 反而可能把旧 CORS grant 安装到同名新 bucket。

## 兼容性影响 {#compatibility}

| 现有用户或部署 | 预期影响 |
| --- | --- |
| 没有配置 Bucket CORS | 继续使用现有全局 CORS |
| 单站 Bucket CORS | 标准控制面与执行行为保留；响应一致性改善 |
| 启用 Site Replication，但不使用 Bucket CORS | 无行为变化 |
| Site Replication + Bucket CORS | 来源顺序、DELETE、重试和 heal 变得可靠 |
| 原始 PUT 调用者 | 必须发送 S3 要求的 Content-MD5 或受支持 checksum |
| 老 peer | 升级前 no-op 未知 CORS 事件；升级后由 heal 收敛 |
| 降级 | 不执行 Bucket CORS；老版本重写记录时可能丢失 metadata |
| 只使用 Console 的运维者 | 暂无 CORS 编辑器；需使用 SDK、CLI 或 S3 API |

空 Origin 与 `?` 的严格化发生在任何包含 PR #71 的 SILO 正式版本之前，因此不存在已经发布的 SILO Bucket CORS 配置需要迁移。

## 验证与发布门槛 {#release-gates}

只有以下条件分别成立，修复才算完成：

1. 定向复制、middleware、校验和 handler 测试通过；
2. 定向 race 测试通过；
3. 完整 `cmd` 测试通过；
4. `go build ./...`、固定版本 lint、生成文件和兼容性检查通过；
5. 标准 `minio-go` PUT/GET/DELETE 与预检冒烟通过；
6. 独立对抗评审没有未解决 blocker；
7. 跟进服务端 PR 已提交、推送、评审并合并；
8. PR CI 与合并后的 `main` CI 全绿；
9. 文档构建和双语链接检查通过；
10. release tag、软件包、镜像发布、部署与生产验证分别完成。

在此之前，Issue #75 保持 open，任何 release 或 Docker 镜像都不能把桶级 CORS 宣称为可发布完成状态。

## 结论 {#conclusion}

桶级 CORS 解决了真实的兼容性和浏览器隔离问题，PR #71 的核心实现值得接纳。剩余缺陷不是丢弃功能的理由，而是要求在发布前精确定义并完成复制状态模型的理由。

最终设计让正常 peer apply、status 与 heal 都保留来源时间和 nil tombstone；对 metadata 错误 fail closed，又不把它升级成新的 S3 可用性故障；修正字面 wildcard 与缓存行为；校验变化坚持证据边界。它复用现有 CORS handler、bucket metadata、save 路径、matcher 和 ObjectLayer 测试，不增加通用框架，也不把无关历史修复塞进分支。

这就是让已经合并的功能达到充分、安全、可维护所需的最小复杂度。
