---
title: "兼容性"
linkTitle: "兼容性"
description: "SILO 能否直接替换 MinIO？按用户影响分为 12 类兼容或改进、4 类轻微差异、8 类需要按条件检查的变化。"
url: "/zh/compatibility/"
weight: 7
type: docs
icon: fa-solid fa-code-compare
sidebar_expanded: true
---

**普通 S3 应用通常可以不改代码，用 SILO 替换 MinIO。** 常用 S3 API、SigV4、SDK 接入方式和对象磁盘布局延续上游；部署、权限及复制状态需要按下列条件检查。因此，SILO 是**有条件的 drop-in replacement**。

{{< cards >}}
{{< card title="🟢 12 类：兼容或改进" link="#compatible" >}}
正常用法无需适配，获得新增能力或正确性修复。
{{< /card >}}
{{< card title="🔵 4 类：轻微差异" link="#minor" >}}
主要影响展示、界面操作和返回信息，通常不改业务代码。
{{< /card >}}
{{< card title="🟠 8 类：按条件检查" link="#conditional" >}}
命中触发条件时，需要验证或调整部署、策略、工具及升级流程。
{{< /card >}}
{{< /cards >}}

**核对日期：2026-09-16。** 下表汇总分叉以来的源码与配套组件变化；当日已发布的 Server 仍为 **20260903**，后续源码修复不等于已经进入该发行版，具体以[组件版本矩阵](/zh/compatibility/versions/)为准。24 项是用户场景分类，**不是 API 数量、兼容率或故障概率**。

## 🟢 兼容或改进：12 类 {#compatible}

这些能力在正常用法下无需迁移适配；依赖旧错误行为、混合版本或历史异常状态的情况另列于橙色项。

