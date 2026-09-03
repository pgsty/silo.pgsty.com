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

- 文案改动同时维护中英两版（`$zh` 分支 / `content/_index.md` 与 `content/_index.zh.md`）。
- 改完模板或 CSS 跑 `hugo --quiet` 验证构建；`static/css/*` 靠 md5 query string 破缓存，
  不需要手动改版本号。
- 指标数据别手写，跑 `bin/metrics.py`。
- 通用文档壳、搜索、短代码和 blocks 来自 `github.com/pgsty/oink`；不要把 OINK
  模板重新复制回项目。这里只保留 SILO 首页、下载页、来源声明等产品专属覆盖。
