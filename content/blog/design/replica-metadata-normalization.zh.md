---
title: "副本元数据归一化：可信复制不得重新注入什么"
linkTitle: "副本元数据归一化"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: >
  PR #194（修复 4fcdf37ce）的决策记录：可信复制 COPY 经由宽松路径重新提取原始请求元数据，使仅传输用的 aws-chunked 编码与 GHSA 脱敏的用户元数据回流到已存储对象中。涵盖期望的编码映射、Snowball 行为变化、为何升级不会修复存量对象，以及存量元数据修复提案的状态。
tags: [设计, 复制, S3, 评审]
weight: 9
draft: false
url: "/zh/blog/design/replica-metadata-normalization/"
---

> **2026-09-17 发布更新：** 本文记录的九月源码修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；协调升级、可选功能启用条件和剩余限制仍按各节执行。下方带日期的源码状态与验证记录保留当时的范围。

本文记录可信复制接收端如何为副本恢复元数据的修复，合入 Server main 为
[PR #194](https://github.com/pgsty/silo/pull/194)（修复
[`4fcdf37ce`](https://github.com/pgsty/silo/commit/4fcdf37ce)，合并为
[`9f3037e941`](https://github.com/pgsty/silo/commit/9f3037e941a49ab4cd8a0eed7c0f01083fbe4bbe)）。

> **截至 2026-09-16：** 修复在核验过的 main
> [`40220bd836cb`](https://github.com/pgsty/silo/commit/40220bd836cbd066ca424fa4dc5dbb90057fb55a)
> 上；**不在**已发布的 Server 20260903 中。<br>
> **来源：** 生产逻辑采纳 Mikhail Khadarenka 的 PR #187；合并后的改动保留其作者身份，并把范围收敛到经评审验证的边界。<br>
> **证据类别：** 针对真实单盘与 16 盘纠删后端的 64 叶 HTTP 级基线（修复前 44 对照通过 / 20 缺陷失败），以及同一套测试对基线 helper 的反事实重放。没有客户事故被归因。

## 哪里错了 {#problem}

普通 PUT 路径会对元数据归一化：从 `Content-Encoding` 中剥掉仅传输用的
`aws-chunked` token，并删除[GHSA-76wf-9vgp-pj7w](https://github.com/google/security-research/security/advisories/GHSA-76wf-9vgp-pj7w) 缓解刻意移除的
`X-Amz-Meta-X-Amz-Unencrypted-Content-Length/-Md5` 用户元数据键。而可信复制
接收端恢复副本元数据时，却以"允许复制"的开关重新运行*同一个宽松提取器*——把
原始请求的全部受支持头与用户元数据重放一遍。具体表现为，可信副本写入时服务器可能存储、并在之后的 GET/HEAD 返回：

- `Content-Encoding: aws-chunked`（纯传输编码，按 AWS SigV4 streaming 规则绝不能存储），或未拆分的 `aws-chunked,gzip` 整串（应为 `gzip`）；
- 两个 GHSA 脱敏用户元数据键——对该缓解的部分回退，仅限可信副本写入；
- 无自身 PAX 头的 Snowball 条目：外层归档的 content-type、cache-control 与用户元数据。

对象字节本身不一定受损；是存储的元数据错了。该回归由
[`56fa63bfd`](https://github.com/pgsty/silo/commit/56fa63bfd)
（2026-04-15，复制头信任边界加固，CVE-2026-34204）引入——其信任保护本身是对的，予以保留。

## 修复 {#fix}

只改一个文件（`cmd/handler-utils.go`）。删除布尔双模式 helper：

- 普通提取器无条件跳过复制专用键；
- 新的副本提取器只遍历复制到内部的头映射，**只**恢复六个复制域字段：SSE-C
  密封密钥材料、密封算法、IV、加密 multipart 标记（空标记按键存在性生效）、实际对象大小，以及 SSE-C checksum 恒等映射；
- 绝不重新读取普通受支持头或用户元数据。

修复后期望的存储编码：

| 请求编码 | 存储的 `Content-Encoding` |
| :-- | :-- |
| `aws-chunked` | 无 |
| `aws-chunked,gzip` | `gzip` |
| `gzip` | `gzip` |

`aws-chunked, gzip`（注意空格）仍存储带前导空格的 ` gzip`，`gzip, aws-chunked` 仍存储整串。这些是**记录在案的现状**，由测试按现状断言——不是修复声明。

## 运维可见变化 {#behavior}

- 可信 Snowball 条目不再继承外层归档的普通元数据。没有 PAX 时，不再继承外层 content-type、cache-control、expires 与用户元数据；有 PAX 时，也不再继承条目自身未重新声明的字段。条目的 `minio.metadata.*` 仍生效，六个复制域字段仍作用于已授权条目，归档的 storage class 仍然继承。仓库内 batch 生产者调用 `PutObjectsSnowball`，SDK 会发送 auto-extract 标记，但外层请求不标记为可信副本，因此没有使用本次受影响的继承路径。
- GHSA 脱敏键不再在副本恢复时被写回——与每次普通 PUT 的行为一致。
- 认证、权限门控与复制信任语义不变；普通提取路径逐字节等价。
- 回滚代码会重新打开注入路径，但**不会**修复已存储的元数据。

## 升级不会修复存量对象 {#existing}

升级阻止新的污染；不扫描、不改写既有对象。两个后果值得注意：

- *权威来源*仍被污染时，与已归一化副本的比较可能检测到差异，从而在 heal/resync 中反复选择元数据复制。先修复权威来源，再让副本收敛。
- 普通 S3 自 COPY 不是通用的修复 API：它会创建新版本或移动时间戳，而不是原位改写单个版本的元数据。

[只读审计 runbook](/zh/operations/replication/replica-metadata-audit/)已提供可执行清单工具与分类规则，但不授权或执行修复。

[只读审计 runbook](/zh/operations/replication/replica-metadata-audit/)已提供可执行清单工具与分类规则，但不授权或执行修复。

### 存量元数据修复提案——状态 {#remediation}

一个*未来*操作的设计已经存在：构建清单（包含非当前版本，不能只查最新）；通过与可信来源版本或独立校验值比对来核验——绝不凭错误的响应头猜测，也绝不因为标签写着 gzip 就重新解压；先处理权威来源的精确版本，再收敛副本；保留不可变清单与元数据备份；小批量验证并演练过回滚。对没有受支持路径的对象，停下来不动它——直接编辑 `xl.meta` 不是受支持操作。

所选操作必须保护需要保留的版本身份与当前版本关系、Object Lock 保留期与 legal hold、标签、复制状态和加密上下文；写入前检查并发变更，受阻或无法核验的版本保持不动。先在本地克隆中证明具体操作与回滚可行，才能把提案变成可执行 runbook。

> **这是一个等待单独批准的设计提案，不是已执行的程序。** 作为其一部分，没有进行任何生产清单扫描、对象写入、版本调整或部署。把它当作未来 runbook 的形状，而不是已验证的 runbook。

## 已知限制 {#limits}

- POST 表单上传路径（`bucket-handlers.go`）直接调用低层提取器，从不归一化编码；该行为不变，作为已知后续项记录；此处不声称已经建立公开 issue。
- 本地验证在测试专用的容量适配（宿主盘满）下运行；R4–R8 集成记录中的合并树复跑覆盖了未改动树的情形。
- 不声明双站点调度、重启或网络故障验收。

## 验证 {#verification}

回归测试（`TestExtractReplicationMetadata*`、`TestAPIReplicaContentEncoding`、`TestAPISnowballReplicaContentEncoding`，外加含 race 的信任/SSE-C 回环）覆盖映射表、六个恢复字段与普通路径等价性；原修复记录中的反事实运行对基线 helper 得到 36 个预期失败（20 个 HTTP 与 16 个 helper 用例），44 个对照通过；这不是本次文档修改重新运行的结果。升级摘要见[组件版本矩阵](/zh/compatibility/versions/#september-reliability)；姊妹修复见[复制标签排序](/zh/blog/design/replicated-tag-ordering/)。

相关记录：[tags](/zh/blog/design/replicated-tag-ordering/) · [metadata](/zh/blog/design/replica-metadata-normalization/) · [HTTP](/zh/blog/design/request-header-timeouts/) · [audit](/zh/operations/replication/replica-metadata-audit/)
