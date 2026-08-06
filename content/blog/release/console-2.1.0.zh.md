---
title: "Silo Console 2.1.0 发布"
linkTitle: "silo/console 2.1.0 发布"
date: 2026-08-06
author: "冯若航"
description: "双语控制台：零依赖的中英文界面覆盖全部页面，仪表盘迁移到 MinIO Metrics V3 并显式处理零值语义，另有一批正确性修复——包括转义安全的占位符替换，以及不会说谎的全选框。"
tags: [发布, console]
weight: 3
url: "/zh/blog/release/console-2.1.0/"
aliases:
  - /releases/console-2.1.0/
---
**发布日期：** 2026-08-06 · **版本：** [v2.1.0](https://github.com/pgsty/silo-console/releases/tag/v2.1.0) · **仓库：** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.1.0 是独立发布 2.0.0 之后的第一个功能版本，做了三件事：

1. **会说两种语言**——全部控制台页面、帮助条目与文档链接都能以中文或英文呈现，切换按钮出现在每一页，且不引入任何新的运行时依赖；
2. **读对了指标**——仪表盘从 MinIO Metrics V2 名称迁移到 V3，并针对 V3 在底层改变的语义逐条做了显式处理；
3. **在边界情况下不再说谎**——全选框与批量操作作用于同一批对象，占位符能扛住包含 `$&` 的对象名，时间戳带上了时区，空指标显示"无数据"而不是编造出来的 `0`。

这是一个**小版本**。环境变量、模块路径、API 契约、二进制名称和数据布局均无变化，升级就是换二进制或换镜像。

{{% alert color="info" %}}
**如果你内嵌了这套控制台，请重新生成嵌入资产**

2.1.0 修复了 2.0.0 之后 `main` 分支上的一个打包缺陷：`go:embed` 负载中仍是 2.0.0 的前端构建产物，因此从中间提交构建出的二进制会提供旧版界面。2.1.0 的正式发布产物基于重新生成的负载构建，不受影响。
{{% /alert %}}

## 双语控制台 {#bilingual-console}

这是一套对象存储的管理界面，而它的运维使用者中有相当一部分以中文为第一语言。2.1.0 在不引入 i18n 框架的前提下把界面变成双语——嵌入式交付意味着每一 KB 都要计入二进制体积。这对应 [issue #6](https://github.com/pgsty/silo-console/issues/6)：该 issue 原本提议使用 `i18next`，而"零依赖"是本次实现相对它唯一一处有意的偏离。

### 实现方式 {#i18n-architecture}

设计约束是：不加新依赖、不加构建步骤、不引入字符串抽取流水线，并且**部分覆盖绝不能让页面出错**。

- **英文原文就是字典的 key**。`t("Create Bucket")` 查找对应的中文条目；查不到则原样返回英文。因此覆盖度可以增量生长，写错 key 的后果是退化成英文，而不是暴露 `console.bucket.create` 这样的裸标识。
- **三份字典，一次合并**。`zh.ts`（165 条界面框架）、`zhHelp.ts`（247 条帮助内容）、`zhScreens.ts`（1373 条功能页面）合并时以框架优先，合计约 1785 条。
- **语言偏好完全复用暗色模式的模式**：`localStorage` → `systemSlice` → `setLanguage`。**不做浏览器语言探测**，默认英文，选择完全显式。
- **集中拦截而非逐点改写**：页头包装器、确认对话框、帮助条目、路由定义、仪表盘面板渲染器各自在输出的最后一步翻译。这正是 220 个页面文件能够在不触碰业务逻辑的情况下完成本地化的原因。
- **模块拆分是必要的**。`i18n/lang.ts` 只存放纯函数原语（`translate`、`localizeUrl`）且不导入 store——`systemSlice` 依赖它，反向导入会形成循环依赖。Hooks（`useT`、`useLanguage`、`useLocalizedLink`）与 `interpolate()` 放在 `i18n/index.tsx`。

切换控件是一个描边风格的 文/A 图标，挂载在所有页面的页头，登录页复用同一控件。

### 覆盖范围 {#i18n-coverage}

登录与 SSO 流程、导航与命令面板、仪表盘与全部指标面板、存储桶与完整对象浏览器（上传、预览、分享、版本、回溯）、用户/用户组/策略/访问密钥、配置与事件目标、IDP 与 KMS、日志、健康报告、性能测试、性能剖析、对象检查、跟踪、监视，以及许可证页面。

除可见文本之外：

- **文档链接会本地化**。`silo.pgsty.com` 的链接在中文下加 `/zh` 前缀；Pigsty 站点做域名对调（`pigsty.io` ↔ `pigsty.cc`）。GitHub、MinIO、AWS、YouTube 链接保持不变。
- **帮助面板的博客源按语言区分**，中文下拉取 `/zh/blog/index.xml`，并为每种语言维护独立缓存。
- **命令面板在两种语言下都能搜到**。菜单项显示时翻译，但保留英文原文作为关键词，因此"桶"和 "buckets" 都能命中。
- **图表图例只翻译静态前缀**。`translateLegend` 保留 `[server:drive]` 这类实例后缀；数据层保留原始图例，所以那些依赖图例做数值匹配（容量求和）的组件继续正常工作。
- **时间戳做的是统一，而不只是翻译**，详见下文。

### 代价 {#i18n-cost}

嵌入负载增加约 **61 KB**（2.79 MB → 2.85 MB，+2.2%），**零新增依赖**，字典进入独立的按需加载分块。英文渲染路径字节稳定：使用默认语言时，输出与 2.0.0 完全一致。

### 仍然是英文的部分 {#i18n-limits}

后端错误信息（182 条）由 Go 服务端产生，前端无法翻译。少量硬编码在 vendored `mds` 组件库内部的字符串——收起态菜单的 "Sign Out" 提示，以及数据表格的 "Columns"、"Loading…" 和 ON/OFF 开关——仍是英文；其中两处（"Sign Out"、"Actions:"）通过作用域 CSS 规则做了中文替换，其余需要改动 vendor 才能处理。

## Metrics V3 迁移 {#metrics-v3}

仪表盘此前查询的是 MinIO Metrics **V2** 名称，而 SILO 部署抓取的是 **V3**（`/minio/metrics/v3`）——也就是说，仪表盘依赖的是监控流水线已经不再采集的端点。2.1.0 将全部 **26 个部件**重写到 V3 目录——31 条查询，涉及 29 个不同的指标名——并移除三个从未被任何布局引用的部件（51/61/62）。这对应 [issue #7](https://github.com/pgsty/silo-console/issues/7)，Info 页面的那一半是 [#8](https://github.com/pgsty/silo-console/issues/8)。

这里的决定是 **V3 only**：不做运行时回退、不做探测、不提供版本选择开关。SILO Console 面向的是 SILO 部署，服务端、抓取流水线与控制台是一同交付的。SILO 服务端继续为外部消费者提供 V2 端点，只是控制台不再使用。回退机制在这里反而有害——保留 15 天 V2 序列的指标库会让 `or` 回退悄悄读到过期数据。

### V3 改变的语义 {#v3-semantics}

有三条 V3 特性会让"照名字改写"的迁移出错，每一条都需要明确的应对：

1. **集群组指标由每个节点重复导出**。`/cluster/*` 指标不带 server 标签，也不做 leader 门控，因此 N 节点的抓取会得到 N 条重复序列。查询统一用 `max()`/`min()` 聚合——绝不能用 `sum()`，那会把集群总量乘以节点数。
2. **零值根本不导出**。任何取值 ≤ 0 的指标都会被跳过。离线磁盘数、修复中磁盘数、纠删集健康状态不是报 `0`，而是直接消失——统计卡片会渲染成空白面板。所有受影响的查询都配了伴随守卫，让面板读出真实的 `0`。
3. **完全不存在 `minio_heal_*` 命名空间**。V2 的修复活动信号本身就是内存态的：重启即清零，任何扫描都会刷新它。它被两张语义可辩护的卡片取代：**纠删健康**（以写入法定人数为基线）和**用量数据时效**（扫描器用量快照的陈旧程度）。

### 零值语义 {#zero-state-semantics}

这次迁移经过了一轮对抗性审查，产出 8 项发现，全部在发布前修复。它们共享同一个主题——区分*零*、*无数据*与*尚未扫描*：

- **容量**的空闲/已用以恒定存在的总量为基线，因此写满的集群显示 `0 空闲`，而不是整个消失。
- **在线磁盘**针对全部离线的场景加了守卫——恰恰是最需要看到这个数字的时候，零值跳过会抹掉面板。
- **桶与对象计数**改用用量组自身的新鲜度指标做守卫，因此尚未完成首次扫描的集群显示*无数据*，而不是编造一个 `0`。
- **空的单值结果**渲染为 `—`，而不是 `0`。
- **空的大小分布**不再伪造七个零高度的柱子。
- **小数速率保持可见**（`parseFloat` 轴域、两位小数的 CPU 格式化器），不再被压成 `0`。
- **不足一秒的用量数据时效**收敛到"1 秒"，而不是渲染成空白。

回归测试套件（`api/admin_info_metrics_test.go`）现在把每条部件查询钉死在 V3 目录上，校验部件 ID 唯一性，并强制执行逐部件的守卫分类法：健康与流量类需要在线节点数伴随项，用量计数类需要用量组新鲜度伴随项，容量类需要总量基线。完整映射记录在 [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/main/docs/metrics-v3.md)。

### 顺带修复 {#metrics-other-fixes}

- 部件 17 把 `sent_bytes` 查了两次，部件 11 把 `syscall_read` 查了两次——两组节点间/系统调用的收发配对都退化成了重复项。
- 无标签矩阵（`max()` 聚合的结果）序列化时**完全没有** `metric` 字段，导致前端的标签提取崩溃，表现为容量环图显示 `0 B`、用量增长图为空。已加守卫。
- 一个从未被使用的逐部件 Prometheus label-values 预取请求，让每次部件请求最多多等一秒。已删除。
- 仪表盘的用量卡片、图表控件以及密集的流量/资源面板按统一语法重建，现在在平板宽度下也能正常重排。

工作中还发现两个**服务端**缺陷，选择上游跟踪而非在此绕过：`minio_cluster_usage_buckets_since_last_update_seconds` 发出的是纳秒（对象变体是正确的），以及 V3 桶级发送/接收流量被对调。

## 正确性修复 {#correctness-fixes}

### 能扛住真实对象名的占位符 {#escape-proofing}

`String.prototype.replace` 会把**替换值中**的 `$&`、`$'`、`` $` ``、`$1` 当作指令解释。而 S3 的 key 合法地允许包含 `$`。于是一个名为 `report$&.csv` 的对象不会按原样渲染——它会把匹配到的占位符文本重新注入输出，破坏整条消息。全部 **37 处**字典占位符替换现已改为传入函数形式的替换值，函数形式不做任何此类解释。这是原本英文界面里就存在的潜在缺陷，并非 i18n 引入；只是 i18n 审计把它找了出来。

### 名副其实的全选 {#select-all}

vendored 数据表格在缺少 `onSelectAll` 时会渲染一个无法翻译的纯文本 "Select" 表头——七张可选表格全都如此。更麻烦的是，直觉的修法是错的：直接用可见行替换整个选择集，会**丢掉被当前过滤条件隐藏的行**，于是表头复选框与随后的批量操作可能作用于不同的集合。实现只切换当前可见行，并保留被过滤隐藏的选择，因此表头状态不可能再暗示一个与实际操作对象不同的集合。

### 带时区的时间戳 {#timestamps}

桶、对象、版本、回溯与访问密钥的时间戳此前混用冗长英文格式，并且有几处使用**不带 AM/PM 的 12 小时制**——这根本是歧义的。现在它们在两种语言下统一渲染为 `yyyy-MM-dd HH:mm[:ss] (ZZZZ)`。

### 扛得住实时数据的翻译运行时 {#translation-runtime}

`t()` 同样会收到运行时字符串：User-Agent、RSS 标题、对象名。由此做了两项加固：

- 未命中时**无条件原样返回**——隐式的 `@context` 后缀剥离被移除，因为它会悄悄改写恰好含有 `@` 的实时数据；
- 字典查找加上 `hasOwnProperty` 守卫，因此恶意输入即便命中继承自 `Object.prototype` 的成员（`constructor`、`toString`）也无法把函数泄漏到界面上。

### 交互与可访问性 {#interaction-fixes}

- 会话过期后打开深链会在 `/login` 之间**来回弹跳**，不断累积重定向链，而不是干脆落到登录表单上（[#1](https://github.com/pgsty/silo-console/issues/1)）。
- 收起态的侧边栏按钮没有可访问名称，屏幕阅读器只能报为未命名控件（[#4](https://github.com/pgsty/silo-console/issues/4)）。访问密钥输入框现在显式声明 autocomplete 意图，而不是让密码管理器去猜（[#5](https://github.com/pgsty/silo-console/issues/5)）。
- 移动端的指标与存储桶面板改为滚动，不再被裁切（[#3](https://github.com/pgsty/silo-console/issues/3)）。
- 性能测试的控件行改为换行而不是溢出卡片，时长可填秒或分钟，大小的默认单位改为 MiB 以匹配其自身的单位列表。
- 侧边栏桶列表的虚拟行距与 44px 的行高对齐，选中与悬停高亮不再互相重叠。
- 单位标签渲染所选单位的**显示名**，而不是原始取值。

## 没有 SUBNET，没有遥测 {#no-telemetry}

上游已移除 Subnet、Registration 与 Call Home，本项目继承了该状态，但仍残留三处痕迹。2.1.0 予以清除：

- 健康诊断 websocket 的 `subnetResponse` 字段从来就不指向任何 subnet——它只是一个"报告已生成"的哨兵值——现改为 `reportStatus: "ok"`；
- 两条帮助文案声称健康报告"会自动上传到 SUBNET"、检查输出"传输到 SILO SUBNET"。两者都不属实。它们现在描述真实行为：报告在部署端生成，由浏览器下载；
- 删除从未被引用的 `CONSOLE_SUBNET_PROXY` 常量。

顺带说明，2.1.0 的出网行为没有变化，仍然是：**无分析、无遥测、无埋点、无外部脚本与字体**。`silo-console update` 依旧禁用。版本目录仅在显式设置 `SILO_RELEASE_SERVICE_HOST`（或 `RELEASE_SERVICE_HOST`）时才会连接——没有默认值。浏览器唯一的自动出网请求是帮助面板的博客源，且只在用户打开 Blog 标签页之后发生。

## 升级指南 {#upgrade-guide}

没有任何需要迁移的内容。2.0.0 到 2.1.0 之间，环境变量、模块路径、协议字段、systemd 单元、二进制名称与数据布局均无变化。

```bash
install -m 0755 silo-console-linux-amd64 /usr/local/bin/silo-console
```

有两点值得知道：

- **仪表盘现在要求 Metrics V3**。如果你的 Prometheus 只抓取 V2 端点，仪表盘面板会显示无数据。请把抓取目标指向 `/minio/metrics/v3`；由 Pigsty 管理的部署已经如此。
- **语言默认为英文**，按浏览器选择并存入 `localStorage`。不存在服务端默认值，也不做浏览器语言探测，因此现有部署升级后外观不会发生变化。

## 验证范围 {#verification-scope}

打标签之前，完整变更集经过审阅，并针对最终代码树执行了以下门禁：`go build`、`go vet`、`golangci-lint`（0 问题）、全部 Go 包的单元测试、`gofmt`、TypeScript 类型检查、前端生产构建、全量 Prettier 检查、字典重复 key 检查，以及对完整 diff 的调试残留扫描。

29 个过程提交通过纯树操作重组为 20 个逻辑提交，重建后的分支顶端与重写前的代码树验证为**逐字节一致**。嵌入负载从干净目录重建两次并确认字节一致——这正是发布流水线零差异门禁所依赖的性质。重写前的历史保留在备份引用中。

Metrics V3 迁移另外接受了一轮由独立模型执行的对抗性审查，8 项发现全部修复（见[零值语义](#zero-state-semantics)）；其查询在含真实集群数据的线上指标库上做过验证。

## 已知限制 {#known-limitations}

- SSO 端到端测试套件依赖外部 OpenLDAP/Dex/MinIO 拓扑，本轮未在该环境中运行；OIDC 代码路径已由单元测试覆盖。
- 后端错误信息与若干 vendored `mds` 组件字符串仍为英文（见[仍然是英文的部分](#i18n-limits)）。
- 中文翻译覆盖控制台自身的界面；帮助条目正文已翻译，但它们所链接的文档页面遵循文档站自身的语言覆盖情况。
- 两个服务端 V3 指标缺陷（桶用量时效的纳秒单位、桶级流量对调）在上游跟踪，控制台侧未做绕过。
- 自动自更新仍然禁用，升级需要显式执行。

## 已关闭的 Issue {#issues-closed}

2.1.0 关闭了针对 2.0.0 提出的全部 issue。每个 issue 在 tracker 上都留有一条评论，说明修复方式、涉及的提交，以及补充的测试覆盖。

| Issue | 解决方式 |
|---|---|
| [#1](https://github.com/pgsty/silo-console/issues/1) — 未认证深链无限递归 `/login` | 改为绝对且感知 base path 的登录目标；补充深链与子路径部署的测试 |
| [#2](https://github.com/pgsty/silo-console/issues/2) — Uptime 陈旧、图例畸形、菜单局促 | Uptime 取自真实服务器状态，图例改用 V3 的 `name` 标签解析，图表控件 32 px，弹出菜单设最小宽度 |
| [#3](https://github.com/pgsty/silo-console/issues/3) — 390 px 视口裁切内容 | 指标标签页改为可横向滚动；桶列表在移动端使用明确的列宽预算 |
| [#4](https://github.com/pgsty/silo-console/issues/4) — 收起态侧边栏按钮无名称 | 标签改为视觉隐藏而非从可访问性树中移除；折叠开关具名且可键盘操作 |
| [#5](https://github.com/pgsty/silo-console/issues/5) — 访问密钥字段缺少 autocomplete 元数据 | 在独立的自动填充 section 中声明 `username` / `new-password` 字段级 token |
| [#6](https://github.com/pgsty/silo-console/issues/6) — 中英文本地化 | 手写双语层，零新增依赖，以英文原文为 key 兜底 |
| [#7](https://github.com/pgsty/silo-console/issues/7) — 监控查询迁移到 Metrics V3 | 仅 V3；26 个部件、31 条查询、29 个指标名，配套守卫分类与回归测试 |
| [#8](https://github.com/pgsty/silo-console/issues/8) — 用可用的 V3 健康信号替换 N/A | Erasure Health 与 Usage Data Age，与高级仪表盘共用同一份部件数据 |

有三项验收标准如实记为未达成，而不是含糊勾掉：`web-app` 目前没有单元测试运行器，因此 #6 的 i18n 测试套件与 #2 中针对 `constructLabelNames` 的专项测试都需要先引入测试工具链；另外 #6 要求的"如何新增翻译 key"的贡献者文档尚未编写。

## 关联提交与链接 {#related-links}

v2.1.0 的完整变更由以下 20 个逻辑提交构成。`v2.1.0` 标签另外还带有三个更晚的文档提交，它们重写了仓库 README，不改变任何已交付的行为。

- [`8764f5d`](https://github.com/pgsty/silo-console/commit/8764f5de) — fix(web): stop recursive login redirects
- [`437c56c`](https://github.com/pgsty/silo-console/commit/437c56cd) — fix(ui): make the dashboard and bucket list usable on narrow screens
- [`85fc0c6`](https://github.com/pgsty/silo-console/commit/85fc0c61) — fix(a11y): name collapsed sidebar controls and credential fields
- [`e3fed07`](https://github.com/pgsty/silo-console/commit/e3fed077) — fix(metrics): rebuild dashboard cards, chart controls, and layout
- [`fa11576`](https://github.com/pgsty/silo-console/commit/fa115764) — feat(login): polish controls and legal attribution
- [`9fc17c1`](https://github.com/pgsty/silo-console/commit/9fc17c16) — feat(i18n): add hand-rolled EN/ZH core, dictionaries, and language toggle
- [`622c02e`](https://github.com/pgsty/silo-console/commit/622c02e8) — feat(i18n): localize login, navigation, and the help system
- [`6a03719`](https://github.com/pgsty/silo-console/commit/6a03719c) — feat(i18n): localize dashboard and metrics screens
- [`14b1c2d`](https://github.com/pgsty/silo-console/commit/14b1c2de) — feat(i18n): localize bucket and object browser screens
- [`0298062`](https://github.com/pgsty/silo-console/commit/0298062a) — feat(i18n): localize identity, configuration, and event destinations
- [`41094f6`](https://github.com/pgsty/silo-console/commit/41094f65) — feat(i18n): localize observability, admin tools, and shared components
- [`e964992`](https://github.com/pgsty/silo-console/commit/e964992f) — feat(metrics): migrate the dashboard to MinIO Metrics V3
- [`0b2251f`](https://github.com/pgsty/silo-console/commit/0b2251f5) — fix(i18n): harden the translation runtime for live data and chart legends
- [`9b60148`](https://github.com/pgsty/silo-console/commit/9b601489) — fix(console): unify timestamps on a timezone-carrying standard format
- [`bf110ae`](https://github.com/pgsty/silo-console/commit/bf110aea) — fix(console): give selectable tables a visible-rows select-all
- [`5fc8f22`](https://github.com/pgsty/silo-console/commit/5fc8f221) — fix(i18n): escape-proof all placeholder substitutions
- [`fef8fab`](https://github.com/pgsty/silo-console/commit/fef8fabe) — fix(console): polish speedtest, sidebar, and help chrome
- [`c4911e8`](https://github.com/pgsty/silo-console/commit/c4911e88) — chore(console): drop SUBNET remnants from health reporting
- [`1d631c4`](https://github.com/pgsty/silo-console/commit/1d631c47) — docs: record the SILO Console v2.1.0 changelog
- [`912d847`](https://github.com/pgsty/silo-console/commit/912d847b) — build: regenerate optimized embedded web assets

相关链接：

- [SILO Console 源代码](https://github.com/pgsty/silo-console) · [Releases](https://github.com/pgsty/silo-console/releases)
- [SILO 网站](https://silo.pgsty.com/zh/) · [文档](https://silo.pgsty.com/zh/docs/)
- [授权说明](https://silo.pgsty.com/zh/about/license/) · [来源归属](https://silo.pgsty.com/zh/about/attribution/) · [商标说明](https://silo.pgsty.com/zh/about/trademark/)
