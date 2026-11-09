---
title: "SILO Console 2.7.0：十种语言与容器可靠性修复"
linkTitle: "Console 2.7.0（发布草稿）"
date: 2026-11-09
author: "SILO"
description: "Console 2.7.0 候选版本说明：十种语言、阿拉伯语 RTL、容器修复、正式 mcli 与 silo-pkg 依赖，以及 API 文档更新。"
tags: [Release, Console]
draft: false
weight: 1
url: "/zh/blog/release/console-2.7.0/"
---

**已验证的 Draft Release，尚未公开发布。** Console 2.7.0 将管理界面扩展到十种语言，修复容器 HTTPS 与临时文件问题，
采用已正式发布的 mcli 20261109、silo-pkg 3.16.0，并更新 API 文档。
`v2.7.0` 标签对应的完整验证与发布流水线均已通过；GitHub 制品保留在 Draft Release 中，
带版本号的候选镜像已在 Docker Hub 就绪。截至 **2026-11-09**，最新正式版仍为
[2.6.0](https://github.com/pgsty/silo-console/releases/tag/v2.6.0)，`latest` 仍指向其已验证镜像。
公开发布草稿与推进 `latest` 是后续独立步骤。

[GitHub Releases](https://github.com/pgsty/silo-console/releases) ·
[2.6.0 之后的变化](https://github.com/pgsty/silo-console/compare/v2.6.0...v2.7.0) ·
[Console 兼容性](/zh/compatibility/console/)

## 一个菜单，十种语言 {#languages}

登录页、公开页面和登录后的控制台共用语言菜单，命令面板提供同样的选择：

| 语言 | 菜单名称 |
| --- | --- |
| 英语 | English |
| 简体中文 | 简体中文 |
| 法语 | Français |
| 德语 | Deutsch |
| 俄语 | Русский |
| 西班牙语 | Español |
| 巴西葡萄牙语 | Português (Brasil) |
| 日语 | 日本語 |
| 阿拉伯语 | العربية |
| 土耳其语 | Türkçe |
{.wide .expand}

英语仍是默认与回退语言。Console 记住用户的显式选择，不按浏览器设置自动切换。
已有的 `en`、`zh` 偏好继续有效，早期的 `pt` 值映射到 `pt-BR`，未知值回退到英文。

全部词典随前端内置。应用加载后，切换语言无需下载翻译，离线时也能完成，并保留表单中尚未保存的内容。
代价是首次下载增加：九种译文词典分别压缩，合计约 **568 KB gzip**，随应用全量加载。
带内容哈希的资源使用一年 immutable 缓存，HTML 每次重新验证；修改一种语言不会使其他词典缓存失效。
运行时不需要在线翻译服务、额外字体或新的国际化框架。

中文继续由核心团队维护完整覆盖，其他语言缺失的条目回退到英文。
新增词典包含 AI 辅助初稿；条目完整并不意味着已经通过母语审校。
欢迎通过 [Console PR](https://github.com/pgsty/silo-console/pulls) 提交翻译修正。

巴西葡萄牙语由 **[@EduardoAndradeMachado](https://github.com/EduardoAndradeMachado)** 在
[PR #83](https://github.com/pgsty/silo-console/pull/83) 中贡献，原始作者提交完整保留。
后续十语言实现将葡萄牙语专用的异步加载器替换为统一的静态词典。

## 本地化格式与阿拉伯语布局 {#rtl}

日期、数字和数量标签按所选语言显示，支持俄语、阿拉伯语所需的多种复数形式。
阿拉伯语还支持从右向左的导航、间距、方向控件、移动抽屉与标签页键盘导航。

对象路径、桶名、ARN、策略 JSON 和原始 Trace／日志数据保持从左向右。
对象名、服务器错误、审计事件和日志正文原样保留；语言选择不翻译存储数据或服务端输出。
产品文档仍为中英双语：中文界面打开中文文档，其余语言打开英文文档。

[实现提交](https://github.com/pgsty/silo-console/commit/51a735992b63593046453d997e7a18584bae2336)
补充词典校验及浏览器覆盖，检查键盘选择、偏好保存、离线切换、未保存表单与 RTL 行为。
中文覆盖率、占位符和复数形式继续接受校验。
[内嵌 GUI 重建](https://github.com/pgsty/silo-console/commit/0059ee2d979e8406f3018766584337c92d5e55fa)
与源码变更分别记录。

## 容器 HTTPS 与大型请求 {#containers}

此前截至 2.6.0 的 Console 镜像使用精简的 `scratch` 文件系统，缺少系统 CA 根证书与 `/tmp`。
未自行挂载证书包时，连接使用公开证书的 SILO Server 或 OIDC 提供方可能报
`x509: certificate signed by unknown authority`；需要落盘的 multipart 请求也可能因临时目录不存在而失败。

[PR #84](https://github.com/pgsty/silo-console/pull/84) 修复了三条镜像构建路径：

- 将系统 CA 证书包放在 `/etc/ssl/certs/ca-certificates.crt`，沿用 SILO 与 mcli 镜像的 UBI 信任库准备方式。
- 提供权限为 `1777` 的 `/tmp`，供大型 multipart 请求写入临时文件。使用只读容器文件系统时，仍需为该路径挂载可写目录或 tmpfs。
- 保留精简镜像、非 root 的 `1000:1000` 运行身份、既有证书配置和启动入口；发布镜像校验新增 CA 证书包与临时目录权限检查。

公开证书可直接使用系统信任，无需关闭 TLS 校验。私有 CA 仍需显式配置；
已有的系统证书包挂载继续覆盖镜像中的证书包。
官方镜像仍位于 Docker Hub 的 **`docker.io/pgsty/silo-console`**；已验证的候选镜像使用 `v2.7.0` 标签，`latest` 保持不变。

## 升级与依赖边界 {#upgrade}

目录和存储桶用量扫描、保留版本统计、新鲜度提示，以及可选的 PostgreSQL 用量后台任务，
已随 [2.6.0](/zh/blog/release/console-2.6.0/) 发布，2.7.0 继续保留。
只有可选用量后台任务需要 PostgreSQL；语言和容器变化不引入这一要求。

候选版本采用 [PR #86](https://github.com/pgsty/silo-console/pull/86) 已验证的正式组件：

| 组件 | 已核对的源码选择 |
| --- | --- |
| Go | 1.27.3 |
| Node / Yarn | 24.22.1 / 4.13.0 |
| `github.com/pgsty/silo-pkg/v3` | v3.16.0，提交 `b7aeea85e84e8888d6ab424c7123a1297711bc3f` |
| 维护的 MC 源码 | mcli 20261109，提交 `e1d4cc5abfe00b674eb36347399e7398990be467` |
| 上游 `github.com/minio/minio-go/v7` | `v7.4.2-0.20261025165926-320af050c445` |
| go-swagger / runtime / server-middleware | v0.36.7 / v0.33.4 / v0.33.4 |
| `golang.org/x/net` | v0.62.0 |
| `golang.org/x/crypto` | `v0.58.1-0.20261009181718-2f1f834330b2` |
{.wide .expand}

[mcli 20261109](/zh/blog/release/mcli-20261109/) 的标签
`RELEASE.2026-11-09T00-00-00Z` 不是 Go SemVer，因此 replacement 使用
`github.com/pgsty/mc v0.0.0-20261109021353-e1d4cc5abfe0` 表示准确的正式发布提交，
并保留 `github.com/minio/mc` 导入路径。这不是发布前快照。
[silo-pkg 3.16.0](/zh/blog/release/pkg-3.16.0/) 使用普通模块标签。
`hack/deps-release.json` 记录两种发布形式与完整 SHA，并经公开 Go proxy、校验和数据库和 go.sum 一致性核验。

这些组件带入 cpuid v2.4.2、YAML v3.0.6 和 gjson v1.20.1；pretty 保持 v1.2.2，避免格式化输出变化。
模块图还采用 go-jose v4.1.9，但独立 Console 的包依赖集合没有 JOSE，因此不宣称修复了该程序的可达 JOSE 漏洞。
既有 tablewriter、runewidth、go-systemd replace 和已验证的 pgx/puddle 版本继续保留。

SILO Server 20261026 内嵌 Console 2.5.1。升级独立 Console 不会替换内嵌前端，也不会补充新的服务端 API。
嵌入方需选择相应 Console 源码并复制其维护的 MC replacement；Go 不会继承依赖模块的 replacement。
正式支持的管理目标仍是 **pgsty/silo**，对未经修改的上游 MinIO 尽最大努力兼容。

[PR #85](https://github.com/pgsty/silo-console/pull/85) 移除了过时的上游 MinIO 构建任务，
保留维护的 SILO 验收矩阵、作为参考的上游 MC 兼容性探针，以及前端与容器资源一致性检查。
准确标签提交及其独立发布制品验收结果见下文。

## API 文档与校验 {#api-docs}

Swagger v0.36.7 修复数组上下文校验遇到零值元素就提前结束的问题。
重新生成时保留定制 server、配置导入绑定、API schema 和 TypeScript 客户端。
当前 schema 没有 `readOnly` 约束，因此没有引入新的上下文请求限制。

默认 `/api/v1/docs` 页面改为以 ES module 加载 Redoc 3；`/swagger.json` 请求现在到达 API，
不再被前端 SPA 回退页面拦截。代码生成可重复，请求绑定与文档路由有直接回归测试。
必需矩阵还针对真实 SILO 检验 MC 适配层的版本读取、删除标记、精确键删除边界、错误传播、watch 取消、生命周期与诊断行为。

CI 使用明确的权限和平台矩阵，从项目版本文件读取工具链版本，移除自动重试与重复配置，保留维护的集成和制品检查。
观察者续期测试使用生产默认参数，并按数据库租约状态同步。

## 贡献者 {#contributors}

截至 2026-11-09，Console 已核对全部 **42 个 Issue 与 44 个 PR**，记录 **6 位人类贡献者**。
提交 Issue 或 PR 即认可为贡献，不以合并为前提；继承的上游作者署名继续保留在 Git 历史与版权声明中。

- **[@Vonng](https://github.com/Vonng)**：项目维护、问题修复、多语言集成、测试、发行与文档。
- **[@cyberbret](https://github.com/cyberbret)**：在
  [#70](https://github.com/pgsty/silo-console/pull/70) 中贡献目录与存储桶用量扫描及可选持久化后台任务；经后续修复合入，已随 2.6.0 发布。
- **[@EduardoAndradeMachado](https://github.com/EduardoAndradeMachado)**：在
  [#83](https://github.com/pgsty/silo-console/pull/83) 中贡献巴西葡萄牙语翻译，推动了本版本的多语言扩展。
- **[@kh0mka](https://github.com/kh0mka)**：在
  [#72](https://github.com/pgsty/silo-console/issues/72) 中报告建桶配额丢失，通过 #74 修复，已包含在 2.6.0 中。
- **[@jiri-pejchal](https://github.com/jiri-pejchal)**：在
  [#52](https://github.com/pgsty/silo-console/issues/52) 中报告分享代理暴露内部指标，已在 2.4.1 修复。
- **[@azataiot](https://github.com/azataiot)**：在
  [#63](https://github.com/pgsty/silo-console/issues/63) 中报告并分析高延迟下健康报告截断，已在 2.5.0 修复。

实际 PR 状态与历史贡献见[社区贡献记录](/zh/about/contributors/)。

## 草稿验收与准确源码 {#verification}

标签 [`v2.7.0`](https://github.com/pgsty/silo-console/tree/v2.7.0) 指向
[`26ce922424f18424ca64389632b74685b8c82752`](https://github.com/pgsty/silo-console/commit/26ce922424f18424ca64389632b74685b8c82752)。
以下检查均验收这一准确提交：

- [Required matrix：38/38 项](https://github.com/pgsty/silo-console/actions/runs/42571555305)，覆盖维护中的 SILO 集成、权限矩阵、SSO、复制、分享下载、PostgreSQL 用量、Swagger 生成、跨平台构建、软件包生命周期与独立制品复现。Playwright 通过 886 项回归测试及另 8 项分组检查。
- [Required vulnerability checks：3/3 项](https://github.com/pgsty/silo-console/actions/runs/42571555292)。
- [标签发布流水线](https://github.com/pgsty/silo-console/actions/runs/42574599791)：草稿制品、校验和与镜像签名、SPDX 声明和 GitHub 来源证明均已验证。

制品任务曾因 GitHub 下载 Syft 校验文件时返回 HTTP 504 而重跑；源码与验证要求保持不变。

草稿包含 **44 个制品**：六个平台的独立可执行文件、六个压缩包、九个 Linux 软件包、
源码包、17 份 SPDX SBOM、法律文件、SHA-256 清单及其 Sigstore 签名包。
校验和清单覆盖 38 个载荷文件。GitHub 草稿制品在公开发布前仅对维护者可见，
公开下载链接继续使用 2.6.0。验证命令见
[该标签的发布契约](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/release-contract.md)。

多平台候选镜像为 `docker.io/pgsty/silo-console:v2.7.0`，支持 Linux amd64 与 arm64，不可变摘要为：

```text
sha256:a7f3e3f326fa992895cba23a216e44689592666dfb070306e2ab058c0b27acc5
```

`latest` 摘要仍为
`sha256:49b297b1ecc6252e2fe95ee641f96b165eaf92db8394872462562d3e90e67608`。
草稿已具备供维护者公开发布的条件，本次尚未公开发布，也未推进 `latest`。
