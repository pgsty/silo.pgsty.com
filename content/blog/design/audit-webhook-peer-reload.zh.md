---
title: "Peer 重载后的审计 Webhook"
linkTitle: "审计 Webhook 的 Peer 重载"
date: 2026-11-04
lastmod: 2026-11-05
author: "PGSTY SILO 维护团队"
summary: >
  解释运行时修改 audit_webhook 后，为什么除了处理该请求的服务器以外，其他每台服务器上的 Webhook 目标一创建，worker 就已经退出；哪些子系统有同样的缺陷；以及为什么用服务器进程上下文构建日志目标，是最小而完整的修复。
tags: [设计, 审计, 日志, 配置, 运维]
weight: 10
draft: false
url: "/zh/blog/design/audit-webhook-peer-reload/"
---

本文覆盖 Henrik Feldt 报告的 [issue #259](https://github.com/pgsty/silo/issues/259)，基于 main [69fcf50cd](https://github.com/pgsty/silo/commit/69fcf50cd2e0854af0150413df5fd66a5d74becc) 评估。本修复完成了维护者此前未提交的工作：补上 Kafka 调用点，在目标从未启动时把排队记录交给替代者，并增加 Kafka 测试覆盖。修复已在本地提交，尚未提交 pull request。

**状态：** 修复已通过审查，已在本地提交。它已和下个版本的其他修复放在同一个集成分支上一起测试：完整测试套件、CI 竞态检测选集，以及针对修复之间相互作用的对抗性审查，全部通过。尚未合并或发布。

## 简短结论 {#tldr}

报告属实，一个定向测试即可复现。管理员在运行时修改 `audit_webhook` 时，接收请求的服务器用进程上下文应用这次修改；其他每台服务器在 peer 重载处理函数里应用它，使用的是一个 30 秒的上下文，处理函数一返回就被取消。HTTP Webhook 目标把它唯一的队列 worker 绑定在初始化时传入的上下文上；配置了 `queue_dir` 时，磁盘重放也绑定在这个上下文上。因此，除一台服务器外，其他每台服务器上的新目标在创建后立刻失效。记录在内存中排队，直到达到 `queue_size`，此后的每条记录都以 `log buffer full` 被丢弃。没有任何机制会重新启动 worker。可靠的恢复方式是重启受影响的服务器，因为启动时用进程上下文构建目标。如果之后的一次修改恰好由受影响的服务器处理，这台服务器会恢复，但其他服务器上的目标会再次停止。

同样的缺陷还影响 `logger_webhook`（无论是否配置 `queue_dir`），以及配置了 `queue_dir` 的 `audit_kafka`。其他动态子系统都没有把长期运行的工作绑定到重载上下文上。

修复分三部分：

1. **用进程上下文构建目标。** `applyDynamicConfigForSubSys` 在其三处日志目标调用点使用进程上下文（`GlobalContext`）构建日志目标。启动、处理请求的服务器和 peer 节点都通过这一个函数应用配置。日志输出仍然使用重载上下文。
2. **先打开队列存储，再启动磁盘队列 worker。** HTTP 磁盘队列 worker 只在队列存储成功打开之后才启动。现在的代码先启动 worker；如果存储打不开，worker 会在没有存储的情况下继续运行，并在收到第一条记录时让服务器崩溃。这在启动时和处理请求的服务器上已经会发生。没有这一部分，第一部分会把这个崩溃扩散到每一台服务器。
3. **排队记录跟随替代目标。** 有了第 2 部分，队列无法打开的目标没有 worker，它的记录在内存中等待。之后的重载替换这个目标时，`Cancel` 现在会在共享交接缓冲区容量允许的范围内，把这些记录交给替代目标，而不是丢弃。

## 定性 {#assessment}

| 维度 | 判断 |
| --- | --- |
| 性质 | peer 配置重载中的上下文生命周期缺陷：长期存在的日志目标被绑定在一个随请求结束的上下文上。继承自上游，不是已发布 SILO 版本引入的回归。 |
| 受影响部署 | 多于一台服务器，并且在运行时通过 `mc admin config set` 或 `mc admin config reset` 修改了 `audit_webhook` 或 `logger_webhook`（无论是否配置 `queue_dir`），或修改了配置了 `queue_dir` 的 `audit_kafka`。同时更新 `logger_webhook` 的 `subnet` 代理修改也走同一条路径。 |
| 不受影响 | 单服务器部署；启动时就已存在、运行时从未修改的目标；处理该管理请求的服务器；未配置 `queue_dir` 的 `audit_kafka`；其他所有动态子系统（见[逐项排查](#sweep)）。 |
| 严重程度 | 高。除一台服务器外，其他所有服务器上的审计记录都会被丢弃，直到这些服务器重启，或者自己处理了之后的一次修改。管理命令报告成功，S3 请求也正常完成；丢弃只体现在服务器日志和日志目标指标中，因此这个缺口往往在审计复核中才被发现，而不是在日常运维中。审计 Webhook 若是合规控制的一部分，这段时间的审计记录就不完整，而且无法重建。 |
| 可达性 | 一条常规管理命令即可触发。修改其中一个目标会重建该子系统中所有启用的目标，因此在其他服务器上它们会全部停止，而不只是被修改的那一个。 |
| 发布紧急度 | 阻塞下一个版本。审计丢失不会报告给管理端或 S3 客户端，并一直持续，直到受影响的服务器重启，或自己处理之后的一次修改；而改动很小，不触及 S3 数据路径。 |
| 剩余工作量 | 代码和审查已完成。还需要远程 CI 和一次三服务器验收。 |

## 触发条件 {#trigger}

1. `mc admin config set ALIAS audit_webhook:NAME enable=on endpoint=…` 到达服务器 A。A 校验并保存配置，通过 `applyDynamic` 应用修改，后者以 `GlobalContext` 调用 `applyDynamicConfigForSubSys`。随后 A 通知每个 peer 重载该子系统（`SignalConfigReload`）。
2. 在每个 peer 上，`SignalServiceHandler` 处理 `serviceReloadDynamic`：读取已保存的配置，在 `context.WithTimeout(context.Background(), 30*time.Second)` 下调用 `applyDynamicConfigForSubSys`，并延迟执行 `cancel`。
3. `updateHTTPTargets` 为该子系统中每个启用的 Webhook 创建新目标，用这个上下文初始化每一个，然后替换目标列表，并取消旧目标。
4. 处理函数返回，上下文被取消，新目标的主 worker 从 `startQueueProcessor` 返回。额外的 worker 共享同一个上下文，也会被要求停止，而且没有任何机制会启动新的 worker。
5. 该服务器上的审计日志仍在调用 `Send`。`Send` 把记录放入目标的通道，直到达到 `queue_size`（默认 100000）；此后返回 `log buffer full`，服务器日志输出 ``Unable to send audit event(s) to the target `NAME`: log buffer full``。

报告者的节点指标展示了这一模式。三台服务器中，`config set` 在服务器 0 上执行，以下数据取自 7.5 小时之后：

| 服务器 | `target_queue_length` | `failed_messages` | `total_messages` |
| --- | --- | --- | --- |
| 0（处理该请求） | 0 | 4 | 2,097,356 |
| 1 | 100000 | 674,917 | 774,917 |
| 2 | 100000 | 712,215 | 812,215 |

在这份报告中，服务器 1 和 2 上的 `total_messages` 减去 `failed_messages` 正好等于队列长度，这与这两台服务器没有发送出任何记录的情况一致。

三种变体的表现如下：

- **配置了 `queue_dir` 的 HTTP Webhook。** 把记录写入磁盘队列的就是同一个 worker，磁盘重放也随同一个上下文停止。新记录永远到不了磁盘，而是像上面那样填满内存队列。修改之前已在磁盘上的记录会保留，重启后在端点可达时重放；内存队列中的记录在服务器重启时丢失。
- **配置了 `queue_dir` 的 Kafka。** `Send` 直接写入磁盘队列，但 `initQueueStore` 启动的重放 goroutine 随上下文停止。记录在磁盘上堆积到 `queue_size`，之后 `Send` 以 `the maximum store limit reached` 失败。重启后，一旦 broker 可达，重放会发送磁盘上的记录。Kafka 目标的队列长度指标只统计内存通道，而这种模式不使用内存通道；它的消息计数也只在重放发送时变化。因此这些指标保持不变。
- **未配置 `queue_dir` 的 Kafka。** 不受影响。连接 broker 时不使用这个上下文，发送循环也不监听它。

## 根因 {#root-cause}

日志目标 `Init` 的 `ctx` 参数承担了两个职责：它是初始化调用的上下文，同时也是目标中 goroutine 的生命周期。`initMemoryStore` 和 `initDiskStore` 用 `context.WithCancel(ctx)` 派生 worker 上下文，并保留取消函数供 `Cancel` 使用；`startQueueProcessor` 在这个上下文结束时返回。因此，一个目标在 `Cancel` 被调用或调用方上下文结束时停止工作，以先发生者为准。两者都只是请求关闭；关闭不能及时完成的情形见[剩余限制](#limits)。

在启动时（`lookupConfigs`）和处理请求的服务器上，调用方上下文是 `GlobalContext`，目标一直存活到被替换或服务器关闭，这正是预期的生命周期。在 peer 上，调用方上下文在 RPC 处理函数返回时就结束了，也就是目标创建后的几毫秒。

这个 30 秒的上限在这里什么都没有保护。在 `applyDynamicConfigForSubSys` 中，这个上下文只用于日志调用、配置查找（同样只用于日志）和目标的 `Init`。HTTP 的 `Init` 不做任何网络 I/O：它启动一个 goroutine，配置了 `queue_dir` 时再打开一个本地目录。Kafka 目标在 `init()` 中连接 broker，而 `init()` 不接收上下文，由客户端自己的拨号和元数据超时约束。

## 子系统逐项排查 {#sweep}

`config.SubSystemsDynamic` 中的每个子系统都走同一条重载路径。对每个子系统要问的是：`applyDynamicConfigForSubSys` 是否创建了在调用返回后仍持有这个上下文的 goroutine 或对象。

| 子系统 | 重载时做什么 | 结论 |
| --- | --- | --- |
| `logger_webhook` | `logger.UpdateHTTPWebhooks(ctx, …)` → `Init(ctx)`：队列 worker，配置 `queue_dir` 时还有磁盘重放 | **受影响**，无论是否配置 `queue_dir` |
| `audit_webhook` | `logger.UpdateAuditWebhooks(ctx, …)`，同一路径 | **受影响**，无论是否配置 `queue_dir` |
| `audit_kafka` | `logger.UpdateAuditKafkaTargets(ctx, …)` → `Init(ctx)` → `initQueueStore`：以 `ctx.Done()` 启动磁盘重放 | **配置 `queue_dir` 时受影响**；未配置时发送循环不使用该上下文 |
| `api` | `globalAPIConfig.init`、`setRemoteInstanceTransport` | 不受影响：只设置值和一个 transport，不涉及上下文 |
| `ilm` | `UpdateWorkers`、`ResizeWorkers` | 不受影响：这些 worker 使用 transition 和 expiry 状态自身的上下文 |
| `scanner` | 原子写入、`scannerSleeper.Update` | 不受影响 |
| `subnet` | `Update`、`ApplyEnv` | 本身不受影响；修改代理时可能连带重新应用 `logger_webhook` |
| `compression`、`heal`、`batch`、`storage_class`、`drive`、`browser`、`callhome` | 在锁内替换一个配置值 | 不受影响 |

在 main 上，通知目标和 Lambda 目标都不是动态子系统。

issue 中有两处描述比实际范围宽。peer 处理函数中针对整份配置的分支（`applyDynamicConfig`）使用同一个上下文，但目前没有任何管理路径会发送不带子系统的重载。`mc admin config import` 只保存配置，需要重启生效，不会通知 peer。

## 行为的来源 {#history}

### 溯源

**由上游 MinIO 引入，不是 SILO 引入的。** 每一个成因都是上游提交，并且都是 SILO 分叉点（[`27742d469`](https://github.com/pgsty/silo/commit/27742d469)，2025-12-03）的祖先；SILO 没有任何提交改动过相关函数。同样的代码存在于分叉前最后一个上游发布 `RELEASE.2025-10-15T17-29-55Z`、已归档的上游 `master`，以及从 `RELEASE.2025-12-03T12-00-00Z` 到 `RELEASE.2026-10-26T00-00-00Z` 的每一个 SILO 发布中。我们逐个 tag 比对了代码：worker 先于存储启动的顺序、绑定上下文的重放、30 秒上下文，在所有 tag 上都相同。

这个缺陷需要两个条件同时成立：随处理函数结束而结束的重载上下文，以及生命周期与 `Init` 所收上下文一致的日志目标 goroutine。它们来自不同的提交：

| 成因 | 提交（PR） | 日期 | 首个上游发布 |
| --- | --- | --- | --- |
| peer 重载在请求上下文中应用子系统，该上下文随处理函数返回而结束。 | [`a89612549`](https://github.com/pgsty/silo/commit/a89612549)（[#11018](https://github.com/minio/minio/pull/11018)）；按子系统的形式 [`040ac5cad`](https://github.com/pgsty/silo/commit/040ac5cad)（[#14928](https://github.com/minio/minio/pull/14928)） | 2020-12-04；2022-05-16 | `RELEASE.2020-12-10T01-54-29Z`；`RELEASE.2022-05-19T18-20-59Z` |
| grid 改造后生命周期不变：`serviceReloadDynamic` 创建 30 秒上下文并延迟 `cancel`。 | [`e06168596`](https://github.com/pgsty/silo/commit/e06168596)（[#19004](https://github.com/minio/minio/pull/19004)） | 2024-02-19 | `RELEASE.2024-02-24T17-11-14Z` |
| 日志与审计 Webhook、审计 Kafka 变为可在运行时重载。 | [`28f188e3e`](https://github.com/pgsty/silo/commit/28f188e3e)（[#14289](https://github.com/minio/minio/pull/14289)）、[`3934700a0`](https://github.com/pgsty/silo/commit/3934700a0)（[#14390](https://github.com/minio/minio/pull/14390)） | 2022-02-17、2022-02-24 | `RELEASE.2022-02-17T23-22-26Z`、`RELEASE.2022-02-24T22-12-01Z` |
| `Init` 开始接收上下文。HTTP 目标和 Kafka 的磁盘重放（`initQueueStore`）随它停止，HTTP worker 用它发送。 | [`57acacd5a`](https://github.com/pgsty/silo/commit/57acacd5a)（[#17121](https://github.com/minio/minio/pull/17121)） | 2023-05-09 | `RELEASE.2023-05-18T00-05-36Z` |
| HTTP 队列 worker 在 `Init` 上下文结束时返回。 | [`1fc4203c1`](https://github.com/pgsty/silo/commit/1fc4203c1)（[#19275](https://github.com/minio/minio/pull/19275)） | 2024-03-25 | `RELEASE.2024-03-26T22-10-45Z` |
| 磁盘队列 worker 在队列存储打开之前启动。 | [`ba54b39c0`](https://github.com/pgsty/silo/commit/ba54b39c0)（[#19854](https://github.com/minio/minio/pull/19854)） | 2024-06-01 | `RELEASE.2024-06-04T19-20-08Z` |

每一步改变了什么：

- **在 #17121 之前，这个缺陷不会发生。** `Init` 和 HTTP worker 都不接收上下文，peer 的上下文无法停止目标，尽管当时重载已经运行在请求上下文中。
- **从 #17121（`RELEASE.2023-05-18T00-05-36Z`）起**，重载上下文能传到目标。设置了 `queue_dir` 时，HTTP 目标和 Kafka 的磁盘重放会在处理函数返回时停止，这就是本记录中带 `queue_dir` 的 Kafka 情形。没有 `queue_dir` 的 HTTP worker 用同一个上下文发送，发送会以 `context canceled` 失败，而不是进入队列。
- **从 #19275（`RELEASE.2024-03-26T22-10-45Z`）起**，HTTP worker 在上下文结束时返回。这就是报告中的现象：记录在内存中等待，直到 `queue_size`，之后以 `log buffer full` 被丢弃。
- **#19854（`RELEASE.2024-06-04T19-20-08Z`）** 修复的是 #19275 重构按其自身说明引入的一次崩溃。它把队列存储的打开移入 `initDiskStore`，但 worker 的启动仍在它之前。这个顺序就是[修复方案](#fix)中描述的崩溃。在 peer 上它大多不可见，因为 worker 通常在第一条记录到达之前就已随重载上下文退出。
- **#19004 没有改变生命周期。** 原来的请求上下文同样在处理函数返回时结束。如[根因](#root-cause)一节所述，30 秒的限制没有保护任何东西。

**SILO 的改动。** 没有任何 SILO 提交改动过 `SignalServiceHandler` 中的 peer 重载分支、`initDiskStore`、HTTP worker、Kafka 的 `initQueueStore`，或 `applyDynamicConfigForSubSys` 中的日志分支。靠近这些代码的 SILO 提交，没有引入、扩大或缩小这个缺陷：

- [`9b11dc946`](https://github.com/pgsty/silo/commit/9b11dc946)（2026-09-03）在这些文件中把 `minio/pkg` 的导入路径换成了 `silo-pkg`。
- [`011b0df5f`](https://github.com/pgsty/silo/commit/011b0df5f)（2026-10-23）在 broker 客户端初始化中设置了默认的 Kafka 协议版本，该处不接收上下文。
- [`5cb900bfa`](https://github.com/pgsty/silo/commit/5cb900bfa) 和 [`079ebb192`](https://github.com/pgsty/silo/commit/079ebb192)（2026-09-07 与 2026-09-08）让系统目标的注册具备幂等性并串行化。只有控制台日志使用这条路径，Webhook 重载不经过它。
- [`77bdc4c0c`](https://github.com/pgsty/silo/commit/77bdc4c0c)、[`7a060cab1`](https://github.com/pgsty/silo/commit/7a060cab1)、[`9b76a2167`](https://github.com/pgsty/silo/commit/9b76a2167) 改动的是 `applyDynamicConfigForSubSys` 中其他子系统的分支（callhome，以及后来被撤销的 ILM 访问分层 worker）。

**证据。** 每个成因在各 tag 上是否存在，以及这些函数中没有 SILO 改动，都是在 git 历史中核对的。#17121 到 #19275 之间的行为来自对代码的阅读，我们没有运行那些旧版本。当前行为由[验证](#verification)一节所述的测试复现。

相关：仍处于开放状态的 [PR #249](https://github.com/pgsty/silo/pull/249) 为通知 Webhook 增加了热重载，出于同样的原因用 `GlobalContext` 构建目标。[IAM 策略重载记录](/zh/blog/design/iam-policy-cancellation/)讨论的是相反的情形：请求内的工作必须跟随请求上下文。

## 方案比较 {#options}

### 方案 A：在日志调用点使用进程上下文

这是选定的方案。`applyDynamicConfigForSubSys` 向三处日志目标更新传入 `GlobalContext`，日志输出继续使用调用方的上下文。所有入口都通过这个函数应用配置，所以一处修改就覆盖了启动、处理请求的服务器和 peer。生命周期的决定放在创建长期对象的地方，与调用方传入什么无关。PR #249 对通知目标采用的也是这种做法。

### 方案 B：在日志包内部解除绑定

`updateHTTPTargets` 或 `Init` 可以用 `context.WithoutCancel` 包装上下文，从而保护所有调用方。但这也会让目标脱离 `GlobalContext`：关闭服务器时取消 `GlobalContext`，目标将不再随之停止。这改变了启动时构建的目标的关闭行为，而这与本缺陷无关。它还会留下一个取消信号被悄悄忽略的 `ctx` 参数。如果要由日志包掌管生命周期，应当去掉这个参数（方案 D）。

### 方案 C：在 peer 处理函数中使用进程上下文

`serviceReloadDynamic` 可以传入 `GlobalContext`，只为真正有界的工作保留 30 秒上限。目前并没有这样的工作（见[根因](#root-cause)），所以这样同样能修复缺陷。但它修的是调用方，而不是创建长期对象的那个函数。任何其他使用短上下文的调用方，例如测试或将来的处理函数，都会再次掉进同一个陷阱。这是可接受的备选，但不是首选。

### 方案 D：由目标自己掌管生命周期

把 `Init` 拆成两步：在调用方上下文中完成的初始化，以及一个生命周期归目标所有、只随 `Cancel` 结束的启动。这是长期正确的形态，但它会修改 `logger.Target` 接口和所有实现（HTTP、Kafka、console、测试 logger）。修复本缺陷并不需要它，因此留作后续候选。

### 决策背后的问题

- **是否有某个 `Init` 依赖这 30 秒上限？** 没有。HTTP 的 `Init` 不做网络 I/O，Kafka 连接 broker 时不使用这个上下文。2024 年 3 月重构之前，HTTP 初始化会用这个上下文探测端点；现在已经不这样做了。
- **反复重载会不会泄漏 goroutine？** 不会因为这次修改而泄漏。每次重载时，`updateHTTPTargets` 让每个旧目标指向它的替代者（`AssignMigrateTarget`），调整共享的遗留记录缓冲区大小（`CreateOrAdjustGlobalBuffer`），启动新目标，然后在后台对旧目标调用 `Cancel`。`Cancel` 把目标标记为已关闭，此后的 `Send` 会转给替代者（如果有的话）；它取消目标自己的上下文，请求 worker 和磁盘重放停止；等待 worker 把遗留记录交给共享缓冲区；把通道中仍有的记录交出去（修复的第 3 部分）；最后关闭通道。旧目标的关闭一直由 `Cancel` 掌管，而不是由调用方上下文掌管，所以改用 `GlobalContext` 不会让每次重载多出 goroutine。审查中的一个探测在两种队列模式下，对空闲目标各连续执行 100 次重载再禁用，goroutine 数量回到初始值；这不涵盖有积压或磁盘写入失败时的关闭。在 main 上，peer 上旧目标的 worker 早已退出，它退出后堆积的记录会在通道关闭时被丢弃，这就是通过同一台服务器再执行一次 `config set` 也救不回 peer 的原因。与本修复无关、早已存在的例外，见[剩余限制](#limits)。

## 修复方案 {#fix}

1. **用进程上下文构建日志目标。** 在 `applyDynamicConfigForSubSys` 中，向 `logger.UpdateHTTPWebhooks`、`logger.UpdateAuditWebhooks` 和 `logger.UpdateAuditKafkaTargets` 传入 `GlobalContext`，错误报告继续使用调用方的上下文。此前的候选修复覆盖了两处 HTTP 调用点；Kafka 调用点在配置 `queue_dir` 时有同样的缺陷，补上它之后修复才完整。
2. **先打开队列存储，再启动磁盘队列 worker。** 现在的 `initDiskStore` 先启动主 worker，再打开队列存储。如果打开失败，例如 `queue_dir` 无法创建或不是目录，`Init` 会返回错误，但目标仍被注册，它的 worker 也仍在没有存储的情况下运行。收到第一条记录时，worker 对不存在的存储调用 `PutMultiple`，服务器随即 panic。目前这会发生在启动时和处理请求的服务器上，因为那里的上下文一直存活。在 peer 上，worker 通常先随重载上下文退出，崩溃因此大多被掩盖；但如果 worker 在重载上下文结束前取到了一条记录，仍然会崩溃。因此，单独应用第 1 部分，会把静默丢弃变成每一台服务器上的崩溃。修复先打开存储：失败时取消派生的上下文并返回，不启动 worker；成功时先设置存储，再启动 worker 和重放。这同时消除了一个数据竞争：当先前的目标在共享缓冲区中留有记录时，worker 可能在 `Init` 设置存储字段的同时读取它。失败的 `Init` 也不再遗留 worker。
3. **把排队记录交给替代目标。** 有了第 2 部分，队列存储打开失败的目标没有 worker。发给它的记录在其通道中等待，最多 `queue_size` 条。没有任何机制会重试初始化：运维人员修复 `queue_dir` 后再次应用配置，这次重载会构建一个替代目标。只有 worker 会把记录交给替代目标，因此 `Cancel` 原本会关闭通道并丢弃这些记录。现在 `Cancel` 会把通道中仍有的记录移入替代目标读取的共享缓冲区：在等待 worker 的 `wg.Wait()` 调用返回之后、关闭通道之前进行，期间持有通道锁和缓冲区映射锁，发送时从不等待空位。如果共享缓冲区已满，其余记录被丢弃，与 worker 自身的交接一致。它也覆盖了在 worker 最后一次排空之后才到达的记录。单个失败目标被一个正常目标替换时，它的记录会全部交出；多个失败目标在短时间内相继被替换时，缓冲区仍可能装不下（见[剩余限制](#limits)）。
4. **回归测试。** `TestDynamicWebhookOutlivesConfigContext` 覆盖 `audit_webhook` 和 `logger_webhook`，每个都包括内存队列、磁盘队列和一个无法打开的磁盘队列；还覆盖配置与未配置 `queue_dir` 的 `audit_kafka`。每种情况都在短上下文中通过 `applyDynamicConfigForSubSys` 应用子系统，像 peer 处理函数那样取消上下文，然后发送一条记录并要求送达。Kafka 的情况使用 Kafka 客户端库自带的模拟 broker，要求在重载上下文结束之后仍有生产请求到达；未配置 `queue_dir` 的 Kafka 不受影响，因此那一项作为对照。在无法打开的情况下，存储不可用期间记录必须保持在队列中；随后测试修复目录并再次应用配置，替代目标必须送达这条记录。每种情况在去掉日志与审计环境变量的子进程中运行，使全局目标注册表不会在各情况之间互相影响。

## 为什么方案充分且必要 {#sufficiency}

**充分性。** 运行中的服务器里，每个日志 Webhook 或 Kafka 目标都由 `applyDynamicConfigForSubSys` 构建：启动时经由 `lookupConfigs` 和 `applyDynamicConfig`，在处理请求的服务器上经由 `applyDynamic`，在 peer 上经由 `serviceReloadDynamic`。这三个更新函数的其他调用方只有测试。有了第 1 部分，每条路径都用进程上下文构建目标，peer 上目标的生命周期与处理请求的服务器相同。逐项排查没有发现其他子系统把长期工作绑定到重载上下文上。旧目标仍由掌管其关闭的 `Cancel` 停止，限制见[剩余限制](#limits)。

**必要性。** 每一部分都关闭一条否则会继续存在的路径：

- 三处调用点都会从这个上下文启动 goroutine：HTTP 队列 worker、HTTP 磁盘重放和 Kafka 磁盘重放。漏掉任何一处，对应的变体在 peer 上仍然失效。
- 没有第 2 部分，无法打开的 `queue_dir` 会让任何一台由 worker 收到记录的服务器崩溃。有了第 1 部分，每台服务器上的 worker 都存活，因此每一台服务器都会在收到第一条审计或日志记录时崩溃，而不再大多只是处理请求的那台。
- 没有第 3 部分，修复这样的 `queue_dir` 并再次应用配置时，失败目标已接受的所有记录都会被丢弃。
- 没有测试，就没有什么能阻止 peer 路径再次与处理请求的服务器产生偏差。

**有意排除的范围：**

- peer 处理函数保留 30 秒上下文，它对所覆盖的日志输出仍然是正确的。
- 不在日志包中使用 `context.WithoutCancel`，也不修改 `logger.Target` 接口（方案 B 和 D）。
- 早已存在、但不会造成本症状的行为留给单独的 issue，列在[剩余限制](#limits)中。

## 代价与兼容性 {#cost}

- 不改变 API、配置、指标、存储格式或依赖。
- peer 上目标的生命周期与处理该管理请求的服务器相同。因此，下面列出的早已存在的替换与关闭限制现在同样适用于 peer。
- 一处可见变化：无法打开的 `queue_dir` 不再在启动时或处理请求的服务器上导致崩溃。目标仍被注册，错误会被记录（`Unable to update audit webhook targets: …`）；记录在内存中排队到 `queue_size`，之后以 `log buffer full` 丢弃，与任何无法发送的目标一样。目录修复并再次应用配置后，替代目标会在共享交接缓冲区容量允许的范围内接手这些等待中的记录。
- 回滚即恢复旧行为，两个方向都不需要迁移任何状态。

## 运维指引 {#operators}

在修复发布之前：

- **运行时修改后，重启其他服务器。** 执行任何涉及 `audit_webhook`、`logger_webhook` 或配置了 `queue_dir` 的 `audit_kafka` 的 `mc admin config set` 或 `mc admin config reset` 之后，重启除处理该命令的服务器以外的每一台服务器。配置了日志 Webhook 时，`subnet` 代理修改也算在内。如果负载均衡器让你无法确定是哪台服务器处理了命令，可以在修改配置时把 `mcli` 别名指向某一台服务器自己的地址，或者逐台重启所有服务器。
- **未修改的目标不受影响。** 启动时就已存在的目标，无论来自环境变量还是已保存的配置，都用进程上下文构建，在下一次运行时修改之前不受影响。
- **已丢失的记录无法找回。** 以 `log buffer full` 丢弃的记录无法恢复。仍在内存队列中的记录会在服务器重启时丢失。配置了 `queue_dir` 时，修改之前已在磁盘上的记录会在重启后、端点可达时重放。

检测这种状态时，要在每台服务器上分别读取节点指标：

- 该目标的 `minio_audit_target_queue_length`（`target_id` 形如 `audit_http_0`，日志 Webhook 为 `sys_http_0`）在部分服务器上逐渐升向 `queue_size`，而在处理请求的那台服务器上接近于零。
- `minio_audit_failed_messages` 持续上升，`minio_audit_total_messages` 减去 `minio_audit_failed_messages` 通常停在队列长度上不再变化。
- 服务器日志出现 ``Unable to send audit event(s) to the target `NAME`: log buffer full``。
- 对配置了 `queue_dir` 的 Kafka，上述指标保持不变；应改为观察目标队列目录下的文件数量，以及 `the maximum store limit reached` 消息。

在受影响的服务器上，新目标的 Webhook 在线指标通常也一直为 0。端点宕机时它同样为 0，所以只能用来佐证其他信号。

## 剩余限制 {#limits}

以下限制都早已存在，并非由重载上下文造成。它们今天已存在于处理请求的服务器和启动时构建的目标上；有了修复，peer 的表现相同。每一项都需要单独的修改。

- **已丢失的记录不会被找回。** 修复防止的是由重载上下文造成的丢失。它不会找回已丢弃的记录，也不修复下面其他交接与关闭环节的丢失。
- **已满的磁盘队列仍可能阻塞旧目标的关闭。** 配置了 `queue_dir`、使用默认的 `max_retry=0`，并且替换目标时磁盘队列已满，旧 worker 会不断重试磁盘写入，而不检查自己的上下文；只要写入一直失败，它的 `Cancel` 就不会结束。重试等待应当响应上下文，而且届时还必须把未完成的批次交出去。
- **worker 已取出但尚未送达的记录会在替换时丢失。** 未配置 `queue_dir` 时，worker 会把记录编码进当前批次。如果目标在这个批次发送之前被替换，例如端点宕机期间，这个批次既不会送达，也不会被交出去。
- **替换期间新旧磁盘队列互相重叠。** 两个目标打开同一个目录，各自维护索引。替代目标打开目录之后旧目标再写入的记录，对替代目标的重放不可见；如果旧目标的重放在发送它之前停止，这条记录会留在磁盘上，直到目录被再次打开（例如下次重启）；两个重放也可能把同一条记录发送两次。Kafka 目标在 `queue_dir` 下使用固定的目录名，因此 `queue_dir` 相同的两个 Kafka 目标会共用它。
- **worker 可能在紧随其后的 `Cancel` 之后才启动。** worker 只有在运行起来之后才登记到 wait group，所以紧接在 `Init` 之后的 `Cancel` 可能在 worker 出现之前就结束等待。worker 对通道字段的读取以及之后对 worker 启动时间的更新同样没有同步。在 main 上，race 检测器同样会报告这些问题。
- **共享交接缓冲区可能装不下。** 它的大小在创建替代目标时确定，依据是被替换目标的队列和缓冲区中已有的记录；更早被替换、尚未完成交接的目标的记录不计在内。多个失败目标在短时间内相继被替换时，审查中的一个探测在 200 条排队记录中送达了 116 条；去掉 `Cancel` 中的交接后一条也没有送达。
- **Kafka 的关闭没有释放所有客户端。** 未配置 `queue_dir` 时，`Init` 创建一个客户端，第一次发送又创建第二个，第一个从未关闭。配置了 `queue_dir` 时，重放中仍在进行的初始化可能在 `Cancel` 返回之后才发布客户端。
- **未配置 `queue_dir` 的 Kafka 目标仍可能在没有发送循环的情况下启动。** 如果初始化目标时 broker 不可达，`Init` 会在启动发送循环之前返回，目标会一直填充通道，直到 `log buffer full`。这与上下文无关，同样留给单独的 issue。

## 验证 {#verification}

在 main 69fcf50cd 的一次性工作树中实际执行：

- 应用修复后，`go test ./cmd -run '^TestDynamicWebhookOutlivesConfigContext$'` 的全部八种情况通过，在 race 检测器下同样通过。完整的 `./cmd` 测试、`./internal/logger/...` 和 `./internal/store/...` 通过，后两者在 race 检测器下同样通过。`go vet ./cmd` 没有报告。
- 只应用测试、撤销生产代码改动后，七种情况失败。内存队列和磁盘队列的情况报告重载返回后 Webhook 停止工作；配置 `queue_dir` 的 Kafka 从未发出生产请求；无法打开队列的情况要么在目标被替换时丢失记录，要么以空指针解引用崩溃，位置在 `startQueueProcessor` 中的 `PutMultiple` 调用，worker 由 `initDiskStore` 启动，具体是哪一种取决于 worker 是否在重载上下文结束前取到了记录。未配置 `queue_dir` 的 Kafka 在两棵代码树上都通过，作为对照。
- 消融实验，每次只去掉一部分、保留其余修复：去掉 Kafka 调用点，只有配置 `queue_dir` 的 Kafka 情况失败；去掉先打开存储再启动 worker 的顺序，两个无法打开队列的情况都在 `PutMultiple` 处崩溃；去掉 `Cancel` 中的交接，两个无法打开队列的情况在再次应用配置时丢失记录。
- 对抗性审查补充了探测。共享缓冲区中已有 32 条记录时，磁盘目标在 race 检测器下完成初始化且没有报告，而 main 在 `PutMultiple` 处 panic。对空闲目标执行 100 次重载后再禁用，goroutine 数量不变。Kafka 在 broker 不可达时，即使上下文只有 10 毫秒，`Init` 也耗时约 10 秒，说明重载上下文在那里没有约束任何东西。在 main 和修复后的代码上，探测复现了四项[剩余限制](#limits)：磁盘队列已满时关闭被阻塞、未发送批次丢失、磁盘队列互相重叠，以及 worker 启动竞争。Kafka 客户端关闭问题通过阅读代码和一次受控交错确认。

通过阅读代码确认、未实际执行：

- 配置 `queue_dir` 时 Kafka 指标的表现、子系统逐项排查，以及历史沿革。

合并前仍需完成：远程 CI 和一次三服务器验收。验收时应通过一台服务器修改 `audit_webhook`，向其他服务器发送 S3 流量，确认接收端收到它们的记录、所有服务器上的 `minio_audit_target_queue_length` 都接近于零；如果有可用的 broker，再对配置了 `queue_dir` 的 `audit_kafka` 重复一次。

**集成验证。** 这个修复已摘取到下个版本的同一个集成分支上，位于 #278 和 #281 之后，与锁域、删除全部版本、Heal 演练、#285 和 Console 的修复放在一起。所有摘取都没有冲突。在该 head 上，完整的 `go test ./cmd/... ./internal/...` 套件通过，CI 的竞态检测选集和覆盖全部新测试的竞态选集也都通过。针对组合的对抗性审查没有发现缺陷，锁域、清理路径以及清除与恢复之间的交互都用实际执行的探针检查过。

## 审查记录 {#review}

| 轮次 | 结果 |
| --- | --- |
| 对抗性审查第 1 轮 | 带小问题通过；没有发现改动引入的生产缺陷。审查报告了六个早已存在的缺陷。修复了其中一个：从未启动的目标中排队的记录，会在重载替换该目标时被丢弃（第 3 部分；测试也改为通过第二次应用配置来恢复）。其余五个列在[剩余限制](#limits)中。测试子进程现在去掉了日志与审计环境变量。本文按审查意见做了更正：重启不是唯一的恢复方式；丢弃在日志和指标中可见；peer 上的崩溃大多被掩盖但并非总是如此；关于关闭和送达的说法加了限定。 |
| 对抗性审查第 2 轮 | 带小问题通过，覆盖 `Cancel` 中的交接和改写后的测试。交接把单个被替换目标的每条记录恰好送达一次，在缓冲区并发调整大小时保住了记录，并经受住了重复和并发的 `Cancel` 调用；端点可用和宕机两种情况下的普通重载没有出现新的丢失或重复。记录了一处剩余丢失：失败目标在短时间内相继被替换时，共享缓冲区可能耗尽（见剩余限制）。测试现在只清理最后一个目标。另外做了进一步的措辞更正。 |
| 对抗性审查第 3 轮 | 带小问题通过。确认了测试清理和更正后的措辞，另有两处表述改得更准确。 |

## 参考 {#references}

- Issue：[#259](https://github.com/pgsty/silo/issues/259)
- 相关的通知 Webhook 热重载：[PR #249](https://github.com/pgsty/silo/pull/249)
- 上游历史：[minio/minio#19004](https://github.com/minio/minio/pull/19004)、[minio/minio#19275](https://github.com/minio/minio/pull/19275)、[minio/minio#19854](https://github.com/minio/minio/pull/19854)
- 相关的上下文设计：[IAM 策略重载：锁粒度、请求取消与超时预算隔离](/zh/blog/design/iam-policy-cancellation/)
- 配置：[将服务日志或审计日志发布到外部服务](/zh/operations/monitoring/minio-logging/)
