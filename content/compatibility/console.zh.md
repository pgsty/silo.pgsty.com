---
title: "Console 兼容性注记"
linkTitle: "Console"
description: "SILO Console 与上游 MinIO Console 的差异"
url: "/zh/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> **最新版本：** [Console v2.4.1](/zh/blog/release/console-2.4.1/)（2026-09-16），包含共享下载边界修复、密码权限拆分、流式 ZIP 与签名发布制品。配套版本见[组件矩阵](/zh/compatibility/versions/)。

SILO Console 是 Silo 构建的 MinIO Console。本页记录二者在哪些地方可以互换使用，在哪些地方存在差异。先看[三档兼容性总览](/zh/compatibility/)，再按下文核对界面与自动化接口。

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) 延续上游 `minio/console` 的历史，起点是其最终提交 [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563)（2026-04-16），品牌重塑自 `50797deb`（2026-08-04）开始。上游仓库已不再公开 —— `github.com/minio/console` 现在返回 404，而 `minio/mc` 只是归档 —— 因此源码谱系只在这个分支中留存。Go 模块路径仍可解析，因为模块代理继续提供它此前缓存的版本。较早版本记录：[v2.0.0](/zh/blog/release/console-2.0.0/)、[v2.1.0](/zh/blog/release/console-2.1.0/)、[v2.1.1]、[v2.2.0](/zh/blog/release/console-2.2.0/)、[v2.2.1]。

## 原则 {#principles}

本分支优先保留既有集成契约，同时明确记录授权、响应与界面变化。

