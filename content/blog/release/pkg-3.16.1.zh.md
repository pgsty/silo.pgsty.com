---
title: "silo-pkg 3.16.1：严格策略 JSON 解码与 Go 1.27.4"
linkTitle: "pkg 3.16.1"
date: 2026-11-12T02:00:00+08:00
author: "SILO"
description: "silo-pkg 3.16.1 对 IAM 与桶策略启用严格 JSON 解码校验，并升级至 Go 1.27.4 依赖基线。"
tags: [Release, Security, Dependencies]
weight: 3
url: "/zh/blog/release/pkg-3.16.1/"
---

**silo-pkg v3.16.1** 是 `github.com/pgsty/silo-pkg/v3` 继 [v3.16.0](/zh/blog/release/pkg-3.16.0/) 之后的源码维护与安全加固版本，要求 **Go 1.27.4**，保持公开包 API 与合法策略语义兼容。独立发布的 [Console 2.7.1](/zh/blog/release/console-2.7.1/) 与 [mcli 20261112](/zh/blog/release/mcli-20261112/) 已采用 `v3.16.1` 构建；已发布的 [SILO Server 20261109](/zh/blog/release/silo-20261109/) 及更早应用制品在重新构建发布前仍保留原有依赖版本。

## 严格策略 JSON 解码 {#policy-decoding}

`policy.ParseConfigStrict` 与 `policy.ParseBucketPolicyConfig` 现统一拒绝以下畸形输入：

- 非 JSON 对象的顶层输入（如 `null`、数组、字符串、数值或布尔值）；
- 根对象之后的尾部多余 JSON token 或拼接文档；
- 顶层、Statement 或 Principal 中的未知字段（含未实现的 `NotPrincipal` 字段与空对象 `Principal: {}`）。

此前，策略结构体的自定义 `UnmarshalJSON` 方法可能绕过外层 `json.Decoder.DisallowUnknownFields()`，使拼写错误的字段（如 `Statements`、`Conditions`）静默变成空策略或丢弃条件子句。对于服务账号内联策略的显式重置路径，`ParseConfigStrictAllowEmpty` 继续识别合法的空策略文档（`{}` 或 `{"Statement":[]}`），而命名策略与账号创建路径使用的 `ParseConfigStrict` 继续拒绝空策略。

## 工具链与依赖更新 {#dependencies}

| 模块 / 工具链                               | v3.16.0   | v3.16.1   |
| ------------------------------------------- | --------- | --------- |
| Go 工具链                                   | `1.27.3`  | `1.27.4`  |
| `golang.org/x/sys`                          | `v0.49.0` | `v0.50.0` |
| `golang.org/x/term`                         | `v0.47.0` | `v0.48.0` |
| `golang.org/x/text`                         | `v0.43.0` | `v0.44.0` |
| `golang.org/x/oauth2`                       | `v0.37.0` | `v0.38.0` |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `v2.32.0` | `v2.33.0` |
| `google.golang.org/grpc`                    | `v1.84.0` | `v1.85.0` |
| `github.com/dustin/go-humanize`             | `v1.0.1`  | `v1.1.0`  |
{.wide .expand}

经核验的 `golang.org/x/crypto`（`2f1f834330b2`）、`github.com/minio/minio-go/v7`（`320af050c445`）、`go-runewidth v0.0.29` 与 `go-systemd/v22 v22.6.0`（NetBSD 可移植性固定版本）保持不变。Go 模块不会向下游传递依赖自身的 `replace` 指令，消费方仍须保留应用级替换规则。

```sh
go get github.com/pgsty/silo-pkg/v3@v3.16.1
go mod tidy
```

请使用 Go 1.27.4 重新构建并测试消费方应用。各组件版本边界见[组件版本矩阵](/zh/compatibility/versions/)。

## 验证 {#verification}

发布源码为 [`433f7eefa714`](https://github.com/pgsty/silo-pkg/commit/433f7eefa714a30b72ca70c4dffcd5faca25804f)。验证涵盖全量 lint 与 `-race` 测试（含严格 JSON、`NotPrincipal` 与空 Principal 回归测试）、实时 LDAP 集成校验、`go mod verify` 与 `govulncheck ./...`。流水线记录：[Go CI](https://github.com/pgsty/silo-pkg/actions/runs/43073526147)、[LDAP CI](https://github.com/pgsty/silo-pkg/actions/runs/43073526280) 与 [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/43073526772)。

[GitHub Release](https://github.com/pgsty/silo-pkg/releases/tag/v3.16.1) · [相对 v3.16.0 的变更](https://github.com/pgsty/silo-pkg/compare/v3.16.0...v3.16.1)
