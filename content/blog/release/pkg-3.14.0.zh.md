---
title: "silo-pkg 3.14.0 发布"
linkTitle: "silo-pkg 3.14.0 发布"
date: 2026-09-13T08:55:28+08:00
author: "Vonng"
description: "密码权限迁移、上游 SDK 修复与 9 月 13 日依赖刷新。"
tags: [Release, pkg]
weight: 1
url: "/zh/blog/release/pkg-3.14.0/"
---

[v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) 于 2026-09-13 发布，
源码为 [`827f8109`](https://github.com/pgsty/silo-pkg/commit/827f8109ff11bf6239a35d8d6d137cb5738539c3)。
消费者直接引用 `github.com/pgsty/silo-pkg/v3`。

## 密码策略迁移 {#migration}

**本版改变授权语义。** 公共方法 `Policy.IsAllowedActions` 默认报告 `admin:ChangeMyPassword`，除非被明确拒绝；
`admin:CreateUser` 必须显式授权。配套 Server/Console 中，单独拒绝 CreateUser 不再锁定调用者自己的密码，
拒绝 ChangeMyPassword 才会锁定。

内置 `readonly` 移除 CreateUser Deny，另一份策略的 CreateUser Allow 因此可能生效。
新增 `consolereadonly` 包含存储桶列举能力，并采用相同拆分；两种策略自身都不授予用户管理权限。
已保存策略和用户覆盖不会自动重写。

要保留旧版同时禁止两类操作的限制，应在升级前把两个动作保留在**同一个 Deny 语句**中，保留原资源范围与条件，
并持续到回滚窗口结束。旧 Server 不会执行此端点的密码专用 Deny。详见[完整迁移指南](/zh/compatibility/password-permissions/)。

截至 2026-09-13，pkg 与 mcli 已发布，配套 Server 和 Console 仍是**主分支源码**。
Server 20260903、Console v2.4.0 尚不包含拆分。见[组件版本矩阵](/zh/compatibility/versions/)。

## 依赖与验证 {#dependencies}

- 上游 minio-go 固定为 `v7.3.1-0.20260910142817-60bd07042d49`：包括可配置上传限制、流式 Content-Type 签名、RDMA 调用者 TLS 信任、列举校验和与可选恢复状态修复。
- 刷新 Go x/* 依赖，使用 govulncheck 1.8.0。库保留 Go 1.26 下限与 Go 1.27.1 工具链，公共 Go 签名不变。
- go-systemd v22.6.0 replacement 仍用于维持 NetBSD 编译兼容。
- Go 1.26.8 与 1.27.1 完整 race 套件、lint、LDAP 配置验证通过。扫描未发现可达或已导入的易受攻击包，但未使用的 OpenPGP 仍有模块级 GO-2026-5932 告警。发布版已通过 Go proxy 与校验和数据库解析验证。

此前 [v3.13.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.3) 的 Deny/NotResource 与有界通配匹配修复均保留。
已经丢失的策略语句仍需从原始策略恢复。[v3.13.0](/zh/blog/release/pkg-3.13.0/) 引入的模块路径迁移已在四个维护组件中完成。

[相对 v3.13.3 的源码变化](https://github.com/pgsty/silo-pkg/compare/v3.13.3...v3.14.0) ·
[上游改动采用记录](https://github.com/pgsty/silo-pkg/blob/v3.14.0/UPSTREAM.md)。
