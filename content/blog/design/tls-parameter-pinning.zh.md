---
title: "写死 TLS 参数与握手兼容性"
linkTitle: "TLS 参数与握手兼容"
date: 2026-09-17
lastmod: 2026-09-17
author: "冯若航"
summary: >
  Go 1.27 为什么改动握手、SILO 继承下来的显式算法清单如何让兼容开关变成一纸空文、20260916 的修复覆盖了什么又覆盖不了什么、入口设备对新 ClientHello 发 RST 时全部可选解法，以及为什么「只有运维设了 GODEBUG 才生效」的修复是一次兼容契约变更而不是普通 bugfix。
tags: [设计, TLS, OIDC, 运维, 兼容性]
weight: 5
draft: false
url: "/zh/blog/design/tls-parameter-pinning/"
---

> **状态，2026-09-17。** Go TLS 默认值修复
> [`48e184652`](https://github.com/pgsty/silo/commit/48e1846525cce0a870fec9720cc9bf078fa4bf31)
> 已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布。
> [issue #154](https://github.com/pgsty/silo/issues/154) 的报告人在该版本复测，
> OIDC discovery 仍然是同一条 `connection reset by peer`。
> **该部署的根因至今未确认。** #154 于 2026-09-11 以「补丁已合并」为由关闭，
> 而不是以报告人复测通过为准；这个处理是错的。本文记录修复覆盖了什么、覆盖不了什么、以及必须改变什么。

> **证据类别。** 下文的 Go 行为取自 Go 1.27.1 标准库源码与[官方发布说明](https://go.dev/doc/go1.27)。
> 握手字节数与分支复现来自 #154 调查的合成夹具，记录在
> [Go 1.27 TLS 与 OIDC](/zh/blog/design/go127-tls-oidc-discovery/)。
> 至今没有获得受影响部署的任何取证抓包。

## 先把本质说清楚 {#plain}

TLS 连接的第一句话叫 **ClientHello**，客户端在其中列出自己支持的算法。
很多企业网络会在链路中放一台设备——WAF、TLS 检查设备、负载均衡器——去解析这句话。
其中一部分设备在见到不认识的算法编号时不是忽略，而是**直接重置连接**。

Go 1.27 往这句话里新增了三个编号——ML-DSA 后量子签名方案——一共 **12 个字节**。
用 Go 1.27 重新编译后，SILO 在线上说的话就和 Go 1.26 时不一样了。
报告人 IdP 前面的某个环节不接受它，于是回了 TCP RST。
同一个容器里 `curl` 却正常，因为 curl 用的是 OpenSSL，不会提供这些编号。

Go 预料到了这类兼容问题，给出了逃生开关 `GODEBUG=tlsmlkem=0`。
这个开关有一个前提：**它只在应用没有自行指定算法清单时生效。**
SILO 带着一份从上游继承来的显式曲线清单，而这份清单里恰好有一个后量子条目——
于是开关对我们失效。2026-09-09 的修复删除了这些显式清单，让开关重新生效。

关键的限制就是全部故事：**这个开关能关闭后量子密钥交换（ML-KEM），
关不掉后量子签名（ML-DSA）**，而多出来的 12 个字节正是 ML-DSA。Go 没有为它提供任何开关。
如果某个部署是被 ML-DSA offer 卡住的，这次修复对它毫无作用——这与复测结果一致。

## Go 到底在解决什么问题 {#why-go}

**后量子密钥交换是一条截止线，不是偏好。** 威胁模型是 harvest-now-decrypt-later：
攻击者今天把加密流量录下来，等若干年后有了足够强的量子计算机再解密。
因此机密性必须在这种机器出现**之前**完成迁移，而不是之后。
NIST 于 2024 年定稿 ML-KEM（[FIPS 203](https://csrc.nist.gov/pubs/fips/203/final)）
与 ML-DSA（[FIPS 204](https://csrc.nist.gov/pubs/fips/204/final)），
实际部署形态是混合：`X25519MLKEM768` 同时运行经典 X25519 与 ML-KEM 并合并两个秘密，
因此即便 ML-KEM 被发现缺陷，连接强度也不低于单独的 X25519。
浏览器、CDN 与 SSH 实现自 2024 年起陆续默认启用混合密钥交换，Go 在 1.24 跟进。

**签名不在同一条时间表上。** 签名不会被追溯伪造——2035 年造出的量子计算机
不会让 2026 年签出的握手失效。所以今天 TLS 1.3 里的 ML-DSA 只是**声明支持**，
并非实际依赖。Go 1.27 把 `MLDSA44`、`MLDSA65`、`MLDSA87` 加入默认签名算法列表，
那 12 个字节就来自这里：

```go
// crypto/tls/defaults.go，Go 1.27.1
func defaultSupportedSignatureAlgorithms() []SignatureScheme {
    return []SignatureScheme{
        MLDSA44,        // 0x0904
        MLDSA65,        // 0x0905
        MLDSA87,        // 0x0906
        PSSWithSHA256,
        ECDSAWithP256AndSHA256,
        ...
```

这些编号只在 TLS 1.3 下定义。`isDisabledSignatureAlgorithm` 会在配置无法协商到
TLS 1.3 时将其剔除——如下文所述，这也是应用层对它唯一的杠杆。

## 这个开关本来就不管显式清单 {#contract}

真正把我们坑到的那处变更范围很窄，而且放在上下文里看是讲得通的。Go 1.27 发布说明原文：

> Post-quantum hybrid key exchanges can now be explicitly enabled in
> `Config.CurvePreferences` even if the `tlsmlkem=0` or `tlssecpmlkem=0` GODEBUG
> options are used. **Those options were always meant to only apply to the
> default set used when `Config.CurvePreferences` is nil.**
>
> （后量子混合密钥交换现在可以在 `Config.CurvePreferences` 中显式启用，
> 即使设置了 `tlsmlkem=0` 或 `tlssecpmlkem=0`。**这些选项本来就只适用于
> `Config.CurvePreferences` 为 nil 时所用的默认集合。**）

标准库自 Go 1.24 起就把两条路径写成二选一：

```go
// CurvePreferences ... If empty, the default will be used.
//
// From Go 1.24, the default includes the [X25519MLKEM768] hybrid
// post-quantum key exchange. To disable it, set CurvePreferences
// explicitly or use the GODEBUG=tlsmlkem=0 environment variable.
```

代码里就是一个分支：给了显式清单就原样使用，只有为空时才查默认集合，而 GODEBUG 住在默认那条路上。

```go
// crypto/tls/common.go，Go 1.27.1
func (c *Config) supportsCurve(version uint16, x CurveID) bool {
    if c != nil && len(c.CurvePreferences) != 0 {
        if !slices.Contains(c.CurvePreferences, x) { return false }   // 只看你的清单
        ...
    } else {
        if !defaultCurveEnabled(x) { return false }                   // GODEBUG 在这里
    }
```

其中的原则是**显式配置应当压过环境变量**——否则运维改一个环境变量，
就能悄悄推翻开发者写在代码里的安全策略。Go 1.26 及更早版本会把显式清单也过滤一遍，
因此 SILO 在 Go 1.26 上「开关有效」其实是依赖了一个 Go 认定的错误行为。

后续升级需要记住一点：Go 把 GODEBUG 的**默认值**绑定在主模块的 `go` 指令上，
声明旧版本的模块会保持旧行为直到主动上调。SILO 的 `go.mod` 写的是 `go 1.27.1`，
等于明确声明我们采用 1.27 的行为。

## SILO 的技术债在哪，以及哪些还没还 {#debt}

出问题的清单是 `{X25519MLKEM768, CurveP256, X25519, CurveP384, CurveP521}`，
继承自上游，后来被加入了那个后量子条目。写死它带来的是两头不靠：
既享受不到标准库默认值的演进，**又**用不了标准库提供的兼容开关。

`48e184652` 在全部 8 个 Server TLS 配置点移除该赋值——外部通用 HTTP transport、
复制 transport、带客户端证书的云 transport、节点间 transport、两条 grid 链路、etcd，
以及入站 S3/Console 监听器——退役 `TLSCurveIDs` helper，
并补充了跨 5 个出站构造函数、2 个对端 TLS 版本、2 种 GODEBUG 设置的线上级回归测试。
证书与主机名校验、密码套件策略、代理处理、HTTP/2 选择均未改变，
也没有引入任何失败后降级或重试。此前只改 OIDC 的候选补丁被放弃，
是因为同一个 transport 还服务身份插件、通知与 Lambda 可达性检查、审计 webhook 和 S3 云分层。

**同一类债在下一层依然存在。** 密码套件仍然写死：
`crypto.TLSCiphers()` 与 `crypto.TLSCiphersBackwardCompatible()` 被赋值在出站 transport、
LDAP、etcd、grid 链路和入站监听器上。监听器至少还有 `MINIO_API_SECURE_CIPHERS`
可以在两套之间切换，**所有出站路径一个开关都没有**。
下次 Go 调整套件默认值时，同样的剧本会再演一遍。

本记录采纳的通用准则：**设 `MinVersion`，其余交给标准库。**
如果确有不兼容的对端需要更窄的配置档位，把它做成产品配置——
在 `mc admin config` 与支持包里可见——而不是写死在源码里。
协议僵化是个老问题：TLS 1.3 不得不在线上伪装成 TLS 1.2，
GREASE 的存在正是为了逼中间设备容忍自己不认识的编号。

## 线上真正的差异 {#wire}

在同一个合成 IdP 夹具前测量，默认设置下：

| 构建 | ClientHello | ML-KEM (4588) | ML-DSA 0x0904-6 | User-Agent |
| --- | ---: | --- | --- | --- |
| 20260804，Go 1.26.5 —— 正常 | 1497 B | 有 | 无 | `MinIO (…)` |
| 20260903，Go 1.27.1 —— 故障 | 1509 B | 有 | 有 | `Silo (…)` |
| 20260916，Go 1.27.1 —— 已修复 | 1509 B | 有（默认） | 有 | `Silo (…)` |
| 20260804 + `tlsmlkem=0` | 275 B | 无 | 无 | `MinIO (…)` |
| 20260903 + `tlsmlkem=0` | 1509 B | **仍然有** | 有 | `Silo (…)` |

有两点容易被忽略，但至关重要。

**能正常工作的版本本来就在发 ML-KEM。** 除非运维在升级**之前**就设过 `tlsmlkem=0`，
否则 ML-KEM 不是新旧版本之间的变量，恢复这个开关也就无法单独解释或修复他们的故障。

**默认设置下，两个版本之间只有两处变化：** 三个 ML-DSA 编号，
以及改名带来的 HTTP User-Agent 变化（`MinIO (…)` → `Silo (…)`）。
后者只有在 RST 发生于握手完成之后时才成立。

## 影响面，以及症状为什么具有误导性 {#blast}

写死的清单覆盖了所有 TLS 路径的两个方向，但后果差别很大：

| 路径 | 入口不兼容时的后果 | 可见度 |
| --- | --- | --- |
| OIDC discovery / JWKS | 身份初始化阻塞，Console 不启动，**节点不提供任何服务** | 立刻致命 |
| KMS/KES、LDAP(S) | 加密或目录认证不可用。这两处本来就用默认曲线，GODEBUG 一直有效 | 立刻可见 |
| 跨站复制目标 | 复制静默积压，只能从指标看出来 | 容易漏 |
| 审计 / 通知 webhook、Lambda 检查 | 审计记录丢失、事件不投递 | 容易漏 |
| S3 分层 / 云后端 | 转冷失败，远端对象读不回 | 容易漏 |
| etcd、节点间 grid | 集群内部流量，一般不经过这类设备 | 低 |
| 入站 S3/Console 监听器 | 客户端连不上；由**对端**的握手决定 | 取决于客户端 |

只有身份路径会阻塞启动，因此它最先被报告。其余几条会安静降级，
所以一个部署完全可能已经受影响而无人提单。

四个特性叠加，使这个症状在现场几乎无法诊断：身份初始化以随机 0–3 秒间隔重试；
discovery 与 JWKS 抓取**没有总超时**，启动可以无限期挂住；
身份离线期间 `/minio/health/live` 与 `/minio/health/ready` **都保持 200**，
Kubernetes 就绪探针会报成功（只有 `/minio/health/cluster` 返回 503
并携带 `X-Minio-Server-Status: iam-offline`）；
而错误文本 `read: connection reset by peer` 不说明 TLS 握手是否完成。
此时从同一镜像跑 curl 还会成功，因为 curl 用的是另一套 TLS 栈并协商了 HTTP/2。

## 20260916 自身带来的变化 {#widening}

移除写死清单不会恢复此前的线上格式，而是采用当前默认值，而它更大：

| 版本 | 实际提供的 `supported_groups` |
| --- | --- |
| 20260903 及更早（写死） | `X25519MLKEM768, X25519, P256, P384, P521` |
| 20260916（Go 默认） | `X25519MLKEM768, SecP256r1MLKEM768, SecP384r1MLKEM1024, X25519, P256, P384, P521` |

因此对于什么都不设置的运维，20260916 会在每一个 TLS 端点（入站与出站）
多提供两个后量子编号。对绝大多数部署这无害，
但一个按 group 编号做白名单的入口，理论上可能在 20260903 正常而在 20260916 失败。
`GODEBUG=tlssecpmlkem=0` 可以只关掉这两个并保留 X25519MLKEM768。
而对于确实设置了 `tlsmlkem=0` 的运维，20260916 产生的握手比此前任何版本都更小更保守——
这正是修复的目的。

## 三种机制，一个决定性事实 {#branches}

调查复现了三种都能产生所报错误文本的机制，而修复只覆盖其中一种。

| 分支 | 机制 | 20260916 是否覆盖 |
| --- | --- | --- |
| A | 入口拒绝 ML-KEM，且运维在升级前就设过 `tlsmlkem=0` | **是**——修复恢复的正是这条 |
| B | 入口拒绝 ML-DSA 签名编号 | 否。只有 TLS 1.2 上限能抑制该 offer，而产品没有暴露这个设置 |
| C | HTTP 层规则在握手成功之后拒绝变更后的 `Silo` User-Agent | 否，任何 TLS 改动都与之无关 |

还有第四项观察，它能解释 curl 对照为什么具有误导性，但解释不了升级回归：
discovery transport 禁用 HTTP/2 且不发 ALPN，而 curl 协商了 h2。
这个差异在正常版本和故障版本里都存在。

**一个事实能把 A/B 与 C 分开，夹具结果能把 B 与 A 分开：**
RST 是紧跟 ClientHello 到达，还是在 GET 写出之后才到达。
在故障网络位置做一次抓包，或者拿到入口在同一秒的拒绝原因，就能定案。
这份证据从未向报告人索取过——本文存在的目的之一就是修正这个流程缺陷。

## 全部可选解法 {#options}

按「谁来动手」分组。每一行只解决特定分支；在拿到定位证据之前，任何一条都是在赌。

**入口侧——唯一完整的解法。**

| 做法 | 分支 | 代价 |
| --- | --- | --- |
| 升级或重新配置中间设备，使其容忍不认识的算法编号 | A、B、C | 需要设备归属方配合，周期不由我们控制 |
| 绕开它：把 `MINIO_IDENTITY_OPENID_CONFIG_URL` 指向不经过该设备的端点，或使用 split-horizon DNS。discovery 文档中的 `issuer` 必须保持不变 | A、B、C | 证书主机名与 issuer 一致性必须成立 |
| 用 sidecar（stunnel、Envoy）自行终止 TLS 并连接 IdP | A、B、C | 多一个组件及其信任链 |
| 走 `HTTPS_PROXY` | 无 | CONNECT 隧道原样转发同一个 ClientHello；只有自行终止 TLS 的代理才有意义 |

**部署侧——今天就能用。**

| 做法 | 分支 | 代价 |
| --- | --- | --- |
| `GODEBUG=tlsmlkem=0` | A | 进程级关闭混合密钥交换，含节点间链路与入站监听器；证书校验不受影响 |
| `GODEBUG=tlssecpmlkem=0` | 20260916 新增的两个 group | 更窄；保留 X25519MLKEM768 |
| `GODEBUG=fips140=on` | A 与 B | **不推荐。** FIPS 白名单里没有 ML-KEM 与 ML-DSA，但它同时替换密码套件与曲线，并对整个进程排除 Ed25519/X25519 |
| 停留在 20260804 | A、B、C | 放弃后续全部安全修复；仅作应急 |
| 在入口放行 `Silo` User-Agent | C | 一条规则改动 |

**今天没有任何办法关掉 ML-DSA。** Go 没有为签名算法提供 GODEBUG——
`internal/godebugs/table.go` 中 crypto/tls 的条目只有 `fips140ems`、`tlsmaxrsasize`、
`tlsmlkem`、`tlssecpmlkem`、`tlssha1`——`tls.Config` 也没有签名算法字段。
唯一的杠杆是版本门：这些编号只在 TLS 1.3 下定义，把 `MaxVersion` 压到 TLS 1.2 即可抑制。
而 SILO 没有在任何地方暴露这个入口。这就是缺口。

## 由此确立的需求 {#requirements}

1. **为 discovery 与 JWKS 抓取加上分阶段诊断。** 通过 `httptrace` 记录
   连接建立 → 握手开始 → 握手完成（附协商到的版本、套件、group）→ 请求写出 → 首个响应字节，
   并在返回的错误中标明最后到达的阶段。无需配置、不改协议行为，
   且可以用一条日志代替抓包来区分 A、B、C 三条分支。这是价值最高的一项。
2. **显式的出站 TLS 兼容档位**，至少覆盖身份提供方：经典曲线，以及可选的 TLS 1.2 上限。
   必须 opt-in、启动时打出醒目警告，并在 `mc admin config` 与支持包中可见。
   `MINIO_API_SECURE_CIPHERS` 是既有先例。这是分支 B 唯一的进程内解法。
3. **启动健壮性**：为 discovery 与 JWKS 抓取加总期限与 context 取消；
   并就就绪检查是否应当反映身份状态做出决定——目前它并不反映。
4. **受支持的诊断子命令**，由调查用探针演化而来：握手分阶段、协商参数，
   以及 classical / TLS 1.2 / User-Agent 对照，使运维无需我们介入即可定位这类故障。
5. **清理剩余的写死密码套件**，至少让出站路径拥有监听器已有的那个开关。

有两个选项被明确否决。**发布一个降低了的默认值**——在 `go.mod` 写 `godebug` 指令，
或在镜像里塞 `ENV GODEBUG=…`——会悄悄削弱所有连接的后量子保护，
而且仍然解决不了分支 B。**握手被 RST 后自动降级重试**
等于把「注入一个 RST 就能把连接压到 TLS 1.2 加经典曲线」交给主动攻击者；
浏览器正是因为这个原因移除了这类 fallback。若将来确要实现，
它只能挂在需求 2 的显式开关之后。

## 发布与沟通门槛 {#gates}

这次修复的兼容前提**确实写了**——写在 Server README 的 TLS 小节、
[Go 1.27 TLS 与 OIDC](/zh/blog/design/go127-tls-oidc-discovery/)，
以及 [20260916 发布说明](/zh/blog/release/silo-20260916/) 中。
没有做的是以下三件事，每一件都直接导致了当前结果：

- 从未在 issue 中告诉报告人：修复需要运维设置 GODEBUG 才会生效，以及它针对的是哪条分支。
- 该要求从未进入升级检查清单。它被归档为「我们改了什么」的记录，而不是「你必须做什么」的动作。
- issue 以补丁合并为依据关闭，而不是以报告人复测为准。

根子上的定性错误才是教训：这次改动被当作正确性修复（恢复标准库默认值），
而它同时是一次**兼容契约变更**——其效果取决于运维的动作。
定性正确的话，它会走发布门禁与用户沟通流程，而不是只走文档流程。

由此确立三条门槛，适用于今后所有同类改动：

1. 任何「效果取决于运维动作」的修复，都要在发布说明和升级检查清单中列为
   **required action**，与协调升级类条目同等待遇。
2. 外部用户报告的 issue，只有在报告人确认复测通过后才能关闭。
   补丁合并只改变状态标签，不改变 issue 状态。
3. 修复无法完整解决所报症状时，issue 中必须写明：处理的是哪条分支、
   还剩哪些分支、以及具体需要什么证据——而不是指望报告人自己去读 README 的某一节。

## 归属 {#attribution}

本文在 [#154 调查与九月 Go 1.27 栈评审](/zh/blog/design/go127-tls-oidc-discovery/)
的基础上，补充发布后的复测结果、机制分析、解法空间与流程门槛。
复现工件与完整证据链保留在文档树之外。可支持的表述仍然是：
合并后的修复在受影响的 8 个 Server 配置点恢复 Go 密钥交换默认值，并经合成负对照验证。
它不诊断任何特定部署；在拿到阶段级证据的复测之前，#154 不做任何根因断言。
