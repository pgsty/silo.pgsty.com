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

> **发布状态：** 此变更已实现，正在
> [pgsty/silo#58](https://github.com/pgsty/silo/issues/58) 中评审。本文发布本身不代表
> 某个服务器版本、软件包、镜像或部署已经包含该变更。

SILO 现在按照请求实际执行的删除类型选择权限：

| 请求 | 所需权限 |
| --- | --- |
| 未携带 `versionId` | `s3:DeleteObject` |
| 版本 UUID | `s3:DeleteObjectVersion` |
| 显式 `versionId=null` | `s3:DeleteObjectVersion` |
| `DeleteObjects` | 对每个 XML 条目独立应用映射 |

此前所有情况都要求 `s3:DeleteObject`，`s3:DeleteObjectVersion` 只用于检查显式 Deny。
因此只有 `DeleteObject` 的主体可以永久移除一个指定的历史版本；反过来，只有
`DeleteObjectVersion` 的最小权限清理主体却无法执行它原本负责的操作。

变更后，只有 `DeleteObject` 的主体仍可执行未指定版本的删除或创建 delete marker，
但删除 UUID 或 `null` 版本会收到 `AccessDenied`。只有 `DeleteObjectVersion` 的主体
可以移除指定版本，但不能创建 delete marker。显式 Deny 与 `s3:versionid` 条件继续遵循
正常策略优先级。多删读取每个条目自己的 `VersionId`；外层查询参数不能污染其他条目的
condition value。

## 复制兼容性 {#replication-compatibility}

存储桶与站点复制的目标策略**不需要**新增 `s3:DeleteObjectVersion`。通过认证的请求凭借
精确内部 marker 与 `s3:ReplicateDelete` 获得复制删除信任；receiver 继续保留已经部署的
`s3:DeleteObject + s3:ReplicateDelete` 契约。显式 Deny
`s3:DeleteObjectVersion` 仍会阻止复制版本清理。

这种区分既避免升级后的目标端静默拒绝永久删除复制，也不会给只有
`ReplicateDelete` 的凭据新增删除能力。真实两站回归使用了不含
`DeleteObjectVersion` 的文档最小策略目标用户；永久版本删除与 delete marker 均成功收敛。

## 升级影响 {#upgrade-impact}

- 检查当前只授予 `s3:DeleteObject`、但会执行 `mc rm --version-id`、
  `mc rm --versions`、Console 删除全部版本或 SDK `versionId` 删除的用户、服务账户、
  OPA 与外部授权策略。
- 对普通的指定版本删除，外部授权插件现在只会看到一次
  `s3:DeleteObjectVersion` 判定，而不再看到旧的 deny-only 检查再加
  `s3:DeleteObject` 两次调用。
- `X-Minio-Force-Delete` 前缀清理仍由 `s3:DeleteObject` 控制；它不是显式版本 S3 请求。
- 不涉及 wire 或存储格式迁移。回滚会恢复旧授权映射，但不会修改已有对象或 metadata。

完整操作权限矩阵参见[对象删除](/zh/administration/object-management/object-delete/)。
