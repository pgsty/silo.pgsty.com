---
title: "请求头截止时间：绝对头部上限与滚动的正文空闲超时"
linkTitle: "请求头截止时间"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: >
  PR #196 的 HTTP 截止时间修复（055030ea5）设计记录：连接层包装器的滚动截止时间覆盖了绝对读头截止时间，且 --read-header-timeout 参数未传入服务器配置。本文说明两类超时的职责边界、配置矩阵、HTTP/1、HTTP/2 与 TLS 各阶段的行为，以及被否决方案为何会中断长上传。
tags: [设计, HTTP, S3, 评审]
weight: 10
draft: false
url: "/zh/blog/design/request-header-timeouts/"
---

本文记录 Server HTTP 读取截止时间的修复设计，该修复通过 [PR #196](https://github.com/pgsty/silo/pull/196) 合入主干（提交 [`055030ea5`](https://github.com/pgsty/silo/commit/055030ea5)），随 [Server 20260916](/zh/blog/release/silo-20260916/)（`40220bd836cbd066ca424fa4dc5dbb90057fb55a`）发布。

排查源于慢速 HTTP DoS 扫描器报告（[#183](https://github.com/pgsty/silo/issues/183)），并通过两组实验验证：一是直接 TCP 对照实验（请求头限制设为 100 ms、实际分批发送耗时 400 ms，标准 Go 服务拒绝该请求而旧版服务返回 204）；二是单盘进程探针验证（通过命令行参数与环境变量两种入口配置后，服务端均拒绝 400 ms 慢速请求头，正常请求不受影响）。

## 一条连接上的两类超时 {#classes}

- **请求头绝对截止时间。** `ReadHeaderTimeout` 限制从开始读取请求头到头部解析完成的*总时长*，慢速逐字节发送无法顺延该上限。在 HTTP/1 keep-alive 连接上，Go 先按 `IdleTimeout` 等待下一个请求的首字节，随后开启新的请求头截止时间。`ReadHeaderTimeout` 同时参与独立的 TLS 握手超时计算。
- **正文滚动空闲超时。** 请求头解析完成、连接进入活跃阶段后，切换回滚动超时：每次成功读取都会顺延截止时间，仅当两次读取之间的停顿超过配置的空闲超时（idle timeout）时才关闭连接；持续传输数据的长上传或长下载不会因头部截止时间中断。

修复前，第一类超时在实际运行中并未生效：连接层包装器在每次部分读取前都将 socket 截止时间重置为 `now + idle + 250 ms`，直接覆盖了 `net/http` 设置的绝对截止时间。慢速客户端只需在每个空闲窗口内发送一个字节，即可无限期占用连接。

## 两个独立缺陷 {#root-cause}

1. **连接层包装器覆盖了绝对截止时间。** `DeadlineConn` 包装器的读取路径在每次部分读取前重置 socket 截止时间，令 Go `net/http` 服务端设置的读头截止时间失效。直接 TCP 对照实验单独验证了这一点：将请求头上限设为 100 ms、空闲窗口设为 2 s 时，耗时 400 ms 才发完的请求头仍被接受。
2. **命令行配置未传入服务器上下文。** CLI 定义并解析了 `--read-header-timeout` 与 `MINIO_READ_HEADER_TIMEOUT`（含默认值），但服务器上下文构建器只复制了 `IdleTimeout` 而漏掉了 `ReadHeaderTimeout`，导致运行中的服务器拿到的值始终为 `0`。仅修复缺陷 1 时，真实服务进程依然接受慢速请求头；第二处修复是在 `IdleTimeout` 赋值旁补齐 `ReadHeaderTimeout` 传递。

该问题长期未被发现，是因为 `--read-header-timeout` 的默认值（30 s）与 `IdleTimeout` 默认值相同；当该参数未传入服务器时，`net/http` 回退使用的读超时恰好也是同一个 30 s，使默认配置下的表面行为与预期一致。

## 配置 {#config}

- **命令行参数：** `--read-header-timeout`（`Hidden: true`，不在常规 CLI 帮助中显示）
- **环境变量：** `MINIO_READ_HEADER_TIMEOUT`
- **默认值：** 30 s（与 idle timeout 默认值一致）
- 两项超时均**无 YAML 配置项**，仅在启动时按“命令行参数 > 环境变量 > 默认值”的优先级绑定一次。

| 取值 | 效果 |
| :-- | :-- |
| `header > 0` | 作为 HTTP/1 请求头阶段的绝对时长上限，并参与 Go 的 TLS 握手读取超时计算（含 HTTP/2 握手） |
| `header = 0`（显式设置） | 回退至 Go 标准库规则：使用读超时（即 idle timeout）；CLI 默认值为 30 s |
| `header < 0` | 关闭请求头专用上限；正值的读/写超时仍约束 TLS 握手读取，正值 `IdleTimeout` 仍约束 keep-alive 空闲等待 |
| 调小 `idle`、未设置 `header` | 请求头阶段仍使用自身的 30 s 默认值——这是唯一比直觉预期宽松的参数组合，但仍具备确定的绝对上限 |

将参数设为负值会关闭请求头绝对上限，使连接重新面临慢速请求头占用风险，不建议在生产环境使用。因超过截止时间而被截断的未完成请求头通常会直接触发连接关闭，而非返回 HTTP 错误状态码。该问题由 @AEGEGE 在 [#183](https://github.com/pgsty/silo/issues/183) 中报告，初始修复 [PR #195](https://github.com/pgsty/silo/pull/195) 经整理后随 [PR #196](https://github.com/pgsty/silo/pull/196) 合入。

## 各协议的超时行为 {#protocols}

- **HTTP/1**：请求头读取与 keep-alive 等待使用绝对截止时间，请求正文保持滚动空闲超时。连接状态钩子与调用方已有的钩子组合执行，互不覆盖。
- **TLS**：握手*读取*阶段取正值 header 截止时间与既有读/写超时的较小值，握手完成后重新计时新的请求头上限；握手*写入*阶段保持滚动超时语义。
- **HTTP/2**：保持不变。协商为 `h2` 时跳过连接阶段切换，沿用 `h2` 原生的单流（per-stream）绝对读超时，`ReadHeaderTimeout` 不注入 `h2` 配置。
- **内部节点通信**：Linux 节点间连接独立维护滚动超时语义；由 grid hijack 接管的连接在进入上述阶段切换前即解包还原为底层裸 TCP 连接。

## 被否决的方案 {#rejected}

- **全局钳制所有未来截止时间。** Go 1.27 在部分路径上会设置整请求截止时间；当读超时等于 idle timeout 时，全局钳制会把整个 HTTP/1 请求（请求头加正文）的总时长硬性限制在该窗口内，导致大文件上传中途断开。
- **移除读超时并将零值解释为滚动空闲超时。** 在 `net/http` 中，零值截止时间代表后台读取与 hijack 连接“永不超时”；改写这一语义会破坏长耗时 handler，同时使 `h2` 失去单流超时保护。
- **包装请求正文读取器或使用 `http.ResponseController`。** 需要完整处理 chunked 编码、连接排空（drain）、EOF 状态记账及 `h2` 特例，改动面远超修复请求头超时所需。
- **在连接状态钩子中重算标准库的截止时间。** 这会复制随 Go 版本演进而变化的 `net/http` 内部算术逻辑；直接记录并保留标准库下发的目标截止时间更加稳健。
- **通过比较参数大小自动推导超时模式。** 三个相关超时参数的默认值均为 30 s，在生产默认配置下无法通过“是否小于空闲窗口”区分所处阶段，该方式仅在人为调小参数的测试配置下有效。

## 验证与限制 {#verification}

单元测试覆盖了连接包装器跨越三个连续刷新周期的行为（验证绝对截止时间不随读取向后顺延）、HTTP/1 keep-alive / TLS / 纯 HTTP/2 协商下的阶段切换，以及真实 CLI 上下文中的命令行参数与环境变量绑定；进程探针验证了配置 100 ms 请求头上限的运行实例能够拒绝耗时 400 ms 的慢速请求头。边界说明：TLS 握手写入阶段仍采用滚动超时；业务 handler 的纯 CPU 或存储等待时间不受连接读取截止时间约束；请求头绝对上限不加额外宽限，而滚动空闲超时保留约 250 ms 的刷新宽限期。

升级注意事项（调小请求头超时会同步收窄 TLS 握手读取窗口）见[组件版本矩阵](/zh/compatibility/versions/#september-reliability)。

相关记录：[tags](/zh/blog/design/replicated-tag-ordering/) · [metadata](/zh/blog/design/replica-metadata-normalization/) · [HTTP](/zh/blog/design/request-header-timeouts/) · [audit](/zh/operations/replication/replica-metadata-audit/)
