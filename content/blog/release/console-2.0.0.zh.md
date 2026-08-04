---
title: "SILO Console 2.0.0 发布"
linkTitle: "silo-console 2.0.0 发布"
date: 2026-08-03
author: "冯若航"
description: "SILO Console 完成独立品牌、仓库与发布链路迁移，同时保留 Go 模块、环境变量、管理接口与 systemd 服务名等兼容契约。"
tags: [发布, console]
weight: 4
url: "/zh/blog/release/console-2.0.0/"
aliases:
  - /blog/console-2.0.0/
  - /releases/console-2.0.0/
---
**发布日期：** 2026-08-03 · **版本：** [v2.0.0](https://github.com/pgsty/silo-console/releases/tag/v2.0.0) · **仓库：** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.0.0 是这套对象存储管理控制台以独立项目身份发布的第一个主版本。它从 `georgmangold/console` 的 v1.9.1 维护线继续演进，正式建立 **SILO Console** 的产品名称、视觉系统、文档入口、源码归属和发布链路。

这次升级不只是替换 Logo。用户可见界面、帮助内容、授权与来源说明、命令行元数据、二进制与容器名称、软件包及发布资产都已经纳入 SILO 项目体系；与此同时，Go 模块路径、既有环境变量、协议字段和部分安装标识被有意保留，以避免一次品牌迁移演变成没有必要的接口破坏。

{{% alert color="warning" %}}
**升级前先看兼容边界**

2.0.0 的主版本变化发生在**公共身份和交付契约**上，而不是对象数据格式或 S3 协议上。使用旧仓库、旧发布二进制名或旧容器镜像名的安装脚本必须更新；使用 `CONSOLE_MINIO_SERVER`、`CONSOLE_MINIO_REGION`、`github.com/minio/console` 或 MinIO-compatible Admin API 的现有集成则不应做全局替换。
{{% /alert %}}

## 为什么是 2.0.0 {#why-2-0-0}

这套控制台最初源自 MinIO Console，随后由 [Alevsk/console](https://github.com/Alevsk/console) 与 [georgmangold/console](https://github.com/georgmangold/console) 两条社区维护线继续发展。SILO Console 在此基础上由 Pigsty 社区接续维护，为 [SILO](https://silo.pgsty.com/) 提供浏览器管理界面。

版本号从 v1.9.1 提升到 v2.0.0，主要是因为以下对外契约同时发生变化：

- 产品名称从通用的 Console/旧品牌表述统一为 **SILO Console**；
- 主仓库迁移到 [`pgsty/silo-console`](https://github.com/pgsty/silo-console)；
- 正式发布二进制从 `console` 改为 `silo-console`；
- 容器镜像迁移到 `ghcr.io/pgsty/silo-console`；
- 发布资产、校验和、软件包元数据、命令行说明与项目链接全部切换到 SILO；
- 界面中的项目身份、帮助入口、版权归属、源代码供应与商标说明重新建立。

这足以构成一个需要运维人员明确感知的主版本升级，但并不意味着对底层兼容接口进行一次机械式改名。2.0.0 采取的是“对外身份清晰、对内兼容克制”的迁移策略。

## 名称与交付契约 {#naming-and-delivery}

本版本的主要名称映射如下：

| 范围             | 旧名称或旧位置                           | 2.0.0 契约                                  |
|:---------------|:----------------------------------|:------------------------------------------|
| 产品             | Console / MinIO Console 的遗留表述     | **SILO Console**                          |
| 源码仓库           | `georgmangold/console`            | `pgsty/silo-console`                      |
| GoReleaser 项目名 | `console`                         | `silo-console`                            |
| 正式二进制          | `console`                         | `silo-console`                            |
| 容器镜像           | `ghcr.io/georgmangold/console`    | `ghcr.io/pgsty/silo-console`              |
| 二进制资产          | `console-<os>-<arch>`             | `silo-console-<os>-<arch>`                |
| 校验和文件          | `console_<version>_checksums.txt` | `silo-console_<version>_checksums.txt`    |
| 网站与文档          | 上游或前维护者入口                         | `silo.pgsty.com` 与 `silo.pgsty.com/docs/` |

命令行程序的作者、用途、帮助文本和项目描述也已经切换为 Pigsty 与 SILO Console。发行版中的可执行文件安装到 `/usr/local/bin/silo-console`，DEB/RPM 的厂商、维护者、主页、描述和许可证元数据相应更新。

## 刻意保留的兼容标识 {#retained-compatibility-contracts}

以下名称虽然包含 `minio` 或沿用旧的 `console`，但它们是接口、协议或安装兼容层的一部分，不属于遗漏的品牌文本：

| 兼容面             | 2.0.0 中的状态                                 | 原因                      |
|:----------------|:-------------------------------------------|:------------------------|
| Go 模块           | 保持 `github.com/minio/console`              | 改动会破坏全部 Go import 与生成代码 |
| 服务端地址           | 保持 `CONSOLE_MINIO_SERVER`                  | 现有部署广泛使用的环境变量           |
| 服务端区域           | 保持 `CONSOLE_MINIO_REGION`                  | 现有部署兼容契约                |
| 其他配置            | 既有 `CONSOLE_*` 变量继续有效                      | 避免无收益的配置迁移              |
| S3/Admin API 名称 | 保留 MinIO-compatible 字段与枚举                  | 它们描述实际协议和 SDK 接口        |
| 源码开发产物          | `make console` 仍生成 `./console`             | 保持开发工作流和脚本兼容            |
| 软件包 systemd 单元  | 保持 `minio-console.service`                 | 避免升级时出现两个服务或丢失原服务状态     |
| systemd 用户与配置   | 保持 `console-user` 与 `/etc/default/console` | 避免不必要的账户和配置文件迁移         |

因此，升级脚本不能简单执行全仓库或全配置的 `minio → silo`、`console → silo-console` 替换。未来若要迁移这些兼容接口，需要提供别名、弃用周期和明确的双读策略；2.0.0 不做这件事。

## 视觉与界面重塑 {#visual-rebranding}

2.0.0 引入了统一的 SILO 徽标与字标组件，并把品牌重塑覆盖到控制台的完整用户旅程：

- 登录页与 OIDC 回调页采用 SILO 视觉和社区项目说明；
- 浏览器标题、页面描述、favicon、Apple Touch Icon、Android Icon、Web App Manifest 与 Safari Pinned Tab 全部更新；
- 侧边栏、折叠菜单、加载状态、错误页、健康检查、性能测试和许可证页面使用统一的 SILO 标识；
- 桶、对象、生命周期、复制、通知、存储分层、用户、策略、身份源、KMS、日志、诊断等界面的产品文案完成审阅；
- 深色主题、窄屏布局和侧边栏折叠状态下的品牌呈现同步调整。

这里的原则是只替换“产品是谁”的表达，不改写真正描述协议、配置或上游兼容性的技术名词。例如，MinIO-compatible Admin API、`minio` 类型枚举和继承代码中的 import path 仍然保留。

## 帮助、文档与社区入口 {#help-and-community}

控制台内置帮助系统已经从旧项目入口迁移到 SILO 内容体系：

- 文档按钮、菜单链接和各功能页帮助链接统一指向 [SILO 文档](https://silo.pgsty.com/docs/)；
- 帮助面板新增 SILO Blog 内容，从站点 RSS Feed 读取最新文章，并在网络不可用时使用本地回退内容；
- Feed 中的跳转链接只接受 `https://silo.pgsty.com`，避免远端内容把用户导向未经声明的地址；
- 视频页暂时保留对功能仍有参考价值的上游 MinIO 视频，并明确标注为上游兼容性资料；
- 帮助面板的宽度与侧边栏状态联动，改善窄屏和折叠菜单下的阅读体验。

SILO Console 不是通用 S3 文件浏览器。桶和对象操作使用 S3 API，但集群配置、用户与策略、复制、健康检查、日志、诊断等管理功能还依赖 SILO 实现的 MinIO-compatible Admin API。

## 授权、来源与商标说明 {#license-attribution-trademark}

2.0.0 将授权与来源信息从附带文本提升为产品界面中的一等内容。许可证页面现在集中说明：

- SILO 服务端、客户端与 Console 均采用 AGPLv3；SILO Console 的 SPDX 口径为 `AGPL-3.0-or-later`；
- 当前运行版本的 Console 源代码地址，以及 SILO 服务端、客户端、上游 MinIO 和前维护分支的来源关系；
- AGPL 第 13 节下，网络用户获取对应源代码的权利；
- SILO 贡献者、MinIO, Inc. 与历代 Console 维护者各自保留的版权；
- 仓库中的 [`NOTICE`](https://github.com/pgsty/silo-console/blob/main/NOTICE) 与 [`CREDITS`](https://github.com/pgsty/silo-console/blob/main/CREDITS)；
- MinIO 商标只用于说明代码来源和兼容性，SILO 与 SILO Console 并非 MinIO, Inc. 的产品，也未得到其关联、赞助或背书。

现有源文件中的上游版权头、依赖路径和归属声明被保留。这些内容是许可证合规与历史来源的一部分，不是需要清除的旧品牌残留。

## 发布产物与平台矩阵 {#release-artifacts}

2.0.0 重新建立了 GoReleaser 交付配置。正式发布提供以下独立二进制：

| 操作系统    | 架构                    |
|:--------|:----------------------|
| Linux   | `amd64`、`arm64`、`arm` |
| macOS   | `amd64`、`arm64`       |
| Windows | `amd64`               |

Linux 同时生成 DEB 与 RPM 软件包；发布流水线将容器镜像推送到 `ghcr.io/pgsty/silo-console`，支持 `linux/amd64` 与 `linux/arm64`。OCI 镜像标签中记录项目名称、版本、提交、源码地址、厂商和 `AGPL-3.0-or-later` 许可证信息。发布核验时，镜像已经上传，但 `pgsty` 组织当前禁用了公开包可见性，因此匿名拉取仍不可用；这不影响 GitHub Release 中的二进制、校验和与 DEB/RPM 软件包。

发布二进制统一使用 `silo-console-<os>-<arch>` 命名，Windows 资产带 `.exe` 后缀，校验和文件使用 `silo-console_<version>_checksums.txt`。这套命名是 2.0.0 起供安装脚本和镜像编排使用的公开契约。

## 更新检查与默认网络行为 {#updates-and-network-behavior}

本版本对升级和版本目录功能采取更保守的默认策略：

- `silo-console update` 的实现暂时保留，但自动自更新被禁用；命令只给出提示，不会下载或替换当前二进制；
- 运行者应通过 GitHub Release、DEB/RPM 或容器镜像执行显式升级，并自行保留回滚版本；
- 版本目录新增 `SILO_RELEASE_SERVICE_HOST` 配置；原有 `RELEASE_SERVICE_HOST` 作为兼容回退继续有效；
- 两个变量都未设置时，不再连接预置的远端版本服务，而是返回空目录；
- 显式配置目录服务时，地址尾部斜杠会被规范化后再访问 `/releases`。

自动更新会在发布资产命名、校验、签名和回滚链路稳定后再重新评估。在此之前，禁用隐式下载比保留一个尚未重新建立信任链的更新通道更符合生产环境预期。

## 前端构建与工程整理 {#frontend-and-engineering}

本轮同时重新生成了由 Go 后端嵌入的生产前端。仓库中旧的 CRA 风格 `asset-manifest/static` 构建结果被 Vite 的 `assets` 布局取代，因此提交中出现了大量带哈希静态文件的删除与新增；这主要是构建产物布局变化，并不代表数百个彼此独立的功能改写。

其他值得记录的工程调整包括：

- 开发代理为 `/api` 启用 WebSocket 转发，保证本地开发与预览中的实时连接可用；
- 移除不再使用的 `tinycolor2` 依赖并收敛锁文件；
- 更新 Swagger 示例中的外部 OAuth 占位地址，避免继续引用旧品牌域名；
- 将配置帮助链接切换到 SILO 文档；
- 补充版本目录、禁用自动更新与发布资产命名相关的测试；
- 将访问拒绝场景的测试期望与实际 HTTP `403` 语义对齐。

完整重塑提交共涉及 413 个文件，其中 382 个位于 `web-app`；大部分文件数量来自前端品牌资源和重新生成的静态构建产物。

## 升级指南 {#upgrade-guide}

### 独立二进制 {#upgrade-binary}

将安装脚本和服务启动命令中的正式可执行文件改为 `silo-console`。例如 Linux amd64：

```bash
install -m 0755 silo-console-linux-amd64 /usr/local/bin/silo-console
/usr/local/bin/silo-console server
```

从源码构建时，`make console` 仍然生成 `./console`；用于正式 systemd 服务前，应按发布名称安装：

```bash
make console
install -m 0755 ./console /usr/local/bin/silo-console
```

### DEB/RPM 与 systemd {#upgrade-packages}

软件包继续安装 `/etc/systemd/system/minio-console.service`，但单元内部启动 `/usr/local/bin/silo-console`。`EnvironmentFile=/etc/default/console`、`console-user` 和既有 `CONSOLE_*` 变量不变。

这个保留是为了让软件包升级继续作用于原有服务，而不是在同一台机器上平行创建一个新服务。手工安装仓库中的 `systemd/console.service` 时，服务名则是 `console.service`；请区分软件包升级与手工部署，不要同时启用两个单元。

### 容器 {#upgrade-container}

将镜像引用切换为：

```bash
docker pull ghcr.io/pgsty/silo-console:v2.0.0
```

原有端口、挂载和 `CONSOLE_*` 环境变量可以继续使用。请在自己的编排系统中固定明确版本，不要把 `latest` 当作可回滚的版本标识。

### 配置与集成 {#upgrade-configuration}

- 不要重命名 `CONSOLE_MINIO_SERVER` 或 `CONSOLE_MINIO_REGION`；
- 不要修改 Go import 中的 `github.com/minio/console`；
- 若使用自建版本目录，优先迁移到 `SILO_RELEASE_SERVICE_HOST`，旧的 `RELEASE_SERVICE_HOST` 仍可用；
- 若脚本依赖 `console update`，改为显式下载、校验并部署发布资产；
- 若监控或资产清单按进程路径识别服务，更新为 `/usr/local/bin/silo-console`；
- 若镜像策略按仓库白名单放行，加入 `ghcr.io/pgsty/silo-console`。

本版本不改变对象数据布局，也不要求对存储桶和对象执行迁移。控制台连接的服务端仍需提供相应的 S3 与 MinIO-compatible Admin API。

## 验证范围 {#validation}

本轮变更在当前提交上完成了以下本地验证：

- Go 单元测试、格式检查和 `golangci-lint`；
- TypeScript 类型检查、Vite 生产构建、Prettier 与未使用代码检查；
- GoReleaser 配置检查与跨平台 snapshot 构建；
- Linux DEB/RPM 的二进制路径、systemd 单元与配置文件引用检查；
- 登录、对象浏览、帮助文档、Blog、视频说明、许可证页面、深色主题、窄屏与折叠菜单的浏览器检查；
- SILO 帮助链接及页内锚点检查。

这些验证说明源码与本地发布产物能够按新的命名和打包契约构建和运行。`v2.0.0` 标签、GitHub Release、13 个上传资产、校验和文件以及资产摘要已经完成远端核验；多架构容器镜像也已由发布流水线成功推送。GHCR 的公开匿名拉取仍受上述组织可见性策略限制。

## 已知限制 {#known-limitations}

- 自动自更新暂时禁用，升级需要由运维人员显式执行；
- 默认不配置远端版本目录，因此相关列表可能为空；
- 2.0.0 容器镜像已经上传，但在 `pgsty` 组织允许公开包并将该包切换为 Public 前，匿名拉取不可用；
- SILO 尚未维护独立的视频资料库，帮助面板中的视频是明确标注的上游兼容性资料；
- 管理能力依赖 MinIO-compatible Admin API，不能把 SILO Console 当作适用于任意 S3 服务的通用浏览器；
- 保留的 Go 模块、环境变量、协议字段和 systemd 服务名仍会在代码、配置和进程管理界面中出现。

## 关联提交与链接 {#related-links}

- [`8a0e348`](https://github.com/pgsty/silo-console/commit/8a0e348729c818287aab2476a3a659d50b4b1317)：rebrand console as SILO Console
- [SILO Console 源代码](https://github.com/pgsty/silo-console)
- [SILO Console Releases](https://github.com/pgsty/silo-console/releases)
- [SILO 网站](https://silo.pgsty.com/zh/)
- [SILO 文档](https://silo.pgsty.com/zh/docs/)
- [授权说明](https://silo.pgsty.com/zh/about/license/)
- [来源归属](https://silo.pgsty.com/zh/about/attribution/)
- [商标说明](https://silo.pgsty.com/zh/about/trademark/)
