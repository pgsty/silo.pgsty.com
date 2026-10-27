---
title: "silo-pkg 3.15：Go 1.27.3 与 S3 SDK 修复"
linkTitle: "pkg 3.15.2"
date: 2026-10-26
lastmod: 2026-10-27
author: "SILO"
description: "silo-pkg 3.15.0—3.15.2 相对 3.14.3 的完整变化：依赖升级、分片与读取修复、移除复制配置兼容性。"
tags: [Release, Dependencies]
weight: 3
url: "/zh/blog/release/pkg-3.15.2/"
aliases:
  - /blog/release/pkg-3.15.0/
  - /blog/release/pkg-3.15.1/
---

**silo-pkg v3.15.2 现已正式发布**（源码提交 [`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0)），由 [SILO 20261026](/zh/blog/release/silo-20261026/) 组件栈以 `github.com/pgsty/silo-pkg/v3` 模块路径直接引入。本文完整汇总自 **v3.14.3** 以来的 3.15 系列更新（`v3.15.0`、`v3.15.1` 与 `v3.15.2`）。

## 3.15.0：Go 工具链与共享依赖升级 {#dependencies}

模块最低 Go 版本要求由 **1.26 提升至 1.27.3**，并同步更新了 13 个直接依赖模块：JWX `3.4.0`、etcd `api` / `client/pkg` / `client` `3.7.3`、gRPC `1.84.0`、grpc-gateway `2.32.0`、`go-json 0.11.2`、`swag/conv 0.29.2`、`go-colorable 0.1.16`、`cpuid 2.4.1`、`fwd 1.2.1`，以及固定在 `ce908d29299b` 的两个 Google API/RPC 生成模块。

下游应用需使用 Go 1.27.3 重新编译以纳入标准库证书校验修复。公开包 API、IAM 策略格式、授权判定逻辑以及 [v3.14.3 的策略匹配性能优化](/zh/blog/release/pkg-3.14.3/)均保持不变。

## 3.15.1：上游 S3 SDK 修复 {#sdk}

`v3.15.1` 将上游 `minio-go` 从 `v7.4.1` 推进至 `ab93db7ba435`，合入了以下修复：

- 在发送不完整分片前直接拒绝被截短的顺序或并行流式分片上传。
- 修复 `ReadAt` 到达 EOF 后的顺序读取状态，并在访问元数据前拒绝负偏移参数。
- 修复调用 `Object.Stat` 之后的读取与 `Seek` 边界计算。
- 对批量删除回退路径中的重复错误去重，确保每个失败项只上报一次。

## 3.15.2：移除桶复制配置兼容 {#replication}

`v3.15.2` 进一步选用上游 **`v7.4.2-0.20261025165926-320af050c445`**（伪版本，上游尚未打 `v7.4.2` 标签）。移除存储桶复制配置（含向 `SetBucketReplication` 传入空配置）现在同时接受服务端返回 **HTTP 200 与 HTTP 204**，而 `AccessDenied` 等真实鉴权或请求失败仍正常返回错误（见[上游提交对比](https://github.com/minio/minio-go/compare/v7.4.1...320af050c445)）。

## 兼容性与验证 {#compatibility}

为保持既有 CLI 输出格式与 NetBSD 编译兼容，下游应用继续固定 `go-humanize v1.0.1`、`go-runewidth v0.0.29` 与 `go-systemd/v22 v22.6.0`。由于 Go 不会传递继承依赖模块的 `replace` 指令，各嵌入方需在自身 `go.mod` 中显式声明所需的模块替换。

`v3.15.2` 已通过含 LDAP 集成在内的全量 lint 与 `-race` 竞态测试、模块校验及三项 CI 流水线（[Go](https://github.com/pgsty/silo-pkg/actions/runs/40318147518)、[LDAP](https://github.com/pgsty/silo-pkg/actions/runs/40318147326)、[VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/40318147298)）。HTTP 协议夹具验证了两个复制移除入口均同时接受 `200`/`204` 并保留 `403` 错误；此前的 3.15 依赖回归测试亦覆盖了 JWT 校验边界、本地 etcd 认证/Watch/租约持久化及 CLI 输出格式。模块级扫描中的 `GO-2026-5932` 位于未被导入的弃用 OpenPGP 包中，不影响运行代码（详见[统一安全审计清单](/zh/blog/release/silo-20261026/#runtime-fixes)）。

```go
require github.com/pgsty/silo-pkg/v3 v3.15.2
```

`silo-pkg` 仅作为 **Go 源码模块**发布，Server、Console 与 mcli 通过重新编译集成该版本。正式维护的依赖组合为 PGSTY 组件栈，对上游 MinIO/MC 保持尽力而为兼容。[GitHub Release](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2) · [完整源码对比](https://github.com/pgsty/silo-pkg/compare/v3.14.3...v3.15.2)。
