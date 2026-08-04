---
title: "解析器认识，Schema 不认：足以带走全部通知的配置键"
linkTitle: "通知键空间注册缺口"
date: 2026-08-04
author: "冯若航"
description: "NATS 的 JWT 凭据被读取它的那台服务器判为非法键。同样的缺口被写进了旧配置迁移，升级后的配置在每次启动时验证失败——而一个子系统失败就会清空整张通知列表。上游三个功能 PR 各自忘掉了同一次注册；第四个表面则在无声地写错值。"
tags: [安全, Bucket Notifications]
weight: 100
draft: false
url: "/zh/blog/security/notify-keyspace-registration/"
---

**状态：** 已在本地 `pgsty/minio` 分支修复，提交 `cc78701a1`，**尚未发布**
**定级：** 配置 Schema 一致性与可用性问题，**不是漏洞**；附带一项防御性加固（验证报错不再回显凭据值）
**影响范围：** `notify_nats` 的 JWT/NKey/TLS-handshake-first 选项、`notify_amqp` 的 `immediate`，以及任何带着启用状态 NATS 目标从 2020 年前配置迁移上来的部署——它的失败会连带压掉**所有**通知后端
**跟踪：** `pgsty/minio` issue #39

> 本文点名了相邻代码中两个尚未修复的可用性缺陷（Postgres/MySQL 迁移写入、`kvFields` 键名吞并）。两者都不可利用——破坏的是操作者自己的配置，要么响亮要么根本不发生——且都已写进已提交审计测试的允许清单。发布无需额外扣留，等版本发布即可。

## 结论先行 {#summary}

- `notify_nats` 的三个选项——`user_credentials`、`nkey_seed`、`tls_handshake_first`——和 `notify_amqp` 的 `immediate`，**解析器在读，旧配置迁移在写，却没有任何地方注册**。`CheckValidKeys` 拒绝的恰恰是 `GetNotifyNATS` 需要的。
- 一个常量身兼二职。`target.NATSUserCredentials` 的值是 `"MINIO_NOTIFY_NATS_USER_CREDENTIALS"`，躺在环境变量常量块里，却**既**被当作环境变量名**又**被当作配置键使用。凭据文件认证的 snake_case 配置键在整个程序里根本不存在。
- 报告者的报错不是他的命令触发的，而是来自**旧配置迁移**：用修复前的迁移代码可以**逐字节**复现 issue 里的错误文本，连他的命令从未提过的 `notify_nats:ONE` 目标名都对得上。迁移只把存储写坏一次；此后**每次启动**验证都会拒绝它。
- 爆炸半径来自放大器：`FetchEnabledTargets` 在第一个坏子系统上快速失败，唯一的调用方只记一条日志，全局目标列表保持 `nil`——一条坏掉的 NATS 配置就把 Kafka、webhook、MQTT 等一切通知无声关停。
- **继承自上游。** 三个功能 PR——#19139（2024-02，`user_credentials`）、#21008（2025-04，`tls_handshake_first`）、#21231（2025-04，`nkey_seed`）——每个都加了解析器和环境变量，每个都跳过了 Schema。上游已归档；缺陷与义务都由 fork 继承。
- 修复内容：注册这些键；拆开一身二职的常量；修正迁移——包括一个把 `immediate` 的值写进 `internal` 键的隐蔽同胞 bug；仅在加载路径容忍磁盘上已有的旧拼写；让**两个** `CheckValidKeys` 形态的报错都不再回显值；再装上一个 AST 审计，把这一整类缺陷在全部十个通知子系统里机械地封死。
- 墨迹未干，审计就抓到了下一例：Postgres/MySQL 的旧配置迁移会写入**五个**未注册键，其中一个是明文数据库密码。已记录、进只减不增的允许清单、列为后续事项。

## 报错点名了一个没人问过的目标 {#the-report}

