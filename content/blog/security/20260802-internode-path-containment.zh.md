---
title: "SN-2026-002：内部节点路径包含审计——补完 CVE-2026-42600 欠下的那笔账"
linkTitle: "SN-2026-002 · 节点间路径审计"
date: 2026-08-02
author: "冯若航"
description: "SN-2026-002 在 CVE-2026-42600 之后对全部四个节点间协议面开展系统审计，闭合 12 项继承自上游的路径穿越、卷根别名、除零崩溃与无界内存分配缺陷，并完整记录开发过程中自造并拦截的 4 次回归。"
tags: [安全, Path Containment]
weight: 90
draft: false
url: "/zh/blog/security/internode-path-containment/"
---

**发布状态：** 已随 [Server 20260804](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-08-04T00-00-00Z) 发布（[发行注记](/zh/blog/release/silo-20260804/#sn-2026-002)）\
**安全编号：** `SN-2026-002`（[安全公告台账](/zh/about/security-advisories/#sn-2026-002)）\
**修复提交：** [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670)、[`b6f70ab08`](https://github.com/pgsty/silo/commit/b6f70ab08)、[`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42)、[`1af351a70`](https://github.com/pgsty/silo/commit/1af351a70)、[`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff)\
**影响范围：** 仅分布式纠删码（distributed erasure）部署；需持有集群 root / 节点间 JWT\
**前置阅读：** [CVE-2026-42600 · ReadMultiple](/zh/blog/security/cve-2026-42600/)

在 [CVE-2026-42600](/zh/blog/security/cve-2026-42600/) 移除 `/rmpl`（`ReadMultiple`）端点之后，**SN-2026-002** 进一步审计了其余所有在 msgpack 请求体或 Grid RPC 帧中传递文件路径的内部节点接口。本文记录跨越四个内部协议面的完整审计结果、检出的 12 项继承缺陷，以及我们在修复过程中引入并在发版前拦截的 4 次回归。

## 结论先行 {#summary}

- **三个无保护协议面共检出 12 项缺陷，全部继承自上游**：经逐函数校验和比对，相关存储文件此前在分支上的改动仅为删除废弃代码，未新增任何逻辑。
- **与 CVE-2026-42600 同源**：`ReadMultiple` 只是踩中这一架构断层的其中一个端点；删掉它之后，同一根因下仍敞开着三个协议面。
- **修复过程中自造并拦截了 4 次回归**：所有回归全部出现在我们“自己新发明的规则”（`isVolumeRootAlias` 与 `guardErasureParams`）上；直接复用对象层既有语义（`hasBadPathComponent`）的部分则是零回归。

## 为什么“数端点个数”是错误的分析框架 {#four-surfaces}

早期的局部排查一直在数 handler 个数，先后数出 19、21、22 个端点，却每次都漏掉整片协议面。按参数到达底层 `xlStorage` 的通道来划分，内部节点通信共有四个协议面：

| 协议面 | 入口数 | 是否受全局 HTTP 查询参数中间件保护 |
| :-- | :-- | :-- |
| Storage-REST HTTP **查询参数（query）** | 9 | **是**——此前曾被误判为无保护 |
| Storage-REST HTTP **msgpack 请求体** | 4 | 否；`r.Form` 从不读取 msgpack 请求体 |
| **Storage Grid RPC**（`/minio/grid/v1`） | 18 | 否；完成一次 WebSocket 升级后，后续帧不再进入 HTTP 中间件链 |
| **Peer-S3 Grid RPC** | 5 | 否；不仅绕过 HTTP 中间件，还绕过 `getStorage()` 直达底层磁盘 |

第一行纠正了此前的误判：只在 handler 函数体内部 grep 校验函数的排查方式，忽略了 9 个 query 参数接口其实已被全局 HTTP 中间件（`url.ParseQuery(RawQuery)` 填充 `r.Form`）保护。而第四行（`Peer-S3 Grid RPC`）则说明：任何只修补 `storage-rest-server.go` 的方案都碰不到直接操作底层磁盘的 `DeleteBucket` 等跨节点桶级 RPC。

## 三层历史设计叠加出的结构性盲区 {#root-cause}

三个各自看似合理的设计事实叠加在一起，构成了整类漏洞的根因：

1. **路径校验只发生在 HTTP 表层**：全局中间件只检查 `r.Form`，而 `r.Form` 仅由 `url.ParseQuery(RawQuery)` 填充，永不解析请求体（2017 年定型）。
2. **Grid RPC 绕过了 HTTP 中间件**：`/minio/grid/v1` 在建立连接时完成一次 WebSocket 升级，之后的 msgpack 帧直接分发给 handler，不再经过 HTTP 中间件链（2023 年引入）。
3. **存储层默认调用方已完成校验**：`getVolDir` 仅在 `volume` 精确等于 `""`、`.` 或 `..` 时拒绝，而 `pathJoin` 会直接调用 `path.Clean`（2018 年定型）。

换句话说：**上层以为下层会校验，下层以为上层已校验，而中间新增的二进制帧通道两边都看不见。**

时间线上还有一处值得单独指出的叠加效应：`ShardFileSize` 的除零风险早在 2020 年就存在，但直到 2024 年 10 月为了修复大对象超时将其挪进 `xioutil.WithDeadline` 后，它才从“单次请求报错”升级为“整个节点进程崩溃退出”——因为 `WithDeadline` 在未挂载 `recover()` 的裸 goroutine 中执行工作函数，Go 无法跨 goroutine 捕获 panic。

## 经实测复现的攻击向量 {#vectors}

以下所有向量均在真实 `xlStorage` 实例上，通过真实的 REST / Grid 客户端配合植入哨兵文件实测复现：

| 攻击向量 | 协议面 | 实测结果 |
| :-- | :-- | :-- |
| `WriteAll("vol", "../../x")` | Storage Grid RPC | 磁盘根目录（drive root）外 **任意文件写入** |
| `RenameFile(".minio.sys", "", "bucket", "x")` | Storage Grid RPC | **将整个 `.minio.sys` 系统卷**（IAM、集群配置）搬入普通可读 S3 桶，**全程无需 `..`** |
| `DeleteBucket("../victim", force)` | Peer-S3 Grid RPC | 磁盘根目录外 **整棵目录树递归删除** |
| `DeleteBulk("vol", "")` | Storage-REST 请求体 | 整个卷被移入回收站目录 |
| `ReadAll(volume: "../")` | 任意协议面 | 追加一个尾斜杠即可绕过 `getVolDir` 的 `".."` 精确匹配检查 |
| `CheckParts` 传入零值 `Erasure`（`DataBlocks = 0`） | Storage Grid RPC | `WithDeadline` 内除零 panic，**节点进程直接终止** |
| `AppendFile` 声明 `Content-Length: 64 GiB` | Storage-REST HTTP | **空请求体直接触发 68,719,574,840 字节内存分配** |
| `DeleteVersions` 声明 1 亿条元素 | Storage-REST 请求体 | 10 字节 msgpack 头部 **触发 10.4 GB 切片预分配** |
| 分片元数据 `Size = -2` | Storage Grid / `AddVersion` | **被截断的损坏分片被报告为健康**，后台自愈静默跳过修复 |

其中两条此前从未被发现的向量尤其关键：

- **空源路径的 `RenameFile`（`srcPath = ""`）**：空路径会直接命中卷根目录本身。针对 `.minio.sys` 调用 `RenameFile(".minio.sys", "", "bucket", "x")` 会把整个系统元数据卷搬进普通 S3 桶，攻击者随后发一次普通 S3 `GetObject` 就能读走集群 IAM 与配置。整个载荷不含任何 `..`，任何只盯着 `..` 的路径审计都会漏掉它。
- **负数分片尺寸（`Size = -2`）**：负数 `Size` 会让 `ShardFileSize` 的计算结果向下取整为 `0`。而 `checkPart` 的唯一完整性判据是 `st.Size() < expectedSize`，于是任何存在的文件（哪怕是被截断的 0 字节文件）都会因为 `0 < 0 == false` 被判定为完好。更棘手的是，自愈流程信任的 `FileInfo.IsValid()` 并不拒绝负数分片尺寸，导致合法的后台自愈读到毒化元数据后会误判“分片完好”并静默跳过修复。

## 修复设计：两处收口覆盖 36 个入口 {#fix}

需要恢复的安全不变量非常明确：**内部节点载荷中的每个文件路径必须解析在其指定的 `volume` 之内，每个 `volume` 必须解析在 `drive root` 之内。**

由于绝对路径与反斜杠前缀会被 `pathJoin` 的 `path.Clean` 折回 `volumeDir` 之下，能够突破前半句的只有 `..` 路径段，能够突破后半句的只有**卷根别名**（空串、纯斜杠、`.` 以及 Windows 下的尾随空格/句点组件）。提交 [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) 在两处收口点执行这两条规则：

| 收口点 | 源码位置 | 覆盖范围 |
| :-- | :-- | :-- |
| **卷名轴（Volume axis）** | `getVolDir` + `NSScanner` 显式守卫 | 全部 `xlStorage` 调用方，**含 Peer-S3 Grid RPC** |
| **路径轴（Path axis）** | `getStorage()` 装饰器（`guardPaths`、`isVolumeRootAlias`） | 31 个远程 storage-REST / Storage Grid RPC 方法及其嵌套结构体字段 |

核心逻辑不到 40 行，不修改具体 handler，也不触碰本地纠删码热路径。有两处实现细节必须在未来的重构中保持：

- **校验必须在 `pathJoin` 之前、针对原始参数执行**：`pathJoin` 会对拼接后的绝对路径 `drivePath` 执行 `path.Clean`，把前导 `..` 彻底抹掉（例如 `/drive/../../etc` 清理后变成 `/etc`）。如果把检查放在 `pathJoin` 之后，看到的永远是干净路径，形同虚设。
- **`NSScanner` 的单行守卫是承重的**：`NSScanner` 是唯一不经过 `getVolDir` 就直接访问文件系统的 `xlStorage` 方法，因此必须保留其独立守卫。

我们也评估过“在 `xl-storage.go` 的全部 33 处 `pathJoin(volumeDir, ...)` 调用点逐一加检查”，但那意味着要在全仓最性能敏感的文件里改动 33 处，且每一处都要单独判断卷根目录本身是否为合法目标。采用两处收口点配合 `StorageAPI` 反射护栏测试，以小得多的风险换取了同等的抗漂移能力。

## 施工日志：我们自己制造并拦截的四次回归 {#regressions}

在开发与审查过程中，我们自己的初版代码曾先后制造出四次回归：

1. **误杀空格对象键（`" "` 与 `"  "`）**：第一版路径守卫把空白字符当成了非法路径分隔符，直接拒绝了 `" "` 与 `"  "`——而它们是完全合法的 S3 对象键。由于 `PutObject` 最终通过 `RenameData` 提交数据，上传名为 `" "` 的对象会在所有远程磁盘上同时失败，直接打崩写入 quorum。
2. **误杀 Unix 下的纯反斜杠键（`"\\"`）**：同一函数还拒绝了 `"\\"`。在 Unix 上，`path.Clean` 从不把 `\` 当作目录分隔符，因此 `"\\"` 只是一个普通文件名。在节点间装饰器中拒绝它，会导致**分布式集群拒绝单机部署接受的合法 S3 写入**。
3. **Windows 下的空格与句点卷根别名（`" "` 与 `"..."`）**：Win32 路径规范化层会自动剥离路径组件末尾的空格与句点，因此完全由空格或句点组成的路径组件会凭空消失并退化为父目录。这意味着在 Windows 上 `" "` 与 `"..."` 都是卷根别名——而在审查指出这一问题前，`"..."` 正好躺在我们的“合法对象名”正向测试白名单里。
4. **负数分片尺寸（`Size < 0`）**：初版 `guardErasureParams` 只拦截了“正数尺寸 + 不可用纠删码参数”，把“非零”写成了 `Size > 0`，漏掉了负数尺寸通过另一条计算路径同样会让 `ShardFileSize` 归零。

## 两次“假绿”测试与一处 Fuzz 盲区 {#false-greens}

编写复现与验收测试时，我们还踩中了三个测试陷阱：

1. **REST 客户端静默覆盖 `Content-Length`**：最初通过 `storageRESTClient` 发送伪造的 `Content-Length: 64 GiB`（配合空 `*bytes.Reader`）测试 `AppendFile` 时，客户端库对 `*bytes.Reader` 做了类型特判并根据其实际长度重写了 `Content-Length: 0`，导致测试拿到了毫无意义的绿灯。
2. **Go 标准 `http.Client` 拒绝发送截断请求体**：换成不透明 `io.Reader` 后，Go 自己的 HTTP 客户端传输层又因为请求体实际长度短于声明的 `Content-Length` 而拒绝发包。最终改用 `httptest` 直接驱动服务端 handler，才真实复现出 64 GiB 分配。
3. **Fuzz 属性测试中的提前返回盲区**：初版 Fuzz 测试把“仅由 `/` 和 `\` 组成的字符串”写成了例外并提前 `return`。这一行提前返回亲手把 Fuzz 挡在了纯反斜杠键门外，哪怕跑上百万次也搜不到 `"\\"`。随后我们将属性测试改写为对 `IsValidObjectName` 的严格包含断言，彻底消除了手写例外。

## 复用既有语义与自造规则的回归对比 {#pattern}

| 守卫组件 | 语义来源 | 开发期间引入的回归数 |
| :-- | :-- | :-- |
| `guardPaths` | 复用对象层既有的 `hasBadPathComponent`（`IsValidObjectPrefix`） | **0** |
| `getVolDir` 守卫 | 复用对象层既有的 `hasBadPathComponent` | **0** |
| `isVolumeRootAlias` | 新编写的规则 | **3** |
| `guardErasureParams` | 新编写的规则 | **1** |

`hasBadPathComponent` 作为对象层自身的校验规则（经 `IsValidObjectPrefix`），早已在多年真实 S3 流量下验证过，结构上不可能拒绝任何可通过 S3 API 合法创建的对象名；而全部 4 次回归都出在新造规则与 S3 / 操作系统边角语义不一致的地方。

## 护栏测试 {#guardrails}

为防止未来改动破坏收口边界（避免重演此前 `CVE-2026-39414` 单点修补后再次出现同类缺口的问题），测试套件从三个方向建立了自动化护栏：

- **可证伪性（变异测试验证）**：逐一临时注释掉守卫逻辑，确认测试真正变红（移除路径穿越守卫后 191 个子测试失败；移除内存分配守卫后 64 GiB 与 10.4 GB 分配立即复现）。
- **合法 S3 流量 Fuzz 等价性**：断言凡是 `IsValidObjectName` 接受的对象键，`guardPaths` 必须全部放行（196 万次执行零违例）；凡是合法桶名，`getVolDir` 必须全部放行（81 万次执行零违例）。
- **`StorageAPI` 方法级反射护栏**：通过反射扫描 `StorageAPI` 接口的所有方法；一旦未来新增了接收路径参数却未在装饰器守卫表中登记的方法，测试直接按方法名报错失败。

```bash
go test ./cmd -run 'Test.*Containment.*|Test.*Guard.*|Fuzz.*' -count=1
```

## 独立代码审查记录 {#adversarial}

本次修复在合入前经过五轮独立代码审查，依次定位出五处遗漏缺陷：空白键误杀 -> 纯反斜杠键误杀 -> `AppendFile` 64 GiB 内存分配 -> Windows 空格与句点卷根别名 -> 负数分片尺寸毒化。将实现与独立验收分离，使这 4 处兼容性或完整性回归在发版前被全部拦截。

## Server 20260804 同步发版的五项后续加固 {#open}

除主提交 [`ca7baa670`](https://github.com/pgsty/silo/commit/ca7baa670) 外，以下五项配套修复已随 [Server 20260804](/zh/blog/release/silo-20260804/#sn-2026-002) 一并发布：

- **`ReadFileHandler` 读取长度上限（`b6f70ab08`）**：提交 [`b6f70ab08`](https://github.com/pgsty/silo/commit/b6f70ab08) 拒绝超过 5 GiB（单 S3 分片最大尺寸）的声明读取长度，消除由调用方任意声明数十 GiB 触发的预分配。
- **拒绝负数分片尺寸（`80e8eaa42`）**：提交 [`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42) 在 `AddVersion` 写入收口点以及 `CheckParts`、`VerifyFile`、节点间 `guardErasureParams` 中统一拒绝负数分片尺寸，同时覆盖新写入与历史落盘元数据。
- **拒绝非正数纠删码块大小（`80e8eaa42`）**：提交 [`80e8eaa42`](https://github.com/pgsty/silo/commit/80e8eaa42) 在 `NewErasure` 构造时校验 `blockSize > 0`，并在 rebalance 的独立除法边界补充校验。
- **`ReadParts` 存储错误正常透传（`1af351a70`）**：提交 [`1af351a70`](https://github.com/pgsty/silo/commit/1af351a70) 修复了 `ReadPartsHandler` 在存储调用结束前就过早调用 `done(nil)` 的历史 bug；此前 `ReadParts` 的任何错误（包括 `errFileNotFound`）都会被塞进保活流并被客户端当作 msgpack 解析，报出 `msgp: attempted to decode type "int" with method for "map"`。修复后真实存储错误正常进入 quorum 归约。
- **`WithDeadline` 协程 panic 恢复与日志告警（`a36fd8fff`）**：提交 [`a36fd8fff`](https://github.com/pgsty/silo/commit/a36fd8fff) 在 `xioutil.WithDeadline` 内捕获 panic，将原本会导致进程退出的异常转化为一行 `stderr` 日志（`panic in deadline-bounded work: ...`，单进程生命周期内最多输出 10 次完整调用栈）并仅使当前请求失败。建议运维人员为日志关键字 `panic in deadline-bounded work:` 配置监控告警。

## 已知限制 {#closing}

以下两项边界需在运维评估时知悉：

- **Windows 平台验证边界**：SILO 发布 Windows 二进制构建，但自动化 CI 运行在 Ubuntu 环境；Windows 卷根别名规则（`" "` 与 `"..."`）系根据 Win32 路径规范化文档语义实现。
- **符号链接词法校验**：路径包含校验采用词法级（lexical）分析，与上游 `xlStorage` 一致，不解析磁盘根目录内部指向外部的操作系统符号链接。
