---
title: "只读 Checksum 审计与可靠的 CLI 输出契约"
linkTitle: "Checksum Verify"
date: 2026-08-29
lastmod: 2026-08-29
author: "冯若航"
summary: >
  MCLI 可以在不修改数据的前提下，将 S3 已存 checksum 与对象逻辑字节重新比对。本文定义候选选择、结果分类、report、退出码，以及管道和 CI 所依赖的 non-TTY 输出契约。
tags: [设计, S3, 兼容性, Checksum, mcli]
weight: 28
draft: true
url: "/zh/blog/design/checksum-verify/"
---

本文是 MCLI 只读 checksum 校验流程，以及发布审查中发现的 non-TTY 输出缺陷
[pgsty/mc#5](https://github.com/pgsty/mc/issues/5) 的设计与实现记录。

> **状态：** 实现、本地提交、真实 S3 探针、subprocess 测试、完整 unit/race、
> lint、vet、品牌、CREDITS、跨平台构建及本地干净溯源已经完成。push、PR、
> 托管 CI、发布、Server 镜像集成与公共文档部署仍是相互独立的后续门禁。<br>
> **归属：** [`pgsty/mc`](https://github.com/pgsty/mc)。<br>
> **跟踪：** [pgsty/mc#5](https://github.com/pgsty/mc/issues/5)。<br>
> **安全边界：** 本命令只读校验，不负责修复。

## 太长不看（TL;DR） {#tldr}

历史 CopyObject 实现可能在转换后的存储字节上计算 additional checksum，而不是在
S3 返回给客户端的逻辑对象字节上计算。`mcli checksum verify` 会筛选对象，独立地
把逻辑对象流送入已记录的算法，并把每个候选分类为 `MATCH`、`MISMATCH`、
`NO_CHECKSUM`、`UNKNOWN_*` 或 `SKIPPED_*`。

首版实现在终端中工作正常，但 stdout 被重定向时完全不输出。MCLI 为了在非终端
环境中禁用进度 UI，会自动把执行状态标记为 quiet；新命令错误地把这项内部状态
理解成了“用户要求隐藏审计结果”。修复将语义输出与进度抑制分离，同时不改变
全局 quiet 行为，也不会在 CI 中重新打开进度条。

## 命令与范围 {#scope}

```console
mcli checksum verify ALIAS/BUCKET/OBJECT
mcli checksum verify --recursive ALIAS/BUCKET[/PREFIX]
mcli checksum verify --manifest candidates.jsonl ALIAS
```

V1 支持标记为 `FULL_OBJECT` 的 CRC32、CRC32C、CRC64NVME、SHA1 与 SHA256。
候选可以是单个对象、精确 VersionID、前缀下的当前对象、所有版本，或 JSON Lines
manifest 给出的精确条目。它还支持 SSE-C key 映射、时间与大小过滤、dry-run 成本
估计、有界 worker、下载限速、JSON 输出和可选的 JSON Lines report。

V1 不验证 `COMPOSITE` checksum，不从 ETag 推断类型，不读取 `xl.meta`，不能确定
历史 writer，也不会修复 metadata。

## Server checksum 兼容边界 {#server-boundary}

Amazon S3 当前定义了十种附加 checksum 算法。本次 SILO 实现 CRC32、
CRC32C、CRC64NVME、SHA1 与 SHA256；MD5、SHA512、XXHASH64、XXHASH3、
XXHASH128 尚未持久化或校验。

不支持的 `x-amz-checksum-*` 值或 trailer 现在会明确返回 HTTP 400
`InvalidArgument`，SILO 不再一边返回成功、一边静默丢弃调用方的完整性断言。
这也意味着：从其他厂商复制携带上述五种未支持算法的对象时，复制会显式失败，
必须改用已支持算法后重试。`x-amz-sdk-checksum-algorithm` 等 SDK 控制头本身
仍可使用，但必须配合已支持的 checksum 值或 trailer。

CRC64NVME 只支持整对象 checksum。CRC64NVME 与 `COMPOSITE` 的组合会被拒绝，
不再静默改写为 `FULL_OBJECT`。逗号分隔的 checksum trailer 会逐项解析；
同时声明多个 checksum trailer 仍属于非法请求。

本次选择“明确拒绝”，而不是直接增加五种持久化 checksum 类型标识。
旧节点无法在滚动升级期间安全解释新标识；完整支持这些算法需要单独设计
存储格式与混合版本兼容方案。

## 只读数据路径 {#data-path}

对每个候选对象，MCLI：

1. 使用 checksum mode 执行 `HEAD`，保留所有支持的 checksum 与 `ChecksumType`；
2. 对不支持或含糊的状态返回 `UNKNOWN_*`，绝不猜测；
3. 将 `GET` 返回的逻辑字节流送入有界 hasher，不把对象体写入磁盘；
4. 对固定版本使用 VersionID；对可变的未版本化/null 对象使用 `If-Match`，并在
   读取后再次 `HEAD`；
5. 将独立计算结果与已存值比较。

S3 边界只允许 LIST、HEAD 与 GET；如果 mock endpoint 收到写方法，测试必须失败。

## 结果与退出码契约 {#result-contract}

每个候选只产生一个稳定结果：

| 结果 | 含义 |
|:--|:--|
| `MATCH` | 所有支持的已存 checksum 都匹配逻辑对象字节 |
| `MISMATCH` | 至少一个已存 checksum 不同 |
| `NO_CHECKSUM` | 没有 additional checksum，因此不读取对象体 |
| `WOULD_VERIFY` | dry-run 找到可验证的 full-object checksum |
| `UNKNOWN_*` | MCLI 无法给出可靠判断 |
| `SKIPPED_*` | 过滤器主动排除了对象 |

`--fail-on` 支持 `mismatch`、`unknown`、`any` 与 `none`。默认 `any` 会在 mismatch
或校验不完整时返回 exit 1。dry-run 不应用 `--fail-on`。参数、认证、枚举与 report
写入失败属于命令失败，而不是对象分类。

其中，`SKIPPED_TOO_LARGE` 会让默认 `any` 返回 exit 1，因为大小上限使审计不完整；
时间过滤与 delete-marker skip 本身不会触发失败。

## 输出与自动化契约 {#output-contract}

对象记录和最终 summary 都是命令的语义输出：

- 除非调用方显式设置 `--quiet`、`-q` 或 `MC_QUIET=true`，TTY 与 non-TTY stdout
  都必须收到全部对象记录和最终 summary。
- non-TTY `--json` 每行输出一个紧凑 JSON 值；TTY JSON 保留 MCLI 既有的美化格式。
- 全局参数在 app、`checksum` 与 `verify` 三层位置都必须生效。
- `--report` 独立于 stdout；即使显式 quiet 让 stdout 静默，它仍会写入对象记录和
  最终 summary 的 JSON Lines。
- 输出通道不会改变 `--fail-on` 的判定。

这一区分之所以必要，是因为 MCLI 历史上的 `globalQuiet` 有两个来源：用户显式的
quiet 参数，以及拿不到终端尺寸时自动启用、用于关闭进度 UI 的 non-TTY 状态。
直接修改这个全局量，可能让 copy、get、put、mirror 等命令在 CI 中重新输出进度条。

最终修复只作用于 checksum 命令。它沿完整 CLI context 链查找显式 quiet/JSON
参数，因为 CLI 库的 `GlobalBool` 会停在最近的祖先 flag set；同时在 checksum action
内部恢复 JSON Lines，因为嵌套 `Before` hook 可能在 app-level `--json` 之后重置它。
其他命令的进度与输出行为均不改变。

## Report、秘密与运行成本 {#operations}

POSIX 系统上的 Report 文件以 `0600` 新建；Windows 使用账户的文件系统 ACL。
目标必须不存在；它只包含 metadata 与结果，不包含对象体
或 SSE-C key。Manifest 同样只保存 bucket、key 与可选 VersionID。

校验会下载每个受支持对象的完整逻辑内容。运维人员应使用 `--dry-run`、`--max-size`、
时间过滤、`--max-workers` 与全局下载限速控制成本和负载。`NO_CHECKSUM` 与
`UNKNOWN_*` 数量必须显式展示，二者都不能被包装成“校验成功”。

## Mismatch 能证明什么 {#meaning}

Mismatch 只能证明：校验时 endpoint 返回的 additional checksum，不能描述同一时刻
返回的逻辑对象字节。它不能单独证明对象一定由某个历史压缩缺陷生成，也不是与外部
真值的比较。

不要原地覆盖 checksum metadata。应先只读审计和分类。对已经确认且确有业务影响的
mismatch，优先写入新 key 或新 version，验证替代对象后再显式切换消费者；
`UNKNOWN_*` 对象不得进入自动修复。

## 验证记录与发布边界 {#verification}

本地验收矩阵覆盖 TTY human/JSON、non-TTY pipe、普通文件重定向、app/parent/leaf
三层 JSON 与 quiet、环境变量 quiet、quiet 下的 report、report 写失败，以及
MISMATCH/UNKNOWN 退出码。真实本地 S3 还覆盖了历史 `MATCH`、`MISMATCH` 与不支持
的 composite 对象。

本地 commit 不是正式发布。只有代码与本文决策记录合并、托管 `main` CI green 后，
才能关闭 [pgsty/mc#5](https://github.com/pgsty/mc/issues/5)。签名 tag、软件包、容器
镜像、Server 内置客户端、公共部署与生产审计仍是之后需要独立证明的门禁。
