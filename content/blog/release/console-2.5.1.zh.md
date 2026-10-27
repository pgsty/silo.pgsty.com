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

**SILO Console v2.5.1 现已正式发布**（源码提交 [`fff1618d9abb`](https://github.com/pgsty/silo-console/commit/fff1618d9abbf1f6125f1914bd50818e2bc347ed)），同时作为 [SILO 20261026](/zh/blog/release/silo-20261026/) 的内嵌控制台交付。本文完整汇总自 **v2.4.2** 以来的 2.5 系列变更，涵盖 `v2.5.0` 的界面重构与 `v2.5.1` 的问题修复。

[GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) · [下载](/zh/download/#console) · [完整源码对比](https://github.com/pgsty/silo-console/compare/v2.4.2...v2.5.1)

## 导航、概览与监控指标 {#interface}

2.5 系列重构了整体界面视觉与交互：采用柔和的明暗主题配色、系统原生字体、统一的信息密度、Lucide 图标库、清晰的键盘焦点样式，并支持系统的“减少动态效果”（Reduced Motion）偏好。移动端抽屉与平板窄侧栏针对小屏做了专门适配，对象详情在移动端以可恢复焦点的底部抽屉呈现，同时完整保留中英双语切换、无障碍控件与开源许可署名。

左侧导航按当前会话的实际权限组织 Identity、Monitoring、Settings 与 Tools 分组，合并了统一的 Buckets 入口与最近访问存储桶列表，并保持登录重定向目标与既有对象深链接兼容（`/browser` 自动跳转至 `/buckets`，桶管理根路径默认进入 Summary 页）。Help 菜单继续提供文档、视频与 Blog/RSS 入口。

Overview 概览页直观展示节点与磁盘健康状态、原始物理容量、活跃告警、快捷操作及数据刷新时间。容量直接采用 Server 上报的实测值（不凭空估算纠删码可用容量），缺失的统计项明确显示为未知。Monitoring 下的 Metrics V3 面板严格区分“样本缺失”与“真实零值”，并正确处理逐节点重复导出的集群指标。注意：尽管 Server 20261026 已支持返回实时存储桶清单，存储桶与账户的对象用量统计仍由后台扫描器异步汇总。

## 存储桶、对象浏览器与任务中心 {#objects}

- **存储桶列表：** 支持排序、名称筛选、URL 查询参数持久化、表格/卡片视图切换、大列表虚拟滚动及未知用量标注；使用稳定的行标识防止排序后选错目标桶，并在页面跳转后自动丢弃在途的旧搜索结果。
- **细粒度权限体验：** 仅具备写入权限的用户也可正常进入对象工作区；完整保留桶根通配授权与前缀访问限制；修改标签等操作被服务端拒绝时直接展示服务端返回的错误原因（列举、读取与修改权限仍各自独立判定）。
- **在线预览与命令提示：** 支持最大 **1 MiB** 的文本、Markdown、CSV/TSV 表格预览、源码高亮、安全 HTML 渲染及明确的截断提示；常用配置表单可直接生成脱敏的等价 `mcli` 命令。
- **Tasks 任务中心：** 统一跟踪文件上传下载、原生流式 ZIP 打包下载、批量删除、历史版本清理与对象恢复任务；写操作并发受控，重试仅针对失败条目（取消任务不会回滚已完成的写入；大文件或流式 ZIP 下载触发浏览器保存后，请在下载完成后核对本地文件完整性）。
- **键盘导航与分页：** 新增键盘上下移动、Shift 范围选择、当前页全选、快捷键面板与按权限裁剪的右键菜单。对象列表继续采用游标分页，排序、名称筛选与全选仅作用于当前页。

## 身份管理与高延迟诊断 {#identity}

用户详情页集中展示账号状态、直接绑定策略、用户组继承策略与 Access Key 数量；策略管理页明确区分原生内置策略、已被覆盖的内置策略与自定义策略，并显示策略分配计数及受影响身份。原生内置策略默认只读（需显式确认后才允许覆盖），已被覆盖的内置策略提供一键 **Reset** 恢复原生定义。重新加载失败时会清空过期的编辑器内容，切换界面语言时保留未保存草稿，表单统一补齐无障碍标签关联并默认遮蔽远端密钥。

**注意：内置策略 Reset 与实时存储桶清单需要配合 Server 20261026 使用。** 单独升级独立部署的 Console 不会修复旧版 Server 的策略缓存，也不会替换旧版 Server 内嵌的前端界面。

在诊断工具面，Health、Trace、Logs、Watch、Speedtest 与 Profile 六类实时诊断流统一复用唯一的读取协程完成 WebSocket 关闭握手（Close 帧发送与等待共享 **5 秒超时预算**，且不打断正常活跃流），彻底修复了 [Azat / @azataiot 在 #63](https://github.com/pgsty/silo-console/issues/63) 中报告的高延迟链路下健康报告截断与 `1006` 异常关闭问题（超时错误返回标准 `1008` 状态码，不泄露内部堆栈细节）。同时，健康报告下载在版本探测与正文读取之间复用同一个 JSON 解码器以保留预读缓冲帧，拒绝被截短、已取消或失败的响应流，并保持 `madmin v3` 的签名传输与重试策略。

## 2.5.1 补丁修复 {#patch}

- **用户组状态切换（[#67](https://github.com/pgsty/silo-console/pull/67)）：** 单独切换用户组启用/禁用状态时保留组内现有成员；显式传入 `members` 数组时仍按原语义替换成员列表。
- **OIDC 组权限与反向代理会话（[#66](https://github.com/pgsty/silo-console/pull/66)）：** 正确保留 OIDC 字符串数组格式的组声明权限；仅在启用了 HTTPS 或配置了可信 TLS 反向代理转发头时设置 `Secure` 会话 Cookie，不再盲目信任未校验的客户端转发头。
- **凭据导出与流式 ZIP 错误状态（[#68](https://github.com/pgsty/silo-console/pull/68)）：** Access Key 导出完整保留原始 UTF-8 JSON 字节；流式 ZIP 下载若在写出首个响应字节前失败，直接透传底层 S3 错误状态码。
- **无障碍与焦点恢复（[#68](https://github.com/pgsty/silo-console/pull/68)）：** 修复表格与表单控件的键盘焦点恢复、可访问名称及进度条数值属性；窗口尺寸变化导致标签栏重排时保持当前焦点标签可见。
- **配套依赖升级（[#69](https://github.com/pgsty/silo-console/pull/69)）：** 升级至正式版 `mcli 20261026`、`silo-pkg v3.15.2` 以及支持 HTTP `204` 移除复制配置的上游 SDK。

## 依赖与交付验证 {#delivery}

本版基于 Go **1.27.3**、Node **24.22.1**、Vite **8.3.5**、GoReleaser **2.19.0**、silo-pkg **3.15.2**、mcli **20261026** 与上游 minio-go **`320af050c445`** 构建；为保持终端输出格式与跨平台兼容，继续固定 `tablewriter v0.0.5`、`go-humanize v1.0.1`、`go-runewidth v0.0.29` 与 `go-systemd v22.6.0`（详见[统一依赖与安全审计清单](/zh/blog/release/silo-20261026/#runtime-fixes)）。

[GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.5.1) 提供各平台二进制归档、Linux 软件包、源码包、SHA-256 校验和、SPDX SBOM 以及 Sigstore/GitHub 构建溯源证明。Windows 归档改用 `.zip` 格式（Linux 与 macOS 保持 `.tar.gz`），官方多架构镜像已发布至 Docker Hub（`docker.io/pgsty/silo-console:v2.5.1`），核验步骤见[发布契约](https://github.com/pgsty/silo-console/blob/v2.5.1/docs/release-contract.md)。

前端静态资源与内嵌产物在隔离工作目录中完成逐字节可复现构建。SILO Console 正式维护的管理目标为 **pgsty/silo**（对上游 MinIO 保持尽力而为兼容），既有 `CONSOLE_*` 环境变量、API 路由、服务单元名称与 Go 模块路径均保持不变；详细的 API 与内嵌依赖说明见 [Console 兼容性指南](/zh/compatibility/console/)。
