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

The **[20261109 coordinated release](/blog/release/silo-20261109/)** ships SILO Server 20261109 alongside embedded and standalone **[Console 2.7.0](/blog/release/console-2.7.0/)**, **[mcli 20261109](/blog/release/mcli-20261109/)**, and **[silo-pkg 3.16.0](/blog/release/pkg-3.16.0/)**, delivering multi-pool lifecycle and two-phase restore repairs, S3 `DeleteObjects` and replicated Object Lock enforcement, submitter-bound batch job authorization, ten UI languages with Arabic RTL, and usage-worker and container fixes.

Earlier **[20261026](/blog/release/silo-20261026/)** notes consolidate SILO Server, mcli, and optional external **KES 20261026** alongside **[Console 2.5.1](/blog/release/console-2.5.1/)** and **[silo-pkg 3.15.2](/blog/release/pkg-3.15.2/)** (folding the October 24–25 maintenance drafts with automatic redirects).
