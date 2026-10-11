# AGENTS.md

silo.pgsty.com —— SILO 官网（Hugo）。给 AI agent 的项目约定，改动前先读这里。

## 硬性约定（不要“顺手修正”）

### Docker Pulls 卡片必须指向 `pgsty/minio`

首页 Key Metrics 里的 Docker Pulls 卡片（`layouts/index.html`，`.stats-grid` 第一张）
链接固定为 `https://hub.docker.com/r/pgsty/minio`，**不要改成 `pgsty/silo`**。

原因：Docker Hub 改名不迁移拉取计数。绝大部分历史下载量沉淀在改名前的
`pgsty/minio` 仓库上，那才是能佐证这个数字的页面。卡片上显示的数值是
`pgsty/minio` + `pgsty/silo` 两个仓库的合计，由 `bin/metrics.py` 采集写入
`data/home/metrics.yaml`。

看到它指向 `pgsty/silo` 时，那是回归，改回 `pgsty/minio`。

## 容器分发

SILO 官方容器镜像统一使用 Docker Hub：`docker.io/pgsty/silo`、
`docker.io/pgsty/mc`、`docker.io/pgsty/silo-console`。发布说明、安装命令与链接
统一指向 Docker Hub。

## 兼容性与依赖口径

保留 SILO、SILO Console、mcli 与上游 MinIO/MC 的兼容性说明，兼容目标是
“尽最大努力”，不是保证每个未修改的上游版本都通过 SILO 发布门禁。正式支持
和发布验收的组合是 `pgsty/silo` + `pgsty/silo-console` + `pgsty/mc` +
`pgsty/silo-pkg`。

文档应明确：维护源码优先直接使用 `github.com/pgsty/silo-pkg/v3`；不得为了
上游源码图降级或绕开 SILO 自有包。`github.com/minio/minio-go/v7` 是明确例外，
继续使用经过验证的上游版本。源码谱系、历史 import path、`MINIO_*`/`MC_*`
变量或协议字段不等同于对原厂 MinIO 的强支持承诺。

## 其它

- 本仓库承载 SILO 的正式用户文档、迁移指南、安全公告、设计与发布说明；服务端源码仓库链接到本站。
  调查计划、会话摘录、执行日志和私有安全材料保存在两个仓库之外，不能原样作为站点内容提交。
- 文案改动在同一分支同时维护相邻的中英文件，例如 `content/_index.md` 与 `content/_index.zh.md`。
- 更新继承页面的实质内容时设置 `upstream_modified: true`，并保留其 `upstream_link`。
- 提交前跑 `make check`，验证严格构建与内部链接；跨仓库迁移还要检查源码仓库指向本站的路径和锚点。
  新路由先随站点发布，再发布依赖它们的源码删除与链接改动。
- `static/css/*` 靠 md5 query string 破缓存，
  不需要手动改版本号。
- 指标数据别手写，跑 `bin/metrics.py`。
- 通用文档壳、搜索、短代码和 blocks 来自 `github.com/pgsty/oink`；不要把 OINK
  模板重新复制回项目。这里只保留 SILO 首页、下载页、来源声明等产品专属覆盖。

## Git 内容与大文件规则

用户于 2026-10-10 明确的通用仓库规则：

- 仓库默认保存源代码、配置和必要的轻量文档、元数据。构建产物、可执行文件、软件包、容器/虚拟机镜像、下载压缩包、数据库导出和大体积原始数据默认不进入 Git；文本格式的数据大文件同样需要检查。
- 在工作树内下载或生成上述文件之前，先选择仓库外的制品/数据位置，或补上合理的 `.gitignore` 规则并验证实际路径已被忽略，防止暂存和代理恢复/差异快照将它们写入 Git 对象库。
- 暂存、提交前检查新增文件的大小、类型和 staged 文件列表，只加入本次需要的源文件；不得用强制添加绕过忽略规则。优先保留来源清单、校验值及可复现的下载/构建方法。
- 对二进制素材、数据集或生成文件是否应纳入版本控制拿不准时，先问用户，再暂存或提交；确需例外时也先取得用户明确指示。
- 本规则不授权删除已有文件、stash、恢复快照或改写 Git 历史。忽略规则不会清除已存在的 Git 对象，历史清理需要单独明确范围。
