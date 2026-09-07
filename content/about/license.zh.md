---
title: "许可协议"
linkTitle: "许可协议"
description: "Silo 软件采用 AGPLv3 许可，本文档采用 CC BY 4.0 许可。"
url: "/zh/about/license/"
weight: 10
type: docs
icon: fa-solid fa-scale-balanced
---

Silo 涉及两套彼此独立的许可协议：软件与文档的分发条款不同，各自沿用其上游作品原有的许可。

| 对象 | 许可协议 | 位置 |
|:-----|:---------|:-----|
| `silo` 服务端 | AGPL-3.0-or-later | [`pgsty/silo`](https://github.com/pgsty/silo/blob/main/LICENSE) |
| SILO Console | AGPL-3.0-or-later | [`pgsty/silo-console`](https://github.com/pgsty/silo-console/blob/main/LICENSE) |
| `mcli` 客户端 | AGPL-3.0-or-later | [`pgsty/mc`](https://github.com/pgsty/mc/blob/main/LICENSE) |
| SILO 共享包 | AGPL-3.0-or-later | [`pgsty/silo-pkg`](https://github.com/pgsty/silo-pkg/blob/main/LICENSE) |
| 本文档 | CC BY 4.0 | [`pgsty/silo.pgsty.com`](https://github.com/pgsty/silo.pgsty.com/blob/main/LICENSE) |

## 软件：AGPLv3 {#software}

PGSTY SILO 是 MinIO 的分支，而 MinIO 自 2021 年起便以
[GNU Affero 通用公共许可证第 3 版](https://www.gnu.org/licenses/agpl-3.0.html)分发。
对于已经以该许可发布的代码，授权不可撤回——这正是本分支得以存在的法律基础。
PGSTY SILO 沿用同一许可：不重新授权、不附加限制、不做开源核心式的功能阉割。

具体而言，AGPLv3 允许你运行、研究、修改与再分发 PGSTY SILO；如果你把修改后的 PGSTY SILO 以网络服务形式提供给用户，
则必须向这些用户提供你所修改版本的对应源代码。

在依据任何摘要（包括本段）行事之前，请阅读[许可证全文](https://www.gnu.org/licenses/agpl-3.0.html)。

## 向 PGSTY SILO 贡献 {#contributions}

四个维护中的软件仓库均按 **AGPL-3.0-or-later** 接收代码贡献，与各仓库自身的许可证一致。
贡献者保留原创内容的版权。SILO 不要求签署 CLA、转让版权，也不要求向 SILO 维护者或上游 MinIO
额外授予 Apache-2.0 许可。

请向负责相应组件的 PGSTY 仓库提交修改，并通过 `git commit -s` 签署
[开发者原创声明 DCO 1.1](https://developercertificate.org/)。详见
[服务端](https://github.com/pgsty/silo/blob/main/CONTRIBUTING.md)、
[Console](https://github.com/pgsty/silo-console/blob/main/CONTRIBUTING.md)、
[mcli](https://github.com/pgsty/mc/blob/main/CONTRIBUTING.md) 和
[共享包](https://github.com/pgsty/silo-pkg/blob/main/CONTRIBUTING.md) 的贡献指南。

本文档的贡献沿用 **CC BY 4.0**。已有的版权、许可和署名声明须予以保留，
单独授权的第三方材料继续遵循其原有许可。

## 文档：CC BY 4.0 {#documentation}

本站发布的全部内容依据
[知识共享署名 4.0 国际许可协议](https://creativecommons.org/licenses/by/4.0/deed.zh)（CC BY 4.0）授权，
与上游 MinIO 文档使用的许可一致。[完整法律文本](https://github.com/pgsty/silo.pgsty.com/blob/main/LICENSE)
以原样形式保存在文档仓库中。

你可以自由地共享与演绎本文档，包括用于商业目的，前提是给出适当的署名、提供许可协议链接，
并说明是否作出了修改。你不得附加任何法律或技术限制，去妨碍他人行使许可协议所允许的权利。

署名是唯一实质性的义务，[归属与署名](/zh/about/attribution/)页面给出了可直接复制使用的署名文本，
以及完整的版权归属层次。

## 许可协议不涵盖什么 {#scope}

许可协议授予的是著作权层面的权利，它不涉及名称。获准使用 MinIO 的代码与文档，
并不等于获准使用 MinIO 商标——参见[商标声明](/zh/about/trademark/)。

## 免责声明 {#disclaimer}

两套许可协议均按“现状”提供作品，不附带任何形式的保证或条件。
完整的保证免责与责任限制条款，见
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode) 第 5 条，
以及 [AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html) 第 15–17 条。

## 参见 {#see-also}

- [署名归属](/zh/about/attribution/) —— 版权归属层次、衍生关系与署名方式
- [商标声明](/zh/about/trademark/) —— MinIO 这一名称在本站的使用方式
- [安全政策](/zh/about/security/) —— 如何报告安全漏洞
