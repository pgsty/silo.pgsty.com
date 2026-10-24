---
title: "安全政策"
linkTitle: "安全政策"
description: "如何报告 PGSTY SILO 的安全漏洞，以及安全公告与修复版本的发布渠道。"
url: "/zh/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

在上游 `minio/minio` 归档停更后，PGSTY SILO 持续维护对象存储栈的漏洞跟踪与安全补丁。生产环境建议运行 [Server 20261018](/zh/blog/release/silo-20261018/)（修复对象锁 `SN-2026-015` / `SN-2026-016` 与 IAM 管理边界 `SN-2026-017`，并包含 Server 20260916 已合入的 `SN-2026-011` 至 `SN-2026-014`）、[Console v2.4.2](/zh/blog/release/console-2.4.2/) 与 [mcli 20261018](/zh/blog/release/mcli-20261018/)；完整升级要求见[十月安全公告](/zh/blog/security/20261018-release-hardening/)、[安全公告台账](/zh/about/security-advisories/)与[组件版本矩阵](/zh/compatibility/versions/)。

## 报告安全漏洞 {#reporting}

请通过私密渠道报告尚未公开披露的安全漏洞，不要直接提交公开 Issue：

- **SILO Server、Console、`mcli` 与 `silo-pkg`**：通过 [`pgsty/silo` GitHub Security Advisories](https://github.com/pgsty/silo/security/advisories/new) 提交私密报告。
- **文档站点（`silo.pgsty.com`）**：在 [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues) 提交 Issue；若内容涉及可利用的安全弱点，请改用上述私密渠道。

报告请附上受影响的组件版本、复现步骤与影响范围。SILO 是开源社区项目，按尽最大努力原则响应与修复，不提供商业 SLA 承诺。

## 上游 MinIO 相关漏洞 {#upstream}

SILO 派生自 `minio/minio`，继承代码中的缺陷通常同时影响两者。由于上游仓库已归档且不再接收报告，请直接向 SILO 提交；涉及其他活跃分支的共性漏洞，我们会按需协调披露。

## 安全修复发布渠道 {#published}

- **[安全公告台账](/zh/about/security-advisories/)**：全部 `CVE-*` 与 `SN-2026-*` 编号、修复提交、影响范围及依赖安全更新的统一索引。
- **[安全公告专栏](/zh/blog/security/)**：各漏洞的触发条件、根因分析、修复方案与升级验证指南。
- **[发布说明](/zh/blog/release/)**：Server、Console、`mcli` 与 `silo-pkg` 各正式版本的发行记录。

## 部署安全加固 {#hardening}

- [安全检查清单](/zh/operations/checklists/security/) —— 生产环境权限控制、网络隔离与密钥管理规范。
- [网络加密（TLS）](/zh/operations/network-encryption/) —— S3 API、Console 与节点间通信的证书配置。

## 参见 {#see-also}

- [许可协议](/zh/about/license/)
- [归属与署名](/zh/about/attribution/)
