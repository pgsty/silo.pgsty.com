---
title: "请求头截止时间：绝对头部上限与滚动的正文空闲超时"
linkTitle: "请求头截止时间"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: >
  PR #196 的 HTTP 截止时间修复（055030ea5）决策记录：连接层的滚动截止时间覆盖了一切绝对的读头截止时间，而 --read-header-timeout 旗标从未接入服务器。涵盖两类超时的区别、配置矩阵、HTTP/1、HTTP/2 与 TLS 各自得到什么，以及被否决方案为何会杀死长上传。
tags: [设计, HTTP, S3, 评审]
weight: 10
draft: false
url: "/zh/blog/design/request-header-timeouts/"
---

本文记录 Server HTTP 读取截止时间的修复，作为
[PR #196](https://github.com/pgsty/silo/pull/196) 的一部分合入 main（修复
[`055030ea5`](https://github.com/pgsty/silo/commit/055030ea5)）。

> **截至 2026-09-16：** 修复在核验过的 main
> [`40220bd836cb`](https://github.com/pgsty/silo/commit/40220bd836cbd066ca424fa4dc5dbb90057fb55a)
> 上；**不在**已发布的 Server 20260903 中。<br>
> **证据类别：** 合成实验——直接 TCP 对照（头部限 100 ms、头部用 400 ms 完成，标准 Go 拒绝而旧 SILO 返回 204），以及真实单盘进程探针（flag 与环境变量两种入口都拒绝 400 ms 慢头，且健康请求继续服务）。没有生产事故被归因；促成调查的 issue 是一份慢速 HTTP DoS 扫描器报告，未在已部署集群上复现。

## 一条连接上的两类超时 {#classes}

- **请求头绝对截止时间。** `ReadHeaderTimeout` 约束从开始读头到读头完成的*总时间*，滴入字节不能延长它。在 HTTP/1 keep-alive 连接上，Go 先用 `IdleTimeout` 等待下一请求的起始字节，再开始新的头部截止时间。`ReadHeaderTimeout` 还参与单独的 TLS 握手超时计算。
- **正文滚动空闲超时。** 头部解析完成、连接进入活跃阶段后，回到既有滚动语义：读取会续期，由配置的 idle timeout 限制字节之间的停滞。本次 HTTP/1 修复不限制持续有进展的上传/下载总时长；其他协议、代理与应用超时仍可能生效。

修复之前，第一类超时实际上不存在：连接层包装器在每次部分读取前把 socket 截止时间重置为 `now + idle + 250 ms`，覆盖 `net/http` 设置的任何绝对截止时间——慢速读取者只要每个空闲窗口发一个字节，就能无限期占住连接。

## 两个独立缺陷 {#root-cause}

1. **连接层中和了绝对截止时间。** `DeadlineConn` 包装器的读路径在每次部分读取前重置 socket 截止时间，使 Go 服务器设置的读头截止时间失效。直接 TCP 基线单独证明了这一点：头部限 100 ms、空闲窗 2 s 时，400 ms 才完成的头部被接受。
2. **配置从未到达服务器。** CLI 接受 `--read-header-timeout` 与 `MINIO_READ_HEADER_TIMEOUT`，默认值也正常解析——但服务器上下文构建器复制了 `IdleTimeout`、完全丢掉 `ReadHeaderTimeout`，运行中的服务器看到的始终是零。只修缺陷 1 时真实进程仍接受慢头；第二处修复是紧邻 idle-timeout 绑定的一行。

长期不可见的原因：flag 默认值（30 s）与 idle timeout 默认值相等，而 flag 未接线时服务器回退到的恰好是同一个 30 s——所有可观测的默认行为都像配置过一样。

## 配置 {#config}

- **旗标：** `--read-header-timeout`（`Hidden: true`，普通 CLI help 不显示）
- **环境变量：** `MINIO_READ_HEADER_TIMEOUT`
- **默认值：** 30 s（与 idle timeout 默认值相等）
- 两个超时都**没有 YAML 配置字段**；值在启动时按 flag > 环境变量 > 默认 一次性绑定。

| 取值 | 效果 |
| :-- | :-- |
| header > 0 | HTTP/1 头部阶段的绝对上限；参与 Go 的 TLS 握手读取窗口（含 HTTP/2 握手） |
| header = 0（显式设置） | 回退 Go 规则：读超时（= idle timeout）生效；CLI 默认值是 30 s |
| header < 0 | 关闭头部专用上限；正值的读/写超时仍限制 TLS 握手读取，正值 `IdleTimeout` 仍限制 keep-alive 等待，并非取消所有连接超时 |
| 缩短 idle、未设 header | 头部阶段独立使用 30 s 默认值——唯一比朴素预期"更松"的组合，但仍严格紧于修复前的无限续期 |

负值关闭绝对读头上限，重新允许持续滴入请求头的慢速占用，不能当作推荐的兼容开关。被截断的未完成请求头通常导致连接关闭，不保证返回 HTTP 错误状态。来源为 @AEGEGE 的 [#183](https://github.com/pgsty/silo/issues/183) 扫描器报告，修复经 [PR #195](https://github.com/pgsty/silo/pull/195) 集成进 #196；这不把实验结果升级为该部署的复现。

## 各协议得到什么 {#protocols}

- **HTTP/1**：头部与 keep-alive 等待是绝对的；正文保持滚动空闲超时。连接状态钩子与调用方钩子组合而非替换。
- **TLS**：握手*读取*取正的 header 截止时间与既有读/写超时的最小值；握手完成后重新开始一个新的头部上限。**握手的写入侧仍是滚动的**——本修复不是完整的 TLS 握手资源限制。
- **HTTP/2**：不动。协商到 h2 时完全跳过相位切换；h2 保留自身原生的绝对 per-stream 读超时，`ReadHeaderTimeout` 根本不进入 h2 配置。
- **内部调用方**：Linux 内部节点拨号使用自己的滚动语义；grid hijack 的连接在任何相位切换之前就解包回裸 TCP 连接。

## 被否决的方案 {#rejected}

- **全局钳制所有未来截止时间。** Go 1.27 在部分路径设置整请求截止时间；在读超时等于 idle timeout 时，这会硬顶整个 HTTP/1 请求——头部加正文——杀死所有大上传。
- **去掉读超时、把零解释为滚动 idle。** 零是 `net/http` 对后台读取与 hijack 连接的"永不超时"语义；重新解释它会破坏长 handler，且 h2 会失去 per-stream 超时。
- **包装正文读取器 / response controller。** 完整的 chunked/drain/EOF 记账加 h2 特判，远超头部缺陷所需。（后续一个未合并的分支为同一 DoS 族探索了正文侧的 response controller；截至本记录，它不是 main 的一部分，也不在本修复的声明范围内。）
- **在钩子里复刻标准库的截止时间算术。** 复制会随 Go 版本漂移的 stdlib 内部逻辑；记住 stdlib 实际要求的值才是稳健做法。
- **按值比较自动推导严格度。** 三个默认值都是 30 s 时，"短于空闲窗口"在生产默认下不可区分；这种逻辑只在测试配置下有效。

## 验证与限制 {#verification}

测试固定了连接包装器跨三个连续更新周期（绝对上限不外推）、HTTP/1 keep-alive / TLS / 仅 HTTP/2 协商的相位切换，以及真实 CLI 上下文的 flag/env 绑定；进程探针让一个 100 ms 头部上限的活服务器拒绝了 400 ms 才完成的头部。已知限制：TLS 握手写入侧仍为滚动；handler 的 CPU/存储等待没有截止时间；绝对头部上限无松弛而滚动 idle 保留约 250 ms 的更新松弛；多节点、跨区域长传输验收是后续工作——集成记录明确不把脚本化的 S3 长传输计为本修复的通过项。

升级注意（更短的头部超时同时收窄 TLS 握手窗口；它不是上传/下载的总时长限制）见[组件版本矩阵](/zh/compatibility/versions/#september-reliability)。

相关记录：[tags](/zh/blog/design/replicated-tag-ordering/) · [metadata](/zh/blog/design/replica-metadata-normalization/) · [HTTP](/zh/blog/design/request-header-timeouts/) · [audit](/zh/operations/replication/replica-metadata-audit/)
