---
title: "Console Compatibility Notes"
linkTitle: "Console"
description: "Differences between SILO Console and the upstream MinIO Console"
url: "/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> **Latest release:** [Console v2.4.1](/blog/release/console-2.4.1/) (2026-09-16), with restricted shared downloads, password-permission separation, streaming ZIPs and signed release artifacts. See the [component matrix](/compatibility/versions/).

SILO Console is Silo's build of the MinIO Console. This page records where the two are interchangeable and where they differ. Start with the [three-level overview](/compatibility/), then use the details below to check UI and automation behavior.

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) continues the upstream `minio/console` history from its final commit, [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563) (2026-04-16); the rebrand begins at `50797deb` (2026-08-04). The upstream repository is no longer published — `github.com/minio/console` now returns 404, where `minio/mc` was merely archived — so the source lineage survives only in this fork. The Go module path still resolves, because the module proxy continues to serve the versions it already cached. Earlier release records: [v2.0.0](/blog/release/console-2.0.0/), [v2.1.0](/blog/release/console-2.1.0/), [v2.1.1], [v2.2.0](/blog/release/console-2.2.0/), and [v2.2.1].

## Principles {#principles}

The fork prioritizes existing integration contracts and explicitly documents authorization, response and interface changes.

- **Renamed** — the artifact on disk (`silo-console`), the product identity in the interface and in `--version`, the distribution channels, and the signing keys.
- **Retained core contracts** — the Go module path `github.com/minio/console`, existing `CONSOLE_*` environment variables (including `CONSOLE_MINIO_SERVER` and `CONSOLE_MINIO_REGION`), and packaging identifiers `minio-console.service`, `console-user` and `/etc/default/console`. REST APIs retain the existing architecture; see [response and operation changes](#api-output) below.
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

### 5. Object listings operate one page at a time {#pagination}

See [B02](/compatibility/#b02). Console v2.4.0 introduced cursor pagination, retained in v2.4.1. Pages default to 100 entries, with 50, 100, 250, 500 and 1,000 available. Navigation offers first, previous and next; there is no load-all mode or arbitrary page jump.

**Sorting, name filtering and select-all apply to the current page.** They cover the whole directory only when the first page already contains it. Paging retains filter text and clears selection; changing page size returns to the first page, and changing directories clears the filter. A failed page leaves the previous page available for retry.

Rewind and deleted-object listings have no cursor. They return at most 1,000 versions within a time budget and disclose incomplete results when either limit is reached. These limits bound browser results, not how many versions the server scans. See the [object-browser contract](https://github.com/pgsty/silo-console/blob/v2.4.1/docs/ObjectBrowser.md#paging).

### 6. API responses and automation {#api-output}

See [B04](/compatibility/#b04) and [O05](/compatibility/#o05). Session responses add `accountAccessKey`, and object listings explicitly return `size: 0` for empty objects. Session capabilities also reflect effective permissions; a visible button does not replace server authorization. Custom parsers should tolerate added fields, and Console automation should handle pagination, expired sessions and WebSocket errors.

User enable/disable gains a separate `PUT /api/v1/user/{name}/status`; the old `PUT /api/v1/user/{name}` remains but is deprecated. Multi-object downloads retain the existing endpoint and also accept a bounded form request for native streaming ZIP downloads. See [password-permission migration](/compatibility/password-permissions/) and the [v2.4.1 sharing changes](/blog/release/console-2.4.1/); use that version's [API definition](https://github.com/pgsty/silo-console/blob/v2.4.1/swagger.yml) for custom integrations.

### 7. For developers: the module graph {#source}

Console v2.4.1 directly requires `github.com/pgsty/silo-pkg/v3` v3.14.1 and
upstream SDK `v7.3.1-0.20260915093545-32e1f32cb176`, retaining the historical
`github.com/minio/console` module path. Embedders explicitly select these released sources:

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20260916075814-1360e26d976d
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20260916070421-e952aa78f10a
```

Go does not inherit dependency replacements. Server must select both PGSTY
Console and MC. go-systemd v22.6.0 preserves NetBSD compatibility and tablewriter
v0.0.5 preserves the MC API. Legacy transitive minio/pkg from colorjson remains
separate from the maintained silo-pkg policy implementation. The old
`minio/pkg => silo-pkg` and `minio-go => silo-go` replacements are unsupported.
See the [component matrix](/compatibility/versions/) and
[embedding guide](https://github.com/pgsty/silo-console/blob/v2.4.1/docs/Embedding.md).

The release-gating target is the coordinated SILO, Console, mcli and pkg stack.
Upstream MinIO/MC probes remain non-blocking compatibility signals and do not
require pkg downgrades or duplicate APIs.

## Migration {#migration}

The official image name is [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console). **Distribution recheck on 2026-09-17: anonymous token requests returned HTTP 401, so public v2.4.1 pulls are not confirmed.** Use the published [GitHub binaries or packages](https://github.com/pgsty/silo-console/releases/tag/v2.4.1). Source or binary publication does not establish image availability; this limitation does not affect Server embedding.

An existing MinIO Console deployment upgrades in place. The service unit, service account, and configuration file keep their names, and every `CONSOLE_*` variable is read unchanged, so the usual path is to install the `silo-console` package over the old one and restart.

Two behaviors change on first start and are worth expecting:

- `silo-console` will not update itself. Roll out new versions through packages, images, or your orchestrator.
- Any workflow that relied on the console reaching MinIO-operated services — the update feed, licensing, or telemetry — no longer has anything to reach.

For v2.4.1, also review the [password-policy migration](/compatibility/password-permissions/).
Linux packages use `/etc/silo-console/certs`; migrate existing certificates or
retain their old path in `CONSOLE_OPTS` in `/etc/default/console` before restarting.
The service and configuration names are retained. Shared downloads require no new
setting. See the [v2.4.1 release notes](/blog/release/console-2.4.1/).

## See also {#see-also}

- [Silo server compatibility](/compatibility/server/) — the server this console administers
- [MCLI client compatibility](/compatibility/mcli/) — the command-line client
- [Console release notes](/tags/console/) and [`CHANGELOG.md`](https://github.com/pgsty/silo-console/blob/main/CHANGELOG.md)

[v2.1.1]: https://github.com/pgsty/silo-console/releases/tag/v2.1.1
[v2.2.1]: https://github.com/pgsty/silo-console/releases/tag/v2.2.1
[v2.3.0]: https://github.com/pgsty/silo-console/releases/tag/v2.3.0
