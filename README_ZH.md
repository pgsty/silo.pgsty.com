# SILO 双语文档站

[English](README.md) · [简体中文](README_ZH.md)

本仓库维护 [silo.pgsty.com](https://silo.pgsty.com/)：英文位于 `/`，简体中文位于 `/zh/`。网站使用 Hugo Extended 0.168.0 与固定在 `go.mod` 中的 OINK v1.5.1。

## 当前版本

当前版本为 **SILO Server 与 mcli 20261109**、**SILO Console v2.7.0**、**silo-pkg v3.16.0** 与 **KES 20261026**，均使用 Go 1.27.3。Server 20261109 内嵌 Console 2.7.0、mcli 20261109 与 pkg v3.16.0；KES 保持独立、可选的外部密钥服务。

| 发布说明                      | English                                                | 简体中文                                             |
| ----------------------------- | ------------------------------------------------------ | ---------------------------------------------------- |
| Server 20261109               | [Release notes](content/blog/release/silo-20261109.md) | [发布说明](content/blog/release/silo-20261109.zh.md) |
| Console 2.7.0                 | [Release notes](content/blog/release/console-2.7.0.md) | [发布说明](content/blog/release/console-2.7.0.zh.md) |
| Console 2.6.0                 | [Release notes](content/blog/release/console-2.6.0.md) | [发布说明](content/blog/release/console-2.6.0.zh.md) |
| mcli 20261109                 | [Release notes](content/blog/release/mcli-20261109.md) | [发布说明](content/blog/release/mcli-20261109.zh.md) |
| silo-pkg 3.16.0               | [Release notes](content/blog/release/pkg-3.16.0.md)    | [发布说明](content/blog/release/pkg-3.16.0.zh.md)    |
| Server / mcli / KES 20261026  | [Release notes](content/blog/release/silo-20261026.md) | [发布说明](content/blog/release/silo-20261026.zh.md) |
| Console 2.5 系列，含 2.5.1    | [Release notes](content/blog/release/console-2.5.1.md) | [发布说明](content/blog/release/console-2.5.1.zh.md) |
| silo-pkg 3.15 系列，含 3.15.2 | [Release notes](content/blog/release/pkg-3.15.2.md)    | [发布说明](content/blog/release/pkg-3.15.2.zh.md)    |

精确源码版本、升级顺序与兼容性边界见[组件矩阵](content/compatibility/versions.zh.md)。

Server 20261109 交付生命周期、恢复、Object Lock 与批处理授权修复。混合版本或回退 batch 作业前，请先阅读升级说明。Console 2.7.0 已独立发布，也内嵌于本次 Server；旧 Server 二进制仍保留各自原有的界面与依赖。

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

### 贡献者记录

`data/home/contributors.yaml` 中经核对的名单驱动首页展示，并生成中英文贡献者页面、五个软件仓库（Server、Console、mcli、silo-pkg 与 KES）的 `CONTRIBUTORS.md` 及其 README 章节。包含处于任意状态的所有人类 issue / PR 作者；保留公开致谢的安全披露者，并区分被后续修复采纳的方案与原 PR 的合并状态。

先拉取数据文件中所列仓库的完整分页 GitHub 记录（`gh api --paginate --slurp 'repos/pgsty/REPO/issues?state=all&per_page=100'`），统一核对描述、采纳证据、账号去重、机器人排除、状态列表、仓库总计、排序与核对日期，随后在存在同级软件仓库检出且安装了 PyYAML 的环境中执行：

```bash
python3 bin/contributors.py
python3 bin/contributor_avatars.py
python3 bin/contributors.py --check
make check
```

若同级仓库位于其他路径，可传入 `--workspace /path/to/checkouts`。涉及新公开页面或头像 URL 时，先发布文档站，再发布引用这些公开 URL 的源码仓库改动。

### 双语目录与归属约定

英文为默认语言，相邻维护中英文文件：

```text
content/operations/concepts/_index.md
content/operations/concepts/_index.zh.md
```

产品首页位于 `/`，文档总览位于 `/docs/`，迁移内容树保留既有的 MinIO 文档 URL 结构：

```text
/
├── operations/
├── administration/
├── developers/
├── reference/
├── integrations/
└── glossary/
```

- 同一分支维护相邻中英文页面，保留一致的章节锚点、组件版本与行为边界。
- 产品、运维、迁移、安全、设计与发布文档归本站；源码仓库保留入口和贡献说明。调查日志、私有安全材料和临时验收文件放在仓库外。
- 实质修改继承页面时在 Front Matter 中设置 `upstream_modified: true`，并保留 `upstream_link`：

```yaml
upstream_link: https://github.com/minio/docs # 页面衍生自的上游素材
upstream_modified: true # 超出格式转换范围的实质修改设为 true
```

- 原创页面（博客、下载与发布页、SILO 专属内容）不声明上游来源；若所在目录通过 cascade 继承了上游字段，使用 `upstream_link: ""` 显式退出。
- 历史版本文章保留原始版本与证据范围，以带日期的补充链接说明后续变化。优先引用固定提交，避免将源码合入、制品验收和生产部署混为一谈。
- 首页 Docker Pulls 指标卡统一指向 [`pgsty/silo`](https://hub.docker.com/r/pgsty/silo)，其数值包含历史 `pgsty/minio` 与当前 `pgsty/silo` 两个仓库的累计拉取量。
- 指标由 `python3 bin/metrics.py` 生成，不手工修改。发布站点前刷新指标并检查差异，再运行 `make check`。
- Cloudflare Pages 发布 `main` 分支。新 URL 先随网站发布，再发布依赖这些路径的源码仓库改动；上线后核对精确提交和中英文页面。

## 署名与许可

本站全部文档内容按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.zh) 授权，部分内容衍生自 [MinIO Object Storage Documentation](https://github.com/minio/docs)（© 2020–Present MinIO, Inc.）并作修改。详见 [LICENSE](LICENSE)、[NOTICE.md](NOTICE.md)、[英文 README](README.md) 及 [AGENTS.md](AGENTS.md)。面向读者的说明发布在 [/zh/about/](https://silo.pgsty.com/zh/about/)：

| 页面                                                                   | 内容                                   |
| :--------------------------------------------------------------------- | :------------------------------------- |
| [/zh/about/license/](https://silo.pgsty.com/zh/about/license/)         | 软件采用 AGPLv3，文档采用 CC BY 4.0    |
| [/zh/about/trademark/](https://silo.pgsty.com/zh/about/trademark/)     | MinIO 名称的使用方式与非关联声明       |
| [/zh/about/attribution/](https://silo.pgsty.com/zh/about/attribution/) | 版权层次、衍生关系、翻译声明与署名格式 |
| [/zh/about/security/](https://silo.pgsty.com/zh/about/security/)       | 漏洞报告方式与安全修复发布渠道         |
