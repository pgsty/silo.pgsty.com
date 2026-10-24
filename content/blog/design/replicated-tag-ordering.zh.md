---
title: "复制标签排序：修订时间戳、墓碑与复活"
linkTitle: "复制标签排序"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: >
  PR #193 与 #196 合入的复制标签修复决策记录：SSE-KMS 目的端复制静默丢弃标签修订时间戳；空标签值没有可表达的修订，迟到的事件可以复活已删除的标签。涵盖墓碑语义、存量胜的平局变化、双端升级要求，以及 resync 期间额外元数据复制的成本。
tags: [设计, 复制, S3, 评审]
weight: 8
draft: false
url: "/zh/blog/design/replicated-tag-ordering/"
---

随 [SILO Server 20260916](/zh/blog/release/silo-20260916/)（`40220bd836cbd066ca424fa4dc5dbb90057fb55a`）发布的 [PR #193](https://github.com/pgsty/silo/pull/193)（修复提交 [`03027727d`](https://github.com/pgsty/silo/commit/03027727d)）与 [PR #196](https://github.com/pgsty/silo/pull/196)（修复提交 [`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)），修复了对象标签在跨桶复制中保持顺序的两项缺陷：SSE-KMS 目的端复制静默丢弃标签修订时间戳（`R4`），以及空标签值（删除操作）缺失修订时间戳导致延迟到达的复制事件将已删除标签“复活”（`R5`）。

## 共同模型：标签值与其修订时间戳共同构成单一状态 {#model}

对象标签在复制时通过请求头 `X-Minio-Source-Tagging-Timestamp` 传递内部修订时间戳（在 `xl.meta` 中存储为 `x-minio-internal-tagging-timestamp`）。接收端在对象写锁保护下通过 `reconcileStoredObjectTags` 执行排序规则：入站复制的标签状态仅在其修订时间戳**严格新于**目标端已存时间戳时才胜出。

本组两项缺陷均以“丢失修订时间戳而非丢失标签值”的方式破坏了这一规则：

- **R4（[PR #193](https://github.com/pgsty/silo/pull/193)）：** 在写入 SSE-KMS 加密目标端时丢弃了入站时间戳，导致较新的标签更新在存储层对账中输给陈旧的已存状态。
- **R5（[PR #196](https://github.com/pgsty/silo/pull/196)）：** 使空标签值（即删除标签）完全不携带修订时间戳，导致复制协议无法表达“在时刻 $T$ 已删除标签”——网络中迟到的旧复制事件因此能够重新恢复客户端早已删除的标签。

## R4：SSE-KMS 目的端复制丢弃标签修订时间戳 {#r4}

**故障形态：** 发往 SSE-KMS 加密目的端的可信复制 `COPY` 请求返回 HTTP `200 OK`，对象密文加密正确，明文 `GET` 读取也完全正常——但目的端对象的标签及其时间戳却停留在旧值。由于 HTTP 请求返回成功，不会触发任何告警或 MRF 重试。存储层对账函数 `reconcileStoredObjectTags` 在对象写锁内比较修订时间戳时，因入站时间戳丢失而直接判定存量旧状态获胜。

**触发范围：** 不仅限于携带显式 SSE-KMS 请求头的调用；当目的端桶配置了桶级默认 KMS 加密或集群开启了全局自动加密时，均会进入同一代码分支，因此即便请求中不含任何 KMS 请求头也会触发该缺陷。

**根因追溯：** `PUT` 类请求的选项构造函数在解析出可信来源标签时间戳并存入 `ObjectOptions` 后，SSE-KMS 分支重新构造并返回了另一个 `ObjectOptions` 结构体字面量——该字面量复制了 `MTime`、`ETag`、复制信任标志与两个 Object Lock 时间戳，唯独漏掉了 `ReplicationSourceTaggingTimestamp`。这一遗漏最早可追溯至上游提交 `c4373ef290`（2021 年）；2026 年初的一次 Object Lock 修复向该结构体字面量补齐了两个保留期/法务锁定时间戳，但依然漏掉了标签时间戳。

**修复（[`03027727d`](https://github.com/pgsty/silo/commit/03027727d)）：** 在 SSE-KMS `ObjectOptions` 字面量中补齐 `ReplicationSourceTaggingTimestamp` 字段传递。回归测试覆盖了全部目的端加密方式（无加密、SSE-S3、带与不带 key context 的 SSE-KMS、SSE-C）$\times$ 可信/不可信来源 $\times$ 缺失/有效/畸形时间戳的完整组合矩阵，以及在单盘和 16 盘纠删码后端上以 1–3 纳秒间隔执行的 50 次有序签名 `COPY`+`GET` 循环验证。

*相近代码观察：* 同一个 SSE-KMS `ObjectOptions` 字面量还遗漏了 `ProxyRequest` 与 `Speedtest` 选项字段（全局自动加密下 `speedtest PUT` 会丢失该标志），该问题作为独立跟进项单独记录，不混入本次复制修复。

## R5：空标签值无修订时间戳，导致已删标签被延迟事件复活 {#r5}

**故障形态：** 基线测试在真实存储与函数级测试中暴露出 9 项具体回归表现：

1. 成功的 `DeleteObjectTagging` 从不生成新的修订时间戳，因此迟到的可信元数据 `COPY` 只需携带旧标签快照即可将已删标签重新写回。
2. 携带空标签状态的较新 `COPY` 被接收端忽略——空字符串被解释为“未提供标签变更”而非“已清空标签”。
3. 首次副本 `PUT` 虽然解析了来源标签时间戳，却未将其持久化写入磁盘元数据。
4. 当源端与目标端可见标签值相等（或均为空）时，发送端将其折叠为“无需复制”；由于 `HEAD` 响应不暴露内部标签修订时间戳，更新的删除或重加操作不可见，无法恢复正确顺序。
5. 排队中的复制事件在完成回调时会将快照中的旧标签写回本地元数据，直接覆盖已提交的删除操作——且在无时间戳保护下，复活的旧标签还会继承删除操作的较新修订状态。

**根因：** 标签值与其修订时间戳（包括空值的时间戳）共同构成一个完整状态。旧协议只能表达非空状态：`DeleteObjectTagging` 从不生成修订时间戳、发送端仅在非空分支附带时间戳、接收端也仅在非空分支执行对账判断。

**修复（[`680eac66e`](https://github.com/pgsty/silo/commit/680eac66e)）：**

1. **每次标签变更均生成单调递增修订：** `PutObjectTagging` 与 `DeleteObjectTagging` 处理器无条件生成单一的 UTC `RFC3339Nano` 修订时间戳，无论该对象当前是否命中复制规则。存储层在写锁内强制保证单调性：若新生成的本地修订不严格新于已存修订，则将其推进至 $\text{stored} + 1\text{ ns}$；多池后端则跨所有存储池计算出严格大于全部池副本的统一修订值。
2. **发送端传输删除墓碑（tombstone）：** 空标签值同样携带其已记录的修订时间戳；对于从未设置过标签的对象（空值且无修订记录）绝不伪造时间戳；若磁盘上已记录的时间戳格式畸形，则按失败关闭（fail-closed）处理，不作静默修补。
3. **接收端对账墓碑状态：** 复制 `COPY` 在重建元数据前先捕获存量标签与时间戳对，使带时间戳的空值作为可胜出的有效状态进入 `reconcileStoredObjectTags`。内部重复版本抑制（`412 PreconditionFailed`）仅对严格更新的可信来源标签修订放宽（客户端显式指定的 `If-Match` 与 `If-None-Match` 依然严格执行）。多段上传完成（`CompleteMultipartUpload`）从已持久化的 upload 元数据读取标签顺序；复制删除确认回调不再将快照标签写回本地；普通 SSE-C 密钥轮换则会从复制的加密元数据中剥离旧标签时间戳，防止其覆盖新生成的本地修订。

### 运维可见变化与升级要求

- **时间戳相等时统一判定存量胜出：** 在不带版本（unqualified）及显式 `null` 版本的 `COPY` 请求上，当入站时间戳与已存时间戳相等时统一保留存量状态（旧逻辑在未限定版本路径上曾让入站请求胜出平局）。
- **携带 `X-Amz-Tagging-Directive: REPLACE` 且无标签的普通 `COPY`：** 现在会按 S3 规范真正清空目的端标签，而不再沿用旧默认路径将源对象标签复制过去。
- **复制两端必须协同升级：** 旧版本对端仍会丢弃空值修订头，新发送端发出的删除墓碑对旧接收端不可见（关于同步包含的 IAM 变更，请参阅 [IAM 与复制升级指南](/zh/operations/replication/iam-upgrade/)）。
- **显式 resync/heal 期间每个带修订记录的对象增加一次元数据 `COPY`：** 当目的端配置了桶级默认 KMS 或全局自动 KMS 加密时，该元数据 `COPY` 会实际重写对象数据，执行大批量重同步时需据此评估 I/O 预算。
- **固有边界：** 历史已丢失或被覆盖的删除时间戳无法自动重建，需从权威源端发起一次新的显式标签写入以重新收敛；带标签过滤条件的复制规则仍按删除后的（空）标签状态评估目标资格；跨站点逐跳排序依赖站点间的时钟同步（NTP），畸形的已记录时间戳会使发送端构造持续失败并经由 MRF 重试，直至被新的合法标签变更替换。

## 评估并否决的候选方案 {#rejected}

- **为空值且无修订记录的对象从 `ModTime` 合成墓碑：** 会使每个从未打过标签的普通对象都获得标签修订，叠加显式同步时的强制元数据复制后，会导致每个对象在每一跳都触发额外的元数据 `COPY`。
- **仅在标签值为空时传输修订时间戳：** 提案者在代码评审中撤回了该方案——在“时刻 $T_1$ 设为 `X` $\to$ 时刻 $T_2$ 删除 $\to$ 时刻 $T_3$ 重新设为相同值 `X`”的序列下，若非空时省略时间戳会丢失 $T_3$ 的重加修订（已由回归测试 `TestTaggingRepeatedValueNeedsRevisionDelivery` 固定该反例）。
- **扩展 `HEAD` 协议返回内部标签修订：** 当前固定的 `minio-go` 元数据提取器会丢弃内部响应头，修改协议契约收益有限，且当修订不同时最坏情况仍需执行一次元数据 `COPY`。
- **引入分布式因果时钟或在底层提交时重新生成时间戳：** 墙钟时间戳配合写锁内的 $+1\text{ ns}$ 单调护栏已是无需修改存储格式的最小正确修复。
- **仅做单池内的单调护栏：** 普通读取仅返回单池对象信息，若只在单池内维护单调性，发送端可能发出落后于其他存储池的旧修订；因此必须跨池计算统一的最高修订值。

## 验证 {#verification}

`R4` 回归测试覆盖了加密模式 $\times$ 信任状态 $\times$ 时间戳矩阵，以及单盘与 16 盘纠删码后端上的有序序列；`R5` 额外包含多存储池标签删除回归测试，[PR #196](https://github.com/pgsty/silo/pull/196) 的全部 11 项 CI 检查均已通过。

升级摘要见[组件版本矩阵](/zh/compatibility/versions/#september-reliability)；阻止归一化副本元数据被重新注入的姊妹修复见[副本元数据归一化](/zh/blog/design/replica-metadata-normalization/)。相关设计记录：[复制标签排序](/zh/blog/design/replicated-tag-ordering/) · [副本元数据归一化](/zh/blog/design/replica-metadata-normalization/) · [请求头超时防护](/zh/blog/design/request-header-timeouts/) · [副本元数据审计手册](/zh/operations/replication/replica-metadata-audit/)。
