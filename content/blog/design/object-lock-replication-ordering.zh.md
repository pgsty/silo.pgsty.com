---
title: "Object Lock 复制排序"
linkTitle: "Object Lock 复制排序"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: "保留期、legal hold 及其删除在副本写入和跨池处理中都是独立排序的状态。"
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/zh/blog/design/object-lock-replication-ordering/"
---

> **2026-09-17 发布更新：** 后续的 #129、#134 与 #178 修复已随 [Server 20260916](/zh/blog/release/silo-20260916/) 发布；协调升级、可选功能启用条件和剩余限制仍按各节执行。下方带日期的源码状态与验证记录保留当时的范围。

**2026-09-16 发布边界：**[`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9) 已随 Server 20260903 发布。后续仅时间戳删除、SSE-C 重传和跨池修复见 [#129](https://github.com/pgsty/silo/pull/129)、[#134](https://github.com/pgsty/silo/pull/134)、[#178](https://github.com/pgsty/silo/pull/178)，它们在 main 中，但不在该发布中。[公告台账](/about/security-advisories/#operational) 记录原始排序缺陷。

## 重建元数据前保留旧状态 {#problem}

副本 COPY 曾在比较保留期和 legal hold 时间戳之前，就用入站请求重建元数据。旧时间戳因此丢失，旧请求看起来也能成为权威更新；legal hold 时间戳还写错到保留期时间戳键。第一批修复在重建目标 map 前捕获已存状态，并让各字段版本保存在各自键中。

保留期和 legal hold 是独立寄存器。较新的保留期不会让较旧的 hold 变得权威，对象修改时间也不能替代任一字段版本。只有入站字段时间戳更新时才应用，旧值或等时间戳更新保留已存状态。

## 删除同样是有序值 {#removals}

移除保留期或 hold 后可能没有活值，但仍携带源时间戳。丢掉时间戳会让延迟旧值回来。后续修复在接收、比较和重发时识别仅时间戳的删除；没有排序证据的缺失字段，与已记录删除是不同状态。

接收端必须在普通元数据 COPY 和完整 SSE-C 副本重传中保留这些差异。对象体重写不能成为删除目标更新 hold 或恢复旧保留期的理由。

## 跨池权威状态 {#pools}

同一版本在多个池有副本时，单个 set 不能独自决定最新字段状态。[多池协调层](/blog/design/multi-pool-object-consistency/) 在共享对象锁下收集同版本副本，分别按时间戳合并保留期和 hold。未知池状态不是空值；该修复关闭了原先以 #133 留下的源码边界。

## 授权与限制 {#limits}

排序不会授予修改 Object Lock 的权限，复制信任检查和相关 S3/admin 权限仍然适用。这不是绕过 governance 或 compliance 保留的新用户 API，也不建立不同步源时钟间的因果顺序，更不提供部分存储失败后的分布式回滚。

历史旧更新可能已经改变存储状态。升级只能阻止修复路径再次接受同类错误，不能重建丢失的保留历史。宣布恢复前，应在各站点按权威记录核对精确版本的保留期和 legal hold。

## 证据 {#verification}

参考 [Object Lock 合并实现](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go)、`erasure-object.go` 的副本写入路径及关联 PR。测试覆盖字段的新旧更新、空值删除、独立字段时间戳、SSE-C 重传和多池；这些源码测试不证明所有历史副本都已收敛。

结合[副本审计手册](/operations/replication/replica-metadata-audit/)、[SSE-C 完整性记录](/blog/design/ssec-replica-integrity/)和[发布矩阵](/compatibility/versions/)使用。依赖组合排序契约前应升级所有参与节点。
