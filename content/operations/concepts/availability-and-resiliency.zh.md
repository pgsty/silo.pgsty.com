---
title: "可用性与韧性"
url: "/zh/operations/concepts/availability-and-resiliency/"
description: "Silo 生产环境的可用性与韧性"
weight: 20
upstream_link: https://github.com/minio/docs/blob/35f2bb81280a3573c64947e8bd979e2c7026d2dd/source/operations/concepts/availability-and-resiliency.rst
upstream_modified: true
---

<a id="minio-availability-resiliency"></a>
<a id="id1"></a>

本页从生产视角概述 MinIO 在可用性与韧性方面的设计和特性。

> [!NOTE]
> **说明**
>
> 本页内容旨在尽力帮助你理解 MinIO 在可用性与韧性方面的预期设计和理念。 它不能替代 [MinIO SUBNET](https://min.io/pricing?jmp=docs) 的能力。使用 [MinIO SUBNET](https://min.io/pricing?jmp=docs) 可以在规划 MinIO 部署时与 MinIO Engineering 协同。
>
> 社区用户可以通过 [MinIO Community Slack](https://slack.min.io) 寻求支持。 社区支持仅为 best-effort，不提供关于响应时间的 SLA。

## 分布式 MinIO 部署 {#minio}

**MinIO 将 [纠删码](/zh/operations/concepts/erasure-coding/#minio-erasure-coding) 作为在驱动器级或节点级故障期间提供可用性与韧性的核心组件。**

> MinIO 会将每个对象拆分为数据分片和 [校验](/zh/operations/concepts/erasure-coding/#minio-ec-parity) 分片，并将这些分片分布到单个 [纠删码集合](/zh/operations/concepts/erasure-coding/#minio-ec-erasure-set) 中。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding.svg" alt="纠删码对象被拆分为 12 个数据分片和 4 个校验分片的示意图" />
>   <figcaption>这个小型单节点部署在一个纠删码集合中拥有 16 块驱动器。
> 假设使用默认 <a href="/zh/operations/concepts/erasure-coding/#minio-ec-parity">校验</a> <code>EC:4</code>，MinIO 会将对象拆分为 4 个校验分片和 12 个数据分片。
> MinIO 会将这些分片均匀分布到纠删码集合中的各块驱动器上。</figcaption>
> </figure>

**MinIO 使用确定性算法为给定对象选择纠删码集合。**

> 对于每个唯一对象命名空间 `BUCKET/PREFIX/[PREFIX/...]/OBJECT.EXTENSION`，MinIO 在读写操作中始终会选择相同的纠删码集合。 这也包括同一对象的所有 [版本](/zh/administration/object-management/object-versioning/#minio-bucket-versioning)。
>
> <figure>
>   <img src="/images/availability/availability-erasure-set-selection.svg" alt="基于对象命名空间选择纠删码集合的示意图" />
>   <figcaption>MinIO 使用完整对象命名空间来计算目标纠删码集合。</figcaption>
> </figure>

**MinIO 需要满足 [读写仲裁](/zh/operations/concepts/erasure-coding/#minio-read-quorum) 才能对纠删码集合执行读写操作。**

> 对于保存在本地的普通非空对象，设其所在纠删集合有 `N` 块磁盘，对象包含 `M` 个校验分片和 `K=N-M` 个数据分片。通常的读仲裁为 `K`，不是 `M`：使用 `K` 个健康分片即可重建数据，最多容忍 `M` 个分片不可用。访问对象还须满足相应的元数据仲裁。应以对象实际记录的校验配置为准：修改默认校验配置不会改变其既有分片。上述分片数量不涵盖所有元数据和初始化要求；例如，分层对象和删除标记采用不同的元数据仲裁规则，关闭默认校验还可能使元数据读取要求所有磁盘可用。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding-degraded.svg" alt="降级纠删码集合示意图，其中两个校验分片替换了两个数据分片" />
>   <figcaption>该节点有两块驱动器故障。
> MinIO 会自动使用校验分片替换丢失的数据分片，并将重建后的对象返回给请求客户端。</figcaption>
> </figure>
>
> 以 `EC:4` 存储的对象可以容忍所在纠删集合中的 4 个分片不可用；只要剩余分片完好且满足元数据仲裁，仍可读取该对象。

**写仲裁取决于配置的校验值和纠删码集合大小。**

> 当 `M < N/2` 时，写仲裁为 `K=N-M`；当 `M=N/2` 时，写仲裁为 `K+1`。对于新写入，应根据该次写入最终采用的分片布局计算这些值。
>
> 当 `MINIO_STORAGE_CLASS_OPTIMIZE=availability` 时，SILO 可以提高写入降级纠删集合的新对象的校验值，上限为 `floor(N/2)` 个校验分片。这可以增加这些新对象的冗余，但不能保证故障前后的可用性不变，也不能绕过写仲裁。应修复或更换故障磁盘，使集合恢复健康。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding-degraded-write.svg" alt="降级纠删码集合示意图，其中两块驱动器发生故障" />
>   <figcaption>该节点有两块驱动器故障。
> 在该示例中，SILO 将新对象的校验值提高到 <code>EC:6</code>。</figcaption>
> </figure>
>
> 对于上面的 16 盘示例，如果固定采用 `EC:4` 布局，则 `K=12`，写仲裁为 12，可以在 4 盘不可用时仍有足够的在线磁盘。新写入的校验升级可能改变分片布局及其写仲裁；不能将这个示例当成所有 `EC:4` 部署的统一故障上限。

**如果校验值等于纠删码集合驱动器数量的 1/2，则写仲裁等于校验值加 1，以避免因 “split brain” 场景导致数据不一致。**

> 例如，当 `M=N/2`，且网络故障使纠删集合中的两半磁盘相互隔离时，任一半都无法满足 `K+1=N/2+1` 的写仲裁。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding-split-brain.svg" alt="一半驱动器故障的纠删码集合示意图" />
>   <figcaption>该节点有 50% 的驱动器故障。
> 如果校验值为 <code>EC:8</code>，该纠删码集合就无法满足写仲裁，MinIO 会拒绝对此集合的写操作。
> 由于该纠删码集合仍然满足读仲裁，对现有对象的读操作仍可能成功。</figcaption>
> </figure>

**如果对象永久丢失的分片数超过其自身的校验分片数 `M`，就无法从该纠删集合重建该对象的数据。**

> 对于磁盘数为偶数、采用最高校验值（`K=M=N/2`）的集合，失去一半磁盘后，剩余的完好分片可能仍足以读取对象，但磁盘数已不足以向该集合写入。例如，16 盘集合中以 `EC:8` 写入的对象读仲裁为 8，写仲裁为 9；如果永久丢失其中 9 个分片，就无法重建该对象。以较低校验值写入的对象，其故障容忍度也更低。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding-degraded-set.svg" alt="完全降级的纠删码集合示意图" />
>   <figcaption>该纠删码集合永久丢失了超过 4 块磁盘。
> 以 <code>EC:4</code> 存储的对象已无法通过剩余分片重建。</figcaption>
> </figure>
>
> 某些瞬时或临时驱动器故障，例如由存储控制器或连接硬件故障引起的情况，仍可能在该纠删码集合内恢复到正常运行状态。

**MinIO 还会通过在 pool 的每个节点间对纠删码集合驱动器进行对称条带化，进一步降低纠删码集合故障风险。**

> MinIO 会根据节点数和驱动器数自动计算最佳纠删码集合大小，其中最大集合大小为 16。 随后，它会跨 pool 为每个纠删码集合从每个节点选择一块驱动器；如果纠删码集合条带大小大于节点数，则会循环选择。 将集合分散到多个节点可以限制单个节点故障造成的分片损失，但能否继续读写，仍取决于每个受影响的集合是否满足相应仲裁。
>
> <figure>
>   <img src="/images/availability/availability-erasure-sharding-striped.svg" alt="一个由 16 节点、每节点 8 块驱动器组成的集群示意图，包含 8 个 16 驱动器纠删码集合，并在各节点上均匀条带化" />
>   <figcaption>在此 16 x 8 部署中，MinIO 会计算出 8 个纠删码集合，每个集合 16 块驱动器。
> 它会在所有可用节点上为每个纠删码集合分配每节点 1 块驱动器。
> 如果只有 8 个节点，则 MinIO 需要为每个纠删码集合从每个节点选择 2 块驱动器。</figcaption>
> </figure>
>
> 在上述拓扑中，该 pool 具有 8 个跨 16 个节点条带化的 16 驱动器纠删码集合。 每个节点都会为每个纠删码集合分配 1 块驱动器。 虽然丢失一个节点在技术上意味着丢失 8 块驱动器，但每个纠删码集合实际上只会各丢失 1 块驱动器。 这使得即使节点停机，系统仍能保持仲裁。

**同一 pool 中的每个纠删码集合彼此独立。**

> 即使一个纠删码集合完全降级，MinIO 仍可对其他纠删码集合执行读写操作。
>
> <figure>
>   <img src="/images/availability/availability-erasure-set-failure.svg" alt="一个 MinIO 多 pool 部署中某个 pool 内一个纠删码集合故障的示意图" />
>   <figcaption>一个 pool 中有一个降级纠删码集合。
> 虽然 MinIO 已无法对该纠删码集合执行读写操作，但它仍能继续对该 pool 中健康的纠删码集合提供服务。</figcaption>
> </figure>
>
> 不过，丢失的数据仍可能影响依赖 100% 数据可用性假设的工作负载。 此外，每个纠删码集合都与其他集合完全独立，因此你不能使用其他纠删码集合来恢复一个完全降级的纠删码集合中的数据。 你必须使用 [站点](/zh/operations/replication/multi-site-replication/#minio-site-replication-overview) 或 [存储桶](/zh/administration/bucket-replication/#minio-bucket-replication) 复制，创建一个具备 <abbr title="Business Continuity / Disaster Recovery">BC/DR</abbr> 能力的远端部署，用于恢复丢失的数据。

**对于多 pool MinIO 部署，每个 pool 都至少需要有一个纠删码集合保持读写仲裁，才能继续提供操作能力。**

> 如果某个 pool 丢失了全部纠删码集合，MinIO 就无法再判断某次读写操作原本是否应被路由到该 pool。 因此，即使其他 pool 仍然可用，MinIO 也会停止整个部署中的所有 I/O。
>
> <figure>
>   <img src="/images/availability/availability-pool-failure.svg" alt="一个 MinIO 多 pool 部署中某个 pool 故障的示意图" />
>   <figcaption>该部署中的一个 pool 已完全故障。
> MinIO 无法再确定 I/O 应路由到哪个 pool 或纠删码集合。
> 如果继续操作，就可能产生不一致状态，使对象及其版本分布在不同纠删码集合中。
> 因此，MinIO 会暂停部署中的所有 I/O，直到该 pool 恢复。</figcaption>
> </figure>
>
> 要恢复对该部署的访问，管理员必须将该 pool 恢复到正常运行状态。 这可能需要根据故障严重程度执行磁盘格式化、硬件更换或节点更换。 更完整的文档请参阅 [硬件故障恢复](/zh/operations/data-recovery/#minio-restore-hardware-failure)。
>
> 你可以使用复制远端将丢失数据恢复回该部署。 存储在健康 pool 中的所有数据仍会安全保留在磁盘上。

> [!NOTE]
> **磁盘独占访问**
>
> MinIO **要求** 对用于对象存储的磁盘或卷拥有 *独占* 访问权限。 任何其他进程、软件、脚本或人员都不应直接对提供给 MinIO 的磁盘或卷， 或 MinIO 在其上放置的对象或文件执行 *任何* 操作。
>
> 除非得到 MinIO Engineering 的明确指示，否则不要使用脚本或工具直接修改、 删除或移动这些磁盘上的任何数据分片、校验分片或元数据文件，包括在磁盘或节点 之间迁移这些文件。 这类操作极有可能导致大范围损坏和数据丢失，超出 MinIO 的自愈能力。

## 复制型 MinIO 部署 {#id3}

**对于 MinIO 部署中发生的小规模或大规模数据丢失，MinIO 将 [站点复制](/zh/operations/replication/multi-site-replication/#minio-site-replication-overview) 作为保证业务连续性和灾难恢复 (BC/DR) 的主要手段。**

> <figure>
>   <img src="/images/availability/availability-multi-site-setup.svg" alt="初始设置期间的多站点部署示意图" />
>   <figcaption>每个对等站点都部署在独立数据中心，以防范大规模故障或灾难。
> 如果某个数据中心完全离线，客户端可以故障切换到另一个站点。</figcaption>
> </figure>

**MinIO 复制可以在站点因瞬时或持续停机而发生部分或全部数据丢失时，自动 [自愈](/zh/operations/concepts/healing/#minio-concepts-healing) 该站点。**

> <figure>
>   <img src="/images/availability/availability-multi-site-healing.svg" alt="自愈过程中的多站点部署示意图" />
>   <figcaption>Datacenter 2 曾经离线，Site B 需要重新同步。
> 负载均衡器会将操作路由到 Datacenter 1 中的 Site A。
> Site A 会持续将数据复制到 Site B。</figcaption>
> </figure>
>
> 一旦所有数据同步完成，你就可以恢复对该站点的正常连接。 根据复制滞后量、站点间延迟以及整体工作负载的 <abbr title="Input / Output">I/O</abbr> 情况，你可能需要临时停止写操作，让各站点完全追平。
>
> 如果某个对等站点彻底故障，你可以将其从配置中完全移除。 负载均衡器配置也应移除该站点，以避免将客户端请求路由到离线站点。
>
> 然后，你可以在修复原始硬件或完全更换硬件后，通过 [将其重新加入站点复制配置](/zh/operations/replication/multi-site-replication/#minio-expand-site-replication) 来恢复该对等站点。 MinIO 会在持续复制新数据的同时，自动开始重同步已有数据。

**站点在重同步期间仍可通过将 `GET/HEAD` 请求代理到健康对等站点来继续处理操作**

> <figure>
>   <img src="/images/availability/availability-multi-site-proxy.svg" alt="重同步期间的多站点部署示意图" />
>   <figcaption>Site B 不具备所请求的对象，可能是由于复制滞后。
> 它会将 <code>GET</code> 请求代理到 Site A。
> Site A 返回对象后，Site B 再将其返回给请求客户端。</figcaption>
> </figure>
>
> 客户端会收到首个返回所请求对象任意版本的对等站点结果。
>
> `PUT` 和 `DELETE` 操作通过常规复制流程进行同步。 `LIST` 操作不会代理，客户端必须只对健康对等站点发起这类请求。
