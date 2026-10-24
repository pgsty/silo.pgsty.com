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

本文汇总随 [Server 20260916](/zh/blog/release/silo-20260916/) 与 [Console v2.4.1](/zh/blog/release/console-2.4.1/) 发布的三项安全修复（`SN-2026-012` 至 `SN-2026-014`）及底层依赖安全更新。完整台账索引见[安全公告台账](/zh/about/security-advisories/)。

| 编号与问题 | 修复源码 | 发布状态 |
| --- | --- | --- |
| `SN-2026-012`：预签名载荷完整性 | Server `c4b5e1cb4`，[PR #177](https://github.com/pgsty/silo/pull/177) | 已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布（`RELEASE.2026-09-03T13-18-01Z` 及更早版本受影响） |
| `SN-2026-013`：持久 IAM 撤销 | Server [PR #191](https://github.com/pgsty/silo/pull/191) / [PR #192](https://github.com/pgsty/silo/pull/192) | 已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；需跨节点与跨站点协调升级 |
| `SN-2026-014`：匿名 Console 分享代理 | [Console PR #56](https://github.com/pgsty/silo-console/pull/56)；[Server PR #209](https://github.com/pgsty/silo/pull/209) | 已在独立 [Console v2.4.1](/zh/blog/release/console-2.4.1/) 与内嵌该版本的 [Server 20260916](/zh/blog/release/silo-20260916/) 中发布 |

## 预签名载荷完整性 — SN-2026-012 {#sn-2026-012}

此前通用认证路径在验证预签名请求时，若调用方通过 `X-Amz-Content-Sha256` 提供载荷哈希，服务端在完成签名比对后可能遗漏对实际请求体字节的 SHA-256 摘要校验，导致持有合法预签名写入 URL 的调用方可以替换请求体内容（回归测试以预签名 `PutBucketPolicy` 复现了该缺陷）。

[PR #177](https://github.com/pgsty/silo/pull/177) 中的提交 [`c4b5e1cb4`](https://github.com/pgsty/silo/commit/c4b5e1cb4) 将请求体摘要校验严格绑定到实际参与签名的载荷哈希上；正文摘要不匹配时立即返回 `XAmzContentSHA256Mismatch`（`400 Bad Request`）。显式签入的 `UNSIGNED-PAYLOAD` 保持原有语义不变。同批修复还确保策略条件求值始终读取经过认证的签名字段（查询串中的签名值优先于后备请求头），并移除了内部暂存头 `X-Amz-Signature-Age`，与 [SN-2026-011](/zh/blog/design/signed-header-coverage/) 形成互补。

升级前请检查自定义签名客户端，确保带具体载荷哈希签名的预签名上传发送与之匹配的正文内容。

## 持久 IAM 撤销 — SN-2026-013 {#sn-2026-013}

在多站点复制或频繁变更场景下，延迟到达的旧复制事件、父身份同名重建或缺失的删除历史，此前可能导致管理员已经撤销的身份或策略重新恢复。[PR #191](https://github.com/pgsty/silo/pull/191) 与 [PR #192](https://github.com/pgsty/silo/pull/192) 引入了持久化的单调递增修订号、删除墓碑（tombstone）以及签入子凭据的父身份撤销代次，确保延迟到达的旧事件与撤销前签发的子凭据无法越过已持久化的撤销边界。

由于该修复涉及持久化 IAM 元数据状态：

- 共享同一 IAM 后端的所有节点以及参与复制的所有站点必须协调一致升级，不支持新旧版本混跑或滚动降级；
- `mcli admin cluster iam export` 仅导出当前活动记录而不包含删除墓碑，升级前请保留完整的底层备份并遵循 [IAM 升级与恢复流程](/zh/operations/replication/iam-upgrade/)；
- 修订排序规则、监控指标与组成员关系边界详见 [IAM 撤销设计记录](/zh/blog/design/iam-revocations/)。

## 匿名 Console 分享代理 — SN-2026-014 {#sn-2026-014}

Jiri Pejchal 报告：无需认证的 Console 分享下载代理接受了指向已配置 Server 源站、但超出预签名对象下载范围的同源 URL。

[Console #56](https://github.com/pgsty/silo-console/pull/56) 严格限定目标 URL 的协议、主机与端口必须匹配已配置的 S3 源站，要求路径必须为合法的 `/{bucket}/{object}`，拒绝系统保留前缀、路径穿越片段以及改变操作类型的查询参数，禁止跟随上游重定向，并透传客户端取消信号；合法的预签名对象下载 URL 则原样保留原始签名字节。

独立部署的 Console 请升级至 [Console v2.4.1](/zh/blog/release/console-2.4.1/)；使用内嵌 Console 的服务端部署（通过 [Server #209](https://github.com/pgsty/silo/pull/209) 集成）请升级至 [Server 20260916](/zh/blog/release/silo-20260916/)。

## 相邻依赖加固 {#dependencies}

[Server 20260916](/zh/blog/release/silo-20260916/) 将 `github.com/rabbitmq/amqp091-go` 升级至 `v1.14.0` 以修复 [GHSA-6c5v-hqjr-5xxp](https://github.com/advisories/GHSA-6c5v-hqjr-5xxp)（上游于 `v1.13.0` 修复：配置了 AMQP 桶事件通知目标时，恶意 AMQP 对端可触发过量内存分配），并同步升级至包含 JWX JSON 编码修复的 [pkg v3.14.1](/zh/blog/release/pkg-3.14.1/)。
