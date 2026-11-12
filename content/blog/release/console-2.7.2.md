---
title: "SILO Console 2.7.2: Coordinated SILO 20261112 Embedding and Release Sync"
linkTitle: "Console 2.7.2"
date: 2026-11-12T12:00:00+08:00
author: "SILO"
description: "Console 2.7.2 synchronizes embedded release metadata, embedding documentation, and optimized web assets for coordinated SILO Server 20261112 delivery, carrying forward all 2.7.1 service-account policy inheritance, strict JSON validation, and HTTPS redirect repairs."
tags: [Release, Console, SILO]
draft: false
weight: 1
url: "/blog/release/console-2.7.2/"
---

**SILO Console 2.7.2 is released**, following [2.7.1](/blog/release/console-2.7.1/), as both the standalone Console release and the embedded Console shipped inside **[SILO Server 20261112](/blog/release/silo-20261112/)**. Tag: [`v2.7.2`](https://github.com/pgsty/silo-console/releases/tag/v2.7.2); source: [`0e7953ff59c4`](https://github.com/pgsty/silo-console/commit/0e7953ff59c4a1eb77c7d203b265e6783ff18d01).

[GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.7.2) · [SILO 20261112 release notes](/blog/release/silo-20261112/) · [Compatibility notes](/compatibility/console/#release-272) · [Downloads](/download/#console)

## Coordinated embedding and release metadata {#overview}

- **Embedded version and asset sync (`0e7953ff5`):** aligns `web-app/package.json`, `web-app/src/version.tsx` (`2.7.2`), `CHANGELOG.md`, `README.md`, `README_ZH.md`, `docs/Embedding.md`, and `docs/README.md`, and rebuilds the optimized embedded web bundle with Node `24.22.1` so both standalone `silo-console` `v2.7.2` and [SILO Server 20261112](/blog/release/silo-20261112/) (`v0.0.0-20261112031746-0e7953ff59c4`) report identical release metadata.
- **Complete 2.7.1 policy and TLS hardening included:** carries forward [Console 2.7.1](/blog/release/console-2.7.1/)'s tri-state service-account inline-policy editor (`SN-2026-025`, preserving dynamic parent-policy inheritance on metadata/status edits, sending explicit `{}` only when **Restrict beyond user policy** is turned off, blocking case-insensitive/Unicode-folded/duplicate-key empty inline variants, and rendering save errors inside the edit modal), strict backend IAM and bucket policy JSON decoding, and `--host 0.0.0.0` / `CONSOLE_SECURE_TLS_HOST` HTTP-to-HTTPS redirect host preservation (`github.com/unrolled/secure v1.18.0`).
- **Toolchain and pinned stack:** built with **Go `1.27.4`**, [silo-pkg v3.16.1](/blog/release/pkg-3.16.1/) (`433f7eefa714`), and [mcli 20261112](/blog/release/mcli-20261112/) (`RELEASE.2026-11-12T00-00-00Z`, `v0.0.0-20261111180825-a37a9f054fba`), verified against the Go module proxy, checksum database, and immutable GitHub release metadata.

**Upgrade note:** upgrading to [SILO Server 20261112](/blog/release/silo-20261112/) updates the embedded Console to `v2.7.2` and enables end-to-end explicit inline-policy reset (`policy: "{}"`). Standalone Console deployments may upgrade directly to `v2.7.2`; when upgrading `console usage-worker` from pre-`2.7.0` builds, stop older worker processes before starting `2.7.2` workers.

## Verification and delivery {#verification}

- [Required matrix](https://github.com/pgsty/silo-console/actions/runs/43147244513) · [Required vulnerability checks](https://github.com/pgsty/silo-console/actions/runs/43147244552) · [Tag release and artifact verification](https://github.com/pgsty/silo-console/actions/runs/43152386737) · [Latest image promotion](https://github.com/pgsty/silo-console/actions/runs/43153492710)
- Image: `docker.io/pgsty/silo-console:v2.7.2` and `docker.io/pgsty/silo-console:latest` (`linux/amd64`, `linux/arm64`), manifest digest `sha256:41ea21e782475e230fc19f59da6c96373387da2974c3cffea0bd4eebf604cb47`.
- GitHub Release ships 44 verified assets (six platform executables and archives, nine Linux RPM/DEB/APK packages, source archive, SPDX SBOMs, legal notices, and a Cosign-signed SHA-256 manifest with GitHub provenance).
