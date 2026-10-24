---
title: "SN-2026-019：通知子系统配置键注册缺失与校验报错脱敏"
linkTitle: "SN-2026-019：通知配置键修复"
date: 2026-08-04
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "解析未注册的通知配置键如何导致配置校验失败、拖垮全局通知目标并在报错信息中回显敏感凭据（SN-2026-019）。"
url: "/zh/blog/security/notify-keyspace-registration/"
tags: ["Security", "Notifications", "Configuration", "NATS", "AMQP", "PostgreSQL", "MySQL", "SILO"]
---

**`SN-2026-019`** 涵盖了 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（提交 `162ded343` 与 `672c07a0f`，[`pgsty/silo#39`](https://github.com/pgsty/silo/issues/39)）修复的一类通知子系统配置缺陷：通知解析器与旧版配置迁移代码读写了未在 `Default*KVS` 中注册的配置键，`CheckValidKeys` 在校验失败时将包含敏感凭据的原始 `key=value` 拼入错误消息，且 `FetchEnabledTargets` 在遇到首个校验错误时会直接中止全部通知目标的加载。随后在 [Server 20260903](/zh/blog/design/notify-url/)（`f1ba68358`）中，由本次 AST 审计顺带揪出的 PostgreSQL 与 MySQL 离散连接字段被正式废弃，统一收敛为 `connection_string` 与 `dsn_string`。

## 结论先行 {#summary}

1. **四处独立维护的代码面发生漂移**：在通知配置子系统中，`Default*KVS`（合法键集合）、`Help*`（帮助文档与敏感级别分类）、`GetNotify*`（配置解析）与 `SetNotify*`（旧配置迁移）长期靠手工同步，缺乏一致性校验。
2. **单个目标报错会拖垮全局通知目标**：`FetchEnabledTargets` 按顺序校验所有通知子系统，一旦遇到首个错误便直接返回，导致全局通知目标列表保持为 `nil`，使正常的通知目标一并失效。
3. **配置校验报错回显了敏感值**：当 `CheckValidKeys` 拒绝未知或拼写错误的键时，旧代码使用 `kv.String()` 格式化错误，将完整的 `key=value`（含密码或凭据内容）直接输出到日志和客户端终端。
4. **通过 AST 审计测试锁死不变量**：Server `20260804` 补齐了 NATS 与 AMQP 缺失的配置键、在 `CheckValidKeys` 报错中剥离键值、扩展了 `HasSensitiveKeys` 脱敏范围，并新增编译期 AST 审计测试，强制要求 `cmd/config/notify` 读写的所有配置键必须在 `Default*KVS` 中注册。

---

## 一条令人困惑的故障报告 {#the-report}

本次排查始于社区用户 `kuldeep-link11` 报告的一个离奇现象：运维人员执行 `mc admin config set us notify_nats:FITCHECK address="..." subject="..."` 时，服务端却报错指向了另一个完全不相干的目标 `notify_nats:ONE`，并且报出了两个当前命令根本没有传入的键（`nkey_seed= tls_handshake_first=off`）：

```text
Error: Invalid key/value pair 'nkey_seed= tls_handshake_first=off' found in subsystem 'notify_nats:ONE'
```

为什么修改 `FITCHECK` 会报出 `ONE` 上从未手敲过的两个键？排查发现这是两个机制叠加的结果：

1. **`mc admin config set` 的分词器吞字效应**：`internal/config/parser.go` 中的 `kvFields` 仅根据 `DefaultKVS` 中已注册的键名进行分词。当用户在命令行传入未注册的键时，`kvFields` 不会将其识别为新键的起点，而是将 `"nkey_seed=..."` 静默吞入前一个合法键（如 `subject`）的值中。
2. **旧配置迁移逻辑向 `notify_nats:ONE` 写入了未注册键**：在此前版本升级或配置持久化的过程中，旧版配置迁移函数 `SetNotifyNATS`（`cmd/config/notify/legacy.go`）直接构造了 KVS 结构体（绕过了 `kvFields` 分词），将 `nkey_seed` 和 `tls_handshake_first` 作为独立键写入了 `notify_nats:ONE`。当运维人员随后修改 `notify_nats:FITCHECK` 时，`validateConfig` 重新校验集群中存储的所有目标，结果在 `notify_nats:ONE` 上撞上了 `CheckValidKeys` 报错。

---

## 同一个常量混用在了两个命名空间 {#the-constant}

检查 `internal/config/notify/target/nats.go` 时，我们在 `nkey_seed` 旁边立刻发现了第二个隐患：

```go
const (
    NATSAddress = "address"
    NATSSubject = "subject"
    ...
    EnvNATSAddress         = "MINIO_NOTIFY_NATS_ADDRESS"
    EnvNATSSubject         = "MINIO_NOTIFY_NATS_SUBJECT"
    NATSUserCredentials    = "MINIO_NOTIFY_NATS_USER_CREDENTIALS"
)
```

2024 年 2 月 PR [`minio/minio#19139`](https://github.com/minio/minio/pull/19139) 为 NATS 引入用户凭据文件支持时，作者将常量 `NATSUserCredentials` 放在了 `Env*` 常量块末尾，赋值为 `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"`，随后将其**同时**用作环境变量名和 `DefaultNATSKVS` 中的 KVS 配置键名。结果，运维人员通过 `mc admin config set notify_nats user_credentials=/path/to/creds` 配置时会因键名未知而被拒绝；反而是字面量 `MINIO_NOTIFY_NATS_USER_CREDENTIALS=/path/to/creds` 成了 `DefaultNATSKVS` 在持久化配置中期待的键名。

---

## 四个缺乏协同的配置面 {#the-class}

梳理 `cmd/config/notify/` 下全部十个通知目标可以发现，每个目标都分散在四个平行的代码面上：
- `Default*KVS`（`cmd/config/notify/config.go`）：由 `CheckValidKeys` 强制校验的合法键清单；
- `Help*`（`cmd/config/notify/help.go`）：面向用户的帮助说明及敏感类型标注（`Sensitive` / `Secret`）；
- `GetNotify*`（`cmd/config/notify/parse.go`）：读取 KVS 配置键与 `MINIO_NOTIFY_*` 环境变量；
- `SetNotify*`（`cmd/config/notify/legacy.go`）：将旧版 JSON 配置结构体序列化为 KVS 键值对。

在 NATS 和 AMQP 中，共有四个配置键在这四个代码面之间发生了漂移：

| 目标子系统 | 配置键 | 引入来源 | `Default*KVS` | `Help*` | `GetNotify*` | `SetNotify*` | 故障表现 |
|---|---|---|---|---|---|---|---|
| `notify_nats` | `user_credentials` | [`#19139`](https://github.com/minio/minio/pull/19139) (2024-02) | 误注册为 `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | 缺失 | 读取 `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | 写入 `MINIO_NOTIFY_NATS_USER_CREDENTIALS` | 执行 `mc admin config set` 传入 `user_credentials` 被拒 |
| `notify_nats` | `nkey_seed` | [`#21231`](https://github.com/minio/minio/pull/21231) (2025-05) | 缺失 | 缺失 | 读取 `nkey_seed` | 写入 `nkey_seed` | 持久化配置无法通过 `CheckValidKeys` |
| `notify_nats` | `tls_handshake_first` | [`#21008`](https://github.com/minio/minio/pull/21008) (2025-02) | 缺失 | 已包含 | 读取 `tls_handshake_first` | 写入 `tls_handshake_first` | 持久化配置无法通过 `CheckValidKeys` |
| `notify_amqp` | `immediate` | 初始 KVS 迁移 | 缺失 | 缺失 | 读取 `immediate` | 将 `cfg.Immediate` 误写入 `AmqpInternal`！ | `immediate` 被拒；且 `SetNotifyAMQP` 用 `cfg.Immediate` 覆盖了 `internal` |

特别注意表格最后一行的 AMQP 缺陷：`cmd/config/notify/legacy.go` 中的 `SetNotifyAMQP` 存在一处复制粘贴笔误，把 `strconv.FormatBool(cfg.Immediate)` 写到了 `target.AmqpInternal` 键下，而真正的 `cfg.Internal` 字段则完全丢失。

---

## 爆炸半径放大器：全有或全无的目标加载机制 {#amplifier}

为什么一个未启用的 `notify_nats:ONE` 目标报错会造成严重后果？在 `cmd/config/notify/parse.go` 中，`FetchEnabledTargets` 会依次加载全部十类通知子系统（`amqp`、`elasticsearch`、`kafka`、`mqtt`、`mysql`、`nats`、`nsq`、`postgres`、`redis`、`webhook`）。只要其中**任何一个**子系统在 `CheckValidKeys` 中返回错误，`FetchEnabledTargets` 就会立即中止并返回错误，不会填充全局活跃通知目标映射表。

这意味着，哪怕某个早已停用的 `notify_nats` 历史条目里残留了一个未注册键，也会导致实例重启或配置重载时全局通知目标列表置空，使正在运行的 Kafka、Webhook 等所有桶通知静默中断，直到管理员手工清理该配置段为止。

我们曾评估是否要将 `FetchEnabledTargets` 改为按子系统隔离错误（跳过损坏的子系统、保留其余目标运行），但最终否决了这一改法：在 SILO 中，配置校验在设计上就是全有或全无的原子操作，以便 `mc admin config set` 能够明确拦截错误配置而非部分生效。补齐合法键注册即可消除误报，无需削弱配置校验的原子性契约。

---

## 修复键注册与敏感级别分类 {#the-fix}

提交 `162ded343` 修复了 NATS 与 AMQP 的键空间缺陷：

1. **拆分配置键常量与环境变量常量**：`target.NATSUserCredentials` 修正为 `"user_credentials"`，同时新增 `target.EnvNATSUserCredentials = "MINIO_NOTIFY_NATS_USER_CREDENTIALS"`。
2. **在 `DefaultNATSKVS` 与 `DefaultAMQPKVS` 中补齐四个键**：将 `user_credentials`、`nkey_seed`、`tls_handshake_first` 注册到 `DefaultNATSKVS`，将 `immediate` 注册到 `DefaultAMQPKVS`。
3. **补全 `HelpNATS` 与 `HelpAMQP`**：为 `user_credentials`、`nkey_seed` 和 `immediate` 补齐帮助项。由于 `user_credentials` 和 `nkey_seed` 接收的都是服务端本地文件路径（与 `client_key` 一致），我们将二者标记为 `config.Sensitive` 而非 `config.Secret`。
4. **修复 `SetNotifyAMQP`**：令 `SetNotifyAMQP` 将 `cfg.Internal` 写入 `target.AmqpInternal`，将 `cfg.Immediate` 写入 `target.AmqpImmediate`。

---

## 对存量 NATS 配置的窄化向后兼容 {#tolerance}

如果存量集群在 `20260804` 之前为了绕开 `#19139`，已经在持久化配置中写入了字面量键 `MINIO_NOTIFY_NATS_USER_CREDENTIALS=/path/to/creds`，该怎么办？

如果仅仅把 `NATSUserCredentials` 改名为 `"user_credentials"`，这些存量集群在升级后首次加载配置时就会被 `CheckValidKeys` 判定为包含非法键——从而直接触发上一节所述的 `FetchEnabledTargets` 全局通知中断。

在设计向后兼容路径时，我们发现了 `internal/config` 中两个同名函数的细微陷阱：
- **包级自由函数** `config.CheckValidKeys(subSys, kvs, defaultKVS, deprecatedKeys...)` 接受可选的废弃键变长参数（`deprecatedKeys`），并在加载校验时放行这些键；
- **`KVS` 的方法** `kvs.CheckValidKeys(subSys, defaultKVS)` 内部调用了 `CheckValidKeys(subSys, kvs, defaultKVS)`，**没有**透传任何废弃键参数。

因此，我们在 NATS 加载路径（`GetNotifyNATS`）中改用包级函数 `config.CheckValidKeys` 并将 `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"` 列入废弃键白名单，同时在解析 `UserCredentials` 时规定了确定的优先级顺序：
1. `MINIO_NOTIFY_NATS_USER_CREDENTIALS` 环境变量（最高优先级）；
2. `user_credentials` KVS 配置键；
3. 历史遗留的 `MINIO_NOTIFY_NATS_USER_CREDENTIALS` KVS 配置键（仅当 `user_credentials` 为空时兜底）。

---

## 校验报错脱敏与敏感键加固（`SN-2026-019`） {#redaction}

在 `20260804` 之前，无论是 `config.CheckValidKeys` 还是 `KVS.CheckValidKeys`，在拼接非法键报错信息时都会直接调用 `kv.String()`（即输出完整的 `key=value`）。如果管理员在设置配置时不小心拼错了敏感键名（例如把 `password` 敲成 `pasword=Hunter2`，或把 `auth_token` 敲成 `auth_tokn=eyJ...`），又或者旧版迁移函数写入了未注册的凭据键，报错信息就会把明文密码原样回显到终端响应和服务端错误日志中。

提交 `162ded343` 修改了这两个 `CheckValidKeys` 函数，使其在报错时**仅输出键名**（`kv.Key`），不再输出 `kv.Value`。

随后在提交 `672c07a0f` 中，我们进一步审查了用于在 `mc admin config get` 导出和健康诊断包（health-diagnostics）中掩码敏感值的 `config.HasSensitiveKeys`（`internal/config/config.go`），将其匹配范围扩展至通知、身份认证与 KMS 子系统使用的全部凭据键名（`password`、`auth_token`、`secret_key`、`client_secret`、`nkey_seed`、`user_credentials`、`sasl_password`、`connection_string` 与 `dsn_string`）。

---

## 用 AST 审计测试锁死注册不变量 {#the-audit}

为了从根源上杜绝 `Default*KVS`、`parse.go` 与 `legacy.go` 再次出现手工同步遗漏，我们在 `cmd/config/notify/config_audit_test.go` 中编写了基于 `go/ast` 的静态审计测试。该测试会解析 `parse.go` 和 `legacy.go` 的抽象语法树，追踪每一处 `kvs.Get(...)` 和 `kvs.Set(...)` 调用所引用的 `internal/config/notify/target` 字符串常量，并断言这些键全部已在对应的 `Default*KVS` 中注册。

在对审计测试本身复核时，我们发现并堵上了初版测试的两个盲区：

1. **反向覆盖与数量下界断言**：如果只断言 `parse.go ⊆ Default*KVS`，万一未来语法树结构变化导致 AST 遍历器一个键都没提取出来，空集也是任何集合的子集，测试会假阳性通过！因此我们加上了反向检查，要求 `Default*KVS` 中注册的每一个键（除 `enable`、`comment` 等通用键外）都必须在 `parse.go` 中被读取，并为每个子系统设置了提取键数量下界。
2. **无类型复合字面量（Untyped Composite Literals）**：在 `legacy.go` 中，部分迁移函数并非调用 `kvs.Set()`，而是直接用无类型复合字面量 `{Key, Value}` 构造 `config.KVS{...}` 切片。当我们把 AST 遍历器扩展到检查 `config.KVS` 复合字面量后，测试立刻在现有代码库中抓出了另一处潜伏缺陷。

---

## AST 审计顺藤摸瓜抓出的问题：PostgreSQL 与 MySQL 离散连接键 {#followups}

一旦 AST 遍历器开始检查 `legacy.go` 中的 `config.KVS` 复合字面量，它当即报出 `SetNotifyPostgres` 与 `SetNotifyMySQL` 存在未注册键写入：这两个函数各自写入了 `host`、`port`、`username`、`password`、`database` 五个离散配置键，且 `GetNotifyPostgres` / `GetNotifyMySQL`（`parse.go`）在 `connection_string` / `dsn_string` 为空时也会读取这五个键，但它们**完全没有**在 `DefaultPostgresKVS` 和 `DefaultMySQLKVS` 中注册！

更糟糕的是，正因为 `password` 未在 `DefaultPostgresKVS` 或 `DefaultMySQLKVS` 中注册，在 `162ded343` 之前，任何传入 `password=...` 或触发旧版 PostgreSQL/MySQL 配置迁移的操作都会撞上 `CheckValidKeys`，并在错误消息中把数据库明文密码直接打印出来。

我们分两步在两个版本中彻底解决了这一历史包袱：
- **Server 20260804（`672c07a0f`）短期止血**：在 `DefaultPostgresKVS` 和 `DefaultMySQLKVS` 中补注册 `host`、`port`、`username`、`password`、`database`（并在 `HelpPostgres` / `HelpMySQL` 中将 `password` 标记为 `Secret`），确保存量配置与新的 AST 审计不变量立即自洽。
- **[Server 20260903](/zh/blog/design/notify-url/)（`f1ba68358`）架构清理**：同时维护两套数据库连接配置方式（`connection_string` 与离散的 `host`/`port`/`username`/`password`/`database` 字段）会导致 `SetNotifyPostgres` 和 `SetNotifyMySQL` 在配置读写往返时用空的离散字段覆盖掉合法的 `connection_string`。因此 Server `20260903` 从 `Default*KVS`、`Help*`、`parse.go` 与 `legacy.go` 中彻底退役了这五个离散字段，统一收敛为使用 `connection_string`（PostgreSQL）与 `dsn_string`（MySQL）。

---

## 明确不做项 {#declined}

- **不在本补丁中改动 `kvFields` 分词边界规则**：若将 `kvFields` 改为按任意 `key=value` 切分而非仅识别 `DefaultKVS` 中的已知键，会改变值内部包含未加引号空格（例如 SQL 语句或通知主题）时的解析行为。在通过 AST 审计保证 `Default*KVS` 完整注册后，合法配置键均可被 `kvFields` 正确识别。
- **不削弱 `FetchEnabledTargets` 的快速失败校验**：如[爆炸半径放大器](#amplifier)所述，配置校验在所有子系统间保持原子性。

## 审查记录 {#review}

代码审查验证了 AST 审计测试的反向覆盖下界断言、无类型 `config.KVS` 复合字面量扫描、`CheckValidKeys` 报错脱敏（`162ded343`）以及 `HasSensitiveKeys` 敏感凭据键覆盖（`672c07a0f`）。

## 总结 {#closing}

随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（`162ded343` 与 `672c07a0f`）发布并在 [Server 20260903](/zh/blog/design/notify-url/)（`f1ba68358`）完成离散键收敛后，所有通知子系统配置键均由 AST 静态测试锁死在 `Default*KVS` 中，且非法键报错不再回显配置值。
