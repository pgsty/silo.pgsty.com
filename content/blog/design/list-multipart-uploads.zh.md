---
title: "ListMultipartUploads：实现、升级契约与历史设计"
linkTitle: "ListMultipartUploads 兼容性"
date: 2026-08-30
lastmod: 2026-10-17
author: "冯若航"
summary: >
  记录 #79 的最终设计取舍：统一持久列表、逐条省略无身份的历史上传、退役迁移开关；解释备选方案、格式兼容性、读写成本、验收证据与尚未解决的边界。
tags: [设计, S3, 兼容性, 分段上传]
weight: 35
draft: false
url: "/zh/blog/design/list-multipart-uploads/"
---

> [!WARNING]
> **旧版分片列举设计已被覆盖 · Earlier multipart-listing designs superseded (2026-10-17)**
>
> **中文：** 本页保留的 8 月分析与 9 月 `legacy`/`strict` 方案已被新设计覆盖，请以[最新设计决策（中文）](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261017)为准。新设计统一使用持久列举，逐条跳过经确认缺少身份的历史上传，取消迁移开关；代码已合入主干，尚未随 Server 版本发布。旧章节只用于理解历史，不改变旧版本二进制的实际行为。
>
> **English:** The August analysis and September `legacy`/`strict` proposal retained below are superseded by the [latest design decision (English)](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261017). It selects one persistent listing path, individual omission of confirmed unidentified historical uploads, and no migration switch. The code is merged into main but has not shipped in a Server release. Historical sections do not change the behavior of older binaries.

