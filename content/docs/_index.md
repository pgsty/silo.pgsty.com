---
title: "PGSTY SILO Documentation"
linkTitle: "Docs"
description: "pgsty/silo 20261018 Documentation"
url: "/docs/"
weight: 1
type: docs
icon: fa-solid fa-book
sidebar_expanded: true
upstream_link: ""
---

**This manual targets [SILO Server 20261018](/blog/release/silo-20261018/), now publicly available.** Key changes are Object Lock and IAM authorization, ordinary LIST recovery, multipart cleanup and retirement of strict multipart listing. The current public Server is 20261018.

Server 20261018 embeds Console v2.4.2 and selects mcli 20261018, pkg v3.14.3 and minio-go v7.4.1. The newer standalone [Console v2.5.0](/blog/release/silo-20261025/#console-250) and [mcli 20261025](/blog/release/mcli-20261025/) use Go 1.27.3 and pkg v3.15.1; installing them does not update Server. Before upgrading, read the [component matrix](/compatibility/versions/), [upgrade requirements](/blog/release/silo-20261018/#upgrade) and [security update](/blog/security/20261018-release-hardening/).

{{< home-docs >}}
