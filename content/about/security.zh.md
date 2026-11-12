---
title: "安全政策"
linkTitle: "安全政策"
description: "如何报告 PGSTY SILO 的安全漏洞，以及安全公告与修复版本的发布渠道。"
url: "/zh/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

在上游 `minio/minio` 归档停更后，PGSTY SILO 持续维护对象存储栈的漏洞跟踪与安全补丁。生产环境应运行 **[Server 20261112](/zh/blog/release/silo-20261112/)**、内嵌与独立版 **[Console v2.7.2](/zh/blog/release/console-2.7.2/)**、**[mcli 20261112](/zh/blog/release/mcli-20261112/)** 与 **[silo-pkg v3.16.1](/zh/blog/release/pkg-3.16.1/)**（统一基于 Go 1.27.4 构建），以及可选外部密钥服务 **[KES 20261026](/zh/blog/release/silo-20261026/#kes)**（Go 1.27.3）。

Server 20261112 内嵌 Console v2.7.2，交付 `SN-2026-020` 至 `SN-2026-025` 安全修复：单池 `DeleteObjects` 路径隔离、服务账号三态内联策略保护、双活复制标签与读取代理鉴权及响应头裁剪、`STREAMING-UNSIGNED-PAYLOAD-TRAILER` 签名时间窗与请求头覆盖校验、对象属性／复制／Select／ZIP 归档读取上的 `s3:ExistingObjectTag/<key>` 与版本动作拒绝执行、严格 IAM 与桶策略 JSON 解码，以及 `null` 版本和副本 Object Lock 加固。该版本同时保留此前全部安全修复，包括 Server 20261109 的 `SN-2026-018` 至 `SN-2026-019`、Server 20261018 的 `SN-2026-015` 至 `SN-2026-017` 与 Server 20260916 的 `SN-2026-011` 至 `SN-2026-014`。升级前请查阅 [20261112 升级要求](/zh/blog/release/silo-20261112/#upgrade)、[安全公告台账](/zh/about/security-advisories/)与[组件版本矩阵](/zh/compatibility/versions/)。

单独升级独立版 Console 或 `mcli` 不会替换旧版 Server 内嵌的组件；服务端授权、生命周期与 Object Lock 修复需通过升级 SILO Server 生效。

## 报告安全漏洞 {#reporting}

请通过私密渠道报告尚未公开披露的安全漏洞，不要直接提交公开 Issue：

- **SILO Server、Console、`mcli`、`silo-pkg` 与 `kes`**：通过 [`pgsty/silo` GitHub Security Advisories](https://github.com/pgsty/silo/security/advisories/new) 提交私密报告；若无法使用 GitHub 私密报告通道，可发送邮件至 [ron@pgsty.com](mailto:ron@pgsty.com) 或 [rh@vonng.com](mailto:rh@vonng.com)。
- **文档站点（`silo.pgsty.com`）**：在 [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues) 提交 Issue；若内容涉及可利用的安全弱点，请改用上述私密渠道。

报告请附上受影响的组件版本、复现步骤与影响范围。SILO 是开源社区项目，按尽最大努力原则响应与修复，不提供商业 SLA 承诺。

## 上游 MinIO 相关漏洞 {#upstream}

SILO 派生自 `minio/minio`，继承代码中的缺陷通常同时影响两者。由于上游仓库已归档且不再接收报告，请直接向 SILO 提交；涉及其他活跃分支的共性漏洞，我们会按需协调披露。

## 安全修复发布渠道 {#published}

- **[安全公告台账](/zh/about/security-advisories/)**：全部 `CVE-*` 与 `SN-2026-*` 编号、修复提交、影响范围及依赖安全更新的统一索引。
- **[安全公告专栏](/zh/blog/security/)**：各漏洞的触发条件、根因分析、修复方案与升级验证指南。
- **[发布说明](/zh/blog/release/)**：Server、Console、`mcli`、`silo-pkg` 与 `kes` 各正式版本的发行记录。

## 部署安全加固 {#hardening}

- [安全检查清单](/zh/operations/checklists/security/) —— 生产环境权限控制、网络隔离与密钥管理规范。
- [网络加密（TLS）](/zh/operations/network-encryption/) —— S3 API、Console 与节点间通信的证书配置。

## 参见 {#see-also}

- [贡献者与致谢](/zh/about/contributors/)
- [许可协议](/zh/about/license/)
- [归属与署名](/zh/about/attribution/)
