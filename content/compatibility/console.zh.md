---
title: "Console 兼容性注记"
linkTitle: "Console"
description: "SILO Console 与上游 MinIO Console 的差异"
url: "/zh/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> **最新已发布：** [Console v2.4.0](/zh/blog/release/console-2.4.0/)（2026-09-08）。对象分页已发布；流式 ZIP、密码权限拆分与新版发布流程尚在 main。Server 内嵌版本与独立发行版不同，见[组件矩阵](/zh/compatibility/versions/)。

SILO Console 是 Silo 构建的 MinIO Console。本页记录二者在哪些地方可以互换使用，在哪些地方存在差异。

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) 延续上游 `minio/console` 的历史，起点是其最终提交 [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563)（2026-04-16），品牌重塑自 `50797deb`（2026-08-04）开始。上游仓库已不再公开 —— `github.com/minio/console` 现在返回 404，而 `minio/mc` 只是归档 —— 因此源码谱系只在这个分支中留存。Go 模块路径仍可解析，因为模块代理继续提供它此前缓存的版本。较早版本记录：[v2.0.0](/zh/blog/release/console-2.0.0/)、[v2.1.0](/zh/blog/release/console-2.1.0/)、[v2.1.1]、[v2.2.0](/zh/blog/release/console-2.2.0/)、[v2.2.1]。

## 原则 {#principles}

本分支遵循与 Silo 其余部分相同的规则：**交付物及其分发渠道改名，其它软件所依赖的接口不改。**

- **改名** —— 磁盘上的产物（`silo-console`）、界面与 `--version` 中的产品标识、分发渠道、签名密钥。
- **不变** —— Go 模块路径 `github.com/minio/console`、全部 `CONSOLE_*` 环境变量（含 `CONSOLE_MINIO_SERVER` 与 `CONSOLE_MINIO_REGION`）、Web 应用调用的 REST API 结构，以及打包标识 `minio-console.service`、`console-user`、`/etc/default/console` —— 因此原地升级软件包依然可用。
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

### 5. 面向开发者：模块图 {#source}

截至 2026-09-13，Console main 直接 require `github.com/pgsty/silo-pkg/v3` v3.14.0，
使用上游 SDK `v7.3.1-0.20260910142817-60bd07042d49`，并保留历史模块路径 `github.com/minio/console`。
维护组件 replacement 为：

```go
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260913012246-4f609a4da3bb
```

Go 不继承依赖的 replacement。Server 必须同时显式选择 PGSTY Console 与 MC。
兼容性固定版本另有 go-systemd v22.6.0（NetBSD）与 tablewriter v0.0.5（MC API）。
旧 `minio/pkg/v3` 可由 colorjson 等间接引入；受维护的策略实现直接来自 silo-pkg。
`minio/pkg => silo-pkg`、`minio-go => silo-go` 的旧 replacement 不再受支持。

**上述是源码图，不是 v2.4.0 发布依赖。** v2.4.0 使用 pkg v3.13.3、MC `c8aa5d25a63a`、SDK `0e78d3f18efe`。
Server 20260903 内嵌的 Console 是 `464a59d73ada`（v2.3.0 版本标识）；Server main 选择 `417559bb2c97`。
精确矩阵见[组件版本](/zh/compatibility/versions/)，嵌入步骤见[源码指南](https://github.com/pgsty/silo-console/blob/main/docs/Embedding.md)。

正式发布门槛针对 SILO、Console、mcli、pkg 的协调栈。上游原版 MinIO/MC 只做非阻塞兼容性探测，
不能据此降级 pkg 或重复实现其 API。

## 迁移 {#migration}

已有的 MinIO Console 部署可以原地升级。服务单元、服务账号与配置文件名称都不变，全部 `CONSOLE_*` 变量按原样读取，因此通常的做法是用 `silo-console` 软件包覆盖安装后重启。

有两处行为会在首次启动后改变，值得提前预期：

- `silo-console` 不会自我更新。请通过软件包、镜像或编排系统来推送新版本。
- 任何依赖控制台访问 MinIO 运营服务的流程 —— 更新源、许可、遥测 —— 都不再有可访问的对端。

## 参见 {#see-also}

- [Silo 服务器兼容性](/zh/compatibility/server/) —— 本控制台所管理的服务器
- [MCLI 客户端兼容性](/zh/compatibility/mcli/) —— 命令行客户端
- [Console 发布说明](/zh/tags/console/) 与 [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1
[v2.3.0]: https://github.com/pgsty/silo-console/releases/tag/v2.3.0
