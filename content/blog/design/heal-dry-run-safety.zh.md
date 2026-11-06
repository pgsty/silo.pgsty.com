---
title: "Heal 演练不能删除数据"
linkTitle: "Heal 演练安全"
date: 2026-11-04
lastmod: 2026-11-06
author: "PGSTY SILO 维护团队"
summary: >
  解释以演练（dry run）方式运行的管理 heal，为何在对象版本的元数据没有读 quorum 时仍可能删除悬空版本；为什么五行的提前返回是本次发布的正确修复；以及为什么同一修复还必须在桶 heal 中把演练标志传给远端节点。
tags: [设计, Heal, 数据安全, 运维]
weight: 10
draft: false
url: "/zh/blog/design/heal-dry-run-safety/"
---

本文覆盖 Jasper Bernhardt（[`@dihmandrake`](https://github.com/dihmandrake)）提交的 [PR #280](https://github.com/pgsty/silo/pull/280) 中与演练（dry run）相关的部分，基于 main [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) 评估。同一个 PR 还让深度扫描并发校验一个对象的各块盘。这项优化另行评审，不在本文范围内。该 PR 尚未运行 CI。

**状态：** 修复已通过审查，已在本地提交。它已和下个版本的其他修复放在同一个集成分支上一起测试：完整测试套件、CI 竞态检测选集，以及针对修复之间相互作用的对抗性审查，全部通过。尚未合并或发布。

## 简短结论 {#tldr}

缺陷属实，是 SILO 从上游 MinIO 继承来的。`mc admin heal --dry-run` 的说明是"只检查数据，不做修改"。在 main 上，只要一个对象版本的 `xl.meta` 没有读 quorum，演练 heal 仍会执行悬空对象清理：如果缺少元数据的盘全部回答"不存在"、且数量多于该版本的校验块数，`deleteIfDangling` 就会向每块可用的盘发出删除该版本的请求：仍持有该版本、且删除成功的每块盘都会失去它（连同数据目录），heal 随后报告对象不存在。运维人员为评估受损集群而运行演练，结果销毁的恰恰是他们正在调查的那些对象的最后几份元数据。

对象 heal 的修复是 PR #280 中五行的提前返回：演练中遇到元数据 quorum 失败时，heal 在清理之前返回 quorum 错误，以及一个根据观察到的盘状态构造的集合级结果。真实 heal 不受影响。它应进入下一个版本，与并行校验改动拆开交付，并保留贡献者署名。

**我们的审计还发现了第二处演练写操作。PR #280 没有涉及它，本修复把它一并覆盖。** 在多节点部署中，桶 heal 只向远端节点发送桶名和 remove 标志。没有演练标志，这些节点执行的就是真实的桶 heal：在缺少桶目录的盘上创建桶目录，或者在所有池中都找不到该桶时删除空的桶目录。它不删除对象，但演练不应改变任何东西。修复在对端消息中加入演练标志，并让远端处理函数遵守它，使远端节点走与本地节点相同的演练返回。改动是四行功能代码，加一个构造对端消息的小辅助函数，以及一个回归测试。

PR 中第二处与演练相关的改动，是在分片校验没有成功时，把盘报告为 `unknown` 而不是 `ok`。这是报告层面的改动，不是安全修复。如果只对演练生效，演练和真实 heal 会对同一块盘给出不同的报告。它可以留给一个同时修正两种模式的改动。

## 定性 {#assessment}

| 维度 | 判断 |
| --- | --- |
| 性质 | 演练标志既没有传到 `erasureObjects.healObject` 中的悬空对象清理，也没有传到远端节点执行的桶 heal，两者都破坏了管理 heal 的安全承诺。继承自上游 MinIO；没有任何 SILO 提交引入或改动它们。 |
| 谁能触发 | 只有具备 heal 权限的管理员，通过设置了 `DryRun` 的管理 heal API 触发。例如对桶、前缀或对象，或带 `--recursive` 运行 `mc admin heal --dry-run`（隐藏参数）。全站演练还会遍历 `.minio.sys/config`，IAM 和服务器配置对象就在那里。 |
| 不受影响 | scanner、MRF、后台 heal 和磁盘 heal 从不设置 `DryRun`。SILO Console 没有调用 heal 的路径。真实 heal 的行为不变。 |
| 删除的内容 | 正在被 heal 的对象版本或删除标记。只要元数据 quorum 失败、且 `isObjectDangling` 判定该版本悬空，就会在每块可用的盘上尝试删除，每次成功的删除都会移除该版本（连同数据目录）。删除过程中的盘错误会写入审计，但不会返回。 |
| 其他改动 | 在多节点部署中，演练桶 heal 会让每个远端节点在自己的盘上创建缺失的桶目录；当所有池中都找不到该桶时，则删除空的桶目录。有内容的目录永远不会被删除。 |
| 严重程度 | 高。受影响的版本已经无法通过 S3 读取，真实 heal（以及用户桶中的 GET 或 HEAD）也会按同一规则清理它们。危害在于：运维人员的检查工具，做出了运维人员明确要求它不要做的不可逆删除。在任何人能决定如何恢复之前，最后几份元数据就已经没了。 |
| 发布紧急度 | 阻塞下一个版本。修复约十行代码，只改变演练行为，并且附带回归测试。 |
| 剩余工作量 | 拆分和审查已完成。剩下的是运行 CI，并在实际部署的多节点集群上验证一次演练桶 heal。 |

## 触发条件 {#trigger}

需要同时满足三个条件：

1. 带 `DryRun` 的 heal 对某个对象版本进入 `healObject`。heal 遍历会逐个版本分别 heal。
2. `objectQuorumFromMeta` 失败：读错误归约后，有结果的盘不足一半；或者没有哪个校验块数（parity）得到足够多可读副本的一致报告。一个 parity 需要的一致副本数，等于它所对应的读 quorum，对普通对象就是数据块数。例如，一个 EC 3+1 的版本只有两份可读副本时，虽然有一半的盘作答，仍然会失败。
3. `isObjectDangling` 判定该版本悬空。此时还没有做任何分片检查，因此判定要求：
   - 至少有一份有效的 `xl.meta`；
   - 每块出错的盘都回答"文件不存在"或"版本不存在"。任何其他错误（盘离线、元数据损坏、桶目录缺失、超时）都会否决这个判定。heal 读取元数据时会一并读取小对象的数据，所以对于没有内联的小对象，即使 `xl.meta` 还在，缺失的分片文件也会表现为"不存在"；
   - 对象版本：缺少元数据的盘数多于该版本的校验块数，也就是元数据副本少于数据块数。删除标记：超过一半的盘上没有它。

举例来说，四块盘、EC 2+2。一个 1 MiB 的对象在三块盘上丢失了 `xl.meta`，这三块盘上的分片文件仍在。在 main 上，对该对象运行演练 heal，会把该版本从第四块盘（唯一还存有其元数据的地方）上删除，并报告"对象不存在"。

**降级集群。** 离线的盘回答 `errDiskNotFound`，这个错误会否决悬空判定。因此一块正常离线的盘会阻止清理，而不是导致清理；这一点我们已经验证过。判定只统计回答"不存在"的盘，并且无法分辨它们为什么这样回答。有些盘回答"不存在"，但它们的回答并不权威：

- 一块已更换的盘：桶目录已经建好，但还没有收到这个对象；
- 一块丢失了 `xl.meta`、但分片文件仍在的盘。`isObjectDangling` 的源码注释承认，这种情况原则上是可以恢复的。

而这正是运维人员会去运行演练的场景。这个规则对真实 heal 是否合适，是另一个继承下来的策略问题；演练根本不应该应用这个规则。

## 根因 {#root-cause}

`healObject` 把 `opts.DryRun` 读入 `dryRun`，并在任何修复写入之前返回，代码注释原文是："After this point, only have to repair data on disk - so return if it is a dry-run"。处理元数据 quorum 失败的分支位于更前面，它调用 `deleteIfDangling` 时没有检查 `dryRun`。

`deleteIfDangling` 自己也无法检查。它接收的是 `ObjectOptions`，其中没有演练字段；它还被 GET、HEAD、`CopyObject`、`PutObjectMetadata` 和 `PutObjectTags` 路径共用，这些路径按设计就会清理悬空版本。它还直接从纠删集合获取盘，所以调用方无法限制它会碰到哪些盘。

`healObject` 中另一处 `deleteIfDangling` 调用，在处理无法修复对象的分支里。它位于演练返回之后，是安全的。

## 行为的来源 {#history}

### 溯源

**由上游 MinIO 引入，不是 SILO 引入的。** 两个缺陷都来自上游提交，这些提交都是 SILO 分叉点（[`27742d469`](https://github.com/pgsty/silo/commit/27742d469)，2025-12-03）的祖先。它们存在于分叉前最后一个上游发布 `RELEASE.2025-10-15T17-29-55Z`、已归档的上游 `master`，以及从 `RELEASE.2025-12-03T12-00-00Z` 到 `RELEASE.2026-10-26T00-00-00Z` 的每一个 SILO 发布中。我们检查了每个 tag：`healObject` 中第一次 `deleteIfDangling` 调用位于演练返回之前，远端桶 heal 的消息不带演练标志。没有任何 SILO 提交引入、扩大或缩小这两个缺陷。

**对象 heal。** 上游曾经有这道保护。它的 `purgeObjectDangling` 只在 `if !opts.DryRun && opts.Remove` 时删除，来自 [`db2155551`](https://github.com/pgsty/silo/commit/db2155551)（[#9159](https://github.com/minio/minio/pull/9159)，2020-03-19，`RELEASE.2020-03-19T21-49-00Z`）。随后两处改动分阶段拆掉了它，第三处把结果留在了 `healObject` 中：

| 步骤 | 提交（PR） | 日期 | 首个上游发布 | 影响 |
| --- | --- | --- | --- | --- |
| 去掉演练条件，保留 `opts.Remove`。 | [`b7c5e45ff`](https://github.com/pgsty/silo/commit/b7c5e45ff)（[#14053](https://github.com/minio/minio/pull/14053)） | 2022-01-07 | `RELEASE.2022-01-08T03-11-54Z` | 演练加 `--remove` 会删除；单独的演练不会。 |
| 函数体改为调用没有 `Remove` 限制的 `deleteIfDangling`。 | [`f19a414e0`](https://github.com/pgsty/silo/commit/f19a414e0)（[#14273](https://github.com/minio/minio/pull/14273)） | 2022-02-08 | `RELEASE.2022-02-12T00-51-25Z` | **单独的演练就会删除。** 报告的行为从这个发布开始。 |
| 调用被内联进 `healObject`，位于演练返回之前。 | [`136d41775`](https://github.com/pgsty/silo/commit/136d41775)（[#15954](https://github.com/minio/minio/pull/15954)） | 2022-10-27 | `RELEASE.2022-10-29T06-21-33Z` | 无。元数据仲裁失败的分支仍在演练返回之前。 |
| 该分支的错误返回被重新整理。 | [`3549e583a`](https://github.com/pgsty/silo/commit/3549e583a)（[#19702](https://github.com/minio/minio/pull/19702)） | 2024-05-09 | `RELEASE.2024-05-10T01-41-38Z` | 对判断条件无影响。当前这个分支的大部分行来自该提交。 |

**桶 heal。** 2024 年 1 月之前，按纠删集的桶 heal 会遵守 `DryRun`。节点级桶 heal 在 [`e31081d79`](https://github.com/pgsty/silo/commit/e31081d79)（[#18612](https://github.com/minio/minio/pull/18612)，2024-01-10，`RELEASE.2024-01-11T07-46-16Z`）中取代了它。它的远端调用只发送桶名和 remove 标志，远端 handler 用这两个值构造 heal 选项。同一调用的本地实现会检查 `DryRun`，所以只有本地节点遵守。[`ff80cfd83`](https://github.com/pgsty/silo/commit/ff80cfd83)（[#18951](https://github.com/minio/minio/pull/18951)，2024-02-02，`RELEASE.2024-02-04T22-36-13Z`）把调用迁到 grid，仍只带这两个值。上游 `master` 上这个缺口依然存在。

**SILO 的改动。** 分叉之后，SILO 对 heal 函数、`cmd/peer-s3-client.go`、`cmd/peer-s3-server.go` 以及 `cmd/peer-rest-server.go` 中的 heal handler 所做的改动：

| SILO 提交 | 日期 | SILO 发布 | 影响 |
| --- | --- | --- | --- |
| [`0b1c21cb4`](https://github.com/pgsty/silo/commit/0b1c21cb4)、[`2a04d5f48`](https://github.com/pgsty/silo/commit/2a04d5f48) | 2026-10-25 | 仅 `RELEASE.2026-10-25T00-00-00Z` | **没有影响。** 前者在 `healObject` 的元数据仲裁分支之后加入了版本代际仲裁检查，后者当天就把它移除了。它位于清除逻辑之后，既没有保护也没有扩大清除。 |
| [`e59a3d938`](https://github.com/pgsty/silo/commit/e59a3d938) | 2026-09-11 | `RELEASE.2026-09-16T00-00-00Z` 及之后 | **没有影响。** 调用方已持有命名空间锁时，`HealObject` 沿用该锁的上下文。 |
| [`9b11dc946`](https://github.com/pgsty/silo/commit/9b11dc946) | 2026-09-03 | `RELEASE.2026-09-03T13-18-01Z` 及之后 | **没有影响。** 只是替换了 errgroup 辅助包的导入路径。 |
| [`7ce7fc8d1`](https://github.com/pgsty/silo/commit/7ce7fc8d1) | 2026-10-29 | 尚未发布 | **没有影响。** heal 遍历同时列出 free version，不含演练逻辑。 |

SILO 没有改动 `deleteIfDangling`、`isObjectDangling`、`remotePeerS3Client.HealBucket` 或 `HealBucketHandler`，也没有在这条路径上增加任何演练保护。[PR #280](https://github.com/pgsty/silo/pull/280) 仍处于开放状态，带有对象 heal 的保护；桶 heal 的部分只是本记录提出的方案。

**证据。** 提交的祖先关系、首个发布、两个缺陷在每个 tag 上的存在，以及这些函数中没有 SILO 改动，都用 git 核对过。2022 年各步骤的行为（先是演练加 `--remove`，之后是单独的演练）来自对改动的阅读，没有在那些版本上运行。当前行为由[验证](#verification)一节中的测试复现。

## 方案比较 {#options}

### 方案 1：在 `healObject` 中提前返回

这是 PR #280 的做法。当 `objectQuorumFromMeta` 失败且设置了 `dryRun` 时，`healObject` 用观察到的错误构造 `defaultHealResult`，连同 quorum 错误一起返回。改动只有一个函数中的五行，只影响演练，真实 heal 的行为与现在完全一致。它的局限是只保护这一个调用点：将来如果别处有演练路径调用 `deleteIfDangling`，需要自己的保护。

### 方案 2：把演练标志传入 `deleteIfDangling`

给 `deleteIfDangling` 增加一个参数或一个 `ObjectOptions` 字段，让它在演练中只做判定、不做删除。它还可以向报告返回"将会清理"的判定。代价是六个调用方都要改动，其中四个是对象读取和元数据更新路径，根本没有演练的概念。而且将来的调用方同样可能忘记传这个标志，就像可能忘记提前返回一样。为这点稳健性付出这么多改动并不划算；"将会清理"的报告应该归入演练报告的重新设计。

### 方案 3：集中式保护

让演练 heal 使用只读包装的盘，这样任何写入都会失败。这是唯一能从结构上防住将来失误的方案。但 `StorageAPI` 有几十个方法，`deleteIfDangling` 从纠删集合而不是从调用方获取盘，而桶 heal 的缺口位于对端 RPC 层，这样的包装也覆盖不到。作为发布修复，它的范围太大。

同一思路的廉价版本适用于测试。PR 的合成测试盘内嵌一个 nil 的 `StorageAPI`，任何测试未预期的写操作都会 panic。回归测试保留这种写法。

### 远端节点上的桶 heal

要阻止远端节点在演练中写入，有两种办法：

- **传递标志。** 在对端消息中携带演练标志，并在远端处理函数中遵守它。这样远端节点会走与本地节点相同的提前返回。消息形态、处理函数和错误归约都不变；将来演练桶报告补全后，远端节点也能报告自己的状态。
- **跳过调用。** 让 `S3PeerSys.HealBucket` 在演练时不调用远端节点。这在滚动升级期间也能防住旧节点，但放弃了将来演练报告中远端的那一半，还要在分发逻辑中加一个演练特例。

我们选择传递标志。修复之前，每个节点的行为本来就等同于标志为 false。升级期间，混合版本的集群不会比现在更差；所有节点都运行修复后，缺口即被关闭。

### 关于报告改动

在演练的深度扫描中，如果一块盘的元数据读取成功，但分片校验因为缺失或损坏以外的原因没有成功，PR 会把它报告为 `unknown`。这些原因包括：检查过程中盘离线、卷缺失、超过截止时间、被取消、访问被拒绝。在 main 上，两种模式都把这块盘报告为 `ok`，修复决策也会忽略这些结果。

PR 只改了演练模式。它自己的测试对同一状态，期望演练给出 `unknown`、真实 heal 给出 `ok`。`mc admin heal` 在给对象着色、以及按在线盘数给对象分组时，只统计 `ok` 的盘。于是同一个对象在演练中会显得比随后的真实 heal 中更糟。

把未经校验的盘报告为 `ok` 确实是一个准确性问题：一次完整性审计可能对它根本没检查过的数据报告"干净"。但这个问题两种模式都有，而且它既不删除也不修改数据。应该同时修正两种模式，包括 heal 序列根据同样的盘状态推导出的"quorum loss"说明。

**建议：** 本次发布中，对象 heal 采用方案 1，桶 heal 采用传递标志；推迟报告改动。

## 修复方案 {#fix}

修复分两部分。第 1 部分是 PR #280 中贡献者的改动，第 2 部分来自维护者的审计。

### 第 1 部分：对象 heal 在悬空清理之前返回

**代码。** 原样采用 PR #280 在 `healObject` 中的第一处改动：

```go
readQuorum, _, err := objectQuorumFromMeta(ctx, partsMetadata, errs, er.defaultParityCount)
if err != nil {
	if dryRun {
		// A metadata quorum failure must not delete dangling data in dry-run.
		return er.defaultHealResult(FileInfo{}, storageDisks, storageEndpoints,
			errs, bucket, object, versionID), err
	}
	m, derr := er.deleteIfDangling(ctx, bucket, object, partsMetadata, errs, nil, ObjectOptions{
		VersionID: versionID,
	})
	// 其余不变
```

演练中，集合级结果把每块盘的读错误映射为盘状态，例如缺少 `xl.meta` 的盘为 `missing`。这次调用传入的是 `FileInfo{}`，所以结果的大小为零，校验块数和数据块数取默认值。返回的错误就是 `objectQuorumFromMeta` 返回的错误，经过 `toObjectErr` 转换：多数盘回答"不存在"时为版本或对象不存在；多数副本损坏时为损坏错误；或者为读 quorum 不足。真实 heal 在报告 quorum 失败之前仍会丢弃各盘的错误，与现在一致。

这些信息并不都能到达管理报告。当每个池都回答"不存在"时（这是悬空的常见情形），`erasureServerPools.HealObject` 会用一个空条目替换各集合的结果，所以报告中只有"不存在"错误，没有逐盘状态，这与 main 在清理之后的表现相同。只有错误是其他类型时（例如元数据损坏或读 quorum 不足），观察到的盘状态才会出现在报告中。读 quorum 不足也涵盖一部分悬空版本：一个 EC 3+1 的版本有两份可读副本、两个"不存在"回答时会被判定为悬空，修复后它的演练报告读 quorum 不足，并带有全部四块盘的状态。

**测试。** 采用 PR 中不依赖并行校验的三个测试及其辅助代码：

- `TestNativeAuditDryRunPreservesFaults` 使用合成盘，覆盖元数据 quorum 失败、元数据损坏、分片缺失或损坏、内联数据损坏，以及没有 quorum 的删除标记；
- `TestNativeAuditDryRunPreservesDanglingFiles` 使用真实盘：从四块盘中的三块删除 `xl.meta`，检查演练不改动任何文件；
- `TestNativeAuditNonDryRunStillDeletesDangling` 是对照组：不带 `DryRun` 的相同场景仍会走到清理。

三处小改动：

- `TestNativeAuditDryRunPreservesFaults` 把删除计数断言放到报告断言之前，这样在未修复的代码上，失败信息会直接指出删除；
- 对每种 quorum 情形，它断言转换后的错误（版本不存在，或损坏错误），取代原来针对 `errFileNotFound` 的检查——经过 `toObjectErr` 之后，那个检查不可能失败；
- 合成盘去掉了 `CheckParts` 桩，它只被 PR 中并行校验和报告相关的测试使用。

### 第 2 部分：远端节点在桶 heal 中遵守演练标志

**代码。** 在 `peerS3BucketDeleted` 旁边新增键 `peerS3BucketDryRun = "dry-run"`。`remotePeerS3Client.HealBucket` 通过一个小编码函数构造消息并加入这个键，`HealBucketHandler` 把它读入 `madmin.HealOpts.DryRun`：

```go
// peer-s3-client.go
func healBucketPeerMSS(bucket string, opts madmin.HealOpts) *grid.MSS {
	return grid.NewMSSWith(map[string]string{
		peerS3Bucket:        bucket,
		peerS3BucketDeleted: strconv.FormatBool(opts.Remove),
		peerS3BucketDryRun:  strconv.FormatBool(opts.DryRun),
	})
}

// peer-rest-server.go，HealBucketHandler
dryRun := mss.Get(peerS3BucketDryRun) == "true"
res, err := healBucketLocal(context.Background(), bucket, madmin.HealOpts{
	Remove: bucketDeleted,
	DryRun: dryRun,
})
```

设置了 `DryRun` 时，`healBucketLocal` 本来就会在任何 `MakeVol` 或 `DeleteVol` 之前返回，所以它不需要改动。RPC 处理函数、它的注册和返回类型也都保持不变。

**测试。** `TestPeerHealBucketDryRun` 启动两个 grid 管理器，在其中一个上注册对端处理函数，再从另一个调用 `remotePeerS3Client.HealBucket`。这样请求会经过真实的客户端、grid 连接和处理函数，作用于一个四块盘的集合，其中一块盘上的桶目录已被删除。两次演练请求（一次带 `Remove`，一次不带）既不能重建缺失的目录，也不能删除空目录。随后两个对照组证明测试场景能走到这两种写操作：一条不带演练键的消息（旧节点发送的形态）会重建目录；一次带 `Remove` 的真实 heal 会删除空目录。该测试不使用任何新增标识符，因此能在 main 上编译，并在第一个演练断言处失败。

**其他对端 heal 调用。** 我们逐一检查过，没有一个存在同样的缺口：

- format heal 只从协调节点保存 `format.json`，并且只在它自己的演练检查之内保存。它会先用常规的存储初始化打开各块盘，而这一步发生在演练检查之前，见[剩余限制](#limits)。在当前代码中，管理 heal 序列不会把 format heal 入队；
- 后台 heal 状态调用是只读的；
- 管理 heal 请求只有在凭 token 轮询已有序列时才会被代理到其他节点，从不用于启动序列。

### 交付

- 把演练改动和上述测试拆成独立的提交和 PR，与并行校验改动分开。后者需要单独评审（慢盘上的 I/O 并发和取消处理），也需要单独的 CI。
- 保留贡献者署名。生产代码改动与贡献者已签署 DCO 的提交完全一致，但测试是经过调整的子集，所以拆分后的提交是维护者提交，附带 Jasper Bernhardt 的 `Co-authored-by` 标注，并引用 PR #280。
- PR #280 随后继续承载并行校验；如有需要，也可以承载一个同时覆盖两种模式的报告改动。
- PR 说明中写明，实现和测试由 AI 编写，贡献者无法独立确认其正确性。演练改动足够小，维护者已按下文所述独立验证；本文依据的是这些验证，而不是 PR 自身的说法。
- 第 2 部分作为单独的维护者提交，放在同一个 PR 中交付。它不含贡献者代码，贡献者署名保留在第 1 部分上。

## 为什么方案充分且必要 {#sufficiency}

我们审计了管理演练 heal 可能修改数据的每一个位置：

| 路径 | 可能的写操作 | main 上 `DryRun` 时 | 修复后 |
| --- | --- | --- | --- |
| `healObject`，元数据 quorum 失败 | `deleteIfDangling`（对所有盘调用 `DeleteVersion`） | **会执行** | 不再执行 |
| `healObject`，无法修复的对象 | `deleteIfDangling` | 位于演练返回之后 | 不变 |
| `healObject`，修复 | 向临时区写分片、`RenameData`、删除远端数据目录、清理临时区 | 位于演练返回之后 | 不变 |
| `HealObject`，发现 bitrot 后的深度扫描重试 | 以相同选项再次运行 `healObject` | 同上 | 同样受修复保护 |
| `healObjectDir` | 删除悬空目录；为缺失的目录执行 `MakeVol` | 删除需要 `!dryRun && remove`；`MakeVol` 位于演练返回之后 | 不变 |
| `HealObjects` 遍历 | `CheckAbandonedParts` | 需要 `Remove && !DryRun`，且 `checkAbandonedParts` 会再次检查 `DryRun` | 不变 |
| 全站 heal 中的 `.minio.sys/config` | 同一个 `healObject` 路径 | **会执行**（读路径的清理跳过 `.minio.sys`，heal 不跳过） | 不再执行 |
| 桶 heal，本地节点（`healBucketLocal`） | `DeleteVol`、`MakeVol` | 在任何写操作之前返回 | 不变 |
| 桶 heal，远端节点 | `MakeVol`、非强制 `DeleteVol` | **会执行**：没有发送演练标志 | 不再执行：标志被发送并得到遵守（升级期间旧节点仍会忽略它） |
| `HealFormat` | 写入 `format.json` 并替换盘；盘初始化可能创建内部目录，或迁移旧的 `format.json` | 保存位于 `if !dryRun` 之内，但初始化发生在这个检查之前。管理 heal 序列不会把它入队；当前代码中唯一的调用方是新盘监视器，且 `dryRun` 为 false | 不变 |
| 全站 heal，桶列举 | `ListBuckets` 会填入创建时间。对于元数据不在缓存中的桶，这会经由普通的对象读路径加载桶元数据，可能迁移旧版桶配置文件，并为 `.metadata.bin` 入队 MRF 修复 | 会执行，走的是服务器在启动时和定期元数据刷新时尝试的同一次加载 | 不变；见[剩余限制](#limits) |
| heal 的元数据读取（`ReadVersion`）、`CheckParts`、`VerifyFile`、heal 遍历 | 无 | 只读 | 不变 |

heal 路径本身不会向 MRF 入队；只有上面的桶元数据加载可能入队。被执行的清理在盘以外唯一的副作用，是一条 `DeleteDanglingObject` 审计记录，只在配置了审计日志时写入。

**充分性。** 两部分都到位、且所有节点都运行修复后，管理演练 heal 不再执行 heal 自身的写操作：对象 heal 在清理之前返回；桶 heal 在每个节点上（而不只是协调 heal 的那个节点）都在 `MakeVol` 和 `DeleteVol` 之前返回。heal 修复逻辑之外，还有两处继承下来的影响，列在[剩余限制](#limits)中：全站列举时的桶元数据加载，以及直接调用 format heal 时的盘初始化。

**必要性。**

- 在演练中，quorum 失败分支是唯一一处在演练返回之前执行的对象 heal 写操作。没有第 1 部分，清理就仍然可达。
- 远端桶 heal 是管理演练能走到的另一处 heal 写操作。没有第 2 部分，多节点部署中的每个远端节点在演练时仍会修复桶目录。
- 报告改动对安全不是必需的。

**有意排除的范围：**

- `checkObjectWithAllParts` 中的并行校验；
- `unknown` 报告改动；
- 真实 heal 和读路径的悬空清理策略。

## 代价与兼容性 {#cost}

- 不改变 API、配置、指标、存储格式或依赖。真实 heal 不变。
- 桶 heal 的对端消息新增一个可选键 `dry-run`。这个消息是字符串映射，grid 编解码会解出收到的每一个键，所以接收方不认识的键会被原样携带并忽略。我们验证过：带新键的消息能完整往返编解码，旧处理函数也能接受它。没有新增 RPC 处理函数，也没有处理函数的版本变更。
- 滚动升级：
  - **新节点调用旧节点。** 旧节点忽略这个键，执行真实的桶 heal，与现在完全相同。
  - **旧节点调用新节点。** 消息中没有这个键，新节点读到 `false`，执行真实的桶 heal，与现在完全相同。
  - 只有在所有节点都运行修复之后，演练桶 heal 才不再改动桶目录；混合版本的集群任何时候都不会比现在更差。
- 演练结果的变化如下：
  - 悬空版本不再被删除；
  - 在集合级，各盘报告观察到的状态，而不是 `ok`。只有错误不是"不存在"时，管理报告中才能看到这些状态，因为当每个池都回答"不存在"时，池聚合会丢弃集合结果；
  - 返回的是经过转换的 `objectQuorumFromMeta` 错误，而不是清理之后的结果；
  - 演练不再产生 `DeleteDanglingObject` 审计记录；
  - 远端节点不再改动桶目录，演练桶报告中远端的部分现在也和本地部分一样是空的。
- 回滚即恢复旧行为，两个方向都不需要迁移。

## 剩余限制 {#limits}

- **混合版本集群。** 在所有节点都运行修复之前，演练桶 heal 仍会让旧节点创建缺失的桶目录或删除空的桶目录。发布说明应写明：只有升级完成后，演练才不再改动桶目录。
- **全站演练会加载桶元数据。** 它的桶列举会填入创建时间。对于元数据不在缓存中的桶，这是一次普通的元数据加载，与服务器在启动时和定期刷新时尝试的加载相同（每轮刷新在上一轮结束 15 分钟后开始）：它可能把旧版桶配置文件迁移进 `.metadata.bin`，并为缺失的 `.metadata.bin` 副本入队 MRF 修复。它不触及对象数据。服务器自己的加载也会做出同样的改动，但迁移或修复何时完成没有保证。让演练列举跳过创建时间即可避免这次加载，这属于后续工作。
- **format heal 在演练检查之前初始化各块盘。** 打开盘时可能创建内部目录并迁移旧的 `format.json`。在当前代码中，管理 heal 序列不会把 format heal 入队，所以管理演练不会走到这里。要让 format 检查只读，需要只读的盘初始化。
- **演练桶 heal 不报告盘状态。** `healBucketLocal` 在把观察到的状态附加到结果之前就返回。修复后，这在每个节点上都成立，而不只是本地节点，所以演练给出的桶摘要没有逐盘细节。在演练返回之前填入观察到的状态，属于报告的后续改动。
- **过去的演练无法撤销。** 如果在本修复之前曾对受损对象运行过演练 heal，被它清理掉的版本已经不存在了。如果配置了审计日志，它们会以 `DeleteDanglingObject` 记录出现，其 caller 标签指向 heal 代码。
- **演练不会提示"将会清理"。** 修复后，一个悬空版本在管理报告中要么表现为一个没有盘状态的"不存在"错误（每个池都回答"不存在"，池聚合丢弃了集合结果），要么表现为带有盘状态的读 quorum 不足错误。两种情况下，集合结果本身的大小都为零、校验块数为默认值。它不会被标注为真实 heal 将要删除的对象。"将会清理"的判定可以放进报告的后续改动。
- **未经校验的盘仍被报告为 `ok`**，两种模式都是如此，直到报告的后续改动完成。
- **真实 heal 的悬空清理策略不变。** 它统计的"不存在"回答，可能来自并不权威的盘。重新审视这个策略是另一项工作。

## 验证 {#verification}

所有运行都用 `go test -run` 只选相关测试，参数为 `-p 2`，标签为 `kqueue,dev`。下文的"main"指一个位于 `69fcf50cd`、只加入了新测试文件的一次性 worktree。

**已执行：main 上的缺陷。**

- 在合成盘上（四块中有三块回答"版本不存在"）运行演练 `HealObject`，会向每块盘发出 `DeleteVersion` 调用，对象版本和删除标记都是如此。
- 把其中一块盘改为离线后，真实 heal 一次也不调用，这证实了离线否决。
- 在真实盘上，演练 heal 删除了最后一份幸存的 `xl.meta`。
- 把只含桶名和 remove 标志的消息（即 main 的远端客户端为演练请求发送的形态）交给对端处理函数，它会重新创建缺失的桶目录；本地 `healBucketLocal` 带 `DryRun` 时不会。PR #280 的改动对此没有影响。

**已执行：提交的测试。**

- 在 main 上：
  - `TestNativeAuditDryRunPreservesFaults` 的元数据 quorum 和删除标记子测试在删除断言处失败；元数据损坏子测试在报告断言处失败：那里的清理被否决了，但 main 把每块盘都报告为 `ok`；
  - `TestNativeAuditDryRunPreservesDanglingFiles` 失败：演练之后，持有最后一份 `xl.meta` 的盘上，对象目录已经不存在；
  - `TestPeerHealBucketDryRun` 能编译，并在第一个演练断言处失败：远端节点重建了缺失的桶目录；
  - 对照组通过：`TestNativeAuditNonDryRunStillDeletesDangling`，以及分片缺失、分片损坏和内联数据损坏三个子测试。
- 应用修复后，以上测试全部通过，`-race -count=3` 也通过。
- 对 `TestPeerHealBucketDryRun` 的变异检查：客户端编码函数漏掉这个键时测试失败，处理函数忽略这个键时测试也失败。
- 新测试与已有的 `TestHealing*`、`TestHealObject*`、`TestHealCorrectQuorum`、`TestHealLastDataShard`、`TestHealEmptyDirectoryErasure`、`TestIsObjectDangling` 和 `TestFreeVersionHealObjects` 在同一进程中以 `-race -count=2` 一起运行，全部通过。已有的 `TestPeer*`、`TestErasureHeal` 和 grid 包测试在不启用 race 检测时也通过。`TestErasureHeal` 在 race 检测下会在 ring buffer 中 panic，在 main 上同样如此，与本修复无关。
- `gofmt` 和 `go vet ./cmd` 都没有报告问题。

**已执行：对抗性评审。**

- 带上新键的消息能完整往返 grid 编解码，main 的处理函数接受并忽略它：重建缺失目录，并删除空目录。这就是"新节点调用旧节点"的情形。
- 同时存在于两个池中的对象仍会经过两个池进行 heal；健康的第二个池仍会在聚合中胜出。
- 每个对端都返回空的演练结果时，归约不会报错；扇出过程改写 `Remove` 和 `Recreate`，但保留 `DryRun`。
- 桶元数据缓存为空时，全站演练会迁移一份旧版桶配置，并为缺失的 `.metadata.bin` 副本入队 MRF 修复，main 和修复后都是如此。让列举跳过创建时间可以同时避免这两者。
- 直接调用的 `HealFormat` 演练会重建缺失的 `.minio.sys/config` 目录，main 和修复后都是如此。
- 在管理层，一次悬空演练报告一个带"不存在"错误的空条目；在集合层，同一次调用报告三块 `missing` 盘。一个有两份可读副本的 EC 3+1 版本报告读 quorum 不足，并带有四块盘的状态，而 main 会清理它。
- 全站演练序列会 heal `.minio.sys/config` 中的对象。修复后，一个悬空的配置对象会保留它最后一份 `xl.meta`。

**根据代码推断，未执行：**

- 只有管理 heal API 会设置 `DryRun`；
- main 的远端客户端只发送这两个字段；
- 没有其他对端 heal 调用会丢掉这个标志；
- `mc admin heal` 如何使用盘状态；
- 上游历史。

**未运行：**

- 完整的 `./cmd` 测试；
- 远端 CI；
- 实际部署的多节点集群和混合版本升级。对端测试使用真实的 grid 连接，但两个管理器位于同一个测试进程中；
- 端到端的 `mc admin heal --dry-run`；
- 并行校验相关的测试。

**集成验证。** 这个修复已摘取到下个版本的同一个集成分支上，位于 #278 和 #281 之后，与锁域、#259、#285 和 Console 的修复放在一起。所有摘取都没有冲突。在该 head 上，完整的 `go test ./cmd/... ./internal/...` 套件通过，CI 的竞态检测选集和覆盖全部新测试的竞态选集也都通过。针对组合的对抗性审查没有发现缺陷，锁域、清理路径以及清除与恢复之间的交互都用实际执行的探针检查过。

## 审查记录 {#review}

| 轮次 | 结果 |
| --- | --- |
| 对抗性审查第 1 轮 | 要求修改。五个问题：全站演练的桶列举会加载未缓存的桶元数据，可能迁移旧版桶配置并入队 MRF 修复（原本就有）；真实盘测试夹具会遗留后台 worker 和全局状态；直接调用的 format heal 在演练检查之前初始化各块盘（原本就有）；每个池都回答"不存在"时，池聚合会丢弃集合级的盘状态（原本就有）；测试中有一个错误断言不可能失败。另外对本文提出十一处更正。结果：列举的影响被认定不阻塞本修复，因为服务器在启动时和定期刷新时会尝试同一次加载；已在文中说明，并列出后续工作。夹具问题有异议：测试沿用了已有 heal 测试的夹具惯例，并且与这些测试一起进行的 race 运行全部通过。format 和聚合两个问题已在文中说明。该断言现在对每种情形检查转换后的错误。所有更正均已采纳。 |
| 对抗性审查第 2 轮 | 批准，附带小问题。审查方撤回了列举和夹具两个问题，不再作为这两部分的发布问题。两处措辞问题：部分悬空版本会报告带盘状态的读 quorum 不足；定期刷新没有完成时间上的保证。另有三处更正。均已采纳。 |

## 参考 {#references}

- 贡献者 PR：[#280](https://github.com/pgsty/silo/pull/280)
- 评估基线：[69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc)
- 上游历史：[minio/minio#14053](https://github.com/minio/minio/pull/14053)、[minio/minio#14273](https://github.com/minio/minio/pull/14273)、[minio/minio#15954](https://github.com/minio/minio/pull/15954)、[minio/minio#18612](https://github.com/minio/minio/pull/18612)
- 相关：[对象自愈](/zh/operations/concepts/healing/)、[`mc admin heal`](/zh/reference/minio-mc-admin/mc-admin-heal/)
