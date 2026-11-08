---
title: "silo-pkg 3.16: JOSE Security and Configuration Fixes"
linkTitle: "pkg 3.16.0"
date: 2026-11-08
author: "SILO"
description: "silo-pkg 3.16.0 updates JOSE and networking dependencies, fixes x86 feature detection and preserves literal YAML merge-key strings."
tags: [Release, Dependencies]
weight: 3
url: "/blog/release/pkg-3.16.0/"
---

**silo-pkg v3.16.0** is a source-only maintenance release of `github.com/pgsty/silo-pkg/v3`. It requires **Go 1.27.3** and remains API-compatible with v3.15.2. Server, Console and mcli receive the changes only after adopting this version and rebuilding; their existing release artifacts are not replaced by a library release.

## Dependency updates {#dependencies}

| Module | v3.15.2 | v3.16.0 |
| --- | --- | --- |
| `github.com/go-jose/go-jose/v4` | `v4.1.6` | `v4.1.9` |
| `golang.org/x/net` | `v0.61.0` | `v0.62.0` |
| `golang.org/x/crypto` | `v0.58.0` | `v0.58.1-0.20261009181718-2f1f834330b2` |
| `github.com/klauspost/cpuid/v2` | `v2.4.1` | `v2.4.2` |
| `go.yaml.in/yaml/v3` | `v3.0.5` | `v3.0.6` |

The JOSE update includes the five security fixes in [go-jose v4.1.7](https://github.com/go-jose/go-jose/releases/tag/v4.1.7): invalid RSA thumbprints, JSON decoding of embedded unexported fields, JWE protected/unprotected header handling, RSA certificate-verification limits, and limits on JWS signatures/JWE recipients. Version 4.1.9 also restores OpaqueSigner support for unrecognized public-key types and improves unsupported-key errors. These are dependency advisories; their applicability depends on which operations a consuming application exposes.

The networking versions were already selected by the maintained application roots. Publishing them in the shared module makes that baseline available to other consumers; it does not establish that those existing application builds were using the older versions.

The cpuid update corrects the ECX bits used to detect XSAVE and OSXSAVE on x86. The YAML encoder now quotes a literal `<<` key, so saving and reloading a configuration does not misinterpret it as a merge directive. A configuration round-trip regression covers this behavior.

## Compatibility and adoption {#compatibility}

Public package APIs, IAM policy formats, and authorization decisions remain compatible. The infraAdmin policy documentation now explicitly includes its existing batch-job permissions. The Go requirement remains 1.27.3, and the upstream `minio-go/v7` selection remains `v7.4.2-0.20261025165926-320af050c445`.

The established `go-humanize v1.0.1`, `go-runewidth v0.0.29`, and `go-systemd/v22 v22.6.0` compatibility selections are retained. Go does not inherit dependency `replace` directives: each application must keep the replacements it needs.

```sh
go get github.com/pgsty/silo-pkg/v3@v3.16.0
go mod tidy
```

Rebuild and test the consuming application with Go 1.27.3. The [component matrix](/compatibility/versions/) distinguishes separately published libraries from the versions embedded in released applications. The maintained PGSTY stack is the supported target; upstream MinIO/MC compatibility is best effort.

## Verification {#verification}

Release source: [`b7aeea85e84e`](https://github.com/pgsty/silo-pkg/commit/b7aeea85e84e8888d6ab424c7123a1297711bc3f). Validation covers full lint and race tests, LDAP integration, module verification, and the exact go-jose/coreos OIDC dependency race suites. The YAML regression fails with v3.0.5 and passes with v3.0.6. The release commit is checked by [Go](https://github.com/pgsty/silo-pkg/actions/runs/42488674109), [LDAP](https://github.com/pgsty/silo-pkg/actions/runs/42488674310), and [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/42488674390).

[GitHub release](https://github.com/pgsty/silo-pkg/releases/tag/v3.16.0) · [Changes since v3.15.2](https://github.com/pgsty/silo-pkg/compare/v3.15.2...v3.16.0)
