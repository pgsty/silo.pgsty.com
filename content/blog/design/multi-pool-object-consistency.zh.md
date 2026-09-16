---
title: "多池对象一致性"
linkTitle: "多池对象一致性"
date: 2026-09-16
lastmod: 2026-09-16
author: "冯若航"
summary: "先在共享锁下选择一个逻辑对象，再判断条件或合并标签和 Object Lock 状态。"
tags: [Design, S3, Operations]
weight: 7
draft: false
url: "/zh/blog/design/multi-pool-object-consistency/"
---

**2026-09-16 源码状态：**[#178](https://github.com/pgsty/silo/pull/178) 修复多池修改顺序，随后 [#207](https://github.com/pgsty/silo/pull/207) 把当前对象选择扩展到条件 PUT。它们已合入 main，但不在 Server 20260903 中，关闭了 [#133](https://github.com/pgsty/silo/issues/133) 与 [#144](https://github.com/pgsty/silo/issues/144) 跟踪的源码缺陷；这不构成新发布产物的验收。

## 一个键可以有多份物理副本 {#problem}

扩池、退役或中断的清理可能在不同池留下同一个键的副本。逐 set 锁不能与选择另一池的写入串行化；读取第一个副本也不能证明其 ETag、标签或保留期代表逻辑对象。

相关失败包括：旧 ETag 错误满足条件写入或删除，较新的保留期/hold 被旧对象元数据遮蔽，以及删除选中副本后旧副本重新可见。独立操作每个池、最后只汇总成功状态不能解决这些竞争。

## 共享选择与锁边界 {#design}

池协调层在选择到修改的全过程持有同一命名空间对象锁。`objectPoolInfos` 读取每个池中指定的版本，包括正在排空的池。未知或不可读状态是错误，不是对象不存在的证据。副本按修改时间排序，时间相同时以池索引决胜。

不带版本的元数据请求先选定逻辑当前版本，再收集那个版本的副本，不能混合不同对象版本的元数据。Object Lock 保留期、legal hold 和标签各有独立源时间戳；`mergedPoolObjectInfo` 按各字段自己的顺序合并，不把对象修改时间当作每个字段的版本。有时间戳的删除同样是状态。

元数据写入、相关对象写入和 healing 使用同一协调锁。这把锁不提供能在后续失败时撤销所有池已完成磁盘写入的事务。

## 条件与删除 {#conditions}

条件 DELETE 在清理前判断一次，并在进入下层前清掉回调；显式 `versionId` 比较该版本。条件 PUT 在外层锁内从相关池选择最新逻辑表示，包括删除标记状态，再安装新内容。[#207](https://github.com/pgsty/silo/pull/207) 修复的是目标池旧副本让 `If-Match`/`If-None-Match` 与当前对象不一致的情况。

清理或元数据传播仍可能先修改一部分物理副本，再遇到存储错误。仲裁/清理失败不能解释为对象没变，也不能证明所有旧副本都已消失。恢复后应核对状态并重试。批量 XML ETag 条件仍未支持，见[条件 DELETE](/blog/design/conditional-delete/)。

## Object Lock 与复制 {#replication}

副本写入从跨池同版本的权威副本中协调目标保留期和 legal hold。较旧入站副本不能缩短较新的保留期或关闭较新的 hold。标签同样与其时间戳共同传递，包括表示删除的空值。详见 [Object Lock 排序](/blog/design/object-lock-replication-ordering/)及[复制标签](/blog/design/replicated-tag-ordering/)。

## 跨池迁移中的标签 {#migration-tags}

rebalance 与 decommission 把每个版本读成 `FileInfo`，转换成 `ObjectInfo`——这一步把标签头从普通元数据表移到 `UserTags` 字段——再把对象写到目标池。迁移写入方自 2022 年引入以来只复制普通元数据表，于是普通和分片对象在两个入口都会丢标签；2020 年的字段拆分本身没有问题。提交 [`fced86303`](https://github.com/pgsty/silo/commit/fced86303) 让四个迁移写入方共用一个元数据组装：克隆元数据表、恢复 `UserTags`、按存储原样保留标签修订字段，不伪造时间戳，并沿用既有的协调锁。回归覆盖普通与分片对象、初始标签、更新与清空的标签、版本化与旧格式读取。

修复只能防止今后的丢失。此前迁移已经丢掉的标签不会恢复，要恢复必须有可信的旧值来源。修复后的八节点 rebalance 与 decommission 验收在本文写作时尚未完成。

## 证据与运维影响 {#verification}

[协调层实现](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool-consistency.go)、[池入口](https://github.com/pgsty/silo/blob/f99ed829b5eba549160725f035156c9e020b6a07/cmd/erasure-server-pool.go)和两份已合并 PR 界定源码契约。覆盖包含多池、旧副本、删除标记、显式版本、并发写入及失败路径，不代表原子回滚或任意故障容错。

依赖共享锁保证前应升级所有参与节点。可能已遇到缺陷的部署仍需清点历史副本、标签和 Object Lock 状态；源码修复不证明历史清理完成。使用[副本审计手册](/operations/replication/replica-metadata-audit/)及[组件矩阵](/compatibility/versions/)。本修复与[多段上传列举](/blog/design/list-multipart-uploads/)的默认限制和扫描成本是不同问题。
