---
title: "扩展分布式 Silo 部署"
url: "/zh/operations/deployments/baremetal-expand-minio-deployment/"
weight: 30
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/deployments/baremetal-expand-minio-deployment.rst
upstream_modified: true
math: true
---

<a id="minio" data-td-print-local></a>
<a id="expand-minio-distributed"></a>

Silo 支持通过添加新的[服务器池](/zh/operations/concepts/#minio-intro-server-pool)扩展现有分布式部署。每个 pool 都会增加集群的总可用存储容量。

扩容不提供业务连续性或灾难恢复（BC/DR）级别的保护。各池有独立的[纠删码集合](/zh/operations/concepts/erasure-coding/#minio-ec-erasure-set)，增加新池不会复制旧池中的对象。一个池不可用时，依赖它的对象及需要检查全部池的写入、删除等操作可能失败；其他池中仍有足够数据和元数据的对象可能继续可读。失去仲裁首先意味着不可用，只有必要分片永久丢失且无可用副本时才构成永久数据丢失。

新的 服务器池 **不必** 与现有任一 服务器池 使用相同类型或规格的硬件和软件配置，不过保持一致通常有助于简化集群管理，并让各 pool 间的性能表现更可预测。 新 pool 内的所有驱动器 **应当** 保持相同类型和容量。 有关如何选择合适配置的完整建议，请参阅 MinIO 的 [硬件建议](/zh/operations/checklists/hardware/#minio-hardware-checklist)。

若要为单 pool 或多 pool 的 MinIO 部署提供 BC/DR 级别的故障切换与恢复支持，请使用 [站点复制](/zh/operations/replication/multi-site-replication/#minio-site-replication-overview)。

本页步骤用于为现有 [分布式](/zh/operations/deployments/installation/#deploy-minio-distributed) MinIO 部署增加一个额外的 服务器池。

> [!WARNING]
> **重要**
>
> MinIO 不支持扩展 单机单盘 拓扑。

<a id="id2" data-td-print-local></a>

## 前提条件 {#expand-minio-distributed-prereqs}

### 网络与防火墙 {#id3}

部署中的每个节点都应当与其他所有节点具备完整的双向网络访问能力。 对于容器化或编排式基础设施，这可能需要针对 Ingress、负载均衡器等网络和路由组件进行专门配置。 某些操作系统还可能需要设置防火墙规则。 例如，以下命令会在使用 `firewalld` 的服务器上显式开放 MinIO server 默认 API 端口 `9000`：

```shell
firewall-cmd --permanent --zone=public --add-port=9000/tcp
firewall-cmd --reload
```

部署中的所有 MinIO server *必须* 使用相同的监听端口。

如果你为 [MinIO Console](/zh/administration/minio-console/#minio-console) 设置了静态端口（例如 `:9001`）， 则还必须允许外部客户端访问该端口，以确保连接可用。

MinIO **强烈建议** 使用负载均衡器管理到集群的连接。 由于部署中的任意 MinIO 节点都可以接收、转发或处理客户端请求，因此负载均衡器应采用 “Least Connections” 算法将请求路由到 MinIO 部署。

以下负载均衡器已知可与 MinIO 良好配合：

- [NGINX](https://www.nginx.com/products/nginx/load-balancing/)
- [HAProxy](https://cbonte.github.io/haproxy-dconv/2.3/intro.html#3.3.5)

如何配置防火墙或负载均衡器以支持 MinIO 不在本步骤范围内。 [为 MinIO Server 配置 NGINX 代理](/zh/integrations/setup-nginx-proxy-with-minio/#integrations-nginx-proxy) 参考页提供了一个将 NGINX 作为反向代理并启用基础负载均衡的基线配置。

### 连续主机名 {#id4}

MinIO 在创建 服务器池 时，*要求* 使用扩展表示法 `{x...y}` 来表示一组连续的 MinIO 主机。 因此，MinIO *要求* 使用连续编号的主机名来表示 pool 中的每个 [`silo server`](/zh/reference/minio-server/#command-minio.server) 进程。

在开始本步骤之前，请先创建所需的 DNS 主机名映射。 例如，以下主机名可用于一个 4 节点分布式 服务器池：

- `minio5.example.com`
- `minio6.example.com`
- `minio7.example.com`
- `minio8.example.com`

你可以使用扩展表示法 `minio{5...8}.example.com` 来指定完整的主机名范围。

如何配置 DNS 以支持 MinIO 不在本步骤范围内。

### 存储要求 {#id5}

以下要求概括了 MinIO 硬件建议中的 [存储](/zh/operations/checklists/hardware/#minio-hardware-checklist-storage) 一节：

**使用本地存储**

> 直连存储（DAS）相比网络存储 （<abbr title="Network Attached Storage">NAS</abbr>、<abbr title="Storage Area Network">SAN</abbr>、 <abbr title="Network File Storage">NFS</abbr>）在性能和一致性方面具有显著优势。 对于主数据或“热”数据，MinIO 强烈建议使用闪存存储（NVMe、SSD）。

**磁盘使用 XFS 格式**

> MinIO 强烈建议为存储配置使用 XFS 格式化的磁盘。 MinIO 在内部测试和验证套件中使用 XFS，因此对其在各种规模下的性能和行为更有信心。
>
> 对于 EXT4、BTRFS 或 ZFS 等其他文件系统，MinIO **既不** 测试，也不推荐。

**使用一致的磁盘类型**

> MinIO 不区分磁盘类型，也无法从混合存储类型中获益。 每个 [pool](/zh/glossary/#term-pool) 都必须使用相同类型的磁盘（NVMe、SSD）
>
> 例如，部署一个仅由 NVMe 磁盘组成的 pool。 如果你在其中混用 SSD 或 HDD，MinIO 会将这些磁盘与 NVMe 磁盘一视同仁。 这可能导致性能问题，因为某些磁盘的读写特性不同或更差，无法以与 NVMe 磁盘相同 的速率响应。

**使用一致的磁盘容量**

> MinIO 会将每块磁盘的可用容量限制为 pool 中最小磁盘的容量。
>
> 例如，部署一个由相同数量、容量均为 `7.68TiB` 的 NVMe 磁盘组成的 pool。 如果其中有一块磁盘容量为 `3.84TiB`，MinIO 会将 pool 中所有磁盘都视为只有 该较小容量。

**配置顺序编号的磁盘挂载**

> MinIO 在创建新的 服务器池 时使用 Go 扩展表示法 `{x...y}` 表示顺序连续的 磁盘序列，其中 服务器池 中所有节点都挂载了完全相同的一组磁盘。 最好将磁盘挂载路径也配置成顺序序列，以便支持这种表示法。 例如，可按 `/mnt/drive-n` 的模式挂载磁盘，其中 `n` 从 `1` 开始，并随每块 磁盘按 `1` 递增。

**在重启后保持磁盘挂载与映射一致**

> 使用 `/etc/fstab` 确保节点重启前后磁盘到挂载点的映射保持一致。
>
> 非 Linux 操作系统应使用等效的磁盘挂载管理工具。

> [!NOTE]
> **磁盘独占访问**
>
> MinIO **要求** 对用于对象存储的磁盘或卷拥有 *独占* 访问权限。 任何其他进程、软件、脚本或人员都不应直接对提供给 MinIO 的磁盘或卷， 或 MinIO 在其上放置的对象或文件执行 *任何* 操作。
>
> 除非得到 MinIO Engineering 的明确指示，否则不要使用脚本或工具直接修改、 删除或移动这些磁盘上的任何数据分片、校验分片或元数据文件，包括在磁盘或节点 之间迁移这些文件。 这类操作极有可能导致大范围损坏和数据丢失，超出 MinIO 的自愈能力。

### 满足纠删码校验的最小驱动器数量 {#id6}

MinIO 要求每个 pool 都满足部署的 [纠删码](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) 设置。 具体来说，新 pool 的拓扑必须为每个 [纠删码集合](/zh/operations/concepts/erasure-coding/#minio-ec-erasure-set) 提供至少 `2 x EC:N` 个驱动器，其中 `EC:N` 是该部署的 [Standard](/zh/reference/minio-server/settings/storage-class/#minio-ec-storage-class) 校验存储类。 这一要求可确保新的 服务器池 满足该部署预期的 <abbr title="Service Level Agreement">SLA</abbr>。

你可以使用 [MinIO Erasure Code Calculator](https://min.io/product/erasure-code-calculator?ref=docs) 检查新 pool 的 **Erasure Code Stripe Size (K+M)**。 如果列出的最大值至少为 `2 x EC:N`，则该 pool 支持部署当前的纠删码校验设置。

### 时间同步 {#id7}

多节点系统必须保持时间和日期同步，才能维持稳定的节点间操作与交互。 请确保所有节点都定期同步到同一时间服务器。 不同操作系统可采用不同方式同步时间和日期，例如 `ntp`、`timedatectl` 或 `timesyncd`。

请查阅所用操作系统的文档，了解如何在各节点之间建立并维护准确且一致的系统时钟。

### 先备份集群设置 {#id8}

在开始扩容前，使用 [`mc admin cluster bucket export`](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-export/#command-mc.admin.cluster.bucket.export) 和 [`mc admin cluster iam export`](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-export/#command-mc.admin.cluster.iam.export) 命令分别为存储桶元数据和 IAM 配置创建快照。 必要时，你可以使用这些快照恢复 [存储桶](/zh/reference/minio-mc-admin/mc-admin-cluster-bucket-import/#minio-mc-admin-cluster-bucket-import) 和 [IAM](/zh/reference/minio-mc-admin/mc-admin-cluster-iam-import/#minio-mc-admin-cluster-iam-import) 设置，以从用户错误或流程错误中恢复。

## 注意事项 {#id9}

<a id="id10" data-td-print-local></a>

### 写入文件 {#minio-writing-files}

SILO 不会因增加新池而自动重平衡已有对象。需要为新对象选择池时，按各可用池的剩余容量加权随机选择；剩余容量越多，被选中的概率越高，并非每次都写入空闲空间最多的池。

用于计算某个 pool 被选中执行写操作概率的公式如下：

\(FreeSpaceOnPoolA / FreeSpaceOnAllPools\)

假设有一个由三个 pool 组成的部署，总空闲空间为 10 TiB，分布如下：

- Pool A 有 3 TiB 空闲空间
- Pool B 有 2 TiB 空闲空间
- Pool C 有 5 TiB 空闲空间

MinIO 计算各 pool 被用于写入操作的概率如下：

- Pool A：30% (\(3TiB / 10TiB\))
- Pool B：20% (\(2TiB / 10TiB\))
- Pool C：50% (\(5TiB / 10TiB\))

除空闲空间计算外，如果某次写入（含校验）会导致驱动器使用率超过 99%，或已知剩余 inode 数量低于 1000，MinIO 也不会写入该 pool。

如有需要，你可以使用 [`mc admin rebalance`](/zh/reference/minio-mc-admin/mc-admin-rebalance/#command-mc.admin.rebalance) 手动启动重平衡过程。 有关重平衡工作方式的更多信息，请参阅 [跨部署管理对象](/zh/operations/concepts/#minio-rebalance)。

同样地，MinIO 不会向正在退役中的 pool 执行写入。

### 扩容需要协调重启 {#id11}

新增 服务器池 需要在大致同一时间重启部署中的 *所有* MinIO server 进程。

扩容需要协调重启全部 SILO 服务端，使它们使用一致的池配置。全量重启期间服务会暂时不可用，正在进行的请求可能失败；请安排维护窗口，并让客户端按操作语义重试和核验结果。重启不构成“无中断”保证。

**不要** 执行“滚动”重启（例如一次只重启一个节点）。

### 基于容量的规划 {#id12}

MinIO 建议预先规划足以存放 **至少** 2 年数据的存储容量，并在使用率达到 70% 之前完成准备。 如果过于频繁地执行 [服务器池 扩容](#expand-minio-distributed)，或按“just-in-time”方式扩容，通常意味着架构或规划存在问题。

例如，假设某套应用每年预计至少产生 100 TiB 数据，并计划在 3 年后再扩容。 初始 服务器池 为该部署提供了约 500 TiB 的可用存储，使集群能够在安全满足 70% 阈值的同时，为数据增长保留一定缓冲。 理想情况下，新 服务器池 **至少** 也应提供 500 TiB 的额外存储，以便在下次扩容前维持类似的生命周期。

由于 MinIO [纠删码](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) 需要预留部分存储用于校验，因此总 **原始** 存储容量必须高于计划中的 **可用** 容量。 建议使用 MinIO [纠删码计算器](https://min.io/product/erasure-code-calculator)，围绕具体纠删码设置进行容量规划。

### 推荐的操作系统 {#id13}

本教程默认所有运行 MinIO 的主机都使用 [推荐的 Linux 操作系统](/zh/operations/deployments/baremetal/#minio-installation-platform-support)。

部署中的所有主机都应采用一致的 [软件配置](/zh/operations/checklists/software/#minio-software-checklists)。

<a id="id14"></a>

## 扩展分布式 MinIO 部署 {#expand-minio-distributed-baremetal}

以下步骤将向现有 MinIO 部署中添加一个 [服务器池](/zh/operations/concepts/#minio-intro-server-pool)。 每个 Pool 都会在保持集群整体 [可用性](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) 的同时，扩展集群的总可用存储容量。

以下所有命令都使用示例值。 请将这些值替换为适用于你部署的实际值。

开始本步骤前，请先阅读 [前提条件](#expand-minio-distributed-prereqs)。

在 [退役旧硬件 pool](/zh/operations/deployments/baremetal-decommission-server-pool/#minio-decommissioning) 之前，请先完成所有计划中的硬件扩容。

### 1) 在新服务器池的每个节点上安装 Silo 二进制 {#id15}

安装与现有 pool **完全相同的公开 Silo 版本**。从[下载与安装](/zh/download/#server)获取 x86-64 或 ARM64 的 RPM、DEB 或独立归档，并在安装前校验摘要。当前 Silo 发布只提供这两种 Linux 架构，因此已删除继承文档中指向未发布 `ppc64le` 与 `s390x` 制品的说明。

{{< tabs group="rpmrhel-debdebianubuntu-tab3" >}}
{{< tab label="RPM（RHEL 系）" value="rpmrhel" >}}
```shell
sudo dnf install ./silo-*.rpm
```
{{< /tab >}}
{{< tab label="DEB（Debian/Ubuntu）" value="debdebianubuntu" >}}
```shell
sudo dpkg -i ./silo_*_amd64.deb
```

ARM64 主机请使用名称中带 `arm64` 的软件包。
{{< /tab >}}
{{< tab label="独立归档" value="tab3" >}}
```shell
tar -xzf silo_*_linux_*.tar.gz
sudo install -m 0755 ./silo /usr/local/bin/silo
silo --version
```
{{< /tab >}}
{{< /tabs >}}

在每个新节点运行 `silo --version` 并与现有 pool 比对；不要把版本不同的节点加入集群。需要升级时，请遵循[`systemctl` 管理的 Silo 升级流程](/zh/operations/deployments/baremetal-upgrade-minio-deployment/#minio-upgrade-systemctl)。

### 2) 添加 TLS/SSL 证书 {#tls-ssl}

对于由 `systemd` 管理的 SILO 部署，建议显式配置证书目录，例如 `/etc/silo/certs`，避免依赖服务账户的主目录。在每个节点放置 `public.crt` 和 `private.key`；需要信任内部 CA 时，将 **CA 公共证书** 放入 `/etc/silo/certs/CAs`。私钥只应允许所需的服务账户读取。

在 `/etc/default/silo` 中设置：

```shell
MINIO_OPTS="--certs-dir /etc/silo/certs --console-address :9001"
```

SILO 软件包使用 `silo` 用户和组，该账户不保证有可用的主目录。确保该账户能够遍历证书目录并读取所需文件。手工安装归档时，先按下一步创建服务账户。有关默认目录的兼容规则和多域名证书，请参阅[网络加密（TLS）](/zh/operations/network-encryption/#minio-tls)与[`--certs-dir`](/zh/reference/minio-server/#minio.server.-certs-dir)。

### 3) 创建 `systemd` 服务文件 {#systemd}

SILO 的 RPM/DEB 软件包安装以下文件，并创建 `silo` 系统用户和组：

- 可执行文件：`/usr/bin/silo`
- 服务单元：`/usr/lib/systemd/system/silo.service`
- 环境文件：`/etc/default/silo`

服务以 `silo:silo` 身份运行。为兼容已有部署，服务单元先读取 `/etc/default/minio`，再读取 `/etc/default/silo`，后者的同名配置覆盖前者；单元还声明与 `minio.service` 冲突，避免两个服务同时访问同一份数据。详见[安装布局](/zh/compatibility/binary/#layout)。

手工安装归档时，创建专用的 `silo` 用户和组，并授予其数据目录和证书目录所需权限。以[当前 SILO 服务单元](https://github.com/pgsty/silo/blob/c3ad836aed0d8a7d23c2e44a5eaa3009d08525e3/silo.service)为模板，将本地单元安装到 `/etc/systemd/system/silo.service`。如果可执行文件安装在 `/usr/local/bin/silo`，同时调整 `AssertFileIsExecutable` 和 `ExecStart`，不要照搬软件包的 `/usr/bin/silo` 路径。

检查实际生效的单元及覆盖配置，修改后重新加载：

```shell
systemctl cat silo.service
sudo systemctl daemon-reload
```

保留既有数据路径；不要因可执行文件或服务改名而重命名对象数据目录。有关版本升级，请参阅[由 systemctl 管理的升级流程](/zh/operations/deployments/baremetal-upgrade-minio-deployment/#minio-upgrade-systemctl)。

### 4) 创建服务环境文件 {#id16}

在 `/etc/default/silo` 创建环境文件。 MinIO 服务会将该文件作为 MinIO *以及* `silo.service` 文件所用全部 [环境变量](/zh/reference/minio-server/settings/#minio-server-environment-variables) 的来源。

以下示例假设：

- 该部署当前只有一个 服务器池，由四台使用连续主机名的 MinIO server 主机构成。

  ```shell
  minio1.example.com   minio3.example.com
  minio2.example.com   minio4.example.com
  ```

  每台主机都有 4 块本地直连驱动器，挂载点连续：

  ```shell
  /mnt/disk1/minio   /mnt/disk3/minio
  /mnt/disk2/minio   /mnt/disk4/minio
  ```

- 新的 服务器池 由八台使用连续主机名的新 MinIO 主机构成：

  ```shell
  minio5.example.com   minio9.example.com
  minio6.example.com   minio10.example.com
  minio7.example.com   minio11.example.com
  minio8.example.com   minio12.example.com
  ```

- 所有主机都具有八块本地直连驱动器，挂载点连续：

  ```shell
  /mnt/disk1/minio  /mnt/disk5/minio
  /mnt/disk2/minio  /mnt/disk6/minio
  /mnt/disk3/minio  /mnt/disk7/minio
  /mnt/disk4/minio  /mnt/disk8/minio
  ```

- 该部署有一个运行在 `https://minio.example.net` 的负载均衡器，用于管理到所有 MinIO 主机的连接。 在此步骤中，负载均衡器不应将请求路由到新主机，但应已准备好所需的配置更新计划。

请根据你的部署拓扑修改示例：

```shell
# Set the hosts and volumes MinIO uses at startup
# The command uses MinIO expansion notation {x...y} to denote a
# sequential series.
#
# The following example starts the MinIO server with two 服务器池s.
#
# The space delimiter indicates a seperate 服务器池
#
# The second set of hostnames and volumes is the newly added pool.
# The pool has sufficient stripe size to meet the existing erasure code
# parity of the deployment (2 x EC:4)
#
# The command includes the port on which the MinIO servers listen for each
# 服务器池.

MINIO_VOLUMES="https://minio{1...4}.example.net:9000/mnt/disk{1...4}/minio https://minio{5...12}.example.net:9000/mnt/disk{1...8}/minio"

# Set all MinIO server options
#
# The following explicitly sets the MinIO Console listen address to
# port 9001 on all network interfaces. The default behavior is dynamic
# port selection.

MINIO_OPTS="--certs-dir /etc/silo/certs --console-address :9001"

# Set the root username. This user has unrestricted permissions to
# perform S3 and administrative API operations on any resource in the
# deployment.
#
# Defer to your organizations requirements for superadmin user name.

MINIO_ROOT_USER=minioadmin

# Set the root password
#
# Use a long, random, unique string that meets your organizations
# requirements for passwords.

MINIO_ROOT_PASSWORD=minio-secret-key-CHANGE-ME
```

你可以根据部署需要指定其他 [环境变量](/zh/reference/minio-server/settings/#minio-server-environment-variables) 或 server 命令行选项。 部署中的所有 MinIO 节点都应包含相同且取值一致的环境变量。

### 5) 使用扩展后的配置重启 MinIO 部署 {#id17}

在部署中的每个节点上 **同时** 执行以下命令，以重启 MinIO 服务：

```shell
sudo systemctl restart silo.service
```

Use the following commands to confirm the service is online and functional:

```shell
sudo systemctl status silo.service
journalctl -f -u silo.service
```

MinIO may log an increased number of non-critical warnings while the server processes connect and synchronize. These warnings are typically transient and should resolve as the deployment comes online.

扩容需要协调重启全部 SILO 服务端，使它们使用一致的池配置。全量重启期间服务会暂时不可用，正在进行的请求可能失败；请安排维护窗口，并让客户端按操作语义重试和核验结果。重启不构成“无中断”保证。

**不要** 执行“滚动”重启（例如一次只重启一个节点）。

### 6) 后续步骤 {#id18}

- 更新所有负载均衡器、反向代理或其他网络控制平面，使客户端请求能够路由到 MinIO 分布式部署中的新主机。 虽然 MinIO 会在内部自动管理路由，但由控制平面处理初始连接通常可以减少网络跳数并提升效率。
- 查看 [MinIO Console](/zh/administration/minio-console/#minio-console)，确认更新后的集群拓扑并监控性能。
