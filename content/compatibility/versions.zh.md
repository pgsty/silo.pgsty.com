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
| <span style="white-space:nowrap">独立<br>Console</span> | [v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) | pkg v3.13.3；MC 源码 `c8aa5d25a63a`；上游 SDK `0e78d3f18efe`；对象浏览器分页 |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-13T00-00-00Z" style="white-space:nowrap">20260913</a> | pkg v3.14.0；上游 SDK `60bd07042d49`；软件包版本 `20260913000000.0.0` |
| 共享 pkg | [v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) | 独立模块路径 `github.com/pgsty/silo-pkg/v3`；密码能力拆分；上游 SDK `60bd07042d49` |

发布说明：[Server 20260903](/zh/blog/release/silo-20260903/)、
[Console v2.4.0](/zh/blog/release/console-2.4.0/)、
[mcli 20260913](/zh/blog/release/mcli-20260913/)、[pkg v3.14.0](/zh/blog/release/pkg-3.14.0/)。
已发布的 Server 镜像仍捆绑原来的客户端与 Console。安装独立组件的新版本不会替换 Server 内嵌的组件。
软件包仓库镜像可能晚于 GitHub 更新；[下载页](/zh/download/)直接链接已发布的制品。

## 主分支协调后的源码 {#source}

9 月 13 日更新通过 [pkg #7](https://github.com/pgsty/silo-pkg/pull/7)、
[MC #42](https://github.com/pgsty/mc/pull/42)、
[Console #53](https://github.com/pgsty/silo-console/pull/53) 与 [#54](https://github.com/pgsty/silo-console/pull/54)、
[Server #181](https://github.com/pgsty/silo/pull/181) 合入。

- **pkg：** `v3.14.0` → `827f8109ff11bf6239a35d8d6d137cb5738539c3`。
- **MC：** `v0.0.0-20260913012246-4f609a4da3bb` → 已发布的 20260913 标签。
- **Server 选择的 Console：** `v0.0.0-20260913015128-417559bb2c97`；经 `449c185a8d14` 合入 main，源码树相同。
- **Server 依赖集成提交：** `5d955b5b7444f8a3ab550ce92713607998f89c0d`。
- **已核对的 Server main：** [`9b4ae82a29cc`](https://github.com/pgsty/silo/commit/9b4ae82a29cc2290fb5be7b551ec3d8cf7acdd99)，包含下述修复及集成测试夹具修正。
- **上游 minio-go：** `v7.3.1-0.20260910142817-60bd07042d49`。

**Server 与 Console 最新标签之后的改动尚未发布。** 其中包括[密码权限拆分](/zh/compatibility/password-permissions/)、
Console 流式 ZIP 下载与新版镜像发布门槛，以及 Server 后续的存储、复制和签名头修复。
Server 主分支现在构建 curl 8.22.0、捆绑 mcli 20260913；现有 Server 镜像保留发布时的内容。
[Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md) 与
[Console changelog](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md) 将这些改动列为 Unreleased。

最新已发布的 Server 受 [SN-2026-011](/zh/blog/security/20260913-signed-header-status/) 影响。
修复已在 main；只升级 pkg、mcli 或独立 Console 无法修补已安装的 Server。
源码验证和漏洞扫描通过，不代表修复版 Server 二进制已经发布。

### 存储、IAM 与 HTTP 修复 {#september-reliability}

以下改动已合入 Server main，尚未进入已发布的 Server 20260903。确认某个构建是否包含修复时，应核对所链接的 PR 与源码记录。

| 范围 | <span style="white-space:nowrap">已合并 PR</span> | 运维可见行为 |
| --- | --- | --- |
| <span style="white-space:nowrap">多池存储</span> | [#188](https://github.com/pgsty/silo/pull/188)<br>[#189](https://github.com/pgsty/silo/pull/189) | 普通单对象版本 DELETE 协调各池副本，副本协调保留标签状态；移除可选的 GET 访问频率池间分层功能。 |
| <span style="white-space:nowrap">分片完成条件</span> | [#190](https://github.com/pgsty/silo/pull/190) | 前置条件使用所有池中的逻辑最新对象，避免旧副本接受过期 ETag，或拒绝当前 ETag。 |
| <span style="white-space:nowrap">普通条件 PUT</span> | [#207](https://github.com/pgsty/silo/pull/207) | 公开写入条件使用所有池中的逻辑当前对象，包括正在退役或再平衡的池；可读性及目标版本行为变化见[下文](#conditional-put)。 |
| <span style="white-space:nowrap">IAM 撤销</span> | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | 节点间删除通知重新加载已提交状态；持久化删除版本与撤销边界，防止旧站点事件重放恢复已撤销身份或旧授权。 |
| <span style="white-space:nowrap">标签与删除标记</span> | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS 复制保留标签修订时间；删除标签推进修订并抵御延迟事件；删除标记清除在 MRF 恢复时保留标记身份和重试状态。 |
| <span style="white-space:nowrap">复制元数据</span> | [#194](https://github.com/pgsty/silo/pull/194) | 恢复复制元数据时，不再把传输用的 `aws-chunked` 编码重新写入对象元数据。 |
| <span style="white-space:nowrap">请求头超时</span> | [#196](https://github.com/pgsty/silo/pull/196) | `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` 正确传入 HTTP 服务，对 HTTP/1 请求头设置绝对读取期限，持续少量发送字节也无法延长；正文保留既有滚动空闲超时。 |

**升级与兼容性要求：**

- **IAM 要求所有参与服务器协调升级。** 不支持共享 IAM 后端的新旧节点混用，也不支持滚动降级。备份完整 IAM 存储及所需加密材料，普通管理导出不包含删除历史。同名父身份重建前签发的旧凭据可能需要重新签发；升级前已经丢失的删除历史无法自动重建。具体操作见 [IAM 升级与回滚说明](/zh/operations/replication/iam-upgrade/)。
- **不可读池会更一致地使写入、删除失败。** 即使另一个池还能处理 GET/HEAD，只要任一池元数据不可读，条件式分片上传完成就会失败。普通版本 DELETE 在池不可读或清理失败时也返回错误；读取仲裁不足返回 `503 SlowDownRead`，应在恢复后重试。出站删除复制尚未完成时，请求成功不代表每块磁盘都已立即物理删除。
- **Server 20260903 从未包含访问频率池间分层。** 只有使用过该实验功能的构建需要按[迁移说明](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/bucket/lifecycle/access-tiering-removal.md)清理配置和 XML。普通生命周期过期、远程层迁移、再平衡与池退役仍可使用。
- 清除操作的审计状态由 `COMPLETE` 规范为 `COMPLETED`。历史异常标签修订可能失败并重试，本次修复不会重建其历史。较短的请求头超时也会限制 TLS 握手读取窗口；它不会给 HTTP/1 上传、下载新增总时长限制。

[R4–R8 集成记录](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/r4-r8-integration/README.md)保留了源码哈希、本地测试及验收边界。PR #196 合并前的 11 项检查全部通过；这些结果证明源码验收，不代表新版本发布或生产集群升级。

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
- **分片上传列表：** [#79](https://github.com/pgsty/silo/issues/79) 仍然开放。[设计记录](/zh/blog/design/list-multipart-uploads/)中的前缀、分页与原始对象键发现限制，不属于上面的分片上传完成修复。
- **Console 对象分享：** [Console #52](https://github.com/pgsty/silo-console/issues/52) 仍然开放，本地修复尚未合入。[拟议的请求限制](/zh/reference/minio-server/settings/console/#object-sharing)尚未进入当前选择的 Console 源码或已发布的 Server、Console。

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
