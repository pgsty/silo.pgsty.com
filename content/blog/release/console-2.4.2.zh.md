---
title: "SILO Console 2.4.2 发布"
linkTitle: "Console 2.4.2"
date: 2026-10-17T20:49:49+08:00
author: "Vonng"
description: "引用 mcli 20261018 与 minio-go v7.4.1，更新构建工具并正确处理桶版本控制错误。"
tags: [Release, Console]
weight: 1
url: "/zh/blog/release/console-2.4.2/"
---

**版本：** [v2.4.2](https://github.com/pgsty/silo-console/releases/tag/v2.4.2) · **源码：** [`ef2dd2c41d21`](https://github.com/pgsty/silo-console/commit/ef2dd2c41d212ed6405c90fa8e5ab671899a7365)。

## 更新内容 {#changes}

- 引用已正式发布的 **mcli 20261018**、**silo-pkg v3.14.2** 和上游 **minio-go v7.4.1**。SDK 修复取消后的失败分段上传清理、保留时间 UTC 格式及 STS 时长传递。并行 GET 与 ComposeObject 仍需显式启用。
- 保留桶版本控制操作中被包装的 S3 错误；当 Object Lock 禁止暂停版本控制时，明确返回 `InvalidBucketState`。Server 的保护规则保持不变。
- 使用 **Go 1.27.2** 与 **Node 24.22.0 LTS** 构建。更新 Go x/* 模块和必要的依赖修复：compress **v1.20.3**、msgp **v1.6.5**、etcd **v3.7.2**、fwd **v1.2.1** 和 cpuid **v2.4.1**。保留 go-systemd **v22.6.0** 以支持 NetBSD，保留 tablewriter **v0.0.5** 以兼容现有 MC API。
- 使用 **GoReleaser v2.18.3**、**golangci-lint v2.15.0** 和 **govulncheck v1.9.0**。重新生成版本号为 2.4.2 的内嵌前端，更新源码构建镜像的固定摘要。

## 集成说明 {#integration}

保留的模块路径没有 `/v2` 后缀，因此 Go 消费者使用规范伪版本 `v0.0.0-20261017112417-ef2dd2c41d21`。嵌入 Console 的 Server 必须显式选择 Console 与 MC 两项替换：

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261017112417-ef2dd2c41d21
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261017101407-fa3b8bf72458
```

Console 直接依赖 `github.com/pgsty/silo-pkg/v3 v3.14.2`。既有密码权限迁移规则仍然适用，参见[迁移指南](/zh/compatibility/password-permissions/)。go-jose **v4.1.6** 的 RSA JWK 大小限制适用于导入该库的 Server OIDC 代码；独立 Console 二进制并未链接 go-jose 和 go-ldap。

升级独立 Console 不会替换 Server 二进制，也不代表 Server 待发布的安全和存储修复已经交付。当前正式 Server 仍为 20260916，Server 20261018 已准备签名标签和通过制品验收的草稿。正式支持的管理集成目标为 SILO，与原版上游 MinIO 的兼容属于尽力支持。

## 发布与验证 {#delivery}

二进制、归档、Linux 软件包和源码附带校验清单、SBOM 与签名来源证明。标签对应的精确提交通过完整 CI 矩阵和漏洞检查，包括权限、SSO、复制、浏览器测试、源码镜像一致性和可复现打包。本地验收同时通过完整 Go race 测试与 251 项前端单元测试。

实际下载并核验了全部 **44 个制品**：六个平台二进制、六份归档和九个 Linux 软件包的载荷、依赖版本及许可证材料均与标签源码一致。校验清单的 Sigstore 签名与 GitHub 来源证明通过验证。下载的 Console 二进制与 SILO 20261018 草稿二进制通过真实 API 和浏览器分享测试；Server 仍未正式发布。

公开的 `docker.io/pgsty/silo-console:v2.4.2` 指向已核验的 Linux amd64/arm64 镜像：

```text
sha256:4cf47061e0d2f249df3c1cd2a939966ff3c69cc3cf7d10a7b1b39d5c110ae999
```

[发布核验约定](https://github.com/pgsty/silo-console/blob/v2.4.2/docs/release-contract.md) · [组件版本表](/zh/compatibility/versions/) · [相对 v2.4.1 的源码变化](https://github.com/pgsty/silo-console/compare/v2.4.1...v2.4.2)。
