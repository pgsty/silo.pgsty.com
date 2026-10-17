---
title: "SILO Console 2.4.1 Released"
linkTitle: "SILO Console 2.4.1 Released"
date: 2026-09-16T16:36:03+08:00
author: "Vonng"
description: "Restricted shared downloads, password-permission migration, streaming ZIPs, refreshed dependencies and verifiable release artifacts."
tags: [Release, console]
weight: 1
url: "/blog/release/console-2.4.1/"
---

[SILO Console v2.4.1](https://github.com/pgsty/silo-console/releases/tag/v2.4.1)
was released on September 16, 2026 from
[`1360e26d976d`](https://github.com/pgsty/silo-console/commit/1360e26d976d82eda395b0b2e449df8c9d49f39c).
It integrates pkg v3.14.1 and mcli 20260916, restricts the anonymous sharing proxy,
streams multi-object ZIP downloads and adds signed, traceable release artifacts.

## Shared downloads {#sharing}

The fix for [#52](https://github.com/pgsty/silo-console/issues/52) restricts the
anonymous proxy to **object-content GET requests at the configured S3 origin**.
It rejects redirects, system paths and query-selected operations that are not
object downloads. Public objects, presigned links and version-specific downloads
continue to work. **No new sharing-disable environment variable is needed.**

Thanks to [Jiri Pejchal (@jiri-pejchal)](https://github.com/jiri-pejchal) for
reporting the internal-metrics exposure. See the
[sharing boundary](/reference/minio-server/settings/console/#object-sharing)
for the supported request forms and reverse-proxy requirements.

## Password-policy migration {#passwords}

**This patch release includes an authorization change.** The Change Password
button and session capability use `admin:ChangeMyPassword`; creating users and
resetting another user's password continue to use `admin:CreateUser`.
With the matching SILO Server, denying CreateUser alone no longer locks the
caller's own password. To retain that restriction, deny **both actions in the
same statement before upgrading**, keeping its original scope and conditions.

The updated built-in `readonly` permits self-service password changes and no
longer overrides a separate CreateUser Allow. Saved policy overrides retain
their stored statements. Upgrade Server, Console and pkg together and review
the [migration and rollback guide](/compatibility/password-permissions/).

## Downloads and browser recovery {#browser}

- Multi-selection ZIP downloads stream to a file writer when the browser
  supports it, with backpressure, cancellation and duplicate-transfer protection.
  Other browsers hand the download to their native download manager. Neither
  path buffers the complete ZIP in JavaScript.
- Progress uses a percentage only when the response supplies a reliable total.
  The native fallback identifies the handoff explicitly; cancellation then
  belongs to the browser's download manager. Selections over 5 GiB or with an
  unknown total recommend mcli for long-running transfers.
- Invalid routes and rendering failures offer recovery without clearing
  preferences. English and Chinese labels, icon controls, sign-out text and
  keyboard-accessible tooltips are completed.

## Dependencies and embedding {#dependencies}

| Component | Selected version |
| --- | --- |
| Shared package | `github.com/pgsty/silo-pkg/v3 v3.14.1` |
| MC source | `github.com/pgsty/mc v0.0.0-20260916070421-e952aa78f10a` — mcli 20260916 |
| Upstream minio-go | `v7.3.1-0.20260915093545-32e1f32cb176` |
| JWX / strfmt | v3.3.0 / v0.27.2 |
| React Router | v7.18.4 |
| Build tools | Go 1.27.1, Node 24.21.0, Yarn 4.13.0 |

The SDK handles S3 errors embedded in HTTP 200 CopyObject responses; JWX fixes
custom JSON field-name escaping and strfmt updates hostname validation for Go
1.27. The embedded frontend and third-party credits are regenerated from this
dependency graph. go-systemd v22.6.0 and tablewriter v0.0.5 remain intentional
compatibility pins.

Go embedders select Console as
`github.com/pgsty/silo-console v0.0.0-20260916075814-1360e26d976d` through the
historical `github.com/minio/console` module replacement. Go does not inherit
dependency replacements: copy the explicit MC replacement from the
[tagged README](https://github.com/pgsty/silo-console/blob/v2.4.1/README.md).
The supported administration target is the coordinated SILO stack; upstream
MinIO/MC compatibility is best effort.

## Packages and verification {#delivery}

The [GitHub Release](https://github.com/pgsty/silo-console/releases/tag/v2.4.1) contains **44 assets**: binaries and bundles, DEB/RPM/APK packages, source, legal notices, SPDX SBOMs, a checksum manifest and its Sigstore bundle. Checksums use Cosign signatures, and provenance records the tagged workflow inputs.

**Container delivery correction, 2026-09-17:** the official image name is [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console), but anonymous token requests returned HTTP 401. Public pulls of v2.4.1 or `latest` are not confirmed. Use the GitHub binaries/packages; source and binary publication do not establish image delivery. This standalone image limitation does not affect Server embedding.

Linux packages retain `minio-console.service`, `console-user` and
`/etc/default/console`. The service now uses `/var/lib/silo-console` for state,
`/etc/silo-console/certs` for certificates, and a 90-second shutdown limit.
**Before restarting an existing installation**, migrate certificates with the
documented ownership or retain the old path through `CONSOLE_OPTS`. The installer
preserves old certificates and keys and does not restart the service for you.
See the [package upgrade instructions](https://github.com/pgsty/silo-console/blob/6a1802261c6a6f6972b42f347d8d4420ad5d1248/systemd/README.md#upgrading-an-installation-with-existing-certificates).

The exact release source passed the [complete CI matrix](https://github.com/pgsty/silo-console/actions/runs/35071257392),
[vulnerability checks](https://github.com/pgsty/silo-console/actions/runs/35071257306)
and [release verification](https://github.com/pgsty/silo-console/actions/runs/35073117397).
Local validation also covered 251 frontend unit tests, 51 browser tests,
byte-identical embedded assets and sharing in standalone and embedded deployments.
The downloaded Darwin/arm64 executable was independently checked against the
signed checksum manifest and exercised against a SILO test server.
