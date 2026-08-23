---
title: "数据库通知统一连接串：#53 的兼容性边界"
date: 2026-08-23
author: "冯若航"
summary: >
  SILO 保留 PostgreSQL 与 MySQL 通知目标，但将配置统一收敛到完整连接串。KV 配置体系之前（pre-KV）的数据库离散字段属于不受支持的迁移输入，必须让服务器启动明确失败，而不是被接受后静默拖垮全部桶通知。
tags: [设计, 通知, 兼容性]
weight: 10
draft: false
url: "/zh/blog/design/notify-url/"
---

本文是 [SILO #53](https://github.com/pgsty/silo/issues/53) 的产品需求文档与设计决策归档，用来在实现开始前固定 PostgreSQL/MySQL 桶通知目标的最终兼容性边界。

## 最终决策 {#decision}

SILO 保留 PostgreSQL 与 MySQL notification target，但每种数据库只支持一种当前配置方式：

- PostgreSQL 必须提供完整的 `connection_string`；
- MySQL 必须提供完整的 `dsn_string`。

旧的五字段形式——`host`、`port`、`username`、`password`、`database`——继续作为当前 KV 配置系统不支持的格式。SILO 不重新注册这些 key，也不在旧配置迁移时自动把它们拼成 DSN。

旧配置迁移契约刻意保持狭窄：

| 旧 target 状态 | 处理结果 |
| --- | --- |
| 未启用 | 忽略，不生成 target。 |
| 已启用，且已有非空 `connection_string` 或 `dsn_string` | 只迁移规范连接串和其他已注册设置。 |
| 已启用，只有离散连接字段 | 在新配置生效前拒绝迁移并使服务器启动失败；错误必须可操作、指出子系统与 target 名称，但绝不能打印凭据。 |

这是配置边界决策，不是删除数据库通知功能。

**状态：** 设计已接受，实现待完成。  
**归属：** SILO 服务端仓库。  
**跟踪：** [pgsty/silo#53](https://github.com/pgsty/silo/issues/53)。  
**目标：** 实现并验证后进入下一个 SILO 补丁版本。

## 背景 {#context}

SILO 从 MinIO 继承了两代数据库通知配置。

KV 时代之前的 JSON 配置既可以保存完整连接串，也可以使用五个离散字段：

```text
host
port
username
password
database
```

当前 KV 配置只暴露驱动原生形式：

```text
notify_postgres  -> connection_string
notify_mysql     -> dsn_string
```

这不是新方向。MinIO 在 `RELEASE.2020-04-10T03-34-42Z` 就废弃了五个离散字段，并要求迁移到 `connection_string` 或 `dsn_string`。SILO 当前的帮助表、环境变量文档与示例也已经把完整连接串作为正式接口。

SILO 是一个迁移步骤显式的新社区分支。它优先保证 S3/Admin API、当前 `MINIO_*` 设置、盘上数据格式和当前 KV 配置的兼容性；当一个规范形式已经存在多年时，没有必要永久保留 2020 年以前的每一种配置拼法。

## 问题本质 {#defect}

当前旧配置迁移器 `SetNotifyPostgres` 与 `SetNotifyMySQL` 会把两种形式一起写入新 KV 配置。即使旧 target 已经有完整连接串，迁移器仍会附带五个离散 key，通常只是写入空值。

新解析器会拒绝这些 key，因为 `DefaultPostgresKVS` 与 `DefaultMySQLKVS` 都没有注册它们。合法性检查只看 key 是否存在，不看值是不是空。因此两种旧来源都会失败：

```text
旧完整连接串 -> 规范连接串 + 五个空的未知 key -> 拒绝
旧离散字段   -> 空规范连接串 + 五个有值的未知 key -> 拒绝
```

通知初始化又放大了这个错误。`FetchEnabledTargets` 对所有通知子系统采用 fail-fast：第一个非法子系统会返回错误和空 target list。上层只记录错误并继续启动对象存储服务，于是健康的 Webhook、Kafka、NATS 等 target 也全部不可用。

仅仅让两个迁移 helper 返回错误还不能修复这个行为。错误会经过 `readConfigWithoutMigrate` 与 `initConfig` 向上传播，但 `initConfigSubsystem` 当前会把不可重试的配置错误降级成 “some features may be missing” 日志并返回成功。服务器随后在没有设置 `globalServerConfig` 的情况下继续启动；通知失败只是其中一个后果，区域、存储类、压缩、身份与其他持久化设置也可能全部缺失。因此实现必须把类型化数据库迁移错误传到启动边界，并在那里按致命错误处理。把它标记为可重试同样不对，因为在没有外部状态变化时，服务器只会无限重试，配置永远不会自行修复。

这个行为格外危险，因为对象读写仍然正常。操作者看到的是健康的 S3 服务，但全部事件管道已经停止。target 根本没有建立，所以不能假定故障期间产生的事件日后还能投递或补放。

此外还有诊断信息暴露问题。未注册的 `password` 没有敏感字段元数据，可能被原样复制到健康检查或诊断材料中；正式注册的 `connection_string` 与 `dsn_string` 已经按敏感值处理。

## 为什么第一版修复被回滚 {#reverted-fix}

第一版修复注册了五个离散 key，并让解析器读取它们。这样迁移结果确实能通过 `CheckValidKeys`，而且 target 参数结构和构造器中也仍然保留着旧字段，看起来是很自然的接线方式。

但它破坏了文档明确支持的完整连接串路径。

共享的 `mc admin config set` 分词器通过查找已注册 key 来识别字段边界，并不能完整理解引号。一旦 `port` 成为已注册 key，下面这条合法输入中就出现了一个看似新的顶层字段：

```text
connection_string="host=db port=5432 dbname=events user=app"
```

分词器会在引号内部的 `port=` 处切开，把 `connection_string` 截断，再把剩余部分交给 `port` 解析器，最终报出 `invalid port`。

在当前分词器下，注册 `host`、`port`、`password` 这类常见词，会让连接串语法与顶层 KV 语法发生直接冲突。因此第一版注册方案被回滚；重新注册这些字段不是可接受的修复。

## 产品判断 {#product-judgment}

数据库 notification target 是一个专业但有价值的能力。它可以直接提供数据库中的对象命名空间视图或访问流水，不要求用户额外部署事件总线；对于小型部署以及本来就在运行 PostgreSQL/MySQL 的用户仍然有意义。

旧连接参数写法的价值则低得多。五字段模型无法表达常见驱动能力：TLS 模式与证书、连接超时、应用名、Unix socket、PostgreSQL 多主机配置、MySQL 驱动参数，以及未来新增的驱动选项。同时支持两种形式还会制造优先级、合并、脱敏与测试问题；单一规范值不存在这些歧义。

完整连接串才是正确的抽象边界：SILO 负责通知语义，数据库驱动负责连接语法。

因此产品决策是保留能力、删除兼容假象。不支持的旧 target 必须被明确拒绝，不能再被“接受”后转换成一个随后拖垮无关 target 的非法配置。

## 目标 {#goals}

1. 把 `connection_string` 与 `dsn_string` 固定为数据库通知唯一受支持的在线配置接口。
2. 允许已经含有规范连接串的旧 JSON target 跨过迁移边界，不改变其连接语义。
3. 在离散字段旧 target 产生半成品或非法 KV 配置之前明确拒绝。
4. 把 #53 当前“服务看似健康、全部通知静默失效”的运行时故障模式，替换为操作者必须先解决才能启动的显式启动期失败。
5. 确保迁移错误、日志、健康报告与诊断包都不会暴露数据库密码。
6. 从未注册写入源代码审计中删除 Postgres/MySQL 的十条例外。
7. 在发布与迁移文档中明确兼容性边界和操作者修复路径。

## 非目标 {#non-goals}

- 在当前 KV 接口中同时支持 DSN 与数据库离散字段；
- 自动从旧离散字段生成 DSN；
- 重写共享 KV 分词器；
- 在本补丁中改变 `FetchEnabledTargets` 的 fail-fast 语义；
- 静默跳过已启用的数据库 target，再以残缺通知覆盖继续运行；
- 删除 PostgreSQL 或 MySQL notification target；
- 删除为解码和识别不受支持输入所需的旧结构体字段。这些字段仍位于在线构造器共用的 target 参数结构上；构造器中的离散字段连接串合成代码无法从当前 KV 配置到达，但这些字段不能重新成为受支持的配置 key。
- 修复其他八个旧通知 setter 被忽略的错误。它们原有的静默跳过行为在这次狭窄的数据库迁移补丁中保持不变，必须另做审计和设计决策。

## 功能需求 {#functional-requirements}

### 当前配置 {#current-configuration}

1. `notify_postgres` 接受 `connection_string`；`notify_mysql` 接受 `dsn_string`。
2. 五个离散 key 继续保持未注册，并被当前配置命令拒绝。
3. 现有完整连接串必须继续支持数据库驱动语法，包括值内部出现 `host`、`port`、`user`、`password`、`database` 等词的情况。
4. 不增加新的公共环境变量或 KV key。
5. 已声明的旧变量 `MINIO_NOTIFY_POSTGRES_HOST`/`PORT`/`USERNAME`/`PASSWORD`/`DATABASE` 及其 MySQL 对应形式没有接入当前解析，继续作为不受支持的形式，也不得在文档中被描述成完整连接串变量的可用替代。

### 旧配置迁移 {#legacy-migration}

1. 旧 target 未启用时，`SetNotifyPostgres` 必须直接返回，不生成 target。
2. 对已启用 target，`SetNotifyPostgres` 必须要求非空 `ConnectionString`，并且只写已注册的 Postgres key。如果规范连接串与离散字段同时存在，以规范连接串为准，所有离散值都被丢弃。
3. `SetNotifyMySQL` 对 `DSN` 执行同样规则。
4. 两个 helper 都不得写出 `host`、`port`、`username`、`password`、`database`。
5. 缺少规范连接串时，必须返回带类型或包装上下文的迁移错误，指出子系统与 target 名称。
6. `cmd/config-migrate.go` 必须检查并传播两个 helper 的错误，禁止忽略。
7. 任一 helper 失败后，都不得启用或持久化半迁移配置。
8. 错误可以指出所需 key 和修复动作，但不得包含任何连接字段值。
9. 传播的类型化迁移错误必须中止服务器启动，尤其不得落入 `initConfigSubsystem` 中 “some features may be missing” 的非致命日志路径，也不得进入可重试错误循环。
10. 已提供规范连接串的校验错误同样遵守启动致命和保密规则；包装错误只能增加 target 上下文，不能重复 DSN 或其组成部分。

推荐错误形式：

```text
notify_postgres:archive uses unsupported legacy discrete connection fields;
set connection_string before migrating to SILO
```

### 操作者修复路径 {#operator-remediation}

遇到错误的操作者必须选择一条明确修复路径。这既适用于首次切换到 SILO，也适用于升级已经运行 SILO 的部署：旧配置迁移结果不会持久化，因此同一份旧 JSON 来源可能在每次启动时重新进入迁移。一个当前仍能启动、但通知已经静默失效的部署，在升级到修复版本后会直接启动失败，直到来源配置被修正。

1. 使用兼容的中间 MinIO 版本，把旧字段替换成 `connection_string` 或 `dsn_string`，验证 target 后再迁移到 SILO；
2. 禁用或删除旧数据库 target，迁移服务器，再用规范连接串重建 target；
3. 对全新 SILO 安装，直接使用规范连接串创建 target，不经过旧配置迁移。
4. 对仍在读取旧 JSON 文件的现有 SILO 部署，先停留在上一个可运行版本，备份来源配置，再转换、禁用或删除数据库 target，然后启动修复版本；不要删除或改写无关配置。

文档不得暗示离散字段 target 会被自动转换。

## 可用性权衡 {#availability-trade-off}

这个决策有意把一种不受支持配置的“降级启动”变成“启动硬失败”。可用性代价是真实的：一台此前仍能提供对象读写、但全部通知已经静默死亡的服务器，在修复后可能拒绝启动。

我们接受这个代价，因为对象服务表面健康、已配置事件出口却全部消失，会造成静默且可能无法补救的下游数据丢失。SILO 是一个迁移边界显式的新 fork，而离散形式从 2020 年起就已废弃。一个致命、可操作的迁移前置条件，比一次看似成功却缩减通知覆盖的升级更安全。发布注记必须突出这个启动行为，不能把它藏在内部迁移清理里。

## 安全要求 {#security-requirements}

1. 不支持输入的错误不得格式化输出旧参数结构或其中任何值。
2. 测试必须使用哨兵密码，并断言返回错误和捕获日志中都不存在它。
3. 迁移输出只能包含已注册的敏感连接串 key，不能出现独立 `password` key。
4. 如果受影响部署曾在修复前导出并分享诊断包，应将数据库密码视为可能泄露并进行轮换。

## 备选方案 {#alternatives}

### 注册并解析离散字段 {#alternative-register}

**优点：** 保留旧来源形式，并复用现存参数字段。  
**拒绝原因：** 注册会把常见字段名暴露给共享分词器，破坏引号内的完整连接串；而且这些字段早在 2020 年就已废弃，重新注册等于反向扩大公共配置面。

### 迁移时自动生成规范连接串 {#alternative-synthesize}

**优点：** 兼容仅使用离散字段的旧安装。  
**拒绝原因：** 这会为过时输入建立永久代码与测试责任，包括 PostgreSQL 引用、MySQL DSN 格式、socket/IPv6 行为、默认值与未来驱动漂移。对于迁移边界显式的新 fork，这个收益不足以覆盖长期维护面。

### 只跳过不支持的 target {#alternative-skip}

**优点：** 对象存储服务与其他通知 target 可以继续运行。  
**拒绝原因：** 静默丢弃已经配置的事件出口可能造成不可见、不可恢复的事件丢失。清晰的迁移失败，比一次通知覆盖缩水却看似成功的升级更安全。

### 修改全局通知 fail-fast 行为 {#alternative-fail-fast}

**优点：** 限制未来非法 target 的故障半径。  
**本次拒绝原因：** 它既不能修复数据库 target，也不能关闭凭据暴露路径，还会改变全系统错误语义。可另立独立设计和运维契约评估。

### 删除数据库通知 target {#alternative-remove-targets}

**优点：** 删除全部数据库专用维护面。  
**拒绝原因：** 这些 target 仍然有用且相对自洽。缺陷属于过时配置形式，不属于通知能力本身。

## 实现范围 {#implementation-scope}

服务端改动应保持狭窄：

1. 修改 `internal/config/notify/legacy.go`：两个数据库 setter 只输出规范已注册 key；已启用但没有规范连接串时明确拒绝。
2. 修改 `cmd/config-migrate.go`：传播两个数据库 helper 的错误，并补充子系统与 target 上下文。
3. 定义类型化数据库迁移错误，修改 `cmd/server-main.go`，让 `initConfigSubsystem` 将其作为致命错误返回，而不是记录后忽略；该错误必须保持不可重试。
4. 本补丁不改变其他八个旧通知 setter 错误被忽略的现状；将其留给独立审计，不能暗中扩大 #53。
5. 从 `knownUnregisteredWrites` 删除 Postgres/MySQL 十项；除非存在另一个独立且有充分理由的旧例外，否则这个棘轮应当归零。
6. 增加聚焦的迁移、启动、校验、保密和共存测试。
7. 更新 `silo.pgsty.com` 的数据库通知与迁移文档。

补丁不得注册旧 key、修改通用分词器，也不得重构无关通知 target。

## 验收标准 {#acceptance-criteria}

只有以下证据全部成立，才算实现完成：

1. 含完整连接串的旧 PostgreSQL target 可以迁移，通过 `CheckValidKeys`，并由 `GetNotifyPostgres` 原样返回连接串。
2. 含完整 DSN 的旧 MySQL target 完成同等验证。
3. 两类已启用离散字段 target 都在 target 初始化前失败；错误包含子系统与 target 名称，给出可操作修复建议，且服务器启动中止。
4. 缺少连接串和畸形连接串的错误都不包含哨兵 host、用户名、密码、数据库或 DSN 值。
5. 未启用的离散旧 target 不生成配置项，也不阻塞迁移。
6. 迁移后的 KVS 不含十个离散 key，包括空值形式。
7. 旧 target 同时包含规范连接串与冲突离散值时，只迁移规范连接串，所有输出 KVS 值中都不存在离散哨兵值。
8. 使用真实 `DefaultPostgresKVS` 和 `DefaultMySQLKVS` key 集的 `SetKVS` 回归测试，能够接受引号内包含 `port=`、`host=`、`password=` 的完整连接串。
9. 包含健康 Webhook、Kafka、NATS target 的配置不能再带着非法迁移数据库 target 进入 `FetchEnabledTargets`：`readConfigWithoutMigrate` 返回错误，不返回、不持久化、也不启用任何半成品配置，启动路径随后因该类型化错误中止。
10. `initConfigSubsystem` 返回类型化迁移错误，既不能记录后继续，也不能进入可重试循环。
11. `knownUnregisteredWrites` 不再包含 Postgres/MySQL 例外。
12. 以下验证全部通过：

    ```sh
    go test ./internal/config/notify ./internal/config ./internal/event/target -count=1
    go test -v ./cmd -run 'Test(ReadConfigWithoutMigrate|InitConfigSubsystem)' -count=1
    git diff --check
    ```

    `cmd` 的详细输出必须显示两个前缀的测试确实执行；零匹配警告视为验收失败。服务端常规 CI 测试也必须通过；文档仓库执行 `make check`。

## 发布与兼容性声明 {#release}

发布注记必须把它描述为一个被正式执行的兼容性边界：

> SILO 数据库通知要求 PostgreSQL 使用 `connection_string`、MySQL 使用 `dsn_string`。2020 年前的离散 `host`/`port`/`username`/`password`/`database` 形式不会被迁移；请在切换到 SILO 前转换或重建这些 target。

仍使用旧格式来源配置、但已经运行 SILO 的部署同样受影响：从这个版本开始，只要存在已启用的旧数据库 target，服务器就不会启动，直到它被转换、禁用或删除。

只有当修复进入已发布的服务端 tag 后，Issue 才能关闭。补丁合入、本地网站构建、正式发布是三个不同的完成门槛。

## 审阅记录 {#review-record}

Claude Fable 5 于 2026-08-23 使用 `xhigh` effort 审阅初稿，结论为 **approve with required changes**。必需校准已经吸收：启动致命错误传播扩展到 `initConfigSubsystem`；覆盖已经运行 SILO 的部署；明确可用性代价；补充规范连接串优先级、无效旧环境变量、其他 helper 错误范围和可执行测试。

同一模型随后完成了基于当前源码的最终复核。最终结论：**approve**，没有 blocking finding。复核确认中英文记录语义对齐，需求可以在当前服务端代码树上实现，验收标准覆盖启动、迁移、解析器回归和凭据保密边界。
