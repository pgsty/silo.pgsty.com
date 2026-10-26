---
title: "PGSTY SILO Documentation"
linkTitle: "Docs"
description: "SILO 20261025 source changes and published-release documentation"
url: "/docs/"
weight: 1
type: docs
icon: fa-solid fa-book
sidebar_expanded: true
upstream_link: ""
upstream_modified: true
---

**This manual incorporates the [SILO Server 20261025 source changes](/compatibility/server/#maintenance-20261025) (in Draft Release as of 2026-10-26; the current public download remains [Server 20261018](/blog/release/silo-20261018/)).** Installation examples use published release artifacts, and sections covering 20261025 changes explicitly note their version scope.

The Server 20261025 source is built with Go 1.27.3 and integrates Console v2.5.0, mcli 20261025, pkg v3.15.1, and upstream `minio-go` commit `ab93db7ba435`, whereas published Server 20261018 embeds Console v2.4.2 and uses mcli 20261018, pkg v3.14.3, and `minio-go` v7.4.1 (updating standalone Console or mcli does not replace an older Server's embedded components or server-side behavior). Before upgrading, review the [component matrix](/compatibility/versions/), [20261025 release notes](/blog/release/silo-20261025/#server-20261025), and [20261018 upgrade requirements](/blog/release/silo-20261018/#upgrade).

{{< home-docs >}}
