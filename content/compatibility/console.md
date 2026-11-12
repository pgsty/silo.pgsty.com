---
title: "Console Compatibility Notes"
linkTitle: "Console"
description: "Differences between SILO Console and the upstream MinIO Console"
url: "/compatibility/console/"
weight: 30
type: docs
icon: fa-solid fa-window-maximize
---

> [!NOTE]
> **Latest published release:** [Console v2.7.1](/blog/release/console-2.7.1/) (2026-11-12, UTC+8) preserves service-account policy inheritance on metadata edits, blocks empty inline-policy variants, surfaces save errors inside the edit modal, enforces strict policy JSON decoding, and adopts Go 1.27.4, [silo-pkg v3.16.1](/blog/release/pkg-3.16.1/), and [mcli 20261112](/blog/release/mcli-20261112/). **Published SILO Server 20261109 embeds Console v2.7.0** (Server 20261026 embeds v2.5.1; prepared Draft Server 20261112 embeds v2.7.1). Upgrading standalone Console does not replace an older Server's embedded Console; explicit inline-policy reset (`{}`) requires the matching post-`20261109` Server update, and built-in policy Reset and live bucket inventory reads require Server 20261026 or later. See the [component matrix](/compatibility/versions/).

SILO Console is Silo's build of the MinIO Console; **published SILO Server 20261109 embeds Console v2.7.0** (Server 20261026 embeds v2.5.1), and standalone builds are published independently. This page records where SILO Console and the upstream MinIO Console are interchangeable and where they differ. Start with the [three-level overview](/compatibility/), then use the details below to check UI and automation behavior.

