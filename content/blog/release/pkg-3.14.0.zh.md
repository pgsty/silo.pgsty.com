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

[v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) 于 2026-09-13 发布，源码提交为 [`827f8109`](https://github.com/pgsty/silo-pkg/commit/827f8109ff11bf6239a35d8d6d137cb5738539c3)，模块导入路径为 `github.com/pgsty/silo-pkg/v3`。

## 密码策略迁移 {#migration}

**本版调整了密码修改的授权语义：**

- 公共方法 `Policy.IsAllowedActions` 默认放行 `admin:ChangeMyPassword`（除非策略显式 `Deny`），而创建或管理他人的 `admin:CreateUser` 仍必须显式 `Allow`。在配套升级后的 Server 与 Console 中，仅拒绝 `admin:CreateUser` 不再禁止调用者修改自己的密码；若需禁止自助改密，须显式拒绝 `admin:ChangeMyPassword`。
- 内置 `readonly` 策略移除了原先的 `admin:CreateUser` `Deny` 规则（若同一主体还绑定了另一份授予 `admin:CreateUser` `Allow` 的策略，该授权将正常生效）。新增的 `consolereadonly` 策略包含存储桶列举能力，并采用相同的权限拆分；两份内置策略本身均不授予任何用户管理权限。
- 集群中已保存的自定义策略与用户级权限覆盖不会自动改写。

如果希望维持旧版“同时禁止创建用户和自助改密”的限制，请在升级前将 `admin:CreateUser` 与 `admin:ChangeMyPassword` 写入**同一条 `Deny` 语句**（保持原有的资源范围与条件），并在整个回滚窗口期内保留该配置——旧版 Server 不会在改密端点上单独识别 `admin:ChangeMyPassword` 的拒绝规则。详见[密码权限迁移指南](/zh/compatibility/password-permissions/)。

**后续配套版本（9 月 16 日）：** [Console v2.4.1](/zh/blog/release/console-2.4.1/) 已发布配套密码管理界面，并搭配 `silo-pkg v3.14.1` 与 `mcli 20260916`。全栈协调升级要求见[组件版本矩阵](/zh/compatibility/versions/)。

## 依赖与验证 {#dependencies}

- **上游 `minio-go` 升级：** 锁定至 `v7.3.1-0.20260910142817-60bd07042d49`，纳入可配置上传大小上限、流式请求 `Content-Type` 签名、RDMA 调用方 TLS 信任传递、列举操作校验和一致性以及归档恢复状态解析修复。
- **工具链与依赖刷新：** 更新 `golang.org/x/*` 依赖，维持 Go 1.26 最低版本要求与 Go 1.27.1 构建工具链，所有导出 Go 函数签名保持不变；维持 `go-systemd v22.6.0` replacement 以确保 NetBSD 交叉编译兼容。
- **测试与安全扫描：** 通过 Go 1.26.8 与 1.27.1 全量 `-race` 测试、lint 及 LDAP 配置校验，并确认可通过 Go module proxy 与校验和数据库正常拉取。`govulncheck 1.8.0` 扫描确认无已导入的可达漏洞包（仅未导入受影响子包的 OpenPGP 模块保留 `GO-2026-5932` 记录）。

本版继续包含 [v3.13.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.3) 的策略 `Deny`/`NotResource` 序列化修复与有界通配符匹配算法（此前因旧版 bug 丢失语句的策略仍需从原始备份恢复）。自 [v3.13.0](/zh/blog/release/pkg-3.13.0/) 引入的 `github.com/pgsty/silo-pkg/v3` 模块路径迁移已在四个维护组件中全部完成。

[相对 v3.13.3 的源码对比](https://github.com/pgsty/silo-pkg/compare/v3.13.3...v3.14.0) · [上游改动采纳记录](https://github.com/pgsty/silo-pkg/blob/v3.14.0/UPSTREAM.md)
