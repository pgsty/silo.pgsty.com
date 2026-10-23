---
title: "从 MinIO 迁移到 Silo"
linkTitle: "迁移指南"
description: "单节点迁移案例、一致性备份、容器切换、数据验证与恢复边界。"
url: "/zh/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

**版本范围，核对日期 2026-10-23：** Server 20261018 是当前已发布的目标版本。请检查其[升级要求](/zh/blog/release/silo-20261018/#upgrade)与[兼容性增量](/zh/compatibility/server/#october-2026)，尤其是旧 strict 分片用户。下文社区案例验证的是 Server 20260916，不能据此宣称 20261018 或更晚构建已通过生产验收。

从 MinIO 迁移到 Silo，通常可以复用现有对象数据和卷，无需逐对象导出、重新导入。**普通 S3 应用通常不改代码，管理员仍需检查部署、权限与状态兼容性。** 先用[三档兼容性总览](/zh/compatibility/)中的 [O01–O08](/zh/compatibility/#conditional) 筛选适用条件，再执行本页步骤。RPM/DEB 安装见[原生软件包迁移](/zh/compatibility/binary/)，各版本要求见[组件矩阵](/zh/compatibility/versions/)。

## 哪些改变 {#scope}

按重要性从大到小：

1. **容器镜像**：`minio/minio`、`quay.io/minio/minio`、`pgsty/minio` 统一替换为 `docker.io/pgsty/silo`。
2. **软件包、systemd 服务与服务端二进制**：`minio` → `silo`。
3. **上游服务**：原地更新器与 MinIO 官方 callhome/SUBNET 被禁用；升级通过软件包、镜像或编排系统进行。
4. **默认操作系统服务账号**：`silo`——仅影响全新安装；迁移场景继续以数据现属主运行。
5. **默认本地配置目录**：`~/.minio` → `~/.silo`（仅影响全新进程；证书回退顺序见[服务端兼容性](/zh/compatibility/server/#config-dir)——既有的 `~/.minio/certs` 仍会被识别）。
6. **品牌呈现**：启动横幅、Console 外观、日志措辞与产品链接显示 Silo。

## 哪些不变 {#unchanged}

- **对象布局、纠删码格式和 `.minio.sys` 目录保留，可以复用兼容基线的数据盘。** 这不等于任意版本都能双向降级，见[回滚边界](#rollback)。
- 既有桶、对象版本、用户、Access Key、策略、生命周期与加密配置继续使用；授权判定、复制状态和新增元数据的例外见 [O02](/zh/compatibility/#o02)、[O07](/zh/compatibility/#o07)，具体以目标版本的[发布说明](/zh/blog/release/silo-20261018/)为准。
- 常用 S3 API、SigV4、SDK、`mc`/`mcli` 与预签名 URL 接入方式延续上游；校验、条件请求和错误行为变化见 [O04](/zh/compatibility/#o04)。
- 端点主机名、API 端口 `9000`、Console 端口、卷挂载。
- `MINIO_*` 环境变量与既有服务端参数。
- `/minio/*` 路由、`x-minio-*` 头、`minio_*` 指标。
- 策略命名空间标识：IAM 策略、通知与审计事件中的 `arn:minio:*` ARN、`minio:s3` 等服务命名空间保持原拼写，无需因产品改名而替换这些字符串；权限语义仍按 [O02](/zh/compatibility/#o02) 检查。

上述结论面向[比较基线](/zh/compatibility/#scope)与兼容的纠删码部署。若 MinIO 版本较旧，或仍使用历史 filesystem/gateway 模式，应先确认对应版本和部署模式的迁移路径，再在预发环境验证。

复用数据卷不代表元数据不会改变。启动、后台任务与后续请求都可能更新持久状态；保留名称和对象布局，不能证明元数据完全不重写，也不能证明逆向降级安全。SILO 对上游保持尽最大努力兼容；正式支持的产品组合是 SILO、SILO Console、mcli 与 silo-pkg。

## 单节点生产案例 {#single-node-case}

Paris Y.（[@yupoet](https://github.com/yupoet)）在 [SILO #228](https://github.com/pgsty/silo/pull/228) 中报告了 **2026-09-26** 的一次生产升级。[原始提交](https://github.com/pgsty/silo/blob/fec1e0804a7493f68ba409345da8e90f0f4d5fbb/docs/upgrade/single-node-from-archived-minio.md)保留为历史记录；其中较宽泛的结论，以本页校准后的术语和操作要求为准。

| 项目 | 贡献者报告的范围 |
| --- | --- |
| 源版本 | MinIO `RELEASE.2025-10-15T17-29-55Z` |
| 目标版本 | SILO `RELEASE.2026-09-16T00-00-00Z` |
| 部署方式 | Docker Compose，单节点、单盘，`server /data` |
| 身份与集成 | 仅使用 root 凭据；没有 IAM 子用户、OIDC、通知目标或反向代理 |
| 数据 | 约 5,900 个对象、34,000 个作者所称的存储块；数据卷具有约 15 个月的历史 |
| 观察结果 | 既有卷打开时未报告错误；分片上传、解析服务读取、列举与删除等应用检查通过 |
| 升级历史 | 据报告，同一个卷依次由 2025-09、2025-10、2026-09 的构建打开 |

15 个月指数据卷跨版本的历史，并非在 2025 年 10 月版本上运行了 15 个月。存储块数量也不等于经审计的 S3 对象数或版本数。原提交没有提供镜像 digest、全量对象/版本读取清单、校验和比对或逆向降级结果。这些观察支持该环境下的一次正向升级成功，不能证明所有历史对象都已检查。该报告未附维护者独立复现的记录。

### 现代单盘存储与旧 FS 模式 {#single-node-storage}

对于报告中的版本，这是**单节点单盘的纠删码部署**，通常使用 `xl-single`；称为旧“FS mode”并不准确。迁移前只读检查实际数据卷的 `.minio.sys/format.json`，不要修改它。[20260916 的加载代码](https://github.com/pgsty/silo/blob/2a4d51406b7ed87af5fe6fe0f801f3290f96eb3c/cmd/format-erasure.go)接受 `xl` 与 `xl-single`，拒绝旧 `fs` 后端。仅凭启动命令 `server /data` 不能确定盘上格式。

旧 FS 与 gateway 模式已在 MinIO 2022-10-29 移除。这些部署须执行单独的 [FS/gateway 迁移流程](/zh/operations/deployments/baremetal-migrate-fs-gateway/)，不能对旧卷直接换镜像。单盘存储也没有盘级校验冗余。

单个进程不会遇到跨节点的二进制一致性检查，也不依赖已移除的私有 `ReadMultiple` 对端调用。仅使用 root 凭据可避开特定的子用户密码权限迁移，但 S3 请求仍受校验、Object Lock 和其他版本变化影响。不要将这个案例推广到共享 IAM、复制、外部身份源或分布式集群。

## Docker 迁移 {#docker}

对于兼容的部署，维护中的镜像仓库为：

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

选择准确的已发布 `RELEASE.YYYY-MM-DDTHH-MM-SSZ` 标签，最好记录并使用核验后的 digest。受控迁移不要使用滚动的 `latest`。标准镜像与 `-distroless` 镜像的启动和探针环境不同。旧 `pgsty/minio` 是历史分发仓库，不会自动跳转到 `pgsty/silo`。

以下顺序适用于由 Compose 管理的单个存储进程。在[验证](#verification)通过前，保持应用流量暂停。共享 IAM、外部状态和复制部署还须执行各自的协调升级流程。

### 1. 记录部署并准备恢复方案 {#docker-preflight}

- 记录实际源镜像 ID、可用的 registry digest、架构、Compose 项目与服务名、解析后的卷名或绑定挂载路径、运行 UID/GID、端口和服务端参数。在本地或可访问的归档中保存旧镜像；仅有标签不能作为恢复制品。
- 安全保存原 Compose 配置、环境变量与 secret 来源、证书挂载，以及所需 KMS/密钥恢复材料。盘点版本控制、Object Lock、加密、生命周期、IAM、复制和外部 etcd，确定适用检查项。只备份数据目录，不会包含外部服务或全部密钥。
- 升级前记录有代表性的既有对象 key、版本 ID、大小和独立内容校验和。按实际使用情况覆盖旧对象、大对象、分片对象与加密对象。对象 ETag 不一定是内容的 MD5。
- 在隔离副本上演练准确的版本组合，阻止副本写入生产 IAM、复制或分层端点。除了正向升级，还要测试恢复过程。

下面的片段展示标准镜像和原生探针，**不能用它直接替换既有 Compose 文件**：保留真实的项目标识、卷声明、运行用户、secret 来源与挂载。改变 Compose 项目名或卷名，可能悄悄选择一个新的空卷。

```yaml
services:
  minio:                              # 服务名可继续为 "minio"
    image: docker.io/pgsty/silo:RELEASE.2026-10-18T00-00-00Z
    command: server /data --console-address ":9001"
    environment:                      # 保留既有凭据来源
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio-data:/data              # 保留实际使用的既有卷
    healthcheck:
      test: ["CMD", "silo", "healthcheck", "ready"]
      interval: 30s
      timeout: 10s
      start_period: 2m
      retries: 3
volumes:
  minio-data:
```

示例镜像是当前已发布、可供规划的目标版本，不代表贡献者已测试该版本。只替换为已针对自身部署选定并验证的准确标签或 digest。

标准镜像的 entrypoint 会将第一个参数 `minio` 翻译为 `silo`，所以 `command: minio server /data` 继续可用。写死的 `entrypoint: /usr/bin/minio`，以及调用该路径的 shell 命令或脚本都需要调整。20260916 与 20261018 的标准镜像包含 curl 和带 `mc` 别名的 mcli；distroless 变体不包含这些工具。为两种镜像编写探针时，优先使用[原生健康检查](/zh/compatibility/feature/healthcheck/)。

### 2. 停止写入并取得一致性备份 {#docker-backup}

保存原配置和旧镜像后，准备目标 Compose 配置，并在旧进程仍可服务时提前拉取目标镜像：

```bash
docker compose pull minio
```

此处及下文的 `minio` 是存储服务示例名；实际执行时使用原有服务名。

停止应用写入方、定时任务及其他客户端，再停止存储进程，确保编排器不会在备份期间重新启动它：

```bash
docker compose stop minio
```

确认没有其他进程写入该卷，**然后**执行离线卷备份或一致性快照。对持续变化的数据目录直接打 tar 包，不是一致性备份。只停应用也不够，存储后台任务仍可能改变状态；在线快照需要单独验证过的一致性流程。

备份应包含整个卷及 `.minio.sys`，保留属主、权限与必要的文件系统属性。保存预检阶段记录的配套部署配置和密钥材料，并验证备份可以恢复到独立位置。不要将 `docker compose down -v` 用作升级步骤，它会删除命名数据卷。

### 3. 只启动替换后的存储进程 {#docker-start}

确认旧进程已经停止、选中的确实是原数据卷，且目标进程可按配置的 UID/GID 访问数据、证书和密钥。启动存储服务，不连带启动其依赖服务：

```bash
docker compose up -d --no-deps minio
docker compose logs --tail=200 minio
docker compose exec -T minio silo healthcheck ready
```

不要让新旧容器同时操作同一个卷。保持应用暂停，完成[验证](#verification)后再恢复流量。启动成功不代表每个对象都已读取；启动与后台处理本身可能已经修改了持久元数据。

### Distroless 变体 {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` 只包含 `silo` 二进制：没有 shell、`mc`、curl，也没有转换旧命令的 shell entrypoint。它的入口为 `/usr/bin/silo`，应使用 `command: server /data --console-address ":9001"`，前面不加 `minio` 或 `silo`。以任意 UID 运行时，既有数据、证书和密钥仍须具有适当权限。

镜像内置原生 `HEALTHCHECK`。已有 Compose 健康检查会覆盖镜像默认值，因此应移除继承的 curl/`CMD-SHELL` 探针，或替换为上面的 exec 形式原生探针。`depends_on: condition: service_healthy` 使用该健康状态；恢复应用流量前仍须验证实际数据路径。

同一版本的标准与 distroless 变体使用相同存储格式；变体切换不能证明跨版本降级安全。确保选定的证书路径可访问，默认路径为 `/tmp/.silo/certs`；如果监听地址需要，设置 `MINIO_HEALTHCHECK_URL`。镜像内没有 shell，调试使用外部工具。

### Kubernetes {#kubernetes}

kubelet 探针是 pod spec 中的 `httpGet` 请求；Docker `HEALTHCHECK` 被忽略，两个镜像变体的探测方式完全相同，现有探针配置继续可用。Helm 部署用 `nameOverride`/`fullnameOverride` 保持 release 身份，应用前比对 `helm template` 输出（[细节](/zh/compatibility/server/#helm)）。

### 回滚 {#rollback}

**先确认状态可恢复，再切回旧版本。** 对象布局兼容不保证旧程序理解新增的桶配置、IAM 修订或删除历史，也不保证回滚后权限和复制状态相同。

升级前保存原镜像摘要、部署配置及匹配的恢复点，并在隔离环境验证确切版本组合。涉及新的 IAM 撤销机制时，必须按 [IAM 升级与恢复](/zh/operations/replication/iam-upgrade/)保留完整 IAM 存储及密钥材料；普通管理导出不包含删除历史。还需检查[桶配置删除状态](/zh/blog/design/bucket-metadata-convergence/#rollout)与[密码权限](/zh/compatibility/password-permissions/#rollback)。

只有对应升级说明明确允许、且恢复验证通过时，才执行既定的镜像或二进制回退。包含持久 IAM 撤销的版本不支持滚动降级。不要让新旧节点同时操作同一份数据；恢复旧快照还需处理备份之后的数据和授权变更。

社区案例**没有执行逆向降级**。三个构建依次正向打开同一个卷，不能证明最旧构建理解最新构建写入的状态。若验收失败，继续阻断客户端、停止新进程，并执行已演练的恢复方案。恢复必须覆盖匹配的数据、配置和密钥；重新开放恢复端点前，还要处理备份之后的写入、删除与凭据撤销。只换镜像不是通用恢复流程。

## 单节点迁移的行为检查 {#single-node-behavior}

| 范围 | 检查内容 |
| --- | --- |
| TLS | 20260903 与 20260916 改变了 TLS 握手行为；20260916 移除显式曲线覆盖，改用 Go 默认值。检查入站客户端，以及适用的出站身份源、通知、复制和分层连接，包括链路上的 TLS 检查设备。见 [TLS 兼容性](/zh/blog/design/tls-parameter-pinning/)。 |
| 条件删除 | 从 20260916 起，单对象 `DeleteObject` 的非空 `If-Match` 会被执行，ETag 不匹配返回 `412`。不要将此保证推广到批量删除。见[条件 DELETE](/zh/blog/design/conditional-delete/)。 |
| 分片列举 | 在 20260916 中，省略 `max-uploads` 时默认值为 1,000，strict 分页器也将页大小限制为 1,000。这不是统一的响应条数上限：默认 legacy 缓存路径忽略分页，可能返回更多条目。可选 strict 模式属于该历史版本，20261018 已将其移除。空列表或成功 abort 都不能证明所有物理上传已清理。见 [20260916 行为](/zh/blog/release/silo-20260916/#multipart)及 [20261018 要求](/zh/blog/release/silo-20261018/#upgrade)。 |
| 代理信任 | 未设置 `MINIO_API_TRUSTED_PROXIES` 时，S3 监听器保留对转发来源地址头的历史信任行为。客户端直连时可考虑 `none`；有代理时，显式列出其实际 IP/CIDR，并确保代理覆盖客户端传入的相关头。Console 与 LDAP STS 有各自的信任规则。见[来源地址信任](/zh/compatibility/server/#trusted-proxies)。 |
| 身份与对象状态 | 仅使用 root 的案例没有验证子用户密码策略、服务账号、STS、OIDC、Object Lock 或复制。按[目标发行版](/zh/blog/release/silo-20261018/#upgrade)、[密码权限迁移](/zh/compatibility/password-permissions/)和 [IAM 恢复](/zh/operations/replication/iam-upgrade/)选择适用检查项。 |

## 从 RELEASE.2026-08-06 升级 {#since-20260806}

`RELEASE.2026-08-06T00-00-00Z` 之后的版本收紧了若干 20260806 曾接受的行为。升级前请逐项核对：

1. **显式删除版本需要 `s3:DeleteObjectVersion`。** 带 `versionId` 的 `DeleteObject` 与 `DeleteObjects` 条目按 `s3:DeleteObjectVersion` 授权，与 AWS 一致。给需要删除特定版本的主体授予该权限；凡是用 `Deny s3:DeleteObject` 来阻止永久删除的策略，都要同时加上 `Deny s3:DeleteObjectVersion`。
2. **启用与禁用是两个独立的管理动作。** `admin:EnableUser` / `admin:DisableUser` 及组的对应动作按请求的目标状态检查；只授予其中一个的策略会失去另一个操作。
3. **新建与更新的策略拒绝裸 ARN 前缀**（如 `arn:aws:s3:::`）以及同时含 `Resource` 与 `NotResource` 的语句。已存储的策略照常加载；重复下发此类策略的自动化会失败。
4. **旧版数据库通知目标必须有连接串。** 已启用的 pre-KV PostgreSQL 或 MySQL 目标若缺少 `connection_string` / `dsn_string`，启动会以不含凭据的错误停止；20260806 在同样情况下会静默丢掉全部通知目标。
5. **校验和请求会被校验。** 未知的 `x-amz-checksum-*` 算法、`CRC64NVME` 与 `COMPOSITE` 的组合、与上传矛盾的校验和类型断言都返回 `400`。AWS SDK、`minio-go` 与 `mcli` 的默认行为不受影响。
6. **桶级 CORS 真正生效。** 设置了自身 CORS 配置的桶只按该配置响应；`MINIO_API_CORS_ALLOW_ORIGIN` 只作用于没有配置的桶。在站点复制组里，等所有站点都运行新版本后再配置桶级 CORS：旧对端会接受但忽略该配置，并持续报告 CORS 不一致。
7. **回滚会丢失新 CORS 配置。** 20260806 忽略桶级 CORS，并会在重写桶元数据时丢弃它；回滚前导出，重新升级后再恢复。其他状态按[回滚边界](#rollback)单独检查。

### 9 月 3 日版本的 Console 回归 {#console-0903}

`RELEASE.2026-09-03T13-18-01Z` 不再识别未配置的本机代理转发的客户端地址，同时清除了四个 `CONSOLE_WS_MAX_*` 连接配置。这会改变 IP Allow/Deny 策略的判断，并使管理员无法提高每个地址默认八条匿名连接的限额。

包含修复的构建会恢复内嵌 Console 对环回 TCP 对端的信任，除非设置了 `MINIO_API_TRUSTED_PROXIES=none`/`off`；同时保留环境变量或 `MINIO_CONFIG_ENV_FILE` 中的四个限额配置。远程代理仍需显式配置 IP/CIDR 列表。独立 Console 的默认行为、转发链信任规则和连接预算保持不变，非法配置会在启动时报错。策略表与配置约束见 [Console 设置](/zh/reference/minio-server/settings/console/#embedded-compatibility)。发布进展见 [#147](https://github.com/pgsty/silo/issues/147) 和 [#148](https://github.com/pgsty/silo/issues/148)；0903 镜像尚不包含这些修复。

在 0903 上，显式将本机代理对端加入 `MINIO_API_TRUSTED_PROXIES` 可恢复客户端地址识别，但也会将 9000 端口的 S3 监听器切换到列表模式，需要同时列出它所需的其他代理。自定义 WebSocket 限额则需要包含修复的 Server 构建或独立 Console。

## 一个集群只运行一种二进制 {#one-binary}

分布式节点在 bootstrap 时相互校验二进制。起进不同二进制对端之间的节点不会报错退出，而是无限停在 `activating`，日志记录：

```text
Expected Silo binary checksum: ..., seen: ...
Waiting for at least 1 remote servers with valid configuration to be online
```

该约束适用于任意两个不同的二进制：MinIO 与 Silo 之间如此，两个不同版本的 Silo 之间同样如此。因此不要逐节点迁移——将来升级也一样。所有节点一次切换：全部停旧二进制，再全部起新二进制（Compose 中一次编辑改完所有节点的镜像，执行一次 `docker compose up -d`）。单机部署不受影响。回滚同理。同一二进制的滚动重启正常可用，重启前用 `silo healthcheck --maintenance cluster` 把关（退出码 `0` = 停掉本节点安全）。

## 验证 {#verification}

在应用流量仍暂停时验证替换后的服务：

1. 确认实际运行版本/镜像、原数据卷标识、预期桶和启动日志。挂载了新空卷的服务也可能通过健康探针。
2. 在容器内运行 `silo healthcheck ready`，或从宿主机探测正确的已发布 HTTP 端点。对于默认的本机 HTTP 监听器，完整命令为 `curl --fail --silent --show-error http://127.0.0.1:9000/minio/health/ready`；TLS 使用正确主机名和受信任 CA。探针成功只是初步信号，不能证明 IAM 就绪或数据完整。
3. 通过既有应用/SDK 读取预先记录的历史对象，比对内容、大小与独立校验和；按实际使用情况检查版本、标签、加密、保留期和 legal hold。全卷保证需要明确的清单，并读取每个需要验证的对象/版本；列表计数和少数探测对象无法证明这一点。
4. 在获准使用的测试桶/key 上，通过真实客户端执行上传、回读与删除，并覆盖分片完成和应用的列举行为。清理测试数据时遵守版本控制和保留规则，不要删除生产对象来做冒烟测试。
5. 验证相关身份与集成，包括应该被拒绝的请求。共享 IAM 或复制部署须按 [IAM 升级流程](/zh/operations/replication/iam-upgrade/)检查每个参与端点。
6. 在流量仍暂停时重启存储服务一次，重新检查就绪状态及带签名的历史对象/探测请求。验收通过后再恢复应用，并记录版本、覆盖范围、结果和未解决的失败。

若历史元数据或对象被拒绝，保留错误及受影响对象的标识，在副本上调查。安装 SILO 不会修复全部历史不一致；没有完整审计时，只应报告“这些检查中未观察到拒绝”。迁移窗口内避免引入可选的新状态，恢复仍须满足[回滚要求](#rollback)。
