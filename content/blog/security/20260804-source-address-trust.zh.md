---
title: "SN-2026-018：客户端源地址信任边界、转发头欺骗与 aws:SourceIp 加固"
linkTitle: "SN-2026-018：源地址信任边界"
date: 2026-08-04
author: "[冯若航](https://vonng.com) ([`@Vonng`](https://github.com/Vonng))"
description: "解析为何设置 _MINIO_API_XFF_HEADER=off 后仍会无条件信任 X-Real-IP 与 Forwarded、为何单纯部署反向代理不足以防御伪造，以及 MINIO_API_TRUSTED_PROXIES 如何闭环源 IP 归属（SN-2026-018）。"
url: "/zh/blog/security/source-address-trust/"
tags: ["Security", "IAM", "Network", "Reverse Proxy", "aws:SourceIp", "Audit", "SILO"]
---

**`SN-2026-018`** 修复了 [silo-pkg `v3.12.0`](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.0)（提交 `62f326d`）与 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z)（`00a8171cb`，[`pgsty/silo#41`](https://github.com/pgsty/silo/issues/41)）中影响 `aws:SourceIp` IAM 条件求值、审计日志、桶事件通知及管理端 HTTP 追踪的客户端源 IP 欺骗问题：`handlers.GetSourceIP` 此前默认无条件信任任意 TCP 对端发来的 `X-Forwarded-For`、`X-Real-IP` 与 RFC 7239 `Forwarded` 请求头；即便管理员显式设置了 `_MINIO_API_XFF_HEADER=off`，该函数也只是跳过了 `X-Forwarded-For`，随后立刻落入并无条件采信客户端伪造的 `X-Real-IP` 与 `Forwarded`。

## 结论先行 {#summary}

1. **`_MINIO_API_XFF_HEADER=off` 漏掉了另外两个转发头**：设置 `_MINIO_API_XFF_HEADER=off` 仅跳过了 `X-Forwarded-For`，但 `handlers.GetSourceIP` 紧接着就会读取 `X-Real-IP` 和 `Forwarded`。任何直连客户端只需伪造 `X-Real-IP: 10.0.0.1` 即可绕过 `aws:SourceIp` 策略限制。
2. **“在前面挡一层反向代理”往往并不够**：即便部署了反向代理，如果代理采用追加模式（如 nginx 默认的 `proxy_add_x_forwarded_for`）而服务端固定取 `X-Forwarded-For` 最左侧的第一个 IP，或者集群内 Pod 可以绕过 Ingress 直连 `ClusterIP`，攻击者依然可以伪造 `aws:SourceIp`。
3. **`MINIO_API_TRUSTED_PROXIES` 提供显式的从右向左信任链校验**：[Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 引入了 `MINIO_API_TRUSTED_PROXIES`（支持 `off` / `none`、授信代理 IP/CIDR 列表、以及兼容旧行为的 `all` / `*`），并从右向左逆序回溯 `X-Forwarded-For` / `Forwarded`，在遇到第一个不属于授信代理集合的跳点时立即停下并将其作为真实客户端地址。

---

## `handlers.GetSourceIP` 的四个核心消费方 {#consumers}

在 SILO 中，`handlers.GetSourceIP(r)`（位于 `silo-pkg/handlers/proxy.go`）是从入站 `*http.Request` 提取客户端 IP 地址的唯一入口。四个与安全及可观测性密切相关的子系统直接依赖其返回值：

| 消费方 | 代码位置 | 安全与运维职责 |
|---|---|---|
| `aws:SourceIp` IAM 条件键 | `cmd/signature-v4-utils.go` (`getConditionValues`) | 评估桶策略与 IAM 策略中的 `IpAddress` 与 `NotIpAddress` 网段条件。 |
| 审计日志 (`remotehost`) | `cmd/logger/audit.go` | 在合规审计日志中记录发起请求的客户端源 IP。 |
| 桶事件通知 (`Host`) | `cmd/notification.go` | 填充 S3 事件通知载荷中的 `requestParameters.sourceIPAddress`。 |
| 管理端 HTTP 追踪 (`mc admin trace`) | `cmd/http-tracer.go` | 在实时诊断追踪输出中展示客户端源 IP。 |

值得一提的是，旧版 `handlers.GetSourceIPRaw` 在提取出第一个匹配的请求头字段后，甚至不会校验它是不是一个语法合法的 IP 地址（上游 `silo-pkg` 的单元测试里 literally 有一条断言验证传入 `X-Forwarded-For: _gazonk` 会原样返回 `"_gazonk"`！）。虽然 `IpAddress` 条件算子内部会用 `net.ParseIP` 解析，但审计日志和事件通知都会被直接注入未校验的原始字符串。

---

## 为什么 `_MINIO_API_XFF_HEADER=off` 防不住源 IP 伪造 {#the-switch}

在 `silo-pkg/handlers/proxy.go` 中，`GetSourceIPRaw` 原本按顺序依次检查三组请求头：

```go
var xffHeaders = []string{"X-Forwarded-For", "x-forwarded-for"}
var realIPHeaders = []string{"X-Real-IP", "x-real-ip"}
var forwardedHeaders = []string{"Forwarded", "forwarded"}
```

2025 年 2 月上游 PR [`minio/minio#20977`](https://github.com/minio/minio/pull/20977)（及 `minio/pkg#306`）引入 `_MINIO_API_XFF_HEADER=off` 开关时，**仅仅**用它包住了第一组 `xffHeaders` 循环：
- 当 `_MINIO_API_XFF_HEADER=off` 时，`GetSourceIPRaw` 跳过 `X-Forwarded-For`；
- 紧接着下一行，它便毫无条件地继续读取 `X-Real-IP`（`realIPHeaders`）和 `Forwarded`（`forwardedHeaders`）！

结果，为了防止直连端点上 `aws:SourceIp` 被伪造而特意配置了 `_MINIO_API_XFF_HEADER=off` 的管理员，面对一条简单的 `curl -H "X-Real-IP: 192.0.2.10"` 或 `curl -H "Forwarded: for=192.0.2.10"` 依然毫无防备。

### 自 2017 年以来的上游演进历史 {#upstream-history}

回顾 Git 历史可以看到，这一位置在过去八年里经历过多次反复：
- **2017-07（[`minio/minio#4736`](https://github.com/minio/minio/pull/4736)）**：上游曾意识到客户端可伪造 `X-Forwarded-For` 绕过 `aws:SourceIp`，一度从 `GetSourceIP` 中移除了转发头。
- **随后的重构**：由于反向代理后面的部署抱怨 `aws:SourceIp` 和审计日志只能看到负载均衡器 IP，后续重构又把 `X-Forwarded-For`、`X-Real-IP` 与 `Forwarded` 加了回来，并且直接取 `X-Forwarded-For` 逗号分隔列表中的**第一个**（最左侧）地址。
- **2023-08（[`minio/minio#17878`](https://github.com/minio/minio/discussions/17878)）与 2025-02（[`minio/minio#20977`](https://github.com/minio/minio/pull/20977)）**：社区多次反馈直连场景下的伪造风险后，上游加入了 `_MINIO_API_XFF_HEADER`，却遗漏了同函数的 `X-Real-IP` 与 `Forwarded`。

---

## 为什么“前面挡一层反向代理”依然不够安全 {#proxy-is-not-enough}

一种常见的误解是：“只要我的对象存储前面挡了 nginx 或 Ingress 反向代理，客户端就没法伪造源 IP 了。”事实上，在以下两种极其普遍的生产拓扑中，即便有反向代理，旧逻辑依然会被轻易击穿：

1. **取最左侧 `X-Forwarded-For` 与代理追加模式（`proxy_add_x_forwarded_for`）的冲突**：nginx 等反向代理的标准配置通常是 `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;`，它的语义是在客户端发来的 `X-Forwarded-For` 末尾**追加**真实客户端 IP。如果攻击者发送 `X-Forwarded-For: 10.0.0.5`，nginx 转发给后端的请求头就是 `X-Forwarded-For: 10.0.0.5, 203.0.113.99`。由于旧版 `GetSourceIP` 无条件取**最左侧**的第一个地址（`10.0.0.5`），攻击者伪造的内网 IP 依然直接胜出！
2. **Ingress 入口与集群内直连并存（Kubernetes ClusterIP）**：在 Kubernetes 环境中，外部流量经过 Ingress 控制器进入，但集群内的业务 Pod 往往直接访问 `silo` 的 `ClusterIP` Service。如果服务端无条件信任任何对端发来的转发头，集群内任意一个普通 Pod 只要直连 `ClusterIP` 并附上 `X-Forwarded-For` 或 `X-Real-IP`，就能冒充受信任子网调用管理或受限接口。

---

## `MINIO_API_TRUSTED_PROXIES` 的设计方案 {#design}

为了同时解决上述两类问题，`silo-pkg v3.12.0`（`62f326d`）与 Server `20260804`（`00a8171cb`）引入了 `MINIO_API_TRUSTED_PROXIES` 环境变量：

| 配置值 | 对端信任策略 | 转发头解析行为 |
|---|---|---|
| `MINIO_API_TRUSTED_PROXIES=off`（或 `none`） | **不信任**任何外部代理跳点 | 对所有外部连接一律采用 TCP 对端地址（`r.RemoteAddr`），完全忽略 `X-Forwarded-For`、`X-Real-IP` 与 `Forwarded`。 |
| `MINIO_API_TRUSTED_PROXIES=10.0.1.0/24,192.168.1.10` | 仅信任显式列出的 IP/CIDR | 若 `r.RemoteAddr` 不在授信集合内，直接返回 `r.RemoteAddr`。若 `r.RemoteAddr` 受信任，则**从右向左**逆序扫描 `X-Forwarded-For`（或 `Forwarded`），返回第一个不在授信集合内的合法 IP。 |
| 未设置、`all` 或 `*` | 历史兼容模式 | 保持 `20260804` 之前的行为（除非额外设置了 `_MINIO_API_XFF_HEADER=off`）。 |

注意：`handlers.GetSourceScheme`（读取 `X-Forwarded-Proto`）被有意保持不变，以确保在反向代理卸载 TLS 的场景下，HTTPS 重定向与预签名 URL 协议检测不受 `MINIO_API_TRUSTED_PROXIES` 影响。

---

## 七项关键工程权衡 {#tradeoffs}

### 1. 默认向后兼容 vs. 显式安全加固 {#tradeoff-default}

如果在小版本更新中直接将未设置时的默认值改为 `off`，所有部署在反向代理之后、正在使用 `aws:SourceIp` 策略但尚未配置 `MINIO_API_TRUSTED_PROXIES` 的存量集群都会在升级瞬间因看到负载均衡器 IP 而全量拒绝合法业务请求。因此我们保持未设置时的默认兼容性，同时提供 `MINIO_API_TRUSTED_PROXIES=off` 与 CIDR 列表作为明确的一等安全控制项。

### 2. 为什么我们撤回了“直接扩大 `_MINIO_API_XFF_HEADER=off` 拦截范围”的初版改法 {#tradeoff-widen}

在第一版草稿中，我们曾直接让 `_MINIO_API_XFF_HEADER=off` 同时禁用 `X-Real-IP` 和 `Forwarded`。然而运行服务端测试集时，`cmd/generic-handlers_test.go` 中的 `TestXFFDisabled` 立刻报错失败！

仔细检查 `TestXFFDisabled` 揭示了原因：该测试专门模拟了这样一种 nginx 部署——nginx 用 `X-Real-IP: $remote_addr` **覆盖**写入真实客户端 IP（单跳可信），同时用 `X-Forwarded-For: $proxy_add_x_forwarded_for` **追加**列表（最左侧不可信）。在这种拓扑下设置 `_MINIO_API_XFF_HEADER=off` 的用户，恰恰指望服务端忽略 `X-Forwarded-For` **以便落入被 nginx 覆盖写死的 `X-Real-IP`**！因此，当 `MINIO_API_TRUSTED_PROXIES` 未设置时，我们完整保留了 `_MINIO_API_XFF_HEADER=off` 的既有行为以兼容 `TestXFFDisabled`，而由 `MINIO_API_TRUSTED_PROXIES=off` 负责彻底关闭全部三类转发头（`X-Forwarded-For`、`X-Real-IP` 与 `Forwarded`）。

### 3. 为什么只支持环境变量而不提供 `mc admin config` 动态配置键 {#tradeoff-config}

在 SILO 的启动时序中，HTTP 监听器与初始路由在分布式纠删码存储加载 `api` 子系统配置之前就已经就绪。如果将授信代理做成 `mc admin config set api` 配置项，节点启动早期在加载完持久化配置之前就会出现一段信任策略未定义的空窗期（要么短暂 Fail-Open，要么短暂拒绝请求），且运行时热修改还涉及跨包并发状态同步。将其固定为进程启动环境变量，可以从根本上消除启动空窗期。

### 4. 本地环回地址（Loopback）豁免：区分 TCP 对端与转发链中间跳点 {#tradeoff-loopback}

SILO 内置的 FTP 与 SFTP 服务端（`cmd/ftp-server.go`、`cmd/sftp-server.go`）以及本机内部转发会通过本地环回地址（`127.0.0.1` / `::1`）连接 S3 层，并通过 `X-Forwarded-For` 传递外部 FTP/SFTP 客户端的真实 IP。因此，当**直接 TCP 对端**（`r.RemoteAddr`）是本地环回地址时，SILO 会信任该本地对端跳点，以确保 FTP/SFTP 的审计日志和 `aws:SourceIp` 能拿到真实客户端 IP。

但至关重要的一点是：**本地环回地址绝不能在 `X-Forwarded-For` 请求头链条内部被无条件当成授信跳点！** 否则，处于一层授信反向代理之后的外部攻击者只需发送 `X-Forwarded-For: 10.0.0.1, 127.0.0.1`，从右向左扫描器就会先跳过反向代理（`r.RemoteAddr`），再跳过请求头里的 `127.0.0.1`，最终采信攻击者伪造的 `10.0.0.1`！

### 5. 请求头优先级：为什么 `X-Forwarded-For` 优先于 `X-Real-IP` {#tradeoff-precedence}

当 `MINIO_API_TRUSTED_PROXIES` 配置为 CIDR/IP 列表时，`GetSourceIP` 先从右向左评估 `X-Forwarded-For`，再检查 `X-Real-IP`（经 `parseIP` 校验），最后从右向左评估 `Forwarded`。这里有意与 `getSTSLDAPTrustedProxySourceIP`（`cmd/sts-handlers.go` 中专用于单跳 LDAP STS 代理、优先读 `X-Real-IP` 的辅助函数）保持区分：在通用多跳 S3 代理链中，只有 `X-Forwarded-For` 完整记录了每一跳的追加轨迹以供从右向左验链，而 `X-Real-IP` 可能停留在外层或内层某一跳。

### 6. 避免配置过宽的内网 CIDR {#tradeoff-breadth}

如果管理员将 `MINIO_API_TRUSTED_PROXIES` 设为过宽的网段（例如 `10.0.0.0/8`），而普通业务容器也运行在 `10.0.0.0/8` 内，那么网段内的任意业务容器都会被视为授信代理并能伪造 `X-Forwarded-For`。在生产环境中应仅填入专用的负载均衡器/Ingress IP 或独立子网。

### 7. 多节点分布式集群的对等节点配置 {#tradeoff-multinode}

在多节点分布式 SILO 集群（如 `silo server http://node{1..4}/data`）中，负载均衡器可能将请求打到节点 1，再由节点 1 在集群内部转发给节点 2～4：

| 部署拓扑 | `MINIO_API_TRUSTED_PROXIES` 应包含的地址 |
|---|---|
| 单节点 + 反向代理 | 仅反向代理的 IP/CIDR |
| 多节点分布式集群 + 反向代理 | 反向代理的 IP/CIDR **以及**所有 SILO 集群节点的 IP/CIDR |
| 客户端直连多节点集群（无外部反向代理） | 所有 SILO 集群节点的 IP/CIDR（若无跨节点转发需求则可设为 `off`） |

---

## 兼容性细节 {#compatibility}

- **启用授信代理控制后拒绝非 IP 脏字符串**：只要启用了 `MINIO_API_TRUSTED_PROXIES`（设为 `off` 或 CIDR 列表），所有候选请求头字段都必须通过合法 IP 地址解析；像 `_gazonk` 这样的畸形字符串会被直接丢弃而不会返回给下游。
- **清理失效的 IPv4-mapped 字符串前缀拼接逻辑**：旧版 `proxy.go` 中有一处针对 `"::ffff:"` 的字符串截取判断，无法正确处理十六进制形式的 IPv4-mapped IPv6 地址；新代码统一使用标准库 `netip.Addr.Unmap()` 将 `::ffff:192.0.2.1` 规范化为 `192.0.2.1`。

---

## 多轮代码审查抓出的 9 个边界缺陷 {#review}

在补丁合入前，我们跨 `silo-pkg` 与 `silo` 进行了三轮代码审查，先后抓出并修复了 9 个隐蔽的边界问题：

### 第二轮审查发现 {#review-round-two}

1. **`init()` 与 `MINIO_CONFIG_ENV_FILE` 的启动加载时序倒置**：初版代码仅在包级 `init()` 函数中读取环境变量；如果管理员将 `MINIO_API_TRUSTED_PROXIES` 或 `_MINIO_API_XFF_HEADER` 写在由 `MINIO_CONFIG_ENV_FILE` 指定的配置文件中，由于该文件在 `serverHandleEnvVars` 阶段才被解析注入进程环境，`init()` 早已执行完毕！我们在 `serverHandleEnvVars` 中显式补齐了这两个开关的二次解析与生效。
2. **转发链内部的 `127.0.0.1` 跳板欺骗（`X-Forwarded-For: spoofed, 127.0.0.1`）**：区分了“TCP 对端 `r.RemoteAddr` 是环回地址”与“请求头字符串里出现 `127.0.0.1`”（详见[权衡 4](#tradeoff-loopback)）。
3. **带作用域标识的 IPv6 地址（`fe80::1%eth0`）**：链路本地（Link-Local）IPv6 对端的 `r.RemoteAddr` 包含 `%zone` 后缀；在匹配 CIDR 前先剥离 Zone 标识再调用 `netip.ParseAddr`，避免了合法 IPv6 链路本地地址解析失败。
4. **多行同名 `X-Forwarded-For` 请求头（`r.Header.Values`）**：HAProxy 或 Envoy 等代理在追加转发信息时，可能直接追加第二行 `X-Forwarded-For` 请求头，而非用逗号拼到第一行末尾。若调用 `r.Header.Get("X-Forwarded-For")` 只会读到第一行（恰恰是客户端伪造的那一行！）。我们改为通过 `r.Header.Values("X-Forwarded-For")` 从最后一行向第一行逆序遍历。
5. **内部 `forwarder.go` 请求头清理**：当不可信对端发来的 `X-Real-IP` 或 `Forwarded` 被拒绝后，内部节点间转发不应将其原样透传给下游受信任节点。
6. **`::ffff:0:0/96` 网段前缀的 `Unmap` 陷阱**：若对 CIDR 的网络前缀地址无条件调用 `Unmap()`，会把 `/96` 的 IPv6 映射网段变成 `0.0.0.0` 并错误匹配所有 IPv4 地址；我们在 CIDR 解析中专门保护了映射网段的前缀长度语义。

### 第三轮审查发现 {#review-round-three}

7. **空列表必须默认安全关闭（`MINIO_API_TRUSTED_PROXIES=","`）**：如果管理员误配了 `MINIO_API_TRUSTED_PROXIES=","`（或纯空格），解析出的 CIDR 切片为空；若将空切片当作“未设置（信任所有）”就会导致严重 Fail-Open！现在只要显式设置了该环境变量但解析不出任何有效规则（且不为 `off`/`none`/`all`/`*`），服务端启动会直接报错退出。
8. **区分“未设置”与“设为空串”**：使用 `env.Get(EnvAPITrustedProxies, "")` 无法区分环境变量未设置与被显式设为 `MINIO_API_TRUSTED_PROXIES=""`；我们改为显式检查环境变量是否存在。
9. **零分配逆序扫描与 100 跳上限**：如果在每个请求上直接调用 `strings.Split(header, ",")`，攻击者只需发送一个包含上百万个逗号的 1 MB `X-Forwarded-For` 请求头，单次请求就会在堆上分配约 33 MB 的字符串切片。我们将 `strings.Split` 替换为原地从右向左扫描器，并将最大扫描跳数限制为 100 跳。

---

## 运维配置建议 {#recommendations}

- **客户端直连 SILO（无反向代理）**：强烈建议设置 `MINIO_API_TRUSTED_PROXIES=off`。
- **部署在 nginx / HAProxy / Envoy / Ingress 之后**：将 `MINIO_API_TRUSTED_PROXIES` 设置为反向代理的 IP/CIDR 列表（多节点集群需一并包含各 SILO 节点 IP/CIDR）。

---

## 明确不做项 {#not-done}

- **TCP 层 PROXY Protocol v1/v2**：监听器层面的二进制 PROXY Protocol 与 HTTP 层的 `X-Forwarded-For` / `Forwarded` 解析属于不同层级，不在本补丁范围内。
- **`GetSourceScheme`**：保持现有 `X-Forwarded-Proto` 识别行为不变，避免影响反向代理卸载 TLS 后的协议判断。
- **`ExistingObjectTag/*` 条件来源隔离**：在关联提交 `2f55347f7`（同样随 `20260804` 发布）中独立修复，确保仅从已存储的对象标签填充该条件键，绝不采信客户端请求头。

## 严重度定级 {#severity}

本问题作为 **`SN-2026-018`** 记录于 SILO 安全台账（与 [CVE-2026-42600](/zh/blog/security/cve-2026-42600/) 相同，上游 `minio/minio` 已归档；对于依赖 `aws:SourceIp` 实施访问控制的环境属于中至高危）。升级至 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 并按拓扑配置 `MINIO_API_TRUSTED_PROXIES` 即可在 IAM、审计日志、事件通知与管理追踪中全面闭环源地址归属。
