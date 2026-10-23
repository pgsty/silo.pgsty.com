# SILO 双语文档站

[English](README.md) · [简体中文](README_ZH.md)

本仓库维护 [silo.pgsty.com](https://silo.pgsty.com/)：英文位于 `/`，简体中文位于 `/zh/`。网站使用 Hugo Extended 0.168.0 与固定在 `go.mod` 中的 OINK v1.3.2。

## 20261018 正式发布

当前正式 Server 为 `RELEASE.2026-10-18T00-00-00Z`，包版本 `20261018000000.0.0`，发行源码 `0cd388c666f8211f552604ae73448a066e9c25ce`。GitHub Release 已公开发布，公开下载与 Docker Hub 镜像于 2026-10-19 完成核验；本机制品验收的环境边界见发布说明，具体生产环境升级仍需独立验收。

| 组件 | 本批次文档 |
| --- | --- |
| Server 20261018 | [英文](content/blog/release/silo-20261018.md) · [中文](content/blog/release/silo-20261018.zh.md) |
| Console v2.4.2 | [英文](content/blog/release/console-2.4.2.md) · [中文](content/blog/release/console-2.4.2.zh.md) |
| mcli 20261018 | [英文](content/blog/release/mcli-20261018.md) · [中文](content/blog/release/mcli-20261018.zh.md) |
| pkg v3.14.2 | [英文](content/blog/release/pkg-3.14.2.md) · [中文](content/blog/release/pkg-3.14.2.zh.md) |
| pkg v3.14.3 | [英文](content/blog/release/pkg-3.14.3.md) · [中文](content/blog/release/pkg-3.14.3.zh.md) |
| 可选 KES 20261018 | [英文](content/blog/release/kes-20261018.md) · [中文](content/blog/release/kes-20261018.zh.md) |

Server 选用 Console v2.4.2、mcli 20261018、pkg v3.14.3、上游 minio-go v7.4.1；已发布的独立 Console 与 mcli 仍声明 pkg v3.14.2。KES 为独立部署的外部密钥服务，不嵌入 Server。精确源码、发布状态和升级顺序见[组件矩阵](content/compatibility/versions.zh.md)。

`data/releases.yaml` 驱动首页与下载页。`server.published: true` 启用公开制品下载链接，`published_server` 记录当前公开版本。准备后续版本时应保持 false，直到匹配的 Server 制品与 Docker 镜像公开并完成核验，同时更新两种语言的交付说明。

`windows_archive_format` 记录各组件已发布的 Windows 归档格式：Server、mcli、KES 20261018 保持 `tar.gz`，Console v2.4.2 使用 `zip`。后续发布 ZIP 版本时，核验制品后同时更新对应组件的版本与格式，不改写旧版本下载链接。Linux 与 macOS 归档继续使用 `tar.gz`。

## 本地开发与校验

使用 Hugo Extended 0.168.0、Go 1.27.2、Git 与支持 venv 的 Python 3.10+。使用 Hugo 内置 LibSass，不需要另装 Sass 编译器或 Node.js。保留可见的构建诊断；当前接受上游 LibSass 弃用警告，不启用 `--panicOnWarning`。

```bash
make dev     # 内存预览
make build   # 构建静态站点
make check   # 既有测试、Go 模块验证、Hugo 构建和内部链接检查
```

Makefile 禁用本地 Go/Hugo workspace 与主题替换，验证 `go.mod` 固定的已发布主题。构建产物不进入 Git。

## 内容与交付约定

- 同一分支维护相邻中英文页面，保留一致的章节锚点、组件版本与行为边界。
- 产品、运维、迁移、安全、设计与发布文档归本站；源码仓库保留入口和贡献说明。调查日志、私有安全材料和临时验收文件放在仓库外。
- 实质修改继承页面时设置 `upstream_modified: true`，保留 `upstream_link`。原创页面不冒用上游来源。
- 历史版本文章保留原始版本与证据范围，以带日期的补充链接说明后续变化。优先引用固定提交，避免将源码合入、制品验收和生产部署混为一谈。
- 首页 Docker Pulls 指标卡固定指向 `pgsty/minio`，其数值包含改名前后两个仓库的累计拉取量。不要把这个历史来源链接改成 `pgsty/silo`。
- 指标由 `python3 bin/metrics.py` 生成，不手工修改。发布站点前刷新指标并检查差异，再运行 `make check`。
- Cloudflare Pages 发布 `main` 分支。新 URL 先随网站发布，再发布依赖这些路径的源码仓库改动；上线后核对精确提交和中英文页面。

贡献者生成流程、完整 URL 约定、页面归属与许可细节见[英文 README](README.md)及 [AGENTS.md](AGENTS.md)。
