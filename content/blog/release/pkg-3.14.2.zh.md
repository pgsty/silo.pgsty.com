---
title: "silo-pkg 3.14.2 发布"
linkTitle: "silo-pkg 3.14.2"
date: 2026-10-15T21:32:32+08:00
lastmod: 2026-10-18
author: "SILO"
description: "mcli 20261018 与 Console v2.4.2 使用的十月 SDK 和安全依赖基线。"
tags: [发布, pkg]
weight: 1
url: "/zh/blog/release/pkg-3.14.2/"
---

**发行版：** [v3.14.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.2) · **源码：** [`c6835145176f`](https://github.com/pgsty/silo-pkg/commit/c6835145176f385dd5f2d2a6d5ccd337b258d9bb)。

`github.com/pgsty/silo-pkg/v3 v3.14.2` 为 [mcli 20261018](/zh/blog/release/mcli-20261018/) 与 [Console v2.4.2](/zh/blog/release/console-2.4.2/) 提供十月依赖基线；后续补丁版 [v3.14.3](/zh/blog/release/pkg-3.14.3/) 在此基础上优化了策略判定性能，供 [Server 20261018](/zh/blog/release/silo-20261018/) 使用。

## 变更内容 {#changes}

- **上游 `minio-go` 升级至 v7.4.1**：在调用方取消上下文后仍确保清理失败的分片上传，以 UTC 序列化 Object Lock 保留期时间，原样透传请求的 STS 时长，并支持 Kubernetes 投射服务账号令牌文件（并行 GET 与 ComposeObject 仍需显式启用）。
- **`go-jose` 升级至 v4.1.6**：修复解析超大恶意 RSA JWK 时的 CPU 消耗问题（[GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)）；同步升级 **LDAP v3.4.15**、**msgp v1.6.5** 与 **etcd 客户端 v3.7.2**。
- **`golang.org/x/*` 升级**：`x/crypto` **v0.58.0**、`x/net` **v0.61.0**、`x/sys` **v0.49.0**、`x/text` **v0.43.0**。使用 **Go 1.27.2** 开发与测试，保持模块 `go 1.26` 最低版本要求及 NetBSD 的 `go-systemd v22.6.0` 替换。

## 兼容性与采用方式 {#adoption}

```go
require github.com/pgsty/silo-pkg/v3 v3.14.2
```

公开包签名与密码策略语义保持不变（从 v3.14.0 之前版本升级请参考[密码权限迁移说明](/zh/compatibility/password-permissions/)，各组件依赖对照见[组件矩阵](/zh/compatibility/versions/)）。

行为变更提示：
- `go-jose v4.1.6` 拒绝超过 **4096 位**的 RSA JWK，使用该解析器的 OIDC/JWKS 消费方需确认身份提供方密钥长度不超过 4096 位。
- 低于 1 小时的 STS 请求时长现在按原值发送，不再被客户端静默改写，因此超出服务端下限的过短时长会被服务端直接拒绝。

## 验证 {#validation}

该版本通过 Go 1.27.2 完整 lint 与 race 测试、Go 1.26.9 race 测试、OpenLDAP 集成测试、模块整洁性检查及 `govulncheck` 扫描（无可达或已导入包漏洞）。

标签源码 CI 记录：[Go](https://github.com/pgsty/silo-pkg/actions/runs/38743292347)、[LDAP](https://github.com/pgsty/silo-pkg/actions/runs/38743292597)、[VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/38743292281)。

[相对 v3.14.1 的变更](https://github.com/pgsty/silo-pkg/compare/v3.14.1...v3.14.2) · [PR #10](https://github.com/pgsty/silo-pkg/pull/10)。
