---
title: "从 MinIO 迁移到 Silo"
linkTitle: "迁移指南"
description: "单节点迁移案例、一致性备份、容器切换、数据验证与恢复边界。"
url: "/zh/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

从 MinIO 迁移到 Silo 可直接复用现有对象数据卷，无需逐对象导出与重新导入。**普通 S3 应用无需修改代码，管理员只需核对部署配置、权限规则与状态兼容性。**

当前最新发布目标为 **Server 20261018**（升级前请一并核对其[升级要求](/zh/blog/release/silo-20261018/#upgrade)与[十月兼容性增量](/zh/compatibility/server/#october-2026)，尤其是曾启用 `strict` 分片列举的部署）。建议先对照[三档兼容性总览](/zh/compatibility/)中的 [O01–O08](/zh/compatibility/#conditional) 筛选适用条件，再执行本页步骤。RPM/DEB 软件包升级见[原生软件包迁移](/zh/compatibility/binary/)，版本配套关系见[组件矩阵](/zh/compatibility/versions/)。

## 哪些改变 {#scope}

按影响范围从大到小排列：

1. **容器镜像**：`minio/minio`、`quay.io/minio/minio`、`pgsty/minio` 统一替换为 `docker.io/pgsty/silo`。
2. **软件包、systemd 服务与服务端二进制**：`minio` → `silo`。
3. **上游内置服务**：原地自更新（`mc admin update`）与 MinIO 官方 callhome/SUBNET 已禁用；版本升级统一通过软件包、容器镜像或编排系统执行。
4. **默认操作系统服务账号**：`silo`（仅影响全新安装；迁移场景继续使用既有数据目录属主运行）。
5. **默认本地配置目录**：`~/.minio` → `~/.silo`（仅影响全新进程；证书回退顺序见[服务端兼容性](/zh/compatibility/server/#config-dir)，既有 `~/.minio/certs` 仍会被自动识别）。
6. **品牌呈现**：启动横幅、Console 界面、日志措辞与文档链接显示为 Silo。

## 哪些不变 {#unchanged}

- **对象布局、纠删码格式和 `.minio.sys` 元数据目录完全保留**，可直接挂载兼容基线的数据盘（跨版本降级要求见[回滚边界](#rollback)）。
- **既有桶、对象版本、用户、Access Key、IAM 策略、生命周期与加密配置继续生效**。授权判定、复制状态和新增元数据的行为收敛见 [O02](/zh/compatibility/#o02)、[O07](/zh/compatibility/#o07) 及目标版本的[发布说明](/zh/blog/release/silo-20261018/)。
- **常用 S3 API、SigV4 签名、SDK、`mc`/`mcli` 与预签名 URL 接入方式保持不变**；校验和、条件请求和错误码收敛见 [O04](/zh/compatibility/#o04)。
- **网络与挂载**：端点主机名、API 端口 `9000`、Console 端口与卷挂载路径不变。
- **运行参数**：`MINIO_*` 环境变量与既有服务端启动参数不变。
- **管理与监控路径**：`/minio/*` 路由、`x-minio-*` 响应头、`minio_*` Prometheus 指标名不变。
- **策略命名空间标识**：IAM 策略、事件通知与审计日志中的 `arn:minio:*` ARN、`minio:s3` 等服务命名空间保持原拼写，无需因产品改名而替换字符串（权限语义按 [O02](/zh/compatibility/#o02) 核对）。

上述结论适用于[比较基线](/zh/compatibility/#scope)及兼容的纠删码部署。注意：复用数据卷时，新进程启动、后台任务与后续请求会按新版本格式更新持久元数据（如 IAM 撤销记录或桶配置），因此切换前必须先完成一致性备份。

## 单节点生产案例 {#single-node-case}

社区贡献者 Paris Y.（[@yupoet](https://github.com/yupoet)）在 [SILO #228](https://github.com/pgsty/silo/pull/228) 中记录了 **2026-09-26** 的一次单节点生产升级（[原始报告归档](https://github.com/pgsty/silo/blob/fec1e0804a7493f68ba409345da8e90f0f4d5fbb/docs/upgrade/single-node-from-archived-minio.md)）：

| 项目 | 报告范围 |
| --- | --- |
| 源版本 | MinIO `RELEASE.2025-10-15T17-29-55Z` |
| 目标版本 | SILO `RELEASE.2026-09-16T00-00-00Z` |
| 部署拓扑 | Docker Compose，单节点、单盘，`server /data` |
| 身份与集成 | 仅使用 root 凭据；无 IAM 子用户、OIDC、通知目标或反向代理 |
| 数据规模 | 约 5,900 个对象（约 34,000 个底层存储块）；数据卷先后历经 2025-09、2025-10、2026-09 三个版本，累计运行约 15 个月 |
| 验证结果 | 原地挂载既有数据卷启动无报错；业务侧分片上传、解析服务读取、列举与删除检查均通过 |

### 现代单盘存储与旧 FS 模式 {#single-node-storage}

上述案例属于**单节点单盘纠删码部署（`xl-single`）**，而非早年已废弃的旧 `fs` 模式。仅凭启动命令 `server /data` 无法区分盘上格式；迁移前可只读查看数据卷 `.minio.sys/format.json` 中的 `format` 字段（切勿手动修改）。[服务端加载逻辑](https://github.com/pgsty/silo/blob/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c/cmd/format-erasure.go)接受 `xl` 与 `xl-single`，拒绝旧 `fs` 后端。

旧 `fs` 与 `gateway` 模式已于 MinIO `2022-10-29` 版本移除。仍在使用旧模式的部署必须先执行 [FS/Gateway 导出迁移流程](/zh/operations/deployments/baremetal-migrate-fs-gateway/)，不能直接替换镜像。

此外，单节点且仅使用 root 凭据的场景不涉及跨节点二进制校验、`ReadMultiple` 节点间 RPC、子用户密码策略迁移、跨站复制或外部身份源；多节点或启用了 IAM/复制特性的集群请继续核对下文各节。

## Docker 迁移步骤 {#docker}

维护中的官方镜像仓库为：

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

迁移时应指定明确的 `RELEASE.YYYY-MM-DDTHH-MM-SSZ` 版本标签（建议同时记录并固定镜像 digest），不要在生产环境使用滚动的 `latest` 标签。历史仓库 `pgsty/minio` 不会自动跳转到 `pgsty/silo`。

以下流程适用于 Docker Compose 管理的单存储进程。在完成[升级验证](#verification)前请保持业务写入暂停；共享 IAM、外部 etcd 和跨站复制部署需同步执行各自的协调升级流程。

### 1. 记录现有部署并准备恢复方案 {#docker-preflight}

- **记录运行环境**：保存当前源镜像 ID 与 registry digest、CPU 架构、Compose 项目名与服务名、实际挂载的命名卷或宿主机路径、运行 UID/GID、端口映射与启动参数，并在本地或内部镜像库保留旧镜像制品。
- **备份配置与密钥**：保存原 Compose 文件、环境变量与 secret 来源、TLS 证书挂载以及 KMS/加密密钥恢复材料。盘点桶版本控制、Object Lock、服务端加密、生命周期、IAM、复制和外部 etcd 配置，确定适用的验证项。
- **采集代表性对象基线**：升级前记录一批代表性对象（涵盖历史对象、大对象、分片对象与加密对象）的 key、版本 ID、字节大小与独立计算的内容校验和（注意分片或加密对象的 ETag 不是明文 MD5）。
- **预发演练**：在隔离副本上演练目标版本升级与回滚流程，并阻断演练环境向生产 IAM、复制或分层端点发起连接。

以下片段展示标准镜像与原生健康探针写法。**请勿直接覆盖既有 Compose 文件**：务必保留原有的 Compose 项目名、卷声明、运行用户、凭据来源与挂载路径（更改 Compose 项目名或卷名会隐式创建全新的空卷）。

```yaml
services:
  minio:                              # 服务名可保持为 "minio"
    image: docker.io/pgsty/silo:RELEASE.2026-10-18T00-00-00Z
    command: server /data --console-address ":9001"
    environment:                      # 保留既有凭据来源
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio-data:/data              # 保留实际使用的既有数据卷
    healthcheck:
      test: ["CMD", "silo", "healthcheck", "ready"]
      interval: 30s
      timeout: 10s
      start_period: 2m
      retries: 3
volumes:
  minio-data:
```

标准镜像的 entrypoint 脚本会自动将首个参数 `minio` 转换为 `silo`，因此原有的 `command: minio server /data` 可继续工作；但写死 `entrypoint: /usr/bin/minio` 的配置或脚本必须更新。标准镜像内置 `curl` 和带 `mc` 别名的 `mcli`，而 `-distroless` 变体不含 shell 与外部工具，建议统一使用[原生健康检查](/zh/compatibility/feature/healthcheck/)。

### 2. 停止写入并获取一致性备份 {#docker-backup}

在旧容器仍在运行时提前拉取目标镜像，缩短停机窗口：

```bash
docker compose pull minio
```

（此处及下文的 `minio` 代表 Compose 中的存储服务名，请替换为实际服务名。）

先停止业务写入端、定时任务及其他客户端，再停止存储容器，并确保编排器不会在备份期间自动拉起容器：

```bash
docker compose stop minio
```

确认没有任何进程仍在写入数据卷后，**再执行离线卷备份或存储快照**。仅停止业务客户端并不够，因为存储进程的后台扫描、生命周期与恢复任务仍会修改 `.minio.sys` 和对象元数据；必须在存储进程完全停止后打包或快照，才能获得一致性备份。

备份须完整包含数据卷及 `.minio.sys` 目录，保留文件属主、权限与扩展属性，并验证备份可在独立目录正常恢复。**切勿在升级过程中执行 `docker compose down -v`**，该命令会直接删除命名数据卷。

### 3. 启动替换后的存储服务 {#docker-start}

确认旧容器已停止、挂载的是原数据卷，且运行 UID/GID 对数据、证书和密钥具备读写权限后，仅启动存储服务本身（不连带拉起依赖它的业务容器）：

```bash
docker compose up -d --no-deps minio
docker compose logs --tail=200 minio
docker compose exec -T minio silo healthcheck ready
```

切勿让新旧容器同时挂载操作同一数据卷。完成[升级验证](#verification)后再恢复上游业务流量。

### Distroless 变体 {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` 仅包含 `/usr/bin/silo` 二进制，不含 shell、`mc`、`curl` 或兼容转换脚本。其默认 `ENTRYPOINT` 为 `/usr/bin/silo`，因此 `command` 应直接写参数（如 `command: server /data --console-address ":9001"`），前面不要加 `minio` 或 `silo`。

该变体已内置原生 `HEALTHCHECK`。若 Compose 文件中保留了旧的 `curl` 或 `CMD-SHELL` 健康检查，会覆盖镜像默认配置并因缺少 shell/curl 而失败，请将其移除或替换为上文的 `["CMD", "silo", "healthcheck", "ready"]`。默认证书搜索路径为 `/tmp/.silo/certs`；若使用了非默认监听地址或端口，可通过 `MINIO_HEALTHCHECK_URL` 指定探针目标。同一版本的标准镜像与 distroless 镜像共享完全相同的存储格式，可随时切换。

### Kubernetes {#kubernetes}

Kubernetes kubelet 直接通过 Pod spec 中的 `httpGet` 探针检查容器，忽略 Docker 镜像内置的 `HEALTHCHECK`，因此标准镜像与 distroless 镜像在 Kubernetes 下的探针配置完全一致，既有探针无需修改。使用 Helm 升级时，通过 `nameOverride` / `fullnameOverride` 保持 release 名称与 PVC 绑定不变，并在应用前对比 `helm template` 的渲染输出（详见[服务端兼容性 — Helm](/zh/compatibility/server/#helm)）。

### 回滚边界 {#rollback}

对象目录布局兼容并不代表高版本写入的新元数据都能被旧版本识别。**在回滚镜像或二进制之前，必须先确认持久状态是否需要一并恢复：**

- **持久化 IAM 撤销历史**：启用新 IAM 撤销机制的版本不支持滚动降级。升级前须按 [IAM 升级与恢复](/zh/operations/replication/iam-upgrade/)完整备份 IAM 存储与密钥材料（常规 `mc admin cluster iam export` 不包含删除/撤销墓碑记录）。
- **桶配置收敛与密码策略权限**：核对[桶配置删除状态](/zh/blog/design/bucket-metadata-convergence/#rollout)与[密码权限回滚要求](/zh/compatibility/password-permissions/#rollback)。
- **恢复操作**：若升级验收未通过，保持客户端流量阻断，停止新进程，并使用升级前的一致性卷备份、配置文件与镜像 digest 恢复。如果在备份后已产生新的写入、删除或凭据撤销，需在重新开放端点前完成差异核对与补救。

## 单节点迁移的行为检查 {#single-node-behavior}

| 检查域 | 核对要点 |
| --- | --- |
| TLS 握手与证书 | 20260903 与 20260916 更新了 TLS 行为；20260916 移除硬编码椭圆曲线覆盖，恢复 Go 默认后量子混合密钥交换，并在 macOS 上影响自定义 CA 信任方式。请检查入站客户端及出站 OIDC、通知、复制、分层链路（含中间 TLS 解密设备）。见 [Go 1.27 TLS 与 OIDC 发现](/zh/blog/design/go127-tls-oidc-discovery/)。 |
| 条件删除 | 自 20260916 起，单对象 `DeleteObject` 严格执行非空 `If-Match`，ETag 不匹配时返回 `412 PreconditionFailed`（批量 `DeleteObjects` 不包含此语义）。见[条件 DELETE](/zh/blog/design/conditional-delete/)。 |
| 分片上传列举 | 20260916 曾提供可选的 `MINIO_API_MULTIPART_LISTING=strict` 磁盘扫描模式；20261018 已将其撤回并恢复 legacy 内存缓存行为（省略 `max-uploads` 默认 1,000，但默认缓存路径不执行严格分页）。见 [20260916 说明](/zh/blog/release/silo-20260916/#multipart)与 [20261018 升级要求](/zh/blog/release/silo-20261018/#upgrade)。 |
| 反向代理来源地址信任 | 未设置 `MINIO_API_TRUSTED_PROXIES` 时，S3 监听器保留对转发头的历史信任行为。直连部署建议设为 `none`；经过反向代理时，显式配置代理 IP/CIDR 并确保代理覆盖客户端伪造的转发头。Console 与 LDAP STS 遵循各自的信任规则。见[来源地址信任](/zh/compatibility/server/#trusted-proxies)。 |
| 身份与对象状态 | 若部署使用了 IAM 子用户密码策略、服务账号、STS、OIDC、Object Lock 或复制，请按[目标发行版说明](/zh/blog/release/silo-20261018/#upgrade)、[密码权限迁移](/zh/compatibility/password-permissions/)和 [IAM 恢复流程](/zh/operations/replication/iam-upgrade/)逐项核对。 |

## 从 RELEASE.2026-08-06 升级 {#since-20260806}

`RELEASE.2026-08-06T00-00-00Z` 之后的版本收紧了以下曾被 20260806 放行的行为，升级前请逐项核对：

1. **显式删除版本需要 `s3:DeleteObjectVersion`。** 携带 `versionId` 的 `DeleteObject` 与 `DeleteObjects` 条目按 `s3:DeleteObjectVersion` 鉴权（与 AWS S3 一致）。请为需要删除指定版本的主体补充该权限；凡是用 `Deny s3:DeleteObject` 阻止永久删除的策略，必须同步加上 `Deny s3:DeleteObjectVersion`。
2. **启用与禁用账户拆分为独立管理动作。** `admin:EnableUser` / `admin:DisableUser`（以及用户组的对应动作）严格按请求的目标状态鉴权；仅授予其中一项的策略将无法执行反向操作。
3. **新建与更新策略拒绝裸 ARN 前缀**（如 `arn:aws:s3:::`）以及同时包含 `Resource` 与 `NotResource` 的语句。已落盘的存量策略仍可正常加载，但重复下发此类策略的自动化脚本会报错。
4. **旧版数据库通知目标必须提供连接串。** 已启用的旧版（pre-KV）PostgreSQL 或 MySQL 通知目标若缺少 `connection_string` / `dsn_string`，启动时会直接报错退出（错误日志脱敏），而 20260806 在此情况下会静默丢弃所有通知目标。
5. **严格校验 Checksum 请求头。** 未知的 `x-amz-checksum-*` 算法、`CRC64NVME` 与 `COMPOSITE` 组合、以及与创建上传时矛盾的校验和类型断言均返回 `400 BadRequest`。AWS SDK、`minio-go` 与 `mcli` 的默认行为不受影响。
6. **桶级 CORS 独立生效。** 配置了桶级 CORS 的存储桶严格按桶配置响应，`MINIO_API_CORS_ALLOW_ORIGIN` 仅作为无配置桶的回退默认值。在站点复制集群中，请等所有站点升级后再配置桶级 CORS，否则旧站点会接收但忽略该配置并持续报告不一致。
7. **回滚至 20260806 会丢失桶级 CORS 配置。** 20260806 忽略桶级 CORS 并在重写桶元数据时将其丢弃；若需回滚，请先导出 CORS 配置，待重新升级后恢复。

### 9 月 3 日版本的 Console 回归与修复 {#console-0903}

`RELEASE.2026-09-03T13-18-01Z` 曾停止识别未配置本机代理转发的客户端地址，并忽略了四个 `CONSOLE_WS_MAX_*` WebSocket 连接限额参数。这会影响基于客户端 IP 的 Allow/Deny 策略判定，并导致管理员无法调整单 IP 默认 8 条匿名连接的上限。

`20260916` 及后续版本（[#147](https://github.com/pgsty/silo/issues/147)、[#148](https://github.com/pgsty/silo/issues/148)）已修复此问题：除非显式设置 `MINIO_API_TRUSTED_PROXIES=none`/`off`，内嵌 Console 默认恢复对环回（loopback）TCP 对端的转发头信任，并正常读取环境变量或 `MINIO_CONFIG_ENV_FILE` 中的四个 `CONSOLE_WS_MAX_*` 限额；远程反向代理仍需显式列入 `MINIO_API_TRUSTED_PROXIES`。详见 [Console 设置参考](/zh/reference/minio-server/settings/console/#embedded-compatibility)。

若仍停留在 `20260903`，可将本机代理地址显式加入 `MINIO_API_TRUSTED_PROXIES` 以恢复客户端 IP 识别，但注意这会同时把 9000 端口的 S3 监听器切换为白名单模式，需将该监听器依赖的所有代理地址一并列入。

## 一个集群只运行一种二进制 {#one-binary}

分布式集群节点在 bootstrap 阶段会相互校验二进制校验和。若某个节点与对端节点的二进制不一致，该节点不会报错退出，而是持续停留在 `activating` 状态并输出：

```text
Expected Silo binary checksum: ..., seen: ...
Waiting for at least 1 remote servers with valid configuration to be online
```

该校验适用于任意两个不同二进制之间（无论是 MinIO 与 Silo 混跑，还是不同版本的 Silo 混跑）。因此，**分布式集群切勿逐节点滚动迁移或跨版本滚动升级**，必须一次性全集群切换：先停止所有节点上的旧二进制，再统一启动新二进制（例如在 Compose 中一次性修改所有节点镜像并执行一次 `docker compose up -d`）。回滚同理。

单节点部署不受此限制。同一版本二进制下的日常维护滚动重启则完全正常，重启每个节点前可用 `silo healthcheck --maintenance cluster` 检查是否具备停机冗余（退出码 `0` 表示当前节点可安全下线）。

## 升级验证 {#verification}

在恢复业务流量前，按以下顺序完成验收：

1. **核对实例与卷身份**：确认运行中的版本/镜像 digest、挂载的原数据卷标识、预期桶列表及启动日志（防止误挂载到新建的空卷）。
2. **执行就绪探针**：在容器内运行 `silo healthcheck ready`，或从宿主机探测 HTTP 端点（默认本机 HTTP 监听器可执行 `curl --fail --silent --show-error http://127.0.0.1:9000/minio/health/ready`；TLS 环境请指定正确的主机名与受信任 CA）。
3. **抽样校验存量数据**：通过业务 SDK 或客户端读取升级前记录的代表性历史对象，核对字节内容、大小与独立校验和；按实际启用的功能检查多版本、标签、SSE 加密、Object Lock 保留期与 Legal Hold。
4. **测试写入与列举路径**：在专用测试桶或测试前缀上，使用真实客户端完成普通上传、分片上传合并、列举、回读与删除（切勿删除生产对象做冒烟测试，清理测试数据时注意桶的版本控制与保留期规则）。
5. **验证权限与外部集成**：验证子用户、服务账号、STS/OIDC 以及预期应被拒绝的越权请求；共享 IAM 或跨站复制集群须按 [IAM 升级流程](/zh/operations/replication/iam-upgrade/)逐个检查参与站点。
6. **重启持久性复核**：在流量仍暂停的情况下重启一次存储服务，确认重启后就绪状态、历史对象读取与签名请求均正常，再正式恢复上游业务流量。

若发现历史元数据或对象访问异常，请保留错误日志与对象标识并在隔离副本上排查；迁移观察窗口内建议暂缓写入非必需的新特性状态，以便随时按[回滚边界](#rollback)安全恢复。
