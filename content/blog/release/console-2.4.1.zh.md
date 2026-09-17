---
title: "SILO Console 2.4.1 发布"
linkTitle: "SILO Console 2.4.1 发布"
date: 2026-09-16T16:36:03+08:00
author: "Vonng"
description: "收紧共享下载、迁移密码权限、流式 ZIP、更新依赖，并提供可验证的发布制品。"
tags: [Release, console]
weight: 1
url: "/zh/blog/release/console-2.4.1/"
---

[SILO Console v2.4.1](https://github.com/pgsty/silo-console/releases/tag/v2.4.1)
于 2026 年 9 月 16 日发布，源码为
[`1360e26d976d`](https://github.com/pgsty/silo-console/commit/1360e26d976d82eda395b0b2e449df8c9d49f39c)。
本版接入 pkg v3.14.1 与 mcli 20260916，收紧匿名分享代理，支持多对象流式 ZIP 下载，并提供带签名和构建溯源的发布制品。

## 共享下载 {#sharing}

[#52](https://github.com/pgsty/silo-console/issues/52) 的修复将匿名代理限制为
**配置的 S3 源站上的对象内容 GET 请求**，拒绝重定向、系统路径和通过查询参数选择的非下载操作。
公开对象、预签名链接和指定版本下载继续可用。**不需要新增一个关闭分享的环境变量。**

感谢 [Jiri Pejchal（@jiri-pejchal）](https://github.com/jiri-pejchal) 报告内部指标暴露问题。
支持的请求形式及反向代理要求见[共享下载边界](/zh/reference/minio-server/settings/console/#object-sharing)。

## 密码策略迁移 {#passwords}

**这个补丁版本包含授权语义变化。** 修改密码按钮和会话能力改用 `admin:ChangeMyPassword`；
创建用户、重置他人密码继续使用 `admin:CreateUser`。配合对应的 SILO Server，
单独拒绝 CreateUser 不再锁定调用者自己的密码。要保留旧限制，应在**升级前于同一个 Deny 语句中拒绝两个动作**，保留原资源范围与条件。

更新后的内置 `readonly` 允许自助修改密码，也不再覆盖另一份策略授予的 CreateUser 权限。
已保存的策略覆盖保留原有语句。请协调升级 Server、Console 与 pkg，并阅读[迁移及回滚说明](/zh/compatibility/password-permissions/)。

## 下载与浏览器恢复 {#browser}

- 浏览器支持文件写入器时，多选 ZIP 使用背压流式写入，支持取消和重复下载保护；其他浏览器交给原生下载管理器。两条路径都不会在 JavaScript 内存中缓冲整个 ZIP。
- 只有响应提供可靠总长度时才显示百分比。原生下载会明确提示已交接，此后需在浏览器下载管理器中取消。选择超过 5 GiB 或总大小未知时，界面推荐使用 mcli 进行长时间传输。
- 无效路由和渲染异常提供恢复入口，不清空偏好设置；补全中英文字段、图标控件、退出文字和支持键盘操作的提示。

## 依赖与嵌入 {#dependencies}

| 组件 | 选择的版本 |
| --- | --- |
| 共享包 | `github.com/pgsty/silo-pkg/v3 v3.14.1` |
| MC 源码 | `github.com/pgsty/mc v0.0.0-20260916070421-e952aa78f10a`，对应 mcli 20260916 |
| 上游 minio-go | `v7.3.1-0.20260915093545-32e1f32cb176` |
| JWX / strfmt | v3.3.0 / v0.27.2 |
| React Router | v7.18.4 |
| 构建工具 | Go 1.27.1、Node 24.21.0、Yarn 4.13.0 |

SDK 正确处理 CopyObject HTTP 200 响应内嵌的 S3 错误；JWX 修复自定义 JSON 字段名转义，
strfmt 更新 Go 1.27 主机名校验。嵌入前端和第三方署名已按最终依赖重新生成。
go-systemd v22.6.0 与 tablewriter v0.0.5 是保留的兼容性固定版本。

Go 嵌入方通过历史模块路径 `github.com/minio/console` 的 replacement 选择
`github.com/pgsty/silo-console v0.0.0-20260916075814-1360e26d976d`。
Go 不继承依赖模块的 replacement，需同时复制[标签 README](https://github.com/pgsty/silo-console/blob/v2.4.1/README.md) 中显式的 MC replacement。
正式支持的管理对象是配套 SILO 组件；上游 MinIO/MC 兼容性属于尽最大努力。

## 软件包与验证 {#delivery}

本次 [GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.4.1) 有 **44 个附件**：二进制及归档、DEB/RPM/APK 软件包、源码、法律声明、SPDX SBOM、校验清单及 Sigstore 签名包。校验清单使用 Cosign 签名，构建溯源记录对应标签和工作流。

**2026-09-17 镜像分发更正：** 官方镜像名称是 [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console)，但匿名 token 请求返回 HTTP 401，尚不能确认公开拉取 v2.4.1 或 `latest`。请使用 GitHub 二进制/软件包，不把源码和二进制的发布视为镜像交付证明。Server 内嵌 Console 不受此独立镜像分发状态影响。

Linux 软件包保留 `minio-console.service`、`console-user` 和 `/etc/default/console`。
服务状态目录为 `/var/lib/silo-console`，证书目录改为 `/etc/silo-console/certs`，停止服务最多等待 90 秒。
**已有安装重启前**，请按要求迁移证书和权限，或通过 `CONSOLE_OPTS` 保留旧证书路径。
安装过程保留旧证书与私钥，不会自动重启服务。具体见[软件包升级说明](https://github.com/pgsty/silo-console/blob/6a1802261c6a6f6972b42f347d8d4420ad5d1248/systemd/README.md#upgrading-an-installation-with-existing-certificates)。

精确发布源码通过[完整 CI 矩阵](https://github.com/pgsty/silo-console/actions/runs/35071257392)、
[漏洞检查](https://github.com/pgsty/silo-console/actions/runs/35071257306)和
[发布验证](https://github.com/pgsty/silo-console/actions/runs/35073117397)。
本地还验证了 251 项前端单元测试、51 项浏览器测试、嵌入资源逐字节一致性，以及独立和内嵌部署的分享行为。
实际下载的 Darwin/arm64 二进制经过签名校验清单核验，并连接 SILO 测试服务执行了分享验证。
