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

[v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) was published on
2026-09-13 from [`827f8109`](https://github.com/pgsty/silo-pkg/commit/827f8109ff11bf6239a35d8d6d137cb5738539c3).
It is consumed directly as `github.com/pgsty/silo-pkg/v3`.

## Password-policy migration {#migration}

**This release changes authorization semantics.** The public
`Policy.IsAllowedActions` method now reports `admin:ChangeMyPassword` unless
explicitly denied; `admin:CreateUser` requires an explicit Allow. With matching
Server/Console source, a CreateUser deny alone no longer locks the caller's
password, while a ChangeMyPassword deny does.

The built-in `readonly` drops its CreateUser deny. A separate CreateUser Allow
can therefore become effective; the added `consolereadonly` follows the same
split and includes bucket listing. Neither policy grants user administration
by itself. Saved policies and overrides are not rewritten.

To preserve the old combined restriction, retain both actions in the **same
Deny statement**, including its original scope and conditions, before upgrading
and throughout rollback. Old Servers do not enforce a password-only deny for
this endpoint. Read the [full migration guide](/compatibility/password-permissions/).

As of 2026-09-13, pkg and mcli have been released, but the matching Server and
Console changes are **main-branch source only**. Server 20260903 and Console
v2.4.0 do not contain the split. See [the component matrix](/compatibility/versions/).

## Dependencies and verification {#dependencies}

- Upstream minio-go is pinned to `v7.3.1-0.20260910142817-60bd07042d49`:
  configurable upload limits, streaming Content-Type signing, caller TLS trust
  for RDMA, consistent listing checksums and optional restore status.
- Go x/* dependencies were refreshed, with govulncheck 1.8.0. The library retains
  its Go 1.26 floor and Go 1.27.1 toolchain; public Go signatures are unchanged.
- The go-systemd v22.6.0 replacement remains necessary for NetBSD compilation.
- Full race suites passed on Go 1.26.8 and 1.27.1, along with lint and LDAP
  configuration validation. Vulnerability scanning found no reachable or
  imported vulnerable package; unused OpenPGP code retains module-only
  GO-2026-5932. The release resolves through the Go proxy and checksum database.

The earlier [v3.13.3](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.3)
policy Deny/NotResource and bounded wildcard fixes remain included. Policies
whose clauses were already lost must be recovered from their original source.
The module-path migration introduced in [v3.13.0](/blog/release/pkg-3.13.0/) is
complete in all four maintained components.

[Source changes since v3.13.3](https://github.com/pgsty/silo-pkg/compare/v3.13.3...v3.14.0) ·
[upstream adoption record](https://github.com/pgsty/silo-pkg/blob/v3.14.0/UPSTREAM.md).