报告（issue #39，报告者 `kuldeep-link11`，环境是使用 JWT operator/accounts 认证的 NATS 集群）是一次干净的复现：给 `notify_nats` 配置凭据文件，看它被弹回来。

```console
$ mc admin config set us notify_nats:FITCHECK \
    address=nats-1:4222 subject=events.object.created \
    MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds \
    jetstream=off queue_dir=/data/queue-fitcheck queue_limit=100000

mc: <ERROR> ... found invalid keys
    (MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds
     nkey_seed= tls_handshake_first=off ) for 'notify_nats:ONE' sub-system,
    use 'mc admin config reset myminio notify_nats:ONE' to fix invalid keys
```

这条报错里有两处怪异，是这条命令解释不了的。非法键列表里有 `nkey_seed=` 和 `tls_handshake_first=off`——用户根本没传过；被拒绝的子系统是 `notify_nats:ONE`，而命令配置的是 `notify_nats:FITCHECK`。

第二处怪异就是整个案子。评审者证明了 `mc admin config set` 这条路径**根本携带不了未注册键**：服务端分词器 `kvFields` 是按*已注册*键名去切分输入行的，未知 token 从来不会成为键——它会被吸进前一个键的值里。直接探测：

```
输入:  subject=s MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/x.creds
存储:  subject="s MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/x.creds"
```

所以拒绝不可能是针对命令行的。那是 `validateConfig` 在横扫整个子系统时，绊倒在一个**早已存进存储、名叫 `ONE` 的另一个目标**上——它身上带着全部三个坏键。整棵代码树里只有一条路径会把这几个键名写进存储：旧配置迁移。用修复前的迁移代码驱动一个启用状态、名为 `ONE` 的 NATS 目标，issue 里的错误文本**逐字符**复现——连空的 `nkey_seed=` 都一样，那正是旧配置里没有 NKey 时迁移写出来的样子。

这就改写了事故的性质。这不是"服务器拒绝了我的命令"，而是：*一份旧配置被迁移过一次，迁移写下了三个验证器不认的键，从那以后这份存储每次启动都验证失败*——并且因为失败只被记日志然后吞掉，它无声地压掉了其它所有通知目标。报告者的命令只是走进了爆炸半径，接住了别人的报错。

## 一个常量，两种含义 {#the-constant}

继承下来的声明（`internal/event/target/nats.go`，修复前）：

```go
const (
    NATSAddress  = "address"
    NATSSubject  = "subject"
    NATSUsername = "username"
    NATSPassword = "password"
    NATSNKeySeed = "nkey_seed"            // 配置键——形状正确
    // ...
    EnvNATSUsername     = "MINIO_NOTIFY_NATS_USERNAME"
    NATSUserCredentials = "MINIO_NOTIFY_NATS_USER_CREDENTIALS"  // ← 在 Env 块里
    EnvNATSPassword     = "MINIO_NOTIFY_NATS_PASSWORD"
)
```

`NATSUserCredentials` 起了个配置键的名字，装着环境变量的值，躺在环境变量的货架上。解析器把它**两用**：一次当环境变量去查，一次当配置键去存储 KVS 里读。迁移则拿它当键去*写*。整个程序里不存在 `"user_credentials"` 这个字符串——凭据文件认证的配置键压根没有出生，这正是报告者翻遍文档找不到键名、只好把环境变量名当键传的原因。

一个名字身兼二义，早晚会在其中一义上出错。这里它两头同时错：作为键，它是没注册的垃圾；作为唯一可用的拼写，它教会了用户和迁移代码去写垃圾。

## 四个表面，没有握手 {#the-class}

这套代码里的一个通知选项活在四个必须一致的表面上：**默认值**（`DefaultNATSKVS`——验证接受什么、`mc admin config get` 显示什么）、**帮助**（`HelpNATS`——`mc admin config` 文档写什么）、**解析器**（`GetNotifyNATS`——服务器实际读什么）、**迁移**（`SetNotifyNATS`——升级会写什么）。没有任何机制把它们绑在一起。上游三个功能 PR 每个都更新了解析器和环境变量管线，每个都忘了前两个表面：

