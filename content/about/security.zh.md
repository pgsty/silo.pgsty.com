---
title: "安全政策"
linkTitle: "安全政策"
description: "如何报告 PGSTY SILO 的安全漏洞，以及已修复问题的公布渠道。"
url: "/zh/about/security/"
weight: 40
type: docs
icon: fa-solid fa-shield-halved
---

安全维护正是这个分支存在的理由。上游 `minio/minio` 已经归档，Silo 持续跟踪针对该代码库的 CVE，
回合并或自行编写修复，并把调查过程公之于众。

## 报告安全漏洞 {#reporting}

未公开披露的高危漏洞请通过私密渠道报告，不要发在公开 issue 里。

- **Silo 服务端与 `mcli` 客户端** —— 建议通过 [`pgsty/silo` 的 GitHub Security Advisories](https://github.com/pgsty/silo/security/advisories/new) 提交私密报告。
- **本文档** —— 请在 [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/issues) 提交 issue；如果内容本身披露了某个弱点，请改用私密渠道。

请注明受影响的版本、影响描述，以及复现步骤（如果有），这将帮助我们更快地确认问题。

我们将尽努力在合理时间内回复，但请注意 Silo 是社区项目，我们不承诺任何修复 SLA 与响应时效。

## 上游 MinIO 的漏洞 {#upstream}

Silo 是分支，因此绝大多数发现同样适用于 `minio/minio`。
上游仓库已归档，不再接收报告——这恰恰是本项目要填补的空缺。
请向 Silo 报告；如果问题影响同一份代码的其他发行版，本项目会与它们协调披露。

## 修复在哪里公布 {#published}

- [安全注记](/zh/blog/security/) ——
  每个调查过的 CVE 一篇文章：原始威胁模型、评审过程中的反复、被否决的备选方案、最终确立的不变量、验证证据，以及兼容性代价。

- [发布说明](/zh/blog/release/) ——
  每个修复首次随哪个版本发布并公开可用。

## 加固你自己的部署 {#hardening}

报告只是一半，配置是另一半。部署加固参见[安全检查清单](/zh/operations/checklists/security/)，
TLS 配置参见[网络加密](/zh/operations/network-encryption/)。

## 参见 {#see-also}

- [许可协议](/zh/about/license/) —— 软件按“现状”提供，不附带任何形式的保证
- [归属与署名](/zh/about/attribution/) —— 本文档的版权归属与衍生关系
