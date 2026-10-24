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

## 2026-10-24 覆盖亲和决策

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
