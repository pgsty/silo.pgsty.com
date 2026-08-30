---
title: "silo-pkg 3.13.0 Released"
linkTitle: "silo/pkg 3.13.0"
date: 2026-08-30
author: "Vonng"
description: "silo-pkg 3.13.0 takes github.com/pgsty/silo-pkg/v3 as its own module path, retires the replace-directive arrangement it depended on, and drops the Silo Go SDK fork in favour of upstream minio-go."
tags: [Release, pkg]
weight: 5
url: "/blog/release/pkg-3.13.0/"
aliases:
  - /releases/pkg-3.13.0/
---

**Release date:** 2026-08-30 · **Version:** [v3.13.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.13.0) · **Commit:** [`215f116`](https://github.com/pgsty/silo-pkg/commit/215f116ec25120ce365c79bce4096cd7665b2c1e) · **Repository:** [pgsty/silo-pkg](https://github.com/pgsty/silo-pkg)

Version 3.13.0 is a breaking release with one theme: the module stops claiming upstream's import path and takes its own. It also retires the `pgsty/silo-go` fork, which no longer carried anything upstream lacks.

> [!WARNING]
> **This package release and a SILO server release are different gates.** The package tag and GitHub Release are public. `silo`, `silo-console`, and `mcli` have **not** yet moved to the new import path; they continue to build against v3.12.2 through the old `replace` arrangement. No SILO server tag, container image, package set, deployment, or production rollout is established by this article.

## Release at a Glance {#glance}

- **Published:** the `silo-pkg v3.13.0` tag and GitHub Release, declaring `module github.com/pgsty/silo-pkg/v3`.
- **Retired:** the `github.com/minio/pkg/v3` module identity and the `replace` directive every consumer had to repeat.
- **Retired:** the `github.com/pgsty/silo-go/v7` fork; this release requires upstream `minio-go` directly.
- **Unchanged:** every package, symbol, and behaviour. Only the path they are imported from moved.
- **Not part of this release:** the matching `silo`, `silo-console`, and `mcli` migrations.

## Why the Path Moved {#why}

The fork kept upstream's `github.com/minio/pkg/v3` path so it stayed a drop-in replacement, selectable with one `replace` directive. Go does not inherit `replace` directives from dependency modules, and three costs came due while preparing the next SILO server release.

**Every consumer had to repeat the redirect, and one that forgot built against upstream silently.** A module that requires this package but omits the replacement resolves the real `minio/pkg`, compiles, and quietly loses the fork's behaviour.

**The `require` line had to name a version the source no longer matched.** `ParseConfigStrict` first appears upstream in v3.11.0, and `Resource.IsBareARN` exists in no upstream version at all. A `require github.com/minio/pkg/v3 v3.6.1` next to source that needs v3.12 APIs is metadata that cannot be made true by editing the number.

**Working around that propagated.** `pgsty/mc` carried a compile-time sentinel — a reference to `Resource.IsBareARN` — purely to turn the silent downgrade into a build failure. Raising `mc`'s floor to make its metadata honest pushed the requirement through the module graph and forced `silo-console`'s deliberately low floor upward, which is exactly what that floor existed to prevent.

Upstream's path had little to offer in return here. `minio/pkg` is a small internal library, and this module's consumers are `silo`, `silo-console`, and `mcli`. The [Silo Go SDK](/compatibility/mcli/) keeps upstream's `github.com/minio/minio-go/v7` path, where drop-in compatibility is worth having and upstream is actively maintained.

## Upstream minio-go Replaces the Silo Go SDK {#minio-go}

`pgsty/silo-go` no longer carried any functional divergence. Its one unique change, [Return CopyObject checksums in UploadInfo](https://github.com/minio/minio-go/pull/2295), was merged upstream on 2026-08-24. Everything else in the fork was a version string, a logo, a README, and a lint-tool block.

Upstream's newest tag `v7.3.0` predates that merge by 14 commits, among them [a data race fix in parallel multipart checksum hashing](https://github.com/minio/minio-go/pull/2290), so pinning the tag would be a regression. This release therefore requires the pseudo-version `v7.3.1-0.20260828014306-0e78d3f18efe` and will move to a tag when upstream cuts one.

## Compatibility {#compatibility}

Every package, exported symbol, and behaviour is unchanged. This release moves where they are imported from, nothing else.

Take it together with the matching `silo`, `silo-console`, and `mcli` changes. A consumer that upgrades alone will not build, because the old and new paths are different modules and types do not cross between them.

Before:

```go
require github.com/minio/pkg/v3 v3.6.1

replace (
    github.com/minio/pkg/v3      => github.com/pgsty/silo-pkg/v3 v3.12.2
    github.com/minio/minio-go/v7 => github.com/pgsty/silo-go/v7 v7.3.1
)
```

After:

```go
require github.com/pgsty/silo-pkg/v3 v3.13.0
```

...and rewrite `github.com/minio/pkg/v3/...` imports to `github.com/pgsty/silo-pkg/v3/...`. Consumers that stay on the old arrangement keep building against v3.12.2 and earlier, which remain published.

One consequence is worth expecting. Because the two paths are now separate modules, a build can contain both — a third-party dependency that imports `github.com/minio/pkg/v3` no longer has its import redirected. In the SILO stack this happens once, through `minio/colorjson` and `minio/dperf`, both of which reach only `pkg/v3/console`. That package's colour switch is `fatih/color`'s process-wide `NoColor`, which every copy shares, so disabling colour still disables it everywhere.

## Verification {#verification}

- `go build ./...`, `go vet ./...`, `go mod tidy -diff`, and `gofmt -l .` are clean; `go test ./...` passes 23 packages.
- CI on the release commit: [Go](https://github.com/pgsty/silo-pkg/actions/runs/33318436618), [LDAP Config Validator](https://github.com/pgsty/silo-pkg/actions/runs/33318438500), [VulnCheck](https://github.com/pgsty/silo-pkg/actions/runs/33318440453).
- The new path was resolved from the module proxy by a fresh module with no `replace` directive, which imported `policy` and ran.
- The downstream migration was validated end to end before this release: `mcli` (194 files), `silo-console` (36 files), and `silo` (181 files) all build, vet, and pass their suites. `silo`'s rebrand guard passes with a compatibility-baseline diff of exactly 19 deleted import entries and no change to environment variables, metrics, headers, routes, policy values, or exported symbols.
