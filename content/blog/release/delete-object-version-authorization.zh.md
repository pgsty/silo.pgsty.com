---
title: "显式版本删除现在要求 DeleteObjectVersion"
linkTitle: "版本删除授权"
date: 2026-09-02T00:00:00+08:00
author: "冯若航"
description: "SILO 现在根据请求的实际 versionId 选择 DeleteObject 或 DeleteObjectVersion，同时保留既有的最小权限复制目标策略。"
tags: [发布, 安全, IAM, S3, 兼容性]
weight: 9
draft: false
url: "/zh/blog/release/delete-object-version-authorization/"
---

自 [Server 20260903](/zh/blog/release/silo-20260903/) 起（[pgsty/silo#104](https://github.com/pgsty/silo/pull/104)，对应 [Issue #58](https://github.com/pgsty/silo/issues/58)），SILO 按照删除请求实际执行的操作类型选择所需权限：

| 请求 | 所需权限 |
| --- | --- |
| 未携带 `versionId` | `s3:DeleteObject` |
| 版本 UUID | `s3:DeleteObjectVersion` |
| 显式 `versionId=null` | `s3:DeleteObjectVersion` |
| `DeleteObjects` | 对每个 XML 条目独立应用映射 |

此前所有情况均要求 `s3:DeleteObject`，而 `s3:DeleteObjectVersion` 仅用于检查显式 Deny。这导致仅持有 `DeleteObject` 的主体可以永久移除指定的历史版本，而仅持有 `DeleteObjectVersion` 的最小权限清理主体却无法执行版本清理。

修复后，仅持有 `DeleteObject` 的主体仍可执行不带版本号的删除或创建删除标记（Delete Marker），但在尝试删除指定 UUID 或 `null` 版本时会收到 `AccessDenied`。仅持有 `DeleteObjectVersion` 的主体可以永久删除指定版本，但不能创建删除标记。显式 Deny 与 `s3:versionid` 策略条件保持原有求值优先级。批量删除（`DeleteObjects`）按每个条目自身的 `VersionId` 求值，外层 URL 查询参数不会污染其他条目的条件值。

## 复制兼容性 {#replication-compatibility}

存储桶与站点复制的目标策略**无需**新增 `s3:DeleteObjectVersion`。已认证请求通过精确的内部复制标记与 `s3:ReplicateDelete` 获得复制删除信任，接收端继续沿用已部署的 `s3:DeleteObject + s3:ReplicateDelete` 策略契约；而针对 `s3:DeleteObjectVersion` 的显式 Deny 仍会阻止复制版本清理。

这种区分既避免了升级后的目标站点静默拒绝永久删除复制，也不会给仅持有 `ReplicateDelete` 的凭据赋予额外的普通删除能力。双站点回归测试验证了使用最小权限策略（不含 `DeleteObjectVersion`）的目标端用户：永久版本删除与删除标记均能正常收敛。

## 升级影响 {#upgrade-impact}

- 请检查当前仅授予 `s3:DeleteObject`，但需要执行 `mc rm --version-id`、`mc rm --versions`、Console“删除全部版本”或 SDK 指定 `versionId` 删除的用户、服务账号、OPA 及外部授权策略，为其补充 `s3:DeleteObjectVersion`。
- 对于普通的指定版本删除，外部授权插件现在只会收到一次 `s3:DeleteObjectVersion` 判定请求，不再像修复前那样先收到一次仅检查 Deny 的 `s3:DeleteObjectVersion` 调用、再收到一次 `s3:DeleteObject` 调用。
- `X-Minio-Force-Delete` 前缀强制删除仍由 `s3:DeleteObject` 控制。
- 本次变更不涉及传输协议或磁盘存储格式迁移。

完整的操作权限矩阵参见[对象删除](/zh/administration/object-management/object-delete/)。