| 类别与一句话变化 | 触发条件 | 影响范围与操作 | 详情索引 |
| --- | --- | --- | --- |
| <span id="g01"></span>**G01 · 完整 Web 管理控制台**<br>恢复桶、对象、用户、策略和系统的完整 Web 管理。 | 通过浏览器管理部署。 | 管理界面增强；普通 S3 应用无需改动。 | [Console 功能](/zh/compatibility/console/#scope) |
| <span id="g02"></span>**G02 · 中文界面与文本预览**<br>增加中英双语和有界、安全的文本预览。 | 切换界面语言或预览文本对象。 | 影响 Console 使用体验，不改变对象内容。 | [双语界面](/zh/compatibility/console/#i18n)、[文本预览](/zh/blog/design/console-text-preview/) |
| <span id="g03"></span>**G03 · 桶级 CORS**<br>原有 CORS 接口开始实际保存和执行逐桶跨域规则。 | 浏览器跨域访问，并配置了桶级 CORS。 | 该桶规则覆盖全局 CORS；对象访问仍需授权。 | [CORS 行为](/zh/blog/release/silo-20260903/#cors-trust) |
| <span id="g04"></span>**G04 · 原生健康检查**<br>新增 `silo healthcheck` 命令，便于容器和运维探测。 | 主动采用新探针命令。 | 原有 HTTP 健康端点继续可用。 | [命令与范围](/zh/compatibility/feature/healthcheck/#command) |
| <span id="g05"></span>**G05 · 客户端校验和审计**<br>新增 `mcli checksum verify`，读取对象并核验校验和。 | 主动运行完整性审计。 | 只读检查和报告，不修改或修复对象。 | [审计命令](/zh/reference/minio-mc/mc-checksum-verify/#command-mc.checksum.verify) |
| <span id="g06"></span>**G06 · 上传与复制校验和修复**<br>合法上传、分片完成和复制更准确地计算、保存及返回校验和。 | 使用相关上传或复制路径。 | 改善 SDK 互操作；非法请求的变化见 [O04](#o04)。 | [分片上传](/zh/blog/design/uploadpart-checksum/#decision)、[S3 修复](/zh/blog/release/silo-20260903/#s3-correctness) |
| <span id="g07"></span>**G07 · 加密与压缩处理修复**<br>修正 SSE-C、KMS、压缩与复制组合中的数据及逻辑大小处理。 | 使用这些加密、压缩或复制组合。 | 改善新请求的正确性；历史损坏不会因此全部自动修复。 | [SSE-C 与历史对象](/zh/blog/design/ssec-replica-integrity/)、[联邦复制](/zh/blog/design/federated-copy-object/) |
| <span id="g08"></span>**G08 · 桶配置并发更新修复**<br>桶配置共用元数据锁，防止并发更新互相覆盖。 | 同时修改策略、生命周期、加密等桶配置。 | 管理操作更可靠，现有调用方式不变。 | [共享配置锁](/zh/blog/release/silo-20260903/#bucket-metadata) |
| <span id="g09"></span>**G09 · 标签与对象锁复制修复**<br>复制更准确地保留并排序标签、保留期与锁状态。 | 使用标签、Object Lock 的复制或修复。 | 减少状态丢失与旧事件覆盖；混合版本见 [O07](#o07)。 | [标签排序](/zh/blog/design/replicated-tag-ordering/)、[对象锁排序](/zh/blog/design/object-lock-replication-ordering/) |
| <span id="g10"></span>**G10 · 池迁移与数据修复改进**<br>再平衡、退役及修复更准确地处理标签、版本和删除标记。 | 迁移存储池、执行 heal 或恢复复制。 | 改善元数据保留与重试；历史异常仍需检查。 | [多池一致性](/zh/blog/design/multi-pool-object-consistency/)、[复制恢复](/zh/blog/design/replication-reliability/) |
| <span id="g11"></span>**G11 · 通知与流式推送修复**<br>修正 NATS/AMQP 配置识别，以及通知、Select 等流式响应刷新。 | 使用相应通知目标或流式接口。 | 配置与事件输出更准确；旧数据库配置见 [O03](#o03)。 | [通知配置](/zh/compatibility/server/#notify-audit)、[流式响应](/zh/compatibility/server/#s3-behavior) |
| <span id="g12"></span>**G12 · 运行稳定性与资源回收**<br>修复并发采集、缓冲区所有权和连接回收等问题。 | 并发读写、指标采集或取消请求。 | 减少相关崩溃与资源问题，不代表所有负载都更快。 | [读缓冲修复](/zh/compatibility/server/#s3-behavior)、[运行与观测](/zh/compatibility/server/#observability) |
{.silo-compatibility-table}

## 🔵 轻微差异：4 类 {#minor}

普通应用通常无需调整；硬编码产品文案、指标含义或响应字段的工具仍应检查。

| 类别与一句话变化 | 触发条件 | 影响范围与操作 | 详情索引 |
| --- | --- | --- | --- |
| <span id="b01"></span>**B01 · 产品名称与展示标识**<br>横幅、日志、HTTP 产品身份及界面展示改为 SILO。 | 阅读输出，或按产品名称匹配规则。 | 展示变化；硬编码名称的脚本需调整，安装变化见 [O01](#o01)。 | [身份变化](/zh/compatibility/server/#identity)、[客户端输出](/zh/compatibility/mcli/#identity) |
| <span id="b02"></span>**B02 · 控制台列表改为分页**<br>对象列表按游标加载，排序、筛选和选择作用于当前页。 | 在 Console 浏览、筛选或批量选择对象。 | 操作习惯有变化，应用直接调用 S3 的方式不变。 | [分页边界](/zh/compatibility/console/#pagination) |
| <span id="b03"></span>**B03 · 监控与诊断信息更完整**<br>新增诊断指标，并修正配额、复制等计数或状态含义。 | 使用对应指标、仪表盘或告警。 | 原指标命名空间保留；核对相关展示和告警规则。 | [指标变化](/zh/compatibility/server/#observability)、[Console 指标](/zh/compatibility/console/#metrics) |
| <span id="b04"></span>**B04 · API 返回字段更丰富**<br>部分复制、分片和 Console 响应增加校验和或会话字段。 | 读取这些 API 的返回结果。 | 标准客户端通常可处理；拒绝未知字段的解析器见 [O05](#o05)。 | [分片响应](/zh/blog/design/complete-multipart-checksum-type/)、[复制响应](/zh/blog/design/copyobject-ssec-checksum-response/#impact)、[Console API](/zh/compatibility/console/#api-output) |
{.silo-compatibility-table}

## 🟠 按条件检查：8 类 {#conditional}

**命中条件，就检查对应项。** 这里不表示“一定很少发生”：例如部署名称变化影响迁移管理员；定制签名则主要影响自制客户端。

| 类别与一句话变化 | 触发条件 | 影响范围与操作 | 详情索引 |
| --- | --- | --- | --- |
| <span id="o01"></span>**O01 · 安装与启动配置**<br>交付物改名为 `silo` / `mcli`，需核对服务、镜像、目录和权限。 | 从 MinIO 软件包、容器、systemd 或 Helm 迁移。 | 管理员执行一次部署迁移检查，通常不改业务代码。 | [容器迁移](/zh/compatibility/migration/#docker)、[软件包与账号](/zh/compatibility/binary/#layout)、[客户端配置](/zh/compatibility/mcli/#naming) |
| <span id="o02"></span>**O02 · 自定义权限策略**<br>改密、永久删除版本及部分桶操作采用修正后的授权规则。 | 自定义 Allow/Deny、对象 ARN 授权桶操作，或使用来源 IP 条件。 | 谁能做什么可能变化；验证有效权限和代理信任配置。 | [密码权限](/zh/compatibility/password-permissions/#migration)、[版本删除](/zh/compatibility/migration/#since-20260806)、[桶授权](/zh/blog/security/object-grant-bucket-reach/)、[代理信任](/zh/compatibility/server/#trusted-proxies) |
| <span id="o03"></span>**O03 · 旧认证及通知配置**<br>旧式认证、数据库通知及部分 TLS、环境文件用法需调整或验证。 | OIDC HMAC token、旧数据库分散参数、老代理/TLS 或特殊环境文件写法。 | 可能影响登录、通知或启动；按对应配置迁移。 | [OIDC 算法](/zh/compatibility/server/#auth-iam)、[通知连接串](/zh/blog/design/notify-url/#operator-remediation)、[TLS](/zh/blog/design/go127-tls-oidc-discovery/)、[环境文件](/zh/blog/design/config-env-file/#compatibility) |
| <span id="o04"></span>**O04 · 依赖旧错误行为的程序**<br>校验、条件、错误码、退出码和列表上限不再沿用部分旧行为。 | 依赖错误请求成功、忽略 `If-Match`，或假设分片上传列表一次超过 1,000 条。 | 检查错误处理、重试、分页与批处理的最终退出码。 | [校验错误](/zh/blog/design/complete-multipart-checksum-errors/#impact)、[条件删除](/zh/blog/design/conditional-delete/)、[分片列表](/zh/blog/design/list-multipart-uploads/#implementation)、[CLI 退出码](/zh/compatibility/mcli/#current-release) |
| <span id="o05"></span>**O05 · 自制客户端与管理工具**<br>私有接口、签名覆盖、Console 自动化及 Go 包路径存在变化。 | 使用 `ReadMultiple`、手写签名、严格响应解析、Go 嵌入或定制 Console。 | 定制集成和编译需单独验证；普通 S3 SDK 不使用私有存储接口。 | [私有接口](/zh/compatibility/server/#storage-rest)、[签名](/zh/blog/design/signed-header-coverage/#impact)、[Console API](/zh/compatibility/console/#api-output)、[Go 模块](/zh/compatibility/server/#source-compatibility) |
| <span id="o06"></span>**O06 · 多池条件操作与新分片模式**<br>多池写删更严格地核实元数据，strict 分片列表另有升级准备要求。 | 多池条件写、指定版本删除，或显式启用 strict 分片列表。 | 故障时可能返回 503，即使 GET 仍成功；strict 需升级全部 writer 并排空旧上传，默认仍为 legacy。 | [多池条件](/zh/blog/design/multi-pool-object-consistency/#conditions)、[strict 契约](/zh/blog/design/list-multipart-uploads/#implementation) |
| <span id="o07"></span>**O07 · 跨站复制、混跑和回滚**<br>IAM 撤销与桶配置删除状态要求协调升级和恢复。 | 多站点、共享 IAM、不同版本混跑或降级恢复。 | 保留完整恢复点并联测各端；不能假定只换回旧程序即可回滚。 | [IAM 升级](/zh/operations/replication/iam-upgrade/)、[配置收敛](/zh/blog/design/bucket-metadata-convergence/#rollout)、[回滚边界](/zh/compatibility/migration/#rollback) |
| <span id="o08"></span>**O08 · 自更新及上游在线服务**<br>原地自更新、SUBNET 与上游托管支持集成被停用。 | 使用 `admin update`、`mcli update` 或 MinIO 在线支持流程。 | 改用软件包、镜像或编排器升级；常规 S3 访问不受此项影响。 | [服务端更新](/zh/compatibility/server/#offline-services)、[客户端更新](/zh/compatibility/mcli/#self-update)、[SUBNET](/zh/compatibility/mcli/#subnet) |
{.silo-compatibility-table}

## 比较范围与版本边界 {#scope}

服务端对照的是分叉时的上游源码 [`27742d469462`](https://github.com/minio/minio/commit/27742d469462e1561c776f88ca7a1f26816d69e2)（**2025-12-03**）；常见的上游最后发行版标签日期是 **2025-10-15**，两者不是同一个比较点。Console、mcli 的各自基线见[控制台说明](/zh/compatibility/console/)与[客户端说明](/zh/compatibility/mcli/)。本页覆盖 API、功能、可见行为与运维变化，同一修复可涉及多个场景。

SILO 对上游 MinIO/MC 保持**尽最大努力兼容**；正式支持和发布验收的组合为 **SILO + SILO Console + mcli + silo-pkg**。保留协议、环境变量和磁盘布局，不构成任意上游版本混跑或双向降级的承诺。[服务端详细审计](/zh/compatibility/server/)保留历史基线和逐项说明，[组件版本矩阵](/zh/compatibility/versions/)区分已发布组件与待发布源码。

曾加入后撤回的[访问频率池间分层](/zh/compatibility/access-tiering-removal/)不属于上述 24 类：它不在分叉时的上游功能中，也从未进入公开 Server 20260903。普通生命周期过期、远程分层、再平衡和池退役仍然保留。

准备迁移时，从 [O01–O08](#conditional) 筛选与你有关的条件，再按[迁移指南](/zh/compatibility/migration/)执行。
