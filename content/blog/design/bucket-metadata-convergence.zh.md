---
title: "桶配置复制：来源时间、删除与确定性收敛"
linkTitle: "桶配置收敛"
date: 2026-09-12
lastmod: 2026-09-17
author: "冯若航"
summary: >
  SILO #77（随 Server 20260916 发布，PR #180）的研究与设计记录：为什么来源时间、删除墓碑记录和整桶锁缺一不可，六类配置如何处理重复与乱序，为什么滚动升级需要默认关闭的开关，以及备选方案的取舍依据。
tags: [设计, 复制, S3]
weight: 6
draft: false
url: "/zh/blog/design/bucket-metadata-convergence/"
translation_notice: false
---

[#77](https://github.com/pgsty/silo/issues/77) 是已在 [Server 20260916](/zh/blog/release/silo-20260916/)（[PR #180](https://github.com/pgsty/silo/pull/180)，提交 [`48ec10312`](https://github.com/pgsty/silo/commit/48ec10312f98b494f75989615a5d24eae3207e44)）中修复的站点复制正确性缺陷。修复前，接收站点将对端事件的来源时间改写为本地到达时间（`UTCNow`），导致后续真正较新的删除请求因早于本地到达时间而被当作旧事件拒绝；同时部分配置在删除后不再导出时间戳，断连期间遗漏的删除也无法通过自愈（heal）恢复。仅补一个 `DELETE` 分支无法同时解决这两类问题，确定性收敛必须同时具备来源时间保留、持久化删除墓碑（tombstone）、规范化内容比较键以及整桶元数据锁。

## 既有工作与本轮范围 {#scope}

此前的[发布说明](/zh/blog/release/silo-20260903/)、[20260903 安全加固记录](/zh/blog/security/20260903-server-hardening/)与 [Server 兼容性说明](/zh/compatibility/server/#limits)已概述 [#77](https://github.com/pgsty/silo/issues/77) 的删除收敛限制。本文完整记录其状态模型、方案取舍与验证证据（原始实验记录归档于 [`docs/investigations/issue-77.md`](https://github.com/pgsty/silo/blob/114dc10529f242e1e22bafd0a08b1a096d69d4bc/docs/investigations/issue-77.md)）。

| 已有工作 | 已解决的问题 | #77 补齐的剩余缺口 |
| :-- | :-- | :-- |
| [PR #91](https://github.com/pgsty/silo/pull/91) | 每站点配置计数、Policy/Quota 统计与畸形字段隔离 | 计数一致不代表配置内容与来源时间已收敛 |
| [PR #103](https://github.com/pgsty/silo/pull/103) | 整个 `.metadata.bin` 记录的写入串行化 | 仅在写盘阶段加锁，无法保证锁外作出的新旧判断在拿到锁时仍然有效 |
| [#76](https://github.com/pgsty/silo/issues/76)、[#78](https://github.com/pgsty/silo/issues/78) | Object Lock 复制载荷与已有桶接管保护 | 未建立覆盖六类配置的统一来源状态比较规则 |
| [CORS 复制修复](/zh/blog/design/cors-replication-trust/) | 桶级 CORS 的独立删除记录与复制信任边界 | 仅针对 CORS 设计，其语义不能直接套用到全部元数据类型 |

本修复处理 Policy、Tags、SSE、Quota、Versioning 与 Object Lock 六类配置。Lifecycle/expiry 保持其合并载荷时间语义；CORS 保留独立机制；notification、IAM、[对象复制可靠性](/zh/blog/design/replication-reliability/)、MRF、resync 与公开统计各自独立维护。

## 复现确立的故障事实 {#evidence}

原始缺陷在 `ErasureSD` 和 16 盘 `Erasure` 两种对象层上均稳定复现：源站在过去时刻 $T$ 写入配置，接收端落盘时却写入当前到达时间；随后收到源时间为 $T + 1\text{ 分钟}$ 的删除事件时，接收端因该时间早于刚才记录的到达时间而将其拒绝。因此单看 RPC 返回成功，并不能保证各站点最终状态一致。

| 配置类型 | 修复前 PUT 保留来源时间 | 空事件的既有语义 | 修复前无载荷时导出时间 |
| :-- | :-- | :-- | :-- |
| Policy | 否 | 删除 | 是 |
| Tags | 否 | 删除 | 否 |
| SSE | 否 | 删除 | 否 |
| Quota | 否 | 删除；零值 JSON 另有语义 | 否 |
| Versioning | 否 | 不操作 | 不作为删除使用 |
| Object Lock | 否 | 不操作 | 不作为删除使用 |

排查过程中还定位了三个必须在入口层修复的问题：

1. 较旧的批量（bulk）事件可以覆盖较新的单字段配置。
2. 请求在锁外完成新旧判断后再排队等待 `metadata.lock`，拿到锁时仍按已过期的判断覆盖新状态。
3. Tag 的远端 heal 请求漏传了 `UpdatedAt` 时间戳。

因此修复不能只改动 heal 的选源条件，必须覆盖所有真实写入与同步入口。

## 字段状态模型与确定性排序 {#state}

状态模型复用 `.metadata.bin` 中既有的字段载荷、字段 `UpdatedAt` 和桶 `Created`，不新增磁盘格式、SDK 字段或持久化 deployment ID。

| 状态 | 判定条件 | 能否作为复制来源 |
| :-- | :-- | :-- |
| 未知或无效 | 创建时间未知、载荷非法，或字段时间早于 `Created` | 否；缺失或损坏的信息不能当成删除 |
| 空基线 | 空载荷，时间为零或等于 `Created` | 否 |
| 有值基线 | 合法非空载荷，时间为零或等于 `Created` | 是；用于历史配置初始化 |
| 真实更新 | 合法非空载荷，时间晚于 `Created` | 是 |
| 真实删除 | 可删除字段的空载荷，时间晚于 `Created` | 是；该带时间戳的空值即删除墓碑（tombstone） |

Versioning 和 Object Lock 的空事件继续保持无操作，不会因共用排序辅助函数而获得删除语义。零时间字段在比较时使用 `Created` 作为基线，不会把历史空值误判为一次新删除。

状态比较按以下四条规则依次裁决：

1. 真实状态（`UpdatedAt > Created`）优先于基线状态。
2. 真实状态之间，来源时间 `UpdatedAt` 较晚者胜出。
3. 来源时间相同时，删除墓碑优先于有值载荷。
4. 同级且同时间的有值冲突，按规范化内容键的字典序裁决，字典序较大的键胜出。

对于带时间戳的对端事件和 heal，当计算出的有效状态与磁盘已有状态完全相同时，接收端既不写盘也不触发事件通知；本地写入则即使可见载荷不变，也始终分配新的单调递增修订时间。有值基线之间同样按内容键排序，防止较晚创建的默认状态压过真实修改。字典序决胜保证多站点在并发冲突下收敛到同一结果；若业务期望特定配置，管理员仍应在冲突后在权威站点重新提交期望值。

### 比较键必须与落盘行为一致 {#canonicalization}

复制状态统计、heal 选源与对端应用必须比较与持久化完全一致的表示：

- **Policy：** Go 中策略集合由 map 支撑，直接 JSON 编码会受 map 遍历顺序影响。服务端对已校验策略的完整 JSON 树（`Statement`、`Action`/`NotAction`、`Resource`/`NotResource`、`Principal`、`Condition`）执行递归排序，并保留 `Sid` 和数字精度。此外，既有策略解析器支持 `NotAction` 与 `NotResource`，但原结构体必填 `Action`/`Resource` 的编码会对空集合报错。修复统一采用显式字段编码，并同步应用于 `GetBucketPolicy`、管理导出和对端复制，既防止含负集合的合法策略“写得进、读不出”，也保证状态统计与 heal 使用完全一致的比较键。
- **Quota：** 使用解析结果的 JSON 编码作为比较键。`{}`、JSON `null` 或合法零配额文档仍是有值文档。旧版发送端曾将零配额 `PUT` 转为对端删除而在本地保留文档；对于 `mcli quota clear` 发送的零配额，升级后各站点统一保留该有值零配额文档，容量限制同样处于关闭状态。空 Policy 则遵循既有删除语义：合法的空策略 `PUT` 清除策略，后续 `GET` 返回 `NoSuchBucketPolicy`。
- **XML 配置（Tags、SSE、Versioning、Object Lock）：** 直接使用有效 XML 文档的字节切片作为比较键，不引入通用 XML 规范化器。Versioning 是唯一需要预处理的例外：比较前必须先应用 Object Lock 约束（启用 Object Lock 时强制 `Enabled`），再比较最终会落盘的有效文档；否则比较器接受未开启版本控制的文档而 `Save` 落盘时将其改写，会导致下一轮 heal 无限重复发送。

## 在同一把锁内完成决策与落盘 {#atomicity}

六类字段共同存储在一份 `.metadata.bin` 中。读取原始记录、校验载荷、比较时间戳、修改字段和写盘保存必须全部位于同一把 `metadata.lock` 锁内：若先在锁外比较、再进锁内写盘，并发写入下仍会使用过期状态；若拆成按字段加锁，整条记录的读改写又会互相覆盖。

本地写入在 `metadata.lock` 锁内分配单调时间：

```text
max(当前 UTC 时间, Created + 1ns, 当前字段时间 + 1ns)
```

该规则使本地纠正操作能够超过已保存的未来字段时间。带来源时间的对端事件保留其原始 `UpdatedAt`；完全重复或较旧的带时间对端事件在锁内直接返回，不产生磁盘写入。

批量（bulk）路径仅处理显式提供的字段，逐项校验通过后至多保存一次：省略字段保持不变，显式 `null` 按类型删除语义处理，任一字段非法都会在落盘前中止整批更新。导入（import）在每桶最终提交锁内为涉及的六类字段分配统一提交时间，磁盘状态和出站复制事件均使用本次提交返回的归一化快照，不在解锁后重新读取存储拼接旧时间。空 Policy 通过专用删除事件发送，避免被批量结构的 `omitempty` 丢弃。

### 桶接管不能制造假删除 {#adoption}

桶接管（adoption）可能调整桶的 `Created` 时间戳。若把 `Created` 改早，却保留空字段原本等于旧 `Created` 的默认时间戳，空基线就会因 `UpdatedAt > Created` 被误判为真实删除；若把 `Created` 改晚，又可能使历史初始配置因 `UpdatedAt < Created` 变成无效状态。

修复在既有接管锁内，仅将这六类字段中原本为零或等于旧 `Created` 的默认时间同步调整为新 `Created`，真实更新和真实删除的时间戳保持不变。

## 所有入口共用同一套状态规则 {#entry-points}

| 入口 | 行为契约 |
| :-- | :-- |
| 本地 S3/Admin 写入 | 在 `metadata.lock` 内分配单调时间；由提交快照生成出站事件 |
| 专用对端事件 | 在 `metadata.lock` 内比较并保存原始来源时间；保留旧 Object Lock 载荷兼容 |
| Bulk/import | 显式区分字段存在性并原子保存；在最终提交锁内统一分配导入时间 |
| 首次同步 | 通过物理磁盘探测补齐缺失的 `Created`；保留历史有值基线；开关开启后补发真实删除 |
| 本地与远端 heal | 先过滤有效候选再选取最大状态，包含完整来源时间；未知 ID 与故障对端不阻断健康目标 |
| 状态导出 | 值与时间取自同一快照；新增删除时间受滚动升级开关控制 |

首次同步保留既有五类配置发送路径，Versioning 仍通过 `MakeBucketHook` 初始化并由 heal 对齐。当桶元数据未记录 `Created` 时间戳时，`GetBucketInfo` 与 `ListBuckets` 一致地返回物理目录探测时间，首次同步将该恢复时间传给建桶钩子并落盘，避免无元数据记录的旧桶无法写入配置。

heal 不再先取 map 第一项作为胜者再过滤默认时间，而是先筛选有效候选再取最大状态。公开 mismatch 计数不再作为唯一门控：内容相同但来源时间不同仍需同步；反之，最终有效状态相同时不再重复写盘或发送 RPC。

## 为什么需要默认关闭的升级开关 {#rollout}

启动环境变量 `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES` 默认为 `off`，用于控制无载荷的 Tags、SSE、Quota 删除墓碑时间是否在状态接口与首次同步中向外导出。

| 行为 | `off`（默认） | `on` |
| :-- | :-- | :-- |
| 来源时间排序与 `metadata.lock` 原子应用 | 启用 | 启用 |
| 普通实时删除事件复制 | 启用 | 启用 |
| Policy 的既有删除时间导出 | 保留 | 保留 |
| Tags/SSE/Quota 无载荷时的真实删除时间导出 | 隐藏 | 导出 |
| 首次同步补发真实删除 | 仅 Policy | 补齐全部四类可删除字段 |

旧版节点无法安全消费全部新增的删除墓碑信息——例如旧版 Quota heal 会在清空原始载荷后保留已解析的内存缓存值。默认保持 `off` 能够安全隔离滚动升级窗口。

### 协调升级与降级步骤

1. 将所有参与站点的全部节点升级至 [Server 20260916](/zh/blog/release/silo-20260916/) 或更高版本，确认同站点配置一致并排空在途请求。
2. 在全部节点统一设置 `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES=on` 并重启。
3. 如需回滚到旧版本，先在全部节点设置 `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES=off` 并重启，再滚动降级软件二进制。

在 `off` 模式下，被隐藏的 Tags、SSE、Quota 删除墓碑可能导致对端在 heal 时重复发送旧状态并由已升级接收端拒绝；只有全站点统一开启 `on` 且状态稳定后，后续 heal 周期才会达到零元数据 RPC。

## 保留与否决的候选方案 {#minimality}

| 设计决策 | 工程依据 |
| :-- | :-- |
| 保留统一的内部六字段排序辅助函数 | 六类配置复现了完全相同的到达时间覆盖缺陷；共用比较器可消除各入口规则漂移，同时按类型区分删除能力 |
| 保留现有整桶锁、持久化字段与 heal 周期 | 分别承担原子性、删除持久性与断连恢复职责，无需引入外部协调服务 |
| 不止于把 `UTCNow` 替换成来源时间 | 仅替换时间戳仍会留下锁外过期判断、无载荷删除丢失、等时冲突与首次同步缺口 |
| 用默认关闭的开关门控新增墓碑导出 | 旧接收端与旧 Quota 缓存路径在混合版本下不安全，必须显式隔离滚动升级窗口 |
| 不以 deployment ID 决胜，也不引入 HLC 或新磁盘 schema | 既有时间戳配合规范化内容键已能保证确定性收敛，无需改动磁盘持久化格式 |
| 不一刀切拒绝零时间专用事件 | 旧版 Tag heal 确实漏传时间戳；以本地单调时间兼容零时间事件可保持协议平滑过渡 |
| 不把所有桶元数据泛化为同一种删除语义 | Versioning 与 Object Lock 不可删除，而 Lifecycle 与 CORS 拥有各自的合并与删除机制 |

生产代码共新增 729 行、删除 692 行 Go 代码（净增 37 行），主要以统一的状态比较器替换原先重复的各类型应用与 heal 分支。每一项保留机制都对应已复现的故障模式：去掉整桶锁会重现跨字段读改写覆盖，去掉规范化 Policy 比较键会在负集合策略上造成永久假 mismatch，去掉升级开关则会在滚动升级期间击穿旧版节点的 Quota 缓存。

## 验证与测试证据 {#validation}

位于 `cmd/site-replication-metadata_test.go`、`cmd/site-replication-metadata-heal_test.go` 与 `cmd/site-replication-metadata-gate_test.go` 的回归测试套件在 `ErasureSD` 和 16 盘 `Erasure` 两种对象层上验证了完整契约：

| 验证范围 | 验证结论 |
| :-- | :-- |
| 来源时间保留、四类可删除配置、重复与乱序事件、锁前排队、跨字段并发写入 | 回归测试与 `-race` 竞态检查在两种对象层上全部通过 |
| 等时双向到达顺序、删除优先于有值、Policy 规范键与负集合 `GET`、bulk/import 原子性 | 不同到达顺序收敛至完全相同的最终状态 |
| 创建时间物理探测恢复与旧顺序策略状态比较 | 真实磁盘对象层测试在每块盘上标记桶目录时间，验证无元数据记录的桶可正确恢复 `Created`，且乱序 Statement 策略不再触发假 mismatch |
| 两个真实站点进程实验（每站 4 个数据目录） | 历史六类配置首次同步保留 `Created`；丢弃真实 `PUT` 的出站 RPC 并注入乱序事件后，正常 30 秒 heal 周期恢复一致 |
| 断连遗漏删除与源站重启 | 四类配置的删除墓碑落盘后跨源进程重启保留，恢复连接后自动收敛 |
| 稳态零 RPC 与诊断日志去重 | 连续两个 65 秒观察窗口（各含两个正常 heal 周期）无多余元数据 RPC；重复异常按“桶/字段/原因”独立去重 |

在测试复核中，早期使用桩对象（stub）伪造创建时间探测的测试被替换为操作真实本地盘桶目录时间戳的测试——确保该用例在叠加修复前生产代码时必定失败，仅在真实恢复链路生效时通过。

### 实现复核与演进记录 {#review}

从基线 `5c5765816` 与初版实现 `1ee64a8d8` 出发，复核发现的三处问题（真实磁盘创建时间恢复、旧顺序 Policy 状态键与 heal 诊断去重）已在 `62cf066ff` 与 `fcbb93e89` 中补齐，最终在 `461e9a721` 完成测试格式整理并通过全量 `cmd`/`internal` 测试与 lint 检查。

## 运维边界与已知限制 {#limits}

1. **历史时间污染无法自动还原。** 升级前被本地到达时间覆盖的配置和无时间戳旧事件已经丢失原始来源时间。部署升级后，应核对各站点配置并在权威站点重新提交期望的配置或删除操作。
2. **零时间专用事件继续兼容。** 不带时间戳的专用对端事件会分配本地单调时间并记录限频 `legacy-zero` 警告；bulk 导入的零时间校验约束保持不变。
3. **桶创建世代冲突不自动合并。** 早于目标桶 `Created` 的事件不予应用（记录 `before-created`）。缺失 `Created` 的桶仅从真实物理桶目录修改时间恢复近似值；若已存在桶的物理创建时间仍为零，配置写入返回 `500 InternalError`（缺失桶返回 `404 NoSuchBucket`）。在配置写入或首次站点同步将该恢复时间落盘前，周期性 heal 会在两个方向上跳过该桶。
4. **物理时钟不是因果时钟。** 本地单调时间允许管理员在未来时间戳之后继续发起本地修正，但跨站点并发写入若与字典序决胜结果不符，仍需人工确认并重新提交。
5. **诊断按桶、字段与原因有界去重。** `legacy-zero`、`before-created`、`indeterminate`、`unreachable` 与 `peer-error` 复用 `LogOnceIf` 以 Warning 级别输出并按小时清理；空基线以及尚未拥有该桶的对端保持静默，而损坏的存量配置即使无可用来源也会输出 `indeterminate` 警告且不触发出站 RPC。

关联记录：[复制标签排序](/zh/blog/design/replicated-tag-ordering/) · [副本元数据归一化](/zh/blog/design/replica-metadata-normalization/) · [请求头超时控制](/zh/blog/design/request-header-timeouts/) · [副本元数据审计](/zh/operations/replication/replica-metadata-audit/)
