---
title: "组件版本"
linkTitle: "组件版本"
description: "Server 20261018 正式发布、准确组件身份与升级边界。"
url: "/zh/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

维护栈的四个组件与可选 KES 分别发布。下表记录各正式版本及其组件依赖关系。

## Server 20261018 正式发布 {#october-release}

目标标签为 `RELEASE.2026-10-18T00-00-00Z`，包版本为 `20261018000000.0.0`，选定源码为 [`0cd388c66`](https://github.com/pgsty/silo/commit/0cd388c666f8211f552604ae73448a066e9c25ce)。GitHub Release 已**正式发布**，匿名下载与 Docker Hub 镜像于 2026-10-19 完成核验。完整功能、安全、兼容性与剩余限制见 [20261018 发布说明](/zh/blog/release/silo-20261018/)。

[20261015](/zh/blog/release/silo-20261015/) 保留为历史未发布草稿，由 [20261018 正式版](/zh/blog/release/silo-20261018/#delivery)取代并交付 10 月的 Object Lock、IAM 与 LIST 修复（Server 20260916 不含这些修复）。

## 10 月组件依赖图 {#october-components}

| 组件 | Server 20261018 选用版本 |
| --- | --- |
| 嵌入式 Console | v2.4.2，`v0.0.0-20261017112417-ef2dd2c41d21` |
| MC 模块／镜像内置 mcli | 20261018，`v0.0.0-20261017101407-fa3b8bf72458` |
| Server 共享包 | `github.com/pgsty/silo-pkg/v3 v3.14.3` |
| 上游 S3 SDK | `github.com/minio/minio-go/v7 v7.4.1` |
| 构建工具链 | Go 1.27.2；Console 前端使用 Node 24.22.0 LTS |

独立 Console v2.4.2 与 mcli 20261018 仍声明 pkg v3.14.2；Server 的模块图选用 v3.14.3。v3.14.2 的[依赖更新](/zh/blog/release/pkg-3.14.2/)与 v3.14.3 的 [admin action 分类优化](/zh/blog/release/pkg-3.14.3/)保持 API、策略格式和授权语义。Server 必须显式选择 Console 与 MC 的 replacement，Go 不会继承依赖的替换配置。正式支持 PGSTY 四组件组合，对原厂 MinIO/MC 兼容尽最大努力。

## 已发布组件 {#published}

| 组件 | 当前正式版本 | 实际内容 |
| --- | --- | --- |
| Server | [20261018](/zh/blog/release/silo-20261018/) | Go 1.27.2；pkg v3.14.3；SDK v7.4.1；mcli 20261018；Console v2.4.2（`ef2dd2c41d21`） |
| 独立 Console | [v2.4.2](/zh/blog/release/console-2.4.2/) | Go 1.27.2；pkg v3.14.2；SDK v7.4.1；mcli 20261018；正确返回桶版本控制错误 |
| mcli | [20261025](/zh/blog/release/mcli-20261025/) | Go 1.27.3；pkg v3.15.1；SDK `ab93db7ba435`；包版本 `20261025000000.0.0`；Windows ZIP |
| 共享 pkg | [v3.15.1](/zh/blog/release/silo-20261025/) | 最低要求 Go 1.27.3；共享依赖更新；minio-go `ab93db7ba435`；保留策略与输出兼容性 |
| 可选 KES | [20261018](/zh/blog/release/kes-20261018/) | 独立密钥服务；Go 1.27.2；AWS SDK v2；OpenBao KV v2 与 Moto 验收 |

**Console v2.5.0 本地准备中，尚未发布：** 源码采用 Go 1.27.3、pkg v3.15.1、mcli 20261025（`dcc78d506f94`）与 minio-go `v7.4.2-0.20261020194015-ab93db7ba435`，并包含 GUI 更新和 #63 诊断 WebSocket 关闭握手修复。依赖、升级边界与状态见[统一维护公告](/zh/blog/release/silo-20261025/#console-250)。

**Server 候选联调：** 本地已集成 Go 1.27.3、pkg v3.15.1、mcli 20261025 及未发布的 Console 2.5.0 源码。IAM Reset 与存储桶列表新鲜度修复需要配套 Server 更新；上表仍列出当前正式 Server 版本。

官方镜像使用 Docker Hub：`docker.io/pgsty/silo`、`docker.io/pgsty/silo-console`、`docker.io/pgsty/mc`、`docker.io/pgsty/kes`。Console v2.4.2 的历史镜像验收见[发布记录](/zh/blog/release/console-2.4.2/#delivery)。软件包仓库镜像可能晚于 GitHub 更新。[下载页](/zh/download/)提供 Server 20261018 的公开制品与固定版本安装命令。

## 9 月 16 日依赖图 {#source}

[Console v2.4.1](/zh/blog/release/console-2.4.1/) 选择以下已发布的 pkg 与 MC 源码，
各模块身份已通过公共 Go proxy 与校验和数据库验证。

- **Console：** `v0.0.0-20260916075814-1360e26d976d` →
  [`1360e26d976d`](https://github.com/pgsty/silo-console/commit/1360e26d976d82eda395b0b2e449df8c9d49f39c)，标签 `v2.4.1`。
- **pkg：** `v3.14.1` → `fa657ef431ae22e720df37e5144cf00f67102945`。
- **MC：** `v0.0.0-20260916070421-e952aa78f10a` →
  [`e952aa78f10a`](https://github.com/pgsty/mc/commit/e952aa78f10a2b77dd525a2b7e3143bcda0cd377)，标签 `RELEASE.2026-09-16T00-00-00Z`。
- **上游 minio-go：** `v7.3.1-0.20260915093545-32e1f32cb176`。
- **JWX / strfmt / React Router：** v3.3.0 / v0.27.2 / v7.18.4。

Console 嵌入前端已按此依赖图重新构建。历史 Go 模块路径没有 `/v2` 后缀，
所以通过规范伪版本引用 Console。Server 嵌入方必须同时复制 Console 与 MC replacement，
见[Console 集成说明](/zh/compatibility/console/#source)。

升级前请检查[密码权限迁移](/zh/compatibility/password-permissions/)：
`admin:ChangeMyPassword` 与 `admin:CreateUser` 分别控制不同操作。
[Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md) 和下列源码链接
说明协调升级 Server 时涉及的存储、IAM 与 HTTP 变化。

### 存储、IAM 与 HTTP 修复 {#september-reliability}

以下改动已随 Server 20260916 发布；Server 20260903 不包含这些修复。实现范围可通过所链接的 PR 与源码记录核对。

| 范围 | <span style="white-space:nowrap">已合并 PR</span> | 运维可见行为 |
| --- | --- | --- |
| <span style="white-space:nowrap">多池存储</span> | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | 普通单对象版本 DELETE 协调各池副本，副本协调保留标签状态；移除可选的 GET 访问频率池间分层功能。 |
| <span style="white-space:nowrap">分片完成条件</span> | [#190](https://github.com/pgsty/silo/pull/190) | 前置条件使用所有池中的逻辑最新对象，避免旧副本接受过期 ETag，或拒绝当前 ETag。 |
| <span style="white-space:nowrap">分片发现与取消</span> | [#198](https://github.com/pgsty/silo/pull/198)<br>[#213](https://github.com/pgsty/silo/pull/213) | Server 20260916 默认使用 legacy 列举与取消。显式启用严格模式后，跨 pool/set 发现持久上传、在原生 marker 对应上传消失后继续分页，并要求多数盘确认取消。严格模式要求所有 writer 升级并排空旧上传，见[升级契约](/zh/blog/design/list-multipart-uploads/#implementation-20260916)。 |
| <span style="white-space:nowrap">普通条件 PUT</span> | [#207](https://github.com/pgsty/silo/pull/207) | 公开写入条件使用所有池中的逻辑当前对象，包括正在退役或再平衡的池；可读性及目标版本行为变化见[下文](#conditional-put)。 |
| <span style="white-space:nowrap">IAM 撤销</span> | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | 节点间删除通知重新加载已提交状态；持久化删除版本与撤销边界，防止旧站点事件重放恢复已撤销身份或旧授权。 |
| <span style="white-space:nowrap">删除标记清除</span> | [`eb4f5e5b3`](https://github.com/pgsty/silo/commit/eb4f5e5b3)<br>[`254b19ac0`](https://github.com/pgsty/silo/commit/254b19ac0)<br>[`358ab38fb`](https://github.com/pgsty/silo/commit/358ab38fb) | 指定版本的清除不再在缺少该标记的盘上创建标记；对已缺失版本的重试须有写仲裁多数的缺失票才确认；heal 后的标记保留复制与清除元数据；排队中的标记创建任务在发送前先在复制锁内复核源端。剩余边界见[下文](#pending)、[#217](https://github.com/pgsty/silo/issues/217) 与[复制可靠性记录第三轮](/zh/blog/design/replication-reliability/#third-round)。 |
| <span style="white-space:nowrap">盘间分歧下的列举</span> | [`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b1) | 当更新的少数盘排在前面时，仍保留达到列举仲裁的 null 对象版本。滚动重启叠加并发覆盖写时，成功的 LIST 仍可能漏掉可读的 key；见[下文](#pending)、[#218](https://github.com/pgsty/silo/issues/218) 与[设计记录](/zh/blog/design/list-null-version-quorum/)。 |
| <span style="white-space:nowrap">跨池迁移标签</span> | [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) | rebalance 与 decommission 对普通和分片写入都把对象标签及其修订字段带到目标池。此前迁移已丢失的标签不会恢复；见[多池对象一致性](/zh/blog/design/multi-pool-object-consistency/#migration-tags)。 |
| <span style="white-space:nowrap">标签与删除标记</span> | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS 复制保留标签修订时间；删除标签推进修订并抵御延迟事件；删除标记清除在 MRF 恢复时保留标记身份和重试状态。 |
| <span style="white-space:nowrap">复制元数据</span> | [#194](https://github.com/pgsty/silo/pull/194) | 恢复复制元数据时，不再把传输用的 `aws-chunked` 编码重新写入对象元数据。 |
| <span style="white-space:nowrap">请求头超时</span> | [#196](https://github.com/pgsty/silo/pull/196) | `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` 正确传入 HTTP 服务，对 HTTP/1 请求头设置绝对读取期限，持续少量发送字节也无法延长；正文保留既有滚动空闲超时。 |

**升级与兼容性要求：**

- **IAM 要求所有参与服务器协调升级。** 不支持共享 IAM 后端的新旧节点混用，也不支持滚动降级。备份完整 IAM 存储及所需加密材料，普通管理导出不包含删除历史。同名父身份重建前签发的旧凭据可能需要重新签发；升级前已经丢失的删除历史无法自动重建。具体操作见 [IAM 升级与回滚说明](/zh/operations/replication/iam-upgrade/)。
- **不可读池会更一致地使写入、删除失败。** 即使另一个池还能处理 GET/HEAD，只要任一池元数据不可读，条件式分片上传完成就会失败。普通版本 DELETE 在池不可读或清理失败时也返回错误；读取仲裁不足返回 `503 SlowDownRead`，应在恢复后重试。出站删除复制尚未完成时，请求成功不代表每块磁盘都已立即物理删除。
- **Server 20260903 从未包含访问频率池间分层。** 只有使用过该实验功能的构建需要按[迁移说明](/zh/compatibility/access-tiering-removal/)清理配置和 XML。普通生命周期过期、远程层迁移、再平衡与池退役仍可使用。
- 清除操作的审计状态由 `COMPLETE` 规范为 `COMPLETED`。历史异常标签修订可能失败并重试，本次修复不会重建其历史。较短的请求头超时也会限制 TLS 握手读取窗口；它不会给 HTTP/1 上传、下载新增总时长限制。
- 带已记录标签修订的对象在显式 resync 或 heal 时**每对象多一次元数据 COPY**；当目的端按桶默认做 KMS 加密时，该复制会重写对象数据。带标签过滤的复制规则仍按删除后的（空）标签状态评估目标资格；任意站点时钟偏差不在修复后的顺序保证之内。复制双方必须都运行修复后的构建，墓碑才会被尊重——旧对端仍会丢弃空值修订。见[复制标签排序](/zh/blog/design/replicated-tag-ordering/)。

[R4–R8 集成记录](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/r4-r8-integration/README.md)保留了源码哈希、本地测试及验收边界。PR #196 合并前的 11 项检查全部通过。

### Console 分享下载 {#console-sharing}

[Console #56](https://github.com/pgsty/silo-console/pull/56) 与
[Server #209](https://github.com/pgsty/silo/pull/209) 修复了
[Console #52](https://github.com/pgsty/silo-console/issues/52) 报告的匿名代理边界问题。
代理只允许访问已配置 S3 源地址上的对象内容 GET，拒绝跳转、系统路径以及
通过查询参数选择的非下载操作。没有新增关闭分享的环境变量，正常公共对象、
预签名和版本下载继续可用，详见[行为与设计权衡](/zh/reference/minio-server/settings/console/#object-sharing)。

修复已随 [Console v2.4.1](/zh/blog/release/console-2.4.1/) 发布。
精确发布源码通过完整 CI 矩阵、漏洞检查与发布工作流；真实 API 和浏览器分享测试
覆盖独立与内嵌部署，实际下载的独立二进制也连接 SILO 测试服务通过了分享回归。

### 普通条件 PUT {#conditional-put}

[#199](https://github.com/pgsty/silo/issues/199) 的跨 pool 条件 PUT 问题已在发布版 Server 20260903 上复现。
[PR #207](https://github.com/pgsty/silo/pull/207) 的提交 `4620be394b52` 于 2026-09-16 通过全部 8 项 CI，
随后以 [`9b4ae82a29cc`](https://github.com/pgsty/silo/commit/9b4ae82a29cc2290fb5be7b551ec3d8cf7acdd99) 合入。
**修复已随 Server 20260916 发布。** 具体行为如下：

- 普通多 pool `If-Match` / `If-None-Match` 条件使用所有池中的逻辑当前对象。
  即使另一个池仍可处理 GET，只要无法核实某池元数据，条件写入就可能失败；读取仲裁不足返回 503，应恢复可读性或完成 heal 后重试。
- 请求指定目标 `versionId` 时，公开写入条件仍比较当前对象，写入的目标版本保持请求指定的值；
  内部复制保留按指定版本检查的语义。无条件 PUT 与单 pool 条件写入保持既有行为。
- 条件覆盖成功不会清理其他池中的旧副本，升级也不能恢复历史上已接受的覆盖。
  仍沿用既有修改时间与 pool 排序，不新增全局时钟排序保证。

#190 的分片完成修复既未引入、也未修复此 PUT 问题。
最终打包候选及部署验收仍由 [#203](https://github.com/pgsty/silo/issues/203) 单独跟踪。

### 仍待完成的工作 {#pending}

- **升级与存量准备：** [#200](https://github.com/pgsty/silo/issues/200) 跟踪 [IAM 升级及恢复演练](/zh/operations/replication/iam-upgrade/)；[#201](https://github.com/pgsty/silo/issues/201) 跟踪[历史复制状态检查及修复验证](/zh/operations/replication/replica-metadata-audit/)。
- **发布交付：** [#202](https://github.com/pgsty/silo/issues/202) 汇总说明和组件身份；[#203](https://github.com/pgsty/silo/issues/203) 跟踪最终制品与多进程栈验证。
- **多站删除标记收敛：** `254b19ac0` 的源端复核覆盖不了已经在网络上在途、或由另一站点重放的创建；多数确认的清除之后崩溃留下的少数标记副本，也没有证明持久的清理责任人。[#217](https://github.com/pgsty/silo/issues/217) 跟踪接收端方案；见[设计记录](/zh/blog/design/replication-reliability/#third-round-limits)。
- **滚动重启期间的列举：** [#239](https://github.com/pgsty/silo/pull/239)（已随 [Server 20261018](/zh/blog/release/silo-20261018/) 发布）承接 [#218](https://github.com/pgsty/silo/issues/218)，对符合条件的最新对象分歧进行确认，区分真实删除与读取故障，并把最终错误传递到分页响应。不增加磁盘格式、客户端参数或迁移开关；详见[最新设计与验收边界](/zh/blog/design/listing-recovery-lock-cost/)。
- **跨池迁移与历史标签：**最终 20261018 制品通过四组本地 2/3 池 rebalance/decommission，覆盖标签、版本、删除标记和中断恢复，见[十月迁移修复](/zh/blog/design/multi-pool-object-consistency/#migration-20261018)。修复前已丢失的标签须单独审计。
- **分片上传列表：** [#79](https://github.com/pgsty/silo/issues/79) 保留开放。Server 20261018 撤回默认持久扫描，并退役可选 strict 模式；公开列表重新使用节点本地缓存或精确 key 查询，完整发现、前缀／分页语义和迟到创建写入仍未解决。详见[当前契约与容量证据](/zh/blog/design/list-multipart-uploads/#implementation)。

## 依赖与发布顺序 {#order}

1. 核验上游 SDK 提交与需要的修复，继续使用 `github.com/minio/minio-go/v7`；退役的 `silo-go` 不再属于维护依赖图。
2. 验证并以 `github.com/pgsty/silo-pkg/v3` 发布 pkg，同时提供迁移说明；通过 Go proxy 与校验和数据库解析标签。
3. MC 更新到该 pkg/SDK，验证后发布日历标签的 mcli。Go 消费者引用其规范伪版本。
4. Console 更新直接 pkg 依赖与 MC replacement，验证嵌入前端和集成；需要正式发布时单独发布 Console，也可明确选择已合入的不可变源码提交。
5. Server 更新直接 pkg/SDK 依赖、两个 PGSTY replacement、客户端归档哈希、镜像和 Helm 客户端版本。验证完整依赖图后，再分别完成 Server 发布、镜像发布与集群升级。

Go 不继承依赖模块的 `replace`。即使 Console 已选择 MC，Server 仍必须显式选择受维护的 Console 与 MC。
Console 和 MC 保留历史 MinIO 模块路径，pkg 直接使用自己的路径。
`colorjson`/`dperf` 带入的旧 `minio/pkg/v3` 传递依赖与维护中的策略实现相互独立。

Console v2.4.2、mcli 20261018 与 Server 20261018 使用 Go **1.27.2**，9 月版栈使用 Go **1.27.1**。pkg v3.14.3 保留 Go **1.26** 库兼容下限；已发布的 pkg v3.15.1 和 mcli 20261025，以及准备中的 Console v2.5.0，均要求 Go **1.27.3**。
Go x/* 依赖已刷新。go-systemd 实际仍选 **v22.6.0**，因为 v22.7.0 在 NetBSD 编译失败；
Console 保留 tablewriter **v0.0.5** replacement 以兼容所用 MC API。

其他依赖按具体 CVE 与缺陷修复更新。
9 月 13 日 Go 扫描没有发现可达或已导入的易受攻击包，未使用的 OpenPGP 代码保留模块级 **GO-2026-5932** 记录。

正式支持的集成对象是协调后的 PGSTY 栈；与原版上游 MinIO/MC 和其他 S3 实现的兼容属于尽力保留。

## 9 月 16 日 Server 源码核对补充 {#source-review}

Server 20260916 源码 [`2a4d51406b7e`](https://github.com/pgsty/silo/commit/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c) 已选择 pkg v3.14.1、上游 minio-go `32e1f32cb176`、Console v2.4.1 源码 `1360e26d976d` 和 MC `e952aa78f10a`（mcli 20260916）。正式 Server 标签为 `RELEASE.2026-09-16T00-00-00Z`，包版本 `20260916000000.0.0`。

- 分段列表经 #213 保持 **legacy 默认**；strict 仅由 `MINIO_API_MULTIPART_LISTING` 进程环境显式启用并重启，不支持共享动态配置键。严格取消的多数确认也只用于 strict。见[设置参考](/zh/reference/minio-server/settings/core/#multipart-listing)与[升级契约](/zh/blog/design/list-multipart-uploads/#implementation-20260916)。
- [多池对象一致性](/zh/blog/design/multi-pool-object-consistency/)、[条件删除](/zh/blog/design/conditional-delete/)与 [Object Lock 复制排序](/zh/blog/design/object-lock-replication-ordering/)区分逻辑当前对象、指定版本与持久化锁。
- [联邦 CopyObject](/zh/blog/design/federated-copy-object/)和 [SSE-C 副本完整性](/zh/blog/design/ssec-replica-integrity/)记录明文字节校验、复制加密与历史对象限制。
- [IAM 持久撤销](/zh/blog/design/iam-revocations/)与[桶配置收敛](/zh/blog/design/bucket-metadata-convergence/)分别说明协调升级、删除历史及默认关闭的 `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES`。
- [请求头超时](/zh/blog/design/request-header-timeouts/)与 [Go 1.27 TLS/OIDC](/zh/blog/design/go127-tls-oidc-discovery/)说明各自范围。
- [九月安全纪事](/zh/blog/security/20260916-release-hardening/)列出 SN-2026-012/013/014 及不同组件的发布边界。

相关 Server 后续修复均未进入 20260903；文章中的原有 Object Lock 修复及其它已发布前置项按各自明确的版本记载。

最后的存储修复还包括 [`fced86303`](https://github.com/pgsty/silo/commit/fced8630365fd57d6116c595b65252bcd12e13be) 的迁移标签保留、[`8d06424b1`](https://github.com/pgsty/silo/commit/8d06424b126b4ac640cd076a4585b66f2ec753a6) 的 null 版本 quorum，以及 `eb4f5e5b3` / `254b19ac0` / `358ab38fb` 的版本 purge、标记元数据和排队创建修复。仍需注意 [#217](https://github.com/pgsty/silo/issues/217) 的迟到创建/崩溃残留和 [#218](https://github.com/pgsty/silo/issues/218) 的重启期间列表遗漏。

## 10 月 15 日源码验收 {#october-source}

**已纳入 Server 20261015 草稿；Server 20260916 不包含。**
[PR #233](https://github.com/pgsty/silo/pull/233) 已以
[`d94b3b3c9251`](https://github.com/pgsty/silo/commit/d94b3b3c9251af5a9dbdb2d178e892c4de75204a)
合入，修复旧版 `xl.meta` 头部复用时的缺失字段残留，并使扫描更新与最终缓存保持互斥。
存储格式、RPC 字段与依赖版本均未变化。[问题与修复说明](/zh/blog/design/stale-metadata-reuse/)
记录了确定性回归测试、双进程扫描验证、合并后 CI 和运维核验方法。
该源码修复已纳入 [Server 20261015](/zh/blog/release/silo-20261015/) 草稿，并随 [Server 20261018](/zh/blog/release/silo-20261018/) 正式发布。

## 20261015 之后纳入 20261018 的修复 {#post-20261015}

20261018 在早期草稿基础上纳入提交元数据错误分类（#232）、上传时间解析（#236）、校验和与 Console 错误（#229/#238）、IAM 管理授权及批量自查询（#242、`995439260`）、LIST 恢复与目录保留（#239、`3dd53eb81`、`2080b3d03`）、空上传父目录清理（`0f9199e0c`），以及撤回公开持久扫描（`4733e1423`）。共享包已升至 v3.14.3。最终候选还包含跨池迁移旧副本覆盖与删除标记修复（`60c7179dd`、`1748f62c7`），以及持久 STS 枚举、撤销传播和漏通知恢复（`0cd388c66`）。

具体行为、升级步骤与未完成事项以 [20261018 发布说明](/zh/blog/release/silo-20261018/)为准。原 strict 用户会失去持久列表与严格取消能力；#79 与 #217 仍未解决。
