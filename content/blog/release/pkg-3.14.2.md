---
title: "silo-pkg 3.14.2 Released"
linkTitle: "silo-pkg 3.14.2"
date: 2026-10-15T21:32:32+08:00
lastmod: 2026-10-18
author: "SILO"
description: "The October SDK and security dependency baseline for mcli 20261018 and Console v2.4.2."
tags: [Release, pkg]
weight: 1
url: "/blog/release/pkg-3.14.2/"
---

**Release:** [v3.14.2](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.2) · **Source:** [`c6835145176f`](https://github.com/pgsty/silo-pkg/commit/c6835145176f385dd5f2d2a6d5ccd337b258d9bb).

This source-only release of `github.com/pgsty/silo-pkg/v3` supplies the dependency baseline used by published [mcli 20261018](/blog/release/mcli-20261018/) and [Console v2.4.2](/blog/release/console-2.4.2/). [v3.14.3](/blog/release/pkg-3.14.3/) adds a policy-evaluation optimization on top of this baseline and is selected by Server 20261018.

## Changes {#changes}

- Update upstream **minio-go to v7.4.1**: cancel failed multipart uploads even after caller cancellation, serialize retention timestamps in UTC, preserve requested STS durations, and support projected Kubernetes token files. Parallel GET and ComposeObject remain opt-in.
- Update **go-jose to v4.1.6**, addressing excessive CPU use when parsing crafted RSA JWKs ([GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)); update **LDAP to v3.4.15**, **msgp to v1.6.5** and **etcd clients to v3.7.2**.
- Update **x/crypto to v0.58.0**, **x/net to v0.61.0**, **x/sys to v0.49.0** and **x/text to v0.43.0**. Develop and test with **Go 1.27.2**, retaining the **Go 1.26** library floor and **go-systemd v22.6.0** NetBSD replacement.

## Compatibility and adoption {#adoption}

```go
require github.com/pgsty/silo-pkg/v3 v3.14.2
```

Public package signatures and password-policy semantics are unchanged. Consumers upgrading from before v3.14.0 must still follow the [password-permission migration](/compatibility/password-permissions/).

go-jose rejects RSA JWKs above **4096 bits**; check identity-provider keys in applications that use this parser. STS durations below one hour are now sent as requested, so invalid short durations can be rejected by the server. A dependency appearing in `go.mod` does not mean every package is linked into every consumer binary.

Adopting the module requires rebuilding the application. This release has no executable, operating-system package or container image and does not update an installed Server, Console or mcli. See the [component matrix](/compatibility/versions/).

## Validation {#validation}

The release record reports full lint and race tests with Go 1.27.2, race tests with Go 1.26.9, OpenLDAP integration, module tidiness and checksum checks. Vulnerability scanning found no reachable or imported-package vulnerability; an unused OpenPGP module-only advisory remained. The JOSE advisory was checked against upstream as well as the vulnerability database.

Tagged-source CI: [Go](https://github.com/pgsty/silo-pkg/actions/runs/38743292347), [LDAP](https://github.com/pgsty/silo-pkg/actions/runs/38743292597), [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/38743292281).

[Changes since v3.14.1](https://github.com/pgsty/silo-pkg/compare/v3.14.1...v3.14.2) · [PR #10](https://github.com/pgsty/silo-pkg/pull/10).
