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

> **已随 SILO 20260903 发布。** 这些修复属于 [`RELEASE.2026-09-03T00-00-00Z`](https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T00-00-00Z)。从 20260806 到 20260903 的完整升级边界、组件、验证证据与已知延期见[完整发布说明](/zh/blog/release/silo-20260903/)。

本公告汇总 SILO Server 最终复审发现的五个相关安全问题，覆盖客户提供的加密密钥、客户端可控复制 header、管理状态变更与显式对象版本删除。

`SN-2026-006` 至 `SN-2026-010` 是分叉内部的 security-note 编号，**不是 CVE**，也没有登记到漏洞数据库，不应包装成 CVE。安全编年史继续为每个 CVE 保留独立文章；这篇发布公告集中没有 CVE 的发现，便于运维方围绕一次升级边界完成评估。

五个缺陷均继承自已归档的 `minio/minio` lineage，影响此前所有 SILO 版本。“继承”描述来源，不代表风险较低。

## 摘要 {#summary}

| 编号 | 攻击者所需位置 | 安全失败 | 发布行为 |
| :-- | :-- | :-- | :-- |
| `SN-2026-006` | 对 SSE-C 零字节对象有读取权限 | 因为没有数据块需要解密，错误客户密钥也会被接受 | 显式认证对象密钥；错误密钥返回 `403 AccessDenied` |
| `SN-2026-007` | 对 SSE-C 对象有读取权限，或能提供客户端自造 replication marker | `GetObjectAttributes` 未认证客户密钥就返回受保护 metadata | 普通请求必须给正确密钥；只有已授权复制对端走 replica 例外 |
| `SN-2026-008` | 能调用受影响读/写/删操作的任意已认证主体 | 内部样式 header 在没有复制授权时获得 replication-only 效果 | 必须同时满足精确 marker 与 `s3:ReplicateObject` / `s3:ReplicateDelete` |
| `SN-2026-009` | 只持有一侧 status action 的已认证管理 API 主体 | enable action 可以授权 disable，反向亦然 | 由请求目标状态选择需要的 admin action |
| `SN-2026-010` | 有 `s3:DeleteObject`、无 `s3:DeleteObjectVersion` 的已认证 S3 主体 | 可在缺少 AWS 要求 action 时永久删除显式版本 | 显式版本删除必须有 `s3:DeleteObjectVersion` |

本公告不声称存在 unauthenticated RCE。每项都需要已认证身份或既有对象权限，但会跨越该身份原本授权之外的 privilege 或 cryptographic boundary。

## SN-2026-006：零字节 SSE-C 密钥认证 {#sn-2026-006}

