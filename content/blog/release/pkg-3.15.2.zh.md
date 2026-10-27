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

**silo-pkg v3.15.2 已发布**，源码为 [`0416eb1f4505`](https://github.com/pgsty/silo-pkg/commit/0416eb1f450536ca2cc3592c2c2a06a3df88d4e0)。[SILO 20261026](/zh/blog/release/silo-20261026/) 直接采用 `github.com/pgsty/silo-pkg/v3`。本文覆盖相对 **v3.14.3** 的完整 3.15 系列变化。

## 3.15.0：工具链与共享依赖 {#dependencies}

最低 Go 版本由 **1.26 提升为 1.27.3**。更新 13 项模块：JWX 3.4.0；etcd API、client/pkg、client 3.7.3；gRPC 1.84.0；grpc-gateway 2.32.0；go-json 0.11.2；swag/conv 0.29.2；go-colorable 0.1.16；cpuid 2.4.1；fwd 1.2.1；以及固定在 `ce908d29299b` 的两个 Google API/RPC 生成模块。

应用需用 Go 1.27.3 重新构建才能获得证书验证修复，库本身不分发 Go 运行时。公开 API、策略格式、授权判定和 [v3.14.3 策略优化](/zh/blog/release/pkg-3.14.3/)保持不变。

## 3.15.1：上游 SDK 修复 {#sdk}

首次 SDK 更新从 v7.4.1 推进到上游 `ab93db7ba435`，纳入六项修复：

- 在发送不完整分片前拒绝过短的顺序、并行流式分片上传。
- `ReadAt` 到达 EOF 后保留顺序读取；负偏移在读取元数据前即被拒绝。
- 修复 `Object.Stat` 后读取和 seek 的边界。
- 批量删除回退中每个失败只报告一次。

## 3.15.2：移除复制配置 {#replication}

最终采用上游 **`v7.4.2-0.20261025165926-320af050c445`**。移除桶复制配置接受 **HTTP 200 与 HTTP 204**，包括向 `SetBucketReplication` 传入空配置；AccessDenied 等真实失败仍返回错误。上游尚未发布 v7.4.2 标签。[上游变化](https://github.com/minio/minio-go/compare/v7.4.1...320af050c445)。

## 兼容性与验证 {#compatibility}

需要维持既有输出与 NetBSD 行为的应用继续保留 go-humanize 1.0.1、go-runewidth 0.0.29 和 go-systemd/v22 22.6.0。Go 不继承依赖的 replace 指令，每个应用需自行声明必要替换。

v3.15.2 通过包含 LDAP 的完整 lint/race 测试、模块验证与三个 push 工作流：[Go](https://github.com/pgsty/silo-pkg/actions/runs/40318147518)、[LDAP](https://github.com/pgsty/silo-pkg/actions/runs/40318147326)、[VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/40318147298)。HTTP 夹具验证两个复制移除入口均接受 200/204、保留 403 错误。此前 3.15 依赖回归覆盖 JWT 边界、本地 etcd 认证/watch/lease 持久性和 CLI 格式。

SDK 补丁不宣称新的 CVE 修复；`GO-2026-5932` 仍是未导入的弃用 OpenPGP 代码中的模块级发现。见[统一安全清单](/zh/blog/release/silo-20261026/#runtime-fixes)。

```go
require github.com/pgsty/silo-pkg/v3 v3.15.2
```

这是**纯源码发布**，没有独立可执行程序、软件包或容器；Server、Console、mcli 需重新构建才能采用。正式依赖图是维护的 PGSTY 组合，对上游 MinIO/MC 尽最大努力兼容。[GitHub 发布](https://github.com/pgsty/silo-pkg/releases/tag/v3.15.2) · [完整变化](https://github.com/pgsty/silo-pkg/compare/v3.14.3...v3.15.2)。
