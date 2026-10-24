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

Object Lock 复制时间戳排序的初始修复（[`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9)）已随 [SILO Server 20260903](/zh/blog/release/silo-20260903/) 发布（收录于[安全公告台账](/zh/about/security-advisories/#operational)）。针对仅携带时间戳的删除（墓碑）、SSE-C 副本完整重传以及跨存储池 Object Lock 状态合并的后续修复（[PR #129](https://github.com/pgsty/silo/pull/129)、[PR #134](https://github.com/pgsty/silo/pull/134) 与 [PR #178](https://github.com/pgsty/silo/pull/178)）已随 [SILO Server 20260916](/zh/blog/release/silo-20260916/) 正式发布。

## 在重建目标元数据前捕获已存状态 {#problem}

此前，副本 `COPY` 在比较 Object Lock 保留期（Retention）与法务锁定（Legal Hold）修订时间戳之前，会先根据入站请求重建目标端元数据映射表。这导致目标端原有的修订时间戳在比较前即被覆盖丢失，使迟到的旧复制请求能够覆盖目标端较新的锁定状态；此外，旧逻辑还误将法务锁定的时间戳写入了保留期的时间戳键名下。

提交 [`f4c1286c9`](https://github.com/pgsty/silo/commit/f4c1286c9) 改为在重建目标元数据映射表之前先捕获已落盘的 Object Lock 状态，并将每个字段的修订时间戳独立保存在各自的内部元数据键中。

保留期（`mode` + `retain-until-date`）与法务锁定（`status`）是两个彼此独立的状态寄存器：

- 较新的保留期时间戳不会使同一请求中较旧的法务锁定生效（反之亦然）；
- 对象数据本体的修改时间（`ModTime`）不能替代任一字段自身的显式修订时间戳；
- 仅当入站字段的时间戳严格新于目标端已存储的对应字段时间戳时才应用更新；对于更旧或时间戳相等的入站更新，一律保留目标端已存状态。

## 将删除操作同样视为带时间戳的有序状态 {#removals}

清空对象的保留期或解除法务锁定后，字段本身不再包含有效值，但仍携带产生该变更的源端时间戳。如果因为字段值为空就丢弃对应的时间戳，网络中延迟到达的旧复制请求就会将已移除的旧保留期或旧法务锁定重新写回。

[PR #129](https://github.com/pgsty/silo/pull/129) 与 [PR #134](https://github.com/pgsty/silo/pull/134) 在复制接收、时间戳比对与重新发送路径中完整识别并传递“仅含时间戳的空值删除”，严格区分“从未设置过该字段（无排序证据）”与“在指定时刻显式清空了该字段（有时间戳的删除）”。

接收端在普通元数据 `COPY` 与完整的 SSE-C 副本对象重传路径中均保持这一语义：即便因 SSE-C 重传而重写整个对象密文数据流，也不会抹去目标端已有的更新法务锁定或回退目标端更新的保留期。

## 跨存储池权威状态合并 {#pools}

当同一对象版本在多个存储池中存在物理副本时（例如扩容或退役迁移期间），仅读取单个本地纠删集无法决定最新的字段状态。[多池一致性协调层](/zh/blog/design/multi-pool-object-consistency/)（[PR #178](https://github.com/pgsty/silo/pull/178)，关闭 [#133](https://github.com/pgsty/silo/issues/133)）会在共享命名空间对象锁下收集所有存储池中的同版本副本，并按各自的时间戳分别合并保留期与法务锁定状态。不可读或未达法定人数的存储池会直接报错，而不会被视为空状态。

## 授权与运维边界 {#limits}

时间戳排序仅用于在已获授权的副本写入上裁决新旧冲突，本身不会授予修改 Object Lock 的权限；复制信任边界校验与相应的 S3/管理端权限（`s3:ReplicateObject`、`s3:BypassGovernanceRetention`、`s3:PutObjectRetention`、`s3:PutObjectLegalHold`）依然强制执行。该机制建立的是基于源端时间戳的逐跳字段顺序，不提供跨站点未同步时钟之间的因果全序，也不提供部分磁盘故障后的分布式事务回滚。

升级至包含修复的版本可阻止旧复制事件再次覆盖较新的锁定状态，但无法自动重建升级前已被旧事件覆盖的历史状态。运维人员在确认恢复前，应结合权威记录核对各站点精确版本的保留期与法务锁定状态。

## 验证与参考 {#verification}

[`cmd/erasure-server-pool-consistency.go`](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go) 中的 Object Lock 合并实现与 `cmd/erasure-object.go` 中的副本写入路径已通过新旧字段更新、空值删除墓碑、独立字段时间戳、SSE-C 重传与多池场景回归测试验证。

请结合[副本元数据审计手册](/zh/operations/replication/replica-metadata-audit/)、[SSE-C 副本完整性记录](/zh/blog/design/ssec-replica-integrity/)以及[组件版本矩阵](/zh/compatibility/versions/)使用，并在依赖完整排序契约前协同升级所有参与复制的节点。
