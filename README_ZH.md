# SILO 双语文档站

[English](README.md) · [简体中文](README_ZH.md)

本仓库维护 [silo.pgsty.com](https://silo.pgsty.com/)：英文位于 `/`，简体中文位于 `/zh/`。网站使用 Hugo Extended 0.168.0 与固定在 `go.mod` 中的 OINK v1.4.0。

## 20261026 正式发布

当前协调版本为 **SILO Server、mcli 与 KES 20261026**（`RELEASE.2026-10-26T00-00-00Z`，包版本 `20261026000000.0.0`）、**SILO Console v2.5.1** 和 **silo-pkg v3.15.2**，统一使用 Go 1.27.3。

| 发布说明 | English | 简体中文 |
| --- | --- | --- |
| Server / mcli / KES 20261026 | [Release notes](content/blog/release/silo-20261026.md) | [发布说明](content/blog/release/silo-20261026.zh.md) |
| Console 2.5 系列，含 2.5.1 | [Release notes](content/blog/release/console-2.5.1.md) | [发布说明](content/blog/release/console-2.5.1.zh.md) |
| silo-pkg 3.15 系列，含 3.15.2 | [Release notes](content/blog/release/pkg-3.15.2.md) | [发布说明](content/blog/release/pkg-3.15.2.zh.md) |

双语日志合并 10 月 24–25 日占位记录，覆盖 20261018 以来全部修改。Server 发行源码为 `c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3`，选用已发布的 Console 与 mcli 源码、pkg v3.15.2 和上游 minio-go `v7.4.2-0.20261025165926-320af050c445`。KES 是可选的外部密钥服务。精确版本与升级顺序见[组件矩阵](content/compatibility/versions.zh.md)。

磁盘超时不证明底层 I/O 已停止；正式版保留既有超时语义，不包含草稿中的 mutation guard 与所有权回滚方案。

`data/releases.yaml` 驱动首页与下载页。`server.published: true` 启用公开制品下载链接，`published_server` 记录当前公开版本。准备后续候选版本时保持 false，直到相应 Server 制品与 Docker 镜像公开且完成核验。`windows_archive_format` 跟随各组件实际发布制品：当前 Windows 归档统一为 ZIP，Linux/macOS 保持 tar.gz；历史下载链接保留原格式。制品发布与具体生产集群部署分别验收。

## 本地开发与校验

使用 Hugo Extended 0.168.0、Go 1.27.3、Git 与支持 venv 的 Python 3.10+。使用 Hugo 内置 LibSass，不需要另装 Sass 编译器或 Node.js。保留可见的构建诊断；当前接受上游 LibSass 弃用警告，不启用 `--panicOnWarning`。

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
- 首页 Docker Pulls 指标卡统一指向 [`pgsty/silo`](https://hub.docker.com/r/pgsty/silo)，其数值包含历史 `pgsty/minio` 与当前 `pgsty/silo` 两个仓库的累计拉取量。
- 指标由 `python3 bin/metrics.py` 生成，不手工修改。发布站点前刷新指标并检查差异，再运行 `make check`。
- Cloudflare Pages 发布 `main` 分支。新 URL 先随网站发布，再发布依赖这些路径的源码仓库改动；上线后核对精确提交和中英文页面。

贡献者生成流程、完整 URL 约定、页面归属与许可细节见[英文 README](README.md)及 [AGENTS.md](AGENTS.md)。
