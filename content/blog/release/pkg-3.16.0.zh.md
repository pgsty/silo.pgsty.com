---
title: "silo-pkg 3.16：JOSE 安全更新与配置修复"
linkTitle: "pkg 3.16.0"
date: 2026-11-08
author: "SILO"
description: "silo-pkg 3.16.0 更新 JOSE 与网络依赖，修正 x86 特性检测，并在 YAML 配置读写中保留字面量合并键字符串。"
tags: [Release, Dependencies]
weight: 3
url: "/zh/blog/release/pkg-3.16.0/"
---

**silo-pkg v3.16.0** 是 `github.com/pgsty/silo-pkg/v3` 的源码维护版本，要求 **Go 1.27.3**，与 v3.15.2 保持 API 兼容。[SILO Server 20261109](/zh/blog/release/silo-20261109/)、[Console 2.7.0](/zh/blog/release/console-2.7.0/) 与 [mcli 20261109](/zh/blog/release/mcli-20261109/) 已采用 v3.16.0 构建发布；库发布本身不会替换更早的应用制品。

## 依赖更新 {#dependencies}

| 模块                            | v3.15.2   | v3.16.0                                 |
| ------------------------------- | --------- | --------------------------------------- |
| `github.com/go-jose/go-jose/v4` | `v4.1.6`  | `v4.1.9`                                |
| `golang.org/x/net`              | `v0.61.0` | `v0.62.0`                               |
| `golang.org/x/crypto`           | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` |
| `github.com/klauspost/cpuid/v2` | `v2.4.1`  | `v2.4.2`                                |
| `go.yaml.in/yaml/v3`            | `v3.0.5`  | `v3.0.6`                                |
{.wide .expand}

JOSE 更新包含 [go-jose v4.1.7](https://github.com/go-jose/go-jose/releases/tag/v4.1.7) 的五项安全修复：无效 RSA 密钥指纹、嵌入未导出字段的 JSON 解码、JWE 受保护与未受保护头处理、RSA 证书验证限制，以及 JWS 签名数/JWE 接收者数限制。v4.1.9 还修复了 OpaqueSigner 对未识别公钥类型的兼容回归，并改进不支持密钥的错误返回。上述公告针对依赖库，是否影响某个应用取决于它实际暴露的操作。

维护中的应用根模块此前已经选用表中的网络依赖版本。本次将该基线纳入共享模块发布，便于其他消费方采用；不能据此认定既有应用构建仍使用旧版依赖。

cpuid 更新修正了 x86 XSAVE、OSXSAVE 检测所用的 ECX 位。YAML 编码器会为字面量 `<<` 键加引号，避免配置保存后再次读取时被误当作合并指令。新增配置读写往返回归测试覆盖此行为。

## 兼容性与采用方式 {#compatibility}

公开包 API、IAM 策略格式与授权判定保持兼容。infraAdmin 策略文档明确列出了原本已有的批任务权限。Go 要求仍为 1.27.3，上游 `minio-go/v7` 引用仍为 `v7.4.2-0.20261025165926-320af050c445`。

继续保留 `go-humanize v1.0.1`、`go-runewidth v0.0.29` 与 `go-systemd/v22 v22.6.0` 的兼容性选择。Go 不会继承依赖模块的 `replace` 指令，各应用仍需保留自身所需的替换。

```sh
go get github.com/pgsty/silo-pkg/v3@v3.16.0
go mod tidy
```

使用 Go 1.27.3 重新构建并测试消费方应用。[组件矩阵](/zh/compatibility/versions/)区分独立发布的库版本与应用制品实际嵌入的版本。正式支持的目标是维护中的 PGSTY 组件栈，对上游 MinIO/MC 尽最大努力兼容。

## 验证 {#verification}

发布源码为 [`b7aeea85e84e`](https://github.com/pgsty/silo-pkg/commit/b7aeea85e84e8888d6ab424c7123a1297711bc3f)。验证覆盖全量 lint 与 race 测试、LDAP 集成、模块校验及选定 go-jose/coreos OIDC 版本的依赖 race 测试。YAML 回归测试在 v3.0.5 上失败，在 v3.0.6 上通过。发布提交对应的流水线为 [Go](https://github.com/pgsty/silo-pkg/actions/runs/42488674109)、[LDAP](https://github.com/pgsty/silo-pkg/actions/runs/42488674310) 与 [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/42488674390)。

[GitHub Release](https://github.com/pgsty/silo-pkg/releases/tag/v3.16.0) · [相对 v3.15.2 的变更](https://github.com/pgsty/silo-pkg/compare/v3.15.2...v3.16.0)