| 键 | 解析器读 | 迁移写 | 默认值 | 帮助 | 引入 |
| :-- | :-- | :-- | :-- | :-- | :-- |
| `user_credentials` | 读（经由二职常量） | 写（写成环境变量名） | **无** | **无** | #19139，2024-02 |
| `nkey_seed` | 读 | 写 | **无** | **无** | #21231，2025-04 |
| `tls_handshake_first` | 读 | 写 | **无** | **无** | #21008，2025-04 |
| `immediate`（AMQP） | 读 | *见下* | **无** | **无** | 配置 KV 重写时代 |

AMQP 那一行藏着更安静的同胞。AMQP 迁移没有跳过 `immediate`——它把 `immediate` 的**值写在了 `internal` 键下**，并把 `cfg.Internal` 整个丢掉：

```go
config.KV{
    Key:   target.AmqpInternal,               // 错误的键
    Value: config.FormatBool(cfg.Immediate),  // 正确的值
},
// cfg.Internal：无处安放
```

因为 `internal` *是*已注册的，这一条能通过验证。NATS 的缺口把迁移后的配置弄坏得足够响亮、终归会被发现；AMQP 的缺口则**无声地写错**——迁移出来的 broker 配置带着错误的开关，验收单上却干干净净。同一类缺陷，两种表现：未注册的键失败得干脆，走错门的值错得安静。

## 放大器 {#amplifier}

若没有聚合语义，这一切都配不上"停摆"二字。`FetchEnabledTargets` 遍历十个通知子系统，在**第一个**失败处返回 `(nil, err)`；唯一的调用方记一条日志就继续走，全局通知目标列表保持 `nil`；后续所有查询在 nil 保护下拿到空列表。于是一个被拒的 `notify_nats` 目标就关掉了**全部**桶通知——Kafka、webhook、AMQP、MQTT，一个不剩——只在服务器日志里留一行。

我们考虑过改成按子系统隔离，**决定在本次修复中不改**。跳过坏子系统是对操作者体验的真实行为变更：今天的语义是聚合式响亮失败（全部停摆），已有部署对"验证是全有或全无"的预期是推理过的。重接这套语义是一项值得独立变更的兼容性决策，不该搭注册修复的车——而且注册修好之后，*合法*配置根本不会再触发级联。这一决定已写成 `FetchEnabledTargets` 的文档注释，并用行为固化测试钉住：下一个动它的人要么有意为之，要么动不了。

## 修复 {#the-fix}

约一百行生产代码变更，由九百行测试托着（`cc78701a1`：8 个文件，+1029/−7）。

**注册。** 四个键全部进入所属默认 KVS 和帮助 Schema，摆在操作者会去找的位置（`user_credentials` 挨着 `username`，`nkey_seed` 排在 `token` 后，`tls_handshake_first` 跟在 `tls_skip_verify` 后，`immediate` 挨着 `mandatory`）。注册同时决定可见性：这四个键现在会出现在 `mc admin config get` 的输出里，此前不会。

**常量，拆开。** `NATSUserCredentials` 成为真正的配置键 `"user_credentials"`；新增 `EnvNATSUserCredentials` 承载环境变量字符串。涉及的每一个环境变量名——`MINIO_NOTIFY_NATS_USER_CREDENTIALS`、`_NKEY_SEED`、`_TLS_HANDSHAKE_FIRST`、`MINIO_NOTIFY_AMQP_IMMEDIATE` 及其 `_TARGET` 后缀形态——逐字节冻结：它们是公开接口，全程可用（环境变量一直是可行的绕行方案），现在有测试用**裸字符串字面量**钉住它们，任何 Go 常量的重命名都无法再让它们悄悄漂移。

