---
title: "silo-pkg 3.16.1: Strict Policy JSON Decoding and Go 1.27.4"
linkTitle: "pkg 3.16.1"
date: 2026-11-12T02:00:00+08:00
author: "SILO"
description: "silo-pkg 3.16.1 enforces strict JSON policy decoding across IAM and bucket policies and updates the Go 1.27.4 dependency baseline."
tags: [Release, Security, Dependencies]
weight: 3
url: "/blog/release/pkg-3.16.1/"
---

**silo-pkg v3.16.1** is a source-only maintenance and security-hardening release of `github.com/pgsty/silo-pkg/v3`, following [v3.16.0](/blog/release/pkg-3.16.0/). It requires **Go 1.27.4** and preserves public package APIs and valid policy semantics. Standalone [Console 2.7.1](/blog/release/console-2.7.1/) and [mcli 20261112](/blog/release/mcli-20261112/) adopt `v3.16.1`; published [SILO Server 20261109](/blog/release/silo-20261109/) and earlier application artifacts retain their original dependency versions until rebuilt.

## Strict policy JSON decoding {#policy-decoding}

`policy.ParseConfigStrict` and `policy.ParseBucketPolicyConfig` now reject:

- non-object JSON documents (such as top-level `null`, arrays, strings, numbers, or booleans);
- trailing JSON tokens or concatenated documents after the root object;
- unknown top-level, statement, or principal fields (including unsupported `NotPrincipal` entries and empty `Principal: {}` objects).

Previously, custom `UnmarshalJSON` methods on policy types could allow misspelled fields such as `Statements` or `Conditions` to bypass `json.Decoder.DisallowUnknownFields()`, silently turning malformed documents into empty policies or dropping condition blocks. Legitimate empty policy documents (`{}` or `{"Statement":[]}`) remain distinguishable via `ParseConfigStrictAllowEmpty` for explicit service-account inline-policy resets while `ParseConfigStrict` continues to reject empty policies on named-policy and account-creation paths.

## Toolchain and dependency updates {#dependencies}

| Module / Toolchain                          | v3.16.0   | v3.16.1   |
| ------------------------------------------- | --------- | --------- |
| Go toolchain                                | `1.27.3`  | `1.27.4`  |
| `golang.org/x/sys`                          | `v0.49.0` | `v0.50.0` |
| `golang.org/x/term`                         | `v0.47.0` | `v0.48.0` |
| `golang.org/x/text`                         | `v0.43.0` | `v0.44.0` |
| `golang.org/x/oauth2`                       | `v0.37.0` | `v0.38.0` |
| `github.com/grpc-ecosystem/grpc-gateway/v2` | `v2.32.0` | `v2.33.0` |
| `google.golang.org/grpc`                    | `v1.84.0` | `v1.85.0` |
| `github.com/dustin/go-humanize`             | `v1.0.1`  | `v1.1.0`  |
{.wide .expand}

The verified `golang.org/x/crypto` (`2f1f834330b2`), `github.com/minio/minio-go/v7` (`320af050c445`), `go-runewidth v0.0.29`, and `go-systemd/v22 v22.6.0` (NetBSD portability) selections remain unchanged. Remember that Go modules do not propagate `replace` directives to downstream consumers.

```sh
go get github.com/pgsty/silo-pkg/v3@v3.16.1
go mod tidy
```

Rebuild and test consuming applications with Go 1.27.4. See the [component matrix](/compatibility/versions/) for version boundaries across the maintained PGSTY stack.

## Verification {#verification}

Release source: [`433f7eefa714`](https://github.com/pgsty/silo-pkg/commit/433f7eefa714a30b72ca70c4dffcd5faca25804f). Validation covers full lint and `-race` test suites (including strict JSON, `NotPrincipal`, and empty-principal regression cases), live LDAP integration, `go mod verify`, and `govulncheck ./...`. Checked by [Go CI](https://github.com/pgsty/silo-pkg/actions/runs/43073526147), [LDAP CI](https://github.com/pgsty/silo-pkg/actions/runs/43073526280), and [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/43073526772).

[GitHub release](https://github.com/pgsty/silo-pkg/releases/tag/v3.16.1) · [Changes since v3.16.0](https://github.com/pgsty/silo-pkg/compare/v3.16.0...v3.16.1)
