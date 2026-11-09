---
title: "多池生命周期过期：按整个对象决策"
linkTitle: "多池生命周期过期"
date: 2026-11-04
lastmod: 2026-11-09
author: "PGSTY SILO 维护团队"
summary: >
  解释生命周期规则只按单个池内的版本求值时，为何会隐藏、删除或复活另一个池中的版本，以及为什么在对象锁内按合并后的版本列表复核，是最小而完整的修复。
tags: [设计, 生命周期, 存储池, 数据安全]
weight: 10
draft: false
url: "/zh/blog/design/multi-pool-lifecycle-expiry/"
---

本文覆盖 [issue #278](https://github.com/pgsty/silo/issues/278) 和 Denis Babchuk 提交的 [PR #279](https://github.com/pgsty/silo/pull/279)，基于 main [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) 评估。修复将通过维护者集成 PR 合入：贡献者提交原样保留，并附加下文所述的维护者后续修正。恢复副本过期的修复（[#281](https://github.com/pgsty/silo/issues/281)）在同一个集成 PR 中交付，另有单独记录。

**状态：** 修复的第一版通过了两轮维护者审查。随后对抗性审查要求修改，即[修复方案](#fix)中的第 6–9 部分。实现这些修改的补丁经过四轮审查后获得批准。它已和下个版本的其他修复放在同一个集成分支上一起测试：带 `kqueue,dev` 标签的本地完整测试套件、本地执行的 CI 竞态检测选集，以及针对修复之间相互作用的对抗性审查，全部通过。远端 CI 和多池验收尚未完成。未合并，未发布。

## 简短结论 {#tldr}

报告属实，也是下一个版本发布前最严重的开放缺陷。部署有多个池时，同一个 key 的版本经常分散在不同池中。生命周期按某一个池里的版本做判断，但由此发起的过期操作会在所有池中删除或隐藏这个 key。于是：

- 一个版本在本池是最新的、但不是整个对象的最新版本，会被当成当前版本；
- 一个在本池里单独存在的删除标记，会被当成"没有更早版本"的标记。

结果是静默的数据损坏：新的删除标记盖住了当前版本，较新的版本随整个 key 一起被删，已删除的对象重新变得可读。decommission 和 rebalance 做的是同样的判断，并且仍然报告 Complete。

修复保留现有的所有生命周期判断点，只在它们的汇合处加一道检查：多池部署中，ILM 过期真正删除任何东西之前，由池层在对象锁内，把该 key 在所有池中的版本合并成一个列表，重新求值一次规则。对整个对象不成立的过期会被拒绝；版本历史或锁保护无法权威确定的过期，同样会被拒绝。decommission 和 rebalance 会迁移这样的版本，而不是把它交给过期处理。在单池上，版本和删除标记的过期跳过合并读取；整对象过期则在锁内检查每一个版本（见[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)）。

## 定性 {#assessment}

| 维度 | 判断 |
| --- | --- |
| 性质 | 生命周期求值中的数据正确性缺陷；继承自上游设计，不是已发布 SILO 版本引入的回归。 |
| 受影响部署 | 多于一个池；桶开启或暂停了版本控制；并配置了 `Expiration`、`ExpiredObjectAllVersions`、`ExpiredObjectDeleteMarker` 或 `DelMarkerExpiration` 规则。 |
| 不受影响 | 单池部署；所有版本都在同一个池中的 key；恢复副本过期（由 #281 跟踪）。 |
| 严重程度 | 致命。版本被删除或隐藏而没有任何错误，唯一的痕迹是 ILM 审计条目和桶通知。 |
| 可达性 | 普通 S3 写入即可触发。在报告者的复现中，SILO 自身的放置策略让三分之一到一半的 key 的版本分布在两个池中。 |
| 发布紧急度 | 阻塞下一个版本。main 上已经合入 [#276](https://github.com/pgsty/silo/pull/276)，它让迁移过期在 decommission 或 rebalance 遍历中立即执行。 |
| 剩余工作量 | 代码、审查和多池验收运行都已完成，还需要远端 CI。 |
{.wide .expand}

## 触发条件 {#trigger}

在正常运行中，一个 key 就会在两个池里都有版本：

- 已存在 key 的新版本写入的池按可用空间加权随机选出，可能不是已经持有该 key 的池；
- 同一个 key 的两次首次写入并发，落在不同的池；
- decommission 或 rebalance 在复制了部分版本后中断。

此时，只要生命周期规则的判断依赖该 key 的其他版本，就会出错。报告者在 main 上的矩阵展示了每一种失败形态：

| 规则 | 扫描前的布局（新的在前） | main 上的结果 |
| --- | --- | --- |
| `Expiration` `Days=1` | p1 `[v1]`，p2 `[v2]` | 新的删除标记盖住了当前版本 `v2`。 |
| `Expiration` 加 `ExpiredObjectAllVersions` | p1 `[v1]`，p2 `[v2]` | `v1` 被当作当前版本，整个 key（包括 `v2`）被删除。 |
| `ExpiredObjectDeleteMarker` | p1 `[dm]`，p2 `[v1]` | 删除标记被移除，已删除的对象重新读出 `v1`。 |
| `DelMarkerExpiration` | 一个池中是删除标记，另一个池中有更新的版本 | 标记过期时连同更新的版本一起删除（由 Go 测试覆盖；普通 S3 写入不会产生这种布局）。 |
{.wide .expand}

同一轮运行中，所有版本都在同一个池里的 key 表现正确。

## 根因 {#root-cause}

生命周期求值需要每个版本的三项信息：

- 是否是最新版本（`IsLatest`）；
- 对象共有多少个版本（`NumVersions`）；
- 后继版本的写入时间（`SuccessorModTime`）。

每个发起过期的地方都只用自己看得到的版本来计算这三项：

- scanner 和磁盘 heal 读取一个纠删集合的 `xl.meta`；
- 带 `versionId` 的 GET 和 HEAD 读取持有该版本的池；
- decommission 和 rebalance 遍历一个池。

执行过期的地方却不一样。`applyExpiryOnNonTransitionedObjects` 和 `expireTransitionedObject` 通过池层删除：整对象动作会在每个池中删除该对象，新的删除标记会在每个池中隐藏该 key。对单个版本或新建删除标记，锁内的集合级复核也帮不上忙，因为它求值的是承接这次删除的那个集合里的版本；如果正是这个集合做了错误判断，复核只会确认它。除跨池判断之外，整对象过期另有单独记录（见[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)）。

一句话：判断是局部的，动作却是全局的。

## 行为的来源 {#history}

### 溯源 {#provenance}

**来自上游，不是 SILO 引入的。** 这个缺陷有两个上游成分：生命周期判断基于单个集合看得到的版本，动作却作用于整个 key；以及一次放置策略的改动，让 key 的版本分布在多个池中成为常态。从 `RELEASE.2025-12-03T12-00-00Z` 到 `RELEASE.2026-10-26T00-00-00Z` 的全部 18 个 SILO 版本都同时包含这两个成分。SILO 在这条路径上的改动，要么没有触及判断，要么尚未发布；有影响的几项列在下面。

**成分 1：本地判断，全局动作。** 每个发起方都用自己读到的版本求值。下表中的提交都在上游，也在每一个 SILO 版本中。

| 发起方 | 提交 | PR | 日期 | 首个上游版本 |
| --- | --- | --- | --- | --- |
| 扫描器按对象求值生命周期（`scannerItem.applyActions`） | [43d6e3a](https://github.com/pgsty/silo/commit/43d6e3ae0)（Klaus Post） | [#9579](https://github.com/minio/minio/pull/9579) | 2020-06-12 | `RELEASE.2020-06-14T18-32-17Z` |
| 扫描器改用完整求值器，输入是单个集合的版本列表 | [01447d2](https://github.com/pgsty/silo/commit/01447d243) | [#21096](https://github.com/minio/minio/pull/21096) | 2025-04-02 | `RELEASE.2025-04-03T14-56-28Z` |
| GET 和 HEAD 让读到的版本过期 | [65aa2bc](https://github.com/pgsty/silo/commit/65aa2bc61)（Anis Elleuch） | [#11296](https://github.com/minio/minio/pull/11296) | 2021-02-01 | `RELEASE.2021-02-01T22-56-52Z` |
| decommission 跳过并让 ILM 已过期的版本过期 | [236ef03](https://github.com/pgsty/silo/commit/236ef03db)（Harshavardhana） | [#15300](https://github.com/minio/minio/pull/15300) | 2022-07-14 | `RELEASE.2022-07-15T03-44-22Z` |
| rebalance，同一过滤逻辑 | [4523da6](https://github.com/pgsty/silo/commit/4523da654)（Krishnan Parthasarathi） | [#15483](https://github.com/minio/minio/pull/15483) | 2022-10-25 | `RELEASE.2022-10-29T06-21-33Z` |
| 驱动器 heal 跳过已过期的版本（直到下一个版本，见第 12 部分） | [109a9e3](https://github.com/pgsty/silo/commit/109a9e3f3)（Harshavardhana） | [#18569](https://github.com/minio/minio/pull/18569) | 2023-12-01 | `RELEASE.2023-12-02T10-51-33Z` |
{.wide .expand}

动作是消费方。对象锁内的集合级复查，即 `erasureObjects.DeleteObject` 中的 `opts.Expiration.Expire`，来自 [35f2552](https://github.com/pgsty/silo/commit/35f2552fc)（[#13091](https://github.com/minio/minio/pull/13091)，Harshavardhana，2021-08-27，`RELEASE.2021-08-31T05-46-54Z`），它读取的是执行删除的那一个集合的版本。上游 master 的代码相同。

**成分 2：让分裂 key 变得常见的放置策略。** [83b2ad4](https://github.com/pgsty/silo/commit/83b2ad418)（jiuker，[minio/minio#21115](https://github.com/minio/minio/pull/21115)，2025-07-19）在 `getPoolIdx`（现名 `getWritePoolIdx`）的条件中加入了 `|| pinfo.Err == nil`。在此之前，只有尚不存在的 key 才按空闲空间选池，已存在 key 的新版本留在持有该 key 的池中。在此之后，已存在的 key 也按空闲空间选池，新版本可能落在另一个池。包含它的首个上游版本是 `RELEASE.2025-07-23T15-54-02Z`；`RELEASE.2025-07-18T21-56-31Z` 不包含。全部 18 个 SILO 版本都包含它，上游 master 至今也保留。该提交的标题讨论的是单个池的空闲阈值，对已存在 key 的影响看起来是副作用，而不是有意的设计。按空闲空间选池是加权随机抽取，而不是“空闲空间最多的池”。

**SILO 在这条路径上改了什么。**

| SILO 改动 | 日期 | 是否发布 | 对缺陷的影响 |
| --- | --- | --- | --- |
| [e59a3d9](https://github.com/pgsty/silo/commit/e59a3d938) 串行化并对账多池对象更新 | 2026-09-11 | 自 `RELEASE.2026-09-16T00-00-00Z` 起 | 收窄了一个触发条件：PUT 现在在同一把池层锁下查找并写入 key，两次首次写入不会再同时认为 key 不存在。放置策略和生命周期求值没有变化，因此分裂 key 仍会产生。 |
| [f54c048](https://github.com/pgsty/silo/commit/f54c04846) 在 `getWritePoolIdx` 中加入写恢复标志，[2a04d5f](https://github.com/pgsty/silo/commit/2a04d5f48) 又把它去掉 | 2026-10-25 | 两者都在 `RELEASE.2026-10-25T00-00-00Z` | 无。已发布代码中的放置条件就是上游的条件。 |
| [7a060ca](https://github.com/pgsty/silo/commit/7a060cab1) 按访问频率在池间迁移热对象，及其回退 [9b76a21](https://github.com/pgsty/silo/commit/9b76a2167) | 2026-08-15、2026-09-15 | 仅同时出现在 `RELEASE.2026-09-16T00-00-00Z` | 无。该功能从未在没有被移除的情况下发布。 |
| [60c7179](https://github.com/pgsty/silo/commit/60c7179dd)、[1748f62](https://github.com/pgsty/silo/commit/1748f62c7) 及其他迁移安全修复 | 2026-10-18 | 自 `RELEASE.2026-10-18T00-00-00Z` 起 | 无。`RELEASE.2026-10-26T00-00-00Z` 中 decommission、rebalance、heal 的 `filterLifecycle` 闭包与上游 master 完全一致，扫描器的求值也一致。 |
| [#266](https://github.com/pgsty/silo/pull/266) decommission 和 rebalance 期间迁移 ILM 已过期的当前版本（[19910230](https://github.com/pgsty/silo/commit/19910230a)、[a995921](https://github.com/pgsty/silo/commit/a995921e5)） | 2026-10-29 | 仅在 main，位于 `RELEASE.2026-10-26T00-00-00Z` 之后 | 收窄。版本控制开启的桶里，当前版本过期只会加一个删除标记，所以遍历现在迁移该版本，而不是跳过它。 |
| [#276](https://github.com/pgsty/silo/pull/276) 迁移期间的 ILM 清理（[0a546c7](https://github.com/pgsty/silo/commit/0a546c7a7)） | 2026-11-02 | 仅在 main | 在时机上放大。它判断的仍是同一份按池的副本，但在源被淘汰之前，在遍历内立即执行过期，包括整对象动作。在已发布版本中，遍历跳过该版本，并把同样的判断交给过期工作线程排队。 |
| [a803027](https://github.com/pgsty/silo/commit/a803027b0) 把 `DelMarkerExpiration` 计为活动规则 | 2026-11-03 | 仅在 main | 暴露面放大。扫描器原先跳过只有 `DelMarkerExpiration` 规则的桶；在 main 上它会对这类桶求值，从而触发上面的第四种失败形态。 |
| 整对象精确 key 修复（[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)） | 2026-11-05 | 仅在集成分支 | 整对象过期的配套修复：按精确 key 而不是前缀删除，在单池和多池上都在锁内检查每个版本，并清理分层版本的远端对象。 |
{.wide .expand}

所以，已发布的 SILO 版本所包含的缺陷就是上游的缺陷，没有变化。#266 和 #276 不在任何发布标签中。#276 没有产生新的错误判断，它让已有的错误判断立即执行，这就是本修复成为下一个版本发布门槛的原因。

针对本问题的维护者修复的第一版自身有两个缺陷：通过过时的少数派元数据修订绕过法律保留，以及重复副本的待清除状态丢失。评审在发布之前发现了它们，两者都从未合入或发布。

日期、PR 编号和发布归属来自 git 历史。关于代码流程的说法来自阅读代码。

## 方案比较 {#options}

### 方案 1：当 key 跨池时禁用生命周期或跳过过期 {#option-1}

这样做安全，但错在另一个方向：合法的规则会无限期失效，而运维人员得不到任何"保留策略已经不再执行"的信号。

### 方案 2：让一个 key 的所有版本都留在同一个池 {#option-2}

池亲和可以减少新产生的跨池 key，但修复不了已有的跨池 key、中断的迁移和并发的首次写入。SILO 已经评估过覆盖写的池亲和方案，因为小对象覆盖写性能回退而没有采用（见 [多池覆盖亲和](/zh/blog/design/overwrite-pool-affinity/)）。池亲和可以作为未来的缓解手段，但不是正确性修复。

### 方案 3：让每个发起方都按合并后的版本求值 {#option-3}

每次 scanner 访问、heal、读取和迁移步骤，都要从每个池读取该 key。这个代价会落在"对象没有任何东西需要过期"这一最常见的情况上，而且每个发起方在判断与删除之间仍然会和写入发生竞争。

### 方案 4：在执行端、对象锁内复核 {#option-4}

这是选定的方案，也是 PR #279 的思路。发起方保留廉价的本地判断；只有即将真正执行的删除才需要付出一次合并读取，而且这次读取和删除在同一把对象写锁内进行，检查与执行之间版本列表不会变化。

### 不采纳的扩展 {#rejected-additions}

全局版本索引、跨请求缓存或新的生命周期状态机，都会引入持久状态和新的故障模式，而修复这个缺陷并不需要它们。

## 修复方案 {#fix}

修复共十二部分：

- **第 1、2 部分**是 PR #279 的原始内容。
- **第 3–5 部分**来自前两轮维护者审查。
- **第 6–9 部分**来自对此版本的对抗性审查。那轮审查复现了前面几部分引入的两个缺陷，以及它们没有关闭的两条更早的路径。
- **第 10–12 部分**来自 2026-11-06 的发布审查。

1. **在执行端按合并版本求值（PR #279 第 1 个提交）。** `lifecycleEventsAllPools` 从每个池中该 key 所在的纠删集合读取版本，忽略分层 free version；按从新到旧合并，在两个池中都有副本的同一版本只计一次；然后用完整的生命周期求值器求值，并按整个对象计算 `IsLatest`、`NumVersions` 和 `SuccessorModTime`。`expiryApplies` 把结果对应到所请求的删除：
   - 整对象删除，要求最新版本带有整对象动作；
   - 新建删除标记，要求最新版本到期；
   - 删除指定版本，要求该版本本身带有删除动作。

   检查有四种结果：
   - 批准；
   - 版本存在但规则不成立时，返回 `errLifecycleNotApplicable`；
   - 目标不存在时，返回 `ObjectNotFound` 或 `VersionNotFound`；
   - 无法权威地读出版本历史时（第 6 部分），返回 `InsufficientWriteQuorum`。

   其他错误照常向上传递。scanner 会在后续轮次重试被拒绝的过期。与"不存在"不同，拒绝结果永远不会确认一次待处理的复制 purge；迁移在源版本仍然存在时被拒绝，也不会退役这个版本。

   `erasureServerPools.DeleteObject` 对多池上的 ILM 删除在对象锁内执行检查，然后把请求标记为 `CheckedAllPools`。`DeleteObjects` 对每一批 ILM 版本清理执行同样的检查，每个 key 只做一次。
2. **迁移规则未覆盖的版本（PR #279 第 2 个提交）。** decommission 和 rebalance 只在 `migrationExpiryApplies` 按所有池确认后，才保留按池做出的过期判断；否则该版本像其他版本一样被迁移，之后由 scanner 在持有该 key 的池中应用规则。没有这一部分，遍历中的过期会被拒绝，decommission 会在被退役的池里还留着该版本时停下。
3. **分层非当前版本批量清理中的全池核准传递。** 新增的集合级 `Expire` 标志导致分层的 `NewerNoncurrentVersions` 批量清理在集合内被拒绝，而批量适配层又把这个拒绝当成成功上报。现在 `deleteObjectsReconciled` 只对带显式版本 ID 的 ILM 条目传递 `CheckedAllPools`，这正好是池层已经检查过的那些条目。
4. **读路径触发的过期，按实际读到的版本复核。** 本地求值认为版本到期时，GET 和 HEAD 会返回 `NoSuchKey` 并把过期入队。在多池部署中，对本地的删除候选，读路径现在会按合并列表再求值一次，并按实际读到的版本身份匹配事件：
   - 别处一个更新的版本到期，不能成为隐藏一个仍然有效的旧版本的理由；
   - 复核失败或未确认过期时，读取照常成功，也不入队；`recheckReadExpiry` 会在 `expiry_incomplete_total` 中按原因（`history_unavailable` 或 `not_applicable`）统计被跳过的过期，并写入 `result=skipped` 的 ILM trace（[04d7d9197](https://github.com/pgsty/silo/commit/04d7d9197)）；
   - 本地结果为"无动作"时，不产生任何额外读取。
5. **被拒绝的过期不再发送删除通知。** 以 `errLifecycleNotApplicable` 被拒绝的批量条目，不再发送 `s3:ObjectRemoved:Delete` 通知，也不再写 ILM 过期审计。第 9 部分把这一点扩展到所有未生效的结果。
6. **要么得到权威的版本历史，要么不做决定。**
   - **采纳规则。** 一个版本的某个修订，由元数据头加上规范化后元数据的 sha256 摘要来标识：
     - 摘要使用无歧义的编码：每张表单独成段，记录条目数，各条目按键排序并带长度前缀。
     - 按设计就因盘而异的字段不参与计算，包括纠删索引和旧格式对象的分片校验和。
     - 只靠 4 字节的元数据头签名并不够，因为两种不同的锁状态可能得到相同的签名。

     只有当集合中至少 `max(n/2 + 1, 该版本自身的元数据读 quorum)` 块盘持有这个修订时，`objectVersions` 才采纳它；`n` 是集合配置的盘数。合并历史之前，会先剔除每块盘上未被采纳的修订，避免一块过时的盘挤掉多数派。
   - **拒绝条件。** 以下任一情况都以 `InsufficientWriteQuorum` 拒绝：
     - 任一块盘上能看到的某个有效版本，没有被采纳的修订；
     - 集合中一半或更多的盘读不到。
   - **适用范围。** 这些检查在每一个提前返回之前都会执行。处理每个版本之间都会检查取消，一旦取消就拒绝删除。
   - **关闭的漏洞。** 此前，一块错过了 legal hold 更新的盘，就可能提供合并所用的修订；而一半的盘读不到时，一个达不到 quorum 的新版本会从历史中消失，于是整对象过期把它删掉。
7. **合并过程中不会丢失的锁保护。**
   - **跨池。** 锁字段按与生命周期求值器相同的键优先级读取：先读小写键，再读规范大小写的键。同一版本在不同池中的副本，如果在 legal hold 或 retention 上不一致，只有当两者都带有效、非零的修订时间戳，且其中一个严格更新时，才采用更新的那个；否则拒绝该对象。

     修改时间不同的副本是不同的写入，例如暂停版本控制的桶中两次写入的 `null` 版本。由最新的那次写入决定；如果更早的那次写入仍受保护，则拒绝该对象。
   - **集合内。** 对单个版本的 ILM 删除，集合在锁内重新读取目标，并在以下两种情况拒绝：
     - 有待处理的复制 purge；
     - 只把已批准状态以严格更新的有效时间戳证明为过时的那些锁字段替换掉之后，版本仍然受保护（retention、legal hold 或时钟不可用）。

     批量删除依靠第 6 部分和跨池规则。
8. **复制状态不一致的重复副本被拒绝。** 对同一版本在两个池中的副本，会在解析后比较复制总状态、purge 总状态和按目标的状态表，任何语义上的差异都会拒绝该对象。此前，一个副本上待处理的 purge 会在合并视图中消失，该版本可能在 purge 复制完成之前就过期。
9. **只有真正完成或确认已不存在的删除才会被通知。** 只有过期删掉了它针对的对象、或确认它原本就不存在时，才发送 `ObjectRemoved` 通知；任何拒绝或失败都不会发送。在批量路径上，删除的 ILM 过期审计也是如此。没有删掉任何东西的过期留下什么记录，取决于原因：
   - **失败**（quorum 失败或其他错误）会带 `ilm-incomplete-reason` 标签写入审计，以 `result=failed` 和原因写入 trace，写入日志（同一对象重复出现的相同失败，由去重日志抑制，直到它每小时重置），并计数；
   - **拒绝**（在锁内重新判断时规则已不适用，或 Object Lock 保护该版本）会以 `result=refused`、原因和错误写入 trace 并计数，但不写审计：分裂的 key 在每次扫描时都会被拒绝。

   scanner 和已转储版本的过期，现在按删除实际做了什么来命名一次完成的过期：没有指定版本 ID、结果是删除标记的过期，创建了这个标记；其他过期删除了它针对的版本，删除标记也包括在内。此前它们从排队的对象取身份，因此版本桶中最新已转储版本的过期，会把它保留的版本报告为已删除。复制重试的处理不变。
10. **被拒绝和失败的过期会被计数。** `expiry_incomplete_total` 按 `reason` 统计每一次没有删掉所针对对象的 ILM 过期尝试：`not_applicable`（规则已不适用）、`locked`（Object Lock）、`history_unavailable`（无法权威读取历史）和 `error`。指标 v2 导出为 `minio_node_ilm_expiry_incomplete_total`，指标 v3 在 `/ilm` 下导出为 `minio_ilm_expiry_incomplete_total`。桶和对象都不是标签，已经不存在的版本不计数。
11. **获批的版本过期会删除所有副本。** 一个版本可能在两个池中都有副本，例如 decommission 或 rebalance 中断之后。池层用所有池的版本核准的 ILM 版本过期，现在会删除每一份副本，先删次要副本、最后删主副本，遇到第一个失败就停止，所以分层版本的远端对象只会在所有副本都删掉之后才删除。每个集合仍守护池层核准的那些保护。此前只删除按最新 key 路由选中的那一份副本：另一份副本仍可读，分层版本的远端对象在那份副本仍引用它时就被删除，持有它的池在 decommission 时完成检查失败。批量非当前版本清理本来就会删除所有副本。
12. **驱动器 heal 会修复它排入过期的版本。** 驱动器 heal 按单个池里的版本求值生命周期。对它认为已到期的版本，它排入过期并跳过 heal。而过期会在对象锁内重新判断，可能被拒绝，于是这样的版本在被更换的盘上一直保持降低的冗余，直到拒绝结束为止；scanner 只 heal 没有到期动作的版本，也不会修复它。现在驱动器 heal 排入过期，同时修复该版本；随后被过期删除的版本只多花一次 heal。heal 与过期通过写者锁域中的对象锁互斥，这由[单池锁域修复](/zh/blog/design/single-pool-lock-domains/)提供。
{.steps}

同一版本在两个池中的副本合并时，各自独立排序的 retention、legal hold 和标签修订都会保留，并遵循第 7 部分的严格排序。

## 为什么方案充分且必要 {#sufficiency}

**对其覆盖的路径是充分的。** 多池部署中，所有针对单个版本或删除标记的 ILM 动作，都经由 `erasureServerPools.DeleteObject` 或 `erasureServerPools.DeleteObjects` 到达存储层，包括 scanner、磁盘 heal、读路径触发的过期、过期 worker 和迁移遍历。合并检查就放在这里：

- 它与串行化该 key 写入的是同一把对象写锁；
- 它使用的是 scanner 用的求值器；
- 有了第 6–8 部分，只要版本历史或保护状态无法确定，它就拒绝。

在这些路径上，错误的本地判断会被拒绝，而不会被执行。迁移在决定"不迁移某个版本"之前，也会调用同一检查。

**由配套修复覆盖。**

- **整对象过期**（`ExpiredObjectAllVersions` 和 `DelMarkerExpiration`），除第 1 部分的跨池判断之外，由[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)覆盖。

**必要性。** 每一部分都关闭一条否则会继续存在的路径：

- 是否到期取决于其他池中的版本，因此判断需要一个完整的跨池视图，并且要和删除串行化。对象锁内的池层执行端，正是这个视图和这把锁交汇的地方。
- 没有迁移部分，decommission 会在被退役的池里还留着被拒绝的版本时停下。
- 没有在批量清理中传递全池核准，分层非当前版本清理会在源端保留了版本的情况下被上报为已完成。
- 没有读路径修改，GET 和 HEAD 仍会对有效版本返回 `NoSuchKey`。
- 没有第 6 部分：
  - 一块过时的盘就能解除 legal hold；
  - 不完整的历史能批准删除一个已提交的版本。
- 没有第 7 部分：
  - 两个池之间时间戳相同的冲突，可能在批量路径上丢掉 hold；
  - 待处理的 purge 可能被忽略。
- 没有第 8 部分，重复副本上待处理的 purge 会被忽略。
- 没有第 5、9 部分，被拒绝的过期会被当作删除发布出去。没有第 10 部分，运维人员无法看出本应删除的版本为何仍然存在。
- 没有第 11 部分，获批的版本过期会在另一个池中留下可读的副本，还可能删掉该副本仍引用的远端对象。
- 没有第 12 部分，过期被拒绝的版本在换盘之后会一直保持降低的冗余。

**有意排除的范围：**

- 在单池上，版本和删除标记的过期跳过合并读取。它们只有一处变化：ILM 拒绝现在返回 `errLifecycleNotApplicable`，而不是"不存在"。scanner 一类的调用方对两者处理相同；迁移永远不会把拒绝当作不存在。
- 恢复副本过期取决于恢复日期，而不是其他版本，由 [#281](https://github.com/pgsty/silo/issues/281) 处理。
- 未开启版本控制时的单副本删除保留集合自身的复核，因为那里的每个副本都是独立的写入。

## 代价与兼容性 {#cost}

- **接口。** 没有新的公开 schema、路由、配置、存储格式或依赖；`ExpirationOptions` 只增加内存中的字段。可见的行为变化有三处：
  - 过期会被拒绝；
  - GET 和 HEAD 会返回以前回答 `NoSuchKey` 的版本；
  - 单池返回上述拒绝错误。
- **I/O 与 CPU。** 多池部署中，每次 ILM 删除都在已持有的锁内，从每个池中该 key 所在集合的每块盘读取完整的版本历史，并对每块盘上的每个版本解码、计算哈希。decommission 和 rebalance 遍历在预检查时每个 key 只读取一次历史，并基于这次读取判断该 key 的每个到期版本；每次过期在删除之前仍会在锁内再读一次历史。批量删除每次调用、每个 key 做一次。取消是协作式的：在版本之间、合并前后检查。合并本身不能被取消，因此没有耗时上限。这里有意不设版本数上限，因为设上限会恰好卡住生命周期最需要清理的长历史 key。
- **合并成本。** 合并开销随历史长度超线性增长。用本修复之前的合并方式，在内存中、16 路盘数据下，1,000 个版本约 2.4 毫秒，8,000 个版本约 230 毫秒。这些数字测的是修复前的合并，不是最终实现。
- **哪些过期会执行。** 对整个对象不成立、或版本历史无法确定的过期不再执行。有一种情况现在会过期而以前不会：带对象大小过滤的规则，作用于一个当前版本所在池与"第一个持有该 key 的池"不同的 key。
- **回滚。** 回滚即恢复旧行为，两个方向都不需要迁移。

## 剩余限制 {#limits}

- **已经造成的损坏不会被修复。** 旧行为已经添加的删除标记会保留。它们是普通的删除标记，核对 ILM 审计日志或桶通知后，可以用 `DELETE ?versionId=` 移除。已经被删除的版本，本修复无法找回。
- **拒绝可能无限期持续。** 以下情况会一直拒绝过期，直到 heal 修复元数据为止；反复扫描本身不会修复它们：
  - 严格的历史规则；
  - 过时的受保护副本；
  - 残留记录；
  - 复制状态不一致。

  一半或更多的盘读不到的降级集合，也会让其中 key 的过期停下。
- **每个池都必须给出历史。** 多池部署中，该 key 在每个池中所在的集合都必须给出 key 的历史。某个池离线，或者它为该 key 所在集合有一半或更多的盘读不到时，即使这个池并不持有该 key 的任何副本，该 key 的过期也会停下。生命周期复核失败不会让本来能成功的 GET 或 HEAD 失败，但它们仍须满足正常的读 quorum。这些拒绝按 `history_unavailable` 计数。这是有意为之：无法应答的池无法证明 key 不在那里。
- **长历史仍然每个被删版本读一次。** 遍历在预检查时每个 key 只读取一次历史，但每次过期都会在锁内再读取并合并一次，因此有大量到期版本的 key，每删除一个版本都要读一次历史。
- **在两个池中都有副本的非版本化 key 可能一直不过期。** 较旧的副本不满足规则的大小或标签过滤、而较新的副本满足时，过期会停在较旧的副本上，较新的副本不会过期。已发布版本中，较新的副本会被删除、较旧的副本暴露出来，这更糟。这种布局很少见。
- **不保证生命周期最终收敛。** 一个版本可能对整个对象是非当前版本，但在它自己的池里是最新的。按池运行的 scanner 可能一直不会提出它，因此在版本合并到同一个池之前（例如 decommission 或 rebalance 之后），一些已到期的版本可能一直保留。
- **读取不会隐藏所有到期版本。** 最新版本的整对象规则已经到期时，对一个更早版本的 GET 或 HEAD 仍可能返回该版本。
- **放置策略不变。** 已存在 key 的新版本仍按空闲空间选池，跨池 key 仍会继续出现。SILO 是否应优先选择 key 所在的池，是另一个关于放置和性能的问题。

## 验证 {#verification}

**第 1–5 部分，在集成分支 head 上：**

- `TestPoolsLifecycleSplitObject` 和 `TestPoolsMigrationLifecycleWholeObject`（来自 PR #279）覆盖 scanner、decommission 和 rebalance。前者中的 HEAD 用例只模拟了求值和入队；真实的 handler 由下面的读取测试覆盖。
- `TestPoolsLifecycleTieredNoncurrentBatch`、`TestPoolsLifecycleTieredBatchNotReplicated`（原名 `TestPoolsLifecycleTieredBatchReplication`，现在检查批量路径不排队任何复制）、`TestPoolsLifecycleTieredBatchIdentity` 和 `TestPoolsLifecycleBatchRejectionNotAnnounced` 覆盖批量路径及其复制、通知副作用。
- `TestPoolsLifecycleDuplicateLockMetadata`、`TestPoolsLifecycleDuplicateTagMetadata` 和 `TestPoolsLifecycleBatchRejectionReplication` 覆盖副本合并和被拒绝的清理。
- `TestPoolsLifecycleReadHTTP`、`TestPoolsLifecycleReadAuthorizationAndClose`、`TestPoolsLifecycleReadBoundaries` 和 `TestPoolsLifecycleReadProxy` 经过真实的 GET 和 HEAD handler，包括鉴权顺序和 reader 释放。
- 早先的维护者审查轮次记录过完整的 `./cmd` 测试、定向 race 选择，以及一次变异测试（38 个变异中 37 个被测试捕获）。对抗性审查轮次没有重新运行这些。

**对抗性审查。** 审查在集成分支 head 上用可执行探针完成，维护者重新运行了全部探针，结果相同。

- **五个探针失败：**
  - 少数派过时锁修订让受 hold 保护的版本被删除；
  - 不完整的历史批准了对新版本的整对象删除；
  - 重复副本上待处理的 purge 被丢掉；
  - quorum 拒绝被当作删除发布；
  - 单池的拒绝错误发生了变化。
- **另外两个是测量：** 读取覆盖范围和合并成本。
- **回归测试。** 第 6–9 部分把相关探针转为回归测试，并另外加入以下用例：
  - 8/8 冲突修订；
  - 降低校验位的部分版本；
  - 读不到的盘数的边界；
  - 残留的 free version；
  - 跨池时间戳相同的保护冲突（单个和批量路径）；
  - 带删除标记元数据的待处理 purge；
  - 顺序不同但等价的按目标状态表；
  - 混合批量的副作用。
- **对照用例。** 正常降级的集合，以及跨池严格更新的解除操作，仍必须正常过期。

**补丁审查。** 获批的补丁新增 26 个测试，它们在之前的 head 上失败、加上补丁后通过，race 检测无问题。生命周期、迁移、恢复和过期相关的测试选集共 88 个测试，全部通过，无失败。审查者自己写的 11 个探针在最终补丁上全部通过。

**端到端运行。** 2026-11-05，在一台带两个池（每池四块盘）的原生服务器上，分别对 `69fcf50cd` 和修复运行了报告者的 `repro.sh`。在 `69fcf50cd` 上，scanner 步骤隐藏了 9 个当前版本，丢失了 8 个版本，并使 8 个已删除的 key 复活；decommission 步骤报告 Complete，同时丢失了 6 个版本、复活了 3 个 key。使用修复后，两个步骤中的每个 key 要么保持不变，要么在其规则到期时被完整过期，scanner 仍然删除了全部 32 个到期的 key。`docs/distributed/decom.sh` 在修复上通过：它扩容集群，对存有多版本和分层对象的池执行 decommission，再移除该池，之后 `s3-check-md5` 报告剩余的每个对象版本都完好。

**发布审查（2026-11-06）。** 第 10–12 部分和更省的预检查附带以下测试，去掉对应改动时每一个都会失败：

- `TestILMExpiryNotDoneClassification`、`TestDeleteObjectVersionsReportsRefusalAndFailure`、`TestExpiryEventsNameTheResult` 和 `TestILMExpiryIncompleteMetrics`：每种错误的原因；一次包含被拒绝、失败和已删除条目的批量清理，对前两者计数并写 trace，只对失败写审计，只对删除发送通知；事件说明创建了标记还是删除了版本；两个版本的指标都按原因导出计数器；
- `TestPoolsLifecycleVersionExpiryDeletesEveryCopy`：两个池中都有副本时，热版本和分层版本的过期都会删除两份副本，远端对象只删除一次；次要副本删不掉时过期失败，两份副本和远端对象都保留；对持有第二份副本的池执行 decommission 能够完成；
- `TestHealDriveHealsVersionWithRefusedExpiry`、`TestHealDriveThenExpiryRemoves` 和 `TestHealDriveThenExpiryAddsMarker`，`TestHealDriveDoesNotRestoreStaleMinority` 作为对照；
- `TestPoolsMigrationExpiryPrecheckReadsHistoryOnce`：对一个有 63 个到期非当前版本的 key 执行 decommission 和 rebalance，只读取一次它的历史，结果不变。

**合并前仍需完成：** 在最终 head 上运行远端 CI。

多节点锁域，以及长时间运行的 scanner 和迁移行为，尚未验证。

**集成验证。** 这个修复是下个版本集成分支的基础。#281 以及锁域、整对象删除、Heal 演练、#259、#285 和 Console 的修复都叠在它上面，所有摘取都没有冲突。在该 head 上，完整的 `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` 套件通过，CI 的竞态检测选集和覆盖全部新测试的竞态选集也都通过。针对组合的对抗性审查没有发现缺陷，锁域、清理路径以及清除与恢复之间的交互都用实际执行的探针检查过。

本地通过记录使用 `kqueue,dev` 标签。最终提交在 Ubuntu CI 上的无标签命令 `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m` 尚待验证；本地带标签的结果不能替代该项验收。

## 审查记录 {#review}

| 轮次 | 结果 |
| --- | --- |
| 维护者第 1、2 轮 | 发现批量清理中全池核准的传递缺口、读路径隐藏有效版本、被拒绝的过期被当作删除发布，作为第 3–5 部分修复。 |
| 对抗性审查 | 要求修改。两个问题由第 1–5 部分引入：过时修订导致的 legal hold 绕过、重复副本上丢失的待处理 purge，作为第 6–8 部分修复。两个问题更早就存在：不完整历史下的整对象删除、其他拒绝也被发布，分别作为第 6、9 部分修复。整对象过期在[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)中修复。单池错误码的变化已在上文说明。 |
| 设计第 2、3 轮 | 有条件同意。修订需要严格多数加上该版本自身的读 quorum；认定过时需要严格更新的有效时间戳；待处理的 purge 一票否决；跨池保护冲突在批准前就拒绝。 |
| 补丁审查第 4–7 轮 | 第 4 轮：发现 4 字节的元数据头签名不能用来标识修订。第 5 轮：发现另外三个问题，即只读小写的锁键（原本就有）、摘要缺少表边界、旧格式的分片校验和在不同盘上永远不一致。第 6 轮：发现旧格式的嵌套表哈希时没有排序。以上问题都已修复并补了回归测试。第 7 轮：在约定范围内没有剩余问题，批准。 |
| 发布审查（2026-11-06） | 发现被拒绝和失败的过期几乎不留痕迹，scanner 把拒绝记成删除（第 9、10 部分）；获批的版本过期只删掉两个池中副本的一份（第 11 部分）；驱动器 heal 跳过它排入过期的版本，过期一旦被拒绝，这些版本就保持降低的冗余（第 12 部分）；遍历在预检查时对每个到期版本都读一次 key 的历史；无法给出历史的池会停止它并不持有的 key 的过期；非版本化的分裂 key 可能一直不过期。最后两点作为限制写明。 |
{.wide .expand}

## 参考 {#references}


- Issue：[#278](https://github.com/pgsty/silo/issues/278)
- 贡献者 PR：[#279](https://github.com/pgsty/silo/pull/279)
- 配套整对象过期修复：[整对象 ILM 过期](/zh/blog/design/ilm-delete-all-exact-key/)
- 相关的恢复副本过期：[#281](https://github.com/pgsty/silo/issues/281)、[#282](https://github.com/pgsty/silo/pull/282)
- 迁移过期改动：[#276](https://github.com/pgsty/silo/pull/276)，以及 [ILM 过期与存储池迁移顺序](/zh/blog/design/ilm-migration-ordering/)
- 上游放置策略改动：[minio/minio#21115](https://github.com/minio/minio/pull/21115)
- 未采用的放置方案：[多池覆盖亲和](/zh/blog/design/overwrite-pool-affinity/)
