---
title: "silo-pkg 3.14.1 发布"
linkTitle: "silo-pkg 3.14.1"
date: 2026-09-16T12:16:06+08:00
author: "冯若航"
description: "JWX JSON 编码加固与上游 CopyObject 响应修复。"
tags: [发布, pkg]
weight: 1
url: "/zh/blog/release/pkg-3.14.1/"
---

[v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1) 从
[`fa657ef4`](https://github.com/pgsty/silo-pkg/commit/fa657ef431ae22e720df37e5144cf00f67102945) 发布。
这是 `github.com/pgsty/silo-pkg/v3` 的依赖与工具更新；
[相对 v3.14.0 的差异](https://github.com/pgsty/silo-pkg/compare/v3.14.0...v3.14.1)没有修改包的 Go 源码或公开 API。

## 依赖变化 {#dependencies}

- JWX 从 v3.2.0 升至 v3.3.0。[上游发布说明](https://github.com/lestrrat-go/jwx/releases/tag/v3.3.0)
  将自定义 JSON 字段名编码时缺少转义的问题标识为 GHSA-4cf7-xm37-g63h。可利用性取决于是否接受攻击者控制的自定义 claim 名称；
  本包 `env` 的 JWT 路径使用已注册的 claim 名称，仅有依赖关系不能证明 mcli 存在可利用路径。
- 上游 minio-go 升至 `v7.3.1-0.20260915093545-32e1f32cb176`，包含
  [minio-go #2306](https://github.com/minio/minio-go/pull/2306)：识别 HTTP 200 响应正文中的 S3 `CopyObject` 错误，避免误报复制成功。
  修复适用于 SDK 的 CopyObject 路径，不代表所有应用都会选择该路径。
- Testify 升至 v1.12.1，lint 配置采用 `gomodguard_v2`。
  保留 Go 1.26 最低版本、Go 1.27.1 工具链及支持 NetBSD 的 go-systemd replacement。

## 组件与迁移边界 {#migration}

[v3.14.0 的密码策略变化](/zh/blog/release/pkg-3.14.0/#migration)继续生效，本补丁没有回退它。
原先意图同时禁止用户管理与修改自身密码的策略，应按[迁移指南](/zh/compatibility/password-permissions/)
保留 `admin:CreateUser` 与 `admin:ChangeMyPassword` 的配对 Deny。

[mcli 20260916](/zh/blog/release/mcli-20260916/) 和 [Console 2.4.1](/zh/blog/release/console-2.4.1/) 已选择此包。
9 月 16 日复核的 Server 源码基线仍选择 v3.14.0；发布一个模块不会更新已编译的 Server。
[组件版本表](/zh/compatibility/versions/)分别记录已发布组件及下一版 Server 选择的依赖。

发布验证记录见上述 release 和 [PR #9](https://github.com/pgsty/silo-pkg/pull/9)。这些是组件发布时的证据，
不代表本次文档修改重新运行了其中的测试。
