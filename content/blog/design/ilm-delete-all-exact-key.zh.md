---
title: '生命周期"删除全部版本"只能作用于一个 key'
linkTitle: "删除全部版本只作用于一个 key"
date: 2026-11-04
lastmod: 2026-11-10
author: "PGSTY SILO 维护团队"
summary: >
  解释生命周期或批量过期对一个 key 执行"删除全部版本"时，为何会连带删除名字位于该 key 之下的所有对象，以及为什么在对象锁内复核后、按版本 ID 清除该 key 自身的版本，是最小而完整的修复。
tags: [Design, Lifecycle, Batch Expiration, Data Safety]
weight: 10
draft: false
url: "/zh/blog/design/ilm-delete-all-exact-key/"
---

本文记录的缺陷是在审查 [#278](https://github.com/pgsty/silo/issues/278) 的修复（[多池生命周期过期](/zh/blog/design/multi-pool-lifecycle-expiry/)）时发现的。评估基于 main [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc)，以及 #278 和 #281 的维护者集成分支；保留当时的评估快照。

**状态：** 已随 [SILO Server 20261109](/zh/blog/release/silo-20261109/)（`d998292387cc`）正式发布。

## 简短结论 {#tldr}

缺陷属实，也是 `SILO Server 20261109` 的发布阻塞项。有三种操作会删除一个 key 的"全部版本"：

- 生命周期扩展 `ExpiredObjectAllVersions`；
- 生命周期动作 `DelMarkerExpiration`；
- `purge.retainVersions: 0` 的批量过期，而这正是默认值。

三者都是在磁盘上递归删除该 key 的目录。对象 `a/b` 存放在对象 `a` 的目录里面，所以清除 `a` 时，`a/b`、`a/b/c` 以及所有以 `a/` 开头的 key 都会被一起删除。这些 key 在每个纠删集合、每个池中都会被删，无论它们有多新，也无论是否有任何规则选中它们。这次清除只为 `a` 写一条 ILM 审计记录、发一条桶通知，其他 key 没有任何记录。

同一条路径还有两个问题。第一，它跳过了本应在对象锁内确认过期是否仍然成立的复核，所以 scanner 做出判断之后才写入的版本也会被删掉。第二，它直接丢掉分层版本的元数据，却不留下分层 free version，这些版本的远端对象永远不会被清理。

修复把递归删除替换为：按版本 ID 清除该 key 自身的版本。清除在删除操作已经持有的对象锁内进行，并在锁内读取的版本上重新做一次判断。随后逐个删除这些版本，最旧的先删，最新的最后删，使用磁盘的版本删除；这一操作只在对象目录为空时才删除目录。`SILO Server 20261109` 中，带有已分层版本的 key 会被拒绝，所有内容保持不变。本修改建立在 #278 修复之上（两者修改同一个函数），也建立在[单池锁域修复](/zh/blog/design/single-pool-lock-domains/)之上。

## 定性 {#assessment}

| 维度       | 判断                                                                                                                                                                                                                                                     |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 性质       | "删除全部版本"实现中的数据丢失缺陷。继承自上游 MinIO，存在于每个 SILO 版本中，包括 RELEASE.2026-10-26T00-00-00Z。不是回归。                                                                                                                              |
| 受影响部署 | 所有纠删码部署：一个或多个池、一个或多个纠删集合。开启、暂停或未开启版本控制的桶都受影响。                                                                                                                                                               |
| 受影响操作 | 带 `ExpiredObjectAllVersions` 的 `Expiration`（`mc ilm rule add --expire-all-object-versions`）；`DelMarkerExpiration`；清除时不保留任何版本的批量过期规则；decommission 和 rebalance 在迁移中应用上述规则时。                                           |
| 受影响布局 | 被该操作删除的 key `K`，同时存在其他以 `K/` 开头的 key。这些 key 不需要匹配规则，也不需要已经过期，可以位于其他纠删集合或池中。                                                                                                                          |
| 不受影响   | 目录对象（`K/`），它的元数据与其子对象分开存放。`Kx`、`K-1` 这类兄弟 key。启用了对象锁的桶上的生命周期：这两类规则在配置时被拒绝，在求值时被跳过。其他生命周期动作，它们每次只作用于一个版本。强制删除（`x-minio-force-delete`），它按约定就是前缀删除。 |
| 严重程度   | 致命。没有被任何规则选中的在用对象被永久删除，而且没有任何审计记录、通知或 trace 提到它们。                                                                                                                                                              |
| 可达性     | 普通配置加普通的 key 布局即可触发：一个 key 同时是其他 key 的"文件夹"，例如 `report` 和 `report/page-1`。按默认设置编写的批量过期任务也会触发。                                                                                                          |
| 发布紧急度 | `SILO Server 20261109` 发布阻塞项（已随 `RELEASE.2026-11-09T00-00-00Z` 发布）。                                                                                                                                                                          |
| 剩余工作量 | 已完成；已随 `SILO Server 20261109`（`d998292387cc`）发布。                                                                                                                                                                                              |
{.wide .expand}

## 触发条件 {#trigger}

有三个调用方会向池层请求删除全部版本：

- **过期 worker**，即 `applyExpiryOnNonTransitionedObjects`。它执行 scanner 入队的过期，也执行 GET、HEAD 和列举操作在遇到到期对象时入队的过期。
- **迁移过期**，即 `applyMigrationExpiry`。自 [#276](https://github.com/pgsty/silo/pull/276) 起，decommission 和 rebalance 在遍历中直接调用 worker 的这个函数。
- **批量过期**，即 `batchObjsForDelete`，用于清除时不保留任何版本的规则。

我们在 main 上逐一做了探测。每种布局中，旧 key 已到期，其他 key 都是新的：

| 探测                                                                    | 布局                                                                                                        | main 上的结果                                               |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| scanner 与过期 worker，`ExpiredObjectAllVersions`，一个池、两个纠删集合 | `ea/parent`（两个版本）；`ea/parent/child` 在同一集合；`ea/parent/deep/grandchild` 在另一集合；`ea/parentx` | parent、child、grandchild 被删；`ea/parentx` 保留           |
| 磁盘 scanner 自身的目录遍历，再执行 worker                              | 同样的布局，位于一个集合                                                                                    | 结果相同                                                    |
| 两个池                                                                  | `ea/parent` 在第一个池；`ea/parent/child` 和 `ea/parentx` 在第二个池                                        | parent 和 child 被删；`ea/parentx` 保留                     |
| `DelMarkerExpiration`                                                   | 最新版本为旧删除标记的 `dm/parent`；`dm/parent/child`                                                       | 两者都被删                                                  |
| 未开启版本控制的桶                                                      | `ea/parent`、`ea/parent/child`                                                                              | 两者都被删                                                  |
| 目录对象                                                                | `ea/dir/`、`ea/dir/kid`                                                                                     | `ea/dir/` 被删；`ea/dir/kid` 保留                           |
| 批量过期，规则 `name: bx/parent`，默认清除                              | `bx/parent`、`bx/parent/child`、`bx/parentx`                                                                | parent 和 child 被删；`bx/parentx` 保留                     |
| 带 `ExpiredObjectAllVersions` 的 decommission 和 rebalance              | `obj-01`、`obj-01/child`、`obj-01x`                                                                         | `obj-01` 和 `obj-01/child` 从两个池中消失；`obj-01x` 被迁移 |
{.wide .expand}

在 #278 的集成分支上，这些探测的结果相同。那个修改并不能缓解本缺陷。

## 根因 {#root-cause}

这次删除经过三层，每一层都把它扩大了一些。

1. **调用方请求前缀删除。** 对于 `Action.DeleteAll()`，`applyExpiryOnNonTransitionedObjects` 设置 `DeletePrefix` 和 `DeletePrefixObject`。批量过期设置同样两个标志。
2. **池层丢掉其他选项。** `erasureServerPools.DeleteObject` 对所有 `DeletePrefix` 请求都用 `deletePrefix` 处理。该函数以新建的 `ObjectOptions{DeletePrefix: true}` 调用每个池，因此丢掉了两样东西：
   - `Expiration.Expire`。上游正是为这个动作在 `erasureObjects.DeleteObject` 中加的复核，因此永远不会执行。
   - `DeletePrefixObject`。`erasureSets.DeleteObject` 因此把删除发给每个池的每个纠删集合，并丢弃它们返回的错误。
3. **磁盘删除整个目录。** `erasureObjects.deletePrefix` 在每块盘上以 `Recursive` 和 `Immediate` 调用 `Delete`。在磁盘上，对象 `a` 是目录 `a/`，里面有它的 `xl.meta` 和数据目录；对象 `a/b` 是这个目录里面的 `a/b/xl.meta`。递归删除把整棵目录树移进磁盘的回收区，并立即清除。

目录对象之所以幸免，只是因为 `a/` 被存成 `a__XLDIR__`，位于 `a/` 旁边，而不是里面。

同一条路径还有三个副作用：

- **没有复核。** scanner 的判断可能是几分钟甚至几小时之前做出的。在单池部署上，判断之后才写入的版本会被一起删除，我们复现了这一点。审查 #278 修复时还发现了一个相关情形，我们做了推理但没有探测：在元数据不完整时做出的判断，例如一半磁盘不可读、其余磁盘中又有一块缺少某个新版本，会删除一个已经提交的版本。
- **分层泄漏。** 整体删除 `xl.meta`，会删掉每个已分层版本的记录，包括先前的删除为分层清理留下的 free version。它们的远端对象仍留在分层存储中，却再也没有任何东西引用它们。我们对该 key 及其子对象都复现了这一点。
- **错误被忽略。** 跨纠删集合的扇出删除，即使某个集合删除失败，也会报告成功。

## 行为的来源 {#history}

### 来源追溯 {#provenance}

**这个缺陷来自上游 MinIO。SILO 在分叉时继承了它，并没有引入它。** 分叉点是 [27742d469](https://github.com/pgsty/silo/commit/27742d469462e1561c776f88ca7a1f26816d69e2)（2025-12-03）。缺陷路径上的函数与上游 master（[7aac2a2c5](https://github.com/pgsty/silo/commit/7aac2a2c5b7c882e68c1ce017d8256be2feea27f)，2026-02-12）完全一致：`erasureServerPools.deletePrefix`、`erasureSets.deletePrefix`、`erasureSets.DeleteObject`、`erasureObjects.deletePrefix` 和 `batchObjsForDelete` 与上游相同，`erasureServerPools.DeleteObject` 和 `erasureObjects.DeleteObject` 中的 `DeletePrefix` 分支也相同。生命周期调用方对"删除全部版本"仍使用上游的选项。

缺陷由四个上游要素组合而成。生命周期规则第一次可能删除其他 key 的版本是 `RELEASE.2023-06-29T05-12-28Z`。第一个带有该缺陷的 SILO 版本是 `RELEASE.2025-12-03T12-00-00Z`，也就是第一个 SILO 标签。从它到 `RELEASE.2026-10-26T00-00-00Z` 的全部 18 个 SILO 版本都包含它。

**上游要素。**

| 要素                                                                                                                      | 提交                                                                                                                                                       | 日期和作者                         | 首个上游版本                   |
| ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------ |
| 在每个纠删集合的每块盘上递归删除 key 的目录，经由一个自己重建选项的池层函数。为强制删除而加入，那里删除整个前缀正是目的。 | [7722b91e1](https://github.com/pgsty/silo/commit/7722b91e1dd465c957c014be4077f6d3039e5ee3)、[minio/minio#12504](https://github.com/minio/minio/pull/12504) | 2021-06-16，Anis Elleuch           | `RELEASE.2021-06-17T00-10-46Z` |
| 第一个生命周期调用方：`ExpiredObjectAllVersions` 设置 `DeletePrefix`。同一提交还把对象锁移到了前缀分支之前。              | [aae684641](https://github.com/pgsty/silo/commit/aae684641325e1c37375d455c790e58d902bd7b6)、[minio/minio#17521](https://github.com/minio/minio/pull/17521) | 2023-06-28，Harshavardhana         | `RELEASE.2023-06-29T05-12-28Z` |
| 批量过期：不保留任何版本的清除使用 `DeletePrefix` 删除。最初没有设置 `DeletePrefixObject`，因此会扇出到所有集合。         | [a50f26b7f](https://github.com/pgsty/silo/commit/a50f26b7f56e5e6b1df8a648423736319ecdabd6)、[minio/minio#17946](https://github.com/minio/minio/pull/17946) | 2023-12-02，Krishnan Parthasarathi | `RELEASE.2023-12-02T10-51-33Z` |
| `DelMarkerExpiration`，走同一条路径。                                                                                     | [7926401cb](https://github.com/pgsty/silo/commit/7926401cbd5cceaacd9509f2e50e1f7d636c2eb8)、[minio/minio#19481](https://github.com/minio/minio/pull/19481) | 2024-04-30，Krishnan Parthasarathi | `RELEASE.2024-05-01T01-11-10Z` |
{.wide .expand}

上游中碰过同一批函数、但没有改变其效果的修改：

- [1a884cd8e](https://github.com/pgsty/silo/commit/1a884cd8e)（[minio/minio#13242](https://github.com/minio/minio/pull/13242)，2021-09-17，`RELEASE.2021-09-18T18-09-59Z`）让跨纠删集合的扇出并发执行，并让它丢弃错误。
- [b49fc33cb](https://github.com/pgsty/silo/commit/b49fc33cb)（[minio/minio#15148](https://github.com/minio/minio/pull/15148)，2022-07-11，`RELEASE.2022-07-13T23-29-44Z`）让强制删除立即清除磁盘的回收区。
- [88a89213f](https://github.com/pgsty/silo/commit/88a89213f)（[minio/minio#19231](https://github.com/minio/minio/pull/19231)，2024-03-09，`RELEASE.2024-03-10T02-53-48Z`）让这种清除不再阻塞。
- [6a1558081](https://github.com/pgsty/silo/commit/6a1558081)（[minio/minio#19685](https://github.com/minio/minio/pull/19685)，2024-05-06，`RELEASE.2024-05-07T06-41-25Z`）让单个集合内的磁盘删除返回写仲裁错误。跨集合的扇出仍然丢弃这些错误。

**上游中没有收窄这条路径的修改。** 三个修改都没有生效，因为池层会重建选项：

- [eb55034df](https://github.com/pgsty/silo/commit/eb55034df)（[minio/minio#17827](https://github.com/minio/minio/pull/17827)，2023-08-09，`RELEASE.2023-08-09T23-30-22Z`）加入了 `DeletePrefixObject`。它是为配置删除避免扇出的优化，并不保护其他 key。
- [c61dd16a1](https://github.com/pgsty/silo/commit/c61dd16a1)（[minio/minio#19365](https://github.com/minio/minio/pull/19365)，2024-03-27，`RELEASE.2024-03-30T09-41-56Z`）在扫描器和批量过期中设置了这个标志，同样是"为避免扇出调用"。
- [289223b6d](https://github.com/pgsty/silo/commit/289223b6d)（[minio/minio#19359](https://github.com/minio/minio/pull/19359)，2024-03-27，`RELEASE.2024-03-30T09-41-56Z`）在 `erasureObjects.DeleteObject` 中加入了 `Expiration.Expire` 下的复核。三个修改里只有它以安全为目的，而池层的调用永远走不到它。

**SILO 版本。** 标签 `RELEASE.2025-12-03T12-00-00Z` 到 `RELEASE.2026-10-26T00-00-00Z`（共 18 个）都以上游的形式包含池层和集合层的前缀函数、扫描器与批量过期的调用点，以及磁盘层的删除。

**碰过这条路径的 SILO 提交。** 没有一个改变了前缀删除本身。它们对缺陷的影响：

| 提交                                                                                                                                                                                                                                                                                                                                                                         | 日期和作者                                              | 发布于                                                           | 影响                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [40bee4b7b](https://github.com/pgsty/silo/commit/40bee4b7b)、[e59a3d938](https://github.com/pgsty/silo/commit/e59a3d938)                                                                                                                                                                                                                                                     | 2026-09-06 和 2026-09-11，Feng Ruohang                  | `RELEASE.2026-09-16T00-00-00Z`                                   | 无。在 `erasureServerPools.DeleteObject` 的 `DeletePrefix` 一带，它们只改了对象锁上方的注释。其余改动（条件删除、跨池串行化）都在该分支之后。                                                                                                                                                                                                                      |
| [1cf529ce8](https://github.com/pgsty/silo/commit/1cf529ce8)、[eb4f5e5b3](https://github.com/pgsty/silo/commit/eb4f5e5b3)、[60c7179dd](https://github.com/pgsty/silo/commit/60c7179dd)、[a30270d9b](https://github.com/pgsty/silo/commit/a30270d9b)、[3c82748e1](https://github.com/pgsty/silo/commit/3c82748e1)、[a2073d251](https://github.com/pgsty/silo/commit/a2073d251) | 2026-09-15 至 2026-10-24，Feng Ruohang 和 Denis Babchuk | `RELEASE.2026-09-16T00-00-00Z` 至 `RELEASE.2026-10-25T00-00-00Z` | 无。它们改的是 `erasureServerPools.DeleteObject` 和批量删除的其他部分（跨池版本删除的协调、数据迁移、删除标记的放置、分层引用）。`DeletePrefix` 分支在这些代码之前就已返回。                                                                                                                                                                                       |
| [1748f62c7](https://github.com/pgsty/silo/commit/1748f62c7)                                                                                                                                                                                                                                                                                                                  | 2026-10-18，Feng Ruohang                                | `RELEASE.2026-10-18T00-00-00Z`                                   | 收窄了一个调用方。下线和再平衡原先像上游一样，用前缀删除把已搬走的 key 从源池移除；现在改为按版本 ID 移除已搬走的版本。该提交声明的目的是并发安全。                                                                                                                                                                                                                |
| [7a060cab1](https://github.com/pgsty/silo/commit/7a060cab1)、[374de0fa3](https://github.com/pgsty/silo/commit/374de0fa3)、[9b76a2167](https://github.com/pgsty/silo/commit/9b76a2167)                                                                                                                                                                                        | 2026-08-15、2026-09-08、2026-09-15                      | 未发布                                                           | 一个按访问频率搬迁对象的功能曾加入一个对精确 key 使用前缀删除的调用方，随后改为按版本寻址的删除，最后被回退。`RELEASE.2026-09-16T00-00-00Z` 标签不含其中任何内容。                                                                                                                                                                                                 |
| [0a546c7a7](https://github.com/pgsty/silo/commit/0a546c7a7)，随 [#276](https://github.com/pgsty/silo/pull/276) 合并于 [0fc5a0b52](https://github.com/pgsty/silo/commit/0fc5a0b52)                                                                                                                                                                                            | 2026-11-02，Feng Ruohang                                | `RELEASE.2026-11-09T00-00-00Z`（与本精确 key 修复一并发布）      | 本修复前曾在 `main` 上扩大暴露面。下线和再平衡把"删除全部版本"的动作交给 `applyExpiryOnNonTransitionedObjects`，等于给缺陷路径增加了一个调用方，同时未改动删除全部版本的选项。在它之前的 [19910230a](https://github.com/pgsty/silo/commit/19910230a) 和 [a995921e5](https://github.com/pgsty/silo/commit/a995921e5) 在迁移期间只执行针对单个版本的动作，没有扩大。 |
{.wide .expand}

因此，这个缺陷不是任何已发布 SILO 版本中的回归。唯一扩大其触发面的 SILO 改动（#276）已与本精确 key 清除修复一并随 `SILO Server 20261109` 发布。

**由 git 历史确认、未实际运行：** 引入提交、它们的日期和各自首个上游版本，上面所列函数与上游 master 逐字节相同，以及每个 SILO 版本的内容。没有把每个要素提交对应的版本重新构建并运行。

**背景。** 上游 master 仍是同样的代码。在 SILO 中，#276 让迁移遍历立即执行这类过期。

## 方案比较 {#options}

### 方案 A：在磁盘层做"精确对象"删除 {#option-a}

新增一个磁盘操作：删除 `xl.meta` 及其引用的数据目录，然后仅在对象目录为空时删除该目录。

- 它能保护子对象。
- 它会删除磁盘上持有的所有版本，包括判断之后写入的版本，以及 quorum 视图中缺失的版本。它仍然需要复核；而且除非接收一个版本列表，否则无法只删除已判定的版本。真到了那一步，它就是现有的 `DeleteVersions` 调用。
- 为了避免分层泄漏，磁盘层必须自己写 free version，这和版本删除路径已经做的事重复。
- 它需要一个新的存储调用。在现有 `Delete` 调用上加新标志是不安全的：旧节点解码 `DeleteOptions` 时会跳过未知字段，滚动升级期间它们会在自己的磁盘上执行递归删除。

不采纳：存储层代码更多，有升级风险，而且仍然需要方案 B 的逻辑。

### 方案 B：按 ID 清除该 key 自身的版本 {#option-b}

这是推荐的方案。

- **子对象。** 版本删除路径（`xlStorage.deleteVersions`）会改写或删除 `xl.meta`，并把每个被删版本的数据目录移入回收区。它只在对象目录为空时才删除该目录，所以其他 key 不受影响。我们用现有批量路径做了原型：删除了一个 key 的全部四个版本，其中有一个删除标记和一个分层版本，两个纠删集合中的子对象都完好无损。
- **分层版本。** `xlMetaV2.DeleteVersion` 会为每个已分层的版本加一个 free version。原型留下了一个，之后由 scanner 的 free version 清理删除远端对象（见 [Tier free version 是内部清理记录](/zh/blog/design/tier-free-version-semantics/)）。
- **对象锁。** 生命周期在启用对象锁的桶上会在配置时拒绝这两类规则，并在求值时跳过它们，清除不改变这一点。由于清除按版本 ID 删除，它可以在这一处逐版本执行保留期和 legal hold 检查，原语会检查将被删除的每个物理修订。批量作业提交者的授权由调用方另行检查。
- **复制。** "删除全部"仍然是本地清除：删除版本时不带复制状态，不创建删除标记，也不入队任何复制，与现在相同。
- **Quorum 与部分历史。**
  - 清除只删除它判定过的版本。quorum 视图中缺失的版本会保留，由 heal 去协调。
  - 写 quorum 失败时，key 保持原样，下一轮扫描会重试。
  - 当一个很长的版本列表分成多次调用时，先删最旧的版本，最新版本最后删，所以部分完成的清除不会改变当前版本，也不会暴露更旧的版本。
- **多池。** 同一个版本列表发给每个池中该 key 所在的纠删集合。不持有某个版本的池会回答"不存在"，批量路径对物理删除接受这个回答。扇出到所有纠删集合的做法不再需要。
- **代价。** 每个池中一个集合的每块盘，做一次 `xl.meta` 的读-改-写，每个版本再做一次数据目录重命名，都在对象锁内完成。历史很长时分成多次调用。
- **滚动升级。** 清除使用现有的 `DeleteVersions` 调用，没有新的传输字段，也不改存储格式。
- **#278 的检查。** 合并检查已经在锁内读取所有池中的版本并对规则求值。清除可以直接使用这个列表，而不只是一个"是/否"的结果。

设计审查修改了这个方案的三处，结果见[修复方案](#fix)。批量路径会重新排列一个 key 的版本，而且池与池之间没有屏障：在一次两池探测中，较旧版本的删除失败了，它却删掉了最新的删除标记，随后的读取返回了那个较旧版本。所以清除改为一次删除一个版本。仅靠 free version 在这里不能保证分层 key 的安全：free version 会把远端对象交给分层清理，而审查发现，另一个池中的副本，或一次没有达到 quorum 的删除，仍可能引用那个对象。所以带有已分层版本的 key 一律拒绝。此外，重复副本和 `null` 写入会重复使用同一个版本 ID，所以清除在删除任何东西之前，先记录每个池中的每个副本。

### 方案 C：`K/` 下还有其他 key 时拒绝执行 {#option-c}

在清除前列举一条 `K/`，发现其他 key 就跳过。

- 存在竞争：列举之后才写入 `K/` 下的 key 仍会被删，因为 `K` 上的锁并不串行化对 `K/child` 的写入。
- 规则对这类 key 永远不再生效，而且没有任何提示。
- 每次清除都要付出一次跨所有纠删集合的列举。
- 分层泄漏和缺失的复核依然存在。

不采纳。

### 方案 D：保留前缀删除，但把 `Expire` 和 `DeletePrefixObject` 传下去 {#option-d}

这样能恢复复核：带上这些选项后，集合级删除拒绝了判断之后写入的版本。但它保护不了子对象：与该 key 位于同一纠删集合的子对象仍会被删，位于其他集合的子对象则幸存。丢失与否将取决于哈希，分层泄漏也依然存在。

不作为修复方案。它的复核部分纳入方案 B。

## 修复方案 {#fix}

以下是经过两轮设计审查确定、并在已审查的补丁中实现的设计。

1. **专用选项。** 过期 worker、迁移过期和批量过期通过一个新的内存选项 `ObjectOptions.DeleteAllVersions` 请求清除，不再设置 `DeletePrefix` 和 `DeletePrefixObject`。`DeletePrefix` 保持原有含义，留给强制删除，以及确实要删除前缀的内部调用方。该选项与 `DeletePrefix`、版本 ID、数据迁移或任何会创建删除标记的选项同时出现时会被拒绝。池层以下的每一层也都拒绝它，所以路由错误的请求不会变成另一种删除。
2. **在锁内基于历史做判断。** `erasureServerPools.DeleteObject` 拿到对象锁后，立即把请求交给清除，在 #278 检查之前，单池部署也一样。
   - 生命周期：原样使用 `lifecycleEventsAllPools`，在该 key 于所有池中的版本上对规则求值。只有最新版本仍带有"删除全部"事件时才执行清除。
   - 批量过期没有规则可以求值。最新版本必须仍是遍历时匹配到的那个版本，按版本 ID（空 ID 视为 `null`）和修改时间比较。否则该 key 报告为未过期，也不再重试。
   - 对每个池的权威历史再读一次，记录每个被认可的版本在哪里：每个副本，包括同一 ID 的较旧写入，例如在多个池中写入的 `null` 版本。这次读取只能确认认可的结果，绝不增加版本。只要有任何差异，或磁盘无法给出完整历史，就返回 `InsufficientWriteQuorum`，不删除任何东西。没有版本的 key 视为成功，不删除任何东西。
3. **删除任何东西之前检查每一次写入。**
   - 清除在每个池中该 key 所属集合的每块盘上读取 `xl.meta`，包括 quorum 视图中没有副本的池。少数磁盘可能持有与历史所认可的不同的版本修订，所以每块盘上每个被认可版本的每个修订都要检查。无法读取的磁盘可能藏着这样的修订，而 heal 之后会删除清除留在它上面的内容，所以只要有一块盘无法读取，整个 key 就被拒绝。之后清除只在它读取过的那些磁盘句柄上删除；之后因重连而换上的句柄不会被使用。
   - 只要任一版本的任一修订已分层，整个 key 就被拒绝。见[分层 key](#tiered)。
   - 清除对它将要删除的每一次写入执行保留期和 legal hold 检查。只要有一个修订受保护，整个 key 就被拒绝。
4. **按版本 ID 依序删除。**
   - 一次一个版本，最旧的先删。在持有副本的每个池中，于该 key 所在的纠删集合、在检查过的磁盘上使用磁盘的版本删除（`DeleteVersion`）。这个调用改写 `xl.meta`，把该版本的数据目录移入回收区，只在对象目录为空时才删除目录。删除不写删除标记、不写复制状态，也不产生 free version。
   - 对每个版本，先删较旧的写入，最后删读取会选中的那个副本。
   - 最新版本最后、单独删除，并且只在每个较旧版本都已从每个池中删除之后。所以中途停止的清除既不会改变读取结果，也不会暴露更旧的版本。
   - 遇到第一个错误就停止。一次删除如果达到了写 quorum、但在部分磁盘上失败，会在仍持有锁时对这些磁盘重试有限次数；剩下的交给 heal。
   - 每次调用的预算是 1000 个版本和一分钟，包括其中的读取和检查，在每个版本之前检查。更长的历史会在最新版本之前停下，由下一次过期继续，届时重新读取历史、重新做判断。
5. **报告删除了什么。** 清除统计它删除的逻辑版本数：包括删除标记，不包括重复副本和 free version；并返回认可的最新版本。ILM 审计记录在标签 `ilm-versions-removed` 中带上这个数。开始删除之后失败或停止的清除记为部分完成（标签 `ilm-partial`），带上已删除的数量和错误，自 `SILO Server 20261109` 起还带上标签 `ilm-incomplete-reason`；即使只删除了副本、没有删完任何一个版本也是如此；它以 `result=partial` 写入 trace，不发送删除通知。因为该 key 没有可删除的内容而什么都没删除的清除，不发送删除通知，只写一条普通 trace。在删除任何东西之前就被拒绝的生命周期清除（有分层版本、规则已不适用、Object Lock）会计数，并以 `result=refused`、原因和错误写入 trace，不写审计。在删除任何东西之前就失败的（历史无法读取或其他错误）还会写审计并记录日志。`expiry_incomplete_total` 中的原因有 `tier_unsupported`、`budget`（取得进展后在预算处停止）、`changed`（批量作业匹配到的最新版本已改变）和 `history_unavailable`，以及与其他过期共用的 `not_applicable`、`locked` 和 `error`；见[多池生命周期过期](/zh/blog/design/multi-pool-lifecycle-expiry/#fix)。批量过期按清除的结果统计对象和删除标记；未能删除某个删除标记的作业报告为失败。

### 分层 key {#tiered}

`SILO Server 20261109` 不对带有已分层版本的 key 执行整 key 物理清除。

- 过期 worker 仍把最新版本已分层的"删除全部"交给 `expireTransitionedObject`。它写一个删除标记，把所有版本和远端对象都留在标记下面，之后的扫描也不会再删除它们。
- 最新版本在本地、但较旧版本已分层的 key 会被拒绝，不删除任何东西。自 `SILO Server 20261109` 起，持有这种分层版本的池，其 scanner 不再把清除排入队列：每个盘的 scanner 每一轮把这次跳过计为一次 `tier_unsupported_skipped`。只有其他池持有的分层版本，这个 scanner 并不知道，所以仍由清除来判断，并以 `tier_unsupported` 拒绝该 key，同时写入日志；同一 key 重复出现的相同拒绝由去重日志抑制，直到它每小时重置。批量过期把该 key 计入 `keysRefused`（状态 `complete-with-skips`，[`07b89b98f`](https://github.com/pgsty/silo/commit/07b89b98f)），本次运行内不再重试。自 `SILO Server 20261109` 起，下线或再平衡在 tier 证据排除整 key 过期时，会正常迁移存活版本及其 tier 元数据。迁移第一个版本之前，先收集所有池和磁盘上的 tier 证据，防止获胜的本地副本隐藏已分层的重复副本或少数盘修订。最终仍检查物理残留，不能把仍有数据的池报告为完成。

分层安全的清除，不能在任何副本仍引用某个远端对象时（包括一次删除没有达到 quorum 之后）把它交给分层清理。这需要持久的清理记录和锁内的证明，属于单独的修改。

### 协调 {#coordination}

- **#278 修复。** 本修改建立在 #278 的提交之上，原样使用它的辅助函数：用 `lifecycleEventsAllPools` 做判断，用 `objectVersions` 读取各池的历史。清除在合并检查之前执行，所以既不需要 `CheckedAllPools`，也不需要单池豁免。
- **单池锁域修复。** 在单池上，一个 key 的写入在它自己的纠删集合中加锁，而 `DELETE` 在第一个集合中加锁，见[大型单池集群的锁域](/zh/blog/design/single-pool-lock-domains/)。清除在 `DELETE` 的锁内做判断并删除，所以只有在那个修复合入之后，它才与该 key 的所有写入互斥。那个修复先合入，本修改在它之上 rebase。清除本身不增加任何加锁。

## 为什么方案充分且必要 {#sufficiency}

**充分性。** 所有"删除全部"都会到达 `erasureServerPools.DeleteObject`，包括过期 worker 及其所有入队方（scanner、GET、HEAD、列举）、迁移过期和批量过期。有了专用选项，它们都不会再走到递归删除：

- 版本删除只触及该 key 自身的 `xl.meta` 和数据目录。子对象有自己的 `xl.meta`，对象目录只在为空时才删除。
- 复核在串行化该 key 写入的同一把锁内进行，使用与 scanner 相同的求值器，所以不再成立的判断不会删除任何东西。
- 只删除认可的列表，可以保留 quorum 视图没有看到的版本。
- 最新版本最后删除，所以在每个较旧版本都删除之前，读取结果保持不变。
- 拒绝带有已分层版本的 key，所以每个远端对象都仍被引用。

**必要性。** 每一部分都关闭一条否则会继续存在的路径：

- 没有精确清除，子对象会被删除；方案 D 表明，即使只在一个集合内做前缀删除，也会丢失子对象。
- 单池部署上没有复核，判断之后写入的版本会被删除。
- 不把删除限制在认可的列表内，quorum 视图中缺失的版本会被删除。
- 没有删除顺序和最新版本之前的屏障，一个池中的删除失败会暴露更旧的版本。
- 没有分层拒绝，远端对象会泄漏，或者分层清理会删除仍被某个副本使用的远端对象。
- 没有批量过期和迁移的改道，这些调用方仍走前缀路径。
- 没有专用选项，设置旧标志的调用方就会再次走到前缀路径。`DeletePrefixObject` 在这条路径上多年来一直没有生效，却没有人注意到。自 `SILO Server 20261109` 起，池层还会把同时带 `DeletePrefix` 和 `Expiration.Expire` 的请求以 `InvalidArgument` 拒绝，所以生命周期过期绝不会删除前缀。强制删除（不带过期的 `DeletePrefix`）不变。

**有意排除的范围：**

- 强制删除和 speedtest 清理保留前缀删除，这是它们的约定。
- 内部配置删除（`deleteConfig`、`delServerConfigHistory`）在系统桶上走同样的递归路径。要发生冲突，需要一个配置名以 `/` 延续另一条记录的文件名，例如一个 IAM 用户的名字以另一个用户的名字加 `/identity.json/` 开头。我们在配置层确认了这个机制，但没有检查管理 API 是否接受这样的名字。严重程度低，可以在后续修改中让这些删除也改用同一个精确清除。

## 代价与兼容性 {#cost}

- 不改变 API、配置、存储格式或传输格式。新增的选项只存在于内存中。
- 每次"删除全部"，清除在每个池中读取该 key 所在集合的 `xl.meta` 三次：用于判断、用于记录位置，以及检查每块盘。之后对每个版本，持有副本的每个集合的每块盘做一次 `xl.meta` 读-改-写和一次数据目录移动。现在的删除则是在每个集合的每块盘上做一次递归删除。大集群的工作量会减少；历史很长的 key 工作量更大，持有对象锁的时间也更长，但每次调用最多持续一个预算。
- 回收区改为后台清除而不是立即清除，空间回收会稍晚一些。
- 判断已不成立的"删除全部"现在不做任何事，单池也一样；scanner 会在后续轮次重试。
- 滚动升级是安全的，因为只使用现有的存储调用。但只有当每个执行过期的节点都运行了修复，保护才完整：执行过期的节点决定如何删除，所以混合版本集群中的旧节点仍会做递归删除。在所有节点都升级之前，请保留临时缓解措施。
- **用量与配额。** scanner 现在按实际大小统计处于"删除全部"之下的 key 的每个版本，无论是否已排入队列，而不再当作已经删除。用量以及硬配额，要在清除成功之后、对该 key 的子树重新扫描一次才会下降；这可能要等到 scanner 的目录扫描间隔，而不是一轮。关于版本过多和版本过大的告警，也会计入 scanner 没有排入队列的 key 的版本。
- 回滚即恢复旧行为，两个方向都不需要迁移。

## 剩余限制 {#limits}

- **已经发生的丢失不会被修复。** 递归删除会立即清除回收区，磁盘上实际上无法撤销。
- **已成孤儿的远端对象会保留。** 分层存储中已经成为孤儿的远端对象仍然留在那里。它们与 key 的对应关系记录在已被删除的元数据中，所以只能手工清理。
- **分层 key 不会被清除。** 见[分层 key](#tiered)。
- **"删除全部"要等每块盘都可用。** 只要该 key 所在纠删集合中有一块盘离线、无法读取该 key，或其上该 key 的 `xl.meta` 无法解码，清除就以 `history_unavailable` 拒绝该 key，由 scanner 在之后的轮次重试。调用方看到的仍是写 quorum 错误（`503`）。这是在删除任何东西之前检查每一个修订的代价。
- **CRC 损坏必须先成功 heal，再执行清除。** `SILO Server 20261109` 把 `xl.meta` 校验和失败归类为存储损坏，存储 RPC 的错误转换也保留这一类别。当某块盘无法解码导致磁盘检查被拒绝，或在历史读取阶段有一半磁盘无法解码（[`7a13780d8`](https://github.com/pgsty/silo/commit/7a13780d8)）时，被拒绝的清除会为可解码磁盘上观察到的每个版本排入 MRF heal；null 版本使用明确的 `null` ID。普通和深度对象 heal 可以从足够的存活副本重建损坏元数据，后续清除再重试。dry-run 不改写元数据；没有元数据 quorum 时，heal 保留原文件，清除继续拒绝。其他无法解码的元数据错误不保证能通过同一路径修复。
- **磁盘句柄指向一块盘，而不是一个后端。** 清除在它检查过的磁盘句柄上删除，但每次存储调用都会在承载该盘的节点上重新解析后端。清除运行期间替换某块盘的后端一开始是空的，只会通过该 key 的写入或 heal 得到它，而两者都要先拿到清除持有的对象锁。以 `nolock` 启动的管理端 heal 会跳过这把锁；那个选项是单独的问题。
- **对象 key 之下的 key 不会被列出。** 列举不会进入一个对象 key 的目录，所以只要 `K` 存在，`K/child` 就不出现在列举结果、批量过期的遍历，以及下线和再平衡的遍历中。这比本修复更早就存在。修复之后，下线或再平衡执行的 `K` 的"删除全部"会保留 `K/child`，但遍历已经越过了它。第一轮会把它报告为遗留对象，这与没有任何生命周期规则时相同（已执行）；之后的一轮会迁移它。
- **数据目录被递归删除。** 每一次版本删除（不只是"删除全部"）都会把该版本的数据目录连同其内容一起移入回收区。一个名为 `K/<data-dir>/...` 的 key，若 `<data-dir>` 恰是 `K` 某个版本的内部数据目录 ID，就会随该版本一起被删除。S3 API 不返回这个 ID，构造这样的名字需要内部元数据。这属于存储层的后续工作。
- **旧格式对象不在覆盖范围内。** 在最早期纠删格式的磁盘上，仍以 `xl.json` 存储的对象，每次删除版本都是递归删除，不只是"删除全部"时。这一点来自代码推理，没有探测。
- **批量过期的复核很有限。** 批量过期只能确认最新版本仍是它匹配到的那个版本。
- **混合版本。** 见[代价与兼容性](#cost)：执行过期的旧节点仍会递归删除。

## 20261109 之前版本的运维指引 {#operators}

**确认是否暴露。**

- 生命周期：运行 `mc ilm rule export ALIAS/BUCKET`，查找已启用、且包含 `"ExpiredObjectAllVersions": true` 或 `DelMarkerExpiration` 的规则。
- 批量过期：运行 `mc batch list ALIAS --type expire` 和 `mc batch describe ALIAS JOB-ID`，查找没有设置 `purge.retainVersions`、或设置为 `retainVersions: 0` 的规则。
- key：在这些桶中（或在规则的前缀下），列出所有 key，包括各个版本和删除标记，然后打印出那些是其他 key 路径前缀的 key：

  ```sh
  mc ls --recursive --versions --json ALIAS/BUCKET | jq -r '.key' | sort -u > keys.txt
  awk 'NR == FNR { k[$0]; next }
       { n = split($0, p, "/"); a = p[1]
         for (i = 2; i <= n; i++) { if (a in k) print a " -> " $0; a = a "/" p[i] } }' keys.txt keys.txt
  ```

  输出 `a -> a/b` 表示对 `a` 执行"删除全部"时也会删除 `a/b`。右侧以 `/` 结尾的是目录对象，它不受影响。

**在所有节点升级到 `SILO Server 20261109` 或更高版本之前的缓解措施。**

- 用 `mc ilm rule edit --id RULE-ID --disable ALIAS/BUCKET` 停用受影响的规则，或从规则中删除对应元素。
- 仍然需要这类策略时，改用按版本执行的规则：
  - 开启版本控制的桶，用 `Expiration` `Days`，加上 `NoncurrentVersionExpiration` `NoncurrentDays` 和 `ExpiredObjectDeleteMarker`；
  - 未开启版本控制的桶，只用 `Expiration` `Days`。

  这些规则按版本删除，不走递归路径（代码推理），只是全部删完所需的时间更长。在 `SILO Server 20261109` 之前的多池部署上，在所有节点升级到 `20261109` 之前它们仍受 [#278](/zh/blog/design/multi-pool-lifecycle-expiry/) 影响。
- 前缀或标签过滤只有在排除父 key 时才有用。只要过滤仍然选中 `a`，就仍会删除 `a/b`，因为子对象不需要匹配规则。
- 不要在存在这类 key 的桶上运行默认清除的批量过期任务，正在运行的用 `mc batch cancel` 取消。`retainVersions` 为 1 或更多时按版本删除（推理），但会保留相应数量的版本。

**排查已经发生的丢失。**

- 如果配置了审计日志，查找 API 名为 `ILMExpiry`、且标签 `ilm-action` 为 `DeleteAllVersionsAction` 或 `DelMarkerDeleteAllVersionsAction` 的记录。桶通知 `s3:ObjectRemoved:DeleteAllVersions` 和 `s3:LifecycleDelMarkerExpiration:Delete` 包含相同的信息。每条记录只提到父 key 和规则；被连带删除的 key 没有任何审计记录、通知或 trace。
- 批量过期的任务状态和批量 trace，只统计、列出规则匹配到的 key。
- 对这样找到的每个父 key `K`，比较事件发生前 `K/` 下的 key 与现在的情况。之前的列表可以来自清单、备份、应用自身的记录或复制目标。一个已经不存在、又没有自己删除记录的 key，很可能就是被本缺陷删除的。
- "删除全部"不会被复制，所以桶复制的目标可能仍保有这些 key，除非目标端运行了同样的规则。站点复制的对端共享生命周期配置并自行执行，因此可能也丢失了同样的 key（推理）。

## 验证 {#verification}

**修复，已执行。** 在修复上，以及在一个位于 [9f7b49369](https://github.com/pgsty/silo/commit/9f7b49369)、只加入新测试的一次性 worktree 上，用 `-p 2` 运行有针对性的 `go test -run` 选择。下面每个回归测试在该基线上失败、在修复上通过。新测试在 race 检测下通过。

- 生命周期"删除全部"之后，位于该 key 自身纠删集合、另一个集合以及更深层级的子对象都保留了全部版本，`ExpiredObjectAllVersions` 和 `DelMarkerExpiration` 都是如此。位于另一个池的子对象（该 key 在两个池中都有副本），以及批量过期清除也一样；批量过期的计数来自清除结果。
- 下线和再平衡删除到期的 key，并保留它的新子对象。
- 位于目录对象 `ea/dir/` 目录中的 `ea/dir__XLDIR__/odd`，在清除 `ea/dir/` 后仍保留。
- 在单池上，scanner 判断之后写入的版本会保留。批量清除匹配到的版本已不是最新版本时，不删除也不计数。
- 在单池上，一半磁盘无法读取时，对这样的历史执行过期不删除任何东西。
- 一个在两个池中都写入过的 `null` 版本，较新的写入无法删除时，记为部分完成、已删除 0 个版本，因为已经删除了一个副本。
- 批量清除删除了较旧版本、但最新的删除标记删除失败时，该标记计为失败，作业也报告为失败。
- 两个池、三个版本：中间版本删除失败时，最旧的版本已删除，最新版本保留且仍是读取结果，审计 trace 标记为部分完成、已删除一个版本，并且不发送删除通知。故障消失后，下一次过期完成清除，并为两个版本发送一条通知。
- 两个版本的预算让一个四版本的清除停在最新版本之前，报告部分进度，下一次过期完成它。
- 最新版本在本地而较旧版本已分层的 key，以及批量清除中最新版本已分层的 key，都被拒绝，所有版本和远端对象都保留；批量过期把它们计入 `keysRefused`（`complete-with-skips`）。
- 受保留期或 legal hold 保护的写入会使整个 key 被拒绝，包括另一个池中受保护的较旧 `null` 写入。
- 十六块盘中只有一块盘上的修订已分层或带 legal hold，整个 key 也会被拒绝，尽管被认可的修订两者都不是。一块无法读取的盘上带 legal hold 的修订，以及一块没有任何保护但无法读取的盘，也都会使 key 被拒绝。
- 检查之后替换了已检查句柄的新磁盘句柄不会收到任何删除。
- 预算为 10 毫秒且元数据读取很慢时，清除在第一次删除之前就停止。
- 一个在两个池中都写入过的 `null` 版本：较新的写入无法删除时，较旧的写入已删除，读取仍返回较新的写入。一个版本在两个池中的两个副本，计为一个被删除的版本。
- 之前删除分层版本时留下的 free version 会保留。
- 该选项与每个冲突选项同时出现时会被拒绝，池层以下各层也拒绝它。不存在的 key 视为成功，不删除任何东西。
- 在两边都通过的对照：没有子对象的 key 执行"删除全部"后所有版本都被删除；`ea/plainx` 和 `ea/plain-1` 保留；目录对象 `ea/dir/` 被删除而 `ea/dir/kid` 保留；强制删除仍删除整个前缀；最新版本已分层时仍得到一个删除标记；在两个池上，过时的判断仍被拒绝。
- `./cmd` 中现有的生命周期、过期、批量、ILM、删除、下线和再平衡测试，以及 `./internal/bucket/lifecycle`，在修复上通过。

**缺陷，已执行。** 所有运行都使用位于 main `69fcf50cd` 的一次性 worktree，以及 `-p 2` 的有针对性 `go test -run` 选择，没有使用 race 检测。

- **直接调用。** 用 scanner 的选项对 `eav-parent` 调用 `DeleteObject` 执行"删除全部"，会删除 `eav-parent/child`，保留 `eav-parentx`。
- **scanner 与过期 worker。**
  - 通过 `scannerItem.applyActions` 和真实过期 worker 应用生命周期，得到[上表](#trigger)中的结果：一个池两个纠删集合、`DelMarkerExpiration`、未开启版本控制的桶，以及目录对象。
  - 磁盘 scanner 自身的目录遍历（`NSScanner`）为父对象入队"删除全部"，worker 随后删除了它的子对象。
- **其他调用方。**
  - 两个池：第二个池中的子对象被删除。
  - 通过 `BatchJobExpire.Start` 启动的批量过期作业，删除了其规则所指定 key 的子对象。
  - 下线和再平衡把到期的 key 和它的新子对象从两个池中都删除了。
- **副作用。**
  - 该 key 及其子对象的分层版本留下远端对象，没有元数据，也没有 free version。之前删除留下的 free version 也被清掉。
  - 单池上，scanner 判断之后写入的版本被删除。直接用 `Expire` 和 `DeletePrefixObject` 调用集合级删除时，它会被拒绝。
  - ILM trace 只有一条过期记录，只针对父对象。
  - 对象层接受 `ea/dir__XLDIR__/odd`，它随目录对象 `ea/dir/` 一起被删除。
  - 保存两条配置记录，一条位于另一条的路径之下；删除外层记录时，内层记录也被删除。
- **最新版本已分层。** "删除全部"写一个删除标记，保留两个版本和远端对象，下一轮扫描不再入队任何操作。
- **方案 D。** 恢复选项后的集合级前缀删除，删除了与该 key 同一集合的子对象，保留了另一个集合中的子对象。
- **方案 B 原型。** 通过现有批量路径按 ID 删除该 key 的版本，所有子对象都保留，并为分层版本留下一个 free version。
- **#278 集成分支。** 单池、两池、迁移以及单池过时判断的探测丢失了同样的 key。两池的过时判断在那里被拒绝。

**来自代码推理，未执行：**

- 缺陷路径上的审计记录和通知只针对父对象：它们与产生那唯一一条 trace 的调用点相同；
- GET、HEAD 和列举通过同一个 worker 入队"删除全部"；
- 跨纠删集合的扇出会丢弃各集合的错误；
- 旧节点会跳过未知的 `DeleteOptions` 字段；
- 逐版本的生命周期规则，以及 `retainVersions` 为 1 或更大的批量清除，不会走到递归路径；
- 复制目标保留了被删除的 key；
- #278 审查中发现的元数据不完整的变体；
- 旧格式 `xl.json` 的行为；
- 回收区的立即清除。

**初始工作树阶段未单独运行：**

- 跨独立主机的混合版本滚动升级验证。

**集成与发布验证。** 该修复为 `SILO Server 20261109` 合入集成分支，位于 #278 和 #281 之后，与单池锁域、Heal 演练、#259、#285 和 Console 修复无冲突合并。本地集成运行通过了完整的 `go test -tags kqueue,dev -p 4 ./cmd/... ./internal/...` 套件与 CI 竞态检测选集，针对组合分支的对抗性审查通过实际执行的探针检查了锁域、清理路径以及清除与恢复之间的交互，未发现缺陷。发布提交 `d998292387cc`（`RELEASE.2026-11-09T00-00-00Z`）已通过 Go CI（含无标签 Ubuntu `CGO_ENABLED=0 MINIO_API_REQUESTS_MAX=10000 go test ./cmd/ -count=1 -timeout 30m` 门禁）、VulnCheck、发布流水线测试与发布构建校验。

## 审查记录 {#review}

| 轮次            | 结果                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| --------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 设计第 1、2 轮  | 同意并要求修改。批量路径会重排版本，池与池之间也没有屏障，所以清除改为一次删除一个版本，最旧的先删，最新的最后且单独删除。仅靠 free version 不能保证分层 key 的安全，所以带有已分层版本的 key 一律拒绝，分层对象的"删除全部"推迟处理。为每个副本记录位置，对每次写入执行保留期和 legal hold 检查，在锁内有限次重试，每次调用有预算，报告只统计确认的删除。单池上的写入互斥交给先合入的锁域修复。每次版本删除都会递归删除数据目录，这一点留给存储层的后续工作。 |
| 补丁审查第 1 轮 | 要求修改。五个问题：少数磁盘上已分层或带 legal hold 的修订没有被检查；删除了副本却没有删完任何一个版本的清除没有记为部分完成；时间预算没有包括读取和检查；批量作业的完成状态忽略了删除失败的删除标记（这是更早就存在的判断，被新的计数暴露出来）；一个测试夹具缺少删除标记计数。全部采纳，并加了回归测试。                                                                                                                                                     |
| 补丁审查第 2 轮 | 要求修改。三个问题：无法读取的磁盘可能藏着受保护的修订，之后会被 heal 删除；磁盘选择被应用到一组新取得的句柄上；清除在已经知道达不到写 quorum 时仍会开始删除。全部采纳：无法读取的磁盘现在会使 key 被拒绝，清除只在它检查过的那些句柄上删除。                                                                                                                                                                                                                  |
| 补丁审查第 3 轮 | 要求修改。一个问题：保留下来的句柄并不能锁定承载该盘的节点上的后端。有异议：替换后的后端一开始是空的，只会通过在清除持有的对象锁下进行的写入或 heal 得到该 key；而要绑定后端的具体实例，需要改变传输格式。                                                                                                                                                                                                                                                     |
| 补丁审查第 4 轮 | 批准，附带小问题。审查方撤回了第 3 轮的问题。两处小问题：把磁盘选择描述为磁盘句柄，并写明替换与加锁的前提；点名管理端 heal 的 `nolock` 选项是例外。均已采纳，分别写入代码注释和[剩余限制](#limits)。                                                                                                                                                                                                                                                           |
{.wide .expand}
## 参考 {#references}

- 评估基线：[69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc)
- 相关修复与记录：[#278](https://github.com/pgsty/silo/issues/278)、[多池生命周期过期](/zh/blog/design/multi-pool-lifecycle-expiry/)
- 迁移过期：[#276](https://github.com/pgsty/silo/pull/276)、[ILM 过期与存储池迁移顺序](/zh/blog/design/ilm-migration-ordering/)
- 分层清理：[Tier free version 是内部清理记录](/zh/blog/design/tier-free-version-semantics/)
- 上游历史：[minio/minio#12504](https://github.com/minio/minio/pull/12504)、[minio/minio#17521](https://github.com/minio/minio/pull/17521)、[minio/minio#17827](https://github.com/minio/minio/pull/17827)、[minio/minio#17946](https://github.com/minio/minio/pull/17946)、[minio/minio#19359](https://github.com/minio/minio/pull/19359)、[minio/minio#19365](https://github.com/minio/minio/pull/19365)、[minio/minio#19481](https://github.com/minio/minio/pull/19481)
- 运维文档：[对象生命周期管理](/zh/administration/object-management/object-lifecycle-management/)、[批量过期](/zh/administration/batch-framework-job-expire/)、[`mc ilm rule add`](/zh/reference/minio-mc/mc-ilm-rule-add/)、[`mc ilm rule edit`](/zh/reference/minio-mc/mc-ilm-rule-edit/)、[`mc ilm rule export`](/zh/reference/minio-mc/mc-ilm-rule-export/)
