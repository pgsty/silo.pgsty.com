---
title: "Silo Console 2.2.0 发布说明"
linkTitle: "silo/console 2.2.0"
date: 2026-08-26
lastmod: 2026-08-26
author: "冯若航"
description: "SILO Console 2.2.0 发布说明：安全文本预览、不会说谎的下载路径、真正生效的权限门控、拆分后的用户 API、加固的通知与 IAM 策略写入，以及基于 Go 1.27 和 SILO 维护分支的依赖栈。"
tags: [发布, console]
weight: 1
draft: false
url: "/zh/blog/release/console-2.2.0/"
aliases:
  - /releases/console-2.2.0/
---

> [!NOTE]
> **已于 2026-08-26 正式发布。** [`v2.2.0`](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) 指向最终提交 [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8)。这棵精确标签树通过了完整 CI 矩阵、漏洞检查与发布流水线。公开 Release 包含六个独立二进制、九个 Linux 软件包和一份 SHA-256 校验和清单。

**版本：** [`v2.2.0`](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) · **发布提交：** `7dc4258a6` · **状态：** 已发布 · **仓库：** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.2.0 是一个以正确性与加固为主题的版本。它新增一项功能——对日志与结构化文本的严格受限预览——其余精力全部用于让既有界面「说真话」：下载不再可能静默交付缺文件的压缩包，进度条不再可能编造百分比，权限门控真正禁用它声称禁用的按钮，用户 API 不再把状态变更与用户组变更捆绑在一起，数据库通知表单发出的连接串与服务器实际存储的完全一致。

在底层，依赖栈迁移到 Go 1.27.0，并切换到 SILO 维护的分支：[`pgsty/silo-pkg` 3.12.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) 取代上游 `minio/pkg`，`pgsty/mc` 分支取代上游 `mc` 库依赖，`minio-go` 升级到 7.3.0，etcd client 系列升级到 3.7.1，关闭 [CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107)。

