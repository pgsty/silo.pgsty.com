---
title: "Component Versions"
linkTitle: "Component Versions"
description: "Published SILO releases, the September 13 source graph, and coordinated upgrade order."
url: "/compatibility/versions/"
weight: 5
type: docs
page_width: wide
icon: fa-solid fa-code-branch
---

**Verified on 2026-09-13.** SILO releases its four components independently.
A merged dependency update does not change an existing binary or image.

## Published components {#published}

| Component | Latest published version | What it contains |
| --- | --- | --- |
| Server | <a href="https://github.com/pgsty/silo/releases/tag/RELEASE.2026-09-03T13-18-01Z" style="white-space:nowrap">20260903</a> | pkg v3.13.2; upstream SDK `0e78d3f18efe`; mcli 20260903; embedded Console source `464a59d73ada` with v2.3.0 version identity |
| <span style="white-space:nowrap">Standalone<br>Console</span> | [v2.4.0](https://github.com/pgsty/silo-console/releases/tag/v2.4.0) | pkg v3.13.3; MC source `c8aa5d25a63a`; upstream SDK `0e78d3f18efe`; bounded object-browser pages |
| mcli | <a href="https://github.com/pgsty/mc/releases/tag/RELEASE.2026-09-13T00-00-00Z" style="white-space:nowrap">20260913</a> | pkg v3.14.0; upstream SDK `60bd07042d49`; package version `20260913000000.0.0` |
| Shared pkg | [v3.14.0](https://github.com/pgsty/silo-pkg/releases/tag/v3.14.0) | Own module path `github.com/pgsty/silo-pkg/v3`; password-capability split; upstream SDK `60bd07042d49` |

Release notes: [Server 20260903](/blog/release/silo-20260903/),
[Console v2.4.0](/blog/release/console-2.4.0/),
[mcli 20260913](/blog/release/mcli-20260913/), [pkg v3.14.0](/blog/release/pkg-3.14.0/).
The published Server image still bundles its original client and Console.
Installing a standalone update does not replace those embedded components.
Package-repository mirrors may lag GitHub; the [download page](/download/)
links directly to the published artifacts.

## Coordinated source on main {#source}

The September 13 refresh landed as [pkg #7](https://github.com/pgsty/silo-pkg/pull/7),
[MC #42](https://github.com/pgsty/mc/pull/42),
[Console #53](https://github.com/pgsty/silo-console/pull/53) and [#54](https://github.com/pgsty/silo-console/pull/54),
and [Server #181](https://github.com/pgsty/silo/pull/181).

- **pkg:** `v3.14.0` → `827f8109ff11bf6239a35d8d6d137cb5738539c3`.
- **MC:** `v0.0.0-20260913012246-4f609a4da3bb` → the published 20260913 tag.
- **Console selected by Server:** `v0.0.0-20260913015128-417559bb2c97`; accepted on main by merge `449c185a8d14` with the same tree.
- **Server integration:** `5d955b5b7444f8a3ab550ce92713607998f89c0d`.
- **Upstream minio-go:** `v7.3.1-0.20260910142817-60bd07042d49`.

**Server and Console changes after their latest tags remain unreleased.** This
includes the [password-permission split](/compatibility/password-permissions/),
Console streaming ZIP downloads and its revised image-promotion gate, and
Server's later storage, replication and signed-header fixes. Server main now
builds curl 8.22.0 and bundles mcli 20260913; existing Server images retain their
published contents. The [Server changelog](https://github.com/pgsty/silo/blob/main/CHANGELOG.md)
and [Console changelog](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)
separate those changes from published releases.

The latest published Server is affected by [SN-2026-011](/blog/security/20260913-signed-header-status/).
Its fix is on main; upgrading only pkg, mcli or standalone Console does not patch
an installed Server. Source validation and vulnerability scans do not establish
that a fixed Server binary has been published.

## Dependency and release order {#order}

1. Verify the upstream SDK commit and required fixes. Keep the upstream
   `github.com/minio/minio-go/v7` path; the retired `silo-go` fork is not part of
   the maintained graph.
2. Validate and publish pkg under `github.com/pgsty/silo-pkg/v3`, including its
   migration notes. Resolve the tag through the Go proxy and checksum database.
3. Update MC to that pkg and SDK, validate it, then publish the calendar-tagged
   mcli release. Go consumers select its canonical pseudo-version.
4. Update Console's direct pkg requirement and explicit MC replacement, validate
   its embedded frontend and integration, and publish Console when a release is
   intended. An accepted immutable source commit can also be selected explicitly.
5. Update Server's direct pkg/SDK requirements and both PGSTY replacements,
   client archive hashes, image and Helm client pins. Validate the complete graph
   before a separate Server release, image publication and cluster rollout.

Go does not inherit a dependency module's `replace` directives. Server must
explicitly select both maintained Console and MC even when Console already
selects MC. Console and MC retain their historical MinIO module paths; pkg uses
its own path directly. Legacy transitive `minio/pkg/v3` from `colorjson`/`dperf`
is separate from the maintained policy implementation.

The main stack uses Go **1.27.1**; pkg retains a Go **1.26** library floor and
was also race-tested with Go **1.26.8**. The Go x/* dependencies were refreshed.
The effective go-systemd version stays **v22.6.0** because v22.7.0 fails to compile
on NetBSD; Console's tablewriter **v0.0.5** replacement preserves its MC API.
These are documented compatibility pins, not missed automatic upgrades.

Other dependencies change for concrete CVE/bug fixes, not just newer major
versions. The September 13 Go scans found no reachable or imported vulnerable
package, but retained module-only **GO-2026-5932** in unused OpenPGP code. A clean
reachability result is not a claim that every selected module is advisory-free.

The supported integration target is the coordinated PGSTY stack. Compatibility
with unmodified upstream MinIO/MC and other S3 implementations is best effort.
