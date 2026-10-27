---
title: "SILO Console 2.5：界面与管理功能更新"
linkTitle: "Console 2.5.1"
date: 2026-10-26
lastmod: 2026-10-27
author: "SILO"
description: "Console 2.5.0 与 2.5.1 相对 2.4.2 的完整更新：界面、诊断、组权限、下载与可访问性。"
tags: [Release, Console]
weight: 2
url: "/zh/blog/release/console-2.5.1/"
aliases:
  - /blog/release/console-2.5.0/
---

**SILO Console v2.5.1 已发布**，源码为 [`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed)，也是 [SILO 20261026](/zh/blog/release/silo-20261026/) 内嵌的控制台版本。本文覆盖相对 **v2.4.2** 的完整 2.5 系列变化，包括 2.5.0 界面更新与 2.5.1 修复。

[GitHub 发布](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) · [下载](/zh/download/#console) · [全部源码变化](https://github.com/pgsty/silo-console/compare/v2.4.2...v2.5.1)

## 导航、概览与指标 {#interface}

界面采用中性的明暗配色、系统字体、一致的信息密度、Lucide 图标、清晰焦点和减少动态效果支持。移动端抽屉、平板侧栏适配窄屏，并优先保留用户设置；对象详情在移动端采用可恢复焦点的面板，对话框和表单适配小屏。保留中英文、可访问控件及许可署名。

导航按权限组织 Identity、Monitoring、Settings、Tools，保留统一 Buckets 入口和最近访问桶，并维持登录后目标与既有对象深链接。`/browser` 跳转到 `/buckets`，桶管理裸路径进入 Summary。Help 持续提供文档、视频及 Blog/RSS。

Overview 显示节点/磁盘健康、原始容量、告警、快捷操作和数据新鲜度。容量来自 Server 实际报告，不推算 EC 可用容量；缺失统计显示未知。Metrics V3 保留在 Monitoring 下，图表区分缺失样本与零值，并正确处理逐节点导出。即使 Server 20261026 已返回实时桶清单，桶/账户用量仍来自扫描器。

## 桶、对象与任务 {#objects}

- 桶表支持排序、筛选、URL 查询保存、表格/卡片切换、大列表虚拟化和未知用量显示；稳定标识避免排序后选错桶，导航后丢弃未完成的搜索更新。
- 仅写用户也能进入对象工作区；保留通配桶根授权和前缀限制；修改标签等被拒绝时显示服务端错误。列表、读取和修改权限仍分别检查。
- 提供有界的文本、Markdown、CSV/TSV 预览、源码视图、安全 HTML 处理，以及明确的 **1 MiB** 截断提示；支持的表单给出不含秘密的 mcli 等价命令。
- Tasks 跟踪传输、原生 ZIP 下载、批量删除、非当前版本清理和恢复；修改并发有界，重试仅针对失败项。取消任务不撤销已完成写入，交给浏览器下载不代表文件已落盘。
- 增加键盘导航、范围选择、当前页全选、快捷键帮助和按权限显示的菜单。继续使用游标分页，排序/筛选/全选只作用于当前页，不覆盖整个桶。

## 身份与诊断 {#identity}

用户页展示状态、直接策略、组继承和访问密钥数；策略页区分原生、被覆盖和自定义策略，展示分配数与受影响身份。原生策略在显式覆盖前只读，被覆盖的内置策略支持 Reset。重载失败清除过期编辑内容，语言切换保留草稿；表单正确关联标签并遮蔽远端秘密。

**Reset 与实时桶清单需要 Server 20261026。** 单独升级 Console 不会修复旧 Server 的策略缓存，也不会替换其内嵌界面。

Health、Trace、Logs、Watch、Speedtest、Profile 复用既有唯一 reader 完成 WebSocket 关闭握手，Close 写入和等待共享 **5 秒预算**，不限制活跃诊断流。修复 [Azat / @azataiot 在 #63](https://github.com/pgsty/silo-console/issues/63) 报告的高 RTT 健康报告截断与 1006 关闭；包装过的超时仍返回 1008，不暴露内部细节。健康报告在版本探测和正文间复用一个 JSON 解码器，保留缓冲帧；拒绝截断、取消和失败响应，保留 madmin v3 的签名传输和重试行为。

## 2.5.1 补丁修复 {#patch}

- 仅修改组状态时保留成员；显式传入成员数组仍具有替换语义。
- 保留 OIDC 字符串数组组权限；配置 HTTPS 或可信 TLS 代理后会话 Cookie 继续保持安全，不盲信任意转发头。
- 凭据导出保留精确 UTF-8 JSON 字节；ZIP 在首个响应字节之前失败时保留 S3 错误状态，不暴露后端细节。
- 修复表格和控件焦点、可访问名称与进度值；标签列表尺寸变化后保持当前焦点标签可见。
- 采用正式 mcli 20261026、silo-pkg v3.15.2，以及移除复制配置接受 HTTP 204 的上游 SDK 修复。

对应记录为 [#67](https://github.com/pgsty/silo-console/pull/67)、[#68](https://github.com/pgsty/silo-console/pull/68)、[#69](https://github.com/pgsty/silo-console/pull/69)。

## 依赖与交付 {#delivery}

正式基线为 Go **1.27.3**、Node **24.22.1**、Vite **8.3.5**、GoReleaser **2.19.0**、silo-pkg **3.15.2**、mcli **20261026** 和上游 minio-go **`320af050c445`**。为保留输出与平台兼容，2.5 系列继续固定 tablewriter 0.0.5、go-humanize 1.0.1、go-runewidth 0.0.29、go-systemd 22.6.0。见[统一依赖/安全清单](/zh/blog/release/silo-20261026/#runtime-fixes)。

[正式 Release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1)提供平台二进制与归档、Linux 包、源码、校验和、SPDX SBOM 和 Sigstore/GitHub 溯源。Windows 使用 ZIP，Linux/macOS 使用 tar.gz；官方镜像位于 Docker Hub：`docker.io/pgsty/silo-console:v2.5.1`。验证方式见[发布契约](https://github.com/pgsty/silo-console/blob/v2.5.1/docs/release-contract.md)。

交付检查校验 Windows ZIP 归档，并在发布多架构镜像前拉取各平台摘要。可复现构建使用隔离工作目录并限制临时磁盘用量；Semgrep 运行环境固定为 Python 3.12.12。生成的 API 文件与内嵌前端资源随兼容性检查一起重新构建，详见共享依赖清单。

正式维护的管理目标是 **pgsty/silo**，上游 MinIO 兼容尽最大努力。既有环境变量、API 路径、服务标识和模块路径继续支持；精确 API 与内嵌依赖图见[兼容指南](/zh/compatibility/console/)。