**帮助标志，循先例。** 两个新 NATS 值都是文件*路径*（`.creds` 文件；NKey 种子文件），故标 `Sensitive` 不标 `Secret`，看齐 `cert_authority`/`client_cert`/`client_key` 而非 `password`/`token`。`Secret` 会连 `mc admin config get` 里都做脱敏——把操作者自己配的路径对他本人藏起来，这正是私钥路径 `client_key` 也从不带它的原因。

**迁移，修正。** `SetNotifyNATS` 现在写真键；`SetNotifyAMQP` 同时写 `immediate = cfg.Immediate` **和** `internal = cfg.Internal`。

如果你今天在修复前的构建上受影响：环境变量路线一直可用；`mc admin config reset myminio notify_nats:<target>` 能以丢失该目标设置为代价解除毒化存储。在修复后的构建上，毒化存储直接恢复加载——见下一节。

## 与旧迁移已经写下的东西共处 {#tolerance}

修好迁移帮的是下一次升级，帮不了旧迁移已经写坏的存储——它们带着字面键 `MINIO_NOTIFY_NATS_USER_CREDENTIALS`，依旧未注册，依旧每次启动都致命。让这些操作者手工重置配置，等于用我们写下的错误惩罚他们。

所以加载路径窄窄地容忍它。验证**仅对 NATS 子系统**接受旧拼写——有测试断言 AMQP 依然拒绝它，容忍成不了通用逃生门——解析器只在真键为空时才回退去读它。优先级是 `env > user_credentials > 旧键`，而且**靠构造成立**而非靠约定：回退结果是作为环境变量查询的*默认参数*传入的。三种次序全部有测试。旧键刻意不进默认值、不进帮助：容忍，但绝不宣传、绝不可能新设（`kvFields` 保证了这一点）。

它的常量是包内字面量，不是 `EnvNATSUserCredentials` 的别名——刻意如此。它命名的是**已经躺在磁盘上的字节**，不能跟着环境变量常量未来的任何改名走。注释就是这么写的。

接线时发现的一个陷阱，值得单独一段，因为它迟早咬人：这套代码里有**两个** `CheckValidKeys`——自由函数和方法——它们的 `deprecatedKeys` 参数含义**相反**。自由函数*容忍*所列的键（跳过）；方法*把它们从合法集合里减掉*（拒绝）。把这处调用从一种形态重构成另一种，会把容忍无声地反转成封禁。这一不对称现已记录在调用点——在给导出 API 改名之外，这是能做到的最好的了。

容忍从写下之日起就带着退役方案：干净的终态是在加载时把旧键改写成 `user_credentials`，然后把容忍和回退一并删除。这就是下文的后续事项 #2——它还能顺手封上容忍留下的一个小洞：未注册键不带 `Sensitive` 标志，被容忍的旧键会把值（一个路径）原样送进健康诊断包，而 `user_credentials` 显示 `*redacted*`。

## 报错里的秘密 {#redaction}

引发这一切的非法键报错，是**连值一起**打印被拒键值对的：`found invalid keys (MINIO_NOTIFY_NATS_USER_CREDENTIALS=/jwt/creds/minio_notifier.creds ...)`。这些路径无伤大雅，机制却不是：任何骑在被拒键上的值——手滑打成 `nkey_sed=<seed>`、遗留 LDAP 键上的 bind 密码——都会落进服务器日志和 `mc` 客户端的终端。

两个 `CheckValidKeys` 形态现在都只打印**键名**，保留原有形状和 `mc admin config reset` 提示。第二处超出了书面任务范围——方法形态服务于 LDAP、OpenID 和策略插件，那里被拒的值可能是真正的 bind 密码——被要求评判这次越界的独立评审说，换他会主动要求这么做：两处一模一样的泄漏只修一处，是半个修复。全仓库范围内没有任何代码从那个字符串里解析值，也没有测试断言旧文本；这一变更是全局的、有意的。

