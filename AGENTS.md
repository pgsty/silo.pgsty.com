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

## 其它

- 文案改动同时维护中英两版（`$zh` 分支 / `content/_index.md` 与 `content/_index.zh.md`）。
- 改完模板或 CSS 跑 `hugo --quiet` 验证构建；`static/css/*` 靠 md5 query string 破缓存，
  不需要手动改版本号。
- 指标数据别手写，跑 `bin/metrics.py`。
