---
title: "访问频率分层移除"
linkTitle: "访问频率分层移除"
description: "可选的 GET 频率池分层特性为何被移除、包含该特性的构建如何迁移，以及升级验收证明了什么、没有证明什么。"
url: "/zh/compatibility/access-tiering-removal/"
weight: 7
type: docs
icon: fa-solid fa-code-compare
---

> **发布边界：** 可选的 GET 频率池分层特性（社区 [PR #60](https://github.com/pgsty/silo/pull/60)）只存在于 main/快照构建中。Server 20260903 早于该特性，Server 20260916 则在移除之后打标签，因此从任一已发布版本升级都**无需**访问分层配置清理。移除经 [PR #188](https://github.com/pgsty/silo/pull/188) 合入；只有运行过包含该特性的构建的部署需要本页。

## 为何移除 {#why}

访问分层是一个默认关闭、按 GET 频率在本地服务器池之间搬移对象的可选调度器。按实际交付的形态，它给配置、生命周期解析、用量缓存、统计和核心多池写入路径带来了不成比例的维护面——换来的收益从未被测量、也从未被宣称（不存在任何吞吐、延迟或锁往返数字）。移除决定保留了所有独立正确的部分：

- 普通生命周期过期与到远端层的 transition；
- rebalance 与 decommission；
- PR #178 的通用多池写入、元数据、heal 与条件删除修复，包括共享远端层引用保护。

保留/移除的切分经过隔离对照验证：整批回退 PR #178 时代的修复会在 13 组检查中失败 10 组，因此这些被刻意保留，而分层特性本身移除。

## 升级包含访问分层的构建之前 {#before-upgrading}

1. 保存服务器 ILM 配置与每个受影响桶的 lifecycle XML 副本。使用保留非标 XML 的 API 客户端；不要依赖会静默丢弃未知元素的客户端模型。
2. 在旧服务器上设置 `ilm access_tiering=off`，移除或禁用所有访问分层环境覆盖。等在途搬移完成后再替换节点。这能减少搬移中间态；移除本身不改变任何存储 RPC 协议。
3. 删除顶层 `AccessTierQuota` 与规则级 `AccessTransition` 元素。**只含 `AccessTransition` 动作的规则整条删除。** 混合规则保留其 filter、status、ID 与普通过期/transition 动作。纯访问规则在升级后可以无害加载，但会变成无动作规则，在下一次 lifecycle 编辑时校验失败。若无规则剩余，通过 S3 API 删除 lifecycle 配置。
4. 使用**协调维护窗口**：停掉整个部署，在每个节点安装相同的新二进制，再全部重启。bootstrap 检查会比对二进制校验和**与**服务器环境设置——四节点实验中，第一个新节点在三个旧节点之间无法完成启动；只在部分节点上移除旧环境覆盖也会在二进制一致时阻止启动。不要以为 RPC 协议未变就可以逐台替换节点。该检查只在启动时运行，对已经在跑不同二进制的节点不构成安全保证。
5. 重启后验证对象读取、桶列表、ILM worker 设置与一次 lifecycle 编辑。检查**每个服务请求节点到每池每块盘**的存储访问：成功的读取或桶列表证明不了完整的盘可达性，admin 磁盘摘要只是服务器本地状态的聚合。启动时连接耗时有波动，固定 sleep 不可靠。

## 存储状态的去向 {#stored-state}

| 状态 | 移除后的行为 |
| --- | --- |
| 十个旧 ILM 键 | `access_tiering`、`access_pools`、`access_max_size`、`access_promote_watermark`、`access_bin_width`、`access_bins`、`access_flush`、`access_min_residency`、`access_workers`、`access_max_tracked` 被接受但忽略。既有的 transition/expiration worker 设置保留。 |
| Admin 配置 | 已弃用键仍可能出现在 `mcli admin config get ilm`；设置它们可能成功但无任何效果，即使 `access_tiering=on`。请从部署清单中移除过时环境设置。 |
| Lifecycle XML | `AccessTierQuota` 与 `AccessTransition` 读取时忽略、重新编码时省略。同一解析器处理新的 PUT 请求，因此这些扩展在那里也被静默丢弃；纯访问规则仍会动作校验失败。 |
| 数据用量缓存 | v8 与 v9 缓存都可读取，保留普通计数、大小、直方图与远端层统计。退役的热层字节计数丢弃；后续写入使用 v8。无需因特性做全量统计重建。 |
| 已搬移的对象 | 留在当前池中，版本与时间戳不变。没有批量搬回，也没有对象元数据改写。 |
| 内部残留 | `x-minio-internal-ilm-atier` 与 `.minio.sys/config/ilm/access/` 计数对象可能残留。它们不需要清理服务或对象扫描。 |

被中断的 rebalance/decommission 本就可能让同一版本存在于多个池，与访问分层无关；移除调度器不会移除这些既有副本。

## 升级验收证明了什么、没有证明什么 {#acceptance}

协调升级流程在**本地四节点双池实验**（单台 Docker Linux 主机、tmpfs 盘）中验证：就绪检查修正后，三次完整升级验收通过，绑定生产代码 `41aa84609`。就绪检查方法可复用：从每个服务请求节点，对各自唯一、从未写入的对象键执行 `GetObjectTagging`——该路径会等待所有盘——并与真实 `storage.ReadVersion` trace 逐条匹配，要求每条节点到盘路径真实返回预期的对象/版本不存在，连续三轮；本例四节点、八盘每轮需要 32 条应答。`drive not found`、超时或缺失 trace 都判失败：不可达的盘不等于健康盘报告对象不存在。单纯的逐节点 404 或 admin 磁盘摘要不能证明这一点。

同系列中更早的两次升级尝试**失败**过（一次 DELETE 返回 204 后某节点对 HEAD/GET 回 503）；这两个实例保持**未归因、未关闭**——它们没有被后续的成功解释掉，也没有被改判为通过。分布式生产升级（跨主机、正式 tag、软件包、镜像）**未**被这些实验证明。请把验收理解为：流程在受测拓扑中得到验证，而不是任何分布式 rollout 都有保证。

## 版本删除范围 {#version-deletion-scope}

此次移除与一项普通单对象 `DELETE ?versionId=...` 的修复同车：它现在跨池调和被寻址的 UUID、null 版本或删除标记（包括对目录标记 key 的未限定 DELETE）。成功的请求按既有逐池 quorum 规则把删除应用到每个已解析的池副本；待处理的出站删除复制保留 `VersionPurgePending` 直到复制 worker 完成 purge——成功不保证立即从每块盘物理移除。若某池不可读，即使另一池有可读副本，这些请求也可能返回 `503 SlowDownRead`（或保留其他错误码）；恢复后重试。批量 `DeleteObjects` 本就跨池扇出。入站复制删除、lifecycle 过期、free-version 清理与搬移内部调用保持既有契约——普通 DELETE 的修复不保证每一种删除来源。

## 历史记录 {#record}

特性的引入、后续修复、回退范围、评审历史与未解决的验证发现在钉定提交
[`40220bd836cb`](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/access-tiering-revert.md)
的归档决策记录与仓库内
[`docs/bucket/lifecycle/access-tiering-removal.md`](https://github.com/pgsty/silo/blob/main/docs/bucket/lifecycle/access-tiering-removal.md)
中保留；本页承载运维契约，二者都不是必需读物。组件状态见[版本矩阵](/zh/compatibility/versions/)。
