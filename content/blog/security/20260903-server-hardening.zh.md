---
title: "SILO 20260903 安全说明：SN-2026-006 至 010"
linkTitle: "20260903 · SN-006–010"
date: 2026-09-03
author: "冯若航"
description: "SILO 20260903 修复的五项继承服务端授权与加密问题：SSE-C 密钥认证、复制 header 信任、管理状态授权与显式版本删除。"
tags: [安全, S3, SSE-C, Replication, IAM]
weight: 8
draft: false
url: "/zh/blog/security/20260903-server-hardening/"
---

本公告汇总随 [SILO Server 20260903](/zh/blog/release/silo-20260903/)（[`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z)）发布的五项服务端安全修复，涵盖客户端提供密钥加密（SSE-C）、客户端可控复制请求头、管理端账户/组状态变更鉴权以及显式对象版本删除。`SN-2026-006` 至 `SN-2026-010` 为 SILO 安全说明编号，对应从上游 `minio/minio` 代码基线继承并在发布前审计中修复的权限与密码学边界缺陷。

## 摘要 {#summary}

| 编号 | 触发前置条件 | 缺陷表现 | `20260903` 修复后行为 |
| :-- | :-- | :-- | :-- |
| `SN-2026-006` | 对 SSE-C 零字节对象具备读取权限 | 因无数据块需要解密，传入错误的客户密钥也会返回成功 | 强制解封并校验对象密钥；错误密钥返回 `403 AccessDenied` |
| `SN-2026-007` | 对 SSE-C 对象具备读取权限，或伪造复制标记请求头 | `GetObjectAttributes` 未校验客户密钥即返回受保护元数据 | 普通请求必须提供正确密钥；仅通过鉴权的复制对端可走副本元数据分支 |
| `SN-2026-008` | 可调用相关读/写/删接口的任意已认证身份 | 伪造内部复制请求头即可在无复制权限时触发复制专用语义 | 必须携带精确标记且通过 `s3:ReplicateObject` 或 `s3:ReplicateDelete` 鉴权 |
| `SN-2026-009` | 仅持有单向状态管理权限的已认证管理 API 主体 | 仅持启用权限即可禁用账户/组，仅持禁用权限反而被拒 | 根据请求的目标状态分别校验对应的启用或禁用权限 |
| `SN-2026-010` | 持有 `s3:DeleteObject` 但无 `s3:DeleteObjectVersion` 的已认证主体 | 缺少 `s3:DeleteObjectVersion` 权限仍可永久删除指定历史版本 | 带显式 `versionId` 的删除必须具备 `s3:DeleteObjectVersion` 权限 |

## SN-2026-006：零字节 SSE-C 密钥认证 {#sn-2026-006}

**影响操作：** SSE-C 零字节对象的 `GetObject`、`HeadObject`、`CopyObject` 源处理与 `GetObjectAttributes`。<br>
**跟踪：** [issue #82](https://github.com/pgsty/silo/issues/82)。<br>
**修复：** `b73581b05`、`c4fd97d0b`。

SSE-C 在元数据中保存密封的对象密钥（sealed object key），并要求调用方在读取时再次提供匹配的客户密钥。常规读取在初始化加密数据流时解封并校验密钥；但零字节对象没有数据块，旧版快速返回分支在解封对象密钥前就提前返回。

结果具有该对象读取权限的调用方即使传入错误的客户密钥也能收到成功响应，甚至可以在不知道当前密钥的情况下用新密钥复制该对象。

修复后，服务端无论对象长度是否为零均强制解封校验 SSE-C 密钥。正确密钥行为不变；错误密钥统一返回 `403 AccessDenied`（覆盖 `null` 版本与密钥轮换场景）。

## SN-2026-007：SSE-C GetObjectAttributes {#sn-2026-007}

**影响操作：** SSE-C 对象的 `GetObjectAttributes`。<br>
**跟踪：** [issue #84](https://github.com/pgsty/silo/issues/84)。<br>
**修复：** `474cd5801`、`74c97d005`、`21870fa2e`。

`GetObjectAttributes` 会返回对象大小、ETag、校验和、存储级别与分片元数据。原有处理函数未验证调用方提供的 SSE-C 密钥即返回上述属性，且只要请求中出现 `X-Minio-Source-Replication-Request` 请求头就会直接跳过密钥检查。

修复将两类调用路径明确分离：

- 普通 S3 调用方必须提供正确的 SSE-C 密钥（密钥缺失或错误返回 `403 AccessDenied`）；
- 站点/桶复制对端必须在通过身份认证并具备 `s3:ReplicateObject` 权限后，方可走副本免解密元数据分支。

## SN-2026-008：复制请求头信任边界加固 {#sn-2026-008}

**影响面：** 对象读写、分片上传完成、对象与版本删除、Snowball 解压、Object Lock 时间戳、校验和元数据与桶事件通知。<br>
**跟踪：** [PR #101](https://github.com/pgsty/silo/pull/101)。<br>
**主要修复范围：** `938603458` 至 `04b097fd9`，以及随后的 Snowball 与规则前缀加固。

[CVE-2026-34204](/zh/blog/security/cve-2026-34204/) 阻止了普通 `PUT` 与 `COPY` 请求导入部分复制加密元数据，但全面排查发现，多处下游代码仍将“请求中带有内部复制头”直接视为“请求来自受信任复制节点”。

视具体接口而定，具备普通读写权限的客户端此前可以通过伪造复制请求头：

- 在不提供客户密钥的情况下读取 SSE-C 对象的免解密路径；
- 强行保留客户端指定的源端 ETag 或修改时间（`MTime`）；
- 注入源端校验和、实际大小、保留期、法律冻结或 `REPLICA` 状态元数据；
- 触发仅限复制使用的删除语义或抑制桶事件通知；
- 在 Snowball 归档解压时跨条目传递复制信任状态。

修复方案在接收端建立了统一的复制信任判定流程：

1. 先按原始签名请求完成 SigV4 认证；
2. 要求携带唯一且精确小写的 `X-Minio-Source-Replication-Request: true` 标记头；
3. 在目标资源上校验 `s3:ReplicateObject` 或 `s3:ReplicateDelete` 权限；
4. 仅在复制状态同时为 `REPLICA` 时派生更严格的 `replicaTrusted` 状态；
5. 将判定结论存入私有的 `req.Context()` 键中；
6. 验签完成后在请求克隆上剥离未受信任的内部复制头，同时保留底层 `Trailer` 映射以确保流式校验和正常验证。

完整的协议矩阵、CORS 交互、双站点 TLS 黑盒复制验证与被否决方案详见[鉴权前不做 I/O，Header 不产生权限](/zh/blog/design/cors-replication-trust/)。

## SN-2026-009：用户与组状态管理授权 {#sn-2026-009}

**影响操作：** 管理 API `SetUserStatus`、`SetGroupStatus`。<br>
**跟踪：** [PR #73](https://github.com/pgsty/silo/pull/73) / [PR #85](https://github.com/pgsty/silo/pull/85)。<br>
**修复：** `58735ee38`、`229fe2b3c`。

原有处理函数在检查目标状态参数前固定校验 `admin:EnableUser` 或 `admin:EnableGroup`。这导致仅被授予启用权限的受限管理员同时也能禁用账户/组，而仅持有禁用权限的管理员反而无法执行禁用操作。

修复后由请求的目标状态决定所需权限：

| 目标操作 | 所需权限 |
| :-- | :-- |
| 启用用户 | `admin:EnableUser` |
| 禁用用户 | `admin:DisableUser` |
| 启用组 | `admin:EnableGroup` |
| 禁用组 | `admin:DisableGroup` |

`admin:*` 与内置 `consoleAdmin` 策略不受影响；仅依赖单一启用权限执行双向操作的自定义最小权限策略需要补齐对应权限。

## SN-2026-010：显式对象版本删除鉴权 {#sn-2026-010}

**影响操作：** `DeleteObject` 与 `DeleteObjects` 中携带显式 `versionId` 的删除条目。<br>
**跟踪：** [issue #58](https://github.com/pgsty/silo/issues/58)、[PR #104](https://github.com/pgsty/silo/pull/104)。<br>
**修复范围：** `75a6734e4` 至 `d2d47a41f`。

原有 S3 删除路径将携带显式 `versionId` 的永久版本删除按普通 `s3:DeleteObject` 授权，仅将 `s3:DeleteObjectVersion` 作为次级 `Deny` 检查。这与 AWS S3 规范不一致，使仅具备普通删除权限的调用方也能永久删除指定的历史版本。

Server `20260903` 要求删除显式版本必须具备 `s3:DeleteObjectVersion` 权限；不带 `versionId` 的普通删除继续校验 `s3:DeleteObject`，复制目标端继续使用 `s3:ReplicateDelete`。升级后：

1. 仅持有 `s3:DeleteObject` 的主体无法再删除显式版本；
2. 通过 `Allow s3:*` 配合 `Deny s3:DeleteObject` 阻止永久删除的策略，需同步将 `s3:DeleteObjectVersion` 加入 `Deny` 列表。

## 运维升级建议 {#operator-actions}

升级前：

1. 梳理需要删除显式对象版本的业务策略，显式授予或拒绝 `s3:DeleteObjectVersion`；
2. 核查涉及用户/组启停的自定义管理策略；
3. 确认复制专用账号具备所需的 `s3:ReplicateObject` / `s3:ReplicateDelete` 权限，且普通业务账号未误配这两项权限；
4. 确认 SSE-C 客户端在 `GET`、`HEAD`、`GetObjectAttributes` 与 `CopyObject` 源读取（含零字节对象）时始终传入正确的客户密钥。

升级后：

- 在测试用 SSE-C 对象上分别验证错误密钥（返回 `403`）与正确密钥访问；
- 验证常规对象复制与删除复制；
- 分别验证受限管理角色的启用与禁用操作；
- 分别使用仅含 `s3:DeleteObject` 与包含 `s3:DeleteObjectVersion` 的身份验证历史版本删除。

## 验证边界 {#verification}

上述五项修复均配有单元、Handler、鉴权、流式 Trailer、Snowball 及跨站点复制回归测试。基于 `ebac0ca73` 的本地全量验收通过了完整的 `cmd` 竞态测试套件以及六种部署拓扑下的 174 项集成验收（174 PASS / 0 FAIL），并完成了[发布前复审](/zh/blog/design/server-release-readiness/#decision)记录的 [`RELEASE.2026-09-03T13-18-01Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z) 构建、签名、SBOM 与镜像发布门禁。

## 相邻问题跟踪 {#residual-risks}

- 条件删除（`DeleteObject` 的 `If-Match` 与 `DeleteObjects` 的逐对象 ETag，[#10](https://github.com/pgsty/silo/issues/10)）以及站点复制间桶级元数据删除收敛（[#77](https://github.com/pgsty/silo/issues/77)）另行跟踪，详见 [Server 20260903 发布说明](/zh/blog/release/silo-20260903/#known-issues)与随后的 [Server 20260916 发布说明](/zh/blog/release/silo-20260916/)。