自 [v2.1.1](https://github.com/pgsty/silo-console/releases/tag/v2.1.1) 以来的最终变更集共 33 个提交，涉及 176 个源文件（+8,794/−2,057 行，不含重新生成的嵌入式前端资产）。

**为什么是 2.2.0 而不是 2.1.2：** 单看用户可见的修复，补丁版本号就够了；但这个周期更换了共享策略/证书实现的提供方、跨越了 etcd client 的 minor 边界、拆分了一条 REST 路由、并刻意改变了下载失败语义。这几件事中的每一件都值得在 minor 版本线上配一份明确的兼容性说明，而不是藏在一个补丁号里。

## 日志与结构化文本预览 {#text-preview}

对象浏览器现在可以把 `.log`、`.txt`、`.json`、`.xml` 对象作为纯文本预览。实现刻意保持多疑——「在管理界面渲染桶里的任意内容」本质上是一份 XSS 邀请函：

- **构造上就有界。** 请求携带 `Range: bytes=0-1048576`；响应以流式读入固定缓冲区并设硬上限，`Content-Range`/`Content-Length` 与实际读到的字节严格互验。超过 1 MiB 的对象报告*过大*——绝不会把片段当成完整内容渲染。
- **要么是文本，要么不渲染。** 字节必须通过严格 UTF-8 解码（`TextDecoder` 开启 `fatal`）且不含 NUL；否则报告*不可预览*，而不是渲染乱码或二进制垃圾。可预览性是精确白名单——四种扩展名加精确的 MIME 类型 `text/plain`、`application/json`、`application/xml`、`text/xml`——`.html`/`.htm`/`.xhtml` 被显式排除，即使其元数据自称 `text/plain`。
- **没有活动文档。** 内容渲染进单个 DOM 文本节点——不用 `innerHTML`、不用 iframe、不做 JSON 到 HTML 的变换。回归套件投喂 HTML、SVG、XML 载荷并断言它们保持为惰性文本。
- **对竞态免疫。** 快速切换对象时，进行中的预览按代际失效，慢返回的旧对象响应不可能覆盖当前对象。取消与重试都是一等状态。
- **匿名可用。** 公开/匿名对象页面通过匿名请求路径获得同样的预览，不触发任何带凭据的 API 调用。

围绕新预览类型，既有预览管线也一并修正：空对象预览为空而不是报错，追加写入的日志按新长度重新预览而不是按过期的列表尺寸截断，快速切换对象时的元数据竞态已消除。预览与分享对话框现在拿到对象的真实大小（[`92e8f4e65`](https://github.com/pgsty/silo-console/commit/92e8f4e65fefad32581cfc86bd2a36f4305b7bd2)）。

## 不会说谎的下载 {#downloads}

整条下载路径——进度报告、单对象、文件夹、归档、字节范围——围绕一条原则重建：**下载要么正确完成，要么可见地失败。**

### 诚实的进度 {#download-progress}

缺失、非法或自相矛盾的总大小不再变成编造的百分比：进度指示器保持**不确定态**，直到真实总量已知。零字节对象被显式归一化而不是落进未知总量路径；中止与取消是终态——迟到的进度事件不可能复活一个已取消的下载。下载请求恰好结算一次，JSON 错误体被安全解析，生成的对象 URL 会被回收。

### 流式文件夹下载 {#folder-downloads}

单文件夹下载改用浏览器原生的流式下载路径，不再把整个 ZIP 累积在 JavaScript 内存里——几个 GB 的文件夹不再有标签页崩溃的风险。交接模型的一个后果：控制台的传输管理器在把流交给浏览器的那一刻即报告*完成*（有 toast 说明），此后由浏览器自己的下载 UI 接管——交接后在控制台里取消不会停止浏览器侧的传输。多选下载仍走既有的 POST 响应，因此仍是内存 `Blob`；改变这一点需要单独的 API 决策，不在本版本范围内。

### ZIP 完整性——一项刻意的行为变更 {#zip-integrity}

> [!IMPORTANT]
> **这是最可能被当作「下载坏了」上报的变更。** 在 2.1.1 及更早版本中，文件夹/ZIP 下载若有对象读取失败，会**静默跳过**这些对象，交付一个 HTTP 200 但缺文件的归档。2.2.0 中任何单对象失败——列举、stat、读取、条目创建、关闭或拷贝——都会中止归档：尚未发送任何数据时返回干净的错误，流传输中途则中断连接，截断的 ZIP 再也不可能冒充完整归档。
>
> 实际后果：策略只授予某前缀的 *List* 而 *GetObject* 只覆盖其中一部分对象的用户——一种常见的 IAM 配置——以前会拿到局部归档；现在下载会在第一个被拒对象处失败。旧行为是静默的数据缺失，2.2.0 把它当作 bug 对待。请下载你能读的内容，或把文件夹下载限定在可读前缀内。

### 字节范围与状态码 {#byte-ranges}

- 畸形或不可满足的非空 `Range` 头现在返回 **`416` 并携带 `Content-Range: bytes */N`**，而不是 500。Range 解析比 Go 的宽容默认更严格：带符号、内嵌空白、`bytes=-0`、空 range 元素都会被拒绝。
- 对**零字节对象**的 range 请求返回空 200 而不是 500——这正是空对象预览 bug 的根源。
- 惰性对象 `Stat` 的失败现在透传**真实的 S3 状态码**（403、404……）而不是一律 500。
- `206` 响应在写响应头*之前*设置 `Content-Length`，部分响应从此携带正确的帧信息。
- 对象大小现在**总是序列化**——REST 与 WebSocket 列表对零字节对象返回 `"size": 0` 而不是省略字段，UI 显示 `0 B`。这是「诚实进度」赖以成立的地基。

### 版本历史 {#versions}

S3 合法的 `null` 版本 ID 保持可见而不被丢弃，版本计数把前缀匹配过滤到精确对象，桶版本控制被暂停或禁用后历史仍然保留。

## 真正生效的权限门控 {#permissions}

### 行操作按钮从未被禁用过 {#table-actions}

每个带数据表格的页面都把权限谓词传给了一个表格组件**早已不读取**的属性名（`disableButtonFunction`）——于是 10 个受影响页面（用户、用户组、策略、IDP、Webhook 设置、桶的访问/复制/生命周期面板）上的查看/编辑/删除按钮无论有无权限一律可点。谓词现在接到组件真正接受的属性上，并有一个源码守卫测试：死属性名再次出现即构建失败。服务端授权从未受影响——没权限点了也只会报错——但 UI 从此如实传达权限，而不是撒谎。

### 独立的服务账号能力 {#service-accounts}

访问密钥管理过去把多个 UI 决策挂在一个合并的权限检查上。2.2.0 在一个模块中推导四项独立能力——List、Create、Update、Remove——并在自助 Account 页面与管理员的用户详情页面一致地应用：

- 能 *list* 才显示服务账号标签页，能 *create* 才显示创建按钮，能 *remove* 才允许行选择与批量删除，能 *update* 才显示编辑铅笔；
- **View 现在是真正的只读**：所有字段禁用、没有提交路径、回车键失效——以前「查看」打开的是可编辑对话框；
- 会话通告的 *Create Access Key* 能力对请求作用域策略的计算修正为：以 `svc:DurationSeconds` 为条件的 `Deny`（一种只有在具体请求存在后才能求值的有效期限制）保持该能力可见——包括通配符管理动作——而无条件或登录期即可判定的 deny 现在会正确隐藏它。最终授权仍由 SILO 在请求时裁决。旧代码对*任意*条件 deny 都保持能力可见，属于过度通告。
- 新增一条 OIDC 创建/列举/查看/删除的集成回归，走 UI 的显式凭据端点，并断言预期中的自我更新拒绝。

### 写入前校验 IAM 策略 {#policy-validation}

命名策略与服务账号策略写入现在会在调用 Admin API 之前拒绝畸形文档和裸 S3 资源 ARN，并返回客户端错误。为兼容历史数据，旧策略读取仍保持宽容；但不兼容的已存策略必须先修正，才能再次保存。严格解析与资源检查位于控制台自身写入路径，而不是导入分支专有的策略 API，因此仍能维持对上游 `minio/pkg v3.6.1` 的源码构建下限。

### 匿名页面回归匿名 {#anonymous}

匿名对象浏览页不再发出只会产生 `Access Denied` 噪音的受保护 Object Lock/保留策略请求，并补上了语言（文/A）与暗色模式切换控件。

## 用户状态与用户组从此是两个操作 {#user-api}

切换用户的启用/禁用状态与编辑用户组过去是一条合并的 `PUT /user/{name}` 调用，两个载荷都必填，且合并的权限门控导致仅仅编辑用户组也要求 `admin:EnableUser`。2.2.0 将其拆分：

- **`PUT /user/{name}/status`**（新增）只改状态，校验取值为 `enabled|disabled`，并拒绝当前登录用户启停自己。失败的切换不再让开关脱离同步——UI 反映服务器的答案，而不是乐观翻转。
- **`PUT /user/{name}/groups`**（既有）成为用户组编辑的唯一调用，不再要求 `admin:EnableUser`。
- **`PUT /user/{name}`** 在线协议上原样保留，作为**已弃用的兼容端点**服务既有 API 消费者；未知状态在该端点现在返回 400 而不是 500。

API 契约细节（含重新生成 Swagger 客户端的注意事项）见[兼容性](#compatibility)。

## 所写即所存的数据库通知表单 {#notifications}

PostgreSQL 与 MySQL 事件目标表单围绕一个共享的 DSN 解析器/序列化器重写：

- 结构化字段与原始连接串是同一份状态：原始串在结构化字段被编辑前保持权威；一旦编辑，就重建**规范化 DSN**——PostgreSQL 使用 libpq 关键字/值引用规则，MySQL 使用感知 IPv6 方括号的 `go-sql-driver` 格式。模式切换不再破坏手工输入的字符串。
- 生成的预览**掩码凭据**；掩码不可能进入 API 载荷（载荷始终使用原始连接值）。
- 保存要求连接串与表名同时存在，清空的值会真正传播。
- 服务器现在**拒绝其配置语法会破坏的 DSN**——内嵌换行、会被解析成兄弟配置键的值（比如密码里含 `table=`）、不平衡的引号——在存储之前返回 400，且不把提交的机密回显在错误里。
- 各通知目标（Kafka、Redis、MQTT、NATS、Webhook）的通用密码与令牌字段渲染为密码输入框，包括被环境变量覆盖的值。

### 诚实的重启标记 {#restart}

配置的新增、更新、删除、重置现在尊重**服务器实际返回的是否需要重启**，而不是硬编码「需要重启」（或者更糟——弄丢它）。待重启标记是单调的：一旦有操作要求重启，后续不要求重启的操作不能清除它——只有真正的服务重启才能。

### 上传提示 {#upload-advisory}

超过 5 GiB 的浏览器上传会收到不阻断的提示：控制台以单个不可续传的请求上传，这个量级应该用 `mcli` 的分片上传。

## 会话、指标认证与 i18n 加固 {#hardening}

- **会话快速失败。** 匿名/空会话立即得到 401，而不是挂在一个空凭据的 Admin 请求上。控制台同时接受规范的 `401` 与旧式 `403` 无效会话响应；过期会话的重定向感知子路径——部署在 `/console/` 下的控制台在自己的基路径内重定向。
- **Prometheus Basic 认证全路径生效。** 健康检查与根路径回退探测现在都发送 Basic 凭据（以前只发 Bearer，导致 Basic 认证的 Prometheus 让所有仪表盘组件被禁用），Bearer 令牌保持优先，且所有响应体都被排空，keep-alive 连接得以真正复用。
- **占位符替换在构造上转义安全。** 翻译占位符填充使用一趟式字面格式化器：值中的 `$&`、`$1`、`` $` ``、反引号、花括号保持字面，重复占位符全部填充，并有一个 AST 源码守卫测试禁止不安全的 `String.replace` 模式回归。

## 工具链与依赖 {#dependencies}

### Go 1.27 基线 {#go-toolchain}

| 组件 | 2.1.1 | 2.2.0 |
|:--|:--|:--|
| `go` 指令、构建镜像、CI 矩阵 | `1.26.5` / `1.26.x` | `1.27.0` / `1.27.x` |
| `golang.org/x/crypto` | v0.54.0 | v0.55.0 |
| `golang.org/x/net` | v0.57.0 | v0.58.0 |
| `golang.org/x/text` | v0.40.0 | v0.41.0 |
| `golang.org/x/mod` | v0.37.0 | v0.40.0（关闭 [CVE-2026-56864/-56865](https://pkg.go.dev/vuln/GO-2026-6180)）|
| `golang.org/x/tools` | v0.47.0 | v0.49.0 |

### SILO 分支 {#silo-forks}

```go
require github.com/minio/pkg/v3 v3.6.1

replace github.com/minio/pkg/v3 => github.com/pgsty/silo-pkg/v3 v3.12.1
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260806055018-b0021fd01ccb
```

- **`silo-pkg` 3.12.1 是正式发布依赖。** [`pgsty/silo-pkg` v3.12.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) 已于 2026-08-25 发布，控制台直接固定它。它建立在 [3.12.0](/zh/blog/release/pkg-3.12.0/) 之上，继承策略资源边界加固、条件键查找、LDAP 与证书监视器修复，以及 Go 1.27 / etcd 3.7 依赖基线。
- **`mc` 库依赖切换到 `pgsty/mc` 分支**，使用日期式伪版本；导入路径不变。
- **`require` 行刻意停留在上游 `v3.6.1`。** Go 会忽略依赖模块中的 `replace` 指令：下游模块 require 本控制台时，解析到的是*上游* `minio/pkg`，而 SILO 的 `v3.12.1` 标签在上游并不存在。要求真实上游标签保证控制台对下游可解析；replace 只在控制台自身构建时应用分支。最终 CI 针对上游 v3.6.1 验证了公共源码构建表面。注意这只是编译层兼容——没有自带顶层 replace 的下游构建得到的是上游*行为*，不含分支的 SILO 专有 IAM 语义。
- **`go-systemd` 回钉到 v22.6.0**：v22.7.0 在 NetBSD 上使用了那里不存在的 `CLOCK_MONOTONIC`，无法编译；钉住直到上游修复发布。

### etcd 3.7.1——仅客户端库 {#etcd-3-7}

三个 etcd Go 模块一起从 3.6.8 移到 3.7.1，关闭 TLS 监听器拒绝服务漏洞 [GO-2026-6107 / CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107)。etcd 3.7 移除了遗留 protobuf 实现并使 `clientv3.New` 变为非阻塞——这些迁移只影响自行构造客户端或内嵌服务器的消费者。控制台两者都不做：它唯一的 etcd 路径是 `silo-pkg/quick` 操作一个已创建的客户端，只用普通的 v3 `Get`/`Put`。**本次升级只涉及编译进二进制的客户端库**——不触碰运维方的 etcd 服务器、集群数据或部署拓扑；服务器升级到 3.7 仍需遵循 etcd 官方的逐 minor 升级流程。

### 第三方维护保持克制 {#third-party}

最终版本在独立兼容性审查后把 `minio-go` 升级到 v7.3.0，迁移其 INI 导入路径，并增加 lifecycle-filter XML 兼容覆盖。控制台侧的兼容解码器可以接受旧服务器返回的 legacy AccountInfo tag payload。其他已接受的维护变更包括 `jwx` v2→v3 与 `httprc` v3、`go-openapi/swag/conv`+`typeutils` 0.28.0、`grpc-gateway` 2.29.0、`cheggaaa/pb` 1.0.30 和 `go.yaml.in/yaml/v3` 3.0.5；无关的更大规模 go-openapi、`pb/v3`、压缩库与测试库升级仍然推迟。

前端方面，漏洞检查工作流扩展到 push、手动触发与开发依赖，使用不可变安装；刷新了有漏洞的传递依赖解析（`fast-xml-parser` 5.11、`nanoid` 3.3.18、`@babel/core` 7.29.7），移除了死导出与未使用的 `http-status-codes` 依赖。`fast-xml-parser` 5.x 新的传递依赖树（`@nodable/entities`、`is-unsafe`、`anynum`、`fast-xml-builder`、`path-expression-matcher`、`xml-naming`）在本次评审中做过供应链核查：六个包全部由 fast-xml-parser 作者本人的账号与组织发布，安装代码不含执行/网络/外传模式，且整棵树仅用于开发——不进入浏览器产物。

## 安全评审 {#security}

- 发布树上的 `govulncheck`：**零个可达的漏洞符号，零个受影响的导入包**。Swagger 构建工具单独扫描，同样干净。
- 依赖迁移关闭的漏洞：[CVE-2026-73500](https://pkg.go.dev/vuln/GO-2026-6107)（etcd TLS 监听器 DoS）、[CVE-2026-56864 / CVE-2026-56865](https://pkg.go.dev/vuln/GO-2026-6180)（x/mod 校验）。
- 仍会报告、但依旧不可达：模块级 [GO-2026-5932](https://pkg.go.dev/vuln/GO-2026-5932) openpgp 公告——控制台不导入 `x/crypto/openpgp`，且该公告没有修复版本。
- 文本预览按 XSS 攻击面评审（见[上文](#text-preview)）；其回归套件包含活动载荷测试。
- 权限门控修复属于 UI 真实性修复：2.1.1 中服务端授权从未被绕过；只是控制台显示了不该显示的控件。

## 兼容性 {#compatibility}

**部署层面一切不变：** 环境变量、配置格式、命令、二进制名、systemd 单元、端口、嵌入数据布局均无变化。发布二进制保持自包含；Go 1.27.0 仅是构建期要求。

**HTTP API 契约**（控制台自身的 REST API）：

| 路由 | 变更 |
|:--|:--|
| `PUT /user/{name}` | 线协议不变；标记弃用。OperationId 由 `UpdateUserInfo` 改名 `UpdateUserInfoLegacy`，请求体模型改名 `legacyUpdateUser`（结构相同）。未知状态：500 → 400。 |
| `PUT /user/{name}/status` | **新增。** 仅状态请求体（`enabled`/`disabled` 枚举，违反返回 422），返回的用户对象只含访问密钥与状态——客户端不得从中读取用户组数据。 |
| `updateUser` 模型 | 变为仅状态且带枚举——**对按 spec 生成代码的消费者是破坏性变更**；旧结构以 `legacyUpdateUser` 延续。 |
| 对象下载 | 错误语义变化：坏 range 500→416（附 `Content-Range: bytes */N`），空对象 range 500→200，`Stat` 失败 500→真实 S3 状态码，ZIP 失败从静默局部 200→可见失败，206 响应携带 `Content-Length`。 |
| 列表与 WebSocket | `size` 总是序列化，包括 `0`。纯增量。 |
| `PUT /configs` | 新增一类 400：拒绝服务器配置语法会破坏的数据库 DSN。 |
| 配置重置/删除 | 响应中的 `restart` 反映服务器的真实答案，不再恒为 `true`。 |
| `GET /session` | 空凭据主体返回 401；通告的 Create-Access-Key 能力计算更严格（见[服务账号](#service-accounts)）。 |

> [!NOTE]
> **如果你从 `swagger.yml` 生成客户端 SDK：** `UpdateUserInfo` 操作现在指向 `/user/{name}/status` 且请求体仅含状态。调用生成的 `UpdateUserInfo` 符号的代码依旧能编译，但目标已是新路由；旧的合并调用是 `UpdateUserInfoLegacy`。重新生成时请审计调用点。

**运维者可能注意到的行为变化：**

1. 对部分可读前缀的文件夹/ZIP 下载**失败，而不是静默省略**不可读对象（[详情](#zip-integrity)）。
2. Range 解析比 Go 的宽容默认严格；畸形 range 头（`bytes=-0`、空元素）现在得到 416 而非尽力处理。
3. 只是碰巧能用的数据库通知配置（DSN 在写入途中被配置语法破坏的那种）现在被前置拒绝并返回 400。
4. 策略无条件拒绝创建访问密钥的会话不再显示创建控件（以前任意条件式拒绝都保持可见）。
5. 待重启指示会持续到真正重启为止，不再会被后来一次无关的配置变更清除。
6. 如果控制台前面的反向代理压缩了 `/api/v1/…/download` 响应，文本预览的严格 `Content-Length` 校验会把所有预览判为错误。控制台自身只压缩静态资产——请让代理对 API 响应保持不压缩。

## 回归评审 {#regression-review}

由于本版本重写了下载路径并更换了共享策略库的提供方，v2.1.1 至今的完整 diff 经过了五路并行的对抗式复审（Go API；对象浏览器预览/下载；权限门控与服务账号；表单/i18n/会话；依赖/构建/CI），每一路都专门猎捕「2.1.1 里正常、现在被悄悄改变」的行为。

**结论：未发现任何非刻意的回归。** 所有确认的行为差异都属于上文记录的刻意变更。评审确实揪出了两个此前就存在的小型 UI 守卫缺陷——死属性被修复激活后，谓词参数类型一直就不对的问题显形了：

- 「不能删除 Default IDP 配置」的行守卫拿行对象与字符串 `"Default"` 比较，因此永远不生效（`IDPConfigurations.tsx`）；
- 「不能删除环境变量覆盖的 Webhook 端点」的行守卫存在同样的对象-字符串错配，同样失效（`WebhookSettings.tsx`）。

两者都不是 2.2.0 的回归——这两个谓词在 2.1.1 里整体就是死代码——且两处服务端仍然执行真实规则。它们作为发布后的后续项继续记录。另有两处锋利边缘记为已知限制而非缺陷：新的 PostgreSQL DSN 解析器在填充结构化字段时只接受规范的 `key=value` 语法（不常见但 libpq 合法的 DSN 会显示为空结构化字段，此时编辑结构化字段会用这些字段重建 DSN）；TestCafe/Playwright 覆盖断言的是 UI 门控，真实服务器的拒绝路径覆盖仍由集成套件承担。

## 验证 {#verification}

发布决策综合了本地候选阶段证据，以及在精确标签树 [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8) 上执行的远端门禁：

**本地发布准备门禁** —— `go build ./...`、`go vet ./...`（含 `-tags testrunmain`）、`gofmt`、`golangci-lint`、`go test -race ./...`、`go tool swagger validate`、`govulncheck`、TypeScript `tsc`、Playwright、Prettier、knip、linux/amd64 与 linux/arm64 发布标签交叉编译、`go mod verify`。

**嵌入资产确定性** —— 前端经完整流水线（`yarn build` + 嵌入优化）从源码重建，与提交的 `web-app/build` 对比：**逐字节一致，零脏文件**。早期候选 `19047161f` 之后的九个提交修改 Go 兼容性、workflow 与浏览器测试时序，没有修改产品前端源码或嵌入资产。

**最终树 CI 完整矩阵** —— [Workflow 32888892876](https://github.com/pgsty/silo-console/actions/runs/32888892876) 报告 32 个成功 job，另有一个明确禁用的 React 测试占位项。覆盖 lint、semgrep、Go 与 API 测试、五个交叉编译目标、Swagger 漂移、最新 MinIO 源码构建、分布式集成、站点复制、封闭 SSO、完整 TestCafe 权限矩阵、subpath-nginx、Playwright 与覆盖率门禁。[Vulnerability Check 32888899120](https://github.com/pgsty/silo-console/actions/runs/32888899120) 在同一提交上两个 job 全部通过。

**发布流水线** —— [goreleaser 32916237254](https://github.com/pgsty/silo-console/actions/runs/32916237254) 针对 `v2.2.0` 的两个 job 全部通过，并发布公开 GitHub Release。

**下游契约** —— 在删除全部 `replace` 的临时树中，`go mod tidy` + `go build ./...` 针对上游 `minio/pkg v3.6.1` 成功，证明分支替换不会把分支独有符号泄漏进公共模块表面。

**本周期一并交付的测试基础设施修复**（让上述门禁真正起门禁作用）：Docker 承载的集成/复制/SSO 套件回到 `testrunmain` 构建标签之后（裸 `go test ./...` 不再试图启动容器）；SSO 门禁封闭化——不再 `sudo` 修改 `/etc/hosts`、不再临时 pip 安装、固定 SILO 镜像、自选端口、真实清理；集成门禁断言新的 416 range 语义并停止把 PostgreSQL fixture 绑定到主机端口；浏览器门禁通过发布 fixture 端口实现脱离 Linux 运行；修复了残存的品牌重塑前「MinIO administrator」选择器；有状态的 TestCafe 套件改为串行；Playwright CI 以不可变方式安装提交的锁文件。

## 发布制品 {#release-artifacts}

[v2.2.0 GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.2.0) 公开发布：

1. 六个独立二进制：Linux amd64/arm64/armv6、macOS amd64/arm64、Windows amd64；
2. 九个 Linux 软件包：amd64、arm64、armv6 各自的 DEB、RPM 与 APK；
3. `silo-console_2.2.0_checksums.txt`，以及 GitHub 为每个制品记录的 SHA-256 digest。

本文核实的是这些制品、标签与 Release 页面；不声称另有独立分发的容器镜像或 detached signature。

## 相关提交 {#related-commits}

- [`16960f7ab`](https://github.com/pgsty/silo-console/commit/16960f7ab894ee8c1750ad9a6a93f984f5cd5077) — fix: keep unknown downloads indeterminate
- [`5968bb37d`](https://github.com/pgsty/silo-console/commit/5968bb37df0f340398f1283a2a63f2c1c9e9ad5f) — chore(deps): align the SILO Go dependency stack
- [`288ab1240`](https://github.com/pgsty/silo-console/commit/288ab12401f1d077511840a790dc697c5295e789) — fix: harden sessions, metrics, and translations
- [`ecf3bb492`](https://github.com/pgsty/silo-console/commit/ecf3bb492691b5bb81d83473321aec4f376a33d7) — fix: harden object previews and downloads
- [`902d9650d`](https://github.com/pgsty/silo-console/commit/902d9650d491723a63dceca7e7f866a2311ce5e4) — chore: tighten dependency and test gates
- [`194c70c7a`](https://github.com/pgsty/silo-console/commit/194c70c7a81bc08716be12b12e87e384dfc89425) — build: prepare SILO Console v2.2.0
- [`927b44e26`](https://github.com/pgsty/silo-console/commit/927b44e26a70ddbefc610371627d1aaddee94697) — fix: harden database notification forms
- [`da2191be9`](https://github.com/pgsty/silo-console/commit/da2191be97ef279c9316c38996ac8c8c0209d26d) — fix: clarify console upload and secret limits
- [`6141c2445`](https://github.com/pgsty/silo-console/commit/6141c2445f3f2872553003021093d84137c742e5) — build: refresh SILO Console v2.2.0 assets
- [`097e76155`](https://github.com/pgsty/silo-console/commit/097e761559b62695e34d3543543d55189bce19c5) — chore(deps): bump the shared package fork to v3.12.0
- [`99ca523d6`](https://github.com/pgsty/silo-console/commit/99ca523d693c8b0b6b3523c615e8079125663aa3) — fix: split user status updates out of the combined user route
- [`f4097992f`](https://github.com/pgsty/silo-console/commit/f4097992f1a25ecadf5c874649885187b1c45768) — fix: honor the server restart result for configuration changes
- [`f1280032a`](https://github.com/pgsty/silo-console/commit/f1280032a8462de1fd00f60626f50bc11045b033) — fix: restore permission-gated table row actions
- [`24ce0af97`](https://github.com/pgsty/silo-console/commit/24ce0af974a3d1fe31449cb3d78e1a0935692dbf) — fix: keep request-scoped access key conditions visible in the console
- [`92e8f4e65`](https://github.com/pgsty/silo-console/commit/92e8f4e65fefad32581cfc86bd2a36f4305b7bd2) — fix: pass the object size into the preview and share dialogs
- [`8f6fb3c78`](https://github.com/pgsty/silo-console/commit/8f6fb3c78e9bd5aed73386bf0c709a143ff4fa0f) — test: make the SSO gate hermetic and pin it to a SILO release
- [`384a2cb95`](https://github.com/pgsty/silo-console/commit/384a2cb95abe5db6ecbbe6edbaef8b1dd9c13840) — build: refresh SILO Console assets and record the changes
- [`a73cda376`](https://github.com/pgsty/silo-console/commit/a73cda376148a0ac19f9f714dd18d5925399ca1d) — test: fix the integration gate's stale range and host port
- [`cf5049c1d`](https://github.com/pgsty/silo-console/commit/cf5049c1df59092aea3f9caea7f5f8e64e0333a6) — test: make the browser gates runnable and fix a stale selector
- [`6fa19d857`](https://github.com/pgsty/silo-console/commit/6fa19d8575f6f0a42954747a16a43d3b9cde1d97) — fix: complete service account permission boundaries
- [`7e57771a4`](https://github.com/pgsty/silo-console/commit/7e57771a44495e7c23e21dcff8f19b171d60c672) — build: refresh SILO Console assets
- [`57cfe7aa0`](https://github.com/pgsty/silo-console/commit/57cfe7aa078361e0e1d41897e460adef1cd1e5a3) — fix: restore downstream and browser release gates
- [`19047161f`](https://github.com/pgsty/silo-console/commit/19047161fa0e6ad6436057e5cc996ac6eb0751e4) — test: stabilize permissions browser gates
- [`e37dec873`](https://github.com/pgsty/silo-console/commit/e37dec873bf1a2f8e15b6937aa391da2b9626ba4) — fix: validate IAM policies before writes
- [`28505ed23`](https://github.com/pgsty/silo-console/commit/28505ed238084b0df4f2026b35adbb2145969cb4) — chore: update minio-go to v7.3.0
- [`16abb971e`](https://github.com/pgsty/silo-console/commit/16abb971e12610a333f3f38a3cb9f52d815f18c9) — ci: harden validation and release gates
- [`2ddfcd036`](https://github.com/pgsty/silo-console/commit/2ddfcd0361b537a5a6ab531600bd3d37f408cf59) — fix: accept legacy AccountInfo tag payloads
- [`31332bca9`](https://github.com/pgsty/silo-console/commit/31332bca9456a1b3340b98fa9108650216578eaf) — fix: preserve policy source compatibility
- [`3a8251086`](https://github.com/pgsty/silo-console/commit/3a82510863366abc2ed7c865f12f4e0bb1562a2a) — ci: allow permission tests to finish
- [`c159fff78`](https://github.com/pgsty/silo-console/commit/c159fff78af92ec5ee237f3c4f289a11461cb401) — ci: serialize shared-role permission tests
- [`2e91cdf9a`](https://github.com/pgsty/silo-console/commit/2e91cdf9afa71f588d467a785e922fb9b54e0a40) — test: wait for watch controls to become ready
- [`7dc4258a6`](https://github.com/pgsty/silo-console/commit/7dc4258a6a33b6e01b5b3bae8a0fd63f02b3bad8) — test: allow asynchronous UI controls to settle

链接：

- [SILO Console 源码](https://github.com/pgsty/silo-console) · [v2.2.0 Release](https://github.com/pgsty/silo-console/releases/tag/v2.2.0)
- [silo-pkg 3.12.1 Release](https://github.com/pgsty/silo-pkg/releases/tag/v3.12.1) · [silo-pkg 3.12.0 发布说明](/zh/blog/release/pkg-3.12.0/)
- [SILO 官网](https://silo.pgsty.com/zh/) · [文档](https://silo.pgsty.com/zh/docs/)