- **改名** —— 磁盘上的产物（`silo-console`）、界面与 `--version` 中的产品标识、分发渠道、签名密钥。
- **保留的基础契约** —— Go 模块路径 `github.com/minio/console`、既有 `CONSOLE_*` 环境变量（含 `CONSOLE_MINIO_SERVER` 与 `CONSOLE_MINIO_REGION`），以及打包标识 `minio-console.service`、`console-user`、`/etc/default/console`。REST API 沿用既有体系，具体响应与操作变化见[下文](#api-output)。
- **切断** —— 自动自更新、遥测、分析、信标、外部脚本与字体、以及 call-home。只有在显式配置时才会访问版本目录，入口是 `SILO_RELEASE_SERVICE_HOST`，并保留 `RELEASE_SERVICE_HOST` 作为兼容回退。
- **保留** —— 上游版权与 AGPL-3.0 许可证。运行时输出同时致谢 MinIO, Inc. 与 PGSTY。

> [!NOTE]
> SILO Console 不是通用 S3 浏览器。它的管理功能需要 Silo 在 S3 API 之外实现的 MinIO 兼容管理 API。

## 差异 {#changed}

### 1. 保留了完整的管理控制台 {#scope}

这是最大的功能差异，方向与通常的分支相反：上游把社区版控制台裁剪成了对象浏览器，SILO Console 保留了完整的管理界面 —— 仪表盘、健康状态、日志、诊断与速度测试；存储桶、对象、生命周期、复制、通知与分层管理；用户、用户组、服务账号、策略、身份提供方与 KMS 配置；以及服务器配置。

### 2. 仪表盘面向 Metrics V3 {#metrics}

仪表盘组件查询 **MinIO Metrics V3** 指标目录 —— 也就是当前部署实际抓取的那一套 —— 并针对其零值语义与按节点导出的语义做了保护，使面板能区分"真实的零"与"数据缺失"。映射关系记录在 [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/main/docs/metrics-v3.md)。

### 3. 更小、更安静的产物 {#payload}

内嵌前端从约 10 MB 降到 3 MB 以内，可逐字节复现构建，并由发布门禁强制校验。没有任何形式的遥测，页面本身也没有外部网络依赖。

### 4. 双语界面 {#i18n}

界面、帮助内容与文档链接提供英文与中文，通过页面级切换使用，且未引入额外的运行时依赖。

### 5. 对象列表按页操作 {#pagination}

对应 [B02](/zh/compatibility/#b02)，自 Console v2.4.0 起使用游标分页，v2.4.1 保留该行为。默认每页 100 项，可选 50、100、250、500、1,000；提供首页、上一页与下一页，不提供“加载全部”或任意跳页。

**排序、名称筛选和全选只作用于当前页。** 只有首页已包含整个目录时，它们才覆盖整个目录。翻页保留筛选文本、清空选择；更换页大小回到首页，更换目录清空筛选。失败的页面保留上一页供重试。

Rewind 与“显示已删除对象”没有游标，最多返回 1,000 个版本，并有时间预算；触及限制会提示结果不完整。它们限制浏览器收到的结果，不保证服务端只扫描这么多版本。详见[对象浏览器契约](https://github.com/pgsty/silo-console/blob/v2.4.1/docs/ObjectBrowser.md#paging)。

### 6. API 返回与自动化 {#api-output}

对应 [B04](/zh/compatibility/#b04)、[O05](/zh/compatibility/#o05)。会话响应增加 `accountAccessKey`，对象列表显式返回零字节对象的 `size: 0`；会话能力字段还会随有效权限变化，按钮可见不替代服务端授权。自制解析器应容忍新增字段，Console 自动化应处理分页、会话失效和 WebSocket 错误。

用户启用/禁用新增独立的 `PUT /api/v1/user/{name}/status`，旧 `PUT /api/v1/user/{name}` 保留但已弃用；批量下载沿用原入口，同时接受受限表单以支持原生流式 ZIP。改密权限另见[密码权限迁移](/zh/compatibility/password-permissions/)，分享下载边界见 [v2.4.1 说明](/zh/blog/release/console-2.4.1/)；定制调用以[该版 API 定义](https://github.com/pgsty/silo-console/blob/v2.4.1/swagger.yml)为准。

### 7. 面向开发者：模块图 {#source}

Console v2.4.1 直接 require `github.com/pgsty/silo-pkg/v3` v3.14.1 与上游 SDK
`v7.3.1-0.20260915093545-32e1f32cb176`，保留历史模块路径 `github.com/minio/console`。
嵌入方显式选择以下已发布源码：

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20260916075814-1360e26d976d
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260916070421-e952aa78f10a
```

Go 不继承依赖模块的 replacement，Server 必须同时选择 PGSTY Console 与 MC。
go-systemd v22.6.0 保留 NetBSD 兼容，tablewriter v0.0.5 保留 MC API 兼容。
colorjson 带入的历史 minio/pkg 传递依赖与维护中的 silo-pkg 策略实现分开；不使用旧的
`minio/pkg => silo-pkg` 或 `minio-go => silo-go` replacement。
详见[组件矩阵](/zh/compatibility/versions/)和[嵌入指南](https://github.com/pgsty/silo-console/blob/v2.4.1/docs/Embedding.md)。

发布门禁验证配套 SILO、Console、mcli 与 pkg；上游 MinIO/MC 探针属于非阻塞兼容信号，不要求降低 pkg 版本或复制 API。

## 迁移 {#migration}

官方容器镜像为 [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console)。固定版本使用 `:v2.4.1`；`latest` 通过正式发布与镜像验证后更新。

已有的 MinIO Console 部署可以原地升级。服务单元、服务账号与配置文件名称都不变，全部 `CONSOLE_*` 变量按原样读取，因此通常的做法是用 `silo-console` 软件包覆盖安装后重启。

有两处行为会在首次启动后改变，值得提前预期：

- `silo-console` 不会自我更新。请通过软件包、镜像或编排系统来推送新版本。
- 任何依赖控制台访问 MinIO 运营服务的流程 —— 更新源、许可、遥测 —— 都不再有可访问的对端。

v2.4.1 升级还需检查[密码权限迁移](/zh/compatibility/password-permissions/)。
Linux 软件包使用 `/etc/silo-console/certs` 作为证书目录；重启前迁移旧证书，或在
`/etc/default/console` 的 `CONSOLE_OPTS` 中保留旧路径。服务名和配置文件路径不变。
共享代理仅接受对象下载，不需要新增环境变量。详见[本版发布说明](/zh/blog/release/console-2.4.1/)。

## 参见 {#see-also}

- [Silo 服务器兼容性](/zh/compatibility/server/) —— 本控制台所管理的服务器
- [MCLI 客户端兼容性](/zh/compatibility/mcli/) —— 命令行客户端
- [Console 发布说明](/zh/tags/console/) 与 [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1
[v2.3.0]: https://github.com/pgsty/silo-console/releases/tag/v2.3.0
