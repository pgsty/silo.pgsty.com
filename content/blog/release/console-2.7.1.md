---
title: "SILO Console 2.7.1: Service-Account Policy Inheritance and Strict Validation"
linkTitle: "Console 2.7.1"
date: 2026-11-12T03:00:00+08:00
author: "SILO"
description: "Console 2.7.1 preserves service-account policy inheritance on metadata edits, blocks empty inline-policy variants, surfaces save errors inside the edit modal, and adopts Go 1.27.4, silo-pkg 3.16.1, and mcli 20261112."
tags: [Release, Security, Console]
draft: false
weight: 1
url: "/blog/release/console-2.7.1/"
---

**SILO Console 2.7.1 is released**, following [2.7.0](/blog/release/console-2.7.0/). Tag: [`v2.7.1`](https://github.com/pgsty/silo-console/releases/tag/v2.7.1); source: [`3825ebc44451`](https://github.com/pgsty/silo-console/commit/3825ebc44451fdc8eefda3d4ec523a79dfecb236). This is a standalone Console release; published [SILO Server 20261109](/blog/release/silo-20261109/) continues to embed Console 2.7.0 until the next Server release is published.

[GitHub release](https://github.com/pgsty/silo-console/releases/tag/v2.7.1) · [Compatibility notes](/compatibility/console/#release-271) · [SN-2026-025 chronicle](/blog/security/20261111-iam-import-status-and-console-policy/) · [Downloads](/download/#console)

## Service-account policy inheritance (`SN-2026-025`) {#policy-inheritance}

- **Separate inherited vs. inline policy tracking (`1be8a74bf`):** Console previously populated the service-account editor with the parent user's effective policy and resubmitted that document during metadata or status saves (`silo-console#89`). Editing an inherited key's name, description, expiry, or enabled state froze the parent policy into a static inline policy and failed whenever the parent policy exceeded the 4 KiB inline session-policy limit (blocking even emergency disable actions). Console 2.7.1 tracks inheritance explicitly and omits `policy` on metadata-only saves when neither the toggle nor the inline document changed.
- **Explicit reset to inheritance:** turning off **Restrict beyond user policy** sends an explicit empty policy (`{}`) so a repaired SILO Server ([post-`20261109` candidate](/compatibility/server/#candidate-after-20261109)) removes the stored inline restriction and restores parent inheritance.
- **Empty inline-policy guard & modal error feedback (`a1a84cab4`, `1fdb279fd`, `3825ebc44`):** while **Restrict beyond user policy** remains enabled, creating or replacing a policy rejects an empty editor, `{}`, `{"Statement":[]}`, `{"Statement":null}`, and backend-accepted case-insensitive, Unicode-folded, or duplicate-key empty variants. Unchanged historical empty inline policies can still save metadata-only edits without altering permissions. Save errors render directly inside the edit modal instead of failing behind the dialog.

## Strict policy JSON validation, HTTPS redirects, and dependencies {#dependencies}

- **Backend policy validation (`3825ebc44`):** Console API endpoints enforce strict JSON policy decoding aligned with [silo-pkg v3.16.1](/blog/release/pkg-3.16.1/), rejecting unknown fields, trailing JSON tokens, non-object payloads, empty `Principal: {}` / unsupported `NotPrincipal` blocks, and empty named policies.
- **HTTPS redirect host preservation (`3825ebc44`):** when TLS redirect is active (`CONSOLE_SECURE_TLS_REDIRECT=on`), HTTP-to-HTTPS browser redirects preserve the incoming request host and configured TLS port when `CONSOLE_SECURE_TLS_HOST` is unset (instead of redirecting wildcard binds such as `--host 0.0.0.0` or `[::]` to `https://0.0.0.0:<tls-port>`), and enforce `CONSOLE_SECURE_TLS_HOST` over `X-Forwarded-Host` when set, paired with `github.com/unrolled/secure v1.18.0`.
- **Toolchain and pinned stack:** built with **Go `1.27.4`**, `github.com/pgsty/silo-pkg/v3 v3.16.1`, and `pgsty/mc RELEASE.2026-11-12T00-00-00Z` ([mcli 20261112](/blog/release/mcli-20261112/), `v0.0.0-20261111180825-a37a9f054fba`), verified against the Go proxy, checksum database, and immutable GitHub release metadata.

**Upgrade note:** standalone Console `v2.7.1` protects metadata-only edits immediately; explicit reset-to-inheritance (`policy: "{}"`) requires the matching post-`20261109` SILO Server update. Stop older `console usage-worker` processes before starting `2.7.1` workers when upgrading from pre-`2.7.0` deployments.

## Verification and delivery {#verification}

- [Required matrix](https://github.com/pgsty/silo-console/actions/runs/43076284524) · [Required vulnerability checks](https://github.com/pgsty/silo-console/actions/runs/43076283437) · [Tag release and artifact verification](https://github.com/pgsty/silo-console/actions/runs/43083874312) · [Latest image promotion](https://github.com/pgsty/silo-console/actions/runs/43085474259)
- Image: `docker.io/pgsty/silo-console:v2.7.1` and `docker.io/pgsty/silo-console:latest` (`linux/amd64`, `linux/arm64`), manifest digest `sha256:2afef06f8505eadb24d657acd0f68c78bce8b148b1d9b74981454560fa3b055f`.
- GitHub Release ships 44 verified assets (six platform executables and archives, nine Linux RPM/DEB/APK packages, source archive, SPDX SBOMs, legal notices, and a Cosign-signed SHA-256 manifest with GitHub provenance).
