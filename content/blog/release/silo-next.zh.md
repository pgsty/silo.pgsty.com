---
title: "Silo 下一版发布说明"
linkTitle: "silo next"
date: 2026-09-02
author: "冯若航"
description: "20260806 之后版本的说明草稿：复制与 CORS 请求信任、Object Lock 与元数据一致性修复、与 AWS 对齐的校验和与删除授权、内嵌 Console 的安全修复，以及升级前需要核对的事项。"
tags: [Release, silo]
weight: 9
draft: true
url: "/zh/blog/release/silo-next/"
---

> **草稿。** 版本标签、提交、提交数与构件摘要在打 tag 时填入。在此之前，本页描述的是发布前清理分支合并后 `main` 的状态。

**版本：** 待定 · **提交：** 待定 · **上一版本：** [20260806](/zh/blog/release/silo-20260806/)

## 亮点 {#highlights}

- **请求信任来自认证而非 header。** 复制专用 header 只在精确标记与 `s3:ReplicateObject` / `s3:ReplicateDelete` 同时成立时才获得复制语义，其余请求在签名验证后被剥离这些 header。预鉴权 CORS 查找只读驻留元数据，任意路径段不再触发元数据读取或缓存增长。
- **桶级 CORS。** `PUT`/`GET`/`DELETE ?cors` 真正实现；桶配置覆盖全局策略，并在站点复制对端之间收敛。
- **元数据一致性。** `metadata.lock` 串行化所有桶配置写入；`ForceCreate` 与站点 adoption 保留既有配置；启用 lock 的桶始终使用纯 Enabled 版本控制。
- **与 AWS 对齐的授权。** 显式删除版本需要 `s3:DeleteObjectVersion`；用户与组状态变更要求与目标状态匹配的动作；策略写入拒绝裸 ARN 前缀。
- **校验和。** 服务端计算分片校验和、联邦 `UploadPartCopy`、`CompleteMultipartUpload` 返回 `ChecksumType`、与 AWS 对齐的完成错误码、拒绝未知算法与 `CRC64NVME` + `COMPOSITE`。
- **SSE-C。** 零字节对象与 `GetObjectAttributes` 校验客户密钥；null 版本与原地换钥复制不再把对象重写成不可读密文。
- **组件。** Go 1.27.0；上游 `minio-go`（`silo-go` 分叉退役）；内嵌含 v2.3.0 安全修复的 Console `43f8447fd`；捆绑 `mcli` 20260901。

## 安全修复 {#security}

已在仓库台账登记为 SN-2026-006 至 SN-2026-010：零字节 SSE-C 密钥校验、`GetObjectAttributes` 的 SSE-C 校验、复制请求信任（补全 CVE-2026-34204）、用户与组状态授权、`DeleteObjectVersion` 授权。均继承自上游，影响此前所有版本。公开的 advisory 文章随本版本之后发布。

## 行为变更与升级检查 {#upgrade}

升级前请阅读 [从 RELEASE.2026-08-06 升级](/zh/compatibility/migration/#since-20260806)。简言之：给需要删版本的主体授予 `s3:DeleteObjectVersion`，给原本靠 `Deny s3:DeleteObject` 阻止永久删除的策略补上对它的 Deny；拆分启用与禁用的管理授权；策略写入会拒绝裸 ARN 前缀；给旧版 PostgreSQL / MySQL 通知目标补连接串；等所有复制站点都升级后再配置桶级 CORS。

## 已知问题 {#known-issues}

- **条件删除。** `DeleteObject` 忽略 HTTP `If-Match` 头，`DeleteObjects` 忽略每个 `<Object>` 条目的 `<ETag>` 元素（[#10](https://github.com/pgsty/silo/issues/10)），两者都执行无条件删除。修复存在于本地分支，不在本版本内。
- **多站点配置删除。** 在一个站点删除桶策略、SSE、标签或配额配置后，仍持有该配置的对端可能把它恢复回来（[#77](https://github.com/pgsty/silo/issues/77)）；只有 CORS 使用带 tombstone 的寄存器。继承自上游。
- **混合版本复制组。** 仍在 20260806 的对端会接受但忽略桶级 CORS，并持续报告 CORS 不一致。请先升级全部站点。
- **回滚。** 20260806 忽略桶级 CORS，并会在重写该桶元数据时把它丢掉。
- **内嵌 Console。** 服务端内嵌的是 `pgsty/silo-pkg` 模块路径迁移之前的最后一个 Console 提交；Console 2.3.0 其余变更要等服务端直接导入该路径后才能跟进。

## 验证 {#verification}

发布候选上：完整 `cmd` 与 `internal` 套件、`cmd` race 套件、lint、生成文件与兼容基线守卫、`govulncheck`，以及六种部署形态（FS、erasure、分布式 erasure、erasure sets、多池、IPv6 多池）的 `make verify` 全部通过。