> **2026-10-17 源码集成更新：** 统一列举修复通过全部八项 PR 检查，经 [PR #243](https://github.com/pgsty/silo/pull/243) 合入主干，合并提交为 [`7e9454456`](https://github.com/pgsty/silo/commit/7e9454456ee7065cd1d782fc4498338324a94894)。它面向下一次 Server 发布，未包含在 [Server 20261015](/zh/blog/release/silo-20261015/) 中；源码接入不会更新已安装的二进制或容器镜像。

> **2026-09-17 发布更新：** 本文记录的九月源码修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；发布时的启用条件保留在历史章节；待发布候选的变化见下节。下方带日期的源码状态与验证记录保留当时的范围。


这是 [SILO Issue #79](https://github.com/pgsty/silo/issues/79) 的问题说明、设计分析与决策记录。

阅读顺序：[待发布行为](#implementation)说明客户端与运维会看到什么；[2026-10-17 决策记录](#decision-20261017)解释为什么这样改、放弃了什么、付出什么代价；[9 月发布契约](#implementation-20260916)与[8 月设计分析](#analysis-20260830)保留历史依据。

## 待发布：统一使用持久元数据列举 {#implementation}

**本节描述 #79 后续修复候选，不代表已经发布。** 对包含本次修改的构建，本节取代下方的模式切换设计；Server 20260916 仍按其发布时的 `legacy`／`strict` 行为运行。此次去掉模式选择，在已有集群上升级后也自动使用磁盘元数据列举。

### 客户端会看到什么

`prefix` 是 S3 已有的字符串参数，不是新增的布尔开关。例如，`GET /photos?uploads&prefix=trips/` 列出对象名以 `trips/` 开头的未完成上传；`GET /photos?uploads&max-uploads=1` 每页列出一项，有后续结果时返回翻页标记。两种请求现在都先发现磁盘上的上传，再筛选、排序、分页；不会因入口节点缓存不同而得到不同清单，也不会把前缀当成完整文件名。

之前的实现已经在新上传的 `xl.meta` 中写入两个内部身份字段。本次不再新增字段、元数据文件、数据库、索引，也不迁移目录。元数据中的相关内容可以直观理解为：

```json
{
  "x-minio-internal-multipart-v1-bucket": "photos",
  "x-minio-internal-multipart-v1-object": "trips/2026/video.mp4"
}
```

这只是元数据映射的示意，不是 `xl.meta` 的实际二进制格式。两个字段随原有元数据一起按上传的写入 quorum 保存，完成上传时删除。旧版本的映射读取器能够接受未知条目；此次不改变编码或存储格式。回退会恢复旧的列表局限，并不会补出原本缺失的身份信息。

### 旧上传不再挡住新上传

按每条记录判断，而不是按集群安装时间判断：

| 磁盘上发现的记录 | 列表如何处理 |
| --- | --- |
| 两个身份字段完整、合法，且与目录哈希一致 | 符合请求的桶和前缀时列出 |
| 经既有读取 quorum 确认可读、选出的元数据中两个字段都不存在 | 只跳过这条历史上传，继续列举 |
| 只存在一个字段、身份为空或非法、可读副本的身份矛盾、哈希不一致，或带身份的记录使用不支持的原生上传 ID | 返回错误，不能把损坏的新记录当成历史数据 |
| 扫描覆盖不足、元数据无法满足读取 quorum、超时或超出资源预算 | 返回错误，不能成功返回不完整清单 |

旧上传若已知桶名、对象名和 upload ID，仍能继续传分片、完成或取消。即使请求前缀恰好等于旧上传的完整对象名，也会跳过该记录；公开 API 不再走原来的精确键捷径。既有过期清理策略不变，过期年龄按发起时间计算，不按最近传分片的时间计算，不应为了消除历史例外而缩短过期时间。

不做回填，不强制排空，也不要求预检通过才开放列表。要让今后创建的上传都带身份，仍需升级所有写入节点。滚动升级期间，旧写入节点可能继续产生无身份上传，旧服务入口也可能继续提供旧的列表语义。切换服务版本后应从头开始分页遍历。**历史上传被省略是明确的兼容性例外：列表为空，不足以证明磁盘上没有旧上传。**

### 退役配置与诊断接口

候选版本忽略 `MINIO_API_MULTIPART_LISTING` 的所有值，启动时提示它已失效；可以从部署配置中移除。历史共享配置键 `api multipart_listing` 仍被容忍，不会导致其它 API 配置失效。不再增加替代环境变量。若要回退到拒绝该共享键的旧构建，下方历史章节中的定向 reset 步骤仍有参考价值。

既有只读签名接口 `GET /minio/admin/v3/multipart-preflight` 仍要求 `admin:StorageInfo`。现在返回 `mode: "persistent"`；`legacyUploads` 统计观察到的历史记录，`complete` 表示所有盘都已扫描且无扫描错误，`ready` 表示完整诊断后没有发现历史记录。**`ready=false` 不会关闭列表功能。** 离线或无法读取的副本仍会导致诊断不完整，不能把不完整的计数当成不存在旧上传的证据。

### 代价和保留边界

此次没有在上传路径增加磁盘写入、RPC、锁、删除墓碑或第二份索引。两个身份字段此前已经保存。新增的日常开销在列举操作上：每一页都会跨 pool/set 扫描上传目录、读取候选元数据，再排序和筛选；其它桶的上传和被跳过的旧上传也会消耗扫描资源。把每页条数调小，只减少响应量，不减少前面的发现工作。

保留既有保护：每进程最多两个并发扫描，每次扫描最多 16 个身份读取 worker、4 个完整元数据读取 worker、30 秒上下文预算，以及 100,000 个累计目录条目。条目包含两层目录以及多盘重复项。16 盘上每个上传使用独立对象名时，一个上传约消耗 32 项，10,000 个这样的上传会超预算，返回 `SlowDown`（503）。如果上传总量不降低，反复重试也不会消除这种确定性的预算超限。本次解决列表语义，不宣称解决大规模列举性能；持久索引或其它有界发现方式需要独立的性能设计与验收。

取消操作保留此前的**默认行为**：满足读取 quorum 后尽力删除，按 pool 顺序返回。退役列表开关也会移除它附带的可选 strict 取消分支；此前主动依赖严格多数删除确认的调用方需要了解这个变化。HTTP 204 不是所有物理副本均已删除的证明。迟到创建竞争仍单独保留：默认路径故障测试展示，在 16 盘／EC:8 下，七份迟到写入加一份离线旧副本可以在取消后恢复八份可读副本。本次没有增加阻止迟到创建的持久屏障。

回归覆盖新旧混合 HTTP 分页、目录分组、按已知 ID 继续并完成旧上传、字段缺失或损坏、读取失败、重新打开存储层后无缓存列举、多 set/pool、已删除的翻页标记、扫描限流，以及原有默认取消行为。显式运行的 `BenchmarkMultipartListingCapacity` 使用 1,000 和 10,000 个真实磁盘上传，包含新旧混合与其它桶；超限场景验证返回错误而非成功的残缺页面。这些本地检查不等于生产分布式存储延迟和前台上传吞吐验收。

## 2026-10-17 决策记录：统一列举，接受历史例外 {#decision-20261017}

**状态：方案已选定，本地验证与 PR CI 已通过，源码已合入主干，尚未发布。** 本节对应实现提交 `4ed86dfe62ed6e07016885552feebcb59f779631`，于 2026-10-17 经 [PR #243](https://github.com/pgsty/silo/pull/243) 接入。源码合并不代表已有发行制品或已部署生产。Server 20260916 与 Server 20261015 的二进制仍适用下方的历史 legacy／strict 契约。

### 决策与优先级 {#decision-contract}

采用一条公开列表路径：从磁盘元数据发现上传，再统一执行 S3 的前缀筛选、目录分组、排序和分页。对于经过读取校验、确认没有桶名和对象名身份的历史上传，只省略该条记录。新版本创建的上传继续使用已有身份字段；升级老集群也会自动获得新行为，无需迁移开关、历史数据回填或先清空全部上传。

选择的优先级是：先让有完整身份的上传得到可靠的标准 API 结果；保持原有上传写入路径和默认取消的可用性；接受临时历史上传无法完整列举的有限例外；再单独解决大规模扫描和迟到写入问题。**“最小且充分”针对的是这项已界定的列表修复，不等于 issue #79 的所有问题都已关闭。**

“老人老办法，新人新办法”按记录内容判断。“老”指两个身份字段都不存在，不是集群创建得早；“新”指写入了可验证身份，不是请求日期更新。即使集群已运行多年，新写入节点创建的上传也适用新规则。混合版本期间，未升级的旧 writer 仍可能继续产生无身份记录，因此不能承诺切换一台服务器后所有上传立即可见。

这里明确放弃一个更强的保证：成功列表不一定覆盖磁盘上的全部历史上传。被省略的记录没有被删除，已知桶名、对象名与 upload ID 的客户端仍能继续操作它们。对新格式候选，无法完成必要校验时返回错误，不用一个成功的残缺页面掩盖问题；扫描的 pool 生命周期范围和容量限制仍然适用。

### 为什么会有 strict，为什么这次可以去掉开关 {#decision-background}

分段上传可以理解为“先领取一个 upload ID，再分几次交付文件内容，最后确认合并”。`ListMultipartUploads` 列出的是这些尚未完成的上传任务；它不是列出已经保存好的对象，也不是列出某个上传内部的分片。

原来的两条快捷路径缺少统一的真实清单。请求没有 `prefix` 时读取节点内存缓存，重启或换节点后可能看不全；有 `prefix` 时把整个字符串当成一个完整对象名进行查找。假设桶 `photos` 有三个未完成上传：`trips/a.mp4`、`trips/b.mp4` 和 `trips/sub/c.mp4`：

| 请求示例 | 客户端合理期待 | 旧快捷路径的问题 | 本次候选行为 |
| --- | --- | --- | --- |
| `GET /photos?uploads&prefix=trips/` | 三个上传 | 去找名为 `trips/` 的单个对象，可能返回空 | 返回三个匹配的上传 |
| `GET /photos?uploads&max-uploads=1` | 一项及后续页标记 | 缓存路径可能一次返回多项，分页失效 | 返回一项，并在仍有结果时返回翻页标记 |
| `GET /photos?uploads&prefix=trips/&delimiter=/` | 两个直接子项和分组 `trips/sub/` | 仍走精确对象查找，无法形成前缀分组 | 返回两个 `Upload` 和一个 `CommonPrefixes`，分组也占分页名额 |
| 重启后重复上述请求 | 同样的可读上传仍可被发现 | 内存清单消失，磁盘上的上传并未消失 | 重新读取持久状态，不等缓存恢复 |

`prefix` 从来就是 S3 的字符串参数；这里没有新增 `prefix=true`。分页客户端回传上一页的 `NextKeyMarker` 和 `NextUploadIdMarker`，分别作为 `key-marker` 和 `upload-id-marker`，交给 SDK 做 URL 编码，不应自己生成 upload ID 标记。即使标记对应的上传已完成或取消，仍可继续翻页；并发创建或删除下，多页结果并不是同一时刻的快照。

[PR #198](https://github.com/pgsty/silo/pull/198) 已经实现“保存身份、扫描磁盘、统一分页”的算法，称为 `strict`。它的特殊之处是采用更严格的完整性要求，并非另一套 S3 API。由于无法确定无身份旧上传属于哪个桶，原 strict 方案遇到这种记录就拒绝整次列举；别的桶遗留的一条记录也可能使当前请求失败。

随后 [PR #213](https://github.com/pgsty/silo/pull/213) 恢复 `legacy` 默认值，用服务器环境变量让运维人员在准备完成后再启用 strict，并避免普通升级改变默认 Abort 的成功条件。当时的开关承担的是**迁移与可用性选择**，不是启用 S3 `prefix` 参数所必需的机制。

本次改变了历史记录的处理契约：允许逐条省略已确认的无身份上传，并保留默认 Abort 的可用性。这就移除了为了等待旧上传排空而保留模式开关的主要理由。继续保留开关，会让默认路径的缺陷继续存在，还要求运维和测试长期维护两套行为。因此退役开关，不再增加新的迁移环境变量。

### 备选方案与选择理由 {#decision-alternatives}

下表用名称区分本轮方案；下方 8 月历史章节里的“方案 1／2／3”属于另一轮比较，不沿用其编号。

| 方案 | 得到什么 | 代价与不足 | 本次取舍 |
| --- | --- | --- | --- |
| **统一持久扫描，逐条省略确认无身份的旧上传** | 普通升级就能修正有身份上传的前缀与分页；不加迁移配置或第二份存储状态 | 旧上传清单不完整；每页扫描有明显读放大，受现有预算限制 | **采用。** 正好满足接受历史例外、确保新写入可发现的要求 |
| 保留 `legacy`／`strict` 两种模式 | 可暂时沿用旧行为，由操作者选择切换时机 | 默认问题继续存在；增加配置、排障和测试组合，strict 仍需处理历史阻塞 | 不采用。新的逐条兼容策略已经消除原来的切换前提 |
| 默认开启原 strict，任何旧上传都报错 | 在成功响应时提供更强的历史清单完整性要求 | 一条无法识别的旧记录就可能阻塞所有桶，必须排空或人工处理；丢失 key/ID 时难以操作 | 不采用。把临时历史数据变成整个列表服务的升级障碍 |
| 回填所有历史上传的身份 | 若有权威映射，可恢复完整历史清单 | 目录只有不可逆的桶／对象哈希；缓存或日志不保证齐全，不能凭空还原原名 | 不做通用回填。有可靠外部映射时的定向恢复另行处理 |
| 增加持久的桶级有序索引 | 可按桶、前缀与标记直接查找，减少重复全量扫描 | 创建、完成、取消要同步维护第二份状态；需定义原子性、修复、重建和混合版本行为 | 延后。规模超出现有扫描能力时，应单独设计并验收 |
| 只补缓存，或增加自有 `prefix=true` 参数 | 表面改动较少，部分单节点场景可能工作 | 不能从根本上解决重启、跨节点和持久分页；自有参数也无法修复标准 SDK 的请求 | 不采用。没有提供可信的持久清单 |

把索引和取消屏障同时加入本次修复，确实可能处理更多问题，但会改变创建与删除的存储协议，使一个列表改动扩展成新的数据生命周期设计。当前决策先复用已经存在的扫描实现，同时明确留下这些后续工作。直接提高扫描条目上限也不等于解决容量问题：每页的扫描量、内存分配与超时压力仍会增长。

### 元数据保存在哪里，为什么兼容 {#decision-storage}

持久扫描先看到的是目录，不是用户的文件名。已有目录结构可以示意为：

```text
.minio.sys/multipart/
└── <桶名与对象名计算出的哈希>/
    └── <内部 upload ID>/
        ├── xl.meta        ← 已有的二进制元数据文件
        └── ...            ← 上传状态与分片相关文件
```

哈希能用于验证“这个桶／对象是否应该放在这个目录”，却不能倒过来还原原始名称。upload ID 也不包含对象名。所以上文示意的两个身份字段保存原始桶名和完整对象名，位于 `xl.meta` 已有的内部元数据映射中，跟随原有写入一起保存；完成上传时移除上传专用字段。**这两个字段在本次后续修复之前就已写入，之前的 legacy 和 strict 模式都会写。本次并未再加两个 key。**

设计上选择已有映射，是因为它本来就用于保存可扩展的键值信息。没有改变目录名、二进制格式版本或必须识别的固定结构字段，也没有新增一个 JSON 文件。若另建旁路文件，还要多写一份文件，并处理“主元数据已写、身份文件未写”或取消后残留一份的问题；当前需求没有得到相应收益。

兼容性结论有具体边界。对 SILO 2026-08-06 历史提交 `3be10fcc1a44f6620ded0bd303461f9d688cca23` 的 `xlMetaV2Object` 及生成的 MessagePack 编解码器，已检查并抽取原实现做解码、重编码验证：内部 `MetaSys` 是 `map[string][]byte`，可以接受并保留这两个条目，不依赖字段名白名单。它不是遇到未知 key 就拒绝读取的固定 schema；当前响应头也会过滤内部保留前缀。

这项验证说明该历史编解码器不会因为这两个映射条目而报错，并能在重编码时保留它们。它**不等于**对所有历史服务端的恢复、修复、复制流程或第三方离线解析器完成了全量回退认证。旧代码能读文件，也不表示它会提供新的列表语义；较旧的完成路径还可能保留不认识的内部字段。受支持的发布验收范围仍是协调的 PGSTY 组件栈，上游兼容保持尽最大努力。

### 哪些可以跳过，哪些必须报错 {#decision-read-policy}

“查不到身份就跳过”过于宽松：元数据损坏、读盘失败或者拿到不同版本的副本，都可能造成查不到。当前规则要求先区分历史格式与无法确认的状态。

1. 在参与服务的 pool/set 中发现上传候选；每个 set 需要足够的目录扫描覆盖。这里 pool 是一组存储资源，set 是其中一起保存纠删码数据的磁盘组。
2. 单盘上的合法身份若能证明属于其他桶，可提前排除。否则按原有元数据读取规则收集副本，达到读取 quorum，也就是有足够的有效副本让存储层确认这条记录可读。
3. 对进入完整读取的候选，额外比较已经读回的有效副本身份。原有通用 quorum 选择并不比较这两个字段；若一个副本无身份、另一个有身份，或身份值相互矛盾，不能恰好选中“旧副本”就把新上传藏起来。
4. 只有确认两个字段都**不存在**时才省略；字段存在但值为空、只存在一个字段、身份非法、目录哈希不匹配、带身份记录的原生 ID 不支持，均返回元数据错误。读取或扫描失败也保持失败。
5. 汇总有身份的上传，按桶／对象／upload ID 去重，再全局排序、筛选、分组和截取页面。不能先在各盘或各 pool 分页再拼起来，否则排序与后续标记会不一致。

新增的副本身份比较使用已经读取的数据，只增加字段查找与比较，不额外读盘。其他桶的合法单来源身份可以提前排除，因此普通列表不是对全部桶全部副本做完整损坏审计。正常列举继续遵守已有的暂停 pool 排除规则；预检会检查暂停 pool，本次未重新定义其生命周期。

读取 quorum 与目录发现的门槛也不同。例如 16 盘、EC:8 的元数据可能只需八份就可读，但目录发现要求至少九盘扫描成功，以避免把没有发现的目录当成不存在。发生不足覆盖时拒绝返回成功，是这条扫描路径相对旧缓存列表的可用性代价之一。

### 成本：写入路径很小，列举路径并不便宜 {#decision-cost}

必须区分比较基线。相对本次修改前已经有 strict 的代码，新上传仍写同一个 `xl.meta`，不增加磁盘写入次数、RPC、锁、索引或持久墓碑。相对更早的无身份实现，两条映射记录增加字段名、桶名和对象名的 UTF-8 字节以及编码开销，并随元数据副本保存；这是此前实现已经引入的成本。

对于之前使用默认 legacy 的部署，公开列表从查缓存或单键目录改成扫描持久状态，读成本会明显增加。一次扫描的工作量取决于存储中的上传总量，而不只取决于响应里的条目数。

| 操作 | 工作与代价 |
| --- | --- |
| 发起上传、上传分片、完成上传 | 本次不新增身份写入步骤或第二份状态；完成仍移除已有上传身份字段 |
| 列表发现 | 每页遍历相关 pool/set 的两层上传目录，其他桶和待省略旧记录也占预算 |
| 身份读取 | 通常先读一个来源副本；属于目标桶或身份不确定时，再走原有全盘元数据读取 |
| 校验、排序与分页 | 比较已读副本的身份；保存目标桶候选并全局排序，排序约为 `O(M log M)`，M 为参与排序的目标桶上传数；另有发现候选集合的内存 |
| 下一页或缩小 `prefix`、`max-uploads` | 仍会重新发现并校验候选；只缩小前缀或页面不能相应减少前面的扫描工作 |
| 预检 | 也占用扫描名额；是按需诊断，不是每次上传或启动必做的迁移流程 |

为使数量直观，假设一个健康的 N 盘 set，每盘目录一致，有 H 个不同对象哈希目录、U 个上传目录：返回目录条目约为 `N × (H + U)`，`ListDir` 调用约为 `N × (1 + H)`。这两者不是同一指标。目标桶或历史候选通常需要一次来源读取，加 N 次完整读取；其他桶候选的合法身份通常只需一次来源读取。

因此四盘、每个上传使用不同对象名、10,000 个目标桶上传时，一页也约需 80,000 个目录条目、40,004 次 `ListDir` 和 50,000 次 `ReadVersion`。这些是存储接口调用数，不应全部称作网络 RPC 或物理磁盘 I/O；本地盘、缓存与部署方式会影响实际代价。

现有保护保持不变：每进程两个扫描名额，每扫描 16 个身份 worker、四个完整读取 worker、30 秒 context 预算、100,000 个累计目录条目。并发已发出的调用可能继续完成，worker 退出前不会释放扫描名额，所以这些限制也不是精确的峰值内存或物理 I/O 截止保证。

**100,000 个条目不是 100,000 个上传。** 16 盘且每上传独占一个对象哈希目录时，约 3,125 个上传就用完条目预算；10,000 个需要约 320,000 项，会返回 `SlowDown`（503）。相同对象上的多个上传可共用上层目录，其他 pool 和残留目录也会改变数量。请求更小的页面或原样重试都不能解决确定性的预算超限。

2026-10-17 对最终候选运行真实文件系统基准，记录首个 1,000 项页面：

| 四盘上的 10,000 个上传 | 耗时 | `ListDir` 次数 | `ReadVersion` 次数 | Go 累计分配字节 |
| --- | --- | --- | --- | --- |
| 全部为目标桶的新格式记录 | 约 2.40 秒 | 40,004 | 50,000 | 485,925,912 |
| 4,000 个目标桶新记录、1,000 个无身份旧记录、5,000 个其他桶新记录 | 约 2.42 秒 | 40,004 | 30,000 | 330,686,136 |

环境为本地 macOS arm64、Apple M5 Max、Go 1.27.2，每种情况只测一次，创建测试数据不计时，期间可能有其他本地验证。累计分配不是峰值驻留内存；更少的接口调用在这两次观察中也没有直接变成更短的耗时。它们不是生产分布式吞吐认证，也不能与 9 月 Docker 环境的数据相除后宣称性能提升。可在服务端仓库复现这两个最终候选样例：

```bash
go test ./cmd -run '^$' \
  -bench '^BenchmarkMultipartListingCapacity$/^drives=4$/^uploads=10000$' \
  -benchtime=1x -benchmem -timeout=10m
```

### 为什么这次不修“取消后又出现” {#decision-abort}

列表与取消有关联，但不是同一个问题。可靠列表负责发现仍然存在的上传；“取消返回后，任何在途创建都不能再使它出现”需要创建与取消共同遵守一个持久的顺序规则。

例如，创建请求已向若干磁盘发起写入，其中一些调用超时但物理写入还未结束。取消随后删除此刻能看见的记录，迟到的写入再落盘，上传就可能重新具备可读副本。默认路径的故障测试保留了一个明确反例：16 盘／EC:8 下，九盘先完成创建、七盘写入滞后；已完成盘中的一盘离线，取消能读取并清理其余八盘；随后七份迟到写入落盘，离线盘恢复后，加上其中的一份旧记录，可以恢复八份可读副本。这里证明的是重新可读，不是已经达到九份的写入 quorum。

仅提高删除确认数量，不能阻止仍在进行的创建写入。真正的屏障可能需要持久墓碑或代际标记，让迟到写入知道“这个 upload ID 已被取消”，并定义屏障在哪些盘上生效、何时清理、离线盘如何恢复、旧节点如何协作。这会增加创建与取消热路径的存储状态和协调成本，必须单独设计、故障测试和验收。

本次保留此前默认的读取 quorum、尽力删除和按 pool 顺序返回的 Abort 行为，避免列表修复降低普通部署的取消可用性。原来与 strict 开关捆绑的“多数删除确认及残片重试”分支随开关退役；**主动启用旧 strict 的用户会失去这部分更强的确认行为**，不能笼统说所有用户的取消语义都未改变。HTTP 204 也可能是不存在上传的幂等响应，不能拿它证明所有物理副本已清空。

### 修改位置与影响范围 {#decision-changes}

| 范围 | 本次修改 | 原因与影响 |
| --- | --- | --- |
| `cmd/erasure-server-pool.go`、`cmd/erasure-sets.go`、`cmd/erasure-multipart.go` | 公开列表统一进入持久扫描，移除模式分支和公开精确键／缓存捷径；Abort 保留默认路径 | 所有公开入口采用同一套列表算法；即使旧记录的完整对象名恰好等于 prefix，也不再额外捞回该记录 |
| `cmd/erasure-multipart-listing.go` | 逐条省略确认无身份的旧记录，校验有效副本的身份一致性，诊断报告使用 `persistent` | 历史记录不阻断新记录；损坏或矛盾身份仍报错，预检不再决定功能是否开启 |
| `internal/config/api/api.go`、`cmd/common-main.go` | 环境变量失效时提示，容忍退役共享配置，不再提供模式选择 | 无需配置新开关；部署配置里的旧变量可移除，其他 API 设置继续生效，不自动重写共享配置 |
| 回归测试与容量基准 | 覆盖新旧混合、HTTP 参数、重启、分页、元数据故障、默认取消与扫描预算 | 把已承诺的行为和仍存在的反例都变成可检查的证据 |

内部按完整对象名查找的 helper 仍用于发起上传时的放置逻辑，不能因为公开 API 不再使用它就一并删除。`mpCache` 的维护和节点间通知协议也保留，以避免额外扩大混合版本变更面；当前公开列表结果不再从这个缓存取数。这里有意保留少量兼容代码，后续清理不应混入功能修复。

主要影响未完成上传的发现、清理工具和运维盘点。标准 SDK 无需增加参数；调用方要遵守原有分页协议，不能假设一次拿齐，也要处理真实的扫描失败。已完成对象的列表与读取、上传数据格式、认证与授权规则不因此改变。空清单依然不能用于证明无身份历史上传已经排空。

### 已验证什么，仍缺什么证据 {#decision-evidence}

| 已完成的检查 | 支持的结论 | 不支持的更强结论 |
| --- | --- | --- |
| 新旧混合 HTTP 列表、prefix、delimiter、全局分页、已删除 marker、多 set/pool、按已知 ID 继续和完成旧上传 | 已界定的列表与历史兼容行为有自动化回归覆盖 | 并发遍历具有快照一致性 |
| 存储层重新打开，以及真实服务进程重启后用 boto3 与 PGSTY mcli 检查 | 新格式发现不依赖进程上传缓存；标准客户端流程可用 | 所有历史或第三方客户端均完成认证 |
| 身份缺失／损坏／矛盾副本、读 quorum、目录覆盖、扫描限流、取消后名额保留测试 | 不能确认的状态返回错误，不以局部页面冒充成功；资源保护有回归覆盖 | 永不超时、精确峰值内存上限或任意规模都可列举 |
| 默认 Abort 故障测试及迟到创建反例 | 默认可用性得到保留；已知竞争仍可被测试观察 | 迟到创建已被修复或 204 意味着物理排空 |
| 定向测试与 race 检查、带 `kqueue,dev` 标签的全仓库测试（51 个有测试的包）、`make verifiers`、构建 | 候选通过本地功能、竞态与项目检查 | 所有生产拓扑、负载和长期故障恢复均已验收 |
| 四／十六盘、1,000／10,000 上传的初版容量矩阵；追加身份一致性检查后重跑上表两个最终样例 | 有真实目录成本与预算超限证据；最终样例的数据可复现 | 完整矩阵已在最终修订逐项重跑，或生产前台负载不受影响 |

这些证据来自候选实现的本地检查，文档只提取可复核的结论，原始执行日志不作为产品文档发布。无身份历史例外、容量上限与迟到写入都是有意记录的边界，不因测试显示通过而自动消失。

### 升级方式与重新评估条件 {#decision-followup}

包含本次修复的版本发布后，按常规流程升级所有服务与写入节点，完成后重新开始分页遍历；不要求先排空历史上传。可以删除失效的 `MINIO_API_MULTIPART_LISTING`，不用设置替代变量。需要了解遗留情况时使用只读预检；`ready=false` 只是尚有历史记录或诊断不完整，不能理解为新列表未启用。

对已知身份的旧上传，继续、完成、取消和原有过期清理仍是处理路径。不能通过缩短过期时间来制造一个迁移截止日期，因为过期年龄按发起时间计算，会同时影响仍在进行的长上传。回退服务器会恢复旧版本的列表与开关行为；若目标构建拒绝曾持久化的 `api multipart_listing` 共享键，按历史章节的定向清理步骤核对，而不是重置整个 API 配置。

以下情况出现时，应重新评估本轮取舍：

- 产品需要列举所有历史上传、且不能容忍任何省略：需要权威身份恢复来源或明确的排空证明，不能靠重新命名开关来兑现。
- 支持规模超出扫描预算，单页延迟或前台上传影响不达标：用明确的磁盘数、桶分布、活跃上传数、并发分页与前台负载制定验收，再决定持久索引或其他发现结构。
- 产品要求取消成功后禁止任何迟到创建恢复上传：单独制定创建／取消屏障协议，包含离线副本、恢复和混合版本规则。
- 需要改变暂停 pool 的可见性或承诺完整回退到某个旧版本：分别补齐 pool 生命周期或指定版本的端到端兼容验收。

最终建议是保留这次明确的范围：让普通升级自动获得有身份上传的可靠列举，公开说明历史省略和扫描成本，把容量与取消屏障作为尚未完成的独立工作继续跟踪。不能把这份决策或候选提交当作 issue #79 已经全面收口的依据。

## 历史：9 月 16 日实现与升级契约 {#implementation-20260916}

> [!WARNING]
> **旧版分片列举设计已被覆盖 · Earlier multipart-listing designs superseded (2026-10-17)**
>
> **中文：** 本节的模式开关与排空启用方案已被[最新设计决策（中文）](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261017)覆盖，请参考新版。以下仅保留 Server 20260916 的历史契约；已安装旧版本仍按该契约运行。新设计已合入主干，尚未发布。
>
> **English:** This mode-switch and drain-before-enabling design is superseded by the [latest design decision (English)](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261017); use that record for the new design. The text below preserves the Server 20260916 contract, which still applies to those installed binaries. The new code is merged into main and remains unreleased.

[PR #198](https://github.com/pgsty/silo/pull/198) 保留 mr javad seydi 的原始元数据与扫描实现，并追加维护者对 marker 消失、发现覆盖不足、取消确认和升级诊断的修复。发布前的兼容性修复将默认模式恢复为 `legacy`，严格模式仅通过进程环境显式启用。本节说明这些源码变更。**Server 20260903 不包含此修复；源码实现也不代表生产性能与部署验收完成。** 下方 8 月 30 日的分析保留为历史设计记录。

### 列表与取消语义

新上传将 bucket 与原始对象键写入既有 `xl.meta`，完成时删除这些上传专用字段。严格列表跨 pool/set 发现持久上传，以既有读取 quorum 验证元数据，再全局处理 prefix、delimiter、`CommonPrefixes` 和最多 1,000 项的分页。节点重启或切换入口无需等待上传缓存重建。

排序为 `(key, 原生上传 ID 中的发起时间, 编码后的 upload ID)`。即使 marker 对应的上传已完成或取消，返回的 marker 仍然表示这个边界。该契约支持客户端回传服务端 marker，不承诺对随机上传 ID 做任意字典序比较。并发变更下，跨页遍历不是快照。没有 `key-marker` 时忽略 `upload-id-marker`；有 key marker 时，非法 base64 保留既有 404 行为，可解码但不支持的原生 ID 返回 400。不能解析的持久 ID 属于旧格式，不会用当前时间伪造发起时间。

每个 set 的目录枚举需要 `floor(N/2)+1` 块盘成功。例如四盘只有两盘可扫描时返回 503，即使两份元数据仍可读取。只有验证 bucket/key 与目录哈希一致后，单来源盘身份读取才能排除其他 bucket；不确定时升级为 quorum 读取。严格模式遇到旧格式返回 `MultipartListingNotReady`（503），身份不合法返回 `MultipartListingMetadataInvalid`（503），不会让整个请求悄悄退回缓存列表。

默认 `legacy` 模式下，Abort 保留已发布版本的读取 quorum、尽力清理和按 pool 顺序返回的行为，避免把原本可成功的取消变为 503。`strict` 模式检查每个相关 pool，删除需要 `floor(N/2)+1` 份确认，元数据已低于读取 quorum 的残片也可以重试清理。多数盘已不存在、但仍观察到残片时，必须成功清理这些已观察副本；空盘的成功不能掩盖残片盘的删除失败。未知 pool 或确认不足仍返回 503。

两种模式都不会因错 key 或错 bucket 的 Abort 清除另一个有效上传的缓存。S3 HTTP 层保留既有幂等行为：上传不存在也返回 204；格式错误、权限不足或 quorum 错误仍返回错误。**204 不是所有物理副本已删除的证明**，离线分片仍可能等待后续清理。

**尚未解决的创建写入边界：** 如果创建上传的物理写入在调用方收到存储超时后继续执行，以上确认不能阻止它迟到提交。故障注入已复现 16 盘/EC:8 场景：取消成功后，七份迟到写入加上七份离线旧副本，可以恢复出可继续写入的上传。测试保留了这个已知限制；测试通过不表示此问题已修复。持久创建屏障需要独立的存储一致性设计。

### 协调升级

**默认使用 `legacy`**，保留原有精确键与缓存列表限制。普通升级无需为了启用新列表而暂停生产或强制排空上传。模式只读取服务器进程环境变量 `MINIO_API_MULTIPART_LISTING=legacy|strict`，不新增共享配置项。未设置时采用 `legacy`；非法值会记录诊断并回退 `legacy`，其他 API 配置继续生效。不要使用 `mcli admin config set` 设置此模式。

只有准备启用严格模式时，才需要先升级**所有 writer**，停止产生旧格式上传，再使用已知 key/ID 完成或取消旧上传，执行以下只读预检，并验证扫描容量能够满足实际负载。通过后，在每台服务器的服务环境中设置 `MINIO_API_MULTIPART_LISTING=strict` 并重启；核对每个入口的生效模式。切换模式后应从头开始分页遍历。默认模式保留的列表缺陷仍由 issue #79 跟踪，本批不宣称完整修复。

如果曾运行写入 `api multipart_listing` 的开发版本：先备份配置并记录 API 设置，让所有配置写入者升级到修复版，停止并发配置写入，再只删除这个历史键：

```bash
mcli admin config reset ALIAS api multipart_listing
mcli admin config get ALIAS api
```

修复版会忽略历史键的模式值，但不会自动改写共享配置或删除历史记录。config get/export 会隐藏退役键，因此列表里看不到它不代表已经删除。应确认单项 reset 成功，重启后核对原有设置，并在受控回滚检查中验证旧版读取；不要重置整个 `api` 子系统。旧开发版本再次写入配置可能重新引入该键，带键的历史配置也不应直接回放。需要临时保护的 API 设置可按原值放入相应环境变量，但这不能替代持久配置清理。此步骤只处理本项 API 配置兼容性，其他变更的回滚条件仍需独立核对。

只读预检接口为 `GET /minio/admin/v3/multipart-preflight`，使用 SigV4 签名，要求 `admin:StorageInfo` 权限。例如，由操作者提供凭据与地址：

```bash
curl --aws-sigv4 'aws:amz:us-east-1:s3' \
  --user "$SILO_ACCESS_KEY:$SILO_SECRET_KEY" \
  "$SILO_ENDPOINT/minio/admin/v3/multipart-preflight"
```

报告包含 `mode`、`ready`、`complete`、`scannedEntries`、`legacyUploads`，以及各 pool/set 的盘覆盖、未覆盖盘序号与最老旧上传的发起时间。它绕过上传缓存，检查包括暂停 pool 在内的持久状态，并识别只剩少数副本的旧上传。`ready=true` 要求全部盘可检查、候选元数据没有不可读状态、且未发现旧格式副本。它无法证明所有 writer 都已升级，也不能阻止并发旧 writer 再引入旧格式。离线盘、扫描错误、超时和预算耗尽均不能报告就绪；不完整计数不能当作零。磁盘恢复后以及切换严格模式前应重新预检。

丢失原始 key/ID 的旧上传由既有 stale-upload 清理器处理，各服务器扫描自己的本地盘。年龄按创建时间计算，**不会被最近上传分片的活动刷新**。保留现有清理策略，等待并验证实际排空；默认 24 小时过期、6 小时清理间隔不等于排空保证。不能据此缩短过期时间催促普通升级，因为这也会删除仍在进行的长上传。无法排空时继续使用默认 `legacy` 模式。本批不改变清理规则，也不新增按任意路径删除的管理接口。

两种模式共用的 `maxUploadsList` 上限由 10,000 降至 1,000，依赖一次返回全部结果的客户端必须分页。

旧格式上传缺少 bucket/key 身份，无法安全地排除为其他桶，因此在 strict 模式下可能阻断任何桶的列表；已验证属于其他桶的新格式身份可提前过滤。不要把这个限制理解为 legacy 默认模式也会返回全局 503。

### 扫描容量与证据边界

每个进程最多同时接受两个扫描，每扫描使用 16 个身份读取 worker 和四个全盘元数据读取 worker。目录读取传递有限 count 并检测溢出。请求合计预算为 100,000 个返回的目录条目，包含不同盘上的重复条目和哈希目录，**不代表支持列出 100,000 个唯一上传**。合计超限时，其他并发目录请求可能已经发出；超限返回 `SlowDown`（503），不能返回成功的局部页面。30 秒 context 预算停止后续调度，扫描 worker 退出前仍占用并发名额。这不是精确内存上限，也不保证已进入系统调用的物理 I/O 立即停止。

仅作预算示例：一个 N 盘 set，每个唯一 key 有一个上传，所有盘都有相同两级目录时，每上传约消耗 `2 × N` 个条目，100,000 条目约对应 `100000 / (2 × N)` 个上传；N=16 时约 3,125。相同 key 的多个上传会分摊哈希目录成本，其他 set/pool、旧目录与超时也影响容量，因此这不是统一的上传数上限。

每一页仍需重扫持久状态，遍历成本随存储候选数与页数共同增长。测试覆盖 marker 消失、多 pool 覆盖、部分删除重试、身份读取回退、RPC 目录边界、取消后并发名额，以及已知迟到写入反例。临时多节点与维护客户端测试只证明记录环境中的功能行为；生产规模延迟和前台负载影响仍需按部署验收，源码合并不等于性能认证。

9 月 16 日的临时 Docker Desktop arm64 测试使用两节点、四个 APFS 绑定卷，两个 bucket 共 11,000 个上传，期间还有其他本地验证负载。目标 bucket 有 10,000 个上传，单次返回 1,000 项耗时 18.7 秒；两个并发请求约 25–27 秒后返回可重试的 `SlowDownRead`。这组观察没有达到暂定的单页五秒目标，也不是隔离的 SSD 基准。容量和前台负载验收仍未完成，不能把有界扫描宣传为大规模性能修复。

## 历史：8 月 30 日分析与提案 {#analysis-20260830}

> [!WARNING]
> **旧版分片列举设计已被覆盖 · Earlier multipart-listing designs superseded (2026-10-17)**
>
> **中文：** 以下早期分析、推荐方案和迁移门槛已被[最新设计决策（中文）](https://silo.pgsty.com/zh/blog/design/list-multipart-uploads/#decision-20261017)覆盖，请参考新版。这里保留原始思考供追溯；其中的方案编号、能力广播、排空估算和启用建议均不是本次主干实现的要求。
>
> **English:** The early proposals, recommendation and migration gates below are superseded by the [latest design decision (English)](https://silo.pgsty.com/blog/design/list-multipart-uploads/#decision-20261017). They remain only as historical reasoning; their option numbers, capability advertisement, drain estimate and enablement advice do not define the implementation now on main.

> **归档分析（2026-08-30）：** 以下“当前”“建议”、方案编号与门禁描述当时的审查和提案。待发布候选以 [10 月 17 日决策](#decision-20261017)为准；Server 20260916 以其[带日期的契约](#implementation-20260916)为准。旧提案中的 writer 升级／排空门槛不是本次候选的启用前提；能力广播、预计一天排空也只是当时提案，不是当前保证。

### 先用最简单的话说明问题 {#plain-language}

假设现在有四个大文件还没传完：

```text
tables/a/part-1
tables/a/part-2
tables/b/part-1
other/file
```

S3 客户端问：“把 `tables/` 下面所有没传完的上传列出来。”AWS S3 会返回前三个。SILO 目前却把 `tables/` 当成一个完整对象名，只查找是否存在一个名字恰好等于 `tables/` 的上传，于是返回空列表。

如果客户端去掉 prefix，要求列出整个存储桶里的所有未完成上传，SILO 又会走另一条捷径：读取当前进程里的内存缓存。创建这些上传的节点也许能看到四个结果，但缓存重启就消失，不同节点之间也不是权威一致的。上传数据仍然在磁盘上，只是列表说错了。

所以这不是“少支持了一个查询参数”那么简单。清理工具可能收到 `200 OK`，认定不存在未完成上传并报告成功，而磁盘上其实还有这些上传。服务端没有丢失已经提交的对象，但它向调用者展示了一个错误的未完成工作视图。

### 决策摘要 {#decision}

只要 SILO 仍希望宣称具有实用的 S3 兼容性，就应该修复这个行为。

修复的理由很明确：当前接口静默返回虚假的成功结果；重启或切换节点会改变答案；标准的 prefix 清理与分页流程无法工作。默认 24 小时的 stale-upload 清理器可以限制默认配置下的空间累积，却不能让 API 响应变得真实。

但这也不是一个小改动。现有上传目录只保存了 bucket 与 object key 的单向哈希，原始对象键没有写入 `xl.meta`。正确实现必须从新上传开始持久化这份身份信息，按纠删码 quorum 规则发现候选项，在所有 pool/set 之上统一执行 S3 语义，并处理滚动升级期间的 legacy 上传。

因此建议的方向是：

1. 把 bucket 与 object key 写进上传现有的 quorum 元数据；
2. 以有界的按需扫描作为持久化正确性路径；
3. 缓存只能是可重建的优化，不能是真相来源；
4. 只有所有 writer 都完成升级、无键 legacy 上传全部排空后，才能启用严格 S3 行为；
5. 只有测量证明扫描达不到产品批准的服务目标时，才考虑持久化二级索引。

### 问题描述与证据来源 {#sources}

本文的问题判断与方案建立在五类证据之上。

#### S3 正式契约 {#source-s3}

[AWS ListMultipartUploads API](https://docs.aws.amazon.com/AmazonS3/latest/API/API_ListMultipartUploads.html) 定义了通用存储桶的公开契约：

- `prefix` 选择所有 key 以该字符串开头的上传；
- `delimiter` 把匹配的 key 汇总成 `CommonPrefixes`；
- `max-uploads` 限制单页数量，文档规定上限为 1,000；
- `key-marker` 与 `upload-id-marker` 用来继续被截断的列表；
- 没有 `key-marker` 时必须忽略 `upload-id-marker`；
- 结果先按对象键排序，同一对象键的上传再按发起时间升序排列。

AWS 文档并没有无歧义地覆盖所有实现边角。同一时间戳、非法或越界的 `max-uploads`、URL 编码、marker 边界，以及 `CommonPrefixes` 如何占用分页名额，都应该在实现前对 AWS 做一次取证，并把结果保存成固定 fixture。

#### Issue 的原始报告 {#source-issue}

[Issue #79](https://github.com/pgsty/silo/issues/79) 提供了一个自包含、自己签名请求的复现程序，在 `pgsty/silo:latest` 上运行，并与 AWS、RustFS、SeaweedFS 和 Garage 比较。它的四个核心观察都可以复现：

| 请求 | 应有行为 | SILO 实际行为 |
| --- | --- | --- |
| `prefix=t/` | 返回三个以 `t/` 开头的 key | 一个上传也不返回 |
| `max-uploads=1` | 返回一项和续页 marker | 返回缓存中的全部上传 |
| `key-marker=t/a_b/p2` | 从这个 key 之后继续 | 返回缓存中的全部上传 |
| `prefix=t/&delimiter=/` | 返回汇总后的 `CommonPrefixes` | upload 与 prefix 都不返回 |

Issue 正确识别了兼容性失败，但“`max-uploads` 总是被忽略、`IsTruncated` 永远为 false”的表述覆盖面过大。这些结论在复现程序经过的无 prefix 缓存路径成立；精确对象路径能够处理 `max-uploads` 和 `upload-id-marker`，也能够设置 `IsTruncated`。

#### 上游设计历史 {#source-upstream}

这个行为是继承来的，并非 SILO 独自发明：

- MinIO 在 2017 年通过 [PR #5248](https://github.com/minio/minio/pull/5248) 有意删除纠删码后端的 prefix listing，理由是“简化” multipart 支持；
- MinIO 在 2024 年通过 [PR #20407](https://github.com/minio/minio/pull/20407) 增加了无 prefix multipart 缓存，主要为了满足 Alluxio 测试；
- 2025 年报告相同 exact-key 行为的 [MinIO Issue #20989](https://github.com/minio/minio/issues/20989) 被以 working as intended 关闭；
- SILO 当前的 [S3 兼容性参考](/zh/reference/s3-api-compatibility/#id5) 已经记录“必须使用精确对象名”的差异，但在本文之前没有解释缓存、分页、marker、delimiter 与重启限制。

这些历史可以解释代码为什么是有意如此，却不能让接口符合 AWS 契约。

#### 源码审查 {#source-code}

当前源码存在两条互斥的 listing 路径：

```text
erasureServerPools.ListMultipartUploads
  prefix == ""  -> 返回节点本地 mpCache 中的条目
  prefix != ""  -> 把 prefix 当成完整对象键做哈希
                    -> 只选择一个 set
                    -> 只列一个 sha256(bucket/object) 目录
```

关键位置包括：

- [`cmd/erasure-server-pool.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-server-pool.go)：无 prefix 的 `mpCache`、逐 pool 拼接，以及 `NewMultipartUpload` 内部使用的精确对象查询；
- [`cmd/erasure-multipart.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-multipart.go)：精确对象 listing、上传目录构造、stale-upload 清理，以及新上传 `xl.meta` 的 quorum 写入；
- [`cmd/erasure-sets.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/erasure-sets.go)：把传入的对象名哈希到单个 erasure set；
- [`cmd/bucket-handlers.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/bucket-handlers.go)：公开请求校验，其中包括 `key-marker` 不属于 prefix 时返回 `501 NotImplemented` 的保护；
- [`cmd/object-api-multipart_test.go`](https://github.com/pgsty/silo/blob/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca/cmd/object-api-multipart_test.go)：虽然有大型期望结果表，但最后的断言只检查回显的标量，没有验证 uploads、prefixes、markers 或截断状态。

#### 独立复现与对抗性审查 {#source-review}

审查者用单节点服务和 SigV4 请求，在被审查的 SILO 源码上独立复现了 Issue 场景。额外探针确认：

- 精确对象键能够给该对象自己的多个上传分页；
- 当前精确键路径即使没有 `key-marker` 也会使用 `upload-id-marker`，与 AWS 不符；
- 精确键被截断时，`NextKeyMarker` 仍为空；
- 当前路径把 `max-uploads=0` 当成无限制；
- 普通服务重启会让 bucket-wide 视图变空，而精确键查询仍能找到磁盘上的上传。

第二轮对抗性架构审查进一步挑战了存储、quorum、迁移、suspended pool、混合版本与性能假设。相关修正已经进入下文；本文不会把 AI 审查当作代码测试或 AWS 兼容性取证的替代品。

### 当前代码到底做了什么 {#current-behavior}

#### 空 prefix：易失的节点本地视图 {#empty-prefix}

没有 prefix 时，pool 层从 `mpCache` 返回该 bucket 的全部 `MultipartInfo`，并且只按发起时间排序。它不应用 `max-uploads`、`key-marker`、`upload-id-marker` 或 `delimiter`，也不计算续页 marker 或 `IsTruncated`。

进程启动时缓存为空。创建上传只填充处理该请求的节点。完成和中止会删除缓存项，部分路径还会通知 peer 删除，但创建没有等价的持久化集群广播，也没有启动重建。因此：

- 重启可以让非空列表变成空列表；
- 两个节点可以对同一存储桶返回不同答案；
- 成功响应不能证明服务端已经枚举了持久化上传状态。

#### 非空 prefix：精确对象查询 {#nonempty-prefix}

存在非空 prefix 时，这个字符串会像完整对象名一样进入对象哈希。系统选择一个 erasure set，然后读取由 `sha256(bucket/object)` 派生的目录。

这条路径可以枚举同一精确对象的多个 upload ID。它按发起时间排序，应用自己的 `upload-id-marker`，在 `max-uploads` 处停止并设置 `IsTruncated`。但它仍然没有实现词法 prefix 匹配、`CommonPrefixes`、通用 key-marker 语义或 `NextKeyMarker`。

#### 多 pool 让分页更加不正确 {#multiple-pools}

多 pool 部署收到非空请求时，pool 层会用相同上限分别调用每个活动 pool，然后直接拼接结果。它不会做全局有序归并，也不会重新计算分页边界和 next markers。请求 `N` 个结果时，可能从每个 pool 各取 `N` 个。

Listing 与其他公开 multipart 动词都会跳过 suspended pool。因此，留在 suspended 或 decommissioning pool 上的未完成上传不只是“没有列出来”，而是完全无法访问。这是相关的生命周期缺陷，但 listing 不能单独展示 `PutObjectPart`、`ListParts`、`CompleteMultipartUpload` 和 `AbortMultipartUpload` 都无法操作的句柄。pool drain 或强制 abort 应当作为覆盖所有动词的独立设计。

### 为什么现有上传无法回填 {#no-backfill}

Multipart 命名空间是平的：

```text
.minio.sys/multipart/<sha256(bucket/object)>/<upload-id>/xl.meta
```

哈希是单向的，路径里没有原始 bucket 和 key。当前 multipart `xl.meta` 里也没有保存名称字段；传入的对象名只在 `newFileInfo` 构造过程中影响 erasure distribution。

因此，全目录扫描可以知道“这里有一个上传”，却无法知道它属于哪个 bucket 或 key。当前节点本地缓存也无法可靠修复这件事，因为它跨节点不完整，重启后还会消失。

这否决了一个很诱人的“小修复”：扫描所有现有 `xl.meta` 再应用 prefix 过滤。系统必须为新上传增加可恢复的身份元数据或持久化索引，同时为旧的 keyless 上传制定明确迁移策略。

### 复杂度评估 {#complexity}

纯语义算法不是最难的部分。真正困难的是：如何在不把一次 listing 变成失控的全集群元数据风暴的前提下，得到完整、满足 quorum、能够全局排序的输入集合。

| 领域 | 复杂度 | 原因 |
| --- | --- | --- |
| 纯 S3 过滤与分页 | 中 | 规则数量有限，但 marker 和 delimiter 边角需要 AWS 取证。 |
| 把 bucket/key 写入新上传元数据 | 中 | 复用现有 quorum 写入，但要验证完成、回退、healing 与复制兼容性。 |
| 候选发现 | 高 | 命名空间混合所有 bucket，并且每个上传在 erasure drives 上重复；只查一块盘会漏掉仍满足 quorum 的上传。 |
| Quorum 与并发删除 | 高 | 扫描既要拒绝少数盘残留的幽灵项，又要容忍 abort、complete、GC rename-to-trash 与瞬时 `ENOENT`。 |
| 多 pool 全局分页 | 高 | 必须在所有可访问 pool/set 之上统一归并、排序、截断并生成 marker。 |
| 滚动迁移 | 高 | 旧 writer 会继续创建 keyless 上传，旧 completer 可能保留未知内部元数据。 |
| 性能与资源控制 | 高 | 一个 bucket 请求可能需要检查全集群的所有活动上传，而不只是该 bucket。 |

总体判断：这是一个高复杂度兼容性项目，wire 兼容风险为中，正确实现的风险为高。它不是破坏性的对象格式迁移：推荐方案只给新的未完成上传增加内部元数据，并保持现有目录结构不变。

### 兼容性与运维影响 {#impact}

#### Wire 行为变化 {#wire-impact}

正确实现会有意改变外部可见结果：

- `prefix=foo` 将匹配 `foo`、`foobar` 与 `foo/...`，不再只匹配精确键 `foo`；
- bucket-wide 结果将按 key 与发起时间排序，而不是只按发起时间；
- `max-uploads` 会真正限制单页；
- 默认值与最大值会从 SILO 当前的 10,000 常量向 AWS 的 1,000 收敛，具体边角以取证契约为准；
- 客户端必须跟随 `NextKeyMarker` 和 `NextUploadIdMarker`，不能再假设一个响应包含全部结果；
- delimiter 请求会返回 `CommonPrefixes`；
- 当前 handler 在 marker 不属于 prefix 时返回的 `501`，将被取证后的 AWS 语义替代。

这些是兼容性修复，但可能破坏意外依赖 SILO 旧行为的软件。特别是忽略分页的客户端，修复后可能只看到更少的首屏结果。因此严格行为应通过明确的发布和 rollout 契约引入，不能偷偷混进一个无关 patch。

#### 存储格式兼容性 {#storage-impact}

推荐写路径是在新上传现有的 quorum `xl.meta` 中加入保留的内部 bucket 与 object key 元数据。它不重命名 multipart 目录，也不创建第二个事务写入位置。

在 `CompleteMultipartUpload` 把上传元数据 rename 成最终对象之前，必须删除这些只属于上传的字段，位置与当前已经删除 multipart checksum 字段的逻辑相同。

旧二进制完成由新二进制创建的上传时，不知道要删除新内部键。这些键不会暴露成 S3 用户元数据，但会惰性地留在已完成对象的内部元数据中。滚动升级测试必须证明未知保留键不会影响 healing、复制、元数据比较或降级读取。随后产品需要在“容忍残留”和“增加 scrubber”之间选择，不能假设它会自动消失。

#### 运维成本 {#operational-impact}

因为所有 bucket 共用同一个平坦哈希命名空间，按需扫描的复杂度是 `O(全体活动 multipart uploads)`，而不是 `O(目标 bucket 的 uploads)`。有界并行、取消、内存限制与失败行为属于正确性要求，不是可有可无的调优。

SILO 默认在 24 小时后过期 stale multipart upload，每 6 小时清理一次。最后一个旧 writer 升级后，keyless population 在通常情况下应当在大约 30 小时内排空。配置了更大自定义 expiry 的运维方会有更长迁移窗口。当前代码把零值映射回默认 24 小时，本次审查没有找到受支持的“禁用 expiry”取值。

清理器能限制默认空间累积，却不能修复虚假的 listing 响应，也不能替代对持续合法 multipart 活动、故障模式和自定义 expiry 的测试。

#### 严重度 {#severity}

建议定级为 **P1 / 高兼容性问题**，而不是 P0：

- 没有发现已经提交的对象数据丢失；
- 没有绕过安全边界；
- 未完成上传在 complete、abort 或被清理前仍在磁盘上；
- 默认 stale-upload 清理可以限制普通配置下的累积。

之所以仍然是高而不是中，是因为服务端返回了伪造的成功结果，答案会在重启或切换节点后变化，并且会让清理与静默期检查工具产生错误信心。

### 候选方案 {#options}

#### 方案 0：保持现状 {#option-zero}

没有工程成本，也保留所有偶然行为；同时继续保留虚假的 `200 OK`、节点本地不一致、重启易失、prefix 清理失败，以及对 S3 支持范围不准确的印象。

只有当 SILO 明确降低公开兼容性承诺、把该接口视为不支持时，这个选择才勉强成立。即便如此，明确拒绝也优于静默返回不完整成功。

**决策：不能作为长期方案。**

#### 方案 1：明确且有文档的差异 {#option-divergence}

对 SILO 无法正确处理的参数组合返回稳定的 `NotImplemented` 类错误，并准确记录支持子集。这比完整兼容小得多，也在运维上更诚实。

它仍然是破坏性行为变化：现在拿到空列表或无界 `200 OK` 的工具可能会开始让作业失败；它也没有得到一个 S3 兼容接口。错误行为和默认发布策略必须有意识地确定。

**决策：如果完整兼容被拒绝或推迟，可以作为短期止血；它不是兼容性修复。**

#### 方案 2：持久化身份、扫描持久状态、可选缓存 {#option-scan}

每次创建新上传时，把 bucket 与 key 写入上传现有 `xl.meta` 的保留内部元数据。Listing 时遍历可访问 pool/set 的上传目录，按 erasure read quorum 验证候选，再执行一个全局 S3 语义层。缓存只有在能够从持久化状态重建和对账时才允许加速这条路径。

它不增加第二个写事务，也不改变目录布局。主要代价是全集群扫描。

**决策：推荐，但必须先通过性能与故障模式原型。**

#### 方案 3：持久化的 bucket 级有序索引 {#option-index}

维护一个按 bucket、key 与 upload identity 排序的二级索引。Listing 可扩展且天然支持分页，但 create、complete、abort、healing、回退与 reconciliation 必须在各种失败下维持两个位置的一致性。这个设计类似 MinIO 在简化该子系统时有意移除的 multipart 索引结构。

**决策：除非测量证明方案 2 无法满足产品批准的服务目标，否则 NO-GO。**

#### 被否决的变体：只修 `mpCache` {#option-cache-only}

给当前缓存增加过滤、排序、分页、create 广播或启动重建可以改善表象，却不能单独建立一个持久化、满足 quorum 的真相来源。只修缓存很可能得到一个“看起来更可信、实质仍不正确”的答案。

**决策：否决。缓存可以优化正确读路径，不能定义它。**

### 推荐设计 {#recommended-design}

#### 1. 先冻结公开契约 {#contract-first}

为通用存储桶建立一套有记录的 AWS fixture，覆盖：

- 跨 key 排序，以及同 key 多个上传的排序；
- 相同发起时间与确定性的全序 tie-break；
- prefix 与 exact-key 重叠；
- key-marker 单独使用和配合 upload-id-marker；
- 没有 key-marker 时的 upload-id-marker；
- delimiter、`CommonPrefixes` 与分页计数；
- 省略、0、1、1,000 和大于 1,000 的 `max-uploads`；
- `encoding-type=url`；
- 空页、末页与 next-marker 的取值。

把取证响应保存成仓库 fixture，CI 不应依赖实时 AWS 访问。

#### 2. 在现有写入中持久化可恢复身份 {#write-path}

在 `NewMultipartUpload` 中，在现有 `writeAllMetadata` quorum 写入之前，为规范化 bucket 与 object key 增加保留内部元数据。具体键名属于实现细节，但必须带版本、无歧义、受现有 object-key 大小限制约束，并且不能暴露到客户端元数据。

成功完成时，在把 `fi.Metadata` 复制到最终对象元数据、执行 `renameData` 之前删除这些 upload-only 键。Abort 与 stale cleanup 已经删除整个上传目录，不需要额外索引操作。

#### 3. 分开“发现候选”与“验证有效” {#read-path}

候选发现和候选有效性是两个不同问题。

对于每个可访问、非 suspended 的 pool 与 set：

1. 按配置的 list-quorum 策略，从所需的所有在线盘列出 hash 与 upload 候选目录；
2. 对目录名做 union 和去重；
3. 通过正常 erasure 元数据路径读取候选 `xl.meta`；
4. 只有元数据满足 quorum 且包含合法 bucket/key identity 时才纳入结果；
5. 容忍候选在 abort、complete 或 stale cleanup 过程中消失；
6. strict list quorum 下，如果所需 set 无法评估，应让请求失败，而不是返回部分成功的 `200 OK`。

只用第一块健康盘做候选发现是不够的：那块盘可能在一个仍满足 quorum 的上传创建时处于离线状态。

#### 4. 只做一次全局语义处理 {#semantic-layer}

把所有 pool/set 的有效候选送进一个纯语义层。它统一负责 bucket 过滤、prefix、delimiter 汇总、排序、markers、最大页计数、URL encoding、`IsTruncated` 与 next markers。

在全局归并前不能应用 pool-local limit 和 marker。相同候选被重复发现时结果必须确定，而且无论请求落到哪个节点都应该得到同一答案。

#### 5. 保留内部精确对象操作 {#exact-helper}

`erasureServerPools.NewMultipartUpload` 当前调用 `ListMultipartUploads(bucket, object, ...)`，目的是让同一对象的另一个上传进入相同 pool。如果公开函数开始把参数解释为词法 prefix，`foo` 可能匹配 `foobar` 并选错 pool。

增加一个命名收敛的内部 helper，例如 `FindMultipartUploadPool` 或 `ListMultipartUploadsExact`。它应继续使用现有对象哈希路径，不能共享公开 prefix 语义。

#### 6. 缓存只能是优化 {#cache}

可以直接删除现有 `mpCache`。如果保留，它必须满足：

- 持久化状态始终是权威；
- 启动时能够重建；
- create、complete 与 abort 更新能够一致传播；
- reconciliation 能发现漏掉的事件与过期条目；
- 冷缓存或分歧缓存会回退到 quorum 扫描；
- 关闭缓存时所有 correctness 测试仍然通过。

#### 7. 通过滚动迁移门槛启用严格行为 {#migration}

Legacy 上传记录缺少 bucket/key identity，无法可靠反推。使用两个对外有意义的模式：

- **legacy mode**，升级后的初始默认：新 writer 持久化身份；统计并排空 keyless 上传；混合 keyed/keyless population 的响应策略必须明确选择；
- **strict mode**：只有所有 writer 节点都声明支持新元数据、观测到的 keyless count 为零时才能启用。此后重新发现 keyless 上传必须报错并产生异常遥测，不能静默遗漏。

短期 shadow 对比可以验证新 scanner，但除非原型发现必要性，否则不需要永久的第三种运行模式。在默认 expiry 下，最后一个旧 writer 停止后，预计用一天再加一个清理周期排空 legacy。

Legacy mode 仍有一个未决产品选择：

| 策略 | 优点 | 代价 |
| --- | --- | --- |
| 返回完整的 keyed 子集，并用文档和遥测说明 | 有界排空期间工具仍可运行 | 普通客户端看不到“不完整”事实，仍会收到不完整 `200 OK` |
| 只要存在 keyless 上传就让 listing 失败 | 永远不伪造完整性 | 整个排空窗口会阻塞清理和现有作业 |

这个选择必须写进 ADR。Strict mode 没有这种歧义：前提被破坏时必须显式失败。

#### 8. 把 suspended-pool 生命周期拆开处理 {#suspended-pools}

Listing 的第一版应与其他 multipart 动词的可访问性契约一致，只扫描非 suspended pool。单独把 suspended-pool 条目加入 listing，会暴露无法继续上传、完成或中止的句柄。

为 pool drain 期间的未完成上传另开生命周期设计：可以在上传结束前保持全部 multipart 动词可用、迁移上传，或按文档策略强制 abort。不要把它偷偷塞进 #79。

### 性能原型与决策规则 {#spike}

方案 2 只有一个持久写入位置，因此是首选；但它的扫描成本必须测量，不能假设。

在不同 pool、set 与 drive 数量组合下生成 1,000、10,000 与 100,000 个活动上传，测量：

- 冷热状态下的 p50/p95/p99 延迟；
- 总体与逐盘 `ListDir` 操作数；
- 元数据读取和节点间 RPC 数；
- 峰值内存与分配量；
- 取消延迟；
- 慢盘、离线盘、healing 与间歇消失磁盘下的行为；
- 同时发生 create、complete、abort 与 stale cleanup；
- 高选择性 prefix、空 prefix、首页与深页成本。

验收阈值是产品决策，必须在解释结果前记录。猜测的一两秒目标不是证据。如果扫描能在有界资源下满足批准的目标，就否决方案 3；如果不能，就用测量结果设计解决已证明瓶颈的最小持久化索引。

### 测试与发布关卡 {#gates}

#### 语义与单元测试 {#unit-tests}

- 根据记录的 AWS fixture 生成纯表格测试；
- 覆盖排序、marker、delimiter、encoding、截断与 maximum 边角；
- 用属性测试保证分页后每个逻辑上传恰好出现一次；
- 重复候选和相同时间戳下保持确定性。

#### Object 与 handler 测试 {#handler-tests}

- 强化现有 object-layer 表格，断言 uploads、common prefixes、markers 与截断；
- 解析并验证 handler XML body，而不是只检查状态码；
- 验证默认和非法 `max-uploads`；
- 独立测试 exact helper 的 pool 选择，不与公开 prefix 语义混用。

#### 分布式与故障测试 {#failure-tests}

- 重启等价性与切换节点等价性；
- 多 set、多 pool 下只有一个全局页边界；
- 候选在一块盘缺失但整体满足 quorum；
- 部分 abort 后少数盘残留的幽灵条目；
- 并发 complete 与 GC rename-to-trash；
- 每种受支持 `list_quorum` 策略下的 set 不可用；
- 滚动升级、旧 writer 重新加入、降级 complete 与 strict mode 门槛；
- healing 与 replication 对未知内部元数据的处理。

#### 交付关卡 {#delivery-gates}

1. 批准 ADR，包括产品模式与性能 SLO；
2. 提交兼容性 fixture；
3. 完成并评审存储原型；
4. 实现并通过定向、全量、race 与故障 QA；
5. 更新 S3 兼容性参考与运维说明；
6. 提交并合并源码变更；
7. 构建并标识 release artifact 或容器镜像；
8. 对滚动升级做 canary，观察 keyless-drain 遥测；
9. 只有所有门槛满足时才启用 strict mode；
10. 验证线上端点后再关闭 #79。

前一个关卡通过，不代表后一个关卡已经发生。

### 最终建议：应该改，但不能急着改 {#final-recommendation}

无限期保留当前接口是错误的权衡。这不是一个冷门响应字段不一致：它影响未完成数据的发现与清理，返回成功但错误的答案，而且会随节点与重启变化。这些性质损害了 S3 兼容性在实践中的含义。

但直接写一个实现补丁同样是错误的权衡。当前磁盘布局无法识别 legacy 上传；正确扫描必须具备 erasure-aware discovery 与 quorum；wire-correct 分页又会改变客户端可见行为。

平衡后的决策是：

- **GO**：ADR、AWS fixture 取证、metadata-plus-scan 原型，以及性能/故障原型；
- **有条件 GO**：产品 SLO 与 legacy 响应策略批准后采用方案 2；
- **NO-GO**：只修缓存、立刻引入持久化二级索引、在 patch release 中默认 strict，或在证明滚动升级门槛可达之前关闭 Issue；
- 如果没有实现资源，**GO**：采用明确、有文档、稳定报错的差异行为，而不是继续伪造成功 listing。

这样既守住兼容性纪律，也不会假装一个高风险的分布式 listing 变更只是两行 bug fix。
