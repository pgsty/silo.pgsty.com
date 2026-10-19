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

**发行版：**[v3.14.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.2) · **源码：**[`c6835145176f`](https://github.com/pgsty/silo-pkg/commit/c6835145176f385dd5f2d2a6d5ccd337b258d9bb)。

这是 `github.com/pgsty/silo-pkg/v3` 的纯源码发行版，为已发布的 [mcli 20261018](/zh/blog/release/mcli-20261018/) 与 [Console v2.4.2](/zh/blog/release/console-2.4.2/) 提供依赖基线。后续 [v3.14.3](/zh/blog/release/pkg-3.14.3/) 在此基础上优化策略判定性能，已被 Server 20261018 选用。

## 变更 {#changes}

- 上游 **minio-go 升至 v7.4.1**：调用者取消后仍清理失败的分片上传，以 UTC 序列化保留时间，保留请求的 STS 时长，并支持 Kubernetes 投射令牌文件。并行 GET 与 ComposeObject 仍需显式启用。
- **go-jose 升至 v4.1.6**，修复解析恶意 RSA JWK 时过量消耗 CPU 的问题（[GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)）；**LDAP 升至 v3.4.15**、**msgp 升至 v1.6.5**、**etcd 客户端升至 v3.7.2**。
- **x/crypto 升至 v0.58.0**、**x/net 升至 v0.61.0**、**x/sys 升至 v0.49.0**、**x/text 升至 v0.43.0**。使用 **Go 1.27.2** 开发与测试，保留库的 **Go 1.26** 最低要求，以及用于 NetBSD 的 **go-systemd v22.6.0** 替换。

## 兼容性与采用方式 {#adoption}

```go
require github.com/pgsty/silo-pkg/v3 v3.14.2
```

公开包接口与密码策略语义不变。从 v3.14.0 之前升级的用户仍需遵循[密码权限迁移说明](/zh/compatibility/password-permissions/)。

go-jose 拒绝超过 **4096 位**的 RSA JWK；使用该解析器的应用应检查身份提供方的密钥。低于一小时的 STS 时长现在按原请求发送，因此不合法的短时长可能被服务端拒绝。依赖出现在 `go.mod` 中，不代表每个消费方的二进制都链接了其中所有包。

采用本模块需要重新构建应用。本版没有可执行程序、系统软件包或容器镜像，也不会更新已经安装的 Server、Console 或 mcli。参见[组件矩阵](/zh/compatibility/versions/)。

## 验证 {#validation}

发布记录包含 Go 1.27.2 下的完整 lint 与 race 测试、Go 1.26.9 下的 race 测试、OpenLDAP 集成、模块整洁性及校验和检查。漏洞扫描未发现可达或已导入包漏洞；未使用的 OpenPGP 仍有模块级公告。JOSE 公告同时对照上游核验，没有只依赖漏洞数据库。

标签源码 CI：[Go](https://github.com/pgsty/silo-pkg/actions/runs/38743292347)、[LDAP](https://github.com/pgsty/silo-pkg/actions/runs/38743292597)、[VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/38743292281)。

[相对 v3.14.1 的变更](https://github.com/pgsty/silo-pkg/compare/v3.14.1...v3.14.2) · [PR #10](https://github.com/pgsty/silo-pkg/pull/10)。