**影响操作：** SSE-C 零字节对象的 `GetObject`、`HeadObject`、`CopyObject` source 处理与 `GetObjectAttributes`。<br>
**跟踪：** [issue #82](https://github.com/pgsty/silo/issues/82)。<br>
**修复：** `b73581b05`、`c4fd97d0b`。

SSE-C 保存一个 sealed object key，读取时要求调用方再次提交 customer key。常规读取在准备 encrypted stream 时认证密钥；零字节对象没有 payload block，旧 fast path 在解封保存的 object key 前就返回。

因此错误客户密钥也可能得到成功响应；caller 甚至可以在不知道当前密钥的情况下，用自己选择的密钥建立 copy 或新 version。调用方仍需有对象读取权限；问题在于对象权限错误替代了独立的 cryptographic proof。

修复让 key authentication 与 payload length 无关。正确密钥行为不变；错误密钥返回 `403 AccessDenied`，并覆盖 null-version 与 key-rotation 情形。

## SN-2026-007：SSE-C GetObjectAttributes {#sn-2026-007}

**影响操作：** SSE-C 对象的 `GetObjectAttributes`。<br>
**跟踪：** [issue #84](https://github.com/pgsty/silo/issues/84)。<br>
**修复：** `474cd5801`、`74c97d005`、`21870fa2e`。

`GetObjectAttributes` 会暴露对象大小、ETag、checksum、storage class 与 multipart part metadata。继承 handler 在没有认证 SSE-C key 的情况下就返回这些属性，还把 `X-Minio-Source-Replication-Request` 的存在当作跳过 key handling 的许可。

修复把两种情况分开：

- 普通 S3 调用方必须提供正确 SSE-C key；
- 真实复制对端只有在鉴权并取得 `s3:ReplicateObject` 后才能走 replica path。

错误密钥现在返回 `403`。缺少所需 key 与权限的裸 marker 不能建立 replica exception。已经持有对应 action 的复制身份继续工作。

## SN-2026-008：复制 Header 不是 Authority {#sn-2026-008}

**影响面：** 对象读写、multipart completion、对象与版本删除、Snowball 解压、Object Lock timestamp、checksum metadata 与 bucket event。<br>
**跟踪：** [PR #101](https://github.com/pgsty/silo/pull/101)。<br>
**主要修复范围：** `938603458` 至 `04b097fd9`，以及之后 Snowball 与 rule-prefix 加固。

[CVE-2026-34204](/zh/blog/security/cve-2026-34204/) 已阻止普通 PUT/COPY 导入一部分 replication SSE metadata；更广泛的审计发现，许多其他 consumer 仍把 header 的存在当作内部复制证明。

视操作不同，只有普通读写权限的客户端可能：

- 在没有客户密钥时请求 SSE-C ciphertext/no-decryption path；
- 保留自带 source ETag 或 modification time；
- 注入 source checksum、actual-size、retention、legal-hold、replica-state metadata；
- 选择 replication-only delete semantics；
- 压制成功 object event；
- 把一个 Snowball archive entry 的 trust 带入另一个 entry。

修复定义统一接收端 authority：

1. 以原始签名形态认证请求；
2. 要求只有一个 marker，且值精确为小写 `true`；
3. 在目标 resource 上授权 `s3:ReplicateObject` 或 `s3:ReplicateDelete`；
4. 只有 replica status 同样成立时才推导更窄的 replica-trusted state；
5. 将决定保存到私有 request context；
6. 鉴权后从 clone 中清除不可信内部 header。

context decision 才是 authority。stripping 保护旧 consumer，却不能自己授予 trust。clone 保留原 trailer map，所以 streaming checksum authentication 仍正确。

详细 protocol matrix、CORS 交互、黑盒 replication test 与否决方案见 [鉴权前不做 I/O，Header 不产生权限](/zh/blog/design/cors-replication-trust/)。

## SN-2026-009：用户与组状态授权 {#sn-2026-009}

**影响操作：** 管理 API `SetUserStatus`、`SetGroupStatus`。<br>
**跟踪：** [PR #73](https://github.com/pgsty/silo/pull/73)。<br>
**修复：** `58735ee38`、`229fe2b3c`。

继承 handler 无论目标状态是什么都检查 `admin:EnableUser` 或 `admin:EnableGroup`。一个只能 enable 身份的最小权限管理员因此也能 disable；只应持有 disable action 的身份则可能失败或按错误 grant 评估。

现在由请求状态决定 action：

| 目标 | 所需 action |
| :-- | :-- |
| 启用用户 | `admin:EnableUser` |
| 禁用用户 | `admin:DisableUser` |
| 启用组 | `admin:EnableGroup` |
| 禁用组 | `admin:DisableGroup` |

`admin:*` 与内建 `consoleAdmin` policy 仍然足够。只有误用单一 action 承担双向操作的自定义 least-privilege policy 需要修改。

## SN-2026-010：显式对象版本删除 {#sn-2026-010}

**影响操作：** `DeleteObject` 与 `DeleteObjects` 中每个带显式 `versionId` 的 entry。<br>
**跟踪：** [issue #58](https://github.com/pgsty/silo/issues/58)、[PR #104](https://github.com/pgsty/silo/pull/104)。<br>
**修复范围：** `75a6734e4` 至 `d2d47a41f`。

继承 S3 path 把显式版本删除当作普通 `s3:DeleteObject` 授权，只把 `s3:DeleteObjectVersion` 当成次级 deny check。这与 AWS 不一致，使只有普通 delete 权限的主体也能永久删除指定历史版本。

本版本要求显式版本必须有 `s3:DeleteObjectVersion`；不带 `versionId` 的删除继续使用 `s3:DeleteObject`；复制 target 保留 `s3:ReplicateDelete` contract。

策略有两点影响：

1. 只有 `s3:DeleteObject` 的主体不再能删除显式版本；
2. 通过 `Allow s3:*` 加 `Deny s3:DeleteObject` 阻止永久删除的策略，必须再 deny `s3:DeleteObjectVersion`。

批量删除修复为每个 entry 保留 authentication 与 audit context，并为普通删除与复制删除加入 least-privilege test。

## 运维动作 {#operator-actions}

升级前：

1. 找出会删除显式版本的 policy 与应用，明确 grant 或 deny `s3:DeleteObjectVersion`；
2. 检查自定义管理 policy 中 user/group enable 与 disable 操作；
3. 确认 replication service account 只有所需 `s3:ReplicateObject` / `s3:ReplicateDelete`，普通应用身份不应拥有这些 action；
4. 确认 SSE-C 集成在 GET、HEAD、attributes、copy-source 操作中都发送同一个客户密钥，包括零字节对象；
5. 若应用依赖“错误 SSE-C key 也成功”，应将其视为潜伏 client bug 并在 rollout 前修正。

升级后：

- 在一次性 SSE-C 对象上分别运行错误密钥 negative test 与正确密钥 positive test；
- 测试一次常规复制与一次复制删除；
- 独立测试每个 delegated admin 方向；
- 分别用只有 `s3:DeleteObject` 的主体、以及额外有 `s3:DeleteObjectVersion` 的主体测试版本删除；
- 先检查 audit log 中意外 deny 的原因，不要直接放宽 policy。

## 验证边界 {#verification}

修复包含 focused unit、handler、authorization、streaming-trailer、Snowball 与 site-replication 测试。`ebac0ca73` 的完整本地验收包括完整 `cmd` race，以及六种部署形态 174 PASS / 0 FAIL。最终发布线在完整验收后又增加一处 CORS state-clear 修复，并通过定向 race、compatibility、generation、diff 与 lint 门禁。

本公告**不声称** `RELEASE.2026-09-03T00-00-00Z` 或任何 image/package 已发布。远端 CI、Test Release、tag 校验、构件签名、checksum、attestation 与真实公开 image pull 仍然是发布 blocker，详见[发布前复审](/zh/blog/design/server-release-readiness/#decision)。

## 本公告之外的残余风险 {#residual-risks}

- 条件删除仍不支持：`DeleteObject` 忽略 `If-Match`，`DeleteObjects` 忽略 per-object ETag（[#10](https://github.com/pgsty/silo/issues/10)）。
- 非 CORS 的 policy/SSE/tag/quota 删除可能无法在站点复制对端间收敛（[#77](https://github.com/pgsty/silo/issues/77)）。
- trust audit 聚焦已知 replication 与 SSE-C 字段；未来新增内部 header 时仍必须回答同一 provenance-and-authorization 问题。

发布说明包含完整的[已知问题与部署边界](/zh/blog/release/silo-20260903/#known-issues)。
