---
title: "silo-pkg 3.14.1 Released"
linkTitle: "silo-pkg 3.14.1"
date: 2026-09-16T12:16:06+08:00
author: "Vonng"
description: "JWX JSON encoding hardening and an upstream CopyObject response fix."
tags: [Release, pkg]
weight: 1
url: "/blog/release/pkg-3.14.1/"
---

[v3.14.1](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.1) was published from
[`fa657ef4`](https://github.com/pgsty/silo-pkg/commit/fa657ef431ae22e720df37e5144cf00f67102945).
This is a dependency and tooling release of `github.com/pgsty/silo-pkg/v3`;
the [diff from v3.14.0](https://github.com/pgsty/silo-pkg/compare/v3.14.0...v3.14.1)
changes no package Go source or public API.

## Dependency changes {#dependencies}

- JWX advances from v3.2.0 to v3.3.0. The [vendor's release notes](https://github.com/lestrrat-go/jwx/releases/tag/v3.3.0)
  identify GHSA-4cf7-xm37-g63h: custom JSON field names must be escaped during
  encoding. Reachability depends on accepting attacker-controlled custom claim
  names. The package's `env` JWT path uses registered claim names; dependency
  presence alone does not establish an exploitable mcli path.
- Upstream minio-go advances to `v7.3.1-0.20260915093545-32e1f32cb176`, including
  [minio-go #2306](https://github.com/minio/minio-go/pull/2306): recognize an S3
  `CopyObject` error embedded in an HTTP 200 response instead of reporting a
  successful copy. The fix applies to the SDK's CopyObject path; it does not
  establish every application's selection of that path.
- Testify advances to v1.12.1 and the lint configuration adopts `gomodguard_v2`.
  The Go 1.26 floor, Go 1.27.1 toolchain and go-systemd NetBSD replacement remain.

## Component and migration boundary {#migration}

The [v3.14.0 password-policy change](/blog/release/pkg-3.14.0/#migration) remains
in force; this patch does not revert it. Preserve the paired
`admin:CreateUser` / `admin:ChangeMyPassword` Deny where that was the intended
restriction, using the [migration guide](/compatibility/password-permissions/).

[mcli 20260916](/blog/release/mcli-20260916/) and
[Console 2.4.1](/blog/release/console-2.4.1/) select this package. The Server
source baseline reviewed on September 16 still selects v3.14.0; publishing a
module does not update a compiled Server. The [component matrix](/compatibility/versions/)
separates published components from the next Server's selected dependencies.

Release verification is recorded in the linked release and
[PR #9](https://github.com/pgsty/silo-pkg/pull/9). Those records are upstream
release evidence, not a new execution of their tests by this documentation update.
