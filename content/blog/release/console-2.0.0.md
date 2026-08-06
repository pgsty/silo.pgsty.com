---
title: "Silo Console 2.0.0 Released"
linkTitle: "silo/console 2.0.0"
date: 2026-08-04
author: "Ruohang Feng"
description: "The first independent major release of SILO Console: full identity and delivery migration, a redesigned login page and console UI, embedded assets cut from ~10MB to 3.5MB, zero known dependency vulnerabilities, and a batch of inherited bug fixes."
tags: [Release, console]
weight: 4
url: "/blog/release/console-2.0.0/"
aliases:
  - /releases/console-2.0.0/
---
**Published:** 2026-08-04 · **Version:** [v2.0.0](https://github.com/pgsty/silo-console/releases/tag/v2.0.0) · **Repository:** [pgsty/silo-console](https://github.com/pgsty/silo-console)

SILO Console 2.0.0 is the first major release of this object-storage administration console as an independent project. Continuing from the `georgmangold/console` v1.9.1 maintenance line, it accomplishes three things:

1. **An independent identity** — product name, visual system, documentation entry points, source attribution, and the release pipeline all move into the SILO project, while the Go module path, environment variables, and other compatibility contracts are deliberately retained;
2. **A redesigned interface** — the login page, theme system, dashboard, and console details are reworked under one design language, backed by a regenerated brand icon set;
3. **Hardened engineering** — the embedded frontend payload shrinks from roughly 10MB to 3.5MB, known dependency vulnerabilities drop to zero, and a batch of inherited defects — including a real runtime data race — is fixed.

Before publication this release went through two independent review passes: a full code review with commit-history restructuring, followed by an adversarial re-verification (exhaustive asset validation, HTTP semantics probing, full routing regression, and smoke tests against the published artifacts themselves).

{{% alert color="warning" %}}
**Read the compatibility boundary before upgrading**

The major-version change in 2.0.0 is about **public identity and delivery contracts**, not the object data format or the S3 protocol. Installation scripts that reference the old repository, binary name, or container image must be updated; existing integrations that use `CONSOLE_MINIO_SERVER`, `CONSOLE_MINIO_REGION`, `github.com/minio/console`, or the MinIO-compatible Admin API must **not** be search-and-replaced.
{{% /alert %}}

## Why 2.0.0 {#why-2-0-0}

This console originated as MinIO Console and was carried forward by the [Alevsk/console](https://github.com/Alevsk/console) and [georgmangold/console](https://github.com/georgmangold/console) community maintenance lines. SILO Console continues from there, maintained by the Pigsty community as the browser-based administration interface for [SILO](https://silo.pgsty.com/).

The version jumps from v1.9.1 to v2.0.0 because these public contracts change together:

- the product is now uniformly **SILO Console**, with the primary repository at [`pgsty/silo-console`](https://github.com/pgsty/silo-console);
- the release binary changes from `console` to `silo-console`, and the container image moves to `ghcr.io/pgsty/silo-console`;
- release assets, checksums, package metadata, CLI descriptions, and project links all switch to SILO;
- in-product identity, help entry points, copyright attribution, source offers, and trademark notices are re-established.

The migration strategy is "clear external identity, restrained internal compatibility": operators must take notice, but the underlying compatibility interfaces are not mechanically renamed.

## Naming and Delivery Contracts {#naming-and-delivery}

| Scope            | Previous name or location         | 2.0.0 contract                              |
|:-----------------|:----------------------------------|:--------------------------------------------|
| Product          | Console / legacy MinIO Console    | **SILO Console**                            |
| Repository       | `georgmangold/console`            | `pgsty/silo-console`                        |
| Release binary   | `console`                         | `silo-console`                              |
| Container image  | `ghcr.io/georgmangold/console`    | `ghcr.io/pgsty/silo-console`                |
| Binary assets    | `console-<os>-<arch>`             | `silo-console-<os>-<arch>`                  |
| Checksums        | `console_<version>_checksums.txt` | `silo-console_<version>_checksums.txt`      |
| Website and docs | upstream / previous maintainer    | `silo.pgsty.com` and `silo.pgsty.com/docs/` |

CLI authorship, usage text, and project descriptions now identify Pigsty and SILO Console. DEB/RPM/APK vendor, maintainer, homepage, description, and license metadata are updated accordingly; the executable installs to `/usr/local/bin/silo-console`.

## Deliberately Retained Compatibility Identifiers {#retained-compatibility-contracts}

The following names still contain `minio` or the old `console`, but they are interface, protocol, or installation compatibility layers — not leftover branding:

| Surface                 | State in 2.0.0                              | Reason                                      |
|:------------------------|:--------------------------------------------|:--------------------------------------------|
| Go module               | `github.com/minio/console` retained         | changing it breaks every Go import          |
| Server endpoint         | `CONSOLE_MINIO_SERVER` retained             | widely used by existing deployments         |
| Server region           | `CONSOLE_MINIO_REGION` retained             | existing compatibility contract             |
| Other configuration     | existing `CONSOLE_*` variables remain valid | avoids migration with no benefit            |
| S3/Admin API names      | MinIO-compatible fields and enums retained  | they describe the actual protocol           |
| Development build       | `make console` still produces `./console`   | keeps developer workflows working           |
| Package systemd unit    | `minio-console.service` retained            | avoids duplicate services on upgrade        |
| systemd user and config | `console-user` and `/etc/default/console`   | avoids unnecessary account/config migration |

Upgrade scripts therefore must not run repository-wide `minio → silo` or `console → silo-console` replacements. Migrating these compatibility interfaces in the future will require aliases, deprecation windows, and an explicit dual-read strategy; 2.0.0 does none of that.

## A Redesigned Interface {#redesigned-interface}

2.0.0 is not a logo swap — the interface was redesigned end to end.

### Login page {#login-page}

The login page is rewritten from scratch. The left brand panel renders a slowly drifting sine-mesh animation generated purely on Canvas (zero external dependencies, honors `prefers-reduced-motion`, pauses in background tabs), states the project's proposition — "Keep the S3 Interface / Own the Object Store" — and keeps the full MinIO trademark notice at the bottom. The right-hand form is functionally untouched, preserving every existing automation selector. The Chakra Petch typeface used by the SILO wordmark ships as a ~20KB locally bundled subset with no external requests.

### A unified theme system {#theme-system}

All console colors converge into one light/dark theme layer: neutral greys for text and borders, the brand steel blue for primary actions and selection, and a sidebar that uses the same night palette as the login panel in both modes. Controls and cards share consistent radii and transitions, inputs get a keyboard focus ring, and modals animate in (also honoring reduced motion). Server-provided `customStyles` keep full precedence.

### Console polish {#console-polish}

- **Dashboard (Metrics)**: stat cards rebuilt under one grammar — muted labels, tabular numerals, aligned status dots; charts and info strips are theme-driven; the upstream absolute-positioning layout is gone.
- **Unified empty states**: placeholder text in Watch, Trace, bucket Events/Replication/Lifecycle, and every other data panel is now centered and de-emphasized instead of raw top-left text.
- **Vertical tabs**: detail-page tabs change from bordered grey blocks to a quiet pill list, eliminating the stray empty cell at the bottom of the rail.
- **License page**: a new VERSION section shows both the connected server's release and the Console's own version; accounts without `admin:ServerInfo` never issue the request and the row stays hidden. The page also consolidates AGPLv3 licensing, the AGPL section-13 source offer, lineage, and trademark boundaries.
- **A batch of interaction fixes**: the sidebar now collapses on initial load at mobile widths (previously it waited for a resize event); the bottom navigation no longer lags window-height changes; the bucket accordion highlight spans the full row; the dashboard no longer overflows horizontally on narrow screens; and the help panel is now truly lazy — the login page makes no external requests at all.

### Brand icon set {#brand-icons}

The favicon, PWA, and Apple Touch icons still carried a previous-generation hand-drawn emblem. 2.0.0 re-rasterizes every size (ico 16+32, favicon 16/32/96, apple 180, manifest 192/512) from the official `silo.svg` vector emblem, with safe-area margins on home-screen sizes, and trims the Web App Manifest to the modern icon set, dropping the 2014-era legacy density entries. The icon payload drops from 473KB to 160KB, and the browser tab icon finally matches the in-product brand.

## Smaller and Faster {#smaller-and-faster}

Embedded delivery is this console's core form factor — the frontend ships inside the binary via `go:embed`. 2.0.0 optimizes that path systematically:

- **Embedded payload: ~9.6MB → 3.5MB.** Text assets (JS/CSS/SVG/…) are precompressed at build time with deterministic gzip and embedded compressed-only; legacy WOFF fonts (~1.25MB that no supported browser ever downloads) and a set of entirely unreferenced orphan images are removed.
- **First-load transfer: ~5.7MB → ~1.7MB.** Static assets previously shipped uncompressed on the wire; they are now emitted directly with `Content-Encoding: gzip` at zero runtime cost, with on-the-fly decompression for the rare client that does not accept gzip.
- **Correct HTTP semantics.** Accept-Encoding is parsed with full RFC 9110 q-values (`gzip;q=0` gets identity bytes), responses carry `Vary: Accept-Encoding`, and non-GET/HEAD requests to static paths and the SPA entry receive 405 with an `Allow` header.
- **Reproducible builds.** Compression uses a pure-JS implementation (fflate) for byte-identical output across platforms, and the release pipeline enforces a hard gate: rebuilding the embedded assets in a clean environment must produce zero diff against the commit.

Release binaries (all frontend assets included, stripped) weigh roughly 35–40MB; for the downstream SILO server, embedding this console now costs about 3.5MB instead of about 10MB.

## Security and Dependencies {#security-and-dependencies}

**Go:** the build baseline moves to Go 1.26.5 and the `golang.org/x` family is fully refreshed. Every reachable vulnerability reported by `govulncheck` is resolved:

| Dependency                         | Fixed version | Advisories                                                   |
|:-----------------------------------|:--------------|:-------------------------------------------------------------|
| `google.golang.org/grpc`           | v1.82.1       | GO-2026-6061                                                 |
| `github.com/prometheus/prometheus` | v0.311.3      | GO-2026-5710 / -5662 / -5381 / -5264 (incl. remote-read DoS) |
| `github.com/klauspost/compress`    | v1.18.7       | GO-2026-5841                                                 |

The single remaining advisory sits in `golang.org/x/crypto`, has no upstream fix yet, and is unreachable from this codebase; it is tracked as a known item.

**Frontend:** the full dependency-tree audit (production and tooling) is clean, covering the high-severity `form-data` CRLF injection and the DOMPurify and qs advisories; React Router is migrated to 7.18.2 (keeping the v6-compatible declarative API, with full routing regression). The only explicitly ignored advisory affects an unstable API this project does not use.

**Runtime correctness:** a real data race between HTTP log-target initialization and shutdown is fixed, along with shared-mock races in the test suite; supported Go packages pass `-race` across the board. As a side benefit, the `go-m1cpu` upgrade fixes the local `go run` cgo crash on recent macOS.

## Update Checks and Default Network Behavior {#updates-and-network-behavior}

This release keeps conservative defaults for upgrade tooling:

- automatic self-update in `silo-console update` is disabled — the command prints guidance and never downloads or replaces the binary;
- the release catalog gains `SILO_RELEASE_SERVICE_HOST`, with the previous `RELEASE_SERVICE_HOST` as a compatibility fallback; with neither set, no remote release service is contacted;
- the help panel's blog content loads only when opened, and its links accept `https://silo.pgsty.com` exclusively.

Automatic updates will be reconsidered once signed release assets and a tested rollback path are in place.

## Release Artifacts and Platform Matrix {#release-artifacts}

The release ships 16 assets:

| Type              | Coverage                                                        |
|:------------------|:----------------------------------------------------------------|
| Standalone binary | Linux `amd64/arm64/arm`, macOS `amd64/arm64`, Windows `amd64`   |
| System packages   | DEB / RPM / APK × `amd64/arm64/armv6`                           |
| Checksums         | `silo-console_2.0.0_checksums.txt` (SHA-256)                    |

The pipeline triggers on tag pushes, pins third-party Actions to commit SHAs, and enforces the clean-checkout and zero-diff asset-rebuild gates before GoReleaser runs.

## Upgrade Guide {#upgrade-guide}

### Standalone binary {#upgrade-binary}

```bash
install -m 0755 silo-console-linux-amd64 /usr/local/bin/silo-console
/usr/local/bin/silo-console server
```

When building from source, `make console` still produces `./console`; install it under the release name before wiring it into a production service.

### DEB/RPM/APK and systemd {#upgrade-packages}

Packages continue to install `/etc/systemd/system/minio-console.service`, whose unit starts `/usr/local/bin/silo-console`. `EnvironmentFile=/etc/default/console`, `console-user`, and existing `CONSOLE_*` variables are unchanged. This retention lets package upgrades keep acting on the existing service instead of creating a parallel one.

### Configuration and integrations {#upgrade-configuration}

- do not rename `CONSOLE_MINIO_SERVER` or `CONSOLE_MINIO_REGION`;
- do not touch `github.com/minio/console` in Go imports;
- prefer `SILO_RELEASE_SERVICE_HOST` for self-hosted release catalogs;
- replace any reliance on `console update` with explicit download, verification, and deployment;
- update process-path-based monitoring to `/usr/local/bin/silo-console`.

This release does not change the object data layout and requires no bucket or object migration.

## Dual Review and Validation Scope {#review-and-validation}

2.0.0 went through two independent review passes before publication. The first pass performed a full code review, fixed the defects described above, restructured 13 intermediate commits into 8 logical ones, and ran Go `-race` across supported packages, `go vet`, `golangci-lint`, `govulncheck`, frontend type checks, production builds, Prettier, dead-code checks, and the full dependency audit. The second, adversarial pass independently re-ran the core gates and added:

- all 184 embedded files fetched three ways each (gzip client, identity client, HEAD) with per-file hash comparison against the embedded sources;
- RFC semantics probes (including combined q-values such as `gzip;q=0, *;q=0.5`), method restrictions, the OIDC callback, and SPA deep links;
- full React Router 7 regression: deep links, client-side navigation, bucket-detail tab switching, and browser history back;
- mobile first-load sidebar behavior, login-page external-request monitoring, and light/dark full-site tours;
- downloaded release assets verified byte-for-byte against checksums, binary self-reported version confirmed, and a smoke test of the published binary against a live server;
- zero-diff asset rebuilds confirmed on both macOS and Linux.

The complete pre-rewrite history is preserved in backup refs for rollback.

## Known Limitations {#known-limitations}

- automatic self-update is disabled; upgrades are explicit;
- the SSO end-to-end suite requires an external OpenLDAP/Dex/MinIO topology and was not run in that environment this cycle (the OIDC code paths are covered by unit tests and HTTP-level checks);
- one `golang.org/x/crypto` advisory has no upstream fix yet and is unreachable from this codebase;
- SILO does not yet maintain its own video library; videos in the help panel are clearly labeled upstream compatibility material;
- administrative features depend on the MinIO-compatible Admin API — SILO Console is not a generic browser for arbitrary S3 services;
- retained Go module paths, environment variables, protocol fields, and the systemd unit name still appear in code, configuration, and process listings.

## Related Commits and Links {#related-links}

The complete v2.0.0 change set consists of 8 logical commits:

- [`50797de`](https://github.com/pgsty/silo-console/commit/50797de) — feat: establish SILO Console identity and compatibility
- [`23ae6e8`](https://github.com/pgsty/silo-console/commit/23ae6e8) — feat: redesign and harden the SILO Console web app
- [`7a83a77`](https://github.com/pgsty/silo-console/commit/7a83a77) — build: update Go toolchain and dependencies
- [`1330d25`](https://github.com/pgsty/silo-console/commit/1330d25) — fix: eliminate logger shutdown and test mock races
- [`06b3a34`](https://github.com/pgsty/silo-console/commit/06b3a34) — docs: publish the SILO Console v2.0.0 guide
- [`4b24372`](https://github.com/pgsty/silo-console/commit/4b24372) — build: regenerate optimized embedded web assets
- [`c38eb64`](https://github.com/pgsty/silo-console/commit/c38eb64) — ci: package and publish SILO Console v2 releases
- [`b952a12`](https://github.com/pgsty/silo-console/commit/b952a12) — brand: regenerate the icon set from the official silo.svg emblem

Links:

- [SILO Console source](https://github.com/pgsty/silo-console) · [Releases](https://github.com/pgsty/silo-console/releases)
- [SILO website](https://silo.pgsty.com/) · [Documentation](https://silo.pgsty.com/docs/)
- [Licensing](https://silo.pgsty.com/about/license/) · [Attribution](https://silo.pgsty.com/about/attribution/) · [Trademark](https://silo.pgsty.com/about/trademark/)
