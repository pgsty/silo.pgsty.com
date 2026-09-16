---
title: "组件版本"
linkTitle: "组件版本"
description: "SILO 已发布组件、截至 9 月 16 日的主分支修复与协调升级要求。"
url: "/zh/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

**核对日期：2026-09-16。** SILO 的四个组件独立发布。依赖更新合入主分支，不会改变已经发布的二进制或镜像。

## 已发布组件 {#published}

| 组件 | 发行版本 | 实际包含内容 |
| --- | --- | --- |
| Server | <a href="https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z" style="white-space:nowrap">20260903</a> | pkg v3.13.2；上游 SDK `0e78d3f18efe`；mcli 20260903；内嵌 Console 源码 `464a59d73ada`，版本标识为 v2.3.0 |
| <span style="white-space:nowrap">独立<br>Console</span> | [v2.4.1](https://github.com/pgsty/silo-console/releases/tag/v2.4.1) | pkg v3.14.1；mcli 20260916；上游 SDK `32e1f32cb176`；共享下载限制、流式 ZIP 与签名制品 |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-16T00-00-00Z" style="white-space:nowrap">20260916</a> | pkg v3.14.1；上游 SDK `32e1f32cb176`；软件包版本 `20260916000000.0.0` |
| 共享 pkg | [v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1) | 独立模块路径 `github.com/pgsty/silo-pkg/v3`；CopyObject 内嵌错误处理；JWX v3.3.0 字段名转义；上游 SDK `32e1f32cb176` |

发布说明：[Server 20260903](/zh/blog/release/silo-20260903/)、
[Console v2.4.1](/zh/blog/release/console-2.4.1/)、
[mcli 20260916](/zh/blog/release/mcli-20260916/)、[pkg v3.14.1](/zh/blog/release/pkg-3.14.1/)。
内嵌部署需要在 Server 构建中显式选择 Console 与 MC。
软件包仓库镜像可能晚于 GitHub 更新；[下载页](/zh/download/)直接链接已发布的制品。

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

以下改动已合入 Server main，尚未进入已发布的 Server 20260903。确认某个构建是否包含修复时，应核对所链接的 PR 与源码记录。

| 范围 | <span style="white-space:nowrap">已合并 PR</span> | 运维可见行为 |
| --- | --- | --- |
| <span style="white-space:nowrap">多池存储</span> | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | 普通单对象版本 DELETE 协调各池副本，副本协调保留标签状态；移除可选的 GET 访问频率池间分层功能。 |
| <span style="white-space:nowrap">分片完成条件</span> | [#190](https://github.com/pgsty/silo/pull/190) | 前置条件使用所有池中的逻辑最新对象，避免旧副本接受过期 ETag，或拒绝当前 ETag。 |
| <span style="white-space:nowrap">分片发现与取消</span> | [#198](https://github.com/pgsty/silo/pull/198) | 跨 pool/set 发现持久上传，原生 marker 对应上传消失后仍能续页，取消需要多数盘确认。严格模式要求所有 writer 升级并排空旧上传，见[升级契约](/zh/blog/design/list-multipart-uploads/#implementation)。 |
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

[R4–R8 集成记录](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/r4-r8-integration/README.md)保留了源码哈希、本地测试及验收边界。PR #196 合并前的 11 项检查全部通过；这些结果证明源码验收，不代表新版本发布或生产集群升级。

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
**修复已在 main，尚未发布。** 具体行为如下：

- 普通多 pool `If-Match` / `If-None-Match` 条件使用所有池中的逻辑当前对象。
  即使另一个池仍可处理 GET，只要无法核实某池元数据，条件写入就可能失败；读取仲裁不足返回 503，应恢复可读性或完成 heal 后重试。
- 请求指定目标 `versionId` 时，公开写入条件仍比较当前对象，写入的目标版本保持请求指定的值；
  内部复制保留按指定版本检查的语义。无条件 PUT 与单 pool 条件写入保持既有行为。
- 条件覆盖成功不会清理其他池中的旧副本，升级也不能恢复历史上已接受的覆盖。
  仍沿用既有修改时间与 pool 排序，不新增全局时钟排序保证。

#190 的分片完成修复既未引入、也未修复此 PUT 问题。
最终打包候选及部署验收仍由 [#203](https://github.com/pgsty/silo/issues/203) 单独跟踪。

### 仍待完成的工作 {#pending}

- **升级与存量准备：** [#200](https://github.com/pgsty/silo/issues/200) 跟踪 [IAM 升级及恢复演练](/zh/operations/replication/iam-upgrade/)；[#201](https://github.com/pgsty/silo/issues/201) 跟踪[历史复制状态检查及修复验证](/zh/operations/replication/replica-metadata-audit/)。源码修复不会自动修复旧状态。
- **发布交付：** [#202](https://github.com/pgsty/silo/issues/202) 汇总说明和组件身份；[#203](https://github.com/pgsty/silo/issues/203) 单独验收最终制品与多进程栈，当前尚未据此发布新 Server。
- **多站删除标记收敛：** `254b19ac0` 的源端复核覆盖不了已经在网络上在途、或由另一站点重放的创建；多数确认的清除之后崩溃留下的少数标记副本，也没有证明持久的清理责任人。[#217](https://github.com/pgsty/silo/issues/217) 跟踪接收端方案。清除修复的三站证据来自组合构建，不是最终 main；见[设计记录](/zh/blog/design/replication-reliability/#third-round-limits)。
- **滚动重启期间的列举：** 在包含 `8d06424b1` 的构建上，四节点滚动重启叠加并发覆盖写时，27,966 次成功 LIST 中有 2,624 次少了一到四个可读的 key；稳态 20,000 次为零。内部原因尚未绑定，[#218](https://github.com/pgsty/silo/issues/218) 跟踪取证与契约裁决。滚动重启期间不要用会删除目标端对象的同步工具；见[设计记录](/zh/blog/design/list-null-version-quorum/#boundary)。
- **跨池迁移标签：** `fced86303` 有单元与 race 覆盖，修复后的八节点 rebalance/decommission 验收尚未完成。此前迁移丢失的标签需要审计，不能默认仍在。
- **分片上传列表：** [#79](https://github.com/pgsty/silo/issues/79) 保留开放，继续跟踪容量、发布验收和迟到创建写入边界。PR #198 已修复持久发现、全局分页与静态残留取消确认，但没有新增创建屏障，也没有完成大规模扫描验收。临时 10,000 上传试验未达到暂定的单页五秒目标，见[设计记录](/zh/blog/design/list-multipart-uploads/#implementation)。

## 依赖与发布顺序 {#order}

1. 核验上游 SDK 提交与需要的修复，继续使用 `github.com/minio/minio-go/v7`；退役的 `silo-go` 不再属于维护依赖图。
2. 验证并以 `github.com/pgsty/silo-pkg/v3` 发布 pkg，同时提供迁移说明；通过 Go proxy 与校验和数据库解析标签。
3. MC 更新到该 pkg/SDK，验证后发布日历标签的 mcli。Go 消费者引用其规范伪版本。
4. Console 更新直接 pkg 依赖与 MC replacement，验证嵌入前端和集成；需要正式发布时单独发布 Console，也可明确选择已合入的不可变源码提交。
5. Server 更新直接 pkg/SDK 依赖、两个 PGSTY replacement、客户端归档哈希、镜像和 Helm 客户端版本。验证完整依赖图后，再分别完成 Server 发布、镜像发布与集群升级。

Go 不继承依赖模块的 `replace`。即使 Console 已选择 MC，Server 仍必须显式选择受维护的 Console 与 MC。
Console 和 MC 保留历史 MinIO 模块路径，pkg 直接使用自己的路径。
`colorjson`/`dperf` 带入的旧 `minio/pkg/v3` 传递依赖与维护中的策略实现相互独立。

主分支栈使用 Go **1.27.1**；pkg 保留 Go **1.26** 库兼容下限，并通过 Go **1.26.8** race 测试。
Go x/* 依赖已刷新。go-systemd 实际仍选 **v22.6.0**，因为 v22.7.0 在 NetBSD 编译失败；
Console 保留 tablewriter **v0.0.5** replacement 以兼容所用 MC API。这些是有原因的兼容性固定版本。

其他依赖按具体 CVE/BUG 更新，不机械追逐新主版本。
9 月 13 日 Go 扫描没有发现可达或已导入的易受攻击包，但未使用的 OpenPGP 代码仍有模块级 **GO-2026-5932** 告警。
可达性扫描通过，不等于整个依赖图没有任何漏洞通告。

正式支持的集成对象是协调后的 PGSTY 栈；与原版上游 MinIO/MC 和其他 S3 实现的兼容属于尽力保留。

## 9 月 16 日 Server 源码核对补充 {#source-review}

固定基线 `f99ed829b5eb` 选择 pkg v3.14.0、上游 minio-go `60bd07042d49`、Console 源码 `56dfe455ac2f` 和镜像捆绑 mcli 20260913。这与独立 Console 2.4.1 的依赖图不同；后续 Server 发布须根据最终 tag 重新核对，不能由独立组件发布推断 Server 已更新。

- 分段列表经 #213 保持 **legacy 默认**；strict 仅由 `MINIO_API_MULTIPART_LISTING` 进程环境显式启用并重启，不支持共享动态配置键。严格取消的多数确认也只用于 strict。见[设置参考](/zh/reference/minio-server/settings/core/#multipart-listing)与[升级契约](/zh/blog/design/list-multipart-uploads/#implementation)。
- [多池对象一致性](/zh/blog/design/multi-pool-object-consistency/)、[条件删除](/zh/blog/design/conditional-delete/)与 [Object Lock 复制排序](/zh/blog/design/object-lock-replication-ordering/)区分逻辑当前对象、指定版本与持久化锁。
- [联邦 CopyObject](/zh/blog/design/federated-copy-object/)和 [SSE-C 副本完整性](/zh/blog/design/ssec-replica-integrity/)记录明文字节校验、复制加密与历史对象限制。
- [IAM 持久撤销](/zh/blog/design/iam-revocations/)与[桶配置收敛](/zh/blog/design/bucket-metadata-convergence/)分别说明协调升级、删除历史及默认关闭的 `MINIO_SITE_REPLICATION_METADATA_TOMBSTONES`。
- [请求头超时](/zh/blog/design/request-header-timeouts/)与 [Go 1.27 TLS/OIDC](/zh/blog/design/go127-tls-oidc-discovery/)说明各自范围。
- [九月安全纪事](/zh/blog/security/20260916-release-hardening/)列出 SN-2026-012/013/014 及不同组件的发布边界。

相关 Server 后续修复均未进入 20260903；文章中的原有 Object Lock 修复及其它已发布前置项按各自明确的版本记载。
