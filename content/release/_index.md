---
title: Release Notes
linkTitle: Release
description: SILO release notes and historical version records.
weight: 35
type: blog
icon: fa-solid fa-tags
sidebar_root_for: self
sidebar_root_link_self: true
sidebar_expanded: true
module: [BLOG]
outputs:
  - HTML
  - RSS
  - print
# 发布注记的用途是快速扫读，索引页整个渲染成一张表：日期、标题、标签，
# 不分页。参见 params.ui.blog_index。
blog_index: table
blog_index_toggle: true
cascade:
  type: blog
  images: [/images/blog/silo-release.webp]
  outputs:
    - HTML
    - print
  params:
    sidebar_menu_foldable: false
    sidebar_menu_compact: false
    sidebar_expand_levels: 3
aliases:
  - /releases/
  - /blog/release/
---

Release notes track feature updates, security fixes, dependency upgrades, compatibility requirements, and artifact delivery across the SILO stack.

The **[20261112 coordinated release](/release/silo-20261112/)** ships SILO Server 20261112 alongside embedded and standalone **[Console 2.7.2](/release/console-2.7.2/)** (following **[2.7.1](/release/console-2.7.1/)**), **[mcli 20261112](/release/mcli-20261112/)**, and **[silo-pkg 3.16.1](/release/pkg-3.16.1/)** on Go 1.27.4, delivering `SN-2026-020` through `SN-2026-025` security hardening, service-account inline-policy tri-state preservation, strict policy JSON validation, Object Lock `null`-version and replica protection, and multi-pool / compressed encrypted `Range` repairs.

Earlier **[20261109](/release/silo-20261109/)** notes cover SILO Server 20261109 with **[Console 2.7.0](/release/console-2.7.0/)**, **[mcli 20261109](/release/mcli-20261109/)**, and **[silo-pkg 3.16.0](/release/pkg-3.16.0/)**, and **[20261026](/release/silo-20261026/)** notes consolidate SILO Server, mcli, and optional external **KES 20261026** alongside **[Console 2.5.1](/release/console-2.5.1/)** and **[silo-pkg 3.15.2](/release/pkg-3.15.2/)** (folding the October 24–25 maintenance drafts with automatic redirects).
