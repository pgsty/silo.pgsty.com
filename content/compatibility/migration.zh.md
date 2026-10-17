---
title: "从 MinIO 迁移到 Silo"
linkTitle: "迁移指南"
description: "哪些改变、哪些不变，以及容器部署如何切换。软件包安装见《原生软件包迁移》。"
url: "/zh/compatibility/migration/"
weight: 10
type: docs
icon: fa-solid fa-arrow-right-arrow-left
---

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
- 既有桶、对象版本、用户、Access Key、策略、生命周期与加密配置继续使用；授权判定、复制状态和新增元数据的例外见 [O02](/zh/compatibility/#o02)、[O07](/zh/compatibility/#o07)，具体以目标版本的[发布说明](/zh/blog/release/silo-20260916/)为准。
- 常用 S3 API、SigV4、SDK、`mc`/`mcli` 与预签名 URL 接入方式延续上游；校验、条件请求和错误行为变化见 [O04](/zh/compatibility/#o04)。
- 端点主机名、API 端口 `9000`、Console 端口、卷挂载。
- `MINIO_*` 环境变量与既有服务端参数。
- `/minio/*` 路由、`x-minio-*` 头、`minio_*` 指标。
- 策略命名空间标识：IAM 策略、通知与审计事件中的 `arn:minio:*` ARN、`minio:s3` 等服务命名空间保持原拼写，无需因产品改名而替换这些字符串；权限语义仍按 [O02](/zh/compatibility/#o02) 检查。

上述结论面向[比较基线](/zh/compatibility/#scope)与兼容的纠删码部署。若 MinIO 版本较旧，或仍使用历史 filesystem/gateway 模式，应先确认对应版本和部署模式的迁移路径，再在预发环境验证。

## Docker 迁移 {#docker}

无论当前使用哪个镜像，统一替换为：

```text
docker.io/pgsty/silo:<RELEASE-tag>
```

tag：不可变的 `RELEASE.YYYY-MM-DDTHH-MM-SSZ`（建议钉住）、滚动 `latest`，以及下述 `-distroless` 变体。旧的 `pgsty/minio` 仓库保持已发布状态，冻结在最后一个 tag。

下面的 Compose 示例保留原端口、数据卷与 `MINIO_*` 配置。切换前核对自定义 entrypoint、二进制路径、运行用户、目录权限和探针；不能仅凭镜像名替换就认定迁移完成。

```yaml
services:
  minio:                              # 服务名可继续为 "minio"
    image: docker.io/pgsty/silo:<RELEASE-tag>
    command: server /data --console-address ":9001"
    environment:                      # MINIO_* 不变
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - minio-data:/data              # 同一卷、同一份数据
volumes:
  minio-data:
```

```bash
docker compose pull minio && docker compose up -d minio
```

entrypoint 会翻译旧的第一个参数，继承下来的 `command: minio server /data` 继续可用；写死的 `entrypoint: /usr/bin/minio` 需改为 `/usr/bin/silo`。现有 `mc ready local` 健康检查继续可用，原生替代为 `test: ["CMD", "silo", "healthcheck", "ready"]`（[参考](/zh/compatibility/feature/healthcheck/)）。不要执行 `docker compose down -v`——`-v` 会删除数据卷。

### Distroless 变体 {#distroless}

`pgsty/silo:<RELEASE-tag>-distroless` 只包含 `silo` 二进制：没有 shell、没有 `mc`、没有 `curl`。内置 `HEALTHCHECK`（即原生探针），任意 `--user` 下均可运行：

```bash
docker run -d --name silo \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=admin \
  -e MINIO_ROOT_PASSWORD=change-me-long-password \
  -v silo-data:/data \
  docker.io/pgsty/silo:<RELEASE-tag>-distroless \
  server /data --console-address ":9001"
```

同一部署的 Compose 写法：

```yaml
services:
  silo:
    image: docker.io/pgsty/silo:<RELEASE-tag>-distroless
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: admin
      MINIO_ROOT_PASSWORD: change-me-long-password
    ports: ["9000:9000", "9001:9001"]
    volumes:
      - silo-data:/data
volumes:
  silo-data:
```

`depends_on: condition: service_healthy` 无需配置 `healthcheck:` 即可生效。卷上的数据格式与经典镜像、MinIO 完全一致——几种镜像可在同一份数据上互换使用。TLS 证书挂载到 `/tmp/.silo/certs`。若命令行 flag 改动了监听地址，用 `MINIO_HEALTHCHECK_URL` 指定内置探针的目标。镜像内没有 shell，调试用 `docker debug` / `kubectl debug`。

### Kubernetes {#kubernetes}

kubelet 探针是 pod spec 中的 `httpGet` 请求；Docker `HEALTHCHECK` 被忽略，两个镜像变体的探测方式完全相同，现有探针配置继续可用。Helm 部署用 `nameOverride`/`fullnameOverride` 保持 release 身份，应用前比对 `helm template` 输出（[细节](/zh/compatibility/server/#helm)）。

### 回滚 {#rollback}

**先确认状态可恢复，再切回旧版本。** 对象布局兼容不保证旧程序理解新增的桶配置、IAM 修订或删除历史，也不保证回滚后权限和复制状态相同。

升级前保存原镜像摘要、部署配置及匹配的恢复点，并在隔离环境验证确切版本组合。涉及新的 IAM 撤销机制时，必须按 [IAM 升级与恢复](/zh/operations/replication/iam-upgrade/)保留完整 IAM 存储及密钥材料；普通管理导出不包含删除历史。还需检查[桶配置删除状态](/zh/blog/design/bucket-metadata-convergence/#rollout)与[密码权限](/zh/compatibility/password-permissions/#rollback)。

只有对应升级说明明确允许、且恢复验证通过时，才执行既定的镜像或二进制回退。包含持久 IAM 撤销的版本不支持滚动降级。不要让新旧节点同时操作同一份数据；恢复旧快照还需处理备份之后的数据和授权变更。

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

动手之前，先记录你要离开的制品：正在运行的镜像 digest（或软件包版本与二进制校验和）、unit 状态与启用状态、数据目录属主的 UID/GID。回滚的精度取决于这份记录。

```bash
silo healthcheck ready                   # 本节点在服务；退出码 0/1
silo healthcheck cluster                 # 集群级写 quorum
mc admin info <现有别名>                  # 所有节点在线、新版本、旧别名直连
```

随后下载一个已知对象比对校验和，用现有 SDK 跑通一个应用，重启服务一次并复查。回滚还有一条前提：迁移窗口内不要启用旧版本无法理解的新功能——回滚意味着回到旧二进制能解析的状态。