还有一个反向事实值得记录：正是这次脱敏，站在了*下一个*同类缺陷与日志中的凭据之间。下文的后续发现里，Postgres/MySQL 迁移在未注册键下写入明文数据库密码——在脱敏之前的构建上，随之而来的拒绝会把那个密码打印出来。

## 让这一类绝种的护栏 {#the-audit}

注册四个键，修好的是四个键。这一类——四个表面、没有握手——只要没有机制把表面机械地绑在一起，就仍然敞着。所以修复附带一个基于 AST 的审计测试：解析 `parse.go` 与 `legacy.go`，从 `target` 包源码解析常量（没有会腐烂的手工清单），对**全部十个**通知子系统断言：

- 解析器读到的每个键都注册在该子系统的默认值里；
- 迁移写出的每个键都已注册（减去一份显式的、只减不增的允许清单——见下节）；
- 每条帮助条目都指向已注册的键。

对修复前的代码树跑它，恰好在四个已知缺口上失败、别处全绿——这正是它测的是对的东西的红色证明。

对抗评审随后用一组变异攻击装置去打审计本身，依据的是[上一篇文章](/zh/blog/security/duplicate-part-numbers/)论证过的纪律——没看它失败过的护栏只是猜测。九个变异里七个被抓住，**两个漏网**，且都让审计*无声*失明：把解析器的循环变量改个名（读收集器模式匹配了接收者名 `kv`），或把迁移条目换成 Go 惯用的省略式复合字面量（写收集器要求显式的 `config.KV{...}`）。两种情况下收集器返回**空映射**，断言循环迭代零个键，测试空洞地通过。两者都是维护者不会多想一秒的重构；其中之一还是 `gofumpt` 会推着你去做的。

两项加固封住了缺口，每项都做了双向验证——有加固时变异被抓，去掉加固（反事实）空洞通过就回来：

- **反方向的下限断言：**每个*已注册*键必须被*看见在读*。这条今天对全部十个子系统成立——是量出来的，不是假设的，包括在嵌套条件里被读取的废弃 `streaming_*` 键——所以零成本；而失明的收集器现在会换来每个已注册键一条响亮报错（NATS 是 22 条），而不是一次绿色运行。
- **放宽的字面量守卫：**类型既非 `config.KV` 也非 `config.KVS` 的带类型字面量跳过；无类型（省略式）字面量没有类型可查，现在会被检查而非无视。

终局比分：十个变异，十个全抓——装置途中添了一个变体，收敛轮全量重扫。审计还双向执行自己的允许清单——删掉仍需要的条目会失败，条目过期（迁移不再写那个键）也会失败，清单既不能悄悄变长，也不能对现状撒谎。

## 审计接着抓到的东西 {#followups}

写侧检查在两个与 issue #39 毫无关系的子系统上拒绝转绿。`SetNotifyPostgres` 和 `SetNotifyMySQL` 写五个键——`host`、`port`、`username`、`password`、`database`——没有任何默认 KVS 注册它们，也没有任何解析器读它们。这些是 DSN 之前配置形态的遗物，迁移至今还在产出。驱动真实的迁移助手证实了它：迁移后的 Postgres 或 MySQL 通知目标在下次加载时被拒，报 `found invalid keys (host, port, username, password, database)`——和 NATS 同一种失败模式、同样每次启动都发作、同样经由快速失败波及全部通知。而那里的 `password` 是明文数据库密码——正是上文那次脱敏如今挡在日志之外的值。

它在本次变更中**刻意不修**。范围锁定在 NATS 与 AMQP 的缺口上，而正确的处置（把五个键注册为废弃、或停止写出、或两者兼施）是值得独立走一遍红/绿循环的判断题。它被钉在审计的 `knownUnregisteredWrites` 允许清单里，配着只减不增的注释，不可能被悄悄遗忘：哪天有人修好它，过期的清单条目会让测试失败，索要属于自己的删除。

