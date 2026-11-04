---
title: "管理对象"
url: "/zh/administration/console/managing-objects/"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/administration/console/managing-objects.rst
upstream_modified: true
---

> **Console 2.5.1 更新：** 新增 Tasks 抽屉用于跟踪分批传输与批量操作进度（取消任务会停止后续批次，但不会回滚已完成的修改）；文本/Markdown/CSV 预览超过 `1 MiB` 时会显示截断提示；ZIP 归档预览在输出首字节前失败时会保留原始 S3 错误状态；对象列表的排序、筛选与全选作用于当前已加载的分页。详见 [Console 2.5.1 对象工作区更新](/zh/blog/release/console-2.5.1/#objects)。

<a id="minio-console-managing-objects"></a>
<a id="id1" data-td-print-local></a>

你可以使用 MinIO Console 执行 MinIO 提供的多种存储桶和对象管理及交互操作。 根据已认证用户的权限和 IAM 策略，你可以：

- [浏览、上传、回退、管理并与对象交互](#minio-console-object-browser)。
- [浏览、创建和管理存储桶](#minio-console-buckets)。
- [创建或监控远程层](#minio-console-tiers)，以支持对象转换规则。

<a id="id3" data-td-print-local></a>

## 对象浏览器 {#minio-console-object-browser}

在 [Server 20261026](/zh/blog/release/silo-20261026/#server-20261026)中，Console 的 `account-info` 请求改为读取实时存储桶清单，创建或删除存储桶后刷新即可获取最新列表（存储桶容量统计仍由后台扫描器更新）。此前的 Server 20261018 返回缓存的存储桶列表。

对象浏览器会列出已认证用户在该部署上有权访问的存储桶和对象。

登录后或切换到该标签页时，对象浏览器会显示该用户的存储桶列表，用户可以对其进行筛选。 选择某个存储桶可显示该桶中的对象列表。

选择某个具体对象后，可显示该对象的摘要信息，例如名称、大小、标签、法律保留以及适用的保留策略。 Console 还会显示该对象的元数据。

用户可根据适用的策略和权限，对存储桶中的对象执行操作。 用户可能可以执行的操作包括：

- 回退到先前版本
- 创建前缀
- 查看已删除对象
- 上传对象
- 下载对象
- 分享
- 预览
- 管理法律保留
- 管理保留策略
- 管理标签
- 检查
- 显示版本
- [删除](/zh/administration/object-management/object-delete/#minio-object-delete)

> [!NOTE]
> **新增: Console**
>
> v0.24.0
>
> 可通过 Console 右上角的对象管理器按钮查看对象上传或下载状态。 如果你在当前会话期间未上传或下载任何对象，则不会显示该按钮。

> [!NOTE]
> **变更: Console**
>
> v0.35.0
>
> 如果你选择下载多个对象，MinIO 会将这些对象打包为一个 ZIP 归档供下载。 下载后你必须解压该归档，才能访问其中的文件。

### 多对象下载与分享 {#silo-downloads}

[Console v2.4.1](/zh/blog/release/console-2.4.1/) 多选 ZIP 下载使用文件写入器流式保存；
不支持该接口的浏览器由原生下载管理器接管，两者都不在 JavaScript 中缓冲完整归档。
Console 会明确提示原生下载交接，此后请在浏览器下载管理器中查看进度、取消或处理网络错误。
递归 ZIP 通常没有可靠总大小，未知大小不显示完成百分比；超过 5 GiB 或大小未知的选择推荐使用 mcli。

对象目录按页加载，排序、筛选与全选仅作用于当前页。重复 ZIP 任务会被阻止，
原生下载交接后关闭 Console 任务条目不会取消浏览器下载。公开对象、预签名链接与指定版本分享
继续可用，匿名代理只接受配置 S3 源站上的对象内容 GET，拒绝重定向和系统端点。
详见[分享边界](/zh/reference/minio-server/settings/console/#object-sharing)。

<a id="minio-console-buckets"></a>
<a id="id4" data-td-print-local></a>

## 存储桶 {#minio-console-admin-buckets}

Console 的 **Bucket** 部分会显示已认证用户具有 [访问权限](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 的所有存储桶。 你可以根据该用户的访问权限，在此部分中创建或管理这些存储桶。

### 创建存储桶 {#id5}

选择 **Create Bucket** 可在该部署上创建新的存储桶。 MinIO 会校验存储桶名称。 如需查看存储桶命名规则，请选择 **View Bucket Naming Rules**。

MinIO 不限制单个部署允许创建的存储桶总数。 不过，作为通用建议，MinIO 建议每个部署的存储桶数量不超过 500,000 个。

创建存储桶时，你可以启用以下功能：[版本控制](/zh/administration/object-management/object-versioning/#minio-bucket-versioning), [对象锁定](/zh/administration/object-management/object-retention/#minio-object-locking), 存储桶大小（配额）限制，以及 [保留规则](/zh/administration/object-management/object-retention/#minio-object-locking-retention-modes)。 保留规则要求启用版本控制。

> [!NOTE]
> **变更: Console**
>
> v0.35.0
>
> 如果启用版本控制，你可以指定要排除在版本控制之外的前缀。

你 **必须** 在创建存储桶时配置复制、锁定和版本控制选项。 之后无法再更改该存储桶的这些设置。

### 管理存储桶 {#id6}

使用 **Search** 栏筛选特定存储桶。 选择某个存储桶所在行可显示该存储桶的摘要信息。

在摘要页面中，选择任一可用标签页以进一步管理该存储桶。

> [!NOTE]
> **说明**
>
> 如果已认证用户没有 [所需的管理权限](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy-mc-admin-actions)，某些管理功能可能不可用。

管理存储桶时，你的访问设置可能允许你查看或更改以下内容：

- **Summary** 部分显示存储桶配置的摘要。

  你可以在此部分查看和修改存储桶的访问策略、加密、配额和标签。
- 在 **Events** 部分配置告警，以便在用户上传、访问或删除匹配对象时触发 [通知事件](/zh/administration/monitoring/bucket-notifications/#minio-bucket-notifications)。
- 在 **Replication** 部分使用 [服务端存储桶复制规则](/zh/administration/bucket-replication/#minio-bucket-replication-serverside) 将对象复制到远程位置。
- 在 **Lifecycle** 部分设置 [对象生命周期管理规则](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management)，以过期或转换存储桶中的对象。
- 在 **Access** 部分通过列出对该存储桶有访问权限的 [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 和 [用户](/zh/administration/identity-access-management/minio-user-management/#minio-users) 来审查安全设置。
- 在 **Anonymous** 部分管理未认证用户可用于读取或写入对象的前缀规则，以妥善保护匿名访问。

<a id="id7" data-td-print-local></a>

## 层 {#minio-console-tiers}

**Tiering** 部分提供了用于添加和管理 [远程层](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-tiering) 的界面，以支持生命周期管理转换规则。 MinIO 分层支持将对象从该部署迁移到远程存储，但不支持自动将其恢复到该部署。

分层标签页允许具有相应权限的用户执行以下操作：

- 查看所有已配置远程层的状态和摘要信息。
- 为新的远程目标存储创建层，目标可以是另一个 MinIO 部署、Google Cloud Storage、Amazon 的 AWS S3 或 Azure。
- 使用层上的 <svg version="1.1" width="1.0em" height="1.0em" class="sd-octicon sd-octicon-pencil" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M11.013 1.427a1.75 1.75 0 012.474 0l1.086 1.086a1.75 1.75 0 010 2.474l-8.61 8.61c-.21.21-.47.364-.756.445l-3.251.93a.75.75 0 01-.927-.928l.929-3.25a1.75 1.75 0 01.445-.758l8.61-8.61zm1.414 1.06a.25.25 0 00-.354 0L10.811 3.75l1.439 1.44 1.263-1.263a.25.25 0 000-.354l-1.086-1.086zM11.189 6.25L9.75 4.81l-6.286 6.287a.25.25 0 00-.064.108l-.558 1.953 1.953-.558a.249.249 0 00.108-.064l6.286-6.286z"></path></svg> 图标轮换任意已配置层的访问凭证。

## 用量扫描（开发中） {#usage-scans}

> **尚未发布：** 本节介绍正在从 [PR #70](https://github.com/pgsty/silo-console/pull/70)
> 整合的 Console 功能，不包含在已发布的 Console 2.5.1 或 Server 20261026 中。
> Console 发布与 SILO Server 更新内嵌 Console 依赖是两个独立的交付步骤。
> 正式支持的集成目标是 `pgsty/silo`；与上游 MinIO 的兼容性属于尽最大努力支持。

<!-- 改编自 pgsty/silo-console PR #70 的 docs/FolderSizes.md。
Copyright (c) 2026 Urbanize. SPDX-License-Identifier: AGPL-3.0-or-later. -->

### 文件夹大小

对象浏览器将 S3 前缀显示为文件夹，但 S3 本身并不记录前缀大小。
**计算文件夹大小**会递归扫描当前目录的对象元数据，将当前对象的大小填入直接下级文件夹的列表行，
不会下载对象内容。打开文件夹不会自动扫描；文件夹的 **刷新** 按钮才会启动扫描。
也可以从某个文件夹的操作菜单选择 **计算大小**，缩小扫描范围。

启用 **包含保留版本** 后，还会列出历史对象版本与删除标记。
大小列始终显示当前对象字节数，保留版本字节数单独显示。
最新版本为删除标记时，该键不贡献当前字节数，但历史版本仍计入保留字节数；
零字节目录标记也计入对象数量。逻辑对象字节数不等于物理磁盘占用，
不包含压缩、纠删码、文件系统快照或副本带来的空间差异。

扫描面板显示进度、条目数与计算时间。**取消** 会停止请求及 S3 分页。
结果仅属于当前视图和会话，导航后清除；对象发生变化后需要重新计算。
扫描读取的是实时列表，不是原子快照，扫描过程中对象可能变化。

只有 **已完成** 才表示列表读取完毕。运行中、已取消、达到限制或失败的结果带有 ≥ / 部分结果标记，
不能作为完整容量统计。权限不足、连接中断或响应不完整不会变成“文件夹大小为零”。
达到限制时应扫描更小的前缀。大小排序对已扫描文件夹使用计算值，对普通对象使用元数据；
排序范围仍是当前已加载的列表行。

### 权限与限制

扫描需要已登录的 Console 会话，并具备目标前缀的 `s3:ListBucket` 权限；
版本扫描还需要 `s3:ListBucketVersions`。
API 始终使用当前会话的 S3 凭据，包括 STS 会话令牌，不借用服务器管理员凭据、
不修改对象，也不允许匿名扫描。

每个 Console 进程可配置以下环境变量：

| 变量 | 默认值 | 允许范围 |
| --- | --- | --- |
| `CONSOLE_PREFIX_USAGE_TIMEOUT` | `10m` | `1s`–`1h` |
| `CONSOLE_PREFIX_USAGE_MAX_ENTRIES` | `10000000` | 1–1000000000000 |
| `CONSOLE_PREFIX_USAGE_MAX_FOLDERS` | `1000` | 1–10000 |
| `CONSOLE_PREFIX_USAGE_MAX_CONCURRENT` | `2` | 1–64 |
| `CONSOLE_PREFIX_USAGE_PROGRESS_INTERVAL` | `1s` | `100ms`–`30s` |

并发限制按进程计算；进程繁忙时返回 HTTP 429。每个浏览器视图只允许一个活动扫描。
达到时间、条目数或下级文件夹数量限制时，会返回表示部分结果的终止帧，并取消后续列表请求。
配置无效时拒绝扫描，不会移除限制后继续运行。

### API

`GET /api/v1/buckets/{bucket}/prefix-usage?prefix=&versions=false&folders=true`
使用普通的已认证 Console API。桶根目录使用 `prefix=`，其他前缀必须以 `/` 结尾；
`folders=false` 表示只统计这个前缀本身。

响应类型为 `application/x-ndjson`，每行是 `swagger.yml` 中定义的 `prefixUsageFrame`，
包含桶/前缀/模式标识、开始与更新时间、已扫描条目数、汇总用量和下级文件夹用量。
字节数使用十进制字符串，避免 JavaScript 对超过 2^53 的总量进行舍入。
终止状态为 `complete`、`limited` 或 `failed`；缺少或无法验证终止数据时，结果不完整。
初始列表请求失败会在开始流式响应前保留权限或资源不存在的 HTTP 状态。
客户端停止读取时应取消请求。

开发验证可运行 `go test ./api -run TestPrefixUsage`、前端 `yarn typecheck` 和
`yarn exec playwright test --project=unit e2e/prefix-usage.unit.ts`。
`e2e/prefix-usage.spec.ts` 连接真实 SILO 和 Console，创建专属测试桶，验证分页、版本计数和文件夹界面，
最后移除所有测试版本与删除标记。使用 `CONSOLE_TEST_ENDPOINT`、`CONSOLE_TEST_ACCESS_KEY`、
`CONSOLE_TEST_SECRET_KEY`，并通过 `SILO_TEST_ENDPOINT` 指定 S3 端点。不要对业务桶运行这些夹具测试。

### 存储桶刷新与自动更新

在 **存储桶** 页面点击 **刷新**，会为当前清单中的每个桶请求新一次元数据扫描，
也包括被搜索条件暂时隐藏的桶。表格和卡片显示当前大小、保留版本字节数、每个桶的完成时间、
排队/运行状态和扫描进度。新扫描期间保留上次完成的统计值；任务入队不代表扫描完成。
未知总量保持未知，部分进度不会替换已完成的总量，排序使用精确整数。

在桶内点击 **刷新**，会刷新对象列表并计算当前目录的直接下级文件夹大小。
文件夹菜单中的 **计算大小** 可缩小范围。这些前台扫描可以取消，导航后结束；
仅浏览目录不会自动启动后台文件夹扫描。

#### 可选的持久化 worker

如需持久化刷新任务和自动更新，为 Console 配置 `CONSOLE_USAGE_DATABASE_URL`，
并使用**同一个构建版本**运行 `console usage-worker`。只有这个可选模式需要 PostgreSQL。
worker 负责数据库模式迁移，需要其专用数据库 `public` schema 中的 CREATE 权限；
Web 进程不会在处理浏览器请求时执行迁移。使用经过验证的 TLS 数据库连接和有上限的连接池，
不要把 worker 的 S3 凭据交给 Web 进程。

两个进程应使用相同的 `CONSOLE_MINIO_SERVER` 端点和数据库。
仅在 worker 上设置 `CONSOLE_USAGE_S3_ACCESS_KEY`、`CONSOLE_USAGE_S3_SECRET_KEY`，
需要时再设置 `CONSOLE_USAGE_S3_SESSION_TOKEN`。专用身份的 S3 策略如下：

```json
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Action":["s3:ListAllMyBuckets","s3:ListenNotification"],"Resource":["*"]},{"Effect":"Allow","Action":["s3:GetBucketLocation","s3:ListBucket","s3:ListBucketVersions","s3:ListenBucketNotification"],"Resource":["arn:aws:s3:::*"]}]}
```

worker 不需要读取对象内容、写入对象或执行管理操作的权限。
Console API 在返回或刷新已保存的汇总前，会独立验证当前调用者对桶根目录的列表权限。
版本列表请求被拒绝时，不返回保留字节数、保留版本数、删除标记数或版本扫描进度。
SILO 当前允许将 ListBucket 作为 ListBucketVersions 的兼容性回退，API 以存储服务器实际授予的权限为准。
只有部分前缀权限的调用者无法获取整个桶的汇总；每次状态请求都会重新验证权限撤销。
API 响应使用 `Cache-Control: no-store`。

worker 订阅经过认证的存储变更通知。创建、覆盖、完成分段上传和删除操作会使相关桶的统计失效。
重复或乱序事件合并为一个待扫描任务，不直接加减可能重复的字节差值；扫描期间发生变更则安排下一代任务。
任务持久化在 PostgreSQL 中，显式刷新优先处理，通过带过期时间和归属校验的租约领取。
worker 在受限时间片之间让出执行权，只在完整对象键及其所有版本处理完毕后保存恢复位置，
因此同一个键跨越多个版本分页时不会漏计。

实时通知订阅**不保证持久化重放**。启动或重新连接后，会将已有统计标为需要校准。
较频繁的桶清单检查仅发现新桶，不重扫未变化的桶；独立的完整校准负责补偿事件流缺口和未通知的变化。
连接与校准恢复前，界面会显示自动更新状态降级。已完成的扫描仍是实时列表，不是原子文件系统快照。

没有配置数据库时，刷新使用有边界的前台元数据扫描，界面明确提示自动更新未配置。
导航后停止扫描，这种模式下的已完成统计不在不同 Console 副本间共享。

#### worker 与 API 配置

以下名称均以 `CONSOLE_USAGE_` 为前缀。时长采用 Go duration 语法。
缺少必需配置、配置无效或互不兼容时，拒绝启用相应功能。

| 后缀 | 默认值 | 用途 |
| --- | --- | --- |
| `DATABASE_URL` | 未设置 | PostgreSQL URI；使 Web 进程启用持久化模式 |
| `S3_ACCESS_KEY`、`S3_SECRET_KEY`、`S3_SESSION_TOKEN` | 未设置 | worker 专用身份；令牌可选 |
| `HTTP_ADDRESS` | `:9091` | worker 内部健康与指标监听地址 |
| `POOL_MAX_CONNECTIONS` | 4 | 每进程最大连接数 |
| `CONCURRENT_SCANS` | 1 | 并发扫描时间片数量 |
| `MAX_ENTRIES` | 100000000 | 每次完整桶扫描最多处理的条目数 |
| `SCAN_TIMEOUT` | `30m` | 跨时间片的完整扫描总耗时上限 |
| `SCAN_SLICE` | `5s` | 公平调度时间片，在完整键边界让出执行权 |
| `LEASE` | `2m` | 扫描与事件观察者的租约期限 |
| `HEARTBEAT` | `15s` | 租约/覆盖状态心跳间隔与单次操作时间预算 |
| `PROGRESS_INTERVAL` | `1s` | 进度持久化间隔 |
| `POLL_INTERVAL` | `1s` | 任务队列轮询与事件写入间隔 |
| `EVENT_DEBOUNCE` | `5s` | 合并突发变更事件的等待时间 |
| `MIN_SCAN_INTERVAL` | `1m` | 自动重扫的最小间隔，手动刷新不受此限制 |
| `RECONCILE_INTERVAL` | `15m` | 轻量的新桶清单检查间隔 |
| `FULL_RECONCILE_INTERVAL` | `24h` | 独立于即时事件/刷新任务的完整校准间隔 |
| `RETRY_INTERVAL`、`MAX_RETRY_INTERVAL` | `30s`、`15m` | 指数退避的初始与最大重试间隔 |
| `AUTH_CONCURRENCY` | 4 | 每个 API 请求的并发调用者权限探测数 |
| `API_MAX_REQUESTS` | 8 | 每个 Console 进程的并发用量 API 请求数 |
| `REQUEST_TIMEOUT` | `15s` | 用量 API 截止时间 |
| `UI_POLL_INTERVAL` | `2s` | 有待处理任务时的轮询间隔；空闲视图使用十倍间隔，最多一分钟 |

条目数、扫描时长、并发数和请求预算均有明确上限，详见 `pkg/usage/config.go`。
达到扫描限制时保留上次成功结果，并暴露 `limited` 状态。自动重试、变更事件和校准不会重新启动受限扫描，
因为重新扫描只会再次触达同一限制。调高预算后，或任何时候需要重试时，请点击 **刷新**：
显式刷新会丢弃受限扫描的检查点，以新的时间和条目预算重新开始扫描。也可以改为扫描更小的前缀。
错误、故障和扫描限制都不会被当作零用量。

`POST /api/v1/bucket-usage/status` 返回已保存的统计与观察覆盖状态；
`POST /api/v1/bucket-usage/refresh` 将优先任务入队并返回 HTTP 202。
两者都接受 `{"buckets":["example-bucket"]}`，每次最多 1000 个桶名，前端会对更大的清单分批请求。
它们使用当前 Console 会话而非 worker 身份认证，精确字节数保持为十进制字符串。

worker 内部接口包括进程存活检查 `/health`、租约观察者及连接校准就绪检查 `/ready`，
以及暴露覆盖状态、队列计数、失败/限制状态和最旧待处理时间的 `/metrics`。
这些端口应仅供内部访问；进程存活并不意味着变更观察者已经健康就绪。

真实 PostgreSQL 测试使用 `go test -tags=integration ./pkg/usage`；
原生 SILO 和权限验证使用
`go test -tags=integration,storageintegration ./pkg/usage ./api -run TestNative`。
将 `TEST_USAGE_DATABASE_URL`、`TEST_USAGE_S3_ENDPOINT`、`TEST_USAGE_S3_ACCESS_KEY`、
`TEST_USAGE_S3_SECRET_KEY` 指向一次性测试环境；显式运行这些测试时缺少配置会失败。
测试会创建并清理自己的桶和 IAM 身份，不要针对业务数据运行。
前端 `e2e/bucket-usage-refresh.unit.ts` 在浏览器中加载真实 hook 和组件，
覆盖排队、进度、完成、错误、导航和精度等行为。

设计参考了 [S3 事件通知说明](https://docs.aws.amazon.com/AmazonS3/latest/userguide/EventNotifications.html)
和[事件乱序、重复处理建议](https://aws.amazon.com/blogs/storage/manage-event-ordering-and-duplicate-events-with-amazon-s3-event-notifications/)：
通知触发幂等任务，校准补偿投递缺口。

### 创建失败与配额精度（开发中） {#creation-and-quota}

尚未发布的创建处理链会在创建桶之前拒绝无效的配额与保留期。
仅指定保留期也会启用对象锁定和版本控制，`versioning` 对象可以省略。
对象锁定不能将前缀或文件夹排除在版本控制之外，因此同时指定锁定或保留期与版本控制排除项的请求，
会在创建任何桶之前被拒绝。
若创建后应用某项配置失败，API 会返回错误并尝试删除空桶；回滚不会删除对象。
若调用者没有删除权限，或桶已不再为空，错误信息会明确提示桶可能仍然存在。
重试前应检查实际配置；收到 HTTP 错误并不证明桶没有被创建。

Console 写入的配额必须大于零且小于 8 PiB（最多 9007199254740991 字节），
选定单位下最多支持两位小数。换算使用整数运算，仅舍去不足一个字节的部分。
更大的配额仍可通过 mcli 和现有整数 API 管理。
浏览器遇到超出 JSON 安全整数范围的已有配额时，不会填入可编辑的近似值，
因此不会因打开后直接保存而悄悄改写配额。仍可清除该配额，或显式输入一个更小的新值。
仅用于展示的容量统计可能经过舍入，需要精确的大整数值时请使用 mcli。
