---
title: Release Notes
linkTitle: Release
description: SILO release notes and historical version records.
weight: 20
icon: fa-solid fa-tag
sidebar_expanded: true
module: [BLOG]
# 发布注记的用途是快速扫读，索引页整个渲染成一张表：日期、标题、标签，
# 不分页。参见 params.ui.blog_index。
blog_index: table
cascade:
  images: [/images/blog/silo-release.webp]
aliases:
  - /releases/
---

Release notes track feature updates, security fixes, dependency upgrades, compatibility requirements, and artifact delivery across the SILO stack.

The **[20261112 coordinated release](/blog/release/silo-20261112/)** ships SILO Server 20261112 alongside embedded and standalone **[Console 2.7.2](/blog/release/console-2.7.2/)** (following **[2.7.1](/blog/release/console-2.7.1/)**), **[mcli 20261112](/blog/release/mcli-20261112/)**, and **[silo-pkg 3.16.1](/blog/release/pkg-3.16.1/)** on Go 1.27.4, delivering `SN-2026-020` through `SN-2026-025` security hardening, service-account inline-policy tri-state preservation, strict policy JSON validation, Object Lock `null`-version and replica protection, and multi-pool / compressed encrypted `Range` repairs.

Earlier **[20261109](/blog/release/silo-20261109/)** notes cover SILO Server 20261109 with **[Console 2.7.0](/blog/release/console-2.7.0/)**, **[mcli 20261109](/blog/release/mcli-20261109/)**, and **[silo-pkg 3.16.0](/blog/release/pkg-3.16.0/)**, and **[20261026](/blog/release/silo-20261026/)** notes consolidate SILO Server, mcli, and optional external **KES 20261026** alongside **[Console 2.5.1](/blog/release/console-2.5.1/)** and **[silo-pkg 3.15.2](/blog/release/pkg-3.15.2/)** (folding the October 24–25 maintenance drafts with automatic redirects).
