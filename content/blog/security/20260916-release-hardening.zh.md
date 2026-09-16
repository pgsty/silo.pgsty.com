---
title: "九月安全修复：载荷完整性、IAM 撤销与 Console 分享"
linkTitle: "九月安全修复"
date: 2026-09-16
author: "冯若航"
description: "SN-2026-012 至 SN-2026-014，分别注明 Server 源码与 Console 发布边界。"
tags: [安全, SigV4, IAM, Console]
weight: 1
url: "/zh/blog/security/20260916-release-hardening/"
---

> **2026-09-17 发布更新：** 本文记录的九月源码修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；协调升级、可选功能启用条件和剩余限制仍按各节执行。下方带日期的源码状态与验证记录保留当时的范围。


本文记录截至 9 月 16 日的三项修复及交付边界。编号属于 SILO 本地安全台账，不是 CVE，也不代表已分配 CVSS 分数。
持续维护的索引见[安全公告台账](/zh/about/security-advisories/)。

| 发现 | 修复源码 | 9 月 16 日的发布状态 |
| --- | --- | --- |
| SN-2026-012：预签名载荷完整性 | Server `c4b5e1cb4`，PR #177 | 不在 Server `RELEASE.2026-09-03T13-18-01Z` 中，等待后续 Server 发布 |
| SN-2026-013：持久 IAM 撤销 | Server PR #191 / #192 | 不在 Server 20260903 中；要求协调升级 |
| SN-2026-014：匿名 Console 分享代理 | Console PR #56；Server PR #209 选择修复 | 独立 Console v2.4.1 已发布；内嵌副本仍需更新 Server 二进制 |

## 预签名载荷完整性 — SN-2026-012 {#sn-2026-012}

通用认证路径可以使用仅通过 `X-Amz-Content-Sha256` 请求头提供的载荷哈希验证预签名请求，却遗漏对实际正文的摘要校验。
持有相应签名写入 URL 的调用者可替换正文。提交中的回归用 `PutBucketPolicy` 演示了这一点；这不表示匿名调用者能任意修改桶策略。

[PR #177](https://github.com/pgsty/silo/pull/177) 中的
[`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4) 将正文校验绑定到实际签名哈希，不匹配时返回 `XAmzContentSHA256Mismatch`（400）。
明确签入的 `UNSIGNED-PAYLOAD` 保留原有含义。相邻修复使策略条件使用已认证的有效值，并删除 `X-Amz-Signature-Age` 暂存头。
它们补充了 [SN-2026-011](/zh/blog/design/signed-header-coverage/)，但不代表 streaming SigV4 的未签名头已获得完整覆盖。

升级前检查自定义签名客户端。query 中的哈希优先于作为后备的 header，修改未签名 header 不能改变策略求值或正文校验使用的值。

## 持久 IAM 撤销 — SN-2026-013 {#sn-2026-013}

延迟复制事件、父身份重建及删除历史丢失可能恢复管理员已经撤销的身份或授权。
[PR #191](https://github.com/pgsty/silo/pull/191) 与 [PR #192](https://github.com/pgsty/silo/pull/192)
保留来源修订、删除墓碑以及签入子凭据的父身份撤销边界，阻止较旧事件和子凭据悄悄跨越已保留的撤销边界。

这是持久状态变化。所有站点及共享 IAM 后端的节点需要协调升级，不支持新旧节点混用或滚动降级。
`mcli admin cluster iam export` 不包含删除历史，不能作为完整恢复备份。应保存并演练完整后端恢复点，调和已知的更早撤销。
墓碑没有 TTL，也不会自动压缩。

[设计记录](/zh/blog/design/iam-revocations/)说明排序、尚存的组成员限制与指标。
操作时遵循[升级恢复流程](/zh/operations/replication/iam-upgrade/)，包括密码策略前置步骤。
撤销可能已经提交，但后续清理失败使请求返回 HTTP 500；不能仅凭这个响应判断旧凭据仍有效。

## 匿名 Console 分享代理 — SN-2026-014 {#sn-2026-014}

Jiri Pejchal 报告：无需认证的分享下载代理接受了超出预期对象下载范围、但仍指向配置中 Server origin 的 URL。
这是同源代理边界问题，不构成任意主机 SSRF 或绕过 Server S3 授权的证据。

[Console #56](https://github.com/pgsty/silo-console/pull/56) 限定 scheme、host、port，要求合法 bucket/object 路径，
拒绝系统路径、路径穿越和改变操作的 query 选择器，禁止重定向，并传递调用方取消信号。
通过验证的对象 URL 保留原始签名字节。

独立部署应升级至 [Console v2.4.1](/zh/blog/release/console-2.4.1/)。
[Server #209](https://github.com/pgsty/silo/pull/209) 已在 main 选择修复源码，但安装独立 Console 不能修补编译进 Server 20260903 的 UI 与代理。
合适的 Server 制品发布前，应按部署情况限制存在问题的 Console 分享端点暴露范围。

## 相邻依赖加固 {#dependencies}

Server main 将 `amqp091-go` 升至 v1.14.0，处理 [GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp)。
上游首个修复版为 v1.13.0。恶意 AMQP 对端可触发过量内存分配；SILO 中需要配置 AMQP 通知目标才可达。
该 Server 变化同样等待 20260903 之后的发布。[pkg v3.14.1](/zh/blog/release/pkg-3.14.1/) 则独立发布了 JWX JSON 编码更新。
组件发布与 Server 采用该依赖是两件事。
