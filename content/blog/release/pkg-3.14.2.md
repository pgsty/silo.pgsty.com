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

`github.com/pgsty/silo-pkg/v3 v3.14.2` provides the October dependency baseline for [mcli 20261018](/blog/release/mcli-20261018/) and [Console v2.4.2](/blog/release/console-2.4.2/); follow-up patch [v3.14.3](/blog/release/pkg-3.14.3/) adds an admin-action classification optimization used by [Server 20261018](/blog/release/silo-20261018/).

## Changes {#changes}

- **Update upstream `minio-go` to v7.4.1**: clean up failed multipart uploads even after caller context cancellation, serialize Object Lock retention timestamps in UTC, preserve requested STS durations, and support projected Kubernetes service-account token files (parallel GET and ComposeObject remain opt-in).
- **Update `go-jose` to v4.1.6**: fix excessive CPU consumption when parsing oversized RSA JWKs ([GHSA-mgcc-cww5-fp2q](https://github.com/go-jose/go-jose/security/advisories/GHSA-mgcc-cww5-fp2q)); update **LDAP to v3.4.15**, **msgp to v1.6.5**, and **etcd clients to v3.7.2**.
- **Refresh `golang.org/x/*`**: `x/crypto` **v0.58.0**, `x/net` **v0.61.0**, `x/sys` **v0.49.0**, and `x/text` **v0.43.0**. Built and tested with **Go 1.27.2** while retaining the `go 1.26` module floor and the `go-systemd v22.6.0` NetBSD replacement.

## Compatibility and adoption {#adoption}

```go
require github.com/pgsty/silo-pkg/v3 v3.14.2
```

Public package signatures and password-policy semantics are unchanged (see the [password-permission migration guide](/compatibility/password-permissions/) when upgrading from before v3.14.0, and the [component matrix](/compatibility/versions/) for version pairings).

Behavioral notes:
- `go-jose v4.1.6` rejects RSA JWKs larger than **4096 bits**; verify identity-provider key sizes in OIDC/JWKS consumers.
- STS durations below one hour are now sent as requested rather than silently clamped by the client, so invalid short durations will be rejected by the server.

## Validation {#validation}

The release passed full lint and race suites under Go 1.27.2, race tests under Go 1.26.9, OpenLDAP integration tests, module tidiness checks, and `govulncheck` scanning (zero reachable or imported-package vulnerabilities).

Tagged-source CI runs: [Go](https://github.com/pgsty/silo-pkg/actions/runs/38743292347), [LDAP](https://github.com/pgsty/silo-pkg/actions/runs/38743292597), [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/38743292281).

[Changes since v3.14.1](https://github.com/pgsty/silo-pkg/compare/v3.14.1...v3.14.2) · [PR #10](https://github.com/pgsty/silo-pkg/pull/10).
