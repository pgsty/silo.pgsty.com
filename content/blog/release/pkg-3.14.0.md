---
title: "silo-pkg 3.14.0 Released"
linkTitle: "silo-pkg 3.14.0 Released"
date: 2026-09-13T08:55:28+08:00
author: "Vonng"
description: "Password-capability migration, upstream SDK fixes and the September 13 dependency refresh."
tags: [Release, pkg]
weight: 1
url: "/blog/release/pkg-3.14.0/"
---

[v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) was published on 2026-09-13 from commit [`827f8109`](https://github.com/pgsty/silo-pkg/commit/827f8109ff11bf6239a35d8d6d137cb5738539c3) under the module path `github.com/pgsty/silo-pkg/v3`.

## Password-policy migration {#migration}

**This release updates authorization semantics for self-service password changes:**

- `Policy.IsAllowedActions` now allows `admin:ChangeMyPassword` by default unless explicitly denied, while `admin:CreateUser` still requires an explicit `Allow`. On matching Server and Console builds, denying `admin:CreateUser` alone no longer blocks a caller from changing their own password; denying `admin:ChangeMyPassword` does.
- The built-in `readonly` policy drops its previous `admin:CreateUser` `Deny` rule (so an explicit `admin:CreateUser` `Allow` granted by another attached policy can now take effect). The new `consolereadonly` policy adds bucket listing and uses the same permission split. Neither built-in policy grants user-management permissions on its own.
- Existing custom policies and user-level policy overrides stored in the cluster are not rewritten automatically.

To keep the previous restriction that blocks both user administration and self-service password changes, include both `admin:CreateUser` and `admin:ChangeMyPassword` in the **same `Deny` statement** (preserving its original resource scope and conditions) before upgrading and throughout your rollback window—older Server builds do not enforce a standalone `admin:ChangeMyPassword` deny on this endpoint. See the [full password-permission migration guide](/compatibility/password-permissions/).

**September 16 follow-up:** [Console v2.4.1](/blog/release/console-2.4.1/) ships the matching password UI alongside `silo-pkg v3.14.1` and `mcli 20260916`. See the [component version matrix](/compatibility/versions/) for coordinated upgrade requirements.

## Dependencies and verification {#dependencies}

- **Upstream `minio-go` update:** Pinned to `v7.3.1-0.20260910142817-60bd07042d49`, bringing configurable upload size limits, streaming `Content-Type` signing, caller TLS trust propagation for RDMA, consistent listing checksums, and optional archive-restore status parsing fixes.
- **Toolchain and dependency refresh:** Refreshed `golang.org/x/*` modules while keeping the Go 1.26 minimum requirement, Go 1.27.1 build toolchain, and existing exported Go signatures unchanged. The `go-systemd v22.6.0` replacement is retained for NetBSD cross-compilation compatibility.
- **Testing and vulnerability scanning:** Passed full `-race` test suites on Go 1.26.8 and 1.27.1, lint checks, LDAP configuration validation, and Go module proxy / checksum database resolution. Scanning with `govulncheck 1.8.0` found no imported vulnerable packages (only the module-level `GO-2026-5932` entry for unused OpenPGP subpackages remains).

This release retains the `Deny`/`NotResource` policy serialization fix and bounded wildcard matcher from [v3.13.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.3) (policies that already lost statements under earlier versions must still be restored from their original source). The `github.com/pgsty/silo-pkg/v3` module-path migration introduced in [v3.13.0](/blog/release/pkg-3.13.0/) is complete across all four maintained components.

[Source changes since v3.13.3](https://github.com/pgsty/silo-pkg/compare/v3.13.3...v3.14.0) · [Upstream adoption record](https://github.com/pgsty/silo-pkg/blob/v3.14.0/UPSTREAM.md)