[`pgsty/silo-console`](https://github.com/pgsty/silo-console) continues the upstream `minio/console` history from its final commit, [`feff71e4`](https://github.com/pgsty/silo-console/commit/feff71e48e39547834399a84a9460edb4fb50563) (2026-04-16); the rebrand begins at `50797deb` (2026-08-04). The upstream repository is no longer published — `github.com/minio/console` now returns 404, where `minio/mc` was merely archived — so the source lineage survives only in this fork. The Go module path still resolves, because the module proxy continues to serve the versions it already cached. Release records: [v2.0.0](/blog/release/console-2.0.0/), [v2.1.0](/blog/release/console-2.1.0/), [v2.1.1], [v2.2.0](/blog/release/console-2.2.0/), [v2.2.1], [v2.3.0](https://github.com/pgsty/silo-console/releases/tag/v2.3.0), [v2.4.0](/blog/release/console-2.4.0/), [v2.4.1](/blog/release/console-2.4.1/), [v2.4.2](/blog/release/console-2.4.2/), [v2.5.1](/blog/release/console-2.5.1/), [v2.6.0](/blog/release/console-2.6.0/), [v2.7.0](/blog/release/console-2.7.0/), and [v2.7.1](/blog/release/console-2.7.1/).

<a id="candidate-policy-edit" data-td-print-local></a>

## 2.7.1 service-account policy inheritance, strict JSON validation, and HTTPS redirects {#release-271}

[Console 2.7.1](/blog/release/console-2.7.1/) (`3825ebc44451`) tracks inherited and inline policies separately (`1be8a74bf`), so changing an access key's name, description, expiry or status preserves inheritance instead of saving a copy of its parent's policy. To remove an existing inline restriction, turn off **Restrict beyond user policy**; the Console sends an explicit empty policy and restores inheritance. While **Restrict beyond user policy** remains enabled, creating or replacing a policy with an empty editor, `{}`, `{"Statement":[]}`, or `{"Statement":null}` prevents saving (`a1a84cab4`, `1fdb279fd`, `3825ebc44`). Empty documents with case-insensitive, Unicode-folded, or duplicate-key field names accepted by the backend are also blocked, and save errors render inside the edit modal. An unchanged historical empty inline policy may still accompany a metadata-only edit, preserving its existing permissions; Console API endpoints also enforce strict policy JSON validation (rejecting unknown fields, trailing JSON, empty `Principal: {}` / `NotPrincipal`, and empty named policies). When TLS redirect is enabled (`CONSOLE_SECURE_TLS_REDIRECT=on`), HTTP-to-HTTPS browser redirects preserve the incoming request host (or explicit `CONSOLE_SECURE_TLS_HOST`) instead of redirecting wildcard listeners (`--host 0.0.0.0` / `[::]`) to `https://0.0.0.0:<tls-port>`, backed by `unrolled/secure v1.18.0`.

Explicit reset to inheritance requires the matching [post-20261109 Server policy semantics](/compatibility/server/#candidate-after-20261109): omitted/null means preserve, explicit empty means reset, and a nonempty document without Version receives the default. It is not included in Console v2.7.0 or published Server 20261109. Standalone Console 2.7.1 protects metadata-only saves immediately; embedded Console updates arrive with the next Server release.

## 2.7.0 ten-language UI, container CA trust and usage-worker repairs {#release-270}

[Console 2.7.0](/blog/release/console-2.7.0/) (embedded in [SILO Server 20261109](/blog/release/silo-20261109/)) delivers:

- **Ten UI languages and Arabic RTL:** expands the shared language menu and command palette to ten bundled languages with Arabic right-to-left layout and field-control alignment (`a9da731c5`, `bc17e124a`).
- **Container CA bundle and `/tmp`:** scratch container images include `/etc/ssl/certs/ca-certificates.crt` and a writable `/tmp` (`1777`), enabling public HTTPS endpoints and large multipart request buffering out of the box.
- **Plain-HTTP browser actions:** **Calculate folder sizes** and the decryption-key copy action work over plain HTTP (`http://<ip>:9001`) without requiring a browser secure context.
- **Usage-worker TLS, scan budget and lifecycle:** `console usage-worker` honors `--certs-dir` (`certs/CAs` and `public.crt`) alongside system roots (`ec897252f`), counts only active S3 listing slice time against `CONSOLE_USAGE_SCAN_TIMEOUT` (`543d3d2af`), persists received events and checkpoints across graceful shutdowns, and purges saved totals when buckets are deleted (`49ad0dff8`..`082b23700`). Stop all older workers before starting 2.7.0 workers.
- **Upload validation and API docs:** malformed or truncated multipart uploads return HTTP `400` instead of panicking (`f1edc61fe`), and `/api/v1/docs` serves Redoc 3 with `/swagger.json` routed to the API rather than the SPA fallback (`77a4551e6`).

## 2.6.0 usage scans and bucket administration {#release-260}

[Console 2.6.0](/blog/release/console-2.6.0/) adds cancellable folder and bucket usage scans with separate current and retained-version totals, an optional PostgreSQL-backed durable usage worker, strict integer range validation for retention, quota, and replication bandwidth inputs, Object Lock versioning-exclusion guards during bucket creation, inert object-detail/version controls during route transitions ([#81](https://github.com/pgsty/silo-console/pull/81)), and a three-minute keep-alive default for embedded Console servers.

## 2.5.1 administration repairs {#release-251}

Status-only group updates now preserve existing members, while explicit member arrays still replace the member list. OIDC string-array group claims preserve mapped permissions, and secure session cookies are set only when HTTPS or a trusted proxy is configured. Credential exports produce valid UTF-8 JSON, and streaming ZIP downloads preserve the underlying S3 error status if they fail before writing the first byte. Keyboard focus, accessible names, and tab scrolling are also fixed. See the [complete 2.5 release notes](/blog/release/console-2.5.1/).

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

Dashboard widgets query the **MinIO Metrics V3** catalog, the metric set current deployments actually scrape, with guards for its zero-value and per-node export semantics so a panel distinguishes a real zero from missing data. The mapping is recorded in [`docs/metrics-v3.md`](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/metrics-v3.md).

### 3. A smaller, quieter payload {#payload}

The embedded frontend went from roughly 10 MB to under 3 MB, rebuilt reproducibly byte for byte and enforced by a release gate. There is no telemetry of any kind, and no external network dependency in the page itself.

### 4. Interface languages {#i18n}

Console 2.7.0 offers ten UI languages — English, Simplified Chinese, French,
German, Russian, Spanish, Brazilian Portuguese, Japanese, Arabic, and Turkish —
through a shared menu and command palette, with bundled dictionaries and Arabic
RTL (Console 2.6.0 and earlier offered English and Chinese). English remains the
default and fallback. Documentation stays bilingual; server messages and log
contents remain intact. See the [language design](/blog/design/console-languages/)
for scope and maintenance tiers.

### 5. Object listings operate one page at a time {#pagination}

See [B02](/compatibility/#b02). Console v2.4.0 introduced cursor pagination, retained through v2.7.0. Pages default to 100 entries, with 50, 100, 250, 500 and 1,000 available. Navigation offers first, previous and next; there is no load-all mode or arbitrary page jump.

**Sorting, name filtering and select-all apply to the current page.** They cover the whole directory only when the first page already contains it. Paging retains filter text and clears selection; changing page size returns to the first page, and changing directories clears the filter. A failed page leaves the previous page available for retry.

Rewind and deleted-object listings have no cursor. They return at most 1,000 versions within a time budget and disclose incomplete results when either limit is reached. See the [object-browser contract](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/ObjectBrowser.md#paging).

### 6. API responses and automation {#api-output}

See [B04](/compatibility/#b04) and [O05](/compatibility/#o05). Session responses add `accountAccessKey`, and object listings explicitly return `size: 0` for empty objects. Session capabilities also reflect effective permissions. Custom parsers should tolerate added fields, and Console automation should handle pagination, expired sessions and WebSocket errors.

User enable/disable gains a separate `PUT /api/v1/user/{name}/status`; the old `PUT /api/v1/user/{name}` remains but is deprecated. Multi-object downloads retain the existing endpoint and also accept a bounded form request for native streaming ZIP downloads. See [password-permission migration](/compatibility/password-permissions/) and the [v2.4.1 sharing changes](/blog/release/console-2.4.1/); use the current [API definition](https://github.com/pgsty/silo-console/blob/v2.7.0/swagger.yml) for custom integrations.

Console v2.4.2 preserves wrapped S3 errors from bucket-versioning operations and returns `InvalidBucketState` explicitly when Object Lock prevents suspension. This makes the existing Server restriction visible to the caller.

### 7. For developers: the module graph {#source}

Console v2.7.1 requires Go 1.27.4, directly selects `github.com/pgsty/silo-pkg/v3` v3.16.1 and
upstream SDK `v7.4.2-0.20261025165926-320af050c445`, and retains the historical
`github.com/minio/console` module path. Embedders explicitly select these released sources:

```go
replace github.com/minio/console => github.com/pgsty/silo-console v0.0.0-20261111181657-3825ebc44451
replace github.com/minio/mc => github.com/pgsty/mc v0.0.0-20261111180825-a37a9f054fba
```

Go does not inherit dependency replacements. Server must select both PGSTY
Console and MC. go-systemd v22.6.0 preserves NetBSD compatibility and tablewriter
v0.0.5 preserves the MC API. Legacy transitive minio/pkg from colorjson remains
separate from the maintained silo-pkg policy implementation. The old
`minio/pkg => silo-pkg` and `minio-go => silo-go` replacements are unsupported.
See the [component matrix](/compatibility/versions/) and
[embedding guide](https://github.com/pgsty/silo-console/blob/v2.7.1/docs/Embedding.md).

The release-gating target is the coordinated SILO, Console, mcli and pkg stack.
Upstream MinIO/MC probes remain non-blocking compatibility signals and do not
require pkg downgrades or duplicate APIs.

## Migration {#migration}

The official image is [`docker.io/pgsty/silo-console`](https://hub.docker.com/r/pgsty/silo-console). **Linux amd64/arm64 images are published** for `v2.7.1` and `latest` (`sha256:2afef06f8505eadb24d657acd0f68c78bce8b148b1d9b74981454560fa3b055f`; `v2.7.0`: `sha256:85aeb3ce802eb4aaae33503bcb665dc72c7544db037b5cda5ffae73b26719892`); see [release verification](/blog/release/console-2.7.1/#verification). Published [GitHub binaries and packages](https://github.com/pgsty/silo-console/releases/tag/v2.7.1) are also available.

The image runs as UID 1000 with no home directory, so its default certificate directory is `/.console/certs`: mount private CA certificates into `/.console/certs/CAs/`, or choose another path with `--certs-dir`. Starting in `v2.7.0`, the scratch container image includes the system CA bundle at `/etc/ssl/certs/ca-certificates.crt` and a writable `/tmp` (`1777`) out of the box (images on `v2.6.0` and earlier omitted both, requiring a read-only host CA mount at `/etc/ssl/certs/ca-certificates.crt` to reach public HTTPS endpoints).

An existing MinIO Console deployment upgrades in place. The service unit, service account, and configuration file keep their names, and every `CONSOLE_*` variable is read unchanged, so the usual path is to install the `silo-console` package over the old one and restart.

Two behaviors change on first start and are worth expecting:

- `silo-console` will not update itself. Roll out new versions through packages, images, or your orchestrator.
- Any workflow that relied on the console reaching MinIO-operated services — the update feed, licensing, or telemetry — no longer has anything to reach.

When upgrading from a version earlier than v2.4.1, review the [password-policy migration](/compatibility/password-permissions/).
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
