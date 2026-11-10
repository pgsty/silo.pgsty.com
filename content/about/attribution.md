---
title: "Attribution"
linkTitle: "Attribution"
description: "Copyright, derivation, and translation notices for the Silo documentation, and how to credit it when you reuse it."
url: "/about/attribution/"
aliases:
  - /attribution/
weight: 30
type: docs
icon: fa-solid fa-copyright
---

## Copyright {#copyright}

**Copyright © 2020–Present MinIO, Inc.**
Original MinIO Object Storage Documentation.

**Copyright © 2026–Present [PIGSTY & SILO Contributors](/about/contributors/)**
Fork maintenance, format conversion, modifications, restored and newly written
content, and Simplified Chinese translation.

Both layers apply at once. A translated or modified page carries MinIO's copyright in the underlying expression and the PGSTY SILO project's copyright in the translation and the changes; neither replaces the other.

## License {#license}

All documentation content on this site is licensed under the
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/) (CC BY 4.0) — the same license as the upstream work. The full legal text is in [LICENSE](https://github.com/pgsty/silo.pgsty.com/blob/main/LICENSE). The PGSTY SILO software itself is licensed separately; see [License](/about/license/).

## Derivation {#derivation}

Portions of this documentation are derived from the [MinIO Object Storage Documentation](https://github.com/minio/docs). The work has been modified from the original: rebranding to PGSTY SILO, restoration of documentation for features removed upstream, conversion of the frozen RST/MyST source to bilingual Markdown, replacement of the Sphinx presentation layer with Hugo and OINK, link and build fixes, ongoing maintenance, and translation into Chinese. The [commit history](https://github.com/pgsty/silo.pgsty.com/commits/main/) is the complete record of changes.

The blog, download and release pages, this section, and PGSTY SILO-specific content are original works of the PGSTY SILO project. Pages that carry upstream material include a notice at the bottom of the page, and pages that PGSTY SILO has modified beyond format conversion link to their change history.

## Translation {#translation}

Chinese translations are unofficial and are maintained by the PGSTY SILO project, not by MinIO, Inc. Where a translation and the original English text differ, the English text is authoritative.

## How to attribute {#how-to-attribute}

If you reuse content from this site, the following credit line satisfies CC BY 4.0:

```text
[PGSTY SILO Documentation](https://silo.pgsty.com) by PGSTY and MinIO, Inc., licensed under CC BY 4.0.
```

For Chinese-language contexts:

```text
[PGSTY SILO 文档](https://silo.pgsty.com/zh)，作者 PGSTY 与 MinIO, Inc.，依据 CC BY 4.0 授权。
```

## Security Research Acknowledgments {#security-acknowledgments}

We acknowledge the security researchers and contributors whose disclosures, root-cause analyses, and patches improved the security of the SILO stack (full activity records are listed in [Contributors](/about/contributors/) and the [Security Advisory Ledger](/about/security-advisories/)):

- **Direct SILO security disclosures and fixes:** [Denis Babchuk (`@botdeniska`)](https://github.com/botdeniska) (private Object Lock, signature verification, replication, and authorization reports, including the report behind [#330](https://github.com/pgsty/silo/pull/330) and [SN-2026-020](/about/security-advisories/#sn-2026-020)), [Eduardo Andrade Machado (`@EduardoAndradeMachado`)](https://github.com/EduardoAndradeMachado) (private security report), [adminsun (`@sun1024`)](https://github.com/sun1024) (private security report), [Oren Yomtov (`@orenyomtov`)](https://github.com/orenyomtov) ([SN-2026-011](/about/security-advisories/#sn-2026-011)), [Dominik Klug (`@nik0xFF`)](https://github.com/nik0xFF) (private email disclosure), [`@szopi00`](https://github.com/szopi00) ([SN-2026-015](/about/security-advisories/#sn-2026-015)), [Jiri Pejchal (`@jiri-pejchal`)](https://github.com/jiri-pejchal) ([SN-2026-014](/about/security-advisories/#sn-2026-014) and `CVE-2026-79921`), [Fabian Schmieder (`@metaneutrons`)](https://github.com/metaneutrons) ([SN-2026-010](/about/security-advisories/#sn-2026-010)), [Sarthak Mittal (`@naiveHobo`)](https://github.com/naiveHobo) ([SN-2026-017](/about/security-advisories/#sn-2026-017)), [`@AEGEGE`](https://github.com/AEGEGE) ([#196](https://github.com/pgsty/silo/pull/196)), [`@ZouhairCharef`](https://github.com/ZouhairCharef) (`CVE-2026-34986`), and [Mario Fredenhagen (`@mfredenhagen`)](https://github.com/mfredenhagen) (`CVE-2026-39883`).
- **Upstream MinIO advisory researchers (remediated in SILO):** [Simeon Poot (`@SimeonPoot`)](https://github.com/SimeonPoot) ([`CVE-2025-62506`](/about/security-advisories/#cve-2025-62506) / [`GHSA-jjjj-jwhf-8rgr`](https://github.com/advisories/GHSA-jjjj-jwhf-8rgr)), [Sang-Hoon Choi (`@KoreaSecurity`)](https://github.com/KoreaSecurity) ([`CVE-2026-33322`](/about/security-advisories/#cve-2026-33322) / [`GHSA-5cx5-wh4m-82fh`](https://github.com/advisories/GHSA-5cx5-wh4m-82fh)), [XlabAI (`@XlabAITeam`)](https://github.com/XlabAITeam) ([`CVE-2026-39414`](/about/security-advisories/#cve-2026-39414) / [`GHSA-h749-fxx7-pwpg`](https://github.com/advisories/GHSA-h749-fxx7-pwpg)), [skull (`@ddd`)](https://github.com/ddd) ([`CVE-2026-40344`](/about/security-advisories/#cve-2026-40344) / [`GHSA-9c4q-hq6p-c237`](https://github.com/advisories/GHSA-9c4q-hq6p-c237) and [`CVE-2026-41145`](/about/security-advisories/#cve-2026-41145) / [`GHSA-hv4r-mvr4-25vw`](https://github.com/advisories/GHSA-hv4r-mvr4-25vw)), and [Adrian Denkiewicz (`@adrian-doyensec`)](https://github.com/adrian-doyensec) ([`CVE-2026-42600`](/about/security-advisories/#cve-2026-42600) / [`GHSA-xh8f-g2qw-gcm7`](https://github.com/advisories/GHSA-xh8f-g2qw-gcm7)).

## Disclaimer {#disclaimer}

Unless otherwise separately undertaken by the Licensor, to the extent possible, the Licensor offers the Licensed Material as-is and as-available, and makes no representations or warranties of any kind concerning the Licensed Material, whether express, implied, statutory, or other. See Section 5 of the [license](https://creativecommons.org/licenses/by/4.0/legalcode) for the complete disclaimer of warranties and limitation of liability.

## See also {#see-also}

- [Contributors](/about/contributors/) — community code, design, issue, and security contributors
- [Security Advisories](/about/security-advisories/) — canonical CVE and `SN-2026-*` advisory ledger
- [License](/about/license/) — AGPLv3 for the software, CC BY 4.0 for this documentation
- [Trademark Notice](/about/trademark/) — how the MinIO name is used here
