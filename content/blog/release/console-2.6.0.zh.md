---
title: "SILO Console 2.6.0：用量扫描与存储桶管理改进"
linkTitle: "Console 2.6.0"
date: 2026-11-05
author: "SILO"
description: "Console 2.6.0：目录与存储桶用量、可选持久化后台任务、数值校验、导航修复与安全依赖更新。"
tags: [Release, Console]
draft: false
weight: 1
url: "/zh/blog/release/console-2.6.0/"
---

**Console 2.6.0 已于 2026-11-05（UTC+8）正式发布**，接续
[2.5.1](/zh/blog/release/console-2.5.1/)。
[GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.6.0)
记录了源码提交 `f8ab146695fd1df74e4b84128a286d552921bf00`、发布制品与验收证据。
这是独立 Console 发布，Server 内嵌控制台按服务端的发布周期交付。

[GitHub Releases](https://github.com/pgsty/silo-console/releases) ·
[发布准备 PR #82](https://github.com/pgsty/silo-console/pull/82) ·
[对象管理文档](/zh/administration/console/managing-objects/)

## 目录与存储桶用量 {#usage}

对象浏览器支持可取消的目录大小扫描，并可选统计保留版本。
当前对象字节数与保留字节数分别显示。扫描只读取元数据，不下载对象内容，也不代表物理磁盘占用。
请求使用当前用户的权限；版本扫描另需列出对象版本的权限。

界面显示进度、新鲜度与部分结果。未知、不可用、失败或中断的测量不会显示为零。
只有完成扫描才提供完整统计；并发写入仍可能改变实时列表。
运维人员可以限制扫描时长、条目数、目录数与并发数。

可选的 PostgreSQL 用量后台任务提供持久化队列、检查点、观察者租约与变更事件校准。
显式刷新可以重新启动达到限制的扫描；慢扫描不会阻塞租约续期，存储桶列表在页面刷新后也能恢复有效用量状态。
只有启用这一可选后台任务时才需要 PostgreSQL。

权限、限制、环境变量与后台任务操作见
[用量扫描指南](/zh/administration/console/managing-objects/#usage-scans)。
最初的目录大小功能与指南由 **Urbanize** 在
[PR #70](https://github.com/pgsty/silo-console/pull/70) 中贡献。

## 存储桶管理与导航 {#fixes}

- 保留期、配额与复制带宽在数值转换前完成校验。输入须处于 JSON/浏览器 API 的精确整数范围内；字节显示与速率标签在适用时保留小数。
- 创建启用对象锁的存储桶时拒绝版本排除配置；请求的配置未成功应用时明确报告失败。部分失败可能留下已创建的桶，需要检查其状态；多项配置 API 不构成一个原子事务。
- 存储桶列表保留新版配额值，区分当前字节、保留字节、部分统计与不可用总量。表格、卡片、工具栏和保留量列适应窄屏及较宽的回退字体；API 请求组件明确标注四分钟计数窗口。
- 切换对象或使用浏览器前进、后退时，详情与版本控制内容在新路由渲染完成前隐藏并禁用，避免在新 URL 下操作旧对象；慢 CPU 场景也有回归覆盖，见 [PR #81](https://github.com/pgsty/silo-console/pull/81)。
- 内嵌 Console 服务采用与 CLI 一致的三分钟 keep-alive 默认值，使 HTTP/2 静态资源请求复用持久连接；显式设置 `--keep-alive=0` 仍可禁用复用。

## 运行时与安全依赖 {#dependencies}

| 组件 | 正式版本选择 |
| --- | --- |
| Go | 1.27.3 |
| Node / Yarn | 24.22.1 / 4.13.0 |
| `silo-pkg/v3` | v3.15.2 |
| mcli 源码 | 已发布的 20261026，提交 `0ceb298cdcd0` |
| 上游 `minio-go/v7` | `v7.4.2-0.20261025165926-320af050c445` |
| `golang.org/x/net` | v0.62.0 |
| `golang.org/x/crypto` | `v0.58.1-0.20261009181718-2f1f834330b2` |
{.wide .expand}

`x/net` 更新包含 HTML 解析与渲染相关的
[GO-2026-6860](https://pkg.go.dev/vuln/GO-2026-6860) 和
[GO-2026-6866](https://pkg.go.dev/vuln/GO-2026-6866) 修复。
所选 `x/crypto` 提交将不再维护的 OpenPGP 包从主模块拆出，具体见
[GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932)。
前端还包含 2.5.1 之后纳入的 URI 解码器安全更新。

继续保留已验证的兼容性选择：`go-systemd v22.6.0` 用于 NetBSD 可移植性，
`tablewriter v0.0.5`、`go-runewidth v0.0.29` 与 `go-humanize v1.0.1` 用于保持输出行为。
生产 JavaScript 依赖接受不带忽略项的审计。
开发依赖 `braces 3.0.3` 的精确例外继续绑定已提交的嵌套深度限制补丁与安全回归测试，不是通用漏洞豁免。

## 集成与发布边界 {#delivery}

正式支持的管理目标是 **pgsty/silo**，配合协调选择的 Console、mcli 和 silo-pkg。
与未修改上游 MinIO 的兼容性仍为尽最大努力。
完整验收矩阵覆盖权限、PostgreSQL 用量后台任务、独立与内嵌部署的共享下载、SSO、复制、反代子路径、浏览器交互、交叉编译、包安装及可复现构建。

Server 20261026 内嵌 Console 2.5.1。安装独立 Console 2.6.0 不会替换其内嵌前端，也不会增加新版服务端 API。
用量后台任务集成与内嵌部署需要对应的受维护 SILO 修订；Console 2.6.0 本身不等于一次联合 Server 发布。
既有 Go 模块路径与所需 MC replacement 见
[内嵌指南](https://github.com/pgsty/silo-console/blob/v2.6.0/docs/Embedding.md)。

标签工作流准备二进制、压缩包、Linux 软件包、源码、SHA-256 清单、SPDX SBOM、Sigstore 签名、GitHub provenance 和 Docker Hub 版本候选镜像。
它要求精确提交通过验收，并在 draft 就绪前验证签名与 provenance；不会推进 `latest`。
发布已验证的 GitHub draft 是另一次维护者操作，会启用后续镜像推进流程，具体见
[发布契约](https://github.com/pgsty/silo-console/blob/v2.6.0/docs/release-contract.md)。