开放事项，截至 2026-08-04 均未进入任何已发布构建：

1. **Postgres/MySQL 迁移的未注册写入**——major；任何带着启用状态的这两类目标从 KV 之前配置迁移上来的部署，每次启动都会发作。
2. **旧 NATS 键的加载时改写**，之后退役容忍与回退；顺带封上被容忍键在健康诊断包中的脱敏缺口。
3. **`kvFields` 键名吞并**——`mc admin config set` 中未知键名会被无声吸进前一个键的值而不是报错。上游既有的老毛病；这回它没保护任何人，早晚会污染谁的 `subject`。

## 评审记录 {#review}

变更在提交前过了三道门：

| 门 | 方法 | 结果 |
| :-- | :-- | :-- |
| 实现者 | 先写测试、对未修改代码树运行；缺失的常量让测试套件**编译失败**，这本身就是常量拆分的红色证明；定向回退产出其余运行期红色 | 每项主张都有红色在案 |
| 独立对抗评审 | 在修复前提交处的分离 worktree；不信报告、逐项重推红色；变异装置攻打审计；优先级边界探针；**从迁移路径逐字节复现报告者的报错** | **REVISE**，两项要求 |
| 收敛轮 | 两项要求全部落地；反事实变异运行（有加固与无加固各跑一遍）证明加固承重；评审重比对 diff、重跑、重变异 | **ACCEPT**，10/10 |

按本系列的老规矩，如实入账：两项要求都不是生产修复里的缺陷。一项是 lint 门（两处英式拼写会让 `make test` 失败——而实现者在修它们时重写的注释又引入了第三处 `dialled`，被同一道门当场抓住；这项要求实时证明了自己）。另一项就是上文的审计失明——护栏的耐久性，不是变更的正确性。评审真正推翻的是事故的起源叙事：迁移路径复现、`ONE` 目标、`kvFields` 吞并证明，全部来自评审者，而它们改变了操作者应当得出的结论——这是一场埋伏在存储配置里的启动期停摆，不是一个 CLI 验证怪癖。

实现者的红色阶段也在修复落地前抓出了自己新测试里的三个 bug，记录在案而非抹平：一个夹具假设存储目标会叠加在默认值之上，而 `config.Merge` 实际是原样透传；一个行为固化测试在 nil HTTP transport 上段错误（`FetchEnabledTargets` 无条件解引用它——对测试不友好，已记录，未修）；还有一版早期草稿把夹具钉在了修复恰好要改名的那个常量上，导致它在修复前也能绿——重写为字面字符串，钉住磁盘上的 Schema 而非 Go 符号。

## 拒绝了的，和留着的 {#declined}

刻意拒绝：

- **`FetchEnabledTargets` 的按子系统错误隔离**——兼容性决策，不搭车（[见上](#amplifier)）。
- **注册或宣传旧键**——加载时容忍，默认值与帮助中缺席，无法新设。
- **修正 `EnvNatsTLSHandshakeFirst` 的怪异大小写**——fork 里的美观性改名是买不来任何东西的 diff 噪音。
- **在本次修复 Postgres/MySQL 迁移**——范围锁定，改钉进允许清单（[见上](#followups)）。

留着的：上面三项后续事项，外加一个外观后果——仍带着被容忍旧键的存储，在加载时改写落地之前，`mc admin config get` 会原样显示那个键。

## 结语 {#closing}

这些键每一个都能通过环境变量完美工作，这正是三个功能 PR 得以发布、过审、被使用，却始终无人注意配置文件那一半接口生来即死的原因。解析器和 Schema 是同一份契约的两份描述，靠手维护，横跨四个表面——两年半里，构建中没有任何东西检查它们是否一致。

如果只允许一句话留下来：**当两个工件必须保持一致、而绑住它们的只有约定，分歧就不是风险，而是日程表**——在它们之间放一台机器，然后变异这台机器，直到你亲眼看它抓住你害怕的那种漂移为止。
