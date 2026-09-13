---
title: "Console Compatibility Notes"
linkTitle: "Console"
description: "Differences between SILO Console and the upstream MinIO Console"
url: "/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> **Latest published:** [Console v2.4.0](/blog/release/console-2.4.0/) (2026-09-08). Object pagination is released; streaming ZIPs, the password split and revised publication flow remain on main. Embedded and standalone versions differ; see the [component matrix](/compatibility/versions/).

SILO Console is Silo's build of the MinIO Console. This page records where the two are interchangeable and where they differ.

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) continues the upstream `minio/console` history from its final commit, [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563) (2026-04-16); the rebrand begins at `50797deb` (2026-08-04). The upstream repository is no longer published — `github.com/minio/console` now returns 404, where `minio/mc` was merely archived — so the source lineage survives only in this fork. The Go module path still resolves, because the module proxy continues to serve the versions it already cached. Earlier release records: [v2.0.0](/blog/release/console-2.0.0/), [v2.1.0](/blog/release/console-2.1.0/), [v2.1.1], [v2.2.0](/blog/release/console-2.2.0/), and [v2.2.1].

## Principles {#principles}

The fork follows the same rule as the rest of Silo: **the shipped artifact and its channels are renamed; the interfaces other software depends on are not.**

- **Renamed** — the artifact on disk (`silo-console`), the product identity in the interface and in `--version`, the distribution channels, and the signing keys.
- **Unchanged** — the Go module path `github.com/minio/console`, every `CONSOLE_*` environment variable (including `CONSOLE_MINIO_SERVER` and `CONSOLE_MINIO_REGION`), the REST API shapes the web application calls, and the packaging identifiers `minio-console.service`, `console-user`, and `/etc/default/console`, so an in-place package upgrade keeps working.
- **Severed** — automatic self-update, telemetry, analytics, beacons, external scripts and fonts, and call-home. A release catalog is contacted only when one is explicitly configured, through `SILO_RELEASE_SERVICE_HOST` with `RELEASE_SERVICE_HOST` retained as a fallback.
- **Preserved** — upstream copyright and the AGPL-3.0 license. Runtime output credits both MinIO, Inc. and PGSTY.

> [!NOTE]
> SILO Console is not a generic S3 browser. Its administrative features need the MinIO-compatible administration APIs that Silo implements in addition to the S3 API.

## What changed {#changed}

### 1. The full administration console is retained {#scope}

This is the largest functional difference, and it runs opposite to the usual direction of a fork. Upstream reduced its community console to an object browser. SILO Console keeps the complete administrative interface: dashboards, health, logs, diagnostics, and speed tests; bucket, object, lifecycle, replication, notification, and tier management; users, groups, service accounts, policies, identity providers, and KMS setup; and server configuration.

### 2. The dashboard targets Metrics V3 {#metrics}

Dashboard widgets query the **MinIO Metrics V3** catalog, the metric set current deployments actually scrape, with guards for its zero-value and per-node export semantics so a panel distinguishes a real zero from missing data. The mapping is recorded in [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/main/docs/metrics-v3.md).

### 3. A smaller, quieter payload {#payload}

The embedded frontend went from roughly 10 MB to under 3 MB, rebuilt reproducibly byte for byte and enforced by a release gate. There is no telemetry of any kind, and no external network dependency in the page itself.

### 4. Bilingual interface {#i18n}

The interface, help content, and documentation links are available in English and Chinese behind a per-page toggle, with no added runtime dependencies.

### 5. For developers: the module graph {#source}

As of 2026-09-13, Console main directly requires `github.com/pgsty/silo-pkg/v3`
v3.14.0 and upstream SDK `v7.3.1-0.20260910142817-60bd07042d49`, while retaining
the historical `github.com/minio/console` module path. Its maintained-component
replacement is:

```go
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260913012246-4f609a4da3bb
```

Go does not inherit dependency replacements. Server must explicitly select both
PGSTY Console and MC. Separate compatibility pins retain go-systemd v22.6.0
for NetBSD and tablewriter v0.0.5 for the MC API. Legacy transitive minio/pkg
from colorjson is separate from the maintained silo-pkg policy implementation.
The old `minio/pkg => silo-pkg` and `minio-go => silo-go` replacements are unsupported.

**This is the source graph, not the v2.4.0 release graph.** v2.4.0 uses pkg
v3.13.3, MC `c8aa5d25a63a` and SDK `0e78d3f18efe`. Server 20260903 embeds Console
`464a59d73ada` (v2.3.0 version identity); Server main selects `417559bb2c97`.
See the [component matrix](/compatibility/versions/) and
[embedding guide](https://github.com/pgsty/silo-console/blob/main/docs/Embedding.md).

The release-gating target is the coordinated SILO, Console, mcli and pkg stack.
Unmodified upstream MinIO/MC probes are non-blocking compatibility signals;
they do not require pkg downgrades or duplicate APIs.

## Migration {#migration}

An existing MinIO Console deployment upgrades in place. The service unit, service account, and configuration file keep their names, and every `CONSOLE_*` variable is read unchanged, so the usual path is to install the `silo-console` package over the old one and restart.

Two behaviors change on first start and are worth expecting:

- `silo-console` will not update itself. Roll out new versions through packages, images, or your orchestrator.
- Any workflow that relied on the console reaching MinIO-operated services — the update feed, licensing, or telemetry — no longer has anything to reach.

## See also {#see-also}

- [Silo server compatibility](/compatibility/server/) — the server this console administers
- [MCLI client compatibility](/compatibility/mcli/) — the command-line client
- [Console release notes](/tags/console/) and [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1
[v2.3.0]: https://github.com/pgsty/silo-console/releases/tag/v2.3.0
