---
title: "署名归属"
linkTitle: "署名归属"
description: "PGSTY SILO 文档的版权、衍生关系与翻译声明，以及复用时应当如何署名。"
url: "/zh/about/attribution/"
aliases:
  - /attribution/ # Hugo prefixes the language code, so this resolves to /zh/attribution/
weight: 30
type: docs
icon: fa-solid fa-copyright
---

## 版权 {#copyright}

**Copyright © 2020–至今 MinIO, Inc.**
MinIO 对象存储文档原作。

**Copyright © 2026–至今 [PIGSTY & SILO Contributors](/zh/about/contributors/)**
分支维护、格式转换、内容修改、恢复与新增的文档，以及中文翻译。

两层版权同时存在。经过翻译或修改的页面，底层表达的版权属于 MinIO，翻译与修改部分的版权属于 PGSTY SILO 项目，二者互不取代。

## 许可 {#license}

本站所有文档内容依据
[知识共享署名 4.0 国际许可协议](https://creativecommons.org/licenses/by/4.0/deed.zh)（CC BY 4.0）授权，
与上游原作使用同一许可证。完整法律文本见
[LICENSE](https://github.com/pgsty/silo.pgsty.com/blob/main/LICENSE)。
PGSTY SILO 软件本身另行授权，参见[许可协议](/zh/about/license/)。

## 衍生关系 {#derivation}

本文档的部分内容衍生自 [MinIO 对象存储文档](https://github.com/minio/docs)，相对原作已进行若干修改：
更名为 Silo、恢复上游已移除功能的文档、将冻结的 RST/MyST 源码转换为双语 Markdown、
以 Hugo 与 OINK 替换 Sphinx 呈现层、修复链接与构建问题、持续维护，以及翻译为中文。完整的变更记录见[提交历史](https://github.com/pgsty/silo.pgsty.com/commits/main/)。

博客、下载与发行页面、本节内容，以及 Silo 专属内容，
均为 PGSTY SILO 项目的原创作品。凡包含上游素材的页面，都会在页面底部标注来源；
被 Silo 修改过（超出格式转换范围）的页面，还会给出该页自身的修改历史链接。

## 翻译 {#translation}

中文翻译由 Silo 项目维护，属于非官方翻译，与 MinIO, Inc. 无关。
如中文译文与英文原文有出入，以英文原文为准。

## 署名 {#how-to-attribute}

如果你复用本站内容，按下面这样署名即可满足 CC BY 4.0 的要求：

```text
[PGSTY SILO 文档](https://silo.pgsty.com/zh)，作者 PGSTY 与 MinIO, Inc.，依据 CC BY 4.0 授权。
```

英文场景可使用：

```text
[PGSTY SILO Documentation](https://silo.pgsty.com) by PGSTY and MinIO, Inc., licensed under CC BY 4.0.
```

## 安全研究致谢 {#security-acknowledgments}

感谢通过私密渠道披露、Issue 报告、补丁提交或上游安全公告推动 SILO 软件栈安全加固的研究者与贡献者（完整参与记录见[贡献者名录](/zh/about/contributors/)与[安全公告台账](/zh/about/security-advisories/)）：

- **SILO 安全报告与修复贡献者：** [Denis Babchuk（`@botdeniska`）](https://github.com/botdeniska)（多项 Object Lock、签名校验、复制与鉴权私密安全报告，含推动 [#330](https://github.com/pgsty/silo/pull/330) 及关联排查 [SN-2026-020](/zh/about/security-advisories/#sn-2026-020) 的报告）、[Eduardo Andrade Machado（`@EduardoAndradeMachado`）](https://github.com/EduardoAndradeMachado)（私密安全报告）、[adminsun（`@sun1024`）](https://github.com/sun1024)（私密安全报告）、[Oren Yomtov（`@orenyomtov`）](https://github.com/orenyomtov)（[SN-2026-011](/zh/about/security-advisories/#sn-2026-011)）、[Dominik Klug（`@nik0xFF`）](https://github.com/nik0xFF)（私密邮件安全报告）、[`@szopi00`](https://github.com/szopi00)（[SN-2026-015](/zh/about/security-advisories/#sn-2026-015)）、[Jiri Pejchal（`@jiri-pejchal`）](https://github.com/jiri-pejchal)（[SN-2026-014](/zh/about/security-advisories/#sn-2026-014) 与 `CVE-2026-79921`）、[Fabian Schmieder（`@metaneutrons`）](https://github.com/metaneutrons)（[SN-2026-010](/zh/about/security-advisories/#sn-2026-010)）、[Sarthak Mittal（`@naiveHobo`）](https://github.com/naiveHobo)（[SN-2026-017](/zh/about/security-advisories/#sn-2026-017)）、[`@AEGEGE`](https://github.com/AEGEGE)（[#196](https://github.com/pgsty/silo/pull/196)）、[`@ZouhairCharef`](https://github.com/ZouhairCharef)（`CVE-2026-34986`）以及 [Mario Fredenhagen（`@mfredenhagen`）](https://github.com/mfredenhagen)（`CVE-2026-39883`）。
- **上游 MinIO 安全公告发现者（已在 SILO 中修复）：** [Simeon Poot（`@SimeonPoot`）](https://github.com/SimeonPoot)（[`CVE-2025-62506`](/zh/about/security-advisories/#cve-2025-62506) / [`GHSA-jjjj-jwhf-8rgr`](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr)）、[Sang-Hoon Choi（`@KoreaSecurity`）](https://github.com/KoreaSecurity)（[`CVE-2026-33322`](/zh/about/security-advisories/#cve-2026-33322) / [`GHSA-5cx5-wh4m-82fh`](https://github.com/advisories/GHSA-5cx5-wh4m-82fh)）、[XlabAI（`@XlabAITeam`）](https://github.com/XlabAITeam)（[`CVE-2026-39414`](/zh/about/security-advisories/#cve-2026-39414) / [`GHSA-h749-fxx7-pwpg`](https://github.com/advisories/GHSA-h749-fxx7-pwpg)）、[skull（`@ddd`）](https://github.com/ddd)（[`CVE-2026-40344`](/zh/about/security-advisories/#cve-2026-40344) / [`GHSA-9c4q-hq6p-c237`](https://github.com/advisories/GHSA-9c4q-hq6p-c237) 与 [`CVE-2026-41145`](/zh/about/security-advisories/#cve-2026-41145) / [`GHSA-hv4r-mvr4-25vw`](https://github.com/advisories/GHSA-hv4r-mvr4-25vw)）以及 [Adrian Denkiewicz（`@adrian-doyensec`）](https://github.com/adrian-doyensec)（[`CVE-2026-42600`](/zh/about/security-advisories/#cve-2026-42600) / [`GHSA-xh8f-g2qw-gcm7`](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7)）。

## 声明 {#disclaimer}

除许可人另行承诺外，在法律允许的范围内，许可人按“现状”与“现有”方式提供许可材料，
不就许可材料作出任何明示、默示、法定或其他形式的陈述或保证。
完整的保证免责与责任限制条款见
[许可证](https://creativecommons.org/licenses/by/4.0/legalcode)第 5 条。

## 参见 {#see-also}

- [贡献者与致谢](/zh/about/contributors/) —— 社区代码、方案、问题报告与安全研究贡献者名录
- [安全公告台账](/zh/about/security-advisories/) —— CVE 与 `SN-2026-*` 安全修复的统一索引
- [许可协议](/zh/about/license/) —— 软件采用 AGPLv3，文档采用 CC BY 4.0
- [商标声明](/zh/about/trademark/) —— MinIO 这一名称在本站的使用方式
