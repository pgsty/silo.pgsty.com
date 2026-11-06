---
title: "失败写入与幽灵空前缀"
linkTitle: "幽灵空前缀"
date: 2026-11-04
lastmod: 2026-11-05
author: "PGSTY SILO 维护团队"
summary: >
  解释暂存数据已经消失的写入，为何会留下一个空的对象目录，并在之后表现为一个下面什么都没有的公共前缀；以及为什么在重命名失败路径上清理空目录，是最小而完整的修复。
tags: [设计, 存储, ListObjects, 运维]
weight: 10
draft: false
url: "/zh/blog/design/failed-rename-empty-prefix/"
---

本文覆盖 [issue #285](https://github.com/pgsty/silo/issues/285) 和 Denis Babchuk 提交的 [PR #286](https://github.com/pgsty/silo/pull/286)，基于 main [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) 与 PR head [ed05d982a](https://github.com/pgsty/silo/commit/ed05d982a1d26502e3ed2c7c5605bcf422f5d228) 评估。

**状态：** 修复已通过审查，已在本地提交。它已和下个版本的其他修复放在同一个集成分支上一起测试：完整测试套件、CI 竞态检测选集，以及针对修复之间相互作用的对抗性审查，全部通过。尚未合并或发布。修复保留 PR #286 的提交不变，并增加一个维护者提交。

## 简短结论 {#tldr}

报告属实。调用方已经放弃并删除了暂存数据之后，某块磁盘仍可能执行 `xlStorage.RenameData`。此时数据目录的重命名会失败，但为这次重命名创建的对象目录会留下来，而且是空的。只要它的父目录下还有其他对象，它就不可见；一旦这些对象被删除，父目录就再也删不掉，带分隔符的列举会返回一个下面什么都没有的公共前缀。

没有任何对象数据丢失、被改动或被暴露。损害是一个永久存在的列举异常：

- 读取每个列出前缀的工具会因此失败，例如 Iceberg `remove_orphan_files`；
- heal 不会移除它；
- 不知道空对象目录的名称时，通过 S3 唯一的清理方式，是对该前缀做一次破坏性的强制删除。

PR #286 是正确的修复。数据目录重命名失败时，它会在对象目录为空的情况下一并删除对象目录，再逐级删除变空的父目录。末尾的斜杠把第一次删除限制在空目录上，因此已有对象、其他数据目录或旧格式数据在这一步都不会被触及。

我们在采纳时补充三处：

- 同一函数的提交步骤，也就是 `xl.meta` 的重命名，有自己的失败分支。对于没有数据目录的写入（例如内联对象和零字节对象），这个分支会留下同样的空目录，因此加上同样的一行清理。
- 向上逐级删除父目录时，只删除空目录。原来它会删除每个父路径上的任何东西，而并发写入可能把这个路径换成一个已提交对象的 `xl.meta`。对抗性审查表明，新的清理使这种情况在每块磁盘上都可能发生。
- 如果某次写入的重命名失败，是因为并发清理删除了其目标路径上的某级目录，而它自己的源仍然存在，它会重新创建这些目录并重试，最多每级路径一次。

修复不会主动清扫已经留在磁盘上的目录。之后对同一个 key 写入再删除，就会移除其中一个；如何发现和移除它们，见[剩余限制](#limits)。

## 定性 {#assessment}

| 维度 | 判断 |
| --- | --- |
| 性质 | 写入失败路径上的清理缺陷；继承自上游 MinIO，不是已发布 SILO 版本引入的回归。 |
| 受影响部署 | 纠删码部署，实际上主要是分布式部署：远端磁盘在调用方放弃之后才完成 `RenameData`，例如节点缓慢或过载、磁盘超时、客户端断开。 |
| 受影响写入 | 该磁盘上还没有 `xl.meta` 的 key 的写入，且数据位于数据目录中：超过内联阈值的对象，以及分段上传完成。没有数据目录的写入会经由提交分支进入同样的状态，但时间窗口更窄。 |
| 不受影响 | 成功的写入；已有的对象和版本；对该磁盘上已有 `xl.meta` 的 key 的覆盖写。 |
| 严重程度 | 中等。没有数据丢失或损坏。列举会无限期返回空前缀，遍历前缀的工具会失败，而在仍有对象的前缀下，这类目录会持续累积。 |
| 可达性 | 依赖时序。报告者在一个注入了网络延迟的 4 节点集群上，用约 5000 次被客户端中断的写入也没能现场复现，但在 12 盘和 16 盘集合的生产环境中发现了它。测试可以确定性地构造这个状态。 |
| 发布紧急度 | 不属于数据安全层面的发布阻塞项，但计划随下一个版本发布：生产用户已经遇到（Iceberg 孤儿文件清理）。清理和重试只在重命名失败时执行；只删除目录的向上清理也作用于普通删除，删除的目录与之前相同，只有仅含 macOS `.DS_Store` 文件的父目录除外。 |
| 剩余工作量 | 修复及其测试已在本地完成并通过审查。剩下远端 CI、合并和发布。 |

## 触发条件 {#trigger}

在一块磁盘上的顺序如下：

1. 一次超过内联阈值的 `PutObject`，或一次 `CompleteMultipartUpload`，进入提交阶段，在纠删集合的每块磁盘上调用 `RenameData`。
2. 调用节点不再等待某块远端磁盘：客户端断开、请求被取消，或磁盘调用超时。远端磁盘并不知情。`RenameDataHandler` 用 `context.Background()` 执行 `RenameData`，grid 单请求 handler 也完全没有 context。远端的磁盘包装层 `xlStorageDiskIDCheck.RenameData` 用磁盘超时（默认 30 秒）约束这次调用，但到期时只是返回，正在进行的文件系统调用仍会继续。
3. 没有写仲裁，调用方判定写入失败。`renameData` 撤销已经报告成功的磁盘；`PutObject` 中延迟执行的 `deleteAll` 会在每块磁盘上删除 `.minio.sys/tmp` 下的暂存对象。对分段上传而言，完成失败后的 `AbortMultipartUpload` 会删除上传目录。
4. 迟到的 `RenameData` 执行到数据重命名。`renameAll` 先创建目标路径的各级父目录（`reliableRename` → `reliableMkdirAll`），也就创建了 `<bucket>/<prefix>/<object>/`。随后重命名以“不存在”失败，而清理只删除数据目录这个从未存在过的路径。
5. 之后，`<prefix>/` 下的其他对象都被删除。每次删除都会移除自己的对象目录，并在父目录处停下，因为父目录里还有那个空的 `<object>/`。

当足够多的磁盘上留有这个空目录时，main 上的列举结果如下（取自测试，只留下了 `day=1/b=9/put/`）：

| 请求 | main 上的结果 |
| --- | --- |
| `ListObjectsV2`，`delimiter=/`，不带前缀 | 前缀 `day=1/` |
| `ListObjectsV2`，`delimiter=/`，前缀 `day=1/` | 前缀 `day=1/b=9/` |
| `ListObjectsV2`，`delimiter=/`，前缀 `day=1/b=9/` | 无结果 |
| 递归 `ListObjectsV2`、`ListObjectVersions`、`HEAD day=1/b=9/put` | 无结果、无结果、不存在 |

只要集合中至少一半的磁盘上有这个目录，前缀就会出现，这就是默认的 `strict` 列举仲裁。在 16 盘集合中，目录留在 8 块盘上时会被列出，留在 7 块盘上时不会。

## 根因 {#root-cause}

两种行为叠加在一起。

**清理假设失败的重命名最多只创建了数据目录。** `deleteFile(dstVolumeDir, dstDataPath, false, false)` 会在数据目录存在且为空时删除它；只有删除成功之后，才会向上逐级删除变空的父目录。源路径不存在时，数据目录从未被创建，删除报告“不存在”，`deleteFile` 提前返回，而 `reliableMkdirAll` 片刻之前创建的对象目录根本不在考虑范围内。

**列举遍历会隐藏空目录，但不会隐藏包含空目录的目录。** 没有 `xl.meta` 的目录只有在非空时才会作为前缀上报。空的 `<object>/` 会被跳过；它的父目录不为空，于是被上报，它之上的每一级祖先目录也一样。删除其他对象无法解决这个问题：每次删除都会向上走到这个父目录，发现它不为空，然后停下。

也没有其他机制会清理它。heal（包括由数据 scanner 触发的 heal）只会删除“持有它的磁盘少于缺少它的磁盘”的目录；scanner 本身也不会从磁盘上删除目录。

## 行为的来源 {#history}

### 溯源

**由上游 MinIO 引入，不是 SILO 引入的。** 残留目录比本想防止它的那段清理更早出现。下面每个成因都是上游提交，并且都是 SILO 分叉点（[`27742d469`](https://github.com/pgsty/silo/commit/27742d469)，2025-12-03）的祖先。这段清理代码在报告者看到问题的 MinIO `RELEASE.2025-07-23T15-54-02Z`、上游最后一个发布 `RELEASE.2025-10-15T17-29-55Z`、已归档的上游 `master`、`main`，以及从 `RELEASE.2025-12-03T12-00-00Z` 到 `RELEASE.2026-10-26T00-00-00Z` 的每一个 SILO 发布中完全一致，我们逐个 tag 比对了相关行。SILO 曾在一个发布中改变过迟到写入的时间窗口，没有任何 SILO 提交改动过这段清理。

| 成因 | 提交（PR） | 日期 | 首个上游发布 |
| --- | --- | --- | --- |
| 重命名在改名之前先创建目标的父目录。 | [`12f67d47f`](https://github.com/pgsty/silo/commit/12f67d47f)（[#5376](https://github.com/minio/minio/pull/5376)） | 2018-01-13 | `RELEASE.2018-01-18T20-33-21Z` |
| `RenameData` 用这种重命名移动数据目录和 `xl.meta`。失败时没有任何清理，因此它创建的目录会留下。 | [`4915433bd`](https://github.com/pgsty/silo/commit/4915433bd)（[#9377](https://github.com/minio/minio/pull/9377)） | 2020-06-12 | `RELEASE.2020-07-11T06-07-16Z` |
| 加入失败清理：对数据目录路径调用 `deleteFile`，提交分支中则对 `xl.meta` 路径调用。`deleteFile` 对不存在的路径在向上清理之前就返回，先是返回“不存在”，从这个提交起返回 `nil`。 | [`dd2831c1a`](https://github.com/pgsty/silo/commit/dd2831c1a)（[#12452](https://github.com/minio/minio/pull/12452)） | 2021-06-07 | `RELEASE.2021-06-07T21-40-51Z` |
| 提交分支的清理目标从 `xl.meta` 路径改为数据目录路径；原先直接写 `xl.meta`、没有数据目录 ID 的写入，现在也走暂存文件的重命名。 | [`c7f7c4738`](https://github.com/pgsty/silo/commit/c7f7c4738)（[#18801](https://github.com/minio/minio/pull/18801)） | 2024-02-20 | `RELEASE.2024-02-24T17-11-14Z` |
| 存储 RPC handler 用 `context.Background()` 执行磁盘变更（grid）。此前 handler 传入的是请求上下文。 | [`51aa59a73`](https://github.com/pgsty/silo/commit/51aa59a73)（[#18461](https://github.com/minio/minio/pull/18461)） | 2023-11-20 | `RELEASE.2023-12-02T10-51-33Z` |
| 磁盘包装层用截止时间限制 `RenameData`，到期即返回，工作继续：先是 deadline worker，后来是 `WithDeadline`，直到现在的形态。 | [`e7b60c4d6`](https://github.com/pgsty/silo/commit/e7b60c4d6)（[#17701](https://github.com/minio/minio/pull/17701)）、[`4a6c97463`](https://github.com/pgsty/silo/commit/4a6c97463)（[#18861](https://github.com/minio/minio/pull/18861)）、[`9693c382a`](https://github.com/pgsty/silo/commit/9693c382a)（[#19548](https://github.com/minio/minio/pull/19548)） | 2023-07-25、2024-01-24、2024-04-23 | `RELEASE.2023-08-04T17-40-21Z`、`RELEASE.2024-01-28T22-35-53Z`、`RELEASE.2024-04-28T17-53-50Z` |

这些部分如何组合：

- **目录泄漏早于清理。** 从第一版 `RenameData` 起，重命名就会创建对象目录，失败时没有任何东西把它删掉。#12452 加入了清理，但源路径缺失时它针对的路径并不存在，`deleteFile` 又在考虑任何父目录之前就返回。它从来没有能力删除这个目录。
- **#18801 没有改变结果。** 在它之前，提交分支清理的是 `xl.meta` 路径，重命名失败后该路径并不存在。在它之后，该分支清理的是数据目录路径：内联写入时它不存在，数据重命名已成功时它是一个非空目录。两种情况都不会删除空的对象目录。该分支仍会创建这个目录，所以提交步骤会留下同样的残留，如本记录所述。
- **迟到的写入来自时间相关的成因。** 磁盘包装层的截止时间（2023 至 2024 年）和 handler 的 `context.Background()`（#18461）使 `RenameData` 可以在调用方放弃、暂存数据被删除之后继续运行。当时 handler 的上下文并不控制 `RenameData` 的任何步骤，所以 #18461 并没有创造这个窗口。后来加入的取消检查（#19627，2024-04-28）在远端磁盘上看不到调用方的取消，只会在远端磁盘自己的截止时间触发，这个截止时间由该磁盘的包装层加上。
- **议题中对清理代码的描述是准确的。** 它与 `RELEASE.2025-07-23T15-54-02Z` 一致，且这段代码自 2024 年 4 月的 #19548 以来没有变化。

**SILO 的改动**（都在分叉之后；没有一个改动 `deleteFile`、`RenameDataHandler` 或两处清理调用）：

| SILO 提交 | 日期 | SILO 发布 | 对残留目录的影响 |
| --- | --- | --- | --- |
| [`f480086b6`](https://github.com/pgsty/silo/commit/f480086b6)（PR #232） | 2026-10-12 | `RELEASE.2026-10-18T00-00-00Z` 及之后 | **没有影响。** `errCommitMetaMissing` 在清理调用之后，把暂存 `xl.meta` 缺失重新归类为写仲裁失败（503），让客户端重试。目录的残留与之前相同。 |
| [`cd1f6cec3`](https://github.com/pgsty/silo/commit/cd1f6cec3)、[`5ad1f344b`](https://github.com/pgsty/silo/commit/5ad1f344b) | 2026-10-25 | 仅 `RELEASE.2026-10-25T00-00-00Z` | **缩小了迟到写入的窗口。** 调用方在回滚、删除暂存文件和释放锁之前，会等待每个已受理的 `RenameData`（磁盘包装层用 `WithDeadlineAndWait`，远端调用不可取消、也没有默认超时）。清理代码没有变化，所以仍然失败的写入会以同样方式留下残留。 |
| [`ea7c794a9`](https://github.com/pgsty/silo/commit/ea7c794a9)、[`8a4097309`](https://github.com/pgsty/silo/commit/8a4097309)、[`652a1c09d`](https://github.com/pgsty/silo/commit/652a1c09d) | 2026-10-25 | 仅 `RELEASE.2026-10-25T00-00-00Z` | **没有影响。** 按路径的变更锁、独立的回滚备份目录，以及保护未完成提交不被废弃数据清理删除。 |
| [`dcc2f20ba`](https://github.com/pgsty/silo/commit/dcc2f20ba) | 2026-10-26 | `RELEASE.2026-10-26T00-00-00Z` 与 `main` | **恢复了继承来的窗口。** 它撤回了上述等待在途操作的改动，以保持既有的超时行为，见[存储超时与回滚边界](/zh/blog/design/multi-pool-object-consistency/#maintenance-20261026)。 |
| [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff)、[`0f9199e0c`](https://github.com/pgsty/silo/commit/0f9199e0c) | 2026-08-02、2026-10-18 | `RELEASE.2026-08-04T00-00-00Z`、`RELEASE.2026-10-18T00-00-00Z` | **没有影响。** 前者在 deadline worker 内部恢复 panic，后者及时删除系统桶下为空的分片上传父目录。两者都不涉及目标对象目录。 |

没有任何 SILO 提交引入或扩大了这个残留。唯一降低暴露的 SILO 改动只发布了一次，一天后就被撤回，因此 `RELEASE.2026-10-26T00-00-00Z` 的暴露程度与上游相同。迟到的磁盘操作仍是一条有文档记录的边界，本问题就是它的一种可见后果。

**证据。** 清理代码块在各 tag 上是否一致、每个提交的祖先关系和首个发布，都用 git 核对过（已执行）。`20261025` 的缩小效果以及 #18801 的影响，来自对改动的阅读（推理）。报告者也无法在线上复现迟到写入；[验证](#verification)一节中的确定性测试直接构造了这个状态。

## 方案比较 {#options}

### 方案 1：在重命名失败路径上删除空目录

这是 PR #286 的思路，也是选定的方案。创建这些目录的函数在同一次调用中、在同一块磁盘上删除它们，而且只删除空目录。成功路径上没有任何代价，也不需要新增状态。

### 方案 2：让远端 `RenameData` 响应调用方的取消

这能缩小窗口但无法关闭它，代价却大得多。grid 单请求 handler 拿不到 context；grid 服务端知道请求的截止时间，但只用它来丢弃迟到的响应。要传播取消，需要修改 grid 请求协议，或为这个调用换用另一种 handler 类型。取消也无法中止正在进行的文件系统调用：如果取消恰好在创建目录和重命名之间到达，目录仍会留下，方案 1 依然必要。SILO 之前等待已受理存储 I/O 的工作，已为保持既有超时行为而撤回（见[行为的来源](#history)）。

### 方案 3：让 heal 或 scanner 删除空的对象目录

这是唯一无需用户操作、就能清扫旧版本遗留目录或崩溃遗留目录的方案，但本次不采用。heal 有意只删除少数磁盘持有的目录。在后台删除多数磁盘都持有的空目录，会与每一次首次写入在“创建目录到重命名”之间发生竞争，而不只是与迟到的写入竞争，除非它持有对象锁并设置时间阈值。这是一种新的、具有破坏性的后台行为，需要单独设计。它仍可作为清理存量遗留的后续工作。

### 方案 4：让列举忽略下面没有任何对象的目录

遍历只知道一个目录是否为空。要证明一棵子树里没有对象，就得在带分隔符的列举中，为每个目录条目读取整棵子树。这些目录也仍然留在磁盘上，父目录仍然删不掉。不采用。

### 方案 5：在创建目标之前检查暂存数据

这会给每次写入增加一次系统调用，而且仍有竞争：暂存数据可能在检查之后、重命名之前消失。不采用。

### 方案 6：让 `reliableRename` 在重试时重建父目录

这能让并发写入者在其目录被清理删除后仍然成功（见[下文的竞争分析](#sufficiency)）。`reliableRename` 本身不做这项改动：`renameAll` 有许多调用方，这一改动恰好会在源路径不存在的情况下重新创建目标父目录，其中包括那些没有任何清理的调用方。

改为在 `RenameData` 中采用一个收窄的形式：只有当目标路径上的某级目录消失、而源仍然存在时，它的两次重命名才会重试并重建目录。源不存在（即迟到写入的情形）不重试；如果源在某次重试期间消失，随后的清理会处理。

## 修复方案 {#fix}

1. **数据重命名失败分支（PR #286）。** 在现有的数据目录清理之后，`RenameData` 调用

   ```go
   s.deleteFile(dstVolumeDir, pathutil.Dir(dstFilePath)+SlashSeparator, false, false)
   ```

   这个路径就是对象目录。不带递归时，`deleteFile` 只尝试删除这个目录本身；带末尾斜杠时，非空目录会返回“不存在”，调用方忽略这个结果，因此任何持有数据的东西都不会被删除。删除成功后，`deleteFile` 向上逐级删除变空的父目录，到桶目录为止。

   PR 增加了两个测试。`TestRenameDataStagedDataGoneLeavesNoPrefix` 在 16 盘集合上，用 8 MiB 对象的 `PutObject` 和 `CompleteMultipartUpload` 构造出报告中的状态，然后检查列举结果和磁盘内容。`TestRenameDataStagedDataGoneKeepsExistingObject` 检查覆盖写失败后旧对象仍然可读。
2. **提交失败分支（维护者补充）。** `RenameData` 末尾对 `xl.meta` 的重命名以同样的方式创建对象目录，它的失败分支也有同样的清理缺口。对于没有数据目录的写入，如果暂存的 `xl.meta` 在写入之后、提交之前消失，就会留下一个空的对象目录，无论是否应用 PR #286。这个分支也加上了同样的调用。`TestXLStorageRenameDataCommitMetaMissingRemovesEmptyDirs` 复用现有 `TestXLStorageRenameDataCommitMetaMissing` 中的 `missingCommitMetaContext` 钩子，它恰好在这一点删除暂存的 `xl.meta`。测试检查零字节写入和内联写入既不留下对象目录，也不留下空父目录；持有其他对象的父目录保留；在提交失败之前已经移入的数据目录保持原位。
3. **只删除目录的向上清理（维护者补充，由对抗性审查发现）。** 删除成功后，`deleteFile` 会向上逐级删除父目录。原来这一步调用删除时不带末尾斜杠，因此也会删除文件。在一次向上清理的两步之间，另一次清理可能删掉这条链上剩下的目录，随后某个写入者可能提交一个对象，其 `xl.meta` 恰好位于第一次清理下一步要删除的路径上：对 key `parent/xl.meta/child` 来说，这个对象就是 `parent`。于是清理会在发生这种交错的每块磁盘上删掉已提交的元数据。现在向上清理传入的父路径带末尾斜杠，只删除空目录，遇到其他任何东西都会停下。另一次清理既可能是新加的清理（这使得普通的失败写入就能触发这种交错），也可能是普通删除，所以这个隐患在修复之前就已存在。`TestXLStorageWalkUpKeepsCommittedObject` 分别通过 `DeleteVersion` 和两个清理分支复现了它。
4. **并发清理之后重试（维护者补充，由对抗性审查发现）。** 新的清理可能在另一个写入创建目标目录之后、重命名之前删除这个目录。原来那次写入即使源完好也会失败，发生在哪些磁盘上就在哪些磁盘上失败，按分支和操作不同，报 `IncompleteBody`（400）、`NoSuchKey`（404）或写仲裁错误。现在 `RenameData` 的两次重命名在某次尝试的目录创建或重命名报告“不存在”、而源仍然存在时重试。判断依据是这次尝试本身的错误，在它被映射为存储错误之前，因为另一个写入（例如嵌套 key 的写入）可能在判断之前重建这些目录。每次重试都会重新执行基准目录以下的目录创建；缓存基准目录的限制见[剩余限制](#limits)。一次清理向上逐级删除，路径上的每个目录最多删除一次，而每次失败的尝试至少需要多一次删除，所以写入最多按其基准目录以下的路径层数重试，任何单次清理都无法把重试耗尽。`TestRenameDataSurvivesConcurrentEmptyDirCleanup` 在 `PutObject`（8 MiB 和内联）或 `CompleteMultipartUpload` 刚创建目录之后，在全部 16 块磁盘上运行一次同一 key 的迟到失败 `RenameData`，检查迟到调用删除了目录，而写入仍然成功。`TestXLStorageRenameDataRetriesWhileCleanupWalksUp` 对 `a/b/object` 逐个删除 `object/`、`b/` 和 `a/`，每一步都紧跟在写入的下一次目录创建到达该目录之后，使这次清理先后挫败第一次重命名和下一次尝试中的两次目录创建；写入仍必须成功。第三个用例让 `a/b/object/child` 的写入在一次失败的目录创建之后立即重建这些目录。

PR #286 的测试辅助函数 `stagedDataGoneDisks` 现在在集合磁盘列表所用的锁下替换列表背后的磁盘，而不是替换那个后台任务不加锁读取的回调。

这两个重命名分支是 `RenameData` 为新 key 创建对象目录的仅有位置。第 3、4 项不改变目录在哪里创建，它们让清理对并发写入是安全的。

## 为什么方案充分且必要 {#sufficiency}

**充分性。** 报告中的目录是在失败的 `renameAll` 内部创建的。清理紧随其后，在同一块磁盘、同一次调用中执行，从对象目录开始向上，恰好删除那些为空的目录。加上提交分支的补充之后，没有数据目录的写入也同样成立。分段上传完成使用同一个 `RenameData`，PR 的测试覆盖了它。

**对数据安全。** 清理中的每一次删除，无论是第一次还是向上清理的每一步，都只删除空目录。任何使目录非空的内容都会让它保留下来：已有版本的 `xl.meta`、其他数据目录、旧格式数据，或同名路径下嵌套的对象。父路径上的文件（例如在此期间提交到那里的对象的 `xl.meta`）会让向上清理停下。把新清理改成递归删除的变体，会让 `TestRenameDataStagedDataGoneKeepsExistingObject` 和提交分支测试的 `data_directory` 用例失败；向上清理去掉末尾斜杠，会让 `TestXLStorageWalkUpKeepsCommittedObject` 失败，因此测试能发现这两种破坏性改动。

**同一个 key 的并发写入。** 迟到的 `RenameData` 在其调用方释放对象锁之后才执行，因此同一个 key 的另一个写入者可能同时到达这块磁盘，典型的是客户端的重试。如果该 key 在这块磁盘上没有 `xl.meta`，清理可能恰好在另一个写入者创建目录之后、重命名之前删除这个目录以及变空的父目录。一次失败写入的迟到调用会到达集合中的每块磁盘，所以这可能发生在任意数量的磁盘上。此时另一个写入者的重命名或目录创建失败，但它的源仍然存在，于是它重新创建目录并重试，最多每级路径一次。一次清理对每个目录最多删除一次，单靠它无法耗尽重试。只有当多次清理在所有重试中不断删除它的目录时，写入才会在这块磁盘上失败。这时纠删层把这块磁盘计为本次写入失败：

- 其他磁盘满足写仲裁时，写入成功，并尝试为这块磁盘排入一次 MRF heal；
- 不满足写仲裁时，写入整体失败，已经提交的磁盘会尽力回滚，客户端需要重试；
- 已提交的对象不会被删除：持有该 key `xl.meta` 的磁盘上，对象目录不为空，而向上清理遇到文件就会停下。

没有这个修复时，这种交错不会导致失败，所以修复引入了一种新的失败形态，重试把它收得很窄。但这一类问题并不新：在 main 上，比锁活得更久的操作已经可能改动单块磁盘，例如迟到提交或迟到回滚，SILO 对这条边界有文档记录。删除对象最后一个版本时，已经会用同一个 `deleteFile` 删除对象目录及其空父目录，而该存储 RPC 同样以 `context.Background()` 执行。其他 key 的写入者，会在清理恰好于其父目录创建之后、其自身目录创建之前删除该父目录时受到影响。这时 `reliableMkdirAll` 会从更高一级的基准目录重试一次，这和今天面对删除路径时完全一样；如果某个 key 自己的目录正是被删除的父目录之一，上面的重试会覆盖它。

**其他清理分支。** 除提交分支外，`RenameData` 还有针对旧格式数据的清理（`legacyPreserved`）。这个分支只在目标位置已有旧格式内容时执行，因此对象目录不为空；它自己的清理会递归删除旧格式数据目录，并且删除成功后已经会向上清理。它不需要改动。第一次 `renameAll` 之前的各个提前返回，都不会为新 key 创建对象目录。

**必要性。** 没有这项清理，就没有任何机制会删除这个目录：`deleteFile` 提前返回，遍历把它隐藏起来，heal 认为多数磁盘都持有的目录是有效的。这些目录会在每个仍有对象的前缀下持续累积，并在那些对象被删除时显现出来。

**有意排除的范围。** 已经留在磁盘上的目录不会被主动清扫（见[剩余限制](#limits)），迟到的 `RenameData` 本身也不会被阻止。

## 代价与兼容性 {#cost}

- 不改变 API、配置、存储格式、指标、路由或依赖。
- 成功的重命名不增加任何文件系统调用。某次尝试的目录创建或重命名报告“不存在”时，磁盘检查源是否仍然存在，存在则重试。重命名最终失败时，磁盘会对对象目录多做一次删除尝试，然后依次尝试每一级父目录，直到某次删除失败或到达基准目录为止；基准目录本身不会被删除。
- 只要这些目录为空且可以删除，失败的首次写入就不再在磁盘上留下对象目录。没有任何东西会读取空的对象目录，因此就这种情形而言，可见的行为变化在列举上。同一 key 的并发写入也有变化：它们现在可能看到自己的目录被删除，然后重试，见[充分性](#sufficiency)。
- 只删除目录的向上清理作用于 `deleteFile` 的所有调用方，包括对象删除和版本删除。它删除的空目录与之前相同，只是不再删除父路径上的文件。在 macOS 上，只含 Finder `.DS_Store` 文件的父目录不再被向上清理删除。
- 回滚即恢复旧行为，两个方向都不需要迁移。

## 剩余限制 {#limits}

- **存量遗留不会被清理。** 旧版本创建的目录不会被主动删除。在仍有对象的前缀下，它们保持不可见，直到那里的最后一个对象被删除才显现，所以升级之后仍可能出现新的空前缀。之后对同一个 key 写入再删除，会移除其中一个，下面的步骤也可以。
- **崩溃会留下同样的状态。** 如果进程或节点恰好在创建目录和重命名之间停止，清理不会执行。
- **路径只创建了一部分。** 如果创建路径中途失败（例如磁盘已满），已经创建的父目录会留下。清理从对象目录开始，而此时对象目录并不存在。
- **数据重命名之后的孤立数据目录。** 如果数据目录已经移入，而调用在 `xl.meta` 就位之前停止，数据目录会留在对象目录中，而没有 `xl.meta`。这发生在 `xl.meta` 的重命名失败时，或两次重命名之间的取消检查触发时（例如到了磁盘自己的截止时间）。这一点保持不变；代码有意不在这一步做递归删除。如果真的在一半磁盘上发生，它也会表现为一个前缀，下面的步骤可以清除它。
- **多次并发清理。** 重试能覆盖一块磁盘上的任意单次清理，即使另一个写入在其间重建了目录也是如此。如果多次清理在所有重试中不断删除某次写入的目录，这次写入仍会在这块磁盘上失败。当同样的失败发生在至少写仲裁数量的磁盘上时，客户端看到的错误取决于失败的步骤：目录创建失败时为 `AccessDenied`（403）；数据重命名失败时，`PutObject` 为 `IncompleteBody`（400），`CompleteMultipartUpload` 为 `NoSuchKey`（404）；`xl.meta` 重命名失败时为 `SlowDownWrite`（503）。否则，失去仲裁的写入报告写仲裁错误（503）。这些映射与 main 相同；在 main 上，删除空父目录的并发删除已经可能耗尽目录创建的那一次重试。
- **缓存的基准目录。** 覆盖写时，两次重命名把对象目录作为目录创建的基准，因为调用开始时它持有 `xl.meta`。在 Unix 上，如果它在此期间被别的操作删除，重试不会重建它；Windows 不使用这个基准目录。新的清理做不到这一点，因为该目录持有 `xl.meta`；这一限制与 main 相同。
- **迟到的 `RenameData` 仍会执行。** 它仍可能在 `.minio.sys/tmp` 下或分段上传目录中重新创建暂存的 `xl.meta`；测试显示，无论是否修复，每块磁盘上都会出现。这些路径属于内部路径，不会通过 S3 列出，现有的过期上传清理会在 `stale_uploads_expiry`（默认 24 小时）之后删除它们。对于内联对象，迟到的调用仍可能在调用方报告失败之后，在这块磁盘上提交元数据。这属于[存储超时与回滚边界](/zh/blog/design/multi-pool-object-consistency/#maintenance-20261026)中描述的迟到提交边界。

### 清理已有的空前缀 {#cleanup}

1. 确认前缀为空：`mcli ls --recursive --versions ALIAS/BUCKET/PREFIX/` 和 `mcli ls --recursive --incomplete ALIAS/BUCKET/PREFIX/` 都没有输出。
2. 确认已经没有客户端向该前缀写入。对 Iceberg 这类表格式来说，就是已经不再写入的分区。
3. 用 `mcli rm --force --purge ALIAS/BUCKET/PREFIX/` 删除列出的最深一级空前缀。服务端会在每个池、每个纠删集合的每块磁盘上递归删除该前缀，然后删除变空的父目录。在测试中，清除 `day=1/b=9/` 时，`day=1/` 也在全部 16 块磁盘上被删除。

强制删除是破坏性的。它会删除该前缀下的**全部**内容，包括所有版本，不留删除标记，且无法撤销。只对已经按第 1、2 步确认为空且无人使用的前缀执行。

知道空对象目录的名称时（例如 `day=1/b=9/put/` 中的 `put`），有一种非破坏性的替代办法。列举不会显示这个名称；可以从磁盘上读到，也可能从失败请求的日志或应用记录中得知。在这个确切的 key 上写入一个零字节对象，再把它删除；在启用版本控制的桶中，按版本 ID 删除。和删除其他对象一样，这次删除会移除对象目录以及每个变空的父目录。如果新对象会被施加默认保留期，这个办法不适用。

启用了 Object Lock 的桶会拒绝强制删除。除非知道叶子名称且不会施加保留期，否则对这些桶没有受支持的 S3 途径可以删除这样的前缀。这些目录不含数据，留在原处是安全的，但读取每个列出前缀的工具必须能容忍它们。不要手工修改磁盘内容。

## 验证 {#verification}

使用 Go 1.27.3（darwin/arm64），在一次性工作树中，针对 main 69fcf50cd、PR head 和修复版本实际执行：

- **回归测试在没有修复时失败、修复后通过。** 在 main 上只加入测试文件时：
  - `TestRenameDataStagedDataGoneLeavesNoPrefix` 失败：根目录列举返回 `day=1/`，`day=1/` 返回 `day=1/b=9/`，`day=1` 在 16 块磁盘中的 16 块上仍然存在；
  - 提交分支测试在零字节写入和内联写入上失败，它们留下了对象目录；
  - `TestXLStorageWalkUpKeepsCommittedObject` 的三个用例都失败：经由 `DeleteVersion` 时已提交的对象 `parent` 丢失，经由两个 `RenameData` 分支时空目录没有被删除；
  - `TestRenameDataSurvivesConcurrentEmptyDirCleanup` 失败，因为迟到调用在全部 16 块磁盘上留下了对象目录；
  - `TestXLStorageRenameDataRetriesWhileCleanupWalksUp` 失败，因为写入扛不过第一次删除。

  只应用 PR head 时，提交分支测试仍然失败，`TestXLStorageWalkUpKeepsCommittedObject` 丢失已提交的对象，`TestRenameDataSurvivesConcurrentEmptyDirCleanup` 的三次写入全部失败，分别报 `IncompleteBody`、`NoSuchKey` 和写仲裁错误。应用修复后，以上测试全部通过，`-race` 下也通过。在 16 块磁盘的每一块上，对 `a/b/object` 运行一次迟到的 `RenameData`，并在其向上清理的每次删除处暂停，使它在写入的第一次重命名和下一次尝试的两次目录创建期间依次删除 `object/`、`b/` 和 `a/`：当写入只重试一次时，`PutObject` 和 `CompleteMultipartUpload` 都以 `AccessDenied` 失败。再加上一个 `a/b/object/child` 的写入在一次失败的目录创建之后立即重建目录时，如果重试判断是在尝试之后检查目标路径，也会出现同样的失败。应用修复后，两种调度下两次写入都成功。
- **守护测试能发现破坏性的变体。** 数据分支的递归清理会让 `TestRenameDataStagedDataGoneKeepsExistingObject` 失败，提交分支的递归清理会让 `data_directory` 用例失败。向上清理去掉末尾斜杠会让 `TestXLStorageWalkUpKeepsCommittedObject` 失败。去掉重试会让 `TestRenameDataSurvivesConcurrentEmptyDirCleanup` 失败；只允许重试一次会让 `TestXLStorageRenameDataRetriesWhileCleanupWalksUp` 以 access denied 失败；在尝试之后检查目标路径来判断是否重试，会让它的嵌套写入用例以同样方式失败。对照测试在 main 上和修复后都通过：`TestRenameDataStagedDataGoneKeepsExistingObject`、`TestXLStorageRenameDataCommitMetaMissing`、`TestRenameDataCommitMetaMissing`，以及 `data_directory` 用例。
- **测试辅助函数。** 在 `-race` 下，集合磁盘列表的一个并发读取者与 PR 的 `stagedDataGoneDisks` 会报数据竞争，与修订后的辅助函数则不会。
- **列举仲裁。** 空目录留在 16 块盘中的 7 块上时，不列出任何前缀；留在 8 块和 16 块上时会列出。所有情况下，递归列举、`ListObjectVersions` 和 `HEAD` 都找不到任何内容。
- **清理步骤。** 在对象层，强制删除选项在全部 16 块磁盘上删除了幽灵前缀 `day=1/b=9/` 这一整条目录链；同一选项作用于另一个前缀时，也删除了其下的真实对象。在未启用版本控制的桶中，对叶子 key 做一次零字节 `PutObject` 再 `DeleteObject`，不用强制删除就移除了这条目录链。
- **附带观察。** 1 KiB 的内联 `PutObject` 即使在 `RenameData` 之前删除了暂存目录也会成功，因为它的数据随请求一起传输。失败的调用之后，无论是否修复，暂存的 `xl.meta` 都会在全部 16 块磁盘的 `.minio.sys/tmp` 和分段上传目录中被重新创建；`ListMultipartUploads` 不报告任何上传。数据重命名之后的取消会留下没有 `xl.meta` 的数据目录，在 main 上和修复后都一样。
- **相邻测试。** 应用修复后，`go vet ./cmd` 通过；由 `^Test(XLStorage|XlStorage|Erasure|DeleteObject|DeleteFile|DeleteVersion|RenameData|PutObject|CompleteMultipart|ObjectComplete|Heal|ListObjects|Walk|Metacache|StorageTimeout|StorageRollback|ReduceWriteQuorumErrs|Multipart|ObjectNewMultipart|NewMultipart|Lifecycle|Decommission|Rebalance|Disk|Posix|Abort|CopyObject|GetObject|Rename|Reliable|OsMkdir|MkdirAll)` 选出的 137 个测试（含新增测试）全部通过。PR #286 的 CI 检查在其 head 上全部通过。

仅由代码推断、未实际执行：

- 远端时序窗口本身，没有多节点的现场复现；
- 写入因多次并发清理而失去一块磁盘之后，最终的 heal；
- 旧格式分支、路径部分创建、崩溃情形，以及内联对象的迟到提交；
- 过期上传清理对重新创建的暂存元数据的删除；
- 启用版本控制的桶中的清理替代办法、`mcli rm --force --purge` 会发送强制删除请求头，以及 Object Lock 桶的拒绝行为；
- Linux 和 Windows 文件系统上的末尾斜杠语义；测试在 macOS 上运行，两个调度目录创建的测试在 Windows 上跳过，因为那里的目录创建没有跟踪；
- 上游历史。

本记录没有运行完整的 `./cmd` 测试。

**集成验证。** 这个修复已摘取到下个版本的同一个集成分支上，位于 #278 和 #281 之后，与锁域、删除全部版本、Heal 演练、#259 和 Console 的修复放在一起。所有摘取都没有冲突。在该 head 上，完整的 `go test ./cmd/... ./internal/...` 套件通过，CI 的竞态检测选集和覆盖全部新测试的竞态选集也都通过。针对组合的对抗性审查没有发现缺陷，锁域、清理路径以及清除与恢复之间的交互都用实际执行的探针检查过。

## 审查记录 {#review}

| 轮次 | 结果 |
| --- | --- |
| 对抗性审查第 1 轮 | 要求修改。删除之后的向上清理可能删除父路径上的文件，因此对于 `parent/xl.meta/child` 这样的 key，新的清理或普通删除都可能删掉在此期间提交的对象的 `xl.meta`；以只删除目录的向上清理修复（第 3 项），这个问题在 main 上经由删除也能触发。清理可能删除另一个写入刚创建的目录，使那次写入以 400 或 404 失败；以重试修复（第 4 项）。PR 的测试辅助函数与磁盘列表的后台读取者存在竞争；已修复。记录做了十处更正。 |
| 第 2 轮 | 要求修改。每块磁盘一次迟到调用，在写入重试期间依次删除各级父目录，就耗尽了唯一的一次重试并返回 403。现在重试最多每级路径一次。没有把耗尽后的失败改判为 503，剩余问题记录在[剩余限制](#limits)中。记录做了七处更正。 |
| 第 3 轮 | 要求修改。嵌套 key 的写入在一次失败的尝试之后重建目录，使重试判断看不到这次失败；现在判断依据是这次尝试本身的错误。两个调度目录创建的测试在 Windows 上跳过。概述与清理指引保持一致。 |
| 第 4 轮 | 附带小修改批准：关于缓存基准目录和清理过程的三处措辞更正，已应用。 |

## 参考 {#references}

- Issue：[#285](https://github.com/pgsty/silo/issues/285)
- 贡献者 PR：[#286](https://github.com/pgsty/silo/pull/286)
- 提交元数据错误分类：[#232](https://github.com/pgsty/silo/pull/232) 与[写入提交错误](/zh/reference/s3-api-compatibility/#write-commit-errors)
- 迟到操作边界：[存储超时与回滚边界](/zh/blog/design/multi-pool-object-consistency/#maintenance-20261026)
- 清理调用的上游来源：[minio/minio#12452](https://github.com/minio/minio/pull/12452)
