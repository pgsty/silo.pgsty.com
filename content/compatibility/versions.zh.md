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
- **Server 选择的 Console：** `v0.0.0-20260916034812-56dfe455ac2f`；经 [`60aa9492779a`](https://github.com/pgsty/silo-console/commit/60aa9492779a67d2f5131a892dea7aa0da5e133c) 合入 main，源码树相同。
- **Server 的 Console 集成提交：** [`2fabd436c0b1`](https://github.com/pgsty/silo/commit/2fabd436c0b18b6f31536889af27a376e718483c)，通过 [#209](https://github.com/pgsty/silo/pull/209) 合入。9 月 13 日选择的其他组件版本保持不变。
- **已核对的 Server main：** [`3c26a8b0b5bd`](https://github.com/pgsty/silo/commit/3c26a8b0b5bd404d594d7e1d77f73a53ffbb1fca)，包含下述修复。
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
| <span style="white-space:nowrap">IAM 撤销</span> | [#191](https://github.com/pgsty/silo/pull/191)<br>[#192](https://github.com/pgsty/silo/pull/192) | 节点间删除通知重新加载已提交状态；持久化删除版本与撤销边界，防止旧站点事件重放恢复已撤销身份或旧授权。 |
| <span style="white-space:nowrap">标签与删除标记</span> | [#193](https://github.com/pgsty/silo/pull/193)<br>[#196](https://github.com/pgsty/silo/pull/196) | SSE-KMS 复制保留标签修订时间；删除标签推进修订并抵御延迟事件；删除标记清除在 MRF 恢复时保留标记身份和重试状态。 |
| <span style="white-space:nowrap">复制元数据</span> | [#194](https://github.com/pgsty/silo/pull/194) | 恢复复制元数据时，不再把传输用的 `aws-chunked` 编码重新写入对象元数据。 |
| <span style="white-space:nowrap">请求头超时</span> | [#196](https://github.com/pgsty/silo/pull/196) | `--read-header-timeout` / `MINIO_READ_HEADER_TIMEOUT` 正确传入 HTTP 服务，对 HTTP/1 请求头设置绝对读取期限，持续少量发送字节也无法延长；正文保留既有滚动空闲超时。 |

**升级与兼容性要求：**

- **IAM 要求所有参与服务器协调升级。** 不支持共享 IAM 后端的新旧节点混用，也不支持滚动降级。备份完整 IAM 存储及所需加密材料，普通管理导出不包含删除历史。同名父身份重建前签发的旧凭据可能需要重新签发；升级前已经丢失的删除历史无法自动重建。具体操作见 [IAM 升级与回滚说明](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/site-replication/iam-revocations.md#protocol-and-supported-upgrade)。
- **不可读池会更一致地使写入、删除失败。** 即使另一个池还能处理 GET/HEAD，只要任一池元数据不可读，条件式分片上传完成就会失败。普通版本 DELETE 在池不可读或清理失败时也返回错误；读取仲裁不足返回 `503 SlowDownRead`，应在恢复后重试。出站删除复制尚未完成时，请求成功不代表每块磁盘都已立即物理删除。
- **Server 20260903 从未包含访问频率池间分层。** 只有使用过该实验功能的构建需要按[迁移说明](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/bucket/lifecycle/access-tiering-removal.md)清理配置和 XML。普通生命周期过期、远程层迁移、再平衡与池退役仍可使用。
- 清除操作的审计状态由 `COMPLETE` 规范为 `COMPLETED`。历史异常标签修订可能失败并重试，本次修复不会重建其历史。较短的请求头超时也会限制 TLS 握手读取窗口；它不会给 HTTP/1 上传、下载新增总时长限制。

[R4–R8 集成记录](https://github.com/pgsty/silo/blob/40220bd836cbd066ca424fa4dc5dbb90057fb55a/docs/investigations/r4-r8-integration/README.md)保留了源码哈希、本地测试及验收边界。PR #196 合并前的 11 项检查全部通过；这些结果证明源码验收，不代表新版本发布或生产集群升级。

### Console 分享下载 {#console-sharing}

[Console #56](https://github.com/pgsty/silo-console/pull/56) 与
[Server #209](https://github.com/pgsty/silo/pull/209) 修复了
[Console #52](https://github.com/pgsty/silo-console/issues/52) 报告的匿名代理边界问题。
代理只允许访问已配置 S3 源地址上的对象内容 GET，拒绝跳转、系统路径以及
通过查询参数选择的非下载操作。没有新增关闭分享的环境变量，正常公共对象、
预签名和版本下载继续可用，详见[行为与设计权衡](/zh/reference/minio-server/settings/console/#object-sharing)。

Console 最终 CI 矩阵与漏洞检查在合并前通过。Server 的正式模块依赖通过了
独立与内嵌两种部署下的真实 API、浏览器分享测试，以及自身 CI 检查。
这些结果属于源码验收：Console v2.4.0 和 Server 20260903 均不包含此修复，
合并上述 PR 不会发布新的二进制或镜像。

### 仍待完成的工作 {#pending}

- **分片上传列表：** [#79](https://github.com/pgsty/silo/issues/79) 仍然开放。[设计记录](/zh/blog/design/list-multipart-uploads/)中的前缀、分页与原始对象键发现限制，不属于上面的分片上传完成修复。

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
