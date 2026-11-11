---
title: "Console 兼容性注记"
linkTitle: "Console"
description: "SILO Console 与上游 MinIO Console 的差异"
url: "/zh/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> [!NOTE]
> **最新正式版：** [Console v2.7.1](/zh/blog/release/console-2.7.1/)（2026-11-12，UTC+8）在元数据编辑时保留服务账号策略继承关系、拦截各类空内联策略变体、在编辑弹窗内直接提示保存错误、启用严格策略 JSON 校验，并升级至 Go 1.27.4、[silo-pkg v3.16.1](/zh/blog/release/pkg-3.16.1/) 与 [mcli 20261112](/zh/blog/release/mcli-20261112/)。**已公开的 SILO Server 20261109 内嵌 Console v2.7.0**（Server 20261026 内嵌 v2.5.1；待发布的 Draft Server 20261112 内嵌 v2.7.1）。升级独立 Console 不会替换旧版 Server 内嵌控制台；显式重置内联策略恢复继承（`{}`）需配合 `20261109` 之后的 Server 更新，内置策略 Reset 与实时存储桶列表需配合 Server 20261026 及后续版本生效。配套版本见[组件矩阵](/zh/compatibility/versions/)。

SILO Console 是 Silo 构建的 MinIO Console；**已公开的 SILO Server 20261109 内嵌 Console v2.7.0**（Server 20261026 内嵌 v2.5.1），同时也提供独立发布的制品。本页记录 SILO Console 与上游 MinIO Console 在哪些地方可以互换使用，在哪些地方存在差异。先看[三档兼容性总览](/zh/compatibility/)，再按下文核对界面与自动化接口。

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) 延续上游 `minio/console` 的历史，起点是其最终提交 [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563)（2026-04-16），品牌重塑自 `50797deb`（2026-08-04）开始。上游仓库已不再公开 —— `github.com/minio/console` 现在返回 404，而 `minio/mc` 只是归档 —— 因此源码谱系只在这个分支中留存。Go 模块路径仍可解析，因为模块代理继续提供它此前缓存的版本。历次版本记录：[v2.0.0](/zh/blog/release/console-2.0.0/)、[v2.1.0](/zh/blog/release/console-2.1.0/)、[v2.1.1]、[v2.2.0](/zh/blog/release/console-2.2.0/)、[v2.2.1]、[v2.3.0](https://github.com/pgsty/silo-console/releases/tag/v2.3.0)、[v2.4.0](/zh/blog/release/console-2.4.0/)、[v2.4.1](/zh/blog/release/console-2.4.1/)、[v2.4.2](/zh/blog/release/console-2.4.2/)、[v2.5.1](/zh/blog/release/console-2.5.1/)、[v2.6.0](/zh/blog/release/console-2.6.0/)、[v2.7.0](/zh/blog/release/console-2.7.0/) 与 [v2.7.1](/zh/blog/release/console-2.7.1/)。

<a id="candidate-policy-edit" data-td-print-local></a>

## 2.7.1 服务账号策略继承保护与严格 JSON 校验 {#release-271}

[Console 2.7.1](/zh/blog/release/console-2.7.1/)（`3825ebc44451`）区分继承与 inline policy（`1be8a74bf`），因此修改访问密钥的名称、描述、有效期或状态会保留继承关系，不会把父账号策略保存成一份 inline policy 副本。要移除已有的 inline 限制，关闭 **Restrict beyond user policy** 开关；Console 会发送显式空策略以恢复继承。开启 **Restrict beyond user policy** 时，创建或替换策略不能提交空编辑器、`{}`、`{"Statement":[]}` 或 `{"Statement":null}`（`a1a84cab4`、`1fdb279fd`、`3825ebc44`）；后端接受的大小写、Unicode 折叠与重复键空文档变体同样被拦截，且保存错误直接在编辑弹窗内展示。历史空内联策略未发生变化时，仍可仅编辑元数据并保留既有权限；Console 后端接口同步执行严格策略 JSON 校验（拒绝未知字段、尾部多余载荷、空 `Principal: {}` / `NotPrincipal` 与空命名策略）。

显式重置内联策略恢复继承需要配套的 [`20261109` 之后 Server 策略语义](/zh/compatibility/server/#candidate-after-20261109)：省略/null 表示保留，显式空文档表示重置，非空文档缺少 Version 时补默认值。该修复不包含在 Console v2.7.0 或已公开的 Server 20261109 中；独立 Console 2.7.1 可立即保护纯元数据编辑，Server 内嵌控制台将随下一版 Server 发布更新。

## 2.7.0 十种界面语言、容器 CA 信任与用量后台任务修复 {#release-270}

[Console 2.7.0](/zh/blog/release/console-2.7.0/)（已内嵌于 [SILO Server 20261109](/zh/blog/release/silo-20261109/)）交付以下改动：

- **十种界面语言与阿拉伯语 RTL：** 共享语言菜单与命令面板扩展至十种内置语言，支持阿拉伯语从右向左（RTL）布局及输入框控件对齐（`a9da731c5`、`bc17e124a`）。
- **容器 CA 证书包与 `/tmp`：** scratch 容器镜像内置 `/etc/ssl/certs/ca-certificates.crt` 与权限为 `1777` 的 `/tmp` 目录，开箱支持公共 HTTPS 端点访问及大型分片请求缓冲。
- **普通 HTTP 浏览器操作：** **计算目录大小**与解密密钥复制按钮在普通 HTTP（如 `http://<ip>:9001`）下可直接工作，不再依赖浏览器安全上下文。
- **用量后台任务 TLS、扫描预算与生命周期：** `console usage-worker` 支持 `--certs-dir`（同时信任系统根证书、`certs/CAs` 与 `public.crt`，`ec897252f`），`CONSOLE_USAGE_SCAN_TIMEOUT` 仅累计实际 S3 列举分片耗时（`543d3d2af`），优雅停机时持久化已接收事件与检查点，并在删除存储桶时清理历史用量记录（`49ad0dff8`..`082b23700`）。升级时须先停齐旧版 worker，再启动 2.7.0 worker。
- **上传校验与 API 文档：** 畸形或截断的 multipart 上传返回 HTTP `400` 而不再触发 handler panic（`f1edc61fe`）；`/api/v1/docs` 加载 Redoc 3，并将 `/swagger.json` 路由至后端 API 而非前端 SPA 回退页（`77a4551e6`）。

## 2.6.0 用量扫描与存储桶管理 {#release-260}

[Console 2.6.0](/zh/blog/release/console-2.6.0/) 新增可取消的目录与存储桶用量扫描（分别显示当前字节与保留版本字节）、可选的 PostgreSQL 持久化用量后台任务、保留期/配额/复制带宽输入的精确整数范围校验、创建启用对象锁存储桶时的版本排除拦截、路由切换期间隐藏并禁用旧对象详情与版本控件（[#81](https://github.com/pgsty/silo-console/pull/81)），以及内嵌 Console 服务的三分钟 keep-alive 默认值。

## 2.5.1 管理修复 {#release-251}

仅切换用户组启用/禁用状态时保留原有成员，显式传入成员数组时仍替换成员列表；支持解析 OIDC 字符串数组格式的组声明以保留对应权限，并仅在配置了 HTTPS 或可信代理时启用安全会话标记。凭据导出保持合法的 UTF-8 JSON 格式，流式 ZIP 在写出首字节前失败时透传底层 S3 错误状态；同时修复了键盘焦点、无障碍名称与标签页滚动问题。详见[完整 2.5 发布说明](/zh/blog/release/console-2.5.1/)。

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

仪表盘组件查询 **MinIO Metrics V3** 指标目录 —— 也就是当前部署实际抓取的那一套 —— 并针对其零值语义与按节点导出的语义做了保护，使面板能区分"真实的零"与"数据缺失"。映射关系记录在 [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/metrics-v3.md)。

### 3. 更小、更安静的产物 {#payload}

内嵌前端从约 10 MB 降到 3 MB 以内，可逐字节复现构建，并由发布门禁强制校验。没有任何形式的遥测，页面本身也没有外部网络依赖。

### 4. 界面语言 {#i18n}

Console 2.7.0 通过统一菜单与命令面板提供十种界面语言：英语、简体中文、法语、德语、俄语、
西班牙语、巴西葡萄牙语、日语、阿拉伯语与土耳其语，词典全部内置，并支持阿拉伯语 RTL
（Console 2.6.0 及更早版本提供中英文界面）。英语仍是默认与回退语言；文档保持中英双语，
服务器消息和日志正文原样保留。覆盖范围与维护分层见[语言设计](/zh/blog/design/console-languages/)。

### 5. 对象列表按页操作 {#pagination}

对应 [B02](/zh/compatibility/#b02)，自 Console v2.4.0 起使用游标分页，并延续至 v2.7.0。默认每页 100 项，可选 50、100、250、500、1,000；提供首页、上一页与下一页，不提供“加载全部”或任意跳页。

**排序、名称筛选和全选只作用于当前页。** 只有首页已包含整个目录时，它们才覆盖整个目录。翻页保留筛选文本、清空选择；更换页大小回到首页，更换目录清空筛选。失败的页面保留上一页供重试。

Rewind 与“显示已删除对象”没有游标，最多返回 1,000 个版本，并有时间预算；触及限制会提示结果不完整。详见[对象浏览器契约](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/ObjectBrowser.md#paging)。

### 6. API 返回与自动化 {#api-output}

对应 [B04](/zh/compatibility/#b04)、[O05](/zh/compatibility/#o05)。会话响应增加 `accountAccessKey`，对象列表显式返回零字节对象的 `size: 0`；会话能力字段还会随有效权限变化。自制解析器应容忍新增字段，Console 自动化应处理分页、会话失效和 WebSocket 错误。

用户启用/禁用新增独立的 `PUT /api/v1/user/{name}/status`，旧 `PUT /api/v1/user/{name}` 保留但已弃用；批量下载沿用原入口，同时接受受限表单以支持原生流式 ZIP。改密权限另见[密码权限迁移](/zh/compatibility/password-permissions/)，分享下载边界见 [v2.4.1 说明](/zh/blog/release/console-2.4.1/)；定制调用以[当前 API 定义](https://github.com/pgsty/silo-console/blob/v2.7.0/swagger.yml)为准。

Console v2.4.2 保留桶版本控制操作中被包装的 S3 错误；当 Object Lock 禁止暂停版本控制时，显式返回 `InvalidBucketState`，让调用方看见 Server 已有的限制。

### 7. 面向开发者：模块图 {#source}

Console v2.7.0 要求 Go 1.27.3，直接 require `github.com/pgsty/silo-pkg/v3` v3.16.0 与上游 SDK
`v7.4.2-0.20261025165926-320af050c445`，保留历史模块路径 `github.com/minio/console`。
嵌入方显式选择以下已发布源码：

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261109114619-4e91ae506e70
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261109021353-e1d4cc5abfe0
```

Go 不继承依赖模块的 replacement，Server 必须同时选择 PGSTY Console 与 MC。
go-systemd v22.6.0 保留 NetBSD 兼容，tablewriter v0.0.5 保留 MC API 兼容。
colorjson 带入的历史 minio/pkg 传递依赖与维护中的 silo-pkg 策略实现分开；不使用旧的
`minio/pkg => silo-pkg` 或 `minio-go => silo-go` replacement。
详见[组件矩阵](/zh/compatibility/versions/)和[嵌入指南](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/Embedding.md)。

发布门禁验证配套 SILO、Console、mcli 与 pkg；上游 MinIO/MC 探针属于非阻塞兼容信号，不要求降低 pkg 版本或复制 API。

## 迁移 {#migration}

官方镜像为 [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console)。**`v2.7.0` 与 `latest` 已发布 Linux amd64/arm64 多架构镜像**（`sha256:85aeb3ce802eb4aaae33503bcb665dc72c7544db037b5cda5ffae73b26719892`），核验细节见 [v2.7.0 发布验收](/zh/blog/release/console-2.7.0/#verification)。同时提供 [GitHub 二进制与软件包](https://github.com/pgsty/silo-console/releases/tag/v2.7.0)。

镜像以 UID 1000 运行且没有主目录，默认证书目录因此是 `/.console/certs`：私有 CA 证书挂载到 `/.console/certs/CAs/`，或用 `--certs-dir` 指定其他路径。自 `v2.7.0` 起，scratch 容器镜像已内置系统 CA 证书库 `/etc/ssl/certs/ca-certificates.crt` 与权限为 `1777` 的 `/tmp` 目录，可直接访问公共 HTTPS 端点（`v2.6.0` 及更早镜像缺少上述两项，访问公共证书 HTTPS 端点时需将宿主机证书包只读挂载到 `/etc/ssl/certs/ca-certificates.crt`）。

已有的 MinIO Console 部署可以原地升级。服务单元、服务账号与配置文件名称都不变，全部 `CONSOLE_*` 变量按原样读取，因此通常的做法是用 `silo-console` 软件包覆盖安装后重启。

有两处行为会在首次启动后改变，值得提前预期：

- `silo-console` 不会自我更新。请通过软件包、镜像或编排系统来推送新版本。
- 任何依赖控制台访问 MinIO 运营服务的流程 —— 更新源、许可、遥测 —— 都不再有可访问的对端。

从早于 v2.4.1 的版本升级时，还需检查[密码权限迁移](/zh/compatibility/password-permissions/)。
Linux 软件包使用 `/etc/silo-console/certs` 作为证书目录；重启前迁移旧证书，或在
`/etc/default/console` 的 `CONSOLE_OPTS` 中保留旧路径。服务名和配置文件路径不变。
共享代理仅接受对象下载，不需要新增环境变量。详见 [v2.4.1 发布说明](/zh/blog/release/console-2.4.1/)。

## 参见 {#see-also}

- [Silo 服务器兼容性](/zh/compatibility/server/) —— 本控制台所管理的服务器
- [MCLI 客户端兼容性](/zh/compatibility/mcli/) —— 命令行客户端
- [Console 发布说明](/zh/tags/console/) 与 [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1
[v2.3.0]: https://github.com/pgsty/silo-console/releases/tag/v2.3.0
