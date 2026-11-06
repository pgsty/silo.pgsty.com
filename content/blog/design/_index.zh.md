---
title: 设计归档
linkTitle: 设计
description: PGSTY SILO 的架构设计、S3 兼容性契约、复制不变量与工程决策记录。
weight: 40
icon: fa-solid fa-pen-ruler
sidebar_expanded: true
module: [BLOG]
blog_index: list
cascade:
  images: [/images/blog/silo-design.webp]
---

设计归档记录 PGSTY SILO 的核心工程决策：缺陷根因、S3 与 IAM 协议不变量、备选方案取舍、运维边界与回归测试索引。

## 2026-11-06 发布验收中发现

- [局部视图不能把存在的对象报成不存在](/zh/blog/design/partial-view-read-404/)：只能连上部分盘的节点，为什么会对存在的对象返回 404，以及为什么判定“不存在”必须要求每块盘都应答。
- [Multipart 提交失败可能让上传卡死](/zh/blog/design/multipart-complete-retry/)：未达到写 quorum 的提交为什么会让上传一直卡到过期清理，以及为什么修复要等到存储操作能够加 fencing 之后再做。

## 2026-11-04 发布阻塞的生命周期修复

- [多池生命周期过期：按整个对象决策](/zh/blog/design/multi-pool-lifecycle-expiry/)（[#278](https://github.com/pgsty/silo/issues/278)、[#279](https://github.com/pgsty/silo/pull/279)）：解释只按单个池内版本做出的过期判断，为何会隐藏、删除或复活另一个池中的版本，以及为什么在对象锁内按合并版本列表复核是最小而完整的修复。
- [恢复副本：过期的是副本，不是对象](/zh/blog/design/restored-copy-expiry/)（[#281](https://github.com/pgsty/silo/issues/281)、[#282](https://github.com/pgsty/silo/pull/282)）：解释当前版本的恢复副本过期为何会隐藏对象或抹掉更早的 null 版本，以及哪些存储层与原生恢复防护要与精确版本修复一起交付。
- [Peer 重载后的审计 Webhook](/zh/blog/design/audit-webhook-peer-reload/)（[#259](https://github.com/pgsty/silo/issues/259)）：解释运行时修改 audit_webhook 为何会让除处理请求的服务器外其他所有服务器上的目标停止工作，哪些日志子系统存在同样问题，以及为什么用服务器上下文构建日志目标、并先打开队列存储是最小而完整的修复。
- [失败写入与幽灵空前缀](/zh/blog/design/failed-rename-empty-prefix/)（[#285](https://github.com/pgsty/silo/issues/285)、[#286](https://github.com/pgsty/silo/pull/286)）：解释暂存数据在远端 rename 之前消失的写入，为何会留下空对象目录并在之后被列为空前缀，以及为什么在两条 rename 失败路径上清理它就足够。
- [Heal 演练不能删除数据](/zh/blog/design/heal-dry-run-safety/)（源自 [#280](https://github.com/pgsty/silo/pull/280)）：解释 heal 演练为何会删掉 dangling 对象最后的元数据副本，并在远端节点上执行真实的桶 heal，以及为什么提前返回加上把演练标志传给 peer 能同时关闭这两条路径。
- [生命周期"删除全部版本"只能作用于一个 key](/zh/blog/design/ilm-delete-all-exact-key/)（在审查 [#278](https://github.com/pgsty/silo/issues/278) 修复时发现）：解释 ExpiredObjectAllVersions、DelMarkerExpiration 和批量过期的默认 purge 为何会删除过期 key 名下的所有其他 key，以及为什么在复核后按版本 ID 只清理该 key 自身的版本，是最小而安全的修复。
- [Console 的桶配额：列表显示与数值校验](/zh/blog/design/console-quota-numeric-validation/)（[silo-console#72](https://github.com/pgsty/silo-console/issues/72)、[silo-console#73](https://github.com/pgsty/silo-console/issues/73)）：解释 Console 设置的配额为何在桶列表中显示为"-"、创建桶时为何会把超大配额变成 1 字节、两者的来源，以及已合并的 Console 修复覆盖了什么。
- [大型单池集群的锁域](/zh/blog/design/single-pool-lock-domains/)：解释在 18 台及以上主机的单池集群中，DELETE 与 CopyObject 为何无法与同一 key 上的 PUT 互斥，哪些布局受影响，以及关闭它的路由改动。

## 2026-11-01 存储池迁移完整性审查

- [存储池迁移完整性审查：#261、#263 与 #265](/zh/blog/design/pool-migration-integrity-review/)：维护者对三个问题及其修复的审查，记录 #266 的贡献合并、#276 的维护者后续修复、验证证据与合并顺序。
- [混合 EC 布局与迁移列表](/zh/blog/design/mixed-ec-migration-listing/)（[#261](https://github.com/pgsty/silo/issues/261)、[#262](https://github.com/pgsty/silo/pull/262)）：解释一次未完成的降级覆写为何会让可读对象从 decommission/rebalance 列表中消失，以及 #262 为何以最小范围解决问题。
- [Tier free version 是内部清理记录](/zh/blog/design/tier-free-version-semantics/)（[#263](https://github.com/pgsty/silo/issues/263)、[#264](https://github.com/pgsty/silo/pull/264)）：解释 free version 为何必须继续供 healing 使用，但不能作为用户可见的删除标记或迁移版本。
- [ILM 过期与存储池迁移顺序](/zh/blog/design/ilm-migration-ordering/)（[#265](https://github.com/pgsty/silo/issues/265)、[#266](https://github.com/pgsty/silo/pull/266)、[#276](https://github.com/pgsty/silo/pull/276)）：解释版本桶的 Expiration 删除标记为何不能让当前版本被跳过，以及维护者后续修复如何保留复制、tier 清理和完成语义。

## 2026-10-24 FULL_OBJECT 校验和复制

- [FULL_OBJECT 校验和复制：在初始化上传时保留类型](/zh/blog/design/replication-full-object-checksum/)（`#254`、`#255`）：解释遗漏类型为何让有效的分片 CRC 对象复制失败，共享请求头的一处修复如何同时恢复已有 CopyObject 路径，以及发送端升级与验收边界。

## 2026-10-24 多池删除与放置决策

- [多池删除：失败时保住最新副本](/zh/blog/design/multi-pool-delete-safety/)（`#256`、`#257`）：解释在线磁盘预检查为何挡不住执行中的 I/O 故障，分阶段清理如何保住每项的权威副本，以及已合并修复的重试、分层引用、性能和兼容性边界。

- [多池覆盖亲和：为何最终没有采纳 #245](/zh/blog/design/overwrite-pool-affinity/)（`#245`）：记录原始放置问题、请求级 quorum 与健康判断改进、仅限普通无版本覆盖的收窄设计、两轮 m3 性能实测，以及小对象覆盖仍未达标后的停止决定。实验修改没有合并。

## 2026-10-23 IAM 与 KMS 设计记录

- [LDAP 长 DN：恢复登录可用性并守住 IAM 撤销安全边界](/zh/blog/design/ldap-long-dn/)（`#250`）：解析 `NormalizeDN` 的 `\xx` 十六进制转义为何触发对象 IAM 后端的单路径分量 255 字节上限，以及为何仅将物理上无法落盘的纯 ASCII 超长分量归类为 `errConfigNotFound`。
- [IAM 策略重载：锁粒度、请求取消与超时预算隔离](/zh/blog/design/iam-policy-cancellation/)（`#251`）：在保留 `writeMu` 写串行锁的前提下将慢速策略加载与 KMS 解密移出内存鉴权缓存锁，将取消信号贯通至 `KES.Decrypt`，并将 `etcd` 单步读取超时与整批解密预算解耦。

## Server 20261018 核心设计记录

围绕 [Server 20261018 正式版](/zh/blog/release/silo-20261018/)的核心架构改动，请参阅：

- [Object Lock 治理保留期与覆写防护](/zh/blog/design/governance-retention-bypass-repair/)（`SN-2026-015`、`SN-2026-016`）
- [IAM Admin 凭据授权边界](/zh/blog/design/iam-admin-authorization/)（`SN-2026-017`）
- [持久化 IAM 撤销与按范围撤销 STS](/zh/blog/design/iam-revocations/#scoped-sts-20261018)（`SN-2026-013`）
- [LIST 恢复锁开销优化](/zh/blog/design/listing-recovery-lock-cost/)
- [ListMultipartUploads 回退决策与容量边界](/zh/blog/design/list-multipart-uploads/#implementation)
- [多池对象一致性与迁移保护](/zh/blog/design/multi-pool-object-consistency/#migration-20261018)
- [KES 与 OpenBao 集成](/zh/blog/design/kes-openbao/)
