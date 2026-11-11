---
title: "退役 服务器池"
url: "/zh/operations/deployments/baremetal-decommission-server-pool/"
weight: 40
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-decommission-server-pool.rst
upstream_modified: true
---

自 Server 20261018 起，退役迁移会保留 null 与 UUID 删除标记，即使它是源池中唯一的版本，因为其他池可能仍有旧数据版本。远端分层对象通过元数据／引用迁移路径处理；保持远端层可用，并在移除池前核对版本、标签、删除状态与实际读取。见[迁移契约](/zh/blog/design/multi-pool-object-consistency/#migration-20261018)。

下方桶／IAM 导出只覆盖配置，不是完整恢复快照。使用持久 IAM 撤销时，还须保留后端删除历史与必要加密材料，见 [IAM 恢复](/zh/operations/replication/iam-upgrade/)。

<a id="decommission-server-pools"></a>
<a id="minio-decommissioning"></a>

MinIO 支持从包含两个或更多 pool 的部署中退役并移除 [服务器池](/zh/operations/concepts/#minio-intro-server-pool)。执行退役前，至少必须保留一个具有足够可用空间的 pool，以接收被退役 pool 中的对象。

从 `RELEASE.2023-01-18T04-36-38Z` 起，MinIO 支持在一条退役命令中排队 [多个 pool](#minio-decommission-multiple-pools)。 每个被列出的 pool 会立即进入只读状态，但实际排空过程一次只处理一个 pool。

退役功能适用于移除那些相较于当前部署中其他 pool 而言，硬件能力或性能已经不足的旧 服务器池。 MinIO 会根据各 pool 的空闲空间占比，自动将被退役 pool 中的数据迁移到部署中其余 pool。

在退役过程中，MinIO 会像平常一样路由读取操作（例如 `GET`、`LIST`、`HEAD`）。 写入操作（例如 `PUT`、带版本的 `DELETE`）会被路由到部署中其余仍处于“active”状态的 pool。 带版本对象在迁移过程中会保持其顺序。

本页步骤用于从至少包含两个 服务器池 的 [分布式](/zh/operations/deployments/installation/#deploy-minio-distributed) MinIO 部署中退役并移除一个或多个 服务器池。

> [!NOTE]
> **退役是永久性的**
>
> 一旦 MinIO 开始退役某个 pool，就会将其标记为 *永久* 非活跃（“draining”）状态。 取消或以其他方式中断退役流程，**不会** 将该 pool 恢复为 active 状态。 退役多个 pool 时必须格外谨慎。
>
> 退役是一项重大的管理操作，规划与执行都需要谨慎对待，并不是轻量或“日常型”的任务。
>
> 如需协助，请参见 [SILO 故障排查](/zh/operations/troubleshooting/)。

<a id="minio-decommissioning-prereqs" data-td-print-local></a>

## 前提条件 {#prerequisites}

<a id="id4" data-td-print-local></a>

### 先备份集群设置 {#back-up-cluster-settings-first}

在开始退役前，使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 和 [`mc admin cluster iam export`](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) 命令分别为存储桶元数据和 IAM 配置创建快照。 必要时，你可以使用这些快照恢复存储桶/IAM 设置，以从用户错误或流程错误中恢复。

<a id="id5" data-td-print-local></a>

### 网络与防火墙 {#networking-and-firewalls}

部署中的每个节点都应当与其他所有节点具备完整的双向网络访问能力。 对于容器化或编排式基础设施，这可能需要针对 Ingress、负载均衡器等网络和路由组件进行专门配置。 某些操作系统还可能需要设置防火墙规则。 例如，以下命令会在使用 `firewalld` 的服务器上显式开放 MinIO server 默认 API 端口 `9000`：

```shell
firewall-cmd --permanent --zone=public --add-port=9000/tcp
firewall-cmd --reload
```

如果你为 [MinIO Console](/zh/administration/minio-console/#minio-console) 设置了静态端口（例如 `:9001`）， 则还必须允许外部客户端访问该端口，以确保连接可用。

MinIO **强烈建议** 使用负载均衡器管理到集群的连接。 由于部署中的任意 MinIO 节点都可以接收、转发或处理客户端请求，因此负载均衡器应采用 “Least Connections” 算法将请求路由到 MinIO 部署。

以下负载均衡器已知可与 MinIO 良好配合：

- [NGINX](https://www.nginx.com/products/nginx/load-balancing/)
- [HAProxy](https://cbonte.github.io/haproxy-dconv/2.3/intro.html#3.3.5)

如何配置防火墙或负载均衡器以支持 MinIO 不在本步骤范围内。

<a id="id6" data-td-print-local></a>

### 部署必须具备足够的存储空间 {#deployment-must-have-sufficient-storage}

退役过程会将目标 pool 中的对象迁移到部署中的其他 pool。 该部署的总可用存储空间 *必须* 大于被退役 pool 的总存储量。

使用 [纠删码计算器](https://min.io/product/erasure-code-calculator) 确认可用存储容量。 然后再减去部署中现有对象已占用的空间。

例如，假设某个部署的已用和空闲存储分布如下：

| 存储池 | 已用容量    | 总容量      |
| ------ | ----------- | ----------- |
| Pool 1 | 100 TB 已用 | 200 TB 总计 |
| Pool 2 | 100 TB 已用 | 200 TB 总计 |
| Pool 3 | 100 TB 已用 | 200 TB 总计 |
{.wide .expand}

退役 Pool 1 需要将这 100TB 已用存储分散到其余 pool 上。 Pool 2 和 Pool 3 各自都有 100TB 未使用存储空间，因此可以安全接收 Pool 1 上的数据。

但如果 Pool 1 已满（例如已使用 200TB），退役会将剩余 pool 完全填满，并可能阻止任何后续写入操作。

<a id="id7" data-td-print-local></a>

## 注意事项 {#considerations}

<a id="id8" data-td-print-local></a>

### 替换 服务器池 {#replacing-a-server-pool}

对于通过新 pool 硬件替换旧 pool 硬件的升级周期，你应先通过 [扩容](/zh/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed) 添加新 pool，再开始退役旧 pool。 先添加新 pool，有助于退役过程在所有可用 pool（包括现有 pool 和新 pool）之间更均衡地迁移对象。

在退役旧硬件 pool 之前，请先完成所有计划中的 [硬件扩容](/zh/operations/deployments/baremetal-expand-minio-deployment/#expand-minio-distributed)。

退役要求集群拓扑在整个 pool 排空过程中保持稳定。 **不要** 试图在同一步骤中同时执行扩容和退役变更。

<a id="id9" data-td-print-local></a>

### 退役可恢复继续执行 {#decommissioning-is-resumable}

如果退役因部署重启、网络故障等瞬时问题而中断，MinIO 会自动继续该过程。

对于人工取消或失败的退役尝试，只有在你手动重新发起退役操作后，MinIO 才会恢复执行。

无论中断原因为何，该 pool 都会持续保持在退役状态。 退役一旦开始，该 pool *永远* 无法恢复为 active 状态。

<a id="id10" data-td-print-local></a>

### 迁移与最终重启 {#decommissioning-is-non-disruptive}

移除已退役的 服务器池 需要在大致同一时间重启部署中的 *所有* MinIO 节点。

完成退役并移除池配置后，全部 SILO 节点需要协调重启，使用一致的剩余池列表。全量重启会暂时中断服务，正在进行的请求可能失败；请安排维护窗口，并让客户端按操作语义重试和核验结果。

**不要** 执行“滚动”重启（例如一次只重启一个节点）。

<a id="deletemarker" data-td-print-local></a>

### 删除标记、过期对象与迁移验证 {#decommissioning-ignores-expired-objects-and-trailing-deletemarker}

SILO Server 20261018 及更高版本会迁移 `null` 和 UUID 删除标记，包括源池中唯一剩下的删除标记。其他池可能仍保留同名对象的旧数据版本，因此不能仅因本池没有其他版本就丢弃标记。这替代了旧版上游跳过孤立删除标记的行为。

退役过程会评估[生命周期规则](/zh/administration/object-management/object-lifecycle-management/#minio-lifecycle-management-expiration)，对跨全部存储池确认可安全过期的对象或版本执行过期处理，并跳过不必要的载荷迁移。[SILO 20261109](/zh/blog/release/silo-20261109/) 在池退役与再平衡期间仅当 `MINIO_SCANNER_SUBSYSTEMS` 启用 `scanner` 时才评估 ILM 规则，先评估生命周期动作（`evalActionFromLifecycle`）再评估分层转移（`evalScannerTransition`）（见 [ILM 迁移顺序](/zh/blog/design/ilm-migration-ordering/)），并包含以下池退役修复：

- 支持迁移跨存储池副本具有不同纠删码布局的对象（[#261](https://github.com/pgsty/silo/issues/261)）。
- 迁移已被 ILM 判定过期的当前版本，避免跳过或将其遗留在退役池中（[#265](https://github.com/pgsty/silo/issues/265)）。
- 对无法在所有存储池上安全完成生命周期过期的版本（例如跨池版本历史或 Object Lock 保护状态缺少权威仲裁）改为迁移而非丢弃（[#278](https://github.com/pgsty/silo/issues/278)，[`5cb91e7d7`](https://github.com/pgsty/silo/commit/5cb91e7d7)）。
- 只要其他存储池仍引用远端分层对象，就保留该远端对象（[#306](https://github.com/pgsty/silo/issues/306)、[#308](https://github.com/pgsty/silo/issues/308)）。
- 单个存储桶无法完成退役时继续迁移后续存储桶，并保留取消能力（[#307](https://github.com/pgsty/silo/issues/307)）。

可使用 [`mc admin trace --call decommission`](/zh/reference/minio-mc-admin/mc-admin-trace/#mc.admin.trace.-call) 查看迁移与跳过原因。

当前版本保留对象标签及其修订字段，并在清理源副本前重新核对已迁移的版本。升级不会恢复早期迁移已经丢失的标签。详见[跨池迁移契约](/zh/blog/design/multi-pool-object-consistency/#migration-20261018)。

仅在退役状态为 `Complete`，且通过 S3 核验目标版本、标签、数据及删除状态后，才移除池配置并按流程下线旧池。销毁旧盘前保留所需备份，不能把“只剩删除标记”当作可直接清盘的依据。

<a id="id11" data-td-print-local></a>

## 行为说明 {#behavior}

<a id="id12" data-td-print-local></a>

### 20261109 之后的候选修复（未发布） {#candidate-progress}

Server 20261109 的物理列举先遇到同名父对象时，可能遗漏其下的子键（[#293](https://github.com/pgsty/silo/issues/293)）。下一候选版本在确认源版本被移除、更多子键显露后重新扫描存储桶，修复这一历史列举限制；逻辑层返回 NotFound 不再被当作源磁盘已清空的证据。

退役和再平衡会在同名的另一个版本被并发删除时，继续清理已经成功迁移的版本。只有确认源端移除，包括安全清理的 free-version 记录，才计为进展；不可读或相互冲突的元数据不计为不存在。源端清理与最终清空核验会检查每一块在线磁盘，允许纠删集读仲裁容错范围内的离线坏盘，但继续拒绝在线盘残留元数据、损坏元数据、目录错误以及超出容错阈值的磁盘离线。扫描没有物理进展时停止；源端仍有物理元数据时，最终检查会返回错误，阻止标记完成。取消也返回错误。失败后应先检查报告中的元数据或磁盘问题，再重新发起操作。

最终物理清空检查仍然必需。如果 free-version 记录仍承担远端分层清理所有权，就不能为了排空池而直接丢弃；未解决的分层所有权仍会阻止完成。这些改动未包含在 20261109 制品中，发布边界见[候选兼容性说明](/zh/compatibility/server/)。

### 最终列表检查 {#final-listing-check}

在退役过程结束时，MinIO 会检查该 pool 上是否还有对象列表。 如果列表为空，MinIO 会将退役标记为成功完成。 如果仍返回任何对象，MinIO 会报错，指出退役过程失败。

如果退役失败，请保留日志，检查池健康状态与可用容量，并在查明原因后再重试。如需协助，请参见 [SILO 故障排查](/zh/operations/troubleshooting/)。

<a id="tiering-server" data-td-print-local></a>

### 对已启用 Tiering 的 Server 执行退役 {#decommissioning-a-server-with-tiering-enabled}

> [!NOTE]
> **变更: RELEASE.2023-03-20T20-16-18Z**

对于已启用并处于活动状态的 tiering 部署，退役会将对象引用迁移到新的 active pool，并且 [SILO 20261109](/zh/blog/release/silo-20261109/) 在其他存储池仍引用远端对象时保留该远端数据（[#306](https://github.com/pgsty/silo/issues/306)、[#308](https://github.com/pgsty/silo/issues/308)）。应用程序可继续对这些对象发出 `GET` 请求，由 SILO 透明地从远端 tier 检索数据。

在旧版本 MinIO 中，tiering 配置会阻止退役操作。

> [!WARNING]
> **退役完成前，保留所有远端 tier 的配置**
>
> tier free version 是某个仍待删除远端对象的内部记录。退役会在确认没有其他存储池引用后先删除远端对象、再移除该记录，因此在池退役完成前必须保留记录所指向的远端 tier 配置。若该 tier 已从配置中移除，退役会失败且记录仍留在退役池中。[SILO 20261109](/zh/blog/release/silo-20261109/) 会先继续迁移其余所有存储桶，并在错误信息中列出该 free version、对应的远端对象和缺失的 tier（[#307](https://github.com/pgsty/silo/issues/307)）。
>
> 请使用 [`mcli ilm tier add`](/zh/reference/minio-mc/mc-ilm-tier-add/#command-mc.ilm.tier.add) 以相同名称重新添加该 tier，然后重新运行 [`mcli admin decommission start`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) 继续处理剩余存储桶。参见[分层游离版本是内部清理记录](/zh/blog/design/tier-free-version-semantics/#operations)。

<a id="id13"></a>

<a id="minio-decommissioning-server-pool" data-td-print-local></a>

## 退役单个 服务器池 {#decommission-a-server-pool}

<a id="minio" data-td-print-local></a>

### 1) 查看 MinIO 部署拓扑 {#review-the-minio-deployment-topology}

[`mc admin decommission`](/zh/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission) 命令会返回 MinIO 部署中所有 pool 的列表：

```shell
mc admin decommission status myminio
```

命令返回的输出类似如下：

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Active │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  60 TiB (used) / 100 TiB (total) │ Active │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 100 TiB (total) │ Active │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴────────┘
```

上例部署共有三个 pool。 每个 pool 都有四台服务器，每台服务器有四块驱动器。

确定要退役的目标 pool，并检查当前容量。 部署中其余 pool 的总容量 *必须* 足以迁移被退役 pool 中存储的所有对象。

在上述示例中，该部署总存储为 210TiB，其中已使用 110TiB。 第一个 pool（`minio-{01...04}`）是退役目标，因为它是在 MinIO 部署创建时配置的，并且已经完全写满。 其余较新的 pool 可以吸收该 pool 中的所有对象，而不会显著影响总可用存储。

<a id="id14" data-td-print-local></a>

### 2) 启动退役过程 {#start-the-decommissioning-process}

> [!NOTE]
> **退役是永久性的**
>
> 一旦 MinIO 开始退役某个 pool，就会将其标记为 *永久* 非活跃（“draining”）状态。 取消或以其他方式中断退役流程，**不会** 将该 pool 恢复为 active 状态。
>
> 在运行以下命令前，请先确认并验证你要退役的是正确的 pool。

使用 [`mc admin decommission start`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) 命令开始退役目标 pool。 指定部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)，以及待退役 pool 的完整描述，包括所有主机、磁盘和文件路径。

```shell
mc admin decommission start myminio/ https://minio-{01...04}.example.net:9000/mnt/disk{1...4}/minio
```

该示例命令会在 `myminio` 部署上启动对匹配 服务器池 的退役。

在退役过程中，对于尚未迁移的对象，MinIO 会继续将读取操作（`GET`、`LIST`、`HEAD`）路由到该 pool。 所有新的写入操作（`PUT`）都会被路由到部署中其余 pool。

此时，负责管理部署连接的负载均衡器、反向代理或其他网络控制组件无需修改其配置。

<a id="id15" data-td-print-local></a>

### 3) 监控退役过程 {#monitor-the-decommissioning-process}

使用 [`mc admin decommission status`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) 命令监控退役过程。

```shell
mc admin decommission status myminio
```

命令返回的输出类似如下：

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬──────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status   │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Draining │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  60 TiB (used) / 100 TiB (total) │ Active   │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 100 TiB (total) │ Active   │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴──────────┘
```

你可以在命令中指定 服务器池 的描述，以获取更详细的信息：

```shell
mc admin decommission status myminio https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio
```

命令返回的输出类似如下：

```shell
Decommissioning rate at 100MiB/sec [1TiB/10TiB]
Started: 30 minutes ago
```

[`mc admin decommission status`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) 会在退役完成后将 **Status** 标记为 **Complete**。 一旦退役完成，你就可以继续下一步。

如果 **Status** 显示为 failed，你可以重新运行 [`mc admin decommission start`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) 命令以恢复该过程。 如果失败持续存在，请使用 [`mc admin logs`](/zh/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) 或查看 `systemd` 日志（例如 `journalctl -u silo`），以定位更具体的错误。

<a id="pool" data-td-print-local></a>

### 4) 从部署配置中移除已退役的 Pool {#remove-the-decommissioned-pool-from-the-deployment-configuration}

每当一个 pool 完成退役后，你都可以安全地将其从部署配置中移除。 请修改部署中每个剩余 MinIO server 的启动命令，并移除已退役 pool。

`.deb` 或 `.rpm` 软件包会将 [systemd](https://www.freedesktop.org/wiki/Software/systemd/) 服务文件安装到 `/lib/systemd/system/silo.service`。 对于二进制安装，本步骤默认该文件已按照 [安装与管理](/zh/operations/deployments/installation/#deploy-minio-distributed) 流程手动创建。

`silo.service` 文件使用位于 `/etc/default/silo` 的环境文件读取配置设置，其中也包括启动配置。 具体来说，`MINIO_VOLUMES` 变量定义了启动命令：

```shell
cat /etc/default/silo | grep "MINIO_VOLUMES"
```

命令返回的输出类似如下：

```shell
MINIO_VOLUMES="https://minio-{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio-{5...8}.example.net:9000/mnt/disk{1...4}/minio https://minio-{9...12}.example.net:9000/mnt/disk{1...4}/minio"
```

编辑该环境文件，并从 `MINIO_VOLUMES` 的值中移除已退役 pool。

<a id="id16" data-td-print-local></a>

### 5) 更新网络控制平面 {#update-network-control-plane}

更新所有负载均衡器、反向代理或其他网络控制平面，从 MinIO 部署的连接配置中移除已退役的 服务器池。

网络控制平面组件的具体配置说明不在本步骤范围内。

<a id="id17" data-td-print-local></a>

### 6) 重启 MinIO 部署 {#restart-the-minio-deployment}

在部署中的每个节点上 **同时** 执行以下命令，以重启 MinIO 服务：

```shell
sudo systemctl restart silo.service
```

使用以下命令确认服务已上线并正常运行：

```shell
sudo systemctl status silo.service
journalctl -f -u silo.service
```

在服务端进程连接与同步期间，SILO 可能会记录较多非致命告警。这些告警通常是暂时性的，待部署完全上线后即会消失。

完成退役并移除池配置后，全部 SILO 节点需要协调重启，使用一致的剩余池列表。全量重启会暂时中断服务，正在进行的请求可能失败；请安排维护窗口，并让客户端按操作语义重试和核验结果。

**不要** 执行“滚动”重启（例如一次只重启一个节点）。

部署重新上线后，使用 [`mc admin info`](/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) 确认部署中所有剩余 server 的运行状态。

<a id="id18" data-td-print-local></a>

<a id="minio-decommission-multiple-pools" data-td-print-local></a>

## 退役多个 服务器池 {#decommission-multiple-server-pools}

> [!NOTE]
> **变更: RELEASE.2023-01-18T04-36-38Z**

在执行退役命令时，你可以一次性启动多个 服务器池 的退役过程。

输入该命令后：

- MinIO 会立即停止对所有待退役 pool 的写访问。
- 退役一次只处理一个 pool。
- 每个 pool 完成排空后，MinIO 才会开始排空下一个 pool。

若要通过一条命令退役多个 服务器池，请将每个待退役 服务器池 的完整描述以逗号分隔列表的形式追加到命令中。

执行多 server 退役时，其他所有关于退役的注意事项同样适用。

- 退役是永久性的。
- 一旦将这些 pool 标记为退役，你就 **无法** 恢复它们。
- 请确认你选择的是预期的 pool。

<a id="id19" data-td-print-local></a>

### 1) 查看 MinIO 部署拓扑 {#id1}

[`mc admin decommission`](/zh/reference/minio-mc-admin/mc-admin-decommission/#command-mc.admin.decommission) 命令会返回 MinIO 部署中所有 pool 的列表：

```shell
mc admin decommission status myminio
```

命令返回的输出类似如下：

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Active │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  95 TiB (used) / 100 TiB (total) │ Active │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 500 TiB (total) │ Active │
│ 4th │ https://minio-{13...16}.example.com:9000/mnt/disk{1...4}/minio │  0  TiB (used) / 500 TiB (total) │ Active │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴────────┘
```

上例部署共有四个 pool。每个 pool 都有四台服务器，每台服务器有四块驱动器。

确定要退役的目标 pool，并检查当前容量。部署中其余 pool 的总容量 *必须* 足以迁移被退役 pool 中存储的所有对象。

在上述示例中，该部署总存储为 1110 TiB，其中已使用 145 TiB。

- 第一个 pool（`minio-{01...04}`）是第一个退役目标，因为它是在 MinIO 部署创建时配置的，并且已经完全写满。
- 第二个 pool（`minio-{05...08}`）是第二个退役目标，因为它同样是在部署创建时配置的，并且已接近写满。
- 第四个 pool（`minio-{13...16}`）是一个刚通过 server 扩容加入的新硬件 pool。

第三个和第四个 pool 可以吸收第一个与第二个 pool 上的全部对象，而不会显著影响总可用存储。

> [!WARNING]
> **重要**
>
> 在开始退役前，请先完成所有新增存储资源所需的 server 扩容。

<a id="id20" data-td-print-local></a>

### 2) 启动退役过程 {#id2}

> [!NOTE]
> **退役是永久性的**
>
> 一旦 MinIO 开始退役这些 pool，就会将它们标记为 *永久* 非活跃（“draining”）状态。 取消或以其他方式中断退役流程，**不会** 将这些 pool 恢复为 active 状态。
>
> 在运行以下命令前，请先确认并验证你要退役的是正确的 pool。

使用 [`mc admin decommission start`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) 命令开始退役目标 pool。 指定部署的 [alias](/zh/reference/minio-mc/mc-alias-set/#alias)，以及以逗号分隔的每个待退役 pool 的完整描述，包括所有主机、磁盘和文件路径。

```shell
mc admin decommission start myminio/ https://minio-{01...04}.example.net:9000/mnt/disk{1...4}/minio,https://minio-{05...08}.example.net:9000/mnt/disk{1...4}/minio
```

该示例命令会在 `myminio` 部署上启动对所列两个匹配 服务器池 的退役。

在退役过程中，对于尚未迁移的对象，MinIO 会继续将读取操作（`GET`、`LIST`、`HEAD`）路由到这些 pool。 所有新的写入操作（`PUT`）都会被路由到部署中那些未计划退役的其余 pool。

已退役 pool 的排空一次只处理一个 pool，并按顺序依次完成每个 pool 的退役。 排空过程 *不会* 对所有待退役 pool 并发执行。

此时，负责管理部署连接的负载均衡器、反向代理或其他网络控制组件无需修改其配置。

<a id="id21" data-td-print-local></a>

### 3) 监控退役过程 {#id3}

使用 [`mc admin decommission status`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) 命令监控退役过程。

```shell
mc admin decommission status myminio
```

命令返回的输出类似如下：

```shell
┌─────┬────────────────────────────────────────────────────────────────┬──────────────────────────────────┬──────────┐
│ ID  │ Pools                                                          │ Capacity                         │ Status   │
│ 1st │ https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio │  10 TiB (used) / 10  TiB (total) │ Draining │
│ 2nd │ https://minio-{05...08}.example.com:9000/mnt/disk{1...4}/minio │  95 TiB (used) / 100 TiB (total) │ Pending  │
│ 3rd │ https://minio-{09...12}.example.com:9000/mnt/disk{1...4}/minio │  40 TiB (used) / 500 TiB (total) │ Active   │
│ 4th │ https://minio-{13...16}.example.com:9000/mnt/disk{1...4}/minio │  0  TiB (used) / 500 TiB (total) │ Active   │
└─────┴────────────────────────────────────────────────────────────────┴──────────────────────────────────┴──────────┘
```

你可以在命令中指定 服务器池 的描述，以获取更详细的信息：

```shell
mc admin decommission status myminio https://minio-{01...04}.example.com:9000/mnt/disk{1...4}/minio
```

命令返回的输出类似如下：

```shell
Decommissioning rate at 100MiB/sec [1TiB/10TiB]
Started: 30 minutes ago
```

[`mc admin decommission status`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.status) 会在退役完成后将 **Status** 标记为 **Complete**。 当 MinIO 完成所有 pool 的退役后，你就可以继续下一步。

如果 **Status** 显示为 failed，你可以重新运行 [`mc admin decommission start`](/zh/reference/minio-mc-admin/mc-admin-decommission/#mc.admin.decommission.start) 命令以恢复该过程。 如果失败持续存在，请使用 [`mc admin logs`](/zh/reference/minio-mc-admin/mc-admin-logs/#command-mc.admin.logs) 或查看 `systemd` 日志（例如 `journalctl -u silo`），以定位更具体的错误。

<a id="id22" data-td-print-local></a>

### 4) 从部署配置中移除已退役的 Pool {#remove-the-decommissioned-pools-from-the-deployment-configuration}

退役完成后，你就可以安全地将这些 pool 从部署配置中移除。 请修改部署中每个剩余 MinIO server 的启动命令，并移除已退役 pool。

`.deb` 或 `.rpm` 软件包会将 [systemd](https://www.freedesktop.org/wiki/Software/systemd/) 服务文件安装到 `/lib/systemd/system/silo.service`。 对于二进制安装，本步骤默认该文件已按照 [安装与管理](/zh/operations/deployments/installation/#deploy-minio-distributed) 流程手动创建。

`silo.service` 文件使用位于 `/etc/default/silo` 的环境文件读取配置设置，其中也包括启动配置。 具体来说，`MINIO_VOLUMES` 变量定义了启动命令：

```shell
cat /etc/default/silo | grep "MINIO_VOLUMES"
```

命令返回的输出类似如下：

```shell
MINIO_VOLUMES="https://minio-{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio-{5...8}.example.net:9000/mnt/disk{1...4}/minio https://minio-{9...12}.example.net:9000/mnt/disk{1...4}/minio"
```

编辑该环境文件，并从 `MINIO_VOLUMES` 的值中移除已退役 pool。

<a id="id23" data-td-print-local></a>

### 5) 更新网络控制平面 {#update-network-control-plane-multiple}

更新所有负载均衡器、反向代理或其他网络控制平面，从 MinIO 部署的连接配置中移除已退役的 服务器池。

网络控制平面组件的具体配置说明不在本步骤范围内。

<a id="id24" data-td-print-local></a>

### 6) 重启 MinIO 部署 {#restart-the-minio-deployment-multiple}

在部署中的每个节点上 **同时** 执行以下命令，以重启 MinIO 服务：

```shell
sudo systemctl restart silo.service
```

使用以下命令确认服务已上线并正常运行：

```shell
sudo systemctl status silo.service
journalctl -f -u silo.service
```

在服务端进程连接与同步期间，SILO 可能会记录较多非致命告警。这些告警通常是暂时性的，待部署完全上线后即会消失。

完成退役并移除池配置后，全部 SILO 节点需要协调重启，使用一致的剩余池列表。全量重启会暂时中断服务，正在进行的请求可能失败；请安排维护窗口，并让客户端按操作语义重试和核验结果。

**不要** 执行“滚动”重启（例如一次只重启一个节点）。

部署重新上线后，使用 [`mc admin info`](/zh/reference/minio-mc-admin/mc-admin-info/#command-mc.admin.info) 确认部署中所有剩余 server 的运行状态。
