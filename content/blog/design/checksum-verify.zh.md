---
title: "只读 Checksum 审计与可靠的 CLI 输出契约"
linkTitle: "Checksum Verify"
date: 2026-08-29
lastmod: 2026-09-03
author: "冯若航"
summary: >
  MCLI 可以在不修改数据的前提下，将 S3 已存 checksum 与对象逻辑字节重新比对。随 mcli 20260903（PR #8、PR #13、#5）发布，本文定义候选选择、结果分类、报告、退出码，以及管道和 CI 所依赖的 non-TTY 输出契约。
tags: [设计, S3, 兼容性, Checksum, mcli]
weight: 28
draft: false
url: "/zh/blog/design/checksum-verify/"
---

本文记录 MCLI 只读 checksum 校验工作流，以及发布复核阶段发现的 non-TTY 输出缺陷 [pgsty/mc#5](https://github.com/pgsty/mc/issues/5) 的设计与实现。该命令经由 [`pgsty/mc`](https://github.com/pgsty/mc) 的 pull request [#8](https://github.com/pgsty/mc/pull/8) 与 [#13](https://github.com/pgsty/mc/pull/13) 合入主干，并随 [mcli 20260903](/zh/blog/release/mcli-20260903/) 正式发布（已内置于 [Server 20260903](/zh/blog/release/silo-20260903/) 容器镜像）。

## 核心概览 {#tldr}

历史版本的 `CopyObject` 实现可能在压缩或加密后的底层存储字节上计算附加校验和（additional checksum），而非在 S3 `GET` 返回给客户端的逻辑对象字节上计算。`mcli checksum verify` 会筛选候选对象，独立地将逻辑对象流送入已记录的校验和算法，并把每个候选分类为 `MATCH`、`MISMATCH`、`NO_CHECKSUM`、`WOULD_VERIFY`（dry run）、十种 `UNKNOWN_*` 分类之一，或三种 `SKIPPED_*` 结果之一。

首版实现在交互式终端中工作正常，但当 stdout 被重定向到文件或管道时却没有任何输出（[#5](https://github.com/pgsty/mc/issues/5)）。原因在于 MCLI 为在非终端环境中禁用进度条 UI，会自动将内部状态 `globalQuiet` 标记为启用；新命令误把这项内部状态当成了“用户要求隐藏审计结果”。[PR #13](https://github.com/pgsty/mc/pull/13) 将语义输出与进度条抑制解耦，在不改变全局 quiet 行为、也不在 CI 中重新打开进度条的前提下恢复了非终端输出。

## 命令与范围 {#scope}

```console
mcli checksum verify ALIAS/BUCKET/OBJECT
mcli checksum verify --recursive ALIAS/BUCKET[/PREFIX]
mcli checksum verify --manifest candidates.jsonl ALIAS
```

第一版支持标记为 `FULL_OBJECT` 的 `CRC32`、`CRC32C`、`CRC64NVME`、`SHA1` 与 `SHA256` 校验和。检查目标可以是单个对象、精确 `VersionID`、前缀下的当前对象、所有历史版本，或由 JSON Lines manifest 给出的精确条目。命令同时支持 SSE-C 密钥映射、时间与大小过滤、`--dry-run` 成本预估、有界并发 worker（`--max-workers`）、全局下载限速、`--json` 输出以及可选的 `--report` JSON Lines 报告。

该命令严格只读：不校验分段复合校验和（`COMPOSITE`），不从 `ETag` 推断校验和类型，不直接读取底层 `xl.meta`，也不修改任何对象元数据。服务端点必须随校验和一并返回类型头（`x-amz-checksum-type`）；对于不返回该头的端点，所有带校验和的对象都会被归类为 `UNKNOWN_CHECKSUM_TYPE`，绝不猜测类型。

当前不支持 `--rewind`、分层恢复、服务端批处理、断点续查或修复。

## 只读数据路径 {#data-path}

对每个候选对象，`mcli checksum verify` 执行以下五步：

1. 启用 checksum mode 发送 `HEAD` 请求，保留所有受支持的校验和摘要与 `ChecksumType`。
2. 对不支持或含糊的元数据状态直接归入 `UNKNOWN_*`，不做猜测。
3. 将 `GET` 返回的逻辑字节流送入有界内存哈希器，不把对象正文写入本地磁盘。
4. 对不可变历史版本使用 `VersionID` 固定目标；对可变的未版本化或 `null` 版本对象使用 `If-Match`，并在流式读取完成后再次 `HEAD` 核验以防并发替换。
5. 将独立计算的摘要与已存摘要逐一比较。

S3 传输边界仅允许 `LIST`、`HEAD` 与 `GET`；若 mock endpoint 收到任何写方法，自动化测试立即失败。

专用 S3 helper 通过 `StatObject` 保留所有校验和与类型，再用 `Core.GetObject` 读取逻辑字节，不启用 SDK 自动校验器。这样无需改变共享 `ClientContent`，也不会改变 `stat`、复制、镜像或 JSON 输出的既有契约。

## 结果与退出码契约 {#result-contract}

每个候选对象只产生一个稳定的分类结果：

| 结果 | 含义 |
| :-- | :-- |
| `MATCH` | 所有受支持的已存校验和均匹配 `GET` 返回的逻辑对象字节 |
| `MISMATCH` | 至少一个已存校验和与逻辑对象字节不一致 |
| `NO_CHECKSUM` | 对象没有附加校验和，不读取对象正文 |
| `WOULD_VERIFY` | `--dry-run` 发现可校验的 `FULL_OBJECT` 校验和 |
| `UNKNOWN_*` | MCLI 无法给出可靠校验结论（如 `COMPOSITE` 或缺失 `ChecksumType`） |
| `SKIPPED_*` | 过滤条件排除了该对象（`SKIPPED_TOO_LARGE`、时间过滤或删除标记） |

最终汇总（summary）携带 `objects`、`verified` 计数、每种结果状态的计数以及 `incomplete` 标志。`verified` 等于 `MATCH` 加 `MISMATCH`——只有这两种结果真正把对象正文流过了哈希器。枚举了大量对象却实际核验为零的运行，会在汇总中清晰体现。

`--fail-on` 支持 `mismatch`、`unknown`、`no-checksum`、`any` 与 `none`：

- 默认值 `any` 在出现 `MISMATCH`、`UNKNOWN_*` 或审计不完整时返回退出码 `1`。其中 `SKIPPED_TOO_LARGE` 会使 `any` 返回退出码 `1`（因为大小上限使审计不完整），而时间过滤与删除标记跳过不会触发失败。
- `no-checksum` 包含 `any` 的全部失败条件，并在任一对象缺少校验和或 `verified == 0` 时返回 `1`。
- `--dry-run` 不执行 `--fail-on` 失败判定。
- 命令行参数、认证、对象枚举与报告写入失败属于命令级错误，直接返回非零退出码。

## 输出与自动化契约 {#output-contract}

逐对象记录和最终 summary 都是命令的语义输出：

- 除非调用方显式指定 `--quiet`、`-q` 或 `MC_QUIET=true`，TTY 与 non-TTY 下的 stdout 都必须收到全部对象记录和最终 summary。
- non-TTY 下的 `--json` 每行输出一个紧凑 JSON 值（JSON Lines）；TTY 下的 `--json` 保留 MCLI 既有的缩进美化格式。
- 全局参数（`--json`、`--quiet`）在根命令 `mcli`、`checksum` 与 `verify` 三层位置均生效。
- `--report` 独立于 stdout：即使显式 `--quiet` 让 stdout 静默，`--report` 仍会完整写入对象记录和最终 summary 的 JSON Lines。
- 输出通道不会改变 `--fail-on` 的退出码判定。

这一区分非常关键：MCLI 历史上的 `globalQuiet` 混合了两个来源——用户显式传入的 quiet 参数，以及拿不到终端尺寸时自动启用、用于关闭进度条 UI 的 non-TTY 状态。如果直接修改全局 `globalQuiet`，会让 `cp`、`get`、`put`、`mirror` 等命令在 CI 日志中重新输出进度条。

因此 [PR #13](https://github.com/pgsty/mc/pull/13) 的修复仅作用于 `checksum` 命令内部：它沿完整 CLI context 链查找显式 quiet/JSON 参数（绕开 CLI 库 `GlobalBool` 只检查最近一层父级 flag set 的限制），并在 `verify` action 内部恢复被嵌套 `Before` 钩子重置的 JSON Lines 模式。

## 报告、密钥安全与运行成本 {#operations}

报告文件（`--report`）在 POSIX 系统上以 `0600` 权限新建，Windows 使用账户的文件系统 ACL。若目标路径已存在则报错退出；报告中只保存对象元数据与校验结果，绝不包含对象正文或 SSE-C 客户密钥。输入清单（`--manifest`）同样只记录 `bucket`、`key` 与可选 `versionId`。

由于校验过程会完整下载每个受支持对象的逻辑正文，运维人员应组合使用 `--dry-run`、`--max-size`、时间过滤、`--max-workers` 与全局下载限速控制网络与存储负载。`NO_CHECKSUM` 与 `UNKNOWN_*` 计数在汇总中独立展示，绝不与 `MATCH` 混同。

## Mismatch 能证明什么 {#meaning}

`MISMATCH` 证明：校验时刻 `HEAD` 返回的附加校验和，与同一时刻 `GET` 返回的逻辑对象字节不一致。单凭 `MISMATCH` 本身，不能直接断定对象一定由某个历史压缩复制缺陷生成，也不能替代与外部权威数据源的比对。

排查出 `MISMATCH` 时，不要原地覆写底层校验和元数据。应先通过只读审计完成分类；对确认受影响且有业务消费的对象，优先写入新对象键或新版本，用 `mcli checksum verify` 验证新对象返回 `MATCH` 后再切换下游消费方。`UNKNOWN_*` 对象不得纳入自动化修复脚本。

## 验证记录与输出 Schema {#verification}

验收矩阵覆盖 TTY 人类可读与 JSON 输出、non-TTY 管道、普通文件重定向、app/parent/leaf 三层 JSON 与 quiet 参数、环境变量 `MC_QUIET=true`、quiet 模式下的 `--report`、报告写入失败、`MISMATCH`/`UNKNOWN_*` 退出码，以及针对真实 SILO 服务端的 `MATCH`、`MISMATCH` 与 `COMPOSITE` 对象实测（详见 [`mc checksum verify` 命令参考](/zh/reference/minio-mc/mc-checksum-verify/#command-mc.checksum.verify)）。

JSON 消费方应校验 `schemaVersion: 1`，并通过 `type: object` 与 `type: summary` 区分逐对象记录和最终汇总。`--max-workers` 默认为 `4`（范围 `1`–`64`），用于限制并发对象校验协程数。

测试还覆盖多校验和任一不匹配、固定与 `null` 版本、正常完成时每个候选只输出一次，以及 worker 取消后正常关闭结果流。`InvalidObjectState` 优先归类为需要恢复的存储状态，不能误作通用 403；SSE-C 错误分类不依赖 URL 或对象名文本。
