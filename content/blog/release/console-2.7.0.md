---
title: "SILO Console 2.7.0: Ten Languages, Usage Worker and Container Fixes"
linkTitle: "Console 2.7.0"
date: 2026-11-09
author: "SILO"
description: "Console 2.7.0: ten UI languages and Arabic RTL, usage-worker TLS and scheduling fixes, folder sizes over plain HTTP, container fixes, released mcli and silo-pkg dependencies, and updated API documentation."
tags: [Release, Console]
draft: false
weight: 1
url: "/blog/release/console-2.7.0/"
---

Console 2.7.0 expands the administration interface to ten languages, fixes
container HTTPS and temporary files, adopts the released mcli 20261109 and
silo-pkg 3.16.0 and updates API documentation. It also fixes usage-worker TLS
and scheduling, folder sizes over plain HTTP and malformed uploads, all found
in the final pre-release review. Publication status and assets are on
[GitHub releases](https://github.com/pgsty/silo-console/releases).

[GitHub releases](https://github.com/pgsty/silo-console/releases) ·
[Changes since 2.6.0](https://github.com/pgsty/silo-console/compare/v2.6.0...v2.7.0) ·
[Console compatibility](/compatibility/console/)

## Fixes found before release {#fixes}

The final review before release found defects that 2.6.0 already shipped
with. 2.7.0 fixes them:

- **Folder sizes over plain HTTP.** Embedded Console is usually opened at
  `http://<ip>:9001`, which browsers do not treat as a secure context. There
  **Calculate folder sizes** and the decryption-key copy button silently did
  nothing. Both now work over HTTP.
- **Usage worker TLS.** `console usage-worker` accepts `--certs-dir` and trusts
  the same roots as `console server`: the system roots, `certs/CAs` and
  Console's `public.crt`. It applies `CONSOLE_MINIO_SERVER_TLS_SKIP_VERIFY` to
  the SILO endpoint only. Earlier workers trusted only the system roots and
  failed against a private CA. The worker only reads the directory: it neither
  creates it nor loads `private.key`.
- **Scan budget.** `CONSOLE_USAGE_SCAN_TIMEOUT` now limits listing time summed
  across scan slices. Time a bucket spends queued behind other buckets no
  longer counts, so many large buckets no longer end `limited` together.
  Buckets left limited by the earlier accounting resume with a full budget on
  their next retry.
- **Worker restarts.** A scan interrupted by stopping the worker returns to the
  queue with its checkpoint and resumes at once, instead of showing
  "Update failed" for at least 30 seconds. Bucket changes the worker received
  before stopping are saved rather than dropped.
- **Deleted buckets.** The worker handles bucket creation and deletion events.
  Deleting a bucket, including a force delete that emits no object events,
  discards its saved totals, so a bucket re-created under the same name never
  shows them.
- **Busy scanner.** Without the usage database, **Refresh** waits and retries
  for about 30 seconds when the server's scan slots are busy (HTTP 429),
  instead of marking buckets as failed.
- **Uploads.** Malformed or truncated multipart uploads return an error instead
  of panicking the request handler.
- **Arabic field layout.** The reveal button and unit selectors of password,
  URL, e-mail and number fields stay beside the text instead of covering it,
  and the task-count badge is back in its corner.

Before upgrading the optional usage worker, stop all older workers, then start
2.7.0 workers. Mixed versions do not accumulate the new scan budget
consistently.

## Ten languages in one menu {#languages}

The login page, public pages and signed-in Console share a language menu.
The command palette offers the same choices:

| Language | Menu label |
| --- | --- |
| English | English |
| Simplified Chinese | 简体中文 |
| French | Français |
| German | Deutsch |
| Russian | Русский |
| Spanish | Español |
| Brazilian Portuguese | Português (Brasil) |
| Japanese | 日本語 |
| Arabic | العربية |
| Turkish | Türkçe |
{.wide .expand}

English remains the default and fallback. Console remembers an explicit
preference instead of selecting a language from browser settings. Existing
`en` and `zh` preferences remain valid; the earlier `pt` value maps to `pt-BR`.
Unknown preferences fall back to English.

All dictionaries ship with the frontend. Switching language requires no
translation download, works offline after the application loads, and preserves
unsaved form values. This increases the first download: the nine translated
catalogs occupy approximately **568 KB gzip** in nine independently compressed
assets. All are loaded eagerly. Content-hashed assets use a one-year immutable
cache, while HTML is revalidated; changing one language does not invalidate the
other catalogs. No translation service, additional fonts or new
localization framework is needed.

Chinese retains complete first-party coverage. Other languages fall back to
English when a translation is missing. The new catalogs include AI-assisted
drafts; complete key coverage does not imply native-speaker review. Translation
corrections are welcome through
[Console pull requests](https://github.com/pgsty/silo-console/pulls).

Brazilian Portuguese was contributed by
**[@EduardoAndradeMachado](https://github.com/EduardoAndradeMachado)** in
[PR #83](https://github.com/pgsty/silo-console/pull/83), preserving the original
authored commits. The subsequent ten-language implementation replaces the
Portuguese-only asynchronous loader with the shared static dictionaries.

## Locale formatting and Arabic layout {#rtl}

Dates, numbers and quantity labels use the selected locale, including the
plural forms needed by Russian and Arabic. Arabic also receives right-to-left
navigation, spacing, directional controls, mobile drawers and tab navigation.

Object paths, bucket names, ARN values, policy JSON and raw Trace/log data remain
left-to-right. Object names, server errors, audit events and log contents are
preserved; language selection does not translate stored data or server output.
Documentation remains bilingual: Chinese UI links open Chinese documentation,
while all other languages open English documentation.

The [implementation](https://github.com/pgsty/silo-console/commit/51a735992b63593046453d997e7a18584bae2336)
adds catalog validation and browser coverage for keyboard selection, saved
preferences, offline switching, unsaved forms and RTL behavior. Chinese
coverage, placeholders and plural-form validation remain checked. The
[embedded GUI rebuild](https://github.com/pgsty/silo-console/commit/0059ee2d979e8406f3018766584337c92d5e55fa)
is recorded separately from the source change.

## Container HTTPS and large requests {#containers}

Previous Console images, through 2.6.0, used a minimal `scratch` filesystem
without system CA roots or `/tmp`. Without an operator-supplied certificate
bundle, outbound HTTPS to a SILO server or OIDC provider could fail with
`x509: certificate signed by unknown authority`. Multipart requests that needed
temporary files could fail because the directory did not exist.

[PR #84](https://github.com/pgsty/silo-console/pull/84) fixes all three image
build paths:

- Include a system CA bundle at `/etc/ssl/certs/ca-certificates.crt`, using the
  same UBI trust-store preparation as the maintained SILO and mcli images.
- Provide `/tmp` with mode `1777`, allowing large multipart requests to spill to
  disk. A read-only container filesystem still needs a writable mount or tmpfs
  at that path.
- Retain the minimal image, non-root `1000:1000` runtime, existing certificate
  configuration and entrypoint. Release-image verification now checks the CA
  bundle and temporary-directory permissions.

Public certificates can use system trust without disabling TLS verification.
Private CAs still need explicit configuration. An existing mount over the
system bundle continues to override it. Official images remain on Docker Hub
as **`docker.io/pgsty/silo-console`**, tagged `v2.7.0` for this release.

## Upgrade and dependency boundaries {#upgrade}

Folder and bucket usage scans, retained-version totals, freshness indicators
and the optional PostgreSQL usage worker already shipped in
[2.6.0](/blog/release/console-2.6.0/). They are retained in 2.7.0, with the
worker fixes [above](#fixes). PostgreSQL is
needed only for that optional worker, not for the language or container changes.

2.7.0 adopts the released components verified in
[PR #86](https://github.com/pgsty/silo-console/pull/86):

| Component | Reviewed source selection |
| --- | --- |
| Go | 1.27.3 |
| Node / Yarn | 24.22.1 / 4.13.0 |
| `github.com/pgsty/silo-pkg/v3` | v3.16.0, commit `b7aeea85e84e8888d6ab424c7123a1297711bc3f` |
| Maintained MC source | mcli 20261109, commit `e1d4cc5abfe00b674eb36347399e7398990be467` |
| Upstream `github.com/minio/minio-go/v7` | `v7.4.2-0.20261025165926-320af050c445` |
| go-swagger / runtime / server-middleware | v0.36.7 / v0.33.4 / v0.33.4 |
| `golang.org/x/net` | v0.62.0 |
| `golang.org/x/crypto` | `v0.58.1-0.20261009181718-2f1f834330b2` |
{.wide .expand}

The [mcli 20261109](/blog/release/mcli-20261109/) tag
`RELEASE.2026-11-09T00-00-00Z` is not Go SemVer. The replacement therefore uses
`github.com/pgsty/mc v0.0.0-20261109021353-e1d4cc5abfe0`, the exact official
release commit, while retaining `github.com/minio/mc` imports. This is not a
pre-release snapshot. [silo-pkg 3.16.0](/blog/release/pkg-3.16.0/) uses its
ordinary module tag. `hack/deps-release.json` records both release forms and
full commits, verified against the public Go proxy, checksum database and go.sum.

These selections bring cpuid v2.4.2, YAML v3.0.6 and gjson v1.20.1. Pretty
remains v1.2.2 to preserve formatting. The module graph selects go-jose v4.1.9,
but JOSE is absent from the standalone Console package dependency set; this is
not a claim of a reachable JOSE vulnerability fix. Existing tablewriter,
runewidth and go-systemd replacements and the reviewed pgx/puddle versions remain.

SILO Server 20261026 embeds Console 2.5.1. Updating standalone Console does not
replace that embedded frontend or supply newer server APIs. Embedders must
select the corresponding Console source and copy its maintained MC replacement;
Go does not inherit replacements from dependencies. The supported administration
target remains **pgsty/silo**; compatibility with unmodified upstream MinIO is
best effort.

The obsolete upstream-MinIO build job was removed in
[PR #85](https://github.com/pgsty/silo-console/pull/85). The maintained SILO
acceptance matrix, advisory upstream-MC compatibility probe and frontend/container
asset-consistency check remain.

## API documentation and validation {#api-docs}

Swagger v0.36.7 fixes array context validation stopping at zero elements.
Regeneration preserves the customized server, configuration-import binding,
schema and TypeScript client. The current schema has no `readOnly` constraints,
so this does not add new contextual request restrictions.

The generated `/api/v1/docs` page loads Redoc 3 as an ES module. Its
`/swagger.json` request now reaches the API instead of the frontend SPA fallback.
Generation is reproducible and the request-binding and documentation routes
have direct regression tests. The required matrix also exercises the MC adapter
against real SILO: version reads, delete markers, exact-key removal boundaries,
error propagation, watch cancellation, lifecycle and diagnostics behavior.

CI uses explicit permission and platform matrices and the project toolchain
version files. Automatic test retries and redundant settings were removed;
the maintained integration and artifact checks remain. Observer renewal is
tested with production defaults and database-state synchronization.

## Contributors {#contributors}

The Console record now includes **six human contributors**, covering all
**42 issues and 44 pull requests** as of 2026-11-09. Issue and PR authors count
regardless of merge status; inherited upstream authorship remains in Git
history and copyright notices.

- **[@Vonng](https://github.com/Vonng)** — maintenance, fixes, multilingual
  integration, testing, releases and documentation.
- **[@cyberbret](https://github.com/cyberbret)** — folder and bucket usage scans
  and the optional durable worker in [#70](https://github.com/pgsty/silo-console/pull/70),
  merged with follow-up repairs and shipped in 2.6.0.
- **[@EduardoAndradeMachado](https://github.com/EduardoAndradeMachado)** —
  Brazilian Portuguese translation in [#83](https://github.com/pgsty/silo-console/pull/83),
  the community contribution behind this release's language expansion.
- **[@kh0mka](https://github.com/kh0mka)** — reported lost bucket quotas in
  [#72](https://github.com/pgsty/silo-console/issues/72), fixed through #74 before 2.6.0.
- **[@jiri-pejchal](https://github.com/jiri-pejchal)** — reported internal-metrics
  exposure through the share proxy in [#52](https://github.com/pgsty/silo-console/issues/52),
  fixed in 2.4.1.
- **[@azataiot](https://github.com/azataiot)** — reported and analyzed high-latency
  health-report truncation in [#63](https://github.com/pgsty/silo-console/issues/63),
  fixed in 2.5.0.

See the [community contribution record](/about/contributors/) for actual PR
states and historical credits.

## Verified release and source {#verification}

Tag [`v2.7.0`](https://github.com/pgsty/silo-console/tree/v2.7.0) resolves to
[`4e91ae506e706ccdecb512b1d8b5ab4d9871d505`](https://github.com/pgsty/silo-console/commit/4e91ae506e706ccdecb512b1d8b5ab4d9871d505).
The release workflow accepted this exact commit:

- [Required matrix](https://github.com/pgsty/silo-console/actions/runs/42612682270), including maintained SILO integration, the permission matrix, SSO, replication, shared downloads, PostgreSQL usage, Swagger regeneration, platform builds, package lifecycle and independent artifact reproduction.
- [Required vulnerability checks](https://github.com/pgsty/silo-console/actions/runs/42612682615).
- [Tag release pipeline](https://github.com/pgsty/silo-console/actions/runs/42616923335): checksum and image signatures, SPDX attestations and GitHub provenance verified.

The release contains **44 assets**: six platform executables, six
bundles, nine Linux packages, a source archive, SPDX SBOMs, legal files, the
SHA-256 manifest and its Sigstore bundle. Verification commands are in the
[tagged release contract](https://github.com/pgsty/silo-console/blob/v2.7.0/docs/release-contract.md).

The multi-platform image is `docker.io/pgsty/silo-console:v2.7.0` for Linux
amd64 and arm64, with immutable digest:

```text
sha256:85aeb3ce802eb4aaae33503bcb665dc72c7544db037b5cda5ffae73b26719892
```

After publication, `promote-image.yaml` ([run 42618891230](https://github.com/pgsty/silo-console/actions/runs/42618891230)) verified the published release, signatures, SBOM attestation, provenance and anonymous access, then promoted this digest to `latest`.

An earlier `v2.7.0` tag on `26ce922` produced only an unpublished draft and
candidate image; it was replaced by this tag before publication, after the final
review found the fixes listed above.

