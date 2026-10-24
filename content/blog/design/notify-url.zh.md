---
linkTitle: "数据库通知迁移"
title: "数据库通知统一连接串：#53 的兼容性边界"
date: 2026-08-23
lastmod: 2026-09-16
author: "冯若航"
summary: >
  SILO 保留 PostgreSQL 与 MySQL 通知目标，但将配置统一收敛到完整连接串。KV 配置体系之前（pre-KV）的数据库离散字段属于不受支持的迁移输入，必须让服务器启动明确失败，而不是被接受后静默拖垮全部桶通知。
tags: [设计, 通知, 兼容性]
weight: 10
draft: false
url: "/zh/blog/design/notify-url/"
---

随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 发布的提交 [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) 修复了 [SILO #53](https://github.com/pgsty/silo/issues/53)，明确了 PostgreSQL 与 MySQL 桶通知目标的兼容性边界、旧配置迁移行为与启动期错误处理契约。

## 最终决策 {#decision}

SILO 保留 PostgreSQL 与 MySQL 通知目标（notification target），但每种数据库仅支持单一的规范配置键：

- PostgreSQL 必须提供完整的 `connection_string`；
- MySQL 必须提供完整的 `dsn_string`。

2020 年之前的五字段形式——`host`、`port`、`username`、`password`、`database`——继续作为当前 KV 配置系统不支持的格式。SILO 既不重新注册这些键，也不在旧 JSON 配置迁移时自动将它们拼接合成为 DSN。

旧配置迁移契约按三类输入状态处理：

| 旧 target 状态 | 迁移结果 |
| --- | --- |
| 未启用（`Enable == false`） | 忽略，不生成任何 KV 配置项。 |
| 已启用，且含有非空 `connection_string` 或 `dsn_string` | 仅迁移规范连接串和其他已注册的 target 设置。 |
| 已启用，但仅有离散连接字段 | 在新配置生效前拒绝迁移并中止服务器启动；错误信息明确指出子系统与 target 名称及修复方法，且绝不打印任何凭据内容。 |

## 背景 {#context}

SILO 从上游继承了两代数据库通知配置方式。在引入 KV 配置体系之前，旧版 JSON 配置既可以保存完整连接串，也可以使用五个离散字段：

```text
host
port
username
password
database
```

当前 KV 配置体系则仅暴露驱动原生的连接串键：

```text
notify_postgres  -> connection_string
notify_mysql     -> dsn_string
```

上游早在 `RELEASE.2020-04-10T03-34-42Z` 中就已废弃这五个离散字段，并要求运维人员迁移到 `connection_string` 或 `dsn_string`。SILO 当前的命令行帮助表、环境变量文档、示例以及 Console 界面也均将完整连接串作为唯一正式接口。

## 问题本质 {#defect}

在 [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) 之前，旧配置迁移辅助函数 `SetNotifyPostgres` 与 `SetNotifyMySQL` 会把两种形式同时写入新 KV 配置。即使旧 JSON target 中已经配置了完整的 `connection_string` 或 `dsn_string`，迁移器仍会一并写出全部五个离散键（通常为空字符串）。

新解析器随后会拒绝这些键，因为 `DefaultPostgresKVS` 与 `DefaultMySQLKVS` 均未注册它们，而 `CheckValidKeys` 仅检查键名是否存在，不区分值是否为空。因此新旧两种来源格式在迁移后都会失败：

```text
旧完整连接串 -> 规范连接串 + 五个空的未知 key -> 拒绝
旧离散字段   -> 空规范连接串 + 五个有值的未知 key -> 拒绝
```

通知子系统的初始化逻辑进一步放大了这一故障。`FetchEnabledTargets` 对所有通知子系统采用快速失败（fail-fast）策略：第一个校验失败的子系统会直接返回错误和空的 target 列表。上层调用方仅记录一行错误日志便继续启动对象存储服务，导致同一集群上原本健康的 Webhook、Kafka、NATS 等其他通知目标也全部被连带禁用。

仅仅让两个迁移函数返回错误还不足以彻底修复该行为。错误虽会沿 `readConfigWithoutMigrate` 与 `initConfig` 向上传播，但 `initConfigSubsystem` 原先会将不可重试的配置错误降级记录为 `"some features may be missing"` 日志并返回成功。随后服务端会在未设置 `globalServerConfig` 的状态下继续启动——不仅桶通知全部失效，区域（region）、存储类型、压缩、身份认证及其他持久化配置也可能全部缺失。反之，若将该错误标记为可重试，服务端又会在静态配置错误上陷入死循环。因此，必须将数据库迁移失败定义为不可重试的类型化致命错误（`LegacyDatabaseTargetError`），一路传递至启动边界并立即终止进程。

修复前的降级行为尤为危险：由于普通 S3 对象读写依然正常，运维人员看到的是表面健康的 S3 服务，而所有已配置的事件通知管道均已静默中断。此外，未注册的 `password` 键缺少敏感字段元数据，可能被明文复制进健康检查或诊断包中；而正式注册的 `connection_string` 与 `dsn_string` 则均按敏感值进行脱敏处理。

## 为什么第一版修复被回滚 {#reverted-fix}

`20260804` 中的第一版尝试（[`SN-2026-019`](/zh/blog/security/notify-keyspace-registration/)）曾在 `DefaultPostgresKVS` 与 `DefaultMySQLKVS` 中重新注册了这五个离散键，并让解析器读取它们。虽然这使迁移后的配置能够通过 `CheckValidKeys`，但却直接破坏了文档正式支持的完整连接串路径。

共享的 `mcli admin config set` 分词器通过扫描已注册的键名来识别字段边界，并不具备完整的引号语法感知能力。一旦 `port` 成为 `notify_postgres` 的已注册顶层键，下面这条合法的引号内连接串就会被误识别为包含第二个顶层 KV 字段：

```text
connection_string="host=db port=5432 dbname=events user=app"
```

分词器会在引号内部的 `port=` 处直接切分，将 `connection_string` 截断为 `"host=db`，再把剩余部分交给整型的 `port` 解析器，最终报出 `invalid port` 错误。

在当前共享分词器语法下，注册 `host`、`port`、`password` 等常见词会导致连接串内部参数语法与顶层 KV 语法发生直接冲突。因此第一版注册方案被彻底回滚，改为严格执行单一连接串边界。

## 产品判断 {#product-judgment}

数据库通知目标无需额外部署外部消息总线即可在数据库中维护对象命名空间视图或访问审计流水，对于小型部署及已运行 PostgreSQL / MySQL 的环境依然具有实用价值。

相比之下，五字段连接参数模型的表达能力十分受限，无法表达常见的数据库驱动选项：TLS 模式与证书路径、连接超时、应用名称、Unix Socket、PostgreSQL 多主机容灾以及 MySQL 驱动参数。同时支持两种格式还会制造优先级、配置合并、密码脱敏与测试矩阵的歧义。由 SILO 负责通知投递语义、由数据库驱动负责原生连接串语法，才是最清晰的抽象边界。

## 目标 {#goals}

1. 将 `connection_string` 与 `dsn_string` 确立为数据库通知唯一受支持的在线配置键。
2. 允许已包含非空规范连接串的旧 JSON target 无损跨过迁移边界。
3. 在仅含离散字段的已启用旧 target 生成半成品或非法 KV 配置之前明确拒绝。
4. 将 #53“服务看似健康、全部通知静默失效”的运行时故障模式，替换为必须先修正才能启动的显式启动期失败（`LegacyDatabaseTargetError`）。
5. 确保迁移错误、日志、健康报告与诊断包均不会泄露数据库密码。
6. 从未注册配置键写入审计（`knownUnregisteredWrites`）中彻底移除 Postgres/MySQL 的十条例外。
7. 在发布说明与迁移文档中明确兼容性边界与运维修复步骤。

## 非目标 {#non-goals}

- 在当前 KV 接口中同时支持 DSN 与数据库离散字段；
- 在旧配置迁移时自动从离散字段拼接合成 DSN；
- 重写共享 KV 分词器；
- 在本补丁中改变 `FetchEnabledTargets` 的跨子系统 fail-fast 语义；
- 静默跳过已启用的非法数据库 target 并以残缺的通知覆盖继续运行；
- 移除 PostgreSQL 或 MySQL 通知功能；
- 删除用于解码旧 JSON 并识别不受支持离散输入的旧结构体字段；
- 修改除 PostgreSQL 和 MySQL 之外其他八个旧通知 setter 的既有错误处理方式。

## 功能需求 {#functional-requirements}

### 当前配置 {#current-configuration}

1. `notify_postgres` 仅接受 `connection_string`；`notify_mysql` 仅接受 `dsn_string`。
2. 五个离散键（`host`、`port`、`username`、`password`、`database`）保持未注册状态，并被当前配置命令拒绝。
3. 完整连接串继续支持数据库驱动原生语法，包括引号内出现 `host=`、`port=`、`user=`、`password=`、`database=` 等子串的情形。
4. 旧环境变量 `MINIO_NOTIFY_POSTGRES_HOST`/`PORT`/`USERNAME`/`PASSWORD`/`DATABASE` 及其 MySQL 对应变量保持未接线和不受支持状态。

### 旧配置迁移 {#legacy-migration}

1. 当旧 target 未启用（`Enable == false`）时，`SetNotifyPostgres` 与 `SetNotifyMySQL` 直接返回 `nil`，不生成任何 KV target。
2. 对已启用的 target，`SetNotifyPostgres` 要求非空 `ConnectionString` 且只写出已注册的 Postgres 键；若规范连接串与离散字段同时存在，则以规范连接串为准并丢弃所有离散值。
3. `SetNotifyMySQL` 对 `DSN` 执行相同规则。
4. 两个迁移函数均不得写出 `host`、`port`、`username`、`password` 或 `database`。
5. 当已启用 target 缺少规范连接串时，返回类型化的 `LegacyDatabaseTargetError`，指明子系统与 target 名称但不包含任何字段值：

```text
notify_postgres:archive uses unsupported legacy discrete connection fields;
set connection_string before migrating to SILO
```

6. `cmd/config-migrate.go` 检查并向上传播两个数据库迁移函数的错误，拒绝启用或持久化半迁移配置。
7. `initConfigSubsystem` 将 `LegacyDatabaseTargetError` 作为不可重试的致命错误直接返回给 `serverMain`。

### 操作者修复路径 {#operator-remediation}

由于旧 JSON 配置只有在迁移成功后才会持久化为新 KV 配置，任何仍在读取旧格式 JSON 来源文件的部署在每次启动时都会重新进入迁移逻辑。遇到该启动错误的运维人员可按以下四条路径之一处理：

1. **切换到 SILO 前转换：** 在兼容的过渡版本上将旧离散字段替换为 `connection_string` 或 `dsn_string`，验证通知正常后再升级至 SILO；
2. **先禁用再重建：** 禁用或删除旧数据库 target，完成服务端升级后，使用规范连接串重新创建 target；
3. **全新安装：** 直接使用 `connection_string` 或 `dsn_string` 创建 target，不涉及旧配置迁移；
4. **仍在读取旧 JSON 的存量部署：** 先备份来源配置，在升级至 SILO Server 20260903 及更新版本前转换、禁用或移除该数据库 target。

## 可用性权衡 {#availability-trade-off}

本设计有意将不受支持的旧数据库通知配置从“降级启动”改为“启动硬失败”。虽然一台此前仍能处理对象读写（但通知已全部静默死亡）的服务器在升级后会拒绝启动，但对象存储表面健康、已配置的事件出口却全部消失，会导致静默且不可逆的下游事件丢失。用明确、可操作的启动前置检查替代隐患重重的静默降级更加安全。

## 安全要求 {#security-requirements}

1. `LegacyDatabaseTargetError` 绝不格式化输出旧参数结构体或其中任何字段值。
2. 回归测试注入哨兵密码（sentinel password），并断言返回错误和捕获日志中均不包含该哨兵值。
3. 迁移输出仅包含已注册的敏感连接串键（`connection_string` 与 `dsn_string`），不生成独立的 `password` 键。
4. 若受影响部署曾在修复前导出并对外提供过诊断包，建议轮换对应的数据库密码。

## 评估与否决的备选方案 {#alternatives}

### 注册并解析五个离散字段 {#alternative-register}

**优点：** 保留 2020 年前的旧 JSON 字段形式，并复用现存结构体字段。<br>
**否决原因：** 注册 `host`、`port`、`password` 等常见词会被共享分词器识别为顶层键，直接截断引号内包含 `port=` 等子串的合法 `connection_string`。

### 迁移时自动拼接生成规范连接串 {#alternative-synthesize}

**优点：** 自动兼容仅配置了离散字段的早期安装。<br>
**否决原因：** 需要为早在 2020 年即已废弃的输入格式永久承担 PostgreSQL 转义引用、MySQL DSN 编码、Unix Socket、IPv6 地址括号及驱动默认值的代码与测试维护负担。

### 仅跳过不支持的数据库 target {#alternative-skip}

**优点：** 让对象存储服务与其他通知 target 继续运行。<br>
**否决原因：** 静默丢弃用户已启用的事件通知出口会造成不可见的事件丢失。

### 修改全局 `FetchEnabledTargets` 的 fail-fast 行为 {#alternative-fail-fast}

**优点：** 隔离不同通知子系统之间的故障半径。<br>
**否决原因：** 既无法修复数据库迁移函数本身，也无法关闭未脱敏 `password` 键的暴露路径，且会改变全系统的通知启动错误语义。

### 彻底删除数据库通知 target {#alternative-remove-targets}

**优点：** 移除全部数据库通知专用代码维护面。<br>
**否决原因：** PostgreSQL 与 MySQL 通知目标本身功能自洽且实用，缺陷仅在于过时的五字段配置形式。

## 实现范围 {#implementation-scope}

服务端提交 [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) 仅修改 `internal/config/notify/legacy.go`、`cmd/config-migrate.go` 与 `cmd/server-main.go` 等 6 个文件：

1. 两个数据库旧配置 setter 仅输出规范已注册键，并在已启用 target 缺少规范连接串时返回不携带字段值的 `LegacyDatabaseTargetError`。
2. `cmd/config-migrate.go` 捕获并传播这两个数据库迁移错误。
3. `cmd/server-main.go` 中的 `initConfigSubsystem` 将 `LegacyDatabaseTargetError` 作为不可重试的致命错误直接返回，由 `serverMain` 通过 `logger.FatalIf` 终止启动。
4. 从 `knownUnregisteredWrites` 中移除全部 10 条 Postgres/MySQL 例外。

## 验收标准 {#acceptance-criteria}

实现通过了以下全部 12 项验收标准：

1. 含完整 `connection_string` 的旧 PostgreSQL target 可正常迁移、通过 `CheckValidKeys`，并由 `GetNotifyPostgres` 原样返回。
2. 含完整 `dsn_string` 的旧 MySQL target 完成同等验证。
3. 两类已启用的纯离散字段 target 均在初始化前失败，返回包含子系统与 target 名称的 `LegacyDatabaseTargetError` 并中止启动。
4. 缺失连接串和畸形连接串的错误均不包含哨兵主机名、用户名、密码、数据库名或 DSN 值。
5. 未启用的离散旧 target 不生成配置项，也不阻塞启动。
6. 迁移后的 KVS 不包含任何十个离散键（包括空值形式）。
7. 旧 target 同时包含规范连接串与冲突离散值时，仅迁移规范连接串，输出中不含任何离散哨兵值。
8. 使用真实 `DefaultPostgresKVS` 和 `DefaultMySQLKVS` 键集的 `SetKVS` 回归测试，能够正确解析引号内包含 `port=`、`host=`、`password=` 的完整连接串。
9. 同时包含健康 Webhook、Kafka、NATS target 与非法旧数据库 target 的配置在 `readConfigWithoutMigrate` 阶段即返回错误，不持久化、也不激活任何半成品配置。
10. `initConfigSubsystem` 直接返回类型化迁移错误，既不记录后继续，也不进入重试循环。
11. `knownUnregisteredWrites` 不再包含 Postgres/MySQL 例外。
12. 全部聚焦与常规测试套件通过：

```sh
go test ./internal/config/notify ./internal/config ./internal/event/target -count=1
go test -v ./cmd -run 'Test(ReadConfigWithoutMigrate|InitConfigSubsystem)' -count=1
```

## 实现结果与发布边界 {#implementation-result}

提交 [`f1ba68358`](https://github.com/pgsty/silo/commit/f1ba68358) 已随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 正式发布。跨仓库核对确认 `pgsty/mc`、`pgsty/silo-pkg` 与 `pgsty/silo-console` 均无需代码修改：客户端原样转发配置文本，`silo-pkg` 不包含通知配置 schema，而 Console 已将表单序列化为规范的 `connection_string` 或 `dsn_string`。

### 发布与兼容性声明 {#release}

SILO 数据库通知要求 PostgreSQL 使用 `connection_string`、MySQL 使用 `dsn_string`。2020 年前的离散 `host`/`port`/`username`/`password`/`database` 形式不会被迁移；在升级至 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 及更新版本前，请先转换、禁用或移除这类旧数据库 target。

### 设计审查校准记录 {#review-record}

初稿经设计审查校准后，补齐了穿过 `initConfigSubsystem` 至 `ExitFunc(1)` 的致命错误传播链路、覆盖了仍在读取旧 JSON 文件的存量部署、明确了规范连接串相对于残留离散字段的优先级，并通过了完整 `cmd` 测试套件与 `-race` 验证。
