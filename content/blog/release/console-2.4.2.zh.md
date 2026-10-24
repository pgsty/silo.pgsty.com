---
title: "SILO Console 2.4.2 发布"
linkTitle: "Console 2.4.2"
date: 2026-10-17T20:49:49+08:00
author: "Vonng"
description: "引用 mcli 20261018 与 minio-go v7.4.1，更新构建工具并正确透传桶版本控制错误。"
tags: [Release, Console]
weight: 1
url: "/zh/blog/release/console-2.4.2/"
---

**版本：** [v2.4.2](https://github.com/pgsty/silo-console/releases/tag/v2.4.2) · **源码：** [`ef2dd2c41d21`](https://github.com/pgsty/silo-console/commit/ef2dd2c41d212ed6405c90fa8e5ab671899a7365)。

本版本作为独立 Console 发行版及 [Server 20261018](/zh/blog/release/silo-20261018/#components) 的内嵌 Console 组件发布（参见 [silo-pkg v3.14.2 发布说明](/zh/blog/release/pkg-3.14.2/)）。

## 更新内容 {#changes}

- 升级至 **mcli 20261018**、**silo-pkg v3.14.2** 与上游 **minio-go v7.4.1**。SDK 包含取消后的失败分段上传清理、UTC 保留期时间戳及 STS 时长透传（并行 GET 与 ComposeObject 仍需显式启用）。
- 保留桶版本控制操作中被包装的底层 S3 错误；当 Object Lock 阻止暂停版本控制时，明确向前端返回 `InvalidBucketState`。
- 使用 **Go 1.27.2** 与 **Node 24.22.0 LTS** 构建。更新 `golang.org/x/*` 模块及依赖版本：compress **v1.20.3**、msgp **v1.6.5**、etcd **v3.7.2**、fwd **v1.2.1** 与 cpuid **v2.4.1**（保留 go-systemd **v22.6.0** 以支持 NetBSD，保留 tablewriter **v0.0.5** 以兼容现有 MC API）。
- 构建工具固定为 **GoReleaser v2.18.3**、**golangci-lint v2.15.0** 与 **govulncheck v1.9.0**，重新生成 2.4.2 内嵌前端资产并更新固定摘要的构建容器。

## 集成说明 {#integration}

由于模块路径保留无 `/v2` 后缀的 `github.com/pgsty/silo-console`，Go 消费方通过伪版本 `v0.0.0-20261017112417-ef2dd2c41d21` 引用。嵌入 Console 的 Server 需同时显式声明 Console 与 MC 替换：

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261017112417-ef2dd2c41d21
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261017101407-fa3b8bf72458
```

Console v2.4.2 直接依赖 `github.com/pgsty/silo-pkg/v3 v3.14.2`（既有密码权限迁移规则见[密码权限迁移指南](/zh/compatibility/password-permissions/)）。注意 `go-jose v4.1.6` 的 4096 位 RSA JWK 限制仅影响链接了该包的 Server OIDC 路径，独立 Console 二进制未链接 `go-jose` 与 `go-ldap`。

## 发布与验证 {#delivery}

全部 **44 个发行制品**（6 个平台二进制、6 份归档、9 个 Linux 软件包及配套校验清单、SBOM 与签名来源证明）均已核验并与标签源码 `ef2dd2c41d21` 一致。该提交通过完整 CI 矩阵（权限、SSO、复制、浏览器测试、源码镜像一致性与可复现打包）、漏洞检查、本地 Go race 测试、251 项前端单元测试，以及搭配 [Server 20261018](/zh/blog/release/silo-20261018/) 的真实 API 与浏览器分享测试。

公开镜像 `docker.io/pgsty/silo-console:v2.4.2`（`linux/amd64` 与 `linux/arm64`）的多架构索引摘要为：

```text
sha256:4cf47061e0d2f249df3c1cd2a939966ff3c69cc3cf7d10a7b1b39d5c110ae999
```

[发布核验约定](https://github.com/pgsty/silo-console/blob/v2.4.2/docs/release-contract.md) · [组件版本矩阵](/zh/compatibility/versions/) · [相对 v2.4.1 的源码差异](https://github.com/pgsty/silo-console/compare/v2.4.1...v2.4.2)。
