---
title: "站点复制概览"
url: "/zh/operations/replication/multi-site-replication/"
weight: 20
icon: fa-solid fa-arrows-rotate
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/replication/multi-site-replication.rst
upstream_modified: true
---

> [!IMPORTANT]
> **SILO 20261109 站点复制更新与升级要求**
>
> - **IAM 与 Server 协调升级：** [SILO 20261109](/zh/blog/release/silo-20261109/) 拒绝不完整的 IAM 策略加载，在惰性加载期间保持缓存认证可用，并直接基于持久化记录执行 IAM 编辑、LDAP 组刷新与服务账户创建，使陈旧对等节点无法恢复旧凭据或复活已删除身份（[#316](https://github.com/pgsty/silo/issues/316)、[#317](https://github.com/pgsty/silo/issues/317)、[#321](https://github.com/pgsty/silo/issues/321)–[#323](https://github.com/pgsty/silo/issues/323)）。升级前请阅读 [IAM 升级与恢复](/zh/operations/replication/iam-upgrade/)、[历史复制状态检查](/zh/operations/replication/replica-metadata-audit/)及[组件版本表](/zh/compatibility/versions/)。
> - **Object Lock、生命周期删除与指标：** 复制删除保留目标端 legal hold 与保留期（提交 [`7e9ee6bef`](https://github.com/pgsty/silo/commit/7e9ee6bef)），生命周期规则创建的删除标记与版本清除不跨站点复制（提交 [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)），且复制工作线程指标在复制线程池缺失时不再触发 panic 并保留历史均值与峰值计数（提交 [`099b7ddf3`](https://github.com/pgsty/silo/commit/099b7ddf3)）。
> - **已知限制：** 多站点删除标记清除顺序（[#217](https://github.com/pgsty/silo/issues/217)）与重放创建存储桶（[#241](https://github.com/pgsty/silo/pull/241)）仍为已知未解决限制。

<a id="site-replication-overview"></a>
<a id="minio-site-replication-overview"></a>

站点复制将多个相互独立的 MinIO 部署配置为一个由副本组成的集群，这些副本称为对等站点。

<figure>
  <img src="/images/architecture/architecture-load-balancer-multi-site.svg" alt="Diagram of a site replication deployment with two sites" />
  <figcaption>一个包含两个对等站点的站点复制部署。
负载均衡器负责将操作路由到两个站点中的任意一个。
写入一个站点的数据会自动复制到另一个对等站点。</figcaption>
</figure>

站点复制要求使用内置的 MinIO Identity Provider (IDP) *或* 外部 IDP。 所有已配置的部署都必须使用同一个 IDP。 使用外部 IDP 的部署必须在各站点之间使用相同的配置。

有关站点复制架构和部署概念的更多信息，请参阅 [Deployment Architecture: Replicated MinIO Deployments](/zh/operations/concepts/architecture/#minio-deployment-architecture-replicated)。

除早期开发、评估或一般性实验外，MinIO 不建议在站点复制中使用 macOS、Windows 或未编排的容器部署。生产环境请使用受支持的 [Linux](/zh/operations/deployments/baremetal/) 或 [Kubernetes](/zh/operations/deployments/kubernetes/) 部署，并按照本页的站点复制流程操作。

## 概览 {#overview}

<a id="minio-site-replication-what-replicates"></a>

### 所有站点之间会复制哪些内容 {#what-replicates-across-all-sites}

每个 MinIO 部署（“对等站点”）都会将以下变更同步到其他对等站点：

- 存储桶和对象的创建、修改与删除，包括

  - 存储桶与对象配置
  - [策略](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy)
  - [`mc tag set`](/zh/reference/minio-mc/mc-tag-set/#command-mc.tag.set)
  - [锁定](/zh/administration/object-management/object-retention/#minio-object-locking)，包括保留和 legal hold 配置
  - [加密设置](/zh/administration/server-side-encryption/#minio-encryption-overview)
- IAM 用户、组、策略以及策略到用户或组的映射（针对 LDAP 用户或组）的创建与删除
- 为可由本地 `root` 凭证验证的会话令牌创建 Security Token Service (STS) 凭证
- [访问密钥](/zh/reference/minio-mc-admin/mc-admin-user-svcacct/#minio-mc-admin-user-svcacct) 的创建与删除 （不包括 `root` 用户拥有的访问密钥）

站点复制会在所有复制站点上，为所有新建和现有存储桶启用 [存储桶版本控制](/zh/administration/object-management/object-versioning/#minio-bucket-versioning)。

在 [SILO 20261109](/zh/blog/release/silo-20261109/) 中，复制删除保留目标站点的 Object Lock legal hold 与保留期（提交 [`7e9ee6bef`](https://github.com/pgsty/silo/commit/7e9ee6bef)）：源站点绕过 `GOVERNANCE` 保留期发起的物理清除不会赋予仍处于有效保护下的对等副本绕过权限，目标站点会拒绝清除并由源站点重试。

> [!NOTE]
> **生命周期过期删除不跨站点复制（`SILO 20261109`）**
>
> 自 [SILO 20261109](/zh/blog/release/silo-20261109/) 起，即使配置中曾设置旧版 ILM 过期复制标志（[`--replicate-ilm-expiry`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add.-replicate-ilm-expiry) 或 [`--enable-ilm-expiry-replication`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update.-enable-ilm-expiry-replication)），生命周期规则创建的删除标记与版本清除也**不会**跨站点复制（提交 [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)），行为与 AWS S3 一致。请在每个对等站点独立配置生命周期过期规则。

### 哪些内容不会在站点之间复制 {#what-does-not-replicate-across-sites}

处于站点复制配置中的 MinIO 部署 *不会* 复制以下项目的创建或修改：

- [存储桶通知](/zh/administration/monitoring/bucket-notifications/#minio-bucket-notifications)
- [生命周期管理（ILM）配置](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management)及生命周期生成的删除标记或版本清除（提交 [`1bd0b1b04`](https://github.com/pgsty/silo/commit/1bd0b1b04)）
- [站点配置设置](/zh/reference/minio-mc-admin/mc-admin-config/#minio-mc-admin-config)

### 站点复制的初始流程 {#initial-site-replication-process}

启用站点复制后，身份与访问管理（IAM）设置会按以下顺序同步：

{{< tabs group="minio-idp-oidc-ldap" >}}
{{< tab label="MinIO IDP" value="minio-idp" >}}
1. 策略
2. 用户账户（针对本地用户）
3. 组
4. Access Keys

   `root` 的 Access Keys 不会同步。
5. 已同步用户账户的策略映射
6. [Security Token Service (STS) users](/zh/developers/security-token-service/#minio-security-token-service) 的策略映射
{{< /tab >}}
{{< tab label="OIDC" value="oidc" >}}
1. 策略
2. 与具有有效 [MinIO Policy](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 的 OIDC 账户关联的 Access Keys。`root` 的 Access Keys 不会同步。
3. 已同步用户账户的策略映射
4. [Security Token Service (STS) users](/zh/developers/security-token-service/#minio-security-token-service) 的策略映射
{{< /tab >}}
{{< tab label="LDAP" value="ldap" >}}
1. 策略
2. 组
3. 与具有有效 [MinIO Policy](/zh/administration/identity-access-management/policy-based-access-control/#minio-policy) 的 LDAP 账户关联的 Access Keys。`root` 的 Access Keys 不会同步。
4. 已同步用户账户的策略映射
5. [Security Token Service (STS) users](/zh/developers/security-token-service/#minio-security-token-service) 的策略映射
{{< /tab >}}
{{< /tabs >}}

在对等站点之间完成初始数据同步后，MinIO 会持续在所有站点之间复制并同步任何站点上新发生的 [可复制数据](#minio-site-replication-what-replicates)。

### 站点自愈 {#site-healing}

站点复制配置中的任意 MinIO 部署，都可以从拥有该数据最新版本的对等站点重新同步受损的 [可复制数据](#minio-site-replication-what-replicates)。

> [!NOTE]
> **重试、重新入队与手动重同步行为**
>
> - **重试上限（`RELEASE.2023-07-18T17-49-40Z`）：** 站点复制操作在移出队列前最多重试三（3）次；[scanner](/zh/operations/concepts/scanner/#minio-concepts-scanner) 会在稍后重新扫描受影响对象并将其重新加入复制队列。
> - **读取触发重新入队（`RELEASE.2022-08-11T04-37-28Z`）：** 执行任意 `GET` 或 `HEAD` API 请求时，失败或待处理的复制会自动重新入队（例如站点恢复在线后执行 [`mc stat`](/zh/reference/minio-mc/mc-stat/#command-mc.stat)、[`mc cat`](/zh/reference/minio-mc/mc-cat/#command-mc.cat) 或 [`mc ls`](/zh/reference/minio-mc/mc-ls/#command-mc.ls)）。
> - **主动重同步（`RELEASE.2022-12-02T23-48-47Z`）：** 若某个站点丢失数据，可执行 [`mc admin replicate resync`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.resync) 立即从健康对等站点重新同步数据，而无需等待被动的 [MinIO scanner](/zh/operations/concepts/scanner/#minio-concepts-scanner)。

你可以使用 [`MINIO_SCANNER_SPEED`](/zh/reference/minio-server/settings/core/#envvar.MINIO_SCANNER_SPEED) 环境变量或 [`scanner speed`](/zh/reference/minio-server/settings/core/#mc-conf.scanner.speed) 配置项， 调整 MinIO 在扫描器性能与读写操作之间的平衡方式。

### 同步复制与异步复制 {#synchronous-vs-asynchronous-replication}

对于给定的远端目标，MinIO 支持指定异步复制（默认）或同步复制。

在异步复制模式下，MinIO 会在将对象放入 [复制队列](/zh/administration/bucket-replication/#minio-replication-process) *之前* 完成发起的 `PUT` 操作。 因此，发起请求的客户端可能会在对象完成复制 *之前* 就看到 `PUT` 操作成功。 虽然这可能导致远端对象陈旧或缺失，但它降低了因复制负载而导致写入变慢的风险。

在同步复制模式下，MinIO 会在完成发起的 `PUT` 操作 *之前* 尝试复制对象。 无论复制尝试是否成功，MinIO 都会返回一个成功的 `PUT` 操作结果。 这降低了写入变慢的风险，但代价是远端位置可能出现陈旧或缺失对象。

MinIO 强烈建议使用默认的异步站点复制。 同步站点复制的性能高度依赖站点之间的延迟，较高的延迟可能导致更低的 PUT 性能和复制滞后。 要配置同步站点复制，请使用 [`mc admin replicate update`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) 并带上 [`--mode`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update.-mode) 选项。

### 代理到其他站点 {#proxy-to-other-sites}

MinIO 对等站点可以将对象的 `GET/HEAD` 请求代理到其他对等站点，以检查该对象是否存在。 这样一来，即使某个站点正在自愈或落后于其他对等站点，仍然可以返回已持久化到其他站点的对象。

例如：

1. 客户端向 `Site1` 发起 `GET("data/invoices/january.xls")`
2. `Site1` 无法定位该对象
3. `Site1` 将请求代理到 `Site2`
4. `Site2` 返回请求对象的最新版本
5. `Site1` 将代理返回的对象响应给客户端

对于 *不* 包含唯一版本 ID 的 `GET/HEAD` 请求，代理请求会返回该对象在对等站点上的 *最新* 版本。 这可能导致取回对象的非当前版本，例如响应请求的对等站点本身也存在复制滞后时。

MinIO 不会代理 `LIST`、`DELETE` 和 `PUT` 操作。

## 前提条件 {#prerequisites}

### 先备份集群设置 {#back-up-cluster-settings-first}

在配置站点复制之前，使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 和 [`mc admin cluster iam export`](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) 命令分别对存储桶元数据和 IAM 配置进行快照。 如果在配置站点复制过程中发生误配置，可以使用这些快照恢复存储桶/IAM 设置。

### 初始化时仅允许一个站点包含数据 {#one-site-with-data-at-setup}

在初始化时，只允许 *一个* 站点包含数据。 其他站点必须不包含任何存储桶和对象。

配置站点复制后，第一个部署上的所有数据都会复制到其他站点。

### 所有站点必须使用相同的 IDP {#all-sites-must-use-the-same-idp}

所有站点都必须使用相同的 [Identity Provider](/zh/administration/identity-access-management/#minio-authentication-and-identity-management)。 站点复制支持内置的 MinIO IDP、OIDC 或 LDAP。

### 所有站点必须使用相同的 MinIO 服务端版本 {#all-sites-must-use-the-same-minio-server-version}

所有站点都必须使用一致且匹配的 MinIO 服务端版本。 在 MinIO 服务端版本不匹配的站点之间配置复制，可能导致意外或不符合预期的复制行为。

还应确保用于配置复制的 [`mc`](/zh/reference/minio-mc/#command-mc) 版本尽量与服务器版本保持接近。

### 访问同一个加密服务 {#access-to-the-same-encryption-service}

如果通过 Key Management Service (KMS) 使用 [SSE-S3](/zh/administration/server-side-encryption/server-side-encryption-sse-s3/#minio-encryption-sse-s3) 或 [SSE-KMS](/zh/administration/server-side-encryption/server-side-encryption-sse-kms/#minio-encryption-sse-kms) 加密，则所有站点都必须能够访问同一个中心化 KMS 部署。

可以通过一个中心化 KES 服务器，或多个 KES 服务器（例如每个站点一个）连接到同一个受支持的中心化 [key vault server](/zh/administration/server-side-encryption/#minio-sse) 来实现。

### 复制要求启用版本控制 {#replication-requires-versioning}

站点复制 *要求* 启用 [存储桶版本控制](/zh/administration/object-management/object-versioning/#minio-bucket-versioning)，并会自动为所有新建存储桶启用该功能。 在站点复制部署中，不能禁用版本控制。

对于存储桶中被排除在版本控制之外的前缀，MinIO 无法复制其中的对象。

### 每个站点都应部署负载均衡器 {#load-balancers-installed-on-each-site}

指定该站点的负载均衡器、反向代理或类似网络控制平面组件的 URL 或 IP 地址。 请求会自动路由到部署中的各个节点。

MinIO 不建议为对等站点使用单个节点主机名。 这会形成单点故障：如果该节点离线，复制就会失败。

### 从存储桶复制切换到站点复制 {#switch-to-site-replication-from-bucket-replication}

[存储桶复制](/zh/administration/bucket-replication/#minio-bucket-replication) 与多站点复制是互斥的。 不能在同一组部署上同时使用这两种复制方式。

如果此前已经配置了存储桶复制，而现在希望改用站点复制，则在初始化站点复制时，必须先删除包含数据的那个部署上的全部存储桶复制规则。 可在命令行中使用 [`mc replicate rm`](/zh/reference/minio-mc/mc-replicate-rm/#command-mc.replicate.rm) 删除存储桶复制规则。

设置站点复制时，只允许一个站点包含数据。 其他所有站点都必须为空。

## 教程 {#tutorials}

<a id="minio-configure-site-replication"></a>

### 配置站点复制 {#configure-site-replication}

以下步骤将为三个 [分布式部署](/zh/operations/deployments/installation/#deploy-minio-distributed) 创建一个新的站点复制配置。 其中一个站点包含 [可复制数据](#minio-site-replication-what-replicates)。

这三个站点分别使用别名 `minio1`、`minio2` 和 `minio3`，且仅 `minio1` 包含数据。

1. 使用相同的 [IDP](/zh/administration/identity-access-management/#minio-authentication-and-identity-management)，[部署](/zh/operations/deployments/installation/#deploy-minio-distributed) 三个或更多彼此独立的 MinIO 站点

   从空站点开始，*或* 确保最多只有一个站点包含任何 [可复制数据](#minio-site-replication-what-replicates)。
2. 为每个站点配置别名

   指定该站点的负载均衡器、反向代理或类似网络控制平面组件的 URL 或 IP 地址。 请求会自动路由到部署中的各个节点。

   MinIO 不建议为对等站点使用单个节点主机名。 这会形成单点故障：如果该节点离线，复制就会失败。

   例如，对于三个 MinIO 站点，可以创建别名 `minio1`、`minio2` 和 `minio3`。

   使用 [`mc alias set`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set) 定义管理该站点连接的负载均衡器主机名或 IP。

   ```shell
   mc alias set minio1 https://minio1.example.com:9000 adminuser adminpassword
   mc alias set minio2 https://minio2.example.com:9000 adminuser adminpassword
   mc alias set minio3 https://minio3.example.com:9000 adminuser adminpassword
   ```

   或定义环境变量

   ```shell
   export MC_HOST_minio1=https://adminuser:adminpassword@minio1.example.com
   export MC_HOST_minio2=https://adminuser:adminpassword@minio2.example.com
   export MC_HOST_minio3=https://adminuser:adminpassword@minio3.example.com
   ```

3. 添加站点复制配置

   ```shell
   mc admin replicate add minio1 minio2 minio3
   ```

   如果所有站点均为空，则别名顺序无关紧要。 如果其中一个站点包含任何 [可复制数据](#minio-site-replication-what-replicates)，则必须将其列在第一位。

   最多只能有一个站点包含可复制数据。
4. 查询站点复制配置进行验证

   ```shell
   mc admin replicate info minio1
   ```

   可以使用站点复制配置中任意对等站点的别名。
5. 查询站点复制状态，确认初始数据已复制到所有对等站点。

   ```shell
   mc admin replicate status minio1
   ```

   可以使用站点复制配置中任意对等站点的别名。 输出应表明所有 [可复制数据](#minio-site-replication-what-replicates) 均已同步。

   输出可能类似如下：

   ```shell
   Bucket replication status:
   ●  1/1 Buckets in sync

   Policy replication status:
   ●  5/5 Policies in sync

   User replication status:
   No Users present

   Group replication status:
   No Groups present
   ```

   有关检查站点复制的更多信息，请参阅 [站点复制状态教程](#minio-site-replication-status-tutorial)。

<a id="minio-expand-site-replication"></a>

### 扩展站点复制 {#expand-site-replication}

可以向现有站点复制配置中添加更多站点。

新站点必须满足以下要求：

- 站点已完成部署，并可通过主机名或 IP 访问
- 与配置中的其他站点共享相同的 IDP 配置
- 使用与其他已配置站点相同的 root 用户凭证
- 不包含任何存储桶或对象数据

1. 按照上述要求部署新的 MinIO 对等站点
2. 为新站点配置别名

   指定该站点的负载均衡器、反向代理或类似网络控制平面组件的 URL 或 IP 地址。 请求会自动路由到部署中的各个节点。

   MinIO 不建议为对等站点使用单个节点主机名。 这会形成单点故障：如果该节点离线，复制就会失败。

   要检查现有别名，请使用 [`mc alias list`](/zh/reference/minio-mc/mc-alias-list/#command-mc.alias.list)。

   使用 [`mc alias set`](/zh/reference/minio-mc/mc-alias-set/#command-mc.alias.set) 定义管理新站点连接的负载均衡器主机名或 IP。

   ```shell
   mc alias set minio4 https://minio4.example.com:9000 adminuser adminpassword
   ```

   或定义环境变量

   ```shell
   export MC_HOST_minio4=https://adminuser:adminpassword@minio4.example.com
   ```

3. 添加站点复制配置

   使用 [`mc admin replicate add`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.add) 命令，将新的对等站点加入站点复制配置中。 先指定 *所有* 现有对等站点的别名，再指定要添加的新站点别名。

   例如，以下命令将新的对等站点 `minio4` 添加到现有站点复制配置中，该配置已包含 `minio1`、`minio2` 和 `minio3` 三个站点。

   ```shell
   mc admin replicate add minio1 minio2 minio3 minio4
   ```

   > [!NOTE]
   > **说明**
   >
   > 如果任一站点不可达或已永久丢失，则在使用新站点进行扩展前，必须先使用 [`mc admin replicate rm`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm) 移除不可达站点。
4. 查询站点复制配置进行验证

   ```shell
   mc admin replicate info minio1
   ```

### 修改站点的端点 {#modify-a-site-s-endpoint}

如果某个对等站点变更了主机名，可以修改复制配置以反映新的主机名。

1. 使用 [`mc admin replicate info`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.info) 获取站点的 Deployment ID

   ```shell
   mc admin replicate info <ALIAS>
   ```

2. 使用 [`mc admin replicate update`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.update) 更新站点的端点

   ```shell
   mc admin replicate update ALIAS --deployment-id [DEPLOYMENT-ID] --endpoint [NEW-ENDPOINT]
   ```

   将 \[DEPLOYMENT-ID\] 替换为要更新站点的 deployment ID。

   将 \[NEW-ENDPOINT\] 替换为该站点的新端点。

   指定该站点的负载均衡器、反向代理或类似网络控制平面组件的 URL 或 IP 地址。 请求会自动路由到部署中的各个节点。

   MinIO 不建议为对等站点使用单个节点主机名。 这会形成单点故障：如果该节点离线，复制就会失败。

### 从复制中移除站点 {#remove-a-site-from-replication}

可以随时将某个站点从复制中移除。 后续也可以重新添加该站点，但必须先彻底清除该站点上的存储桶和对象数据。

使用 [`mc admin replicate rm`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.rm)：

```shell
mc admin replicate rm ALIAS PEER_TO_REMOVE --force
```

- 将 `ALIAS` 替换为复制配置中任意对等站点的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)。
- 将 `PEER_TO_REMOVE` 替换为要移除的对等站点别名。

站点复制配置中的所有健康对等站点都会自动更新，以移除指定的对等站点。

MinIO 要求使用 `--force` 标志，才能将该对等站点从站点复制配置中移除。

<a id="minio-site-replication-status-tutorial"></a>

### 查看复制状态 {#review-replication-status}

MinIO 提供跨站点的用户、组、策略或存储桶复制信息。

汇总信息包括各类别中 **Synced** 和 **Failed** 项目的数量。

使用 [`mc admin replicate status`](/zh/reference/minio-mc-admin/mc-admin-replicate/#mc.admin.replicate.status)：

```shell
mc admin replicate status <ALIAS> --<flag> <value>
```

例如：

- `mc admin replicate status minio3 --bucket images`

  显示 `minio3` 站点上 `images` 存储桶的复制状态。

  输出类似如下：

  ```text
  ●  Bucket config replication summary for: images

  Bucket          | MINIO2          | MINIO3          | MINIO4
  Tags            |                 |                 |
  Policy          |                 |                 |
  Quota           |                 |                 |
  Retention       |                 |                 |
  Encryption      |                 |                 |
  Replication     | ✔               | ✔               | ✔
  ```

- `mc admin replicate status minio3 --all`

  显示 `minio3` 所属全部复制站点的复制状态摘要。

  输出类似如下：

  ```text
  Bucket replication status:
  ●  1/1 Buckets in sync

  Policy replication status:
  ●  5/5 Policies in sync

  User replication status:
  ●  1/1 Users in sync

  Group replication status:
  ●  0/2 Groups in sync

  Group           | MINIO2          | MINIO3          | MINIO4
  ittechs         | ✗  in-sync      |                 | ✗  in-sync
  managers        | ✗  in-sync      |                 | ✗  in-sync
  ```
